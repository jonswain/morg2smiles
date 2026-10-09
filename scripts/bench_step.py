"""Measure sustained training step time, which decides what fits in a night.

Must be a real file rather than a heredoc: with ``num_workers > 0`` macOS spawns
worker processes that re-import ``__main__``, and a script fed on stdin has no
path to re-import.

Warmup steps are discarded. The first steps of a run are not representative --
allocator and kernel caches are cold -- and including them is how a plan ends up
built on a number that is twice as fast as reality.
"""

from __future__ import annotations

import time
from functools import partial

import click
import torch
from torch.utils.data import DataLoader

from morg2smiles.data.dataset import FingerprintDataset, collate, load_split
from morg2smiles.model import build_model, select_device
from morg2smiles.tokenizer import SmilesTokenizer
from morg2smiles.train import load_configs


@click.command()
@click.option("--config", required=True, multiple=True, help="Repeatable.")
@click.option("--workers", default="0,4", help="Comma-separated worker counts.")
@click.option("--warmup", default=10, show_default=True)
@click.option("--measure", default=40, show_default=True)
def main(config: tuple[str, ...], workers: str, warmup: int, measure: int) -> None:
    device = select_device()
    worker_counts = [int(w) for w in workers.split(",")]

    for cfg_path in config:
        fp_cfg, model_cfg, train_cfg, raw = load_configs(cfg_path)
        shard = raw.get("shard_dir", "data/shards/10k")
        train_smiles = load_split(shard, "train")
        tokenizer = SmilesTokenizer.build(train_smiles)
        steps_per_epoch = -(-len(train_smiles) // train_cfg.batch_size)
        total_steps = steps_per_epoch * train_cfg.epochs
        click.echo(f"\n{cfg_path}  shard={shard}  {len(train_smiles):,} molecules")

        for n_workers in worker_counts:
            model = build_model(model_cfg, fp_cfg, tokenizer).to(device)
            dataset = FingerprintDataset(
                train_smiles,
                fp_cfg,
                tokenizer,
                max_tokens=model.cfg.max_tokens,
                randomize=train_cfg.randomize_smiles,
                seed=0,
            )
            loader = DataLoader(
                dataset,
                batch_size=train_cfg.batch_size,
                shuffle=True,
                collate_fn=partial(collate, pad_id=tokenizer.pad_id),
                num_workers=n_workers,
                persistent_workers=n_workers > 0,
                prefetch_factor=4 if n_workers else None,
            )
            optimizer = torch.optim.AdamW(model.parameters(), lr=train_cfg.lr)
            criterion = torch.nn.CrossEntropyLoss(ignore_index=tokenizer.pad_id)

            started = None
            step = 0
            for batch in loader:
                tokens = batch["tokens"].to(device)
                logits = model(
                    batch["fp_indices"].to(device),
                    batch["fp_counts"].to(device),
                    batch["fp_mask"].to(device),
                    tokens,
                )
                loss = criterion(logits.reshape(-1, logits.size(-1)), tokens[:, 1:].reshape(-1))
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
                step += 1
                if step == warmup:
                    if device.type == "mps":
                        torch.mps.synchronize()
                    started = time.perf_counter()
                elif step == warmup + measure:
                    break

            if device.type == "mps":
                torch.mps.synchronize()
            per_step = (time.perf_counter() - started) / measure
            click.echo(
                f"  {model.n_parameters / 1e6:5.1f}M params  workers={n_workers}  "
                f"{per_step:.2f}s/step  -> {total_steps * per_step / 3600:5.1f}h "
                f"for {total_steps:,} steps ({train_cfg.epochs} epoch(s))"
            )
            del loader, dataset, model, optimizer


if __name__ == "__main__":
    main()
