#!/usr/bin/env bash
# 首次安装依赖
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> 安装 Python 依赖"
python3 -m pip install -r requirements.txt

mkdir -p data/reports data/logs

if [[ ! -f "$ROOT/.env" ]]; then
  echo "==> 未找到 .env，从 .env.example 复制"
  cp .env.example .env
  echo "请编辑 .env 填入 DASHSCOPE_API_KEY 后重新运行 ./scripts/start.sh"
  exit 1
fi

set -a
# shellcheck source=/dev/null
source "$ROOT/.env"
set +a

if [[ -z "${DASHSCOPE_API_KEY:-}${MEDICAL_LLM_API_KEY:-}" ]]; then
  echo "警告: 未配置 API Key，仅可使用 Gold 演示模式"
fi

echo "==> 运行测试"
python3 -m pytest backend/tests/ -q

echo ""
echo "安装完成。启动: ./scripts/start.sh"
