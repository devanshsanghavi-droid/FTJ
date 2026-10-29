"""Trace check: every number printed in RESULTS.md and figures/takeaways.md must come from saved outputs.

Checks
  1. Registry consistency: each row of outputs/number_registry_*.csv is re-rendered from the CURRENT
     outputs/stats.json; a mismatch means the text is stale.
  2. Coverage: every numeric token in the Markdown files is either (a) a registered rendering, or
     (b) a structural token (figure/panel/arm/prediction labels, dates, file names, list numbering,
     the "95%" CI level, table headers). Anything else is reported as UNTRACED.
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
    report.append('RESULT: ' + ('PASS' if fails == 0 else f'FAIL ({fails} problems)'))
    open(os.path.join(OUT, 'trace_check.txt'), 'w').write('\n'.join(report) + '\n')
    print('\n'.join(report))
    sys.exit(0 if fails == 0 else 1)


if __name__ == '__main__':
    main()
