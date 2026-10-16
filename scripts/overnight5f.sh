#!/usr/bin/env bash
# Night 5, sixth part -- measure the budget curve instead of extrapolating it.
#
#  12  small_1m at T=0.6, k=60, on the large protocol's molecules   ~60 min
#
# Everything this project says about the brute-force route comes from
# extrapolating the 10 -> 20 step of a 20-slot list, and tonight two accounts
# that both fit the measured range disagree about where it goes:
#
#   * independent draws. The size factorisation says each 20 samples yield
#     about 1.9 right-sized proposals above 35 heavy atoms, each an exact
#     preimage with probability 0.107. Independence gives
#     rec@k = 1 - (1 - 0.107)^(0.095k): 0.191 at k=20 against a measured
#     0.1885, and *0.47 at k=60*.
#   * decaying returns. The measured factors are already falling inside the
#     window -- 1.61 for 5 -> 10, 1.45 for 10 -> 20 -- and extrapolating the
#     last one gives *0.28 at k=60*.
#
# Pre-registered before the run: between 0.26 and 0.36, so the draws are not
# independent and the decoder keeps re-proposing from a shrinking
# neighbourhood. k=60 separates the two accounts by 19 points, which is twelve
# times the between-seed sd of this metric, so one run settles it.
#
# Same molecules as the large protocol (eval-n 2400, min 30 heavy atoms, seed
# 0), so the k=20 prefix of this dump must reproduce the T=0.6 number already
# in hand -- a free check that nothing about the larger budget changed the
# protocol underneath it.
set -u
cd "$(dirname "$0")/.."
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src:.
LOGS=results/overnight5
mkdir -p "$LOGS/outcomes_large_k60"
DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-17 11:50" "+%s")

caffeinate -dimsu -w $$ &

say() { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOGS/driver.log"; }
remaining() { echo $(( DEADLINE_EPOCH - $(date "+%s") )); }

say "=== night 5f start, $(( $(remaining) / 60 )) min to 11:50 ==="

if [ "$(remaining)" -lt 3600 ]; then
    say "SKIP stage 12: $(( $(remaining) / 60 )) min left, needs 60"
else
    say "stage 12: small_1m at T=0.6, k=60, on the large protocol's molecules"
    $PY -u scripts/compare_checkpoints.py --no-baseline --only small_1m \
        --eval-n 2400 --min-heavy-atoms 30 --eval-k 60 \
        --temperature 0.6 --top-p 1.0 --max-oversample 12 \
        --out "$LOGS/comparison_large_k60.json" \
        --dump-outcomes "$LOGS/outcomes_large_k60" \
        > "$LOGS/stage12_large_k60.log" 2>&1
    say "stage 12 exit=$?"

    # Free, from the dump just written: the curve itself, and whether the
    # extra budget bought right-sized proposals or more of the same.
    $PY -u scripts/miss_anatomy.py --dump "$LOGS/outcomes_large_k60/small_1m.jsonl" --k 60 \
        --out "$LOGS/miss_anatomy_large_k60.json" > "$LOGS/stage12_anatomy.log" 2>&1
    say "stage 12 anatomy exit=$?"
    $PY -u scripts/size_bias.py --dump "$LOGS/outcomes_large_k60/small_1m.jsonl" --k 60 \
        --out "$LOGS/size_bias_large_k60.json" > "$LOGS/stage12_size_bias.log" 2>&1
    say "stage 12 size bias exit=$?"
fi

say "=== night 5f done, $(( $(remaining) / 60 )) min to spare ==="
