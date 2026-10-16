"""Where in the size distribution does a difference between two runs live?

Night 4 established two things that this script exists to combine. Recovery
collapses with molecule size -- 0.88 below 20 heavy atoms, 0.02 above 50 -- and
the error bar on a comparison is a *paired* one, so it shrinks when two runs
share a checkpoint and grows when a band holds few queries. A gap quoted over
the whole protocol therefore says nothing about where the model changed, and a
gap quoted inside a band says nothing at all unless the band is big enough to
carry it.

Both come out of the dumped outcomes for free. For every band this reports each
run's recovery, every pairwise gap with McNemar's exact p-value, and -- when
three or more runs are passed, as the three variance seeds are -- the
between-run sd *within that band*, which is the detection threshold any future
training experiment has to beat there.

Two uses:

* Fixing the metric for an experiment before it runs. The size-weighted mix is
  aimed at the 30-39 band; what counts as a result there is the seed sd in that
  band, not the 0.75 points measured over the whole protocol.
* Reading an intervention per band. The temperature dumps (T=0.6, 0.7, 1.0 on
  one checkpoint) are paired on the same molecules, so cooling the decoder can
  be followed band by band without generating anything again.

Bands may overlap: ``30-39`` and ``35+`` are both useful and both reported.
"""

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path
from statistics import mean, stdev

import click
from rdkit import Chem

from morg2smiles.stats import discordance, mcnemar_exact, paired_se
from scripts.variance_analysis import hits, load

DEFAULT_BANDS = "0-24,25-29,30-34,35-39,40-49,50+,30-39,35+,all"


def parse_band(spec: str) -> tuple[str, int, int]:
    """``"30-39"``, ``"35+"`` or ``"all"`` to an inclusive bound pair."""
    if spec == "all":
        return spec, 0, 10**6
    if spec.endswith("+"):
        return spec, int(spec[:-1]), 10**6
    lo, hi = spec.split("-")
    return spec, int(lo), int(hi)


def heavy_atoms(smiles: str) -> int:
    mol = Chem.MolFromSmiles(smiles)
    return mol.GetNumHeavyAtoms() if mol is not None else 0


@click.command()
@click.option(
    "--dumps",
    type=click.Path(exists=True, path_type=Path),
    default=Path("results/overnight4/outcomes"),
    help="Directory of *.jsonl outcome dumps, all scored on the same molecules.",
)
@click.option("--glob", "pattern", default="*.jsonl")
@click.option("--bands", default=DEFAULT_BANDS, show_default=True)
@click.option("--budget", default="molecules")
@click.option("--k", default=20)
@click.option("--order", default="consensus", type=click.Choice(["generation", "consensus"]))
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    default=Path("results/overnight5/band_analysis.json"),
)
def main(dumps, pattern, bands, budget, k, order, out) -> None:
    paths = sorted(dumps.glob(pattern))
    if not paths:
        raise click.ClickException(f"no dumps matching {pattern} in {dumps}")

    runs, refs = {}, None
    for path in paths:
        outcomes = load(path, budget)
        mine = [o.reference_smiles for o in outcomes if o.fp_unseen]
        if refs is None:
            refs = mine
        elif mine != refs:
            raise click.ClickException(f"{path.stem} was scored on different molecules")
        runs[path.stem] = hits(outcomes, k, order)

    sizes = [heavy_atoms(s) for s in refs]
    names = list(runs)
    click.echo(
        f"{len(names)} runs, {len(refs):,} fingerprint-unseen queries, rec@{k} {order} order"
    )
    click.echo(f"runs: {', '.join(names)}\n")

    report = {
        "k": k,
        "order": order,
        "budget": budget,
        "n_fp_unseen": len(refs),
        "runs": names,
        "bands": {},
    }

    for spec in bands.split(","):
        label, lo, hi = parse_band(spec)
        idx = [i for i, size in enumerate(sizes) if lo <= size <= hi]
        if not idx:
            click.echo(f"--- {label} heavy atoms: no queries ---\n")
            continue
        per_run = {name: [runs[name][i] for i in idx] for name in names}
        rates = {name: mean(h) for name, h in per_run.items()}

        pairs = {}
        for a, b_name in combinations(names, 2):
            b_only, a_only = discordance(per_run[a], per_run[b_name])
            gap = 100 * (rates[b_name] - rates[a])
            se = 100 * paired_se(b_only, a_only, len(idx))
            pairs[f"{a}->{b_name}"] = {
                "gap_points": gap,
                "b_only": b_only,
                "a_only": a_only,
                "paired_se_points": se,
                "gap_in_paired_se": gap / se if se else 0.0,
                "mcnemar_p": mcnemar_exact(b_only, a_only),
            }

        band = {
            "n_queries": len(idx),
            "share_of_protocol": len(idx) / len(refs),
            "per_run": rates,
            "pairs": pairs,
        }
        if len(names) >= 3:
            # With identically-trained runs this is the detection threshold in
            # this band; with anything else it is just a spread, so it is
            # labelled as between-run, not as noise.
            band["between_run_sd_points"] = 100 * stdev(rates.values())
            band["between_run_mean"] = mean(rates.values())
        report["bands"][label] = band

        click.echo(f"--- {label} heavy atoms: {len(idx):,} queries ---")
        for name in names:
            click.echo(f"  {name:<22}{rates[name]:.4f}")
        if "between_run_sd_points" in band:
            click.echo(
                f"  {'between-run sd':<22}{band['between_run_sd_points']:.2f} pts "
                f"(mean {band['between_run_mean']:.4f})"
            )
        for key, p in pairs.items():
            pv = p["mcnemar_p"]
            click.echo(
                f"  {key:<34}{p['gap_points']:>+7.2f} pts  SE {p['paired_se_points']:>5.2f}  "
                f"{p['gap_in_paired_se']:>+5.1f} SE  p "
                f"{(f'{pv:.2e}' if pv < 1e-3 else f'{pv:.3f}')}"
            )
        click.echo()

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    click.echo(f"wrote {out}")


if __name__ == "__main__":
    main()
