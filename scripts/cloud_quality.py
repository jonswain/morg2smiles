"""Does an intervention move the proposal cloud, or only the score?

The account the night settled on is that at every molecule size the decoder
proposes about twenty molecules roughly 0.68 Tanimoto from the target, and
recovery is whether that cloud happens to contain an exact preimage -- which
gets exponentially less likely as the molecule grows. The account predicts two
things about any intervention that works above 35 heavy atoms: the cloud
should measurably tighten, and the same tightening should convert into less
and less recovery as the band gets larger.

Both are testable from the dumps, without retraining anything. This groups
`miss_anatomy.py` reports into arms, reads the between-seed spread of each
quantity off the reference arm, and divides the recovery gain by the cloud
gain to get the conversion -- recovery points bought per point of Tanimoto.

One caveat on the levels. `miss_anatomy.py` reads rec@k off the first k slots
of the dumped candidate list, while the protocols spend a budget of k *unique
valid molecules*, so the recovery printed here runs some four points below the
protocol's own number for the same checkpoints and queries. The arms are all
read the same way, so the gaps and the conversion are sound; the levels should
be taken from `band_analysis.py`.
"""

from __future__ import annotations

import json
import statistics as st
from pathlib import Path

import click

QUANTITIES = (
    ("mean_best_tanimoto_among_misses", "best Tanimoto on a miss"),
    ("fraction_of_misses_above_0.9_tanimoto", "misses above 0.9 Tanimoto"),
    ("collision_rate_among_hits", "collisions among hits"),
    ("recovery", "recovery"),
    ("structure", "structure accuracy"),
)


def _arm(spec: str) -> tuple[str, list[str]]:
    name, _, runs = spec.partition("=")
    return name, [r for r in runs.split(",") if r]


@click.command()
@click.option(
    "--reports",
    type=click.Path(path_type=Path),
    default=Path("results/overnight5"),
    show_default=True,
    help="Directory of miss_anatomy_<tag>_<run>.json reports.",
)
@click.option("--prefix", default="miss_anatomy_large_", show_default=True)
@click.option("--arm", "arms", multiple=True, required=True, help="name=run1,run2 -- repeat.")
@click.option("--bands", default="30-34,35-39,40-49,50+,35+,all", show_default=True)
@click.option("--out", type=click.Path(path_type=Path), default=None)
def main(reports, prefix, arms, bands, out):
    parsed = [_arm(a) for a in arms]
    loaded = {
        run: json.loads((reports / f"{prefix}{run}.json").read_text())["bands"]
        for _, runs in parsed
        for run in runs
    }
    band_order = [b for b in bands.split(",") if b in next(iter(loaded.values()))]
    ref_name, ref_runs = parsed[0]

    result = {"prefix": prefix, "arms": {n: r for n, r in parsed}, "quantities": {}}
    for key, label in QUANTITIES:
        click.echo(f"=== {label} ===")
        header = f"{'band':>7}{'n':>7}{ref_name:>12}{'(sd)':>9}" + "".join(
            f"{n:>12}{'gap':>9}" for n, _ in parsed[1:]
        )
        click.echo(header)
        click.echo("-" * len(header))
        rows = {}
        for band in band_order:
            ref = [loaded[r][band][key] for r in ref_runs]
            mean = st.mean(ref)
            sd = st.stdev(ref) if len(ref) > 1 else float("nan")
            line = f"{band:>7}{loaded[ref_runs[0]][band]['n_queries']:>7,}{mean:>12.4f}{sd:>9.4f}"
            row = {"n_queries": loaded[ref_runs[0]][band]["n_queries"], ref_name: mean, "sd": sd}
            for name, runs in parsed[1:]:
                value = st.mean([loaded[r][band][key] for r in runs])
                line += f"{value:>12.4f}{100 * (value - mean):>+9.2f}"
                row[name] = value
                row[f"{name}_gap_points"] = 100 * (value - mean)
            click.echo(line)
            rows[band] = row
        click.echo()
        result["quantities"][key] = rows

    # The conversion: recovery points bought per point of Tanimoto on a miss.
    tan = result["quantities"]["mean_best_tanimoto_among_misses"]
    rec = result["quantities"]["recovery"]
    click.echo("=== recovery points per point of cloud tightening ===")
    header = f"{'band':>7}" + "".join(f"{n:>26}" for n, _ in parsed[1:])
    click.echo(header)
    click.echo("-" * len(header))
    conversion = {}
    for band in band_order:
        cells = ""
        conversion[band] = {}
        for name, _ in parsed[1:]:
            d_tan = tan[band][f"{name}_gap_points"]
            d_rec = rec[band][f"{name}_gap_points"]
            ratio = d_rec / d_tan if abs(d_tan) > 1e-9 else None
            conversion[band][name] = {
                "tanimoto_points": d_tan,
                "recovery_points": d_rec,
                "ratio": ratio,
            }
            shown = "--" if ratio is None else f"{ratio:+.2f}"
            cells += f"{f'{d_rec:+.2f} / {d_tan:+.2f} = {shown}':>26}"
        click.echo(f"{band:>7}{cells}")
    result["conversion"] = conversion

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2))
        click.echo(f"\nwrote {out}")


if __name__ == "__main__":
    main()
