#!/usr/bin/env python3
"""Generate cases/matrix/* from cases/template + the §8 case matrix.

Naming (§8): <waveform>_f<freq>_A<amp>_Q<level>_C<rate>, e.g.
sine_f1.00_A0.40_Q2_C3 / steady_f0.00_A0.00_Q2_C3 / square_f0.50_D0.50_Q2_C3.

Each generated case is a copy of the template's SOURCE files plus a
case.env that Allrun.pre sources (WAVEFORM/QBAR_ML_MIN/FREQ_HZ/AMP/DUTY),
with endTime set to t_discharge. Rule 2: these cases are NEVER hand-edited.

Currently only C3 is generatable — the 1C/2C heat-generation polynomials
exist only as Liu Fig 3b curves and are not yet digitised (heatgen.yaml).

Usage:
    generate_cases.py [--blocks steady anchors sine pareto square] [--dry-run]
    (pareto block retained in code but DROPPED from the plan under D-12/D-15)
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
TEMPLATE = REPO / "cases/template"
MATRIX = REPO / "cases/matrix"
Q_LEVELS = {1: 50.0, 2: 90.0, 3: 130.0,          # D-11 [mL/min]
            4: 250.0, 5: 500.0}                  # D-14 high-flow anchors
# production dt cap for steady cases (env STEADY_MAXDT overrides). D-13's
# 0.0125 was an Euler-era value; with `backward` (§4.6) the cap is set from
# the backward dt pair (run_bwdcheck_ec2.sh) — 0.05 unless the pair disagrees.
STEADY_MAXDT = float(os.environ.get("STEADY_MAXDT", "0.05"))
FREQS = [0.1, 0.25, 0.5, 1.0, 2.0]               # §3.5
AMPS = [0.2, 0.4, 0.6]
DUTIES = [0.25, 0.5, 0.75]
SOURCES = ["Allrun", "Allrun.pre", "makeMesh.py", "makePhysics.py",
           "0.orig", "system", "constant"]


def add(cases, waveform, q, c, f=0.0, A=0.0, D=None):
    if c != 3:
        sys.exit(f"C{c} requested but only the 3C heat-gen polynomial is "
                 "digitised (heatgen.yaml) — digitise Fig 3b first.")
    if waveform == "square":
        name = f"square_f{f:.2f}_D{D:.2f}_Q{q}_C{c}"
    else:
        name = f"{waveform}_f{f:.2f}_A{A:.2f}_Q{q}_C{c}"
    env = dict(WAVEFORM=waveform, QBAR_ML_MIN=Q_LEVELS[q],
               FREQ_HZ=f, AMP=A, DUTY=(D or 0.5))
    if f == 0:
        env["MAXDT"] = STEADY_MAXDT                       # D-13
    else:
        # E4 gate (>= 40 steps/period) with 5% margin: adjustableRunTime
        # write-snapping enlarges dt by up to ~0.4% above maxDeltaT, which
        # left the sine sweep at 39.86-39.94 steps/period (E4 waived W4).
        # Never coarser than the steady production cap.
        env["MAXDT"] = round(min(STEADY_MAXDT, 1.0 / (42 * f)), 6)
    if os.environ.get("NOUTER"):                          # PIMPLE outer correctors
        env["NOUTER"] = int(os.environ["NOUTER"])         # (region-coupling convergence)
    cases[name] = env


def build_matrix(blocks):
    cases = {}
    if "steady" in blocks:                        # baseline (C3 slice)
        for q in (1, 2, 3):
            add(cases, "steady", q, 3)
    if "anchors" in blocks:                       # D-14 regime-map anchors
        for q in (4, 5):
            add(cases, "steady", q, 3)
    if "sine" in blocks:                          # §8 sweep at Q2, C3
        for f in FREQS:
            for A in AMPS:
                add(cases, "sine", 2, 3, f=f, A=A)
    if "pareto" in blocks:                        # reduced-Qbar block: the
        for q_ml in (30, 40, 60, 70):             # energy-fair points bracket
            Q_LEVELS[len(Q_LEVELS) + 1] = float(q_ml)
            add(cases, "sine", len(Q_LEVELS), 3, f=1.0, A=0.4)
    if "square" in blocks:
        for D in DUTIES:
            for f in (0.5, 1.0):
                add(cases, "square", 2, 3, f=f, D=D)
    return cases


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", nargs="+",
                    default=["steady"],
                    choices=["steady", "anchors", "sine", "pareto", "square"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    t_disch = yaml.safe_load(
        (REPO / "data/reference/heatgen.yaml").read_text())["liu3c"]["t_discharge"]
    cases = build_matrix(a.blocks)
    for name, env in cases.items():
        print(f"  {name}")
        if a.dry_run:
            continue
        dst = MATRIX / name
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir(parents=True)
        for s in SOURCES:
            src = TEMPLATE / s
            (shutil.copytree if src.is_dir() else shutil.copy2)(src, dst / s)
        # endTime = discharge duration; keep 30 restart points
        cd = dst / "system/controlDict"
        txt = cd.read_text()
        txt = txt.replace(
            "endTime         30;                 // TEMPLATE SMOKE; "
            "generate_cases.py sets 900 (t_discharge) per matrix case",
            f"endTime         {t_disch:g};                // t_discharge "
            "(set by generate_cases.py)")
        txt = txt.replace("writeInterval   10;", "writeInterval   30;")
        cd.write_text(txt)
        (dst / "case.env").write_text(
            "".join(f"export {k}={v}\n" for k, v in env.items()))
    print(f"{len(cases)} cases {'(dry run)' if a.dry_run else 'generated'} "
          f"-> {MATRIX.relative_to(REPO)}")


if __name__ == "__main__":
    main()
