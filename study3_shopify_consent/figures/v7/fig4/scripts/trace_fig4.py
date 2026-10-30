"""Trace check for Figure 4 (v7, ../../DESIGN_V7.md section 11; written for v5): every number printed in the two panels
(axis ticks only), the caption and the alt text is a registered
rendering of a value in the CURRENT stats.json / figures/v7/derived_numbers.json / fig4/derived_numbers.json, and every
registered value still equals its source (so a re-run analysis that changes a number fails this check).

  1. Registry consistency: every row of fig4_numbers.csv (panels) and caption_fig4_numbers.csv (caption + alt text) is
     re-rendered from the current sources; a drawn-only mark (fmt 'mark': dot position, CI end, diamond tip) must still
     equal its registered value.
  2. Coverage: every numeric token in the panel PDFs' text, caption_fig4.tex and alt_text_fig4.txt is a registered
     rendering or an explicitly listed structural token (axis tick labels, the 95% CI level, the Supplementary figure
     reference, the name of the crawl round; v7: the reference to loss point (2) of Fig. 1a, DESIGN_V7 sections 7.4
     and 10 -- a loss numeral and a figure reference, never a measured number; 'Fig.~3a', the plot whose zero-line
     grammar b-right shares, a figure reference).
     v7 tick list: b right's difference axis is -20 to +40 pp by 20 (DESIGN_V7 section 6: at most 4-5 ticks; v6 drew
     -10 to +40 by 10).
Exit 1 on any failure; writes ../trace_fig4.txt. (v4's check_fig4_numbers.py, extended to marks and the alt text.)
"""
import csv
import json
import os
import re
import sys

from pypdf import PdfReader

HERE = os.path.dirname(os.path.abspath(__file__))
FIG4 = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG4, '..', 'style')))
import figstyle as fs  # noqa: E402

D4 = json.load(open(os.path.join(FIG4, 'derived_numbers.json')))
MINUS = fs.MINUS
PANEL_PDFS = ('fig4a_primary.pdf', 'fig4b_like_for_like.pdf')


def value(source, key):
    if source == 'stats':
        return fs.stat(key)
    if source == 'derived':
        return fs.derived(key)
    name, _, rest = key.partition('/')
    return fs._walk(D4[name]['value'], rest) if rest else D4[name]['value']


report, fails, shown = [], 0, set()
for fn in ('fig4_numbers.csv', 'caption_fig4_numbers.csv'):
    rows = list(csv.DictReader(open(os.path.join(FIG4, fn))))
    bad = 0
    for r in rows:
        v = value(r['source'], r['key'])
        if r['fmt'] == 'mark':                     # drawn, not printed: the value must be unchanged
            ok = json.dumps(v) == r['value']
            now = v
        else:
            now = fs.render(v, r['fmt'])
            ok = now == r['text']
            shown.add(r['text'].replace('-', MINUS))
            shown.add(r['text'].replace(',', ''))
            shown.add(r['text'])
        if not ok:
            bad += 1
            report.append(f'STALE {fn}: {r["key"]} registered {r["text"] or r["value"]!r}, now {now!r}')
    fails += bad
    n_marks = sum(r['fmt'] == 'mark' for r in rows)
    report.append(f'{fn}: {len(rows)} registered numbers ({n_marks} drawn-only marks), {bad} stale')

NUM = re.compile(r'(?<![\w.])[-−]?\d[\d,]*(?:\.\d+)?')
# structural tokens: axis tick labels drawn by make_fig4_panels.py (the only numbers printed in the panels)
TICKS_PCT = {str(t) for t in range(0, 101, 25)}                         # a and b left (x): fs.pct_axis 0-100, step 25
TICKS_PP = {fs.fmt_dec(t, 0) for t in range(-20, 41, 20)}               # b right (x): fs.signed_ticks -20..+40 pp (v7)
# identifiers: the 95% CI level, the Supplementary figure reference, '(pp;' and the name of the crawl round
# ('Round~4', the Round 4 expansion: a label, not a measured number); v7: 'Point~(2) of Fig.~1a' (the schematic's loss
# numeral (2) and the figure it is drawn in; DESIGN_V7 sections 7.4, 10) and 'Fig.~3a' (b-right shares the zero-line
# grammar of Fig. 3a-right; a figure reference, never a measured number)
STRUCT = re.compile(r'95\s?(?:\\)?%|Fig\.~?S\d+|\(pp;|Round~4\b|Point~\(2\) of Fig\.~1a\b|Fig\.~3a\b')


def check(label, text, extra_ok=()):
    global fails
    text = STRUCT.sub(' ', text)
    bad = []
    for m in NUM.finditer(text):
        t = m.group(0).replace('-', MINUS)
        if t in shown or t.replace(MINUS, '') in shown or t.replace(',', '') in shown or t in extra_ok:
            continue
        bad.append((t, text[max(0, m.start() - 30):m.end() + 15].replace('\n', ' ')))
    fails += len(bad)
    report.append(f'{label}: {len(NUM.findall(text))} numeric tokens, {len(bad)} untraced')
    for t, ctx in bad:
        report.append(f'  UNTRACED {t!r}: ...{ctx}...')


for pdf, extra in zip(PANEL_PDFS, (TICKS_PCT, TICKS_PCT | TICKS_PP)):
    txt = '\n'.join(p.extract_text() or '' for p in PdfReader(os.path.join(FIG4, 'panels', pdf)).pages)
    check(f'panel {pdf}', txt, extra)
cap = open(os.path.join(FIG4, 'caption_fig4.tex')).read()
cap = '\n'.join(ln for ln in cap.splitlines() if not ln.startswith('%')).replace('$-$', MINUS).replace('\\%', '%')
cap = re.sub(r'\\label\{[^}]*\}', ' ', cap)
check('caption_fig4.tex', cap)
check('alt_text_fig4.txt', open(os.path.join(FIG4, 'alt_text_fig4.txt')).read())
report.append('RESULT: ' + ('PASS' if fails == 0 else f'FAIL ({fails})'))
open(os.path.join(FIG4, 'trace_fig4.txt'), 'w').write('\n'.join(report) + '\n')
print('\n'.join(report))
sys.exit(1 if fails else 0)
