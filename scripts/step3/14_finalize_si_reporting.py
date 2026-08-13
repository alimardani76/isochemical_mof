#!/usr/bin/env python3
"""
Project 17 manuscript closure: generate complete SI secondary tables and
reproducibility/source-data map from already-audited result tables.

This script does NOT perform new scientific analysis.
It only reports all rows already present in the frozen Step 3.5 summary tables.

Inputs
------
Step 3 results/05_secondary_outcome_atlas/secondary_adsorption_summary.csv
Step 3 results/05_secondary_outcome_atlas/secondary_process_summary.csv

Outputs
-------
Project17_SI_closure_tables.tex
Step 3 results/10_manuscript_closure/
    closure_reporting_manifest.json
    secondary_adsorption_reporting_inventory.csv
    secondary_process_reporting_inventory.csv

Tables generated
----------------
S23 Complete secondary adsorption summary
S24 Complete secondary process summary
S25 Source-data and code map
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
DEFINITION_VERSION = "manuscript_closure_reporting_v1"

ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIR = (
    ROOT
    / "Step 3 results"
    / "05_secondary_outcome_atlas"
)

ADS_PATH = SOURCE_DIR / "secondary_adsorption_summary.csv"
PROCESS_PATH = SOURCE_DIR / "secondary_process_summary.csv"

OUTPUT_TEX = ROOT / "Project17_SI_closure_tables.tex"

RESULT_DIR = (
    ROOT
    / "Step 3 results"
    / "10_manuscript_closure"
)


ALIASES = {
    "context": [
        "context",
        "application",
        "application_context",
        "source_context",
        "dataset",
        "source_table",
    ],
    "guest": [
        "guest",
        "gas",
        "species",
        "adsorbate",
    ],
    "temperature_K": [
        "temperature_K",
        "temperature",
        "T_K",
        "T/K",
        "T",
    ],
    "pressure_bar": [
        "pressure_bar",
        "pressure",
        "p_bar",
        "p/bar",
        "p",
    ],
    "metric": [
        "metric",
        "outcome_metric",
        "response_metric",
        "quantity",
    ],
    "process": [
        "process",
        "process_name",
        "application",
        "context",
    ],
    "pairs": [
        "complete_pairs",
        "pairs",
        "pair_count",
        "n_pairs",
        "n_complete_pairs",
        "n",
    ],
    "median": [
        "median_effect",
        "median_delta",
        "median_change",
        "median_signed_effect",
        "median_delta_q_mmol_g",
        "median_effect_value",
    ],
    "mean": [
        "mean_effect",
        "mean_delta",
        "mean_change",
        "mean_signed_effect",
        "mean_delta_q_mmol_g",
        "mean_effect_value",
    ],
    "positive": [
        "positive_effect_fraction",
        "positive_fraction",
        "fraction_positive",
        "positive_pair_fraction",
    ],
    "symrel": [
        "median_symmetric_relative_effect",
        "median_symmetric_relative",
        "median_relative_effect",
        "median_sym_relative_effect",
    ],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_text(text: str, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def atomic_write_csv(frame: pd.DataFrame, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    frame.to_csv(tmp, index=False)
    os.replace(tmp, path)


def find_col(frame: pd.DataFrame, key: str, required: bool = True) -> str | None:
    cols = list(frame.columns)

    # Exact first.
    for candidate in ALIASES[key]:
        if candidate in cols:
            return candidate

    # Case-insensitive exact.
    lowered = {str(c).lower(): c for c in cols}
    for candidate in ALIASES[key]:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]

    if required:
        raise ValueError(
            f"Could not resolve required column {key!r}. "
            f"Available columns: {cols}"
        )

    return None


def escape_latex(value: object) -> str:
    if pd.isna(value):
        return "--"

    text = str(value)

    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }

    return "".join(replacements.get(ch, ch) for ch in text)


def fmt_num(value: object, digits: int = 4) -> str:
    if pd.isna(value):
        return "--"

    x = float(value)

    if not np.isfinite(x):
        return "--"

    if x == 0:
        return "0"

    abs_x = abs(x)

    if abs_x >= 1000:
        return f"{x:.3g}"

    if abs_x < 0.0001:
        return f"{x:.3g}"

    return f"{x:.{digits}f}".rstrip("0").rstrip(".")


def canonical_metric(value: object) -> str:
    text = str(value).strip()

    mapping = {
        "mmol/g": r"\si{\milli\mole\per\gram}",
        "v/v": "v/v",
        "wt%": r"wt\%",
        "hoa/kcal/mol": r"HOA (\si{\kilo\calorie\per\mole})",
        "hoa": r"HOA (\si{\kilo\calorie\per\mole})",
        "selectivity": "Selectivity",
        "purity": "Purity",
        "ssp": "SSP",
        "afm": "AFM",
        "mmol/g_uptake": r"Uptake (\si{\milli\mole\per\gram})",
        "mmol/g_working_capacity": r"Working capacity (\si{\milli\mole\per\gram})",
        "v/v_uptake": "Uptake (v/v)",
        "v/v_working_capacity": "Working capacity (v/v)",
        "wt%_uptake": r"Uptake (wt\%)",
        "wt%_working_capacity": r"Working capacity (wt\%)",
    }

    return mapping.get(text, escape_latex(text))


def build_ads_table(frame: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    c_context = find_col(frame, "context")
    c_guest = find_col(frame, "guest")
    c_temp = find_col(frame, "temperature_K")
    c_pressure = find_col(frame, "pressure_bar")
    c_metric = find_col(frame, "metric")
    c_pairs = find_col(frame, "pairs")
    c_median = find_col(frame, "median")
    c_mean = find_col(frame, "mean", required=False)
    c_positive = find_col(frame, "positive")
    c_symrel = find_col(frame, "symrel", required=False)

    out = pd.DataFrame({
        "context": frame[c_context].astype(str),
        "guest": frame[c_guest].astype(str),
        "temperature_K": pd.to_numeric(frame[c_temp], errors="coerce"),
        "pressure_bar": pd.to_numeric(frame[c_pressure], errors="coerce"),
        "metric": frame[c_metric].astype(str),
        "pairs": pd.to_numeric(frame[c_pairs], errors="coerce"),
        "median": pd.to_numeric(frame[c_median], errors="coerce"),
        "positive": pd.to_numeric(frame[c_positive], errors="coerce"),
    })

    out["mean"] = (
        pd.to_numeric(frame[c_mean], errors="coerce")
        if c_mean is not None
        else np.nan
    )

    out["symrel"] = (
        pd.to_numeric(frame[c_symrel], errors="coerce")
        if c_symrel is not None
        else np.nan
    )

    out = out.sort_values(
        ["context", "guest", "temperature_K", "pressure_bar", "metric"]
    ).reset_index(drop=True)

    lines = [
        r"\begin{longtable}{llrrlrrrr}",
        r"\caption{Complete frozen secondary adsorption summary. All rows from the audited "
        r"\texttt{secondary\_adsorption\_summary.csv} are reported; no endpoint is selected "
        r"or omitted on the basis of effect magnitude.}\label{tab:S23}\\",
        r"\toprule",
        r"Context & Guest & $T$ (K) & $p$ (bar) & Metric & Pairs & Median $\Delta$ & "
        r"Positive fraction & Median sym. rel. \\",
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        r"Context & Guest & $T$ (K) & $p$ (bar) & Metric & Pairs & Median $\Delta$ & "
        r"Positive fraction & Median sym. rel. \\",
        r"\midrule",
        r"\endhead",
    ]

    for row in out.itertuples(index=False):
        lines.append(
            " & ".join([
                escape_latex(row.context),
                escape_latex(row.guest)
                    .replace("CH4", r"CH$_4$")
                    .replace("CO2", r"CO$_2$")
                    .replace("N2", r"N$_2$")
                    .replace("H2", r"H$_2$"),
                fmt_num(row.temperature_K, 1),
                fmt_num(row.pressure_bar, 4),
                canonical_metric(row.metric),
                f"{int(row.pairs):,}" if pd.notna(row.pairs) else "--",
                fmt_num(row.median, 5),
                fmt_num(row.positive, 4),
                fmt_num(row.symrel, 5),
            ]) + r" \\"
        )

    lines.extend([
        r"\bottomrule",
        r"\end{longtable}",
        "",
    ])

    return "\n".join(lines), out


def build_process_table(frame: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    c_process = find_col(frame, "process")
    c_metric = find_col(frame, "metric")
    c_pairs = find_col(frame, "pairs")
    c_median = find_col(frame, "median")
    c_mean = find_col(frame, "mean", required=False)
    c_positive = find_col(frame, "positive")
    c_symrel = find_col(frame, "symrel", required=False)

    out = pd.DataFrame({
        "process": frame[c_process].astype(str),
        "metric": frame[c_metric].astype(str),
        "pairs": pd.to_numeric(frame[c_pairs], errors="coerce"),
        "median": pd.to_numeric(frame[c_median], errors="coerce"),
        "positive": pd.to_numeric(frame[c_positive], errors="coerce"),
    })

    out["mean"] = (
        pd.to_numeric(frame[c_mean], errors="coerce")
        if c_mean is not None
        else np.nan
    )

    out["symrel"] = (
        pd.to_numeric(frame[c_symrel], errors="coerce")
        if c_symrel is not None
        else np.nan
    )

    out = out.sort_values(
        ["process", "metric"]
    ).reset_index(drop=True)

    lines = [
        r"\begin{longtable}{llrrrr}",
        r"\caption{Complete frozen secondary process summary. All rows from the audited "
        r"\texttt{secondary\_process\_summary.csv} are reported.}\label{tab:S24}\\",
        r"\toprule",
        r"Process & Metric & Pairs & Median $\Delta$ & Positive fraction & Median sym. rel. \\",
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        r"Process & Metric & Pairs & Median $\Delta$ & Positive fraction & Median sym. rel. \\",
        r"\midrule",
        r"\endhead",
    ]

    for row in out.itertuples(index=False):
        lines.append(
            " & ".join([
                escape_latex(row.process),
                canonical_metric(row.metric),
                f"{int(row.pairs):,}" if pd.notna(row.pairs) else "--",
                fmt_num(row.median, 5),
                fmt_num(row.positive, 4),
                fmt_num(row.symrel, 5),
            ]) + r" \\"
        )

    lines.extend([
        r"\bottomrule",
        r"\end{longtable}",
        "",
    ])

    return "\n".join(lines), out


def build_source_map() -> str:
    rows = [
        (
            "Figure 1",
            "Stages 1.1--1.4; Steps 2.1--2.3 frozen cohort and pair tables",
            "03_make_figure1.py",
        ),
        (
            "Figure 2",
            r"Step 3.4 \texttt{primary\_ch4\_pair\_effects.parquet} and summaries",
            "05_make_figure2.py",
        ),
        (
            "Figure 3",
            r"Step 3.5 secondary adsorption/process summary tables",
            "07_make_figure3_clean_v2.py",
        ),
        (
            "Figure 4",
            r"Step 3.7 response archetype tables",
            "10_make_figure4_v2.py",
        ),
        (
            "Figures S1--S3",
            r"Steps 3.5--3.6 secondary and concordance tables",
            "11_make_si_figures.py",
        ),
        (
            "Tables S17--S18",
            r"Step 3.8 dominant-context robustness tables",
            "12_analyze_robustness_transferability.py",
        ),
        (
            "Tables S19--S21",
            r"Step 3.10 database-provenance robustness tables",
            "13_analyze_database_provenance.py",
        ),
        (
            "Tables S23--S24",
            r"Audited full Step 3.5 summary tables",
            "14_finalize_si_reporting.py",
        ),
    ]

    lines = [
        r"\begin{longtable}{lll}",
        r"\caption{Source-data and code map for manuscript figures and late-stage "
        r"Supporting Information tables.}\label{tab:S25}\\",
        r"\toprule",
        r"Output & Frozen source data & Production script \\",
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        r"Output & Frozen source data & Production script \\",
        r"\midrule",
        r"\endhead",
    ]

    for output, data, script in rows:
        lines.append(
            f"{escape_latex(output)} & {data} & "
            + r"\texttt{" + escape_latex(script) + r"} \\"
        )

    lines.extend([
        r"\bottomrule",
        r"\end{longtable}",
        "",
    ])

    return "\n".join(lines)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    for path in (ADS_PATH, PROCESS_PATH):
        if not path.is_file():
            raise FileNotFoundError(path)

    ads = pd.read_csv(ADS_PATH)
    process = pd.read_csv(PROCESS_PATH)

    ads_tex, ads_inventory = build_ads_table(ads)
    process_tex, process_inventory = build_process_table(process)
    source_map_tex = build_source_map()

    header = r"""% Auto-generated by Step 3 production/14_finalize_si_reporting.py.
% This file reports already-audited results only. Do not edit values manually.

\section{Complete secondary-result reporting}

Tables~S23--S24 expose the complete frozen Step 3.5 summary outputs. The compact
main-text and earlier SI tables emphasize the principal \si{\milli\mole\per\gram}
and process findings, whereas these tables report every audited secondary metric
without outcome-based selection.

"""

    complete_tex = (
        header
        + ads_tex
        + "\n"
        + process_tex
        + "\n"
        + r"""\section{Reproducibility map}

The analysis used ARC--MOF release v7 (Zenodo record 16802743). The local raw-data
inventory comprised the charged CIF archive together with the ARC--MOF topology,
dimensionality, geometry, RAC/cluster, adsorption, and process tables used by the
staged workflow. Each analytical stage wrote deterministic tables and a manifest;
each stage was followed by an independent reconstruction audit.

"""
        + source_map_tex
    )

    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    atomic_write_text(complete_tex, OUTPUT_TEX)
    atomic_write_csv(
        ads_inventory,
        RESULT_DIR / "secondary_adsorption_reporting_inventory.csv",
    )
    atomic_write_csv(
        process_inventory,
        RESULT_DIR / "secondary_process_reporting_inventory.csv",
    )

    manifest = {
        "script": Path(__file__).name,
        "script_version": SCRIPT_VERSION,
        "definition_version": DEFINITION_VERSION,
        "completed_at_utc": utc_now(),
        "completed_successfully": True,
        "new_scientific_analysis_performed": False,
        "adsorption_source": str(ADS_PATH.relative_to(ROOT)),
        "process_source": str(PROCESS_PATH.relative_to(ROOT)),
        "adsorption_source_rows": int(len(ads)),
        "adsorption_reported_rows": int(len(ads_inventory)),
        "process_source_rows": int(len(process)),
        "process_reported_rows": int(len(process_inventory)),
        "adsorption_metrics": sorted(ads_inventory["metric"].dropna().unique().tolist()),
        "process_metrics": sorted(process_inventory["metric"].dropna().unique().tolist()),
        "output_tex": str(OUTPUT_TEX.relative_to(ROOT)),
        "arc_mof_release": "v7",
        "arc_mof_zenodo_record": "16802743",
    }

    atomic_write_text(
        json.dumps(manifest, indent=2),
        RESULT_DIR / "closure_reporting_manifest.json",
    )

    print("PROJECT 17 - MANUSCRIPT CLOSURE REPORTING")
    print("Policy: reporting only; no new scientific analysis")
    print()
    print(f"Adsorption summary source rows: {len(ads):,}")
    print(f"Adsorption rows reported:       {len(ads_inventory):,}")
    print(
        "Adsorption metrics: "
        + ", ".join(sorted(ads_inventory["metric"].dropna().unique().tolist()))
    )
    print()
    print(f"Process summary source rows: {len(process):,}")
    print(f"Process rows reported:       {len(process_inventory):,}")
    print(
        "Process metrics: "
        + ", ".join(sorted(process_inventory["metric"].dropna().unique().tolist()))
    )
    print()
    print(f"Generated SI include: {OUTPUT_TEX}")
    print(f"Saved audit inventory: {RESULT_DIR}")
    print("Run py .\\test_18.py.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
