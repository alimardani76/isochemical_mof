#!/usr/bin/env python3
from pathlib import Path
import argparse, numpy as np, pandas as pd, matplotlib.pyplot as plt
from figure_style_redesign import *
from data_utils import *
DESCS = ['ASA', 'AVA', 'AVAf', 'POAVA', 'POAVAf', 'Di', 'Df', 'Dif']

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--project-root', type=Path, required=True); ap.add_argument('--output-dir', type=Path, required=True)
    a = ap.parse_args(); root = a.project_root.resolve(); out = a.output_dir.resolve(); out.mkdir(parents=True, exist_ok=True)
    b = 'results/submission_upgrade/H2_geometry_attribution/'
    pp = modern(root, b + 'geometry_attribution_pair_level.parquet'); pc = modern(root, b + 'descriptor_difference_correlation.csv'); ps = modern(root, b + 'clean_dominant_primary_summary.csv'); pm = modern(root, b + 'descriptor_threshold_multiplicity.csv')
    P = read_parquet(pp, {'top1_div_top2', 'delta_q_mmol_g'}); C = read_csv(pc); S = read_csv(ps, {'descriptor', 'minimum_top1_top2_ratio', 'pairs', 'median_delta_q_mmol_g'}); M = read_csv(pm, {'n_ge_10pct', 'pairs', 'median_delta_q_mmol_g'})
    assert_n(P, 11072, 'H2 pair-level')
    apply_style()
    fig = plt.figure(figsize=(7.15, 5.45))
    gs = fig.add_gridspec(2, 2, left=.09, right=.98, bottom=.10, top=.965, wspace=.45, hspace=.47)
    A = fig.add_subplot(gs[0, 0]); B = fig.add_subplot(gs[0, 1]); Cc = fig.add_subplot(gs[1, 0]); D = fig.add_subplot(gs[1, 1])

    vals = pd.to_numeric(P.top1_div_top2).replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
    x = np.linspace(1, 2.5, 160); ret = np.array([(vals >= t).sum() for t in x])
    A.plot(x, ret, color=PALETTE['blue'], lw=1.5)
    A.set(xlabel='Minimum top1/top2 geometry-difference ratio', ylabel='Retained frozen pairs')
    for r in [1.10, 1.25, 1.50]:
        n = int((pd.to_numeric(P.top1_div_top2) >= r).sum())
        A.axvline(r, color=PALETTE['gray'], lw=.7, ls='--')
        A.scatter([r], [n], s=24, color=PALETTE['vermillion'], zorder=3)
        A.text(r, n + 170, f'{r:.2f}\nn={n:,}', ha='center', fontsize=5.8,
               bbox=dict(boxstyle='round,pad=0.14', fc='white', ec='none', alpha=0.90))
    clean_axis(A); panel_label(A, 'A')

    mat = C.set_index(C.columns[0]).loc[DESCS, DESCS].to_numpy(float)
    im = B.imshow(mat, vmin=0, vmax=1, cmap='Blues')
    B.set_xticks(range(8), [descriptor_label(x) for x in DESCS], rotation=45, ha='right')
    B.set_yticks(range(8), [descriptor_label(x) for x in DESCS])
    B.tick_params(labelsize=6.2)
    cb = fig.colorbar(im, ax=B, fraction=.045, pad=.025); cb.set_label('Spearman ρ', fontsize=7)
    panel_label(B, 'B')

    focus = {'ASA', 'AVA', 'Df'}
    label_offsets = {
        ('ASA', 1.25): (0.015, 0.08), ('ASA', 1.50): (0.012, 0.06),
        ('AVA', 1.25): (0.015, 0.04), ('AVA', 1.50): (0.010, -0.08),
        ('Df', 1.25): (0.010, -0.12), ('Df', 1.50): (0.010, 0.02),
    }
    for desc in DESCS:
        g = S[S.descriptor == desc].sort_values('minimum_top1_top2_ratio')
        Cc.plot(g.minimum_top1_top2_ratio, g.median_delta_q_mmol_g, marker='o', ms=3.5, lw=1.0,
                color=descriptor_color(desc), alpha=.35 if desc not in focus else 1.0,
                label=descriptor_label(desc) if desc in focus else None)
        if desc in focus:
            for r in g.itertuples():
                key = (desc, float(r.minimum_top1_top2_ratio))
                if key in label_offsets:
                    dx, dy = label_offsets[key]
                    Cc.text(r.minimum_top1_top2_ratio + dx, r.median_delta_q_mmol_g + dy, f'n={int(r.pairs)}', fontsize=5.4,
                            ha='center', va='bottom', bbox=dict(boxstyle='round,pad=0.10', fc='white', ec='none', alpha=0.85))
    Cc.axhline(0, color=PALETTE['ink'], lw=.8)
    Cc.set(xlabel='Minimum top1/top2 ratio', ylabel=r'Median primary $\Delta q$ (mmol g$^{-1}$)')
    Cc.legend(loc='best', ncol=3)
    clean_axis(Cc); panel_label(Cc, 'C')

    xM = pd.to_numeric(M.n_ge_10pct).to_numpy(int); yM = pd.to_numeric(M.median_delta_q_mmol_g).to_numpy(float)
    D.plot(xM, yM, marker='o', lw=1.2, color=PALETTE['blue'])
    D.axhline(0, color=PALETTE['ink'], lw=.8)
    D.set(xlabel='Descriptors changing ≥10%', ylabel=r'Median primary $\Delta q$ (mmol g$^{-1}$)', xticks=xM)
    clean_axis(D); panel_label(D, 'D')

    outs = export_figure(fig, out / 'Figure_S4_geometry_attribution_stability')
    plt.close(fig)
    save_manifest(out / 'Figure_S4_manifest.json', script=Path(__file__).name, sources=[str(pp), str(pc), str(ps), str(pm)], outputs=outs,
                  plotting_only_aggregation=['Panel A cumulative retained-pair curve from committed H2 pair-level table'],
                  notes={'status': 'secondary/post-freeze robustness; largest-contrast label is not causal'})
if __name__ == '__main__':
    main()
