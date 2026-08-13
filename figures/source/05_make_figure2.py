#!/usr/bin/env python3
"""
Project 17 Figure 2, revision 3

Changes from v2
---------------
- Panel A: raise panel label slightly to align better with panel B.
- Panel A: move legend to lower right and enlarge markers/text.
- Panel C: remove the median-effect number from bar annotations; keep only
  positive fraction and n, and enlarge the annotation text.
- Panel D: place negative-bar annotations on the positive side of the zero line.
- Panel E: add a legend explaining the shaded band and the point/line series.

Reads only audited Step 3.4 outputs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
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

RESULT_DIR = PROJECT_ROOT / "Step 3 results" / "04_primary_ch4_analysis"
FIGURE_DIR = PROJECT_ROOT / "figures"

PAIR_EFFECT_PATH = RESULT_DIR / "primary_ch4_pair_effects.parquet"
SUMMARY_PATH = RESULT_DIR / "primary_ch4_summary.csv"
TIER_PATH = RESULT_DIR / "primary_ch4_geometry_tier_summary.csv"
DRIVER_PATH = RESULT_DIR / "primary_ch4_driver_summary.csv"
TOPOLOGY_PATH = RESULT_DIR / "primary_ch4_topology_summary.csv"
BOOTSTRAP_PATH = RESULT_DIR / "primary_ch4_bootstrap_medians.csv"

AXIS_LABEL_SIZE = 9.8
PANEL_LABEL_SIZE = 18.0


def require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)


def add_panel_label(
    ax,
    label: str,
    *,
    x: float = -0.085,
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


def summary_dict(summary: pd.DataFrame) -> dict[str, float]:
    return {
        str(row["metric"]): float(row["value"])
        for _, row in summary.iterrows()
    }


def draw_panel_a(ax, effects: pd.DataFrame, summary: dict[str, float]) -> None:
    q_low = effects["q_geometry_low_mmol_g"].to_numpy(dtype=float)
    q_high = effects["q_geometry_high_mmol_g"].to_numpy(dtype=float)
    delta = effects["delta_q_mmol_g"].to_numpy(dtype=float)

    positive = delta > 0
    negative = delta < 0

    ax.scatter(
        q_low[negative],
        q_high[negative],
        s=5,
        alpha=0.22,
        color=COLORS["warning"],
        edgecolors="none",
        rasterized=True,
        zorder=2,
    )
    ax.scatter(
        q_low[positive],
        q_high[positive],
        s=5,
        alpha=0.18,
        color=COLORS["primary"],
        edgecolors="none",
        rasterized=True,
        zorder=3,
    )

    xy_max = float(max(np.nanmax(q_low), np.nanmax(q_high)))
    identity_max = xy_max * 1.02

    ax.plot(
        [0, identity_max],
        [0, identity_max],
        color="black",
        lw=1.0,
        ls="--",
        zorder=1,
    )

    ax.set_xlim(0, identity_max)
    ax.set_ylim(0, identity_max)

    set_axis_titles(
        ax,
        xlabel=r"Geometry-low CH$_4$ uptake (mmol g$^{-1}$)",
        ylabel=r"Geometry-high CH$_4$ uptake (mmol g$^{-1}$)",
    )

    handles = [
        Line2D(
            [0], [0],
            marker="o",
            linestyle="none",
            markerfacecolor=COLORS["primary"],
            markeredgecolor="none",
            markersize=7.5,
            label=f"Increase ({100*summary['positive_effect_fraction']:.1f}%)",
        ),
        Line2D(
            [0], [0],
            marker="o",
            linestyle="none",
            markerfacecolor=COLORS["warning"],
            markeredgecolor="none",
            markersize=7.5,
            label=f"Decrease ({100*summary['negative_effect_fraction']:.1f}%)",
        ),
    ]
    ax.legend(
        handles=handles,
        loc="lower right",
        frameon=False,
        borderaxespad=0.35,
        handlelength=0.8,
        prop={
            "family": "Arial",
            "weight": "bold",
            "size": 9.0,
        },
    )

    style_axis(ax)
    add_panel_label(ax, "A", x=-0.02, y=1.07)


def draw_panel_b(ax, bootstrap: pd.DataFrame, summary: dict[str, float]) -> None:
    values = bootstrap["bootstrap_median_delta_q_mmol_g"].to_numpy(dtype=float)

    median = summary["median_delta_q_mmol_g"]
    ci_low = summary["bootstrap_95ci_low_median_delta_q_mmol_g"]
    ci_high = summary["bootstrap_95ci_high_median_delta_q_mmol_g"]

    ax.hist(
        values,
        bins=45,
        color=COLORS["secondary"],
        edgecolor="white",
        linewidth=0.35,
    )

    ax.axvline(median, color="black", lw=1.5, zorder=4)
    ax.axvline(ci_low, color=COLORS["neutral"], lw=1.0, ls="--", zorder=4)
    ax.axvline(ci_high, color=COLORS["neutral"], lw=1.0, ls="--", zorder=4)

    ymax = ax.get_ylim()[1]
    y_text = ymax * 0.94

    ax.text(
        ci_low,
        y_text,
        "0.05",
        ha="right",
        va="top",
        fontsize=6.2,
        fontweight="bold",
        fontfamily="Arial",
        color="black",
    )
    ax.text(
        median,
        y_text,
        "median",
        ha="center",
        va="top",
        fontsize=6.2,
        fontweight="bold",
        fontfamily="Arial",
        color="black",
    )
    ax.text(
        ci_high,
        y_text,
        "0.95",
        ha="left",
        va="top",
        fontsize=6.2,
        fontweight="bold",
        fontfamily="Arial",
        color="black",
    )

    set_axis_titles(
        ax,
        xlabel=r"Bootstrap median $\Delta q$ (mmol g$^{-1}$)",
        ylabel="Bootstrap replicates",
    )

    style_axis(ax)
    add_panel_label(ax, "B")


def draw_panel_c(ax, tiers: pd.DataFrame) -> None:
    tiers = tiers.copy()
    order = ["primary_10pct", "stronger_20pct", "stronger_30pct"]
    tiers["tier"] = pd.Categorical(tiers["tier"], categories=order, ordered=True)
    tiers = tiers.sort_values("tier")

    labels = ["10%", "20%", "30%"]
    colors = [THRESHOLD_COLORS[10], THRESHOLD_COLORS[20], THRESHOLD_COLORS[30]]

    x = np.arange(len(tiers))
    median_delta = tiers["median_delta_q_mmol_g"].to_numpy(dtype=float)
    positive_fraction = 100.0 * tiers["positive_effect_fraction"].to_numpy(dtype=float)
    pair_counts = tiers["pairs"].to_numpy(dtype=int)

    bars = ax.bar(
        x,
        median_delta,
        width=0.62,
        color=colors,
        edgecolor="none",
    )

    ax.set_xticks(x, labels)
    set_axis_titles(
        ax,
        xlabel="Minimum frozen geometry contrast",
        ylabel=r"Median $\Delta q$ (mmol g$^{-1}$)",
    )

    ymax = float(max(median_delta))
    ax.set_ylim(0, ymax * 1.24)

    for bar, positive_pct, count in zip(bars, positive_fraction, pair_counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + ymax * 0.05,
            f"{positive_pct:.1f}% positive\nn={count:,}",
            ha="center",
            va="bottom",
            fontsize=8.0,
            fontweight="bold",
            fontfamily="Arial",
            color="black",
            linespacing=1.06,
        )

    style_axis(ax)
    add_panel_label(ax, "C")


def draw_panel_d(ax, driver: pd.DataFrame) -> None:
    driver = driver.copy()

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

    driver["label"] = [pretty.get(str(x), str(x)) for x in driver["driver_descriptor"]]
    driver = driver.sort_values("median_delta_q_mmol_g", ascending=True)

    y = np.arange(len(driver))
    effects = driver["median_delta_q_mmol_g"].to_numpy(dtype=float)
    colors = [COLORS["primary"] if value >= 0 else COLORS["warning"] for value in effects]

    ax.barh(
        y,
        effects,
        color=colors,
        edgecolor="none",
        height=0.68,
    )
    ax.axvline(0, color="black", lw=0.9)

    ax.set_yticks(y, driver["label"])

    set_axis_titles(
        ax,
        xlabel=r"Median $\Delta q$ (mmol g$^{-1}$)",
    )

    xmin = min(-0.72, float(effects.min()) - 0.38)
    xmax = float(effects.max()) + 1.00
    ax.set_xlim(xmin, xmax)

    for yi, (_, row) in enumerate(driver.iterrows()):
        effect = float(row["median_delta_q_mmol_g"])
        label = f"n={int(row['pairs']):,}; {100*float(row['positive_effect_fraction']):.1f}% +"

        if effect >= 0:
            x_text = effect + 0.12
            ha = "left"
        else:
            x_text = 0.06
            ha = "left"

        ax.text(
            x_text,
            yi,
            label,
            ha=ha,
            va="center",
            fontsize=5.5,
            fontweight="bold",
            fontfamily="Arial",
            color="black",
        )

    style_axis(ax)
    add_panel_label(ax, "D")


def make_geometry_deciles(effects: pd.DataFrame) -> pd.DataFrame:
    data = effects[["pair_max_fractional_difference", "delta_q_mmol_g"]].copy()

    data["geometry_bin"] = pd.qcut(
        data["pair_max_fractional_difference"],
        q=10,
        duplicates="drop",
    )

    grouped = (
        data.groupby("geometry_bin", observed=True)
        .agg(
            n=("delta_q_mmol_g", "size"),
            geometry_median=("pair_max_fractional_difference", "median"),
            delta_median=("delta_q_mmol_g", "median"),
            delta_q25=("delta_q_mmol_g", lambda x: x.quantile(0.25)),
            delta_q75=("delta_q_mmol_g", lambda x: x.quantile(0.75)),
        )
        .reset_index(drop=True)
    )

    return grouped


def draw_panel_e(ax, effects: pd.DataFrame) -> None:
    binned = make_geometry_deciles(effects)

    x = 100.0 * binned["geometry_median"].to_numpy(dtype=float)
    y = binned["delta_median"].to_numpy(dtype=float)
    q25 = binned["delta_q25"].to_numpy(dtype=float)
    q75 = binned["delta_q75"].to_numpy(dtype=float)

    band = ax.fill_between(
        x,
        q25,
        q75,
        color=COLORS["secondary"],
        alpha=0.28,
        linewidth=0,
        label="Interquartile range",
    )
    line, = ax.plot(
        x,
        y,
        color=COLORS["primary"],
        marker="o",
        markersize=4.2,
        lw=1.5,
        label="Decile median",
    )

    ax.axhline(0, color="black", lw=0.9, ls="--")

    set_axis_titles(
        ax,
        xlabel="Maximum frozen pair difference (%)",
        ylabel=r"Median $\Delta q$ (mmol g$^{-1}$)",
    )

    ax.set_xlim(left=0)

    legend_handles = [
        Patch(facecolor=COLORS["secondary"], edgecolor="none", alpha=0.28, label="Interquartile range"),
        Line2D([0], [0], color=COLORS["primary"], marker="o", lw=1.5, markersize=4.2, label="Decile median"),
    ]
    ax.legend(
        handles=legend_handles,
        loc="upper left",
        frameon=False,
        prop={
            "family": "Arial",
            "weight": "bold",
            "size": 6.4,
        },
        handlelength=1.6,
        borderaxespad=0.25,
    )

    style_axis(ax)
    add_panel_label(ax, "E")


def draw_panel_f(ax, topology: pd.DataFrame) -> None:
    topology = topology.copy()

    top = (
        topology.sort_values(["pairs", "topology"], ascending=[False, True])
        .head(8)
        .copy()
    )

    top = top.sort_values("median_delta_q_mmol_g", ascending=True)

    labels = [f"{str(row.topology)} (n={int(row.pairs):,})" for row in top.itertuples()]
    effects = top["median_delta_q_mmol_g"].to_numpy(dtype=float)
    colors = [COLORS["primary"] if value >= 0 else COLORS["warning"] for value in effects]
    y = np.arange(len(top))

    ax.barh(
        y,
        effects,
        color=colors,
        edgecolor="none",
        height=0.68,
    )
    ax.axvline(0, color="black", lw=0.9)
    ax.set_yticks(y, labels)

    set_axis_titles(
        ax,
        xlabel=r"Median $\Delta q$ (mmol g$^{-1}$)",
    )

    if len(effects):
        span = max(0.5, float(np.max(np.abs(effects))))
        ax.set_xlim(
            min(-0.25, float(effects.min()) - 0.08 * span),
            float(effects.max()) + 0.28 * span,
        )

    for yi, (_, row) in enumerate(top.iterrows()):
        effect = float(row["median_delta_q_mmol_g"])
        positive_pct = 100.0 * float(row["positive_effect_fraction"])

        if effect >= 0:
            x_text = effect + 0.035 * max(0.5, np.max(np.abs(effects)))
            ha = "left"
        else:
            x_text = effect - 0.035 * max(0.5, np.max(np.abs(effects)))
            ha = "right"

        ax.text(
            x_text,
            yi,
            f"{positive_pct:.1f}% +",
            ha=ha,
            va="center",
            fontsize=5.5,
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
        PAIR_EFFECT_PATH,
        SUMMARY_PATH,
        TIER_PATH,
        DRIVER_PATH,
        TOPOLOGY_PATH,
        BOOTSTRAP_PATH,
    ):
        require_file(path)

    apply_project17_style()

    effects = pd.read_parquet(PAIR_EFFECT_PATH)
    summary_table = pd.read_csv(SUMMARY_PATH)
    tiers = pd.read_csv(TIER_PATH)
    driver = pd.read_csv(DRIVER_PATH)
    topology = pd.read_csv(TOPOLOGY_PATH)
    bootstrap = pd.read_csv(BOOTSTRAP_PATH)

    summary = summary_dict(summary_table)

    fig = plt.figure(figsize=(7.15, 8.15), constrained_layout=False)
    gs = fig.add_gridspec(
        3,
        2,
        left=0.085,
        right=0.985,
        bottom=0.065,
        top=0.975,
        wspace=0.38,
        hspace=0.46,
        height_ratios=[1.0, 1.0, 1.0],
    )

    axes = {
        "A": fig.add_subplot(gs[0, 0]),
        "B": fig.add_subplot(gs[0, 1]),
        "C": fig.add_subplot(gs[1, 0]),
        "D": fig.add_subplot(gs[1, 1]),
        "E": fig.add_subplot(gs[2, 0]),
        "F": fig.add_subplot(gs[2, 1]),
    }

    draw_panel_a(axes["A"], effects, summary)
    draw_panel_b(axes["B"], bootstrap, summary)
    draw_panel_c(axes["C"], tiers)
    draw_panel_d(axes["D"], driver)
    draw_panel_e(axes["E"], effects)
    draw_panel_f(axes["F"], topology)

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    pdf_path = FIGURE_DIR / "Figure_2.pdf"
    png_path = FIGURE_DIR / "Figure_2.png"

    save_figure(fig, pdf_path=pdf_path, png_path=png_path, dpi=600)
    plt.close(fig)

    print("Project 17 Figure 2 revision generated")
    print(f"PDF: {pdf_path}")
    print(f"PNG: {png_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
