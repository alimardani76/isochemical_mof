#!/usr/bin/env python3
"""
Project 17 Step 2.3: construct one outcome-blind geometry pair per eligible family.

Frozen inputs
-------------
Step 1.3 chemistry is already frozen.
Step 1.4 architecture is already frozen.
Step 2.2 froze a 10% primary pore-geometry threshold.

Primary pair rule
-----------------
For every family eligible at the 10% threshold:
  1. consider every within-family pair;
  2. compute the symmetric relative difference for each of eight pore descriptors:
         |x_i - x_j| / max(|x_i|, |x_j|)
  3. pair score = largest of the eight descriptor differences;
  4. select the pair with the largest pair score;
  5. tie-break by larger mean difference across all eight descriptors;
  6. final tie-break by lexicographically sorted framework IDs.

Exactly one primary pair is selected per eligible family.

No adsorption/process outcomes are read.
No outcome information enters pair selection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SCRIPT_VERSION = "1.0.0"
DEFINITION_VERSION = "outcome_blind_primary_geometry_pairs_v1"

DEFAULT_ROOT = Path(__file__).resolve().parents[1]

STEP21_DIR_REL = Path("Step 2 results") / "01_geometry_variation"
STEP22_DIR_REL = Path("Step 2 results") / "02_geometry_threshold_census"
OUTPUT_DIR_REL = Path("Step 2 results") / "03_geometry_pairs"

PRIMARY_THRESHOLD = 0.10
SENSITIVITY_THRESHOLDS = [0.20, 0.30]

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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
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


def select_pair(members: pd.DataFrame) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Return one deterministic selected pair plus eight descriptor-level records.
    """
    members = members.sort_values("mof_id").reset_index(drop=True)

    if len(members) < 2:
        raise ValueError("eligible family has fewer than two members")

    ids = members["mof_id"].astype(str).to_numpy()
    values = members[PORE_DESCRIPTORS].to_numpy(dtype=float)

    i_idx, j_idx = np.triu_indices(len(members), k=1)

    left = values[i_idx]
    right = values[j_idx]
    differences = rel_diff_matrix(left, right)

    max_diff = differences.max(axis=1)
    mean_diff = differences.mean(axis=1)

    # np.lexsort uses the last key as primary.
    # Primary: largest max_diff
    # Secondary: largest mean_diff
    # Tertiary/quaternary: smallest sorted indices -> lexicographically smallest IDs
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

    pair_diffs = differences[chosen]
    driver_index = int(np.argmax(pair_diffs))
    driver_descriptor = PORE_DESCRIPTORS[driver_index]

    driver_left_value = float(values[i, driver_index])
    driver_right_value = float(values[j, driver_index])

    if driver_left_value <= driver_right_value:
        low_id = str(ids[i])
        high_id = str(ids[j])
    else:
        low_id = str(ids[j])
        high_id = str(ids[i])

    record: dict[str, Any] = {
        "architecture_group_id": str(
            members["architecture_group_id"].iloc[0]
        ),
        "source_chemistry_group_id": str(
            members["source_chemistry_group_id"].iloc[0]
        ),
        "topology": str(members["topology_clean"].iloc[0]),
        "dimensionality": str(
            members["dimensionality_clean"].iloc[0]
        ),
        "family_size": len(members),
        "n_possible_pairs": int(len(members) * (len(members) - 1) // 2),
        "mof_id_a": str(ids[i]),
        "mof_id_b": str(ids[j]),
        "pair_max_fractional_difference": float(max_diff[chosen]),
        "pair_mean_fractional_difference": float(mean_diff[chosen]),
        "driver_descriptor": driver_descriptor,
        "driver_low_mof_id": low_id,
        "driver_high_mof_id": high_id,
        "primary_10pct_pair": bool(max_diff[chosen] >= PRIMARY_THRESHOLD),
        "sensitivity_20pct_pair": bool(max_diff[chosen] >= 0.20),
        "sensitivity_30pct_pair": bool(max_diff[chosen] >= 0.30),
    }

    descriptor_records: list[dict[str, Any]] = []

    for descriptor_index, descriptor in enumerate(PORE_DESCRIPTORS):
        value_a = float(values[i, descriptor_index])
        value_b = float(values[j, descriptor_index])
        diff = float(pair_diffs[descriptor_index])

        record[f"{descriptor}_a"] = value_a
        record[f"{descriptor}_b"] = value_b
        record[f"{descriptor}_fractional_difference"] = diff

        descriptor_records.append(
            {
                "architecture_group_id": record["architecture_group_id"],
                "mof_id_a": record["mof_id_a"],
                "mof_id_b": record["mof_id_b"],
                "descriptor": descriptor,
                "value_a": value_a,
                "value_b": value_b,
                "fractional_difference": diff,
                "meets_10pct": bool(diff >= 0.10),
                "meets_20pct": bool(diff >= 0.20),
                "meets_30pct": bool(diff >= 0.30),
                "is_driver_descriptor": descriptor == driver_descriptor,
            }
        )

    return record, descriptor_records


def atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_name(path.name + ".tmp")
    frame.to_parquet(temporary, index=False)
    os.replace(temporary, path)


def atomic_write_csv(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_name(path.name + ".tmp")
    frame.to_csv(temporary, index=False)
    os.replace(temporary, path)


def atomic_write_text(text: str, path: Path) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=DEFAULT_ROOT,
    )
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args()
    root = args.project_root.resolve()

    step21_dir = root / STEP21_DIR_REL
    step22_dir = root / STEP22_DIR_REL
    output_dir = root / OUTPUT_DIR_REL

    framework_path = step21_dir / "geometry_variation_frameworks.parquet"
    family_path = step22_dir / "geometry_threshold_families.parquet"
    step21_manifest_path = step21_dir / "run_manifest.json"
    step22_manifest_path = step22_dir / "run_manifest.json"

    for path in (
        framework_path,
        family_path,
        step21_manifest_path,
        step22_manifest_path,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    step21_manifest = json.loads(
        step21_manifest_path.read_text(encoding="utf-8")
    )
    step22_manifest = json.loads(
        step22_manifest_path.read_text(encoding="utf-8")
    )

    for stage, manifest in (
        ("Step 2.1", step21_manifest),
        ("Step 2.2", step22_manifest),
    ):
        if manifest.get("completed_successfully") is not True:
            raise RuntimeError(f"{stage} is not marked complete")
        if manifest.get("outcome_values_read") is not False:
            raise RuntimeError(
                f"{stage} provenance does not confirm outcome blindness"
            )
        if manifest.get("pairs_constructed") is not False:
            raise RuntimeError(
                f"{stage} provenance does not confirm pair blindness"
            )

    frameworks = pd.read_parquet(framework_path)
    families = pd.read_parquet(family_path)

    required_framework = {
        "mof_id",
        "source_chemistry_group_id",
        "architecture_group_id",
        "topology_clean",
        "dimensionality_clean",
        *PORE_DESCRIPTORS,
    }
    missing = required_framework - set(frameworks.columns)
    if missing:
        raise ValueError(
            f"Step 2.1 framework table is missing columns: {sorted(missing)}"
        )

    eligibility_col = "any_pore_descriptor_ge_10pct"
    if eligibility_col not in families.columns:
        raise ValueError(
            f"Step 2.2 family table lacks {eligibility_col}"
        )

    frameworks["mof_id"] = frameworks["mof_id"].astype("string")
    frameworks["architecture_group_id"] = frameworks[
        "architecture_group_id"
    ].astype("string")
    families["architecture_group_id"] = families[
        "architecture_group_id"
    ].astype("string")

    for descriptor in PORE_DESCRIPTORS:
        frameworks[descriptor] = pd.to_numeric(
            frameworks[descriptor],
            errors="raise",
        )

    eligible_ids = set(
        families.loc[
            families[eligibility_col].astype("boolean").fillna(False),
            "architecture_group_id",
        ].astype(str)
    )

    eligible_frameworks = frameworks.loc[
        frameworks["architecture_group_id"]
        .astype(str)
        .isin(eligible_ids)
    ].copy()

    found_ids = set(
        eligible_frameworks["architecture_group_id"].astype(str)
    )
    if found_ids != eligible_ids:
        missing_ids = sorted(eligible_ids - found_ids)
        raise RuntimeError(
            f"eligible families missing framework rows: {missing_ids[:10]}"
        )

    print("Project 17 Step 2.3: constructing outcome-blind geometry pairs")
    print(
        "Policy: one pair per 10%-eligible family; maximize largest pore "
        "difference; tie-break by mean pore difference; no outcomes"
    )
    print(
        f"Eligible families: {len(eligible_ids):,}; "
        f"frameworks available: {len(eligible_frameworks):,}"
    )

    started_at = utc_now()

    pair_rows: list[dict[str, Any]] = []
    descriptor_rows: list[dict[str, Any]] = []

    total_groups = len(eligible_ids)
    for counter, (group_id, members) in enumerate(
        eligible_frameworks.groupby("architecture_group_id", sort=True),
        start=1,
    ):
        pair, details = select_pair(members)
        pair_rows.append(pair)
        descriptor_rows.extend(details)

        if counter % 2000 == 0 or counter == total_groups:
            print(f"processed {counter:,}/{total_groups:,} families")

    pairs = pd.DataFrame(pair_rows)
    pair_descriptors = pd.DataFrame(descriptor_rows)

    if len(pairs) != len(eligible_ids):
        raise RuntimeError(
            "pair count does not equal number of eligible families"
        )
    if not pairs["primary_10pct_pair"].all():
        raise RuntimeError(
            "at least one selected primary pair does not meet the frozen 10% threshold"
        )

    driver_census = (
        pairs.groupby("driver_descriptor")
        .agg(
            selected_pairs=("architecture_group_id", "size"),
            median_driver_pair_difference=(
                "pair_max_fractional_difference",
                "median",
            ),
        )
        .reset_index()
        .sort_values(
            ["selected_pairs", "driver_descriptor"],
            ascending=[False, True],
        )
        .reset_index(drop=True)
    )

    summary = pd.DataFrame(
        [
            ("primary_threshold", PRIMARY_THRESHOLD),
            ("eligible_families", len(eligible_ids)),
            ("available_frameworks", len(eligible_frameworks)),
            ("selected_primary_pairs", len(pairs)),
            (
                "unique_frameworks_in_primary_pairs",
                len(
                    set(pairs["mof_id_a"].astype(str))
                    | set(pairs["mof_id_b"].astype(str))
                ),
            ),
            (
                "selected_pairs_meeting_20pct",
                int(pairs["sensitivity_20pct_pair"].sum()),
            ),
            (
                "selected_pairs_meeting_30pct",
                int(pairs["sensitivity_30pct_pair"].sum()),
            ),
            (
                "median_selected_pair_max_fractional_difference",
                float(pairs["pair_max_fractional_difference"].median()),
            ),
            (
                "median_selected_pair_mean_fractional_difference",
                float(pairs["pair_mean_fractional_difference"].median()),
            ),
            (
                "median_family_size",
                float(pairs["family_size"].median()),
            ),
            (
                "families_with_more_than_two_members",
                int(pairs["family_size"].gt(2).sum()),
            ),
        ],
        columns=["metric", "value"],
    )

    definition = {
        "definition_version": DEFINITION_VERSION,
        "primary_threshold": PRIMARY_THRESHOLD,
        "sensitivity_thresholds": SENSITIVITY_THRESHOLDS,
        "pore_descriptors": PORE_DESCRIPTORS,
        "eligible_family_rule": (
            "Step 2.2 family has at least one pore descriptor with "
            "within-family fractional span >= 10%"
        ),
        "pair_difference": (
            "abs(x_i - x_j) / max(abs(x_i), abs(x_j)); zero when both are zero"
        ),
        "pair_score": (
            "maximum fractional difference across the eight pore descriptors"
        ),
        "tie_break_1": (
            "larger mean fractional difference across the eight pore descriptors"
        ),
        "tie_break_2": (
            "lexicographically smallest sorted pair of mof_id values"
        ),
        "pairs_per_family": 1,
        "unit_cell_volume_used": False,
        "density_used": False,
        "outcome_values_read": False,
        "pair_selection_outcome_blind": True,
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    atomic_write_parquet(
        pairs.sort_values("architecture_group_id").reset_index(drop=True),
        output_dir / "primary_geometry_pairs.parquet",
    )
    atomic_write_parquet(
        pair_descriptors.sort_values(
            ["architecture_group_id", "descriptor"]
        ).reset_index(drop=True),
        output_dir / "primary_pair_descriptor_differences.parquet",
    )
    atomic_write_csv(
        driver_census,
        output_dir / "primary_pair_driver_census.csv",
    )
    atomic_write_csv(
        summary,
        output_dir / "primary_geometry_pair_summary.csv",
    )
    atomic_write_text(
        json.dumps(definition, indent=2),
        output_dir / "primary_geometry_pair_definition.json",
    )

    manifest = {
        "script": Path(__file__).name,
        "script_version": SCRIPT_VERSION,
        "definition_version": DEFINITION_VERSION,
        "started_at_utc": started_at,
        "completed_at_utc": utc_now(),
        "step21_frameworks_sha256": sha256_file(framework_path),
        "step22_families_sha256": sha256_file(family_path),
        "source_step21_definition_version": step21_manifest.get(
            "definition_version"
        ),
        "source_step22_definition_version": step22_manifest.get(
            "definition_version"
        ),
        "primary_threshold": PRIMARY_THRESHOLD,
        "sensitivity_thresholds": SENSITIVITY_THRESHOLDS,
        "one_pair_per_family": True,
        "unit_cell_volume_used": False,
        "density_used": False,
        "outcome_values_read": False,
        "pair_selection_outcome_blind": True,
        "raw_directory_modified": False,
        "completed_successfully": True,
        "output_directory": str(OUTPUT_DIR_REL),
    }

    atomic_write_text(
        json.dumps(manifest, indent=2),
        output_dir / "run_manifest.json",
    )

    print()
    print(summary.to_string(index=False))

    print()
    print("Driver descriptor census:")
    print(driver_census.to_string(index=False))

    print()
    print(f"Saved results: {output_dir}")
    print(
        "Stop here and run py .\\test_07.py. "
        "Do not read adsorption/process outcomes until the pair audit passes."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
