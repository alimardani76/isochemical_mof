# Project 17 — Pressure-Dependent Pore-Geometry Effects in Chemistry- and Topology-Matched MOFs

This repository contains the reproducible analysis workflow for **Project 17**, a matched-family study of pore-geometry effects in the ARC–MOF database.

The central design is outcome-blind:

1. define same-recorded-chemistry families;
2. refine them by recorded topology and dimensionality;
3. quantify within-family pore-geometry variation;
4. freeze a 10% geometry-contrast threshold;
5. select exactly one deterministic maximum-separation pair per eligible family;
6. freeze the confirmatory adsorption endpoint;
7. only then read adsorption/process outcomes.

The confirmatory endpoint is **CH4 uptake at 298 K and 65 bar in mmol/g**.

## Main scientific result

The frozen cohort contains **11,072 geometry pairs** comprising **22,144 unique frameworks**.

- median geometry-high minus geometry-low response: **+0.5836 mmol/g**
- family-bootstrap 95% CI: **[0.5546, 0.6149] mmol/g**
- positive pairs: **70.5%**
- >=20% geometry tier: **+1.6980 mmol/g**, 78.3% positive
- >=30% geometry tier: **+3.1645 mmol/g**, 85.2% positive

The response is not universal across geometry classes. Pairs labelled by ASA/AVA as their largest geometry contrast are strongly enriched in favorable responses, while diameter-labelled pairs have slightly negative median responses. Pressure, adsorbate, topology, and process objective all modify the response.

## Repository layout

```text
README.md
HANDOVER.md
LICENSE_NOTE.md
.gitignore

data_manifest/       raw-data inventory and repository manifests
environment/         Python/environment records
figures/             plotting sources and final figures
manuscript/          manuscript/SI source
provenance/          SHA256 provenance
reproduce/           compatibility-workspace instructions
results/             frozen analysis outputs
scripts/             historical stage scripts and audits
submission_upgrade/  post-freeze coauthor robustness work
```

## Raw data

Raw ARC–MOF files are **not redistributed here**. The analysis used **ARC–MOF release v7, Zenodo record 16802743**. Required filenames and recorded hashes are documented under `data_manifest/` and `provenance/`.

## Reproducing the historical workflow

The repository is organized for handover (`scripts/step1`, `scripts/step2`, `scripts/step3`, `results/step1`, etc.), whereas many historical scripts were originally written against the local folders:

```text
Step 1 preparation/
Step 1 results/
Step 2 calculation/
Step 2 results/
Step 3 production/
Step 3 results/
```

Therefore, do **not** assume that executing a relocated historical script directly from `scripts/` reproduces its original path environment. Use `reproduce/build_legacy_workspace.py` and the instructions in `reproduce/README.md` to reconstruct a compatible workspace, then restore the external ARC–MOF raw data in `workspace/raw/` before rerunning source-dependent stages.

Each scientific stage has an independent audit. A stage should not be considered complete unless its audit passes.

## Frozen definitions

Do not silently change these when reproducing the reported paper:

- chemistry key: scale-invariant whole-CIF composition + scale-invariant metal composition + metal/linker/functional ARC–MOF cluster assignments;
- architecture key: frozen chemistry group + recorded topology + recorded dimensionality;
- scientific pore descriptors: ASA, AVA, AVAf, POAVA, POAVAf, Di, Df, Dif;
- primary geometry threshold: **10%**;
- stronger prespecified tiers: **20% and 30%**;
- one deterministic pair per eligible family;
- pair orientation: lower to higher value of the frozen largest-contrast descriptor;
- confirmatory endpoint: **CH4, 298 K, 65 bar, mmol/g**;
- primary estimator: median family-level signed difference;
- bootstrap: 10,000 family resamples, seed 17.

## Main figures

- **Figure 1** — outcome-blind cohort construction and geometry support.
- **Figure 2** — confirmatory high-pressure methane response.
- **Figure 3** — pressure, adsorbate, and process dependence.
- **Figure 4** — response archetypes and geometry/topology heterogeneity.

Supporting figures S1–S3 cover N2/H2 responses, AFM–SSP trade-offs, and cross-condition concordance. Post-freeze scripts H2/H3/H6 also generate candidate Figures S4–S6 locally.

## Interpretation boundary

This analysis supports **geometry-associated differences within tightly matched recorded chemistry and architecture families**. It does not establish atom-by-atom structural identity, causal framework deformation, a universal larger-pore rule, universal process improvement, or experimental transferability across MOF space.

The frozen `driver_descriptor` is the descriptor with the largest observed geometry contrast in a pair. It is an attribution label, not proof that this descriptor changed in isolation or caused the adsorption response.

The final cohort is overwhelmingly hypothetical: **99.2% of frozen pairs are hypothetical–hypothetical**.

## Submission-upgrade branch

The `submission-upgrade` branch contains post-freeze checks requested during coauthor handover. They do **not** redefine the frozen cohort, orientation, geometry threshold, endpoint, or estimator.

### H2 — geometry-attribution stability

As the largest geometry contrast is required to dominate the second-largest more strongly, the pooled primary response attenuates:

- top1/top2 >=1.10: 4,603 pairs, median **+0.4135 mmol/g**, 66.3% positive;
- >=1.25: 2,866 pairs, median **+0.1873 mmol/g**, 60.2% positive;
- >=1.50: 1,715 pairs, median **+0.0383 mmol/g**, 53.1% positive.

This supports a multidimensional pore-change interpretation rather than an isolated single-descriptor causal rule.

### H3 — uptake-basis/density robustness

The positive 65-bar methane response persists on a volumetric basis:

- mmol/g: median +0.5836, 70.5% positive, 95% CI [0.5546, 0.6149];
- v/v: median +3.7972, 60.9% positive, 95% CI [3.4385, 4.1851];
- wt%: median +0.9337, 70.5% positive, 95% CI [0.8873, 0.9839].

The v/v comparison is the meaningful density-related robustness check; wt% is closely tied to the mass-basis molar uptake for fixed CH4.

### H4 — structural case studies

Six mutually exclusive frozen pairs were selected deterministically across pressure-activated ASA/AVA, positive-both accessible-space, negative diameter, pressure-suppressed, and experimental-source strata. The 12 corresponding CIFs were extracted locally with checksums for structural rendering.

### H6 — source-stratified effects

Same-source responses are heterogeneous: DB0 median +0.342, DB5 +10.437, DB6 -0.244, and DB13 +0.466 mmol/g. These strata also differ sharply in geometry magnitude and ASA/AVA composition, so source identity is treated as an applicability variable rather than a causal factor.

See `HANDOVER.md`, `submission_upgrade/RESULTS_SUMMARY.md`, and `submission_upgrade/LOCAL_ARTIFACTS_TO_ADD.md`.

## Coauthor handover

Start with [`HANDOVER.md`](HANDOVER.md). It records the frozen design, key results, post-freeze sprint, interpretation boundaries, and what must be rerun if a frozen definition is changed.
