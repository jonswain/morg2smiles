#!/usr/bin/env bash
# Night 5, third part -- does the size mix keep paying as the dose rises?
#
#   8  size mix at threshold 35, factor 6 (8,508 steps)   ~3 h
#   9  score it on the large protocol and the common one  ~25 min
#
# The first arm over-sampled 30+ heavy atoms threefold and moved the large
# protocol by +2.75 points above 35 heavy atoms, +0.46 at 30-34, +1.97 above
# 50. Where the gain is, the exposure was not: 30-34 took a third of every
# batch and did not respond. This run gives 35+ molecules 58.8% of draws
# instead of 32.5% and asks whether the response keeps growing.
#
# One seed, deliberately: the previous commit's arithmetic says a third seed of
# the *same* dose would shrink the error bar by only a tenth of a point, because
# the baseline arm already has three. Spending the same three hours on a larger
# expected effect is the better buy.
set -u
cd "$(dirname "$0")/.."
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src:.
LOGS=results/overnight5
mkdir -p "$LOGS"
DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-17 11:00" "+%s")

caffeinate -dimsu -w $$ &

say() { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOGS/driver.log"; }
remaining() { echo $(( DEADLINE_EPOCH - $(date "+%s") )); }
fits() {
    if [ "$(remaining)" -lt "$1" ]; then
        say "SKIP $2: $(( $(remaining) / 60 )) min left, needs $(( $1 / 60 ))"
        return 1
    fi
}

say "=== night 5c start, $(( $(remaining) / 60 )) min to 11:00 ==="

if fits 14400 "stage 8"; then
    say "stage 8: size mix at threshold 35, factor 6, 8,508 steps"
    $PY -u scripts/run_experiment.py --config configs/size_mix_t35.yaml \
        --eval-n 2000 --budget molecules --no-baseline \
        --note "8M, 100k shard, 8508 steps, seed 1 -- 6x over-sampling of 35+ heavy atoms" \
        > "$LOGS/stage8_size_mix_t35.log" 2>&1
    say "stage 8 exit=$?"
fi

if [ -f "checkpoints/size_mix_t35/best.pt" ] && fits 2400 "stage 9"; then
    say "stage 9: scoring size_mix_t35 on the large protocol"
    $PY -u scripts/compare_checkpoints.py --no-baseline --only size_mix_t35 \
        --eval-n 2400 --min-heavy-atoms 30 \
        --out "$LOGS/comparison_large_t35.json" \
        --dump-outcomes "$LOGS/outcomes_large" \
        > "$LOGS/stage9_large_t35.log" 2>&1
    say "stage 9 exit=$?"
    say "stage 9b: scoring size_mix_t35 on the common protocol"
    $PY -u scripts/compare_checkpoints.py --no-baseline --only size_mix_t35 \
        --out "$LOGS/comparison_common_t35.json" \
        --dump-outcomes "$LOGS/outcomes_common" \
        > "$LOGS/stage9b_common_t35.log" 2>&1
    say "stage 9b exit=$?"
fi

say "=== night 5c done, $(( $(remaining) / 60 )) min to spare ==="
