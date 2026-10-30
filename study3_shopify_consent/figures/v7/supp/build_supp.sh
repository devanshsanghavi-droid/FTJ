#!/bin/zsh
# build_supp.sh -- rebuild every v2 Supplementary Figure (S1-S10) from the committed analysis outputs.
#   1. derived numbers  (scripts/derive_supp_numbers.py -> derived_numbers.json, tables/s7b_entries.csv)
#   2. panels           (scripts/s2.py ... s10.py -> panels/*.pdf + panels/figS<N>_numbers.csv registries)
#   3. composites       (figS1.tex ... figS10.tex -> figS<N>.pdf, vector, Arial, 190 mm wide) with tectonic
#   4. supp.pdf         (the ten figures, one per page, merged with pypdf; vector, nothing re-rendered)
#   5. captions         (scripts/make_captions.py -> caption_supp.tex; every number rendered from stats / derived)
#   6. checks           (qa_check.py on every figure; scripts/trace_supp.py -> trace_supp.txt; grey-ramp validation)
#   7. preview          (300 dpi PNGs supp_preview-p01..p10.png, one per figure)
# Usage: ./build_supp.sh            (from anywhere)
set -e
HERE="${0:A:h}"; cd "$HERE"
STUDY="${HERE:h:h:h}"
TECTONIC="${TECTONIC:-$(command -v tectonic)}"   # release: tectonic on PATH, or set TECTONIC=
PNG="$STUDY/paper/tools/pdfpages2png"
python3 scripts/derive_supp_numbers.py > /dev/null
for n in 2 3 4 5 6 7 8 9 10; do python3 scripts/s$n.py > /dev/null; done
for n in 1 2 3 4 5 6 7 8 9 10; do "$TECTONIC" --chatter minimal figS$n.tex 2>&1 | grep -v 'accessing absolute path' || true; done
python3 - <<'PY'
from pypdf import PdfWriter
w = PdfWriter()
for n in range(1, 11):
    w.append(f'figS{n}.pdf')
w.add_metadata({'/Title': 'Supplementary Figures S1-S10 (v2)', '/Creator': 'figures/v7/supp/build_supp.sh'})
with open('supp.pdf', 'wb') as f:
    w.write(f)
print('wrote supp.pdf')
PY
python3 scripts/make_captions.py
for n in 1 2 3 4 5 6 7 8 9 10; do
  python3 ../style/qa_check.py figS$n.pdf --no-render | grep -E '^(QA|RESULT|FAIL|WARN)'
done
python3 scripts/trace_supp.py | tail -1
VALIDATOR=${VALIDATOR:-}
if command -v node >/dev/null && [[ -f "$VALIDATOR" ]]; then
  node "$VALIDATOR" "$(python3 -c 'import sys; sys.path.insert(0, "scripts"); import s2; print(",".join(s2.RAMP))')" --ordinal > palette_validation_supp.txt 2>&1 || true
  tail -2 palette_validation_supp.txt
fi
# release: the previews need paper/tools/pdfpages2png (swiftc -O -o paper/tools/pdfpages2png paper/tools/pdfpages2png.swift, macOS)
if [[ -x "$PNG" ]]; then "$PNG" supp.pdf supp_preview 300 > /dev/null; ls -la supp_preview-p*.png; fi
ls -la supp.pdf
