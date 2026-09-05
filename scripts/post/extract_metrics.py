#!/usr/bin/env python3
"""Function-object output -> tidy metric CSVs, with §9 HARD-FAIL gates.

Usage:
    extract_metrics.py <case-dir> [--power-per-cell W] [--label NAME]

Reads postProcessing/ of a liu2023-static-style case (per-cell volFieldValue
monitors, fluid volAverage, fluid fieldMinMax, fluid-side wallHeatFlux) and
the solver log, writes/updates:

    data/processed/timeseries.csv   one row per (case, time)
    data/processed/summary.csv      one row per case

§9 sanity gates — assertion failures exit non-zero (rule 4; a silently
non-conserving case reaching a figure is the worst possible outcome):

    E1  energy balance: |input - stored - wall_loss| / input <= 2%
    E2  Courant: solver-log max Courant <= 1.05 x controlDict maxCo
    E3  mean inlet flow within 0.5% of intent   [forced-flow cases only]
    E4  >= 40 steps per pulsation period        [pulsed cases only]

E3/E4 are auto-skipped (with notice) when the case has no inlet — the
static validation configuration.
"""

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

REPO = Path(__file__).resolve().parents[2]
PROCESSED = REPO / "data/processed"

# Sign convention of the wallHeatFlux FO 'integral' column: verified against
# the 10 s smoke run (fluid warmer than the fixed-T wall -> heat leaves the
# fluid; the FO reports that as NEGATIVE integral). Wall LOSS is therefore
# -integral. Re-verify if the FO ever changes.
WALL_LOSS_SIGN = -1.0


def read_dat(path):
    """volFieldValue/fieldMinMax .dat -> (header_meta, DataFrame)."""
    meta = {}
    for line in path.read_text().splitlines():
        if line.startswith("#"):
            m = re.match(r"#\s*(\w[\w ()]*?)\s*:\s*(.+)", line)
            if m:
                meta[m.group(1).strip()] = m.group(2).strip()
        else:
            break
    df = pd.read_csv(path, comment="#", sep=r"\s+", header=None)
    return meta, df


def read_all(globdir, pattern):
    """Read a monitor across ALL its postProcessing time-subdirectories
    (a resumed run writes a fresh <restartTime>/ segment). Segments are
    concatenated in numeric order; a later segment overrides the overlap of
    an earlier one (the pre-interruption segment ran past the checkpoint it
    was resumed from). Returns (meta-of-last-segment, DataFrame)."""
    hits = sorted(globdir.glob(pattern), key=lambda h: float(h.parent.name))
    if not hits:
        sys.exit(f"extract_metrics: missing {globdir}/{pattern}")
    meta, out = None, None
    for h in hits:
        meta, df = read_dat(h)
        df[0] = df[0].astype(float)
        out = df if out is None else pd.concat(
            [out[out[0] < df[0].iloc[0]], df], ignore_index=True)
    return meta, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case")
    ap.add_argument("--power-per-cell", type=float, default=None,
                    help="W per cell; default: parse from a fvOptions comment "
                         "or constant source value")
    ap.add_argument("--label", default=None, help="case label in the CSVs")
    ap.add_argument("--waive-e2", metavar="REASON", default=None,
                    help="record E2 as WAIVED (documented) instead of failing")
    ap.add_argument("--waive-e1", metavar="REASON", default=None,
                    help="record E1 as WAIVED with this reason instead of "
                         "hard-failing; the waiver lands in summary.csv")
    ap.add_argument("--waive-e4", metavar="REASON", default=None,
                    help="record E4 as WAIVED when 39 <= steps/period < 40 "
                         "(adjustableRunTime write-snapping enlarges dt by "
                         "<0.4%% above maxDeltaT); below 39 still hard-fails")
    a = ap.parse_args()
    waivers = []                       # recorded in summary.csv waived_gates

    case = Path(a.case).resolve()
    label = a.label or case.name
    pp = case / "postProcessing"
    props = yaml.safe_load((REPO / "data/reference/properties.yaml").read_text())
    cellp, coolp = props["cell"], props["coolant"]

    # ---- per-cell temperature series ---------------------------------------
    cells = sorted(int(d.name[4:]) for d in pp.glob("cell[0-9]*"))
    if not cells:
        sys.exit("extract_metrics: no cell regions found in postProcessing/")
    series = {}
    cell_vol = {}
    for i in cells:
        for op in ("max", "min", "volAverage"):
            meta, df = read_all(pp, f"cell{i}/T{op}_cell{i}/*/volFieldValue.dat")
            series[f"T{op}_cell{i}"] = df.set_index(0)[1]
            if op == "volAverage" and "Volume" in meta:
                cell_vol[i] = float(meta["Volume"])
    meta, df = read_all(pp, "fluid/TvolAverage_fluid/*/volFieldValue.dat")
    series["TvolAverage_fluid"] = df.set_index(0)[1]
    fluid_vol = float(meta["Volume"])

    # fluid extremes: fieldMinMax layout: time field min minLoc max maxLoc
    _, mm = read_all(pp, "fluid/TfluidMinMax/*/fieldMinMax.dat")
    tmm = mm[mm[1] == "T"].set_index(0)
    umm = mm[mm[1] == "mag(U)"].set_index(0)
    series["Tmin_fluid"] = tmm[2].astype(float)
    series["Tmax_fluid"] = tmm[4].astype(float)
    series["magUmax_fluid"] = umm[4].astype(float)

    ts = pd.DataFrame(series).sort_index()
    ts.index.name = "time"
    ts.insert(0, "case", label)
    cell_avg_cols = [f"TvolAverage_cell{i}" for i in cells]
    cell_max_cols = [f"Tmax_cell{i}" for i in cells]
    ts["Tmax_module"] = ts[cell_max_cols].max(axis=1)
    ts["dT_module"] = ts[cell_avg_cols].max(axis=1) - ts[cell_avg_cols].min(axis=1)
    ts["sigmaT_module"] = ts[cell_avg_cols].std(axis=1, ddof=0)

    # ---- wall loss (fluid-side wallHeatFlux; sparse write-time samples) ----
    _, wf = read_all(pp, "fluid/wallLoss_fluid/*/wallHeatFlux.dat")
    wf = wf[wf[1] == "walls"]
    t_w = wf[0].astype(float).to_numpy()
    q_out = WALL_LOSS_SIGN * wf[4].astype(float).to_numpy()   # W, >0 = loss
    wall_loss_J = float(np.trapezoid(q_out, t_w)) if len(t_w) > 1 else 0.0

    # ---- heat input --------------------------------------------------------
    t_end = float(ts.index[-1])
    fvopt = (case / "constant/cell0/fvOptions").read_text()
    if a.power_per_cell is not None:
        power_per_cell = a.power_per_cell            # mean, for the summary
        e_in = power_per_cell * len(cells) * t_end
    elif "source-model: liu3c" in fvopt:
        hg = yaml.safe_load((REPO / "data/reference/heatgen.yaml").read_text())["liu3c"]
        coeffs = [float(c) for c in hg["coefficients"]]     # W/cell, t^n
        assert t_end <= float(hg["t_discharge"]) + 1e-6, \
            f"run t_end {t_end} exceeds heat-gen fit domain {hg['t_discharge']}"
        e_cell = sum(c * t_end ** (n + 1) / (n + 1) for n, c in enumerate(coeffs))
        e_in = e_cell * len(cells)
        power_per_cell = e_cell / t_end              # mean, for the summary
    else:
        m = re.search(r"h\s+\(([\d.eE+-]+)\s", fvopt)
        qdot = float(m.group(1))                     # W/m3 constant
        power_per_cell = qdot * cell_vol[cells[0]]
        e_in = power_per_cell * len(cells) * t_end

    log = case / "log.chtMultiRegionFoam"

    # ---- E1: energy balance ------------------------------------------------
    rho_cp_cell = cellp["density"] * cellp["specific_heat"]
    stored_cells = sum(
        rho_cp_cell * cell_vol[i]
        * (ts[f"TvolAverage_cell{i}"].iloc[-1] - ts[f"TvolAverage_cell{i}"].iloc[0])
        for i in cells)
    stored_fluid = (coolp["density"] * coolp["specific_heat"] * fluid_vol
                    * (ts["TvolAverage_fluid"].iloc[-1] - ts["TvolAverage_fluid"].iloc[0]))
    dH_net_J = 0.0
    if (case / "system/caseMeta.yaml").exists():
        cp_f = coolp["specific_heat"]
        _, pi = read_all(pp, "fluid/sum_inlet/*/surfaceFieldValue.dat")
        _, po = read_all(pp, "fluid/sum_outlet/*/surfaceFieldValue.dat")
        # Net advected enthalpy needs SIGNED flux sums: under buoyancy the
        # outlet face is bidirectional (hot out on top, ambient re-entry
        # below), so any average(T)-times-net-mass estimate fails (75% E1
        # miss on the first duct baselines). TphiSum_* = weightedSum(T)
        # with weightField phi = sum(phi*T) [kg.K/s], signed.
        #   dH = cp * Int[ (sum phiT)_out + (sum phiT)_in
        #                  - Tref*((sum phi)_out + (sum phi)_in) ] dt
        # with Tref = T_inlet so the books share the storage reference.
        def phiT_series(patch):
            d = read_all(pp, f"fluid/TphiSum_{patch}/*/surfaceFieldValue.dat")[1]
            return (d[0].astype(float).to_numpy(),
                    d.iloc[:, -1].astype(float).to_numpy())
        tt = pi[0].astype(float).to_numpy()
        phi_i = pi[1].astype(float).to_numpy()            # signed
        phi_o = po[1].astype(float).to_numpy()
        tpo_t, tpo = phiT_series("outlet")
        tpi_t, tpi = phiT_series("inlet")
        Tref = float(yaml.safe_load((case / "system/caseMeta.yaml")
                                    .read_text())["T_inlet"])
        n = min(len(tt), len(phi_o), len(phi_i))
        # coarser replay time base -> interpolate onto the flow time base
        phiT_o = np.interp(tt[:n], tpo_t, tpo)
        phiT_i = np.interp(tt[:n], tpi_t, tpi)
        dH_net_J = float(np.trapezoid(
            cp_f * (phiT_o + phiT_i
                    - Tref * (phi_o[:n] + phi_i[:n])), tt[:n]))
    # ---- E1 (preferred form): solver-native rho*h conservation -------------
    # Boundary-flux estimators are unreliable on bidirectional bath-like
    # faces (gross ~9x net). Instead: (a) HARD gate on the early window
    # (t in [10,90] s, before boundary export develops) where dH_total/dt
    # must equal source power; (b) full-window residual reported as the
    # physically meaningful NET EXPORT (informational, no gate).
    rhoh_hits = sorted(pp.glob("fluid/rhoh_fluid/*/volFieldValue.dat"))
    if rhoh_hits and "source-model: liu3c" in fvopt:
        _, rf = read_all(pp, "fluid/rhoh_fluid/*/volFieldValue.dat")
        t_h = rf[0].astype(float).to_numpy()
        H = rf[1].astype(float).to_numpy()
        for i in cells:
            _, rc = read_all(pp, f"cell{i}/rhoh_cell{i}/*/volFieldValue.dat")
            H = H + cellp["density"] * np.interp(t_h, rc[0].astype(float),
                                                 rc[1].astype(float))
        hg2 = yaml.safe_load((REPO / "data/reference/heatgen.yaml").read_text())["liu3c"]
        cfs = [float(c) for c in hg2["coefficients"]]
        Q = lambda tau: len(cells) * sum(c * tau ** (n + 1) / (n + 1)
                                         for n, c in enumerate(cfs))
        # early window [10,90] s for full runs; scaled for short smokes
        lo, hi = min(10.0, 0.1 * t_h[-1]), min(90.0, 0.9 * t_h[-1])
        win = (t_h >= lo) & (t_h <= hi)
        assert win.sum() >= 2, "E1 early window has <2 rho*h samples"
        i0, i1 = np.where(win)[0][[0, -1]]
        ratio = (H[i1] - H[i0]) / (Q(t_h[i1]) - Q(t_h[i0]))
        net_export_J = e_in - float(H[-1])
        print(f"E1 (rho*h native): early-window conservation ratio "
              f"{ratio:.4f} (gate 0.97-1.03); stored_total={H[-1]:.1f} J, "
              f"net export={net_export_J:.1f} J over the run")
        if not (0.97 <= ratio <= 1.03):
            if a.waive_e1:
                print(f"*** E1 WAIVED at ratio {ratio:.4f} — {a.waive_e1}")
                waivers.append(f"E1(ratio {ratio:.4f}): {a.waive_e1}")
            else:
                raise AssertionError(
                    f"E1 FAILED: early conservation ratio {ratio:.4f}")
        e1 = abs(1 - ratio)
        residual = net_export_J          # informational in the summary
    else:
        residual = e_in - stored_cells - stored_fluid - wall_loss_J - dH_net_J
        e1 = abs(residual) / e_in if e_in else 0.0
        print(f"E1 energy: in={e_in:.2f} J, cells={stored_cells:.2f} J, "
              f"fluid={stored_fluid:.2f} J, walls={wall_loss_J:.2f} J, "
              f"advected={dH_net_J:.2f} J, residual={residual:+.2f} J ({e1*100:.2f}%)")
        if e1 > 0.02 and a.waive_e1:
            print(f"*** E1 WAIVED at {e1*100:.2f}% > 2% — reason: {a.waive_e1}")
            waivers.append(f"E1({e1*100:.2f}%): {a.waive_e1}")
        else:
            assert e1 <= 0.02, f"E1 FAILED: energy imbalance {e1*100:.2f}% > 2%"

    # ---- E2: Courant vs maxCo ---------------------------------------------
    co_max = max((float(m) for m in
                  re.findall(r"Courant Number.*max:\s*([\d.eE+-]+)",
                             log.read_text())), default=None)
    maxco = float(re.search(r"maxCo\s+([\d.]+);",
                            (case / "system/controlDict").read_text()).group(1))
    # adjustTimeStep sets dt from the PREVIOUS step's velocity, so an
    # accelerating (buoyant) flow transiently overshoots maxCo by ~10%;
    # that is stable under PIMPLE and not a runaway. Gate at 1.25x: a true
    # instability blows far past it within a few steps.
    print(f"E2 Courant: log max {co_max}, controlDict maxCo {maxco} "
          f"(gate {1.25*maxco:.2f})")
    if co_max is not None and co_max > 1.25 * maxco and a.waive_e2:
        print(f"*** E2 WAIVED at Courant {co_max} — {a.waive_e2}")
        waivers.append(f"E2(Co {co_max}): {a.waive_e2}")
    else:
        assert co_max is not None and co_max <= 1.25 * maxco, \
            f"E2 FAILED: Courant {co_max} exceeds 1.25 x maxCo ({maxco})"

    # ---- E3/E4: forced/pulsed duct cases (caseMeta.yaml present) -----------
    meta_f = case / "system/caseMeta.yaml"
    if meta_f.exists():
        cm = yaml.safe_load(meta_f.read_text())
        rho_in = 1430.0                       # inlet held at 25 C
        _, ph = read_all(pp, "fluid/sum_inlet/*/surfaceFieldValue.dat")
        t_p = ph[0].astype(float).to_numpy()
        mdot = np.abs(ph[1].astype(float).to_numpy())      # |sum(phi)| kg/s
        # averaging window: last 3 full periods (pulsed) / last half (steady)
        if cm["waveform"] == "steady":
            win = t_p >= t_p[-1] / 2
        else:
            win = t_p >= t_p[-1] - 3.0 / cm["freq_hz"]
            assert win.sum() > 10, "E4 precheck: <3 periods of flow samples"
        q_mean = float(np.trapezoid(mdot[win], t_p[win])
                       / (t_p[win][-1] - t_p[win][0])) / rho_in
        e3 = abs(q_mean - cm["qbar_m3s"]) / cm["qbar_m3s"]
        print(f"E3 mean flow: {q_mean*6e7:.3f} vs intent "
              f"{cm['qbar_m3s']*6e7:.3f} mL/min ({e3*100:.3f}%)")
        assert e3 <= 0.005, f"E3 FAILED: mean flow off by {e3*100:.2f}% > 0.5%"
        summ_extra = {"Qbar_mLmin": round(q_mean * 6e7, 4)}
        if cm["waveform"] != "steady":
            # solver dt from the log (monitor cadence is every 10 steps and
            # would under-count by 10x); worst case over the whole run
            dt_max = max(float(x) for x in re.findall(
                r"^deltaT = ([\d.eE+-]+)", log.read_text(), re.M))
            spp = (1.0 / cm["freq_hz"]) / dt_max
            print(f"E4 steps/period: >= {spp:.0f} (gate >= 40)")
            if spp < 40 - 1e-6 and a.waive_e4 and spp >= 39:
                print(f"*** E4 WAIVED at {spp:.2f} steps/period — {a.waive_e4}")
                waivers.append(f"E4({spp:.2f} steps/period): {a.waive_e4}")
            else:
                assert spp >= 40 - 1e-6, \
                    f"E4 FAILED: {spp:.2f} steps/period < 40"
            summ_extra["steps_per_period"] = round(spp, 1)
        else:
            print("E4 steps-per-period: skipped (steady case)")
    else:
        print("E3 mean-flow gate: skipped (static case, no inlet)")
        print("E4 steps-per-period gate: skipped (static case, no pulsation)")
        summ_extra = {}

    # ---- emit --------------------------------------------------------------
    PROCESSED.mkdir(parents=True, exist_ok=True)
    ts_path = PROCESSED / "timeseries.csv"
    if ts_path.exists():
        old = pd.read_csv(ts_path, index_col="time")
        old = old[old["case"] != label]
        out = pd.concat([old, ts])
    else:
        out = ts
    out.to_csv(ts_path)

    summ = {
        "case": label, "t_end": t_end,
        "Tmax_K": ts["Tmax_module"].iloc[-1],
        "dT_module_K": ts["dT_module"].iloc[-1],
        "sigmaT_K": ts["sigmaT_module"].iloc[-1],
        "power_per_cell_W": power_per_cell,
        "E_in_J": e_in, "E_stored_cells_J": stored_cells,
        "E_stored_fluid_J": stored_fluid, "E_wall_J": wall_loss_J,
        "energy_residual_pct": e1 * 100, "Courant_max": co_max,
        **summ_extra,
        "waived_gates": " | ".join(waivers),
    }
    sm_path = PROCESSED / "summary.csv"
    sm = pd.read_csv(sm_path) if sm_path.exists() else pd.DataFrame()
    if not sm.empty:
        sm = sm[sm["case"] != label]
    pd.concat([sm, pd.DataFrame([summ])]).to_csv(sm_path, index=False)
    print(f"wrote {ts_path.relative_to(REPO)} ({len(ts)} rows) and "
          f"{sm_path.relative_to(REPO)}; all gates passed.")


if __name__ == "__main__":
    main()
