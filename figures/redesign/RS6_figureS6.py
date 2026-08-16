#!/usr/bin/env python3
from pathlib import Path
import argparse,numpy as np,pandas as pd,matplotlib.pyplot as plt
from figure_style_redesign import *
from data_utils import *
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--project-root',type=Path,required=True);ap.add_argument('--output-dir',type=Path,required=True);a=ap.parse_args();root=a.project_root.resolve();out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=True);p=modern(root,'results/submission_upgrade/H6_source_stratified/source_stratified_primary.csv');S=read_csv(p,{'source','pairs','median_delta_q_mmol_g','median_pair_max_geometry_difference','asa_ava_fraction'}).sort_values('pairs',ascending=True);apply_style();fig=plt.figure(figsize=(7.15,3.35));gs=fig.add_gridspec(1,3,left=.10,right=.98,bottom=.19,top=.93,wspace=.48);axs=[fig.add_subplot(gs[0,i]) for i in range(3)];y=np.arange(len(S));labs=[f'{r.source} (n={int(r.pairs):,})' for r in S.itertuples()]
 vals=S.median_delta_q_mmol_g.to_numpy(float);axs[0].hlines(y,0,vals,color=PALETTE['blue'],lw=3);axs[0].scatter(vals,y,s=38,color=PALETTE['blue']);axs[0].axvline(0,color=PALETTE['ink'],lw=.8);axs[0].set_yticks(y,labs);axs[0].set_xlabel(r'Median $\Delta q$ (mmol g$^{-1}$)');clean_axis(axs[0]);panel_label(axs[0],'A')
 g=100*S.median_pair_max_geometry_difference.to_numpy(float);axs[1].hlines(y,0,g,color=PALETTE['purple'],lw=3);axs[1].scatter(g,y,s=38,color=PALETTE['purple']);axs[1].set_yticks(y,[]);axs[1].set_xlabel('Median maximum geometry contrast (%)');clean_axis(axs[1]);panel_label(axs[1],'B')
 f=100*S.asa_ava_fraction.to_numpy(float);axs[2].hlines(y,0,f,color=PALETTE['teal'],lw=3);axs[2].scatter(f,y,s=38,color=PALETTE['teal']);axs[2].set_yticks(y,[]);axs[2].set(xlabel='ASA/AVA-labelled pairs (%)',xlim=(0,100));clean_axis(axs[2]);panel_label(axs[2],'C');outs=export_figure(fig,out/'Figure_S6_source_stratified');plt.close(fig);save_manifest(out/'Figure_S6_manifest.json',script=Path(__file__).name,sources=[str(p)],outputs=outs,notes={'status':'provenance/applicability diagnostic; source is not interpreted causally'})
if __name__=='__main__':main()
