"""What does a band get for being shown to the model more often?

Two size-weighted mixes have now been trained on the same 100k shard with the
same step schedule, differing only in how they re-weight the sampler:

    size_mix_s1/s2   threshold 30, factor 3  -- 30+ atoms at 1.69x exposure
    size_mix_t35     threshold 35, factor 6  -- 35+ atoms at 3.06x exposure

Both are re-weightings of one fixed corpus, so a band's gain is paid for out
of some other band's exposure. That makes the interesting quantity not the
gap but the gap *per doubling of exposure*, band by band, and the interesting
question whether the two mixes lie on one curve. If they do, the curve prices
every re-weighting of this shard that anyone might try next.

The molecule accounting is here too, because points are not comparable across
bands of different sizes: 7.59 points on 123 queries is nine molecules, and
the only honest summary of a trade is how many small molecules were given up
per large molecule gained.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import click


def _arm(spec: str) -> tuple[str, list[str], str | None]:
    name, _, rest = spec.partition("=")
    runs, _, record = rest.partition("@")
    return name, [r for r in runs.split(",") if r], record or None


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def _exposure(record_path: str) -> dict[str, float]:
    mix = json.loads(Path(record_path).read_text())["size_weighted_mix"]
    return {b: v["weighted_share"] / v["share"] for b, v in mix["bands"].items()}


def _ols(xs: list[float], ys: list[float]) -> tuple[float, float, float] | None:
    """Slope, intercept and r of a straight line through the points.

    None when the x values carry no contrast, which is the normal case for a
    mix scored on a protocol that only contains bands on one side of its
    threshold: the large protocol starts at 30 atoms, so every one of its
    bands sits at 1.69x under the threshold-30 mix and no slope is defined.
    """
    mx, my = _mean(xs), _mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx < 1e-9 or syy < 1e-9:
        return None
    slope = sxy / sxx
    return slope, my - slope * mx, sxy / math.sqrt(sxx * syy)


@click.command()
@click.option("--bands", type=click.Path(path_type=Path), required=True)
@click.option("--reference", required=True, help="name=run1,run2,run3")
@click.option(
    "--mix",
    "mixes",
    multiple=True,
    required=True,
    help="name=run1,run2@checkpoints/<run>/record.json -- repeat for each dose.",
)
@click.option(
    "--elementary-bands",
    default="0-24,25-29,30-34,35-39,40-49,50+",
    show_default=True,
    help="Bands that partition the protocol; the overlapping summaries are skipped.",
)
@click.option("--out", type=click.Path(path_type=Path), default=None)
def main(bands, reference, mixes, elementary_bands, out):
    report = json.loads(bands.read_text())
    band_order = [b for b in elementary_bands.split(",") if b in report["bands"]]
    if not band_order:
        raise click.ClickException(
            f"none of --elementary-bands ({elementary_bands}) is in {bands}, which has "
            f"{', '.join(report['bands'])}; the bands must partition the protocol, so "
            "the overlapping summaries like 35+ cannot be used here"
        )
    ref_name, ref_runs, _ = _arm(reference)

    click.echo(f"{bands}  k={report['k']}  {report['order']} order  metric={report['metric']}")
    click.echo(f"reference arm {ref_name}: {', '.join(ref_runs)}\n")

    result = {
        "bands_report": str(bands),
        "metric": report["metric"],
        "reference": {"name": ref_name, "runs": ref_runs},
        "mixes": {},
    }
    doses = []
    for spec in mixes:
        name, runs, record = _arm(spec)
        if record is None:
            raise click.ClickException(f"mix {name} needs @path/to/record.json for its exposure")
        exposure = _exposure(record)
        rows = []
        for band in band_order:
            entry = report["bands"][band]
            n = entry["n_queries"]
            base = _mean([entry["per_run"][r] for r in ref_runs])
            mixed = _mean([entry["per_run"][r] for r in runs])
            ratio = exposure[band]
            rows.append(
                {
                    "band": band,
                    "n_queries": n,
                    "exposure_ratio": ratio,
                    "log2_exposure": math.log2(ratio),
                    "reference": base,
                    "mix": mixed,
                    "gap_points": 100 * (mixed - base),
                    "molecules": n * (mixed - base),
                    "points_per_doubling": 100 * (mixed - base) / math.log2(ratio),
                }
            )

        header = (
            f"{'band':>7}{'n':>7}{'exposure':>10}{'ref':>9}{'mix':>9}"
            f"{'gap':>8}{'mols':>8}{'pts/2x':>9}"
        )
        click.echo(f"=== {name} ===")
        click.echo(header)
        click.echo("-" * len(header))
        for r in rows:
            click.echo(
                f"{r['band']:>7}{r['n_queries']:>7,}{r['exposure_ratio']:>9.2f}x"
                f"{r['reference']:>9.4f}{r['mix']:>9.4f}{r['gap_points']:>+8.2f}"
                f"{r['molecules']:>+8.1f}{r['points_per_doubling']:>+9.2f}"
            )

        lost = sum(r["molecules"] for r in rows if r["molecules"] < 0)
        gained = sum(r["molecules"] for r in rows if r["molecules"] > 0)
        n_total = sum(r["n_queries"] for r in rows)
        fit = _ols([r["log2_exposure"] for r in rows], [r["gap_points"] for r in rows])
        summary = {
            "rows": rows,
            "molecules_lost": lost,
            "molecules_gained": gained,
            "molecules_net": lost + gained,
            "net_points": 100 * (lost + gained) / n_total,
            # No rate when one side of the trade is empty: a protocol that
            # holds no band the mix de-weighted sees a gain with no cost.
            "given_up_per_gain": -lost / gained if lost and gained else None,
            "fit": None
            if fit is None
            else {"points_per_doubling": fit[0], "intercept": fit[1], "r": fit[2]},
        }
        trade = (
            "no band on this protocol pays for the gain"
            if summary["given_up_per_gain"] is None
            else f"{summary['given_up_per_gain']:.1f} given up per one gained"
        )
        click.echo(
            f"  lost {-lost:,.1f} molecules, gained {gained:,.1f}; {trade}; "
            f"net {summary['net_points']:+.2f} points over {n_total:,} queries"
        )
        if fit is None:
            click.echo(
                "  every band here sits at the same exposure, so this protocol "
                "cannot price a doubling\n"
            )
        else:
            click.echo(
                f"  straight line through log2 exposure: {fit[0]:+.2f} points per doubling "
                f"(intercept {fit[1]:+.2f}, r={fit[2]:.3f})\n"
            )
        result["mixes"][name] = summary
        # A mix's dose is how hard it pushed the bands it up-weighted, read
        # off the training record rather than off which bands happened to gain.
        up = [r["log2_exposure"] for r in rows if r["exposure_ratio"] > 1]
        doses.append((_mean(up) if up else max(r["log2_exposure"] for r in rows), name, summary))

    doses.sort()
    for (_, lo_name, lo), (_, hi_name, hi) in zip(doses, doses[1:], strict=False):
        extra_lost = hi["molecules_lost"] - lo["molecules_lost"]
        extra_gained = hi["molecules_gained"] - lo["molecules_gained"]
        rate = -extra_lost / extra_gained if extra_gained > 0 else None
        verdict = (
            f"{rate:.1f} given up per one gained"
            if rate is not None
            else "the larger dose gained less, not more, so there is no rate to quote"
        )
        click.echo(
            f"marginal, {lo_name} -> {hi_name}: {extra_gained:+.1f} molecules gained for "
            f"{-extra_lost:+.1f} lost -- {verdict}"
        )
        result.setdefault("marginal", {})[f"{lo_name}->{hi_name}"] = {
            "extra_gained": extra_gained,
            "extra_lost": extra_lost,
            "given_up_per_gain": rate,
        }

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2))
        click.echo(f"\nwrote {out}")


if __name__ == "__main__":
    main()
