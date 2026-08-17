# Publication figure generation

This directory contains the reproducible visualization layer for Figures 1–4 and Supporting Figures S1–S6. It is intentionally separated from the frozen scientific analysis.

These scripts read already-audited tables under `results/` and may change only visual communication. They must not change pair membership, orientation, thresholds, the primary endpoint, estimand, bootstrap definition, response archetypes, or post-freeze analysis status.

Before generation, `validate_redesign_values.py` verifies the principal frozen anchors, including 11,072 primary pairs; primary median +0.5835545 mmol g^-1; the family-bootstrap interval; 20/30% tier counts; ASA/AVA/Df anchors; and pressure-activated/suppressed archetype counts. If validation fails, regenerated figures must not be used.

## Install and generate

```bash
python -m pip install -r figures/redesign/requirements.txt
python figures/redesign/run_all.py
```

Outputs are written to `figures/redesign/outputs/` and ignored by Git. Each generator writes vector PDF/SVG, high-resolution PNG, and a run/source manifest.

## Visual and interpretation safeguards

- uppercase panel labels and restrained color-blind-safe styling;
- vector text/axes; dense point layers may be rasterized inside vector containers;
- publication text uses `largest-contrast descriptor/class`, not causal `driver`;
- LOW/HIGH refers to frozen geometry ordering;
- Figure 3 connects discrete stored endpoints only;
- S4–S6 remain secondary/post-freeze;
- crystallographic v/v is not device/packed-bed capacity;
- source strata are applicability/provenance categories, not causal factors.

See `spec/figure_style.md`. Structural Figure 5 has different inputs and provenance and is maintained under `figures/source/` plus `submission_upgrade/H4_STRUCTURAL_FIGURE_METHOD.md`.
