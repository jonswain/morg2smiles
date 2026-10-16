"""The exchange rate the size-mix verdict rests on.

`exposure_response.py` turns per-band gaps into the two numbers the write-up
actually argues from -- molecules given up per molecule gained, and points per
doubling of exposure -- and both are easy to get quietly wrong: points are not
comparable across bands of different sizes, and a protocol whose bands all sit
at one exposure cannot price a doubling at all, which is exactly the case for
the large protocol under a threshold-30 mix.
"""

from __future__ import annotations

import json
import math

import pytest
from click.testing import CliRunner

from scripts.exposure_response import _ols
from scripts.exposure_response import main as exposure_response


def bands_file(tmp_path, bands: dict[str, tuple[int, float, float]]):
    """bands: band -> (n_queries, reference rate, mix rate)."""
    path = tmp_path / "bands.json"
    path.write_text(
        json.dumps(
            {
                "k": 20,
                "order": "generation",
                "metric": "recovery",
                "budget": "molecules",
                "n_fp_unseen": sum(n for n, _, _ in bands.values()),
                "runs": ["base", "mix"],
                "bands": {
                    band: {"n_queries": n, "per_run": {"base": ref, "mix": got}}
                    for band, (n, ref, got) in bands.items()
                },
            }
        )
    )
    return path


def record_file(tmp_path, name: str, ratios: dict[str, float]):
    path = tmp_path / f"{name}.json"
    path.write_text(
        json.dumps(
            {
                "size_weighted_mix": {
                    "threshold": 30,
                    "factor": 3.0,
                    "bands": {
                        b: {"share": 0.1, "weighted_share": 0.1 * r} for b, r in ratios.items()
                    },
                }
            }
        )
    )
    return path


def run(tmp_path, bands, *mixes, elementary=None):
    out = tmp_path / "out.json"
    if elementary is None:
        elementary = ",".join(json.loads(bands.read_text())["bands"])
    args = [
        "--bands",
        str(bands),
        "--reference",
        "baseline=base",
        "--elementary-bands",
        elementary,
        "--out",
        str(out),
    ]
    for spec in mixes:
        args += ["--mix", spec]
    result = CliRunner().invoke(exposure_response, args)
    assert result.exit_code == 0, result.output
    return json.loads(out.read_text()), result.output


class TestMoleculeAccounting:
    def setup_method(self):
        # 1,000 small queries lose a point; 100 large ones gain five.
        self.bands = {"0-24": (1000, 0.80, 0.79), "35+": (100, 0.20, 0.25)}

    def test_gap_becomes_molecules(self, tmp_path):
        bands = bands_file(tmp_path, self.bands)
        record = record_file(tmp_path, "mix", {"0-24": 0.5, "35+": 2.0})
        report, _ = run(tmp_path, bands, f"mix=mix@{record}")
        rows = {r["band"]: r for r in report["mixes"]["mix"]["rows"]}
        assert rows["0-24"]["molecules"] == pytest.approx(-10.0)
        assert rows["35+"]["molecules"] == pytest.approx(5.0)

    def test_exchange_rate_is_lost_over_gained(self, tmp_path):
        bands = bands_file(tmp_path, self.bands)
        record = record_file(tmp_path, "mix", {"0-24": 0.5, "35+": 2.0})
        report, output = run(tmp_path, bands, f"mix=mix@{record}")
        assert report["mixes"]["mix"]["given_up_per_gain"] == pytest.approx(2.0)
        assert "2.0 given up per one gained" in output

    def test_net_points_weight_bands_by_size(self, tmp_path):
        # -10 + 5 molecules over 1,100 queries is -0.45 points, not the
        # +2.0 that averaging the two band gaps would give.
        bands = bands_file(tmp_path, self.bands)
        record = record_file(tmp_path, "mix", {"0-24": 0.5, "35+": 2.0})
        report, _ = run(tmp_path, bands, f"mix=mix@{record}")
        assert report["mixes"]["mix"]["net_points"] == pytest.approx(100 * -5 / 1100)

    def test_a_mix_that_costs_nothing_here_has_no_rate(self, tmp_path):
        bands = bands_file(tmp_path, {"35+": (100, 0.20, 0.25)})
        record = record_file(tmp_path, "mix", {"35+": 2.0})
        report, output = run(tmp_path, bands, f"mix=mix@{record}")
        assert report["mixes"]["mix"]["given_up_per_gain"] is None
        assert "no band on this protocol pays for the gain" in output


class TestPointsPerDoubling:
    def test_band_rate_divides_by_log2_exposure(self, tmp_path):
        bands = bands_file(tmp_path, {"35+": (100, 0.20, 0.26)})
        record = record_file(tmp_path, "mix", {"35+": 4.0})
        report, _ = run(tmp_path, bands, f"mix=mix@{record}")
        row = report["mixes"]["mix"]["rows"][0]
        assert row["log2_exposure"] == pytest.approx(2.0)
        assert row["points_per_doubling"] == pytest.approx(3.0)

    def test_a_de_weighted_band_that_lost_ground_still_reads_positive(self, tmp_path):
        # Half the exposure, three points worse: the rate is +3 per doubling,
        # because both the gap and the dose changed sign.
        bands = bands_file(tmp_path, {"0-24": (100, 0.80, 0.77)})
        record = record_file(tmp_path, "mix", {"0-24": 0.5})
        report, _ = run(tmp_path, bands, f"mix=mix@{record}")
        assert report["mixes"]["mix"]["rows"][0]["points_per_doubling"] == pytest.approx(3.0)


class TestFit:
    def test_slope_recovers_a_planted_line(self):
        xs = [-1.0, 0.0, 1.0, 2.0]
        ys = [2.0 + 4.0 * x for x in xs]
        slope, intercept, r = _ols(xs, ys)
        assert slope == pytest.approx(4.0)
        assert intercept == pytest.approx(2.0)
        assert r == pytest.approx(1.0)

    def test_no_contrast_in_exposure_is_not_a_slope(self):
        assert _ols([1.0, 1.0, 1.0], [0.5, 2.5, 1.0]) is None

    def test_one_exposure_for_every_band_cannot_price_a_doubling(self, tmp_path):
        bands = bands_file(tmp_path, {"30-34": (100, 0.5, 0.51), "35+": (100, 0.2, 0.24)})
        record = record_file(tmp_path, "mix", {"30-34": 1.69, "35+": 1.69})
        report, output = run(tmp_path, bands, f"mix=mix@{record}")
        assert report["mixes"]["mix"]["fit"] is None
        assert "cannot price a doubling" in output


class TestElementaryBands:
    def test_a_band_list_that_matches_nothing_is_an_error_not_a_division(self, tmp_path):
        bands = bands_file(tmp_path, {"35+": (100, 0.20, 0.25)})
        record = record_file(tmp_path, "mix", {"35+": 2.0})
        result = CliRunner().invoke(
            exposure_response,
            [
                "--bands",
                str(bands),
                "--reference",
                "baseline=base",
                "--mix",
                f"mix=mix@{record}",
            ],
        )
        assert result.exit_code != 0
        assert "must partition the protocol" in result.output


class TestMarginalDose:
    def test_rate_between_doses_uses_only_the_difference(self, tmp_path):
        bands = bands_file(tmp_path, {"0-24": (1000, 0.80, 0.79), "35+": (100, 0.20, 0.25)})
        low = record_file(tmp_path, "low", {"0-24": 0.9, "35+": 1.5})
        high = record_file(tmp_path, "high", {"0-24": 0.5, "35+": 3.0})
        # Both mixes score the same runs here, so the difference is zero and
        # there is nothing to charge for -- the guard must say so rather than
        # divide by it.
        report, output = run(tmp_path, bands, f"low=mix@{low}", f"high=mix@{high}")
        assert report["marginal"]["low->high"]["extra_gained"] == pytest.approx(0.0)
        assert "no rate to quote" in output

    def test_doses_are_ordered_by_the_up_weighted_bands(self, tmp_path):
        bands = bands_file(tmp_path, {"35+": (100, 0.20, 0.25)})
        low = record_file(tmp_path, "low", {"35+": 1.5})
        high = record_file(tmp_path, "high", {"35+": 3.0})
        report, _ = run(tmp_path, bands, f"high=mix@{high}", f"low=mix@{low}")
        assert list(report["marginal"]) == ["low->high"]
        assert math.log2(1.5) < math.log2(3.0)
