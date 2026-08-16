# Figure 5 structural-pair selection and rendering

This file records the reproducible workflow used for the six-panel structural Figure 5. It accompanies `submission_upgrade/17_select_structural_case_studies.py` and `results/submission_upgrade/H4_structural_cases/`.

## Scope

Figure 5 contains six matched LOW→HIGH geometry pairs (12 CIFs). LOW/HIGH is the frozen ordering by each pair's `driver_descriptor`; it is not an ordering by adsorption performance and does not represent a before/after structural transformation.

The renderings are post-hoc structural context for the matched-pair analysis. The local insets are not assigned as adsorption or binding sites.

## Deterministic structural-case selection

The selector is `submission_upgrade/17_select_structural_case_studies.py`.

Six strata are declared before visualization:

| Panel | Stratum |
|---|---|
| A | pressure-activated, ASA-led |
| B | pressure-activated, AVA-led |
| C | positive-both accessible-space |
| D | negative-both diameter |
| E | pressure-suppressed |
| F | experimental–experimental provenance |

Panels A–C additionally use the frozen 20% sensitivity criterion where defined. Six distinct `architecture_group_id` values are required.

Within each stratum, candidates are ranked by robust distance from the stratum median using `pair_max_fractional_difference`, `primary_delta_q_mmol_g`, and `activation_score`. Each variable is centred by its stratum median and scaled by the median absolute deviation (MAD), with population standard deviation as a fallback when MAD is zero. The Euclidean norm of the resulting robust z-scores is `representativeness_distance`.

The lowest-distance unused pair is selected; ties are resolved deterministically by `architecture_group_id`. Pair reuse across panels is forbidden. Visual attractiveness, maximum response, and response sign are not selection criteria.

Frozen selection outputs are `case_study_candidates_ranked.csv`, `case_study_selection_ledger.csv`, `case_study_framework_metrics.csv`, `cif_extraction_manifest.csv`, `run_manifest.json`, and the 12 CIFs in `results/submission_upgrade/H4_structural_cases/cifs/`.

## Structural rendering

The final renderer is `figures/source/12_make_figure5_structural_assets.py`.

Recommended software: Python 3.11, OVITO 3.15.5, NumPy, and Pillow. Hydrogens are hidden for clarity; all other chemical species are retained. Atom colours/radii are fixed across all LOW/HIGH structures. Explicit element-pair bond cutoffs are used only to obtain a readable visualization network and are not reported as pore metrics.

Crystallographic `[uvw]` directions are converted using the actual direct-space lattice vectors from each CIF. The final locked views are:

| Panel | LOW view | HIGH view | Up direction |
|---|---|---|---|
| A | `[001]` | `[001]` | `[010]` / `[010]` |
| B | `[100]` | `[010]` | `[001]` / `[001]` |
| C | `[010]` | `[100]` | `[001]` / `[001]` |
| D | `[001]` | `[001]` | `[010]` / `[010]` |
| E | `[001]` | `[001]` | `[010]` / `[010]` |
| F | `[010]` | `[010]` | `[001]` / `[001]` |

B and C intentionally use different literal axes because their CIF cell settings differ. The chosen orientations match the corresponding physical framework motif.

LOW and HIGH are rendered with the same orthographic field of view within each panel. The renderer uses a periodic buffer with three repeats in each screen-plane lattice direction and one repeat along the viewing direction, followed by a symmetric central crop. This keeps periodic edge fragments away from the final frame without editing the chemistry.

Final whole-framework images are 2800×2800 px. Insets are crops of the same working render, so no second camera is introduced. The locked inset centres and sizes are:

| Panel | Centre (x,y) | Crop (px) |
|---|---:|---:|
| A | (0.50,0.50) | 1400 |
| B | (0.60,0.60) | 1600 |
| C | (0.50,0.50) | 1600 |
| D | (0.33,0.33) | 1800 |
| E | (0.33,0.33) | 1800 |
| F | (0.50,0.50) | 1400 |

The renderer writes four lossless PNGs per panel: LOW whole, HIGH whole, LOW inset, and HIGH inset, together with a render manifest and SHA-256 checksums. PNG metadata is written at 600 dpi.

Run from the repository root:

```bash
python figures/source/12_make_figure5_structural_assets.py --cif-dir results/submission_upgrade/H4_structural_cases/cifs --output-dir results/submission_upgrade/H4_structural_cases/figure5_assets
```

## Interpretation guardrails

1. LOW/HIGH means geometry ordering, not adsorption performance.
2. Do not reverse a pair because its response is negative.
3. Do not describe the pair arrow as a transition or deformation trajectory.
4. Do not infer Df/Di/Dif from hand-measured distances in a rendering.
5. Do not claim an isolated descriptor mechanism when several geometry descriptors co-vary.
6. Panel F uses experimental-source structures, while the response labels remain simulation-derived.
7. Insets provide structural context only and should be labelled as representative local pore/channel views.
