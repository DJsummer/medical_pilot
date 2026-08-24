"""加载 Schema、Gold Dataset、模板、校验规则（多检查类型）。"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.app.core.config import DATA_DIR
from backend.app.services.exam_registry import DEFAULT_EXAM_TYPE, get_exam_type_meta, normalize_exam_type


def _load_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _meta_paths(exam_type: str) -> dict[str, Path]:
    meta = get_exam_type_meta(exam_type)
    if not meta:
        meta = get_exam_type_meta(DEFAULT_EXAM_TYPE)
    assert meta is not None
    return {
        "schema": DATA_DIR / "schemas" / meta["schema_file"],
        "gold": DATA_DIR / "gold_dataset" / meta["gold_file"],
        "template": DATA_DIR / "templates" / meta["template_file"],
        "rules": DATA_DIR / "validation_rules" / meta["rules_file"],
    }


@lru_cache
def load_schema(exam_type: str = DEFAULT_EXAM_TYPE) -> dict:
    et = normalize_exam_type(exam_type)
    return _load_json(_meta_paths(et)["schema"])


@lru_cache
def load_gold_dataset(exam_type: str = DEFAULT_EXAM_TYPE) -> dict:
    et = normalize_exam_type(exam_type)
    return _load_json(_meta_paths(et)["gold"])


@lru_cache
def load_template(exam_type: str = DEFAULT_EXAM_TYPE) -> dict:
    et = normalize_exam_type(exam_type)
    return _load_json(_meta_paths(et)["template"])


@lru_cache
def load_validation_rules(exam_type: str = DEFAULT_EXAM_TYPE) -> dict:
    et = normalize_exam_type(exam_type)
    return _load_json(_meta_paths(et)["rules"])


def get_few_shot_examples(count: int = 2, exam_type: str = DEFAULT_EXAM_TYPE) -> list[dict]:
    samples = load_gold_dataset(exam_type).get("samples", [])
    return [
        {"asr_text": s["asr_text"], "structured": s["structured"]}
        for s in samples[:count]
    ]


def get_gold_sample(sample_id: str, exam_type: str | None = None) -> dict | None:
    if exam_type:
        for s in load_gold_dataset(exam_type).get("samples", []):
            if s.get("id") == sample_id:
                return s
        return None

    from backend.app.services.exam_registry import load_exam_types_registry

    for item in load_exam_types_registry().get("exam_types", []):
        for s in load_gold_dataset(item["id"]).get("samples", []):
            if s.get("id") == sample_id:
                return s
    return None


def list_gold_samples(exam_type: str = DEFAULT_EXAM_TYPE) -> list[dict]:
    ds = load_gold_dataset(exam_type)
    return [
        {"id": s["id"], "asr_text": s["asr_text"]}
        for s in ds.get("samples", [])
    ]
