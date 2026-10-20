#!/usr/bin/env bash
# Night 7 -- item 1 of docs/next-steps-2026-10-19.md, the whole of it.
#
# Fourteen hours, Tuesday 18:42 to Wednesday 08:42, deadline set at 08:30 to
# leave the morning clear. The item is the constant-passes corpus row, and it
# is the first job of the closing plan: it answers the question stage 9 could
# only infer an answer to, and it is what makes the final full-ChEMBL run
# interpretable rather than another corpus-and-steps comparison.
#
# The two pre-registrations are in the configs, as usual:
#   configs/small_100k_1p2.yaml   856 steps, 0.30 h -- the floor check
#   configs/small_full_1p2.yaml 17,772 steps, 6.60 h -- the measurement
#
# Priority order, and why. The floor check trains first because it is 18
# minutes and can falsify the decomposition on its own. The main training is
# second because it is the deliverable and everything after it is scoring. The
# main run's k=60 scoring is third because the pre-registered number is read
# off it. The floor check's scoring is *fifth*, after the analyses, because its
# informative branch is the one that needs no precision: if it recovers
# anything at all the decomposition is in trouble, and that shows up in a cheap
# draw as readily as an expensive one.
#
# Every stage is guarded on the clock and skips rather than overruns, the house
# pattern since night 3. Stages that already have their output on disk skip
# too, so re-running this script after a crash resumes rather than restarts.
set -u
cd "$(dirname "$0")/.."
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src:.
LOGS=results/overnight7
mkdir -p "$LOGS/outcomes_full_1p2" "$LOGS/outcomes_100k_1p2" "$LOGS/outcomes_common_1p2"
DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-21 08:30" "+%s")

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
print(r.get('stopped_because', '?'), '/', round(r.get('elapsed_hours', 0), 2), 'h')
" 2>/dev/null || echo '?'
}

say "=== night 7 start, $(( $(remaining) / 60 )) min to Wed 08:30 ==="

# ---------------------------------------------------------------- stage 1
# The floor check. 856 steps on the 100k shard at 1.2087 passes.
if [ -f checkpoints/small_100k_1p2/best.pt ]; then
    say "SKIP stage 1 training: checkpoints/small_100k_1p2/best.pt exists"
elif fits 3600 "stage 1"; then
    say "stage 1: small_100k_1p2, 8.0M params, 100k shard, 856 steps"
    $PY -u scripts/run_experiment.py --config configs/small_100k_1p2.yaml \
        --eval-n 500 --budget molecules --no-baseline \
        --note "8.0M, 100k shard, 856 steps -- the constant-passes floor check" \
        > "$LOGS/stage1_small_100k_1p2.log" 2>&1
    say "stage 1 exit=$?, $(stopped_because small_100k_1p2)"
fi

# ---------------------------------------------------------------- stage 2
# The measurement. 17,772 steps on the full shard at 1.2087 passes.
#
# Needs 6.60 h at the measured 1.337 s/step; the guard asks for 8.0 h so that a
# run which would hit max_hours and leave its cosine schedule unfinished is not
# started at all. An incomplete run here is worse than no run: it would not be
# a complete 17,772-step run and the pre-registration would not apply to it.
if [ -f checkpoints/small_full_1p2/best.pt ]; then
    say "SKIP stage 2 training: checkpoints/small_full_1p2/best.pt exists"
elif fits 28800 "stage 2"; then
    say "stage 2: small_full_1p2, 8.0M params, full shard, 17,772 steps"
    $PY -u scripts/run_experiment.py --config configs/small_full_1p2.yaml \
        --eval-n 500 --budget molecules --no-baseline \
        --note "8.0M, full shard, 17772 steps -- f' at constant passes, 1.2087" \
        > "$LOGS/stage2_small_full_1p2.log" 2>&1
    say "stage 2 exit=$?, $(stopped_because small_full_1p2)"
fi

# ---------------------------------------------------------------- stage 3
# The pre-registered number. The invocation is small_1m_matched's exactly, so
# the two are prefix-to-prefix comparable: --eval-n 2400 --min-heavy-atoms 30
# --eval-k 60 -T 0.6 --top-p 1.0 --max-oversample 12, large protocol, k=60.
if [ ! -f checkpoints/small_full_1p2/best.pt ]; then
    say "SKIP stage 3: checkpoints/small_full_1p2/best.pt does not exist"
elif fits 7200 "stage 3"; then
    say "stage 3: small_full_1p2 at T=0.6, k=60, large protocol"
    $PY -u scripts/compare_checkpoints.py --no-baseline --only small_full_1p2 \
        --eval-n 2400 --min-heavy-atoms 30 --eval-k 60 \
        --temperature 0.6 --top-p 1.0 --max-oversample 12 \
        --out "$LOGS/comparison_k60_full_1p2.json" \
        --dump-outcomes "$LOGS/outcomes_full_1p2" \
        > "$LOGS/stage3_k60.log" 2>&1
    say "stage 3 exit=$?"
    $PY -c "
import json
d = json.load(open('$LOGS/comparison_k60_full_1p2.json'))
print(json.dumps(d, indent=2)[:4000])
" >> "$LOGS/driver.log" 2>&1
fi

# ---------------------------------------------------------------- stage 4
# The band table and the budget exponent, so the result can be read per band
# and against the deficit power law -- both adopted practice since night 5.
D="$LOGS/outcomes_full_1p2/small_full_1p2.jsonl"
if [ ! -f "$D" ]; then
    say "SKIP stage 4: no dump at $D"
elif fits 1800 "stage 4"; then
    for metric in recovery structure; do
        suffix=""; [ "$metric" = structure ] && suffix="_structure"
        $PY -u scripts/band_analysis.py --dumps "$LOGS/outcomes_full_1p2" \
            --k 60 --order generation --metric $metric \
            --out "$LOGS/band_k60_full_1p2${suffix}.json" \
            > "$LOGS/stage4_band${suffix}.log" 2>&1
    done
    say "stage 4 band tables exit=$?"
    $PY -u scripts/miss_anatomy.py --dump "$D" --k 60 \
        --out "$LOGS/miss_anatomy_full_1p2.json" > "$LOGS/stage4_anatomy.log" 2>&1
    $PY -u scripts/budget_curve.py --anatomy "$LOGS/miss_anatomy_full_1p2.json" \
        --dump "$D" --k 60 --out "$LOGS/budget_curve_full_1p2.json" \
        > "$LOGS/stage4_curve.log" 2>&1
    say "stage 4 analyses exit=$?"
fi

# ---------------------------------------------------------------- stage 5
# The floor check's number, on a deliberately cheap draw. 600 queries at
# --max-oversample 4 rather than 2,400 at 12: a model at 856 steps hits the
# oversample cap on nearly every query, so the full protocol would cost about
# seven hours to measure a quantity predicted to be zero. Both economies push
# the number down, which is why the config registers this cell as able to
# falsify and not to confirm.
if [ ! -f checkpoints/small_100k_1p2/best.pt ]; then
    say "SKIP stage 5: checkpoints/small_100k_1p2/best.pt does not exist"
elif fits 4200 "stage 5"; then
    say "stage 5: small_100k_1p2 at T=0.6, k=60, 600 queries, capped draw"
    $PY -u scripts/compare_checkpoints.py --no-baseline --only small_100k_1p2 \
        --eval-n 600 --min-heavy-atoms 30 --eval-k 60 \
        --temperature 0.6 --top-p 1.0 --max-oversample 4 \
        --out "$LOGS/comparison_k60_100k_1p2.json" \
        --dump-outcomes "$LOGS/outcomes_100k_1p2" \
        > "$LOGS/stage5_k60.log" 2>&1
    say "stage 5 exit=$?"
    $PY -c "
import json
d = json.load(open('$LOGS/comparison_k60_100k_1p2.json'))
print(json.dumps(d, indent=2)[:3000])
" >> "$LOGS/driver.log" 2>&1
fi

# ---------------------------------------------------------------- stage 6
# Optional, and last: the main run on the common protocol as well, so the new
# checkpoint has a row in the table the README quotes. Not part of item 1's
# registration -- that is stage 3 -- but it is 40 minutes and the final run
# will want both protocols anyway.
if [ ! -f checkpoints/small_full_1p2/best.pt ]; then
    say "SKIP stage 6: checkpoints/small_full_1p2/best.pt does not exist"
elif fits 3600 "stage 6"; then
    say "stage 6: small_full_1p2 and small_1m_matched on the common protocol at T=0.6"
    $PY -u scripts/compare_checkpoints.py --no-baseline \
        --only small_full_1p2 --only small_1m_matched \
        --eval-n 2000 --eval-k 20 --temperature 0.6 --top-p 1.0 \
        --out "$LOGS/comparison_common_1p2.json" \
        --dump-outcomes "$LOGS/outcomes_common_1p2" \
        > "$LOGS/stage6_common.log" 2>&1
    say "stage 6 exit=$?"
fi

say "=== night 7 done, $(( $(remaining) / 60 )) min to spare ==="
