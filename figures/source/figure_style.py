"""
Project 17 publication figure style.

Use this module for every main-text and SI figure so typography, colours,
line widths, panel labels, and export settings remain consistent.

Design rules
------------
- Arial / Helvetica-compatible sans-serif typography.
- Bold text throughout, as requested.
- Lowercase bold panel labels.
- White background.
- No plot titles inside the artwork.
- No background gridlines.
- Colour-blind-safe categorical palette.
- Black axis/legend text.
- Vector PDF export with editable TrueType text (fonttype 42).
"""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt


# Colour-blind-safe core palette.
COLORS = {
    "primary": "#0072B2",      # dark blue
    "secondary": "#56B4E9",    # sky blue
    "validated": "#009E73",    # bluish green
    "accent": "#E69F00",       # orange
    "sensitivity": "#CC79A7",  # reddish purple
    "warning": "#D55E00",      # vermillion
    "neutral": "#4D4D4D",      # dark gray
    "light": "#BDBDBD",        # light gray
    "very_light": "#E6E6E6",   # very light gray
    "black": "#111111",
    "white": "#FFFFFF",
}

THRESHOLD_COLORS = {
    5: COLORS["light"],
    10: COLORS["primary"],
    20: COLORS["sensitivity"],
    30: COLORS["warning"],
}


def apply_project17_style() -> None:
    """Apply the shared Project 17 matplotlib style."""
    mpl.rcParams.update(
        {
            # Fonts
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 7.0,
            "font.weight": "bold",
            "axes.labelweight": "bold",
            "axes.titleweight": "bold",
            "axes.unicode_minus": False,

            # Editable embedded fonts
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",

            # Figure / axes
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": COLORS["black"],
            "axes.labelcolor": COLORS["black"],
            "axes.linewidth": 0.8,
            "axes.grid": False,

            # Ticks
            "xtick.color": COLORS["black"],
            "ytick.color": COLORS["black"],
            "xtick.direction": "out",
            "ytick.direction": "out",
            "xtick.major.size": 3.0,
            "ytick.major.size": 3.0,
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,
            "xtick.minor.size": 1.8,
            "ytick.minor.size": 1.8,
            "xtick.minor.width": 0.6,
            "ytick.minor.width": 0.6,

            # Lines / markers
            "lines.linewidth": 1.2,
            "lines.markersize": 4.0,
            "patch.linewidth": 0.8,

            # Legends
            "legend.frameon": False,
            "legend.fontsize": 6.5,
            "legend.handlelength": 1.6,
            "legend.handletextpad": 0.45,
            "legend.borderaxespad": 0.35,
            "legend.columnspacing": 0.9,

            # Saving
            "savefig.facecolor": "white",
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.03,
        }
    )


def style_axis(ax, *, left=True, bottom=True) -> None:
    """Apply consistent minimal axis styling."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(left)
    ax.spines["bottom"].set_visible(bottom)

    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight("bold")
        label.set_fontfamily("Arial")


def panel_label(ax, label: str, x: float = -0.12, y: float = 1.06) -> None:
    """Add a bold lowercase panel label in the upper-left."""
    ax.text(
        x,
        y,
        label,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=9,
        fontweight="bold",
        fontfamily="Arial",
        color=COLORS["black"],
        clip_on=False,
    )


def save_figure(fig, pdf_path, png_path=None, dpi: int = 600) -> None:
    """Save publication PDF and optional high-resolution PNG."""
    fig.savefig(pdf_path, format="pdf")
    if png_path is not None:
        fig.savefig(png_path, format="png", dpi=dpi)
