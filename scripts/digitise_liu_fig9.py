#!/usr/bin/env python3
"""Digitise the immersion-cooling EXPERIMENT curve (T2 vs t, red open
circles) from Liu et al. 2023 Fig. 9 -> data/reference/liu_validation_curves.csv.

Method (developed + visually audited at 600 DPI, 2026-08-28):
  1. Render the Fig. 9 region of AM page 14 (pymupdf, 600 DPI).
  2. Calibrate axes from tick-label centroids (y-residual < 0.02 C,
     x-residual < 3.5 s over 0..1000 s).
  3. Split the red mask into the thick simulation line (survives a
     radius-4 morphological opening) and thin ring strokes.
  4. Markers lie on a measured ~14.83 s grid. Primary estimator, per slot:
     Kasa circle fit to the ring pixels with 3 outlier-rejecting refits;
     accepted when the fitted radius is 12..19 px (true ring ~15.5 px).
     Audited: centres sit visually dead-centre in the circles.
  5. Fallback for slots where the circles merge with the line (the tail,
     and the two earliest resolvable slots): centroid of the enclosed ring
     interiors (fill-holes method). Cross-method bias measured at all
     overlapping slots and reported; it is O(0.1 C).
Limitations:
  - t < ~198 s: the black air-cooling markers overprint and cut the rings;
    not digitisable. The t=0 row (25.0 C) is the initial condition stated
    in Liu §3.3, not a digitised point.
"""

from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image
from scipy import ndimage

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data/reference/liu_validation_curves.csv"

PITCH_S = 14.83                      # measured marker pitch
GRID = np.arange(213.4 - 14 * PITCH_S, 910, PITCH_S)
GRID = GRID[GRID > -7]

# ---- render -----------------------------------------------------------------
doc = pymupdf.open(REPO / "data/reference/liu2023.pdf")
pix = doc[13].get_pixmap(dpi=600, clip=pymupdf.Rect(150, 455, 445, 690))
img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
img = img[..., :3].astype(int)
R, G, B = img[..., 0], img[..., 1], img[..., 2]

# ---- calibration (tick-label centroids, verified) ---------------------------
px2t = np.polyfit([385.0, 752.0, 1115.5, 1485.0, 1852.0, 2205.0],
                  [0, 200, 400, 600, 800, 1000], 1)
px2T = np.polyfit([241.0, 483.5, 723.5, 964.5, 1204.5, 1445.0],
                  [50, 45, 40, 35, 30, 25], 1)


def mask_red(strict):
    d = 40 if strict else 22
    m = (R - G > d) & (R - B > d) & (R > (120 if strict else 110))
    m[:129, :] = m[1572:, :] = False       # outside plot frame
    m[:, :390] = m[:, 2220:] = False
    m[700:881, 1450:] = False              # red annotation text
    m[1280:, :] = False                    # legend block
    return m


def kasa(x, y):
    A = np.c_[2 * x, 2 * y, np.ones(len(x))]
    b = x**2 + y**2
    (cx, cy, c), *_ = np.linalg.lstsq(A, b, rcond=None)
    return cx, cy, np.sqrt(c + cx**2 + cy**2)


# ---- primary: circle fits on line-removed ring pixels -----------------------
red = mask_red(strict=False)
disk = np.zeros((9, 9), bool)
yy, xx = np.mgrid[-4:5, -4:5]
disk[np.hypot(xx, yy) <= 4] = True
line = ndimage.binary_dilation(ndimage.binary_opening(red, structure=disk),
                               iterations=3)
ring = red & ~line
ys, xs = np.where(ring)
tx = np.polyval(px2t, xs)

primary = {}
for k, tg in enumerate(GRID):
    m = np.abs(tx - tg) < PITCH_S / 2 * 0.95
    if m.sum() < 80:
        continue
    x, y = xs[m].astype(float), ys[m].astype(float)
    cx, cy, r = kasa(x, y)
    for _ in range(3):
        d = np.hypot(x - cx, y - cy)
        keep = np.abs(d - r) < 4.5
        if keep.sum() < 50:
            break
        cx, cy, r = kasa(x[keep], y[keep])
    if 12 <= r <= 19:
        primary[k] = (float(np.polyval(px2t, cx)), float(np.polyval(px2T, cy)))

# ---- fallback: enclosed-interior centroids ----------------------------------
red_s = mask_red(strict=True)
closed = ndimage.binary_closing(red_s, structure=np.ones((5, 5)))
holes = ndimage.binary_fill_holes(closed) & ~closed
holes[700:881, 1450:] = False
holes[1280:, :] = False
# only ROUND, WHOLE interior components are unbiased centre estimates
# (line-split half-holes and inter-ring tunnels read high by ~0.25 C —
# measured below — so they are NOT used)
hlab, hn = ndimage.label(holes)
fallback = {}
for i, sl in enumerate(ndimage.find_objects(hlab)):
    npx = (hlab[sl] == i + 1).sum()
    h = sl[0].stop - sl[0].start
    w = sl[1].stop - sl[1].start
    if not (180 <= npx <= 700 and 0.7 <= w / h <= 1.4):
        continue
    cy = (sl[0].start + sl[0].stop) / 2
    cx = (sl[1].start + sl[1].stop) / 2
    t = float(np.polyval(px2t, cx))
    k = int(round((t - GRID[0]) / PITCH_S))
    if 0 <= k < len(GRID) and abs(t - GRID[k]) < PITCH_S / 2:
        fallback[k] = (t, float(np.polyval(px2T, cy)))

# ---- cross-method bias at overlapping slots ---------------------------------
both = sorted(set(primary) & set(fallback))
bias = np.array([fallback[k][1] - primary[k][1] for k in both])
print(f"method overlap: {len(both)} slots; fallback-minus-primary bias "
      f"mean {bias.mean():+.3f} C, max |{np.abs(bias).max():.3f}| C")

# ---- assemble ---------------------------------------------------------------
pts = [(0.0, 25.0, "initial_condition")]
for k in range(len(GRID)):
    if k in primary:
        t, T = primary[k]
        pts.append((round(t, 1), round(T, 3), "circle_fit"))
    elif k in fallback:
        t, T = fallback[k]
        pts.append((round(t, 1), round(T, 3), "hole_centroid"))

arr = np.array([(t, T) for t, T, _ in pts])
assert (np.diff(arr[:, 1]) > -0.08).all(), "series not monotone"
assert 36.2 <= arr[-1, 1] <= 36.8 and arr[-1, 0] > 880, \
    "endpoint disagrees with the ~36.5 C @ 900 s anchor"
n_cf = sum(1 for *_, p in pts if p == "circle_fit")
hdr = (
    "# Liu et al. 2023 (ATE 233:121184) Fig. 9 — immersion cooling EXPERIMENT,\n"
    "# T2 (mid-height surface of cell-2) vs time, 3C discharge.\n"
    "# Digitised from the green-OA accepted manuscript by\n"
    "# scripts/digitise_liu_fig9.py (method, audit and limitations there).\n"
    "# provenance: circle_fit = primary estimator (visually dead-centre);\n"
    "#   hole_centroid = fallback where markers merge with the sim line\n"
    f"#   (cross-method bias at {len(both)} common slots: "
    f"mean {bias.mean():+.3f} C, max {np.abs(bias).max():.3f} C);\n"
    "#   initial_condition = stated 25.0 C start (Liu §3.3), not digitised.\n"
    "# t < ~198 s not digitisable (overprinted by air-cooling markers).\n"
    "time_s,T2_C,provenance\n"
)
OUT.write_text(hdr + "\n".join(f"{t},{T},{p}" for t, T, p in pts) + "\n")
print(f"wrote {OUT.relative_to(REPO)}: {len(pts)} rows "
      f"({n_cf} circle_fit, {len(pts)-1-n_cf} hole_centroid), "
      f"{arr[1,0]:.0f}..{arr[-1,0]:.0f} s digitised")
