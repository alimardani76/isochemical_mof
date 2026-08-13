#!/usr/bin/env python3
"""
Project 17 Step 2.1: measure within-family geometry variation.

Input:
    Step 1 results/04_same_architecture/same_architecture_frameworks.parquet

Scope:
    - use only validated same-chemistry + same-architecture families
    - use only measured geometry descriptors
    - quantify within-family variation
    - do NOT define a scientific contrast threshold
    - do NOT construct framework pairs
    - do NOT read adsorption/process outcomes

This is a descriptive census that tells us how geometry varies before we decide
what should count as a meaningful geometry contrast.
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

import pandas as pd


SCRIPT_VERSION = "1.0.0"
DEFINITION_VERSION = "within_family_geometry_variation_v1"

DEFAULT_ROOT = Path(__file__).resolve().parents[1]

STAGE14_DIR_REL = Path("Step 1 results") / "04_same_architecture"
OUTPUT_DIR_REL = Path("Step 2 results") / "01_geometry_variation"

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

NUMERICAL_TOLERANCE = {
    "UC_volume": 1e-8,
    "Density": 1e-10,
    "ASA": 1e-8,
    "AVA": 1e-10,
    "AVAf": 1e-12,
    "POAVA": 1e-10,
    "POAVAf": 1e-12,
    "Di": 1e-10,
    "Df": 1e-10,
    "Dif": 1e-10,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def material_span(minimum: float, maximum: float, column: str) -> bool:
    scale = max(1.0, abs(float(minimum)), abs(float(maximum)))
    tolerance = max(NUMERICAL_TOLERANCE[column], 1e-12 * scale)
    return float(maximum) - float(minimum) > tolerance


def fractional_span(minimum: float, maximum: float) -> float:
    """
    Scale-free descriptive spread.
    For the nonnegative geometry descriptors in this dataset it lies in [0, 1].
    """
    minimum = float(minimum)
    maximum = float(maximum)
    denominator = max(abs(minimum), abs(maximum))
    if denominator == 0:
        return 0.0
    return (maximum - minimum) / denominator


def atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    frame.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def atomic_write_csv(frame: pd.DataFrame, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    frame.to_csv(tmp, index=False)
    os.replace(tmp, path)


def atomic_write_text(text: str, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


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

    stage14_dir = root / STAGE14_DIR_REL
    input_path = stage14_dir / "same_architecture_frameworks.parquet"
    manifest_path = stage14_dir / "run_manifest.json"
    output_dir = root / OUTPUT_DIR_REL

    for path in (input_path, manifest_path):
        if not path.is_file():
            raise FileNotFoundError(path)

    stage14_manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )
    if stage14_manifest.get("completed_successfully") is not True:
        raise RuntimeError("Stage 1.4 is not marked complete")
    if stage14_manifest.get("outcome_values_read") is not False:
        raise RuntimeError("Stage 1.4 provenance does not confirm outcome blindness")
    if stage14_manifest.get("pairs_constructed") is not False:
        raise RuntimeError("Stage 1.4 provenance does not confirm pair blindness")

    frame = pd.read_parquet(input_path)

    required = {
        "mof_id",
        "source_chemistry_group_id",
        "architecture_group_id",
        "same_architecture_family",
        "geometry_descriptors_complete",
        "topology_clean",
        "dimensionality_clean",
        *GEOMETRY_COLUMNS,
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Stage 1.4 table is missing columns: {sorted(missing)}")

    frame["mof_id"] = frame["mof_id"].astype("string")

    validated = frame.loc[
        frame["same_architecture_family"]
        .astype("boolean")
        .fillna(False)
    ].copy()

    geometry_complete = validated.loc[
        validated["geometry_descriptors_complete"]
        .astype("boolean")
        .fillna(False)
    ].copy()

    if geometry_complete.empty:
        raise RuntimeError("No validated frameworks have complete geometry")

    for column in GEOMETRY_COLUMNS:
        geometry_complete[column] = pd.to_numeric(
            geometry_complete[column],
            errors="raise",
        )

    print("Project 17 Step 2.1: measuring within-family geometry variation")
    print(
        "Policy: validated Stage 1.4 families only; descriptive geometry only; "
        "no contrast threshold, no pairs, no outcomes"
    )
    print(
        f"Validated frameworks: {len(validated):,}; "
        f"geometry-complete frameworks: {len(geometry_complete):,}"
    )

    started_at = utc_now()

    group_rows: list[dict[str, Any]] = []

    for group_id, members in geometry_complete.groupby(
        "architecture_group_id",
        sort=True,
    ):
        row: dict[str, Any] = {
            "architecture_group_id": str(group_id),
            "source_chemistry_group_id": str(
                members["source_chemistry_group_id"].iloc[0]
            ),
            "topology": str(members["topology_clean"].iloc[0]),
            "dimensionality": str(
                members["dimensionality_clean"].iloc[0]
            ),
            "framework_count": len(members),
        }

        varying_descriptors = 0
        fractional_spans = []

        for column in GEOMETRY_COLUMNS:
            values = members[column].dropna()
            minimum = float(values.min())
            maximum = float(values.max())
            median = float(values.median())
            mean = float(values.mean())
            absolute_span = maximum - minimum
            fraction = fractional_span(minimum, maximum)
            varies = material_span(minimum, maximum, column)

            row[f"{column}_min"] = minimum
            row[f"{column}_max"] = maximum
            row[f"{column}_median"] = median
            row[f"{column}_mean"] = mean
            row[f"{column}_absolute_span"] = absolute_span
            row[f"{column}_fractional_span"] = fraction
            row[f"{column}_varies"] = varies

            if varies:
                varying_descriptors += 1
                fractional_spans.append(fraction)

        row["n_varying_descriptors"] = varying_descriptors
        row["has_geometry_variation"] = varying_descriptors > 0
        row["max_fractional_span"] = (
            max(fractional_spans) if fractional_spans else 0.0
        )
        row["mean_fractional_span_across_varying"] = (
            sum(fractional_spans) / len(fractional_spans)
            if fractional_spans
            else 0.0
        )

        group_rows.append(row)

    groups = pd.DataFrame(group_rows)

    # Framework-level output is simply the validated, geometry-complete population
    # with no new scientific classification.
    framework_output_columns = [
        "mof_id",
        "source_chemistry_group_id",
        "architecture_group_id",
        "topology_clean",
        "dimensionality_clean",
        *GEOMETRY_COLUMNS,
    ]
    framework_output = geometry_complete[
        framework_output_columns
    ].copy()

    # Descriptor-level census makes it easy to see which geometry variables
    # actually vary across families before choosing any contrast rule.
    descriptor_rows = []
    for column in GEOMETRY_COLUMNS:
        varies_col = f"{column}_varies"
        span_col = f"{column}_fractional_span"

        varying = groups[varies_col].astype("boolean").fillna(False)

        descriptor_rows.append(
            {
                "descriptor": column,
                "families_total": len(groups),
                "families_with_material_variation": int(varying.sum()),
                "fraction_of_families_varying": (
                    float(varying.mean()) if len(groups) else 0.0
                ),
                "median_fractional_span_among_varying": (
                    float(groups.loc[varying, span_col].median())
                    if varying.any()
                    else 0.0
                ),
                "p90_fractional_span_among_varying": (
                    float(groups.loc[varying, span_col].quantile(0.90))
                    if varying.any()
                    else 0.0
                ),
                "max_fractional_span": (
                    float(groups[span_col].max())
                    if len(groups)
                    else 0.0
                ),
            }
        )

    descriptor_census = pd.DataFrame(descriptor_rows)

    varying_groups = (
        groups["has_geometry_variation"]
        .astype("boolean")
        .fillna(False)
    )

    summary = pd.DataFrame(
        [
            ("validated_stage14_frameworks", len(validated)),
            (
                "geometry_complete_validated_frameworks",
                len(geometry_complete),
            ),
            (
                "validated_architecture_groups_with_geometry",
                groups["architecture_group_id"].nunique(),
            ),
            (
                "groups_with_geometry_variation",
                int(varying_groups.sum()),
            ),
            (
                "groups_without_geometry_variation",
                int((~varying_groups).sum()),
            ),
            (
                "frameworks_in_geometry_varying_groups",
                int(
                    groups.loc[
                        varying_groups,
                        "framework_count",
                    ].sum()
                ),
            ),
            (
                "median_varying_descriptors_per_varying_group",
                float(
                    groups.loc[
                        varying_groups,
                        "n_varying_descriptors",
                    ].median()
                )
                if varying_groups.any()
                else 0.0,
            ),
            (
                "median_max_fractional_span_per_varying_group",
                float(
                    groups.loc[
                        varying_groups,
                        "max_fractional_span",
                    ].median()
                )
                if varying_groups.any()
                else 0.0,
            ),
        ],
        columns=["metric", "value"],
    )

    definition = {
        "definition_version": DEFINITION_VERSION,
        "input_population": (
            "Stage 1.4 validated same-recorded-chemistry + "
            "same-recorded-architecture families"
        ),
        "geometry_descriptors": GEOMETRY_COLUMNS,
        "measurement": {
            "absolute_span": "family maximum minus family minimum",
            "fractional_span": (
                "(maximum - minimum) / max(abs(minimum), abs(maximum)); "
                "descriptive only"
            ),
            "variation_flag": (
                "descriptor range exceeds only numerical-noise tolerance"
            ),
        },
        "scientific_threshold_defined": False,
        "framework_pairs_constructed": False,
        "outcome_values_read": False,
        "purpose": (
            "measure the empirical within-family geometry variation distribution "
            "before choosing any meaningful contrast threshold"
        ),
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    atomic_write_parquet(
        framework_output.sort_values("mof_id").reset_index(drop=True),
        output_dir / "geometry_variation_frameworks.parquet",
    )
    atomic_write_parquet(
        groups.sort_values(
            ["max_fractional_span", "architecture_group_id"],
            ascending=[False, True],
        ).reset_index(drop=True),
        output_dir / "geometry_variation_groups.parquet",
    )
    atomic_write_csv(
        descriptor_census.sort_values(
            "families_with_material_variation",
            ascending=False,
        ).reset_index(drop=True),
        output_dir / "geometry_descriptor_census.csv",
    )
    atomic_write_csv(
        summary,
        output_dir / "geometry_variation_summary.csv",
    )
    atomic_write_text(
        json.dumps(definition, indent=2),
        output_dir / "geometry_variation_definition.json",
    )

    manifest = {
        "script": Path(__file__).name,
        "script_version": SCRIPT_VERSION,
        "definition_version": DEFINITION_VERSION,
        "started_at_utc": started_at,
        "completed_at_utc": utc_now(),
        "stage14_frameworks_sha256": sha256_file(input_path),
        "source_stage14_definition_version": stage14_manifest.get(
            "definition_version"
        ),
        "stage14_validated_only": True,
        "geometry_descriptors": GEOMETRY_COLUMNS,
        "scientific_contrast_threshold_defined": False,
        "pairs_constructed": False,
        "outcome_values_read": False,
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
    print("Descriptor census:")
    print(
        descriptor_census[
            [
                "descriptor",
                "families_with_material_variation",
                "fraction_of_families_varying",
                "median_fractional_span_among_varying",
                "p90_fractional_span_among_varying",
            ]
        ].to_string(index=False)
    )

    print()
    print(f"Saved results: {output_dir}")
    print(
        "Stop here. Inspect the variation distributions before defining "
        "a meaningful geometry contrast or constructing pairs."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
