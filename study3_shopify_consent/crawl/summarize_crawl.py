"""Headline raw (unweighted) rates from the crawl tables. Writes crawl_summary.json and prints it.
All rates are store-level shares with Wilson 95% intervals. Main sample only unless noted;
the creator stratum is reported separately. Unweighted = no Tranco-bucket weights applied here.
Usage: python summarize_crawl.py [--dir DIR] [--exclude CSV --out NAME]
  --exclude CSV  drop the stores listed in CSV (column store_id; rows whose status starts 'excluded from all analyses')
                 before summarising, and write NAME instead of crawl_summary.json. The analysis uses
                 --exclude ../analysis/ethics_flags.csv --out crawl_summary_analysed.json for its cross-check of the
                 analysed stores (content-sensitivity exclusions, 2026-09-29); crawl_summary.json stays the whole crawl.
"""
import json, math, os, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
D = sys.argv[sys.argv.index('--dir') + 1] if '--dir' in sys.argv else HERE
SANDBOX = {'strict_worker', 'lax_iframe'}
EXCL = sys.argv[sys.argv.index('--exclude') + 1] if '--exclude' in sys.argv else None
OUTNAME = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else 'crawl_summary.json'


def wilson(k, n, z=1.96):
    if n == 0:
        return dict(k=int(k), n=int(n), p=None, lo=None, hi=None)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return dict(k=int(k), n=int(n), p=round(p, 4), lo=round(c - h, 4), hi=round(c + h, 4))


def main():
    L = pd.read_csv(os.path.join(D, 'loads.csv'), low_memory=False)
    R = pd.read_csv(os.path.join(D, 'requests.csv.gz'), low_memory=False)
    out = {}
    if EXCL:
        fl = pd.read_csv(EXCL)
        ex = set(fl[fl.status.str.startswith('excluded from all analyses')].store_id)
        L = L[~L.store_id.isin(ex)]
        R = R[R.load_id.isin(L.load_id)]
        out['excluded_stores'] = sorted(ex)
    L['ok'] = (L.goto_status.fillna(0).between(200, 399)) & (L.has_shopify == True) & (L.blocked_hint != True) & (L.n_requests.fillna(0) > 20)
    out['loads'] = {a: dict(n=int((L.arm == a).sum()), ok=int(((L.arm == a) & L.ok).sum())) for a in sorted(L.arm.unique())}
    base = ['A0', 'A1', 'A2']
    okset = L[L.ok].groupby('store_id').arm.apply(set)
    captured = [s for s, arms in okset.items() if set(base) <= arms]
    strat = L.drop_duplicates('store_id').set_index('store_id').stratum
    out['stores_planned'] = int(L.store_id.nunique())
    out['stores_captured_all_base_arms'] = dict(main=sum(1 for s in captured if strat.get(s) == 'main'), creator=sum(1 for s in captured if strat.get(s) == 'creator'))
    out['blocked_or_failed_loads'] = int((~L.ok).sum())
    out['blocked_hint_loads'] = int((L.blocked_hint == True).sum())
    ad = R[R.is_advertising == True].copy()
    ad['sandbox'] = ad.origin.isin(SANDBOX)
    by = ad.groupby('load_id').agg(n_ad=('i', 'size'), n_sbx=('sandbox', 'sum'))
    def load_counts(load_ids, phase=None):
        a = ad[ad.load_id.isin(load_ids)]
        if phase is not None:
            a = a[a.phase.isin(phase)]
        g = a.groupby('load_id').agg(n_ad=('i', 'size'), n_sbx=('sandbox', 'sum'))
        return g
    for stratum in ('main', 'creator'):
        o = {}
        A0 = L[(L.arm == 'A0') & L.ok & L.store_id.isin(captured) & (L.stratum == stratum)].set_index('store_id')
        c0 = load_counts(A0.load_id)
        A0 = A0.join(c0, on='load_id').fillna({'n_ad': 0, 'n_sbx': 0})
        ban = A0[A0.banner_visible == True]
        o['A0_n_stores'] = len(A0)
        o['A0_banner_visible'] = wilson((A0.banner_visible == True).sum(), len(A0))
        o['A0_any_ad_request'] = wilson((A0.n_ad > 0).sum(), len(A0))
        o['A0_banner_stores_any_ad_request_prechoice'] = wilson((ban.n_ad > 0).sum(), len(ban))
        o['A0_banner_stores_sandboxed_ad_request_prechoice'] = wilson((ban.n_sbx > 0).sum(), len(ban))
        o['A0_nobanner_stores_sandboxed_ad_request'] = wilson((A0[A0.banner_visible != True].n_sbx > 0).sum(), int((A0.banner_visible != True).sum()))
        for mode, sel in (('optout_M_allowed', ban.cmp_allow_m == True), ('optin_M_denied', ban.cmp_allow_m == False)):
            b = ban[sel]
            o[f'A0_banner_stores_{mode}_sandboxed_ad'] = wilson((b.n_sbx > 0).sum(), len(b))
        # time: first sandboxed ad request vs banner visible
        first = ad[ad.load_id.isin(ban.load_id) & ad.sandbox].groupby('load_id').t_ms.min()
        bt = ban.set_index('load_id').t_banner_visible
        j = pd.concat([first.rename('t_first'), bt.rename('t_banner')], axis=1).dropna()
        o['A0_banner_stores_first_sandboxed_ad_before_banner'] = wilson((j.t_first < j.t_banner).sum(), len(j))
        o['A0_median_ms_first_sandboxed_ad'] = float(j.t_first.median()) if len(j) else None
        o['A0_median_ms_banner_visible'] = float(j.t_banner.median()) if len(j) else None
        # decline
        A1 = L[(L.arm == 'A1') & L.ok & L.store_id.isin(captured) & (L.stratum == stratum)]
        o['A1_banner_found'] = wilson((A1.a1_banner_found == True).sum(), len(A1))
        fb = A1[A1.a1_banner_found == True]
        o['A1_no_decline_option_among_banner'] = wilson((fb.no_decline_option == True).sum(), len(fb))
        clk = fb[fb.click_method.isin(['playwright_click', 'playwright_force', 'js_click'])]
        o['A1_clicked'] = int(len(clk))
        o['A1_cpapi_marketing_denied_after_click'] = wilson((clk.cp_marketing_end == False).sum(), len(clk))
        cpost = load_counts(clk.load_id, ['post_click']).reindex(clk.load_id).fillna(0)
        cnext = load_counts(clk.load_id, ['next_page']).reindex(clk.load_id).fillna(0)
        cpre = load_counts(clk.load_id, ['pre_banner', 'banner_prechoice', 'pre_choice']).reindex(clk.load_id).fillna(0)
        o['A1_clicked_sandboxed_ad_before_click'] = wilson((cpre.n_sbx > 0).sum(), len(clk))
        o['A1_clicked_sandboxed_ad_after_click_same_page'] = wilson((cpost.n_sbx > 0).sum(), len(clk))
        o['A1_clicked_sandboxed_ad_next_page'] = wilson((cnext.n_sbx > 0).sum(), len(clk))
        o['A1_clicked_any_ad_next_page'] = wilson((cnext.n_ad > 0).sum(), len(clk))
        pre_s = set(cpre[cpre.n_sbx > 0].index)
        sub = [l for l in clk.load_id if l in pre_s]
        o['A1_next_page_sandboxed_ad_given_prechoice_sandboxed'] = wilson(sum(1 for l in sub if cnext.loc[l].n_sbx > 0), len(sub))
        # GPC
        A2 = L[(L.arm == 'A2') & L.ok & L.store_id.isin(captured) & (L.stratum == stratum)].set_index('store_id')
        c2 = load_counts(A2.load_id)
        A2 = A2.join(c2, on='load_id').fillna({'n_ad': 0, 'n_sbx': 0})
        both = A0.join(A2[['n_ad', 'n_sbx', 'cp_sale_end', 'cmp_header_raw']], rsuffix='_gpc', how='inner')
        s0 = both[both.n_sbx > 0]
        o['A2_shopify_saleOfData_denied'] = wilson((A2.cp_sale_end == False).sum(), int(A2.cp_sale_end.notna().sum()))
        o['A2_given_A0_sandboxed_ad_still_sandboxed_ad'] = wilson((s0.n_sbx_gpc > 0).sum(), len(s0))
        o['A2_given_A0_any_ad_still_any_ad'] = wilson((both[both.n_ad > 0].n_ad_gpc > 0).sum(), int((both.n_ad > 0).sum()))
        o['A2_median_ratio_ad_requests_gpc_over_default'] = float((s0.n_ad_gpc / s0.n_ad).median()) if len(s0) else None
        out[stratum] = o
    # vendor-level GPC for pixels declaring SALE_OF_DATA (TikTok/Pinterest/Snap strict workers)
    m = L[L.ok & L.store_id.isin(captured) & (L.stratum == 'main')]
    for v in ('tiktok', 'pinterest', 'snap', 'meta', 'google_ads', 'klaviyo'):
        a0 = set(ad[(ad.vendor == v) & ad.load_id.isin(m[m.arm == 'A0'].load_id)].store_id)
        a2 = set(ad[(ad.vendor == v) & ad.load_id.isin(m[m.arm == 'A2'].load_id)].store_id)
        out.setdefault('vendor_gpc_main', {})[v] = dict(stores_fired_A0=len(a0), of_which_fired_A2=wilson(len(a0 & a2), len(a0)))
    # repeat agreement (any sandboxed ad request, same arm)
    rep = {}
    for a, b in (('A0', 'A0r'), ('A2', 'A2r')):
        x = L[(L.arm == a) & L.ok].set_index('store_id').load_id
        y = L[(L.arm == b) & L.ok].set_index('store_id').load_id
        ids = x.index.intersection(y.index)
        fx = set(ad[ad.load_id.isin(x[ids]) & ad.sandbox].store_id)
        fy = set(ad[ad.load_id.isin(y[ids]) & ad.sandbox].store_id)
        agree = sum(1 for s in ids if (s in fx) == (s in fy))
        rep[f'{a}_vs_{b}'] = dict(pairs=len(ids), agree=wilson(agree, len(ids)))
    out['repeat_agreement_sandboxed_ad'] = rep
    # Brave native GPC vs emulated GPC
    x = L[(L.arm == 'A2') & L.ok].set_index('store_id').load_id
    y = L[(L.arm == 'V1') & L.ok].set_index('store_id').load_id
    ids = x.index.intersection(y.index)
    fx = set(ad[ad.load_id.isin(x[ids]) & ad.sandbox].store_id)
    fy = set(ad[ad.load_id.isin(y[ids]) & ad.sandbox].store_id)
    out['v1_brave_vs_a2_sandboxed_ad'] = dict(pairs=len(ids), agree=wilson(sum(1 for s in ids if (s in fx) == (s in fy)), len(ids)), fired_a2=len(fx), fired_v1=len(fy))
    V1 = L[(L.arm == 'V1') & L.ok]
    out['v1_shopify_saleOfData_denied'] = wilson((V1.cp_sale_end == False).sum(), int(V1.cp_sale_end.notna().sum()))
    # canary reach
    adm = ad[ad.load_id.isin(L[L.ok & (L.stratum == 'main')].load_id)]
    out['ad_requests_main'] = int(len(adm))
    out['ad_beacons_with_canary_main'] = wilson(((adm.kind != 'library') & adm.has_canary).sum(), int((adm.kind != 'library').sum()))
    out['ad_beacons_with_full_url_main'] = wilson(((adm.kind != 'library') & adm.has_full_url).sum(), int((adm.kind != 'library').sum()))
    out['origin_share_of_ad_requests_main'] = {k: int(v) for k, v in adm.origin.value_counts().items()}
    json.dump(out, open(os.path.join(D, OUTNAME), 'w'), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
