"""Derived numbers for Figure 2 (methodology) that neither analysis/outputs/stats.json nor figures/v7/derived_numbers.json
holds. Written, with value, definition, script and inputs, to figures/v7/fig2/derived_numbers.json.

Nothing is typed by hand: counts are read from stats.json (which analysis/analyze.py computed from the crawl tables) and
re-checked against the committed store table where possible; intervals use the analysis' own Wilson function
(analysis/common.py), so they match every other Wilson interval in the paper.

Run:  python3 figures/v7/fig2/scripts/derive_fig2.py
"""
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FIG2 = os.path.normpath(os.path.join(HERE, '..'))
STUDY = os.path.normpath(os.path.join(FIG2, '..', '..', '..'))
OUT = os.path.join(STUDY, 'analysis', 'outputs')
sys.path.insert(0, os.path.join(STUDY, 'analysis'))
from common import wilson  # noqa: E402  (the analysis' own interval, z = 1.959964)

SCRIPT = 'figures/v7/fig2/scripts/derive_fig2.py'
DST = os.path.join(FIG2, 'derived_numbers.json')
S = json.load(open(os.path.join(OUT, 'stats.json')))
D = {}


def rec(name, value, definition, inputs, check=None):
    D[name] = dict(value=value, definition=definition, script=SCRIPT, inputs=inputs, check=check)


# ---------- agreement between loads, per store, with Wilson 95% intervals (v4 Fig 2d; v5 Fig 6d) ----------
# v5: Fig 2 no longer draws this (its panel d moved to Fig 6d); the record is kept, values unchanged, for that panel.
# stats.json holds the agreement counts (validation.*.agree / n) and Cohen's kappa with its interval, but not a Wilson
# interval for the share of stores that agree, which the agreement panel plots on the same axis as the screenshot audit
# (supp.S4.*, whose Wilson intervals stats.json already holds).
st = pd.read_csv(os.path.join(OUT, 'store_table.csv'), low_memory=False)
agree = {}
for key, (a, b) in {'A0_vs_A0r': ('A0_sbx', 'A0r_sbx'), 'A2_vs_A2r': ('A2_sbx', 'A2r_sbx'),
                    'A2_vs_V1': ('A2_sbx', 'V1_sbx')}.items():
    v = S['validation'][key]
    w = wilson(v['agree'], v['n'])
    # cross-check the counts against the committed store table when both flags are present there
    chk = None
    if a in st.columns and b in st.columns:
        m = st[(st.stratum == 'main') & st[a].notna() & st[b].notna()]
        n_t, k_t = int(len(m)), int((m[a].astype(bool) == m[b].astype(bool)).sum())
        chk = dict(n=n_t, agree=k_t, matches_stats=(n_t, k_t) == (v['n'], v['agree']))
        assert chk['matches_stats'], (key, chk, v['n'], v['agree'])
    agree[key] = dict(k=int(v['agree']), n=int(v['n']), p=w['p'], lo=w['lo'], hi=w['hi'], store_table_check=chk)
rec('fig2d_agreement', agree,
    'Share of stores on which two loads agree on "a sandboxed ad pixel sent a request" (Default vs its repeat; GPC vs '
    'its repeat; emulated GPC vs Brave native GPC), with the Wilson 95% interval from analysis/common.py.',
    ['analysis/outputs/stats.json:validation.{A0_vs_A0r,A2_vs_A2r,A2_vs_V1}.{agree,n}',
     'analysis/outputs/store_table.csv (cross-check of the counts)'],
    'k, n equal stats.json validation.*.agree / n; store_table.csv flags reproduce them where present')

# ---------- Table S-arms (figures/tables/tableS_arms.tex): the passive scrolls' start in seconds ----------
# stats.json holds it in milliseconds (design.first_scroll_after_load_ms); the table states windows in seconds.
ms = S['design']['first_scroll_after_load_ms']
assert ms % 1000 == 0, ms
rec('tableS_arms', dict(first_scroll_after_load_s=ms // 1000),
    'Start of the passive mouse-wheel scrolls, in seconds after the load event (design.first_scroll_after_load_ms / '
    '1000), for the Action column of Supplementary Table S-arms.',
    ['analysis/outputs/stats.json:design.first_scroll_after_load_ms'],
    'integer division is exact (asserted)')

# ---------- v7 Fig 2a: the flagged domains that were never drawn for checking ----------
# The flow drops from 2,634 flagged domains to 1,518 checked ones: every flagged domain of the three upper rank buckets
# was checked (census), but in the 100k-200k bucket domains were drawn in a seeded random order only until the quota of
# eligible stores was met. v7 draws the remainder as the flow's first side branch, so that every stage equals the one
# above minus its branches (asserted in make_fig2_panels.py).
P = S['checks']['provenance']['sample']
V2 = json.load(open(os.path.join(FIG2, '..', 'derived_numbers.json')))['fig2a_funnel']['value']
not_drawn = P['random_bucket_flagged'] - P['random_bucket_drawn']
assert not_drawn == V2['flagged'] - V2['verified'], (not_drawn, V2['flagged'], V2['verified'])
assert P['census_drawn'] + P['random_bucket_drawn'] == V2['verified']
rec('fig2a_not_drawn', dict(n=int(not_drawn)),
    'Flagged domains of the 100k-200k Tranco bucket that were never drawn for checking (the bucket was checked in a '
    'seeded random order until its quota of eligible stores was met): random_bucket_flagged - random_bucket_drawn.',
    ['analysis/outputs/stats.json:checks.provenance.sample.{random_bucket_flagged,random_bucket_drawn,census_drawn}',
     'figures/v7/derived_numbers.json:fig2a_funnel.{flagged,verified}'],
    'equals flagged - verified; census_drawn + random_bucket_drawn == verified (both asserted)')

# ---------- v7.1 Fig 2a: the Tranco domains that the DNS rule did not flag (the flow's first branch) ----------
# The flow's first step, Tranco top 200,000 -> 2,634 flagged, had no branch, so the caption's 'each count is the one
# above minus its branches' did not hold for it. v7.1 draws the remainder (domains not on Shopify by the DNS rule).
not_shopify = S['design']['tranco_top_n'] - V2['flagged']
assert V2['tranco'] == S['design']['tranco_top_n'] and not_shopify > 0, (V2['tranco'], not_shopify)
rec('fig2a_not_on_shopify', dict(n=int(not_shopify)),
    "Tranco top-N domains that the DNS rule did not flag as Shopify (neither the apex nor the www host resolved to "
    "Shopify's address block or a myshopify.com CNAME): design.tranco_top_n - fig2a_funnel.flagged.",
    ['analysis/outputs/stats.json:design.tranco_top_n', 'figures/v7/derived_numbers.json:fig2a_funnel.{tranco,flagged}'],
    'fig2a_funnel.tranco equals design.tranco_top_n; the difference is positive (both asserted)')

# ---------- v7 Fig 2c: where the protocol's variable moments fall, for drawing the arms on a real time axis ----------
# v7 (DESIGN_V7 section 8.5) draws the arms 'under one time axis'. The axis is the time from each page's load event
# (the protocol's own origin: the windows are fixed relative to it), so its fixed times -- 0, the 10 s compared window,
# the 15 s observation -- are exact. The moments that vary by store (navigation start, the banner becoming visible, the
# Decline click, the reload, the next page's navigation) are drawn at their MEDIANS over the analysed stores' loads,
# which this record holds (ms; never printed in the figure, registered as drawn values). Sources: crawl/loads.csv
# (t_load, t_banner_visible, t_click, t_next_nav: ms from the page's navigation start) and, for the next page's load
# event (not in loads.csv), the raw Decline records (next_load_epoch - next_goto_epoch).
import gzip  # noqa: E402
sys.path.insert(0, os.path.join(STUDY, 'analysis'))
from common import CONTENT_EXCLUDED  # noqa: E402
an = st[(st.stratum == 'main') & (~st.store_id.isin(CONTENT_EXCLUDED))]
assert len(an) == S['design']['n_main']
L = pd.read_csv(os.path.join(STUDY, 'crawl', 'loads.csv'), low_memory=False)
L = L[L.store_id.isin(an.store_id)]
arm = {a: L[L.arm == a].set_index('store_id') for a in ('A0', 'A1', 'A2')}
assert all(len(v) == S['design']['n_main'] and v.index.is_unique for v in arm.values())
clicked = an[an.clicked == True].store_id                                    # noqa: E712
assert len(clicked) == S['fig5']['decline']['clicked_all']
dc = arm['A1'].loc[clicked]
assert int(arm['A0'].t_banner_visible.notna().sum()) == int(an.banner_A0.sum())   # Default loads with a visible banner
a0b = arm['A0'][arm['A0'].t_banner_visible.notna() & arm['A0'].t_load.notna()]     # ... that also had a load event
nxt, same_clock = [], 0
for sid in clicked:
    r = json.load(gzip.open(os.path.join(STUDY, 'crawl', 'raw', f'{sid}__A1.json.gz')))
    assert r['next_goto_epoch'] and r['next_load_epoch'], sid
    # loads.csv times are ms from the page's performance.timeOrigin: the raw next navigation reproduces t_next_nav
    same_clock += abs((r['next_goto_epoch'] - r['time_origin']) - dc.loc[sid, 't_next_nav']) <= 1.5
    nxt.append(r['next_load_epoch'] - r['next_goto_epoch'])
assert same_clock >= 0.95 * len(clicked), same_clock         # the raw records and loads.csv describe the same loads


def med(s):
    s = pd.Series(s).dropna()
    return dict(ms=float(s.median()), n=int(len(s)))


tl = dict(
    default_nav_to_load=med(arm['A0'].t_load),
    default_banner_before_load=med(a0b.t_load - a0b.t_banner_visible),
    gpc_nav_to_load=med(arm['A2'].t_load),
    decline_nav_to_load=med(dc.t_load),
    decline_banner_before_load=med(dc.t_load - dc.t_banner_visible),
    decline_click_from_load=med(dc.t_click - dc.t_load),
    decline_reload_from_load=med(dc.t_next_nav - dc.t_load),
    next_nav_to_load=med(nxt),
    raw_matches_loads_csv=int(same_clock),
)
assert tl['decline_click_from_load']['n'] == len(clicked) and tl['next_nav_to_load']['n'] == len(clicked)
# the caption states these as 'before the load event' and 'after it': the signs are asserted
assert tl['default_banner_before_load']['ms'] > 0 and tl['decline_banner_before_load']['ms'] > 0
assert 0 < tl['decline_click_from_load']['ms'] < tl['decline_reload_from_load']['ms']
rec('fig2c_timeline', tl,
    'Medians (ms, with the number of loads) over the analysed stores of the moments that vary by store: *_nav_to_load '
    'from navigation start to the load event; *_before_load from the banner becoming visible to the load event; '
    "*_from_load from the page's load event to the Decline click or to the reload's navigation. Default and GPC loads "
    'with a load event; Default loads with a visible banner; Decline loads with a click (banner, click, the reload, and '
    "the next page's load event from the raw records). Drawn in Fig 2c and stated in its caption.",
    ['crawl/loads.csv:{t_load,t_banner_visible,t_click,t_next_nav}',
     'crawl/raw/<store>__A1.json.gz:{next_goto_epoch,next_load_epoch,time_origin}',
     'analysis/outputs/store_table.csv:{stratum,clicked,banner_A0}', 'analysis/common.py:CONTENT_EXCLUDED'],
    'analysed stores = design.n_main; clicked loads = fig5.decline.clicked_all; banner loads = banner_A0; the raw '
    'next-navigation time equals loads.csv t_next_nav (+-1.5 ms) for >= 95% of the clicked loads '
    '(raw_matches_loads_csv); banners before the load event; 0 < click < reload (all asserted)')

json.dump(D, open(DST, 'w'), indent=1)
for k, v in D.items():
    print(k, json.dumps(v['value']))
print('wrote', DST)
