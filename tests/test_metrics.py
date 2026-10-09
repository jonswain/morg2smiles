"""Tests for the metrics, with emphasis on the slicing.

The ``fp_unseen`` slice is what separates reconstruction from memorisation, so
most of these tests check that it is computed and reported honestly rather than
quietly falling back to the flattering number.
"""

from __future__ import annotations

import pytest

from morg2smiles.metrics import (
    QueryOutcome,
    evaluate,
    format_report,
    recovery_at_k,
    structure_accuracy_at_k,
)
from morg2smiles.oracle import OracleResult


def result(fp_match: bool, *, exact: bool = False, tanimoto: float = 0.5, smiles: str = "CCO"):
    return OracleResult(
        smiles=smiles,
        valid=True,
        fp_match=fp_match,
        exact_structure=exact,
        tanimoto=1.0 if fp_match else tanimoto,
        canonical=smiles,
    )


INVALID = OracleResult("C((", valid=False, fp_match=False, exact_structure=False, tanimoto=0.0)


# -- recovery@k ----------------------------------------------------------------
def test_recovery_at_k_counts_a_hit_anywhere_in_the_first_k():
    outcome = QueryOutcome(results=[result(False), result(False), result(True)])
    assert recovery_at_k([outcome], 1) == 0.0
    assert recovery_at_k([outcome], 2) == 0.0
    assert recovery_at_k([outcome], 3) == 1.0
    assert recovery_at_k([outcome], 100) == 1.0


def test_recovery_at_k_is_monotonic_in_k():
    outcomes = [
        QueryOutcome(results=[result(False)] * 5 + [result(True)]),
        QueryOutcome(results=[result(True)]),
        QueryOutcome(results=[result(False)] * 10),
    ]
    values = [recovery_at_k(outcomes, k) for k in (1, 2, 5, 10, 20)]
    assert values == sorted(values)


def test_queries_that_generated_nothing_count_as_failures():
    """Failing to generate is a failure, not an exclusion from the denominator."""
    outcomes = [QueryOutcome(results=[result(True)]), QueryOutcome(results=[])]
    assert recovery_at_k(outcomes, 20) == 0.5


def test_recovery_on_empty_input():
    assert recovery_at_k([], 20) == 0.0
    assert structure_accuracy_at_k([], 20) == 0.0


def test_structure_accuracy_is_bounded_by_recovery():
    outcomes = [
        QueryOutcome(results=[result(True, exact=False)]),
        QueryOutcome(results=[result(True, exact=True)]),
    ]
    assert structure_accuracy_at_k(outcomes, 20) == 0.5
    assert recovery_at_k(outcomes, 20) == 1.0


def test_hit_rank():
    assert QueryOutcome(results=[result(False), result(True)]).hit_rank() == 1
    assert QueryOutcome(results=[result(True)]).hit_rank() == 0
    assert QueryOutcome(results=[result(False)]).hit_rank() is None
    assert QueryOutcome(results=[]).hit_rank() is None


# -- slicing -------------------------------------------------------------------
def test_slices_are_reported_separately():
    outcomes = [
        QueryOutcome(results=[result(True)], fp_unseen=False),  # memorisable hit
        QueryOutcome(results=[result(True)], fp_unseen=False),
        QueryOutcome(results=[result(False)], fp_unseen=True),  # genuine miss
    ]
    report = evaluate(outcomes, ks=[1])
    assert report["slices"]["all"]["recovery_at_k"]["1"] == pytest.approx(2 / 3)
    assert report["slices"]["fp_unseen"]["recovery_at_k"]["1"] == 0.0


def test_primary_metric_is_the_unseen_slice():
    """A model that only memorises must score zero on the headline number."""
    outcomes = [QueryOutcome(results=[result(True)], fp_unseen=False) for _ in range(10)]
    report = evaluate(outcomes, ks=[1, 5])
    assert report["slices"]["all"]["recovery_at_k"]["5"] == 1.0
    assert report["primary_metric"] == 0.0
    assert "fp_unseen" in report["primary_metric_name"]


def test_primary_metric_uses_the_largest_k():
    outcomes = [QueryOutcome(results=[result(False), result(True)], fp_unseen=True)]
    report = evaluate(outcomes, ks=[1, 20])
    assert report["primary_metric_name"] == "recovery@20 (fp_unseen)"
    assert report["primary_metric"] == 1.0


def test_fp_unseen_fraction_is_reported():
    outcomes = [
        QueryOutcome(results=[result(True)], fp_unseen=True),
        QueryOutcome(results=[result(True)], fp_unseen=False),
    ]
    assert evaluate(outcomes, ks=[1])["fp_unseen_fraction"] == 0.5


def test_empty_slice_does_not_crash():
    outcomes = [QueryOutcome(results=[result(True)], fp_unseen=False)]
    report = evaluate(outcomes, ks=[1])
    assert report["slices"]["fp_unseen"]["n_queries"] == 0
    assert report["primary_metric"] == 0.0
    assert isinstance(format_report(report), str)


def test_unknown_slice_rejected():
    with pytest.raises(ValueError, match="unknown slice"):
        from morg2smiles.metrics import _slice

        _slice([], "nonsense")


# -- auxiliary metrics ---------------------------------------------------------
def test_validity_and_diversity():
    outcomes = [
        QueryOutcome(
            results=[result(False, smiles="CCO"), result(False, smiles="CC"), INVALID],
            fp_unseen=True,
        )
    ]
    metrics = evaluate(outcomes, ks=[1])["slices"]["fp_unseen"]
    assert metrics["validity"] == pytest.approx(2 / 3)
    assert metrics["unique_valid_per_query"] == pytest.approx(2.0)
    assert metrics["mean_candidates_per_query"] == 3


def test_mean_best_tanimoto_tracks_near_misses():
    outcomes = [QueryOutcome(results=[result(False, tanimoto=0.3), result(False, tanimoto=0.8)])]
    assert evaluate(outcomes, ks=[1])["slices"]["all"]["mean_best_tanimoto"] == pytest.approx(0.8)


def test_mean_hit_rank_ignores_misses():
    outcomes = [
        QueryOutcome(results=[result(False), result(True)]),
        QueryOutcome(results=[result(False)]),
    ]
    assert evaluate(outcomes, ks=[1])["slices"]["all"]["mean_hit_rank"] == 1.0


def test_throughput_reported_when_timed():
    outcomes = [QueryOutcome(results=[result(True)], fp_unseen=True)]
    report = evaluate(outcomes, ks=[1], elapsed_seconds=2.0)
    assert report["queries_per_second"] == 0.5


def test_report_is_json_serialisable():
    import json

    outcomes = [QueryOutcome(results=[result(True)], fp_unseen=True)]
    json.dumps(evaluate(outcomes, ks=[1, 5], elapsed_seconds=1.0))


def test_format_report_mentions_both_slices():
    outcomes = [
        QueryOutcome(results=[result(True)], fp_unseen=True),
        QueryOutcome(results=[result(False)], fp_unseen=False),
    ]
    text = format_report(evaluate(outcomes, ks=[1]))
    assert "all" in text and "fp_unseen" in text
