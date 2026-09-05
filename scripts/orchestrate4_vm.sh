#!/usr/bin/env bash
# VM-side orchestrator v4 — block 3 under D-16 (fixed dt 0.0125, backward,
# nOuter 2). Q2 baseline comes from bwd_dt0.0125_Q2 (running): lane 1 skips
# steady_Q2 via .claimed; on bwfine End its artifacts are copied in under the
# steady name and scored. Ends: VM-wide scoring -> BLOCK3_DONE.
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
launch() { tmux has-session -t "$1" 2>/dev/null && { log "$1 already running"; return 0; }
    tmux new-session -d -s "$1" "openfoam2606 -c \"$2\" > $3 2>&1"; log "launched $1: $2"; }

rm -f BLOCK3_HELD BLOCK3_VETO
log "D-16: preparing block 3 (fixed dt 0.0125, backward, nOuter 2)"
STEADY_MAXDT=0.0125 bash scripts/run_block3_ec2.sh prepare > block3-prepare.out 2>&1 && log "prepared: $(tail -n 2 block3-prepare.out | tr '\n' ' ')" || { log "!!! prepare FAILED: $(tail -3 block3-prepare.out)"; exit 2; }
touch "$M/steady_f0.00_A0.00_Q2_C3/.claimed"; log "steady Q2 claimed (baseline = bwd_dt0.0125_Q2)"
launch b3l1 "STEADY_MAXDT=0.0125 bash scripts/run_block3_ec2.sh lane1" block3-lane1.out
launch b3l2 "STEADY_MAXDT=0.0125 bash scripts/run_block3_ec2.sh lane2" block3-lane2.out
# Q2 alias when bwfine ends
wait_end bwd_dt0.0125_Q2
Q2=$M/steady_f0.00_A0.00_Q2_C3
cp -a "$M/bwd_dt0.0125_Q2/postProcessing" "$Q2/postProcessing"
cp "$M/bwd_dt0.0125_Q2/log.chtMultiRegionFoam" "$Q2/"
cp "$M/bwd_dt0.0125_Q2/system/caseMeta.yaml" "$Q2/system/" 2>/dev/null || true
log "Q2 baseline aliased from bwd_dt0.0125_Q2"; score steady_f0.00_A0.00_Q2_C3
# close-out
wait_file_has block3-lane1.out 'lane1 COMPLETE'; wait_file_has block3-lane2.out 'lane2 COMPLETE'
log "BLOCK 3 COMPLETE — VM-side scoring"
for c in "$M"/steady_*_C3 "$M"/sine_*_C3 "$M"/square_f*_C3; do n=$(basename "$c"); grep -q '^End$' "$c/log.chtMultiRegionFoam" 2>/dev/null && score "$n" || log "SKIP $n (no End)"; done
$PY scripts/post/sweep_summary.py > sweep_summary.out 2>&1 && log "sweep summary written" || log "sweep_summary failed: $(tail -1 sweep_summary.out)"
touch BLOCK3_DONE; log "BLOCK3_DONE. Mac: pull data/processed + postProcessing + fields, then stop the VM."
