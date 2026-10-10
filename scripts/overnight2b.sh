#!/usr/bin/env bash
# Follow-on to overnight2.sh, launched alongside it.
#
# overnight2.sh turned out to have hours to spare: the full shard built in 11
# minutes and the 100k run is going at 0.98 s/step. This spends that slack on
# the one point the fixed-compute curve is missing honestly.
#
# The curve wants 100k, 1M and the full corpus all trained for 8,508 steps.
# 100k is configs/small.yaml, already on disk. The full corpus is overnight2's
# stage 3. The 1M point could be read off the existing small_1m curve at step
# 8,508, but that run's cosine was set for 21,117 steps, so its learning rate
# was still high there and it is not comparable with runs whose schedule
# completed. This run removes the confound.
#
# It cannot be folded into overnight2.sh because that script is executing, and
# bash reads a script incrementally by byte offset: editing a running script
# makes the shell execute garbage. So it waits for the driver to exit instead.
set -u

cd "$(dirname "$0")/.."
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src
LOGS=results/overnight2
mkdir -p "$LOGS"

DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-11 08:45" "+%s")
ANALYSIS_SECONDS=3600

say() { echo "[$(date '+%m-%d %H:%M:%S')] (2b) $*" | tee -a "$LOGS/driver.log"; }
remaining() { echo $(( DEADLINE_EPOCH - $(date "+%s") )); }

while pgrep -f "overnight2.sh" >/dev/null; do sleep 120; done
say "=== follow-on start, $(( $(remaining) / 60 )) minutes to deadline ==="

needed=$(( 4*3600 + 1800 + ANALYSIS_SECONDS ))
if [ "$(remaining)" -gt "$needed" ]; then
    say "stage 6: small_1m_matched -- 8,508 steps on the 1M shard"
    $PY -u scripts/run_experiment.py \
        --config configs/small_1m_matched.yaml \
        --eval-n 2000 --budget molecules --no-baseline \
        --note "8M, 1M shard, 8508 steps -- de-confounded middle of the fixed-compute curve" \
        > "$LOGS/stage6_small_1m_matched.log" 2>&1
    say "stage 6 exit=$?, $(( $(remaining) / 60 )) minutes left"

    say "stage 7: re-running the common protocol with every checkpoint"
    $PY -u scripts/compare_checkpoints.py --eval-n 2000 \
        --out results/overnight2/comparison.json \
        > "$LOGS/stage7_comparison.log" 2>&1
    say "stage 7 exit=$?"

    say "stage 8: re-running the scaffold probe"
    $PY -u scripts/scaffold_probe.py --eval-n 1000 \
        --out results/overnight2/scaffold_probe.json \
        > "$LOGS/stage8_scaffold.log" 2>&1
    say "stage 8 exit=$?"
else
    say "stage 6 SKIPPED: $(( $(remaining) / 60 )) minutes left, needs $(( needed / 60 ))"
fi

say "=== follow-on done, $(( $(remaining) / 60 )) minutes to spare ==="
