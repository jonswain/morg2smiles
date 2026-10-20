#!/bin/bash
# Night 7b: f' at 50+ heavy atoms, on 893 queries instead of 127.
#
# Night 7's headline reads f' = +22.09 points per doubling on 2,321 queries,
# but its 50-64 band rests on 127 -- the sample size that produced two of this
# project's overturned nulls (entries 13 and 15 of docs/retractions.md). Night
# 6 built a dedicated 50+ protocol for exactly this reason and scored
# small_1m_matched on it, which is tonight's constant-passes partner. So
# scoring small_full_1p2 on that same protocol costs one generation pass and
# turns the thinnest row of tonight's table into its best-powered one.
#
# The invocation is night 6 stage 11's exactly -- --eval-n 1000
# --min-heavy-atoms 50 --eval-k 60 -T 0.6 --top-p 1.0 --max-oversample 10,
# giving 893 fp_unseen queries -- because a capped draw and an uncapped one are
# different protocols (methodology.md section 4) and the cap here is 10, not
# the large protocol's 12. Prefix-to-prefix or it is nothing.
#
# This is also job 4's prerequisite: docs/overnight-2026-10-20.md argues the
# final full-ChEMBL run cannot be headlined on rec@60 "all" because it is
# predicted at 0.92, and that the 50+ band is where the headroom is. That
# argument needs the 50+ cell measured on a protocol with power, not inferred
# from 127 queries.
set -u

cd "$(dirname "$0")/.." || exit 1
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src:.
LOGS=results/overnight7b
mkdir -p "$LOGS"

DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-21 08:00" "+%s")

caffeinate -dimsu -w $$ &

say() { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOGS/driver.log"; }
remaining() { echo $(($DEADLINE_EPOCH - $(date "+%s"))); }
fits() {
    local need=$1 what=$2 left
    left=$(remaining)
    if [ "$left" -lt "$need" ]; then
        say "SKIP $what: ${left}s left, needs ${need}s"
        return 1
    fi
    return 0
}

say "=== night 7b start, $(( $(remaining) / 60 )) min to deadline ==="

# ---------------------------------------------------------------- stage 1
# The measurement. small_1m_matched is already dumped at
# results/overnight6/outcomes_50plus/small_1m_matched.jsonl under this exact
# invocation, so only the new checkpoint needs generating.
if [ ! -f checkpoints/small_full_1p2/best.pt ]; then
    say "SKIP stage 1: checkpoints/small_full_1p2/best.pt does not exist"
elif fits 7200 "stage 1"; then
    say "stage 1: small_full_1p2 on the 50+ protocol, k=60, T=0.6"
    $PY -u scripts/compare_checkpoints.py --no-baseline --only small_full_1p2 \
        --eval-n 1000 --min-heavy-atoms 50 --eval-k 60 \
        --temperature 0.6 --top-p 1.0 --max-oversample 10 \
        --out "$LOGS/comparison_50plus_full_1p2.json" \
        --dump-outcomes "$LOGS/outcomes_50plus_1p2" \
        > "$LOGS/stage1_50plus.log" 2>&1
    say "stage 1 exit=$?"
fi

# ---------------------------------------------------------------- stage 2
# rec@60 in the registered convention, both cells, one tool. Night 7 nearly
# scored its registration against a baseline from the other convention; doing
# both sides here with miss_anatomy is the fix, not a formality.
for tag in full_1p2 matched; do
    case $tag in
        full_1p2) dump="$LOGS/outcomes_50plus_1p2/small_full_1p2.jsonl" ;;
        matched) dump="results/overnight6/outcomes_50plus/small_1m_matched.jsonl" ;;
    esac
    if [ ! -f "$dump" ]; then
        say "SKIP stage 2 $tag: no dump at $dump"
        continue
    fi
    say "stage 2 $tag: miss_anatomy at k=60"
    # Every query here is 50+, so the default band list is mostly empty rows;
    # these split the 50-64 window instead, which is the resolution the 30+
    # protocol could not afford at n=127.
    $PY -u scripts/miss_anatomy.py --dump "$dump" --k 60 \
        --bands 50-54,55-59,60-64,all \
        --out "$LOGS/miss_anatomy_50plus_$tag.json" \
        > "$LOGS/stage2_anatomy_$tag.log" 2>&1
    say "stage 2 $tag exit=$?"
done

# ---------------------------------------------------------------- stage 3
# The comparison, printed so the morning does not have to compute it.
if [ -f "$LOGS/miss_anatomy_50plus_full_1p2.json" ] &&
    [ -f "$LOGS/miss_anatomy_50plus_matched.json" ]; then
    say "stage 3: f' at 50+, 893 queries"
    $PY - <<'PYEOF' 2>&1 | tee -a "$LOGS/driver.log"
import json
import math

new = json.load(open("results/overnight7b/miss_anatomy_50plus_full_1p2.json"))["bands"]
old = json.load(open("results/overnight7b/miss_anatomy_50plus_matched.json"))["bands"]
dbl = math.log2(1881996 / 900917)

print(f"corpus doublings {dbl:.4f}  (900,917 -> 1,881,996 at 1.2087 passes)")
print(f"{'band':8s} {'n':>5s} {'0.9M':>8s} {'1.88M':>8s} {'delta':>8s} {'per dbl':>8s} {'SE':>6s}")
for band, cell in new.items():
    if band not in old:
        continue
    n = cell["n_queries"]
    a = old[band]["recovery_at_k"]["60"]
    c = cell["recovery_at_k"]["60"]
    se = 100 * math.sqrt(max(c * (1 - c), 1e-9) / n)
    print(
        f"{band:8s} {n:5d} {a:8.4f} {c:8.4f} "
        f"{100 * (c - a):+8.2f} {100 * (c - a) / dbl:+8.2f} {se:6.2f}"
    )
print()
print("night 7's 30+ protocol put the 50-64 band at 0.0630 -> 0.2598 on n=127,")
print("+18.52 points per doubling. Compare the 50+ rows above.")
PYEOF
    say "stage 3 exit=$?"
fi

say "=== night 7b done, $(( $(remaining) / 60 )) min to spare ==="
