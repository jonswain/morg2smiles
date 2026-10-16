"""Can the decoder know how big the molecule is before it generates it?

The temperature gain rises monotonically with molecule size -- under half a
point below 24 heavy atoms, nearly ten points above 50 -- so the best setting
is probably size-dependent. A size-dependent setting is only usable if size can
be read off the *input*, because at generation time the molecule is exactly
what is unknown.

A Morgan fingerprint's set-bit count is the obvious estimator: more atoms means
more distinct substructure environments. Folding caps it -- 2,048 bits and
collisions -- so the relationship must flatten somewhere, and where it flattens
decides whether a bit-count rule can separate the bands that matter.

This script measures the relationship on the clean pool and scores every bit
threshold as a classifier for "at least ``--atoms`` heavy atoms", which is the
form a policy would take: one threshold, no molecule, no oracle.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean, stdev

import click
from rdkit import Chem, RDLogger

from morg2smiles.data.dataset import load_split
from morg2smiles.fingerprints import FPConfig, compute

RDLogger.DisableLog("rdApp.*")


def pearson(xs: list[float], ys: list[float]) -> float:
    mx, my = mean(xs), mean(ys)
    sx, sy = stdev(xs), stdev(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / (len(xs) - 1)
    return cov / (sx * sy)


@click.command()
@click.option("--pool-shard", default="data/shards/1m", show_default=True)
@click.option("--n", "n_molecules", default=5000, show_default=True)
@click.option("--atoms", default=35, show_default=True, help="The size class to predict.")
@click.option("--seed", default=0, show_default=True)
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    default=Path("results/overnight5/size_from_fingerprint.json"),
)
def main(pool_shard: str, n_molecules: int, atoms: int, seed: int, out: Path) -> None:
    import random

    fp_cfg = FPConfig()
    pool = load_split(pool_shard, "valid")
    rng = random.Random(seed)
    smiles = [pool[i] for i in sorted(rng.sample(range(len(pool)), min(n_molecules, len(pool))))]

    sizes, bits = [], []
    for s in smiles:
        mol = Chem.MolFromSmiles(s)
        if mol is None:
            continue
        sizes.append(mol.GetNumHeavyAtoms())
        bits.append(len(compute(s, fp_cfg)))

    r = pearson([float(b) for b in bits], [float(s) for s in sizes])
    click.echo(f"{len(sizes):,} molecules from {pool_shard} valid")
    click.echo(f"set bits vs heavy atoms: r = {r:.4f}")

    # Mean bits per band, to see where folding flattens the relationship.
    bands = [(0, 24), (25, 29), (30, 34), (35, 39), (40, 49), (50, 10**9)]
    per_band = {}
    click.echo(f"\n{'band':>8}{'n':>7}{'mean bits':>12}{'sd':>8}")
    for lo, hi in bands:
        chosen = [b for b, s in zip(bits, sizes, strict=True) if lo <= s <= hi]
        label = f"{lo}-{hi}" if hi < 10**9 else f"{lo}+"
        if not chosen:
            continue
        per_band[label] = {
            "n": len(chosen),
            "mean_bits": mean(chosen),
            "sd_bits": stdev(chosen) if len(chosen) > 1 else 0.0,
        }
        click.echo(
            f"{label:>8}{len(chosen):>7}{mean(chosen):>12.1f}{per_band[label]['sd_bits']:>8.1f}"
        )

    # Every threshold, scored as the policy it would be.
    positives = sum(1 for s in sizes if s >= atoms)
    best = None
    rows = []
    for threshold in range(min(bits), max(bits) + 1):
        tp = sum(1 for b, s in zip(bits, sizes, strict=True) if b >= threshold and s >= atoms)
        fp_ = sum(1 for b, s in zip(bits, sizes, strict=True) if b >= threshold and s < atoms)
        fn = positives - tp
        precision = tp / (tp + fp_) if tp + fp_ else 0.0
        recall = tp / positives if positives else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        accuracy = (len(sizes) - fp_ - fn) / len(sizes)
        row = {
            "bits": threshold,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "accuracy": accuracy,
        }
        rows.append(row)
        if best is None or f1 > best["f1"]:
            best = row

    click.echo(
        f"\nbest single bit-count threshold for >={atoms} heavy atoms: {best['bits']} set bits"
    )
    click.echo(
        f"  precision {best['precision']:.3f}  recall {best['recall']:.3f}  "
        f"F1 {best['f1']:.3f}  accuracy {best['accuracy']:.3f}  "
        f"(base rate {positives / len(sizes):.3f})"
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "pool_shard": pool_shard,
                "n_molecules": len(sizes),
                "atoms": atoms,
                "pearson_r": r,
                "bits_by_band": per_band,
                "best_threshold": best,
                "base_rate": positives / len(sizes),
                "thresholds": rows,
            },
            indent=2,
        )
    )
    click.echo(f"wrote {out}")


if __name__ == "__main__":
    main()
