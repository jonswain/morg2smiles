"""Validity by size band, from the outcome dumps.

All three review rounds asked for this. `report.md` §5.10 asserts that 50–64 is
"the corpus's worst-validity band" and builds its central decoding argument on a
cancellation between validity and diversity — cooling raises validity by 6.6 and
2.8 points while lowering distinct molecules per query by 3.3 and 6.1 — yet the
report has band-level figures for recovery, structure, collisions, preimages and
Tanimoto, and none at all for validity. The one mechanism the argument turns on
is the one quantity never broken out by size.

Free: a streaming pass over dumps already on disk. No GPU, no model.

PRE-REGISTRATION, written before the script was first run and committed in the
same commit as this docstring. This project's rule is that a measurement whose
reading is chosen afterwards is not a measurement (report.md §3.9), and five
retractions came from breaking it.

  Known, not predicted. The whole-protocol figures are already in the night-9
  logs: validity 0.972 on the 30+ protocol (fp_unseen, 2,321 queries) and 0.890
  on the 50+ instrument (893 queries). Any per-band numbers must average to
  these, which is the arithmetic check rather than the finding.

  1. DIRECTION. Validity falls as query size rises, on both protocols. A rise,
     or a flat profile, would mean the 0.972 → 0.890 whole-protocol gap is not a
     size effect at all and §5.10's mechanism needs rewriting.
  2. 50–64 IS THE WORST BAND on the 30+ protocol. This is the specific claim
     §5.10 makes and it has never been checked.
  3. INTERVALS. On the 30+ protocol, 30–34 in 0.975–0.995 and the 50+ band in
     0.84–0.94. On the 50+ instrument, a monotone decline across 50–54 / 55–59 /
     60–64, with 60–64 in 0.80–0.90.
  4. THE INFERENCE, registered as the thing that would matter. §5.10 concludes
     "validity is not the binding constraint on large molecules". That survives
     only if the worst band still supplies far more valid proposals than the
     budget needs. Concretely: at k=60, if 60–64 validity is ≥ 0.80 then ≥ 48 of
     60 slots are chemically valid, against a measured 3.54 preimages drawn per
     solved query — so invalidity cannot be what makes the cliff.
     **Validity below ~0.35 in any band would falsify that** and make §5.10's
     cancellation argument the wrong way round.

  The honest expectation is that 1, 2 and 4 hold and that 3 is the row most
  likely to miss, since the interval ends were chosen from two whole-protocol
  averages rather than from any band-level evidence.

Run: PYTHONPATH=src:. python scripts/validity_by_band.py
"""

from __future__ import annotations

import json
from pathlib import Path

import click
from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BANDS = "30-34,35-39,40-49,50-54,55-59,60-64,50+,35+,all"


def parse_band(spec: str) -> tuple[str, int, int]:
    if spec == "all":
        return spec, 0, 10**6
    if spec.endswith("+"):
        return spec, int(spec[:-1]), 10**6
    lo, hi = spec.split("-")
    return spec, int(lo), int(hi)


def heavy_atoms(smiles: str) -> int | None:
    mol = Chem.MolFromSmiles(smiles)
    return None if mol is None else mol.GetNumHeavyAtoms()


def scan(dump: Path) -> list[dict]:
    """One row per fingerprint-unseen query: its size and its proposals."""
    rows = []
    with dump.open() as fh:
        for line in fh:
            rec = json.loads(line)
            if not rec.get("fp_unseen", True):
                continue
            n = heavy_atoms(rec["reference"])
            if n is None:
                continue
            results = rec["results"]
            rows.append(
                {
                    "heavy": n,
                    "n_proposals": len(results),
                    "n_valid": sum(1 for r in results if r["valid"]),
                    "n_duplicate": sum(1 for r in results if r.get("duplicate")),
                }
            )
    return rows


@click.command()
@click.option("--dump", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--bands", default=DEFAULT_BANDS, show_default=True)
@click.option("--out", type=click.Path(path_type=Path), default=None)
def main(dump: Path, bands: str, out: Path | None) -> None:
    rows = scan(dump)
    specs = [parse_band(s) for s in bands.split(",")]

    click.echo(f"{dump}  {len(rows):,} fingerprint-unseen queries\n")
    click.echo(
        f"{'band':>7}{'n':>7}{'validity':>10}{'valid/query':>13}"
        f"{'proposals/query':>17}{'duplicate rate':>16}"
    )
    click.echo("-" * 70)

    report: dict[str, dict] = {}
    for spec, lo, hi in specs:
        band = [r for r in rows if lo <= r["heavy"] <= hi]
        if not band:
            continue
        proposals = sum(r["n_proposals"] for r in band)
        valid = sum(r["n_valid"] for r in band)
        dup = sum(r["n_duplicate"] for r in band)
        validity = valid / proposals if proposals else float("nan")
        report[spec] = {
            "n_queries": len(band),
            "validity": validity,
            "valid_per_query": valid / len(band),
            "proposals_per_query": proposals / len(band),
            "duplicate_rate": dup / proposals if proposals else float("nan"),
        }
        click.echo(
            f"{spec:>7}{len(band):>7,}{validity:>10.4f}"
            f"{valid / len(band):>13.1f}{proposals / len(band):>17.1f}"
            f"{dup / proposals if proposals else float('nan'):>16.3f}"
        )

    click.echo(
        "\nvalidity is valid proposals / all proposals, with duplicates marked rather\n"
        "than dropped -- dropping them changes the denominator and once made validity\n"
        "read 0.714 against a true 0.785 (report.md section 3.5)."
    )
    if out:
        out.write_text(json.dumps({"dump": str(dump), "bands": report}, indent=2) + "\n")
        click.echo(f"\nwrote {out}")


if __name__ == "__main__":
    main()
