"""Single source of truth for every fingerprint decision in the project.

Training, generation, evaluation and the oracle must all agree exactly on how a
fingerprint is computed -- a silent mismatch would make recovery rates
meaningless rather than merely wrong. So there is exactly one way to build a
fingerprint here (:func:`compute`), exactly one object describing how
(:class:`FPConfig`), and every artefact that stores fingerprints also stores
:attr:`FPConfig.fingerprint_id` so mismatches fail loudly on load.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from functools import lru_cache

import numpy as np
from rdkit import Chem, DataStructs
from rdkit.Chem import rdFingerprintGenerator

__all__ = [
    "FPConfig",
    "Sparse",
    "compute",
    "compute_dense",
    "compute_bitvect",
    "equal",
    "tanimoto",
    "check_config_match",
    "FPConfigMismatch",
]

#: A fingerprint in the project's internal form: identifier -> count.
#:
#: For folded modes the identifier is a bit index in ``[0, n_bits)``; for
#: unfolded modes it is the raw 32/64-bit Morgan environment identifier. For
#: binary modes every count is exactly 1. This one representation serves the
#: model's set encoder, the oracle and the metrics alike.
Sparse = dict[int, int]


class FPConfigMismatch(ValueError):
    """Raised when an artefact's fingerprint config differs from the one in use."""


@dataclass(frozen=True)
class FPConfig:
    """How to compute a Morgan fingerprint.

    Attributes:
        radius: Morgan radius. ``2`` corresponds to the conventional ECFP4.
        n_bits: Fold width. Ignored when ``folded`` is False.
        counts: Keep substructure multiplicity instead of collapsing to presence.
        folded: Hash identifiers down into ``n_bits``. False keeps the raw
            identifier set, which has no collisions and is therefore a much
            easier -- and less realistic -- reconstruction target.
        use_chirality: Include chiral tags in atom invariants. Off by default,
            and the data pipeline strips stereochemistry to match: a stereo-blind
            fingerprint cannot possibly determine stereochemistry, so leaving it
            in the target would only add unlearnable noise.
        use_features: Use FCFP-style pharmacophoric atom invariants instead of
            plain atom types.
    """

    radius: int = 2
    n_bits: int = 2048
    counts: bool = False
    folded: bool = True
    use_chirality: bool = False
    use_features: bool = False

    def __post_init__(self) -> None:
        if self.radius < 0:
            raise ValueError(f"radius must be >= 0, got {self.radius}")
        if self.folded and self.n_bits < 1:
            raise ValueError(f"n_bits must be >= 1, got {self.n_bits}")

    @property
    def fingerprint_id(self) -> str:
        """Short stable hash of this config, stamped onto every artefact."""
        payload = json.dumps(self.to_dict(), sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()[:12]

    @property
    def vocab_size(self) -> int:
        """Size of the identifier space the model's set encoder embeds over.

        Folded identifiers are used directly as embedding indices. Unfolded
        identifiers span the full 32-bit space, so they are hashed into this
        many buckets instead -- collisions reappear, but only inside the model,
        not in the oracle's view of the fingerprint.
        """
        return self.n_bits if self.folded else 2**20

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> FPConfig:
        known = {f for f in cls.__dataclass_fields__}
        unknown = set(d) - known
        if unknown:
            raise ValueError(f"unknown FPConfig fields: {sorted(unknown)}")
        return cls(**d)

    def describe(self) -> str:
        mode = "count" if self.counts else "binary"
        fold = f"folded/{self.n_bits}" if self.folded else "unfolded"
        return f"morgan r={self.radius} {mode} {fold}"


@lru_cache(maxsize=16)
def _generator(cfg: FPConfig):
    """Cached RDKit generator for a config. Generators are stateless and reusable."""
    inv_gen = rdFingerprintGenerator.GetMorganFeatureAtomInvGen() if cfg.use_features else None
    return rdFingerprintGenerator.GetMorganGenerator(
        radius=cfg.radius,
        fpSize=cfg.n_bits,
        includeChirality=cfg.use_chirality,
        atomInvariantsGenerator=inv_gen,
    )


def _to_mol(mol_or_smiles: Chem.Mol | str) -> Chem.Mol | None:
    if isinstance(mol_or_smiles, Chem.Mol):
        return mol_or_smiles
    return Chem.MolFromSmiles(mol_or_smiles)


def compute(mol_or_smiles: Chem.Mol | str, cfg: FPConfig) -> Sparse:
    """Compute a fingerprint in the project's internal sparse form.

    Args:
        mol_or_smiles: An RDKit molecule, or a SMILES string to parse.
        cfg: The fingerprint specification.

    Returns:
        A mapping of identifier to count. Counts are all 1 unless
        ``cfg.counts``.

    Raises:
        ValueError: If a SMILES string could not be parsed.
    """
    mol = _to_mol(mol_or_smiles)
    if mol is None:
        raise ValueError(f"could not parse SMILES: {mol_or_smiles!r}")

    gen = _generator(cfg)
    if cfg.folded:
        counts = gen.GetCountFingerprint(mol).GetNonzeroElements()
    else:
        counts = gen.GetSparseCountFingerprint(mol).GetNonzeroElements()

    if cfg.counts:
        return {int(k): int(v) for k, v in counts.items()}
    return dict.fromkeys((int(k) for k in counts), 1)


def compute_dense(mol_or_smiles: Chem.Mol | str, cfg: FPConfig) -> np.ndarray:
    """Compute a folded fingerprint as a dense vector.

    Returns:
        ``uint8`` presence vector, or ``uint16`` count vector when
        ``cfg.counts``. Counts saturate at 65535, which no real molecule
        approaches.

    Raises:
        ValueError: If ``cfg.folded`` is False -- unfolded fingerprints have no
            dense form. Use :func:`compute` instead.
    """
    if not cfg.folded:
        raise ValueError("compute_dense requires folded=True; use compute() for unfolded")
    sparse = compute(mol_or_smiles, cfg)
    dtype = np.uint16 if cfg.counts else np.uint8
    vec = np.zeros(cfg.n_bits, dtype=dtype)
    if sparse:
        idx = np.fromiter(sparse.keys(), dtype=np.int64, count=len(sparse))
        val = np.fromiter(sparse.values(), dtype=np.int64, count=len(sparse))
        vec[idx] = np.minimum(val, np.iinfo(dtype).max)
    return vec


def compute_bitvect(mol_or_smiles: Chem.Mol | str, cfg: FPConfig):
    """Compute an RDKit ``ExplicitBitVect``, for fast bulk similarity searches.

    Only meaningful for folded binary configs, which is where the
    nearest-neighbour baseline needs the speed.
    """
    if not cfg.folded:
        raise ValueError("compute_bitvect requires folded=True")
    mol = _to_mol(mol_or_smiles)
    if mol is None:
        raise ValueError(f"could not parse SMILES: {mol_or_smiles!r}")
    return _generator(cfg).GetFingerprint(mol)


def equal(a: Sparse, b: Sparse) -> bool:
    """Exact fingerprint equality -- the oracle's definition of success.

    Both arguments must come from the same :class:`FPConfig`; dict equality
    compares identifiers and counts together, so for binary configs (all counts
    1) this reduces to set equality of the identifiers.
    """
    return a == b


def tanimoto(a: Sparse, b: Sparse) -> float:
    """Tanimoto similarity between two sparse fingerprints.

    Uses the min/max generalisation, which coincides with the usual
    intersection-over-union for binary fingerprints. Returns 1.0 for two empty
    fingerprints, which do compare equal.
    """
    if not a and not b:
        return 1.0
    keys = a.keys() | b.keys()
    num = sum(min(a.get(k, 0), b.get(k, 0)) for k in keys)
    den = sum(max(a.get(k, 0), b.get(k, 0)) for k in keys)
    return num / den if den else 0.0


def bulk_tanimoto(query, references) -> list[float]:
    """Bulk Tanimoto over RDKit bit vectors, for the baseline's similarity search."""
    return list(DataStructs.BulkTanimotoSimilarity(query, references))


def check_config_match(expected: FPConfig, found: FPConfig | dict | str, *, source: str) -> None:
    """Fail loudly if an artefact was built with a different fingerprint config.

    Args:
        expected: The config currently in use.
        found: The artefact's config, as an :class:`FPConfig`, its dict form, or
            just its ``fingerprint_id``.
        source: Human-readable origin of ``found``, used in the error message.

    Raises:
        FPConfigMismatch: If the configs differ.
    """
    if isinstance(found, str):
        if found != expected.fingerprint_id:
            raise FPConfigMismatch(
                f"{source} was built with fingerprint config {found}, "
                f"but {expected.fingerprint_id} ({expected.describe()}) is in use"
            )
        return

    found_cfg = FPConfig.from_dict(found) if isinstance(found, dict) else found
    if found_cfg != expected:
        raise FPConfigMismatch(
            f"{source} was built with {found_cfg.describe()} "
            f"[{found_cfg.fingerprint_id}], but {expected.describe()} "
            f"[{expected.fingerprint_id}] is in use"
        )
