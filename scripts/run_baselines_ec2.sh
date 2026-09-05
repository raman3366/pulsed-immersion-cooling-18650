#!/usr/bin/env bash
# Phase-5a baseline block (tmux entry, ON the VM): two balanced lanes at
# 16 ranks each on the 32-core box.
#   lane1: fine-GCI Q2 (~4h) -> medium Q1 (~2h)
#   lane2: medium Q2 (~2h) -> medium Q3 (~2h) -> coarse-GCI Q2 (~1h)
# Baselines run on the MEDIUM duct grid (§4.2); the Q2 coarse/fine pair is
# the duct-GCI spot-check.
set -eo pipefail
cd "$(dirname "$0")/.."

M=cases/matrix
LANE="${1:?usage: run_baselines_ec2.sh lane1|lane2|prepare}"

clone_grid() {                       # $1 = src matrix case, $2 = dst, $3 = grid
    rm -rf "$2"; cp -r "$1" "$2"
    echo "export GRID=$3" >> "$2/case.env"
}

case "$LANE" in
  prepare)
    .venv/bin/python scripts/generate_cases.py --blocks steady 2>/dev/null \
        || python3 scripts/generate_cases.py --blocks steady
    for c in "$M"/steady_*_C3; do echo "export GRID=medium" >> "$c/case.env"; done
    clone_grid "$M/steady_f0.00_A0.00_Q2_C3" "$M/gci_duct_coarse_Q2" coarse
    sed -i 's/^export GRID=medium$//' "$M/gci_duct_coarse_Q2/case.env"
    clone_grid "$M/steady_f0.00_A0.00_Q2_C3" "$M/gci_duct_fine_Q2" fine
    sed -i 's/^export GRID=medium$//' "$M/gci_duct_fine_Q2/case.env"
    echo "prepared: $(ls $M)" ;;
  lane1)
    echo "=== lane1: fine-GCI Q2 ($(date)) ==="
    bash scripts/run_ec2.sh "$M/gci_duct_fine_Q2" 16
    echo "=== lane1: medium Q1 ($(date)) ==="
    bash scripts/run_ec2.sh "$M/steady_f0.00_A0.00_Q1_C3" 16
    echo "=== lane1 COMPLETE ($(date)) ===" ;;
  lane2)
    echo "=== lane2: medium Q2 ($(date)) ==="
    bash scripts/run_ec2.sh "$M/steady_f0.00_A0.00_Q2_C3" 16
    echo "=== lane2: medium Q3 ($(date)) ==="
    bash scripts/run_ec2.sh "$M/steady_f0.00_A0.00_Q3_C3" 16
    echo "=== lane2: coarse-GCI Q2 ($(date)) ==="
    bash scripts/run_ec2.sh "$M/gci_duct_coarse_Q2" 16
    echo "=== lane2 COMPLETE ($(date)) ===" ;;
  *) echo "unknown lane"; exit 1 ;;
esac
