"""Torch dataset, SMILES augmentation, and the ``fp_unseen`` mask.

Two things here carry more weight than the usual dataset boilerplate.

**SMILES randomisation.** The fingerprint determines a *molecule*, and a
molecule has many valid SMILES strings. Training only on the canonical string
teaches the decoder RDKit's canonicalisation algorithm alongside the chemistry,
and makes sampling collapse onto near-copies of one string -- which caps
recovery@k, since k guesses are only worth having if they differ. Emitting a
fresh random traversal each epoch removes that, and tends to be the single
largest win available on this task.

**The ``fp_unseen`` mask.** Computed per fingerprint config and cached, it marks
test molecules whose fingerprint appears nowhere in training. Metrics are
reported with and without it; see :mod:`morg2smiles.metrics` for why that
distinction decides whether a result means anything.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import torch
from rdkit import Chem, RDLogger
from torch.utils.data import Dataset
from tqdm import tqdm

from ..fingerprints import FPConfig, Sparse, compute
from ..tokenizer import SmilesTokenizer

RDLogger.DisableLog("rdApp.*")

__all__ = [
    "FingerprintDataset",
    "collate",
    "load_split",
    "fp_to_indices",
    "fp_unseen_mask",
    "randomize_smiles",
    "MAX_COUNT",
]

#: Count values are clamped to this before embedding. Morgan counts above a
#: handful are rare and carry little extra signal, so a short embedding table
#: avoids rows that are almost never trained.
MAX_COUNT = 8


def load_split(shard_dir: str | Path, split: str, *, scaffold: bool = False) -> list[str]:
    """Read one split's canonical SMILES.

    Args:
        shard_dir: A directory produced by :func:`morg2smiles.data.prepare.prepare`.
        split: ``"train"``, ``"valid"`` or ``"test"``.
        scaffold: Read the scaffold-split variant instead of the random one.
    """
    base = Path(shard_dir) / "scaffold" if scaffold else Path(shard_dir)
    path = base / f"{split}.smi"
    if not path.exists():
        raise FileNotFoundError(f"no {split} split at {path}; run morg2smiles.data.prepare first")
    return [line for line in path.read_text().splitlines() if line]


def randomize_smiles(smiles: str, rng: random.Random) -> str:
    """Return a random valid SMILES for the same molecule.

    Falls back to the input if RDKit cannot re-render the molecule, so a rare
    failure degrades to canonical training rather than crashing the epoch.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return smiles
    try:
        # Renumbering the atoms before rendering gives a different traversal
        # root and order; doRandom alone is less uniform across RDKit versions.
        order = list(range(mol.GetNumAtoms()))
        rng.shuffle(order)
        mol = Chem.RenumberAtoms(mol, order)
        out = Chem.MolToSmiles(mol, canonical=False)
        return out or smiles
    except Exception:
        return smiles


def fp_to_indices(fp: Sparse, cfg: FPConfig) -> tuple[list[int], list[int]]:
    """Convert a sparse fingerprint to parallel embedding-index and count lists.

    Folded identifiers are bit indices and are used directly. Unfolded
    identifiers span the 32-bit space, so they are folded into
    :attr:`FPConfig.vocab_size` buckets here -- collisions reappear, but only
    inside the model's embedding table, never in the oracle's comparison.
    """
    vocab = cfg.vocab_size
    indices, counts = [], []
    for identifier, count in fp.items():
        indices.append(identifier if cfg.folded else identifier % vocab)
        counts.append(min(count, MAX_COUNT))
    return indices, counts


class FingerprintDataset(Dataset):
    """Pairs of (fingerprint, SMILES token ids).

    The fingerprint is always computed from the *canonical* molecule, while the
    target string may be a random traversal of it. That asymmetry is the point:
    one input, many correct outputs.
    """

    def __init__(
        self,
        smiles: list[str],
        fp_cfg: FPConfig,
        tokenizer: SmilesTokenizer,
        *,
        max_tokens: int = 128,
        randomize: bool = False,
        seed: int = 0,
    ):
        self.smiles = smiles
        self.fp_cfg = fp_cfg
        self.tokenizer = tokenizer
        self.max_tokens = max_tokens
        self.randomize = randomize
        self.seed = seed
        self.epoch = 0

    def set_epoch(self, epoch: int) -> None:
        """Reseed augmentation so each epoch sees different traversals.

        Called by the training loop. Without it, every epoch would reuse the
        same "random" strings and the augmentation would be worth little.
        """
        self.epoch = epoch

    def __len__(self) -> int:
        return len(self.smiles)

    def __getitem__(self, i: int) -> dict:
        canonical = self.smiles[i]
        target = canonical
        if self.randomize:
            # Seeded on (seed, epoch, index) so runs stay reproducible while
            # still varying per epoch, and so dataloader workers agree.
            rng = random.Random((self.seed, self.epoch, i).__hash__())
            target = randomize_smiles(canonical, rng)

        try:
            ids = self.tokenizer.encode(target)
        except Exception:
            ids = self.tokenizer.encode(canonical)
        if len(ids) > self.max_tokens:
            # Randomisation can lengthen a string past the limit; fall back
            # rather than truncating, which would train on an invalid target.
            ids = self.tokenizer.encode(canonical)[: self.max_tokens]

        fp = compute(canonical, self.fp_cfg)
        indices, counts = fp_to_indices(fp, self.fp_cfg)
        return {
            "fp_indices": torch.tensor(indices, dtype=torch.long),
            "fp_counts": torch.tensor(counts, dtype=torch.long),
            "tokens": torch.tensor(ids, dtype=torch.long),
            "index": i,
        }


def collate(batch: list[dict], pad_id: int = 0) -> dict:
    """Pad a batch of variable-length fingerprint sets and token sequences.

    Padding is dynamic -- to the longest member of the batch, not a global
    maximum -- because a dense 2048-wide input would be ~40x the real work: a
    drug-like molecule sets only a few dozen bits.
    """
    n = len(batch)
    max_bits = max(len(b["fp_indices"]) for b in batch)
    max_len = max(len(b["tokens"]) for b in batch)

    fp_indices = torch.zeros(n, max_bits, dtype=torch.long)
    fp_counts = torch.zeros(n, max_bits, dtype=torch.long)
    fp_mask = torch.zeros(n, max_bits, dtype=torch.bool)
    tokens = torch.full((n, max_len), pad_id, dtype=torch.long)

    for i, b in enumerate(batch):
        nb, nt = len(b["fp_indices"]), len(b["tokens"])
        fp_indices[i, :nb] = b["fp_indices"]
        fp_counts[i, :nb] = b["fp_counts"]
        fp_mask[i, :nb] = True
        tokens[i, :nt] = b["tokens"]

    return {
        "fp_indices": fp_indices,
        "fp_counts": fp_counts,
        # True where a real bit sits; the encoder attends only to these, and a
        # molecule with zero set bits would otherwise produce a NaN attention row.
        "fp_mask": fp_mask,
        "tokens": tokens,
        "token_mask": tokens != pad_id,
        "index": torch.tensor([b["index"] for b in batch], dtype=torch.long),
    }


def _fp_key(fp: Sparse) -> bytes:
    """Compact hashable form of a sparse fingerprint, for set membership.

    A 16-byte digest rather than the obvious ``tuple(sorted(fp.items()))``,
    because this is used to index the *whole training set*. The tuple form
    keeps ~50 live Python tuples per molecule, which measured around 5 KB per
    molecule -- fine for a 100k shard, about 4.5 GB for a 1M one, which is
    where the index stops fitting comfortably and starts thrashing.

    blake2b rather than ``hash()`` so the digest is stable across processes and
    runs, which matters because the resulting mask is cached on disk. At 16
    bytes the collision probability over a million fingerprints is ~1e-27; a
    collision would mark one unseen fingerprint as seen, costing a query from
    the primary slice rather than corrupting a metric.
    """
    payload = b"".join(
        index.to_bytes(4, "little") + count.to_bytes(2, "little")
        for index, count in sorted(fp.items())
    )
    return hashlib.blake2b(payload, digest_size=16).digest()


def fp_unseen_mask(
    shard_dir: str | Path,
    fp_cfg: FPConfig,
    *,
    split: str = "test",
    scaffold: bool = False,
    cache: bool = True,
    show_progress: bool = True,
) -> list[bool]:
    """Flag the molecules in ``split`` whose fingerprint is absent from training.

    Results are cached per fingerprint config, since computing them means
    fingerprinting the whole training set.

    Returns:
        One boolean per molecule in the split, in file order. True means the
        fingerprint is unseen, so recovering it cannot be memorisation.
    """
    shard_dir = Path(shard_dir)
    tag = f"{'scaffold_' if scaffold else ''}{split}_{fp_cfg.fingerprint_id}"
    cache_path = shard_dir / "masks" / f"fp_unseen_{tag}.json"

    if cache and cache_path.exists():
        payload = json.loads(cache_path.read_text())
        if payload.get("fingerprint_id") == fp_cfg.fingerprint_id:
            return payload["mask"]

    train = load_split(shard_dir, "train", scaffold=scaffold)
    query = load_split(shard_dir, split, scaffold=scaffold)

    iterator = tqdm(train, desc="indexing train fps", disable=not show_progress)
    train_keys = {_fp_key(compute(s, fp_cfg)) for s in iterator}

    iterator = tqdm(query, desc=f"checking {split} fps", disable=not show_progress)
    mask = [_fp_key(compute(s, fp_cfg)) not in train_keys for s in iterator]

    if cache:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(
                {
                    "fingerprint_id": fp_cfg.fingerprint_id,
                    "fp_config": fp_cfg.to_dict(),
                    "split": split,
                    "scaffold": scaffold,
                    "n_unseen": sum(mask),
                    "mask": mask,
                }
            )
        )
    return mask
