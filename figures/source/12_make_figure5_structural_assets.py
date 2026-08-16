#!/usr/bin/env python3
"""Render the locked Figure 5 structural assets with OVITO.

The script consumes the 12 CIFs selected by
``submission_upgrade/17_select_structural_case_studies.py`` and writes exactly
four lossless PNG assets per panel (LOW/HIGH whole-framework views and matched
LOW/HIGH insets), plus a reproducibility manifest.

Scientific scope
----------------
* LOW/HIGH denotes the frozen geometry ordering from the matched-pair analysis,
  not adsorption performance.
* Insets are representative structural context only; they are not adsorption or
  binding-site assignments.
* Pairwise bond cutoffs below are visualization settings. They are not pore
  metrics and must not be interpreted as Df/Di/Dif.

The camera orientations, screen-plane replication, and inset crop coordinates
are locked to the final Figure 5 artwork. B and C intentionally use different
literal [uvw] labels between LOW and HIGH because the corresponding CIF cell
settings differ; the selected views match the physical motif.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image
from ovito.io import import_file
from ovito.modifiers import (
    CreateBondsModifier,
    DeleteSelectedModifier,
    ReplicateModifier,
    SelectTypeModifier,
)
from ovito.vis import BondsVis, TachyonRenderer, Viewport


PANELS = {
    "A": {
        "low": "A_low_DB5-hypotheticalMOF_5048518_2_1_1_19_20_2.cif",
        "high": "A_high_DB5-hypotheticalMOF_5048517_2_0_1_19_20_2.cif",
        "low_dir": "001", "high_dir": "001",
        "low_up": "010", "high_up": "010",
        "inset": (0.50, 0.50, 1400),
        "role": "broad accessible-space contrast",
    },
    "B": {
        "low": "B_low_DB0-m3_o90_o23_f0_fsc.sym.78.cif",
        "high": "B_high_DB0-m3_o52_o23_f0_fsc.sym.17.cif",
        "low_dir": "100", "high_dir": "010",
        "low_up": "001", "high_up": "001",
        "inset": (0.60, 0.60, 1600),
        "role": "AVA-led accessible-space contrast",
    },
    "C": {
        "low": "C_low_DB0-m3_o90_o21_f0_fsc.sym.6.cif",
        "high": "C_high_DB0-m3_o520_o21_f0_fsc.sym.12.cif",
        "low_dir": "010", "high_dir": "100",
        "low_up": "001", "high_up": "001",
        "inset": (0.50, 0.50, 1600),
        "role": "ASA-dominant geometry non-equivalence",
    },
    "D": {
        "low": "D_low_DB0-m3_o25_o26_f0_pcu.sym.33.cif",
        "high": "D_high_DB0-m3_o25_o26_f0_pcu.sym.31.cif",
        "low_dir": "001", "high_dir": "001",
        "low_up": "010", "high_up": "010",
        "inset": (0.33, 0.33, 1800),
        "role": "diameter-dominated counterexample",
    },
    "E": {
        "low": "E_low_DB0-m3_o13_o28_f0_pcu.sym.77.cif",
        "high": "E_high_DB0-m3_o13_o28_f0_pcu.sym.78.cif",
        "low_dir": "001", "high_dir": "001",
        "low_up": "010", "high_up": "010",
        "inset": (0.33, 0.33, 1800),
        "role": "pressure-suppressed diameter contrast",
    },
    "F": {
        "low": "F_low_DB12-ENANIS_clean.cif",
        "high": "F_high_DB12-LUFBUL_clean.cif",
        "low_dir": "010", "high_dir": "010",
        "low_up": "001", "high_up": "001",
        "inset": (0.50, 0.50, 1400),
        "role": "experimental-source accessible-space anchor",
    },
}

ATOM_RADII = {
    "C": 0.28, "N": 0.30, "O": 0.31, "Zn": 0.42,
    "Cu": 0.42, "Cl": 0.29, "H": 0.20,
}
ATOM_COLORS = {
    "C": (0.55, 0.55, 0.55), "N": (0.22, 0.38, 0.82),
    "O": (0.86, 0.20, 0.18), "Zn": (0.47, 0.56, 0.64),
    "Cu": (0.73, 0.49, 0.18), "Cl": (0.28, 0.56, 0.35),
    "H": (0.85, 0.85, 0.85),
}
PAIRWISE_CUTOFFS = {
    ("C", "C"): 1.82, ("C", "N"): 1.80, ("C", "O"): 1.78,
    ("C", "Cl"): 1.92, ("N", "N"): 1.76, ("N", "O"): 1.74,
    ("Zn", "O"): 2.35, ("Zn", "N"): 2.30, ("Zn", "Cl"): 2.80,
    ("Cu", "O"): 2.20, ("Cu", "N"): 2.18, ("Cu", "Cu"): 2.90,
}
BACKGROUND = (1.0, 1.0, 1.0)
FOV_MARGIN = 1.025


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(chunk_size):
            h.update(block)
    return h.hexdigest()


def parse_uvw(value: str) -> np.ndarray:
    text = value.strip().replace("[", "").replace("]", "")
    if len(text) == 3 and all(c.isdigit() for c in text):
        return np.asarray([int(text[0]), int(text[1]), int(text[2])], dtype=float)
    parts = text.replace(",", " ").split()
    if len(parts) != 3:
        raise ValueError(f"Cannot parse [uvw] direction: {value!r}")
    return np.asarray([float(v) for v in parts], dtype=float)


def cell_matrix(cif_path: Path) -> np.ndarray:
    data = import_file(str(cif_path)).compute()
    return np.asarray(data.cell.matrix[:, :3], dtype=float)


def lattice_vector(cell3x3: np.ndarray, uvw_value: str) -> np.ndarray:
    vector = cell3x3 @ parse_uvw(uvw_value)
    norm = np.linalg.norm(vector)
    if norm == 0:
        raise ValueError(f"Zero lattice vector for {uvw_value!r}")
    return vector / norm


def orthogonalized_up(view_vec: np.ndarray, raw_up: np.ndarray) -> np.ndarray:
    up = raw_up - np.dot(raw_up, view_vec) * view_vec
    norm = np.linalg.norm(up)
    if norm < 1e-8:
        trial = np.asarray([0.0, 0.0, 1.0])
        if abs(np.dot(trial, view_vec)) > 0.9:
            trial = np.asarray([0.0, 1.0, 0.0])
        up = trial - np.dot(trial, view_vec) * view_vec
        norm = np.linalg.norm(up)
    return up / norm


def make_viewport(cell3x3: np.ndarray, view_key: str, up_key: str):
    view_vec = lattice_vector(cell3x3, view_key)
    up_vec = orthogonalized_up(view_vec, lattice_vector(cell3x3, up_key))
    viewport = Viewport(type=Viewport.Type.Ortho)
    viewport.camera_dir = tuple(view_vec.tolist())
    viewport.camera_up = tuple(up_vec.tolist())
    return viewport, view_vec, up_vec


def style_types(frame, data) -> None:
    if data.particles is None or "Particle Type" not in data.particles:
        return
    for atom_type in data.particles_.particle_types_.types_:
        if atom_type.name in ATOM_RADII:
            atom_type.radius = ATOM_RADII[atom_type.name]
        if atom_type.name in ATOM_COLORS:
            atom_type.color = ATOM_COLORS[atom_type.name]


def present_types(cif_path: Path) -> set[str]:
    data = import_file(str(cif_path)).compute()
    if data.particles is None or "Particle Type" not in data.particles:
        return set()
    return {t.name for t in data.particles.particle_types.types}


def buffer_replication(direction: str) -> tuple[int, int, int]:
    return {"001": (3, 3, 1), "010": (3, 1, 3), "100": (1, 3, 3)}[direction]


def build_pipeline(cif_path: Path, replication: tuple[int, int, int]):
    pipeline = import_file(str(cif_path))
    pipeline.modifiers.append(SelectTypeModifier(property="Particle Type", types={"H"}))
    pipeline.modifiers.append(DeleteSelectedModifier())
    rx, ry, rz = replication
    pipeline.modifiers.append(ReplicateModifier(num_x=rx, num_y=ry, num_z=rz, adjust_box=True))
    pipeline.modifiers.append(style_types)

    types = present_types(cif_path)
    types.discard("H")
    bonds = CreateBondsModifier(mode=CreateBondsModifier.Mode.Pairwise)
    for (type_a, type_b), cutoff in PAIRWISE_CUTOFFS.items():
        if type_a in types and type_b in types:
            bonds.set_pairwise_cutoff(type_a, type_b, cutoff)
    bonds.vis.width = 0.16
    bonds.vis.coloring_mode = BondsVis.ColoringMode.Uniform
    bonds.vis.color = (0.62, 0.62, 0.62)
    pipeline.modifiers.append(bonds)

    data = pipeline.compute()
    if data.cell is not None:
        data.cell.vis.enabled = False
    particle_count = data.particles.count if data.particles is not None else 0
    bond_count = data.particles.bonds.count if data.particles is not None and data.particles.bonds is not None else 0
    return pipeline, particle_count, bond_count


def fitted_fov(pipeline, cell3x3, direction, up, source_pixels: int) -> float:
    pipeline.add_to_scene()
    try:
        viewport, _, _ = make_viewport(cell3x3, direction, up)
        viewport.zoom_all(size=(source_pixels, source_pixels))
        return float(viewport.fov)
    finally:
        pipeline.remove_from_scene()


def render_source(pipeline, cell3x3, direction, up, common_fov, source_pixels, output_path):
    pipeline.add_to_scene()
    try:
        viewport, view_vec, up_vec = make_viewport(cell3x3, direction, up)
        viewport.zoom_all(size=(source_pixels, source_pixels))
        viewport.fov = float(common_fov)
        renderer = TachyonRenderer(ambient_occlusion=True, shadows=False, antialiasing=True)
        if hasattr(renderer, "samples_per_pixel"):
            try:
                renderer.samples_per_pixel = 24
            except Exception:
                pass
        viewport.render_image(size=(source_pixels, source_pixels), filename=str(output_path), background=BACKGROUND, alpha=False, renderer=renderer)
        return view_vec, up_vec
    finally:
        pipeline.remove_from_scene()


def central_crop(image: Image.Image, target_pixels: int) -> Image.Image:
    width, height = image.size
    left = (width - target_pixels) // 2
    top = (height - target_pixels) // 2
    return image.crop((left, top, left + target_pixels, top + target_pixels))


def crop_at_normalized_center(image, center_x, center_y, crop_pixels):
    width, height = image.size
    half = crop_pixels // 2
    x = int(round(center_x * width))
    y = int(round(center_y * height))
    left = max(0, min(width - crop_pixels, x - half))
    top = max(0, min(height - crop_pixels, y - half))
    return image.crop((left, top, left + crop_pixels, top + crop_pixels))


def save_png(image: Image.Image, path: Path, dpi: int) -> None:
    image.save(path, format="PNG", dpi=(dpi, dpi), optimize=True)


def iter_final_assets(output_dir: Path) -> Iterable[Path]:
    for panel in PANELS:
        panel_dir = output_dir / panel
        yield panel_dir / f"{panel}_LOW_WHOLE_FINAL_600dpi.png"
        yield panel_dir / f"{panel}_HIGH_WHOLE_FINAL_600dpi.png"
        yield panel_dir / f"{panel}_LOW_INSET_FINAL_600dpi.png"
        yield panel_dir / f"{panel}_HIGH_INSET_FINAL_600dpi.png"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cif-dir", type=Path, default=Path("results/submission_upgrade/H4_structural_cases/cifs"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/submission_upgrade/H4_structural_cases/figure5_assets"))
    parser.add_argument("--dpi", type=int, default=600)
    parser.add_argument("--source-pixels", type=int, default=4200)
    parser.add_argument("--working-pixels", type=int, default=3000)
    parser.add_argument("--whole-pixels", type=int, default=2800)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cif_dir = args.cif_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    missing = [cif_dir / spec[side] for spec in PANELS.values() for side in ("low", "high") if not (cif_dir / spec[side]).is_file()]
    if missing:
        raise FileNotFoundError("Missing CIF files:\n" + "\n".join(map(str, missing)))

    run_rows = []
    for panel, spec in PANELS.items():
        panel_dir = output_dir / panel
        panel_dir.mkdir(parents=True, exist_ok=True)
        low_path, high_path = cif_dir / spec["low"], cif_dir / spec["high"]
        low_rep, high_rep = buffer_replication(spec["low_dir"]), buffer_replication(spec["high_dir"])
        low_pipeline, low_particles, low_bonds = build_pipeline(low_path, low_rep)
        high_pipeline, high_particles, high_bonds = build_pipeline(high_path, high_rep)
        low_cell, high_cell = cell_matrix(low_path), cell_matrix(high_path)

        low_fov = fitted_fov(low_pipeline, low_cell, spec["low_dir"], spec["low_up"], args.source_pixels)
        high_fov = fitted_fov(high_pipeline, high_cell, spec["high_dir"], spec["high_up"], args.source_pixels)
        common_fov = max(low_fov, high_fov) * FOV_MARGIN

        low_source = panel_dir / f"{panel}_LOW_SOURCE_BUFFERED.png"
        high_source = panel_dir / f"{panel}_HIGH_SOURCE_BUFFERED.png"
        low_view, low_up_vec = render_source(low_pipeline, low_cell, spec["low_dir"], spec["low_up"], common_fov, args.source_pixels, low_source)
        high_view, high_up_vec = render_source(high_pipeline, high_cell, spec["high_dir"], spec["high_up"], common_fov, args.source_pixels, high_source)

        low_working = central_crop(Image.open(low_source).convert("RGB"), args.working_pixels)
        high_working = central_crop(Image.open(high_source).convert("RGB"), args.working_pixels)
        low_whole_img = central_crop(low_working, args.whole_pixels)
        high_whole_img = central_crop(high_working, args.whole_pixels)

        low_whole = panel_dir / f"{panel}_LOW_WHOLE_FINAL_600dpi.png"
        high_whole = panel_dir / f"{panel}_HIGH_WHOLE_FINAL_600dpi.png"
        save_png(low_whole_img, low_whole, args.dpi)
        save_png(high_whole_img, high_whole, args.dpi)

        center_x, center_y, inset_pixels = spec["inset"]
        low_inset = panel_dir / f"{panel}_LOW_INSET_FINAL_600dpi.png"
        high_inset = panel_dir / f"{panel}_HIGH_INSET_FINAL_600dpi.png"
        save_png(crop_at_normalized_center(low_working, center_x, center_y, inset_pixels), low_inset, args.dpi)
        save_png(crop_at_normalized_center(high_working, center_x, center_y, inset_pixels), high_inset, args.dpi)
        low_source.unlink(missing_ok=True)
        high_source.unlink(missing_ok=True)

        run_rows.append({
            "panel": panel, "role": spec["role"], "low_cif": spec["low"], "high_cif": spec["high"],
            "low_dir": spec["low_dir"], "high_dir": spec["high_dir"], "low_up": spec["low_up"], "high_up": spec["high_up"],
            "low_rep": "x".join(map(str, low_rep)), "high_rep": "x".join(map(str, high_rep)),
            "low_particles": low_particles, "high_particles": high_particles, "low_bonds": low_bonds, "high_bonds": high_bonds,
            "common_fov": f"{common_fov:.10f}", "inset_center_x": center_x, "inset_center_y": center_y,
            "inset_pixels": inset_pixels, "whole_pixels": args.whole_pixels, "dpi": args.dpi,
            "low_camera_dir_xyz": " ".join(f"{x:.8f}" for x in low_view), "high_camera_dir_xyz": " ".join(f"{x:.8f}" for x in high_view),
            "low_camera_up_xyz": " ".join(f"{x:.8f}" for x in low_up_vec), "high_camera_up_xyz": " ".join(f"{x:.8f}" for x in high_up_vec),
        })

    with (output_dir / "render_manifest.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(run_rows[0]))
        writer.writeheader(); writer.writerows(run_rows)

    checksums = {str(path.relative_to(output_dir)).replace("\\", "/"): sha256_file(path) for path in iter_final_assets(output_dir)}
    (output_dir / "asset_sha256.json").write_text(json.dumps(checksums, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PASS: wrote {len(checksums)} final structural assets -> {output_dir}")


if __name__ == "__main__":
    main()
