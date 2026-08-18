# Publication status

## Current state

The scientific analysis for **Matched MOF Families Reveal Regime-Dependent Pore-Geometry Effects on Adsorption** is frozen. The current coauthor-review manuscript checkpoint is the **Materials Horizons G2 candidate (2026-08-18)**.

Completed journal-facing work:

- PASS B-final — forensic reference audit and bounded self-citation integration; 40-entry bibliography, all entries used;
- PASS G1 — Communication-level editorial compression while preserving the central chemistry and robustness discussion;
- PASS G2 — 156-word New Concepts statement, Materials Horizons cover letter, title decision, submission checklist, positioning memo, and graphical-abstract/TOC brief.

The journal-facing package is under `manuscript/` and `manuscript/submission/`.

## Scientific contract — frozen

Do not silently change the recorded-chemistry/architecture definitions, frozen pair catalogue, pair orientation, 10% primary criterion, 20%/30% stronger tiers, CH4 298 K / 65 bar primary endpoint, family-median estimator, 10,000-replicate bootstrap with seed 17, or the bounded post-freeze analyses.

## Coauthor review / PR #4

PR #4 is the publication-hardening and manuscript-synchronization PR into `main`. The G2 candidate is intended for Hosein's review before merge. `main` should remain unchanged until that review is complete.

## Items still requiring author/owner confirmation

1. final CRediT roles;
2. competing-interests statement;
3. funding / acknowledgements / computing resources;
4. repository code license;
5. final tagged submission release;
6. DOI-bearing archive if the authors choose one;
7. final Data Availability release/version identifier;
8. optional repository-visibility change (owner/admin only).

These are publication declarations/release decisions, not reasons to reopen the frozen analysis.

## Important Data Availability note

The current manuscript still cites an **interim Git checkpoint** in its Data Availability section. That identifier is acceptable for coauthor review but is **not the final journal-release identifier**. PASS H must replace it with the final tagged/released version after coauthor approval and verify every repository/data URL.

## Next gate

After coauthor review and the author declarations above, run **PASS H** against one common Overleaf/GitHub source:

- final native main/SI/bibliography/closure sources;
- exact Figure 1–5 and S1–S6 bundle;
- zero undefined references/citations;
- numerical-anchor and caption checks;
- DOI/link verification;
- final RSC/Materials Horizons template/portal check;
- immutable release/DOI update if chosen;
- final source/PDF ZIP and SHA-256 manifest.

No repository version should be described as the final journal release until that gate is complete.
