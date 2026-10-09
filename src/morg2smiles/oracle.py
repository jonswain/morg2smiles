"""The oracle: does a generated SMILES actually reproduce the target fingerprint?

This is what makes the task worth attacking with an autonomous loop -- success
is decidable, not a proxy. Everything here is therefore deliberately strict and
deliberately boring: recompute the fingerprint under the *same* config and
compare exactly.

No exception escapes :func:`check`. An unparseable or absurd candidate is a
rejection, not a crash, because generation produces plenty of both and a crash
mid-evaluation would be indistinguishable from a bad model.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from rdkit import Chem, RDLogger

from .fingerprints import FPConfig, Sparse, compute, equal, tanimoto

__all__ = ["OracleResult", "check", "check_many", "canonicalize", "best_result"]

# Generation produces malformed SMILES by the thousand; RDKit's per-failure
# console spew would bury everything else.
RDLogger.DisableLog("rdApp.*")


@dataclass(frozen=True)
class OracleResult:
    """The verdict on one candidate SMILES.

    Attributes:
        smiles: The candidate as given.
        valid: Whether RDKit could parse and sanitise it.
        fp_match: Whether its fingerprint equals the target exactly. **This is
            the project's definition of success** -- it permits a different
            molecule from the reference, which is correct: the mapping really is
            many-to-one, and any molecule with the right fingerprint is a right
            answer.
        exact_structure: Whether it is the *reference* molecule, compared as
            canonical SMILES. Strictly stronger than ``fp_match`` and bounded
            above by fingerprint collisions, so it is a secondary metric.
        tanimoto: Similarity of candidate to target fingerprint. Not a success
            criterion -- it is the graceful-degradation signal that shows whether
            a near-miss was close or nonsense.
        canonical: Canonical SMILES of the candidate, or None if invalid.
    """

    smiles: str
    valid: bool
    fp_match: bool
    exact_structure: bool
    tanimoto: float
    canonical: str | None = None

    def __bool__(self) -> bool:
        """An oracle result is truthy when the fingerprint matches."""
        return self.fp_match


def canonicalize(smiles: str) -> str | None:
    """Canonical SMILES, or None if the input cannot be parsed or sanitised."""
    try:
        mol = Chem.MolFromSmiles(smiles)
    except Exception:
        return None
    if mol is None:
        return None
    try:
        return Chem.MolToSmiles(mol)
    except Exception:
        return None


def check(
    smiles: str,
    target_fp: Sparse,
    cfg: FPConfig,
    *,
    reference_smiles: str | None = None,
) -> OracleResult:
    """Judge one candidate SMILES against a target fingerprint.

    Args:
        smiles: The candidate.
        target_fp: Target fingerprint, computed under ``cfg``.
        cfg: The fingerprint config. Must be the one ``target_fp`` was built
            with; the caller is responsible for that, which is why datasets and
            checkpoints carry :attr:`FPConfig.fingerprint_id`.
        reference_smiles: The molecule the target came from, if known. Enables
            ``exact_structure``. It is compared canonically, so it need not
            already be canonical.

    Returns:
        An :class:`OracleResult`. Never raises.
    """
    try:
        mol = Chem.MolFromSmiles(smiles)
    except Exception:
        mol = None

    if mol is None:
        return OracleResult(smiles, False, False, False, 0.0, None)

    try:
        canonical = Chem.MolToSmiles(mol)
        candidate_fp = compute(mol, cfg)
    except Exception:
        return OracleResult(smiles, False, False, False, 0.0, None)

    fp_match = equal(candidate_fp, target_fp)
    exact_structure = False
    if reference_smiles is not None:
        ref_canonical = canonicalize(reference_smiles)
        exact_structure = ref_canonical is not None and canonical == ref_canonical

    return OracleResult(
        smiles=smiles,
        valid=True,
        fp_match=fp_match,
        exact_structure=exact_structure,
        tanimoto=tanimoto(candidate_fp, target_fp),
        canonical=canonical,
    )


def check_many(
    candidates: Iterable[str],
    target_fp: Sparse,
    cfg: FPConfig,
    *,
    reference_smiles: str | None = None,
    dedupe: bool = True,
) -> list[OracleResult]:
    """Judge a list of candidates against one target.

    Args:
        candidates: Candidate SMILES, in the order generated.
        target_fp: The target fingerprint.
        cfg: Fingerprint config.
        reference_smiles: The source molecule, if known.
        dedupe: Drop repeated candidates. Sampling returns duplicates
            constantly, and counting the same string twice would inflate
            recovery@k by letting one distinct guess occupy several of the k
            slots. Deduplication is on raw strings, before parsing, so the
            budget k counts distinct *guesses*.

    Returns:
        Results in input order, duplicates removed when ``dedupe``.
    """
    seen: set[str] = set()
    results = []
    for smiles in candidates:
        if dedupe:
            if smiles in seen:
                continue
            seen.add(smiles)
        results.append(check(smiles, target_fp, cfg, reference_smiles=reference_smiles))
    return results


def best_result(results: Sequence[OracleResult]) -> OracleResult | None:
    """The most successful result in a list, or None if the list is empty.

    Ranks a fingerprint match above everything, then prefers an exact structural
    match, then falls back to highest Tanimoto. This is the ordering
    :meth:`~morg2smiles.generate.Morg2Smiles.generate` uses to put verified hits
    first.
    """
    if not results:
        return None
    return max(results, key=lambda r: (r.fp_match, r.exact_structure, r.tanimoto))
