#!/usr/bin/env bash
# Duct time-step independence check (tmux entry, ON the VM). Motivation
# (2026-09-01): sweep T_max tracks the solver dt (median 0.048/0.025/0.0125 s
# for steady/1 Hz/2 Hz) rather than the pulsation amplitude. Re-run the
# steady Q2 baseline with the maxDeltaT cap that the 1 Hz and 2 Hz cases
# actually ran at; compare T_max / dT against steady_f0.00_A0.00_Q2_C3
# (median dt 0.0485, Co-limited at maxCo 1.0).
#   lane1: dt cap 0.025 (~1.3 h at 16 ranks), then the best cheap sweep
#          point (sine 0.1 Hz A0.6) at dt cap 0.0125 (~2.7 h) — is the
#          UNIFORMITY result dt-robust at the 2 Hz cases' dt?
#   lane2: steady dt cap 0.0125 (~2.7 h)
set -eo pipefail
cd "$(dirname "$0")/.."
M=cases/matrix
LANE="${1:?usage: run_dtcheck_ec2.sh prepare|lane1|lane2}"

clone_dt() {                         # $1 = src case, $2 = dst, $3 = maxDeltaT
    rm -rf "$2"; cp -r "$1" "$2"
    rm -rf "$2"/processor* "$2"/postProcessing "$2"/log.* "$2"/.claimed
    find "$2" -maxdepth 1 -regex '.*/[0-9][0-9.e+-]*' ! -name 0 -exec rm -rf {} +
    grep -v '^export MAXDT=' "$2/case.env" > "$2/case.env.tmp" || true   # portable (BSD/GNU)
    echo "export MAXDT=$3" >> "$2/case.env.tmp"; mv "$2/case.env.tmp" "$2/case.env"
}

case "$LANE" in
  prepare)
    if [ ! -d "$M/steady_f0.00_A0.00_Q2_C3" ]; then      # wiped in the disk-full clean-up
        .venv/bin/python scripts/generate_cases.py --blocks steady
        for c in "$M"/steady_*_C3; do echo "export GRID=medium" >> "$c/case.env"; done
    fi
    clone_dt "$M/steady_f0.00_A0.00_Q2_C3" "$M/dtchk_dt0.0250_Q2" 0.025
    clone_dt "$M/steady_f0.00_A0.00_Q2_C3" "$M/dtchk_dt0.0125_Q2" 0.0125
    clone_dt "$M/sine_f0.10_A0.60_Q2_C3" "$M/dtchk_sine_f0.10_A0.60_dt0.0125" 0.0125
    grep -H MAXDT "$M"/dtchk_*/case.env ;;
  lane1)
    echo "=== lane1: steady Q2 @ maxDeltaT 0.025 ($(date)) ==="
    bash scripts/run_ec2.sh "$M/dtchk_dt0.0250_Q2" 16
    echo "=== lane1: sine 0.1 Hz A0.6 @ maxDeltaT 0.0125 ($(date)) ==="
    bash scripts/run_ec2.sh "$M/dtchk_sine_f0.10_A0.60_dt0.0125" 16
    echo "=== lane1 COMPLETE ($(date)) ===" ;;
  lane2)
    echo "=== lane2: steady Q2 @ maxDeltaT 0.0125 ($(date)) ==="
    bash scripts/run_ec2.sh "$M/dtchk_dt0.0125_Q2" 16
    echo "=== lane2 COMPLETE ($(date)) ===" ;;
  *) echo "unknown lane"; exit 1 ;;
esac
