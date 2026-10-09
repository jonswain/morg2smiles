#!/usr/bin/env bash
# The overnight run of 2026-10-09. Reasoning and results:
# docs/overnight-2026-10-09.md
#
# Runs unattended against a hard deadline, so:
#   * stages are sequential and fail-soft -- a stage that dies does not take the
#     rest of the night with it;
#   * each training run carries its own max_hours cap in its config;
#   * the analysis stages are protected by a deadline check, because an
#     unanalysed checkpoint is worth much less than an analysed one. If a run
#     overruns, the *run* loses its tail, never the analysis.
set -u

cd "$(dirname "$0")/.."
export PYTHONPATH=src
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
LOGS=results/overnight
mkdir -p "$LOGS"

# Everything must be finished by this time. Analysis needs ~75 minutes.
DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-10 09:45" "+%s")
ANALYSIS_SECONDS=4500

say() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOGS/driver.log"; }

remaining() { echo $(( DEADLINE_EPOCH - $(date "+%s") )); }

# A stage only runs if its own cap fits in the time left, with the analysis
# window reserved. The earlier version asked only whether 105 minutes remained,
# which would happily launch a 3.5 h stage with 2 h left -- the stage would then
# run until its cap and the analysis stages would be the thing that got cut.
# Takes the stage's max_hours so the arithmetic is about the stage in hand.
have_time_for_training() {
    local cap_hours="$1"
    local left; left=$(remaining)
    local needed; needed=$(printf "%.0f" "$(echo "$cap_hours * 3600" | bc -l)")
    # Allow one evaluation interval of overshoot: the cap is only tested at an
    # evaluation, so a run stops at its cap plus up to one interval.
    needed=$(( needed + 1800 ))
    [ "$left" -gt $(( ANALYSIS_SECONDS + needed )) ]
}

say "=== overnight start, $(( $(remaining) / 60 )) minutes to deadline ==="
say "machine: $(sysctl -n hw.model), $(sysctl -n hw.ncpu) cores"
say "git: $(git rev-parse --short HEAD)"

# ---- Stage 1: the data variable (8M params, 1M shard, capped at 8.5 h) -----
if have_time_for_training 8.5; then
    say "stage 1: small_1m -- 8M params, 1M shard, data variable"
    $PY -u scripts/run_experiment.py \
        --config configs/small_1m.yaml \
        --eval-n 2000 --budget molecules --no-baseline \
        --note "8M params, 1M shard -- data variable vs small.yaml (100k)" \
        > "$LOGS/run1_small_1m.log" 2>&1
    say "stage 1 exit=$?, $(( $(remaining) / 60 )) minutes left"
else
    say "stage 1 SKIPPED: not enough time"
fi

# ---- Stage 2: the capacity variable (15M params, capped at 3.5 h) ----------
if have_time_for_training 1.75; then
    say "stage 2: medium_1m -- 15M params, 1M shard, capacity variable"
    $PY -u scripts/run_experiment.py \
        --config configs/medium_1m.yaml \
        --eval-n 2000 --budget molecules --no-baseline \
        --note "15M params, 1M shard -- capacity variable vs small_1m" \
        > "$LOGS/run2_medium_1m.log" 2>&1
    say "stage 2 exit=$?, $(( $(remaining) / 60 )) minutes left"
else
    say "stage 2 SKIPPED: not enough time left after stage 1"
fi

# ---- Stage 3: every checkpoint under one identical protocol ----------------
# The per-run numbers come from different eval subsamples and must not be
# compared directly. This re-scores all of them on the same molecules, with the
# same seed, budget and k. The retrieval baseline runs once here rather than
# per-run: indexing is O(train set) and it is already established at exactly
# zero on the fp_unseen slice.
say "stage 3: common evaluation of every checkpoint"
$PY -u scripts/compare_checkpoints.py \
    --eval-n 2000 --seed 0 --budget molecules \
    --out "$LOGS/comparison.json" \
    > "$LOGS/stage3_comparison.log" 2>&1
say "stage 3 exit=$?, $(( $(remaining) / 60 )) minutes left"

# ---- Stage 4: novel-scaffold probe ----------------------------------------
# fp_unseen asks about unseen fingerprints; this asks about unseen *chemotypes*,
# which is the harder question and the one a user would actually care about.
say "stage 4: novel-scaffold generalisation probe"
$PY -u scripts/scaffold_probe.py \
    --eval-n 1000 --seed 0 \
    --out "$LOGS/scaffold_probe.json" \
    > "$LOGS/stage4_scaffold.log" 2>&1
say "stage 4 exit=$?"

say "=== overnight done, $(( $(remaining) / 60 )) minutes to spare ==="
