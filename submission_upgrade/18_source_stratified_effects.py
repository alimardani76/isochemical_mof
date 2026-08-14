#!/usr/bin/env python3
"""Project 17 same-source provenance heterogeneity audit (post-freeze)."""
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np,pandas as pd
import matplotlib.pyplot as plt
try:
    from p17_style_v2 import apply_style,clean_axis,panel_label,export_figure,PALETTE
except ImportError:
    apply_style=clean_axis=panel_label=export_figure=None

def first_existing(root,rels):
    for r in rels:
        p=root/r
        if p.is_file(): return p
    raise FileNotFoundError("Missing provenance pair file")
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--project-root",type=Path,required=True)
    ap.add_argument("--output-dir",type=Path,required=True); ap.add_argument("--min-pairs",type=int,default=100)
    a=ap.parse_args(); root=a.project_root.resolve(); out=a.output_dir.resolve(); out.mkdir(parents=True,exist_ok=True)
    p=first_existing(root,[Path("results/step3/09_database_provenance_robustness/01_pair_provenance.parquet"),
                           Path("Step 3 results/09_database_provenance_robustness/01_pair_provenance.parquet")])
    d=pd.read_parquet(p)
    req={"source_low","source_high","same_source_pair","delta_q_mmol_g","driver_descriptor","pair_max_fractional_difference"}
    if m:=req-set(d.columns): raise ValueError(f"missing {sorted(m)}")
    x=d[d["same_source_pair"].astype("boolean").fillna(False)].copy()
    x["source"]=x["source_low"].astype(str)
    rows=[]
    for s,g in x.groupby("source"):
        if len(g)<a.min_pairs: continue
        rows.append({"source":s,"pairs":len(g),"median_delta_q_mmol_g":float(g["delta_q_mmol_g"].median()),
                     "mean_delta_q_mmol_g":float(g["delta_q_mmol_g"].mean()),
                     "positive_effect_fraction":float((g["delta_q_mmol_g"]>0).mean()),
                     "median_pair_max_geometry_difference":float(g["pair_max_fractional_difference"].median()),
                     "asa_ava_fraction":float(g["driver_descriptor"].isin(["ASA","AVA"]).mean())})
    s=pd.DataFrame(rows).sort_values("pairs",ascending=False)
    s.to_csv(out/"source_stratified_primary.csv",index=False)
    comp=(x.groupby(["source","driver_descriptor"]).size().rename("pairs").reset_index())
    comp.to_csv(out/"source_stratified_composition.csv",index=False)
    if apply_style is not None and len(s):
        apply_style(7.0)
        fig,ax=plt.subplots(figsize=(6.8,3.2))
        y=np.arange(len(s))
        ax.scatter(s["median_delta_q_mmol_g"],y,s=np.sqrt(s["pairs"])*2.2,
                   color=PALETTE["navy"],alpha=.85)
        ax.axvline(0,color=PALETTE["ink"],lw=.7)
        ax.set_yticks(y,s["source"]); ax.set_xlabel("Median Δq (mmol g$^{-1}$)")
        ax.set_ylabel("ARC–MOF source"); clean_axis(ax); panel_label(ax,"A")
        export_figure(fig,out/"Figure_S6_source_stratified"); plt.close(fig)
    (out/"run_manifest.json").write_text(json.dumps({
        "script":"18_source_stratified_effects.py","completed_at_utc":datetime.now(timezone.utc).isoformat(),
        "post_freeze":True,"minimum_same_source_pairs":a.min_pairs,"input":str(p)},indent=2),encoding="utf-8")
    print("PASS",out); print(s.to_string(index=False))
if __name__=="__main__": main()
