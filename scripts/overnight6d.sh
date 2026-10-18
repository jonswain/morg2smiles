#!/usr/bin/env bash
# Stage 10, chained off scripts/overnight6c.sh: the fourth cell of the
# capacity x steps 2x2.
#
# Added mid-run on Sunday afternoon, after stage 6 came in about eleven hours
# ahead of the deadline and block 3's uniform-cut result turned out to have one
# sharp test that costs only training time. It is a separate script rather than
# another stage appended to the running driver, because appending to a script
# bash is executing relies on bash's read buffering; chaining on the driver's
# exit does not.
#
# configs/medium_1m_8k.yaml carries the pre-registration and the arithmetic. In
# short: if capacity's 17% deficit cut is a property of the capacity step, then
# the same ratio holds at 8,508 steps, which pins this run's rec@60 at 0.6045
# on the large protocol before it exists.
#
# Last in priority on purpose. Stages 8 and 9 were registered before the
# weekend began and this was not, so it runs on the clock they leave behind,
# against the same hard deadline. Both halves are guarded separately: the
# training is worth having even if the k=60 scoring does not fit, because the
# common-protocol pair is 40 minutes and answers the capacity gap at 8,508
# steps on its own.
set -u
cd "$(dirname "$0")/.."
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src:.
LOGS=results/overnight6
mkdir -p "$LOGS/outcomes_cap8k" "$LOGS/outcomes_common_t06_cap8k"
DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-19 06:30" "+%s")

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

say "=== stage 10 start, $(( $(remaining) / 60 )) min to Mon 06:30 ==="

if [ -f checkpoints/medium_1m_8k/best.pt ]; then
    say "SKIP stage 10 training: checkpoints/medium_1m_8k/best.pt already exists"
elif fits 23400 "stage 10"; then
    say "stage 10: medium_1m_8k, 15.1M params, 1M shard, 8,508 steps"
    $PY -u scripts/run_experiment.py --config configs/medium_1m_8k.yaml \
        --eval-n 2000 --budget molecules --no-baseline \
        --note "15.1M, 1M shard, 8508 steps -- the fourth cell of the capacity x steps 2x2" \
        > "$LOGS/stage10_medium_1m_8k.log" 2>&1
    say "stage 10 exit=$?"
    say "stage 10 stopped at: $($PY -c "
import json
r = json.load(open('checkpoints/medium_1m_8k/record.json'))
print(r.get('stopped_because', '?'), '/', round(r.get('elapsed_hours', 0), 1), 'h')
" 2>/dev/null || echo '?')"
fi

if [ ! -f checkpoints/medium_1m_8k/best.pt ]; then
    say "SKIP stage 10 scoring: checkpoints/medium_1m_8k/best.pt does not exist"
else
    # The capacity gap at 8,508 steps, both arms in one call so they share the
    # draw exactly -- the same construction as stage 6, one row down.
    if fits 3600 "stage 10 common"; then
        say "stage 10: medium_1m_8k and small_1m_matched on the common protocol at T=0.6"
        $PY -u scripts/compare_checkpoints.py --no-baseline \
            --only medium_1m_8k --only small_1m_matched \
            --eval-n 2000 --eval-k 20 --temperature 0.6 --top-p 1.0 \
            --out "$LOGS/comparison_common_t06_cap8k.json" \
            --dump-outcomes "$LOGS/outcomes_common_t06_cap8k" \
            > "$LOGS/stage10_common.log" 2>&1
        say "stage 10 common exit=$?"
        for metric in recovery structure; do
            suffix=""; [ "$metric" = structure ] && suffix="_structure"
            $PY -u scripts/band_analysis.py --dumps "$LOGS/outcomes_common_t06_cap8k" \
                --k 20 --order generation --metric $metric \
                --out "$LOGS/band_common_t06_cap8k${suffix}.json" \
                > "$LOGS/stage10_band${suffix}.log" 2>&1
        done
        say "stage 10 band tables exit=$?"
    fi
    # The pre-registered number needs the k=60 ladder on the large protocol,
    # where small_1m_matched's own dump already exists from block 1 as
    # s1m_8k_t06.jsonl, scored with these exact settings.
    if fits 9000 "stage 10 k=60"; then
        say "stage 10: medium_1m_8k at T=0.6, k=60, large protocol"
        $PY -u scripts/compare_checkpoints.py --no-baseline --only medium_1m_8k \
            --eval-n 2400 --min-heavy-atoms 30 --eval-k 60 \
            --temperature 0.6 --top-p 1.0 --max-oversample 12 \
            --out "$LOGS/comparison_k60_cap8k.json" \
            --dump-outcomes "$LOGS/outcomes_cap8k" \
            > "$LOGS/stage10_k60.log" 2>&1
        say "stage 10 k=60 exit=$?"
        D="$LOGS/outcomes_cap8k/medium_1m_8k.jsonl"
        $PY -u scripts/miss_anatomy.py --dump "$D" --k 60 \
            --out "$LOGS/miss_anatomy_cap8k.json" > "$LOGS/stage10_anatomy.log" 2>&1
        $PY -u scripts/budget_curve.py --anatomy "$LOGS/miss_anatomy_cap8k.json" \
            --dump "$D" --k 60 --out "$LOGS/budget_curve_cap8k.json" \
            > "$LOGS/stage10_curve.log" 2>&1
        say "stage 10 analyses exit=$?"
    fi
fi

say "=== stage 10 done, $(( $(remaining) / 60 )) min to spare ==="
