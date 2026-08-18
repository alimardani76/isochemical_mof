# Matched MOF Families Reveal Regime-Dependent Pore-Geometry Effects on Adsorption

This repository is the publication-facing reproducibility companion for the matched-family analysis of pore geometry in ARC–MOF.

The study asks a controlled question: **when major recorded chemistry and broad architecture differences are fixed before adsorption outcomes are inspected, what geometry-associated response remains?**

## Paper at a glance

The frozen primary catalogue contains **11,072 matched pairs** (22,144 unique frameworks). Pair identity, orientation, the 10% primary geometry criterion, and the primary adsorption endpoint were fixed before outcome inspection.

At CH4 uptake at 298 K and 65 bar in mmol g^-1, the median geometry-high minus geometry-low response is **+0.5836 mmol g^-1** (95% family-bootstrap interval **0.5546–0.6149 mmol g^-1**; **70.5%** positive pairs).

The central materials conclusion is not a universal “larger pore is better” rule. Accessible-space-labelled pairs are strongly enriched in favorable high-pressure methane responses, whereas diameter-labelled populations have slightly negative median responses. The value of the same structural direction is then reorganized by loading condition, framework density, and process objective.

## Current publication checkpoint

As of **2026-08-18**, `shayan-final-edit` contains the **Materials Horizons G2 candidate**:

- Communication-level manuscript compression completed in PASS G1;
- final 40-entry audited bibliography from PASS B-final;
- 156-word **New Concepts** paragraph inserted after the abstract;
- audited Supporting Information with complete main↔SI evidence navigation;
- journal-facing cover letter, title audit, submission checklist, positioning memo, and graphical-abstract/TOC brief under `manuscript/submission/`.

The scientific analysis itself is frozen. G1/G2 are editorial and journal-packaging passes, not new analyses.

## Repository map

```text
manuscript/          current manuscript, SI, bibliography, and journal-facing submission support
figures/redesign/    reproducible publication-figure generators (Figures 1–4, S1–S6)
figures/source/      historical plotting source + Figure 5 structural renderer/provenance
figures/archive/     superseded artwork retained for provenance, not current submission art
results/             canonical frozen analysis outputs and post-freeze robustness outputs
scripts/             original staged analysis and independent audits
submission_upgrade/  post-freeze robustness/structural scripts (historical directory name)
reproduce/           reproduction instructions and compatibility workspace
data_manifest/       ARC–MOF input inventory and raw-data requirements
environment/         recorded Python environment
provenance/          historical checksum records
```

The historical directory name `submission_upgrade/` is retained because it is embedded in manifests and script paths. Publication-facing text refers to these as secondary/post-freeze robustness and structural-analysis modules.

## Frozen analysis contract

The reported study depends on the following frozen definitions:

- chemistry key: scale-invariant whole-CIF composition, scale-invariant metal composition, and ARC–MOF metal/linker/functional cluster assignments;
- architecture key: frozen chemistry group + recorded topology + recorded dimensionality;
- pore descriptors: ASA, AVA, AVAf, POAVA, POAVAf, Di, Df, Dif;
- primary geometry criterion: **10%**;
- stronger prespecified tiers: **20% and 30%**;
- one deterministic pair per eligible family;
- orientation: lower → higher value of the frozen largest-contrast descriptor;
- primary endpoint: **CH4, 298 K, 65 bar, mmol g^-1**;
- primary estimator: median family-level signed difference;
- uncertainty: 10,000 family-bootstrap resamples, seed 17.

Changing any item above defines a new analysis and must not overwrite the frozen outputs used by this manuscript.

## Data and reproduction

Raw ARC–MOF files are **not redistributed** here. The study used **ARC–MOF release v7, Zenodo record 16802743**. Required filenames and recorded input hashes are documented under `data_manifest/` and `provenance/`.

Current quantitative figures are regenerated from `figures/redesign/`:

```bash
python -m pip install -r figures/redesign/requirements.txt
python figures/redesign/validate_redesign_values.py
python figures/redesign/run_all.py
```

Figure 5 uses a separate deterministic structural workflow documented in `submission_upgrade/H4_STRUCTURAL_FIGURE_METHOD.md` and `figures/source/Figure_5_FINAL_ARTIFACTS.md`.

Historical source-dependent scripts retain their original path assumptions. Use `reproduce/build_legacy_workspace.py` and `reproduce/README.md` rather than running relocated scripts blindly.

## Manuscript and Materials Horizons package

Publication source is under `manuscript/`. The current G2 manuscript contains the New Concepts paragraph and the audited 40-reference bibliography. `SI.tex` and the generated SI closure tables are unchanged by G2.

Journal-facing support files are under `manuscript/submission/`.

The remaining items are release/author attestations, not scientific-analysis tasks: CRediT roles, conflicts, funding/acknowledgements/computing, repository license, and the final tagged/DOI-bearing submission release. See `PUBLICATION_STATUS.md`.

## Interpretation boundary

This is a matched observational analysis of recorded structures. It supports **geometry-associated differences within recorded-chemistry- and architecture-matched families**. It does not establish atom-by-atom identity, causal mechanical framework deformation, isolated single-descriptor perturbations, a continuous transition pressure from discrete endpoints, device-level volumetric performance from crystallographic v/v, source-database causality, or broad experimental transferability.

The internal field `driver_descriptor` is publication-facing as **largest-contrast descriptor/class**. Pore descriptors co-vary; this is an attribution label, not proof of an isolated causal variable.

The frozen cohort is overwhelmingly hypothetical (99.2% hypothetical–hypothetical pairs).

## Release status

This branch is the coauthor-review candidate, **not yet the immutable journal release**. The interim Git checkpoint currently cited in the manuscript Data Availability section must be replaced by the final tagged/released version during PASS H after author approval.

No code license is implied by public repository visibility; see `LICENSE_NOTE.md`.

`ANALYSIS_PROVENANCE.md` records the frozen design and prior milestones. `HANDOVER.md` remains only as a historical compatibility pointer.
