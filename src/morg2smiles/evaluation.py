"""Evaluation: generate, judge, score.

One function, used by both the training loop (on validation, every epoch) and
the experiment runner (on whichever split was asked for). Keeping it in one
place means the number the iteration loop chases is computed by exactly the
same code as the number that gets reported.
"""

from __future__ import annotations

import time
from collections.abc import Sequence

from tqdm import tqdm

from .fingerprints import FPConfig, compute
from .generate import beam_search, sample
from .metrics import QueryOutcome, evaluate
from .model import Morg2SmilesModel
from .oracle import check_many

__all__ = ["evaluate_model", "generate_outcomes"]


def generate_outcomes(
    model: Morg2SmilesModel,
    smiles: Sequence[str],
    *,
    k: int = 20,
    fp_unseen: Sequence[bool] | None = None,
    strategy: str = "sample",
    batch_size: int = 16,
    temperature: float = 1.0,
    top_p: float = 1.0,
    show_progress: bool = True,
    **kwargs,
) -> list[QueryOutcome]:
    """Generate k candidates per molecule and judge them against its fingerprint.

    Args:
        model: A trained model.
        smiles: Reference molecules. Their fingerprints are the queries, and
            they double as the ``exact_structure`` reference.
        k: Candidates per query.
        fp_unseen: Per-molecule flags from
            :func:`morg2smiles.data.dataset.fp_unseen_mask`. When omitted, every
            query is treated as seen, which makes the ``fp_unseen`` slice empty
            and the primary metric zero -- deliberately, so a missing mask is
            obvious rather than quietly flattering.
        strategy: ``"sample"`` or ``"beam"``.
        batch_size: Queries per device batch. Sampling runs k per query, so the
            real batch on the device is ``batch_size * k``. The default was
            measured on an M2: throughput is flat from 16 to 32 and degrades
            sharply at 64, where the cache stops fitting comfortably.

    Returns:
        One :class:`QueryOutcome` per input molecule, in input order.
    """
    fp_cfg: FPConfig = model.fp_cfg
    if fp_unseen is not None and len(fp_unseen) != len(smiles):
        raise ValueError(f"fp_unseen has {len(fp_unseen)} entries for {len(smiles)} molecules")

    fps = [compute(s, fp_cfg) for s in smiles]
    outcomes: list[QueryOutcome] = []

    if strategy == "beam":
        iterator = tqdm(
            range(len(smiles)), desc="beam", unit=" mol", disable=not show_progress
        )
        for i in iterator:
            candidates = beam_search(model, fps[i], k=k, **kwargs)
            outcomes.append(
                QueryOutcome(
                    results=check_many(candidates, fps[i], fp_cfg, reference_smiles=smiles[i]),
                    fp_unseen=bool(fp_unseen[i]) if fp_unseen is not None else False,
                    reference_smiles=smiles[i],
                )
            )
        return outcomes

    total = (len(smiles) + batch_size - 1) // batch_size
    iterator = tqdm(
        range(0, len(smiles), batch_size),
        total=total,
        desc=f"sampling k={k}",
        unit=" batch",
        disable=not show_progress,
    )
    for start in iterator:
        chunk = list(range(start, min(start + batch_size, len(smiles))))
        batch_candidates = sample(
            model,
            [fps[i] for i in chunk],
            k=k,
            temperature=temperature,
            top_p=top_p,
            **kwargs,
        )
        for i, candidates in zip(chunk, batch_candidates, strict=True):
            outcomes.append(
                QueryOutcome(
                    results=check_many(candidates, fps[i], fp_cfg, reference_smiles=smiles[i]),
                    fp_unseen=bool(fp_unseen[i]) if fp_unseen is not None else False,
                    reference_smiles=smiles[i],
                )
            )
    return outcomes


def evaluate_model(
    model: Morg2SmilesModel,
    smiles: Sequence[str],
    *,
    k: int = 20,
    ks: Sequence[int] | None = None,
    fp_unseen: Sequence[bool] | None = None,
    **kwargs,
) -> dict:
    """Generate, judge and score, returning a full metric report.

    Args:
        k: Candidates to generate per query. This is the budget.
        ks: The k values to report recovery at. Defaults to the powers of the
            budget that fit -- reporting recovery@100 from 20 candidates would
            just restate recovery@20.

    Returns:
        The report from :func:`morg2smiles.metrics.evaluate`.
    """
    ks = ks or [n for n in (1, 5, 20, 100) if n <= k] or [k]
    started = time.perf_counter()
    outcomes = generate_outcomes(model, smiles, k=k, fp_unseen=fp_unseen, **kwargs)
    elapsed = time.perf_counter() - started
    report = evaluate(outcomes, ks=ks, elapsed_seconds=elapsed)
    report["generation"] = {"k": k, **{key: value for key, value in kwargs.items() if isinstance(value, (int, float, str, bool))}}
    return report
