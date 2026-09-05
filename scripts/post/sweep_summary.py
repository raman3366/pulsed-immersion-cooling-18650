#!/usr/bin/env python3
"""D-12 scoring of the sine sweep: uniformity (dT_module, sigma_T) and
pump energy vs (f, A) at fixed Qbar, against the steady Q2 baseline.
Reads data/processed/pareto.csv; writes sweep_summary.csv + sweep_dT_map.png.
"""
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[2]
pr = pd.read_csv(REPO / "data/processed/pareto.csv")
base = pr[pr.case == "steady_f0.00_A0.00_Q2_C3"]
assert len(base), "steady Q2 baseline row missing from pareto.csv"
b = base.iloc[-1]
sw = pr[pr.case.str.startswith("sine_")].copy()
sw["dT_rel_pct"] = (sw.dT_module_K / b.dT_module_K - 1) * 100
sw["sigmaT_rel_pct"] = (sw.sigmaT_K / b.sigmaT_K - 1) * 100
sw["Tmax_delta_K"] = sw.Tmax_C - b.Tmax_C
sw["Epump_rel"] = sw.Epump_model_J / b.Epump_model_J        # D-17 primary basis
sw["Epump_meas_rel"] = sw.Epump_J / b.Epump_J             # aliased measured integral (validation only)
sw = sw.sort_values(["freq_hz", "amp"])
sw.to_csv(REPO / "data/processed/sweep_summary.csv", index=False)
print(f"steady Q2 baseline: dT={b.dT_module_K:.3f} K sigma={b.sigmaT_K:.3f} K "
      f"Tmax={b.Tmax_C:.2f} C Epump(model)={b.Epump_model_J*1e3:.3f} mJ")
print(sw[["case", "freq_hz", "amp", "dT_module_K", "dT_rel_pct",
          "sigmaT_rel_pct", "Tmax_delta_K", "Epump_rel", "Epump_meas_rel"]].to_string(index=False))

# uniformity map dT_rel(f, A)
fs, As = sorted(sw.freq_hz.unique()), sorted(sw.amp.unique())
Z = np.full((len(As), len(fs)), np.nan)
for _, r in sw.iterrows():
    Z[As.index(r.amp), fs.index(r.freq_hz)] = r.dT_rel_pct
fig, ax = plt.subplots(figsize=(7, 4.5))
im = ax.imshow(Z, origin="lower", aspect="auto", cmap="RdBu_r",
               vmin=-np.nanmax(abs(Z)), vmax=np.nanmax(abs(Z)))
ax.set_xticks(range(len(fs))); ax.set_xticklabels(fs)
ax.set_yticks(range(len(As))); ax.set_yticklabels(As)
ax.set_xlabel("pulsation frequency f [Hz]"); ax.set_ylabel("amplitude ratio A")
ax.set_title("Module dT change vs steady at matched Qbar=90 mL/min [%]")
for i in range(len(As)):
    for j in range(len(fs)):
        if not np.isnan(Z[i, j]):
            ax.text(j, i, f"{Z[i,j]:+.0f}", ha="center", va="center", fontsize=9)
fig.colorbar(im, ax=ax, label="dT_module change [%] (negative = more uniform)")
fig.tight_layout(); fig.savefig(REPO / "data/processed/sweep_dT_map.png", dpi=150)
print("wrote sweep_summary.csv + sweep_dT_map.png")
