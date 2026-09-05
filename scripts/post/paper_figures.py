#!/usr/bin/env python3
"""Journal figure set for the ATE manuscript (paper/figures/fig01..fig12 + graphical
abstract), PDF (vector) + PNG (600 dpi), Okabe-Ito categorical palette, single
hue sequential, RdBu diverging with neutral midpoint, 190 mm double-column width.
Run after data/processed is final.  Usage: paper_figures.py"""
import re
from pathlib import Path
import numpy as np, pandas as pd, yaml
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyArrowPatch, Polygon
from matplotlib.collections import PolyCollection

REPO = Path(__file__).resolve().parents[2]; OUT = REPO / "paper/figures"; OUT.mkdir(exist_ok=True)
D = REPO / "data/processed"; M = REPO / "cases/matrix"
C1, C2, C3, C4, C5 = "#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9"   # Okabe-Ito (validated)
MM = 1 / 25.4; W1, W2 = 90 * MM, 190 * MM
plt.rcParams.update({"font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8, "legend.fontsize": 7,
                     "xtick.labelsize": 7, "ytick.labelsize": 7, "axes.linewidth": 0.6, "lines.linewidth": 1.4,
                     "grid.alpha": 0.25, "grid.linewidth": 0.5, "font.family": "DejaVu Sans", "savefig.dpi": 600,
                     "axes.spines.top": False, "axes.spines.right": False, "figure.constrained_layout.use": True})
def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf"); fig.savefig(OUT / f"{name}.png"); plt.close(fig); print("wrote", name)

par = pd.read_csv(D / "pareto.csv").set_index("case"); ss = pd.read_csv(D / "sweep_summary.csv")
ts = pd.read_csv(D / "timeseries.csv"); base = par.loc["steady_f0.00_A0.00_Q2_C3"]
def series(lbl): return ts[ts["case"] == lbl].set_index("time").sort_index()

# ---------- fig01 geometry --------------------------------------------------------------
fig, axs = plt.subplots(1, 2, figsize=(W2, 62 * MM), gridspec_kw={"width_ratios": [1, 1.6]})
ax = axs[0]; ax.set_title("(a) validation rig: static immersion")
ax.add_patch(Rectangle((-60, -40), 120, 80, fc="#dbe9f6", ec="k", lw=1.2))
ax.add_patch(Rectangle((-65, -45), 130, 90, fill=False, ec="#7f7f7f", lw=3, alpha=.5))
for cx in (-22, 0, 22):
    for cy in (-11, 11): ax.add_patch(Circle((cx, cy), 9, fc="#f4a261", ec="k", lw=.7))
ax.text(0, -33, "6 × 18650, 3C discharge\nNovec-7200, 861 mL", ha="center", va="center", fontsize=6.5)
ax.text(0, -50, "acrylic 5 mm in a 22 °C water bath\n(U = 27 W m⁻² K⁻¹)", ha="center", fontsize=6.5, va="top")
ax.set_xlim(-75, 75); ax.set_ylim(-68, 52); ax.set_aspect("equal"); ax.axis("off")
ax = axs[1]; ax.set_title("(b) production duct, 180 × 46 × 72 mm")
ax.add_patch(Rectangle((-90, 0), 180, 72, fc="#dbe9f6", ec="k", lw=1.2))
for cx in (-22, 0, 22): ax.add_patch(Rectangle((cx - 9, 0), 18, 65, fc="#f4a261", ec="k", lw=.7))
ax.add_patch(FancyArrowPatch((-108, 36), (-92, 36), arrowstyle="-|>", mutation_scale=12, color=C1, lw=1.5))
ax.add_patch(FancyArrowPatch((92, 36), (108, 36), arrowstyle="-|>", mutation_scale=12, color=C1, lw=1.5))
ax.text(-100, 42, "inlet\nQ(t)", ha="center", fontsize=6.5, color=C1); ax.text(100, 42, "outlet\np = 0", ha="center", fontsize=6.5, color=C1)
ax.text(0, 74, "adiabatic walls", ha="center", fontsize=6.5, va="bottom"); ax.text(60, 30, "cells on floor,\n7 mm ceiling\nclearance", ha="center", fontsize=6.5)
ax.annotate("", xy=(-90, -6), xytext=(90, -6), arrowprops=dict(arrowstyle="<->", lw=.6)); ax.text(0, -12, "x ∈ [−90, 90] mm", ha="center", fontsize=6.5)
ax.set_xlim(-115, 115); ax.set_ylim(-18, 84); ax.set_aspect("equal"); ax.axis("off")
save(fig, "fig01_geometry")

# ---------- fig02 mesh (cutting planes from the surfaces sampler, if present) ----------
def read_vtk_polys(path):
    txt = Path(path).read_text()
    if "<VTKFile" in txt:   # XML vtp
        import xml.etree.ElementTree as ET
        r = ET.fromstring(txt); pts = np.fromstring(r.find(".//Points/DataArray").text, sep=" ").reshape(-1, 3)
        polys = r.find(".//Polys"); conn = np.fromstring(polys.find("DataArray[@Name='connectivity']").text, sep=" ").astype(int)
        offs = np.fromstring(polys.find("DataArray[@Name='offsets']").text, sep=" ").astype(int)
        faces = np.split(conn, offs[:-1]); return pts, faces
    m = re.search(r"POINTS\s+(\d+)\s+\w+\s*\n(.*?)\n(?=POLYGONS)", txt, re.S); n = int(m.group(1))
    pts = np.fromstring(m.group(2), sep=" ")[:3 * n].reshape(n, 3)
    m2 = re.search(r"POLYGONS\s+(\d+)\s+(\d+)\s*\n(.*?)(?=\n[A-Z]|\Z)", txt, re.S); arr = np.fromstring(m2.group(3), sep=" ").astype(int)
    faces, i = [], 0
    while i < len(arr): k = arr[i]; faces.append(arr[i + 1:i + 1 + k]); i += k + 1
    return pts, faces
cut = {k: next(iter((M / "fields_steady_f0.00_A0.00_Q2_C3/postProcessing").rglob(f"{k}*")), None) for k in ("zMid", "yRow")}
if all(cut.values()):
    fig, axs = plt.subplots(2, 1, figsize=(W2, 95 * MM), gridspec_kw={"height_ratios": [1, 1.6]})
    for ax, (k, path), (ix, iy, lab) in zip(axs, cut.items(), [(0, 1, "y"), (0, 2, "z")]):
        pts, faces = read_vtk_polys(path); polys = [pts[f][:, [ix, iy]] * 1e3 for f in faces]
        ax.add_collection(PolyCollection(polys, facecolor="none", edgecolor="0.25", linewidth=0.12))
        ax.set_xlim(-90, 90); ax.set_ylim(*((-23, 23) if k == "zMid" else (0, 72))); ax.set_aspect("equal")
        ax.set_xlabel("x [mm]"); ax.set_ylabel(f"{lab} [mm]")
    axs[0].set_title("(a) horizontal plane, z = 32.5 mm (cell mid-height)"); axs[1].set_title("(b) vertical plane through one cell row, y = 11 mm")
    save(fig, "fig02_mesh")
else: print("fig02: cutting planes not found — skipped")

# ---------- fig03 validation ------------------------------------------------------------
exp = pd.read_csv(REPO / "data/reference/liu_validation_curves.csv", comment="#")
runs = {"U = 27 W m⁻² K⁻¹ (accepted)": ("liu2023-static-u27", C1), "adiabatic walls": ("liu2023-static", C2), "k = 0.6 W m⁻¹ K⁻¹ (Liu effective)": ("liu2023-static-k06", C4)}
fig, ax = plt.subplots(figsize=(W1, 62 * MM))
ax.plot(exp.time_s, exp.T2_C, "o", ms=3.5, color="k", mfc="none", label="experiment, Liu et al. Fig. 9 (digitised)")
for lab, (case, col) in runs.items():
    pr = sorted((REPO / "cases/validation" / case).glob("postProcessing/T2probe/cell1/*/T"))
    if not pr: continue
    df = pd.read_csv(pr[-1], comment="#", sep=r"\s+", header=None); ax.plot(df[0], df.iloc[:, 1:5].mean(axis=1) - 273.15, "-", color=col, label=f"model, {lab}")
ax.set_xlabel("time [s]"); ax.set_ylabel("T2, mid-height cell surface [°C]"); ax.legend(loc="upper left"); ax.grid(True)
ax.text(0.98, 0.04, "3C discharge; accepted model MAE 5.7 %", transform=ax.transAxes, ha="right", va="bottom", fontsize=7)
save(fig, "fig03_validation")

# ---------- fig04 heat generation ---------------------------------------------------------
hg = yaml.safe_load((REPO / "data/reference/heatgen.yaml").read_text())["liu3c"]; a = hg["coefficients"]; t = np.linspace(0, hg["t_discharge"], 400)
q = sum(c * t**i for i, c in enumerate(a))
fig, ax = plt.subplots(figsize=(W1, 50 * MM)); ax.plot(t, q, color=C1); ax.set_xlabel("time from start of 3C discharge [s]"); ax.set_ylabel("heat generation per cell [W]")
ax.grid(True); ax.text(0.98, 0.05, f"Liu et al. 5th-order fit; mean {np.trapezoid(q, t)/t[-1]:.2f} W/cell,\n{6*np.trapezoid(q, t)/1e3:.1f} kJ per module discharge", transform=ax.transAxes, ha="right", va="bottom", fontsize=7)
save(fig, "fig04_heatgen")

# ---------- fig05 temporal resolution study ----------------------------------------------
seq = {"Euler, 2 outer correctors": ([0.0485, 0.025, 0.0125], ["steady_f0.00_A0.00_Q2_C3", "dtchk_dt0.0250_Q2", "dtchk_dt0.0125_Q2"], C2, "o"),
       "backward, 2 outer correctors": ([0.0394, 0.025, 0.0125], ["bwd_dt0.0500_Q2", "bwd_dt0.0250_Q2", "bwd_dt0.0125_Q2"], C1, "s"),
       "backward, 6 outer correctors": ([0.0394, 0.025], ["bwd_dt0.0500_nOC6_Q2", "bwd_dt0.0250_nOC6_Q2"], C3, "^"),
       "backward, 4 outer correctors": ([0.0394], ["bwd_dt0.0500_nOC4_Q2"], C4, "D")}
fig, ax = plt.subplots(figsize=(W1, 62 * MM))
for lab, (dts, cases, col, mk) in seq.items():
    pts = [(dt, par.loc[c].Tmax_C) for dt, c in zip(dts, cases) if c in par.index]
    ax.plot([p[0] * 1e3 for p in pts], [p[1] for p in pts], "-", marker=mk, ms=5, color=col, label=lab)
ax.set_xscale("log"); ax.invert_xaxis(); ax.set_xlabel("median time step [ms]"); ax.set_ylabel("T_max at t = 900 s [°C]"); ax.grid(True, which="major"); ax.legend(loc="lower left")
ax.set_xticks([50, 40, 30, 20, 12.5]); ax.set_xticklabels(["50", "40", "30", "20", "12.5"]); ax.minorticks_off(); ax.set_ylim(31.2, 32.1)
ax.axvline(12.5, color="0.6", ls="--", lw=.8); ax.text(13.2, 32.02, "production Δt", fontsize=6.5, color="0.4", ha="right")
save(fig, "fig05_dt_study")

# ---------- fig06 steady vs flow -------------------------------------------------------------
st = par[par.waveform == "steady"].sort_values("Qbar_mLmin")
fig, axs = plt.subplots(1, 3, figsize=(W2, 52 * MM))
for ax, y, lab in zip(axs, [st.Tmax_C, st.dT_module_K, st.Epump_model_J * 1e3], ["T_max at 900 s [°C]", "module ΔT [K]", "pump energy per discharge [mJ]"]):
    ax.plot(st.Qbar_mLmin, y, "o-", color=C1, ms=5); ax.set_xscale("log"); ax.set_xlabel("mean flow Q̄ [mL/min]"); ax.set_ylabel(lab); ax.grid(True, which="major")
    ax.set_xticks([50, 90, 130, 250, 500]); ax.set_xticklabels(["50", "90", "130", "250", "500"]); ax.minorticks_off()
axs[2].set_yscale("log"); axs[0].set_ylim(30.6, 32.4)
for ax, l in zip(axs, "abc"): ax.set_title(f"({l})", loc="left")
save(fig, "fig06_steady_vs_flow")

# ---------- fig07 T_max histories ------------------------------------------------------------
sel = [("td_steady_f0.00_A0.00_Q2_C3", "steady", "k", "-"), ("td_sine_f2.00_A0.60_Q2_C3", "sine 2 Hz, A = 0.6", C1, "-"),
       ("td_sine_f0.25_A0.60_Q2_C3", "sine 0.25 Hz, A = 0.6 (layer flush at 720 s)", C2, "-"), ("td_square_f1.00_D0.25_Q2_C3", "square 1 Hz, D = 0.25", C3, "-")]
fig, axs = plt.subplots(1, 2, figsize=(W2, 55 * MM))
for lbl, lab, col, ls in sel:
    s = series(lbl)
    if s.empty: continue
    axs[0].plot(s.index, s.Tmax_module - 273.15, ls, color=col, label=lab, lw=1.2); axs[1].plot(s.index, s.dT_module, ls, color=col, lw=1.2)
axs[0].set_ylabel("T_max [°C]"); axs[1].set_ylabel("module ΔT [K]")
for ax, l in zip(axs, "ab"): ax.set_xlabel("time [s]"); ax.grid(True); ax.set_title(f"({l})", loc="left")
axs[0].legend(loc="lower right"); save(fig, "fig07_histories")

# ---------- fig08 regime maps -------------------------------------------------------------------
FREQS, AMPS = sorted(ss.freq_hz.unique()), sorted(ss.amp.unique())
fig, axs = plt.subplots(1, 3, figsize=(W2, 62 * MM), gridspec_kw={"width_ratios": [1, 1, 1.25]})
for ax, col, ttl in zip(axs[:2], ["dT_rel_pct", "sigmaT_rel_pct"], ["(a) module ΔT change [%]", "(b) cell-to-cell σ_T change [%]"]):
    Mx = ss.pivot(index="amp", columns="freq_hz", values=col).loc[AMPS, FREQS]; v = 30
    im = ax.imshow(Mx.values, origin="lower", cmap="RdBu_r", vmin=-v, vmax=v, aspect="auto")
    ax.set_xticks(range(len(FREQS))); ax.set_xticklabels([f"{f:g}" for f in FREQS]); ax.set_yticks(range(len(AMPS))); ax.set_yticklabels([f"{a:g}" for a in AMPS])
    ax.set_xlabel("f [Hz]"); ax.set_ylabel("A"); ax.set_title(ttl, loc="left")
    for i in range(len(AMPS)):
        for j in range(len(FREQS)): ax.text(j, i, f"{Mx.iloc[i, j]:+.0f}", ha="center", va="center", fontsize=7, color="k")
fig.colorbar(im, ax=list(axs[:2]), shrink=0.85, pad=0.03, label="change vs steady [%]")
ax = axs[2]
for a_, col, mk in zip(AMPS, [C1, C2, C3], "osD"):
    d = ss[ss.amp == a_].sort_values("freq_hz"); ax.plot(d.freq_hz, d.Tmax_delta_K, "-", marker=mk, ms=4, color=col, label=f"A = {a_:g}")
ax.axhspan(-0.1, 0.1, color="0.9", zorder=0); ax.set_xscale("log"); ax.set_xlabel("f [Hz]"); ax.set_ylabel("T_max − T_max,steady [K]"); ax.grid(True, which="both"); ax.legend(loc="lower left")
ax.set_title("(c) peak-temperature shift", loc="left"); ax.annotate("layer flush\n(0.25 Hz, A 0.6)", (0.25, -0.61), xytext=(0.45, -0.45), fontsize=6, arrowprops=dict(arrowstyle="->", lw=.6))
save(fig, "fig08_regime_maps")

# ---------- fig09 pump energy ---------------------------------------------------------------------
sq = par[par.waveform == "square"].sort_values(["freq_hz", "duty"])
fig, axs = plt.subplots(1, 2, figsize=(W2, 60 * MM), gridspec_kw={"width_ratios": [1, 1.2]})
A = np.linspace(0, 0.7, 50); axs[0].plot(A, 1 + A**2 / 2, "-", color="k", label="model 1 + A²/2 (any f)")
sn = par[(par.waveform == "sine") & (par.freq_hz <= 1.0)]; axs[0].plot(sn.amp, sn.Epump_J / base.Epump_J, "o", mfc="none", color=C1, ms=5, label="integrated ∫Q·Δp dt, f ≤ 1 Hz")
sn2 = par[(par.waveform == "sine") & (par.freq_hz > 1.0)]; axs[0].plot(sn2.amp, sn2.Epump_J / base.Epump_J, "x", color=C2, ms=5, label="integrated, 2 Hz (inertia-aliased)")
axs[0].set_xlabel("amplitude ratio A"); axs[0].set_ylabel("E_pump / E_pump,steady"); axs[0].legend(loc="upper left"); axs[0].grid(True); axs[0].set_title("(a) sinusoidal", loc="left")
x = np.arange(len(sq)); axs[1].bar(x, sq.Epump_visc_J * 1e3, color=C1, label="viscous", width=.7)
axs[1].bar(x, sq.Epump_inert_J * 1e3, bottom=sq.Epump_visc_J * 1e3, color=C2, label="start/stop kinetic energy", width=.7)
axs[1].axhline(base.Epump_model_J * 1e3, color="k", ls="--", lw=.8, label="steady")
axs[1].set_xticks(x); axs[1].set_xticklabels([f"{r.freq_hz:g} Hz\nD = {r.duty:g}" for _, r in sq.iterrows()], fontsize=6.5)
axs[1].set_ylabel("E_pump per discharge [mJ]"); axs[1].legend(loc="upper left"); axs[1].grid(True, axis="y"); axs[1].set_title("(b) square-wave", loc="left")
for xi, (_, r) in zip(x, sq.iterrows()): axs[1].text(xi, r.Epump_model_J * 1e3 + 0.03, f"{r.Epump_model_J/base.Epump_model_J:.0f}×", ha="center", fontsize=6)
save(fig, "fig09_pump_energy")

# ---------- fig10 square-wave uniformity ---------------------------------------------------------
fig, axs = plt.subplots(1, 3, figsize=(W2, 56 * MM))
lab = [f"{r.duty:g}" for _, r in sq.iterrows()]
for ax, y, yl, l in zip(axs, [100 * (sq.dT_module_K / base.dT_module_K - 1), 100 * (sq.sigmaT_K / base.sigmaT_K - 1), sq.Tmax_C - base.Tmax_C],
                        ["module ΔT change [%]", "σ_T change [%]", "T_max − T_max,steady [K]"], "abc"):
    ax.bar(x, y, color=[C1 if r.freq_hz == 0.5 else C3 for _, r in sq.iterrows()], width=.7); ax.axhline(0, color="k", lw=.6)
    ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=7); ax.set_xlabel("duty ratio D"); ax.set_ylabel(yl); ax.grid(True, axis="y"); ax.set_title(f"({l})", loc="left")
    for xi, v in zip(x, y): ax.text(xi, v - (2 if v < 0 else -2) if l != "c" else v - 0.012, f"{v:+.0f}" if l != "c" else f"{v:+.2f}", ha="center", va="top", fontsize=6)
from matplotlib.patches import Patch
axs[0].legend(handles=[Patch(color=C1, label="0.5 Hz"), Patch(color=C3, label="1 Hz")], loc="upper right")
save(fig, "fig10_square")

# ---------- fig11 contours (reuse fields_fig5 machinery) -------------------------------------------
import importlib.util, sys
spec = importlib.util.spec_from_file_location("f5", REPO / "scripts/post/fields_fig5.py"); f5 = importlib.util.module_from_spec(spec); sys.argv = ["x"]; spec.loader.exec_module(f5)
sel5 = [p for p in f5.PANELS if (M / p[0] / str(p[1]) / "fluid/T").exists()]
if sel5:
    for plane, h in (("vertical", 2.0), ("horizontal", 1.55)):
        n = len(sel5); ncol = 3; nrow = int(np.ceil(n / ncol))
        fig, axs = plt.subplots(nrow, ncol, figsize=(W2, (26 if plane == "vertical" else 16) * MM * nrow + 6 * MM), squeeze=False); cf = None
        for k, (case, t_, title) in enumerate(sel5): cf = f5.panel(axs[k // ncol][k % ncol], case, t_, plane, title) or cf
        for k in range(n, nrow * ncol): axs[k // ncol][k % ncol].axis("off")
        if cf is not None: fig.colorbar(cf, ax=axs.ravel().tolist(), label="T [°C]", shrink=0.6, pad=0.01, aspect=30)
        save(fig, f"fig11_fields_{plane}")

# ---------- graphical abstract ---------------------------------------------------------------------------
fig = plt.figure(figsize=(13 * 2.54 * MM * 1.0 * 4, 5 * 2.54 * MM * 4))   # 13 x 5 cm at 4x for 2400x... px after dpi
fig = plt.figure(figsize=(133 * MM, 50 * MM))
gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.05, 0.95], wspace=0.3)
ax = fig.add_subplot(gs[0]); ax.add_patch(Rectangle((-90, 0), 180, 72, fc="#dbe9f6", ec="k", lw=1))
for cx in (-22, 0, 22): ax.add_patch(Rectangle((cx - 9, 0), 18, 65, fc="#f4a261", ec="k", lw=.6))
ax.add_patch(FancyArrowPatch((-112, 36), (-92, 36), arrowstyle="-|>", mutation_scale=10, color=C1, lw=1.4)); ax.text(-102, 44, "Q(t)", ha="center", fontsize=7, color=C1)
ax.set_xlim(-118, 100); ax.set_ylim(-8, 80); ax.set_aspect("equal"); ax.axis("off"); ax.set_title("6 × 18650 in dielectric duct\nsteady · sine · square", fontsize=7.5)
ax = fig.add_subplot(gs[1]); Mx = ss.pivot(index="amp", columns="freq_hz", values="dT_rel_pct").loc[AMPS, FREQS]
ax.imshow(Mx.values, origin="lower", cmap="RdBu_r", vmin=-30, vmax=30, aspect="auto"); ax.set_xticks(range(len(FREQS))); ax.set_xticklabels([f"{f:g}" for f in FREQS], fontsize=6); ax.set_yticks(range(len(AMPS))); ax.set_yticklabels([f"{a:g}" for a in AMPS], fontsize=6)
for i in range(len(AMPS)):
    for j in range(len(FREQS)): ax.text(j, i, f"{Mx.iloc[i, j]:+.0f}", ha="center", va="center", fontsize=6)
ax.set_xlabel("f [Hz]", fontsize=7); ax.set_ylabel("A", fontsize=7); ax.set_title("ΔT change vs steady [%]\nsine, matched mean flow", fontsize=7)
ax = fig.add_subplot(gs[2]); ax.axis("off")
ax.text(0, 0.98, "Buoyancy-dominated:\n1 K peak-T change\nover 10× flow;\nE_pump 0.03–3.8 mJ\nper discharge", va="top", fontsize=6.5)
ax.text(0, 0.55, "Intermittent flow:\nΔT −28 %, σ_T −35 %,\nT_max −0.2 K\nat 25× E_pump (1.8 mJ)", va="top", fontsize=6.5, color=C3)
ax.text(0, 0.18, "1st-order Δt ≈ 0.05 s fabricates\na spurious 0.1 Hz benefit", va="top", fontsize=6.5, color=C2)
fig.savefig(OUT / "graphical_abstract.png", dpi=460); fig.savefig(OUT / "graphical_abstract.pdf"); plt.close(fig); print("wrote graphical_abstract")
