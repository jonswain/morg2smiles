"""Is the proposal cloud narrow in the wrong *place*, and in a fixable direction?

Tonight's account says the decoder proposes about twenty molecules close to the
target and misses because none of them is an exact preimage. That leaves open a
question with a cheap answer and an actionable one: are the proposals the right
*size*? A decoder that systematically offers 44-atom molecules for a 55-atom
fingerprint is not failing combinatorially, it is failing at something a length
prior could correct -- and the information is demonstrably in the input, since
set-bit count predicts heavy atoms at r = 0.83 (`size_from_fingerprint.py`).

Reads the dumps only, so it costs nothing. Hits are reported beside misses as
the control: a bias that shows up on both is the decoder's, while one that
shows up only on misses is a property of the hard queries.

The second table asks the question that decides how much of the cliff is a
size failure. Among the proposals that *are* the right size, how often is one
an exact preimage? If that rate were flat across bands, the whole cliff would
reduce to the decoder not proposing big enough molecules -- which a length
prior could address. If it falls with size as well, size is one layer and the
combinatorics is underneath it.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean, median
from typing import TYPE_CHECKING

import click
from rdkit import Chem

from scripts.seed_union import _band_bounds
from scripts.variance_analysis import load

if TYPE_CHECKING:
    from morg2smiles.metrics import QueryOutcome


def _heavy(smiles: str | None) -> int | None:
    if not smiles:
        return None
    mol = Chem.MolFromSmiles(smiles)
    return mol.GetNumHeavyAtoms() if mol is not None else None


def _proposals(outcome: QueryOutcome, k: int) -> list[tuple[int, bool]]:
    """(heavy atoms, is an exact preimage) for each valid proposal in the budget."""
    out = []
    for r in outcome.scored()[:k]:
        n = _heavy(r.canonical or r.smiles) if r.valid else None
        if n:
            out.append((n, r.fp_match))
    return out


@click.command()
@click.option("--dump", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--k", default=20, show_default=True)
@click.option("--budget", default="molecules", show_default=True)
@click.option("--bands", default="0-24,25-29,30-34,35-39,40-49,50+,35+,all", show_default=True)
@click.option("--out", type=click.Path(path_type=Path), default=None)
def main(dump, k, budget, bands, out):
    outcomes = [o for o in load(dump, budget) if o.fp_unseen]
    rows = []
    for o in outcomes:
        target = _heavy(o.reference_smiles)
        proposals = _proposals(o, k)
        if target is None or not proposals:
            continue
        sizes = [n for n, _ in proposals]
        right = [(n, m) for n, m in proposals if n == target]
        rows.append(
            {
                "target": target,
                "hit": any(m for _, m in proposals),
                "mean_proposal": mean(sizes),
                "median_proposal": median(sizes),
                "n_proposals": len(sizes),
                "closest": min(sizes, key=lambda n: abs(n - target)),
                "n_right_size": len(right),
                "n_right_size_matching": sum(1 for _, m in right if m),
            }
        )

    click.echo(f"{dump}  k={k}  {len(rows):,} fingerprint-unseen queries with valid proposals")
    header = (
        f"{'band':>7}{'n':>7}{'target|miss':>12}"
        f"{'misses: mean':>14}{'bias':>7}{'closest':>9}"
        f"{'hits: mean':>12}{'bias':>7}"
    )
    click.echo(header)
    click.echo("-" * len(header))
    report = {"dump": str(dump), "k": k, "bands": {}}
    for spec in bands.split(","):
        lo, hi = _band_bounds(spec)
        band = [r for r in rows if lo <= r["target"] <= hi]
        if not band:
            continue
        misses = [r for r in band if not r["hit"]]
        hits = [r for r in band if r["hit"]]
        entry = {"n_queries": len(band), "n_misses": len(misses), "n_hits": len(hits)}
        # The target column is the *misses'* mean size, so that it and the
        # miss columns beside it describe the same queries; a band's misses are
        # its larger molecules, so a band-wide mean would read as a bias.
        target_of_misses = mean(r["target"] for r in misses) if misses else float("nan")
        line = f"{spec:>7}{len(band):>7,}{target_of_misses:>12.1f}"
        for label, group in (("miss", misses), ("hit", hits)):
            if group:
                proposal = mean(r["mean_proposal"] for r in group)
                bias = mean(r["mean_proposal"] - r["target"] for r in group)
                closest = mean(r["closest"] - r["target"] for r in group)
                entry[label] = {
                    "mean_proposal": proposal,
                    "mean_bias": bias,
                    "mean_closest_bias": closest,
                }
                line += (
                    f"{proposal:>14.1f}{bias:>+7.1f}{closest:>+9.1f}"
                    if label == "miss"
                    else f"{proposal:>12.1f}{bias:>+7.1f}"
                )
            else:
                line += (
                    f"{'--':>14}{'--':>7}{'--':>9}" if label == "miss" else f"{'--':>12}{'--':>7}"
                )
        click.echo(line)
        report["bands"][spec] = entry

    click.echo(
        "\nbias = mean proposal size minus target size; closest = the single "
        "proposal nearest the target in size, same units."
    )

    click.echo("\namong the proposals that are the right size")
    header = (
        f"{'band':>7}{'n':>7}{'valid/query':>13}{'right size':>12}"
        f"{'share':>8}{'any right':>11}{'match | right':>15}"
    )
    click.echo(header)
    click.echo("-" * len(header))
    for spec in bands.split(","):
        lo, hi = _band_bounds(spec)
        band = [r for r in rows if lo <= r["target"] <= hi]
        if not band:
            continue
        valid = mean(r["n_proposals"] for r in band)
        right = mean(r["n_right_size"] for r in band)
        total_right = sum(r["n_right_size"] for r in band)
        matching = sum(r["n_right_size_matching"] for r in band)
        any_right = sum(1 for r in band if r["n_right_size"]) / len(band)
        rate = matching / total_right if total_right else float("nan")
        click.echo(
            f"{spec:>7}{len(band):>7,}{valid:>13.1f}{right:>12.1f}"
            f"{right / valid:>8.1%}{any_right:>11.1%}{rate:>15.3%}"
        )
        report["bands"][spec]["right_size"] = {
            "valid_per_query": valid,
            "right_size_per_query": right,
            "share_of_proposals": right / valid,
            "queries_with_any": any_right,
            "match_rate_among_right_size": rate,
        }
    click.echo(
        "\nmatch | right = the share of right-sized proposals that are an exact "
        "preimage, which is the rate a length prior cannot change."
    )
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        click.echo(f"wrote {out}")


if __name__ == "__main__":
    main()
