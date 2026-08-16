#!/usr/bin/env python3
from pathlib import Path
import argparse,numpy as np,pandas as pd,matplotlib.pyplot as plt
from figure_style_redesign import *
from data_utils import *
def short(r):
 cm={'methane-storage':'MS','landfill-gas':'LG','natural-gas-purification':'NGP','post-combustion-vsa':'PC','pre-combustion-40-40':'PreC'};gm={'CH4':r'CH$_4$','CO2':r'CO$_2$','N2':r'N$_2$','H2':r'H$_2$'};return f"{cm.get(str(r.context),str(r.context))} {gm.get(str(r.guest),str(r.guest))} {float(r.pressure_bar):g}"
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--project-root',type=Path,required=True);ap.add_argument('--output-dir',type=Path,required=True);a=ap.parse_args();root=a.project_root.resolve();out=a.output_dir.resolve();out.mkdir(parents=True,exist_ok=True);b='results/step3/06_cross_condition_consistency/';pm=modern(root,b+'mmolg_endpoint_metadata.csv');ps=modern(root,b+'mmolg_endpoint_spearman.csv');pa=modern(root,b+'mmolg_endpoint_sign_agreement.csv');m=read_csv(pm,{'endpoint_id','context','guest','pressure_bar'}).sort_values(['context','guest','pressure_bar']).reset_index(drop=True);ids=m.endpoint_id.astype(str).tolist();labels=[short(r) for r in m.itertuples()];S=pd.read_csv(ps,index_col=0);A=pd.read_csv(pa,index_col=0);S.index=S.index.astype(str);S.columns=S.columns.astype(str);A.index=A.index.astype(str);A.columns=A.columns.astype(str);S=S.loc[ids,ids];A=A.loc[ids,ids];apply_style();fig=plt.figure(figsize=(8.1,4.7));gs=fig.add_gridspec(1,2,left=.10,right=.95,bottom=.22,top=.94,wspace=.42);axs=[fig.add_subplot(gs[0,i]) for i in range(2)]
 im0=axs[0].imshow(S.to_numpy(float),vmin=-1,vmax=1,cmap='coolwarm',aspect='equal');im1=axs[1].imshow(A.to_numpy(float),vmin=0,vmax=1,cmap='Blues',aspect='equal')
 for ax,title,panel in zip(axs,['Spearman correlation','Sign agreement'],['A','B']):
  ax.set_xticks(range(len(labels)),labels,rotation=60,ha='right');ax.set_yticks(range(len(labels)),labels);ax.tick_params(labelsize=5.6);panel_label(ax,panel,x=-.16)
  changes=[i-.5 for i in range(1,len(m)) if m.loc[i,'context']!=m.loc[i-1,'context']]
  for c in changes:ax.axvline(c,color='white',lw=1.0);ax.axhline(c,color='white',lw=1.0)
 mask=(m.guest.astype(str)=='CH4') & (pd.to_numeric(m.pressure_bar)==65.0)
 if mask.any():
  idx=int(np.flatnonzero(mask.to_numpy())[0]);
  for ax in axs:ax.axvline(idx-.5,color=PALETTE['ink'],lw=.7);ax.axvline(idx+.5,color=PALETTE['ink'],lw=.7);ax.axhline(idx-.5,color=PALETTE['ink'],lw=.7);ax.axhline(idx+.5,color=PALETTE['ink'],lw=.7)
 cb0=fig.colorbar(im0,ax=axs[0],fraction=.045,pad=.025);cb0.set_label('Spearman ρ',fontsize=7);cb1=fig.colorbar(im1,ax=axs[1],fraction=.045,pad=.025);cb1.set_label('Agreement fraction',fontsize=7);outs=export_figure(fig,out/'Figure_S3');plt.close(fig);save_manifest(out/'Figure_S3_manifest.json',script=Path(__file__).name,sources=[str(pm),str(ps),str(pa)],outputs=outs,notes={'ordering':'Predefined context → gas → pressure; no outcome-driven clustering.'})
if __name__=='__main__':main()
