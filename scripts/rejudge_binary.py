"""Re-judge dumped candidates under the binary fingerprint.

A count-fingerprint model is judged by its own oracle, which demands an exact
*count* match -- a stricter target than the binary models face. Comparing that
number with theirs would penalise the richer input for being asked a harder
question. This re-scores the same candidates, in the same order, against the
binary fingerprint, so the two can be compared like for like.
"""

from __future__ import annotations

import json
from pathlib import Path

import click

from morg2smiles.fingerprints import FPConfig, compute, equal


@click.command()
@click.argument("dump", type=click.Path(exists=True, path_type=Path))
@click.option("--k", default=20)
def main(dump: Path, k: int) -> None:
    binary = FPConfig(radius=2, n_bits=2048, counts=False, folded=True)
    rows = [json.loads(line) for line in open(dump)]
    unseen = [r for r in rows if r["fp_unseen"]]
    ks = (1, 5, k)
    hits = {n: {"own": 0, "binary": 0} for n in ks}
    for row in unseen:
        target = compute(row["reference"], binary)
        scored = [r for r in row["results"] if r["valid"] and not r["duplicate"]][:k]
        own = [r["fp_match"] for r in scored]
        bin_ = [equal(compute(r["canonical"], binary), target) for r in scored]
        for n in ks:
            hits[n]["own"] += any(own[:n])
            hits[n]["binary"] += any(bin_[:n])
    out = {
        "dump": str(dump),
        "n_fp_unseen": len(unseen),
        **{f"rec@{n}": {key: v / len(unseen) for key, v in hits[n].items()} for n in ks},
    }
    click.echo(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
