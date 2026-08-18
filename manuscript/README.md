# Manuscript source

This directory contains the publication-facing LaTeX sources for **Matched MOF Families Reveal Regime-Dependent Pore-Geometry Effects on Adsorption**.

## Canonical files

- `main.tex` — main manuscript
- `SI.tex` — Supporting Information
- `Project17_References.bib` — current verified bibliography checkpoint
- `Project17_SI_closure_tables.tex` — generated complete-result closure tables

The closure-table file is generated evidence and should not be manually edited to change numerical results.

## Current checkpoint

The repository copies of `main.tex`, `SI.tex`, `Project17_References.bib`, and `Project17_SI_closure_tables.tex` are synchronized to the current 2026-08-17 Overleaf checkpoint used for the publication-finalization workflow. The manuscript integrates redesigned Figures 1–4, the structural Figure 5, SI Figures S1–S6, the chemistry-facing descriptor table, and complete main-to-SI evidence navigation. The main text calls every SI Figure S1–S6 and Table S1–S33.

The scientific analysis remains frozen. Repository/manuscript editing at this stage is publication communication and packaging, not analytical reopening.

## Figure files

The Overleaf/release bundle places publication PDFs in a sibling `figures/` directory next to `main.tex`/`SI.tex`. The repository treats generated quantitative artwork as reproducible build/release products. Regenerate Figures 1–4 and S1–S6 with `figures/redesign/`; Figure 5 follows the separate structural workflow documented in `figures/source/` and `submission_upgrade/`.

Exact publication-artifact hashes are recorded in `../PUBLICATION_ARTIFACTS.md`.

## Compile

With the current publication figure bundle present:

```bash
pdflatex main.tex
bibtex8 main
pdflatex main.tex
pdflatex main.tex

pdflatex SI.tex
bibtex8 SI
pdflatex SI.tex
pdflatex SI.tex
```

The source contains figure fallbacks so the LaTeX can still be syntax-checked if a binary figure is absent, but that placeholder build is not the publication PDF.

## Release-level items still open

The manuscript source contains no submission TODO placeholder. The remaining items require verified author/owner decisions rather than scientific rewriting:

- final CRediT author contributions;
- competing-interests declaration;
- funding / acknowledgements / computing-resource statement;
- repository license;
- final tagged submission release and, if chosen, DOI-bearing archive;
- replacement of the interim Git checkpoint in the Data Availability statement with the final release identifier at submission.

See `PASS_F_AUTHOR_CONFIRMATION.md` and `../PUBLICATION_STATUS.md`.
