"""The second of the two prices, and the one that is easier to quote wrongly.

`step_curve.py` compares an exponent measured over a twelvefold range of
inference budget against one measured over a 2.5-fold range of training steps,
and then converts the pair into a query count above which the longer run is
cheaper. Two things have to hold for that number to mean anything: the pair
exponent has to be read from the deficit rather than from recovery, and the
break-even has to charge inference per query and training once. Getting either
backwards reverses the recommendation.

The accelerating-trace test is the one that protects the write-up's caveat: if
the early-fit error ever came out positive the script would be claiming a law
where it has a local slope.
"""

from __future__ import annotations

import json
import math

import pytest
from click.testing import CliRunner

from scripts.step_curve import break_even, fit_trace, pair_exponent, read_trace
from scripts.step_curve import main as step_curve


def history(tmp_path, name: str, points, *, slice_name="fp_unseen", omit_step=False):
    """Write a history.json whose rec@20 trace is `points` [(step, rec), ...]."""
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    rows = []
    for step, rec in points:
        row = {
            "epoch": 1,
            "train_loss": 0.5,
            "valid": {"slices": {slice_name: {"recovery_at_k": {"1": rec / 4, "20": rec}}}},
        }
        if not omit_step:
            row["step"] = step
        rows.append(row)
    (d / "history.json").write_text(json.dumps(rows))
    return d


def planted(c: float, scale: float, steps=(1500, 3000, 6000, 12000, 21000)):
    """A planted law: 1 - rec(S) = scale * S^-c."""
    return [(s, 1 - scale * s**-c) for s in steps]


def anatomy(tmp_path, name, bands):
    path = tmp_path / name
    path.write_text(json.dumps({"k": 60, "bands": bands}))
    return path


class TestReadTrace:
    def test_reads_step_and_recovery(self, tmp_path):
        history(tmp_path, "r", [(1500, 0.1), (3000, 0.2)])
        assert read_trace("r", tmp_path) == [(1500, 0.1), (3000, 0.2)]

    def test_sorts_by_step(self, tmp_path):
        history(tmp_path, "r", [(3000, 0.2), (1500, 0.1)])
        assert [s for s, _ in read_trace("r", tmp_path)] == [1500, 3000]

    def test_skips_rows_from_before_the_step_column_existed(self, tmp_path):
        history(tmp_path, "r", [(1500, 0.1), (3000, 0.2)], omit_step=True)
        assert read_trace("r", tmp_path) == []

    def test_drops_saturated_and_empty_points(self, tmp_path):
        # 0 and 1 have no finite log-deficit; they are dropped, not clamped.
        history(tmp_path, "r", [(1500, 0.0), (3000, 0.4), (4500, 1.0)])
        assert read_trace("r", tmp_path) == [(3000, 0.4)]

    def test_falls_back_to_the_all_slice(self, tmp_path):
        history(tmp_path, "r", [(1500, 0.3)], slice_name="all")
        assert read_trace("r", tmp_path) == [(1500, 0.3)]

    def test_prefers_fp_unseen_when_both_are_present(self, tmp_path):
        d = tmp_path / "r"
        d.mkdir()
        (d / "history.json").write_text(
            json.dumps(
                [
                    {
                        "step": 1500,
                        "valid": {
                            "slices": {
                                "all": {"recovery_at_k": {"20": 0.9}},
                                "fp_unseen": {"recovery_at_k": {"20": 0.3}},
                            }
                        },
                    }
                ]
            )
        )
        assert read_trace("r", tmp_path) == [(1500, 0.3)]


class TestFitTrace:
    def test_recovers_a_planted_exponent(self):
        c, _, r = fit_trace(planted(0.8, 50.0))
        assert c == pytest.approx(0.8)
        assert r == pytest.approx(-1.0)

    def test_needs_three_points(self):
        assert fit_trace(planted(0.8, 50.0, steps=(1500, 3000))) is None

    def test_a_flat_trace_has_no_fit(self):
        assert fit_trace([(1500, 0.4), (3000, 0.4), (6000, 0.4)]) is None


class TestPairExponent:
    def test_recovers_a_planted_exponent(self):
        # deficit 0.8 -> 0.4 over a doubling of steps is exactly c = 1.
        assert pair_exponent((1000, 0.2), (2000, 0.6)) == pytest.approx(1.0)

    def test_reads_the_deficit_not_the_recovery(self):
        # Recovery trebles here while the deficit falls by a quarter: an
        # exponent read off recovery would be positive and much larger.
        c = pair_exponent((1000, 0.2), (2000, 0.6))
        wrong = math.log(0.6 / 0.2) / math.log(2)
        assert c == pytest.approx(1.0)
        assert wrong > 1.5

    def test_guards_the_degenerate_cases(self):
        assert pair_exponent((2000, 0.2), (1000, 0.6)) is None  # steps not increasing
        assert pair_exponent((1000, 0.2), (2000, 1.0)) is None  # saturated
        assert pair_exponent((1000, 0.0), (2000, 0.6)) is None  # nothing at the short end


class TestBreakEven:
    def test_charges_inference_per_query_and_training_once(self):
        # Halving the deficit with b = c costs the same multiple of each, so the
        # break-even is just the ratio of the two unit costs.
        n = break_even(0.5, 0.5, 0.5, steps=1000, k=10, sec_per_step=2.0, sec_per_slot=0.5)
        assert n == pytest.approx(2000 / 5)

    def test_a_steeper_step_exponent_lowers_the_break_even_for_deeper_cuts(self):
        kw = dict(b=0.3, c=0.9, steps=21117, k=20, sec_per_step=1.337, sec_per_slot=0.016)
        assert break_even(0.5, **kw) < break_even(0.75, **kw)

    def test_no_break_even_when_the_cut_is_not_a_cut(self):
        kw = dict(b=0.3, c=0.9, steps=1000, k=20, sec_per_step=1.0, sec_per_slot=0.1)
        assert break_even(1.0, **kw) is None
        assert break_even(1.5, **kw) is None

    def test_no_break_even_without_a_falling_deficit(self):
        assert break_even(0.5, 0.0, 0.9, 1000, 20, 1.0, 0.1) is None
        assert break_even(0.5, 0.3, 0.0, 1000, 20, 1.0, 0.1) is None


class TestCli:
    def test_reports_a_planted_trace(self, tmp_path):
        history(tmp_path, "r", planted(0.8, 50.0))
        result = CliRunner().invoke(step_curve, ["--runs", "r", "--checkpoints", str(tmp_path)])
        assert result.exit_code == 0, result.output
        assert "0.800" in result.output

    def test_an_accelerating_trace_reports_a_negative_early_error(self, tmp_path):
        # The exponent grows with step, which is what the real traces do; the
        # early fit must then underpredict the final recovery.
        history(
            tmp_path,
            "r",
            [
                (s, 1 - 20.0 * s ** -(0.5 + 0.00002 * s))
                for s in (1500, 3000, 4500, 6000, 12000, 21000)
            ],
        )
        out = tmp_path / "o.json"
        result = CliRunner().invoke(
            step_curve, ["--runs", "r", "--checkpoints", str(tmp_path), "--out", str(out)]
        )
        assert result.exit_code == 0, result.output
        entry = json.loads(out.read_text())["traces"]["r"]
        assert entry["extrapolated"]["exponent"] < entry["exponent"]
        assert entry["extrapolated"]["error_points"] < 0

    def test_a_trace_window_restricts_the_fit(self, tmp_path):
        """Two runs of different lengths are only comparable over one window."""
        # A planted trace whose exponent rises with step, as the real ones do.
        history(
            tmp_path,
            "r",
            [
                (s, 1 - 20.0 * s ** -(0.5 + 0.00002 * s))
                for s in (1500, 3000, 4500, 6000, 12000, 21000)
            ],
        )
        out_all, out_win = tmp_path / "a.json", tmp_path / "w.json"
        for out, extra in ((out_all, []), (out_win, ["--trace-window", "6000,21000"])):
            result = CliRunner().invoke(
                step_curve,
                ["--runs", "r", "--checkpoints", str(tmp_path), "--out", str(out), *extra],
            )
            assert result.exit_code == 0, result.output
        whole = json.loads(out_all.read_text())["traces"]["r"]
        windowed = json.loads(out_win.read_text())["traces"]["r"]
        assert windowed["first_step"] == 6000
        assert windowed["n_points"] < whole["n_points"]
        # The late window sees the steeper part of an accelerating curve.
        assert windowed["exponent"] > whole["exponent"]

    def test_pair_and_break_even_tables(self, tmp_path):
        history(tmp_path, "r", planted(0.8, 50.0))
        short = anatomy(
            tmp_path, "short.json",
            {"35+": {"n_queries": 100, "recovery_at_k": {"20": 0.2, "60": 0.3}}},
        )
        long = anatomy(
            tmp_path, "long.json",
            {"35+": {"n_queries": 100, "recovery_at_k": {"20": 0.6, "60": 0.7}}},
        )
        curve = tmp_path / "curve.json"
        curve.write_text(json.dumps({"bands": {"35+": {"exponent": 0.28}}}))
        out = tmp_path / "o.json"
        result = CliRunner().invoke(
            step_curve,
            ["--runs", "r", "--checkpoints", str(tmp_path), "--pair", f"{short},{long}",
             "--pair-steps", "1000,2000", "--bands", "35+", "--budget-curve", str(curve),
             "--out", str(out)],
        )
        assert result.exit_code == 0, result.output
        report = json.loads(out.read_text())
        assert report["pair"]["35+"]["k20"] == pytest.approx(1.0)
        entry = report["break_even"]["35+"]
        assert entry["ratio"] == pytest.approx(1.0 / 0.28)
        assert entry["break_even_queries"]["0.5"] > 0

    def test_a_cheaper_slot_raises_the_break_even(self, tmp_path):
        """Cheap inference means more queries before the training run pays."""
        history(tmp_path, "r", planted(0.8, 50.0))
        short = anatomy(
            tmp_path, "short.json", {"35+": {"n_queries": 100, "recovery_at_k": {"20": 0.2}}}
        )
        long = anatomy(
            tmp_path, "long.json", {"35+": {"n_queries": 100, "recovery_at_k": {"20": 0.6}}}
        )
        curve = tmp_path / "curve.json"
        curve.write_text(json.dumps({"bands": {"35+": {"exponent": 0.28}}}))
        seen = []
        for slot in ("0.1", "0.01"):
            out = tmp_path / f"o{slot}.json"
            result = CliRunner().invoke(
                step_curve,
                ["--runs", "r", "--checkpoints", str(tmp_path), "--pair", f"{short},{long}",
                 "--pair-steps", "1000,2000", "--bands", "35+", "--budget-curve", str(curve),
                 "--sec-per-slot", slot, "--out", str(out)],
            )
            assert result.exit_code == 0, result.output
            seen.append(json.loads(out.read_text())["break_even"]["35+"]["break_even_queries"]["0.5"])
        assert seen[1] == pytest.approx(seen[0] * 10)
