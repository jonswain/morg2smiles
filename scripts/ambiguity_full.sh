#!/bin/bash
# Fingerprint ambiguity on the whole corpus, binary and counts.
#
# Every ambiguity figure in this project is from the 1M shard (950,967
# molecules, train+valid) or from the 11,669-molecule shard that produced the
# retracted 99.97%. The full shard has never been measured, so `report.md`
# section 2.1's "98.6% of molecules are the only molecule with their
# fingerprint" describes roughly half of ChEMBL, and the privacy argument that
# rests on it has only ever been checked at that scale.
#
# Free of GPU: a CPU pass over ~1.99M molecules. Queued behind the common
# protocol scoring rather than run beside it, because three stalls of ~1,000 s
# each were traced to a second job competing with a live one (report.md 3.10).
#
# PRE-REGISTRATION, committed before this script was first run.
#
#   Known: 11,669 molecules gave 0.03% of molecules sharing a fingerprint;
#   950,967 gave 1.40%, and 6.13% at 50-59 heavy atoms. Those two points span
#   6.35 corpus doublings and a 46.7x change in the rate, so the rate scales
#   as roughly corpus^0.87 -- slightly sub-linear, which is what a birthday
#   argument predicts once the fingerprint space stops being effectively
#   infinite.
#
#   1. DIRECTION. The full shard's ambiguity rate is HIGHER than the 1M
#      shard's 1.40%. A rate that is flat or lower would mean collisions do
#      not in fact grow with corpus size, which is retraction 18's entire
#      finding and would reopen it.
#   2. INTERVAL. train+valid of the full shard is 1,986,551 molecules, 2.089x
#      the 1M shard. Extrapolating the measured exponent gives 2.63%, and a
#      purely linear rate gives 2.92%. Registered interval: **2.2% to 3.2%**
#      of molecules sharing a fingerprint, i.e. 96.8% to 97.8% unique.
#   3. PER BAND. The same factor applies roughly uniformly in size, so 50-59
#      lands in **10% to 13%** and 0-24 in **1.7% to 2.3%**. If the factor is
#      instead concentrated in the large bands, the size dependence of
#      ambiguity is steeper than the project has assumed and section 5.11's
#      "the reduction factor is flat in size" needs re-checking.
#   4. COUNTS. Count fingerprints cut the rate by about 5.6x on the 1M shard
#      and the factor was flat in size. Registered: the factor stays within
#      **4x to 7x** on the full shard. Dropping below 4x would mean counts buy
#      less as the corpus grows, which is the first thing anyone scaling this
#      up would want to know.
#   5. MAX GROUP SIZE can only grow with the corpus, so >= 39. Not a
#      prediction, an arithmetic check that the larger shard is a superset.
#
#   Honest expectation: 1, 4 and 5 hold; 2 is the row most likely to miss,
#   because it rests on a two-point exponent with no error bar, measured
#   across a corpus range where the 60+ band already behaves oddly.
#
# Run: bash scripts/ambiguity_full.sh
set -u
cd "/Users/jonswain/Desktop/Personal Projects/morg2smiles"
PY=/Users/jonswain/miniforge3/envs/morg2smiles/bin/python
export PYTHONPATH=src:.
L=results/overnight10
mkdir -p "$L"
say() { echo "[$(date '+%m-%d %H:%M:%S')] $*" | tee -a "$L/ambiguity.log"; }

# Wait for the scorer, if one is still running. One job per machine.
if [ -n "${WAIT_FOR:-}" ]; then
    say "waiting for pid $WAIT_FOR before starting"
    while kill -0 "$WAIT_FOR" 2>/dev/null; do sleep 60; done
    say "pid $WAIT_FOR gone, starting"
fi

say "=== fingerprint ambiguity on data/shards/full (train+valid) ==="

say "stage 1: binary, r=2, 2048 bits"
$PY -u scripts/fingerprint_ambiguity.py --shard data/shards/full --splits train,valid \
    --binary --out "$L/fingerprint_ambiguity_full.json" > "$L/stage3_ambiguity_binary.log" 2>&1
say "stage 1 exit=$?"

say "stage 2: counts, same shard and bands"
$PY -u scripts/fingerprint_ambiguity.py --shard data/shards/full --splits train,valid \
    --counts --out "$L/fingerprint_ambiguity_full_counts.json" > "$L/stage4_ambiguity_counts.log" 2>&1
say "stage 2 exit=$?"

say "=== done; score against the registration in this script's header ==="
