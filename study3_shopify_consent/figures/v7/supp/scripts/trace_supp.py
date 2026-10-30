"""trace_supp.py -- trace check for the v2 Supplementary Figures (the project's trace_check.py covers RESULTS.md and
takeaways.md only; this applies the same two checks to figS1-S10 and caption_supp.tex).

1. Registry consistency: every number a panel script or make_captions.py rendered (panels/*_numbers.csv) is re-rendered
   from the CURRENT stats.json / derived_numbers.json (or, for numbers read from an analysis table, found in that table);
   a mismatch means a figure is stale.
2. Coverage: every numeric token in each figure PDF and in caption_supp.tex is either a registered rendering, or a
   structural token: axis tick labels (listed per figure below), the 95% CI level, figure / panel names, arm and
   Consent Mode codes (G111, 'npa=1'), the numbered list in S1. Anything else is reported as UNTRACED.
Writes ../trace_supp.txt; exit 1 on any failure.
"""
import csv
import glob
import json
import os
import re
import sys

import pandas as pd
from pypdf import PdfReader

from supp_common import AOUT, SUPP, fs

S = json.load(open(fs.STATS_JSON))
DV2 = json.load(open(fs.DERIVED_JSON))
DS = json.load(open(os.path.join(SUPP, 'derived_numbers.json')))
NUM = re.compile(r'(?<![\w.=\-−])([−-]?\d[\d,]*(?:\.\d+)?)')
# axis tick labels per figure (structural; values of the tick locators set in the scripts)
TICKS = {   # S4d: two-decimal kappa ticks (s4.KTICKS)
    1: set(), 2: {'0', '25', '50', '75', '100'}, 3: {'0', '50', '100'},       # S2: also the grey-ramp bin edges (colors.ORD_EDGES)
    4: {'0.90', '0.95', '1.00'}, 5: {'0', '25', '50', '75', '100'},
    6: {'0', '25', '50', '75', '100', '−3', '−2', '−1', '1', '2', '3', '10'},          # S6e log axis: 1, 10, 100
    7: {'0', '25', '50', '75', '100', '5', '10', '15', '20'},
    8: {'0', '20', '40', '60', '25', '50', '75', '100', '5', '10', '15', '−5', '−4', '−3', '−2', '−1', '1', '−0.1', '0.1'},   # S8d: Fig 5c's symlog race axis (s8.D_MAJOR; ±0.01 unlabelled)
    9: {'0', '50', '100', '20', '40', '60', '25', '75', '5', '10', '15'},
    10: {'0', '25', '50', '75', '100'},
}
TICKS[9] |= __import__('s9').storec_tick_labels()          # S9D broken time axis: whole seconds in each segment
STRUCT = [r'\branks 200k\s*(?:--|–)\s*1M\b', r'95\s?\\?%', r'\b\d+k\b', r'Hairlines at 0 ', r"‘npa=1’", r"‘rdp=1’", r"‘Sec-GPC: 1’", r'\bG1\d\d\b', r'^\s*[1-5]\s', r'\b[1-5]\s+‘']


def walk(d, key):
    return fs._walk(d, key)


def check_registries(log):
    bad = 0
    n = 0
    for p in sorted(glob.glob(os.path.join(SUPP, 'panels', '*_numbers.csv'))):
        for r in csv.DictReader(open(p)):
            n += 1
            src, key, f = r['source'], r['key'], r['fmt']
            if src == 'stats':
                v = walk(S, key)
            elif src == 'derived':
                name, _, rest = key.partition('/')
                v = walk(DV2[name]['value'], rest) if rest else DV2[name]['value']
            elif src == 'supp_derived':
                name, _, rest = key.partition('/')
                v = walk(DS[name]['value'], rest) if rest else DS[name]['value']
            elif src == 'csv':
                fn = key.split(':', 1)[0]
                T = pd.read_csv(os.path.join(AOUT, fn))
                val = json.loads(r['value'])
                if not (T.astype(str) == str(val)).any().any() and not (T.select_dtypes('number') == val).any().any():
                    bad += 1
                    log.append(f'STALE {os.path.basename(p)}: {key} = {val} not found in {fn}')
                continue
            else:
                bad += 1
                log.append(f'UNKNOWN SOURCE {src} in {os.path.basename(p)}')
                continue
            if fs.render(v, f) != r['text']:
                bad += 1
                log.append(f'STALE {os.path.basename(p)}: {src}:{key} now renders {fs.render(v, f)!r}, figure shows {r["text"]!r}')
    log.append(f'registry rows re-rendered: {n}; stale: {bad}')
    return bad


def shown_set(names):
    out = set()
    for nm in names:
        p = os.path.join(SUPP, 'panels', nm)
        if os.path.exists(p):
            for r in csv.DictReader(open(p)):
                s = r['shown']
                out.add(s)
                out.update(re.findall(r'[−-]?\d[\d,]*(?:\.\d+)?', s))
    return out


def tokens(text):
    t = text
    for rx in STRUCT:
        t = re.sub(rx, ' ', t, flags=re.M)
    return NUM.findall(t)


def check_figures(log):
    bad = 0
    for n in range(1, 11):
        pdf = os.path.join(SUPP, f'figS{n}.pdf')
        txt = PdfReader(pdf).pages[0].extract_text() or ''
        reg = shown_set([f'figS{n}_numbers.csv'])
        toks = tokens(txt)
        unt = [t for t in toks if t not in reg and t not in TICKS[n]]
        n_reg = sum(t in reg for t in toks)
        n_tick = sum(t in TICKS[n] and t not in reg for t in toks)
        log.append(f'figS{n}.pdf: {len(toks)} numeric tokens; {n_reg} registered; {n_tick} tick labels; untraced: {unt or "none"}')
        bad += len(unt)
    return bad


def check_captions(log):
    t = open(os.path.join(SUPP, 'caption_supp.tex')).read()
    t = re.sub(r'(?m)^%.*$', '', t)
    t = re.sub(r'\\label\{[^}]*\}', '', t)
    t = re.sub(r'Fig\.~(?:S)?\d[A-D]?', ' ', t)
    t = t.replace('{,}', ',').replace('$-$', '−')
    reg = shown_set(['captions_numbers.csv'])
    toks = tokens(t)
    unt = [x for x in toks if x not in reg]
    log.append(f'caption_supp.tex: {len(toks)} numeric tokens; untraced: {unt or "none"}')
    return len(unt)


def main():
    log = []
    bad = check_registries(log) + check_figures(log) + check_captions(log)
    log.append('RESULT: ' + ('PASS' if bad == 0 else f'FAIL ({bad})'))
    open(os.path.join(SUPP, 'trace_supp.txt'), 'w').write('\n'.join(log) + '\n')
    print('\n'.join(log))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
