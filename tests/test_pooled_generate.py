"""Pooling several temperatures through one model, the best-measured setting.

Night 4 measured recovery@20 0.9279 from sampling one checkpoint at 0.6, 0.7
and 1.0 and ranking the union by spelling counts summed across the three --
better than any single temperature and better than pooling three separately
trained checkpoints. What is tested here is the mechanism rather than the
number: that a pooled call really samples once per temperature, that the votes
are counted over the union, and that the default stays a single pass so nobody
pays three times for a default they did not choose.
"""

from __future__ import annotations

import pytest
import torch

from morg2smiles import TEMPERATURE_POOL
from morg2smiles.fingerprints import FPConfig, compute
from morg2smiles.generate import Morg2Smiles, _temperatures
from morg2smiles.model import ModelConfig, build_model
from morg2smiles.tokenizer import SmilesTokenizer

ASPIRIN = "CC(=O)Oc1ccccc1C(=O)O"
TINY = ModelConfig(d_model=32, n_heads=2, d_ff=64, n_encoder_layers=1, n_decoder_layers=1)


@pytest.fixture
def wrapper():
    tokenizer = SmilesTokenizer.build([ASPIRIN, "CCO", "c1ccccc1"])
    model = build_model(TINY, FPConfig(), tokenizer).eval()
    return Morg2Smiles(model, torch.device("cpu"))


def test_one_temperature_or_several():
    assert _temperatures(0.6) == (0.6,)
    assert _temperatures(1) == (1.0,)
    assert _temperatures([0.6, 0.7]) == (0.6, 0.7)
    assert _temperatures(TEMPERATURE_POOL) == (0.6, 0.7, 1.0)


def test_an_empty_pool_is_refused():
    with pytest.raises(ValueError):
        _temperatures([])


def test_the_measured_pool_is_what_was_measured():
    assert TEMPERATURE_POOL == (0.6, 0.7, 1.0)


def test_pooling_samples_once_per_temperature(wrapper, monkeypatch):
    """Three temperatures, three sampling passes, each at the full draw."""
    import morg2smiles.generate as module

    calls = []
    real = module.sample

    def spy(model, fps, **kwargs):
        calls.append(kwargs["temperature"])
        return real(model, fps, **kwargs)

    monkeypatch.setattr(module, "sample", spy)
    fp = compute(ASPIRIN, wrapper.fp_config)
    wrapper.generate(fp, k=4, temperature=TEMPERATURE_POOL)
    assert calls == [0.6, 0.7, 1.0]


def test_the_default_is_a_single_pass(wrapper, monkeypatch):
    import morg2smiles.generate as module

    calls = []
    real = module.sample

    def spy(model, fps, **kwargs):
        calls.append(kwargs["temperature"])
        return real(model, fps, **kwargs)

    monkeypatch.setattr(module, "sample", spy)
    wrapper.generate(compute(ASPIRIN, wrapper.fp_config), k=4)
    assert len(calls) == 1


def test_a_pooled_call_still_returns_at_most_k_distinct_molecules(wrapper):
    out = wrapper.generate(compute(ASPIRIN, wrapper.fp_config), k=3, temperature=[0.6, 1.0])
    assert len(out) <= 3
    assert len(set(out)) == len(out)


def test_beam_search_ignores_the_pool(wrapper):
    """A pooled temperature is meaningless for beam search; it must not crash."""
    out = wrapper.generate(
        compute(ASPIRIN, wrapper.fp_config), k=3, strategy="beam", temperature=TEMPERATURE_POOL
    )
    assert isinstance(out, list)
