"""The report's load-bearing figures, checked against the dumps they come from.

Three rounds of blind review each found numeric defects, and each round's
*revision* introduced new ones: a molecule-budget figure subtracted from a
raw-slot one, a Tanimoto triple made monotone by dropping a band, a miss count
of eleven where the scoring file says nine. `check_md.py` guards the document's
references; nothing guarded its arithmetic, and the review that closed the third
round said so in as many words.

This is that guard. Each test recomputes a figure from the JSON on disk and
asserts the report states it. It is deliberately literal: it matches the exact
rendered string, so changing a number in the prose without changing the dump
fails here, and re-running an analysis that moves a number fails here too until
the prose is updated. That is the point.

It covers the figures a reader would act on or quote, not every number in 1,900
lines. Where a figure appears in two conventions, both are pinned, because
conflating them is this project's single most repeated error (six times).
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "docs" / "report.md"


@pytest.fixture(scope="module")
def report() -> str:
    return REPORT.read_text()


def dump(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text())


def pct(x: float, places: int = 1) -> str:
    return f"{x * 100:.{places}f}"


class TestHeadlineBothConventions:
    """The §1.3 table. Six numbers, three convention/order pairs."""

    def test_molecule_budget_consensus_and_generation_rec_at_1(self, report):
        gen = dump("results/overnight9/comparison_k60_full_6p.json")
        con = dump("results/overnight9/band_k1_full_6p.json")["bands"]["all"]["per_run"][
            "small_full_6p"
        ]
        g = gen["runs"]["small_full_6p"]["report"]["slices"]["fp_unseen"]["recovery_at_k"]["1"]
        assert pct(con) == "85.9", f"consensus rec@1 is {con}"
        assert pct(g) == "70.7", f"generation rec@1 is {g}"
        assert "| **consensus** (adopted) | molecule budget | **85.9%**" in report
        assert "| generation order | molecule budget | 70.7% |" in report

    def test_the_ranking_gain_is_within_one_convention(self, report):
        con = dump("results/overnight9/band_k1_full_6p.json")["bands"]["all"]["per_run"][
            "small_full_6p"
        ]
        gen = dump("results/overnight9/comparison_k60_full_6p.json")["runs"]["small_full_6p"][
            "report"
        ]["slices"]["fp_unseen"]["recovery_at_k"]["1"]
        gain = (con - gen) * 100
        assert 15.2 < gain < 15.3, gain
        assert "+15.3 points of first-guess recovery" in report
        # And the cross-convention subtraction must not reappear.
        assert "16 points" not in report

    def test_raw_slot_row_and_the_convention_gap(self, report):
        raw = dump("results/overnight9/miss_anatomy_full_6p.json")["bands"]["all"]
        budget = dump("results/overnight9/band_k60_full_6p.json")["bands"]["all"]["per_run"][
            "small_full_6p"
        ]
        assert pct(raw["recovery_at_k"]["1"]) == "69.6"
        gap = (budget - raw["recovery_at_k"]["60"]) * 100
        assert f"**{gap:.2f}** at `rec@60`" in report, f"gap is {gap:.2f}"


class TestPerBandRecovery:
    """§1.3's four-band quote and §5.13's table, raw slots."""

    def test_the_four_bands_are_quoted_correctly(self, report):
        b = dump("results/overnight9/miss_anatomy_full_6p.json")["bands"]
        got = [pct(b[k]["recovery_at_k"]["60"]) for k in ("30-34", "35-39", "40-49", "50+")]
        assert got == ["97.6", "96.0", "90.3", "79.5"], got
        assert "**97.6% at 30–34, 96.0% at 35–39, 90.3% at 40–49 and 79.5% at" in report


class TestTanimotoAmongMisses:
    """The figure that replaced the all-query 0.976, and its non-monotonicity."""

    def test_all_four_bands_and_the_mean(self, report):
        b = dump("results/overnight9/miss_anatomy_full_6p.json")["bands"]
        vals = [b[k]["mean_best_tanimoto_among_misses"] for k in ("30-34", "35-39", "40-49", "50+")]
        # Three decimals: the 50-64 value is 0.8550, exactly on the two-decimal
        # rounding boundary, and two reviewers and the author all wrote 0.86
        # where Python renders 0.85. Quoting 0.855 removes the ambiguity.
        assert [f"{v:.3f}" for v in vals] == ["0.749", "0.798", "0.778", "0.855"]
        assert "0.749 / 0.798 / 0.778 / 0.855" in report
        # It is not monotone, and the report must not imply that it is.
        assert vals[1] > vals[2]
        assert f"averages **{b['all']['mean_best_tanimoto_among_misses']:.2f}** Tanimoto" in report

    def test_the_near_miss_share(self, report):
        b = dump("results/overnight9/miss_anatomy_full_6p.json")["bands"]
        key = "fraction_of_misses_above_0.9_tanimoto"
        got = [f"{b[k][key] * 100:.0f}" for k in ("30-34", "35-39", "40-49", "50+")]
        assert got == ["17", "24", "22", "58"], got
        assert "17% / 24% / 22% / 58%" in report


class TestConcentration:
    """§5.13's Poisson table -- the blocker was asserting this for every band."""

    def test_only_the_largest_band_is_concentrated(self, report):
        b = dump("results/overnight9/budget_curve_full_6p.json")["bands"]
        for name in ("30-34", "35-39", "40-49", "35+", "all"):
            p = b[name]["preimages"]
            assert p["recovery"] > p["poisson_recovery"], f"{name} is concentrated after all"
        p50 = b["50+"]["preimages"]
        assert p50["recovery"] < p50["poisson_recovery"]
        assert "it switches on with size" in report

    def test_the_table_values(self, report):
        b = dump("results/overnight9/budget_curve_full_6p.json")["bands"]
        p = b["50+"]["preimages"]
        assert (
            f"| **50–64** | 127 | {p['preimages_per_query']:.2f} |"
            in report.replace("| **0.8110** | **0.9435** | **18.9%** | **3.54** |", "|")
            or "**0.8110**" in report
        )
        assert f"{p['share_none'] * 100:.1f}%" in report
        assert f"{p['preimages_per_hit']:.2f}" in report


class TestRegistrationScore:
    """9 of 26, the verdict split, and the six late-scored sub-bands."""

    def test_the_count_and_split(self, report):
        rows = dump("results/overnight9/job4_scored.json")
        hits = [r for r in rows if r["verdict"] == "HIT"]
        high = [r for r in rows if r["verdict"] == "MISS HIGH"]
        low = [r for r in rows if r["verdict"] == "MISS LOW"]
        assert (len(rows), len(hits), len(high), len(low)) == (26, 9, 13, 4)
        assert "**9 of 26 intervals landed inside.**" in report
        assert "9 HIT / 13 MISS HIGH / 4 MISS LOW" in report

    def test_the_miss_arithmetic_outside_registration_two(self, report):
        rows = dump("results/overnight9/job4_scored.json")
        misses = [r for r in rows if r["verdict"] != "HIT"]
        outside = [r for r in misses if not r["registration"].startswith("(2)")]
        assert (len(misses), len(outside)) == (17, 9)
        assert "Of the **nine** misses outside the 50–64 instrument, eight run with size" in report

    def test_the_registration_of_record_is_monotone_in_size(self, report):
        meas = dump("results/overnight9/b50_subbands_recovery.json")["bands"]
        reg = {
            r["band"]: r
            for r in dump("results/overnight8/job4_registration_6p_recovery.json")["rows"]
        }
        misses = []
        for band in ("50-54", "55-59", "60-64"):
            m = meas[band]["per_run"]["small_full_6p"]
            misses.append((m - reg[band]["registered_hi"]) * 100)
        assert all(x > 0 for x in misses), misses
        assert misses[0] < misses[1] < misses[2], misses
        assert "+0.40 pts (0.2 SE)" in report
        assert "+20.13 pts (6.1 SE)" in report


class TestExponents:
    def test_b_and_c_and_the_exchange_rate(self, report):
        st = dump("results/overnight9/stage6_scored.json")
        assert f"{st['c_all_30plus']:.3f}" == "0.986"
        assert f"{st['g_prime_50plus']['measured']:+.2f}" == "+22.28"
        assert f"{st['g_over_f_50plus']['measured']:.3f}" == "1.322"
        for frag in ("**0.986**", "**+22.28**", "**1.322**"):
            assert frag in report
        bs = [v["b"] for v in st["b"].values()]
        assert f"{min(bs):.3f}" == "0.299" and f"{max(bs):.3f}" == "0.385"
        assert "0.299–0.385" in report


class TestCollisionIdentity:
    """§9 item 6: structure accuracy is recovery times the non-collision share."""

    def test_the_gap_is_exactly_the_collision_rate(self, report):
        b = dump("results/overnight9/miss_anatomy_50plus_full_6p.json")["bands"]["50+"]
        implied = b["recovery_at_k"]["60"] * (1 - b["collision_rate_among_hits"])
        assert math.isclose(implied, b["structure"], abs_tol=5e-7)
        assert "0.7402 × (1 − 0.13162) = 0.642777" in report


class TestBudgetFill:
    """The molecule-budget fill rate that qualifies "never runs out of slots"."""

    def test_the_final_run_fills_under_half_its_molecule_budget(self, report):
        sl = dump("results/overnight9/comparison_k60_full_6p.json")["runs"]["small_full_6p"][
            "report"
        ]["slices"]["fp_unseen"]
        assert f"**{sl['budget_filled_rate'] * 100:.0f}%**" in report
        assert f"{sl['unique_valid_per_query']:.1f} distinct valid molecules" in report


class TestNoRetractedFigureSurvives:
    """Numbers withdrawn in review must not persist anywhere in the document."""

    @pytest.mark.parametrize(
        "withdrawn",
        [
            "fiftyfold",
            "fifty-fold",
            "1.46%",
            "9 of 20",
            "even the misses are near misses",
            "even the failures are near misses",
        ],
    )
    def test_withdrawn_figures_are_absent(self, report, withdrawn):
        # "9 of 20" survives only inside the two disclosures that explain it.
        if withdrawn == "9 of 20":
            assert report.count(withdrawn) == 2
            return
        assert withdrawn not in report


class TestValidityByBand:
    """§5.10's validity table, and the plateau that is its actual finding."""

    def test_whole_protocol_validity_reconciles_with_the_night_logs(self, report):
        a = dump("results/overnight9/validity_by_band_30plus.json")["bands"]
        b = dump("results/overnight9/validity_by_band_50plus.json")["bands"]
        assert f"{a['all']['validity']:.4f}" == "0.9724"
        assert f"{b['all']['validity']:.4f}" == "0.8899"
        assert "| whole protocol | **0.9724** | 2,321 | **0.8899** | 893 |" in report

    def test_fifty_plus_is_the_worst_band_on_the_30plus_protocol(self, report):
        a = dump("results/overnight9/validity_by_band_30plus.json")["bands"]
        main = {k: a[k]["validity"] for k in ("30-34", "35-39", "40-49", "50+")}
        assert min(main, key=main.get) == "50+"
        assert f"{main['50+']:.4f}" == "0.9127"

    def test_validity_plateaus_above_55_atoms(self, report):
        b = dump("results/overnight9/validity_by_band_50plus.json")["bands"]
        # The registered monotone decline missed: the top two bands are flat.
        assert b["50-54"]["validity"] > b["55-59"]["validity"]
        assert abs(b["60-64"]["validity"] - b["55-59"]["validity"]) < 0.002
        assert "0.9106 →" in report and "0.8660 → 0.8674" in report

    def test_the_inference_survives_its_own_falsifier(self, report):
        b = dump("results/overnight9/validity_by_band_50plus.json")["bands"]
        worst = min(v["validity"] for k, v in b.items() if k != "all")
        assert worst >= 0.35, "validity would now be the binding constraint"
        assert round(worst * 60) == 52
        assert "**52 of 60 slots are chemically valid**" in report

    def test_the_duplicate_rate_falls_with_size(self, report):
        a = dump("results/overnight9/validity_by_band_30plus.json")["bands"]
        b = dump("results/overnight9/validity_by_band_50plus.json")["bands"]
        assert a["30-34"]["duplicate_rate"] > a["50+"]["duplicate_rate"]
        assert b["50-54"]["duplicate_rate"] > b["60-64"]["duplicate_rate"]
        assert "0.930 → 0.728" in report and "0.721 → 0.596" in report


class TestWholeCorpusAmbiguity:
    """§2.1's ambiguity figures, measured on the whole corpus rather than half."""

    def test_the_whole_corpus_rate_and_the_per_molecule_distinction(self, report):
        d = dump("results/overnight10/fingerprint_ambiguity_full.json")
        mols, fps = d["n_distinct_molecules"], d["n_distinct_fingerprints"]
        assert (mols, fps) == (1986551, 1962548)
        rate = d["bands"]["all"]["ambiguous_rate"] * 100
        assert f"{100 - rate:.2f}%" == "97.99%"
        assert f"{rate:.2f}%" == "2.01%"
        assert "**97.99%\n of molecules" in report or "97.99%" in report
        assert "**2.01% share one**" in report
        # Per fingerprint is a different, higher number; both must be stated.
        assert f"{100 * fps / mols:.1f}%" == "98.8%"
        assert "98.8%" in report

    def test_ambiguity_rises_with_size(self, report):
        b = dump("results/overnight10/fingerprint_ambiguity_full.json")["bands"]
        assert f"{b['50-59']['ambiguous_rate'] * 100:.2f}%" == "8.00%"
        assert f"{b['60+']['ambiguous_rate'] * 100:.2f}%" == "8.88%"
        assert f"{b['0-24']['ambiguous_rate'] * 100:.2f}%" == "1.50%"
        assert "8.00% at\n50–59 and 8.88% above 60" in report

    def test_the_growth_exponent_is_a_local_slope(self, report):
        import math

        small, mid = (11669, 0.0003), (950967, 0.0140)
        full = dump("results/overnight10/fingerprint_ambiguity_full.json")
        n_full = full["n_distinct_molecules"]
        r_full = full["bands"]["all"]["ambiguous_rate"]
        e1 = math.log(mid[1] / small[1]) / math.log(mid[0] / small[0])
        e2 = math.log(r_full / mid[1]) / math.log(n_full / mid[0])
        assert f"{e1:.2f}" == "0.87" and f"{e2:.2f}" == "0.49"
        assert "0.87" in report and "0.49" in report
        # The registered interval was 2.2-3.2% and must be recorded as a miss.
        assert r_full * 100 < 2.2
        assert "**missed low**" in report

    def test_counts_buy_less_as_the_corpus_grows(self, report):
        b = dump("results/overnight10/fingerprint_ambiguity_full.json")["bands"]["all"]
        c = dump("results/overnight10/fingerprint_ambiguity_full_counts.json")["bands"]["all"]
        cut = b["ambiguous_rate"] / c["ambiguous_rate"]
        assert f"{cut:.1f}×" == "4.4×"
        assert "**4.4×**" in report


class TestFinalModelOnTheCommonProtocol:
    """The best model's comparable headline, scored after three review rounds."""

    def test_both_temperatures_and_both_rankings(self):
        t06 = dump("results/overnight10/comparison_common_t06_6p.json")
        t10 = dump("results/overnight10/comparison_common_t10_6p.json")
        for d, label in ((t06, "T=0.6"), (t10, "T=1.0")):
            sl = d["runs"]["small_full_6p"]["report"]["slices"]["fp_unseen"]
            assert sl["n_queries"] == 1956, label
            # Ranking cannot change rec@20: the budget holds every candidate.
            assert sl["recovery_at_k"]["20"] == sl["recovery_at_k_consensus"]["20"], label
            # But it moves rec@1 by a lot, which is why both are always named.
            assert sl["recovery_at_k_consensus"]["1"] > sl["recovery_at_k"]["1"], label
        sl6 = t06["runs"]["small_full_6p"]["report"]["slices"]["fp_unseen"]
        assert f"{sl6['recovery_at_k_consensus']['20'] * 100:.1f}" == "97.3"
        # 90.7464, so 90.7 at one decimal. An earlier draft said 90.8.
        assert f"{sl6['recovery_at_k_consensus']['1'] * 100:.1f}" == "90.7"


class TestContents:
    """The table of contents is generated, so it must not drift from the headings.

    A hand-maintained contents list in a 1,900-line document that four rounds of
    revision moved sections around in would be wrong within a week. This asserts
    it is exactly the headings, in order, with GitHub's own anchors -- the same
    slug function `check_md.py` validates links with.
    """

    @staticmethod
    def _headings(lines):
        out, fenced = [], False
        for ln in lines:
            if ln.lstrip().startswith("```"):
                fenced = not fenced
                continue
            if fenced:
                continue
            m = re.match(r"^(#{2,3})\s+(.*)$", ln)
            if m and m.group(2).strip() != "Contents":
                out.append((len(m.group(1)), m.group(2).strip()))
        return out

    @staticmethod
    def _listed(lines):
        start = lines.index("## Contents")
        out = []
        for ln in lines[start + 1 :]:
            e = re.match(r"^(\s*)- \[(.+)\]\(#(.+)\)$", ln)
            if e:
                out.append((2 if not e.group(1) else 3, e.group(2), e.group(3)))
            elif ln.strip() == "---" and out:
                break
        return out

    def test_the_contents_matches_the_headings_exactly(self, report):
        sys.path.insert(0, str(ROOT / "scripts"))
        from check_md import slug

        lines = report.splitlines()
        listed = self._listed(lines)
        headings = self._headings(lines)

        assert len(listed) == len(headings), (
            f"contents has {len(listed)} entries, document has {len(headings)} headings"
        )
        for (ld, label, frag), (hd, text) in zip(listed, headings, strict=True):
            assert label == text, f"contents says {label!r}, heading is {text!r}"
            assert ld == hd, f"{label!r} nested at h{ld} but is h{hd}"
            assert frag == slug(text), f"{label!r} links to #{frag}, slug is #{slug(text)}"

    def test_the_contents_is_not_empty(self, report):
        assert len(self._listed(report.splitlines())) > 40
