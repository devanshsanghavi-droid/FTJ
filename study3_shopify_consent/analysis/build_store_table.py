"""Build the store-level analysis tables from the crawl tables.

Outputs (analysis/outputs/):
  store_table.csv    one row per captured store (main + creator): design, CMP, region mode, arm outcomes
  store_vendor.csv   one row per captured store x vendor group: sandboxed / any-origin ad requests by condition
  ad_requests.parquet-like CSV (ad_requests.csv.gz): ad requests of ok loads of captured stores, with store join
Conditions
  A0        Default load, whole observation window (all before any choice)
  A1pre     Decline load, before the click (clicked loads) ; A1post same page after the click ; A1next next page
  A2        GPC (emulated) load, whole window
  A0r/A2r/V1 repeat and Brave native-GPC loads
Revision after review (2026-09-26):
  * ad requests carry oclass (sandbox / relay / open_pixel / page): 'relay' only when the initiator stack holds nothing
    but Shopify or store scripts (outputs/raw_stacks.csv from extract_raw.py);
  * ad requests carry the refusal signals in their URL (gcs, flag_refusal, flag_kind; common.consent_flags);
  * Decline loads get an explicit-refusal measure (currentVisitorConsent.marketing or trackingConsent == 'no' in any
    reading after the click), a refusal category and click success (banner dismissed, or an explicit 'no' recorded);
  * equal-window flags: sandboxed ad request within 10 s of the load event (A0_sbx_10s, A2_sbx_10s), the same span
    the Decline arm's next page is observed for;
  * beacon-only and canary-beacon flags for the sensitivity rows.
"""
import os
import sys

import numpy as np
import pandas as pd

from common import (CRAWL, OUT, PRECHOICE_PHASES, VENDOR_GROUPS, consent_flags, load_sample, load_tables, origin_class,
                    primary_cmp)
import json
import warnings
warnings.simplefilter("ignore", pd.errors.PerformanceWarning)

CLICK_METHODS = ['playwright_click', 'playwright_force', 'js_click']
RESTART_UTC = '2026-09-26T07:34'   # coordinator restart (logs/COORDINATOR_NOTE.txt: 00:35:57 PDT)
RETRY_UTC = '2026-09-26T09:59'


def segment(t):
    t = str(t)
    return 'conc6' if t < RESTART_UTC else ('conc10' if t < RETRY_UTC else 'conc6_retry')


def has_purpose(pp, purpose):
    return isinstance(pp, str) and purpose in pp.split('|')


def main():
    L, R, captured = load_tables()
    S, Cs = load_sample()
    sig = json.load(open(os.path.join(CRAWL, 'cmp_signatures.json')))
    mode_of = {k: c.get('integration_mode') for k, c in sig['cmps'].items()}
    ok = L[L.ok & L.captured].copy()
    ok['pcmp'] = primary_cmp(ok)
    ok['segment'] = ok.started_at.map(segment)

    # ---------------- ad requests of ok loads of captured stores ----------------
    ad = R[R.ad & R.load_id.isin(ok.load_id)].copy()
    ad['vgroup'] = ad.vgroup.replace('', 'Reddit/other')
    ad.loc[~ad.vgroup.isin(VENDOR_GROUPS), 'vgroup'] = 'Reddit/other'
    ad['decl_sale'] = ad.pixel_purposes.map(lambda x: has_purpose(x, 'SALE_OF_DATA'))
    ad['decl_mkt'] = ad.pixel_purposes.map(lambda x: has_purpose(x, 'MARKETING'))
    ad['no_purpose'] = ad.pixel_purposes == 'NONE'
    stk = pd.read_csv(os.path.join(OUT, 'raw_stacks.csv'))[['load_id', 'i', 'stack_class']]
    ad = ad.merge(stk, on=['load_id', 'i'], how='left')
    ad['oclass'] = [origin_class(o, k) for o, k in zip(ad.origin, ad.stack_class)]
    fl = [consent_flags(u, v) for u, v in zip(ad.url, ad.vendor)]
    ad['gcs'] = [f[0] for f in fl]
    ad['flag_refusal'] = [f[1] for f in fl]
    ad['flag_kind'] = [f[2] for f in fl]
    ad['cond'] = ad.arm
    ad.loc[(ad.arm == 'A1') & ad.phase.isin(PRECHOICE_PHASES), 'cond'] = 'A1pre'
    ad.loc[(ad.arm == 'A1') & (ad.phase == 'post_click'), 'cond'] = 'A1post'
    ad.loc[(ad.arm == 'A1') & (ad.phase == 'next_page'), 'cond'] = 'A1next'
    ad.to_csv(os.path.join(OUT, 'ad_requests.csv.gz'), index=False, compression={'method': 'gzip', 'mtime': 0})  # mtime 0: same bytes on every run
    # referee revision (2026-09-26): what the two attribution corrections changed, per arm (main sample)
    Rk = R[R.load_id.isin(ok.load_id) & (R.is_advertising == True) & (R.stratum == 'main')]
    Nn = pd.read_csv(os.path.join(OUT, 'nested_lax_frames.csv'))
    amb = set(zip(Nn[Nn.ambiguous].load_id, Nn[Nn.ambiguous].frame_url))
    att = {}
    for arm, g in Rk.groupby('arm'):
        pf = g[g.preflight]
        old_sbx = g.origin_crawl.isin(['strict_worker', 'lax_iframe'])
        att[arm] = dict(ad_requests_crawl=int(len(g)), preflights=int(len(pf)), preflights_by_origin={k: int(v) for k, v in pf.origin_crawl.value_counts().items()},
                        preflights_by_group={k: int(v) for k, v in pf.color_group.fillna('Reddit/other').value_counts().items()},
                        nested=int((g.origin == 'lax_nested').sum()), nested_stores=int(g[g.origin == 'lax_nested'].store_id.nunique()),
                        nested_by_group={k: int(v) for k, v in g[g.origin == 'lax_nested'].color_group.fillna('Reddit/other').value_counts().items()},
                        ambiguous_kept_subframe=int(sum((l_, u_) in amb for l_, u_, o_ in zip(g.load_id, g.frame_url, g.origin) if o_ == 'subframe')),
                        sandboxed_crawl_labels=int(old_sbx.sum()), sandboxed_now=int((g.sandbox & ~g.preflight).sum()), ad_requests_now=int((~g.preflight).sum()))
    json.dump(att, open(os.path.join(OUT, 'attribution_changes.json'), 'w'), indent=1)

    # ---------------- store table ----------------
    base = ok[ok.arm.isin(['A0', 'A1', 'A2'])]
    a0 = base[base.arm == 'A0'].set_index('store_id')
    a1 = base[base.arm == 'A1'].set_index('store_id')
    a2 = base[base.arm == 'A2'].set_index('store_id')
    st = pd.DataFrame(index=sorted(set(a0.index)))
    st.index.name = 'store_id'
    st['stratum'] = a0.stratum
    st['domain'] = a0.domain
    smap = S.set_index('store_id')
    st['bucket'] = smap.bucket.reindex(st.index)
    st['weight'] = smap.weight.reindex(st.index)
    st['tranco_rank'] = smap.tranco_rank.reindex(st.index)
    # region mode from the Default navigation's Server-Timing _cmp (M allowed = opt-out)
    st['region_optout'] = a0.cmp_allow_m
    st['cmp_region'] = a0.cmp_region
    st['cmp_header_A0'] = a0.cmp_header_raw
    st['nostra'] = a0.nostra
    st['cf_cache_A0'] = a0.cf_cache_status
    st['segment_A0'] = a0.segment
    st['segment_A1'] = a1.segment
    st['segment_A2'] = a2.segment
    st['n_pixels'] = a0.n_pixels
    st['n_strict'] = a0.n_strict
    st['n_lax'] = a0.n_lax
    st['n_open'] = a0.n_open
    st['cmps_detected'] = a0.cmps_detected
    # banner and primary CMP: prefer the CMP that showed the banner (A1, else A0), else detection
    st['banner_A0'] = a0.banner_visible == True
    st['t_banner_A0'] = a0.t_banner_visible
    st['banner_A1'] = a1.a1_banner_found == True
    pc = a1.pcmp.where(a1.a1_banner_found == True)
    pc = pc.fillna(a0.pcmp.where(a0.banner_visible == True))
    pc = pc.fillna(a0.pcmp)
    st['cmp'] = pc.reindex(st.index).fillna('none')
    st['cmp_mode'] = st.cmp.map(lambda c: mode_of.get(c, 'none' if c in ('none',) else 'X'))
    st.loc[st.cmp.isin(['multiple', 'generic']), 'cmp_mode'] = 'X'
    # Decline arm
    st['no_decline_option'] = a1.no_decline_option == True
    st['clicked'] = a1.click_method.isin(CLICK_METHODS) & (a1.a1_banner_found == True)
    st['click_method'] = a1.click_method
    st['t_click'] = a1.t_click
    st['banner_still_after_click'] = a1.banner_still_after_click
    st['cp_marketing_end_A1'] = a1.cp_marketing_end
    # legacy flag, kept for comparison: marketingAllowed() false at the end of the Decline load (true by default on
    # 'denied until consent' stores, so it does not show that the Decline was written to Shopify)
    st['decline_reached_shopify'] = np.where(st.clicked, a1.cp_marketing_end.reindex(st.index) == False, np.nan)
    st['marketing_denied_end_A1'] = st.decline_reached_shopify
    # explicit refusal: any Customer Privacy API reading after the click with currentVisitorConsent.marketing == 'no'
    # or trackingConsent == 'no' (first page after the click, or the next page)
    CS = pd.read_csv(os.path.join(CRAWL, 'consent_states.csv'), low_memory=False)
    CS = CS[(CS.arm == 'A1') & CS.load_id.isin(a1.load_id) & (CS.has_cp == True) & CS.error.isna()].copy()

    def _mk(x):
        try:
            return json.loads(x).get('marketing')
        except Exception:
            return None
    CS['cvm'] = CS.currentVisitorConsent.map(_mk)
    CS['tc'] = CS.trackingConsent.astype(str).str.strip('"')
    CS = CS.merge(a1.reset_index()[['store_id', 't_click']], on='store_id', how='left')
    after = CS[CS.t_click.notna() & (CS.t_ms >= CS.t_click)]
    no_st = set(after[(after.cvm == 'no') | (after.tc == 'no')].store_id)
    read_st = set(after.store_id)
    st['explicit_refusal'] = np.where(st.clicked, st.index.isin(no_st), np.nan)
    st['n_reads_after_click'] = after.groupby('store_id').size().reindex(st.index).fillna(0).astype(int)

    def _cat(s_):
        if not st.loc[s_, 'clicked']:
            return None
        if s_ in no_st:
            return 'refused'
        me = st.loc[s_, 'cp_marketing_end_A1']
        if me is True or me == True:
            return 'still_allowed'
        if me is False or me == False:
            return 'no_record_default_denied'
        return 'unknown'
    st['refusal_cat'] = [_cat(x) for x in st.index]
    # click success: the banner was gone 2 s after the click, or Shopify recorded an explicit 'no'
    st['click_ok'] = st.clicked & ((st.banner_still_after_click != True) | st.index.isin(no_st))
    st['next_status'] = a1.next_status
    st['next_cmp_header'] = a1.next_cmp_header_raw
    # GPC arm
    st['cp_sale_end_A2'] = a2.cp_sale_end
    st['cp_marketing_end_A2'] = a2.cp_marketing_end
    st['cmp_header_A2'] = a2.cmp_header_raw
    st['A2_header_sale_declined'] = a2.cmp_choice_s == 'declined'
    st['A2_header_S_allowed'] = a2.cmp_allow_s
    st['cp_sale_first_A2'] = a2.cp_sale_first
    st['cp_marketing_end_A0'] = a0.cp_marketing_end
    st['cp_marketing_first_A0'] = a0.cp_marketing_first
    st['cp_sale_end_A0'] = a0.cp_sale_end

    # request-derived outcomes
    def flag(cond, sel=None, name=None):
        a = ad[ad.cond == cond]
        if sel is not None:
            a = a[sel(a)]
        return a.groupby('store_id').size()

    conds = ['A0', 'A1pre', 'A1post', 'A1next', 'A2']
    for c in conds:
        a = ad[ad.cond == c]
        st[f'{c}_n_ad'] = a.groupby('store_id').size().reindex(st.index).fillna(0).astype(int)
        st[f'{c}_n_sbx'] = a[a.sandbox].groupby('store_id').size().reindex(st.index).fillna(0).astype(int)
        st[f'{c}_any'] = st[f'{c}_n_ad'] > 0
        st[f'{c}_sbx'] = st[f'{c}_n_sbx'] > 0
        # sandboxed requests from pixels that declare the purpose the visitor denied
        st[f'{c}_sbx_decl_sale'] = a[a.sandbox & a.decl_sale].groupby('store_id').size().reindex(st.index).fillna(0).astype(int) > 0
        st[f'{c}_sbx_nodecl_sale'] = a[a.sandbox & ~a.decl_sale].groupby('store_id').size().reindex(st.index).fillna(0).astype(int) > 0
        st[f'{c}_sbx_decl_mkt'] = a[a.sandbox & a.decl_mkt].groupby('store_id').size().reindex(st.index).fillna(0).astype(int) > 0
        st[f'{c}_sbx_nodecl_mkt'] = a[a.sandbox & ~a.decl_mkt].groupby('store_id').size().reindex(st.index).fillna(0).astype(int) > 0
        st[f'{c}_sbx_nopurpose'] = a[a.sandbox & a.no_purpose].groupby('store_id').size().reindex(st.index).fillna(0).astype(int) > 0
        st[f'{c}_first_sbx_t'] = a[a.sandbox].groupby('store_id').t_ms.min().reindex(st.index)
    # equal observation windows: within 10 s of the load event (DOMContentLoaded if load never fired)
    Lw = ok.set_index('load_id')
    tref = Lw.t_load.where(Lw.t_load.notna(), Lw.t_dcl)
    ad['t_ref'] = ad.load_id.map(tref)
    for c in ['A0', 'A2']:
        a = ad[(ad.cond == c) & ad.sandbox & (ad.t_ms <= ad.t_ref + 10000)]
        st[f'{c}_sbx_10s'] = st.index.isin(set(a.store_id))
    # beacon-only (not a library/script load) and canary-carrying beacon versions of the sandboxed flags
    for c, conds_ in (('A0', ['A0']), ('A1after', ['A1post', 'A1next']), ('A2', ['A2'])):
        a = ad[ad.cond.isin(conds_) & ad.sandbox & ad.beacon]
        st[f'{c}_sbx_beacon'] = st.index.isin(set(a.store_id))
        st[f'{c}_sbx_canary_beacon'] = st.index.isin(set(a[a.has_canary == True].store_id))
    # repeat / Brave (only stores that have them)
    for arm in ['A0r', 'A2r', 'V1']:
        la = ok[ok.arm == arm].set_index('store_id')
        a = ad[ad.arm == arm]
        st[f'{arm}_ok'] = st.index.isin(la.index)
        st[f'{arm}_sbx'] = np.where(st[f'{arm}_ok'], st.index.isin(a[a.sandbox].store_id), np.nan)
        st[f'{arm}_any'] = np.where(st[f'{arm}_ok'], st.index.isin(a.store_id), np.nan)
        if arm == 'V1':
            st['V1_cp_sale_end'] = la.cp_sale_end
    st.reset_index().to_csv(os.path.join(OUT, 'store_table.csv'), index=False)

    # ---------------- store x vendor group ----------------
    rows = []
    allc = conds + ['A0r', 'A2r', 'V1']
    g_any = ad.groupby(['store_id', 'cond', 'vgroup']).size()
    g_sbx = ad[ad.sandbox].groupby(['store_id', 'cond', 'vgroup']).size()
    g_sbx_sale = ad[ad.sandbox & ad.decl_sale].groupby(['store_id', 'cond', 'vgroup']).size()
    g_sbx_mkt = ad[ad.sandbox & ad.decl_mkt].groupby(['store_id', 'cond', 'vgroup']).size()
    ga = set(g_any.index)
    gs = set(g_sbx.index)
    gss = set(g_sbx_sale.index)
    gsm = set(g_sbx_mkt.index)
    for s in st.index:
        for v in VENDOR_GROUPS:
            r = dict(store_id=s, vgroup=v)
            for c in allc:
                r[f'{c}_any'] = (s, c, v) in ga
                r[f'{c}_sbx'] = (s, c, v) in gs
                r[f'{c}_sbx_decl_sale'] = (s, c, v) in gss
                r[f'{c}_sbx_decl_mkt'] = (s, c, v) in gsm
            rows.append(r)
    sv = pd.DataFrame(rows)
    sv.to_csv(os.path.join(OUT, 'store_vendor.csv'), index=False)
    print('store_table', st.shape, 'store_vendor', sv.shape, 'ad requests', len(ad))


if __name__ == '__main__':
    main()
