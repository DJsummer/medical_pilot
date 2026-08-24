#!/usr/bin/env bash
# 部署自检
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ROOT/.env"
  set +a
fi

PORT="${MEDICAL_PORT:-8900}"
BASE="http://127.0.0.1:${PORT}"

echo "==> Health"
curl -fsS "$BASE/api/health" | python3 -m json.tool

echo "==> Gold pipeline (abd-001, 无 LLM)"
curl -fsS -X POST "$BASE/api/pipeline" \
  -H 'Content-Type: application/json' \
  -d '{"sample_id":"abd-001","use_llm":false}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('findings:', d['findings_text'][:60]+'...')"

echo "==> 报告存储"
curl -fsS "$BASE/api/reports" | python3 -c "import sys,json; d=json.load(sys.stdin); print('reports:', len(d.get('reports',[])))"

echo ""
echo "自检通过 ✓"
