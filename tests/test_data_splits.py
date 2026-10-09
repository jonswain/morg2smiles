"""Tests for standardisation, splitting and the dataset.

Leakage between splits is the failure mode that would quietly invalidate every
number the project produces, so the split invariants are tested against the
real prepared shard whenever one exists.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest
import torch
from rdkit import Chem

from morg2smiles.data.dataset import (
    FingerprintDataset,
    collate,
    fp_to_indices,
    load_split,
    randomize_smiles,
)
from morg2smiles.data.prepare import StandardizeConfig, standardize
from morg2smiles.fingerprints import FPConfig, compute
from morg2smiles.tokenizer import SmilesTokenizer

SHARD = Path("data/shards/10k")
needs_shard = pytest.mark.skipif(
    not (SHARD / "meta.json").exists(),
    reason="run `python -m morg2smiles.data.prepare --subset 10k` first",
)

CFG = StandardizeConfig()


# -- standardisation -----------------------------------------------------------
def test_salt_is_stripped_to_largest_fragment():
    assert standardize("CCO.Cl", CFG)[0] == "CCO"
    assert standardize("CC(=O)Oc1ccccc1C(=O)[O-].[Na+]", CFG)[0] == "CC(=O)Oc1ccccc1C(=O)O"


def test_stereochemistry_is_stripped():
    """Morgan fingerprints are stereo-blind by default; targets must match."""
    out, reason = standardize("C[C@H](N)C(=O)O", CFG)
    assert reason == "ok"
    assert "@" not in out


def test_stereo_isomers_collapse_to_one_molecule():
    left = standardize("C[C@H](N)C(=O)O", CFG)[0]
    right = standardize("C[C@@H](N)C(=O)O", CFG)[0]
    assert left == right


def test_output_is_canonical():
    out = standardize("c1ccccc1", CFG)[0]
    assert out == Chem.MolToSmiles(Chem.MolFromSmiles(out))


@pytest.mark.parametrize(
    "smiles,reason",
    [
        ("garbage((", "unparseable"),
        ("C", "too_small"),
        ("[Fe+2]", "too_small"),
        ("c1ccccc1" + "C" * 200, "too_large"),
    ],
)
def test_drop_reasons_are_specific(smiles, reason):
    """Each rejection is tagged, so a surprising drop rate is diagnosable."""
    out, got = standardize(smiles, CFG)
    assert out is None
    assert got == reason


def test_disallowed_elements_are_dropped():
    out, reason = standardize("CC[Fe]CC", CFG)
    assert out is None and reason == "disallowed_element"


def test_token_limit_is_enforced():
    cfg = StandardizeConfig(max_tokens=10)
    assert standardize("CC(=O)Oc1ccccc1C(=O)O", cfg)[1] == "too_many_tokens"


def test_every_standardised_molecule_tokenizes_losslessly():
    for smiles in ["CC(=O)Oc1ccccc1C(=O)O", "CN1C=NC2=C1C(=O)N(C)C(=O)N2C", "CCO.Cl"]:
        out, reason = standardize(smiles, CFG)
        if reason == "ok":
            assert "".join(SmilesTokenizer.tokenize(out)) == out


# -- split integrity -----------------------------------------------------------
@needs_shard
def test_splits_do_not_overlap():
    """The invariant that makes held-out numbers mean anything."""
    splits = {name: set(load_split(SHARD, name)) for name in ("train", "valid", "test")}
    assert not splits["train"] & splits["valid"]
    assert not splits["train"] & splits["test"]
    assert not splits["valid"] & splits["test"]


@needs_shard
def test_no_duplicates_within_a_split():
    for name in ("train", "valid", "test"):
        members = load_split(SHARD, name)
        assert len(members) == len(set(members))


@needs_shard
def test_scaffold_splits_also_disjoint():
    splits = {
        name: set(load_split(SHARD, name, scaffold=True)) for name in ("train", "valid", "test")
    }
    assert not splits["train"] & splits["test"]
    assert not splits["train"] & splits["valid"]


@needs_shard
def test_every_stored_molecule_is_canonical_and_parses():
    for smiles in load_split(SHARD, "test"):
        mol = Chem.MolFromSmiles(smiles)
        assert mol is not None
        assert Chem.MolToSmiles(mol) == smiles


@needs_shard
def test_missing_split_raises_clearly():
    with pytest.raises(FileNotFoundError, match="prepare"):
        load_split(SHARD, "nonexistent")


# -- augmentation --------------------------------------------------------------
@pytest.mark.parametrize("smiles", ["CC(=O)Oc1ccccc1C(=O)O", "CN1C=NC2=C1C(=O)N(C)C(=O)N2C"])
def test_randomization_preserves_the_molecule(smiles):
    """Augmentation must change the string without changing the fingerprint."""
    cfg = FPConfig()
    target = compute(smiles, cfg)
    rng = random.Random(0)
    variants = {randomize_smiles(smiles, rng) for _ in range(25)}
    assert len(variants) > 1, "augmentation should actually vary the string"
    for variant in variants:
        assert Chem.MolFromSmiles(variant) is not None
        assert compute(variant, cfg) == target


def test_randomization_of_garbage_falls_back():
    assert randomize_smiles("not a molecule", random.Random(0)) == "not a molecule"


# -- dataset and collation -----------------------------------------------------
def test_fp_to_indices_folded_uses_bit_indices():
    cfg = FPConfig()
    fp = compute("CCO", cfg)
    indices, counts = fp_to_indices(fp, cfg)
    assert sorted(indices) == sorted(fp)
    assert all(0 <= i < cfg.n_bits for i in indices)
    assert set(counts) == {1}


def test_fp_to_indices_unfolded_hashes_into_vocab():
    cfg = FPConfig(folded=False)
    indices, _ = fp_to_indices(compute("CC(=O)Oc1ccccc1C(=O)O", cfg), cfg)
    assert all(0 <= i < cfg.vocab_size for i in indices)


def test_fp_to_indices_clamps_counts():
    from morg2smiles.data.dataset import MAX_COUNT

    cfg = FPConfig(counts=True)
    _, counts = fp_to_indices(compute("C" * 40, cfg), cfg)
    assert max(counts) <= MAX_COUNT


def test_dataset_item_shapes():
    smiles = ["CC(=O)Oc1ccccc1C(=O)O", "CCO"]
    cfg = FPConfig()
    tok = SmilesTokenizer.build(smiles)
    item = FingerprintDataset(smiles, cfg, tok)[0]
    assert item["fp_indices"].shape == item["fp_counts"].shape
    assert item["tokens"][0] == tok.bos_id
    assert item["tokens"][-1] == tok.eos_id


def test_dataset_conditions_on_the_canonical_fingerprint():
    """Randomised targets must not perturb the model's input."""
    smiles = ["CC(=O)Oc1ccccc1C(=O)O"]
    cfg = FPConfig()
    tok = SmilesTokenizer.build(smiles)
    plain = FingerprintDataset(smiles, cfg, tok, randomize=False)[0]
    for epoch in range(5):
        augmented = FingerprintDataset(smiles, cfg, tok, randomize=True)
        augmented.set_epoch(epoch)
        item = augmented[0]
        assert set(item["fp_indices"].tolist()) == set(plain["fp_indices"].tolist())


def test_set_epoch_changes_the_target():
    smiles = ["CC(=O)Oc1ccccc1C(=O)O"] * 1
    cfg = FPConfig()
    tok = SmilesTokenizer.build(["CC(=O)Oc1ccccc1C(=O)O"])
    ds = FingerprintDataset(smiles, cfg, tok, randomize=True)
    seen = set()
    for epoch in range(10):
        ds.set_epoch(epoch)
        seen.add(tuple(ds[0]["tokens"].tolist()))
    assert len(seen) > 1, "each epoch should present a different traversal"


def test_collate_pads_and_masks():
    smiles = ["CC(=O)Oc1ccccc1C(=O)O", "CCO", "c1ccccc1"]
    cfg = FPConfig()
    tok = SmilesTokenizer.build(smiles)
    ds = FingerprintDataset(smiles, cfg, tok)
    batch = collate([ds[i] for i in range(len(smiles))], tok.pad_id)

    assert batch["fp_indices"].shape == batch["fp_mask"].shape
    assert batch["tokens"].shape[0] == len(smiles)
    # The mask must select exactly the real bits of each molecule.
    for i, s in enumerate(smiles):
        assert int(batch["fp_mask"][i].sum()) == len(compute(s, cfg))
    assert batch["fp_mask"].dtype == torch.bool
    assert batch["token_mask"].dtype == torch.bool


def test_collate_pads_to_batch_maximum_not_global():
    """Dynamic padding is what keeps the set encoder cheap."""
    smiles = ["CCO", "CC"]
    cfg = FPConfig()
    tok = SmilesTokenizer.build(smiles)
    ds = FingerprintDataset(smiles, cfg, tok)
    batch = collate([ds[0], ds[1]], tok.pad_id)
    assert batch["fp_indices"].shape[1] < cfg.n_bits
