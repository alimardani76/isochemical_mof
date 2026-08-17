# Manuscript source

This directory contains the publication-facing LaTeX sources for **Matched MOF Families Reveal Regime-Dependent Pore-Geometry Effects on Adsorption**.

## Canonical files

- `main.tex` — main manuscript
- `SI.tex` — Supporting Information
- `Project17_References.bib` — verified bibliography
- `Project17_SI_closure_tables.tex` — generated complete-result closure tables

The closure-table file is generated evidence and should not be manually edited to change numerical results.

## Current checkpoint

The sources correspond to the PASS-E writing/integration checkpoint: redesigned Figures 1–4 and S1–S6 are discussed in the text; Figure 5 structural discussion is integrated; the main text references all SI Figures S1–S6 and Tables S1–S33; and the local PASS-E compile audit had zero undefined citations/references and zero overfull boxes.

## Figure files

The Overleaf/release bundle places publication PDFs in a sibling `figures/` directory next to `main.tex`/`SI.tex`. The repository treats generated quantitative artwork as build products. Regenerate it with `figures/redesign/`; Figure 5 follows the separate structural workflow documented in `figures/source/` and `submission_upgrade/`.

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

## Submission-only items still pending

The manuscript intentionally retains placeholders/comments for permanent archive DOI/reviewer access, CRediT, competing interests, and funding/acknowledgements/computing statement. These require verified author information and must not be invented.
