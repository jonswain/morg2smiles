"""The arithmetic every band claim rests on.

`scripts/` is otherwise untested here, on the reasonable ground that it holds
analysis rather than library code. These two pieces are the exception. Every
error bar in `docs/overnight-2026-10-16.md` is produced by `arm_table.py`
combining per-arm between-seed sds, and every band number is produced by
`hits()` choosing a field on the oracle verdict -- so a silent regression in
either would not break a run, it would publish a wrong number.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from morg2smiles.metrics import QueryOutcome
from morg2smiles.oracle import OracleResult
from scripts.arm_table import main as arm_table
from scripts.arm_table import parse_arm
from scripts.variance_analysis import hits


def verdict(*, fp_match: bool, exact_structure: bool) -> OracleResult:
    return OracleResult(
        smiles="C",
        valid=True,
        fp_match=fp_match,
        exact_structure=exact_structure,
        tanimoto=1.0 if fp_match else 0.5,
        canonical="C",
        duplicate=False,
    )


def outcome(*verdicts: OracleResult, fp_unseen: bool = True) -> QueryOutcome:
    return QueryOutcome(
        results=list(verdicts), fp_unseen=fp_unseen, reference_smiles="C", n_samples=1
    )


class TestHitsMetric:
    """A collision is a hit for recovery and a miss for structure."""

    def test_collision_counts_for_recovery_only(self):
        collided = outcome(verdict(fp_match=True, exact_structure=False))
        assert hits([collided], k=20, order="generation") == [True]
        assert hits([collided], k=20, order="generation", metric="recovery") == [True]
        assert hits([collided], k=20, order="generation", metric="structure") == [False]

    def test_exact_hit_counts_for_both(self):
        exact = outcome(verdict(fp_match=True, exact_structure=True))
        assert hits([exact], k=20, order="generation", metric="recovery") == [True]
        assert hits([exact], k=20, order="generation", metric="structure") == [True]

    def test_miss_counts_for_neither(self):
        miss = outcome(verdict(fp_match=False, exact_structure=False))
        assert hits([miss], k=20, order="generation", metric="recovery") == [False]
        assert hits([miss], k=20, order="generation", metric="structure") == [False]

    def test_k_truncates_under_both_metrics(self):
        late = outcome(
            verdict(fp_match=False, exact_structure=False),
            verdict(fp_match=True, exact_structure=True),
        )
        assert hits([late], k=1, order="generation", metric="recovery") == [False]
        assert hits([late], k=2, order="generation", metric="recovery") == [True]
        assert hits([late], k=1, order="generation", metric="structure") == [False]
        assert hits([late], k=2, order="generation", metric="structure") == [True]

    def test_fp_seen_queries_are_dropped(self):
        seen = outcome(verdict(fp_match=True, exact_structure=True), fp_unseen=False)
        assert hits([seen], k=20, order="generation", metric="structure") == []


class TestParseArm:
    def test_splits_name_from_runs(self):
        assert parse_arm("mix=a,b") == ("mix", ["a", "b"])

    def test_single_run_arm(self):
        assert parse_arm("solo=a") == ("solo", ["a"])


def band_report(tmp_path, per_run: dict[str, float]):
    path = tmp_path / "bands.json"
    path.write_text(
        json.dumps(
            {
                "k": 20,
                "order": "generation",
                "runs": sorted(per_run),
                "bands": {"35+": {"n_queries": 1000, "per_run": per_run}},
            }
        )
    )
    return path


class TestArmTable:
    def run(self, tmp_path, per_run, *arms):
        bands = band_report(tmp_path, per_run)
        out = tmp_path / "arms.json"
        result = CliRunner().invoke(
            arm_table,
            ["--bands", str(bands), "--out", str(out), *sum((["--arm", a] for a in arms), [])],
        )
        assert result.exit_code == 0, result.output
        return json.loads(out.read_text())["bands"]["35+"]

    def test_gap_is_mix_minus_reference(self, tmp_path):
        band = self.run(
            tmp_path,
            {"b1": 0.10, "b2": 0.12, "m1": 0.20, "m2": 0.22},
            "baseline=b1,b2",
            "mix=m1,m2",
        )
        assert band["arms"]["baseline"]["mean"] == pytest.approx(0.11)
        assert band["arms"]["mix"]["mean"] == pytest.approx(0.21)
        assert band["vs_reference"]["mix"]["gap_points"] == pytest.approx(10.0)

    def test_se_combines_both_arms(self, tmp_path):
        # statistics.stdev is the *sample* sd, so each arm's sd over {x, x+0.04}
        # is 0.04/sqrt(2); SE = sqrt(sd^2/2 + sd^2/2) = sd.
        sd = 0.04 / 2**0.5
        band = self.run(
            tmp_path,
            {"b1": 0.10, "b2": 0.14, "m1": 0.20, "m2": 0.24},
            "baseline=b1,b2",
            "mix=m1,m2",
        )
        assert band["vs_reference"]["mix"]["se_points"] == pytest.approx(100 * sd)
        assert band["vs_reference"]["mix"]["se_units"] == pytest.approx(0.10 / sd)

    def test_pairs_favouring_counts_every_cross_pair(self, tmp_path):
        band = self.run(
            tmp_path,
            {"b1": 0.10, "b2": 0.30, "m1": 0.20, "m2": 0.22},
            "baseline=b1,b2",
            "mix=m1,m2",
        )
        # m1 and m2 each beat b1 and lose to b2.
        assert band["vs_reference"]["mix"]["pairs_favouring"] == 2
        assert band["vs_reference"]["mix"]["pairs_total"] == 4

    def test_single_seed_arm_borrows_the_reference_sd(self, tmp_path):
        band = self.run(
            tmp_path, {"b1": 0.10, "b2": 0.14, "solo": 0.20}, "baseline=b1,b2", "solo=solo"
        )
        entry = band["vs_reference"]["solo"]
        assert entry["sd_borrowed_from_reference"] is True
        # The solo arm has no sd of its own, so it is given the reference's:
        # SE = sqrt(sd^2 / 2 + sd^2 / 1) with sd the sample sd of {0.10, 0.14}.
        sd = 0.04 / 2**0.5
        assert entry["se_points"] == pytest.approx(100 * (sd**2 / 2 + sd**2) ** 0.5)
        assert band["arms"]["solo"]["sd"] is None
