"""ASR 服务测试。"""
from unittest.mock import MagicMock, patch

from backend.app.services.asr_service import transcribe_audio


def test_transcribe_rejects_empty():
    ok, msg = transcribe_audio(b"", "audio/webm")
    assert not ok


def test_transcribe_rejects_bad_type():
    ok, msg = transcribe_audio(b"data", "text/plain")
    assert not ok
    assert "不支持" in msg


@patch("backend.app.services.asr_service.asr_enabled", return_value=True)
@patch("backend.app.services.asr_service.asr_config")
@patch("openai.OpenAI")
def test_transcribe_qwen_asr(mock_openai_cls, mock_cfg, _enabled):
    mock_cfg.return_value = {
        "api_key": "test-key",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen3-asr-flash",
        "timeout": 30,
    }
    mock_msg = MagicMock()
    mock_msg.content = "肝脏大小形态正常"
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion
    mock_openai_cls.return_value = mock_client

    ok, text = transcribe_audio(b"fake audio bytes", "audio/webm")
    assert ok
    assert "肝脏" in text
    call_kw = mock_client.chat.completions.create.call_args.kwargs
    assert call_kw["model"] == "qwen3-asr-flash"
    assert call_kw["extra_body"]["asr_options"]["language"] == "zh"
