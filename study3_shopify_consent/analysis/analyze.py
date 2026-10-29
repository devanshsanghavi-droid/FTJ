"""Study 3 main analysis. Reads the tables built by build_store_table.py and gate_audit.py and writes
outputs/stats.json (every number used in RESULTS.md / takeaways.md / figures) plus one CSV per figure panel.

Run order: extract_raw.py -> build_store_table.py -> gate_audit.py -> analyze.py -> models.py -> (figures)
           -> write_results.py -> trace_check.py
Unit of analysis: the store (main sample, captured in all three base arms, n = 1,362) unless stated.
CIs (revised after review): Wilson 95% intervals are PRIMARY for store-level proportions (the sample is a
stratified census plus a random draw of stores, for which Wilson is the design-consistent interval of an
unweighted share). A cluster bootstrap by CMP product (BCa, B = 2,000; stores without a CMP are singleton
clusters) is a SENSITIVITY interval for headline rates only, because clustering by CMP is not part of the sampling
design. Request-level shares and kappa use a bootstrap that resamples stores. Weighted (population) estimates
are stratified by Tranco bucket; conditional weighted rates use a ratio estimator.

Main revisions after the 2026-09-26 review (review/figure_fixes.md):
  * Decline analysis: only clicks that worked (banner gone 2 s later, or Shopify recorded an explicit 'no'); the
    9 failed forced clicks are reported separately. 'Shopify recorded the Decline' = explicit refusal after the
    click (currentVisitorConsent.marketing or trackingConsent == 'no'), with an 'unknown' category.
  * Decline vs GPC is compared on a fresh page with equal windows: Decline = sandboxes created on the next page
    (observed until 10 s after its load event); Default and GPC = sandboxed requests within 10 s of the load event.
  * Relay = wpm_main_proxy request whose stack holds only Shopify / store scripts (others are main-thread tags).
  * Pre-banner timing: the conservative estimate (earlier by more than the 250 ms polling interval) is primary.
  * Gate audit: denominators are configured pixels at risk ('pixel starts' when OPEN scripts are included).
  * Fig 4b presence from the pixel configuration only; Fig 4c restricted to vendors with a configured Shopify pixel.
  * Refusal signals carried by requests (Google Consent Mode gcs/gcd, npa, rdp, us_privacy; UET asc; Reddit LDU).
"""
import json
import os
import re

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from common import (CRAWL, OUT, SAMPLE, SEED, VENDOR_GROUPS, cluster_bootstrap_bca, dump, kappa, kappa_boot, wilson)
from gate_audit import decode_state

B = 2000
S = {}
CUSTOM_NAME_VENDOR = [  # custom pixel name -> ad vendor (config-only presence for Fig 4b/4c)
    ('tiktok', r'tik\s*tok'), ('meta', r'\bmeta\b|facebook|\bfb\b|\bcapi\b'), ('pinterest', r'pinterest|pintrk'), ('snap', r'snap'),
    ('microsoft_uet', r'\bbing\b|\buet\b|microsoft ads|microsoft advertising'),
    ('google_ads', r'google ads|adwords|\bgads\b|gtag|\bgtm\b|tag manager|google tag'),
    ('reddit', r'reddit'), ('linkedin', r'linkedin'), ('x_twitter', r'twitter|\bx pixel|\bx ads'), ('applovin', r'applovin|\baxon\b'),
    ('criteo', r'criteo'), ('taboola', r'taboola'), ('outbrain', r'outbrain'), ('amazon_ads', r'amazon'), ('stackadapt', r'stackadapt'),
    ('adroll', r'adroll'), ('tradedesk', r'trade ?desk|\bttd\b'), ('tvscientific', r'tvscientific'), ('mntn', r'\bmntn\b'),
    ('quora', r'quora'), ('liveintent', r'liveintent'), ('tapad', r'tapad'), ('quantcast', r'quantcast'), ('liveramp', r'liveramp'),
]
APP_VG = {'google_ads': 'Google', 'meta': 'Meta', 'tiktok': 'TikTok', 'pinterest': 'Pinterest', 'snap': 'Snap', 'linkedin': 'Reddit/other',
          'applovin': 'Reddit/other', 'reddit': 'Reddit/other', 'tvscientific': 'Reddit/other'}


def W(k, n):
    return wilson(k, n)


def WC(y, clusters):
    """Wilson record (primary) plus a BCa cluster-bootstrap interval by CMP product (sensitivity)."""
    y = np.asarray(y, dtype=int)
    r = wilson(int(y.sum()), len(y))
    cb = cluster_bootstrap_bca(y, clusters, B=B, seed=SEED)
    r['cb_lo'], r['cb_hi'], r['n_clusters'] = cb['lo'], cb['hi'], cb['n_clusters']
    return r


def boot_share(num, den, groups, B=B, seed=SEED):
    """Ratio sum(num)/sum(den) with a percentile CI from resampling groups (stores)."""
    df = pd.DataFrame(dict(num=num, den=den, g=groups)).groupby('g').sum()
    if df.den.sum() == 0:
        return dict(k=0, n=0, p=None, lo=None, hi=None, n_stores=0)
    rng = np.random.default_rng(seed)
    nv, dv = df.num.values, df.den.values
    idx = rng.integers(0, len(df), size=(B, len(df)))
    est = nv[idx].sum(1) / np.maximum(dv[idx].sum(1), 1)
    return dict(k=int(nv.sum()), n=int(dv.sum()), p=float(nv.sum() / dv.sum()), lo=float(np.percentile(est, 2.5)), hi=float(np.percentile(est, 97.5)),
                n_stores=int(len(df)))


def kg_share(num, groups, B=B, seed=SEED):
    """Share of requests with a property, clustered by store: a Korn-Graubard interval (Clopper-Pearson on the
    effective sample size, with the degrees-of-freedom correction for the number of stores). The design variance
    comes from resampling stores. When that variance is zero (every store has the same share, or p is 0 or 1) the
    effective sample size is set to the number of stores, which is conservative; the percentile bootstrap is
    degenerate (zero width) in exactly these cases, and at small store counts it is too narrow (review FIG-01).
    Korn EL, Graubard BI (1998), Survey Methodology 24(2):193-201."""
    from scipy.stats import beta, t as tdist
    df_ = pd.DataFrame(dict(num=np.asarray(num, dtype=float), g=np.asarray(groups))).groupby('g').num.agg(['sum', 'count'])
    n, k, G = int(df_['count'].sum()), float(df_['sum'].sum()), len(df_)
    if n == 0:
        return dict(k=0, n=0, p=None, kg_lo=None, kg_hi=None, n_eff=None, n_stores=0)
    p = k / n
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, G, size=(B, G))
    est = df_['sum'].values[idx].sum(1) / df_['count'].values[idx].sum(1)
    var = float(est.var(ddof=1)) if G > 1 else 0.0
    if var > 0 and 0 < p < 1:
        n_eff = min(p * (1 - p) / var, n)
        rule = 'design effect'
    else:
        n_eff = float(G)
        rule = 'no between-store variation: n_eff = stores'
    if G > 1 and n_eff > 1:
        n_eff = n_eff * (tdist.ppf(0.975, n - 1) / tdist.ppf(0.975, G - 1)) ** 2 if n > 1 else n_eff
        n_eff = min(n_eff, n)
    x = p * n_eff
    lo = 0.0 if x <= 0 else float(beta.ppf(0.025, x, n_eff - x + 1))
    hi = 1.0 if x >= n_eff else float(beta.ppf(0.975, x + 1, n_eff - x))
    return dict(k=int(k), n=n, p=float(p), kg_lo=lo, kg_hi=hi, n_eff=float(n_eff), n_stores=int(G), kg_rule=rule)


def mcnemar(a, b):
    """Exact McNemar test for paired binary outcomes a, b (two-sided binomial test on the discordant pairs)."""
    a = np.asarray(a, dtype=bool)
    b = np.asarray(b, dtype=bool)
    n10, n01 = int((a & ~b).sum()), int((~a & b).sum())
    p = binomtest(n10, n10 + n01, 0.5).pvalue if (n10 + n01) else 1.0
    return dict(n=len(a), a_only=n10, b_only=n01, both=int((a & b).sum()), neither=int((~a & ~b).sum()), p_exact=float(p),
                k_a=int(a.sum()), k_b=int(b.sum()))


def newcombe_paired(a, b):
    """Paired risk difference P(a) - P(b) with Newcombe's (1998) hybrid-score interval for paired data (method 10,
    Wilson limits combined with the continuity-corrected phi). Referee 2, S2."""
    a = np.asarray(a, dtype=bool)
    b = np.asarray(b, dtype=bool)
    n = len(a)
    A, B_, C, D = int((a & b).sum()), int((a & ~b).sum()), int((~a & b).sum()), int((~a & ~b).sum())
    w1, w2 = wilson(A + B_, n), wilson(A + C, n)
    p1, p2 = w1['p'], w2['p']
    den = np.sqrt(float((A + B_) * (C + D) * (A + C) * (B_ + D)))
    num = float(A * D - B_ * C)
    if num > 0:
        num = max(num - n / 2, 0.0)
    phi = num / den if den else 0.0
    dl = np.sqrt(max((p1 - w1['lo']) ** 2 - 2 * phi * (p1 - w1['lo']) * (w2['hi'] - p2) + (w2['hi'] - p2) ** 2, 0.0))
    du = np.sqrt(max((w1['hi'] - p1) ** 2 - 2 * phi * (w1['hi'] - p1) * (p2 - w2['lo']) + (p2 - w2['lo']) ** 2, 0.0))
    d = p1 - p2
    return dict(n=n, k_a=A + B_, k_b=A + C, a_only=B_, b_only=C, diff=float(d), diff_lo=float(d - dl), diff_hi=float(d + du),
                method='Newcombe paired hybrid score (method 10)')


def newcombe_indep(k1, n1, k2, n2):
    """Risk difference k1/n1 - k2/n2 with Newcombe's (1998) hybrid-score interval for independent samples (method 10)."""
    w1, w2 = wilson(k1, n1), wilson(k2, n2)
    d = w1['p'] - w2['p']
    return dict(k1=int(k1), n1=int(n1), k2=int(k2), n2=int(n2), p1=w1['p'], p2=w2['p'], diff=float(d),
                diff_lo=float(d - np.sqrt((w1['p'] - w1['lo']) ** 2 + (w2['hi'] - w2['p']) ** 2)),
                diff_hi=float(d + np.sqrt((w1['hi'] - w1['p']) ** 2 + (w2['p'] - w2['lo']) ** 2)), method='Newcombe hybrid score (method 10)')


def mantel_haenszel(strata):
    """Mantel-Haenszel risk difference (Sato 1989 variance) and odds ratio (Robins-Breslow-Greenland variance) over
    strata given as (a, n1, c, n0): a events among n1 exposed, c events among n0 unexposed. Strata that lack either
    group carry no information and are dropped."""
    from scipy.stats import norm
    z = norm.ppf(0.975)
    st_ = [(a, n1, c, n0) for a, n1, c, n0 in strata if n1 > 0 and n0 > 0]
    if not st_:
        return None
    num = den = sp = sq = 0.0
    R = S_ = PR = PSQR = QS = 0.0
    for a, n1, c, n0 in st_:
        N = n1 + n0
        b, d = n1 - a, n0 - c
        num += (a * n0 - c * n1) / N
        den += n1 * n0 / N
        sp += (n1 ** 2 * c - n0 ** 2 * a + n1 * n0 * (n0 - n1) / 2) / N ** 2
        sq += (a * (n0 - c) + c * (n1 - a)) / (2 * N)
        r_, s_ = a * d / N, b * c / N
        p_, q_ = (a + d) / N, (b + c) / N
        R += r_
        S_ += s_
        PR += p_ * r_
        PSQR += p_ * s_ + q_ * r_
        QS += q_ * s_
    rd = num / den
    se = np.sqrt(max((rd * sp + sq) / den ** 2, 0.0))
    out = dict(n_strata=len(st_), rd=float(rd), rd_lo=float(rd - z * se), rd_hi=float(rd + z * se), rd_method='Mantel-Haenszel, Sato variance',
               k1=int(sum(s[0] for s in st_)), n1=int(sum(s[1] for s in st_)), k0=int(sum(s[2] for s in st_)), n0=int(sum(s[3] for s in st_)))
    if R > 0 and S_ > 0:
        orr = R / S_
        v = PR / (2 * R ** 2) + PSQR / (2 * R * S_) + QS / (2 * S_ ** 2)
        out.update(odds_ratio=float(orr), or_lo=float(np.exp(np.log(orr) - z * np.sqrt(v))), or_hi=float(np.exp(np.log(orr) + z * np.sqrt(v))),
                   or_method='Mantel-Haenszel, Robins-Breslow-Greenland variance')
    return out


def WK(y, groups):
    """Wilson record plus a Korn-Graubard interval clustered by store, for shares whose unit is a pixel entry, a pixel
    start or a store-vendor pair (referee 2, S1: these units are clustered within stores)."""
    y = np.asarray(y, dtype=int)
    r = wilson(int(y.sum()), len(y))
    if len(y):
        kg = kg_share(y, groups)
        r.update(kg_lo=kg['kg_lo'], kg_hi=kg['kg_hi'], n_eff=kg['n_eff'], n_stores=kg['n_stores'], kg_rule=kg['kg_rule'])
    return r


def pid_str(x):
    s = str(x)
    return s[:-2] if s.endswith('.0') else s


def vg_of(s):
    s = s.fillna('').replace('', 'Reddit/other')
    return s.where(s.isin(VENDOR_GROUPS), 'Reddit/other')


def main():
    st = pd.read_csv(os.path.join(OUT, 'store_table.csv'))
    st = st.set_index('store_id')
    sv = pd.read_csv(os.path.join(OUT, 'store_vendor.csv'))
    ad = pd.read_csv(os.path.join(OUT, 'ad_requests.csv.gz'), low_memory=False)
    SC = pd.read_csv(os.path.join(OUT, 'sandbox_creations.csv'), low_memory=False, dtype={'pixel_id': str})
    NX = pd.read_csv(os.path.join(OUT, 'next_page_requests.csv'), low_memory=False)
    NX['vgroup'] = vg_of(NX.color_group)
    L = pd.read_csv(os.path.join(CRAWL, 'loads.csv'), low_memory=False)
    L['ok'] = (L.goto_status.fillna(0).between(200, 399)) & (L.has_shopify == True) & (L.blocked_hint != True) & (L.n_requests.fillna(0) > 20)
    PX = pd.read_csv(os.path.join(CRAWL, 'pixels.csv'), dtype={'pixel_id': str, 'apiClientId': str})
    CE = pd.read_csv(os.path.join(CRAWL, 'consent_events.csv'))
    CD = pd.read_csv(os.path.join(CRAWL, 'cmp_declared.csv'))
    LS = pd.read_csv(os.path.join(OUT, 'load_scripts.csv'))
    FA = pd.read_csv(os.path.join(os.path.dirname(OUT), 'forced_click_audit.csv'))
    summ = json.load(open(os.path.join(CRAWL, 'crawl_summary.json')))
    funnel = json.load(open(os.path.join(SAMPLE, 'raw', 'funnel.json')))
    Lx = L.set_index('load_id')
    tref = Lx.t_load.where(Lx.t_load.notna(), Lx.t_dcl)
    ad['t_ref'] = ad.load_id.map(tref)
    ad['in10s'] = ad.t_ms <= ad.t_ref + 10000

    m = st[st.stratum == 'main'].copy()
    cr = st[st.stratum == 'creator'].copy()
    clus = np.where(m.cmp.isin(['none', 'generic', 'multiple']), 'solo_' + m.index.to_series(), m.cmp)
    m['cluster'] = clus
    adm = ad[ad.stratum == 'main']
    svm = sv[sv.store_id.isin(m.index)].copy()
    bann = m[m.banner_A0]
    nob = m[~m.banner_A0]

    # ------------------------------------------------------------------ design / counts
    S['design'] = dict(bootstrap_B=B, seed=SEED, min_cell_n=5, min_cell_n_heatmap=10, min_stores_row=10, n_main=len(m), n_creator=len(cr),
                       n_planned=int(L.store_id.nunique()),
                       n_main_planned=int(L[L.stratum == 'main'].store_id.nunique()), n_creator_planned=int(L[L.stratum == 'creator'].store_id.nunique()),
                       n_loads_total=int(len(L)), n_ad_requests_main=int(len(adm)), n_clusters=int(pd.Series(clus).nunique()),
                       n_cmp_clusters=int(m[~m.cmp.isin(['none', 'generic', 'multiple'])].cmp.nunique()),
                       n_singleton_clusters=int(pd.Series(clus).str.startswith('solo_').sum()),
                       top3_cmp_share_of_banner_stores=float(bann.cmp.value_counts().head(3).sum() / len(bann)),
                       n_segment_conc6=int((m.segment_A0 == 'conc6').sum()), n_segment_conc10=int((m.segment_A0 == 'conc10').sum()),
                       loads_by_arm={a: dict(run=int((L.arm == a).sum())) for a in sorted(L.arm.unique())},
                       tranco_top_n=funnel['top_n'], sample_n=funnel['sample_after_dedupe'],
                       concurrency_limit=6, concurrency_coordinator=10, observe_after_load_s=15, next_page_observe_s=10, equal_window_s=10,
                       first_scroll_after_load_ms=2000, banner_poll_ms=250, timeline_axis_s=6, click_check_s=2, gap_threshold2_ms=500,
                       kappa_almost_perfect=0.81, repeat_fraction_pct=20, brave_subsample=100,
                       repeat_planned=int((L.arm == 'A0r').sum()), brave_planned=int((L.arm == 'V1').sum()))
    for a, v in summ['loads'].items():
        S['design']['loads_by_arm'][a]['ok'] = v['ok']
    S['design']['failed_loads'] = summ['blocked_or_failed_loads']
    ex = funnel['exclusion_reasons']
    S['design']['funnel_excl'] = dict(
        drawn_to_live=int(funnel['drawn_for_verification'] - funnel['verified_live_online_store']),
        headless=ex['headless_or_assets_only'], http403=ex['blocked_http_403'],
        other_errors=int(funnel['drawn_for_verification'] - funnel['verified_live_online_store'] - ex['headless_or_assets_only'] - ex['blocked_http_403']),
        live_to_sample=int(funnel['verified_live_online_store'] - funnel['sample_after_dedupe']),
        no_product=ex['no_product_url'], child=ex['child_directed'], duplicate=ex['duplicate_of'], adult=ex['adult_content'],
        sample_to_captured=int(funnel['sample_after_dedupe'] - len(m)))

    # ------------------------------------------------------------------ Figure 1b: situating data
    f1 = {}
    f1['banner'] = WC(m.banner_A0, m.cluster)
    f1['sandboxed_prechoice'] = WC(m.A0_sbx, m.cluster)
    f1['both'] = WC(m.banner_A0 & m.A0_sbx, m.cluster)
    f1['any_ad_prechoice'] = WC(m.A0_any, m.cluster)
    f1['banner_any_ad_prechoice'] = WC(m.banner_A0 & m.A0_any, m.cluster)
    f1['banner_fires'] = WC(bann.A0_sbx, bann.cluster)
    f1['nobanner_fires'] = WC(nob.A0_sbx, nob.cluster)
    # region default: Wilson plus the cluster bootstrap by consent tool (the default is strongly clustered by product)
    mr_ = m[m.region_optout.notna()]
    f1['region_allowed'] = WC(mr_.region_optout == True, mr_.cluster)
    S['fig1b'] = f1
    pd.DataFrame([dict(row=k, **v) for k, v in f1.items()]).to_csv(os.path.join(OUT, 'fig1b.csv'), index=False)

    # ------------------------------------------------------------------ Figure 1c: one real page load
    cand = m[m.banner_A0 & m.A0_sbx & (m.A0_first_sbx_t < m.t_banner_A0)].copy()
    a0s = adm[(adm.cond == 'A0') & adm.sandbox]
    ngroups = a0s.groupby('store_id').vgroup.nunique()
    cand['n_vgroups'] = ngroups.reindex(cand.index).fillna(0)
    medb = float(m[m.banner_A0 & m.A0_sbx].t_banner_A0.median())
    cand['dist'] = (cand.t_banner_A0 - medb).abs()
    cand = cand[(cand.n_vgroups >= 3) & (cand.t_banner_A0 <= 4000)]
    pick = cand.sort_values(['n_vgroups', 'dist'], ascending=[False, True]).index[0]
    tl = adm[(adm.cond == 'A0') & (adm.store_id == pick)][['t_ms', 'vgroup', 'vendor', 'origin', 'oclass', 'sandbox', 'kind', 'beacon', 'has_canary',
                                                           'has_full_url']].sort_values('t_ms')
    tl.to_csv(os.path.join(OUT, 'fig1c_timeline.csv'), index=False)
    first_sbx = tl[tl.sandbox].iloc[0]
    S['fig1c'] = dict(store_id=pick, domain=m.loc[pick, 'domain'], cmp=m.loc[pick, 'cmp'], t_banner=float(m.loc[pick, 't_banner_A0']),
                      n_ad_requests=int(len(tl)), n_sandboxed=int(tl.sandbox.sum()), n_vgroups_sandboxed=int(tl[tl.sandbox].vgroup.nunique()),
                      n_sandboxed_before_banner=int((tl.sandbox & (tl.t_ms < m.loc[pick, 't_banner_A0'])).sum()),
                      t_first_sandboxed=float(first_sbx.t_ms), first_sandboxed_is_library=bool(first_sbx.kind == 'library'),
                      t_first_sandboxed_beacon=float(tl[tl.sandbox & tl.beacon].t_ms.min()),
                      n_library=int((tl.kind == 'library').sum()), n_sandboxed_library=int((tl.sandbox & (tl.kind == 'library')).sum()),
                      n_candidates=int(len(cand)), median_banner_ms_ref=medb,
                      region_header=m.loc[pick, 'cmp_header_A0'], n_with_full_url=int(tl.has_full_url.sum()),
                      n_sandboxed_with_full_url=int((tl.sandbox & tl.has_full_url).sum()))

    # ------------------------------------------------------------------ Figure 3
    f3 = {'a': {}, 'b': {}, 'c': {}, 'd': {}}
    rows = []
    for v in VENDOR_GROUPS:
        x = svm[svm.vgroup == v].set_index('store_id')
        # per-vendor rows now carry the cluster bootstrap too, so every row of Fig 3a has both intervals (review FIG-04)
        rb_ = WC(x.loc[bann.index, 'A0_sbx'].astype(int).values, bann.cluster.values)
        rn_ = WC(x.loc[nob.index, 'A0_sbx'].astype(int).values, nob.cluster.values)
        f3['a'][v] = dict(banner=rb_, no_banner=rn_)
        rows.append(dict(vgroup=v, group='banner', **rb_))
        rows.append(dict(vgroup=v, group='no_banner', **rn_))
    f3['a']['any'] = dict(banner=WC(bann.A0_sbx, bann.cluster), no_banner=WC(nob.A0_sbx, nob.cluster))
    rows.append(dict(vgroup='Any vendor', group='banner', **f3['a']['any']['banner']))
    rows.append(dict(vgroup='Any vendor', group='no_banner', **f3['a']['any']['no_banner']))
    pd.DataFrame(rows).to_csv(os.path.join(OUT, 'fig3a.csv'), index=False)
    # b: timing on banner stores with a pre-choice sandboxed ad request. The banner detector polls every 250 ms, so
    # a request counts as surely before the banner only if it came more than one polling interval earlier.
    bb = bann[bann.A0_sbx].dropna(subset=['A0_first_sbx_t', 't_banner_A0']).copy()
    bb['gap'] = bb.t_banner_A0 - bb.A0_first_sbx_t
    poll = S['design']['banner_poll_ms']
    a0b = adm[(adm.cond == 'A0') & adm.sandbox & adm.beacon].groupby('store_id').t_ms.min()
    a0cb = adm[(adm.cond == 'A0') & adm.sandbox & adm.beacon & (adm.has_canary == True)].groupby('store_id').t_ms.min()
    bb['t_first_beacon'] = a0b.reindex(bb.index)
    bb['t_first_canary_beacon'] = a0cb.reindex(bb.index)
    xb = bb.dropna(subset=['t_first_beacon'])
    xcb = bb.dropna(subset=['t_first_canary_beacon'])
    pd.DataFrame(dict(store_id=bb.index, t_first_sbx=bb.A0_first_sbx_t, t_banner=bb.t_banner_A0, gap=bb.gap,
                      t_first_beacon=bb.t_first_beacon)).to_csv(os.path.join(OUT, 'fig3b.csv'), index=False)
    axis_ms = 1000 * S['design']['timeline_axis_s']
    f3['b'] = dict(n=len(bb), before_banner=W(int((bb.gap > 0).sum()), len(bb)), before_banner_by_poll=W(int((bb.gap > poll).sum()), len(bb)),
                   before_banner_500=W(int((bb.gap > 500).sum()), len(bb)),
                   beacon_before_banner=W(int((xb.t_banner_A0 > xb.t_first_beacon).sum()), len(xb)),
                   beacon_before_banner_by_poll=W(int((xb.t_banner_A0 - xb.t_first_beacon > poll).sum()), len(xb)),
                   canary_beacon_before_banner=W(int((xcb.t_banner_A0 > xcb.t_first_canary_beacon).sum()), len(xcb)),
                   median_first_sbx_ms=float(bb.A0_first_sbx_t.median()), median_banner_ms=float(bb.t_banner_A0.median()),
                   median_gap_ms=float(bb.gap.median()), q25_gap_ms=float(bb.gap.quantile(.25)), q75_gap_ms=float(bb.gap.quantile(.75)),
                   q25_first_sbx_ms=float(bb.A0_first_sbx_t.quantile(.25)), q75_first_sbx_ms=float(bb.A0_first_sbx_t.quantile(.75)),
                   q25_banner_ms=float(bb.t_banner_A0.quantile(.25)), q75_banner_ms=float(bb.t_banner_A0.quantile(.75)),
                   n_gap_beyond_axis=int((bb.gap.abs() > axis_ms / 2).sum()),
                   n_first_beyond_axis=int((bb.A0_first_sbx_t > axis_ms).sum()), n_banner_beyond_axis=int((bb.t_banner_A0 > axis_ms).sum()),
                   segment_conc6_before=W(int(((bb.gap > 0) & (bb.segment_A0 == 'conc6')).sum()), int((bb.segment_A0 == 'conc6').sum())),
                   segment_conc10_before=W(int(((bb.gap > 0) & (bb.segment_A0 == 'conc10')).sum()), int((bb.segment_A0 == 'conc10').sum())))
    # repeatability of the before-banner flag (stores with a banner and a sandboxed request in both Default loads)
    Lr = L[(L.arm == 'A0r') & L.ok].set_index('store_id')
    r_first = adm[(adm.arm == 'A0r') & adm.sandbox].groupby('store_id').t_ms.min()
    rep = bb[bb.index.isin(Lr.index)].copy()
    rep['t_banner_r'] = Lr.t_banner_visible.reindex(rep.index)
    rep['t_first_r'] = r_first.reindex(rep.index)
    rep = rep.dropna(subset=['t_banner_r', 't_first_r'])
    fa, fb = (rep.gap > 0).values, ((rep.t_banner_r - rep.t_first_r) > 0).values
    f3['b']['repeat'] = dict(n=len(rep), agree=int((fa == fb).sum()), kappa=kappa(fa, fb), before_A0=int(fa.sum()), before_A0r=int(fb.sum()),
                             median_abs_shift_first_ms=float((rep.A0_first_sbx_t - rep.t_first_r).abs().median()),
                             median_abs_shift_banner_ms=float((rep.t_banner_A0 - rep.t_banner_r).abs().median()))
    # c: origin of pre-choice ad requests (revised classes: relay only with a Shopify/store-only stack)
    a0 = adm[adm.cond == 'A0'].copy()
    rows = []
    for v in VENDOR_GROUPS + ['All']:
        x = a0 if v == 'All' else a0[a0.vgroup == v]
        n = len(x)
        r = dict(vgroup=v, n_requests=n, n_stores=int(x.store_id.nunique()))
        for o in ['sandbox', 'relay', 'open_pixel', 'page']:
            r[o] = float((x.oclass == o).sum() / n) if n else 0.0
            r[o + '_k'] = int((x.oclass == o).sum())
        rows.append(r)
        f3['c'][v] = r
    pd.DataFrame(rows).to_csv(os.path.join(OUT, 'fig3c.csv'), index=False)
    f3['c']['share_sandbox_boot'] = boot_share((a0.oclass == 'sandbox').astype(int), np.ones(len(a0)), a0.store_id)
    f3['c']['share_wpm_boot'] = boot_share(a0.oclass.isin(['sandbox', 'relay']).astype(int), np.ones(len(a0)), a0.store_id)
    # the old label: manager bundle anywhere in the stack (for the record)
    # referee revision: CORS preflights removed and frames nested in a LAX sandbox counted as sandboxed (common.py)
    S['attribution'] = json.load(open(os.path.join(OUT, 'attribution_changes.json')))
    ac_ = S['attribution']['A0']
    f3['c']['share_sandbox_crawl_labels'] = W(ac_['sandboxed_crawl_labels'], ac_['ad_requests_crawl'])
    f3['c']['share_old_proxy_label_boot'] = boot_share(a0.origin.isin(['strict_worker', 'lax_iframe', 'wpm_main_proxy']).astype(int), np.ones(len(a0)), a0.store_id)
    px_ = a0[a0.origin == 'wpm_main_proxy']
    f3['c']['old_proxy_label'] = dict(n=int(len(px_)), n_loads=int(px_.load_id.nunique()),
                                      vendor_library=W(int((px_.stack_class == 'vendor_library').sum()), len(px_)),
                                      other_third_party=W(int((px_.stack_class == 'other_third_party').sum()), len(px_)),
                                      shopify_or_store_only=W(int((px_.stack_class == 'shopify_or_store_only').sum()), len(px_)))
    # store-level summary: per-store share of Default ad requests that were sandboxed (median over stores with any)
    ps = a0.groupby('store_id').apply(lambda g: (g.oclass == 'sandbox').mean(), include_groups=False)
    f3['c']['store_share_sandbox'] = dict(median=float(ps.median()), q25=float(ps.quantile(.25)), q75=float(ps.quantile(.75)), n_stores=int(len(ps)),
                                          stores_any_sandbox=W(int((ps > 0).sum()), len(ps)))
    # referee 1 (section 4, item 3; text pass 2026-09-26): what a cookie-based audit would see of sandboxed traffic.
    # n_cookies = number of Cookie-header names recorded for the request (DevTools requestWillBeSentExtraInfo).
    ck = {}
    for o_ in ('strict_worker', 'lax_iframe', 'lax_nested', 'main_thread'):
        x_ = a0[a0.origin == o_]
        ck[o_] = dict(n=int(len(x_)), with_cookie=int((x_.n_cookies.fillna(0) > 0).sum()), n_cookies_missing=int(x_.n_cookies.isna().sum()))
    sb_ = a0[a0.sandbox]
    anyck = sb_.groupby('store_id').n_cookies.apply(lambda s_: bool((s_.fillna(0) > 0).any()))
    ck['stores_sbx'] = int(len(anyck))
    ck['stores_sbx_all_cookieless'] = W(int((~anyck).sum()), int(len(anyck)))
    ck['note'] = ('Default load, main sample, ad requests (preflights removed); a request "carries a cookie" if DevTools recorded at least one '
                  'Cookie header name for it. Stores: those with a sandboxed ad request before any choice.')
    f3['c']['cookies'] = ck
    # d: region mode (P1)
    rows = []
    for mode, sel in (('opt_out', bann.region_optout == True), ('opt_in', bann.region_optout == False)):
        b = bann[sel]
        f3['d'][mode] = dict(any_sbx=WC(b.A0_sbx, b.cluster), mkt_sbx=WC(b.A0_sbx_decl_mkt, b.cluster), nopurpose_sbx=W(int(b.A0_sbx_nopurpose.sum()), len(b)),
                             nomkt_sbx=W(int(b.A0_sbx_nodecl_mkt.sum()), len(b)))
        rows.append(dict(mode=mode, measure='any_sbx', **f3['d'][mode]['any_sbx']))
        rows.append(dict(mode=mode, measure='mkt_sbx', **f3['d'][mode]['mkt_sbx']))
    grants = consent_changes(CE, L, st)
    S['consent_changes_summary'] = summarize_changes(grants, m, cr, L)
    # referee revision: what the pages saw of our browser, and CMP rules that react to it
    S['automation'] = automation(L, st, m, cr, CE, grants, adm)
    bot_rule = set(S['automation']['pandectes_bot']['stores'])
    # opt-in proxy (referee 1, M4): on 'denied until consent' banner stores, sandboxed pixels that do not declare marketing
    # or declare no purpose (Wilson records already exist; add the cluster interval by consent tool)
    for mode, sel in (('opt_out', bann.region_optout == True), ('opt_in', bann.region_optout == False)):
        b = bann[sel]
        f3['d'][mode]['nomkt_sbx'] = WC(b.A0_sbx_nodecl_mkt, b.cluster)
        f3['d'][mode]['nopurpose_sbx'] = WC(b.A0_sbx_nopurpose, b.cluster)
    # referee 2, m2: the region-default association within consent product (banner stores with a readable default;
    # stores without a single consent product are their own stratum and carry no information)
    bd = bann[bann.region_optout.notna()]
    strata = []
    for c, x in bd.groupby('cluster'):
        a_, d_ = x[x.region_optout == True], x[x.region_optout == False]
        strata.append((int(a_.A0_sbx.sum()), len(a_), int(d_.A0_sbx.sum()), len(d_)))
    mh = mantel_haenszel(strata)
    mh['crude'] = newcombe_indep(int(bd[bd.region_optout == True].A0_sbx.sum()), int((bd.region_optout == True).sum()),
                                 int(bd[bd.region_optout == False].A0_sbx.sum()), int((bd.region_optout == False).sum()))
    mh['by_product'] = {c: dict(allowed=W(int(x[x.region_optout == True].A0_sbx.sum()), int((x.region_optout == True).sum())),
                                denied=W(int(x[x.region_optout == False].A0_sbx.sum()), int((x.region_optout == False).sum())))
                        for c, x in bd.groupby('cmp') if c in ('pandectes', 'onetrust', 'cookiebot', 'shopify_native', 'osano')}
    mh['stores_in_informative_strata'] = int(mh['n1'] + mh['n0'])
    f3['d']['mh_by_product'] = mh
    oi = bann[(bann.region_optout == False) & bann.A0_sbx_decl_mkt]
    ce0 = CE[(CE.arm == 'A0') & CE.detail.str.contains('"marketingAllowed":true')]
    first_mkt = adm[(adm.cond == 'A0') & adm.sandbox & adm.decl_mkt].groupby('store_id').t_ms.min()
    oi_grant = [s for s in oi.index if ((ce0.store_id == s) & (ce0.t_ms <= first_mkt.get(s, -1))).any()]
    f3['d']['opt_in_mkt_fired_after_cmp_grant'] = dict(k=len(oi_grant), n=len(oi), stores=oi_grant,
                                                       other=[s for s in oi.index if s not in oi_grant])
    pd.DataFrame(rows).to_csv(os.path.join(OUT, 'fig3d.csv'), index=False)
    f3['nobanner_any_sbx'] = WC(nob.A0_sbx, nob.cluster)
    S['fig3'] = f3

    # ------------------------------------------------------------------ config-only presence (Fig 4b, 4c)
    pres = config_presence(PX, adm, m.index)
    # ------------------------------------------------------------------ Figure 4: declared vs actual
    f4 = {'a': {}, 'b': {}}
    d = CD[(CD.arm == 'A0') & CD.store_id.isin(m.index) & (CD.is_advertising == True)].copy()
    vg_map = ad.drop_duplicates('vendor').set_index('vendor').vgroup.to_dict()
    d['vgroup'] = d.vendor.map(vg_map).fillna('Reddit/other')
    blk_st = sorted(d[d.declared_prechoice == 'blocked'].store_id.unique())
    a0all = adm[adm.cond == 'A0']
    fired_sbx_pairs = set(zip(a0all[a0all.sandbox].store_id, a0all[a0all.sandbox].vendor))
    fired_sbx_mkt_pairs = set(zip(a0all[a0all.sandbox & a0all.decl_mkt].store_id, a0all[a0all.sandbox & a0all.decl_mkt].vendor))
    fired_any_pairs = set(zip(a0all.store_id, a0all.vendor))
    db = d[d.declared_prechoice == 'blocked'].copy()
    decl_vendor_sbx = [s for s in blk_st if any((s, v) in fired_sbx_pairs for v in db[db.store_id == s].vendor)]
    decl_vendor_sbx_mkt = [s for s in blk_st if any((s, v) in fired_sbx_mkt_pairs for v in db[db.store_id == s].vendor)]
    decl_vendor_any = [s for s in blk_st if any((s, v) in fired_any_pairs for v in db[db.store_id == s].vendor)]
    rows = []
    x = m.loc[blk_st]
    f4['a']['blocklist'] = dict(any_sbx=W(int(x.A0_sbx.sum()), len(x)), mkt_sbx=W(int(x.A0_sbx_decl_mkt.sum()), len(x)),
                                declared_vendor_fired_sbx=W(len(decl_vendor_sbx), len(x)), declared_vendor_fired_sbx_mkt=W(len(decl_vendor_sbx_mkt), len(x)),
                                declared_vendor_fired_any=W(len(decl_vendor_any), len(x)),
                                n_pairs_declared_blocked=int(len(db)), n_pairs_fired_any=int(sum((r.store_id, r.vendor) in fired_any_pairs for r in db.itertuples())),
                                n_pairs_fired_sbx=int(sum((r.store_id, r.vendor) in fired_sbx_pairs for r in db.itertuples())),
                                by_cmp={c: int(g.store_id.nunique()) for c, g in db.groupby('cmp')}, n_cmps=int(db.cmp.nunique()))
    # c: blocklisted vendor entries, restricted to vendors whose Shopify pixel is configured (sandboxed) on that store
    po = a0all.groupby(['store_id', 'vendor']).oclass.apply(set)
    db['cfg_sandboxed'] = [(r.store_id, r.vendor) in pres['cfg_vendor'] for r in db.itertuples()]
    db['cfg_open'] = [(r.store_id, r.vendor) in pres['cfg_open_vendor'] for r in db.itertuples()]
    outc = []
    for r in db.itertuples():
        o = po.get((r.store_id, r.vendor))
        outc.append('none' if o is None else ('sandbox' if 'sandbox' in o else ('open_pixel' if 'open_pixel' in o else ('relay' if 'relay' in o else 'page'))))
    db['outcome'] = outc
    db.to_csv(os.path.join(OUT, 'fig4c_declared_blocked_pairs.csv'), index=False)
    c4 = dict(n_pairs=int(len(db)), n_stores=int(db.store_id.nunique()), outcomes={k: int(v) for k, v in db.outcome.value_counts().items()})
    g1 = db[db.cfg_sandboxed]
    g2 = db[~db.cfg_sandboxed]
    # entry-level shares carry a Korn-Graubard interval clustered by store (referee 2, S1); Wilson kept for reference
    c4['cfg'] = dict(n=int(len(g1)), n_stores=int(g1.store_id.nunique()), vendors={k: int(v) for k, v in g1.vgroup.value_counts().items()},
                     sandbox=WK(g1.outcome == 'sandbox', g1.store_id), open_pixel=WK(g1.outcome == 'open_pixel', g1.store_id),
                     relay=WK(g1.outcome == 'relay', g1.store_id), page=WK(g1.outcome == 'page', g1.store_id),
                     any=WK(g1.outcome != 'none', g1.store_id),
                     stores_sandbox=W(int(g1[g1.outcome == 'sandbox'].store_id.nunique()), int(g1.store_id.nunique())))
    c4['nocfg'] = dict(n=int(len(g2)), n_stores=int(g2.store_id.nunique()), n_open_cfg=int(g2.cfg_open.sum()),
                       any=WK(g2.outcome != 'none', g2.store_id), sandbox=WK(g2.outcome == 'sandbox', g2.store_id),
                       open_pixel=WK(g2.outcome == 'open_pixel', g2.store_id), relay=WK(g2.outcome == 'relay', g2.store_id),
                       page=WK(g2.outcome == 'page', g2.store_id))
    rows4c = []
    for grp, gg in (('cfg', g1), ('nocfg', g2)):
        for o in ['sandbox', 'open_pixel', 'relay', 'page', 'any']:
            y_ = (gg.outcome != 'none') if o == 'any' else (gg.outcome == o)
            rows4c.append(dict(group=grp, outcome=o, **WK(y_, gg.store_id)))
    pd.DataFrame(rows4c).to_csv(os.path.join(OUT, 'fig4c.csv'), index=False)
    f4['c'] = c4
    # Sensitivity of the blocklist row (final audit, 2026-09-26). On some blocklist stores the CMP itself wrote
    # 'marketing: yes' to Shopify without any click, so at runtime the CMP was in a consented state, not 'blocked'.
    #   excl_auto_grant:     drop stores where that write switched a denying region default to 'yes' (automatic grant)
    #   excl_yes_before_pixel: drop stores where a 'yes' write came before the declared vendor's first sandboxed request
    #                        (or, where no declared vendor fired, any 'yes' write)
    #   excl_any_yes:        drop every store whose CMP wrote 'yes' without a click
    g0g = grants[(grants.arm == 'A0') & (grants.m_change == 'grant') & grants.store_id.isin(m.index)]
    auto_grant = sorted(set(g0g.store_id) & set(blk_st))
    ce_yes = CE[(CE.arm == 'A0') & CE.detail.str.contains('"marketingAllowed":true') & CE.store_id.isin(blk_st)]
    yes_t = ce_yes.groupby('store_id').t_ms.min().to_dict()
    first_decl = {}
    for s in blk_st:
        t_ = a0all[(a0all.store_id == s) & a0all.sandbox & a0all.vendor.isin(set(db[db.store_id == s].vendor))].t_ms
        first_decl[s] = float(t_.min()) if len(t_) else None
    yes_first = sorted(s for s in yes_t if first_decl[s] is None or yes_t[s] <= first_decl[s])

    def _sub(excl):
        keep = [s for s in blk_st if s not in excl]
        return dict(stores_excluded=sorted(excl), n_excluded=len(excl), fired=W(sum(s in decl_vendor_sbx for s in keep), len(keep)),
                    fired_mkt=W(sum(s in decl_vendor_sbx_mkt for s in keep), len(keep)), any_sbx=W(int(m.loc[keep].A0_sbx.sum()), len(keep)))
    f4['a']['blocklist']['sens_excl_auto_grant'] = _sub(auto_grant)
    f4['a']['blocklist']['sens_excl_yes_before_pixel'] = _sub(yes_first)
    f4['a']['blocklist']['sens_excl_any_yes'] = _sub(sorted(yes_t))
    f4['a']['blocklist']['yes_write_stores'] = dict(n=len(yes_t), auto_grant=len(auto_grant), yes_before_pixel=len(yes_first),
                                                    yes_after_pixel=sorted(s for s in yes_t if s not in yes_first),
                                                    auto_grant_declared_vendor_fired=sum(s in decl_vendor_sbx for s in auto_grant))
    # stratified by Shopify's region default (moved into the pipeline from review/text_fix_checks, review MET-21)
    g0dn_ = set(grants[(grants.arm == 'A0') & (grants.m_change == 'deny')].store_id)
    bd_ = {}
    for lab_, sel_ in (('allowed', m.loc[blk_st].region_optout == True), ('denied', m.loc[blk_st].region_optout == False)):
        ids_ = [s_ for s_, ok_ in zip(blk_st, sel_) if ok_]
        bd_[lab_] = dict(fired=W(sum(s_ in decl_vendor_sbx for s_ in ids_), len(ids_)), any_sbx=W(int(m.loc[ids_].A0_sbx.sum()), len(ids_)),
                         auto_grant=sum(s_ in set(g0g.store_id) for s_ in ids_), auto_deny=sum(s_ in g0dn_ for s_ in ids_))
    bd_['unknown_default'] = int(m.loc[blk_st].region_optout.isna().sum())
    ag_den = [s_ for s_ in auto_grant if m.loc[s_, 'region_optout'] == False]
    bd_['denied_auto_grant'] = dict(n=len(ag_den), stores=ag_den, declared_vendor_fired=sum(s_ in decl_vendor_sbx for s_ in ag_den),
                                    any_sbx=int(m.loc[ag_den].A0_sbx.sum()) if ag_den else 0,
                                    cmp={c_: int(v_) for c_, v_ in m.loc[ag_den].cmp.value_counts().items()})
    bd_['by_cmp'] = {c_: int(v_) for c_, v_ in m.loc[blk_st].cmp.value_counts().items()}
    # beacon-only version of the vendor-matched rate
    a0b_ = a0all[a0all.sandbox & a0all.beacon & a0all.store_id.isin(blk_st)]
    bpairs_ = set(zip(db.store_id, db.vendor))
    bd_['beacon_only'] = dict(declared_vendor_fired_sbx=W(len({s_ for s_, v_ in zip(a0b_.store_id, a0b_.vendor) if (s_, v_) in bpairs_}), len(blk_st)),
                              any_sbx=W(int(a0b_.store_id.nunique()), len(blk_st)))
    f4['a']['blocklist']['by_default'] = bd_
    # ---- referee revision (2026-09-26): blocked on paper, conditioned on the CMP intending to block for this visitor ----
    # PRIMARY: stores whose CMP wrote no 'marketing: yes' in the Default load (a 'yes' write means the CMP itself had
    # consented for our browser, by its configuration, its implied-consent mode or its bot rule, so its blocklist was
    # not in force). The unconditioned 12 of 21 stays as 'declared_vendor_fired_sbx'.
    bl = f4['a']['blocklist']
    bl['primary'] = dict(_sub(sorted(yes_t)), rule="stores whose CMP wrote no 'marketing: yes' in the Default load")
    bl['bot_rule'] = dict(stores=sorted(set(blk_st) & bot_rule), n=len(set(blk_st) & bot_rule),
                          declared_vendor_fired=sum(s_ in decl_vendor_sbx for s_ in set(blk_st) & bot_rule),
                          among_auto_grant=len(set(auto_grant) & bot_rule), among_denied_auto_grant=len(set(ag_den) & bot_rule))
    # the seven 'yes' writers: version, default, banner, timing of the write relative to our first passive scroll
    ver_ = {s_: str(g_.detail.iloc[0])[:2] for s_, g_ in db.groupby('store_id')}
    Lx0 = L.set_index('load_id')
    yw = {}
    for s_ in sorted(yes_t):
        lid_ = f'{s_}__A0'
        tl_ = Lx0.loc[lid_, 't_load'] if lid_ in Lx0.index else np.nan
        yw[s_] = dict(cmp=db[db.store_id == s_].cmp.iloc[0], version=ver_.get(s_), default_allows=bool(m.loc[s_, 'region_optout'] == True),
                      banner=bool(m.loc[s_, 'banner_A0']), t_yes=float(yes_t[s_]), t_banner=float(m.loc[s_, 't_banner_A0']) if pd.notna(m.loc[s_, 't_banner_A0']) else None,
                      after_first_scroll=bool(pd.notna(tl_) and yes_t[s_] >= tl_ + 2000), bot_rule=s_ in bot_rule, auto_grant=s_ in auto_grant,
                      declared_vendor_fired=s_ in decl_vendor_sbx)
    bl['yes_writers'] = yw
    bl['yes_writers_summary'] = dict(n=len(yw), bot_rule=sum(v['bot_rule'] for v in yw.values()),
                                     pandectes_v4=sum(v['version'] == 'v4' for v in yw.values()),
                                     v4_no_banner=sorted(s_ for s_, v in yw.items() if v['version'] == 'v4' and not v['banner']),
                                     v4_banner_yes_before_scroll=sorted(s_ for s_, v in yw.items() if v['version'] == 'v4' and v['banner'] and not v['after_first_scroll']),
                                     v4_banner_yes_after_scroll=sorted(s_ for s_, v in yw.items() if v['version'] == 'v4' and v['banner'] and v['after_first_scroll']))
    ys_ = bl['yes_writers_summary']
    ys_.update(n_v4_no_banner=len(ys_['v4_no_banner']), n_v4_banner_yes_before_scroll=len(ys_['v4_banner_yes_before_scroll']),
               n_v4_banner_yes_after_scroll=len(ys_['v4_banner_yes_after_scroll']))
    # Pandectes version of the blocklist stores (v4 code was not saved; v5 applies an 'optout' policy outside its strict regions)
    pv_ = pd.Series({s_: ver_[s_] for s_ in blk_st if db[db.store_id == s_].cmp.iloc[0] == 'pandectes'})
    bl['pandectes_versions'] = {k: int(v) for k, v in pv_.value_counts().items()}
    bl['pandectes_v4_no_yes'] = dict(n=int(sum((v == 'v4') and (s_ not in yes_t) for s_, v in pv_.items())),
                                     fired=int(sum((v == 'v4') and (s_ not in yes_t) and (s_ in decl_vendor_sbx) for s_, v in pv_.items())))
    # per product (the CMP whose blocklist was read)
    bl['by_cmp_fired'] = {c: W(sum(s_ in decl_vendor_sbx for s_ in g_.store_id.unique()), int(g_.store_id.nunique())) for c, g_ in db.groupby('cmp')}
    bl['primary_by_cmp_fired'] = {c: W(sum(s_ in decl_vendor_sbx for s_ in g_.store_id.unique() if s_ not in yes_t),
                                        int(sum(s_ not in yes_t for s_ in g_.store_id.unique()))) for c, g_ in db.groupby('cmp')}
    # outcome-independent conditioning (referee 2, S4b): stores with a configured sandboxed pixel of a declared vendor
    cfg_st = sorted(db[db.cfg_sandboxed].store_id.unique())
    bl['cfg_stores'] = dict(fired=W(sum(s_ in decl_vendor_sbx for s_ in cfg_st), len(cfg_st)),
                            neither_cfg_nor_fired=int(sum((s_ not in cfg_st) and (s_ not in decl_vendor_sbx) for s_ in blk_st)),
                            fired_without_cfg=int(sum((s_ not in cfg_st) and (s_ in decl_vendor_sbx) for s_ in blk_st)))
    cfg_ny = [s_ for s_ in cfg_st if s_ not in yes_t]
    bl['cfg_stores_primary'] = W(sum(s_ in decl_vendor_sbx for s_ in cfg_ny), len(cfg_ny))
    # like-for-like (referee 2, S4a): ANY sandboxed ad pixel on blocklist stores vs banner stores without a readable
    # declaration, within Shopify's region default (the reference of the 'allowed' stratum is Fig 4a's reference row)
    ref_al = bann[(bann.region_optout == True) & ~bann.index.isin(blk_st) & ~bann.index.isin(set(grants[(grants.arm == 'A0') & (grants.m_change == 'deny')].store_id))]
    ref_dn = bann[(bann.region_optout == False) & ~bann.index.isin(blk_st)]
    lf = {}
    strata = []
    for lab_, ref_ in (('allowed', ref_al), ('denied', ref_dn)):
        ids_ = [s_ for s_ in blk_st if m.loc[s_, 'region_optout'] == (lab_ == 'allowed')]
        k1, n1 = int(m.loc[ids_].A0_sbx.sum()), len(ids_)
        k0, n0 = int(ref_.A0_sbx.sum()), len(ref_)
        lf[lab_] = dict(blocklist=W(k1, n1), reference=W(k0, n0), diff=newcombe_indep(k1, n1, k0, n0),
                        blocklist_declared_vendor=W(sum(s_ in decl_vendor_sbx for s_ in ids_), n1),
                        auto_grant=sum(s_ in auto_grant for s_ in ids_), yes_write=sum(s_ in yes_t for s_ in ids_),
                        declared_vendor_fired_auto_grant=sum((s_ in decl_vendor_sbx) and (s_ in auto_grant) for s_ in ids_))
        strata.append((k1, n1, k0, n0))
    lf['mh'] = mantel_haenszel(strata)
    lf['all_blocklist_any_sbx'] = f4['a']['blocklist']['any_sbx']
    # the same comparison among stores whose CMP wrote no 'yes' in the Default load (blocklist and reference alike)
    yes_any = set(ce0.store_id)
    strata = []
    for lab_, ref_ in (('allowed', ref_al), ('denied', ref_dn)):
        ids_ = [s_ for s_ in blk_st if m.loc[s_, 'region_optout'] == (lab_ == 'allowed') and s_ not in yes_any]
        rf_ = ref_[~ref_.index.isin(yes_any)]
        k1, n1, k0, n0 = int(m.loc[ids_].A0_sbx.sum()), len(ids_), int(rf_.A0_sbx.sum()), len(rf_)
        lf[lab_ + '_no_yes'] = dict(blocklist=W(k1, n1), reference=W(k0, n0), diff=newcombe_indep(k1, n1, k0, n0),
                                     blocklist_declared_vendor=W(sum(s_ in decl_vendor_sbx for s_ in ids_), n1),
                                     reference_excluded=int(ref_.index.isin(yes_any).sum()))
        strata.append((k1, n1, k0, n0))
    lf['mh_no_yes'] = mantel_haenszel(strata)
    lf['mh_no_yes']['reduction_ruled_out_beyond'] = float(max(0.0, -lf['mh_no_yes']['rd_lo']))
    lf['note'] = ("tests the falsification criterion of pre-crawl prediction P1 (notes/mechanism.md): a blocklist that lowered "
                  "sandboxed firing would show a negative difference")
    f4['a']['like_for_like'] = lf
    # pattern-level check (referee 1, M2; exploratory): for Pandectes entries whose vendor fired from the sandbox, does
    # the CMP's own blocklist pattern (a regular expression) match a URL that the sandbox fetched in the Default load?
    a0sx = a0all[a0all.sandbox]
    pm_rows = []
    for r in db[db.outcome == 'sandbox'].itertuples():
        mt = re.match(r'v\d \S+ (.+?); ', str(r.detail))
        pat = mt.group(1) if (r.cmp == 'pandectes' and mt) else None
        urls = a0sx[(a0sx.store_id == r.store_id) & (a0sx.vendor == r.vendor)].url.astype(str)
        hit = None
        if pat:
            try:
                rx_ = re.compile(pat.replace('\n', '|'))
                hit = bool(any(rx_.search(u) for u in urls))
            except re.error:
                hit = bool(any(any(x.replace('\\', '') in u for x in pat.split('|') if x) for u in urls))
        pm_rows.append(dict(store_id=r.store_id, cmp=r.cmp, vendor=r.vendor, pattern=pat, n_sandbox_urls=len(urls), match=hit))
    PMx = pd.DataFrame(pm_rows)
    PMx.to_csv(os.path.join(OUT, 'fig4_pattern_match.csv'), index=False)
    hitx = PMx[PMx.match == True]
    bl['pattern_match'] = dict(entries_fired_sbx=int(len(PMx)), entries_pandectes=int((PMx.cmp == 'pandectes').sum()),
                               entries_pattern_read=int(PMx.pattern.notna().sum()), entries_match=int(len(hitx)), stores_match=int(hitx.store_id.nunique()),
                               stores_match_ids=sorted(hitx.store_id.unique()), stores_match_primary=int(sum(s_ not in yes_t for s_ in hitx.store_id.unique())),
                               vendors_match={k: int(v) for k, v in hitx.vendor.value_counts().items()}, exploratory=True)
    g0d = grants[(grants.arm == 'A0') & (grants.m_change == 'deny') & grants.store_id.isin(m.index)]
    x = m.loc[sorted(g0d.store_id.unique())]
    f4['a']['cpapi_deny'] = dict(any_sbx=W(int(x.A0_sbx.sum()), len(x)), mkt_sbx=W(int(x.A0_sbx_decl_mkt.sum()), len(x)),
                                 by_cmp={c: int(v) for c, v in x.cmp.value_counts().items()})
    x = bann[bann.region_optout == False]
    f4['a']['region_optin'] = dict(any_sbx=W(int(x.A0_sbx.sum()), len(x)), mkt_sbx=W(int(x.A0_sbx_decl_mkt.sum()), len(x)))
    x = bann[(bann.region_optout == True) & ~bann.index.isin(blk_st) & ~bann.index.isin(g0d.store_id)]
    f4['a']['none_declared_optout'] = dict(any_sbx=W(int(x.A0_sbx.sum()), len(x)), mkt_sbx=W(int(x.A0_sbx_decl_mkt.sum()), len(x)))
    rows.append(dict(row='blocklist', measure='any_sbx', **f4['a']['blocklist']['declared_vendor_fired_sbx']))
    rows.append(dict(row='blocklist', measure='mkt_sbx', **f4['a']['blocklist']['declared_vendor_fired_sbx_mkt']))
    rows.append(dict(row='blocklist_excl_auto_grant', measure='any_sbx', **f4['a']['blocklist']['sens_excl_auto_grant']['fired']))
    rows.append(dict(row='blocklist_excl_auto_grant', measure='mkt_sbx', **f4['a']['blocklist']['sens_excl_auto_grant']['fired_mkt']))
    for k in ['cpapi_deny', 'region_optin', 'none_declared_optout']:
        for meas in ['any_sbx', 'mkt_sbx']:
            rows.append(dict(row=k, measure=meas, **f4['a'][k][meas]))
    # referee revision: primary (no CMP 'yes' write) and like-for-like rows (declared vendor vs any sandboxed ad pixel)
    rows.append(dict(row='blocklist_primary', measure='declared_vendor_sbx', **bl['primary']['fired']))
    rows.append(dict(row='blocklist_primary', measure='any_sbx', **bl['primary']['any_sbx']))
    rows.append(dict(row='blocklist', measure='any_sbx_like_for_like', **bl['any_sbx']))
    for lab_ in ('allowed', 'denied'):
        rows.append(dict(row=f'blocklist_default_{lab_}', measure='declared_vendor_sbx', **lf[lab_]['blocklist_declared_vendor']))
        rows.append(dict(row=f'blocklist_default_{lab_}', measure='any_sbx', **lf[lab_]['blocklist']))
        rows.append(dict(row=f'reference_default_{lab_}', measure='any_sbx', **lf[lab_]['reference']))
    pd.DataFrame(rows).to_csv(os.path.join(OUT, 'fig4a.csv'), index=False)
    # b: heatmap vendor x CMP product among banner stores; presence from the pixel configuration only
    top = bann.cmp.value_counts()
    cols = [c for c in top.index if top[c] >= 10 and c not in ('none', 'generic', 'multiple')]
    bann = bann.copy()
    bann['cmpcol'] = np.where(bann.cmp.isin(cols), bann.cmp, 'other')
    fired0 = set(zip(svm[svm.A0_sbx].store_id, svm[svm.A0_sbx].vgroup))
    present = pres['cfg']
    rows = []
    for c in cols + ['other']:
        ids = bann[bann.cmpcol == c].index
        for v in VENDOR_GROUPS:
            pairs = [s for s in ids if (s, v) in present]
            k = sum((s, v) in fired0 for s in pairs)
            rows.append(dict(cmp=c, vgroup=v, **W(k, len(pairs)), n_banner_stores=len(ids)))
        pairs = [(s, v) for s in ids for v in VENDOR_GROUPS if (s, v) in present]
        k = sum(p in fired0 for p in pairs)
        rows.append(dict(cmp=c, vgroup='All vendors', **W(k, len(pairs)), n_banner_stores=len(ids)))
        xs = bann[bann.cmpcol == c]
        rows.append(dict(cmp=c, vgroup='region_denied', **W(int((xs.region_optout == False).sum()), int(xs.region_optout.notna().sum())), n_banner_stores=len(ids)))
    H = pd.DataFrame(rows)
    H.to_csv(os.path.join(OUT, 'fig4b.csv'), index=False)
    allpairs = [(s, v) for s in bann.index for v in VENDOR_GROUPS if (s, v) in present]
    # the pairs the old definition added (a sandboxed request in some arm, no configured pixel): reported separately
    req_only = [(s, v) for s in bann.index for v in VENDOR_GROUPS if (s, v) in pres['req'] and (s, v) not in present]
    old_def = [(s, v) for s in bann.index for v in VENDOR_GROUPS if (s, v) in pres['req'] or (s, v) in pres['old_cfg']]
    Hc = H[H.vgroup.isin(VENDOR_GROUPS)]
    f4['b'] = dict(cmps=cols + ['other'], n_pairs=len(allpairs), fired=WK([p in fired0 for p in allpairs], [s for s, _ in allpairs]),
                   n_stores=int(len({s for s, _ in allpairs})),
                   request_only_pairs=W(sum(p in fired0 for p in req_only), len(req_only)),
                   old_definition=W(sum(p in fired0 for p in old_def), len(old_def)),
                   cells_n_lt10=int((Hc.n < 10).sum()), cells_n_lt5=int((Hc.n < 5).sum()), cells=int(len(Hc)),
                   by_cmp={c: dict(W(int(H[(H.cmp == c) & (H.vgroup == 'All vendors')].k.iloc[0]), int(H[(H.cmp == c) & (H.vgroup == 'All vendors')].n.iloc[0])),
                                   n_banner_stores=int(H[(H.cmp == c)].n_banner_stores.iloc[0]),
                                   region_denied=W(int(H[(H.cmp == c) & (H.vgroup == 'region_denied')].k.iloc[0]),
                                                   int(H[(H.cmp == c) & (H.vgroup == 'region_denied')].n.iloc[0]))) for c in cols + ['other']},
                   presence_sources=pres['sources'])
    # stratified by region default (the confounder of the CMP comparison)
    strat = {}
    for mode, lab in ((True, 'allowed'), (False, 'denied')):
        for c in cols + ['other']:
            ids = bann[(bann.cmpcol == c) & (bann.region_optout == mode)].index
            pp = [(s, v) for s in ids for v in VENDOR_GROUPS if (s, v) in present]
            strat.setdefault(lab, {})[c] = W(sum(p in fired0 for p in pp), len(pp))
    f4['b']['by_region'] = strat
    S['fig4'] = f4

    # ------------------------------------------------------------------ Figure 5
    f5 = {'a': {}, 'b': {}, 'c': {}, 'd': {}}
    clk_all = m[m.clicked].copy()
    failed = clk_all[~clk_all.click_ok.astype(bool)]
    clk = clk_all[clk_all.click_ok.astype(bool)].copy()
    nxs = NX[NX.store_id.isin(m.index) & (NX.next_source != 'main_thread_or_other')]
    newp = nxs[nxs.next_source == 'new_page']
    oldp = nxs[nxs.next_source == 'old_page']
    for frame_ in (clk, clk_all):
        frame_['after_decline_sbx'] = frame_.A1post_sbx | frame_.A1next_sbx
        frame_['fresh'] = frame_.index.isin(set(newp.store_id))
        frame_['fresh_mkt'] = frame_.index.isin(set(newp[newp.pixel_purposes.fillna('').str.contains('MARKETING')].store_id))
        frame_['fresh_nomkt'] = frame_.index.isin(set(newp[~newp.pixel_purposes.fillna('').str.contains('MARKETING')].store_id))
        frame_['unload_old'] = frame_.index.isin(set(oldp.store_id))
    # same page after the click: sandboxed requests from pixels declaring marketing (created before the click)
    post = adm[(adm.cond == 'A1post') & adm.sandbox]
    clk['same_mkt'] = clk.index.isin(set(post[post.decl_mkt].store_id))
    clk['same_nomkt'] = clk.index.isin(set(post[~post.decl_mkt].store_id))
    fresh_v = set(zip(newp.store_id, newp.vgroup))
    a0_10 = adm[(adm.cond == 'A0') & adm.sandbox & adm.in10s]
    a2_10 = adm[(adm.cond == 'A2') & adm.sandbox & adm.in10s]
    s0_10, s2_10 = set(zip(a0_10.store_id, a0_10.vgroup)), set(zip(a2_10.store_id, a2_10.vgroup))
    sva = svm.set_index('store_id')
    rows = []
    for v in VENDOR_GROUPS + ['Any vendor']:
        if v == 'Any vendor':
            d0, d1, d2 = clk.A0_sbx_10s, clk.fresh, clk.A2_sbx_10s
            dany, dpre = clk.after_decline_sbx, clk.A1pre_sbx
        else:
            d0 = pd.Series([(s, v) in s0_10 for s in clk.index], index=clk.index)
            d1 = pd.Series([(s, v) in fresh_v for s in clk.index], index=clk.index)
            d2 = pd.Series([(s, v) in s2_10 for s in clk.index], index=clk.index)
            x = sva[sva.vgroup == v].loc[clk.index]
            dany, dpre = x.A1post_sbx | x.A1next_sbx, x.A1pre_sbx
        f5['a'][v] = dict(Default=W(int(d0.sum()), len(clk)), Decline=W(int(d1.sum()), len(clk)), GPC=W(int(d2.sum()), len(clk)),
                          Decline_any_after=W(int(dany.sum()), len(clk)), Decline_preclick=W(int(dpre.sum()), len(clk)))
        for arm, dd in (('Default', d0), ('Decline', d1), ('GPC', d2), ('Decline_preclick', dpre)):
            rows.append(dict(vgroup=v, arm=arm, **W(int(dd.sum()), len(clk))))
    pd.DataFrame(rows).to_csv(os.path.join(OUT, 'fig5a.csv'), index=False)
    f5['a']['n_clicked'] = len(clk)
    # paired comparison, equal windows (Decline next page, fresh sandboxes vs GPC first 10 s) and the reviewer's version
    f5['compare'] = dict(equal_window=mcnemar(clk.fresh, clk.A2_sbx_10s), gpc_whole_load=mcnemar(clk.fresh, clk.A2_sbx),
                         old_any_after_vs_gpc=mcnemar(clk.after_decline_sbx, clk.A2_sbx),
                         all_clicked_fresh_vs_gpc=mcnemar(clk_all.fresh, clk_all.A2_sbx))
    # referee 2, S2: effect sizes. Paired risk differences (Newcombe) for the primary comparison, for each control
    # against Default in the same window on the same stores, and for the whole visit (pre-click exposure under Decline
    # against the whole GPC load); the estimand of the primary comparison is persistence after the choice on a later page
    cp_ = f5['compare']
    for k_, (a_, b_) in dict(equal_window=(clk.fresh, clk.A2_sbx_10s), gpc_whole_load=(clk.fresh, clk.A2_sbx),
                             all_clicked_fresh_vs_gpc=(clk_all.fresh, clk_all.A2_sbx)).items():
        cp_[k_]['paired_diff'] = newcombe_paired(a_, b_)
    cp_['default_vs_decline'] = dict(mcnemar(clk.A0_sbx_10s, clk.fresh), paired_diff=newcombe_paired(clk.A0_sbx_10s, clk.fresh))
    cp_['default_vs_gpc'] = dict(mcnemar(clk.A0_sbx_10s, clk.A2_sbx_10s), paired_diff=newcombe_paired(clk.A0_sbx_10s, clk.A2_sbx_10s))
    cp_['whole_visit_preclick_vs_gpc'] = dict(mcnemar(clk.A1pre_sbx, clk.A2_sbx), paired_diff=newcombe_paired(clk.A1pre_sbx, clk.A2_sbx))
    dl_any = clk.A1pre_sbx | clk.A1post_sbx | clk.A1next_sbx
    cp_['whole_visit_decline_load_vs_gpc'] = dict(mcnemar(dl_any, clk.A2_sbx), paired_diff=newcombe_paired(dl_any, clk.A2_sbx))
    cp_['estimand'] = 'post-choice persistence: a sandbox created on a later page (Decline) vs the GPC load, equal 10 s windows'
    cp_['fresh_given_default'] = W(int((clk.fresh & clk.A0_sbx_10s).sum()), int(clk.A0_sbx_10s.sum()))
    cp_['gpc_given_default'] = W(int((clk.A2_sbx_10s & clk.A0_sbx_10s).sum()), int(clk.A0_sbx_10s.sum()))

    def mgroup(md):
        return {'N': 'Shopify native banner', 'A': 'CMP writes to Shopify API', 'C': 'CMP writes to Shopify API'}.get(md, 'Blocker only / unknown / none')
    clk['mgroup'] = clk.cmp_mode.map(mgroup)
    m['mgroup'] = m.cmp_mode.map(mgroup)
    rcat = {'refused': 'Shopify recorded a refusal', 'still_allowed': 'marketing still allowed', 'no_record_default_denied': 'unknown / no record',
            'unknown': 'unknown / no record'}
    clk['rgroup'] = clk.refusal_cat.map(rcat)
    rows = []
    for g, x in clk.groupby('mgroup'):
        f5['b'][g] = dict(decline_residual=WC(x.fresh, x.cluster), decline_any_after=W(int(x.after_decline_sbx.sum()), len(x)),
                          refused=W(int((x.refusal_cat == 'refused').sum()), len(x)),
                          default_allowed=W(int((x.region_optout == True).sum()), int(x.region_optout.notna().sum())))
        rows.append(dict(group=g, kind='mode', arm='Decline', **f5['b'][g]['decline_residual']))
    for g in ['Shopify recorded a refusal', 'marketing still allowed', 'unknown / no record']:
        x = clk[clk.rgroup == g]
        f5['b'][g] = dict(decline_residual=WC(x.fresh, x.cluster), decline_any_after=W(int(x.after_decline_sbx.sum()), len(x)),
                          fresh_mkt=W(int(x.fresh_mkt.sum()), len(x)))
        rows.append(dict(group=g, kind='refusal', arm='Decline', **f5['b'][g]['decline_residual']))
    s0 = m[m.A0_sbx]
    for g, x in s0.groupby('mgroup'):
        f5['b'].setdefault('gpc_' + g, {})['gpc_residual'] = W(int(x.A2_sbx.sum()), len(x))
        rows.append(dict(group=g, kind='mode', arm='GPC', **W(int(x.A2_sbx.sum()), len(x))))
    pd.DataFrame(rows).to_csv(os.path.join(OUT, 'fig5b.csv'), index=False)
    # refusal recording
    allowed_default = clk[clk.region_optout == True]
    fa_ = FA.set_index('store_id')
    f5['decline'] = dict(
        clicked_all=len(clk_all), clicked=len(clk), failed_clicks=len(failed), forced=int((clk_all.click_method == 'playwright_force').sum()),
        forced_still_visible=int(((clk_all.click_method == 'playwright_force') & (clk_all.banner_still_after_click == True)).sum()),
        forced_explicit_no=int(((clk_all.click_method == 'playwright_force') & (clk_all.explicit_refusal == True)).sum()),
        forced_audit=dict(n=len(FA), failed=int(FA.audit_click_failed.sum()),
                          overlay_modal=int(FA.overlay_in_pre_shot.str.contains('modal|selector|gate').sum()),
                          chat_widget=int(FA.overlay_in_pre_shot.str.contains('chat').sum()),
                          agree_with_rule=int(sum((fa_.loc[s, 'audit_click_failed'] == 1) == (not bool(clk_all.loc[s, 'click_ok'])) for s in fa_.index if s in clk_all.index))),
        failed_residual_fresh=W(int(failed.index.isin(set(newp.store_id)).sum()), len(failed)),
        refused=W(int((clk.refusal_cat == 'refused').sum()), len(clk)),
        refused_all_clicked=W(int((clk_all.refusal_cat == 'refused').sum()), len(clk_all)),
        still_allowed=W(int((clk.refusal_cat == 'still_allowed').sum()), len(clk)),
        unknown=W(int(clk.refusal_cat.isin(['unknown', 'no_record_default_denied']).sum()), len(clk)),
        no_record_default_denied=int((clk.refusal_cat == 'no_record_default_denied').sum()),
        refused_on_allowed_default=W(int((allowed_default.refusal_cat == 'refused').sum()), len(allowed_default)),
        old_flag_denied_end=W(int((clk_all.marketing_denied_end_A1 == True).sum()), len(clk_all)),
        old_flag_denied_end_default_denied=int(((clk_all.marketing_denied_end_A1 == True) & (clk_all.region_optout == False)).sum()),
        old_flag_not_denied_on_denied_default_unreadable=int(((clk_all.marketing_denied_end_A1 != True) & (clk_all.region_optout == False) &
                                                              clk_all.cp_marketing_end_A1.isna()).sum()),
        old_flag_not_denied_on_denied_default_allowed=int(((clk_all.marketing_denied_end_A1 != True) & (clk_all.region_optout == False) &
                                                           (clk_all.cp_marketing_end_A1 == True)).sum()),
        fresh=WC(clk.fresh, clk.cluster), after_decline_any_sbx=WC(clk.after_decline_sbx, clk.cluster),
        same_page=W(int(clk.A1post_sbx.sum()), len(clk)), next_page_any_phase=W(int(clk.A1next_sbx.sum()), len(clk)),
        unload_old=W(int(clk.unload_old.sum()), len(clk)), pre_click_sbx=W(int(clk.A1pre_sbx.sum()), len(clk)),
        next_given_pre=W(int((clk.A1pre_sbx & clk.A1next_sbx).sum()), int(clk.A1pre_sbx.sum())),
        fresh_given_pre=W(int((clk.A1pre_sbx & clk.fresh).sum()), int(clk.A1pre_sbx.sum())),
        banner_found=W(int(m.banner_A1.sum()), len(m)), no_reject=W(int((m.banner_A1 & m.no_decline_option).sum()), int(m.banner_A1.sum())),
        next_any_ad=W(int(clk.A1next_any.sum()), len(clk)))
    f5['gpc_residual'] = WC(m[m.A0_sbx].A2_sbx, m[m.A0_sbx].cluster)
    # c: after Shopify recorded the refusal, which sandboxed pixels still sent requests?
    gdeny = m[(m.A2_header_sale_declined == True) | (m.cp_sale_end_A2 == False)]
    c5 = {}
    c5['gpc_n'] = len(gdeny)
    c5['gpc_decl_sale_fired'] = W(int(gdeny.A2_sbx_decl_sale.sum()), len(gdeny))
    c5['gpc_nodecl_sale_fired'] = W(int(gdeny.A2_sbx_nodecl_sale.sum()), len(gdeny))
    c5['gpc_nopurpose_fired'] = W(int(gdeny.A2_sbx_nopurpose.sum()), len(gdeny))
    dd = clk[clk.refusal_cat == 'refused']
    c5['decline_n'] = len(dd)
    c5['decline_newpage_mkt_fired'] = W(int(dd.fresh_mkt.sum()), len(dd))
    c5['decline_newpage_nomkt_fired'] = W(int(dd.fresh_nomkt.sum()), len(dd))
    c5['decline_samepage_mkt_fired'] = W(int(dd.same_mkt.sum()), len(dd))
    c5['decline_samepage_nomkt_fired'] = W(int(dd.same_nomkt.sum()), len(dd))
    c5['decline_unload_fired'] = W(int(dd.unload_old.sum()), len(dd))
    # referee 2, S3: unload beacons split by whether the old sandbox's pixel declares marketing (the refused purpose)
    old_mkt = set(oldp[oldp.pixel_purposes.fillna('').str.contains('MARKETING')].store_id)
    c5['decline_unload_mkt_fired'] = W(int(dd.index.isin(old_mkt).sum()), len(dd))
    c5['decline_unload_nomkt_fired'] = W(int(dd.index.isin(set(oldp[~oldp.pixel_purposes.fillna('').str.contains('MARKETING')].store_id)).sum()), len(dd))
    c5['composition'] = residual_composition(dd, gdeny, adm, newp, oldp, SC, L)
    # timing and stacks of the same-page continued sends by marketing-declaring pixels
    pm = post[post.decl_mkt & post.store_id.isin(dd.index)].copy()
    pm['dt'] = pm.t_ms - pm.t_click
    stk = pd.read_csv(os.path.join(OUT, 'raw_stacks.csv'))
    pm = pm.drop(columns=['stack_class']).merge(stk[['load_id', 'i', 'stack_class', 'has_wpm_code']], on=['load_id', 'i'], how='left')
    c5['samepage_mkt_requests'] = dict(n=int(len(pm)), stores=int(pm.store_id.nunique()), median_ms=float(pm.dt.median()), max_ms=float(pm.dt.max()),
                                       min_ms=float(pm.dt.min()),
                                       vendors={k: int(v) for k, v in pm.vendor.value_counts().head(6).items()},
                                       stack_pixel_code_only=int((pm.stack_class == 'shopify_or_store_only').sum()),
                                       stack_vendor_library=int((pm.stack_class == 'vendor_library').sum()),
                                       stack_none=int((pm.stack_class == 'no_stack').sum()),
                                       kinds={k: int(v) for k, v in pm.kind.fillna('other').value_counts().items()})
    ol = oldp[oldp.store_id.isin(clk.index)].merge(clk[['t_click']], left_on='store_id', right_index=True)
    ol['dt'] = ol.t_ms - ol.t_click
    c5['unload_requests'] = dict(n=int(len(ol)), stores=int(ol.store_id.nunique()), uet=int((ol.vendor == 'microsoft_uet').sum()),
                                 min_s=float(ol.dt.min() / 1000), max_s=float(ol.dt.max() / 1000), median_s=float(ol.dt.median() / 1000),
                                 beacons=int((ol.kind == 'beacon').sum()),
                                 median_s_after_reload=float((ol.t_ms - ol.load_id.map(Lx.t_next_nav)).median() / 1000))
    # Fig 5c (referee revision): residual classes. cat = refused (the pixel declares a purpose the choice refused),
    # left_allowed (it declares only purposes the choice left allowed), none (it declares no purpose)
    cg, cd, cl_ = c5['composition']['gpc'], c5['composition']['decline'], c5['composition']['decline']['classes']
    f3w = W(cl_['f3'], cl_['n'])
    f3i = W(cl_['f3_incomplete'], cl_['n'])
    f4n = W(cl_['f4_no_purpose'], cl_['n'])
    rows = [dict(block='GPC', bar='declares sale of data', cat='refused', **cg['sale']),
            dict(block='GPC', bar='declares only purposes GPC leaves allowed', cat='left_allowed', **cg['left_allowed']),
            dict(block='GPC', bar='declares no purpose', cat='none', **cg['none']),
            dict(block='Decline', bar='started before the click, kept sending (same page or unload beacon)', cat='refused', **f3w),
            dict(block='Decline', bar='new sandbox after the refusal, declares a refused purpose', cat='refused', **cd['fresh_page']['refused']),
            dict(block='Decline', bar='declares only purposes the Decline left allowed (any window)', cat='left_allowed', **f3i),
            dict(block='Decline', bar='declares no purpose (any window)', cat='none', **f4n)]
    c5['fig5c_rows'] = dict(f3=f3w, f3_incomplete=f3i, f4_no_purpose=f4n)
    pd.DataFrame(rows).to_csv(os.path.join(OUT, 'fig5c.csv'), index=False)
    # ---- gate audit (revised denominators) ----
    c5['gate_audit'] = gate_audit_summary(SC, L, PX, grants, m, st)
    f5['c'] = c5
    # d: race -- CMP-initiated consent changes (no click) vs creation of THIRD-PARTY marketing-declaring sandboxes
    tct = LS.set_index('load_id').t_ctapi
    SC3 = SC[SC.declares_marketing & (SC.pixel_api.astype(str) != 'shopify-pixel') & (SC.kind != 'open_main_thread_pixel')]
    rr = []
    for r in grants[grants.m_change.isin(['grant', 'deny']) & grants.arm.isin(['A0', 'A2']) & (grants.stratum == 'main')].itertuples():
        sc = SC3[SC3.load_id == r.load_id]
        if not len(sc):
            continue
        tc_ = tct.get(r.load_id, np.nan)
        rr.append(dict(load_id=r.load_id, store_id=r.store_id, arm=r.arm, stratum=r.stratum, change=r.m_change, t_update=r.t_ev,
                       t_first_create=float(sc.t_ms.min()), t_last_create=float(sc.t_ms.max()), n_pixels=len(sc),
                       n_before=int((sc.t_ms < r.t_ev).sum()), n_after=int((sc.t_ms >= r.t_ev).sum()), cmp=st.loc[r.store_id, 'cmp'],
                       t_ctapi=tc_, n_before_ctapi=int((sc.t_ms < tc_).sum()) if pd.notna(tc_) else None,
                       t_first_scroll=r.t_first_scroll, before_scroll=bool(r.t_ev < r.t_first_scroll) if pd.notna(r.t_first_scroll) else None))
    RC = pd.DataFrame(rr)
    RC['dt_first'] = RC.t_first_create - RC.t_update
    RC.to_csv(os.path.join(OUT, 'fig5d.csv'), index=False)
    all_mkt = SC[SC.declares_marketing]
    for ch in ('grant', 'deny'):
        x = RC[RC.change == ch]
        lids = set(x.load_id)
        allx = all_mkt[all_mkt.load_id.isin(set(grants[(grants.m_change == ch) & grants.arm.isin(['A0', 'A2']) & (grants.stratum == 'main')].load_id))]
        f5['d'][ch] = dict(loads=len(x), stores=int(x.store_id.nunique()), pixels=int(x.n_pixels.sum()), pixels_before=int(x.n_before.sum()),
                           pixels_after=int(x.n_after.sum()), loads_first_before=int((x.t_first_create < x.t_update).sum()),
                           loads_any_before=int((x.n_before > 0).sum()),
                           loads_all_before=int((x.n_after == 0).sum()), loads_all_after=int((x.n_before == 0).sum()),
                           loads_first_after=int((x.t_first_create >= x.t_update).sum()),
                           first_after_stores=sorted(x[x.t_first_create >= x.t_update].store_id.tolist()),
                           first_after_lag_ms=[float(v) for v in x[x.t_first_create >= x.t_update].dt_first],
                           median_lag_first_ms=float(x.dt_first.median()) if len(x) else None,
                           median_update_ms=float(x.t_update.median()) if len(x) else None,
                           median_first_create_ms=float(x.t_first_create.median()) if len(x) else None,
                           pixels_before_ctapi=int(x.n_before_ctapi.fillna(0).sum()), loads_with_ctapi=int(x.t_ctapi.notna().sum()),
                           median_ctapi_ms=float(x.t_ctapi.median()) if x.t_ctapi.notna().any() else None,
                           before_first_scroll=int((x.before_scroll == True).sum()),
                           by_arm={a: int(v) for a, v in x.arm.value_counts().items()},
                           by_arm_first_before={a: int(((g.t_first_create < g.t_update)).sum()) for a, g in x.groupby('arm')},
                           by_cmp={c: int(v) for c, v in x.cmp.value_counts().head(8).items()},
                           all_marketing_creations=int(len(allx)), shopify_own=int((allx.pixel_api.astype(str) == 'shopify-pixel').sum()),
                           open_scripts=int((allx.kind == 'open_main_thread_pixel').sum()))
        lag = []
        for r in x.itertuples():
            lag += list(SC3[SC3.load_id == r.load_id].t_ms - r.t_update)
        f5['d'][ch]['median_lag_pixel_ms'] = float(np.median(lag)) if lag else None
        f5['d'][ch]['median_abs_lag_pixel_ms'] = float(abs(np.median(lag))) if lag else None
        # referee 2, m1 (text pass): the race by crawl segment (6 vs 10 concurrent browsers), since CPU contention could shift timing
        seg_ = pd.Series([st.loc[r.store_id, f'segment_{r.arm}'] for r in x.itertuples()], index=x.index, dtype=object)
        f5['d'][ch]['by_segment'] = {sg: dict(loads=int((seg_ == sg).sum()), loads_first_before=int(((seg_ == sg) & (x.t_first_create < x.t_update)).sum()),
                                              pixels=int(x[seg_ == sg].n_pixels.sum()), pixels_before=int(x[seg_ == sg].n_before.sum()))
                                     for sg in ('conc6', 'conc10')}
    # ---- refusal signals carried by requests (Google Consent Mode etc.) ----
    f5['flags'] = refusal_signals(adm, clk, m, newp)
    # ---- e: projection to the population (moved from Fig 6d) ----
    f5['e'] = projection(m, clk, funnel)
    pd.DataFrame([dict(outcome=k, **{kk: vv for kk, vv in v.items() if not isinstance(vv, dict)}) for k, v in f5['e'].items() if isinstance(v, dict) and 'p' in v]
                 ).to_csv(os.path.join(OUT, 'fig5e.csv'), index=False)
    S['fig5'] = f5

    # ------------------------------------------------------------------ Figure 6
    f6 = {'a': {}, 'b': {}, 'c': {}}
    bea = adm[adm.beacon & adm.arm.isin(['A0', 'A1', 'A2'])]
    rows = []
    for v in VENDOR_GROUPS + ['All']:
        for arm, lab in (('A0', 'Default'), ('A1', 'Decline'), ('A2', 'GPC')):
            x = bea[(bea.arm == arm) & ((bea.vgroup == v) | (v == 'All'))]
            xs = x[x.sandbox]
            r = boot_share(xs.has_full_url.astype(int), np.ones(len(xs)), xs.store_id)
            if len(xs):
                kg_ = kg_share(xs.has_full_url.astype(int), xs.store_id)
                r.update(kg_lo=kg_['kg_lo'], kg_hi=kg_['kg_hi'], n_eff=kg_['n_eff'], kg_rule=kg_['kg_rule'])
            ra = boot_share(x.has_full_url.astype(int), np.ones(len(x)), x.store_id)
            rows.append(dict(vgroup=v, arm=lab, origin='sandboxed', **r))
            rows.append(dict(vgroup=v, arm=lab, origin='all', **ra))
            f6['a'].setdefault(v, {})[lab] = r
            f6['a'][v][lab + '_all_origins'] = ra
    pd.DataFrame(rows).to_csv(os.path.join(OUT, 'fig6a.csv'), index=False)
    sbe = bea[bea.sandbox & (bea.arm == 'A0')]
    f6['a']['sandboxed_A0'] = boot_share(sbe.has_full_url.astype(int), np.ones(len(sbe)), sbe.store_id)
    alle = bea[bea.arm == 'A0']
    f6['a']['all_origins_A0'] = boot_share(alle.has_full_url.astype(int), np.ones(len(alle)), alle.store_id)
    stores_url = adm[(adm.cond == 'A0') & adm.sandbox & adm.has_full_url].store_id.nunique()
    f6['a']['stores_sandboxed_full_url_A0'] = W(stores_url, len(m))
    # b: creator case (Store C = C005)
    adc = ad[ad.stratum == 'creator']
    cl = adc[adc.store_id == 'C005'].copy()
    cl.to_csv(os.path.join(OUT, 'fig6b_store_c.csv'), index=False)
    Lc = L[L.store_id == 'C005'].set_index('arm')
    f6['b']['store_c'] = {a: dict(n_ad=int((cl.arm == a).sum()), n_sandboxed=int(((cl.arm == a) & cl.sandbox).sum()),
                                     n_tiktok=int(((cl.arm == a) & (cl.vgroup == 'TikTok')).sum()),
                                     n_creator_token=int(((cl.arm == a) & cl.has_creator_token).sum()),
                                     n_creator_token_tiktok=int(((cl.arm == a) & cl.has_creator_token & (cl.vgroup == 'TikTok')).sum()),
                                     n_creator_token_tiktok_sbx=int(((cl.arm == a) & cl.has_creator_token & (cl.vgroup == 'TikTok') & cl.sandbox).sum()),
                                     n_creator_token_nongoogle=int(((cl.arm == a) & cl.has_creator_token & (cl.vgroup != 'Google')).sum()),
                                     vendors_with_token=sorted(cl[(cl.arm == a) & cl.has_creator_token].vendor.unique().tolist()),
                                     t_banner=float(Lc.loc[a, 't_banner_visible']) if a in Lc.index and pd.notna(Lc.loc[a, 't_banner_visible']) else None,
                                     t_click=float(Lc.loc[a, 't_click']) if a in Lc.index and pd.notna(Lc.loc[a, 't_click']) else None,
                                     t_next_nav=float(Lc.loc[a, 't_next_nav']) if a in Lc.index and pd.notna(Lc.loc[a, 't_next_nav']) else None,
                                     n_vendors_with_token=int(cl[(cl.arm == a) & cl.has_creator_token].vendor.nunique()),
                                     n_vendors_with_token_nongoogle=int(cl[(cl.arm == a) & cl.has_creator_token & (cl.vgroup != 'Google')].vendor.nunique()),
                                     header=str(Lc.loc[a, 'cmp_header_raw'])[:20] if a in Lc.index else None)
                                 for a in ['A0', 'A0r', 'A1', 'A2', 'A2r']}
    ca = cl[cl.cond.isin(['A1post', 'A1next']) & cl.has_creator_token]
    cp_ = cl[(cl.cond == 'A1pre') & cl.has_creator_token]
    f6['b']['store_c_after_decline'] = dict(n=int(len(ca)), n_nongoogle=int((ca.vgroup != 'Google').sum()), vendors=sorted(ca.vendor.unique().tolist()),
                                               n_vendors=int(ca.vendor.nunique()), n_vendors_nongoogle=int(ca[ca.vgroup != 'Google'].vendor.nunique()),
                                               n_sandboxed=int(ca.sandbox.sum()), n_vendors_sandboxed=int(ca[ca.sandbox].vendor.nunique()),
                                               tiktok=int((ca.vgroup == 'TikTok').sum()))
    f6['b']['store_c_pre_click'] = dict(n=int(len(cp_)), n_vendors=int(cp_.vendor.nunique()), vendors=sorted(cp_.vendor.unique().tolist()),
                                           n_vendors_sandboxed=int(cp_[cp_.sandbox].vendor.nunique()))
    tok = adc[adc.has_creator_token]
    f6['b']['creator_stores'] = len(cr)
    f6['b']['creator_token_reached_ad_vendor_A0'] = W(int(tok[tok.arm == 'A0'].store_id.nunique()), len(cr))
    f6['b']['creator_token_reached_nongoogle_A0'] = W(int(tok[(tok.arm == 'A0') & (tok.vgroup != 'Google')].store_id.nunique()), len(cr))
    f6['b']['creator_token_reached_sandboxed_A0'] = W(int(tok[(tok.arm == 'A0') & tok.sandbox].store_id.nunique()), len(cr))
    f6['b']['creator_token_by_arm'] = {a: int(tok[tok.arm == a].store_id.nunique()) for a in ['A0', 'A1', 'A2', 'A0r', 'A2r']}
    f6['b']['creator_token_stores_A0'] = sorted(tok[tok.arm == 'A0'].store_id.unique().tolist())
    Cst = pd.read_csv(os.path.join(SAMPLE, 'creator_stratum.csv')).set_index('store_id')
    f6['b']['token_level_counts'] = {k: int(v) for k, v in Cst.token_level.value_counts().items()}
    vid = Cst[Cst.token_level == 'video'].index if 'video' in set(Cst.token_level) else []
    f6['b']['video_token_stores'] = len(vid)
    f6['b']['video_token_reached_A0'] = int(tok[(tok.arm == 'A0') & tok.store_id.isin(vid)].store_id.nunique())
    f6['b']['video_token_reached_nongoogle_A0'] = int(tok[(tok.arm == 'A0') & tok.store_id.isin(vid) & (tok.vgroup != 'Google')].store_id.nunique())
    f6['b']['creator_A0_sbx'] = W(int(cr.A0_sbx.sum()), len(cr))
    f6['b']['creator_A2_given_A0_sbx'] = W(int((cr.A0_sbx & cr.A2_sbx).sum()), int(cr.A0_sbx.sum()))
    ct = []
    for s, r in cr.iterrows():
        ct.append(dict(store_id=s, domain=r.domain, token_level=Cst.loc[s, 'token_level'] if s in Cst.index else None, cmp=r.cmp, banner=r.banner_A0,
                       A0_sbx=r.A0_sbx, A2_sbx=r.A2_sbx, clicked=r.clicked, after_decline_sbx=bool(r.A1post_sbx or r.A1next_sbx),
                       token_A0=s in set(tok[tok.arm == 'A0'].store_id), token_A0_vendors='|'.join(sorted(tok[(tok.arm == 'A0') & (tok.store_id == s)].vendor.unique())),
                       token_A2=s in set(tok[tok.arm == 'A2'].store_id)))
    pd.DataFrame(ct).to_csv(os.path.join(OUT, 'creator_stratum_results.csv'), index=False)
    # c: do requests after a refusal carry it? (refusal signals by vendor group and arm)
    f6['c'] = f5['flags']['by_group']
    S['fig6'] = f6

    # ------------------------------------------------------------------ Validation (moved from Fig 6c to Fig S4d)
    kk = {}
    for a, b_ in (('A0', 'A0r'), ('A2', 'A2r'), ('A2', 'V1')):
        x = st[st[f'{b_}_ok'] == True]
        x = x[x.stratum == 'main'] if b_ != 'V1' else x
        y1 = x[f'{a}_sbx'].astype(int).values
        y2 = x[f'{b_}_sbx'].astype(float).astype(int).values
        kk[f'{a}_vs_{b_}'] = kappa_boot(y1, y2, B=B, seed=SEED)
        vx = sv[sv.store_id.isin(x.index)]
        kk[f'{a}_vs_{b_}_vendor'] = kappa_boot(vx[f'{a}_sbx'].astype(int).values, vx[f'{b_}_sbx'].astype(int).values, B=B, seed=SEED,
                                               groups=vx.store_id.values)
    # request-count repeatability (review MET-30): per-store count of sandboxed ad requests, Spearman rank correlation
    # between a load and its same-day repeat, with a percentile bootstrap over stores
    from scipy.stats import spearmanr
    for a, b_ in (('A0', 'A0r'), ('A2', 'A2r')):
        ids = st[(st[f'{b_}_ok'] == True) & (st.stratum == 'main')].index
        c1 = adm[(adm.arm == a) & adm.sandbox].groupby('store_id').size().reindex(ids, fill_value=0)
        c2 = adm[(adm.arm == b_) & adm.sandbox].groupby('store_id').size().reindex(ids, fill_value=0)
        rho = float(spearmanr(c1.values, c2.values).correlation)
        rng_ = np.random.default_rng(SEED)
        bs = []
        for _ in range(B):
            ii = rng_.integers(0, len(ids), len(ids))
            x1, x2 = c1.values[ii], c2.values[ii]
            if x1.std() > 0 and x2.std() > 0:
                bs.append(spearmanr(x1, x2).correlation)
        kk[f'{a}_vs_{b_}_count_spearman'] = dict(rho=rho, lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)), n=int(len(ids)),
                                                 n_nonzero_either=int(((c1 > 0) | (c2 > 0)).sum()), median_count_a=float(c1[c1 > 0].median()),
                                                 median_abs_diff_nonzero=float((c1 - c2).abs()[(c1 > 0) | (c2 > 0)].median()))
        # referee 2, m6 (text pass): most stores have zero requests in both loads, so rho over all stores is dominated by tied zeros;
        # report it also among stores positive in both loads, with a percentile bootstrap over those stores
        pos = ((c1 > 0) & (c2 > 0)).values
        p1_, p2_ = c1.values[pos], c2.values[pos]
        rng_ = np.random.default_rng(SEED)
        bs = []
        for _ in range(B):
            ii = rng_.integers(0, len(p1_), len(p1_))
            if p1_[ii].std() > 0 and p2_[ii].std() > 0:
                bs.append(spearmanr(p1_[ii], p2_[ii]).correlation)
        kk[f'{a}_vs_{b_}_count_spearman']['zero_both'] = int(((c1 == 0) & (c2 == 0)).sum())
        kk[f'{a}_vs_{b_}_count_spearman_pos'] = dict(rho=float(spearmanr(p1_, p2_).correlation), lo=float(np.percentile(bs, 2.5)),
                                                     hi=float(np.percentile(bs, 97.5)), n=int(pos.sum()),
                                                     note='stores with at least one sandboxed ad request in both loads')
    # discriminating power of the Brave check (review MET-22): stores / store-vendor pairs where Default and GPC differ
    xv = st[st['V1_ok'] == True]
    d_ = xv[xv.A0_sbx.astype(bool) != xv.A2_sbx.astype(bool)]
    vx_ = sv[sv.store_id.isin(xv.index)]
    dv_ = vx_[vx_.A0_sbx.astype(bool) != vx_.A2_sbx.astype(bool)]
    kk['brave_power'] = dict(n_stores=int(len(xv)), stores_default_gpc_differ=int(len(d_)),
                             stores_brave_matches_gpc=int((d_.V1_sbx.astype(float).astype(bool) == d_.A2_sbx.astype(bool)).sum()),
                             n_pairs=int(len(vx_)), pairs_default_gpc_differ=int(len(dv_)),
                             pairs_brave_matches_gpc=int((dv_.V1_sbx.astype(float).astype(bool) == dv_.A2_sbx.astype(bool)).sum()),
                             stratum=sorted(xv.stratum.unique().tolist()))
    S['validation'] = kk
    pd.DataFrame([dict(pair=k, **v) for k, v in kk.items() if 'kappa' in v]).to_csv(os.path.join(OUT, 'figS4_kappa.csv'), index=False)

    # ------------------------------------------------------------------ Supplementary
    E = {b: v['est_eligible_in_frame'] for b, v in funnel['per_bucket'].items()}
    fpc_N = {b: v['flagged_N'] for b, v in funnel['per_bucket'].items()}
    S['supp'] = supplementary(m, clk, clk_all, svm, adm, st, grants, E, fpc_N, newp)
    # referee 2, m1 (text pass): the concurrency segments compared with a difference and its interval, and the approximate
    # difference the comparison could detect (80% power, two-sided 5% level, pooled proportion; normal approximation)
    from scipy.stats import norm as _norm
    zz = _norm.ppf(0.975) + _norm.ppf(0.80)
    s6_ = pd.DataFrame(S['supp']['S6'])
    segd = {}

    def _seg(k1, n1, k2, n2):
        r = newcombe_indep(k1, n1, k2, n2)
        pb = (k1 + k2) / (n1 + n2)
        r['mdd80'] = float(zz * np.sqrt(pb * (1 - pb) * (1 / n1 + 1 / n2)))
        return r
    for oc_ in ('prechoice_sbx_banner', 'decline_residual', 'gpc_residual'):
        r6 = s6_[(s6_.outcome == oc_) & (s6_.variant == 'crawl run at 6 browsers')].iloc[0]
        r10 = s6_[(s6_.outcome == oc_) & (s6_.variant == 'crawl run at 10 browsers')].iloc[0]
        segd[oc_] = _seg(int(r6.k), int(r6.n), int(r10.k), int(r10.n))
    b6, b10 = S['fig3']['b']['segment_conc6_before'], S['fig3']['b']['segment_conc10_before']
    segd['first_request_before_banner'] = _seg(b6['k'], b6['n'], b10['k'], b10['n'])
    segd['race_deny'] = S['fig5']['d']['deny']['by_segment']
    segd['mdd_max'] = max(v['mdd80'] for v in segd.values() if isinstance(v, dict) and 'mdd80' in v)
    segd['mdd_min'] = min(v['mdd80'] for v in segd.values() if isinstance(v, dict) and 'mdd80' in v)
    segd['power'], segd['alpha'] = 0.80, 0.05
    segd['note'] = ('6-browser minus 10-browser segment; Newcombe hybrid-score interval; mdd80: approximate difference detectable with 80% power '
                    'at the two-sided 5% level (pooled proportion, normal approximation)')
    S['supp']['S6_segments'] = segd
    S['supp']['S4'] = audit_summary()
    S['creator'] = dict(n=len(cr), banner=W(int(cr.banner_A0.sum()), len(cr)), A0_sbx=W(int(cr.A0_sbx.sum()), len(cr)),
                        clicked=int(cr.clicked.sum()), after_decline=W(int((cr.clicked & (cr.A1post_sbx | cr.A1next_sbx)).sum()), int(cr.clicked.sum())),
                        gpc_residual=W(int((cr.A0_sbx & cr.A2_sbx).sum()), int(cr.A0_sbx.sum())))
    fb = json.load(open(os.path.join(CRAWL, 'failure_breakdown.json')))
    gl = json.load(open(os.path.join(CRAWL, 'validation', 'gpc_live_summary.json')))
    S['context'] = dict(
        region_optout=int((m.region_optout == True).sum()), region_optin=int((m.region_optout == False).sum()),
        region_unknown=int(m.region_optout.isna().sum()),
        region_optout_share=W(int((m.region_optout == True).sum()), int(m.region_optout.notna().sum())),
        gpc_header_sale_declined=W(int((m.A2_header_sale_declined == True).sum()), len(m)),
        gpc_cp_sale_denied=W(int((m.cp_sale_end_A2 == False).sum()), int(m.cp_sale_end_A2.notna().sum())),
        v1_cp_sale_denied=summ['v1_shopify_saleOfData_denied'],
        strict_workers_A2=gl['A2']['strict_workers'], strict_workers_A2_injected=gl['A2']['strict_workers_inject_state_ok'],
        strict_workers_A2_gpc_undefined=gl['A2']['strict_workers_gpc_undefined'], strict_workers_V1=gl['V1']['strict_workers'],
        strict_workers_V1_gpc_undefined=gl['V1']['strict_workers_gpc_undefined'], lax_frames_A2_true=gl['A2']['lax_sandbox_frames_gpc_True'],
        lax_frames_A2=gl['A2']['lax_sandbox_frames'], worker_req_sec_gpc=gl['A2']['req_worker_sec_gpc_1'],
        failed_loads=fb['not_ok_loads'], failed_stores=fb['not_ok_stores_any_arm'], failed_by_reason=fb['not_ok_by_reason'],
        blocked_like_stores=fb['blocked_like_stores(http_403/429/503 or off-site redirect or bot wall)'],
        loads_conc6=fb['status_log_lines_by_segment']['conc6_first_segment'], loads_conc10=fb['status_log_lines_by_segment']['conc10_coordinator_segment'],
        loads_retry=fb['status_log_lines_by_segment']['conc6_retry_pass'], retried_ok=fb['retried_ok_now'],
        nostra_stores=int((m.nostra == True).sum()), cf_hit_stores=int((m.cf_cache_A0 == 'HIT').sum()),
        a0_any_ad=W(int(m.A0_any.sum()), len(m)), a2_any_given_a0_any=W(int((m.A0_any & m.A2_any).sum()), int(m.A0_any.sum())),
        store_c_header=str(L[(L.store_id == 'C005') & (L.arm == 'A0')].cmp_header_raw.iloc[0])[:16],
        repeat_main_ok=int(((st.A0r_ok == True) & (st.stratum == 'main')).sum()), brave_ok=int((st.V1_ok == True).sum()))
    # referee 1, m5 (text pass): the GPC navigation's consent string by its sale-of-data-region field (4th field of the v3 string,
    # notes/mechanism.md 2.4): does Shopify decline sale of data only where that field is set?
    a2l = L[(L.arm == 'A2') & L.store_id.isin(m.index) & L.ok & L.cmp_allow_s.notna() & L.cmp_sod_region.notna()]
    sodr = a2l.cmp_sod_region.astype(str) == 'True'
    alls = a2l.cmp_allow_s.astype(str) == 'True'
    S['context']['gpc_sale_by_sod_region'] = dict(
        field_unset=W(int((~sodr & ~alls).sum()), int((~sodr).sum())), field_set=W(int((sodr & ~alls).sum()), int(sodr.sum())),
        n_loads=int(len(a2l)), note="GPC loads of captured main-sample stores; k = the navigation's consent string declined sale of data")
    # ------------------------------------------------------------------ Ethics sensitivity (review COORD-01, AUD-04)
    S['ethics_sensitivity'] = ethics_sensitivity(m, cr, st, clk, clk_all, set(newp.store_id), SC, L, PX, grants, blk_st, decl_vendor_sbx, tok)
    S['crosscheck'] = dict(
        banner=(f1['banner']['k'], summ['main']['A0_banner_visible']['k']),
        banner_sbx=(int((m.banner_A0 & m.A0_sbx).sum()), summ['main']['A0_banner_stores_sandboxed_ad_request_prechoice']['k']),
        clicked=(len(clk_all), summ['main']['A1_clicked']),
        next_sbx=(int(clk_all.A1next_sbx.sum()), summ['main']['A1_clicked_sandboxed_ad_next_page']['k']),
        gpc_resid=(int((m.A0_sbx & m.A2_sbx).sum()), summ['main']['A2_given_A0_sandboxed_ad_still_sandboxed_ad']['k']),
        gpc_base=(int(m.A0_sbx.sum()), summ['main']['A2_given_A0_sandboxed_ad_still_sandboxed_ad']['n']))
    S['crosscheck_ok'] = all(a == b for a, b in S['crosscheck'].values())
    dump(S, 'stats.json')
    json.dump(dict(captured_all_arms=int(len(m)), captured_creator=int(len(cr)), repeat_planned=S['design']['repeat_planned'],
                   repeat_main_ok=S['context']['repeat_main_ok'], brave_planned=S['design']['brave_planned'], brave_ok=S['context']['brave_ok'],
                   funnel_excl=S['design']['funnel_excl'],
                   source='analysis/analyze.py (stores with an ok load in A0, A1 and A2)'),
              open(os.path.join(os.path.dirname(OUT), 'crawl_funnel.json'), 'w'), indent=1)
    print('crosscheck', S['crosscheck'], S['crosscheck_ok'])


PURP_KEY = {'ANALYTICS': 'a', 'MARKETING': 'm', 'PREFERENCES': 'p', 'SALE_OF_DATA': 's'}
CS_COL = {'a': 'analyticsProcessingAllowed', 'm': 'marketingAllowed', 'p': 'preferencesProcessingAllowed', 's': 'saleOfDataAllowed'}


def _tb(v):
    return {'True': True, 'False': False, 'true': True, 'false': False}.get(str(v)) if not isinstance(v, (bool, np.bool_)) else bool(v)


def residual_composition(dd, gdeny, adm, newp, oldp, SC, L):
    """Which pixels carry the residual traffic after a refusal (referee 1, M3; referee 2, S3; added 2026-09-26).
    Every residual sandboxed ad request is classified by the purposes its pixel declares and by Shopify's state at the
    time: 'refused' = the pixel declares a purpose that the state denied (for Decline, marketing, which a recorded
    refusal always denies); 'left_allowed' = it declares purposes, all of which the state still allowed (for Decline,
    typically sale of data, which many CMPs do not refuse on Decline; under GPC, marketing or analytics, which Shopify's
    GPC mapping leaves allowed); 'none' = it declares no purpose, so no choice can gate it; 'unmatched' = no pixel
    configuration. State: for new sandboxes, the state when the sandbox started (gate audit, sandbox_creations.csv);
    for pixels started before the click (same page, and unload beacons as the page reloads), the last Customer Privacy
    API reading after the click on the first page.
      dd     stores with a working Decline click and a recorded refusal; gdeny  stores where GPC set 'sale of data: no'"""
    out = {}
    Lx = L.set_index('load_id')
    cs = pd.read_csv(os.path.join(CRAWL, 'consent_states.csv'), low_memory=False)
    cs = cs[(cs.arm == 'A1') & cs.store_id.isin(dd.index) & (cs.has_cp == True) & cs.error.isna()]
    cs = cs.merge(dd[['t_click']], left_on='store_id', right_index=True)
    cs['t_next'] = cs.load_id.map(Lx.t_next_nav)
    first = cs[(cs.t_ms >= cs.t_click) & (cs.t_next.isna() | (cs.t_ms < cs.t_next))]
    last1 = first.sort_values('t_ms').groupby('store_id').last()
    post_state = {s_: {k: _tb(r[c]) for k, c in CS_COL.items()} for s_, r in last1.iterrows()}
    after = cs[cs.t_ms >= cs.t_click].sort_values('t_ms').groupby('store_id').last()
    sod = after.saleOfDataAllowed.map(_tb)
    out['decline_sale_after_refusal'] = dict(n=int(len(dd)), with_reading=int(len(after)), sale_allowed=W(int((sod == True).sum()), int(len(after))),
                                             sale_denied=int((sod == False).sum()),
                                             sale_region_flag=int(after.saleOfDataRegion.map(_tb).eq(True).sum()))
    SCi = SC.assign(pid=SC.pixel_id.map(pid_str)).drop_duplicates(['load_id', 'pid']).set_index(['load_id', 'pid'])

    def classify(purposes, state):
        pp = [PURP_KEY[x] for x in str(purposes).split('|') if x in PURP_KEY]
        if not isinstance(purposes, str) or purposes in ('', 'nan', 'UNMATCHED'):
            return 'unmatched'
        if purposes == 'NONE' or not pp:
            return 'none'
        if state is None:
            return 'state_unknown'
        if any(state.get(p) is False for p in pp):
            return 'refused'
        return 'left_allowed'

    def sc_state(lid, pid):
        k = (lid, pid_str(pid))
        if k not in SCi.index:
            return None
        r = SCi.loc[k]
        st_ = {p: _tb(r[f'st_{p}']) for p in 'amps'}
        return None if all(v is None for v in st_.values()) else st_
    rows = []
    post = adm[(adm.cond == 'A1post') & adm.sandbox & adm.store_id.isin(dd.index)]
    for r in post.itertuples():
        rows.append(dict(window='same_page', store_id=r.store_id, pixel_type=r.pixel_type, purposes=r.pixel_purposes,
                         mkt=bool(r.decl_mkt), cat=classify(r.pixel_purposes, post_state.get(r.store_id))))
    for r in oldp[oldp.store_id.isin(dd.index)].itertuples():
        rows.append(dict(window='unload', store_id=r.store_id, pixel_type=r.pixel_type, purposes=r.pixel_purposes, vendor=r.vendor,
                         mkt='MARKETING' in str(r.pixel_purposes), cat=classify(r.pixel_purposes, post_state.get(r.store_id))))
    for r in newp[newp.store_id.isin(dd.index)].itertuples():
        rows.append(dict(window='fresh_page', store_id=r.store_id, pixel_type=r.pixel_type, purposes=r.pixel_purposes,
                         mkt='MARKETING' in str(r.pixel_purposes), cat=classify(r.pixel_purposes, sc_state(r.load_id, r.pixel_id))))
    D = pd.DataFrame(rows)
    D['arm'] = 'Decline'
    # GPC: Shopify maps GPC to 'sale of data: no' only, so the refused purpose is sale of data; other declared purposes
    # are left allowed by that mapping (the state-based class is kept as cat_state: it differs only on edge-cached pages)
    g2 = adm[(adm.cond == 'A2') & adm.sandbox & adm.store_id.isin(gdeny.index)]
    rows = []
    for r in g2.itertuples():
        pp_ = str(r.pixel_purposes)
        cat_ = ('unmatched' if pp_ in ('', 'nan') else 'none' if pp_ == 'NONE' else 'refused' if 'SALE_OF_DATA' in pp_ else 'left_allowed')
        rows.append(dict(window='gpc_load', store_id=r.store_id, pixel_type=r.pixel_type, purposes=r.pixel_purposes, arm='GPC',
                         mkt=bool(r.decl_mkt), sale=bool(r.decl_sale), cat=cat_, cat_state=classify(r.pixel_purposes, sc_state(r.load_id, r.pixel_id))))
    G = pd.DataFrame(rows)
    pd.concat([D, G], ignore_index=True).to_csv(os.path.join(OUT, 'residual_composition.csv'), index=False)
    nD, nG = len(dd), len(gdeny)

    def stores(x):
        return set(x.store_id)
    dec = {}
    for w_ in ('same_page', 'unload', 'fresh_page'):
        x = D[D.window == w_]
        dec[w_] = dict(any=W(len(stores(x)), nD), **{c: W(len(stores(x[x.cat == c])), nD) for c in ('refused', 'left_allowed', 'none', 'unmatched', 'state_unknown')},
                       mkt=W(len(stores(x[x.mkt])), nD), not_mkt=W(len(stores(x[~x.mkt])), nD),
                       by_type={f'{t}_{c}': int(x[(x.pixel_type == t) & (x.cat == c)].store_id.nunique()) for t in ('APP', 'CUSTOM') for c in ('none', 'left_allowed', 'refused')},
                       left_allowed_purposes={k: int(v) for k, v in x[x.cat == 'left_allowed'].groupby('purposes').store_id.nunique().items()},
                       custom_any=int(x[x.pixel_type == 'CUSTOM'].store_id.nunique()), app_any=int(x[x.pixel_type == 'APP'].store_id.nunique()))
    x = D[D.window == 'unload']
    dec['unload']['mkt_vendors_requests'] = {k: int(v) for k, v in x[x.mkt].vendor.value_counts().items()}
    # the failure classes of the paper, per store: F3 = a pixel that declares the refused purpose kept sending (same page
    # or unload beacon, i.e. started before the choice), F3i = an incomplete refusal (the pixel declares only purposes
    # the CMP's Decline left allowed), F4 = the pixel declares no purpose (under-declaration: ungatable by any choice)
    f3 = stores(D[D.window.isin(['same_page', 'unload']) & (D.cat == 'refused')])
    f3i = stores(D[D.cat == 'left_allowed'])
    f4 = stores(D[D.cat == 'none'])
    notmkt = stores(D[~D.mkt])
    f3m = stores(D[D.window.isin(['same_page', 'unload']) & D.mkt])   # referee 2's rule: marketing-declaring pixels only
    dec['classes_mkt'] = dict(f3=len(f3m), not_mkt_any_window=len(notmkt), both=len(f3m & notmkt), union=len(f3m | notmkt))
    dec['classes'] = dict(n=nD, f3=len(f3), f3_incomplete=len(f3i), f4_no_purpose=len(f4), f3_and_f4=len(f3 & (f3i | f4)),
                          not_mkt_any_window=len(notmkt), f3_and_not_mkt=len(f3 & notmkt), union=len(f3 | f3i | f4),
                          fresh_refused=len(stores(D[(D.window == 'fresh_page') & (D.cat == 'refused')])),
                          f3_samepage_only=len(stores(D[(D.window == 'same_page') & (D.cat == 'refused')])))
    out['decline'] = dec
    gp = dict(any=W(len(stores(G)), nG), **{c: W(len(stores(G[G.cat == c])), nG) for c in ('refused', 'left_allowed', 'none', 'unmatched', 'state_unknown')},
              sale=W(len(stores(G[G.sale])), nG), left_allowed_mkt=W(len(stores(G[(G.cat == 'left_allowed') & G.mkt])), nG),
              left_allowed_other=W(len(stores(G[(G.cat == 'left_allowed') & ~G.mkt])), nG))
    ty = G.groupby('store_id').pixel_type.apply(lambda s_: '+'.join(sorted(set(s_.dropna()) & {'APP', 'CUSTOM'})) or 'unknown')
    gp['stores_by_type'] = {k: int(v) for k, v in ty.value_counts().items()}
    gp['left_allowed_purposes'] = {k: int(v) for k, v in G[G.cat == 'left_allowed'].groupby('purposes').store_id.nunique().items()}
    gp['by_type'] = {f'{t}_{c}': int(G[(G.pixel_type == t) & (G.cat == c)].store_id.nunique()) for t in ('APP', 'CUSTOM') for c in ('none', 'left_allowed', 'refused')}
    gp['state_refused'] = dict(stores=sorted(stores(G[G.cat_state == 'refused'])), note='declared purpose denied at start; edge-cached consent string')
    out['gpc'] = gp
    return out


AUTOMATION_TERMS = re.compile(r'webdriver|HeadlessChrome|headlesschrome|Playwright/|isBot|isUserBot|isSpider|botsFriendly|X-OneTrust-IsBot|Googlebot', re.I)
MATCHES_OUR_CRAWLER = re.compile(r'HeadlessChrome|headlesschrome|navigator\.webdriver|Playwright/')


def automation(L, st, m, cr, CE, grants, adm):
    """What the pages could see of our crawler, and which consent tools react to it (referee 1, M1 and m6; added
    2026-09-26). Reads outputs/load_probe.csv and worker_pauses.csv (extract_probe.py), the saved CMP code in
    crawl/static_mechanism/cmp_code, consent_events.csv and loads.csv.
      fingerprint     navigator.webdriver and a 'HeadlessChrome' user agent, per browser, loads with a page probe
      pandectes_bot   the signature of Pandectes v5's bot rule (core code: botsFriendly and (navigator.webdriver or a
                      HeadlessChrome UA) -> 'hide_allow' -> consent 'allow', reason 'bot'): v5 banner configured
                      visible for California, banner element present but hidden, and a 'marketing: yes' write in a
                      load without any click; contrast = same strict-California configuration, banner shown, no write
      scroll_yes      'yes' writes without a click that came within 1 s after one of our passive scrolls
      yes_writes      Default 'yes' writes that switched a denying default (automatic grants): with and without a
                      detected banner, and how many match the bot rule
      static_scan     automation-sensitive terms in the saved CMP code (as review/referee1_evidence/cmp_bot_rules.py)
      detection       per consent product (Default, main sample): stores detected, banner visible, banner element hidden
      worker_pause    time each worker waited for the instrumentation (waitForDebuggerOnStart): auto-attach to resume"""
    out = {}
    P = pd.read_csv(os.path.join(OUT, 'load_probe.csv'), low_memory=False)
    okl = L[L.ok & L.store_id.isin(st.index)]
    Pk = P[P.load_id.isin(okl.load_id) & (P.has_probe == True)]
    fp = {}
    for b, g in Pk.groupby('browser'):
        fp[b] = dict(loads=int(len(g)), webdriver=int((g.webdriver == True).sum()), headless_ua=int((g.ua_headlesschrome == True).sum()))
    out['fingerprint'] = dict(by_browser=fp, loads=int(len(Pk)), webdriver=int((Pk.webdriver == True).sum()),
                              headless_ua=int((Pk.ua_headlesschrome == True).sum()), loads_without_probe=int(okl.load_id.isin(P[P.has_probe != True].load_id).sum()))
    # 'yes' writes per load (A0 and A2 loads have no click; the Decline arm is excluded)
    ce = CE[CE.load_id.isin(okl.load_id)]
    yes_l = set(ce[ce.detail.str.contains('"marketingAllowed":true')].load_id)
    p5 = Pk[(Pk.pandectes_v5 == True) & Pk.arm.isin(['A0', 'A2'])].copy()
    p5['yes'] = p5.load_id.isin(yes_l)
    sig = p5[(p5.p5_visible_here == True) & (p5.pandectes_dom == 'present_hidden') & p5.yes]
    con = p5[(p5.p5_visible_here == True) & (p5.p5_ca_strict == True) & (p5.pandectes_dom == 'visible') & ~p5.yes]
    bot = sorted(sig.store_id.unique())
    out['pandectes_bot'] = dict(v5_loads=int(len(p5)), v5_stores=int(p5.store_id.nunique()),
                                v5_loads_webdriver=int((p5.webdriver == True).sum()), v5_loads_headless_ua=int((p5.ua_headlesschrome == True).sum()),
                                signature_loads=int(len(sig)), signature_arms={a: int(v) for a, v in sig.arm.value_counts().items()},
                                stores=bot, n_stores=len(bot), stores_both_arms=sorted(s_ for s_, g in sig.groupby('store_id') if g.arm.nunique() == 2),
                                stores_ca_strict=sorted(sig[sig.p5_ca_strict == True].store_id.unique()),
                                contrast_stores=sorted(con.store_id.unique()), n_contrast_stores=int(con.store_id.nunique()),
                                contrast_stores_both_arms=sorted(s_ for s_, g in con.groupby('store_id') if g.arm.nunique() == 2),
                                region_denied=int((st.loc[bot].region_optout == False).sum()) if bot else 0,
                                main=sorted(set(bot) & set(m.index)), creator=sorted(set(bot) & set(cr.index)))
    # 'yes' writes after a passive scroll (scrolls at 2, 3, ..., 7 s after the load event; A0 only)
    Lx = okl.set_index('load_id')
    first_yes = ce[ce.detail.str.contains('"marketingAllowed":true')].groupby('load_id').t_ms.min()
    rows = []
    for lid, t in first_yes.items():
        if lid not in Lx.index or Lx.loc[lid, 'arm'] not in ('A0', 'A2') or pd.isna(Lx.loc[lid, 't_load']):
            continue
        sc = [Lx.loc[lid, 't_load'] + 2000 + 1000 * j for j in range(6)]
        prev = [s_ for s_ in sc if s_ <= t]
        rows.append(dict(load_id=lid, store_id=Lx.loc[lid, 'store_id'], arm=Lx.loc[lid, 'arm'], t=t, after_scroll=bool(prev),
                         lag=float(t - prev[-1]) if prev else None))
    Y = pd.DataFrame(rows)
    Ym = Y[Y.store_id.isin(m.index)]
    ys = Ym[Ym.after_scroll]
    out['scroll_yes'] = dict(loads_with_yes=int(len(Ym)), stores_with_yes=int(Ym.store_id.nunique()),
                             before_first_scroll=int((~Ym.after_scroll).sum()), after_a_scroll=int(Ym.after_scroll.sum()),
                             after_scroll_stores=sorted(ys.store_id.unique()), n_after_scroll_stores=int(ys.store_id.nunique()),
                             lag_after_last_scroll_ms=[float(v) for v in ys.lag],
                             lag_min_ms=float(ys.lag.min()) if len(ys) else None, lag_max_ms=float(ys.lag.max()) if len(ys) else None,
                             by_cmp={c: int(v) for c, v in m.loc[ys.store_id.unique()].cmp.value_counts().items()} if len(ys) else {})
    # Default automatic grants (a 'yes' write that switched a denying default): banner or not, bot rule or not
    g0 = grants[(grants.arm == 'A0') & (grants.m_change == 'grant') & grants.store_id.isin(m.index)]
    gs = sorted(g0.store_id.unique())
    nob = [s_ for s_ in gs if not m.loc[s_, 'banner_A0']]
    out['yes_writes'] = dict(auto_grant_stores=len(gs), with_banner=len(gs) - len(nob), without_banner=len(nob), without_banner_stores=nob,
                             without_banner_bot_rule=sorted(set(nob) & set(bot)), without_banner_other=sorted(set(nob) - set(bot)),
                             without_banner_other_by_cmp={c: int(v) for c, v in m.loc[sorted(set(nob) - set(bot))].cmp.value_counts().items()},
                             bot_rule=sorted(set(gs) & set(bot)), n_without_banner_bot_rule=len(set(nob) & set(bot)),
                             n_without_banner_other=len(set(nob) - set(bot)), n_bot_rule=len(set(gs) & set(bot)))
    # static scan of the saved CMP code
    cdir = os.path.join(CRAWL, 'static_mechanism', 'cmp_code')
    scan = []
    for fn in sorted(os.listdir(cdir)):
        if not fn.endswith('.js'):
            continue
        s_ = open(os.path.join(cdir, fn), errors='ignore').read()
        hits = sorted({x.group(0) for x in AUTOMATION_TERMS.finditer(s_)})
        scan.append(dict(file=fn, product=fn.split('__')[0], terms=hits, matches_our_crawler=bool(MATCHES_OUR_CRAWLER.search(s_)), size=len(s_)))
    out['static_scan'] = dict(files=len(scan), files_with_terms=sum(bool(x['terms']) for x in scan),
                              products_matching_our_crawler=sorted({x['product'] for x in scan if x['matches_our_crawler']}),
                              products_with_other_bot_logic=sorted({x['product'] for x in scan if x['terms'] and not x['matches_our_crawler']}),
                              rows=[x for x in scan if x['terms']], products_scanned=sorted({x['product'] for x in scan if x['size'] > 0}),
                              empty_files=sorted(x['file'] for x in scan if x['size'] == 0))
    # detection vs banner shown, per consent product (Default load, main sample)
    a0 = okl[(okl.arm == 'A0') & okl.store_id.isin(m.index)].merge(Pk[['load_id', 'cmp_dom']], on='load_id', how='left')
    det = {}
    for r in a0.itertuples():
        dom = json.loads(r.cmp_dom) if isinstance(r.cmp_dom, str) else {}
        for c in [x for x in str(r.cmps_detected).split('|') if x and x != 'nan']:
            d_ = det.setdefault(c, dict(detected=0, banner=0, dom_hidden=0))
            d_['detected'] += 1
            d_['banner'] += int(r.banner_visible == True and (r.banner_cmp == c or not isinstance(r.banner_cmp, str) or r.banner_cmp in ('', 'generic')))
            d_['dom_hidden'] += int(dom.get(c) == 'present_hidden')
    rows = sorted(({'cmp': c, **v} for c, v in det.items() if v['detected'] >= 5), key=lambda x: -x['detected'])
    out['detection'] = dict(rows=rows, min_detected=5, n_products=len(rows))
    pd.DataFrame(rows).to_csv(os.path.join(OUT, 'cmp_detection.csv'), index=False)
    # instrumentation pause of workers (all workers of usable loads of analysed stores)
    Wp = pd.read_csv(os.path.join(OUT, 'worker_pauses.csv'))
    Wp = Wp[Wp.load_id.isin(okl.load_id)]
    wp = {}
    for lab, g in (('all', Wp), ('strict', Wp[Wp.strict == True]), ('other', Wp[Wp.strict != True])):
        x = g.pause_ms.astype(float)
        wp[lab] = dict(n=int(len(x)), loads=int(g.load_id.nunique()), median=float(x.median()), p90=float(x.quantile(.9)), p99=float(x.quantile(.99)),
                       max=float(x.max()), over_poll=W(int((x > 250).sum()), len(x)), over_1s=int((x > 1000).sum()))
    out['worker_pause'] = wp
    return out


def ethics_flag_sets(st):
    """Stores flagged in the ethics review after the crawl (final audit, 2026-09-26):
      robots_landing  robots.txt disallowed the exact landing URL (crawl/recheck/robots/robots_eval.csv, landing == False)
      robots_home     robots.txt disallowed the homepage used in sampling (home == False)
      adult           sells adult products: the broader title screen (review/human_relabel_kit/E_broader_child_screen_BLANK.csv)
      child_flagged   a child-directed candidate noticed on a re-check screenshot (analysis/ethics_flags.csv)
      child_pending   a further candidate awaiting a human decision (analysis/ethics_flags.csv, ledger AUD-06)"""
    rb = pd.read_csv(os.path.join(CRAWL, 'recheck', 'robots', 'robots_eval.csv'))
    E = pd.read_csv(os.path.join(os.path.dirname(OUT), '..', 'review', 'human_relabel_kit', 'E_broader_child_screen_BLANK.csv'))
    fl = pd.read_csv(os.path.join(os.path.dirname(OUT), 'ethics_flags.csv'))
    sets = dict(robots_landing=sorted(rb[rb.landing == False].store_id), robots_home=sorted(rb[rb.home == False].store_id),
                adult=sorted(E[E.title.str.contains(r'\bsex dolls?\b|adult sex|adult dolls', case=False, regex=True)].store_id),
                child_flagged=sorted(fl[fl.status.str.startswith('excluded')].store_id),
                child_pending=sorted(fl[fl.status.str.startswith('human decision pending')].store_id))
    flagged = sorted(set(sets['robots_landing']) | set(sets['robots_home']) | set(sets['adult']) | set(sets['child_flagged']))
    return sets, flagged


def ethics_sensitivity(m, cr, st, clk, clk_all, fresh_set, SC, L, PX, grants, blk_st, decl_vendor_sbx, tok):
    """Headline rates recomputed without the stores flagged in the ethics review. Variants: all stores (reproduces the
    main analysis), without the 2 adult-product stores, without every flagged store, and additionally without the
    pending child-directed candidate (human decision)."""
    sets, flagged = ethics_flag_sets(st)
    analysed = set(m.index) | set(cr.index)
    out = dict(sets=sets, flagged=flagged, n_flagged=len(flagged),
               flagged_analysed_main=sorted(set(flagged) & set(m.index)), flagged_analysed_creator=sorted(set(flagged) & set(cr.index)),
               flagged_not_analysed=sorted(set(flagged) - analysed), n_flagged_not_analysed=len(set(flagged) - analysed),
               robots_home_within_landing=sorted(set(sets['robots_home']) & set(sets['robots_landing'])))
    fm = m.loc[out['flagged_analysed_main']]
    out['flagged_main_profile'] = dict(n=len(fm), banner=int(fm.banner_A0.sum()), prechoice_sbx=int(fm.A0_sbx.sum()),
                                       gpc_sbx=int((fm.A0_sbx & fm.A2_sbx).sum()), clicked_ok=int(fm.index.isin(clk.index).sum()),
                                       blocklist=int(fm.index.isin(blk_st).sum()))
    variants = dict(all=[], excl_adult=sets['adult'], excl_flagged=flagged, excl_flagged_and_pending=sorted(set(flagged) | set(sets['child_pending'])))
    tok0 = tok[tok.arm == 'A0']
    res = {}
    for name, excl in variants.items():
        ex = set(excl)
        mm = m[~m.index.isin(ex)]
        bn, nb = mm[mm.banner_A0], mm[~mm.banner_A0]
        ck = clk[~clk.index.isin(ex)]
        s0_ = mm[mm.A0_sbx]
        bl = [s_ for s_ in blk_st if s_ not in ex]
        crx = cr[~cr.index.isin(ex)]
        tk = tok0[tok0.store_id.isin(crx.index)]
        ga = gate_audit_summary(SC[~SC.store_id.isin(ex)], L, PX, grants, mm, st)
        res[name] = dict(n_excluded=len(ex), n_excluded_main=int(m.index.isin(ex).sum()), n_excluded_creator=int(cr.index.isin(ex).sum()),
                         prechoice=W(int(mm.A0_sbx.sum()), len(mm)), banner=W(int(mm.banner_A0.sum()), len(mm)),
                         banner_fires=W(int(bn.A0_sbx.sum()), len(bn)), nobanner_fires=W(int(nb.A0_sbx.sum()), len(nb)),
                         optout_fires=W(int(bn[bn.region_optout == True].A0_sbx.sum()), int((bn.region_optout == True).sum())),
                         optin_fires=W(int(bn[bn.region_optout == False].A0_sbx.sum()), int((bn.region_optout == False).sum())),
                         blocklist=W(sum(s_ in decl_vendor_sbx for s_ in bl), len(bl)),
                         decline_fresh=W(int(ck.index.isin(fresh_set).sum()), len(ck)), gpc=W(int(s0_.A2_sbx.sum()), len(s0_)),
                         gate_informative=ga['pixel_starts']['informative'], gate_gpc_sale=W(ga['gpc_sale_pixels']['k'], ga['gpc_sale_pixels']['n']),
                         gate_default_denied_held=W(ga['default_denied_mkt_pixels']['k'], ga['default_denied_mkt_pixels']['n']),
                         creator_reached=W(int(tk.store_id.nunique()), len(crx)),
                         creator_reached_nongoogle=W(int(tk[tk.vgroup != 'Google'].store_id.nunique()), len(crx)),
                         creator_reached_sandboxed=W(int(tk[tk.sandbox].store_id.nunique()), len(crx)))
    out['variants'] = res
    keys = ['prechoice', 'banner_fires', 'nobanner_fires', 'optout_fires', 'optin_fires', 'blocklist', 'decline_fresh', 'gpc']
    out['max_abs_change_pp_flagged'] = float(max(abs(res['excl_flagged'][k]['p'] - res['all'][k]['p']) for k in keys) * 100)
    out['max_abs_change_pp_flagged_and_pending'] = float(max(abs(res['excl_flagged_and_pending'][k]['p'] - res['all'][k]['p']) for k in keys) * 100)
    pd.DataFrame([dict(variant=v, measure=k, **{kk: vv for kk, vv in r[k].items()}) for v, r in res.items() for k in r if isinstance(r[k], dict)]
                 ).to_csv(os.path.join(OUT, 'ethics_sensitivity.csv'), index=False)
    return out


def config_presence(PX, adm, main_ids):
    """(store, vendor) and (store, vendor group) pairs where the store's Web Pixels configuration lists a SANDBOXED
    (STRICT/LAX) pixel of that vendor, without reference to whether it fired:
      * app pixels whose apiClientId is a known vendor app (crawl vendor column);
      * other app pixels by their apiClientId, mapped to a vendor only from OTHER stores (leave-one-store-out: on at
        least two other stores configuring the app, at least half sent sandboxed ad requests to that vendor);
      * custom pixels by their name (custom pixel code is not in the configuration).
    Also returns the pairs seen only through a sandboxed request (the old definition's extra class)."""
    vg_of_vendor = adm.drop_duplicates('vendor').set_index('vendor').vgroup.to_dict()
    vg_of_vendor.update({k: v for k, v in APP_VG.items()})
    P = PX[PX.store_id.isin(main_ids)].copy()
    P['api'] = P.apiClientId.astype(str)
    sb = P[P.runtimeContext.isin(['STRICT', 'LAX'])]
    op = P[P.runtimeContext == 'OPEN']
    cfgv, openv = set(), set()
    src = {}
    for r in sb[sb.vendor.isin(APP_VG)].itertuples():
        cfgv.add((r.store_id, r.vendor))
    old_cfg = {(s_, APP_VG[v_]) for s_, v_ in cfgv}
    src['app_vendor'] = len(cfgv)
    for r in op[op.vendor.isin(APP_VG)].itertuples():
        openv.add((r.store_id, r.vendor))
    s_req = adm[adm.sandbox & adm.pixel_api.notna()].copy()
    s_req['api'] = s_req.pixel_api.map(lambda x: str(int(float(x))) if re.fullmatch(r'[\d.]+', str(x)) else str(x))
    seen = s_req.groupby(['api', 'vendor']).store_id.apply(set).to_dict()
    vendors_of_api = s_req.groupby('api').vendor.apply(set).to_dict()
    app_stores = sb[sb.type == 'APP'].groupby('api').store_id.apply(set).to_dict()
    n0 = len(cfgv)
    for r in sb[(sb.type == 'APP') & ~sb.vendor.isin(APP_VG)].itertuples():
        others = app_stores.get(r.api, set()) - {r.store_id}
        if len(others) < 2:
            continue
        for v in vendors_of_api.get(r.api, ()):
            k = len(seen.get((r.api, v), set()) - {r.store_id})
            if k >= 2 and k / len(others) >= 0.5:
                cfgv.add((r.store_id, v))
    src['app_learned'] = len(cfgv) - n0
    n1 = len(cfgv)
    for r in sb[(sb.type == 'CUSTOM') & sb.name.notna()].itertuples():
        nm = str(r.name).lower()
        for v, rx in CUSTOM_NAME_VENDOR:
            if re.search(rx, nm):
                cfgv.add((r.store_id, v))
    src['custom_name'] = len(cfgv) - n1
    src['custom_unnamed'] = int(((sb.type == 'CUSTOM') & sb.name.isna()).sum())
    src['custom_total'] = int((sb.type == 'CUSTOM').sum())
    cfg = {(s_, vg_of_vendor.get(v_, 'Reddit/other')) for s_, v_ in cfgv}
    cfg = {(s_, g_ if g_ in VENDOR_GROUPS else 'Reddit/other') for s_, g_ in cfg}
    req = set(zip(adm[adm.sandbox].store_id, adm[adm.sandbox].vgroup))
    return dict(cfg=cfg, cfg_vendor=cfgv, cfg_open_vendor=openv, old_cfg=old_cfg, req=req, sources=src)


def gate_audit_summary(SC, L, PX, grants, m, st):
    """Revised gate audit. Denominators are configured pixels AT RISK (a declared purpose denied by the page's own
    consent string), because a creation-only audit cannot count the pixels the gate withheld."""
    out = {}
    Lx = L.set_index('load_id')
    created = set(zip(SC.load_id, SC.pixel_id.astype(str)))
    px = PX[PX.store_id.isin(m.index)].copy()
    px['pp'] = px.privacyPurposes.fillna('')
    px_by = {s_: g_ for s_, g_ in px.groupby('store_id')}
    first_grant = grants.groupby('load_id').apply(lambda g: bool(((g.m_change == 'grant') | (g.s_change == 'grant')).any()), include_groups=False).to_dict()
    SCk = SC.set_index(['load_id', 'pixel_id']).sort_index()

    def at_risk(arm, key, purpose, want):
        rows = []
        for s in m.index:
            lid = f'{s}__{arm}'
            if lid not in Lx.index or not Lx.loc[lid, 'ok']:
                continue
            hs = decode_state(Lx.loc[lid, 'cmp_header_raw'])
            if hs is None or hs.get(key) is not want:
                continue
            ps_ = px_by.get(s)
            if ps_ is None:
                continue
            for r in ps_[ps_.pp.str.contains(purpose)].itertuples():
                pid = str(r.pixel_id)
                c = (lid, pid) in created
                st_at = None
                if c:
                    v = SCk.loc[(lid, pid)]
                    v = v.iloc[0] if isinstance(v, pd.DataFrame) else v
                    st_at = v[f'st_{key}']
                rows.append(dict(load_id=lid, pid=pid, rc=r.runtimeContext, created=c, cmp_grant=first_grant.get(lid, False), state_at_creation=st_at))
        return pd.DataFrame(rows)
    g = at_risk('A2', 's', 'SALE_OF_DATA', False)
    # referee 2, S1: the entry-level zero-event bound treats entries as independent; the load (= store) level bound is
    # the one to quote (each at-risk load is one store's GPC load)
    out['gpc_sale_pixels'] = dict(W(int(g.created.sum()), len(g)), loads=int(g.load_id.nunique()), by_container={k: int(v) for k, v in g.rc.value_counts().items()},
                                  loads_with_start=W(int(g[g.created].load_id.nunique()), int(g.load_id.nunique())))
    d = at_risk('A0', 'm', 'MARKETING', False)
    dn = d[~d.cmp_grant]
    later = dn.created & (dn.state_at_creation.astype(str) == 'True')
    risk = dn[~later]
    out['default_denied_mkt_pixels'] = dict(WK(~risk.created.astype(bool), risk.load_id), started=int(risk.created.sum()), excluded_after_later_change=int(later.sum()),
                                            loads_with_start=W(int(risk[risk.created].load_id.nunique()), int(risk.load_id.nunique())),
                                            loads=int(risk.load_id.nunique()), with_cmp_grant=int(d.cmp_grant.sum()),
                                            with_cmp_grant_started=int(d[d.cmp_grant].created.sum()))
    a = at_risk('A0', 'm', 'MARKETING', True)
    out['allowed_mkt_pixels_started'] = dict(WK(a.created.astype(bool), a.load_id), loads=int(a.load_id.nunique()))
    # creation-level composition (the old denominator), renamed 'pixel starts' because OPEN scripts are included
    ga = SC[(SC.stratum == 'main') & (SC.arm.isin(['A0', 'A0r', 'A2', 'A2r', 'V1']) | ((SC.arm == 'A1') & (SC.page == 'next')))]
    viol = ga[ga.violation]
    anyden = ~(ga[['st_a', 'st_m', 'st_p', 'st_s']].astype(str).eq('True').all(axis=1))
    inf = ga[anyden & ~ga.no_purpose]
    vl = viol.groupby('load_id').first()

    def vclass(lid):
        r = Lx.loc[lid]
        reg = str(r.cmp_region)
        if r.nostra == True or r.cf_cache_status == 'HIT' or reg not in ('USCA', 'nan'):
            return 'edge_cached_header'
        if vl.loc[lid, 'state_src'] == 'event':
            return 'created_after_cmp_event'
        return 'unexplained'
    vcls = {lid: vclass(lid) for lid in vl.index}
    ex = SC[(SC.stratum == 'main') & (SC.arm == 'A1') & (SC.page == 'first')]
    out['pixel_starts'] = dict(n=len(ga), loads=int(ga.load_id.nunique()), stores=int(ga.store_id.nunique()), violations=int(ga.violation.sum()),
                               no_purpose=int(ga.no_purpose.sum()), open_scripts=int((ga.kind == 'open_main_thread_pixel').sum()),
                               all_allowed=int((~anyden).sum()), partly_denied=int(anyden.sum()),
                               informative=W(int(inf.violation.sum()), len(inf)),
                               # referee 2, S1: the flagged starts cluster in a few loads and stores; store- and load-level
                               # rates, and a store-clustered interval for the start-level ratio
                               informative_cluster=dict(WK(inf.violation.astype(bool), inf.store_id),
                                                        **{('boot_' + k): v for k, v in boot_share(inf.violation.astype(int), np.ones(len(inf)), inf.store_id).items()
                                                           if k in ('lo', 'hi')}),
                               informative_stores=W(int(inf.groupby('store_id').violation.any().sum()), int(inf.store_id.nunique())),
                               informative_loads=W(int(inf.groupby('load_id').violation.any().sum()), int(inf.load_id.nunique())),
                               informative_max_per_store=sorted([int(v) for v in inf.groupby('store_id').violation.sum() if v > 0], reverse=True),
                               violation_loads=int(viol.load_id.nunique()), violation_stores=int(viol.store_id.nunique()),
                               violation_loads_by_class={k: int(v) for k, v in pd.Series(vcls).value_counts().items()},
                               unexplained_loads=sorted([k for k, v in vcls.items() if v == 'unexplained']),
                               violation_stores_list=sorted(viol.store_id.unique().tolist()),
                               state_unknown=int(ga.state_unknown.sum()),
                               excluded_decline_first_page=dict(n=int(len(ex)), flagged=int(ex.violation.sum()), loads=int(ex[ex.violation].load_id.nunique()),
                                                                after_click=int((ex.violation & (ex.t_ms > ex.t_click)).sum())))
    return out


def refusal_signals(adm, clk, m, newp):
    """Refusal signals carried by ad requests (URL only): Google Consent Mode gcs / gcd, npa, rdp, us_privacy;
    Microsoft UET asc=D; Reddit dpm=LDU. Post-choice requests are split into flagged and unflagged."""
    out = {}
    g = adm[adm.vgroup == 'Google']
    conds = {'Default': adm.cond == 'A0', 'Decline_next': adm.cond == 'A1next', 'Decline_after': adm.cond.isin(['A1post', 'A1next']), 'GPC': adm.cond == 'A2'}
    gb = {}
    for k, sel in conds.items():
        x = g[sel.loc[g.index] & g.beacon]
        vc = x.gcs.fillna('').replace('', 'none').value_counts()
        gb[k] = dict(n=int(len(x)), stores=int(x.store_id.nunique()), none=int(vc.get('none', 0)), G100=int(vc.get('G100', 0)), G111=int(vc.get('G111', 0)),
                     G101=int(vc.get('G101', 0)), with_gcs=int((x.gcs.fillna('') != '').sum()),
                     G100_stores=int(x[x.gcs == 'G100'].store_id.nunique()), G111_stores=int(x[x.gcs == 'G111'].store_id.nunique()),
                     none_stores=int(x[x.gcs.fillna('') == ''].store_id.nunique()),
                     ad_denied=W(int(x.gcs.fillna('').str.startswith('G10').sum()), int((x.gcs.fillna('') != '').sum())))
    out['google_beacons_gcs'] = gb
    out['npa1_requests'] = {k: int(g[sel.loc[g.index]].flag_kind.fillna('').str.contains('npa').sum()) for k, sel in conds.items()}
    kinds = ['gcs_ad_denied', 'gcd_denied', 'npa', 'rdp', 'us_privacy_optout']
    out['google_flag_kinds'] = {k: dict(n=int(sel.loc[g.index].sum()), **{kk: int(g[sel.loc[g.index]].flag_kind.fillna('').str.contains(kk).sum()) for kk in kinds})
                                for k, sel in conds.items()}
    # by vendor group x arm: share of ad requests (any origin) carrying a refusal signal
    rows = []
    groups = [('Google', adm.vgroup == 'Google'), ('Microsoft', adm.vgroup == 'Microsoft'), ('Other vendors', ~adm.vgroup.isin(['Google', 'Microsoft']))]
    byg = {}
    for gname, gsel in groups:
        for arm, csel in (('Default', conds['Default']), ('Decline', conds['Decline_next']), ('GPC', conds['GPC'])):
            x = adm[gsel & csel]
            r = boot_share(x.flag_refusal.astype(int), np.ones(len(x)), x.store_id)
            byg.setdefault(gname, {})[arm] = r
            rows.append(dict(group=gname, arm=arm, origin='all', **r))
        for arm, csel in (('Default', conds['Default']), ('GPC', conds['GPC'])):
            x = adm[gsel & csel & adm.sandbox]
            r = boot_share(x.flag_refusal.astype(int), np.ones(len(x)), x.store_id)
            byg[gname][arm + '_sandboxed'] = r
            rows.append(dict(group=gname, arm=arm, origin='sandboxed', **r))
    pd.DataFrame(rows).to_csv(os.path.join(OUT, 'fig6c.csv'), index=False)
    out['by_group'] = byg
    # post-choice requests, any origin: flagged vs unflagged
    for k in ('Decline_after', 'GPC'):
        x = adm[conds[k]]
        out['post_choice_' + k] = dict(n=int(len(x)), flagged=int(x.flag_refusal.sum()), stores=int(x.store_id.nunique()),
                                       google=int((x.vgroup == 'Google').sum()), google_flagged=int(((x.vgroup == 'Google') & x.flag_refusal).sum()))
    # residual sandboxed requests: did every residual request carry a refusal signal?
    resid_d = adm[(adm.cond == 'A1next') & adm.sandbox & adm.store_id.isin(set(newp.store_id)) & adm.store_id.isin(clk.index)]
    # restrict to requests from new sandboxes: match by pixel id on the next page
    newkeys = set(zip(newp.load_id, newp.pixel_id.map(pid_str)))
    resid_d = resid_d[[(l_, pid_str(p_)) in newkeys for l_, p_ in zip(resid_d.load_id, resid_d.pixel_id)]]
    resid_g = adm[(adm.cond == 'A2') & adm.sandbox & adm.store_id.isin(m[m.A0_sbx].index)]
    for k, x in (('decline_fresh', resid_d), ('gpc', resid_g)):
        allf = x.groupby('store_id').flag_refusal.all()
        gonly = x.groupby('store_id').vgroup.apply(lambda s: (s == 'Google').all())
        out['resid_' + k] = dict(requests=int(len(x)), flagged=int(x.flag_refusal.sum()), stores=int(len(allf)), stores_all_flagged=int(allf.sum()),
                                 stores_google_only=int(gonly.sum()), stores_unflagged_nongoogle=int(x[~x.flag_refusal & (x.vgroup != 'Google')].store_id.nunique()))
    return out


def projection(m, clk, funnel, sims=20000, seed=SEED):
    """Stratified projection to the DNS-flagged Online Store storefronts of the Tranco top-200k. Rates are shares of
    ALL storefronts. Count intervals propagate both the outcome's sampling error (per bucket) and the uncertainty
    of the frame size in the randomly sampled bucket (its share of eligible storefronts among those drawn)."""
    pb = funnel['per_bucket']
    E = {b: v['est_eligible_in_frame'] for b, v in pb.items()}
    Etot = sum(E.values())
    fpc_N = {b: v['flagged_N'] for b, v in pb.items()}
    fresh_all = m.index.isin(clk[clk.fresh].index)
    outcomes = {
        'banner_and_prechoice_sbx': m.banner_A0 & m.A0_sbx,
        'banner_no_first_layer_reject': m.banner_A1 & m.no_decline_option,
        'decline_clicked_still_sbx': pd.Series(fresh_all, index=m.index),
        'gpc_still_sbx': m.A2_sbx,
        'gpc_declared_sale_pixel_fires': m.A2_sbx_decl_sale,
        'prechoice_sbx': m.A0_sbx,
        'banner': m.banner_A0,
    }
    # final-audit sensitivity: banners the detector missed but the screenshot re-check showed (crawl/recheck)
    mb_fp = os.path.join(CRAWL, 'recheck', 'missed_banner_stores.csv')
    if os.path.exists(mb_fp):
        bx = m.banner_A0 | m.index.isin(set(pd.read_csv(mb_fp).store_id))
        outcomes['banner_and_prechoice_sbx_recheck'] = bx & m.A0_sbx
        outcomes['banner_recheck'] = bx
    rng = np.random.default_rng(seed)
    out = {}
    for k, y in outcomes.items():
        y = y.astype(int)
        est = strat_est(y, m.bucket, E, fpc_N)
        if int(y.sum()) == 0:
            est['hi'] = est['hi_fpc'] = wilson(0, len(y))['hi']
            est['zero_events_wilson_upper'] = True
        cnt = np.zeros(sims)
        for b, v in pb.items():
            yy = y[m.bucket == b]
            n = len(yy)
            if n == 0:
                continue
            ph = yy.mean()
            ps = rng.normal(ph, np.sqrt(max(ph * (1 - ph), 0.25 / n) / n), sims) if ph in (0, 1) else rng.normal(ph, np.sqrt(ph * (1 - ph) / n), sims)
            ps = np.clip(ps, 0, 1)
            if v['sampling_fraction'] < 1:
                q = v['sample'] / v['drawn_n']
                qs = np.clip(rng.normal(q, np.sqrt(q * (1 - q) / v['drawn_n'] * (1 - v['drawn_n'] / v['flagged_N'])), sims), 0, 1)
                Eb = v['flagged_N'] * qs
            else:
                Eb = np.full(sims, E[b])
            cnt += Eb * ps
        est['count'] = est['p'] * Etot
        est['count_lo'] = float(np.percentile(cnt, 2.5)) if int(y.sum()) else 0.0
        est['count_hi'] = float(np.percentile(cnt, 97.5)) if int(y.sum()) else est['hi'] * Etot
        est['unweighted'] = W(int(y.sum()), len(y))
        out[k] = est
    q = pb['100k-200k']
    out['population_estimate'] = Etot
    out['frame_estimate_ci'] = dict(lo=float(sum(E[b] for b in E if b != '100k-200k') + q['flagged_N'] * wilson(q['sample'], q['drawn_n'])['lo']),
                                    hi=float(sum(E[b] for b in E if b != '100k-200k') + q['flagged_N'] * wilson(q['sample'], q['drawn_n'])['hi']))
    out['buckets'] = {b: dict(E=E[b], n_captured=int((m.bucket == b).sum())) for b in E}
    return out


def audit_summary():
    """Figure S4: crawler labels vs the visual screenshot audit (outputs/audit_sample.csv + audit_labels.csv)."""
    A = pd.read_csv(os.path.join(OUT, 'audit_sample.csv')).merge(pd.read_csv(os.path.join(os.path.dirname(OUT), 'audit_labels.csv')), on='store_id')
    o = dict(n=len(A), n_clicked=int((A.stratum == 'clicked').sum()), n_noreject=int((A.stratum == 'no_reject_option').sum()))
    o['banner_precision'] = wilson(int(A.audit_banner_visible.sum()), len(A))
    o['banner_precision_clicked'] = wilson(int(A[A.stratum == 'clicked'].audit_banner_visible.sum()), o['n_clicked'])
    o['banner_precision_noreject'] = wilson(int(A[A.stratum == 'no_reject_option'].audit_banner_visible.sum()), o['n_noreject'])
    b = A[A.audit_banner_visible == 1]
    cm = pd.crosstab(b.crawler_reject_found.astype(bool), b.audit_reject_first_layer.astype(int) == 1)
    o['reject_confusion'] = {f'crawler_{bool(i)}__audit_{bool(j)}': int(cm.loc[i, j]) if (i in cm.index and j in cm.columns) else 0
                             for i in (True, False) for j in (True, False)}
    o['reject_agreement'] = wilson(int((b.crawler_reject_found.astype(bool) == (b.audit_reject_first_layer == 1)).sum()), len(b))
    c = A[(A.stratum == 'clicked')]
    cs = c.crawler_banner_still_after_click.astype(str).str.lower() == 'true'
    gone = c.audit_banner_gone_after_click == 1
    o['click_confusion'] = dict(crawler_dismissed__audit_gone=int((~cs & gone).sum()), crawler_dismissed__audit_not_gone=int((~cs & ~gone & c.audit_banner_visible.eq(1)).sum()),
                                crawler_still__audit_gone=int((cs & gone).sum()), crawler_still__audit_not_gone=int((cs & ~gone & c.audit_banner_visible.eq(1)).sum()),
                                no_banner_in_audit=int((c.audit_banner_visible == 0).sum()))
    o['click_success_audit'] = wilson(int(gone.sum()), int((c.audit_banner_visible == 1).sum()))
    vis = c.audit_banner_visible == 1
    o['click_flag_agreement'] = wilson(int((((~cs) == gone) & vis).sum()), int(vis.sum()))
    o['clicked_without_visible_banner'] = int((c.audit_banner_visible == 0).sum())
    o['labeller'] = 'analysis assistant (AI); independent human re-labelling pending'
    rows = [dict(panel='banner', crawler='banner detected', audit='banner visible', k=int(A.audit_banner_visible.sum())),
            dict(panel='banner', crawler='banner detected', audit='no banner visible', k=int((A.audit_banner_visible == 0).sum()))]
    for key, v in o['reject_confusion'].items():
        cr_, au_ = key.split('__')
        rows.append(dict(panel='reject', crawler='reject found' if cr_.endswith('True') else 'no reject found',
                         audit='reject visible' if au_.endswith('True') else 'no reject visible', k=v))
    cc = o['click_confusion']
    rows += [dict(panel='click', crawler='banner dismissed', audit='banner gone', k=cc['crawler_dismissed__audit_gone']),
             dict(panel='click', crawler='banner dismissed', audit='banner still shown', k=cc['crawler_dismissed__audit_not_gone']),
             dict(panel='click', crawler='banner still shown', audit='banner gone', k=cc['crawler_still__audit_gone']),
             dict(panel='click', crawler='banner still shown', audit='banner still shown', k=cc['crawler_still__audit_not_gone'])]
    pd.DataFrame(rows).to_csv(os.path.join(OUT, 'figS4.csv'), index=False)
    return o


def strat_est(y, bucket, E, N):
    """Stratified (Tranco bucket) estimate of a proportion of ALL storefronts. Primary CI treats stores as a sample
    from a super-population (no finite-population correction); ci_fpc applies the FPC of each bucket."""
    Etot = sum(E.values())
    p = v = vf = 0.0
    for b, Eb in E.items():
        yy = y[bucket == b]
        n = len(yy)
        if n == 0:
            continue
        ph = yy.mean()
        Wh = Eb / Etot
        p += Wh * ph
        s2 = ph * (1 - ph) * n / (n - 1) if n > 1 else 0
        v += Wh ** 2 * s2 / n
        fpc = max(0.0, 1 - n / Eb) if Eb >= n else 0.0
        vf += Wh ** 2 * s2 / n * fpc
    se, sef = np.sqrt(v), np.sqrt(vf)
    return dict(p=float(p), lo=float(max(0, p - 1.96 * se)), hi=float(min(1, p + 1.96 * se)), lo_fpc=float(max(0, p - 1.96 * sef)),
                hi_fpc=float(min(1, p + 1.96 * sef)), se=float(se))


def strat_ratio(y, x, bucket, E):
    """Stratified ratio estimator of a CONDITIONAL rate: sum_h w_h sum y / sum_h w_h sum x (w_h = E_h / n_h), with a
    linearisation variance (no finite-population correction)."""
    Yt = Xt = 0.0
    parts = {}
    for b, Eb in E.items():
        sel = bucket == b
        n = int(sel.sum())
        if n == 0:
            continue
        w = Eb / n
        Yt += w * y[sel].sum()
        Xt += w * x[sel].sum()
        parts[b] = (n, w, y[sel].values.astype(float), x[sel].values.astype(float))
    R = Yt / Xt
    V = 0.0
    for b, (n, w, yy, xx) in parts.items():
        z = yy - R * xx
        if n > 1:
            V += (w * n) ** 2 * z.var(ddof=1) / n
    se = np.sqrt(V) / Xt
    return dict(p=float(R), lo=float(max(0, R - 1.96 * se)), hi=float(min(1, R + 1.96 * se)), se=float(se))


def consent_changes(CE, L, st):
    """First CMP-initiated consent event per load (no click involved) with the change it made to Shopify's
    marketing / sale-of-data state relative to the navigation's _cmp default."""
    Lx = L.set_index('load_id')
    CE = CE[CE.arm.isin(['A0', 'A2', 'A0r', 'A2r', 'V1'])]
    rows = []
    for lid, g in CE.sort_values('t_ms').groupby('load_id'):
        if lid not in Lx.index:
            continue
        r0 = Lx.loc[lid]
        if r0.ok is not True and r0.ok != True:
            continue
        hdr = decode_state(r0.cmp_header_raw) or {}
        dd = json.loads(g.iloc[0].detail)
        m0, s0 = hdr.get('m'), hdr.get('s')
        m1, s1 = dd.get('marketingAllowed'), dd.get('saleOfDataAllowed')
        mc = 'grant' if (m0 is False and m1 is True) else ('deny' if (m0 is not False and m1 is False) else 'none')
        sc = 'grant' if (s0 is False and s1 is True) else ('deny' if (s0 is not False and s1 is False) else 'none')
        t_load = r0.t_load if pd.notna(r0.t_load) else np.nan
        rows.append(dict(load_id=lid, store_id=r0.store_id, stratum=r0.stratum, arm=r0.arm, t_ev=float(g.iloc[0].t_ms), m0=m0, m1=m1, s0=s0, s1=s1,
                         m_change=mc, s_change=sc, n_events=len(g), t_first_scroll=t_load + 2000 if pd.notna(t_load) else np.nan))
    G = pd.DataFrame(rows)
    G = G[G.store_id.isin(st.index)]
    G.to_csv(os.path.join(OUT, 'consent_changes.csv'), index=False)
    return G


def summarize_changes(G, m, cr, L):
    x = G[(G.arm == 'A0') & G.store_id.isin(m.index)]
    out = dict(A0_loads_with_event=int(len(x)), A0_grant_m=int((x.m_change == 'grant').sum()), A0_deny_m=int((x.m_change == 'deny').sum()),
               A0_grant_m_before_first_scroll=int(((x.m_change == 'grant') & (x.t_ev < x.t_first_scroll)).sum()),
               A0_deny_m_before_first_scroll=int(((x.m_change == 'deny') & (x.t_ev < x.t_first_scroll)).sum()),
               A0_grant_by_cmp={c: int(v) for c, v in m.loc[x[x.m_change == 'grant'].store_id].cmp.value_counts().items()},
               A0_deny_by_cmp={c: int(v) for c, v in m.loc[x[x.m_change == 'deny'].store_id].cmp.value_counts().items()},
               A0_grant_banner=int(m.loc[x[x.m_change == 'grant'].store_id].banner_A0.sum()),
               A0_grant_optin=int((m.loc[x[x.m_change == 'grant'].store_id].region_optout == False).sum()))
    x2 = G[(G.arm == 'A2') & G.store_id.isin(m.index)]
    out.update(A2_loads_with_event=int(len(x2)), A2_deny_m=int((x2.m_change == 'deny').sum()), A2_grant_m=int((x2.m_change == 'grant').sum()))
    out['A0_grant_share_of_optin'] = wilson(out['A0_grant_optin'], int((m.region_optout == False).sum()))
    return out


def supplementary(m, clk, clk_all, svm, adm, st, grants, E, fpc_N, newp):
    sp = {}
    fresh_set = set(newp.store_id)
    # S2: per CMP (banner stores); rows = CMP products with >= 5 banner stores in A0 or A1
    rows = []
    b = m[m.banner_A0 | m.banner_A1]
    cm = b.cmp.value_counts()
    cmps = [c for c in cm.index if cm[c] >= 5 and c not in ('none', 'generic', 'multiple')]
    g0 = grants[grants.arm == 'A0']
    for c in cmps + ['other']:
        x = b[b.cmp == c] if c != 'other' else b[~b.cmp.isin(cmps)]
        xc = x[x.click_ok.astype(bool)]
        xs = m[(m.cmp == c) if c != 'other' else ~m.cmp.isin(cmps)]
        xa = x[x.banner_A0]   # Default-load banner stores (review CE-22: 'Banners' and the default column use the Default load)
        r = dict(cmp=c, n_banner=len(xa), n_banner_any_arm=len(x), mode=x.cmp_mode.mode().iloc[0] if len(x) else '',
                 prechoice_sbx=W(int((x.banner_A0 & x.A0_sbx).sum()), int(x.banner_A0.sum())),
                 reject_first_layer=W(int((x.banner_A1 & ~x.no_decline_option).sum()), int(x.banner_A1.sum())),
                 reached=W(int((xc.refusal_cat == 'refused').sum()), len(xc)),
                 after_decline=W(int(xc.index.isin(fresh_set).sum()), len(xc)),
                 gpc_resid=W(int((xs.A0_sbx & xs.A2_sbx).sum()), int(xs.A0_sbx.sum())),
                 region_denied=W(int((xa.region_optout == False).sum()), int(xa.region_optout.notna().sum())),
                 cmp_grant=int(g0[(g0.m_change == 'grant') & g0.store_id.isin(xs.index)].store_id.nunique()),
                 cmp_deny=int(g0[(g0.m_change == 'deny') & g0.store_id.isin(xs.index)].store_id.nunique()),
                 n_stores_detected=len(xs))
        rows.append(r)
    sp['S2'] = rows
    sp['S2_totals'] = dict(n_banner=int(sum(r['n_banner'] for r in rows)), n_banner_any_arm=int(sum(r['n_banner_any_arm'] for r in rows)),
                           region_denied_k=int(sum(r['region_denied']['k'] for r in rows)), region_denied_n=int(sum(r['region_denied']['n'] for r in rows)),
                           decline_arm_only_banners=int(len(b) - int(b.banner_A0.sum())))
    flat = []
    for r in rows:
        for k in ['prechoice_sbx', 'reject_first_layer', 'reached', 'after_decline', 'gpc_resid', 'region_denied']:
            flat.append(dict(cmp=r['cmp'], n_banner=r['n_banner'], mode=r['mode'], metric=k, **r[k]))
    pd.DataFrame(flat).to_csv(os.path.join(OUT, 'figS2.csv'), index=False)
    # S3: by Tranco bucket
    rows = []
    order = ['1-10k', '10k-50k', '50k-100k', '100k-200k']
    for bk in order:
        x = m[m.bucket == bk]
        xb = x[x.banner_A0]
        xc = x[x.click_ok.astype(bool)]
        xs = x[x.A0_sbx]
        r = dict(bucket=bk, n=len(x), banner=W(int(x.banner_A0.sum()), len(x)), prechoice_sbx_banner=W(int(xb.A0_sbx.sum()), len(xb)),
                 after_decline=W(int(xc.index.isin(fresh_set).sum()), len(xc)), gpc_resid=W(int(xs.A2_sbx.sum()), len(xs)),
                 prechoice_sbx=W(int(x.A0_sbx.sum()), len(x)))
        rows.append(r)
    sp['S3'] = rows
    bn = [r['banner']['p'] for r in rows if r['banner']['n'] >= 5]
    pb = [r['prechoice_sbx_banner']['p'] for r in rows if r['prechoice_sbx_banner']['n'] >= 20]
    sp['S3_banner_range'] = dict(lo=float(min(bn)), hi=float(max(bn)))
    sp['S3_prechoice_banner_range'] = dict(lo=float(min(pb)), hi=float(max(pb)))
    flat = []
    for r in rows:
        for k in ['banner', 'prechoice_sbx', 'prechoice_sbx_banner', 'after_decline', 'gpc_resid']:
            flat.append(dict(bucket=r['bucket'], metric=k, **r[k]))
    pd.DataFrame(flat).to_csv(os.path.join(OUT, 'figS3.csv'), index=False)
    # S5: per individual ad vendor (top 20 by stores in Default)
    a0 = adm[adm.cond == 'A0']
    top = a0.groupby('vendor').store_id.nunique().sort_values(ascending=False)
    fresh_pairs = set(zip(newp.store_id, newp.vendor))
    rows = []
    for v in top.index[:20]:
        s_a0 = set(a0[a0.vendor == v].store_id)
        s_a0_sbx = set(a0[(a0.vendor == v) & a0.sandbox].store_id)
        a2 = adm[(adm.cond == 'A2') & (adm.vendor == v)]
        vb = adm[(adm.vendor == v) & adm.beacon & (adm.cond == 'A0')]
        clk_v = [s for s in clk.index if s in s_a0_sbx]
        rows.append(dict(vendor=v, vgroup=a0[a0.vendor == v].vgroup.iloc[0], stores_default=len(s_a0), share_stores=len(s_a0) / len(m),
                         stores_default_sandboxed=len(s_a0_sbx), sandbox_share_requests=float(a0[a0.vendor == v].sandbox.mean()),
                         gpc_still=len(s_a0 & set(a2.store_id)), gpc_still_sbx=len(s_a0_sbx & set(a2[a2.sandbox].store_id)),
                         decline_base=len(clk_v), decline_still=sum((s, v) in fresh_pairs for s in clk_v),
                         beacons_default=len(vb), full_url_share=float(vb.has_full_url.mean()) if len(vb) else None))
    S5 = pd.DataFrame(rows)
    S5.to_csv(os.path.join(OUT, 'figS5.csv'), index=False)
    sp['S5_top_vendors'] = S5.vendor.tolist()
    sp['S5_rows'] = S5.to_dict('records')
    sp['S5_sandbox_share_min'] = dict(vendor=S5.loc[S5.sandbox_share_requests.idxmin(), 'vendor'], p=float(S5.sandbox_share_requests.min()))
    sp['S5_sandbox_share_max'] = dict(vendor=S5.loc[S5.sandbox_share_requests.idxmax(), 'vendor'], p=float(S5.sandbox_share_requests.max()))
    # S6: sensitivity analyses (each row = outcome under a variant)
    rows = []

    def add(outcome, variant, k, n, kind='robustness'):
        rows.append(dict(outcome=outcome, variant=variant, kind=kind, **W(int(k), int(n))))
    bann = m[m.banner_A0]
    add('prechoice_sbx_banner', 'main analysis', bann.A0_sbx.sum(), len(bann), 'main')
    add('prechoice_sbx_banner', 'data beacons only (no library loads)', bann.A0_sbx_beacon.sum(), len(bann), 'definition')
    add('prechoice_sbx_banner', 'beacons carrying our test code only', bann.A0_sbx_canary_beacon.sum(), len(bann), 'definition')
    add('prechoice_sbx_banner', 'any origin (not only sandbox)', bann.A0_any.sum(), len(bann), 'definition')
    for seg, lab in (('conc6', 'crawl run at 6 browsers'), ('conc10', 'crawl run at 10 browsers')):
        x = bann[bann.segment_A0 == seg]
        add('prechoice_sbx_banner', lab, x.A0_sbx.sum(), len(x))
    x = bann[(bann.nostra != True) & (bann.cf_cache_A0 != 'HIT')]
    add('prechoice_sbx_banner', 'excluding edge-cached pages', x.A0_sbx.sum(), len(x))
    x = bann[bann.cmp_region == 'USCA']
    add('prechoice_sbx_banner', 'only pages with a California consent string', x.A0_sbx.sum(), len(x))
    # Banner-detector recall (final audit, 2026-09-26): (a) add the stores on which the screenshot re-check
    # (crawl/recheck) showed a consent banner that the A0 detector had missed; (b) the audit's worst case: count every
    # Consentmo store on which Shopify's shouldShowBanner() was true in A0 as a banner store.
    mb_fp = os.path.join(CRAWL, 'recheck', 'missed_banner_stores.csv')
    missed = set(pd.read_csv(mb_fp).store_id) & set(m.index) if os.path.exists(mb_fp) else set()
    cs_ = pd.read_csv(os.path.join(CRAWL, 'consent_states.csv'), usecols=['store_id', 'arm', 'shouldShowBanner'])
    ssb_ = set(cs_[(cs_.arm == 'A0') & (cs_.shouldShowBanner.astype(str) == 'True')].store_id)
    csm = set(m[(m.cmp == 'consentmo') & m.index.isin(ssb_) & ~m.banner_A0].index)
    sens_b = {}
    for lab_, extra in (('adding banners missed by the detector (re-check)', missed),
                        ('Consentmo + shouldShowBanner() counted as banner', csm)):
        xb = m[m.banner_A0 | m.index.isin(extra)]
        xn = m[~(m.banner_A0 | m.index.isin(extra))]
        add('prechoice_sbx_banner', lab_, xb.A0_sbx.sum(), len(xb))
        sens_b[lab_] = dict(n_added=len(extra), banner=W(int(xb.A0_sbx.sum()), len(xb)), no_banner=W(int(xn.A0_sbx.sum()), len(xn)),
                            added_sbx=int(m.loc[sorted(extra)].A0_sbx.sum()) if extra else 0,
                            added_region_denied=int((m.loc[sorted(extra)].region_optout == False).sum()) if extra else 0)
    sp['S6_banner_recall'] = sens_b
    _, flagged_ = ethics_flag_sets(st)   # robots.txt, adult-product and child-directed flags (review COORD-01)
    x = bann[~bann.index.isin(flagged_)]
    add('prechoice_sbx_banner', 'excluding stores flagged in the ethics review', x.A0_sbx.sum(), len(x))
    add('decline_residual', 'main analysis (next page, fresh sandboxes)', clk.index.isin(fresh_set).sum(), len(clk), 'main')
    add('decline_residual', 'data beacons only (no library loads)',
        clk.index.isin(set(adm[(adm.cond == 'A1next') & adm.sandbox & adm.beacon].store_id) & fresh_set).sum(), len(clk), 'definition')
    add('decline_residual', 'any time after the click (same or next page)', (clk.A1post_sbx | clk.A1next_sbx).sum(), len(clk), 'definition')
    add('decline_residual', 'next page, any sandbox', clk.A1next_sbx.sum(), len(clk), 'definition')
    add('decline_residual', 'including the failed forced clicks', clk_all.index.isin(fresh_set).sum(), len(clk_all))
    for seg, lab in (('conc6', 'crawl run at 6 browsers'), ('conc10', 'crawl run at 10 browsers')):
        x = clk[clk.segment_A1 == seg]
        add('decline_residual', lab, x.index.isin(fresh_set).sum(), len(x))
    x = clk[clk.click_method == 'playwright_click']
    add('decline_residual', 'excluding all forced clicks', x.index.isin(fresh_set).sum(), len(x))
    x = clk[~clk.index.isin(flagged_)]
    add('decline_residual', 'excluding stores flagged in the ethics review', x.index.isin(fresh_set).sum(), len(x))
    s0 = m[m.A0_sbx]
    add('gpc_residual', 'main analysis', s0.A2_sbx.sum(), len(s0), 'main')
    s0b = m[m.A0_sbx_beacon]
    add('gpc_residual', 'data beacons only (no library loads)', s0b.A2_sbx_beacon.sum(), len(s0b), 'definition')
    s0c = m[m.A0_sbx_canary_beacon]
    add('gpc_residual', 'beacons carrying our test code only', s0c.A2_sbx_canary_beacon.sum(), len(s0c), 'definition')
    s010 = m[m.A0_sbx_10s]
    add('gpc_residual', 'first 10 s of each load', s010.A2_sbx_10s.sum(), len(s010))
    for seg, lab in (('conc6', 'crawl run at 6 browsers'), ('conc10', 'crawl run at 10 browsers')):
        x = s0[s0.segment_A2 == seg]
        add('gpc_residual', lab, x.A2_sbx.sum(), len(x))
    x = s0[(s0.nostra != True) & (s0.cf_cache_A0 != 'HIT')]
    add('gpc_residual', 'excluding edge-cached pages', x.A2_sbx.sum(), len(x))
    x = s0[~s0.index.isin(flagged_)]
    add('gpc_residual', 'excluding stores flagged in the ethics review', x.A2_sbx.sum(), len(x))
    add('gpc_residual', 'pixels declaring sale of data only', s0.A2_sbx_decl_sale.sum(), len(s0), 'definition')
    add('gpc_residual', 'any origin (not only sandbox)', (m.A0_any & m.A2_any).sum(), int(m.A0_any.sum()), 'definition')
    S6 = pd.DataFrame(rows)
    # weighted versions (ratio estimator) and CMP-cluster BCa intervals of the three headline outcomes
    wrows = []
    clk_fresh = pd.Series(clk.index.isin(fresh_set), index=clk.index)
    for outcome, y, sub in (('prechoice_sbx_banner', bann.A0_sbx, bann), ('decline_residual', clk_fresh, clk), ('gpc_residual', s0.A2_sbx, s0)):
        ind = m.index.isin(sub.index)
        yy = pd.Series(0, index=m.index)
        yy.loc[sub.index] = y.astype(int).values
        e = strat_ratio(yy, pd.Series(ind.astype(int), index=m.index), m.bucket, E)
        wrows.append(dict(outcome=outcome, variant='weighted to the Tranco top-200k (ratio estimator)', kind='robustness', k=None, n=len(sub), p=e['p'],
                          lo=e['lo'], hi=e['hi']))
        cl_ = np.where(sub.cmp.isin(['none', 'generic', 'multiple']), 'solo_' + sub.index.to_series(), sub.cmp)
        cb = cluster_bootstrap_bca(y.astype(int).values, cl_, B=B, seed=SEED)
        wrows.append(dict(outcome=outcome, variant='cluster bootstrap by consent tool (BCa)', kind='interval', k=int(y.sum()), n=len(sub), p=cb['p'],
                          lo=cb['lo'], hi=cb['hi']))
    S6 = pd.concat([S6, pd.DataFrame(wrows)], ignore_index=True)
    S6.to_csv(os.path.join(OUT, 'figS6.csv'), index=False)
    ov = []
    for oc_ in S6.outcome.unique():
        g = S6[S6.outcome == oc_]
        main_ = g[g.kind == 'main'].iloc[0]
        for _, r in g[g.kind == 'robustness'].iterrows():
            ov.append(bool(r.lo <= main_.hi and r.hi >= main_.lo))
    sp['S6_robustness_variants'] = len(ov)
    sp['S6_robustness_overlap'] = int(sum(ov))
    sp['S6'] = S6.to_dict('records')
    return sp


if __name__ == '__main__':
    main()
