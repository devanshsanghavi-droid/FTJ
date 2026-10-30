"""Derived numbers for the v2 Supplementary Figures (figures/v7/FIGURE_PLAN_v2.md, section 3).

Values that a supplementary figure draws or prints but that analysis/outputs/stats.json (or figures/v7/derived_numbers.json)
does not hold are computed here from committed analysis / crawl tables (read only; never the raw crawl) and written, with
definition, script and inputs, to figures/v7/supp/derived_numbers.json. Every block asserts that it reproduces the
stats.json values it refines, so a drift fails loudly. Entry-level flags for the S7B unit chart go to
figures/v7/supp/tables/s7b_entries.csv (drawing data, 104 rows).

Run:  python3 figures/v7/supp/scripts/derive_supp_numbers.py
"""
import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SUPP = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(SUPP, '..', '..', '..'))            # study3_shopify_consent/
OUT = os.path.join(ROOT, 'analysis', 'outputs')
CRAWL = os.path.join(ROOT, 'crawl')
DST = os.path.join(SUPP, 'derived_numbers.json')
TAB = os.path.join(SUPP, 'tables')
os.makedirs(TAB, exist_ok=True)
SCRIPT = 'figures/v7/supp/scripts/derive_supp_numbers.py'
S = json.load(open(os.path.join(OUT, 'stats.json')))
DV2 = json.load(open(os.path.join(ROOT, 'figures', 'v7', 'derived_numbers.json')))
D = {}


def rec(name, value, definition, inputs, check=None):
    D[name] = dict(value=value, definition=definition, script=SCRIPT, inputs=inputs, check=check)


def kn(d):
    return d['k'], d['n']


# ---------- S7B: blocklist entries by route, all 21 blocklist stores (unit chart; independent route flags) ----------
ad = pd.read_csv(os.path.join(OUT, 'ad_requests.csv.gz'), low_memory=False, usecols=['store_id', 'stratum', 'cond', 'vendor', 'oclass'])
a0 = ad[(ad.stratum == 'main') & (ad.cond == 'A0')]
po = a0.groupby(['store_id', 'vendor']).oclass.apply(set)
pairs = pd.read_csv(os.path.join(OUT, 'fig4c_declared_blocked_pairs.csv'))
pairs['oset'] = [po.get((r.store_id, r.vendor)) for r in pairs.itertuples()]


def hier(o):
    return 'none' if o is None else ('sandbox' if 'sandbox' in o else ('open_pixel' if 'open_pixel' in o else ('relay' if 'relay' in o else 'page')))


assert all(hier(o) == oc for o, oc in zip(pairs.oset, pairs.outcome)), 'outcome no longer reproduces analyze.py'
pairs['f_sbx'] = [bool(o) and 'sandbox' in o for o in pairs.oset]
pairs['f_page'] = [bool(o) and 'page' in o for o in pairs.oset]
pairs['f_any'] = pairs.outcome != 'none'
excl = set(S['fig4']['a']['blocklist']['primary']['stores_excluded'])
pairs['primary'] = ~pairs.store_id.isin(excl)
cfg = pairs[pairs.cfg_sandboxed]
nocfg = pairs[~pairs.cfg_sandboxed]
r_cfg = dict(n=int(len(cfg)), n_stores=int(cfg.store_id.nunique()), sandbox=int(cfg.f_sbx.sum()), page=int(cfg.f_page.sum()),
             both=int((cfg.f_sbx & cfg.f_page).sum()), neither=int((~cfg.f_sbx & ~cfg.f_page).sum()),
             sandbox_only=int((cfg.f_sbx & ~cfg.f_page).sum()), page_only=int((~cfg.f_sbx & cfg.f_page).sum()))
r_no = dict(n=int(len(nocfg)), n_stores=int(nocfg.store_id.nunique()), any=int(nocfg.f_any.sum()))
va = DV2['fig4a_routes']['value']['all_stores']
assert (r_cfg['sandbox'], r_cfg['page'], r_cfg['both'], r_cfg['n'], r_cfg['n_stores']) == \
    (va['sandbox'], va['page'], va['both'], va['n'], va['n_stores'])
assert (r_cfg['sandbox'], r_cfg['n']) == kn(S['fig4']['c']['cfg']['sandbox'])
assert (r_no['any'], r_no['n']) == kn(S['fig4']['c']['nocfg']['any']) and r_no['n_stores'] == S['fig4']['c']['nocfg']['n_stores']
assert pairs.store_id.nunique() == S['fig4']['c']['n_stores'] and len(pairs) == S['fig4']['c']['n_pairs']
rec('s7b_routes', dict(cfg=r_cfg, nocfg=r_no, n_blocklist_stores=int(pairs.store_id.nunique()), n_entries=int(len(pairs))),
    'Blocklist entries (an ad vendor that a CMP blocklist declared blocked before any choice), all 21 blocklist stores, '
    'Default load. cfg: the vendor has a configured sandboxed Shopify pixel on the store; flags sandbox / page are '
    'independent (fired from a Shopify sandbox; fired from an ordinary page script). nocfg: no configured sandboxed '
    'pixel of the vendor identified; any = fired by any route (sandbox, OPEN pixel, relay or page).',
    ['analysis/outputs/fig4c_declared_blocked_pairs.csv', 'analysis/outputs/ad_requests.csv.gz'],
    'cfg equals figures/v7/derived_numbers.json fig4a_routes.all_stores and fig4.c.cfg.sandbox; nocfg.any equals fig4.c.nocfg.any')
ent = pairs[['store_id', 'vendor', 'vgroup', 'cfg_sandboxed', 'f_sbx', 'f_page', 'f_any', 'primary', 'outcome']]
ent.to_csv(os.path.join(TAB, 's7b_entries.csv'), index=False)

# ---------- S7C: re-check load, nested store tallies ----------
bs = pd.read_csv(os.path.join(CRAWL, 'recheck', 'blocker_by_store.csv'))
bl = S['checks']['recheck']['blocker']
act = bs[bs.blocker_active]
neu = bs[bs.declared_neutralized]
ns = bs[bs.neutralized_and_sbx]
assert set(neu.store_id) <= set(act.store_id) and set(ns.store_id) <= set(neu.store_id), 'tallies are not nested'
assert len(bs) == bl['stores'] and len(act) == bl['active']['k'] and len(neu) == bl['stores_declared_tag_neutralized'] \
    and len(ns) == bl['stores_neutralized_and_sbx']
fm = bs[bs.declared_fired_sbx_main_crawl]
rec('s7c_recheck_nesting', dict(stores=int(len(bs)), active=int(len(act)), declared_tag_neutralized=int(len(neu)),
                                neutralized_and_sbx=int(len(ns)), nested=True,
                                # the stores that leave each stage (Fig. S7c's branches): each stage is the one above minus these
                                excluded=dict(not_active=int(len(bs) - len(act)), not_neutralised=int(len(act) - len(neu)),
                                              sent_nothing=int(len(neu) - len(ns))),
                                fired_main_crawl=int(len(fm)), fired_main_crawl_fired_again=int(fm.declared_fired_sbx_recheck.sum())),
    'Re-check load, 21 blocklist stores: blocker active; of those, the tag of a declared-blocked vendor was neutralised; '
    "of those, the same vendor's sandboxed pixel sent an ad request. Each set is contained in the previous one.",
    ['crawl/recheck/blocker_by_store.csv (read only)'],
    'counts equal checks.recheck.blocker.{stores, active.k, stores_declared_tag_neutralized, stores_neutralized_and_sbx}')
assert (int(fm.declared_fired_sbx_recheck.sum()), len(fm)) == kn(bl['fired_main_crawl_fired_again'])

# ---------- S8D: race per load, loads per row ----------
f5d = pd.read_csv(os.path.join(OUT, 'fig5d.csv'))
rows = {}
for ch in ('deny', 'grant'):
    for arm in ('A0', 'A2'):
        g = f5d[(f5d.change == ch) & (f5d.arm == arm)]
        rows[f'{ch}_{arm}'] = dict(loads=int(len(g)), first_before=int((g.dt_first < 0).sum()), first_after=int((g.dt_first >= 0).sum()),
                                   min_ms=float(g.dt_first.min()), max_ms=float(g.dt_first.max()))
dd = S['fig5']['d']
assert rows['deny_A0']['loads'] == dd['deny']['by_arm']['A0'] and rows['deny_A2']['loads'] == dd['deny']['by_arm']['A2']
assert rows['deny_A0']['first_before'] + rows['deny_A2']['first_before'] == dd['deny']['loads_first_before']
assert rows['grant_A0']['loads'] + rows['grant_A2']['loads'] == dd['grant']['loads']
assert rows['grant_A0']['first_before'] + rows['grant_A2']['first_before'] == dd['grant']['loads_first_before']
rec('s8d_race_loads', rows,
    "Loads in which a CMP wrote 'marketing: no' (deny) or 'yes' (grant) without a click, by arm (A0 Default, A2 GPC): "
    'number of loads, and loads whose first third-party marketing sandbox started before / at or after the write.',
    ['analysis/outputs/fig5d.csv'], 'deny loads by arm equal fig5.d.deny.by_arm; first-before totals equal fig5.d.*.loads_first_before')

# ---------- S9B: Google beacons by Consent Mode state, the remainder 'other state' ----------
gc = S['fig5']['flags']['google_beacons_gcs']
st = {}
for arm in ('Default', 'Decline_next', 'GPC'):
    r = gc[arm]
    other = r['with_gcs'] - r['G100'] - r['G101'] - r['G111']
    assert other >= 0 and r['with_gcs'] + r['none'] == r['n']
    st[arm] = dict(n=r['n'], G100=r['G100'], G101=r['G101'], G111=r['G111'], other_state=int(other), no_state=r['none'])
rec('s9b_gcs_states', st,
    "Google ad beacons by the Consent Mode state in their 'gcs' parameter: G100 (ad and analytics storage denied), G101 (ad "
    'storage denied, analytics granted), G111 (both granted), other states, no state. other_state = with_gcs - G100 - G101 - G111.',
    ['stats.json:fig5.flags.google_beacons_gcs'], 'with_gcs + none == n for every arm')

# ---------- S9C: share of Google ad requests carrying each refusal-signal kind, by arm (drawn as points; no text) ----------
fk = S['fig5']['flags']['google_flag_kinds']
sh = {}
for arm in ('Default', 'Decline_next', 'GPC'):
    r = fk[arm]
    sh[arm] = dict(n=r['n'], **{k: dict(k=r[k], p=r[k] / r['n']) for k in ('gcs_ad_denied', 'gcd_denied', 'npa', 'rdp', 'us_privacy_optout')})
assert fk['Decline_next']['n'] == S['fig5']['flags']['by_group']['Google']['Decline']['n']
rec('s9c_google_flag_shares', sh,
    'Google ad requests by arm (Default load; next page after Decline; GPC load): share carrying each refusal signal in the '
    "URL: Consent Mode 'gcs' with ad storage denied, 'gcd' denied, npa=1, rdp=1, us_privacy opt-out. p = k / n.",
    ['stats.json:fig5.flags.google_flag_kinds'], 'Decline_next n equals fig5.flags.by_group.Google.Decline.n')

# ---------- S9C: 'other' Consent Mode states (too thin to draw; the caption gives their largest share) ----------
osh = {arm: dict(k=st[arm]['other_state'], n=st[arm]['n'], p=st[arm]['other_state'] / st[arm]['n']) for arm in st}
rec('s9c_other_state', dict(by_arm=osh, max_share=max(v['p'] for v in osh.values())),
    "Google ad beacons whose 'gcs' state is none of G100, G101, G111, by arm, and the largest of these shares. In Fig. S9C "
    'such a segment is narrower than the white gap between segments, so it is not drawn.',
    ['figures/v7/supp/derived_numbers.json:s9b_gcs_states'], 'k equals s9b_gcs_states other_state')


# ---------- S9D: Store C request ticks grouped by the Fig. 4C rule (tick_groups) ----------
# Fig. 4C draws requests of one kind that are less than tick_merge_ms apart as one tick with a count badge ('x2').
# The same rule, with the same window (read from fig4/derived_numbers.json, never typed), groups the S9D ticks. In S9D
# 'one kind' is one drawn mark: one vendor group (tick colour) and one tick height (tall: data beacons and other
# requests; short: library loads), within one load and one sub-row (sandbox / other). A request joins the current group
# when it is less than the window after the group's latest request (consecutive requests less than the window apart),
# so two groups of one kind are always at least the window apart. The function reproduces Fig. 4C's own tick_groups
# from its stored requests (asserted), so the two figures group ticks identically.
F4 = json.load(open(os.path.join(ROOT, 'figures', 'v7', 'fig4', 'derived_numbers.json')))
F4C = F4['fig4c_recheck']['value']
MERGE_MS = F4C['tick_merge_ms']


def tick_groups(reqs, merge_ms=MERGE_MS):
    """reqs: dicts with t_ms and kind (sorted or not). Groups of one kind whose consecutive members are < merge_ms apart."""
    groups, last = [], {}
    for q in sorted(reqs, key=lambda q: (q['t_ms'], q['kind'])):
        g = last.get(q['kind'])
        if g is not None and q['t_ms'] - g['t_ms_last'] < merge_ms:
            g['t_ms_last'] = q['t_ms']
            g['n'] += 1
            g['n_code'] += int(q.get('code', False))
        else:
            g = dict(kind=q['kind'], t_ms_first=q['t_ms'], t_ms_last=q['t_ms'], n=1, n_code=int(q.get('code', False)))
            groups.append(g)
            last[q['kind']] = g
    return sorted(groups, key=lambda g: (g['t_ms_first'], g['kind']))


# the rule reproduces Fig. 4C's tick groups on Fig. 4C's own requests
f4_within = [q for q in F4C['requests'] if q['t_ms'] <= F4C['axis_ms']]
f4_again = [{k: g[k] for k in ('kind', 't_ms_first', 't_ms_last', 'n')} for g in tick_groups(f4_within)]
assert f4_again == F4C['tick_groups'], 'S9D tick grouping no longer reproduces fig4c_recheck.tick_groups'

cr = pd.read_csv(os.path.join(OUT, 'fig6b_store_c.csv'))
LOADS9 = ('A0', 'A0r', 'A1', 'A2', 'A2r')
tg = dict(merge_ms=MERGE_MS, loads={})
n_multi = 0
for arm in LOADS9:
    d = cr[cr.arm == arm]
    tg['loads'][arm] = {}
    for sub, sbx in (('sandbox', True), ('other', False)):
        dd = d[d.sandbox == sbx]
        reqs = [dict(t_ms=int(r.t_ms), kind=f"{r.vgroup}|{'short' if r.kind == 'library' else 'tall'}",
                     code=bool(r.has_creator_token)) for r in dd.itertuples()]
        gs = tick_groups(reqs)
        for g in gs:
            g['vgroup'], g['mark'] = g.pop('kind').split('|')
        assert sum(g['n'] for g in gs) == len(dd)
        by_kind = {}
        for g in gs:                           # groups of one kind are at least the window apart (no ambiguous badge)
            k = (g['vgroup'], g['mark'])
            if k in by_kind:
                assert g['t_ms_first'] - by_kind[k]['t_ms_last'] >= MERGE_MS
            by_kind[k] = g
        tg['loads'][arm][sub] = gs
        n_multi += sum(g['n'] > 1 for g in gs)
    # TikTok's sandboxed requests that carried the code: the per-load count shown in Fig. 6A row 1
    tik = sum(g['n_code'] for g in tg['loads'][arm]['sandbox'] if g['vgroup'] == 'TikTok')
    assert tik == S['fig6']['b']['store_c'][arm]['n_creator_token_tiktok_sbx'], arm
tg['n_groups_multi'] = n_multi
tg['max_span_ms'] = max(g['t_ms_last'] - g['t_ms_first'] for a in LOADS9 for s in ('sandbox', 'other') for g in tg['loads'][a][s])
tk = [g for g in tg['loads']['A0']['sandbox'] if g['vgroup'] == 'TikTok' and g['mark'] == 'tall']
assert len(tk) == 1 and tk[0]['n'] == tk[0]['n_code'] == S['fig6']['b']['store_c']['A0']['n_creator_token_tiktok_sbx']
tg['example'] = dict(load='A0', sub='sandbox', vgroup='TikTok', n=tk[0]['n'])
rec('s9d_tick_groups', tg,
    'Fig. S9D: the requests of each Store C load, per sub-row (sandbox / other), grouped into drawn ticks by the Fig. 4C '
    'rule: requests of one kind (one vendor group and one tick height: tall = data beacons and other requests, short = '
    'library loads) whose consecutive members are less than merge_ms apart form one tick, labelled with its count n when '
    'n > 1. n_code: members that carried the per-video code. example: the TikTok tick of the Default load (sandbox).',
    ['analysis/outputs/fig6b_store_c.csv', 'figures/v7/fig4/derived_numbers.json:fig4c_recheck.tick_merge_ms',
     'stats.json:fig6.b.store_c'],
    "reproduces fig4c_recheck.tick_groups on Fig. 4C's requests; n sums to the requests per load and sub-row; TikTok's "
    'sandboxed code-carrying requests equal fig6.b.store_c.<load>.n_creator_token_tiktok_sbx')

# ---------- S9B bottom: share of still-sending stores whose every remaining sandboxed request carried a refusal ----------
# (cross-figure QA 2, label rule 1: the row label 'p% · k of n stores' needs a registered p; stats.json holds k and n only)
rs = {}
for k in ('resid_decline_fresh', 'resid_gpc'):
    f = S['fig5']['flags'][k]
    rs[k] = dict(k=int(f['stores_all_flagged']), n=int(f['stores']), p=f['stores_all_flagged'] / f['stores'])
rec('s9b_refusal_store_share', rs,
    "Fig. S9B (bottom): among the stores that still sent a sandboxed ad request (Decline: fresh page; GPC: whole load), "
    "the share on which every remaining sandboxed request carried a refusal signal: p = k / n.",
    ['stats.json:fig5.flags.resid_decline_fresh', 'stats.json:fig5.flags.resid_gpc'],
    'k and n equal fig5.flags.<row>.stores_all_flagged and .stores')

# ---------- S10 caption: the date of the Round 4 beyond-Shopify crawl (all loads on one UTC day, and the same day in
# California, the vantage point: UTC-7 in September) ----------
import datetime as _dt
cb = S['round4']['crawl']['beyond']
t0, t1 = (_dt.datetime.fromisoformat(cb[k].replace('Z', '+00:00')) for k in ('first_load_utc', 'last_load_utc'))
assert t0.date() == t1.date() == (t0 - _dt.timedelta(hours=7)).date() == (t1 - _dt.timedelta(hours=7)).date()
rec('s10_crawl_date', t0.strftime('%-d %b %Y'),
    'Fig. S10 caption: the day of the beyond-Shopify pilot crawl, rendered as day, month abbreviation and year; the first '
    'and last load fall on this day in UTC and in California (PDT, UTC-7).',
    ['stats.json:round4.crawl.beyond.first_load_utc', 'stats.json:round4.crawl.beyond.last_load_utc'],
    'first and last load on the same date in UTC and in UTC-7')

with open(DST, 'w') as f:
    json.dump(D, f, indent=1, default=int)
print(json.dumps({k: v['value'] for k, v in D.items()}, indent=1, default=int))
