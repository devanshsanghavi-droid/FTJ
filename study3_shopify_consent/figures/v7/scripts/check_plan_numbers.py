"""Check every number in the takeaway and caption sections of FIGURE_PLAN_v2.md (between <!-- nums:start --> and
<!-- nums:end -->) against stats.json and derived_numbers.json. Prints numbers that match no stored value in any of the
formats used in the paper (integer, thousands separator, percent with 1 decimal, CI bounds, pp differences, ms).
Structural numbers (figure and panel references, '95%' CI level, leak-point numbers) are listed separately."""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
S = json.load(open(os.path.join(ROOT, 'analysis', 'outputs', 'stats.json')))
DN = json.load(open(os.path.join(ROOT, 'figures', 'v7', 'derived_numbers.json')))
PLAN = open(os.path.join(ROOT, 'figures', 'v7', 'FIGURE_PLAN_v2.md')).read()

ok = set()


def add(v):
    if isinstance(v, bool) or v is None:
        return
    if isinstance(v, (int, float)):
        for x in (v, abs(v)):
            if float(x).is_integer():
                ok.update({str(int(x)), f'{int(x):,}'})
            for d in (1, 2, 3):
                ok.add(f'{x:.{d}f}')
            if abs(x) <= 1.0:                       # shares and differences -> percent / pp
                for d in (0, 1):
                    ok.add(f'{abs(x) * 100:.{d}f}')
            ok.add(f'{abs(x) / 1000:.2f}')          # ms -> s
    elif isinstance(v, str):
        for t in re.findall(r'\d+(?:\.\d+)?', v):
            ok.add(t)


def walk(d):
    if isinstance(d, dict):
        for v in d.values():
            walk(v)
    elif isinstance(d, list):
        for v in d:
            walk(v)
    else:
        add(d)


walk(S)
walk({k: v['value'] for k, v in DN.items()})

blocks = re.findall(r'<!-- nums:start -->(.*?)<!-- nums:end -->', PLAN, flags=re.S)
STRUCT = re.compile(r'(Fig\. ?S?\d[A-D]?|Figs?\. ?\d|\(\d\)|95%|\bS\d\b)')
bad, n = [], 0
for b in blocks:
    b2 = STRUCT.sub(' ', b).replace('−', '-')
    for tok in re.findall(r'\d[\d,]*(?:\.\d+)?', b2):
        n += 1
        t = tok.rstrip(',')
        if t not in ok and t.replace(',', '') not in ok:
            i = b2.find(tok)
            bad.append((t, b2[max(0, i - 40):i + 25].replace('\n', ' ')))
print(f'{n} numeric tokens checked in {len(blocks)} sections; {len(bad)} not found in stats.json/derived_numbers.json:')
for t, ctx in bad:
    print(f'  {t!r:>10}  ...{ctx}...')

# ---- stronger check: every "k of n" / "k/n" pair must exist as a stored (k, n) pair ----
pairs = set()


def walk_pairs(d):
    if isinstance(d, dict):
        ks = {k: v for k, v in d.items() if isinstance(v, (int, float)) and not isinstance(v, bool) and v == v}
        for a, b in (('k', 'n'), ('k1', 'n1'), ('k2', 'n2'), ('k0', 'n0'), ('k_a', 'n'), ('k_b', 'n'), ('pixels_before', 'pixels'),
                     ('pixels_after', 'pixels'), ('agree', 'n'), ('fired', 'n')):
            if a in ks and b in ks:
                pairs.add((int(ks[a]), int(ks[b])))
        for v in d.values():
            walk_pairs(v)
    elif isinstance(d, list):
        for v in d:
            walk_pairs(v)


walk_pairs(S)
dv = {k: v['value'] for k, v in DN.items()}
walk_pairs(dv)
# derived partitions: add (part, n) for every integer field against the block's n
for blk in (dv['fig3c_timing_split'], dv['fig4a_routes']['all_stores'], dv['fig4a_routes']['primary_no_yes'],
            dv['fig5b_exclusive_classes']['decline_refused'], dv['fig5b_exclusive_classes']['gpc'],
            dv['fig5c_race_per_sandbox']['deny'], dv['fig5c_race_per_sandbox']['grant']):
    n_ = blk.get('n', blk.get('sandboxes'))
    for v in blk.values():
        if isinstance(v, int):
            pairs.add((v, n_))
bad2 = []
for b in blocks:
    b2 = b.replace('−', '-')
    for k_, n_ in re.findall(r'(\d[\d,]*) (?:of|/) (\d[\d,]*)', b2) + re.findall(r'(\d[\d,]*)/(\d[\d,]*)', b2):
        kk, nn = int(k_.replace(',', '')), int(n_.replace(',', ''))
        if (kk, nn) not in pairs:
            bad2.append((kk, nn))
print(f'k-of-n pairs not stored: {bad2}')
