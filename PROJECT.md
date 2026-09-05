# Pulsed Immersion Cooling of a Li-ion Battery Module
### OpenFOAM conjugate-heat-transfer study — project specification

**Repo:** `immersion-pulsed-cfd`
**Owner:** (you)
**Target journal:** Applied Thermal Engineering (Elsevier, hybrid, no APC on the subscription route)
**Fallback:** International Communications in Heat and Mass Transfer
**Status:** Week 1 of 8 — setup
**Last updated:** 2026-08-27

---

## 0. How to use this document

This is the single source of truth for the project. It is written so that a
person can open the repo cold and know what
to build, how to verify it, and what "done" means.

- **Sections 1–4** are the specification. Change them only through a decision
  entry in §2, so that the reason for every change survives.
- **Sections 5–9** are the mechanics: layout, environment, run workflow,
  post-processing.
- **Sections 10–13** are the research process: validation gate, schedule,
  figures, submission.
- **Section 14** is the risk register. Re-read it at every weekly checkpoint.

Keep this file at the repository root.

---

## 1. Project at a glance

**Objective.** Produce a submission-ready journal manuscript in 8 weeks on
single-phase dielectric immersion cooling of a cylindrical Li-ion battery
module, using OpenFOAM conjugate heat transfer, in which the novelty is
**pulsed / intermittent coolant flow evaluated as a cooling-performance vs
pump-energy trade-off**.

**Why this angle.** Pulsating flow is established for cold-plate BTMS
(≈5% pump-energy saving, *Energy* 273 (2023); up to 50% pump-power reduction,
*Int. J. Heat Mass Transfer* (2025)) but has not been evaluated systematically
for **module-level** immersion cooling. The closest prior work — Li et al.,
*J. Energy Storage* 64 (2023) 107177 — is reciprocating immersion of a
**single 18650 cell under fast charging**. The contribution must therefore be
positioned explicitly as: *module scale, single-phase (non-boiling), with a
pump-energy optimisation framework and a temperature-uniformity focus.*

**Gap statement (draft — reuse in the Introduction).**
> Single-phase immersion cooling of lithium-ion modules has been studied
> extensively under static and steady forced flow, with recent work optimising
> coolant selection, inlet/outlet placement, flow-distribution plates and cell
> arrangement. Pulsating and intermittent flow — shown to cut pump energy while
> preserving heat transfer in cold-plate BTMS — has not been systematically
> evaluated for module-level immersion cooling. Using a validated OpenFOAM
> conjugate-heat-transfer model, this work quantifies the maximum-temperature,
> module temperature-uniformity, pressure-drop and pump-energy trade-offs of
> pulsed versus steady immersion flow across pulsation frequency and amplitude,
> and identifies energy-optimal operating points on a Pareto front.

**Deliverables.**
1. A reproducible OpenFOAM case suite (the repo itself, offered as
   supplementary material — a real differentiator, since almost all recent work
   in this space is Fluent-based).
2. A validated model, benchmarked against published experiment.
3. A manuscript with >50 references, majority from the target journal and
   majority 2024–2026.

**Candidate titles.**
1. Pulsed single-phase immersion cooling of a cylindrical lithium-ion battery
   module: a conjugate heat transfer study of the thermal performance–pump
   energy trade-off
2. Energy-efficient immersion thermal management of lithium-ion batteries under
   pulsating dielectric flow: an OpenFOAM conjugate heat transfer analysis
3. Trade-off between cooling performance and pumping power in pulsed immersion
   cooling of lithium-ion battery modules

---

## 2. Open decisions

Record every decision here with a date and a one-line rationale. Anything not
listed is still open and must not be silently assumed in code.

| ID | Decision | Status | Notes |
|----|----------|--------|-------|
| D-01 | **The ATE paper is the live one.** | Decided 2026-08-27 | The IEEEtran notes are a legacy artifact of earlier planning; the literature pool (58% ATE) and validation anchor were built for ATE. |
| D-02 | Cell format: **18650**, 6P1S, 2 mm inter-cell gap | Decided 2026-08-18 | Chosen because Liu et al. (ATE 233:121184) is the most complete validation dataset and is in the target journal |
| D-03 | Dielectric fluid: **3M Novec-7200** for validation | Decided 2026-08-18 | Matches primary validation case |
| D-04 | Solver: **`chtMultiRegionFoam`**, laminar | Decided 2026-08-18 | Justify laminar by Re; switch to k-ω SST low-Re if transitional |
| D-05 | Comparison basis: **primary = matched pump energy (Pareto front); secondary = matched mean flow, framed as the mechanism study only** | Decided 2026-08-27 | Laminar ⟨Q²⟩ ≥ ⟨Q⟩² makes matched-mean-flow energy claims indefensible (§3.6); no prior immersion work uses an energy-fair basis — this gap is novelty pillar #1 (`docs/literature/gap-analysis.md`) |
| D-06 | Waveform set: sinusoidal + square (intermittent) | Proposed | Square wave with duty cycle is where the pump-energy story actually lives |
| D-07 | Novec-7200 thermal conductivity: **0.068 W/m·K, CLOSED** | Closed 2026-08-30 | Validation runs: k=0.068 passes the §10 gate (5.74% MAE); k=0.6 fails at 26.4% — the "effective conductivity" overcools by 13 °C in a convection-resolving model. Publishable observation (`data/processed/validation_liu3c.csv`) |
| D-08 | Cloud target: AWS EC2 spot (c7a / c7g) | Decided 2026-08-14 | Mac is a front-end only; OCI Ampere free tier for meshing trials. An existing c7i.8xlarge spot box is available; reuse-vs-relaunch decided at first production launch |
| D-10 | **Production duct — REVISED 2026-08-31 (user): tight channel**, 46 mm (w) × 72 mm (h) (module + 4 mm side / 7 mm top clearance), flow along x, x ∈ [−90, +90]; cells on floor, caps adiabatic, walls adiabatic | Revised 2026-08-31 | The original wide duct proved buoyancy-dominated: T_max flow-independent (30.7 °C at 50–130 mL/min), pump power ~µW — no Pareto trade-off exists there (kept as a context result). Tight duct: gap Re = 36/65/94 at D-11 flows — forced convection competitive, shedding-capable, matches pack-channel architecture |
| D-12 | **Paper reframed (user, 2026-08-31): regime map + uniformity.** Validated finding: at practical immersion flows the module is buoyancy-dominated — T_max flow-flat (31.4/31.3/31.3 °C in the tight duct), pump energy 0.04–0.21 mJ/discharge → the pulsed-vs-steady PUMP-ENERGY question is ill-posed at realistic conditions (energy-honesty result, contribution #1). Pulsation is evaluated as a near-zero-cost UNIFORMITY actuator (ΔT_mod −39% with flow while T_max static; sweep scores ΔT/σ_T, contribution #2), plus 2–3 high-flow anchor cases mapping where forced convection would begin to dominate (regime map, contribution #3). §3.6's Pareto framing is retained only as the honesty argument | Decided 2026-08-31 | Supersedes the E_pump-vs-T_max headline; §12 figure list to be revised at manuscript time |
| D-11 | **Mean-flow levels Q̄ = 50 / 90 / 130 mL/min** | Decided 2026-08-31 (user) | Brackets the published forced-immersion range (Chandrasekaran 50–125). Exact Re/Wo/Ri table computed at build time — NOTE: gap Re ~ O(10) → no natural vortex shedding; mechanism framing shifts to pulsation-modulated mixed convection (flagged to user at build) |
| D-13 | **Time-step policy — uniformity-first (user, 2026-09-01).** Duct dt check: T_max is dt-dependent (+0.18 K from dt 0.048→0.025, Euler at Co≈1; matches the sweep's apparent +0.20 K at 1 Hz) while ΔT and σ_T are dt-robust (±0.002 K). Policy: the 15-case sine sweep is the ΔT/σ_T/E_pump regime map (no T_max claims from it except the fine-dt subset: 2 Hz cases + sine 0.1 Hz A0.6 at dt 0.0125); every T_max-bearing steady comparison (3 baselines, anchors) runs at maxDeltaT 0.0125. The box time-step study (0.038%) is superseded for the duct. | Decided 2026-09-01 (user) | Options priced: uniform cap 0.025 (≈$22), 0.0125 everywhere (≈$43), extrapolate-only; chosen ≈$11 + anchors. |
| D-16 | **Block-3 numerics (user, 2026-09-02, option A): FIXED uniform dt 0.0125 s for the entire production matrix**, `backward`, nOuterCorrectors 2 (≈nOuter6 within 0.01 K at this dt), maxCo 1.0 as CFL guard. All claims are deltas at matched temporal numerics; absolute T_max carries a temporal-uncertainty band (±0.15–0.2 K) documented by the 12-run dt study. Q2 baseline = bwd_dt0.0125_Q2 (identical recipe, aliased in place of steady_f0.00_A0.00_Q2_C3); anchors Q4/Q5 run Courant-limited below 0.0125 (footnoted, finer not coarser); 2 Hz rows capped at 1/(42f)=0.0119 (E4). Supersedes D-13's cap policy. ≈133 lane-h ≈ $110. | Decided 2026-09-02 (user) | Options B ($50, ±0.3 K) and C (uniformity-only) declined. |
| D-17 | **Pump-energy basis (user, 2026-09-04): viscous + start/stop kinetic energy.** $E_p = k_\mathrm{lam}\int Q^2 dt/\eta$ with $k_\mathrm{lam}=\Delta p/\bar Q$ of the steady case at the same $\bar Q$ (laminar), plus, for intermittent (square) flow only, $N_\mathrm{cycles}\,\tfrac12\rho V_\mathrm{duct} U_\mathrm{on}^2/\eta$ (kinetic energy injected at each ON step and dissipated at each valve closure; inertial work over a smooth sine cycle is reversible → 0). The measured $\int Q\,\Delta p\,dt$ (monitor cadence 0.125 s) aliases the inertial pressure $\rho L\,dU/dt$ — negative for square waves, +0.2–0.3× spurious at 2 Hz — and is retained only as a validation column (agrees within 3 % for steady and $f\le1$ Hz). | Decided 2026-09-04 (user) | Alternatives declined: viscous-only (understates intermittent cost), measured-only (loses square + 2 Hz). |
| D-14 | **High-flow anchors Q̄ = 250 and 500 mL/min** (steady, dt 0.0125) for the regime map — Ri ≈ 1/8 and 1/31 of Q2. | Decided 2026-09-01 (user) | 1000 mL/min (≈14 h, ≈$23) declined; 200/400 declined. |
| D-15 | **Block 2 composition + schedule:** steady Q1/Q3 at dt 0.0125 (Q2 = dtchk_dt0.0125_Q2), anchors Q4/Q5, square-wave block (6: D 0.25/0.5/0.75 × f 0.5/1 Hz, Q2, dt 1/(42f)), field-writing re-runs of sine 0.1 Hz A0.6 and 2 Hz A0.6 (phase quarters over the last period) for the contour figure; steady field panel from the Q2 fine baseline. Runs continuously from the end of the dt check, unattended, two lanes, auto-pull + auto-stop. Reduced-Q̄ Pareto block and 1C/2C block DROPPED under D-12. | Decided 2026-09-01 (user) | ≈37 lane-hours ≈ 19 h wall ≈ $31. |
| D-09 | Static-validation outer wall — **AMENDED 2026-08-30: bath acts through the wall resistance**, `externalWallHeatFluxTemperature` U = 27 W/m²K (5 mm acrylic 38 + bath film ~100 in series) to 22 °C, on all bath-facing boundaries. Production duct cases stay adiabatic with stated justification | Amended 2026-08-30 (user gate acceptance) | Direct fixed-T (original D-09) overcooled by 7.3 °C — walls absorbed 81% of input. Four-step diagnostic ladder (fixed-T 10.45% → lid 9.53% → β 8.81% → h=38 6.55% → U=27 **5.74% PASS**) in `validation_liu3c.csv`; the ladder doubles as the paper's BC-sensitivity table. Parallels D-07: physical inputs for a physics-resolving model |

---

## 3. Scientific specification

### 3.1 Physical problem

A 6-cell (6P1S) 18650 module, 2 mm inter-cell gap, fully immersed in flowing
dielectric coolant inside a rectangular duct. The cells generate heat
volumetrically at a rate set by C-rate. Coolant enters at controlled
temperature and time-varying flow rate, and leaves at the far end. Heat leaves
the cells by conduction into the fluid and is carried away by advection;
buoyancy is retained (the solver is buoyant), so the static-immersion validation
case is representable with the same setup at zero inlet flow.

### 3.2 Governing equations

Fluid region: unsteady, incompressible-buoyant Navier–Stokes with the Boussinesq
or full `rhoThermo` treatment as provided by `chtMultiRegionFoam`, plus energy.
Solid regions: transient conduction with **anisotropic** conductivity and a
volumetric source term. Coupling at all cell–fluid interfaces is via the
standard `compressible::turbulentTemperatureCoupledBaffleMixed` (or the
`...RadCoupledMixed` variant) condition — temperature and heat flux continuity.

### 3.3 Material properties

From Liu, Aldan, Huang & Hao, *Applied Thermal Engineering* 233 (2023) 121184.
Put these in `data/reference/properties.yaml` and generate the OpenFOAM
dictionaries from that file — never hand-type them twice.

**Cell (Samsung ICR18650-22P, 2.2 Ah, NMC111):**

| Property | Value | Unit |
|---|---|---|
| Density | 2523 | kg/m³ |
| Specific heat | 1145 | J/kg·K |
| Conductivity, radial | 1.2 | W/m·K |
| Conductivity, axial | 34.4 | W/m·K |

Anisotropy is essential — a 29× ratio. Implement with
`thermophysicalProperties` using an anisotropic solid thermo model and a
`coordinateSystem` per cell (cylindrical, axis along the can). Verify this
renders correctly before trusting any result: a quick check is a single cell
with a fixed base temperature — the axial gradient must be ~29× shallower than
the radial one.

**Coolant (3M Novec-7200):**

| Property | Value | Unit |
|---|---|---|
| Density | 1430 | kg/m³ |
| Dynamic viscosity | 6.1e-4 | Pa·s |
| Specific heat | 1220 | J/kg·K |
| Thermal conductivity | **0.068 baseline** (0.6 in validation sensitivity — see D-07) | W/m·K |

> **D-07 matters more than it looks.** A factor of ~9 in coolant conductivity
> changes the static (natural-convection) validation case substantially and the
> forced-flow cases only mildly. Manufacturer data for HFE-7200 is around
> 0.068 W/m·K, which suggests the 0.6 figure is an error in the source — but do
> not assume. Run the static validation at both values and report which
> reproduces the experiment. That sensitivity study is itself a small, honest
> contribution and pre-empts a reviewer finding it first.

### 3.4 Heat generation

Volumetric source in each cell region:

```
q''' = I(U_oc - U)/V_cell  -  I·T·(dU_oc/dT)/V_cell      [W/m³]
```

For the paper, fit the polynomial heat-generation profile reported by Liu et al.
against C-rate and depth-of-discharge, and implement it as a `codedSource` so
the source can depend on both time and the region-averaged cell temperature.
Store the fit coefficients in `data/reference/heatgen.yaml`.

C-rates in scope: **1C, 2C, 3C** constant discharge, plus one drive-cycle
transient (WLTP-derived) as a relevance case only — not a headline result.

### 3.5 Pulsation definition

Sinusoidal:

```
Q(t) = Q̄ · [1 + A · sin(2πft)]
```

Intermittent (square wave, duty cycle D):

```
Q(t) = Q̄/D   for  mod(t, 1/f) < D/f
Q(t) = 0      otherwise
```

Both preserve the cycle-mean flow rate Q̄. Parameter ranges:

- Frequency f: 0.1, 0.25, 0.5, 1, 2 Hz
- Amplitude ratio A: 0.2, 0.4, 0.6
- Duty cycle D: 0.25, 0.5, 0.75
- Mean flow Q̄: 3 levels bracketing the validation range

Report the dimensionless groups, not just the raw settings — reviewers in this
field expect them: Reynolds number Re (based on cell diameter and mean gap
velocity), Prandtl number Pr, **Womersley number Wo = R√(ω/ν)** (the parameter
that actually governs whether the oscillating boundary layer detaches from the
mean profile), amplitude ratio A, and Richardson number Ri (to justify whether
buoyancy is negligible in forced cases).

### 3.6 The comparison basis — read this before designing the matrix

**This is the methodological trap that will otherwise sink the paper at review.**

In laminar flow, pressure drop is linear in flow rate, Δp ≈ kQ. Cycle-averaged
pump power is then

```
⟨P⟩ = ⟨Q·Δp⟩/η = k⟨Q²⟩/η ≥ k⟨Q⟩²/η
```

with equality only for steady flow. For a sinusoid, ⟨Q²⟩ = Q̄²(1 + A²/2); for a
square wave at duty cycle D, ⟨Q²⟩ = Q̄²/D. **So at matched mean flow rate,
pulsation always costs more pump energy than steady flow, not less.** Any result
claiming otherwise at matched mean flow is a numerical artefact and a reviewer
will say so.

The saving reported in the cold-plate literature comes from a different place:
pulsation improves heat transfer *per unit pumping energy*, which lets you
**lower the mean flow** and still hold T_max. The correct framing is therefore:

- **Primary result: a Pareto front** of cycle-averaged pump energy E_pump
  versus T_max (and versus module ΔT), with the steady-flow cases forming the
  baseline curve and the pulsed cases forming a second curve. The claim is that
  the pulsed curve lies below/left of the steady curve over some region.
- **Secondary: a PEC map** over (f, A) at fixed mean flow, showing where
  enhancement is strongest.
- **Report matched-mean-flow comparisons too**, but present them as the
  mechanism study, not the headline. Be explicit in the text that matched mean
  flow is not an energy-fair comparison, and say why. Owning this earns
  credibility.

**Decision D-05 is: primary basis = matched pump energy (Pareto), secondary =
matched mean flow (mechanism).** Confirm and mark decided.

The physical mechanism to look for and describe: the module is a **cylinder
array**, so the wakes behind cells are the dominant mixing structure. Pulsation
that couples to the shedding frequency (or that periodically re-attaches and
sheds the recirculation zones behind the downstream cells) is where enhancement
should appear. Extract the shedding Strouhal number from the steady baseline
first, then choose at least one pulsation frequency near it. That gives the
paper a mechanism, not just a sweep.

### 3.7 Output metrics

Computed for every case, per §9:

| Symbol | Definition | Purpose |
|---|---|---|
| T_max | Max temperature over all solid regions | Safety limit (< 40 °C target) |
| ΔT_mod | max−min cell-volume-average temperature | Module uniformity (< 3 °C target) |
| σ_T | Std. dev. of cell-average temperatures | Uniformity, less outlier-sensitive |
| Δp | Area-averaged p at inlet − outlet | Hydraulic cost |
| P_pump(t) | Q(t)·Δp(t)/η, η = 0.7 (state and sensitivity-test) | Instantaneous cost |
| E_pump | ∫P_pump dt over the discharge | **Headline energy metric** |
| PEC | (Nu/Nu₀)/(f_D/f_D,₀)^(1/3) | Standard enhancement criterion |
| Wo, Re, Ri | Dimensionless groups | Generalisation |

Define Nu with an explicit characteristic length and reference temperature in
the paper — ambiguity here is a common reviewer complaint.

---

## 4. Numerical specification

### 4.1 Solver and version pinning

- **Distribution:** ESI OpenFOAM (`openfoam.com`). The EC2 box is on **v2606**.
- **Pin the version everywhere.** Local Mac, EC2 and any future machine must run
  the same tag. Use the Docker/Apptainer image in `env/` as the definition of
  record, and record the exact `Build :` banner string in
  `docs/environment.md`.
- **Solver:** `chtMultiRegionFoam`.

> **Version check to run in Week 1, before writing any case:** confirm
> `chtMultiRegionFoam` exists in v2606 and check the current syntax for
> `fvOptions`/`fvModels` sources and for `Function1` entries — ESI has been
> migrating these between releases, and syntax in this document reflects
> recent-but-not-verified-for-2606 usage. The authority is
> `$FOAM_TUTORIALS/heatTransfer/chtMultiRegionFoam` on the actual install.
> Copy a working tutorial and mutate it; do not write dictionaries from scratch.

### 4.2 Meshing

1. Geometry as STL: duct, 6 cylinders (`cell0`…`cell5`), exported from CAD or
   generated by script into `geometry/`.
2. `blockMesh` background block, uniform, cell size ≈ 1.5 mm.
3. `snappyHexMesh` with `castellatedMesh`/`snap`/`addLayers`, each cylinder as a
   closed surface producing a **cellZone + faceZone**.
4. `splitMeshRegions -cellZones -overwrite` → regions `fluid`, `cell0`…`cell5`.
5. `checkMesh -allRegions` must pass; target max non-orthogonality < 65,
   max skewness < 4, and ≥ 5 prism layers in the gaps.

Target sizes: coarse ≈ 1.2 M, medium ≈ 2.5 M, fine ≈ 5.5 M cells
(refinement ratio r ≈ 1.3 in each direction). The production matrix runs on the
**medium** mesh once GCI clears.

### 4.3 Boundary conditions

| Patch | U | p_rgh | T |
|---|---|---|---|
| inlet | `flowRateInletVelocity` (Function1) | `fixedFluxPressure` | `fixedValue` (inlet temp) |
| outlet | `pressureInletOutletVelocity` | `fixedValue` (0) | `inletOutlet` |
| duct walls | `noSlip` | `fixedFluxPressure` | `zeroGradient` (adiabatic) or fixed h |
| cell↔fluid | mapped coupling | — | `compressible::turbulentTemperatureCoupledBaffleMixed` |

Outer walls: **the validation rig was not insulated** — Liu et al.'s acrylic
box sat in a water bath at 22 ± 2 °C (full text; `docs/literature/anchors.md`
A1). The static validation case therefore uses `fixedValue` T = 22 °C on the
outer walls with a ±2 °C sensitivity (D-09); the conjugate 5 mm acrylic-wall
region is the fallback if the 8% gate is missed. Production duct cases keep
adiabatic walls — a different, flow-through configuration where advection
dominates wall losses — and state that justification explicitly.

### 4.4 Pulsed inlet — implementation

Use `flowRateInletVelocity` with a `Function1` volumetric flow rate. This
guarantees the mean flow rate is exactly what you intend, which matters for
§3.6. Do **not** impose a sinusoid on velocity directly at a patch whose area
you might later change.

Sinusoidal:

```cpp
inlet
{
    type                flowRateInletVelocity;
    volumetricFlowRate  sine;
    volumetricFlowRateCoeffs
    {
        frequency   1;          // f [Hz]
        amplitude   1;          // keep 1; put magnitude in scale
        scale       8.33e-8;    // A * Q̄  [m³/s]
        level       2.78e-7;    // Q̄      [m³/s]
        t0          0;
    }
    value           uniform (0 0 0);
}
```

Intermittent: use the `square` Function1 (has a mark/space ratio for duty
cycle) or a `table` with `repeat` bounds handling. A `csvFile` Function1 is the
escape hatch for the drive-cycle case.

**Ramp the first cycle.** Starting a pulsating inlet from a dead-stop field
produces a pressure transient that pollutes the first period. Either start from
a converged steady solution at Q̄, or multiply by a `scale`/ramp Function1 over
one period, and discard the first 2–3 periods from all cycle-averages.

### 4.5 Volumetric heat source in the solids

Per solid region, in `constant/<region>/fvOptions` (or `fvModels` — see the
version check in §4.1):

```cpp
batteryHeat
{
    type            semiImplicitSource;
    selectionMode   all;
    volumeMode      specific;      // W/m³
    sources { h  (Q_dot 0); }      // explicit part only
}
```

For the C-rate/DoD-dependent profile of §3.4, replace with a `codedSource` that
evaluates the fitted polynomial from the current time and the region-average
temperature. Keep the coded source in `src/` and `#include` it, so it is
reviewable and version-controlled rather than buried in a dictionary.

### 4.6 Numerics

- `PIMPLE` with 2 outer correctors, 2 pressure correctors, momentum predictor
  on. Tighten `residualControl` until outer iterations converge in ≤ 2.
- `ddtSchemes: backward` (2nd order) for production; `Euler` only for
  start-up robustness.
- `divSchemes`: `Gauss limitedLinear 1` for velocity and enthalpy; avoid pure
  `upwind` in the final runs — a reviewer will ask about numerical diffusion in
  the wakes, which is exactly where your mechanism lives.
- `adjustTimeStep yes`, `maxCo 0.8`, and — critically —
  **`maxDeltaT` set so that there are ≥ 40 time steps per pulsation period.**
  At 2 Hz that means `maxDeltaT ≤ 0.0125` s. Record steps-per-period in the
  case log; it is a table entry in the paper.
- `writeControl adjustableRunTime` so writes land on fixed wall-clock intervals
  and restarts are clean on spot instances.

### 4.7 On-the-fly metrics (function objects)

Configure once in `cases/template/system/functions/` and `#include` everywhere:

- `volFieldValue` per solid region: `max(T)`, `volAverage(T)`
- `surfaceFieldValue` on inlet and outlet: `areaAverage(p)`, `sum(phi)`
- `fieldMinMax` over all regions
- `writeInterval` fine enough to resolve the pulsation (≥ 20 samples/period)

This means the metrics of §3.7 fall out of the run as CSV without
post-processing full fields — essential, because you will not want to download
5 M-cell field data from EC2 for 25 cases.

### 4.8 Independence studies

**Mesh (GCI, Celik et al. 2008, ASME J. Fluids Eng. 130(7):078001):** three
grids, refinement ratio r > 1.3, report apparent order p and GCI_fine for both
T_max and Δp. **Accept the mesh when GCI_fine < 3%.**

**Time step:** halve `maxDeltaT` on the medium mesh at the highest frequency
(2 Hz) and the highest C-rate; accept when T_max and cycle-averaged Δp change
by < 1%.

**Both studies go in the paper as a table.** Skipping them is the fastest route
to rejection for a CFD-only submission.

---

## 5. Repository layout

```
immersion-pulsed-cfd/
├── README.md                   # 20-line orientation + how to run
├── .gitignore
├── docs/
│   ├── PROJECT.md              # this file
│   ├── environment.md          # exact versions, banner strings, install notes
│   ├── validation.md           # validation log: what was compared, error, date
│   └── decisions/              # one file per non-obvious decision (ADR style)
├── env/
│   ├── Dockerfile              # pinned OpenFOAM image, used on Mac and EC2
│   └── apptainer.def
├── geometry/
│   ├── make_geometry.py        # parametric STL generation
│   └── stl/                    # generated, gitignored except a hash manifest
├── cases/
│   ├── template/               # the canonical case; everything derives from it
│   ├── validation/
│   │   ├── liu2023-static/
│   │   └── forced-flow/
│   ├── mesh-study/{coarse,medium,fine}/
│   └── matrix/                 # generated by scripts/generate_cases.py
├── scripts/
│   ├── generate_cases.py       # matrix (§8) -> case dirs from template
│   ├── run_local.sh            # smoke test, coarse, serial-ish
│   ├── run_ec2.sh              # decomposePar -> mpirun -> reconstruct -> S3
│   ├── sync_results.sh
│   └── post/
│       ├── extract_metrics.py  # function-object CSV -> tidy dataframe
│       ├── pec.py              # PEC, pump energy, Pareto front
│       └── figures.py          # every figure in §12, one function each
├── data/
│   ├── reference/              # properties.yaml, heatgen.yaml, digitised expt curves
│   ├── processed/              # metrics CSVs — COMMITTED, these are the results
│   └── raw/                    # foam output — gitignored, lives on S3
├── src/
│   └── codedSource/            # heat-generation coded source, reviewable
└── paper/
    ├── main.tex
    ├── refs.bib
    └── figures/
```

**Rules that keep this repo sane:**

1. `cases/template/` is the only hand-edited case. Every other case is
   **generated**. If you find yourself editing two cases by hand, stop and fix
   the generator.
2. `data/processed/*.csv` is committed. Those files are the paper. Raw fields
   are not committed and not backed up beyond S3.
3. Every figure in the paper is produced by a function in `figures.py` from a
   committed CSV. No figure is ever made by hand in ParaView without a script
   that reproduces it — except the contour/streamline plots, which get a saved
   ParaView state file in `paper/figures/state/`.
4. Case names are the parameter set (§8). Never `test2`, `final`, `final_v2`.

---

## 6. Environment

### 6.1 Local (MacBook Air, 8 GB)

Front-end only: case authoring, generation scripts, post-processing, ParaView,
manuscript. Coarse smoke tests (< 300 k cells) are fine; production runs are
not. Do not fight this — the machine is fanless and RAM-bound.

Install via the community `openfoam-app` (native Apple Silicon) for speed, or
Docker for exactness. **Docker is the one that matters for reproducibility**, so
if there is any divergence, Docker wins and the app build is a convenience.

```bash
# ParaView + python tooling
brew install --cask paraview
python3 -m venv .venv && source .venv/bin/activate
pip install numpy pandas matplotlib pyyaml scipy pyvista
```

### 6.2 EC2 (production)

- **Instances:** `c7a` (AMD) or `c7g`/`c8g` (Graviton). Every vCPU is a physical
  core on both — CFD gains little from hyperthreading. Avoid `hpc*` families,
  they are on-demand only.
- **Sizing:** 50–100 k cells per core at `decomposePar`. Below ~25 k cells/core,
  MPI overhead eats the scaling. A 2.5 M-cell medium mesh → 32 cores.
- **Spot is safe for CFD** if you checkpoint: `writeControl adjustableRunTime`,
  `startFrom latestTime`, EBS + `aws s3 sync` after each write. A reclaimed
  instance costs you one write interval.
- **Storage:** transient runs write tens of GB. Use a dedicated EBS volume, sync
  to S3, and run `foamToVTK`/`postProcess` **on the instance** — download slices
  and CSVs, never full fields.
- `decomposePar` with `scotch`.

### 6.3 OCI Ampere free tier

4 ARM cores / 24 GB, permanently free, and more capable than the Air. Use it
for meshing experiments and overnight coarse runs so you are not paying AWS to
discover a snappyHexMesh typo.

### 6.4 Reproducibility contract

`docs/environment.md` records: OpenFOAM banner string, image digest, Python
package versions (`pip freeze`), and the instance types used for each result set.
The paper's Data Availability statement points at the repo.

---

## 7. Run workflow

```
author/edit cases/template  →  generate matrix  →  smoke test locally (coarse)
      →  push to git  →  pull on EC2  →  decomposePar  →  mpirun  →  metrics CSV
      →  s3 sync  →  pull CSVs locally  →  figures  →  manuscript
```

The invariant: **the repo is the transport layer.** Nothing gets to EC2 except
through git; nothing comes back except CSVs and slices. That way any result can
be traced to a commit.

```bash
# on EC2, one case
./scripts/run_ec2.sh cases/matrix/sine_f1.00_A0.40_Q2_C3
# runs: decomposePar -> mpirun -np 32 chtMultiRegionFoam -parallel
#       -> reconstructPar -latestTime -> postProcess -> s3 sync
```

Log every run in `data/processed/run_log.csv`: case name, commit hash, instance
type, cores, wall time, end status. Wall-time data is also how you find out in
Week 5 whether the remaining matrix actually fits in the schedule.

---

## 8. Case matrix

Naming: `<waveform>_f<freq>_A<amp>_Q<level>_C<rate>`, e.g.
`sine_f1.00_A0.40_Q2_C3`, `steady_f0.00_A0.00_Q2_C3`,
`square_f0.50_D0.50_Q2_C3`.

| Block | Cases | Purpose |
|---|---|---|
| Validation | 2–4 | Reproduce Liu et al. static; forced-flow backup |
| Mesh/time independence | 4 | GCI + time-step study |
| Steady baseline | 3 Q̄ × 3 C-rate = 9 | Pareto baseline curve |
| Sinusoidal sweep | 5 f × 3 A at fixed Q̄, C=3 | PEC map, mechanism |
| Sine at reduced Q̄ | 6 | The energy-fair Pareto points |
| Intermittent | 3 D × 2 f | Duty-cycle branch |
| Bridging cases | 2–3 | Drive cycle; ±15% cell-to-cell heterogeneity |

**~35 runs.** That is more than the 15–25 originally scoped, because §3.6
requires a proper Pareto front. Mitigation is in §14 (frozen-flow decoupling)
and the priority order is: validation → mesh study → steady baseline → sine
sweep → reduced-Q̄ Pareto → intermittent → bridging. **If time runs out, the
paper still stands after the reduced-Q̄ Pareto block.** Everything after that is
bonus.

---

## 9. Post-processing

`extract_metrics.py` reads the function-object output of each case and emits one
row per (case, time) into `data/processed/timeseries.csv`, plus one row per case
into `data/processed/summary.csv` with cycle-averaged quantities taken over the
**last three full periods** (discarding start-up per §4.4).

`pec.py` computes E_pump, PEC, the dimensionless groups, and the Pareto front.
Assumptions that must be stated explicitly in the paper and sensitivity-tested:
pump efficiency η, the definition of Nu, and the averaging window.

Sanity checks the pipeline should assert, not just report:

- Energy balance: ∫q'''dV over all solids vs enthalpy rise between inlet and
  outlet plus stored energy. **Closure within 2%** or the case is rejected.
- Cycle-mean inlet flow rate equals the intended Q̄ within 0.5%.
- Courant number max stayed below the target.
- Steps per pulsation period ≥ 40.

Make these hard failures in the script. A silently non-conserving case that
reaches a figure is the worst outcome available to this project.

---

## 10. Validation protocol — the go/no-go gate

**Primary:** Liu, Aldan, Huang & Hao, *Applied Thermal Engineering* 233 (2023)
121184 — 18650, 6P1S, Novec-7200, static immersion. Compare cell temperature
histories at 1C/2C/3C against the digitised published curves. The paper's stated
bound is T_max below 40 °C with a temperature gradient within 3 °C at 3C.

> The specific figures (T_max 37 °C, ΔT 1.8 °C, 2.9% average model error at 3C)
> were **verified against the full accepted manuscript on 2026-08-27** (green-OA
> copy; extraction with section references in `docs/literature/anchors.md` A1).
> Per-C-rate curves at 1C/2C still need digitising from the figures in Week 3.

**Backup:** Chandrasekaran & Jithin, *J. Energy Storage* 111 (2025) 115445
(AmpCool AC-110, 50–125 mL/min forced flow). Its cell format, immersion depth,
inlet temperature and full property table are paywalled and must be extracted
from the full text before this can serve as a quantitative anchor.

**Open-access single-cell case:** Li et al., *Case Studies in Thermal
Engineering* 34 (2022) 102034 — useful as a third point and freely checkable.

**Gate (end of Week 4).** Accept if temperature error ≤ 8% after resolving D-07.
If not: switch the primary anchor to the forced-flow or single-cell dataset
**before** starting the case matrix. Do not proceed into the matrix on an
unvalidated model in the hope of fixing it later; that failure mode costs the
whole project.

Log every validation attempt in `docs/validation.md` with date, case commit,
what was compared, and the resulting error. That log becomes the validation
subsection of the paper almost verbatim.

---

## 11. Schedule

8 weeks, Week 1 starting **Mon 31 Aug 2026**, submission target **Sun 25 Oct
2026**. Two months gets you to a submission-ready manuscript, not a publication:
ATE medians run ~6 days to desk decision, ~42 days to post-review decision,
~95 days to acceptance.

| Week | Dates | Work | Gate |
|---|---|---|---|
| 1 | Aug 31 – Sep 6 | Resolve D-01. Repo + env + version check (§4.1). Copy and run the cht tutorial. Geometry script. Reference matrix started, live ATE% / 2024-26% counters. | Tutorial runs on EC2 at the pinned version |
| 2 | Sep 7 – 13 | Mesh: snappy + splitMeshRegions + checkMesh on three grids. Properties and coded heat source wired. Anisotropy verification test. | `checkMesh -allRegions` passes on all three |
| 3 | Sep 14 – 20 | Static validation vs Liu et al., both D-07 conductivity values. Energy-balance check working. | Validation curves plotted |
| 4 | Sep 21 – 27 | GCI + time-step study. Finish validation. Steady baseline runs start. | **GO/NO-GO (§10). GCI_fine < 3%.** |
| 5 | Sep 28 – Oct 4 | Steady baseline complete. Sine sweep (PEC map). Shedding frequency extracted. | Baseline Pareto curve exists |
| 6 | Oct 5 – 11 | Reduced-Q̄ Pareto block. Intermittent block. Bridging cases if time. | **Pulsed curve vs steady curve — the result** |
| 7 | Oct 12 – 18 | All figures and tables. Draft Results + Discussion. | Every figure regenerable from CSV |
| 8 | Oct 19 – 25 | Intro/Methods/Conclusions. Highlights, graphical abstract, nomenclature, declarations. Internal review pass. | Submit |

**Parallel track:** the OpenFOAM learning cases (`flatPlateHT`, `cylinder3D`)
continue alongside Week 1–2 but must not block them. Learn snappyHexMesh on the
cylinder case *and* on the real geometry at the same time — the real geometry is
the better teacher now.

**Realistic warning.** This assumes near-daily effort and that OpenFOAM
fundamentals are in hand by end of Week 2. If Week 4's gate slips, the honest
move is to cut the intermittent and bridging blocks rather than compress the
validation — a smaller paper with a solid gate beats a broad one with a shaky
model.

---

## 12. Figures and tables

| # | Content |
|---|---|
| Fig. 1 | Module geometry, computational domain, boundary conditions |
| Fig. 2 | Mesh detail + prism layers, with GCI table inset |
| Fig. 3 | Validation: predicted vs measured temperature histories |
| Fig. 4 | Heat-generation profile vs C-rate and DoD |
| Fig. 5 | Temperature contours + streamlines, steady vs pulsed at phase quarters |
| Fig. 6 | T_max vs time, steady vs pulsed at matched mean flow |
| Fig. 7 | Module ΔT and σ_T vs frequency and amplitude |
| Fig. 8 | Instantaneous and cycle-averaged pump power |
| Fig. 9 | **PEC map over (f, A)** |
| Fig. 10 | **Pareto front: E_pump vs T_max, steady vs pulsed vs intermittent** — the headline |
| Fig. 11 | Drive-cycle / heterogeneity bridging case |

| Table | Content |
|---|---|
| T1 | Cell and fluid properties |
| T2 | Case matrix |
| T3 | GCI and time-step independence |
| T4 | Summary metrics per case |
| T5 | Dimensionless groups per case block |

Figures 9 and 10 are the paper. Everything else supports them.

---

## 13. Manuscript and submission

**D-01 decided 2026-08-27: Applied Thermal Engineering is the live target.**

- Elsevier "Your Paper Your Way" — relaxed formatting at first submission,
  strict at revision.
- **Highlights:** 3–5 bullets, max 85 characters each including spaces,
  submitted as a separate editable file with "highlights" in the filename.
- **Graphical abstract:** separate file.
- **Keywords:** 1–7, avoid multi-word phrases, avoid repeating title words.
- **Nomenclature** after abstract/keywords, two columns, Greek letters and
  sub/superscripts grouped separately.
- Abstract: single paragraph, no references or uncommon abbreviations.
- References: Elsevier numbered, consistent from the first citation.
- Submission via Editorial Manager, single-anonymised review.
- **Required statements:** competing interests; CRediT author statement; data
  availability; declaration of generative-AI use in writing.

**Reference strategy (advisor's mandate):** >50 references, majority from ATE,
majority 2024–2026. Keep live counters from Week 1 and never let either fall
below 55%. Track in `paper/refs.bib` with a script that reports both
percentages.

**Common ATE desk rejections to pre-empt:** scope mismatch; simulation-only
without experimental validation; parametric studies with no applied-engineering
hook; missing Highlights or graphical abstract; incomplete declarations;
reference-style drift. The validated model + pulsed-flow novelty + energy
trade-off + Pareto framing answers the first three directly.

**Verify before the cover letter:** current impact factor and scope wording on
the official journal page. Aggregator figures vary by source and year.

---

## 14. Risk register

| Risk | Signal | Mitigation |
|---|---|---|
| **Scooped** — a 2026 module-level pulsed-immersion paper appears | Weekly Scopus/Google Scholar alert on "immersion cooling pulsating" | Pivot framing to PEC-optimisation + heterogeneity/baffle recovery, which stays open |
| **Validation fails** | Week 4 gate, error > 8% | Switch anchor dataset (§10) before the matrix, not after |
| **D-07 conductivity unresolved** | Static case cannot match either value | Report as a sensitivity study; lean on the forced-flow anchor instead |
| **Runtime overrun** — 35 transient CHT runs | Week 5 wall-time log extrapolates past Week 6 | **Frozen-flow decoupling:** converge the pulsating velocity field to a periodic state, then solve only the energy equation on a frozen/periodically-updated flow field for the slowly varying thermal load. Cuts long-discharge cost dramatically. Also: cut the intermittent and bridging blocks first |
| **Pulsed shows no benefit** | Pareto curves overlap | This is still publishable if framed honestly as bounding the conditions under which pulsation helps — but decide by Week 6 and reframe the title and abstract accordingly, do not bury it |
| **Numerical diffusion masks the mechanism** | Wakes look over-smoothed | Second-order divergence schemes (§4.6); show the shedding is resolved on the medium mesh |
| **Spot reclamation** | Interrupted run | `startFrom latestTime` + S3 sync; costs one write interval |
| **Desk rejection on scope** | — | ICHMT fallback kept formatted in parallel: shorter intro, fewer figures, reformat costs days not weeks |

---

## 15. Changelog

| Date | Change |
|---|---|
| 2026-08-27 | Initial specification. Novelty angle, validation dataset, journal and schedule carried over from the planning conversation. Comparison basis (§3.6) newly specified — this supersedes the earlier "matched mean flow" assumption, which is not energy-fair. Case count raised from ~25 to ~35 to support the Pareto front. |
| 2026-08-27 | Decisions D-01 (ATE), D-05 (matched pump energy primary), D-07 (0.068 baseline + sensitivity) taken; D-09 added (validation outer wall = fixed-T 22 °C — Liu rig was bath-bounded, not insulated; §4.3 corrected). §10 validation targets verified against the Liu full text. Basis: the literature session of 2026-08-27 (74 verified refs, counters green). Novelty positioning updated against Gao et al., *Energy* 310 (2024) 133266 — see `docs/literature/gap-analysis.md`. |
| 2026-08-30 | **Validation gate PASSED and accepted (user):** MAE 1.95 °C / 5.74% vs digitised Liu Fig 9 at 3C on the coarse grid, U=27 model. D-07 closed (0.068), D-09 amended (bath via acrylic+film). Spot abandoned for on-demand c7a.8xlarge (Oregon) after a capacity interruption — AMI copied cross-region. Remaining before matrix: k=0.6 recheck under corrected BC, GCI (grids built, runs pending), time-step study, β from manufacturer ρ(T). |
| 2026-08-30 | **GCI accepted by user at 3.305%** (self-imposed <3% narrowly missed; literature norm ≤5%): monotonic, p=1.40, ±1.0 °C band on T2; comparative production claims cancel discretization error. Time-step independence 0.038%. Phase 3 (validation) and Phase 4 (independence) are COMPLETE. Next: Phase 4 steady baselines → Phase 5 production matrix (template duct case build first). |
| 2026-08-31 | **Duct E1 audit RESOLVED — no solver leak.** Time-resolved solver-native rho·h audit: conservation 98% early; pseudo-steady export ≈ source (12.7 W) with required mixing-cup rise 4.85 K matching the observed +5.0 K hot band. Ledger blind spots fixed: areaAverage(T) under-reads stratified outflow; -postProcess phi reconstruction unreliable at bidirectional faces (gross ~9× net) — live weightedSum(phi·T) monitors now standard. Wide-duct metrics retain PRELIMINARY tag (superseded by D-10 revision). |
| 2026-08-31 | Tight-duct baselines + full duct GCI complete (all §9 gates, 2 documented waivers: E1 early-window export physics, E2 gap-jet Courant peaks → maxCo 1.0 forward). **D-12: paper reframed to regime-map + uniformity** after the validated model showed buoyancy dominance at practical flows. Sweep to be launched next session under the new scoring. |
| 2026-09-01 | **Sine sweep complete (15/15, Q2, medium duct)** — all §9 gates with recorded waivers (E1 export W1; E2 Courant ≤1.71 W2; new W4: 39.8–39.99 steps/period from adjustableRunTime write-snapping, generator margin now 1/(42f)). ΔT uniformity response non-monotone in f (−14% at 0.1 Hz A0.6 for +4% E_pump; −24% at 2 Hz A0.6 for +69% E_pump; +9% worse at 1 Hz A0.2). **Open numerics flag:** T_max rises with f independent of A and tracks the solver dt (Euler, Co≈1) — duct time-step independence check pending (steady Q2 at maxDeltaT 0.025/0.0125) before any T_max/regime-map claim; §9 time-step gate on the box does not transfer to the duct. Post-processing readers now handle multi-segment (resumed) monitors. |
| 2026-09-01 | D-13/D-14/D-15 decided (user): dt policy uniformity-first, anchors 250/500, block 2 = baselines Q1/Q3 @0.0125 + anchors + square block + field re-runs; Pareto and C-rate blocks dropped. First dt point: steady Q2 @0.025 → T_max +0.18 K, ΔT +0.002 K. |
| 2026-09-01 | **Duct dt check → Euler DIVERGES: T_max 31.28 / 31.46 / 31.82 °C at dt 0.048 / 0.025 / 0.0125 (differences growing), bulk fluid T rising with refinement, no unsteadiness (σ(T_max) 0.014 K).** Diagnosis: implicit-Euler temporal numerical diffusion ≈ u²Δt/2 — ~60× the coolant's molecular diffusivity in the plumes/gap jets at dt 0.05, still ~15× at 0.0125 — artificially mixes the plumes and over-exports heat. §4.6 already mandates `backward` for production; the baselines and sweep ran Euler by implementation error. **Rectified:** template/makePhysics default `backward` (DDT=Euler override retained), backward dt-pair check launched (steady Q2 at 0.05/0.025/0.0125); Euler block 2 halted after 5 min. All Euler results (baselines, 15-case sweep, dt check) become the documented numerics cautionary tale; production matrix to be re-run with backward once the pair agrees within 0.05 K. D-13's dt-cap policy is superseded by the scheme change (cap to be set from the backward pair). |
| 2026-09-01 | Backward dt pair also non-convergent (31.446→31.677 °C, dt 0.039→0.025); solver log shows unconverged fluid–solid coupling within each step (nOuterCorrectors 2). Diagnostic: backward + nOuterCorrectors 6 at dt 0.05 / 0.025; if converged, §4.6 numerics become `backward` + 6 outer correctors (cap 0.05) for the whole production matrix (block 3, auto-launched by the VM orchestrator v2). |
| 2026-09-02 | **Temporal-recipe search complete (11 runs), BLOCK3_HELD.** Steady Q2: Euler 31.282/31.464/31.818 °C (dt .048/.025/.0125); backward nOuter2 31.446/31.677; backward nOuter6 31.542/31.687 (dt .039/.025); nOuter4 31.514 ≈ nOuter6 (0.03 K). Converged coupling removes ~40% of the dt slope; the remainder is ~1st-order temporal resolution of the buoyant plumes at Co≈1 (converged T_max ≈ 31.9–32.0, needs dt≈0.006 — infeasible per case). Proposed design: FIXED uniform dt for the whole matrix (claims = deltas at matched numerics; absolute T_max with a temporal-uncertainty band). Options: A dt 0.0125 (±0.15–0.2 K, ≈$100), B dt 0.025 (±0.3 K, ≈$50), C = B uniformity-only. Backward fine point (dt 0.0125) running to anchor the band. User decision pending. |
| 2026-09-02 | D-16 decided (user): block 3 launched under fixed dt 0.0125 / backward / nOuter 2; VM orchestrator v4 (skip-Q2 alias, auto close-out). |
| 2026-09-02 | **Backward fine point: T_max 31.960 °C at dt 0.0125** (sequence 31.446/31.677/31.960 — differences +0.23/+0.28 K, still ~1st-order). The dt-0.0125 absolute is itself ≥0.3 K below the converged value; D-16 stands (fixed-dt deltas) but the manuscript must state absolute T_max as under-resolved with a one-sided temporal bias (converged ≈ 32.2–32.5 by extrapolation) — or quote T2-style comparisons only. dT at 0.0125: 0.186 K (non-monotone across dt/schemes → deltas only at matched numerics). Q2 baseline aliased + scored; block 3 resumed cleanly after the bwfine freeze window. |
| 2026-09-04 | **Fixed-Δt matrix (D-16) — steady + sine sweep scored (20/26).** Steady: T_max 32.03/31.96/31.84/31.54/31.01 °C at 50/90/130/250/500 mL/min (−1 K over a decade of flow); E_pump 0.03–3.8 mJ per discharge — energy-honesty finding stands. Sweep at matched numerics: T_max unchanged by pulsation (all 15 within ±0.1 K of steady, except the 0.25 Hz A0.6 buoyant-layer flush event at t≈720 s, −0.6 K, clean solver). Uniformity: the Euler-era 0.1 Hz 'cheap win' (−14 %) was a Δt artefact — at fixed Δt low-f pulsation is neutral (−2…+4 %), the 0.5–1 Hz band is adverse (+25…+29 % ΔT), and only 2 Hz at A ≥ 0.4 helps (ΔT −16/−22 %, σ_T −20 %, E_pump 1.36/1.52×). Intra-cycle variation of the end-snapshot metrics < 0.02 K (equals cycle average). Square block + fields pending. |
| 2026-09-04 | D-17 pump-energy basis decided; pareto.csv carries Epump_J (measured), Epump_visc_J, Epump_inert_J, Epump_model_J (primary). First square cases: ΔT −17…−28 %, σ_T −18…−35 %, T_max −0.1…−0.2 K at 4.6–24.5× steady pump energy (0.33–1.79 mJ, KE-dominated). |
| 2026-09-04 | **Square block complete (6/6, fixed Δt).** All six improve uniformity: ΔT −6.5…−28 %, σ_T −5…−35 %, T_max −0.05…−0.19 K (only waveforms to move T_max); gain grows as D shrinks and slightly with f. Cost (D-17): 2.5–25× steady (0.18–1.79 mJ), KE-dominated. 26/26 production cases scored; only the three field re-runs (Fig. 5) remain on the VM. |
| 2026-09-05 | **All compute complete; VM stopped for good (user).** Field re-runs pulled (fields_sine 2 Hz/0.1 Hz phase snapshots, steady t=900); Fig. 5 rendered from cell-centre slices (no pyvista). Manuscript fully drafted pending author sign-off. Total EC2 spend this project ≈ $190 (validation+independence ≈ $30, Euler sweep ≈ $35, dt/recipe study ≈ $20, block 3 ≈ $105). |
| 2026-09-05 | **Manuscript built for ATE submission** (paper/submission/): full text, 11 figures + S1, 4 tables, 58 references (57 % ATE / 72 % 2024–26), highlights, graphical abstract, cover letter, checklist; compiled with tectonic (elsarticle). Author sign-off items marked `% AUTHOR CHECK`; GfA items to verify listed in docs/submission-checklist.md. |
