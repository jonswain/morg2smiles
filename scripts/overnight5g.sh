#!/usr/bin/env bash
# Night 5, seventh part -- does the mix's bill grow with cooling too?
#
#  13  three arms on the COMMON protocol at T=0.6        ~12 min each
#
# Stage 10 found the mix and the cooled decoder stack: above 35 heavy atoms the
# mix is worth +3.28 at T=0.6 against +2.75 at T=1.0. The whole verdict on the
# mix is an exchange rate, and its denominator -- what small molecules pay --
# has only ever been measured at T=1.0, where it was -3.11 below 24 atoms and
# -2.90 at 25-29. If the cost grows with cooling as the gain did, the trade is
# unchanged; if it does not, the mix is a better deal at the adopted setting
# than this document says.
#
# Three arms, not five: the two mix seeds and one baseline seed. The cost bands
# are where the between-seed sd is smallest (0.23 points below 29 atoms at
# T=1.0), so one reference seed is enough there, and `arm_table.py` borrows the
# reference's sd for a single-seed arm and says so in its note.
set -u
cd "$(dirname "$0")/.."
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src:.
LOGS=results/overnight5
mkdir -p "$LOGS/outcomes_common_t06_arms"
DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-17 11:55" "+%s")

caffeinate -dimsu -w $$ &

say() { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOGS/driver.log"; }
remaining() { echo $(( DEADLINE_EPOCH - $(date "+%s") )); }

say "=== night 5g start, $(( $(remaining) / 60 )) min to 11:55 ==="

for RUN in size_mix_s1 variance_s1 size_mix_s2; do
    if [ "$(remaining)" -lt 900 ]; then
        say "SKIP stage 13 $RUN: $(( $(remaining) / 60 )) min left, needs 15"
        continue
    fi
    say "stage 13: $RUN on the common protocol at T=0.6"
    $PY -u scripts/compare_checkpoints.py --no-baseline --only "$RUN" \
        --temperature 0.6 --top-p 1.0 \
        --out "$LOGS/comparison_common_t06_$RUN.json" \
        --dump-outcomes "$LOGS/outcomes_common_t06_arms" \
        > "$LOGS/stage13_common_t06_$RUN.log" 2>&1
    say "stage 13 $RUN exit=$?"
done

say "=== night 5g done, $(( $(remaining) / 60 )) min to spare ==="
