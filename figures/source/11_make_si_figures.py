#!/usr/bin/env python3
"""
Project 17 Supporting Information figures

Generates:
    Figure_S1.pdf / .png
        Secondary N2 and H2 pressure responses.

    Figure_S2.pdf / .png
        AFM versus SSP process trade-off.

    Figure_S3.pdf / .png
        Cross-condition Spearman correlation and sign-agreement matrices.

Reads ONLY already-audited Step 3.5 and Step 3.6 result tables.
No raw adsorption/process files are read.

Visual rules:
- Arial bold through figure_style.py
- no panel titles
- clean restrained palette
- uppercase panel labels where multi-panel
- vector PDF + 600 dpi PNG
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

from figure_style import (
    COLORS,
    apply_project17_style,
    save_figure,
    style_axis,
)


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

STEP35 = (
    PROJECT_ROOT
    / "Step 3 results"
    / "05_secondary_outcome_atlas"
)

STEP36 = (
    PROJECT_ROOT
    / "Step 3 results"
    / "06_cross_condition_consistency"
)

FIGURE_DIR = PROJECT_ROOT / "figures"

ADS_PATH = STEP35 / "secondary_adsorption_mmolg_summary.csv"
PROCESS_PATH = STEP35 / "secondary_process_summary.csv"

SPEARMAN_PATH = STEP36 / "mmolg_endpoint_spearman.csv"
AGREEMENT_PATH = STEP36 / "mmolg_endpoint_sign_agreement.csv"
META_PATH = STEP36 / "mmolg_endpoint_metadata.csv"

AXIS_LABEL_SIZE = 9.8
PANEL_LABEL_SIZE = 18.0


def require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)


def add_panel_label(
    ax,
    label: str,
    *,
    x: float = -0.10,
    y: float = 1.05,
) -> None:
    ax.text(
        x,
        y,
        label,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=PANEL_LABEL_SIZE,
        fontweight="bold",
        fontfamily="Arial",
        color="black",
        clip_on=False,
    )


def set_axis_titles(ax, *, xlabel=None, ylabel=None) -> None:
    if xlabel is not None:
        ax.set_xlabel(
            xlabel,
            fontsize=AXIS_LABEL_SIZE,
            fontweight="bold",
            fontfamily="Arial",
            color="black",
        )

    if ylabel is not None:
        ax.set_ylabel(
            ylabel,
            fontsize=AXIS_LABEL_SIZE,
            fontweight="bold",
            fontfamily="Arial",
            color="black",
        )


def figure_s1(ads: pd.DataFrame) -> None:
    """Secondary N2 and H2 pressure response."""
    data = ads.copy()

    for col in (
        "pressure_bar",
        "median_symmetric_relative_effect",
        "positive_effect_fraction",
    ):
        data[col] = pd.to_numeric(
            data[col],
            errors="coerce",
        )

    data["relative_pct"] = (
        100.0 * data["median_symmetric_relative_effect"]
    )

    fig, ax = plt.subplots(
        figsize=(4.8, 3.5),
        constrained_layout=False,
    )

    series = [
        (
            "N2",
            "post-combustion-vsa",
            COLORS["secondary"],
            r"N$_2$",
        ),
        (
            "H2",
            "pre-combustion-40-40",
            COLORS["validated"],
            r"H$_2$",
        ),
    ]

    for guest, context, color, label in series:
        block = data.loc[
            data["guest"].eq(guest)
            & data["context"].eq(context)
        ].sort_values("pressure_bar")

        x = block["pressure_bar"].to_numpy(dtype=float)
        y = block["relative_pct"].to_numpy(dtype=float)

        ax.plot(
            x,
            y,
            marker="o",
            markersize=6.0,
            lw=1.8,
            color=color,
            label=label,
        )

    ax.axhline(
        0,
        color="black",
        lw=0.9,
        ls="--",
    )

    ax.set_xscale("log")

    set_axis_titles(
        ax,
        xlabel="Pressure (bar)",
        ylabel="Median relative uptake effect (%)",
    )

    ax.legend(
        loc="upper left",
        frameon=False,
        prop={
            "family": "Arial",
            "weight": "bold",
            "size": 7.5,
        },
        handlelength=1.5,
        handletextpad=0.45,
        borderaxespad=0.25,
    )

    style_axis(ax)

    FIGURE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    save_figure(
        fig,
        pdf_path=FIGURE_DIR / "Figure_S1.pdf",
        png_path=FIGURE_DIR / "Figure_S1.png",
        dpi=600,
    )
    plt.close(fig)


def figure_s2(process: pd.DataFrame) -> None:
    """AFM versus SSP process trade-off on a symmetric relative scale."""
    data = process.copy()

    for col in (
        "median_symmetric_relative_effect",
        "positive_effect_fraction",
    ):
        data[col] = pd.to_numeric(
            data[col],
            errors="coerce",
        )

    afm = data.loc[
        data["metric"].eq("afm"),
        [
            "process",
            "median_symmetric_relative_effect",
        ],
    ].rename(
        columns={
            "median_symmetric_relative_effect": "afm_rel"
        }
    )

    ssp = data.loc[
        data["metric"].eq("ssp"),
        [
            "process",
            "median_symmetric_relative_effect",
        ],
    ].rename(
        columns={
            "median_symmetric_relative_effect": "ssp_rel"
        }
    )

    merged = afm.merge(
        ssp,
        on="process",
        how="inner",
    ).dropna()

    display = {
        "landfill-gas-vpsa": "Landfill gas",
        "natural-gas-purification": "Natural-gas purification",
        "post-combustion-vsa": "Post-combustion",
        "pre-combustion-40-40": "Pre-combustion",
    }

    colors = {
        "landfill-gas-vpsa": COLORS["validated"],
        "natural-gas-purification": COLORS["accent"],
        "post-combustion-vsa": COLORS["sensitivity"],
        "pre-combustion-40-40": COLORS["warning"],
    }

    fig, ax = plt.subplots(
        figsize=(4.8, 3.7),
        constrained_layout=False,
    )

    for row in merged.itertuples(index=False):
        x = 100.0 * float(row.ssp_rel)
        y = 100.0 * float(row.afm_rel)
        process_name = str(row.process)

        ax.scatter(
            x,
            y,
            s=58,
            color=colors[process_name],
            edgecolors="black",
            linewidths=0.45,
            zorder=3,
        )

        ax.annotate(
            display[process_name],
            xy=(x, y),
            xytext=(6, 4),
            textcoords="offset points",
            ha="left",
            va="bottom",
            fontsize=6.2,
            fontweight="bold",
            fontfamily="Arial",
            color="black",
        )

    ax.axhline(
        0,
        color="black",
        lw=0.9,
        ls="--",
    )
    ax.axvline(
        0,
        color="black",
        lw=0.9,
        ls="--",
    )

    set_axis_titles(
        ax,
        xlabel="Median relative SSP effect (%)",
        ylabel="Median relative AFM effect (%)",
    )

    style_axis(ax)

    save_figure(
        fig,
        pdf_path=FIGURE_DIR / "Figure_S2.pdf",
        png_path=FIGURE_DIR / "Figure_S2.png",
        dpi=600,
    )
    plt.close(fig)


def short_endpoint_label(row) -> str:
    context_map = {
        "methane-storage": "MS",
        "landfill-gas": "LG",
        "natural-gas-purification": "NGP",
        "post-combustion-vsa": "PC",
        "pre-combustion-40-40": "PreC",
    }

    guest_map = {
        "CH4": r"CH$_4$",
        "CO2": r"CO$_2$",
        "N2": r"N$_2$",
        "H2": r"H$_2$",
    }

    context = context_map.get(
        str(row.context),
        str(row.context),
    )
    guest = guest_map.get(
        str(row.guest),
        str(row.guest),
    )
    pressure = float(row.pressure_bar)

    return f"{context} {guest} {pressure:g}"


def load_square_matrix(
    path: Path,
    ordered_ids: list[str],
) -> pd.DataFrame:
    frame = pd.read_csv(
        path,
        index_col=0,
    )

    frame.index = frame.index.astype(str)
    frame.columns = frame.columns.astype(str)

    return frame.loc[
        ordered_ids,
        ordered_ids,
    ]


def figure_s3(
    metadata: pd.DataFrame,
    spearman: pd.DataFrame,
    agreement: pd.DataFrame,
) -> None:
    """Two-panel full endpoint concordance matrices."""
    meta = metadata.copy()

    for col in (
        "temperature_K",
        "pressure_bar",
    ):
        meta[col] = pd.to_numeric(
            meta[col],
            errors="raise",
        )

    meta = meta.sort_values(
        [
            "context",
            "guest",
            "pressure_bar",
        ]
    ).reset_index(drop=True)

    ordered_ids = meta["endpoint_id"].astype(str).tolist()
    labels = [
        short_endpoint_label(row)
        for row in meta.itertuples(index=False)
    ]

    spearman = spearman.loc[
        ordered_ids,
        ordered_ids,
    ]
    agreement = agreement.loc[
        ordered_ids,
        ordered_ids,
    ]

    fig = plt.figure(
        figsize=(8.2, 4.8),
        constrained_layout=False,
    )

    gs = fig.add_gridspec(
        1,
        2,
        left=0.11,
        right=0.94,
        bottom=0.25,
        top=0.94,
        wspace=0.38,
    )

    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])

    im1 = ax1.imshow(
        spearman.to_numpy(dtype=float),
        vmin=-1,
        vmax=1,
        cmap="coolwarm",
        aspect="equal",
        interpolation="nearest",
    )

    im2 = ax2.imshow(
        agreement.to_numpy(dtype=float),
        vmin=0,
        vmax=1,
        cmap="Blues",
        aspect="equal",
        interpolation="nearest",
    )

    for ax in (ax1, ax2):
        ax.set_xticks(
            np.arange(len(labels)),
            labels,
            rotation=90,
        )
        ax.set_yticks(
            np.arange(len(labels)),
            labels,
        )

        ax.tick_params(
            axis="both",
            labelsize=4.5,
            width=0.6,
            length=2.5,
        )

        for lab in (
            list(ax.get_xticklabels())
            + list(ax.get_yticklabels())
        ):
            lab.set_fontfamily("Arial")
            lab.set_fontweight("bold")

        for spine in ax.spines.values():
            spine.set_linewidth(0.8)

    add_panel_label(
        ax1,
        "A",
        x=-0.15,
        y=1.04,
    )
    add_panel_label(
        ax2,
        "B",
        x=-0.15,
        y=1.04,
    )

    cbar1 = fig.colorbar(
        im1,
        ax=ax1,
        fraction=0.046,
        pad=0.025,
    )
    cbar1.set_label(
        r"Spearman $\rho$",
        fontsize=7.0,
        fontweight="bold",
        fontfamily="Arial",
    )

    cbar2 = fig.colorbar(
        im2,
        ax=ax2,
        fraction=0.046,
        pad=0.025,
    )
    cbar2.set_label(
        "Same-sign fraction",
        fontsize=7.0,
        fontweight="bold",
        fontfamily="Arial",
    )

    for cbar in (cbar1, cbar2):
        cbar.ax.tick_params(labelsize=6.0)
        for lab in cbar.ax.get_yticklabels():
            lab.set_fontfamily("Arial")
            lab.set_fontweight("bold")

    save_figure(
        fig,
        pdf_path=FIGURE_DIR / "Figure_S3.pdf",
        png_path=FIGURE_DIR / "Figure_S3.png",
        dpi=600,
    )
    plt.close(fig)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="replace",
        )

    for path in (
        ADS_PATH,
        PROCESS_PATH,
        SPEARMAN_PATH,
        AGREEMENT_PATH,
        META_PATH,
    ):
        require_file(path)

    apply_project17_style()

    ads = pd.read_csv(ADS_PATH)
    process = pd.read_csv(PROCESS_PATH)
    metadata = pd.read_csv(META_PATH)

    meta_order = metadata.sort_values(
        [
            "context",
            "guest",
            "pressure_bar",
        ]
    )["endpoint_id"].astype(str).tolist()

    spearman = load_square_matrix(
        SPEARMAN_PATH,
        meta_order,
    )
    agreement = load_square_matrix(
        AGREEMENT_PATH,
        meta_order,
    )

    figure_s1(ads)
    figure_s2(process)
    figure_s3(
        metadata,
        spearman,
        agreement,
    )

    print("Project 17 SI figures generated")
    print(f"Figure S1: {FIGURE_DIR / 'Figure_S1.pdf'}")
    print(f"Figure S2: {FIGURE_DIR / 'Figure_S2.pdf'}")
    print(f"Figure S3: {FIGURE_DIR / 'Figure_S3.pdf'}")
    print("No raw outcome files were read.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
