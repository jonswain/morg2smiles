#!/usr/bin/env bash
# Night 3 -- 2026-10-14 into 2026-10-15. Stages 2 onward; stage 1 (the
# re-score that gates everything) runs from overnight3_rescore.sh and this
# waits for it.
#
#   2  failure taxonomy + likelihood ranking on small_1m       ~20 min
#   3  bit-flip probe on small_1m                              ~30 min
#   4  constant-epoch point: small_100k_3ep, 2,127 steps       ~60 min
#      + common-protocol scoring (--only)                      ~30 min
#   5  count fingerprints, cheap signal: 8,508 steps on 100k   ~3.3 h
#      + common-protocol scoring + binary re-judge             ~40 min
#
# One job at a time. Every stage checks it can finish before the deadline,
# which is set so the machine is idle by the time its owner is back at 07:00.
set -u
cd "$(dirname "$0")/.."
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src
LOGS=results/overnight3
mkdir -p "$LOGS"
DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-15 06:40" "+%s")

caffeinate -dimsu -w $$ &

say() { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOGS/driver.log"; }
remaining() { echo $(( DEADLINE_EPOCH - $(date "+%s") )); }
fits() {  # fits SECONDS NAME
    if [ "$(remaining)" -lt "$1" ]; then
        say "SKIP $2: $(( $(remaining) / 60 )) min left, needs $(( $1 / 60 ))"
        return 1
    fi
}

say "=== night 3 driver start, git $(git rev-parse --short HEAD), $(( $(remaining) / 60 )) min to 06:40 ==="
while ! grep -q "stage 1 rescore exit" "$LOGS/driver.log"; do sleep 30; done
say "stage 1 finished; continuing"

if fits 1800 "stage 2"; then
    say "stage 2: failure analysis"
    $PY -u scripts/failure_analysis.py > "$LOGS/stage2_failure_analysis.log" 2>&1
    say "stage 2 exit=$?"
fi

if fits 2700 "stage 3"; then
    say "stage 3: bit-flip probe"
    $PY -u scripts/bitflip_probe.py > "$LOGS/stage3_bitflip.log" 2>&1
    say "stage 3 exit=$?"
fi

if fits 7200 "stage 4"; then
    say "stage 4: small_100k_3ep, 2,127 steps"
    $PY -u scripts/run_experiment.py --config configs/small_100k_3ep.yaml \
        --eval-n 2000 --budget molecules --no-baseline \
        --note "8M, 100k shard, 3 epochs = 2127 steps -- constant-epoch corpus point vs small_1m" \
        > "$LOGS/stage4_small_100k_3ep.log" 2>&1
    say "stage 4 train exit=$?"
    if [ -f checkpoints/small_100k_3ep/best.pt ]; then
        $PY -u scripts/compare_checkpoints.py --no-baseline --only small_100k_3ep \
            --out "$LOGS/comparison_100k_3ep.json" --dump-outcomes "$LOGS/outcomes" \
            > "$LOGS/stage4_score.log" 2>&1
        say "stage 4 score exit=$?"
    fi
fi

# 8,508 steps at up to 1.45 s/step is 3.4 h (max_hours 4.0), plus ~45 min of scoring.
if fits 16800 "stage 5"; then
    say "stage 5: count_fp_100k, 8,508 steps"
    $PY -u scripts/run_experiment.py --config configs/count_fp_100k.yaml \
        --eval-n 2000 --budget molecules --no-baseline \
        --note "8M, 100k shard, 8508 steps, COUNT fingerprints -- input-representation test vs small_100k" \
        > "$LOGS/stage5_count_fp_100k.log" 2>&1
    say "stage 5 train exit=$?"
    if [ -f checkpoints/count_fp_100k/best.pt ] && fits 2400 "stage 5 scoring"; then
        $PY -u scripts/compare_checkpoints.py --no-baseline --only count_fp_100k \
            --out "$LOGS/comparison_count_fp.json" --dump-outcomes "$LOGS/outcomes" \
            > "$LOGS/stage5_score.log" 2>&1
        say "stage 5 score exit=$?"
        $PY -u scripts/rejudge_binary.py "$LOGS/outcomes/count_fp_100k.jsonl" \
            > "$LOGS/stage5_rejudge.log" 2>&1
        say "stage 5 rejudge exit=$?"
    fi
fi

say "=== night 3 driver done, $(( $(remaining) / 60 )) min to spare ==="
