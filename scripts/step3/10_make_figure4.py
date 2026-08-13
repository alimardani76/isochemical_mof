#!/usr/bin/env python3
"""
Project 17 Figure 4
Pressure-response archetypes and heterogeneity.

Reads ONLY audited Step 3.7 outputs.
No raw outcome files are read.

Panels
------
A  Pair-level low-pressure vs high-pressure positive-response fractions.
B  Overall response-archetype prevalence.
C  Archetype composition by frozen geometry driver.
D  Pressure-activated fraction across well-supported topologies (n >= 100).

No titles are placed inside panels.

Outputs
-------
figures/Figure_4.pdf
figures/Figure_4.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

from figure_style import (
    COLORS,
    apply_project17_style,
    save_figure,
    style_axis,
)


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

RESULT_DIR = (
    PROJECT_ROOT
    / "Step 3 results"
    / "07_response_archetypes"
)
FIGURE_DIR = PROJECT_ROOT / "figures"

ARCHETYPE_PATH = RESULT_DIR / "response_archetypes.parquet"
SUMMARY_PATH = RESULT_DIR / "response_archetype_summary.csv"
DRIVER_PATH = RESULT_DIR / "response_archetype_driver_summary.csv"
TOPOLOGY_PATH = RESULT_DIR / "response_archetype_topology_summary.csv"

AXIS_LABEL_SIZE = 9.8
PANEL_LABEL_SIZE = 18.0


ARCHETYPE_ORDER = [
    "positive_both",
    "pressure_activated",
    "pressure_suppressed",
    "negative_both",
]

ARCHETYPE_LABELS = {
    "positive_both": "Positive both",
    "pressure_activated": "Pressure activated",
    "pressure_suppressed": "Pressure suppressed",
    "negative_both": "Negative both",
}

ARCHETYPE_COLORS = {
    "positive_both": COLORS["primary"],
    "pressure_activated": COLORS["accent"],
    "pressure_suppressed": COLORS["sensitivity"],
    "negative_both": COLORS["neutral"],
}

DRIVER_ORDER = [
    "ASA",
    "AVA",
    "AVAf",
    "POAVA",
    "POAVAf",
    "Df",
    "Di",
    "Dif",
]

DRIVER_LABELS = {
    "ASA": "ASA",
    "AVA": "AVA",
    "AVAf": "AVAf",
    "POAVA": "POAVA",
    "POAVAf": "POAVAf",
    "Df": r"$D_f$",
    "Di": r"$D_i$",
    "Dif": r"$D_{\mathrm{if}}$",
}


def require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)


def add_panel_label(
    ax,
    label: str,
    *,
    x: float = -0.10,
    y: float = 1.055,
) -> None:
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


def draw_panel_a(ax, archetypes: pd.DataFrame) -> None:
    x = pd.to_numeric(
        archetypes["positive_fraction_low_pressure"],
        errors="raise",
    ).to_numpy(dtype=float)

    y = pd.to_numeric(
        archetypes["positive_fraction_high_pressure"],
        errors="raise",
    ).to_numpy(dtype=float)

    bins = np.linspace(-0.055, 1.055, 11)

    counts, xedges, yedges = np.histogram2d(
        x,
        y,
        bins=[bins, bins],
    )

    positive_counts = counts[counts > 0]
    vmin = max(1, float(positive_counts.min()))
    vmax = float(positive_counts.max())

    mesh = ax.pcolormesh(
        xedges,
        yedges,
        counts.T,
        cmap="Blues",
        norm=LogNorm(vmin=vmin, vmax=vmax),
        shading="flat",
        edgecolors="white",
        linewidth=0.35,
    )

    ax.plot(
        [0, 1],
        [0, 1],
        color="black",
        lw=1.0,
        ls="--",
    )

    ax.axvline(
        0.5,
        color=COLORS["light"],
        lw=0.8,
    )
    ax.axhline(
        0.5,
        color=COLORS["light"],
        lw=0.8,
    )

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    ax.set_xticks(
        [0, 0.25, 0.5, 0.75, 1.0],
        ["0", "25", "50", "75", "100"],
    )
    ax.set_yticks(
        [0, 0.25, 0.5, 0.75, 1.0],
        ["0", "25", "50", "75", "100"],
    )

    set_axis_titles(
        ax,
        xlabel="Positive endpoints at low pressure (%)",
        ylabel="Positive endpoints at high pressure (%)",
    )

    cbar = ax.figure.colorbar(
        mesh,
        ax=ax,
        fraction=0.046,
        pad=0.025,
    )
    cbar.set_label(
        "Pairs",
        fontsize=7.0,
        fontweight="bold",
        fontfamily="Arial",
    )
    cbar.ax.tick_params(labelsize=6.2)

    for label in cbar.ax.get_yticklabels():
        label.set_fontweight("bold")
        label.set_fontfamily("Arial")

    style_axis(ax)
    add_panel_label(ax, "A")


def draw_panel_b(ax, summary: pd.DataFrame) -> None:
    summary = summary.copy()

    summary["archetype"] = pd.Categorical(
        summary["archetype"],
        categories=ARCHETYPE_ORDER,
        ordered=True,
    )
    summary = summary.sort_values("archetype")

    x = np.arange(len(summary))

    pairs = pd.to_numeric(
        summary["pairs"],
        errors="raise",
    ).to_numpy(dtype=int)

    fractions = (
        100.0
        * pd.to_numeric(
            summary["fraction"],
            errors="raise",
        ).to_numpy(dtype=float)
    )

    colors = [
        ARCHETYPE_COLORS[str(a)]
        for a in summary["archetype"]
    ]

    bars = ax.bar(
        x,
        fractions,
        width=0.64,
        color=colors,
        edgecolor="none",
    )

    ax.set_xticks(
        x,
        [
            "Positive\nboth",
            "Pressure\nactivated",
            "Pressure\nsuppressed",
            "Negative\nboth",
        ],
    )

    set_axis_titles(
        ax,
        ylabel="Frozen pairs (%)",
    )

    ymax = float(fractions.max())
    ax.set_ylim(0, ymax * 1.22)

    for bar, pct, n in zip(
        bars,
        fractions,
        pairs,
    ):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            pct + ymax * 0.035,
            f"{pct:.1f}%\nn={n:,}",
            ha="center",
            va="bottom",
            fontsize=6.2,
            fontweight="bold",
            fontfamily="Arial",
            color="black",
            linespacing=1.05,
        )

    style_axis(ax)
    add_panel_label(ax, "B")


def draw_panel_c(ax, driver: pd.DataFrame) -> None:
    driver = driver.copy()

    driver = driver.loc[
        driver["driver_descriptor"].isin(DRIVER_ORDER)
    ].copy()

    order_map = {
        name: i
        for i, name in enumerate(DRIVER_ORDER)
    }
    driver["display_order"] = driver[
        "driver_descriptor"
    ].map(order_map)

    driver = driver.sort_values(
        "display_order",
        ascending=False,
    )

    y = np.arange(len(driver))
    left = np.zeros(len(driver), dtype=float)

    fraction_columns = {
        "positive_both": "positive_both_fraction",
        "pressure_activated": "pressure_activated_fraction",
        "pressure_suppressed": "pressure_suppressed_fraction",
        "negative_both": "negative_both_fraction",
    }

    for archetype in ARCHETYPE_ORDER:
        values = (
            100.0
            * pd.to_numeric(
                driver[fraction_columns[archetype]],
                errors="raise",
            ).to_numpy(dtype=float)
        )

        ax.barh(
            y,
            values,
            left=left,
            height=0.66,
            color=ARCHETYPE_COLORS[archetype],
            edgecolor="white",
            linewidth=0.35,
        )

        left += values

    labels = [
        f"{DRIVER_LABELS[str(row.driver_descriptor)]} "
        f"(n={int(row.pairs):,})"
        for row in driver.itertuples(index=False)
    ]

    ax.set_yticks(
        y,
        labels,
    )

    ax.set_xlim(0, 100)

    set_axis_titles(
        ax,
        xlabel="Archetype composition (%)",
    )

    legend_handles = [
        Patch(
            facecolor=ARCHETYPE_COLORS[name],
            edgecolor="none",
            label=ARCHETYPE_LABELS[name],
        )
        for name in ARCHETYPE_ORDER
    ]

    ax.legend(
        handles=legend_handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.005),
        ncol=2,
        frameon=False,
        prop={
            "family": "Arial",
            "weight": "bold",
            "size": 5.7,
        },
        handlelength=1.2,
        handletextpad=0.4,
        columnspacing=0.8,
        borderaxespad=0.2,
    )

    style_axis(ax)
    add_panel_label(ax, "C")


def draw_panel_d(
    ax,
    topology: pd.DataFrame,
    overall_pressure_activated_fraction: float,
) -> None:
    """
    Show whether pressure activation depends on topology.

    To keep this main-text panel defensible and uncluttered, retain only
    topologies represented by at least 100 frozen pairs.
    """
    data = topology.copy()

    data["pairs"] = pd.to_numeric(
        data["pairs"],
        errors="raise",
    ).astype(int)

    data["pressure_activated_fraction"] = pd.to_numeric(
        data["pressure_activated_fraction"],
        errors="raise",
    )

    data = data.loc[
        data["pairs"] >= 100
    ].copy()

    # Sort by pressure-activated fraction so the topology effect is obvious.
    data = data.sort_values(
        "pressure_activated_fraction",
        ascending=True,
    ).reset_index(drop=True)

    y = np.arange(len(data))

    values = (
        100.0
        * data["pressure_activated_fraction"].to_numpy(dtype=float)
    )

    overall_pct = 100.0 * overall_pressure_activated_fraction

    bars = ax.barh(
        y,
        values,
        color=COLORS["accent"],
        edgecolor="none",
        height=0.62,
    )

    ax.axvline(
        overall_pct,
        color="black",
        lw=1.0,
        ls="--",
        zorder=0,
    )

    labels = [
        f"{str(row.topology)} (n={int(row.pairs):,})"
        for row in data.itertuples(index=False)
    ]

    ax.set_yticks(
        y,
        labels,
    )

    xmax = max(
        40.0,
        float(values.max()) * 1.20,
    )
    ax.set_xlim(0, xmax)

    set_axis_titles(
        ax,
        xlabel="Pressure-activated pairs (%)",
    )

    for bar, value in zip(bars, values):
        ax.text(
            value + xmax * 0.018,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.1f}%",
            ha="left",
            va="center",
            fontsize=6.2,
            fontweight="bold",
            fontfamily="Arial",
            color="black",
        )

    ax.text(
        overall_pct,
        1.02,
        f"overall = {overall_pct:.1f}%",
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="bottom",
        fontsize=6.0,
        fontweight="bold",
        fontfamily="Arial",
        color="black",
        clip_on=False,
    )

    style_axis(ax)
    add_panel_label(ax, "D")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="replace",
        )

    for path in (
        ARCHETYPE_PATH,
        SUMMARY_PATH,
        DRIVER_PATH,
        TOPOLOGY_PATH,
    ):
        require_file(path)

    apply_project17_style()

    archetypes = pd.read_parquet(
        ARCHETYPE_PATH
    )
    summary = pd.read_csv(
        SUMMARY_PATH
    )
    driver = pd.read_csv(
        DRIVER_PATH
    )
    topology = pd.read_csv(
        TOPOLOGY_PATH
    )

    pressure_activated_row = summary.loc[
        summary["archetype"].eq("pressure_activated")
    ]

    if len(pressure_activated_row) != 1:
        raise RuntimeError(
            "pressure_activated summary row is not unique"
        )

    overall_pressure_activated_fraction = float(
        pressure_activated_row.iloc[0]["fraction"]
    )

    fig = plt.figure(
        figsize=(7.15, 5.9),
        constrained_layout=False,
    )

    gs = fig.add_gridspec(
        2,
        2,
        left=0.10,
        right=0.975,
        bottom=0.095,
        top=0.96,
        wspace=0.43,
        hspace=0.48,
        height_ratios=[1.0, 1.0],
    )

    axes = {
        "A": fig.add_subplot(gs[0, 0]),
        "B": fig.add_subplot(gs[0, 1]),
        "C": fig.add_subplot(gs[1, 0]),
        "D": fig.add_subplot(gs[1, 1]),
    }

    draw_panel_a(
        axes["A"],
        archetypes,
    )
    draw_panel_b(
        axes["B"],
        summary,
    )
    draw_panel_c(
        axes["C"],
        driver,
    )
    draw_panel_d(
        axes["D"],
        topology,
        overall_pressure_activated_fraction,
    )

    FIGURE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    pdf_path = FIGURE_DIR / "Figure_4.pdf"
    png_path = FIGURE_DIR / "Figure_4.png"

    save_figure(
        fig,
        pdf_path=pdf_path,
        png_path=png_path,
        dpi=600,
    )

    plt.close(fig)

    print("Project 17 Figure 4 generated")
    print(f"PDF: {pdf_path}")
    print(f"PNG: {png_path}")
    print("Panel D: pressure-activated fraction by topology, n >= 100.")
    print("No raw outcome files were read.")
    print("No titles were placed inside the figure.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
