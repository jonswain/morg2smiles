#!/bin/bash
# Night 7c: the 50+ cell job 4's registration needs.
#
# docs/overnight-2026-10-20.md prices the final full-ChEMBL run by applying the
# 1M shard's per-band deficit cut from 1.21 to 3.00 passes to the full shard's
# measured cell. At 50-64 heavy atoms that cut is 41.2% -- read off 127 queries
# of the 30+ protocol, which is the sample size behind two of this project's
# overturned nulls.
#
# The dedicated 50+ protocol has 893 queries, and night 7b puts small_full_1p2
# on it. small_1m_matched is already there from night 6. The missing cell is
# small_1m, the 3.00-passes end of the transition, without which the deficit
# cut at 50+ still rests on 127 queries however well-powered the other two are.
#
# One generation pass, same invocation as night 6 stage 11 and night 7b:
# --eval-n 1000 --min-heavy-atoms 50 --eval-k 60 -T 0.6 --top-p 1.0
# --max-oversample 10.
set -u

cd "$(dirname "$0")/.." || exit 1
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src:.
LOGS=results/overnight7c
mkdir -p "$LOGS"

DEADLINE_EPOCH=$(date -j -f "%Y-%m-%d %H:%M" "2026-10-21 08:00" "+%s")

caffeinate -dimsu -w $$ &

say() { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOGS/driver.log"; }
remaining() { echo $(($DEADLINE_EPOCH - $(date "+%s"))); }

say "=== night 7c start, $(( $(remaining) / 60 )) min to deadline ==="

if [ "$(remaining)" -lt 5400 ]; then
    say "SKIP: $(( $(remaining) / 60 )) min left, needs 90"
    exit 0
fi

if [ ! -f checkpoints/small_1m/best.pt ]; then
    say "SKIP: checkpoints/small_1m/best.pt does not exist"
    exit 0
fi

say "stage 1: small_1m on the 50+ protocol, k=60, T=0.6"
$PY -u scripts/compare_checkpoints.py --no-baseline --only small_1m \
    --eval-n 1000 --min-heavy-atoms 50 --eval-k 60 \
    --temperature 0.6 --top-p 1.0 --max-oversample 10 \
    --out "$LOGS/comparison_50plus_small_1m.json" \
    --dump-outcomes "$LOGS/outcomes_50plus_small_1m" \
    > "$LOGS/stage1_50plus.log" 2>&1
say "stage 1 exit=$?"

dump="$LOGS/outcomes_50plus_small_1m/small_1m.jsonl"
if [ -f "$dump" ]; then
    say "stage 2: miss_anatomy at k=60"
    $PY -u scripts/miss_anatomy.py --dump "$dump" --k 60 \
        --bands 50-54,55-59,60-64,all \
        --out "$LOGS/miss_anatomy_50plus_small_1m.json" \
        > "$LOGS/stage2_anatomy.log" 2>&1
    say "stage 2 exit=$?"
fi

# ---------------------------------------------------------------- stage 3
# The three cells together: the deficit cut per doubling of passes at 50+, on
# 893 queries, and what it predicts for the 3-pass full-ChEMBL run.
say "stage 3: the 50+ transition, and job 4's registration"
$PY - <<'PYEOF' 2>&1 | tee -a "$LOGS/driver.log"
import json
import math
from pathlib import Path

cells = {
    "1M @1.21 passes": "results/overnight7b/miss_anatomy_50plus_matched.json",
    "1M @3.00 passes": "results/overnight7c/miss_anatomy_50plus_small_1m.json",
    "full @1.21 passes": "results/overnight7b/miss_anatomy_50plus_full_1p2.json",
}
missing = [name for name, path in cells.items() if not Path(path).exists()]
if missing:
    print("cannot complete: missing", ", ".join(missing))
    raise SystemExit(0)

bands = {name: json.load(open(path))["bands"] for name, path in cells.items()}
order = ["50-54", "55-59", "60-64", "all"]

print(f"{'band':8s} {'n':>5s} {'1M@1.21':>9s} {'1M@3.0':>9s} {'defcut':>8s} "
      f"{'full@1.21':>10s} {'pred@3.0':>9s}")
rows = []
for band in order:
    cell = bands["full @1.21 passes"].get(band)
    if cell is None:
        continue
    n = cell["n_queries"]
    a = bands["1M @1.21 passes"][band]["recovery_at_k"]["60"]
    c = bands["1M @3.00 passes"][band]["recovery_at_k"]["60"]
    d = cell["recovery_at_k"]["60"]
    cut = (c - a) / (1 - a) if a < 1 else float("nan")
    pred = 1 - (1 - d) * (1 - cut)
    print(f"{band:8s} {n:5d} {a:9.4f} {c:9.4f} {100 * cut:7.1f}% {d:10.4f} {pred:9.4f}")
    rows.append({"band": band, "n": n, "pred_3_passes": pred, "deficit_cut": cut})

dbl = math.log2(1881996 / 900917)
all_a = bands["1M @1.21 passes"]["all"]["recovery_at_k"]["60"]
all_d = bands["full @1.21 passes"]["all"]["recovery_at_k"]["60"]
print()
print(f"f' at 50+, on {bands['full @1.21 passes']['all']['n_queries']} queries: "
      f"{100 * (all_d - all_a) / dbl:+.2f} points per doubling")
print("night 7's 30+ protocol read this on 127 queries as +18.52.")
Path("results/overnight7c/job4_registration.json").write_text(
    json.dumps({"rows": rows, "f_prime_50plus_per_doubling": (all_d - all_a) / dbl}, indent=2)
)
print("wrote results/overnight7c/job4_registration.json")
PYEOF
say "stage 3 exit=$?"

say "=== night 7c done, $(( $(remaining) / 60 )) min to spare ==="
