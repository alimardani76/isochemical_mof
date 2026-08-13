#!/usr/bin/env python3
"""
Project 17 Figure 1
Outcome-blind construction and support of the frozen geometry-pair cohort.

This script reads only already-frozen Stage 2 result tables.
It does NOT read adsorption/process outcomes.

Panels
------
A  Cohort flow from ARC-MOF registry to frozen primary pairs.
B  Distribution of strongest within-family pore span with frozen 10% threshold.
C  Family support retained at 5%, 10%, 20%, and 30%.
D  Driver descriptor of the selected frozen pair.
E  Geometry strength of the selected pair: maximum vs mean pore difference.
F  Topology representation among frozen primary pairs.

No titles are placed inside the figure.

Outputs
-------
figures/Figure_1.pdf
figures/Figure_1.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd

from figure_style import (
    COLORS,
    THRESHOLD_COLORS,
    apply_project17_style,
    save_figure,
    style_axis,
)


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

STEP22_DIR = PROJECT_ROOT / "Step 2 results" / "02_geometry_threshold_census"
STEP23_DIR = PROJECT_ROOT / "Step 2 results" / "03_geometry_pairs"
FIGURE_DIR = PROJECT_ROOT / "figures"

FAMILY_PATH = STEP22_DIR / "geometry_threshold_families.parquet"
THRESHOLD_CENSUS_PATH = STEP22_DIR / "geometry_threshold_census.csv"
PAIR_PATH = STEP23_DIR / "primary_geometry_pairs.parquet"
DRIVER_PATH = STEP23_DIR / "primary_pair_driver_census.csv"


FROZEN_COHORT = [
    ("ARC-MOF registry", 279_019),
    ("Charged CIFs parsed", 242_363),
    ("Same-chemistry candidates", 48_366),
    ("Same architecture", 44_511),
    ("10% geometry eligible", 26_146),
    ("Frozen primary pairs", 11_072),
]


# Requested Figure-1 typography changes.
# Previous general text/axis labels were ~7 pt.
AXIS_LABEL_SIZE = 9.8       # 1.4 x; ticks are deliberately unchanged
PANEL_LABEL_SIZE = 18.0     # ~2 x previous 9-pt panel letters


def require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)


def comma_formatter(x, _pos=None):
    return f"{int(round(x)):,}"


def add_panel_label(
    ax,
    label: str,
    *,
    x: float = -0.105,
    y: float = 1.055,
) -> None:
    """Large uppercase bold panel label."""
    ax.text(
        x,
        y,
        label.upper(),
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=PANEL_LABEL_SIZE,
        fontweight="bold",
        fontfamily="Arial",
        color="black",
        clip_on=False,
    )


def set_axis_titles(ax, *, xlabel=None, ylabel=None) -> None:
    """
    Increase axis TITLES only.
    Tick-label sizes remain whatever figure_style.py specifies.
    """
    if xlabel is not None:
        ax.set_xlabel(
            xlabel,
            fontsize=AXIS_LABEL_SIZE,
            fontweight="bold",
            fontfamily="Arial",
            color="black",
        )
    if ylabel is not None:
        ax.set_ylabel(
            ylabel,
            fontsize=AXIS_LABEL_SIZE,
            fontweight="bold",
            fontfamily="Arial",
            color="black",
        )


def draw_panel_a(ax) -> None:
    """Moderate-width funnel for the frozen cohort."""
    ax.set_axis_off()

    n = len(FROZEN_COHORT)
    ys = np.linspace(0.90, 0.10, n)

    # Moderate funnel: obvious narrowing, but not a sharp triangle.
    widths = [0.84, 0.80, 0.76, 0.72, 0.68, 0.64]

    # Each stage has a distinct colour, while staying in the shared
    # colour-blind-safe Project 17 palette.
    stage_colors = [
        "#111111",               # source population: true black
        COLORS["secondary"],     # parsed structures: sky blue
        COLORS["accent"],        # chemistry candidates: orange
        COLORS["validated"],     # validated architecture: green
        COLORS["sensitivity"],   # geometry eligibility: purple
        COLORS["primary"],       # frozen primary pairs: blue
    ]

    box_height = 0.108
    center_x = 0.50

    for i, ((label, count), y, width, color) in enumerate(
        zip(FROZEN_COHORT, ys, widths, stage_colors)
    ):
        left = center_x - width / 2

        box = FancyBboxPatch(
            (left, y - box_height / 2),
            width,
            box_height,
            boxstyle="round,pad=0.012,rounding_size=0.018",
            transform=ax.transAxes,
            facecolor=color,
            edgecolor="none",
        )
        ax.add_patch(box)

        ax.text(
            center_x,
            y + 0.014,
            f"{count:,}",
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=8.3,
            fontweight="bold",
            fontfamily="Arial",
            color="white",
        )
        ax.text(
            center_x,
            y - 0.022,
            label,
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=6.1,
            fontweight="bold",
            fontfamily="Arial",
            color="white",
        )

        if i < n - 1:
            y_next = ys[i + 1]
            ax.annotate(
                "",
                xy=(center_x, y_next + box_height / 2 + 0.004),
                xytext=(center_x, y - box_height / 2 - 0.004),
                xycoords=ax.transAxes,
                textcoords=ax.transAxes,
                arrowprops=dict(
                    arrowstyle="-|>",
                    lw=0.9,
                    color="#555555",
                    shrinkA=0,
                    shrinkB=0,
                    mutation_scale=8,
                ),
            )

    add_panel_label(ax, "A", x=-0.045, y=1.015)


def draw_panel_b(ax, families: pd.DataFrame) -> None:
    values = (
        pd.to_numeric(
            families["max_pore_fractional_span"],
            errors="raise",
        )
        .clip(lower=0, upper=1.0)
        .to_numpy()
        * 100.0
    )

    bins = np.linspace(0, 100, 41)

    ax.hist(
        values,
        bins=bins,
        color=COLORS["secondary"],
        edgecolor="white",
        linewidth=0.35,
    )

    # Only the frozen primary threshold remains.
    ax.axvline(
        10,
        color="black",
        lw=1.5,
        zorder=5,
    )

    # Direct annotation replaces the legend entirely.
    ymax = ax.get_ylim()[1]
    ax.annotate(
        "10% frozen threshold",
        xy=(10, ymax * 0.80),
        xytext=(16.5, ymax * 0.91),
        ha="left",
        va="center",
        fontsize=6.5,
        fontweight="bold",
        fontfamily="Arial",
        color="black",
        arrowprops=dict(
            arrowstyle="-",
            color="black",
            lw=0.8,
        ),
    )

    set_axis_titles(
        ax,
        xlabel="Maximum within-family pore span (%)",
        ylabel="Families",
    )
    ax.set_xlim(0, 100)
    ax.yaxis.set_major_formatter(FuncFormatter(comma_formatter))

    style_axis(ax)
    add_panel_label(ax, "B")


def draw_panel_c(ax, census: pd.DataFrame) -> None:
    census = census.copy()
    census["threshold_percent"] = pd.to_numeric(
        census["threshold_percent"],
        errors="raise",
    ).astype(int)
    census["eligible_families"] = pd.to_numeric(
        census["eligible_families"],
        errors="raise",
    ).astype(int)
    census["eligible_frameworks"] = pd.to_numeric(
        census["eligible_frameworks"],
        errors="raise",
    ).astype(int)

    census = census.sort_values("threshold_percent")
    x = np.arange(len(census))

    colors = [
        THRESHOLD_COLORS[int(t)]
        for t in census["threshold_percent"]
    ]

    bars = ax.bar(
        x,
        census["eligible_families"],
        color=colors,
        width=0.64,
        edgecolor="none",
    )

    ax.set_xticks(
        x,
        [f"{t}%" for t in census["threshold_percent"]],
    )
    set_axis_titles(
        ax,
        xlabel="Candidate pore-geometry threshold",
        ylabel="Eligible families",
    )
    ax.yaxis.set_major_formatter(FuncFormatter(comma_formatter))

    ymax = census["eligible_families"].max()
    ax.set_ylim(0, ymax * 1.18)
    ax.margins(x=0.075)

    # All annotations are black and placed above the bars.
    for bar, family_count, framework_count in zip(
        bars,
        census["eligible_families"],
        census["eligible_frameworks"],
    ):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + ymax * 0.022,
            f"{family_count:,}\n({framework_count:,} frameworks)",
            ha="center",
            va="bottom",
            fontsize=5.6,
            fontweight="bold",
            fontfamily="Arial",
            color="black",
            linespacing=1.05,
            clip_on=False,
        )

    style_axis(ax)
    # A touch farther left/up than before so the large C stays clear of the axis.
    add_panel_label(ax, "C", x=-0.125, y=1.065)


def draw_panel_d(ax, driver: pd.DataFrame) -> None:
    driver = driver.copy()
    driver["selected_pairs"] = pd.to_numeric(
        driver["selected_pairs"],
        errors="raise",
    ).astype(int)

    driver = driver.sort_values(
        "selected_pairs",
        ascending=True,
    )

    y = np.arange(len(driver))

    bars = ax.barh(
        y,
        driver["selected_pairs"],
        color=COLORS["primary"],
        edgecolor="none",
        height=0.68,
    )

    pretty = {
        "Di": r"$D_i$",
        "Df": r"$D_f$",
        "Dif": r"$D_{\mathrm{if}}$",
        "ASA": "ASA",
        "AVA": "AVA",
        "AVAf": "AVAf",
        "POAVA": "POAVA",
        "POAVAf": "POAVAf",
    }

    labels = [
        pretty.get(str(value), str(value))
        for value in driver["driver_descriptor"]
    ]

    ax.set_yticks(y, labels)
    set_axis_titles(
        ax,
        xlabel="Frozen primary pairs",
    )
    ax.xaxis.set_major_formatter(FuncFormatter(comma_formatter))

    xmax = driver["selected_pairs"].max()
    ax.set_xlim(0, xmax * 1.16)

    for bar, count in zip(bars, driver["selected_pairs"]):
        ax.text(
            count + xmax * 0.018,
            bar.get_y() + bar.get_height() / 2,
            f"{count:,}",
            ha="left",
            va="center",
            fontsize=5.8,
            fontweight="bold",
            fontfamily="Arial",
            color="black",
        )

    style_axis(ax)
    add_panel_label(ax, "D")


def draw_panel_e(ax, pairs: pd.DataFrame) -> None:
    x = (
        pd.to_numeric(
            pairs["pair_max_fractional_difference"],
            errors="raise",
        ).to_numpy()
        * 100.0
    )
    y = (
        pd.to_numeric(
            pairs["pair_mean_fractional_difference"],
            errors="raise",
        ).to_numpy()
        * 100.0
    )

    ax.scatter(
        x,
        y,
        s=5,
        alpha=0.18,
        color=COLORS["primary"],
        edgecolors="none",
        rasterized=True,
    )

    median_x = float(np.median(x))
    median_y = float(np.median(y))

    ax.axvline(
        median_x,
        color=COLORS["neutral"],
        lw=0.9,
        ls="--",
    )
    ax.axhline(
        median_y,
        color=COLORS["neutral"],
        lw=0.9,
        ls="--",
    )

    ax.text(
        0.98,
        0.04,
        f"medians: {median_x:.1f}% / {median_y:.1f}%",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=5.8,
        fontweight="bold",
        fontfamily="Arial",
        color="black",
    )

    set_axis_titles(
        ax,
        xlabel="Maximum pair difference (%)",
        ylabel="Mean pair difference (%)",
    )
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)

    style_axis(ax)
    add_panel_label(ax, "E")


def draw_panel_f(ax, pairs: pd.DataFrame) -> None:
    if "topology" not in pairs.columns:
        raise KeyError(
            "primary_geometry_pairs.parquet must contain a 'topology' column"
        )

    counts = (
        pairs["topology"]
        .astype("string")
        .fillna("missing")
        .value_counts()
    )

    top_n = 10
    top = counts.head(top_n).copy()
    other_count = int(counts.iloc[top_n:].sum())

    if other_count > 0:
        top.loc["Other"] = other_count

    top = top.sort_values(ascending=True)

    y = np.arange(len(top))
    colors = [
        COLORS["light"] if label == "Other" else COLORS["validated"]
        for label in top.index
    ]

    bars = ax.barh(
        y,
        top.values,
        color=colors,
        edgecolor="none",
        height=0.68,
    )

    ax.set_yticks(y, [str(value) for value in top.index])
    set_axis_titles(
        ax,
        xlabel="Frozen primary pairs",
    )
    ax.xaxis.set_major_formatter(FuncFormatter(comma_formatter))

    xmax = max(top.values)
    ax.set_xlim(0, xmax * 1.16)

    for bar, count in zip(bars, top.values):
        ax.text(
            count + xmax * 0.018,
            bar.get_y() + bar.get_height() / 2,
            f"{int(count):,}",
            ha="left",
            va="center",
            fontsize=5.6,
            fontweight="bold",
            fontfamily="Arial",
            color="black",
        )

    style_axis(ax)
    add_panel_label(ax, "F")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    for path in (
        FAMILY_PATH,
        THRESHOLD_CENSUS_PATH,
        PAIR_PATH,
        DRIVER_PATH,
    ):
        require_file(path)

    apply_project17_style()

    families = pd.read_parquet(FAMILY_PATH)
    census = pd.read_csv(THRESHOLD_CENSUS_PATH)
    pairs = pd.read_parquet(PAIR_PATH)
    driver = pd.read_csv(DRIVER_PATH)

    required_family = {"max_pore_fractional_span"}
    required_pair = {
        "pair_max_fractional_difference",
        "pair_mean_fractional_difference",
        "topology",
    }
    required_driver = {"driver_descriptor", "selected_pairs"}

    if not required_family.issubset(families.columns):
        raise KeyError(
            f"Missing family columns: "
            f"{sorted(required_family - set(families.columns))}"
        )
    if not required_pair.issubset(pairs.columns):
        raise KeyError(
            f"Missing pair columns: "
            f"{sorted(required_pair - set(pairs.columns))}"
        )
    if not required_driver.issubset(driver.columns):
        raise KeyError(
            f"Missing driver columns: "
            f"{sorted(required_driver - set(driver.columns))}"
        )

    fig = plt.figure(
        figsize=(7.15, 8.05),
        constrained_layout=False,
    )

    gs = fig.add_gridspec(
        3,
        2,
        left=0.075,
        right=0.985,
        bottom=0.065,
        top=0.975,
        wspace=0.34,
        hspace=0.44,
        height_ratios=[1.16, 1.0, 1.0],
    )

    axes = {
        "A": fig.add_subplot(gs[0, 0]),
        "B": fig.add_subplot(gs[0, 1]),
        "C": fig.add_subplot(gs[1, 0]),
        "D": fig.add_subplot(gs[1, 1]),
        "E": fig.add_subplot(gs[2, 0]),
        "F": fig.add_subplot(gs[2, 1]),
    }

    draw_panel_a(axes["A"])
    draw_panel_b(axes["B"], families)
    draw_panel_c(axes["C"], census)
    draw_panel_d(axes["D"], driver)
    draw_panel_e(axes["E"], pairs)
    draw_panel_f(axes["F"], pairs)

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    pdf_path = FIGURE_DIR / "Figure_1.pdf"
    png_path = FIGURE_DIR / "Figure_1.png"

    save_figure(
        fig,
        pdf_path=pdf_path,
        png_path=png_path,
        dpi=600,
    )

    plt.close(fig)

    print("Project 17 Figure 1 generated")
    print(f"PDF: {pdf_path}")
    print(f"PNG: {png_path}")
    print("No adsorption/process outcome values were read.")
    print("No titles were placed inside the figure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
