"""The ``morg2smiles`` command line entry point.

A thin click group over the three things you actually do: build a dataset,
train a model, and ask a trained model to invert a fingerprint. Each
subcommand delegates to the module that owns the work, so there is no logic
here worth testing -- that lives in :mod:`morg2smiles.data.prepare`,
:mod:`morg2smiles.train` and :mod:`morg2smiles.generate`.
"""

from __future__ import annotations

from pathlib import Path

import click

from . import __version__


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="morg2smiles")
def main() -> None:
    """Recover SMILES strings from Morgan fingerprints."""


@main.command()
@click.option("--subset", default="10k", show_default=True, help="10k, 100k, 1m or full.")
@click.option("--data-dir", default="data", type=click.Path(path_type=Path), show_default=True)
@click.option("--source", type=click.Path(exists=True, path_type=Path), help="Local chemreps file.")
@click.option("--overwrite", is_flag=True)
def prepare(subset: str, data_dir: Path, source: Path | None, overwrite: bool) -> None:
    """Download and standardise a ChEMBL subset into train/valid/test shards."""
    from .data.prepare import prepare as _prepare

    _prepare(subset=subset, data_dir=data_dir, source=source, overwrite=overwrite)


@main.command()
@click.option("--config", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--shard-dir", type=click.Path(path_type=Path), help="Overrides the config.")
@click.option("--out-dir", type=click.Path(path_type=Path), help="Overrides the config.")
@click.option("--epochs", type=int, help="Overrides the config.")
def train(config: Path, shard_dir: Path | None, out_dir: Path | None, epochs: int | None) -> None:
    """Train a fingerprint-conditioned decoder from a YAML config."""
    from dataclasses import replace

    from .train import load_configs
    from .train import train as _train

    fp_cfg, model_cfg, train_cfg, raw = load_configs(config)
    if epochs:
        train_cfg = replace(train_cfg, epochs=epochs)
    _train(
        shard_dir or raw.get("shard_dir", "data/shards/10k"),
        fp_cfg=fp_cfg,
        model_cfg=model_cfg,
        train_cfg=train_cfg,
        out_dir=out_dir or raw.get("out_dir", "checkpoints/run"),
        scaffold=raw.get("scaffold_split", False),
    )


@main.command()
@click.argument("smiles")
@click.option(
    "--checkpoint",
    default="checkpoints/best.pt",
    type=click.Path(exists=True, path_type=Path),
    show_default=True,
)
@click.option("--k", default=20, show_default=True, help="Candidates to generate.")
@click.option("--temperature", default=1.0, show_default=True)
@click.option("--top-p", default=1.0, show_default=True)
@click.option(
    "--verified-only",
    is_flag=True,
    help="Only print candidates whose fingerprint matches exactly.",
)
def invert(
    smiles: str,
    checkpoint: Path,
    k: int,
    temperature: float,
    top_p: float,
    verified_only: bool,
) -> None:
    """Fingerprint SMILES, then try to recover it from that fingerprint alone.

    The round trip is the point: the model never sees the input string, only
    the bits. A line marked ``=`` is an exact fingerprint match.
    """
    from .fingerprints import compute
    from .generate import Morg2Smiles
    from .oracle import check

    model = Morg2Smiles.load(checkpoint)
    fp = compute(smiles, model.fp_config)
    if not fp:
        raise click.ClickException(f"could not fingerprint {smiles!r}")

    candidates = model.generate(
        fp, k=k, temperature=temperature, top_p=top_p, verified_only=verified_only
    )
    if not candidates:
        click.echo("no candidates")
        return

    for candidate in candidates:
        result = check(candidate, fp, model.fp_config, reference_smiles=smiles)
        mark = "=" if result.fp_match else f"{result.tanimoto:.2f}"
        click.echo(f"{mark:>5}  {candidate}")


if __name__ == "__main__":  # pragma: no cover
    main()
