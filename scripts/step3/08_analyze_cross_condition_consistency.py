#!/usr/bin/env python3
"""
Project 17 Step 3.6: pair-level cross-condition consistency atlas.

Purpose
-------
Use the already-audited Step 3.5 adsorption pair effects to determine whether
geometry-associated uptake responses transfer across gases/pressures and where
sign reversals occur.

Only adsorption metric:
    mmol/g

No raw adsorption files are read.
No process metrics are used.
No primary endpoint, pair membership, pair orientation, or geometry threshold
is changed.

Outputs
-------
1. mmolg_pair_endpoint_matrix.parquet
   One row per frozen architecture pair, one delta-q column per adsorption
   endpoint.

2. mmolg_primary_concordance.csv
   For every endpoint versus the frozen primary CH4 298 K / 65 bar endpoint:
   common pairs, Spearman rho, same-sign fraction, positive fractions.

3. mmolg_endpoint_spearman.csv
   Pairwise Spearman correlation matrix across all mmol/g endpoints.

4. mmolg_endpoint_sign_agreement.csv
   Pairwise sign-agreement matrix across all mmol/g endpoints.

5. mmolg_low_high_pressure_transitions.csv
   Within every source/guest series that has exactly two pressures:
   low/high positive fractions, sign-flip fraction, negative->positive and
   positive->negative fractions, and low/high Spearman rho.

6. mmolg_pair_generality.parquet
   Per frozen pair: number of observed endpoints, number/fraction positive,
   and corresponding low-pressure/high-pressure positive fractions.

7. run_manifest.json
8. cross_condition_definition.json
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
DEFINITION_VERSION = "mmolg_cross_condition_consistency_v1"

ROOT = Path(__file__).resolve().parents[1]

SOURCE_PATH = (
    ROOT
    / "Step 3 results"
    / "05_secondary_outcome_atlas"
    / "secondary_adsorption_pair_effects.parquet"
)

SOURCE_MANIFEST = (
    ROOT
    / "Step 3 results"
    / "05_secondary_outcome_atlas"
    / "run_manifest.json"
)

OUTPUT_DIR = (
    ROOT
    / "Step 3 results"
    / "06_cross_condition_consistency"
)

PRIMARY_SOURCE = "methane.csv"
PRIMARY_CONTEXT = "methane-storage"
PRIMARY_GUEST = "CH4"
PRIMARY_T = 298.0
PRIMARY_P = 65.0
METRIC = "mmol/g"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def endpoint_id(
    context: str,
    guest: str,
    temperature_K: float,
    pressure_bar: float,
) -> str:
    return (
        f"{context}|{guest}|"
        f"{float(temperature_K):g}K|"
        f"{float(pressure_bar):g}bar"
    )


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


def sign_series(values: pd.Series) -> pd.Series:
    array = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    signs = np.sign(array)
    return pd.Series(signs, index=values.index, dtype=float)


def pairwise_sign_agreement(wide: pd.DataFrame) -> pd.DataFrame:
    cols = list(wide.columns)
    matrix = pd.DataFrame(
        np.nan,
        index=cols,
        columns=cols,
        dtype=float,
    )

    for a in cols:
        for b in cols:
            block = wide[[a, b]].dropna()
            if block.empty:
                continue

            sa = np.sign(block[a].to_numpy(dtype=float))
            sb = np.sign(block[b].to_numpy(dtype=float))
            matrix.loc[a, b] = float(np.mean(sa == sb))

    matrix.index.name = "endpoint_id"
    return matrix


def build_low_high_metadata(
    endpoint_meta: pd.DataFrame,
) -> tuple[set[str], set[str]]:
    low_ids: set[str] = set()
    high_ids: set[str] = set()

    for (_source, _guest), block in endpoint_meta.groupby(
        ["source", "guest"],
        sort=True,
    ):
        block = block.sort_values("pressure_bar")
        if len(block) != 2:
            continue

        low_ids.add(str(block.iloc[0]["endpoint_id"]))
        high_ids.add(str(block.iloc[1]["endpoint_id"]))

    return low_ids, high_ids


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if not SOURCE_PATH.is_file():
        raise FileNotFoundError(SOURCE_PATH)
    if not SOURCE_MANIFEST.is_file():
        raise FileNotFoundError(SOURCE_MANIFEST)

    source_manifest = json.loads(
        SOURCE_MANIFEST.read_text(encoding="utf-8")
    )

    if source_manifest.get("completed_successfully") is not True:
        raise RuntimeError("Step 3.5 source is not marked complete")
    if source_manifest.get("primary_endpoint_modified") is not False:
        raise RuntimeError("Step 3.5 modified the primary endpoint")
    if source_manifest.get("pair_membership_modified") is not False:
        raise RuntimeError("Step 3.5 modified frozen pair membership")
    if source_manifest.get("pair_orientation_modified") is not False:
        raise RuntimeError("Step 3.5 modified frozen pair orientation")

    effects = pd.read_parquet(SOURCE_PATH)

    required = {
        "source",
        "context",
        "guest",
        "temperature_K",
        "pressure_bar",
        "metric",
        "architecture_group_id",
        "driver_descriptor",
        "delta",
        "is_primary_endpoint",
    }
    missing = required - set(effects.columns)
    if missing:
        raise ValueError(
            f"secondary adsorption pair effects missing: {sorted(missing)}"
        )

    effects = effects.loc[
        effects["metric"].eq(METRIC)
    ].copy()

    effects["temperature_K"] = pd.to_numeric(
        effects["temperature_K"],
        errors="raise",
    )
    effects["pressure_bar"] = pd.to_numeric(
        effects["pressure_bar"],
        errors="raise",
    )
    effects["delta"] = pd.to_numeric(
        effects["delta"],
        errors="raise",
    )
    effects["architecture_group_id"] = effects[
        "architecture_group_id"
    ].astype("string")

    effects["endpoint_id"] = [
        endpoint_id(c, g, t, p)
        for c, g, t, p in zip(
            effects["context"],
            effects["guest"],
            effects["temperature_K"],
            effects["pressure_bar"],
        )
    ]

    endpoint_meta = (
        effects[
            [
                "endpoint_id",
                "source",
                "context",
                "guest",
                "temperature_K",
                "pressure_bar",
                "is_primary_endpoint",
            ]
        ]
        .drop_duplicates()
        .sort_values(
            ["context", "guest", "temperature_K", "pressure_bar"]
        )
        .reset_index(drop=True)
    )

    if endpoint_meta["endpoint_id"].duplicated().any():
        raise RuntimeError("endpoint_id is not unique")

    primary_rows = endpoint_meta.loc[
        endpoint_meta["source"].eq(PRIMARY_SOURCE)
        & endpoint_meta["context"].eq(PRIMARY_CONTEXT)
        & endpoint_meta["guest"].eq(PRIMARY_GUEST)
        & endpoint_meta["temperature_K"].eq(PRIMARY_T)
        & endpoint_meta["pressure_bar"].eq(PRIMARY_P)
    ]

    if len(primary_rows) != 1:
        raise RuntimeError("frozen primary endpoint not uniquely found")

    primary_id = str(primary_rows.iloc[0]["endpoint_id"])

    # One row per pair, one column per adsorption endpoint.
    wide = effects.pivot(
        index="architecture_group_id",
        columns="endpoint_id",
        values="delta",
    ).sort_index()

    # Preserve driver descriptor for later counterexample analysis.
    driver_by_pair = (
        effects[
            ["architecture_group_id", "driver_descriptor"]
        ]
        .drop_duplicates()
        .set_index("architecture_group_id")["driver_descriptor"]
    )

    if driver_by_pair.index.duplicated().any():
        raise RuntimeError(
            "a frozen architecture pair has multiple driver descriptors"
        )

    wide_output = wide.copy()
    wide_output.insert(
        0,
        "driver_descriptor",
        driver_by_pair.reindex(wide.index).astype("string"),
    )
    wide_output = wide_output.reset_index()

    # Endpoint-to-primary concordance.
    primary = wide[primary_id]

    concordance_rows = []

    for row in endpoint_meta.itertuples(index=False):
        eid = str(row.endpoint_id)

        block = pd.concat(
            [primary.rename("primary"), wide[eid].rename("endpoint")],
            axis=1,
        ).dropna()

        primary_sign = np.sign(
            block["primary"].to_numpy(dtype=float)
        )
        endpoint_sign = np.sign(
            block["endpoint"].to_numpy(dtype=float)
        )

        rho = block["primary"].corr(
            block["endpoint"],
            method="spearman",
        )

        concordance_rows.append(
            {
                "endpoint_id": eid,
                "source": row.source,
                "context": row.context,
                "guest": row.guest,
                "temperature_K": float(row.temperature_K),
                "pressure_bar": float(row.pressure_bar),
                "is_primary_endpoint": bool(
                    row.is_primary_endpoint
                ),
                "common_pairs": int(len(block)),
                "spearman_rho_vs_primary": float(rho),
                "same_sign_fraction_vs_primary": float(
                    np.mean(primary_sign == endpoint_sign)
                ),
                "primary_positive_fraction_common": float(
                    np.mean(primary_sign > 0)
                ),
                "endpoint_positive_fraction_common": float(
                    np.mean(endpoint_sign > 0)
                ),
                "negative_to_positive_vs_primary_fraction": float(
                    np.mean(
                        (primary_sign < 0)
                        & (endpoint_sign > 0)
                    )
                ),
                "positive_to_negative_vs_primary_fraction": float(
                    np.mean(
                        (primary_sign > 0)
                        & (endpoint_sign < 0)
                    )
                ),
            }
        )

    concordance = pd.DataFrame(concordance_rows)

    # Pairwise endpoint correlation / sign agreement.
    spearman = wide.corr(
        method="spearman",
        min_periods=100,
    )
    spearman.index.name = "endpoint_id"

    sign_agreement = pairwise_sign_agreement(wide)

    # Within each source+guest series, compare low versus high pressure.
    transition_rows = []

    for (source, guest), meta_block in endpoint_meta.groupby(
        ["source", "guest"],
        sort=True,
    ):
        meta_block = meta_block.sort_values("pressure_bar")

        if len(meta_block) != 2:
            continue

        low_meta = meta_block.iloc[0]
        high_meta = meta_block.iloc[1]

        low_id = str(low_meta["endpoint_id"])
        high_id = str(high_meta["endpoint_id"])

        block = wide[[low_id, high_id]].dropna()
        low = block[low_id].to_numpy(dtype=float)
        high = block[high_id].to_numpy(dtype=float)

        low_sign = np.sign(low)
        high_sign = np.sign(high)

        transition_rows.append(
            {
                "source": source,
                "context": str(low_meta["context"]),
                "guest": guest,
                "temperature_K": float(low_meta["temperature_K"]),
                "low_pressure_bar": float(low_meta["pressure_bar"]),
                "high_pressure_bar": float(high_meta["pressure_bar"]),
                "common_pairs": int(len(block)),
                "low_positive_fraction": float(
                    np.mean(low_sign > 0)
                ),
                "high_positive_fraction": float(
                    np.mean(high_sign > 0)
                ),
                "same_sign_fraction": float(
                    np.mean(low_sign == high_sign)
                ),
                "sign_flip_fraction": float(
                    np.mean(low_sign != high_sign)
                ),
                "negative_to_positive_fraction": float(
                    np.mean(
                        (low_sign < 0)
                        & (high_sign > 0)
                    )
                ),
                "positive_to_negative_fraction": float(
                    np.mean(
                        (low_sign > 0)
                        & (high_sign < 0)
                    )
                ),
                "spearman_rho_low_vs_high": float(
                    pd.Series(low).corr(
                        pd.Series(high),
                        method="spearman",
                    )
                ),
                "median_delta_low": float(np.median(low)),
                "median_delta_high": float(np.median(high)),
            }
        )

    transitions = pd.DataFrame(transition_rows)

    # Pair-level generality across all mmol/g endpoints.
    low_ids, high_ids = build_low_high_metadata(endpoint_meta)

    low_cols = [
        c for c in wide.columns if c in low_ids
    ]
    high_cols = [
        c for c in wide.columns if c in high_ids
    ]

    observed = wide.notna().sum(axis=1)
    positive = wide.gt(0).sum(axis=1)

    low_observed = wide[low_cols].notna().sum(axis=1)
    low_positive = wide[low_cols].gt(0).sum(axis=1)

    high_observed = wide[high_cols].notna().sum(axis=1)
    high_positive = wide[high_cols].gt(0).sum(axis=1)

    generality = pd.DataFrame(
        {
            "architecture_group_id": wide.index.astype(str),
            "driver_descriptor": (
                driver_by_pair.reindex(wide.index)
                .astype("string")
                .to_numpy()
            ),
            "observed_mmolg_endpoints": observed.to_numpy(dtype=int),
            "positive_mmolg_endpoints": positive.to_numpy(dtype=int),
            "positive_fraction_all_endpoints": (
                positive / observed
            ).to_numpy(dtype=float),
            "observed_low_pressure_endpoints": low_observed.to_numpy(dtype=int),
            "positive_low_pressure_endpoints": low_positive.to_numpy(dtype=int),
            "positive_fraction_low_pressure": (
                low_positive / low_observed
            ).to_numpy(dtype=float),
            "observed_high_pressure_endpoints": high_observed.to_numpy(dtype=int),
            "positive_high_pressure_endpoints": high_positive.to_numpy(dtype=int),
            "positive_fraction_high_pressure": (
                high_positive / high_observed
            ).to_numpy(dtype=float),
            "primary_delta_q_mmol_g": (
                primary.reindex(wide.index)
                .to_numpy(dtype=float)
            ),
        }
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    atomic_write_parquet(
        wide_output,
        OUTPUT_DIR / "mmolg_pair_endpoint_matrix.parquet",
    )
    atomic_write_csv(
        endpoint_meta,
        OUTPUT_DIR / "mmolg_endpoint_metadata.csv",
    )
    atomic_write_csv(
        concordance.sort_values(
            ["is_primary_endpoint", "spearman_rho_vs_primary"],
            ascending=[False, False],
        ).reset_index(drop=True),
        OUTPUT_DIR / "mmolg_primary_concordance.csv",
    )
    atomic_write_csv(
        spearman.reset_index(),
        OUTPUT_DIR / "mmolg_endpoint_spearman.csv",
    )
    atomic_write_csv(
        sign_agreement.reset_index(),
        OUTPUT_DIR / "mmolg_endpoint_sign_agreement.csv",
    )
    atomic_write_csv(
        transitions.sort_values(
            ["guest", "context"]
        ).reset_index(drop=True),
        OUTPUT_DIR / "mmolg_low_high_pressure_transitions.csv",
    )
    atomic_write_parquet(
        generality.sort_values(
            "architecture_group_id"
        ).reset_index(drop=True),
        OUTPUT_DIR / "mmolg_pair_generality.parquet",
    )

    definition = {
        "definition_version": DEFINITION_VERSION,
        "source": str(SOURCE_PATH.relative_to(ROOT)),
        "metric": METRIC,
        "raw_outcome_files_read": False,
        "process_metrics_used": False,
        "primary_endpoint": {
            "source": PRIMARY_SOURCE,
            "context": PRIMARY_CONTEXT,
            "guest": PRIMARY_GUEST,
            "temperature_K": PRIMARY_T,
            "pressure_bar": PRIMARY_P,
            "endpoint_id": primary_id,
        },
        "concordance_metrics": [
            "Spearman rho",
            "exact sign agreement",
            "positive fractions",
            "negative-to-positive fraction",
            "positive-to-negative fraction",
        ],
        "low_high_transition_rule": (
            "within each source+guest series having exactly two pressures, "
            "lower pressure is compared with higher pressure using the same "
            "frozen pair orientation"
        ),
        "pair_membership_modified": False,
        "pair_orientation_modified": False,
        "geometry_threshold_modified": False,
        "primary_endpoint_modified": False,
        "secondary_endpoint_promoted_to_primary": False,
    }

    manifest = {
        "script": Path(__file__).name,
        "script_version": SCRIPT_VERSION,
        "definition_version": DEFINITION_VERSION,
        "completed_at_utc": utc_now(),
        "completed_successfully": True,
        "raw_outcome_files_read": False,
        "source_pair_effect_table_read": True,
        "metric": METRIC,
        "endpoint_count": int(len(endpoint_meta)),
        "frozen_pair_count": int(len(wide)),
        "primary_endpoint_id": primary_id,
        "pair_membership_modified": False,
        "pair_orientation_modified": False,
        "geometry_threshold_modified": False,
        "primary_endpoint_modified": False,
        "secondary_endpoint_promoted_to_primary": False,
    }

    atomic_write_text(
        json.dumps(definition, indent=2),
        OUTPUT_DIR / "cross_condition_definition.json",
    )
    atomic_write_text(
        json.dumps(manifest, indent=2),
        OUTPUT_DIR / "run_manifest.json",
    )

    print("PROJECT 17 - STEP 3.6 CROSS-CONDITION CONSISTENCY")
    print(
        "Policy: audited mmol/g pair effects only; no raw outcomes; "
        "primary endpoint and frozen pair orientation unchanged"
    )
    print()
    print(
        f"Frozen pairs: {len(wide):,}; "
        f"mmol/g adsorption endpoints: {len(endpoint_meta):,}"
    )

    print()
    print("PRIMARY-ENDPOINT CONCORDANCE")
    display_concordance = concordance.loc[
        ~concordance["is_primary_endpoint"]
    ].sort_values(
        "spearman_rho_vs_primary",
        ascending=False,
    )
    print(
        display_concordance[
            [
                "context",
                "guest",
                "pressure_bar",
                "common_pairs",
                "spearman_rho_vs_primary",
                "same_sign_fraction_vs_primary",
                "endpoint_positive_fraction_common",
            ]
        ].to_string(index=False)
    )

    print()
    print("LOW -> HIGH PRESSURE TRANSITIONS")
    print(
        transitions[
            [
                "context",
                "guest",
                "low_pressure_bar",
                "high_pressure_bar",
                "low_positive_fraction",
                "high_positive_fraction",
                "negative_to_positive_fraction",
                "positive_to_negative_fraction",
                "spearman_rho_low_vs_high",
            ]
        ].to_string(index=False)
    )

    print()
    print("PAIR GENERALITY")
    print(
        f"Median positive fraction across all endpoints: "
        f"{generality['positive_fraction_all_endpoints'].median():.3f}"
    )
    print(
        f"Median positive fraction at low pressure: "
        f"{generality['positive_fraction_low_pressure'].median():.3f}"
    )
    print(
        f"Median positive fraction at high pressure: "
        f"{generality['positive_fraction_high_pressure'].median():.3f}"
    )

    print()
    print(f"Saved results: {OUTPUT_DIR}")
    print(
        "Stop here and run py .\\test_12.py before designing Figure 4."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
