"""The factorisation the cliff account now rests on.

`size_bias.py` splits recovery into "did the decoder propose a molecule of the
right size" and "was a right-sized proposal the preimage", and the write-up
multiplies the two back together to reproduce the measured recovery. Both
quantities are easy to compute slightly wrong -- counting an invalid proposal,
or counting a right-sized proposal once per query instead of once each -- and
either error would move the conclusion about which lever to pull.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from scripts.size_bias import _heavy
from scripts.size_bias import main as size_bias

BENZENE = "c1ccccc1"  # 6 heavy atoms
TOLUENE = "Cc1ccccc1"  # 7
ETHANOL = "CCO"  # 3


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
    """queries: (reference, [proposal dicts])."""
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


def run(tmp_path, queries, *extra):
    out = tmp_path / "out.json"
    path = dump(tmp_path, queries)
    result = CliRunner().invoke(
        size_bias, ["--dump", str(path), "--out", str(out), "--bands", "all", *extra]
    )
    assert result.exit_code == 0, result.output
    return json.loads(out.read_text())["bands"]["all"], result.output


class TestHeavyAtoms:
    def test_counts_heavy_atoms_only(self):
        assert _heavy(BENZENE) == 6
        assert _heavy(ETHANOL) == 3

    def test_unparseable_is_none(self):
        assert _heavy("not a molecule") is None
        assert _heavy(None) is None
        assert _heavy("") is None


class TestBias:
    def test_bias_is_proposal_minus_target(self, tmp_path):
        # Target toluene (7), both proposals benzene (6): one atom short.
        band, _ = run(tmp_path, [(TOLUENE, [proposal(BENZENE), proposal(BENZENE)])])
        assert band["miss"]["mean_bias"] == pytest.approx(-1.0)
        assert band["miss"]["mean_proposal"] == pytest.approx(6.0)

    def test_hits_and_misses_are_reported_apart(self, tmp_path):
        band, _ = run(
            tmp_path,
            [
                (TOLUENE, [proposal(TOLUENE, match=True)]),
                (TOLUENE, [proposal(ETHANOL)]),
            ],
        )
        assert band["n_hits"] == 1
        assert band["n_misses"] == 1
        assert band["hit"]["mean_bias"] == pytest.approx(0.0)
        assert band["miss"]["mean_bias"] == pytest.approx(-4.0)

    def test_nearest_sized_proposal_is_not_the_mean(self, tmp_path):
        # One proposal of exactly the right size among three tiny ones: the
        # mean is far off and the nearest is spot on.
        band, _ = run(
            tmp_path,
            [(TOLUENE, [proposal(ETHANOL), proposal(ETHANOL), proposal(TOLUENE)])],
        )
        assert band["miss"]["mean_bias"] == pytest.approx((3 + 3 + 7) / 3 - 7)
        assert band["miss"]["mean_closest_bias"] == pytest.approx(0.0)

    def test_invalid_proposals_are_not_counted(self, tmp_path):
        band, _ = run(
            tmp_path,
            [(TOLUENE, [proposal(TOLUENE), proposal("junk", valid=False)])],
        )
        assert band["right_size"]["valid_per_query"] == pytest.approx(1.0)
        assert band["miss"]["mean_bias"] == pytest.approx(0.0)


class TestRightSizeConditional:
    def test_right_sized_proposals_are_counted_once_each(self, tmp_path):
        band, _ = run(
            tmp_path,
            [(TOLUENE, [proposal(TOLUENE), proposal(TOLUENE), proposal(ETHANOL)])],
        )
        assert band["right_size"]["right_size_per_query"] == pytest.approx(2.0)
        assert band["right_size"]["share_of_proposals"] == pytest.approx(2 / 3)
        assert band["right_size"]["queries_with_any"] == pytest.approx(1.0)

    def test_match_rate_is_over_right_sized_proposals_not_queries(self, tmp_path):
        # Four right-sized proposals across two queries, one of them a match.
        band, _ = run(
            tmp_path,
            [
                (TOLUENE, [proposal(TOLUENE, match=True), proposal(TOLUENE)]),
                (TOLUENE, [proposal(TOLUENE), proposal(TOLUENE)]),
            ],
        )
        assert band["right_size"]["match_rate_among_right_size"] == pytest.approx(0.25)

    def test_a_wrong_sized_match_does_not_enter_the_conditional(self, tmp_path):
        # Pathological but possible: a fingerprint match of a different size.
        band, _ = run(tmp_path, [(TOLUENE, [proposal(ETHANOL, match=True)])])
        assert band["right_size"]["right_size_per_query"] == pytest.approx(0.0)
        assert band["n_hits"] == 1

    def test_the_product_reproduces_recovery(self, tmp_path):
        # Two queries, one recovered: recovery 0.5, and the product of
        # right-sized proposals per query and the match rate agrees.
        band, _ = run(
            tmp_path,
            [
                (TOLUENE, [proposal(TOLUENE, match=True), proposal(TOLUENE)]),
                (TOLUENE, [proposal(TOLUENE), proposal(TOLUENE)]),
            ],
        )
        r = band["right_size"]
        assert r["right_size_per_query"] * r["match_rate_among_right_size"] == pytest.approx(0.5)
        assert band["n_hits"] / band["n_queries"] == pytest.approx(0.5)
