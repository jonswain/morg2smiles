"""Tests for the oracle.

The oracle is the project's definition of truth, so these tests matter more
than most: a lenient oracle inflates every number in the leaderboard, and a
crashing one makes a model look broken when generation is merely noisy.
"""

from __future__ import annotations

import pytest

from morg2smiles.fingerprints import FPConfig, compute
from morg2smiles.oracle import best_result, canonicalize, check, check_many

MOLECULES = [
    "CC(=O)Oc1ccccc1C(=O)O",
    "CC(C)Cc1ccc(C(C)C(=O)O)cc1",
    "CN1C=NC2=C1C(=O)N(C)C(=O)N2C",
    "CCO",
    "c1ccccc1",
]

MODES = [FPConfig(), FPConfig(counts=True), FPConfig(folded=False), FPConfig(n_bits=1024)]


@pytest.mark.parametrize("cfg", MODES)
@pytest.mark.parametrize("smiles", MOLECULES)
def test_molecule_matches_its_own_fingerprint(cfg, smiles):
    """The invariant everything else rests on."""
    result = check(smiles, compute(smiles, cfg), cfg, reference_smiles=smiles)
    assert result.valid
    assert result.fp_match
    assert result.exact_structure
    assert result.tanimoto == pytest.approx(1.0)
    assert bool(result) is True


@pytest.mark.parametrize("smiles", MOLECULES)
def test_non_canonical_form_still_matches(smiles):
    """A correct answer written differently is still a correct answer."""
    from rdkit import Chem

    cfg = FPConfig()
    mol = Chem.MolFromSmiles(smiles)
    scrambled = Chem.MolToSmiles(mol, canonical=False, doRandom=True)
    result = check(scrambled, compute(smiles, cfg), cfg, reference_smiles=smiles)
    assert result.fp_match
    assert result.exact_structure, "exact_structure must compare canonically, not literally"


def test_different_molecule_is_rejected():
    cfg = FPConfig()
    result = check("CCO", compute(MOLECULES[0], cfg), cfg, reference_smiles=MOLECULES[0])
    assert result.valid
    assert not result.fp_match
    assert not result.exact_structure
    assert result.tanimoto < 1.0
    assert bool(result) is False


@pytest.mark.parametrize(
    "bad",
    [
        "not a molecule",
        "C(((",
        "c1ccccc",  # unclosed ring
        "[Xx]",  # nonsense element
        "1234",
        "))((",
        "C1CC",  # unclosed ring bond
    ],
)
def test_invalid_candidates_are_rejected_without_raising(bad):
    """Generation emits malformed strings constantly; none may crash evaluation."""
    cfg = FPConfig()
    result = check(bad, compute("CCO", cfg), cfg)
    assert not result.valid
    assert not result.fp_match
    assert result.canonical is None


@pytest.mark.parametrize("odd", ["", "C" * 500])
def test_parseable_but_useless_candidates_are_handled(odd):
    """An empty molecule and a 500-carbon chain both parse; neither may crash.

    They are wrong rather than malformed, so the oracle accepts them as valid
    and simply reports no fingerprint match.
    """
    cfg = FPConfig()
    result = check(odd, compute("CCO", cfg), cfg)
    assert result.valid
    assert not result.fp_match


def test_unsanitisable_molecule_is_rejected():
    """Parseable-looking but chemically invalid input must not raise."""
    cfg = FPConfig()
    result = check("c1ccc1", compute("CCO", cfg), cfg)  # 4-membered aromatic ring
    assert not result.fp_match


def test_exact_structure_requires_a_reference():
    cfg = FPConfig()
    result = check(MOLECULES[0], compute(MOLECULES[0], cfg), cfg)
    assert result.fp_match
    assert not result.exact_structure, "without a reference there is nothing to compare against"


def test_tanimoto_is_reported_for_near_misses():
    cfg = FPConfig()
    target = compute("CC(=O)Oc1ccccc1C(=O)O", cfg)
    result = check("CC(=O)Oc1ccccc1C(=O)N", cfg=cfg, target_fp=target)
    assert result.valid and not result.fp_match
    assert 0.3 < result.tanimoto < 1.0, "a one-atom change should score high but not perfect"


# -- check_many ----------------------------------------------------------------
def test_check_many_preserves_order():
    cfg = FPConfig()
    target = compute(MOLECULES[0], cfg)
    results = check_many(["CCO", MOLECULES[0], "c1ccccc1"], target, cfg)
    assert [r.smiles for r in results] == ["CCO", MOLECULES[0], "c1ccccc1"]
    assert [r.fp_match for r in results] == [False, True, False]


def test_check_many_deduplicates_by_default():
    """One guess repeated must not occupy several of the k slots."""
    cfg = FPConfig()
    target = compute("CCO", cfg)
    results = check_many(["CCO"] * 5 + ["CC"], target, cfg)
    assert len(results) == 2


def test_check_many_can_keep_duplicates():
    cfg = FPConfig()
    results = check_many(["CCO"] * 3, compute("CCO", cfg), cfg, dedupe=False)
    assert len(results) == 3


def test_check_many_on_empty_input():
    assert check_many([], compute("CCO", FPConfig()), FPConfig()) == []


# -- ranking -------------------------------------------------------------------
def test_best_result_prefers_fingerprint_match():
    cfg = FPConfig()
    target = compute(MOLECULES[0], cfg)
    results = check_many(
        ["CCO", "CC(=O)Oc1ccccc1C(=O)N", MOLECULES[0]], target, cfg, reference_smiles=MOLECULES[0]
    )
    best = best_result(results)
    assert best is not None and best.fp_match


def test_best_result_falls_back_to_tanimoto():
    cfg = FPConfig()
    target = compute(MOLECULES[0], cfg)
    results = check_many(["CCO", "CC(=O)Oc1ccccc1C(=O)N"], target, cfg)
    best = best_result(results)
    assert best is not None and not best.fp_match
    assert best.smiles == "CC(=O)Oc1ccccc1C(=O)N"


def test_best_result_on_empty_list():
    assert best_result([]) is None


# -- canonicalize --------------------------------------------------------------
def test_canonicalize_is_idempotent():
    once = canonicalize("c1ccccc1")
    assert once is not None
    assert canonicalize(once) == once


def test_canonicalize_returns_none_on_garbage():
    assert canonicalize("not a molecule") is None
    assert canonicalize("") == ""  # empty SMILES is a valid empty molecule
