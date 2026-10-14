# Paper 17 — private repository snapshot verification and H7 integration

**Review date:** 2026-10-14  
**Inspected repository artifact:** `isochemical_mof-main.zip` (not a Git history, not the remote `submission-upgrade` branch).  
**New H7 scientific outputs:** preserved unchanged from coauthor handover; Figure 6 is the redesigned, data-driven version supplied with the earlier preparation.

## Verified observations

- The ZIP integrity check passed. The archive holds **296 files** (~264.32 MB uncompressed). Its single top folder is `isochemical_mof-main/`. GitHub's conventional archive naming indicates a `main` branch snapshot; the archive contains no `.git` branch refs or commit metadata, so its exact remote commit is not independently established.
- The repo has `submission_upgrade/` with scripts `15`–`19`, the shared plotting style, and an H4 structural method note. **No `submission_upgrade/H7/` folder exists in this snapshot.**
- The repo stores the three frozen H7 input tables in the exact expected locations. Their SHA-256 values precisely match the input hashes recorded by `H7/code/results/run_manifest.json`:

| Frozen input | Repository location | SHA-256 | H7 agreement |
|---|---|---|---|
| pairs | `results/step2/03_geometry_pairs/primary_geometry_pairs.parquet` | `83d4d6f4d937b6d6c57cdea43121748450d27f1af76016d0232ce8e3f006bb75` | Exact |
| effects | `results/step3/04_primary_ch4_analysis/primary_ch4_pair_effects.parquet` | `8a4b24e3c4a741f7935efc229c67646b96ba9e7d2c8d0cb5bc840c6869e0403f` | Exact |
| geometry | `results/step2/01_geometry_variation/geometry_variation_frameworks.parquet` | `49032c10f3039c9a35b3f2f78f0f0d12e616dd9e8b75415a66e21d963d0f99ca` | Exact |

This verifies **input-byte identity**, not an independent reproduction of the original CIF neighbor calculation or LightGBM fitting. The ARC-MOF raw archive is not in the repo ZIP, which matches the repository's published raw-data policy. H7 Figure 6 can be rebuilt from the stored output CSVs without it.

## Figure 6 scientific boundary

The model comparison remains an exploratory, post-freeze check over 11,065 usable pairs (11,072 frozen pairs remain unchanged). Adding local features raises mean Spearman from 0.8639 to 0.8666 on random 5-fold CV but decreases it from 0.7490 to 0.7372 on topology-held-out 5-fold CV. The figure correctly emphasizes lack of improvement in topology transfer, not a verified local-coordination mechanism.

Figure 6A is explicitly schematic and not a CIF-derived structural rendering. The H7 parquets, predictions, input/result manifests, analysis script, and Figure 6 data source are retained.

## Overleaf-to-repository comparison

The repository `manuscript/` documents a **2026-08-18 Materials Horizons G2 candidate**, while the user supplied `Ver_3(1).zip` as the **2026-10-14 Overleaf source**. Their differences: `SI.tex`, `Project17_References.bib`, and `Project17_SI_closure_tables.tex` are byte-for-byte **identical**; `main.tex` is **not** byte-for-byte identical. Its changes are limited to a few Figure 5 cross-reference wording replacements and the insertion of `\newpage` (plus a blank line) immediately before the bibliography commands. The new H7 inserts are in neither latest source. **Use the October Overleaf version for any later manuscript merge; do not copy the older GitHub main.tex or the September H7 handover main.tex into Overleaf.**

## Safe manual browser upload

1. In your signed-in browser, open the private GitHub repository. Confirm you have permission to upload.
2. **Inspect the branch menu.** Hosein requested `submission-upgrade`, but this ZIP contains **main**. The existence/current state of `submission-upgrade` is not verified by this attachment. If it exists and is the approved integration branch, select it. If it is absent, ask Hosein which branch to use rather than silently uploading to `main`.
3. Open `submission_upgrade/` on the chosen branch. Ensure no conflicting H7 folder already exists.
4. Extract `P17_H7_REPO_VERIFIED_MANUAL_UPLOAD.zip` locally. Inside `submission_upgrade/`, locate the extracted folder `H7/`.
5. Click **Add file → Upload files** in the repository's `submission_upgrade/` folder, then drag in the **`H7` folder**. This preserves `submission_upgrade/H7/code`, `/figure`, `/tex` and `/audit`. Do not drag the *entire outer `submission_upgrade/` folder* while already inside that directory (which would incorrectly create a nested `submission_upgrade/submission_upgrade/H7/`).
6. Confirm the proposed file paths and selected branch in GitHub's file list before the browser commit. The upload includes only the new H7 tree, not root `README.md`, existing frozen inputs, or the current manuscript.
7. Verify the result in GitHub by visiting `submission_upgrade/H7/README.md`, `submission_upgrade/H7/figure/Figure_6.pdf`, `submission_upgrade/H7/code/results/run_manifest.json` and all expected CSV/parquet files on the chosen branch.

**No repository changes or upload have been performed by the assistant.** The ZIP archive alone cannot confirm upload permissions, commit ID, protected-branch rules, or the remote `submission-upgrade` branch's current state.

## Existing-document updates (later, after confirming destination branch)

These are **suggestions, not modified files in the upload**. The existing `submission_upgrade/README.md` lists H2/H3/H4/H6 and `19_submission_sanity_check.py`; consider adding a one-line index entry for `H7/`. The top-level README and reproduction map should eventually mention H7 and Figure 6, but changing shared root documentation now without examining the real destination branch risks overwriting someone else's work.

**Submission gate:** The uploaded `main.tex` says that scripts and outputs are `publicly available at` the GitHub URL, but you have confirmed that the live repository is private. A private repo cannot substantiate that public-access claim. Arrange an authorized public/tagged archive or correct the availability statement before submitting; do not switch visibility without coauthor/owner approval. Other outstanding author declarations, final figure bundle, source/figure version synchronization, repository license, and release identifier are listed in the repo's `PUBLICATION_STATUS.md` and submission checklist.

## Items not established by this snapshot

- Live state or existence of the `submission-upgrade` branch, its changes since `main`, branch protections, or PR history.
- Independent end-to-end rerun of all H7 CIF feature extraction and LightGBM models.
- Public accessibility of the repo or final journal-submission readiness.
- Completed Overleaf integration.
