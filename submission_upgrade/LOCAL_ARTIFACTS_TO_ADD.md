# Canonical local artifacts to add before merge

The GitHub connector cannot read files generated only on the local Windows Project17 tree. Copy these outputs verbatim before merging `submission-upgrade`; do not reconstruct them from Markdown summaries.

## H2
`Project17/submission_upgrade/15_geometry_attribution_stability/`

Expected outputs include `geometry_attribution_pair_level.parquet`, `driver_margin_summary.csv`, `clean_dominant_primary_summary.csv`, `descriptor_threshold_multiplicity.csv`, `descriptor_difference_correlation.csv`, `Figure_S4_geometry_attribution_stability.{pdf,svg,png}`, and `run_manifest.json`.

## H3
`Project17/submission_upgrade/16_uptake_basis_density_robustness/`

Expected outputs include `basis_primary_pair_level.parquet`, `basis_primary_summary.csv`, `basis_primary_bootstrap.csv`, `basis_by_geometry_tier.csv`, `basis_by_descriptor_group.csv`, `density_quintile_summary.csv`, `density_effect_correlations.csv`, `Figure_S5_basis_density_robustness.{pdf,svg,png}`, `run_manifest.json`, and `methane_working_capacity_basis_summary.csv` when generated.

## H4
`Project17/submission_upgrade/17_structural_case_studies/`

Expected outputs include `case_study_candidates_ranked.csv`, `case_study_selection_ledger.csv`, `case_study_framework_metrics.csv`, `cif_extraction_manifest.csv`, `cifs/` containing 12 extracted CIFs, and `run_manifest.json`.

## H6
`Project17/submission_upgrade/18_source_stratified_effects/`

Expected outputs include `source_stratified_primary.csv`, `source_stratified_composition.csv`, `Figure_S6_source_stratified.{pdf,svg,png}`, and `run_manifest.json`.

Recommended repository destinations are `results/submission_upgrade/H2_geometry_attribution/`, `H3_uptake_basis_density/`, `H4_structural_cases/`, and `H6_source_stratified/`. If pair-level Parquet files exceed normal GitHub limits, place those files in Git LFS, a GitHub Release, or Zenodo and record their SHA256 plus external location in the data manifest.
