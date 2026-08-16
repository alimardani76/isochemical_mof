#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse
import numpy as np,pandas as pd,matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from figure_style_redesign import *
from data_utils import *

def load(root):
 b="results/step3/05_secondary_outcome_atlas/";p1=modern(root,b+"secondary_adsorption_mmolg_summary.csv");p2=modern(root,b+"secondary_process_summary.csv");return(read_csv(p1,{"guest","context","pressure_bar","median_symmetric_relative_effect"}),read_csv(p2,{"process","metric","median_delta"})),[str(p1),str(p2)]
def endpoint(ax,A,guest,contexts,panel):
 z=A.copy();z["pressure_bar"]=pd.to_numeric(z.pressure_bar);z["eff"]=100*pd.to_numeric(z.median_symmetric_relative_effect);z=z[(z.guest==guest)&z.context.isin(contexts)];ys=np.arange(len(contexts))[::-1]
 for y,c in zip(ys,contexts):
  g=z[z.context==c].sort_values('pressure_bar');
  if len(g)<2:continue
  l,h=g.iloc[0],g.iloc[-1];col=PROCESS_COLORS[c];ax.plot([l.eff,h.eff],[y,y],lw=1.5,color=PALETTE['lightgray']);ax.scatter(l.eff,y,s=38,facecolor='white',edgecolor=col,lw=1.25,zorder=3);ax.scatter(h.eff,y,s=42,color=col,edgecolor='white',lw=.35,zorder=3);ax.text(l.eff,y+.22,f"{l.pressure_bar:g}",ha='center',fontsize=5.7,color=PALETTE['slate']);ax.text(h.eff,y-.28,f"{h.pressure_bar:g}",ha='center',fontsize=5.7,color=PALETTE['slate'])
 ax.axvline(0,color=PALETTE['ink'],lw=.8);ax.set_yticks(ys,[DISPLAY_NAMES[c] for c in contexts]);ax.set_xlabel('Median relative uptake effect (%)');ax.text(.98,.96,'pressure labels in bar',transform=ax.transAxes,ha='right',va='top',fontsize=5.8,color=PALETTE['slate']);clean_axis(ax);panel_label(ax,panel)
def aligned_process(ax,P,metric,order,panel,xlabel,show_y=True):
 z=P[P.metric==metric].set_index('process');ys=np.arange(len(order))[::-1];vals=[]
 for y,p in zip(ys,order):
  if p not in z.index: vals.append(np.nan);continue
  r=z.loc[p];v=float(r.median_delta);vals.append(v);col=PROCESS_COLORS[p];ax.plot([0,v],[y,y],lw=2.7,color=col);ax.scatter(v,y,s=36,color=col,zorder=3);ax.text(v,y+.18,f"{v:+.2f}",ha='center',va='bottom',fontsize=5.9)
 ax.axvline(0,color=PALETTE['ink'],lw=.8);ax.set_yticks(ys,[DISPLAY_NAMES[p] for p in order] if show_y else []);ax.set_xlabel(xlabel);clean_axis(ax);panel_label(ax,panel)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--project-root',type=Path,required=True);ap.add_argument('--output-dir',type=Path,required=True);a=ap.parse_args();out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=True);apply_style();(A,P),src=load(a.project_root.resolve());fig=plt.figure(figsize=(7.15,5.15));gs=fig.add_gridspec(2,2,left=.125,right=.98,bottom=.105,top=.96,wspace=.42,hspace=.48,height_ratios=[1.1,.9]);aa=fig.add_subplot(gs[0,0]);bb=fig.add_subplot(gs[0,1]);endpoint(aa,A,'CH4',['methane-storage','landfill-gas','natural-gas-purification'],'A');endpoint(bb,A,'CO2',['post-combustion-vsa','natural-gas-purification','landfill-gas','pre-combustion-40-40'],'B');order=['methane-storage-psa','landfill-gas-vpsa','natural-gas-purification','post-combustion-vsa','pre-combustion-40-40'];cc=fig.add_subplot(gs[1,0]);dd=fig.add_subplot(gs[1,1]);aligned_process(cc,P,'mmol/g_working_capacity',order,'C',r'Median working-capacity change (mmol g$^{-1}$)',True);aligned_process(dd,P,'selectivity',order,'D','Median selectivity change',False);dd.text(.02,.03,'Methane-storage selectivity: not defined in the audited process table',transform=dd.transAxes,fontsize=5.6,color=PALETTE['slate']);outs=export_figure(fig,out/'Figure_3_concept');plt.close(fig);save_manifest(out/'Figure_3_concept_manifest.json',script=Path(__file__).name,sources=src,outputs=outs,notes={'visual_claim':'Discrete operating endpoints and aligned process objectives; no continuous pressure trajectory is inferred.'})
if __name__=='__main__':main()
