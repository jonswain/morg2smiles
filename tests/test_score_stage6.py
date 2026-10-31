"""The stage 6 scorer: exponents read from a matched pair of protocol dumps.

The arithmetic worth testing is `pair_exponent`, because it is the whole reason
stage 6 exists. Stage 5b fits a run's own in-training trace, and night 8 showed
those traces can disagree in *direction* with the held-out protocol; stage 6
replaces that with two points on one protocol. If the two-point fit is wrong,
every exponent in night 9's report is wrong and nothing else catches it.

The other thing under test is that `against` reports distance rather than a
verdict. These quantities were deliberately registered as targets and not as
intervals -- the error bar on an exponent from a single pair has never been
measured here -- so the scorer must not imply a significance it cannot compute.
"""

from __future__ import annotations

import math

from scripts.score_stage6 import LONG_STEPS, SHORT_STEPS, against, pair_exponent, rec_at


def report(band: str, **rec: float) -> dict:
    return {
        "bands": {band: {"n_queries": 100, "recovery_at_k": {str(k): v for k, v in rec.items()}}}
    }


class TestPairExponent:
    """c in  1 - rec = A * steps^-c,  from exactly two points."""

    def test_a_known_exponent_is_recovered(self):
        # Construct a pair that sits exactly on c = 1.0: the deficit must fall
        # by the same factor the steps rise by.
        ratio = LONG_STEPS / SHORT_STEPS
        short, long_ = report("all", **{"60": 0.5}), report("all", **{"60": 1 - 0.5 / ratio})
        assert abs(pair_exponent(short, long_, "all", 60) - 1.0) < 1e-12

    def test_no_improvement_is_a_zero_exponent(self):
        short, long_ = report("all", **{"60": 0.4}), report("all", **{"60": 0.4})
        assert abs(pair_exponent(short, long_, "all", 60)) < 1e-12

    def test_a_larger_gain_gives_a_larger_exponent(self):
        short = report("all", **{"60": 0.2})
        small = pair_exponent(short, report("all", **{"60": 0.5}), "all", 60)
        large = pair_exponent(short, report("all", **{"60": 0.9}), "all", 60)
        assert large > small > 0

    def test_night_nines_published_50plus_exponent(self):
        # The number that appears in docs/overnight-2026-10-30.md, so that the
        # report and the code cannot drift apart silently.
        short, long_ = report("all", **{"60": 0.2251}), report("all", **{"60": 0.7402})
        assert abs(pair_exponent(short, long_, "all", 60) - 0.682) < 5e-4

    def test_a_saturated_point_is_none_not_a_domain_error(self):
        # rec == 1.0 makes log(0) -- the deficit form's one singularity, and a
        # real possibility now that bands reach 0.9756.
        short, long_ = report("all", **{"60": 0.5}), report("all", **{"60": 1.0})
        assert pair_exponent(short, long_, "all", 60) is None

    def test_an_absent_band_is_none(self):
        short, long_ = report("all", **{"60": 0.5}), report("50+", **{"60": 0.7})
        assert pair_exponent(short, long_, "50+", 60) is None


class TestRecAt:
    def test_reads_the_requested_k(self):
        r = report("all", **{"20": 0.6, "60": 0.8})
        assert rec_at(r, "all", 20) == 0.6
        assert rec_at(r, "all", 60) == 0.8

    def test_absent_band_is_none(self):
        assert rec_at(report("all", **{"60": 0.8}), "50+", 60) is None


class TestAgainst:
    """Distance from a target, never a significance claim."""

    def test_inside(self):
        assert against(0.35, 0.32, 0.38) == "inside"

    def test_below_reports_the_distance(self):
        assert against(1.322, 1.52, 1.68) == "below by 0.198"

    def test_above_reports_the_distance(self):
        assert against(0.401, 0.320, 0.380) == "above by 0.021"

    def test_the_bounds_are_inside(self):
        assert against(0.320, 0.320, 0.380) == "inside"
        assert against(0.380, 0.320, 0.380) == "inside"

    def test_it_never_says_significant(self):
        # The registration is a target, not an interval with a noise floor.
        for m in (0.1, 0.35, 9.9):
            assert "signific" not in against(m, 0.32, 0.38)


def test_the_passes_doublings_match_the_registration():
    from scripts.score_stage6 import DOUBLINGS, LONG_PASSES, SHORT_PASSES

    assert abs(DOUBLINGS - math.log2(LONG_PASSES / SHORT_PASSES)) < 1e-12
    assert abs(DOUBLINGS - 2.3115) < 5e-4
