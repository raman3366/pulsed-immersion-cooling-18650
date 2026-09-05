#!/usr/bin/env bash
# VM-side orchestrator v3 (tmux 'orch3'). Recipe search after Euler and
# backward(nOuter 2) both failed dt-convergence (coupling lag):
#   diag  = backward nOuter6 @0.05  (lane 2, running)
#   diag2 = backward nOuter6 @0.025 (lane 1, launched now; bw1 killed)
#   diag3 = backward nOuter4 @0.05  (lane 2, after diag)
# Verdict: converged if |T6(0.05)-T6(0.025)| <= 0.05 K and lift over nOuter2
# > 0.1 K; NOUTER = 4 if |T4(0.05)-T6(0.05)| <= 0.05 K else 6. Then block 3
# (STEADY_MAXDT 0.05, NOUTER chosen), both lanes; VM-side scoring; BLOCK3_DONE.
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
clone() { rm -rf "$2"; cp -r "$1" "$2"; rm -rf "$2"/processor* "$2"/postProcessing "$2"/log.* "$2"/keep "$2"/.claimed
    find "$2" -maxdepth 1 -regex '.*/[0-9][0-9.e+-]*' ! -name 0 -exec rm -rf {} +
    cp cases/template/Allrun.pre "$2/Allrun.pre"; printf '%b\n' "$3" >> "$2/case.env"; }
launch() { tmux has-session -t "$1" 2>/dev/null && { log "$1 already running"; return 0; }
    tmux new-session -d -s "$1" "openfoam2606 -c \"$2\" > $3 2>&1"; log "launched $1: $2"; }

# 1. diag2 now (lane 1), diag3 after diag (lane 2)
clone "$M/bwd_dt0.0250_Q2" "$M/bwd_dt0.0250_nOC6_Q2" "export NOUTER=6"
launch diag2 "bash scripts/run_ec2.sh $M/bwd_dt0.0250_nOC6_Q2 16" diag2-nOC6.out
wait_end bwd_dt0.0500_nOC6_Q2; score bwd_dt0.0500_nOC6_Q2
clone "$M/bwd_dt0.0500_Q2" "$M/bwd_dt0.0500_nOC4_Q2" "export NOUTER=4"
launch diag3 "bash scripts/run_ec2.sh $M/bwd_dt0.0500_nOC4_Q2 16" diag3-nOC4.out
# 2. verdict
wait_end bwd_dt0.0250_nOC6_Q2; score bwd_dt0.0250_nOC6_Q2
wait_end bwd_dt0.0500_nOC4_Q2; score bwd_dt0.0500_nOC4_Q2
TA=$(tmax bwd_dt0.0500_nOC6_Q2); TB=$(tmax bwd_dt0.0250_nOC6_Q2); T4=$(tmax bwd_dt0.0500_nOC4_Q2)
D=$($PY -c "print(round(abs($TA-$TB),4))"); LIFT=$($PY -c "print(round($TA-31.446,4))"); D4=$($PY -c "print(round(abs($TA-$T4),4))")
log "VERDICT DATA: nOuter6 Tmax(0.05)=$TA Tmax(0.025)=$TB |diff|=$D K; lift over nOuter2 = $LIFT K; nOuter4(0.05)=$T4 |4-6|=$D4 K"
if $PY -c "import sys; sys.exit(0 if ($D <= 0.05 and $LIFT > 0.1) else 1)"; then
    NO=6; $PY -c "import sys; sys.exit(0 if $D4 <= 0.05 else 1)" && NO=4
    [ -f BLOCK3_VETO ] && { log "BLOCK3_VETO present — not launching"; touch BLOCK3_HELD; exit 3; }
    log "ACCEPT recipe: backward + nOuterCorrectors $NO + cap 0.05 -> block 3"
    STEADY_MAXDT=0.05 NOUTER=$NO bash scripts/run_block3_ec2.sh prepare > block3-prepare.out 2>&1 && log "block3 prepared: $(tail -n 3 block3-prepare.out | tr '\n' ' ')" || { log "!!! prepare FAILED: $(tail -2 block3-prepare.out)"; touch BLOCK3_HELD; exit 2; }
    launch b3l1 "STEADY_MAXDT=0.05 NOUTER=$NO bash scripts/run_block3_ec2.sh lane1" block3-lane1.out
    launch b3l2 "STEADY_MAXDT=0.05 NOUTER=$NO bash scripts/run_block3_ec2.sh lane2" block3-lane2.out
else
    log "!!! HELD: nOuter=6 pair diff $D K, lift $LIFT K — recipe not accepted; user decision needed"; touch BLOCK3_HELD; exit 2
fi
# 3. close-out
wait_file_has block3-lane1.out 'lane1 COMPLETE'; wait_file_has block3-lane2.out 'lane2 COMPLETE'
log "BLOCK 3 COMPLETE — VM-side scoring"
for c in "$M"/steady_*_C3 "$M"/sine_*_C3 "$M"/square_f*_C3; do n=$(basename "$c"); grep -q '^End$' "$c/log.chtMultiRegionFoam" 2>/dev/null && score "$n" || log "SKIP $n (no End)"; done
$PY scripts/post/sweep_summary.py > sweep_summary.out 2>&1 && log "sweep summary written" || log "sweep_summary failed: $(tail -1 sweep_summary.out)"
touch BLOCK3_DONE; log "BLOCK3_DONE. Mac: pull + stop VM."
