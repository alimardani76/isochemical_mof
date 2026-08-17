# Results directory

This directory contains the canonical frozen outputs used to audit the manuscript.

Primary workflow outputs are under `step1/`, `step2/`, and `step3/`. Post-freeze H2/H3/H4/H6 outputs are canonical under `submission_upgrade/`.

Duplicate output mirrors previously stored beside the scripts under `../submission_upgrade/` have been removed from the publication branch. Scripts stay under `submission_upgrade/`; canonical result tables stay here.

These outputs are evidence, not editable manuscript conveniences. If a scientific definition changes, rerun the upstream workflow into a new analysis location and its audits rather than manually modifying frozen CSV/Parquet/JSON files.
