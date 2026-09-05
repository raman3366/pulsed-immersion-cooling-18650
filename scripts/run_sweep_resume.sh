#!/usr/bin/env bash
# Resume the disk-full-interrupted sweep: two lanes.
#   lane1: resume f2.0 A0.2 from checkpoint (long)
#   lane2: resume f0.25 A0.6 (short), then the 3 never-started cases fresh
set -eo pipefail
cd "$(dirname "$0")/.."
M=cases/matrix
finish() { grep -q "^End$" "$1/log.chtMultiRegionFoam" && rm -rf "$1"/processor* || true; }
case "${1:?lane1|lane2}" in
  lane1)
    echo "=== resume sine_f2.00_A0.20 ($(date)) ==="
    bash scripts/run_ec2_restart.sh "$M/sine_f2.00_A0.20_Q2_C3" 16; finish "$M/sine_f2.00_A0.20_Q2_C3"
    echo "=== lane1 COMPLETE ($(date)) ===" ;;
  lane2)
    echo "=== resume sine_f0.25_A0.60 ($(date)) ==="
    bash scripts/run_ec2_restart.sh "$M/sine_f0.25_A0.60_Q2_C3" 16; finish "$M/sine_f0.25_A0.60_Q2_C3"
    for c in sine_f0.10_A0.60 sine_f0.50_A0.40 sine_f1.00_A0.60; do
      echo "=== $c ($(date)) ==="; bash scripts/run_ec2.sh "$M/${c}_Q2_C3" 16
    done
    echo "=== lane2 COMPLETE ($(date)) ===" ;;
esac
