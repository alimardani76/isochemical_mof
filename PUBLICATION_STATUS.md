# Publication and archival status

## Current scientific state

- Frozen primary analysis: complete.
- Post-freeze H2/H3/H4/H6 analyses: complete and bounded as secondary/post-freeze.
- Publication figure redesign workflow: complete.
- Figure 5 deterministic selection/rendering workflow: complete.
- Current manuscript/SI/bibliography/closure-table sources: synchronized to the 2026-08-17 Overleaf publication-finalization checkpoint on `shayan-final-edit`.
- Main ↔ SI evidence navigation: complete (Figures S1–S6 and Tables S1–S33 are called from the main manuscript).
- Current compiled checkpoint supplied with the synchronized source: main manuscript 24 pages; SI 27 pages.

## Current manuscript title

**Matched MOF Families Reveal Regime-Dependent Pore-Geometry Effects on Adsorption**

## Pull-request state

PR #4 is the publication-hardening and source-synchronization pull request from `shayan-final-edit` to `main`. The previously stale manuscript-source warning has been resolved by synchronizing the current Overleaf source. The branch is ready for coauthor review of the publication-side repository changes; merging remains a coauthor/owner action.

## Items intentionally still open before immutable submission release

1. **Permanent archive / DOI** — after coauthor review, create the exact submission release and, if chosen, archive it in a DOI-minting repository. Record that immutable identifier in manuscript/repository metadata.
2. **Code license** — coauthors must select an explicit license; see `LICENSE_NOTE.md`.
3. **Author declarations** — finalize CRediT, competing interests, and funding/acknowledgements/computing-resource statements; see `manuscript/PASS_F_AUTHOR_CONFIRMATION.md`.
4. **Repository visibility** — the repository is currently public; changing visibility requires repository owner/admin permission.
5. **Publication release bundle** — include the exact manuscript/SI source and PDFs, Figure 1–5 and S1–S6 publication binaries, compact frozen outputs, environment/provenance records, and hashes in the immutable release.
6. **Data Availability version identifier** — the current manuscript contains an interim Git checkpoint. Replace that interim identifier with the final tagged/archived submission release once it exists.

## Frozen boundary

See `ANALYSIS_PROVENANCE.md` and the manuscript/SI methods. The chemistry key, architecture key, pair catalogue, orientation, 10/20/30% criteria, primary endpoint, primary estimator, bootstrap definition, and structural case selection are frozen for the reported paper. Publication editing must not silently change them.
