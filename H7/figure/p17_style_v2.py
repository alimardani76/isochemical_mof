#!/usr/bin/env python3
"""Project 17 publication style v2.

Design goals:
- Arial/Helvetica-compatible sans serif.
- Bold scientific typography.
- Editable PDF/SVG text.
- White background; no gridlines.
- Limited, accessible, non-default palette.
- Uppercase panel labels for Project 17 internal consistency.
- Vector-first export.

This module changes appearance only. It must not change plotted data.
"""

from __future__ import annotations

from pathlib import Path
import matplotlib as mpl
import matplotlib.pyplot as plt

PALETTE = {
    # Established Project 17 palette.
    "primary": "#0072B2",      # dark blue
    "secondary": "#56B4E9",    # sky
    "validated": "#009E73",    # green
    "accent": "#E69F00",       # orange
    "sensitivity": "#CC79A7",  # purple
    "warning": "#D55E00",      # vermillion
    "neutral": "#4D4D4D",
    "lightgray": "#BDBDBD",
    "black": "#111111",
    "white": "#FFFFFF",

    # Backward-compatible aliases used by the supplied sprint scripts.
    "ink": "#111111",
    "navy": "#0072B2",
    "blue": "#56B4E9",
    "teal": "#009E73",
    "amber": "#E69F00",
    "coral": "#D55E00",
    "violet": "#CC79A7",
    "slate": "#4D4D4D",
    "midgray": "#BDBDBD",
    "pale": "#F2F2F2",
}

# Semantic aliases. Do not use red/green alone to communicate sign.
SEMANTIC = {
    "frozen": PALETTE["primary"],
    "primary": PALETTE["primary"],
    "positive": PALETTE["validated"],
    "negative": PALETTE["warning"],
    "switching": PALETTE["sensitivity"],
    "sensitivity": PALETTE["accent"],
    "neutral": PALETTE["neutral"],
    "reference": PALETTE["lightgray"],
}

def apply_style(base_font: float = 7.0) -> None:
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"],
        "font.size": base_font,
        "font.weight": "bold",
        "axes.labelweight": "bold",
        "axes.titleweight": "bold",
        "axes.linewidth": 0.7,
        "axes.edgecolor": PALETTE["ink"],
        "axes.labelcolor": PALETTE["ink"],
        "axes.facecolor": "white",
        "axes.grid": False,
        "xtick.color": PALETTE["ink"],
        "ytick.color": PALETTE["ink"],
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": 2.8,
        "ytick.major.size": 2.8,
        "xtick.major.width": 0.7,
        "ytick.major.width": 0.7,
        "lines.linewidth": 1.15,
        "lines.markersize": 4.0,
        "patch.linewidth": 0.7,
        "legend.frameon": False,
        "legend.fontsize": max(5.5, base_font - 0.5),
        "legend.handlelength": 1.5,
        "legend.handletextpad": 0.4,
        "legend.borderaxespad": 0.3,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.03,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "axes.unicode_minus": False,
    })

def clean_axis(ax, left: bool = True, bottom: bool = True) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(left)
    ax.spines["bottom"].set_visible(bottom)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight("bold")

def panel_label(ax, label: str, x: float = -0.12, y: float = 1.05,
                fontsize: float = 10.0) -> None:
    ax.text(
        x, y, str(label).upper(),
        transform=ax.transAxes,
        ha="left", va="bottom",
        fontsize=fontsize,
        fontweight="bold",
        color=PALETTE["ink"],
        clip_on=False,
    )

def export_figure(fig, stem: str | Path, dpi: int = 600) -> None:
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(stem.with_suffix(".pdf"), format="pdf")
    fig.savefig(stem.with_suffix(".svg"), format="svg")
    fig.savefig(stem.with_suffix(".png"), format="png", dpi=dpi)

