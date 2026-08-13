#!/usr/bin/env python3
"""
Project 17 Step 1.4: define same-architecture families.

Simple baseline:
    Stage 1.3 chemistry is frozen.
    Within each Stage 1.3 multi-member chemistry family, frameworks are grouped by:
        1. recorded topology
        2. recorded dimensionality

No CIFs are parsed.
No bonds are inferred.
No CrystalNN is used.
No adsorption/process outcomes are read.
No framework pairs are constructed.

Missing topology or dimensionality is treated as ambiguous and is not placed in a
validated same-architecture family.

Measured geometry is NOT part of the architecture key. Geometry variation is
evaluated only after same-architecture groups are defined.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


SCRIPT_VERSION = "1.0.0"
DEFINITION_VERSION = "recorded_topology_dimensionality_architecture_v1"

DEFAULT_ROOT = Path(__file__).resolve().parents[1]

REGISTRY_RELATIVE = Path("Step 1 results") / "01_framework_registry"
STAGE13_RELATIVE = Path("Step 1 results") / "03_same_chemistry"
OUTPUT_RELATIVE = Path("Step 1 results") / "04_same_architecture"

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

GEOMETRY_NUMERICAL_TOLERANCE = {
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

STAGE13_COLUMNS = [
    "mof_id",
    "chemistry_group_id",
    "chemistry_group_size",
    "multi_member_candidate_family",
]

REGISTRY_COLUMNS = [
    "mof_id",
    "topology",
    "dimensionality",
    "geometry_descriptors_complete",
    *GEOMETRY_COLUMNS,
]

MISSING_LABELS = {
    "",
    "nan",
    "none",
    "null",
    "na",
    "n/a",
    "unknown",
    "?",
    "<na>",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def clean_label(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if text.lower() in MISSING_LABELS:
        return None
    return text


def architecture_id(
    chemistry_group_id: str,
    topology: str,
    dimensionality: str,
) -> str:
    payload = "\n".join(
        [
            DEFINITION_VERSION,
            str(chemistry_group_id),
            str(topology),
            str(dimensionality),
        ]
    )
    return "arch1_" + sha256_text(payload)


def geometry_span_is_material(
    minimum: Any,
    maximum: Any,
    column: str,
) -> bool:
    if pd.isna(minimum) or pd.isna(maximum):
        return False

    low = float(minimum)
    high = float(maximum)
    scale = max(1.0, abs(low), abs(high))
    tolerance = max(
        GEOMETRY_NUMERICAL_TOLERANCE[column],
        1e-12 * scale,
    )
    return high - low > tolerance


def load_manifest(path: Path, stage: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing {stage} manifest: {path}")

    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("completed_successfully") is not True:
        raise RuntimeError(f"{stage} manifest is not marked successful")
    return manifest


def require_columns(
    actual: Iterable[str],
    required: Iterable[str],
    source: str,
) -> None:
    actual_set = set(actual)
    missing = [column for column in required if column not in actual_set]
    if missing:
        raise ValueError(
            f"{source} is missing required columns: {missing}"
        )


def parquet_columns(path: Path) -> list[str]:
    try:
        import pyarrow.parquet as pq

        return list(pq.ParquetFile(path).schema.names)
    except Exception:
        return list(pd.read_parquet(path).columns)


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
        help="Project17 root; default inferred from script location",
    )
    return parser.parse_args()


def build_definition() -> dict[str, Any]:
    return {
        "definition_version": DEFINITION_VERSION,
        "scientific_target": (
            "refine Stage 1.3 same-recorded-chemistry candidate families "
            "into a simple same-recorded-architecture baseline"
        ),
        "chemistry_source": (
            "Stage 1.3 chemistry_group_id is accepted as the chemistry grouping "
            "and is not recomputed in Stage 1.4"
        ),
        "architecture_key": [
            "Stage 1.3 chemistry_group_id",
            "recorded topology",
            "recorded dimensionality",
        ],
        "matching_rule": (
            "two frameworks are in the same Stage 1.4 architecture group only "
            "when chemistry_group_id, topology, and dimensionality all match exactly"
        ),
        "missing_label_policy": (
            "missing topology or dimensionality is ambiguous and is excluded "
            "from validated same-architecture groups"
        ),
        "geometry_policy": (
            "measured geometry is excluded from the architecture key and is "
            "evaluated only after architecture groups are defined"
        ),
        "bond_policy": "no bond connectivity is inferred",
        "topology_policy": (
            "recorded topology is used as a practical architecture label; "
            "it is not claimed to be perfect ground truth"
        ),
        "pair_policy": "no framework pairs are constructed in Stage 1.4",
        "outcome_policy": "no adsorption or process outcomes are read",
        "known_limitations": [
            "Stage 1.3 chemistry is a recorded-chemistry candidate definition, not proof of molecular identity",
            "recorded topology may be missing or imperfect",
            "same topology plus dimensionality is a practical architecture proxy, not an atom-level graph proof",
            "missing architecture labels are conservatively treated as ambiguous",
        ],
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args()
    root = args.project_root.resolve()

    registry_dir = root / REGISTRY_RELATIVE
    stage13_dir = root / STAGE13_RELATIVE
    output_dir = root / OUTPUT_RELATIVE

    registry_path = registry_dir / "framework_registry.parquet"
    stage13_path = stage13_dir / "same_chemistry_frameworks.parquet"

    for path in (registry_path, stage13_path):
        if not path.is_file():
            raise FileNotFoundError(path)

    registry_manifest = load_manifest(
        registry_dir / "run_manifest.json",
        "Stage 1.1",
    )
    stage13_manifest = load_manifest(
        stage13_dir / "run_manifest.json",
        "Stage 1.3",
    )

    if stage13_manifest.get("outcome_values_read") is not False:
        raise RuntimeError(
            "Stage 1.3 provenance does not confirm outcome blindness"
        )
    if stage13_manifest.get("pairs_constructed") is not False:
        raise RuntimeError(
            "Stage 1.3 provenance does not confirm pair blindness"
        )

    require_columns(
        parquet_columns(stage13_path),
        STAGE13_COLUMNS,
        stage13_path.name,
    )
    require_columns(
        parquet_columns(registry_path),
        REGISTRY_COLUMNS,
        registry_path.name,
    )

    print("Project 17 Step 1.4: defining same recorded architecture")
    print(
        "Policy: Stage 1.3 chemistry frozen; exact topology + dimensionality; "
        "no CIFs, no CrystalNN, no outcomes, no pairs"
    )

    started_at = utc_now()

    stage13 = pd.read_parquet(
        stage13_path,
        columns=STAGE13_COLUMNS,
    )
    registry = pd.read_parquet(
        registry_path,
        columns=REGISTRY_COLUMNS,
    )

    for name, frame in (
        ("Stage 1.3", stage13),
        ("registry", registry),
    ):
        if frame["mof_id"].isna().any():
            raise RuntimeError(f"{name} contains missing mof_id values")
        if not frame["mof_id"].is_unique:
            raise RuntimeError(f"{name} contains duplicate mof_id values")
        frame["mof_id"] = frame["mof_id"].astype("string")

    targets = stage13.loc[
        stage13["multi_member_candidate_family"]
        .astype("boolean")
        .fillna(False)
    ].copy()

    if targets.empty:
        raise RuntimeError(
            "Stage 1.3 contains no multi-member candidate chemistry families"
        )

    target_ids = set(targets["mof_id"].astype(str))
    registry_targets = registry.loc[
        registry["mof_id"].astype(str).isin(target_ids)
    ].copy()

    if set(registry_targets["mof_id"].astype(str)) != target_ids:
        raise RuntimeError(
            "not every Stage 1.3 target exists in the framework registry"
        )

    frame = targets.merge(
        registry_targets,
        on="mof_id",
        how="left",
        validate="one_to_one",
    ).rename(
        columns={
            "chemistry_group_id": "source_chemistry_group_id",
            "chemistry_group_size": "source_chemistry_group_size",
        }
    )

    frame["topology_clean"] = (
        frame["topology"].map(clean_label).astype("string")
    )
    frame["dimensionality_clean"] = (
        frame["dimensionality"].map(clean_label).astype("string")
    )

    frame["architecture_label_complete"] = (
        frame["topology_clean"].notna()
        & frame["dimensionality_clean"].notna()
    )

    frame["architecture_group_id"] = pd.Series(
        pd.NA,
        index=frame.index,
        dtype="string",
    )

    eligible = frame["architecture_label_complete"]

    frame.loc[eligible, "architecture_group_id"] = [
        architecture_id(
            chemistry_group_id,
            topology,
            dimensionality,
        )
        for chemistry_group_id, topology, dimensionality in zip(
            frame.loc[eligible, "source_chemistry_group_id"].astype(str),
            frame.loc[eligible, "topology_clean"].astype(str),
            frame.loc[eligible, "dimensionality_clean"].astype(str),
        )
    ]

    group_sizes = (
        frame.loc[eligible, "architecture_group_id"]
        .value_counts()
    )
    frame["architecture_group_size"] = (
        frame["architecture_group_id"]
        .map(group_sizes)
        .astype("Int64")
    )

    frame["same_architecture_family"] = (
        frame["architecture_label_complete"]
        & frame["architecture_group_size"].ge(2).fillna(False)
    )

    frame["architecture_status"] = pd.Series(
        "architecture_singleton",
        index=frame.index,
        dtype="string",
    )

    missing_topology = frame["topology_clean"].isna()
    missing_dimensionality = frame["dimensionality_clean"].isna()

    frame.loc[
        missing_topology & missing_dimensionality,
        "architecture_status",
    ] = "ambiguous_missing_topology_and_dimensionality"

    frame.loc[
        missing_topology & ~missing_dimensionality,
        "architecture_status",
    ] = "ambiguous_missing_topology"

    frame.loc[
        ~missing_topology & missing_dimensionality,
        "architecture_status",
    ] = "ambiguous_missing_dimensionality"

    frame.loc[
        frame["same_architecture_family"],
        "architecture_status",
    ] = "validated_same_architecture"

    # Build validated groups only.
    validated = frame.loc[
        frame["same_architecture_family"]
    ].copy()

    group_rows: list[dict[str, Any]] = []

    for group_id, members in validated.groupby(
        "architecture_group_id",
        sort=True,
    ):
        complete_geometry = (
            members["geometry_descriptors_complete"]
            .astype("boolean")
            .fillna(False)
        )

        row: dict[str, Any] = {
            "architecture_group_id": str(group_id),
            "source_chemistry_group_id": str(
                members["source_chemistry_group_id"].iloc[0]
            ),
            "architecture_group_size": len(members),
            "topology": str(members["topology_clean"].iloc[0]),
            "dimensionality": str(
                members["dimensionality_clean"].iloc[0]
            ),
            "frameworks_with_complete_geometry": int(
                complete_geometry.sum()
            ),
        }

        has_variation = False
        for column in GEOMETRY_COLUMNS:
            values = pd.to_numeric(
                members.loc[complete_geometry, column],
                errors="coerce",
            ).dropna()

            minimum = values.min() if len(values) else pd.NA
            maximum = values.max() if len(values) else pd.NA

            row[f"{column}_min"] = minimum
            row[f"{column}_max"] = maximum

            if (
                len(values) >= 2
                and geometry_span_is_material(
                    minimum,
                    maximum,
                    column,
                )
            ):
                has_variation = True

        row["has_measured_geometry_variation"] = has_variation
        row["geometry_contrast_candidate_family"] = bool(
            len(members) >= 2
            and int(complete_geometry.sum()) >= 2
            and has_variation
        )

        group_rows.append(row)

    groups = pd.DataFrame(group_rows)

    if groups.empty:
        groups = pd.DataFrame(
            columns=[
                "architecture_group_id",
                "source_chemistry_group_id",
                "architecture_group_size",
                "topology",
                "dimensionality",
                "frameworks_with_complete_geometry",
                *[
                    item
                    for column in GEOMETRY_COLUMNS
                    for item in (f"{column}_min", f"{column}_max")
                ],
                "has_measured_geometry_variation",
                "geometry_contrast_candidate_family",
            ]
        )

    if len(groups):
        group_index = groups.set_index("architecture_group_id")
        frame["group_has_measured_geometry_variation"] = (
            frame["architecture_group_id"]
            .map(group_index["has_measured_geometry_variation"])
            .astype("boolean")
        )
        frame["geometry_contrast_candidate_family"] = (
            frame["architecture_group_id"]
            .map(group_index["geometry_contrast_candidate_family"])
            .astype("boolean")
        )
    else:
        frame["group_has_measured_geometry_variation"] = pd.Series(
            pd.NA,
            index=frame.index,
            dtype="boolean",
        )
        frame["geometry_contrast_candidate_family"] = pd.Series(
            pd.NA,
            index=frame.index,
            dtype="boolean",
        )

    exclusions = frame.loc[
        ~frame["same_architecture_family"]
    ].copy()

    status_counts = (
        frame.groupby(
            "architecture_status",
            dropna=False,
        )
        .agg(frameworks=("mof_id", "size"))
        .reset_index()
        .sort_values(
            ["frameworks", "architecture_status"],
            ascending=[False, True],
        )
        .reset_index(drop=True)
    )

    chemistry_family_census = (
        frame.groupby(
            "source_chemistry_group_id",
            sort=True,
        )
        .agg(
            source_chemistry_group_size=("mof_id", "size"),
            architecture_label_complete_frameworks=(
                "architecture_label_complete",
                "sum",
            ),
            validated_frameworks=(
                "same_architecture_family",
                "sum",
            ),
            validated_architecture_groups=(
                "architecture_group_id",
                lambda values: int(
                    values[
                        frame.loc[values.index, "same_architecture_family"]
                    ].nunique()
                ),
            ),
        )
        .reset_index()
    )

    multi_architecture = (
        chemistry_family_census[
            "validated_architecture_groups"
        ].gt(1)
    )

    geometry_groups = (
        groups["geometry_contrast_candidate_family"]
        .astype("boolean")
        .fillna(False)
        if len(groups)
        else pd.Series(dtype="boolean")
    )

    summary_rows: list[tuple[str, Any]] = [
        (
            "source_multi_member_chemistry_families",
            frame["source_chemistry_group_id"].nunique(),
        ),
        ("target_frameworks", len(frame)),
        (
            "frameworks_with_complete_architecture_labels",
            int(frame["architecture_label_complete"].sum()),
        ),
        (
            "frameworks_with_missing_topology",
            int(frame["topology_clean"].isna().sum()),
        ),
        (
            "frameworks_with_missing_dimensionality",
            int(frame["dimensionality_clean"].isna().sum()),
        ),
        (
            "validated_same_architecture_frameworks",
            int(frame["same_architecture_family"].sum()),
        ),
        ("validated_same_architecture_groups", len(groups)),
        (
            "source_chemistry_families_split_into_multiple_architectures",
            int(multi_architecture.sum()),
        ),
        (
            "architecture_singleton_frameworks",
            int(
                frame["architecture_status"]
                .eq("architecture_singleton")
                .sum()
            ),
        ),
        (
            "ambiguous_missing_architecture_frameworks",
            int(
                frame["architecture_status"]
                .str.startswith("ambiguous_", na=False)
                .sum()
            ),
        ),
        (
            "geometry_contrast_candidate_families",
            int(geometry_groups.sum()) if len(groups) else 0,
        ),
        (
            "frameworks_in_geometry_contrast_candidate_families",
            int(
                groups.loc[
                    geometry_groups,
                    "architecture_group_size",
                ].sum()
            )
            if len(groups)
            else 0,
        ),
    ]

    summary = pd.DataFrame(
        summary_rows,
        columns=["metric", "value"],
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    framework_output = frame.sort_values(
        "mof_id"
    ).reset_index(drop=True)

    groups_output = groups.sort_values(
        ["architecture_group_size", "architecture_group_id"],
        ascending=[False, True],
    ).reset_index(drop=True)

    exclusions_output = exclusions.sort_values(
        "mof_id"
    ).reset_index(drop=True)

    chemistry_family_census = chemistry_family_census.sort_values(
        [
            "validated_architecture_groups",
            "source_chemistry_group_size",
            "source_chemistry_group_id",
        ],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    atomic_write_parquet(
        framework_output,
        output_dir / "same_architecture_frameworks.parquet",
    )
    atomic_write_parquet(
        groups_output,
        output_dir / "same_architecture_groups.parquet",
    )
    atomic_write_parquet(
        exclusions_output,
        output_dir / "same_architecture_exclusions.parquet",
    )
    atomic_write_parquet(
        chemistry_family_census,
        output_dir / "chemistry_family_architecture_census.parquet",
    )
    atomic_write_csv(
        summary,
        output_dir / "same_architecture_summary.csv",
    )
    atomic_write_csv(
        status_counts,
        output_dir / "same_architecture_status_counts.csv",
    )
    atomic_write_text(
        json.dumps(build_definition(), indent=2),
        output_dir / "same_architecture_definition.json",
    )

    completed_at = utc_now()

    manifest = {
        "script": Path(__file__).name,
        "script_version": SCRIPT_VERSION,
        "definition_version": DEFINITION_VERSION,
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
        "registry_sha256": sha256_file(registry_path),
        "same_chemistry_frameworks_sha256": sha256_file(stage13_path),
        "source_registry_script_version": registry_manifest.get(
            "script_version"
        ),
        "source_stage13_script_version": stage13_manifest.get(
            "script_version"
        ),
        "source_stage13_definition_version": stage13_manifest.get(
            "definition_version"
        ),
        "chemistry_frozen_from_stage13": True,
        "architecture_key": [
            "chemistry_group_id",
            "topology",
            "dimensionality",
        ],
        "topology_used_in_architecture_key": True,
        "dimensionality_used_in_architecture_key": True,
        "geometry_used_in_architecture_key": False,
        "geometry_evaluated_after_architecture_grouping": True,
        "cif_archive_read": False,
        "bond_connectivity_inferred": False,
        "crystalnn_used": False,
        "outcome_values_read": False,
        "pairs_constructed": False,
        "raw_directory_modified": False,
        "completed_successfully": True,
        "output_directory": str(OUTPUT_RELATIVE),
    }

    atomic_write_text(
        json.dumps(manifest, indent=2),
        output_dir / "run_manifest.json",
    )

    print()
    print(summary.to_string(index=False))

    print()
    print("Status counts:")
    print(status_counts.to_string(index=False))

    print()
    print(f"Saved results: {output_dir}")
    print(
        "Stop here and run py .\\test_04.py. "
        "Do not construct pairs yet."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
