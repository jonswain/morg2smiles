"""Does the colder decoder still win once sampling compute is matched?

Stage 6 found T=0.7 worth +1.18 points of recovery@20 over T=1.0 on the common
protocol, at the same oracle budget of 20 calls. But a colder decoder repeats
itself, so the adaptive top-up keeps drawing to fill the 20 slots and gives up:
140.3 samples per query against 123.4, which is 14% more forward passes for the
same 20 oracle calls. The budget this project defines is oracle calls, so the
comparison is legitimate as stated -- but a 14% compute difference is exactly
the kind of second varying thing that has produced three retractions here.

So: truncate each query's candidate list to the first M candidates, in the order
they were drawn, and score both temperatures at the same M. If the colder
decoder still wins at matched M, the gain is the decoder; if the curves cross,
part of it was the extra sampling.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

import click

from morg2smiles.metrics import QueryOutcome
from morg2smiles.oracle import OracleResult
from morg2smiles.stats import discordance, mcnemar_exact, paired_se

FIELDS = ("smiles", "valid", "fp_match", "exact_structure", "tanimoto", "canonical", "duplicate")


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in open(path)]


def hits_at_cost(rows: list[dict], m: int | None, k: int, budget: str) -> list[bool]:
    """Hit at k for fingerprint-unseen queries, seeing only the first m candidates."""
    out = []
    for row in rows:
        if not row["fp_unseen"]:
            continue
        kept = row["results"][:m] if m is not None else row["results"]
        outcome = QueryOutcome(
            results=[OracleResult(**{f: r[f] for f in FIELDS}) for r in kept],
            fp_unseen=True,
            reference_smiles=row["reference"],
            budget=budget,
            n_samples=row["n_samples"],
        )
        out.append(any(r.fp_match for r in outcome.scored_by_consensus()[:k]))
    return out


@click.command()
@click.option("--cold", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--warm", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--cold-label", default="T=0.7")
@click.option("--warm-label", default="T=1.0")
@click.option("--k", default=20)
@click.option("--budget", default="molecules")
@click.option("--caps", default="20,40,60,80,100,120")
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    default=Path("results/overnight4/decode_matched_cost.json"),
)
def main(cold, warm, cold_label, warm_label, k, budget, caps, out):
    cold_rows, warm_rows = load_rows(cold), load_rows(warm)
    cold_mean = mean(r["n_samples"] for r in cold_rows)
    warm_mean = mean(r["n_samples"] for r in warm_rows)
    click.echo(
        f"{cold_label}: {cold_mean:.1f} samples/query   "
        f"{warm_label}: {warm_mean:.1f} samples/query   "
        f"({100 * (cold_mean / warm_mean - 1):+.1f}%)\n"
    )

    report = {
        "cold": {"dump": str(cold), "label": cold_label, "samples_per_query": cold_mean},
        "warm": {"dump": str(warm), "label": warm_label, "samples_per_query": warm_mean},
        "k": k,
        "caps": {},
    }
    header = f"{'candidates seen':>16}{warm_label:>10}{cold_label:>10}{'gap':>8}{'SE':>7}{'p':>11}"
    click.echo(header)
    click.echo("-" * len(header))
    for cap in [int(x) for x in caps.split(",")] + [None]:
        c, w = hits_at_cost(cold_rows, cap, k, budget), hits_at_cost(warm_rows, cap, k, budget)
        b, a = discordance(w, c)
        n = len(w)
        row = {
            "warm": mean(w),
            "cold": mean(c),
            "gap_points": 100 * (mean(c) - mean(w)),
            "paired_se_points": 100 * paired_se(b, a, n),
            "mcnemar_p": mcnemar_exact(b, a),
            "cold_only": b,
            "warm_only": a,
        }
        report["caps"]["all" if cap is None else str(cap)] = row
        p = row["mcnemar_p"]
        click.echo(
            f"{'all' if cap is None else cap:>16}{row['warm']:>10.4f}{row['cold']:>10.4f}"
            f"{row['gap_points']:>+8.2f}{row['paired_se_points']:>7.2f}"
            f"{(f'{p:.1e}' if p < 1e-3 else f'{p:.3f}'):>11}"
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    click.echo(f"\nwrote {out}")


if __name__ == "__main__":
    main()
