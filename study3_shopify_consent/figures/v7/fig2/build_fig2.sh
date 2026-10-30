#!/bin/zsh
# Build Figure 2 (methodology), v7.1 (binding spec ../DESIGN_V7.md, section 12 'How to build'; worked example ../fig1):
# derived numbers -> geometry, printed numbers and drawn positions (checked against measured Arial widths; hero area and
# composite asserted) -> TikZ panels a (sampling flow), b (hero: where the crawler attaches) and c (the arms under one
# time axis) -> composite -> caption + alt text (they carry every count and the median moments) + Supplementary Table
# S-arms -> trace check -> QA gate (the one review PNG, _v7_review-p01.png at 200 dpi: the disk is tight; includes the
# text-collision audit) -> palette gate -> skill screen and export manifest -> sciplot palette check (CVD dE2000).
# The CVD / grayscale montage is a review aid written only on request (CVD_OUT=/path/to/montage.png), so the folder
# keeps one PNG. Any failing check stops the build.
# Run:  PATH=/opt/anaconda3/bin:$PATH zsh build_fig2.sh   (from anywhere)
set -e
setopt pipefail
HERE="${0:A:h}"; cd "$HERE"
STUDY="$HERE"                                           # .../study3_shopify_consent: the first ancestor holding
while [[ "$STUDY" != "/" && ! ( -d "$STUDY/analysis" && -d "$STUDY/figures" ) ]]; do STUDY="${STUDY:h}"; done
                                                        # analysis/ and figures/
TECTONIC="${TECTONIC:-$(command -v tectonic)}"
[[ -x "$TECTONIC" ]] || { echo "tectonic not found at $TECTONIC (set TECTONIC=...)"; exit 1; }
export TECTONIC PYTHONDONTWRITEBYTECODE=1
tex() { "$TECTONIC" --chatter minimal "$@" 2>&1 | { grep -v 'accessing absolute path' || true; }; }

if [[ -d "$STUDY/crawl/raw" ]]; then python3 scripts/derive_fig2.py > /dev/null; else echo "derive_fig2.py skipped: it reads raw captures (on request); the shipped derived_numbers.json is used"; fi
python3 scripts/make_fig2_panels.py                      # -> build/fig2_{layout,numbers}.tex, panels/fig2_numbers.csv
(cd tex && for f in fig2a_funnel fig2b_instrumentation fig2c_arms; do tex --outdir ../panels $f.tex; done)
tex fig2.tex
python3 scripts/make_caption_fig2.py                     # -> caption_fig2.tex, alt_text_fig2.txt
python3 scripts/make_table_arms.py                       # -> tableS_arms.tex (Supplementary Table S-arms)
python3 scripts/trace_fig2.py
rm -f fig2_preview_300dpi.png _qa_cvd.png _v6_review-p01.png    # older review renders (one review PNG per figure)
python3 ../style/qa_check.py fig2.pdf --dpi 200 --png-prefix "$HERE/_v7_review" | tee qa_check_fig2.txt | sed -n '1,/^RESULT/p'
python3 ../style/palette_gate.py fig2.pdf --out palette_validation_fig2.txt
if [[ -n "${CVD_OUT:-}" ]]; then python3 ../style/cvd_check.py _v7_review-p01.png "$CVD_OUT"; fi
python3 scripts/skill_qa_fig2.py fig2.pdf
python3 scripts/sp_lint.py fig2.pdf                      # sciplot palette check (CVD dE2000) -> sp_lint_fig2.txt
