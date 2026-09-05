#!/usr/bin/env bash
# RESUME an interrupted parallel run from the latest checkpoint. Wipes NOTHING
# (the spot-interruption safety net: startFrom latestTime + processor dirs).
#   openfoam2606 -c "bash scripts/run_ec2_restart.sh <case-dir> [ranks]"
set -euo pipefail
[ -n "${WM_PROJECT_DIR:-}" ] || { echo "source the OpenFOAM env first"; exit 1; }

CASE="${1:?usage: run_ec2_restart.sh <case-dir> [ranks]}"
RANKS="${2:-16}"
cd "$CASE"
[ -d processor0 ] || { echo "no processor dirs — nothing to resume"; exit 1; }

start=$(date +%s)
mpirun -np "$RANKS" chtMultiRegionFoam -parallel >> log.chtMultiRegionFoam 2>&1
echo ">>> resumed solver wall clock: $(( ($(date +%s) - start) / 60 )) min"
