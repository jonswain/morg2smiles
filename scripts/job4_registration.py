"""Build item 4's pre-registration from the three cells of the 50+ instrument.

Item 4 of docs/next-steps-2026-10-19.md is the full-ChEMBL run, and its headline
rec@60 saturates: under the measured decomposition the all-slice number lands
above 1.0, which is where this project has twice mistaken a ceiling for a null.
So the registration lives on the 50+ protocol, per band, on both metrics.

Night 7c built the 3-pass version inline in its driver. This exists because the
budget changed to 6 passes after night 8, which means every number in that
registration was for the wrong run -- and because a registration derived by a
script that can be re-read is worth more than one derived in a heredoc.

The instrument has three cells, all on the same 893-query draw:

    small_1m_matched   900,917 molecules   1.21 passes
    small_full_1p2   1,881,996 molecules   1.21 passes
    small_1m           900,917 molecules   3.00 passes

so the corpus slope f' is read matched -> full_1p2 at constant passes, and the
passes slope g' is read matched -> s1m at constant corpus. The target cell is
the full shard at the chosen budget, which is full_1p2 extended along passes
alone -- one measured cell on the right corpus, moved along one axis.

Everything is fitted in **deficit** rather than points. The points form returns
above 1.0 in four of six bands, and §2.2a of docs/results.md is the reason:
recovery is bounded, so a slope in points conflates the law with the ceiling.

The registration is an **interval**, and its width is not decoration. The
passes exponent is measured over 1.31 doublings and the target is 2.31, so a
third of the extrapolation is outside the measured range -- and night 8
established that this exponent *falls* with range. The upper bound holds the
exponent constant; the lower bound decays it past the measured range by the
factor night 8 measured. A result above the upper bound means the passes axis
is better than its own slope suggests; below the lower bound means the decay is
steeper at 1-6 passes than it was at 30-74, which would be new.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import click

# Night 8's measured exponent decay: c fell 0.9113 -> 0.7008 between one
# doubling-and-a-third of steps and the next on a fixed corpus, a factor of
# 0.769 per 1.31 doublings of extension. Applied here to the part of the
# extrapolation that sits beyond the measured range, as the pessimistic bound.
# It is a transfer from a different repetition regime -- 30-74 passes rather
# than 1-6 -- which is exactly why it bounds the interval instead of setting
# the point estimate.
NIGHT8_DECAY = 0.7008 / 0.9113


def _band_values(path: Path, run: str) -> dict[str, tuple[float, int]]:
    d = json.loads(path.read_text())
    out = {}
    for band, v in d["bands"].items():
        per_run = v["per_run"]
        if run in per_run:
            out[band] = (per_run[run], v["n_queries"])
    if not out:
        raise click.ClickException(f"{run} not found in {path}; has {d['runs']}")
    return out


def _exponent(lo: float, hi: float, doublings: float) -> float:
    """Deficit exponent c such that deficit scales by 2**(-c * doublings)."""
    d_lo, d_hi = 1.0 - lo, 1.0 - hi
    if d_lo <= 0 or d_hi <= 0:
        raise click.ClickException("a cell is at the ceiling; the deficit form needs both < 1")
    return -math.log2(d_hi / d_lo) / doublings


@click.command()
@click.option("--matched", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--full-1p2", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--s1m", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--target-passes", default=6.0, show_default=True)
@click.option("--base-passes", default=1.2087, show_default=True)
@click.option("--s1m-passes", default=3.0, show_default=True)
@click.option("--corpus-doublings", default=1.0629, show_default=True, help="900,917 -> 1,881,996.")
@click.option("--out", type=click.Path(path_type=Path), required=True)
def main(
    matched: Path,
    full_1p2: Path,
    s1m: Path,
    target_passes: float,
    base_passes: float,
    s1m_passes: float,
    corpus_doublings: float,
    out: Path,
) -> None:
    m = _band_values(matched, "small_1m_matched")
    f = _band_values(full_1p2, "small_full_1p2")
    s = _band_values(s1m, "small_1m")

    g_doublings = math.log2(s1m_passes / base_passes)
    target_doublings = math.log2(target_passes / base_passes)
    # The share of the extrapolation that the g' measurement actually covers.
    # Beyond it the exponent is decayed, because night 8 measured it falling.
    measured = min(g_doublings, target_doublings)
    beyond = max(0.0, target_doublings - g_doublings)

    rows = []
    for band in m:
        if band not in f or band not in s:
            continue
        base, n = f[band]
        f_prime = _exponent(m[band][0], f[band][0], corpus_doublings)
        g_prime = _exponent(m[band][0], s[band][0], g_doublings)

        deficit = 1.0 - base
        hi = 1.0 - deficit * 2.0 ** (-g_prime * target_doublings)
        lo = 1.0 - deficit * 2.0 ** (-g_prime * (measured + beyond * NIGHT8_DECAY))

        # The extrapolation bounds alone are too narrow to register, and that
        # is not a rounding matter: at 60-64 they span 2.5 points while the
        # binomial SE on 203 queries at that rate is 3.5. A registration
        # narrower than the noise on the instrument reading it is the thin
        # sample mistake night 7c paid for, in a new place -- there the sample
        # was 127 queries and the registration moved six points when it was
        # rebuilt on 893. So the interval is widened by one SE on each side,
        # evaluated at the nearer bound, which is the conservative choice.
        se_lo = math.sqrt(max(lo * (1.0 - lo), 0.0) / n)
        se_hi = math.sqrt(max(hi * (1.0 - hi), 0.0) / n)

        rows.append(
            {
                "band": band,
                "n": n,
                "cells": {
                    "matched_900k_1p21": m[band][0],
                    "full_1p2": base,
                    "s1m_900k_3p00": s[band][0],
                },
                "f_prime_deficit_exponent": f_prime,
                "g_prime_deficit_exponent": g_prime,
                "extrapolation_lo": lo,
                "extrapolation_hi": hi,
                "se_at_lo": se_lo,
                "se_at_hi": se_hi,
                "registered_lo": lo - se_lo,
                "registered_hi": hi + se_hi,
            }
        )

    payload = {
        "target": {
            "shard": "data/shards/full",
            "passes": target_passes,
            "steps": round(1881996 * target_passes / 128),
            "base_cell": "small_full_1p2",
            "base_passes": base_passes,
            "passes_doublings": target_doublings,
            "g_measured_over_doublings": g_doublings,
            "fraction_extrapolated": beyond / target_doublings if target_doublings else 0.0,
            "night8_decay_applied_beyond_measured": NIGHT8_DECAY,
        },
        "metric": json.loads(matched.read_text())["metric"],
        "k": json.loads(matched.read_text())["k"],
        "rows": rows,
    }
    out.write_text(json.dumps(payload, indent=2) + "\n")

    print(
        f"item 4 registration -- {payload['metric']}@{payload['k']}, full shard, {target_passes} passes"
    )
    print(
        f"  {payload['target']['steps']:,} steps; {payload['target']['fraction_extrapolated']:.0%} of the passes extrapolation is beyond the measured range\n"
    )
    print(
        f"  {'band':8} {'n':>5} {'full_1p2':>9} {'f-prime':>8} {'g-prime':>8} "
        f"{'extrapolation':>17} {'+/-1 SE':>8} {'REGISTERED':>19}"
    )
    for r in rows:
        print(
            f"  {r['band']:8} {r['n']:5} {r['cells']['full_1p2']:9.4f} "
            f"{r['f_prime_deficit_exponent']:8.4f} {r['g_prime_deficit_exponent']:8.4f} "
            f"{r['extrapolation_lo']:7.4f} - {r['extrapolation_hi']:.4f} "
            f"{r['se_at_hi']:8.4f} "
            f"{r['registered_lo']:8.4f} - {r['registered_hi']:.4f}"
        )
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
