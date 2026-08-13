#!/usr/bin/env python3
"""
Project 17 Step 3.8: dominant-context robustness and transferability stress tests.

Purpose
-------
Test whether the frozen primary CH4 result is dominated by:
1. one major topology,
2. one geometry-driver class,
3. the two dominant topology classes together (pcu + fsc),
4. the two strongly favorable area/volume drivers together (ASA + AVA).

This is a secondary robustness analysis. It does NOT change:
- chemistry definition,
- architecture definition,
- geometry threshold,
- frozen pair membership,
- pair orientation,
- primary endpoint,
- primary estimand.

Inputs
------
Step 3 results/04_primary_ch4_analysis/primary_ch4_pair_effects.parquet
Step 3 results/04_primary_ch4_analysis/run_manifest.json
Step 3 results/04_primary_ch4_analysis/primary_ch4_summary.csv

Outputs
-------
1. leave_one_topology_out.csv
2. leave_one_driver_out.csv
3. dominant_context_stress_tests.csv
4. geometry_tier_stress_tests.csv
5. aggressive_stress_bootstrap.csv
6. robustness_definition.json
7. run_manifest.json

Bootstrap
---------
The confirmatory baseline CI is NOT recomputed or replaced.
For the two aggressive post hoc stress populations only:
- exclude pcu + fsc
- exclude ASA + AVA
we report a descriptive 10,000-replicate family bootstrap median CI
using seed 17.

These robustness intervals are secondary/descriptive and do not replace the
frozen confirmatory interval.
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
DEFINITION_VERSION = "dominant_context_robustness_v1"

BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 17
BOOTSTRAP_CHUNK = 250
MIN_MAJOR_TOPOLOGY_PAIRS = 100

ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIR = (
    ROOT
    / "Step 3 results"
    / "04_primary_ch4_analysis"
)

SOURCE_PATH = SOURCE_DIR / "primary_ch4_pair_effects.parquet"
SOURCE_MANIFEST = SOURCE_DIR / "run_manifest.json"
SOURCE_SUMMARY = SOURCE_DIR / "primary_ch4_summary.csv"

OUTPUT_DIR = (
    ROOT
    / "Step 3 results"
    / "08_robustness_transferability"
)

TIER_DEFINITIONS = [
    ("primary_10pct", "primary_10pct_pair"),
    ("stronger_20pct", "sensitivity_20pct_pair"),
    ("stronger_30pct", "sensitivity_30pct_pair"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_csv(frame: pd.DataFrame, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    frame.to_csv(tmp, index=False)
    os.replace(tmp, path)


def atomic_write_text(text: str, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def summarize_effects(
    frame: pd.DataFrame,
    *,
    label: str,
    exclusion_type: str,
    excluded_value: str,
) -> dict[str, object]:
    delta = pd.to_numeric(
        frame["delta_q_mmol_g"],
        errors="raise",
    ).to_numpy(dtype=float)

    if len(delta) == 0:
        return {
            "analysis": label,
            "exclusion_type": exclusion_type,
            "excluded_value": excluded_value,
            "pairs_retained": 0,
            "fraction_of_full_cohort_retained": 0.0,
            "median_delta_q_mmol_g": np.nan,
            "mean_delta_q_mmol_g": np.nan,
            "positive_effect_fraction": np.nan,
            "median_symmetric_relative_effect": np.nan,
        }

    return {
        "analysis": label,
        "exclusion_type": exclusion_type,
        "excluded_value": excluded_value,
        "pairs_retained": int(len(frame)),
        "fraction_of_full_cohort_retained": np.nan,  # filled later
        "median_delta_q_mmol_g": float(np.median(delta)),
        "mean_delta_q_mmol_g": float(np.mean(delta)),
        "positive_effect_fraction": float(np.mean(delta > 0)),
        "median_symmetric_relative_effect": float(
            pd.to_numeric(
                frame["symmetric_relative_effect"],
                errors="coerce",
            ).median()
        ),
    }


def bootstrap_median_ci(
    values: np.ndarray,
    replicates: int,
    seed: int,
    chunk_size: int,
) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)

    if len(values) == 0:
        return np.nan, np.nan

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


def fill_retained_fraction(
    frame: pd.DataFrame,
    full_n: int,
) -> pd.DataFrame:
    result = frame.copy()
    result["fraction_of_full_cohort_retained"] = (
        result["pairs_retained"] / full_n
    )
    return result


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="replace",
        )

    for path in (
        SOURCE_PATH,
        SOURCE_MANIFEST,
        SOURCE_SUMMARY,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    source_manifest = json.loads(
        SOURCE_MANIFEST.read_text(encoding="utf-8")
    )

    if source_manifest.get("completed_successfully") is not True:
        raise RuntimeError("Step 3.4 primary analysis is not marked complete")
    if source_manifest.get("pair_membership_modified") is not False:
        raise RuntimeError("primary source modified pair membership")
    if source_manifest.get("geometry_threshold_modified") is not False:
        raise RuntimeError("primary source modified geometry threshold")
    if source_manifest.get("primary_endpoint_modified") is not False:
        raise RuntimeError("primary source modified primary endpoint")

    data = pd.read_parquet(SOURCE_PATH)

    required = {
        "architecture_group_id",
        "topology",
        "driver_descriptor",
        "primary_10pct_pair",
        "sensitivity_20pct_pair",
        "sensitivity_30pct_pair",
        "delta_q_mmol_g",
        "symmetric_relative_effect",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(
            f"primary pair-effect source missing columns: {sorted(missing)}"
        )

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

    if not data["architecture_group_id"].is_unique:
        raise RuntimeError("primary pair-effect source is not one row per pair")

    full_n = len(data)

    # Read frozen baseline summary only for reference.
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
    baseline_ci_low = float(
        source_metrics[
            "bootstrap_95ci_low_median_delta_q_mmol_g"
        ]
    )
    baseline_ci_high = float(
        source_metrics[
            "bootstrap_95ci_high_median_delta_q_mmol_g"
        ]
    )

    # -----------------------------
    # Leave-one-major-topology-out.
    # Major = at least 100 frozen primary pairs, matching Figure 4 support rule.
    # -----------------------------
    topology_counts = (
        data["topology"]
        .value_counts()
        .rename_axis("topology")
        .reset_index(name="pairs")
    )

    major_topologies = (
        topology_counts.loc[
            topology_counts["pairs"] >= MIN_MAJOR_TOPOLOGY_PAIRS,
            "topology",
        ]
        .astype(str)
        .tolist()
    )

    topology_rows = []

    for topology in major_topologies:
        subset = data.loc[
            ~data["topology"].eq(topology)
        ].copy()

        row = summarize_effects(
            subset,
            label=f"exclude_{topology}",
            exclusion_type="topology",
            excluded_value=topology,
        )
        row["excluded_pairs"] = int(
            data["topology"].eq(topology).sum()
        )
        row["median_change_vs_full_mmol_g"] = (
            float(row["median_delta_q_mmol_g"])
            - baseline_median
        )
        topology_rows.append(row)

    topology_out = fill_retained_fraction(
        pd.DataFrame(topology_rows),
        full_n,
    )

    # -----------------------------
    # Leave-one-driver-out.
    # -----------------------------
    driver_counts = (
        data["driver_descriptor"]
        .value_counts()
        .rename_axis("driver_descriptor")
        .reset_index(name="pairs")
    )

    drivers = driver_counts[
        "driver_descriptor"
    ].astype(str).tolist()

    driver_rows = []

    for driver in drivers:
        subset = data.loc[
            ~data["driver_descriptor"].eq(driver)
        ].copy()

        row = summarize_effects(
            subset,
            label=f"exclude_{driver}",
            exclusion_type="driver",
            excluded_value=driver,
        )
        row["excluded_pairs"] = int(
            data["driver_descriptor"].eq(driver).sum()
        )
        row["median_change_vs_full_mmol_g"] = (
            float(row["median_delta_q_mmol_g"])
            - baseline_median
        )
        driver_rows.append(row)

    driver_out = fill_retained_fraction(
        pd.DataFrame(driver_rows),
        full_n,
    )

    # -----------------------------
    # Prespecified stress-test table.
    # -----------------------------
    stress_specs = [
        (
            "full_cohort",
            "none",
            "none",
            pd.Series(True, index=data.index),
        ),
        (
            "exclude_pcu",
            "topology",
            "pcu",
            ~data["topology"].eq("pcu"),
        ),
        (
            "exclude_fsc",
            "topology",
            "fsc",
            ~data["topology"].eq("fsc"),
        ),
        (
            "exclude_pcu_fsc",
            "topology_combined",
            "pcu+fsc",
            ~data["topology"].isin(["pcu", "fsc"]),
        ),
        (
            "exclude_ASA",
            "driver",
            "ASA",
            ~data["driver_descriptor"].eq("ASA"),
        ),
        (
            "exclude_AVA",
            "driver",
            "AVA",
            ~data["driver_descriptor"].eq("AVA"),
        ),
        (
            "exclude_ASA_AVA",
            "driver_combined",
            "ASA+AVA",
            ~data["driver_descriptor"].isin(["ASA", "AVA"]),
        ),
    ]

    stress_rows = []

    for label, exclusion_type, excluded_value, mask in stress_specs:
        subset = data.loc[mask].copy()

        row = summarize_effects(
            subset,
            label=label,
            exclusion_type=exclusion_type,
            excluded_value=excluded_value,
        )
        row["excluded_pairs"] = int(full_n - len(subset))
        row["median_change_vs_full_mmol_g"] = (
            float(row["median_delta_q_mmol_g"])
            - baseline_median
        )
        row["median_ratio_to_full"] = (
            float(row["median_delta_q_mmol_g"])
            / baseline_median
            if baseline_median != 0
            else np.nan
        )
        stress_rows.append(row)

    stress_out = fill_retained_fraction(
        pd.DataFrame(stress_rows),
        full_n,
    )

    # -----------------------------
    # Stronger-contrast tier robustness.
    # Compare full tier, exclude pcu+fsc, exclude ASA+AVA.
    # -----------------------------
    tier_rows = []

    tier_stress_specs = [
        (
            "full",
            pd.Series(True, index=data.index),
        ),
        (
            "exclude_pcu_fsc",
            ~data["topology"].isin(["pcu", "fsc"]),
        ),
        (
            "exclude_ASA_AVA",
            ~data["driver_descriptor"].isin(["ASA", "AVA"]),
        ),
    ]

    for tier_name, flag_col in TIER_DEFINITIONS:
        tier_mask = (
            data[flag_col]
            .astype("boolean")
            .fillna(False)
        )

        tier_full_n = int(tier_mask.sum())

        for stress_name, stress_mask in tier_stress_specs:
            subset = data.loc[
                tier_mask & stress_mask
            ].copy()

            delta = subset[
                "delta_q_mmol_g"
            ].to_numpy(dtype=float)

            tier_rows.append(
                {
                    "tier": tier_name,
                    "stress_test": stress_name,
                    "pairs_retained": int(len(subset)),
                    "fraction_of_tier_retained": (
                        float(len(subset) / tier_full_n)
                        if tier_full_n
                        else np.nan
                    ),
                    "median_delta_q_mmol_g": (
                        float(np.median(delta))
                        if len(delta)
                        else np.nan
                    ),
                    "mean_delta_q_mmol_g": (
                        float(np.mean(delta))
                        if len(delta)
                        else np.nan
                    ),
                    "positive_effect_fraction": (
                        float(np.mean(delta > 0))
                        if len(delta)
                        else np.nan
                    ),
                }
            )

    tier_out = pd.DataFrame(tier_rows)

    # -----------------------------
    # Bootstrap only the two aggressive combined exclusions.
    # These are descriptive robustness intervals, not confirmatory.
    # -----------------------------
    bootstrap_specs = [
        (
            "exclude_pcu_fsc",
            data.loc[
                ~data["topology"].isin(["pcu", "fsc"])
            ].copy(),
        ),
        (
            "exclude_ASA_AVA",
            data.loc[
                ~data["driver_descriptor"].isin(["ASA", "AVA"])
            ].copy(),
        ),
    ]

    bootstrap_rows = []

    for label, subset in bootstrap_specs:
        delta = subset[
            "delta_q_mmol_g"
        ].to_numpy(dtype=float)

        ci_low, ci_high = bootstrap_median_ci(
            delta,
            BOOTSTRAP_REPLICATES,
            BOOTSTRAP_SEED,
            BOOTSTRAP_CHUNK,
        )

        bootstrap_rows.append(
            {
                "analysis": label,
                "pairs_retained": int(len(subset)),
                "median_delta_q_mmol_g": float(
                    np.median(delta)
                ),
                "bootstrap_replicates": BOOTSTRAP_REPLICATES,
                "bootstrap_seed": BOOTSTRAP_SEED,
                "bootstrap_95ci_low_median_delta_q_mmol_g": ci_low,
                "bootstrap_95ci_high_median_delta_q_mmol_g": ci_high,
            }
        )

    bootstrap_out = pd.DataFrame(bootstrap_rows)

    # Save.
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    atomic_write_csv(
        topology_out.sort_values(
            ["excluded_pairs", "excluded_value"],
            ascending=[False, True],
        ).reset_index(drop=True),
        OUTPUT_DIR / "leave_one_topology_out.csv",
    )

    atomic_write_csv(
        driver_out.sort_values(
            ["excluded_pairs", "excluded_value"],
            ascending=[False, True],
        ).reset_index(drop=True),
        OUTPUT_DIR / "leave_one_driver_out.csv",
    )

    atomic_write_csv(
        stress_out,
        OUTPUT_DIR / "dominant_context_stress_tests.csv",
    )

    atomic_write_csv(
        tier_out,
        OUTPUT_DIR / "geometry_tier_stress_tests.csv",
    )

    atomic_write_csv(
        bootstrap_out,
        OUTPUT_DIR / "aggressive_stress_bootstrap.csv",
    )

    definition = {
        "definition_version": DEFINITION_VERSION,
        "source": str(SOURCE_PATH.relative_to(ROOT)),
        "analysis_status": "secondary robustness analysis",
        "major_topology_rule": (
            f"topologies with at least {MIN_MAJOR_TOPOLOGY_PAIRS} "
            "frozen primary pairs"
        ),
        "leave_one_topology_out": True,
        "leave_one_driver_out": True,
        "aggressive_topology_stress_test": "exclude pcu + fsc",
        "aggressive_driver_stress_test": "exclude ASA + AVA",
        "tier_stress_tests": [
            "primary_10pct",
            "stronger_20pct",
            "stronger_30pct",
        ],
        "bootstrap": {
            "applied_only_to": [
                "exclude_pcu_fsc",
                "exclude_ASA_AVA",
            ],
            "replicates": BOOTSTRAP_REPLICATES,
            "seed": BOOTSTRAP_SEED,
            "interval": "percentile 95%",
            "role": (
                "secondary/descriptive robustness interval; "
                "does not replace confirmatory CI"
            ),
        },
        "frozen_confirmatory_reference": {
            "median_delta_q_mmol_g": baseline_median,
            "bootstrap_95ci_low_median_delta_q_mmol_g": baseline_ci_low,
            "bootstrap_95ci_high_median_delta_q_mmol_g": baseline_ci_high,
        },
        "raw_outcome_files_read": False,
        "pair_membership_modified": False,
        "pair_orientation_modified": False,
        "geometry_threshold_modified": False,
        "primary_endpoint_modified": False,
        "primary_estimand_modified": False,
    }

    manifest = {
        "script": Path(__file__).name,
        "script_version": SCRIPT_VERSION,
        "definition_version": DEFINITION_VERSION,
        "completed_at_utc": utc_now(),
        "completed_successfully": True,
        "raw_outcome_files_read": False,
        "source_primary_pairs": int(full_n),
        "major_topologies_tested": major_topologies,
        "drivers_tested": drivers,
        "bootstrap_replicates_for_aggressive_tests": (
            BOOTSTRAP_REPLICATES
        ),
        "pair_membership_modified": False,
        "pair_orientation_modified": False,
        "geometry_threshold_modified": False,
        "primary_endpoint_modified": False,
        "primary_estimand_modified": False,
    }

    atomic_write_text(
        json.dumps(definition, indent=2),
        OUTPUT_DIR / "robustness_definition.json",
    )

    atomic_write_text(
        json.dumps(manifest, indent=2),
        OUTPUT_DIR / "run_manifest.json",
    )

    print("PROJECT 17 - STEP 3.8 DOMINANT-CONTEXT ROBUSTNESS")
    print(
        "Policy: audited primary pair effects only; "
        "no raw outcomes; all frozen definitions unchanged"
    )
    print()
    print(
        f"Frozen primary pairs: {full_n:,}"
    )
    print(
        f"Frozen baseline median delta q: "
        f"{baseline_median:.6f} mmol/g"
    )
    print(
        f"Frozen baseline 95% CI: "
        f"[{baseline_ci_low:.6f}, {baseline_ci_high:.6f}]"
    )

    print()
    print("LEAVE-ONE-MAJOR-TOPOLOGY-OUT")
    print(
        topology_out[
            [
                "excluded_value",
                "excluded_pairs",
                "pairs_retained",
                "median_delta_q_mmol_g",
                "positive_effect_fraction",
                "median_change_vs_full_mmol_g",
            ]
        ].to_string(index=False)
    )

    print()
    print("LEAVE-ONE-DRIVER-OUT")
    print(
        driver_out[
            [
                "excluded_value",
                "excluded_pairs",
                "pairs_retained",
                "median_delta_q_mmol_g",
                "positive_effect_fraction",
                "median_change_vs_full_mmol_g",
            ]
        ].to_string(index=False)
    )

    print()
    print("AGGRESSIVE COMBINED STRESS TESTS")
    print(
        stress_out.loc[
            stress_out["analysis"].isin(
                ["full_cohort", "exclude_pcu_fsc", "exclude_ASA_AVA"]
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

    print()
    print("AGGRESSIVE STRESS BOOTSTRAP")
    print(
        bootstrap_out.to_string(index=False)
    )

    print()
    print("GEOMETRY-TIER STRESS TESTS")
    print(
        tier_out.to_string(index=False)
    )

    print()
    print(f"Saved results: {OUTPUT_DIR}")
    print("Stop here and run py .\\test_14.py.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
