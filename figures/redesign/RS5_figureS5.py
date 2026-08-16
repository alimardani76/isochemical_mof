#!/usr/bin/env python3
from pathlib import Path
import argparse, numpy as np, pandas as pd, matplotlib.pyplot as plt
from figure_style_redesign import *
from data_utils import *

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--project-root', type=Path, required=True); ap.add_argument('--output-dir', type=Path, required=True)
    a = ap.parse_args(); root = a.project_root.resolve(); out = a.output_dir.resolve(); out.mkdir(parents=True, exist_ok=True)
    b = 'results/submission_upgrade/H3_uptake_basis_density/'
    pp = modern(root, b + 'basis_primary_pair_level.parquet'); ps = modern(root, b + 'basis_primary_summary.csv'); pq = modern(root, b + 'density_quintile_summary.csv'); pc = modern(root, b + 'density_effect_correlations.csv'); pg = modern(root, b + 'basis_by_descriptor_group.csv')
    P = read_parquet(pp); S = read_csv(ps, {'metric', 'pairs', 'median_delta', 'positive_effect_fraction', 'bootstrap_95ci_low', 'bootstrap_95ci_high'}); Q = read_csv(pq, {'density_change_quintile', 'metric', 'median_delta'}); C = read_csv(pc, {'metric', 'spearman_rho'}); G = read_csv(pg, {'descriptor_group', 'metric', 'pairs', 'median_delta', 'positive_effect_fraction'})
    assert_n(P, 11072, 'H3 pair-level')
    apply_style()
    fig = plt.figure(figsize=(7.15, 5.45))
    gs = fig.add_gridspec(2, 2, left=.09, right=.98, bottom=.10, top=.965, wspace=.48, hspace=.48)
    A = fig.add_subplot(gs[0, 0]); B = fig.add_subplot(gs[0, 1]); Cc = fig.add_subplot(gs[1, 0]); D = fig.add_subplot(gs[1, 1])

    x = np.arange(len(S)); vals = S.median_delta.to_numpy(float); cols = [PALETTE['blue'], PALETTE['teal'], PALETTE['purple']]
    A.scatter(x, vals, s=48, color=cols, zorder=3)
    A.vlines(x, 0, vals, color=cols, lw=2.5)
    A.set_xticks(x, S.metric.astype(str))
    A.set_ylabel('Median change (native metric units)')
    ymax = max(vals)
    label_dx = [-0.03, 0.0, 0.03]
    label_dy = [0.10, 0.18, 0.10]
    for i, (xx, r) in enumerate(zip(x, S.itertuples())):
        A.text(xx + label_dx[i], r.median_delta + label_dy[i], f'{r.median_delta:.3g}\n{100*r.positive_effect_fraction:.1f}% +',
               ha='center', va='bottom', fontsize=6.1, bbox=dict(boxstyle='round,pad=0.12', fc='white', ec='none', alpha=0.88))
    A.set_ylim(-0.15, ymax * 1.15)
    clean_axis(A); panel_label(A, 'A')

    xcol = 'delta__mmol/g'; ycol = 'delta__v/v'
    if xcol not in P or ycol not in P:
        raise KeyError(f'H3 pair table must contain {xcol!r} and {ycol!r}')
    xv = pd.to_numeric(P[xcol]).to_numpy(float); yv = pd.to_numeric(P[ycol]).to_numpy(float)
    B.scatter(xv, yv, s=3, alpha=.10, color=PALETTE['blue'], edgecolors='none', rasterized=True)
    B.axhline(0, color=PALETTE['ink'], lw=.75); B.axvline(0, color=PALETTE['ink'], lw=.75)
    B.set(xlabel=r'$\Delta$CH$_4$ (mmol g$^{-1}$)', ylabel=r'$\Delta$CH$_4$ (v/v)')
    clean_axis(B); panel_label(B, 'B')

    q = Q[Q.metric == 'v/v'].copy(); q['o'] = q.density_change_quintile.str.extract(r'(\d+)').astype(int); q = q.sort_values('o')
    Cc.plot(q.density_change_quintile, q.median_delta, marker='o', lw=1.3, color=PALETTE['teal'])
    Cc.axhline(0, color=PALETTE['ink'], lw=.75)
    Cc.set(xlabel='Density-change quintile (Q1 decrease → Q5 increase)', ylabel='Median ΔCH$_4$ (v/v)')
    rho = float(C[C.metric == 'v/v'].spearman_rho.iloc[0])
    Cc.text(.97, .93, f'ρ(density change, v/v) = {rho:.3f}', transform=Cc.transAxes, ha='right', fontsize=6.2)
    clean_axis(Cc); panel_label(Cc, 'C')

    pivot = G.pivot(index='descriptor_group', columns='metric', values='positive_effect_fraction').loc[['ASA/AVA', 'Other'], ['mmol/g', 'v/v']] * 100
    xx = np.arange(2); w = .16
    D.bar(xx - w/2, pivot['mmol/g'], w, color=PALETTE['blue'], label='mmol/g')
    D.bar(xx + w/2, pivot['v/v'], w, color=PALETTE['teal'], label='v/v')
    D.axhline(50, color=PALETTE['gray'], ls='--', lw=.75)
    D.set_xticks(xx, ['ASA/AVA', 'Other'])
    D.set_ylabel('Positive pairs (%)')
    D.legend()
    clean_axis(D); panel_label(D, 'D')

    outs = export_figure(fig, out / 'Figure_S5_basis_density_robustness')
    plt.close(fig)
    save_manifest(out / 'Figure_S5_manifest.json', script=Path(__file__).name, sources=[str(pp), str(ps), str(pq), str(pc), str(pg)], outputs=outs,
                  notes={'status': 'secondary uptake-basis/density robustness; crystallographic v/v is not device or packed-bed capacity'})
if __name__ == '__main__':
    main()
