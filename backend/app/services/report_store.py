"""报告持久化 — JSON 文件存储 + 修改记录。"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.core.config import DATA_DIR

REPORTS_DIR = DATA_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _report_path(report_id: str) -> Path:
    return REPORTS_DIR / f"{report_id}.json"


def list_reports(limit: int = 50) -> list[dict]:
    items: list[dict] = []
    for f in sorted(REPORTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        with open(f, encoding="utf-8") as fp:
            data = json.load(fp)
        items.append({
            "id": data["id"],
            "status": data.get("status"),
            "exam_part": data.get("exam_part"),
            "patient_name": (data.get("patient") or {}).get("name"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "signed_at": data.get("signed_at"),
        })
        if len(items) >= limit:
            break
    return items


def get_report(report_id: str) -> dict | None:
    path = _report_path(report_id)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_report(payload: dict) -> dict:
    report_id = payload.get("id") or str(uuid.uuid4())
    existing = get_report(report_id)
    now = _now_iso()

    record = {
        "id": report_id,
        "status": payload.get("status") or "draft",
        "exam_type": payload.get("exam_type") or "abdominal_ultrasound",
        "exam_part": payload.get("exam_part") or "腹部超声",
        "report_no": payload.get("report_no"),
        "exam_date": payload.get("exam_date"),
        "device_model": payload.get("device_model"),
        "patient": payload.get("patient") or {},
        "signatures": payload.get("signatures") or {},
        "asr_text": payload.get("asr_text") or "",
        "structured": payload.get("structured") or {},
        "findings_text": payload.get("findings_text") or "",
        "impression_text": payload.get("impression_text") or "",
        "warnings": payload.get("warnings") or [],
        "edit_log": payload.get("edit_log") or (existing or {}).get("edit_log") or [],
        "created_at": (existing or {}).get("created_at") or now,
        "updated_at": now,
        "signed_at": payload.get("signed_at") or (existing or {}).get("signed_at"),
    }

    with open(_report_path(report_id), "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return record


def append_edit(report_id: str, field: str, old_value: str, new_value: str, source: str = "doctor") -> dict | None:
    report = get_report(report_id)
    if not report:
        return None
    log = report.setdefault("edit_log", [])
    log.append({
        "field": field,
        "old_value": old_value,
        "new_value": new_value,
        "source": source,
        "timestamp": _now_iso(),
    })
    report["updated_at"] = _now_iso()
    with open(_report_path(report_id), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report


def sign_report(report_id: str, force: bool = False) -> tuple[dict | None, str | None]:
    report = get_report(report_id)
    if not report:
        return None, "报告不存在"
    if report.get("status") == "signed":
        return report, None

    errors = [w for w in report.get("warnings") or [] if w.get("severity") == "error"]
    if errors and not force:
        return None, "存在 error 级校验项，请确认后再签发"

    report["status"] = "signed"
    report["signed_at"] = _now_iso()
    report["updated_at"] = report["signed_at"]
    with open(_report_path(report_id), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report, None
