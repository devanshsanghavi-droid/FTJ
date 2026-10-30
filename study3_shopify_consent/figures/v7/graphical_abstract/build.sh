#!/bin/zsh
# Build the Elsevier graphical abstract: numbers -> panels -> composite -> QA (300 dpi PNG) -> number trace check.
# Usage: ./build.sh            (from anywhere; outputs stay in this directory)
set -e
HERE="${0:A:h}"
cd "$HERE"
STUDY="${HERE:h:h:h}"                       # .../study3_shopify_consent
TECTONIC="${TECTONIC:-$(command -v tectonic)}"   # release: tectonic on PATH, or set TECTONIC=
PY=${PY:-python3}
tex() { "$TECTONIC" --chatter minimal "$@" 2>&1 | grep -v 'accessing absolute path' || true; }

rm -f panels/ga_pipeline.pdf panels/ga_tiles.pdf graphical_abstract.pdf   # never QA a stale PDF
$PY scripts/make_ga_numbers.py
(cd panels && tex ga_pipeline.tex && tex ga_tiles.tex)
for f in panels/ga_pipeline.pdf panels/ga_tiles.pdf; do [[ -f $f ]] || { echo "build failed: $f"; exit 1; }; done
tex graphical_abstract.tex
[[ -f graphical_abstract.pdf ]] || { echo "build failed"; exit 1; }

# QA gate (size 130 x 50 mm, fonts, raster, text sizes, colours) + 300 dpi preview PNG
$PY ../style/qa_check.py graphical_abstract.pdf --width 130 --max-height 50 --png-prefix graphical_abstract_300dpi \
  | sed '/^VISUAL QA CHECKLIST/,$d'
mv -f graphical_abstract_300dpi-p01.png graphical_abstract_300dpi.png
# GA rule: nothing below 10 pt; every printed number traced to stats.json / derived_numbers.json
$PY scripts/check_ga.py
