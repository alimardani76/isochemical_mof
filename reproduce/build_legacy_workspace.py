#!/usr/bin/env python3
"""Build a legacy-compatible Project 17 workspace from the handover repository."""
from __future__ import annotations
import argparse, shutil
from pathlib import Path


def copy_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for p in src.rglob("*"):
        rel=p.relative_to(src); q=dst/rel
        if p.is_dir(): q.mkdir(parents=True, exist_ok=True)
        else:
            q.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p,q)


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",type=Path,default=Path("."))
    ap.add_argument("--output",type=Path,default=Path("workspace"))
    a=ap.parse_args(); root=a.repo_root.resolve(); out=a.output.resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty workspace: {out}")
    out.mkdir(parents=True,exist_ok=True)
    for src,dst in [
        (root/"scripts"/"step1",out/"Step 1 preparation"),
        (root/"scripts"/"step2",out/"Step 2 calculation"),
        (root/"scripts"/"step3",out/"Step 3 production"),
        (root/"results"/"step1",out/"Step 1 results"),
        (root/"results"/"step2",out/"Step 2 results"),
        (root/"results"/"step3",out/"Step 3 results"),
        (root/"figures"/"final",out/"figures")]:
        copy_tree(src,dst)
    audits=root/"scripts"/"audits"
    if audits.exists():
        for p in audits.glob("test_*.py"): shutil.copy2(p,out/p.name)
    copy_tree(root/"submission_upgrade",out/"submission_upgrade")
    (out/"raw").mkdir(exist_ok=True)
    print(f"PASS: legacy-compatible workspace created at {out}")
    print("NEXT: populate workspace/raw from ARC-MOF v7 before rerunning source-dependent stages.")

if __name__=="__main__": main()
