#!/usr/bin/env bash
# Parallel production driver (runs ON the VM inside the OpenFOAM env):
#   openfoam2606 -c "bash scripts/run_ec2.sh cases/validation/liu2023-static [RANKS]"
# Fresh start: Allrun.pre (wipes + remeshes) -> decomposePar -> mpirun.
# To RESUME after an interruption use run_ec2_restart.sh — this script WIPES.
# Env passthrough: GRID, COOLANT_K (see Allrun.pre).
set -eo pipefail   # no -u: RunFunctions references unset FOAM_LD_LIBRARY_PATH
[ -n "${WM_PROJECT_DIR:-}" ] || { echo "source the OpenFOAM env first"; exit 1; }

CASE="${1:?usage: run_ec2.sh <case-dir> [ranks]}"
RANKS="${2:-16}"                       # c7i.8xlarge: 16 PHYSICAL cores, never 32
# a case claimed by another lane (touch $CASE/.claimed) is skipped — lets an
# idle lane pick up a queued case without editing a running lane script
[ -f "$CASE/.claimed" ] && { echo ">>> $CASE claimed by another lane — skipping"; exit 0; }
cd "$CASE"

./Allrun.pre

cat > system/decomposeParDict <<EOF
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      decomposeParDict;
}
numberOfSubdomains  $RANKS;
method              scotch;
EOF

. "$WM_PROJECT_DIR"/bin/tools/RunFunctions
runApplication decomposePar -allRegions -decomposeParDict system/decomposeParDict

start=$(date +%s)
mpirun -np "$RANKS" chtMultiRegionFoam -parallel > log.chtMultiRegionFoam 2>&1
echo ">>> solver wall clock: $(( ($(date +%s) - start) / 60 )) min ($RANKS ranks)"
grep -c "^Time = " log.chtMultiRegionFoam | xargs echo ">>> timesteps:"
# disk hygiene: a completed case's decomposed fields are not needed (metrics
# come from postProcessing/ + log); 15 cases x full histories filled 30 GB
# a case marked .keepfields (field-writing re-runs, D-15) keeps its processor
# dirs for the restart stage / reconstructPar in run_block2_ec2.sh
if grep -q "^End$" log.chtMultiRegionFoam; then
    if [ -f .keepfields ]; then echo ">>> .keepfields: processor dirs kept"
    else rm -rf processor*; echo ">>> processor dirs removed (case complete)"; fi
fi
