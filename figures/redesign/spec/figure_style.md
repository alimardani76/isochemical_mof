# Project 17 Figure Style Specification — redesign package

## Scientific boundary

This style layer changes **appearance and visual grammar only**. It must not change frozen pair membership, pair orientation, the 10/20/30% thresholds, endpoint definitions, estimators, bootstrap settings, secondary classifications, or numeric results. Publication-facing text uses **largest-contrast descriptor/class** rather than causal `driver` wording.

## Figure geometry

- Main multi-panel width: **7.15 in (181.6 mm)**.
- SI width: 5.2–8.1 in depending on panel density.
- White background; no decorative grid.
- Top and right spines removed when they add no information.
- Dense clouds are rasterized inside PDF/SVG exports; text and axes remain vector.

## Typography

- Family: Arial first; Helvetica, Liberation Sans, DejaVu Sans fallback.
- Base text: **7.5 pt, regular**.
- Axis titles: **9.0 pt, bold**.
- Tick labels: **7.2 pt, regular**.
- Legends: **6.9 pt**.
- Annotations: target **≥6.5 pt**.
- Panel labels: **10.8 pt, bold, uppercase A/B/C/D...**.
- The previous 18-pt main-figure panel letters are intentionally removed because they compete with the data.
- Do not make all text bold. Hierarchy comes from selective weight, spacing, and placement.

## Palette

The palette stays close to the established Project 17 / Okabe–Ito-safe family, but is used more semantically and sparingly:

| Role | Hex |
|---|---|
| Ink | `#1A1A1A` |
| Primary blue | `#0072B2` |
| Sky | `#56B4E9` |
| Teal | `#009E73` |
| Amber | `#E69F00` |
| Vermillion accent | `#D55E00` |
| Purple | `#CC79A7` |
| Slate | `#5F6B73` |
| Gray | `#8A8A8A` |
| Pale background | `#EFF3F6` |

Rules:
- Never use red/green alone to encode sign.
- Accessible-space descriptor family: blue/teal visual family.
- Diameter descriptor family: purple family.
- Process colors are stable across Figure 3 and SI.
- Neutral/reference information stays gray/black.

## Panel-specific redesign choices

### Figure 1
- **Conservative:** keep A–F, clean hierarchy, neutralize funnel colors, retain topology.
- **Concept:** make outcome-blind chronology the large opening panel; combine threshold-support information; keep class-support and multidimensional-pair panels; move topology composition out of the main concept version.

### Figure 2
- **Conservative:** preserve all six evidence panels but reduce visual heaviness.
- **Concept:** emphasize pair-level primary response, primary/tier estimates, largest-contrast geometry-class heterogeneity, and geometry-contrast deciles. Bootstrap histogram/topology response are demoted from the concept version, not deleted from the evidence base.

### Figure 3
- Replace continuous-looking pressure lines with **discrete endpoint dumbbells** in both variants. Pressure labels are placed at the stored endpoints. This is the most important visual correction in the set.
- Process panels use aligned zero-centered lollipop/dot grammar.

### Figure 4
- Explicitly label the four 50%-majority archetype regions.
- Make the ~4.5× pressure-activation/suppression asymmetry visible.
- Keep descriptor-class composition central; topology remains a modulation/applicability panel, not a causal mechanism.

### SI
- S1 adopts the same discrete-endpoint grammar as Figure 3.
- S2 remains a clean AFM–SSP scatter.
- S3 preserves predefined endpoint ordering; no outcome-driven clustering.
- S4 emphasizes clean-dominance support and descriptor-resolved behavior.
- S5 preserves the exact H3 pair-level mmol/g vs v/v panel and the density/basis diagnostics.
- S6 expands the same-source summary into effect / geometry contrast / ASA-AVA composition panels.

## Export

Every Stage-B script exports:
- PDF (vector-first; editable text, fonttype 42)
- SVG (editable text)
- PNG (600 dpi)
- JSON source/run manifest

No manual editing of bar lengths, point positions, or numerical labels is part of this workflow.
