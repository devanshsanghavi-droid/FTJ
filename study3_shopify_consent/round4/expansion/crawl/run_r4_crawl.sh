#!/bin/zsh
# Round 4 measurement crawl, both sets in sequence (never in parallel: one global navigation gate per process, so
# running them together would exceed 1 navigation/s). Resumable: rerun this script after a stop; prepared sites and
# finished loads are skipped. Stop: touch round4/expansion/crawl/STOP (and round4/beyond/crawl/STOP).
# Free-disk floor: 1.2 GB (checked here and inside crawl.js / crawl_r4.js).
set -u
HERE="${0:A:h}"
R4="${HERE:h:h}"
LOG="$HERE/logs/run_r4.log"
mkdir -p "$HERE/logs" "$R4/beyond/crawl/logs"
export CS3_TMP="${CS3_TMP:-${TMPDIR:-/tmp}/cs3profiles_r4}"
free_ok() { [[ $(df -k "$HERE" | awk 'NR==2{print $4}') -gt 1200000 ]] }
for SET in expansion beyond; do
  OUTD="$R4/$SET/crawl"
  [[ -f "$OUTD/STOP" ]] && { echo "$(date -u +%FT%TZ) STOP present for $SET" >> "$LOG"; exit 0; }
  free_ok || { echo "$(date -u +%FT%TZ) DISK_LOW before $SET" >> "$LOG"; exit 1; }
  echo "$(date -u +%FT%TZ) prepare $SET" >> "$LOG"
  node "$HERE/crawl_r4.js" --set $SET --prepare >> "$LOG" 2>&1 || { echo "prepare failed $SET" >> "$LOG"; exit 1; }
  echo "$(date -u +%FT%TZ) crawl $SET" >> "$LOG"
  node "$HERE/crawl_r4.js" --set $SET --conc 6 >> "$LOG" 2>&1 || { echo "crawl failed $SET" >> "$LOG"; exit 1; }
done
echo "$(date -u +%FT%TZ) ALL SETS DONE" >> "$LOG"
