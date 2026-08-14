#!/usr/bin/env python3
"""Project 17 submission-package sanity checker.

Static packaging checks only. This is not a scientific audit and does not replace
stage-specific reconstruction audits.
"""
from __future__ import annotations
import argparse,re
from pathlib import Path
import pandas as pd


def add(rows,severity,category,item,status,detail):
    rows.append(dict(severity=severity,category=category,item=item,status=status,detail=detail))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,required=True)
    ap.add_argument("--output-dir",type=Path,required=True)
    a=ap.parse_args(); root=a.project_root.resolve(); out=a.output_dir.resolve(); out.mkdir(parents=True,exist_ok=True)
    rows=[]

    required=[
        "README.md","HANDOVER.md",".gitignore",
        "data_manifest/RAW_DATA_REQUIRED.md","data_manifest/RAW_DATA_INVENTORY.csv",
        "data_manifest/REPO_FILE_MANIFEST.csv","environment/python-version.txt",
        "manuscript/main.tex","manuscript/SI.tex","manuscript/Project17_References.bib",
        "manuscript/Project17_SI_closure_tables.tex",
        "provenance/SHA256SUMS.txt","reproduce/README.md",
        "reproduce/build_legacy_workspace.py","submission_upgrade/README.md"]
    for r in required:
        ok=(root/r).is_file()
        add(rows,"RED" if not ok else "GREEN","repository_file",r,"PASS" if ok else "FAIL",
            "present" if ok else "missing")

    # Code-license choice is a coauthor/public-release decision, not a scientific blocker.
    lic=(root/"LICENSE").is_file()
    add(rows,"GREEN" if lic else "YELLOW","repository_file","LICENSE",
        "PASS" if lic else "REVIEW",
        "present" if lic else "choose code license before archival/public release")

    # Main figures 1-4 are required. Figure 5 is optional pending structural rendering.
    for i in range(1,5):
        f=f"Figure_{i}.pdf"; p=root/"figures"/"final"/f
        add(rows,"GREEN" if p.is_file() else "RED","figure",f,"PASS" if p.is_file() else "FAIL",str(p))
    f="Figure_5.pdf"; p=root/"figures"/"final"/f
    add(rows,"GREEN" if p.is_file() else "YELLOW","figure",f,"PASS" if p.is_file() else "PENDING",
        "structural-case figure present" if p.is_file() else "optional structural rendering not yet committed")

    # Placeholders / risky wording.
    text_files=[root/"README.md",root/"HANDOVER.md",root/"manuscript"/"main.tex",root/"manuscript"/"SI.tex"]
    for p in text_files:
        if not p.is_file(): continue
        t=p.read_text(encoding="utf-8",errors="replace")
        for pat,label in [(r"\bTODO\b","TODO"),(r"\bTBD\b","TBD"),(r"insert\s+here","insert here")]:
            if re.search(pat,t,re.I):
                add(rows,"RED","placeholder",label,"FAIL",f"found in {p.relative_to(root)}")

    risks=["chemically identical","isostructural","causal deformation","experimental validation",
           "transition pressure","principal drivers","most reliable route"]
    for p in [root/"manuscript"/"main.tex",root/"manuscript"/"SI.tex"]:
        if not p.is_file(): continue
        t=p.read_text(encoding="utf-8",errors="replace")
        for s in risks:
            if s.lower() in t.lower():
                add(rows,"YELLOW","wording_risk",s,"REVIEW",f"found in {p.relative_to(root)}")

    # Reorganized historical scripts are expected to retain legacy path assumptions;
    # the compatibility workspace is the supported execution route.
    compatibility=(root/"reproduce"/"build_legacy_workspace.py").is_file()
    legacy_hits=0
    for p in root.glob("scripts/**/*.py"):
        t=p.read_text(encoding="utf-8",errors="replace")
        if "parents[1]" in t and any(z in t for z in ["Step 1 results","Step 2 results","Step 3 results"]):
            legacy_hits += 1
    add(rows,"GREEN" if compatibility else "RED","path_compatibility","historical relocated scripts",
        "PASS" if compatibility else "FAIL",
        f"{legacy_hits} legacy path-dependent scripts; compatibility workspace {'present' if compatibility else 'missing'}")

    # Submission-upgrade scripts expected.
    for name in [
        "15_geometry_attribution_stability.py","16_uptake_basis_density_robustness.py",
        "17_select_structural_case_studies.py","18_source_stratified_effects.py",
        "19_submission_sanity_check.py","p17_style_v2.py"]:
        p=root/"submission_upgrade"/name
        add(rows,"GREEN" if p.is_file() else "RED","submission_upgrade",name,
            "PASS" if p.is_file() else "FAIL","present" if p.is_file() else "missing")

    df=pd.DataFrame(rows)
    df.to_csv(out/"submission_sanity_report.csv",index=False)
    counts=df.groupby(["severity","status"]).size().reset_index(name="count")
    md=["# Project 17 submission sanity report","",f"Root: `{root}`","",
        "## Summary","",counts.to_markdown(index=False),"","## Findings","",df.to_markdown(index=False)]
    (out/"SUBMISSION_SANITY_REPORT.md").write_text("\n".join(md),encoding="utf-8")
    print(counts.to_string(index=False))
    print("Report:",out/"SUBMISSION_SANITY_REPORT.md")


if __name__=="__main__":
    main()
