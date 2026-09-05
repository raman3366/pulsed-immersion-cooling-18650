#!/usr/bin/env python3
"""Paper figures from data/processed (D-12 framing). Writes paper/figures/*.png.

  fig_regime_dT.png      f x A map of module dT change vs steady (uniformity)
  fig_regime_sigmaT.png  f x A map of sigma_T change vs steady
  fig_regime_epump.png   f x A map of E_pump relative to steady
  fig_tmax_vs_f.png      T_max shift vs f, coloured by A  (OPEN dt FLAG —
                         annotated; do not use in the manuscript until the
                         duct time-step check clears; see PROJECT.md changelog 2026-09-01)
  fig_baseline_vs_Q.png  steady T_max, dT, E_pump vs mean flow (D-12 energy-
                         honesty finding)
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "paper/figures"; OUT.mkdir(parents=True, exist_ok=True)
ss = pd.read_csv(REPO / "data/processed/sweep_summary.csv")
par = pd.read_csv(REPO / "data/processed/pareto.csv")
FREQS = sorted(ss.freq_hz.unique()); AMPS = sorted(ss.amp.unique())


def heat(col, title, cbar, fname, fmt="{:+.0f}", cmap="RdBu_r", center=True):
    M = ss.pivot(index="amp", columns="freq_hz", values=col).loc[AMPS, FREQS]
    v = np.nanmax(np.abs(M.values - (0 if center else 1)))
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    im = ax.imshow(M.values, origin="lower", cmap=cmap, aspect="auto",
                   vmin=(-v if center else 1 - v), vmax=(v if center else 1 + v))
    ax.set_xticks(range(len(FREQS))); ax.set_xticklabels([f"{f:g}" for f in FREQS])
    ax.set_yticks(range(len(AMPS))); ax.set_yticklabels([f"{a:g}" for a in AMPS])
    ax.set_xlabel("pulsation frequency f [Hz]"); ax.set_ylabel("amplitude ratio A")
    for i, a in enumerate(AMPS):
        for j, f in enumerate(FREQS):
            ax.text(j, i, fmt.format(M.iloc[i, j]), ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, label=cbar); ax.set_title(title, fontsize=10)
    fig.tight_layout(); fig.savefig(OUT / fname, dpi=200); plt.close(fig)


heat("dT_rel_pct", "Module ΔT change vs steady, Q̄ = 90 mL/min, 3C, fixed Δt",
     "ΔT change [%]", "fig_regime_dT.png")
heat("sigmaT_rel_pct", "Cell-to-cell σ_T change vs steady, Q̄ = 90 mL/min, 3C, fixed Δt",
     "σ_T change [%]", "fig_regime_sigmaT.png")
# pump energy (D-17 basis): sine = analytic 1+A^2/2 with measured points where
# trustworthy (f <= 1 Hz); square = stacked viscous + start/stop KE bars
sq = par[par.waveform == "square"].sort_values(["freq_hz", "duty"])
b = par.loc[par.case == "steady_f0.00_A0.00_Q2_C3"].iloc[-1]
fig, axs = plt.subplots(1, 2, figsize=(8.4, 3.2), gridspec_kw={"width_ratios": [1, 1.2]})
A = np.linspace(0, 0.7, 50); axs[0].plot(A, 1 + A**2 / 2, "k-", label="model $1+A^2/2$ (any $f$)")
sn = par[(par.waveform == "sine") & (par.freq_hz <= 1.0)]
axs[0].plot(sn.amp, sn.Epump_J / b.Epump_J, "o", mfc="none", color="tab:blue", label="measured ∫Q·Δp dt, f ≤ 1 Hz")
sn2 = par[(par.waveform == "sine") & (par.freq_hz > 1.0)]
axs[0].plot(sn2.amp, sn2.Epump_J / b.Epump_J, "x", color="tab:red", label="measured, 2 Hz (inertia-aliased)")
axs[0].set_xlabel("amplitude ratio A"); axs[0].set_ylabel("$E_{pump}/E_{pump,steady}$"); axs[0].legend(fontsize=7); axs[0].grid(alpha=.3)
axs[0].set_title("Sinusoidal pulsation", fontsize=9)
lbl = [f"{r.freq_hz:g} Hz\nD={r.duty:g}" for _, r in sq.iterrows()]
x = np.arange(len(sq))
axs[1].bar(x, sq.Epump_visc_J * 1e3, color="tab:blue", label="viscous")
axs[1].bar(x, sq.Epump_inert_J * 1e3, bottom=sq.Epump_visc_J * 1e3, color="tab:orange", label="start/stop KE")
axs[1].axhline(b.Epump_model_J * 1e3, color="k", ls="--", lw=1, label="steady")
axs[1].set_xticks(x); axs[1].set_xticklabels(lbl, fontsize=7); axs[1].set_ylabel("$E_{pump}$ per discharge [mJ]")
axs[1].legend(fontsize=7); axs[1].grid(alpha=.3, axis="y"); axs[1].set_title("Square-wave (intermittent) flow", fontsize=9)
fig.tight_layout(); fig.savefig(OUT / "fig_regime_epump.png", dpi=200); plt.close(fig)

# T_max vs f — flagged
fig, ax = plt.subplots(figsize=(5.2, 3.4))
for a in AMPS:
    d = ss[ss.amp == a].sort_values("freq_hz")
    ax.plot(d.freq_hz, d.Tmax_delta_K, "o-", label=f"A = {a:g}")
ax.set_xscale("log"); ax.set_xlabel("f [Hz]"); ax.set_ylabel("T_max − T_max,steady [K]")
ax.legend(fontsize=8); ax.grid(alpha=.3)
ax.axhspan(-0.1, 0.1, color="0.9", zorder=0)
ax.set_title("T_max shift vs frequency at matched numerics (fixed Δt = 12.5 ms);\n"
             "grey band ±0.1 K; 0.25 Hz A0.6 = buoyant-layer flush event at t≈720 s", fontsize=8)
fig.tight_layout(); fig.savefig(OUT / "fig_tmax_vs_f.png", dpi=200); plt.close(fig)

# baselines vs Q
st = par[par.waveform == "steady"].sort_values("Qbar_mLmin")
fig, axs = plt.subplots(1, 3, figsize=(9, 2.9))
axs[0].plot(st.Qbar_mLmin, st.Tmax_C, "ko-"); axs[0].set_ylabel("T_max [°C]")
axs[1].plot(st.Qbar_mLmin, st.dT_module_K, "ko-"); axs[1].set_ylabel("module ΔT [K]")
axs[2].plot(st.Qbar_mLmin, st.Epump_model_J * 1e3, "ko-"); axs[2].set_ylabel("E_pump per discharge [mJ]")
for ax in axs:
    ax.set_xlabel("Q̄ [mL/min]"); ax.set_xscale("log"); ax.grid(alpha=.3, which="both")
axs[0].set_ylim(st.Tmax_C.min() - 0.5, st.Tmax_C.max() + 0.5); axs[2].set_yscale("log")
fig.suptitle("Steady flow, 3C discharge, fixed Δt: T_max falls only 1 K over 50→500 mL/min; pump energy stays in the mJ range", fontsize=8)
fig.tight_layout(); fig.savefig(OUT / "fig_baseline_vs_Q.png", dpi=200); plt.close(fig)
print("wrote", sorted(p.name for p in OUT.glob("fig_*.png")))


# --- temporal-resolution study (final data, 2026-09-02): Tmax vs dt ---------
tp = pd.read_csv(REPO / "data/processed/pareto.csv").set_index("case")
seq = {
    "Euler, 2 outer corr.": [(0.0485, "steady_f0.00_A0.00_Q2_C3"), (0.025, "dtchk_dt0.0250_Q2"), (0.0125, "dtchk_dt0.0125_Q2")],
    "backward, 2 outer corr.": [(0.0394, "bwd_dt0.0500_Q2"), (0.025, "bwd_dt0.0250_Q2"), (0.0125, "bwd_dt0.0125_Q2")],
    "backward, 6 outer corr.": [(0.0394, "bwd_dt0.0500_nOC6_Q2"), (0.025, "bwd_dt0.0250_nOC6_Q2")],
    "backward, 4 outer corr.": [(0.0394, "bwd_dt0.0500_nOC4_Q2")],
}
fig, ax = plt.subplots(figsize=(5.2, 3.6))
for lbl, pts in seq.items():
    d = [(dt, tp.loc[c].Tmax_C) for dt, c in pts if c in tp.index]
    ax.plot([x[0] for x in d], [x[1] for x in d], "o-", label=lbl)
ax.set_xscale("log"); ax.invert_xaxis()
ax.set_xlabel("median solver time step [s]"); ax.set_ylabel("T_max at t = 900 s [°C]")
ax.grid(alpha=.3); ax.legend(fontsize=7, loc="upper left")
ax.set_title("Temporal-resolution study, steady Q2 (medium duct grid)", fontsize=9)
fig.tight_layout(); fig.savefig(OUT / "fig_dt_study.png", dpi=200); plt.close(fig)
print("wrote fig_dt_study.png")
