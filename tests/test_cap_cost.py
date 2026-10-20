"""The measurement a committed decision rests on.

Item 3 of the closing plan kept `max_heavy_atoms = 64`, and the stated reason
is this script's two numbers: 2.6% of ChEMBL is above the cap, and 73% of what
the cap excludes would be excluded by the 128-token context anyway. A sign or
scaling error in either would reverse the decision, so both are pinned here on
a planted corpus rather than on ChEMBL.

The subtle one is `raised_cap_fates`: it must consider *only* the molecules the
cap itself rejects. A molecule that fails the element whitelist was never the
cap's to admit, and counting it would understate the yield of raising the cap.
"""

from __future__ import annotations

import gzip
import json

import pytest
from click.testing import CliRunner
from rdkit import Chem

from morg2smiles.data.prepare import StandardizeConfig, standardize
from scripts.cap_cost import (
    MIN_CHARS_FOR_OVER_CAP,
    heavy_atom_histogram,
    raised_cap_fates,
    read_smiles,
    reservoir_sample,
)
from scripts.cap_cost import (
    main as cap_cost,
)

BENZENE = "c1ccccc1"  # 6 heavy atoms
# 70 carbons: over a cap of 64, and 70 tokens, so it clears a 128-token limit.
C70 = "C" * 70
# 200 carbons: over the cap and over the token limit, which is the case that
# turned the decision -- raising the cap would not admit it.
C200 = "C" * 200
# Over the cap and carrying a disallowed element.
WITH_TIN = "[Sn]" + "C" * 70


def chemreps(tmp_path, rows, *, gzipped=True):
    path = tmp_path / ("chemreps.txt.gz" if gzipped else "chemreps.txt")
    body = "chembl_id\tcanonical_smiles\tstandard_inchi\tstandard_inchi_key\n"
    for i, smi in enumerate(rows):
        body += f"CHEMBL{i}\t{smi}\tInChI=1S/x\tKEY\n"
    if gzipped:
        path.write_bytes(gzip.compress(body.encode()))
    else:
        path.write_text(body)
    return path


def test_read_smiles_skips_the_header_and_takes_column_two(tmp_path):
    path = chemreps(tmp_path, [BENZENE, C70])
    assert list(read_smiles(path)) == [BENZENE, C70]


def test_read_smiles_handles_an_uncompressed_file(tmp_path):
    path = chemreps(tmp_path, [BENZENE], gzipped=False)
    assert list(read_smiles(path)) == [BENZENE]


def test_reservoir_sample_counts_the_whole_stream_not_the_sample():
    sample, seen = reservoir_sample(iter(range(1000)), 10, seed=0)
    assert len(sample) == 10
    assert seen == 1000  # the scaling factor depends on this


def test_reservoir_sample_keeps_everything_when_the_stream_is_short():
    sample, seen = reservoir_sample(iter([1, 2, 3]), 10, seed=0)
    assert sorted(sample) == [1, 2, 3]
    assert seen == 3


def test_reservoir_sample_is_uniform_enough_to_scale_with():
    # Half the stream is marked; a sample's marked share should track it.
    stream = ["x"] * 5000 + ["y"] * 5000
    sample, seen = reservoir_sample(iter(stream), 1000, seed=0)
    assert seen == 10_000
    share = sample.count("x") / len(sample)
    assert 0.45 < share < 0.55


def test_heavy_atom_histogram_counts_heavy_atoms_and_reports_failures():
    hist, failed = heavy_atom_histogram([BENZENE, C70, "not a molecule("])
    assert hist == {6: 1, 70: 1}
    assert failed == 1


def test_min_chars_prefilter_cannot_lose_a_candidate():
    # The prefilter rests on len(smiles) >= n_heavy, so a molecule over the cap
    # can never have a string shorter than the cap.
    for smi in (BENZENE, C70, C200, WITH_TIN, "C1CC2CCC1CC2", "c1ccc2ccccc2c1"):
        canonical, _ = standardize(smi, StandardizeConfig(max_heavy_atoms=10**9))
        if canonical is None:
            continue
        if Chem.MolFromSmiles(canonical).GetNumHeavyAtoms() > 64:
            assert len(smi) >= MIN_CHARS_FOR_OVER_CAP


def test_raised_cap_fates_separates_the_token_limit_from_the_cap():
    fates, survivors, longest = raised_cap_fates([C70, C200], cap=64, raised=10**9)

    # C70 clears every other filter; C200 dies on tokens, not on the cap.
    assert fates["survives"] == 1
    assert fates["too_many_tokens"] == 1
    assert survivors == {70: 1}
    assert longest[70] == 70


def test_raised_cap_fates_ignores_molecules_the_cap_never_rejected():
    # Benzene is admitted at both caps, so it is not the cap's discard and must
    # not dilute the denominator.
    fates, survivors, _ = raised_cap_fates([BENZENE, C70], cap=64, raised=10**9)
    assert sum(fates.values()) == 1
    assert survivors == {70: 1}


def test_raised_cap_fates_attributes_an_element_failure_to_the_element():
    fates, survivors, _ = raised_cap_fates([WITH_TIN], cap=64, raised=10**9)
    assert survivors == {}
    assert fates["survives"] == 0
    assert sum(fates.values()) == 1
    assert "disallowed_element" in fates


def test_raised_cap_fates_is_empty_when_nothing_is_over_the_cap():
    fates, survivors, longest = raised_cap_fates([BENZENE], cap=64, raised=10**9)
    assert fates == {}
    assert survivors == {}
    assert longest == {}


def test_cli_reports_the_share_above_the_cap_and_writes_json(tmp_path):
    # Nine benzenes and one 70-carbon chain: 10% above a cap of 64, all of
    # which survives a raise.
    path = chemreps(tmp_path, [BENZENE] * 9 + [C70])
    out = tmp_path / "cap.json"
    result = CliRunner().invoke(
        cap_cost,
        ["--raw", str(path), "--sample", "100", "--yield-sample", "100", "--out", str(out)],
    )
    assert result.exit_code == 0, result.output

    payload = json.loads(out.read_text())
    assert payload["n_rows"] == 10
    assert payload["stage1"]["over_cap"] == 1
    assert payload["stage1"]["over_cap_share"] == pytest.approx(0.1)
    assert payload["stage1"]["largest_seen"] == 70
    assert payload["stage2"]["n_too_large"] == 1
    assert payload["stage2"]["fates"] == {"survives": 1}
    assert payload["stage2"]["implied_survivors"] == 1
    assert payload["stage2"]["longest_tokens_by_band"] == {"70": 70}


def test_cli_scales_counts_to_the_whole_file_when_sampling(tmp_path):
    # 400 rows, a sample of 100. The contract is that a sampled count is
    # multiplied by n_rows / n_sampled before being reported as corpus-wide --
    # asserted exactly, because a statistical assertion here would only be
    # testing the sampler's luck.
    path = chemreps(tmp_path, ([BENZENE] * 3 + [C70]) * 100)
    out = tmp_path / "cap.json"
    result = CliRunner().invoke(
        cap_cost,
        ["--raw", str(path), "--sample", "100", "--yield-sample", "50", "--out", str(out)],
    )
    assert result.exit_code == 0, result.output

    payload = json.loads(out.read_text())
    stage1, stage2 = payload["stage1"], payload["stage2"]
    assert payload["n_rows"] == 400

    scale = payload["n_rows"] / stage1["sampled"]
    assert stage1["implied_over_cap"] == round(stage1["over_cap"] * scale)
    assert stage1["implied_over_cap"] > stage1["over_cap"]  # the point of scaling

    # Stage 2's denominator is the length-prefiltered stream, not the file.
    yield_scale = stage2["n_long"] / stage2["sampled"]
    assert stage2["implied_survivors"] == round(stage2["fates"]["survives"] * yield_scale)
    # Only the 100 long rows pass the prefilter, and all of them survive a raise.
    assert stage2["n_long"] == 100
    assert stage1["over_cap_share"] == pytest.approx(0.25, abs=0.15)
