"""The arithmetic behind "more models or more samples?".

`seed_union.py` decides a spending question, so the two quantities it turns on
have to be right: the share of one seed's misses that another seed recovers,
and the equal-spend split, where j models asked for k/j candidates each must be
compared against one model asked for k. Getting either subtly wrong -- counting
a union over the wrong prefix, say -- would answer the question backwards.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from scripts.seed_union import _band_bounds, prod
from scripts.seed_union import main as seed_union

# Two molecules, one small and one large, so a band split is testable.
SMALL = "CCO"
LARGE = "C1=CC=CC=C1CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"


def result(smiles: str, *, hit: bool):
    return {
        "smiles": smiles,
        "valid": True,
        "fp_match": hit,
        "exact_structure": hit,
        "tanimoto": 1.0 if hit else 0.5,
        "canonical": smiles,
        "duplicate": False,
    }


def dump(tmp_path, name: str, queries: list[tuple[str, int | None]], k: int = 20):
    """queries: (reference, slot the hit lands in, or None for a miss)."""
    path = tmp_path / f"{name}.jsonl"
    with open(path, "w") as f:
        for reference, slot in queries:
            results = [
                result(f"C{'C' * i}O", hit=(slot is not None and i == slot)) for i in range(k)
            ]
            f.write(
                json.dumps(
                    {
                        "reference": reference,
                        "fp_unseen": True,
                        "n_samples": k,
                        "results": results,
                    }
                )
                + "\n"
            )
    return path


def run(tmp_path, runs, *extra):
    out = tmp_path / "out.json"
    result = CliRunner().invoke(
        seed_union,
        ["--dumps", str(tmp_path), "--runs", ",".join(runs), "--out", str(out), *extra],
    )
    assert result.exit_code == 0, result.output
    return json.loads(out.read_text()), result.output


class TestUnion:
    def test_disjoint_hits_union_to_both(self, tmp_path):
        # Seed a hits query 1, seed b hits query 2; each is at 0.5 alone.
        dump(tmp_path, "a", [(SMALL, 0), (SMALL, None)])
        dump(tmp_path, "b", [(SMALL, None), (SMALL, 3)])
        report, _ = run(tmp_path, ["a", "b"], "--bands", "all")
        band = report["bands"]["all"]
        assert band["one_seed"] == pytest.approx(0.5)
        assert band["union"] == pytest.approx(1.0)
        assert band["all_seeds_miss"] == pytest.approx(0.0)
        # Every one of a seed's misses was recovered by the other.
        assert band["luck_share_of_misses"] == pytest.approx(1.0)

    def test_shared_misses_leave_the_union_where_it_was(self, tmp_path):
        dump(tmp_path, "a", [(SMALL, 0), (SMALL, None)])
        dump(tmp_path, "b", [(SMALL, 2), (SMALL, None)])
        report, _ = run(tmp_path, ["a", "b"], "--bands", "all")
        band = report["bands"]["all"]
        assert band["union"] == pytest.approx(0.5)
        assert band["all_seeds_miss"] == pytest.approx(0.5)
        assert band["luck_share_of_misses"] == pytest.approx(0.0)

    def test_independence_prediction_is_the_product_of_the_misses(self, tmp_path):
        dump(tmp_path, "a", [(SMALL, 0), (SMALL, None)])
        dump(tmp_path, "b", [(SMALL, 2), (SMALL, None)])
        report, _ = run(tmp_path, ["a", "b"], "--bands", "all")
        # Two seeds at 0.5 would reach 0.75 between them if they were
        # independent; they reached 0.50, which is the finding.
        assert report["bands"]["all"]["union_if_independent"] == pytest.approx(0.75)

    def test_misaligned_dumps_are_refused(self, tmp_path):
        dump(tmp_path, "a", [(SMALL, 0)])
        dump(tmp_path, "b", [(LARGE, 0)])
        result = CliRunner().invoke(
            seed_union, ["--dumps", str(tmp_path), "--runs", "a,b", "--bands", "all"]
        )
        assert result.exit_code != 0
        assert "different molecules" in result.output


class TestEqualSpend:
    def test_a_hit_beyond_the_split_is_not_counted(self, tmp_path):
        # Both seeds hit at slot 15. One seed with all 20 slots finds it;
        # two seeds with 10 slots each do not.
        dump(tmp_path, "a", [(SMALL, 15)])
        dump(tmp_path, "b", [(SMALL, 15)])
        report, output = run(tmp_path, ["a", "b"], "--bands", "all")
        spend = report["bands"]["all"]["equal_spend"]
        assert spend["1_seeds_at_k_20"] == pytest.approx(1.0)
        assert spend["2_seeds_at_k_10"] == pytest.approx(0.0)
        assert "the same 20 molecules of budget" in output

    def test_splitting_wins_when_the_seeds_hit_early_and_differ(self, tmp_path):
        dump(tmp_path, "a", [(SMALL, 1), (SMALL, 15)])
        dump(tmp_path, "b", [(SMALL, 15), (SMALL, 1)])
        report, _ = run(tmp_path, ["a", "b"], "--bands", "all")
        spend = report["bands"]["all"]["equal_spend"]
        assert spend["1_seeds_at_k_20"] == pytest.approx(1.0)
        assert spend["2_seeds_at_k_10"] == pytest.approx(1.0)


class TestBands:
    def test_bounds(self):
        assert _band_bounds("30-34") == (30, 34)
        assert _band_bounds("35+")[0] == 35
        assert _band_bounds("all") == (0, 10**9)

    def test_a_band_splits_the_queries_by_heavy_atoms(self, tmp_path):
        dump(tmp_path, "a", [(SMALL, 0), (LARGE, None)])
        dump(tmp_path, "b", [(SMALL, 0), (LARGE, None)])
        report, _ = run(tmp_path, ["a", "b"], "--bands", "0-24,35+,all")
        assert report["bands"]["0-24"]["n_queries"] == 1
        assert report["bands"]["0-24"]["one_seed"] == pytest.approx(1.0)
        assert report["bands"]["35+"]["one_seed"] == pytest.approx(0.0)

    def test_prod(self):
        assert prod([0.5, 0.5, 0.5]) == pytest.approx(0.125)
        assert prod([]) == pytest.approx(1.0)
