#!/usr/bin/env python3
"""Audit Project 17 Step 3.6 cross-condition consistency atlas."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent

SOURCE_PATH = (
    ROOT
    / "Step 3 results"
    / "05_secondary_outcome_atlas"
    / "secondary_adsorption_pair_effects.parquet"
)

RESULTS = (
    ROOT
    / "Step 3 results"
    / "06_cross_condition_consistency"
)

DEFINITION_VERSION = "mmolg_cross_condition_consistency_v1"

EXPECTED_FILES = [
    "mmolg_pair_endpoint_matrix.parquet",
    "mmolg_endpoint_metadata.csv",
    "mmolg_primary_concordance.csv",
    "mmolg_endpoint_spearman.csv",
    "mmolg_endpoint_sign_agreement.csv",
    "mmolg_low_high_pressure_transitions.csv",
    "mmolg_pair_generality.parquet",
    "cross_condition_definition.json",
    "run_manifest.json",
]


class Audit:
    def __init__(self):
        self.failures = []

    def check(self, condition, message):
        try:
            ok = bool(condition)
        except Exception:
            ok = False

        print(("PASS  " if ok else "FAIL  ") + message)

        if not ok:
            self.failures.append(message)


def endpoint_id(context, guest, temperature_K, pressure_bar):
    return (
        f"{context}|{guest}|"
        f"{float(temperature_K):g}K|"
        f"{float(pressure_bar):g}bar"
    )


def main() -> int:
    audit = Audit()

    print("PROJECT 17 - STEP 3.6 CROSS-CONDITION CONSISTENCY AUDIT")

    audit.check(
        RESULTS.is_dir(),
        "Step 3.6 result folder exists",
    )

    if not RESULTS.is_dir():
        return 1

    missing = [
        name
        for name in EXPECTED_FILES
        if not (RESULTS / name).is_file()
    ]

    audit.check(
        not missing,
        "all expected Step 3.6 files exist",
    )

    if missing:
        print("Missing:", missing)
        return 1

    audit.check(
        SOURCE_PATH.is_file(),
        "audited Step 3.5 pair-effect source exists",
    )

    if audit.failures:
        return 1

    manifest = json.loads(
        (RESULTS / "run_manifest.json").read_text(encoding="utf-8")
    )
    definition = json.loads(
        (RESULTS / "cross_condition_definition.json")
        .read_text(encoding="utf-8")
    )

    endpoint_meta = pd.read_csv(
        RESULTS / "mmolg_endpoint_metadata.csv"
    )
    concordance = pd.read_csv(
        RESULTS / "mmolg_primary_concordance.csv"
    )
    transitions = pd.read_csv(
        RESULTS / "mmolg_low_high_pressure_transitions.csv"
    )
    matrix = pd.read_parquet(
        RESULTS / "mmolg_pair_endpoint_matrix.parquet"
    )
    generality = pd.read_parquet(
        RESULTS / "mmolg_pair_generality.parquet"
    )
    saved_spearman = pd.read_csv(
        RESULTS / "mmolg_endpoint_spearman.csv",
        index_col=0,
    )
    saved_agreement = pd.read_csv(
        RESULTS / "mmolg_endpoint_sign_agreement.csv",
        index_col=0,
    )

    effects = pd.read_parquet(SOURCE_PATH)
    effects = effects.loc[
        effects["metric"].eq("mmol/g")
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

    print("\nPOLICY")

    audit.check(
        manifest.get("completed_successfully") is True,
        "manifest records successful completion",
    )
    audit.check(
        manifest.get("definition_version") == DEFINITION_VERSION,
        "correct definition version is recorded",
    )
    audit.check(
        manifest.get("raw_outcome_files_read") is False,
        "no raw outcome files were read",
    )
    audit.check(
        manifest.get("metric") == "mmol/g",
        "only mmol/g adsorption effects were used",
    )
    audit.check(
        manifest.get("pair_membership_modified") is False,
        "pair membership was not modified",
    )
    audit.check(
        manifest.get("pair_orientation_modified") is False,
        "pair orientation was not modified",
    )
    audit.check(
        manifest.get("geometry_threshold_modified") is False,
        "geometry threshold was not modified",
    )
    audit.check(
        manifest.get("primary_endpoint_modified") is False,
        "primary endpoint was not modified",
    )
    audit.check(
        manifest.get("secondary_endpoint_promoted_to_primary") is False,
        "no secondary endpoint was promoted to primary",
    )

    print("\nDEFINITION")

    audit.check(
        definition.get("definition_version") == DEFINITION_VERSION,
        "definition version is exact",
    )
    audit.check(
        definition.get("metric") == "mmol/g",
        "definition metric is exact",
    )
    audit.check(
        definition.get("raw_outcome_files_read") is False,
        "definition confirms no raw outcome access",
    )
    audit.check(
        definition.get("process_metrics_used") is False,
        "process metrics were excluded",
    )

    print("\nENDPOINT POPULATION")

    expected_meta = (
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
        .sort_values("endpoint_id")
        .reset_index(drop=True)
    )

    observed_meta = (
        endpoint_meta
        .sort_values("endpoint_id")
        .reset_index(drop=True)
    )

    audit.check(
        expected_meta["endpoint_id"].tolist()
        == observed_meta["endpoint_id"].tolist(),
        "endpoint IDs match exactly",
    )
    audit.check(
        len(endpoint_meta) == 18,
        "exactly 18 mmol/g adsorption endpoints are present",
    )

    primary_rows = endpoint_meta.loc[
        endpoint_meta["is_primary_endpoint"]
        .astype("boolean")
        .fillna(False)
    ]

    audit.check(
        len(primary_rows) == 1,
        "exactly one primary endpoint is flagged",
    )

    print("\nPAIR-ENDPOINT MATRIX")

    expected_wide = effects.pivot(
        index="architecture_group_id",
        columns="endpoint_id",
        values="delta",
    ).sort_index()

    observed_wide = (
        matrix
        .drop(columns=["driver_descriptor"])
        .set_index("architecture_group_id")
    )
    observed_wide.index = observed_wide.index.astype("string")
    observed_wide = observed_wide.sort_index()

    audit.check(
        expected_wide.index.astype(str).tolist()
        == observed_wide.index.astype(str).tolist(),
        "pair IDs match exactly",
    )
    audit.check(
        set(expected_wide.columns)
        == set(observed_wide.columns),
        "endpoint columns match exactly",
    )

    matrix_exact = True

    for column in expected_wide.columns:
        if not np.allclose(
            expected_wide[column].to_numpy(dtype=float),
            observed_wide[column].to_numpy(dtype=float),
            rtol=0,
            atol=1e-12,
            equal_nan=True,
        ):
            matrix_exact = False
            break

    audit.check(
        matrix_exact,
        "all pair-level endpoint effects are exact",
    )

    print("\nCORRELATION MATRICES")

    expected_spearman = expected_wide.corr(
        method="spearman",
        min_periods=100,
    )

    saved_spearman = saved_spearman.loc[
        expected_spearman.index,
        expected_spearman.columns,
    ]

    audit.check(
        np.allclose(
            expected_spearman.to_numpy(dtype=float),
            saved_spearman.to_numpy(dtype=float),
            rtol=0,
            atol=1e-12,
            equal_nan=True,
        ),
        "Spearman matrix is exact",
    )

    agreement_expected = pd.DataFrame(
        np.nan,
        index=expected_wide.columns,
        columns=expected_wide.columns,
    )

    for a in expected_wide.columns:
        for b in expected_wide.columns:
            block = expected_wide[[a, b]].dropna()
            sa = np.sign(block[a].to_numpy(dtype=float))
            sb = np.sign(block[b].to_numpy(dtype=float))
            agreement_expected.loc[a, b] = float(
                np.mean(sa == sb)
            )

    saved_agreement = saved_agreement.loc[
        agreement_expected.index,
        agreement_expected.columns,
    ]

    audit.check(
        np.allclose(
            agreement_expected.to_numpy(dtype=float),
            saved_agreement.to_numpy(dtype=float),
            rtol=0,
            atol=1e-12,
            equal_nan=True,
        ),
        "sign-agreement matrix is exact",
    )

    print("\nPRIMARY CONCORDANCE")

    primary_id = str(
        primary_rows.iloc[0]["endpoint_id"]
    )
    primary = expected_wide[primary_id]

    concordance_ok = True

    for row in concordance.itertuples(index=False):
        eid = str(row.endpoint_id)

        block = pd.concat(
            [
                primary.rename("primary"),
                expected_wide[eid].rename("endpoint"),
            ],
            axis=1,
        ).dropna()

        rho = block["primary"].corr(
            block["endpoint"],
            method="spearman",
        )

        same_sign = np.mean(
            np.sign(block["primary"].to_numpy(dtype=float))
            == np.sign(block["endpoint"].to_numpy(dtype=float))
        )

        if not (
            int(row.common_pairs) == len(block)
            and np.isclose(
                float(row.spearman_rho_vs_primary),
                float(rho),
                rtol=0,
                atol=1e-12,
                equal_nan=True,
            )
            and np.isclose(
                float(row.same_sign_fraction_vs_primary),
                float(same_sign),
                rtol=0,
                atol=1e-12,
                equal_nan=True,
            )
        ):
            concordance_ok = False
            break

    audit.check(
        concordance_ok,
        "primary-endpoint concordance rows reproduce exactly",
    )

    print("\nLOW/HIGH PRESSURE TRANSITIONS")

    transition_ok = True

    for row in transitions.itertuples(index=False):
        source_meta = endpoint_meta.loc[
            endpoint_meta["source"].eq(row.source)
            & endpoint_meta["guest"].eq(row.guest)
        ].sort_values("pressure_bar")

        if len(source_meta) != 2:
            transition_ok = False
            break

        low_id = str(source_meta.iloc[0]["endpoint_id"])
        high_id = str(source_meta.iloc[1]["endpoint_id"])

        block = expected_wide[[low_id, high_id]].dropna()
        low = block[low_id].to_numpy(dtype=float)
        high = block[high_id].to_numpy(dtype=float)

        low_sign = np.sign(low)
        high_sign = np.sign(high)

        checks = [
            int(row.common_pairs) == len(block),
            np.isclose(
                float(row.low_positive_fraction),
                float(np.mean(low_sign > 0)),
                rtol=0,
                atol=1e-12,
            ),
            np.isclose(
                float(row.high_positive_fraction),
                float(np.mean(high_sign > 0)),
                rtol=0,
                atol=1e-12,
            ),
            np.isclose(
                float(row.negative_to_positive_fraction),
                float(
                    np.mean(
                        (low_sign < 0)
                        & (high_sign > 0)
                    )
                ),
                rtol=0,
                atol=1e-12,
            ),
        ]

        if not all(checks):
            transition_ok = False
            break

    audit.check(
        transition_ok,
        "low/high pressure transition rows reproduce exactly",
    )

    print("\nPAIR GENERALITY")

    audit.check(
        len(generality) == len(expected_wide),
        "generality table has one row per frozen pair",
    )
    audit.check(
        generality["architecture_group_id"].astype(str).is_unique,
        "generality pair IDs are unique",
    )

    print("\nSCIENTIFIC CENSUS")

    print(
        concordance.loc[
            ~concordance["is_primary_endpoint"]
            .astype("boolean")
            .fillna(False),
            [
                "context",
                "guest",
                "pressure_bar",
                "spearman_rho_vs_primary",
                "same_sign_fraction_vs_primary",
            ],
        ]
        .sort_values(
            "spearman_rho_vs_primary",
            ascending=False,
        )
        .to_string(index=False)
    )

    print("\nOVERALL RESULT")

    if audit.failures:
        print(
            f"FAIL - {len(audit.failures)} hard check(s) failed. "
            "Do not design Figure 4."
        )
        return 1

    print(
        "PASS - pair-level cross-condition consistency atlas is "
        "internally consistent."
    )
    print(
        "Next: use concordance, pressure sign transitions, and pair "
        "generality to define Figure 4 / counterexample analysis."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
