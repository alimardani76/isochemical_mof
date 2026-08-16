# Project 17 submission-upgrade work

This folder contains post-freeze checks requested during coauthor handover. They are secondary robustness/visualization tasks only and must not redefine the frozen 11,072 pairs, pair orientation, 10% geometry threshold, confirmatory CH4 endpoint, or family-level estimator.

## Completed checks

- **H2 geometry-attribution stability** — tests how the primary result changes when the largest geometry difference increasingly dominates the second-largest one.
- **H3 uptake-basis/density robustness** — verifies the frozen mmol/g result and evaluates v/v, wt%, and density-related behavior.
- **H4 structural case selection** — deterministically selects six mutually exclusive frozen pairs, extracts the 12 CIFs, and provides the reproducible Figure 5 structural-rendering workflow.
- **H6 source-stratified effects** — summarizes same-source primary effects together with geometry magnitude and ASA/AVA composition.

## H4 structural Figure 5 workflow

The H4 selector is `17_select_structural_case_studies.py`. It uses predeclared scientific strata and robust median/MAD representativeness distance; it does **not** select examples by visual attractiveness or maximum adsorption response.

The final rendering source is `../figures/source/12_make_figure5_structural_assets.py`. It converts the 12 frozen CIFs into four final structural assets per panel (LOW/HIGH whole views and matched LOW/HIGH insets) using locked camera directions, matched orthographic scale, periodic buffering, and symmetric cropping.

Full details, including the frozen panel strata, representativeness score, locked views, inset locations, bond-visualization settings, and scientific guardrails, are recorded in `H4_STRUCTURAL_FIGURE_METHOD.md`.

## Interpretation change

The post-freeze work does not replace the original headline result. It tightens the interpretation:

1. `driver_descriptor` is the descriptor with the largest observed pairwise geometry contrast, not proof of an isolated causal perturbation.
2. The positive 65-bar CH4 median survives volumetric normalization.
3. Same-source effect magnitudes are strongly heterogeneous because source populations sample different geometry regimes.
4. The six structural examples intentionally include positive and negative/failure-boundary cases.
5. Figure 5 insets are representative structural context only; they are not adsorption-site assignments.

See `RESULTS_SUMMARY.md`, `LOCAL_ARTIFACTS_TO_ADD.md`, `H4_STRUCTURAL_FIGURE_METHOD.md`, and the root `HANDOVER.md`.
