#!/usr/bin/env python3
"""Extract outcome-blind chemical evidence from Project 17 CIF files.

Scientific role
---------------
This stage parses the CIFs represented in the framework registry and records
composition, element, metal-element, disorder, cell, and charge metadata.  It
does not define "same chemistry", identify framework-node metals, infer bonds,
construct pairs, or inspect adsorption/process outcomes.

Why metal-element rather than framework-metal?
-----------------------------------------------
``pymatgen.Element.is_metal`` classifies elements, not their structural role.
A metal in a parsed CIF may be part of the framework, a counterion, or a guest.
The columns produced here therefore use explicit ``metal_element`` names.  A
later candidate-validation stage must establish framework membership from
connectivity and local coordination evidence.

The archive is streamed and never extracted.  Parsed records are checkpointed
as immutable Parquet parts, so an interrupted run can resume without deleting
completed work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import sys
import tarfile
import warnings
from concurrent.futures import FIRST_COMPLETED, Future, ProcessPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np
import pandas as pd


SCRIPT_VERSION = "1.0.0"
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
REGISTRY_RESULTS = ROOT / "Step 1 results" / "01_framework_registry"
REGISTRY_PATH = REGISTRY_RESULTS / "framework_registry.parquet"
REGISTRY_MANIFEST = REGISTRY_RESULTS / "run_manifest.json"
ARCHIVE_PATH = RAW / "ARCMOF_20241004.tar.gz"

ARCHIVE_REFERENCE_CIF_COUNT = 242_517
DEFAULT_SAMPLE_SIZE = 500
DEFAULT_SAMPLE_SEED = 17
DEFAULT_WORKERS = min(6, max(1, (os.cpu_count() or 2) - 1))
DEFAULT_CHECKPOINT_SIZE = 2_000

SUFFIX_PATTERN = re.compile(r"(?i)(?:\.cif|_repeat|_sqe)$")
NUMBER_UNCERTAINTY_PATTERN = re.compile(r"\([^)]*\)$")
ELEMENT_PREFIX_PATTERN = re.compile(r"([A-Z][a-z]?)")

STRING_COLUMNS = [
    "mof_id",
    "cif_member_path",
    "cif_basename_raw",
    "cif_sha256",
    "text_encoding",
    "failure_code",
    "error_type",
    "error_message",
    "warning_messages",
    "structure_selection_code",
    "chemical_formula_sum_raw",
    "chemical_formula_structural_raw",
    "formula",
    "reduced_formula",
    "composition_json",
    "element_fraction_json",
    "elements",
    "raw_elements",
    "nonmetal_elements",
    "metal_elements",
    "metal_composition_json",
    "oxidation_state_signature_json",
    "raw_charge_tag",
    "raw_cif_audit_error",
]

BOOLEAN_COLUMNS = [
    "parse_ok",
    "raw_cif_audit_ok",
    "has_any_metal_element",
    "single_metal_element",
    "oxidation_states_present",
    "all_species_have_oxidation_states",
    "charge_length_aligned",
    "element_sets_match",
]

INTEGER_COLUMNS = [
    "warning_count",
    "n_data_blocks",
    "n_parsed_structures",
    "selected_structure_index",
    "n_structure_sites",
    "n_distinct_elements",
    "n_distinct_metal_elements",
    "n_disordered_sites",
    "n_partial_occupancy_sites",
    "raw_atom_rows",
    "raw_charge_rows",
    "raw_occupancy_rows",
]

FLOAT_COLUMNS = [
    "metal_amount_in_parsed_cell",
    "net_formal_oxidation_charge",
    "cif_cell_volume",
    "cif_density",
    "charge_numeric_fraction",
    "occupancy_weighted_charge_sum",
]

RESULT_COLUMNS = [
    "mof_id",
    "cif_member_path",
    "cif_basename_raw",
    "cif_sha256",
    "text_encoding",
    "parse_ok",
    "failure_code",
    "error_type",
    "error_message",
    "warning_count",
    "warning_messages",
    "n_data_blocks",
    "n_parsed_structures",
    "selected_structure_index",
    "structure_selection_code",
    "raw_cif_audit_ok",
    "raw_cif_audit_error",
    "chemical_formula_sum_raw",
    "chemical_formula_structural_raw",
    "formula",
    "reduced_formula",
    "composition_json",
    "element_fraction_json",
    "elements",
    "raw_elements",
    "n_distinct_elements",
    "nonmetal_elements",
    "metal_elements",
    "metal_composition_json",
    "n_distinct_metal_elements",
    "has_any_metal_element",
    "single_metal_element",
    "metal_amount_in_parsed_cell",
    "oxidation_states_present",
    "all_species_have_oxidation_states",
    "oxidation_state_signature_json",
    "net_formal_oxidation_charge",
    "n_structure_sites",
    "cif_cell_volume",
    "cif_density",
    "n_disordered_sites",
    "n_partial_occupancy_sites",
    "raw_atom_rows",
    "raw_charge_tag",
    "raw_charge_rows",
    "raw_occupancy_rows",
    "charge_length_aligned",
    "charge_numeric_fraction",
    "occupancy_weighted_charge_sum",
    "element_sets_match",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def canonicalize_member(member_name: str) -> str | None:
    """Apply the exact terminal-decoration rule used by registry Stage 1.1."""
    basename = PurePosixPath(str(member_name).replace("\\", "/")).name.strip()
    if not basename:
        return None
    result = basename
    for _ in range(4):
        updated = SUFFIX_PATTERN.sub("", result)
        if updated == result:
            break
        result = updated
    result = result.strip()
    return result or None


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, np.ndarray, pd.Series)):
        return list(value)
    return [value]


def first_text(value: Any) -> str | None:
    values = as_list(value)
    if not values:
        return None
    text = str(values[0]).strip().strip("'\"")
    return text if text and text not in {".", "?"} else None


def clean_number(value: Any) -> float:
    if value is None:
        return math.nan
    text = str(value).strip().strip("'\"")
    if text.lower() in {"", ".", "?", "nan", "none"}:
        return math.nan
    text = NUMBER_UNCERTAINTY_PATTERN.sub("", text)
    try:
        return float(text)
    except ValueError:
        return math.nan


def element_symbol(value: Any) -> str | None:
    match = ELEMENT_PREFIX_PATTERN.match(str(value).strip())
    return match.group(1) if match else None


def stable_json(mapping: dict[str, float]) -> str:
    cleaned = {
        str(key): round(float(value), 12)
        for key, value in sorted(mapping.items())
    }
    return json.dumps(cleaned, sort_keys=True, separators=(",", ":"))


def empty_record(
    mof_id: str,
    member_name: str | None,
    *,
    basename: str | None = None,
    digest: str | None = None,
    encoding: str | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {column: None for column in RESULT_COLUMNS}
    record.update(
        {
            "mof_id": mof_id,
            "cif_member_path": member_name,
            "cif_basename_raw": basename,
            "cif_sha256": digest,
            "text_encoding": encoding,
            "parse_ok": False,
            "raw_cif_audit_ok": False,
            "warning_count": 0,
            "charge_length_aligned": False,
            "element_sets_match": False,
        }
    )
    return record


def decode_cif(raw_bytes: bytes) -> tuple[str | None, str | None, str | None]:
    """Decode without replacement characters and report the chosen encoding."""
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw_bytes.decode(encoding, errors="strict"), encoding, None
        except UnicodeDecodeError:
            continue
    return None, None, "CIF bytes are neither strict UTF-8 nor strict CP1252"


def raw_block_audit(parser: Any, record: dict[str, Any]) -> None:
    """Add raw CIF-tag evidence without changing structure-parse success."""
    try:
        raw_dict = parser.as_dict()
        record["n_data_blocks"] = len(raw_dict)
        if not raw_dict:
            raise ValueError("pymatgen returned no CIF data blocks")
        block = next(iter(raw_dict.values()))

        record["chemical_formula_sum_raw"] = first_text(
            block.get("_chemical_formula_sum")
        )
        record["chemical_formula_structural_raw"] = first_text(
            block.get("_chemical_formula_structural")
        )

        symbols = as_list(
            block.get("_atom_site_type_symbol")
            or block.get("_atom_site_label")
        )
        occupancies = as_list(block.get("_atom_site_occupancy"))
        if not occupancies and symbols:
            occupancies = [1.0] * len(symbols)

        charge_tag = None
        charges: list[Any] = []
        for key in (
            "_atom_site_charge",
            "_atom_site_partial_charge",
            "_atom_type_partial_charge",
            "_atom_site_mulliken_charge",
        ):
            if key in block:
                charge_tag = key
                charges = as_list(block[key])
                break

        raw_elements = sorted(
            {
                symbol
                for value in symbols
                if (symbol := element_symbol(value)) is not None
            }
        )
        numeric_charges = np.asarray([clean_number(value) for value in charges])
        numeric_occupancies = np.asarray(
            [clean_number(value) for value in occupancies]
        )
        aligned = bool(
            symbols
            and len(symbols) == len(charges) == len(occupancies)
        )
        numeric_fraction = (
            float(np.isfinite(numeric_charges).mean())
            if len(numeric_charges)
            else math.nan
        )
        weighted_sum = math.nan
        if aligned and len(numeric_charges):
            valid = np.isfinite(numeric_charges) & np.isfinite(numeric_occupancies)
            if valid.any():
                weighted_sum = float(
                    np.sum(numeric_charges[valid] * numeric_occupancies[valid])
                )

        record.update(
            {
                "raw_cif_audit_ok": True,
                "raw_elements": ";".join(raw_elements),
                "raw_atom_rows": len(symbols),
                "raw_charge_tag": charge_tag,
                "raw_charge_rows": len(charges),
                "raw_occupancy_rows": len(occupancies),
                "charge_length_aligned": aligned,
                "charge_numeric_fraction": numeric_fraction,
                "occupancy_weighted_charge_sum": weighted_sum,
            }
        )
    except Exception as error:
        record["raw_cif_audit_error"] = (
            f"{type(error).__name__}: {error}"[:1000]
        )


def parse_one(payload: tuple[str, str, str, str, str]) -> dict[str, Any]:
    """Worker process: parse one decoded CIF string with pymatgen."""
    mof_id, member_name, text, digest, encoding = payload
    basename = PurePosixPath(member_name.replace("\\", "/")).name
    record = empty_record(
        mof_id,
        member_name,
        basename=basename,
        digest=digest,
        encoding=encoding,
    )

    try:
        from pymatgen.core import Element
        from pymatgen.io.cif import CifParser

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            parser = CifParser.from_str(text)
            structures = parser.parse_structures(primitive=False)

        record["warning_count"] = len(caught)
        record["warning_messages"] = " | ".join(
            dict.fromkeys(str(item.message)[:300] for item in caught)
        )[:2000]

        raw_block_audit(parser, record)
        record["n_parsed_structures"] = len(structures)
        if not structures:
            record.update(
                {
                    "failure_code": "no_structure_returned",
                    "error_type": "ValueError",
                    "error_message": "pymatgen returned no structure",
                }
            )
            return record

        structure = structures[0]
        composition = structure.composition
        element_amounts = {
            str(symbol): float(amount)
            for symbol, amount in composition.get_el_amt_dict().items()
        }
        total_amount = float(sum(element_amounts.values()))
        element_fractions = {
            symbol: amount / total_amount
            for symbol, amount in element_amounts.items()
        } if total_amount > 0 else {}

        metals: dict[str, float] = {}
        oxidation_states: dict[str, float] = {}
        all_species_have_oxidation_states = True
        net_formal_charge = 0.0
        any_oxidation_state = False
        disordered_sites = 0
        partial_occupancy_sites = 0

        for site in structure:
            if not site.is_ordered:
                disordered_sites += 1
            site_occupancy = float(sum(float(value) for value in site.species.values()))
            if not math.isclose(site_occupancy, 1.0, rel_tol=0.0, abs_tol=1e-6):
                partial_occupancy_sites += 1

            for specie, occupancy_value in site.species.items():
                occupancy = float(occupancy_value)
                symbol = getattr(specie, "symbol", None)
                if symbol is None:
                    all_species_have_oxidation_states = False
                    continue

                try:
                    if bool(Element(symbol).is_metal):
                        metals[symbol] = metals.get(symbol, 0.0) + occupancy
                except Exception:
                    pass

                oxidation_state = getattr(specie, "oxi_state", None)
                if oxidation_state is None:
                    all_species_have_oxidation_states = False
                else:
                    any_oxidation_state = True
                    oxidation_value = float(oxidation_state)
                    key = f"{symbol}:{oxidation_value:g}"
                    oxidation_states[key] = oxidation_states.get(key, 0.0) + occupancy
                    net_formal_charge += oxidation_value * occupancy

        element_symbols = sorted(element_amounts)
        metal_symbols = sorted(metals)
        nonmetal_symbols = sorted(set(element_symbols) - set(metal_symbols))
        raw_elements = set(filter(None, str(record.get("raw_elements") or "").split(";")))

        record.update(
            {
                "parse_ok": True,
                "failure_code": None,
                "error_type": None,
                "error_message": None,
                "selected_structure_index": 0,
                "structure_selection_code": (
                    "only_structure" if len(structures) == 1 else "first_of_multiple"
                ),
                "formula": str(composition.formula),
                "reduced_formula": str(composition.reduced_formula),
                "composition_json": stable_json(element_amounts),
                "element_fraction_json": stable_json(element_fractions),
                "elements": ";".join(element_symbols),
                "n_distinct_elements": len(element_symbols),
                "nonmetal_elements": ";".join(nonmetal_symbols),
                "metal_elements": ";".join(metal_symbols),
                "metal_composition_json": stable_json(metals),
                "n_distinct_metal_elements": len(metal_symbols),
                "has_any_metal_element": bool(metal_symbols),
                "single_metal_element": len(metal_symbols) == 1,
                "metal_amount_in_parsed_cell": float(sum(metals.values())),
                "oxidation_states_present": any_oxidation_state,
                "all_species_have_oxidation_states": (
                    any_oxidation_state and all_species_have_oxidation_states
                ),
                "oxidation_state_signature_json": stable_json(oxidation_states),
                "net_formal_oxidation_charge": (
                    net_formal_charge if any_oxidation_state else math.nan
                ),
                "n_structure_sites": len(structure),
                "cif_cell_volume": float(structure.volume),
                "cif_density": float(structure.density),
                "n_disordered_sites": disordered_sites,
                "n_partial_occupancy_sites": partial_occupancy_sites,
                "element_sets_match": bool(
                    record.get("raw_cif_audit_ok")
                    and raw_elements == set(element_symbols)
                ),
            }
        )
    except Exception as error:
        record.update(
            {
                "parse_ok": False,
                "failure_code": "pymatgen_parse_error",
                "error_type": type(error).__name__,
                "error_message": str(error)[:1000],
            }
        )

    return record


def normalize_result_frame(frame: pd.DataFrame) -> pd.DataFrame:
    for column in RESULT_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA
    frame = frame[RESULT_COLUMNS].copy()
    for column in STRING_COLUMNS:
        frame[column] = frame[column].astype("string")
    for column in BOOLEAN_COLUMNS:
        frame[column] = frame[column].astype("boolean")
    for column in INTEGER_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Int64")
    for column in FLOAT_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype(float)
    return frame


def atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_name(path.name + ".tmp")
    frame.to_parquet(temporary, index=False)
    os.replace(temporary, path)


def atomic_write_text(text: str, path: Path) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def flush_checkpoint(
    buffer: list[dict[str, Any]],
    checkpoint_dir: Path,
    next_part: int,
) -> int:
    if not buffer:
        return next_part
    frame = normalize_result_frame(pd.DataFrame(buffer))
    path = checkpoint_dir / f"part_{next_part:06d}.parquet"
    atomic_write_parquet(frame, path)
    buffer.clear()
    return next_part + 1


def load_checkpoints(checkpoint_dir: Path) -> tuple[list[Path], set[str]]:
    parts = sorted(checkpoint_dir.glob("part_*.parquet"))
    completed: set[str] = set()
    for path in parts:
        ids = pd.read_parquet(path, columns=["mof_id"])["mof_id"].astype(str)
        overlap = completed & set(ids)
        if overlap:
            raise RuntimeError(
                f"Duplicate IDs across checkpoint parts: {sorted(overlap)[:10]}"
            )
        completed.update(ids)
    return parts, completed


def collect_finished(
    pending: dict[Future[dict[str, Any]], tuple[str, str]],
    buffer: list[dict[str, Any]],
) -> dict[Future[dict[str, Any]], tuple[str, str]]:
    done, _ = wait(pending, return_when=FIRST_COMPLETED)
    for future in done:
        mof_id, member_name = pending.pop(future)
        try:
            buffer.append(future.result())
        except Exception as error:
            record = empty_record(mof_id, member_name)
            record.update(
                {
                    "failure_code": "worker_process_error",
                    "error_type": type(error).__name__,
                    "error_message": str(error)[:1000],
                }
            )
            buffer.append(record)
    return pending


def verify_dependencies() -> dict[str, str]:
    missing: list[str] = []
    versions: dict[str, str] = {}
    for package in ("numpy", "pandas", "pyarrow", "pymatgen"):
        try:
            module = __import__(package)
            versions[package] = str(getattr(module, "__version__", "installed"))
        except ImportError:
            missing.append(package)
    if missing:
        raise RuntimeError(
            "Missing Python packages: "
            + ", ".join(missing)
            + ". Install them with: py -m pip install numpy pandas pyarrow pymatgen"
        )
    return versions


def select_targets(
    expected_ids: set[str],
    *,
    full: bool,
    sample_size: int,
    sample_seed: int,
) -> tuple[str, set[str]]:
    if full:
        return "full", set(expected_ids)
    if sample_size < 1:
        raise ValueError("--sample-size must be at least 1")
    ordered = sorted(expected_ids)
    rng = random.Random(sample_seed)
    return "sample", set(rng.sample(ordered, min(sample_size, len(ordered))))


def target_hash(target_ids: set[str]) -> str:
    payload = "\n".join(sorted(target_ids)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_registry() -> tuple[pd.DataFrame, dict[str, Any]]:
    if not REGISTRY_PATH.is_file() or not REGISTRY_MANIFEST.is_file():
        raise FileNotFoundError(
            "Step 1.1 registry outputs are missing. Complete and audit Stage 1.1 first."
        )
    manifest = json.loads(REGISTRY_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("completed_successfully") is not True:
        raise RuntimeError("Step 1.1 manifest is not marked successful")
    registry = pd.read_parquet(REGISTRY_PATH, columns=["mof_id", "has_cif"])
    if registry["mof_id"].isna().any() or not registry["mof_id"].is_unique:
        raise RuntimeError("Step 1.1 registry has invalid mof_id values")
    return registry, manifest


def build_summary(
    result: pd.DataFrame,
    *,
    mode: str,
    target_count: int,
    archive_cif_count: int,
    archive_unique_cif_ids: int,
    archive_outside_registry_count: int,
    registry_cif_count: int,
    checkpoint_parts: int,
) -> pd.DataFrame:
    parsed = result["parse_ok"].fillna(False)
    successful = result.loc[parsed]
    rows = [
        ("mode", mode),
        ("target_CIF_records", target_count),
        ("chemistry_records_written", len(result)),
        ("successful_parses", int(parsed.sum())),
        ("failed_parses", int((~parsed).sum())),
        ("registry_CIF_records", registry_cif_count),
        ("archive_CIF_files", archive_cif_count),
        ("archive_unique_CIF_ids", archive_unique_cif_ids),
        ("archive_CIF_IDs_outside_registry", archive_outside_registry_count),
        ("checkpoint_parts", checkpoint_parts),
        ("raw_CIF_audit_ok", int(successful["raw_cif_audit_ok"].fillna(False).sum())),
        ("single_metal_element", int(successful["single_metal_element"].fillna(False).sum())),
        ("multiple_metal_elements", int(successful["n_distinct_metal_elements"].gt(1).sum())),
        ("no_metal_elements", int(successful["n_distinct_metal_elements"].eq(0).sum())),
        ("element_sets_match", int(successful["element_sets_match"].fillna(False).sum())),
        ("disordered_structures", int(successful["n_disordered_sites"].gt(0).sum())),
        ("multiple_parsed_structures", int(successful["n_parsed_structures"].gt(1).sum())),
        ("oxidation_states_present", int(successful["oxidation_states_present"].fillna(False).sum())),
        ("charge_length_aligned", int(successful["charge_length_aligned"].fillna(False).sum())),
        ("fully_numeric_charge_arrays", int(successful["charge_numeric_fraction"].eq(1.0).sum())),
        ("cp1252_decoded", int(result["text_encoding"].eq("cp1252").sum())),
    ]
    return pd.DataFrame(rows, columns=["metric", "value"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--full",
        action="store_true",
        help="parse all registry-covered CIFs after the sample run is approved",
    )
    mode.add_argument(
        "--sample-size",
        type=int,
        default=DEFAULT_SAMPLE_SIZE,
        help=f"deterministic smoke-test size (default: {DEFAULT_SAMPLE_SIZE})",
    )
    parser.add_argument("--sample-seed", type=int, default=DEFAULT_SAMPLE_SEED)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument(
        "--checkpoint-size", type=int, default=DEFAULT_CHECKPOINT_SIZE
    )
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be at least 1")
    if args.checkpoint_size < 1:
        raise ValueError("--checkpoint-size must be at least 1")

    packages = verify_dependencies()
    if not ARCHIVE_PATH.is_file():
        raise FileNotFoundError(f"Missing CIF archive: {ARCHIVE_PATH}")

    registry, registry_manifest = load_registry()
    registry_ids = set(registry["mof_id"].astype(str))
    expected_ids = set(
        registry.loc[registry["has_cif"].fillna(False), "mof_id"].astype(str)
    )
    mode, targets = select_targets(
        expected_ids,
        full=args.full,
        sample_size=args.sample_size,
        sample_seed=args.sample_seed,
    )

    output_name = "02_cif_chemistry" if mode == "full" else "02_cif_chemistry_sample"
    output_dir = ROOT / "Step 1 results" / output_name
    checkpoint_dir = output_dir / "checkpoint_parts"
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    target_digest = target_hash(targets)
    registry_digest = sha256_file(REGISTRY_PATH)
    config = {
        "script_version": SCRIPT_VERSION,
        "mode": mode,
        "sample_size": None if mode == "full" else len(targets),
        "sample_seed": None if mode == "full" else args.sample_seed,
        "target_sha256": target_digest,
        "registry_sha256": registry_digest,
        "canonicalization": registry_manifest.get("canonicalization"),
    }
    config_path = output_dir / "checkpoint_config.json"
    if config_path.exists():
        prior_config = json.loads(config_path.read_text(encoding="utf-8"))
        if prior_config != config:
            raise RuntimeError(
                f"Existing checkpoint configuration differs in {output_dir}. "
                "Preserve it and use the original arguments."
            )
    else:
        atomic_write_text(json.dumps(config, indent=2), config_path)

    pd.DataFrame({"mof_id": sorted(targets)}).to_csv(
        output_dir / "target_ids.csv", index=False
    )

    completed_manifest_path = output_dir / "run_manifest.json"
    final_output_path = output_dir / "cif_chemistry.parquet"
    if completed_manifest_path.is_file() and final_output_path.is_file():
        completed_manifest = json.loads(
            completed_manifest_path.read_text(encoding="utf-8")
        )
        if (
            completed_manifest.get("completed_successfully") is True
            and completed_manifest.get("target_sha256") == target_digest
        ):
            print(f"Stage 1.2 {mode} output is already complete: {output_dir}")
            print("Run py test.py to audit it.")
            return 0

    parts, completed_ids = load_checkpoints(checkpoint_dir)
    unexpected_checkpoint_ids = completed_ids - targets
    if unexpected_checkpoint_ids:
        raise RuntimeError(
            "Checkpoint contains IDs outside this target set: "
            f"{sorted(unexpected_checkpoint_ids)[:10]}"
        )

    print(f"Project 17 Step 1.2: CIF chemistry extraction ({mode})")
    print("Policy: chemistry evidence only; no pairs or same-chemistry decisions")
    print(f"Targets: {len(targets):,}; resumed records: {len(completed_ids):,}")
    print(f"Workers: {args.workers}; checkpoint size: {args.checkpoint_size:,}")

    started_at = utc_now()
    buffer: list[dict[str, Any]] = []
    next_part = len(parts)
    pending: dict[Future[dict[str, Any]], tuple[str, str]] = {}
    seen_archive_ids: set[str] = set()
    outside_registry_rows: list[dict[str, str]] = []
    archive_cif_count = 0
    submitted = 0

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        with tarfile.open(ARCHIVE_PATH, mode="r|gz") as archive:
            for member in archive:
                if not member.isfile() or not member.name.lower().endswith(".cif"):
                    continue

                archive_cif_count += 1
                mof_id = canonicalize_member(member.name)
                if mof_id is None:
                    raise RuntimeError(f"Empty canonical CIF ID: {member.name}")
                if mof_id in seen_archive_ids:
                    raise RuntimeError(
                        f"Duplicate canonical CIF identifier in archive: {mof_id}"
                    )
                seen_archive_ids.add(mof_id)

                if mof_id not in registry_ids:
                    outside_registry_rows.append(
                        {"mof_id": mof_id, "cif_member_path": member.name}
                    )
                    continue
                if mof_id not in targets or mof_id in completed_ids:
                    continue

                handle = archive.extractfile(member)
                if handle is None:
                    record = empty_record(mof_id, member.name)
                    record.update(
                        {
                            "failure_code": "archive_member_unreadable",
                            "error_type": "OSError",
                            "error_message": "tarfile.extractfile returned None",
                        }
                    )
                    buffer.append(record)
                else:
                    raw_bytes = handle.read()
                    digest = hashlib.sha256(raw_bytes).hexdigest()
                    text, encoding, decode_error = decode_cif(raw_bytes)
                    if text is None:
                        record = empty_record(
                            mof_id,
                            member.name,
                            basename=PurePosixPath(member.name).name,
                            digest=digest,
                        )
                        record.update(
                            {
                                "failure_code": "text_decode_error",
                                "error_type": "UnicodeDecodeError",
                                "error_message": decode_error,
                            }
                        )
                        buffer.append(record)
                    else:
                        future = executor.submit(
                            parse_one,
                            (mof_id, member.name, text, digest, str(encoding)),
                        )
                        pending[future] = (mof_id, member.name)
                        submitted += 1

                if len(pending) >= max(args.workers * 2, 2):
                    collect_finished(pending, buffer)
                if len(buffer) >= args.checkpoint_size:
                    next_part = flush_checkpoint(buffer, checkpoint_dir, next_part)
                    print(
                        f"checkpoint: {len(completed_ids) + submitted:,} encountered; "
                        f"parts={next_part:,}"
                    )

        while pending:
            collect_finished(pending, buffer)
            if len(buffer) >= args.checkpoint_size:
                next_part = flush_checkpoint(buffer, checkpoint_dir, next_part)

    next_part = flush_checkpoint(buffer, checkpoint_dir, next_part)
    parts, completed_ids = load_checkpoints(checkpoint_dir)

    missing_targets = targets - completed_ids
    if missing_targets:
        missing_records = []
        for mof_id in sorted(missing_targets):
            record = empty_record(mof_id, None)
            record.update(
                {
                    "failure_code": "target_CIF_not_found_in_archive_scan",
                    "error_type": "FileNotFoundError",
                    "error_message": "Registry marked has_cif but archive scan did not find the ID",
                }
            )
            missing_records.append(record)
        next_part = flush_checkpoint(missing_records, checkpoint_dir, next_part)
        parts, completed_ids = load_checkpoints(checkpoint_dir)

    frames = [pd.read_parquet(path) for path in parts]
    result = normalize_result_frame(pd.concat(frames, ignore_index=True))
    result = result.sort_values("mof_id").reset_index(drop=True)
    if result["mof_id"].duplicated().any():
        raise RuntimeError("Duplicate chemistry records after checkpoint assembly")
    if set(result["mof_id"].astype(str)) != targets:
        raise RuntimeError("Final chemistry IDs do not exactly equal target IDs")

    atomic_write_parquet(result, final_output_path)
    outside_registry = pd.DataFrame(
        outside_registry_rows,
        columns=["mof_id", "cif_member_path"],
    ).sort_values("mof_id")
    outside_registry.to_csv(output_dir / "archive_cifs_outside_registry.csv", index=False)

    failures = result.loc[
        ~result["parse_ok"].fillna(False),
        [
            "mof_id",
            "cif_member_path",
            "failure_code",
            "error_type",
            "error_message",
        ],
    ]
    failures.to_csv(output_dir / "cif_chemistry_failures.csv", index=False)

    summary = build_summary(
        result,
        mode=mode,
        target_count=len(targets),
        archive_cif_count=archive_cif_count,
        archive_unique_cif_ids=len(seen_archive_ids),
        archive_outside_registry_count=len(outside_registry),
        registry_cif_count=len(expected_ids),
        checkpoint_parts=len(parts),
    )
    summary.to_csv(output_dir / "cif_chemistry_summary.csv", index=False)

    completed_at = utc_now()
    manifest = {
        "script": Path(__file__).name,
        "script_version": SCRIPT_VERSION,
        "mode": mode,
        "sample_seed": None if mode == "full" else args.sample_seed,
        "target_count": len(targets),
        "target_sha256": target_digest,
        "registry_sha256": registry_digest,
        "archive_name": ARCHIVE_PATH.name,
        "archive_reference_cif_count": ARCHIVE_REFERENCE_CIF_COUNT,
        "workers": args.workers,
        "checkpoint_size": args.checkpoint_size,
        "package_versions": packages,
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
        "outcome_values_read": False,
        "pairs_constructed": False,
        "same_chemistry_defined": False,
        "bond_connectivity_inferred": False,
        "framework_node_metals_identified": False,
        "raw_archive_extracted": False,
        "raw_directory_modified": False,
        "completed_successfully": True,
        "metal_definition": (
            "all parsed elements for which pymatgen Element.is_metal is true; "
            "structural role is intentionally unresolved"
        ),
        "structure_selection": "first parsed structure; multiplicity explicitly flagged",
        "output_directory": str(output_dir.relative_to(ROOT)),
    }
    atomic_write_text(json.dumps(manifest, indent=2), completed_manifest_path)

    print(summary.to_string(index=False))
    print(f"Saved results: {output_dir}")
    print("Stop here and run py test.py. Do not start full mode or matching yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
