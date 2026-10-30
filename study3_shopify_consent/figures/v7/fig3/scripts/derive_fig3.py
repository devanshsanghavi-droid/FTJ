"""Derived numbers that Figure 3 (v5; v6 RESTRAINT since 2026-10-19) shows but that analysis/outputs/stats.json and figures/v7/derived_numbers.json do
not hold. Computed from committed analysis tables only (never the raw crawl, never typed by hand) and written, with
definition, script and inputs, to figures/v7/fig3/derived_numbers.json. Each block asserts that the table reproduces
the stored values it refines, so a drift between this script and analysis/analyze.py fails loudly.

  fig3a_strata  panel a: every consent-product stratum of the Mantel-Haenszel difference (stats fig3.d.mh_by_product),
                with its counts, its MH weight and its Newcombe difference (the same formulas as analysis/analyze.py)
  fig3c_shares  the three exclusive timing parts of the 205 stores, and
  fig3c_gap     the per-store gap (banner visible minus first sandboxed ad request) behind fig3.b.before_banner:
                both belonged to panel c, which was removed on 2026-10-17 (it duplicated Fig 1c and Fig. S6b). They are
                still computed, unchanged, because analysis/outputs/derived_numbers_provenance.json lists fig3c_shares
                and their asserts check fig3b.csv against stats.json; no panel or caption of Fig 3 prints them now.

Run from anywhere:  python3 figures/v7/fig3/scripts/derive_fig3.py
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE                                                             # study3_shopify_consent/ (searched upwards,
while not (os.path.isdir(os.path.join(ROOT, 'analysis')) and os.path.isdir(os.path.join(ROOT, 'figures'))):
    ROOT = os.path.dirname(ROOT)                                        #  so a copied figure set still resolves it)
SET = os.path.normpath(os.path.join(HERE, '..', '..'))                  # this figure set (figures/v5)
OUT = os.path.join(ROOT, 'analysis', 'outputs')
DST = os.path.join(SET, 'fig3', 'derived_numbers.json')                 # this set's own fig3/ (never another version)
SCRIPT = 'figures/v7/fig3/scripts/derive_fig3.py'
S = json.load(open(os.path.join(OUT, 'stats.json')))
DV2 = json.load(open(os.path.join(SET, 'derived_numbers.json')))
sys.path.insert(0, os.path.join(ROOT, 'analysis'))
from common import CONTENT_EXCLUDED, wilson  # noqa: E402
D = {}


def rec(name, value, definition, inputs, check):
    D[name] = dict(value=value, definition=definition, script=SCRIPT, inputs=inputs, check=check)


def close(a, b, tol=1e-12):
    return abs(a - b) <= tol


# ---------- Fig 3c caption: the three exclusive timing parts as shares of the 205 stores ----------
fb = pd.read_csv(os.path.join(OUT, 'fig3b.csv'))
poll = S['design']['banner_poll_ms']
n = int(len(fb))
k_before = int((fb.gap > poll).sum())
same = 0                                   # gap (ms) at or below which the banner counts as first
k_within = int(((fb.gap > same) & (fb.gap <= poll)).sum())
k_first = int((fb.gap <= same).sum())
split = DV2['fig3c_timing_split']['value']
assert (k_before, k_within, k_first, n) == (split['more_than_one_poll_before'], split['within_one_poll_before'],
                                            split['banner_first_or_same'], split['n']), 'fig3b.csv drifted from v2 split'
assert (k_before, n) == (S['fig3']['b']['before_banner_by_poll']['k'], S['fig3']['b']['before_banner_by_poll']['n'])
assert k_before + k_within == S['fig3']['b']['before_banner']['k'] and n == S['fig3']['b']['n']
assert k_before + k_within + k_first == n
rec('fig3c_shares',
    dict(n=n, poll_ms=poll,
         more_than_one_poll_before=dict(k=k_before, p=k_before / n),
         within_one_poll_before=dict(k=k_within, p=k_within / n, lo_ms=same, hi_ms=poll),
         banner_first_or_same=dict(k=k_first, p=k_first / n)),
    'Banner stores with a pre-choice sandboxed request (n = 205), split by gap = banner visible minus first sandboxed '
    'ad request: gap > one poll (250 ms); lo_ms < gap <= hi_ms (0 < gap <= 250 ms); gap <= 0 (banner first or same '
    'poll). k and share k / n.',
    ['analysis/outputs/fig3b.csv', 'stats.json:design.banner_poll_ms'],
    'k equal figures/v7/derived_numbers.json:fig3c_timing_split; first k equals stats fig3.b.before_banner_by_poll; '
    'first two k sum to fig3.b.before_banner.k')


# ---------- Fig 3a: the consent-product strata of the Mantel-Haenszel difference ----------
def newcombe(k1, n1, k2, n2):
    """k1/n1 - k2/n2 with Newcombe's hybrid-score interval (method 10); = analysis/analyze.py newcombe_indep."""
    w1, w2 = wilson(k1, n1), wilson(k2, n2)
    d = w1['p'] - w2['p']
    return (d, d - math.sqrt((w1['p'] - w1['lo']) ** 2 + (w2['hi'] - w2['p']) ** 2),
            d + math.sqrt((w1['hi'] - w1['p']) ** 2 + (w2['p'] - w2['lo']) ** 2))


mh = S['fig3']['d']['mh_by_product']
cr = mh['crude']
assert all(close(a, b) for a, b in zip(newcombe(cr['k1'], cr['n1'], cr['k2'], cr['n2']),
                                       (cr['diff'], cr['diff_lo'], cr['diff_hi']))), 'Newcombe drifted from analyze.py'
st = pd.read_csv(os.path.join(OUT, 'store_table.csv'))
m = st[(st.stratum == 'main') & (~st.store_id.isin(CONTENT_EXCLUDED))].copy()
assert len(m) == S['design']['n_main']
# the stratum of a store = its consent product; no single product = a stratum of its own (analysis/analyze.py)
m['cluster'] = np.where(m.cmp.isin(['none', 'generic', 'multiple']), 'solo_' + m.store_id, m.cmp)
bd = m[(m.banner_A0 == True) & m.region_optout.notna()]                     # noqa: E712
assert (int((bd.region_optout == True).sum()), int((bd.region_optout == False).sum())) == (   # noqa: E712
    S['fig3']['d']['opt_out']['any_sbx']['n'], S['fig3']['d']['opt_in']['any_sbx']['n'])
rows = {}
for c, x in bd.groupby('cluster'):
    a_, d_ = x[x.region_optout == True], x[x.region_optout == False]         # noqa: E712
    if len(a_) == 0 or len(d_) == 0:
        continue                                                            # no information (dropped by MH)
    ak, an, dk, dn = int(a_.A0_sbx.sum()), len(a_), int(d_.A0_sbx.sum()), len(d_)
    diff, lo, hi = newcombe(ak, an, dk, dn)
    # v6 (2026-10-19): panel a is a dot plot of the two shares with their Wilson 95% CIs (lo, hi), per product
    wa, wd = wilson(ak, an), wilson(dk, dn)
    rows[c] = dict(allowed=dict(k=ak, n=an, p=ak / an, lo=wa['lo'], hi=wa['hi']),
                   denied=dict(k=dk, n=dn, p=dk / dn, lo=wd['lo'], hi=wd['hi']),
                   mh_weight=an * dn / (an + dn), diff=diff, diff_lo=lo, diff_hi=hi)
order = sorted(rows, key=lambda c: (-rows[c]['mh_weight'], c))
wsum = sum(r['mh_weight'] for r in rows.values())
for r in rows.values():
    r['mh_weight_share'] = r['mh_weight'] / wsum
rd = sum((r['allowed']['k'] * r['denied']['n'] - r['denied']['k'] * r['allowed']['n']) /
         (r['allowed']['n'] + r['denied']['n']) for r in rows.values()) / wsum
assert len(rows) == mh['n_strata'] and close(rd, mh['rd']), 'strata do not reproduce the stored MH difference'
assert sum(r['allowed']['k'] for r in rows.values()) == mh['k1'] and sum(r['allowed']['n'] for r in rows.values()) == mh['n1']
assert sum(r['denied']['k'] for r in rows.values()) == mh['k0'] and sum(r['denied']['n'] for r in rows.values()) == mh['n0']
for c, br in mh['by_product'].items():
    for side in ('allowed', 'denied'):
        assert (rows[c][side]['k'], rows[c][side]['n']) == (br[side]['k'], br[side]['n']), (c, side)
        assert all(close(rows[c][side][f], br[side][f]) for f in ('p', 'lo', 'hi')), ('Wilson drifted', c, side)
n_strata_stores = mh['stores_in_informative_strata']
n_readable = len(bd)
min_n = S['design']['min_cell_n']
# v6 r2 (2026-10-19): panel a draws only the products with >= min_cell_n stores under both defaults ('full'); the
# others enter the pooled difference and are listed in the caption. w_share_full = the full products' share of the
# total MH weight (what the drawn rows carry of the pooled estimate).
full = [c for c in order if min(rows[c]['allowed']['n'], rows[c]['denied']['n']) >= min_n]
w_share_full = sum(rows[c]['mh_weight_share'] for c in full)
assert 0 < w_share_full <= 1 and full == order[:len(full)], 'MH order no longer puts the full products first'
rec('fig3a_strata',
    dict(order=order, rows=rows, n_readable=n_readable, n_strata_stores=n_strata_stores,
         n_other=n_readable - n_strata_stores, min_cell_n=min_n,
         n_sparse=sum(1 for r in rows.values() if min(r['allowed']['n'], r['denied']['n']) < min_n),
         n_full=len(full), w_share_full=w_share_full),
    'Banner stores with a readable region default, Default load. One record per consent product (the strata of '
    'stats fig3.d.mh_by_product: products with at least one store under each default): stores that fired / stores '
    'under each default with the share p and its Wilson 95% CI (lo, hi; analysis/common.py wilson), MH weight '
    'n1 n0 / (n1 + n0) and its share of the total, and the difference allowed minus '
    'denied with Newcombe hybrid-score 95% CI. order = descending MH weight. n_other = readable-default banner stores '
    'outside the strata (a product seen under one default only, or no single product). n_sparse = strata with fewer '
    'than design.min_cell_n stores under either default; n_full = the others (the products panel a draws), and '
    'w_share_full = their summed share of the total MH weight.',
    ['analysis/outputs/store_table.csv', 'analysis/common.py:CONTENT_EXCLUDED', 'stats.json:fig3.d'],
    'stratum count, summed k and n, and the MH difference reproduce stats fig3.d.mh_by_product; the five products in '
    'by_product match (k, n and the Wilson p, lo, hi); the Newcombe formula reproduces mh_by_product.crude')

# ---------- Fig 3c: the per-store gap (banner visible minus first sandboxed ad request) ----------
g = m[(m.banner_A0 == True) & (m.A0_sbx == True)].set_index('store_id')    # noqa: E712
gap_t = (g.t_banner_A0 - g.A0_first_sbx_t)
fbi = fb.set_index('store_id')
assert set(fbi.index) == set(g.index) and (fbi.gap - gap_t.loc[fbi.index]).abs().max() == 0, 'fig3b.csv vs store_table'
gaps = sorted(int(v) if float(v).is_integer() else float(v) for v in fb.gap)
X_LO_S, X_HI_S = -2, 2                     # panel c axis: first request relative to the banner (s)
rel = -np.asarray(gaps, dtype=float) / 1000.0
rec('fig3c_gap',
    dict(n=n, gaps_ms=gaps, k_before=int((rel < 0).sum()), k_before_poll=int((rel < -poll / 1000).sum()),
         x_lo_s=X_LO_S, x_hi_s=X_HI_S, n_left_of_axis=int((rel < X_LO_S).sum()),
         n_right_of_axis=int((rel > X_HI_S).sum())),
    'The 205 banner stores with a pre-choice sandboxed request: gap = banner visible minus first sandboxed ad request '
    '(ms), sorted. Panel c plots the cumulative share of stores against -gap (first request relative to the banner, s) '
    'on [x_lo_s, x_hi_s]; n_left_of_axis / n_right_of_axis = stores whose first request lies outside that range.',
    ['analysis/outputs/fig3b.csv', 'analysis/outputs/store_table.csv'],
    'gaps equal store_table t_banner_A0 - A0_first_sbx_t; k_before = stats fig3.b.before_banner.k; k_before_poll = '
    'stats fig3.b.before_banner_by_poll.k')
gv = D['fig3c_gap']['value']
assert gv['k_before'] == S['fig3']['b']['before_banner']['k'] and gv['k_before_poll'] == k_before

json.dump(D, open(DST, 'w'), indent=1)
print('wrote', DST)
for k, v in D.items():
    s = json.dumps(v['value'])
    print(' ', k, s if len(s) < 300 else s[:300] + ' ...')
