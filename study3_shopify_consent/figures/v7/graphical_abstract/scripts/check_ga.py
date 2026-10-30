#!/usr/bin/env python3
"""check_ga.py -- the graphical abstract's own gate, on top of ../style/qa_check.py.

1. Registry: every row of ga_numbers.csv re-renders identically from the CURRENT stats.json, figures/v7/
   derived_numbers.json (source 'derived') or figures/v7/fig4/derived_numbers.json (source 'fig4_derived'); the meter
   shares in derived_numbers.json equal k / n of their sources; tile B's counts equal Fig 4A's (fig4a_entries).
2. Trace: every numeric token printed in graphical_abstract.pdf and in caption_graphical_abstract.tex is a registered
   rendering (the caption's '648 ms before' is the registered '-648' with its sign carried by 'before'); '95%' is
   the CI level. Anything else is UNTRACED.
3. GA rules (FIGURE_PLAN_v2.md section 5; Elsevier legibility at 5 x 13 cm on screen): no text below 10 pt; hero
   numbers 18 pt; at most 26 words besides the numbers ('of' inside 'k of n' counts as part of the number).
Exit 1 on any failure.
"""
import csv
import json
import os
import re
import sys

from pypdf import PdfReader

HERE = os.path.dirname(os.path.abspath(__file__))
GA = os.path.dirname(HERE)
V2 = os.path.dirname(GA)
sys.path.insert(0, os.path.join(V2, 'style'))
import figstyle as fs  # noqa: E402
import qa_check  # noqa: E402

PDF = os.path.join(GA, 'graphical_abstract.pdf')
CAPTION = os.path.join(GA, 'caption_graphical_abstract.tex')
REGISTRY = os.path.join(GA, 'ga_numbers.csv')
DERIVED = os.path.join(GA, 'derived_numbers.json')
FIG4_DERIVED = os.path.join(V2, 'fig4', 'derived_numbers.json')
NUM = re.compile(r'(?<![\w.,])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)')
# 26 since 2026-09-26 (was 25): tile B now states its route, 'fired from sandbox', because its 12 of 19 is Fig 4A's
# sandbox row (13 of 19 fired by some route); the previous 25-word version had cut that qualifier. See QA.md.
MAX_WORDS = 26
MIN_PT = 10.0


def main():
    fails, out = [], []
    reg = list(csv.DictReader(open(REGISTRY)))
    d4 = json.load(open(FIG4_DERIVED))

    def fig4_derived(key):
        name, _, rest = key.partition('/')
        return fs._walk(d4[name]['value'], rest) if rest else d4[name]['value']

    getters = {'stats': fs.stat, 'derived': fs.derived, 'fig4_derived': fig4_derived}
    # 1. registry consistency
    for r in reg:
        get = getters.get(r['source'])
        v = get(r['key']) if get else None
        if v is None:
            fails.append(f'registry row with unknown source: {r}')
            continue
        if fs.render(v, r['fmt']) != r['text']:
            fails.append(f"stale registry row {r['key']}: {r['text']} vs now {fs.render(v, r['fmt'])}")
    d = json.load(open(DERIVED))
    src = {'ga_race_share': (fs.stat('fig5/d/deny/pixels_before'), fs.stat('fig5/d/deny/pixels')),
           'ga_blocked_share': (fs.derived('fig4a_routes/primary_no_yes/sandbox'),
                                fs.derived('fig4a_routes/primary_no_yes/n'))}
    for name, (k, n) in src.items():
        rec = d.get(name)
        if rec is None or abs(rec['value'] - k / n) > 1e-12 or (rec['k'], rec['n']) != (k, n):
            fails.append(f'derived {name} is missing or stale')
    unknown = set(d) - set(src)
    if unknown:
        fails.append(f'derived values without a check: {sorted(unknown)}')
    # tile B = the Fig 4A hero (same entries, same unit)
    c4 = fig4_derived('fig4a_entries/counts')
    if (c4['sandbox'], c4['n']) != src['ga_blocked_share']:
        fails.append(f"tile B {src['ga_blocked_share']} != Fig 4A top row {(c4['sandbox'], c4['n'])}")
    registered = {r['text'].replace(',', '') for r in reg} | {r['text'].lstrip('-').replace(',', '') for r in reg}
    out.append(f'registry: {len(reg)} rendered numbers, all re-render from current stats.json / derived numbers; '
               f"tile B = Fig 4A top row ({c4['sandbox']} of {c4['n']} entries)" if not fails else
               'registry: see failures')

    # 2a. numbers and text in the PDF
    wk = qa_check.Walker(PdfReader(PDF))
    page = PdfReader(PDF).pages[0]
    wk.walk(page.get_contents(), page.get('/Resources'), [1, 0, 0, 1, 0, 0])
    runs = [x for x in wk.runs if x['text'].strip()]
    text = ' '.join(x['text'] for x in runs)
    sizes = sorted({round(x['size'], 2) for x in runs})
    out.append(f'PDF text sizes (pt): {sizes}')
    small = [x for x in runs if x['size'] < MIN_PT - 0.05]
    if small:
        fails.append('text below 10 pt: ' + '; '.join(f"{x['size']:.2f} {x['text']!r}" for x in small[:6]))
    heroes = [x for x in runs if x['size'] > 12]
    if any(abs(x['size'] - fs.FS['hero']) > 0.1 for x in heroes):
        fails.append('a hero number is not 18 pt')
    # tile C's unit is the one Fig 1 badge 3, Fig 5C and the caption use for 535 of 545: sandboxes, not pixels
    if 'sandboxes beat the' not in re.sub(r'\s+', ' ', text):
        fails.append("tile C does not read 'sandboxes beat the ...' (Fig 1 / Fig 5C unit)")
    pdf_nums = NUM.findall(text)
    untraced = [t for t in pdf_nums if t.replace(',', '') not in registered]
    out.append(f'PDF numbers: {pdf_nums}')
    if untraced:
        fails.append(f'UNTRACED numbers in the PDF: {untraced}')

    # 2b. numbers in the caption
    cap = open(CAPTION).read().split('\n', 1)[1]           # skip the generated-file comment line
    cap_masked = re.sub(r'95\\?%', ' ', cap)
    cap_nums = NUM.findall(cap_masked)
    untraced = [t for t in cap_nums if t.replace(',', '') not in registered]
    out.append(f'caption numbers: {cap_nums}')
    if untraced:
        fails.append(f'UNTRACED numbers in the caption: {untraced}')

    # 3. word budget (numbers, and 'of' inside 'k of n', do not count)
    words_text = re.sub(r'\d[\d,]*\s+of\s+\d[\d,]*', ' ', text)
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'’‘`-]*", words_text)]
    out.append(f'words besides numbers: {len(words)} (max {MAX_WORDS}): {" ".join(words)}')
    if len(words) > MAX_WORDS:
        fails.append(f'{len(words)} words (max {MAX_WORDS})')

    print('\n'.join(out))
    for f in fails:
        print('FAIL ' + f)
    print('check_ga: ' + ('PASS' if not fails else f'FAIL ({len(fails)})'))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
