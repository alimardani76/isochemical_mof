# Paper 17 · H7 post-freeze local coordination analysis

**Release refreshed 2026-10-14 from `H7_HANDOVER.zip` (2026-09-09), integrating the latest reviewed Figure 6 v3.** Original analysis script and original tabulated scientific results are retained unchanged. Only the figure generator, generated figure exports, caption and documentation were updated. No model was refitted.

## Scientific question and conclusion

Does a lightweight CrystalNN-based local atomic fingerprint explain additional variation in the existing matched-pair CH4 response (298 K, 65 bar), beyond the eight global pore-geometry descriptors and density? Matching, 10% threshold, geometry-low/high orientation and primary endpoint were frozen in advance. Seven of the 22,144 unique structures failed local fingerprinting; all three representations use the same 11,065 complete pairs.

Mean five-fold **Spearman correlation** (pores+density / local / combined):

- Random cross-validation: **0.8639 / 0.6543 / 0.8666**.
- GroupKFold with topology held out: **0.7490 / 0.3257 / 0.7372**.

Thus the small gain under random CV does **not** generalize to held-out topologies. The local metal-count feature depends on CIF/unit-cell representation; some motif features have severe coverage limitations. The SHAP ranking is not evidence of mechanism. This is an exploratory, post-freeze model comparison, not a revision of the main primary analysis.

## Contents

- `code/20_local_coordination_context.py` — source code for full H7 analysis; scientific code unchanged from the delivered handover.
- `code/results/` — frozen H7 output tables, fingerprints, out-of-fold predictions, SHAP summaries, QC, run manifest, and checksums.
- `figure/make_figure6.py` — revised publication-figure generator; uses only `code/results/*.csv`.
- `figure/p17_style_v2.py` — unchanged Project 17 graphic style.
- `figure/Figure_6.pdf`, `.svg`, `.png` — regenerated, data-driven Figure 6.
- `tex/H7_addition.tex`, `tex/H7_caption.tex` — handover results and methods insert, and an updated caption. These are **not yet merged into the later October Overleaf manuscript**.
- `audit/` — preservation of the original H7 handover checksum list.

## Regenerate the exact figure (no CIFs or model fitting)

From the **H7 folder**:

```bash
python -m pip install numpy pandas matplotlib
python figure/make_figure6.py
```

This writes PDF/SVG/PNG into `figure/`. No random samples are generated in the figure. Panel A alone is explicitly a conceptual illustration, not a rendering of specific CIF structures. Panels B–D are plotted from original H7 result CSVs. The file `code/results/cv_predictions.csv` allows independent recomputation of held-out Spearman/MAE/R² across all 30 model-fold records.

## Re-run local fingerprints and LightGBM (optional, more involved)

The *unmodified H7 analysis code* expects **three original, frozen Project 17 parquet input tables** in its documented expected paths under your repository root, and the original ARC-MOF CIF archive, for example `raw/ARCMOF_20241004.tar.gz`, from the ARC-MOF v7 Zenodo data release (record 16802743). The CIF archive **is not included here**. The three frozen input parquet tables are not duplicated inside H7; they **are already present at the expected paths in the supplied `isochemical_mof-main.zip` repository snapshot**, with SHA-256 hashes that exactly match H7 `run_manifest.json`. The requirements file is a compatible version range, not an exact environment lock. The current handover permits figure-level reproduction independently, but it is **not a fully standalone end-to-end retraining archive**.

```bash
python -m pip install -r submission_upgrade/H7/code/requirements.txt
python submission_upgrade/H7/code/20_local_coordination_context.py \
  --project-root . --archive raw/ARCMOF_20241004.tar.gz --workers 6
python submission_upgrade/H7/figure/make_figure6.py
```

The analysis has input SHA-256 values recorded in `code/results/run_manifest.json`. Verify them against the frozen Project 17 source files before any rerun; do not silently rematch, reorient, replace failed fingerprints, or tune against the observed results.

## Manuscript integration is deliberately deferred

The old handover included a complete September `main.tex`, which must **not** overwrite the newer October 14 Overleaf `main.tex`. Therefore this release includes only the short H7 results/methods insert and caption as reference. The later Overleaf merge should be made against the actual latest `main.tex` and `SI.tex`, followed by compilation and cross-reference validation. In the Overleaf `figures/` folder, the intended file is `Figure_6.pdf`.

## GitHub location / branch caveat

Intended browser-upload path: `submission_upgrade/H7/` **on branch `submission-upgrade`**, as instructed in Hosein's handover. The supplied 2026-10-14 repository snapshot `isochemical_mof-main.zip` has been inspected: 296 files (264.3 MB uncompressed), `submission_upgrade/` exists, H7 is absent, and all three frozen H7 source-table SHA-256 hashes match. The ZIP is explicitly labeled `main`; it cannot establish the current contents or even existence of the different `submission-upgrade` branch. Before uploading, verify the **actual target branch** in the signed-in GitHub browser. **Do not upload a ZIP file as an opaque ZIP** if your goal is browser-browsable code and results; extract it and upload the files preserving their paths. Do not overwrite unrelated files or add old execution packages.

All original result CSV/parquet files and original analysis script were preserved unchanged in this package; see `code/results/SHA256SUMS.txt` for release checksums and `audit/ORIGINAL_HANDOVER_SHA256SUMS.txt` for the original handover hashes.

## Verified repository compatibility (2026-10-14)

The archive `isochemical_mof-main.zip` passed its ZIP integrity check. The H7 run manifest matches byte-for-byte the three frozen input parquet files under the repository's `results/step2/` and `results/step3/` trees. See `audit/REPOSITORY_SNAPSHOT_VERIFICATION.md` for exact paths, hashes and upload caveats. Full CIF reconstruction and model training were **not** rerun during this repository check.

The manuscript currently describes the repository as publicly available. If it remains private at journal submission, update the availability statement to reflect the actual authorized archival/access method, or arrange a properly authorized public release. Do not make it public without agreement of the repository owner/coauthors.

## Rechecked release notes (2026-10-14)

- Figure 6 labels explicitly identify the 8-pore-descriptor-plus-density baseline; **the scientific code and numerical results have not been altered**.
- The input-byte identity against the user-supplied `isochemical_mof-main.zip` has been verified for the three frozen input Parquet files. See `audit/REPOSITORY_SNAPSHOT_VERIFICATION.md`.
- `audit/QC_REPORT_20261014.json` contains a machine-readable report of the source-cohort and saved model-output checks.
- No live branch, commit, publication release or public accessibility was verified. The submitted ZIP is a **candidate for manual review/upload**, not a GitHub push or journal-ready source bundle.


## GitHub browser upload of this ZIP

The ZIP contains one top-level directory, `H7/`. Extract it on your computer,
open the intended branch of `alimardani76/isochemical_mof` (Hosein originally
specified `submission-upgrade`), navigate into its existing `submission_upgrade/`
directory, and drag the local **H7 folder** onto **Add file → Upload files**.
The resulting paths must begin `submission_upgrade/H7/`, never
`submission_upgrade/submission_upgrade/H7/` or `submission_upgrade/H7/H7/`.
If H7 already exists in the live branch, stop and compare before overwriting.
The user's October Overleaf manuscript is NOT in this package.

Figure version: latest `P17_FIGURE6_REFINED_STAGE1_20261014_v3.zip`
(visual adjustments only; no re-fit). This is the latest working design,
not a declaration of manuscript/figure approval by all coauthors.
