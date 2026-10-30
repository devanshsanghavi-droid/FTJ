#!/bin/zsh
# Rebuild every Study 3 analysis output, data figure, the Figure 1 composite, RESULTS.md and takeaways.md, then trace-check.
# Order matters: raw probes (webdriver/UA, worker pauses, frames nested in LAX sandboxes; referee revision) -> raw stacks -> store table -> gate audit -> stats -> models (merges into stats.json) -> re-check crawl summary
# -> post-crawl checks (merge into stats.json) -> figures -> checks -> text.
set -e
HERE="${0:A:h}"
PY="${PY:-python3}"   # release: override with PY=/path/to/python3
cd "$HERE"
$PY extract_probe.py > /dev/null        # resumable (outputs/_probe_cache); reads crawl/raw only
$PY extract_raw.py > /dev/null          # resumable (outputs/_extract_cache); reads crawl/raw only
(cd ../crawl && $PY summarize_crawl.py --exclude ../analysis/ethics_flags.csv --out crawl_summary_analysed.json > /dev/null)   # analysed stores only (content-sensitivity exclusions, 2026-09-29)
$PY build_store_table.py
$PY gate_audit.py > /dev/null
$PY analyze.py
$PY models.py > /dev/null
(cd ../crawl/recheck && $PY analyze_recheck.py > /dev/null)   # re-check crawl: banner recall, blocker activity (reads saved raw only)
$PY checks.py                            # final-audit checks -> stats.json['checks']
$PY merge_derived_numbers.py              # v2 figures' derived numbers -> stats.json['derived_v2'] + provenance (2026-09-27)
$PY merge_round4_numbers.py               # Round 4 stats_r4.json -> stats.json['round4'] + provenance (2026-09-27)
(cd ../figures/scripts && for f in fig1bc fig3 fig4 fig5 fig6 figS; do $PY $f.py > /dev/null; done)
(cd ../figures/schematics && $PY make_numbers.py > /dev/null && zsh build.sh > /dev/null)
(cd ../figures && "${TECTONIC:-tectonic}" --chatter minimal fig1_composite.tex > /dev/null 2>&1 && schematics/tools/pdf2png fig1_composite.pdf fig1_composite.png 300)
(cd ../figures/scripts && $PY check_fonts.py > /dev/null && zsh ../validate_palettes.sh > /dev/null)
$PY write_results.py
$PY trace_check.py
