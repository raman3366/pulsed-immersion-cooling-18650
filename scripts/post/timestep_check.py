#!/usr/bin/env python3
"""§4.8 time-step independence: identical coarse grid + U=27 model, dt cap
maxDi 10 (liu2023-static-u27) vs maxDi 100 (liu2023-static-dt).
Acceptance: end-value change < 1%. Writes data/processed/timestep_independence.csv.
"""
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]


def t2(case):
    f = sorted((REPO / case).glob("postProcessing/T2probe/cell1/*/T"))[-1]
    df = pd.read_csv(f, comment="#", sep=r"\s+", header=None)
    return df[0].to_numpy(), df.iloc[:, 1:5].mean(axis=1).to_numpy() - 273.15


ta, Ta = t2("cases/validation/liu2023-static-u27")
tb, Tb = t2("cases/validation/liu2023-static-dt")
d = np.interp(ta, tb, Tb) - Ta
end_pct = abs(Tb[-1] - Ta[-1]) / Ta[-1] * 100
row = {
    "grid": "coarse", "model": "U27_k0068",
    "dt_cap_A": "maxDi 10 (dt ~36.5 ms)", "dt_cap_B": "maxDi 100 (dt ~54 ms Co-limited)",
    "T2_end_A_C": round(float(Ta[-1]), 3), "T2_end_B_C": round(float(Tb[-1]), 3),
    "max_abs_dT2_C": round(float(np.abs(d).max()), 4),
    "mean_abs_dT2_C": round(float(np.abs(d).mean()), 4),
    "end_change_pct": round(float(end_pct), 4),
    "verdict": "PASS" if end_pct < 1.0 else "FAIL",
}
out = REPO / "data/processed/timestep_independence.csv"
pd.DataFrame([row]).to_csv(out, index=False)
print(row["verdict"], f"end change {end_pct:.4f}% (<1%)", "->", out.name)
