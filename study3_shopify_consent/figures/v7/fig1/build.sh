#!/bin/zsh
# Build Figure 1 (v7 reference figure; binding spec ../DESIGN_V7.md, section 12 'How to build'): derived numbers ->
# panels b, c (fs.v7_context(); each linted by sciplot's rules) -> TikZ panel a (nested regions, loss numerals, no data
# numbers) -> composite -> caption + alt text (they carry every count) -> trace check -> QA gate (the one review PNG,
# _v7_review-p01.png at 200 dpi: the disk is tight) -> palette gate -> skill screen and export manifest -> sciplot
# palette check (CVD dE2000). The CVD / grayscale montage is a review aid written only on request
# (CVD_OUT=/path/to/montage.png), so the folder keeps one PNG. Any failing check stops the build.
# Run:  PATH=/opt/anaconda3/bin:$PATH zsh build.sh   (from anywhere)
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
if [[ -d "$STUDY/crawl/recheck/raw" ]]; then python3 scripts/derive_fig1.py > /dev/null; else echo "derive_fig1.py skipped: it reads raw captures (on request); the shipped derived_numbers.json is used"; fi
python3 scripts/make_panels.py                            # -> panels/fig1b_trace.pdf, fig1c_raster.pdf (+ registry)
"$TECTONIC" --chatter minimal --outdir panels fig1a_pipeline.tex 2>&1 | { grep -v 'accessing absolute path' || true; }
"$TECTONIC" --chatter minimal fig1.tex 2>&1 | { grep -v 'accessing absolute path' || true; }
python3 scripts/make_caption.py                           # -> caption_fig1.tex, alt_text_fig1.txt (+ registries)
python3 scripts/trace_fig1.py                             # every printed number traced (trace_fig1.txt)
rm -f fig1_preview_300dpi.png _qa_cvd.png _bake-p01.png   # older review renders (one review PNG per figure)
python3 ../style/qa_check.py fig1.pdf --dpi 200 --png-prefix "$HERE/_v7_review" | tee qa_check_fig1.txt | sed -n "1,/^RESULT/p"
python3 ../style/palette_gate.py fig1.pdf --out palette_validation_fig1.txt
if [[ -n "${CVD_OUT:-}" ]]; then python3 ../style/cvd_check.py _v7_review-p01.png "$CVD_OUT"; fi
python3 scripts/skill_qa_fig1.py fig1.pdf
python3 scripts/sp_lint.py fig1.pdf                       # sciplot palette check (CVD dE2000) -> sp_lint_fig1.txt
