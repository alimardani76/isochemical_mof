#!/usr/bin/env python3
"""Project 17 post-freeze gravimetric/volumetric and density robustness.

Uses the frozen pair catalogue/orientation. Does not alter the primary endpoint.
The v/v and density results are secondary robustness analyses.
"""

from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

try:
    from p17_style_v2 import apply_style, clean_axis, panel_label, export_figure, PALETTE
except ImportError:
    apply_style = clean_axis = panel_label = export_figure = None

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def first_existing(root: Path, rels, required=True):
    for rel in rels:
        p=root/rel
        if p.is_file(): return p
    if required:
        raise FileNotFoundError("None of these paths exists:\n"+"\n".join(str(root/r) for r in rels))
    return None

def sym(high, low):
    den=np.abs(high)+np.abs(low)
    return np.divide(2*(high-low),den,out=np.zeros_like(high,dtype=float),where=den!=0)

def bootstrap_median(values, reps=10000, seed=17, chunk=250):
    values=np.asarray(values,dtype=float)
    rng=np.random.default_rng(seed)
    n=len(values); out=np.empty(reps)
    k0=0
    while k0<reps:
        k=min(chunk,reps-k0)
        idx=rng.integers(0,n,size=(k,n))
        out[k0:k0+k]=np.median(values[idx],axis=1)
        k0+=k
    return np.percentile(out,[2.5,97.5]), out

def find_density_col(df):
    for c in ["Density","density","framework_density","density_g_cm3"]:
        if c in df.columns: return c
    raise KeyError("No density column found. Available: "+", ".join(df.columns))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,required=True)
    ap.add_argument("--output-dir",type=Path,required=True)
    args=ap.parse_args()
    root=args.project_root.resolve(); out=args.output_dir.resolve(); out.mkdir(parents=True,exist_ok=True)

    ads_path=first_existing(root,[
        Path("results/step3/05_secondary_outcome_atlas/secondary_adsorption_pair_effects.parquet"),
        Path("Step 3 results/05_secondary_outcome_atlas/secondary_adsorption_pair_effects.parquet")])
    primary_path=first_existing(root,[
        Path("results/step3/04_primary_ch4_analysis/primary_ch4_pair_effects.parquet"),
        Path("Step 3 results/04_primary_ch4_analysis/primary_ch4_pair_effects.parquet")])
    geom_path=first_existing(root,[
        Path("results/step2/01_geometry_variation/geometry_variation_frameworks.parquet"),
        Path("Step 2 results/01_geometry_variation/geometry_variation_frameworks.parquet")])
    process_path=first_existing(root,[
        Path("results/step3/05_secondary_outcome_atlas/secondary_process_pair_effects.parquet"),
        Path("Step 3 results/05_secondary_outcome_atlas/secondary_process_pair_effects.parquet")], required=False)

    ads=pd.read_parquet(ads_path)
    primary=pd.read_parquet(primary_path)
    geom=pd.read_parquet(geom_path)

    required_ads={"architecture_group_id","source","temperature_K","pressure_bar","metric",
                  "value_geometry_low","value_geometry_high","delta"}
    if missing:=required_ads-set(ads.columns):
        raise ValueError(f"secondary adsorption table missing {sorted(missing)}")

    target=ads[
        ads["source"].astype(str).eq("methane.csv") &
        pd.to_numeric(ads["temperature_K"],errors="coerce").eq(298.0) &
        pd.to_numeric(ads["pressure_bar"],errors="coerce").eq(65.0) &
        ads["metric"].astype(str).isin(["mmol/g","v/v","wt%"])
    ].copy()
    if target.empty: raise RuntimeError("No methane 298 K, 65 bar basis rows found")

    wide=target.pivot(index="architecture_group_id",columns="metric",
                      values=["value_geometry_low","value_geometry_high","delta"])
    wide.columns=[f"{a}__{b}" for a,b in wide.columns]
    wide=wide.reset_index()

    keep_cols=["architecture_group_id","driver_low_mof_id","driver_high_mof_id","driver_descriptor",
               "pair_max_fractional_difference","primary_10pct_pair",
               "sensitivity_20pct_pair","sensitivity_30pct_pair","delta_q_mmol_g"]
    meta=primary[[c for c in keep_cols if c in primary.columns]].copy()
    x=meta.merge(wide,on="architecture_group_id",how="inner",validate="one_to_one")
    if len(x)!=len(primary):
        raise RuntimeError(f"basis join incomplete: primary={len(primary)}, basis={len(x)}")
    if len(x) != 11072:
        raise RuntimeError(f"expected 11,072 frozen pairs, found {len(x):,}")

    # Guard the frozen core: the secondary-atlas mmol/g value at the primary
    # condition must reproduce the already frozen primary pair effect exactly.
    atlas_primary = pd.to_numeric(x["delta__mmol/g"], errors="raise").to_numpy(float)
    frozen_primary = pd.to_numeric(x["delta_q_mmol_g"], errors="raise").to_numpy(float)
    max_abs_primary_mismatch = float(np.max(np.abs(atlas_primary - frozen_primary)))
    if max_abs_primary_mismatch > 1e-10:
        raise RuntimeError(
            f"secondary atlas does not reproduce frozen primary effects; max abs mismatch="
            f"{max_abs_primary_mismatch:.3e}"
        )

    density_col=find_density_col(geom)
    id_col="mof_id"
    if id_col not in geom.columns: raise KeyError("geometry framework table lacks mof_id")
    den_map=pd.to_numeric(geom.set_index(id_col)[density_col],errors="coerce")
    x["density_low"]=x["driver_low_mof_id"].map(den_map)
    x["density_high"]=x["driver_high_mof_id"].map(den_map)
    x["delta_density"]=x["density_high"]-x["density_low"]
    x["symmetric_relative_density_effect"]=sym(x["density_high"].to_numpy(float),x["density_low"].to_numpy(float))
    x.to_parquet(out/"basis_primary_pair_level.parquet",index=False)

    summary_rows=[]; boot_rows=[]
    for metric in ["mmol/g","v/v","wt%"]:
        col=f"delta__{metric}"
        if col not in x: continue
        v=pd.to_numeric(x[col],errors="coerce").dropna().to_numpy()
        ci, boots=bootstrap_median(v)
        summary_rows.append({
            "metric":metric,"pairs":len(v),"median_delta":float(np.median(v)),
            "mean_delta":float(np.mean(v)),"positive_effect_fraction":float(np.mean(v>0)),
            "bootstrap_95ci_low":float(ci[0]),"bootstrap_95ci_high":float(ci[1])
        })
        boot_rows.extend({"metric":metric,"bootstrap_median":float(z)} for z in boots)
    summary=pd.DataFrame(summary_rows)
    summary.to_csv(out/"basis_primary_summary.csv",index=False)
    pd.DataFrame(boot_rows).to_csv(out/"basis_primary_bootstrap.csv",index=False)

    tier_rows=[]
    tiers=[("10%","primary_10pct_pair"),("20%","sensitivity_20pct_pair"),("30%","sensitivity_30pct_pair")]
    for t,flag in tiers:
        for metric in ["mmol/g","v/v"]:
            col=f"delta__{metric}"
            y=x[x[flag].astype("boolean").fillna(False)]
            vals=pd.to_numeric(y[col],errors="coerce").dropna()
            tier_rows.append({"tier":t,"metric":metric,"pairs":len(vals),
                              "median_delta":float(vals.median()),
                              "positive_effect_fraction":float((vals>0).mean())})
    pd.DataFrame(tier_rows).to_csv(out/"basis_by_geometry_tier.csv",index=False)

    x["descriptor_group"]=np.where(x["driver_descriptor"].isin(["ASA","AVA"]),"ASA/AVA","Other")
    dg=[]
    for g,y in x.groupby("descriptor_group"):
        for metric in ["mmol/g","v/v"]:
            vals=pd.to_numeric(y[f"delta__{metric}"],errors="coerce").dropna()
            dg.append({"descriptor_group":g,"metric":metric,"pairs":len(vals),
                       "median_delta":float(vals.median()),
                       "positive_effect_fraction":float((vals>0).mean())})
    dg=pd.DataFrame(dg); dg.to_csv(out/"basis_by_descriptor_group.csv",index=False)

    valid=x["symmetric_relative_density_effect"].notna()
    x.loc[valid,"density_change_quintile"]=pd.qcut(
        x.loc[valid,"symmetric_relative_density_effect"],5,
        labels=["Q1","Q2","Q3","Q4","Q5"],duplicates="drop")
    qrows=[]
    for q,y in x.dropna(subset=["density_change_quintile"]).groupby("density_change_quintile",observed=True):
        for metric in ["mmol/g","v/v"]:
            vals=pd.to_numeric(y[f"delta__{metric}"],errors="coerce").dropna()
            qrows.append({"density_change_quintile":str(q),"metric":metric,"pairs":len(vals),
                          "median_delta":float(vals.median()),
                          "positive_effect_fraction":float((vals>0).mean()),
                          "median_symmetric_density_change":float(y["symmetric_relative_density_effect"].median())})
    qdf=pd.DataFrame(qrows); qdf.to_csv(out/"density_quintile_summary.csv",index=False)

    corr_rows=[]
    for metric in ["mmol/g","v/v"]:
        a=x["symmetric_relative_density_effect"]
        b=pd.to_numeric(x[f"delta__{metric}"],errors="coerce")
        m=a.notna() & b.notna()
        rho,p=spearmanr(a[m],b[m])
        corr_rows.append({"metric":metric,"pairs":int(m.sum()),"spearman_rho":float(rho),"p_value":float(p)})
    pd.DataFrame(corr_rows).to_csv(out/"density_effect_correlations.csv",index=False)

    # Optional process working capacity.
    if process_path:
        proc=pd.read_parquet(process_path)
        if {"process","metric","delta"}.issubset(proc.columns):
            p=proc[proc["process"].astype(str).str.contains("methane",case=False,na=False) &
                   proc["metric"].astype(str).isin(["mmol/g_working_capacity","v/v_working_capacity"])].copy()
            if not p.empty:
                ps=(p.groupby("metric").agg(pairs=("delta","size"),
                    median_delta=("delta","median"),
                    positive_effect_fraction=("delta",lambda s:float((s>0).mean()))).reset_index())
                ps.to_csv(out/"methane_working_capacity_basis_summary.csv",index=False)

    if apply_style is not None:
        apply_style(7.0)
        fig=plt.figure(figsize=(7.15,5.6)); gs=fig.add_gridspec(2,2,wspace=0.38,hspace=0.42)

        axA=fig.add_subplot(gs[0,0])
        rel_rows=[]
        for metric in ["mmol/g","v/v","wt%"]:
            lo=f"value_geometry_low__{metric}"; hi=f"value_geometry_high__{metric}"
            if lo in x and hi in x:
                rr=sym(pd.to_numeric(x[hi],errors="coerce").to_numpy(float),
                       pd.to_numeric(x[lo],errors="coerce").to_numpy(float))
                rel_rows.append((metric,100*float(np.nanmedian(rr))))
        labels=[z[0] for z in rel_rows]; values=[z[1] for z in rel_rows]
        bx=np.arange(len(values))
        axA.bar(bx,values,color=[PALETTE["primary"],PALETTE["validated"],PALETTE["accent"]][:len(values)])
        axA.axhline(0,color=PALETTE["black"],lw=.7)
        axA.set_xticks(bx,labels)
        axA.set_ylabel("Median symmetric relative effect (%)")
        clean_axis(axA); panel_label(axA,"A")

        axB=fig.add_subplot(gs[0,1])
        axB.scatter(x["delta__mmol/g"],x["delta__v/v"],s=5,alpha=.18,color=PALETTE["blue"],edgecolors="none",rasterized=True)
        axB.axhline(0,color=PALETTE["ink"],lw=.6); axB.axvline(0,color=PALETTE["ink"],lw=.6)
        axB.set_xlabel("Δ CH$_4$ (mmol g$^{-1}$)")
        axB.set_ylabel("Δ CH$_4$ (v/v)")
        clean_axis(axB); panel_label(axB,"B")

        axC=fig.add_subplot(gs[1,0])
        vv=qdf[qdf["metric"]=="v/v"]
        axC.bar(vv["density_change_quintile"],vv["median_delta"],color=PALETTE["violet"])
        axC.axhline(0,color=PALETTE["ink"],lw=.7)
        axC.set_xlabel("Density-change quintile")
        axC.set_ylabel("Median Δ CH$_4$ (v/v)")
        clean_axis(axC); panel_label(axC,"C")

        axD=fig.add_subplot(gs[1,1])
        order=["ASA/AVA","Other"]; offsets={"mmol/g":-0.16,"v/v":0.16}
        for metric,c in [("mmol/g",PALETTE["navy"]),("v/v",PALETTE["teal"])]:
            sub=dg[dg["metric"]==metric].set_index("descriptor_group").reindex(order)
            axD.scatter(np.arange(2)+offsets[metric],sub["positive_effect_fraction"],s=36,color=c,label=metric)
        axD.axhline(.5,color=PALETTE["midgray"],lw=.7,ls="--")
        axD.set_xticks(range(2),order)
        axD.set_ylim(0,1)
        axD.set_ylabel("Positive-pair fraction")
        axD.legend()
        clean_axis(axD); panel_label(axD,"D")

        export_figure(fig,out/"Figure_S5_basis_density_robustness"); plt.close(fig)

    manifest={"script":"16_uptake_basis_density_robustness.py","completed_at_utc":utc_now(),
              "post_freeze":True,"pair_membership_modified":False,"primary_endpoint_modified":False,
              "pairs":len(x),"adsorption_source":str(ads_path),"density_source":str(geom_path),
              "max_abs_primary_effect_mismatch":max_abs_primary_mismatch}
    (out/"run_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print("PASS: H3 outputs ->",out)
    print(summary.to_string(index=False))

if __name__=="__main__":
    main()
