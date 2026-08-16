#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter
from figure_style_redesign import *
from data_utils import *

COHORT=[("ARC–MOF registry",279019),("Charged CIFs",242363),("Same recorded\nchemistry",48366),("Same recorded\narchitecture",44511),("10% geometry\neligible",26146),("Frozen\npairs",11072)]

def load(root):
    paths=[modern(root,"results/step2/02_geometry_threshold_census/geometry_threshold_families.parquet"),modern(root,"results/step2/02_geometry_threshold_census/geometry_threshold_census.csv"),modern(root,"results/step2/03_geometry_pairs/primary_geometry_pairs.parquet"),modern(root,"results/step2/03_geometry_pairs/primary_pair_driver_census.csv")]
    F=read_parquet(paths[0],{"max_pore_fractional_span"});C=read_csv(paths[1],{"threshold_percent","eligible_families","eligible_frameworks"});P=read_parquet(paths[2],{"pair_max_fractional_difference","pair_mean_fractional_difference"});D=read_csv(paths[3],{"driver_descriptor","selected_pairs"});assert_n(P,11072,"primary pairs");return (F,C,P,D),[str(p) for p in paths]

def workflow(ax):
    ax.set_axis_off(); xs=np.linspace(.08,.86,len(COHORT)); y=.56
    for i,((lab,n),x) in enumerate(zip(COHORT,xs)):
        fc=PALETTE["blue"] if i==5 else (PALETTE["slate"] if i==0 else PALETTE["pale"]);tc="white" if i in {0,5} else PALETTE["ink"]
        box=FancyBboxPatch((x-.07,y-.12),.14,.24,boxstyle="round,pad=.008,rounding_size=.015",transform=ax.transAxes,facecolor=fc,edgecolor=PALETTE["lightgray"] if i not in {0,5} else "none",lw=.6);ax.add_patch(box)
        ax.text(x,y+.035,f"{n:,}",transform=ax.transAxes,ha="center",fontweight="bold",fontsize=8.1,color=tc);ax.text(x,y-.055,lab,transform=ax.transAxes,ha="center",va="center",fontsize=6.2,color=tc,linespacing=1.05)
        if i<5: ax.annotate("",xy=(xs[i+1]-.075,y),xytext=(x+.075,y),xycoords=ax.transAxes,textcoords=ax.transAxes,arrowprops=dict(arrowstyle="-|>",color=PALETTE["gray"],lw=.75,mutation_scale=8))
    gate_x=.945;ax.plot([.905,.905],[.22,.88],transform=ax.transAxes,color=PALETTE["vermillion"],lw=1.3,clip_on=False)
    ax.text(.905,.91,"OUTCOMES NOT USED",transform=ax.transAxes,ha="center",va="bottom",fontsize=6.3,fontweight="bold",color=PALETTE["vermillion"])
    box=FancyBboxPatch((gate_x-.048,y-.12),.096,.24,boxstyle="round,pad=.008,rounding_size=.015",transform=ax.transAxes,facecolor="white",edgecolor=PALETTE["vermillion"],lw=1.0);ax.add_patch(box)
    ax.text(gate_x,y,"Open\nadsorption\noutcomes",transform=ax.transAxes,ha="center",va="center",fontsize=6.4,fontweight="bold")
    ax.annotate("",xy=(gate_x-.052,y),xytext=(.885,y),xycoords=ax.transAxes,textcoords=ax.transAxes,arrowprops=dict(arrowstyle="-|>",color=PALETTE["vermillion"],lw=.85,mutation_scale=8))
    labels=["parse","match chemistry","match topology +\ndimensionality","freeze 10% +\nselect one pair","deterministic pair"]
    for i,t in enumerate(labels):ax.text((xs[i]+xs[i+1])/2,.27,t,transform=ax.transAxes,ha="center",fontsize=5.8,color=PALETTE["slate"])
    panel_label(ax,"A",x=-.015,y=.98)

def hist_support(ax,F,C):
    v=pd.to_numeric(F.max_pore_fractional_span).clip(0,1).to_numpy()*100;ax.hist(v,bins=np.linspace(0,100,41),color=PALETTE["sky"],edgecolor="white",linewidth=.3);ax.axvline(10,color=PALETTE["ink"],lw=1.1);ax.text(12,ax.get_ylim()[1]*.88,"10% frozen threshold",fontsize=6.5,fontweight="bold")
    C=C.copy();C["threshold_percent"]=pd.to_numeric(C.threshold_percent).astype(int);lookup={int(r.threshold_percent):int(r.eligible_families) for r in C.itertuples()};strip="   |   ".join(f"{t}%: {lookup[t]:,}" for t in [5,10,20,30] if t in lookup);ax.text(.5,-.27,strip,transform=ax.transAxes,ha="center",fontsize=6.3,color=PALETTE["slate"])
    ax.set(xlabel="Maximum within-family pore span (%)",ylabel="Families",xlim=(0,100));ax.yaxis.set_major_formatter(FuncFormatter(lambda x,p:f"{int(x):,}"));clean_axis(ax);panel_label(ax,"B")

def class_support(ax,D):
    D=D.copy();D["selected_pairs"]=pd.to_numeric(D.selected_pairs).astype(int);order=["Dif","Di","Df","POAVAf","POAVA","AVAf","ASA","AVA"];D["o"]=D.driver_descriptor.map({k:i for i,k in enumerate(order)});D=D.sort_values(["o","selected_pairs"]);y=np.arange(len(D));vals=D.selected_pairs.to_numpy();cols=[descriptor_color(x) for x in D.driver_descriptor]
    ax.barh(y,vals,color=cols,height=.64);ax.set_yticks(y,[descriptor_label(x) for x in D.driver_descriptor]);ax.set_xlabel("Frozen primary pairs");ax.xaxis.set_major_formatter(FuncFormatter(lambda x,p:f"{int(x):,}"));ax.set_xlim(0,max(vals)*1.15)
    for yi,n in zip(y,vals):ax.text(n+max(vals)*.018,yi,f"{n:,}",va="center",fontsize=6.1)
    ax.text(.98,.06,"accessible-space",transform=ax.transAxes,ha="right",color=PALETTE["blue"],fontsize=6.2,fontweight="bold");ax.text(.98,.14,"diameter",transform=ax.transAxes,ha="right",color=PALETTE["purple"],fontsize=6.2,fontweight="bold")
    clean_axis(ax);panel_label(ax,"C")

def multidim(ax,P):
    x=pd.to_numeric(P.pair_max_fractional_difference).to_numpy()*100;y=pd.to_numeric(P.pair_mean_fractional_difference).to_numpy()*100;ax.scatter(x,y,s=4,alpha=.13,color=PALETTE["blue"],edgecolors="none",rasterized=True);mx,my=np.median(x),np.median(y);ax.axvline(mx,color=PALETTE["gray"],ls="--",lw=.75);ax.axhline(my,color=PALETTE["gray"],ls="--",lw=.75);ax.text(.97,.05,f"median max {mx:.1f}%\nmedian mean {my:.1f}%",transform=ax.transAxes,ha="right",fontsize=6.2)
    ax.set(xlabel="Maximum pair difference (%)",ylabel="Mean pair difference (%)",xlim=(0,None),ylim=(0,None));clean_axis(ax);panel_label(ax,"D")

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--project-root",type=Path,required=True);ap.add_argument("--output-dir",type=Path,required=True);a=ap.parse_args();root=a.project_root.resolve();out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=True);apply_style();(F,C,P,D),src=load(root)
    fig=plt.figure(figsize=(7.15,5.05));gs=fig.add_gridspec(2,3,left=.075,right=.98,bottom=.11,top=.965,wspace=.50,hspace=.58,height_ratios=[.83,1.17]);axA=fig.add_subplot(gs[0,:]);workflow(axA);axB=fig.add_subplot(gs[1,0]);axC=fig.add_subplot(gs[1,1]);axD=fig.add_subplot(gs[1,2]);hist_support(axB,F,C);class_support(axC,D);multidim(axD,P)
    outputs=export_figure(fig,out/"Figure_1_concept");plt.close(fig);save_manifest(out/"Figure_1_concept_manifest.json",script=Path(__file__).name,sources=src,outputs=outputs,plotting_only_aggregation=["Panel B embeds audited threshold-support counts"],notes={"panel_migration":"Current topology-support panel is omitted from concept main figure; retain in SI/archive."})
if __name__=="__main__":main()
