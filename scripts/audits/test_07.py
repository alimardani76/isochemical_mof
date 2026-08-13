#!/usr/bin/env python3
"""Audit Project 17 Step 2.3 outcome-blind primary geometry pairs."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent

STEP21_DIR = ROOT / "Step 2 results" / "01_geometry_variation"
STEP22_DIR = ROOT / "Step 2 results" / "02_geometry_threshold_census"
RESULTS_DIR = ROOT / "Step 2 results" / "03_geometry_pairs"

FRAMEWORK_PATH = STEP21_DIR / "geometry_variation_frameworks.parquet"
FAMILY_PATH = STEP22_DIR / "geometry_threshold_families.parquet"

DEFINITION_VERSION = "outcome_blind_primary_geometry_pairs_v1"
PRIMARY_THRESHOLD = 0.10

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

EXPECTED_FILES = [
    "primary_geometry_pairs.parquet",
    "primary_pair_descriptor_differences.parquet",
    "primary_pair_driver_census.csv",
    "primary_geometry_pair_summary.csv",
    "primary_geometry_pair_definition.json",
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
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def rel_diff_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    denominator = np.maximum(np.abs(a), np.abs(b))
    numerator = np.abs(a - b)
    return np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator, dtype=float),
        where=denominator != 0,
    )


def recompute_best_pair(members: pd.DataFrame):
    members = members.sort_values("mof_id").reset_index(drop=True)
    ids = members["mof_id"].astype(str).to_numpy()
    values = members[PORE_DESCRIPTORS].to_numpy(dtype=float)

    i_idx, j_idx = np.triu_indices(len(members), k=1)
    differences = rel_diff_matrix(values[i_idx], values[j_idx])
    max_diff = differences.max(axis=1)
    mean_diff = differences.mean(axis=1)

    order = np.lexsort(
        (
            j_idx,
            i_idx,
            -mean_diff,
            -max_diff,
        )
    )
    chosen = int(order[0])
    i = int(i_idx[chosen])
    j = int(j_idx[chosen])

    driver_index = int(np.argmax(differences[chosen]))

    return {
        "mof_id_a": str(ids[i]),
        "mof_id_b": str(ids[j]),
        "max_diff": float(max_diff[chosen]),
        "mean_diff": float(mean_diff[chosen]),
        "driver_descriptor": PORE_DESCRIPTORS[driver_index],
        "differences": differences[chosen],
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    audit = Audit()
    print("PROJECT 17 - STEP 2.3 PRIMARY GEOMETRY PAIR AUDIT")

    audit.check(RESULTS_DIR.is_dir(), "Step 2.3 result folder exists")
    if not RESULTS_DIR.is_dir():
        return 1

    missing = [
        name for name in EXPECTED_FILES
        if not (RESULTS_DIR / name).is_file()
    ]
    audit.check(not missing, "all expected Step 2.3 files exist")
    if missing:
        print("Missing:", missing)
        return 1

    for path in (FRAMEWORK_PATH, FAMILY_PATH):
        audit.check(path.is_file(), f"source exists: {path.name}")
    if not FRAMEWORK_PATH.is_file() or not FAMILY_PATH.is_file():
        return 1

    manifest = json.loads(
        (RESULTS_DIR / "run_manifest.json").read_text(encoding="utf-8")
    )
    definition = json.loads(
        (RESULTS_DIR / "primary_geometry_pair_definition.json")
        .read_text(encoding="utf-8")
    )

    frameworks = pd.read_parquet(FRAMEWORK_PATH)
    families = pd.read_parquet(FAMILY_PATH)
    pairs = pd.read_parquet(
        RESULTS_DIR / "primary_geometry_pairs.parquet"
    )
    details = pd.read_parquet(
        RESULTS_DIR / "primary_pair_descriptor_differences.parquet"
    )
    summary = pd.read_csv(
        RESULTS_DIR / "primary_geometry_pair_summary.csv"
    )

    frameworks["mof_id"] = frameworks["mof_id"].astype("string")
    frameworks["architecture_group_id"] = frameworks[
        "architecture_group_id"
    ].astype("string")
    families["architecture_group_id"] = families[
        "architecture_group_id"
    ].astype("string")
    pairs["architecture_group_id"] = pairs[
        "architecture_group_id"
    ].astype("string")

    print("\nPOLICY")
    audit.check(
        manifest.get("completed_successfully") is True,
        "manifest records successful completion",
    )
    audit.check(
        manifest.get("definition_version") == DEFINITION_VERSION,
        "correct pair definition is recorded",
    )
    audit.check(
        manifest.get("primary_threshold") == PRIMARY_THRESHOLD,
        "frozen primary threshold is 10%",
    )
    audit.check(
        manifest.get("one_pair_per_family") is True,
        "exactly one pair per family is the declared rule",
    )
    audit.check(
        manifest.get("unit_cell_volume_used") is False,
        "unit-cell volume was not used for pair selection",
    )
    audit.check(
        manifest.get("density_used") is False,
        "density was not used for pair selection",
    )
    audit.check(
        manifest.get("outcome_values_read") is False,
        "no adsorption/process outcomes were read",
    )
    audit.check(
        manifest.get("pair_selection_outcome_blind") is True,
        "pair selection is explicitly outcome-blind",
    )
    audit.check(
        manifest.get("step21_frameworks_sha256") == sha256_file(FRAMEWORK_PATH),
        "Step 2.1 framework source hash matches",
    )
    audit.check(
        manifest.get("step22_families_sha256") == sha256_file(FAMILY_PATH),
        "Step 2.2 family source hash matches",
    )

    print("\nDEFINITION")
    audit.check(
        definition.get("definition_version") == DEFINITION_VERSION,
        "definition version is exact",
    )
    audit.check(
        definition.get("pore_descriptors") == PORE_DESCRIPTORS,
        "pair descriptor set is exact",
    )
    audit.check(
        definition.get("pairs_per_family") == 1,
        "definition specifies one pair per family",
    )
    audit.check(
        definition.get("outcome_values_read") is False,
        "definition preserves outcome blindness",
    )

    eligible_ids = set(
        families.loc[
            families["any_pore_descriptor_ge_10pct"]
            .astype("boolean")
            .fillna(False),
            "architecture_group_id",
        ].astype(str)
    )
    pair_ids = set(pairs["architecture_group_id"].astype(str))

    print("\nPAIR POPULATION")
    audit.check(
        pairs["architecture_group_id"].is_unique,
        "pair table has one row per architecture family",
    )
    audit.check(
        pair_ids == eligible_ids,
        "pair table covers exactly all 10%-eligible families",
    )
    audit.check(
        pairs["mof_id_a"].astype(str).ne(
            pairs["mof_id_b"].astype(str)
        ).all(),
        "every pair contains two different frameworks",
    )
    audit.check(
        pairs["primary_10pct_pair"]
        .astype("boolean")
        .fillna(False)
        .all(),
        "every selected primary pair meets the frozen 10% threshold",
    )

    framework_group = dict(
        zip(
            frameworks["mof_id"].astype(str),
            frameworks["architecture_group_id"].astype(str),
        )
    )

    endpoints_valid = True
    for row in pairs.itertuples():
        if (
            framework_group.get(str(row.mof_id_a))
            != str(row.architecture_group_id)
            or framework_group.get(str(row.mof_id_b))
            != str(row.architecture_group_id)
        ):
            endpoints_valid = False
            break

    audit.check(
        endpoints_valid,
        "both pair members belong to their declared architecture family",
    )

    print("\nPAIR OPTIMALITY")
    # Full deterministic recomputation. This remains modest because families are
    # disjoint and the primary cohort contains only ~26k frameworks.
    pair_by_group = pairs.set_index("architecture_group_id")
    optimal = True
    score_exact = True
    driver_exact = True
    descriptor_exact = True

    detail_lookup = details.set_index(
        ["architecture_group_id", "descriptor"]
    )

    eligible_frameworks = frameworks.loc[
        frameworks["architecture_group_id"]
        .astype(str)
        .isin(eligible_ids)
    ]

    total = len(eligible_ids)
    for counter, (group_id, members) in enumerate(
        eligible_frameworks.groupby("architecture_group_id", sort=True),
        start=1,
    ):
        expected = recompute_best_pair(members)
        observed = pair_by_group.loc[str(group_id)]

        if (
            str(observed["mof_id_a"]) != expected["mof_id_a"]
            or str(observed["mof_id_b"]) != expected["mof_id_b"]
        ):
            optimal = False

        if not (
            np.isclose(
                float(observed["pair_max_fractional_difference"]),
                expected["max_diff"],
                rtol=0,
                atol=1e-12,
            )
            and np.isclose(
                float(observed["pair_mean_fractional_difference"]),
                expected["mean_diff"],
                rtol=0,
                atol=1e-12,
            )
        ):
            score_exact = False

        if str(observed["driver_descriptor"]) != expected["driver_descriptor"]:
            driver_exact = False

        for index, descriptor in enumerate(PORE_DESCRIPTORS):
            detail = detail_lookup.loc[(str(group_id), descriptor)]
            if not np.isclose(
                float(detail["fractional_difference"]),
                float(expected["differences"][index]),
                rtol=0,
                atol=1e-12,
            ):
                descriptor_exact = False
                break

        if counter % 3000 == 0 or counter == total:
            print(f"audited {counter:,}/{total:,} families")

    audit.check(
        optimal,
        "every selected pair is the deterministic maximum-separation pair",
    )
    audit.check(
        score_exact,
        "pair max/mean geometry scores are exact",
    )
    audit.check(
        driver_exact,
        "driver descriptor is exact",
    )
    audit.check(
        descriptor_exact,
        "all descriptor-level pair differences are exact",
    )

    print("\nDETAIL TABLE")
    audit.check(
        len(details) == len(pairs) * len(PORE_DESCRIPTORS),
        "descriptor table has exactly eight rows per selected pair",
    )
    counts = details.groupby("architecture_group_id").size()
    audit.check(
        counts.eq(len(PORE_DESCRIPTORS)).all(),
        "every selected pair has all eight descriptor records",
    )

    print("\nSENSITIVITY TIERS")
    expected_20 = int(
        families[
            "any_pore_descriptor_ge_20pct"
        ].astype("boolean").fillna(False).sum()
    )
    expected_30 = int(
        families[
            "any_pore_descriptor_ge_30pct"
        ].astype("boolean").fillna(False).sum()
    )
    observed_20 = int(
        pairs["sensitivity_20pct_pair"]
        .astype("boolean")
        .fillna(False)
        .sum()
    )
    observed_30 = int(
        pairs["sensitivity_30pct_pair"]
        .astype("boolean")
        .fillna(False)
        .sum()
    )

    audit.check(
        observed_20 == expected_20,
        "20% selected-pair sensitivity count matches the frozen family census",
    )
    audit.check(
        observed_30 == expected_30,
        "30% selected-pair sensitivity count matches the frozen family census",
    )

    print("\nSUMMARY ACCOUNTING")
    summary_dict = dict(
        zip(summary["metric"].astype(str), summary["value"])
    )

    expected_summary = {
        "eligible_families": len(eligible_ids),
        "selected_primary_pairs": len(pairs),
        "unique_frameworks_in_primary_pairs": len(
            set(pairs["mof_id_a"].astype(str))
            | set(pairs["mof_id_b"].astype(str))
        ),
        "selected_pairs_meeting_20pct": observed_20,
        "selected_pairs_meeting_30pct": observed_30,
    }

    for metric, expected_value in expected_summary.items():
        audit.check(
            int(float(summary_dict[metric])) == int(expected_value),
            f"summary metric {metric} matches",
        )

    print("\nSCIENTIFIC CENSUS")
    print(f"  10%-eligible families: {len(eligible_ids):,}")
    print(f"  Frozen primary geometry pairs: {len(pairs):,}")
    print(
        f"  Unique frameworks used in primary pairs: "
        f"{len(set(pairs['mof_id_a'].astype(str)) | set(pairs['mof_id_b'].astype(str))):,}"
    )
    print(f"  Pairs also meeting >=20%: {observed_20:,}")
    print(f"  Pairs also meeting >=30%: {observed_30:,}")
    print(
        f"  Median selected max pore difference: "
        f"{float(pairs['pair_max_fractional_difference'].median()):.4f}"
    )
    print(
        f"  Median selected mean pore difference: "
        f"{float(pairs['pair_mean_fractional_difference'].median()):.4f}"
    )

    print("\nOVERALL RESULT")
    if audit.failures:
        print(
            f"FAIL - {len(audit.failures)} hard check(s) failed. "
            "Do not connect pairs to adsorption outcomes."
        )
        return 1

    print(
        "PASS - primary geometry pair catalogue is frozen and internally consistent."
    )
    print(
        "Next: only after this pass, connect the frozen pair IDs to adsorption/process "
        "tables without changing chemistry, architecture, threshold, or pair selection."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
