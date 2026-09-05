#!/usr/bin/env python3
"""§10 validation gate: our T2 probe vs Liu's digitised Fig 9 experiment.

For each case: T2_sim(t) = mean of the 4 mid-height near-surface probes on
cell1; interpolated to the digitised experimental times; errors reported in
degC and as % of the experimental value in degC (Liu's own metric — their
COMSOL scored 2.9%). GATE (PROJECT.md §10): mean error <= 8%.

Writes data/processed/validation_liu3c.csv and a comparison figure.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
CASES = {
    "k=0.068 (physical, D-07 baseline)":
        REPO / "cases/validation/liu2023-static",
    "k=0.6 (Liu effective, sensitivity)":
        REPO / "cases/validation/liu2023-static-k06",
    "k=0.068 + adiabatic lid (free surface)":
        REPO / "cases/validation/liu2023-static-lidadi",
    "k=0.068 + beta 0.8e-3 (half buoyancy)":
        REPO / "cases/validation/liu2023-static-beta08",
    "k=0.068 + acrylic h=38 all faces":
        REPO / "cases/validation/liu2023-static-acrylic",
    "k=0.068 + U=27 (acrylic+bath film)":
        REPO / "cases/validation/liu2023-static-u27",
}
GATE_PCT = 8.0

exp = pd.read_csv(REPO / "data/reference/liu_validation_curves.csv", comment="#")
t_exp = exp.time_s.to_numpy()
T_exp = exp.T2_C.to_numpy()

rows, curves = [], {}
for name, case in CASES.items():
    probes = sorted(case.glob("postProcessing/T2probe/cell1/*/T"))
    if not probes:
        print(f"(skipping {name}: no T2probe output)")
        continue
    df = pd.read_csv(probes[-1], comment="#", sep=r"\s+", header=None)
    t_sim = df[0].to_numpy()
    T_sim = df.iloc[:, 1:5].mean(axis=1).to_numpy() - 273.15
    curves[name] = (t_sim, T_sim)
    Ti = np.interp(t_exp, t_sim, T_sim)
    err = Ti - T_exp
    mae_C = np.abs(err).mean()
    mae_pct = float(np.mean(np.abs(err) / T_exp) * 100)
    max_C = float(np.abs(err).max())
    end_C = float(Ti[-1])
    verdict = "PASS" if mae_pct <= GATE_PCT else "FAIL"
    rows.append({"case": name, "MAE_C": round(mae_C, 3),
                 "MAE_pct": round(mae_pct, 2), "max_err_C": round(max_C, 3),
                 "T2_end_sim_C": round(end_C, 2),
                 "T2_end_exp_C": round(float(T_exp[-1]), 2),
                 "gate_8pct": verdict})
    print(f"{name}\n  MAE {mae_C:.2f} C ({mae_pct:.2f}%)  max {max_C:.2f} C  "
          f"end {end_C:.2f} vs exp {T_exp[-1]:.2f} C  -> {verdict}")

out = pd.DataFrame(rows)
out.to_csv(REPO / "data/processed/validation_liu3c.csv", index=False)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(8, 5.5))
ax.plot(t_exp, T_exp, "o", mfc="none", color="crimson", ms=5,
        label="Liu experiment (digitised Fig 9)")
for (name, (ts, Ts)), c in zip(curves.items(), ("tab:blue", "tab:orange", "tab:green", "tab:purple", "black", "tab:red")):
    ax.plot(ts, Ts, "-", color=c, lw=1.8, label=f"present model, {name}")
ax.set_xlabel("time [s]")
ax.set_ylabel("T2, mid-height cell surface [degC]")
ax.set_title("Liu 3C static-immersion validation (coarse grid)")
ax.legend()
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(REPO / "data/processed/validation_liu3c.png", dpi=150)
print(f"wrote data/processed/validation_liu3c.csv + .png")
