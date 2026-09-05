# Environment record

Reproducibility contract per PROJECT.md §6.4. Update this file whenever a
machine, version or package changes; the paper's Data Availability statement
points at this repo.

## OpenFOAM — pinned version

| | Mac (front end) | EC2 (production) |
|---|---|---|
| Distribution | ESI OpenFOAM (openfoam.com) | ESI OpenFOAM |
| Version | **v2606** (api 2606, patch 0) | **v2606** |
| Build string | `_481094fdf3-20260618` | record at first VM session |
| Install | `OpenFOAM-v2606.app` (native Apple Silicon), wrapper `/opt/homebrew/bin/openfoam2606` | `/usr/lib/openfoam/openfoam2606` |
| Invocation | `openfoam2606 -c "<cmd>"` | `openfoam2606 -c "<cmd>"` |
| Arch flags | Clang, DP, label=32 | (verify identical at first VM session) |

Cases port between the two unchanged (proven in the sibling project
`openfoam.htanalysis18650`).

## §4.1 version check — executed 2026-08-27 on the Mac install

All syntax assumptions in PROJECT.md §4.4/§4.5 verified against the actual
v2606 sources (`$WM_PROJECT_DIR/src`), not from memory:

- `chtMultiRegionFoam` present:
  `platforms/darwin64ClangDPInt32Opt/bin/chtMultiRegionFoam`.
- **`Function1 sine`** — exactly as §4.4: `frequency`, `amplitude`, `scale`,
  `level`, `t0` (period form also available). Ramp Function1s exist for the
  start-up (`linearRamp`, `halfCosineRamp`, `quarterSineRamp`, ...), plus
  `Table`/`TableFile`/`CSV` for the drive-cycle case.
- **`Function1 square`** — has the **mark/space ratio `r`** → duty cycle D is
  expressible directly. (Confirm the exact entry keyword when writing the
  dictionary — header truncates the entry table.)
- **`fvOptions`, not `fvModels`** — `fvModels` does not exist anywhere in the
  v2606 tree; sources live in `constant/<region>/fvOptions`.
- **`semiImplicitSource`** — §4.5's `sources { h (Su Sp); }` form is the
  current syntax (OpenFOAM-2206+). Bonus: each source entry may be a
  **Function1 or `exprField`** (`explicit`/`implicit` sub-entries), so the
  time-dependent part of the heat profile may not even need a codedSource.
  `codedFvSource` also present for the temperature-feedback term.
- **`flowRateInletVelocity`** — present
  (`src/finiteVolume/fields/fvPatchFields/derived/flowRateInletVelocity`).
- **Anisotropic solid thermo** — `heSolidThermo` with `transport constAnIso`,
  vector `kappa`, and a `coordinateSystem` block (see tutorial
  `heatTransfer/solidFoam/multiSolidWithAnisoConduction`); `cylindricalCS`
  exists for per-cell axes.
- **The interface trap is structurally confirmed:** `temperatureCoupledBase`
  in v2606 offers `kappaMethod` ∈ {`fluidThermo`, `solidThermo`,
  **`directionalSolidThermo`**, `lookup`, `function`}. Per the sibling
  project, `solidThermo` silently uses mag(kappa) for anisotropic solids —
  cell↔fluid interfaces MUST use `directionalSolidThermo` (+ `alphaAni`),
  and the §3.3 single-cell anisotropy check runs before anything else.

## §3.3 anisotropy gate — PASSED 2026-08-27 (`cases/checks/anisotropy`)

Transient erfc-penetration test on an 18×18×65 mm block with the real cell
thermo (`constAnIso`, cylindrical CS, kappa (1.2 1.2 34.4)): the **solver**
recovers k_axial = 34.44 (err 0.12%), k_radial = 1.200 (err 0.04%),
anisotropy ratio 28.71 vs 28.67 exact. The interior conduction operator
(`solidThermo::heatDiffusion` → `aniAlpha` tensor; hybrid-harmonic variant
for zone mixtures) is anisotropy-correct.

**New trap found by the gate — scalar kappa accessors are mag-collapsed.**
`constAnIsoSolidTransport::kappa(p,T)` returns `mag(kappa_)` verbatim
(v2606 `constAnIsoSolidTransportI.H:70`), i.e. 34.442 for our cell in EVERY
direction. Every consumer of the scalar `kappa()`/`alpha()` accessor
inherits this, confirmed by measurement for the **`wallHeatFlux` function
object** (solid branch computes `alpha()*snGrad(he)`): it over-reports the
radial flux by ~29×. Consequences for this project:

- **Never use `wallHeatFlux` (or any scalar-kappa FO) on cell regions.**
  The §9 energy balance must book solid-side heat via volume integrals
  (source power, dU/dt from `volFieldValue`) and take interface fluxes from
  the **fluid side**, where the thermo is isotropic and the accessor is fine.
- Boundary conditions that convert flux↔gradient via scalar kappa
  (`externalWallHeatFluxTemperature`, coupled BCs with
  `kappaMethod solidThermo`) are equally wrong on cell regions — coupled
  interfaces use `kappaMethod directionalSolidThermo`, and no flux-type BC
  goes directly on an anisotropic solid.
- The gate keeps a sentinel assertion on the FO output; if an OpenFOAM
  update ever fixes the accessor, the sentinel flags it for re-evaluation.
- Template ancestor chosen:
  `$FOAM_TUTORIALS/heatTransfer/chtMultiRegionFoam/snappyMultiRegionHeater`
  (snappy + multi-region CHT, same meshing workflow as ours).

## Python

Front-end venv: `.venv/` at repo root, packages in `requirements.txt`.
Record `pip freeze` output here once results are produced.

## Instance types used for results

| Result set | Machine | Cores/ranks | Notes |
|---|---|---|---|
| (none yet) | | | |
