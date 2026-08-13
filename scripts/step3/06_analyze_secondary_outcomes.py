#!/usr/bin/env python3
"""
Project 17 Step 3.5: secondary adsorption and process outcome atlas.

Scope
-----
Uses the already-frozen Step 2.3 geometry pairs and the already-frozen
driver_low_mof_id -> driver_high_mof_id orientation.

Reads all prespecified SECONDARY outcome tables only after the primary endpoint
(CH4, 298 K, 65 bar, mmol/g) was frozen and analyzed.

Adsorption metrics retained:
    mmol/g
    v/v
    wt%
    hoa/kcal/mol
    S(g1) where available

Process metrics retained:
    mmol/g_uptake
    mmol/g_working_capacity
    v/v_uptake
    v/v_working_capacity
    wt%_uptake
    wt%_working_capacity
    selectivity
    purity
    ssp
    afm

For every endpoint:
    delta = value_geometry_high - value_geometry_low
    symmetric relative effect =
        2*(high-low)/(abs(high)+abs(low)), or 0 when both are zero

This is a secondary/exploratory atlas.
It does not change the primary endpoint, pair membership, geometry threshold,
or pair orientation.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT_VERSION = "1.0.0"
DEFINITION_VERSION = "secondary_outcome_atlas_v1"

ROOT = Path(__file__).resolve().parents[1]

PAIR_PATH = (
    ROOT
    / "Step 2 results"
    / "03_geometry_pairs"
    / "primary_geometry_pairs.parquet"
)

PRIMARY_FREEZE = (
    ROOT
    / "Step 3 results"
    / "03_primary_endpoint_freeze"
    / "primary_endpoint_definition.json"
)

PRIMARY_ANALYSIS_MANIFEST = (
    ROOT
    / "Step 3 results"
    / "04_primary_ch4_analysis"
    / "run_manifest.json"
)

RAW = ROOT / "raw"

OUTPUT_DIR = (
    ROOT
    / "Step 3 results"
    / "05_secondary_outcome_atlas"
)

ADSORPTION_SOURCES = {
    "methane.csv": {
        "context": "methane-storage",
        "guest": "CH4",
    },
    "landfill-CH4.csv": {
        "context": "landfill-gas",
        "guest": "CH4",
    },
    "landfill-CO2.csv": {
        "context": "landfill-gas",
        "guest": "CO2",
    },
    "methane_purification-CH4.csv": {
        "context": "natural-gas-purification",
        "guest": "CH4",
    },
    "methane_purification-CO2.csv": {
        "context": "natural-gas-purification",
        "guest": "CO2",
    },
    "post_comb_vsa-CO2.csv": {
        "context": "post-combustion-vsa",
        "guest": "CO2",
    },
    "post_comb_vsa-N2.csv": {
        "context": "post-combustion-vsa",
        "guest": "N2",
    },
    "pre_comb_4040-CO2.csv": {
        "context": "pre-combustion-40-40",
        "guest": "CO2",
    },
    "pre_comb_4040-H2.csv": {
        "context": "pre-combustion-40-40",
        "guest": "H2",
    },
}

ADSORPTION_METRICS = {
    "mmol/g": "mmol/g",
    "v/v": "v/v",
    "wt%": "wt%",
    "hoa/kcal/mol": "kcal/mol",
    "S(g1)": "dimensionless",
}

PROCESS_FILE = "overall_process.csv"

PROCESS_METRICS = {
    "mmol/g_uptake": "mmol/g",
    "mmol/g_working_capacity": "mmol/g",
    "v/v_uptake": "v/v",
    "v/v_working_capacity": "v/v",
    "wt%_uptake": "wt%",
    "wt%_working_capacity": "wt%",
    "selectivity": "dimensionless",
    "purity": "dimensionless",
    "ssp": "source-defined",
    "afm": "source-defined",
}

PRIMARY_ENDPOINT_KEY = (
    "methane.csv",
    298.0,
    65.0,
    "mmol/g",
)

SUFFIX_PATTERN = re.compile(r"(?i)(?:\.cif|_repeat|_sqe)$")


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


def symmetric_relative_effect(
    high: np.ndarray,
    low: np.ndarray,
) -> np.ndarray:
    denominator = np.abs(high) + np.abs(low)
    numerator = 2.0 * (high - low)
    return np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator, dtype=float),
        where=denominator != 0,
    )


def pair_effect_table(
    pairs: pd.DataFrame,
    lookup: pd.Series,
    *,
    source: str,
    source_type: str,
    context: str,
    guest: str | None,
    temperature_K: float | None,
    pressure_bar: float | None,
    process: str | None,
    metric: str,
    unit: str,
    is_primary_endpoint: bool,
) -> pd.DataFrame:
    out = pairs[
        [
            "architecture_group_id",
            "source_chemistry_group_id",
            "topology",
            "dimensionality",
            "driver_descriptor",
            "driver_low_mof_id",
            "driver_high_mof_id",
            "pair_max_fractional_difference",
            "pair_mean_fractional_difference",
            "primary_10pct_pair",
            "sensitivity_20pct_pair",
            "sensitivity_30pct_pair",
        ]
    ].copy()

    out["value_geometry_low"] = (
        out["driver_low_mof_id"].map(lookup)
    )
    out["value_geometry_high"] = (
        out["driver_high_mof_id"].map(lookup)
    )

    out["complete_pair"] = (
        out["value_geometry_low"].notna()
        & out["value_geometry_high"].notna()
    )

    out = out.loc[out["complete_pair"]].copy()

    low = out["value_geometry_low"].to_numpy(dtype=float)
    high = out["value_geometry_high"].to_numpy(dtype=float)

    out["delta"] = high - low
    out["symmetric_relative_effect"] = (
        symmetric_relative_effect(high, low)
    )

    out.insert(0, "source", source)
    out.insert(1, "source_type", source_type)
    out.insert(2, "context", context)
    out.insert(3, "guest", guest)
    out.insert(4, "temperature_K", temperature_K)
    out.insert(5, "pressure_bar", pressure_bar)
    out.insert(6, "process", process)
    out.insert(7, "metric", metric)
    out.insert(8, "unit", unit)
    out.insert(9, "is_primary_endpoint", is_primary_endpoint)

    return out


def summarize_effects(frame: pd.DataFrame) -> dict[str, object]:
    delta = frame["delta"].to_numpy(dtype=float)
    relative = frame["symmetric_relative_effect"].to_numpy(dtype=float)

    return {
        "complete_pairs": int(len(frame)),
        "median_delta": float(np.median(delta)) if len(delta) else np.nan,
        "mean_delta": float(np.mean(delta)) if len(delta) else np.nan,
        "q25_delta": float(np.quantile(delta, 0.25)) if len(delta) else np.nan,
        "q75_delta": float(np.quantile(delta, 0.75)) if len(delta) else np.nan,
        "positive_effect_fraction": (
            float(np.mean(delta > 0)) if len(delta) else np.nan
        ),
        "negative_effect_fraction": (
            float(np.mean(delta < 0)) if len(delta) else np.nan
        ),
        "median_symmetric_relative_effect": (
            float(np.median(relative)) if len(relative) else np.nan
        ),
    }


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


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    for path in (
        PAIR_PATH,
        PRIMARY_FREEZE,
        PRIMARY_ANALYSIS_MANIFEST,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    for filename in [*ADSORPTION_SOURCES.keys(), PROCESS_FILE]:
        if not (RAW / filename).is_file():
            raise FileNotFoundError(RAW / filename)

    freeze = json.loads(
        PRIMARY_FREEZE.read_text(encoding="utf-8")
    )
    primary_manifest = json.loads(
        PRIMARY_ANALYSIS_MANIFEST.read_text(encoding="utf-8")
    )

    if freeze.get("endpoint_switching_after_value_access_allowed") is not False:
        raise RuntimeError("primary freeze policy is not intact")
    if primary_manifest.get("completed_successfully") is not True:
        raise RuntimeError("primary outcome analysis is not complete")
    if primary_manifest.get("primary_endpoint_modified") is not False:
        raise RuntimeError("primary endpoint provenance was modified")

    pairs = pd.read_parquet(PAIR_PATH)

    required_pairs = {
        "architecture_group_id",
        "source_chemistry_group_id",
        "topology",
        "dimensionality",
        "driver_descriptor",
        "driver_low_mof_id",
        "driver_high_mof_id",
        "pair_max_fractional_difference",
        "pair_mean_fractional_difference",
        "primary_10pct_pair",
        "sensitivity_20pct_pair",
        "sensitivity_30pct_pair",
    }
    missing = required_pairs - set(pairs.columns)
    if missing:
        raise ValueError(
            f"pair table missing columns: {sorted(missing)}"
        )

    for column in (
        "architecture_group_id",
        "driver_low_mof_id",
        "driver_high_mof_id",
    ):
        pairs[column] = pairs[column].astype("string")

    print("PROJECT 17 - STEP 3.5 SECONDARY OUTCOME ATLAS")
    print(
        "Policy: frozen pair IDs/orientation; primary endpoint unchanged; "
        "remaining outcomes are secondary/exploratory"
    )
    print(f"Frozen primary pairs: {len(pairs):,}")

    adsorption_effect_blocks: list[pd.DataFrame] = []
    adsorption_summary_rows: list[dict[str, object]] = []

    for filename, meta in ADSORPTION_SOURCES.items():
        path = RAW / filename

        header = pd.read_csv(path, nrows=0).columns.tolist()

        metrics_present = [
            metric
            for metric in ADSORPTION_METRICS
            if metric in header
        ]

        usecols = [
            "filename",
            "T/K",
            "p/bar",
            *metrics_present,
        ]

        frame = pd.read_csv(
            path,
            usecols=usecols,
            low_memory=False,
        )

        frame["mof_id"] = canonicalize_ids(frame["filename"])
        frame["T/K"] = pd.to_numeric(frame["T/K"], errors="raise")
        frame["p/bar"] = pd.to_numeric(frame["p/bar"], errors="raise")

        if frame["mof_id"].isna().any():
            raise RuntimeError(
                f"{filename} contains missing canonical IDs"
            )

        for metric in metrics_present:
            frame[metric] = pd.to_numeric(
                frame[metric],
                errors="coerce",
            )

        for (temperature, pressure), condition in frame.groupby(
            ["T/K", "p/bar"],
            sort=True,
            dropna=False,
        ):
            if condition["mof_id"].duplicated().any():
                raise RuntimeError(
                    f"{filename}, T={temperature}, p={pressure}: "
                    "duplicate canonical IDs"
                )

            for metric in metrics_present:
                lookup = condition.set_index("mof_id")[metric]

                is_primary = (
                    filename,
                    float(temperature),
                    float(pressure),
                    metric,
                ) == PRIMARY_ENDPOINT_KEY

                effect = pair_effect_table(
                    pairs,
                    lookup,
                    source=filename,
                    source_type="adsorption",
                    context=meta["context"],
                    guest=meta["guest"],
                    temperature_K=float(temperature),
                    pressure_bar=float(pressure),
                    process=None,
                    metric=metric,
                    unit=ADSORPTION_METRICS[metric],
                    is_primary_endpoint=is_primary,
                )

                adsorption_effect_blocks.append(effect)

                row = {
                    "source": filename,
                    "source_type": "adsorption",
                    "context": meta["context"],
                    "guest": meta["guest"],
                    "temperature_K": float(temperature),
                    "pressure_bar": float(pressure),
                    "process": pd.NA,
                    "metric": metric,
                    "unit": ADSORPTION_METRICS[metric],
                    "is_primary_endpoint": is_primary,
                    **summarize_effects(effect),
                }
                adsorption_summary_rows.append(row)

    adsorption_effects = pd.concat(
        adsorption_effect_blocks,
        ignore_index=True,
    )
    adsorption_summary = pd.DataFrame(
        adsorption_summary_rows
    )

    # Process outcomes
    process_path = RAW / PROCESS_FILE
    process_header = pd.read_csv(
        process_path,
        nrows=0,
    ).columns.tolist()

    process_metrics_present = [
        metric
        for metric in PROCESS_METRICS
        if metric in process_header
    ]

    process_frame = pd.read_csv(
        process_path,
        usecols=[
            "filename",
            "process",
            *process_metrics_present,
        ],
        low_memory=False,
    )

    process_frame["mof_id"] = canonicalize_ids(
        process_frame["filename"]
    )
    process_frame["process"] = (
        process_frame["process"]
        .astype("string")
        .str.strip()
    )

    if process_frame["mof_id"].isna().any():
        raise RuntimeError(
            "overall_process.csv contains missing canonical IDs"
        )
    if process_frame["process"].isna().any():
        raise RuntimeError(
            "overall_process.csv contains missing process labels"
        )

    for metric in process_metrics_present:
        process_frame[metric] = pd.to_numeric(
            process_frame[metric],
            errors="coerce",
        )

    process_effect_blocks: list[pd.DataFrame] = []
    process_summary_rows: list[dict[str, object]] = []

    for process_name, condition in process_frame.groupby(
        "process",
        sort=True,
        dropna=False,
    ):
        if condition["mof_id"].duplicated().any():
            raise RuntimeError(
                f"process {process_name}: duplicate canonical IDs"
            )

        for metric in process_metrics_present:
            lookup = condition.set_index("mof_id")[metric]

            effect = pair_effect_table(
                pairs,
                lookup,
                source=PROCESS_FILE,
                source_type="process",
                context=str(process_name),
                guest=None,
                temperature_K=None,
                pressure_bar=None,
                process=str(process_name),
                metric=metric,
                unit=PROCESS_METRICS[metric],
                is_primary_endpoint=False,
            )

            process_effect_blocks.append(effect)

            process_summary_rows.append(
                {
                    "source": PROCESS_FILE,
                    "source_type": "process",
                    "context": str(process_name),
                    "guest": pd.NA,
                    "temperature_K": pd.NA,
                    "pressure_bar": pd.NA,
                    "process": str(process_name),
                    "metric": metric,
                    "unit": PROCESS_METRICS[metric],
                    "is_primary_endpoint": False,
                    **summarize_effects(effect),
                }
            )

    process_effects = pd.concat(
        process_effect_blocks,
        ignore_index=True,
    )
    process_summary = pd.DataFrame(
        process_summary_rows
    )

    # Compact mmol/g adsorption table for Figure 3 gas/pressure panels.
    adsorption_mmolg = adsorption_summary.loc[
        adsorption_summary["metric"].eq("mmol/g")
    ].copy()

    # Compact process table focused on later Figure 3 application panels.
    process_key_metrics = process_summary.loc[
        process_summary["metric"].isin(
            [
                "mmol/g_working_capacity",
                "selectivity",
                "purity",
                "ssp",
                "afm",
            ]
        )
    ].copy()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    atomic_write_parquet(
        adsorption_effects,
        OUTPUT_DIR / "secondary_adsorption_pair_effects.parquet",
    )
    atomic_write_csv(
        adsorption_summary.sort_values(
            [
                "context",
                "guest",
                "temperature_K",
                "pressure_bar",
                "metric",
            ],
            na_position="last",
        ).reset_index(drop=True),
        OUTPUT_DIR / "secondary_adsorption_summary.csv",
    )
    atomic_write_csv(
        adsorption_mmolg.sort_values(
            [
                "context",
                "guest",
                "temperature_K",
                "pressure_bar",
            ],
            na_position="last",
        ).reset_index(drop=True),
        OUTPUT_DIR / "secondary_adsorption_mmolg_summary.csv",
    )

    atomic_write_parquet(
        process_effects,
        OUTPUT_DIR / "secondary_process_pair_effects.parquet",
    )
    atomic_write_csv(
        process_summary.sort_values(
            ["process", "metric"]
        ).reset_index(drop=True),
        OUTPUT_DIR / "secondary_process_summary.csv",
    )
    atomic_write_csv(
        process_key_metrics.sort_values(
            ["process", "metric"]
        ).reset_index(drop=True),
        OUTPUT_DIR / "secondary_process_key_metrics.csv",
    )

    definition = {
        "definition_version": DEFINITION_VERSION,
        "analysis_status": "secondary_exploratory",
        "frozen_pair_orientation": (
            "driver_low_mof_id -> driver_high_mof_id"
        ),
        "pair_effect": "value_geometry_high - value_geometry_low",
        "symmetric_relative_effect": (
            "2*(high-low)/(abs(high)+abs(low)); 0 when both are zero"
        ),
        "adsorption_sources": ADSORPTION_SOURCES,
        "adsorption_metrics": ADSORPTION_METRICS,
        "process_source": PROCESS_FILE,
        "process_metrics": PROCESS_METRICS,
        "primary_endpoint_preserved": {
            "source": "methane.csv",
            "temperature_K": 298.0,
            "pressure_bar": 65.0,
            "metric": "mmol/g",
        },
        "no_secondary_endpoint_promoted_to_primary": True,
        "pair_membership_modified": False,
        "pair_orientation_modified": False,
        "geometry_threshold_modified": False,
    }

    atomic_write_text(
        json.dumps(definition, indent=2),
        OUTPUT_DIR / "secondary_outcome_atlas_definition.json",
    )

    manifest = {
        "script": Path(__file__).name,
        "script_version": SCRIPT_VERSION,
        "definition_version": DEFINITION_VERSION,
        "completed_at_utc": utc_now(),
        "completed_successfully": True,
        "pair_source_sha256": sha256_file(PAIR_PATH),
        "primary_freeze_sha256": sha256_file(PRIMARY_FREEZE),
        "primary_analysis_manifest_sha256": sha256_file(
            PRIMARY_ANALYSIS_MANIFEST
        ),
        "secondary_outcomes_read": True,
        "primary_endpoint_modified": False,
        "pair_membership_modified": False,
        "pair_orientation_modified": False,
        "geometry_threshold_modified": False,
        "no_secondary_endpoint_promoted_to_primary": True,
    }

    atomic_write_text(
        json.dumps(manifest, indent=2),
        OUTPUT_DIR / "run_manifest.json",
    )

    print()
    print("ADSORPTION MMOL/G SUMMARY")
    print(
        adsorption_mmolg[
            [
                "context",
                "guest",
                "temperature_K",
                "pressure_bar",
                "is_primary_endpoint",
                "complete_pairs",
                "median_delta",
                "positive_effect_fraction",
                "median_symmetric_relative_effect",
            ]
        ].to_string(index=False)
    )

    print()
    print("PROCESS KEY METRICS")
    print(
        process_key_metrics[
            [
                "process",
                "metric",
                "complete_pairs",
                "median_delta",
                "positive_effect_fraction",
                "median_symmetric_relative_effect",
            ]
        ].to_string(index=False)
    )

    print()
    print(f"Saved results: {OUTPUT_DIR}")
    print(
        "Stop here and run py .\\test_11.py before building Figure 3."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
