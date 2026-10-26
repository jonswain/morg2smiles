#!/usr/bin/env bash
# Night 9 -- item 4 of docs/next-steps-2026-10-19.md, the final run.
#
# Full ChEMBL, 8.0M parameters, 6 passes, 88,218 steps. The plan and every cost
# in it: docs/final-run-plan.md. The pre-registration: configs/small_full_6p.yaml.
#
# THIRTY-THREE HOURS. The job is priced at 28.0 h end to end -- 26.3 h of
# training (88,218 steps at a solved 1.047 s/step plus twelve evaluations) and
# 1.75 h of scoring -- with an upper bound of 30.6 h if the whole run held the
# slowest sustained rate any 8.0M cell has produced. The guard below asks for
# 33 h before starting stage 1 at all.
#
# It asks rather than hopes because an incomplete run is worse than no run: the
# cosine schedule anneals to zero at max_steps, so a run stopped early is not a
# complete 88,218-step run and the pre-registration does not apply to it. That
# is block 1's voided-trace lesson, and it is why max_hours in the config is a
# runaway guard set well above the expected time instead of a deadline.
#
# Priority order, which is night 8's and worked: training is the only
# irreplaceable thing in the window. All the scoring runs against a checkpoint
# on disk and can happen any time afterwards, so every stage after stage 1
# guards tightly, skips without complaint, and is re-runnable -- stages whose
# output already exists are skipped, so running this again later finishes
# whatever the clock cut off.
#
# Usage: scripts/overnight9.sh [deadline]
#   deadline defaults to 33 h from launch; pass "YYYY-MM-DD HH:MM" to pin it.
set -u
cd "$(dirname "$0")/.."
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src:.
LOGS=results/overnight9
mkdir -p "$LOGS/outcomes_full_6p" "$LOGS/outcomes_50plus_full_6p"

if [ "$#" -ge 1 ]; then
    DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "$1" "+%s")
else
    DEADLINE_EPOCH=$(( $(date "+%s") + 33 * 3600 ))
fi

caffeinate -dimsu -w $$ &

say() { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOGS/driver.log"; }
remaining() { echo $(( DEADLINE_EPOCH - $(date "+%s") )); }
fits() {
    if [ "$(remaining)" -lt "$1" ]; then
        say "SKIP $2: $(( $(remaining) / 60 )) min left, needs $(( $1 / 60 ))"
        return 1
    fi
    return 0
}
stopped_because() {
    $PY -c "
import json
r = json.load(open('checkpoints/$1/record.json'))
print(r.get('stopped_because', '?'), '/', round(r.get('total_seconds', 0) / 3600, 2), 'h')
" 2>/dev/null || echo '?'
}

say "=== night 9 start, git $(git rev-parse --short HEAD), $(( $(remaining) / 60 )) min to deadline ==="

# ---------------------------------------------------------------- stage 1
# The run. 88,218 steps on the full shard, 6.00 passes.
#
# Needs 26.3 h at the solved rate; the guard asks for 33 h so that a run which
# would hit max_hours and leave its cosine schedule unfinished is not started.
if [ -f checkpoints/small_full_6p/best.pt ]; then
    say "SKIP stage 1 training: checkpoints/small_full_6p/best.pt exists"
elif fits 118800 "stage 1"; then
    say "stage 1: small_full_6p, 8.0M params, full shard, 88,218 steps, 6.00 passes"
    $PY -u scripts/run_experiment.py --config configs/small_full_6p.yaml \
        --eval-n 500 --budget molecules --no-baseline \
        --note "8.0M, full shard, 88218 steps -- item 4, the final run at 6 passes" \
        > "$LOGS/stage1_small_full_6p.log" 2>&1
    say "stage 1 exit=$?, $(stopped_because small_full_6p)"
fi

# ---------------------------------------------------------------- stage 2
# The large protocol. Night 6's score() exactly, which is what produced every
# other cell of the 30+ instrument, so all four are prefix-to-prefix
# comparable: --eval-n 2400 --min-heavy-atoms 30 --eval-k 60 -T 0.6 --top-p 1.0
# --max-oversample 12.
if [ ! -f checkpoints/small_full_6p/best.pt ]; then
    say "SKIP stage 2: checkpoints/small_full_6p/best.pt does not exist"
elif [ -f "$LOGS/comparison_k60_full_6p.json" ]; then
    say "SKIP stage 2: comparison already on disk"
elif fits 7200 "stage 2"; then
    say "stage 2: small_full_6p at T=0.6, k=60, large protocol (30+, 2,400 queries)"
    $PY -u scripts/compare_checkpoints.py --no-baseline --only small_full_6p \
        --eval-n 2400 --min-heavy-atoms 30 --eval-k 60 \
        --temperature 0.6 --top-p 1.0 --max-oversample 12 \
        --out "$LOGS/comparison_k60_full_6p.json" \
        --dump-outcomes "$LOGS/outcomes_full_6p" \
        > "$LOGS/stage2_k60.log" 2>&1
    say "stage 2 exit=$?"
fi

# ---------------------------------------------------------------- stage 3
# The 50+ protocol -- the registration of record for large molecules. Night
# 7b's invocation exactly: --eval-n 1000 --min-heavy-atoms 50 --eval-k 60
# -T 0.6 --top-p 1.0 --max-oversample 10, which draws 893 fp_unseen queries
# from a 1,068-molecule pool.
if [ ! -f checkpoints/small_full_6p/best.pt ]; then
    say "SKIP stage 3: checkpoints/small_full_6p/best.pt does not exist"
elif [ -f "$LOGS/comparison_50plus_full_6p.json" ]; then
    say "SKIP stage 3: 50+ comparison already on disk"
elif fits 3600 "stage 3"; then
    say "stage 3: small_full_6p on the 50+ protocol, k=60, T=0.6"
    $PY -u scripts/compare_checkpoints.py --no-baseline --only small_full_6p \
        --eval-n 1000 --min-heavy-atoms 50 --eval-k 60 \
        --temperature 0.6 --top-p 1.0 --max-oversample 10 \
        --out "$LOGS/comparison_50plus_full_6p.json" \
        --dump-outcomes "$LOGS/outcomes_50plus_full_6p" \
        > "$LOGS/stage3_50plus.log" 2>&1
    say "stage 3 exit=$?"
fi

# ---------------------------------------------------------------- stage 4
# The band tables the registration is scored against. Four reads per protocol:
# both metrics at k=60, and both metrics at k=1 in consensus order, which is
# registration (3) and the one place on the 30+ protocol with room to move.
#
# Rule 3 of methodology section 7, re-affirmed on night 7b: read every size
# claim on structure_accuracy as well as recovery. Recovery overstated a slope
# by 43% at 60-64 when the low cell sat on the floor.
D="$LOGS/outcomes_full_6p/small_full_6p.jsonl"
if [ ! -f "$D" ]; then
    say "SKIP stage 4: no 30+ dump at $D"
elif fits 2400 "stage 4"; then
    for metric in recovery structure; do
        sfx=""; [ "$metric" = structure ] && sfx="_structure"
        $PY -u scripts/band_analysis.py --dumps "$LOGS/outcomes_full_6p" \
            --k 60 --order generation --metric $metric \
            --out "$LOGS/band_k60_full_6p${sfx}.json" \
            > "$LOGS/stage4_band_k60${sfx}.log" 2>&1
        $PY -u scripts/band_analysis.py --dumps "$LOGS/outcomes_full_6p" \
            --k 1 --order consensus --metric $metric \
            --out "$LOGS/band_k1_full_6p${sfx}.json" \
            > "$LOGS/stage4_band_k1${sfx}.log" 2>&1
    done
    say "stage 4 30+ band tables exit=$?"
fi

D50="$LOGS/outcomes_50plus_full_6p/small_full_6p.jsonl"
if [ ! -f "$D50" ]; then
    say "SKIP stage 4b: no 50+ dump at $D50"
elif fits 1800 "stage 4b"; then
    for metric in recovery structure; do
        sfx=""; [ "$metric" = structure ] && sfx="_structure"
        $PY -u scripts/band_analysis.py --dumps "$LOGS/outcomes_50plus_full_6p" \
            --k 60 --order generation --metric $metric \
            --out "$LOGS/b50_full_6p${sfx}.json" \
            > "$LOGS/stage4b_b50${sfx}.log" 2>&1
    done
    say "stage 4b 50+ band tables exit=$?"
fi

# ---------------------------------------------------------------- stage 5
# Registration (5): do the two exponents transport to this corpus? b from the
# budget curve against the 0.144-0.396 range of results.md section 2.1, and c
# from the step curve against the 0.701-0.911 item 2 measured. Cheapest stages
# here -- no GPU, seconds each -- which is why they run last.
if [ ! -f "$D" ]; then
    say "SKIP stage 5: no 30+ dump"
elif fits 1800 "stage 5"; then
    $PY -u scripts/miss_anatomy.py --dump "$D" --k 60 \
        --out "$LOGS/miss_anatomy_full_6p.json" > "$LOGS/stage5_anatomy.log" 2>&1
    $PY -u scripts/budget_curve.py --anatomy "$LOGS/miss_anatomy_full_6p.json" \
        --dump "$D" --k 60 --out "$LOGS/budget_curve_full_6p.json" \
        > "$LOGS/stage5_curve.log" 2>&1
    say "stage 5 anatomy and budget curve exit=$?"
fi

if [ ! -f checkpoints/small_full_6p/history.json ]; then
    say "SKIP stage 5b: no history for small_full_6p"
elif fits 900 "stage 5b"; then
    $PY -u scripts/step_curve.py --runs small_full_6p,small_full_1p2,small_1m \
        --out "$LOGS/step_curve_full_6p.json" > "$LOGS/stage5b_step_curve.log" 2>&1
    say "stage 5b step exponent exit=$?"
fi

say "=== night 9 done, $(( $(remaining) / 60 )) min to spare ==="
say "score the registration against configs/small_full_6p.yaml -- five entries,"
say "intervals that tile, both metrics. The headline rec@60 is a ceiling reading."
