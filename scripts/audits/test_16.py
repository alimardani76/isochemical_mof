#!/usr/bin/env python3
"""Audit Project 17 Step 3.10 ARC-MOF database provenance robustness."""

from __future__ import annotations

import json
import re
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
    / "09_database_provenance_robustness"
)

EXPECTED_FILES = [
    "01_pair_provenance.parquet",
    "02_source_pair_census.csv",
    "03_provenance_class_summary.csv",
    "04_leave_one_source_out.csv",
    "05_asa_ava_provenance_summary.csv",
    "06_asa_ava_leave_one_source_out.csv",
    "07_provenance_definition.json",
    "08_run_manifest.json",
]

DEFINITION_VERSION = "arcmof_database_provenance_robustness_v1"
MAJOR_SOURCE_MIN_TOUCHED_PAIRS = 100

EXPERIMENTAL_SOURCES = {"DB12", "DB14"}
HYPOTHETICAL_SOURCES = {
    "DB0", "DB1", "DB2", "DB3", "DB4", "DB5",
    "DB6", "DB7", "DB8", "DB10", "DB13", "DB15",
}
KNOWN_SOURCES = EXPERIMENTAL_SOURCES | HYPOTHETICAL_SOURCES

DB_RE = re.compile(r"^(DB\d+)-", flags=re.IGNORECASE)


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


def source_from_mof_id(value: object) -> str:
    match = DB_RE.match(str(value).strip())
    if match is None:
        raise ValueError(value)
    source = match.group(1).upper()
    if source not in KNOWN_SOURCES:
        raise ValueError(source)
    return source


def source_kind(source: str) -> str:
    if source in EXPERIMENTAL_SOURCES:
        return "experimental"
    if source in HYPOTHETICAL_SOURCES:
        return "hypothetical"
    raise ValueError(source)


def summarize(frame: pd.DataFrame):
    delta = pd.to_numeric(
        frame["delta_q_mmol_g"],
        errors="raise",
    ).to_numpy(dtype=float)

    if len(delta) == 0:
        return 0, np.nan, np.nan, np.nan

    return (
        len(delta),
        float(np.median(delta)),
        float(np.mean(delta)),
        float(np.mean(delta > 0)),
    )


def close(a, b):
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

    print("PROJECT 17 - STEP 3.10 PROVENANCE AUDIT")

    audit.check(
        RESULTS.is_dir(),
        "Step 3.10 result folder exists",
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
        "all expected Step 3.10 files exist",
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

    definition = json.loads(
        (RESULTS / "07_provenance_definition.json")
        .read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (RESULTS / "08_run_manifest.json")
        .read_text(encoding="utf-8")
    )

    stored_pairs = pd.read_parquet(
        RESULTS / "01_pair_provenance.parquet"
    )
    class_out = pd.read_csv(
        RESULTS / "03_provenance_class_summary.csv"
    )
    leave_out = pd.read_csv(
        RESULTS / "04_leave_one_source_out.csv"
    )
    favorable_out = pd.read_csv(
        RESULTS / "05_asa_ava_provenance_summary.csv"
    )
    favorable_leave_out = pd.read_csv(
        RESULTS / "06_asa_ava_leave_one_source_out.csv"
    )

    source = pd.read_parquet(SOURCE_PATH).copy()

    print("\nPOLICY")

    audit.check(
        manifest.get("completed_successfully") is True,
        "manifest records successful completion",
    )
    audit.check(
        manifest.get("definition_version") == DEFINITION_VERSION,
        "definition version is exact",
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

    print("\nPROVENANCE DEFINITION")

    audit.check(
        definition.get("definition_version") == DEFINITION_VERSION,
        "definition file version is exact",
    )
    audit.check(
        set(definition.get("experimental_sources", []))
        == EXPERIMENTAL_SOURCES,
        "experimental DB mapping is exact",
    )
    audit.check(
        set(definition.get("hypothetical_sources", []))
        == HYPOTHETICAL_SOURCES,
        "hypothetical DB mapping is exact",
    )
    audit.check(
        definition.get("major_source_min_touched_pairs")
        == MAJOR_SOURCE_MIN_TOUCHED_PAIRS,
        "major-source support threshold is exact",
    )

    print("\nPAIR-LEVEL RECONSTRUCTION")

    source["source_low"] = source[
        "driver_low_mof_id"
    ].map(source_from_mof_id)
    source["source_high"] = source[
        "driver_high_mof_id"
    ].map(source_from_mof_id)

    source["source_kind_low"] = source[
        "source_low"
    ].map(source_kind)
    source["source_kind_high"] = source[
        "source_high"
    ].map(source_kind)

    source["same_source_pair"] = (
        source["source_low"] == source["source_high"]
    )

    source["source_pair"] = [
        "|".join(sorted((a, b)))
        for a, b in zip(
            source["source_low"],
            source["source_high"],
        )
    ]

    source["provenance_class"] = [
        (
            "hypothetical_hypothetical"
            if a == "hypothetical"
            and b == "hypothetical"
            else (
                "experimental_experimental"
                if a == "experimental"
                and b == "experimental"
                else "mixed_hypothetical_experimental"
            )
        )
        for a, b in zip(
            source["source_kind_low"],
            source["source_kind_high"],
        )
    ]

    audit.check(
        len(source) == 11072,
        "source contains exactly 11,072 frozen pairs",
    )
    audit.check(
        source["architecture_group_id"].is_unique,
        "source remains one row per frozen pair",
    )
    audit.check(
        len(stored_pairs) == len(source),
        "stored provenance table preserves all frozen pairs",
    )

    key_cols = [
        "architecture_group_id",
        "source_low",
        "source_high",
        "source_kind_low",
        "source_kind_high",
        "same_source_pair",
        "source_pair",
        "provenance_class",
    ]

    reconstructed = source[
        key_cols
    ].sort_values(
        "architecture_group_id"
    ).reset_index(drop=True)

    stored = stored_pairs[
        key_cols
    ].sort_values(
        "architecture_group_id"
    ).reset_index(drop=True)

    audit.check(
        reconstructed.equals(stored),
        "all pair provenance labels reconstruct exactly",
    )

    print("\nPROVENANCE CLASS SUMMARY")

    summary = pd.read_csv(SOURCE_SUMMARY)
    metrics = dict(
        zip(
            summary["metric"].astype(str),
            pd.to_numeric(
                summary["value"],
                errors="coerce",
            ),
        )
    )
    baseline_median = float(
        metrics["median_delta_q_mmol_g"]
    )

    class_masks = {
        "full_cohort": pd.Series(
            True,
            index=source.index,
        ),
        "same_source": source["same_source_pair"],
        "cross_source": ~source["same_source_pair"],
        "hypothetical_hypothetical":
            source["provenance_class"].eq(
                "hypothetical_hypothetical"
            ),
        "experimental_experimental":
            source["provenance_class"].eq(
                "experimental_experimental"
            ),
        "mixed_hypothetical_experimental":
            source["provenance_class"].eq(
                "mixed_hypothetical_experimental"
            ),
    }

    class_exact = True
    for row in class_out.itertuples(index=False):
        name = str(row.population)
        if name not in class_masks:
            class_exact = False
            break

        n, median, mean, positive = summarize(
            source.loc[class_masks[name]]
        )

        if not (
            int(row.pairs) == n
            and close(row.median_delta_q_mmol_g, median)
            and close(row.mean_delta_q_mmol_g, mean)
            and close(row.positive_effect_fraction, positive)
            and close(
                row.median_change_vs_full_mmol_g,
                median - baseline_median,
            )
        ):
            class_exact = False
            break

    audit.check(
        class_exact,
        "all broad provenance summaries are exact",
    )

    print("\nLEAVE-ONE-SOURCE-OUT")

    touched_counts = {}
    for db in sorted(KNOWN_SOURCES):
        touched_counts[db] = int(
            (
                source["source_low"].eq(db)
                | source["source_high"].eq(db)
            ).sum()
        )

    expected_major = sorted(
        db
        for db, count in touched_counts.items()
        if count >= MAJOR_SOURCE_MIN_TOUCHED_PAIRS
    )
    observed_major = sorted(
        leave_out["excluded_source"]
        .astype(str)
        .tolist()
    )

    audit.check(
        expected_major == observed_major,
        "major source population is exact",
    )

    leave_exact = True

    for row in leave_out.itertuples(index=False):
        db = str(row.excluded_source)

        block = source.loc[
            ~(
                source["source_low"].eq(db)
                | source["source_high"].eq(db)
            )
        ]

        n, median, mean, positive = summarize(
            block
        )

        if not (
            int(row.pairs_touching_source)
            == touched_counts[db]
            and int(row.pairs_retained) == n
            and close(
                row.median_delta_q_mmol_g,
                median,
            )
            and close(
                row.mean_delta_q_mmol_g,
                mean,
            )
            and close(
                row.positive_effect_fraction,
                positive,
            )
            and close(
                row.median_change_vs_full_mmol_g,
                median - baseline_median,
            )
        ):
            leave_exact = False
            break

    audit.check(
        leave_exact,
        "all leave-one-source-out results are exact",
    )

    print("\nASA/AVA PROVENANCE")

    favorable = source.loc[
        source["driver_descriptor"].isin(
            ["ASA", "AVA"]
        )
    ].copy()

    favorable_baseline = float(
        np.median(
            favorable["delta_q_mmol_g"]
            .to_numpy(dtype=float)
        )
    )

    favorable_masks = {
        "ASA_AVA_all": pd.Series(
            True,
            index=favorable.index,
        ),
        "ASA_AVA_same_source":
            favorable["same_source_pair"],
        "ASA_AVA_cross_source":
            ~favorable["same_source_pair"],
        "ASA_AVA_hypothetical_hypothetical":
            favorable["provenance_class"].eq(
                "hypothetical_hypothetical"
            ),
        "ASA_AVA_experimental_experimental":
            favorable["provenance_class"].eq(
                "experimental_experimental"
            ),
        "ASA_AVA_mixed_hypothetical_experimental":
            favorable["provenance_class"].eq(
                "mixed_hypothetical_experimental"
            ),
    }

    favorable_exact = True

    for row in favorable_out.itertuples(index=False):
        name = str(row.population)

        if name not in favorable_masks:
            favorable_exact = False
            break

        block = favorable.loc[
            favorable_masks[name]
        ]

        n, median, mean, positive = summarize(
            block
        )

        if not (
            int(row.pairs) == n
            and close(
                row.median_delta_q_mmol_g,
                median,
            )
            and close(
                row.mean_delta_q_mmol_g,
                mean,
            )
            and close(
                row.positive_effect_fraction,
                positive,
            )
            and close(
                row.median_change_vs_ASA_AVA_full_mmol_g,
                (
                    median - favorable_baseline
                    if n
                    else np.nan
                ),
            )
        ):
            favorable_exact = False
            break

    audit.check(
        favorable_exact,
        "ASA/AVA provenance summaries are exact",
    )

    favorable_touched = {}
    for db in sorted(KNOWN_SOURCES):
        favorable_touched[db] = int(
            (
                favorable["source_low"].eq(db)
                | favorable["source_high"].eq(db)
            ).sum()
        )

    expected_favorable_major = sorted(
        db
        for db, count in favorable_touched.items()
        if count >= MAJOR_SOURCE_MIN_TOUCHED_PAIRS
    )
    observed_favorable_major = sorted(
        favorable_leave_out["excluded_source"]
        .astype(str)
        .tolist()
    )

    audit.check(
        expected_favorable_major
        == observed_favorable_major,
        "ASA/AVA major source population is exact",
    )

    favorable_leave_exact = True

    for row in favorable_leave_out.itertuples(
        index=False
    ):
        db = str(row.excluded_source)

        block = favorable.loc[
            ~(
                favorable["source_low"].eq(db)
                | favorable["source_high"].eq(db)
            )
        ]

        n, median, mean, positive = summarize(
            block
        )

        if not (
            int(row.ASA_AVA_pairs_touching_source)
            == favorable_touched[db]
            and int(row.pairs_retained) == n
            and close(
                row.median_delta_q_mmol_g,
                median,
            )
            and close(
                row.mean_delta_q_mmol_g,
                mean,
            )
            and close(
                row.positive_effect_fraction,
                positive,
            )
            and close(
                row.median_change_vs_ASA_AVA_full_mmol_g,
                median - favorable_baseline,
            )
        ):
            favorable_leave_exact = False
            break

    audit.check(
        favorable_leave_exact,
        "ASA/AVA leave-one-source-out results are exact",
    )

    print("\nSCIENTIFIC CENSUS")
    print(
        class_out[
            [
                "population",
                "pairs",
                "median_delta_q_mmol_g",
                "positive_effect_fraction",
            ]
        ].to_string(index=False)
    )

    print()
    print(
        leave_out[
            [
                "excluded_source",
                "source_kind",
                "pairs_touching_source",
                "pairs_retained",
                "median_delta_q_mmol_g",
                "positive_effect_fraction",
            ]
        ].to_string(index=False)
    )

    print("\nOVERALL RESULT")

    if audit.failures:
        print(
            f"FAIL - {len(audit.failures)} hard check(s) failed. "
            "Do not freeze provenance claims."
        )
        return 1

    print(
        "PASS - database-provenance robustness reproduces exactly."
    )
    print(
        "Next: interpret whether one ARC-MOF source dominates the "
        "primary or ASA/AVA result, then finalize manuscript/SI."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
