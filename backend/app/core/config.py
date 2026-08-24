"""应用配置 — 从环境变量读取 LLM 等设置。"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"


def llm_enabled() -> bool:
    return bool(os.environ.get("MEDICAL_LLM_API_KEY", "").strip())


def llm_config() -> dict:
    base = (os.environ.get("MEDICAL_LLM_BASE_URL") or os.environ.get("OPENAI_API_BASE") or "").strip().rstrip("/")
    return {
        "api_key": (os.environ.get("MEDICAL_LLM_API_KEY") or os.environ.get("DASHSCOPE_API_KEY") or "").strip(),
        "base_url": base,
        "model": (os.environ.get("MEDICAL_LLM_MODEL") or os.environ.get("QS_LLM_MODEL") or "qwen-plus").strip(),
        "temperature": float(os.environ.get("MEDICAL_LLM_TEMPERATURE", "0.1")),
        "max_tokens": int(os.environ.get("MEDICAL_LLM_MAX_TOKENS", "4096")),
        "timeout": float(os.environ.get("MEDICAL_LLM_TIMEOUT", "120")),
    }


def asr_enabled() -> bool:
    return bool(
        (os.environ.get("MEDICAL_ASR_API_KEY") or os.environ.get("MEDICAL_LLM_API_KEY") or os.environ.get("DASHSCOPE_API_KEY") or "").strip()
    )


def asr_config() -> dict:
    cfg = llm_config()
    base = (os.environ.get("MEDICAL_ASR_BASE_URL") or cfg["base_url"] or "").strip().rstrip("/")
    return {
        "api_key": (os.environ.get("MEDICAL_ASR_API_KEY") or cfg["api_key"] or "").strip(),
        "base_url": base,
        "model": (os.environ.get("MEDICAL_ASR_MODEL") or "qwen3-asr-flash").strip(),
        "timeout": float(os.environ.get("MEDICAL_ASR_TIMEOUT", "60")),
    }
