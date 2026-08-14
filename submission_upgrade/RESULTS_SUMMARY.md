# Project 17 submission-upgrade results summary

These are console-verified headline values from completed local runs. Canonical machine-readable CSV/Parquet/JSON/figure/CIF outputs remain the source of record and should be copied from the local Project17 working tree before this branch is merged.

## H2 — geometry-attribution stability

| criterion | pairs | cohort fraction | median top1/top2 | median delta_q (mmol/g) | positive fraction |
|---|---:|---:|---:|---:|---:|
| top1/top2 >= 1.10 | 4,603 | 0.415733 | 1.344062 | 0.413537 | 0.662611 |
| top1/top2 >= 1.25 | 2,866 | 0.258851 | 1.638244 | 0.187258 | 0.601535 |
| top1/top2 >= 1.50 | 1,715 | 0.154895 | 2.118525 | 0.038287 | 0.531195 |

Increasing isolation of the nominal driver attenuates the primary signal. The frozen driver is therefore a largest-contrast attribution label within correlated pore changes, not a causal one-descriptor perturbation.

## H3 — 65-bar CH4 uptake basis

| metric | pairs | median delta | mean delta | positive fraction | bootstrap 95% CI |
|---|---:|---:|---:|---:|---:|
| mmol/g | 11,072 | 0.583554 | 2.427468 | 0.705022 | [0.554565, 0.614922] |
| v/v | 11,072 | 3.797193 | 13.825888 | 0.608833 | [3.438461, 4.185063] |
| wt% | 11,072 | 0.933689 | 3.883949 | 0.705022 | [0.887304, 0.983874] |

The positive median survives volumetric normalization; density moderates pair-level sign consistency but does not reverse the population result.

## H4 — structural cases

A pressure_activated_ASA: +9.096988 mmol/g
B pressure_activated_AVA: +2.994237 mmol/g
C positive_both_accessible_space: +2.667362 mmol/g
D negative_both_diameter: -0.459752 mmol/g
E pressure_suppressed: -0.187601 mmol/g
F experimental_source_pair: +0.082596 mmol/g

Twelve CIFs were extracted locally with a checksum/extraction manifest.

## H6 — same-source primary effects

| source | pairs | median delta_q (mmol/g) | mean delta_q | positive fraction | median max geometry diff | ASA/AVA fraction |
|---|---:|---:|---:|---:|---:|---:|
| DB0 | 8,053 | 0.342040 | 0.704850 | 0.652800 | 0.225298 | 0.518068 |
| DB5 | 1,808 | 10.437185 | 10.665019 | 0.994469 | 0.958033 | 0.721792 |
| DB6 | 476 | -0.244486 | -0.214923 | 0.342437 | 0.180201 | 0.079832 |
| DB13 | 225 | 0.466370 | 0.659570 | 0.702222 | 0.172244 | 0.391111 |

Source identity is confounded with geometry magnitude and driver composition and is treated as an applicability variable rather than a causal factor.
