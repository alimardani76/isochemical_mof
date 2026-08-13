#!/usr/bin/env python3
"""
Project 17 Step 3.2: all-outcome condition and frozen-pair coverage census.

Purpose
-------
Before reading any adsorption/process outcome values, determine:
  - every available T/P condition in each adsorption table;
  - every available process label in overall_process.csv;
  - how many frozen primary geometry pairs have both members represented.

Only metadata columns are read:
  adsorption tables: filename, T/K, p/bar
  process table:     filename, process

No uptake, selectivity, working capacity, heat of adsorption, uncertainty,
purity, SSP, AFM, or other outcome values are read.

No endpoint is selected by this script.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


SCRIPT_VERSION = "1.0.0"
DEFINITION_VERSION = "all_outcome_condition_pair_coverage_v1"

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
PAIR_PATH = (
    ROOT
    / "Step 2 results"
    / "03_geometry_pairs"
    / "primary_geometry_pairs.parquet"
)
OUTPUT_DIR = (
    ROOT
    / "Step 3 results"
    / "02_all_outcome_condition_coverage"
)

ADSORPTION_FILES = [
    "methane.csv",
    "landfill-CH4.csv",
    "landfill-CO2.csv",
    "methane_purification-CH4.csv",
    "methane_purification-CO2.csv",
    "post_comb_vsa-CO2.csv",
    "post_comb_vsa-N2.csv",
    "pre_comb_4040-CO2.csv",
    "pre_comb_4040-H2.csv",
]

PROCESS_FILE = "overall_process.csv"

# Exact Stage 1.1 canonicalization rule:
# repeatedly remove terminal .cif, _repeat, or _sqe; preserve case/internal text.
SUFFIX_PATTERN = re.compile(r"(?i)(?:\.cif|_repeat|_sqe)$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonicalize_ids(values: pd.Series) -> pd.Series:
    result = values.astype("string").str.strip()
    result = result.mask(result.eq(""), pd.NA)

    for _ in range(4):
        updated = result.str.replace(SUFFIX_PATTERN, "", regex=True)
        if updated.equals(result):
            break
        result = updated

    result = result.str.strip()
    return result.mask(result.eq(""), pd.NA)


def atomic_write_csv(frame: pd.DataFrame, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    frame.to_csv(tmp, index=False)
    os.replace(tmp, path)


def atomic_write_text(text: str, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def pair_coverage(
    available_ids: set[str],
    pair_a: pd.Series,
    pair_b: pd.Series,
) -> dict[str, int | float]:
    a_present = pair_a.isin(available_ids)
    b_present = pair_b.isin(available_ids)

    complete = a_present & b_present
    exactly_one = a_present ^ b_present
    neither = ~(a_present | b_present)

    total_pairs = len(pair_a)

    return {
        "complete_pairs": int(complete.sum()),
        "exactly_one_member_pairs": int(exactly_one.sum()),
        "neither_member_pairs": int(neither.sum()),
        "complete_pair_fraction": (
            float(complete.mean()) if total_pairs else 0.0
        ),
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if not PAIR_PATH.is_file():
        raise FileNotFoundError(PAIR_PATH)

    for filename in [*ADSORPTION_FILES, PROCESS_FILE]:
        path = RAW / filename
        if not path.is_file():
            raise FileNotFoundError(path)

    pairs = pd.read_parquet(
        PAIR_PATH,
        columns=[
            "architecture_group_id",
            "mof_id_a",
            "mof_id_b",
        ],
    )

    pairs["architecture_group_id"] = pairs[
        "architecture_group_id"
    ].astype("string")
    pairs["mof_id_a"] = pairs["mof_id_a"].astype("string")
    pairs["mof_id_b"] = pairs["mof_id_b"].astype("string")

    if not pairs["architecture_group_id"].is_unique:
        raise RuntimeError("Frozen pair table is not one row per family")
    if pairs[["mof_id_a", "mof_id_b"]].isna().any().any():
        raise RuntimeError("Frozen pair table contains missing pair member IDs")

    pair_a = pairs["mof_id_a"]
    pair_b = pairs["mof_id_b"]
    frozen_member_ids = set(pair_a.astype(str)) | set(pair_b.astype(str))

    print("PROJECT 17 - STEP 3.2 ALL-OUTCOME CONDITION COVERAGE")
    print(
        "Policy: metadata only; adsorption = filename/T/p; "
        "process = filename/process; no outcome values"
    )
    print(f"Frozen primary pairs: {len(pairs):,}")
    print(f"Frozen pair members: {len(frozen_member_ids):,}")

    condition_rows: list[dict[str, object]] = []
    source_rows: list[dict[str, object]] = []

    for filename in ADSORPTION_FILES:
        path = RAW / filename

        frame = pd.read_csv(
            path,
            usecols=["filename", "T/K", "p/bar"],
            low_memory=False,
        )

        frame["mof_id"] = canonicalize_ids(frame["filename"])
        frame["T/K"] = pd.to_numeric(frame["T/K"], errors="raise")
        frame["p/bar"] = pd.to_numeric(frame["p/bar"], errors="raise")

        if frame["mof_id"].isna().any():
            raise RuntimeError(f"{filename} has blank/canonical-missing IDs")
        if frame[["T/K", "p/bar"]].isna().any().any():
            raise RuntimeError(f"{filename} has missing T/P metadata")

        unique_ids = set(frame["mof_id"].astype(str))
        overlap_ids = unique_ids & frozen_member_ids

        duplicate_rows = int(
            frame.duplicated(["mof_id", "T/K", "p/bar"]).sum()
        )

        source_rows.append(
            {
                "source": filename,
                "source_type": "adsorption",
                "rows_read": int(len(frame)),
                "unique_source_ids": int(frame["mof_id"].nunique()),
                "frozen_member_ids_present": int(len(overlap_ids)),
                "unique_conditions_or_processes": int(
                    frame[["T/K", "p/bar"]]
                    .drop_duplicates()
                    .shape[0]
                ),
                "duplicate_id_condition_rows": duplicate_rows,
            }
        )

        grouped = frame.groupby(
            ["T/K", "p/bar"],
            sort=True,
            dropna=False,
        )

        for (temperature, pressure), group in grouped:
            ids = set(group["mof_id"].astype(str))
            coverage = pair_coverage(ids, pair_a, pair_b)

            condition_rows.append(
                {
                    "source": filename,
                    "source_type": "adsorption",
                    "condition_label": (
                        f"T={float(temperature):g} K; "
                        f"p={float(pressure):g} bar"
                    ),
                    "temperature_K": float(temperature),
                    "pressure_bar": float(pressure),
                    "process": pd.NA,
                    "rows": int(len(group)),
                    "unique_source_ids": int(group["mof_id"].nunique()),
                    "frozen_member_ids_present": int(
                        len(ids & frozen_member_ids)
                    ),
                    **coverage,
                }
            )

    # overall_process.csv: metadata-only process labels.
    process_frame = pd.read_csv(
        RAW / PROCESS_FILE,
        usecols=["filename", "process"],
        low_memory=False,
    )

    process_frame["mof_id"] = canonicalize_ids(process_frame["filename"])
    process_frame["process"] = (
        process_frame["process"]
        .astype("string")
        .str.strip()
    )

    if process_frame["mof_id"].isna().any():
        raise RuntimeError("overall_process.csv has blank/canonical-missing IDs")
    if process_frame["process"].isna().any() or process_frame["process"].eq("").any():
        raise RuntimeError("overall_process.csv has missing/blank process labels")

    process_unique_ids = set(process_frame["mof_id"].astype(str))

    source_rows.append(
        {
            "source": PROCESS_FILE,
            "source_type": "process",
            "rows_read": int(len(process_frame)),
            "unique_source_ids": int(process_frame["mof_id"].nunique()),
            "frozen_member_ids_present": int(
                len(process_unique_ids & frozen_member_ids)
            ),
            "unique_conditions_or_processes": int(
                process_frame["process"].nunique()
            ),
            "duplicate_id_condition_rows": int(
                process_frame.duplicated(["mof_id", "process"]).sum()
            ),
        }
    )

    for process, group in process_frame.groupby(
        "process",
        sort=True,
        dropna=False,
    ):
        ids = set(group["mof_id"].astype(str))
        coverage = pair_coverage(ids, pair_a, pair_b)

        condition_rows.append(
            {
                "source": PROCESS_FILE,
                "source_type": "process",
                "condition_label": str(process),
                "temperature_K": pd.NA,
                "pressure_bar": pd.NA,
                "process": str(process),
                "rows": int(len(group)),
                "unique_source_ids": int(group["mof_id"].nunique()),
                "frozen_member_ids_present": int(
                    len(ids & frozen_member_ids)
                ),
                **coverage,
            }
        )

    condition_census = pd.DataFrame(condition_rows)
    source_census = pd.DataFrame(source_rows)

    condition_census = condition_census.sort_values(
        [
            "complete_pairs",
            "source_type",
            "source",
            "temperature_K",
            "pressure_bar",
            "condition_label",
        ],
        ascending=[False, True, True, True, True, True],
        na_position="last",
    ).reset_index(drop=True)

    source_census = source_census.sort_values(
        ["source_type", "source"]
    ).reset_index(drop=True)

    # Compact table for choosing Figure 2 / Figure 3 endpoints by support.
    ranked = condition_census[
        [
            "source",
            "source_type",
            "condition_label",
            "temperature_K",
            "pressure_bar",
            "process",
            "frozen_member_ids_present",
            "complete_pairs",
            "complete_pair_fraction",
            "exactly_one_member_pairs",
            "neither_member_pairs",
        ]
    ].copy()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    atomic_write_csv(
        source_census,
        OUTPUT_DIR / "outcome_source_metadata_census.csv",
    )
    atomic_write_csv(
        condition_census,
        OUTPUT_DIR / "outcome_condition_pair_coverage.csv",
    )
    atomic_write_csv(
        ranked,
        OUTPUT_DIR / "outcome_endpoint_support_ranking.csv",
    )

    definition = {
        "definition_version": DEFINITION_VERSION,
        "frozen_pair_source": str(PAIR_PATH.relative_to(ROOT)),
        "frozen_primary_pairs": int(len(pairs)),
        "frozen_pair_members": int(len(frozen_member_ids)),
        "adsorption_sources": ADSORPTION_FILES,
        "process_source": PROCESS_FILE,
        "columns_read": {
            "adsorption": ["filename", "T/K", "p/bar"],
            "process": ["filename", "process"],
        },
        "id_canonicalization": (
            "strip whitespace and repeated terminal .cif, _repeat, _sqe; "
            "preserve case and internal text"
        ),
        "outcome_values_read": False,
        "endpoint_selected": False,
        "pair_membership_modified": False,
        "purpose": (
            "freeze endpoint choice from scientific relevance and frozen-pair "
            "support before inspecting any adsorption/process values"
        ),
    }

    atomic_write_text(
        json.dumps(definition, indent=2),
        OUTPUT_DIR / "outcome_condition_coverage_definition.json",
    )

    manifest = {
        "script": Path(__file__).name,
        "script_version": SCRIPT_VERSION,
        "definition_version": DEFINITION_VERSION,
        "completed_at_utc": utc_now(),
        "completed_successfully": True,
        "metadata_only": True,
        "outcome_values_read": False,
        "endpoint_selected": False,
        "pair_membership_modified": False,
        "frozen_primary_pairs": int(len(pairs)),
        "frozen_pair_members": int(len(frozen_member_ids)),
        "output_directory": str(OUTPUT_DIR.relative_to(ROOT)),
    }

    atomic_write_text(
        json.dumps(manifest, indent=2),
        OUTPUT_DIR / "run_manifest.json",
    )

    print()
    print("SOURCE METADATA CENSUS")
    print(source_census.to_string(index=False))

    print()
    print("ENDPOINT SUPPORT RANKING")
    display = ranked.copy()
    display["complete_pair_fraction"] = (
        100.0 * display["complete_pair_fraction"]
    )
    display = display.rename(
        columns={"complete_pair_fraction": "complete_pair_pct"}
    )
    print(display.to_string(index=False))

    print()
    print(f"Saved results: {OUTPUT_DIR}")
    print(
        "Stop here and run py .\\test_08.py. "
        "Do not read outcome values or select an endpoint until the audit passes."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
