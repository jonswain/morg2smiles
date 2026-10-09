"""Metrics, and the slicing that stops them from flattering the model.

The headline number is **recovery@k**: the fraction of held-out fingerprints for
which at least one of k distinct guesses reproduces the fingerprint exactly.

Every metric is reported on two slices:

``all``
    Every query in the split.
``fp_unseen``
    Only queries whose fingerprint never appears in the training set.

The gap between them is the point. A model can score well on ``all`` by
memorising the training set, and a nearest-neighbour lookup does exactly that.
Only ``fp_unseen`` measures reconstruction, so that is the number to optimise
and the number any claim should quote.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from statistics import mean

from .oracle import OracleResult

__all__ = ["QueryOutcome", "recovery_at_k", "structure_accuracy_at_k", "evaluate", "SLICES"]

SLICES = ("all", "fp_unseen")


@dataclass
class QueryOutcome:
    """Everything observed for one held-out fingerprint.

    Attributes:
        results: Oracle verdicts on the distinct candidates, **in the order
            generated**. Order matters: recovery@k reads the first k, so a model
            that puts its best guess first scores better at low k.
        fp_unseen: Whether this fingerprint is absent from the training set.
            Supplied by the dataset, not inferred here.
        reference_smiles: The source molecule, for failure analysis.
        budget: What one of the k slots is spent on. ``"molecules"`` (the
            default) spends it on a distinct parseable molecule; ``"strings"``
            spends it on any distinct string the model emitted, including
            unparseable ones. See :meth:`scored`.
        n_samples: Raw strings drawn from the model, before any deduplication.
            Kept because every other diagnostic divides by it: with
            oversampling, ``len(results)`` no longer says how much sampling
            the number cost.
    """

    results: list[OracleResult] = field(default_factory=list)
    fp_unseen: bool = False
    reference_smiles: str | None = None
    budget: str = "molecules"
    n_samples: int = 0

    def scored(self, k: int | None = None) -> list[OracleResult]:
        """The candidates that consume the k budget, in generation order.

        Under the ``"molecules"`` budget, unparseable candidates do not consume
        a slot. The oracle is a fingerprint comparison on a parsed molecule, so
        an unparseable string is not a guess it can be asked about -- RDKit
        rejects it locally, for free, without consulting the oracle at all. No
        sane caller would spend one of k oracle queries on a string it already
        knows does not parse, so scoring as if it had understates the model.

        Validity is not thereby excused: it is reported separately, and it
        still sets how much sampling a k-molecule budget costs.
        """
        if self.budget == "molecules":
            candidates = [r for r in self.results if r.valid and not r.duplicate]
        else:
            candidates = [r for r in self.results if not r.duplicate]
        return candidates if k is None else candidates[:k]

    @property
    def n_candidates(self) -> int:
        """Distinct candidates judged by the oracle -- the oracle's workload."""
        return len(self.results)

    @property
    def n_scored(self) -> int:
        """Candidates that consume a slot of the k budget."""
        return len(self.scored())

    def hit_rank(self) -> int | None:
        """Index of the first fingerprint match, or None if there is none."""
        for i, r in enumerate(self.scored()):
            if r.fp_match:
                return i
        return None


def _slice(outcomes: Sequence[QueryOutcome], name: str) -> list[QueryOutcome]:
    if name == "all":
        return list(outcomes)
    if name == "fp_unseen":
        return [o for o in outcomes if o.fp_unseen]
    raise ValueError(f"unknown slice {name!r}; expected one of {SLICES}")


def recovery_at_k(outcomes: Sequence[QueryOutcome], k: int) -> float:
    """Fraction of queries with a fingerprint match in the first k candidates.

    Queries that produced fewer than k candidates still count in the
    denominator -- failing to generate is a failure, not an exclusion.
    """
    if not outcomes:
        return 0.0
    hits = sum(any(r.fp_match for r in o.scored(k)) for o in outcomes)
    return hits / len(outcomes)


def structure_accuracy_at_k(outcomes: Sequence[QueryOutcome], k: int) -> float:
    """Fraction of queries whose *original* molecule appears in the first k.

    Strictly below recovery@k, and capped by fingerprint collisions: where
    several molecules share a fingerprint, no model can reliably pick the one
    the test set happened to draw from.
    """
    if not outcomes:
        return 0.0
    hits = sum(any(r.exact_structure for r in o.scored(k)) for o in outcomes)
    return hits / len(outcomes)


def _slice_metrics(outcomes: Sequence[QueryOutcome], ks: Sequence[int]) -> dict:
    if not outcomes:
        return {"n_queries": 0}

    all_results = [r for o in outcomes for r in o.results]
    valid = [r for r in all_results if r.valid]
    hit_ranks = [r for r in (o.hit_rank() for o in outcomes) if r is not None]
    n_samples = sum(o.n_samples for o in outcomes)

    return {
        "n_queries": len(outcomes),
        "recovery_at_k": {str(k): recovery_at_k(outcomes, k) for k in ks},
        "structure_accuracy_at_k": {str(k): structure_accuracy_at_k(outcomes, k) for k in ks},
        # Fraction of what the model emitted that RDKit accepts, counted over
        # every candidate including same-molecule respellings. Those are marked
        # rather than dropped precisely so this denominator stays a property of
        # the model: excluding them would remove mostly valid candidates and
        # make a model look less valid the more it repeats itself.
        #
        # Low validity does not cost recovery under the molecules budget, but it
        # sets how much sampling that budget costs, so it is still worth fixing.
        "validity": len(valid) / len(all_results) if all_results else 0.0,
        # How much of the sampling went on molecules already proposed.
        "duplicate_rate": (
            sum(1 for r in all_results if r.duplicate) / len(all_results) if all_results else 0.0
        ),
        # Distinct valid molecules per query: the diversity recovery@k depends
        # on. A model that samples one molecule 100 times cannot improve past
        # recovery@1. Counted per query and then averaged -- taking one set
        # over every query conflates "this query was diverse" with "different
        # queries got different answers", which is not the same thing and is
        # only coincidentally close when targets rarely repeat.
        "unique_valid_per_query": mean(
            len({r.canonical for r in o.results if r.valid}) for o in outcomes
        ),
        # Three different counts, because under oversampling they diverge and
        # each answers a different question: how much sampling the number cost,
        # how much oracle work it cost, and how much of the k budget it used.
        "mean_samples_per_query": n_samples / len(outcomes) if n_samples else None,
        "mean_candidates_per_query": mean(o.n_candidates for o in outcomes),
        "mean_scored_per_query": mean(o.n_scored for o in outcomes),
        # How close the near-misses were. Distinguishes "almost right" from
        # "generating noise" when recovery is low.
        "mean_best_tanimoto": mean(
            max((r.tanimoto for r in o.results), default=0.0) for o in outcomes
        ),
        # Where in the candidate list hits land, over the queries that hit at
        # all. Near 0 means ranking is good and a bigger k would buy little.
        "mean_hit_rank": mean(hit_ranks) if hit_ranks else None,
    }


def evaluate(
    outcomes: Sequence[QueryOutcome],
    *,
    ks: Sequence[int] = (1, 5, 20, 100),
    elapsed_seconds: float | None = None,
) -> dict:
    """Compute the full metric report over both slices.

    Args:
        outcomes: One :class:`QueryOutcome` per held-out fingerprint.
        ks: The k values to report recovery at. Values above the number of
            candidates actually generated are reported but will plateau.
        elapsed_seconds: Wall-clock for the generation pass, to report
            throughput. Optional.

    Returns:
        A JSON-serialisable dict with a sub-dict per slice, plus the headline
        ``primary_metric`` -- recovery@max(ks) on the ``fp_unseen`` slice --
        hoisted to the top level so the leaderboard and the iteration loop
        cannot accidentally sort on the memorisable one.
    """
    ks = tuple(sorted(set(int(k) for k in ks)))
    budgets = {o.budget for o in outcomes}
    report: dict = {
        "ks": list(ks),
        # What a slot in the k budget buys. Recorded on every report because it
        # changes what recovery@k *means*, so rows computed under different
        # budgets are not comparable and must not be silently ranked together.
        "budget": budgets.pop() if len(budgets) == 1 else "mixed",
        "slices": {s: _slice_metrics(_slice(outcomes, s), ks) for s in SLICES},
    }

    unseen = report["slices"]["fp_unseen"]
    report["primary_metric"] = unseen.get("recovery_at_k", {}).get(str(max(ks)), 0.0)
    report["primary_metric_name"] = f"recovery@{max(ks)} (fp_unseen)"
    report["fp_unseen_fraction"] = unseen["n_queries"] / len(outcomes) if outcomes else 0.0

    if elapsed_seconds:
        n_candidates = sum(o.n_candidates for o in outcomes)
        report["elapsed_seconds"] = elapsed_seconds
        report["queries_per_second"] = len(outcomes) / elapsed_seconds
        report["candidates_per_second"] = n_candidates / elapsed_seconds

    return report


def format_report(report: dict) -> str:
    """Render a metric report as a short text table for terminal output."""
    lines = [f"{report['primary_metric_name']}: {report['primary_metric']:.4f}", ""]
    ks = report["ks"]
    header = f"{'slice':<12}{'n':>8}" + "".join(f"{'rec@' + str(k):>10}" for k in ks)
    lines += [header, "-" * len(header)]
    for name, m in report["slices"].items():
        if not m.get("n_queries"):
            lines.append(f"{name:<12}{0:>8}")
            continue
        row = f"{name:<12}{m['n_queries']:>8}"
        row += "".join(f"{m['recovery_at_k'][str(k)]:>10.4f}" for k in ks)
        lines.append(row)
    lines.append("")
    for name, m in report["slices"].items():
        if not m.get("n_queries"):
            continue
        lines.append(
            f"{name:<12} validity={m['validity']:.3f} "
            f"unique/query={m['unique_valid_per_query']:.1f} "
            f"best_tanimoto={m['mean_best_tanimoto']:.3f} "
            f"struct@{max(ks)}={m['structure_accuracy_at_k'][str(max(ks))]:.4f}"
        )
    if "candidates_per_second" in report:
        lines.append("")
        lines.append(
            f"throughput: {report['queries_per_second']:.1f} queries/s, "
            f"{report['candidates_per_second']:.0f} candidates/s"
        )
    return "\n".join(lines)
