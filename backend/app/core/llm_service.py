"""LLM 网关 — OpenAI 兼容 chat/completions（stdlib urllib）。"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from backend.app.core.config import llm_config, llm_enabled

logger = logging.getLogger(__name__)


def _chat_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return base + "/chat/completions"


def chat(
    messages: List[Dict[str, str]],
    *,
    json_mode: bool = False,
    usage_out: Optional[Dict[str, int]] = None,
) -> Tuple[bool, str]:
    if not llm_enabled():
        return False, "LLM 未配置：请设置 MEDICAL_LLM_API_KEY 或 DASHSCOPE_API_KEY"

    cfg = llm_config()
    api_key = cfg["api_key"]
    url = _chat_url(cfg["base_url"])
    if not api_key or not cfg["base_url"]:
        return False, "LLM Base URL 或 API Key 未配置"

    body: Dict[str, Any] = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": cfg["temperature"],
        "max_tokens": cfg["max_tokens"],
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=cfg["timeout"]) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        logger.error("LLM HTTP %s: %s", e.code, err_body[:500])
        return False, f"LLM 请求失败 HTTP {e.code}: {err_body[:200]}"
    except Exception as e:
        logger.exception("LLM request failed")
        return False, str(e)

    usage = raw.get("usage") or {}
    if usage_out is not None:
        usage_out.update({
            "prompt_tokens": int(usage.get("prompt_tokens") or 0),
            "completion_tokens": int(usage.get("completion_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
        })

    content = (raw.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    return True, content.strip()
