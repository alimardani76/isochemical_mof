#!/usr/bin/env python3
"""Audit Project 17 Step 1.4: simple same-architecture baseline."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parent
REGISTRY_DIR = ROOT / "Step 1 results" / "01_framework_registry"
STAGE13_DIR = ROOT / "Step 1 results" / "03_same_chemistry"
RESULTS_DIR = ROOT / "Step 1 results" / "04_same_architecture"

REGISTRY_PATH = REGISTRY_DIR / "framework_registry.parquet"
STAGE13_PATH = STAGE13_DIR / "same_chemistry_frameworks.parquet"

DEFINITION_VERSION = "recorded_topology_dimensionality_architecture_v1"

EXPECTED_FILES = [
    "same_architecture_frameworks.parquet",
    "same_architecture_groups.parquet",
    "same_architecture_exclusions.parquet",
    "chemistry_family_architecture_census.parquet",
    "same_architecture_summary.csv",
    "same_architecture_status_counts.csv",
    "same_architecture_definition.json",
    "run_manifest.json",
]

MISSING = {"", "nan", "none", "null", "na", "n/a", "unknown", "?", "<na>"}


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


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def clean_label(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return None if text.lower() in MISSING else text


def architecture_id(chemistry_group_id: str, topology: str, dimensionality: str) -> str:
    payload = "\n".join(
        [
            DEFINITION_VERSION,
            str(chemistry_group_id),
            str(topology),
            str(dimensionality),
        ]
    )
    return "arch1_" + sha256_text(payload)


def b(series: pd.Series) -> pd.Series:
    return series.astype("boolean").fillna(False)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    audit = Audit()

    print("PROJECT 17 - SAME ARCHITECTURE AUDIT")

    audit.check(RESULTS_DIR.is_dir(), "Stage 1.4 result folder exists")
    if not RESULTS_DIR.is_dir():
        return 1

    missing_files = [
        name for name in EXPECTED_FILES
        if not (RESULTS_DIR / name).is_file()
    ]
    audit.check(not missing_files, "all expected Stage 1.4 files exist")
    if missing_files:
        print("Missing:", missing_files)
        return 1

    audit.check(REGISTRY_PATH.is_file(), "Stage 1.1 registry exists")
    audit.check(STAGE13_PATH.is_file(), "Stage 1.3 chemistry table exists")
    if not REGISTRY_PATH.is_file() or not STAGE13_PATH.is_file():
        return 1

    manifest = json.loads(
        (RESULTS_DIR / "run_manifest.json").read_text(encoding="utf-8")
    )
    definition = json.loads(
        (RESULTS_DIR / "same_architecture_definition.json").read_text(encoding="utf-8")
    )

    frameworks = pd.read_parquet(
        RESULTS_DIR / "same_architecture_frameworks.parquet"
    )
    groups = pd.read_parquet(
        RESULTS_DIR / "same_architecture_groups.parquet"
    )
    exclusions = pd.read_parquet(
        RESULTS_DIR / "same_architecture_exclusions.parquet"
    )
    census = pd.read_parquet(
        RESULTS_DIR / "chemistry_family_architecture_census.parquet"
    )
    summary = pd.read_csv(
        RESULTS_DIR / "same_architecture_summary.csv"
    )
    status = pd.read_csv(
        RESULTS_DIR / "same_architecture_status_counts.csv"
    )

    stage13 = pd.read_parquet(
        STAGE13_PATH,
        columns=[
            "mof_id",
            "chemistry_group_id",
            "multi_member_candidate_family",
        ],
    )
    registry = pd.read_parquet(
        REGISTRY_PATH,
        columns=["mof_id", "topology", "dimensionality"],
    )

    for df in (frameworks, stage13, registry):
        df["mof_id"] = df["mof_id"].astype("string")

    print("\nPOLICY")
    audit.check(
        manifest.get("completed_successfully") is True,
        "Stage 1.4 manifest records successful completion",
    )
    audit.check(
        manifest.get("definition_version") == DEFINITION_VERSION,
        "correct simple architecture definition is recorded",
    )
    audit.check(
        manifest.get("chemistry_frozen_from_stage13") is True,
        "Stage 1.3 chemistry is frozen",
    )
    audit.check(
        manifest.get("topology_used_in_architecture_key") is True,
        "topology is used in the architecture key",
    )
    audit.check(
        manifest.get("dimensionality_used_in_architecture_key") is True,
        "dimensionality is used in the architecture key",
    )
    audit.check(
        manifest.get("geometry_used_in_architecture_key") is False,
        "geometry is excluded from the architecture key",
    )
    audit.check(
        manifest.get("cif_archive_read") is False,
        "CIF archive was not read",
    )
    audit.check(
        manifest.get("bond_connectivity_inferred") is False,
        "no bonding was inferred",
    )
    audit.check(
        manifest.get("crystalnn_used") is False,
        "CrystalNN was not used",
    )
    audit.check(
        manifest.get("outcome_values_read") is False,
        "no adsorption/process outcomes were read",
    )
    audit.check(
        manifest.get("pairs_constructed") is False,
        "no framework pairs were constructed",
    )
    audit.check(
        manifest.get("registry_sha256") == sha256_file(REGISTRY_PATH),
        "registry source hash matches",
    )
    audit.check(
        manifest.get("same_chemistry_frameworks_sha256") == sha256_file(STAGE13_PATH),
        "Stage 1.3 source hash matches",
    )

    print("\nDEFINITION")
    audit.check(
        definition.get("definition_version") == DEFINITION_VERSION,
        "definition version is exact",
    )
    audit.check(
        definition.get("architecture_key")
        == [
            "Stage 1.3 chemistry_group_id",
            "recorded topology",
            "recorded dimensionality",
        ],
        "architecture key is chemistry + topology + dimensionality only",
    )

    print("\nTARGET SET")
    expected = stage13.loc[
        stage13["multi_member_candidate_family"]
        .astype("boolean")
        .fillna(False)
    ].merge(
        registry,
        on="mof_id",
        how="left",
        validate="one_to_one",
    ).rename(
        columns={"chemistry_group_id": "source_chemistry_group_id"}
    )

    expected_ids = set(expected["mof_id"].astype(str))
    observed_ids = set(frameworks["mof_id"].astype(str))

    audit.check(
        frameworks["mof_id"].is_unique and frameworks["mof_id"].notna().all(),
        "one Stage 1.4 row exists per framework",
    )
    audit.check(
        observed_ids == expected_ids,
        "Stage 1.4 covers exactly all Stage 1.3 multi-member chemistry candidates",
    )

    expected["topology_clean"] = (
        expected["topology"].map(clean_label).astype("string")
    )
    expected["dimensionality_clean"] = (
        expected["dimensionality"].map(clean_label).astype("string")
    )
    expected["complete"] = (
        expected["topology_clean"].notna()
        & expected["dimensionality_clean"].notna()
    )

    expected["expected_group_id"] = pd.Series(
        pd.NA, index=expected.index, dtype="string"
    )

    good = expected["complete"]
    expected.loc[good, "expected_group_id"] = [
        architecture_id(c, t, d)
        for c, t, d in zip(
            expected.loc[good, "source_chemistry_group_id"].astype(str),
            expected.loc[good, "topology_clean"].astype(str),
            expected.loc[good, "dimensionality_clean"].astype(str),
        )
    ]

    expected_sizes = expected.loc[good, "expected_group_id"].value_counts()
    expected["expected_group_size"] = (
        expected["expected_group_id"]
        .map(expected_sizes)
        .astype("Int64")
    )
    expected["expected_valid"] = (
        expected["complete"]
        & expected["expected_group_size"].ge(2).fillna(False)
    )

    observed = frameworks.set_index("mof_id")
    expected = expected.set_index("mof_id")

    print("\nGROUPING")
    audit.check(
        observed["source_chemistry_group_id"].astype("string")
        .eq(expected["source_chemistry_group_id"].astype("string"))
        .all(),
        "Stage 1.3 chemistry group IDs are preserved exactly",
    )
    audit.check(
        observed["topology_clean"].astype("string").fillna("<M>")
        .eq(expected["topology_clean"].astype("string").fillna("<M>"))
        .all(),
        "topology labels are cleaned correctly",
    )
    audit.check(
        observed["dimensionality_clean"].astype("string").fillna("<M>")
        .eq(expected["dimensionality_clean"].astype("string").fillna("<M>"))
        .all(),
        "dimensionality labels are cleaned correctly",
    )
    audit.check(
        observed["architecture_group_id"].astype("string").fillna("<M>")
        .eq(expected["expected_group_id"].astype("string").fillna("<M>"))
        .all(),
        "architecture group IDs are exact chemistry+topology+dimensionality hashes",
    )
    audit.check(
        observed["architecture_group_size"].astype("Int64").fillna(-1)
        .eq(expected["expected_group_size"].astype("Int64").fillna(-1))
        .all(),
        "architecture group sizes are exact",
    )
    audit.check(
        b(observed["same_architecture_family"])
        .eq(expected["expected_valid"])
        .all(),
        "validated same-architecture membership is exact",
    )

    print("\nGROUP TABLES")
    expected_valid = expected.loc[expected["expected_valid"]]
    expected_group_sizes = (
        expected_valid["expected_group_id"]
        .astype("string")
        .value_counts()
    )
    observed_group_sizes = (
        groups.assign(
            architecture_group_id=groups["architecture_group_id"].astype("string")
        )
        .set_index("architecture_group_id")["architecture_group_size"]
    )

    expected_group_sizes.index = expected_group_sizes.index.astype(str)
    observed_group_sizes.index = observed_group_sizes.index.astype(str)

    audit.check(
        set(expected_group_sizes.index) == set(observed_group_sizes.index),
        "validated group IDs match exactly",
    )
    audit.check(
        all(
            int(expected_group_sizes.loc[g])
            == int(observed_group_sizes.loc[g])
            for g in set(expected_group_sizes.index)
        ),
        "validated group sizes match exactly",
    )

    expected_exclusions = set(
        expected.loc[~expected["expected_valid"]].index.astype(str)
    )
    observed_exclusions = set(exclusions["mof_id"].astype(str))
    audit.check(
        expected_exclusions == observed_exclusions,
        "exclusion ledger is exact",
    )

    print("\nSUMMARY")
    summary_dict = dict(
        zip(summary["metric"].astype(str), summary["value"])
    )

    core_expected = {
        "source_multi_member_chemistry_families":
            int(frameworks["source_chemistry_group_id"].nunique()),
        "target_frameworks": len(frameworks),
        "frameworks_with_complete_architecture_labels":
            int(b(frameworks["architecture_label_complete"]).sum()),
        "validated_same_architecture_frameworks":
            int(b(frameworks["same_architecture_family"]).sum()),
        "validated_same_architecture_groups":
            len(groups),
        "frameworks_with_missing_topology":
            int(frameworks["topology_clean"].isna().sum()),
        "frameworks_with_missing_dimensionality":
            int(frameworks["dimensionality_clean"].isna().sum()),
    }

    for metric, expected_value in core_expected.items():
        actual = int(float(summary_dict[metric]))
        audit.check(
            actual == expected_value,
            f"summary metric {metric} matches",
        )

    status_expected = (
        frameworks.groupby("architecture_status")
        .size()
        .rename("frameworks")
        .sort_index()
    )
    status_observed = (
        status.assign(
            frameworks=pd.to_numeric(status["frameworks"], errors="coerce")
        )
        .set_index("architecture_status")["frameworks"]
        .sort_index()
    )
    audit.check(
        status_expected.astype(int).equals(status_observed.astype(int)),
        "status counts match exactly",
    )

    print("\nSCIENTIFIC CENSUS")
    geometry_groups = b(groups["geometry_contrast_candidate_family"])
    print(
        f"  Chemistry families entering Stage 1.4: "
        f"{frameworks['source_chemistry_group_id'].nunique():,}"
    )
    print(f"  Frameworks entering Stage 1.4: {len(frameworks):,}")
    print(
        f"  Validated same-architecture groups: {len(groups):,}"
    )
    print(
        f"  Frameworks in validated groups: "
        f"{int(b(frameworks['same_architecture_family']).sum()):,}"
    )
    print(
        f"  Same-architecture groups retaining geometry variation: "
        f"{int(geometry_groups.sum()):,}"
    )
    print(
        f"  Frameworks in those geometry-contrast groups: "
        f"{int(groups.loc[geometry_groups, 'architecture_group_size'].sum()):,}"
    )
    print(
        f"  Chemistry families split into multiple validated architectures: "
        f"{int(census['validated_architecture_groups'].gt(1).sum()):,}"
    )

    print("\nOVERALL RESULT")
    if audit.failures:
        print(
            f"FAIL - {len(audit.failures)} hard check(s) failed. "
            "Do not construct pairs."
        )
        return 1

    print(
        "PASS - simple Stage 1.4 same-architecture baseline is internally consistent."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
