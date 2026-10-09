"""Tests for the SMILES tokenizer.

The central invariant is losslessness: if tokenization mangles a string, the
model trains on a target the oracle will never accept, and the failure looks
like a modelling problem rather than a plumbing one.
"""

from __future__ import annotations

import pytest
from rdkit import Chem

from morg2smiles.tokenizer import SmilesTokenizer, TokenizationError

TRICKY = [
    "CC(=O)Oc1ccccc1C(=O)O",
    "CN1C=NC2=C1C(=O)N(C)C(=O)N2C",
    "c1ccc2[nH]ccc2c1",  # bracket aromatic atom
    "C1CC%10CCC%10C1",  # two-digit ring closure
    "[Si](Cl)(Br)F",  # two-letter atoms and a bracket atom
    "C/C=C/C",  # directional bonds
    "C[C@@H](N)C(=O)O",  # stereo bracket atoms
    "[Na+].[Cl-]",  # dot-disconnected, charged
    "c1ccc(-c2ccccc2)cc1",  # explicit single bond
    "C#N",
    "O=S(=O)(N)c1ccccc1",
    "[13CH4]",  # isotope
    "C%99CC%99",  # high ring closure
    "*CC",  # wildcard atom
]


@pytest.mark.parametrize("smiles", TRICKY)
def test_tokenize_is_lossless(smiles):
    assert "".join(SmilesTokenizer.tokenize(smiles)) == smiles


@pytest.mark.parametrize("smiles", TRICKY)
def test_encode_decode_round_trip(smiles):
    tok = SmilesTokenizer.build(TRICKY)
    assert tok.decode(tok.encode(smiles)) == smiles


def test_two_letter_atoms_are_single_tokens():
    tokens = SmilesTokenizer.tokenize("ClBrCNOSPFI")
    assert tokens[:2] == ["Cl", "Br"]
    assert "l" not in tokens and "r" not in tokens


def test_two_digit_ring_closures_are_single_tokens():
    assert "%10" in SmilesTokenizer.tokenize("C1CC%10CCC%10C1")


def test_bracket_atoms_are_single_tokens():
    assert SmilesTokenizer.tokenize("[C@@H]") == ["[C@@H]"]
    assert SmilesTokenizer.tokenize("[13CH4]") == ["[13CH4]"]


def test_lossy_input_raises():
    """An unsupported character must fail loudly, not vanish."""
    with pytest.raises(TokenizationError):
        SmilesTokenizer.tokenize("CCO wait what")


def test_special_tokens_come_first_and_are_distinct():
    tok = SmilesTokenizer.build(TRICKY)
    assert tok.itos[:4] == ["<pad>", "<bos>", "<eos>", "<unk>"]
    assert tok.pad_id == 0
    assert len({tok.pad_id, tok.bos_id, tok.eos_id, tok.unk_id}) == 4


def test_encode_adds_bos_and_eos():
    tok = SmilesTokenizer.build(["CCO"])
    ids = tok.encode("CCO")
    assert ids[0] == tok.bos_id and ids[-1] == tok.eos_id
    assert len(ids) == 5
    assert tok.encode("CCO", add_special=False) == ids[1:-1]


def test_decode_stops_at_eos_and_drops_padding():
    tok = SmilesTokenizer.build(["CCO"])
    ids = tok.encode("CCO") + [tok.pad_id] * 5
    assert tok.decode(ids) == "CCO"


def test_decode_skips_unknown_tokens():
    tok = SmilesTokenizer.build(["CCO"])
    assert tok.decode([tok.bos_id, tok.unk_id, tok.stoi["C"], tok.eos_id]) == "C"


def test_unseen_token_maps_to_unk():
    tok = SmilesTokenizer.build(["CCO"])
    assert tok.unk_id in tok.encode("CCBr")


def test_min_count_prunes_rare_tokens():
    tok = SmilesTokenizer.build(["CCO", "CCO", "CCBr"], min_count=2)
    assert "Br" not in tok.stoi
    assert "C" in tok.stoi


def test_save_and_load_round_trip(tmp_path):
    tok = SmilesTokenizer.build(TRICKY)
    path = tmp_path / "vocab.json"
    tok.save(path)
    loaded = SmilesTokenizer.load(path)
    assert loaded.itos == tok.itos
    assert loaded.encode(TRICKY[0]) == tok.encode(TRICKY[0])


def test_dict_round_trip():
    tok = SmilesTokenizer.build(TRICKY)
    assert SmilesTokenizer.from_dict(tok.to_dict()).itos == tok.itos


def test_duplicate_tokens_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        SmilesTokenizer(["C", "C"])


def test_randomized_rdkit_smiles_all_tokenize():
    """Augmentation must never produce a string the tokenizer cannot handle."""
    mol = Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O")
    for _ in range(25):
        variant = Chem.MolToSmiles(mol, canonical=False, doRandom=True)
        assert "".join(SmilesTokenizer.tokenize(variant)) == variant
