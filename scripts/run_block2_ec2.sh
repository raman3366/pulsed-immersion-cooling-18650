#!/usr/bin/env bash
# Block 2 (D-15), tmux entry ON the VM, two lanes at 16 ranks:
#   lane1: square smoke gate (20 s) -> steady Q1 @dt0.0125 -> anchor Q5 (500)
#          -> square 1 Hz x3
#   lane2: steady Q3 @dt0.0125 -> anchor Q4 (250) -> square 0.5 Hz x3
#          -> field re-runs: sine 0.1 Hz A0.6, sine 2 Hz A0.6 (two-stage:
#             run to 870 s keeping processor dirs, then restart 870->900 with
#             writes every quarter period, purgeWrite 8, reconstructPar)
# Steady Q2 @dt0.0125 = dtchk_dt0.0125_Q2 (already run). Square cases are
# skipped if the smoke gate fails (flag file SQUARE_SMOKE_FAILED).
set -eo pipefail
cd "$(dirname "$0")/.."
M=cases/matrix
LANE="${1:?usage: run_block2_ec2.sh prepare|lane1|lane2}"

clean_clone() {                      # $1 = src case, $2 = dst
    rm -rf "$2"; cp -r "$1" "$2"
    rm -rf "$2"/processor* "$2"/postProcessing "$2"/log.* "$2"/.claimed "$2"/.keepfields "$2"/keep
    find "$2" -maxdepth 1 -regex '.*/[0-9][0-9.e+-]*' ! -name 0 -exec rm -rf {} +
}
set_cd() { sed -i "s|^$2 .*|$2 $3;|" "$1/system/controlDict"; }   # key value

run_square() {                       # skip the whole square block on smoke failure
    if [ -f SQUARE_SMOKE_FAILED ]; then echo ">>> square block skipped (smoke failed): $1"; return 0; fi
    echo "=== $1 ($(date)) ==="; bash scripts/run_ec2.sh "$M/$1" 16
}

run_fields() {                       # $1 = sweep case name, $2 = period [s]
    src="$M/$1"; dst="$M/fields_$1"
    echo "=== fields stage 1: $dst to 870 s ($(date)) ==="
    clean_clone "$src" "$dst"; touch "$dst/.keepfields"
    set_cd "$dst" endTime 870
    bash scripts/run_ec2.sh "$dst" 16
    grep -q '^End$' "$dst/log.chtMultiRegionFoam" || { echo "!!! stage 1 did not reach End"; return 1; }
    echo "=== fields stage 2: 870 -> 900 s, writes every $2/4 s, purgeWrite 8 ($(date)) ==="
    set_cd "$dst" endTime 900
    set_cd "$dst" writeInterval "$(python3 -c "print($2/4)")"
    set_cd "$dst" purgeWrite 8
    bash scripts/run_ec2_restart.sh "$dst" 16
    ( cd "$dst" && reconstructPar -allRegions -newTimes > log.reconstructPar 2>&1 && rm -rf processor* && echo ">>> reconstructed: $(ls -d [0-9]* | tr '\n' ' ')" )
}

case "$LANE" in
  prepare)
    .venv/bin/python scripts/generate_cases.py --blocks steady anchors square
    for c in "$M"/steady_*_C3 "$M"/square_*_C3; do echo "export GRID=medium" >> "$c/case.env"; done
    clean_clone "$M/square_f0.50_D0.25_Q2_C3" "$M/square_smoke"; set_cd "$M/square_smoke" endTime 20
    rm -f SQUARE_SMOKE_FAILED
    grep -H MAXDT "$M"/steady_*/case.env "$M"/square_*/case.env ;;
  lane1)
    echo "=== square smoke gate ($(date)) ==="
    if bash scripts/run_ec2.sh "$M/square_smoke" 16 && grep -q '^End$' "$M/square_smoke/log.chtMultiRegionFoam" \
       && ! grep -q 'FOAM FATAL' "$M/square_smoke/log.chtMultiRegionFoam"; then echo ">>> square smoke PASSED"
    else touch SQUARE_SMOKE_FAILED; echo "!!! square smoke FAILED — square block will be skipped"; fi
    echo "=== steady Q1 @dt0.0125 ($(date)) ==="; bash scripts/run_ec2.sh "$M/steady_f0.00_A0.00_Q1_C3" 16
    echo "=== anchor Q5 500 mL/min ($(date)) ==="; bash scripts/run_ec2.sh "$M/steady_f0.00_A0.00_Q5_C3" 16
    for D in 0.25 0.50 0.75; do run_square "square_f1.00_D${D}_Q2_C3"; done
    echo "=== lane1 COMPLETE ($(date)) ===" ;;
  lane2)
    echo "=== steady Q3 @dt0.0125 ($(date)) ==="; bash scripts/run_ec2.sh "$M/steady_f0.00_A0.00_Q3_C3" 16
    echo "=== anchor Q4 250 mL/min ($(date)) ==="; bash scripts/run_ec2.sh "$M/steady_f0.00_A0.00_Q4_C3" 16
    for D in 0.25 0.50 0.75; do run_square "square_f0.50_D${D}_Q2_C3"; done
    run_fields sine_f0.10_A0.60_Q2_C3 10
    run_fields sine_f2.00_A0.60_Q2_C3 0.5
    echo "=== lane2 COMPLETE ($(date)) ===" ;;
  *) echo "unknown lane"; exit 1 ;;
esac
