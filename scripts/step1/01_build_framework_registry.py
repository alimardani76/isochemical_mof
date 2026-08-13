#!/usr/bin/env python3
"""Build the outcome-blind Project 17 ARC-MOF framework registry.

Scientific role
---------------
This script establishes one traceable row per ARC-MOF framework. It joins
geometry, topology, cluster, RAC, CIF-availability, adsorption-availability,
and process-availability metadata. It does not read adsorption or process
outcome values, construct pairs, or define "same chemistry".

Project 17 deliberately postpones eligibility and matching decisions. In
particular, Project 7's metal-change eligibility flags are not reproduced.
"""

from __future__ import annotations

import gc
import json
import re
import sys
import tarfile
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

import pandas as pd


SCRIPT_VERSION = "1.0.0"

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
OUT = ROOT / "Step 1 results" / "01_framework_registry"

ARCHIVE_NAME = "ARCMOF_20241004.tar.gz"

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

CLUSTER_SOURCES = [
    ("geo-clusters.csv", "geo_cluster"),
    ("mc-clusters.csv", "metal_cluster"),
    ("func-clusters.csv", "functional_cluster"),
    ("flig-clusters.csv", "linker_cluster"),
]

ADSORPTION_SOURCES = [
    ("landfill-CH4.csv", "has_ads_landfill_ch4"),
    ("landfill-CO2.csv", "has_ads_landfill_co2"),
    ("methane.csv", "has_ads_methane"),
    ("methane_purification-CH4.csv", "has_ads_methane_purification_ch4"),
    ("methane_purification-CO2.csv", "has_ads_methane_purification_co2"),
    ("post_comb_vsa-CO2.csv", "has_ads_post_comb_vsa_co2"),
    ("post_comb_vsa-N2.csv", "has_ads_post_comb_vsa_n2"),
    ("pre_comb_4040-CO2.csv", "has_ads_pre_comb_4040_co2"),
    ("pre_comb_4040-H2.csv", "has_ads_pre_comb_4040_h2"),
]

REQUIRED_FILES = [
    "geometric_properties.csv",
    "ARC-MOF_Dim.csv",
    "all_topology_lists.csv",
    "RACs.csv",
    ARCHIVE_NAME,
    "overall_process.csv",
    *[name for name, _ in CLUSTER_SOURCES],
    *[name for name, _ in ADSORPTION_SOURCES],
]

# These are compatibility signatures from the Project 7 ARC-MOF source release.
# They are audited, not treated as universal scientific constants.
REFERENCE_SIGNATURES = {
    "geometry_rows": 521_316,
    "arc_mof_geometry_rows": 279_019,
    "archive_cif_files": 242_517,
    "adsorption_union_overlap": 279_010,
    "adsorption_union_outside_registry": 600,
}

RAC_METADATA = {
    "Unnamed: 0",
    "filename",
    "ARC_MOF",
    "DB_num",
    "order_f-lig",
    "bool_f-lig",
    "order_mc",
    "bool_mc",
    "order_func",
    "bool_func",
    "order_lc",
    "bool_lc",
}

SUFFIX_PATTERN = re.compile(r"(?i)(?:\.cif|_repeat|_sqe)$")


def require_columns(frame: pd.DataFrame, columns: Iterable[str], source: str) -> None:
    """Fail before a join if a required source column is absent."""
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{source} is missing required columns: {missing}")


def require_parquet_engine() -> None:
    """Fail before expensive input scans if pandas cannot write Parquet."""
    try:
        import pyarrow  # noqa: F401
    except ImportError:
        try:
            import fastparquet  # noqa: F401
        except ImportError as error:
            raise RuntimeError(
                "A Parquet engine is required. Install one with: "
                "py -m pip install pyarrow"
            ) from error


def canonicalize_ids(values: pd.Series) -> pd.Series:
    """Normalize only verified terminal filename decorations.

    Case and internal text are preserved. Repeated terminal decorations are
    removed to handle forms such as ``name_sqe_repeat.cif``. Any resulting
    collision is audited and is never silently accepted for the registry key.
    """
    result = values.astype("string").str.strip()
    result = result.mask(result.eq(""), pd.NA)

    for _ in range(4):
        updated = result.str.replace(SUFFIX_PATTERN, "", regex=True)
        if updated.equals(result):
            break
        result = updated

    result = result.str.strip()
    return result.mask(result.eq(""), pd.NA)


def canonicalize_one(value: str) -> str | None:
    result = canonicalize_ids(pd.Series([value], dtype="string")).iloc[0]
    return None if pd.isna(result) else str(result)


def parse_arc_mof_flag(values: pd.Series) -> pd.Series:
    """Parse the study-boundary flag without relying on pandas dtype guessing."""
    normalized = values.astype("string").str.strip().str.lower()
    mapping = {
        "true": True,
        "1": True,
        "yes": True,
        "false": False,
        "0": False,
        "no": False,
    }
    parsed = normalized.map(mapping).astype("boolean")
    invalid = values.notna() & parsed.isna()
    if invalid.any():
        examples = values.loc[invalid].astype(str).drop_duplicates().head(10).tolist()
        raise ValueError(f"Unrecognized ARC-MOF flag values: {examples}")
    if parsed.isna().any():
        raise ValueError("ARC-MOF contains missing study-boundary flags")
    return parsed


def add_id_audit(
    rows: list[dict[str, object]],
    examples: list[dict[str, object]],
    source: str,
    raw_values: pd.Series,
    canonical_values: pd.Series,
) -> None:
    """Record missing IDs, duplicate keys, and normalization/case collisions."""
    raw = raw_values.astype("string")
    raw_stripped = raw.str.strip()
    table = pd.DataFrame({"raw_id": raw_stripped, "mof_id": canonical_values})
    valid = table.dropna(subset=["mof_id"]).copy()

    raw_per_canonical = valid.groupby("mof_id", dropna=False)["raw_id"].nunique()
    normalization_collisions = raw_per_canonical.loc[raw_per_canonical.gt(1)]

    canonical_unique = valid["mof_id"].drop_duplicates()
    case_table = pd.DataFrame(
        {
            "mof_id": canonical_unique,
            "casefold_id": canonical_unique.str.casefold(),
        }
    )
    case_counts = case_table.groupby("casefold_id")["mof_id"].nunique()
    case_collisions = case_counts.loc[case_counts.gt(1)]

    rows.append(
        {
            "source": source,
            "rows_scanned": len(table),
            "missing_or_blank_raw_ids": int(raw_stripped.isna().sum() + raw_stripped.eq("").sum()),
            "unique_raw_ids": int(raw_stripped.nunique(dropna=True)),
            "unique_canonical_ids": int(valid["mof_id"].nunique()),
            "duplicate_canonical_rows": int(valid["mof_id"].duplicated().sum()),
            "normalization_collision_groups": int(len(normalization_collisions)),
            "casefold_collision_groups": int(len(case_collisions)),
        }
    )

    for mof_id in normalization_collisions.index[:20]:
        raw_forms = valid.loc[valid["mof_id"].eq(mof_id), "raw_id"].drop_duplicates()
        examples.append(
            {
                "source": source,
                "collision_type": "multiple_raw_forms_to_one_canonical",
                "diagnostic_key": str(mof_id),
                "values": " | ".join(raw_forms.astype(str).head(10)),
            }
        )

    for casefold_id in case_collisions.index[:20]:
        forms = case_table.loc[
            case_table["casefold_id"].eq(casefold_id), "mof_id"
        ].drop_duplicates()
        examples.append(
            {
                "source": source,
                "collision_type": "case_only_canonical_difference",
                "diagnostic_key": str(casefold_id),
                "values": " | ".join(forms.astype(str).head(10)),
            }
        )


def require_unique_registry_key(frame: pd.DataFrame, source: str) -> None:
    if frame["mof_id"].isna().any():
        raise RuntimeError(f"{source} contains missing canonical IDs")
    duplicates = frame["mof_id"].duplicated(keep=False)
    if duplicates.any():
        sample = frame.loc[duplicates, "mof_id"].drop_duplicates().head(10).tolist()
        raise RuntimeError(f"Duplicate canonical IDs in {source}: {sample}")


def collapse_consistent_mapping(
    frame: pd.DataFrame,
    value_columns: list[str],
    source: str,
) -> pd.DataFrame:
    """Allow exact repetition but reject one ID mapping to conflicting values."""
    if frame["mof_id"].isna().any():
        raise RuntimeError(f"{source} contains missing canonical IDs")

    duplicate_ids = frame.loc[frame["mof_id"].duplicated(keep=False), "mof_id"].unique()
    if len(duplicate_ids):
        duplicate_rows = frame.loc[frame["mof_id"].isin(duplicate_ids)]
        conflicts: list[str] = []
        for mof_id, group in duplicate_rows.groupby("mof_id", sort=False):
            if any(group[column].nunique(dropna=False) > 1 for column in value_columns):
                conflicts.append(str(mof_id))
                if len(conflicts) >= 10:
                    break
        if conflicts:
            raise RuntimeError(f"Conflicting mappings in {source}: {conflicts}")

    return frame.drop_duplicates("mof_id", keep="first").copy()


def coverage_row(
    source: str,
    source_ids: set[str],
    registry_ids: set[str],
) -> dict[str, object]:
    overlap = source_ids & registry_ids
    return {
        "source": source,
        "source_unique_ids": len(source_ids),
        "matched_registry_ids": len(overlap),
        "registry_ids_missing_from_source": len(registry_ids - source_ids),
        "source_ids_outside_registry": len(source_ids - registry_ids),
        "fraction_of_registry_matched": len(overlap) / len(registry_ids),
    }


def scan_membership_csv(
    path: Path,
    id_audit_rows: list[dict[str, object]],
    collision_examples: list[dict[str, object]],
) -> set[str]:
    """Read only the filename column from an outcome-bearing CSV."""
    canonical_ids: set[str] = set()
    unique_raw_ids: set[str] = set()
    first_raw_by_id: dict[str, str] = {}
    rows_scanned = 0
    missing_or_blank = 0
    valid_canonical_rows = 0
    normalization_collision_ids: set[str] = set()
    casefold_first: dict[str, str] = {}
    casefold_collision_ids: set[str] = set()

    for chunk in pd.read_csv(path, usecols=["filename"], chunksize=250_000):
        raw = chunk["filename"].astype("string").str.strip()
        canonical = canonicalize_ids(raw)
        rows_scanned += len(chunk)
        missing_or_blank += int(raw.isna().sum() + raw.eq("").sum())

        valid = pd.DataFrame({"raw_id": raw, "mof_id": canonical}).dropna(
            subset=["mof_id"]
        )
        valid_canonical_rows += len(valid)
        unique_raw_ids.update(valid["raw_id"].astype(str).unique())

        # Outcome files commonly repeat one framework across conditions. Loop
        # only over unique raw/canonical pairs, not over every outcome row.
        unique_pairs = valid.drop_duplicates(["raw_id", "mof_id"])
        canonical_ids.update(unique_pairs["mof_id"].astype(str))

        for raw_id, mof_id in unique_pairs[["raw_id", "mof_id"]].itertuples(
            index=False, name=None
        ):
            canonical_id = str(mof_id)
            raw_text = str(raw_id)

            prior_raw = first_raw_by_id.setdefault(canonical_id, raw_text)
            if prior_raw != raw_text:
                normalization_collision_ids.add(canonical_id)
                if len(collision_examples) < 200:
                    collision_examples.append(
                        {
                            "source": path.name,
                            "collision_type": "multiple_raw_forms_to_one_canonical",
                            "diagnostic_key": canonical_id,
                            "values": f"{prior_raw} | {raw_text}",
                        }
                    )

            folded = canonical_id.casefold()
            prior_case = casefold_first.setdefault(folded, canonical_id)
            if prior_case != canonical_id:
                casefold_collision_ids.add(folded)

        del chunk, raw, canonical, valid, unique_pairs

    id_audit_rows.append(
        {
            "source": path.name,
            "rows_scanned": rows_scanned,
            "missing_or_blank_raw_ids": missing_or_blank,
            "unique_raw_ids": len(unique_raw_ids),
            "unique_canonical_ids": len(canonical_ids),
            "duplicate_canonical_rows": valid_canonical_rows - len(canonical_ids),
            "normalization_collision_groups": len(normalization_collision_ids),
            "casefold_collision_groups": len(casefold_collision_ids),
        }
    )
    return canonical_ids


def scan_cif_archive(
    path: Path,
    id_audit_rows: list[dict[str, object]],
    collision_examples: list[dict[str, object]],
) -> tuple[set[str], int]:
    """Scan CIF member names without extracting archive contents."""
    canonical_ids: set[str] = set()
    unique_raw_ids: set[str] = set()
    first_raw_by_id: dict[str, str] = {}
    exact_duplicate_rows = 0
    normalization_collision_ids: set[str] = set()
    casefold_first: dict[str, str] = {}
    casefold_collision_ids: set[str] = set()
    cif_files = 0

    with tarfile.open(path, mode="r|gz") as archive:
        for member in archive:
            if not member.isfile() or not member.name.lower().endswith(".cif"):
                continue
            cif_files += 1
            member_name = member.name.replace("\\", "/")
            raw_id = PurePosixPath(member_name).name
            unique_raw_ids.add(raw_id)
            canonical_id = canonicalize_one(raw_id)
            if canonical_id is None:
                continue

            if canonical_id in canonical_ids:
                exact_duplicate_rows += 1
            else:
                canonical_ids.add(canonical_id)

            prior_raw = first_raw_by_id.setdefault(canonical_id, raw_id)
            if prior_raw != raw_id:
                normalization_collision_ids.add(canonical_id)
                if len(collision_examples) < 200:
                    collision_examples.append(
                        {
                            "source": path.name,
                            "collision_type": "multiple_raw_forms_to_one_canonical",
                            "diagnostic_key": canonical_id,
                            "values": f"{prior_raw} | {raw_id}",
                        }
                    )

            folded = canonical_id.casefold()
            prior_case = casefold_first.setdefault(folded, canonical_id)
            if prior_case != canonical_id:
                casefold_collision_ids.add(folded)

    id_audit_rows.append(
        {
            "source": path.name,
            "rows_scanned": cif_files,
            "missing_or_blank_raw_ids": 0,
            "unique_raw_ids": len(unique_raw_ids),
            "unique_canonical_ids": len(canonical_ids),
            "duplicate_canonical_rows": exact_duplicate_rows,
            "normalization_collision_groups": len(normalization_collision_ids),
            "casefold_collision_groups": len(casefold_collision_ids),
        }
    )
    return canonical_ids, cif_files


def write_outputs(
    registry: pd.DataFrame,
    exclusions: pd.DataFrame,
    id_audit_rows: list[dict[str, object]],
    collision_examples: list[dict[str, object]],
    coverage_rows: list[dict[str, object]],
    rac_audit: pd.DataFrame,
    observed_signatures: dict[str, int],
) -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    registry.to_parquet(OUT / "framework_registry.parquet", index=False)
    exclusions.to_parquet(OUT / "geometry_exclusions.parquet", index=False)
    pd.DataFrame(id_audit_rows).to_csv(OUT / "source_id_audit.csv", index=False)
    pd.DataFrame(
        collision_examples,
        columns=["source", "collision_type", "diagnostic_key", "values"],
    ).to_csv(
        OUT / "normalization_collision_examples.csv", index=False
    )
    pd.DataFrame(coverage_rows).to_csv(OUT / "source_coverage.csv", index=False)
    rac_audit.to_csv(OUT / "rac_descriptor_audit.csv", index=False)

    signature_rows = []
    for metric, expected in REFERENCE_SIGNATURES.items():
        observed = observed_signatures[metric]
        signature_rows.append(
            {
                "metric": metric,
                "reference_value": expected,
                "observed_value": observed,
                "matches_project7_source_release": observed == expected,
            }
        )
    pd.DataFrame(signature_rows).to_csv(OUT / "dataset_signature.csv", index=False)

    summary_rows: list[tuple[str, object]] = [
        ("registry_rows", len(registry)),
        ("unique_mof_ids", registry["mof_id"].nunique()),
        ("excluded_non_arc_mof_geometry_rows", len(exclusions)),
        ("geometry_descriptor_count", len(GEOMETRY_COLUMNS)),
        ("rac_descriptor_count", len(rac_audit)),
        ("has_dimensionality", int(registry["has_dimensionality"].sum())),
        ("has_topology", int(registry["has_topology"].sum())),
        ("has_all_cluster_labels", int(registry["has_all_cluster_labels"].sum())),
        ("has_cif", int(registry["has_cif"].sum())),
        ("has_any_adsorption_source", int(registry["has_any_adsorption_source"].sum())),
        ("has_all_adsorption_sources", int(registry["has_all_adsorption_sources"].sum())),
        ("has_process_source", int(registry["has_process_source"].sum())),
        ("geometry_descriptors_complete", int(registry["geometry_descriptors_complete"].sum())),
        ("positive_Df", int(registry["positive_Df"].sum())),
        ("rac_descriptors_complete", int(registry["rac_descriptors_complete"].sum())),
    ]
    pd.DataFrame(summary_rows, columns=["metric", "value"]).to_csv(
        OUT / "registry_summary.csv", index=False
    )

    manifest = {
        "script": Path(__file__).name,
        "script_version": SCRIPT_VERSION,
        "registry_grain": "one row per canonical ARC-MOF geometry identifier",
        "canonicalization": "strip whitespace and repeated terminal .cif, _repeat, _sqe; preserve case",
        "outcome_values_read": False,
        "pairs_constructed": False,
        "eligibility_defined": False,
        "raw_directory_modified": False,
        "completed_successfully": True,
        "output_directory": str(OUT.relative_to(ROOT)),
    }
    (OUT / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    require_parquet_engine()

    missing_files = [name for name in REQUIRED_FILES if not (RAW / name).is_file()]
    if missing_files:
        raise FileNotFoundError(f"Missing required raw files: {missing_files}")

    id_audit_rows: list[dict[str, object]] = []
    collision_examples: list[dict[str, object]] = []
    coverage_rows: list[dict[str, object]] = []

    print("Project 17 Step 1.1: building framework registry")
    print("Policy: no outcome values, no pairs, no eligibility decisions")

    # 1. Geometry defines the registry universe and the ARC-MOF boundary.
    geometry = pd.read_csv(RAW / "geometric_properties.csv", low_memory=False)
    require_columns(
        geometry,
        ["filename", "ARC-MOF", "DB_num", *GEOMETRY_COLUMNS],
        "geometric_properties.csv",
    )
    geometry["geometry_filename_raw"] = geometry["filename"].astype("string")
    geometry["mof_id"] = canonicalize_ids(geometry["geometry_filename_raw"])
    add_id_audit(
        id_audit_rows,
        collision_examples,
        "geometric_properties.csv",
        geometry["geometry_filename_raw"],
        geometry["mof_id"],
    )
    require_unique_registry_key(geometry, "geometric_properties.csv")
    geometry["is_arc_mof"] = parse_arc_mof_flag(geometry["ARC-MOF"])

    for column in GEOMETRY_COLUMNS:
        original = geometry[column]
        converted = pd.to_numeric(original, errors="coerce")
        invalid = original.notna() & converted.isna()
        if invalid.any():
            examples = original.loc[invalid].astype(str).drop_duplicates().head(10).tolist()
            raise ValueError(f"Non-numeric values in geometry column {column}: {examples}")
        geometry[column] = converted

    exclusions = geometry.loc[
        ~geometry["is_arc_mof"], ["geometry_filename_raw", "mof_id"]
    ].copy()
    exclusions["exclusion_reason"] = "not_arc_mof_in_geometry_source"

    registry = geometry.loc[
        geometry["is_arc_mof"],
        ["mof_id", "geometry_filename_raw", "DB_num", *GEOMETRY_COLUMNS],
    ].copy()
    require_unique_registry_key(registry, "ARC-MOF geometry registry")
    registry_ids = set(registry["mof_id"].astype(str))
    coverage_rows.append(coverage_row("geometric_properties.csv:ARC-MOF", registry_ids, registry_ids))
    geometry_rows = len(geometry)
    del geometry
    gc.collect()

    # 2. Dimensionality is metadata, not a matching requirement at this stage.
    dimensionality = pd.read_csv(
        RAW / "ARC-MOF_Dim.csv",
        usecols=["Filename", "Dimensionality"],
        low_memory=False,
    )
    dimensionality["dimensionality_filename_raw"] = dimensionality["Filename"].astype("string")
    dimensionality["mof_id"] = canonicalize_ids(dimensionality["dimensionality_filename_raw"])
    add_id_audit(
        id_audit_rows,
        collision_examples,
        "ARC-MOF_Dim.csv",
        dimensionality["dimensionality_filename_raw"],
        dimensionality["mof_id"],
    )
    dimensionality = collapse_consistent_mapping(
        dimensionality,
        ["Dimensionality"],
        "ARC-MOF_Dim.csv",
    )
    dimensionality = dimensionality.rename(columns={"Dimensionality": "dimensionality"})
    dim_ids = set(dimensionality["mof_id"].astype(str))
    coverage_rows.append(coverage_row("ARC-MOF_Dim.csv", dim_ids, registry_ids))
    registry = registry.merge(
        dimensionality[["mof_id", "dimensionality_filename_raw", "dimensionality"]],
        on="mof_id",
        how="left",
        validate="one_to_one",
    )
    registry["has_dimensionality"] = registry["dimensionality_filename_raw"].notna()
    del dimensionality

    # 3. Topology labels are retained with their provenance fields.
    topology = pd.read_csv(
        RAW / "all_topology_lists.csv",
        usecols=["Name", "filename", "Crystalnet", "likely topology"],
        low_memory=False,
    )
    topology["topology_name_raw"] = topology["Name"].astype("string")
    topology["mof_id"] = canonicalize_ids(topology["topology_name_raw"])
    add_id_audit(
        id_audit_rows,
        collision_examples,
        "all_topology_lists.csv",
        topology["topology_name_raw"],
        topology["mof_id"],
    )
    topology = topology.rename(
        columns={
            "filename": "topology_source",
            "Crystalnet": "topology_crystalnet",
            "likely topology": "topology",
        }
    )
    topology = collapse_consistent_mapping(
        topology,
        ["topology", "topology_source", "topology_crystalnet"],
        "all_topology_lists.csv",
    )
    topology_ids = set(topology["mof_id"].astype(str))
    coverage_rows.append(coverage_row("all_topology_lists.csv", topology_ids, registry_ids))
    registry = registry.merge(
        topology[
            [
                "mof_id",
                "topology_name_raw",
                "topology",
                "topology_source",
                "topology_crystalnet",
            ]
        ],
        on="mof_id",
        how="left",
        validate="one_to_one",
    )
    registry["has_topology"] = registry["topology_name_raw"].notna()
    del topology

    # 4. Cluster labels are source features, not proof of chemical identity.
    cluster_presence_columns: list[str] = []
    for filename, output_column in CLUSTER_SOURCES:
        clusters = pd.read_csv(
            RAW / filename,
            usecols=["filename", "cluster_id"],
            low_memory=False,
        )
        raw_column = f"{output_column}_filename_raw"
        clusters[raw_column] = clusters["filename"].astype("string")
        clusters["mof_id"] = canonicalize_ids(clusters[raw_column])
        add_id_audit(
            id_audit_rows,
            collision_examples,
            filename,
            clusters[raw_column],
            clusters["mof_id"],
        )
        clusters = collapse_consistent_mapping(clusters, ["cluster_id"], filename)
        cluster_ids = set(clusters["mof_id"].astype(str))
        coverage_rows.append(coverage_row(filename, cluster_ids, registry_ids))
        registry = registry.merge(
            clusters[["mof_id", raw_column, "cluster_id"]].rename(
                columns={"cluster_id": output_column}
            ),
            on="mof_id",
            how="left",
            validate="one_to_one",
        )
        presence_column = f"has_{output_column}_label"
        registry[presence_column] = registry[raw_column].notna()
        cluster_presence_columns.append(presence_column)
        del clusters
    registry["has_all_cluster_labels"] = registry[cluster_presence_columns].all(axis=1)

    # 5. Retain every numeric RAC descriptor. Feature selection happens later.
    racs = pd.read_csv(RAW / "RACs.csv", low_memory=False)
    require_columns(racs, ["filename"], "RACs.csv")
    racs["rac_filename_raw"] = racs["filename"].astype("string")
    racs["mof_id"] = canonicalize_ids(racs["rac_filename_raw"])
    add_id_audit(
        id_audit_rows,
        collision_examples,
        "RACs.csv",
        racs["rac_filename_raw"],
        racs["mof_id"],
    )
    require_unique_registry_key(racs, "RACs.csv")

    rac_source_columns = [column for column in racs.columns if column not in RAC_METADATA | {"mof_id", "rac_filename_raw"}]
    if not rac_source_columns:
        raise RuntimeError("RACs.csv contains no descriptor columns")

    rac_audit_rows: list[dict[str, object]] = []
    rac_rename: dict[str, str] = {}
    for column in rac_source_columns:
        original = racs[column]
        converted = pd.to_numeric(original, errors="coerce")
        invalid = original.notna() & converted.isna()
        if invalid.any():
            examples = original.loc[invalid].astype(str).drop_duplicates().head(10).tolist()
            raise ValueError(f"Non-numeric values in RAC column {column}: {examples}")
        racs[column] = converted
        output_column = f"rac__{column}"
        rac_rename[column] = output_column
        rac_audit_rows.append(
            {
                "source_column": column,
                "registry_column": output_column,
                "source_nonmissing": int(converted.notna().sum()),
                "source_unique_nonmissing": int(converted.nunique(dropna=True)),
                "is_constant_in_source": converted.nunique(dropna=True) <= 1,
            }
        )
    racs = racs.rename(columns=rac_rename)
    rac_columns = list(rac_rename.values())
    rac_ids = set(racs["mof_id"].astype(str))
    coverage_rows.append(coverage_row("RACs.csv", rac_ids, registry_ids))
    registry = registry.merge(
        racs[["mof_id", "rac_filename_raw", *rac_columns]],
        on="mof_id",
        how="left",
        validate="one_to_one",
    )
    registry["has_rac_record"] = registry["rac_filename_raw"].notna()
    registry["rac_nonmissing_count"] = registry[rac_columns].notna().sum(axis=1)
    registry["rac_descriptors_complete"] = registry["rac_nonmissing_count"].eq(len(rac_columns))
    rac_audit = pd.DataFrame(rac_audit_rows)
    del racs
    gc.collect()

    # 6. Scan archive membership only. CIF chemistry is the next stage.
    cif_ids, cif_file_count = scan_cif_archive(
        RAW / ARCHIVE_NAME,
        id_audit_rows,
        collision_examples,
    )
    coverage_rows.append(coverage_row(ARCHIVE_NAME, cif_ids, registry_ids))
    registry["has_cif"] = registry["mof_id"].isin(cif_ids)

    # 7. Read only outcome-file identifiers and retain per-source availability.
    adsorption_union: set[str] = set()
    adsorption_presence_columns: list[str] = []
    for filename, presence_column in ADSORPTION_SOURCES:
        source_ids = scan_membership_csv(
            RAW / filename,
            id_audit_rows,
            collision_examples,
        )
        coverage_rows.append(coverage_row(filename, source_ids, registry_ids))
        registry[presence_column] = registry["mof_id"].isin(source_ids)
        adsorption_presence_columns.append(presence_column)
        adsorption_union.update(source_ids)
        del source_ids
        gc.collect()

    registry["adsorption_source_count"] = registry[adsorption_presence_columns].sum(axis=1)
    registry["has_any_adsorption_source"] = registry["adsorption_source_count"].gt(0)
    registry["has_all_adsorption_sources"] = registry["adsorption_source_count"].eq(
        len(adsorption_presence_columns)
    )

    process_ids = scan_membership_csv(
        RAW / "overall_process.csv",
        id_audit_rows,
        collision_examples,
    )
    coverage_rows.append(coverage_row("overall_process.csv", process_ids, registry_ids))
    registry["has_process_source"] = registry["mof_id"].isin(process_ids)

    # 8. Neutral completeness descriptors. These are not selection criteria.
    registry["geometry_nonmissing_count"] = registry[GEOMETRY_COLUMNS].notna().sum(axis=1)
    registry["geometry_descriptors_complete"] = registry["geometry_nonmissing_count"].eq(
        len(GEOMETRY_COLUMNS)
    )
    registry["positive_Df"] = registry["Df"].gt(0) & registry["Df"].notna()

    require_unique_registry_key(registry, "final framework registry")
    if len(registry) != len(registry_ids):
        raise RuntimeError("Registry row count changed during joins")

    observed_signatures = {
        "geometry_rows": geometry_rows,
        "arc_mof_geometry_rows": len(registry),
        "archive_cif_files": cif_file_count,
        "adsorption_union_overlap": len(adsorption_union & registry_ids),
        "adsorption_union_outside_registry": len(adsorption_union - registry_ids),
    }

    write_outputs(
        registry,
        exclusions,
        id_audit_rows,
        collision_examples,
        coverage_rows,
        rac_audit,
        observed_signatures,
    )

    signature_matches = {
        key: observed_signatures[key] == expected
        for key, expected in REFERENCE_SIGNATURES.items()
    }
    print(f"Registry rows: {len(registry):,}")
    print(f"RAC descriptors retained: {len(rac_columns):,}")
    print(f"CIF-covered registry rows: {int(registry['has_cif'].sum()):,}")
    print(f"Any-adsorption registry rows: {int(registry['has_any_adsorption_source'].sum()):,}")
    print(f"All reference signatures match: {all(signature_matches.values())}")
    if not all(signature_matches.values()):
        print("Reference mismatches:")
        for key, matches in signature_matches.items():
            if not matches:
                print(
                    f"  {key}: observed={observed_signatures[key]:,}; "
                    f"reference={REFERENCE_SIGNATURES[key]:,}"
                )
    print(f"Saved results: {OUT}")
    print("Stop here and audit these outputs before CIF chemistry extraction.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
