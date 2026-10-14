# H7 local coordination analysis — code and frozen outputs

The analysis is a post-freeze extension of Project 17. The core analysis script `20_local_coordination_context.py` and all saved **scientific output CSV/parquet/JSON files** here are identical to the coauthor's 2026-09-09 handover. Only the figure presentation, integration notes, and checksum manifest have been updated for the 2026-10-14 release.

The `results/` folder contains 22,137 successful CIF fingerprints from 22,144 requested frameworks and 11,065 complete matched pairs (out of 11,072 frozen pairs). The model comparison is based on identical complete pairs: geometry/local/combined mean Spearman = 0.8639/0.6543/0.8666 in random 5-fold CV and 0.7490/0.3257/0.7372 in topology-grouped CV.

## Regenerate Figure 6 (quick, no CIF archive)

From the H7 directory:

```bash
python -m pip install numpy pandas matplotlib
python figure/make_figure6.py
```

## Recompute analysis from original CIFs (optional)

The original frozen Project 17 input parquet files and ARC-MOF v7 raw archive are **required but not bundled**. See the root `H7/README.md` for required source paths, commands and scientific limits. The `requirements.txt` uses lower version bounds and is **not a precise lock of the completed scientific run**.

`results/run_manifest.json` preserves input SHA-256 hashes and H7 training settings. `results/SHA256SUMS.txt` records the files in this **updated public release**; `../audit/ORIGINAL_HANDOVER_SHA256SUMS.txt` preserves the September handover manifest for comparison. No frozen matching or outcome recomputation was performed to create the redesigned figure.
