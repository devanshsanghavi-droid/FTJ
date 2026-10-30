"""Derived numbers for the v2 figure set (figures/v7/FIGURE_PLAN_v2.md).

Every value that a v2 figure shows but that analysis/outputs/stats.json does not hold is computed here from the
committed analysis tables (never from the raw crawl, never typed by hand) and written, with its definition, script and
inputs, to figures/v7/derived_numbers.json. Each block asserts that the table reproduces the stats.json value it
refines, so a drift between this script and analysis/analyze.py fails loudly.

Run from anywhere:  python3 figures/v7/scripts/derive_numbers.py
"""
import json
import os
from urllib.parse import parse_qsl, urlsplit

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))       # study3_shopify_consent/
OUT = os.path.join(ROOT, 'analysis', 'outputs')
DST = os.path.join(ROOT, 'figures', 'v7', 'derived_numbers.json')
SCRIPT = 'figures/v7/scripts/derive_numbers.py'
S = json.load(open(os.path.join(OUT, 'stats.json')))
D = {}


def rec(name, value, definition, inputs, check=None):
    D[name] = dict(value=value, definition=definition, script=SCRIPT, inputs=inputs, check=check)


def kn(d):
    return d['k'], d['n']


# ---------- Fig 2A: sampling funnel (bar lengths) ----------
prov = S['checks']['provenance']['sample']
fx = S['design']['funnel_excl']
flagged = prov['census_drawn'] + prov['random_bucket_flagged']          # census buckets: every flagged domain drawn
verified = prov['census_drawn'] + prov['random_bucket_drawn']
live = verified - fx['drawn_to_live']
sample = live - fx['live_to_sample']
captured = sample - fx['content_excluded'] - fx['sample_to_captured']   # content-sensitivity exclusions after the crawl (2026-09-29)
assert sample == S['design']['sample_n'] and captured == S['design']['n_main'], (sample, captured)
rec('fig2a_funnel', dict(tranco=S['design']['tranco_top_n'], flagged=flagged, verified=verified, live=live,
                         sample=sample, captured=captured, creator=S['design']['n_creator'],
                         excluded=dict(not_live=fx['drawn_to_live'], content_rules=fx['live_to_sample'],
                                       not_captured=fx['sample_to_captured'], content_sensitivity=fx['content_excluded'],
                                       sample_to_analysed=fx['content_excluded'] + fx['sample_to_captured'])),
    'Funnel steps: Tranco top-N; DNS-flagged (census buckets drawn in full + flagged in the random bucket); verified '
    '(drawn); live storefronts; sample; captured in all three base arms and analysed (sample minus the stores excluded '
    'after the crawl for content sensitivity minus the stores not captured). Creator stratum added separately.',
    ['analysis/outputs/stats.json:checks.provenance.sample', 'stats.json:design.funnel_excl', 'stats.json:design'],
    'sample == design.sample_n and captured == design.n_main')

# ---------- Fig 1C: lead of the first sandboxed request over the banner; events beyond the 6 s crop ----------
c = S['fig1c']
tl = pd.read_csv(os.path.join(OUT, 'fig1c_timeline.csv'))
axis_ms = S['design']['timeline_axis_s'] * 1000
assert int((tl.sandbox & (tl.t_ms < c['t_banner'])).sum()) == c['n_sandboxed_before_banner']
rec('fig1c_lead_ms', dict(first_sandboxed_lead_ms=c['t_banner'] - c['t_first_sandboxed'],
                          first_sandboxed_beacon_lead_ms=c['t_banner'] - c['t_first_sandboxed_beacon'],
                          n_requests=int(len(tl)), n_beyond_axis=int((tl.t_ms > axis_ms).sum()), axis_ms=axis_ms,
                          n_sandboxed_before_banner=c['n_sandboxed_before_banner']),
    'Store S1152 Default load: banner-visible time minus first sandboxed request (and first sandboxed data beacon); '
    'requests after the 6 s axis crop (drawn as an edge count).',
    ['stats.json:fig1c', 'analysis/outputs/fig1c_timeline.csv'], 'sandboxed-before-banner count == fig1c.n_sandboxed_before_banner')

# ---------- Fig 2B: the worked request (first sandboxed data beacon with our test code in the Fig 1C load) ----------
ad = pd.read_csv(os.path.join(OUT, 'ad_requests.csv.gz'), low_memory=False,
                 usecols=['load_id', 'stratum', 'cond', 't_ms', 'vendor', 'vgroup', 'origin', 'oclass', 'kind', 'beacon',
                          'host', 'url', 'has_canary', 'has_full_url', 'sandbox', 't_banner_visible', 'event',
                          'pixel_type', 'store_id'])
lid = f"{c['store_id']}__A0"
wx = ad[(ad.load_id == lid) & ad.sandbox & ad.beacon & ad.has_canary].sort_values('t_ms').iloc[0]
q = dict(parse_qsl(urlsplit(wx.url).query))
carrier = next(k for k, v in q.items() if 'utm_campaign=' in v or 'cmpstudy-' in v)
inner = urlsplit(q[carrier])
inner_q = dict(parse_qsl(inner.query))
rec('fig2b_worked_request', dict(load_id=lid, t_ms=int(wx.t_ms), t_banner_ms=float(wx.t_banner_visible),
                                 before_banner_ms=float(wx.t_banner_visible - wx.t_ms), vendor=wx.vendor, vgroup=wx.vgroup,
                                 origin=wx.origin, pixel_type=wx.pixel_type, event=wx.event, host=urlsplit(wx.url).netloc,
                                 path=urlsplit(wx.url).path, n_params=len(q), carrier_param=carrier,
                                 carried_path=inner.path.split('/sandbox/modern')[-1],
                                 carried_origin_marker='web-pixels@.../custom/web-pixel-<id>/sandbox/modern',
                                 test_code=inner_q.get('utm_campaign')),
    'First sandboxed data beacon carrying our test code in the Fig 1C load. Redaction rule for the figure: show host, '
    'path (account number masked), the carrier parameter and the decoded landing path + utm_* test code; drop all other '
    'parameter values (client IDs, hashes).',
    ['analysis/outputs/ad_requests.csv.gz', 'stats.json:fig1c'], None)

# ---------- Fig 1 / 3: banner stores by region default (exact partition) ----------
st = pd.read_csv(os.path.join(OUT, 'store_table.csv'), low_memory=False)
m = st[st.stratum == 'main']
b = m[m.banner_A0 == True]  # noqa: E712
part = {}
for lab, sel in (('allowed', b.region_optout == True), ('denied', b.region_optout == False),  # noqa: E712
                 ('unreadable', b.region_optout.isna())):
    x = b[sel]
    part[lab] = dict(n=int(len(x)), fired=int(x.A0_sbx.astype(bool).sum()))
assert (part['allowed']['fired'], part['allowed']['n']) == kn(S['fig3']['d']['opt_out']['any_sbx'])
assert (part['denied']['fired'], part['denied']['n']) == kn(S['fig3']['d']['opt_in']['any_sbx'])
assert sum(v['n'] for v in part.values()) == S['fig1b']['banner_fires']['n']
assert sum(v['fired'] for v in part.values()) == S['fig1b']['banner_fires']['k']
rec('banner_default_partition', part,
    "Default-load banner stores split by Shopify's region default (allowed until choice / denied until consent / not "
    'readable), with the number whose sandboxed pixel sent an ad request before any choice.',
    ['analysis/outputs/store_table.csv'], 'allowed/denied equal fig3.d; totals equal fig1b.banner_fires')

# ---------- Fig 3C: first sandboxed request vs banner, three exclusive parts ----------
fb = pd.read_csv(os.path.join(OUT, 'fig3b.csv'))
poll = S['design']['banner_poll_ms']
parts = dict(more_than_one_poll_before=int((fb.gap > poll).sum()), within_one_poll_before=int(((fb.gap > 0) & (fb.gap <= poll)).sum()),
             banner_first_or_same=int((fb.gap <= 0).sum()), n=int(len(fb)), poll_ms=poll)
assert (parts['more_than_one_poll_before'], parts['n']) == kn(S['fig3']['b']['before_banner_by_poll'])
assert parts['more_than_one_poll_before'] + parts['within_one_poll_before'] == S['fig3']['b']['before_banner']['k']
rec('fig3c_timing_split', parts,
    'Banner stores with a pre-choice sandboxed request (n = 205): gap = banner visible minus first sandboxed request; '
    '> one poll (250 ms) / 0 < gap <= 250 ms / gap <= 0.', ['analysis/outputs/fig3b.csv', 'stats.json:design.banner_poll_ms'],
    'first part == fig3.b.before_banner_by_poll; first two == fig3.b.before_banner')

# ---------- Fig 4A: declared-blocked entries with a configured sandboxed pixel, fired by route (independent flags) ----------
pairs = pd.read_csv(os.path.join(OUT, 'fig4c_declared_blocked_pairs.csv'))
a0 = ad[(ad.stratum == 'main') & (ad.cond == 'A0')]
po = a0.groupby(['store_id', 'vendor']).oclass.apply(set)


def hier(o):
    return 'none' if o is None else ('sandbox' if 'sandbox' in o else ('open_pixel' if 'open_pixel' in o else ('relay' if 'relay' in o else 'page')))


pairs['oset'] = [po.get((r.store_id, r.vendor)) for r in pairs.itertuples()]
assert all(hier(o) == oc for o, oc in zip(pairs.oset, pairs.outcome)), 'outcome no longer reproduces analyze.py'
pairs['f_sbx'] = [bool(o) and 'sandbox' in o for o in pairs.oset]
pairs['f_page'] = [bool(o) and 'page' in o for o in pairs.oset]
excl = set(S['fig4']['a']['blocklist']['primary']['stores_excluded'])


def routes(g):
    return dict(n=int(len(g)), n_stores=int(g.store_id.nunique()), sandbox=int(g.f_sbx.sum()), page=int(g.f_page.sum()),
                both=int((g.f_sbx & g.f_page).sum()), sandbox_only=int((g.f_sbx & ~g.f_page).sum()),
                page_only=int((~g.f_sbx & g.f_page).sum()), neither_route=int((~g.f_sbx & ~g.f_page).sum()),
                stores_sandbox=int(g[g.f_sbx].store_id.nunique()))


g_all = pairs[pairs.cfg_sandboxed]
r_all = routes(g_all)
assert (r_all['sandbox'], r_all['n']) == kn(S['fig4']['c']['cfg']['sandbox'])
r_pri = routes(g_all[~g_all.store_id.isin(excl)])
rec('fig4a_routes', dict(all_stores=r_all, primary_no_yes=r_pri),
    'Blocklist entries (vendor declared blocked before any choice) whose vendor has a configured sandboxed Shopify pixel '
    'on that store; fired in the Default load from a Shopify sandbox and, independently, from an ordinary page script '
    '(not hierarchical, unlike fig4c.csv outcome). primary_no_yes drops the 7 stores whose CMP wrote marketing: yes.',
    ['analysis/outputs/fig4c_declared_blocked_pairs.csv', 'analysis/outputs/ad_requests.csv.gz',
     'stats.json:fig4.a.blocklist.primary.stores_excluded'], 'sandbox/n == fig4.c.cfg.sandbox; outcome reproduces analyze.py')

# ---------- Fig 5B: why pixels still fire, mutually exclusive classes (hierarchy) ----------
rc = pd.read_csv(os.path.join(OUT, 'residual_composition.csv'))
Dd = rc[rc.arm == 'Decline']
Gg = rc[rc.arm == 'GPC']
f3 = set(Dd[Dd.window.isin(['same_page', 'unload']) & (Dd.cat == 'refused')].store_id)
la = set(Dd[Dd.cat == 'left_allowed'].store_id) - f3
no = set(Dd[Dd.cat == 'none'].store_id) - f3 - la
other = set(Dd.store_id) - f3 - la - no
cl = S['fig5']['c']['composition']['decline']['classes']
assert len(f3) == cl['f3'] and len(f3 | la | no) == cl['union'], (len(f3), len(f3 | la | no))
dec = dict(n=S['fig5']['c']['decline_n'], kept_sending_refused_purpose=len(f3), only_left_allowed_purposes=len(la),
           no_purpose=len(no), other=len(other), any=len(set(Dd.store_id)),
           new_pixel_declaring_refused_purpose=cl['fresh_refused'])
g_la = set(Gg[Gg.cat == 'left_allowed'].store_id)
g_no = set(Gg[Gg.cat == 'none'].store_id) - g_la
g_ot = set(Gg.store_id) - g_la - g_no
gp = S['fig5']['c']['composition']['gpc']
assert len(g_la) == gp['left_allowed']['k'] and len(set(Gg.store_id)) == gp['any']['k']
gpc = dict(n=S['fig5']['c']['gpc_n'], only_left_allowed_purposes=len(g_la), no_purpose=len(g_no), other_unmatched=len(g_ot),
           any=len(set(Gg.store_id)), pixel_declaring_sale=gp['refused']['k'])
rec('fig5b_exclusive_classes', dict(decline_refused=dec, gpc=gpc),
    'Stores with a residual sandboxed ad request, one class per store by hierarchy: (1) a pixel that declares the '
    'refused purpose kept sending (same page or unload; Decline only), else (2) a pixel declaring only purposes the '
    'choice left allowed, else (3) a pixel declaring no purpose, else other/unmatched. Decline: stores with a recorded '
    'refusal (any window after the click); GPC: stores where Shopify set sale of data: no.',
    ['analysis/outputs/residual_composition.csv', 'stats.json:fig5.c.composition'],
    'F3 and union equal composition.decline.classes; GPC left_allowed and any equal composition.gpc')

# ---------- Fig 5C: the race per sandbox (lag = sandbox start minus CMP write) ----------
sc = pd.read_csv(os.path.join(OUT, 'sandbox_creations.csv'), low_memory=False, dtype={'pixel_id': str})
f5d = pd.read_csv(os.path.join(OUT, 'fig5d.csv'))
sc3 = sc[sc.declares_marketing & (sc.pixel_api.astype(str) != 'shopify-pixel') & (sc.kind != 'open_main_thread_pixel')]
race = {}
for ch in ('deny', 'grant'):
    L = f5d[f5d.change == ch][['load_id', 't_update']]
    j = sc3.merge(L, on='load_id')
    lag = j.t_ms - j.t_update
    race[ch] = dict(sandboxes=int(len(j)), before=int((lag < 0).sum()), after=int((lag >= 0).sum()),
                    median_lag_ms=float(lag.median()), clip_lo_ms=-3000, clip_hi_ms=1000,
                    n_below_clip=int((lag < -3000).sum()), n_above_clip=int((lag > 1000).sum()), loads=int(len(L)))
    assert race[ch]['sandboxes'] == S['fig5']['d'][ch]['pixels'] and race[ch]['before'] == S['fig5']['d'][ch]['pixels_before']
rec('fig5c_race_per_sandbox', race,
    "Third-party sandboxes declaring 'marketing' in loads where a CMP wrote marketing no (deny) or yes (grant) without "
    'a click; lag = sandbox start minus the consent event; axis clipped at -3 s / +1 s (edge counts).',
    ['analysis/outputs/sandbox_creations.csv', 'analysis/outputs/fig5d.csv'], 'totals equal fig5.d.{deny,grant}.pixels / pixels_before')

with open(DST, 'w') as f:
    json.dump(D, f, indent=1, default=int)
print(json.dumps({k: v['value'] for k, v in D.items()}, indent=1, default=int))
