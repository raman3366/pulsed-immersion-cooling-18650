#!/usr/bin/env python3
"""Fig. 5: temperature contours + in-plane velocity on (a) the vertical plane
through one cell row (y = +11 mm) and (b) the horizontal plane at cell
mid-height (z = 32.5 mm), for steady flow and phase-resolved pulsed flow.
No pyvista: cell centres come from `postProcess -func writeCellCentres`
(local OpenFOAM), fields are parsed from the ascii files; a plane slice is
the layer of cells nearest the plane. Writes paper/figures/fig5_*.png.
Usage: fields_fig5.py [--test]"""
import re, subprocess, sys
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation

REPO = Path(__file__).resolve().parents[2]; M = REPO / "cases/matrix"; OUT = REPO / "paper/figures"
Y_ROW, Z_MID = 0.011, 0.0325
TMIN, TMAX = 25.0, 32.5
REGIONS = ["fluid"] + [f"cell{i}" for i in range(6)]

def read_field(path):
    txt = path.read_text()
    m = re.search(r"internalField\s+nonuniform\s+List<(scalar|vector)>\s*\n?(\d+)\s*\n?\(", txt)
    if not m:
        u = re.search(r"internalField\s+uniform\s+(\(?[-\d.eE+ ]+\)?)", txt); v = np.fromstring(u.group(1).strip("()"), sep=" ")
        return v
    kind, n = m.group(1), int(m.group(2)); start = m.end()
    body = txt[start:]; end = body.index("\n)\n"); body = body[:end]
    if kind == "scalar": return np.fromstring(body, sep="\n")[:n]
    return np.array(re.findall(r"\(([-\d.eE+ ]+)\)", body), dtype=object).astype(str).__array__() if False else \
           np.fromstring(body.replace("(", " ").replace(")", " "), sep=" ").reshape(n, 3)

def ensure_centres(case, t, region):
    c = M / case / str(t) / region / "C"
    if not c.exists():
        subprocess.run(["openfoam2606", "-c", f"postProcess -func writeCellCentres -region {region} -time {t} > /dev/null 2>&1"],
                       cwd=M / case, check=True)
    return read_field(c)

def layer(C, axis, value):
    z = C[:, axis]; zs = np.unique(np.round(z, 4)); z0 = zs[np.argmin(abs(zs - value))]
    return abs(z - z0) < 5e-4

def panel(ax, case, t, plane, title):
    axis, value, ix, iy = ((1, Y_ROW, 0, 2) if plane == "vertical" else (2, Z_MID, 0, 1))
    cf = None
    for region in REGIONS:
        d = M / case / str(t) / region
        if not (d / "T").exists(): continue
        C = ensure_centres(case, t, region); T = read_field(d / "T") - 273.15
        sel = layer(C, axis, value)
        if sel.sum() < 10: continue
        x, y = C[sel, ix] * 1e3, C[sel, iy] * 1e3
        tri = Triangulation(x, y)
        cf = ax.tricontourf(tri, T[sel], levels=np.linspace(TMIN, TMAX, 31), cmap="inferno", extend="both")
        if region == "fluid" and (d / "U").exists():
            U = read_field(d / "U")[sel]; step = max(1, sel.sum() // 500)
            ax.quiver(x[::step], y[::step], U[::step, ix], U[::step, iy], color="w", scale=0.04, width=0.0025, alpha=0.75)
    ax.set_aspect("equal"); ax.set_title(title, fontsize=8); ax.tick_params(labelsize=6)
    ax.set_xlabel("x [mm]", fontsize=7); ax.set_ylabel(("z" if plane == "vertical" else "y") + " [mm]", fontsize=7)
    return cf

PANELS = [("fields_steady_f0.00_A0.00_Q2_C3", 900, "steady, t = 900 s"),
          ("fields_sine_f2.00_A0.60_Q2_C3", 899.5, "2 Hz A0.6, φ = 0"),
          ("fields_sine_f2.00_A0.60_Q2_C3", 899.625, "2 Hz A0.6, φ = π/2"),
          ("fields_sine_f2.00_A0.60_Q2_C3", 899.75, "2 Hz A0.6, φ = π"),
          ("fields_sine_f2.00_A0.60_Q2_C3", 899.875, "2 Hz A0.6, φ = 3π/2"),
          ("fields_sine_f0.10_A0.60_Q2_C3", 892.5, "0.1 Hz A0.6, φ = 0"),
          ("fields_sine_f0.10_A0.60_Q2_C3", 895, "0.1 Hz A0.6, φ = π/2"),
          ("fields_sine_f0.10_A0.60_Q2_C3", 897.5, "0.1 Hz A0.6, φ = π"),
          ("fields_sine_f0.10_A0.60_Q2_C3", 900, "0.1 Hz A0.6, φ = 3π/2")]

if __name__ == "__main__":
    test = "--test" in sys.argv
    sel = [PANELS[1]] if test else [p for p in PANELS if (M / p[0] / str(p[1]) / "fluid/T").exists()]
    for plane in ("vertical", "horizontal"):
        n = len(sel); ncol = 3 if n > 4 else max(n, 1); nrow = int(np.ceil(n / ncol))
        fig, axs = plt.subplots(nrow, ncol, figsize=(4.4 * ncol, (2.4 if plane == "vertical" else 1.8) * nrow + 0.5), squeeze=False)
        cf = None
        for k, (case, t, title) in enumerate(sel):
            cf = panel(axs[k // ncol][k % ncol], case, t, plane, title) or cf
        for k in range(n, nrow * ncol): axs[k // ncol][k % ncol].axis("off")
        if cf is not None: fig.colorbar(cf, ax=axs.ravel().tolist(), label="T [°C]", shrink=0.8)
        name = OUT / f"fig5_{plane}{'_test' if test else ''}.png"
        fig.savefig(name, dpi=170, bbox_inches="tight"); plt.close(fig); print("wrote", name.name)
