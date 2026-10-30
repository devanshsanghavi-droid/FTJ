"""Derived numbers for Figure 6 (v5): the Store C check grid of panel a, and (v5) the Wilson intervals of the
between-load agreement shown in panel d (record fig6d_agreement, ported unchanged from v4 Fig 2d).

stats.json holds the Store C counts per LOAD (fig6.b.store_c.<arm>), plus the pre-click and fresh-page split of the
Decline load for vendors (fig6.b.store_c_pre_click, fig6.b.store_c_after_decline). Panel A's grid needs three
counts for each of six columns (Default, Default repeat, Decline before the click, Decline after the click, GPC, GPC repeat):
  tiktok_sbx_code   requests that carried the creator's per-video code to TikTok from TikTok's sandbox
  vendors_code      ad vendors that received the code (any route; Google Ads and Google Merchant Center count separately)
  vendors_code_sbx  of those, vendors that received it from a Shopify sandbox (worker or iframe)
The Decline load is split at the click: before it, and after it (the rest of that page plus the fresh page after the
reload, the window of stats.json fig6.b.store_c_after_decline).
Two of the 18 cells are not in stats.json (vendors_code_sbx for the Default and GPC loads and their repeats) and one
refines a whole-load value (tiktok_sbx_code before the Decline click). They are computed here from the committed table
analysis/outputs/fig6b_store_c.csv (written by analysis/analyze.py; never the raw crawl). Every cell that stats.json
also holds is asserted equal to it, so a drift between this script and analyze.py fails loudly.

v4 adds the per-load VENDOR MATRIX of panel a (fig6a_store_c_vendors): for every ad vendor that received the code in
any load (columns ordered by vendor group, figures/colors.py VENDOR_ORDER, then vendor id), its route in each grid
column: 2 = received the code from a Shopify sandbox (at least one request), 1 = only by another route, 0 = not at all.
It holds no new number: per column, the count of non-zero cells must equal vendors_code and the count of 2s
vendors_code_sbx (asserted below).

Run:  python3 figures/v7/fig6/scripts/derive_fig6.py      (writes figures/v7/fig6/derived_numbers.json)
"""
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FIG6 = os.path.normpath(os.path.join(HERE, '..'))
ROOT = os.path.normpath(os.path.join(FIG6, '..', '..', '..'))          # study3_shopify_consent/
OUT = os.path.join(ROOT, 'analysis', 'outputs')
DST = os.path.join(FIG6, 'derived_numbers.json')
SCRIPT = 'figures/v7/fig6/scripts/derive_fig6.py'
TABLE = 'analysis/outputs/fig6b_store_c.csv'

S = json.load(open(os.path.join(OUT, 'stats.json')))
cl = S['fig6']['b']['store_c']
pre = S['fig6']['b']['store_c_pre_click']
aft = S['fig6']['b']['store_c_after_decline']

T = pd.read_csv(os.path.join(OUT, 'fig6b_store_c.csv'))
assert set(T.cond) <= {'A0', 'A0r', 'A1pre', 'A1post', 'A1next', 'A2', 'A2r'}, sorted(set(T.cond))
assert T.ad.all(), 'fig6b_store_c.csv should hold ad requests only'
tok = T[T.has_creator_token.astype(bool)]

# grid columns in figure order: (column id, table condition)
# A1after = everything after the Decline click: the rest of that page (A1post) and the fresh page after the reload
# (A1next); this is the window of stats.json fig6.b.store_c_after_decline.
COLS = [('A0', ['A0']), ('A0r', ['A0r']), ('A1pre', ['A1pre']), ('A1after', ['A1post', 'A1next']), ('A2', ['A2']),
        ('A2r', ['A2r'])]
grid = {}
for col, conds in COLS:
    x = tok[tok.cond.isin(conds)]
    grid[col] = dict(
        tiktok_sbx_code=int(((x.vgroup == 'TikTok') & x.sandbox.astype(bool)).sum()),
        vendors_code=int(x.vendor.nunique()),
        vendors_code_sbx=int(x[x.sandbox.astype(bool)].vendor.nunique()),
    )

# ---- checks against stats.json (every cell that stats.json also holds) ----
for a in ('A0', 'A0r', 'A2', 'A2r'):
    assert grid[a]['tiktok_sbx_code'] == cl[a]['n_creator_token_tiktok_sbx'], a
    assert grid[a]['vendors_code'] == cl[a]['n_vendors_with_token'], a
    assert len(T[T.cond == a]) == cl[a]['n_ad'], a
for a in ('A2', 'A2r'):                       # no sandboxed ad request at all in the GPC loads
    assert cl[a]['n_sandboxed'] == 0 and grid[a]['vendors_code_sbx'] == 0, a
# Decline load: the whole-load TikTok count all falls before the click (none after the click or on the fresh page)
a1 = tok[tok.cond.isin(['A1pre', 'A1post', 'A1next'])]
assert int(((a1.vgroup == 'TikTok') & a1.sandbox.astype(bool)).sum()) == cl['A1']['n_creator_token_tiktok_sbx']
assert grid['A1pre']['tiktok_sbx_code'] == cl['A1']['n_creator_token_tiktok_sbx']
t_click = float(T[T.arm == 'A1'].t_click.dropna().iloc[0])
assert t_click == cl['A1']['t_click']
assert (tok[(tok.cond == 'A1pre') & (tok.vgroup == 'TikTok')].t_ms < t_click).all()
assert grid['A1pre']['vendors_code'] == pre['n_vendors']
assert grid['A1pre']['vendors_code_sbx'] == pre['n_vendors_sandboxed']
assert grid['A1after']['vendors_code'] == aft['n_vendors']
assert grid['A1after']['vendors_code_sbx'] == aft['n_vendors_sandboxed']
assert grid['A1after']['tiktok_sbx_code'] == aft['tiktok'] == 0
assert len(tok[tok.cond.isin(['A1post', 'A1next'])]) == aft['n']
assert (tok[tok.cond.isin(['A1post', 'A1next'])].t_ms > t_click).all()

# ---- v4: per-load vendor matrix (route of each vendor that received the code), same windows as the grid ----
sys.path.insert(0, os.path.join(ROOT, 'figures'))
import colors as _C  # noqa: E402
vend = (tok[['vendor', 'vgroup']].drop_duplicates().assign(o=lambda d: d.vgroup.map(_C.VENDOR_ORDER.index))
        .sort_values(['o', 'vendor']))
assert vend.vendor.is_unique, 'a vendor id maps to two vendor groups'
routes = {}
for col, conds in COLS:
    x = tok[tok.cond.isin(conds)]
    sbx = set(x[x.sandbox.astype(bool)].vendor)
    anyr = set(x.vendor)
    routes[col] = [2 if v in sbx else (1 if v in anyr else 0) for v in vend.vendor]
    assert sum(r > 0 for r in routes[col]) == grid[col]['vendors_code'], col
    assert sum(r == 2 for r in routes[col]) == grid[col]['vendors_code_sbx'], col

# ---- v5: panel d (validation), ported from figures/v4/fig2/scripts/derive_fig2.py (record fig2d_agreement) ----
# stats.json holds the between-load agreement counts (validation.*.agree / n) and Cohen's kappa with its interval, but
# not a Wilson interval for the share of stores that agree, which panel d plots on the same axis as the screenshot
# audit (supp.S4.*, whose Wilson intervals stats.json already holds). Same method as v4: the analysis' own Wilson
# function (analysis/common.py, z = 1.959964); the counts are cross-checked against the committed store table.
sys.path.insert(0, os.path.join(ROOT, 'analysis'))
from common import wilson  # noqa: E402
ST = pd.read_csv(os.path.join(OUT, 'store_table.csv'), low_memory=False)
agree = {}
for key, (a, b) in {'A0_vs_A0r': ('A0_sbx', 'A0r_sbx'), 'A2_vs_A2r': ('A2_sbx', 'A2r_sbx'),
                    'A2_vs_V1': ('A2_sbx', 'V1_sbx')}.items():
    v = S['validation'][key]
    w = wilson(v['agree'], v['n'])
    chk = None
    if a in ST.columns and b in ST.columns:
        m = ST[(ST.stratum == 'main') & ST[a].notna() & ST[b].notna()]
        n_t, k_t = int(len(m)), int((m[a].astype(bool) == m[b].astype(bool)).sum())
        chk = dict(n=n_t, agree=k_t, matches_stats=(n_t, k_t) == (v['n'], v['agree']))
        assert chk['matches_stats'], (key, chk, v['n'], v['agree'])
    agree[key] = dict(k=int(v['agree']), n=int(v['n']), p=w['p'], lo=w['lo'], hi=w['hi'], store_table_check=chk)
# the v4 record must be reproduced exactly (the numbers move from Fig 2d to Fig 6d unchanged)
_V4 = os.path.join(ROOT, 'figures', 'v4', 'fig2', 'derived_numbers.json')
if os.path.exists(_V4):
    assert json.load(open(_V4))['fig2d_agreement']['value'] == agree, 'fig6d_agreement differs from v4 fig2d_agreement'

D = {
    'fig6d_agreement': dict(
        value=agree,
        definition=('Share of stores on which two loads agree on "a sandboxed ad pixel sent a request" (Default vs its '
                    'repeat; GPC vs its repeat; emulated GPC vs Brave native GPC), with the Wilson 95% interval from '
                    'analysis/common.py. Ported unchanged from figures/v4/fig2/derived_numbers.json fig2d_agreement '
                    '(v4 Fig 2d), which v5 shows as Fig 6d.'),
        script=SCRIPT,
        inputs=['analysis/outputs/stats.json:validation.{A0_vs_A0r,A2_vs_A2r,A2_vs_V1}.{agree,n}',
                'analysis/outputs/store_table.csv (cross-check of the counts)'],
        check=('k, n equal stats.json validation.*.agree / n; store_table.csv flags reproduce them where present; '
               'value equals v4 fig2d_agreement'),
        not_in_stats=['p, lo, hi (the Wilson interval of the agreement share)'],
    ),
    'fig6a_store_c_vendors': dict(
        value=dict(vendors=vend.vendor.tolist(), groups=vend.vgroup.tolist(), routes=routes),
        definition=('Store C, the same six grid columns as fig6a_store_c_grid. vendors: every ad vendor (analysis vendor '
                    'id) that received the creator\'s per-video code in any column, ordered by vendor group '
                    '(figures/colors.py VENDOR_ORDER), then id; groups: its vendor group. routes[column][i]: 2 = vendor i '
                    'received the code from a Shopify sandbox (worker or iframe) in that column, 1 = only by another '
                    'route, 0 = not at all.'),
        script=SCRIPT,
        inputs=[TABLE],
        check=('per column: count(routes > 0) == fig6a_store_c_grid vendors_code; count(routes == 2) == '
               'vendors_code_sbx'),
        not_in_stats=['the whole matrix (vendor identity per load; no number is printed from it)'],
    ),
    'fig6a_store_c_grid': dict(
        value=grid,
        definition=('Store C (creator stratum, C005) landing page reached from the creator video link. Per grid column: '
                    'tiktok_sbx_code = ad requests to TikTok sent from TikTok\'s Shopify sandbox that carried the '
                    'creator\'s per-video code; vendors_code = distinct ad vendors (analysis vendor ids; Google Ads and '
                    'Google Merchant Center are separate) that received the code by any route; vendors_code_sbx = of '
                    'those, vendors that received it from a Shopify sandbox (worker or iframe). Columns: A0 Default, A0r '
                    'Default repeat, A1pre Decline load before the click, A1after Decline load after the click (the rest of '
                    'that page and the fresh page after the reload), A2 GPC, A2r GPC repeat.'),
        script=SCRIPT,
        inputs=[TABLE, 'analysis/outputs/stats.json:fig6.b.store_c, store_c_pre_click, store_c_after_decline'],
        check=('A0/A0r/A2/A2r tiktok_sbx_code == n_creator_token_tiktok_sbx and vendors_code == n_vendors_with_token; '
               'A1pre tiktok_sbx_code == A1 n_creator_token_tiktok_sbx (all before t_click); A1pre vendors == '
               'store_c_pre_click; A1after == store_c_after_decline; A2/A2r n_sandboxed == 0'),
        not_in_stats=['A0.vendors_code_sbx', 'A0r.vendors_code_sbx', 'A1pre.tiktok_sbx_code (refines the whole-load '
                      'A1 value)'],
    ),
}
json.dump(D, open(DST, 'w'), indent=1)
print('wrote', DST)
for c, v in grid.items():
    print(f'  {c:7s}', v, routes[c])
print('  vendors', list(zip(vend.vendor, vend.vgroup)))
