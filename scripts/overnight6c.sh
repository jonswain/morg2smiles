#!/usr/bin/env bash
# Weekend of 2026-10-17, blocks 3-5. Chained off block 2, which may land
# anywhere between ~13:00 and 18:00 Sunday, so this runs in priority order
# against one hard deadline rather than in time slots: whatever does not fit
# is skipped, cheapest-and-sharpest first.
#
#  5b matched-step trace against small_1m          seconds (reads history.json)
#  6  score medium_1m_full on both protocols        ~3 h   (the capacity arm)
#  7  size_mix_t35 on the common protocol at T=0.6  ~20 min
#  8  the reverse-direction mix, and score it       ~3.7 h
#
# Stage 5b is free and is the reading block 1 showed we need, so it goes first.
# Stage 6 is what block 2 was for, so it goes next. Stage 7 is twenty minutes
# for a number the project has been quoting wrong: night 5 found the first
# dose's exchange rate roughly halves when the decoder is cooled (2.34 small
# molecules per large one at T=1.0, 1.28 at T=0.6), and the second dose's 4.4
# was also measured hot. Stage 8 is the out-of-sample test of the exposure law
# and is the one that should be dropped if the clock has gone against us,
# because it needs training and the other two do not.
set -u
cd "$(dirname "$0")/.."
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src:.
LOGS=results/overnight6
mkdir -p "$LOGS/outcomes_capacity" "$LOGS/outcomes_common_t06_capacity" "$LOGS/outcomes_rev"
DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-19 06:30" "+%s")

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

say "=== blocks 3-5 start, $(( $(remaining) / 60 )) min to Mon 06:30 ==="

# ---- stage 5b: the matched-step trace ------------------------------------
# Pre-registered after block 1, which showed that nothing here is converged at
# 21,117 steps: 2.5x the steps still buys +0.34 rec@20. So a flat endpoint
# comparison between a 7.95M and a 15.1M model at a matched step count cannot
# tell "capacity does not pay" from "the bigger model is further from its own
# asymptote at the same step". The two training traces can. Both runs use
# data/shards/1m and evaluate on its valid split every 1,500 steps, so for this
# one pair matched_steps.py's usual caveat -- each run scored on its own shard
# -- does not apply, and the only variable left between the columns is the
# parameter count. Registered: medium_1m_full above small_1m at every matched
# step and still rising at the last, or capacity is not paying at this budget.
# Costs nothing: it reads two history.json files. Runs even if block 2 was
# truncated, since a partial trace is still a trace.
if [ -f checkpoints/medium_1m_full/history.json ]; then
    say "stage 5b: matched-step trace, medium_1m_full against small_1m"
    $PY -u scripts/matched_steps.py medium_1m_full small_1m \
        > "$LOGS/stage5b_matched_steps.md" 2>&1
    say "stage 5b exit=$?"
else
    say "SKIP stage 5b: checkpoints/medium_1m_full/history.json does not exist"
fi

# ---- stage 6: the capacity arm -------------------------------------------
if [ ! -f checkpoints/medium_1m_full/best.pt ]; then
    say "SKIP stage 6: checkpoints/medium_1m_full/best.pt does not exist"
elif fits 10800 "stage 6"; then
    # The band location, on the protocol where both arms can be compared. Both
    # runs in one call so they share the draw exactly.
    say "stage 6: medium_1m_full and small_1m on the common protocol at T=0.6"
    $PY -u scripts/compare_checkpoints.py --no-baseline \
        --only medium_1m_full --only small_1m \
        --eval-n 2000 --eval-k 20 --temperature 0.6 --top-p 1.0 \
        --out "$LOGS/comparison_common_t06_capacity.json" \
        --dump-outcomes "$LOGS/outcomes_common_t06_capacity" \
        > "$LOGS/stage6_common.log" 2>&1
    say "stage 6 common exit=$?"
    for metric in recovery structure; do
        suffix=""; [ "$metric" = structure ] && suffix="_structure"
        $PY -u scripts/band_analysis.py --dumps "$LOGS/outcomes_common_t06_capacity" \
            --k 20 --order generation --metric $metric \
            --out "$LOGS/band_common_t06_capacity${suffix}.json" \
            > "$LOGS/stage6_band${suffix}.log" 2>&1
    done
    say "stage 6 band tables exit=$?"

    # The exponent, which needs the k=60 ladder. small_1m's own k=60 dump
    # already exists from night 5 (results/overnight5/outcomes_large_k60).
    if fits 9000 "stage 6 k=60"; then
        say "stage 6: medium_1m_full at T=0.6, k=60, large protocol"
        $PY -u scripts/compare_checkpoints.py --no-baseline --only medium_1m_full \
            --eval-n 2400 --min-heavy-atoms 30 --eval-k 60 \
            --temperature 0.6 --top-p 1.0 --max-oversample 12 \
            --out "$LOGS/comparison_k60_capacity.json" \
            --dump-outcomes "$LOGS/outcomes_capacity" \
            > "$LOGS/stage6_k60.log" 2>&1
        say "stage 6 k=60 exit=$?"
        D="$LOGS/outcomes_capacity/medium_1m_full.jsonl"
        $PY -u scripts/miss_anatomy.py --dump "$D" --k 60 \
            --out "$LOGS/miss_anatomy_capacity.json" > "$LOGS/stage6_anatomy.log" 2>&1
        $PY -u scripts/size_bias.py --dump "$D" --k 60 \
            --out "$LOGS/size_bias_capacity.json" > "$LOGS/stage6_size_bias.log" 2>&1
        $PY -u scripts/budget_curve.py --anatomy "$LOGS/miss_anatomy_capacity.json" \
            --dump "$D" --k 60 --out "$LOGS/budget_curve_capacity.json" \
            > "$LOGS/stage6_curve.log" 2>&1
        say "stage 6 analyses exit=$?"
        # Does capacity reach fingerprints small_1m cannot, or the same ones
        # more often? The concentration result's direct test.
        # seed_union.py takes one directory and names within it, so small_1m's
        # night-5 k=60 dump is copied alongside. Both were scored on the large
        # protocol's same 2,400-molecule draw, which the script verifies.
        cp results/overnight5/outcomes_large_k60/small_1m.jsonl "$LOGS/outcomes_capacity/"
        $PY -u scripts/seed_union.py --dumps "$LOGS/outcomes_capacity" \
            --runs medium_1m_full,small_1m \
            --k 60 --out "$LOGS/seed_union_capacity.json" \
            > "$LOGS/stage6_union.log" 2>&1
        say "stage 6 union exit=$?"
    fi
fi

# ---- stage 7: the second dose's bill, cooled ------------------------------
if fits 2400 "stage 7"; then
    say "stage 7: size_mix_t35 on the common protocol at T=0.6"
    $PY -u scripts/compare_checkpoints.py --no-baseline --only size_mix_t35 \
        --eval-n 2000 --eval-k 20 --temperature 0.6 --top-p 1.0 \
        --out "$LOGS/comparison_common_t06_t35.json" \
        --dump-outcomes results/overnight5/outcomes_common_t06_arms \
        > "$LOGS/stage7_t35.log" 2>&1
    say "stage 7 exit=$?"
    # Re-run the arm and exposure tables over the four-arm directory, which now
    # holds baseline, both x3 seeds and the x6 dose at the adopted temperature.
    for metric in recovery structure; do
        suffix=""; [ "$metric" = structure ] && suffix="_structure"
        $PY -u scripts/band_analysis.py --dumps results/overnight5/outcomes_common_t06_arms \
            --k 20 --order generation --metric $metric \
            --out "$LOGS/band_common_t06_doses${suffix}.json" \
            > "$LOGS/stage7_band${suffix}.log" 2>&1
    done
    $PY -u scripts/exposure_response.py --bands "$LOGS/band_common_t06_doses.json" \
        --reference "baseline=variance_s1" \
        --mix "mix3x30=size_mix_s1,size_mix_s2@checkpoints/size_mix_s1/record.json" \
        --mix "mix6x35=size_mix_t35@checkpoints/size_mix_t35/record.json" \
        --out "$LOGS/exposure_response_common_t06_doses.json" \
        > "$LOGS/stage7_exposure.log" 2>&1
    say "stage 7 tables exit=$?"
fi

# ---- stage 8: the exposure law, run backwards -----------------------------
if fits 16200 "stage 8"; then
    say "stage 8: size_mix_rev, threshold 30 factor 1/3, 8,508 steps"
    $PY -u scripts/run_experiment.py --config configs/size_mix_rev.yaml \
        --eval-n 2000 --budget molecules --no-baseline \
        --note "8M, 100k shard, 8508 steps, seed 1 -- 1/3 DE-weighting of 30+ heavy atoms, the reverse-direction control" \
        > "$LOGS/stage8_size_mix_rev.log" 2>&1
    say "stage 8 exit=$?"
    if [ -f checkpoints/size_mix_rev/best.pt ] && fits 3000 "stage 8 scoring"; then
        say "stage 8: scoring size_mix_rev on the common protocol at T=0.6"
        $PY -u scripts/compare_checkpoints.py --no-baseline --only size_mix_rev \
            --eval-n 2000 --eval-k 20 --temperature 0.6 --top-p 1.0 \
            --out "$LOGS/comparison_common_t06_rev.json" \
            --dump-outcomes "$LOGS/outcomes_rev" \
            > "$LOGS/stage8_score.log" 2>&1
        say "stage 8 scoring exit=$?"
    fi
fi

# ---- stage 9: a third point on the corpus axis ----------------------------
# Only worth anything if block 1 says the corpus is the dial, but it is 75
# minutes and it turns a two-point axis into three at matched steps:
# 90,682 (variance_s1), 900,917 (small_1m_matched) and 1,881,996 molecules
# (small_full), all at 8,508 steps and all 8M parameters.
if fits 5400 "stage 9"; then
    say "stage 9: small_full at T=0.6, k=60, large protocol"
    $PY -u scripts/compare_checkpoints.py --no-baseline --only small_full \
        --eval-n 2400 --min-heavy-atoms 30 --eval-k 60 \
        --temperature 0.6 --top-p 1.0 --max-oversample 12 \
        --out "$LOGS/comparison_k60_s188m_8k_t06.json" \
        --dump-outcomes "$LOGS/outcomes_exponent_2x2" \
        > "$LOGS/stage9_score.log" 2>&1
    say "stage 9 exit=$?"
    mv "$LOGS/outcomes_exponent_2x2/small_full.jsonl" \
       "$LOGS/outcomes_exponent_2x2/s188m_8k_t06.jsonl" 2>/dev/null
    $PY -u scripts/miss_anatomy.py --dump "$LOGS/outcomes_exponent_2x2/s188m_8k_t06.jsonl" \
        --k 60 --out "$LOGS/miss_anatomy_s188m_8k_t06.json" > "$LOGS/stage9_anatomy.log" 2>&1
    $PY -u scripts/budget_curve.py --anatomy "$LOGS/miss_anatomy_s188m_8k_t06.json" \
        --dump "$LOGS/outcomes_exponent_2x2/s188m_8k_t06.jsonl" --k 60 \
        --out "$LOGS/budget_curve_s188m_8k_t06.json" > "$LOGS/stage9_curve.log" 2>&1
    say "stage 9 analyses exit=$?"
fi

say "=== blocks 3-5 done, $(( $(remaining) / 60 )) min to spare ==="
