#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import pandas as pd


def first_existing(root: Path, *rels: str) -> Path:
    for rel in rels:
        p = root / rel
        if p.is_file():
            return p
    raise FileNotFoundError("None of these source paths exists:\n" + "\n".join(str(root/r) for r in rels))


def modern(root: Path, rel: str) -> Path:
    p = root / rel
    if not p.is_file():
        raise FileNotFoundError(p)
    return p


def read_csv(path: Path, required: set[str] | None = None) -> pd.DataFrame:
    df = pd.read_csv(path)
    if required:
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"{path.name} missing columns: {sorted(missing)}")
    return df


def read_parquet(path: Path, required: set[str] | None = None) -> pd.DataFrame:
    df = pd.read_parquet(path)
    if required:
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"{path.name} missing columns: {sorted(missing)}")
    return df


def assert_n(df: pd.DataFrame, n: int, name: str) -> None:
    if len(df) != n:
        raise RuntimeError(f"{name}: expected {n:,} rows, found {len(df):,}")


def summary_dict(df: pd.DataFrame) -> dict[str, float]:
    if not {"metric", "value"}.issubset(df.columns):
        raise ValueError("Expected primary summary columns 'metric' and 'value'")
    return {str(r.metric): float(r.value) for r in df.itertuples(index=False)}
