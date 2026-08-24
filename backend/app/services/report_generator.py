"""规则模板引擎 — 结构化 JSON → 超声所见 + 超声提示。"""
from __future__ import annotations

from backend.app.services.term_mapper import humanize_location, humanize_term

ECHO_MAP = {
    "anechoic": "无回声",
    "hypoechoic": "低回声",
    "hyperechoic": "强回声",
    "mixed": "混合回声",
    "isoechoic": "等回声",
}

BOUNDARY_MAP = {"clear": "边界清", "unclear": "边界欠清"}
MOBILITY_MAP = {
    "mobile": "改变体位可移动",
    "immobile": "改变体位不移动",
    "not_tested": "未探及移动",
}


def _shadow_desc(val: bool | None) -> str:
    if val is True:
        return "后方伴声影"
    if val is False:
        return "后方未见明显声影"
    return ""


def _posterior_desc(enhancement: bool | None) -> str:
    if enhancement:
        return "后方回声增强"
    return ""


def _join_parts(parts: list[str]) -> str:
    parts = [p.strip() for p in parts if p and p.strip()]
    if not parts:
        return ""
    text = "，".join(parts)
    if not text.endswith("。"):
        text += "。"
    return text


def _is_collecting_separation(cs: str) -> bool:
    if not cs:
        return False
    if cs in ("未见分离", "无分离") or cs.endswith("未见分离"):
        return False
    return "分离" in cs


def _render_liver(liver: dict) -> str:
    parts: list[str] = []
    has_lesions = bool(liver.get("lesions"))
    size = liver.get("size") or {}
    if size.get("status") == "enlarged":
        parts.append("肝脏增大")
    elif size.get("status") == "shrunk":
        parts.append("肝脏缩小")
    elif not has_lesions and (not liver.get("parenchyma_echo") or liver.get("parenchyma_echo") == "normal"):
        parts.append("肝脏大小、形态正常")

    if liver.get("morphology") == "abnormal":
        desc = liver.get("morphology_description") or "形态异常"
        parts.append(desc)

    capsule = liver.get("capsule")
    if capsule == "smooth":
        parts.append("包膜光滑")
    elif capsule in ("rough", "irregular"):
        parts.append("包膜毛糙")

    echo = liver.get("parenchyma_echo")
    echo_map = {
        "normal": "肝实质回声均匀",
        "increased": "肝实质回声稍增强",
        "decreased": "肝实质回声减低",
        "heterogeneous": "肝实质回声不均匀",
    }
    if echo in echo_map:
        parts.append(echo_map[echo])
    if liver.get("parenchyma_description"):
        parts.append(liver["parenchyma_description"])

    vessels = liver.get("vessels") or {}
    if vessels.get("portal_vein"):
        parts.append(f"门静脉{vessels['portal_vein']}")
    if vessels.get("hepatic_veins"):
        parts.append(f"肝静脉{vessels['hepatic_veins']}")

    for lesion in liver.get("lesions") or []:
        loc = humanize_location(lesion.get("location"), "肝")
        if loc and "肝" not in loc:
            loc = f"肝脏{loc}"
        elif not loc:
            loc = "肝脏"
        size_mm = lesion.get("size_mm")
        echo_desc = ECHO_MAP.get(lesion.get("echo") or "", "") or humanize_term(
            lesion.get("echo"), kind="echo"
        )
        boundary = BOUNDARY_MAP.get(lesion.get("boundary") or "", "") or (
            f"边界{humanize_term(lesion.get('boundary'), kind='status')}"
            if lesion.get("boundary") else ""
        )
        posterior = _posterior_desc(lesion.get("posterior_enhancement"))
        ltype = lesion.get("type")
        if ltype == "cyst":
            parts.append(_join_parts([
                f"{loc}可见约{size_mm}mm无回声",
                boundary,
                posterior,
            ]).rstrip("。"))
        elif ltype == "hemangioma":
            parts.append(_join_parts([
                f"{loc}可见约{size_mm}mm高回声团",
                boundary,
            ]).rstrip("。"))
        else:
            parts.append(_join_parts([
                f"{loc}可见约{size_mm}mm{echo_desc}结节",
                boundary,
                posterior,
            ]).rstrip("。"))

    return _join_parts(parts)


def _render_gallbladder(gb: dict) -> str:
    parts: list[str] = []
    size = gb.get("size") or {}
    wall = gb.get("wall") or {}
    cavity = gb.get("cavity") or {}
    only_lesions = (
        gb.get("lesions")
        and not gb.get("size")
        and not gb.get("wall")
        and not cavity.get("description")
    )

    if not only_lesions:
        if size.get("status") == "enlarged":
            parts.append("胆囊增大")
        elif size.get("status") == "shrunk":
            parts.append("胆囊缩小")
        else:
            parts.append("胆囊大小正常")

        if wall.get("status") == "thickened":
            thick = wall.get("thickness_mm")
            desc = wall.get("description")
            if desc and thick:
                parts.append(f"壁{desc}，厚约{thick}mm")
            elif thick:
                parts.append(f"壁增厚约{thick}mm")
            else:
                parts.append("壁增厚")
        elif wall.get("status") == "normal" or not wall.get("status"):
            parts.append("壁不厚")

    if cavity.get("description"):
        desc = cavity["description"]
        if not desc.startswith("腔内"):
            desc = f"腔内{desc}"
        parts.append(desc)

    for lesion in gb.get("lesions") or []:
        size_mm = lesion.get("size_mm")
        shadow = _shadow_desc(lesion.get("acoustic_shadow"))
        mobility = MOBILITY_MAP.get(lesion.get("mobility") or "", "")
        count = lesion.get("count")
        ltype = lesion.get("type")
        gb_prefix = "胆囊" if not parts and not wall and not cavity.get("description") else "腔内"
        if count == "multiple" and ltype == "stone":
            parts.append(_join_parts([
                f"{gb_prefix}可见多个强回声，最大约{size_mm}mm",
                shadow,
                mobility,
            ]).rstrip("。"))
        else:
            parts.append(_join_parts([
                f"{gb_prefix}可见约{size_mm}mm强回声",
                shadow,
                mobility,
            ]).rstrip("。"))

    return _join_parts(parts)


def _render_bile_duct(bd: dict) -> str:
    parts: list[str] = []
    if bd.get("hepatic_duct"):
        parts.append(f"肝内胆管{bd['hepatic_duct']}")
    elif bd.get("common_bile_duct_status") == "normal":
        parts.append("肝内外胆管未见扩张")

    if bd.get("common_bile_duct_mm") is not None:
        parts.append(f"胆总管内径约{bd['common_bile_duct_mm']}mm")
    if bd.get("description"):
        parts.append(bd["description"])
    return _join_parts(parts)


def _render_pancreas(p: dict) -> str:
    if p.get("visibility") == "obscured":
        return "胰腺显示不清。"

    parts: list[str] = []
    if p.get("size") == "enlarged":
        parts.append("胰腺增大")
    elif p.get("size") == "atrophic":
        parts.append("胰腺萎缩")
    else:
        parts.append("胰腺大小形态正常")

    echo_map = {
        "normal": "回声均匀",
        "increased": "回声增强",
        "decreased": "回声减低",
        "heterogeneous": "回声不均匀",
    }
    if p.get("echo") in echo_map:
        parts.append(echo_map[p["echo"]])
    if p.get("parenchyma_description"):
        parts.append(p["parenchyma_description"])

    duct = p.get("duct_mm")
    if duct is not None and duct > 0:
        parts.append(f"主胰管内径约{duct}mm")
    else:
        parts.append("主胰管未见扩张")

    return _join_parts(parts)


def _render_spleen(s: dict) -> str:
    parts: list[str] = []
    size = s.get("size") or {}
    if size.get("status") == "enlarged" or (size.get("thickness_mm") and size.get("thickness_mm") > 40):
        thick = size.get("thickness_mm")
        parts.append(f"脾脏厚径约{thick}mm" if thick else "脾脏增大")
    else:
        parts.append("脾脏大小正常")

    echo_map = {"normal": "回声均匀", "increased": "回声增强", "decreased": "回声减低"}
    echo = s.get("echo")
    if echo in echo_map:
        parts.append(echo_map[echo])
    return _join_parts(parts)


def _render_kidney(side: str, k: dict) -> str:
    parts: list[str] = []
    label = "左肾" if side == "left" else "右肾"
    size = k.get("size") or {}
    if size.get("length_mm"):
        parts.append(f"{label}长径约{size['length_mm']}mm")
    if k.get("morphology") == "normal":
        parts.append(f"{label}形态正常")
    if k.get("cortex_echo") == "normal":
        parts.append("皮髓质分界清")
    if k.get("collecting_system"):
        cs = k["collecting_system"]
        if "分离" in cs:
            parts.append(f"{label}集合系统{cs}")
        else:
            parts.append(f"集合系统{cs}")

    for lesion in k.get("lesions") or []:
        loc = humanize_location(lesion.get("location"))
        size_mm = lesion.get("size_mm")
        ltype = lesion.get("type")
        if ltype == "cyst":
            parts.append(_join_parts([
                f"{label}{loc}可见约{size_mm}mm无回声",
                BOUNDARY_MAP.get(lesion.get("boundary") or "", ""),
                _posterior_desc(lesion.get("posterior_enhancement")),
            ]).rstrip("。"))
        elif ltype == "stone":
            parts.append(_join_parts([
                f"{label}{loc}可见强回声约{size_mm}mm",
                _shadow_desc(lesion.get("acoustic_shadow")),
            ]).rstrip("。"))

    if not parts and k.get("morphology") == "normal":
        return f"{label}未见明显异常。"
    return _join_parts(parts)


def _render_kidneys(kidneys: dict) -> str:
    left = kidneys.get("left") or {}
    right = kidneys.get("right") or {}

    left_len = (left.get("size") or {}).get("length_mm")
    right_len = (right.get("size") or {}).get("length_mm")
    both_have_len = left_len and right_len
    both_morph_normal = left.get("morphology") == "normal" and right.get("morphology") == "normal"
    both_no_lesions = not left.get("lesions") and not right.get("lesions")
    left_cs = left.get("collecting_system") or ""
    right_cs = right.get("collecting_system") or ""
    same_cs = left_cs and left_cs == right_cs

    if both_have_len and both_morph_normal and both_no_lesions and same_cs and not _is_collecting_separation(left_cs):
        parts = [f"左肾长径约{left_len}mm", f"右肾长径约{right_len}mm", "双肾形态正常", "皮髓质分界清"]
        if left_cs:
            parts.append(f"集合系统{left_cs}")
        return _join_parts(parts)

    both_normal = (
        left and left.get("morphology") == "normal" and not left.get("lesions")
        and right and right.get("morphology") == "normal" and not right.get("lesions")
        and not left_len and not right_len
    )
    if both_normal and not left_cs and not right_cs:
        return "双肾大小形态正常，皮髓质分界清，集合系统未见分离。"

    sections: list[str] = []
    if left:
        sections.append(_render_kidney("left", left))
    if right:
        sections.append(_render_kidney("right", right))
    return "\n".join(s for s in sections if s)


def _has_lesions(data: dict) -> bool:
    for key in ("liver", "gallbladder", "pancreas", "spleen", "bladder"):
        organ = data.get(key) or {}
        if organ.get("lesions"):
            return True
    kidneys = data.get("kidneys") or {}
    for side in ("left", "right"):
        if (kidneys.get(side) or {}).get("lesions"):
            return True
    return False


def _default_impression(data: dict, sections: list[str]) -> str:
    hints = data.get("impression_hints") or []
    if hints:
        return "\n".join(h + ("。" if not h.endswith("。") else "") for h in hints)

    organs = data.get("organs_examined") or []
    if not sections:
        return "腹部超声未见明显异常。"

    if data.get("pancreas", {}).get("visibility") == "obscured" and len(organs) <= 1:
        return "胰腺显示不清。"

    kidney_only = set(organs) <= {"kidney_left", "kidney_right"} and not _has_lesions(data)
    if kidney_only and not hints:
        return "双肾未见明显异常。"

    bladder_only = organs == ["bladder"] and not _has_lesions(data)
    if bladder_only:
        return "膀胱未见明显异常。"

    gb_only = set(organs) <= {"gallbladder", "bile_duct"} and not _has_lesions(data)
    if gb_only and not hints:
        return "胆管及胆囊未见明显异常。"

    if not _has_lesions(data) and not hints and len(organs) >= 3:
        return "腹部超声未见明显异常。"

    return ""


def _render_bladder(b: dict) -> str:
    parts: list[str] = []
    filling_map = {"good": "膀胱充盈尚可", "poor": "膀胱充盈欠佳", "empty": "膀胱空虚"}
    if b.get("filling") in filling_map:
        parts.append(filling_map[b["filling"]])

    if b.get("wall") == "thickened":
        thick = b.get("wall_thickness_mm")
        parts.append(f"壁增厚约{thick}mm" if thick else "壁增厚")
    elif b.get("wall") == "smooth":
        parts.append("壁光滑")

    if b.get("cavity"):
        parts.append(f"腔内{b['cavity']}")
    elif not b.get("lesions"):
        parts.append("腔内未见异常回声")

    return _join_parts(parts)


def _render_free_fluid(ff: dict) -> str:
    if ff.get("present"):
        desc = ff.get("description") or "游离积液"
        return f"腹腔见{desc}。"
    return "腹腔未见游离积液。"


def generate_report(data: dict) -> dict[str, str]:
    """从结构化 JSON 生成超声所见与超声提示。"""
    from backend.app.services.exam_registry import normalize_exam_type
    from backend.app.services.report_extra import GENERATORS

    exam_type = normalize_exam_type(data.get("exam_type"))
    data.setdefault("exam_type", exam_type)
    if exam_type in GENERATORS:
        return GENERATORS[exam_type](data)

    sections: list[str] = []
    organs = data.get("organs_examined") or []

    organ_renderers = {
        "liver": lambda: _render_liver(data.get("liver") or {}),
        "gallbladder": lambda: _render_gallbladder(data.get("gallbladder") or {}),
        "bile_duct": lambda: _render_bile_duct(data.get("bile_duct") or {}),
        "pancreas": lambda: _render_pancreas(data.get("pancreas") or {}),
        "spleen": lambda: _render_spleen(data.get("spleen") or {}),
    }

    for organ in ["liver", "gallbladder", "bile_duct", "pancreas", "spleen"]:
        if organ in organs or data.get(organ):
            text = organ_renderers[organ]()
            if text:
                sections.append(text)

    if "kidney_left" in organs or "kidney_right" in organs or data.get("kidneys"):
        kidneys_text = _render_kidneys(data.get("kidneys") or {})
        if kidneys_text:
            sections.append(kidneys_text)

    if "bladder" in organs or data.get("bladder"):
        bladder_text = _render_bladder(data.get("bladder") or {})
        if bladder_text:
            sections.append(bladder_text)

    if data.get("other_findings"):
        sections.append(data["other_findings"] + ("。" if not data["other_findings"].endswith("。") else ""))

    ff = data.get("free_fluid")
    if ff is not None:
        sections.append(_render_free_fluid(ff))

    if "pancreas" in organs and (data.get("pancreas") or {}).get("visibility") == "obscured":
        if len(organs) == 1 and not data.get("other_findings"):
            sections.append("余脏器未见明显异常。")

    findings = "\n".join(sections)
    impression = _default_impression(data, sections)

    return {"findings_text": findings, "impression_text": impression}
