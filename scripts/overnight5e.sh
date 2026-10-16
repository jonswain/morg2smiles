#!/usr/bin/env bash
# Night 5, fifth part -- re-open count fingerprints where they could matter.
#
#  11  count_fp_100k and its binary twin on the large protocol   ~30 min
#
# Night 3 trained `count_fp_100k` -- identical to `small_100k` but for
# `counts: true` -- and closed the question: 0.5890 against 0.5890 on the common
# protocol, p = 0.32. Tonight's whole lesson is that the common protocol
# averages away anything that acts on one part of the size distribution, and a
# count fingerprint is a candidate for exactly that. Stage 0d found that above
# 35 heavy atoms about one recovery in eight is a *different* molecule with the
# same folded binary fingerprint, and counts are the cheapest way to make a
# fingerprint pin a large molecule harder.
#
# Two readings, and the second is the point:
#
#   * recovery by band. The count model's oracle demands an exact *count*
#     match, which is a strictly harder target than a bit match, so parity on
#     recovery is already a win for counts and a loss is not conclusive.
#   * the collision rate among its hits, from `miss_anatomy.py`. That one is
#     not confounded by the harder target: it asks, of the molecules this model
#     scored as recovered, how many were the query's own.
#
# The protocol's fingerprint-unseen flags come from the *binary* checkpoint
# either way -- `compare_checkpoints.py` fixes them from the first present run
# before `--only` -- so both rows describe the same queries.
set -u
cd "$(dirname "$0")/.."
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src:.
LOGS=results/overnight5
mkdir -p "$LOGS/outcomes_large_countfp"
DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-17 11:30" "+%s")

caffeinate -dimsu -w $$ &

say() { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOGS/driver.log"; }
remaining() { echo $(( DEADLINE_EPOCH - $(date "+%s") )); }

say "=== night 5e start, $(( $(remaining) / 60 )) min to 11:30 ==="

for RUN in count_fp_100k small_100k; do
    if [ "$(remaining)" -lt 1200 ]; then
        say "SKIP stage 11 $RUN: $(( $(remaining) / 60 )) min left, needs 20"
        continue
    fi
    say "stage 11: $RUN on the large protocol"
    $PY -u scripts/compare_checkpoints.py --no-baseline --only "$RUN" \
        --eval-n 2400 --min-heavy-atoms 30 \
        --out "$LOGS/comparison_large_countfp_$RUN.json" \
        --dump-outcomes "$LOGS/outcomes_large_countfp" \
        > "$LOGS/stage11_large_$RUN.log" 2>&1
    say "stage 11 $RUN exit=$?"
done

say "=== night 5e done, $(( $(remaining) / 60 )) min to spare ==="
