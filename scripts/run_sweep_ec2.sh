#!/usr/bin/env bash
# Sine-sweep block (tmux entry ON the VM): 15 cases in two cost-balanced
# lanes at 16 ranks each. High-frequency cases are dt-limited (E4) and
# therefore long, so each lane gets a mix.
#   bash scripts/run_sweep_ec2.sh prepare | lane1 | lane2
set -eo pipefail
cd "$(dirname "$0")/.."
M=cases/matrix
case "${1:?prepare|lane1|lane2}" in
  prepare)
    python3 scripts/generate_cases.py --blocks sine
    for c in "$M"/sine_*; do echo "export GRID=medium" >> "$c/case.env"; done
    ls "$M" | grep -c sine_ ;;
  lane1)
    for c in sine_f2.00_A0.40 sine_f0.10_A0.20 sine_f1.00_A0.20 sine_f0.25_A0.40 \
             sine_f0.50_A0.60 sine_f2.00_A0.20 sine_f0.10_A0.60 sine_f1.00_A0.60; do
      echo "=== $c ($(date)) ==="; bash scripts/run_ec2.sh "$M/${c}_Q2_C3" 16
    done; echo "=== lane1 COMPLETE ($(date)) ===" ;;
  lane2)
    for c in sine_f2.00_A0.60 sine_f0.10_A0.40 sine_f1.00_A0.40 sine_f0.25_A0.20 \
             sine_f0.50_A0.20 sine_f0.25_A0.60 sine_f0.50_A0.40; do
      echo "=== $c ($(date)) ==="; bash scripts/run_ec2.sh "$M/${c}_Q2_C3" 16
    done; echo "=== lane2 COMPLETE ($(date)) ===" ;;
esac
