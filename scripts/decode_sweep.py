"""Is the decoder's temperature leaving points on the table?

Every number in this project was measured at temperature 1.0, top_p 1.0, and
nothing has ever checked whether that is the right place to sample from.
`small_1m` fills only 63.9% of its 20-slot budget because it keeps re-proposing
the same molecules, which is what a too-cold decoder looks like; but a hotter
one buys diversity with validity. The trade has a maximum somewhere and it
costs nothing to find.

**Tuned on a disjoint set.** The grid is evaluated on molecules drawn from the
clean pool *excluding* the 2,000 of the common protocol, so a setting chosen
here can then be verified on the common protocol without having been fitted to
it. Choosing decode settings on the reported evaluation set would be tuning on
the test set in all but name.

Reports both orderings, since consensus ranking and temperature interact: a
hotter decoder spreads its votes thinner.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import click

from morg2smiles.data.dataset import _fp_key, load_split
from morg2smiles.evaluation import generate_outcomes
from morg2smiles.fingerprints import compute
from morg2smiles.metrics import evaluate
from morg2smiles.model import Morg2SmilesModel, select_device


@click.command()
@click.option("--checkpoint", default="checkpoints/small_1m/best.pt")
@click.option("--n", "n_queries", default=400, show_default=True)
@click.option("--k", default=20)
@click.option("--temperatures", default="0.7,0.8,0.9,1.0,1.1")
@click.option("--top-ps", default="1.0,0.95,0.9")
@click.option("--max-oversample", default=10.0)
@click.option("--pool-shard", default="data/shards/1m")
@click.option(
    "--protocol-seed", default=0, help="Seed of the common protocol, whose molecules are excluded."
)
@click.option(
    "--protocol-n", default=2000, help="Size of the common protocol, whose molecules are excluded."
)
@click.option("--seed", default=7, help="Seed for the tuning draw and for sampling.")
@click.option(
    "--out", type=click.Path(path_type=Path), default=Path("results/overnight4/decode_sweep.json")
)
def main(
    checkpoint,
    n_queries,
    k,
    temperatures,
    top_ps,
    max_oversample,
    pool_shard,
    protocol_seed,
    protocol_n,
    seed,
    out,
):
    device = select_device()
    model, _ = Morg2SmilesModel.load(checkpoint, device=device)
    fp_cfg = model.fp_cfg

    # Rebuild the common protocol's pool and draw exactly as
    # compare_checkpoints.py does, so the molecules it uses can be removed.
    shards = ["data/shards/100k", "data/shards/1m", "data/shards/full"]
    train_molecules: set[str] = set()
    for shard in shards:
        train_molecules |= set(load_split(shard, "train"))
    pool = [s for s in load_split(pool_shard, "valid") if s not in train_molecules]
    protocol_idx = set(
        random.Random(protocol_seed).sample(range(len(pool)), min(protocol_n, len(pool)))
    )
    tuning_pool = [s for i, s in enumerate(pool) if i not in protocol_idx]
    click.echo(
        f"clean pool {len(pool):,}; {len(protocol_idx):,} reserved to the common protocol; "
        f"tuning from the remaining {len(tuning_pool):,}"
    )

    rng = random.Random(seed)
    smiles = [tuning_pool[i] for i in sorted(rng.sample(range(len(tuning_pool)), n_queries))]

    click.echo(f"indexing {len(train_molecules):,} training fingerprints ...")
    train_keys = {_fp_key(compute(s, fp_cfg)) for s in train_molecules}
    fp_unseen = [_fp_key(compute(s, fp_cfg)) not in train_keys for s in smiles]
    click.echo(f"tuning set: {len(smiles):,} molecules, {sum(fp_unseen):,} fingerprint-unseen")

    report = {
        "checkpoint": checkpoint,
        "n_queries": len(smiles),
        "n_fp_unseen": sum(fp_unseen),
        "k": k,
        "tuning_seed": seed,
        "disjoint_from_protocol": {"seed": protocol_seed, "n": protocol_n},
        "grid": {},
    }
    header = (
        f"{'T':>5}{'top_p':>7}{'rec@1':>9}{'con@1':>9}{'rec@20':>9}{'con@20':>9}"
        f"{'valid':>8}{'uniq':>7}{'fill':>7}{'samp':>7}"
    )
    click.echo(header)
    click.echo("-" * len(header))
    best = None
    for temperature in (float(x) for x in temperatures.split(",")):
        for top_p in (float(x) for x in top_ps.split(",")):
            outcomes = generate_outcomes(
                model,
                smiles,
                k=k,
                fp_unseen=fp_unseen,
                temperature=temperature,
                top_p=top_p,
                max_oversample=max_oversample,
                seed=seed,
                show_progress=False,
            )
            u = evaluate(outcomes, ks=(1, 5, 20))["slices"]["fp_unseen"]
            row = {
                "recovery": u["recovery_at_k"],
                "recovery_consensus": u["recovery_at_k_consensus"],
                "validity": u["validity"],
                "unique_valid_per_query": u["unique_valid_per_query"],
                "budget_filled_rate": u["budget_filled_rate"],
                "mean_samples_per_query": u["mean_samples_per_query"],
                "duplicate_rate": u["duplicate_rate"],
            }
            report["grid"][f"T{temperature}_p{top_p}"] = row
            click.echo(
                f"{temperature:>5.2f}{top_p:>7.2f}{u['recovery_at_k']['1']:>9.4f}"
                f"{u['recovery_at_k_consensus']['1']:>9.4f}{u['recovery_at_k']['20']:>9.4f}"
                f"{u['recovery_at_k_consensus']['20']:>9.4f}{u['validity']:>8.3f}"
                f"{u['unique_valid_per_query']:>7.1f}{u['budget_filled_rate']:>7.3f}"
                f"{u['mean_samples_per_query']:>7.0f}"
            )
            score = u["recovery_at_k_consensus"]["20"]
            if best is None or score > best[1]:
                best = (f"T{temperature}_p{top_p}", score, temperature, top_p)

    report["best_by_consensus_rec20"] = {
        "name": best[0],
        "value": best[1],
        "temperature": best[2],
        "top_p": best[3],
    }
    baseline = report["grid"].get("T1.0_p1.0", {}).get("recovery_consensus", {}).get("20")
    if baseline is not None:
        report["best_vs_default_points"] = 100 * (best[1] - baseline)
        click.echo(
            f"\nbest {best[0]} at {best[1]:.4f}; default T1.0_p1.0 at {baseline:.4f} "
            f"({100 * (best[1] - baseline):+.2f} points on the tuning set)"
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    click.echo(f"wrote {out}")


if __name__ == "__main__":
    main()
