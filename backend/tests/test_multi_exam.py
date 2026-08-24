"""多检查类型报告生成测试。"""
from backend.app.services.data_loader import get_gold_sample
from backend.app.services.exam_registry import list_exam_types
from backend.app.services.report_generator import generate_report


def test_exam_types_registry():
    types = list_exam_types()
    ids = {t["id"] for t in types}
    assert "abdominal_ultrasound" in ids
    assert "thyroid_ultrasound" in ids
    assert "breast_ultrasound" in ids
    assert len(types) >= 7


def test_thyroid_report():
    sample = get_gold_sample("thy-002")
    assert sample is not None
    report = generate_report(sample["structured"])
    assert "低回声" in report["findings_text"] or "8" in report["findings_text"]
    assert "甲状腺" in report["impression_text"]


def test_breast_report():
    sample = get_gold_sample("bre-002")
    report = generate_report(sample["structured"])
    assert "乳腺" in report["findings_text"] or "12" in report["findings_text"]


def test_cardiac_report():
    sample = get_gold_sample("car-002")
    report = generate_report(sample["structured"])
    assert "左室" in report["findings_text"]
    assert "反流" in report["impression_text"] or "左室" in report["impression_text"]


def test_superficial_ln_report():
    sample = get_gold_sample("ln-002")
    report = generate_report(sample["structured"])
    assert "淋巴结" in report["findings_text"]
    assert "淋巴结" in report["impression_text"]
