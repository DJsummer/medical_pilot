#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$ROOT/data/server.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "未找到 PID 文件，服务可能未运行"
  exit 0
fi

PID="$(cat "$PID_FILE")"
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  echo "已停止服务 (PID $PID)"
else
  echo "进程不存在 (PID $PID)"
fi
rm -f "$PID_FILE"
