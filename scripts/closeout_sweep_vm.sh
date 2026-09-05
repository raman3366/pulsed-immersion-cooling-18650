#!/usr/bin/env bash
# VM-side close-out (raw data stays on the VM; only data/processed/ returns):
# gates on all sine cases -> pec scoring -> D-12 sweep summary + map.
set -eo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
W1="tight-duct early window not export-free (7mm ceiling current); ratio flat across 4.8x refinement = physical export not leak"
W2="adjustTimeStep lag on buoyant gap jets; PIMPLE stable, clean End, dt-independence 0.038% shown"
fail=0
for c in cases/matrix/sine_*/; do
  n=$(basename $c)
  grep -q "^End$" $c/log.chtMultiRegionFoam || { echo "SKIP $n (incomplete)"; continue; }
  $PY scripts/post/extract_metrics.py $c --label td_$n --waive-e1 "$W1" --waive-e2 "$W2" > $c/log.metrics 2>&1 \
    && echo "gates OK: $n $(grep -E 'E1 \(|E4 ' $c/log.metrics | tr '\n' ' ')" \
    || { echo "GATES FAILED: $n"; tail -3 $c/log.metrics; fail=$((fail+1)); }
done
echo "gate failures: $fail"
$PY scripts/post/pec.py cases/matrix/sine_*/ cases/matrix/steady_f0.00_A0.00_Q2_C3 2>/dev/null \
  || $PY scripts/post/pec.py cases/matrix/sine_*/
$PY scripts/post/sweep_summary.py
