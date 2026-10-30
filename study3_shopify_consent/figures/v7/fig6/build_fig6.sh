#!/bin/zsh
# Build Figure 6 (v7; binding spec ../DESIGN_V7.md, section 12 'How to build'; worked example ../fig1/build.sh):
# derived numbers -> panels (a's plot, b, c, d; fs.v7_context(); each linted by sciplot's rules; composite cells and the
# drawing's text asserted) -> TikZ drawing of a (fig6a_path.tex: nested regions, no numbers) -> composite -> caption +
# alt text (they carry every number) -> trace check -> QA gate (the one review PNG, _v7_review-p01.png at 200 dpi: the
# disk is tight) -> palette gate -> skill screen and export manifest -> sciplot palette check (CVD dE2000). The CVD /
# grayscale montage is a review aid written only on request (CVD_OUT=/path/to/montage.png), so the folder keeps one
# PNG. Any failing check stops the build.
# Run:  PATH=/opt/anaconda3/bin:$PATH zsh build_fig6.sh   (from anywhere)
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
python3 scripts/derive_fig6.py > /dev/null              # -> derived_numbers.json (asserts against stats.json)
python3 scripts/make_fig6_panels.py                     # -> panels/fig6a_loads.pdf, b, c, d, fig6_layout.tex, registry
"$TECTONIC" --chatter minimal --outdir panels fig6a_path.tex 2>&1 | { grep -v 'accessing absolute path' || true; }
"$TECTONIC" --chatter minimal fig6.tex 2>&1 | { grep -v 'accessing absolute path' || true; }
python3 scripts/make_caption_fig6.py                    # -> caption_fig6.tex, alt_text_fig6.txt (+ registry)
python3 scripts/trace_fig6.py                           # every printed number traced (trace_fig6.txt)
rm -f fig6_preview_300dpi.png _qa_cvd.png _v6_review-p01.png   # older review renders (one review PNG per figure)
python3 ../style/qa_check.py fig6.pdf --dpi 200 --png-prefix "$HERE/_v7_review" | tee qa_check_fig6.txt | sed -n "1,/^RESULT/p"
python3 ../style/palette_gate.py fig6.pdf --out palette_validation_fig6.txt
if [[ -n "${CVD_OUT:-}" ]]; then python3 ../style/cvd_check.py _v7_review-p01.png "$CVD_OUT"; fi
python3 scripts/skill_qa_fig6.py fig6.pdf
python3 scripts/sp_lint.py fig6.pdf                     # sciplot palette check (CVD dE2000) -> sp_lint_fig6.txt
