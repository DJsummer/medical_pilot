"""医学术语 — Schema 英文枚举/字段 → 报告中文。"""
from __future__ import annotations

import re

# 解剖部位词素（组合翻译 snake_case）
_WORD_MAP: dict[str, str] = {
    "right": "右",
    "left": "左",
    "lobe": "叶",
    "pole": "极",
    "upper": "上",
    "lower": "下",
    "middle": "中",
    "anterior": "前",
    "posterior": "后",
    "lateral": "外侧",
    "medial": "内侧",
    "kidney": "肾",
    "liver": "肝",
    "gallbladder": "胆囊",
    "spleen": "脾",
    "pancreas": "胰腺",
    "bladder": "膀胱",
    "uterus": "子宫",
    "ovary": "卵巢",
    "breast": "乳腺",
    "thyroid": "甲状腺",
    "isthmus": "峡部",
    "cervical": "颈部",
    "axillary": "腋窝",
    "quadrant": "象限",
    "outer": "外",
    "inner": "内",
    "hilum": "门部",
    "bifurcation": "分叉处",
    "cortex": "皮质",
    "medulla": "髓质",
}

# 完整短语优先匹配
_PHRASE_MAP: dict[str, str] = {
    "right_lobe": "右叶",
    "left_lobe": "左叶",
    "right_kidney": "右肾",
    "left_kidney": "左肾",
    "upper_pole": "上极",
    "lower_pole": "下极",
    "middle_pole": "中下极",
    "outer_upper_quadrant": "外上象限",
    "outer_lower_quadrant": "外下象限",
    "inner_upper_quadrant": "内上象限",
    "inner_lower_quadrant": "内下象限",
}

_ECHO_MAP: dict[str, str] = {
    "anechoic": "无回声",
    "hypoechoic": "低回声",
    "hyperechoic": "强回声",
    "mixed": "混合回声",
    "isoechoic": "等回声",
}

_TYPE_MAP: dict[str, str] = {
    "cyst": "囊性",
    "solid": "实性",
    "calcification": "钙化",
    "hemangioma": "血管瘤",
    "stone": "结石",
    "polyp": "息肉",
    "sludge": "沉积物",
    "fibroid": "肌瘤",
    "other": "占位",
}

_STATUS_MAP: dict[str, str] = {
    "normal": "正常",
    "enlarged": "增大",
    "shrunk": "缩小",
    "thickened": "增厚",
    "dilated": "扩张",
    "clear": "清",
    "unclear": "欠清",
    "smooth": "光滑",
    "rough": "毛糙",
    "irregular": "不规则",
    "mobile": "可移动",
    "immobile": "不移动",
    "present": "可见",
    "absent": "未见",
}


def _has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def humanize_term(value: str | None, *, kind: str = "location") -> str:
    """将 Schema 英文枚举转为中文；已是中文则原样返回。"""
    if not value:
        return ""
    text = str(value).strip()
    if _has_cjk(text):
        return text

    key = text.lower().replace(" ", "_").replace("-", "_")
    if key in _PHRASE_MAP:
        return _PHRASE_MAP[key]

    if kind == "echo" and key in _ECHO_MAP:
        return _ECHO_MAP[key]
    if kind == "type" and key in _TYPE_MAP:
        return _TYPE_MAP[key]
    if kind == "status" and key in _STATUS_MAP:
        return _STATUS_MAP[key]

    if "_" in key:
        parts = key.split("_")
        mapped = [_WORD_MAP.get(p, p) for p in parts]
        if all(p in _WORD_MAP for p in parts):
            return "".join(mapped)

    if key in _WORD_MAP:
        return _WORD_MAP[key]

    return text


def humanize_location(location: str | None, organ_prefix: str = "") -> str:
    """部位 → 中文，可选器官前缀（如肝、肾）。"""
    loc = humanize_term(location, kind="location")
    if not loc:
        return organ_prefix or ""
    if organ_prefix and organ_prefix not in loc and "肝" not in loc and "肾" not in loc:
        return f"{organ_prefix}{loc}"
    return loc
