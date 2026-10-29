"""Checks added after the crawl (final audit and polish, 2026-09-26), merged into outputs/stats.json under 'checks'.

Moves into the analysis pipeline the numbers that the manuscript previously took from review-stage scripts
(review/final_audit_checks/final_audit_numbers.py, review/text_fix_checks/text_fix_numbers.py,
review/review_methods_evidence/v1_power.py, product_page_selection.txt), so that RESULTS.md stays the single source.
Reads only saved outputs; makes no network requests. Run after analyze.py, models.py and crawl/recheck/analyze_recheck.py:
  recheck        crawl/recheck/recheck_summary.json (+ blocker_by_store.csv, blocker_by_entry.csv, recall_by_store.csv as a cross-check)
  frame_recall   sample/raw/frame_recall/frame_recall_summary.json (the DNS frame's recall; saved by the final audit)
  lost_stores    main-sample stores not captured in all three base arms, by reason, Tranco bucket and CMP (writes outputs/lost_stores.csv)
  robots         crawl/recheck/robots/robots_summary.json (retrospective robots.txt fetch)
  content        the broader title screen run after the crawl (review/human_relabel_kit/E_broader_child_screen_BLANK.csv)
  v5_strict      Pandectes v5 stores whose strict (opt-in) regions include California (crawl/cmp_declared.csv)
  loads          page loads per store, including pilot re-runs, the next-page reload and the re-check crawl
  landing        landing pages that are gift cards, vouchers or certificates (sample/sample.csv product_url)
  gpc_injection  crawl/validation/gpc_live_summary.json (GPC flag in frames and workers)
  provenance     numbers of the sampling, crawl, pilot and local-validation stages quoted in the manuscript (consistency pass):
                 sample/raw/*.json, crawl/loads.csv, requests.csv.gz, logs/traffic_counts.json, crawl/validation/*,
                 notes/mechanism_evidence/*.txt with ../study2_creator_links/capture/pages.csv, review evidence files
"""
import collections
import json
import os

import pandas as pd

from common import CRAWL, OUT, SAMPLE, STUDY, dump, wilson

W = wilson


def recheck(st):
    R = json.load(open(os.path.join(CRAWL, 'recheck', 'recheck_summary.json')))
    rc, bl = R['recall'], R['blocker']
    mc = rc['main_crawl']
    out = dict(loads=R['loads'], stores=R['stores'], loads_ok=R['loads_ok'], first_load=R['first_load'], last_load=R['last_load'])
    out['recall'] = dict(
        flagged_n=rc['flagged']['n_stores'], flagged_visible=W(rc['flagged']['banner_visible'], rc['flagged']['with_screenshots']),
        flagged_no_screenshot=len(rc['flagged']['no_screenshot']),
        consentmo=W(rc['flagged']['consentmo']['banner_visible'], rc['flagged']['consentmo']['n']),
        flagged_visible_by_cmp=rc['flagged']['by_cmp_visible'],
        random=W(rc['random_nb']['banner_visible'], rc['random_nb']['with_screenshots']),
        blocklist_visible=W(rc['blocklist']['banner_visible'], rc['blocklist']['with_screenshots']),
        missed_on_recheck=rc['missed_on_recheck'], missed_on_recheck_dg_consent_banner=rc['missed_on_recheck_dg_consent_banner'],
        detector_precision_recheck=rc['detector_on_recheck']['precision'], detector_recall_recheck=rc['detector_on_recheck']['recall_on_this_set'],
        pool_outside_flagged=mc['pool_outside_flagged'], missed_observed=mc['missed_observed'],
        est_missed=mc['est_missed'], est_missed_lo=mc['est_missed_lo'], est_missed_hi=mc['est_missed_hi'],
        est_recall=mc['est_recall'], est_recall_lo=mc['est_recall_lo'], est_recall_hi=mc['est_recall_hi'],
        missed_banner_stores=rc['missed_banner_stores'], n_missed_banner_stores=len(rc['missed_banner_stores']),
        missed_banner_stores_A0_sbx=rc['missed_banner_stores_A0_sbx'],
        sens_banner=rc['sens_banner_rate_with_missed']['banner'], sens_no_banner=rc['sens_banner_rate_with_missed']['no_banner'],
        labeller='analysis assistant (AI), blind to group, consent tool and detector result; human re-labelling pending')
    by_cmp = {}
    for c, v in bl['blocker_active_by_cmp'].items():
        k, n = (int(x) for x in v.split('/'))
        by_cmp[c] = W(k, n)
    out['blocker'] = dict(
        stores=bl['stores'], loads_ok=bl['loads_ok'], active=W(bl['blocker_active'], bl['stores']), active_by_cmp=by_cmp,
        fired_main_crawl=bl['stores_fired_main_crawl'],
        fired_main_crawl_active=W(bl['fired_main_crawl_blocker_active'], bl['stores_fired_main_crawl']),
        fired_main_crawl_fired_again=W(bl['fired_main_crawl_fired_again_sbx'], bl['stores_fired_main_crawl']),
        stores_declared_tag_neutralized=bl['stores_declared_tag_neutralized'],
        stores_neutralized_and_sbx=bl['stores_neutralized_and_sbx'], stores_neutralized_and_sbx_ids=bl['stores_neutralized_and_sbx_ids'],
        stores_neutralized_and_sbx_excl_auto_grant=bl['stores_neutralized_and_sbx_excl_auto_grant'],
        entries=bl['entries'], entries_tag_seen=W(bl['entries_tag_seen'], bl['entries']), entries_neutralized=bl['entries_neutralized'],
        entries_neutralized_fired_main=bl['entries_neutralized_fired_main'], entries_neutralized_fired_sbx=bl['entries_neutralized_fired_sbx'],
        entries_cfg_sandboxed=bl['entries_cfg_sandboxed'], entries_cfg_sandboxed_fired_sbx=bl['entries_cfg_sandboxed_fired_sbx'],
        entries_cfg_sandboxed_neutralized=bl['entries_cfg_sandboxed_neutralized'],
        excl_auto_grant=dict(n=bl['n_excl_auto_grant'], active=W(bl['blocker_active_excl_auto_grant'], bl['n_excl_auto_grant']),
                             fired_main_crawl_active=W(bl['fired_main_crawl_excl_auto_grant_blocker_active'], bl['fired_main_crawl_excl_auto_grant'])),
        note='one re-check load per store, after the main crawl; blocker activity was not logged in the main crawl')
    # cross-check the summary against the per-store and per-entry tables it was written with
    bs = pd.read_csv(os.path.join(CRAWL, 'recheck', 'blocker_by_store.csv'))
    # referee 1, M2(c)/m8: stores where the declared vendor fired in the main crawl but no blocker was active on the re-check
    ina = bs[bs.declared_fired_sbx_main_crawl & ~bs.blocker_active]
    out['blocker']['fired_main_crawl_inactive'] = dict(stores=sorted(ina.store_id), n=int(len(ina)), by_cmp={c: int(v) for c, v in ina.cmp.value_counts().items()})
    ns = bs[bs.neutralized_and_sbx]
    out['blocker']['stores_neutralized_and_sbx_by_cmp'] = {c: int(v) for c, v in ns.cmp.value_counts().items()}
    # referee 1, M1: the re-check browser had the same automation fingerprint as the main crawl
    import gzip
    fp = collections.Counter()
    rd = os.path.join(CRAWL, 'recheck', 'raw')
    for f in sorted(os.listdir(rd)):
        if f.endswith('.json.gz'):
            pr = json.load(gzip.open(os.path.join(rd, f))).get('probe') or {}
            if pr:
                fp['with_probe'] += 1
                fp['webdriver'] += int(str(pr.get('webdriver')) == 'True')
                fp['headless_ua'] += int('headlesschrome' in str(pr.get('ua')).lower())
    out['fingerprint'] = dict(fp)
    be = pd.read_csv(os.path.join(CRAWL, 'recheck', 'blocker_by_entry.csv'))
    rs = pd.read_csv(os.path.join(CRAWL, 'recheck', 'recall_by_store.csv'))
    out['crosscheck_ok'] = bool(
        int(bs.blocker_active.sum()) == bl['blocker_active'] and int(bs.declared_fired_sbx_main_crawl.sum()) == bl['stores_fired_main_crawl']
        and int(bs.neutralized_and_sbx.sum()) == bl['stores_neutralized_and_sbx'] and len(be) == bl['entries']
        and int(be.main_tag_seen.sum()) == bl['entries_tag_seen'] and int((be.main_tag_neutralized & be.fired_sandbox).sum()) == bl['entries_neutralized_fired_sbx']
        and int(rs[rs.groups == 'random_nb'].vis.sum()) == rc['random_nb']['banner_visible'])
    return out


def frame_recall():
    F = json.load(open(os.path.join(SAMPLE, 'raw', 'frame_recall', 'frame_recall_summary.json')))
    oc, ov = F['overall_counts'], F['overall']
    out = dict(seed=F['seed'], sampled_per_bucket=F['http_n'], sub_sample_per_bucket=F['sub_n'], contacted=oc['contacted'], inspected=oc['inspected'],
               storefronts_missed=oc['storefronts_missed'], sub_live=oc['sub_live'], est_sub_total=oc['est_sub_total'],
               subdomain_homepages_checked=oc['subdomain_homepages_checked'], not_contacted_keyword=oc['not_contacted_keyword'],
               recall=ov['recall'], recall_lo=ov['recall_lo'], recall_hi=ov['recall_hi'], inframe_live=ov['inframe_live'], est_missed=ov['est_missed'],
               missed_share=1 - ov['recall'], note=ov['note'])
    out['buckets'] = {b: dict(recall=v['recall'], recall_lo=v['recall_lo'], recall_hi=v['recall_hi'], inframe_live=v['inframe_live'],
                              est_missed=v['est_missed'], est_missed_lo=v['est_missed_lo'], est_missed_hi=v['est_missed_hi'],
                              inspected=v['inspected_http200'], contacted=v['contacted'], storefronts_missed=v['storefront_same_site'],
                              sub_live=v['sub_live_storefronts'], est_sub=v['est_sub_storefronts'])
                      for b, v in F['buckets'].items()}
    return out


def ok_loads():
    L = pd.read_csv(os.path.join(CRAWL, 'loads.csv'), low_memory=False)
    L['ok'] = (L.goto_status.fillna(0).between(200, 399)) & (L.has_shopify == True) & (L.blocked_hint != True) & (L.n_requests.fillna(0) > 20)
    return L


def lost_stores(L):
    samp = pd.read_csv(os.path.join(SAMPLE, 'sample.csv')).set_index('store_id')
    base = L[L.arm.isin(['A0', 'A1', 'A2']) & (L.stratum == 'main')]
    cap = base.groupby('store_id').ok.all()
    lost, captured = sorted(cap[~cap].index), sorted(cap[cap].index)

    def reason(r):
        if r.ok:
            return 'ok'
        if r.offsite_redirect == True:
            return 'redirect_off_site'
        if r.goto_status == 404:
            return 'product_page_gone_404'
        if isinstance(r.goto_error, str) and 'NAME_NOT_RESOLVED' in r.goto_error:
            return 'dns_not_resolved'
        if r.goto_status in (402, 403):
            return f'http_{int(r.goto_status)}'
        if r.has_shopify != True:
            return 'no_window_Shopify'
        return 'other'
    x = base[base.store_id.isin(lost)].copy()
    x['reason'] = x.apply(reason, axis=1)
    first_fail = x[x.reason != 'ok'].groupby('store_id').reason.agg(lambda s: s.value_counts().index[0])
    cm = L[L.stratum == 'main'].groupby('store_id').cmps_detected.agg(
        lambda s: '|'.join(sorted({c for v in s.dropna() for c in str(v).split('|') if c})) or 'none')

    def cmp_class(v):
        if v == 'none':
            return 'none detected'
        return 'multiple' if len(v.split('|')) > 1 else v
    D = pd.DataFrame(dict(store_id=lost, bucket=samp.loc[lost].bucket.values, reason=first_fail.reindex(lost).values,
                          cmp=[cmp_class(cm.get(s, 'none')) for s in lost]))
    D.to_csv(os.path.join(OUT, 'lost_stores.csv'), index=False)
    all_b = samp.bucket.value_counts().to_dict()
    cap_cmp = pd.Series([cmp_class(cm.get(s, 'none')) for s in captured]).value_counts()
    bb = D.bucket.value_counts()
    return dict(n=len(lost), n_sample=len(samp), captured=len(captured), by_reason={k: int(v) for k, v in D.reason.value_counts().items()},
                by_bucket={b: W(int(bb.get(b, 0)), int(all_b[b])) for b in all_b}, by_cmp={k: int(v) for k, v in D.cmp.value_counts().items()},
                lost_with_cmp=W(int((D.cmp != 'none detected').sum()), len(D)),
                captured_with_cmp=W(int(cap_cmp.drop('none detected', errors='ignore').sum()), len(captured)))


def robots():
    R = json.load(open(os.path.join(CRAWL, 'recheck', 'robots', 'robots_summary.json')))
    keep = ['stores', 'main', 'creator', 'robots_200', 'unreachable', 'status_4xx', 'status_5xx', 'landing_disallowed', 'landing_disallowed_stores',
            'landing_path_disallowed', 'landing_disallowed_by_query_only', 'landing_disallowed_by_utm_rule', 'home_disallowed', 'pjson_checked',
            'pjson_disallowed', 'disallow_all', 'named_group_for_headlesschrome']
    out = {k: R[k] for k in keep}
    out['excluded_from_fetch'] = R['excluded']
    return out


def content():
    E = pd.read_csv(os.path.join(STUDY, 'review', 'human_relabel_kit', 'E_broader_child_screen_BLANK.csv'))
    return dict(broader_title_hits=len(E))


def v5_strict():
    d = pd.read_csv(os.path.join(CRAWL, 'cmp_declared.csv'))
    p = d[(d.cmp == 'pandectes') & d.detail.str.startswith('v5')].copy()
    p['optin'] = p.detail.str.contains('optin_region=True')
    g = p.groupby('store_id').optin.max()
    blk = set(pd.read_csv(os.path.join(OUT, 'fig4c_declared_blocked_pairs.csv')).store_id)
    opt = sorted(g[g].index)
    return dict(v5_stores=int(len(g)), california_strict=W(int(g.sum()), int(len(g))), california_strict_stores=opt,
                in_blocklist=W(len(set(opt) & blk), len(blk)), in_blocklist_stores=sorted(set(opt) & blk))


def loads_per_store():
    d = pd.read_csv(os.path.join(CRAWL, 'loads.csv'), usecols=['store_id', 'arm', 'next_status'])
    c = collections.Counter(d.store_id)
    for sub in ('superseded_v1_detector/raw', 'raw_failed_attempt1'):
        for f in os.listdir(os.path.join(CRAWL, sub)):
            c[f.split('__')[0]] += 1
    for s_ in d[d.next_status.notna()].store_id:
        c[s_] += 1
    before = pd.Series(dict(c))
    rc = [f.split('__')[0] for f in os.listdir(os.path.join(CRAWL, 'recheck', 'raw')) if f.endswith('.json.gz')]
    for s_ in rc:
        c[s_] += 1
    v = pd.Series(dict(c))
    # minimum gap between the starts of two page loads of the same store in the final crawl (loads.csv started_at)
    t = pd.read_csv(os.path.join(CRAWL, 'loads.csv'), usecols=['store_id', 'started_at'])
    t['t'] = pd.to_datetime(t.started_at)
    gap = t.sort_values('t').groupby('store_id').t.apply(lambda s: s.diff().dt.total_seconds().min())
    return dict(before_max=int(before.max()), before_gt7=int((before > 7).sum()), before_ge10=int((before >= 10).sum()),
                recheck_loads=len(rc), recheck_stores=len(set(rc)),
                with_recheck_min=int(v.min()), with_recheck_max=int(v.max()), with_recheck_gt7=int((v > 7).sum()), with_recheck_ge11=int((v >= 11).sum()),
                min_gap_same_store_s=round(float(gap.min()), 1))


def provenance():
    """Numbers of the sampling, crawl, pilot and local-validation stages that the manuscript quotes (consistency pass,
    2026-09-26). Each is read from the saved file of its stage or recomputed from the saved crawl tables, so that every
    number in the paper is in stats.json (and RESULTS.md); the file is named in 'source' next to each group."""
    import re
    from scipy.stats import fisher_exact
    P = {}
    # ---- sampling stage ----
    Nn = json.load(open(os.path.join(SAMPLE, 'raw', 'notes_numbers.json')))
    F = json.load(open(os.path.join(SAMPLE, 'raw', 'funnel.json')))
    Rq = json.load(open(os.path.join(SAMPLE, 'raw', 'request_stats.json')))
    pb = F['per_bucket']
    rnd = [b for b in pb if pb[b]['sampling_fraction'] < 1][0]
    X = pd.read_csv(os.path.join(SAMPLE, 'raw', 'creator_stratum_exclusions.csv'))
    ver = X[X.stage == 'verify'].reason.value_counts()
    nou = dict(Nn['creator_no_url_primary_reason'])
    P['sample'] = dict(
        source='sample/raw/notes_numbers.json, funnel.json, request_stats.json, creator_stratum_exclusions.csv',
        keyword_screen_flagged=Nn['content_review_flagged'],
        census_drawn=int(sum(pb[b]['drawn_n'] for b in pb if pb[b]['sampling_fraction'] == 1.0)),
        random_bucket_drawn=pb[rnd]['drawn_n'], random_bucket_flagged=pb[rnd]['flagged_N'], random_bucket_weight=pb[rnd]['weight'],
        weight_sum=Rq['sample_weight_sum'], product_list_requests=Rq['verify_results.jsonl']['products_json_requests'],
        landing_from_product_list=Rq['sample_product_url_from_products_json'],
        pilot_hosts_on_dns=W(Nn['study2_shopify_hosts_on_shopify_dns'], Nn['study2_shopify_hosts']),
        creator_candidates=Rq['creator_verify.jsonl']['sites'],
        creator_no_eligible_url=Nn['creator_exclusions_by_stage']['no_eligible_decorated_url'],
        creator_no_url_affiliate_or_click_id=nou['affiliate_network_or_click_id'],
        creator_no_url_no_or_opaque_token=nou['no_token(token_level none/opaque)'],
        creator_no_url_creator_owned=nou['creator_owned_domain_without_url_token'], creator_no_url_platform_site=nou['other:platform_site(3)'],
        creator_verify_excluded=Nn['creator_exclusions_by_stage']['verify'],
        creator_verify_headless=int(ver.get('headless_or_assets_only', 0)), creator_verify_no_markers=int(ver.get('no_markers', 0)),
        creator_verify_blocked_403=int(ver.get('homepage_status_403', 0)), creator_verify_rate_limited_429=int(ver.get('homepage_status_429', 0)),
        creator_stratum=Nn['creator_stratum_rows'], creator_video_tokens=Nn['creator_token_level']['video'],
        creator_in_main_sample=Nn['creator_also_in_main_sample'])
    # ---- crawl stage ----
    T = json.load(open(os.path.join(CRAWL, 'logs', 'traffic_counts.json')))
    FB = json.load(open(os.path.join(CRAWL, 'failure_breakdown.json')))
    Ld = pd.read_csv(os.path.join(CRAWL, 'loads.csv'), usecols=['browser', 'browser_version'])
    ver_by = Ld.groupby('browser').browser_version.agg(lambda s: sorted({str(x).split('.')[0] for x in s}))
    Rr = pd.read_csv(os.path.join(CRAWL, 'requests.csv.gz'), usecols=['origin', 'is_advertising', 'pixel_matched'], low_memory=False)
    ad = Rr[Rr.is_advertising == True]
    join = {o: W(int(ad[ad.origin == o].pixel_matched.fillna(False).astype(bool).sum()), int((ad.origin == o).sum()))
            for o in ('strict_worker', 'lax_iframe')}
    chk = os.path.join(CRAWL, 'validation', 'pilot_runs', 'check_v3_detector', 'raw')
    P['crawl'] = dict(
        source='crawl/loads.csv, requests.csv.gz, logs/traffic_counts.json, failure_breakdown.json, validation/pilot_runs/',
        loads_chromium=int((Ld.browser == 'chromium-headless-shell').sum()), loads_brave=int((Ld.browser == 'brave').sum()),
        chromium_major=int(ver_by['chromium-headless-shell'][0]), brave_major=int(ver_by['brave'][0]),
        first_load_utc=FB['first_load_at'][11:16], last_load_utc=FB['last_load_at'][11:16],
        next_page_reloads=T['a1_next_page_navigations'], superseded_v1_loads=T['superseded_v1_loads'],
        retry_originals=T['retry_originals'], pilot_v1_detector_loads=T['pilot_v1_detector_loads'],
        check_v3_detector_loads=T['check_v3_detector_loads'], check_v3_detector_stores=len({f.split('__')[0] for f in os.listdir(chk)}),
        redirect_host_google=FB['offsite_redirect_hosts'].get('google.com', 0),
        join_strict=join['strict_worker'], join_lax=join['lax_iframe'])
    # ---- consent writes without a click and the first passive scroll (all events, not only the first; review MET-17) ----
    from gate_audit import decode_state  # same decoding of the navigation's _cmp string as the gate audit
    CE = pd.read_csv(os.path.join(CRAWL, 'consent_events.csv'), dtype={'store_id': str})
    Lc = pd.read_csv(os.path.join(CRAWL, 'loads.csv'), usecols=['load_id', 't_load', 'cmp_header_raw']).set_index('load_id')
    st_ids = set(pd.read_csv(os.path.join(OUT, 'store_table.csv'), usecols=['store_id']).store_id)
    ce = CE[CE.arm.isin(['A0', 'A0r', 'A2', 'A2r', 'V1']) & CE.load_id.isin(Lc.index) & CE.store_id.isin(st_ids)].copy()
    ce['t_first_scroll'] = ce.load_id.map(Lc.t_load) + 2000
    ce['mkt'] = ce.detail.apply(lambda s: json.loads(s).get('marketingAllowed'))
    ce = ce.sort_values(['load_id', 't_ms'])
    ce['prev_mkt'] = ce.groupby('load_id').mkt.shift(1)
    ce['hdr_m'] = ce.load_id.map(Lc.cmp_header_raw).apply(lambda r: (decode_state(r) or {}).get('m'))
    ce['prev_state'] = ce.prev_mkt.where(ce.prev_mkt.notna(), ce.hdr_m)
    g = ce[(ce.mkt == True) & (ce.prev_state == False)]
    after = g.t_ms >= g.t_first_scroll
    P['scroll'] = dict(source='crawl/consent_events.csv, crawl/loads.csv (as review/text_fix_checks/text_fix_numbers.py, section 3)',
                       marketing_grants_without_click=int(len(g)), before_first_scroll=int((~after).sum()), after_first_scroll=int(after.sum()),
                       after_first_scroll_stores=int(g[after].store_id.nunique()),
                       after_first_scroll_cmps=sorted(set(pd.read_csv(os.path.join(OUT, 'store_table.csv'), usecols=['store_id', 'cmp'])
                                                          .set_index('store_id').cmp.reindex(g[after].store_id.unique()).astype(str))),
                       after_first_scroll_lag_s_min=round(float((g[after].t_ms - g[after].t_first_scroll).min()) / 1000, 1) if after.any() else None,
                       after_first_scroll_lag_s_max=round(float((g[after].t_ms - g[after].t_first_scroll).max()) / 1000, 1) if after.any() else None)
    # ---- attribution checks of the review stage (saved files) ----
    lax = open(os.path.join(STUDY, 'review', 'review_methods_evidence', 'lax_sandbox_attr_check.txt')).read()
    m = re.search(r'sampled:\s*(\d+)\s*;\s*LAX sandbox frames:\s*(\d+)\s*;\s*frames with a recorded sandbox attribute:\s*(\d+)', lax)
    sp = pd.read_csv(os.path.join(STUDY, 'review', 'review_methods_evidence', 'spotcheck_30.csv'))
    sw = sp[sp.origin == 'strict_worker']
    bl = pd.read_csv(os.path.join(OUT, 'fig4c_declared_blocked_pairs.csv'))
    bl = bl[bl.declared_prechoice == 'blocked']
    sets = bl.groupby('store_id').agg(cmp=('cmp', 'first'), s=('vendor', lambda v: tuple(sorted(set(v)))))
    P['attribution'] = dict(
        source='review/review_methods_evidence/lax_sandbox_attr_check.txt, spotcheck_30.csv; outputs/fig4c_declared_blocked_pairs.csv',
        lax_records_sampled=int(m.group(1)), lax_frames=int(m.group(2)), lax_frames_with_attribute=int(m.group(3)),
        spotcheck_strict=int(len(sw)),
        spotcheck_strict_google_from_applovin=int(((sw.vendor == 'google_ads') & sw.note.str.contains('cfg_vendor=applovin')).sum()),
        blocklist_sets={c: dict(stores=int(len(x)), distinct_sets=int(x.s.nunique())) for c, x in sets.groupby('cmp')})
    # ---- local validation of the GPC injection and of Brave's Shields setting ----
    txt = open(os.path.join(CRAWL, 'validation', 'gpc_injection_selftest_output.txt')).read()
    blocks = {}
    for head, body in re.findall(r'^## ([^\n]+)\n(\{.*?\n\})', txt, flags=re.S | re.M):
        blocks[head] = json.loads(body)
    inj = next(v for k, v in blocks.items() if v.get('inject') is True)
    ctl = next(v for k, v in blocks.items() if v.get('inject') is False and k.startswith('chromium'))
    tgt = inj['first_statement_gpc']
    runs_all_true = sum(all(v['gpc_true'] == v['n'] for v in [tgt[t]]) for t in tgt)
    bf = json.load(open(os.path.join(CRAWL, 'validation', 'brave_farbling_control.json')))
    off = bf['out']['brave:default_value_shields_off']
    P['validation'] = dict(
        source='crawl/validation/gpc_injection_selftest_output.txt, brave_farbling_control.json',
        selftest_runs=inj['runs'], selftest_min_true_per_target=int(min(v['gpc_true'] for v in tgt.values())), selftest_targets=len(tgt),
        selftest_targets_all_true=int(runs_all_true),
        control_runs=ctl['runs'], control_true_first_statement=int(max(v['gpc_true'] for v in ctl['first_statement_gpc'].values())),
        brave_shields_off_runs=len(off), brave_shields_off_true_hw=int(sum(x['hc'] == bf['true_hw_concurrency'] for x in off)))
    # ---- pilot loads of Store C in the earlier creator-link study (notes/mechanism_evidence, Study 2 pages.csv) ----
    ev = os.path.join(STUDY, 'notes', 'mechanism_evidence')
    lines = [l for l in open(os.path.join(ev, 'gpc_race_store_c.txt')).read().splitlines() if re.match(r'\s*(cid|S2C\d+)\s', l)]
    tab = pd.read_csv(pd.io.common.StringIO('\n'.join(lines)), sep=r'\s+')
    pages = pd.read_csv(os.path.join(STUDY, '..', 'study2_creator_links', 'capture', 'pages.csv'), usecols=['capture_id', 'token_level'])
    lvl = pages.drop_duplicates('capture_id').set_index('capture_id').token_level
    tab['level'] = tab.cid.map(lvl)
    gp = tab[tab.cond == 'gpc']
    vid = gp[gp.level == 'video']
    nos = gp[gp.nostra_skipcache_fetch == True]
    sb = open(os.path.join(ev, 'sandbox_vs_blocker_store_c.txt')).read()
    dflt = re.search(r'\[default\] n=(\d+)\n\s*TikTok \(STRICT worker\): sandbox created (\d+)/(\d+).*?\n\s*Meta \(OPEN main thread\): '
                     r'pixel script loaded \d+/\d+; fbevents\.js loaded (\d+)/(\d+)', sb)
    c3 = json.load(open(os.path.join(OUT, 'stats.json')))['fig6']['b']['store_c']
    miss = int(sum(c3[a]['n_tiktok'] == 0 for a in ('A2', 'A2r')))
    k_v, n_v = int(vid.tiktok_fired.sum()), int(len(vid))
    P['pilot'] = dict(
        source='notes/mechanism_evidence/gpc_race_store_c.txt, sandbox_vs_blocker_store_c.txt; study2_creator_links/capture/pages.csv',
        gpc_tiktok_fired=W(int(gp.tiktok_fired.sum()), int(len(gp))), gpc_tiktok_fired_video=W(k_v, n_v),
        edge_cached_gpc_loads=int(len(nos)), fired_lag_max_ms=int(nos[nos.tiktok_fired].lag_ms.max()),
        not_fired_lag_min_ms=int(nos[~nos.tiktok_fired].lag_ms.min()),
        fired_within_threshold=W(int((nos.tiktok_fired & (nos.lag_ms <= nos[nos.tiktok_fired].lag_ms.max())).sum()), int(nos.tiktok_fired.sum())),
        not_fired_beyond_threshold=W(int((~nos.tiktok_fired & (nos.lag_ms > nos[nos.tiktok_fired].lag_ms.max())).sum()), int((~nos.tiktok_fired).sum())),
        default_tiktok_sandbox=W(int(dflt.group(2)), int(dflt.group(3))), default_meta_fbevents=W(int(dflt.group(4)), int(dflt.group(5))),
        crawl_gpc_misses=W(0, miss) if miss else None,
        fisher_p_video_vs_crawl=float(fisher_exact([[k_v, n_v - k_v], [0, miss]])[1]),
        p_two_misses_at_pilot_rate=float((1 - k_v / n_v) ** miss))
    return P


def landing(m):
    s = pd.read_csv(os.path.join(SAMPLE, 'sample.csv')).set_index('store_id')
    x = s.loc[m.index]
    h = x.product_url.str.lower().str.extract(r'/products/([^/?#]+)')[0].fillna('')
    gift_any = x.product_url.str.lower().str.contains('gift')
    card = h.str.contains(r'gift[-_]?card|giftcard|e[-_]?gift|gift[-_]?(?:voucher|certificate)', regex=True)
    y = m.A0_sbx.astype(bool)
    return dict(url_contains_gift=int(gift_any.sum()), gift_card=W(int(card.sum()), len(m)), gift_other=int((gift_any & ~card).sum()),
                gift_card_prechoice=W(int(y[card].sum()), int(card.sum())), other_prechoice=W(int(y[~card].sum()), int((~card).sum())),
                rule='product handle matches gift card / giftcard / e-gift / gift voucher / gift certificate')


def gpc_injection():
    g = json.load(open(os.path.join(CRAWL, 'validation', 'gpc_live_summary.json')))
    a2, v1 = g['A2'], g['V1']
    return dict(lax_frames=W(a2['lax_sandbox_frames_gpc_True'], a2['lax_sandbox_frames']),
                other_workers=W(a2['other_workers_gpc_true'], a2['other_workers']),
                strict_injection_before_own_code=W(a2['strict_workers_own_globals_added_after_injection'], a2['strict_workers']),
                other_workers_ordering_confirmed=W(a2['other_workers_own_globals_added_after_injection'], a2['other_workers']),
                strict_workers_read_undefined=W(a2['strict_workers_gpc_undefined'], a2['strict_workers']),
                brave_strict_workers_read_undefined=W(v1['strict_workers_gpc_undefined'], v1['strict_workers']),
                worker_requests_sec_gpc=W(a2['req_worker_sec_gpc_1'], a2['req_worker_with_header_info']))


def main():
    sp = os.path.join(OUT, 'stats.json')
    S = json.load(open(sp))
    st = pd.read_csv(os.path.join(OUT, 'store_table.csv')).set_index('store_id')
    m = st[st.stratum == 'main']
    L = ok_loads()
    C = dict(recheck=recheck(st), frame_recall=frame_recall(), lost_stores=lost_stores(L), robots=robots(), content=content(),
             v5_strict=v5_strict(), loads=loads_per_store(), landing=landing(m), gpc_injection=gpc_injection(), provenance=provenance())
    C['lost_stores']['matches_design'] = bool(C['lost_stores']['n'] == S['design']['funnel_excl']['sample_to_captured'])
    S['checks'] = C
    dump(S, 'stats.json')
    print('checks:', {k: (v.get('crosscheck_ok') if isinstance(v, dict) and 'crosscheck_ok' in v else 'ok') for k, v in C.items()},
          'lost stores', C['lost_stores']['n'], 'frame recall', round(C['frame_recall']['recall'], 3))


if __name__ == '__main__':
    main()
