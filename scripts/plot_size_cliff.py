"""The size cliff as one figure: recovery against molecule size, per band.

Every number this project reports about large molecules is a row in a band
table, and band tables are unreadable at a glance. This renders the one picture
those tables are making: recovery at two budgets against heavy-atom count, with
each band's query count on its tick so the thin bands cannot be over-read.

It consumes the same dumps and the same ``hits`` helper ``band_analysis.py``
uses, so the figure cannot drift from the tables it illustrates.

Two files come out, one per theme, for a README or post that serves both with
``<picture>``. Colours are slots 1 and 2 of the house categorical palette, in
fixed order.

    python scripts/plot_size_cliff.py --dumps results/overnight4/outcomes_t06 \
        --run small_1m --subtitle "8M-parameter model, T=0.6"
"""

from __future__ import annotations

from pathlib import Path

import click
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from scripts.band_analysis import heavy_atoms, parse_band  # noqa: E402
from scripts.variance_analysis import hits, load  # noqa: E402

DEFAULT_BANDS = "0-14,15-19,20-24,25-29,30-34,35-39,40-49,50+"

THEMES = {
    "light": {
        "surface": "#ffffff",
        "ink": "#1a1a19",
        "ink2": "#55544d",
        "muted": "#8a897f",
        "grid": "#e6e5e0",
        "high": "#2a78d6",
        "low": "#eb6834",
    },
    "dark": {
        "surface": "#1a1a19",
        "ink": "#f0efec",
        "ink2": "#c3c2b7",
        "muted": "#8a897f",
        "grid": "#343431",
        "high": "#3987e5",
        "low": "#d95926",
    },
}


def band_recovery(dump: Path, budget: str, order: str, k: int, bands: str):
    """Recovery at k per band, plus each band's query count."""
    outcomes = load(dump, budget)
    sizes = [heavy_atoms(o.reference_smiles) for o in outcomes if o.fp_unseen]
    per_query = hits(outcomes, k, order)

    values, counts, labels = [], [], []
    for spec in bands.split(","):
        label, lo, hi = parse_band(spec)
        idx = [i for i, size in enumerate(sizes) if lo <= size <= hi]
        if not idx:
            continue
        values.append(sum(per_query[i] for i in idx) / len(idx))
        counts.append(len(idx))
        # "50+" is really 50-64: prepare.py caps heavy atoms at 64, and a label
        # that hides the cap invites exactly the over-reading this repo keeps
        # correcting.
        labels.append("50–64" if hi > 64 else label.replace("-", "–"))
    return values, counts, labels


def render(theme_name, theme, high, low, counts, labels, k_high, k_low, subtitle, out_dir):
    x = range(len(labels))
    fig, ax = plt.subplots(figsize=(8.2, 4.6), dpi=200)
    fig.patch.set_facecolor(theme["surface"])
    ax.set_facecolor(theme["surface"])

    ax.yaxis.grid(True, color=theme["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(theme["grid"])

    for values, colour, label in (
        (high, theme["high"], f"recovery@{k_high}"),
        (low, theme["low"], f"recovery@{k_low}"),
    ):
        ax.plot(x, values, color=colour, linewidth=2, zorder=3)
        ax.plot(
            x,
            values,
            "o",
            color=colour,
            markersize=8,
            markeredgecolor=theme["surface"],
            markeredgewidth=2,
            zorder=4,
            label=label,
        )
        # The last band is the story; a number on every point is noise.
        ax.annotate(
            f"{values[-1]:.0%}",
            (len(labels) - 1, values[-1]),
            textcoords="offset points",
            xytext=(0, 13 if values is high else -20),
            ha="center",
            color=colour,
            fontsize=10,
            fontweight="bold",
        )

    ax.set_ylim(0, 1.06)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0", "25%", "50%", "75%", "100%"], color=theme["ink2"], fontsize=9)
    ax.set_xticks(list(x))
    ax.set_xticklabels(
        [f"{lab}\nn={n}" for lab, n in zip(labels, counts, strict=True)],
        color=theme["ink2"],
        fontsize=9,
    )
    ax.tick_params(length=0)
    ax.set_xlabel("heavy atoms", color=theme["ink2"], fontsize=10, labelpad=6)

    ax.set_title(
        "Recovery collapses with molecule size",
        color=theme["ink"],
        fontsize=14,
        fontweight="bold",
        loc="left",
        pad=26,
    )
    ax.text(
        0,
        1.045,
        subtitle,
        transform=ax.transAxes,
        color=theme["muted"],
        fontsize=9.5,
        va="bottom",
    )

    legend = ax.legend(
        loc="lower left", frameon=False, fontsize=10, handletextpad=0.6, borderaxespad=0.2
    )
    for text in legend.get_texts():
        text.set_color(theme["ink2"])

    fig.tight_layout()
    path = out_dir / f"size-cliff-{theme_name}.png"
    fig.savefig(path, facecolor=theme["surface"])
    plt.close(fig)
    return path


@click.command()
@click.option("--dumps", type=click.Path(path_type=Path), required=True)
@click.option("--run", required=True, help="Which run's dump in --dumps to plot.")
@click.option("--bands", default=DEFAULT_BANDS, show_default=True)
@click.option("--budget", default="molecules")
@click.option("--order", default="consensus", type=click.Choice(["generation", "consensus"]))
@click.option("--k-high", default=20, show_default=True)
@click.option("--k-low", default=1, show_default=True)
@click.option("--subtitle", default="", help="Protocol line under the title.")
@click.option(
    "--out-dir", type=click.Path(path_type=Path), default=Path("docs/images"), show_default=True
)
def main(dumps, run, bands, budget, order, k_high, k_low, subtitle, out_dir):
    dump = dumps / f"{run}.jsonl"
    if not dump.exists():
        raise click.ClickException(f"no dump at {dump}")

    high, counts, labels = band_recovery(dump, budget, order, k_high, bands)
    low, _, _ = band_recovery(dump, budget, order, k_low, bands)

    out_dir.mkdir(parents=True, exist_ok=True)
    line = subtitle or f"{run}, {sum(counts):,} fingerprint-unseen queries"
    for name, theme in THEMES.items():
        path = render(name, theme, high, low, counts, labels, k_high, k_low, line, out_dir)
        click.echo(f"wrote {path}")

    for label, n, hi, lo in zip(labels, counts, high, low, strict=True):
        click.echo(f"  {label:>7s}  n={n:4d}  rec@{k_high}={hi:.4f}  rec@{k_low}={lo:.4f}")


if __name__ == "__main__":
    main()
