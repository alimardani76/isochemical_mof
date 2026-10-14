# Paper 17 — Figure 6 (revised 2026-10-14)

Run `python figure/make_figure6.py` from the H7 directory, or run the script by its full path from any working directory. `numpy`, `pandas`, and `matplotlib` are sufficient. Only fixed results in `../code/results/{model_comparison,cv_fold_metrics,shap_feature_importance}.csv` are used. The original H7 model fitting is not repeated.

Panel A is a **schematic**, not a crystallographically faithful pair or mechanism; metal centers M and different-colored neighbors represent abstract local environments. Panel B shows mean held-out Spearman correlation, with error bars equal to the **sample standard deviation across five test folds**, not confidence intervals. Panel C reports mean absolute held-out SHAP values of the combined model under topology-held-out validation; local metal count is unit-cell dependent. Panel D plots each fold's `combined − geometry` Spearman difference (circles), together with the unweighted mean across folds (diamonds). The two validation strategies have different test sets; the same fold numbers do not denote identical structures.

The original H7 scientific results are unchanged; the figure is vector PDF/SVG plus PNG at 400 dpi and adopts the Paper 17 blue/green graphical palette and Arial-compatible sans-serif font settings. `Figure_6.pdf` is the intended Overleaf asset.

**Label precision (2026-10-14 recheck):** The global-only model has eight pore-geometry descriptors **and crystal density**, not geometry alone. Panel B is therefore labeled "Pores + density". Panel D uses the same explicit baseline. Panel C colors are descriptive: blue means global descriptors, green means a local input.
