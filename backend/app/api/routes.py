"""API 路由。"""
from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from backend.app.core.config import asr_enabled, llm_enabled
from backend.app.models.schemas import (
    EditRecordRequest,
    GenerateReportRequest,
    PipelineRequest,
    PipelineResult,
    ReportResult,
    ReportSaveRequest,
    ReportSignRequest,
    StructureFromGoldRequest,
    StructureRequest,
    StructureResult,
    WarningItem,
)
from backend.app.services.data_loader import get_gold_sample, list_gold_samples, load_gold_dataset, load_schema
from backend.app.services.exam_registry import list_exam_types, normalize_exam_type
from backend.app.services.report_generator import generate_report
from backend.app.services.report_store import append_edit, get_report, list_reports, save_report, sign_report
from backend.app.services.asr_service import transcribe_audio
from backend.app.services.structure_extractor import extract_structure
from backend.app.services.validation_engine import validate_structured

router = APIRouter(prefix="/api", tags=["ultrasound"])


@router.get("/health")
def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "service": "AI B超报告书写助手",
        "llm_enabled": llm_enabled(),
        "asr_enabled": asr_enabled(),
    }


@router.get("/asr/status")
def asr_status():
    return {
        "server_asr_enabled": asr_enabled(),
        "browser_asr_hint": "Chrome/Edge 支持 Web Speech API 实时听写",
    }


@router.post("/asr/transcribe")
async def asr_transcribe(audio: UploadFile = File(...)):
    content = await audio.read()
    ok, result = transcribe_audio(
        content,
        audio.content_type or "audio/webm",
        audio.filename or "audio.webm",
    )
    if not ok:
        return {"ok": False, "error": result}
    return {"ok": True, "text": result, "bytes": len(content)}


@router.get("/exam-types")
def get_exam_types():
    return {"exam_types": list_exam_types()}


@router.get("/schema/{exam_type}")
def get_schema(exam_type: str):
    et = normalize_exam_type(exam_type)
    return load_schema(et)


@router.get("/schema/abdominal")
def get_abdominal_schema():
    return load_schema("abdominal_ultrasound")


@router.get("/gold-dataset")
def list_gold_dataset(exam_type: str = "abdominal_ultrasound"):
    et = normalize_exam_type(exam_type)
    samples = list_gold_samples(et)
    return {"exam_type": et, "count": len(samples), "samples": samples}


@router.get("/gold-dataset/{sample_id}")
def get_gold_sample_detail(sample_id: str):
    sample = get_gold_sample(sample_id)
    if not sample:
        return {"ok": False, "error": f"样本 {sample_id} 不存在"}
    return {"ok": True, "sample": sample}


@router.post("/structure", response_model=StructureResult)
def structure_text(req: StructureRequest):
    result = extract_structure(
        req.asr_text,
        few_shot_count=req.few_shot_count,
        exam_type=req.exam_type or "abdominal_ultrasound",
    )
    return StructureResult(
        ok=result["ok"],
        structured=result.get("structured"),
        error=result.get("error"),
        usage=result.get("usage"),
    )


@router.post("/structure/from-gold", response_model=StructureResult)
def structure_from_gold(req: StructureFromGoldRequest):
    sample = get_gold_sample(req.sample_id)
    if not sample:
        return StructureResult(ok=False, error=f"样本 {req.sample_id} 不存在")
    return StructureResult(ok=True, structured=sample["structured"])


@router.post("/report/generate", response_model=ReportResult)
def generate_report_endpoint(req: GenerateReportRequest):
    report = generate_report(req.structured)
    warnings = validate_structured(req.structured)
    return ReportResult(
        findings_text=report["findings_text"],
        impression_text=report["impression_text"],
        warnings=[WarningItem(**w) for w in warnings],
    )


@router.post("/pipeline", response_model=PipelineResult)
def run_pipeline(req: PipelineRequest):
    exam_type = normalize_exam_type(req.exam_type)
    asr_text = (req.asr_text or "").strip()
    structured: dict
    llm_used = False
    error = None

    if req.use_llm and llm_enabled():
        if not asr_text:
            return PipelineResult(
                asr_text="",
                structured={},
                findings_text="",
                impression_text="",
                warnings=[],
                llm_used=False,
                error="口述文本为空",
            )
        extract = extract_structure(asr_text, few_shot_count=req.few_shot_count, exam_type=exam_type)
        if not extract["ok"]:
            return PipelineResult(
                asr_text=asr_text,
                structured={},
                findings_text="",
                impression_text="",
                warnings=[],
                llm_used=True,
                error=extract.get("error"),
            )
        structured = extract["structured"]
        llm_used = True
    elif req.sample_id:
        sample = get_gold_sample(req.sample_id, exam_type)
        if not sample:
            sample = get_gold_sample(req.sample_id)
        if not sample:
            return PipelineResult(
                asr_text=asr_text,
                structured={},
                findings_text="",
                impression_text="",
                warnings=[],
                llm_used=False,
                error=f"样本 {req.sample_id} 不存在",
            )
        structured = sample["structured"]
        asr_text = asr_text or sample["asr_text"]
    else:
        matched = None
        if asr_text:
            for s in load_gold_dataset(exam_type).get("samples", []):
                if s.get("asr_text") == asr_text:
                    matched = s
                    break
        if matched:
            structured = matched["structured"]
        else:
            return PipelineResult(
                asr_text=asr_text,
                structured={},
                findings_text="",
                impression_text="",
                warnings=[],
                llm_used=False,
                error="LLM 未启用：请配置 MEDICAL_LLM_API_KEY，或选择 Gold 样本演示",
            )

    report = generate_report(structured)
    warnings = validate_structured(structured)
    return PipelineResult(
        asr_text=asr_text,
        structured=structured,
        findings_text=report["findings_text"],
        impression_text=report["impression_text"],
        warnings=[WarningItem(**w) for w in warnings],
        llm_used=llm_used,
        error=error,
    )


@router.get("/reports")
def reports_list():
    return {"reports": list_reports()}


@router.get("/reports/{report_id}")
def reports_get(report_id: str):
    report = get_report(report_id)
    if not report:
        return {"ok": False, "error": "报告不存在"}
    return {"ok": True, "report": report}


@router.post("/reports")
def reports_save(req: ReportSaveRequest):
    payload = req.model_dump()
    if req.patient:
        payload["patient"] = req.patient.model_dump()
    if req.signatures:
        payload["signatures"] = req.signatures.model_dump()
    payload["warnings"] = [w.model_dump() for w in req.warnings]
    record = save_report(payload)
    return {"ok": True, "report": record}


@router.post("/reports/{report_id}/edits")
def reports_add_edit(report_id: str, req: EditRecordRequest):
    report = append_edit(report_id, req.field, req.old_value, req.new_value, req.source)
    if not report:
        return {"ok": False, "error": "报告不存在"}
    return {"ok": True, "report": report}


@router.post("/reports/{report_id}/sign")
def reports_sign(report_id: str, req: ReportSignRequest):
    report, err = sign_report(report_id, force=req.force)
    if err:
        return {"ok": False, "error": err}
    return {"ok": True, "report": report}
