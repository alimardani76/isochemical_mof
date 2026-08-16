#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.patches import Patch
from figure_style_redesign import *
from data_utils import *
ORDER = ['positive_both', 'pressure_activated', 'pressure_suppressed', 'negative_both']
LAB = {'positive_both': 'Positive both', 'pressure_activated': 'Pressure activated', 'pressure_suppressed': 'Pressure suppressed', 'negative_both': 'Negative both'}
COL = {'positive_both': PALETTE['blue'], 'pressure_activated': PALETTE['teal'], 'pressure_suppressed': PALETTE['purple'], 'negative_both': PALETTE['slate']}
DORDER = ['ASA', 'AVA', 'AVAf', 'POAVA', 'POAVAf', 'Df', 'Di', 'Dif']

def load(root):
    b = 'results/step3/07_response_archetypes/'
    ps = [modern(root, b + n) for n in ['response_archetypes.parquet', 'response_archetype_summary.csv', 'response_archetype_driver_summary.csv', 'response_archetype_topology_summary.csv']]
    A = read_parquet(ps[0], {'positive_fraction_low_pressure', 'positive_fraction_high_pressure'})
    S = read_csv(ps[1], {'archetype', 'pairs', 'fraction'})
    D = read_csv(ps[2], {'driver_descriptor', 'pairs', 'positive_both_fraction', 'pressure_activated_fraction', 'pressure_suppressed_fraction', 'negative_both_fraction'})
    T = read_csv(ps[3], {'topology', 'pairs', 'pressure_activated_fraction'})
    assert_n(A, 11072, 'response archetypes')
    return (A, S, D, T), [str(p) for p in ps]

def heat(ax, A):
    x = A.positive_fraction_low_pressure.to_numpy(float)
    y = A.positive_fraction_high_pressure.to_numpy(float)
    bins = np.linspace(-.055, 1.055, 11)
    c, xe, ye = np.histogram2d(x, y, bins=[bins, bins])
    pos = c[c > 0]
    m = ax.pcolormesh(xe, ye, c.T, cmap='Blues', norm=LogNorm(vmin=max(1, pos.min()), vmax=pos.max()), edgecolors='white', linewidth=.3)
    ax.axvline(.5, color=PALETTE['ink'], lw=.8)
    ax.axhline(.5, color=PALETTE['ink'], lw=.8)
    ax.plot([0, 1], [0, 1], ls='--', lw=.7, color=PALETTE['gray'])
    ax.set(xlim=(0, 1), ylim=(0, 1), xlabel='Positive endpoints at low pressure (%)', ylabel='Positive endpoints at high pressure (%)')
    ax.set_xticks([0, .25, .5, .75, 1], [0, 25, 50, 75, 100])
    ax.set_yticks([0, .25, .5, .75, 1], [0, 25, 50, 75, 100])
    box = dict(boxstyle='round,pad=0.18', fc='white', ec='none', alpha=0.85)
    ax.text(.75, .77, 'Positive both', transform=ax.transAxes, ha='center', fontsize=6.2, fontweight='bold', bbox=box)
    ax.text(.24, .77, 'Pressure activated', transform=ax.transAxes, ha='center', fontsize=6.2, fontweight='bold', bbox=box)
    ax.text(.76, .22, 'Pressure suppressed', transform=ax.transAxes, ha='center', fontsize=6.2, fontweight='bold', bbox=box)
    ax.text(.25, .22, 'Negative both', transform=ax.transAxes, ha='center', fontsize=6.2, fontweight='bold', bbox=box)
    cb = ax.figure.colorbar(m, ax=ax, fraction=.045, pad=.025)
    cb.set_label('Pairs', fontsize=7.0)
    cb.ax.tick_params(labelsize=6.2)
    clean_axis(ax)
    panel_label(ax, 'A')

def prev(ax, S):
    S = S.copy()
    S['archetype'] = pd.Categorical(S.archetype, categories=ORDER, ordered=True)
    S = S.sort_values('archetype')
    x = np.arange(4)
    v = 100 * S.fraction.to_numpy(float)
    bars = ax.bar(x, v, color=[COL[str(k)] for k in S.archetype], width=.52)
    ax.set_xticks(x, ['Positive\nboth', 'Pressure\nactivated', 'Pressure\nsuppressed', 'Negative\nboth'])
    ax.set_ylabel('Frozen pairs (%)')
    ax.set_ylim(0, max(v) * 1.27)
    for b, r, pct in zip(bars, S.itertuples(), v):
        ax.text(b.get_x() + b.get_width() / 2, pct + max(v) * .035, f'{pct:.1f}%\nn={int(r.pairs):,}', ha='center', fontsize=6.1, fontweight='bold')
    act = float(S[S.archetype == 'pressure_activated'].fraction.iloc[0])
    sup = float(S[S.archetype == 'pressure_suppressed'].fraction.iloc[0])
    ax.text(1.52, max(v) * 1.08, f'{act/sup:.1f}× more common than\npressure-suppressed', ha='center', va='center', fontsize=6.6,
            fontweight='bold', color=PALETTE['vermillion'], bbox=dict(boxstyle='round,pad=0.22', fc='white', ec='none', alpha=0.92))
    clean_axis(ax)
    panel_label(ax, 'B')

def comp(ax, D):
    Z = D[D.driver_descriptor.isin(DORDER)].copy()
    Z['o'] = Z.driver_descriptor.map({k: i for i, k in enumerate(DORDER)})
    Z = Z.sort_values('o', ascending=False)
    y = np.arange(len(Z))
    left = np.zeros(len(Z))
    mapping = {'positive_both': 'positive_both_fraction', 'pressure_activated': 'pressure_activated_fraction', 'pressure_suppressed': 'pressure_suppressed_fraction', 'negative_both': 'negative_both_fraction'}
    for k in ORDER:
        v = 100 * pd.to_numeric(Z[mapping[k]]).to_numpy(float)
        ax.barh(y, v, left=left, height=.56, color=COL[k], edgecolor='white', lw=.3)
        left += v
    ax.set_yticks(y, [f'{descriptor_label(r.driver_descriptor)} (n={int(r.pairs):,})' for r in Z.itertuples()])
    ax.set(xlim=(0, 100), xlabel='Archetype composition (%)')
    ax.legend(handles=[Patch(facecolor=COL[k], label=LAB[k]) for k in ORDER], ncol=2, loc='lower center', bbox_to_anchor=(.5, 1.005), fontsize=6.0)
    clean_axis(ax)
    panel_label(ax, 'C')

def topo(ax, T, S):
    z = T.copy()
    z['pairs'] = pd.to_numeric(z.pairs).astype(int)
    z = z[z.pairs >= 100].sort_values('pressure_activated_fraction')
    y = np.arange(len(z))
    v = 100 * pd.to_numeric(z.pressure_activated_fraction).to_numpy(float)
    overall = 100 * float(S[S.archetype == 'pressure_activated'].fraction.iloc[0])
    ax.hlines(y, 0, v, color=COL['pressure_activated'], lw=3.2)
    ax.scatter(v, y, s=34, color=COL['pressure_activated'])
    ax.axvline(overall, color=PALETTE['ink'], ls='--', lw=.8)
    ax.text(overall, 1.02, f'overall = {overall:.1f}%', transform=ax.get_xaxis_transform(), ha='center', va='bottom', fontsize=6.2, fontweight='bold')
    ax.set_yticks(y, [f'{r.topology} (n={int(r.pairs):,})' for r in z.itertuples()])
    ax.set_xlabel('Pressure-activated pairs (%)')
    clean_axis(ax)
    panel_label(ax, 'D')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project-root', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    a = ap.parse_args()
    out = a.output_dir.resolve(); out.mkdir(parents=True, exist_ok=True)
    apply_style()
    (A, S, D, T), src = load(a.project_root.resolve())
    fig = plt.figure(figsize=(7.15, 5.45))
    gs = fig.add_gridspec(2, 2, left=.09, right=.98, bottom=.10, top=.965, wspace=.48, hspace=.48)
    aa = fig.add_subplot(gs[0, 0]); bb = fig.add_subplot(gs[0, 1]); cc = fig.add_subplot(gs[1, 0]); dd = fig.add_subplot(gs[1, 1])
    heat(aa, A); prev(bb, S); comp(cc, D); topo(dd, T, S)
    outs = export_figure(fig, out / 'Figure_4_conservative')
    plt.close(fig)
    save_manifest(out / 'Figure_4_conservative_manifest.json', script=Path(__file__).name, sources=src, outputs=outs, notes={'classification': 'Archetypes use the audited 50% majority rule at discrete low/high endpoint sets.'})
if __name__ == '__main__':
    main()
