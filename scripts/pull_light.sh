#!/usr/bin/env bash
# Data-light pull of finished matrix cases from the VM (mobile-data safe):
# postProcessing/ (monitor series, ~5 MB/case) + provenance files + a log
# STUB distilled on the VM (Time/deltaT/Courant/End lines only, ~200 KB)
# so extract_metrics' E2/E4 gates work without the 150 MB solver log.
#   scripts/pull_light.sh <case-name> [<case-name> ...]
set -eo pipefail
cd "$(dirname "$0")/.."
R=openfoam.pulsedimmersioncooling
for c in "$@"; do
  D=cases/matrix/$c
  mkdir -p "$D/system" "$D/constant/cell0" "$D/constant/fluid/polyMesh"
  rsync -az "openfoam-server:$R/$D/postProcessing/" "$D/postProcessing/"
  rsync -az "openfoam-server:$R/$D/case.env" "$D/" 2>/dev/null || true
  rsync -az "openfoam-server:$R/$D/system/controlDict" "$D/system/"
  rsync -az "openfoam-server:$R/$D/system/caseMeta.yaml" "$D/system/"
  rsync -az "openfoam-server:$R/$D/constant/cell0/fvOptions" "$D/constant/cell0/"
  rsync -az "openfoam-server:$R/$D/constant/fluid/polyMesh/boundary" "$D/constant/fluid/polyMesh/"
  ssh openfoam-server "grep -E '^Time = |^deltaT = |Courant Number|^End\$' $R/$D/log.chtMultiRegionFoam" \
      > "$D/log.chtMultiRegionFoam"
  echo "pulled (light) $c: $(du -sh "$D" | cut -f1)"
done
