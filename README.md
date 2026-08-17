# Matched MOF Families Reveal Regime-Dependent Pore-Geometry Effects on Adsorption

This repository contains the analysis, audited intermediate results, figure-generation workflows, and manuscript source for a matched-family study of pore geometry in the ARC–MOF database.

The study asks a deliberately controlled question: **when major recorded chemistry and broad architecture differences are fixed before adsorption outcomes are inspected, what geometry-associated response remains?**

## Paper at a glance

The frozen primary catalogue contains **11,072 matched pairs** (22,144 unique frameworks). Pair identity, pair orientation, the 10% geometry criterion, and the primary endpoint were fixed before adsorption values were opened.

At the primary endpoint—CH4 uptake at 298 K and 65 bar in mmol g^-1—the median geometry-high minus geometry-low response is **+0.5836 mmol g^-1** (95% family-bootstrap interval **0.5546–0.6149 mmol g^-1**; **70.5%** positive pairs).

The central materials conclusion is not a universal “larger pore is better” rule. Accessible-space-labelled pairs (especially ASA/AVA) are strongly enriched in favorable high-pressure methane responses, whereas diameter-labelled populations have slightly negative median responses. The same structural direction is then re-ordered by adsorbate, loading condition, framework density, and process objective.

## Repository map

```text
manuscript/          current manuscript and Supporting Information source
figures/redesign/    reproducible publication-figure generators (Figures 1–4, S1–S6)
figures/source/      historical plotting source + Figure 5 structural renderer/provenance
figures/archive/     earlier artwork retained for provenance, not current submission art
results/             canonical frozen analysis outputs and post-freeze robustness outputs
scripts/             original staged analysis and independent audits
submission_upgrade/  post-freeze robustness/structural scripts (historical directory name)
reproduce/           reproduction instructions and compatibility workspace
data_manifest/       ARC–MOF input inventory and raw-data requirements
environment/         recorded Python environment
provenance/          historical checksum records
```

The directory name `submission_upgrade/` is retained because it is embedded in historical manifests and script paths. In publication-facing terms it contains **secondary/post-freeze robustness and structural-analysis modules**; it is not a separate scientific project.

## Frozen analysis contract

The reported paper depends on the following frozen definitions:

- chemistry key: scale-invariant whole-CIF composition, scale-invariant metal composition, and ARC–MOF metal/linker/functional cluster assignments;
- architecture key: frozen chemistry group + recorded topology + recorded dimensionality;
- pore descriptors: ASA, AVA, AVAf, POAVA, POAVAf, Di, Df, Dif;
- primary geometry criterion: **10%**;
- stronger prespecified contrast tiers: **20% and 30%**;
- one deterministic pair per eligible family;
- pair orientation: lower → higher value of the frozen largest-contrast descriptor;
- primary endpoint: **CH4, 298 K, 65 bar, mmol g^-1**;
- primary estimator: median family-level signed difference;
- uncertainty: 10,000 family-bootstrap resamples, seed 17.

Changing any item above defines a new analysis and should not overwrite the frozen outputs used by the manuscript.

## Data

Raw ARC–MOF files are **not redistributed** in this repository. The analysis used **ARC–MOF release v7, Zenodo record 16802743**. Required source filenames and the recorded input hashes are documented in `data_manifest/` and `provenance/`.

The repository contains the compact/frozen outputs needed to audit the reported results. Large upstream source files remain under the ARC–MOF release terms.

## Reproduce the publication figures

The current quantitative figure workflow is under `figures/redesign/`.

```bash
python -m pip install -r figures/redesign/requirements.txt
python figures/redesign/validate_redesign_values.py
python figures/redesign/run_all.py
```

The validator runs before figure generation and aborts if frozen numerical anchors do not match the reported analysis. Outputs are written under `figures/redesign/outputs/` and are intentionally not versioned as generated build products.

Figure 5 has a separate structural workflow because it depends on deterministic case selection, the 12 frozen H4 CIFs, locked OVITO rendering, and a manually assembled publication composite. See:

- `submission_upgrade/H4_STRUCTURAL_FIGURE_METHOD.md`
- `figures/source/12_make_figure5_structural_assets.py`
- `figures/source/Figure_5_FINAL_ARTIFACTS.md`
- `PUBLICATION_ARTIFACTS.md`

## Reproduce the scientific workflow

Historical scripts retain their original path assumptions. Do not run relocated `scripts/step1`, `scripts/step2`, or `scripts/step3` files blindly from the repository tree.

Use:

```bash
python reproduce/build_legacy_workspace.py
```

and follow `reproduce/README.md` to recreate the expected directory layout and restore the external ARC–MOF inputs before running source-dependent stages.

Every scientific stage has an independent audit. A regenerated stage should not be accepted unless the corresponding audit passes.

## Manuscript

The publication-facing manuscript source is under `manuscript/`.

The manuscript and SI currently correspond to the post-PASS-E writing checkpoint: the main text references all Supporting Information Figures S1–S6 and Tables S1–S33, and the generated SI closure tables remain unchanged.

See `manuscript/README.md` for compilation and figure-bundle details.

## Interpretation boundary

This is a matched observational analysis of recorded structures. It supports **geometry-associated differences within recorded-chemistry- and architecture-matched families**. It does not establish atom-by-atom identity, causal mechanical framework deformation, isolated single-descriptor perturbations, a continuous transition pressure from the discrete endpoint grid, device-level volumetric performance from crystallographic v/v, source-database causality, or broad experimental transferability.

The internal field `driver_descriptor` is publication-facing as **largest-contrast descriptor/class**. Pore descriptors co-vary; the label is an attribution class, not proof of an isolated causal variable.

The frozen cohort is overwhelmingly hypothetical (99.2% hypothetical–hypothetical pairs).

## Publication and archival status

The scientific analysis is frozen; manuscript and repository packaging are still being finalized for journal submission. Outstanding release-level items are listed in `PUBLICATION_STATUS.md`.

In particular, a permanent article/code-data archive DOI and an explicit license for the authors' original analysis code have **not yet been finalized**. No license is implied by public visibility; see `LICENSE_NOTE.md`.

## Historical provenance

`ANALYSIS_PROVENANCE.md` records the frozen design, bounded post-freeze analyses, and prior repository milestones. `HANDOVER.md` remains only as a compatibility pointer for older links.
