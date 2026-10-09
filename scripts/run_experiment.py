#!/usr/bin/env python
"""Run one experiment end to end and append it to the leaderboard.

This is the entry point an autonomous iteration loop drives: change one thing
in a config, run this, read the leaderboard, repeat.

**The guardrail that makes that safe:** this script evaluates on the
**validation** split by default. The test split requires ``--split test``, and
the record is tagged with which split was used. An iteration loop makes
hundreds of choices against whatever number it can see; if that number came
from the test split, the test split stops being held out after the first few
iterations and the final figure becomes meaningless. Validation is the thing to
optimise. Test is for occasional, deliberate measurement.
"""

from __future__ import annotations

import json
import platform
import subprocess
import time
from dataclasses import replace
from pathlib import Path

import click
import torch

from morg2smiles.baselines.nearest_neighbour import evaluate_baseline
from morg2smiles.data.dataset import fp_unseen_mask, load_split
from morg2smiles.evaluation import evaluate_model
from morg2smiles.metrics import format_report
from morg2smiles.model import Morg2SmilesModel, select_device
from morg2smiles.train import load_configs, train

LEADERBOARD = Path("results/leaderboard.jsonl")


def git_commit() -> str | None:
    """Current commit, so a leaderboard row can be traced back to the code."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def append_record(record: dict, path: Path = LEADERBOARD) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as handle:
        handle.write(json.dumps(record) + "\n")


@click.command()
@click.option("--config", required=True, type=click.Path(exists=True, path_type=Path))
@click.option(
    "--split",
    default="valid",
    type=click.Choice(["valid", "test"]),
    show_default=True,
    help="Evaluation split. Keep this at 'valid' while iterating.",
)
@click.option("--shard-dir", type=click.Path(path_type=Path), help="Overrides the config.")
@click.option("--out-dir", type=click.Path(path_type=Path), help="Overrides the config.")
@click.option("--epochs", type=int, help="Overrides the config.")
@click.option("--eval-k", default=20, show_default=True, help="Candidate budget at evaluation.")
@click.option("--eval-n", type=int, help="Cap evaluation molecules. Default: the whole split.")
@click.option(
    "--strategy", default="sample", type=click.Choice(["sample", "beam"]), show_default=True
)
@click.option("--temperature", default=1.0, show_default=True)
@click.option("--top-p", default=1.0, show_default=True)
@click.option(
    "--budget",
    default="molecules",
    type=click.Choice(["molecules", "strings"]),
    show_default=True,
    help="What one of the k slots is spent on. Rows under different budgets are not comparable.",
)
@click.option(
    "--oversample",
    default=2.0,
    show_default=True,
    help="Draw k*oversample strings so k distinct molecules are available.",
)
@click.option(
    "--baseline/--no-baseline", default=True, show_default=True, help="Also score retrieval."
)
@click.option("--skip-train", is_flag=True, help="Evaluate an existing checkpoint instead.")
@click.option("--checkpoint", type=click.Path(path_type=Path), help="With --skip-train.")
@click.option("--note", default="", help="Free-text label for the leaderboard row.")
def main(
    config,
    split,
    shard_dir,
    out_dir,
    epochs,
    eval_k,
    eval_n,
    strategy,
    temperature,
    top_p,
    budget,
    oversample,
    baseline,
    skip_train,
    checkpoint,
    note,
):
    """Train (or load) a model, evaluate it, and record the result."""
    fp_cfg, model_cfg, train_cfg, raw = load_configs(config)
    shard_dir = Path(shard_dir or raw.get("shard_dir", "data/shards/10k"))
    out_dir = Path(out_dir or raw.get("out_dir", "checkpoints/run"))
    if epochs:
        train_cfg = replace(train_cfg, epochs=epochs)
    scaffold = bool(raw.get("scaffold_split", False))

    if split == "test":
        click.secho(
            "evaluating on TEST. Do this deliberately and rarely -- optimising "
            "against it destroys its value as a held-out measurement.",
            fg="yellow",
        )

    started = time.perf_counter()
    train_record = None
    if skip_train:
        ckpt_path = Path(checkpoint or out_dir / "best.pt")
        click.echo(f"loading {ckpt_path}")
        model, _ = Morg2SmilesModel.load(ckpt_path, device=select_device(train_cfg.device))
    else:
        train_record = train(
            shard_dir,
            fp_cfg=fp_cfg,
            model_cfg=model_cfg,
            train_cfg=train_cfg,
            out_dir=out_dir,
            scaffold=scaffold,
        )
        model, _ = Morg2SmilesModel.load(
            out_dir / "best.pt", device=select_device(train_cfg.device)
        )

    # The model's own stamped fingerprint config wins over the YAML, so a
    # checkpoint can never be evaluated under settings it was not trained for.
    fp_cfg = model.fp_cfg

    eval_smiles = load_split(shard_dir, split, scaffold=scaffold)
    mask = fp_unseen_mask(shard_dir, fp_cfg, split=split, scaffold=scaffold)
    if eval_n:
        eval_smiles, mask = eval_smiles[:eval_n], mask[:eval_n]
    click.echo(
        f"evaluating on {len(eval_smiles):,} {split} molecules "
        f"({sum(mask):,} with unseen fingerprints)"
    )

    model_report = evaluate_model(
        model,
        eval_smiles,
        k=eval_k,
        fp_unseen=mask,
        strategy=strategy,
        temperature=temperature,
        top_p=top_p,
        budget=budget,
        oversample=oversample,
    )
    click.echo("")
    click.secho("model", bold=True)
    click.echo(format_report(model_report))

    baseline_report = None
    if baseline:
        train_smiles = load_split(shard_dir, "train", scaffold=scaffold)
        baseline_report = evaluate_baseline(
            train_smiles, eval_smiles, fp_cfg, k=eval_k, fp_unseen=mask
        )
        click.echo("")
        click.secho("nearest-neighbour baseline", bold=True)
        click.echo(format_report(baseline_report))

        delta = model_report["primary_metric"] - baseline_report["primary_metric"]
        colour = "green" if delta > 0 else "red"
        click.echo("")
        click.secho(
            f"model - baseline on {model_report['primary_metric_name']}: {delta:+.4f}",
            fg=colour,
            bold=True,
        )
        if delta <= 0:
            click.secho(
                "the model does not beat retrieval on unseen fingerprints, so it has "
                "not learned to reconstruct.",
                fg="red",
            )

    record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "config_file": str(config),
        "note": note,
        "git_commit": git_commit(),
        "platform": f"{platform.system()} {platform.machine()}",
        "torch": torch.__version__,
        "shard_dir": str(shard_dir),
        "split": split,
        "scaffold_split": scaffold,
        "fp_config": fp_cfg.to_dict(),
        "fingerprint_id": fp_cfg.fingerprint_id,
        "model_config": model.cfg.to_dict(),
        "train_config": train_cfg.to_dict(),
        "n_parameters": model.n_parameters,
        "checkpoint": str(out_dir / "best.pt"),
        "generation": {
            "k": eval_k,
            "strategy": strategy,
            "temperature": temperature,
            "top_p": top_p,
            "budget": budget,
            "oversample": oversample,
        },
        "primary_metric_name": model_report["primary_metric_name"],
        "primary_metric": model_report["primary_metric"],
        "baseline_primary_metric": baseline_report["primary_metric"] if baseline_report else None,
        "model_report": model_report,
        "baseline_report": baseline_report,
        "best_valid_metric": train_record["best_valid_metric"] if train_record else None,
        "total_seconds": time.perf_counter() - started,
    }
    append_record(record)
    click.echo(f"\nappended to {LEADERBOARD}")


if __name__ == "__main__":
    main()
