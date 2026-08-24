#!/usr/bin/env bash
# 启动 AI B超报告书写助手
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ROOT/.env"
  set +a
fi

# 复用 QS 百炼配置
if [[ -z "${MEDICAL_LLM_API_KEY:-}" && -f "$ROOT/../QS/backend/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ROOT/../QS/backend/.env"
  set +a
  export MEDICAL_LLM_API_KEY="${DASHSCOPE_API_KEY:-}"
  export MEDICAL_LLM_BASE_URL="${OPENAI_API_BASE:-}"
  export MEDICAL_LLM_MODEL="${QS_LLM_MODEL:-qwen-plus}"
  export MEDICAL_ASR_API_KEY="${DASHSCOPE_API_KEY:-}"
  export MEDICAL_ASR_BASE_URL="${OPENAI_API_BASE:-}"
fi

PORT="${MEDICAL_PORT:-8900}"
echo "Starting on http://127.0.0.1:${PORT}"
exec uvicorn backend.app.main:app --host 0.0.0.0 --port "$PORT" --reload
