#!/usr/bin/env python3
"""§4.8 grid convergence (Celik et al. 2008, ASME JFE 130(7):078001) on the
validated Liu case: phi = T2 at end of discharge [degC], three grids at
identical numerics (U=27 model, maxDi 100; coarse uses liu2023-static-dt).

Usage: gci.py N_coarse N_medium N_fine
Gate (§4.8): GCI_fine < 3%. Writes data/processed/gci.csv.
"""
import sys
from math import log
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]


def t2_end(case):
    f = sorted((REPO / case).glob("postProcessing/T2probe/cell1/*/T"))[-1]
    df = pd.read_csv(f, comment="#", sep=r"\s+", header=None)
    return float(df.iloc[-1, 1:5].mean() - 273.15)


N3, N2, N1 = (int(x) for x in sys.argv[1:4])        # coarse, medium, fine
p3 = t2_end("cases/validation/liu2023-static-dt")    # coarse
p2 = t2_end("cases/mesh-study/medium")
p1 = t2_end("cases/mesh-study/fine")

r21 = (N1 / N2) ** (1 / 3)
r32 = (N2 / N3) ** (1 / 3)
e21, e32 = p2 - p1, p3 - p2
s = 1.0 if e32 / e21 > 0 else -1.0
p = 1.0
for _ in range(50):                                  # Celik fixed-point
    q = log((r21**p - s) / (r32**p - s))
    p = abs(log(abs(e32 / e21)) + q) / log(r21)
phi_ext = (r21**p * p1 - p2) / (r21**p - 1)
ea21 = abs(e21 / p1)
gci_fine = 1.25 * ea21 / (r21**p - 1) * 100          # %

row = {
    "phi": "T2_end_C", "N_coarse": N3, "N_medium": N2, "N_fine": N1,
    "r21": round(r21, 4), "r32": round(r32, 4),
    "phi_coarse": p3, "phi_medium": p2, "phi_fine": p1,
    "apparent_order_p": round(p, 3),
    "phi_extrapolated": round(phi_ext, 3),
    "GCI_fine_pct": round(gci_fine, 3),
    "gate_3pct": "PASS" if gci_fine < 3.0 else "FAIL",
}
pd.DataFrame([row]).to_csv(REPO / "data/processed/gci.csv", index=False)
print(f"r21={r21:.3f} r32={r32:.3f}  p={p:.2f}  phi_ext={phi_ext:.3f} C")
print(f"GCI_fine = {gci_fine:.3f}%  -> {row['gate_3pct']} (gate <3%)")
