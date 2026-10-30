"""Trace check for Figure 2 (v7; ../../DESIGN_V7.md section 11): every number printed in fig2.pdf, in caption_fig2.tex,
in alt_text_fig2.txt and in the companion Supplementary Table S-arms (fig2/tableS_arms.tex) must come from the data.

  1. Staleness: every registry row (panels/fig2_numbers.csv, caption_fig2_numbers.csv, tableS_arms_numbers.csv) is
     re-rendered from the CURRENT stats.json / derived_numbers.json files; a mismatch means the figure or caption is
     stale. Drawn-only rows (fmt 'mark': c's median moments and protocol windows) must hold the same value; a fmt
     '<f>/1000' row is a time stored in ms and shown in seconds.
  2. Coverage: every numeric token in the figure's text (read from the PDF, nested panels included) and in the caption
     must be a registered rendering, part of a registered string (the test code), or structural: figure / panel
     references, and -- v7 -- the tick labels of c's time axis ('0', '+5', '+10', '+15', '+20' = make_fig2_panels.
     C_TICKLABELS; v7.1 adds '+20' so that the axis covers the reload), accepted only in c's panel form, at the tick
     size, regular weight, each exactly once. Anything else is UNTRACED.
  3. Redaction: no unmasked identifying string (product slug, account number) anywhere.
  4. Panel d moved to Fig 6d: no '(d)' in the caption and no 'Fig. 2d' reference in the caption or the table.
Writes trace_fig2.txt next to the figure; exit status 1 on any failure.
"""
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIG2 = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG2, '..', 'style')))
import figstyle as fs  # noqa: E402
import qa_check  # noqa: E402
sys.path.insert(0, HERE)
import redact  # noqa: E402
from pypdf import PdfReader  # noqa: E402

F2 = json.load(open(os.path.join(FIG2, 'derived_numbers.json')))
REGS = [os.path.join(FIG2, 'panels', 'fig2_numbers.csv'), os.path.join(FIG2, 'caption_fig2_numbers.csv'),
        os.path.join(FIG2, 'tableS_arms_numbers.csv')]
TABLE = os.path.join(FIG2, 'tableS_arms.tex')
NUM = re.compile(r'(?<![\w.])[\u2212\-+]?\d[\d,]*(?:\.\d+)?')
sys.path.insert(0, HERE)
import make_fig2_panels as mp  # noqa: E402  (C_TICKLABELS, C_AXIS_TITLE)
C_TICKS = set(mp.C_TICKLABELS)                                     # c: s from the page's load event (structural)
report, fails = [], 0


def current(row):
    src, key, f = row['source'], row['key'], row['fmt']
    if src == 'stats':
        v = fs.stat(key)
    elif src == 'derived':
        v = fs.derived(key)
    elif src == 'fig2_derived':
        name, _, sub = key.partition('/')
        v = fs._walk(F2[name]['value'], sub)
    else:
        raise ValueError(src)
    if f.startswith('str'):
        mask = f.partition(':mask=')[2]          # a masked string is registered, and re-derived, only in masked form
        return str(redact.apply(mask, v)) if mask else str(v)
    if f == 'mark':                              # drawn, not printed: the value itself must be unchanged
        return row['text'] if json.dumps(v) == row['value'] else 'CHANGED ' + json.dumps(v)
    if f.endswith('/1000'):                      # a time stored in ms, shown in s
        return fs.render(v / 1000.0, f[:-5])
    return fs.render(v, f)


shown, strings = set(), []
for reg in REGS:
    rows = list(csv.DictReader(open(reg)))
    bad = [r for r in rows if current(r) != r['text']]
    for r in bad:
        report.append(f'STALE {os.path.basename(reg)}: {r["key"]} shows {r["text"]!r}, source now {current(r)!r}')
    fails += len(bad)
    report.append(f'{os.path.basename(reg)}: {len(rows)} registered values, {len(bad)} stale')
    for r in rows:
        if r['fmt'] == 'mark':
            continue
        if r['fmt'].startswith('str'):
            strings.append(r['shown'])
        else:
            shown.add(r['shown'].replace(fs.MINUS, '-'))


def in_strings(tok):
    return any(tok in s for s in strings)


# ---- figure text (PDF, nested panel forms included)
rd = PdfReader(os.path.join(FIG2, 'fig2.pdf'))
wk = qa_check.Walker(rd)
wk.walk(rd.pages[0].get_contents(), rd.pages[0].get('/Resources'), [1, 0, 0, 1, 0, 0])
text = ' '.join(x['text'] for x in wk.runs).replace(fs.MINUS, '-')
# c's panel form: the one that holds c's axis title
c_forms = {x['panel'] for x in wk.runs if x['text'].strip() == mp.C_AXIS_TITLE}
assert len(c_forms) == 1, c_forms
untraced, n_tok, n_ticks = [], 0, 0
for x in wk.runs:
    t = x['text'].strip()
    if not re.search(r'\d', t):
        continue
    if (x['panel'] in c_forms and t in C_TICKS and 'bold' not in x['font'].lower()
            and abs(x['size'] - fs.FS['tick']) < 0.05):
        n_ticks += 1
        n_tok += 1
        continue                                                   # an axis tick label of c (structural)
    tt = t.replace(fs.MINUS, '-')
    for m in NUM.finditer(tt):
        tok = m.group(0).lstrip('+-')
        n_tok += 1
        if tok in shown or in_strings(tok):
            continue
        untraced.append((tok, f'[{x["panel"]}] {tt[:60]}'))
assert n_ticks == len(C_TICKS), ('c: every tick label printed once', n_ticks)
report.append(f'figure text: {n_tok} numeric tokens ({n_ticks} of them c\'s tick labels), {len(untraced)} untraced')
for t, ctx in untraced:
    report.append(f'  UNTRACED (figure) {t!r}: ...{ctx}...')
fails += len(untraced)

# ---- caption
cap = open(os.path.join(FIG2, 'caption_fig2.tex')).read()
cap = '\n'.join(l for l in cap.splitlines() if not l.lstrip().startswith('%'))
cap = re.sub(r'\\label\{[^}]*\}', ' ', cap)
moved = [m.group(0) for m in re.finditer(r'\(d\)|Fig\.~?2d', cap)]
cap = re.sub(r'Fig\.~?S?\d[A-Da-d]?', ' ', cap)                       # figure references (lowercase panels)
cap = cap.replace('--', '-')
untraced, n_tok = [], 0
for m in NUM.finditer(cap):
    tok = m.group(0).lstrip('+-')
    n_tok += 1
    if tok in shown or in_strings(tok):
        continue
    untraced.append((tok, cap[max(0, m.start() - 30):m.end() + 15].replace('\n', ' ')))
report.append(f'caption: {n_tok} numeric tokens, {len(untraced)} untraced')
for t, ctx in untraced:
    report.append(f'  UNTRACED (caption) {t!r}: ...{ctx}...')
fails += len(untraced)

# ---- alt text (scripts/make_caption_fig2.py)
alt = open(os.path.join(FIG2, 'alt_text_fig2.txt')).read()
untraced, n_tok = [], 0
for m in NUM.finditer(alt):
    tok = m.group(0).lstrip('+-').rstrip(',')
    n_tok += 1
    if tok in shown or in_strings(tok):
        continue
    untraced.append((tok, alt[max(0, m.start() - 30):m.end() + 15].replace('\n', ' ')))
report.append(f'alt text: {n_tok} numeric tokens, {len(untraced)} untraced')
for t, ctx in untraced:
    report.append(f'  UNTRACED (alt text) {t!r}: ...{ctx}...')
fails += len(untraced)

# ---- Supplementary Table S-arms (scripts/make_table_arms.py)
tab = open(TABLE).read()
tab = '\n'.join(l for l in tab.splitlines() if not l.lstrip().startswith('%'))
moved += [m.group(0) + ' (table)' for m in re.finditer(r'Fig\.~?2d', tab)]
tab = re.sub(r'\\label\{[^}]*\}', ' ', tab)
tab = re.sub(r'Fig\.~?S?\d[A-Da-d]?', ' ', tab)                       # figure references (v4: lowercase panels)
tab = tab.replace(r'\code{Sec-GPC:~1}', ' ')                          # the header's value (structural)
tab = re.sub(r"p\{\d+mm\}|\\hspace\{\d+pt\}|\\hsize=\d\.\d|\\\\\[\d+pt\]", " ", tab)             # column spec
untraced, n_tok = [], 0
for m in NUM.finditer(tab):
    tok = m.group(0).lstrip('+-').rstrip(',')                           # '150,' at a clause end
    n_tok += 1
    if tok in shown or in_strings(tok):
        continue
    untraced.append((tok, tab[max(0, m.start() - 30):m.end() + 15].replace('\n', ' ')))
report.append(f'table S-arms: {n_tok} numeric tokens, {len(untraced)} untraced')
for t, ctx in untraced:
    report.append(f'  UNTRACED (table) {t!r}: ...{ctx}...')
fails += len(untraced)

report.append(f'panel d moved to Fig 6d: no "(d)" or "Fig. 2d" left in caption or table: '
              f'{"yes" if not moved else "NO: " + ", ".join(moved)}')
fails += len(moved)

# ---- redaction: no unmasked identifying string (product slug, account number) in the figure, caption or registries
wr = fs.derived('fig2b_worked_request')
acct = re.findall(r'\d{5,}', wr['path'])   # release: masked as <account> in the public derived numbers
secrets = {'product slug': wr['carried_path'].split('/')[2], **({'account number': acct[0]} if acct else {})}
leaks = []
for where, body in [('figure text', text), ('caption', open(os.path.join(FIG2, 'caption_fig2.tex')).read())] + \
        [(os.path.basename(r), open(r).read()) for r in REGS + [os.path.join(FIG2, 'build', 'fig2_numbers.tex'),
                                                            os.path.join(FIG2, 'alt_text_fig2.txt'), TABLE]]:
    leaks += [f'{what} in {where}' for what, sec in secrets.items() if sec in body]
report.append(f'redaction: product slug and account number absent from figure, caption and registries: '
              f'{"yes" if not leaks else "NO"}')
for lk in leaks:
    report.append(f'  LEAK {lk}')
fails += len(leaks)

report.append('RESULT: ' + ('PASS' if not fails else f'FAIL ({fails})'))
open(os.path.join(FIG2, 'trace_fig2.txt'), 'w').write('\n'.join(report) + '\n')
print('\n'.join(report))
sys.exit(1 if fails else 0)
