#!/usr/bin/env python3
"""
Project 17 Step 3.3: freeze the confirmatory adsorption endpoint.

This script DOES NOT read adsorption values.

It writes the prespecified endpoint and estimand definition that must be used
before opening outcome values.

Primary endpoint
----------------
Source: methane.csv
Guest: CH4
Temperature: 298 K
Pressure: 65 bar
Uptake basis: mmol/g

Primary orientation
-------------------
Each frozen geometry pair is oriented by its outcome-blind driver descriptor:
the framework with the smaller driver-descriptor value is "geometry-low" and
the framework with the larger value is "geometry-high".

Primary pair-level effect:
    delta_q = q_geometry_high - q_geometry_low   [mmol/g]

Primary summary:
    median(delta_q) across frozen families

Primary uncertainty:
    nonparametric bootstrap of whole frozen families, 10,000 replicates,
    fixed seed 17, percentile 95% confidence interval.

Prespecified supporting metrics at the same endpoint:
    - mean(delta_q)
    - fraction of pairs with delta_q > 0
    - symmetric relative effect:
          2 * (q_high - q_low) / (abs(q_high) + abs(q_low))
      defined as 0 when both uptake values are 0
    - log ratio log(q_high/q_low) only when both values are strictly positive

Sensitivity cohorts:
    - all primary pairs (>=10% geometry contrast)
    - >=20% geometry contrast
    - >=30% geometry contrast

Secondary outcome program remains frozen as secondary:
    - CH4 at 5.8 bar
    - all landfill, methane-purification, post-combustion, and pre-combustion
      gas/pressure conditions
    - v/v and wt% uptake bases
    - heat of adsorption
    - process uptake, working capacity, selectivity, purity, SSP, AFM

No endpoint may be replaced or promoted after outcome inspection.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COVERAGE_DIR = (
    ROOT
    / "Step 3 results"
    / "02_all_outcome_condition_coverage"
)
OUTPUT_DIR = (
    ROOT
    / "Step 3 results"
    / "03_primary_endpoint_freeze"
)

COVERAGE_MANIFEST = COVERAGE_DIR / "run_manifest.json"
COVERAGE_TABLE = COVERAGE_DIR / "outcome_condition_pair_coverage.csv"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_text(text: str, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def main() -> int:
    if not COVERAGE_MANIFEST.is_file():
        raise FileNotFoundError(COVERAGE_MANIFEST)
    if not COVERAGE_TABLE.is_file():
        raise FileNotFoundError(COVERAGE_TABLE)

    coverage_manifest = json.loads(
        COVERAGE_MANIFEST.read_text(encoding="utf-8")
    )

    if coverage_manifest.get("completed_successfully") is not True:
        raise RuntimeError("Step 3.2 is not marked complete")
    if coverage_manifest.get("outcome_values_read") is not False:
        raise RuntimeError(
            "Step 3.2 provenance does not preserve outcome blindness"
        )
    if coverage_manifest.get("endpoint_selected") is not False:
        raise RuntimeError(
            "Step 3.2 unexpectedly reports an endpoint already selected"
        )

    definition = {
        "definition_version": "primary_adsorption_endpoint_v1",
        "frozen_before_outcome_values": True,

        "primary_endpoint": {
            "source": "methane.csv",
            "guest": "CH4",
            "temperature_K": 298.0,
            "pressure_bar": 65.0,
            "uptake_column": "mmol/g",
            "uptake_unit": "mmol/g",
        },

        "scientific_rationale": (
            "high-pressure methane uptake is selected as the confirmatory "
            "geometry-dominant regime; endpoint choice was made before reading "
            "uptake values and not from observed effect size"
        ),

        "pair_orientation": {
            "rule": (
                "use the already-frozen Step 2.3 driver descriptor; orient each "
                "pair from the lower driver-descriptor value to the higher value"
            ),
            "uses_outcome_values": False,
        },

        "primary_pair_effect": {
            "name": "signed_absolute_uptake_difference",
            "formula": "q_geometry_high - q_geometry_low",
            "unit": "mmol/g",
        },

        "primary_population_summary": {
            "estimator": "median",
            "dependence_unit": "one frozen architecture family / primary pair",
            "confidence_interval": "nonparametric percentile bootstrap",
            "bootstrap_replicates": 10000,
            "bootstrap_seed": 17,
            "confidence_level": 0.95,
        },

        "supporting_same_endpoint_metrics": [
            "mean signed absolute uptake difference",
            "fraction of pairs with positive signed uptake difference",
            (
                "signed symmetric relative difference: "
                "2*(q_high-q_low)/(abs(q_high)+abs(q_low)); "
                "0 when both are zero"
            ),
            (
                "signed log uptake ratio log(q_high/q_low), "
                "reported only when both values are strictly positive"
            ),
        ],

        "prespecified_geometry_sensitivity_tiers": [
            {
                "name": "primary",
                "minimum_max_pore_fractional_difference": 0.10,
            },
            {
                "name": "stronger_20pct",
                "minimum_max_pore_fractional_difference": 0.20,
            },
            {
                "name": "stronger_30pct",
                "minimum_max_pore_fractional_difference": 0.30,
            },
        ],

        "secondary_program": {
            "status": "secondary_not_confirmatory",
            "conditions": (
                "all remaining adsorption gas/T/p conditions including CH4 "
                "at 5.8 bar"
            ),
            "uptake_bases": ["v/v", "wt%"],
            "energetic_endpoint": "hoa/kcal/mol",
            "process_endpoints": [
                "mmol/g_uptake",
                "mmol/g_working_capacity",
                "v/v_uptake",
                "v/v_working_capacity",
                "wt%_uptake",
                "wt%_working_capacity",
                "selectivity",
                "purity",
                "ssp",
                "afm",
            ],
        },

        "missing_data_rule": (
            "no imputation; a pair contributes to an endpoint only when both "
            "frozen members have observed values for that endpoint"
        ),

        "endpoint_switching_after_value_access_allowed": False,
        "pair_membership_modification_allowed": False,
        "geometry_threshold_modification_allowed": False,
    }

    manifest = {
        "completed_at_utc": utc_now(),
        "completed_successfully": True,
        "definition_version": definition["definition_version"],
        "outcome_values_read": False,
        "primary_endpoint_frozen": True,
        "primary_source": "methane.csv",
        "primary_temperature_K": 298.0,
        "primary_pressure_bar": 65.0,
        "primary_uptake_column": "mmol/g",
        "pair_membership_modified": False,
        "geometry_threshold_modified": False,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    atomic_write_text(
        json.dumps(definition, indent=2),
        OUTPUT_DIR / "primary_endpoint_definition.json",
    )
    atomic_write_text(
        json.dumps(manifest, indent=2),
        OUTPUT_DIR / "run_manifest.json",
    )

    print("PROJECT 17 - STEP 3.3 PRIMARY ENDPOINT FREEZE")
    print("PASS  outcome values were not read")
    print("PASS  frozen pair membership was not changed")
    print("PASS  geometry threshold was not changed")
    print()
    print("PRIMARY ENDPOINT")
    print("  Guest: CH4")
    print("  Temperature: 298 K")
    print("  Pressure: 65 bar")
    print("  Uptake basis: mmol/g")
    print("  Pair orientation: lower -> higher frozen driver descriptor")
    print("  Primary effect: q_high - q_low")
    print("  Primary summary: median across frozen families")
    print("  CI: family bootstrap, 10,000 replicates, seed 17")
    print()
    print(f"Saved: {OUTPUT_DIR}")
    print(
        "The primary endpoint is now frozen. "
        "Only after this step should uptake values be opened."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
