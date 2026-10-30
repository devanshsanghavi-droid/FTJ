"""Derived numbers for Figure 4 (v2) that neither analysis/outputs/stats.json nor figures/v7/derived_numbers.json hold.

Writes figures/v7/fig4/derived_numbers.json. Every value is computed from committed analysis tables or read-only crawl
records (never typed by hand), and each block asserts that it reproduces the stats.json / derived_numbers.json value it
refines, so a drift fails loudly.

  fig4a_entries      the 19 blocklist entries of panel A (vendor declared blocked before any choice, configured sandboxed
                     Shopify pixel, store whose CMP wrote no 'marketing: yes'), one per column, with independent route
                     flags, in the drawing order (both routes, sandbox only, page script only, neither), the same
                     column order as Supplementary Fig. S7B.
  fig4a_kg           Korn-Graubard 95% intervals clustered by store for the 12/19 (sandbox) and 5/19 (page script)
                     entry shares (analysis/analyze.py kg_share, same seed); checked on the all-store set against
                     stats.json fig4.c.cfg.sandbox.
  fig4c_recheck      the panel C re-check load: store chosen by the plan's rule (first ID among
                     checks.recheck.blocker.stores_neutralized_and_sbx_ids whose CMP wrote no 'yes'), vendor chosen by a
                     fixed rule (the declared-blocked vendor with a neutralised page tag and the most sandboxed ad requests
                     in that load), and the event times, all relative to navigation start. tick_groups: the sandboxed
                     requests within the axis grouped into one drawn tick when they are of the same kind and less than
                     TICK_MERGE_MS apart (panel C labels such a tick with a count badge, e.g. '×2').

Run from anywhere:  python3 figures/v7/fig4/scripts/derive_fig4.py
"""
import gzip
import json
import os
import re
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FIG4 = os.path.normpath(os.path.join(HERE, '..'))
ROOT = os.path.normpath(os.path.join(FIG4, '..', '..', '..'))          # study3_shopify_consent/
OUT = os.path.join(ROOT, 'analysis', 'outputs')
RECHECK = os.path.join(ROOT, 'crawl', 'recheck')
DST = os.path.join(FIG4, 'derived_numbers.json')
SCRIPT = 'figures/v7/fig4/scripts/derive_fig4.py'
sys.path.insert(0, os.path.join(ROOT, 'analysis'))
from analyze import kg_share  # noqa: E402  (the paper's own Korn-Graubard implementation and seed)

S = json.load(open(os.path.join(OUT, 'stats.json')))
DV2 = json.load(open(os.path.join(ROOT, 'figures', 'v7', 'derived_numbers.json')))
D = {}


def rec(name, value, definition, inputs, check):
    D[name] = dict(value=value, definition=definition, script=SCRIPT, inputs=inputs, check=check)


# ------------------------------------------------------------------ panel A: the 19 entries, independent route flags
pairs = pd.read_csv(os.path.join(OUT, 'fig4c_declared_blocked_pairs.csv'))
ad = pd.read_csv(os.path.join(OUT, 'ad_requests.csv.gz'), low_memory=False,
                 usecols=['stratum', 'cond', 'store_id', 'vendor', 'oclass'])
a0 = ad[(ad.stratum == 'main') & (ad.cond == 'A0')]
po = a0.groupby(['store_id', 'vendor']).oclass.apply(set)


def hier(o):     # analyze.py's hierarchical outcome (sandbox > OPEN > relay > page), to prove the join is the same
    return 'none' if o is None else ('sandbox' if 'sandbox' in o else ('open_pixel' if 'open_pixel' in o else
                                                                        ('relay' if 'relay' in o else 'page')))


pairs['oset'] = [po.get((r.store_id, r.vendor)) for r in pairs.itertuples()]
assert all(hier(o) == oc for o, oc in zip(pairs.oset, pairs.outcome)), 'outcome no longer reproduces analyze.py'
pairs['f_sbx'] = [bool(o) and 'sandbox' in o for o in pairs.oset]
pairs['f_page'] = [bool(o) and 'page' in o for o in pairs.oset]
excl = set(S['fig4']['a']['blocklist']['primary']['stores_excluded'])
cfg = pairs[pairs.cfg_sandboxed].copy()
pri = cfg[~cfg.store_id.isin(excl)].copy()

CLASS_ORDER = ['both', 'sandbox_only', 'page_only', 'neither']     # = S7B (supp/scripts/s7.py): one order in both unit charts


def cls(r):
    return 'both' if (r.f_sbx and r.f_page) else ('sandbox_only' if r.f_sbx else ('page_only' if r.f_page else 'neither'))


pri['cls'] = [cls(r) for r in pri.itertuples()]
pri['cls_i'] = pri.cls.map(CLASS_ORDER.index)
pri = pri.sort_values(['cls_i', 'store_id', 'vgroup', 'vendor']).reset_index(drop=True)
counts = dict(n=int(len(pri)), n_stores=int(pri.store_id.nunique()), sandbox=int(pri.f_sbx.sum()), page=int(pri.f_page.sum()),
              both=int((pri.f_sbx & pri.f_page).sum()), sandbox_only=int((pri.cls == 'sandbox_only').sum()),
              page_only=int((pri.cls == 'page_only').sum()), neither_route=int((pri.cls == 'neither').sum()),
              stores_sandbox=int(pri[pri.f_sbx].store_id.nunique()))
ref = DV2['fig4a_routes']['value']['primary_no_yes']
assert counts == ref, (counts, ref)
entries = [dict(col=i + 1, store_id=r.store_id, cmp=r.cmp, vendor=r.vendor, vgroup=r.vgroup, sandbox=bool(r.f_sbx),
                page=bool(r.f_page), cls=r.cls) for i, r in enumerate(pri.itertuples())]
rec('fig4a_entries', dict(counts=counts, class_order=CLASS_ORDER, entries=entries),
    "Panel A columns: blocklist entries (ad vendor declared blocked before any choice) whose vendor has a configured "
    "sandboxed Shopify pixel, on stores whose CMP wrote no 'marketing: yes' in the Default load. Route flags are "
    "independent: 'sandbox' = the vendor sent an ad request from a Shopify sandbox (worker or iframe) in the Default "
    "load; 'page' = it sent one from an ordinary page script. Columns are ordered both routes, sandbox only, page "
    "only, neither (the same order as Fig. S7B), then by store and vendor.",
    ['analysis/outputs/fig4c_declared_blocked_pairs.csv', 'analysis/outputs/ad_requests.csv.gz',
     'stats.json:fig4.a.blocklist.primary.stores_excluded'],
    'counts == figures/v7/derived_numbers.json fig4a_routes.primary_no_yes; hierarchical outcome reproduces analyze.py')

# ------------------------------------------------------------------ panel A: store-clustered (Korn-Graubard) intervals
kg_all = kg_share(cfg.f_sbx.astype(int).values, cfg.store_id.values)
ref_all = S['fig4']['c']['cfg']['sandbox']
assert (kg_all['k'], kg_all['n']) == (ref_all['k'], ref_all['n'])
assert abs(kg_all['kg_lo'] - ref_all['kg_lo']) < 1e-9 and abs(kg_all['kg_hi'] - ref_all['kg_hi']) < 1e-9, (kg_all, ref_all)
kg_sbx = kg_share(pri.f_sbx.astype(int).values, pri.store_id.values)
kg_page = kg_share(pri.f_page.astype(int).values, pri.store_id.values)
assert (kg_sbx['k'], kg_sbx['n'], kg_page['k'], kg_page['n']) == (ref['sandbox'], ref['n'], ref['page'], ref['n'])
rec('fig4a_kg', dict(sandbox=kg_sbx, page=kg_page),
    'Shares of the panel A entries that fired by each route, with Korn-Graubard 95% intervals clustered by store '
    '(analysis/analyze.py kg_share: Clopper-Pearson on the effective sample size from a store bootstrap, B = 2,000, '
    'seed 20260926, with the degrees-of-freedom correction for the number of stores).',
    ['fig4a_entries (this file)', 'analysis/analyze.py:kg_share'],
    'kg_share on the all-store set reproduces stats.json fig4.c.cfg.sandbox (k, n, kg_lo, kg_hi)')

# ------------------------------------------------------------------ panel C: the re-check load
BLOCKED = {'javascript/blocked', 'text/plain', 'osano/blocked'}                       # = crawl/recheck/analyze_recheck.py
SANDBOX = {'strict_worker', 'lax_iframe'}
INLINE_SIG = {'tiktok': r'\bttq\b|analytics\.tiktok', 'meta': r'\bfbq\b|connect\.facebook', 'pinterest': r'\bpintrk\b|pinimg',
              'snap': r'\bsnaptr\b|sc-static', 'microsoft_uet': r'\buetq\b|bat\.bing', 'google_ads': r'AW-\d|googleads',
              'reddit': r'\brdt\(|redditstatic'}
bl = S['checks']['recheck']['blocker']
cand = sorted(bl['stores_neutralized_and_sbx_ids'])
store = [s for s in cand if s not in excl][0]
be = pd.read_csv(os.path.join(RECHECK, 'blocker_by_entry.csv'))
bs = pd.read_csv(os.path.join(RECHECK, 'blocker_by_store.csv'))
assert int(bs.neutralized_and_sbx.sum()) == bl['stores_neutralized_and_sbx']
E = be[(be.store_id == store) & be.main_tag_neutralized & be.fired_sandbox]
assert len(E) >= 1
r = json.load(gzip.open(os.path.join(RECHECK, 'raw', f'{store}__R0.json.gz')))
off = r['time_origin'] - r['nav_wall']        # performance.now() (scriptlog, probe) -> ms since navigation start
sl = r.get('scriptlog') or {}
neutral = [x for x in sl.get('added', []) if (x.get('type') or '').strip() in BLOCKED] + \
          [x for x in sl.get('changed', []) if x['attr'] == 'type' and x['now'] in BLOCKED]
rq = [q for q in (r.get('requests') or []) if q.get('vendor') and q.get('ad')]


def vendor_events(v):
    neu = [x for x in neutral if x.get('vendor') == v or (x.get('inline') and re.search(INLINE_SIG.get(v, r'$^'), x.get('inline') or ''))]
    sbx = sorted([q for q in rq if q['vendor'] == v and q.get('origin') in SANDBOX], key=lambda q: q['t'])
    mt = [q for q in rq if q['vendor'] == v and q.get('origin') not in SANDBOX]
    return neu, sbx, mt


per_vendor = {v: vendor_events(v) for v in sorted(E.vendor)}
vendor = max(per_vendor, key=lambda v: (len(per_vendor[v][1]), v))
neu, sbx, mt = per_vendor[vendor]
assert neu and sbx and not mt, 'panel C needs a neutralised tag, sandboxed requests and no page-script requests'
axis_ms = S['design']['timeline_axis_s'] * 1000
cs3 = (r.get('probe') or {}).get('cs3') or {}
t_banner = (cs3.get('banner') or {}).get('t')
reqs = [dict(t_ms=int(q['t']), kind=q.get('vkind'), origin=q['origin'], type=q.get('type')) for q in sbx]
yes_writes = [e for e in (cs3.get('ev') or []) if '"marketingAllowed":true' in (e.get('d') or '')]
c_val = dict(
    store_id=store, cmp=str(E.cmp.iloc[0]), vendor=vendor,
    vendor_label={'tiktok': 'TikTok', 'meta': 'Meta', 'google_ads': 'Google', 'pinterest': 'Pinterest', 'snap': 'Snap',
                  'microsoft_uet': 'Microsoft'}.get(vendor, vendor),
    rule_store="first store ID in stats.json checks.recheck.blocker.stores_neutralized_and_sbx_ids whose CMP wrote no "
               "'marketing: yes' (not in fig4.a.blocklist.primary.stores_excluded)",
    rule_vendor='declared-blocked vendor of that store with a neutralised page tag and the most sandboxed ad requests',
    candidates=cand, vendors_neutralized_and_sbx=sorted(E.vendor),
    t_tag_neutralized_ms=int(round(min(x['t'] for x in neu) + off)),
    n_tag_elements_neutralized=len({x.get('src') or x.get('inline') for x in neu}),
    neutralized_type=sorted({(x.get('type') or x.get('now') or '').strip() for x in neu}),
    t_banner_ms=int(round(t_banner + off)) if t_banner is not None else None,
    clicks=r.get('clicks'), cmp_yes_writes=len(yes_writes),
    n_sandbox_requests=len(reqs), n_sandbox_beacons=sum(q['kind'] == 'beacon' for q in reqs),
    n_sandbox_libraries=sum(q['kind'] == 'library' for q in reqs),
    sandbox_origins=sorted({q['origin'] for q in reqs}),
    t_first_sandbox_ms=reqs[0]['t_ms'], lead_first_sandbox_over_tag_ms=int(round(min(x['t'] for x in neu) + off)) - reqs[0]['t_ms'],
    n_page_requests=len(mt), axis_ms=axis_ms,
    n_within_axis=sum(q['t_ms'] <= axis_ms for q in reqs), n_beyond_axis=sum(q['t_ms'] > axis_ms for q in reqs),
    n_beacons_within_axis=sum(q['t_ms'] <= axis_ms and q['kind'] == 'beacon' for q in reqs),
    n_libraries_within_axis=sum(q['t_ms'] <= axis_ms and q['kind'] == 'library' for q in reqs),
    n_distinct_times_within_axis=len({q['t_ms'] for q in reqs if q['t_ms'] <= axis_ms}),
    beyond_axis_ms=[q['t_ms'] for q in reqs if q['t_ms'] > axis_ms],
    beyond_axis_kinds=[q['kind'] for q in reqs if q['t_ms'] > axis_ms],
    t_obs_end_ms=int(round(r['t_obs_end'] - r['nav_wall'])), time_origin_minus_nav_ms=off,
    requests=reqs)
# ticks drawn as one: requests of the same kind less than TICK_MERGE_MS apart. At panel C's scale (6 s over 108 mm,
# 18 mm/s) 50 ms is 0.9 mm, about two widths of a 1.25 pt tick, so such ticks cannot be told apart by eye. Each group
# is drawn at its members' own times and labelled with its count when it holds more than one request.
TICK_MERGE_MS = 50
within = sorted((q for q in reqs if q['t_ms'] <= axis_ms), key=lambda q: q['t_ms'])
groups = []
for q in within:
    g = groups[-1] if groups else None
    if g and g['kind'] == q['kind'] and q['t_ms'] - g['t_ms_first'] < TICK_MERGE_MS:
        g['t_ms_last'] = q['t_ms']
        g['n'] += 1
    else:
        groups.append(dict(kind=q['kind'], t_ms_first=q['t_ms'], t_ms_last=q['t_ms'], n=1))
for a, b in zip(groups, groups[1:]):      # no two groups closer than the merge window (else a badge would be ambiguous)
    assert b['t_ms_first'] - a['t_ms_last'] >= TICK_MERGE_MS, (a, b)
assert sum(g['n'] for g in groups if g['kind'] == 'library') == c_val['n_libraries_within_axis']
assert sum(g['n'] for g in groups if g['kind'] == 'beacon') == c_val['n_beacons_within_axis']
c_val.update(tick_merge_ms=TICK_MERGE_MS, tick_groups=groups, n_tick_groups=len(groups),
             n_tick_groups_multi=sum(g['n'] > 1 for g in groups))
assert c_val['clicks'] is None and c_val['cmp_yes_writes'] == 0
assert bool(bs.set_index('store_id').loc[store, 'neutralized_and_sbx'])
rec('fig4c_recheck', c_val,
    "Panel C: one re-check load (arm R0: no interaction) of the store and vendor chosen by the rules above. Times are "
    "ms since navigation start (requests: wall time minus the navigation request; page scriptlog and banner detector: "
    "performance.now() plus time_origin minus nav_wall). 'Tag neutralised' = the vendor's script element entered the "
    "page with, or was changed to, a blocked type; sandboxed requests = the vendor's ad requests from a Shopify "
    "worker or sandboxed iframe (kind from the vendor classifier: beacon or library). tick_groups: the requests within "
    "the axis, grouped when of the same kind and less than tick_merge_ms apart (drawn as one tick with a count badge).",
    ['crawl/recheck/raw/<store>__R0.json.gz (read-only)', 'crawl/recheck/blocker_by_entry.csv',
     'crawl/recheck/blocker_by_store.csv', 'stats.json:checks.recheck.blocker', 'stats.json:design.timeline_axis_s'],
    'store is in checks.recheck.blocker.stores_neutralized_and_sbx_ids and blocker_by_store.neutralized_and_sbx; '
    'the vendor has a neutralised tag and sandboxed requests and no page-script requests; no click, no CMP yes write')

# ------------------------------------------------------------------ Round 4: the two samples' Tranco rank ranges
# Panels A-C name the samples ('Main sample (top 200k)', 'Expansion (ranks 200k-1M)') and the caption gives the exact
# ranges. The main sample's bound is stats.json design.tranco_top_n; the expansion's range is the Round 4 screen's own
# record (round4/expansion/funnel.json 'ranks', written by round4/expansion/build_candidates.py), read-only here.
R4 = S['round4']['blocklist']
funnel = json.load(open(os.path.join(ROOT, 'round4', 'expansion', 'funnel.json')))
r_lo, r_hi = (int(x) for x in funnel['ranks'].split('-'))
top_n = int(S['design']['tranco_top_n'])
assert r_lo == top_n + 1, (r_lo, top_n)                         # the expansion starts where the main sample ends
assert top_n % 1000 == 0 and r_hi % 1000000 == 0
assert R4['expansion_funnel']['blocklist_at_runtime'] == R4['expansion']['n_blocklist']
# the Round 4 main-sample numbers are the paper's (stats.json round4 = round4/analysis/stats_r4.json, trace check 3)
for k in ('k', 'n'):
    assert R4['main']['primary']['fired'][k] == S['round4']['main_paper']['primary'][k]
assert R4['main']['like_for_like']['mh_no_yes'] == S['fig4']['a']['like_for_like']['mh_no_yes']
rec('fig4_samples',
    dict(main_top_n=top_n, main_top_k=top_n // 1000, expansion_rank_lo=r_lo, expansion_rank_hi=r_hi,
         expansion_rank_lo_k=(r_lo - 1) // 1000, expansion_rank_hi_m=r_hi // 1000000,
         tranco_list_id=funnel['tranco_list_id']),
    "Tranco rank ranges of the two samples in Fig. 4. Main sample: the top main_top_n domains (main_top_k in "
    "thousands, shown as 'top 200k'). Round 4 expansion: ranks expansion_rank_lo to expansion_rank_hi of the same "
    "Tranco list, shown as '200k-1M' (expansion_rank_lo_k in thousands, i.e. the rank just below the range's first "
    "rank, and expansion_rank_hi_m in millions).",
    ['stats.json:design.tranco_top_n', 'round4/expansion/funnel.json:ranks,tranco_list_id (read-only)'],
    'expansion_rank_lo == design.tranco_top_n + 1; round4.blocklist.expansion_funnel.blocklist_at_runtime == '
    'round4.blocklist.expansion.n_blocklist; round4 main primary and mh_no_yes equal the paper values')

json.dump(D, open(DST, 'w'), indent=1)
print('wrote', DST)
print(json.dumps({k: (v['value'] if k != 'fig4a_entries' else v['value']['counts']) for k, v in D.items()}, indent=1)[:4000])
