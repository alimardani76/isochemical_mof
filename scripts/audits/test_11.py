#!/usr/bin/env python3
"""Audit Project 17 Step 3.5 secondary outcome atlas."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent

PAIR_PATH = (
    ROOT
    / "Step 2 results"
    / "03_geometry_pairs"
    / "primary_geometry_pairs.parquet"
)

PRIMARY_FREEZE = (
    ROOT
    / "Step 3 results"
    / "03_primary_endpoint_freeze"
    / "primary_endpoint_definition.json"
)

RESULTS = (
    ROOT
    / "Step 3 results"
    / "05_secondary_outcome_atlas"
)

RAW = ROOT / "raw"

DEFINITION_VERSION = "secondary_outcome_atlas_v1"

ADSORPTION_SOURCES = [
    "methane.csv",
    "landfill-CH4.csv",
    "landfill-CO2.csv",
    "methane_purification-CH4.csv",
    "methane_purification-CO2.csv",
    "post_comb_vsa-CO2.csv",
    "post_comb_vsa-N2.csv",
    "pre_comb_4040-CO2.csv",
    "pre_comb_4040-H2.csv",
]

PROCESS_FILE = "overall_process.csv"

EXPECTED_FILES = [
    "secondary_adsorption_pair_effects.parquet",
    "secondary_adsorption_summary.csv",
    "secondary_adsorption_mmolg_summary.csv",
    "secondary_process_pair_effects.parquet",
    "secondary_process_summary.csv",
    "secondary_process_key_metrics.csv",
    "secondary_outcome_atlas_definition.json",
    "run_manifest.json",
]

SUFFIX_PATTERN = re.compile(r"(?i)(?:\.cif|_repeat|_sqe)$")


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


def canonicalize_ids(values: pd.Series) -> pd.Series:
    result = values.astype("string").str.strip()
    result = result.mask(result.eq(""), pd.NA)

    for _ in range(4):
        updated = result.str.replace(SUFFIX_PATTERN, "", regex=True)
        if updated.equals(result):
            break
        result = updated

    result = result.str.strip()
    return result.mask(result.eq(""), pd.NA)


def symmetric_relative_effect(high, low):
    denominator = np.abs(high) + np.abs(low)
    numerator = 2.0 * (high - low)
    return np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator, dtype=float),
        where=denominator != 0,
    )


def main() -> int:
    audit = Audit()

    print("PROJECT 17 - STEP 3.5 SECONDARY OUTCOME ATLAS AUDIT")

    audit.check(RESULTS.is_dir(), "Step 3.5 result folder exists")
    if not RESULTS.is_dir():
        return 1

    missing = [
        name
        for name in EXPECTED_FILES
        if not (RESULTS / name).is_file()
    ]
    audit.check(not missing, "all expected Step 3.5 files exist")
    if missing:
        print("Missing:", missing)
        return 1

    audit.check(PAIR_PATH.is_file(), "frozen pair source exists")
    audit.check(PRIMARY_FREEZE.is_file(), "primary endpoint freeze exists")

    for filename in [*ADSORPTION_SOURCES, PROCESS_FILE]:
        audit.check(
            (RAW / filename).is_file(),
            f"raw source exists: {filename}",
        )

    if audit.failures:
        return 1

    definition = json.loads(
        (
            RESULTS
            / "secondary_outcome_atlas_definition.json"
        ).read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (RESULTS / "run_manifest.json").read_text(encoding="utf-8")
    )
    freeze = json.loads(
        PRIMARY_FREEZE.read_text(encoding="utf-8")
    )

    adsorption_effects = pd.read_parquet(
        RESULTS / "secondary_adsorption_pair_effects.parquet"
    )
    adsorption_summary = pd.read_csv(
        RESULTS / "secondary_adsorption_summary.csv"
    )
    process_effects = pd.read_parquet(
        RESULTS / "secondary_process_pair_effects.parquet"
    )
    process_summary = pd.read_csv(
        RESULTS / "secondary_process_summary.csv"
    )

    pairs = pd.read_parquet(PAIR_PATH)

    print("\nPOLICY")
    audit.check(
        manifest.get("completed_successfully") is True,
        "manifest records successful completion",
    )
    audit.check(
        manifest.get("definition_version") == DEFINITION_VERSION,
        "correct definition version is recorded",
    )
    audit.check(
        manifest.get("secondary_outcomes_read") is True,
        "secondary outcome access is recorded",
    )
    audit.check(
        manifest.get("primary_endpoint_modified") is False,
        "primary endpoint was not modified",
    )
    audit.check(
        manifest.get("pair_membership_modified") is False,
        "pair membership was not modified",
    )
    audit.check(
        manifest.get("pair_orientation_modified") is False,
        "pair orientation was not modified",
    )
    audit.check(
        manifest.get("geometry_threshold_modified") is False,
        "geometry threshold was not modified",
    )
    audit.check(
        manifest.get("no_secondary_endpoint_promoted_to_primary") is True,
        "no secondary endpoint was promoted to primary",
    )

    print("\nDEFINITION")
    audit.check(
        definition.get("definition_version") == DEFINITION_VERSION,
        "definition version is exact",
    )
    audit.check(
        definition.get("analysis_status") == "secondary_exploratory",
        "analysis is explicitly secondary/exploratory",
    )
    audit.check(
        definition.get("frozen_pair_orientation")
        == "driver_low_mof_id -> driver_high_mof_id",
        "frozen pair orientation is exact",
    )
    audit.check(
        definition.get("pair_effect")
        == "value_geometry_high - value_geometry_low",
        "secondary signed effect is exact",
    )
    audit.check(
        definition.get("no_secondary_endpoint_promoted_to_primary") is True,
        "definition preserves primary/secondary hierarchy",
    )

    primary = freeze["primary_endpoint"]
    audit.check(
        primary["source"] == "methane.csv"
        and float(primary["temperature_K"]) == 298.0
        and float(primary["pressure_bar"]) == 65.0
        and primary["uptake_column"] == "mmol/g",
        "frozen primary endpoint remains CH4 298 K / 65 bar mmol/g",
    )

    print("\nPAIR ORIENTATION")
    pair_orientation = pairs[
        [
            "architecture_group_id",
            "driver_low_mof_id",
            "driver_high_mof_id",
        ]
    ].copy()
    pair_orientation["architecture_group_id"] = pair_orientation[
        "architecture_group_id"
    ].astype(str)

    pair_lookup = pair_orientation.set_index(
        "architecture_group_id"
    )

    orientation_ok = True

    for frame in (adsorption_effects, process_effects):
        sample = frame[
            [
                "architecture_group_id",
                "driver_low_mof_id",
                "driver_high_mof_id",
            ]
        ].drop_duplicates()

        sample["architecture_group_id"] = sample[
            "architecture_group_id"
        ].astype(str)

        for row in sample.itertuples(index=False):
            expected = pair_lookup.loc[str(row.architecture_group_id)]
            if (
                str(row.driver_low_mof_id)
                != str(expected["driver_low_mof_id"])
                or str(row.driver_high_mof_id)
                != str(expected["driver_high_mof_id"])
            ):
                orientation_ok = False
                break

        if not orientation_ok:
            break

    audit.check(
        orientation_ok,
        "every secondary row preserves the frozen pair orientation",
    )

    print("\nEFFECT ARITHMETIC")
    effect_arithmetic_ok = True
    relative_ok = True

    for frame in (adsorption_effects, process_effects):
        low = frame["value_geometry_low"].to_numpy(dtype=float)
        high = frame["value_geometry_high"].to_numpy(dtype=float)

        if not np.allclose(
            frame["delta"].to_numpy(dtype=float),
            high - low,
            rtol=0,
            atol=1e-12,
            equal_nan=True,
        ):
            effect_arithmetic_ok = False

        expected_relative = symmetric_relative_effect(high, low)

        if not np.allclose(
            frame["symmetric_relative_effect"].to_numpy(dtype=float),
            expected_relative,
            rtol=0,
            atol=1e-12,
            equal_nan=True,
        ):
            relative_ok = False

    audit.check(
        effect_arithmetic_ok,
        "all secondary signed differences are exact",
    )
    audit.check(
        relative_ok,
        "all secondary symmetric relative effects are exact",
    )

    print("\nSUMMARY RECONSTRUCTION")
    summary_ok = True

    for effects, summary in (
        (adsorption_effects, adsorption_summary),
        (process_effects, process_summary),
    ):
        key_cols = [
            "source",
            "context",
            "guest",
            "temperature_K",
            "pressure_bar",
            "process",
            "metric",
        ]

        for row in summary.itertuples(index=False):
            mask = pd.Series(True, index=effects.index)

            for column in key_cols:
                expected_value = getattr(row, column)

                if pd.isna(expected_value):
                    mask &= effects[column].isna()
                else:
                    mask &= effects[column].astype(str).eq(
                        str(expected_value)
                    )

            block = effects.loc[mask]

            if len(block) != int(row.complete_pairs):
                summary_ok = False
                break

            if len(block):
                delta = block["delta"].to_numpy(dtype=float)

                checks = [
                    np.isclose(
                        float(row.median_delta),
                        float(np.median(delta)),
                        rtol=0,
                        atol=1e-12,
                        equal_nan=True,
                    ),
                    np.isclose(
                        float(row.mean_delta),
                        float(np.mean(delta)),
                        rtol=0,
                        atol=1e-12,
                        equal_nan=True,
                    ),
                    np.isclose(
                        float(row.positive_effect_fraction),
                        float(np.mean(delta > 0)),
                        rtol=0,
                        atol=1e-12,
                        equal_nan=True,
                    ),
                ]

                if not all(checks):
                    summary_ok = False
                    break

        if not summary_ok:
            break

    audit.check(
        summary_ok,
        "secondary summary rows reproduce from pair-level effects",
    )

    print("\nPRIMARY ENDPOINT CONSISTENCY")
    primary_secondary = adsorption_summary.loc[
        adsorption_summary["source"].eq("methane.csv")
        & pd.to_numeric(
            adsorption_summary["temperature_K"],
            errors="coerce",
        ).eq(298.0)
        & pd.to_numeric(
            adsorption_summary["pressure_bar"],
            errors="coerce",
        ).eq(65.0)
        & adsorption_summary["metric"].eq("mmol/g")
    ]

    audit.check(
        len(primary_secondary) == 1,
        "secondary atlas contains exactly one copy of the frozen primary endpoint",
    )
    if len(primary_secondary) == 1:
        audit.check(
            bool(primary_secondary.iloc[0]["is_primary_endpoint"]),
            "the frozen primary endpoint is correctly flagged",
        )

    print("\nSCIENTIFIC CENSUS")
    mmol_summary = adsorption_summary.loc[
        adsorption_summary["metric"].eq("mmol/g")
    ].copy()

    print(
        mmol_summary[
            [
                "context",
                "guest",
                "temperature_K",
                "pressure_bar",
                "complete_pairs",
                "median_delta",
                "positive_effect_fraction",
            ]
        ].to_string(index=False)
    )

    print("\nOVERALL RESULT")
    if audit.failures:
        print(
            f"FAIL - {len(audit.failures)} hard check(s) failed. "
            "Do not build Figure 3."
        )
        return 1

    print(
        "PASS - secondary adsorption/process outcome atlas is internally "
        "consistent and preserves the frozen primary analysis hierarchy."
    )
    print(
        "Next: interpret gas/pressure/process dependence and build Figure 3 "
        "from the audited summary tables."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
