#!/usr/bin/env bash
# Local (Mac) smoke test of one case: coarse meshes only (< ~300k cells).
# Usage: ./scripts/run_local.sh cases/validation/liu2023-static
set -euo pipefail
CASE="${1:?usage: run_local.sh <case-dir>}"
[ -d "$CASE" ] || { echo "no such case: $CASE"; exit 1; }
command -v openfoam2606 >/dev/null || { echo "openfoam2606 wrapper not found"; exit 1; }
exec openfoam2606 -c "cd '$CASE' && ./Allrun"
