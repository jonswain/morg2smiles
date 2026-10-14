"""What are the queries the model never inverts, and does likelihood rank better?

Item 2 of docs/next-steps-2026-10-13.md. Reads the per-query candidates that
``compare_checkpoints.py --dump-outcomes`` wrote, so nothing is re-sampled and
the numbers are those of the common protocol.

Two questions:

**Failure taxonomy.** Each fingerprint-unseen miss is put in the first bucket
that explains it:

``too_long``
    The reference needs more tokens than the decoder can emit. Unreachable by
    construction.
``beyond_budget``
    A candidate with the right fingerprint *was* drawn, but ranked outside the
    first k scored. Not a failure of the model's chemistry, only of the order
    it proposes things in -- so this bucket is what better ranking recovers.
``collision``
    Another ChEMBL molecule carries the same fingerprint, so the input
    underdetermines the answer. (Only relevant to struct@k; a twin with the
    right fingerprint would still count as recovery, so these are misses on a
    fingerprint that *is* recoverable in principle.)
``near``, ``analogue``, ``far``
    Best candidate Tanimoto >= 0.9, >= 0.7, below that.

Plus recovery against size and complexity, which separates an information
ceiling (failures concentrate on collisions) from a capability one (failures
concentrate on big, unusual molecules).

**Likelihood ranking.** Re-orders each query's first k scored candidates by
model log-probability and reports recovery@1/@5 under each ordering. The
candidate set is fixed, so only the order changes.

One caveat belongs next to the ranking numbers. The oracle here is fingerprint
equality, and anyone holding the query fingerprint can compute it locally, so in
practice every candidate can be verified for free and recovery@1 under an
oracle-first sort equals recovery@k. Ranking matters when verification is not
free -- a partial or perturbed fingerprint, or choosing *which* of several
fingerprint matches is the original molecule.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

import click
import torch
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

from morg2smiles.data.dataset import _fp_key, load_split
from morg2smiles.fingerprints import compute
from morg2smiles.generate import _batch_inputs
from morg2smiles.model import Morg2SmilesModel, select_device


def describe(smiles: str) -> dict:
    mol = Chem.MolFromSmiles(smiles)
    ring_info = mol.GetRingInfo()
    ring_sizes = [len(r) for r in ring_info.AtomRings()]
    return {
        "heavy_atoms": mol.GetNumHeavyAtoms(),
        "rings": ring_info.NumRings(),
        "largest_ring": max(ring_sizes, default=0),
        "stereocentres": len(Chem.FindMolChiralCenters(mol, includeUnassigned=True)),
        "charged": any(a.GetFormalCharge() != 0 for a in mol.GetAtoms()),
        "rot_bonds": rdMolDescriptors.CalcNumRotatableBonds(mol),
        "mw": Descriptors.MolWt(mol),
    }


@torch.no_grad()
def log_probs(model, fp, strings: list[str], device) -> list[float]:
    """Sum of token log-probabilities of each string given the fingerprint."""
    if not strings:
        return []
    tok = model.tokenizer
    encoded = []
    for s in strings:
        try:
            encoded.append(tok.encode(s))
        except Exception:
            encoded.append(None)
    usable = [e for e in encoded if e is not None and len(e) <= model.cfg.max_tokens]
    if not usable:
        return [-math.inf] * len(strings)
    width = max(len(e) for e in usable)
    tokens = torch.full((len(usable), width), tok.pad_id, dtype=torch.long, device=device)
    for i, e in enumerate(usable):
        tokens[i, : len(e)] = torch.tensor(e, device=device)
    indices, counts, mask = _batch_inputs([fp] * len(usable), model.fp_cfg, device)
    logits = model(indices, counts, mask, tokens)
    lp = logits.log_softmax(-1).gather(-1, tokens[:, 1:].unsqueeze(-1)).squeeze(-1)
    lp = lp.masked_fill(tokens[:, 1:] == tok.pad_id, 0.0).sum(-1).tolist()
    out, j = [], 0
    for e in encoded:
        if e is None or len(e) > model.cfg.max_tokens:
            out.append(-math.inf)
        else:
            out.append(lp[j])
            j += 1
    return out


def rate(xs) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


@click.command()
@click.option("--run", default="small_1m")
@click.option("--checkpoint", default="checkpoints/small_1m/best.pt")
@click.option(
    "--outcomes", type=click.Path(path_type=Path), default=Path("results/overnight3/outcomes")
)
@click.option("--collision-shard", default="data/shards/full")
@click.option("--k", default=20)
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    default=Path("results/overnight3/failure_analysis.json"),
)
def main(run, checkpoint, outcomes, collision_shard, k, out):
    rows = [json.loads(line) for line in open(outcomes / f"{run}.jsonl")]
    device = select_device()
    model, _ = Morg2SmilesModel.load(checkpoint, device=device)
    fp_cfg = model.fp_cfg
    tok = model.tokenizer

    click.echo(f"indexing {collision_shard} for fingerprint twins ...")
    twins: Counter = Counter()
    for split in ("train", "valid", "test"):
        for s in load_split(collision_shard, split):
            twins[_fp_key(compute(s, fp_cfg))] += 1

    queries = []
    for row in rows:
        if not row["fp_unseen"]:
            continue
        ref = row["reference"]
        fp = compute(ref, fp_cfg)
        scored = [r for r in row["results"] if r["valid"] and not r["duplicate"]][:k]
        spellings = Counter(r["canonical"] for r in row["results"] if r["valid"])
        ref_canon = Chem.MolToSmiles(Chem.MolFromSmiles(ref))
        in_corpus = twins[_fp_key(fp)]
        # The reference itself may or may not be in the collision shard; twins
        # are other molecules with the key.
        ref_in_shard = 1 if ref_canon in _shard_members(collision_shard) else 0
        q = {
            "reference": ref,
            "hit": any(r["fp_match"] for r in scored),
            # Over every candidate drawn, not just the first k scored. The gap
            # to "hit" is the budget window, not the model.
            "hit_anywhere": any(r["fp_match"] for r in row["results"]),
            "exact": any(r["exact_structure"] for r in scored),
            "best_tanimoto": max((r["tanimoto"] for r in row["results"]), default=0.0),
            "first_valid": bool(row["results"]) and row["results"][0]["valid"],
            "n_scored": len(scored),
            "n_tokens": len(tok.tokenize(ref)) + 2,
            "twins": max(0, in_corpus - ref_in_shard),
            "fp_bits": len(fp),
            **describe(ref),
        }
        lp_sampled = log_probs(model, fp, [r["smiles"] for r in scored], device)
        lp_canon = log_probs(model, fp, [r["canonical"] for r in scored], device)
        orders = {
            "generation": list(range(len(scored))),
            "logp_sampled": sorted(range(len(scored)), key=lambda i: -lp_sampled[i]),
            "logp_canonical": sorted(range(len(scored)), key=lambda i: -lp_canon[i]),
            "logp_per_token": sorted(
                range(len(scored)),
                key=lambda i: -lp_sampled[i] / max(1, len(tok.tokenize(scored[i]["smiles"]))),
            ),
            "n_spellings": sorted(
                range(len(scored)), key=lambda i: -spellings[scored[i]["canonical"]]
            ),
        }
        q["rank_hits"] = {
            name: {str(n): any(scored[i]["fp_match"] for i in order[:n]) for n in (1, 5)}
            | {f"exact{n}": any(scored[i]["exact_structure"] for i in order[:n]) for n in (1, 5)}
            for name, order in orders.items()
        }
        queries.append(q)

    n = len(queries)
    fails = [q for q in queries if not q["hit"]]
    max_tok = model.cfg.max_tokens

    def bucket(q):
        if q["n_tokens"] > max_tok:
            return "too_long"
        if q["hit_anywhere"]:
            return "beyond_budget"
        if q["twins"] > 0:
            return "collision"
        if q["best_tanimoto"] >= 0.9:
            return "near"
        if q["best_tanimoto"] >= 0.7:
            return "analogue"
        return "far"

    taxonomy = Counter(bucket(q) for q in fails)

    def by_bins(key, edges):
        out = {}
        for lo, hi in zip(edges, edges[1:], strict=False):
            sel = [q for q in queries if lo <= q[key] < hi]
            if sel:
                out[f"{lo}-{hi - 1}"] = {"n": len(sel), "recovery": rate(q["hit"] for q in sel)}
        return out

    report = {
        "run": run,
        "n_fp_unseen": n,
        "recovery": rate(q["hit"] for q in queries),
        "recovery_any_drawn": rate(q["hit_anywhere"] for q in queries),
        "n_fail": len(fails),
        "taxonomy": dict(taxonomy),
        "first_candidate_validity": rate(q["first_valid"] for q in queries),
        "with_twin": {
            "n": sum(q["twins"] > 0 for q in queries),
            "recovery": rate(q["hit"] for q in queries if q["twins"] > 0),
            "exact": rate(q["exact"] for q in queries if q["twins"] > 0),
        },
        "without_twin": {
            "recovery": rate(q["hit"] for q in queries if q["twins"] == 0),
        },
        "success_vs_failure": {
            key: {
                "hit_median": median(q[key] for q in queries if q["hit"]),
                "fail_median": median(q[key] for q in fails) if fails else None,
            }
            for key in (
                "heavy_atoms",
                "rings",
                "largest_ring",
                "stereocentres",
                "rot_bonds",
                "n_tokens",
                "fp_bits",
            )
        },
        "recovery_rate_by_flag": {
            flag: {
                "with": rate(q["hit"] for q in queries if q[flag]),
                "without": rate(q["hit"] for q in queries if not q[flag]),
                "n_with": sum(bool(q[flag]) for q in queries),
            }
            for flag in ("charged",)
        },
        "recovery_by_heavy_atoms": by_bins("heavy_atoms", [0, 15, 20, 25, 30, 35, 40, 50, 70, 200]),
        "recovery_by_stereocentres": by_bins("stereocentres", [0, 1, 2, 3, 5, 100]),
        "recovery_by_largest_ring": by_bins("largest_ring", [0, 7, 9, 13, 100]),
        "fail_best_tanimoto_mean": mean(q["best_tanimoto"] for q in fails) if fails else None,
        "ranking": {
            name: {
                metric: rate(q["rank_hits"][name][metric] for q in queries)
                for metric in ("1", "5", "exact1", "exact5")
            }
            for name in queries[0]["rank_hits"]
        },
        "underfilled": {
            "n": sum(q["n_scored"] < k for q in queries),
            "recovery": rate(q["hit"] for q in queries if q["n_scored"] < k),
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    (out.parent / f"failures_{run}.jsonl").write_text(
        "".join(
            json.dumps({key: v for key, v in q.items() if key != "rank_hits"}) + "\n" for q in fails
        )
    )
    click.echo(json.dumps(report, indent=2))


_MEMBERS: dict[str, set[str]] = defaultdict(set)


def _shard_members(shard: str) -> set[str]:
    if shard not in _MEMBERS:
        for split in ("train", "valid", "test"):
            _MEMBERS[shard].update(load_split(shard, split))
    return _MEMBERS[shard]


if __name__ == "__main__":
    main()
