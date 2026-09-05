#!/usr/bin/env bash
# VM-SIDE orchestrator (tmux session 'orch') — survives Mac disconnects.
# 1. when the Euler sine dt case finishes -> launch backward dt 0.0125 (lane1)
# 2. score backward 0.05 / 0.025 -> verdict -> block-3 prepare + launch lane2
# 3. when backward 0.0125 finishes -> score -> launch block-3 lane1
# 4. when both block-3 lanes complete -> VM-side gates/scoring -> BLOCK3_DONE
# Log: orchestrate.out. Idempotent launches (tmux has-session guards).
set -uo pipefail
cd "$(dirname "$0")/.."
M=cases/matrix; PY=.venv/bin/python
W1="tight-duct early window not export-free (7mm ceiling current); ratio flat across 4.8x refinement = physical export not leak"
W2="adjustTimeStep lag on buoyant gap jets; PIMPLE stable, clean End"
log() { echo "[$(date -u +%m-%d\ %H:%M) UTC] $*"; }
wait_end() { until grep -q '^End$' "$M/$1/log.chtMultiRegionFoam" 2>/dev/null; do sleep 120; done; log "$1 reached End"; }
wait_file_has() { until grep -q "$2" "$1" 2>/dev/null; do sleep 120; done; }
score() { $PY scripts/post/extract_metrics.py "$M/$1" --label "td_$1" --waive-e1 "$W1" --waive-e2 "$W2" > "$M/$1/log.metrics" 2>&1 \
            && log "$1 gates OK ($(grep -o 'ratio [0-9.]*' "$M/$1/log.metrics" | head -1))" || log "$1 GATES FAILED: $(tail -1 "$M/$1/log.metrics")"
          $PY scripts/post/pec.py "$M/$1" | head -1; }
tmax() { $PY -c "import pandas as pd; print(pd.read_csv('data/processed/pareto.csv').set_index('case').loc['$1'].Tmax_C)"; }
launch() {  # $1 tmux name, $2 script, $3 lane, $4 out, [$5 cap]
    tmux has-session -t "$1" 2>/dev/null && { log "$1 already running"; return 0; }
    tmux new-session -d -s "$1" "STEADY_MAXDT=${5:-0.05} openfoam2606 -c \"bash scripts/$2 $3\" > $4 2>&1"; log "launched $1: $2 $3 (cap ${5:-n/a})"; }

# 1. backward dt 0.0125 on lane1 after the Euler sine case
wait_file_has dtcheck-lane1.out 'lane1 COMPLETE'; score dtchk_sine_f0.10_A0.60_dt0.0125
launch bw1 run_bwdcheck_ec2.sh lane1 bwdcheck-lane1.out
# 2. pair verdict
wait_end bwd_dt0.0500_Q2; score bwd_dt0.0500_Q2
wait_end bwd_dt0.0250_Q2; score bwd_dt0.0250_Q2
T05=$(tmax bwd_dt0.0500_Q2); T025=$(tmax bwd_dt0.0250_Q2); D1=$($PY -c "print(round(abs($T05-$T025),4))")
log "BACKWARD PAIR: Tmax(0.05)=$T05 Tmax(0.025)=$T025 |diff|=$D1 K (Euler: 31.282/31.464/31.818)"
CAP=""
if $PY -c "import sys; sys.exit(0 if $D1 <= 0.05 else 1)"; then
    CAP=0.05; log "ACCEPT: converged at dt 0.05 -> STEADY_MAXDT=$CAP"
    STEADY_MAXDT=$CAP bash scripts/run_block3_ec2.sh prepare > block3-prepare.out 2>&1 && log "block3 prepared" || log "!!! block3 prepare FAILED: $(tail -2 block3-prepare.out)"
    launch b3l2 run_block3_ec2.sh lane2 block3-lane2.out $CAP
    wait_file_has bwdcheck-lane1.out 'lane1 COMPLETE'; score bwd_dt0.0125_Q2
    T0125=$(tmax bwd_dt0.0125_Q2); log "third point Tmax(0.0125)=$T0125 |0.025-0.0125|=$($PY -c "print(round(abs($T025-$T0125),4))") K"
    launch b3l1 run_block3_ec2.sh lane1 block3-lane1.out $CAP
else
    log "HOLD: pair differs by $D1 K — waiting for dt 0.0125"
    wait_file_has bwdcheck-lane1.out 'lane1 COMPLETE'; score bwd_dt0.0125_Q2
    T0125=$(tmax bwd_dt0.0125_Q2); D2=$($PY -c "print(round(abs($T025-$T0125),4))"); log "SECOND PAIR: Tmax(0.0125)=$T0125 |diff|=$D2 K"
    if $PY -c "import sys; sys.exit(0 if $D2 <= 0.05 else 1)"; then
        CAP=0.025; log "ACCEPT at dt 0.025 -> STEADY_MAXDT=$CAP"
        STEADY_MAXDT=$CAP bash scripts/run_block3_ec2.sh prepare > block3-prepare.out 2>&1 && log "block3 prepared" || log "!!! prepare FAILED"
        launch b3l2 run_block3_ec2.sh lane2 block3-lane2.out $CAP; launch b3l1 run_block3_ec2.sh lane1 block3-lane1.out $CAP
    else
        log "!!! NOT CONVERGED with backward (diffs $D1, $D2 K) — block 3 NOT launched; user decision needed"; touch BLOCK3_HELD; exit 2
    fi
fi
# 4. close-out on the VM when both lanes finish
wait_file_has block3-lane1.out 'lane1 COMPLETE'; wait_file_has block3-lane2.out 'lane2 COMPLETE'
log "BLOCK 3 COMPLETE — VM-side scoring"
for c in "$M"/steady_*_C3 "$M"/sine_*_C3 "$M"/square_f*_C3; do n=$(basename "$c"); grep -q '^End$' "$c/log.chtMultiRegionFoam" 2>/dev/null && score "$n" || log "SKIP $n (no End)"; done
$PY scripts/post/sweep_summary.py > sweep_summary.out 2>&1 && log "sweep summary written" || log "sweep_summary failed: $(tail -1 sweep_summary.out)"
touch BLOCK3_DONE; log "BLOCK3_DONE (cap $CAP). Mac: pull data/processed + postProcessing, then stop the VM."
