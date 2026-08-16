#!/usr/bin/env python3
from pathlib import Path
import argparse,pandas as pd,matplotlib.pyplot as plt
from figure_style_redesign import *
from data_utils import *
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--project-root',type=Path,required=True);ap.add_argument('--output-dir',type=Path,required=True);a=ap.parse_args();root=a.project_root.resolve();out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=True);p=modern(root,'results/step3/05_secondary_outcome_atlas/secondary_process_summary.csv');d=read_csv(p,{'process','metric','median_symmetric_relative_effect'});af=d[d.metric=='afm'][['process','median_symmetric_relative_effect']].rename(columns={'median_symmetric_relative_effect':'afm'});ss=d[d.metric=='ssp'][['process','median_symmetric_relative_effect']].rename(columns={'median_symmetric_relative_effect':'ssp'});z=af.merge(ss,on='process').dropna();apply_style();fig,ax=plt.subplots(figsize=(5.2,3.8))
 for r in z.itertuples():
  x=100*float(r.ssp);y=100*float(r.afm);c=PROCESS_COLORS.get(str(r.process),PALETTE['blue']);ax.scatter(x,y,s=48,color=c,edgecolor='white',lw=.5,zorder=3);ax.annotate(DISPLAY_NAMES.get(str(r.process),str(r.process)),(x,y),xytext=(5,4),textcoords='offset points',fontsize=6.4)
 ax.axhline(0,color=PALETTE['ink'],lw=.8);ax.axvline(0,color=PALETTE['ink'],lw=.8);ax.set(xlabel='Median relative SSP effect (%)',ylabel='Median relative AFM effect (%)');clean_axis(ax);outs=export_figure(fig,out/'Figure_S2');plt.close(fig);save_manifest(out/'Figure_S2_manifest.json',script=Path(__file__).name,sources=[str(p)],outputs=outs)
if __name__=='__main__':main()
