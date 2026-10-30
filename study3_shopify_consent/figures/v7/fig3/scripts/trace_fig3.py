"""Trace check for Figure 3 (v7, ../../DESIGN_V7.md section 11; written for v5): every number printed in the two
panels (in v7: the axis ticks and the threshold in a's grey note, a registered rendering; the direct labels and the
group names are words), the caption and the alt text is a
registered rendering of a value in the CURRENT stats.json /
figures/v7/derived_numbers.json / fig3/derived_numbers.json, and every registered value still equals its source (so a
re-run analysis that changes a number fails this check).

  1. Registry consistency: every row of panels/fig3_numbers.csv (panels) and caption_fig3_numbers.csv (caption + alt
     text) is re-rendered from the current sources; a drawn-only mark (fmt 'mark': dot position, CI end, diamond) must
     still equal its registered value.
  2. Coverage: every numeric token in the panel PDFs' text, caption_fig3.tex and alt_text_fig3.txt is a registered
     rendering or an explicitly listed structural token: the axis tick labels drawn by make_fig3_panels.py (per panel,
     taken from that script's own axis constants), the 95% CI level and the Supplementary figure reference.
Exit 1 on any failure; writes ../trace_fig3.txt.
"""
import csv
import json
import os
import re
import sys

from pypdf import PdfReader

HERE = os.path.dirname(os.path.abspath(__file__))
FIG3 = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG3, '..', 'style')))
sys.path.insert(0, HERE)
import figstyle as fs  # noqa: E402
import make_fig3_panels as P  # noqa: E402  (the axis constants: what the tick labels can be)

D3 = json.load(open(os.path.join(FIG3, 'derived_numbers.json')))
MINUS = fs.MINUS


def value(source, key):
    if source == 'stats':
        return fs.stat(key)
    if source == 'derived':
        return fs.derived(key)
    name, _, rest = key.partition('/')
    return fs._walk(D3[name]['value'], rest) if rest else D3[name]['value']


report, fails, shown = [], 0, set()
for fn in ('panels/fig3_numbers.csv', 'caption_fig3_numbers.csv'):
    rows = list(csv.DictReader(open(os.path.join(FIG3, fn))))
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
# structural tokens: the axis tick labels drawn by make_fig3_panels.py (v7: the only numbers printed in the panels)
TICKS_PCT = {str(t) for t in range(0, 101, 25)}                              # a left (x) and b (y): 0-100 %, step 25
TICKS_PP = {fs.fmt_dec(t, 0) for t in range(P.D_LO, P.D_HI + 1, P.D_STEP)}  # a right (x): fs.signed_ticks, pp
                                                                             # (v7 r1: -20 ... +60)
# identifiers: the 95% CI level and the Supplementary figure reference
STRUCT = re.compile(r'95\s?(?:\\)?%|Fig\.~?S\d+')
PANEL_TICKS = {'fig3a_default.pdf': TICKS_PCT | TICKS_PP, 'fig3b_purpose.pdf': TICKS_PCT}


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


pdfs = sorted(f for f in os.listdir(os.path.join(FIG3, 'panels')) if f.endswith('.pdf'))
assert pdfs == sorted(PANEL_TICKS), f'unexpected panel PDFs (a stale panel would escape the check): {pdfs}'
for pdf in pdfs:
    txt = '\n'.join(p.extract_text() or '' for p in PdfReader(os.path.join(FIG3, 'panels', pdf)).pages)
    check(f'panel {pdf}', txt, PANEL_TICKS[pdf])
cap = open(os.path.join(FIG3, 'caption_fig3.tex')).read()
cap = '\n'.join(ln for ln in cap.splitlines() if not ln.startswith('%')).replace('$-$', MINUS).replace('\\%', '%')
cap = re.sub(r'\\label\{[^}]*\}', ' ', cap)
check('caption_fig3.tex', cap)
check('alt_text_fig3.txt', open(os.path.join(FIG3, 'alt_text_fig3.txt')).read())
report.append('RESULT: ' + ('PASS' if fails == 0 else f'FAIL ({fails})'))
open(os.path.join(FIG3, 'trace_fig3.txt'), 'w').write('\n'.join(report) + '\n')
print('\n'.join(report))
sys.exit(1 if fails else 0)
