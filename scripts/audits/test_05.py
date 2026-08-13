#!/usr/bin/env python3
"""Audit Project 17 Step 2.1 geometry-variation census."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parent
STAGE14_DIR = ROOT / "Step 1 results" / "04_same_architecture"
RESULTS_DIR = ROOT / "Step 2 results" / "01_geometry_variation"

INPUT_PATH = STAGE14_DIR / "same_architecture_frameworks.parquet"

DEFINITION_VERSION = "within_family_geometry_variation_v1"

GEOMETRY_COLUMNS = [
    "UC_volume",
    "Density",
    "ASA",
    "AVA",
    "AVAf",
    "POAVA",
    "POAVAf",
    "Di",
    "Df",
    "Dif",
]

EXPECTED_FILES = [
    "geometry_variation_frameworks.parquet",
    "geometry_variation_groups.parquet",
    "geometry_descriptor_census.csv",
    "geometry_variation_summary.csv",
    "geometry_variation_definition.json",
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


def b(series: pd.Series) -> pd.Series:
    return series.astype("boolean").fillna(False)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    audit = Audit()
    print("PROJECT 17 - STEP 2.1 GEOMETRY VARIATION AUDIT")

    audit.check(RESULTS_DIR.is_dir(), "Step 2.1 result folder exists")
    if not RESULTS_DIR.is_dir():
        return 1

    missing = [
        name for name in EXPECTED_FILES
        if not (RESULTS_DIR / name).is_file()
    ]
    audit.check(not missing, "all expected Step 2.1 files exist")
    if missing:
        print("Missing:", missing)
        return 1

    audit.check(INPUT_PATH.is_file(), "Stage 1.4 framework table exists")
    if not INPUT_PATH.is_file():
        return 1

    manifest = json.loads(
        (RESULTS_DIR / "run_manifest.json").read_text(encoding="utf-8")
    )
    definition = json.loads(
        (RESULTS_DIR / "geometry_variation_definition.json")
        .read_text(encoding="utf-8")
    )

    stage14 = pd.read_parquet(INPUT_PATH)
    frameworks = pd.read_parquet(
        RESULTS_DIR / "geometry_variation_frameworks.parquet"
    )
    groups = pd.read_parquet(
        RESULTS_DIR / "geometry_variation_groups.parquet"
    )
    descriptor_census = pd.read_csv(
        RESULTS_DIR / "geometry_descriptor_census.csv"
    )
    summary = pd.read_csv(
        RESULTS_DIR / "geometry_variation_summary.csv"
    )

    print("\nPOLICY")
    audit.check(
        manifest.get("completed_successfully") is True,
        "manifest records successful completion",
    )
    audit.check(
        manifest.get("definition_version") == DEFINITION_VERSION,
        "correct geometry-variation definition is recorded",
    )
    audit.check(
        manifest.get("stage14_validated_only") is True,
        "only validated Stage 1.4 families were used",
    )
    audit.check(
        manifest.get("scientific_contrast_threshold_defined") is False,
        "no scientific contrast threshold was defined",
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
        manifest.get("stage14_frameworks_sha256") == sha256_file(INPUT_PATH),
        "Stage 1.4 source hash matches",
    )

    print("\nDEFINITION")
    audit.check(
        definition.get("definition_version") == DEFINITION_VERSION,
        "definition version is exact",
    )
    audit.check(
        definition.get("geometry_descriptors") == GEOMETRY_COLUMNS,
        "geometry descriptor list is exact",
    )
    audit.check(
        definition.get("scientific_threshold_defined") is False,
        "definition is descriptive rather than thresholded",
    )
    audit.check(
        definition.get("framework_pairs_constructed") is False,
        "definition preserves pair blindness",
    )

    expected_validated = stage14.loc[
        b(stage14["same_architecture_family"])
    ].copy()
    expected_complete = expected_validated.loc[
        b(expected_validated["geometry_descriptors_complete"])
    ].copy()

    expected_ids = set(expected_complete["mof_id"].astype(str))
    observed_ids = set(frameworks["mof_id"].astype(str))

    print("\nFRAMEWORK POPULATION")
    audit.check(
        frameworks["mof_id"].is_unique
        and frameworks["mof_id"].notna().all(),
        "framework output has one row per geometry-complete validated framework",
    )
    audit.check(
        observed_ids == expected_ids,
        "framework output exactly matches geometry-complete validated Stage 1.4 frameworks",
    )

    expected_group_ids = set(
        expected_complete["architecture_group_id"].astype(str)
    )
    observed_group_ids = set(
        groups["architecture_group_id"].astype(str)
    )

    print("\nGROUP POPULATION")
    audit.check(
        expected_group_ids == observed_group_ids,
        "group output covers every geometry-complete validated architecture group",
    )

    expected_group_sizes = (
        expected_complete.groupby("architecture_group_id")
        .size()
        .to_dict()
    )
    observed_group_sizes = dict(
        zip(
            groups["architecture_group_id"].astype(str),
            groups["framework_count"].astype(int),
        )
    )
    expected_group_sizes = {
        str(k): int(v) for k, v in expected_group_sizes.items()
    }

    audit.check(
        expected_group_sizes == observed_group_sizes,
        "group framework counts are exact",
    )

    print("\nDESCRIPTOR CENSUS")
    audit.check(
        set(descriptor_census["descriptor"].astype(str))
        == set(GEOMETRY_COLUMNS),
        "descriptor census contains exactly the ten geometry descriptors",
    )

    for column in GEOMETRY_COLUMNS:
        required = {
            f"{column}_min",
            f"{column}_max",
            f"{column}_absolute_span",
            f"{column}_fractional_span",
            f"{column}_varies",
        }
        audit.check(
            required.issubset(groups.columns),
            f"{column} variation fields exist",
        )

    print("\nSUMMARY")
    summary_dict = dict(
        zip(summary["metric"].astype(str), summary["value"])
    )

    core_expected = {
        "validated_stage14_frameworks": len(expected_validated),
        "geometry_complete_validated_frameworks": len(expected_complete),
        "validated_architecture_groups_with_geometry": len(expected_group_ids),
        "groups_with_geometry_variation": int(
            b(groups["has_geometry_variation"]).sum()
        ),
        "groups_without_geometry_variation": int(
            (~b(groups["has_geometry_variation"])).sum()
        ),
        "frameworks_in_geometry_varying_groups": int(
            groups.loc[
                b(groups["has_geometry_variation"]),
                "framework_count",
            ].sum()
        ),
    }

    for metric, expected_value in core_expected.items():
        actual = int(float(summary_dict[metric]))
        audit.check(
            actual == int(expected_value),
            f"summary metric {metric} matches",
        )

    print("\nSCIENTIFIC CENSUS")
    varying = b(groups["has_geometry_variation"])
    print(f"  Geometry-complete validated frameworks: {len(frameworks):,}")
    print(f"  Architecture groups with geometry data: {len(groups):,}")
    print(f"  Groups with material geometry variation: {int(varying.sum()):,}")
    print(
        f"  Frameworks in geometry-varying groups: "
        f"{int(groups.loc[varying, 'framework_count'].sum()):,}"
    )

    print("\nOVERALL RESULT")
    if audit.failures:
        print(
            f"FAIL - {len(audit.failures)} hard check(s) failed. "
            "Do not define geometry contrasts yet."
        )
        return 1

    print(
        "PASS - Step 2.1 geometry-variation census is internally consistent."
    )
    print(
        "Next: use these empirical distributions to choose a simple meaningful "
        "geometry-contrast rule."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
