"""At a fixed oracle budget, is one model better than three?

Night 4 trained three seeds to measure variance, which incidentally produced
something this project has not had: three independently initialised models of
equal cost. Their dumps answer a question about where to spend compute, for
free.

The seeds agree on four fifths of the evaluation set but disagree on 13% of
queries, and 1,371 of 1,956 queries are solved by *at least one* seed against a
single-seed mean of 1,179. That 9.8-point headroom is real but it is not free:
polling three models three ways costs three times the oracle calls, and this
project's budget is oracle calls.

So the comparison has to be made at equal budget. ``k`` candidates are drawn
from the three seeds round-robin by each seed's own consensus rank -- seed 1's
best, seed 2's best, seed 3's best, seed 1's second, and so on -- deduplicated
by canonical SMILES, and cut at ``k``. Each seed therefore contributes about
k/3 candidates and the oracle is called exactly k times, as for a single model.

Reported beside it:

``single``
    Each seed alone at budget k, averaged. The baseline.
``pooled_votes``
    The same three-seed union, but ranked by spelling counts summed across
    seeds rather than round-robin. Consensus ranking worked within one model
    because a model reaches its best answer by several routes; this asks
    whether agreement *between* models is a stronger signal still.
``union_3k``
    Every seed's own top k, unioned: 3k oracle calls. Not a fair comparison,
    included as the ceiling the equal-budget schemes are trying to reach.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import mean

import click

from morg2smiles.stats import discordance, mcnemar_exact, paired_se
from scripts.variance_analysis import load


def hit_at(selected, k: int) -> bool:
    """Does the oracle find the reference among the first k candidates offered?"""
    return any(r.fp_match for r in selected[:k])


@click.command()
@click.option(
    "--dumps",
    type=click.Path(exists=True, path_type=Path),
    default=Path("results/overnight4/outcomes"),
)
@click.option("--budget", default="molecules")
@click.option("--ks", default="1,5,20")
@click.option(
    "--runs",
    default="variance_s1,variance_s2,variance_s3",
    help="Dump stems to combine. Defaults to the three variance seeds.",
)
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    default=Path("results/overnight4/ensemble_seeds.json"),
)
def main(dumps: Path, budget: str, ks: str, runs: str, out: Path) -> None:
    names = [x.strip() for x in runs.split(",")]
    paths = [dumps / f"{name}.jsonl" for name in names]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise click.ClickException(f"no dump for {', '.join(missing)}")
    runs = [load(p, budget) for p in paths]
    n_seeds = len(runs)

    # Fingerprint-unseen queries only, in the order the protocol drew them.
    per_query = []
    for outcomes in zip(*runs, strict=True):
        if not outcomes[0].fp_unseen:
            continue
        assert len({o.reference_smiles for o in outcomes}) == 1
        per_query.append(outcomes)
    n = len(per_query)
    click.echo(f"{n_seeds} seeds ({', '.join(names)}), {n:,} fingerprint-unseen queries\n")

    report = {"seeds": names, "n_fp_unseen": n, "schemes": {}}
    k_list = [int(x) for x in ks.split(",")]

    for k in k_list:
        per_single = [
            [hit_at(q[i].scored_by_consensus(), k) for q in per_query] for i in range(n_seeds)
        ]
        single = [mean(h) for h in per_single]
        best_single = max(single)
        best_hits = per_single[single.index(best_single)]

        round_robin, pooled, union3k = [], [], []
        for outcomes in per_query:
            ranked = [o.scored_by_consensus() for o in outcomes]

            seen, selected = set(), []
            for rank in range(max(len(r) for r in ranked)):
                for cands in ranked:
                    if rank < len(cands) and cands[rank].canonical not in seen:
                        seen.add(cands[rank].canonical)
                        selected.append(cands[rank])
                if len(selected) >= k:
                    break
            round_robin.append(hit_at(selected, k))

            votes: Counter = Counter()
            best: dict[str, object] = {}
            for o in outcomes:
                for r in o.results:
                    if r.valid:
                        votes[r.canonical] += 1
                        best.setdefault(r.canonical, r)
            order = [best[c] for c, _ in votes.most_common()]
            pooled.append(hit_at(order, k))

            union3k.append(any(any(r.fp_match for r in c[:k]) for c in ranked))

        row = {
            "single_per_seed": dict(zip(names, single, strict=True)),
            "single_mean": mean(single),
            "round_robin": mean(round_robin),
            "pooled_votes": mean(pooled),
            "union_3k": mean(union3k),
            "oracle_calls": {
                "single": k,
                "round_robin": k,
                "pooled_votes": k,
                "union_3k": n_seeds * k,
            },
        }
        # Does the ensemble beat the best member, or only the average one?
        # The average is not a thing anyone would deploy; the best member is.
        b, c = discordance(best_hits, pooled)
        row["best_single"] = best_single
        row["pooled_vs_best_single"] = {
            "gap_points": 100 * (mean(pooled) - best_single),
            "ensemble_only": b,
            "best_only": c,
            "paired_se_points": 100 * paired_se(b, c, n),
            "mcnemar_p": mcnemar_exact(b, c),
        }
        row["round_robin_gain_points"] = 100 * (row["round_robin"] - row["single_mean"])
        row["pooled_vs_best_single_points"] = 100 * (row["pooled_votes"] - best_single)
        row["pooled_gain_points"] = 100 * (row["pooled_votes"] - row["single_mean"])
        row["union_gain_points"] = 100 * (row["union_3k"] - row["single_mean"])
        report["schemes"][str(k)] = row

        click.echo(f"--- budget k={k} ---")
        click.echo(
            f"  single model (mean of {n_seeds})     {row['single_mean']:.4f}   {k} oracle calls"
        )
        click.echo(f"  best single model               {best_single:.4f}   {k} oracle calls")
        click.echo(
            f"  all {n_seeds}, round-robin            {row['round_robin']:.4f}   {k} oracle calls"
            f"   {row['round_robin_gain_points']:+.2f} pts"
        )
        click.echo(
            f"  all {n_seeds}, pooled votes         {row['pooled_votes']:.4f}   {k} oracle calls"
            f"   {row['pooled_gain_points']:+.2f} pts vs mean,"
            f" {row['pooled_vs_best_single_points']:+.2f} vs best"
        )
        click.echo(
            f"  all {n_seeds}, union of top-{k:<2}      {row['union_3k']:.4f}   {n_seeds * k} oracle calls"
            f"   {row['union_gain_points']:+.2f} pts"
        )
        click.echo()

        v = row["pooled_vs_best_single"]
        click.echo(
            f"  pooled vs best single           {v['gap_points']:+.2f} pts"
            f"   paired SE {v['paired_se_points']:.2f}"
            f"   McNemar p {v['mcnemar_p']:.3g}"
            f"   ({v['ensemble_only']} vs {v['best_only']})"
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    click.echo(f"wrote {out}")


if __name__ == "__main__":
    main()
