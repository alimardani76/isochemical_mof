#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse
import numpy as np,pandas as pd,matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.patches import Patch
from figure_style_redesign import *
from data_utils import *
ORDER=['positive_both','pressure_activated','pressure_suppressed','negative_both'];LAB={'positive_both':'Positive both','pressure_activated':'Pressure activated','pressure_suppressed':'Pressure suppressed','negative_both':'Negative both'};COL={'positive_both':PALETTE['blue'],'pressure_activated':PALETTE['amber'],'pressure_suppressed':PALETTE['purple'],'negative_both':PALETTE['slate']};DORDER=['ASA','AVA','AVAf','POAVA','POAVAf','Df','Di','Dif']
def load(root):
 b='results/step3/07_response_archetypes/';ps=[modern(root,b+n) for n in ['response_archetypes.parquet','response_archetype_summary.csv','response_archetype_driver_summary.csv','response_archetype_topology_summary.csv']];return(read_parquet(ps[0]),read_csv(ps[1]),read_csv(ps[2]),read_csv(ps[3])),[str(p) for p in ps]
def heat(ax,A,S):
 x=pd.to_numeric(A.positive_fraction_low_pressure).to_numpy();y=pd.to_numeric(A.positive_fraction_high_pressure).to_numpy();bins=np.linspace(-.055,1.055,11);c,xe,ye=np.histogram2d(x,y,bins=[bins,bins]);p=c[c>0];m=ax.pcolormesh(xe,ye,c.T,cmap='Blues',norm=LogNorm(vmin=max(1,p.min()),vmax=p.max()),edgecolors='white',linewidth=.25);ax.axvline(.5,color=PALETTE['ink'],lw=.9);ax.axhline(.5,color=PALETTE['ink'],lw=.9);ax.set(xlim=(0,1),ylim=(0,1),xlabel='Positive endpoints at low pressure (%)',ylabel='Positive endpoints at high pressure (%)');ax.set_xticks([0,.5,1],[0,50,100]);ax.set_yticks([0,.5,1],[0,50,100]);frac={r.archetype:100*float(r.fraction) for r in S.itertuples()};labels=[(.76,.80,'positive_both'),(.24,.80,'pressure_activated'),(.76,.20,'pressure_suppressed'),(.24,.20,'negative_both')]
 for xx,yy,k in labels:ax.text(xx,yy,f"{LAB[k]}\n{frac[k]:.1f}%",transform=ax.transAxes,ha='center',va='center',fontsize=6.5,fontweight='bold',color=PALETTE['ink'])
 cb=ax.figure.colorbar(m,ax=ax,fraction=.045,pad=.025);cb.set_label('Pairs',fontsize=7);clean_axis(ax);panel_label(ax,'A')
def prev(ax,S):
 S=S.copy();S['archetype']=pd.Categorical(S.archetype,categories=ORDER,ordered=True);S=S.sort_values('archetype');v=100*S.fraction.to_numpy(float);x=np.arange(4);bars=ax.bar(x,v,color=[COL[k] for k in ORDER],width=.6);ax.set_xticks(x,['Positive\nboth','Pressure\nactivated','Pressure\nsuppressed','Negative\nboth']);ax.set_ylabel('Frozen pairs (%)');ax.set_ylim(0,max(v)*1.23)
 for b,r,p in zip(bars,S.itertuples(),v):ax.text(b.get_x()+b.get_width()/2,p+max(v)*.03,f'{p:.1f}%\nn={int(r.pairs):,}',ha='center',fontsize=6.2)
 act=v[1];sup=v[2];ax.text(1.5,max(v)*1.12,f'activation / suppression = {act/sup:.1f}×',ha='center',fontsize=7,fontweight='bold',color=PALETTE['vermillion']);clean_axis(ax);panel_label(ax,'B')
def comp(ax,D):
 Z=D[D.driver_descriptor.isin(DORDER)].copy();Z['o']=Z.driver_descriptor.map({k:i for i,k in enumerate(DORDER)});Z=Z.sort_values('o',ascending=False);y=np.arange(len(Z));left=np.zeros(len(Z));mp={'positive_both':'positive_both_fraction','pressure_activated':'pressure_activated_fraction','pressure_suppressed':'pressure_suppressed_fraction','negative_both':'negative_both_fraction'}
 for k in ORDER:
  v=100*pd.to_numeric(Z[mp[k]]).to_numpy();ax.barh(y,v,left=left,height=.64,color=COL[k],edgecolor='white',lw=.35);left+=v
 ax.set_yticks(y,[f'{descriptor_label(r.driver_descriptor)}  n={int(r.pairs):,}' for r in Z.itertuples()]);ax.set(xlim=(0,100),xlabel='Archetype composition (%)');ax.legend(handles=[Patch(facecolor=COL[k],label=LAB[k]) for k in ORDER],ncol=4,loc='lower center',bbox_to_anchor=(.5,1.01),fontsize=6.1,columnspacing=.8);ax.axhline(2.5,color=PALETTE['lightgray'],lw=.8);ax.text(101,5.7,'accessible-space',rotation=90,va='center',fontsize=6,color=PALETTE['blue'],clip_on=False);ax.text(101,1,'diameter',rotation=90,va='center',fontsize=6,color=PALETTE['purple'],clip_on=False);clean_axis(ax);panel_label(ax,'C')
def topo(ax,T,S):
 z=T.copy();z['pairs']=pd.to_numeric(z.pairs).astype(int);z=z[z.pairs>=100].sort_values('pressure_activated_fraction');y=np.arange(len(z));v=100*pd.to_numeric(z.pressure_activated_fraction).to_numpy();overall=100*float(S[S.archetype=='pressure_activated'].fraction.iloc[0]);ax.hlines(y,0,v,color=PALETTE['amber'],lw=3.4);ax.scatter(v,y,s=35,color=PALETTE['amber']);ax.axvline(overall,color=PALETTE['ink'],ls='--',lw=.8);ax.set_yticks(y,[f'{r.topology} (n={int(r.pairs):,})' for r in z.itertuples()]);ax.set_xlabel('Pressure-activated pairs (%)');ax.text(overall,1.02,f'overall {overall:.1f}%',transform=ax.get_xaxis_transform(),ha='center',fontsize=6.2);clean_axis(ax);panel_label(ax,'D')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--project-root',type=Path,required=True);ap.add_argument('--output-dir',type=Path,required=True);a=ap.parse_args();out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=True);apply_style();(A,S,D,T),src=load(a.project_root.resolve());assert_n(A,11072,'archetype pairs');fig=plt.figure(figsize=(7.15,5.45));gs=fig.add_gridspec(2,5,left=.09,right=.98,bottom=.10,top=.965,wspace=.65,hspace=.48);aa=fig.add_subplot(gs[0,:3]);bb=fig.add_subplot(gs[0,3:]);cc=fig.add_subplot(gs[1,:3]);dd=fig.add_subplot(gs[1,3:]);heat(aa,A,S);prev(bb,S);comp(cc,D);topo(dd,T,S);outs=export_figure(fig,out/'Figure_4_concept');plt.close(fig);save_manifest(out/'Figure_4_concept_manifest.json',script=Path(__file__).name,sources=src,outputs=outs,notes={'visual_hierarchy':'Panel C receives greater width; Panel A directly labels majority-rule archetype quadrants.'})
if __name__=='__main__':main()
