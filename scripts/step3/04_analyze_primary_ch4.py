#!/usr/bin/env python3
"""
Project 17 Step 3.4: primary CH4 outcome analysis.

Frozen primary endpoint
-----------------------
Source: methane.csv
Guest: CH4
T = 298 K
p = 65 bar
Outcome = mmol/g

Frozen pair orientation
-----------------------
Use Step 2.3 driver_low_mof_id -> driver_high_mof_id.
No pair membership, geometry threshold, driver descriptor, or endpoint is changed.

Primary pair effect
-------------------
delta_q = q_geometry_high - q_geometry_low  [mmol/g]

Primary population estimator
----------------------------
median(delta_q)

Primary uncertainty
-------------------
10,000-replicate nonparametric bootstrap of whole frozen families,
seed = 17, percentile 95% CI.

This script reads NO other outcome table and NO other outcome column.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT_VERSION = "1.0.0"
DEFINITION_VERSION = "primary_ch4_298K_65bar_mmolg_v1"

ROOT = Path(__file__).resolve().parents[1]

PAIR_PATH = (
    ROOT
    / "Step 2 results"
    / "03_geometry_pairs"
    / "primary_geometry_pairs.parquet"
)

FREEZE_DIR = (
    ROOT
    / "Step 3 results"
    / "03_primary_endpoint_freeze"
)
FREEZE_DEFINITION = FREEZE_DIR / "primary_endpoint_definition.json"
FREEZE_MANIFEST = FREEZE_DIR / "run_manifest.json"

METHANE_PATH = ROOT / "raw" / "methane.csv"

OUTPUT_DIR = (
    ROOT
    / "Step 3 results"
    / "04_primary_ch4_analysis"
)

TEMPERATURE_K = 298.0
PRESSURE_BAR = 65.0
OUTCOME_COLUMN = "mmol/g"

BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 17
BOOTSTRAP_CHUNK = 250

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


def symmetric_relative_effect(q_high: np.ndarray, q_low: np.ndarray) -> np.ndarray:
    denominator = np.abs(q_high) + np.abs(q_low)
    numerator = 2.0 * (q_high - q_low)
    return np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator, dtype=float),
        where=denominator != 0,
    )


def bootstrap_median_ci(
    values: np.ndarray,
    replicates: int,
    seed: int,
    chunk_size: int,
) -> tuple[float, float, np.ndarray]:
    if values.ndim != 1:
        raise ValueError("bootstrap values must be one-dimensional")
    if len(values) == 0:
        raise ValueError("cannot bootstrap empty values")

    rng = np.random.default_rng(seed)
    n = len(values)
    medians = np.empty(replicates, dtype=float)

    written = 0
    while written < replicates:
        k = min(chunk_size, replicates - written)
        indices = rng.integers(
            0,
            n,
            size=(k, n),
            endpoint=False,
        )
        samples = values[indices]
        medians[written:written + k] = np.median(samples, axis=1)
        written += k

    low, high = np.percentile(medians, [2.5, 97.5])
    return float(low), float(high), medians


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
        FREEZE_DEFINITION,
        FREEZE_MANIFEST,
        METHANE_PATH,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    freeze_definition = json.loads(
        FREEZE_DEFINITION.read_text(encoding="utf-8")
    )
    freeze_manifest = json.loads(
        FREEZE_MANIFEST.read_text(encoding="utf-8")
    )

    primary = freeze_definition.get("primary_endpoint", {})
    summary_rule = freeze_definition.get("primary_population_summary", {})

    if freeze_manifest.get("completed_successfully") is not True:
        raise RuntimeError("Step 3.3 freeze is not marked complete")
    if freeze_manifest.get("primary_endpoint_frozen") is not True:
        raise RuntimeError("primary endpoint is not frozen")
    if primary.get("source") != "methane.csv":
        raise RuntimeError("frozen primary source is not methane.csv")
    if float(primary.get("temperature_K")) != TEMPERATURE_K:
        raise RuntimeError("frozen primary temperature is not 298 K")
    if float(primary.get("pressure_bar")) != PRESSURE_BAR:
        raise RuntimeError("frozen primary pressure is not 65 bar")
    if primary.get("uptake_column") != OUTCOME_COLUMN:
        raise RuntimeError("frozen uptake basis is not mmol/g")
    if int(summary_rule.get("bootstrap_replicates")) != BOOTSTRAP_REPLICATES:
        raise RuntimeError("frozen bootstrap replicate count mismatch")
    if int(summary_rule.get("bootstrap_seed")) != BOOTSTRAP_SEED:
        raise RuntimeError("frozen bootstrap seed mismatch")

    pairs = pd.read_parquet(PAIR_PATH)

    required_pair_columns = {
        "architecture_group_id",
        "source_chemistry_group_id",
        "topology",
        "dimensionality",
        "family_size",
        "mof_id_a",
        "mof_id_b",
        "driver_descriptor",
        "driver_low_mof_id",
        "driver_high_mof_id",
        "pair_max_fractional_difference",
        "pair_mean_fractional_difference",
        "primary_10pct_pair",
        "sensitivity_20pct_pair",
        "sensitivity_30pct_pair",
    }
    missing = required_pair_columns - set(pairs.columns)
    if missing:
        raise ValueError(
            f"primary pair table missing columns: {sorted(missing)}"
        )

    pairs["architecture_group_id"] = pairs[
        "architecture_group_id"
    ].astype("string")
    for col in (
        "mof_id_a",
        "mof_id_b",
        "driver_low_mof_id",
        "driver_high_mof_id",
    ):
        pairs[col] = pairs[col].astype("string")

    if not pairs["architecture_group_id"].is_unique:
        raise RuntimeError("pair table is not one row per family")

    # Read only the frozen primary outcome and the metadata needed to select it.
    methane = pd.read_csv(
        METHANE_PATH,
        usecols=["filename", "T/K", "p/bar", OUTCOME_COLUMN],
        low_memory=False,
    )

    methane["mof_id"] = canonicalize_ids(methane["filename"])
    methane["T/K"] = pd.to_numeric(methane["T/K"], errors="raise")
    methane["p/bar"] = pd.to_numeric(methane["p/bar"], errors="raise")
    methane[OUTCOME_COLUMN] = pd.to_numeric(
        methane[OUTCOME_COLUMN],
        errors="coerce",
    )

    primary_rows = methane.loc[
        methane["T/K"].eq(TEMPERATURE_K)
        & methane["p/bar"].eq(PRESSURE_BAR),
        ["mof_id", OUTCOME_COLUMN],
    ].copy()

    if primary_rows["mof_id"].isna().any():
        raise RuntimeError("primary methane rows contain missing canonical IDs")

    duplicates = primary_rows.duplicated("mof_id", keep=False)
    if duplicates.any():
        duplicate_ids = (
            primary_rows.loc[duplicates, "mof_id"]
            .astype(str)
            .unique()
            .tolist()
        )
        raise RuntimeError(
            f"duplicate primary methane rows after canonicalization: "
            f"{duplicate_ids[:10]}"
        )

    outcome_by_id = primary_rows.set_index("mof_id")[OUTCOME_COLUMN]

    analysis = pairs.copy()
    analysis["q_geometry_low_mmol_g"] = (
        analysis["driver_low_mof_id"].map(outcome_by_id)
    )
    analysis["q_geometry_high_mmol_g"] = (
        analysis["driver_high_mof_id"].map(outcome_by_id)
    )

    analysis["primary_outcome_complete"] = (
        analysis["q_geometry_low_mmol_g"].notna()
        & analysis["q_geometry_high_mmol_g"].notna()
    )

    complete = analysis.loc[
        analysis["primary_outcome_complete"]
    ].copy()

    if complete.empty:
        raise RuntimeError("no frozen pairs have complete primary outcomes")

    q_low = complete["q_geometry_low_mmol_g"].to_numpy(dtype=float)
    q_high = complete["q_geometry_high_mmol_g"].to_numpy(dtype=float)

    complete["delta_q_mmol_g"] = q_high - q_low
    complete["symmetric_relative_effect"] = symmetric_relative_effect(
        q_high,
        q_low,
    )

    log_ratio = np.full(len(complete), np.nan, dtype=float)
    positive = (q_high > 0) & (q_low > 0)
    log_ratio[positive] = np.log(q_high[positive] / q_low[positive])
    complete["log_uptake_ratio"] = log_ratio

    delta = complete["delta_q_mmol_g"].to_numpy(dtype=float)

    median_delta = float(np.median(delta))
    mean_delta = float(np.mean(delta))
    positive_fraction = float(np.mean(delta > 0))
    zero_fraction = float(np.mean(delta == 0))
    negative_fraction = float(np.mean(delta < 0))

    ci_low, ci_high, bootstrap_medians = bootstrap_median_ci(
        delta,
        BOOTSTRAP_REPLICATES,
        BOOTSTRAP_SEED,
        BOOTSTRAP_CHUNK,
    )

    tier_rows = []
    tier_definitions = [
        ("primary_10pct", "primary_10pct_pair"),
        ("stronger_20pct", "sensitivity_20pct_pair"),
        ("stronger_30pct", "sensitivity_30pct_pair"),
    ]

    for tier_name, flag_column in tier_definitions:
        tier = complete.loc[
            complete[flag_column]
            .astype("boolean")
            .fillna(False)
        ].copy()

        tier_delta = tier["delta_q_mmol_g"].to_numpy(dtype=float)

        tier_rows.append(
            {
                "tier": tier_name,
                "pairs": int(len(tier)),
                "median_delta_q_mmol_g": (
                    float(np.median(tier_delta))
                    if len(tier_delta)
                    else np.nan
                ),
                "mean_delta_q_mmol_g": (
                    float(np.mean(tier_delta))
                    if len(tier_delta)
                    else np.nan
                ),
                "positive_effect_fraction": (
                    float(np.mean(tier_delta > 0))
                    if len(tier_delta)
                    else np.nan
                ),
                "median_symmetric_relative_effect": (
                    float(
                        tier["symmetric_relative_effect"].median()
                    )
                    if len(tier)
                    else np.nan
                ),
            }
        )

    tier_summary = pd.DataFrame(tier_rows)

    driver_summary = (
        complete.groupby("driver_descriptor", sort=True)
        .agg(
            pairs=("architecture_group_id", "size"),
            median_delta_q_mmol_g=("delta_q_mmol_g", "median"),
            mean_delta_q_mmol_g=("delta_q_mmol_g", "mean"),
            positive_effect_fraction=(
                "delta_q_mmol_g",
                lambda s: float((s > 0).mean()),
            ),
            median_pair_max_geometry_difference=(
                "pair_max_fractional_difference",
                "median",
            ),
        )
        .reset_index()
        .sort_values(
            ["pairs", "driver_descriptor"],
            ascending=[False, True],
        )
        .reset_index(drop=True)
    )

    topology_summary = (
        complete.groupby("topology", sort=True)
        .agg(
            pairs=("architecture_group_id", "size"),
            median_delta_q_mmol_g=("delta_q_mmol_g", "median"),
            mean_delta_q_mmol_g=("delta_q_mmol_g", "mean"),
            positive_effect_fraction=(
                "delta_q_mmol_g",
                lambda s: float((s > 0).mean()),
            ),
        )
        .reset_index()
        .sort_values(
            ["pairs", "topology"],
            ascending=[False, True],
        )
        .reset_index(drop=True)
    )

    primary_summary = pd.DataFrame(
        [
            ("frozen_primary_pairs", len(analysis)),
            (
                "complete_primary_outcome_pairs",
                int(analysis["primary_outcome_complete"].sum()),
            ),
            (
                "incomplete_primary_outcome_pairs",
                int((~analysis["primary_outcome_complete"]).sum()),
            ),
            ("median_delta_q_mmol_g", median_delta),
            ("bootstrap_95ci_low_median_delta_q_mmol_g", ci_low),
            ("bootstrap_95ci_high_median_delta_q_mmol_g", ci_high),
            ("mean_delta_q_mmol_g", mean_delta),
            ("positive_effect_fraction", positive_fraction),
            ("zero_effect_fraction", zero_fraction),
            ("negative_effect_fraction", negative_fraction),
            (
                "median_symmetric_relative_effect",
                float(complete["symmetric_relative_effect"].median()),
            ),
            (
                "mean_symmetric_relative_effect",
                float(complete["symmetric_relative_effect"].mean()),
            ),
            (
                "positive_log_ratio_pairs",
                int(complete["log_uptake_ratio"].notna().sum()),
            ),
            (
                "median_log_uptake_ratio_positive_pairs",
                float(complete["log_uptake_ratio"].median()),
            ),
        ],
        columns=["metric", "value"],
    )

    definition = {
        "definition_version": DEFINITION_VERSION,
        "primary_endpoint": {
            "source": "methane.csv",
            "temperature_K": TEMPERATURE_K,
            "pressure_bar": PRESSURE_BAR,
            "outcome_column": OUTCOME_COLUMN,
        },
        "outcome_columns_read": [
            "filename",
            "T/K",
            "p/bar",
            OUTCOME_COLUMN,
        ],
        "other_outcome_tables_read": False,
        "other_outcome_columns_read": False,
        "pair_orientation": (
            "driver_low_mof_id -> driver_high_mof_id from frozen Step 2.3 pairs"
        ),
        "primary_effect": "q_geometry_high - q_geometry_low",
        "primary_estimator": "median",
        "bootstrap": {
            "method": "nonparametric resampling of whole frozen families",
            "replicates": BOOTSTRAP_REPLICATES,
            "seed": BOOTSTRAP_SEED,
            "interval": "percentile 95%",
        },
        "missing_data_rule": (
            "no imputation; pair included only when both primary outcome values exist"
        ),
        "pair_membership_modified": False,
        "geometry_threshold_modified": False,
        "primary_endpoint_modified": False,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_columns = [
        "architecture_group_id",
        "source_chemistry_group_id",
        "topology",
        "dimensionality",
        "family_size",
        "mof_id_a",
        "mof_id_b",
        "driver_descriptor",
        "driver_low_mof_id",
        "driver_high_mof_id",
        "pair_max_fractional_difference",
        "pair_mean_fractional_difference",
        "primary_10pct_pair",
        "sensitivity_20pct_pair",
        "sensitivity_30pct_pair",
        "q_geometry_low_mmol_g",
        "q_geometry_high_mmol_g",
        "primary_outcome_complete",
        "delta_q_mmol_g",
        "symmetric_relative_effect",
        "log_uptake_ratio",
    ]

    # Analysis output contains complete pairs only for columns requiring effects.
    atomic_write_parquet(
        complete[output_columns]
        .sort_values("architecture_group_id")
        .reset_index(drop=True),
        OUTPUT_DIR / "primary_ch4_pair_effects.parquet",
    )

    atomic_write_csv(
        primary_summary,
        OUTPUT_DIR / "primary_ch4_summary.csv",
    )
    atomic_write_csv(
        tier_summary,
        OUTPUT_DIR / "primary_ch4_geometry_tier_summary.csv",
    )
    atomic_write_csv(
        driver_summary,
        OUTPUT_DIR / "primary_ch4_driver_summary.csv",
    )
    atomic_write_csv(
        topology_summary,
        OUTPUT_DIR / "primary_ch4_topology_summary.csv",
    )
    atomic_write_csv(
        pd.DataFrame(
            {"bootstrap_median_delta_q_mmol_g": bootstrap_medians}
        ),
        OUTPUT_DIR / "primary_ch4_bootstrap_medians.csv",
    )
    atomic_write_text(
        json.dumps(definition, indent=2),
        OUTPUT_DIR / "primary_ch4_analysis_definition.json",
    )

    manifest = {
        "script": Path(__file__).name,
        "script_version": SCRIPT_VERSION,
        "definition_version": DEFINITION_VERSION,
        "completed_at_utc": utc_now(),
        "completed_successfully": True,
        "pair_source_sha256": sha256_file(PAIR_PATH),
        "freeze_definition_sha256": sha256_file(FREEZE_DEFINITION),
        "methane_source_sha256": sha256_file(METHANE_PATH),
        "primary_endpoint_only": True,
        "outcome_values_read": True,
        "other_outcome_tables_read": False,
        "other_outcome_columns_read": False,
        "pair_membership_modified": False,
        "geometry_threshold_modified": False,
        "primary_endpoint_modified": False,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "bootstrap_seed": BOOTSTRAP_SEED,
    }

    atomic_write_text(
        json.dumps(manifest, indent=2),
        OUTPUT_DIR / "run_manifest.json",
    )

    print("PROJECT 17 - STEP 3.4 PRIMARY CH4 ANALYSIS")
    print(
        "Endpoint: CH4, 298 K, 65 bar, mmol/g | "
        "orientation: frozen geometry driver low -> high"
    )
    print()
    print(primary_summary.to_string(index=False))

    print()
    print("GEOMETRY SENSITIVITY TIERS")
    print(tier_summary.to_string(index=False))

    print()
    print("DRIVER DESCRIPTOR SUMMARY")
    print(driver_summary.to_string(index=False))

    print()
    print(f"Saved results: {OUTPUT_DIR}")
    print(
        "Stop here and run py .\\test_10.py before generating Figure 2."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
