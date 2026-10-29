"""Flatten raw/<store>__<arm>.json.gz (written by crawl.js) into analysis tables.

Outputs (in the crawl directory, or --out DIR):
  loads.csv            one row per store x arm load
  requests.csv.gz      one row per vendor request (vendor from vendor_endpoints.json) + Shopify WPM sandbox URLs
  canary_other.csv     third-party requests NOT in the vendor map that carried the canary (map gaps)
  consent_states.csv   every Shopify.customerPrivacy readout (~1 s polls + click+1/+5 + end)
  consent_events.csv   visitorConsentCollected events seen by the init script
  cmp.csv              one row per load x detected CMP (detection evidence, banner, click, declared config)
  cmp_declared.csv     one row per load x CMP x vendor: what the CMP DECLARES about that vendor pre-choice
  pixels.csv           WPM webPixelsConfigList per store (from the first successful load)
  gpc_checks.csv       per load x (frame|worker): navigator.globalPrivacyControl + injection marker
Usage: python build_tables.py [--raw DIR] [--out DIR]
"""
import csv, glob, gzip, json, os, re, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
def arg(k, d):
    return args[args.index(k) + 1] if k in args else d
RAW = arg('--raw', os.path.join(HERE, 'raw'))
OUT = arg('--out', HERE)
SIG = json.load(open(os.path.join(HERE, 'cmp_signatures.json')))
VE = json.load(open(os.path.join(HERE, 'vendor_endpoints.json')))
VEND = [(v['vendor'], re.compile(v['host_regex']), v.get('is_advertising'), v.get('figure_color_group')) for v in VE['vendors']]
VINFO = {v['vendor']: v for v in VE['vendors']}
CMP_MODE = {k: c.get('integration_mode') for k, c in SIG['cmps'].items()}
WEAK_GLOBALS = {'__tcfapi', '__cmp', 'CookieConsent'}  # generic TCF / cookieconsent globals shared by several CMPs


def strong(evs):
    return any(e in ('script', 'cookie') or (e.startswith('global:') and e[7:] not in WEAK_GLOBALS) for e in evs)
CMP_SCRIPT = {k: [re.compile(x) for x in (c.get('detect') or {}).get('script_url_regex') or []] for k, c in SIG['cmps'].items()}
CMP_COOKIES = {k: (c.get('detect') or {}).get('cookies') or [] for k, c in SIG['cmps'].items()}
AD_VENDORS = [v['vendor'] for v in VE['vendors'] if v.get('is_advertising')]


def vendor_of_host(h):
    h = (h or '').lower().lstrip('.').lstrip('*').lstrip('.')
    for name, rx, ad, col in VEND:
        if rx.search(h):
            return name
    return None


def decode_cmp(v):
    if not v or not v.startswith('3'):
        return {}
    parts = v[1:].split('_')
    head = parts[0]
    choices, purposes = (head.split('.', 1) + [''])[:2]
    def choice(ch):
        return 'declined' if ch.lower() in choices else ('accepted' if ch.upper() in choices else 'none')
    return dict(cmp_choice_m=choice('m'), cmp_choice_s=choice('s'), cmp_allow_a='A' in purposes, cmp_allow_m='M' in purposes,
                cmp_allow_p='P' in purposes, cmp_allow_s='S' in purposes, cmp_region=parts[1] if len(parts) > 1 else '',
                cmp_banner=(parts[2] == 't') if len(parts) > 2 else None, cmp_sod_region=(parts[3] == 't') if len(parts) > 3 else None)


def server_timing_cmp(h):
    if not h:
        return ''
    st = h.get('server-timing') or ''
    m = re.search(r'_cmp;desc="([^"]+)"', st)
    return m.group(1) if m else ''


def phase(t, rec):
    """pre_banner | banner_prechoice | post_click | next_page (A1); pre_choice for loads without a click."""
    if t is None:
        return ''
    nav = rec.get('nav_wall') or 0
    nxt = rec.get('next_goto_epoch')
    if nxt and t >= nxt - nav:
        return 'next_page'
    cl = (rec.get('clicks') or {}).get('t_click_epoch')
    if cl and t >= cl - nav:
        return 'post_click'
    bt = banner_t(rec)
    if bt is not None and t >= bt:
        return 'banner_prechoice'
    return 'pre_banner' if bt is not None else 'pre_choice'


def banner_t(rec):
    """Banner first visible, ms after navigation start (page clock -> navigation wall clock)."""
    b = None
    pr = rec.get('probe') or {}
    if isinstance(pr, dict) and pr.get('cs3') and pr['cs3'].get('banner'):
        b = pr['cs3']['banner']
    bw = (rec.get('banner_wait') or {}).get('banner')
    if rec.get('arm') == 'A1' and bw:
        b = bw
    if not b or b.get('t') is None:
        return None
    to = rec.get('time_origin')
    nav = rec.get('nav_wall')
    if to and nav:
        return round(to + b['t'] - nav)
    return b['t']


def detect_cmps(rec):
    """CMP detection from script URLs (requests), page globals/DOM (probe) and cookie names."""
    found = defaultdict(set)
    for r in rec.get('requests') or []:
        u = r.get('url') or ''
        for k, rxs in CMP_SCRIPT.items():
            if any(rx.search(u) for rx in rxs):
                found[k].add('script')
    for pr in (rec.get('probe_first'), rec.get('probe')):
        if isinstance(pr, dict):
            for k, v in (pr.get('cmp') or {}).items():
                for g in v.get('globals') or []:
                    found[k].add('global:' + g)
                if v.get('dom'):
                    found[k].add('dom_' + v['dom'])
    names = [c.get('n') for c in rec.get('cookies') or []]
    for k, cks in CMP_COOKIES.items():
        for pat in cks:
            p = pat.split(' ')[0]
            rx = re.compile('^' + re.escape(p).replace('\\*', '.*') + '$')
            if any(n and rx.match(n) for n in names):
                found[k].add('cookie')
    # the generic '#cookie-bar' / '.cc-window' / '.cmp-banner' selectors alone are weak evidence
    return {k: sorted(v) for k, v in found.items()}


def _merge(out, v, pre, post, detail):
    rank = {'blocked': 2, 'listed_allowed': 1, None: 0}
    cur = out.get(v)
    if not cur:
        out[v] = dict(pre=pre, post=post, detail=detail)
        return
    if rank[pre] > rank[cur['pre']]:
        cur['pre'] = pre
        cur['detail'] = detail
    if rank[post] > rank[cur['post']]:
        cur['post'] = post


def region_of(rec):
    for c in rec.get('consent') or []:
        if isinstance(c, dict) and c.get('getRegion'):
            return c['getRegion']
    return ''


def declared_by_vendor(rec, cmp):
    """What the CMP DECLARES about each vendor it lists (only for CMPs whose config we can read).
    pre  = status before any choice for this visitor; post = status after a Decline (all non-essential refused).
    status: blocked | listed_allowed. Vendors not listed are absent."""
    out = {}
    pr = (rec.get('probe_first') if rec.get('arm') == 'A1' and isinstance(rec.get('probe_first'), dict) else rec.get('probe')) or {}
    dc = (pr.get('declared') or {}) if isinstance(pr, dict) else {}
    if cmp == 'pandectes':
        # v4 (PandectesSettings / PandectesRulesSettings): blocker.patterns.blackList[cat]; defaultBlocked bitmask
        for key in ('pandectes', 'pandectes_rules'):
            p = dc.get(key)
            if not p or not p.get('blackList'):
                continue
            try:
                db = int(p.get('defaultBlocked') if p.get('defaultBlocked') is not None else (p.get('cookiesBlockedByDefault') or 0))
            except Exception:
                db = 0
            active = bool(p.get('isActive'))
            for lst_name in ('blackList', 'iframesBlackList', 'beaconsBlackList'):
                bl = p.get(lst_name) or {}
                if isinstance(bl, list):
                    bl = {'0': bl}
                for cat, pats in bl.items():
                    try:
                        c = int(cat)
                    except Exception:
                        c = 0
                    for pat in (pats or []):
                        for alt in str(pat).split('|'):
                            v = vendor_of_host(alt.strip().split('/')[0].replace('\\', ''))
                            if not v:
                                continue
                            pre = 'blocked' if active and (db & c) != 0 else 'listed_allowed'
                            post = 'blocked' if active and c != 0 else 'listed_allowed'
                            _merge(out, v, pre, post, f'v4 {key}.{lst_name}[{cat}] {alt[:60]}; defaultBlocked={db}; isActive={active}')
        # v5 (window.pandectesRulesSettings): blocker.scripts/iframes/pixels[cat]; opt-in only in regions.strict
        p5 = dc.get('pandectes_v5') or ((rec.get('pandectes_rules_file') or {}).get('settings') or {})
        if p5 and p5.get('blocker'):
            b = p5['blocker']
            active = bool(b.get('enabled'))
            reg = region_of(rec)
            strict = (p5.get('regions') or {}).get('strict') or []
            optin = bool(reg) and (reg in strict or reg[:2] in strict)
            for lst_name in ('scripts', 'iframes', 'pixels'):
                for cat, pats in (b.get(lst_name) or {}).items():
                    try:
                        c = int(cat)
                    except Exception:
                        c = 0
                    for pat in (pats or []):
                        for alt in str(pat).split('|'):
                            alt2 = re.sub(r'^https?://', '', alt.strip()).replace('\\', '')
                            v = vendor_of_host(alt2.split('/')[0].split('?')[0])
                            if not v:
                                continue
                            pre = 'blocked' if active and optin and c != 0 else 'listed_allowed'
                            post = 'blocked' if active and c != 0 else 'listed_allowed'
                            _merge(out, v, pre, post, f'v5 blocker.{lst_name}[{cat}] {alt[:60]}; region={reg}; optin_region={optin}; enabled={active}')
    if cmp == 'onetrust' and (rec.get('otautoblock') or {}).get('tags'):
        ag = ((dc.get('onetrust') or {}).get('activeGroups') or '')
        active = set(x for x in re.split(r'[,\s]+', ag) if x)
        for tg in rec['otautoblock']['tags']:
            m = re.match(r'^(?:https?:)?//([^/]+)', tg.get('tag') or '')
            if not m:
                continue
            v = vendor_of_host(m.group(1))
            if not v:
                continue
            cats = tg.get('cat') or []
            pre = 'listed_allowed' if any(c in active for c in cats) else 'blocked'
            post = 'listed_allowed' if 'C0001' in cats else 'blocked'
            _merge(out, v, pre, post, f"OtAutoBlock {tg.get('tag','')[:60]} cat={','.join(cats)} active={ag[:60]}")
    if cmp == 'cookiebot' and (rec.get('cookiebot_cfg') or {}).get('tags'):
        cb = dc.get('cookiebot') or {}
        cons = cb.get('consent') or {}
        allowed = {1}
        if cons.get('preferences'):
            allowed.add(2)
        if cons.get('statistics'):
            allowed.add(3)
        if cons.get('marketing'):
            allowed.add(4)
        auto = (cb.get('blockingmode') or '') == 'auto'
        for tg in rec['cookiebot_cfg']['tags']:
            m = re.match(r'^(?:https?:)?//([^/]+)', tg.get('url') or '')
            if not m:
                continue
            v = vendor_of_host(m.group(1))
            if not v:
                continue
            cats = set(tg.get('cat') or [])
            pre = 'blocked' if auto and not cats.issubset(allowed) else 'listed_allowed'
            post = 'blocked' if auto and not cats.issubset({1}) else 'listed_allowed'
            _merge(out, v, pre, post, f"cookiebot {tg.get('url','')[:60]} cat={sorted(cats)} blockingmode={cb.get('blockingmode')}")
    return out


def pixel_cols(p):
    """Config of the WPM pixel a request is attributed to. pixel_purposes = 'NONE' when the pixel declares none."""
    if not p:
        return dict(pixel_matched=False, pixel_type='', pixel_api='', pixel_vendor='', pixel_rc='', pixel_name='', pixel_purposes='')
    return dict(pixel_matched=True, pixel_type=p.get('type') or '', pixel_api=p.get('api') or '', pixel_vendor=p.get('vendor') or '', pixel_rc=p.get('rc') or '',
                pixel_name=(p.get('name') or '')[:60], pixel_purposes='|'.join(p.get('pp') or []) or 'NONE')


def write_csv(fn, rows, keys=None, gz=False):
    keys = keys or list(dict.fromkeys(k for r in rows for k in r))
    op = gzip.open if gz else open
    with op(fn, 'wt', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    print(f'{os.path.basename(fn)}: {len(rows)} rows')


def main():
    files = sorted(glob.glob(os.path.join(RAW, '*.json.gz')))
    loads, reqs, canary_other, cstates, cevents, cmps, cdecl, gpcs = [], [], [], [], [], [], [], []
    pixels_by_store = {}
    for fn in files:
        try:
            rec = json.load(gzip.open(fn, 'rt'))
        except Exception as e:
            print('bad', fn, e)
            continue
        sid, arm = rec.get('store_id'), rec.get('arm')
        load_id = f'{sid}__{arm}'
        rq = rec.get('requests') or []
        navs = rec.get('navigations') or []
        first_nav = [n for n in navs if n['t'] < 2000 or n is navs[0]]
        final_hdr = None
        for n in navs:
            if rec.get('next_goto_epoch') and rec.get('nav_wall') and n['t'] >= rec['next_goto_epoch'] - rec['nav_wall']:
                break
            if n.get('headers'):
                final_hdr = n['headers']
        cmp_raw = server_timing_cmp(final_hdr)
        next_hdr = None
        if rec.get('next_goto_epoch') and rec.get('nav_wall'):
            for n in navs:
                if n['t'] >= rec['next_goto_epoch'] - rec['nav_wall'] and n.get('headers'):
                    next_hdr = n['headers']
        det = detect_cmps(rec)
        pr = rec.get('probe') if isinstance(rec.get('probe'), dict) else {}
        bw = rec.get('banner_wait') or {}
        cl = rec.get('clicks') or {}
        bt = banner_t(rec)
        wpm = rec.get('wpm') or {}
        pix = wpm.get('pixels') or []
        if pix and sid not in pixels_by_store:
            for p in pix:
                pixels_by_store.setdefault(sid, []).append(dict(store_id=sid, source_arm=arm, pixel_id=p.get('id'), type=p.get('type'), runtimeContext=p.get('rc'), apiClientId=p.get('api'),
                                                          vendor=p.get('vendor') or '', privacyPurposes='|'.join(p.get('pp') or []), has_privacyPurposes_key=p.get('pp_key'), dataSharingState=p.get('dss'), name=p.get('name')))
        consent_first = next((c for c in rec.get('consent') or [] if not c.get('__err') and c.get('has_cp')), None)
        consent_end = next((c for c in reversed(rec.get('consent') or []) if not c.get('__err') and c.get('has_cp')), None)
        vreq = [r for r in rq if r.get('vendor')]
        cl_t = (cl.get('t_click_epoch') - rec['nav_wall']) if cl.get('t_click_epoch') and rec.get('nav_wall') else None
        # bot-wall / blocking: HTTP 401/403/429/503, a challenge page (hint words or challenge title) WITHOUT a Shopify
        # storefront, or a redirect off the store's site (e.g. to google.com). Hint words alone are not enough:
        # 'captcha' / 'access denied' also appear in normal storefront text (reCAPTCHA notices, policies).
        fin = (pr.get('location') or rec.get('goto_url') or '')
        try:
            fin_host = re.sub(r'^www\.', '', re.match(r'^https?://([^/?#]+)', fin).group(1).lower())
        except Exception:
            fin_host = ''
        dom = re.sub(r'^www\.', '', (rec.get('domain') or '').lower())
        def rd(h):
            p = h.split('.')
            return '.'.join(p[-3:]) if re.search(r'\.(co|com|net|org|gov|edu|ac)\.[a-z]{2}$', h) else '.'.join(p[-2:])
        offsite = bool(fin_host) and rd(fin_host) != rd(dom)
        challenge_title = bool(re.search(r'just a moment|access denied|attention required|are you a robot|verify you are human', (pr.get('title') or ''), re.I))
        blocked_hint = (rec.get('goto_status') in (401, 403, 429, 503)) or ((bool(pr.get('bot_wall_hints')) or challenge_title) and pr.get('has_shopify') is not True) or (offsite and pr.get('has_shopify') is not True)
        row = dict(load_id=load_id, store_id=sid, stratum=rec.get('stratum'), domain=rec.get('domain'), arm=arm, browser=rec.get('browser'), browser_version=rec.get('browser_version'),
                   started_at=rec.get('started_at'), url=rec.get('url'), goto_status=rec.get('goto_status'), goto_error=rec.get('goto_error') or rec.get('fatal_error'),
                   final_url=(pr.get('location') or rec.get('goto_url') or '')[:300], load_timeout=rec.get('load_timeout'),
                   t_dcl=(rec['dcl_epoch'] - rec['nav_wall']) if rec.get('dcl_epoch') and rec.get('nav_wall') else None,
                   t_load=(rec['load_epoch'] - rec['nav_wall']) if rec.get('load_epoch') and rec.get('nav_wall') else None,
                   blocked_hint=blocked_hint, offsite_redirect=offsite, final_host=fin_host, bot_wall_hints='|'.join(pr.get('bot_wall_hints') or []), title=(pr.get('title') or '')[:120],
                   has_shopify=pr.get('has_shopify'), wpm_config_found=wpm.get('found'), wpm_source=wpm.get('source'), n_pixels=len(pix),
                   n_app_pixels=sum(1 for p in pix if p.get('type') == 'APP'), n_strict=sum(1 for p in pix if p.get('rc') == 'STRICT'), n_lax=sum(1 for p in pix if p.get('rc') == 'LAX'), n_open=sum(1 for p in pix if p.get('rc') == 'OPEN'),
                   nostra=pr.get('nostra') or (rec.get('html_flags') or {}).get('nostra'),
                   cmp_header_raw=cmp_raw, **decode_cmp(cmp_raw),
                   cf_cache_status=(final_hdr or {}).get('cf-cache-status'), age=(final_hdr or {}).get('age'),
                   next_cmp_header_raw=server_timing_cmp(next_hdr),
                   cmps_detected='|'.join(sorted(k for k, e in det.items() if strong(e))),
                   cmps_weak_only='|'.join(sorted(k for k, e in det.items() if not strong(e))),
                   cmp_modes='|'.join(sorted(set(CMP_MODE.get(k) or 'X' for k, e in det.items() if strong(e)))),
                   banner_visible=bt is not None, t_banner_visible=bt, banner_how=((bw.get('banner') or {}).get('how') if arm == 'A1' else ((pr.get('cs3') or {}).get('banner') or {}).get('how')),
                   banner_cmp=((bw.get('banner') or {}).get('cmp') if arm == 'A1' else ((pr.get('cs3') or {}).get('banner') or {}).get('cmp')),
                   a1_banner_found=bw.get('found') if arm == 'A1' else None,
                   reject_found=(cl.get('find') or {}).get('found') if arm == 'A1' and bw.get('found') else None,
                   reject_text=(cl.get('find') or {}).get('text') if arm == 'A1' else None, reject_how=(cl.get('find') or {}).get('how') if arm == 'A1' else None,
                   reject_cmp=(cl.get('find') or {}).get('cmp') if arm == 'A1' else None,
                   no_decline_option=bool(rec.get('no_decline_option')) if arm == 'A1' else None,
                   click_method=cl.get('method'), t_click=cl_t,
                   banner_still_after_click=(cl.get('banner_after') or {}).get('found') if cl.get('method') else None,
                   buttons_seen='|'.join(((cl.get('find') or {}).get('buttons') or [])[:12]) if arm == 'A1' else None,
                   next_status=rec.get('next_status'), next_error=rec.get('next_error'),
                   t_next_nav=(rec['next_goto_epoch'] - rec['nav_wall']) if rec.get('next_goto_epoch') and rec.get('nav_wall') else None,
                   cp_region_first=(consent_first or {}).get('getRegion'), cp_marketing_first=(consent_first or {}).get('marketingAllowed'),
                   cp_analytics_first=(consent_first or {}).get('analyticsProcessingAllowed'), cp_sale_first=(consent_first or {}).get('saleOfDataAllowed'),
                   cp_banner_first=(consent_first or {}).get('shouldShowBanner'), cp_sod_region=(consent_first or {}).get('saleOfDataRegion'),
                   cp_marketing_end=(consent_end or {}).get('marketingAllowed'), cp_sale_end=(consent_end or {}).get('saleOfDataAllowed'),
                   cp_visitor_end=json.dumps((consent_end or {}).get('currentVisitorConsent'))[:200] if consent_end else None,
                   n_consent_events=len(((pr.get('cs3') or {}).get('ev') or [])),
                   gpc_main=pr.get('gpc'), n_requests=len(rq), n_vendor_requests=len(vreq), n_ad_requests=sum(1 for r in vreq if r.get('ad')),
                   n_ad_requests_prechoice=sum(1 for r in vreq if r.get('ad') and (cl_t is None or (r.get('t') is not None and r['t'] < cl_t))),
                   ad_vendors='|'.join(sorted(set(r['vendor'] for r in vreq if r.get('ad')))),
                   n_worker_targets=sum(1 for t in rec.get('targets') or [] if t.get('type') == 'worker'),
                   n_strict_worker_requests=sum(1 for r in rq if r.get('origin') == 'strict_worker'),
                   n_canary_requests=sum(1 for r in rq if r.get('canary')), n_canary_thirdparty=sum(1 for r in rq if r.get('canary') and r.get('tp')),
                   screenshots='|'.join(rec.get('shots') or []), errors='|'.join((rec.get('errors') or [])[:3])[:300], ms=rec.get('ms'))
        loads.append(row)
        pmap = {str(p.get('id')): p for p in pix}
        for r in rq:
            if not (r.get('vendor') or r.get('wpm')):
                if r.get('canary') and r.get('tp'):
                    canary_other.append(dict(load_id=load_id, store_id=sid, arm=arm, t=r.get('t'), host=r.get('host'), url=(r.get('url') or '')[:300], origin=r.get('origin'), full_url=r.get('full_url')))
                continue
            vi = VINFO.get(r.get('vendor')) or {}
            reqs.append(dict(load_id=load_id, store_id=sid, stratum=rec.get('stratum'), arm=arm, i=r.get('i'), t_ms=r.get('t'), phase=phase(r.get('t'), rec),
                             vendor=r.get('vendor') or 'shopify_wpm', vendor_class=vi.get('vendor_class') or ('shopify_wpm' if r.get('wpm') else ''), is_advertising=bool(r.get('ad')),
                             color_group=vi.get('figure_color_group') or '', kind=r.get('vkind') or r.get('wpm'), host=r.get('host'), url=(r.get('url') or '')[:1000],
                             method=r.get('m'), resource_type=r.get('type'), session=r.get('sess'), origin=r.get('origin'), origin_evidence=r.get('oev'),
                             pixel_id=r.get('pixel') or r.get('wpm_pixel'), sess_url=(r.get('sess_url') or '')[:200], frame_url=(r.get('frame_url') or '')[:200],
                             initiator=r.get('ini_url') or ((r.get('ini_stack') or [''])[0]), status=r.get('st'), failed=r.get('fail'), blocked_reason=r.get('blocked'),
                             has_canary=bool(r.get('canary')), has_full_url=bool(r.get('full_url')), has_path=bool(r.get('path_hit')), has_creator_token=bool(r.get('creator_token')),
                             event=('|'.join(r.get('events') or []))[:120], cookies_sent='|'.join(r.get('ck') or [])[:400], n_cookies=len(r.get('ck') or []),
                             sec_gpc=r.get('gpc_hdr'), post_len=r.get('post_len') or (len(r['post']) if r.get('post') else 0),
                             **pixel_cols(pmap.get(str(r.get('pixel') or r.get('wpm_pixel')))),
                             t_banner_visible=bt, t_click=cl_t))
        for c in rec.get('consent') or []:
            if c.get('__err'):
                cstates.append(dict(load_id=load_id, store_id=sid, arm=arm, tag=c.get('tag'), t_ms=(c['epoch'] - rec['nav_wall']) if rec.get('nav_wall') and c.get('epoch') else None, error=c['__err']))
                continue
            cstates.append(dict(load_id=load_id, store_id=sid, arm=arm, tag=c.get('tag'), t_ms=(c['epoch'] - rec['nav_wall']) if rec.get('nav_wall') and c.get('epoch') else None,
                                page_t=c.get('t'), has_shopify=c.get('has_shopify'), has_cp=c.get('has_cp'), region=c.get('getRegion'), shouldShowBanner=c.get('shouldShowBanner'),
                                saleOfDataRegion=c.get('saleOfDataRegion'), analyticsProcessingAllowed=c.get('analyticsProcessingAllowed'), marketingAllowed=c.get('marketingAllowed'),
                                preferencesProcessingAllowed=c.get('preferencesProcessingAllowed'), saleOfDataAllowed=c.get('saleOfDataAllowed'),
                                currentVisitorConsent=json.dumps(c.get('currentVisitorConsent')) if c.get('currentVisitorConsent') is not None else '',
                                trackingConsent=json.dumps(c.get('getTrackingConsent'))[:200] if c.get('getTrackingConsent') is not None else '', consentId=c.get('consentId'),
                                gpc_main=c.get('gpc'), banner_page_t=c.get('banner_t'), n_events=c.get('nev')))
        to, nav = rec.get('time_origin'), rec.get('nav_wall')
        for e in ((pr.get('cs3') or {}).get('ev') or []):
            cevents.append(dict(load_id=load_id, store_id=sid, arm=arm, page_t=e.get('t'), t_ms=round(to + e['t'] - nav) if to and nav else None, detail=e.get('d')))
        for k, evs in det.items():
            d = declared_by_vendor(rec, k)
            dc = ((rec.get('probe_first') if arm == 'A1' and isinstance(rec.get('probe_first'), dict) else pr) or {}).get('declared') or {}
            extra = {}
            if k == 'pandectes':
                p4 = dc.get('pandectes') or dc.get('pandectes_rules') or {}
                p5 = dc.get('pandectes_v5') or ((rec.get('pandectes_rules_file') or {}).get('settings') or {})
                extra = dict(pandectes_version='v5' if p5 else ('v4' if p4 else ''), blocker_active=(p5.get('blocker') or {}).get('enabled') if p5 else p4.get('isActive'),
                             default_blocked=p4.get('defaultBlocked') if p4 else '', gpc_honoured_by_cmp=(p5.get('gpc') or {}).get('enabled') if p5 else p4.get('gpcIsActive'),
                             geo=json.dumps(p4.get('geolocation'))[:200] if p4.get('geolocation') is not None else (json.dumps((p5.get('regions') or {}).get('visible')) if p5 else ''))
            if k == 'onetrust':
                ot = rec.get('otautoblock') or {}
                extra = dict(blocker_active=bool(ot.get('tags')), autoblock_url=(ot.get('url') or '')[:120], autoblock_err=ot.get('err'), active_groups=((dc.get('onetrust') or {}).get('activeGroups') or '')[:120], n_autoblock_tags=len(ot.get('tags') or []))
            if k == 'cookiebot':
                cb = dc.get('cookiebot') or {}
                extra = dict(blocker_active=(cb.get('blockingmode') == 'auto'), blockingmode=cb.get('blockingmode'), cb_consent=json.dumps(cb.get('consent'))[:150], n_config_tags=len((rec.get('cookiebot_cfg') or {}).get('tags') or []))
            cmps.append(dict(load_id=load_id, store_id=sid, arm=arm, cmp=k, integration_mode=CMP_MODE.get(k), evidence='|'.join(evs), strong_evidence=strong(evs), banner_cmp=row['banner_cmp'],
                             declared_config_readable=bool(d),
                             declared_blocked_prechoice='|'.join(sorted(v for v, x in d.items() if x['pre'] == 'blocked')),
                             declared_blocked_after_decline='|'.join(sorted(v for v, x in d.items() if x['post'] == 'blocked')),
                             declared_listed='|'.join(sorted(d)), **extra))
            for v, x in d.items():
                cdecl.append(dict(load_id=load_id, store_id=sid, arm=arm, cmp=k, integration_mode=CMP_MODE.get(k), vendor=v, is_advertising=bool((VINFO.get(v) or {}).get('is_advertising')),
                                  declared_prechoice=x['pre'], declared_after_decline=x['post'], detail=(x['detail'] or '')[:200]))
        for f in rec.get('frames_gpc') or []:
            gpcs.append(dict(load_id=load_id, store_id=sid, arm=arm, kind='frame', url=(f.get('h') or '')[:160], gpc=f.get('g'), origin=f.get('s'), err=f.get('err')))
        for wk in rec.get('workers_gpc') or []:
            v = wk.get('val') or {}
            inj = v.get('inj') or {}
            tg = next((t for t in rec.get('targets') or [] if t.get('sid') == wk.get('sid')), {})
            gpcs.append(dict(load_id=load_id, store_id=sid, arm=arm, kind='worker', url=(wk.get('url') or '')[:160], gpc=v.get('gpc'), err=wk.get('err'),
                             inject_state=(tg.get('inject') or {}).get('state'), inject_marker=bool(inj), n_globals_at_injection=inj.get('n0'), n_globals_end=v.get('n1'),
                             navigator_own=v.get('nav_own'), navigator_tag=v.get('nav_tag'), proto_has_gpc=v.get('proto_has'), proto_gpc_value=v.get('proto_val')))
    write_csv(os.path.join(OUT, 'loads.csv'), loads)
    write_csv(os.path.join(OUT, 'requests.csv.gz'), reqs, gz=True)
    write_csv(os.path.join(OUT, 'canary_other.csv'), canary_other)
    write_csv(os.path.join(OUT, 'consent_states.csv'), cstates)
    write_csv(os.path.join(OUT, 'consent_events.csv'), cevents)
    write_csv(os.path.join(OUT, 'cmp.csv'), cmps)
    write_csv(os.path.join(OUT, 'cmp_declared.csv'), cdecl)
    write_csv(os.path.join(OUT, 'pixels.csv'), [p for v in pixels_by_store.values() for p in v])
    write_csv(os.path.join(OUT, 'gpc_checks.csv'), gpcs)


if __name__ == '__main__':
    main()
