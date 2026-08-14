# Project 17 — Coauthor Handover

## Scientific status

The frozen Project 17 analysis is complete. The core design is outcome-blind: recorded chemistry and broad architecture are fixed before geometry contrasts and adsorption outcomes are examined. The frozen primary cohort contains 11,072 pairs (22,144 unique frameworks); the confirmatory endpoint is CH4 uptake at 298 K and 65 bar in mmol/g, with a family-level median estimand and 10,000-replicate bootstrap (seed 17).

Frozen definitions must not be silently changed: chemistry key, topology/dimensionality architecture refinement, 10% geometry threshold, deterministic one-pair-per-family catalogue, pair orientation, primary endpoint, primary estimator, and bootstrap seed.

## Core confirmatory result

- 11,072 frozen pairs
- median delta_q = +0.583554 mmol/g
- 95% family-bootstrap CI = [0.554565, 0.614922] mmol/g
- 70.50% positive
- >=20% geometry tier: median +1.698016 mmol/g, 78.27% positive
- >=30% geometry tier: median +3.164466 mmol/g, 85.22% positive

The primary response is not universal across geometry classes. ASA/AVA-labelled pairs are strongly enriched in favorable responses, while diameter-labelled pairs have slightly negative median responses. Pressure and process objective substantially change the response.

## Important interpretation boundary

The matched families control recorded composition, ARC-MOF chemistry-cluster assignments, topology, and dimensionality. They do not prove atom-by-atom identity and do not constitute causal mechanical deformations. The pair driver is the descriptor with the largest observed geometry contrast, not a proof that the descriptor changed in isolation.

The cohort is overwhelmingly hypothetical: 99.2% of frozen pairs are hypothetical–hypothetical. Experimental transferability is therefore weakly sampled.

## Submission-upgrade / coauthor sprint

The `submission-upgrade` branch adds bounded post-freeze checks. None changes pair membership, orientation, the 10% threshold, the confirmatory endpoint, or the estimand.

### H2 — geometry-attribution stability

The eight pore-descriptor differences were re-ranked inside each already-frozen pair. The ratio between the largest and second-largest geometry differences was used only to form robustness subsets:

| top1/top2 criterion | pairs | median delta_q (mmol/g) | positive fraction |
|---|---:|---:|---:|
| >=1.10 | 4,603 | +0.413537 | 0.662611 |
| >=1.25 | 2,866 | +0.187258 | 0.601535 |
| >=1.50 | 1,715 | +0.038287 | 0.531195 |

Interpretation: increasing isolation of the nominal driver attenuates the pooled signal. The stored `driver_descriptor` should therefore be described as the largest observed geometry-contrast label within correlated pore changes, not as an isolated causal perturbation.

### H3 — uptake-basis / density robustness

| metric | pairs | median delta | positive fraction | bootstrap 95% CI |
|---|---:|---:|---:|---:|
| mmol/g | 11,072 | +0.583554 | 0.705022 | [0.554565, 0.614922] |
| v/v | 11,072 | +3.797193 | 0.608833 | [3.438461, 4.185063] |
| wt% | 11,072 | +0.933689 | 0.705022 | [0.887304, 0.983874] |

The volumetric comparison is the meaningful basis robustness check. Density reduces pair-level sign consistency but does not reverse the positive population-level high-pressure CH4 result. wt% should not be oversold as an independent robustness test because it is closely related to the mass-basis molar uptake for fixed CH4.

### H4 — deterministic structural cases

Six mutually exclusive frozen pairs were selected for visualization, and the 12 corresponding CIFs were extracted locally with checksums:

| panel | case | driver | archetype | primary delta_q (mmol/g) |
|---|---|---|---|---:|
| A | pressure-activated ASA | ASA | pressure activated | +9.096988 |
| B | pressure-activated AVA | AVA | pressure activated | +2.994237 |
| C | positive-both accessible space | ASA | positive both | +2.667362 |
| D | negative-both diameter | Df | negative both | -0.459752 |
| E | pressure suppressed | Di | pressure suppressed | -0.187601 |
| F | experimental-source pair | AVA | positive both | +0.082596 |

These are visualization aids, not a new estimand or a cherry-picked positive-only set.

### H6 — same-source heterogeneity

| source | pairs | median delta_q (mmol/g) | positive fraction | median max geometry difference | ASA/AVA fraction |
|---|---:|---:|---:|---:|---:|
| DB0 | 8,053 | +0.342040 | 0.652800 | 0.225298 | 0.518068 |
| DB5 | 1,808 | +10.437185 | 0.994469 | 0.958033 | 0.721792 |
| DB6 | 476 | -0.244486 | 0.342437 | 0.180201 | 0.079832 |
| DB13 | 225 | +0.466370 | 0.702222 | 0.172244 | 0.391111 |

Do not interpret these as causal database-source effects. Source populations occupy very different geometry regimes and driver compositions. H6 primarily explains why the earlier leave-one-source-out robustness results change strongly in magnitude.

## Repository/reproducibility note

The repository is organized for handover (`scripts/step1`, `scripts/step2`, `scripts/step3`, `results/step1`, etc.), while many historical scripts were originally written against the local folders `Step 1 preparation`, `Step 1 results`, `Step 2 calculation`, `Step 2 results`, `Step 3 production`, and `Step 3 results`. Historical source files are preserved for provenance. Use the compatibility-workspace instructions on this branch before rerunning path-dependent historical scripts; do not assume direct execution from the reorganized `scripts/` tree is equivalent to the original environment.

Original ARC-MOF source data are not redistributed. The analysis used ARC-MOF release v7 (Zenodo record 16802743); exact expected source files and hashes are documented under `data_manifest/` and `provenance/`.

## What remains for the coauthor

The scientific analysis is intentionally frozen. Remaining work is manuscript/story review, structural rendering from the six selected pairs, journal formatting, author contributions, competing interests, acknowledgements/funding, and final decisions about permanent code/data archiving. Any new science should be treated as a new analysis branch rather than silently altering the frozen workflow.
