# Project 17 submission-upgrade branch

This folder contains post-freeze checks requested during coauthor handover. They are secondary robustness/visualization tasks only and must not redefine the frozen 11,072 pairs, pair orientation, 10% geometry threshold, confirmatory CH4 endpoint, or family-level estimator.

## Completed checks

- H2 geometry-attribution stability: tests how the primary result changes when the largest geometry difference increasingly dominates the second-largest one.
- H3 uptake-basis/density robustness: verifies the frozen mmol/g result and evaluates v/v, wt%, and density-related behavior.
- H4 structural case selection: deterministically selects six mutually exclusive frozen pairs and extracts the 12 CIFs when `--extract-cifs` is used.
- H6 source-stratified effects: summarizes same-source primary effects together with geometry magnitude and ASA/AVA composition.

## Interpretation change

The post-freeze work does not replace the original headline result. It tightens the interpretation:

1. `driver_descriptor` is the descriptor with the largest observed pairwise geometry contrast, not proof of an isolated causal perturbation.
2. The positive 65-bar CH4 median survives volumetric normalization.
3. Same-source effect magnitudes are strongly heterogeneous because source populations sample different geometry regimes.
4. The six structural examples intentionally include positive and negative/failure-boundary cases.

See `RESULTS_SUMMARY.md`, `LOCAL_ARTIFACTS_TO_ADD.md`, and the root `HANDOVER.md`.
