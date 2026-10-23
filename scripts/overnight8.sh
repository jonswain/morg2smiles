#!/usr/bin/env bash
# Night 8 -- item 2 of docs/next-steps-2026-10-19.md, the whole of it.
#
# Twenty-four hours, Saturday ~11:00 to Sunday 11:00, deadline set at 11:00 to
# leave the machine free by midday. The item is the third point on the 100k
# step arm at 52,500 steps, and it is the job that picks the final run's step
# budget: 6 passes if saturation has not appeared by here, 3 if it has.
#
# The pre-registration is in the config, as usual:
#   configs/small_100k_52k.yaml   52,500 steps, 20.0 h -- interval 0.88-0.95
#
# Priority order, and why it differs from night 7's. The training is 20.0 h of
# a 24 h window at small_100k_long's measured 1.373 s/step -- not the 18.4 h
# item 2 was priced with, which used count_fp_100k's 1.198 and a different
# fingerprint config. That leaves about 3 h, so this night cannot be a queue of
# stages that each assume the last one finished early. Training is the only
# irreplaceable thing in the window; the k=60 scoring is 80 minutes and can be
# run any time afterwards against the checkpoint on disk. So every stage after
# stage 1 is guarded tightly and skips without complaint, and the script is
# re-runnable: stages whose output exists already are skipped, so running it
# again on Sunday finishes whatever the clock cut off.
set -u
cd "$(dirname "$0")/.."
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src:.
LOGS=results/overnight8
mkdir -p "$LOGS/outcomes_100k_52k"
DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-25 11:00" "+%s")

caffeinate -dimsu -w $$ &

say() { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOGS/driver.log"; }
remaining() { echo $(( DEADLINE_EPOCH - $(date "+%s") )); }
fits() {
    if [ "$(remaining)" -lt "$1" ]; then
        say "SKIP $2: $(( $(remaining) / 60 )) min left, needs $(( $1 / 60 ))"
        return 1
    fi
    return 0
}
stopped_because() {
    $PY -c "
import json
r = json.load(open('checkpoints/$1/record.json'))
print(r.get('stopped_because', '?'), '/', round(r.get('total_seconds', 0) / 3600, 2), 'h')
" 2>/dev/null || echo '?'
}

say "=== night 8 start, git $(git rev-parse --short HEAD), $(( $(remaining) / 60 )) min to Sun 11:00 ==="

# ---------------------------------------------------------------- stage 1
# The measurement. 52,500 steps on the 100k shard, 74.05 passes.
#
# Needs 20.0 h at 1.373 s/step; the guard asks for 22 h so that a run which
# would hit max_hours and leave its cosine schedule unfinished is not started
# at all. An incomplete run here is worse than no run: the pre-registration is
# written against a complete 52,500-step run and would not apply to it.
if [ -f checkpoints/small_100k_52k/best.pt ]; then
    say "SKIP stage 1 training: checkpoints/small_100k_52k/best.pt exists"
elif fits 79200 "stage 1"; then
    say "stage 1: small_100k_52k, 8.0M params, 100k shard, 52,500 steps"
    $PY -u scripts/run_experiment.py --config configs/small_100k_52k.yaml \
        --eval-n 500 --budget molecules --no-baseline \
        --note "8.0M, 100k shard, 52500 steps -- item 2, the step-saturation third point" \
        > "$LOGS/stage1_small_100k_52k.log" 2>&1
    say "stage 1 exit=$?, $(stopped_because small_100k_52k)"
fi

# ---------------------------------------------------------------- stage 2
# The pre-registered number. The invocation is night 6's score() exactly, which
# is what produced the arm's other two cells, so all three are prefix-to-prefix
# comparable: --eval-n 2400 --min-heavy-atoms 30 --eval-k 60 -T 0.6 --top-p 1.0
# --max-oversample 12, large protocol, k=60.
if [ ! -f checkpoints/small_100k_52k/best.pt ]; then
    say "SKIP stage 2: checkpoints/small_100k_52k/best.pt does not exist"
elif [ -f "$LOGS/comparison_k60_s100k_52k_t06.json" ]; then
    say "SKIP stage 2: comparison already on disk"
elif fits 5400 "stage 2"; then
    say "stage 2: small_100k_52k at T=0.6, k=60, large protocol"
    $PY -u scripts/compare_checkpoints.py --no-baseline --only small_100k_52k \
        --eval-n 2400 --min-heavy-atoms 30 --eval-k 60 \
        --temperature 0.6 --top-p 1.0 --max-oversample 12 \
        --out "$LOGS/comparison_k60_s100k_52k_t06.json" \
        --dump-outcomes "$LOGS/outcomes_100k_52k" \
        > "$LOGS/stage2_k60.log" 2>&1
    say "stage 2 exit=$?"
    $PY -c "
import json
d = json.load(open('$LOGS/comparison_k60_s100k_52k_t06.json'))
print(json.dumps(d, indent=2)[:4000])
" >> "$LOGS/driver.log" 2>&1
fi

# ---------------------------------------------------------------- stage 3
# The band table on both metrics, and the deficit curve. Rule 3 of methodology
# section 7, re-affirmed on night 7b: read every size claim on
# structure_accuracy as well as recovery, because recovery can overstate a
# slope by 43% at 60-64 when the low cell sits on the floor.
D="$LOGS/outcomes_100k_52k/small_100k_52k.jsonl"
if [ ! -f "$D" ]; then
    say "SKIP stage 3: no dump at $D"
elif fits 2400 "stage 3"; then
    for metric in recovery structure; do
        suffix=""; [ "$metric" = structure ] && suffix="_structure"
        $PY -u scripts/band_analysis.py --dumps "$LOGS/outcomes_100k_52k" \
            --k 60 --order generation --metric $metric \
            --out "$LOGS/band_k60_s100k_52k${suffix}.json" \
            > "$LOGS/stage3_band${suffix}.log" 2>&1
    done
    say "stage 3 band tables exit=$?"
    $PY -u scripts/miss_anatomy.py --dump "$D" --k 60 \
        --out "$LOGS/miss_anatomy_s100k_52k.json" > "$LOGS/stage3_anatomy.log" 2>&1
    $PY -u scripts/budget_curve.py --anatomy "$LOGS/miss_anatomy_s100k_52k.json" \
        --dump "$D" --k 60 --out "$LOGS/budget_curve_s100k_52k.json" \
        > "$LOGS/stage3_curve.log" 2>&1
    say "stage 3 analyses exit=$?"
fi

# ---------------------------------------------------------------- stage 4
# The step exponent refit with the third point included -- the question item 2
# exists to answer. step_curve.py reads the in-training traces, so this costs
# no GPU and is the cheapest stage here, which is why it runs last: it can also
# be run on Sunday in thirty seconds if the clock takes it.
if [ ! -f checkpoints/small_100k_52k/history.json ]; then
    say "SKIP stage 4: no history for small_100k_52k"
elif fits 900 "stage 4"; then
    say "stage 4: step exponent refit including the 52,500-step point"
    $PY -u scripts/step_curve.py --runs small_100k_52k,small_100k_long,small_1m \
        --out "$LOGS/step_curve_with_52k.json" > "$LOGS/stage4_step_curve.log" 2>&1
    say "stage 4 exit=$?"
fi

say "=== night 8 done, $(( $(remaining) / 60 )) min to spare ==="
