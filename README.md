# Pulsed coolant flow in single-phase dielectric immersion cooling of an 18650 module — data and code

Companion release for: Lakshmipathi, Deepanraj, Thamizharasan, *Pulsed coolant flow in single-phase dielectric immersion cooling of an 18650 module: a regime map for temperature uniformity at millijoule pumping cost*, submitted to Applied Thermal Engineering (2026).

## Contents
- `data_processed/` — every number in the paper: `pareto.csv` (per-case metrics incl. the D-17 pump-energy decomposition), `sweep_summary.csv`, `summary.csv` (conservation gates and recorded waivers per run), `timeseries.csv` (monitor time series, all runs), `gci.csv`, `timestep_independence.csv`, `validation_liu3c.csv`.
- `data_reference/` — cell/coolant properties, heat-generation polynomial, digitised validation curve (with provenance).
- `case_template/` — the OpenFOAM v2606 `chtMultiRegionFoam` case template (mesh, physics rendering, monitors); `scripts/generate_cases.py` produces every production case from it.
- `scripts/` — case generation, EC2 run drivers, post-processing (`post/extract_metrics.py` gates, `post/pec.py` pump energy, `post/paper_figures.py`, `post/tables.py`).
- `paper/` — figure and table sources as submitted.
- `PROJECT.md` — full specification and decision log (D-01 … D-17) with changelog.

## Reproduce
OpenFOAM v2606 (ESI), Python 3.11+ with numpy, pandas, matplotlib, pyyaml, scipy. See `environment.md` and `PROJECT.md` §6–§7. Raw field data (≈ 0.7 GB) are available from the corresponding author on request.

## Licence
Code: MIT. Data, figures and text: CC BY 4.0. See `LICENSE`.
