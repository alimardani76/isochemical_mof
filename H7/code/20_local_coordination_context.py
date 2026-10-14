#!/usr/bin/env python3
"""Project 17 H7: local coordination context as a post-freeze explanatory analysis.

Frozen core is read-only. This script does not reconstruct pairs, reorient pairs,
change thresholds, or change the primary endpoint. It fingerprints the two CIFs
already present in each frozen pair, forms high-minus-low local feature changes,
and compares three fixed LightGBM representations under identical CV folds.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import tarfile
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold, KFold

DESCRIPTORS = ["ASA", "AVA", "AVAf", "POAVA", "POAVAf", "Di", "Df", "Dif"]
SEED = 17
N_SPLITS = 5
BOOTSTRAP_REPS = 2000
MIN_FRAMEWORK_COVERAGE = 0.90
MIN_PAIR_COVERAGE = 0.90
SUFFIX_PATTERN = re.compile(r"(?i)(?:\.cif|_repeat|_sqe)$")

LOCAL_FEATURES = [
    "metal_count",
    "metal_fraction",
    "mean_metal_cn",
    "sd_metal_cn",
    "mean_metal_neighbor_distance_A",
    "sd_metal_neighbor_distance_A",
    "mean_metal_distance_cv",
    "frac_O_neighbors",
    "frac_N_neighbors",
    "frac_S_neighbors",
    "mean_abs_metal_neighbor_eneg_diff",
    "mean_tetrahedral_character",
    "mean_square_planar_character",
    "mean_octahedral_character",
    "mean_atomic_degree",
    "sd_atomic_degree",
    "atomic_degree_cv",
    "mean_nearest_metal_metal_distance_A",
    "sd_nearest_metal_metal_distance_A",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def canonicalize_member(name: str) -> str | None:
    base = PurePosixPath(str(name).replace("\\", "/")).name.strip()
    result = base
    for _ in range(4):
        new = SUFFIX_PATTERN.sub("", result)
        if new == result:
            break
        result = new
    return result.strip() or None


def safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", s)


def first_existing(root: Path, rels: list[Path]) -> Path:
    for rel in rels:
        p = root / rel
        if p.is_file():
            return p
    raise FileNotFoundError("None of the required paths exists:\n" + "\n".join(str(root / r) for r in rels))


def resolve_inputs(root: Path) -> dict[str, Path]:
    return {
        "pairs": first_existing(root, [
            Path("results/step2/03_geometry_pairs/primary_geometry_pairs.parquet"),
            Path("Step 2 results/03_geometry_pairs/primary_geometry_pairs.parquet"),
        ]),
        "effects": first_existing(root, [
            Path("results/step3/04_primary_ch4_analysis/primary_ch4_pair_effects.parquet"),
            Path("Step 3 results/04_primary_ch4_analysis/primary_ch4_pair_effects.parquet"),
        ]),
        "geometry": first_existing(root, [
            Path("results/step2/01_geometry_variation/geometry_variation_frameworks.parquet"),
            Path("Step 2 results/01_geometry_variation/geometry_variation_frameworks.parquet"),
        ]),
    }


def validate_frozen_inputs(paths: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pairs = pd.read_parquet(paths["pairs"])
    effects = pd.read_parquet(paths["effects"])
    geometry = pd.read_parquet(paths["geometry"])

    req_pairs = {
        "architecture_group_id", "topology", "driver_low_mof_id", "driver_high_mof_id",
        "driver_descriptor", "primary_10pct_pair", "pair_max_fractional_difference",
        *[f"{d}_a" for d in DESCRIPTORS], *[f"{d}_b" for d in DESCRIPTORS],
        "mof_id_a", "mof_id_b",
    }
    req_effects = {"architecture_group_id", "delta_q_mmol_g", "driver_low_mof_id", "driver_high_mof_id"}
    missing = req_pairs - set(pairs.columns)
    if missing:
        raise ValueError(f"Frozen pair table missing columns: {sorted(missing)}")
    missing = req_effects - set(effects.columns)
    if missing:
        raise ValueError(f"Primary effect table missing columns: {sorted(missing)}")
    if "mof_id" not in geometry.columns:
        raise ValueError("Geometry framework table lacks mof_id")
    density_col = next((c for c in ["Density", "density", "framework_density", "density_g_cm3"] if c in geometry.columns), None)
    if density_col is None:
        raise ValueError("Geometry framework table lacks a density column")

    if len(pairs) != 11072 or len(effects) != 11072:
        raise RuntimeError(f"Frozen-core gate failed: expected 11,072 pairs; pairs={len(pairs)}, effects={len(effects)}")
    if not pairs["primary_10pct_pair"].astype("boolean").fillna(False).all():
        raise RuntimeError("Frozen-core gate failed: at least one pair is not a 10% primary pair")
    if not pairs["architecture_group_id"].is_unique or not effects["architecture_group_id"].is_unique:
        raise RuntimeError("Frozen-core gate failed: architecture_group_id must be unique")

    chk = pairs[["architecture_group_id", "driver_low_mof_id", "driver_high_mof_id"]].merge(
        effects[["architecture_group_id", "driver_low_mof_id", "driver_high_mof_id"]],
        on="architecture_group_id", suffixes=("_pair", "_effect"), validate="one_to_one"
    )
    bad = (chk["driver_low_mof_id_pair"].astype(str) != chk["driver_low_mof_id_effect"].astype(str)) | (
        chk["driver_high_mof_id_pair"].astype(str) != chk["driver_high_mof_id_effect"].astype(str)
    )
    if bad.any():
        raise RuntimeError("Frozen-core gate failed: pair orientation differs between pair and effect tables")

    return pairs, effects, geometry


def extract_needed_cifs(archive: Path, wanted_ids: set[str], cache_dir: Path) -> pd.DataFrame:
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = cache_dir / "cif_cache_manifest.csv"
    if manifest_path.is_file():
        old = pd.read_csv(manifest_path)
        if {"mof_id", "cached_file"}.issubset(old.columns):
            old_ids = set(old["mof_id"].astype(str))
            if wanted_ids.issubset(old_ids):
                ok = True
                for _, r in old[old["mof_id"].astype(str).isin(wanted_ids)].iterrows():
                    if (not (cache_dir / str(r["cached_file"])).is_file()
                        or (cache_dir / str(r["cached_file"])).stat().st_size != int(r.get("size_bytes", -1))
                        or (cache_dir / str(r["cached_file"])).stat().st_size == 0
                        or sha256_file(cache_dir / str(r["cached_file"])) != str(r.get("sha256", ""))):
                        ok = False
                        break
                if ok:
                    return old[old["mof_id"].astype(str).isin(wanted_ids)].copy()

    if not archive.is_file():
        raise FileNotFoundError(archive)

    found: set[str] = set()
    rows: list[dict[str, Any]] = []
    with tarfile.open(archive, "r:gz") as tf:
        for m in tf:
            if not m.isfile() or not m.name.lower().endswith(".cif"):
                continue
            cid = canonicalize_member(m.name)
            if cid not in wanted_ids or cid in found:
                continue
            fh = tf.extractfile(m)
            if fh is None:
                continue
            raw = fh.read()
            dest = cache_dir / f"{safe_name(cid)}.cif"
            if not raw:
                raise RuntimeError(f"Empty CIF member: {m.name}")
            tmp = dest.with_suffix(".cif.tmp")
            tmp.write_bytes(raw)
            tmp.replace(dest)
            rows.append({
                "mof_id": cid,
                "archive_member": m.name,
                "cached_file": dest.name,
                "size_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            })
            found.add(cid)
            if len(found) == len(wanted_ids):
                break

    missing = sorted(wanted_ids - found)
    if missing:
        raise RuntimeError(f"CIF archive is missing {len(missing)} required frozen-pair structures. First: {missing[:10]}")

    out = pd.DataFrame(rows).sort_values("mof_id").reset_index(drop=True)
    out.to_csv(manifest_path, index=False)
    return out


def _dominant_symbol(site) -> str:
    species = list(site.species.items())
    if not species:
        raise ValueError("site has no species")
    specie, _occ = max(species, key=lambda x: float(x[1]))
    return str(specie.element.symbol if hasattr(specie, "element") else specie.symbol)


def _safe_mean(vals: list[float]) -> float:
    a = np.asarray([x for x in vals if x is not None and np.isfinite(x)], dtype=float)
    return float(np.mean(a)) if len(a) else np.nan


def _safe_sd(vals: list[float]) -> float:
    a = np.asarray([x for x in vals if x is not None and np.isfinite(x)], dtype=float)
    return float(np.std(a, ddof=0)) if len(a) else np.nan


def _motif_value(op: dict[str, Any] | None, motif: str) -> float:
    if not op:
        return np.nan
    candidates = []
    for k, v in op.items():
        if v is None:
            continue
        key = str(k).lower().replace("_", " ")
        if motif == "tet" and "tet" in key:
            candidates.append(float(v))
        elif motif == "square" and (("square" in key and "plan" in key) or "sq plan" in key):
            candidates.append(float(v))
        elif motif == "oct" and "oct" in key:
            candidates.append(float(v))
    return float(max(candidates)) if candidates else np.nan


def fingerprint_one(mof_id: str, cif_path: str) -> dict[str, Any]:
    try:
        from pymatgen.core import Structure
        from pymatgen.core.periodic_table import Element
        from pymatgen.analysis.local_env import CrystalNN

        structure = Structure.from_file(cif_path)
        n_atoms = len(structure)
        symbols = [_dominant_symbol(site) for site in structure]
        metal_indices = [i for i, s in enumerate(symbols) if Element(s).is_metal]
        if not metal_indices:
            raise RuntimeError("no metal site identified")

        # Pymatgen docs explicitly suggest x_diff_weight=1.5 and search_cutoff=4.5
        # as a starting point for MOFs. Oxidation states are not required here.
        cnn = CrystalNN(
            weighted_cn=False,
            cation_anion=False,
            distance_cutoffs=(0.5, 1.0),
            x_diff_weight=1.5,
            porous_adjustment=True,
            search_cutoff=4.5,
        )
        all_nn = cnn.get_all_nn_info(structure)
        atomic_degrees = [len(x) for x in all_nn]

        cns: list[float] = []
        all_dist: list[float] = []
        site_distance_cvs: list[float] = []
        neighbor_symbols: list[str] = []
        eneg_diffs: list[float] = []
        tet: list[float] = []
        sq: list[float] = []
        octa: list[float] = []

        for i in metal_indices:
            nns = all_nn[i]
            if not nns:
                continue
            cns.append(float(len(nns)))
            dists: list[float] = []
            metal_el = Element(symbols[i])
            for nn in nns:
                neigh = nn["site"]
                d = float(np.linalg.norm(np.asarray(neigh.coords) - np.asarray(structure[i].coords)))
                if np.isfinite(d):
                    dists.append(d)
                    all_dist.append(d)
                nsym = _dominant_symbol(neigh)
                neighbor_symbols.append(nsym)
                try:
                    nx = Element(nsym).X
                    mx = metal_el.X
                    if nx is not None and mx is not None and np.isfinite(nx) and np.isfinite(mx):
                        eneg_diffs.append(abs(float(mx) - float(nx)))
                except Exception:
                    pass
            if dists:
                m = float(np.mean(dists))
                site_distance_cvs.append(float(np.std(dists, ddof=0) / m) if m > 0 else np.nan)
            try:
                op = cnn.get_local_order_parameters(structure, i)
            except Exception:
                op = None
            tet.append(_motif_value(op, "tet"))
            sq.append(_motif_value(op, "square"))
            octa.append(_motif_value(op, "oct"))

        if not cns:
            raise RuntimeError("metal sites identified but CrystalNN returned no metal neighbours")

        neigh_n = max(1, len(neighbor_symbols))
        mm_nearest: list[float] = []
        if len(metal_indices) >= 2:
            for i in metal_indices:
                ds = [float(structure.get_distance(i, j)) for j in metal_indices if j != i]
                if ds:
                    mm_nearest.append(min(ds))

        mean_degree = float(np.mean(atomic_degrees)) if atomic_degrees else np.nan
        sd_degree = float(np.std(atomic_degrees, ddof=0)) if atomic_degrees else np.nan
        row = {
            "mof_id": mof_id,
            "fingerprint_success": True,
            "failure_reason": "",
            "n_atoms": n_atoms,
            "n_metal_sites": len(metal_indices),
            "n_disordered_sites": int(sum(len(site.species) > 1 for site in structure)),
            "metal_count": float(len(metal_indices)),
            "metal_fraction": float(len(metal_indices) / n_atoms),
            "mean_metal_cn": _safe_mean(cns),
            "sd_metal_cn": _safe_sd(cns),
            "mean_metal_neighbor_distance_A": _safe_mean(all_dist),
            "sd_metal_neighbor_distance_A": _safe_sd(all_dist),
            "mean_metal_distance_cv": _safe_mean(site_distance_cvs),
            "frac_O_neighbors": float(sum(x == "O" for x in neighbor_symbols) / neigh_n),
            "frac_N_neighbors": float(sum(x == "N" for x in neighbor_symbols) / neigh_n),
            "frac_S_neighbors": float(sum(x == "S" for x in neighbor_symbols) / neigh_n),
            "mean_abs_metal_neighbor_eneg_diff": _safe_mean(eneg_diffs),
            "mean_tetrahedral_character": _safe_mean(tet),
            "mean_square_planar_character": _safe_mean(sq),
            "mean_octahedral_character": _safe_mean(octa),
            "mean_atomic_degree": mean_degree,
            "sd_atomic_degree": sd_degree,
            "atomic_degree_cv": float(sd_degree / mean_degree) if np.isfinite(mean_degree) and mean_degree > 0 else np.nan,
            "mean_nearest_metal_metal_distance_A": _safe_mean(mm_nearest),
            "sd_nearest_metal_metal_distance_A": _safe_sd(mm_nearest),
        }
        row["n_missing_local_features"] = int(sum(pd.isna(row[c]) for c in LOCAL_FEATURES))
        return row
    except Exception as exc:
        return {
            "mof_id": mof_id,
            "fingerprint_success": False,
            "failure_reason": f"{type(exc).__name__}: {exc}",
            "traceback_tail": " | ".join(traceback.format_exc().splitlines()[-3:]),
            "n_atoms": np.nan,
            "n_metal_sites": np.nan,
            "n_disordered_sites": np.nan,
            **{c: np.nan for c in LOCAL_FEATURES},
            "n_missing_local_features": len(LOCAL_FEATURES),
        }


def compute_fingerprints(cif_manifest: pd.DataFrame, cache_dir: Path, workers: int) -> pd.DataFrame:
    checkpoint = cache_dir / "framework_local_fingerprints.partial.parquet"
    existing = pd.DataFrame()
    done: set[str] = set()
    if checkpoint.is_file():
        existing = pd.read_parquet(checkpoint)
        done = set(existing["mof_id"].astype(str))

    tasks = [(str(r.mof_id), str(cache_dir / str(r.cached_file))) for r in cif_manifest.itertuples(index=False) if str(r.mof_id) not in done]
    rows: list[dict[str, Any]] = []
    if tasks:
        print(f"Fingerprinting {len(tasks):,} CIFs with {workers} CPU workers")
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(fingerprint_one, mid, path): mid for mid, path in tasks}
            for k, fut in enumerate(as_completed(futures), start=1):
                rows.append(fut.result())
                if k % 250 == 0 or k == len(tasks):
                    block = pd.concat([existing, pd.DataFrame(rows)], ignore_index=True)
                    block = block.drop_duplicates("mof_id", keep="last").sort_values("mof_id").reset_index(drop=True)
                    checkpoint_tmp = checkpoint.with_suffix(".tmp.parquet")
                    block.to_parquet(checkpoint_tmp, index=False)
                    checkpoint_tmp.replace(checkpoint)
                    print(f"  fingerprinted {k:,}/{len(tasks):,}")

    final = pd.read_parquet(checkpoint) if checkpoint.is_file() else existing
    return final.sort_values("mof_id").reset_index(drop=True)


def orient_global_features(pairs: pd.DataFrame, geometry: pd.DataFrame) -> pd.DataFrame:
    out = pairs[["architecture_group_id", "topology", "driver_low_mof_id", "driver_high_mof_id", "driver_descriptor"]].copy()
    low_is_a = pairs["driver_low_mof_id"].astype(str).eq(pairs["mof_id_a"].astype(str)).to_numpy()
    for d in DESCRIPTORS:
        a = pd.to_numeric(pairs[f"{d}_a"], errors="raise").to_numpy(float)
        b = pd.to_numeric(pairs[f"{d}_b"], errors="raise").to_numpy(float)
        low = np.where(low_is_a, a, b)
        high = np.where(low_is_a, b, a)
        out[f"d{d}"] = high - low

    density_col = next(c for c in ["Density", "density", "framework_density", "density_g_cm3"] if c in geometry.columns)
    den = pd.to_numeric(geometry.drop_duplicates("mof_id").set_index("mof_id")[density_col], errors="coerce")
    out["density_low"] = out["driver_low_mof_id"].map(den)
    out["density_high"] = out["driver_high_mof_id"].map(den)
    out["dDensity"] = out["density_high"] - out["density_low"]
    return out


def build_pair_table(pairs: pd.DataFrame, effects: pd.DataFrame, geometry: pd.DataFrame, fp: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = orient_global_features(pairs, geometry)
    base = base.merge(effects[["architecture_group_id", "delta_q_mmol_g"]], on="architecture_group_id", how="left", validate="one_to_one")

    fp_idx = fp.set_index("mof_id")
    success = fp_idx["fingerprint_success"].astype(bool)
    rows = []
    for r in base.itertuples(index=False):
        low = str(r.driver_low_mof_id)
        high = str(r.driver_high_mof_id)
        low_ok = low in fp_idx.index and bool(success.get(low, False))
        high_ok = high in fp_idx.index and bool(success.get(high, False))
        rec = {"architecture_group_id": r.architecture_group_id, "local_pair_complete": low_ok and high_ok}
        for c in LOCAL_FEATURES:
            lv = fp_idx.at[low, c] if low_ok else np.nan
            hv = fp_idx.at[high, c] if high_ok else np.nan
            rec[f"dlocal_{c}"] = float(hv - lv) if pd.notna(hv) and pd.notna(lv) else np.nan
        rows.append(rec)
    local = pd.DataFrame(rows)
    full = base.merge(local, on="architecture_group_id", how="left", validate="one_to_one")

    fw_success = float(fp["fingerprint_success"].mean())
    pair_success = float(full["local_pair_complete"].mean())
    coverage = pd.DataFrame([
        {"level": "framework", "n_total": len(fp), "n_complete": int(fp["fingerprint_success"].sum()), "fraction_complete": fw_success, "minimum_required": MIN_FRAMEWORK_COVERAGE},
        {"level": "pair", "n_total": len(full), "n_complete": int(full["local_pair_complete"].sum()), "fraction_complete": pair_success, "minimum_required": MIN_PAIR_COVERAGE},
    ])
    if fw_success < MIN_FRAMEWORK_COVERAGE or pair_success < MIN_PAIR_COVERAGE:
        raise RuntimeError(
            f"Predeclared coverage gate failed: framework={fw_success:.3f} (min {MIN_FRAMEWORK_COVERAGE}), "
            f"pair={pair_success:.3f} (min {MIN_PAIR_COVERAGE}). Do not tune CrystalNN after viewing outcomes."
        )
    return full, coverage


def make_model(n_jobs: int) -> LGBMRegressor:
    from lightgbm import LGBMRegressor
    return LGBMRegressor(
        objective="regression_l1",
        n_estimators=400,
        learning_rate=0.035,
        num_leaves=24,
        max_depth=6,
        min_child_samples=40,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_alpha=0.10,
        reg_lambda=0.50,
        random_state=SEED,
        n_jobs=n_jobs,
        deterministic=True,
        force_col_wise=True,
        verbosity=-1,
    )


def impute_train_test(Xtr: pd.DataFrame, Xte: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    med = Xtr.median(axis=0, skipna=True).fillna(0.0)
    return Xtr.fillna(med), Xte.fillna(med)


def metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    rho = spearmanr(y, p).statistic
    return {"spearman_rho": float(rho), "mae": float(mean_absolute_error(y, p)), "r2": float(r2_score(y, p))}


def run_cv(data: pd.DataFrame, feature_sets: dict[str, list[str]], scheme: str, n_jobs: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    y = pd.to_numeric(data["delta_q_mmol_g"], errors="raise").to_numpy(float)
    if scheme == "random_5fold":
        splitter = KFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)
        splits = list(splitter.split(data))
    elif scheme == "topology_grouped_5fold":
        groups = data["topology"].astype(str).to_numpy()
        if len(np.unique(groups)) < N_SPLITS:
            raise RuntimeError("Fewer than five unique topology groups")
        splitter = GroupKFold(n_splits=N_SPLITS)
        splits = list(splitter.split(data, y, groups=groups))
    else:
        raise ValueError(scheme)

    pred_rows = []
    fold_rows = []
    shap_rows = []

    for fold, (tr, te) in enumerate(splits, start=1):
        fold_pred = {
            "architecture_group_id": data.iloc[te]["architecture_group_id"].astype(str).to_numpy(),
            "topology": data.iloc[te]["topology"].astype(str).to_numpy(),
            "split_scheme": scheme,
            "fold": fold,
            "y_true": y[te],
        }
        for model_name, features in feature_sets.items():
            Xtr, Xte = impute_train_test(data.iloc[tr][features], data.iloc[te][features])
            model = make_model(n_jobs)
            model.fit(Xtr, y[tr])
            pred = model.predict(Xte)
            fold_pred[f"pred_{model_name}"] = pred
            m = metrics(y[te], pred)
            fold_rows.append({"split_scheme": scheme, "fold": fold, "model": model_name, "n_train": len(tr), "n_test": len(te), **m})

            if model_name == "combined":
                contrib = model.booster_.predict(Xte, pred_contrib=True)
                # Last column is expected value/bias.
                for j, f in enumerate(features):
                    vals = contrib[:, j]
                    shap_rows.append(pd.DataFrame({
                        "split_scheme": scheme,
                        "fold": fold,
                        "architecture_group_id": data.iloc[te]["architecture_group_id"].astype(str).to_numpy(),
                        "feature": f,
                        "shap_value": vals,
                    }))

        pred_rows.append(pd.DataFrame(fold_pred))

    return pd.concat(pred_rows, ignore_index=True), pd.DataFrame(fold_rows), pd.concat(shap_rows, ignore_index=True)


def summarize_metrics(fold_metrics: pd.DataFrame) -> pd.DataFrame:
    return (fold_metrics.groupby(["split_scheme", "model"], as_index=False)
            .agg(n_folds=("fold", "size"),
                 spearman_mean=("spearman_rho", "mean"), spearman_sd=("spearman_rho", "std"),
                 mae_mean=("mae", "mean"), mae_sd=("mae", "std"),
                 r2_mean=("r2", "mean"), r2_sd=("r2", "std")))


def paired_bootstrap(pred: pd.DataFrame, reps: int = BOOTSTRAP_REPS) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    y = pred["y_true"].to_numpy(float)
    pg = pred["pred_geometry"].to_numpy(float)
    pc = pred["pred_combined"].to_numpy(float)
    n = len(y)
    rows = []
    for b in range(reps):
        idx = rng.integers(0, n, size=n)
        yg, gg, cc = y[idx], pg[idx], pc[idx]
        rg = spearmanr(yg, gg).statistic
        rc = spearmanr(yg, cc).statistic
        rows.append({
            "bootstrap": b + 1,
            "delta_spearman_combined_minus_geometry": float(rc - rg),
            "mae_improvement_geometry_minus_combined": float(mean_absolute_error(yg, gg) - mean_absolute_error(yg, cc)),
        })
    return pd.DataFrame(rows)


def preflight(root: Path, archive: Path) -> None:
    paths = resolve_inputs(root)
    pairs, effects, geometry = validate_frozen_inputs(paths)
    if not archive.is_file():
        raise FileNotFoundError(archive)
    unique_ids = set(pairs["driver_low_mof_id"].astype(str)) | set(pairs["driver_high_mof_id"].astype(str))
    print("H7 PREFLIGHT PASS")
    print(f"Frozen pairs: {len(pairs):,}")
    print(f"Unique CIFs required: {len(unique_ids):,}")
    print(f"Primary effects: {len(effects):,}")
    print(f"Geometry framework rows: {len(geometry):,}")
    print(f"CIF archive: {archive}")
    print("Frozen core will be read only.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, default=None)
    ap.add_argument("--archive", type=Path, default=None)
    ap.add_argument("--workers", type=int, default=max(1, min(24, (os.cpu_count() or 8) - 2)))
    ap.add_argument("--lgbm-threads", type=int, default=max(1, min(16, os.cpu_count() or 8)))
    ap.add_argument("--preflight", action="store_true")
    args = ap.parse_args()

    root = args.project_root.resolve()
    out = (args.output_dir or (Path(__file__).resolve().parent / "results")).resolve()
    archive = (args.archive or (root / "raw/ARCMOF_20241004.tar.gz")).resolve()

    if args.preflight:
        preflight(root, archive)
        return

    out.mkdir(parents=True, exist_ok=True)
    paths = resolve_inputs(root)
    pairs, effects, geometry = validate_frozen_inputs(paths)

    unique_ids = set(pairs["driver_low_mof_id"].astype(str)) | set(pairs["driver_high_mof_id"].astype(str))
    cache_dir = Path(__file__).resolve().parent / ".cache"
    cif_dir = cache_dir / "cifs"
    cif_manifest = extract_needed_cifs(archive, unique_ids, cif_dir)
    fp = compute_fingerprints(cif_manifest, cif_dir, args.workers)

    # Persist framework-level results and QC.
    fp.to_parquet(out / "framework_local_fingerprints.parquet", index=False)
    qc_cols = ["mof_id", "fingerprint_success", "failure_reason", "traceback_tail", "n_atoms", "n_metal_sites", "n_disordered_sites", "n_missing_local_features"]
    for c in qc_cols:
        if c not in fp.columns:
            fp[c] = "" if c in {"failure_reason", "traceback_tail"} else np.nan
    fp[qc_cols].to_csv(out / "fingerprint_qc.csv", index=False)

    full, coverage = build_pair_table(pairs, effects, geometry, fp)
    coverage.to_csv(out / "coverage_summary.csv", index=False)
    full.to_parquet(out / "pair_local_feature_changes.parquet", index=False)

    # Representation comparison is restricted to the same complete-pair subset.
    model_data = full[full["local_pair_complete"].astype(bool)].copy().reset_index(drop=True)
    feature_coverage = []
    for c in [x for x in model_data if x.startswith("dlocal_")]:
        s = model_data[c]
        feature_coverage.append({"feature": c, "n_pairs": len(s),
                                 "missing": int(s.isna().sum()),
                                 "nonzero": int((s.fillna(0).abs() > 1e-12).sum()),
                                 "unique_nonmissing": int(s.nunique())})
    pd.DataFrame(feature_coverage).to_csv(out / "local_feature_coverage.csv", index=False)
    global_features = [f"d{d}" for d in DESCRIPTORS] + ["dDensity"]
    local_features = [f"dlocal_{c}" for c in LOCAL_FEATURES]
    feature_sets = {
        "geometry": global_features,
        "local": local_features,
        "combined": global_features + local_features,
    }

    all_preds = []
    all_folds = []
    all_shap = []
    all_boot = []
    for scheme in ["random_5fold", "topology_grouped_5fold"]:
        print(f"Running {scheme}")
        pred, fold, shap_long = run_cv(model_data, feature_sets, scheme, args.lgbm_threads)
        all_preds.append(pred); all_folds.append(fold); all_shap.append(shap_long)
        boot = paired_bootstrap(pred)
        boot.insert(0, "split_scheme", scheme)
        all_boot.append(boot)

    preds = pd.concat(all_preds, ignore_index=True)
    folds = pd.concat(all_folds, ignore_index=True)
    shap_long = pd.concat(all_shap, ignore_index=True)
    boot = pd.concat(all_boot, ignore_index=True)
    comparison = summarize_metrics(folds)
    shap_summary = (shap_long.groupby(["split_scheme", "feature"], as_index=False)
                    .agg(mean_abs_shap=("shap_value", lambda s: float(np.mean(np.abs(s)))),
                         median_abs_shap=("shap_value", lambda s: float(np.median(np.abs(s)))),
                         mean_shap=("shap_value", "mean")))

    preds.to_csv(out / "cv_predictions.csv", index=False)
    folds.to_csv(out / "cv_fold_metrics.csv", index=False)
    comparison.to_csv(out / "model_comparison.csv", index=False)
    comparison[comparison["split_scheme"] == "topology_grouped_5fold"].to_csv(out / "topology_grouped_model_comparison.csv", index=False)
    boot.to_csv(out / "incremental_value_bootstrap.csv", index=False)
    shap_summary.to_csv(out / "shap_feature_importance.csv", index=False)


    manifest = {
        "script": "20_local_coordination_context.py",
        "completed_at_utc": utc_now(),
        "post_freeze": True,
        "frozen_pair_count_expected": 11072,
        "frozen_pair_membership_modified": False,
        "pair_orientation_modified": False,
        "geometry_threshold_modified": False,
        "primary_endpoint_modified": False,
        "primary_endpoint": "CH4 298 K 65 bar; delta_q_mmol_g = geometry-high minus geometry-low",
        "random_seed": SEED,
        "cv_folds": N_SPLITS,
        "bootstrap_reps": BOOTSTRAP_REPS,
        "coverage_gate": {"framework": MIN_FRAMEWORK_COVERAGE, "pair": MIN_PAIR_COVERAGE},
        "crystalnn": {
            "weighted_cn": False,
            "cation_anion": False,
            "distance_cutoffs": [0.5, 1.0],
            "x_diff_weight": 1.5,
            "porous_adjustment": True,
            "search_cutoff": 4.5,
        },
        "lightgbm": {
            "objective": "regression_l1", "n_estimators": 400, "learning_rate": 0.035,
            "num_leaves": 24, "max_depth": 6, "min_child_samples": 40,
            "subsample": 0.85, "colsample_bytree": 0.85, "reg_alpha": 0.10, "reg_lambda": 0.50,
            "deterministic": True,
        },
        "input_sha256": {k: sha256_file(v) for k, v in paths.items()},
        "archive": archive.name,
        "frameworks_requested": len(unique_ids),
        "frameworks_fingerprinted_successfully": int(fp["fingerprint_success"].sum()),
        "pairs_in_common_model_subset": len(model_data),
        "outputs": sorted(p.name for p in out.iterdir() if p.is_file()),
    }
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("\nH7 PASS")
    print(coverage.to_string(index=False))
    print("\nMODEL COMPARISON")
    print(comparison.to_string(index=False))
    print(f"\nOutputs: {out}")
    print("Plot separately: python " + str(Path(__file__).resolve().parents[1] / "figure" / "make_figure6.py"))


if __name__ == "__main__":
    main()
