#!/bin/zsh
# Build Figure 5 (v7; binding spec ../DESIGN_V7.md, section 12 'How to build'; worked example ../fig1): derived
# numbers -> panels a, b, c (fs.v7_context(); each linted by sciplot's rules; they print axis ticks only) -> composite
# -> caption + alt text (they carry every count) -> trace check -> QA gate (the one review PNG, _v7_review-p01.png at
# 200 dpi: the disk is tight) -> palette gate -> skill screen and export manifest -> sciplot palette check (CVD
# dE2000). The CVD / grayscale montage is a review aid written only on request (CVD_OUT=/path/to/montage.png), so the
# folder keeps one PNG. Any failing check stops the build.
# Run:  PATH=/opt/anaconda3/bin:$PATH zsh build_fig5.sh   (from anywhere)
set -e
setopt pipefail
HERE="${0:A:h}"; cd "$HERE"
STUDY="$HERE"                                           # .../study3_shopify_consent: the first ancestor holding
while [[ "$STUDY" != "/" && ! ( -d "$STUDY/analysis" && -d "$STUDY/figures" ) ]]; do STUDY="${STUDY:h}"; done
                                                        # analysis/ and figures/
TECTONIC="${TECTONIC:-$(command -v tectonic)}"
[[ -x "$TECTONIC" ]] || { echo "tectonic not found at $TECTONIC (set TECTONIC=...)"; exit 1; }
export TECTONIC
export PYTHONDONTWRITEBYTECODE=1
python3 scripts/derive_fig5_numbers.py > /dev/null       # -> derived_numbers.json (per-load race lags)
python3 scripts/make_fig5_panels.py                      # -> panels/fig5{a_dots,b_gate,c_race}.pdf (+ registry, ticks)
"$TECTONIC" --chatter minimal fig5.tex 2>&1 | { grep -v 'accessing absolute path' || true; }
python3 scripts/make_caption_fig5.py > /dev/null         # -> caption_fig5.tex, alt_text_fig5.txt (+ registry)
python3 scripts/trace_fig5.py                            # every printed number traced (trace_fig5.txt)
rm -f fig5_preview_300dpi.png _qa_cvd.png _v6_review-p01.png   # older review renders (one review PNG per figure)
python3 ../style/qa_check.py fig5.pdf --dpi 200 --png-prefix "$HERE/_v7_review" | tee qa_check_fig5.txt | sed -n "1,/^RESULT/p"
python3 ../style/palette_gate.py fig5.pdf --out palette_validation_fig5.txt
if [[ -n "${CVD_OUT:-}" ]]; then python3 ../style/cvd_check.py _v7_review-p01.png "$CVD_OUT"; fi
python3 scripts/skill_qa_fig5.py fig5.pdf
python3 scripts/sp_lint.py fig5.pdf                      # sciplot palette check (CVD dE2000) -> sp_lint_fig5.txt
