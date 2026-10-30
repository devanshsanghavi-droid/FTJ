"""Trace check for Figure 5 (v7, ../../DESIGN_V7.md section 11; written for v5): every number printed in fig5.pdf (axis
ticks only),
caption_fig5.tex and alt_text_fig5.txt comes from saved outputs.

  1. Registry consistency: each row of panels/fig5_numbers.csv and panels/caption_fig5_numbers.csv (caption + alt text)
     is re-rendered from the CURRENT analysis/outputs/stats.json, figures/v7/derived_numbers.json or
     figures/v7/fig5/derived_numbers.json; a mismatch means the figure or caption is stale. Rows with fmt 'mark' (values
     drawn but not printed -- dot positions, CI ends, bar and segment counts, per-load lags) must still equal their
     source value exactly.
  2. Axis ticks: every numeric tick label recorded by make_fig5_panels.py (panels/fig5_ticks.csv) must be one of the axis
     scales listed in ALLOWED_TICKS (category labels, which are words, are exempt): a (y) 0-100 % in steps of 25 (v7:
     DESIGN_V7 section 6, share axes run 0-100, as Fig. S8a v7); b (x, v7:
     thin horizontal share bars, DESIGN_V7 section 8.7) 0-100 % in steps of 25; c x the signed decades of the symmetric-log race axis (-1, -0.1, -0.01, 0, +0.01, +0.1, +1 s); c y the
     round row counts 1, 25, 50, 100 (rows are counted within each block). A tick outside the list fails, so a data
     value (e.g. a block's load count) can never pass as a tick.
  3. Coverage: every numeric token in the figure's text (read from the composite PDF, including the nested panels) is
     an allowed axis tick (the panels print no data numbers: DESIGN_V7 section 1), and every numeric token in the
     caption and in the alt text is a registered rendering or a structural token (the 95% CI level, figure references
     such as S8a). Anything else is UNTRACED.
Same rules as analysis/trace_check.py (which covers RESULTS.md and takeaways.md). Exit code 1 on any failure.
Run: python3 figures/v7/fig5/scripts/trace_fig5.py
"""
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIG5 = os.path.normpath(os.path.join(HERE, '..'))
STYLE = os.path.normpath(os.path.join(FIG5, '..', 'style'))
sys.path.insert(0, STYLE)
import figstyle as fs  # noqa: E402
import qa_check  # noqa: E402  (its content walker decodes text inside nested panel XObjects)
from pypdf import PdfReader  # noqa: E402

NUM = re.compile(r'(?<![\w.])(\d[\d,]*(?:\.\d+)?)')
STRUCT = re.compile(r'95\\?\s?%|Fig\.?~?\s?S\d+[A-D]?')
# axis scales (make_fig5_panels.py): a fs.pct_axis 0-100 step 25 (y; v7 moved it from 0-60 step 20 to the section 6
# share scale, with Fig. S8a); b fs.pct_axis 0-100 step 25 (x: the bars are
# horizontal in v7, DESIGN_V7 section 8.7 -- the same tick list moved from b's y axis to its x axis);
# c x: the decades of the symmetric-log race axis (race_tick_label); c y: round row counts within each block
ALLOWED_TICKS = {('a', 'y'): {str(t) for t in range(0, 101, 25)},
                 ('b', 'x'): {str(t) for t in range(0, 101, 25)},
                 ('c', 'x'): {fs.MINUS + '1', fs.MINUS + '0.1', fs.MINUS + '0.01', '0', '+0.01', '+0.1', '+1'},
                 ('c', 'y'): {'1', '25', '50', '100'}}


def local_derived(key):
    d = json.load(open(os.path.join(FIG5, 'derived_numbers.json')))
    name, _, rest = key.partition('/')
    cur = d[name]['value']
    for part in rest.split('/') if rest else []:
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    return cur


def nums(s):
    return [m.group(1).rstrip(',') for m in NUM.finditer(s)]


def main():
    fails, report = 0, []
    registered = set()
    for fn in ('fig5_numbers.csv', 'caption_fig5_numbers.csv'):
        rows = list(csv.DictReader(open(os.path.join(FIG5, 'panels', fn))))
        bad = 0
        for r in rows:
            src = r['source']
            v = fs.stat(r['key']) if src == 'stats' else fs.derived(r['key']) if src == 'derived' else local_derived(r['key'])
            if r['fmt'] == 'mark':                      # drawn, not printed: the value must be unchanged
                if json.dumps(v) != r['value']:
                    bad += 1
                    report.append(f'STALE {fn}: drawn mark {r["key"]} changed in its source')
                continue
            now = fs.typo(fs.render(v, r['fmt']))
            if now != r['shown']:
                bad += 1
                report.append(f'STALE {fn}: {r["key"]} shows {r["shown"]!r}, sources now give {now!r}')
            registered.update(nums(r['shown']))
        fails += bad
        n_mark = sum(r['fmt'] == 'mark' for r in rows)
        report.append(f'{fn}: {len(rows) - n_mark} registered numbers + {n_mark} drawn marks, {bad} stale')
    tick_rows = list(csv.DictReader(open(os.path.join(FIG5, 'panels', 'fig5_ticks.csv'))))
    num_rows = [r for r in tick_rows if re.search(r'\d', r['text'])]          # category ticks (words) carry no number
    bad_ticks = [r for r in num_rows if r['text'] not in ALLOWED_TICKS.get((r['panel'], r['axis']), set())]
    report.append(f'fig5_ticks.csv: {len(tick_rows)} tick labels ({len(num_rows)} numeric), {len(bad_ticks)} numeric '
                  f'outside the axis scales')
    for r in bad_ticks:
        report.append(f"  BAD TICK panel {r['panel']} {r['axis']}: {r['text']!r}")
    fails += len(bad_ticks)
    ticks = {t for r in tick_rows for t in nums(r['text'])}

    # figure text, from the composite PDF (panels are nested form XObjects)
    wk = qa_check.Walker(PdfReader(os.path.join(FIG5, 'fig5.pdf')))
    r0 = wk.reader.pages[0]
    wk.walk(r0.get_contents(), r0.get('/Resources'), [1, 0, 0, 1, 0, 0])
    fig_text = [x['text'] for x in wk.runs if x['text'].strip()]
    untraced, n_tok = [], 0
    for t in fig_text:
        for tok in nums(t):
            n_tok += 1
            if tok not in ticks:                       # the panels print axis ticks only
                untraced.append((t, tok))
    report.append(f'fig5.pdf: {n_tok} numeric tokens in {len(fig_text)} text runs (axis ticks only); {len(untraced)} untraced')
    for t, tok in untraced:
        report.append(f'  UNTRACED figure token {tok!r} in {t!r}')
    fails += len(untraced)

    # caption
    cap = open(os.path.join(FIG5, 'caption_fig5.tex')).read()
    cap = '\n'.join(l for l in cap.splitlines() if not l.startswith('%'))
    masked = STRUCT.sub(' ', cap)
    cu, n_tok = [], 0
    for tok in nums(masked):
        n_tok += 1
        if tok not in registered:
            cu.append(tok)
    report.append(f'caption_fig5.tex: {n_tok} numeric tokens; {len(cu)} untraced' + (f': {cu}' if cu else ''))
    fails += len(cu)

    # alt text (same registry as the caption)
    alt = open(os.path.join(FIG5, 'alt_text_fig5.txt')).read()
    au, n_tok = [], 0
    for tok in nums(STRUCT.sub(' ', alt)):
        n_tok += 1
        if tok not in registered:
            au.append(tok)
    report.append(f'alt_text_fig5.txt: {n_tok} numeric tokens; {len(au)} untraced' + (f': {au}' if au else ''))
    fails += len(au)
    report.append('RESULT: ' + ('PASS' if fails == 0 else f'FAIL ({fails})'))
    txt = '\n'.join(report)
    open(os.path.join(FIG5, 'trace_fig5.txt'), 'w').write(txt + '\n')
    print(txt)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
