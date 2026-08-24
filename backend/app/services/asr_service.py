"""ASR 服务 — 百炼 Qwen3-ASR-Flash（OpenAI 兼容 chat/completions + base64 音频）。"""
from __future__ import annotations

import base64
import logging
from typing import Tuple

from backend.app.core.config import asr_config, asr_enabled

logger = logging.getLogger(__name__)

ALLOWED_AUDIO_TYPES = {
    "audio/mpeg",
    "audio/mp4",
    "audio/wav",
    "audio/x-wav",
    "audio/m4a",
    "audio/x-m4a",
    "audio/webm",
    "audio/ogg",
}
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # Qwen3-ASR-Flash base64 限制约 10MB


def _is_qwen_asr_model(model: str) -> bool:
    m = (model or "").lower()
    return "qwen" in m and "asr" in m


def transcribe_audio(
    audio_bytes: bytes,
    content_type: str,
    filename: str = "audio.webm",
) -> Tuple[bool, str]:
    """上传音频 → 转写文本。返回 (ok, text_or_error)。"""
    if not asr_enabled():
        return False, "ASR 未配置 API Key"

    ct = (content_type or "").split(";")[0].strip().lower()
    if ct not in ALLOWED_AUDIO_TYPES:
        return False, f"不支持的音频格式: {content_type}"

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        return False, "音频文件不能超过 10 MB"

    if not audio_bytes:
        return False, "音频为空"

    cfg = asr_config()
    if not cfg["api_key"] or not cfg["base_url"]:
        return False, "ASR Base URL 或 API Key 未配置"

    model = cfg["model"]
    if not _is_qwen_asr_model(model):
        model = "qwen3-asr-flash"

    try:
        return _transcribe_qwen_asr(audio_bytes, ct, cfg, model)
    except Exception as e:
        logger.exception("ASR transcribe failed")
        return False, f"语音转写失败: {e}"


def _transcribe_qwen_asr(
    audio_bytes: bytes,
    content_type: str,
    cfg: dict,
    model: str,
) -> Tuple[bool, str]:
    """百炼 Qwen3-ASR-Flash：chat/completions + input_audio base64。"""
    try:
        from openai import OpenAI
    except ImportError:
        return False, "请安装 openai: pip install openai>=1.52"

    data_uri = f"data:{content_type};base64,{base64.b64encode(audio_bytes).decode()}"
    client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"], timeout=cfg["timeout"])

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {"data": data_uri},
                    }
                ],
            }
        ],
        stream=False,
        extra_body={
            "asr_options": {
                "language": "zh",
                "enable_itn": True,
            }
        },
    )

    msg = completion.choices[0].message
    text = (msg.content or "").strip()
    if not text:
        return False, "转写结果为空，请重新口述"
    return True, text
