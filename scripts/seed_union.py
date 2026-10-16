"""Three models, or one model given three times the budget?

Night 4 found on the common protocol that misses are strongly query-intrinsic:
585 of 1,956 queries were missed by all three seeds where 123 would be if the
seeds failed independently. That was a whole-protocol count, and the size cliff
is the one place it matters -- if the cloud account is right and recovery above
35 heavy atoms is a matter of whether twenty draws happen to contain an exact
preimage, then two models trained from different initialisations should be
unlucky on *different* molecules, and an ensemble should be worth more there
than anywhere else.

That is a decision, not a curiosity. Three seeds and one seed at three times
the budget cost the same at inference, and this project has already priced the
second: the return per doubling of k, measured band by band. So the comparison
printed here is the union of the arm's seeds against each seed's own k-curve
extrapolated to the same spend. The extrapolation uses the measured k/2 -> k
factor, and returns decay with k, so it flatters the budget route.

The second table needs no extrapolation at all. Splitting a fixed budget of k
molecules across j seeds -- j models asked for k/j candidates each -- spends
exactly what one seed spends on k, so it answers the same question with
measured numbers only, at the cost of asking it at a smaller k.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from math import log2
from pathlib import Path
from statistics import mean

import click
from rdkit import Chem

from scripts.variance_analysis import load

BANDS = "30-34,35-39,40-49,50+,35+,all"


def _band_bounds(spec: str) -> tuple[int, int]:
    if spec == "all":
        return 0, 10**9
    if spec.endswith("+"):
        return int(spec[:-1]), 10**9
    lo, _, hi = spec.partition("-")
    return int(lo), int(hi)


def _heavy(smiles: str) -> int:
    mol = Chem.MolFromSmiles(smiles)
    return mol.GetNumHeavyAtoms() if mol is not None else 0


def _hit_at(outcome, k: int, field: str) -> bool:
    return any(getattr(r, field) for r in outcome.scored()[:k])


def _share(flags: Iterable[bool]) -> float:
    flags = list(flags)
    return sum(flags) / len(flags) if flags else float("nan")


@click.command()
@click.option(
    "--dumps",
    type=click.Path(exists=True, path_type=Path),
    default=Path("results/overnight5/outcomes_large"),
    show_default=True,
)
@click.option("--runs", required=True, help="Comma-separated run names forming one arm.")
@click.option("--k", default=20, show_default=True)
@click.option("--budget", default="molecules", show_default=True)
@click.option("--metric", type=click.Choice(["recovery", "structure"]), default="recovery")
@click.option("--bands", default=BANDS, show_default=True)
@click.option("--out", type=click.Path(path_type=Path), default=None)
def main(dumps, runs, k, budget, metric, bands, out):
    names = [r for r in runs.split(",") if r]
    field = "fp_match" if metric == "recovery" else "exact_structure"
    loaded = {n: load(dumps / f"{n}.jsonl", budget) for n in names}
    references = [o.reference_smiles for o in next(iter(loaded.values()))]
    for name, outcomes in loaded.items():
        if [o.reference_smiles for o in outcomes] != references:
            raise click.ClickException(f"{name} was scored on different molecules")

    keep = [i for i, o in enumerate(next(iter(loaded.values()))) if o.fp_unseen]
    heavy = {i: _heavy(references[i]) for i in keep}
    hits = {n: {i: _hit_at(loaded[n][i], k, field) for i in keep} for n in names}
    half = {n: {i: _hit_at(loaded[n][i], max(k // 2, 1), field) for i in keep} for n in names}

    click.echo(f"{dumps}  k={k}  metric={metric}  arm of {len(names)}: {', '.join(names)}")
    header = (
        f"{'band':>7}{'n':>7}{'one seed':>10}{'union':>8}{'if indep':>10}"
        f"{'all miss':>10}{'luck':>7}{'k x3':>8}"
    )
    click.echo(header)
    click.echo("-" * len(header))
    report = {"dumps": str(dumps), "runs": names, "k": k, "metric": metric, "bands": {}}
    for spec in bands.split(","):
        lo, hi = _band_bounds(spec)
        idx = [i for i in keep if lo <= heavy[i] <= hi]
        if not idx:
            continue
        per_seed = [_share(hits[n][i] for i in idx) for n in names]
        one = mean(per_seed)
        union = _share(any(hits[n][i] for n in names) for i in idx)
        independent = 1 - prod(1 - p for p in per_seed)
        all_miss = _share(not any(hits[n][i] for n in names) for i in idx)
        # What the same spend buys from one seed instead: the measured k/2 -> k
        # factor, applied over the log2(len(names)) further doublings.
        factors = [
            _share(hits[n][i] for i in idx) / _share(half[n][i] for i in idx)
            if _share(half[n][i] for i in idx)
            else float("nan")
            for n in names
        ]
        projected = min(one * mean(factors) ** log2(len(names)), 1.0)
        luck = (union - one) / (1 - one) if one < 1 else float("nan")
        click.echo(
            f"{spec:>7}{len(idx):>7,}{one:>10.4f}{union:>8.4f}{independent:>10.4f}"
            f"{all_miss:>10.4f}{luck:>7.1%}{projected:>8.4f}"
        )
        report["bands"][spec] = {
            "n_queries": len(idx),
            "per_seed": dict(zip(names, per_seed, strict=True)),
            "one_seed": one,
            "union": union,
            "union_if_independent": independent,
            "all_seeds_miss": all_miss,
            "luck_share_of_misses": luck,
            "doubling_factor": mean(factors),
            "projected_one_seed_at_k_times_n": projected,
        }

    click.echo(
        "\nluck = the share of one seed's misses that some other seed recovered; "
        f"k x{len(names)} = one seed extrapolated to the same spend at its measured "
        f"{max(k // 2, 1)} -> {k} return, which overstates it."
    )

    # Equal spend, no extrapolation: j seeds asked for k/j candidates each.
    splits = [j for j in range(1, len(names) + 1) if k // j >= 1]
    click.echo(f"\nthe same {k} molecules of budget, split across seeds")
    header = f"{'band':>7}{'n':>7}" + "".join(f"{f'{j} x {k // j}':>12}" for j in splits)
    click.echo(header)
    click.echo("-" * len(header))
    split_hits = {
        j: {n: {i: _hit_at(loaded[n][i], k // j, field) for i in keep} for n in names}
        for j in splits
    }
    for spec in bands.split(","):
        lo, hi = _band_bounds(spec)
        idx = [i for i in keep if lo <= heavy[i] <= hi]
        if not idx:
            continue
        cells, values = "", {}
        for j in splits:
            value = mean(
                _share(any(split_hits[j][n][i] for n in names[s : s + j]) for i in idx)
                for s in range(0, len(names) - j + 1)
            )
            values[j] = value
            cells += f"{value:>12.4f}"
        click.echo(f"{spec:>7}{len(idx):>7,}{cells}")
        if spec in report["bands"]:
            report["bands"][spec]["equal_spend"] = {
                f"{j}_seeds_at_k_{k // j}": values[j] for j in splits
            }
    click.echo(
        "\nevery column spends the same number of oracle calls; j > 1 averages "
        "over the windows of j consecutive seeds."
    )
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        click.echo(f"wrote {out}")


def prod(values: Iterable[float]) -> float:
    total = 1.0
    for v in values:
        total *= v
    return total


if __name__ == "__main__":
    main()
