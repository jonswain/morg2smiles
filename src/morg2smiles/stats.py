"""Error bars for paired comparisons between runs.

Every comparison in this project scores two runs on the *same* held-out
molecules, so the uncertainty that matters is not the binomial error of either
rate -- that describes a single rate against the population of all molecules --
but the error of their *difference*, measured twice on one fixed set. Queries
both runs get right, and queries both get wrong, cancel exactly and carry no
information about which run is better. Only disagreement does.

Night 4 measured what this is worth. Three runs identical but for ``train.seed``
differed by up to 1.43 points of recovery@20 with a true difference of zero,
against a paired standard error of 0.81 points. The working rule that came out
of it: a gap below about two paired standard errors is not evidence.
"""

from __future__ import annotations

from math import comb, sqrt

__all__ = ["mcnemar_exact", "paired_se", "discordance"]


def discordance(a: list[bool], b: list[bool]) -> tuple[int, int]:
    """Queries ``b`` solves and ``a`` does not, and the reverse.

    Raises if the two runs were not scored on the same queries, since a paired
    test on misaligned results would be silently meaningless.
    """
    if len(a) != len(b):
        raise ValueError(f"paired comparison needs equal lengths, got {len(a)} and {len(b)}")
    b_only = sum(1 for x, y in zip(a, b, strict=True) if not x and y)
    a_only = sum(1 for x, y in zip(a, b, strict=True) if x and not y)
    return b_only, a_only


def paired_se(b_only: int, a_only: int, n: int) -> float:
    """Standard error of the difference in rates, as a fraction (not points).

    ``sqrt(discordant) / n`` -- McNemar's. With no disagreement the two runs
    are identical on every query and the error is zero.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    return sqrt(b_only + a_only) / n


def mcnemar_exact(b_only: int, a_only: int) -> float:
    """Two-sided p-value for McNemar's exact test.

    Under the null the two runs are equally good, so each disagreement is an
    independent coin flip and the number falling one way is
    ``Binomial(b_only + a_only, 1/2)``. The p-value is twice the probability of
    a split at least as lopsided as the one observed. With no disagreements
    there is no evidence either way, so the p-value is 1.
    """
    if b_only < 0 or a_only < 0:
        raise ValueError("discordant counts cannot be negative")
    n = b_only + a_only
    if n == 0:
        return 1.0
    lo = min(b_only, a_only)
    tail = sum(comb(n, i) for i in range(lo + 1)) / 2**n
    return min(1.0, 2 * tail)
