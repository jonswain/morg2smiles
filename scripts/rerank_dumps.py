"""Re-score every dumped run under consensus ordering, for free.

`compare_checkpoints.py --dump-outcomes` wrote each query's judged candidates,
so the effect of re-ordering them can be measured without sampling anything
again. The candidate sets are exactly those of the common protocol; only the
order changes.

The question this answers that a single run cannot: is consensus ranking a
general property of the task, or an artefact of one strong model? A gain that
grows with model quality means confidence is being learned; a flat gain means
it is a property of sampling with replacement.
"""

from __future__ import annotations

import json
from pathlib import Path

import click

from morg2smiles.metrics import QueryOutcome, evaluate
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


@click.command()
@click.option(
    "--dumps",
    type=click.Path(exists=True, path_type=Path),
    default=Path("results/overnight3/outcomes"),
)
@click.option("--budget", default="molecules")
@click.option(
    "--out", type=click.Path(path_type=Path), default=Path("results/overnight4/rerank.json")
)
def main(dumps: Path, budget: str, out: Path) -> None:
    report = {}
    header = (
        f"{'run':<18}{'n':>6}"
        + "".join(f"{'gen@' + str(k):>9}{'con@' + str(k):>9}{'delta':>8}" for k in (1, 5))
        + f"{'rec@20':>9}"
    )
    click.echo(header)
    click.echo("-" * len(header))
    for path in sorted(dumps.glob("*.jsonl")):
        outcomes = load(path, budget)
        full = evaluate(outcomes, ks=(1, 5, 20))
        unseen = full["slices"]["fp_unseen"]
        gen, con = unseen["recovery_at_k"], unseen["recovery_at_k_consensus"]
        report[path.stem] = {
            "n_fp_unseen": unseen["n_queries"],
            "generation": gen,
            "consensus": con,
            "structure_generation": unseen["structure_accuracy_at_k"],
            "structure_consensus": unseen["structure_accuracy_at_k_consensus"],
            "duplicate_rate": unseen["duplicate_rate"],
            "unique_valid_per_query": unseen["unique_valid_per_query"],
        }
        row = f"{path.stem:<18}{unseen['n_queries']:>6}"
        for k in ("1", "5"):
            row += f"{gen[k]:>9.4f}{con[k]:>9.4f}{100 * (con[k] - gen[k]):>+8.2f}"
        row += f"{gen['20']:>9.4f}"
        click.echo(row)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    click.echo(f"\nwrote {out}")


if __name__ == "__main__":
    main()
