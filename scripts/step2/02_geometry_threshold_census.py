#!/usr/bin/env python3
"""
Project 17 Step 2.2: census of meaningful geometry-contrast thresholds.

Input:
    Step 2 results/01_geometry_variation/geometry_variation_groups.parquet

Purpose:
    Count how many validated same-chemistry + same-architecture families retain
    at least one pore-geometry descriptor with a relative within-family span above
    simple candidate thresholds: 5%, 10%, 20%, 30%.

No framework pairs are constructed.
No adsorption/process outcomes are read.
No threshold is declared "final" by this script.

Relative span comes directly from Step 2.1:
    (family maximum - family minimum) / max(abs(minimum), abs(maximum))
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


SCRIPT_VERSION = "1.0.0"
DEFINITION_VERSION = "geometry_threshold_census_v1"

DEFAULT_ROOT = Path(__file__).resolve().parents[1]

STEP21_DIR_REL = Path("Step 2 results") / "01_geometry_variation"
OUTPUT_DIR_REL = Path("Step 2 results") / "02_geometry_threshold_census"

PORE_DESCRIPTORS = [
    "ASA",
    "AVA",
    "AVAf",
    "POAVA",
    "POAVAf",
    "Di",
    "Df",
    "Dif",
]

THRESHOLDS = [0.05, 0.10, 0.20, 0.30]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def threshold_label(value: float) -> str:
    return f"{int(round(value * 100)):02d}pct"


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=DEFAULT_ROOT,
    )
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args()
    root = args.project_root.resolve()

    step21_dir = root / STEP21_DIR_REL
    input_path = step21_dir / "geometry_variation_groups.parquet"
    step21_manifest_path = step21_dir / "run_manifest.json"
    output_dir = root / OUTPUT_DIR_REL

    for path in (input_path, step21_manifest_path):
        if not path.is_file():
            raise FileNotFoundError(path)

    step21_manifest = json.loads(
        step21_manifest_path.read_text(encoding="utf-8")
    )
    if step21_manifest.get("completed_successfully") is not True:
        raise RuntimeError("Step 2.1 is not marked complete")
    if step21_manifest.get("outcome_values_read") is not False:
        raise RuntimeError("Step 2.1 provenance does not confirm outcome blindness")
    if step21_manifest.get("pairs_constructed") is not False:
        raise RuntimeError("Step 2.1 provenance does not confirm pair blindness")

    groups = pd.read_parquet(input_path)

    required = {
        "architecture_group_id",
        "source_chemistry_group_id",
        "framework_count",
        *[f"{column}_fractional_span" for column in PORE_DESCRIPTORS],
    }
    missing = required - set(groups.columns)
    if missing:
        raise ValueError(
            f"Step 2.1 group table is missing columns: {sorted(missing)}"
        )

    groups["architecture_group_id"] = groups[
        "architecture_group_id"
    ].astype("string")

    for descriptor in PORE_DESCRIPTORS:
        groups[f"{descriptor}_fractional_span"] = pd.to_numeric(
            groups[f"{descriptor}_fractional_span"],
            errors="raise",
        )

    print("Project 17 Step 2.2: geometry threshold census")
    print(
        "Policy: pore-geometry descriptors only; candidate thresholds 5/10/20/30%; "
        "no final threshold, no pairs, no outcomes"
    )
    print(f"Architecture groups entering census: {len(groups):,}")

    started_at = utc_now()

    family_output = groups[
        [
            "architecture_group_id",
            "source_chemistry_group_id",
            "framework_count",
            *[f"{d}_fractional_span" for d in PORE_DESCRIPTORS],
        ]
    ].copy()

    max_span_columns = [
        f"{descriptor}_fractional_span"
        for descriptor in PORE_DESCRIPTORS
    ]
    family_output["max_pore_fractional_span"] = (
        family_output[max_span_columns].max(axis=1)
    )

    threshold_rows: list[dict[str, Any]] = []
    descriptor_rows: list[dict[str, Any]] = []

    for threshold in THRESHOLDS:
        label = threshold_label(threshold)

        per_descriptor_flags = []
        for descriptor in PORE_DESCRIPTORS:
            flag_col = f"{descriptor}_ge_{label}"
            flag = (
                family_output[f"{descriptor}_fractional_span"]
                >= threshold
            )
            family_output[flag_col] = flag
            per_descriptor_flags.append(flag_col)

            descriptor_rows.append(
                {
                    "threshold": threshold,
                    "threshold_percent": int(round(threshold * 100)),
                    "descriptor": descriptor,
                    "families_meeting_threshold": int(flag.sum()),
                    "fraction_of_all_families": float(flag.mean()),
                    "frameworks_in_families_meeting_threshold": int(
                        family_output.loc[flag, "framework_count"].sum()
                    ),
                }
            )

        any_col = f"any_pore_descriptor_ge_{label}"
        count_col = f"n_pore_descriptors_ge_{label}"

        family_output[count_col] = (
            family_output[per_descriptor_flags]
            .astype(int)
            .sum(axis=1)
        )
        family_output[any_col] = (
            family_output[count_col] >= 1
        )

        eligible = family_output[any_col]

        threshold_rows.append(
            {
                "threshold": threshold,
                "threshold_percent": int(round(threshold * 100)),
                "eligible_families": int(eligible.sum()),
                "fraction_of_all_families": float(eligible.mean()),
                "eligible_frameworks": int(
                    family_output.loc[
                        eligible,
                        "framework_count",
                    ].sum()
                ),
                "median_family_size_among_eligible": float(
                    family_output.loc[
                        eligible,
                        "framework_count",
                    ].median()
                )
                if eligible.any()
                else 0.0,
                "median_number_of_descriptors_meeting_threshold": float(
                    family_output.loc[
                        eligible,
                        count_col,
                    ].median()
                )
                if eligible.any()
                else 0.0,
            }
        )

    threshold_census = pd.DataFrame(threshold_rows)
    descriptor_census = pd.DataFrame(descriptor_rows)

    # Helpful distribution of the family's strongest pore-geometry difference.
    quantiles = [0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
    max_span_quantiles = pd.DataFrame(
        [
            {
                "quantile": q,
                "max_pore_fractional_span": float(
                    family_output[
                        "max_pore_fractional_span"
                    ].quantile(q)
                ),
            }
            for q in quantiles
        ]
    )

    summary = pd.DataFrame(
        [
            ("architecture_groups_entering_census", len(family_output)),
            (
                "frameworks_in_architecture_groups",
                int(family_output["framework_count"].sum()),
            ),
            (
                "median_max_pore_fractional_span",
                float(
                    family_output[
                        "max_pore_fractional_span"
                    ].median()
                ),
            ),
            (
                "p90_max_pore_fractional_span",
                float(
                    family_output[
                        "max_pore_fractional_span"
                    ].quantile(0.90)
                ),
            ),
        ],
        columns=["metric", "value"],
    )

    definition = {
        "definition_version": DEFINITION_VERSION,
        "input": (
            "Step 2.1 validated architecture-group geometry variation table"
        ),
        "pore_descriptors": PORE_DESCRIPTORS,
        "candidate_thresholds": THRESHOLDS,
        "eligibility_rule": (
            "family meets a candidate threshold when at least one pore-geometry "
            "descriptor has within-family fractional span >= threshold"
        ),
        "fractional_span_definition": (
            "(family maximum - family minimum) / "
            "max(abs(minimum), abs(maximum))"
        ),
        "unit_cell_volume_used": False,
        "density_used": False,
        "final_threshold_selected": False,
        "pairs_constructed": False,
        "outcome_values_read": False,
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    atomic_write_parquet(
        family_output.sort_values(
            [
                "max_pore_fractional_span",
                "architecture_group_id",
            ],
            ascending=[False, True],
        ).reset_index(drop=True),
        output_dir / "geometry_threshold_families.parquet",
    )
    atomic_write_csv(
        threshold_census,
        output_dir / "geometry_threshold_census.csv",
    )
    atomic_write_csv(
        descriptor_census,
        output_dir / "geometry_threshold_descriptor_census.csv",
    )
    atomic_write_csv(
        max_span_quantiles,
        output_dir / "max_pore_span_quantiles.csv",
    )
    atomic_write_csv(
        summary,
        output_dir / "geometry_threshold_summary.csv",
    )
    atomic_write_text(
        json.dumps(definition, indent=2),
        output_dir / "geometry_threshold_definition.json",
    )

    manifest = {
        "script": Path(__file__).name,
        "script_version": SCRIPT_VERSION,
        "definition_version": DEFINITION_VERSION,
        "started_at_utc": started_at,
        "completed_at_utc": utc_now(),
        "step21_groups_sha256": sha256_file(input_path),
        "source_step21_definition_version": step21_manifest.get(
            "definition_version"
        ),
        "pore_descriptors": PORE_DESCRIPTORS,
        "candidate_thresholds": THRESHOLDS,
        "final_threshold_selected": False,
        "pairs_constructed": False,
        "outcome_values_read": False,
        "raw_directory_modified": False,
        "completed_successfully": True,
        "output_directory": str(OUTPUT_DIR_REL),
    }

    atomic_write_text(
        json.dumps(manifest, indent=2),
        output_dir / "run_manifest.json",
    )

    print()
    print("Threshold census:")
    print(
        threshold_census[
            [
                "threshold_percent",
                "eligible_families",
                "fraction_of_all_families",
                "eligible_frameworks",
                "median_number_of_descriptors_meeting_threshold",
            ]
        ].to_string(index=False)
    )

    print()
    print("Strongest pore-span quantiles:")
    print(max_span_quantiles.to_string(index=False))

    print()
    print("Descriptor-specific counts:")
    for threshold in THRESHOLDS:
        block = descriptor_census.loc[
            descriptor_census["threshold"].eq(threshold)
        ].sort_values(
            "families_meeting_threshold",
            ascending=False,
        )
        print()
        print(f"{int(threshold * 100)}% threshold")
        print(
            block[
                [
                    "descriptor",
                    "families_meeting_threshold",
                    "fraction_of_all_families",
                ]
            ].to_string(index=False)
        )

    print()
    print(f"Saved results: {output_dir}")
    print(
        "Stop here. Use this census to choose one simple geometry-contrast threshold "
        "before constructing any pairs."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
