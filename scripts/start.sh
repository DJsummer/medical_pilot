#!/usr/bin/env bash
# 生产模式启动（无 reload，日志写入 data/logs）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PID_FILE="$ROOT/data/server.pid"
LOG_DIR="$ROOT/data/logs"
LOG_FILE="$LOG_DIR/server.log"

mkdir -p "$LOG_DIR" "$ROOT/data/reports"

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "服务已在运行 (PID $(cat "$PID_FILE"))"
  echo "访问: http://127.0.0.1:${MEDICAL_PORT:-8900}"
  exit 0
fi

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ROOT/.env"
  set +a
elif [[ -f "$ROOT/../QS/backend/.env" ]]; then
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
WORKERS="${MEDICAL_WORKERS:-1}"

nohup uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  --workers "$WORKERS" \
  --log-level info \
  >> "$LOG_FILE" 2>&1 &

echo $! > "$PID_FILE"
sleep 2

if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "AI B超报告书写助手 已启动"
  echo "  PID:   $(cat "$PID_FILE")"
  echo "  地址:  http://127.0.0.1:${PORT}"
  echo "  日志:  $LOG_FILE"
  curl -fsS "http://127.0.0.1:${PORT}/api/health" && echo ""
else
  echo "启动失败，查看日志: $LOG_FILE"
  tail -20 "$LOG_FILE"
  exit 1
fi
