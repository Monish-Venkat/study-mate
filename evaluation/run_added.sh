#!/usr/bin/env bash
# Ablation of the additions made after the first revision.
#
# Every configuration below holds the *original* ablation's conditions fixed
# (boilerplate filter on, CRAG on with the 3B grader) and switches exactly one
# new mechanism, so each row is comparable to "full" in Table III and to the
# row above it.
#
#   full_rerun    filter + CRAG(3B), everything new disabled.
#                 Re-measures the published row on today's hardware, because a
#                 new row is only comparable if the old one reproduces.
#   floor         + evidence floor (CRAG_MIN_EVIDENCE=3)
#   floor_hybrid  + hybrid retrieval (BM25 fused with dense by RRF)
#   floor_ground  + post-generation grounding audit
#
#   bash evaluation/run_added.sh [limit]
set -u
LIMIT="${1:-40}"
PORT=8000
LOGDIR="${TMPDIR:-/tmp}"

run_config () {
  local label="$1" hybrid="$2" ground="$3" floor="$4"
  echo "=== ${label}  (HYBRID=${hybrid} GROUNDING=${ground} MIN_EVIDENCE=${floor}) ==="
  local pid
  pid=$(netstat -ano | grep ":${PORT}.*LISTENING" | awk '{print $5}' | head -1)
  [ -n "${pid}" ] && powershell -NoProfile -Command "Stop-Process -Id ${pid} -Force" >/dev/null 2>&1
  sleep 2
  FILTER_BOILERPLATE=true ENABLE_CRAG=true \
  ENABLE_HYBRID="${hybrid}" ENABLE_GROUNDING="${ground}" \
  ENABLE_GROUNDING_VERIFY="${ground}" CRAG_MIN_EVIDENCE="${floor}" \
    python -m uvicorn app.main:app --host 127.0.0.1 --port "${PORT}" \
    > "${LOGDIR}/abl_${label}.log" 2>&1 &
  until curl -s -m 3 "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; do sleep 2; done
  python evaluation/run_benchmark.py --label "${label}" --limit "${LIMIT}"
}

# full_rerun is kept in the ladder because a new row is only comparable if the
# published one still reproduces; run it first when re-measuring from scratch.
#   run_config full_rerun   false false 0
#   run_config floor_hybrid true  false 3   # hybrid is measured at retrieval level instead
run_config floor        false false 3
run_config floor_ground false true  3

echo "=== done ==="
