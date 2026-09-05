#!/usr/bin/env bash
# Assemble the Zenodo/GitHub data-and-code release for the ATE paper.
# Output: release/pulsed-immersion-cooling-v1/ (+ .zip). Raw fields excluded.
set -eo pipefail; cd "$(dirname "$0")/.."
V=${1:-v1}; R=release/pulsed-immersion-cooling-$V; rm -rf "$R"; mkdir -p "$R"
cp -r data/processed "$R/data_processed"; cp -r data/reference "$R/data_reference"
mkdir -p "$R/scripts"; cp scripts/*.py scripts/*.sh "$R/scripts/" 2>/dev/null; cp -r scripts/post "$R/scripts/post"
cp -r cases/template "$R/case_template"; find "$R/case_template" -name "log.*" -delete; rm -rf "$R/case_template/processor*" "$R/case_template/postProcessing"
cp -r geometry "$R/geometry" 2>/dev/null || true
mkdir -p "$R/paper"; cp paper/figures/fig*.pdf paper/figures/graphical_abstract.png "$R/paper/" 2>/dev/null; cp paper/tables/*.tex "$R/paper/" 2>/dev/null
cp docs/PROJECT.md "$R/PROJECT.md"; cp docs/environment.md "$R/environment.md" 2>/dev/null || true
cp release/README.md release/LICENSE release/CITATION.cff "$R/"
(cd release && zip -qr "pulsed-immersion-cooling-$V.zip" "pulsed-immersion-cooling-$V")
du -sh "$R" release/pulsed-immersion-cooling-$V.zip
