"""LLM 医学信息抽取 — 医生口述 → 结构化 JSON。"""
from __future__ import annotations

import json
import re
from typing import Any

from backend.app.core.llm_service import chat
from backend.app.services.data_loader import get_few_shot_examples
from backend.app.services.exam_registry import normalize_exam_type

SCHEMA_SUMMARIES: dict[str, str] = {
    "abdominal_ultrasound": """
exam_type: "abdominal_ultrasound" (必填)
organs_examined: liver, gallbladder, bile_duct, pancreas, spleen, kidney_left, kidney_right, bladder
liver: size.status, morphology, capsule, parenchyma_echo, vessels, lesions[]
gallbladder: size, wall, cavity, lesions[] (type: stone/polyp, size_mm, mobility, acoustic_shadow)
bile_duct: common_bile_duct_mm, common_bile_duct_status, hepatic_duct
pancreas: visibility, size, echo, duct_mm, lesions[]
spleen: size.thickness_mm, size.status, echo, lesions[]
kidneys.left/right: size.length_mm, morphology, cortex_echo, collecting_system, lesions[]
bladder: filling, wall, wall_thickness_mm, cavity, lesions[]
free_fluid: present, description
""",
    "thyroid_ultrasound": """
exam_type: "thyroid_ultrasound" (必填)
organs_examined: thyroid_right, thyroid_left, isthmus
thyroid_right/left: size, echo, nodules[] (location, size_mm, echo, boundary, calcification, halo)
isthmus: thickness_mm, description
""",
    "breast_ultrasound": """
exam_type: "breast_ultrasound" (必填)
organs_examined: breast_right, breast_left
breast_right/left: gland_echo, duct, nodules[] (quadrant, location, size_mm, echo, boundary)
""",
    "gynecology_ultrasound": """
exam_type: "gynecology_ultrasound" (必填)
organs_examined: uterus, ovary_left, ovary_right, adnexa
uterus: size, position, myometrium_echo, endometrium_thickness_mm, fibroids[]
ovary_left/right: size, follicles, cysts[], solid_mass
adnexa: description
""",
    "cardiac_ultrasound": """
exam_type: "cardiac_ultrasound" (必填)
organs_examined: lv, rv, atria, valves, pericardium
lv: internal_diameter_mm, wall_thickness_mm, wall_motion, ef_percent
valves: mitral, aortic, tricuspid, pulmonary
atria: left_atrium_mm
pericardium: description
""",
    "vascular_ultrasound": """
exam_type: "vascular_ultrasound" (必填)
organs_examined: carotid_right, carotid_left, vertebral, lower_limb
carotid_right/left: imt_mm, stenosis_percent, plaques[], description
vertebral: description
lower_limb: description
""",
    "superficial_ln_ultrasound": """
exam_type: "superficial_ln_ultrasound" (必填)
organs_examined: cervical, axillary, other
cervical/axillary/other: nodes[] (location, size_mm, shape, boundary, hilum, blood_flow)
""",
}

COMMON_RULES = """
other_findings: string
impression_hints: 提示性短语数组（非诊断）
metadata: { asr_text, uncertain_fields[] }
未提及的器官/字段必须 omit（整段不写），不要填「正常」，也不要把 omit 的字段放进 uncertain_fields。
uncertain_fields 仅用于：口述含糊、数值不确定、或已在 JSON 中填写但 confidence 低的字段路径。
医生只说某器官「未见明显异常」时，可写 other_findings 或省略该器官，禁止把 liver.size、pancreas.echo 等未填字段列入 uncertain_fields。
病灶级不确定用 lesions[].uncertainty: true，并在 uncertain_fields 写具体路径如 liver.lesions[0].type。
location 等描述字段必须使用中文（如「右叶」「上极」），禁止使用 right_lobe 等英文 key。
"""


def _path_exists(data: Any, path: str) -> bool:
    """字段路径在 structured 中是否真实存在。"""
    parts = re.split(r"\.|\[|\]", path)
    parts = [p for p in parts if p]
    cur: Any = data
    for p in parts:
        if isinstance(cur, dict):
            if p not in cur:
                return False
            cur = cur[p]
        elif isinstance(cur, list):
            try:
                cur = cur[int(p)]
            except (ValueError, IndexError, TypeError):
                return False
        else:
            return False
    return True


def _collect_uncertainty_flags(data: Any, prefix: str = "") -> list[str]:
    """扫描 uncertainty: true 的字段路径。"""
    found: list[str] = []
    if isinstance(data, dict):
        if data.get("uncertainty") is True and prefix:
            found.append(prefix)
        for key, val in data.items():
            if key in ("metadata", "exam_type"):
                continue
            child = f"{prefix}.{key}" if prefix else key
            found.extend(_collect_uncertainty_flags(val, child))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            found.extend(_collect_uncertainty_flags(item, f"{prefix}[{i}]"))
    return found


def _sanitize_uncertain_fields(structured: dict) -> None:
    """去掉 LLM 误填的「未口述=不确定」字段，仅保留真实存在且需确认的路径。"""
    meta = structured.setdefault("metadata", {})
    raw = meta.get("uncertain_fields")
    llm_paths: list[str] = []
    if isinstance(raw, list):
        llm_paths = [str(p).strip() for p in raw if isinstance(p, str) and str(p).strip()]

    auto_paths = _collect_uncertainty_flags(structured)
    merged: list[str] = []
    seen: set[str] = set()
    for path in llm_paths + auto_paths:
        if path in seen:
            continue
        if _path_exists(structured, path):
            seen.add(path)
            merged.append(path)

    meta["uncertain_fields"] = merged


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return None
    return None


def build_extraction_prompt(
    asr_text: str,
    few_shot_count: int = 2,
    exam_type: str = "abdominal_ultrasound",
) -> list[dict[str, str]]:
    et = normalize_exam_type(exam_type)
    examples = get_few_shot_examples(few_shot_count, et)
    few_shot_block = ""
    for ex in examples:
        few_shot_block += f"\n口述：{ex['asr_text']}\nJSON：{json.dumps(ex['structured'], ensure_ascii=False)}\n"

    schema_summary = SCHEMA_SUMMARIES.get(et, SCHEMA_SUMMARIES["abdominal_ultrasound"])

    system = (
        "你是超声报告结构化助手。将医生口述的检查所见转为 JSON，严格遵循 Schema。"
        "只抽取所见，不做诊断。数值带单位含义（size_mm 等为毫米）。"
        f"\nSchema 摘要：{schema_summary}\n{COMMON_RULES}"
    )
    user = f"Few-shot 示例：{few_shot_block}\n请结构化以下口述，只返回 JSON：\n{asr_text}"

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def extract_structure(
    asr_text: str,
    *,
    few_shot_count: int = 2,
    exam_type: str = "abdominal_ultrasound",
) -> dict[str, Any]:
    """口述文本 → 结构化 JSON。返回 { ok, structured?, error?, usage? }"""
    asr_text = (asr_text or "").strip()
    if not asr_text:
        return {"ok": False, "error": "口述文本为空"}

    et = normalize_exam_type(exam_type)
    messages = build_extraction_prompt(asr_text, few_shot_count, et)
    usage: dict[str, int] = {}
    ok, content = chat(messages, json_mode=True, usage_out=usage)
    if not ok:
        return {"ok": False, "error": content, "usage": usage}

    structured = _extract_json(content)
    if not structured:
        return {"ok": False, "error": f"无法解析 LLM 返回的 JSON: {content[:300]}", "usage": usage}

    structured.setdefault("exam_type", et)
    meta = structured.setdefault("metadata", {})
    meta.setdefault("asr_text", asr_text)
    _sanitize_uncertain_fields(structured)

    return {"ok": True, "structured": structured, "usage": usage, "raw_llm": content}
