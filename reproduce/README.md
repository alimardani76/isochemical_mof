# Reproducing the historical Project 17 workflow

The handover repository is reorganized under `scripts/` and `results/`, but many historical analysis scripts were originally written against this local layout:

```text
Project17/
├── raw/
├── Step 1 preparation/
├── Step 1 results/
├── Step 2 calculation/
├── Step 2 results/
├── Step 3 production/
├── Step 3 results/
├── figures/
└── test_*.py
```

Do not assume a relocated historical script can be run directly from `scripts/` with identical path resolution. Build a compatibility workspace first, restore ARC-MOF v7 raw data in `workspace/raw/`, then run the original stages and audits from that workspace root.

The post-freeze `submission_upgrade` scripts are newer and use explicit `--project-root` and `--output-dir` arguments, so they are portable once the frozen upstream results exist.

This repository-path compatibility layer fixes organization only; it does not bundle ARC-MOF raw source data or replace stage-specific reconstruction audits.
