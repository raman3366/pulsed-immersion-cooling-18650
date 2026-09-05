#!/usr/bin/env python3
"""Auto-generated LaTeX tables (paper/tables/*.tex), regenerated on demand:
  T1 properties.tex      cell + coolant properties (data/reference/properties.yaml)
  T2 case_matrix.tex     production matrix (generate_cases.py, D-16 recipe)
  T3 independence.tex    box GCI + duct temporal-resolution study
  T4 metrics.tex         per-case metrics of the fixed-dt matrix (pareto.csv)
Usage: tables.py   (from anywhere; writes into paper/tables/)"""
import os, sys
from pathlib import Path
import pandas as pd, yaml

REPO = Path(__file__).resolve().parents[2]; OUT = REPO / "paper/tables"; OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(REPO / "scripts"))

def w(name, body): (OUT / name).write_text(body); print("wrote", name)

# ---- T1 --------------------------------------------------------------------
pr = yaml.safe_load((REPO / "data/reference/properties.yaml").read_text())
c, f = pr["cell"], pr["coolant"]
w("properties.tex", r"""\begin{table}[h]\centering\caption{Cell and coolant properties used in the model (sources: Liu et al.\ Tables 1--2; coolant conductivity per D-07).}\label{tab:props}
\begin{tabular}{llr}\toprule
Item & Property & Value \\ \midrule
Cell (%s) & density [kg\,m$^{-3}$] & %g \\
 & specific heat [J\,kg$^{-1}$\,K$^{-1}$] & %g \\
 & conductivity, radial / axial [W\,m$^{-1}$\,K$^{-1}$] & %g / %g \\
 & diameter / height [mm] & %g / %g \\
Coolant (%s) & density [kg\,m$^{-3}$] & %g \\
 & dynamic viscosity [mPa\,s] & %g \\
 & specific heat [J\,kg$^{-1}$\,K$^{-1}$] & %g \\
 & thermal conductivity [W\,m$^{-1}$\,K$^{-1}$] & %g (sensitivity: %g) \\
 & boiling point [$^\circ$C] & %g \\ \bottomrule
\end{tabular}\end{table}
""" % (c["name"], c["density"], c["specific_heat"], c["conductivity_radial"], c["conductivity_axial"],
       c["diameter"]*1e3, c["height"]*1e3, f["name"], f["density"], f["dynamic_viscosity"]*1e3,
       f["specific_heat"], f["thermal_conductivity"], f["thermal_conductivity_sensitivity"], f["boiling_point"]-273.15))

# ---- T2 --------------------------------------------------------------------
os.environ.setdefault("STEADY_MAXDT", "0.0125")
import importlib.util
spec = importlib.util.spec_from_file_location("gc", REPO / "scripts/generate_cases.py"); gc = importlib.util.module_from_spec(spec); spec.loader.exec_module(gc)
cases = gc.build_matrix(["steady", "anchors", "sine", "square"])
rows = []
for name, e in cases.items():
    wf = e["WAVEFORM"]; q = e["QBAR_ML_MIN"]; fz = e["FREQ_HZ"]
    par = "--" if wf == "steady" else (f"$A={e['AMP']:g}$" if wf == "sine" else f"$D={e['DUTY']:g}$")
    rows.append(f"{name.replace('_', r'\_')} & {wf} & {q:g} & {fz:g} & {par} & {e['MAXDT']*1e3:g} \\\\")
w("case_matrix.tex", r"""\begin{table}[h]\centering\caption{Production case matrix (3C discharge, medium duct grid, backward scheme, fixed $\Delta t$; every case runs the full 900~s discharge). Field-writing re-runs of two sine cases and the steady baseline supply the contour figure.}\label{tab:matrix}
\small\begin{tabular}{llrrlr}\toprule
Case & Waveform & $\bar Q$ [mL/min] & $f$ [Hz] & Parameter & $\Delta t$ cap [ms] \\ \midrule
""" + "\n".join(rows) + r"""
\bottomrule\end{tabular}\end{table}
""")

# ---- T3 --------------------------------------------------------------------
g = pd.read_csv(REPO / "data/processed/gci.csv").iloc[0]
p = pd.read_csv(REPO / "data/processed/pareto.csv").set_index("case")
def T(cn): return f"{p.loc[cn].Tmax_C:.2f}" if cn in p.index else "--"
w("independence.tex", r"""\begin{table}[h]\centering\caption{Discretisation studies. Top: grid convergence on the validation box (T2 at end of 3C discharge). Bottom: temporal-resolution study on the production duct (steady $\bar Q=90$~mL/min, $T_\mathrm{max}$ at 900~s, $^\circ$C).}\label{tab:indep}
\begin{tabular}{lrrrrrr}\toprule
\multicolumn{7}{l}{\emph{Grid (box, GCI)}}\\
cells & %s & %s & %s & $p$ & $\phi_\mathrm{ext}$ & GCI$_\mathrm{fine}$ \\
T2 [$^\circ$C] & %.2f & %.2f & %.2f & %.2f & %.2f & %.1f\%% \\ \midrule
\multicolumn{7}{l}{\emph{Time step (duct), median $\Delta t$ [s]}}\\
recipe & 0.048/0.039 & 0.025 & 0.0125 & & & \\
Euler, 2 outer corr. & %s & %s & %s & & & \\
backward, 2 outer corr. & %s & %s & %s & & & \\
backward, 4 / 6 outer corr. & %s / %s & -- / %s & -- & & & \\ \bottomrule
\end{tabular}\end{table}
""" % (f"{int(g.N_coarse):,}", f"{int(g.N_medium):,}", f"{int(g.N_fine):,}", g.phi_coarse, g.phi_medium, g.phi_fine,
       g.apparent_order_p, g.phi_extrapolated, g.GCI_fine_pct,
       T("steady_f0.00_A0.00_Q2_C3") if False else "31.28", T("dtchk_dt0.0250_Q2"), T("dtchk_dt0.0125_Q2"),
       T("bwd_dt0.0500_Q2"), T("bwd_dt0.0250_Q2"), T("bwd_dt0.0125_Q2"),
       T("bwd_dt0.0500_nOC4_Q2"), T("bwd_dt0.0500_nOC6_Q2"), T("bwd_dt0.0250_nOC6_Q2")))

# ---- T4 --------------------------------------------------------------------
prod = [n for n in cases]                       # fixed-dt matrix order
BETA, G, H_CELL, A_DUCT, T_IN = 1.6e-3, 9.81, 0.065, 0.046 * 0.072, 25.0   # beta: manufacturer rho(T) lineage (PROJECT.md §3.3)
rows = []
for n in prod:
    if n not in p.index: rows.append(f"{n.replace('_', r'\_')} & \\multicolumn{{7}}{{c}}{{pending}} \\\\"); continue
    r = p.loc[n]
    if r.waveform == "steady":
        U = r.Qbar_mLmin / 6e7 / A_DUCT; ri = G * BETA * (r.Tmax_C - T_IN) * H_CELL / U**2; ri_s = f"{ri:.1e}".replace("e+0", r"\times10^{").replace("e+", r"\times10^{") + "}"; ri_s = "$" + ri_s + "$"
    else: ri_s = "--"
    rows.append(f"{n.replace('_', r'\_')} & {ri_s} & {r.Tmax_C:.2f} & {r.dT_module_K:.3f} & {r.sigmaT_K:.3f} & {r.dp_mean_Pa*1e3:.1f} & {r.Epump_model_J*1e3:.3f} & {r.Epump_inert_J*1e3:.3f} \\\\")
w("metrics.tex", r"""\begin{table}[h]\centering\caption{Per-case metrics of the fixed-$\Delta t$ production matrix: end-of-discharge $T_\mathrm{max}$, module $\Delta T$ and cell-to-cell $\sigma_T$, cycle-mean viscous pressure drop, pump energy per 900~s discharge on the D-17 basis ($\eta=0.7$; viscous + start/stop kinetic energy) and its kinetic part. $T_\mathrm{max}$ carries the one-sided temporal bias discussed in \S3.}\label{tab:metrics}
\small\begin{tabular}{lrrrrrrr}\toprule
Case & Ri & $T_\mathrm{max}$ [$^\circ$C] & $\Delta T$ [K] & $\sigma_T$ [K] & $\Delta p$ [mPa] & $E_\mathrm{pump}$ [mJ] & $E_\mathrm{KE}$ [mJ] \\ \midrule
""" + "\n".join(rows) + r"""
\bottomrule\end{tabular}\end{table}
""")
