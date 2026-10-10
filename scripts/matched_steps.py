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

One caveat this script cannot remove: each run evaluates against the validation
split of *its own* shard, so the rows below are matched on compute but not on
the molecules being asked for. That is fine for reading whether a run is ahead
or behind and by roughly how much, and it is not good enough for a headline
number. The headline comes from scripts/compare_checkpoints.py, which puts every
checkpoint against one holdout set that was excluded from every training set.

Usage::

    python scripts/matched_steps.py small_100k_long small_1m small_full
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

METRIC = ("fp_unseen", "recovery_at_k", "20")


def protocol(rec: dict) -> tuple:
    """A signature of how this evaluation was scored.

    Matching the step is not enough to make two numbers comparable: the
    in-training evaluation protocol changed during the project. The older runs
    drew a fixed number of *strings* per query, the newer ones draw until they
    have a fixed number of distinct *molecules*, which is a strictly larger
    budget and scores several points higher on identical weights. Put those two
    in adjacent columns and the difference reads as data or compute when it is
    neither -- the same class of mistake this script exists to prevent, so it is
    checked rather than left to the reader.

    Cross-run numbers under one deliberate protocol come from
    scripts/compare_checkpoints.py, which re-evaluates every checkpoint itself.

    Deliberately excludes ``n_queries``: it lands at 499 against 493 here only
    because a different number of the 500 sampled molecules happened to be
    fp-unseen, which is a property of the shard and not of the protocol.
    """
    valid = rec.get("valid") or {}
    slice_ = valid.get("slices", {}).get("fp_unseen", {})
    return (
        valid.get("budget", "legacy-string-budget"),
        tuple(valid.get("ks", ())),
        slice_.get("mean_samples_per_query"),
    )


def load(name: str) -> dict[int, dict]:
    """Return {step: record} for one checkpoint directory."""
    path = Path("checkpoints") / name / "history.json"
    if not path.exists():
        raise SystemExit(f"no history at {path}")
    records = json.loads(path.read_text())
    # The oldest runs logged per epoch and recorded no step at all; there is no
    # way to place those on a step axis, so they are not silently given one.
    missing = [r for r in records if "step" not in r]
    if missing:
        raise SystemExit(
            f"{name}: {len(missing)} of {len(records)} records have no step field "
            "(pre-max_steps schema, logged per epoch). It cannot be placed on a "
            "step axis -- use scripts/compare_checkpoints.py for this run."
        )
    return {rec["step"]: rec for rec in records}


def metric(rec: dict) -> float | None:
    slice_, family, k = METRIC
    try:
        return rec["valid"]["slices"][slice_][family][k]
    except (KeyError, TypeError):
        return None


def main(names: list[str]) -> None:
    runs = {name: load(name) for name in names}

    signatures = {}
    for name, hist in runs.items():
        scored = {protocol(r) for r in hist.values() if r.get("valid")}
        if len(scored) > 1:
            raise SystemExit(f"{name}: evaluation protocol changed mid-run: {scored}")
        signatures[name] = scored.pop() if scored else None

    distinct = {sig for sig in signatures.values() if sig is not None}
    if len(distinct) > 1:
        lines = "\n".join(f"  {n}: {s}" for n, s in signatures.items())
        raise SystemExit(
            "these runs were not scored the same way, so their numbers are not\n"
            "comparable at any step. Signature is (budget, ks, n_queries, "
            "samples/query):\n" + lines + "\n"
            "Use scripts/compare_checkpoints.py, which re-scores every "
            "checkpoint under one protocol."
        )

    shared = set.intersection(*(set(r) for r in runs.values()))
    if not shared:
        cadences = {n: sorted(r)[:4] for n, r in runs.items()}
        raise SystemExit(
            "no step was evaluated in every run; cadences do not line up:\n"
            + "\n".join(f"  {n}: {steps}..." for n, steps in cadences.items())
        )

    print("### rec@20 fp_unseen at matched steps\n")
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
