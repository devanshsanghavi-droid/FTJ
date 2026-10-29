#!/bin/zsh
# Re-validate every palette the figures use (binding: FIGURE_PLAN.md style guide) and write palette_validation.txt.
# Validator: the dataviz skill's scripts/validate_palette.js (path below; override with VALIDATOR=...).
HERE="${0:A:h}"
V=${VALIDATOR:-/private/tmp/claude-502/bundled-skills/2.1.281/a9e15d2c5dcb745ab76737f9aa4ed918/dataviz/scripts/validate_palette.js}
OUT="$HERE/palette_validation.txt"
VEND="#2a78d6,#eb6834,#1baf7a,#eda100,#e87ba4,#008300,#4a3aa7,#e34948"
{
echo "# Palette validation for Study 3 figures ($(date -u +%Y-%m-%dT%H:%MZ)); validator: dataviz/scripts/validate_palette.js"
echo "# Revised after review: section 4 is the NEW 4-step ordinal heatmap ramp (no Google hex); section 6 documents the"
echo "# all-pairs failure of the 7 vendor colours, which is why Fig 1c gives each vendor its own sub-row and Fig 6b adds"
echo "# sandbox/other sub-rows and a TikTok marker (colour is never the only identity cue for scatter-like marks)."
echo; echo "## 1. Vendor categorical palette (7 slots used + spare), adjacent pairs, print surface #ffffff"; echo
node "$V" "$VEND" --mode light --surface "#ffffff"; echo "exit=$?"
echo; echo "## 2. Same palette, default light surface #fcfcfb"; echo
node "$V" "$VEND" --mode light; echo "exit=$?"
echo; echo "## 3. First three slots, all pairs (scatter / small multiples cap)"; echo
node "$V" "#2a78d6,#eb6834,#1baf7a" --mode light --surface "#ffffff" --pairs all; echo "exit=$?"
echo; echo "## 4. Heatmap ramp (Fig 4b): ordinal steps 250/350/550/700, bins 0-25-50-75-100 %"; echo
node "$V" "#86b6ef,#5598e7,#1c5cab,#0d366b" --mode light --surface "#ffffff" --ordinal; echo "exit=$?"
echo; echo "## 5. Same ramp on the default surface"; echo
node "$V" "#86b6ef,#5598e7,#1c5cab,#0d366b" --mode light --ordinal; echo "exit=$?"
echo; echo "## 6. The 7 vendor colours, ALL pairs (expected to fail: secondary encodings are used wherever marks are scatter-like)"; echo
node "$V" "#2a78d6,#eb6834,#1baf7a,#eda100,#e87ba4,#008300,#4a3aa7" --mode light --surface "#ffffff" --pairs all; echo "exit=$?"
} > "$OUT" 2>&1
echo "wrote $OUT"
