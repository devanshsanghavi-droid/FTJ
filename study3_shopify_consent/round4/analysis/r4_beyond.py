"""Round 4 B2: beyond-Shopify pilot analysis (round4/beyond/PROTOCOL.md sections 3-5, 8).

Reads round4/beyond/crawl/raw/<site>__<arm>.json.gz (crawl_r4.js --set beyond) and round4/beyond/candidates.csv.
Classification of each request, in this order (PROTOCOL.md section 4):
  1. the Part A host map (the crawler's own `vendor`/`ad` labels), then the 39 host entries added in
     vendor_endpoints_extra.json;
  2. first-party rules (same site or a hosted-sGTM host): `strong` ones count in the headline as 'via first-party
     endpoint', `moderate` ones are reported separately; the Partytown proxy (?url=<vendor URL>) is attributed to the
     inner URL's vendor.
  'ad request' = a request to an advertising vendor (Part A map or the added hosts) or a strong first-party hit whose
  wire format names an ad vendor (Google Ads / Meta / TikTok). 'first-party collect' = any strong first-party beacon
  (GA4, Google Ads, UA, Meta, TikTok, Zaraz track call). Requests blocked by the browser (blockedReason) and CORS
  preflights are not counted as data sent. Server-side forwarding is never inferred.
Load qualification (replaces Part A's window.Shopify test, PROTOCOL.md 5): HTTP 2xx/3xx, not 401/403/429/503, no
  challenge-page title, no redirect to another site, more than 20 requests.
Arms: A0 Default (all requests are before any choice); A1 Decline (click only 'Decline/Reject'; after = same page
  after the click + the next page); A2 GPC.
CIs: Wilson (primary) plus a site bootstrap (percentile, B = 2000, seed 20260926). Paired A0 vs A2: exact McNemar and
  Newcombe's paired interval (analysis/analyze.py). PT (8 sites) and ZZ (1 site) are case studies: no rates.

Outputs (round4/analysis/outputs/beyond/): beyond_loads.csv, beyond_requests.csv.gz (classified data-bearing
  requests), beyond_sites.csv, beyond_r4.json, case_studies.json
"""
import csv
import gzip
import json
import os
import re
import sys
from collections import Counter, defaultdict
from urllib.parse import parse_qs, unquote, urlsplit

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(STUDY, 'analysis'))
sys.path.insert(0, os.path.join(STUDY, 'crawl'))
_argv = sys.argv
sys.argv = [sys.argv[0]]
import build_tables as BT  # noqa: E402  (Part A helpers: phase(), banner_t(), detect_cmps(), vendor map)
sys.argv = _argv
from common import wilson  # noqa: E402

RAW = os.environ.get('R4_BEYOND_RAW', os.path.join(STUDY, 'round4', 'beyond', 'crawl', 'raw'))
OUT = os.environ.get('R4_BEYOND_OUT', os.path.join(HERE, 'outputs', 'beyond'))
EX = json.load(open(os.path.join(STUDY, 'round4', 'beyond', 'vendor_endpoints_extra.json')))
VE = json.load(open(os.path.join(STUDY, 'crawl', 'vendor_endpoints.json')))
B = 2000
SEED = 20260926
ARCH_CODE = {'partytown': 'PT', 'zaraz': 'ZZ', 'gateway': 'GW', 'wix': 'WX', 'bigcommerce': 'BC'}
AD_FP_VENDORS = {'google_ads', 'meta', 'tiktok'}
IS_AD = {v['vendor']: bool(v.get('is_advertising')) for v in VE['vendors'] + EX['vendors']}
EXTRA_HOSTS = [(v['vendor'], re.compile(v['host_regex']), bool(v.get('is_advertising')), v['vendor_class']) for v in EX['vendors']]
GW_HOSTS = [rx for name, rx, ad, cls in EXTRA_HOSTS if cls == 'tag_gateway_host']
RULES = []
for r in EX['first_party_rules']:
    RULES.append(dict(r, _p=re.compile(r['path_regex']) if r.get('path_regex') else None, _q=re.compile(r['query_regex']) if r.get('query_regex') else None,
                      _h=re.compile(r['host_regex']) if r.get('host_regex') else None, _qb=re.compile(r['query_or_body_regex']) if r.get('query_or_body_regex') else None,
                      _b=re.compile(r['body_regex']) if r.get('body_regex') else None, _sc=re.compile(r['response_set_cookie_names']) if r.get('response_set_cookie_names') else None,
                      _fh=re.compile(r['frame_host_regex']) if r.get('frame_host_regex') else None))
GCD = EX['consent_signal_decoders']['google_gcd']


def regdom(h):
    h = (h or '').replace('www.', '', 1).lower() if (h or '').startswith('www.') else (h or '').lower()
    p = h.split('.')
    if len(p) <= 2:
        return h
    return '.'.join(p[-3:]) if re.search(r'\.(co|com|net|org|gov|edu|ac)\.[a-z]{2}$', h) else '.'.join(p[-2:])


def extra_vendor(host):
    for name, rx, ad, cls in EXTRA_HOSTS:
        if rx.search(host or ''):
            return name, ad, cls
    return None, False, None


def orig_vendor(host):
    return BT.vendor_of_host(host)


def match_rules(q, page_host):
    """First matching first-party rule id (and its record) for a request, or (None, None)."""
    host = q.get('host') or ''
    url = q.get('url') or ''
    try:
        U = urlsplit(url)
    except Exception:
        return None, None
    same = regdom(host) == regdom(page_host)
    gwh = any(rx.search(host) for rx in GW_HOSTS)
    query = U.query
    body = q.get('post') or ''
    meth = (q.get('m') or '').upper()
    for r in RULES:
        sc = r['scope']
        if sc == 'frame_host':
            continue
        if sc == 'same_site' and not same:
            continue
        if sc == 'same_site_or_known_gateway_host' and not (same or gwh):
            continue
        if sc == 'same_site_subdomain' and not (same and host != page_host):
            continue
        if r.get('method') and r['method'] != 'any' and meth and meth not in r['method'].split('|'):
            continue
        if r['_p'] and not r['_p'].search(U.path):
            continue
        if r['_q'] and not r['_q'].search(query):
            continue
        if r['_h'] and not r['_h'].search(host):
            continue
        if r['_qb'] and not (r['_qb'].search(query) or r['_qb'].search(body)):
            continue
        if r['_b'] and not r['_b'].search(body):
            continue
        if r['_sc']:
            if not any(r['_sc'].match(n) for n in (q.get('setck') or [])):
                continue
        if not (r['_p'] or r['_q'] or r['_h'] or r['_qb'] or r['_b'] or r['_sc']):
            continue
        return r['id'], r
    return None, None


def gconsent(url):
    """Consent state a Google hit declares for ad_storage: denied / granted / not_set / none (no parameter).
    gcs is primary (documented values); gcd (unofficial letter code) is used when gcs is absent."""
    try:
        qs = parse_qs(urlsplit(url).query)
    except Exception:
        return 'none', None, None
    gcs = (qs.get('gcs') or [None])[0]
    gcd = (qs.get('gcd') or [None])[0]
    s_gcs = s_gcd = None
    if gcs:
        m = re.match(r'^G1([01-])([01-])$', gcs)
        if m:
            s_gcs = {'1': 'granted', '0': 'denied', '-': 'not_set'}[m.group(1)]
    if gcd and len(gcd) > GCD['positions']['ad_storage']:
        L = gcd[GCD['positions']['ad_storage']]
        s_gcd = 'granted' if L in GCD['effective_granted'] else ('denied' if L in GCD['effective_denied'] else 'not_set')
    st = s_gcs or s_gcd or 'none'
    return st, s_gcs, s_gcd


def origin_label(q, arch, rec):
    sess = q.get('sess') or ''
    su = q.get('sess_url') or ''
    fu = q.get('frame_url') or ''
    stack = ' '.join([q.get('ini_url') or ''] + (q.get('ini_stack') or []))
    if sess in ('worker', 'shared_worker', 'service_worker'):
        if re.search(r'partytown', su) or (su.startswith('blob:') and rec.get('_has_pt')):
            return 'partytown_worker'
        if arch == 'wix':
            return 'wix_platform_worker'
        return 'other_worker'
    if fu and q.get('origin') == 'subframe':
        fh = urlsplit(fu).hostname or ''
        if re.search(r'(^|\.)filesusr\.com$', fh):
            return 'wix_embed_iframe'
        if re.search(r'(^|\.)(wixapps\.net|wix\.com)$', fh):
            return 'wix_app_frame'
        return 'subframe'
    if q.get('origin') == 'subframe':
        return 'subframe'
    if '/cdn-cgi/zaraz/' in stack:
        return 'zaraz_client'
    return 'main_thread'


def load_record(fn, meta):
    rec = json.load(gzip.open(fn, 'rt'))
    sid, arm = rec['store_id'], rec['arm']
    m = meta.get(sid, {})
    arch = m.get('architecture', rec.get('stratum', '').replace('b2_', ''))
    pr = rec.get('probe') if isinstance(rec.get('probe'), dict) else {}
    cons = [c for c in rec.get('consent') or [] if isinstance(c, dict) and not c.get('__err')]
    b2s = [c.get('b2') or {} for c in cons]
    rec['_has_pt'] = any(b.get('pt') for b in b2s)
    fin = pr.get('location') or rec.get('goto_url') or ''
    try:
        fin_host = urlsplit(fin).hostname or ''
    except Exception:
        fin_host = ''
    offsite = bool(fin_host) and regdom(fin_host) != regdom(rec.get('domain') or '')
    title = pr.get('title') or ''
    challenge = bool(re.search(r'just a moment|access denied|attention required|are you a robot|verify you are human', title, re.I))
    st = rec.get('goto_status')
    rq = rec.get('requests') or []
    ok = st is not None and 200 <= st < 400 and st not in (401, 403, 429, 503) and not challenge and not offsite and len(rq) > int(os.environ.get('R4_BEYOND_MINREQ', '20'))
    bt = BT.banner_t(rec)
    cl = rec.get('clicks') or {}
    bw = rec.get('banner_wait') or {}
    page_host = fin_host or (urlsplit(rec.get('url') or '').hostname or '')
    det = BT.detect_cmps(rec)
    load = dict(load_id=f'{sid}__{arm}', site=sid, arm=arm, architecture=arch, domain=rec.get('domain'), goto_status=st, goto_error=rec.get('goto_error') or rec.get('fatal_error'),
                final_host=fin_host, offsite=offsite, challenge_title=challenge, bot_wall_hints='|'.join(pr.get('bot_wall_hints') or []), n_requests=len(rq), ok=ok,
                banner_visible=bt is not None, t_banner=bt, banner_cmp=((bw.get('banner') or {}).get('cmp') if arm == 'A1' else ((pr.get('cs3') or {}).get('banner') or {}).get('cmp')),
                banner_how=((bw.get('banner') or {}).get('how') if arm == 'A1' else ((pr.get('cs3') or {}).get('banner') or {}).get('how')),
                a1_banner_found=bw.get('found') if arm == 'A1' else None, no_decline_option=bool(rec.get('no_decline_option')) if arm == 'A1' else None,
                reject_text=(cl.get('find') or {}).get('text'), click_method=cl.get('method'), banner_still_after_click=(cl.get('banner_after') or {}).get('found') if cl.get('method') else None,
                t_click=(cl['t_click_epoch'] - rec['nav_wall']) if cl.get('t_click_epoch') and rec.get('nav_wall') else None,
                next_status=rec.get('next_status'), cmps_detected='|'.join(sorted(k for k, e in det.items() if BT.strong(e))),
                gpc_main=pr.get('gpc'), webdriver=pr.get('webdriver'), title=title[:100], started_at=rec.get('started_at'),
                workers=sum(1 for t in rec.get('targets') or [] if t.get('type') in ('worker', 'shared_worker', 'service_worker')),
                workers_gpc_true=sum(1 for w in rec.get('workers_gpc') or [] if (w.get('val') or {}).get('gpc') == 'true'),
                cookie_names='|'.join(sorted({c.get('n') for c in rec.get('cookies') or [] if c.get('n')}))[:2000])
    # architecture readouts: first and last checkpoint
    def pick(b, k):
        return json.dumps(b.get(k), sort_keys=True)[:600] if b.get(k) is not None else None
    b_first = next((b for b in b2s if b), {})
    b_last = next((b for b in reversed(b2s) if b), {})
    for k in ('pt', 'zz', 'wx', 'bc'):
        load[f'b2_{k}_first'] = pick(b_first, k)
        load[f'b2_{k}_last'] = pick(b_last, k)
    load['consent_cookies_last'] = '|'.join(b_last.get('ck') or [])
    load['tcf'] = any(b.get('tcf') for b in b2s)
    reqs = []
    for q in rq:
        host = q.get('host') or ''
        if (q.get('m') or '').upper() == 'OPTIONS' or q.get('blocked'):
            continue
        v, ad, via = q.get('vendor'), bool(q.get('ad')), 'host_map'
        if not v:
            v, ad, _cls = extra_vendor(host)
            via = 'host_map_extra' if v else None
        rid, rule = (None, None)
        fp_kind = fp_ev = None
        if not v:
            rid, rule = match_rules(q, page_host)
            if rule:
                via = 'first_party'
                fp_ev = rule['evidence']
                fp_kind = rule['kind']
                v = rule['attributes_to']
                if v == 'decode_inner_url':
                    inner = None
                    for k in ('url', 'u', 'target'):
                        mm = re.search(r'[?&]' + k + r'=([^&]+)', q.get('url') or '')
                        if mm:
                            inner = unquote(mm.group(1))
                            break
                    ih = urlsplit(inner).hostname if inner else ''
                    v = orig_vendor(ih) or extra_vendor(ih)[0] or 'unknown_proxied'
                    via = 'partytown_proxy'
                ad = v in AD_FP_VENDORS and fp_ev == 'strong'
        if not v:
            continue
        kind = q.get('vkind') or fp_kind or 'other'
        ph = BT.phase(q.get('t'), rec)
        gst, s_gcs, s_gcd = gconsent(q.get('url') or '') if (v or '').startswith('google') or rid in ('G4', 'G5', 'G6', 'G7', 'G8') else ('none', None, None)
        reqs.append(dict(load_id=load['load_id'], site=sid, arm=arm, architecture=arch, i=q.get('i'), t=q.get('t'), phase=ph, host=host, vendor=v, ad=bool(ad), via=via, rule=rid,
                         fp_evidence=fp_ev, kind=kind, beacon=kind != 'library', origin=origin_label(q, arch, rec), origin_crawl=q.get('origin'), sess_url=(q.get('sess_url') or '')[:120],
                         frame_url=(q.get('frame_url') or '')[:120], gcons=gst, gcs_state=s_gcs, gcd_state=s_gcd, setck='|'.join(q.get('setck') or []), fail=q.get('fail'),
                         canary=bool(q.get('canary')), url=(q.get('url') or '')[:400]))
    return load, reqs


def WB(y):
    y = np.asarray(y, dtype=int)
    r = wilson(int(y.sum()), len(y))
    if len(y):
        rng = np.random.default_rng(SEED)
        est = y[rng.integers(0, len(y), size=(B, len(y)))].mean(1)
        r.update(boot_lo=float(np.percentile(est, 2.5)), boot_hi=float(np.percentile(est, 97.5)))
    return r


def main():
    os.makedirs(OUT, exist_ok=True)
    cand = [r for r in csv.DictReader(open(os.path.join(STUDY, 'round4', 'beyond', 'candidates.csv'))) if r['selection'] == 'selected']
    meta = {f"b2-{ARCH_CODE[r['architecture']]}{int(r['selection_order']):03d}": r for r in cand}
    files = sorted(f for f in os.listdir(RAW) if f.endswith('.json.gz')) if os.path.isdir(RAW) else []
    if os.environ.get('R4_BEYOND_TESTARCH'):   # offline self-test on a local page only
        for f in files:
            sid = f.split('__')[0]
            meta.setdefault(sid, dict(architecture=os.environ['R4_BEYOND_TESTARCH'], tier='T', screen_stratum='T', cmps='', tranco_rank=0, selection_order=0))
    loads, reqs = [], []
    for f in files:
        ld, rq = load_record(os.path.join(RAW, f), meta)
        loads.append(ld)
        reqs += rq
    L = pd.DataFrame(loads)
    Q = pd.DataFrame(reqs)
    L.to_csv(os.path.join(OUT, 'beyond_loads.csv'), index=False)
    Q.to_csv(os.path.join(OUT, 'beyond_requests.csv.gz'), index=False, compression={'method': 'gzip', 'mtime': 0})
    if not len(L):
        print('no loads')
        return
    okL = L[L.ok]
    oks = okL.groupby('site').arm.apply(set)
    sites = []
    for sid, m in meta.items():
        arch = m['architecture']
        r = dict(site=sid, architecture=arch, tier=m['tier'], screen_stratum=m['screen_stratum'], static_cmps=m['cmps'], rank=int(m['tranco_rank']))
        arms = oks.get(sid, set())
        r['planned'] = True
        r['n_loads_run'] = int((L.site == sid).sum())
        r['ok_A0'], r['ok_A1'], r['ok_A2'] = 'A0' in arms, 'A1' in arms, 'A2' in arms
        r['captured'] = {'A0', 'A1', 'A2'} <= arms
        g = Q[Q.site == sid]
        l0 = okL[(okL.site == sid) & (okL.arm == 'A0')]
        l1 = okL[(okL.site == sid) & (okL.arm == 'A1')]
        r['banner_A0'] = bool(l0.banner_visible.any()) if len(l0) else None
        r['banner_A1'] = bool(l1.a1_banner_found.fillna(False).astype(bool).any()) if len(l1) else None
        r['banner_any'] = bool(r['banner_A0']) or bool(r['banner_A1'])
        r['cmps_detected'] = l0.cmps_detected.iloc[0] if len(l0) else None
        g0 = g[(g.arm == 'A0') & g.load_id.isin(okL.load_id)]
        g1 = g[(g.arm == 'A1') & g.load_id.isin(okL.load_id)]
        g2 = g[(g.arm == 'A2') & g.load_id.isin(okL.load_id)]
        r['A0_ad'] = bool(g0.ad.any()) if len(l0) else None
        r['A0_ad_beacon'] = bool((g0.ad & g0.beacon).any()) if len(l0) else None
        r['A0_ad_vendors'] = '|'.join(sorted(g0[g0.ad].vendor.unique()))
        r['A0_ad_origins'] = '|'.join(sorted(g0[g0.ad].origin.unique()))
        r['A0_ad_offmain'] = bool((g0.ad & (g0.origin != 'main_thread')).any()) if len(l0) else None
        r['A0_ad_fp'] = bool((g0.ad & (g0.via == 'first_party')).any()) if len(l0) else None
        fpc = lambda x: x[(x.via.isin(['first_party'])) & (x.fp_evidence == 'strong') & x.beacon]  # noqa: E731
        r['A0_fp_collect'] = bool(len(fpc(g0))) if len(l0) else None
        r['A0_fp_moderate'] = bool(((g0.via == 'first_party') & (g0.fp_evidence == 'moderate')).any()) if len(l0) else None
        r['A0_pt_worker_ad'] = bool((g0.ad & (g0.origin == 'partytown_worker')).any()) if len(l0) else None
        r['A0_zaraz_track'] = bool((g0.rule == 'Z2').any()) if len(l0) else None
        # Decline
        if len(l1):
            x = l1.iloc[0]
            r['clicked'] = x.click_method in ('playwright_click', 'playwright_force', 'js_click') and bool(x.a1_banner_found)
            r['click_ok'] = bool(r['clicked'] and x.banner_still_after_click is not True)
            r['no_decline_option'] = bool(x.no_decline_option)
            r['reject_text'] = x.reject_text
            aft = g1[g1.phase.isin(['post_click', 'next_page'])]
            pre1 = g1[g1.phase.isin(['pre_banner', 'banner_prechoice', 'pre_choice'])]
            r['A1_pre_ad'] = bool(pre1.ad.any())
            r['A1_after_ad'] = bool(aft.ad.any()) if r['click_ok'] else None
            r['A1_after_ad_beacon'] = bool((aft.ad & aft.beacon).any()) if r['click_ok'] else None
            r['A1_next_ad'] = bool(aft[aft.phase == 'next_page'].ad.any()) if r['click_ok'] else None
            r['A1_after_ad_vendors'] = '|'.join(sorted(aft[aft.ad].vendor.unique())) if r['click_ok'] else None
            r['A1_after_ad_origins'] = '|'.join(sorted(aft[aft.ad].origin.unique())) if r['click_ok'] else None
            fa = fpc(aft)
            r['A1_after_fp_collect'] = bool(len(fa)) if r['click_ok'] else None
            r['A1_after_fp_gcons'] = '|'.join(f'{k}:{v}' for k, v in sorted(Counter(fa.gcons).items())) if r['click_ok'] else None
            sc_re = next(x['_sc'] for x in RULES if x['id'] == 'G13')
            fp_ck = aft[(aft.via == 'first_party') & aft.setck.fillna('').str.len().gt(0)]
            r['A1_after_server_id_cookie'] = bool(fp_ck.setck.map(lambda s: any(sc_re.match(n) for n in s.split('|') if n)).any()) if r['click_ok'] else None
            r['A1_after_zaraz_track'] = bool((aft.rule == 'Z2').any()) if r['click_ok'] else None
        # GPC
        r['A2_ad'] = bool(g2.ad.any()) if len(okL[(okL.site == sid) & (okL.arm == 'A2')]) else None
        r['A2_fp_collect'] = bool(len(fpc(g2))) if r['A2_ad'] is not None else None
        l2 = okL[(okL.site == sid) & (okL.arm == 'A2')]
        r['A2_workers'] = int(l2.workers.iloc[0]) if len(l2) else None
        r['A2_workers_gpc_true'] = int(l2.workers_gpc_true.iloc[0]) if len(l2) else None
        # architecture readouts (A0)
        for k in ('pt', 'zz', 'wx', 'bc'):
            r[f'b2_{k}'] = l0[f'b2_{k}_first'].iloc[0] if len(l0) else None
        if arch == 'wix' and len(l0) and isinstance(l0.b2_wx_first.iloc[0], str):
            w = json.loads(l0.b2_wx_first.iloc[0])
            pol = (w or {}).get('policy') or {}
            r['wx_default_advertising'] = pol.get('advertising')
            r['wx_gdpr_geo'] = (w or {}).get('gdprGeo')
            r['A0_ad_wix_top'] = bool((g0.ad & (g0.origin == 'main_thread')).any())
            r['A0_ad_wix_embed_or_app'] = bool((g0.ad & g0.origin.isin(['wix_embed_iframe', 'wix_app_frame'])).any())
        if arch == 'bigcommerce' and len(l0):
            bf, bl = l0.b2_bc_first.iloc[0], l0.b2_bc_last.iloc[0]
            bf = json.loads(bf) if isinstance(bf, str) else None
            bl = json.loads(bl) if isinstance(bl, str) else None
            r['bc_consent_enabled'] = bool(bf and bf.get('cfg') not in (None, 'err', 'null'))
            r['bc_held_first'] = sum((bf or {}).get('held', {}).get(k, 0) for k in (bf or {}).get('held', {}) if k.endswith('text/plain'))
            r['bc_held_last'] = sum((bl or {}).get('held', {}).get(k, 0) for k in (bl or {}).get('held', {}) if k.endswith('text/plain'))
        sites.append(r)
    S = pd.DataFrame(sites)
    for c in ('clicked', 'click_ok', 'no_decline_option', 'reject_text', 'A1_pre_ad', 'A1_after_ad', 'A1_after_ad_beacon', 'A1_next_ad', 'A1_after_ad_vendors',
              'A1_after_ad_origins', 'A1_after_fp_collect', 'A1_after_fp_gcons', 'A1_after_server_id_cookie', 'A1_after_zaraz_track', 'wx_default_advertising',
              'wx_gdpr_geo', 'A0_ad_wix_top', 'A0_ad_wix_embed_or_app', 'bc_consent_enabled', 'bc_held_first', 'bc_held_last'):
        if c not in S.columns:
            S[c] = None
    S.to_csv(os.path.join(OUT, 'beyond_sites.csv'), index=False)
    res = dict(_meta=dict(bootstrap_B=B, seed=SEED, n_raw_files=len(files), definitions=__doc__.split('Outputs')[0].strip()[:3000]))
    res['funnel'] = {a: dict(selected=int((S.architecture == a).sum()), loads_run=int(L[L.architecture == a].shape[0]), loads_ok=int(okL[okL.architecture == a].shape[0]),
                             sites_any_ok=int(S[(S.architecture == a) & (S.ok_A0 | S.ok_A1 | S.ok_A2)].shape[0]), captured=int(S[(S.architecture == a) & S.captured].shape[0]),
                             failures=Counter([('offsite' if x.offsite else ('challenge' if x.challenge_title else (f'http_{int(x.goto_status)}' if pd.notna(x.goto_status) and not (200 <= x.goto_status < 400) else ('error' if pd.isna(x.goto_status) else 'few_requests'))))
                                               for x in L[(L.architecture == a) & ~L.ok].itertuples()]))
                     for a in ARCH_CODE}
    rates = {}
    for a in ('wix', 'bigcommerce', 'gateway'):
        s = S[(S.architecture == a) & S.ok_A0]
        sb = s[s.banner_any]
        d = dict(n_A0=int(len(s)), banner=WB(s.banner_any), prechoice_ad_all=WB(s.A0_ad), prechoice_ad_banner=WB(sb.A0_ad), prechoice_ad_beacon_banner=WB(sb.A0_ad_beacon),
                 prechoice_ad_offmain_banner=WB(sb.A0_ad_offmain), prechoice_fp_collect_all=WB(s.A0_fp_collect), prechoice_fp_collect_banner=WB(sb.A0_fp_collect),
                 prechoice_ad_via_fp_banner=WB(sb.A0_ad_fp))
        c = S[(S.architecture == a) & S.ok_A1]
        ck = c[c.click_ok == True]
        d['decline'] = dict(n_A1=int(len(c)), banner_found=WB(c.banner_A1.fillna(False)), no_decline_option=int(c.no_decline_option.fillna(False).sum()), clicked=int(c.clicked.fillna(False).sum()),
                            click_ok=int(len(ck)), after_ad=WB(ck.A1_after_ad.astype(bool)), after_ad_beacon=WB(ck.A1_after_ad_beacon.astype(bool)),
                            next_page_ad=WB(ck.A1_next_ad.astype(bool)), after_fp_collect=WB(ck.A1_after_fp_collect.astype(bool)),
                            after_server_id_cookie=WB(ck.A1_after_server_id_cookie.astype(bool)),
                            pre_ad_then_after=dict(pre=int(ck.A1_pre_ad.sum()), pre_and_after=int((ck.A1_pre_ad & ck.A1_after_ad.astype(bool)).sum())),
                            after_fp_consent_states=dict(Counter(k for v in ck.A1_after_fp_gcons.dropna() for k in [x.split(':')[0] for x in v.split('|') if x])))
        p = S[(S.architecture == a) & S.ok_A0 & S.ok_A2]
        if len(p):
            import analyze as A
            d['gpc'] = dict(n_pairs=int(len(p)), A0_ad=WB(p.A0_ad), A2_ad=WB(p.A2_ad), mcnemar=A.mcnemar(p.A0_ad.astype(bool), p.A2_ad.astype(bool)),
                            diff=A.newcombe_paired(p.A2_ad.astype(bool), p.A0_ad.astype(bool)),
                            banner_sites=dict(n=int(p.banner_any.sum()), A0_ad=WB(p[p.banner_any].A0_ad), A2_ad=WB(p[p.banner_any].A2_ad)),
                            workers_gpc_injected=dict(workers=int(p.A2_workers.fillna(0).sum()), gpc_true=int(p.A2_workers_gpc_true.fillna(0).sum())))
        if a == 'wix':
            for lab, v in (('adv_denied_default', False), ('adv_allowed_default', True)):
                w = s[s.wx_default_advertising == v]
                d[lab] = dict(n=int(len(w)), banner=WB(w.banner_any), ad=WB(w.A0_ad), ad_top_frame=WB(w.A0_ad_wix_top), ad_embed_or_app_frame=WB(w.A0_ad_wix_embed_or_app),
                              gdpr_geo_true=int((w.wx_gdpr_geo == True).sum()))
            d['default_policy_unread'] = int(s.wx_default_advertising.isna().sum())
        if a == 'bigcommerce':
            e = s[s.bc_consent_enabled == True]
            d['consent_enabled'] = dict(n=int(len(e)), banner=WB(e.banner_any), prechoice_ad=WB(e.A0_ad), prechoice_ad_banner=WB(e[e.banner_any].A0_ad),
                                        held_back_first_mean=float(e.bc_held_first.mean()) if len(e) else None, held_back_last_mean=float(e.bc_held_last.mean()) if len(e) else None,
                                        held_back_released_sites=int((e.bc_held_last < e.bc_held_first).sum()))
            d['consent_not_enabled'] = dict(n=int((s.bc_consent_enabled != True).sum()), prechoice_ad=WB(s[s.bc_consent_enabled != True].A0_ad))
        # vendors and origins of pre-choice ad requests (banner sites)
        q0 = Q[(Q.architecture == a) & (Q.arm == 'A0') & Q.ad & Q.site.isin(sb.site)]
        d['prechoice_ad_vendor_sites'] = {k: int(v) for k, v in q0.groupby('vendor').site.nunique().sort_values(ascending=False).head(12).items()}
        d['prechoice_ad_origin_sites'] = {k: int(v) for k, v in q0.groupby('origin').site.nunique().items()}
        d['prechoice_ad_via_sites'] = {k: int(v) for k, v in q0.groupby('via').site.nunique().items()}
        rates[a] = d
    res['rates'] = rates
    # gcd vs gcs agreement on hits that carry both (PROTOCOL 4.5 validation)
    both = Q[Q.gcs_state.notna() & Q.gcd_state.notna()]
    res['gcd_vs_gcs'] = dict(n=int(len(both)), agree=int((both.gcs_state == both.gcd_state).sum()), table={f'{a}|{b}': int(n) for (a, b), n in both.groupby(['gcs_state', 'gcd_state']).size().items()})
    # case studies: Partytown and Zaraz sites, one record each
    cases = {}
    for r in S[S.architecture.isin(['partytown', 'zaraz'])].itertuples():
        g = Q[Q.site == r.site]
        per = {}
        for arm in ('A0', 'A1', 'A2'):
            ga = g[g.arm == arm]
            per[arm] = dict(ok=bool(getattr(r, f'ok_{arm}')), ad_vendors=sorted(ga[ga.ad].vendor.unique()), ad_by_origin={k: int(v) for k, v in ga[ga.ad].origin.value_counts().items()},
                            ad_by_phase={k: int(v) for k, v in ga[ga.ad].phase.value_counts().items()}, pt_worker_requests=int((ga.origin == 'partytown_worker').sum()),
                            zaraz_track_calls={k: int(v) for k, v in ga[ga.rule == 'Z2'].phase.value_counts().items()}, fp_collect=int(((ga.via == 'first_party') & (ga.fp_evidence == 'strong') & ga.beacon).sum()))
        la = L[L.site == r.site]
        cases[r.site] = dict(architecture=r.architecture, tier=r.tier, static_cmps=r.static_cmps, cmps_detected=r.cmps_detected, banner_A0=r.banner_A0, banner_A1=r.banner_A1,
                             click_ok=getattr(r, 'click_ok', None), reject_text=getattr(r, 'reject_text', None), b2_pt=r.b2_pt, b2_zz=r.b2_zz, arms=per,
                             loads=la[['arm', 'ok', 'goto_status', 'goto_error', 'n_requests', 'final_host', 'workers', 'workers_gpc_true', 'b2_pt_last', 'b2_zz_last', 'consent_cookies_last']].astype(str).to_dict('records'))
    json.dump(cases, open(os.path.join(OUT, 'case_studies.json'), 'w'), indent=1, default=str)
    # case-study summary (counts only, no domains; 2026-09-27 final manuscript pass): per setup, sites captured, sites with the
    # setup's runtime readout, requests from Partytown workers, Zaraz track calls, sites with any ad request (Default) and its origin
    csum = {}
    for arch in ('partytown', 'zaraz'):
        cs = {k: v for k, v in cases.items() if v['architecture'] == arch}
        cap = {k: v for k, v in cs.items() if any(a['ok'] for a in v['arms'].values())}
        def _cfg(v):
            try:
                x = json.loads(v['b2_pt'] if arch == 'partytown' else v['b2_zz'])
            except Exception:
                return False
            return bool(x and (x.get('cfg') if arch == 'partytown' else x.get('loaded')))
        a0 = {k: v['arms']['A0'] for k, v in cap.items()}
        csum[arch] = dict(selected=len(cs), captured=len(cap), readout=sum(_cfg(v) for v in cap.values()),
                          banner=sum(bool(v['banner_A0'] is True) for v in cap.values()),
                          decline_clicked=sum(bool(v['click_ok'] is True) for v in cap.values()),
                          pt_worker_requests=sum(a['pt_worker_requests'] for v in cap.values() for a in v['arms'].values()),
                          zaraz_track_calls=sum(sum(a['zaraz_track_calls'].values()) for v in cap.values() for a in v['arms'].values()),
                          sites_ad_default=sum(bool(a['ad_vendors']) for a in a0.values()),
                          sites_ad_main_thread_default=sum(bool(a['ad_by_origin'].get('main_thread')) for a in a0.values()),
                          sites_ad_subframe_default=sum(bool(a['ad_by_origin'].get('subframe')) for a in a0.values()),
                          sites_ad_after_decline=sum(bool(v['arms']['A1']['ad_by_phase'].get('next_page')) for v in cap.values()),
                          sites_ad_gpc=sum(bool(v['arms']['A2']['ad_vendors']) for v in cap.values()))
    res['case_summary'] = csum
    res['case_studies_file'] = 'case_studies.json'
    res['case_study_sites'] = sorted(cases)
    json.dump(res, open(os.path.join(OUT, 'beyond_r4.json'), 'w'), indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
    print('loads', len(L), 'ok', int(L.ok.sum()), 'sites captured', int(S.captured.sum()), {a: v['prechoice_ad_banner'] for a, v in rates.items()})


if __name__ == '__main__':
    main()
