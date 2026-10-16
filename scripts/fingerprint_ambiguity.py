"""Does the fingerprint still identify the molecule, once the molecule is big?

The dumps say that above 35 heavy atoms roughly one recovery in ten is a
*different* molecule with the same fingerprint, against one in a hundred below
30. That could be the model -- a decoder that cannot place substituents might
land on near-twins -- or it could be the representation, a folded 2048-bit
Morgan r=2 fingerprint running out of room to distinguish large molecules.

No model is needed to tell the two apart. Group real molecules by fingerprint
and count how many share theirs with at least one other. That rate is a
property of the fingerprint and the corpus alone, and if it rises with size
then part of the recovery cliff is a floor rather than a failure: the inversion
has genuinely more than one answer, and `recovery` -- which asks for a
fingerprint match, not the original molecule -- is the right metric for a task
whose answer is not unique, while `structure_accuracy` is asking for something
unachievable.

A collision found here is a lower bound: the model may generate molecules that
are nowhere in the corpus, so the ambiguity it faces is at least this large.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import click
from rdkit import Chem, RDLogger

from morg2smiles.data.dataset import _fp_key, load_split
from morg2smiles.fingerprints import FPConfig, compute

RDLogger.DisableLog("rdApp.*")

DEFAULT_BANDS = "0-24,25-29,30-34,35-39,40-49,50-59,60+,35+,all"


@click.command()
@click.option("--shard", default="data/shards/1m", show_default=True)
@click.option("--splits", default="train,valid", show_default=True)
@click.option("--n-bits", default=2048, show_default=True)
@click.option("--radius", default=2, show_default=True)
@click.option(
    "--counts/--binary",
    default=False,
    show_default=True,
    help=(
        "Counts carry how many times each environment occurs, not just whether "
        "it does. The README calls the difference worth +0.0002 uniquely "
        "determined molecules, measured on 11,669 of them, where binary "
        "ambiguity is itself 0.05% -- a corpus too small for either number to "
        "mean anything about the task."
    ),
)
@click.option(
    "--limit", type=int, default=None, help="Take only this many molecules, for a smoke test."
)
@click.option("--bands", default=DEFAULT_BANDS, show_default=True)
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    default=Path("results/overnight5/fingerprint_ambiguity.json"),
)
def main(shard, splits, n_bits, radius, counts, limit, bands, out) -> None:
    from scripts.band_analysis import parse_band

    cfg = FPConfig(radius=radius, n_bits=n_bits, counts=counts)
    smiles: list[str] = []
    for split in splits.split(","):
        smiles.extend(load_split(shard, split))
    if limit:
        smiles = smiles[:limit]
    click.echo(
        f"{len(smiles):,} molecules from {shard} [{splits}], morgan r={radius}/{n_bits}"
        f" {'counts' if counts else 'binary'}"
    )

    # Canonicalise first: the same molecule written two ways is not a collision.
    # Molecules are held as hashes of their canonical SMILES rather than the
    # strings, which keeps two million of them in a couple of gigabytes; a
    # 64-bit collision across that many is a one-in-ten-million event and would
    # merge two molecules into one group, understating ambiguity rather than
    # inventing it.
    by_key: dict[bytes, set[int]] = defaultdict(set)
    size_of: dict[int, int] = {}
    for i, smi in enumerate(smiles):
        if i and i % 200_000 == 0:
            click.echo(f"  {i:,} ... {len(size_of):,} molecules so far", err=True)
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue
        canonical = hash(Chem.MolToSmiles(mol))
        if canonical not in size_of:
            size_of[canonical] = mol.GetNumHeavyAtoms()
        by_key[_fp_key(compute(smi, cfg))].add(canonical)

    click.echo(f"{len(size_of):,} distinct molecules, {len(by_key):,} distinct fingerprints")

    # Per molecule: how many distinct molecules share its fingerprint.
    twins: dict[int, int] = {}
    for members in by_key.values():
        for m in members:
            twins[m] = len(members)

    specs = [parse_band(b) for b in bands.split(",")]
    header = f"{'band':>8}{'molecules':>12}{'ambiguous':>11}{'rate':>8}{'mean group':>12}{'max group':>11}"
    click.echo("\n" + header)
    click.echo("-" * len(header))
    table = {}
    for name, lo, hi in specs:
        members = [m for m, sz in size_of.items() if lo <= sz <= hi]
        if not members:
            continue
        groups = [twins[m] for m in members]
        ambiguous = sum(g > 1 for g in groups)
        click.echo(
            f"{name:>8}{len(members):>12,}{ambiguous:>11,}{ambiguous / len(members):>8.4f}"
            f"{sum(groups) / len(groups):>12.3f}{max(groups):>11,}"
        )
        table[name] = {
            "molecules": len(members),
            "ambiguous": ambiguous,
            "ambiguous_rate": ambiguous / len(members),
            "mean_group_size": sum(groups) / len(groups),
            "max_group_size": max(groups),
        }

    click.echo(
        "\nambiguous: molecules sharing their fingerprint with at least one other"
        "\n           molecule in this corpus -- a lower bound on the ambiguity"
        "\n           the model faces, which can also generate molecules not here."
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "shard": shard,
                "splits": splits,
                "fingerprint": {
                    "radius": radius,
                    "n_bits": n_bits,
                    "counts": counts,
                    "folded": True,
                },
                "n_input_smiles": len(smiles),
                "n_distinct_molecules": len(size_of),
                "n_distinct_fingerprints": len(by_key),
                "bands": table,
            },
            indent=2,
        )
    )
    click.echo(f"\nwrote {out}")


if __name__ == "__main__":
    main()
