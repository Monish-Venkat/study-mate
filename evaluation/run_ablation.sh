#!/usr/bin/env bash
# Ablation ladder: isolate whether the corrective layer earns its cost.
#   1 vanilla RAG            no boilerplate filter, no grading
#   2 + boilerplate filter   near-zero-cost preprocessing
#   3 + CRAG only            grading and re-retrieval, no filter
#   4 full                   filter + CRAG (shipped configuration)
#
#   bash evaluation/run_ablation.sh [limit]
set -u
LIMIT="${1:-40}"
PORT=8000

run_config () {
  local label="$1" filter="$2" crag="$3"
  echo "=== ${label} (FILTER_BOILERPLATE=${filter} ENABLE_CRAG=${crag}) ==="
  local pid
  pid=$(netstat -ano | grep ":${PORT}.*LISTENING" | awk '{print $5}' | head -1)
  [ -n "${pid}" ] && powershell -NoProfile -Command "Stop-Process -Id ${pid} -Force" >/dev/null 2>&1
  sleep 2
  FILTER_BOILERPLATE="${filter}" ENABLE_CRAG="${crag}" \
    python -m uvicorn app.main:app --host 127.0.0.1 --port "${PORT}" > "/tmp/abl_${label}.log" 2>&1 &
  until curl -s -m 3 "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; do sleep 2; done
  python evaluation/run_benchmark.py --label "${label}" --limit "${LIMIT}"
}

run_config vanilla       false false
run_config filter_only   true  false
run_config crag_only     false true
run_config full          true  true

python evaluation/make_table.py
