"""Trace check for Figure 6 (v7, ../../DESIGN_V7.md section 11; the method of fig4/scripts/trace_fig4.py and
analysis/trace_check.py; unchanged from v6 except the panel list: a is now a line drawing, fig6a_path.pdf, which must
print no digit at all, beside its per-load plot, fig6a_loads.pdf).

1. Registry consistency: every row of panels/fig6_numbers.csv (make_fig6_panels.py) and caption_fig6_numbers.csv
   (make_caption_fig6.py) is re-rendered from the CURRENT analysis/outputs/stats.json or fig6/derived_numbers.json; a
   printed value must render to the same text, a drawn-only value ('mark': dot position, CI end, count) must be
   unchanged.
2. Coverage, per panel: every numeric token printed in each panel PDF (every text run, read with qa_check's content
   walker so adjacent runs never merge) is a rendering registered by the PANEL script
   (none: it registers drawn marks only, so a number the caption registers cannot excuse one printed in a panel), or
   a tick label of THAT panel's own axis, matched as a whole run (the panels print only tick labels). The allowed ticks
   are listed per panel below, so a count such as '5' is accepted only as a tick of a's count axis, nowhere else; the
   drawing (fig6a_path.pdf) has no allowed token, so any digit in it fails.
3. The composite fig6.pdf adds no numeric text of its own: its numeric runs are exactly the union of the panels'.
4. Coverage of caption_fig6.tex and alt_text_fig6.txt: every numeric token is a registered rendering, or structural
   (the 95% CI level, supplementary figure references).
Writes trace_fig6.txt next to the figure; exit status 1 on any failure.
"""
import collections
import csv
import json
import os
import re
import sys

from pypdf import PdfReader

HERE = os.path.dirname(os.path.abspath(__file__))
FIG6 = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG6, '..', 'style')))
import figstyle as fs  # noqa: E402
import qa_check  # noqa: E402

D6 = json.load(open(os.path.join(FIG6, 'derived_numbers.json')))
NUM = re.compile(r'(?<![\w.\-@#,])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)')
# axis tick labels drawn by make_fig6_panels.py, per panel (whole runs only)
TICKS_PCT = {str(t) for t in range(0, 101, 25)}                       # b, c: fs.pct_axis 0-100, step 25
PANEL_TICKS = {
    'fig6a_path.pdf': set(),                                          # a, left: the line drawing prints no digit
    'fig6a_loads.pdf': {str(t) for t in range(0, 6)},                 # a, right: the count axis, 0-5 ad vendors
    'fig6b_creators.pdf': TICKS_PCT,                                  # b's x axis (v7: rows, as c)
    'fig6c_url.pdf': TICKS_PCT,
    'fig6d_validation.pdf': {'85', '90', '95', '100'},                # d's agreement axis (limits 85-101)
}


def current(row):
    src, key = row['source'], row['key']
    if src == 'stats':
        return fs.stat(key)
    if src == 'derived':
        return fs.derived(key)
    name, _, rest = key.partition('/')
    v = D6[name]['value']
    return fs._walk(v, rest) if rest else v


def runs(pdf):
    rd = PdfReader(pdf)
    wk = qa_check.Walker(rd)
    wk.walk(rd.pages[0].get_contents(), rd.pages[0].get('/Resources'), [1, 0, 0, 1, 0, 0])
    return [r['text'].strip().replace(fs.MINUS, '-') for r in wk.runs if r['text'].strip()]


def main():
    lines, fails = [], 0
    shown = set()                       # every registered printed rendering (caption + alt text)
    shown_by = {}                       # ... per registry: a panel may print only what the PANEL registry printed
    for reg in ('panels/fig6_numbers.csv', 'caption_fig6_numbers.csv'):
        mine = shown_by.setdefault(reg, set())
        rows = list(csv.DictReader(open(os.path.join(FIG6, reg))))
        bad = 0
        for r in rows:
            v = current(r)
            if r['fmt'] == 'mark':
                ok = json.dumps(v) == r['value']
            else:
                ok = fs.typo(fs.render(v, r['fmt'])) == r['shown']
                mine |= {r['shown'].replace(fs.MINUS, '-'), r['text']}
                shown |= {r['shown'].replace(fs.MINUS, '-'), r['text']}
            if not ok:
                bad += 1
                lines.append(f'STALE {reg}: {r["key"]} registered {r["shown"] or r["value"]!r}, now {v!r}')
        fails += bad
        n_marks = sum(r['fmt'] == 'mark' for r in rows)
        lines.append(f'{reg}: {len(rows)} rows ({n_marks} drawn-only marks), {bad} stale')

    # coverage 1: each panel against its own tick list
    panel_numeric = collections.Counter()
    for pdf, ticks in PANEL_TICKS.items():
        n = 0
        for t in runs(os.path.join(FIG6, 'panels', pdf)):
            for m in NUM.finditer(t):
                n += 1
                panel_numeric[t] += 1
                tok = m.group(1)
                if tok in shown_by['panels/fig6_numbers.csv'] or (tok in ticks and t == tok):
                    continue
                fails += 1
                lines.append(f'UNTRACED {pdf}: {tok!r} in run {t!r}')
        lines.append(f'panel {pdf}: {n} numeric tokens (allowed ticks: {", ".join(sorted(ticks, key=float)) or "none"})')
    # coverage 2: the composite adds no numeric text (its numeric runs = the panels' numeric runs)
    comp = collections.Counter(t for t in runs(os.path.join(FIG6, 'fig6.pdf')) if NUM.search(t))
    if comp != panel_numeric:
        fails += 1
        lines.append(f'MISMATCH fig6.pdf numeric runs differ from the panels\': extra {dict(comp - panel_numeric)}, '
                     f'missing {dict(panel_numeric - comp)}')
    lines.append(f'fig6.pdf: {sum(comp.values())} numeric runs, the same as its panels')
    # coverage 3: the caption
    cap = open(os.path.join(FIG6, 'caption_fig6.tex')).read()
    cap = '\n'.join(ln for ln in cap.splitlines() if not ln.lstrip().startswith('%'))
    cap = re.sub(r'95\\%', ' ', cap)                   # CI level
    cap = re.sub(r'Fig\.~S\d+', ' ', cap)              # supplementary figure references
    cap = re.sub(r'\\label\{[^}]*\}', ' ', cap)
    cap = cap.replace('$-$', '-')
    n_cap = 0
    for m in NUM.finditer(cap):
        n_cap += 1
        tok = m.group(1)
        if tok in shown:
            continue
        fails += 1
        i = m.start()
        lines.append(f'UNTRACED caption_fig6.tex: {tok!r} in ...{cap[max(0, i - 40):i + 20]!r}...')
    # coverage 4: the alt text (same registry as the caption; the 95% CI level is structural)
    alt = open(os.path.join(FIG6, 'alt_text_fig6.txt')).read()
    alt = re.sub(r'95% confidence', ' confidence', alt)
    n_alt = 0
    for m in NUM.finditer(alt):
        n_alt += 1
        if m.group(1) not in shown:
            fails += 1
            lines.append(f'UNTRACED alt_text_fig6.txt: {m.group(1)!r}')
    lines.append(f'coverage: {n_cap} numeric tokens in caption_fig6.tex, {n_alt} in alt_text_fig6.txt')
    lines.append('RESULT: ' + ('PASS' if fails == 0 else f'FAIL ({fails})'))
    open(os.path.join(FIG6, 'trace_fig6.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
