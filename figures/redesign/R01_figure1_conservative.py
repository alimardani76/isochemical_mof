#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter
from figure_style_redesign import *
from data_utils import *

COHORT = [
    ("ARC–MOF registry", 279_019), ("Charged CIFs parsed", 242_363),
    ("Same-chemistry candidates", 48_366), ("Same recorded architecture", 44_511),
    ("10% geometry eligible", 26_146), ("Frozen primary pairs", 11_072),
]

def load(root):
    fam = modern(root, "results/step2/02_geometry_threshold_census/geometry_threshold_families.parquet")
    cen = modern(root, "results/step2/02_geometry_threshold_census/geometry_threshold_census.csv")
    pairs = modern(root, "results/step2/03_geometry_pairs/primary_geometry_pairs.parquet")
    drv = modern(root, "results/step2/03_geometry_pairs/primary_pair_driver_census.csv")
    F = read_parquet(fam, {"max_pore_fractional_span"})
    C = read_csv(cen, {"threshold_percent", "eligible_families", "eligible_frameworks"})
    P = read_parquet(pairs, {"pair_max_fractional_difference", "pair_mean_fractional_difference", "topology"})
    D = read_csv(drv, {"driver_descriptor", "selected_pairs"})
    assert_n(P, 11072, "primary_geometry_pairs")
    return (F, C, P, D), [str(fam), str(cen), str(pairs), str(drv)]

def pA(ax):
    ax.set_axis_off()
    ys = np.linspace(0.90, 0.10, len(COHORT))
    widths = np.linspace(0.84, 0.67, len(COHORT))
    heights = np.full(len(COHORT), 0.092)

    for i, ((lab, n), y, w, h) in enumerate(zip(COHORT, ys, widths, heights)):
        color = PALETTE["blue"] if i == len(COHORT) - 1 else (
            PALETTE["slate"] if i == 0 else PALETTE["pale"]
        )
        txt = "white" if i in {0, len(COHORT) - 1} else PALETTE["ink"]
        edge = PALETTE["lightgray"] if i not in {0, len(COHORT) - 1} else "none"

        box = FancyBboxPatch(
            (0.5 - w / 2, y - h / 2),
            w,
            h,
            boxstyle="round,pad=0.010,rounding_size=0.015",
            transform=ax.transAxes,
            facecolor=color,
            edgecolor=edge,
            linewidth=0.7,
        )
        ax.add_patch(box)

        ax.text(
            0.5, y + 0.024, f"{n:,}",
            ha="center", va="center",
            transform=ax.transAxes,
            fontsize=8.6, fontweight="bold", color=txt,
        )
        ax.text(
            0.5, y - 0.024, lab,
            ha="center", va="center",
            transform=ax.transAxes,
            fontsize=6.8, color=txt,
        )

        if i < len(COHORT) - 1:
            ax.annotate(
                "",
                xy=(0.5, ys[i + 1] + heights[i + 1] / 2 + 0.016),
                xytext=(0.5, y - h / 2 - 0.016),
                xycoords=ax.transAxes,
                textcoords=ax.transAxes,
                arrowprops=dict(
                    arrowstyle="->",
                    lw=0.85,
                    color=PALETTE["gray"],
                    shrinkA=0,
                    shrinkB=0,
                    mutation_scale=8,
                ),
            )

    panel_label(ax, "A", x=-0.03, y=1.01)

def pB(ax, F):
    v = pd.to_numeric(F.max_pore_fractional_span, errors="raise").clip(0, 1).to_numpy() * 100
    counts, bins, _ = ax.hist(v, bins=np.linspace(0, 100, 41), color=PALETTE["sky"], edgecolor="white", linewidth=0.3)
    ymax = max(counts) if len(counts) else 1
    ax.axvline(10, color=PALETTE["ink"], lw=1.1, zorder=3)
    ax.text(12.5, ymax * 0.90, "10% frozen", fontsize=ANNOTATION_SIZE, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.92))
    ax.set(xlabel="Maximum within-family pore span (%)", ylabel="Families", xlim=(0, 100))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{int(x):,}"))
    clean_axis(ax)
    panel_label(ax, "B")

def pC(ax, C):
    C = C.copy()
    C["threshold_percent"] = pd.to_numeric(C.threshold_percent).astype(int)
    C = C.sort_values("threshold_percent")

    x = np.arange(len(C))
    vals = pd.to_numeric(C.eligible_families).astype(int).to_numpy()
    cols = [THRESHOLD_COLORS.get(int(t), PALETTE["gray"]) for t in C.threshold_percent]

    bars = ax.bar(x, vals, width=0.46, color=cols)
    ax.set_xticks(x, [f"{t}%" for t in C.threshold_percent])
    ax.set(xlabel="Candidate geometry threshold", ylabel="Eligible families")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{int(x):,}"))
    ax.set_ylim(0, max(vals) * 1.36)

    pad = max(vals) * 0.045
    for b, n, fw in zip(bars, vals, pd.to_numeric(C.eligible_frameworks).astype(int)):
        ax.text(
            b.get_x() + b.get_width() / 2,
            n + pad,
            f"{n:,}\n({fw:,} frameworks)",
            ha="center",
            va="bottom",
            fontsize=5.4,
            linespacing=0.95,
            clip_on=False,
        )

    clean_axis(ax)
    panel_label(ax, "C")

def pD(ax, D):
    D = D.copy().sort_values("selected_pairs")
    y = np.arange(len(D))
    vals = pd.to_numeric(D.selected_pairs).astype(int).to_numpy()
    labs = [descriptor_label(x) for x in D.driver_descriptor]
    colors = [descriptor_color(x) for x in D.driver_descriptor]
    ax.barh(y, vals, color=colors, height=0.56)
    ax.set_yticks(y, labs)
    ax.set_xlabel("Frozen primary pairs")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{int(x):,}"))
    ax.set_xlim(0, max(vals) * 1.16)
    for yi, n in zip(y, vals):
        ax.text(n + max(vals) * 0.018, yi, f"{n:,}", va="center", fontsize=ANNOTATION_SIZE)
    clean_axis(ax)
    panel_label(ax, "D")

def pE(ax, P):
    x = pd.to_numeric(P.pair_max_fractional_difference).to_numpy() * 100
    y = pd.to_numeric(P.pair_mean_fractional_difference).to_numpy() * 100
    ax.scatter(x, y, s=4, alpha=0.14, color=PALETTE["blue"], edgecolors="none", rasterized=True)
    mx, my = np.median(x), np.median(y)
    ax.axvline(mx, color=PALETTE["gray"], ls="--", lw=0.75)
    ax.axhline(my, color=PALETTE["gray"], ls="--", lw=0.75)
    ax.text(.97, .04, f"medians: {mx:.1f}% / {my:.1f}%", transform=ax.transAxes,
            ha="right", fontsize=ANNOTATION_SIZE)
    ax.set(xlabel="Maximum pair difference (%)", ylabel="Mean pair difference (%)", xlim=(0, None), ylim=(0, None))
    clean_axis(ax)
    panel_label(ax, "E")

def pF(ax, P):
    c = P.topology.astype("string").fillna("missing").value_counts()
    top = c.head(10).copy()
    other = int(c.iloc[10:].sum())
    if other:
        top.loc["Other"] = other
    top = top.sort_values()
    y = np.arange(len(top))
    colors = [PALETTE["lightgray"] if k == "Other" else PALETTE["teal"] for k in top.index]
    ax.barh(y, top.values, color=colors, height=0.56)
    ax.set_yticks(y, [str(k) for k in top.index])
    ax.set_xlabel("Frozen primary pairs")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{int(x):,}"))
    ax.set_xlim(0, max(top.values) * 1.18)
    for yi, n in zip(y, top.values):
        ax.text(n + max(top.values) * 0.018, yi, f"{int(n):,}", va="center", fontsize=6.1)
    clean_axis(ax)
    panel_label(ax, "F")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    a = ap.parse_args()
    root = a.project_root.resolve()
    out = a.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    apply_style()
    (F, C, P, D), src = load(root)
    fig = plt.figure(figsize=(7.15, 5.55))
    gs = fig.add_gridspec(2, 3, left=.075, right=.98, bottom=.095, top=.965, wspace=.48, hspace=.48)
    axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(3)]
    pA(axes[0]); pB(axes[1], F); pC(axes[2], C); pD(axes[3], D); pE(axes[4], P); pF(axes[5], P)
    outputs = export_figure(fig, out / "Figure_1_conservative")
    plt.close(fig)
    save_manifest(out / "Figure_1_conservative_manifest.json", script=Path(__file__).name, sources=src, outputs=outputs)
if __name__ == "__main__":
    main()
