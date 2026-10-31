"""Score stage 6 of the final run: the exponents, on the held-out protocol.

Stage 5b of `overnight9.sh` fits the step exponent from each run's *own*
in-training history, and night 8 established that those traces can disagree in
direction with the held-out protocol. Stage 6, registered in
`docs/final-run-plan.md` section 8 before any of these numbers existed, answers
the same question from the matched pair of protocol dumps instead.

Six quantities, each registered against a specific number rather than an
interval, because this project has never measured the error bar on an exponent
from a single pair and a registration narrower than an unmeasured noise floor
is its own failure mode. So this script reports distance-from-target and says
what the sign means; it does not pretend to a significance it cannot compute.

Run: PYTHONPATH=src:. python scripts/score_stage6.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The pair: same 8.0M architecture, same data/shards/full, same night-6
# invocation at k=60 / T=0.6 / --max-oversample 12, same queries. Only the step
# count differs, which on a fixed corpus is the passes axis.
SHORT_STEPS, LONG_STEPS = 17_772, 88_218
SHORT_PASSES, LONG_PASSES = 1.2087, 6.00

PAIR_30 = (
    "results/overnight7/miss_anatomy_full_1p2.json",
    "results/overnight9/miss_anatomy_full_6p.json",
)
PAIR_50 = (
    "results/overnight7b/miss_anatomy_50plus_full_1p2.json",
    "results/overnight9/miss_anatomy_50plus_full_6p.json",
)

# Registered targets, docs/final-run-plan.md section 8.
C_ALL_LO, C_ALL_HI = 0.7008, 0.9113  # item 2's range, from the 100k 2x2
C_PER_BAND = {"30-34": 1.092, "35-39": 1.083, "40-49": 0.770, "50+": 0.381}
B_LO, B_HI = 0.144, 0.396  # results.md section 2.1
B_OVER_REC_LO, B_OVER_REC_HI = 0.320, 0.380
G_PRIME_50_TARGET = 26.30  # the 1M shard, per passes doubling
F_PRIME_50 = 16.86  # measured on the 1M shard at 50+, results.md section 2.9b
G_OVER_F_LO, G_OVER_F_HI = 1.52, 1.68

DOUBLINGS = math.log2(LONG_PASSES / SHORT_PASSES)


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text())


def rec_at(report: dict, band: str, k: int) -> float | None:
    b = report.get("bands", {}).get(band)
    return None if b is None else b["recovery_at_k"][str(k)]


def pair_exponent(short: dict, long_: dict, band: str, k: int) -> float | None:
    """c in  1 - rec = A * steps^-c,  from two points."""
    lo, hi = rec_at(short, band, k), rec_at(long_, band, k)
    if lo is None or hi is None or lo >= 1 or hi >= 1:
        return None
    return -math.log((1 - hi) / (1 - lo)) / math.log(LONG_STEPS / SHORT_STEPS)


def against(measured: float, lo: float, hi: float) -> str:
    if measured < lo:
        return f"below by {lo - measured:.3f}"
    if measured > hi:
        return f"above by {measured - hi:.3f}"
    return "inside"


def main() -> None:
    short30, long30 = (load(p) for p in PAIR_30)
    short50, long50 = (load(p) for p in PAIR_50)
    out: dict = {"doublings_of_passes": DOUBLINGS}

    print("=" * 78)
    print("Stage 6: the exponents on the held-out protocol")
    print(f"{SHORT_STEPS:,} vs {LONG_STEPS:,} steps = {SHORT_PASSES} vs {LONG_PASSES} passes")
    print("=" * 78)

    # (a) c overall, and (b) c per band.
    print("\n(a) c at k=60, all bands -- read against item 2's 0.7008-0.9113")
    c_all = pair_exponent(short30, long30, "all", 60)
    c_all_50 = pair_exponent(short50, long50, "all", 60)
    print(f"  30+ protocol, 2,321 queries : c = {c_all:.3f}   {against(c_all, C_ALL_LO, C_ALL_HI)}")
    print(
        f"  50+ instrument,  893 queries : c = {c_all_50:.3f}   {against(c_all_50, C_ALL_LO, C_ALL_HI)}"
    )
    out["c_all_30plus"] = c_all
    out["c_all_50plus"] = c_all_50

    print("\n(b) c per band -- read against the 100k 2x2's k=60 column")
    print(f"  {'band':8} {'registered':>11} {'measured':>9}  {'ratio':>6}")
    out["c_per_band"] = {}
    for band, target in C_PER_BAND.items():
        c = pair_exponent(short30, long30, band, 60)
        if c is None:
            continue
        print(f"  {band:8} {target:11.3f} {c:9.3f}  {c / target:6.2f}x")
        out["c_per_band"][band] = {"registered": target, "measured": c, "ratio": c / target}

    # (c) b, and (d) the b / rec@60 invariant.
    curve = load("results/overnight9/budget_curve_full_6p.json")
    rows = curve.get("bands", curve.get("deficit", {}))
    print(
        f"\n(c) b -- read against {B_LO}-{B_HI};  (d) b / rec@60 -- against {B_OVER_REC_LO}-{B_OVER_REC_HI}"
    )
    print(f"  {'band':8} {'b':>6} {'verdict':>14}  {'b/rec@60':>8} {'verdict':>14}")
    out["b"] = {}
    for band, row in rows.items():
        b = row.get("exponent", row.get("b"))
        rec = rec_at(long30, band, 60)
        if b is None or rec is None:
            continue
        ratio = b / rec
        print(
            f"  {band:8} {b:6.3f} {against(b, B_LO, B_HI):>14}  "
            f"{ratio:8.3f} {against(ratio, B_OVER_REC_LO, B_OVER_REC_HI):>14}"
        )
        out["b"][band] = {"b": b, "rec_at_60": rec, "b_over_rec": ratio}

    # (e) g' at 50+, and (f) the g'/f' exchange rate.
    lo, hi = rec_at(short50, "all", 60), rec_at(long50, "all", 60)
    g_prime = (hi - lo) * 100.0 / DOUBLINGS
    g_over_f = g_prime / F_PRIME_50
    print(f"\n(e) g' at 50+ on the full shard -- read against +{G_PRIME_50_TARGET}")
    print(f"  rec@60 {lo:.4f} -> {hi:.4f} over {DOUBLINGS:.4f} doublings")
    print(
        f"  g' = {g_prime:+.2f} pts / passes doubling   ({g_prime - G_PRIME_50_TARGET:+.2f} vs target)"
    )
    print(
        f"\n(f) g'/f' at 50+ -- read against {G_OVER_F_LO}-{G_OVER_F_HI}, with f' = +{F_PRIME_50}"
    )
    print(f"  g'/f' = {g_over_f:.3f}   {against(g_over_f, G_OVER_F_LO, G_OVER_F_HI)}")
    out["g_prime_50plus"] = {"measured": g_prime, "registered": G_PRIME_50_TARGET}
    out["g_over_f_50plus"] = {"measured": g_over_f, "registered": [G_OVER_F_LO, G_OVER_F_HI]}

    dest = ROOT / "results/overnight9/stage6_scored.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nwritten: {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
