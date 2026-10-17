"""Two ways to buy a point of recovery: a bigger budget, or a longer run.

`budget_curve.py` measured what inference budget costs — the recovery deficit
falls as `k^−b`, with b between 0.09 and 0.40 depending on molecule size. This
asks the same question of training steps, which block 1 of the weekend of
2026-10-17 identified as the dial that actually moves recovery, by a factor
four over the training corpus.

The two exponents are only comparable if they are measured on the same queries
at the same k, so the step exponent here is a *pair* exponent: two checkpoints
of the same architecture trained on the same shard for different numbers of
steps, scored on the same protocol, giving

    c = log(D_short / D_long) / log(S_long / S_short)

for the deficit D at a fixed k. Fitting a run's own `history.json` trace gives
a second estimate over a much wider range of steps, and reports it separately
because the two measure different things: the trace is scored against 500
molecules of its own shard's validation split, not the holdout protocol.

**The step law is not as clean as the budget law, and this script says so
rather than hiding it.** The budget deficit is straight in log-log to
|r| ≥ 0.99 over a twelvefold range of k. The step deficit curves: fitting a
trace's first half and predicting its last point underestimates recovery by 3
to 9 points, and the fitted exponent rises as more of the range is included.
That is a curve accelerating in log-log space, which cannot continue — recovery
is bounded by 1 — so the exponent reported here is a local slope at the top of
the measured range and nothing else. The `--extrapolate-from` check prints the
error so the reader can see the size of it.

The break-even is the one number worth taking away. Cutting the deficit by a
factor f costs `f^(-1/b)` times the inference budget on *every* query forever,
or `f^(-1/c)` times the training steps once, so there is a query count above
which the longer run is cheaper. It is computed only for cuts inside the
measured range of both laws.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import click

TRACE_METRIC = ("recovery_at_k", "20")


def _ols(xs: list[float], ys: list[float]) -> tuple[float, float, float] | None:
    """Slope, intercept and correlation, or None when x or y does not vary."""
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx < 1e-12 or syy < 1e-12:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    slope = sxy / sxx
    return slope, my - slope * mx, sxy / math.sqrt(sxx * syy)


def read_trace(name: str, root: Path = Path("checkpoints")) -> list[tuple[int, float]]:
    """(step, rec@20) from a run's history, dropping unusable points.

    Runs from before the step column existed contribute nothing, and a recovery
    of exactly 0 or 1 has no finite log-deficit.
    """
    path = root / name / "history.json"
    key, k = TRACE_METRIC
    out = []
    for row in json.loads(path.read_text()):
        if "step" not in row:
            continue
        slices = row.get("valid", {}).get("slices", {})
        sl = slices.get("fp_unseen") or slices.get("all")
        if not sl or k not in sl.get(key, {}):
            continue
        rec = sl[key][k]
        if 0.0 < rec < 1.0:
            out.append((row["step"], rec))
    return sorted(out)


def fit_trace(trace: list[tuple[int, float]]) -> tuple[float, float, float] | None:
    """Fit log(1 - rec) on log(step). Returns (c, intercept, r) with c positive."""
    fit = _ols([math.log(s) for s, _ in trace], [math.log(1 - v) for _, v in trace])
    if fit is None:
        return None
    slope, intercept, r = fit
    return -slope, intercept, r


def pair_exponent(short: tuple[int, float], long: tuple[int, float]) -> float | None:
    """The step exponent from two matched checkpoints at one k."""
    (s0, r0), (s1, r1) = short, long
    if s1 <= s0 or not (0 < r0 < 1) or not (0 < r1 < 1):
        return None
    return math.log((1 - r0) / (1 - r1)) / math.log(s1 / s0)


def break_even(
    f: float, b: float, c: float, steps: int, k: int, sec_per_step: float, sec_per_slot: float
) -> float | None:
    """Queries above which buying the cut with training steps is cheaper.

    `f` is the factor the deficit is multiplied by, so f < 1 is an improvement.
    """
    if not 0 < f < 1 or b <= 0 or c <= 0:
        return None
    train = sec_per_step * steps * (f ** (-1 / c) - 1)
    per_query = sec_per_slot * k * (f ** (-1 / b) - 1)
    if per_query <= 0:
        return None
    return train / per_query


@click.command()
@click.option(
    "--runs",
    required=True,
    help="Comma-separated checkpoint names whose history.json traces are fitted.",
)
@click.option(
    "--checkpoints",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("checkpoints"),
    show_default=True,
    help="Directory holding <run>/history.json.",
)
@click.option(
    "--pair",
    default=None,
    help=(
        "Two miss_anatomy.py reports, short,long, for the matched pair exponent. "
        "Both must be the same architecture on the same shard and protocol."
    ),
)
@click.option("--pair-steps", default=None, help="The two step counts, short,long.")
@click.option("--bands", default="30-34,35-39,40-49,50+,35+,all")
@click.option("--at-k", default="20,60", help="The fixed k values at which the pair is read.")
@click.option(
    "--trace-window",
    default=None,
    help=(
        "lo,hi -- fit each trace only over this step interval. Because the step "
        "law accelerates, a run's global exponent depends on the range it covers, "
        "so comparing two runs that stopped at different steps requires pinning "
        "the window. Runs sharing a shard also share the validation draw, which "
        "makes the restricted exponents directly comparable."
    ),
)
@click.option(
    "--extrapolate-from",
    default=0.5,
    show_default=True,
    help="Fit each trace on this fraction of its steps and score it against the last point.",
)
@click.option(
    "--sec-per-step", default=1.337, show_default=True, help="Measured on small_1m: 7.84 h / 21,117."
)
@click.option(
    "--sec-per-slot",
    default=0.01596,
    show_default=True,
    help="Measured on small_1m_matched: 2,298 s / (2,400 queries x 60 slots).",
)
@click.option("--cuts", default="0.75,0.5", help="Deficit factors for the break-even table.")
@click.option(
    "--budget-curve",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="A budget_curve.py report, whose exponents b are priced against the pair's c.",
)
@click.option("--at-steps", default=21117, show_default=True, help="The step count being doubled.")
@click.option("--at-budget", default=20, show_default=True, help="The budget being multiplied.")
@click.option("--out", type=click.Path(path_type=Path), default=None)
def main(
    runs,
    checkpoints,
    trace_window,
    pair,
    pair_steps,
    bands,
    at_k,
    extrapolate_from,
    sec_per_step,
    sec_per_slot,
    cuts,
    budget_curve,
    at_steps,
    at_budget,
    out,
):
    report: dict = {"traces": {}, "pair": {}, "break_even": {}}

    names = [s.strip() for s in runs.split(",") if s.strip()]
    window = None
    if trace_window is not None:
        lo, hi = (int(s.strip()) for s in trace_window.split(","))
        window = (lo, hi)
        report["trace_window"] = {"lo": lo, "hi": hi}
    click.echo("the deficit against training steps, from each run's own history")
    click.echo("(scored on 500 molecules of that run's own shard, not the holdout protocol)")
    if window is not None:
        click.echo(f"(restricted to steps {window[0]:,}..{window[1]:,})")
    click.echo("")
    header = f"{'run':>18}{'pts':>5}{'steps':>18}{'rec@20':>8}{'c':>8}{'r':>9}{'early c':>9}{'error':>9}"
    click.echo(header)
    click.echo("-" * len(header))
    for name in names:
        trace = read_trace(name, checkpoints)
        if window is not None:
            trace = [p for p in trace if window[0] <= p[0] <= window[1]]
        fit = fit_trace(trace)
        if fit is None:
            click.echo(f"{name:>18}{len(trace):>5}  too few usable points")
            continue
        c, intercept, r = fit
        entry = {"n_points": len(trace), "first_step": trace[0][0], "last_step": trace[-1][0],
                 "rec_at_last": trace[-1][1], "exponent": c, "correlation": r}
        cut = trace[-1][0] * extrapolate_from
        early = [p for p in trace if p[0] <= cut]
        early_fit = fit_trace(early) if len(early) >= 3 else None
        if early_fit is not None:
            ec, ei, _ = early_fit
            predicted = 1 - math.exp(ei) * trace[-1][0] ** -ec
            err = 100 * (predicted - trace[-1][1])
            entry["extrapolated"] = {"fitted_to_step": cut, "exponent": ec,
                                     "predicted": predicted, "error_points": err}
            tail = f"{ec:>9.3f}{err:>+9.2f}"
        else:
            tail = f"{'--':>9}{'--':>9}"
        report["traces"][name] = entry
        click.echo(
            f"{name:>18}{len(trace):>5}{f'{trace[0][0]:,}..{trace[-1][0]:,}':>18}"
            f"{trace[-1][1]:>8.4f}{c:>8.3f}{r:>9.4f}{tail}"
        )
    click.echo(
        "\n'early c' refits on the first half of the run and 'error' scores that fit against "
        "the last point. A negative error with a smaller early exponent is a curve that "
        "accelerates in log-log space, so the exponent is a local slope, not a law."
    )

    if pair is None:
        _write(out, report)
        return

    short_path, long_path = (Path(s.strip()) for s in pair.split(","))
    s0, s1 = (int(s.strip()) for s in pair_steps.split(","))
    short = json.loads(short_path.read_text())["bands"]
    long = json.loads(long_path.read_text())["bands"]
    ks = [int(s) for s in at_k.split(",")]
    specs = [s.strip() for s in bands.split(",")]

    click.echo(
        f"\nthe matched pair exponent: {s0:,} against {s1:,} steps, same architecture, "
        "same shard, same protocol"
    )
    header = f"{'band':>7}{'n':>7}" + "".join(f"{'c at k=' + str(k):>12}" for k in ks)
    click.echo(header)
    click.echo("-" * len(header))
    for spec in specs:
        if spec not in short or spec not in long:
            continue
        row = {}
        for k in ks:
            a = short[spec]["recovery_at_k"].get(str(k))
            b_ = long[spec]["recovery_at_k"].get(str(k))
            row[k] = pair_exponent((s0, a), (s1, b_)) if a is not None and b_ is not None else None
        report["pair"][spec] = {f"k{k}": v for k, v in row.items()}
        click.echo(
            f"{spec:>7}{long[spec]['n_queries']:>7,}"
            + "".join(f"{row[k]:>12.3f}" if row[k] is not None else f"{'--':>12}" for k in ks)
        )

    if budget_curve is None:
        _write(out, report)
        return

    curve = json.loads(budget_curve.read_text())["bands"]
    factors = [float(s) for s in cuts.split(",")]
    click.echo(
        f"\n what the same cut costs each way, at {at_steps:,} steps and k={at_budget}"
        f"\n (training {sec_per_step:.3f} s/step once; inference {sec_per_slot:.5f} s/slot "
        "per query, forever)"
    )
    header = (
        f"{'band':>7}{'b':>7}{'c':>7}{'c/b':>6}"
        + "".join(f"{'x' + f'{f:g}' + ': queries':>18}" for f in factors)
    )
    click.echo(header)
    click.echo("-" * len(header))
    for spec in specs:
        c = report["pair"].get(spec, {}).get(f"k{at_budget}")
        b = curve.get(spec, {}).get("exponent")
        if c is None or b is None or c <= 0 or b <= 0:
            continue
        entry = {"b": b, "c": c, "ratio": c / b, "break_even_queries": {}}
        cells = ""
        for f in factors:
            n = break_even(f, b, c, at_steps, at_budget, sec_per_step, sec_per_slot)
            entry["break_even_queries"][f"{f:g}"] = n
            k_needed = at_budget * f ** (-1 / b)
            cells += f"{f'{n:,.0f} (k={k_needed:,.0f})':>18}" if n is not None else f"{'--':>18}"
        report["break_even"][spec] = entry
        click.echo(f"{spec:>7}{b:>7.3f}{c:>7.3f}{c / b:>6.2f}" + cells)
    click.echo(
        "\nAbove that many queries the longer training run is the cheaper way to buy the "
        "same cut, because its cost is paid once. The k in brackets is the budget the same "
        "cut needs; where it exceeds 60 the budget law is being read outside the range it "
        "was measured over, and the step law always is."
    )
    _write(out, report)


def _write(out, report):
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2))
        click.echo(f"\nwrote {out}")


if __name__ == "__main__":
    main()
