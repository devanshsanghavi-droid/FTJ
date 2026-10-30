"""Trace check for Figure 1 (v6 RESTRAINT): every number printed in fig1.pdf, caption_fig1.tex and alt_text_fig1.txt comes from
saved outputs.

1. Registry consistency: each row of fig1_numbers.csv (figure), caption_fig1_numbers.csv (caption) and
   alt_text_fig1_numbers.csv (alt text) is re-rendered from the CURRENT analysis/outputs/stats.json or
   figures/v7/fig1/derived_numbers.json; a mismatch = stale text. Drawn-only values (fmt 'mark') must be unchanged.
   A fmt '<f>/1000' row is a time stored in ms and shown in seconds.
2. Figure coverage: every numeric token in the PDF's text runs (read with qa_check.Walker, nested panels included) is a
   registered rendering (counted: each registered rendering may be printed once), or structural: an axis tick label
   (b: make_panels.B_TICKLABELS, seconds from the banner '0', '+0.5' ... '+2'; c: x -4 to +8 by 2, signed, and y rows
   1, 50, 100, 150, 200 = make_panels.Y_TICKS_C). v7 (../../DESIGN_V7.md section 7.4): panel a prints no data number;
   its only digits are the five outlined loss numerals 1-5 (make_panels.LOSS_NUMERALS), each exactly once, at
   FS['numeral'], regular weight -- any other digit in /Fm0 fails, and so does a missing or repeated numeral. Every
   registered rendering must be found.
   The caption must name the same five points, '(1)~' to '(5)~' in order, in its panel-a text (structural tokens).
3. Caption and alt-text coverage: the same, for caption_fig1.tex ('95%', the leak numbers '(1)'-'(5)' and figure
   references such as 'Fig.~5c', 'Fig.~S6e' are structural) and for alt_text_fig1.txt.
Exit 1 on any failure. Run after build.sh:  python3 figures/v7/fig1/scripts/trace_fig1.py
"""
import collections
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIG1 = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG1, '..', 'style')))
import figstyle as fs  # noqa: E402
import qa_check as qa  # noqa: E402
from pypdf import PdfReader  # noqa: E402

NUM = re.compile(r'(?<![\w.])(\d[\d,]*(?:\.\d+)?)')
FIGREF = r'Fig(?:ure)?s?\.?~?\s*S?\d+[a-eA-E]?(?:(?:,|~and|;)\s*(?:Fig\.~?)?S?\d+[a-eA-E]?)*'
DER = json.load(open(os.path.join(FIG1, 'derived_numbers.json')))
fails, report = [], []


def current(row):
    if row['source'] == 'stats':
        return fs.stat(row['key'])
    if row['source'] == 'fig1_derived':
        name, _, rest = row['key'].partition('/')
        return fs._walk(DER[name]['value'], rest) if rest else DER[name]['value']
    raise ValueError(row['source'])


def rerender(row, v):
    f = row['fmt']
    if f.endswith('/1000'):
        return fs.render(v / 1000.0, f[:-5])
    return fs.render(v, f)


def check_registry(fn):
    rows = list(csv.DictReader(open(os.path.join(FIG1, fn))))
    shown = collections.Counter()
    for r in rows:
        try:
            v = current(r)
        except Exception as e:  # noqa: BLE001
            fails.append(f'{fn}: key {r["key"]} not found ({e})')
            continue
        if r['fmt'] == 'mark':
            if json.dumps(v) != r['value']:
                fails.append(f'{fn}: drawn value {r["key"]} changed since the build')
            continue
        s = rerender(r, v)
        if s != r['text']:
            fails.append(f'{fn}: stale {r["key"]}: printed {r["text"]}, sources now give {s}')
        shown[r['shown'].replace(',', '')] += 1
    report.append(f'{fn}: {len(rows)} registered rows re-rendered from current sources')
    return shown


def coverage(name, text, reg):
    used = collections.Counter()
    n = 0
    for m in NUM.finditer(text):
        n += 1
        tok = m.group(1).replace(',', '')
        used[tok] += 1
        if used[tok] > reg[tok]:
            i = m.start()
            fails.append(f'{name}: "{m.group(1)}" in ...{text[max(0, i - 40):i + 20]!r}... is not a registered rendering')
    unused = {k: v - used[k] for k, v in reg.items() if v > used[k]}
    if unused:
        fails.append(f'{name}: registry entries not found in the text: {unused}')
    return n


def main():
    fig_reg = check_registry('fig1_numbers.csv')
    cap_reg = check_registry('caption_fig1_numbers.csv')
    alt_reg = check_registry('alt_text_fig1_numbers.csv')

    # ---- figure text
    r = PdfReader(os.path.join(FIG1, 'fig1.pdf'))
    w = qa.Walker(r)
    p = r.pages[0]
    w.walk(p.get_contents(), p.get('/Resources'), [1, 0, 0, 1, 0, 0])
    sys.path.insert(0, HERE)
    import make_panels as mp
    ticks = {'/Fm1': set(mp.B_TICKLABELS),                                                  # b: s from the banner
             '/Fm2': ({'0'} | {fs.MINUS + str(v) for v in (2, 4)} | {'+' + str(v) for v in (2, 4, 6, 8)} |   # c: x
                      {str(v) for v in mp.Y_TICKS_C})}                                                       # c: y rows
    runs, n_struct, numerals = [], 0, []
    for x in w.runs:
        t = x['text'].strip()
        if not re.search(r'\d', t):
            continue
        bold = 'bold' in x['font'].lower()
        if x['panel'] in ticks and t in ticks[x['panel']] and not bold and abs(x['size'] - fs.FS['tick']) < 0.05:
            n_struct += 1
            continue                                          # axis tick label
        if (x['panel'] == '/Fm0' and t in {str(i) for i in mp.LOSS_NUMERALS} and not bold
                and abs(x['size'] - fs.FS['numeral']) < 0.05):
            numerals.append(t)
            n_struct += 1
            continue                                          # a loss numeral (structural)
        if x['panel'] == '/Fm0':
            fails.append(f'fig1.pdf: panel a prints {t!r} (v7: no data numbers in the schematic; only the loss numerals)')
        n_struct += len(re.findall(r'Fig\.', t))
        runs.append(re.sub(FIGREF, ' ', t))
    if sorted(numerals) != [str(i) for i in mp.LOSS_NUMERALS]:
        fails.append(f'fig1.pdf: panel a loss numerals {sorted(numerals)} (must be 1-5, each exactly once)')
    n_tok = coverage('fig1.pdf', '\n'.join(runs), fig_reg)
    report.append(f'fig1.pdf: {n_tok} data numbers traced to the registry; {n_struct} structural tokens '
                  f'(axis tick labels and the {len(numerals)} loss numerals of a)')

    # ---- caption text
    cap = open(os.path.join(FIG1, 'caption_fig1.tex')).read()
    cap = '\n'.join(ln for ln in cap.splitlines() if not ln.lstrip().startswith('%'))
    cap_a = cap[cap.index('(a)~'):cap.index('(b)~')]
    if re.findall(r'\((\d)\)~', cap_a) != [str(i) for i in mp.LOSS_NUMERALS]:
        fails.append("caption_fig1.tex: panel a's text must name the loss points (1)~ to (5)~ once each, in order "
                     '(they are the outlined numerals of a)')
    cap = re.sub(r'\\label\{[^}]*\}', ' ', cap)
    cap = re.sub(FIGREF + r'|\(\d\)~?|95\\%', ' ', cap)
    cap = cap.replace('--', ' ').replace('~', ' ').replace('$-$', '-')
    n_cap = coverage('caption_fig1.tex', cap, cap_reg)
    report.append(f'caption_fig1.tex: {n_cap} numbers traced to the caption registry')

    # ---- alt text
    alt = open(os.path.join(FIG1, 'alt_text_fig1.txt')).read()
    alt = re.sub(r'\(\d\)', ' ', alt)
    n_alt = coverage('alt_text_fig1.txt', alt, alt_reg)
    report.append(f'alt_text_fig1.txt: {n_alt} numbers traced to the alt-text registry')

    for f in fails:
        report.append('FAIL ' + f)
    report.append('RESULT: ' + ('PASS' if not fails else f'FAIL ({len(fails)} problems)'))
    print('\n'.join(report))
    open(os.path.join(FIG1, 'trace_fig1.txt'), 'w').write('\n'.join(report) + '\n')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
