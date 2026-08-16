#!/usr/bin/env python3
"""Publication-style visual layer for Project 17.

Appearance only: this module must never alter scientific values, frozen pair
membership, orientation, thresholds, estimands, or endpoint definitions.
"""
from __future__ import annotations
from pathlib import Path
import json
import matplotlib as mpl
import matplotlib.pyplot as plt

PALETTE = {
    "ink": "#1A1A1A",
    "blue": "#0072B2",
    "sky": "#56B4E9",
    "teal": "#009E73",
    "amber": "#E69F00",
    "vermillion": "#D55E00",
    "purple": "#CC79A7",
    "slate": "#5F6B73",
    "gray": "#8A8A8A",
    "lightgray": "#C8CDD2",
    "pale": "#EFF3F6",
    "white": "#FFFFFF",
}
SEMANTIC = {
    "primary": PALETTE["blue"],
    "accessible": PALETTE["blue"],
    "diameter": PALETTE["purple"],
    "negative": PALETTE["amber"],
    "reference": PALETTE["gray"],
    "neutral": PALETTE["slate"],
    "highlight": PALETTE["vermillion"],
}
THRESHOLD_COLORS = {5: PALETTE["lightgray"], 10: PALETTE["blue"], 20: PALETTE["purple"], 30: PALETTE["vermillion"]}
PROCESS_COLORS = {
    "methane-storage": PALETTE["blue"],
    "methane-storage-psa": PALETTE["blue"],
    "landfill-gas": PALETTE["teal"],
    "landfill-gas-vpsa": PALETTE["teal"],
    "natural-gas-purification": PALETTE["amber"],
    "post-combustion-vsa": PALETTE["purple"],
    "pre-combustion-40-40": PALETTE["vermillion"],
}
DISPLAY_NAMES = {
    "methane-storage": "Methane storage",
    "methane-storage-psa": "Methane storage",
    "landfill-gas": "Landfill gas",
    "landfill-gas-vpsa": "Landfill gas",
    "natural-gas-purification": "Natural-gas purification",
    "post-combustion-vsa": "Post-combustion",
    "pre-combustion-40-40": "Pre-combustion",
}

BASE_FONT = 7.5
AXIS_LABEL_SIZE = 9.0
TICK_SIZE = 7.2
LEGEND_SIZE = 6.9
ANNOTATION_SIZE = 6.5
PANEL_LABEL_SIZE = 10.8


def apply_style(base_font: float = BASE_FONT) -> None:
    """Apply clean, readable final-size typography without global bold text."""
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"],
        "font.size": base_font,
        "font.weight": "normal",
        "axes.labelsize": AXIS_LABEL_SIZE,
        "axes.labelweight": "bold",
        "axes.titlesize": AXIS_LABEL_SIZE,
        "axes.titleweight": "bold",
        "axes.edgecolor": PALETTE["ink"],
        "axes.labelcolor": PALETTE["ink"],
        "axes.linewidth": 0.75,
        "axes.facecolor": PALETTE["white"],
        "axes.grid": False,
        "xtick.labelsize": TICK_SIZE,
        "ytick.labelsize": TICK_SIZE,
        "xtick.color": PALETTE["ink"],
        "ytick.color": PALETTE["ink"],
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": 3.0,
        "ytick.major.size": 3.0,
        "xtick.major.width": 0.72,
        "ytick.major.width": 0.72,
        "legend.frameon": False,
        "legend.fontsize": LEGEND_SIZE,
        "legend.handlelength": 1.5,
        "legend.handletextpad": 0.45,
        "legend.borderaxespad": 0.3,
        "figure.facecolor": PALETTE["white"],
        "savefig.facecolor": PALETTE["white"],
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.035,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "axes.unicode_minus": False,
    })


def clean_axis(ax, *, left: bool = True, bottom: bool = True) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(left)
    ax.spines["bottom"].set_visible(bottom)
    ax.tick_params(axis="both", labelsize=TICK_SIZE)


def panel_label(ax, label: str, x: float = -0.12, y: float = 1.045, fontsize: float = PANEL_LABEL_SIZE) -> None:
    ax.text(x, y, str(label).upper(), transform=ax.transAxes,
            ha="left", va="bottom", fontsize=fontsize, fontweight="bold",
            color=PALETTE["ink"], clip_on=False)


def zero_line(ax, *, vertical=False, horizontal=True, lw=0.8) -> None:
    if horizontal:
        ax.axhline(0, color=PALETTE["ink"], lw=lw, alpha=0.72, zorder=0)
    if vertical:
        ax.axvline(0, color=PALETTE["ink"], lw=lw, alpha=0.72, zorder=0)


def export_figure(fig, stem: str | Path, dpi: int = 600) -> list[str]:
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext, kwargs in [
        (".pdf", {"format": "pdf"}),
        (".svg", {"format": "svg"}),
        (".png", {"format": "png", "dpi": dpi}),
    ]:
        p = stem.with_suffix(ext)
        fig.savefig(p, **kwargs)
        paths.append(str(p))
    return paths


def save_manifest(path: str | Path, *, script: str, sources: list[str], outputs: list[str], plotting_only_aggregation: list[str] | None = None, notes: dict | None = None) -> None:
    payload = {
        "script": script,
        "pinned_commit": "1e81b1961f3853417b4a5b63eee19e3aefbe07a4",
        "sources": sources,
        "outputs": outputs,
        "plotting_only_aggregation": plotting_only_aggregation or [],
        "scientific_values_modified": False,
        "notes": notes or {},
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def descriptor_label(value: str) -> str:
    return {"Di": r"$D_i$", "Df": r"$D_f$", "Dif": r"$D_{if}$"}.get(str(value), str(value))


def descriptor_family(value: str) -> str:
    return "diameter" if str(value) in {"Di", "Df", "Dif"} else "accessible"


def descriptor_color(value: str) -> str:
    return SEMANTIC[descriptor_family(value)]
