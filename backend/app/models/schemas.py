"""Pydantic 请求/响应模型。"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class StructureRequest(BaseModel):
    asr_text: str = Field(..., description="ASR 原始文本或医生口述")
    few_shot_count: int = Field(2, ge=0, le=5)
    exam_type: Optional[str] = Field("abdominal_ultrasound", description="检查类型 ID")


class StructureFromGoldRequest(BaseModel):
    sample_id: str = Field("abd-001", description="Gold Dataset 样本 ID")


class GenerateReportRequest(BaseModel):
    structured: dict[str, Any]


class PipelineRequest(BaseModel):
    asr_text: str = ""
    sample_id: Optional[str] = None
    few_shot_count: int = 2
    use_llm: bool = True
    exam_type: Optional[str] = Field("abdominal_ultrasound", description="检查类型 ID")


class WarningItem(BaseModel):
    id: str
    severity: str
    field: str
    message: str
    value: Optional[Any] = None
    fields: Optional[list[str]] = None


class ReportResult(BaseModel):
    findings_text: str
    impression_text: str
    warnings: list[WarningItem] = []


class StructureResult(BaseModel):
    ok: bool
    structured: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    usage: Optional[dict[str, int]] = None


class PipelineResult(BaseModel):
    asr_text: str
    structured: dict[str, Any]
    findings_text: str
    impression_text: str
    warnings: list[WarningItem]
    llm_used: bool
    error: Optional[str] = None


class PatientInfo(BaseModel):
    name: Optional[str] = None
    sex: Optional[str] = None
    age: Optional[str] = None
    outpatient_no: Optional[str] = None
    inpatient_no: Optional[str] = None
    bed_no: Optional[str] = None
    dept: Optional[str] = None


class Signatures(BaseModel):
    examiner: Optional[str] = None
    recorder: Optional[str] = None
    reviewer: Optional[str] = None


class ReportSaveRequest(BaseModel):
    id: Optional[str] = None
    exam_type: Optional[str] = "abdominal_ultrasound"
    exam_part: Optional[str] = "腹部超声"
    report_no: Optional[str] = None
    exam_date: Optional[str] = None
    device_model: Optional[str] = None
    patient: Optional[PatientInfo] = None
    signatures: Optional[Signatures] = None
    asr_text: Optional[str] = ""
    structured: dict[str, Any] = {}
    findings_text: Optional[str] = ""
    impression_text: Optional[str] = ""
    warnings: list[WarningItem] = []
    edit_log: list[dict[str, Any]] = []


class ReportSignRequest(BaseModel):
    force: bool = False


class EditRecordRequest(BaseModel):
    field: str
    old_value: str = ""
    new_value: str = ""
    source: str = "doctor"
