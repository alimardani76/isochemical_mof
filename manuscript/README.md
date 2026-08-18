# Manuscript source

This directory contains the publication-facing source for **Matched MOF Families Reveal Regime-Dependent Pore-Geometry Effects on Adsorption**.

## Current checkpoint

As of **2026-08-18**, this directory is synchronized to the **Materials Horizons G2 candidate**.

- `main.tex` — PASS G1 Communication-level editorial compression, PASS B-final literature/self-citation integration, and the 156-word New Concepts paragraph added in PASS G2.
- `SI.tex` — audited Supporting Information with the full S1–S33 table set, Figures S1–S6, post-freeze robustness sections, structural-case ledger, limitations, and audit trail.
- `Project17_References.bib` — final PASS B reference checkpoint: 40 entries, all used in the main manuscript, with no duplicate DOI/title entries in the local forensic audit.
- `Project17_SI_closure_tables.tex` — generated closure evidence; scientific values are not manually edited.
- `submission/` — Materials Horizons-facing New Concepts statement, cover letter, title audit, submission checklist, positioning memo, and graphical-abstract/TOC brief.

## Scientific contract

The journal-facing passes do **not** alter the frozen scientific design. Pair membership/orientation, chemistry and architecture keys, the 10/20/30% geometry criteria, the CH4 298 K / 65 bar primary endpoint, family-median estimand, 10,000-replicate bootstrap with seed 17, post-freeze H2/H3/H6 definitions, and Figure 5 structural cases remain frozen.

## Compile

The working sources use:

```latex
\bibliography{Project17_References}
```

and the SI includes:

```latex
\input{Project17_SI_closure_tables.tex}
```

The complete publication figure bundle is maintained separately from generated build products. For final submission, compile the native LaTeX sources with the exact publication figures and include the resulting manuscript/SI PDFs in the submission bundle.

## Remaining pre-submission items

These require author/owner confirmation or the final PASS H release process:

1. CRediT / author-contribution statement;
2. competing-interests declaration;
3. funding / acknowledgements / computing-resource statement;
4. repository license;
5. final tagged submission release and DOI-bearing archive if approved;
6. replacement of the interim Git identifier in Data Availability with the final released version;
7. final Materials Horizons template/portal proof and submission ZIP.

Do not invent or infer author attestations to close these items.
