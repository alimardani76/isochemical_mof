# Project 17 — Pressure-Dependent Pore-Geometry Effects in Chemistry- and Topology-Matched MOFs

This repository contains the reproducible analysis workflow for **Project 17**, a matched-family analysis of pore-geometry effects in the ARC–MOF database.

The central design is deliberately outcome-blind:

1. define same-recorded-chemistry families;
2. refine them by recorded topology and dimensionality;
3. quantify within-family pore-geometry variation;
4. freeze a 10% geometry-contrast threshold;
5. select exactly one deterministic maximum-separation pair per eligible family;
6. freeze the confirmatory adsorption endpoint;
7. only then read adsorption/process outcomes.

The confirmatory endpoint is **CH4 uptake at 298 K and 65 bar in mmol g^-1**.

## Main scientific result

The frozen cohort contains **11,072 geometry pairs** comprising **22,144 unique frameworks**.

For the confirmatory high-pressure CH4 endpoint:

- median geometry-high minus geometry-low response: **+0.5836 mmol g^-1**
- family-bootstrap 95% CI: **[0.5546, 0.6149] mmol g^-1**
- positive pairs: **70.5%**
- >=20% geometry-contrast tier: **+1.6980 mmol g^-1**, 78.3% positive
- >=30% geometry-contrast tier: **+3.1645 mmol g^-1**, 85.2% positive

The response is not universal across geometry classes. ASA- and AVA-driven pairs carry most of the pooled 10% signal, while diameter-driven pairs have slightly negative median responses. Pressure also changes the sign structure: pressure-activated pairs are substantially more common than pressure-suppressed pairs.

## Repository layout

```text
Project17/
├── README.md
├── HANDOVER.md
├── LICENSE
├── .gitignore
├── environment/
│   └── requirements-lock.txt
├── data_manifest/
│   ├── RAW_DATA_REQUIRED.md
│   ├── REPO_FILE_MANIFEST.csv
│   └── LARGE_FILES_NOT_COMMITTED.csv
├── scripts/
│   ├── step1/
│   ├── step2/
│   ├── step3/
│   └── audits/
├── results/
│   ├── step1/
│   ├── step2/
│   └── step3/
├── figures/
│   ├── source/
│   └── final/
├── manuscript/
│   ├── main.tex
│   ├── Project17_SI.tex
│   ├── Project17_SI_closure_tables.tex
│   └── Project17_References.bib
└── provenance/
    └── SHA256SUMS.txt
```

## Raw data

Raw ARC–MOF files are **not redistributed in this repository**.

The analysis used **ARC–MOF release v7, Zenodo record 16802743**. The local `raw/` directory must be reconstructed before rerunning the full pipeline. See [`data_manifest/RAW_DATA_REQUIRED.md`](data_manifest/RAW_DATA_REQUIRED.md).

The raw charged-CIF archive and original ARC–MOF tables remain external source data. This repository instead contains:

- all analysis scripts;
- all independent audit scripts;
- frozen definitions/manifests;
- compact result tables;
- figure source code;
- final figures;
- manuscript/SI source;
- file checksums;
- environment lock.

Large pair-level/intermediate files that exceed a practical GitHub size are listed in `data_manifest/LARGE_FILES_NOT_COMMITTED.csv`. They should be distributed via GitHub Releases, Zenodo, institutional storage, or Git LFS if needed.

## Reproducing the analysis

Run from the repository/project root with the exact environment in `environment/requirements-lock.txt`.

The intended execution order is:

```text
Stage 1 — outcome-blind cohort construction
  registry
  charged-CIF chemistry extraction
  same-recorded-chemistry families
  same-recorded-architecture refinement

Step 2 — geometry definition
  geometry variation census
  threshold census
  frozen deterministic pair catalogue

Step 3 — outcome analysis
  outcome schema / coverage inventory
  confirmatory endpoint freeze
  primary CH4 analysis
  secondary outcome atlas
  cross-condition consistency
  response archetypes
  dominant-context robustness
  database-provenance robustness
  final SI reporting
```

After each analytical stage, run the corresponding independent audit in `scripts/audits/`. A stage should not be treated as complete unless its audit passes.

The late-stage audited commands used in the final workflow include:

```powershell
py ".\Step 3 production\12_analyze_robustness_transferability.py"
py .\test_14.py

py ".\Step 3 production\13_analyze_database_provenance.py"
py .\test_16.py

py ".\Step 3 production\14_finalize_si_reporting_v2.py"
py .\test_18.py
```

Earlier scripts and tests are preserved in the repository under their original stage folders.

## Frozen definitions

Do not change these definitions when reproducing the reported paper:

- recorded chemistry key:
  - scale-invariant whole-CIF elemental composition;
  - scale-invariant metal-element composition;
  - metal cluster;
  - linker cluster;
  - functional cluster.
- recorded architecture key:
  - frozen chemistry group;
  - recorded topology;
  - recorded dimensionality.
- scientific geometry descriptors:
  - ASA, AVA, AVAf, POAVA, POAVAf, Di, Df, Dif.
- primary geometry threshold: **10%**.
- stronger prespecified sensitivity tiers: **20% and 30%**.
- one deterministic pair per eligible family.
- pair orientation: lower to higher value of the frozen pair driver descriptor.
- confirmatory endpoint: **CH4, 298 K, 65 bar, mmol g^-1**.
- primary estimator: median family-level signed difference.
- bootstrap: 10,000 family resamples, seed 17.

## Figures

The main paper has four figures:

- **Figure 1** — outcome-blind cohort construction and geometry support.
- **Figure 2** — confirmatory high-pressure methane response.
- **Figure 3** — pressure, adsorbate, and process dependence.
- **Figure 4** — pressure-response archetypes, geometry-driver heterogeneity, and topology dependence.

Supporting figures:

- **Figure S1** — N2/H2 pressure responses.
- **Figure S2** — AFM–SSP process trade-off.
- **Figure S3** — cross-condition concordance matrices.

All plotting code is included under `figures/source/`. Figures must be regenerated from frozen result tables, not manually edited.

## Important interpretation boundary

This analysis supports **geometry-associated differences within tightly matched recorded chemistry and architecture families**.

It does **not** establish:

- atom-by-atom structural identity;
- a causal mechanical deformation experiment;
- a universal "larger pore is better" rule;
- universal improvement in separation performance;
- experimental transferability across MOF space.

The final frozen cohort is overwhelmingly hypothetical: **99.2% of pairs are hypothetical–hypothetical**. Experimental–experimental support is limited.

## Handover

For project history, frozen decisions, completed results, caveats, and what should or should not be changed, read [`HANDOVER.md`](HANDOVER.md) before rerunning or modifying the workflow.
