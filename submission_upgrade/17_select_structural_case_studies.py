#!/usr/bin/env python3
"""Deterministic Project 17 structure-case selector.

Selects six representative MATCHED PAIRS (12 CIFs), not six isolated structures.
Selection is performed within predeclared scientific strata and uses robust
distance to the stratum median, not maximum adsorption effect or visual beauty.

The script does not modify the frozen catalogue.
"""

from __future__ import annotations
import argparse, hashlib, json, re, tarfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import numpy as np
import pandas as pd

SUFFIX_PATTERN=re.compile(r"(?i)(?:\.cif|_repeat|_sqe)$")
DESCRIPTORS=["ASA","AVA","AVAf","POAVA","POAVAf","Di","Df","Dif"]

def utc_now(): return datetime.now(timezone.utc).isoformat()
def sha256_file(path,chunk=1024*1024):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        while True:
            b=f.read(chunk)
            if not b: break
            h.update(b)
    return h.hexdigest()

def first_existing(root, rels, required=True):
    for r in rels:
        p=root/r
        if p.is_file(): return p
    if required: raise FileNotFoundError("Missing any of:\n"+"\n".join(str(root/r) for r in rels))
    return None

def canonicalize_member(name):
    base=PurePosixPath(str(name).replace("\\","/")).name.strip()
    result=base
    for _ in range(4):
        new=SUFFIX_PATTERN.sub("",result)
        if new==result: break
        result=new
    return result.strip() or None

def robust_distance(frame, features):
    z=[]
    for c in features:
        v=pd.to_numeric(frame[c],errors="coerce")
        med=float(v.median())
        mad=float((v-med).abs().median())
        scale=mad if mad>1e-12 else float(v.std(ddof=0) or 1.0)
        z.append(((v-med)/scale).fillna(0).to_numpy())
    arr=np.column_stack(z)
    return np.sqrt((arr**2).sum(axis=1))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,required=True)
    ap.add_argument("--output-dir",type=Path,required=True)
    ap.add_argument("--archive",type=Path,default=None)
    ap.add_argument("--extract-cifs",action="store_true")
    ap.add_argument("--top-k",type=int,default=15)
    args=ap.parse_args()
    root=args.project_root.resolve(); out=args.output_dir.resolve(); out.mkdir(parents=True,exist_ok=True)

    pair_path=first_existing(root,[Path("results/step2/03_geometry_pairs/primary_geometry_pairs.parquet"),
                                   Path("Step 2 results/03_geometry_pairs/primary_geometry_pairs.parquet")])
    diff_path=first_existing(root,[Path("results/step2/03_geometry_pairs/primary_pair_descriptor_differences.parquet"),
                                   Path("Step 2 results/03_geometry_pairs/primary_pair_descriptor_differences.parquet")])
    effect_path=first_existing(root,[Path("results/step3/04_primary_ch4_analysis/primary_ch4_pair_effects.parquet"),
                                     Path("Step 3 results/04_primary_ch4_analysis/primary_ch4_pair_effects.parquet")])
    arch_path=first_existing(root,[Path("results/step3/07_response_archetypes/response_archetypes.parquet"),
                                   Path("Step 3 results/07_response_archetypes/response_archetypes.parquet")])
    prov_path=first_existing(root,[Path("results/step3/09_database_provenance_robustness/01_pair_provenance.parquet"),
                                   Path("Step 3 results/09_database_provenance_robustness/01_pair_provenance.parquet")])
    geom_path=first_existing(root,[Path("results/step2/01_geometry_variation/geometry_variation_frameworks.parquet"),
                                   Path("Step 2 results/01_geometry_variation/geometry_variation_frameworks.parquet")],required=False)

    pairs=pd.read_parquet(pair_path); diffs=pd.read_parquet(diff_path)
    effects=pd.read_parquet(effect_path); arche=pd.read_parquet(arch_path); prov=pd.read_parquet(prov_path)

    base_cols=["architecture_group_id","driver_low_mof_id","driver_high_mof_id","driver_descriptor",
               "topology","dimensionality","pair_max_fractional_difference",
               "sensitivity_20pct_pair","sensitivity_30pct_pair"]
    base=effects[[c for c in base_cols if c in effects.columns]].copy()
    base=base.merge(arche[[c for c in ["architecture_group_id","archetype","activation_score",
                                      "primary_delta_q_mmol_g","primary_positive"] if c in arche.columns]],
                    on="architecture_group_id",how="left",validate="one_to_one")
    base=base.merge(prov[[c for c in ["architecture_group_id","source_low","source_high",
                                     "provenance_class","same_source_pair"] if c in prov.columns]],
                    on="architecture_group_id",how="left",validate="one_to_one")

    rr=[]
    for gid,g in diffs.groupby("architecture_group_id"):
        g=g.sort_values(["fractional_difference","descriptor"],ascending=[False,True]).reset_index(drop=True)
        if len(g)<2: continue
        a=float(g.loc[0,"fractional_difference"]); b=float(g.loc[1,"fractional_difference"])
        rr.append({"architecture_group_id":gid,"top1_descriptor":str(g.loc[0,"descriptor"]),
                   "top2_descriptor":str(g.loc[1,"descriptor"]),
                   "top1_difference":a,"top2_difference":b,
                   "top1_top2_ratio":np.inf if b==0 and a>0 else (1 if a==b==0 else a/b)})
    base=base.merge(pd.DataFrame(rr),on="architecture_group_id",how="left",validate="one_to_one")
    if "primary_delta_q_mmol_g" not in base:
        base=base.merge(effects[["architecture_group_id","delta_q_mmol_g"]],on="architecture_group_id",how="left")
        base=base.rename(columns={"delta_q_mmol_g":"primary_delta_q_mmol_g"})

    specs=[
        ("A","pressure_activated_ASA",
         (base["archetype"]=="pressure_activated")&(base["driver_descriptor"]=="ASA")&base["sensitivity_20pct_pair"].astype("boolean").fillna(False)),
        ("B","pressure_activated_AVA",
         (base["archetype"]=="pressure_activated")&(base["driver_descriptor"]=="AVA")&base["sensitivity_20pct_pair"].astype("boolean").fillna(False)),
        ("C","positive_both_accessible_space",
         (base["archetype"]=="positive_both")&base["driver_descriptor"].isin(["ASA","AVA"])&base["sensitivity_20pct_pair"].astype("boolean").fillna(False)),
        ("D","negative_both_diameter",
         (base["archetype"]=="negative_both")&base["driver_descriptor"].isin(["Di","Df","Dif"])),
        ("E","pressure_suppressed",
         (base["archetype"]=="pressure_suppressed")),
        ("F","experimental_source_pair",
         (base["provenance_class"]=="experimental_experimental")),
    ]

    ranked_blocks=[]; selected=[]; used_groups=set()
    features=["pair_max_fractional_difference","primary_delta_q_mmol_g","activation_score"]
    for panel,name,mask in specs:
        c=base.loc[mask].copy()
        if c.empty:
            raise RuntimeError(f"Panel {panel} stratum {name} has no candidates")
        c["representativeness_distance"]=robust_distance(c,features)
        c=c.sort_values(["representativeness_distance","architecture_group_id"]).reset_index(drop=True)
        c["panel"]=panel; c["case_definition"]=name; c["rank_in_stratum"]=np.arange(1,len(c)+1)
        ranked_blocks.append(c.head(args.top_k))

        available=c[~c["architecture_group_id"].isin(used_groups)]
        if available.empty:
            raise RuntimeError(f"Panel {panel} stratum {name} has no unused candidate")
        chosen=available.iloc[0]
        pick=chosen.to_dict()
        used_groups.add(chosen["architecture_group_id"])
        pick["selection_status"]=(
            "selected_rank1_pending_visual_qc" if int(chosen["rank_in_stratum"])==1
            else f"selected_rank{int(chosen['rank_in_stratum'])}_after_cross_panel_dedup_pending_visual_qc"
        )
        pick["rejection_reason"]=""
        selected.append(pick)

    ranked=pd.concat(ranked_blocks,ignore_index=True)
    ledger=pd.DataFrame(selected)
    ranked.to_csv(out/"case_study_candidates_ranked.csv",index=False)
    ledger.to_csv(out/"case_study_selection_ledger.csv",index=False)

    if geom_path:
        geom=pd.read_parquet(geom_path)
        idcol="mof_id"
        cols=[c for c in ["mof_id","Density","ASA","AVA","AVAf","POAVA","POAVAf","Di","Df","Dif"] if c in geom.columns]
        gm=geom[cols].drop_duplicates(idcol).set_index(idcol)
        fr=[]
        for _,r in ledger.iterrows():
            for side,idc in [("low","driver_low_mof_id"),("high","driver_high_mof_id")]:
                mid=str(r[idc]); rec={"panel":r["panel"],"side":side,"mof_id":mid}
                if mid in gm.index:
                    for c in gm.columns: rec[c]=gm.loc[mid,c]
                fr.append(rec)
        pd.DataFrame(fr).to_csv(out/"case_study_framework_metrics.csv",index=False)

    extraction=[]
    if args.extract_cifs:
        archive=args.archive.resolve() if args.archive else (root/"raw"/"ARCMOF_20241004.tar.gz")
        if not archive.is_file(): raise FileNotFoundError(archive)
        wanted={}
        for _,r in ledger.iterrows():
            wanted[str(r["driver_low_mof_id"])]=(str(r["panel"]),"low")
            wanted[str(r["driver_high_mof_id"])]=(str(r["panel"]),"high")
        cifdir=out/"cifs"; cifdir.mkdir(exist_ok=True)
        found=set()
        with tarfile.open(archive,"r:gz") as tf:
            for m in tf:
                if not m.isfile() or not m.name.lower().endswith(".cif"): continue
                cid=canonicalize_member(m.name)
                if cid not in wanted: continue
                fh=tf.extractfile(m)
                raw=fh.read()
                panel,side=wanted[cid]
                safe=re.sub(r"[^A-Za-z0-9_.-]+","_",cid)
                dest=cifdir/f"{panel}_{side}_{safe}.cif"
                dest.write_bytes(raw)
                found.add(cid)
                extraction.append({"panel":panel,"side":side,"mof_id":cid,"archive_member":m.name,
                                   "output_file":dest.name,"sha256":hashlib.sha256(raw).hexdigest(),
                                   "size_bytes":len(raw)})
                if len(found)==len(wanted): break
        missing=sorted(set(wanted)-found)
        if missing: raise RuntimeError("Could not find CIFs for: "+", ".join(missing))
        pd.DataFrame(extraction).to_csv(out/"cif_extraction_manifest.csv",index=False)

    manifest={"script":"17_select_structural_case_studies.py","completed_at_utc":utc_now(),
              "post_freeze":True,"pair_membership_modified":False,
              "selection_method":"predeclared strata + robust median/MAD representativeness distance",
              "panels":{p:n for p,n,_ in specs},"selected_pairs":len(ledger),
              "selected_pairs_unique":bool(ledger["architecture_group_id"].is_unique),
              "cifs_requested":12 if args.extract_cifs else 0}
    (out/"run_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print("PASS: structural selection outputs ->",out)
    print(ledger[["panel","case_definition","architecture_group_id","driver_low_mof_id",
                  "driver_high_mof_id","driver_descriptor","archetype",
                  "primary_delta_q_mmol_g","representativeness_distance"]].to_string(index=False))

if __name__=="__main__":
    main()
