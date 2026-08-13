#!/usr/bin/env python3
"""
Project 17 Step 3.7: response archetypes across low- and high-pressure endpoints.

Uses only audited Step 3.6 outputs plus the frozen Step 2.3 pair catalogue
for topology metadata. No raw outcomes are read.

Each frozen pair has up to nine low-pressure and nine high-pressure mmol/g
endpoints (one low/high condition for each source+guest series).

A pair is "majority positive" within a pressure regime when strictly more than
half of its observed endpoint effects are positive.

Four deterministic archetypes:
    positive_both
        majority positive at low and high pressure

    pressure_activated
        not majority positive at low pressure,
        majority positive at high pressure

    pressure_suppressed
        majority positive at low pressure,
        not majority positive at high pressure

    negative_both
        not majority positive at low or high pressure

This is descriptive and does not alter any frozen analysis choice.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT_VERSION = "1.0.0"
DEFINITION_VERSION = "low_high_pressure_response_archetypes_v1"

ROOT = Path(__file__).resolve().parents[1]

CONSISTENCY_DIR = (
    ROOT
    / "Step 3 results"
    / "06_cross_condition_consistency"
)

MATRIX_PATH = CONSISTENCY_DIR / "mmolg_pair_endpoint_matrix.parquet"
META_PATH = CONSISTENCY_DIR / "mmolg_endpoint_metadata.csv"
CONSISTENCY_MANIFEST = CONSISTENCY_DIR / "run_manifest.json"

PAIR_PATH = (
    ROOT
    / "Step 2 results"
    / "03_geometry_pairs"
    / "primary_geometry_pairs.parquet"
)

OUTPUT_DIR = (
    ROOT
    / "Step 3 results"
    / "07_response_archetypes"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_csv(frame: pd.DataFrame, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    frame.to_csv(tmp, index=False)
    os.replace(tmp, path)


def atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    frame.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def atomic_write_text(text: str, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def classify_archetype(
    low_majority_positive: bool,
    high_majority_positive: bool,
) -> str:
    if low_majority_positive and high_majority_positive:
        return "positive_both"
    if (not low_majority_positive) and high_majority_positive:
        return "pressure_activated"
    if low_majority_positive and (not high_majority_positive):
        return "pressure_suppressed"
    return "negative_both"


def build_pressure_sets(
    metadata: pd.DataFrame,
) -> tuple[list[str], list[str], pd.DataFrame]:
    low_ids: list[str] = []
    high_ids: list[str] = []
    rows: list[dict[str, object]] = []

    for (source, guest), block in metadata.groupby(
        ["source", "guest"],
        sort=True,
    ):
        block = block.sort_values("pressure_bar")

        if len(block) != 2:
            raise RuntimeError(
                f"{source} / {guest} does not have exactly two pressure endpoints"
            )

        low = block.iloc[0]
        high = block.iloc[1]

        low_id = str(low["endpoint_id"])
        high_id = str(high["endpoint_id"])

        low_ids.append(low_id)
        high_ids.append(high_id)

        rows.append(
            {
                "source": source,
                "context": low["context"],
                "guest": guest,
                "temperature_K": float(low["temperature_K"]),
                "low_endpoint_id": low_id,
                "low_pressure_bar": float(low["pressure_bar"]),
                "high_endpoint_id": high_id,
                "high_pressure_bar": float(high["pressure_bar"]),
            }
        )

    return low_ids, high_ids, pd.DataFrame(rows)


def summarize_group(
    group: pd.DataFrame,
) -> dict[str, float | int]:
    n = len(group)

    return {
        "pairs": int(n),
        "median_activation_score": float(
            group["activation_score"].median()
        ),
        "mean_activation_score": float(
            group["activation_score"].mean()
        ),
        "primary_positive_fraction": float(
            group["primary_positive"].mean()
        ),
        "positive_both_fraction": float(
            group["archetype"].eq("positive_both").mean()
        ),
        "pressure_activated_fraction": float(
            group["archetype"].eq("pressure_activated").mean()
        ),
        "pressure_suppressed_fraction": float(
            group["archetype"].eq("pressure_suppressed").mean()
        ),
        "negative_both_fraction": float(
            group["archetype"].eq("negative_both").mean()
        ),
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    for path in (
        MATRIX_PATH,
        META_PATH,
        CONSISTENCY_MANIFEST,
        PAIR_PATH,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    consistency_manifest = json.loads(
        CONSISTENCY_MANIFEST.read_text(encoding="utf-8")
    )

    if consistency_manifest.get("completed_successfully") is not True:
        raise RuntimeError("Step 3.6 is not marked complete")
    if consistency_manifest.get("raw_outcome_files_read") is not False:
        raise RuntimeError("Step 3.6 provenance is not raw-outcome blind")
    if consistency_manifest.get("primary_endpoint_modified") is not False:
        raise RuntimeError("Step 3.6 modified the primary endpoint")

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
    metadata["temperature_K"] = pd.to_numeric(
        metadata["temperature_K"],
        errors="raise",
    )

    low_ids, high_ids, series_metadata = build_pressure_sets(metadata)

    if len(low_ids) != 9 or len(high_ids) != 9:
        raise RuntimeError(
            f"expected 9 low and 9 high endpoints, found "
            f"{len(low_ids)} low and {len(high_ids)} high"
        )

    primary_meta = metadata.loc[
        metadata["is_primary_endpoint"]
        .astype("boolean")
        .fillna(False)
    ]

    if len(primary_meta) != 1:
        raise RuntimeError("primary endpoint is not uniquely flagged")

    primary_id = str(primary_meta.iloc[0]["endpoint_id"])

    endpoint_matrix = matrix.set_index("architecture_group_id")

    missing_cols = (
        set(low_ids)
        | set(high_ids)
        | {primary_id}
    ) - set(endpoint_matrix.columns)

    if missing_cols:
        raise RuntimeError(
            f"pair-endpoint matrix missing endpoints: {sorted(missing_cols)}"
        )

    low = endpoint_matrix[low_ids].apply(
        pd.to_numeric,
        errors="coerce",
    )
    high = endpoint_matrix[high_ids].apply(
        pd.to_numeric,
        errors="coerce",
    )

    low_observed = low.notna().sum(axis=1)
    high_observed = high.notna().sum(axis=1)

    low_positive = low.gt(0).sum(axis=1)
    high_positive = high.gt(0).sum(axis=1)

    low_fraction = low_positive / low_observed
    high_fraction = high_positive / high_observed

    # Strict majority among observed endpoints.
    low_majority = low_positive > (low_observed / 2.0)
    high_majority = high_positive > (high_observed / 2.0)

    archetypes = [
        classify_archetype(bool(lo), bool(hi))
        for lo, hi in zip(low_majority, high_majority)
    ]

    primary_delta = pd.to_numeric(
        endpoint_matrix[primary_id],
        errors="coerce",
    )

    result = pd.DataFrame(
        {
            "architecture_group_id": endpoint_matrix.index.astype(str),
            "observed_low_pressure_endpoints": low_observed.to_numpy(dtype=int),
            "positive_low_pressure_endpoints": low_positive.to_numpy(dtype=int),
            "positive_fraction_low_pressure": low_fraction.to_numpy(dtype=float),
            "low_pressure_majority_positive": low_majority.to_numpy(dtype=bool),
            "observed_high_pressure_endpoints": high_observed.to_numpy(dtype=int),
            "positive_high_pressure_endpoints": high_positive.to_numpy(dtype=int),
            "positive_fraction_high_pressure": high_fraction.to_numpy(dtype=float),
            "high_pressure_majority_positive": high_majority.to_numpy(dtype=bool),
            "activation_score": (
                high_fraction - low_fraction
            ).to_numpy(dtype=float),
            "archetype": archetypes,
            "primary_delta_q_mmol_g": primary_delta.to_numpy(dtype=float),
            "primary_positive": primary_delta.gt(0).to_numpy(dtype=bool),
        }
    )

    result = result.merge(
        pairs,
        on="architecture_group_id",
        how="left",
        validate="one_to_one",
    )

    if result["topology"].isna().any():
        raise RuntimeError("missing topology after frozen-pair merge")
    if result["driver_descriptor"].isna().any():
        raise RuntimeError("missing driver descriptor after frozen-pair merge")

    archetype_order = [
        "positive_both",
        "pressure_activated",
        "pressure_suppressed",
        "negative_both",
    ]

    archetype_summary = (
        result["archetype"]
        .value_counts()
        .reindex(archetype_order, fill_value=0)
        .rename_axis("archetype")
        .reset_index(name="pairs")
    )
    archetype_summary["fraction"] = (
        archetype_summary["pairs"] / len(result)
    )

    driver_rows = []

    for driver, group in result.groupby(
        "driver_descriptor",
        sort=True,
    ):
        driver_rows.append(
            {
                "driver_descriptor": driver,
                **summarize_group(group),
            }
        )

    driver_summary = pd.DataFrame(driver_rows).sort_values(
        ["pairs", "driver_descriptor"],
        ascending=[False, True],
    ).reset_index(drop=True)

    topology_rows = []

    for topology, group in result.groupby(
        "topology",
        sort=True,
    ):
        topology_rows.append(
            {
                "topology": topology,
                **summarize_group(group),
            }
        )

    topology_summary = pd.DataFrame(topology_rows).sort_values(
        ["pairs", "topology"],
        ascending=[False, True],
    ).reset_index(drop=True)

    # Deterministic descriptive counterexample / archetype exemplars:
    # strongest absolute activation-score cases within each archetype.
    exemplar_blocks = []

    for archetype in archetype_order:
        block = result.loc[
            result["archetype"].eq(archetype)
        ].copy()

        block["abs_activation_score"] = (
            block["activation_score"].abs()
        )

        block = block.sort_values(
            [
                "abs_activation_score",
                "pair_max_fractional_difference",
                "architecture_group_id",
            ],
            ascending=[False, False, True],
        ).head(25)

        exemplar_blocks.append(block)

    exemplars = pd.concat(
        exemplar_blocks,
        ignore_index=True,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    atomic_write_parquet(
        result.sort_values("architecture_group_id").reset_index(drop=True),
        OUTPUT_DIR / "response_archetypes.parquet",
    )
    atomic_write_csv(
        archetype_summary,
        OUTPUT_DIR / "response_archetype_summary.csv",
    )
    atomic_write_csv(
        driver_summary,
        OUTPUT_DIR / "response_archetype_driver_summary.csv",
    )
    atomic_write_csv(
        topology_summary,
        OUTPUT_DIR / "response_archetype_topology_summary.csv",
    )
    atomic_write_csv(
        series_metadata,
        OUTPUT_DIR / "low_high_endpoint_series.csv",
    )
    atomic_write_csv(
        exemplars,
        OUTPUT_DIR / "response_archetype_exemplars.csv",
    )

    definition = {
        "definition_version": DEFINITION_VERSION,
        "source_pair_endpoint_matrix": str(
            MATRIX_PATH.relative_to(ROOT)
        ),
        "source_endpoint_metadata": str(
            META_PATH.relative_to(ROOT)
        ),
        "raw_outcome_files_read": False,
        "low_pressure_endpoints": low_ids,
        "high_pressure_endpoints": high_ids,
        "majority_rule": (
            "strictly more than half of observed endpoint effects are positive"
        ),
        "archetypes": {
            "positive_both": (
                "majority positive at both low and high pressure"
            ),
            "pressure_activated": (
                "not majority positive at low pressure; "
                "majority positive at high pressure"
            ),
            "pressure_suppressed": (
                "majority positive at low pressure; "
                "not majority positive at high pressure"
            ),
            "negative_both": (
                "not majority positive at either pressure regime"
            ),
        },
        "activation_score": (
            "positive_fraction_high_pressure - positive_fraction_low_pressure"
        ),
        "exemplar_rule": (
            "within each archetype, top 25 by absolute activation score; "
            "then larger frozen geometry contrast; then architecture_group_id"
        ),
        "pair_membership_modified": False,
        "pair_orientation_modified": False,
        "geometry_threshold_modified": False,
        "primary_endpoint_modified": False,
    }

    manifest = {
        "script": Path(__file__).name,
        "script_version": SCRIPT_VERSION,
        "definition_version": DEFINITION_VERSION,
        "completed_at_utc": utc_now(),
        "completed_successfully": True,
        "raw_outcome_files_read": False,
        "frozen_pairs": int(len(result)),
        "low_pressure_endpoint_count": int(len(low_ids)),
        "high_pressure_endpoint_count": int(len(high_ids)),
        "pair_membership_modified": False,
        "pair_orientation_modified": False,
        "geometry_threshold_modified": False,
        "primary_endpoint_modified": False,
    }

    atomic_write_text(
        json.dumps(definition, indent=2),
        OUTPUT_DIR / "response_archetype_definition.json",
    )
    atomic_write_text(
        json.dumps(manifest, indent=2),
        OUTPUT_DIR / "run_manifest.json",
    )

    print("PROJECT 17 - STEP 3.7 RESPONSE ARCHETYPES")
    print(
        "Policy: audited cross-condition matrix only; "
        "9 low-pressure + 9 high-pressure mmol/g endpoints"
    )
    print()

    print("ARCHETYPE CENSUS")
    print(archetype_summary.to_string(index=False))

    print()
    print("DRIVER SUMMARY")
    print(
        driver_summary[
            [
                "driver_descriptor",
                "pairs",
                "median_activation_score",
                "positive_both_fraction",
                "pressure_activated_fraction",
                "pressure_suppressed_fraction",
                "negative_both_fraction",
            ]
        ].to_string(index=False)
    )

    print()
    print("TOP TOPOLOGIES")
    print(
        topology_summary.head(12)[
            [
                "topology",
                "pairs",
                "median_activation_score",
                "pressure_activated_fraction",
                "positive_both_fraction",
                "negative_both_fraction",
            ]
        ].to_string(index=False)
    )

    print()
    print(f"Saved results: {OUTPUT_DIR}")
    print("Stop here and run py .\\test_13.py before Figure 4.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
