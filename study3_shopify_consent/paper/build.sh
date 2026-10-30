#!/bin/zsh
# Build the Study 3 manuscript.
#   1. copy the final v2 figure PDFs and their generated captions from ../figures/v2 (integrate_figures_v2.py;
#      the paper never edits figures or captions)
#   2. regenerate the generated tables (tables/*.py)
#   3. compile supplement.tex, main.tex, supplement.tex again (xr-hyper cross-references in both directions),
#      then main_5p.tex (two-column preview) and highlights.tex
#   4. render every page to preview/*.png, count words and check every number (check_numbers.py)
# Usage: ./build.sh            (everything)
#        ./build.sh flat       (flat Editorial Manager folder ../submission/, verified; see flatten() below)
set -e
HERE="${0:A:h}"
cd "$HERE"
ROOT="${HERE:h:h}"          # .../scratch-2026-09-25-a71bef
TECTONIC="${TECTONIC:-tectonic}"   # release: tectonic on PATH, or set TECTONIC=/path/to/tectonic
PY="${PY:-python3}"   # release: override with PY=/path/to/python3
FIG=../figures

tex() { "$TECTONIC" --keep-logs --keep-intermediates --chatter minimal "$1.tex" 2>&1 | grep -v "accessing absolute path" || true; }

# Editorial Manager cannot process subfolders: make_submission.py writes the flat submission folder ../submission/
# (one main.tex with everything inlined, fig1-6.pdf, main.bbl, refs.bib, elsarticle.cls/-harv.bst, highlights.txt,
# supplement.pdf, main.pdf), checks it for pdfLaTeX compatibility, compiles a fresh copy with tectonic and compares it
# with this build's main.pdf page by page. Run it after a full build (it needs this build's .aux, .bbl and PDFs).
# Its report is saved in build_submission.log. README_SUBMISSION.md in that folder lists each file's item type.
flatten() {
  $PY make_submission.py > build_submission.log 2>&1 && rc=0 || rc=$?
  grep -E "FAIL|RESULT" build_submission.log
  return $rc
}

if [[ "$1" == "flat" ]]; then flatten; exit $?; fi

mkdir -p figs preview
# v2 figures (2026-09-27): figs/fig1-6.pdf and figs/figS1-S9.pdf plus their generated captions (captions/*.tex) and the
# supplementary arm table come from ../figures/v2 via integrate_figures_v2.py; the v1 PDFs are kept in figs/v1/.
$PY integrate_figures_v2.py
# generated tables that the figure scripts write (referee revision: the projection, formerly Fig 5e, and the consent-tool detection table)
cp $FIG/tables/table_projection.tex $FIG/tables/tableS_cmp_detection.tex tables/

$PY tables/pixel_config_table.py   > /dev/null
$PY tables/banner_region_by_cmp.py > /dev/null
$PY tables/supp_tables.py          > /dev/null

tex supplement
tex main
tex supplement
tex main_5p
tex highlights

rm -f preview/*.png(N)
for d in main supplement main_5p highlights; do tools/pdfpages2png $d.pdf preview/$d 110 > /dev/null 2>&1 || true; done
$PY wordcount.py > wordcount.txt
$PY check_numbers.py
