#!/usr/bin/env bash
# Night 5, fourth part -- do the training-side and decode-side gains stack?
#
#  10  every arm on the large protocol at T=0.6, one run at a time   ~2 h
#
# Tonight produced two independent ways to move large molecules, and both were
# measured against a baseline that did not have the other. The size mix was
# scored at the protocol's T=1.0; the temperature result is one checkpoint
# (`small_1m`) at four temperatures. So the project has +4.60 points above 35
# heavy atoms from exposure and +6.96 from cooling, and no reason to believe
# the sum. Cooling may already be recovering the molecules the mix recovers --
# both work by spending more of the budget on fewer, likelier strings -- in
# which case the second intervention is free of charge and worth nothing.
#
# Scoring every arm at 0.6 answers it directly: the mix-vs-baseline gap at the
# decode setting anyone would actually ship. One `compare_checkpoints.py` call
# per run, so a run that does not fit before the deadline costs only itself,
# and the order is interleaved -- one mix seed, one baseline seed, then the
# rest -- so an early stop still leaves a comparison rather than one arm.
#
# `size_mix_t35` is deliberately *not* in this list. Two arms of three and two
# seeds carry a 0.86-point error bar above 35 heavy atoms, which is what the
# registered prediction needs; a sixth run would spend 25 minutes on a
# single-seed arm this comparison does not use.
set -u
cd "$(dirname "$0")/.."
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src:.
LOGS=results/overnight5
mkdir -p "$LOGS/outcomes_large_t06_arms"
DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-17 11:15" "+%s")

caffeinate -dimsu -w $$ &

say() { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOGS/driver.log"; }
remaining() { echo $(( DEADLINE_EPOCH - $(date "+%s") )); }

say "=== night 5d start, $(( $(remaining) / 60 )) min to 11:15 ==="

for RUN in size_mix_s1 variance_s1 size_mix_s2 variance_s2 variance_s3; do
    if [ ! -f "checkpoints/$RUN/best.pt" ]; then
        say "SKIP stage 10 $RUN: no checkpoint"
        continue
    fi
    if [ "$(remaining)" -lt 1800 ]; then
        say "SKIP stage 10 $RUN: $(( $(remaining) / 60 )) min left, needs 30"
        continue
    fi
    say "stage 10: $RUN on the large protocol at T=0.6"
    $PY -u scripts/compare_checkpoints.py --no-baseline --only "$RUN" \
        --eval-n 2400 --min-heavy-atoms 30 --temperature 0.6 \
        --out "$LOGS/comparison_large_t06_$RUN.json" \
        --dump-outcomes "$LOGS/outcomes_large_t06_arms" \
        > "$LOGS/stage10_large_t06_$RUN.log" 2>&1
    say "stage 10 $RUN exit=$?"
done

say "=== night 5d done, $(( $(remaining) / 60 )) min to spare ==="
