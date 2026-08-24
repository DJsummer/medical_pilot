"""Gold Dataset 报告生成回归测试。"""
from __future__ import annotations

import re

from backend.app.services.data_loader import load_gold_dataset
from backend.app.services.report_generator import generate_report


def _phrases(text: str) -> list[str]:
    text = text.replace("\n", "。")
    parts = re.split(r"[。；]", text)
    return [p.strip() for p in parts if len(p.strip()) >= 4]


def phrase_coverage(expected: str, actual: str) -> float:
    phrases = _phrases(expected)
    if not phrases:
        return 1.0
    hit = 0
    for p in phrases:
        if p in actual:
            hit += 1
        elif len(p) > 6 and (p[2:] in actual or p[:-2] in actual):
            hit += 0.5
    return hit / len(phrases)


def test_all_gold_samples_generate():
    ds = load_gold_dataset()
    for sample in ds.get("samples", []):
        report = generate_report(sample["structured"])
        assert report["findings_text"]
        hints = sample["structured"].get("impression_hints") or []
        if hints:
            assert any(h.replace("。", "") in report["impression_text"] for h in hints)


def test_gold_average_coverage():
    ds = load_gold_dataset()
    f_covs, i_covs = [], []
    for sample in ds.get("samples", []):
        report = generate_report(sample["structured"])
        ef = sample.get("expected_findings") or ""
        ei = sample.get("expected_impression") or ""
        if ef:
            f_covs.append(phrase_coverage(ef, report["findings_text"]))
        if ei:
            i_covs.append(phrase_coverage(ei, report["impression_text"]))
    avg_f = sum(f_covs) / len(f_covs) if f_covs else 1.0
    avg_i = sum(i_covs) / len(i_covs) if i_covs else 1.0
    assert avg_f >= 0.35, f"平均 findings 覆盖 {avg_f:.0%} < 35%"
    assert avg_i >= 0.35, f"平均 impression 覆盖 {avg_i:.0%} < 35%"


def test_abd001_strict():
    sample = next(s for s in load_gold_dataset()["samples"] if s["id"] == "abd-001")
    report = generate_report(sample["structured"])
    assert "6mm" in report["findings_text"]
    assert "胆囊息肉样病变" in report["impression_text"]
