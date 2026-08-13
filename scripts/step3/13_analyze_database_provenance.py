#!/usr/bin/env python3
"""
Project 17 Step 3.10: ARC-MOF database-provenance robustness.

Purpose
-------
Final bounded robustness analysis motivated by ARC-MOF source heterogeneity.

Questions
---------
1. Is the frozen 65-bar CH4 result dominated by one ARC-MOF source database?
2. Does the result differ between same-source and cross-source frozen pairs?
3. Where provenance permits, how do hypothetical-only, experimental-only,
   and mixed hypothetical/experimental pairs behave?
4. Is the favorable ASA/AVA-driven primary signal concentrated in one source?

This analysis is secondary/descriptive. It does NOT change:
- chemistry definition,
- architecture definition,
- geometry threshold,
- frozen pair membership,
- pair orientation,
- primary endpoint,
- primary estimand.

Input
-----
Step 3 results/04_primary_ch4_analysis/primary_ch4_pair_effects.parquet

ARC-MOF provenance rule
-----------------------
The ARC-MOF paper states that filenames comprise a "DBx-" prefix identifying the
source database. DB12 (CoRE 2019) and DB14 (CSD-MOF) are experimental collections.
The other DB labels present in ARC-MOF Table 1 are computationally generated /
hypothetical sources:
DB0, DB1, DB2, DB3, DB4, DB5, DB6, DB7, DB8, DB10, DB13, DB15.

Outputs
-------
01_pair_provenance.parquet
02_source_pair_census.csv
03_provenance_class_summary.csv
04_leave_one_source_out.csv
05_asa_ava_provenance_summary.csv
06_asa_ava_leave_one_source_out.csv
07_provenance_definition.json
08_run_manifest.json
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT_VERSION = "1.0.0"
DEFINITION_VERSION = "arcmof_database_provenance_robustness_v1"

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
    / "09_database_provenance_robustness"
)

MAJOR_SOURCE_MIN_TOUCHED_PAIRS = 100

EXPERIMENTAL_SOURCES = {"DB12", "DB14"}
HYPOTHETICAL_SOURCES = {
    "DB0", "DB1", "DB2", "DB3", "DB4", "DB5",
    "DB6", "DB7", "DB8", "DB10", "DB13", "DB15",
}
KNOWN_SOURCES = EXPERIMENTAL_SOURCES | HYPOTHETICAL_SOURCES

DB_RE = re.compile(r"^(DB\d+)-", flags=re.IGNORECASE)


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


def source_from_mof_id(value: object) -> str:
    text = str(value).strip()
    match = DB_RE.match(text)
    if match is None:
        raise ValueError(
            f"cannot recover ARC-MOF DB prefix from framework ID: {text!r}"
        )
    source = match.group(1).upper()
    if source not in KNOWN_SOURCES:
        raise ValueError(
            f"framework ID uses DB source not covered by frozen mapping: "
            f"{source} from {text!r}"
        )
    return source


def source_kind(source: str) -> str:
    if source in EXPERIMENTAL_SOURCES:
        return "experimental"
    if source in HYPOTHETICAL_SOURCES:
        return "hypothetical"
    raise ValueError(source)


def summarize(
    frame: pd.DataFrame,
    *,
    population: str,
) -> dict[str, object]:
    delta = pd.to_numeric(
        frame["delta_q_mmol_g"],
        errors="raise",
    ).to_numpy(dtype=float)

    if len(delta) == 0:
        return {
            "population": population,
            "pairs": 0,
            "median_delta_q_mmol_g": np.nan,
            "mean_delta_q_mmol_g": np.nan,
            "positive_effect_fraction": np.nan,
            "median_symmetric_relative_effect": np.nan,
        }

    return {
        "population": population,
        "pairs": int(len(frame)),
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

    manifest = json.loads(
        SOURCE_MANIFEST.read_text(encoding="utf-8")
    )

    if manifest.get("completed_successfully") is not True:
        raise RuntimeError(
            "frozen primary analysis is not marked complete"
        )

    data = pd.read_parquet(SOURCE_PATH)

    required = {
        "architecture_group_id",
        "driver_low_mof_id",
        "driver_high_mof_id",
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

    if len(data) != 11072:
        raise RuntimeError(
            f"expected 11,072 frozen primary pairs, found {len(data):,}"
        )

    if not data["architecture_group_id"].is_unique:
        raise RuntimeError(
            "primary source is not one row per frozen pair"
        )

    data = data.copy()

    data["source_low"] = data[
        "driver_low_mof_id"
    ].map(source_from_mof_id)

    data["source_high"] = data[
        "driver_high_mof_id"
    ].map(source_from_mof_id)

    data["source_kind_low"] = data[
        "source_low"
    ].map(source_kind)

    data["source_kind_high"] = data[
        "source_high"
    ].map(source_kind)

    data["same_source_pair"] = (
        data["source_low"] == data["source_high"]
    )

    data["source_pair"] = [
        "|".join(sorted((a, b)))
        for a, b in zip(
            data["source_low"],
            data["source_high"],
        )
    ]

    provenance_class = []
    for low_kind, high_kind in zip(
        data["source_kind_low"],
        data["source_kind_high"],
    ):
        if (
            low_kind == "hypothetical"
            and high_kind == "hypothetical"
        ):
            provenance_class.append(
                "hypothetical_hypothetical"
            )
        elif (
            low_kind == "experimental"
            and high_kind == "experimental"
        ):
            provenance_class.append(
                "experimental_experimental"
            )
        else:
            provenance_class.append(
                "mixed_hypothetical_experimental"
            )

    data["provenance_class"] = provenance_class

    # Exact baseline reference.
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

    # 1. Source-pair census.
    source_pair_rows = []

    for source_pair, block in data.groupby(
        "source_pair",
        sort=True,
        observed=True,
    ):
        row = summarize(
            block,
            population=str(source_pair),
        )
        row["source_pair"] = str(source_pair)
        row["same_source_pair"] = bool(
            block["same_source_pair"].iloc[0]
        )
        source_pair_rows.append(row)

    source_pair_out = pd.DataFrame(
        source_pair_rows
    ).sort_values(
        ["pairs", "source_pair"],
        ascending=[False, True],
    )

    # 2. Broad provenance classes.
    class_specs = [
        (
            "full_cohort",
            pd.Series(True, index=data.index),
        ),
        (
            "same_source",
            data["same_source_pair"],
        ),
        (
            "cross_source",
            ~data["same_source_pair"],
        ),
        (
            "hypothetical_hypothetical",
            data["provenance_class"].eq(
                "hypothetical_hypothetical"
            ),
        ),
        (
            "experimental_experimental",
            data["provenance_class"].eq(
                "experimental_experimental"
            ),
        ),
        (
            "mixed_hypothetical_experimental",
            data["provenance_class"].eq(
                "mixed_hypothetical_experimental"
            ),
        ),
    ]

    class_rows = []

    for name, mask in class_specs:
        row = summarize(
            data.loc[mask],
            population=name,
        )
        row[
            "fraction_of_full_cohort"
        ] = row["pairs"] / len(data)
        row[
            "median_change_vs_full_mmol_g"
        ] = (
            float(row["median_delta_q_mmol_g"])
            - baseline_median
            if row["pairs"] > 0
            else np.nan
        )
        class_rows.append(row)

    class_out = pd.DataFrame(class_rows)

    # 3. Source incidence and leave-one-source-out.
    touched_counts = {}

    for source in sorted(KNOWN_SOURCES):
        touched = (
            data["source_low"].eq(source)
            | data["source_high"].eq(source)
        )
        touched_counts[source] = int(touched.sum())

    major_sources = [
        source
        for source, count in touched_counts.items()
        if count >= MAJOR_SOURCE_MIN_TOUCHED_PAIRS
    ]

    leave_rows = []

    for source in major_sources:
        keep = ~(
            data["source_low"].eq(source)
            | data["source_high"].eq(source)
        )
        block = data.loc[keep]

        row = summarize(
            block,
            population=f"exclude_{source}",
        )
        row["excluded_source"] = source
        row["source_kind"] = source_kind(source)
        row["pairs_touching_source"] = touched_counts[source]
        row["pairs_retained"] = row.pop("pairs")
        row[
            "fraction_of_full_cohort_retained"
        ] = row["pairs_retained"] / len(data)
        row[
            "median_change_vs_full_mmol_g"
        ] = (
            float(row["median_delta_q_mmol_g"])
            - baseline_median
        )
        leave_rows.append(row)

    leave_out = pd.DataFrame(
        leave_rows
    ).sort_values(
        ["pairs_touching_source", "excluded_source"],
        ascending=[False, True],
    )

    # 4. ASA/AVA subset provenance.
    favorable_mask = data[
        "driver_descriptor"
    ].isin(["ASA", "AVA"])

    favorable = data.loc[
        favorable_mask
    ].copy()

    favorable_baseline_median = float(
        np.median(
            favorable[
                "delta_q_mmol_g"
            ].to_numpy(dtype=float)
        )
    )

    favorable_specs = [
        (
            "ASA_AVA_all",
            pd.Series(True, index=favorable.index),
        ),
        (
            "ASA_AVA_same_source",
            favorable["same_source_pair"],
        ),
        (
            "ASA_AVA_cross_source",
            ~favorable["same_source_pair"],
        ),
        (
            "ASA_AVA_hypothetical_hypothetical",
            favorable["provenance_class"].eq(
                "hypothetical_hypothetical"
            ),
        ),
        (
            "ASA_AVA_experimental_experimental",
            favorable["provenance_class"].eq(
                "experimental_experimental"
            ),
        ),
        (
            "ASA_AVA_mixed_hypothetical_experimental",
            favorable["provenance_class"].eq(
                "mixed_hypothetical_experimental"
            ),
        ),
    ]

    favorable_rows = []

    for name, mask in favorable_specs:
        block = favorable.loc[mask]
        row = summarize(
            block,
            population=name,
        )
        row[
            "fraction_of_ASA_AVA_pairs"
        ] = (
            row["pairs"] / len(favorable)
            if len(favorable)
            else np.nan
        )
        row[
            "median_change_vs_ASA_AVA_full_mmol_g"
        ] = (
            float(row["median_delta_q_mmol_g"])
            - favorable_baseline_median
            if row["pairs"] > 0
            else np.nan
        )
        favorable_rows.append(row)

    favorable_out = pd.DataFrame(
        favorable_rows
    )

    # 5. Leave-one-source-out within ASA/AVA subset.
    favorable_touched_counts = {}
    for source in sorted(KNOWN_SOURCES):
        touched = (
            favorable["source_low"].eq(source)
            | favorable["source_high"].eq(source)
        )
        favorable_touched_counts[source] = int(
            touched.sum()
        )

    favorable_major_sources = [
        source
        for source, count in favorable_touched_counts.items()
        if count >= MAJOR_SOURCE_MIN_TOUCHED_PAIRS
    ]

    favorable_leave_rows = []

    for source in favorable_major_sources:
        keep = ~(
            favorable["source_low"].eq(source)
            | favorable["source_high"].eq(source)
        )
        block = favorable.loc[keep]

        row = summarize(
            block,
            population=f"ASA_AVA_exclude_{source}",
        )
        row["excluded_source"] = source
        row["source_kind"] = source_kind(source)
        row[
            "ASA_AVA_pairs_touching_source"
        ] = favorable_touched_counts[source]
        row["pairs_retained"] = row.pop("pairs")
        row[
            "fraction_of_ASA_AVA_retained"
        ] = (
            row["pairs_retained"] / len(favorable)
            if len(favorable)
            else np.nan
        )
        row[
            "median_change_vs_ASA_AVA_full_mmol_g"
        ] = (
            float(row["median_delta_q_mmol_g"])
            - favorable_baseline_median
        )
        favorable_leave_rows.append(row)

    favorable_leave_out = pd.DataFrame(
        favorable_leave_rows
    ).sort_values(
        [
            "ASA_AVA_pairs_touching_source",
            "excluded_source",
        ],
        ascending=[False, True],
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    atomic_write_parquet(
        data,
        OUTPUT_DIR / "01_pair_provenance.parquet",
    )
    atomic_write_csv(
        source_pair_out,
        OUTPUT_DIR / "02_source_pair_census.csv",
    )
    atomic_write_csv(
        class_out,
        OUTPUT_DIR / "03_provenance_class_summary.csv",
    )
    atomic_write_csv(
        leave_out,
        OUTPUT_DIR / "04_leave_one_source_out.csv",
    )
    atomic_write_csv(
        favorable_out,
        OUTPUT_DIR / "05_asa_ava_provenance_summary.csv",
    )
    atomic_write_csv(
        favorable_leave_out,
        OUTPUT_DIR / "06_asa_ava_leave_one_source_out.csv",
    )

    definition = {
        "definition_version": DEFINITION_VERSION,
        "analysis_status": (
            "final secondary database-provenance robustness"
        ),
        "provenance_source": (
            "DBx- filename/framework identifier prefix as "
            "defined in ARC-MOF Table 1"
        ),
        "experimental_sources": sorted(
            EXPERIMENTAL_SOURCES
        ),
        "hypothetical_sources": sorted(
            HYPOTHETICAL_SOURCES
        ),
        "leave_one_source_rule": (
            "remove every frozen pair for which either member "
            "belongs to the excluded DB source"
        ),
        "major_source_min_touched_pairs": (
            MAJOR_SOURCE_MIN_TOUCHED_PAIRS
        ),
        "asa_ava_focus": (
            "secondary stress test because Step 3.8 showed the "
            "10% pooled primary signal is concentrated in "
            "ASA- and AVA-driven pairs"
        ),
        "raw_outcome_files_read": False,
        "pair_membership_modified": False,
        "pair_orientation_modified": False,
        "geometry_threshold_modified": False,
        "primary_endpoint_modified": False,
        "primary_estimand_modified": False,
    }

    run_manifest = {
        "script": Path(__file__).name,
        "script_version": SCRIPT_VERSION,
        "definition_version": DEFINITION_VERSION,
        "completed_at_utc": utc_now(),
        "completed_successfully": True,
        "source_primary_pairs": int(len(data)),
        "pairs_with_recovered_DB_prefix": int(len(data)),
        "major_sources_tested": major_sources,
        "ASA_AVA_pairs": int(len(favorable)),
        "ASA_AVA_major_sources_tested": (
            favorable_major_sources
        ),
        "raw_outcome_files_read": False,
        "pair_membership_modified": False,
        "pair_orientation_modified": False,
        "geometry_threshold_modified": False,
        "primary_endpoint_modified": False,
        "primary_estimand_modified": False,
    }

    atomic_write_text(
        json.dumps(
            definition,
            indent=2,
        ),
        OUTPUT_DIR / "07_provenance_definition.json",
    )
    atomic_write_text(
        json.dumps(
            run_manifest,
            indent=2,
        ),
        OUTPUT_DIR / "08_run_manifest.json",
    )

    print("PROJECT 17 - STEP 3.10 DATABASE PROVENANCE ROBUSTNESS")
    print(
        "Policy: frozen primary pair effects only; no raw outcomes; "
        "DB source recovered from ARC-MOF DBx- framework prefix"
    )
    print()
    print(f"Frozen pairs: {len(data):,}")
    print(
        f"ASA/AVA-driven pairs: {len(favorable):,}"
    )
    print(
        "Experimental DB labels: "
        + ", ".join(sorted(EXPERIMENTAL_SOURCES))
    )
    print(
        "Hypothetical DB labels: "
        + ", ".join(sorted(HYPOTHETICAL_SOURCES))
    )

    print()
    print("PROVENANCE CLASS SUMMARY")
    print(
        class_out[
            [
                "population",
                "pairs",
                "fraction_of_full_cohort",
                "median_delta_q_mmol_g",
                "positive_effect_fraction",
                "median_change_vs_full_mmol_g",
            ]
        ].to_string(index=False)
    )

    print()
    print("MAJOR SOURCE INCIDENCE")
    for source in major_sources:
        print(
            f"{source:>4s} "
            f"{source_kind(source):>12s} "
            f"pairs_touched={touched_counts[source]:,}"
        )

    print()
    print("LEAVE-ONE-MAJOR-SOURCE-OUT")
    print(
        leave_out[
            [
                "excluded_source",
                "source_kind",
                "pairs_touching_source",
                "pairs_retained",
                "median_delta_q_mmol_g",
                "positive_effect_fraction",
                "median_change_vs_full_mmol_g",
            ]
        ].to_string(index=False)
    )

    print()
    print("ASA/AVA PROVENANCE SUMMARY")
    print(
        favorable_out[
            [
                "population",
                "pairs",
                "fraction_of_ASA_AVA_pairs",
                "median_delta_q_mmol_g",
                "positive_effect_fraction",
                "median_change_vs_ASA_AVA_full_mmol_g",
            ]
        ].to_string(index=False)
    )

    print()
    print("ASA/AVA LEAVE-ONE-MAJOR-SOURCE-OUT")
    if len(favorable_leave_out):
        print(
            favorable_leave_out[
                [
                    "excluded_source",
                    "source_kind",
                    "ASA_AVA_pairs_touching_source",
                    "pairs_retained",
                    "median_delta_q_mmol_g",
                    "positive_effect_fraction",
                    "median_change_vs_ASA_AVA_full_mmol_g",
                ]
            ].to_string(index=False)
        )
    else:
        print("No source touches >=100 ASA/AVA pairs.")

    print()
    print(f"Saved results: {OUTPUT_DIR}")
    print("Stop here and run py .\\test_16.py.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
