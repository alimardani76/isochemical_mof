#!/usr/bin/env python3
from pathlib import Path
import argparse,numpy as np,pandas as pd,matplotlib.pyplot as plt
from figure_style_redesign import *
from data_utils import *
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--project-root',type=Path,required=True);ap.add_argument('--output-dir',type=Path,required=True);a=ap.parse_args();root=a.project_root.resolve();out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=True);p=modern(root,'results/step3/05_secondary_outcome_atlas/secondary_adsorption_mmolg_summary.csv');d=read_csv(p,{'guest','context','pressure_bar','median_symmetric_relative_effect'});d['pressure_bar']=pd.to_numeric(d.pressure_bar);d['eff']=100*pd.to_numeric(d.median_symmetric_relative_effect);apply_style();fig,ax=plt.subplots(figsize=(5.3,3.4));series=[('N2','post-combustion-vsa',PALETTE['purple'],r'N$_2$ / post-combustion'),('H2','pre-combustion-40-40',PALETTE['teal'],r'H$_2$ / pre-combustion')];ys=np.arange(len(series))[::-1]
 for y,(guest,ctx,col,label) in zip(ys,series):
  g=d[(d.guest==guest)&(d.context==ctx)].sort_values('pressure_bar');
  if len(g)<2:continue
  l,h=g.iloc[0],g.iloc[-1];ax.plot([l.eff,h.eff],[y,y],color=PALETTE['lightgray'],lw=1.5);ax.scatter(l.eff,y,s=42,facecolor='white',edgecolor=col,lw=1.2);ax.scatter(h.eff,y,s=44,color=col);ax.text(l.eff,y+.18,f'{l.pressure_bar:g} bar',ha='center',fontsize=6);ax.text(h.eff,y-.24,f'{h.pressure_bar:g} bar',ha='center',fontsize=6)
 ax.axvline(0,color=PALETTE['ink'],lw=.8);ax.set_yticks(ys,[s[3] for s in series]);ax.set_xlabel('Median relative uptake effect (%)');clean_axis(ax);outs=export_figure(fig,out/'Figure_S1');plt.close(fig);save_manifest(out/'Figure_S1_manifest.json',script=Path(__file__).name,sources=[str(p)],outputs=outs,notes={'discrete_endpoints':True})
if __name__=='__main__':main()
