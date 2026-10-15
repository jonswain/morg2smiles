"""Test every past pairwise claim against the error bar night 4 measured.

Each run in the common protocol was scored on the *same* 1,956 fingerprint-
unseen molecules, and ``--dump-outcomes`` kept each query's verdict, so any two
runs can be compared as a paired test rather than by subtracting two rates.
That is the comparison this project has been making by eye since night 1.

For runs A and B, ``b`` is the number of queries B solves and A does not and
``c`` the reverse; everything else cancels. McNemar's exact test gives the
probability of a split that lopsided if the two runs were equally good:
two-sided ``2 * P(X <= min(b, c))`` for ``X ~ Binomial(b + c, 1/2)``.

The p-value answers "could this gap be sampling noise on these molecules?" It
does *not* answer "could this gap be training-seed luck?" -- for that the three
variance seeds give an sd directly, and a difference needs to clear both. Both
are reported next to each gap.
"""

from __future__ import annotations

import json
from itertools import combinations
from math import sqrt
from pathlib import Path

import click

from morg2smiles.stats import discordance, mcnemar_exact, paired_se
from scripts.variance_analysis import hits, load

SEED_SD_POINTS = 0.75  # rec@20, generation order, three seeds at 8,508 steps


@click.command()
@click.option(
    "--dumps",
    type=click.Path(exists=True, path_type=Path),
    default=Path("results/overnight3/outcomes"),
)
@click.option("--budget", default="molecules")
@click.option("--k", default=20)
@click.option("--order", default="generation", type=click.Choice(["generation", "consensus"]))
@click.option(
    "--pair",
    multiple=True,
    help="Compare just these pairs, as A:B. Default: every pair, ordered by gap.",
)
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    default=Path("results/overnight4/paired_tests.json"),
)
def main(dumps: Path, budget: str, k: int, order: str, pair: tuple[str, ...], out: Path) -> None:
    runs = {p.stem: hits(load(p, budget), k, order) for p in sorted(dumps.glob("*.jsonl"))}
    n = len(next(iter(runs.values())))
    click.echo(f"{len(runs)} runs, {n:,} fingerprint-unseen queries, rec@{k} {order} order\n")

    wanted = [tuple(p.split(":")) for p in pair] if pair else list(combinations(runs, 2))
    rows = []
    for a, b_name in wanted:
        ha, hb = runs[a], runs[b_name]
        b, c = discordance(ha, hb)
        gap = 100 * (sum(hb) - sum(ha)) / n
        se = 100 * paired_se(b, c, n)
        rows.append(
            {
                "a": a,
                "b": b_name,
                "rate_a": sum(ha) / n,
                "rate_b": sum(hb) / n,
                "gap_points": gap,
                "b_only": b,
                "a_only": c,
                "paired_se_points": se,
                "gap_in_paired_se": gap / se if se else 0.0,
                "mcnemar_p": mcnemar_exact(b, c),
                "gap_in_seed_sd": gap / (SEED_SD_POINTS * sqrt(2)),
            }
        )
    rows.sort(key=lambda r: abs(r["gap_points"]))

    header = (
        f"{'comparison':<40}{'gap':>8}{'pairedSE':>10}{'xSE':>7}{'McNemar p':>12}{'x seed sd':>11}"
    )
    click.echo(header)
    click.echo("-" * len(header))
    for r in rows:
        p = r["mcnemar_p"]
        click.echo(
            f"{r['a'] + ' -> ' + r['b']:<40}{r['gap_points']:>+8.2f}{r['paired_se_points']:>10.2f}"
            f"{r['gap_in_paired_se']:>+7.1f}{(f'{p:.2e}' if p < 1e-3 else f'{p:.3f}'):>12}"
            f"{r['gap_in_seed_sd']:>+11.1f}"
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {"k": k, "order": order, "n": n, "seed_sd_points": SEED_SD_POINTS, "pairs": rows},
            indent=2,
        )
    )
    click.echo(f"\nwrote {out}")


if __name__ == "__main__":
    main()
