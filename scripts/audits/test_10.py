#!/usr/bin/env python3
"""Audit Project 17 Step 3.4 primary CH4 analysis."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent

PAIR_PATH = (
    ROOT
    / "Step 2 results"
    / "03_geometry_pairs"
    / "primary_geometry_pairs.parquet"
)
FREEZE_DEFINITION = (
    ROOT
    / "Step 3 results"
    / "03_primary_endpoint_freeze"
    / "primary_endpoint_definition.json"
)
METHANE_PATH = ROOT / "raw" / "methane.csv"

RESULTS = (
    ROOT
    / "Step 3 results"
    / "04_primary_ch4_analysis"
)

DEFINITION_VERSION = "primary_ch4_298K_65bar_mmolg_v1"

EXPECTED_FILES = [
    "primary_ch4_pair_effects.parquet",
    "primary_ch4_summary.csv",
    "primary_ch4_geometry_tier_summary.csv",
    "primary_ch4_driver_summary.csv",
    "primary_ch4_topology_summary.csv",
    "primary_ch4_bootstrap_medians.csv",
    "primary_ch4_analysis_definition.json",
    "run_manifest.json",
]

SUFFIX_PATTERN = re.compile(r"(?i)(?:\.cif|_repeat|_sqe)$")


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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
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


def symmetric_relative_effect(q_high, q_low):
    denominator = np.abs(q_high) + np.abs(q_low)
    numerator = 2.0 * (q_high - q_low)
    return np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator, dtype=float),
        where=denominator != 0,
    )


def bootstrap_medians(values, replicates=10000, seed=17, chunk_size=250):
    rng = np.random.default_rng(seed)
    n = len(values)
    output = np.empty(replicates, dtype=float)
    written = 0

    while written < replicates:
        k = min(chunk_size, replicates - written)
        indices = rng.integers(
            0,
            n,
            size=(k, n),
            endpoint=False,
        )
        output[written:written+k] = np.median(
            values[indices],
            axis=1,
        )
        written += k

    return output


def main() -> int:
    audit = Audit()

    print("PROJECT 17 - STEP 3.4 PRIMARY CH4 ANALYSIS AUDIT")

    audit.check(RESULTS.is_dir(), "Step 3.4 result folder exists")
    if not RESULTS.is_dir():
        return 1

    missing = [
        name for name in EXPECTED_FILES
        if not (RESULTS / name).is_file()
    ]
    audit.check(not missing, "all expected Step 3.4 files exist")
    if missing:
        print("Missing:", missing)
        return 1

    for path, label in (
        (PAIR_PATH, "frozen pair source exists"),
        (FREEZE_DEFINITION, "endpoint freeze definition exists"),
        (METHANE_PATH, "methane source exists"),
    ):
        audit.check(path.is_file(), label)

    if audit.failures:
        return 1

    manifest = json.loads(
        (RESULTS / "run_manifest.json").read_text(encoding="utf-8")
    )
    definition = json.loads(
        (RESULTS / "primary_ch4_analysis_definition.json")
        .read_text(encoding="utf-8")
    )
    freeze = json.loads(
        FREEZE_DEFINITION.read_text(encoding="utf-8")
    )

    effects = pd.read_parquet(
        RESULTS / "primary_ch4_pair_effects.parquet"
    )
    summary = pd.read_csv(
        RESULTS / "primary_ch4_summary.csv"
    )
    bootstrap_saved = pd.read_csv(
        RESULTS / "primary_ch4_bootstrap_medians.csv"
    )["bootstrap_median_delta_q_mmol_g"].to_numpy(dtype=float)

    pairs = pd.read_parquet(PAIR_PATH)

    print("\nPOLICY")
    audit.check(
        manifest.get("completed_successfully") is True,
        "manifest records successful completion",
    )
    audit.check(
        manifest.get("definition_version") == DEFINITION_VERSION,
        "correct analysis definition is recorded",
    )
    audit.check(
        manifest.get("primary_endpoint_only") is True,
        "only the frozen primary endpoint was analyzed",
    )
    audit.check(
        manifest.get("outcome_values_read") is True,
        "manifest records primary outcome value access",
    )
    audit.check(
        manifest.get("other_outcome_tables_read") is False,
        "no other outcome tables were read",
    )
    audit.check(
        manifest.get("other_outcome_columns_read") is False,
        "no other outcome columns were read",
    )
    audit.check(
        manifest.get("pair_membership_modified") is False,
        "pair membership was not modified",
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
        manifest.get("pair_source_sha256") == sha256_file(PAIR_PATH),
        "frozen pair source hash matches",
    )
    audit.check(
        manifest.get("freeze_definition_sha256")
        == sha256_file(FREEZE_DEFINITION),
        "endpoint freeze hash matches",
    )
    audit.check(
        manifest.get("methane_source_sha256")
        == sha256_file(METHANE_PATH),
        "methane source hash matches",
    )

    print("\nFROZEN ENDPOINT")
    primary = freeze["primary_endpoint"]
    audit.check(
        primary["source"] == "methane.csv",
        "source is methane.csv",
    )
    audit.check(
        float(primary["temperature_K"]) == 298.0,
        "temperature is 298 K",
    )
    audit.check(
        float(primary["pressure_bar"]) == 65.0,
        "pressure is 65 bar",
    )
    audit.check(
        primary["uptake_column"] == "mmol/g",
        "outcome basis is mmol/g",
    )
    audit.check(
        definition.get("outcome_columns_read")
        == ["filename", "T/K", "p/bar", "mmol/g"],
        "outcome access columns are exact",
    )

    print("\nFULL OUTCOME RECONSTRUCTION")
    methane = pd.read_csv(
        METHANE_PATH,
        usecols=["filename", "T/K", "p/bar", "mmol/g"],
        low_memory=False,
    )
    methane["mof_id"] = canonicalize_ids(methane["filename"])
    methane["T/K"] = pd.to_numeric(methane["T/K"], errors="raise")
    methane["p/bar"] = pd.to_numeric(methane["p/bar"], errors="raise")
    methane["mmol/g"] = pd.to_numeric(
        methane["mmol/g"],
        errors="coerce",
    )

    endpoint = methane.loc[
        methane["T/K"].eq(298.0)
        & methane["p/bar"].eq(65.0),
        ["mof_id", "mmol/g"],
    ].copy()

    audit.check(
        not endpoint.duplicated("mof_id").any(),
        "primary endpoint has one row per canonical framework ID",
    )

    lookup = endpoint.set_index("mof_id")["mmol/g"]

    expected = pairs.copy()
    expected["q_low"] = expected["driver_low_mof_id"].astype("string").map(lookup)
    expected["q_high"] = expected["driver_high_mof_id"].astype("string").map(lookup)
    expected["complete"] = expected["q_low"].notna() & expected["q_high"].notna()
    expected = expected.loc[expected["complete"]].copy()
    expected["delta"] = expected["q_high"] - expected["q_low"]

    observed_ids = set(effects["architecture_group_id"].astype(str))
    expected_ids = set(expected["architecture_group_id"].astype(str))

    audit.check(
        observed_ids == expected_ids,
        "analysis table contains exactly all complete frozen pairs",
    )

    effects_indexed = effects.set_index("architecture_group_id")
    expected_indexed = expected.set_index("architecture_group_id")

    common = sorted(expected_ids)

    q_low_exact = np.allclose(
        effects_indexed.loc[common, "q_geometry_low_mmol_g"].to_numpy(dtype=float),
        expected_indexed.loc[common, "q_low"].to_numpy(dtype=float),
        rtol=0,
        atol=1e-12,
        equal_nan=True,
    )
    q_high_exact = np.allclose(
        effects_indexed.loc[common, "q_geometry_high_mmol_g"].to_numpy(dtype=float),
        expected_indexed.loc[common, "q_high"].to_numpy(dtype=float),
        rtol=0,
        atol=1e-12,
        equal_nan=True,
    )
    delta_exact = np.allclose(
        effects_indexed.loc[common, "delta_q_mmol_g"].to_numpy(dtype=float),
        expected_indexed.loc[common, "delta"].to_numpy(dtype=float),
        rtol=0,
        atol=1e-12,
        equal_nan=True,
    )

    audit.check(q_low_exact, "geometry-low uptake values are exact")
    audit.check(q_high_exact, "geometry-high uptake values are exact")
    audit.check(delta_exact, "signed uptake differences are exact")

    q_low = effects["q_geometry_low_mmol_g"].to_numpy(dtype=float)
    q_high = effects["q_geometry_high_mmol_g"].to_numpy(dtype=float)
    expected_rel = symmetric_relative_effect(q_high, q_low)

    audit.check(
        np.allclose(
            effects["symmetric_relative_effect"].to_numpy(dtype=float),
            expected_rel,
            rtol=0,
            atol=1e-12,
            equal_nan=True,
        ),
        "symmetric relative effects are exact",
    )

    print("\nPRIMARY SUMMARY")
    summary_dict = dict(
        zip(summary["metric"].astype(str), summary["value"])
    )

    delta = effects["delta_q_mmol_g"].to_numpy(dtype=float)
    observed_median = float(np.median(delta))
    observed_mean = float(np.mean(delta))
    observed_positive = float(np.mean(delta > 0))

    audit.check(
        np.isclose(
            float(summary_dict["median_delta_q_mmol_g"]),
            observed_median,
            rtol=0,
            atol=1e-12,
        ),
        "primary median effect is exact",
    )
    audit.check(
        np.isclose(
            float(summary_dict["mean_delta_q_mmol_g"]),
            observed_mean,
            rtol=0,
            atol=1e-12,
        ),
        "mean effect is exact",
    )
    audit.check(
        np.isclose(
            float(summary_dict["positive_effect_fraction"]),
            observed_positive,
            rtol=0,
            atol=1e-12,
        ),
        "positive-effect fraction is exact",
    )

    print("\nBOOTSTRAP")
    expected_bootstrap = bootstrap_medians(
        delta,
        replicates=10000,
        seed=17,
        chunk_size=250,
    )

    audit.check(
        np.allclose(
            bootstrap_saved,
            expected_bootstrap,
            rtol=0,
            atol=1e-12,
        ),
        "all 10,000 bootstrap medians reproduce exactly",
    )

    low, high = np.percentile(expected_bootstrap, [2.5, 97.5])

    audit.check(
        np.isclose(
            float(
                summary_dict[
                    "bootstrap_95ci_low_median_delta_q_mmol_g"
                ]
            ),
            float(low),
            rtol=0,
            atol=1e-12,
        ),
        "bootstrap lower 95% bound is exact",
    )
    audit.check(
        np.isclose(
            float(
                summary_dict[
                    "bootstrap_95ci_high_median_delta_q_mmol_g"
                ]
            ),
            float(high),
            rtol=0,
            atol=1e-12,
        ),
        "bootstrap upper 95% bound is exact",
    )

    print("\nSCIENTIFIC CENSUS")
    print(f"  Frozen pairs: {len(pairs):,}")
    print(f"  Complete primary pairs: {len(effects):,}")
    print(f"  Median delta q: {observed_median:.6f} mmol/g")
    print(f"  95% bootstrap CI: [{low:.6f}, {high:.6f}] mmol/g")
    print(f"  Mean delta q: {observed_mean:.6f} mmol/g")
    print(f"  Fraction positive: {observed_positive:.4f}")

    print("\nOVERALL RESULT")
    if audit.failures:
        print(
            f"FAIL - {len(audit.failures)} hard check(s) failed. "
            "Do not generate Figure 2."
        )
        return 1

    print(
        "PASS - primary CH4 Figure 2 analysis is internally consistent "
        "and exactly reproduces the frozen endpoint/estimand."
    )
    print(
        "Next: interpret the primary result and generate Figure 2 from "
        "primary_ch4_pair_effects.parquet plus the frozen summary tables."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
