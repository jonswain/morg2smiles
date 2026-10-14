#!/usr/bin/env bash
# Night 3, stage 1 -- the gate. Re-score every checkpoint on the common
# protocol with adaptive top-up (max_oversample 10), dumping every judged
# candidate for the failure analysis that follows.
set -u
cd "$(dirname "$0")/.."
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src
LOGS=results/overnight3
mkdir -p "$LOGS"
caffeinate -dimsu -w $$ &
echo "[$(date '+%m-%d %H:%M:%S')] stage 1 rescore start" >> "$LOGS/driver.log"
$PY -u scripts/compare_checkpoints.py --no-baseline --max-oversample 10 \
    --out "$LOGS/comparison_topup.json" --dump-outcomes "$LOGS/outcomes" \
    > "$LOGS/stage1_rescore.log" 2>&1
echo "[$(date '+%m-%d %H:%M:%S')] stage 1 rescore exit=$?" >> "$LOGS/driver.log"
