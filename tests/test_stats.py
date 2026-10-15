"""Tests for the paired error bars.

These underwrite every claim in docs/overnight-2026-10-15.md, where a p-value
decides whether a result is reported as a finding or as a null, so the exact
test is checked against hand-computable cases rather than only for plausibility.
"""

from __future__ import annotations

import pytest

from morg2smiles.stats import discordance, mcnemar_exact, paired_se


def test_no_disagreement_is_no_evidence():
    assert mcnemar_exact(0, 0) == 1.0
    assert paired_se(0, 0, 100) == 0.0


def test_an_even_split_is_the_null():
    # 10 disagreements split 5-5: every outcome is at least as likely.
    assert mcnemar_exact(5, 5) == 1.0


def test_fully_lopsided_splits_are_the_binomial_tail():
    # All n disagreements one way: 2 * (1/2)^n.
    assert mcnemar_exact(5, 0) == pytest.approx(2 * 0.5**5)
    assert mcnemar_exact(0, 8) == pytest.approx(2 * 0.5**8)


def test_one_from_lopsided_sums_two_terms():
    # 2 * P(X <= 1) for X ~ Binomial(6, 1/2) = 2 * (1 + 6) / 64.
    assert mcnemar_exact(5, 1) == pytest.approx(2 * 7 / 64)


def test_direction_does_not_change_the_p_value():
    assert mcnemar_exact(17, 4) == mcnemar_exact(4, 17)


def test_p_value_is_never_above_one():
    for b in range(6):
        for a in range(6):
            assert 0.0 <= mcnemar_exact(b, a) <= 1.0


def test_night_four_count_fingerprint_null():
    """The gap that night 4 reported as a real null, from its own discordance."""
    # count_fp_100k vs small_100k: binary wins 155 queries, counts win 137,
    # a gap of 0.92 points over 1,956 queries that is not a difference.
    assert mcnemar_exact(155, 137) == pytest.approx(0.320, abs=0.005)
    assert 100 * paired_se(155, 137, 1956) == pytest.approx(0.87, abs=0.01)


def test_paired_se_shrinks_with_agreement():
    many = paired_se(200, 200, 2000)
    few = paired_se(20, 20, 2000)
    assert few < many


def test_discordance_counts_each_direction():
    a = [True, True, False, False]
    b = [True, False, True, False]
    assert discordance(a, b) == (1, 1)


def test_discordance_rejects_misaligned_runs():
    with pytest.raises(ValueError, match="equal lengths"):
        discordance([True], [True, False])
