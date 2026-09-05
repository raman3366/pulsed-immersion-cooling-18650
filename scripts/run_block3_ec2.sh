#!/usr/bin/env bash
# Block 3 = the PRODUCTION MATRIX with the §4.6 `backward` scheme (the Euler
# runs of 2026-08-31/09-01 are superseded). tmux entry ON the VM, two lanes.
# Env: STEADY_MAXDT (from the backward dt pair; default 0.05).
#   lane1: square smoke (20 s) -> steady Q1,Q2 -> sine f0.1 x3, f0.25 x3,
#          f0.5 x3 -> square 1 Hz x3 -> fields sine 0.1 Hz A0.6
#   lane2: steady Q3 -> anchors Q4,Q5 -> sine f1 x3, f2 x3 -> square 0.5 Hz x3
#          -> fields sine 2 Hz A0.6
# (~28 cases, ~60 lane-hours; balanced ~30 h each at 16 ranks)
set -eo pipefail
cd "$(dirname "$0")/.."
M=cases/matrix
LANE="${1:?usage: run_block3_ec2.sh prepare|lane1|lane2}"
export STEADY_MAXDT="${STEADY_MAXDT:-0.05}"
export NOUTER="${NOUTER:-}"      # PIMPLE outer correctors written into every case.env by the generator

clean_clone() { rm -rf "$2"; cp -r "$1" "$2"; rm -rf "$2"/processor* "$2"/postProcessing "$2"/log.* "$2"/.claimed "$2"/.keepfields "$2"/keep
    find "$2" -maxdepth 1 -regex '.*/[0-9][0-9.e+-]*' ! -name 0 -exec rm -rf {} +; }
set_cd() { sed -i "s|^$2 .*|$2 $3;|" "$1/system/controlDict"; }
run() { echo "=== $1 ($(date)) ==="; bash scripts/run_ec2.sh "$M/$1" 16; }
run_square() { if [ -f SQUARE_SMOKE_FAILED ]; then echo ">>> square skipped (smoke failed): $1"; return 0; fi; run "$1"; }
run_fields() {   # $1 sweep case, $2 period [s]: stage 1 to 870 s keeping processors, stage 2 870->900 writes every P/4
    src="$M/$1"; dst="$M/fields_$1"
    echo "=== fields stage 1: $dst -> 870 s ($(date)) ==="
    clean_clone "$src" "$dst"; touch "$dst/.keepfields"; set_cd "$dst" endTime 870
    bash scripts/run_ec2.sh "$dst" 16
    grep -q '^End$' "$dst/log.chtMultiRegionFoam" || { echo "!!! stage 1 did not reach End"; return 1; }
    echo "=== fields stage 2: 870 -> 900 s ($(date)) ==="
    set_cd "$dst" endTime 900; set_cd "$dst" writeInterval "$(python3 -c "print($2/4)")"; set_cd "$dst" purgeWrite 8
    bash scripts/run_ec2_restart.sh "$dst" 16
    ( cd "$dst" && reconstructPar -allRegions -newTimes > log.reconstructPar 2>&1 && rm -rf processor* && echo ">>> reconstructed: $(ls -d [0-9]* | tr '\n' ' ')" )
}

case "$LANE" in
  prepare)
    echo "STEADY_MAXDT=$STEADY_MAXDT NOUTER=${NOUTER:-default}"
    .venv/bin/python scripts/generate_cases.py --blocks steady anchors sine square
    for c in "$M"/steady_*_C3 "$M"/sine_*_C3 "$M"/square_*_C3; do echo "export GRID=medium" >> "$c/case.env"; done
    clean_clone "$M/square_f0.50_D0.25_Q2_C3" "$M/square_smoke"; set_cd "$M/square_smoke" endTime 20
    rm -f SQUARE_SMOKE_FAILED
    grep -h "ddtSchemes" "$M/steady_f0.00_A0.00_Q2_C3/makePhysics.py" | head -1
    grep -H MAXDT "$M"/steady_f0.00_A0.00_Q2_C3/case.env "$M"/sine_f0.10_A0.20_Q2_C3/case.env "$M"/sine_f2.00_A0.20_Q2_C3/case.env ;;
  lane1)
    echo "=== square smoke gate ($(date)) ==="
    if bash scripts/run_ec2.sh "$M/square_smoke" 16 && grep -q '^End$' "$M/square_smoke/log.chtMultiRegionFoam" && ! grep -q 'FOAM FATAL' "$M/square_smoke/log.chtMultiRegionFoam"; then echo ">>> square smoke PASSED"; else touch SQUARE_SMOKE_FAILED; echo "!!! square smoke FAILED — square block skipped"; fi
    run steady_f0.00_A0.00_Q1_C3; run steady_f0.00_A0.00_Q2_C3
    for f in 0.10 0.25 0.50; do for A in 0.20 0.40 0.60; do run "sine_f${f}_A${A}_Q2_C3"; done; done
    for D in 0.25 0.50 0.75; do run_square "square_f1.00_D${D}_Q2_C3"; done
    run_fields sine_f0.10_A0.60_Q2_C3 10
    echo "=== lane1 COMPLETE ($(date)) ===" ;;
  lane2)
    run steady_f0.00_A0.00_Q3_C3; run steady_f0.00_A0.00_Q4_C3; run steady_f0.00_A0.00_Q5_C3
    for f in 1.00 2.00; do for A in 0.20 0.40 0.60; do run "sine_f${f}_A${A}_Q2_C3"; done; done
    for D in 0.25 0.50 0.75; do run_square "square_f0.50_D${D}_Q2_C3"; done
    run_fields sine_f2.00_A0.60_Q2_C3 0.5
    echo "=== lane2 COMPLETE ($(date)) ===" ;;
  *) echo "unknown lane"; exit 1 ;;
esac
