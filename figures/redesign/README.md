# Project 17 publication-figure redesign

This directory contains the reproducible redesign layer for Figures 1–4 and
Supporting Figures S1–S6. The redesign is intentionally separated from the
frozen analysis and from the original production artwork in `figures/source/`.

## Scientific contract

The scripts in this directory **must not** change the frozen Project 17 analysis.
They read already-audited tables under `results/` and only change visual
communication: typography, panel hierarchy, plot grammar, spacing, annotation,
color, and export format.

The numerical preflight protects the main invariants, including:

- 11,072 frozen primary pairs;
- primary CH4 median change of +0.5835545 mmol g^-1;
- family-bootstrap 95% CI of [0.5545650, 0.6149215] mmol g^-1;
- 20% and 30% geometry-tier counts of 6,948 and 5,115;
- descriptor-class anchors for ASA, AVA, and Df;
- pressure-activated and pressure-suppressed archetype counts.

If `validate_redesign_values.py` fails, do not use the regenerated figures.

## Layout

```text
figures/redesign/
  README.md
  run_all.py
  figure_style_redesign.py
  data_utils.py
  validate_redesign_values.py
  R01_figure1_conservative.py
  R01_figure1_concept.py
  R02_figure2_conservative.py
  R02_figure2_concept.py
  R03_figure3_conservative.py
  R03_figure3_concept.py
  R04_figure4_conservative.py
  R04_figure4_concept.py
  RS1_figureS1.py
  RS2_figureS2.py
  RS3_figureS3.py
  RS4_figureS4.py
  RS5_figureS5.py
  RS6_figureS6.py
  spec/
```

The conservative variants preserve the current evidence architecture as closely
as possible. The concept variants change visual hierarchy only; they do not
change statistical status or numerical results.

## Environment

Use the repository environment or install the minimal plotting dependencies:

```bash
python -m pip install -r figures/redesign/requirements.txt
```

## Regenerate all redesign candidates

From the repository root:

```bash
python figures/redesign/run_all.py
```

Outputs are written to `figures/redesign/outputs/` and are ignored by Git.
Every figure exports PDF, SVG, and 600-dpi PNG artwork together with a source/run
manifest. Dense scatter layers may be rasterized inside otherwise-vector output.

To regenerate a subset:

```bash
python figures/redesign/run_all.py --only \
  R01_figure1_conservative.py \
  R02_figure2_conservative.py \
  R03_figure3_conservative.py \
  RS5_figureS5.py
```

## Visual conventions

- uppercase panel labels;
- Arial/Helvetica-compatible sans-serif typography;
- restrained color-blind-safe palette;
- white background and no decorative grids;
- consistent process and descriptor colors across main and SI figures;
- editable vector text in PDF/SVG output;
- direct labels preferred when they reduce legend clutter.

The detailed style contract is in `spec/figure_style.md`.

## Figure-specific design notes

**Figure 1.** The conservative version retains the six-panel cohort audit. The
concept version makes the outcome-blind construction visually explicit. Cohort
counts and thresholds remain frozen.

**Figure 2.** The primary matched-pair response is preserved. The bootstrap
panel shows the single audited 95% CI without redundant labeling. In the
descriptor panel, point position encodes the median signed change, while the
annotation reports the fraction of positive pairs; a descriptor may therefore
have a negative median while still containing positive individual pairs.

**Figure 3.** Pressure responses are drawn as discrete lower/higher endpoint
dumbbells. Connecting segments are visual pairings only and must not be read as
continuous isotherms or fitted transition pressures.

**Figure 4.** Archetypes use the audited 50% majority rule. The visualization
emphasizes pressure activation/suppression and geometry-class composition
without changing the classification.

**S4–S6.** These remain secondary/post-freeze robustness figures. The redesign
must not promote them to confirmatory analyses.

## Interpretation boundaries

- use `largest-contrast descriptor/class`, not causal `driver`, when discussing
  correlated pore changes;
- LOW/HIGH refers to geometry ordering, not adsorption-performance ordering;
- do not infer continuous pressure transitions from discrete endpoints;
- crystallographic v/v is not packed-bed or device-level capacity;
- source-stratified differences are descriptive and are not source-causal.

## Relationship to Figure 5 structural reproducibility

Figure 5 structural case selection and the locked OVITO rendering workflow are
maintained separately because they have different reproducibility inputs and
artifacts. Keeping the structural-rendering workflow separate prevents figure
redesign code from silently altering case selection or structural provenance.
