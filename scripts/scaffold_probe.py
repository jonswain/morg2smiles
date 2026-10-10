"""Does the model generalise to chemotypes it has never seen?

``fp_unseen`` asks whether a *fingerprint* appeared in training. That is the
right guard against memorising a lookup table, but it is a low bar: because the
fingerprint is nearly injective, almost every held-out molecule qualifies, and a
model could still be working only within scaffolds it knows well.

This asks the harder question. Bemis-Murcko scaffolds are computed for the
training set and for the evaluation molecules, and recovery is reported on two
slices:

``scaffold_seen``
    The molecule's scaffold appears somewhere in training. A new molecule, but
    familiar structural territory.
``scaffold_novel``
    The scaffold appears nowhere in training. Genuinely new territory.

The gap between them is the interesting number, and it is the one that predicts
behaviour on chemistry a user actually brings.

Note on method: this deliberately does *not* use the shard's prebuilt scaffold
split. That split has its own train set, which is not the one this model was
trained on, so molecules in its test half may well have been trained on via the
random split -- the number would be contaminated and flattering. Slicing the
model's own held-out validation data by scaffold novelty asks the same question
honestly with the checkpoint we actually have.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import click
from rdkit import Chem, RDLogger
from rdkit.Chem.Scaffolds import MurckoScaffold
from tqdm import tqdm

from morg2smiles.data.dataset import _fp_key, load_split
from morg2smiles.evaluation import generate_outcomes
from morg2smiles.fingerprints import compute
from morg2smiles.metrics import evaluate, recovery_at_k, structure_accuracy_at_k
from morg2smiles.model import Morg2SmilesModel, select_device

RDLogger.DisableLog("rdApp.*")

RUNS = [
    ("small_100k", "checkpoints/small/best.pt", "data/shards/100k"),
    ("small_1m", "checkpoints/small_1m/best.pt", "data/shards/1m"),
    ("medium_1m", "checkpoints/medium_1m/best.pt", "data/shards/1m"),
    ("small_100k_long", "checkpoints/small_100k_long/best.pt", "data/shards/100k"),
    ("small_1m_matched", "checkpoints/small_1m_matched/best.pt", "data/shards/1m"),
    ("small_full", "checkpoints/small_full/best.pt", "data/shards/full"),
]


def scaffold_of(smiles: str) -> str | None:
    """Bemis-Murcko scaffold as canonical SMILES, or None if it has none.

    Acyclic molecules reduce to an empty scaffold. They are excluded rather than
    bundled together, since "has no ring system" is not a chemotype and lumping
    them in would put every alkane in one bucket.
    """
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        scaffold = MurckoScaffold.GetScaffoldForMol(mol)
        if scaffold is None or scaffold.GetNumAtoms() == 0:
            return None
        return Chem.MolToSmiles(scaffold)
    except Exception:
        return None


@click.command()
@click.option("--eval-n", default=1000, show_default=True)
@click.option("--seed", default=0, show_default=True)
@click.option("--eval-k", default=20, show_default=True)
@click.option("--out", type=click.Path(path_type=Path), default=Path("results/scaffold_probe.json"))
def main(eval_n: int, seed: int, eval_k: int, out: Path) -> None:
    runs = [(n, c, s) for n, c, s in RUNS if Path(c).exists()]
    if not runs:
        raise click.ClickException("no checkpoints found")

    device = select_device()
    results: dict = {"protocol": {"eval_n": eval_n, "seed": seed, "eval_k": eval_k}, "runs": {}}

    # Scaffolding and fingerprinting a 900k training set takes minutes, and runs
    # share shards, so both are memoised. Stage 4 runs against a deadline.
    scaffold_cache: dict[str, set[str]] = {}
    fp_key_cache: dict[tuple[str, str], set[bytes]] = {}

    for name, checkpoint, shard in runs:
        click.echo(f"\n=== {name} ({shard}) ===")
        model, _ = Morg2SmilesModel.load(checkpoint, device=device)
        fp_cfg = model.fp_cfg

        train_smiles = load_split(shard, "train")
        valid_smiles = load_split(shard, "valid")

        if shard not in scaffold_cache:
            click.echo(f"scaffolding {len(train_smiles):,} training molecules ...")
            scaffold_cache[shard] = {
                s for s in (scaffold_of(m) for m in tqdm(train_smiles, unit=" mol")) if s
            }
        train_scaffolds = scaffold_cache[shard]
        click.echo(f"{len(train_scaffolds):,} distinct training scaffolds")

        # Keep only validation molecules that have a scaffold at all, then take
        # a balanced-ish sample so the novel slice is not a handful of rows.
        rng = random.Random(seed)
        order = list(range(len(valid_smiles)))
        rng.shuffle(order)

        seen_pool: list[str] = []
        novel_pool: list[str] = []
        want = eval_n // 2
        for i in order:
            if len(seen_pool) >= want and len(novel_pool) >= want:
                break
            smiles = valid_smiles[i]
            scaffold = scaffold_of(smiles)
            if scaffold is None:
                continue
            if scaffold in train_scaffolds:
                if len(seen_pool) < want:
                    seen_pool.append(smiles)
            elif len(novel_pool) < want:
                novel_pool.append(smiles)

        click.echo(f"sampled {len(seen_pool):,} scaffold-seen, {len(novel_pool):,} scaffold-novel")
        if not novel_pool:
            click.echo("no novel-scaffold molecules found; skipping")
            continue

        cache_key = (shard, fp_cfg.fingerprint_id)
        if cache_key not in fp_key_cache:
            click.echo(f"indexing {len(train_smiles):,} training fingerprints ...")
            fp_key_cache[cache_key] = {_fp_key(compute(m, fp_cfg)) for m in train_smiles}
        train_keys = fp_key_cache[cache_key]

        payload: dict = {"checkpoint": checkpoint, "train_shard": shard, "slices": {}}
        for slice_name, molecules in (
            ("scaffold_seen", seen_pool),
            ("scaffold_novel", novel_pool),
        ):
            fp_unseen = [_fp_key(compute(m, fp_cfg)) not in train_keys for m in molecules]
            outcomes = generate_outcomes(
                model,
                molecules,
                k=eval_k,
                fp_unseen=fp_unseen,
                budget="molecules",
                seed=seed,
            )
            # Report over fingerprint-unseen queries only, so the two slices
            # differ in scaffold novelty and nothing else.
            unseen_only = [o for o in outcomes if o.fp_unseen]
            report = evaluate(unseen_only, ks=[1, 5, eval_k])
            payload["slices"][slice_name] = {
                "n_sampled": len(molecules),
                "n_fp_unseen": len(unseen_only),
                "recovery_at_k": {str(k): recovery_at_k(unseen_only, k) for k in (1, 5, eval_k)},
                "structure_accuracy_at_20": structure_accuracy_at_k(unseen_only, eval_k),
                "validity": report["slices"]["all"]["validity"],
                "mean_best_tanimoto": report["slices"]["all"]["mean_best_tanimoto"],
            }
            got = payload["slices"][slice_name]
            click.echo(
                f"  {slice_name:<15} n={got['n_fp_unseen']:<5} "
                f"rec@1={got['recovery_at_k']['1']:.4f} "
                f"rec@{eval_k}={got['recovery_at_k'][str(eval_k)]:.4f} "
                f"tanimoto={got['mean_best_tanimoto']:.3f}"
            )

        seen = payload["slices"].get("scaffold_seen", {}).get("recovery_at_k", {})
        novel = payload["slices"].get("scaffold_novel", {}).get("recovery_at_k", {})
        if seen and novel:
            drop = seen[str(eval_k)] - novel[str(eval_k)]
            payload["novel_scaffold_penalty_at_20"] = drop
            click.echo(f"  novel-scaffold penalty at k={eval_k}: {drop:+.4f}")

        results["runs"][name] = payload
        del model

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    click.echo(f"\nwrote {out}")


if __name__ == "__main__":
    main()
