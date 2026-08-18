# Figure workflows

The repository separates **scientific source data**, **publication plotting code**, and **generated artwork** so that visual redesign cannot silently change the frozen analysis.

## Quantitative figures: Figures 1–4 and S1–S6

Use `redesign/`:

```bash
python -m pip install -r figures/redesign/requirements.txt
python figures/redesign/validate_redesign_values.py
python figures/redesign/run_all.py
```

The current manuscript uses the approved redesigned visual grammar for Figures 1–4 and S1–S6.

## Structural Figure 5

- deterministic pair selection: `../submission_upgrade/17_select_structural_case_studies.py`
- canonical selected cases/CIFs: `../results/submission_upgrade/H4_structural_cases/`
- renderer: `source/12_make_figure5_structural_assets.py`
- method: `../submission_upgrade/H4_STRUCTURAL_FIGURE_METHOD.md`
- publication master record: `source/Figure_5_FINAL_ARTIFACTS.md`

LOW/HIGH is geometry ordering, not adsorption-performance ordering. Insets provide crystallographic context only and are not adsorption-site or measured-bottleneck assignments.

## Earlier artwork

`archive/legacy_pre_redesign/` retains earlier committed artwork for provenance. It is not the current submission artwork. Exact current publication hashes are in `../PUBLICATION_ARTIFACTS.md`.
