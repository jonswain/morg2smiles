"""Tests for the fingerprint module -- the project's single source of truth."""

from __future__ import annotations

import numpy as np
import pytest
from rdkit import Chem

from morg2smiles.fingerprints import (
    FPConfig,
    FPConfigMismatch,
    check_config_match,
    compute,
    compute_bitvect,
    compute_dense,
    equal,
    tanimoto,
)

MOLECULES = [
    "CC(=O)Oc1ccccc1C(=O)O",  # aspirin
    "CC(C)Cc1ccc(C(C)C(=O)O)cc1",  # ibuprofen
    "CN1C=NC2=C1C(=O)N(C)C(=O)N2C",  # caffeine
    "c1ccccc1",
    "CCO",
    "C1CCCCC1",
]

ALL_MODES = [
    FPConfig(),
    FPConfig(counts=True),
    FPConfig(folded=False),
    FPConfig(folded=False, counts=True),
    FPConfig(n_bits=1024),
    FPConfig(radius=3),
]


@pytest.mark.parametrize("cfg", ALL_MODES)
@pytest.mark.parametrize("smiles", MOLECULES)
def test_compute_is_deterministic(cfg, smiles):
    assert compute(smiles, cfg) == compute(smiles, cfg)


@pytest.mark.parametrize("cfg", ALL_MODES)
@pytest.mark.parametrize("smiles", MOLECULES)
def test_mol_and_smiles_inputs_agree(cfg, smiles):
    assert compute(smiles, cfg) == compute(Chem.MolFromSmiles(smiles), cfg)


@pytest.mark.parametrize("cfg", ALL_MODES)
@pytest.mark.parametrize("smiles", MOLECULES)
def test_binary_counts_are_all_one(cfg, smiles):
    fp = compute(smiles, cfg)
    if not cfg.counts:
        assert set(fp.values()) <= {1}
    else:
        assert all(v >= 1 for v in fp.values())


@pytest.mark.parametrize("smiles", MOLECULES)
def test_non_canonical_smiles_give_the_same_fingerprint(smiles):
    """The fingerprint is a property of the molecule, not of the string.

    This underpins SMILES randomisation: a random traversal must not change the
    input the model is conditioned on.
    """
    cfg = FPConfig()
    mol = Chem.MolFromSmiles(smiles)
    randomized = Chem.MolToSmiles(mol, canonical=False, doRandom=True)
    assert compute(randomized, cfg) == compute(smiles, cfg)


@pytest.mark.parametrize("smiles", MOLECULES)
def test_folding_never_adds_identifiers(smiles):
    """Folding can only merge environments, never create them."""
    folded = compute(smiles, FPConfig(n_bits=2048))
    unfolded = compute(smiles, FPConfig(folded=False))
    assert len(folded) <= len(unfolded)


@pytest.mark.parametrize("smiles", MOLECULES)
def test_dense_and_sparse_agree(smiles):
    cfg = FPConfig()
    dense = compute_dense(smiles, cfg)
    sparse = compute(smiles, cfg)
    assert dense.shape == (cfg.n_bits,)
    assert set(np.nonzero(dense)[0].tolist()) == set(sparse)


@pytest.mark.parametrize("smiles", MOLECULES)
def test_dense_counts_preserve_total_mass(smiles):
    cfg = FPConfig(counts=True)
    assert compute_dense(smiles, cfg).sum() == sum(compute(smiles, cfg).values())


def test_dense_rejects_unfolded():
    with pytest.raises(ValueError, match="folded"):
        compute_dense("CCO", FPConfig(folded=False))


def test_bitvect_matches_sparse():
    cfg = FPConfig()
    bv = compute_bitvect(MOLECULES[0], cfg)
    assert set(bv.GetOnBits()) == set(compute(MOLECULES[0], cfg))


def test_compute_raises_on_unparseable():
    with pytest.raises(ValueError, match="could not parse"):
        compute("this is not a molecule", FPConfig())


@pytest.mark.parametrize("cfg", ALL_MODES)
def test_equal_and_tanimoto_on_self(cfg):
    fp = compute(MOLECULES[0], cfg)
    assert equal(fp, compute(MOLECULES[0], cfg))
    assert tanimoto(fp, fp) == pytest.approx(1.0)


def test_tanimoto_bounds_and_symmetry():
    cfg = FPConfig()
    a, b = compute(MOLECULES[0], cfg), compute(MOLECULES[1], cfg)
    value = tanimoto(a, b)
    assert 0.0 <= value < 1.0
    assert value == pytest.approx(tanimoto(b, a))


def test_tanimoto_of_empty_fingerprints():
    assert tanimoto({}, {}) == 1.0
    assert tanimoto({}, {1: 1}) == 0.0


def test_different_molecules_differ():
    cfg = FPConfig()
    assert not equal(compute(MOLECULES[0], cfg), compute(MOLECULES[1], cfg))


# -- config identity and guards ------------------------------------------------
def test_fingerprint_id_is_stable_and_distinguishing():
    assert FPConfig().fingerprint_id == FPConfig().fingerprint_id
    ids = {cfg.fingerprint_id for cfg in ALL_MODES}
    assert len(ids) == len(ALL_MODES), "every distinct config needs a distinct id"


def test_vocab_size_tracks_folding():
    assert FPConfig(n_bits=2048).vocab_size == 2048
    assert FPConfig(folded=False).vocab_size > 2048


def test_round_trip_through_dict():
    cfg = FPConfig(radius=3, n_bits=1024, counts=True)
    assert FPConfig.from_dict(cfg.to_dict()) == cfg


def test_from_dict_rejects_unknown_fields():
    with pytest.raises(ValueError, match="unknown FPConfig fields"):
        FPConfig.from_dict({"radius": 2, "nonsense": True})


def test_check_config_match_accepts_identical():
    check_config_match(FPConfig(), FPConfig(), source="test")
    check_config_match(FPConfig(), FPConfig().to_dict(), source="test")
    check_config_match(FPConfig(), FPConfig().fingerprint_id, source="test")


@pytest.mark.parametrize(
    "other",
    [FPConfig(counts=True), FPConfig(n_bits=1024), FPConfig(radius=3), FPConfig(folded=False)],
)
def test_check_config_match_rejects_different(other):
    """A silent config mismatch would make every recovery number meaningless."""
    with pytest.raises(FPConfigMismatch):
        check_config_match(FPConfig(), other, source="shard")
    with pytest.raises(FPConfigMismatch):
        check_config_match(FPConfig(), other.fingerprint_id, source="shard")


def test_invalid_configs_are_rejected():
    with pytest.raises(ValueError):
        FPConfig(radius=-1)
    with pytest.raises(ValueError):
        FPConfig(n_bits=0)
