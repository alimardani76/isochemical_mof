#!/usr/bin/env python3
"""Project 17 post-freeze geometry-attribution stability audit.

This script DOES NOT change frozen pair membership, pair orientation, the
geometry threshold, or the primary endpoint. It asks how clearly separated the
largest pairwise geometry contrast is from the second largest contrast.

Outputs are secondary/post-freeze robustness results.
"""

from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

try:
    from p17_style_v2 import apply_style, clean_axis, panel_label, export_figure, PALETTE, SEMANTIC
except ImportError:
    apply_style = clean_axis = panel_label = export_figure = None

DESCRIPTORS = ["ASA","AVA","AVAf","POAVA","POAVAf","Di","Df","Dif"]
RATIOS = [1.00, 1.10, 1.25, 1.50]

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def first_existing(root: Path, rels):
    for rel in rels:
        p = root / rel
        if p.is_file():
            return p
    raise FileNotFoundError("None of these paths exists:\n" + "\n".join(str(root/r) for r in rels))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    root = args.project_root.resolve()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)

    diff_path = first_existing(root, [
        Path("results/step2/03_geometry_pairs/primary_pair_descriptor_differences.parquet"),
        Path("Step 2 results/03_geometry_pairs/primary_pair_descriptor_differences.parquet"),
    ])
    effect_path = first_existing(root, [
        Path("results/step3/04_primary_ch4_analysis/primary_ch4_pair_effects.parquet"),
        Path("Step 3 results/04_primary_ch4_analysis/primary_ch4_pair_effects.parquet"),
    ])

    d = pd.read_parquet(diff_path)
    e = pd.read_parquet(effect_path)

    req_d = {"architecture_group_id","descriptor","fractional_difference","is_driver_descriptor"}
    req_e = {"architecture_group_id","driver_descriptor","delta_q_mmol_g",
             "primary_10pct_pair","sensitivity_20pct_pair","sensitivity_30pct_pair"}
    if missing := req_d - set(d.columns):
        raise ValueError(f"descriptor-difference table missing {sorted(missing)}")
    if missing := req_e - set(e.columns):
        raise ValueError(f"primary-effect table missing {sorted(missing)}")

    d = d[d["descriptor"].astype(str).isin(DESCRIPTORS)].copy()
    d["fractional_difference"] = pd.to_numeric(d["fractional_difference"], errors="raise")

    rows = []
    for gid, g in d.groupby("architecture_group_id", sort=True):
        g = g.copy()
        if len(g) != 8:
            raise RuntimeError(f"{gid}: expected 8 descriptor rows, found {len(g)}")

        driver_rows = g[g["is_driver_descriptor"].astype("boolean").fillna(False)]
        if len(driver_rows) != 1:
            raise RuntimeError(f"{gid}: expected exactly one frozen driver row, found {len(driver_rows)}")

        driver = driver_rows.iloc[0]
        top1_desc = str(driver["descriptor"])
        top1 = float(driver["fractional_difference"])

        others = g[g["descriptor"].astype(str) != top1_desc].copy()
        others = others.sort_values(
            ["fractional_difference", "descriptor"], ascending=[False, True]
        ).reset_index(drop=True)
        top2_desc = str(others.loc[0, "descriptor"])
        top2 = float(others.loc[0, "fractional_difference"])

        # The stored driver must attain the pair maximum.  Equal maxima are allowed;
        # the frozen driver label is retained rather than re-resolved post-freeze.
        numeric_max = float(g["fractional_difference"].max())
        if not np.isclose(top1, numeric_max, rtol=1e-12, atol=1e-12):
            raise RuntimeError(
                f"{gid}: frozen driver difference {top1} is not the pair maximum {numeric_max}"
            )

        ratio = np.inf if top2 == 0 and top1 > 0 else (1.0 if top1 == top2 == 0 else top1/top2)
        rows.append({
            "architecture_group_id": gid,
            "top1_descriptor": top1_desc,
            "top2_descriptor": top2_desc,
            "top1_fractional_difference": top1,
            "top2_fractional_difference": top2,
            "top1_minus_top2": top1-top2,
            "top1_div_top2": ratio,
            "n_ge_10pct": int((g["fractional_difference"] >= 0.10).sum()),
            "n_ge_20pct": int((g["fractional_difference"] >= 0.20).sum()),
            "n_ge_30pct": int((g["fractional_difference"] >= 0.30).sum()),
        })
    pair = pd.DataFrame(rows)
    pair = pair.merge(e, on="architecture_group_id", how="inner", validate="one_to_one")

    if len(pair) != len(e):
        raise RuntimeError(f"join lost pairs: effects={len(e)}, joined={len(pair)}")

    mismatch = pair["top1_descriptor"].astype(str) != pair["driver_descriptor"].astype(str)
    if mismatch.any():
        ex = pair.loc[mismatch, ["architecture_group_id","top1_descriptor","driver_descriptor"]].head()
        raise RuntimeError("Frozen driver label disagrees between descriptor and effect tables.\n" + ex.to_string(index=False))

    if len(pair) != 11072:
        raise RuntimeError(f"expected 11,072 frozen pairs, found {len(pair):,}")

    pair.to_parquet(out/"geometry_attribution_pair_level.parquet", index=False)

    margin_rows = []
    for r in [1.10,1.25,1.50]:
        x = pair[pair["top1_div_top2"] >= r]
        margin_rows.append({
            "criterion": f"top1_div_top2_ge_{r:.2f}",
            "pairs": len(x),
            "fraction_of_frozen_pairs": len(x)/len(pair),
            "median_top1_div_top2": float(x["top1_div_top2"].replace(np.inf,np.nan).median()),
            "median_delta_q_mmol_g": float(x["delta_q_mmol_g"].median()),
            "positive_effect_fraction": float((x["delta_q_mmol_g"]>0).mean()),
        })
    pd.DataFrame(margin_rows).to_csv(out/"driver_margin_summary.csv", index=False)

    clean_rows = []
    for desc in DESCRIPTORS:
        for r in RATIOS:
            x = pair[(pair["top1_descriptor"]==desc) & (pair["top1_div_top2"] >= r)]
            clean_rows.append({
                "descriptor": desc,
                "minimum_top1_top2_ratio": r,
                "pairs": len(x),
                "median_delta_q_mmol_g": float(x["delta_q_mmol_g"].median()) if len(x) else np.nan,
                "mean_delta_q_mmol_g": float(x["delta_q_mmol_g"].mean()) if len(x) else np.nan,
                "positive_effect_fraction": float((x["delta_q_mmol_g"]>0).mean()) if len(x) else np.nan,
                "median_pair_max_fractional_difference": float(x["pair_max_fractional_difference"].median()) if "pair_max_fractional_difference" in x and len(x) else np.nan,
            })
    clean = pd.DataFrame(clean_rows)
    clean.to_csv(out/"clean_dominant_primary_summary.csv", index=False)

    multiplicity = (pair.groupby("n_ge_10pct")
                    .agg(pairs=("architecture_group_id","size"),
                         median_delta_q_mmol_g=("delta_q_mmol_g","median"),
                         positive_effect_fraction=("delta_q_mmol_g", lambda s: float((s>0).mean())))
                    .reset_index())
    multiplicity.to_csv(out/"descriptor_threshold_multiplicity.csv", index=False)

    piv = d.pivot(index="architecture_group_id", columns="descriptor", values="fractional_difference")[DESCRIPTORS]
    corr = piv.corr(method="spearman")
    corr.to_csv(out/"descriptor_difference_correlation.csv")

    # Figure S4
    if apply_style is not None:
        apply_style(7.0)
        fig = plt.figure(figsize=(7.15,5.6))
        gs = fig.add_gridspec(2,2, wspace=0.38, hspace=0.40)
        axA = fig.add_subplot(gs[0,0])
        vals = pair["top1_div_top2"].replace(np.inf,np.nan).dropna().clip(upper=3)
        axA.hist(vals, bins=np.linspace(1,3,35), color=PALETTE["violet"], edgecolor="white", linewidth=0.3)
        for r in [1.10,1.25,1.50]:
            axA.axvline(r, color=PALETTE["ink"], lw=0.7, ls="--")
        axA.set_xlabel("Largest / second-largest geometry contrast")
        axA.set_ylabel("Pairs")
        clean_axis(axA); panel_label(axA,"A")

        axB = fig.add_subplot(gs[0,1])
        im = axB.imshow(corr.values, vmin=-1, vmax=1, cmap="coolwarm")
        axB.set_xticks(range(8), DESCRIPTORS, rotation=45, ha="right")
        axB.set_yticks(range(8), DESCRIPTORS)
        cbar = fig.colorbar(im, ax=axB, fraction=0.046, pad=0.04)
        cbar.set_label("Spearman ρ", fontweight="bold")
        panel_label(axB,"B")

        axC = fig.add_subplot(gs[1,0])
        x = np.arange(len(DESCRIPTORS))
        offsets = [-0.24,-0.08,0.08,0.24]
        cols = [PALETTE["slate"], PALETTE["blue"], PALETTE["amber"], PALETTE["coral"]]
        for off, r, c in zip(offsets,RATIOS,cols):
            sub = clean[clean["minimum_top1_top2_ratio"]==r].set_index("descriptor").reindex(DESCRIPTORS)
            axC.scatter(x+off, sub["median_delta_q_mmol_g"], s=22, color=c, label=f"ratio ≥ {r:.2f}")
        axC.axhline(0,color=PALETTE["ink"],lw=0.7)
        axC.set_xticks(x, DESCRIPTORS, rotation=45, ha="right")
        axC.set_ylabel("Median Δq (mmol g$^{-1}$)")
        axC.legend(ncol=2, loc="best")
        clean_axis(axC); panel_label(axC,"C")

        axD = fig.add_subplot(gs[1,1])
        axD.bar(multiplicity["n_ge_10pct"], multiplicity["median_delta_q_mmol_g"],
                color=PALETTE["teal"], width=0.72)
        axD.axhline(0,color=PALETTE["ink"],lw=0.7)
        axD.set_xlabel("Descriptors changing by ≥10% within pair")
        axD.set_ylabel("Median Δq (mmol g$^{-1}$)")
        clean_axis(axD); panel_label(axD,"D")
        export_figure(fig, out/"Figure_S4_geometry_attribution_stability")
        plt.close(fig)

    manifest = {
        "script":"15_geometry_attribution_stability.py",
        "completed_at_utc":utc_now(),
        "post_freeze":True,
        "pair_membership_modified":False,
        "pair_orientation_modified":False,
        "geometry_threshold_modified":False,
        "primary_endpoint_modified":False,
        "pairs":len(pair),
        "input_descriptor_differences":str(diff_path),
        "input_primary_effects":str(effect_path),
    }
    (out/"run_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(f"PASS: wrote H2 outputs to {out}")
    print(pd.DataFrame(margin_rows).to_string(index=False))

if __name__ == "__main__":
    main()
