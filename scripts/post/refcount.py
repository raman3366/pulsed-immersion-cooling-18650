#!/usr/bin/env python3
"""Reference counters for paper/refs.bib (PROJECT.md §13: keep >55 % ATE and >55 % 2024-26)."""
import re
from pathlib import Path
bib = (Path(__file__).resolve().parents[2] / "paper/refs.bib").read_text()
entries = re.split(r"\n@", "\n" + bib)[1:]
n = len(entries); ate = sum(1 for e in entries if re.search(r"journal\s*=\s*[{\"].*applied thermal engineering", e, re.I))
recent = sum(1 for e in entries if re.search(r"year\s*=\s*[{\"]?\s*(2024|2025|2026)", e))
print(f"refs: {n}   ATE: {ate} ({100*ate/n:.0f}%)   2024-26: {recent} ({100*recent/n:.0f}%)   gates >55%: {'OK' if ate/n>0.55 and recent/n>0.55 else 'FAIL'}")
