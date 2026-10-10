"""Align several runs on optimiser step and print them side by side.

``scripts/curve.py`` reads one run down its own history, which answers "is this
still improving?" but not "which of these runs is ahead?". Comparing endpoints
answers that question wrongly whenever the runs stopped at different steps: the
night-1 write-up credited a 30-point gap to 10x more data when the larger-data
run had also taken 2.5x more optimiser steps, and the two cannot be separated
from endpoints alone.

So this reads the step column instead. A row is one step at which *every*
requested run was evaluated, which makes the comparison matched on compute --
same architecture, same batch size, same step count, so the only variable left
is the shard the data came from.

Steps are matched exactly, not by nearest neighbour: an interpolated row would
invite reading a difference that no measurement actually took. Runs whose
evaluation cadences do not line up therefore produce no rows, which is the
honest outcome rather than a misleading one.

Usage::

    python scripts/matched_steps.py small_100k_long small_1m small_full
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

METRIC = ("fp_unseen", "recovery_at_k", "20")


def load(name: str) -> dict[int, dict]:
    """Return {step: record} for one checkpoint directory."""
    path = Path("checkpoints") / name / "history.json"
    if not path.exists():
        raise SystemExit(f"no history at {path}")
    return {rec["step"]: rec for rec in json.loads(path.read_text())}


def metric(rec: dict) -> float | None:
    slice_, family, k = METRIC
    try:
        return rec["valid"]["slices"][slice_][family][k]
    except (KeyError, TypeError):
        return None


def main(names: list[str]) -> None:
    runs = {name: load(name) for name in names}

    shared = set.intersection(*(set(r) for r in runs.values()))
    if not shared:
        cadences = {n: sorted(r)[:4] for n, r in runs.items()}
        raise SystemExit(
            "no step was evaluated in every run; cadences do not line up:\n"
            + "\n".join(f"  {n}: {steps}..." for n, steps in cadences.items())
        )

    print(f"### rec@20 fp_unseen at matched steps\n")
    print("| step | " + " | ".join(names) + " |")
    print("|---" * (len(names) + 1) + "|")
    for step in sorted(shared):
        cells = []
        for name in names:
            value = metric(runs[name][step])
            cells.append("--" if value is None else f"{value:.4f}")
        print(f"| {step} | " + " | ".join(cells) + " |")

    # Each run's own endpoint, which is what a leaderboard reports and what the
    # matched rows above exist to qualify.
    print("\n| run | last step | epochs there | rec@20 unseen |")
    print("|---|---|---|---|")
    for name, hist in runs.items():
        last = max(hist)
        value = metric(hist[last])
        shown = "--" if value is None else f"{value:.4f}"
        print(f"| {name} | {last} | {hist[last]['epoch']} | {shown} |")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    main(sys.argv[1:])
