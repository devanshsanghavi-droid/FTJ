"""Merge the Round 4 numbers (round4/analysis/stats_r4.json) into the analysis provenance (2026-09-27, final manuscript pass).

Round 4 (27 Sep 2026) added the blocklist expansion (Shopify, Tranco ranks 200k-1M) and the beyond-Shopify pilot. Its own
pipeline (round4/analysis/run_r4.sh) writes stats_r4.json, RESULTS_R4.md and outputs/number_registry_r4.csv and checks them
with r4_trace_check.py (registry, coverage, reproduction of the main sample's estimands, crawl provenance). This script copies
stats_r4.json, unchanged, into
  outputs/stats.json                    under 'round4' (and round4/expansion/funnel.json, the expansion's static
                                        screening funnel, under 'round4_screen') (so paper/check_numbers.py, check_semantic.py and the figure scripts,
                                        which read stats.json, reach every Round 4 number and every (k, n) pair);
  outputs/round4_provenance.json        sha256 of stats_r4.json, RESULTS_R4.md, the Round 4 registry and scripts, and the
                                        result line of round4/analysis/outputs/trace_check_r4.txt.
analysis/trace_check.py (check 5) verifies that both are in sync and that the Round 4 trace check passed. It never computes
or edits a number. Idempotent; run by run_all.sh after merge_derived_numbers.py.
"""
import glob
import hashlib
import json
import os
import sys

from common import OUT, STUDY, dump

R4 = os.path.join(STUDY, 'round4', 'analysis')
STATS_R4 = os.path.join(R4, 'stats_r4.json')
PROV = os.path.join(OUT, 'round4_provenance.json')
TRACE_R4 = os.path.join(R4, 'outputs', 'trace_check_r4.txt')
SCREEN = os.path.join(STUDY, 'round4', 'expansion', 'funnel.json')   # static screen of the expansion (written by screen.py)


def sha(fn):
    return hashlib.sha256(open(fn, 'rb').read()).hexdigest()


def collect():
    values = json.load(open(STATS_R4))
    screen = json.load(open(SCREEN))
    files = [STATS_R4, os.path.join(R4, 'RESULTS_R4.md'), os.path.join(R4, 'outputs', 'number_registry_r4.csv'),
             os.path.join(R4, 'outputs', 'blocklist_r4.json'), SCREEN] + sorted(glob.glob(os.path.join(R4, '*.py'))) + \
            [os.path.join(R4, 'run_r4.sh')]
    trace = open(TRACE_R4).read().strip().splitlines() if os.path.exists(TRACE_R4) else []
    prov = {'stats_key': 'round4', 'written_by': 'round4/analysis/run_r4.sh (r4_write_results.py)',
            'checked_by': 'round4/analysis/r4_trace_check.py',
            'trace_check_r4_result': trace[-1] if trace else 'MISSING',
            'files': {os.path.relpath(f, STUDY): sha(f) for f in files if os.path.exists(f)}}
    return values, screen, prov


def main():
    values, screen, prov = collect()
    sp = os.path.join(OUT, 'stats.json')
    stats = json.load(open(sp))
    stats['round4'] = values
    stats['round4_screen'] = screen
    dump(stats, 'stats.json')
    json.dump(prov, open(PROV, 'w'), indent=1)
    print(f"merge_round4_numbers: stats_r4.json -> stats.json[round4], {os.path.relpath(PROV, STUDY)}; "
          f"Round 4 trace check: {prov['trace_check_r4_result']}")
    return 0 if prov['trace_check_r4_result'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
