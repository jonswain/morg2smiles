#!/usr/bin/env bash
# Second unattended night, 2026-10-10.
#
# Last night's experiment varied data and compute together and the write-up
# credited data with all of it. Tonight fixes that: three shard sizes, one
# architecture, one step budget (21,117), so the only thing that differs is how
# many molecules the model saw.
#
#   stage 1  build the full ChEMBL shard, excluding the smaller shards' holdouts
#   stage 2  small_100k_long  21,117 steps on 100k -- matched to the 1M run, so
#            it answers whether the small shard could have got there on compute
#   stage 3  small_full       8,508 steps on all of ChEMBL -- matched to the
#            original small.yaml run, so it is the data contrast at fixed compute
#   stage 4  compare_checkpoints  one common protocol across every model
#   stage 5  scaffold_probe       novel-chemotype generalisation
#
# Sixteen hours available, so the step budgets are chosen to reuse runs already
# on disk rather than repeat them: stage 2 matches small_1m's 21,117 steps and
# stage 3 matches small.yaml's 8,508, both with their cosine horizons set to the
# same budget. Three full-length runs would not have fitted.
#
# Guards, all of which earned their place last night:
#   * max_hours is a real wall clock now, and caffeinate holds the machine awake
#   * max_steps stops a run on the exact step, so compute is genuinely matched
#   * have_time_for_training compares the time left against the stage's own cap
#   * stages are fail-soft and log separately
set -u

cd "$(dirname "$0")/.."
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src
LOGS=results/overnight2
mkdir -p "$LOGS"

DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-11 08:45" "+%s")
ANALYSIS_SECONDS=3600

say() { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOGS/driver.log"; }
remaining() { echo $(( DEADLINE_EPOCH - $(date "+%s") )); }

have_time_for_training() {
    local cap_hours="$1"
    local left; left=$(remaining)
    local needed; needed=$(printf "%.0f" "$(echo "$cap_hours * 3600" | bc -l)")
    needed=$(( needed + 1800 ))
    [ "$left" -gt $(( ANALYSIS_SECONDS + needed )) ]
}

# Keep the machine awake for the whole night. Last night 3.9 h of wall time
# vanished into suspension, which is also why max_hours now uses time.time().
caffeinate -dimsu -w $$ &
say "=== night 2 start, $(( $(remaining) / 60 )) minutes to deadline ==="
say "git: $(git rev-parse --short HEAD)"

# ---- Stage 1: the full shard ----------------------------------------------
if [ -f data/shards/full/meta.json ]; then
    say "stage 1: full shard already built, skipping"
else
    say "stage 1: building full ChEMBL shard (excluding 1m + 100k holdouts)"
    $PY -u -m morg2smiles.data.prepare --subset full \
        --exclude data/shards/1m/valid.smi \
        --exclude data/shards/1m/test.smi \
        --exclude data/shards/100k/valid.smi \
        --exclude data/shards/100k/test.smi \
        > "$LOGS/stage1_prepare_full.log" 2>&1
    say "stage 1 exit=$?, $(( $(remaining) / 60 )) minutes left"
fi

# ---- Stage 2: matched-compute control at 100k ------------------------------
if have_time_for_training 9.0; then
    say "stage 2: small_100k_long -- 21,117 steps on 90,682 molecules"
    $PY -u scripts/run_experiment.py \
        --config configs/small_100k_long.yaml \
        --eval-n 2000 --budget molecules --no-baseline \
        --note "8M, 100k shard, 21117 steps -- matched-compute control vs small_1m" \
        > "$LOGS/stage2_small_100k_long.log" 2>&1
    say "stage 2 exit=$?, $(( $(remaining) / 60 )) minutes left"
else
    say "stage 2 SKIPPED: not enough time"
fi

# ---- Stage 3: the third data point at fixed compute -----------------------
if [ ! -f data/shards/full/meta.json ]; then
    say "stage 3 SKIPPED: full shard was not built"
elif have_time_for_training 4.5; then
    say "stage 3: small_full -- 21,117 steps on all of ChEMBL"
    $PY -u scripts/run_experiment.py \
        --config configs/small_full.yaml \
        --eval-n 2000 --budget molecules --no-baseline \
        --note "8M, full ChEMBL, 21117 steps -- third fixed-compute data point" \
        > "$LOGS/stage3_small_full.log" 2>&1
    say "stage 3 exit=$?, $(( $(remaining) / 60 )) minutes left"
else
    say "stage 3 SKIPPED: not enough time left after stage 2"
fi

# ---- Stage 4+5: analysis ---------------------------------------------------
say "stage 4: common evaluation of every checkpoint"
$PY -u scripts/compare_checkpoints.py --eval-n 2000 \
    --out results/overnight2/comparison.json \
    > "$LOGS/stage4_comparison.log" 2>&1
say "stage 4 exit=$?, $(( $(remaining) / 60 )) minutes left"

say "stage 5: novel-scaffold generalisation probe"
$PY -u scripts/scaffold_probe.py --eval-n 1000 \
    --out results/overnight2/scaffold_probe.json \
    > "$LOGS/stage5_scaffold.log" 2>&1
say "stage 5 exit=$?"

say "=== night 2 done, $(( $(remaining) / 60 )) minutes to spare ==="
