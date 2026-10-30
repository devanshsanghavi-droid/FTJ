"""Derived numbers for Figure 1 (v5) that analysis/outputs/stats.json does not hold in the form the figure prints.

v5 (2026-10-17): panel b is the two-lane re-check trace that was v4 Fig 4d; its record `fig1b_trace` is computed here
from the read-only re-check crawl (ported from figures/v4/fig4/scripts/derive_fig4.py, block 'fig4c_recheck', same
rules and the same values) so that Figure 1 no longer depends on Figure 4's files. When figures/v7/fig4/
derived_numbers.json still carries `fig4c_recheck`, the two records must be identical (asserted).

The records below `fig1b_trace` are kept from the v2-v4 single-store strip (they feed
analysis/outputs/derived_numbers_provenance.json); the v5 panels do not print them.
They give the lead of the first sandboxed request over the banner in SECONDS (stats.json has both times
in ms), the lead of the first sandboxed DATA BEACON in ms (the first sandboxed request is a library load, so the caption
gives both; cross-figure QA 2026-09-26), the requests that fall beyond the 6 s crop, counted per row (the edge
count), and how the requests within the crop group into visible ticks (caption; cross-figure QA 2026-09-26). Each value is computed from
committed analysis outputs (stats.json, fig1c_timeline.csv), never typed, and checked against the shared
figures/v7/derived_numbers.json record `fig1c_lead_ms` (built by figures/v7/scripts/derive_numbers.py).

Writes figures/v7/fig1/derived_numbers.json (value, definition, script, inputs, check per record).
Run:  python3 figures/v7/fig1/scripts/derive_fig1.py
"""
import gzip
import json
import os
import re

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FIG1 = os.path.normpath(os.path.join(HERE, '..'))
def _find_study(d):
    """The study root: the first ancestor holding analysis/ and figures/ (a copied figure set may sit deeper)."""
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, 'analysis')) and os.path.isdir(os.path.join(d, 'figures')):
            return d
        d = os.path.dirname(d)
    raise RuntimeError('study root not found above ' + FIG1)


STUDY = _find_study(FIG1)
OUT = os.path.join(STUDY, 'analysis', 'outputs')
RECHECK = os.path.join(STUDY, 'crawl', 'recheck')
SCRIPT = 'figures/v7/fig1/scripts/derive_fig1.py'
DST = os.path.join(FIG1, 'derived_numbers.json')
TICK_MERGE_MS = 50       # tick-grouping window of every event strip (a drawing rule, not data): Fig 1b and 1c

# ---- panel b (re-check trace): the rules of v4 Fig 4d (figures/v4/fig4/scripts/derive_fig4.py), unchanged
BLOCKED = {'javascript/blocked', 'text/plain', 'osano/blocked'}                       # = crawl/recheck/analyze_recheck.py
SANDBOX = {'strict_worker', 'lax_iframe'}
INLINE_SIG = {'tiktok': r'\bttq\b|analytics\.tiktok', 'meta': r'\bfbq\b|connect\.facebook', 'pinterest': r'\bpintrk\b|pinimg',
              'snap': r'\bsnaptr\b|sc-static', 'microsoft_uet': r'\buetq\b|bat\.bing', 'google_ads': r'AW-\d|googleads',
              'reddit': r'\brdt\(|redditstatic'}
VENDOR_LABEL = {'tiktok': 'TikTok', 'meta': 'Meta', 'google_ads': 'Google', 'pinterest': 'Pinterest', 'snap': 'Snap',
                'microsoft_uet': 'Microsoft'}


def trace_record(S):
    """Panel b: one re-check load (arm R0, no interaction). Store: the first ID in
    stats.json checks.recheck.blocker.stores_neutralized_and_sbx_ids whose CMP wrote no 'marketing: yes' (not in
    fig4.a.blocklist.primary.stores_excluded). Vendor: that store's declared-blocked vendor with a neutralised page tag
    and the most sandboxed ad requests. Times in ms since navigation start."""
    excl = set(S['fig4']['a']['blocklist']['primary']['stores_excluded'])
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
        neu = [x for x in neutral if x.get('vendor') == v or
               (x.get('inline') and re.search(INLINE_SIG.get(v, r'$^'), x.get('inline') or ''))]
        sbx = sorted([q for q in rq if q['vendor'] == v and q.get('origin') in SANDBOX], key=lambda q: q['t'])
        mt = [q for q in rq if q['vendor'] == v and q.get('origin') not in SANDBOX]
        return neu, sbx, mt

    per_vendor = {v: vendor_events(v) for v in sorted(E.vendor)}
    vendor = max(per_vendor, key=lambda v: (len(per_vendor[v][1]), v))
    neu, sbx, mt = per_vendor[vendor]
    assert neu and sbx and not mt, 'panel b needs a neutralised tag, sandboxed requests and no page-script requests'
    axis_ms = S['design']['timeline_axis_s'] * 1000
    cs3 = (r.get('probe') or {}).get('cs3') or {}
    t_banner = (cs3.get('banner') or {}).get('t')
    reqs = [dict(t_ms=int(q['t']), kind=q.get('vkind'), origin=q['origin'], type=q.get('type')) for q in sbx]
    yes_writes = [e for e in (cs3.get('ev') or []) if '"marketingAllowed":true' in (e.get('d') or '')]
    v = dict(
        store_id=store, cmp=str(E.cmp.iloc[0]), vendor=vendor, vendor_label=VENDOR_LABEL.get(vendor, vendor),
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
        t_first_sandbox_ms=reqs[0]['t_ms'],
        lead_first_sandbox_over_tag_ms=int(round(min(x['t'] for x in neu) + off)) - reqs[0]['t_ms'],
        n_page_requests=len(mt), axis_ms=axis_ms,
        n_within_axis=sum(q['t_ms'] <= axis_ms for q in reqs), n_beyond_axis=sum(q['t_ms'] > axis_ms for q in reqs),
        n_beacons_within_axis=sum(q['t_ms'] <= axis_ms and q['kind'] == 'beacon' for q in reqs),
        n_libraries_within_axis=sum(q['t_ms'] <= axis_ms and q['kind'] == 'library' for q in reqs),
        n_distinct_times_within_axis=len({q['t_ms'] for q in reqs if q['t_ms'] <= axis_ms}),
        beyond_axis_ms=[q['t_ms'] for q in reqs if q['t_ms'] > axis_ms],
        beyond_axis_kinds=[q['kind'] for q in reqs if q['t_ms'] > axis_ms],
        t_obs_end_ms=int(round(r['t_obs_end'] - r['nav_wall'])), time_origin_minus_nav_ms=off,
        requests=reqs)
    # ticks drawn as one: requests of the same kind less than TICK_MERGE_MS apart (at panel b's scale, 6 s over 115 mm,
    # 50 ms is under 1 mm, about two widths of a 1.4 pt tick). Each group is drawn at its members' own times and carries
    # a count badge when it holds more than one request.
    within = sorted((q for q in reqs if q['t_ms'] <= axis_ms), key=lambda q: q['t_ms'])
    groups = []
    for q in within:
        g = groups[-1] if groups else None
        if g and g['kind'] == q['kind'] and q['t_ms'] - g['t_ms_first'] < TICK_MERGE_MS:
            g['t_ms_last'] = q['t_ms']
            g['n'] += 1
        else:
            groups.append(dict(kind=q['kind'], t_ms_first=q['t_ms'], t_ms_last=q['t_ms'], n=1))
    for a, b in zip(groups, groups[1:]):      # no two groups closer than the merge window (else a badge is ambiguous)
        assert b['t_ms_first'] - a['t_ms_last'] >= TICK_MERGE_MS, (a, b)
    assert sum(g['n'] for g in groups if g['kind'] == 'library') == v['n_libraries_within_axis']
    assert sum(g['n'] for g in groups if g['kind'] == 'beacon') == v['n_beacons_within_axis']
    v.update(tick_merge_ms=TICK_MERGE_MS, tick_groups=groups, n_tick_groups=len(groups),
             n_tick_groups_multi=sum(g['n'] > 1 for g in groups))
    assert v['clicks'] is None and v['cmp_yes_writes'] == 0
    assert bool(bs.set_index('store_id').loc[store, 'neutralized_and_sbx'])
    # one record, two figures: while Fig 4 (v5) still carries the v4 record, it must be identical
    f4 = os.path.join(STUDY, 'figures', 'v7', 'fig4', 'derived_numbers.json')
    if os.path.exists(f4):
        old = json.load(open(f4)).get('fig4c_recheck')
        if old is not None:
            assert json.loads(json.dumps(v)) == old['value'], 'fig1b_trace differs from fig4/derived_numbers.json'
    return dict(
        value=v,
        definition="Fig 1b (v4 Fig 4d): one re-check load (arm R0: no interaction) of the store and vendor chosen by the "
                   "rules in value.rule_store / value.rule_vendor. Times are ms since navigation start (requests: wall "
                   "time minus the navigation request; page scriptlog and banner detector: performance.now() plus "
                   "time_origin minus nav_wall). 'Tag neutralised' = the vendor's script element entered the page with, "
                   "or was changed to, a blocked type; sandboxed requests = the vendor's ad requests from a Shopify "
                   "worker or sandboxed iframe (kind from the vendor classifier: beacon or library). tick_groups: the "
                   "requests within the axis, grouped when of the same kind and less than tick_merge_ms apart (drawn as "
                   "one tick with a count badge).",
        script=SCRIPT,
        inputs=['crawl/recheck/raw/<store>__R0.json.gz (read-only)', 'crawl/recheck/blocker_by_entry.csv',
                'crawl/recheck/blocker_by_store.csv', 'stats.json:checks.recheck.blocker',
                'stats.json:fig4.a.blocklist.primary.stores_excluded', 'stats.json:design.timeline_axis_s'],
        check='store is in checks.recheck.blocker.stores_neutralized_and_sbx_ids and blocker_by_store.neutralized_and_sbx; '
              'the vendor has a neutralised tag and sandboxed requests and no page-script requests; no click, no CMP '
              "'yes' write; equals figures/v7/fig4/derived_numbers.json:fig4c_recheck while that record exists")


RASTER_X_S = (-4.0, 8.0)     # panel c's time axis (s relative to the banner becoming visible); a drawing choice


def raster_record(S):
    """Panel c: the banner stores whose sandboxed pixel sent an ad request before any choice (stats fig3/b/n), and
    the requests that fall outside the drawn time axis (v5 rule: out-of-range values are stated in the panel)."""
    import sys
    sys.path.insert(0, os.path.join(STUDY, 'analysis'))
    from common import CONTENT_EXCLUDED
    st = pd.read_csv(os.path.join(OUT, 'store_table.csv'))
    m = st[(st.stratum == 'main') & (~st.store_id.isin(CONTENT_EXCLUDED))]
    g = m[(m.banner_A0 == True) & (m.A0_sbx == True)].set_index('store_id')        # noqa: E712
    assert len(g) == S['fig3']['b']['n'] == S['fig1b']['banner_fires']['k']
    r = pd.read_csv(os.path.join(OUT, 'ad_requests.csv.gz'), low_memory=False,
                    usecols=['store_id', 'arm', 'sandbox', 'ad', 't_ms', 'vgroup'])
    q = r[(r.arm == 'A0') & r.store_id.isin(g.index) & (r.sandbox == True) & (r.ad == True)].copy()   # noqa: E712
    assert q.groupby('store_id').t_ms.min().sub(g.A0_first_sbx_t).abs().max() == 0
    rel = (q.t_ms - q.store_id.map(g.t_banner_A0)) / 1000.0
    lead = (g.A0_first_sbx_t - g.t_banner_A0) / 1000.0
    xl, xr = RASTER_X_S
    assert int((lead < 0).sum()) == S['fig3']['b']['before_banner']['k']
    v = dict(x_lo_s=xl, x_hi_s=xr, n_stores=int(len(g)), n_requests=int(len(q)),
             n_requests_left=int((rel < xl).sum()), n_requests_right=int((rel > xr).sum()),
             n_requests_within=int(((rel >= xl) & (rel <= xr)).sum()),
             n_first_left=int((lead < xl).sum()), n_first_right=int((lead > xr).sum()))
    assert v['n_requests_left'] + v['n_requests_right'] + v['n_requests_within'] == v['n_requests']
    return dict(
        value=v,
        definition='Fig 1c raster: the banner stores whose Default load sent a sandboxed ad request before any choice '
                   '(one row each) and their sandboxed ad requests, timed relative to the banner becoming visible. '
                   'n_requests_left / _right: requests before x_lo_s / after x_hi_s (not drawn; counted in the panel); '
                   'n_first_left / _right: stores whose FIRST request lies outside the axis (the first-request line is '
                   'clipped there).',
        script=SCRIPT, inputs=['analysis/outputs/store_table.csv', 'analysis/outputs/ad_requests.csv.gz',
                               'analysis/common.py:CONTENT_EXCLUDED', 'stats.json:fig3.b'],
        check='n_stores == stats.json fig3.b.n == fig1b.banner_fires.k; first request < 0 on fig3.b.before_banner.k '
              'stores; left + right + within == n_requests')


def main():
    S = json.load(open(os.path.join(OUT, 'stats.json')))
    shared = json.load(open(os.path.join(STUDY, 'figures', 'v7', 'derived_numbers.json')))['fig1c_lead_ms']['value']
    c = S['fig1c']
    tl = pd.read_csv(os.path.join(OUT, 'fig1c_timeline.csv'))
    axis_s = S['design']['timeline_axis_s']

    # --- lead of the first sandboxed request over the banner, in seconds
    lead_ms = c['t_banner'] - c['t_first_sandboxed']
    first = tl[tl.sandbox].sort_values('t_ms').iloc[0]
    assert float(first.t_ms) == c['t_first_sandboxed'], (first.t_ms, c['t_first_sandboxed'])
    assert lead_ms == shared['first_sandboxed_lead_ms'], (lead_ms, shared)
    # the first sandboxed request is a library (script) load; the first sandboxed data beacon (any non-library ad request,
    # common.py) left later: its lead is what the caption states next to the bracket's 0.67 s
    assert (first.kind == 'library') == bool(c['first_sandboxed_is_library']), (first.kind, c['first_sandboxed_is_library'])
    beacon = tl[tl.sandbox & (tl.kind != 'library')].sort_values('t_ms').iloc[0]
    assert float(beacon.t_ms) == c['t_first_sandboxed_beacon'], (beacon.t_ms, c['t_first_sandboxed_beacon'])
    beacon_lead_ms = c['t_banner'] - c['t_first_sandboxed_beacon']
    assert beacon_lead_ms == shared['first_sandboxed_beacon_lead_ms'], (beacon_lead_ms, shared)

    # --- requests beyond the axis crop, by the row they would sit in (vendor group if sandboxed, else 'outside')
    tl['row'] = tl.vgroup.where(tl.sandbox, 'outside')
    beyond = tl[tl.t_ms > axis_s * 1000]
    by_row = {k: int(v) for k, v in beyond.groupby('row').size().items()}
    assert sum(by_row.values()) == shared['n_beyond_axis'], (by_row, shared)
    assert len(tl) == c['n_ad_requests'] and int(tl.sandbox.sum()) == c['n_sandboxed']

    # --- ticks drawn as one (cross-figure QA 2026-09-26): requests in one row less than TICK_MERGE_MS apart overlap at
    # this panel's scale (6 s over 76 mm, 12.7 mm/s: 50 ms = 0.63 mm, under two widths of a 1.25 pt tick), and a short
    # (library) tick under a tall one is hidden, so rows are grouped regardless of kind. Same window as Fig 1b.
    within = tl[tl.t_ms <= axis_s * 1000].sort_values(['row', 't_ms'], kind='stable')
    groups = []
    for row, g in within.groupby('row', sort=False):
        cur = None
        for q in g.itertuples():
            if cur is not None and q.t_ms - cur['t_ms_first'] < TICK_MERGE_MS:
                cur['t_ms_last'] = int(q.t_ms)
                cur['n'] += 1
                cur['n_library'] += int(q.kind == 'library')
            else:
                cur = dict(row=str(row), t_ms_first=int(q.t_ms), t_ms_last=int(q.t_ms), n=1,
                           n_library=int(q.kind == 'library'))
                groups.append(cur)
    for a, b in zip(groups, groups[1:]):        # distinct ticks in a row are at least the window apart
        if a['row'] == b['row']:
            assert b['t_ms_first'] - a['t_ms_last'] >= TICK_MERGE_MS, (a, b)
    assert sum(g['n'] for g in groups) == len(within) == c['n_ad_requests'] - int(len(beyond))
    big = max(groups, key=lambda g: g['n'])
    assert sum(g['n'] == big['n'] for g in groups) == 1, 'largest tick group is not unique'
    tr = trace_record(S)                       # one merge rule for both event strips (Fig 1b, 1c): TICK_MERGE_MS
    assert tr['value']['tick_merge_ms'] == TICK_MERGE_MS

    D = {
        'fig1b_trace': tr,
        'fig1c_raster': raster_record(S),
        'fig1c_lead_s': dict(
            value=dict(first_sandboxed_lead_s=lead_ms / 1000, first_sandboxed_t_s=c['t_first_sandboxed'] / 1000,
                       banner_t_s=c['t_banner'] / 1000, first_sandboxed_vgroup=str(first.vgroup),
                       first_sandboxed_kind=str(first.kind),
                       first_sandboxed_beacon_lead_ms=int(beacon_lead_ms),
                       first_sandboxed_beacon_vgroup=str(beacon.vgroup)),
            definition='Store S1152 Default load: banner-visible time minus the first sandboxed ad request, in '
                       'seconds (Fig 1C bracket label; that request is a library load), plus the two event times in '
                       'seconds (bracket ends), the row and kind of the first sandboxed request, and the banner-visible '
                       'time minus the first sandboxed DATA BEACON in ms (caption).',
            script=SCRIPT, inputs=['analysis/outputs/stats.json:fig1c', 'analysis/outputs/fig1c_timeline.csv'],
            check='first_sandboxed_lead_s * 1000 == figures/v7/derived_numbers.json:fig1c_lead_ms.first_sandboxed_lead_ms; '
                  'first sandboxed row of fig1c_timeline.csv == stats.json:fig1c.t_first_sandboxed and its kind '
                  'agrees with fig1c.first_sandboxed_is_library; first sandboxed non-library row == '
                  'fig1c.t_first_sandboxed_beacon; first_sandboxed_beacon_lead_ms == '
                  'figures/v7/derived_numbers.json:fig1c_lead_ms.first_sandboxed_beacon_lead_ms'),
        'fig1c_beyond_axis': dict(
            value=dict(axis_s=axis_s, n_beyond=int(len(beyond)), by_row=by_row),
            definition='Ad requests of the Fig 1C load sent after the 6 s axis crop (design.timeline_axis_s), by row '
                       '(vendor group for sandboxed requests, "outside" otherwise); drawn as an edge count.',
            script=SCRIPT, inputs=['analysis/outputs/fig1c_timeline.csv', 'analysis/outputs/stats.json:design'],
            check='n_beyond == figures/v7/derived_numbers.json:fig1c_lead_ms.n_beyond_axis'),
        'fig1c_ticks': dict(
            value=dict(merge_ms=TICK_MERGE_MS, n_within_axis=int(len(within)), n_ticks=len(groups),
                       n_ticks_multi=sum(g['n'] > 1 for g in groups),
                       largest=dict(n=big['n'], row=big['row'], t_s=big['t_ms_first'] / 1000,
                                    n_library=big['n_library']),
                       groups=groups),
            definition='Fig 1C ticks as drawn: the ad requests within the 6 s axis, grouped per row (vendor group if '
                       'sandboxed, else "outside") so that a request joins the current group when it left less than '
                       'merge_ms after the group\'s first request, whatever its kind (a short library tick under a '
                       'tall beacon tick is hidden). Distinct groups in a row are at least merge_ms apart, so '
                       '"requests less than merge_ms apart share a tick" holds exactly. n_ticks = visible ticks; '
                       'largest = the group with the most requests (caption). Window as the Fig 1b trace (fig1b_trace.tick_merge_ms).',
            script=SCRIPT, inputs=['analysis/outputs/fig1c_timeline.csv', 'analysis/outputs/stats.json:design,fig1c'],
            check='sum of group sizes == n_within_axis == stats.json:fig1c.n_ad_requests - fig1c_beyond_axis.n_beyond; '
                  'gaps between groups in a row >= merge_ms; merge_ms == fig1b_trace.tick_merge_ms'),
    }
    json.dump(D, open(DST, 'w'), indent=1)
    print('wrote', DST)
    print(json.dumps({k: v['value'] for k, v in D.items()}))


if __name__ == '__main__':
    main()
