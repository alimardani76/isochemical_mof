# Future Overleaf stage: editorial/interpretive corrections

This upload DOES NOT replace the October 14 Overleaf manuscript. The `tex/` snippets are review material only.

1. Insert the regenerated `Figure_6.pdf` into `figures/` and write the H7 Results subsection immediately following the Figure 5 discussion, with its methods before Audit and reproducibility. Use the latest October `main.tex`, never the September `H7/tex/main.tex` (intentionally excluded).
2. The **geometry-only** model in the original H7 prose is actually eight pore descriptors PLUS density. Prefer **global pore-plus-density model** throughout, especially because density dominates the SHAP attribution.
3. Keep random-fold gains and topology-held-out ranking losses visible together. The grouped folds have 4,659, 4,219, 1,051, 653, and 483 test pairs. Arithmetic mean of fold scores is NOT a pair-weighted score or an uncertainty interval.
4. Report 11,065 complete fingerprint pairs as H7 modeling subset; frozen primary analysis still has 11,072 pairs, and primary estimator remains untouched. Do not rewrite abstract primary numbers as H7 numbers.
5. Matminer fingerprint was a proposed method, **not** the actual method. Code uses pymatgen CrystalNN with 19 local summary inputs. Some are constant or mostly unavailable. Metal count is CIF-cell dependent. SHAP is predictive attribution and cannot prove a coordination mechanism.
6. Coordinate with repository owner on private GitHub versus `publicly available` statement, tagged version/DOI, reuse license, and actual target branch. No release permissions were inferred from the archive.
7. Scientific manuscript/SI submission and full LaTeX cross-reference/audit work are pending; do not describe this GitHub H7 upload as final journal-ready material.
