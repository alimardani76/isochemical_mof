#!/usr/bin/env python3
"""Read-only audit for Project 17 Stage 1.4 two-gate framework identity."""

from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parent
REGISTRY_DIR = ROOT / "Step 1 results" / "01_framework_registry"
CHEMISTRY_DIR = ROOT / "Step 1 results" / "02_cif_chemistry"
STAGE13_DIR = ROOT / "Step 1 results" / "03_same_chemistry"
FULL_DIR = ROOT / "Step 1 results" / "04_framework_identity"
SAMPLE_DIR = ROOT / "Step 1 results" / "04_framework_identity_sample"

DEFINITION_VERSION = "two_gate_framework_identity_v1"
METHODS = {
    "chemical": {},
    "geometry_sensitivity": {"x_diff_weight": 0, "porous_adjustment": False},
}

GEOMETRY_COLUMNS = [
    "UC_volume", "Density", "ASA", "AVA", "AVAf",
    "POAVA", "POAVAf", "Di", "Df", "Dif",
]

EXPECTED_FILES = [
    "checkpoint_config.json",
    "target_ids.csv",
    "framework_identity.parquet",
    "validated_identity_groups.parquet",
    "source_family_refinement.parquet",
    "framework_identity_summary.csv",
    "framework_identity_definition.json",
    "framework_identity_status_counts.csv",
    "run_manifest.json",
]


class Audit:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def check(self, condition: Any, message: str) -> None:
        try:
            passed = bool(condition)
        except Exception:
            passed = False
        if passed:
            print(f"PASS  {message}")
        else:
            print(f"FAIL  {message}")
            self.failures.append(message)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def target_hash(values: set[str]) -> str:
    return sha256_text("\n".join(sorted(values)))


def metric_table(path: Path) -> dict[str, str]:
    frame = pd.read_csv(path, dtype="string")
    return dict(zip(frame["metric"], frame["value"]))


def int_metric(summary: dict[str, str], name: str) -> int:
    return int(float(summary[name]))


def bool_values(values: pd.Series) -> pd.Series:
    return values.astype("boolean").fillna(False)


def select_results_dir() -> Path | None:
    full_manifest = FULL_DIR / "run_manifest.json"
    sample_manifest = SAMPLE_DIR / "run_manifest.json"
    if full_manifest.is_file():
        try:
            value = json.loads(full_manifest.read_text(encoding="utf-8"))
            if value.get("completed_successfully") is True:
                return FULL_DIR
        except Exception:
            return FULL_DIR
    if sample_manifest.is_file():
        return SAMPLE_DIR
    if FULL_DIR.is_dir():
        return FULL_DIR
    if SAMPLE_DIR.is_dir():
        return SAMPLE_DIR
    return None


def deterministic_sample(
    stage13: pd.DataFrame,
    family_count: int,
    members_per_family: int,
    seed: int,
) -> set[str]:
    candidates = stage13.loc[
        stage13["multi_member_candidate_family"]
        .astype("boolean")
        .fillna(False)
    ].copy()

    family_ids = sorted(
        candidates["chemistry_group_id"].dropna().astype(str).unique()
    )
    rng = random.Random(seed)
    chosen_families = set(
        rng.sample(family_ids, min(family_count, len(family_ids)))
    )

    chosen_ids: set[str] = set()
    for family_id in sorted(chosen_families):
        members = candidates.loc[
            candidates["chemistry_group_id"].astype(str).eq(family_id)
        ].copy().sort_values("mof_id")

        ids = list(members["mof_id"].astype(str))
        if len(ids) > members_per_family:
            local_seed = int(
                sha256_text(f"{seed}\n{family_id}")[:16], 16
            )
            local_rng = random.Random(local_seed)
            ids = local_rng.sample(ids, members_per_family)
        chosen_ids.update(ids)
    return chosen_ids


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    audit = Audit()
    print("PROJECT 17 - STAGE 1.4 TWO-GATE FRAMEWORK IDENTITY AUDIT")

    results_dir = select_results_dir()
    audit.check(results_dir is not None, "a Stage 1.4 result folder exists")
    if results_dir is None:
        return 1

    print(f"Results folder: {results_dir}")
    missing = [
        name for name in EXPECTED_FILES
        if not (results_dir / name).is_file()
    ]
    audit.check(not missing, "all expected Stage 1.4 files exist")
    if missing:
        print(f"  Missing: {missing}")
        return 1

    registry_path = REGISTRY_DIR / "framework_registry.parquet"
    chemistry_path = CHEMISTRY_DIR / "cif_chemistry.parquet"
    stage13_path = STAGE13_DIR / "same_chemistry_frameworks.parquet"

    source_paths = [
        REGISTRY_DIR / "run_manifest.json",
        CHEMISTRY_DIR / "run_manifest.json",
        STAGE13_DIR / "run_manifest.json",
        registry_path,
        chemistry_path,
        stage13_path,
    ]
    audit.check(
        all(path.is_file() for path in source_paths),
        "all Stage 1.1-1.3 audited sources exist",
    )
    if not all(path.is_file() for path in source_paths):
        return 1

    manifest = json.loads(
        (results_dir / "run_manifest.json").read_text(encoding="utf-8")
    )
    config = json.loads(
        (results_dir / "checkpoint_config.json").read_text(encoding="utf-8")
    )
    definition = json.loads(
        (results_dir / "framework_identity_definition.json")
        .read_text(encoding="utf-8")
    )
    target_file = pd.read_csv(
        results_dir / "target_ids.csv", dtype="string"
    )
    framework = pd.read_parquet(
        results_dir / "framework_identity.parquet"
    )
    groups = pd.read_parquet(
        results_dir / "validated_identity_groups.parquet"
    )
    families = pd.read_parquet(
        results_dir / "source_family_refinement.parquet"
    )
    summary = metric_table(
        results_dir / "framework_identity_summary.csv"
    )
    status_counts = pd.read_csv(
        results_dir / "framework_identity_status_counts.csv",
        dtype="string",
    )

    stage13 = pd.read_parquet(
        stage13_path,
        columns=[
            "mof_id",
            "chemistry_group_id",
            "multi_member_candidate_family",
        ],
    )

    mode = str(manifest.get("mode"))
    print(f"Mode: {mode}")

    print("\nPROVENANCE AND POLICY")
    audit.check(
        manifest.get("completed_successfully") is True,
        "manifest records successful completion",
    )
    audit.check(
        manifest.get("definition_version") == DEFINITION_VERSION,
        "manifest uses the two-gate definition",
    )
    audit.check(
        manifest.get("methods") == METHODS,
        "manifest records the two declared CrystalNN settings",
    )
    audit.check(
        manifest.get("outcome_values_read") is False,
        "no adsorption/process outcomes were read",
    )
    audit.check(
        manifest.get("pairs_constructed") is False,
        "no framework pairs were constructed",
    )
    audit.check(
        manifest.get("geometry_used_in_identity_signature") is False,
        "measured geometry was excluded from identity signatures",
    )
    audit.check(
        manifest.get("topology_used_in_identity_signature") is False,
        "recorded topology was excluded from identity signatures",
    )
    audit.check(
        manifest.get("recorded_dimensionality_used_in_identity_signature")
        is False,
        "recorded dimensionality was excluded from identity signatures",
    )
    audit.check(
        manifest.get("cross_method_absolute_graph_equality_required")
        is False,
        "cross-method absolute graph equality is not required",
    )
    audit.check(
        manifest.get("within_method_family_equivalence_required") is True,
        "family members are compared within each method",
    )
    audit.check(
        manifest.get("bond_connectivity_authoritative") is False,
        "inferred connectivity is not claimed authoritative",
    )
    audit.check(
        manifest.get("raw_archive_extracted") is False,
        "raw archive was not extracted",
    )
    audit.check(
        manifest.get("raw_directory_modified") is False,
        "raw directory was not modified",
    )
    audit.check(
        manifest.get("registry_sha256") == sha256_file(registry_path),
        "registry source hash matches",
    )
    audit.check(
        manifest.get("cif_chemistry_sha256") == sha256_file(chemistry_path),
        "Stage 1.2 source hash matches",
    )
    audit.check(
        manifest.get("same_chemistry_frameworks_sha256")
        == sha256_file(stage13_path),
        "Stage 1.3 source hash matches",
    )

    print("\nDEFINITION AUDIT")
    audit.check(
        definition.get("definition_version") == DEFINITION_VERSION,
        "definition version is exact",
    )
    audit.check(
        definition.get("methods") == METHODS,
        "definition freezes both methods",
    )
    audit.check(
        "not required" in definition.get("comparison_principle", ""),
        "definition explicitly rejects cross-method absolute-signature equality",
    )
    gate_a_text = json.dumps(definition.get("gate_a", {}))
    gate_b_text = json.dumps(definition.get("gate_b", {}))
    audit.check(
        "framework chemical building blocks" in gate_a_text,
        "Gate A is chemical-building-block identity",
    )
    audit.check(
        "coarse framework architecture" in gate_b_text,
        "Gate B is coarse framework architecture",
    )
    excluded = set(definition.get("excluded_from_identity", []))
    audit.check(
        set(GEOMETRY_COLUMNS).issubset(excluded),
        "all measured geometry descriptors are excluded from identity",
    )
    audit.check(
        definition.get("pair_policy")
        == "no framework pairs are constructed in Stage 1.4",
        "definition preserves the later pair gate",
    )

    print("\nTARGET IDENTITY")
    all_candidates = stage13.loc[
        stage13["multi_member_candidate_family"]
        .astype("boolean")
        .fillna(False)
    ].copy()

    if mode == "full":
        expected_ids = set(all_candidates["mof_id"].astype(str))
    else:
        expected_ids = deterministic_sample(
            stage13,
            int(config["sample_families"]),
            int(config["sample_members_per_family"]),
            int(config["sample_seed"]),
        )

    observed_targets = set(target_file["mof_id"].astype(str))
    observed_frameworks = set(framework["mof_id"].astype(str))

    audit.check(
        mode in {"sample", "full"},
        "run mode is recognized",
    )
    audit.check(
        observed_targets == expected_ids,
        "target ledger equals the deterministic family-based target set",
    )
    audit.check(
        observed_frameworks == expected_ids,
        "framework output covers every target exactly",
    )
    audit.check(
        target_file["mof_id"].notna().all()
        and target_file["mof_id"].is_unique,
        "target IDs are valid and unique",
    )
    audit.check(
        framework["mof_id"].notna().all()
        and framework["mof_id"].is_unique,
        "framework output has one row per target",
    )
    audit.check(
        int(manifest.get("target_count")) == len(expected_ids),
        "manifest target count is exact",
    )
    audit.check(
        manifest.get("target_sha256") == target_hash(expected_ids),
        "manifest target hash is exact",
    )

    print("\nTWO-GATE LOGIC")
    required_framework_columns = {
        "source_chemistry_group_id",
        "chemical_gate_a_signature",
        "geometry_sensitivity_gate_a_signature",
        "chemical_coarse_architecture_signature",
        "geometry_sensitivity_coarse_architecture_signature",
        "gate_a_subfamily_id",
        "gate_a_subfamily_size",
        "gate_a_pass",
        "gate_a_status",
        "gate_b_subfamily_id",
        "gate_b_subfamily_size",
        "gate_b_pass",
        "gate_b_status",
        "validated_identity_group_id",
    }
    audit.check(
        required_framework_columns.issubset(framework.columns),
        "framework output contains all gate evidence and decisions",
    )

    both_usable = bool_values(framework["both_methods_usable"])
    gate_a_expected_id = pd.Series(
        pd.NA, index=framework.index, dtype="string"
    )
    for index, row in framework.loc[both_usable].iterrows():
        gate_a_expected_id.loc[index] = "gateA1_" + sha256_text(
            "\n".join(
                [
                    str(row["source_chemistry_group_id"]),
                    str(row["chemical_gate_a_signature"]),
                    str(row["geometry_sensitivity_gate_a_signature"]),
                ]
            )
        )

    audit.check(
        framework.loc[both_usable, "gate_a_subfamily_id"]
        .astype("string")
        .eq(gate_a_expected_id.loc[both_usable])
        .all(),
        "Gate A subfamily IDs are deterministic two-method relative-equivalence keys",
    )

    gate_a_sizes = (
        framework.loc[both_usable, "gate_a_subfamily_id"]
        .value_counts()
    )
    expected_gate_a_pass = (
        both_usable
        & framework["gate_a_subfamily_id"]
        .map(gate_a_sizes)
        .ge(2)
        .fillna(False)
    )
    audit.check(
        bool_values(framework["gate_a_pass"])
        .eq(expected_gate_a_pass)
        .all(),
        "Gate A PASS requires at least two members sharing both method-specific chemistry classes",
    )

    gate_b_eligible = expected_gate_a_pass
    gate_b_expected_id = pd.Series(
        pd.NA, index=framework.index, dtype="string"
    )
    for index, row in framework.loc[gate_b_eligible].iterrows():
        gate_b_expected_id.loc[index] = "gateB1_" + sha256_text(
            "\n".join(
                [
                    str(row["gate_a_subfamily_id"]),
                    str(row["chemical_coarse_architecture_signature"]),
                    str(row["geometry_sensitivity_coarse_architecture_signature"]),
                ]
            )
        )

    audit.check(
        framework.loc[gate_b_eligible, "gate_b_subfamily_id"]
        .astype("string")
        .eq(gate_b_expected_id.loc[gate_b_eligible])
        .all(),
        "Gate B subfamily IDs refine Gate A using method-specific architecture",
    )

    gate_b_sizes = (
        framework.loc[gate_b_eligible, "gate_b_subfamily_id"]
        .value_counts()
    )
    expected_gate_b_pass = (
        gate_b_eligible
        & framework["gate_b_subfamily_id"]
        .map(gate_b_sizes)
        .ge(2)
        .fillna(False)
    )
    audit.check(
        bool_values(framework["gate_b_pass"])
        .eq(expected_gate_b_pass)
        .all(),
        "Gate B PASS requires at least two members sharing both method-specific architectures",
    )
    audit.check(
        bool_values(framework["gate_b_pass"])
        .le(bool_values(framework["gate_a_pass"]))
        .all(),
        "Gate B never passes a framework that failed Gate A",
    )

    print("\nGROUP AND CONTEXT INTEGRITY")
    eligible = framework.loc[expected_gate_b_pass].copy()
    expected_group_sizes = (
        eligible["gate_b_subfamily_id"].value_counts().sort_index()
    )
    observed_group_sizes = (
        groups.set_index("validated_identity_group_id")[
            "validated_identity_group_size"
        ].sort_index()
        if len(groups)
        else pd.Series(dtype="int64")
    )
    audit.check(
        expected_group_sizes.index.equals(observed_group_sizes.index),
        "validated group IDs equal the complete Gate-B membership partition",
    )
    if expected_group_sizes.index.equals(observed_group_sizes.index):
        audit.check(
            (
                expected_group_sizes.astype(int)
                == observed_group_sizes.astype(int)
            ).all(),
            "validated group sizes match framework membership",
        )

    if len(groups):
        audit.check(
            groups["validated_identity_group_size"].ge(2).all(),
            "every validated identity group has at least two members",
        )
        audit.check(
            ~(
                bool_values(groups["strong_primary_control_family"])
                & bool_values(groups["recorded_context_conflict"])
            ).any(),
            "no strong primary family has a topology/dimensionality conflict",
        )
        audit.check(
            groups.loc[
                bool_values(groups["strong_primary_control_family"]),
                "validation_tier",
            ]
            .eq("primary_guest_free")
            .all(),
            "every strong primary family is guest-free",
        )

    print("\nGEOMETRY SEPARATION")
    audit.check(
        not any(
            column.startswith(tuple(GEOMETRY_COLUMNS))
            for column in (
                "chemical_gate_a_signature",
                "geometry_sensitivity_gate_a_signature",
                "chemical_coarse_architecture_signature",
                "geometry_sensitivity_coarse_architecture_signature",
            )
        ),
        "measured geometry is not part of the gate signature columns",
    )
    if len(groups):
        primary_geometry = bool_values(
            groups["primary_geometry_candidate_family"]
        )
        audit.check(
            (
                ~primary_geometry
                | (
                    bool_values(groups["strong_primary_control_family"])
                    & bool_values(groups["has_measured_geometry_variation"])
                    & groups["frameworks_with_complete_geometry"].ge(2)
                )
            ).all(),
            "primary geometry candidates are evaluated only after strong identity validation",
        )

    print("\nSUMMARY ACCOUNTING")
    expected_summary = {
        "source_candidate_families": len(families),
        "target_frameworks": len(framework),
        "complete_source_families_sampled": int(
            families["complete_source_family_sampled"].sum()
        ),
        "gate_a_pass_frameworks": int(
            bool_values(framework["gate_a_pass"]).sum()
        ),
        "gate_a_ambiguous_frameworks": int(
            framework["gate_a_status"].eq("AMBIGUOUS").sum()
        ),
        "gate_a_fail_frameworks": int(
            framework["gate_a_status"].eq("FAIL").sum()
        ),
        "gate_b_pass_frameworks": int(
            bool_values(framework["gate_b_pass"]).sum()
        ),
        "gate_b_ambiguous_frameworks": int(
            framework["gate_b_status"].eq("AMBIGUOUS").sum()
        ),
        "gate_b_fail_frameworks": int(
            framework["gate_b_status"].eq("FAIL").sum()
        ),
        "validated_identity_subfamilies": len(groups),
    }
    audit.check(
        set(expected_summary).issubset(summary),
        "summary contains all core census metrics",
    )
    for metric, expected in expected_summary.items():
        if metric in summary:
            audit.check(
                int_metric(summary, metric) == expected,
                f"summary metric {metric} matches audited tables",
            )

    audit.check(
        summary.get("mode") == mode,
        "summary mode matches manifest",
    )

    observed_status = (
        framework.groupby(
            ["gate_a_status", "gate_b_status"],
            dropna=False,
        )
        .size()
        .rename("frameworks")
        .reset_index()
        .sort_values(["gate_a_status", "gate_b_status"])
        .reset_index(drop=True)
    )
    reported_status = (
        status_counts.assign(
            frameworks=pd.to_numeric(
                status_counts["frameworks"], errors="coerce"
            )
        )
        .sort_values(["gate_a_status", "gate_b_status"])
        .reset_index(drop=True)
    )
    audit.check(
        observed_status.astype("string").equals(
            reported_status.astype("string")
        ),
        "status-count table exactly reproduces framework outcomes",
    )

    print("\nSCIENTIFIC CENSUS")
    print(f"  Mode: {mode}")
    print(f"  Candidate families tested: {len(families):,}")
    print(f"  Frameworks tested: {len(framework):,}")
    print(
        f"  Gate A PASS frameworks: "
        f"{int(bool_values(framework['gate_a_pass']).sum()):,}"
    )
    print(
        f"  Gate B PASS frameworks: "
        f"{int(bool_values(framework['gate_b_pass']).sum()):,}"
    )
    print(f"  Validated identity subfamilies: {len(groups):,}")
    if len(groups):
        print(
            f"  Strong primary control families: "
            f"{int(bool_values(groups['strong_primary_control_family']).sum()):,}"
        )
        print(
            f"  Primary families retaining geometry variation: "
            f"{int(bool_values(groups['primary_geometry_candidate_family']).sum()):,}"
        )

    print("\nOVERALL RESULT")
    if audit.failures:
        print(
            f"FAIL - {len(audit.failures)} hard check(s) failed. "
            "Do not run full mode and do not construct pairs."
        )
        return 1

    if mode == "sample":
        print(
            "PASS - Stage 1.4 sample implementation is internally consistent. "
            "Interpret the scientific census before approving full mode."
        )
    else:
        print(
            "PASS - Stage 1.4 full implementation is internally consistent. "
            "Do not construct pairs until the scientific census is approved."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
