"""The product default and the protocol default must not drift into each other.

Night 4 measured that sampling at 0.6 beats 1.0 by +1.99 points of recovery@20,
so user-facing generation uses 0.6. The evaluation path deliberately stays at
1.0, because every number this project has published was measured there and
re-scoring an old checkpoint has to reproduce it. The two being different is the
point, and a tidy-up that unified them would silently invalidate the comparison
tables, so it is pinned here.
"""

from __future__ import annotations

import inspect

from morg2smiles.defaults import DEFAULT_TEMPERATURE
from morg2smiles.evaluation import generate_outcomes
from morg2smiles.generate import Morg2Smiles, sample


def default_of(fn, name: str):
    return inspect.signature(fn).parameters[name].default


def test_product_default_is_the_measured_optimum():
    assert DEFAULT_TEMPERATURE == 0.6


def test_user_facing_generate_uses_the_product_default():
    assert default_of(Morg2Smiles.generate, "temperature") == DEFAULT_TEMPERATURE


def test_the_evaluation_path_stays_at_one():
    assert default_of(generate_outcomes, "temperature") == 1.0
    assert default_of(sample, "temperature") == 1.0


def test_the_two_defaults_are_deliberately_different():
    assert default_of(generate_outcomes, "temperature") != DEFAULT_TEMPERATURE
