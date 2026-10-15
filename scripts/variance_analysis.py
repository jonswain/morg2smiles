"""How big is the error bar this repository has never had?

Three runs identical but for ``train.seed`` were trained for 8,508 steps on the
100k shard and scored on the common protocol. This script turns them into the
two numbers every past comparison in this project needed and did not have:

**The between-run sd.** The spread of the headline metric across seeds. Any
claimed difference between two training runs smaller than a couple of these is
not a difference.

**The paired error bar.** Every comparison here scores runs on the *same* 1,956
molecules, so the relevant uncertainty is not the binomial error on 1,956
(0.68 points at p=0.9) nor the between-run sd on its own, but the standard
error of a *paired* difference, estimated from how often two runs disagree on
the same query -- McNemar's sqrt(discordant)/n. With three seeds there are
three pairs whose true difference is zero, so the estimate can be checked
against observed differences instead of assumed.

**Are failures query-intrinsic?** If each seed independently solved a query
with probability p, the number of seeds solving it would be Binomial(3, p).
Mass piled at 0 and 3 beyond that means the misses are a property of the
molecule, not of the run -- which is what night 3's size analysis implies and
what decides whether more seeds or better capability is the way forward.
"""

from __future__ import annotations

import json
from itertools import combinations
from math import comb, sqrt
from pathlib import Path
from statistics import mean, median, stdev

import click
from rdkit import Chem

from morg2smiles.metrics import QueryOutcome
from morg2smiles.oracle import OracleResult

FIELDS = ("smiles", "valid", "fp_match", "exact_structure", "tanimoto", "canonical", "duplicate")


def load(path: Path, budget: str) -> list[QueryOutcome]:
    outcomes = []
    for line in open(path):
        row = json.loads(line)
        outcomes.append(
            QueryOutcome(
                results=[OracleResult(**{f: r[f] for f in FIELDS}) for r in row["results"]],
                fp_unseen=row["fp_unseen"],
                reference_smiles=row["reference"],
                budget=budget,
                n_samples=row["n_samples"],
            )
        )
    return outcomes


def hits(outcomes: list[QueryOutcome], k: int, order: str) -> list[bool]:
    """Per-query hit at k under one ordering, fingerprint-unseen queries only."""
    out = []
    for o in outcomes:
        if not o.fp_unseen:
            continue
        scored = o.scored_by_consensus() if order == "consensus" else o.scored()
        out.append(any(r.fp_match for r in scored[:k]))
    return out


def heavy_atoms(smiles: str) -> int:
    mol = Chem.MolFromSmiles(smiles)
    return mol.GetNumHeavyAtoms() if mol is not None else 0


@click.command()
@click.option(
    "--dumps",
    type=click.Path(exists=True, path_type=Path),
    default=Path("results/overnight4/outcomes"),
)
@click.option("--budget", default="molecules")
@click.option("--k", default=20)
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    default=Path("results/overnight4/variance_analysis.json"),
)
def main(dumps: Path, budget: str, k: int, out: Path) -> None:
    paths = sorted(dumps.glob("variance_s*.jsonl"))
    if len(paths) < 2:
        raise click.ClickException(f"need at least two seeds in {dumps}")
    runs = {p.stem: load(p, budget) for p in paths}
    names = list(runs)
    click.echo(f"{len(names)} seeds: {', '.join(names)}")

    refs = [o.reference_smiles for o in next(iter(runs.values())) if o.fp_unseen]
    for name, outcomes in runs.items():
        theirs = [o.reference_smiles for o in outcomes if o.fp_unseen]
        if theirs != refs:
            raise click.ClickException(f"{name} was scored on different molecules")
    n = len(refs)
    click.echo(f"{n:,} fingerprint-unseen queries, identical across seeds\n")

    report: dict = {"seeds": names, "n_fp_unseen": n, "k": k, "metrics": {}}

    for order in ("generation", "consensus"):
        per_run = {name: hits(o, k, order) for name, o in runs.items()}
        rates = {name: mean(h) for name, h in per_run.items()}
        m, sd = mean(rates.values()), stdev(rates.values())

        # Paired disagreement: the error bar for comparing two runs on one set.
        pairs = {}
        for a, b in combinations(names, 2):
            ha, hb = per_run[a], per_run[b]
            b_only = sum(1 for x, y in zip(ha, hb, strict=True) if not x and y)
            a_only = sum(1 for x, y in zip(ha, hb, strict=True) if x and not y)
            discordant = a_only + b_only
            pairs[f"{a}-{b}"] = {
                "difference_points": 100 * (rates[a] - rates[b]),
                "discordant": discordant,
                "discordant_rate": discordant / n,
                "mcnemar_se_points": 100 * sqrt(discordant) / n,
            }

        # Is a miss a property of the molecule or of the run?
        solved_by = [sum(per_run[name][i] for name in names) for i in range(n)]
        observed = {str(j): solved_by.count(j) for j in range(len(names) + 1)}
        expected = {
            str(j): n * comb(len(names), j) * m**j * (1 - m) ** (len(names) - j)
            for j in range(len(names) + 1)
        }

        sizes = [heavy_atoms(s) for s in refs]
        by_agreement = {
            str(j): {
                "n": solved_by.count(j),
                "median_heavy_atoms": median([sizes[i] for i in range(n) if solved_by[i] == j])
                if solved_by.count(j)
                else None,
            }
            for j in range(len(names) + 1)
        }

        report["metrics"][order] = {
            "per_seed": rates,
            "mean": m,
            "sd_points": 100 * sd,
            "range_points": 100 * (max(rates.values()) - min(rates.values())),
            "se_of_mean_points": 100 * sd / sqrt(len(names)),
            "binomial_se_points": 100 * sqrt(m * (1 - m) / n),
            "pairs": pairs,
            "mean_mcnemar_se_points": mean(p["mcnemar_se_points"] for p in pairs.values()),
            "agreement_observed": observed,
            "agreement_if_independent": expected,
            "agreement_vs_size": by_agreement,
        }

        click.echo(f"--- rec@{k}, {order} order ---")
        for name in names:
            click.echo(f"  {name:<14}{rates[name]:.4f}")
        click.echo(
            f"  mean {m:.4f}  sd {100 * sd:.2f} pts  range {100 * (max(rates.values()) - min(rates.values())):.2f} pts"
        )
        click.echo(
            f"  binomial SE (if runs were independent samples): "
            f"{100 * sqrt(m * (1 - m) / n):.2f} pts"
        )
        for key, p in pairs.items():
            click.echo(
                f"  {key:<28}{p['difference_points']:+6.2f} pts   "
                f"discordant {p['discordant']:>4} ({100 * p['discordant_rate']:.1f}%)   "
                f"paired SE {p['mcnemar_se_points']:.2f} pts"
            )
        click.echo(
            "  seeds solving a query:  "
            + "  ".join(f"{j}:{observed[str(j)]}" for j in range(len(names) + 1))
        )
        click.echo(
            "  if independent:         "
            + "  ".join(f"{j}:{expected[str(j)]:.0f}" for j in range(len(names) + 1))
        )
        click.echo(
            "  median heavy atoms:     "
            + "  ".join(
                f"{j}:{by_agreement[str(j)]['median_heavy_atoms']}" for j in range(len(names) + 1)
            )
        )
        click.echo()

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    click.echo(f"wrote {out}")


if __name__ == "__main__":
    main()
