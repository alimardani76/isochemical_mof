#!/usr/bin/env python3
"""Audit Project 17 Step 3.3 primary endpoint freeze."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = (
    ROOT
    / "Step 3 results"
    / "03_primary_endpoint_freeze"
)

DEFINITION = RESULTS / "primary_endpoint_definition.json"
MANIFEST = RESULTS / "run_manifest.json"


def check(condition, message, failures):
    ok = bool(condition)
    print(("PASS  " if ok else "FAIL  ") + message)
    if not ok:
        failures.append(message)


def main() -> int:
    failures = []

    print("PROJECT 17 - STEP 3.3 PRIMARY ENDPOINT FREEZE AUDIT")

    check(RESULTS.is_dir(), "result folder exists", failures)
    check(DEFINITION.is_file(), "endpoint definition exists", failures)
    check(MANIFEST.is_file(), "manifest exists", failures)

    if failures:
        return 1

    definition = json.loads(DEFINITION.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    primary = definition.get("primary_endpoint", {})
    summary = definition.get("primary_population_summary", {})

    print("\nENDPOINT")
    check(
        primary.get("source") == "methane.csv",
        "primary source is methane.csv",
        failures,
    )
    check(
        primary.get("guest") == "CH4",
        "primary guest is CH4",
        failures,
    )
    check(
        float(primary.get("temperature_K")) == 298.0,
        "primary temperature is 298 K",
        failures,
    )
    check(
        float(primary.get("pressure_bar")) == 65.0,
        "primary pressure is 65 bar",
        failures,
    )
    check(
        primary.get("uptake_column") == "mmol/g",
        "primary uptake basis is mmol/g",
        failures,
    )

    print("\nESTIMAND")
    check(
        definition.get("pair_orientation", {}).get("uses_outcome_values")
        is False,
        "pair orientation is outcome-blind",
        failures,
    )
    check(
        definition.get("primary_pair_effect", {}).get("formula")
        == "q_geometry_high - q_geometry_low",
        "primary signed effect is exact",
        failures,
    )
    check(
        summary.get("estimator") == "median",
        "primary population estimator is median",
        failures,
    )
    check(
        int(summary.get("bootstrap_replicates")) == 10000,
        "bootstrap replicate count is 10,000",
        failures,
    )
    check(
        int(summary.get("bootstrap_seed")) == 17,
        "bootstrap seed is 17",
        failures,
    )

    print("\nFREEZE POLICY")
    check(
        definition.get("frozen_before_outcome_values") is True,
        "endpoint was frozen before outcome values",
        failures,
    )
    check(
        definition.get("endpoint_switching_after_value_access_allowed")
        is False,
        "endpoint switching after value access is forbidden",
        failures,
    )
    check(
        definition.get("pair_membership_modification_allowed") is False,
        "pair membership modification is forbidden",
        failures,
    )
    check(
        definition.get("geometry_threshold_modification_allowed") is False,
        "geometry threshold modification is forbidden",
        failures,
    )
    check(
        manifest.get("outcome_values_read") is False,
        "manifest records no outcome values read",
        failures,
    )
    check(
        manifest.get("primary_endpoint_frozen") is True,
        "manifest records primary endpoint frozen",
        failures,
    )

    print("\nOVERALL RESULT")
    if failures:
        print(
            f"FAIL - {len(failures)} hard check(s) failed. "
            "Do not open adsorption values."
        )
        return 1

    print(
        "PASS - confirmatory Figure 2 endpoint and estimand are frozen."
    )
    print(
        "Next: read only CH4 298 K / 65 bar mmol/g for the frozen pairs "
        "and construct the Figure 2 analysis table."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
