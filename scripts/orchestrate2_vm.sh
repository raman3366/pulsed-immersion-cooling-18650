#!/usr/bin/env bash
# VM-side orchestrator v2 (tmux 'orch2') — replaces orchestrate_block3_vm.sh
# after the backward pair failed to converge (31.446 -> 31.677 K, dt .039->.025).
# Hypothesis: region-coupling lag (nOuterCorrectors 2). Recipe under test:
# backward + NOUTER=6 at cap 0.05.
#   1. bw1 (backward 0.0125) completes -> score (third point) -> launch diag2
#      = backward nOuter6 at dt 0.025 on lane 1
#   2. diag (nOuter6 @0.05, running on lane 2) + diag2 scored -> verdict:
#      |T(0.05)-T(0.025)| <= 0.05 K AND T_nOC6(0.05) - 31.446 > 0.1 K
#      -> block 3 prepared with STEADY_MAXDT=0.05 NOUTER=6, both lanes launched
#      else BLOCK3_HELD
#   3. both block-3 lanes complete -> VM-side scoring -> BLOCK3_DONE
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
clone() {  # $1 src $2 dst $3 extra case.env lines (newline-separated)
    rm -rf "$2"; cp -r "$1" "$2"; rm -rf "$2"/processor* "$2"/postProcessing "$2"/log.* "$2"/keep "$2"/.claimed
    find "$2" -maxdepth 1 -regex '.*/[0-9][0-9.e+-]*' ! -name 0 -exec rm -rf {} +
    cp cases/template/Allrun.pre "$2/Allrun.pre"; printf '%b\n' "$3" >> "$2/case.env"; }
launch() {  # $1 tmux, $2 cmd, $3 out
    tmux has-session -t "$1" 2>/dev/null && { log "$1 already running"; return 0; }
    tmux new-session -d -s "$1" "openfoam2606 -c \"$2\" > $3 2>&1"; log "launched $1: $2"; }

# 1. third backward point, then diag2 on lane 1
wait_file_has bwdcheck-lane1.out 'lane1 COMPLETE'; score bwd_dt0.0125_Q2
log "backward sequence: $(tmax bwd_dt0.0500_Q2) / $(tmax bwd_dt0.0250_Q2) / $(tmax bwd_dt0.0125_Q2) C at dt .039/.025/.0125"
clone "$M/bwd_dt0.0250_Q2" "$M/bwd_dt0.0250_nOC6_Q2" "export NOUTER=6"
launch diag2 "bash scripts/run_ec2.sh $M/bwd_dt0.0250_nOC6_Q2 16" diag2-nOC6.out
# 2. verdict on the nOuter=6 pair
wait_end bwd_dt0.0500_nOC6_Q2; score bwd_dt0.0500_nOC6_Q2
wait_end bwd_dt0.0250_nOC6_Q2; score bwd_dt0.0250_nOC6_Q2
TA=$(tmax bwd_dt0.0500_nOC6_Q2); TB=$(tmax bwd_dt0.0250_nOC6_Q2); D=$($PY -c "print(round(abs($TA-$TB),4))"); LIFT=$($PY -c "print(round($TA-31.446,4))")
log "nOUTER=6 PAIR: Tmax(0.05)=$TA Tmax(0.025)=$TB |diff|=$D K; lift over nOuter2@0.05 = $LIFT K"
if $PY -c "import sys; sys.exit(0 if ($D <= 0.05 and $LIFT > 0.1) else 1)"; then
    log "ACCEPT recipe: backward + nOuterCorrectors 6 + cap 0.05 -> block 3"
    STEADY_MAXDT=0.05 NOUTER=6 bash scripts/run_block3_ec2.sh prepare > block3-prepare.out 2>&1 && log "block3 prepared: $(tail -n 3 block3-prepare.out | tr '\n' ' ')" || { log "!!! prepare FAILED: $(tail -2 block3-prepare.out)"; touch BLOCK3_HELD; exit 2; }
    launch b3l1 "STEADY_MAXDT=0.05 NOUTER=6 bash scripts/run_block3_ec2.sh lane1" block3-lane1.out
    launch b3l2 "STEADY_MAXDT=0.05 NOUTER=6 bash scripts/run_block3_ec2.sh lane2" block3-lane2.out
else
    log "!!! HELD: nOuter=6 pair diff $D K, lift $LIFT K — recipe not accepted; user decision needed"; touch BLOCK3_HELD; exit 2
fi
# 3. close-out
wait_file_has block3-lane1.out 'lane1 COMPLETE'; wait_file_has block3-lane2.out 'lane2 COMPLETE'
log "BLOCK 3 COMPLETE — VM-side scoring"
for c in "$M"/steady_*_C3 "$M"/sine_*_C3 "$M"/square_f*_C3; do n=$(basename "$c"); grep -q '^End$' "$c/log.chtMultiRegionFoam" 2>/dev/null && score "$n" || log "SKIP $n (no End)"; done
$PY scripts/post/sweep_summary.py > sweep_summary.out 2>&1 && log "sweep summary written" || log "sweep_summary failed: $(tail -1 sweep_summary.out)"
touch BLOCK3_DONE; log "BLOCK3_DONE. Mac: pull + stop VM."
