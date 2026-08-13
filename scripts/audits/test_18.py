#!/usr/bin/env python3
"""Audit Project 17 final SI reporting closure."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent

SOURCE_DIR = (
    ROOT
    / "Step 3 results"
    / "05_secondary_outcome_atlas"
)

ADS_PATH = SOURCE_DIR / "secondary_adsorption_summary.csv"
PROCESS_PATH = SOURCE_DIR / "secondary_process_summary.csv"

RESULT_DIR = (
    ROOT
    / "Step 3 results"
    / "10_manuscript_closure"
)

OUTPUT_TEX = ROOT / "Project17_SI_closure_tables.tex"

EXPECTED = [
    RESULT_DIR / "closure_reporting_manifest.json",
    RESULT_DIR / "secondary_adsorption_reporting_inventory.csv",
    RESULT_DIR / "secondary_process_reporting_inventory.csv",
    OUTPUT_TEX,
]


class Audit:
    def __init__(self):
        self.failures = []

    def check(self, condition, message):
        try:
            ok = bool(condition)
        except Exception:
            ok = False

        print(("PASS  " if ok else "FAIL  ") + message)

        if not ok:
            self.failures.append(message)


def main() -> int:
    audit = Audit()

    print("PROJECT 17 - FINAL SI REPORTING AUDIT")

    for path in (ADS_PATH, PROCESS_PATH):
        audit.check(path.is_file(), f"source exists: {path.name}")

    for path in EXPECTED:
        audit.check(path.is_file(), f"closure output exists: {path.name}")

    if audit.failures:
        return 1

    ads_source = pd.read_csv(ADS_PATH)
    process_source = pd.read_csv(PROCESS_PATH)

    ads_inv = pd.read_csv(
        RESULT_DIR / "secondary_adsorption_reporting_inventory.csv"
    )
    process_inv = pd.read_csv(
        RESULT_DIR / "secondary_process_reporting_inventory.csv"
    )

    manifest = json.loads(
        (RESULT_DIR / "closure_reporting_manifest.json")
        .read_text(encoding="utf-8")
    )

    tex = OUTPUT_TEX.read_text(encoding="utf-8")

    print("\nPOLICY")

    audit.check(
        manifest.get("completed_successfully") is True,
        "closure manifest records successful completion",
    )
    audit.check(
        manifest.get("new_scientific_analysis_performed") is False,
        "closure performed reporting only",
    )

    print("\nROW COMPLETENESS")

    audit.check(
        len(ads_source) == len(ads_inv),
        "every audited adsorption summary row is reported",
    )
    audit.check(
        len(process_source) == len(process_inv),
        "every audited process summary row is reported",
    )
    audit.check(
        manifest.get("adsorption_source_rows") == len(ads_source)
        == manifest.get("adsorption_reported_rows"),
        "adsorption row counts are exact in manifest",
    )
    audit.check(
        manifest.get("process_source_rows") == len(process_source)
        == manifest.get("process_reported_rows"),
        "process row counts are exact in manifest",
    )

    print("\nMETRIC COMPLETENESS")

    source_ads_metric_col = next(
        (
            c for c in ads_source.columns
            if c.lower() in {
                "metric",
                "outcome_metric",
                "response_metric",
                "quantity",
            }
        ),
        None,
    )
    source_process_metric_col = next(
        (
            c for c in process_source.columns
            if c.lower() in {
                "metric",
                "outcome_metric",
                "response_metric",
                "quantity",
            }
        ),
        None,
    )

    audit.check(
        source_ads_metric_col is not None,
        "adsorption source metric column found",
    )
    audit.check(
        source_process_metric_col is not None,
        "process source metric column found",
    )

    if source_ads_metric_col is not None:
        source_metrics = set(
            ads_source[source_ads_metric_col].dropna().astype(str)
        )
        reported_metrics = set(
            ads_inv["metric"].dropna().astype(str)
        )
        audit.check(
            source_metrics == reported_metrics,
            "all adsorption metric classes are represented",
        )

    if source_process_metric_col is not None:
        source_metrics = set(
            process_source[source_process_metric_col].dropna().astype(str)
        )
        reported_metrics = set(
            process_inv["metric"].dropna().astype(str)
        )
        audit.check(
            source_metrics == reported_metrics,
            "all process metric classes are represented",
        )

    print("\nLATEX CONTENT")

    for label in ["tab:S23", "tab:S24", "tab:S25"]:
        audit.check(label in tex, f"generated SI contains {label}")

    audit.check(
        "ARC--MOF release v7" in tex,
        "exact ARC-MOF release is stated",
    )
    audit.check(
        "16802743" in tex,
        "Zenodo record is stated",
    )
    audit.check(
        "no endpoint is selected" in tex,
        "complete-table caption states non-selection",
    )

    print("\nOVERALL RESULT")

    if audit.failures:
        print(
            f"FAIL - {len(audit.failures)} closure check(s) failed. "
            "Do not call the SI complete."
        )
        return 1

    print(
        "PASS - all audited Step 3.5 secondary summary rows are exposed "
        "in the SI closure tables."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
