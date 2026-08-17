# Post-freeze robustness and structural-analysis modules

The historical directory name `submission_upgrade/` is retained because it appears in manifests, scripts, and prior commits. In the publication repository this folder contains **bounded post-freeze analyses** and the Figure 5 structural workflow.

None of these scripts changes the frozen primary pair catalogue, orientation, 10% geometry criterion, primary endpoint, or primary estimator.

## Scripts

- `15_geometry_attribution_stability.py` — H2, clean-dominance/descriptor-covariance analysis
- `16_uptake_basis_density_robustness.py` — H3, uptake-basis and density coupling
- `17_select_structural_case_studies.py` — H4, deterministic six-pair selection
- `18_source_stratified_effects.py` — H6, same-source applicability analysis
- `19_submission_sanity_check.py` — repository/result sanity checks
- `p17_style_v2.py` — plotting style used by the original post-freeze scripts
- `H4_STRUCTURAL_FIGURE_METHOD.md` — structural rendering/provenance contract

Canonical outputs live under `results/submission_upgrade/`. Earlier duplicate output mirrors beside these scripts have been removed from the publication branch.

H2/H3/H6 are secondary/post-freeze. H4 is a deterministic visualization selection, not a new estimand. Their role is to bound and interpret the frozen primary result, not to retroactively optimize the analysis.
