#!/usr/bin/env python3
"""Audit Project 17 Step 3.7 response archetypes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent

CONSISTENCY_DIR = (
    ROOT
    / "Step 3 results"
    / "06_cross_condition_consistency"
)

MATRIX_PATH = CONSISTENCY_DIR / "mmolg_pair_endpoint_matrix.parquet"
META_PATH = CONSISTENCY_DIR / "mmolg_endpoint_metadata.csv"

PAIR_PATH = (
    ROOT
    / "Step 2 results"
    / "03_geometry_pairs"
    / "primary_geometry_pairs.parquet"
)

RESULTS = (
    ROOT
    / "Step 3 results"
    / "07_response_archetypes"
)

DEFINITION_VERSION = "low_high_pressure_response_archetypes_v1"

EXPECTED_FILES = [
    "response_archetypes.parquet",
    "response_archetype_summary.csv",
    "response_archetype_driver_summary.csv",
    "response_archetype_topology_summary.csv",
    "low_high_endpoint_series.csv",
    "response_archetype_exemplars.csv",
    "response_archetype_definition.json",
    "run_manifest.json",
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


def classify(low_majority, high_majority):
    if low_majority and high_majority:
        return "positive_both"
    if (not low_majority) and high_majority:
        return "pressure_activated"
    if low_majority and (not high_majority):
        return "pressure_suppressed"
    return "negative_both"


def main() -> int:
    audit = Audit()

    print("PROJECT 17 - STEP 3.7 RESPONSE ARCHETYPE AUDIT")

    audit.check(
        RESULTS.is_dir(),
        "Step 3.7 result folder exists",
    )

    if not RESULTS.is_dir():
        return 1

    missing = [
        name
        for name in EXPECTED_FILES
        if not (RESULTS / name).is_file()
    ]

    audit.check(
        not missing,
        "all expected Step 3.7 files exist",
    )

    if missing:
        print("Missing:", missing)
        return 1

    for path, message in (
        (MATRIX_PATH, "pair-endpoint matrix source exists"),
        (META_PATH, "endpoint metadata source exists"),
        (PAIR_PATH, "frozen pair source exists"),
    ):
        audit.check(path.is_file(), message)

    if audit.failures:
        return 1

    definition = json.loads(
        (RESULTS / "response_archetype_definition.json")
        .read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (RESULTS / "run_manifest.json")
        .read_text(encoding="utf-8")
    )

    observed = pd.read_parquet(
        RESULTS / "response_archetypes.parquet"
    )
    observed_summary = pd.read_csv(
        RESULTS / "response_archetype_summary.csv"
    )

    matrix = pd.read_parquet(MATRIX_PATH)
    metadata = pd.read_csv(META_PATH)
    pairs = pd.read_parquet(
        PAIR_PATH,
        columns=[
            "architecture_group_id",
            "topology",
            "driver_descriptor",
            "pair_max_fractional_difference",
        ],
    )

    matrix["architecture_group_id"] = matrix[
        "architecture_group_id"
    ].astype("string")
    pairs["architecture_group_id"] = pairs[
        "architecture_group_id"
    ].astype("string")

    metadata["pressure_bar"] = pd.to_numeric(
        metadata["pressure_bar"],
        errors="raise",
    )

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
        manifest.get("raw_outcome_files_read") is False,
        "no raw outcome files were read",
    )
    audit.check(
        manifest.get("low_pressure_endpoint_count") == 9,
        "exactly nine low-pressure endpoints were used",
    )
    audit.check(
        manifest.get("high_pressure_endpoint_count") == 9,
        "exactly nine high-pressure endpoints were used",
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
        manifest.get("primary_endpoint_modified") is False,
        "primary endpoint was not modified",
    )

    print("\nDEFINITION")

    audit.check(
        definition.get("definition_version") == DEFINITION_VERSION,
        "definition version is exact",
    )
    audit.check(
        definition.get("raw_outcome_files_read") is False,
        "definition confirms no raw outcome access",
    )
    audit.check(
        "strictly more than half"
        in definition.get("majority_rule", ""),
        "strict-majority rule is recorded",
    )

    print("\nFULL RECOMPUTATION")

    low_ids = []
    high_ids = []

    for (_source, _guest), block in metadata.groupby(
        ["source", "guest"],
        sort=True,
    ):
        block = block.sort_values("pressure_bar")

        if len(block) != 2:
            raise RuntimeError("endpoint metadata does not form exact pairs")

        low_ids.append(str(block.iloc[0]["endpoint_id"]))
        high_ids.append(str(block.iloc[1]["endpoint_id"]))

    audit.check(
        len(low_ids) == 9 and len(high_ids) == 9,
        "recomputed low/high endpoint sets are 9 + 9",
    )

    primary_meta = metadata.loc[
        metadata["is_primary_endpoint"]
        .astype("boolean")
        .fillna(False)
    ]
    primary_id = str(primary_meta.iloc[0]["endpoint_id"])

    wide = matrix.set_index("architecture_group_id")

    low = wide[low_ids].apply(pd.to_numeric, errors="coerce")
    high = wide[high_ids].apply(pd.to_numeric, errors="coerce")

    low_observed = low.notna().sum(axis=1)
    high_observed = high.notna().sum(axis=1)

    low_positive = low.gt(0).sum(axis=1)
    high_positive = high.gt(0).sum(axis=1)

    low_fraction = low_positive / low_observed
    high_fraction = high_positive / high_observed

    low_majority = low_positive > (low_observed / 2.0)
    high_majority = high_positive > (high_observed / 2.0)

    expected_archetype = [
        classify(bool(lo), bool(hi))
        for lo, hi in zip(low_majority, high_majority)
    ]

    expected = pd.DataFrame(
        {
            "architecture_group_id": wide.index.astype(str),
            "positive_fraction_low_pressure": low_fraction.to_numpy(dtype=float),
            "positive_fraction_high_pressure": high_fraction.to_numpy(dtype=float),
            "activation_score": (
                high_fraction - low_fraction
            ).to_numpy(dtype=float),
            "archetype": expected_archetype,
            "primary_delta_q_mmol_g": pd.to_numeric(
                wide[primary_id],
                errors="coerce",
            ).to_numpy(dtype=float),
        }
    ).sort_values("architecture_group_id").reset_index(drop=True)

    obs = observed.sort_values(
        "architecture_group_id"
    ).reset_index(drop=True)

    audit.check(
        expected["architecture_group_id"].tolist()
        == obs["architecture_group_id"].astype(str).tolist(),
        "pair IDs match exactly",
    )
    audit.check(
        expected["archetype"].tolist()
        == obs["archetype"].astype(str).tolist(),
        "archetype assignment is exact",
    )

    numeric_exact = True

    for column in (
        "positive_fraction_low_pressure",
        "positive_fraction_high_pressure",
        "activation_score",
        "primary_delta_q_mmol_g",
    ):
        if not np.allclose(
            expected[column].to_numpy(dtype=float),
            pd.to_numeric(
                obs[column],
                errors="raise",
            ).to_numpy(dtype=float),
            rtol=0,
            atol=1e-12,
            equal_nan=True,
        ):
            numeric_exact = False
            break

    audit.check(
        numeric_exact,
        "all pressure-fraction / activation fields are exact",
    )

    print("\nARCHETYPE ACCOUNTING")

    expected_counts = (
        expected["archetype"]
        .value_counts()
        .to_dict()
    )

    summary_counts = dict(
        zip(
            observed_summary["archetype"].astype(str),
            pd.to_numeric(
                observed_summary["pairs"],
                errors="raise",
            ).astype(int),
        )
    )

    audit.check(
        all(
            summary_counts.get(name, 0) == count
            for name, count in expected_counts.items()
        ),
        "archetype summary counts are exact",
    )
    audit.check(
        int(observed_summary["pairs"].sum()) == len(expected),
        "archetype summary accounts for every frozen pair",
    )

    print("\nSCIENTIFIC CENSUS")

    print(observed_summary.to_string(index=False))

    print("\nOVERALL RESULT")

    if audit.failures:
        print(
            f"FAIL - {len(audit.failures)} hard check(s) failed. "
            "Do not build Figure 4."
        )
        return 1

    print(
        "PASS - low/high-pressure response archetypes are internally consistent."
    )
    print(
        "Next: use archetype prevalence, activation score, driver dependence, "
        "and topology dependence to design Figure 4."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
