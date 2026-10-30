#!/bin/zsh
# Round 4 analysis: tables with the main pipeline's code -> blocked-on-paper estimands -> beyond-Shopify -> text -> trace.
set -e
HERE="${0:A:h}"
PY="${PY:-python3}"   # release: override with PY=/path/to/python3
cd "$HERE"
if [[ -d ../expansion/crawl/raw ]]; then $PY r4_tables.py > outputs/_r4_tables.log 2>&1; fi
$PY r4_blocklist.py records --ds main
if [[ -f outputs/expansion/store_table.csv ]]; then $PY r4_blocklist.py records --ds expansion; fi
$PY r4_blocklist.py combine
$PY r4_beyond.py
$PY r4_write_results.py
$PY r4_trace_check.py
