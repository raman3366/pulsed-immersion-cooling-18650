#!/usr/bin/env bash
# backward (2nd-order ddt, §4.6) time-step convergence check on the duct,
# tmux entry ON the VM. Steady Q2 at maxDeltaT 0.05 / 0.025 / 0.0125.
# Motivation: Euler sequence diverged (T_max 31.28/31.46/31.82 C) — temporal
# numerical diffusion in the plumes. Acceptance: successive T_max within
# 0.05 K -> production dt cap chosen at the coarser of the agreeing pair.
#   lane2: dt 0.05 (~1.3 h) -> dt 0.025 (~2.2 h)      lane1: dt 0.0125 (~4.4 h)
set -eo pipefail
cd "$(dirname "$0")/.."
M=cases/matrix
LANE="${1:?usage: run_bwdcheck_ec2.sh prepare|lane1|lane2}"
clone() {   # $1 src, $2 dst, $3 maxDeltaT
    rm -rf "$2"; cp -r "$1" "$2"
    rm -rf "$2"/processor* "$2"/postProcessing "$2"/log.* "$2"/.claimed "$2"/keep
    find "$2" -maxdepth 1 -regex '.*/[0-9][0-9.e+-]*' ! -name 0 -exec rm -rf {} +
    grep -v '^export MAXDT=' "$2/case.env" > "$2/case.env.tmp" || true
    printf 'export MAXDT=%s\nexport DDT=backward\n' "$3" >> "$2/case.env.tmp"; mv "$2/case.env.tmp" "$2/case.env"
}
case "$LANE" in
  prepare)
    # ALWAYS regenerate from the current template: a clone inherits the case's
    # own Allrun.pre/makePhysics.py, so stale generated cases silently keep the
    # old scheme (bit us 2026-09-01: first backward launch rendered Euler)
    .venv/bin/python scripts/generate_cases.py --blocks steady
    for c in "$M"/steady_*_C3; do echo "export GRID=medium" >> "$c/case.env"; done
    clone "$M/steady_f0.00_A0.00_Q2_C3" "$M/bwd_dt0.0500_Q2" 0.05
    clone "$M/steady_f0.00_A0.00_Q2_C3" "$M/bwd_dt0.0250_Q2" 0.025
    clone "$M/steady_f0.00_A0.00_Q2_C3" "$M/bwd_dt0.0125_Q2" 0.0125
    grep -H "MAXDT\|DDT" "$M"/bwd_*/case.env ;;
  lane2)
    for d in 0.0500 0.0250; do echo "=== bwd dt $d ($(date)) ==="; bash scripts/run_ec2.sh "$M/bwd_dt${d}_Q2" 16; done
    echo "=== lane2 COMPLETE ($(date)) ===" ;;
  lane1)
    echo "=== bwd dt 0.0125 ($(date)) ==="; bash scripts/run_ec2.sh "$M/bwd_dt0.0125_Q2" 16
    echo "=== lane1 COMPLETE ($(date)) ===" ;;
  *) echo "unknown lane"; exit 1 ;;
esac
