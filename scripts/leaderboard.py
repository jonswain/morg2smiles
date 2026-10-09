#!/usr/bin/env python
"""Show the experiment ledger.

Rows are sorted by the primary metric -- recovery@k on fingerprints unseen in
training -- not by the memorisable ``all``-slice number. That is deliberate: a
leaderboard sorted on the flattering metric would steer an iteration loop
straight into memorisation.

Usage:
    python scripts/leaderboard.py
    python scripts/leaderboard.py --split test --limit 10
    python scripts/leaderboard.py --show 3        # full detail for a row
"""

from __future__ import annotations

import json
from pathlib import Path

import click

LEADERBOARD = Path("results/leaderboard.jsonl")


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _recovery(record: dict, slice_name: str, k: str) -> float | None:
    try:
        return record["model_report"]["slices"][slice_name]["recovery_at_k"][k]
    except (KeyError, TypeError):
        return None


def _fmt(value: float | None, width: int = 9, places: int = 4) -> str:
    return f"{'-':>{width}}" if value is None else f"{value:>{width}.{places}f}"


@click.command()
@click.option("--path", default=str(LEADERBOARD), type=click.Path(path_type=Path), show_default=True)
@click.option("--split", type=click.Choice(["valid", "test"]), help="Filter by evaluation split.")
@click.option("--limit", default=20, show_default=True)
@click.option("--sort-by-time", is_flag=True, help="Most recent first instead of best first.")
@click.option("--show", type=int, help="Print the full JSON record for this row number.")
def main(path, split, limit, sort_by_time, show):
    """Render results/leaderboard.jsonl as a table."""
    records = load_records(Path(path))
    if split:
        records = [r for r in records if r.get("split") == split]
    if not records:
        click.echo(f"no records in {path}")
        return

    for i, record in enumerate(records):
        record["_row"] = i
    if sort_by_time:
        ordered = list(reversed(records))
    else:
        ordered = sorted(records, key=lambda r: r.get("primary_metric") or -1, reverse=True)
    ordered = ordered[:limit]

    if show is not None:
        match = next((r for r in records if r["_row"] == show), None)
        if match is None:
            click.echo(f"no row {show}")
            return
        match.pop("_row", None)
        click.echo(json.dumps(match, indent=2))
        return

    header = (
        f"{'row':>4} {'when':<17} {'split':<6} {'params':>8} "
        f"{'rec@1':>9} {'rec@20':>9} {'UNSEEN@20':>10} {'base@20':>9} {'delta':>9}  note"
    )
    click.echo(header)
    click.echo("-" * len(header))

    for record in ordered:
        model_unseen = _recovery(record, "fp_unseen", "20")
        base_unseen = None
        try:
            base_unseen = record["baseline_report"]["slices"]["fp_unseen"]["recovery_at_k"]["20"]
        except (KeyError, TypeError):
            pass
        delta = (
            model_unseen - base_unseen
            if model_unseen is not None and base_unseen is not None
            else None
        )

        row = (
            f"{record['_row']:>4} "
            f"{record.get('timestamp', '')[:17]:<17} "
            f"{record.get('split', ''):<6} "
            f"{record.get('n_parameters', 0) / 1e6:>7.1f}M"
            f"{_fmt(_recovery(record, 'all', '1'))}"
            f"{_fmt(_recovery(record, 'all', '20'))}"
            f"{_fmt(model_unseen, 10)}"
            f"{_fmt(base_unseen)}"
            f"{_fmt(delta)}"
            f"  {record.get('note', '')}"
        )
        colour = None
        if delta is not None:
            colour = "green" if delta > 0 else "red"
        click.secho(row, fg=colour)

    click.echo("")
    click.echo(
        "UNSEEN@20 is the primary metric: recovery@20 on fingerprints absent from training. "
        "delta is model minus retrieval baseline; a non-positive delta means the model has "
        "not learned to reconstruct."
    )


if __name__ == "__main__":
    main()
