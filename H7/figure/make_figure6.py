#!/usr/bin/env python3
"""Rebuild Paper 17 Figure 6 from the frozen H7 handover CSV outputs.

No model training, CIF files, or synthetic numerical values.
Usage: python figure/make_figure6.py [--results code/results] [--out figure]
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch
from p17_style_v2 import apply_style, PALETTE, panel_label

BLUE = PALETTE['primary']
GREEN = PALETTE['validated']
GRAY = PALETTE['neutral']
MID = PALETTE['lightgray']
INK = PALETTE['ink']
VERMILION = PALETTE['warning']
LIGHT_GRAY = '#F2F4F5'


def motif(ax, cx, cy, shape, scale=1.0, central_label='M'):
    """Conceptual metal-neighbor sketch, NOT obtained from a particular CIF."""
    coords = {
        'low': [(-.110,-.080),(.110,-.080),(.10,.092),(-.10,.092)],
        'high':[(-.128,-.062),(-.044,.124),(.114,.108),(.132,-.064),(.006,-.130)]
    }[shape]
    neighbor_colors = [VERMILION, BLUE, '#C97DB4', VERMILION, GREEN]
    for i, (dx,dy) in enumerate(coords):
        px, py = cx + scale*dx, cy + scale*dy
        ax.plot([cx, px], [cy, py], color='#95A7B6', lw=1.9, zorder=1, solid_capstyle='round')
        ax.add_patch(Circle((px, py), 0.022*scale, color=neighbor_colors[i % len(neighbor_colors)],
                            ec='white', lw=.7, zorder=3))
    ax.add_patch(Circle((cx, cy), 0.038*scale, color=BLUE, ec=INK, lw=.9, zorder=4))
    ax.text(cx, cy, central_label, color='white', ha='center', va='center',
            fontsize=8.2*scale, fontweight='bold', zorder=5)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--results', type=Path, default=Path(__file__).resolve().parents[1] / 'code' / 'results')
    cli.add_argument('--out', type=Path, default=Path(__file__).resolve().parent)
    args = cli.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    comp = pd.read_csv(args.results / 'model_comparison.csv')
    folds = pd.read_csv(args.results / 'cv_fold_metrics.csv')
    shap = pd.read_csv(args.results / 'shap_feature_importance.csv')

    assert len(comp) == 6 and len(folds) == 30
    assert set(comp.model) == {'geometry', 'local', 'combined'}
    assert set(comp.split_scheme) == {'random_5fold', 'topology_grouped_5fold'}

    apply_style(8.9)
    plt.rcParams.update({
        'axes.labelsize': 8.8,
        'axes.titlesize': 10.0,
        'axes.titleweight': 'bold',
        'xtick.labelsize': 7.6,
        'ytick.labelsize': 7.6,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'pdf.fonttype': 42,
        'svg.fonttype': 'none',
        'svg.hashsalt': 'p17-h7-figure6-refined-20261014v3'
    })

    fig = plt.figure(figsize=(8.95, 6.7), facecolor='white')
    gs = fig.add_gridspec(2, 2, left=.085, right=.982, top=.935, bottom=.148,
                          wspace=.36, hspace=.40, width_ratios=[1.03, 1.08], height_ratios=[0.98, 1.16])

    # A: clean original-style schematic; intentionally free of text cards.
    ax = fig.add_subplot(gs[0, 0])
    panel_label(ax, 'A', x=-0.115, y=1.095, fontsize=14.2)
    ax.set_title('Post-freeze local-environment comparison', loc='left', pad=15)
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis('off')
    ax.text(.06, .91, 'Frozen matched pair', fontsize=8.3, fontweight='bold', color=GRAY)

    motif(ax, .255, .655, 'low', scale=.95)
    motif(ax, .750, .655, 'high', scale=.95)
    ax.annotate('', xy=(.585, .655), xytext=(.43, .655),
                arrowprops={'arrowstyle': '-|>', 'lw': 1.25, 'color': INK, 'mutation_scale': 13})
    ax.text(.255, .450, 'Geometry-low', ha='center', fontsize=8.3, fontweight='bold')
    ax.text(.750, .450, 'Geometry-high', ha='center', fontsize=8.3, fontweight='bold')
    ax.text(.5, .342, r'$\Delta x = x_{\mathrm{high}}-x_{\mathrm{low}}$',
            ha='center', fontsize=10.6, fontweight='bold')
    ax.text(.5, .232, '8 pore descriptors + density   |   19 local features',
            ha='center', fontsize=7.7)
    ax.text(.5, .128, r'Target: $\Delta q$, CH$_4$ (298 K, 65 bar)',
            ha='center', fontsize=8.0)
    ax.text(.5, .020, 'Conceptual metal-neighbor sketches  |  n = 11,065 pairs',
            ha='center', fontsize=6.7, color=GRAY)

    # B: held-out predictive performance
    ax = fig.add_subplot(gs[0, 1])
    panel_label(ax, 'B', x=-0.115, y=1.095, fontsize=14.2)
    ax.set_title('Held-out predictive performance', loc='left', pad=16)
    models = ['geometry', 'local', 'combined']
    pos = np.arange(3)
    bw = .31
    for scheme, offset, color, name in [
        ('random_5fold', -.17, BLUE, 'Random 5-fold'),
        ('topology_grouped_5fold', .17, GREEN, 'Topology-held-out')]:
        sub = comp[comp.split_scheme.eq(scheme)].set_index('model').loc[models]
        ax.bar(pos + offset, sub.spearman_mean, bw, color=color, alpha=.97, label=name, zorder=2)
        ax.errorbar(pos + offset, sub.spearman_mean, yerr=sub.spearman_sd,
                    fmt='none', ecolor=INK, elinewidth=.82, capsize=2.4, zorder=3)
    ax.set_xticks(pos, ['Pores +\ndensity', 'Local', 'Combined'])
    ax.set_ylabel(r'Held-out Spearman $\rho$')
    ax.set_ylim(0, 1.01)
    ax.set_yticks(np.arange(0, 1.01, .2))
    ax.legend(loc='upper center', bbox_to_anchor=(.52, 1.05), ncol=2, fontsize=7.0,
              frameon=False, columnspacing=1.1, handlelength=1.0, handletextpad=0.35)
    ax.tick_params(axis='x', pad=6)
    ax.spines['left'].set_bounds(0, 1)

    # C: feature attribution
    ax = fig.add_subplot(gs[1, 0])
    panel_label(ax, 'C', x=-0.115, y=1.085, fontsize=14.2)
    ax.set_title('Combined-model feature attribution', loc='left', pad=15)
    t = shap[shap.split_scheme.eq('topology_grouped_5fold')].nlargest(9, 'mean_abs_shap').iloc[::-1]
    name = {
        'dDensity': r'$\Delta$Density',
        'dAVAf': r'$\Delta$AVAf',
        'dASA': r'$\Delta$ASA',
        'dPOAVA': r'$\Delta$POAVA',
        'dPOAVAf': r'$\Delta$POAVAf',
        'dDf': r'$\Delta D_f$',
        'dDi': r'$\Delta D_i$',
        'dDif': r'$\Delta D_{if}$',
        'dAVA': r'$\Delta$AVA',
        'dlocal_metal_count': r'$\Delta$Metal count*'
    }
    y = np.arange(len(t))
    ax.barh(y, t.mean_abs_shap, height=.64,
            color=[GREEN if s.startswith('dlocal_') else BLUE for s in t.feature])
    ax.set_yticks(y, [name.get(s, s.replace('dlocal_', 'Δ')) for s in t.feature])
    ax.set_xlabel(r'Mean absolute held-out SHAP (mmol g$^{-1}$)')
    ax.set_xlim(0, max(t.mean_abs_shap) * 1.15)
    ax.tick_params(axis='y', length=0, pad=5)
    ax.text(.99, .04, 'Topology-held-out models\n*Unit-cell dependent', transform=ax.transAxes,
            ha='right', va='bottom', fontsize=7, color=GRAY)

    # D: incremental ranking value
    ax = fig.add_subplot(gs[1, 1])
    panel_label(ax, 'D', x=-0.115, y=1.085, fontsize=14.2)
    ax.set_title('Incremental ranking value', loc='left', pad=15)
    row_defs = [('random_5fold', 1.0, BLUE, 'Random 5-fold'),
                ('topology_grouped_5fold', 0.0, GREEN, 'Topology-held-out')]
    jitter = np.array([-.10, -.05, 0, .05, .10])
    for scheme, center, color, label in row_defs:
        pivot = folds.loc[folds.split_scheme.eq(scheme)].pivot(index='fold', columns='model', values='spearman_rho')
        delta = (pivot.combined - pivot.geometry).sort_index().values
        ax.scatter(delta, center + jitter, s=38, color=color, edgecolors='white', linewidths=.55, zorder=4)
        ax.scatter([delta.mean()], [center], marker='D', s=108, color=color,
                   edgecolors=INK, linewidths=.7, zorder=5)
        if center > 0:
            xytext = (-4, 20)
            va = 'bottom'
        else:
            xytext = (0, -23)
            va = 'top'
        ax.annotate(f'Mean {delta.mean():+.4f}', (delta.mean(), center), xytext=xytext,
                    textcoords='offset points', ha='center', va=va,
                    fontsize=7.4, fontweight='bold', color=color)
    ax.axvline(0, color=GRAY, ls='--', lw=.95, zorder=1)
    ax.set_yticks([0, 1], ['Topology-held-out', 'Random 5-fold'])
    ax.set_xlim(-.040, .018)
    ax.set_ylim(-.45, 1.52)
    ax.set_xticks([-.04, -.03, -.02, -.01, 0, .01])
    ax.set_xlabel(r'$\Delta$Spearman $\rho$ (combined $-$ pores+density)')
    ax.tick_params(axis='y', length=0, pad=7)
    for edge in ['left', 'right', 'top']:
        ax.spines[edge].set_visible(False)

    for ext in ('pdf', 'svg', 'png'):
        fp = args.out / ('Figure_6.' + ext)
        metadata = ({'CreationDate': datetime(2026, 10, 14, tzinfo=timezone.utc)} if ext == 'pdf'
                    else {'Date': '2026-10-14'} if ext == 'svg'
                    else {'Software': 'Paper 17 H7 Figure 6 refined'})
        fig.savefig(fp, format=ext, dpi=400, facecolor='white', bbox_inches='tight',
                    pad_inches=.065, metadata=metadata)
        print(fp)
    plt.close(fig)


if __name__ == '__main__':
    main()
