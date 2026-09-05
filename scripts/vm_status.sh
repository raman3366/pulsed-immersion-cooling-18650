#!/usr/bin/env bash
# One-shot status of everything on the VM (orchestrator, lanes, cases, flags).
# Usage: scripts/vm_status.sh   (from the Mac; ssh alias openfoam-server)
st=$(aws ec2 describe-instances --region us-west-2 --instance-ids i-0d9504316bb8cd248 --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null)
echo "VM state: ${st:-unknown}   local $(date '+%a %H:%M')"
[ "$st" = "running" ] || exit 0
ssh -o ConnectTimeout=20 openfoam-server bash -s <<'REMOTE'
cd ~/openfoam.pulsedimmersioncooling
echo "--- tmux: $(tmux ls 2>/dev/null | cut -d: -f1 | tr '\n' ' ')   solvers: $(pgrep -fc '[c]htMultiRegionFoam')   disk: $(df -h / | tail -1 | awk '{print $5}')   load: $(cut -d' ' -f1 /proc/loadavg)   $(date -u +%H:%M) UTC"
for f in BLOCK3_DONE BLOCK3_HELD SQUARE_SMOKE_FAILED; do [ -f $f ] && echo "!!! FLAG: $f"; done
echo "--- orchestrator (last 6):"; tail -n 6 orchestrate4.out 2>/dev/null || echo "(no orchestrate4.out)"
echo "--- lanes (last line):"; for f in bwdcheck-lane1 diag-nOC6 diag2-nOC6 diag3-nOC4 block3-lane1 block3-lane2; do [ -f $f.out ] && printf "%-16s %s\n" "$f" "$(grep -E '^=== |^!!! |^>>> square smoke' $f.out | tail -1 | cut -c1-80)"; done
echo "--- running cases:"
for p in $(pgrep -f 'mpirun -np 16 chtMultiRegionFoam'); do c=$(readlink /proc/$p/cwd); L=$c/log.chtMultiRegionFoam; printf "  %-40s t=%7s / %s s  steps=%s\n" "$(basename $c)" "$(grep '^Time = ' $L | tail -1 | awk '{print $3}')" "$(grep -o '^endTime *[0-9.]*' $c/system/controlDict | awk '{print $2}')" "$(grep -c '^Time = ' $L)"; done
echo "--- completed (End) cases: $(grep -l '^End$' cases/matrix/*/log.chtMultiRegionFoam 2>/dev/null | wc -l)   FATAL logs: $(grep -l 'FOAM FATAL' cases/matrix/*/log.chtMultiRegionFoam 2>/dev/null | wc -l)"
REMOTE
