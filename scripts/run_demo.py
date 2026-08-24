#!/usr/bin/env python3
"""本地演示：Gold structured → 报告生成 + 校验（无需 LLM）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.services.data_loader import get_gold_sample
from backend.app.services.report_generator import generate_report
from backend.app.services.validation_engine import validate_structured


def main():
    sample_id = sys.argv[1] if len(sys.argv) > 1 else "abd-001"
    sample = get_gold_sample(sample_id)
    if not sample:
        print(f"样本 {sample_id} 不存在")
        sys.exit(1)

    print("=" * 60)
    print(f"样本: {sample_id}")
    print("=" * 60)
    print("\n🎙 医生原话:")
    print(sample["asr_text"])

    structured = sample["structured"]
    print("\n🤖 结构化 JSON (摘要):")
    print(json.dumps(structured, ensure_ascii=False, indent=2)[:800] + "...")

    report = generate_report(structured)
    warnings = validate_structured(structured)

    print("\n📄 超声所见:")
    print(report["findings_text"])
    print("\n📄 超声提示:")
    print(report["impression_text"])

    if warnings:
        print("\n⚠ 校验:")
        for w in warnings:
            print(f"  [{w['severity']}] {w['message']}")

    if sample.get("expected_findings"):
        print("\n✓ 期望所见:")
        print(sample["expected_findings"])


if __name__ == "__main__":
    main()
