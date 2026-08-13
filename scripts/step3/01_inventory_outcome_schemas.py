#!/usr/bin/env python3
"""
Project 17 Step 3.1: outcome-table schema inventory.

Purpose
-------
Inspect only CSV headers for the available adsorption/process outcome tables.
No outcome values are read.
No joins to the frozen geometry pairs are performed.
No endpoint is selected by this script.

This step exists only so the primary endpoint can be chosen and frozen before
opening outcome values.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_ROOT = Path(__file__).resolve().parents[1]

RAW_REL = Path("raw")
OUTPUT_REL = Path("Step 3 results") / "01_outcome_schema_inventory"

OUTCOME_FILES = [
    "methane.csv",
    "landfill-CH4.csv",
    "landfill-CO2.csv",
    "methane_purification-CH4.csv",
    "methane_purification-CO2.csv",
    "post_comb_vsa-CO2.csv",
    "post_comb_vsa-N2.csv",
    "pre_comb_4040-CO2.csv",
    "pre_comb_4040-H2.csv",
    "overall_process.csv",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_text(text: str, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def read_header(path: Path) -> list[str]:
    # utf-8-sig tolerates an optional BOM.
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            return next(reader)
        except StopIteration:
            return []


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    root = DEFAULT_ROOT.resolve()
    raw_dir = root / RAW_REL
    output_dir = root / OUTPUT_REL

    if not raw_dir.is_dir():
        raise FileNotFoundError(raw_dir)

    records = []

    print("PROJECT 17 - STEP 3.1 OUTCOME SCHEMA INVENTORY")
    print(
        "Policy: CSV headers only; no adsorption/process values, "
        "no pair joins, no endpoint selection"
    )
    print()

    for filename in OUTCOME_FILES:
        path = raw_dir / filename

        if not path.is_file():
            records.append(
                {
                    "file": filename,
                    "exists": False,
                    "columns": [],
                }
            )
            print(f"{filename}")
            print("  MISSING")
            print()
            continue

        columns = read_header(path)

        records.append(
            {
                "file": filename,
                "exists": True,
                "columns": columns,
            }
        )

        print(filename)
        if not columns:
            print("  [empty header]")
        else:
            for i, column in enumerate(columns, start=1):
                print(f"  {i:>2}. {column}")
        print()

    output_dir.mkdir(parents=True, exist_ok=True)

    inventory = {
        "created_at_utc": utc_now(),
        "policy": {
            "headers_only": True,
            "outcome_values_read": False,
            "pair_ids_read": False,
            "pair_join_performed": False,
            "endpoint_selected": False,
        },
        "files": records,
    }

    atomic_write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False),
        output_dir / "outcome_schema_inventory.json",
    )

    missing = [r["file"] for r in records if not r["exists"]]

    print("SUMMARY")
    print(f"  Expected outcome tables: {len(OUTCOME_FILES)}")
    print(f"  Present: {len(OUTCOME_FILES) - len(missing)}")
    print(f"  Missing: {len(missing)}")
    if missing:
        for filename in missing:
            print(f"    - {filename}")

    print()
    print(f"Saved: {output_dir / 'outcome_schema_inventory.json'}")
    print(
        "Stop here. Use the printed column names to freeze the primary outcome "
        "before any outcome values are read."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
