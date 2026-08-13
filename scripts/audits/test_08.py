#!/usr/bin/env python3
"""Audit Project 17 Step 3.2 metadata-only outcome/pair coverage census."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"

PAIR_PATH = (
    ROOT
    / "Step 2 results"
    / "03_geometry_pairs"
    / "primary_geometry_pairs.parquet"
)

RESULTS_DIR = (
    ROOT
    / "Step 3 results"
    / "02_all_outcome_condition_coverage"
)

DEFINITION_VERSION = "all_outcome_condition_pair_coverage_v1"

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

EXPECTED_FILES = [
    "outcome_source_metadata_census.csv",
    "outcome_condition_pair_coverage.csv",
    "outcome_endpoint_support_ranking.csv",
    "outcome_condition_coverage_definition.json",
    "run_manifest.json",
]

SUFFIX_PATTERN = re.compile(r"(?i)(?:\.cif|_repeat|_sqe)$")


class Audit:
    def __init__(self):
        self.failures = []

    def check(self, condition: Any, message: str) -> None:
        try:
            ok = bool(condition)
        except Exception:
            ok = False

        print(("PASS  " if ok else "FAIL  ") + message)
        if not ok:
            self.failures.append(message)


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


def pair_coverage(
    ids: set[str],
    pair_a: pd.Series,
    pair_b: pd.Series,
):
    a = pair_a.isin(ids)
    b = pair_b.isin(ids)

    complete = a & b
    exactly_one = a ^ b
    neither = ~(a | b)

    return {
        "complete_pairs": int(complete.sum()),
        "exactly_one_member_pairs": int(exactly_one.sum()),
        "neither_member_pairs": int(neither.sum()),
        "complete_pair_fraction": float(complete.mean()),
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    audit = Audit()

    print("PROJECT 17 - STEP 3.2 OUTCOME CONDITION COVERAGE AUDIT")

    audit.check(RESULTS_DIR.is_dir(), "Step 3.2 result folder exists")
    if not RESULTS_DIR.is_dir():
        return 1

    missing = [
        name
        for name in EXPECTED_FILES
        if not (RESULTS_DIR / name).is_file()
    ]
    audit.check(not missing, "all expected Step 3.2 files exist")
    if missing:
        print("Missing:", missing)
        return 1

    audit.check(PAIR_PATH.is_file(), "frozen primary pair source exists")

    for filename in [*ADSORPTION_FILES, PROCESS_FILE]:
        audit.check(
            (RAW / filename).is_file(),
            f"raw source exists: {filename}",
        )

    if audit.failures:
        return 1

    manifest = json.loads(
        (RESULTS_DIR / "run_manifest.json").read_text(encoding="utf-8")
    )
    definition = json.loads(
        (
            RESULTS_DIR
            / "outcome_condition_coverage_definition.json"
        ).read_text(encoding="utf-8")
    )

    census = pd.read_csv(
        RESULTS_DIR / "outcome_condition_pair_coverage.csv"
    )
    ranking = pd.read_csv(
        RESULTS_DIR / "outcome_endpoint_support_ranking.csv"
    )
    source_census = pd.read_csv(
        RESULTS_DIR / "outcome_source_metadata_census.csv"
    )

    pairs = pd.read_parquet(
        PAIR_PATH,
        columns=["architecture_group_id", "mof_id_a", "mof_id_b"],
    )
    pair_a = pairs["mof_id_a"].astype("string")
    pair_b = pairs["mof_id_b"].astype("string")
    frozen_ids = set(pair_a.astype(str)) | set(pair_b.astype(str))

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
        manifest.get("metadata_only") is True,
        "manifest records metadata-only access",
    )
    audit.check(
        manifest.get("outcome_values_read") is False,
        "no outcome values were read",
    )
    audit.check(
        manifest.get("endpoint_selected") is False,
        "no endpoint was selected",
    )
    audit.check(
        manifest.get("pair_membership_modified") is False,
        "frozen pair membership was not modified",
    )
    audit.check(
        int(manifest.get("frozen_primary_pairs")) == len(pairs),
        "manifest frozen-pair count matches",
    )
    audit.check(
        int(manifest.get("frozen_pair_members")) == len(frozen_ids),
        "manifest frozen-member count matches",
    )

    print("\nDEFINITION")
    audit.check(
        definition.get("definition_version") == DEFINITION_VERSION,
        "definition version is exact",
    )
    audit.check(
        definition.get("columns_read", {}).get("adsorption")
        == ["filename", "T/K", "p/bar"],
        "adsorption access is restricted to filename/T/p",
    )
    audit.check(
        definition.get("columns_read", {}).get("process")
        == ["filename", "process"],
        "process access is restricted to filename/process",
    )
    audit.check(
        definition.get("outcome_values_read") is False,
        "definition preserves outcome blindness",
    )
    audit.check(
        definition.get("endpoint_selected") is False,
        "definition preserves endpoint blindness",
    )

    print("\nSOURCE CENSUS")
    expected_sources = set([*ADSORPTION_FILES, PROCESS_FILE])
    audit.check(
        set(source_census["source"].astype(str)) == expected_sources,
        "source census contains exactly all ten outcome tables",
    )
    audit.check(
        len(source_census) == len(expected_sources),
        "source census has exactly one row per source",
    )

    print("\nFULL RECOMPUTATION")
    expected_rows = []

    for filename in ADSORPTION_FILES:
        frame = pd.read_csv(
            RAW / filename,
            usecols=["filename", "T/K", "p/bar"],
            low_memory=False,
        )
        frame["mof_id"] = canonicalize_ids(frame["filename"])
        frame["T/K"] = pd.to_numeric(frame["T/K"], errors="raise")
        frame["p/bar"] = pd.to_numeric(frame["p/bar"], errors="raise")

        for (temperature, pressure), group in frame.groupby(
            ["T/K", "p/bar"],
            sort=True,
            dropna=False,
        ):
            ids = set(group["mof_id"].astype(str))
            expected_rows.append(
                {
                    "source": filename,
                    "source_type": "adsorption",
                    "condition_label": (
                        f"T={float(temperature):g} K; "
                        f"p={float(pressure):g} bar"
                    ),
                    "temperature_K": float(temperature),
                    "pressure_bar": float(pressure),
                    "process": None,
                    "rows": int(len(group)),
                    "unique_source_ids": int(group["mof_id"].nunique()),
                    "frozen_member_ids_present": int(
                        len(ids & frozen_ids)
                    ),
                    **pair_coverage(ids, pair_a, pair_b),
                }
            )

    process = pd.read_csv(
        RAW / PROCESS_FILE,
        usecols=["filename", "process"],
        low_memory=False,
    )
    process["mof_id"] = canonicalize_ids(process["filename"])
    process["process"] = process["process"].astype("string").str.strip()

    for process_name, group in process.groupby(
        "process",
        sort=True,
        dropna=False,
    ):
        ids = set(group["mof_id"].astype(str))
        expected_rows.append(
            {
                "source": PROCESS_FILE,
                "source_type": "process",
                "condition_label": str(process_name),
                "temperature_K": None,
                "pressure_bar": None,
                "process": str(process_name),
                "rows": int(len(group)),
                "unique_source_ids": int(group["mof_id"].nunique()),
                "frozen_member_ids_present": int(
                    len(ids & frozen_ids)
                ),
                **pair_coverage(ids, pair_a, pair_b),
            }
        )

    expected = pd.DataFrame(expected_rows)

    key = ["source", "condition_label"]
    observed = census.copy()

    expected = expected.sort_values(key).reset_index(drop=True)
    observed = observed.sort_values(key).reset_index(drop=True)

    audit.check(
        list(expected[key].itertuples(index=False, name=None))
        == list(observed[key].astype(str).itertuples(index=False, name=None)),
        "condition/process keys match exactly",
    )

    numeric_cols = [
        "rows",
        "unique_source_ids",
        "frozen_member_ids_present",
        "complete_pairs",
        "exactly_one_member_pairs",
        "neither_member_pairs",
    ]

    numeric_exact = True
    for column in numeric_cols:
        if not (
            pd.to_numeric(expected[column], errors="raise")
            .astype(int)
            .eq(
                pd.to_numeric(observed[column], errors="raise")
                .astype(int)
            )
            .all()
        ):
            numeric_exact = False
            break

    audit.check(
        numeric_exact,
        "all condition/process support counts are exact",
    )

    fraction_exact = (
        pd.to_numeric(
            expected["complete_pair_fraction"],
            errors="raise",
        )
        .round(14)
        .eq(
            pd.to_numeric(
                observed["complete_pair_fraction"],
                errors="raise",
            ).round(14)
        )
        .all()
    )

    audit.check(
        fraction_exact,
        "all complete-pair coverage fractions are exact",
    )

    print("\nRANKING")
    ranking_keys = list(
        ranking[["source", "condition_label"]]
        .astype(str)
        .itertuples(index=False, name=None)
    )
    census_keys = list(
        census.sort_values(
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
        )[["source", "condition_label"]]
        .astype(str)
        .itertuples(index=False, name=None)
    )

    audit.check(
        ranking_keys == census_keys,
        "endpoint support ranking order is exact",
    )

    print("\nTOP SUPPORT")
    top = census.sort_values(
        ["complete_pairs", "source", "condition_label"],
        ascending=[False, True, True],
    ).head(15)

    print(
        top[
            [
                "source",
                "condition_label",
                "complete_pairs",
                "complete_pair_fraction",
            ]
        ].to_string(index=False)
    )

    print("\nOVERALL RESULT")
    if audit.failures:
        print(
            f"FAIL - {len(audit.failures)} hard check(s) failed. "
            "Do not select an endpoint or read outcome values."
        )
        return 1

    print(
        "PASS - metadata-only outcome condition / frozen-pair coverage "
        "census is internally consistent."
    )
    print(
        "Next: choose and freeze the primary Figure 2 endpoint using "
        "scientific relevance + this coverage table, before reading values."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
