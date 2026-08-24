"""端到端链路测试（不依赖 LLM）。"""
from backend.app.services.data_loader import get_gold_sample
from backend.app.services.report_generator import generate_report
from backend.app.services.validation_engine import validate_structured


def test_abd001_report_generation():
    sample = get_gold_sample("abd-001")
    assert sample is not None
    structured = sample["structured"]
    report = generate_report(structured)

    assert "肝实质回声稍增强" in report["findings_text"]
    assert "6mm" in report["findings_text"] or "6mm" in report["findings_text"]
    assert "胆囊息肉样病变" in report["impression_text"]
    assert "肝实质回声稍增强" in report["impression_text"]


def test_abd002_validation_cbd():
    sample = get_gold_sample("abd-002")
    assert sample is not None
    warnings = validate_structured(sample["structured"])
    ids = {w["id"] for w in warnings}
    assert "cbd_dilated" in ids


def test_abd012_no_warnings():
    sample = get_gold_sample("abd-012")
    warnings = validate_structured(sample["structured"])
    critical = [w for w in warnings if w["severity"] in ("error", "warning")]
    assert len(critical) == 0


def test_abd014_uncertainty():
    sample = get_gold_sample("abd-014")
    warnings = validate_structured(sample["structured"])
    ids = {w["id"] for w in warnings}
    assert "uncertainty_highlight" in ids
