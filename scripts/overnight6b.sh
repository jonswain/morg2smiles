#!/usr/bin/env bash
# Weekend of 2026-10-17, block 2 -- the capacity arm, full length. Deadline
# 18:00 Sunday for the training; blocks 3-5 chain off it.
#
#  5  medium_1m_full: 15.1M params, 1M shard, 21,117 steps or 16 h  ~16 h
#
# WHY. This is the only route night 5 left standing. Three of the four ways of
# spending more on a hard fingerprint are measured and dead -- more models,
# splitting a budget across models, and re-weighting the training mix, which is
# a transfer rather than a gain -- and the fourth, widening k, is now priced and
# runs out at about 40 heavy atoms. What is left is changing what the model can
# represent, which on night 5's own account is changing *which fingerprints the
# conditional can reach at all*: above 50 heavy atoms 52% of queries draw no
# exact preimage at any budget, and a differently initialised copy of the model
# draws from the same reachable set.
#
# The design is one variable. `small_1m` is this same corpus and this same step
# budget at 7.96M parameters; `medium_1m_full` is 15.12M. Nothing else moves.
#
# PRE-REGISTERED, two independent locations:
#
#   * Band location. If the limit is capacity the gain concentrates above 35
#     heavy atoms and the 0-24 band moves by less than a point. A gain that is
#     flat across bands is not the size cliff getting better, and would say the
#     cliff is in the fingerprint or the data rather than in the model.
#   * The exponent. Night 5 found the deficit power law's exponent at 35+ to be
#     0.094 for an 8M model on the 100k corpus and 0.303 for an 8M model on the
#     1M corpus. Block 1 says which of corpus and training length did that. If
#     capacity is a dial at all, `medium_1m_full` should exceed `small_1m`'s
#     0.303 on the same protocol at the same temperature in the same fitting
#     window. If it lands at 0.303, capacity moves the level and not the slope,
#     and the budget route and the capacity route are different routes after
#     all.
#
# Honest about the truncation risk: the stub measured 2.62 s/step, and this
# project's step-time estimates have been wrong by 2x in both directions. The
# config caps at 16 h, so a slow run stops short of 21,117 steps and the step
# it reached must be reported beside every number -- an unmatched-step
# comparison with a stated step count, not a matched one.
set -u
cd "$(dirname "$0")/.."
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src:.
LOGS=results/overnight6
DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-18 18:00" "+%s")

caffeinate -dimsu -w $$ &

say() { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOGS/driver.log"; }
remaining() { echo $(( DEADLINE_EPOCH - $(date "+%s") )); }

say "=== block 2 start, $(( $(remaining) / 60 )) min to 18:00 ==="

if [ "$(remaining)" -lt 10800 ]; then
    say "SKIP stage 5: $(( $(remaining) / 60 )) min left, a 15M run needs hours not minutes"
else
    say "stage 5: medium_1m_full, 15.1M params, 1M shard, up to 21,117 steps / 16 h"
    $PY -u scripts/run_experiment.py --config configs/medium_1m_full.yaml \
        --eval-n 2000 --budget molecules --no-baseline \
        --note "15.1M, 1M shard, 21117 steps -- the capacity arm against small_1m, same corpus and step budget" \
        > "$LOGS/stage5_medium_1m_full.log" 2>&1
    say "stage 5 exit=$?"
    if [ -f checkpoints/medium_1m_full/record.json ]; then
        say "stage 5 stopped at: $($PY -c "import json;d=json.load(open('checkpoints/medium_1m_full/record.json'));print(d.get('best_checkpoint'),'/',d.get('stopped_because'),'/',round(d.get('total_seconds',0)/3600,2),'h')")"
    fi
fi

say "=== block 2 done, $(( $(remaining) / 60 )) min to spare ==="

nohup scripts/overnight6c.sh > "$LOGS/nohup6c.log" 2>&1 &
