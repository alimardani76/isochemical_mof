#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from figure_style_redesign import *
from data_utils import *

def load(root):
    base = "results/step3/04_primary_ch4_analysis/"
    names = [
        "primary_ch4_pair_effects.parquet", "primary_ch4_summary.csv", "primary_ch4_geometry_tier_summary.csv",
        "primary_ch4_driver_summary.csv", "primary_ch4_topology_summary.csv", "primary_ch4_bootstrap_medians.csv"
    ]
    ps = [modern(root, base + n) for n in names]
    E = read_parquet(ps[0], {"q_geometry_low_mmol_g", "q_geometry_high_mmol_g", "delta_q_mmol_g", "pair_max_fractional_difference"})
    S = read_csv(ps[1], {"metric", "value"})
    T = read_csv(ps[2], {"tier", "median_delta_q_mmol_g", "positive_effect_fraction", "pairs"})
    D = read_csv(ps[3], {"driver_descriptor", "median_delta_q_mmol_g", "positive_effect_fraction", "pairs"})
    Top = read_csv(ps[4], {"topology", "median_delta_q_mmol_g", "positive_effect_fraction", "pairs"})
    B = read_csv(ps[5], {"bootstrap_median_delta_q_mmol_g"})
    assert_n(E, 11072, "primary CH4 effects")
    return (E, summary_dict(S), T, D, Top, B), [str(p) for p in ps]

def aplot(ax, E, S):
    lo = E.q_geometry_low_mmol_g.to_numpy(float)
    hi = E.q_geometry_high_mmol_g.to_numpy(float)
    d = E.delta_q_mmol_g.to_numpy(float)
    pos = d > 0
    neg = d < 0
    ax.scatter(lo[neg], hi[neg], s=4, alpha=.18, color=PALETTE["amber"], edgecolors="none", rasterized=True)
    ax.scatter(lo[pos], hi[pos], s=4, alpha=.13, color=PALETTE["blue"], edgecolors="none", rasterized=True)
    m = max(np.nanmax(lo), np.nanmax(hi)) * 1.02
    ax.plot([0, m], [0, m], ls="--", lw=.8, color=PALETTE["ink"])
    ax.set(xlim=(0, m), ylim=(0, m), xlabel=r"Geometry-low CH$_4$ uptake (mmol g$^{-1}$)", ylabel=r"Geometry-high CH$_4$ uptake (mmol g$^{-1}$)")
    handles = [
        Line2D([0], [0], marker='o', ls='none', mfc=PALETTE['blue'], mec='none', label=f"Increase ({100*S['positive_effect_fraction']:.1f}%)"),
        Line2D([0], [0], marker='o', ls='none', mfc=PALETTE['amber'], mec='none', label=f"Decrease ({100*S['negative_effect_fraction']:.1f}%)")
    ]
    ax.legend(handles=handles, loc="lower right")
    clean_axis(ax)
    panel_label(ax, "A")

def bplot(ax, B, S):
    v = B.bootstrap_median_delta_q_mmol_g.to_numpy(float)
    counts, bins, _ = ax.hist(
        v, bins=45, color=PALETTE["sky"], edgecolor="white", linewidth=.25
    )
    med = S["median_delta_q_mmol_g"]
    lo = S["bootstrap_95ci_low_median_delta_q_mmol_g"]
    hi = S["bootstrap_95ci_high_median_delta_q_mmol_g"]
    ymax = max(counts) if len(counts) else 1.0
    ax.axvline(med, color=PALETTE["ink"], lw=1.1)
    ax.axvline(lo, color=PALETTE["gray"], lw=.8, ls="--")
    ax.axvline(hi, color=PALETTE["gray"], lw=.8, ls="--")
    yb = ymax * 0.90
    tick_h = ymax * 0.03
    ax.plot([lo, hi], [yb, yb], color=PALETTE["gray"], lw=1.0)
    ax.plot([lo, lo], [yb - tick_h, yb + tick_h], color=PALETTE["gray"], lw=1.0)
    ax.plot([hi, hi], [yb - tick_h, yb + tick_h], color=PALETTE["gray"], lw=1.0)
    ax.text(
        .98, .94,
        f"median {med:.3f}\n95% CI {lo:.3f}–{hi:.3f}",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=6.2,
        bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.88),
    )
    ax.set(
        xlabel=r"Bootstrap median $\Delta q$ (mmol g$^{-1}$)",
        ylabel="Bootstrap replicates",
    )
    clean_axis(ax)
    panel_label(ax, "B")

def cplot(ax, T):
    T = T.copy()
    order = ["primary_10pct", "stronger_20pct", "stronger_30pct"]
    T["tier"] = pd.Categorical(T.tier, categories=order, ordered=True)
    T = T.sort_values("tier")
    x = np.arange(len(T))
    vals = T.median_delta_q_mmol_g.to_numpy(float)
    cols = [THRESHOLD_COLORS[t] for t in [10, 20, 30]]
    bars = ax.bar(x, vals, color=cols, width=.50)
    ax.set_xticks(x, ["10%", "20%", "30%"])
    ax.set(xlabel="Minimum frozen geometry\ncontrast", ylabel=r"Median $\Delta q$ (mmol g$^{-1}$)")
    ax.set_ylim(0, max(vals) * 1.34)
    for b, r in zip(bars, T.itertuples()):
        ax.text(
            b.get_x() + b.get_width() / 2,
            b.get_height() + max(vals) * .05,
            f"{100*r.positive_effect_fraction:.1f}% positive\nn={int(r.pairs):,}",
            ha="center", fontsize=5.9,
        )
    clean_axis(ax)
    panel_label(ax, "C")

def dplot(ax, D):
    D = D.copy().sort_values("median_delta_q_mmol_g")
    y = np.arange(len(D))
    vals = D.median_delta_q_mmol_g.to_numpy(float)
    cols = [descriptor_color(x) for x in D.driver_descriptor]
    ax.hlines(y, 0, vals, color=cols, lw=2.2)
    ax.scatter(vals, y, s=28, color=cols, zorder=3)
    ax.axvline(0, color=PALETTE["ink"], lw=.8)
    ax.set_yticks(y, [descriptor_label(x) for x in D.driver_descriptor])
    ax.set_xlabel(r"Median $\Delta q$ (mmol g$^{-1}$)")
    xmin = min(vals.min() * 1.45, -0.45)
    xmax = max(vals.max() * 1.30, 0.85)
    ax.set_xlim(xmin, xmax)
    text_x_for_negative = max(0.10, xmax * 0.12)
    span = xmax - xmin
    for yi, r in enumerate(D.itertuples()):
        if r.median_delta_q_mmol_g >= 0:
            tx = r.median_delta_q_mmol_g + 0.04 * span
            ha = "left"
        else:
            tx = text_x_for_negative
            ha = "left"
        ax.text(tx, yi, f"n={int(r.pairs):,}; {100*r.positive_effect_fraction:.1f}% positive",
                va="center", ha=ha, fontsize=5.7)
    clean_axis(ax)
    panel_label(ax, "D")

def deciles(E):
    z = E[["pair_max_fractional_difference", "delta_q_mmol_g"]].copy()
    z["bin"] = pd.qcut(z.pair_max_fractional_difference, 10, duplicates="drop")
    return z.groupby("bin", observed=True).agg(
        n=("delta_q_mmol_g", "size"),
        x=("pair_max_fractional_difference", "median"),
        y=("delta_q_mmol_g", "median"),
        q25=("delta_q_mmol_g", lambda v: v.quantile(.25)),
        q75=("delta_q_mmol_g", lambda v: v.quantile(.75)),
    ).reset_index(drop=True)

def eplot(ax, E):
    z = deciles(E)
    x = 100 * z.x.to_numpy()
    ax.fill_between(x, z.q25, z.q75, color=PALETTE["sky"], alpha=.24, lw=0)
    ax.plot(x, z.y, color=PALETTE["blue"], marker="o", ms=3.8, lw=1.25)
    ax.axhline(0, color=PALETTE["ink"], lw=.75)
    ax.set(xlabel="Maximum frozen pair difference (%)", ylabel=r"Median $\Delta q$ (mmol g$^{-1}$)", xlim=(0, None))
    clean_axis(ax)
    panel_label(ax, "E")

def fplot(ax, T):
    Z = T.sort_values(["pairs", "topology"], ascending=[False, True]).head(8).sort_values("median_delta_q_mmol_g")
    y = np.arange(len(Z))
    v = Z.median_delta_q_mmol_g.to_numpy(float)
    ax.hlines(y, 0, v, color=PALETTE["teal"], lw=2.2)
    ax.scatter(v, y, s=25, color=PALETTE["teal"])
    ax.axvline(0, color=PALETTE["ink"], lw=.8)
    ax.set_yticks(y, [f"{r.topology} (n={int(r.pairs):,})" for r in Z.itertuples()])
    ax.set_xlabel(r"Median $\Delta q$ (mmol g$^{-1}$)")
    clean_axis(ax)
    panel_label(ax, "F")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    a = ap.parse_args()
    out = a.output_dir.resolve(); out.mkdir(parents=True, exist_ok=True)
    apply_style()
    (E, S, T, D, Top, B), src = load(a.project_root.resolve())
    fig = plt.figure(figsize=(7.15, 5.65))
    gs = fig.add_gridspec(2, 3, left=.08, right=.985, bottom=.11, top=.965, wspace=.58, hspace=.50)
    axs = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(3)]
    aplot(axs[0], E, S); bplot(axs[1], B, S); cplot(axs[2], T); dplot(axs[3], D); eplot(axs[4], E); fplot(axs[5], Top)
    outs = export_figure(fig, out / "Figure_2_conservative")
    plt.close(fig)
    save_manifest(out / "Figure_2_conservative_manifest.json", script=Path(__file__).name, sources=src, outputs=outs, plotting_only_aggregation=["Panel E uses descriptive geometry-contrast deciles, matching existing figure logic."])
if __name__ == "__main__":
    main()
