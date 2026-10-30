"""The scorer for the final run's pre-registration.

`score_job4.py` is the one script in this project whose output is a verdict
rather than a number, so the two things worth testing are that a verdict lands
on the right branch -- including at the interval's own edges, which is where a
"miss low by 0.11 points" lives -- and that it refuses to read a registration
against a band table measured in a different convention. The second is the
guard: four of this project's withdrawn claims came from comparing a rec@60 in
one convention against a rec@60 in another, and entry 20 of the retractions
ledger is that error specifically.
"""

from __future__ import annotations

import json

from scripts.score_job4 import binomial_se, verdict


class TestVerdict:
    """Branches, and the edges between them."""

    def test_inside_is_a_hit(self):
        assert verdict(0.70, 0.63, 0.75) == ("HIT", 0.0)

    def test_below_is_a_miss_low_with_the_distance_in_points(self):
        branch, miss = verdict(0.6289, 0.6310, 0.6912)
        assert branch == "MISS LOW"
        assert miss < 0
        assert abs(miss - (-0.21)) < 1e-9

    def test_above_is_a_miss_high(self):
        branch, miss = verdict(0.72, 0.63, 0.6912)
        assert branch == "MISS HIGH"
        assert abs(miss - 2.88) < 1e-9

    def test_the_bounds_themselves_are_inside(self):
        # A closed interval. Night 8's result landed 0.11 points under a floor
        # and was scored a miss, so which side the boundary falls on is a
        # decision this project has already had to make once.
        assert verdict(0.6310, 0.6310, 0.6912)[0] == "HIT"
        assert verdict(0.6912, 0.6310, 0.6912)[0] == "HIT"


class TestBinomialSE:
    def test_se_shrinks_with_n(self):
        assert binomial_se(0.5, 893) < binomial_se(0.5, 203)

    def test_zero_n_is_nan_not_a_crash(self):
        assert binomial_se(0.5, 0) != binomial_se(0.5, 0)  # nan


def write(path, payload):
    path.write_text(json.dumps(payload))
    return path


def registration(tmp_path, *, metric="recovery", k=60):
    return write(
        tmp_path / f"reg_{metric}_{k}.json",
        {
            "metric": metric,
            "k": k,
            "rows": [{"band": "50-54", "n": 433, "registered_lo": 0.7325, "registered_hi": 0.7997}],
        },
    )


def measurement(tmp_path, *, metric="recovery", k=60, order="generation", value=0.75):
    return write(
        tmp_path / f"band_{metric}_{k}_{order}.json",
        {
            "metric": metric,
            "k": k,
            "order": order,
            "bands": {"50-54": {"n_queries": 433, "per_run": {"small_full_6p": value}}},
        },
    )


class TestConventionGuard:
    """A registration may only be read against a table measured its way."""

    def _score(self, tmp_path, monkeypatch, reg, band, *, k=60, order="generation"):
        import scripts.score_job4 as mod

        monkeypatch.setattr(mod, "ROOT", tmp_path)
        return mod.score_pair("test", reg.name, band.name, k, order, "50+", "small_full_6p")

    def test_matching_conventions_score(self, tmp_path, monkeypatch):
        scored = self._score(
            tmp_path,
            monkeypatch,
            registration(tmp_path),
            measurement(tmp_path, value=0.75),
        )
        assert len(scored) == 1
        assert scored[0]["verdict"] == "HIT"

    def test_a_metric_mismatch_is_refused(self, tmp_path, monkeypatch):
        scored = self._score(
            tmp_path,
            monkeypatch,
            registration(tmp_path, metric="recovery"),
            measurement(tmp_path, metric="structure"),
        )
        assert scored == []

    def test_a_k_mismatch_is_refused(self, tmp_path, monkeypatch):
        # The k=1 consensus registration against the k=60 generation table is
        # the specific collision the 50+ instrument invites.
        scored = self._score(
            tmp_path,
            monkeypatch,
            registration(tmp_path, k=1),
            measurement(tmp_path, k=60),
            k=1,
        )
        assert scored == []

    def test_an_order_mismatch_is_refused(self, tmp_path, monkeypatch):
        scored = self._score(
            tmp_path,
            monkeypatch,
            registration(tmp_path),
            measurement(tmp_path, order="generation"),
            order="consensus",
        )
        assert scored == []

    def test_an_absent_run_is_reported_not_scored(self, tmp_path, monkeypatch):
        import scripts.score_job4 as mod

        monkeypatch.setattr(mod, "ROOT", tmp_path)
        scored = mod.score_pair(
            "test",
            registration(tmp_path).name,
            measurement(tmp_path).name,
            60,
            "generation",
            "50+",
            "a_run_that_does_not_exist",
        )
        assert scored == []
