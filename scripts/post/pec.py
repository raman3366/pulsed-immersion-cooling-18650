#!/usr/bin/env python3
"""Pump-energy / Pareto metrics (§3.7): dp, P_pump = Q·dp/eta, E_pump,
paired with T_max and dT from the §9 timeseries.

Usage: pec.py <case-dir> [case-dir ...]
Appends/updates one row per case in data/processed/pareto.csv.
eta = 0.7 (stated + sensitivity-tested in the paper, §3.7).
Averaging: steady -> last half of the run; pulsed -> last 3 full periods
(start-up discarded per §4.4). Cycle metrics use the same window.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

REPO = Path(__file__).resolve().parents[2]
ETA = 0.7
RHO_IN = 1430.0                     # inlet fixed at 25 C


def dp_over_q(matrix_dir, qbar):
    """laminar dp/Q from the steady case at the same Qbar (pareto.csv), else None."""
    f = REPO / "data/processed/pareto.csv"
    if not f.exists(): return None
    d = pd.read_csv(f); d = d[(d.waveform == "steady") & (abs(d.Qbar_mLmin - qbar * 6e7) < 0.5)]
    d = d[d.case.str.startswith("steady_")]
    return float(d.dp_mean_Pa.iloc[0] / qbar) if len(d) else None


def dat(case, sub):
    """All postProcessing time-segments of a monitor, concatenated in numeric
    order; a later (resumed) segment overrides the overlap of an earlier one."""
    hits = sorted((case / "postProcessing/fluid" / sub).glob("*/surfaceFieldValue.dat"),
                  key=lambda h: float(h.parent.name))
    out = None
    for h in hits:
        df = pd.read_csv(h, comment="#", sep=r"\s+", header=None)
        out = df if out is None else pd.concat(
            [out[out[0] < df[0].iloc[0]], df], ignore_index=True)
    return out


rows = []
for cd in sys.argv[1:]:
    case = Path(cd).resolve()
    cm = yaml.safe_load((case / "system/caseMeta.yaml").read_text())
    pin = dat(case, "areaAverage_inlet")     # [t, p, T]
    pout = dat(case, "areaAverage_outlet")
    phi = dat(case, "sum_inlet")             # [t, sum(phi)]
    n = min(len(pin), len(pout), len(phi))
    t = pin[0].to_numpy()[:n]
    dp = (pin[1].to_numpy() - pout[1].to_numpy())[:n]
    q = np.abs(phi[1].to_numpy())[:n] / RHO_IN          # m3/s
    if cm["waveform"] == "steady":
        win = t >= t[-1] / 2
    else:
        win = t >= t[-1] - 3.0 / cm["freq_hz"]
    p_pump = q * dp / ETA
    e_pump = float(np.trapezoid(p_pump, t))             # whole discharge [J] — MEASURED
    # ---- model decomposition (2026-09-04): the measured integral aliases the
    # inertial pressure rho*L*dU/dt (tens of Pa per step for a square wave vs
    # 0.04 Pa viscous) at the 0.125 s monitor cadence -> negative/garbage E for
    # square waves and +0.2-0.3x spurious at 2 Hz sine. Honest accounting:
    #   E_visc   = k_lam * Int q^2 dt / eta, k_lam = dp/Qbar of the STEADY case at
    #              the same Qbar (laminar dp ~ k Q); sine: <q^2>/<q>^2 = 1+A^2/2
    #   E_inert  = (square only) N_on * 1/2 rho V_duct U_on^2 / eta: kinetic energy
    #              injected at each ON step and dissipated at each OFF step
    #              (sine: inertial work is reversible over a cycle -> 0)
    V_DUCT = 0.180 * 0.046 * 0.072 - 6 * np.pi * 0.009**2 * 0.065   # D-10 duct minus cells [m3]
    A_DUCT = 0.046 * 0.072
    qbar = cm["qbar_m3s"]; T_END = float(t[-1])
    k_lam = dp_over_q(case.parent, qbar) or float(np.mean(dp[win]) / qbar)
    if cm["waveform"] == "steady":   q2_ratio = 1.0
    elif cm["waveform"] == "sine":   q2_ratio = 1.0 + cm["amp"]**2 / 2
    else:                            q2_ratio = 1.0 / cm["duty"]
    e_visc = k_lam * qbar**2 * q2_ratio * T_END / ETA
    e_inert = 0.0
    if cm["waveform"] == "square":
        u_on = qbar / cm["duty"] / A_DUCT
        e_inert = cm["freq_hz"] * T_END * 0.5 * RHO_IN * V_DUCT * u_on**2 / ETA
    e_model = e_visc + e_inert
    # temperatures from the committed timeseries (extract_metrics must have run)
    ts = pd.read_csv(REPO / "data/processed/timeseries.csv")
    for lbl in (f"td_{case.name}", case.name):
        sel = ts[ts["case"] == lbl]
        if len(sel):
            ts = sel
            break
    assert len(ts), f"run extract_metrics first for {case.name}"
    rows.append({
        "case": case.name, "waveform": cm["waveform"],
        "Qbar_mLmin": round(cm["qbar_m3s"] * 6e7, 2),
        "freq_hz": cm["freq_hz"], "amp": cm["amp"], "duty": cm["duty"],
        "dp_mean_Pa": round(float(np.mean(dp[win])), 4),
        "Ppump_mean_W": round(float(np.mean(p_pump[win])), 8),
        "Epump_J": round(e_pump, 6),             # measured Int q*dp/eta dt (aliases inertia)
        "Epump_visc_J": round(e_visc, 7),        # laminar viscous work
        "Epump_inert_J": round(e_inert, 7),      # start/stop kinetic energy (square only)
        "Epump_model_J": round(e_model, 7),      # = visc + inert  (proposed primary basis)
        "Tmax_C": round(float(ts["Tmax_module"].iloc[-1]) - 273.15, 3),
        "dT_module_K": round(float(ts["dT_module"].iloc[-1]), 3),
        "sigmaT_K": round(float(ts["sigmaT_module"].iloc[-1]), 3),
    })
    print(f"{case.name}: dp={rows[-1]['dp_mean_Pa']} Pa  "
          f"E_meas={e_pump*1e3:.3f} mJ  E_model={e_model*1e3:.3f} mJ (visc {e_visc*1e3:.3f} + inert {e_inert*1e3:.3f})  "
          f"Tmax={rows[-1]['Tmax_C']} C  dT={rows[-1]['dT_module_K']} K")

out = REPO / "data/processed/pareto.csv"
old = pd.read_csv(out) if out.exists() else pd.DataFrame()
if not old.empty:
    old = old[~old["case"].isin([r["case"] for r in rows])]
pd.concat([old, pd.DataFrame(rows)]).to_csv(out, index=False)
print(f"wrote {out.relative_to(REPO)}")
