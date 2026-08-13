#!/usr/bin/env python3
"""Define outcome-blind candidate families with the same recorded chemistry.

Scientific role
---------------
Project 17 holds chemistry approximately constant and later compares geometry.
This stage therefore constructs *candidate chemistry families*, not framework
pairs and not adsorption contrasts.

The family key is deliberately conservative and auditable. It requires:

* the same scale-invariant whole-CIF elemental composition;
* the same scale-invariant metal-element composition;
* the same valid ARC-MOF metal-, linker-, and functional-chemistry clusters;
* successful, internally consistent CIF parsing with no disorder or partial
  occupancy; and
* complete RAC evidence.

ARC-MOF documents negative cluster labels as structures that do not belong to
any cluster and should be treated as unique. Such labels are never allowed to
group frameworks here.

Topology, dimensionality, geometric cluster, measured pore descriptors, and
partial charges are excluded from the chemistry key. They are retained only as
descriptive evidence so later stages can study geometry rather than silently
matching it away.

Important limitation
--------------------
Whole-CIF composition and RAC-based cluster agreement do not prove identical
framework-connected linkers or nodes. No bonds are inferred here. The output
is a candidate-family census that must precede targeted connectivity checks and
pair construction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


SCRIPT_VERSION = "1.0.0"
DEFINITION_VERSION = "recorded_component_chemistry_v1"
COMPOSITION_DECIMALS = 12
DEFAULT_ROOT = Path(__file__).resolve().parents[1]

REGISTRY_RELATIVE = Path("Step 1 results") / "01_framework_registry"
CHEMISTRY_RELATIVE = Path("Step 1 results") / "02_cif_chemistry"
OUTPUT_RELATIVE = Path("Step 1 results") / "03_same_chemistry"

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

# These tolerances only distinguish an exactly repeated descriptor value from
# numerical noise in the group census. They are not scientific matching limits.
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

CLUSTER_COLUMNS = ["metal_cluster", "linker_cluster", "functional_cluster"]
CLUSTER_KEY_COLUMNS = [f"{column}_key" for column in CLUSTER_COLUMNS]

SIGNATURE_COMPONENTS = [
    "canonical_whole_cif_composition_json",
    "canonical_metal_fraction_json",
    "metal_cluster_key",
    "linker_cluster_key",
    "functional_cluster_key",
]

REGISTRY_COLUMNS = [
    "mof_id",
    "has_cif",
    "metal_cluster",
    "linker_cluster",
    "functional_cluster",
    "geo_cluster",
    "topology",
    "dimensionality",
    "rac_descriptors_complete",
    "geometry_descriptors_complete",
    *GEOMETRY_COLUMNS,
]

CHEMISTRY_COLUMNS = [
    "mof_id",
    "parse_ok",
    "raw_cif_audit_ok",
    "element_sets_match",
    "n_parsed_structures",
    "n_disordered_sites",
    "n_partial_occupancy_sites",
    "reduced_formula",
    "composition_json",
    "element_fraction_json",
    "metal_elements",
    "metal_composition_json",
    "n_distinct_metal_elements",
    "single_metal_element",
]

FRAMEWORK_OUTPUT_COLUMNS = [
    "mof_id",
    "has_cif",
    "chemistry_record_present",
    "parse_ok",
    "raw_cif_audit_ok",
    "element_sets_match",
    "n_parsed_structures",
    "n_disordered_sites",
    "n_partial_occupancy_sites",
    "reduced_formula",
    "canonical_whole_cif_composition_json",
    "canonical_metal_fraction_json",
    "composition_fraction_agrees",
    "metal_elements",
    "n_distinct_metal_elements",
    "single_metal_element",
    "metal_cluster",
    "linker_cluster",
    "functional_cluster",
    "metal_cluster_key",
    "linker_cluster_key",
    "functional_cluster_key",
    "missing_cluster_fields",
    "negative_unique_cluster_fields",
    "rac_descriptors_complete",
    "geometry_descriptors_complete",
    "composition_group_id",
    "signature_eligible",
    "same_chemistry_status",
    "exclusion_reason",
    "chemistry_group_id",
    "chemistry_group_size",
    "multi_member_candidate_family",
    "group_has_measured_geometry_variation",
    "geometry_contrast_candidate_family",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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


def require_columns(
    available: Iterable[str], required: Iterable[str], source: str
) -> None:
    available_set = set(available)
    missing = [column for column in required if column not in available_set]
    if missing:
        raise ValueError(f"{source} is missing required columns: {missing}")


def boolean_values(values: pd.Series) -> pd.Series:
    """Return nullable/object booleans as a warning-free nonmissing mask."""
    return values.astype("boolean").fillna(False)


def parquet_columns(path: Path) -> list[str]:
    try:
        import pyarrow.parquet as pq
    except ImportError as error:
        raise RuntimeError(
            "pyarrow is required. Install it with: py -m pip install pyarrow"
        ) from error
    return list(pq.ParquetFile(path).schema_arrow.names)


def parse_positive_mapping(value: Any) -> dict[str, Decimal] | None:
    """Parse a positive element-to-amount JSON object without float coercion."""
    if value is None or pd.isna(value):
        return None
    try:
        parsed = json.loads(
            str(value),
            parse_float=Decimal,
            parse_int=Decimal,
        )
    except (TypeError, ValueError, json.JSONDecodeError, InvalidOperation):
        return None
    if not isinstance(parsed, dict) or not parsed:
        return None

    cleaned: dict[str, Decimal] = {}
    for raw_key, raw_amount in parsed.items():
        key = str(raw_key).strip()
        if not key:
            return None
        try:
            amount = raw_amount if isinstance(raw_amount, Decimal) else Decimal(str(raw_amount))
        except (InvalidOperation, ValueError):
            return None
        if not amount.is_finite() or amount <= 0:
            return None
        cleaned[key] = cleaned.get(key, Decimal(0)) + amount
    return cleaned or None


def canonical_fraction_json(value: Any) -> str | None:
    """Create a cell-scale-invariant, order-invariant composition signature."""
    mapping = parse_positive_mapping(value)
    if mapping is None:
        return None
    total = sum(mapping.values(), Decimal(0))
    if not total.is_finite() or total <= 0:
        return None

    quantum = Decimal(1).scaleb(-COMPOSITION_DECIMALS)
    fractions: dict[str, str] = {}
    for key in sorted(mapping):
        fraction = (mapping[key] / total).quantize(quantum)
        if fraction <= 0:
            return None
        fractions[key] = format(fraction, f".{COMPOSITION_DECIMALS}f")
    return json.dumps(fractions, sort_keys=True, separators=(",", ":"))


def fraction_maps_close(
    canonical_json: Any,
    reference_json: Any,
    *,
    tolerance: float = 5e-11,
) -> bool:
    if canonical_json is None or pd.isna(canonical_json):
        return False
    reference = parse_positive_mapping(reference_json)
    if reference is None:
        return False
    try:
        canonical = json.loads(str(canonical_json))
        canonical_float = {str(key): float(value) for key, value in canonical.items()}
    except (TypeError, ValueError, json.JSONDecodeError):
        return False

    reference_total = float(sum(reference.values(), Decimal(0)))
    if not math.isfinite(reference_total) or reference_total <= 0:
        return False
    reference_float = {
        key: float(amount) / reference_total for key, amount in reference.items()
    }
    if set(canonical_float) != set(reference_float):
        return False
    return all(
        math.isclose(
            canonical_float[key],
            reference_float[key],
            rel_tol=0.0,
            abs_tol=tolerance,
        )
        for key in canonical_float
    )


def normalize_cluster(value: Any) -> tuple[str | None, str]:
    """Return a stable nonnegative integer cluster key and its evidence status."""
    if value is None or pd.isna(value):
        return None, "missing"
    text = str(value).strip()
    if not text:
        return None, "missing"
    try:
        numeric = Decimal(text)
    except InvalidOperation:
        return None, "invalid"
    if not numeric.is_finite() or numeric != numeric.to_integral_value():
        return None, "invalid"
    integer = int(numeric)
    if integer < 0:
        return str(integer), "negative_unique"
    return str(integer), "valid"


def joined_flag_names(
    frame: pd.DataFrame,
    status_columns: list[str],
    wanted_status: str | set[str],
) -> pd.Series:
    wanted = {wanted_status} if isinstance(wanted_status, str) else wanted_status
    values = [
        ";".join(
            cluster_column
            for cluster_column, status in zip(CLUSTER_COLUMNS, statuses)
            if status in wanted
        )
        for statuses in frame[status_columns].itertuples(index=False, name=None)
    ]
    return pd.Series(values, index=frame.index, dtype="string")


def signature_payload(row: pd.Series) -> str:
    values = [DEFINITION_VERSION, *(str(row[column]) for column in SIGNATURE_COMPONENTS)]
    return "\n".join(values)


def geometry_span_is_material(minimum: Any, maximum: Any, column: str) -> bool:
    if pd.isna(minimum) or pd.isna(maximum):
        return False
    minimum_float = float(minimum)
    maximum_float = float(maximum)
    scale = max(1.0, abs(minimum_float), abs(maximum_float))
    tolerance = max(GEOMETRY_NUMERICAL_TOLERANCE[column], 1e-12 * scale)
    return maximum_float - minimum_float > tolerance


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Project 17 root (default: inferred from this script location)",
    )
    return parser.parse_args()


def load_source_manifest(path: Path, stage: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing {stage} manifest: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("completed_successfully") is not True:
        raise RuntimeError(f"{stage} manifest is not marked successful")
    return manifest


def build_definition() -> dict[str, Any]:
    return {
        "definition_version": DEFINITION_VERSION,
        "scientific_target": (
            "candidate families with the same recorded chemical representation "
            "while topology and measured geometry remain free to vary"
        ),
        "signature_components": SIGNATURE_COMPONENTS,
        "composition_normalization": {
            "scope": "all elements in the parsed CIF structure",
            "cell_scale_invariant": True,
            "decimal_places": COMPOSITION_DECIMALS,
            "element_order_invariant": True,
        },
        "required_evidence": [
            "successful CIF parse",
            "successful raw-CIF audit and raw/parsed element-set agreement",
            "exactly one parsed structure",
            "no disordered or partial-occupancy sites",
            "at least one metal element",
            "complete RAC descriptors",
            "valid nonnegative metal, linker, and functional cluster labels",
        ],
        "excluded_from_signature": {
            "geometry": [*GEOMETRY_COLUMNS, "geo_cluster"],
            "structure_context": ["topology", "dimensionality"],
            "simulation_electrostatics": [
                "partial charges",
                "occupancy-weighted charge sum",
            ],
            "outcomes": ["adsorption values", "process values"],
        },
        "negative_cluster_policy": (
            "ARC-MOF negative cluster labels mean unclustered/assumed unique; "
            "they never place two frameworks in one chemistry family"
        ),
        "mixed_metal_policy": (
            "mixed-metal frameworks are not automatically excluded; they require "
            "the same normalized whole-CIF and metal-element compositions"
        ),
        "oxidation_state_policy": (
            "oxidation state is unavailable in Stage 1.2 and is not inferred"
        ),
        "pair_policy": (
            "family membership is not pair acceptance; connectivity and linker/node "
            "identity must be checked later for proposed comparisons"
        ),
        "known_limitations": [
            "whole-CIF composition is not a framework-only composition",
            "RAC/DBSCAN cluster agreement is similarity evidence, not identity proof",
            "bond connectivity and framework membership are not inferred here",
            "oxidation states are unavailable",
            "no geometry contrast or adsorption effect is accepted at this stage",
        ],
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args()
    root = args.project_root.resolve()
    registry_dir = root / REGISTRY_RELATIVE
    chemistry_dir = root / CHEMISTRY_RELATIVE
    output_dir = root / OUTPUT_RELATIVE
    registry_path = registry_dir / "framework_registry.parquet"
    chemistry_path = chemistry_dir / "cif_chemistry.parquet"

    for path in (registry_path, chemistry_path):
        if not path.is_file():
            raise FileNotFoundError(path)

    registry_manifest = load_source_manifest(
        registry_dir / "run_manifest.json", "Stage 1.1"
    )
    chemistry_manifest = load_source_manifest(
        chemistry_dir / "run_manifest.json", "Stage 1.2"
    )
    if chemistry_manifest.get("mode") != "full":
        raise RuntimeError("Stage 1.3 requires the audited full Stage 1.2 output")
    if chemistry_manifest.get("outcome_values_read") is not False:
        raise RuntimeError("Stage 1.2 provenance does not confirm outcome blindness")

    require_columns(parquet_columns(registry_path), REGISTRY_COLUMNS, registry_path.name)
    require_columns(parquet_columns(chemistry_path), CHEMISTRY_COLUMNS, chemistry_path.name)

    print("Project 17 Step 1.3: defining same-recorded-chemistry candidate families")
    print("Policy: no outcomes, no pairs, no geometry in the chemistry signature")
    started_at = utc_now()

    registry = pd.read_parquet(registry_path, columns=REGISTRY_COLUMNS)
    chemistry = pd.read_parquet(chemistry_path, columns=CHEMISTRY_COLUMNS)

    for name, frame in (("registry", registry), ("chemistry", chemistry)):
        if frame["mof_id"].isna().any() or not frame["mof_id"].is_unique:
            raise RuntimeError(f"{name} contains missing or duplicate mof_id values")
        frame["mof_id"] = frame["mof_id"].astype("string")

    registry_ids = set(registry["mof_id"].astype(str))
    registry_cif_ids = set(
        registry.loc[registry["has_cif"].fillna(False), "mof_id"].astype(str)
    )
    chemistry_ids = set(chemistry["mof_id"].astype(str))
    if chemistry_ids != registry_cif_ids:
        raise RuntimeError(
            "Full Stage 1.2 chemistry IDs do not exactly equal registry CIF IDs"
        )
    if not chemistry_ids.issubset(registry_ids):
        raise RuntimeError("Chemistry contains IDs outside the registry")

    chemistry["chemistry_record_present"] = True
    frame = registry.merge(
        chemistry,
        on="mof_id",
        how="left",
        validate="one_to_one",
    )
    frame["chemistry_record_present"] = boolean_values(
        frame["chemistry_record_present"]
    )

    frame["canonical_whole_cif_composition_json"] = frame["composition_json"].map(
        canonical_fraction_json
    )
    frame["canonical_metal_fraction_json"] = frame["metal_composition_json"].map(
        canonical_fraction_json
    )
    frame["composition_fraction_agrees"] = pd.Series(
        [
            fraction_maps_close(canonical, reference)
            for canonical, reference in zip(
                frame["canonical_whole_cif_composition_json"],
                frame["element_fraction_json"],
            )
        ],
        index=frame.index,
        dtype="boolean",
    )

    cluster_status_columns: list[str] = []
    for column in CLUSTER_COLUMNS:
        normalized = frame[column].map(normalize_cluster)
        frame[f"{column}_key"] = normalized.map(lambda item: item[0]).astype("string")
        status_column = f"{column}_status"
        frame[status_column] = normalized.map(lambda item: item[1]).astype("string")
        cluster_status_columns.append(status_column)

    frame["missing_cluster_fields"] = joined_flag_names(
        frame, cluster_status_columns, {"missing", "invalid"}
    )
    frame["negative_unique_cluster_fields"] = joined_flag_names(
        frame, cluster_status_columns, "negative_unique"
    )

    valid_composition = frame["canonical_whole_cif_composition_json"].notna()
    frame["composition_group_id"] = pd.Series(pd.NA, index=frame.index, dtype="string")
    frame.loc[valid_composition, "composition_group_id"] = (
        "comp1_"
        + frame.loc[valid_composition, "canonical_whole_cif_composition_json"].map(
            sha256_text
        )
    )

    has_cif = boolean_values(frame["has_cif"])
    record_present = boolean_values(frame["chemistry_record_present"])
    parsed = boolean_values(frame["parse_ok"])
    raw_ok = boolean_values(frame["raw_cif_audit_ok"])
    element_match = boolean_values(frame["element_sets_match"])
    exactly_one_structure = frame["n_parsed_structures"].eq(1).fillna(False)
    ordered = (
        frame["n_disordered_sites"].eq(0).fillna(False)
        & frame["n_partial_occupancy_sites"].eq(0).fillna(False)
    )
    composition_ok = valid_composition & boolean_values(
        frame["composition_fraction_agrees"]
    )
    metal_ok = (
        frame["canonical_metal_fraction_json"].notna()
        & frame["n_distinct_metal_elements"].gt(0).fillna(False)
    )
    rac_ok = boolean_values(frame["rac_descriptors_complete"])
    clusters_valid = frame[cluster_status_columns].eq("valid").all(axis=1)

    conditions = [
        ~has_cif,
        has_cif & ~record_present,
        record_present & ~parsed,
        parsed & ~raw_ok,
        parsed & raw_ok & ~element_match,
        parsed & raw_ok & element_match & ~exactly_one_structure,
        parsed & raw_ok & element_match & exactly_one_structure & ~ordered,
        parsed & raw_ok & element_match & exactly_one_structure & ordered & ~composition_ok,
        parsed
        & raw_ok
        & element_match
        & exactly_one_structure
        & ordered
        & composition_ok
        & ~metal_ok,
        parsed
        & raw_ok
        & element_match
        & exactly_one_structure
        & ordered
        & composition_ok
        & metal_ok
        & ~rac_ok,
        frame["missing_cluster_fields"].ne(""),
        frame["negative_unique_cluster_fields"].ne(""),
    ]
    reason_codes = [
        "registry_without_cif",
        "cif_chemistry_record_missing",
        "cif_parse_failed",
        "raw_cif_audit_failed",
        "raw_parsed_element_mismatch",
        "not_exactly_one_parsed_structure",
        "disorder_or_partial_occupancy",
        "invalid_or_inconsistent_whole_cif_composition",
        "no_valid_metal_element_composition",
        "incomplete_rac_descriptors",
        "missing_or_invalid_chemical_cluster_label",
        "negative_cluster_unique_assignment",
    ]
    frame["exclusion_reason"] = pd.Series(
        np.select(conditions, reason_codes, default="eligible_complete_signature"),
        index=frame.index,
        dtype="string",
    )
    frame["signature_eligible"] = frame["exclusion_reason"].eq(
        "eligible_complete_signature"
    )

    eligible = frame["signature_eligible"]
    frame["chemistry_group_id"] = pd.Series(pd.NA, index=frame.index, dtype="string")
    frame.loc[eligible, "chemistry_group_id"] = (
        "chem1_"
        + frame.loc[eligible, SIGNATURE_COMPONENTS]
        .apply(signature_payload, axis=1)
        .map(sha256_text)
    )

    group_sizes = frame.loc[eligible, "chemistry_group_id"].value_counts()
    frame["chemistry_group_size"] = (
        frame["chemistry_group_id"].map(group_sizes).astype("Int64")
    )
    frame["multi_member_candidate_family"] = (
        frame["signature_eligible"] & frame["chemistry_group_size"].ge(2).fillna(False)
    ).astype("boolean")
    frame["same_chemistry_status"] = frame["exclusion_reason"].copy()
    frame.loc[
        frame["signature_eligible"] & frame["chemistry_group_size"].eq(1),
        "same_chemistry_status",
    ] = "complete_signature_singleton"
    frame.loc[
        frame["multi_member_candidate_family"].fillna(False),
        "same_chemistry_status",
    ] = "multi_member_candidate_family"

    eligible_frame = frame.loc[eligible].copy()
    grouped = eligible_frame.groupby("chemistry_group_id", sort=True, dropna=False)
    groups = grouped.agg(
        chemistry_group_size=("mof_id", "size"),
        canonical_whole_cif_composition_json=(
            "canonical_whole_cif_composition_json",
            "first",
        ),
        canonical_metal_fraction_json=("canonical_metal_fraction_json", "first"),
        metal_elements=("metal_elements", "first"),
        n_distinct_metal_elements=("n_distinct_metal_elements", "first"),
        single_metal_element=("single_metal_element", "first"),
        metal_cluster_key=("metal_cluster_key", "first"),
        linker_cluster_key=("linker_cluster_key", "first"),
        functional_cluster_key=("functional_cluster_key", "first"),
        unique_reduced_formula_strings=("reduced_formula", "nunique"),
        frameworks_with_complete_geometry=("geometry_descriptors_complete", "sum"),
        unique_topology_labels=("topology", "nunique"),
        frameworks_with_topology=("topology", "count"),
        unique_dimensionality_labels=("dimensionality", "nunique"),
        frameworks_with_dimensionality=("dimensionality", "count"),
        unique_geo_cluster_labels=("geo_cluster", "nunique"),
        frameworks_with_geo_cluster=("geo_cluster", "count"),
    ).reset_index()

    for column in GEOMETRY_COLUMNS:
        statistics = grouped[column].agg(["count", "min", "max", "nunique"])
        statistics = statistics.rename(
            columns={
                "count": f"{column}_nonmissing",
                "min": f"{column}_min",
                "max": f"{column}_max",
                "nunique": f"{column}_unique_values",
            }
        ).reset_index()
        groups = groups.merge(
            statistics,
            on="chemistry_group_id",
            how="left",
            validate="one_to_one",
        )
        groups[f"{column}_span"] = groups[f"{column}_max"] - groups[f"{column}_min"]

    variation_flags = []
    for column in GEOMETRY_COLUMNS:
        variation_flags.append(
            pd.Series(
                [
                    geometry_span_is_material(minimum, maximum, column)
                    for minimum, maximum in zip(
                        groups[f"{column}_min"], groups[f"{column}_max"]
                    )
                ],
                index=groups.index,
                dtype="boolean",
            )
        )
    groups["has_measured_geometry_variation"] = pd.concat(
        variation_flags, axis=1
    ).any(axis=1)
    groups["multi_member_candidate_family"] = groups["chemistry_group_size"].ge(2)
    groups["geometry_contrast_candidate_family"] = (
        groups["multi_member_candidate_family"]
        & groups["frameworks_with_complete_geometry"].ge(2)
        & groups["has_measured_geometry_variation"]
    )
    groups = groups.sort_values(
        ["chemistry_group_size", "chemistry_group_id"],
        ascending=[False, True],
    ).reset_index(drop=True)

    geometry_variation_map = groups.set_index("chemistry_group_id")[
        "has_measured_geometry_variation"
    ]
    geometry_candidate_map = groups.set_index("chemistry_group_id")[
        "geometry_contrast_candidate_family"
    ]
    frame["group_has_measured_geometry_variation"] = (
        frame["chemistry_group_id"].map(geometry_variation_map).astype("boolean")
    )
    frame["geometry_contrast_candidate_family"] = (
        frame["chemistry_group_id"].map(geometry_candidate_map).astype("boolean")
    )

    framework_output = frame[FRAMEWORK_OUTPUT_COLUMNS].copy()
    exclusions = framework_output.loc[~framework_output["signature_eligible"]].copy()

    status_counts = (
        framework_output.groupby("same_chemistry_status", dropna=False)
        .agg(frameworks=("mof_id", "size"))
        .reset_index()
        .sort_values(["frameworks", "same_chemistry_status"], ascending=[False, True])
    )

    multi_groups = groups["multi_member_candidate_family"].fillna(False)
    geometry_groups = groups["geometry_contrast_candidate_family"].fillna(False)
    eligible_rows = framework_output["signature_eligible"].fillna(False)
    summary_rows: list[tuple[str, Any]] = [
        ("registry_frameworks", len(framework_output)),
        ("full_cif_chemistry_records", int(framework_output["chemistry_record_present"].sum())),
        ("valid_whole_cif_composition_signatures", int(framework_output["composition_group_id"].notna().sum())),
        ("complete_candidate_signature_frameworks", int(eligible_rows.sum())),
        ("complete_candidate_signature_groups", len(groups)),
        ("multi_member_candidate_families", int(multi_groups.sum())),
        (
            "frameworks_in_multi_member_candidate_families",
            int(groups.loc[multi_groups, "chemistry_group_size"].sum()),
        ),
        ("complete_signature_singletons", int(groups["chemistry_group_size"].eq(1).sum())),
        ("geometry_contrast_candidate_families", int(geometry_groups.sum())),
        (
            "frameworks_in_geometry_contrast_candidate_families",
            int(groups.loc[geometry_groups, "chemistry_group_size"].sum()),
        ),
        (
            "single_metal_signature_frameworks",
            int(
                boolean_values(
                    framework_output.loc[eligible_rows, "single_metal_element"]
                )
                .sum()
            ),
        ),
        (
            "mixed_metal_signature_frameworks",
            int(
                framework_output.loc[eligible_rows, "n_distinct_metal_elements"]
                .gt(1)
                .sum()
            ),
        ),
        ("excluded_frameworks", len(exclusions)),
    ]
    summary = pd.DataFrame(summary_rows, columns=["metric", "value"])

    definition = build_definition()
    output_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_parquet(
        framework_output.sort_values("mof_id").reset_index(drop=True),
        output_dir / "same_chemistry_frameworks.parquet",
    )
    atomic_write_parquet(groups, output_dir / "same_chemistry_groups.parquet")
    atomic_write_parquet(
        exclusions.sort_values("mof_id").reset_index(drop=True),
        output_dir / "same_chemistry_exclusions.parquet",
    )
    atomic_write_csv(summary, output_dir / "same_chemistry_summary.csv")
    atomic_write_csv(status_counts, output_dir / "same_chemistry_status_counts.csv")
    atomic_write_text(
        json.dumps(definition, indent=2),
        output_dir / "same_chemistry_definition.json",
    )

    completed_at = utc_now()
    manifest = {
        "script": Path(__file__).name,
        "script_version": SCRIPT_VERSION,
        "definition_version": DEFINITION_VERSION,
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
        "registry_sha256": sha256_file(registry_path),
        "cif_chemistry_sha256": sha256_file(chemistry_path),
        "source_registry_script_version": registry_manifest.get("script_version"),
        "source_chemistry_script_version": chemistry_manifest.get("script_version"),
        "source_chemistry_mode": chemistry_manifest.get("mode"),
        "signature_components": SIGNATURE_COMPONENTS,
        "composition_decimal_places": COMPOSITION_DECIMALS,
        "outcome_values_read": False,
        "pairs_constructed": False,
        "pairwise_same_chemistry_decisions_made": False,
        "candidate_chemistry_families_defined": True,
        "final_framework_chemistry_identity_claimed": False,
        "bond_connectivity_inferred": False,
        "framework_components_separated": False,
        "oxidation_states_inferred": False,
        "geometry_used_in_chemistry_signature": False,
        "topology_used_in_chemistry_signature": False,
        "partial_charges_used_in_chemistry_signature": False,
        "mixed_metal_frameworks_automatically_excluded": False,
        "negative_cluster_labels_grouped": False,
        "raw_directory_modified": False,
        "completed_successfully": True,
        "output_directory": str(OUTPUT_RELATIVE),
    }
    atomic_write_text(
        json.dumps(manifest, indent=2), output_dir / "run_manifest.json"
    )

    print(summary.to_string(index=False))
    print("\nStatus counts:")
    print(status_counts.to_string(index=False))
    print(f"\nSaved results: {output_dir}")
    print("Stop here and run py test.py. Do not construct geometry pairs yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
