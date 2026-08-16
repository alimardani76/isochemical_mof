#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from figure_style_redesign import *
from data_utils import *

def load(root):
    base = "results/step3/05_secondary_outcome_atlas/"
    p1 = modern(root, base + "secondary_adsorption_mmolg_summary.csv")
    p2 = modern(root, base + "secondary_process_summary.csv")
    A = read_csv(p1, {"guest", "context", "pressure_bar", "median_symmetric_relative_effect"})
    P = read_csv(p2, {"process", "metric", "median_delta"})
    return (A, P), [str(p1), str(p2)]

def prep(A):
    z = A.copy()
    z["pressure_bar"] = pd.to_numeric(z.pressure_bar, errors="raise")
    z["effect_pct"] = 100 * pd.to_numeric(z.median_symmetric_relative_effect, errors="raise")
    return z

def dumbbell(ax, A, guest, contexts, panel):
    z = prep(A)
    z = z[(z.guest == guest) & z.context.isin(contexts)].copy()
    ypos = np.arange(len(contexts))[::-1]
    all_x = []

    for yi, ctx in zip(ypos, contexts):
        g = z[z.context == ctx].sort_values("pressure_bar")
        if len(g) < 2:
            continue

        low, high = g.iloc[0], g.iloc[-1]
        all_x.extend([low.effect_pct, high.effect_pct])
        col = PROCESS_COLORS[ctx]

        ax.plot([low.effect_pct, high.effect_pct], [yi, yi], color=col, lw=1.6, zorder=1)
        ax.scatter(low.effect_pct, yi, s=35, facecolor="white", edgecolor=col, lw=1.2, zorder=3)
        ax.scatter(high.effect_pct, yi, s=38, color=col, edgecolor="white", lw=.35, zorder=3)

        bbox = dict(boxstyle="round,pad=0.14", fc="white", ec="none", alpha=0.88)
        low_offset = (0, 12)
        high_offset = (0, -16)
        low_ha = "center"
        high_ha = "center"

        if panel == "A" and ctx == "methane-storage":
            low_offset = (0, 13)
            high_offset = (0, -15)

        if panel == "A" and ctx == "landfill-gas":
            low_offset = (0, 12)
            high_offset = (0, -16)

        if panel == "A" and ctx == "natural-gas-purification":
            low_offset = (-8, 12)
            low_ha = "right"
            high_offset = (12, -12)
            high_ha = "left"

        if panel == "B" and ctx == "post-combustion-vsa":
            low_offset = (0, 11)
            high_offset = (0, -15)

        if panel == "B" and ctx == "pre-combustion-40-40":
            high_offset = (0, -14)

        ax.annotate(
            f"{low.pressure_bar:g} bar",
            (low.effect_pct, yi),
            xytext=low_offset,
            textcoords="offset points",
            ha=low_ha,
            fontsize=5.8,
            color=PALETTE["slate"],
            bbox=bbox,
        )
        ax.annotate(
            f"{high.pressure_bar:g} bar",
            (high.effect_pct, yi),
            xytext=high_offset,
            textcoords="offset points",
            ha=high_ha,
            fontsize=5.8,
            color=PALETTE["slate"],
            bbox=bbox,
        )

    xmin, xmax = min(all_x), max(all_x)
    pad = max(1.0, 0.12 * (xmax - xmin))
    ax.set_xlim(xmin - pad, xmax + pad)
    ax.axvline(0, color=PALETTE["ink"], lw=.8)
    ax.set_yticks(ypos, [DISPLAY_NAMES[c] for c in contexts])
    ax.set_xlabel("Median relative uptake effect (%)")
    clean_axis(ax)
    panel_label(ax, panel)

    handles = [
        Line2D([0], [0], marker="o", ls="none", mfc="white", mec=PALETTE["slate"], label="Lower-pressure endpoint"),
        Line2D([0], [0], marker="o", ls="none", mfc=PALETTE["slate"], mec=PALETTE["slate"], label="Higher-pressure endpoint"),
    ]

    if panel == "A":
        ax.legend(handles=handles, loc="lower right", bbox_to_anchor=(0.98, 0.08), fontsize=6.0)
    else:
        ax.legend(handles=handles, loc="best", fontsize=6.2)

def process_plot(ax, P, metric, processes, panel, xlabel):
    z = P[P.metric == metric].copy()
    z = z[z.process.isin(processes)]
    z["o"] = z.process.map({p: i for i, p in enumerate(processes)})
    z = z.sort_values("o", ascending=False)
    y = np.arange(len(z))
    v = pd.to_numeric(z.median_delta, errors="raise").to_numpy()
    cols = [PROCESS_COLORS[p] for p in z.process]
    ax.hlines(y, 0, v, color=cols, lw=2.6)
    ax.scatter(v, y, s=34, color=cols, zorder=3)
    ax.axvline(0, color=PALETTE["ink"], lw=.8)
    ax.set_yticks(y, [DISPLAY_NAMES[p] for p in z.process])
    ax.set_xlabel(xlabel)
    max_abs = max(abs(v.min()), abs(v.max())) if len(v) else 1
    ax.set_xlim(min(v.min(), 0) - 0.22 * max_abs, max(v.max(), 0) + 0.10 * max_abs)
    span = ax.get_xlim()[1] - ax.get_xlim()[0]
    for yi, val in zip(y, v):
        if val >= 0:
            tx = val + 0.03 * span
            ha = "left"
        else:
            tx = val * 0.55
            ha = "center"
        ax.text(tx, yi, f"{val:+.2f}", va="center", ha=ha, fontsize=6.3,
                bbox=dict(boxstyle="round,pad=0.10", fc="white", ec="none", alpha=0.82))
    clean_axis(ax)
    panel_label(ax, panel)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    a = ap.parse_args()
    out = a.output_dir.resolve(); out.mkdir(parents=True, exist_ok=True)
    apply_style()
    (A, P), src = load(a.project_root.resolve())
    fig = plt.figure(figsize=(7.15, 5.45))
    gs = fig.add_gridspec(2, 2, left=.12, right=.98, bottom=.105, top=.96, wspace=.62, hspace=.54)
    aa = fig.add_subplot(gs[0, 0]); bb = fig.add_subplot(gs[0, 1]); cc = fig.add_subplot(gs[1, 0]); dd = fig.add_subplot(gs[1, 1])
    dumbbell(aa, A, "CH4", ["methane-storage", "landfill-gas", "natural-gas-purification"], "A")
    dumbbell(bb, A, "CO2", ["post-combustion-vsa", "natural-gas-purification", "landfill-gas", "pre-combustion-40-40"], "B")
    process_plot(cc, P, "mmol/g_working_capacity", ["methane-storage-psa", "landfill-gas-vpsa", "natural-gas-purification", "post-combustion-vsa", "pre-combustion-40-40"], "C", r"Median working-capacity change (mmol g$^{-1}$)")
    process_plot(dd, P, "selectivity", ["landfill-gas-vpsa", "natural-gas-purification", "post-combustion-vsa", "pre-combustion-40-40"], "D", "Median selectivity change")
    outs = export_figure(fig, out / "Figure_3_conservative")
    plt.close(fig)
    save_manifest(out / "Figure_3_conservative_manifest.json", script=Path(__file__).name, sources=src, outputs=outs, notes={"critical_redesign": "Panels A/B use only the stored discrete lower/higher endpoints; connecting segments do not imply an isotherm or transition pressure."})
if __name__ == "__main__":
    main()
