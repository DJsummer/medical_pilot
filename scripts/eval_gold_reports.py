#!/usr/bin/env python3
"""评估 Gold Dataset 报告生成质量。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.tests.test_gold_regression import phrase_coverage
from backend.app.services.data_loader import load_gold_dataset
from backend.app.services.report_generator import generate_report


def main():
    ds = load_gold_dataset()
    print("Gold Dataset 报告生成评估")
    print("=" * 72)
    f_covs, i_covs = [], []

    for sample in ds.get("samples", []):
        report = generate_report(sample["structured"])
        ef = sample.get("expected_findings") or ""
        ei = sample.get("expected_impression") or ""
        fc = phrase_coverage(ef, report["findings_text"]) if ef else 1.0
        ic = phrase_coverage(ei, report["impression_text"]) if ei else 1.0
        f_covs.append(fc)
        i_covs.append(ic)
        mark = "✓" if fc >= 0.65 and ic >= 0.6 else "✗"
        print(f"{mark} {sample['id']}  findings={fc:.0%}  impression={ic:.0%}")

    print("=" * 72)
    print(f"平均 findings 覆盖: {sum(f_covs)/len(f_covs):.0%}")
    print(f"平均 impression 覆盖: {sum(i_covs)/len(i_covs):.0%}")


if __name__ == "__main__":
    main()
