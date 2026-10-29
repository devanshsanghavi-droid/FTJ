"""Analysis of the final-audit re-check crawl (crawl/recheck, 2026-09-26). Writes recheck_summary.json,
recall_by_store.csv and blocker_by_entry.csv.

(1) Banner-detector recall. Screenshot labels are in sheets/labels_assistant.csv. They were made BLIND (codes only, no
    group, CMP or detector result) but by the AI assistant, not by a person; human re-labelling is pending.
(2) Blocker activity on the 21 blocklist stores: which <script>/<iframe> elements the page neutralized (type set to
    javascript/blocked, text/plain or osano/blocked, on insertion or by a later change), whether a tag of each
    declared-blocked ad vendor was installed in the main document and neutralized, and whether that vendor's pixel sent
    requests from Shopify's sandbox or from the main thread in the same load.
"""
import csv, gzip, json, math, os, re
import pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
ST = os.path.join(H, '..', '..')
BLOCKED = {'javascript/blocked', 'text/plain', 'osano/blocked'}
SANDBOX = {'strict_worker', 'lax_iframe'}
INLINE_SIG = {'tiktok': r'\bttq\b|analytics\.tiktok', 'meta': r'\bfbq\b|connect\.facebook', 'pinterest': r'\bpintrk\b|pinimg',
              'snap': r'\bsnaptr\b|sc-static', 'microsoft_uet': r'\buetq\b|bat\.bing', 'google_ads': r'AW-\d|googleads',
              'reddit': r'\brdt\(|redditstatic', 'x_twitter': r'\btwq\b|static\.ads-twitter', 'linkedin': r'_linkedin_partner_id|snap\.licdn',
              'amazon_ads': r'amazon-adsystem', 'criteo': r'criteo', 'adroll': r'adroll', 'outbrain': r'obApi|outbrain', 'applovin': r'applovin'}


def wilson(k, n, z=1.959964):
    if n == 0:
        return dict(k=k, n=n, p=None, lo=None, hi=None)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return dict(k=int(k), n=int(n), p=p, lo=max(0.0, c - h), hi=min(1.0, c + h))


lst = pd.read_csv(os.path.join(H, 'recheck_list.csv'))
key = {r['code']: r['store_id'] for r in csv.DictReader(open(os.path.join(H, 'sheets', 'blind_key.csv')))}
lab = pd.read_csv(os.path.join(H, 'sheets', 'labels_assistant.csv'))
lab['store_id'] = lab.code.map(key)
st = pd.read_csv(os.path.join(ST, 'analysis', 'outputs', 'store_table.csv')).set_index('store_id')
R = {s: json.load(gzip.open(os.path.join(H, 'raw', f'{s}__R0.json.gz'))) for s in lst.store_id}
out = {'date': '2026-09-26', 'loads': len(R), 'stores': int(lst.store_id.nunique()),
       'loads_ok': int(sum(1 for r in R.values() if (r.get('goto_status') or 0) in range(200, 400) and not r.get('fatal_error'))),
       'first_load': min(r['started_at'] for r in R.values()), 'last_load': max(r['started_at'] for r in R.values())}

# ---------------- (1) recall
rows = []
for s, r in R.items():
    det = any(isinstance(c.get('banner'), dict) and (c['banner'] or {}).get('banner') for c in r['checkpoints']) or \
        bool(((r.get('probe') or {}).get('cs3') or {}).get('banner')) if isinstance(r.get('probe'), dict) else False
    rows.append(dict(store_id=s, det_recheck=bool(det), ssb_recheck=any(c.get('shouldShowBanner') is True for c in r['consent']),
                     shot_times=[c.get('since_load_ms') for c in r['checkpoints']]))
D = pd.DataFrame(rows).merge(lab[['store_id', 'code', 'consent_banner_visible', 'note']], on='store_id').merge(lst[['store_id', 'groups']], on='store_id')
D = D.join(st[['cmp', 'banner_A0', 'banner_A1', 'A0_sbx']], on='store_id')
D['shot'] = D.consent_banner_visible.isin(['yes', 'no'])
D['vis'] = D.consent_banner_visible == 'yes'
D.drop(columns=['shot_times']).to_csv(os.path.join(H, 'recall_by_store.csv'), index=False)
g = {}
for grp in ('flagged', 'random_nb', 'blocklist'):
    x = D[D.groups.str.contains(grp) & D.shot]
    g[grp] = dict(n_stores=int(D.groups.str.contains(grp).sum()), with_screenshots=len(x), banner_visible=int(x.vis.sum()),
                  banner_visible_detected_recheck=int((x.vis & x.det_recheck).sum()), detector_false_positive=int((~x.vis & x.det_recheck).sum()),
                  main_crawl_banner_A0=int(x.banner_A0.sum()))
fl = D[D.groups.str.contains('flagged') & D.shot]
g['flagged']['consentmo'] = dict(n=int((fl.cmp == 'consentmo').sum()), banner_visible=int((fl.vis & (fl.cmp == 'consentmo')).sum()))
g['flagged']['by_cmp_visible'] = fl[fl.vis].cmp.value_counts().to_dict()
g['flagged']['no_screenshot'] = sorted(D[D.groups.str.contains('flagged') & ~D.shot].store_id)
cls = []
for s in D[D.vis & ~D.det_recheck].store_id:
    c = (R[s]['checkpoints'][-1].get('cand') or {}).get('fixed') or []
    cls += [x['cls'] for x in c if re.search(r'cookie|consent|privacy', (x.get('text') or '') + x['cls'], re.I)][:1]
g['missed_banner_container_classes'] = cls
g['missed_on_recheck'] = int((D.vis & ~D.det_recheck).sum())
g['missed_on_recheck_dg_consent_banner'] = sum('dg-consent-banner' in c for c in cls)
all_shot = D[D.shot]
out['recall'] = g
out['recall']['detector_on_recheck'] = dict(precision=wilson(int((all_shot.vis & all_shot.det_recheck).sum()), int(all_shot.det_recheck.sum())),
                                           recall_on_this_set=wilson(int((all_shot.vis & all_shot.det_recheck).sum()), int(all_shot.vis.sum())))
# main-crawl banner stores and missed banners among the 952 stores without a detected A0 banner
m = st[st.stratum == 'main']
n_banner = int(m.banner_A0.sum()); nb = m[~m.banner_A0]
pool_random = int((~m.banner_A0 & ~m.banner_A1).sum()) - g['flagged']['n_stores'] + int((D.groups.str.contains('flagged') & D.banner_A1.fillna(False)).sum())
rn = wilson(g['random_nb']['banner_visible'], g['random_nb']['with_screenshots'])
pool = int(len(nb)) - g['flagged']['n_stores']  # no-banner stores outside the flagged group (random_nb was drawn from those also without an A1 banner)
missed_obs = g['flagged']['banner_visible'] + g['random_nb']['banner_visible']
est_missed = g['flagged']['banner_visible'] + rn['p'] * pool
est_lo = g['flagged']['banner_visible'] + rn['lo'] * pool
est_hi = g['flagged']['banner_visible'] + rn['hi'] * pool
out['recall']['main_crawl'] = dict(banner_A0=n_banner, no_banner_A0=int(len(nb)), pool_outside_flagged=pool, random_rate=rn,
                                    missed_observed=missed_obs, est_missed=est_missed, est_missed_lo=est_lo, est_missed_hi=est_hi,
                                    est_recall=n_banner / (n_banner + est_missed), est_recall_lo=n_banner / (n_banner + est_hi), est_recall_hi=n_banner / (n_banner + est_lo),
                                    note='assumes a banner seen on the re-check load was also shown in the A0 load; the random rate is applied to all no-banner stores outside the flagged group')
missed_ids = sorted(D[D.vis & ~D.banner_A0.astype(bool) & D.groups.str.contains('flagged|random_nb')].store_id)
out['recall']['missed_banner_stores'] = missed_ids
pd.DataFrame(dict(store_id=missed_ids)).to_csv(os.path.join(H, 'missed_banner_stores.csv'), index=False)
# how the missed-banner stores behaved before any choice in the main crawl
x = m.loc[missed_ids]
out['recall']['missed_banner_stores_A0_sbx'] = wilson(int(x.A0_sbx.sum()), len(x))
out['recall']['missed_banner_stores_region_optout'] = int((x.region_optout == True).sum())
bm = m[m.banner_A0 | m.index.isin(missed_ids)]; nbm = m[~(m.banner_A0 | m.index.isin(missed_ids))]
out['recall']['sens_banner_rate_with_missed'] = dict(banner=wilson(int(bm.A0_sbx.sum()), len(bm)), no_banner=wilson(int(nbm.A0_sbx.sum()), len(nbm)))

# ---------------- (2) blocker activity on the 21 blocklist stores
db = pd.read_csv(os.path.join(ST, 'analysis', 'outputs', 'fig4c_declared_blocked_pairs.csv'))
main_fire = pd.read_csv(os.path.join(ST, 'analysis', 'outputs', 'fig4a.csv'))
S0 = json.load(open(os.path.join(ST, 'analysis', 'outputs', 'stats.json')))
ent, srows = [], []
for s, gdf in db.groupby('store_id'):
    r = R.get(s)
    if r is None:
        continue
    sl = r.get('scriptlog') or {}
    els = [dict(x, how='added') for x in sl.get('added', [])] + [dict(x, how='snapshot') for x in (r.get('script_snapshot') or [])]
    neutral = [x for x in sl.get('added', []) if (x.get('type') or '').strip() in BLOCKED] + \
              [x for x in sl.get('changed', []) if x['attr'] == 'type' and x['now'] in BLOCKED]
    rq = [q for q in (r.get('requests') or []) if q.get('vendor') and q.get('ad')]
    for v in sorted(set(gdf.vendor)):
        tag = [x for x in els if x.get('vendor') == v or (x.get('inline') and re.search(INLINE_SIG.get(v, r'$^'), x['inline'] or ''))]
        neu = [x for x in neutral if x.get('vendor') == v or (x.get('inline') and re.search(INLINE_SIG.get(v, r'$^'), x.get('inline') or ''))]
        sbx = [q for q in rq if q['vendor'] == v and q.get('origin') in SANDBOX]
        mt = [q for q in rq if q['vendor'] == v and q.get('origin') not in SANDBOX]
        row = gdf[gdf.vendor == v].iloc[0]
        ent.append(dict(store_id=s, cmp=row.cmp, vendor=v, cfg_sandboxed=bool(row.cfg_sandboxed), main_crawl_outcome=row.outcome,
                        main_tag_seen=bool(tag), main_tag_neutralized=bool(neu), fired_sandbox=bool(sbx), fired_main=bool(mt)))
    E = pd.DataFrame([e for e in ent if e['store_id'] == s])
    srows.append(dict(store_id=s, cmp=gdf.cmp.iloc[0], ok=(r.get('goto_status') or 0) in range(200, 400), n_neutralized=len(neutral),
                      n_neutralized_ad=sum(1 for x in neutral if x.get('ad')), blocker_active=len(neutral) > 0,
                      declared_fired_sbx_main_crawl=bool((E.main_crawl_outcome == 'sandbox').any()),
                      declared_fired_sbx_recheck=bool(E.fired_sandbox.any()), declared_neutralized=bool(E.main_tag_neutralized.any()),
                      neutralized_and_sbx=bool((E.main_tag_neutralized & E.fired_sandbox).any()),
                      cmp_yes_event=any('"marketingAllowed":true' in (e.get('d') or '') for e in (((r.get('probe') or {}).get('cs3') or {}).get('ev') or []))))
E = pd.DataFrame(ent); SR = pd.DataFrame(srows)
E.to_csv(os.path.join(H, 'blocker_by_entry.csv'), index=False); SR.to_csv(os.path.join(H, 'blocker_by_store.csv'), index=False)
auto = S0['fig4']['a']['blocklist'].get('sens_excl_auto_grant', {}).get('stores_excluded', [])
fired12 = SR[SR.declared_fired_sbx_main_crawl]
out['blocker'] = dict(stores=len(SR), loads_ok=int(SR.ok.sum()), blocker_active=int(SR.blocker_active.sum()),
                      blocker_active_by_cmp={c: f'{int(x.blocker_active.sum())}/{len(x)}' for c, x in SR.groupby('cmp')},
                      stores_fired_main_crawl=len(fired12), fired_main_crawl_blocker_active=int(fired12.blocker_active.sum()),
                      fired_main_crawl_fired_again_sbx=int(fired12.declared_fired_sbx_recheck.sum()),
                      stores_declared_tag_neutralized=int(SR.declared_neutralized.sum()),
                      stores_neutralized_and_sbx=int(SR.neutralized_and_sbx.sum()), stores_neutralized_and_sbx_ids=sorted(SR[SR.neutralized_and_sbx].store_id),
                      entries=len(E), entries_tag_seen=int(E.main_tag_seen.sum()), entries_neutralized=int(E.main_tag_neutralized.sum()),
                      entries_neutralized_fired_main=int((E.main_tag_neutralized & E.fired_main).sum()),
                      entries_neutralized_fired_sbx=int((E.main_tag_neutralized & E.fired_sandbox).sum()),
                      entries_cfg_sandboxed=int(E.cfg_sandboxed.sum()), entries_cfg_sandboxed_fired_sbx=int((E.cfg_sandboxed & E.fired_sandbox).sum()),
                      entries_cfg_sandboxed_neutralized=int((E.cfg_sandboxed & E.main_tag_neutralized).sum()),
                      entries_not_cfg_fired_any=int((~E.cfg_sandboxed & (E.fired_main | E.fired_sandbox)).sum()), entries_not_cfg=int((~E.cfg_sandboxed).sum()),
                      entries_not_cfg_tag_seen=int((~E.cfg_sandboxed & E.main_tag_seen).sum()),
                      blocker_active_excl_auto_grant=int(SR[~SR.store_id.isin(auto)].blocker_active.sum()), n_excl_auto_grant=int((~SR.store_id.isin(auto)).sum()),
                      stores_neutralized_and_sbx_excl_auto_grant=int(SR[~SR.store_id.isin(auto)].neutralized_and_sbx.sum()),
                      fired_main_crawl_excl_auto_grant_blocker_active=int(fired12[~fired12.store_id.isin(auto)].blocker_active.sum()),
                      fired_main_crawl_excl_auto_grant=int((~fired12.store_id.isin(auto)).sum()))
json.dump(out, open(os.path.join(H, 'recheck_summary.json'), 'w'), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
