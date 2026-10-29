#!/bin/zsh
# Build every schematic panel: numbers.tex -> PDF (tectonic) -> 600 dpi PNG preview.
# Usage: ./build.sh            (all panels)
#        ./build.sh fig1a_consent_pipeline   (one panel, no extension)
set -e
HERE="${0:A:h}"
cd "$HERE"
ROOT="${HERE:h:h:h}"   # .../scratch-2026-09-25-a71bef
TECTONIC="${TECTONIC:-tectonic}"   # release: tectonic on PATH
PY="${PY:-python3}"
DPI=${DPI:-600}

# PNG renderer (CoreGraphics; no poppler/mupdf on this machine)
if [[ ! -x tools/pdf2png || tools/pdf2png.swift -nt tools/pdf2png ]]; then
  swiftc -O tools/pdf2png.swift -o tools/pdf2png
fi

$PY make_numbers.py > /dev/null

if [[ $# -gt 0 ]]; then panels=("$@"); else
  panels=(fig1a_consent_pipeline fig2a_sampling_funnel fig2b_measurement_arms fig2c_attribution fig2d_validation fig2_composite figS1_wpm_architecture)
fi
for p in $panels; do
  "$TECTONIC" --chatter minimal "$p.tex"
  tools/pdf2png "$p.pdf" "png/$p.png" $DPI
done
