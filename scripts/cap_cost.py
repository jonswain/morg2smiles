"""What does `max_heavy_atoms = 64` actually exclude, and what would raising it buy?

Item 3 of `docs/next-steps-2026-10-19.md` had to decide whether to widen the
corpus window before the final run baked a shard. Its original premise was that
nothing above 64 heavy atoms exists in ChEMBL 35 "as standardised here", which
is circular -- the standardisation *is* the cap -- so the decision was
re-derived from measurement. This script is that measurement.

It answers two questions against the raw chemreps file, before any
standardisation:

1. **How much is above the cap?** A reservoir sample over the whole file, with
   the heavy-atom histogram and the implied corpus-wide counts.
2. **What would a raised cap yield?** For the molecules the cap is responsible
   for discarding -- those `standardize` tags `too_large` and nothing else --
   it re-runs the real `standardize` with the cap lifted and reports where they
   die instead. The answer turned out to be that `max_tokens: 128` binds first
   and three quarters of them exceed it.

Both passes call the project's own `standardize`, not a reimplementation of it,
because the whole point is what *this* pipeline would admit.

    python scripts/cap_cost.py --raw data/raw/chembl_35_chemreps.txt.gz

`len(smiles) >= n_heavy` always holds -- every heavy atom contributes at least
one character -- so stage 2 may prefilter on string length without losing a
candidate.
"""

from __future__ import annotations

import gzip
import json
import random
from collections import Counter
from pathlib import Path

import click
from rdkit import Chem, RDLogger

from morg2smiles.data.prepare import StandardizeConfig, standardize
from morg2smiles.tokenizer import SmilesTokenizer

RDLogger.DisableLog("rdApp.*")

# Every heavy atom costs at least one SMILES character, so a string shorter
# than the cap cannot standardise to more heavy atoms than the cap.
MIN_CHARS_FOR_OVER_CAP = 65


def read_smiles(path: Path):
    """Yield the canonical_smiles column of a chemreps file, gzipped or not."""
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt") as fh:
        next(fh, None)  # header
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2 and parts[1]:
                yield parts[1]


def reservoir_sample(items, n: int, seed: int = 0):
    """A uniform sample of `n` items from a stream of unknown length.

    Returns `(sample, n_seen)`, so a count in the sample can be scaled to the
    whole stream by `n_seen / len(sample)`.
    """
    rng = random.Random(seed)
    out: list[str] = []
    seen = 0
    for item in items:
        seen += 1
        if len(out) < n:
            out.append(item)
        else:
            j = rng.randrange(seen)
            if j < n:
                out[j] = item
    return out, seen


def heavy_atom_histogram(smiles_list) -> tuple[Counter, int]:
    """Heavy-atom counts of whatever parses, plus the number that did not."""
    hist: Counter = Counter()
    failed = 0
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            failed += 1
            continue
        hist[mol.GetNumHeavyAtoms()] += 1
    return hist, failed


def raised_cap_fates(smiles_list, cap: int, raised: int) -> tuple[Counter, Counter, Counter]:
    """Where the cap's own discards die once the cap is lifted.

    Only molecules that `standardize` rejects as `too_large` at `cap` are
    considered -- a molecule failing an earlier filter was never the cap's to
    admit. Returns `(fates, survivors_by_band, longest_tokens_by_band)`.
    """
    base = StandardizeConfig(max_heavy_atoms=cap)
    wide = StandardizeConfig(max_heavy_atoms=raised)

    fates: Counter = Counter()
    survivors: Counter = Counter()
    longest: Counter = Counter()

    for smi in smiles_list:
        _, reason = standardize(smi, base)
        if reason != "too_large":
            continue
        canonical, reason = standardize(smi, wide)
        if canonical is None:
            fates[reason] += 1
            continue
        fates["survives"] += 1
        mol = Chem.MolFromSmiles(canonical)
        band = mol.GetNumHeavyAtoms() // 10 * 10
        survivors[band] += 1
        longest[band] = max(longest[band], len(SmilesTokenizer.tokenize(canonical)))

    return fates, survivors, longest


@click.command()
@click.option(
    "--raw",
    type=click.Path(exists=True, path_type=Path),
    default=Path("data/raw/chembl_35_chemreps.txt.gz"),
    show_default=True,
)
@click.option("--sample", default=120_000, show_default=True, help="Reservoir size, stage 1.")
@click.option("--yield-sample", default=60_000, show_default=True, help="Reservoir size, stage 2.")
@click.option("--cap", default=64, show_default=True, help="The cap under test.")
@click.option("--raised", default=1_000_000_000, show_default=True, help="The cap to compare to.")
@click.option("--seed", default=0, show_default=True)
@click.option("--out", type=click.Path(path_type=Path), default=None)
def main(raw, sample, yield_sample, cap, raised, seed, out):
    cfg = StandardizeConfig(max_heavy_atoms=cap)
    click.echo(f"cap {cap}, max_tokens {cfg.max_tokens}, raw {raw}")

    # -------------------------------------------------- stage 1: how much is above
    sampled, n_rows = reservoir_sample(read_smiles(raw), sample, seed)
    scale = n_rows / len(sampled)
    hist, failed = heavy_atom_histogram(sampled)
    parsed = sum(hist.values())
    over = sum(c for k, c in hist.items() if k > cap)

    click.echo(
        f"\nrows {n_rows:,}  sampled {len(sampled):,}  parsed {parsed:,} (failed {failed:,})"
    )
    click.echo(
        f"above the cap: {over:,} of {parsed:,} = {100 * over / parsed:.3f}%"
        f"  implied {round(over * scale):,}"
    )
    click.echo(f"largest in sample: {max(hist)} heavy atoms")
    click.echo("\ntail, in bands:")
    tail = []
    for lo, hi in ((cap + 1, 69), (70, 79), (80, 99), (100, 149), (150, 10**9)):
        count = sum(v for k, v in hist.items() if lo <= k <= hi)
        label = f"{lo}-{hi}" if hi < 10**9 else f"{lo}+"
        click.echo(f"  {label:>8s}: {count:6,}  {100 * count / parsed:6.3f}%")
        tail.append({"band": label, "n_sampled": count, "implied": round(count * scale)})

    # -------------------------------------------------- stage 2: what a raise yields
    long_enough = (s for s in read_smiles(raw) if len(s) >= MIN_CHARS_FOR_OVER_CAP)
    candidates, n_long = reservoir_sample(long_enough, yield_sample, seed)
    yield_scale = n_long / len(candidates)
    fates, survivors, longest = raised_cap_fates(candidates, cap, raised)
    n_too_large = sum(fates.values())

    click.echo(
        f"\nlen(smiles) >= {MIN_CHARS_FOR_OVER_CAP}: {n_long:,}  sampled {len(candidates):,}"
    )
    click.echo(f"of those, {n_too_large:,} are discarded as 'too_large' at a cap of {cap}\n")
    click.echo("their fate once the cap is raised:")
    for reason, count in fates.most_common():
        click.echo(
            f"  {reason:22s} {count:6,}  {100 * count / n_too_large:6.2f}%"
            f"  implied {round(count * yield_scale):,}"
        )

    click.echo("\nsurvivors by band, and the tokens they need:")
    for band in sorted(survivors):
        click.echo(
            f"  {band:4d}-{band + 9}: {survivors[band]:5,}"
            f"  implied {round(survivors[band] * yield_scale):7,}"
            f"  longest {longest[band]:4d} tokens"
        )
    click.echo(
        f"\ntotal implied new molecules: {round(fates['survives'] * yield_scale):,}"
        f"  ({100 * fates['survives'] / n_too_large:.2f}% of what the cap excludes)"
    )

    if out:
        payload = {
            "raw": str(raw),
            "cap": cap,
            "raised": raised,
            "max_tokens": cfg.max_tokens,
            "n_rows": n_rows,
            "stage1": {
                "sampled": len(sampled),
                "parsed": parsed,
                "over_cap": over,
                "over_cap_share": over / parsed,
                "implied_over_cap": round(over * scale),
                "largest_seen": max(hist),
                "tail": tail,
            },
            "stage2": {
                "n_long": n_long,
                "sampled": len(candidates),
                "n_too_large": n_too_large,
                "fates": dict(fates),
                "implied_survivors": round(fates["survives"] * yield_scale),
                "survivors_by_band": {str(k): v for k, v in sorted(survivors.items())},
                "longest_tokens_by_band": {str(k): v for k, v in sorted(longest.items())},
            },
        }
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2))
        click.echo(f"\nwrote {out}")


if __name__ == "__main__":
    main()
