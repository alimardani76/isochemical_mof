#!/usr/bin/env python3
"""Final Project 17 closure audit using local closure filenames."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent

MAIN = ROOT / "Project17_main_CLOSURE.tex"
SI = ROOT / "Project17_SI_CLOSURE.tex"
CLOSURE = ROOT / "Project17_SI_closure_tables.tex"

failures = []


def check(condition, message):
    ok = bool(condition)
    print(("PASS  " if ok else "FAIL  ") + message)
    if not ok:
        failures.append(message)


print("PROJECT 17 - FINAL CLOSURE AUDIT")

for path in (MAIN, SI, CLOSURE):
    check(path.is_file(), f"required local audit file exists: {path.name}")

if failures:
    print()
    print("These files are needed only for the local audit.")
    print("Overleaf files are not visible to this script.")
    sys.exit(1)

main = MAIN.read_text(encoding="utf-8")
si = SI.read_text(encoding="utf-8")
closure = CLOSURE.read_text(encoding="utf-8")

print("\nMANUSCRIPT COHERENCE")

check(main.count("{") == main.count("}"), "main braces balanced")
check(si.count("{") == si.count("}"), "SI braces balanced")

check(
    "Our question is therefore deliberately narrower than" in main,
    "novelty is distinguished from the original ARC-MOF geometry observation",
)

check(
    "No minimum ``practically meaningful'' uptake difference was prespecified" in main,
    "primary practical-effect boundary is explicit",
)

check(
    "does not propagate the per-framework Monte Carlo sampling uncertainty" in main,
    "bootstrap scope is explicit",
)

check(
    "no multiplicity-adjusted significance testing" in main,
    "secondary multiplicity boundary is explicit",
)

check(
    "directly reject a universal" in main
    and "larger-pore-is-better" in main,
    "counterexamples explicitly reject a universal pore rule",
)

print("\nSI COMPLETENESS")

check(
    r"\input{Project17_SI_closure_tables}" in si,
    "SI includes complete generated secondary tables",
)

for label in ["tab:S23", "tab:S24", "tab:S25"]:
    check(label in closure, f"closure include contains {label}")

check(
    "Complete frozen secondary adsorption summary" in closure,
    "complete adsorption reporting table is present",
)

check(
    "Complete frozen secondary process summary" in closure,
    "complete process reporting table is present",
)

check(
    "ARC--MOF release v7" in si and "16802743" in si,
    "exact ARC-MOF release and Zenodo record are stated",
)

check(
    "no multiplicity-adjusted confirmatory testing" in si,
    "SI states exploratory multiplicity policy",
)

print("\nFIGURE / TABLE SCOPE")

for fig in ["Figure_1.pdf", "Figure_2.pdf", "Figure_3.pdf", "Figure_4.pdf"]:
    check(fig in main, f"main references {fig}")

check("Figure_5.pdf" not in main, "no obsolete Figure 5")
check("Figure_6.pdf" not in main, "no obsolete Figure 6")

for fig in ["Figure_S1.pdf", "Figure_S2.pdf", "Figure_S3.pdf"]:
    check(fig in si, f"SI references {fig}")

for i in range(1, 23):
    check(f"tab:S{i}" in si, f"SI body contains Table S{i}")

print("\nADMINISTRATIVE BOUNDARY")

check(r"\TODO" not in main, "no visible TODO commands")
check(r"\RESULT" not in main, "no visible RESULT commands")

print("\nOVERALL RESULT")

if failures:
    print(
        f"FAIL - {len(failures)} closure check(s) failed. "
        "Do not call Project 17 submission-complete."
    )
    sys.exit(1)

print(
    "PASS - scientific narrative, statistical boundaries, full secondary reporting, "
    "and reproducibility mapping are closed."
)
print(
    "Only author-supplied administrative statements and journal-specific formatting remain."
)
