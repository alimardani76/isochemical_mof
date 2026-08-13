#!/usr/bin/env python3
"""Audit Project 17 Step 3.8 dominant-context robustness."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent

SOURCE_DIR = (
    ROOT
    / "Step 3 results"
    / "04_primary_ch4_analysis"
)
SOURCE_PATH = SOURCE_DIR / "primary_ch4_pair_effects.parquet"
SOURCE_SUMMARY = SOURCE_DIR / "primary_ch4_summary.csv"

RESULTS = (
    ROOT
    / "Step 3 results"
    / "08_robustness_transferability"
)

DEFINITION_VERSION = "dominant_context_robustness_v1"
MIN_MAJOR_TOPOLOGY_PAIRS = 100
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 17
BOOTSTRAP_CHUNK = 250

EXPECTED_FILES = [
    "leave_one_topology_out.csv",
    "leave_one_driver_out.csv",
    "dominant_context_stress_tests.csv",
    "geometry_tier_stress_tests.csv",
    "aggressive_stress_bootstrap.csv",
    "robustness_definition.json",
    "run_manifest.json",
]

TIER_DEFINITIONS = [
    ("primary_10pct", "primary_10pct_pair"),
    ("stronger_20pct", "sensitivity_20pct_pair"),
    ("stronger_30pct", "sensitivity_30pct_pair"),
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


def bootstrap_median_ci(
    values: np.ndarray,
    replicates: int,
    seed: int,
    chunk_size: int,
) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)

    rng = np.random.default_rng(seed)
    medians = np.empty(replicates, dtype=float)

    start = 0
    while start < replicates:
        stop = min(start + chunk_size, replicates)
        block_n = stop - start

        indices = rng.integers(
            0,
            len(values),
            size=(block_n, len(values)),
            endpoint=False,
        )

        medians[start:stop] = np.median(
            values[indices],
            axis=1,
        )

        start = stop

    low, high = np.percentile(
        medians,
        [2.5, 97.5],
    )

    return float(low), float(high)


def summarize(frame: pd.DataFrame) -> tuple[int, float, float, float]:
    delta = pd.to_numeric(
        frame["delta_q_mmol_g"],
        errors="raise",
    ).to_numpy(dtype=float)

    return (
        int(len(frame)),
        float(np.median(delta)),
        float(np.mean(delta)),
        float(np.mean(delta > 0)),
    )


def close(a, b) -> bool:
    return bool(
        np.isclose(
            float(a),
            float(b),
            rtol=0,
            atol=1e-12,
            equal_nan=True,
        )
    )


def main() -> int:
    audit = Audit()

    print("PROJECT 17 - STEP 3.8 ROBUSTNESS AUDIT")

    audit.check(
        RESULTS.is_dir(),
        "Step 3.8 result folder exists",
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
        "all expected Step 3.8 files exist",
    )

    if missing:
        print("Missing:", missing)
        return 1

    audit.check(
        SOURCE_PATH.is_file(),
        "audited primary pair-effect source exists",
    )
    audit.check(
        SOURCE_SUMMARY.is_file(),
        "frozen primary summary exists",
    )

    if audit.failures:
        return 1

    manifest = json.loads(
        (RESULTS / "run_manifest.json")
        .read_text(encoding="utf-8")
    )
    definition = json.loads(
        (RESULTS / "robustness_definition.json")
        .read_text(encoding="utf-8")
    )

    topology_out = pd.read_csv(
        RESULTS / "leave_one_topology_out.csv"
    )
    driver_out = pd.read_csv(
        RESULTS / "leave_one_driver_out.csv"
    )
    stress_out = pd.read_csv(
        RESULTS / "dominant_context_stress_tests.csv"
    )
    tier_out = pd.read_csv(
        RESULTS / "geometry_tier_stress_tests.csv"
    )
    bootstrap_out = pd.read_csv(
        RESULTS / "aggressive_stress_bootstrap.csv"
    )

    data = pd.read_parquet(SOURCE_PATH)

    data["architecture_group_id"] = data[
        "architecture_group_id"
    ].astype("string")
    data["topology"] = data["topology"].astype("string")
    data["driver_descriptor"] = data[
        "driver_descriptor"
    ].astype("string")
    data["delta_q_mmol_g"] = pd.to_numeric(
        data["delta_q_mmol_g"],
        errors="raise",
    )

    source_summary = pd.read_csv(SOURCE_SUMMARY)
    source_metrics = dict(
        zip(
            source_summary["metric"].astype(str),
            pd.to_numeric(
                source_summary["value"],
                errors="coerce",
            ),
        )
    )
    baseline_median = float(
        source_metrics["median_delta_q_mmol_g"]
    )

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
        manifest.get("primary_estimand_modified") is False,
        "primary estimand was not modified",
    )

    print("\nDEFINITION")

    audit.check(
        definition.get("definition_version") == DEFINITION_VERSION,
        "definition version is exact",
    )
    audit.check(
        definition.get("analysis_status")
        == "secondary robustness analysis",
        "analysis is explicitly secondary robustness",
    )
    audit.check(
        definition.get("aggressive_topology_stress_test")
        == "exclude pcu + fsc",
        "combined topology stress test is exact",
    )
    audit.check(
        definition.get("aggressive_driver_stress_test")
        == "exclude ASA + AVA",
        "combined driver stress test is exact",
    )

    print("\nSOURCE POPULATION")

    audit.check(
        data["architecture_group_id"].is_unique,
        "source remains one row per frozen pair",
    )
    audit.check(
        len(data) == 11072,
        "source contains exactly 11,072 frozen primary pairs",
    )
    audit.check(
        close(
            np.median(data["delta_q_mmol_g"]),
            baseline_median,
        ),
        "source median matches frozen primary summary",
    )

    print("\nLEAVE-ONE-TOPOLOGY-OUT RECOMPUTATION")

    counts = data["topology"].value_counts()
    expected_major = sorted(
        counts.loc[
            counts >= MIN_MAJOR_TOPOLOGY_PAIRS
        ].index.astype(str).tolist()
    )
    observed_major = sorted(
        topology_out["excluded_value"].astype(str).tolist()
    )

    audit.check(
        expected_major == observed_major,
        "major-topology population is exact",
    )

    topology_exact = True

    for row in topology_out.itertuples(index=False):
        subset = data.loc[
            ~data["topology"].eq(str(row.excluded_value))
        ]

        n, median, mean, positive = summarize(subset)

        if not (
            int(row.pairs_retained) == n
            and close(row.median_delta_q_mmol_g, median)
            and close(row.mean_delta_q_mmol_g, mean)
            and close(row.positive_effect_fraction, positive)
            and close(
                row.median_change_vs_full_mmol_g,
                median - baseline_median,
            )
        ):
            topology_exact = False
            break

    audit.check(
        topology_exact,
        "all leave-one-topology-out results are exact",
    )

    print("\nLEAVE-ONE-DRIVER-OUT RECOMPUTATION")

    expected_drivers = sorted(
        data["driver_descriptor"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
    observed_drivers = sorted(
        driver_out["excluded_value"].astype(str).tolist()
    )

    audit.check(
        expected_drivers == observed_drivers,
        "driver population is exact",
    )

    driver_exact = True

    for row in driver_out.itertuples(index=False):
        subset = data.loc[
            ~data["driver_descriptor"].eq(
                str(row.excluded_value)
            )
        ]

        n, median, mean, positive = summarize(subset)

        if not (
            int(row.pairs_retained) == n
            and close(row.median_delta_q_mmol_g, median)
            and close(row.mean_delta_q_mmol_g, mean)
            and close(row.positive_effect_fraction, positive)
            and close(
                row.median_change_vs_full_mmol_g,
                median - baseline_median,
            )
        ):
            driver_exact = False
            break

    audit.check(
        driver_exact,
        "all leave-one-driver-out results are exact",
    )

    print("\nDOMINANT-CONTEXT STRESS TESTS")

    expected_masks = {
        "full_cohort": pd.Series(True, index=data.index),
        "exclude_pcu": ~data["topology"].eq("pcu"),
        "exclude_fsc": ~data["topology"].eq("fsc"),
        "exclude_pcu_fsc": ~data["topology"].isin(
            ["pcu", "fsc"]
        ),
        "exclude_ASA": ~data["driver_descriptor"].eq("ASA"),
        "exclude_AVA": ~data["driver_descriptor"].eq("AVA"),
        "exclude_ASA_AVA": ~data["driver_descriptor"].isin(
            ["ASA", "AVA"]
        ),
    }

    stress_exact = True

    for row in stress_out.itertuples(index=False):
        label = str(row.analysis)

        if label not in expected_masks:
            stress_exact = False
            break

        subset = data.loc[
            expected_masks[label]
        ]

        n, median, mean, positive = summarize(subset)

        if not (
            int(row.pairs_retained) == n
            and close(row.median_delta_q_mmol_g, median)
            and close(row.mean_delta_q_mmol_g, mean)
            and close(row.positive_effect_fraction, positive)
            and close(
                row.median_change_vs_full_mmol_g,
                median - baseline_median,
            )
        ):
            stress_exact = False
            break

    audit.check(
        stress_exact,
        "all dominant-context stress tests are exact",
    )

    print("\nGEOMETRY-TIER STRESS TESTS")

    tier_exact = True

    stress_masks = {
        "full": pd.Series(True, index=data.index),
        "exclude_pcu_fsc": ~data["topology"].isin(
            ["pcu", "fsc"]
        ),
        "exclude_ASA_AVA": ~data["driver_descriptor"].isin(
            ["ASA", "AVA"]
        ),
    }

    for row in tier_out.itertuples(index=False):
        tier_matches = [
            flag_col
            for tier_name, flag_col in TIER_DEFINITIONS
            if tier_name == str(row.tier)
        ]

        if len(tier_matches) != 1:
            tier_exact = False
            break

        flag_col = tier_matches[0]

        tier_mask = (
            data[flag_col]
            .astype("boolean")
            .fillna(False)
        )

        stress_name = str(row.stress_test)

        if stress_name not in stress_masks:
            tier_exact = False
            break

        subset = data.loc[
            tier_mask & stress_masks[stress_name]
        ]

        n, median, mean, positive = summarize(subset)

        if not (
            int(row.pairs_retained) == n
            and close(row.median_delta_q_mmol_g, median)
            and close(row.mean_delta_q_mmol_g, mean)
            and close(row.positive_effect_fraction, positive)
        ):
            tier_exact = False
            break

    audit.check(
        tier_exact,
        "all geometry-tier stress tests are exact",
    )

    print("\nAGGRESSIVE STRESS BOOTSTRAP")

    bootstrap_exact = True

    bootstrap_masks = {
        "exclude_pcu_fsc": ~data["topology"].isin(
            ["pcu", "fsc"]
        ),
        "exclude_ASA_AVA": ~data["driver_descriptor"].isin(
            ["ASA", "AVA"]
        ),
    }

    for row in bootstrap_out.itertuples(index=False):
        label = str(row.analysis)

        if label not in bootstrap_masks:
            bootstrap_exact = False
            break

        delta = data.loc[
            bootstrap_masks[label],
            "delta_q_mmol_g",
        ].to_numpy(dtype=float)

        ci_low, ci_high = bootstrap_median_ci(
            delta,
            BOOTSTRAP_REPLICATES,
            BOOTSTRAP_SEED,
            BOOTSTRAP_CHUNK,
        )

        if not (
            int(row.pairs_retained) == len(delta)
            and close(
                row.median_delta_q_mmol_g,
                np.median(delta),
            )
            and int(row.bootstrap_replicates)
            == BOOTSTRAP_REPLICATES
            and int(row.bootstrap_seed)
            == BOOTSTRAP_SEED
            and close(
                row.bootstrap_95ci_low_median_delta_q_mmol_g,
                ci_low,
            )
            and close(
                row.bootstrap_95ci_high_median_delta_q_mmol_g,
                ci_high,
            )
        ):
            bootstrap_exact = False
            break

    audit.check(
        bootstrap_exact,
        "aggressive-stress bootstrap intervals reproduce exactly",
    )

    print("\nSCIENTIFIC CENSUS")

    print(
        stress_out.loc[
            stress_out["analysis"].isin(
                [
                    "full_cohort",
                    "exclude_pcu_fsc",
                    "exclude_ASA_AVA",
                ]
            ),
            [
                "analysis",
                "pairs_retained",
                "median_delta_q_mmol_g",
                "positive_effect_fraction",
                "median_ratio_to_full",
            ],
        ].to_string(index=False)
    )

    print("\nOVERALL RESULT")

    if audit.failures:
        print(
            f"FAIL - {len(audit.failures)} hard check(s) failed. "
            "Do not freeze robustness claims."
        )
        return 1

    print(
        "PASS - dominant-context robustness analysis reproduces exactly."
    )
    print(
        "Next: interpret whether the primary conclusion survives dominant "
        "topology and driver removal, then freeze the final design claims."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
