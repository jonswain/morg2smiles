#!/usr/bin/env bash
# Night 4 -- 2026-10-15 into 2026-10-16. Executes the "new, and cheap" section
# of the revised plan in docs/overnight-2026-10-14.md.
#
#   1  decode sweep on small_1m, tuned on a disjoint set      ~45 min
#   2  variance seed 1  -- 8,508 steps on the 100k shard      ~2.9 h
#   3  variance seed 2                                        ~2.9 h
#   4  variance seed 3                                        ~2.9 h
#   5  score all three seeds on the common protocol           ~1 h
#   6  verify the swept decode setting on the common protocol ~35 min
#
# Stages 2-4 are the point of the night: three runs identical but for
# train.seed, so every comparison in this repository can finally carry an error
# bar. Stage 5 scores them in one call because the 2M-fingerprint index costs
# ~20 min and is shared.
#
# One job at a time. Each stage checks it can finish before the deadline, set
# so the machine is idle well before its owner is back at 08:30.
set -u
cd "$(dirname "$0")/.."
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src
LOGS=results/overnight4
mkdir -p "$LOGS"
DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-16 07:50" "+%s")

caffeinate -dimsu -w $$ &

say() { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOGS/driver.log"; }
remaining() { echo $(( DEADLINE_EPOCH - $(date "+%s") )); }
fits() {
    if [ "$(remaining)" -lt "$1" ]; then
        say "SKIP $2: $(( $(remaining) / 60 )) min left, needs $(( $1 / 60 ))"
        return 1
    fi
}

say "=== night 4 start, git $(git rev-parse --short HEAD), $(( $(remaining) / 60 )) min to 07:50 ==="

if fits 4200 "stage 1"; then
    say "stage 1: decode sweep on small_1m"
    $PY -u scripts/decode_sweep.py --n 400 \
        --temperatures 0.7,0.8,0.9,1.0,1.1 --top-ps 1.0,0.95,0.9 \
        > "$LOGS/stage1_decode_sweep.log" 2>&1
    say "stage 1 exit=$?"
fi

# 8,508 steps at up to 1.45 s/step is 3.4 h; max_hours 3.6 is the backstop.
for S in 1 2 3; do
    if fits 13500 "stage $((S+1))"; then
        say "stage $((S+1)): variance seed $S, 8,508 steps"
        $PY -u scripts/run_experiment.py --config configs/variance_s$S.yaml \
            --eval-n 2000 --budget molecules --no-baseline \
            --note "8M, 100k shard, 8508 steps, seed $S -- training variance sample $S of 3" \
            > "$LOGS/stage$((S+1))_variance_s$S.log" 2>&1
        say "stage $((S+1)) exit=$?"
    fi
done

# Score whichever seeds finished, in one call: the protocol is derived from
# every present checkpoint either way, so --only narrows only the scoring.
PRESENT=""
for S in 1 2 3; do
    [ -f "checkpoints/variance_s$S/best.pt" ] && PRESENT="$PRESENT --only variance_s$S"
done
if [ -n "$PRESENT" ] && fits 4800 "stage 5"; then
    say "stage 5: scoring$PRESENT"
    $PY -u scripts/compare_checkpoints.py --no-baseline $PRESENT \
        --out "$LOGS/comparison_variance.json" --dump-outcomes "$LOGS/outcomes" \
        > "$LOGS/stage5_score.log" 2>&1
    say "stage 5 exit=$?"
fi

# Verify the swept setting on the common protocol -- the set it was *not*
# tuned on. Only worth the time if the sweep actually beat the default.
if [ -f "$LOGS/decode_sweep.json" ] && fits 3000 "stage 6"; then
    read -r T P GAIN <<< "$($PY -c "
import json
d = json.load(open('$LOGS/decode_sweep.json'))
b = d['best_by_consensus_rec20']
print(b['temperature'], b['top_p'], d.get('best_vs_default_points', 0.0))
")"
    if [ "$(echo "$GAIN > 0.3" | bc -l)" = "1" ]; then
        say "stage 6: verifying T=$T top_p=$P on the common protocol (tuning gain $GAIN pts)"
        $PY -u scripts/compare_checkpoints.py --no-baseline --only small_1m \
            --temperature "$T" --top-p "$P" \
            --out "$LOGS/comparison_decode.json" \
            > "$LOGS/stage6_verify.log" 2>&1
        say "stage 6 exit=$?"
    else
        say "stage 6 skipped: sweep gained only $GAIN points, not worth verifying"
    fi
fi

say "=== night 4 done, $(( $(remaining) / 60 )) min to spare ==="
