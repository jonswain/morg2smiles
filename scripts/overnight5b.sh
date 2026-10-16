#!/usr/bin/env bash
# Night 5, second half -- is the best decoder temperature size-dependent?
#
#   5  sweep T on a *large-molecule* tuning set, disjoint from the protocol  ~45 min
#   6  verify the coldest useful setting on the large-molecule protocol      ~70 min
#   7  the same setting on the common protocol, for what it costs small      ~35 min
#
# Night 4 cooled the decoder from 1.0 to 0.6 and gained +1.99 points overall,
# all of it above 30 heavy atoms. Reading its three temperature dumps band by
# band (results/overnight5/band_temperatures.json) shows the gain growing
# monotonically with size -- +0.4 points below 24 atoms, +3.2 in the 30-39
# band, +8.1 at 40-49, +9.8 above 50 -- which suggests the optimum keeps
# falling as molecules get bigger and that 0.6, chosen on a random draw where
# 64% of molecules are under 30 atoms, is too hot for the band that matters.
#
# 0.5 was measured once, on a random tuning draw, and was worse overall. That
# is consistent with both stories: it could be worse everywhere, or worse on
# the small molecules that dominate a random draw while better on the large
# ones. Stage 5 settles it by sweeping where the signal is, on molecules of 30+
# heavy atoms held out of the common protocol, so nothing is tuned on the set
# it is then verified on.
#
# Stage 6 verifies on the 2,400-molecule large protocol, where the same
# comparison carries a ~1-point standard error instead of the 1.7 the common
# protocol's 359 large queries allow.
set -u
cd "$(dirname "$0")/.."
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src:.
LOGS=results/overnight5
mkdir -p "$LOGS"
DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-17 10:30" "+%s")

caffeinate -dimsu -w $$ &

say() { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOGS/driver.log"; }
remaining() { echo $(( DEADLINE_EPOCH - $(date "+%s") )); }
fits() {
    if [ "$(remaining)" -lt "$1" ]; then
        say "SKIP $2: $(( $(remaining) / 60 )) min left, needs $(( $1 / 60 ))"
        return 1
    fi
}

say "=== night 5b start, $(( $(remaining) / 60 )) min to 10:30 ==="

if fits 4500 "stage 5"; then
    say "stage 5: temperature sweep on 500 molecules of 30+ heavy atoms, disjoint from protocol"
    $PY -u scripts/decode_sweep.py --n 500 --min-heavy-atoms 30 \
        --temperatures 0.3,0.4,0.5,0.6,0.7,1.0 --top-ps 1.0 \
        --out "$LOGS/decode_sweep_large.json" \
        > "$LOGS/stage5_sweep_large.log" 2>&1
    say "stage 5 exit=$?"
fi

# Verify on the large protocol: the swept pick, and 0.6 as the incumbent. Both
# arms are the same checkpoint on the same 2,400 molecules, so the comparison
# is paired and sub-point effects are visible.
if [ -f "$LOGS/decode_sweep_large.json" ] && fits 5400 "stage 6"; then
    T=$($PY -c "
import json
d = json.load(open('$LOGS/decode_sweep_large.json'))
print(d['best_by_consensus_rec20']['temperature'])
")
    TEMPS=$($PY -c "
picked = $T
print(' '.join(str(t) for t in dict.fromkeys([picked, 0.6])))
")
    say "stage 6: large protocol at T in [$TEMPS] (sweep picked $T)"
    # Both arms' dumps land in one directory under distinct names, so
    # scripts/band_analysis.py can read them as a paired set.
    mkdir -p "$LOGS/outcomes_large_temps"
    for TEMP in $TEMPS; do
        TAG=$($PY -c "print(str($TEMP).replace('.',''))")
        $PY -u scripts/compare_checkpoints.py --no-baseline --only small_1m \
            --eval-n 2400 --min-heavy-atoms 30 --temperature "$TEMP" \
            --out "$LOGS/comparison_large_t$TAG.json" \
            --dump-outcomes "$LOGS/dump_tmp_t$TAG" \
            > "$LOGS/stage6_large_t$TAG.log" 2>&1
        say "stage 6 (T=$TEMP) exit=$?"
        [ -f "$LOGS/dump_tmp_t$TAG/small_1m.jsonl" ] && \
            mv "$LOGS/dump_tmp_t$TAG/small_1m.jsonl" "$LOGS/outcomes_large_temps/t$TAG.jsonl" && \
            rmdir "$LOGS/dump_tmp_t$TAG"
    done
fi

# What the cold setting costs on the molecules it was not chosen for. The
# large protocol cannot see this: it holds no molecule under 30 heavy atoms.
# Dumped next to symlinks to night 4's three temperature dumps, which are the
# same checkpoint on the same 1,956 molecules, so the four arms form one paired
# set and a size-conditional policy can be evaluated over them without
# generating anything again.
if [ -f "$LOGS/decode_sweep_large.json" ] && fits 3000 "stage 7"; then
    T=$($PY -c "
import json
d = json.load(open('$LOGS/decode_sweep_large.json'))
print(d['best_by_consensus_rec20']['temperature'])
")
    TAG=$($PY -c "print(str($T).replace('.',''))")
    # Night 4's dumps first, so that a sweep landing back on 0.6, 0.7 or 1.0
    # finds the measurement already there instead of repeating it.
    mkdir -p "$LOGS/outcomes_common_temps"
    for PAIR in t06:outcomes_t06 t07:outcomes_decode t10:outcomes_default; do
        NAME=${PAIR%%:*}; DIR=${PAIR##*:}
        [ -f "results/overnight4/$DIR/small_1m.jsonl" ] && \
            ln -sf "../../overnight4/$DIR/small_1m.jsonl" \
                   "$LOGS/outcomes_common_temps/$NAME.jsonl"
    done
    if [ ! -e "$LOGS/outcomes_common_temps/t$TAG.jsonl" ]; then
        say "stage 7: common protocol at T=$T, for the small-molecule cost"
        $PY -u scripts/compare_checkpoints.py --no-baseline --only small_1m \
            --temperature "$T" \
            --out "$LOGS/comparison_common_t$TAG.json" \
            --dump-outcomes "$LOGS/dump_common_t$TAG" \
            > "$LOGS/stage7_common_t$TAG.log" 2>&1
        say "stage 7 exit=$?"
        [ -f "$LOGS/dump_common_t$TAG/small_1m.jsonl" ] && \
            mv "$LOGS/dump_common_t$TAG/small_1m.jsonl" \
               "$LOGS/outcomes_common_temps/t$TAG.jsonl" && \
            rmdir "$LOGS/dump_common_t$TAG"
    else
        say "stage 7 skipped: T=$T is already measured on the common protocol"
    fi
fi

say "=== night 5b done, $(( $(remaining) / 60 )) min to spare ==="
