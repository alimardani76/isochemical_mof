#!/usr/bin/env python3
"""Regenerate the Project 17 publication-figure redesign candidates.

The runner performs the numerical preflight first and stops immediately if any
frozen invariant fails. It then executes the requested figure scripts and writes
vector/raster outputs plus per-figure manifests under ``outputs/``.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

SCRIPTS = [
    "R01_figure1_conservative.py",
    "R01_figure1_concept.py",
    "R02_figure2_conservative.py",
    "R02_figure2_concept.py",
    "R03_figure3_conservative.py",
    "R03_figure3_concept.py",
    "R04_figure4_conservative.py",
    "R04_figure4_concept.py",
    "RS1_figureS1.py",
    "RS2_figureS2.py",
    "RS3_figureS3.py",
    "RS4_figureS4.py",
    "RS5_figureS5.py",
    "RS6_figureS6.py",
]


def main() -> int:
    here = Path(__file__).resolve().parent
    repo_root = here.parents[1]

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-root",
        type=Path,
        default=repo_root,
        help="Repository root containing results/ and submission_upgrade/.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=here / "outputs",
        help="Build directory for regenerated figures.",
    )
    parser.add_argument(
        "--only",
        nargs="*",
        choices=SCRIPTS,
        help="Optional subset of redesign scripts to run.",
    )
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    audit = output_dir / "FIGURE_VALUE_AUDIT.json"
    subprocess.run(
        [
            sys.executable,
            str(here / "validate_redesign_values.py"),
            "--project-root",
            str(project_root),
            "--output",
            str(audit),
        ],
        check=True,
    )

    records: list[dict[str, object]] = []
    for script_name in args.only or SCRIPTS:
        script = here / script_name
        destination = output_dir / script.stem
        destination.mkdir(parents=True, exist_ok=True)

        print(f"RUN {script_name}")
        proc = subprocess.run(
            [
                sys.executable,
                str(script),
                "--project-root",
                str(project_root),
                "--output-dir",
                str(destination),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        (destination / "run.log").write_text(proc.stdout or "", encoding="utf-8")
        records.append(
            {
                "script": script_name,
                "returncode": proc.returncode,
                "output_dir": str(destination),
            }
        )
        if proc.stdout:
            print(proc.stdout[-1200:])
        if proc.returncode:
            raise RuntimeError(f"{script_name} failed; inspect {destination / 'run.log'}")

    (output_dir / "RUN_SUMMARY.json").write_text(
        json.dumps(records, indent=2), encoding="utf-8"
    )
    print(f"PASS: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
