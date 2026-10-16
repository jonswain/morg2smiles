"""The law the brute-force price is quoted from.

`budget_curve.py` does two things the write-up leans on hard: it fits an
exponent to the recovery deficit and then inverts that fit into a budget, and
it scores the fit-on-k<=20 extrapolation that every earlier price rested on.
A sign error in either direction would turn an unaffordable route into a cheap
one. The preimage table underneath it carries the night's mechanism claim --
that big molecules draw about as many preimages as small ones but pile them on
fewer queries -- so the count has to be per proposal, not per query.
"""

from __future__ import annotations

import json
import math

import pytest
from click.testing import CliRunner

from scripts.budget_curve import _budget_for, _fit_deficit
from scripts.budget_curve import main as budget_curve

BENZENE = "c1ccccc1"  # 6 heavy atoms


def ladder(exponent: float, scale: float, ks=(1, 2, 5, 10, 20, 30, 40, 60)):
    """A planted power law: 1 - rec(k) = scale * k^-exponent."""
    return {str(k): 1 - scale * k**-exponent for k in ks}


def anatomy(tmp_path, bands: dict[str, dict]):
    path = tmp_path / "anatomy.json"
    path.write_text(json.dumps({"k": 60, "bands": bands}))
    return path


def proposal(smiles: str, *, valid: bool = True, match: bool = False):
    return {
        "smiles": smiles,
        "valid": valid,
        "fp_match": match,
        "exact_structure": match,
        "tanimoto": 1.0 if match else 0.4,
        "canonical": smiles if valid else None,
        "duplicate": False,
    }


def dump(tmp_path, queries):
    path = tmp_path / "d.jsonl"
    with open(path, "w") as f:
        for reference, results in queries:
            f.write(
                json.dumps(
                    {
                        "reference": reference,
                        "fp_unseen": True,
                        "n_samples": len(results),
                        "results": results,
                    }
                )
                + "\n"
            )
    return path


def run(tmp_path, bands, *extra):
    out = tmp_path / "out.json"
    result = CliRunner().invoke(
        budget_curve,
        ["--anatomy", str(anatomy(tmp_path, bands)), "--out", str(out), *extra],
    )
    assert result.exit_code == 0, result.output
    return json.loads(out.read_text())["bands"], result.output


class TestFit:
    def test_recovers_a_planted_exponent(self):
        fit = _fit_deficit(
            {
                k: v
                for k, v in zip(
                    (1, 2, 5, 10, 20, 30, 40, 60),
                    [1 - 0.8 * k**-0.3 for k in (1, 2, 5, 10, 20, 30, 40, 60)],
                    strict=True,
                )
            },
            5,
            60,
        )
        slope, intercept, r = fit
        assert slope == pytest.approx(-0.3, abs=1e-9)
        assert math.exp(intercept) == pytest.approx(0.8, rel=1e-9)
        assert r == pytest.approx(-1.0, abs=1e-9)

    def test_needs_three_rungs(self):
        assert _fit_deficit({5: 0.5, 10: 0.6}, 5, 60) is None

    def test_ignores_rungs_outside_the_window(self):
        # A wild value at k=1 must not reach the fit when min_k is 5.
        planted = {1: 0.99, 5: 1 - 0.8 * 5**-0.3, 10: 1 - 0.8 * 10**-0.3, 20: 1 - 0.8 * 20**-0.3}
        slope, _, _ = _fit_deficit(planted, 5, 60)
        assert slope == pytest.approx(-0.3, abs=1e-9)

    def test_drops_a_saturated_rung_rather_than_taking_log_of_zero(self):
        # rec exactly 1.0 has an infinite log-deficit; the rung is skipped.
        fit = _fit_deficit({5: 0.5, 10: 0.6, 20: 0.7, 40: 1.0}, 5, 60)
        assert fit is not None


class TestBudgetFor:
    def test_inverts_the_planted_law(self):
        # 1 - rec = 0.8 k^-0.3 reaches rec = 0.9 where 0.8 k^-0.3 = 0.1.
        fit = (-0.3, math.log(0.8), -1.0)
        assert _budget_for(fit, 0.9) == pytest.approx((0.1 / 0.8) ** (-1 / 0.3))

    def test_a_flat_or_rising_deficit_has_no_budget(self):
        assert _budget_for((0.0, math.log(0.5), 0.0), 0.9) is None
        assert _budget_for((0.2, math.log(0.5), 1.0), 0.9) is None


class TestExtrapolation:
    def test_a_perfect_power_law_extrapolates_without_error(self, tmp_path):
        bands, output = run(
            tmp_path,
            {"all": {"n_queries": 100, "recovery_at_k": ladder(0.3, 0.8)}},
            "--bands",
            "all",
        )
        extrapolated = bands["all"]["extrapolated"]
        assert extrapolated["error_points"] == pytest.approx(0.0, abs=1e-6)
        assert extrapolated["exponent"] == pytest.approx(0.3, abs=1e-6)
        assert bands["all"]["exponent"] == pytest.approx(0.3, abs=1e-6)

    def test_returns_diminishing_faster_than_the_law_show_a_negative_error(self, tmp_path):
        rungs = ladder(0.3, 0.8)
        rungs["60"] = 1 - 1.5 * (1 - float(rungs["60"]))  # a bigger deficit than fitted
        bands, _ = run(
            tmp_path, {"all": {"n_queries": 100, "recovery_at_k": rungs}}, "--bands", "all"
        )
        assert bands["all"]["extrapolated"]["error_points"] < 0

    def test_a_band_not_in_the_report_is_an_error(self, tmp_path):
        result = CliRunner().invoke(
            budget_curve,
            [
                "--anatomy",
                str(
                    anatomy(tmp_path, {"all": {"n_queries": 1, "recovery_at_k": ladder(0.3, 0.8)}})
                ),
                "--bands",
                "35+",
            ],
        )
        assert result.exit_code != 0
        assert "whose bands are" in result.output


class TestPreimages:
    def two_queries(self, tmp_path):
        # Both queries get two preimages each: concentration equal to its mean.
        return dump(
            tmp_path,
            [
                (
                    BENZENE,
                    [proposal(BENZENE, match=True), proposal(BENZENE, match=True), proposal("CCO")],
                ),
                (BENZENE, [proposal(BENZENE, match=True), proposal(BENZENE, match=True)]),
            ],
        )

    def test_counts_preimages_per_proposal_not_per_query(self, tmp_path):
        out = tmp_path / "out.json"
        result = CliRunner().invoke(
            budget_curve,
            [
                "--anatomy",
                str(
                    anatomy(tmp_path, {"all": {"n_queries": 2, "recovery_at_k": ladder(0.3, 0.8)}})
                ),
                "--dump",
                str(self.two_queries(tmp_path)),
                "--bands",
                "all",
                "--out",
                str(out),
            ],
        )
        assert result.exit_code == 0, result.output
        pre = json.loads(out.read_text())["bands"]["all"]["preimages"]
        assert pre["preimages_per_query"] == pytest.approx(2.0)
        assert pre["recovery"] == pytest.approx(1.0)
        assert pre["share_none"] == 0.0
        assert pre["preimages_per_hit"] == pytest.approx(2.0)

    def test_concentration_shows_up_as_recovery_below_poisson(self, tmp_path):
        # Four preimages on one query and none on the other: the same mean of
        # 2.0 per query, half the recovery, and Poisson above both.
        path = dump(
            tmp_path,
            [
                (BENZENE, [proposal(BENZENE, match=True) for _ in range(4)]),
                (BENZENE, [proposal("CCO")]),
            ],
        )
        out = tmp_path / "out.json"
        result = CliRunner().invoke(
            budget_curve,
            [
                "--anatomy",
                str(
                    anatomy(tmp_path, {"all": {"n_queries": 2, "recovery_at_k": ladder(0.3, 0.8)}})
                ),
                "--dump",
                str(path),
                "--bands",
                "all",
                "--out",
                str(out),
            ],
        )
        assert result.exit_code == 0, result.output
        pre = json.loads(out.read_text())["bands"]["all"]["preimages"]
        assert pre["preimages_per_query"] == pytest.approx(2.0)
        assert pre["recovery"] == pytest.approx(0.5)
        assert pre["poisson_recovery"] == pytest.approx(1 - math.exp(-2.0))
        assert pre["recovery"] < pre["poisson_recovery"]

    def test_invalid_proposals_are_not_counted(self, tmp_path):
        path = dump(
            tmp_path,
            [
                (
                    BENZENE,
                    [proposal(BENZENE, valid=False, match=True), proposal(BENZENE, match=True)],
                ),
            ],
        )
        out = tmp_path / "out.json"
        result = CliRunner().invoke(
            budget_curve,
            [
                "--anatomy",
                str(
                    anatomy(tmp_path, {"all": {"n_queries": 1, "recovery_at_k": ladder(0.3, 0.8)}})
                ),
                "--dump",
                str(path),
                "--bands",
                "all",
                "--out",
                str(out),
            ],
        )
        assert result.exit_code == 0, result.output
        assert json.loads(out.read_text())["bands"]["all"]["preimages"][
            "preimages_per_query"
        ] == pytest.approx(1.0)
