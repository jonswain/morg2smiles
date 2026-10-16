"""When the model misses a large molecule, what does it miss by?

Every night so far has measured *how far* recovery falls with molecule size.
None has asked what the failure is made of, and the dumps already answer it.
Four things are separable, and they point at different work:

**Collisions.** `recovery` counts a candidate whose fingerprint matches the
query, which is the right definition -- the task is inverting a fingerprint,
not guessing the molecule the fingerprint came from -- but a candidate can
match the fingerprint and be a different molecule. That gap between recovery
and structure accuracy is the part of the task that is genuinely ambiguous, and
if it grows with size then part of the cliff is a property of Morgan
fingerprints rather than of this model. Nothing can fix that part.

**Near misses.** Among queries the model never matches, the best Tanimoto it
reaches says whether it is in the right region of chemical space and cannot
land, or lost. A model that misses at 0.95 needs precision; one that misses at
0.6 needs capability, and the two are not the same project.

**Budget.** A query whose 20 slots are not full failed partly for lack of
distinct proposals. On the large protocol this is nearly never the reason --
99.4% of queries fill their budget -- which is worth stating, because "it ran
out of guesses" is the intuitive explanation and it is wrong.

A full budget is not a saturated one, though, so the second table reports
recovery against k per band. If recovery is still climbing at k=20 for large
molecules and flat for small ones, then large molecules are limited by how many
guesses they get rather than by how good the guesses are, and the budget is the
cheapest thing in the project to increase.

**Ranking.** For recovered queries, where in the 20 the match sits. If hits
cluster late, the budget is doing the work and a smaller k would lose them.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

import click

from scripts.band_analysis import DEFAULT_BANDS, heavy_atoms, parse_band


def rows(path: Path):
    for line in open(path):
        yield json.loads(line)


@click.command()
@click.option("--dump", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--bands", default=DEFAULT_BANDS, show_default=True)
@click.option("--k", default=20)
@click.option("--unseen-only/--all-queries", default=True)
@click.option("--out", type=click.Path(path_type=Path), default=None)
def main(dump: Path, bands: str, k: int, unseen_only: bool, out: Path | None) -> None:
    specs = [parse_band(b) for b in bands.split(",")]
    queries = []
    for row in rows(dump):
        if unseen_only and not row["fp_unseen"]:
            continue
        cands = row["results"][:k]
        fp_hit = [i for i, c in enumerate(cands) if c["fp_match"]]
        st_hit = [i for i, c in enumerate(cands) if c["exact_structure"]]
        tanimotos = [c["tanimoto"] for c in cands if c["valid"] and c["tanimoto"] is not None]
        queries.append(
            {
                "size": heavy_atoms(row["reference"]),
                "n_slots": len(cands),
                "fp_rank": fp_hit[0] + 1 if fp_hit else None,
                "st_rank": st_hit[0] + 1 if st_hit else None,
                "n_fp_match": len(fp_hit),
                "collision": bool(fp_hit) and not st_hit,
                "best_tanimoto": max(tanimotos) if tanimotos else 0.0,
            }
        )

    click.echo(f"{dump}  k={k}  {len(queries):,} queries\n")
    header = (
        f"{'band':>8}{'n':>7}{'rec':>8}{'struct':>8}{'collide':>9}"
        f"{'miss tan':>10}{'>=0.9':>8}{'full k':>8}{'hit rank':>10}"
    )
    click.echo(header)
    click.echo("-" * len(header))

    table = {}
    for name, lo, hi in specs:
        band = [q for q in queries if lo <= q["size"] <= hi]
        if not band:
            continue
        n = len(band)
        rec = sum(q["fp_rank"] is not None for q in band) / n
        struct = sum(q["st_rank"] is not None for q in band) / n
        hits = [q for q in band if q["fp_rank"] is not None]
        misses = [q for q in band if q["fp_rank"] is None]
        # Of the queries scored as recovered, how many were recovered by a
        # molecule that is not the reference -- the ambiguous fraction.
        collide = sum(q["collision"] for q in hits) / len(hits) if hits else 0.0
        miss_tan = mean(q["best_tanimoto"] for q in misses) if misses else float("nan")
        near = sum(q["best_tanimoto"] >= 0.9 for q in misses) / len(misses) if misses else 0.0
        full = sum(q["n_slots"] >= k for q in band) / n
        rank = mean(q["fp_rank"] for q in hits) if hits else float("nan")
        click.echo(
            f"{name:>8}{n:>7,}{rec:>8.4f}{struct:>8.4f}{collide:>9.3f}"
            f"{miss_tan:>10.3f}{near:>8.3f}{full:>8.3f}{rank:>10.1f}"
        )
        table[name] = {
            "n_queries": n,
            "recovery": rec,
            "structure": struct,
            "collision_rate_among_hits": collide,
            "mean_best_tanimoto_among_misses": miss_tan,
            "fraction_of_misses_above_0.9_tanimoto": near,
            "budget_filled_rate": full,
            "mean_fp_hit_rank": rank,
        }

    # Second table: the shape of recovery against budget, per band. Derived
    # from the same ranks, so it costs nothing.
    ladder = [1, 2, 5, 10, 20]
    ladder = [j for j in ladder if j <= k]
    header2 = f"{'band':>8}{'n':>7}" + "".join(f"{'@' + str(j):>9}" for j in ladder)
    header2 += f"{'last half':>11}{'k=10->20':>10}"
    click.echo("\n" + header2)
    click.echo("-" * len(header2))
    for name, lo, hi in specs:
        band = [q for q in queries if lo <= q["size"] <= hi]
        if not band:
            continue
        n = len(band)
        curve = {
            j: sum(q["fp_rank"] is not None and q["fp_rank"] <= j for q in band) / n for j in ladder
        }
        row = f"{name:>8}{n:>7,}" + "".join(f"{curve[j]:>9.4f}" for j in ladder)
        if 20 in curve and 10 in curve:
            # Of the hits a budget of 20 buys, the share that needed slots 11-20,
            # and the points the second half of the budget added.
            share = (curve[20] - curve[10]) / curve[20] if curve[20] else float("nan")
            row += f"{share:>11.3f}{100 * (curve[20] - curve[10]):>+10.2f}"
        click.echo(row)
        table[name]["recovery_at_k"] = curve

    click.echo(
        "\nrec/struct: fraction of queries with a fingerprint / exact-structure match in k."
        "\ncollide: of recovered queries, the fraction recovered by a *different* molecule"
        "\n         with the same fingerprint -- the irreducible part of the task."
        "\nmiss tan: mean best Tanimoto on queries never matched; >=0.9 its tail."
        "\nlast half: of the hits k=20 buys, the share found in slots 11-20."
    )
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"dump": str(dump), "k": k, "bands": table}, indent=2))
        click.echo(f"\nwrote {out}")


if __name__ == "__main__":
    main()
