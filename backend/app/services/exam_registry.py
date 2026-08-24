"""检查类型注册表。"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from backend.app.core.config import DATA_DIR

DEFAULT_EXAM_TYPE = "abdominal_ultrasound"


@lru_cache
def load_exam_types_registry() -> dict:
    import json

    with open(DATA_DIR / "exam_types.json", encoding="utf-8") as f:
        return json.load(f)


def list_exam_types() -> list[dict[str, str]]:
    items = load_exam_types_registry().get("exam_types", [])
    return [{"id": i["id"], "label": i["label"]} for i in items]


def get_exam_type_meta(exam_type: str) -> dict[str, Any] | None:
    for item in load_exam_types_registry().get("exam_types", []):
        if item["id"] == exam_type:
            return item
    return None


def normalize_exam_type(exam_type: str | None) -> str:
    et = (exam_type or "").strip() or DEFAULT_EXAM_TYPE
    if get_exam_type_meta(et):
        return et
    return DEFAULT_EXAM_TYPE


def exam_label(exam_type: str) -> str:
    meta = get_exam_type_meta(exam_type)
    return meta["label"] if meta else exam_type
