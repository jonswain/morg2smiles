"""Candidate generation, and the small public API.

Because the fingerprint-to-molecule mapping is many-to-one and the oracle is
free, the right way to use this model is not "produce the answer" but "produce
k guesses and let the oracle pick". Recovery@k is defined on exactly that, so
sampling diversity matters as much as per-token accuracy: k guesses that are
near-copies of each other are worth little more than one.

Two strategies are provided. **Sampling** (temperature plus nucleus) gives the
diversity recovery@k rewards and is the default. **Beam search** gives the
model's most-probable strings, which is better at k=1 but saturates quickly
because beams share prefixes.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

import numpy as np
import torch
from torch import Tensor

from .data.dataset import fp_to_indices
from .fingerprints import FPConfig, Sparse
from .model import Morg2SmilesModel, select_device
from .oracle import OracleResult, check_many

__all__ = ["Morg2Smiles", "sample", "beam_search"]


def _as_sparse(fp: Sparse | np.ndarray | Sequence[int], cfg: FPConfig) -> Sparse:
    """Accept a sparse dict or a dense vector, return the sparse form."""
    if isinstance(fp, dict):
        return fp
    arr = np.asarray(fp)
    if arr.ndim != 1:
        raise ValueError(f"expected a 1-D fingerprint vector, got shape {arr.shape}")
    if cfg.folded and arr.size != cfg.n_bits:
        raise ValueError(f"expected {cfg.n_bits} bits, got {arr.size}")
    nz = np.nonzero(arr)[0]
    return {int(i): int(arr[i]) for i in nz}


def _batch_inputs(
    fps: Sequence[Sparse], cfg: FPConfig, device: torch.device
) -> tuple[Tensor, Tensor, Tensor]:
    """Pad a list of sparse fingerprints into encoder inputs."""
    converted = [fp_to_indices(fp, cfg) for fp in fps]
    max_bits = max((len(i) for i, _ in converted), default=1) or 1
    n = len(converted)

    indices = torch.zeros(n, max_bits, dtype=torch.long)
    counts = torch.zeros(n, max_bits, dtype=torch.long)
    mask = torch.zeros(n, max_bits, dtype=torch.bool)
    for i, (idx, cnt) in enumerate(converted):
        indices[i, : len(idx)] = torch.tensor(idx, dtype=torch.long)
        counts[i, : len(cnt)] = torch.tensor(cnt, dtype=torch.long)
        mask[i, : len(idx)] = True

    return indices.to(device), counts.to(device), mask.to(device)


def _filter_logits(logits: Tensor, temperature: float, top_p: float, top_k: int) -> Tensor:
    """Apply temperature, nucleus and top-k filtering to final-position logits."""
    if temperature != 1.0:
        logits = logits / max(temperature, 1e-6)

    if top_k > 0:
        kth = logits.topk(min(top_k, logits.size(-1)), dim=-1).values[..., -1:]
        logits = logits.masked_fill(logits < kth, float("-inf"))

    if 0.0 < top_p < 1.0:
        ordered, order = logits.sort(dim=-1, descending=True)
        cumulative = ordered.softmax(dim=-1).cumsum(dim=-1)
        # Keep tokens up to and including the one that crosses top_p, so the
        # kept set is never empty even when one token dominates.
        drop = cumulative - ordered.softmax(dim=-1) >= top_p
        drop[..., 0] = False
        ordered = ordered.masked_fill(drop, float("-inf"))
        logits = ordered.gather(-1, order.argsort(dim=-1))

    return logits


@torch.no_grad()
def sample(
    model: Morg2SmilesModel,
    fps: Sequence[Sparse],
    *,
    k: int = 20,
    temperature: float = 1.0,
    top_p: float = 1.0,
    top_k: int = 0,
    max_tokens: int | None = None,
    device: torch.device | None = None,
    generator: torch.Generator | None = None,
) -> list[list[str]]:
    """Draw k independent samples per fingerprint.

    Each fingerprint's encoder memory is computed once and reused across its k
    samples, so the cost is k decoder passes, not k full passes.

    Returns:
        One list of k SMILES strings per input fingerprint, in sample order.
        Strings may repeat; the oracle layer deduplicates.
    """
    model.eval()
    device = device or next(model.parameters()).device
    tokenizer = model.tokenizer
    max_tokens = max_tokens or model.cfg.max_tokens
    n = len(fps)
    if n == 0:
        return []

    indices, counts, mask = _batch_inputs(fps, model.fp_cfg, device)
    memory, memory_pad_mask = model.encode_fp(indices, counts, mask)

    # Interleave so row (i * k + j) is sample j of fingerprint i.
    memory = memory.repeat_interleave(k, dim=0)
    memory_pad_mask = memory_pad_mask.repeat_interleave(k, dim=0)

    rows = n * k
    nxt = torch.full((rows, 1), tokenizer.bos_id, dtype=torch.long, device=device)
    finished = torch.zeros(rows, dtype=torch.bool, device=device)
    caches = model.new_caches(rows, max_len=max_tokens, device=device)
    emitted = [nxt]

    for position in range(max_tokens - 1):
        # Incremental decoding: only the new token goes through the layers, and
        # the caches supply the prefix. Without this each step would re-attend
        # over the whole prefix, which dominates evaluation cost.
        logits = model.decode_step(
            nxt, memory, memory_pad_mask, caches=caches, offset=position
        )[:, -1, :]
        logits = _filter_logits(logits, temperature, top_p, top_k)
        probs = logits.softmax(dim=-1)
        nxt = torch.multinomial(probs, num_samples=1, generator=generator)

        # Once a sequence has emitted <eos>, hold it at <pad>: it stops
        # contributing tokens but keeps its row alignment and its cache slot.
        nxt = torch.where(finished.unsqueeze(1), torch.full_like(nxt, tokenizer.pad_id), nxt)
        emitted.append(nxt)
        finished |= nxt.squeeze(1) == tokenizer.eos_id
        if bool(finished.all()):
            break

    tokens = torch.cat(emitted, dim=1)
    decoded = [tokenizer.decode(row) for row in tokens.tolist()]
    return [decoded[i * k : (i + 1) * k] for i in range(n)]


def _reorder_caches(caches: list, index: Tensor) -> None:
    """Permute every layer's cache to follow beam selection."""
    for cache in caches:
        cache.reorder(index)


@torch.no_grad()
def beam_search(
    model: Morg2SmilesModel,
    fp: Sparse,
    *,
    k: int = 20,
    beam_width: int | None = None,
    length_penalty: float = 1.0,
    max_tokens: int | None = None,
    device: torch.device | None = None,
) -> list[str]:
    """Return up to k highest-probability SMILES for one fingerprint.

    Args:
        beam_width: Defaults to ``k``. Wider than k explores more before
            committing, at proportional cost.
        length_penalty: Divides a finished beam's log-probability by
            ``length ** length_penalty``. 1.0 compares mean per-token
            likelihood; 0.0 compares raw totals and favours short strings.

    Returns:
        SMILES strings, most probable first.
    """
    model.eval()
    device = device or next(model.parameters()).device
    tokenizer = model.tokenizer
    max_tokens = max_tokens or model.cfg.max_tokens
    width = beam_width or k

    indices, counts, mask = _batch_inputs([fp], model.fp_cfg, device)
    memory, memory_pad_mask = model.encode_fp(indices, counts, mask)
    memory = memory.repeat_interleave(width, dim=0)
    memory_pad_mask = memory_pad_mask.repeat_interleave(width, dim=0)

    tokens = torch.full((1, 1), tokenizer.bos_id, dtype=torch.long, device=device)
    scores = torch.zeros(1, device=device)
    caches = model.new_caches(1, max_len=max_tokens, device=device)
    nxt = tokens
    finished: list[tuple[float, list[int]]] = []

    for position in range(max_tokens - 1):
        live = nxt.size(0)
        logits = model.decode_step(
            nxt, memory[:live], memory_pad_mask[:live], caches=caches, offset=position
        )[:, -1, :]
        log_probs = logits.log_softmax(dim=-1) + scores.unsqueeze(1)

        flat = log_probs.view(-1)
        top_scores, top_flat = flat.topk(min(width, flat.numel()))
        beam_idx = torch.div(top_flat, log_probs.size(1), rounding_mode="floor")
        token_idx = top_flat % log_probs.size(1)

        _reorder_caches(caches, beam_idx)
        tokens = torch.cat([tokens[beam_idx], token_idx.unsqueeze(1)], dim=1)
        scores = top_scores

        done = token_idx == tokenizer.eos_id
        if bool(done.any()):
            for i in done.nonzero(as_tuple=True)[0].tolist():
                sequence = tokens[i].tolist()
                penalty = max(len(sequence) - 1, 1) ** length_penalty
                finished.append((scores[i].item() / penalty, sequence))
            keep = ~done
            if not bool(keep.any()):
                break
            keep_idx = keep.nonzero(as_tuple=True)[0]
            _reorder_caches(caches, keep_idx)
            tokens, scores, token_idx = tokens[keep_idx], scores[keep_idx], token_idx[keep_idx]

        if len(finished) >= k:
            break
        nxt = token_idx.unsqueeze(1)

    # Unfinished beams are still usable candidates when few beams completed.
    for i in range(tokens.size(0)):
        sequence = tokens[i].tolist()
        penalty = max(len(sequence) - 1, 1) ** length_penalty
        finished.append((scores[i].item() / penalty, sequence))

    finished.sort(key=lambda pair: pair[0], reverse=True)
    return [tokenizer.decode(sequence) for _, sequence in finished[:k]]


class Morg2Smiles:
    """The public interface: a loaded model you can hand fingerprints to.

    Example:
        >>> m = Morg2Smiles.load("checkpoints/best.pt")
        >>> m.generate(fp, k=20)        # oracle-verified matches first
    """

    def __init__(self, model: Morg2SmilesModel, device: torch.device | None = None):
        self.device = device or select_device()
        self.model = model.to(self.device).eval()

    @classmethod
    def load(cls, path: str | Path, *, device: str = "auto") -> Morg2Smiles:
        resolved = select_device(device)
        model, _ = Morg2SmilesModel.load(path, device=resolved)
        return cls(model, resolved)

    @property
    def fp_config(self) -> FPConfig:
        """The fingerprint config this model was trained for.

        Compute input fingerprints with this, or the oracle will reject
        everything for reasons that have nothing to do with the model.
        """
        return self.model.fp_cfg

    def generate(
        self,
        fp: Sparse | np.ndarray,
        *,
        k: int = 20,
        strategy: str = "sample",
        verified_only: bool = False,
        **kwargs,
    ) -> list[str]:
        """Generate candidate SMILES for one fingerprint, best first.

        Args:
            fp: The target fingerprint, sparse or dense, computed under
                :attr:`fp_config`.
            k: Number of distinct candidates to aim for.
            strategy: ``"sample"`` or ``"beam"``.
            verified_only: Return only candidates the oracle accepts. The
                default returns everything, ordered so verified matches come
                first, so a caller that wants a best-effort answer still gets
                one when nothing verifies.
            **kwargs: Passed through to :func:`sample` or :func:`beam_search`.

        Returns:
            Candidate SMILES: exact fingerprint matches first, then by
            descending similarity to the target.
        """
        sparse = _as_sparse(fp, self.fp_config)
        results = self._judge(sparse, k=k, strategy=strategy, **kwargs)
        if verified_only:
            return [r.smiles for r in results if r.fp_match]
        return [r.smiles for r in results]

    def _judge(self, fp: Sparse, *, k: int, strategy: str, **kwargs) -> list[OracleResult]:
        if strategy == "sample":
            candidates = sample(self.model, [fp], k=k, device=self.device, **kwargs)[0]
        elif strategy == "beam":
            candidates = beam_search(self.model, fp, k=k, device=self.device, **kwargs)
        else:
            raise ValueError(f"unknown strategy {strategy!r}; expected 'sample' or 'beam'")

        results = check_many(candidates, fp, self.fp_config)
        results.sort(key=lambda r: (r.fp_match, r.tanimoto), reverse=True)
        return results

    def generate_batch(
        self,
        fps: Iterable[Sparse | np.ndarray],
        *,
        k: int = 20,
        batch_size: int = 32,
        **kwargs,
    ) -> list[list[str]]:
        """Generate for many fingerprints, batched on the device."""
        sparse = [_as_sparse(fp, self.fp_config) for fp in fps]
        out: list[list[str]] = []
        for start in range(0, len(sparse), batch_size):
            chunk = sparse[start : start + batch_size]
            out.extend(sample(self.model, chunk, k=k, device=self.device, **kwargs))
        return out
