#!/bin/zsh
# Build the v2 style foundation outputs: palette_v2.tex, demo panels, style_sheet.pdf, palette validation, QA.
# Usage: ./build_style_sheet.sh [png_prefix]      (png_prefix: where qa_check.py writes the 300 dpi render)
set -e
HERE="${0:A:h}"
cd "$HERE"
STUDY="${HERE:h:h:h}"                       # .../study3_shopify_consent
TECTONIC="${TECTONIC:-$(command -v tectonic)}"   # release: tectonic on PATH, or set TECTONIC=
PY=${PY:-python3}
VALIDATOR=${VALIDATOR:-}

$PY figstyle.py --write-tex --selftest
$PY demo/make_demo_panels.py
for f in demo_a_type demo_b_dictionary demo_e_icons demo_f_strokes; do
  (cd demo && "$TECTONIC" --chatter minimal --outdir build "$f.tex" 2>&1 | grep -v 'accessing absolute path' || true)
done
"$TECTONIC" --chatter minimal style_sheet.tex 2>&1 | grep -v 'accessing absolute path' || true
"$TECTONIC" --chatter minimal --outdir demo/build composite_template.tex 2>&1 | grep -v 'accessing absolute path' || true

# palette validation (dataviz skill validator): vendor slots + spare on the print surface; red next to each grey
if command -v node >/dev/null && [[ -f "$VALIDATOR" ]]; then
  {
    echo "# v2 palette validation ($(date -u +%Y-%m-%dT%H:%MZ)); validator: dataviz/scripts/validate_palette.js"
    echo; echo "## Vendors (fixed order, 7 slots + spare), adjacent pairs, print surface #ffffff"
    node "$VALIDATOR" "$($PY -c 'import figstyle as f; print(",".join([f.VENDOR[v] for v in f.VENDOR_ORDER] + ["#e34948"]))')" --mode light --surface "#ffffff" || true
    echo; echo "## Red (consent failed) next to TikTok orange: must never share a panel (expected FAIL)"
    node "$VALIDATOR" "#d03b3b,#eb6834" --mode light --surface "#ffffff" || true
    echo; echo "## Ordinal blue ramp (heatmaps)"
    node "$VALIDATOR" "$($PY -c 'import figstyle as f; print(",".join(f.ORD_BLUE))')" --mode light --surface "#ffffff" --ordinal || true
  } > palette_validation_v2.txt 2>&1
  echo "wrote palette_validation_v2.txt"
fi

extra=()
[[ -n "$1" ]] && extra=(--png-prefix "$1")
$PY qa_check.py style_sheet.pdf --allow-red-with-vendors "${extra[@]}"
