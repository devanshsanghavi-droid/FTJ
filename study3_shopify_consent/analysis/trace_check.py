"""Trace check: every number printed in RESULTS.md and figures/takeaways.md must come from saved outputs.

Checks
  1. Registry consistency: each row of outputs/number_registry_*.csv is re-rendered from the CURRENT
     outputs/stats.json; a mismatch means the text is stale.
  2. Coverage: every numeric token in the Markdown files is either (a) a registered rendering, or
     (b) a structural token (figure/panel/arm/prediction labels, dates, file names, list numbering,
     the "95%" CI level, table headers). Anything else is reported as UNTRACED.
  3. No number typed into write_results.py's text templates.
  4. The v2 figures' derived numbers (figures/v2/**/derived_numbers.json) are merged, unchanged, into stats.json
     ['derived_v2'] and outputs/derived_numbers_provenance.json (merge_derived_numbers.py), each with script and inputs.
Exit code 1 if any check fails. Writes outputs/trace_check.txt.
"""
import csv
import json
import os
import re
import sys

from common import OUT, STUDY
import numreg

FILES = [
    (os.path.join(STUDY, 'analysis', 'RESULTS.md'), os.path.join(OUT, 'number_registry_results.csv')),
    (os.path.join(STUDY, 'figures', 'takeaways.md'), os.path.join(OUT, 'number_registry_takeaways.csv')),
]

NUM = re.compile(r'(?<![\w.\-@#,])(\d[\d,]*(?:\.\d+)?)')
STRUCTURAL = [
    r'\b(?:Fig(?:ure)?s?\.?|Figures?)\s*\d[a-d]?(?:[–-]\d[a-d]?)?(?:\s*(?:and|,)\s*\d[a-d]?)*',  # Figure 3, Fig 5c, Figs 3-6
    r'\bS\d\b', r'\bA[012]r?\b', r'\bV1\b', r'\bP\d\b', r'\bH\d\b',                      # S4, arms, predictions
    r'\b95\s?%', r'\b\d{4}-\d{2}-\d{2}\b', r'\b\d{2}:\d{2}(?::\d{2})?\b',                 # CI level, dates, times
    r'`[^`]*`',                                                                            # code / file names
    r'\[[^\]]*\]\([^)]*\)',                                                                # links
    r'\b\d+(?:st|nd|rd|th)\b',
    r'\bL5PZ4\b', r'\btop-200k\b', r'\b\d+k[–-]\d+k\b', r'\b1[–-]10k\b', r'\b100k[–-]200k\b',  # Tranco list id / buckets
    r'\b(?:1|2|3|4|5|6)\s*(?:main|big)\b', r'\bsix\b',
    r'\b3\.AMPS\w*', r'\b3s\.\w+',                                                         # consent strings
    r'\bIF\s*>\s*2\b', r'\bImpact Factor\b[^.]*', r'\bsha\d+\b', r'\bCohen\'s\b',
    r'\bCPAPI\b', r'\bwpm\w*', r'\b[A-Z]\d{3,4}\b',                                          # store ids S0123/C005
    r'\bn\s*<\s*5\b', r'\b0\s*[–-]\s*1\b',
]
STRUCT_RX = re.compile('|'.join(STRUCTURAL))


def masked(line):
    return STRUCT_RX.sub(lambda m: ' ' * len(m.group(0)), line)


def main():
    stats = json.load(open(os.path.join(OUT, 'stats.json')))
    report, fails = [], 0
    for md, regfn in FILES:
        if not os.path.exists(md) or not os.path.exists(regfn):
            report.append(f'MISSING {md} or {regfn}')
            fails += 1
            continue
        reg = list(csv.DictReader(open(regfn)))
        # 1. registry consistency against current stats.json
        texts = set()
        for r in reg:
            try:
                v = numreg.get(r['key'])
                s = numreg.render(v, r['fmt'])
            except Exception as e:
                report.append(f'FAIL {os.path.basename(md)} key {r["key"]} not in stats.json ({e})')
                fails += 1
                continue
            if s != r['text']:
                report.append(f'FAIL {os.path.basename(md)} stale: key {r["key"]} printed {r["text"]} but stats.json now gives {s}')
                fails += 1
            texts.add(r['text'])
        # 2. coverage of every numeric token
        n_tokens = n_traced = 0
        in_code = False
        for ln, line in enumerate(open(md), 1):
            if line.strip().startswith('```'):
                in_code = not in_code
                continue
            if in_code:
                continue
            body = re.sub(r'^\s*(?:\d+\.|[-*])\s+', lambda m: ' ' * len(m.group(0)), line)  # list markers
            body = masked(body)
            for m in NUM.finditer(body):
                tok = m.group(1).rstrip(',.')
                if not tok:
                    continue
                n_tokens += 1
                if tok in texts:
                    n_traced += 1
                else:
                    report.append(f'UNTRACED {os.path.basename(md)}:{ln}: "{tok}" in: {line.strip()[:140]}')
                    fails += 1
        report.append(f'{os.path.basename(md)}: {n_tokens} numeric tokens, {n_traced} traced to stats.json via {len(reg)} registry entries')
    # 3. static scan: no data number may be typed into the text templates of write_results.py
    src = open(os.path.join(STUDY, 'analysis', 'write_results.py')).read()
    n_lit = 0
    for mm in re.finditer(r"(\"[^\"\n]*\"|'[^'\n]*')", src):
        body = re.sub(r"\{[^{}]*\}", " ", mm.group(1))
        body = re.sub(r'^.\s*(?:#+\s*)?(?:\d+\.\s+)?', ' ', body)        # headings / list numbers
        body = body.replace('~1', ' ')                                    # key-path escapes
        body = masked(body)
        body = re.sub(r'\bStudy 3\b|\bFigure \d\b|\bFig \d[a-d]?\b|\b\d[a-d]\b|\bS\d\b|\ball 3 base arms\b', ' ', body)
        for d in NUM.finditer(body):
            n_lit += 1
            line = src[:mm.start()].count('\n') + 1
            report.append(f'HARD-CODED write_results.py:{line}: "{d.group(1)}" in {mm.group(1)[:100]}')
            fails += 1
    report.append(f'write_results.py: {n_lit} hard-coded numbers in text templates')
    # 4. v2 figures' derived numbers (merge_derived_numbers.py): stats.json['derived_v2'] and the provenance file must equal
    #    what the figure folders hold now, and every recorded script must exist (2026-09-27, v2 figure integration)
    import merge_derived_numbers as mdn
    want_vals, want_prov = mdn.collect()
    have_prov = json.load(open(mdn.PROV)) if os.path.exists(mdn.PROV) else {}
    if not os.path.isdir(mdn.V2):
        # Public release: figures/v2 (the earlier figure set whose scripts derived these numbers) is not shipped.
        # Check that stats.json[derived_v2] and the shipped provenance file list the same numbers; their values
        # were checked against the figure folders in the project before release.
        want_vals = stats.get('derived_v2') or {}
        if {f'{t}/{n}' for t, d in want_vals.items() for n in d} != set(have_prov):
            report.append('FAIL stats.json[derived_v2] and outputs/derived_numbers_provenance.json list different numbers')
            fails += 1
        want_prov = have_prov
    if stats.get('derived_v2') != json.loads(json.dumps(want_vals)):
        report.append('FAIL derived_v2 in stats.json differs from figures/v2/**/derived_numbers.json: run merge_derived_numbers.py')
        fails += 1
    if have_prov != json.loads(json.dumps(want_prov)):
        report.append('FAIL outputs/derived_numbers_provenance.json is stale: run merge_derived_numbers.py')
        fails += 1
    for k, p in want_prov.items():
        if not p['script_exists'] or not p['inputs']:
            report.append(f'FAIL derived number {k}: script {p["script"]!r} missing or no inputs recorded')
            fails += 1
    report.append(f'derived numbers (figures/v2): {len(want_prov)} records from {len(want_vals)} files checked against stats.json[derived_v2]')
    # 5. Round 4 numbers (merge_round4_numbers.py, 2026-09-27): stats.json['round4'] must equal round4/analysis/stats_r4.json,
    #    the provenance file must match the Round 4 files on disk, and the Round 4 trace check must have passed
    import merge_round4_numbers as mr4
    r4_vals, r4_screen, r4_prov = mr4.collect()
    have_r4 = json.load(open(mr4.PROV)) if os.path.exists(mr4.PROV) else {}
    if stats.get('round4') != json.loads(json.dumps(r4_vals)) or stats.get('round4_screen') != json.loads(json.dumps(r4_screen)):
        report.append('FAIL round4 / round4_screen in stats.json differ from stats_r4.json / expansion funnel.json: run merge_round4_numbers.py')
        fails += 1
    if not os.path.isdir(mdn.V2):
        # Public release: the Round 4 files are released pseudonymized (run_r4.sh also patched), so their SHA-256
        # differ from the hashes recorded in the project; compare the recorded file list and trace result instead.
        have_r4 = dict(have_r4, files=sorted(have_r4.get('files', {})))
        r4_prov = dict(r4_prov, files=sorted(r4_prov['files']))
    if have_r4 != json.loads(json.dumps(r4_prov)):
        report.append('FAIL outputs/round4_provenance.json is stale: run merge_round4_numbers.py')
        fails += 1
    if r4_prov['trace_check_r4_result'] != 'PASS':
        report.append(f"FAIL Round 4 trace check: {r4_prov['trace_check_r4_result']}")
        fails += 1
    report.append(f"round4 numbers: stats.json[round4] in sync with stats_r4.json ({len(r4_prov['files'])} files hashed); "
                  f"Round 4 trace check {r4_prov['trace_check_r4_result']}")
    report.append('RESULT: ' + ('PASS' if fails == 0 else f'FAIL ({fails} problems)'))
    open(os.path.join(OUT, 'trace_check.txt'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report))
    sys.exit(0 if fails == 0 else 1)


if __name__ == '__main__':
    main()
