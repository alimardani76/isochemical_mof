#!/usr/bin/env python3
"""
Project 17 Figure 3
Gas-, pressure-, and process-dependence of geometry-associated adsorption effects.

Revised clean 4-panel main-text version.

Changes in this revision
------------------------
- Panels A and B:
    * remove direct line-end annotations
    * use compact legends in the lower-right
- Panel C:
    * extend the negative x-range to give small negative bars/labels more room
- Panel D:
    * unchanged

Reads ONLY audited Step 3.5 summary tables.
It does NOT read raw adsorption/process files.

Outputs
-------
figures/Figure_3.pdf
figures/Figure_3.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
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
    / "05_secondary_outcome_atlas"
)
FIGURE_DIR = PROJECT_ROOT / "figures"

ADS_PATH = RESULT_DIR / "secondary_adsorption_mmolg_summary.csv"
PROCESS_PATH = RESULT_DIR / "secondary_process_summary.csv"

AXIS_LABEL_SIZE = 9.8
PANEL_LABEL_SIZE = 18.0


PROCESS_COLORS = {
    "methane-storage": COLORS["primary"],
    "landfill-gas": COLORS["validated"],
    "natural-gas-purification": COLORS["accent"],
    "post-combustion-vsa": COLORS["sensitivity"],
    "pre-combustion-40-40": COLORS["warning"],
    "methane-storage-psa": COLORS["primary"],
    "landfill-gas-vpsa": COLORS["validated"],
}

DISPLAY_NAMES = {
    "methane-storage": "Methane storage",
    "landfill-gas": "Landfill gas",
    "natural-gas-purification": "Natural-gas purification",
    "post-combustion-vsa": "Post-combustion",
    "pre-combustion-40-40": "Pre-combustion",
    "methane-storage-psa": "Methane storage",
    "landfill-gas-vpsa": "Landfill gas",
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


def prepare_adsorption(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()

    for column in (
        "temperature_K",
        "pressure_bar",
        "median_symmetric_relative_effect",
        "median_delta",
        "positive_effect_fraction",
    ):
        out[column] = pd.to_numeric(
            out[column],
            errors="coerce",
        )

    out["relative_effect_pct"] = (
        100.0 * out["median_symmetric_relative_effect"]
    )

    return out


def draw_panel_a(ax, adsorption: pd.DataFrame) -> None:
    contexts = [
        "methane-storage",
        "landfill-gas",
        "natural-gas-purification",
    ]

    subset = adsorption.loc[
        adsorption["guest"].eq("CH4")
        & adsorption["context"].isin(contexts)
    ].copy()

    for context in contexts:
        block = (
            subset.loc[subset["context"].eq(context)]
            .sort_values("pressure_bar")
        )

        if block.empty:
            continue

        x = block["pressure_bar"].to_numpy(dtype=float)
        y = block["relative_effect_pct"].to_numpy(dtype=float)

        ax.plot(
            x,
            y,
            color=PROCESS_COLORS[context],
            marker="o",
            markersize=5.2,
            lw=1.6,
            label=DISPLAY_NAMES[context],
        )

    ax.axhline(
        0,
        color="black",
        lw=0.9,
        ls="--",
        zorder=0,
    )

    ax.set_xscale("log")
    ax.set_xlim(0.006, 120)
    ax.set_ylim(-5.2, 6.0)

    set_axis_titles(
        ax,
        xlabel="Pressure (bar)",
        ylabel="Median relative uptake effect (%)",
    )

    ax.legend(
        loc="upper left",
        frameon=False,
        prop={
            "family": "Arial",
            "weight": "bold",
            "size": 6.2,
        },
        handlelength=1.5,
        handletextpad=0.45,
        borderaxespad=0.35,
        labelspacing=0.35,
    )

    style_axis(ax)
    add_panel_label(ax, "A")


def draw_panel_b(ax, adsorption: pd.DataFrame) -> None:
    contexts = [
        "post-combustion-vsa",
        "natural-gas-purification",
        "landfill-gas",
        "pre-combustion-40-40",
    ]

    subset = adsorption.loc[
        adsorption["guest"].eq("CO2")
        & adsorption["context"].isin(contexts)
    ].copy()

    for context in contexts:
        block = (
            subset.loc[subset["context"].eq(context)]
            .sort_values("pressure_bar")
        )

        if block.empty:
            continue

        x = block["pressure_bar"].to_numpy(dtype=float)
        y = block["relative_effect_pct"].to_numpy(dtype=float)

        ax.plot(
            x,
            y,
            color=PROCESS_COLORS[context],
            marker="o",
            markersize=5.2,
            lw=1.6,
            label=DISPLAY_NAMES[context],
        )

    ax.axhline(
        0,
        color="black",
        lw=0.9,
        ls="--",
        zorder=0,
    )

    ax.set_xscale("log")
    ax.set_xlim(0.01, 35)
    ax.set_ylim(-19.5, 7.0)

    set_axis_titles(
        ax,
        xlabel="Pressure (bar)",
        ylabel="Median relative uptake effect (%)",
    )

    ax.legend(
        loc="lower right",
        frameon=False,
        prop={
            "family": "Arial",
            "weight": "bold",
            "size": 6.0,
        },
        handlelength=1.5,
        handletextpad=0.45,
        borderaxespad=0.35,
        labelspacing=0.32,
    )

    style_axis(ax)
    add_panel_label(ax, "B")


def process_metric(
    process: pd.DataFrame,
    metric: str,
) -> pd.DataFrame:
    block = process.loc[
        process["metric"].eq(metric)
    ].copy()

    for column in (
        "median_delta",
        "positive_effect_fraction",
        "median_symmetric_relative_effect",
    ):
        block[column] = pd.to_numeric(
            block[column],
            errors="coerce",
        )

    return block


def draw_horizontal_process_bars(
    ax,
    process: pd.DataFrame,
    *,
    metric: str,
    processes: list[str],
    xlabel: str,
    panel: str,
    decimals: int,
    xlim: tuple[float, float],
) -> None:
    block = process_metric(process, metric)

    block = block.loc[
        block["process"].isin(processes)
    ].copy()

    order_map = {
        name: i
        for i, name in enumerate(processes)
    }
    block["display_order"] = block["process"].map(order_map)
    block = block.sort_values(
        "display_order",
        ascending=False,
    )

    y = np.arange(len(block))

    values = block["median_delta"].to_numpy(dtype=float)
    colors = [
        PROCESS_COLORS[str(name)]
        for name in block["process"]
    ]

    bars = ax.barh(
        y,
        values,
        color=colors,
        edgecolor="none",
        height=0.62,
    )

    ax.axvline(
        0,
        color="black",
        lw=0.9,
        zorder=0,
    )

    labels = [
        DISPLAY_NAMES[str(name)]
        for name in block["process"]
    ]
    ax.set_yticks(y, labels)

    ax.set_xlim(*xlim)

    set_axis_titles(
        ax,
        xlabel=xlabel,
    )

    span = xlim[1] - xlim[0]
    fmt = f"{{:+.{decimals}f}}"

    for bar, value in zip(bars, values):
        if value >= 0:
            x_text = value + 0.025 * span
            ha = "left"
        else:
            x_text = value - 0.025 * span
            ha = "right"

        ax.text(
            x_text,
            bar.get_y() + bar.get_height() / 2,
            fmt.format(value),
            ha=ha,
            va="center",
            fontsize=6.0,
            fontweight="bold",
            fontfamily="Arial",
            color="black",
            clip_on=False,
        )

    style_axis(ax)
    add_panel_label(ax, panel)


def draw_panel_c(ax, process: pd.DataFrame) -> None:
    draw_horizontal_process_bars(
        ax,
        process,
        metric="mmol/g_working_capacity",
        processes=[
            "methane-storage-psa",
            "landfill-gas-vpsa",
            "natural-gas-purification",
            "post-combustion-vsa",
            "pre-combustion-40-40",
        ],
        xlabel=r"Median working-capacity change (mmol g$^{-1}$)",
        panel="C",
        decimals=2,

        # More room on the negative side so the -0.02 / -0.10
        # bars and their labels do not crowd the zero line/y labels.
        xlim=(-0.32, 0.82),
    )


def draw_panel_d(ax, process: pd.DataFrame) -> None:
    draw_horizontal_process_bars(
        ax,
        process,
        metric="selectivity",
        processes=[
            "landfill-gas-vpsa",
            "natural-gas-purification",
            "post-combustion-vsa",
            "pre-combustion-40-40",
        ],
        xlabel="Median selectivity change",
        panel="D",
        decimals=2,
        xlim=(-5.45, 0.30),
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="replace",
        )

    require_file(ADS_PATH)
    require_file(PROCESS_PATH)

    apply_project17_style()

    adsorption = prepare_adsorption(
        pd.read_csv(ADS_PATH)
    )
    process = pd.read_csv(PROCESS_PATH)

    fig = plt.figure(
        figsize=(7.15, 5.55),
        constrained_layout=False,
    )

    gs = fig.add_gridspec(
        2,
        2,
        left=0.105,
        right=0.945,
        bottom=0.105,
        top=0.965,
        wspace=0.48,
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
        adsorption,
    )
    draw_panel_b(
        axes["B"],
        adsorption,
    )
    draw_panel_c(
        axes["C"],
        process,
    )
    draw_panel_d(
        axes["D"],
        process,
    )

    FIGURE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    pdf_path = FIGURE_DIR / "Figure_3.pdf"
    png_path = FIGURE_DIR / "Figure_3.png"

    save_figure(
        fig,
        pdf_path=pdf_path,
        png_path=png_path,
        dpi=600,
    )

    plt.close(fig)

    print("Project 17 Figure 3 generated")
    print(f"PDF: {pdf_path}")
    print(f"PNG: {png_path}")
    print("A/B legends moved to lower right.")
    print("C negative x-range expanded.")
    print("No raw outcome files were read by this figure script.")
    print("No titles were placed inside the figure.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
