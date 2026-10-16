#!/usr/bin/env bash
# Night 5 -- 2026-10-16 into 2026-10-17. The working-day items from the revised
# plan in docs/overnight-2026-10-15.md, re-sized after measuring the error bar
# *inside* each size band.
#
#   1  size-weighted mix, seed 1 -- 8,508 steps on the 100k shard   ~3 h
#   2  size-weighted mix, seed 2                                    ~3 h
#   3  score 3 baseline seeds + 2 mix seeds on a large-molecule
#      protocol: 2,400 molecules of 30+ heavy atoms                 ~2.5 h
#   4  score both mix seeds on the common protocol                  ~35 min
#
# Why two seeds and a second protocol, when the plan said one run on the common
# protocol: scripts/band_analysis.py on night 4's three variance seeds shows the
# between-seed sd inside the 30-39 heavy-atom band is 1.84 points, not the 0.75
# measured over the whole protocol, because the band holds only 568 of the 1,956
# queries. A single run against a single baseline would need about 4 points
# there to mean anything. Two seeds per arm and a protocol drawn entirely from
# large molecules bring that to roughly 1.5, which an experiment worth running
# can clear.
#
# Stage 3 scores all five checkpoints in one call because the 2M-fingerprint
# index is shared and costs ~20 min on its own.
#
# One job at a time. Each stage checks it can finish before the deadline, set
# early enough to leave the write-up and the commit inside the window.
set -u
cd "$(dirname "$0")/.."
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src
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

say "=== night 5 start, git $(git rev-parse --short HEAD), $(( $(remaining) / 60 )) min to 10:30 ==="

# 8,508 steps at up to 1.45 s/step is 3.4 h; max_hours 3.6 is the backstop.
# Seeds 1 and 2 match configs/variance_s1.yaml and variance_s2.yaml, so each
# arm of the comparison shares an initialisation with its baseline.
for S in 1 2; do
    if fits 13500 "stage $S"; then
        say "stage $S: size-weighted mix seed $S, 8,508 steps, 30+ heavy atoms x3"
        $PY -u scripts/run_experiment.py --config configs/size_mix_s$S.yaml \
            --eval-n 2000 --budget molecules --no-baseline \
            --note "8M, 100k shard, 8508 steps, seed $S -- 3x over-sampling of 30+ heavy atoms" \
            > "$LOGS/stage${S}_size_mix_s$S.log" 2>&1
        say "stage $S exit=$?"
    fi
done

# The large-molecule protocol. Drawn from the same clean pool as the common
# protocol and with the same seed, but restricted to molecules of 30+ heavy
# atoms, of which the pool holds 17,633. The retrieval baseline is skipped: it
# costs a nearest-neighbour pass over 2M training molecules and nothing in this
# experiment is compared against it.
LARGE=""
for R in variance_s1 variance_s2 variance_s3 size_mix_s1 size_mix_s2; do
    [ -f "checkpoints/$R/best.pt" ] && LARGE="$LARGE --only $R"
done
if [ -n "$LARGE" ] && fits 10800 "stage 3"; then
    say "stage 3: large-molecule protocol (2,400 molecules, 30+ heavy atoms)$LARGE"
    $PY -u scripts/compare_checkpoints.py --no-baseline $LARGE \
        --eval-n 2400 --min-heavy-atoms 30 \
        --out "$LOGS/comparison_large.json" --dump-outcomes "$LOGS/outcomes_large" \
        > "$LOGS/stage3_large.log" 2>&1
    say "stage 3 exit=$?"
fi

# The common protocol too, so the mix can be read against every other run in
# the project's one comparable table -- including what it costs on the small
# molecules it de-emphasises, which the large protocol cannot see.
COMMON=""
for R in size_mix_s1 size_mix_s2; do
    [ -f "checkpoints/$R/best.pt" ] && COMMON="$COMMON --only $R"
done
if [ -n "$COMMON" ] && fits 3600 "stage 4"; then
    say "stage 4: common protocol$COMMON"
    $PY -u scripts/compare_checkpoints.py --no-baseline $COMMON \
        --out "$LOGS/comparison_size_mix.json" --dump-outcomes "$LOGS/outcomes_common" \
        > "$LOGS/stage4_common.log" 2>&1
    say "stage 4 exit=$?"
fi

say "=== night 5 done, $(( $(remaining) / 60 )) min to spare ==="
