#!/bin/zsh
# build_one.sh N [--no-qa]: rebuild Supplementary Figure S<N> (panels, composite, QA render into the scratch prefix $QA_PREFIX).
set -e
HERE="${0:A:h}"; cd "$HERE"
TECTONIC="${HERE:h:h:h:h}/tools/texenv/bin/tectonic"
N=$1
[[ -f scripts/s$N.py ]] && python3 scripts/s$N.py
"$TECTONIC" --chatter minimal figS$N.tex 2>&1 | grep -v 'accessing absolute path' || true
if [[ "$2" != "--no-qa" ]]; then
  python3 ../style/qa_check.py figS$N.pdf --png-prefix "${QA_PREFIX:-<tmp>}/qS$N" | sed -n '1,/^RESULT/p'
fi
