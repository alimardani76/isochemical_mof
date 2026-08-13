#!/usr/bin/env python3
"""Audit Project 17 Step 2.2 geometry threshold census."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parent

STEP21_DIR = ROOT / "Step 2 results" / "01_geometry_variation"
RESULTS_DIR = ROOT / "Step 2 results" / "02_geometry_threshold_census"

INPUT_PATH = STEP21_DIR / "geometry_variation_groups.parquet"

DEFINITION_VERSION = "geometry_threshold_census_v1"

PORE_DESCRIPTORS = [
    "ASA",
    "AVA",
    "AVAf",
    "POAVA",
    "POAVAf",
    "Di",
    "Df",
    "Dif",
]

THRESHOLDS = [0.05, 0.10, 0.20, 0.30]

EXPECTED_FILES = [
    "geometry_threshold_families.parquet",
    "geometry_threshold_census.csv",
    "geometry_threshold_descriptor_census.csv",
    "max_pore_span_quantiles.csv",
    "geometry_threshold_summary.csv",
    "geometry_threshold_definition.json",
    "run_manifest.json",
]


class Audit:
    def __init__(self):
        self.failures = []

    def check(self, condition: Any, message: str):
        try:
            ok = bool(condition)
        except Exception:
            ok = False
        print(("PASS  " if ok else "FAIL  ") + message)
        if not ok:
            self.failures.append(message)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def threshold_label(value: float) -> str:
    return f"{int(round(value * 100)):02d}pct"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    audit = Audit()

    print("PROJECT 17 - STEP 2.2 GEOMETRY THRESHOLD CENSUS AUDIT")

    audit.check(RESULTS_DIR.is_dir(), "Step 2.2 result folder exists")
    if not RESULTS_DIR.is_dir():
        return 1

    missing = [
        name for name in EXPECTED_FILES
        if not (RESULTS_DIR / name).is_file()
    ]
    audit.check(not missing, "all expected Step 2.2 files exist")
    if missing:
        print("Missing:", missing)
        return 1

    audit.check(INPUT_PATH.is_file(), "Step 2.1 group table exists")
    if not INPUT_PATH.is_file():
        return 1

    manifest = json.loads(
        (RESULTS_DIR / "run_manifest.json").read_text(encoding="utf-8")
    )
    definition = json.loads(
        (RESULTS_DIR / "geometry_threshold_definition.json")
        .read_text(encoding="utf-8")
    )

    source = pd.read_parquet(INPUT_PATH)
    families = pd.read_parquet(
        RESULTS_DIR / "geometry_threshold_families.parquet"
    )
    census = pd.read_csv(
        RESULTS_DIR / "geometry_threshold_census.csv"
    )
    descriptor = pd.read_csv(
        RESULTS_DIR / "geometry_threshold_descriptor_census.csv"
    )

    print("\nPOLICY")
    audit.check(
        manifest.get("completed_successfully") is True,
        "manifest records successful completion",
    )
    audit.check(
        manifest.get("definition_version") == DEFINITION_VERSION,
        "correct threshold-census definition is recorded",
    )
    audit.check(
        manifest.get("final_threshold_selected") is False,
        "no final threshold was selected",
    )
    audit.check(
        manifest.get("pairs_constructed") is False,
        "no framework pairs were constructed",
    )
    audit.check(
        manifest.get("outcome_values_read") is False,
        "no adsorption/process outcomes were read",
    )
    audit.check(
        manifest.get("step21_groups_sha256") == sha256_file(INPUT_PATH),
        "Step 2.1 source hash matches",
    )

    print("\nDEFINITION")
    audit.check(
        definition.get("definition_version") == DEFINITION_VERSION,
        "definition version is exact",
    )
    audit.check(
        definition.get("pore_descriptors") == PORE_DESCRIPTORS,
        "pore descriptor set is exact",
    )
    audit.check(
        definition.get("candidate_thresholds") == THRESHOLDS,
        "candidate thresholds are exactly 5/10/20/30%",
    )
    audit.check(
        definition.get("unit_cell_volume_used") is False,
        "unit-cell volume is excluded from threshold rule",
    )
    audit.check(
        definition.get("density_used") is False,
        "density is excluded from threshold rule",
    )

    print("\nFAMILY POPULATION")
    source_ids = set(source["architecture_group_id"].astype(str))
    family_ids = set(families["architecture_group_id"].astype(str))

    audit.check(
        families["architecture_group_id"].is_unique,
        "family output has one row per architecture group",
    )
    audit.check(
        source_ids == family_ids,
        "family output covers exactly all Step 2.1 architecture groups",
    )

    print("\nTHRESHOLD FLAGS")
    for threshold in THRESHOLDS:
        label = threshold_label(threshold)
        descriptor_flags = []

        for descriptor_name in PORE_DESCRIPTORS:
            span_col = f"{descriptor_name}_fractional_span"
            flag_col = f"{descriptor_name}_ge_{label}"

            expected_flag = families[span_col] >= threshold
            actual_flag = families[flag_col].astype(bool)

            audit.check(
                expected_flag.eq(actual_flag).all(),
                f"{descriptor_name} {int(threshold*100)}% flag is exact",
            )
            descriptor_flags.append(actual_flag.astype(int))

        expected_count = sum(descriptor_flags)
        count_col = f"n_pore_descriptors_ge_{label}"
        any_col = f"any_pore_descriptor_ge_{label}"

        audit.check(
            families[count_col].astype(int).eq(expected_count).all(),
            f"{int(threshold*100)}% descriptor-count field is exact",
        )
        audit.check(
            families[any_col].astype(bool)
            .eq(expected_count >= 1)
            .all(),
            f"{int(threshold*100)}% family eligibility flag is exact",
        )

    print("\nCENSUS ACCOUNTING")
    for threshold in THRESHOLDS:
        label = threshold_label(threshold)
        any_col = f"any_pore_descriptor_ge_{label}"
        eligible = families[any_col].astype(bool)

        row = census.loc[
            pd.to_numeric(census["threshold"], errors="coerce")
            .eq(threshold)
        ]
        audit.check(
            len(row) == 1,
            f"{int(threshold*100)}% census has exactly one row",
        )
        if len(row) == 1:
            row = row.iloc[0]
            audit.check(
                int(row["eligible_families"])
                == int(eligible.sum()),
                f"{int(threshold*100)}% eligible-family count matches",
            )
            audit.check(
                int(row["eligible_frameworks"])
                == int(
                    families.loc[
                        eligible,
                        "framework_count",
                    ].sum()
                ),
                f"{int(threshold*100)}% eligible-framework count matches",
            )

    expected_descriptor_rows = len(THRESHOLDS) * len(PORE_DESCRIPTORS)
    audit.check(
        len(descriptor) == expected_descriptor_rows,
        "descriptor census has every threshold-descriptor combination",
    )

    print("\nSCIENTIFIC CENSUS")
    print(f"  Architecture groups examined: {len(families):,}")
    for threshold in THRESHOLDS:
        label = threshold_label(threshold)
        eligible = families[f"any_pore_descriptor_ge_{label}"].astype(bool)
        print(
            f"  >= {int(threshold*100)}% in any pore descriptor: "
            f"{int(eligible.sum()):,} families; "
            f"{int(families.loc[eligible, 'framework_count'].sum()):,} frameworks"
        )

    print("\nOVERALL RESULT")
    if audit.failures:
        print(
            f"FAIL - {len(audit.failures)} hard check(s) failed. "
            "Do not freeze a geometry threshold yet."
        )
        return 1

    print(
        "PASS - Step 2.2 threshold census is internally consistent."
    )
    print(
        "Next: choose one threshold from the observed support and freeze it "
        "before pair construction."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
