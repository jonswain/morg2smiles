#!/usr/bin/env python
"""How much of the molecule does a Morgan fingerprint actually determine?

Run this *before* training anything. It measures the ceiling the model is
working against, so later numbers can be read against something.

Two different ceilings matter, and conflating them is the easiest way to
misread a result:

**structure_accuracy is capped by collisions.** Where several molecules in the
corpus share a fingerprint, no model can reliably pick the one the test set
happened to draw. The fraction of molecules with a corpus-unique fingerprint is
an upper bound on recovering the *original* molecule.

**recovery is not capped at all.** Any molecule with the right fingerprint is a
correct answer, so collisions make recovery *easier*, not harder -- a
fingerprint with many preimages has many ways to be right.

The report also measures how much information folding destroys, by comparing
each folded mode against the unfolded identifier set for the same molecules.

Usage:
    python scripts/analyse_recoverability.py --subset 10k
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import mean, median

import click
from tqdm import tqdm

from morg2smiles.data.dataset import load_split
from morg2smiles.fingerprints import FPConfig, compute

MODES: dict[str, FPConfig] = {
    "folded_binary_2048": FPConfig(n_bits=2048, counts=False, folded=True),
    "folded_count_2048": FPConfig(n_bits=2048, counts=True, folded=True),
    "folded_binary_4096": FPConfig(n_bits=4096, counts=False, folded=True),
    "unfolded_binary": FPConfig(counts=False, folded=False),
    "unfolded_count": FPConfig(counts=True, folded=False),
}


def _key(fp: dict[int, int]) -> tuple:
    return tuple(sorted(fp.items()))


def analyse_mode(molecules: list[str], cfg: FPConfig, *, show_progress: bool = True) -> dict:
    """Collision and density statistics for one fingerprint mode."""
    groups: dict[tuple, list[str]] = {}
    n_bits_set: list[int] = []
    total_counts: list[int] = []

    iterator = tqdm(molecules, desc=cfg.describe(), unit=" mol", disable=not show_progress)
    for smiles in iterator:
        fp = compute(smiles, cfg)
        groups.setdefault(_key(fp), []).append(smiles)
        n_bits_set.append(len(fp))
        total_counts.append(sum(fp.values()))

    sizes = [len(members) for members in groups.values()]
    size_histogram = Counter(sizes)
    n_unique = size_histogram.get(1, 0)
    n_molecules = len(molecules)

    return {
        "fp_config": cfg.to_dict(),
        "fingerprint_id": cfg.fingerprint_id,
        "description": cfg.describe(),
        "n_molecules": n_molecules,
        "n_distinct_fingerprints": len(groups),
        # The headline ceiling: fraction of molecules that are the sole
        # preimage of their fingerprint within this corpus.
        "frac_molecules_uniquely_determined": n_unique / n_molecules if n_molecules else 0.0,
        "structure_accuracy_ceiling": n_unique / n_molecules if n_molecules else 0.0,
        "max_molecules_per_fingerprint": max(sizes, default=0),
        "mean_molecules_per_fingerprint": mean(sizes) if sizes else 0.0,
        "collision_group_size_histogram": dict(sorted(size_histogram.items())),
        "bits_set": {
            "mean": mean(n_bits_set) if n_bits_set else 0.0,
            "median": median(n_bits_set) if n_bits_set else 0.0,
            "min": min(n_bits_set, default=0),
            "max": max(n_bits_set, default=0),
            # Density matters for the set encoder: this is its sequence length.
            "mean_density": (mean(n_bits_set) / cfg.n_bits)
            if (cfg.folded and n_bits_set)
            else None,
        },
        "total_count_mass": {"mean": mean(total_counts) if total_counts else 0.0},
    }


def analyse_folding_loss(molecules: list[str], *, show_progress: bool = True) -> dict:
    """How many distinct environments each folded mode loses to collisions."""
    unfolded = FPConfig(folded=False)
    results = {}
    for name in ("folded_binary_2048", "folded_binary_4096"):
        cfg = MODES[name]
        kept, true = [], []
        iterator = tqdm(
            molecules, desc=f"folding loss {cfg.n_bits}", unit=" mol", disable=not show_progress
        )
        for smiles in iterator:
            n_true = len(compute(smiles, unfolded))
            n_kept = len(compute(smiles, cfg))
            true.append(n_true)
            kept.append(n_kept)
        lost = [t - k for t, k in zip(true, kept, strict=True)]
        results[name] = {
            "mean_true_environments": mean(true),
            "mean_distinct_bits": mean(kept),
            "mean_environments_lost": mean(lost),
            "frac_environments_lost": sum(lost) / sum(true) if sum(true) else 0.0,
            "frac_molecules_with_any_collision": sum(1 for x in lost if x > 0) / len(lost),
        }
    return results


def format_markdown(report: dict) -> str:
    """Render the report as a short markdown document."""
    lines = [
        "# Morgan fingerprint recoverability",
        "",
        f"Corpus: `{report['shard_dir']}`, {report['n_molecules']:,} molecules "
        f"({report['splits_used']}).",
        "",
        "## Collisions by fingerprint mode",
        "",
        "`unique` is the fraction of molecules that are the only molecule in this corpus with "
        "their fingerprint. It bounds **structure_accuracy** (recovering the original molecule) "
        "but *not* **recovery** (producing any molecule with the right fingerprint), which "
        "collisions make easier rather than harder.",
        "",
        "| mode | distinct fps | unique | max preimages | mean bits set | density |",
        "|---|---|---|---|---|---|",
    ]
    for name, m in report["modes"].items():
        density = m["bits_set"]["mean_density"]
        density_cell = f"{density:.3f}" if density is not None else "n/a"
        lines.append(
            f"| `{name}` | {m['n_distinct_fingerprints']:,} "
            f"| {m['frac_molecules_uniquely_determined']:.4f} "
            f"| {m['max_molecules_per_fingerprint']} "
            f"| {m['bits_set']['mean']:.1f} "
            f"| {density_cell} |"
        )

    lines += [
        "",
        "## Information lost to folding",
        "",
        "| mode | true environments | distinct bits | lost | molecules affected |",
        "|---|---|---|---|---|",
    ]
    for name, m in report["folding_loss"].items():
        lines.append(
            f"| `{name}` | {m['mean_true_environments']:.1f} | {m['mean_distinct_bits']:.1f} "
            f"| {m['frac_environments_lost']:.3%} "
            f"| {m['frac_molecules_with_any_collision']:.1%} |"
        )

    binary = report["modes"].get("folded_binary_2048", {})
    count = report["modes"].get("folded_count_2048", {})
    if binary and count:
        delta = (
            count["frac_molecules_uniquely_determined"]
            - binary["frac_molecules_uniquely_determined"]
        )
        lines += [
            "",
            "## Do counts earn their keep?",
            "",
            f"Counts move the uniquely-determined fraction by **{delta:+.4f}** "
            f"({binary['frac_molecules_uniquely_determined']:.4f} binary -> "
            f"{count['frac_molecules_uniquely_determined']:.4f} count). "
            "A small gap means count fingerprints add little for this corpus and the "
            "extra input channel is not worth much.",
        ]
    return "\n".join(lines) + "\n"


@click.command()
@click.option("--subset", default="10k", show_default=True)
@click.option("--data-dir", default="data", type=click.Path(path_type=Path), show_default=True)
@click.option(
    "--splits",
    default="train,valid,test",
    show_default=True,
    help="Comma-separated splits to pool.",
)
@click.option("--limit", type=int, help="Cap molecules analysed, for a quick look.")
@click.option("--out-dir", default="reports", type=click.Path(path_type=Path), show_default=True)
def main(subset, data_dir, splits, limit, out_dir):
    """Measure what a Morgan fingerprint does and does not determine."""
    shard_dir = Path(data_dir) / "shards" / subset
    split_names = [s.strip() for s in splits.split(",") if s.strip()]

    molecules: list[str] = []
    for split in split_names:
        molecules.extend(load_split(shard_dir, split))
    if limit:
        molecules = molecules[:limit]
    click.echo(f"analysing {len(molecules):,} molecules from {shard_dir}")

    report = {
        "shard_dir": str(shard_dir),
        "splits_used": ", ".join(split_names),
        "n_molecules": len(molecules),
        "modes": {name: analyse_mode(molecules, cfg) for name, cfg in MODES.items()},
        "folding_loss": analyse_folding_loss(molecules),
    }

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"recoverability_{subset}.json"
    md_path = out_dir / f"recoverability_{subset}.md"
    json_path.write_text(json.dumps(report, indent=2))
    md_path.write_text(format_markdown(report))

    click.echo("")
    click.echo(format_markdown(report))
    click.echo(f"wrote {json_path} and {md_path}")


if __name__ == "__main__":
    main()
