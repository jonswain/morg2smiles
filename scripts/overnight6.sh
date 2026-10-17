#!/usr/bin/env bash
# Weekend of 2026-10-17, block 1 -- what actually moves the budget curve's
# exponent. Four scoring runs, no training. Deadline 01:45.
#
#  1  variance_s1       at T=0.6, k=60   ~75 min
#  2  small_100k_long   at T=0.6, k=60   ~75 min
#  3  small_1m_matched  at T=0.6, k=60   ~75 min
#  4  variance_s1       at T=1.0, k=60   ~75 min
#
# WHY. Night 5 reported that "the exponent is the one quantity capacity moves",
# from an exponent of 0.094 for `variance_s1` against 0.303 for `small_1m`.
# Both models are 7.95M parameters. They differ in training corpus (90,682
# against 900,917 molecules) and in step count (8,508 against 21,117), so the
# contrast cannot be capacity, and the claim as published is mislabelled. The
# 2x2 that separates the two candidates is already trained:
#
#                   8,508 steps        21,117 steps
#     100k corpus   variance_s1        small_100k_long
#       1M corpus   small_1m_matched   small_1m  (measured: b = 0.303)
#
# Runs 1-3 fill it in. Run 1 also re-measures the known cell at k=60 rather
# than reading it off a k=20 ladder, so all four cells share a protocol.
#
# PRE-REGISTERED, on the mechanism rather than on a curve fit. Night 5's
# concentration result says recovery is governed by which fingerprints the
# learned conditional can reach at all. Seeing ten times as many distinct
# molecules should widen that set; re-reading the same 90,682 molecules three
# times as often should not. So the dial should be the corpus:
#
#   * small_1m_matched  (1M corpus, few steps)  -> b >= 0.25, near small_1m
#   * small_100k_long   (100k corpus, many steps) -> b <= 0.15, near variance_s1
#
# If it comes out the other way round the dial is training length, and that
# matters immediately for block 2: `medium_1m_full` shares its step budget with
# `small_1m`, so a training-length dial would make a flat capacity result
# uninformative rather than negative. Either way the published claim gets
# rewritten under the right label.
#
# Run 4 settles a pre-registration already in the repository, from
# docs/overnight-2026-10-16.md item 1b: `variance_s1` at T=1.0, 35+ heavy
# atoms, rec@60 lands 0.21-0.26 in miss_anatomy.py's first-k-slots units,
# where the deficit power law fitted to this arm's own k<=20 rungs predicts
# 0.232, independence predicts 0.47 and the recovery-multiplier extrapolation
# predicts 0.28. Mind the units: this arm reads 0.1634 at k=20 in those units
# against the protocol's 0.1885, and conflating the two is what voided the
# last pre-registration.
set -u
cd "$(dirname "$0")/.."
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src:.
LOGS=results/overnight6
mkdir -p "$LOGS/outcomes_exponent_2x2"
DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-18 01:45" "+%s")

caffeinate -dimsu -w $$ &

say() { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOGS/driver.log"; }
remaining() { echo $(( DEADLINE_EPOCH - $(date "+%s") )); }
fits() {  # fits <seconds> <label>
    if [ "$(remaining)" -lt "$1" ]; then
        say "SKIP $2: $(( $(remaining) / 60 )) min left, needs $(( $1 / 60 ))"
        return 1
    fi
    return 0
}

say "=== block 1 start, git $(git rev-parse --short HEAD), $(( $(remaining) / 60 )) min to 01:45 ==="

score() {  # score <run> <temperature> <tag>
    local run=$1 temp=$2 tag=$3
    fits 4800 "$tag" || return 0
    say "$tag: $run at T=$temp, k=60, large protocol"
    $PY -u scripts/compare_checkpoints.py --no-baseline --only "$run" \
        --eval-n 2400 --min-heavy-atoms 30 --eval-k 60 \
        --temperature "$temp" --top-p 1.0 --max-oversample 12 \
        --out "$LOGS/comparison_k60_$tag.json" \
        --dump-outcomes "$LOGS/outcomes_exponent_2x2" \
        > "$LOGS/${tag}_score.log" 2>&1
    say "$tag score exit=$?"
    # Rename the dump, since two arms here are the same checkpoint at
    # different temperatures and would otherwise overwrite each other.
    [ -f "$LOGS/outcomes_exponent_2x2/$run.jsonl" ] && \
        mv "$LOGS/outcomes_exponent_2x2/$run.jsonl" "$LOGS/outcomes_exponent_2x2/$tag.jsonl"
    $PY -u scripts/miss_anatomy.py --dump "$LOGS/outcomes_exponent_2x2/$tag.jsonl" --k 60 \
        --out "$LOGS/miss_anatomy_$tag.json" > "$LOGS/${tag}_anatomy.log" 2>&1
    say "$tag anatomy exit=$?"
    $PY -u scripts/size_bias.py --dump "$LOGS/outcomes_exponent_2x2/$tag.jsonl" --k 60 \
        --out "$LOGS/size_bias_$tag.json" > "$LOGS/${tag}_size_bias.log" 2>&1
    $PY -u scripts/budget_curve.py --anatomy "$LOGS/miss_anatomy_$tag.json" \
        --dump "$LOGS/outcomes_exponent_2x2/$tag.jsonl" --k 60 \
        --out "$LOGS/budget_curve_$tag.json" > "$LOGS/${tag}_curve.log" 2>&1
    say "$tag curve exit=$?"
}

score variance_s1      0.6 "s100k_8k_t06"
score small_100k_long  0.6 "s100k_21k_t06"
score small_1m_matched 0.6 "s1m_8k_t06"
score variance_s1      1.0 "s100k_8k_t10"

say "=== block 1 done, $(( $(remaining) / 60 )) min to spare ==="

# Block 2 chains off this one regardless of what block 1 found: the capacity
# arm is worth running on its own terms, and 16 h of GPU should not wait for a
# human to read a table.
nohup scripts/overnight6b.sh > "$LOGS/nohup6b.log" 2>&1 &
