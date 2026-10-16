"""Choose the decoder's temperature per query, from the fingerprint alone.

The temperature gain rises monotonically with molecule size, which suggests the
best setting is not one number. A per-query setting is only usable if it can be
chosen from the *input*: at generation time the molecule is what is unknown.

A folded Morgan fingerprint's set-bit count is a usable estimator of size --
r = 0.83 on the clean pool, and 62 set bits is the best single threshold for
"at least 35 heavy atoms" (precision 0.77, recall 0.64; see
scripts/size_from_fingerprint.py). **That threshold is fixed there, against
molecule size, not here against recovery**, so the policy it defines is not
fitted to the set it is scored on. The full threshold curve is reported beside
it for context, and the best cell of that curve is a selected maximum and
should be read as one.

Every arm is the same checkpoint on the same molecules, so switching between
them costs nothing but the choice: the policy is scored on the arm it picks,
query by query, from dumps that already exist.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

import click
from rdkit import Chem

from morg2smiles.fingerprints import FPConfig, compute
from morg2smiles.stats import discordance, mcnemar_exact, paired_se
from scripts.variance_analysis import hits, load

#: Chosen by scripts/size_from_fingerprint.py to predict 35+ heavy atoms.
DEFAULT_BITS = 62


@click.command()
@click.option(
    "--dumps",
    type=click.Path(exists=True, path_type=Path),
    default=Path("results/overnight5/outcomes_common_temps"),
    help="Directory of t<tag>.jsonl dumps, one per temperature, same molecules.",
)
@click.option("--cold", required=True, help="Dump stem for large molecules, e.g. t04.")
@click.option("--hot", required=True, help="Dump stem for small molecules, e.g. t06.")
@click.option("--bits", default=DEFAULT_BITS, show_default=True)
@click.option("--k", default=20)
@click.option("--order", default="consensus", type=click.Choice(["generation", "consensus"]))
@click.option("--budget", default="molecules")
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    default=Path("results/overnight5/temperature_policy.json"),
)
def main(dumps, cold, hot, bits, k, order, budget, out) -> None:
    arms = {}
    refs = None
    for stem in (cold, hot):
        path = dumps / f"{stem}.jsonl"
        if not path.exists():
            raise click.ClickException(f"no dump at {path}")
        outcomes = load(path, budget)
        mine = [o.reference_smiles for o in outcomes if o.fp_unseen]
        if refs is None:
            refs = mine
        elif mine != refs:
            raise click.ClickException(f"{stem} was scored on different molecules")
        arms[stem] = hits(outcomes, k, order)

    fp_cfg = FPConfig()
    set_bits = [len(compute(s, fp_cfg)) for s in refs]
    sizes = [
        (Chem.MolFromSmiles(s).GetNumHeavyAtoms() if Chem.MolFromSmiles(s) else 0) for s in refs
    ]
    n = len(refs)
    click.echo(f"{n:,} fingerprint-unseen queries, rec@{k} {order} order")
    click.echo(f"arms: cold={cold}  hot={hot}\n")

    def policy(threshold: int) -> list[bool]:
        return [arms[cold][i] if set_bits[i] >= threshold else arms[hot][i] for i in range(n)]

    chosen = policy(bits)
    report = {
        "n_fp_unseen": n,
        "k": k,
        "order": order,
        "cold": cold,
        "hot": hot,
        "bits_threshold": bits,
        "fixed_arms": {stem: mean(h) for stem, h in arms.items()},
        "policy": mean(chosen),
        "n_routed_cold": sum(1 for b in set_bits if b >= bits),
        "comparisons": {},
        "curve": [],
    }
    for stem, h in arms.items():
        b_only, a_only = discordance(h, chosen)
        report["comparisons"][stem] = {
            "gap_points": 100 * (mean(chosen) - mean(h)),
            "policy_only": b_only,
            "arm_only": a_only,
            "paired_se_points": 100 * paired_se(b_only, a_only, n),
            "mcnemar_p": mcnemar_exact(b_only, a_only),
        }

    # The best achievable by choosing per query with hindsight: not deployable,
    # but it bounds what any input-only rule could reach.
    oracle = [arms[cold][i] or arms[hot][i] for i in range(n)]
    report["per_query_oracle"] = mean(oracle)

    click.echo(f"{'arm':<28}{'rec@' + str(k):>9}")
    for stem, rate in report["fixed_arms"].items():
        click.echo(f"{stem:<28}{rate:>9.4f}")
    click.echo(
        f"{'policy (bits >= ' + str(bits) + ')':<28}{report['policy']:>9.4f}"
        f"   {report['n_routed_cold']:,} of {n:,} routed cold"
    )
    click.echo(f"{'per-query oracle (bound)':<28}{report['per_query_oracle']:>9.4f}\n")
    for stem, c in report["comparisons"].items():
        pv = c["mcnemar_p"]
        click.echo(
            f"policy vs {stem:<12}{c['gap_points']:>+7.2f} pts  SE {c['paired_se_points']:>5.2f}"
            f"   p {(f'{pv:.2e}' if pv < 1e-3 else f'{pv:.3f}')}"
        )

    click.echo(f"\n{'bits':>6}{'routed cold':>13}{'rec@' + str(k):>9}{'vs hot':>9}")
    for threshold in range(30, 101, 2):
        p = policy(threshold)
        report["curve"].append(
            {
                "bits": threshold,
                "routed_cold": sum(1 for b in set_bits if b >= threshold),
                "recovery": mean(p),
            }
        )
        click.echo(
            f"{threshold:>6}{report['curve'][-1]['routed_cold']:>13}"
            f"{mean(p):>9.4f}{100 * (mean(p) - mean(arms[hot])):>+9.2f}"
        )

    # How well the routing actually tracked size, for the record.
    routed = [1 if b >= bits else 0 for b in set_bits]
    large = [1 if s >= 35 else 0 for s in sizes]
    tp = sum(1 for r, is_large in zip(routed, large, strict=True) if r and is_large)
    report["routing_on_this_set"] = {
        "precision": tp / max(sum(routed), 1),
        "recall": tp / max(sum(large), 1),
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    click.echo(f"\nwrote {out}")


if __name__ == "__main__":
    main()
