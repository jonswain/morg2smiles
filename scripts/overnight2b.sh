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
#
# Usage: scripts/overnight2b.sh <pid of the running overnight2.sh>
set -u

# Which process to wait for, by pid, because matching on the name does not
# work: `pgrep -f overnight2.sh` matches any command line *containing* that
# string, which includes every watcher shell that greps for the driver -- so
# the wait below would have hung on a watcher of mine rather than on the
# driver, and stage 6 would simply never have started. A pid is unambiguous.
DRIVER_PID="${1:?pass the pid of the running overnight2.sh}"

cd "$(dirname "$0")/.."
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src
LOGS=results/overnight2
mkdir -p "$LOGS"

DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-11 08:45" "+%s")
ANALYSIS_SECONDS=3600

# Hold the machine awake for this script's own lifetime. overnight2.sh runs its
# own caffeinate bound to its pid, which dies with it -- exactly when this
# script starts working, so without one of its own stage 6 would be the first
# thing tonight to run with the machine free to sleep. Night 1 showed what that
# costs: suspension does not advance perf_counter, and it does not advance the
# training either.
caffeinate -dimsu -w $$ &

say() { echo "[$(date '+%m-%d %H:%M:%S')] (2b) $*" | tee -a "$LOGS/driver.log"; }
remaining() { echo $(( DEADLINE_EPOCH - $(date "+%s") )); }

# How long stage 6 will take, measured rather than guessed.
#
# A matched-compute point is only worth having if it reaches the exact step the
# other runs stopped at, so a truncated stage 6 is worth nothing and the guard
# has to be right. The first version of this guard assumed 4 hours, which at
# the observed 1.35 s/step would have skipped a 2.6-hour run for want of time
# that existed. overnight2's stage 3 runs the same model for the same 8,508
# steps, so its recorded wall time is a direct measurement of this one's. Take
# it from the leaderboard, with 20% headroom for a slower shard, and fall back
# to the pessimistic 4 hours if the record is missing.
estimate_training_seconds() {
    $PY - <<'PYEOF' 2>/dev/null || echo $(( 4 * 3600 ))
import json
from pathlib import Path

path = Path("results/leaderboard.jsonl")
seconds = None
for line in path.read_text().splitlines():
    if not line.strip():
        continue
    rec = json.loads(line)
    if rec.get("config_file", "").endswith("small_full.yaml"):
        seconds = rec.get("total_seconds")
print(int(seconds * 1.2) if seconds else 4 * 3600)
PYEOF
}

while kill -0 "$DRIVER_PID" 2>/dev/null; do sleep 120; done
say "=== follow-on start (driver $DRIVER_PID gone), $(( $(remaining) / 60 )) minutes to deadline ==="

training=$(estimate_training_seconds)
needed=$(( training + 1800 + ANALYSIS_SECONDS ))
say "stage 6 budget: $(( training / 60 )) min training (from stage 3's wall time), $(( needed / 60 )) min total"

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
