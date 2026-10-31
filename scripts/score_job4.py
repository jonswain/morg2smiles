"""Score the final run against the five registrations in configs/small_full_6p.yaml.

Written before the run finished, on purpose. The registrations are intervals on
disk and the measurements are band tables on disk, so scoring is a lookup rather
than a judgement -- which is the whole point of registering an interval, and the
thing retractions entries 22 and 26 were paid for.

The pairing below is the load-bearing part. Each registration names a metric, a
k, an order and a protocol, and each has exactly one band table measured the
same way; reading a registration against a table that differs in any of those is
the convention collision of methodology section 1, which has been caught four
times. So the pairs are declared explicitly and the script refuses a mismatch
rather than silently comparing across conventions.

Usage: python scripts/score_job4.py [--run small_full_6p]
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (label, registration file, measured band table, k, order, protocol)
#
# Registration (1) -- the headline -- is deliberately absent: config section 4a
# registers it as a ceiling reading rather than as a test, so there is nothing to
# score. It is reported by --headline instead.
PAIRS = [
    (
        "(2) 50+ protocol, rec@60",
        "results/overnight8/job4_registration_6p_recovery.json",
        "results/overnight9/b50_subbands_recovery.json",
        60,
        "generation",
        "50+ (893 queries)",
    ),
    (
        "(2) 50+ protocol, struct@60",
        "results/overnight8/job4_registration_6p_structure.json",
        "results/overnight9/b50_subbands_structure.json",
        60,
        "generation",
        "50+ (893 queries)",
    ),
    (
        "(3) 30+ protocol, rec@1 consensus",
        "results/overnight9/job4_registration_k1_6p_recovery.json",
        "results/overnight9/band_k1_full_6p.json",
        1,
        "consensus",
        "30+ (2,321 queries)",
    ),
    (
        "(3) 30+ protocol, struct@1 consensus",
        "results/overnight9/job4_registration_k1_6p_structure.json",
        "results/overnight9/band_k1_full_6p_structure.json",
        1,
        "consensus",
        "30+ (2,321 queries)",
    ),
    (
        "(4) 30+ protocol, rec@60",
        "results/overnight9/job4_registration_30plus_6p_recovery.json",
        "results/overnight9/band_k60_full_6p.json",
        60,
        "generation",
        "30+ (2,321 queries)",
    ),
    (
        "(4) 30+ protocol, struct@60",
        "results/overnight9/job4_registration_30plus_6p_structure.json",
        "results/overnight9/band_k60_full_6p_structure.json",
        60,
        "generation",
        "30+ (2,321 queries)",
    ),
]

# Registration (4) names only these two bands as informative; the rest of the
# 30+ table is ceiling by section 4c and is printed as context, not scored.
REG4_SCORED = {"40-49", "35+"}


def binomial_se(p: float, n: int) -> float:
    return math.sqrt(max(p * (1.0 - p), 0.0) / n) if n else float("nan")


def verdict(measured: float, lo: float, hi: float) -> tuple[str, float]:
    """Return the branch and the signed distance outside the interval, in points."""
    if measured < lo:
        return "MISS LOW", (measured - lo) * 100.0
    if measured > hi:
        return "MISS HIGH", (measured - hi) * 100.0
    return "HIT", 0.0


def score_pair(label, reg_path, band_path, k, order, protocol, run, scored_only=None):
    reg = json.loads((ROOT / reg_path).read_text())
    band = json.loads((ROOT / band_path).read_text())

    # Refuse to compare across conventions. Every number in this project that
    # had to be withdrawn for a convention error would have been caught here.
    problems = []
    if reg["metric"] != band["metric"]:
        problems.append(f"metric {reg['metric']} vs {band['metric']}")
    if reg["k"] != band["k"] or band["k"] != k:
        problems.append(f"k {reg['k']} vs {band['k']} (expected {k})")
    if band["order"] != order:
        problems.append(f"order {band['order']} (expected {order})")
    if problems:
        print(f"\n{label}\n  REFUSED: {'; '.join(problems)}")
        return []

    print(f"\n{label}  --  {protocol}, {band['metric']}@{k}, {band['order']} order")
    print(f"  {'band':<8}{'n':>6}{'registered':>18}{'measured':>11}{'SE':>7}  verdict")

    results = []
    for row in reg["rows"]:
        name = row["band"]
        cell = band["bands"].get(name)
        if cell is None or run not in cell["per_run"]:
            print(f"  {name:<8}{row['n']:>6}{'':>18}{'absent':>11}")
            continue

        measured = cell["per_run"][run]
        n = cell["n_queries"]
        lo, hi = row["registered_lo"], row["registered_hi"]
        se = binomial_se(measured, n)
        branch, miss = verdict(measured, lo, hi)

        tag = branch if (scored_only is None or name in scored_only) else "context"
        note = f"{branch} by {abs(miss):.2f} pts" if (tag != "context" and miss) else tag
        print(
            f"  {name:<8}{n:>6}{f'{lo:.4f}-{hi:.4f}':>18}{measured:>11.4f}{se * 100:>7.2f}  {note}"
        )
        if tag != "context":
            results.append(
                {
                    "registration": label,
                    "band": name,
                    "n": n,
                    "lo": lo,
                    "hi": hi,
                    "measured": measured,
                    "se_points": se * 100,
                    "verdict": branch,
                    "miss_points": miss,
                }
            )
    return results


def headline(run: str) -> None:
    """Registration (1): report the all-slice number, do not score it."""
    path = ROOT / "results/overnight9/band_k60_full_6p.json"
    if not path.exists():
        return
    band = json.loads(path.read_text())
    cell = band["bands"].get("all") or band["bands"].get("all 30+")
    if not cell or run not in cell["per_run"]:
        return
    value = cell["per_run"][run]
    print("\n(1) THE HEADLINE -- reported, not scored (config section 4a)")
    print(
        f"  rec@60 all-slice, {cell['n_queries']} queries: {value:.4f}"
        "\n  Registered 0.9634-0.9767 as a CEILING READING. A whole-protocol number"
        "\n  this close to 1.0 cannot resolve anything -- the 1.6-point threshold is"
        "\n  wider than the interval. Weight belongs on rec@1, 40-49, 50+ and"
        "\n  structure accuracy."
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="small_full_6p")
    ap.add_argument("--out", default="results/overnight9/job4_scored.json")
    args = ap.parse_args()

    print("=" * 78)
    print("Scoring the final run against configs/small_full_6p.yaml")
    print("=" * 78)

    headline(args.run)

    all_results = []
    for label, reg, band, k, order, protocol in PAIRS:
        if not (ROOT / band).exists():
            print(f"\n{label}\n  not yet measured: {band}")
            continue
        scored_only = REG4_SCORED if label.startswith("(4)") else None
        all_results += score_pair(label, reg, band, k, order, protocol, args.run, scored_only)

    if all_results:
        hits = sum(r["verdict"] == "HIT" for r in all_results)
        print(f"\n{'=' * 78}")
        print(f"{hits} of {len(all_results)} scored entries inside their interval")
        for r in all_results:
            if r["verdict"] != "HIT":
                print(
                    f"  {r['verdict']}: {r['registration']} {r['band']} "
                    f"by {abs(r['miss_points']):.2f} pts "
                    f"({abs(r['miss_points']) / r['se_points']:.1f} SE)"
                )
        out = ROOT / args.out
        out.write_text(json.dumps(all_results, indent=2) + "\n")
        print(f"\nwritten: {args.out}")


if __name__ == "__main__":
    main()
