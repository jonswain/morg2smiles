"""Group runs into arms and read a band table as an experiment, not a run list.

`band_analysis.py` reports every run and every pairwise gap. That is the right
output when the runs *are* the question (three seeds of one recipe, three
temperatures of one checkpoint), but an experiment with two or three seeds per
arm needs the arm means and one error bar per band, and quoting the best or
worst pair instead is how a seed difference gets published as an effect.

The error bar here is deliberately the crude one: each arm's between-seed sd,
combined as `sqrt(s_a^2/n_a + s_b^2/n_b)`. It is wider than the paired
McNemar SE of any single pair, because it has to carry the seed variance that
a pair comparison conditions away, and the seed variance is exactly what a
training-side claim is up against. An arm with one seed has no sd of its own
and borrows the reference arm's -- stated in the output, because it is an
equal-variance assumption, not a measurement.

Also printed: how many of the `n_a * n_b` cross-arm pairs favour the arm. With
two or three seeds a side that is the only distribution-free thing available,
and a clean sweep of the pairs is worth more than a flattering mean.
"""

from __future__ import annotations

import json
from itertools import product
from pathlib import Path
from statistics import mean, stdev

import click


def parse_arm(spec: str) -> tuple[str, list[str]]:
    name, _, runs = spec.partition("=")
    if not runs:
        raise click.BadParameter(f"expected name=run1,run2 but got {spec!r}")
    return name, [r for r in runs.split(",") if r]


@click.command()
@click.option(
    "--bands",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="A band_analysis.py report.",
)
@click.option(
    "--arm",
    "arms",
    multiple=True,
    required=True,
    help="name=run1,run2 -- repeat; the first arm is the reference.",
)
@click.option("--out", type=click.Path(path_type=Path), default=None)
def main(bands: Path, arms: tuple[str, ...], out: Path | None) -> None:
    report = json.loads(bands.read_text())
    parsed = [parse_arm(a) for a in arms]
    known = set(report["runs"])
    for name, runs in parsed:
        missing = [r for r in runs if r not in known]
        if missing:
            raise click.BadParameter(f"arm {name}: {missing} not in {sorted(known)}")

    ref_name, ref_runs = parsed[0]
    click.echo(f"{bands}  k={report['k']}  {report['order']} order")
    for name, runs in parsed:
        click.echo(f"  arm {name:<12} {len(runs)} seed(s): {', '.join(runs)}")
    click.echo(f"  reference arm: {ref_name}\n")

    header = f"{'band':>8}{'n':>7}" + "".join(f"{n:>10}" for n, _ in parsed)
    for _ in parsed[1:]:
        header += f"{'gap':>8}{'SE':>7}{'x SE':>7}{'pairs':>8}"
    click.echo(header)
    click.echo("-" * len(header))

    table = {}
    borrowed = False
    for band, body in report["bands"].items():
        per_run = body["per_run"]
        stats = {}
        for name, runs in parsed:
            vals = [per_run[r] for r in runs]
            stats[name] = (mean(vals), stdev(vals) if len(vals) > 1 else None, len(vals), vals)
        ref_mu, ref_sd, ref_n, ref_vals = stats[ref_name]

        row = f"{band:>8}{body['n_queries']:>7,}"
        row += "".join(f"{stats[n][0]:>10.4f}" for n, _ in parsed)
        entry = {
            "n_queries": body["n_queries"],
            "arms": {
                n: {"mean": stats[n][0], "sd": stats[n][1], "values": stats[n][3]}
                for n, _ in parsed
            },
            "vs_reference": {},
        }
        for name, _runs in parsed[1:]:
            mu, sd, n, vals = stats[name]
            sd_used, sd_borrowed = (sd, False) if sd is not None else (ref_sd, True)
            borrowed |= sd_borrowed
            se = ((ref_sd or 0.0) ** 2 / ref_n + (sd_used or 0.0) ** 2 / n) ** 0.5
            gap = mu - ref_mu
            favour = sum(1 for a, b in product(ref_vals, vals) if b > a)
            row += f"{100 * gap:>+8.2f}{100 * se:>7.2f}"
            row += f"{gap / se:>+7.1f}" if se else f"{'-':>7}"
            row += f"{favour:>4}/{ref_n * n:<3}"
            entry["vs_reference"][name] = {
                "gap_points": 100 * gap,
                "se_points": 100 * se,
                "se_units": gap / se if se else None,
                "pairs_favouring": favour,
                "pairs_total": ref_n * n,
                "sd_borrowed_from_reference": sd_borrowed,
            }
        click.echo(row)
        table[band] = entry

    if borrowed:
        click.echo(
            "\nnote: an arm with a single seed has no between-seed sd of its own and was "
            f"given {ref_name}'s, so its SE assumes the two arms vary alike."
        )
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(
                {
                    "bands_report": str(bands),
                    "k": report["k"],
                    "order": report["order"],
                    "arms": {n: r for n, r in parsed},
                    "reference_arm": ref_name,
                    "bands": table,
                },
                indent=2,
            )
        )
        click.echo(f"\nwrote {out}")


if __name__ == "__main__":
    main()
