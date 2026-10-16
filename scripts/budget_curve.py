"""How far does a bigger sampling budget go, and what does it buy?

Every price this project has quoted for the brute-force route -- widen k inside
one model -- came from extrapolating the 10 -> 20 step of a 20-slot list. This
reads a run that actually generated past k=20 and asks three things of it.

**Does the deficit follow a law?** `1 - rec(k) = A k^-b` is the natural shape
if a fixed share of the candidate space is reachable per draw, and it has the
property the recovery-multiplier extrapolation lacks: it cannot predict a
recovery above 1. The fit is reported per band with its correlation, so a band
where the shape is wrong says so.

**Would the old method have worked?** The same fit is re-run on the rungs at or
below k=20 and asked to predict the largest rung measured. That is the
extrapolation the pricing rested on, scored against the measurement it was
guessing, which is the only way to say how much the quoted prices are worth.

**Where do the recoveries go?** Counting exact preimages per query separates
two accounts of the size cliff that the pooled rate cannot. If big molecules
simply draw fewer preimages, recovery falls because the cloud is thinner. If
they draw about as many but concentrated on fewer queries, the population is
splitting into reachable and unreachable fingerprints and extra budget mostly
re-finds molecules already found. The Poisson column is the reference: it is
the recovery that this many preimages per query would give if they fell
independently across the queries of the band.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

import click

from scripts.seed_union import _band_bounds
from scripts.size_bias import _heavy, _proposals
from scripts.variance_analysis import load


def _ols(xs: list[float], ys: list[float]) -> tuple[float, float, float] | None:
    """Slope, intercept and correlation, or None when x or y does not vary."""
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx < 1e-9 or syy < 1e-9:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    slope = sxy / sxx
    return slope, my - slope * mx, sxy / math.sqrt(sxx * syy)


def _fit_deficit(
    ladder: dict[int, float], min_k: int, max_k: int
) -> tuple[float, float, float] | None:
    """Fit log(1 - rec) on log k over the rungs in [min_k, max_k].

    Rungs below 5 are excluded by the caller's default: the first few slots are
    where the consensus ordering and the duplicate rate do their work, and the
    asymptotic shape is not supposed to hold there.
    """
    ks = [k for k in sorted(ladder) if min_k <= k <= max_k and ladder[k] < 1.0]
    if len(ks) < 3:
        return None
    return _ols([math.log(k) for k in ks], [math.log(1 - ladder[k]) for k in ks])


def _budget_for(fit: tuple[float, float, float], target: float) -> float | None:
    """The k at which the fitted law reaches `target` recovery."""
    slope, intercept, _ = fit
    if slope >= -1e-9:
        return None
    return math.exp((math.log(1 - target) - intercept) / slope)


def _fmt_k(k: float | None) -> str:
    if k is None:
        return "--"
    if k > 1e12:
        return f"{k:>.1e}"
    return f"{k:,.0f}"


@click.command()
@click.option(
    "--anatomy",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="A miss_anatomy.py report, which carries the rec@k ladder per band.",
)
@click.option(
    "--dump",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="The outcomes dump, for the preimages-per-query table. Optional.",
)
@click.option("--k", default=60, show_default=True, help="Budget for the preimage count.")
@click.option("--budget", default="molecules", show_default=True)
@click.option("--min-fit-k", default=5, show_default=True)
@click.option(
    "--extrapolate-from",
    default=20,
    show_default=True,
    help="Re-fit on rungs up to here and score the prediction at the top rung.",
)
@click.option("--targets", default="0.9,0.95,0.99", show_default=True)
@click.option("--bands", default="30-34,35-39,40-49,50+,35+,all", show_default=True)
@click.option("--out", type=click.Path(path_type=Path), default=None)
def main(anatomy, dump, k, budget, min_fit_k, extrapolate_from, targets, bands, out):
    report = json.loads(anatomy.read_text())
    band_reports = report["bands"]
    targets = [float(t) for t in targets.split(",")]
    specs = [s for s in bands.split(",") if s in band_reports]
    if not specs:
        raise click.ClickException(
            f"none of {bands} is in {anatomy}, whose bands are {', '.join(band_reports)}"
        )

    out_report = {"anatomy": str(anatomy), "k": report.get("k"), "bands": {}}
    click.echo(f"{anatomy}  generated to k={report.get('k')}")
    click.echo("\nthe deficit against budget:  1 - rec(k) = A k^-b")
    header = (
        f"{'band':>7}{'n':>7}{'rec@top':>9}{'b':>7}{'r':>8}"
        f"{'b(<=' + str(extrapolate_from) + ')':>9}{'predicts':>10}{'error':>8}"
    )
    click.echo(header)
    click.echo("-" * len(header))
    fits = {}
    for spec in specs:
        band = band_reports[spec]
        ladder = {int(j): v for j, v in band["recovery_at_k"].items()}
        top = max(ladder)
        full = _fit_deficit(ladder, min_fit_k, top)
        early = _fit_deficit(ladder, min_fit_k, extrapolate_from)
        entry = {"n_queries": band["n_queries"], "top_k": top, "recovery_at_top": ladder[top]}
        line = f"{spec:>7}{band['n_queries']:>7,}{ladder[top]:>9.4f}"
        if full is None:
            line += f"{'--':>7}{'--':>8}"
        else:
            entry["exponent"] = -full[0]
            entry["correlation"] = full[2]
            line += f"{-full[0]:>7.3f}{full[2]:>8.4f}"
        if early is None or top <= extrapolate_from:
            line += f"{'--':>9}{'--':>10}{'--':>8}"
        else:
            predicted = 1 - math.exp(early[1] + early[0] * math.log(top))
            entry["extrapolated"] = {
                "fitted_to_k": extrapolate_from,
                "exponent": -early[0],
                "predicted": predicted,
                "error_points": 100 * (ladder[top] - predicted),
            }
            line += f"{-early[0]:>9.3f}{predicted:>10.4f}{100 * (ladder[top] - predicted):>+8.2f}"
        click.echo(line)
        fits[spec] = full
        out_report["bands"][spec] = entry

    click.echo(
        "\nb is the exponent: every doubling of the budget cuts the shortfall by "
        f"a factor 2^-b. The last three columns re-fit on k<={extrapolate_from} only and "
        "score that fit against the top rung, which is the extrapolation every "
        "price quoted before this run rested on."
    )

    click.echo("\nthe budget the fitted law asks for")
    header = f"{'band':>7}" + "".join(f"{'k for ' + f'{t:g}':>16}" for t in targets)
    click.echo(header)
    click.echo("-" * len(header))
    for spec in specs:
        if fits[spec] is None:
            continue
        needed = {f"{t:g}": _budget_for(fits[spec], t) for t in targets}
        out_report["bands"][spec]["budget_for"] = needed
        click.echo(f"{spec:>7}" + "".join(f"{_fmt_k(needed[f'{t:g}']):>16}" for t in targets))
    click.echo(
        "\nExtrapolations, all of them, and lower bounds on the cost: they assume "
        "the fitted exponent holds for decades past the three the fit saw."
    )

    if dump is None:
        _write(out, out_report)
        return

    rows = []
    for o in load(dump, budget):
        if not o.fp_unseen:
            continue
        target = _heavy(o.reference_smiles)
        proposals = _proposals(o, k)
        if target is None or not proposals:
            continue
        rows.append((target, sum(1 for _, m in proposals if m)))

    click.echo(f"\nexact preimages per query within k={k}, from {dump}")
    header = (
        f"{'band':>7}{'n':>7}{'rec':>8}{'preimages/q':>13}{'if Poisson':>12}"
        f"{'none':>8}{'one':>7}{'two':>7}{'3+':>7}{'per hit':>9}"
    )
    click.echo(header)
    click.echo("-" * len(header))
    for spec in specs:
        lo, hi = _band_bounds(spec)
        band = [n for t, n in rows if lo <= t <= hi]
        if not band:
            continue
        n = len(band)
        lam = sum(band) / n
        counts = Counter(min(c, 3) for c in band)
        hits = [c for c in band if c]
        entry = {
            "n_queries": n,
            "recovery": len(hits) / n,
            "preimages_per_query": lam,
            "poisson_recovery": 1 - math.exp(-lam),
            "share_none": counts[0] / n,
            "preimages_per_hit": (sum(hits) / len(hits)) if hits else None,
        }
        out_report["bands"][spec]["preimages"] = entry
        click.echo(
            f"{spec:>7}{n:>7,}{len(hits) / n:>8.4f}{lam:>13.3f}{1 - math.exp(-lam):>12.4f}"
            f"{counts[0] / n:>8.3f}{counts[1] / n:>7.3f}{counts[2] / n:>7.3f}{counts[3] / n:>7.3f}"
            f"{(sum(hits) / len(hits)) if hits else float('nan'):>9.2f}"
        )
    click.echo(
        "\nRecovery here counts a query as recovered when a preimage is among its "
        "first k proposals, so it sits slightly above the protocol's own number; "
        "read the columns against each other, not against the headline. 'if "
        "Poisson' is the recovery this many preimages per query would give if "
        "they fell independently across the band's queries -- above the measured "
        "recovery means the preimages are concentrated on fewer queries than "
        "chance."
    )
    _write(out, out_report)


def _write(out: Path | None, report: dict) -> None:
    if out is None:
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    click.echo(f"wrote {out}")


if __name__ == "__main__":
    main()
