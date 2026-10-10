"""Score every checkpoint on one common, uncontaminated evaluation set.

Why this exists rather than just reading the leaderboard: each run reports on
its own shard's validation split, and **the shard subsets are nested**. The 10k,
100k and 1M shards are drawn in order from one fixed shuffle, and each computes
its train/valid/test split within itself. So a molecule held out of the 100k
shard is very often *inside* the 1M shard's training set -- measured here at
4,540 of 5,037, or 90%.

Evaluating a 1M-trained model on the 100k shard's validation split therefore
measures memorisation, and comparing two models trained on different shards via
their own splits is meaningless. Nothing in the per-run numbers is wrong; they
simply answer a different question each.

This script builds one evaluation set that is held out of *every* model's
training data, computes the ``fp_unseen`` mask against the **union** of all
training fingerprints, and scores each checkpoint on identical molecules with an
identical seed, budget and k. Only then are the numbers comparable.

The test splits are not touched. Everything here comes from validation.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import click

from morg2smiles.baselines.nearest_neighbour import evaluate_baseline
from morg2smiles.data.dataset import _fp_key, load_split
from morg2smiles.evaluation import evaluate_model
from morg2smiles.fingerprints import compute
from morg2smiles.metrics import format_report
from morg2smiles.model import Morg2SmilesModel, select_device

# Checkpoint -> the shard it trained on. Kept explicit: inferring it from the
# checkpoint's record would be convenient and would silently mis-slice if a
# config were ever edited after a run.
RUNS = [
    ("small_100k", "checkpoints/small/best.pt", "data/shards/100k"),
    ("small_1m", "checkpoints/small_1m/best.pt", "data/shards/1m"),
    ("medium_1m", "checkpoints/medium_1m/best.pt", "data/shards/1m"),
    ("small_100k_long", "checkpoints/small_100k_long/best.pt", "data/shards/100k"),
    ("small_1m_matched", "checkpoints/small_1m_matched/best.pt", "data/shards/1m"),
    ("small_full", "checkpoints/small_full/best.pt", "data/shards/full"),
]


def present_runs() -> list[tuple[str, str, str]]:
    return [(n, c, s) for n, c, s in RUNS if Path(c).exists()]


@click.command()
@click.option("--eval-n", default=2000, show_default=True, help="Molecules in the common set.")
@click.option("--seed", default=0, show_default=True)
@click.option("--budget", default="molecules", type=click.Choice(["molecules", "strings"]))
@click.option("--eval-k", default=20, show_default=True)
@click.option("--baseline/--no-baseline", default=True, show_default=True)
@click.option("--pool-shard", default="data/shards/1m", show_default=True)
@click.option("--out", type=click.Path(path_type=Path), default=Path("results/comparison.json"))
def main(
    eval_n: int,
    seed: int,
    budget: str,
    eval_k: int,
    baseline: bool,
    pool_shard: str,
    out: Path,
) -> None:
    runs = present_runs()
    if not runs:
        raise click.ClickException("no checkpoints found; nothing to compare")
    click.echo(f"comparing {len(runs)} checkpoint(s): {', '.join(n for n, _, _ in runs)}")

    # Every training set in play, by molecule and by fingerprint.
    shards = sorted({shard for _, _, shard in runs})
    train_molecules: set[str] = set()
    for shard in shards:
        train_molecules |= set(load_split(shard, "train"))
    click.echo(f"union of training sets: {len(train_molecules):,} molecules from {shards}")

    # The pool: validation molecules of the largest shard, minus anything any
    # model trained on.
    pool = [s for s in load_split(pool_shard, "valid") if s not in train_molecules]
    click.echo(f"clean pool: {len(pool):,} of {pool_shard} valid, held out of every training set")

    rng = random.Random(seed)
    eval_smiles = [pool[i] for i in sorted(rng.sample(range(len(pool)), min(eval_n, len(pool))))]

    # fp_unseen against the union, so the primary slice is honest for every
    # model rather than only for the one whose shard supplied the split.
    fp_cfg = Morg2SmilesModel.load(runs[0][1], device=select_device())[0].fp_cfg
    click.echo(f"indexing {len(train_molecules):,} training fingerprints ...")
    train_keys = {_fp_key(compute(s, fp_cfg)) for s in train_molecules}
    fp_unseen = [_fp_key(compute(s, fp_cfg)) not in train_keys for s in eval_smiles]
    click.echo(
        f"evaluation set: {len(eval_smiles):,} molecules, "
        f"{sum(fp_unseen):,} with fingerprints unseen in any training set"
    )

    results: dict = {
        "protocol": {
            "eval_n": len(eval_smiles),
            "seed": seed,
            "budget": budget,
            "eval_k": eval_k,
            "pool_shard": pool_shard,
            "split": "valid",
            "n_fp_unseen": sum(fp_unseen),
            "training_union_size": len(train_molecules),
            "shards_excluded": shards,
        },
        "runs": {},
    }

    device = select_device()
    for name, checkpoint, shard in runs:
        click.echo(f"\n--- {name} ({checkpoint}) ---")
        model, ckpt = Morg2SmilesModel.load(checkpoint, device=device)
        report = evaluate_model(
            model,
            eval_smiles,
            k=eval_k,
            fp_unseen=fp_unseen,
            budget=budget,
            seed=seed,
        )
        click.echo(format_report(report))
        results["runs"][name] = {
            "checkpoint": checkpoint,
            "train_shard": shard,
            "n_parameters": model.n_parameters,
            "trained_epoch": ckpt.get("epoch"),
            "trained_step": ckpt.get("step"),
            "model_config": model.cfg.to_dict(),
            "report": report,
        }
        del model

    if baseline:
        click.echo("\n--- retrieval baseline (union of training sets) ---")
        base = evaluate_baseline(
            sorted(train_molecules), eval_smiles, fp_cfg, k=eval_k, fp_unseen=fp_unseen
        )
        click.echo(format_report(base))
        results["baseline"] = base

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    click.echo(f"\nwrote {out}")

    # Final table: one protocol, so these rows are comparable.
    click.echo("\n" + "=" * 78)
    click.echo("COMMON PROTOCOL -- recovery on fingerprints unseen in any training set")
    click.echo("=" * 78)
    header = f"{'run':<12} {'params':>8} {'shard':>16} {'rec@1':>8} {'rec@5':>8} {'rec@20':>8}"
    click.echo(header)
    click.echo("-" * len(header))
    rows = list(results["runs"].items())
    if "baseline" in results:
        rows.append(("retrieval", {"report": results["baseline"], "n_parameters": 0}))
    for name, payload in rows:
        unseen = payload["report"]["slices"]["fp_unseen"]
        rec = unseen.get("recovery_at_k", {})
        params = payload.get("n_parameters") or 0
        shard = payload.get("train_shard", "-")
        click.echo(
            f"{name:<12} {params / 1e6:>7.1f}M {Path(shard).name:>16} "
            f"{rec.get('1', 0):>8.4f} {rec.get('5', 0):>8.4f} {rec.get('20', 0):>8.4f}"
        )


if __name__ == "__main__":
    main()
