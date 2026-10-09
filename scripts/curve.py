"""Render a run's ``history.json`` as a markdown table.

Step-based evaluation turns every run into a curve rather than a point, and the
curve is what answers "is this converged, or did the cap cut it off?". Reading
it out of the raw log means parsing tqdm carriage returns; ``history.json`` has
it structured already, so this just formats it.

    python scripts/curve.py checkpoints/small_1m [checkpoints/medium_1m ...]

Numbers come from each run's *own* validation subsample, so columns are
comparable *down* a run and not *across* runs -- for that, see
``scripts/compare_checkpoints.py``, which scores every checkpoint on one
common evaluation set.
"""

from __future__ import annotations

import json
from pathlib import Path

import click


def rows(history: list[dict], k: int) -> list[tuple]:
    out = []
    for record in history:
        valid = record.get("valid") or {}
        slices = valid.get("slices") or {}
        unseen = (slices.get("fp_unseen") or {}).get("recovery_at_k") or {}
        all_ = (slices.get("all") or {}).get("recovery_at_k") or {}
        if not unseen:
            continue  # an epoch with no evaluation attached
        out.append(
            (
                record.get("epoch"),
                record.get("step"),
                record.get("train_loss"),
                record.get("valid_loss"),
                unseen.get(str(k)),
                all_.get(str(k)),
                (slices.get("all") or {}).get("validity"),
            )
        )
    return out


@click.command()
@click.argument("run_dirs", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option("--k", default=20, show_default=True, help="recovery@k column to show")
def main(run_dirs: tuple[Path, ...], k: int) -> None:
    for run_dir in run_dirs:
        path = run_dir / "history.json"
        if not path.exists():
            click.echo(f"{run_dir}: no history.json yet")
            continue
        history = json.loads(path.read_text())
        table = rows(history, k)
        click.echo(f"\n### {run_dir.name}  ({len(history)} evaluations)\n")
        if not table:
            click.echo("no evaluations recorded yet")
            continue
        click.echo(
            f"| epoch | step | train | valid loss | rec@{k} unseen | rec@{k} all | validity |"
        )
        click.echo("|---|---|---|---|---|---|---|")
        for epoch, step, train, vloss, unseen, all_, validity in table:

            def fmt(x: float | None, places: int = 4) -> str:
                return "--" if x is None else f"{x:.{places}f}"

            click.echo(
                f"| {epoch} | {step if step is not None else '--'} | "
                f"{fmt(train)} | {fmt(vloss)} | "
                f"**{fmt(unseen)}** | {fmt(all_)} | {fmt(validity, 3)} |"
            )

        best = max(table, key=lambda r: r[4] or 0.0)
        where = f"epoch {best[0]}" + (f" step {best[1]}" if best[1] is not None else "")
        click.echo(f"\nbest rec@{k} unseen: {best[4]:.4f} at {where}")


if __name__ == "__main__":
    main()
