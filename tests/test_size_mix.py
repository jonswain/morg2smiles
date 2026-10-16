"""The size-weighted sampler must change the mix and nothing else.

Night 4 found that all three ChEMBL shards hold the same share of large
molecules, so the training mix is the only training-side lever on the size
cliff. The two things that make the resulting comparison readable are tested
here: the weights do what they claim, and weighting leaves the step schedule
alone -- an epoch still draws one sample per molecule, so a weighted run stays
step-for-step comparable with the unweighted baseline it is measured against.
"""

from __future__ import annotations

import pytest
import torch
from torch.utils.data import WeightedRandomSampler

from morg2smiles.data.dataset import size_weights
from morg2smiles.train import TrainConfig

# Heavy-atom counts: 2, 3, 9, 14, 20. Chosen so a threshold can split them.
SMILES = ["CC", "CCC", "c1ccccc1O", "CC(=O)Oc1ccccc1C(=O)O", "c1ccc2cc3ccccc3cc2c1"]


def test_weights_split_on_the_threshold():
    weights, summary = size_weights(SMILES, 10, 3.0)
    assert weights == [1.0, 1.0, 1.0, 3.0, 3.0]
    assert summary["share_at_or_above_threshold"] == pytest.approx(2 / 5)
    # 6 of 9 units of weight land on the two large molecules.
    assert summary["weighted_share_at_or_above_threshold"] == pytest.approx(6 / 9)


def test_a_factor_of_one_is_the_identity():
    weights, summary = size_weights(SMILES, 10, 1.0)
    assert weights == [1.0] * 5
    assert summary["weighted_share_at_or_above_threshold"] == pytest.approx(
        summary["share_at_or_above_threshold"]
    )


def test_band_shares_sum_to_one_and_shift_upwards():
    # Spans the real bands: 14, 20 and 32 heavy atoms.
    spread = ["c1ccc2cc3ccccc3cc2c1", "c1ccc2cc3cc4ccccc4cc3cc2c1", "C" * 32]
    _, summary = size_weights(spread, 30, 3.0)
    bands = summary["bands"]
    assert sum(b["share"] for b in bands.values()) == pytest.approx(1.0)
    assert sum(b["weighted_share"] for b in bands.values()) == pytest.approx(1.0)
    # The small bands lose mass to the large ones; none of it is created.
    assert bands["0-24"]["weighted_share"] < bands["0-24"]["share"]
    assert bands["30-34"]["weighted_share"] > bands["30-34"]["share"]


def test_a_nonsense_factor_is_refused():
    with pytest.raises(ValueError):
        size_weights(SMILES, 10, 0.0)


def test_unparseable_smiles_count_as_small_rather_than_crashing():
    weights, _ = size_weights(["not a molecule", "CC(=O)Oc1ccccc1C(=O)O"], 10, 2.0)
    assert weights == [1.0, 2.0]


def test_weighting_does_not_change_the_epoch_length():
    """The schedule has to survive, or the comparison is confounded by compute."""
    weights, _ = size_weights(SMILES, 10, 3.0)
    sampler = WeightedRandomSampler(
        weights,
        num_samples=len(SMILES),
        replacement=True,
        generator=torch.Generator().manual_seed(0),
    )
    assert len(list(sampler)) == len(SMILES)


def test_the_sampler_actually_favours_large_molecules():
    weights, _ = size_weights(SMILES, 10, 3.0)
    sampler = WeightedRandomSampler(
        weights, num_samples=5000, replacement=True, generator=torch.Generator().manual_seed(0)
    )
    drawn = list(sampler)
    large = sum(1 for i in drawn if i >= 3) / len(drawn)
    assert large == pytest.approx(6 / 9, abs=0.03)


def test_the_mix_is_off_by_default():
    cfg = TrainConfig()
    assert cfg.size_weight_threshold is None
    assert cfg.size_weight_factor == 1.0
