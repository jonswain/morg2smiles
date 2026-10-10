#!/usr/bin/env bash
# Stage 6, rescheduled -- the third point on the 8,508-step data axis.
#
# overnight2b.sh skipped this run on a correct measurement: 209 minutes left
# against a 294-minute need, where the need included a full re-scoring of every
# checkpoint. Two things changed after stages 4 and 5 finished early:
#
#   * the data axis at 8,508 steps now rests on two points (90,682 and
#     1,881,996 molecules, 1.39x error reduction per decade). A third point at
#     909,800 turns a two-point slope into something that can be falsified.
#   * compare_checkpoints.py gained --only, so scoring one new checkpoint costs
#     ~25 minutes rather than ~66, because the protocol is still derived from
#     every present run and only the scoring is narrowed.
#
# Together that fits in the time left, with the deadline pulled in to 08:40 so
# the machine is idle before its owner wants it.
#
# configs/small_1m_matched.yaml was trimmed to two intermediate evaluations and
# max_hours 2.7: the endpoint is the point of this run, and a hard wall-clock
# stop matters more than its curve.
set -u

cd "$(dirname "$0")/.."
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src
LOGS=results/overnight2
mkdir -p "$LOGS"

DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-11 08:40" "+%s")
SCORING_SECONDS=1800

caffeinate -dimsu -w $$ &

say() { echo "[$(date '+%m-%d %H:%M:%S')] (2c) $*" | tee -a "$LOGS/driver.log"; }
remaining() { echo $(( DEADLINE_EPOCH - $(date "+%s") )); }

say "=== stage 6 retry, $(( $(remaining) / 60 )) minutes to 08:40 ==="

needed=$(( 10000 + SCORING_SECONDS ))
if [ "$(remaining)" -lt "$needed" ]; then
    say "ABORT: $(( $(remaining) / 60 )) min left, needs $(( needed / 60 ))"
    exit 0
fi

say "stage 6: small_1m_matched -- 8,508 steps on the 1M shard, horizon 8,508"
$PY -u scripts/run_experiment.py \
    --config configs/small_1m_matched.yaml \
    --eval-n 2000 --budget molecules --no-baseline \
    --note "8M, 1M shard, 8508 steps, horizon 8508 -- third point on the fixed-compute data axis" \
    > "$LOGS/stage6_small_1m_matched.log" 2>&1
say "stage 6 exit=$?, $(( $(remaining) / 60 )) minutes left"

# Only score if the run actually reached the step it was matched to. A
# truncated run is not a matched-compute point and must not enter the table.
reached=$($PY - <<'PYEOF'
import json
from pathlib import Path

path = Path("checkpoints/small_1m_matched/record.json")
if not path.exists():
    print("missing")
else:
    rec = json.loads(path.read_text())
    steps = [h.get("step") for h in rec.get("history", []) if h.get("step")]
    print(max(steps) if steps else "none")
PYEOF
)
say "stage 6 reached step: $reached (needs 8508)"

if [ "$reached" = "8508" ] && [ "$(remaining)" -gt "$SCORING_SECONDS" ]; then
    say "stage 9: scoring small_1m_matched under the stage-4 protocol"
    $PY -u scripts/compare_checkpoints.py --eval-n 2000 \
        --only small_1m_matched \
        --out results/overnight2/comparison_1m_matched.json \
        > "$LOGS/stage9_comparison_only.log" 2>&1
    say "stage 9 exit=$?"
else
    say "stage 9 SKIPPED: reached=$reached, $(( $(remaining) / 60 )) min left"
fi

say "=== stage 6 retry done, $(( $(remaining) / 60 )) minutes to spare ==="
