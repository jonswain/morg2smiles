"""Training loop.

Validation is oracle-based, not loss-based: every ``eval_every`` epochs the
model generates candidates for a validation subsample and is scored on
recovery@k. Token-level cross-entropy is a poor proxy here -- it rewards
reproducing the canonical string, while the task rewards producing *any*
molecule with the right fingerprint -- so checkpoint selection uses the real
metric.

The validation split is the only split used for model selection. The test split
is left alone, so that it still means something after the iteration loop has
made hundreds of choices against validation.
"""

from __future__ import annotations

import json
import math
import random
import time
from dataclasses import asdict, dataclass, replace
from functools import partial
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader
from tqdm import tqdm

from .data.dataset import FingerprintDataset, collate, fp_unseen_mask, load_split
from .evaluation import evaluate_model
from .fingerprints import FPConfig
from .metrics import format_report
from .model import ModelConfig, build_model, select_device
from .tokenizer import SmilesTokenizer

__all__ = ["TrainConfig", "train", "set_seed"]


@dataclass(frozen=True)
class TrainConfig:
    """Optimisation and schedule settings."""

    epochs: int = 20
    batch_size: int = 128
    lr: float = 3e-4
    weight_decay: float = 0.01
    warmup_steps: int = 500
    min_lr_factor: float = 0.05
    grad_clip: float = 1.0
    label_smoothing: float = 0.0
    #: Emit a fresh random SMILES traversal per molecule per epoch. Usually the
    #: largest single win on this task; see :mod:`morg2smiles.data.dataset`.
    randomize_smiles: bool = True
    num_workers: int = 0
    device: str = "auto"
    #: ``"fp32"`` or ``"bf16"``. MPS autocast support is uneven across torch
    #: versions, so fp32 is the default and bf16 is something to measure.
    precision: str = "fp32"
    seed: int = 0
    #: Epochs between oracle-based validation passes.
    eval_every: int = 1
    #: Optimiser steps between validation passes, if set. Takes precedence over
    #: ``eval_every``, and exists because epochs are the wrong unit at scale: on
    #: a 1M shard one epoch is ~7,000 steps and several hours, so epoch-based
    #: evaluation yields a two-point curve and almost no basis for choosing a
    #: checkpoint. Steps decouple how often we look from how big the data is.
    eval_every_steps: int | None = None
    #: Validation molecules to sample. Generation is far slower than training,
    #: so a subsample keeps the epoch loop responsive; the full split is used
    #: for the final report.
    eval_n: int = 500
    eval_k: int = 20
    #: Molecules for the (cheap) teacher-forced validation loss. Unlike the
    #: oracle pass this is one forward pass, so it can afford more molecules and
    #: run at every evaluation. It is a diagnostic, never the selection
    #: criterion: loss and recovery are only loosely coupled on this task, which
    #: is the specific mistake the first attempt at this project made.
    valid_loss_n: int = 2000
    #: Stop when validation recovery has not improved for this many evaluations.
    patience: int = 5
    #: Hard wall-clock budget in hours, checked at each evaluation. Exists for
    #: unattended runs: step-time estimates on this hardware have been wrong by
    #: a factor of two in both directions, and a run that overshoots silently
    #: eats the analysis that was supposed to follow it. Stopping at a budget
    #: costs the tail of one curve; overrunning costs the whole night.
    max_hours: float | None = None
    #: Stop after this many optimiser steps, whatever the epoch schedule says.
    #: Data-scaling comparisons need runs matched on *compute*, not on epochs:
    #: one epoch of the 1M shard is 11 epochs of the 100k shard, so comparing
    #: "3 epochs" against "12 epochs" varies data and compute together and
    #: cannot say which one moved the result.
    max_steps: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> TrainConfig:
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in known})


def set_seed(seed: int) -> None:
    """Seed Python, NumPy and torch together."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _lr_at(step: int, total_steps: int, cfg: TrainConfig) -> float:
    """Linear warmup then cosine decay, as a multiplier on the base lr."""
    if step < cfg.warmup_steps:
        return (step + 1) / max(cfg.warmup_steps, 1)
    progress = (step - cfg.warmup_steps) / max(total_steps - cfg.warmup_steps, 1)
    progress = min(max(progress, 0.0), 1.0)
    cosine = 0.5 * (1 + math.cos(math.pi * progress))
    return cfg.min_lr_factor + (1 - cfg.min_lr_factor) * cosine


def train(
    shard_dir: str | Path,
    *,
    fp_cfg: FPConfig = FPConfig(),
    model_cfg: ModelConfig = ModelConfig(),
    train_cfg: TrainConfig = TrainConfig(),
    out_dir: str | Path = "checkpoints/run",
    scaffold: bool = False,
    show_progress: bool = True,
) -> dict:
    """Train a model and return its training record.

    Args:
        shard_dir: Prepared shard directory.
        fp_cfg: Fingerprint specification. Stamped into the checkpoint so the
            model can never be used with a different one.
        model_cfg: Architecture. ``vocab_size`` and ``fp_vocab_size`` are
            overwritten from the tokenizer and fingerprint config.
        train_cfg: Optimisation settings.
        out_dir: Where checkpoints, the tokenizer and the history land.
        scaffold: Train and validate on the scaffold split instead of random.

    Returns:
        A record with the config, the best validation report, and the per-epoch
        history.
    """
    shard_dir, out_dir = Path(shard_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    set_seed(train_cfg.seed)
    device = select_device(train_cfg.device)

    train_smiles = load_split(shard_dir, "train", scaffold=scaffold)
    valid_smiles = load_split(shard_dir, "valid", scaffold=scaffold)
    print(f"train {len(train_smiles):,}  valid {len(valid_smiles):,}  device {device}")
    print(f"fingerprint: {fp_cfg.describe()} [{fp_cfg.fingerprint_id}]")

    tokenizer = SmilesTokenizer.build(train_smiles)
    tokenizer.save(out_dir / "tokenizer.json")
    print(f"vocabulary: {len(tokenizer)} tokens")

    model = build_model(model_cfg, fp_cfg, tokenizer).to(device)
    print(f"parameters: {model.n_parameters:,}")

    dataset = FingerprintDataset(
        train_smiles,
        fp_cfg,
        tokenizer,
        max_tokens=model.cfg.max_tokens,
        randomize=train_cfg.randomize_smiles,
        seed=train_cfg.seed,
    )
    loader = DataLoader(
        dataset,
        batch_size=train_cfg.batch_size,
        shuffle=True,
        # partial, not a lambda: with num_workers > 0 macOS spawns worker
        # processes and a lambda collate_fn cannot be pickled.
        collate_fn=partial(collate, pad_id=tokenizer.pad_id),
        num_workers=train_cfg.num_workers,
        persistent_workers=train_cfg.num_workers > 0,
        prefetch_factor=4 if train_cfg.num_workers > 0 else None,
        drop_last=False,
    )

    # Weight decay on matrices only. Decaying LayerNorm gains and biases is
    # the usual accidental regulariser and costs a little accuracy for nothing.
    decay, no_decay = [], []
    for _name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        (no_decay if param.ndim < 2 else decay).append(param)
    optimizer = torch.optim.AdamW(
        [
            {"params": decay, "weight_decay": train_cfg.weight_decay},
            {"params": no_decay, "weight_decay": 0.0},
        ],
        lr=train_cfg.lr,
        betas=(0.9, 0.98),
    )
    criterion = nn.CrossEntropyLoss(
        ignore_index=tokenizer.pad_id, label_smoothing=train_cfg.label_smoothing
    )

    # A fixed validation subsample, so epoch-to-epoch comparisons are not noise
    # from re-drawing the molecules.
    rng = random.Random(train_cfg.seed)
    eval_idx = sorted(
        rng.sample(range(len(valid_smiles)), min(train_cfg.eval_n, len(valid_smiles)))
    )
    eval_smiles = [valid_smiles[i] for i in eval_idx]
    full_mask = fp_unseen_mask(
        shard_dir, fp_cfg, split="valid", scaffold=scaffold, show_progress=show_progress
    )
    eval_mask = [full_mask[i] for i in eval_idx]
    print(
        f"validation subsample: {len(eval_smiles)} molecules, "
        f"{sum(eval_mask)} with unseen fingerprints"
    )

    # A second, larger subsample for the teacher-forced validation loss. Cheap
    # enough to take more molecules than the oracle pass can afford.
    loss_idx = sorted(
        rng.sample(range(len(valid_smiles)), min(train_cfg.valid_loss_n, len(valid_smiles)))
    )
    loss_dataset = FingerprintDataset(
        [valid_smiles[i] for i in loss_idx],
        fp_cfg,
        tokenizer,
        max_tokens=model.cfg.max_tokens,
        randomize=False,  # a moving target would make the curve unreadable
        seed=train_cfg.seed,
    )
    loss_loader = DataLoader(
        loss_dataset,
        batch_size=train_cfg.batch_size,
        shuffle=False,
        collate_fn=partial(collate, pad_id=tokenizer.pad_id),
    )

    total_steps = max(train_cfg.epochs * len(loader), 1)
    if train_cfg.max_steps:
        # The cosine schedule must finish decaying by the step the run actually
        # stops on, or a step-capped run ends with its learning rate still high
        # and is penalised for a reason unrelated to what it is testing. This
        # matters for matched-compute comparisons, where the same step budget
        # is a different number of epochs on each shard.
        total_steps = min(total_steps, train_cfg.max_steps)
    autocast_dtype = torch.bfloat16 if train_cfg.precision == "bf16" else None

    def forward_loss(batch: dict) -> torch.Tensor:
        tokens = batch["tokens"].to(device)
        logits = model(
            batch["fp_indices"].to(device),
            batch["fp_counts"].to(device),
            batch["fp_mask"].to(device),
            tokens,
        )
        return criterion(logits.reshape(-1, logits.size(-1)), tokens[:, 1:].reshape(-1))

    @torch.no_grad()
    def validation_loss() -> float:
        was_training = model.training
        model.eval()
        total, n = 0.0, 0
        for batch in loss_loader:
            if autocast_dtype is not None:
                with torch.autocast(device_type=device.type, dtype=autocast_dtype):
                    total += forward_loss(batch).item()
            else:
                total += forward_loss(batch).item()
            n += 1
        if was_training:
            model.train()
        return total / max(n, 1)

    history: list[dict] = []
    best_metric, best_label, since_improved = -1.0, "", 0
    best_vloss = float("inf")
    best_index = -1
    step = 0
    # Wall clock, deliberately, not ``time.perf_counter()``. On macOS
    # perf_counter does not advance while the process is suspended, and an
    # unattended overnight run does get suspended: the first 1M run logged
    # 6.90 h of perf_counter time across 10.78 h of real time, so an 8.5 h
    # cap never fired and the stage ate the slot reserved for analysis.
    # A deadline is in wall time, so the budget guarding it must be too.
    started = time.time()

    def evaluate_now(epoch: int, train_loss: float, *, reason: str) -> None:
        """Run both validation passes, log, and keep the best checkpoint.

        Shared by the step-based and epoch-based triggers so the two cannot
        drift apart in what they measure or what they save.
        """
        nonlocal best_metric, best_label, best_index, best_vloss, since_improved

        report = evaluate_model(
            model,
            eval_smiles,
            k=train_cfg.eval_k,
            fp_unseen=eval_mask,
            show_progress=show_progress,
        )
        vloss = validation_loss()
        label = f"epoch {epoch + 1} step {step}"
        record = {
            "epoch": epoch + 1,
            "step": step,
            "trigger": reason,
            "train_loss": train_loss,
            "valid_loss": vloss,
            "elapsed_seconds": time.time() - started,
            "valid": report,
        }
        history.append(record)

        metric = report["primary_metric"]
        print(
            f"{label}: train {train_loss:.4f}  valid {vloss:.4f}  "
            f"{report['primary_metric_name']} {metric:.4f}  "
            f"recovery@1(all) {report['slices']['all']['recovery_at_k']['1']:.4f}"
        )

        # Recovery decides; validation loss only breaks ties. Early in a run
        # every evaluation recovers nothing, and without a tiebreak the first
        # one wins and ``best.pt`` holds the worst model in the run. Loss must
        # never outrank recovery, though -- selecting on loss is exactly the
        # mistake this project exists to avoid.
        improved = metric > best_metric or (metric == best_metric and vloss < best_vloss)
        if improved:
            best_metric, best_label, since_improved = metric, label, 0
            best_vloss = vloss
            best_index = len(history) - 1
            model.save(
                out_dir / "best.pt",
                epoch=epoch + 1,
                step=step,
                valid_report=report,
                valid_loss=vloss,
                train_config=train_cfg.to_dict(),
            )
        else:
            since_improved += 1

        model.save(
            out_dir / "last.pt", epoch=epoch + 1, step=step, train_config=train_cfg.to_dict()
        )
        (out_dir / "history.json").write_text(json.dumps(history, indent=2))

    def _should_stop() -> bool:
        if train_cfg.patience and since_improved >= train_cfg.patience:
            return True
        if train_cfg.max_steps and step >= train_cfg.max_steps:
            return True
        if train_cfg.max_hours and (time.time() - started) / 3600 >= train_cfg.max_hours:
            return True
        return False

    def _stop_reason() -> str:
        if train_cfg.patience and since_improved >= train_cfg.patience:
            return f"no improvement for {since_improved} evaluations"
        if train_cfg.max_steps and step >= train_cfg.max_steps:
            return f"step budget of {train_cfg.max_steps} reached"
        return f"wall-clock budget of {train_cfg.max_hours} h reached"

    for epoch in range(train_cfg.epochs):
        model.train()
        dataset.set_epoch(epoch)
        running, n_batches = 0.0, 0
        bar = tqdm(loader, desc=f"epoch {epoch + 1}/{train_cfg.epochs}", disable=not show_progress)
        for batch in bar:
            for group in optimizer.param_groups:
                group["lr"] = train_cfg.lr * _lr_at(step, total_steps, train_cfg)

            if autocast_dtype is not None:
                with torch.autocast(device_type=device.type, dtype=autocast_dtype):
                    loss = forward_loss(batch)
            else:
                loss = forward_loss(batch)

            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            if train_cfg.grad_clip:
                nn.utils.clip_grad_norm_(model.parameters(), train_cfg.grad_clip)
            optimizer.step()

            running += loss.item()
            n_batches += 1
            step += 1
            bar.set_postfix(
                loss=f"{running / n_batches:.4f}", lr=f"{optimizer.param_groups[0]['lr']:.2e}"
            )

            if train_cfg.eval_every_steps and step % train_cfg.eval_every_steps == 0:
                evaluate_now(epoch, running / n_batches, reason="step")
                if _should_stop():
                    break
            elif train_cfg.max_steps and step >= train_cfg.max_steps:
                # A matched-compute run must stop on the exact step, so this
                # one condition is checked every step rather than only at an
                # evaluation. The final measurement is taken below.
                evaluate_now(epoch, running / n_batches, reason="step-budget")
                break

        stop_early = _should_stop()

        # With step-based evaluation the epoch boundary is not special, so only
        # evaluate here if steps are not already driving it -- or if this is the
        # very last batch of training, which must not go unmeasured.
        is_last = epoch == train_cfg.epochs - 1
        if not stop_early and (
            (
                not train_cfg.eval_every_steps
                and ((epoch + 1) % train_cfg.eval_every == 0 or is_last)
            )
            or (train_cfg.eval_every_steps and is_last and history and history[-1]["step"] != step)
        ):
            evaluate_now(epoch, running / max(n_batches, 1), reason="epoch")
            stop_early = _should_stop()

        if stop_early:
            print(f"stopping early: {_stop_reason()}")
            break

    record = {
        "shard_dir": str(shard_dir),
        "scaffold_split": scaffold,
        "fp_config": fp_cfg.to_dict(),
        "fingerprint_id": fp_cfg.fingerprint_id,
        "model_config": model.cfg.to_dict(),
        "train_config": train_cfg.to_dict(),
        "n_parameters": model.n_parameters,
        "n_train": len(train_smiles),
        "best_checkpoint": best_label,
        "best_epoch": history[best_index]["epoch"] if best_index >= 0 else -1,
        "best_step": history[best_index]["step"] if best_index >= 0 else -1,
        "best_valid_metric": best_metric,
        "stopped_because": _stop_reason() if _should_stop() else "completed schedule",
        "total_seconds": time.time() - started,
        "history": history,
    }
    (out_dir / "record.json").write_text(json.dumps(record, indent=2))

    if best_index >= 0:
        best_report = history[best_index].get("valid") or {}
        if best_report:
            print()
            print(f"best checkpoint: {best_label}")
            print(format_report(best_report))
    return record


def load_configs(path: str | Path) -> tuple[FPConfig, ModelConfig, TrainConfig, dict]:
    """Read a YAML experiment config into the three config objects.

    Returns:
        ``(fp_cfg, model_cfg, train_cfg, raw)`` where ``raw`` keeps the whole
        parsed document, including the keys the experiment runner needs.
    """
    import yaml

    raw = yaml.safe_load(Path(path).read_text()) or {}
    fp_cfg = FPConfig(**raw.get("fingerprint", {}))
    model_cfg = ModelConfig.from_dict(raw.get("model", {}))
    train_cfg = TrainConfig.from_dict(raw.get("train", {}))
    return fp_cfg, model_cfg, train_cfg, raw


def main() -> None:
    """``python -m morg2smiles.train --config configs/tiny.yaml``"""
    import click

    @click.command()
    @click.option("--config", required=True, type=click.Path(exists=True, path_type=Path))
    @click.option("--shard-dir", type=click.Path(path_type=Path), help="Overrides the config.")
    @click.option("--out-dir", type=click.Path(path_type=Path), help="Overrides the config.")
    @click.option("--epochs", type=int, help="Overrides the config.")
    def cli(config, shard_dir, out_dir, epochs):
        fp_cfg, model_cfg, train_cfg, raw = load_configs(config)
        if epochs:
            train_cfg = replace(train_cfg, epochs=epochs)
        train(
            shard_dir or raw.get("shard_dir", "data/shards/10k"),
            fp_cfg=fp_cfg,
            model_cfg=model_cfg,
            train_cfg=train_cfg,
            out_dir=out_dir or raw.get("out_dir", "checkpoints/run"),
            scaffold=raw.get("scaffold_split", False),
        )

    cli()


if __name__ == "__main__":
    main()
