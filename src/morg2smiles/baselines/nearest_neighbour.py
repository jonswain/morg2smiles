"""Nearest-neighbour retrieval: the honest memorisation baseline.

Given a query fingerprint, return the most similar training molecules. This is
not a reconstruction method at all -- it cannot produce a molecule it has never
seen -- which is exactly why it is the right control.

On the ``all`` slice it scores genuinely well, because a held-out fingerprint
often collides with a training one and retrieval then returns a verified exact
match for free. On the ``fp_unseen`` slice it scores near zero by construction.
Any neural result that fails to beat it **on the fp_unseen slice** has learned
retrieval, not chemistry, and the gap between the two slices is the clearest
single read on whether a model is doing the task.
"""

from __future__ import annotations

import time
from collections.abc import Sequence

from rdkit import DataStructs
from tqdm import tqdm

from ..fingerprints import FPConfig, Sparse, compute, compute_bitvect, tanimoto
from ..metrics import QueryOutcome, evaluate
from ..oracle import check_many

__all__ = ["NearestNeighbourBaseline", "evaluate_baseline"]


def _fp_key(fp: Sparse) -> tuple:
    return tuple(sorted(fp.items()))


class NearestNeighbourBaseline:
    """Retrieves training molecules by fingerprint similarity.

    Args:
        train_smiles: The training corpus to retrieve from.
        fp_cfg: Fingerprint config, which must match the one used for queries.
        show_progress: Show a bar while indexing.
    """

    def __init__(
        self, train_smiles: Sequence[str], fp_cfg: FPConfig, *, show_progress: bool = True
    ):
        self.fp_cfg = fp_cfg
        self.train_smiles = list(train_smiles)

        # Folded binary fingerprints get RDKit's bulk similarity, which is
        # orders of magnitude faster than comparing dicts in Python. Other
        # modes fall back to the generic path.
        self.use_bitvect = fp_cfg.folded and not fp_cfg.counts
        iterator = tqdm(
            self.train_smiles, desc="indexing baseline", unit=" mol", disable=not show_progress
        )

        self.bitvects = []
        self.sparse: list[Sparse] = []
        # Exact-fingerprint lookup. This is what actually produces verified
        # hits: when a query fingerprint is present in training, the molecule
        # that generated it is a guaranteed oracle match.
        self.exact: dict[tuple, str] = {}

        for smiles in iterator:
            fp = compute(smiles, fp_cfg)
            self.exact.setdefault(_fp_key(fp), smiles)
            if self.use_bitvect:
                self.bitvects.append(compute_bitvect(smiles, fp_cfg))
            else:
                self.sparse.append(fp)

    def __len__(self) -> int:
        return len(self.train_smiles)

    def generate(self, fp: Sparse, *, k: int = 20) -> list[str]:
        """Return up to k training molecules, most similar first.

        An exact fingerprint match, if the index holds one, is placed first.
        """
        ranked: list[str] = []
        exact = self.exact.get(_fp_key(fp))
        if exact is not None:
            ranked.append(exact)
        if len(ranked) >= k:
            return ranked[:k]

        if self.use_bitvect:
            query = _bitvect_from_sparse(fp, self.fp_cfg)
            scores = DataStructs.BulkTanimotoSimilarity(query, self.bitvects)
        else:
            scores = [tanimoto(fp, ref) for ref in self.sparse]

        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        for i in order:
            candidate = self.train_smiles[i]
            if candidate != exact:
                ranked.append(candidate)
            if len(ranked) >= k:
                break
        return ranked[:k]


def _bitvect_from_sparse(fp: Sparse, cfg: FPConfig):
    """Rebuild an RDKit bit vector from a sparse fingerprint."""
    from rdkit.DataStructs import ExplicitBitVect

    vec = ExplicitBitVect(cfg.n_bits)
    for bit in fp:
        vec.SetBit(bit)
    return vec


def evaluate_baseline(
    train_smiles: Sequence[str],
    query_smiles: Sequence[str],
    fp_cfg: FPConfig,
    *,
    k: int = 20,
    ks: Sequence[int] | None = None,
    fp_unseen: Sequence[bool] | None = None,
    show_progress: bool = True,
) -> dict:
    """Score the retrieval baseline with the same metrics the model uses.

    Returns:
        A report in the same shape as
        :func:`morg2smiles.evaluation.evaluate_model`, so the two go into the
        leaderboard side by side.
    """
    ks = ks or [n for n in (1, 5, 20, 100) if n <= k] or [k]
    index = NearestNeighbourBaseline(train_smiles, fp_cfg, show_progress=show_progress)

    started = time.perf_counter()
    outcomes: list[QueryOutcome] = []
    iterator = tqdm(
        range(len(query_smiles)), desc="baseline queries", unit=" mol", disable=not show_progress
    )
    for i in iterator:
        fp = compute(query_smiles[i], fp_cfg)
        candidates = index.generate(fp, k=k)
        outcomes.append(
            QueryOutcome(
                results=check_many(candidates, fp, fp_cfg, reference_smiles=query_smiles[i]),
                fp_unseen=bool(fp_unseen[i]) if fp_unseen is not None else False,
                reference_smiles=query_smiles[i],
            )
        )
    elapsed = time.perf_counter() - started

    report = evaluate(outcomes, ks=ks, elapsed_seconds=elapsed)
    report["generation"] = {"k": k, "method": "nearest_neighbour", "n_index": len(index)}
    return report
