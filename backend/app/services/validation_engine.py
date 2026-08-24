"""校验规则引擎 — 数值异常、矛盾检测（多检查类型）。"""
from __future__ import annotations

import re
from typing import Any

from backend.app.services.exam_registry import normalize_exam_type


def _get_nested(data: dict, path: str) -> Any:
    parts = path.split(".")
    cur: Any = data
    for p in parts:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    return cur


def _humanize_field_path(path: str) -> str:
    """校验提示中的字段路径 → 简短中文。"""
    labels = {
        "liver": "肝脏",
        "gallbladder": "胆囊",
        "pancreas": "胰腺",
        "spleen": "脾脏",
        "kidneys": "双肾",
        "lesions": "病灶",
        "size": "大小",
        "morphology": "形态",
        "capsule": "包膜",
        "parenchyma_echo": "实质回声",
        "wall": "壁",
        "cavity": "腔内",
        "visibility": "显示",
        "echo": "回声",
        "duct_mm": "胰管",
        "type": "类型",
        "size_mm": "大小",
    }
    parts = re.split(r"\.|\[|\]", path)
    parts = [p for p in parts if p and not p.isdigit()]
    return ".".join(labels.get(p, p) for p in parts)


def _validate_uncertainty(data: dict) -> list[dict]:
    warnings: list[dict] = []
    uncertain = _get_nested(data, "metadata.uncertain_fields")
    if isinstance(uncertain, list) and len(uncertain) > 0:
        display = ", ".join(_humanize_field_path(p) for p in uncertain)
        warnings.append({
            "id": "uncertainty_highlight",
            "severity": "warning",
            "field": "metadata.uncertain_fields",
            "message": f"存在不确定字段，请医生确认：{display}",
            "fields": uncertain,
        })
    return warnings


def _validate_abdominal(data: dict) -> list[dict]:
    warnings: list[dict] = []

    cbd = _get_nested(data, "bile_duct.common_bile_duct_mm")
    if isinstance(cbd, (int, float)):
        if cbd > 10:
            warnings.append({
                "id": "cbd_critical",
                "severity": "error",
                "field": "bile_duct.common_bile_duct_mm",
                "message": f"胆总管内径 {cbd}mm 明显扩张，请核实",
                "value": cbd,
            })
        elif cbd > 6:
            warnings.append({
                "id": "cbd_dilated",
                "severity": "warning",
                "field": "bile_duct.common_bile_duct_mm",
                "message": f"胆总管内径 {cbd}mm，超过正常参考值（≤6mm），请确认",
                "value": cbd,
            })

    gb_wall = _get_nested(data, "gallbladder.wall.thickness_mm")
    if isinstance(gb_wall, (int, float)) and gb_wall > 3:
        warnings.append({
            "id": "gallbladder_wall_thick",
            "severity": "warning",
            "field": "gallbladder.wall.thickness_mm",
            "message": f"胆囊壁厚 {gb_wall}mm，超过正常（≤3mm），请确认",
            "value": gb_wall,
        })

    lesions = _get_nested(data, "gallbladder.lesions")
    if isinstance(lesions, list):
        for i, lesion in enumerate(lesions):
            if not isinstance(lesion, dict):
                continue
            if lesion.get("type") == "stone" and lesion.get("acoustic_shadow") is False:
                warnings.append({
                    "id": "gallbladder_stone_no_shadow",
                    "severity": "warning",
                    "field": f"gallbladder.lesions[{i}]",
                    "message": "胆囊结石通常伴声影，当前标注无声影，请确认",
                })
            if lesion.get("type") == "polyp" and lesion.get("mobility") == "mobile":
                warnings.append({
                    "id": "gallbladder_polyp_mobile",
                    "severity": "warning",
                    "field": f"gallbladder.lesions[{i}]",
                    "message": "息肉样病变通常不移动，当前标注可移动，请确认是否为结石",
                })

    kidneys = data.get("kidneys") or {}
    left_len = _get_nested(kidneys, "left.size.length_mm")
    right_len = _get_nested(kidneys, "right.size.length_mm")
    if isinstance(left_len, (int, float)):
        if left_len < 90 or left_len > 120:
            warnings.append({
                "id": "kidney_left_size",
                "severity": "info",
                "field": "kidneys.left.size.length_mm",
                "message": f"左肾长径 {left_len}mm，参考范围 90-120mm",
                "value": left_len,
            })
    if isinstance(right_len, (int, float)):
        if right_len < 90 or right_len > 120:
            warnings.append({
                "id": "kidney_right_size",
                "severity": "info",
                "field": "kidneys.right.size.length_mm",
                "message": f"右肾长径 {right_len}mm，参考范围 90-120mm",
                "value": right_len,
            })
    if isinstance(left_len, (int, float)) and isinstance(right_len, (int, float)):
        if abs(left_len - right_len) > 15:
            warnings.append({
                "id": "kidney_size_symmetry",
                "severity": "warning",
                "field": "kidneys",
                "message": "双肾长径差异超过 15mm，请确认",
            })

    spleen_thick = _get_nested(data, "spleen.size.thickness_mm")
    if isinstance(spleen_thick, (int, float)) and spleen_thick > 40:
        warnings.append({
            "id": "spleen_enlarged",
            "severity": "warning",
            "field": "spleen.size.thickness_mm",
            "message": f"脾脏厚径 {spleen_thick}mm，超过正常（≤40mm）",
            "value": spleen_thick,
        })

    liver_status = _get_nested(data, "liver.size.status")
    if liver_status == "enlarged":
        warnings.append({
            "id": "liver_enlarged",
            "severity": "info",
            "field": "liver.size.status",
            "message": "肝脏增大，请确认描述是否完整",
        })

    duct_mm = _get_nested(data, "pancreas.duct_mm")
    if isinstance(duct_mm, (int, float)) and duct_mm > 2:
        warnings.append({
            "id": "pancreas_duct_dilated",
            "severity": "warning",
            "field": "pancreas.duct_mm",
            "message": f"主胰管内径 {duct_mm}mm，超过正常（≤2mm）",
            "value": duct_mm,
        })

    return warnings


def _validate_thyroid(data: dict) -> list[dict]:
    warnings: list[dict] = []
    for side in ("thyroid_right", "thyroid_left"):
        for i, nodule in enumerate((data.get(side) or {}).get("nodules") or []):
            size = nodule.get("size_mm")
            if isinstance(size, (int, float)) and size > 10:
                warnings.append({
                    "id": "thyroid_nodule_large",
                    "severity": "info",
                    "field": f"{side}.nodules[{i}]",
                    "message": f"甲状腺结节约 {size}mm，建议关注大小变化",
                    "value": size,
                })
    return warnings


def _validate_cardiac(data: dict) -> list[dict]:
    warnings: list[dict] = []
    lv = data.get("lv") or {}
    if isinstance(lv.get("internal_diameter_mm"), (int, float)) and lv["internal_diameter_mm"] > 55:
        warnings.append({
            "id": "lv_dilated",
            "severity": "warning",
            "field": "lv.internal_diameter_mm",
            "message": f"左室内径 {lv['internal_diameter_mm']}mm，提示左室扩大",
            "value": lv["internal_diameter_mm"],
        })
    if isinstance(lv.get("ef_percent"), (int, float)) and lv["ef_percent"] < 50:
        warnings.append({
            "id": "lv_ef_low",
            "severity": "warning",
            "field": "lv.ef_percent",
            "message": f"估测 EF {lv['ef_percent']}%，请确认心功能描述",
            "value": lv["ef_percent"],
        })
    return warnings


def _validate_vascular(data: dict) -> list[dict]:
    warnings: list[dict] = []
    for side in ("carotid_right", "carotid_left"):
        carotid = data.get(side) or {}
        stenosis = carotid.get("stenosis_percent")
        if isinstance(stenosis, (int, float)) and stenosis >= 50:
            warnings.append({
                "id": "carotid_stenosis",
                "severity": "error",
                "field": f"{side}.stenosis_percent",
                "message": f"颈动脉狭窄约 {stenosis}%，请核实",
                "value": stenosis,
            })
        imt = carotid.get("imt_mm")
        if isinstance(imt, (int, float)) and imt > 1.0:
            warnings.append({
                "id": "carotid_imt_thick",
                "severity": "info",
                "field": f"{side}.imt_mm",
                "message": f"颈动脉内膜厚 {imt}mm，超过参考值",
                "value": imt,
            })
    return warnings


def _validate_superficial_ln(data: dict) -> list[dict]:
    warnings: list[dict] = []
    for region in ("cervical", "axillary", "other"):
        for i, node in enumerate(data.get(region) or []):
            size = node.get("size_mm")
            if isinstance(size, (int, float)) and size > 15:
                warnings.append({
                    "id": "ln_enlarged",
                    "severity": "warning",
                    "field": f"{region}[{i}]",
                    "message": f"淋巴结长约 {size}mm，请确认形态及淋巴门",
                    "value": size,
                })
            if node.get("hilum") == "absent":
                warnings.append({
                    "id": "ln_hilum_absent",
                    "severity": "info",
                    "field": f"{region}[{i}]",
                    "message": "淋巴结淋巴门未见，请结合临床",
                })
    return warnings


_TYPE_VALIDATORS = {
    "abdominal_ultrasound": _validate_abdominal,
    "thyroid_ultrasound": _validate_thyroid,
    "cardiac_ultrasound": _validate_cardiac,
    "vascular_ultrasound": _validate_vascular,
    "superficial_ln_ultrasound": _validate_superficial_ln,
}


def validate_structured(data: dict) -> list[dict]:
    exam_type = normalize_exam_type(data.get("exam_type"))
    warnings = _validate_uncertainty(data)
    validator = _TYPE_VALIDATORS.get(exam_type)
    if validator:
        warnings.extend(validator(data))
    return warnings
