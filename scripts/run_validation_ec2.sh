#!/usr/bin/env bash
# Stage-5 validation driver (tmux entry point ON the VM).
#   bash scripts/run_validation_ec2.sh baseline   # k = 0.068 (D-07 baseline)
#   bash scripts/run_validation_ec2.sh k06        # k = 0.6   (D-07 sensitivity)
#   bash scripts/run_validation_ec2.sh both       # sequential (16-core VMs)
# On a 32-core machine run 'baseline' and 'k06' in two tmux sessions
# concurrently, RANKS=16 each.
set -eo pipefail
cd "$(dirname "$0")/.."

BASE=cases/validation/liu2023-static
SENS=cases/validation/liu2023-static-k06
BETA08=cases/validation/liu2023-static-beta08
RANKS="${RANKS:-16}"
MODE="${1:-both}"

clone_case() {   # $1 = destination
    DEST="$1"
    rm -rf "$DEST"
    mkdir -p "$DEST"
    for f in Allrun Allrun.pre makePhysics.py makeMesh.py 0.orig system \
             constant/regionProperties constant/g \
             constant/fluid/turbulenceProperties; do
        mkdir -p "$DEST/$(dirname "$f")"
        cp -r "$BASE/$f" "$DEST/$f"
    done
    for r in fluid cell0 cell1 cell2 cell3 cell4 cell5; do
        mkdir -p "$DEST/constant/$r"
        cp "$BASE/constant/$r/radiationProperties" "$DEST/constant/$r/"
    done
    # scrub generated/state that came with system/
    rm -rf "$DEST"/system/cell* "$DEST"/system/monitors "$DEST"/system/decomposeParDict
}

case "$MODE" in
  baseline)
    echo "=== k = 0.068 baseline ($(date)) ==="
    bash scripts/run_ec2.sh "$BASE" "$RANKS"
    echo "=== baseline COMPLETE ($(date)) ===" ;;
  prepare)
    clone_case "$SENS"
    echo "k06 clone prepared" ;;
  k06)
    echo "=== k = 0.6 sensitivity ($(date)) ==="
    # clone must be prepared BEFORE concurrent launches (race with baseline
    # wiping itself); 'both' and 'prepare' do it serially
    [ -d "$SENS/system" ] || clone_case "$SENS"
    COOLANT_K=0.6 bash scripts/run_ec2.sh "$SENS" "$RANKS"
    echo "=== k06 COMPLETE ($(date)) ===" ;;
  beta08)
    echo "=== beta = 0.8e-3 sensitivity ($(date)) ==="
    clone_case "$BETA08"
    BETA=0.8e-3 bash scripts/run_ec2.sh "$BETA08" "$RANKS"
    echo "=== beta08 COMPLETE ($(date)) ===" ;;
  temporal)
    # coarse grid, maxDi 100 (same numerics as GCI medium/fine): serves the
    # §4.8 time-step check vs the maxDi-10 coarse run AND GCI consistency
    echo "=== temporal/coarse-maxDi100 ($(date)) ==="
    clone_case cases/validation/liu2023-static-dt
    bash scripts/run_ec2.sh cases/validation/liu2023-static-dt "$RANKS"
    echo "=== temporal COMPLETE ($(date)) ===" ;;
  both)
    clone_case "$SENS"
    "$0" baseline
    "$0" k06
    echo "=== both validation runs complete ($(date)) ===" ;;
  *) echo "unknown mode '$MODE'"; exit 1 ;;
esac
