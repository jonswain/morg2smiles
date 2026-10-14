"""Is there a generative model in here? Perturb the fingerprint and see.

From docs/next-steps-2026-10-13.md: at k=20 the model almost never finds a
*different* molecule with the right fingerprint, because there is essentially
one right answer. Loosening the constraint is the route to generation, and the
cheapest loosening is to perturb a known fingerprint and ask what the model
produces for it. No retraining.

For each of N fingerprint-unseen molecules from the common protocol, and each
perturbation size n, three conditions:

``drop``  remove n of the molecule's set bits
``add``   set n random bits that were unset
``swap``  remove n/2 and add n/2

and sample k candidates. What is measured, per condition:

* validity and distinct valid molecules per query -- does the model still
  produce chemistry, or does it fall apart off-manifold?
* exact match to the *perturbed* fingerprint -- does it find a real molecule
  that lands exactly there? (Often none exists, especially for ``add``.)
* best Tanimoto to the perturbed target, and to the *original* fingerprint --
  does it chase the perturbation, or snap back to the molecule it knows?
* recovery of the original molecule -- the same thing seen as robustness.
* novelty -- fraction of distinct valid candidates that are not the original.

A model that is only a lookup will snap back (original Tanimoto high, perturbed
Tanimoto no better than the original's). A model that has learned bits as
substructure evidence will move towards the perturbed target.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from statistics import mean

import click
from rdkit import Chem

from morg2smiles.fingerprints import compute, equal, tanimoto
from morg2smiles.generate import sample
from morg2smiles.model import Morg2SmilesModel, select_device
from morg2smiles.oracle import check_many


def perturb(
    fp: dict[int, int], mode: str, n: int, n_bits: int, rng: random.Random
) -> dict[int, int]:
    on = sorted(fp)
    off = [b for b in range(n_bits) if b not in fp]
    n_drop = {"drop": n, "add": 0, "swap": n // 2}[mode]
    n_add = {"drop": 0, "add": n, "swap": n - n // 2}[mode]
    n_drop = min(n_drop, len(on) - 1)
    out = dict(fp)
    for b in rng.sample(on, n_drop):
        del out[b]
    for b in rng.sample(off, n_add):
        out[b] = 1
    return out


@click.command()
@click.option("--checkpoint", default="checkpoints/small_1m/best.pt")
@click.option(
    "--outcomes",
    type=click.Path(path_type=Path),
    default=Path("results/overnight3/outcomes/small_1m.jsonl"),
)
@click.option("--n", "n_queries", default=300)
@click.option("--k", default=40, help="Raw strings drawn per query.")
@click.option("--sizes", default="0,1,2,4,8,16")
@click.option("--modes", default="drop,add,swap")
@click.option("--seed", default=0)
@click.option("--batch-size", default=16)
@click.option(
    "--out", type=click.Path(path_type=Path), default=Path("results/overnight3/bitflip.json")
)
def main(checkpoint, outcomes, n_queries, k, sizes, modes, seed, batch_size, out):
    device = select_device()
    model, _ = Morg2SmilesModel.load(checkpoint, device=device)
    fp_cfg = model.fp_cfg
    if fp_cfg.counts:
        raise click.ClickException("bit flips are defined for binary fingerprints only")

    rows = [json.loads(line) for line in open(outcomes)]
    refs = [r["reference"] for r in rows if r["fp_unseen"]]
    rng = random.Random(seed)
    refs = sorted(rng.sample(refs, min(n_queries, len(refs))))
    originals = [compute(s, fp_cfg) for s in refs]
    canon = [Chem.MolToSmiles(Chem.MolFromSmiles(s)) for s in refs]

    import torch

    generator = torch.Generator(device=device)
    report = {"checkpoint": checkpoint, "n_queries": len(refs), "k_raw": k, "conditions": {}}
    for mode in modes.split(","):
        for size in (int(x) for x in sizes.split(",")):
            if size == 0 and mode != modes.split(",")[0]:
                continue
            name = "none" if size == 0 else f"{mode}{size}"
            prng = random.Random(f"{seed}-{name}")
            targets = [perturb(fp, mode, size, fp_cfg.n_bits, prng) for fp in originals]
            generator.manual_seed(seed)
            stats = []
            for start in range(0, len(refs), batch_size):
                idx = range(start, min(start + batch_size, len(refs)))
                cands = sample(model, [targets[i] for i in idx], k=k, generator=generator)
                for i, c in zip(idx, cands, strict=True):
                    judged = check_many(c, targets[i], fp_cfg, reference_smiles=refs[i])
                    distinct = [r for r in judged if r.valid and not r.duplicate]
                    cand_fps = [compute(r.canonical, fp_cfg) for r in distinct]
                    stats.append(
                        {
                            "validity": mean(r.valid for r in judged) if judged else 0.0,
                            "distinct": len(distinct),
                            "hit_perturbed": any(r.fp_match for r in distinct),
                            "hit_original_fp": any(equal(f, originals[i]) for f in cand_fps),
                            "exact_original": any(r.canonical == canon[i] for r in distinct),
                            "best_tan_perturbed": max((r.tanimoto for r in distinct), default=0.0),
                            "best_tan_original": max(
                                (tanimoto(f, originals[i]) for f in cand_fps), default=0.0
                            ),
                            "target_vs_original": tanimoto(targets[i], originals[i]),
                            "novel_fraction": (
                                mean(r.canonical != canon[i] for r in distinct) if distinct else 0.0
                            ),
                            # Novel candidates that sit closer to the perturbed
                            # target than the original molecule does.
                            "beats_original_on_target": any(
                                r.canonical != canon[i]
                                and r.tanimoto > tanimoto(originals[i], targets[i])
                                for r in distinct
                            ),
                        }
                    )
            agg = {key: mean(float(s[key]) for s in stats) for key in stats[0]}
            report["conditions"][name] = agg
            click.echo(
                f"{name:>8}  valid {agg['validity']:.3f}  distinct {agg['distinct']:5.1f}  "
                f"hit_pert {agg['hit_perturbed']:.3f}  exact_orig {agg['exact_original']:.3f}  "
                f"tan_pert {agg['best_tan_perturbed']:.3f}  tan_orig {agg['best_tan_original']:.3f}  "
                f"tgt~orig {agg['target_vs_original']:.3f}  beats {agg['beats_original_on_target']:.3f}"
            )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    click.echo(f"wrote {out}")


if __name__ == "__main__":
    main()
