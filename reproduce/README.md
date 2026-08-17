# Reproducing the frozen analysis

Several historical scripts preserve paths from the original analysis workspace. Do not execute relocated historical scripts blindly from the repository tree.

1. Use the recorded dependencies under `environment/`.
2. Run `python reproduce/build_legacy_workspace.py` from repository root.
3. Restore the exact ARC–MOF release-v7 inputs listed in `data_manifest/RAW_DATA_REQUIRED.md` and verify the recorded inventory/hashes.
4. Run staged scripts in order (`scripts/step1/`, `scripts/step2/`, `scripts/step3/`) and require the corresponding audits under `scripts/audits/` to pass.
5. Run post-freeze H2/H3/H4/H6 scripts from `submission_upgrade/`; canonical outputs belong under `results/submission_upgrade/`.
6. Generate current quantitative publication figures with `figures/redesign/validate_redesign_values.py` followed by `figures/redesign/run_all.py`. Structural Figure 5 follows `submission_upgrade/H4_STRUCTURAL_FIGURE_METHOD.md`.

Do not substitute a newer ARC–MOF release or change the chemistry key, architecture key, pair rule, thresholds, orientation, endpoint, estimator, or bootstrap without treating it as a new analysis.
