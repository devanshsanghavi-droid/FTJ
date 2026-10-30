#!/usr/bin/env bash
# One command: regenerate every data figure, the supplementary LaTeX tables, RESULTS.md and takeaways.md from the
# released analysis outputs, check that every number printed in them traces to analysis/outputs/stats.json, and
# compare the regenerated files with the shipped ones.
#
#   ./reproduce.sh                  uses python3 on PATH
#   PY=/path/to/python3 ./reproduce.sh
#
# The full pipeline (raw captures -> tables -> stats.json) needs the data that are available on request; see
# README.md, "Full re-run from the raw captures".
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PY:-python3}"
TECTONIC="${TECTONIC:-tectonic}"
S3="$ROOT/study3_shopify_consent"

echo "== 1/5 integrity: every file matches MANIFEST.tsv (size and SHA-256)"
"$PY" "$ROOT/release_tools/check.py" verify

echo "== 2/5 data figures (figures/panels) and supplementary tables (figures/tables) from analysis/outputs"
( cd "$S3/figures/scripts" && for f in fig1bc fig3 fig4 fig5 fig6 figS; do echo "   $f.py"; "$PY" "$f.py" > /dev/null; done )

echo "== 3/5 RESULTS.md and takeaways.md re-rendered from stats.json; trace check of every printed number"
( cd "$S3/analysis" && "$PY" write_results.py > /dev/null && "$PY" trace_check.py | sed 's/^/   /' )

echo "== 4/5 schematics and the Figure 1 composite (optional: needs tectonic, zsh, and macOS for the PNG previews)"
PDF2PNG="$S3/figures/schematics/tools/pdf2png"
if command -v "$TECTONIC" > /dev/null && command -v zsh > /dev/null && [[ "$(uname)" == Darwin ]] \
   && { [[ -x "$PDF2PNG" ]] || swiftc -O "$PDF2PNG.swift" -o "$PDF2PNG" > /dev/null 2>&1; }; then
  ( cd "$S3/figures/schematics" && PY="$PY" TECTONIC="$TECTONIC" zsh build.sh > /dev/null 2>&1 )
  ( cd "$S3/figures" && "$TECTONIC" --chatter minimal fig1_composite.tex > /dev/null 2>&1 \
      && schematics/tools/pdf2png fig1_composite.pdf fig1_composite.png 300 )
  echo "   rebuilt"
else
  echo "   skipped (needs tectonic, zsh and macOS with a working swiftc); the shipped schematic PDFs are used"
fi

echo "== 5/5 regenerated files vs shipped files"
"$PY" "$ROOT/release_tools/check.py" compare
