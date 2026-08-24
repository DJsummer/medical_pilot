"""非腹部超声 — 规则模板报告生成。"""
from __future__ import annotations

from typing import Any

from backend.app.services.data_loader import load_template
from backend.app.services.exam_registry import exam_label

from backend.app.services.term_mapper import humanize_location, humanize_term

ECHO_MAP = {
    "anechoic": "无回声",
    "hypoechoic": "低回声",
    "hyperechoic": "强回声",
    "mixed": "混合回声",
    "isoechoic": "等回声",
}
BOUNDARY_MAP = {"clear": "边界清", "unclear": "边界欠清"}
ECHO_NORMAL_MAP = {
    "normal": "回声均匀",
    "increased": "回声增强",
    "decreased": "回声减低",
    "heterogeneous": "回声不均匀",
}


def _join(parts: list[str]) -> str:
    parts = [p.strip() for p in parts if p and p.strip()]
    if not parts:
        return ""
    text = "，".join(parts)
    if not text.endswith("。"):
        text += "。"
    return text


def _impression(data: dict, template: dict, default_key: str = "impression_no_abnormal") -> str:
    hints = data.get("impression_hints") or []
    if hints:
        return "\n".join(h + ("。" if not h.endswith("。") else "") for h in hints)
    return template.get(default_key, f"{exam_label(data.get('exam_type', ''))}未见明显异常。")


def _render_nodule_list(nodules: list, prefix: str = "") -> list[str]:
    lines: list[str] = []
    for n in nodules or []:
        if not isinstance(n, dict):
            continue
        loc = n.get("location") or n.get("quadrant") or prefix
        loc = humanize_location(loc) or loc
        size = n.get("size_mm")
        echo = ECHO_MAP.get(n.get("echo") or "", "") or humanize_term(n.get("echo"), kind="echo")
        boundary = BOUNDARY_MAP.get(n.get("boundary") or "", "")
        parts = []
        if loc and size:
            parts.append(f"{loc}可见约{size}mm{echo or '结节'}")
        elif size:
            parts.append(f"可见约{size}mm{echo or '结节'}")
        if boundary:
            parts.append(boundary)
        if n.get("calcification"):
            parts.append("伴钙化")
        if n.get("posterior_enhancement"):
            parts.append("后方回声增强")
        if parts:
            lines.append(_join(parts).rstrip("。"))
    return lines


def generate_thyroid_report(data: dict) -> dict[str, str]:
    template = load_template("thyroid_ultrasound")
    sections: list[str] = []

    for side, label in [("thyroid_right", "甲状腺右叶"), ("thyroid_left", "甲状腺左叶")]:
        lobe = data.get(side) or {}
        if not lobe:
            continue
        parts: list[str] = []
        size = lobe.get("size") or {}
        if size.get("length_mm"):
            parts.append(f"{label}长径约{size['length_mm']}mm")
        echo = lobe.get("echo")
        if echo == "normal" and not lobe.get("nodules"):
            parts.append(f"{label}大小形态正常，回声均匀")
        elif echo in ECHO_NORMAL_MAP:
            parts.append(f"{label}{ECHO_NORMAL_MAP[echo]}")
        if lobe.get("echo_description"):
            parts.append(lobe["echo_description"])
        nodule_lines = _render_nodule_list(lobe.get("nodules") or [], label)
        if parts:
            sections.append(_join(parts))
        sections.extend(nodule_lines)

    isthmus = data.get("isthmus") or {}
    if isthmus.get("thickness_mm"):
        sections.append(f"峡部厚约{isthmus['thickness_mm']}mm。")
    if isthmus.get("description"):
        sections.append(isthmus["description"] + ("。" if not isthmus["description"].endswith("。") else ""))

    if data.get("other_findings"):
        sections.append(data["other_findings"])

    findings = "\n".join(s for s in sections if s)
    return {
        "findings_text": findings,
        "impression_text": _impression(data, template),
    }


def generate_breast_report(data: dict) -> dict[str, str]:
    template = load_template("breast_ultrasound")
    sections: list[str] = []

    for side, label in [("breast_right", "右侧乳腺"), ("breast_left", "左侧乳腺")]:
        breast = data.get(side) or {}
        if not breast:
            continue
        parts: list[str] = []
        echo = breast.get("gland_echo")
        if echo == "normal" and not breast.get("nodules"):
            parts.append(f"{label}腺体回声均匀")
        elif echo in ECHO_NORMAL_MAP:
            parts.append(f"{label}腺体{ECHO_NORMAL_MAP[echo]}")
        if breast.get("duct"):
            parts.append(f"导管{breast['duct']}")
        if parts:
            sections.append(_join(parts))
        for n in breast.get("nodules") or []:
            quad = n.get("quadrant") or ""
            loc = n.get("location") or label
            prefix = f"{loc}{quad}" if quad else loc
            sections.extend(_render_nodule_list([{**n, "location": prefix}]))

    if not sections:
        sections.append("双侧乳腺腺体回声均匀，导管未见扩张。")

    return {
        "findings_text": "\n".join(sections),
        "impression_text": _impression(data, template),
    }


def generate_gynecology_report(data: dict) -> dict[str, str]:
    template = load_template("gynecology_ultrasound")
    sections: list[str] = []

    uterus = data.get("uterus") or {}
    if uterus:
        parts: list[str] = []
        size = uterus.get("size") or {}
        if size.get("length_mm") and size.get("width_mm"):
            parts.append(f"子宫长径约{size['length_mm']}mm，宽径约{size['width_mm']}mm")
        pos_map = {"anteverted": "前位", "retroverted": "后位", "neutral": "居中"}
        if uterus.get("position") in pos_map:
            parts.append(f"子宫{pos_map[uterus['position']]}")
        if uterus.get("myometrium_echo") == "normal":
            parts.append("肌层回声均匀")
        elif uterus.get("myometrium_echo") in ECHO_NORMAL_MAP:
            parts.append(f"肌层{ECHO_NORMAL_MAP[uterus['myometrium_echo']]}")
        if uterus.get("endometrium_thickness_mm"):
            desc = uterus.get("endometrium_description") or "内膜"
            parts.append(f"{desc}厚约{uterus['endometrium_thickness_mm']}mm")
        for fib in uterus.get("fibroids") or []:
            loc = fib.get("location") or "肌层"
            size = fib.get("size_mm")
            echo = ECHO_MAP.get(fib.get("echo") or "", "低回声")
            parts.append(f"子宫{loc}可见约{size}mm{echo}团")
        if parts:
            sections.append(_join(parts))

    for side, label in [("ovary_left", "左侧卵巢"), ("ovary_right", "右侧卵巢")]:
        ovary = data.get(side) or {}
        if not ovary:
            continue
        parts: list[str] = []
        size = ovary.get("size") or {}
        if size.get("length_mm"):
            parts.append(f"{label}长径约{size['length_mm']}mm")
        if ovary.get("follicles"):
            parts.append(f"{label}{ovary['follicles']}")
        for cyst in ovary.get("cysts") or []:
            loc = cyst.get("location") or label
            size_mm = cyst.get("size_mm")
            parts.append(f"{loc}可见约{size_mm}mm囊性包块")
        solid = ovary.get("solid_mass")
        if isinstance(solid, dict) and solid.get("size_mm"):
            parts.append(f"{label}可见约{solid['size_mm']}mm实性占位")
        if parts:
            sections.append(_join(parts))

    adnexa = data.get("adnexa") or {}
    if adnexa.get("description"):
        sections.append(adnexa["description"] + ("。" if not adnexa["description"].endswith("。") else ""))

    return {
        "findings_text": "\n".join(sections),
        "impression_text": _impression(data, template),
    }


def generate_cardiac_report(data: dict) -> dict[str, str]:
    template = load_template("cardiac_ultrasound")
    sections: list[str] = []

    lv = data.get("lv") or {}
    if lv:
        parts: list[str] = []
        if lv.get("internal_diameter_mm"):
            parts.append(f"左室内径约{lv['internal_diameter_mm']}mm")
        if lv.get("wall_thickness_mm"):
            parts.append(f"室间隔厚约{lv['wall_thickness_mm']}mm")
        motion_map = {"normal": "室壁运动协调", "reduced": "室壁运动减低", "asymmetric": "室壁运动不对称"}
        if lv.get("wall_motion") in motion_map:
            parts.append(motion_map[lv["wall_motion"]])
        if lv.get("wall_motion_description"):
            parts.append(lv["wall_motion_description"])
        if lv.get("ef_percent"):
            parts.append(f"估测EF约{lv['ef_percent']}%")
        if parts:
            sections.append(_join(parts))

    rv = data.get("rv") or {}
    if rv.get("internal_diameter_mm"):
        sections.append(f"右室内径约{rv['internal_diameter_mm']}mm。")

    atria = data.get("atria") or {}
    if atria.get("left_atrium_mm"):
        sections.append(f"左房内径约{atria['left_atrium_mm']}mm。")
    if atria.get("right_atrium_description"):
        sections.append(f"右房{atria['right_atrium_description']}。")

    valves = data.get("valves") or {}
    valve_parts: list[str] = []
    for key, label in [
        ("mitral", "二尖瓣"),
        ("aortic", "主动脉瓣"),
        ("tricuspid", "三尖瓣"),
        ("pulmonary", "肺动脉瓣"),
    ]:
        if valves.get(key):
            valve_parts.append(f"{label}{valves[key]}")
    if valve_parts:
        sections.append(_join(valve_parts))

    pericardium = data.get("pericardium") or {}
    if pericardium.get("description"):
        sections.append(f"心包{pericardium['description']}。")

    return {
        "findings_text": "\n".join(sections),
        "impression_text": _impression(data, template),
    }


def generate_vascular_report(data: dict) -> dict[str, str]:
    template = load_template("vascular_ultrasound")
    sections: list[str] = []

    for side, label in [("carotid_right", "右侧颈动脉"), ("carotid_left", "左侧颈动脉")]:
        carotid = data.get(side) or {}
        if not carotid:
            continue
        parts: list[str] = []
        if carotid.get("imt_mm"):
            parts.append(f"{label}内膜厚约{carotid['imt_mm']}mm")
        if carotid.get("description"):
            parts.append(carotid["description"])
        for plaque in carotid.get("plaques") or []:
            loc = plaque.get("location") or label
            size = plaque.get("size_mm")
            surface = "表面尚光滑" if plaque.get("surface") == "smooth" else ""
            parts.append(f"{loc}可见约{size}mm斑块，{surface}".rstrip("，"))
        if carotid.get("stenosis_percent") is not None:
            pct = carotid["stenosis_percent"]
            if pct > 0:
                parts.append(f"管腔狭窄约{pct}%")
            else:
                parts.append("管腔未见明显狭窄")
        if parts:
            sections.append(_join(parts))

    vertebral = data.get("vertebral") or {}
    if vertebral.get("description"):
        sections.append(f"椎动脉{vertebral['description']}。")

    lower = data.get("lower_limb") or {}
    if lower.get("description"):
        sections.append(lower["description"] + ("。" if not lower["description"].endswith("。") else ""))

    return {
        "findings_text": "\n".join(sections),
        "impression_text": _impression(data, template),
    }


def _render_ln_nodes(nodes: list, region_label: str) -> list[str]:
    if not nodes:
        return [f"{region_label}未见明显肿大淋巴结。"]
    lines: list[str] = []
    for node in nodes:
        loc = node.get("location") or region_label
        size = node.get("size_mm")
        parts = [f"{loc}可见约{size}mm淋巴结"]
        shape_map = {"oval": "形态椭圆", "round": "形态圆", "irregular": "形态不规则"}
        if node.get("shape") in shape_map:
            parts.append(shape_map[node["shape"]])
        boundary = BOUNDARY_MAP.get(node.get("boundary") or "", "")
        if boundary:
            parts.append(boundary)
        hilum_map = {"present": "淋巴门可见", "absent": "淋巴门未见", "compressed": "淋巴门受压"}
        if node.get("hilum") in hilum_map:
            parts.append(hilum_map[node["hilum"]])
        if node.get("blood_flow"):
            parts.append(f"血流信号{node['blood_flow']}")
        lines.append(_join(parts).rstrip("。"))
    return lines


def generate_superficial_ln_report(data: dict) -> dict[str, str]:
    template = load_template("superficial_ln_ultrasound")
    sections: list[str] = []

    cervical = data.get("cervical")
    if cervical is not None:
        sections.extend(_render_ln_nodes(cervical, "颈部"))

    axillary = data.get("axillary")
    if axillary is not None:
        sections.extend(_render_ln_nodes(axillary, "腋窝"))

    other = data.get("other")
    if other is not None:
        sections.extend(_render_ln_nodes(other, "浅表"))

    if not sections and data.get("organs_examined"):
        sections.append("浅表淋巴结未见明显肿大。")

    return {
        "findings_text": "\n".join(sections),
        "impression_text": _impression(data, template),
    }


GENERATORS: dict[str, Any] = {
    "thyroid_ultrasound": generate_thyroid_report,
    "breast_ultrasound": generate_breast_report,
    "gynecology_ultrasound": generate_gynecology_report,
    "cardiac_ultrasound": generate_cardiac_report,
    "vascular_ultrasound": generate_vascular_report,
    "superficial_ln_ultrasound": generate_superficial_ln_report,
}
