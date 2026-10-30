"""Static homepage markers for the beyond-Shopify pilot (Part B2). Pure functions, no network.

analyse(domain, final_url, headers, text) -> dict with
  platform flags (wix, bigcommerce, shopify), architecture evidence (partytown, zaraz, gateway),
  CMP / banner evidence, audience-screen fields (title, description, adult/child flags) and a product link.
"""
import html, re, urllib.parse

# ---------------------------------------------------------------- audience screen (adult / child-directed)
# Domain screens are applied BEFORE any request (screen_http.py); text screens after the one homepage GET.
ADULT_DOMAIN = re.compile(
    r"(porn|xxx|sextoy|sexshop|adulttoy|erotic|fetish|hentai|dildo|vibrator|xvideo|xhamster|xnxx|redtube|youporn|"
    r"spankbang|chaturbate|stripchat|bongacams|livejasmin|camsoda|onlyfans|fansly|rule34|nsfw|brazzers|escort|nude|"
    r"naked|milf|tube8|eporner|motherless|tnaflix|fapello|hanime|jerk|boobs|pussy|dating|hookup|sugardadd|bdsm|"
    r"camgirl|sexcam|livesex|sex\.|sexy|slut|cuckold|swinger|ashleymadison|adultfriend|playboy|hustler|kink)", re.I)
CHILD_DOMAIN = re.compile(r"(kids|kid\.|toys|toddler|children|preschool|kinder|junior|abcya|pbskids|nickjr|"
                          r"disneyjunior|cartoonnetwork|coolmath|roblox|poki\.|friv|abcmouse|starfall|funbrain|"
                          r"splashlearn|brainpop|kiddle|kidzsearch|prodigygame|lego\.|miniclip|y8\.|crazygames|kizi)",
                          re.I)
ADULT_RE = re.compile(r"\b(porn\w*|xxx|sex\s*toys?|adult\s*(?:toys?|store|shop|products|content|videos?|site)|sex\s*shop|"
                      r"erotic\w*|fetish\w*|bdsm|vibrators?|dildos?|nsfw|hentai|onlyfans|escorts?|masturbat\w*|"
                      r"sexual\s+wellness|kink\w*|nude\w*|camgirls?|sex\s*cams?|hookups?|18\+)\b", re.I)
CHILD_RE = re.compile(r"\b(kids?|kid'?s|toys?|children'?s?|child|preschool|tweens?|toddlers?|for\s+kids|"
                      r"games\s+for\s+kids|kindergarten)\b", re.I)
ADULT_AUDIENCE = re.compile(r"\b(men'?s?|women'?s?|adults?|mom|moms|mothers?|parents?|dad|dads|family|teachers?|"
                            r"doctors?|clinic|hospital|lawyers?|attorneys?)\b", re.I)
RE_RATING = re.compile(r"<meta[^>]+name=[\"']rating[\"'][^>]*content=[\"'](adult|mature|RTA-5042-1996-1400-1577-RTA)[\"']", re.I)
RE_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
RE_DESC = re.compile(r"<meta[^>]+name=[\"']description[\"'][^>]*content=[\"']([^\"']*)[\"']", re.I)
RE_DESC2 = re.compile(r"<meta[^>]+content=[\"']([^\"']*)[\"'][^>]*name=[\"']description[\"']", re.I)
RE_OGSITE = re.compile(r"<meta[^>]+property=[\"']og:site_name[\"'][^>]*content=[\"']([^\"']*)[\"']", re.I)
RE_LANG = re.compile(r"<html[^>]*\slang=[\"']?([A-Za-z-]{2,10})", re.I)

# ---------------------------------------------------------------- consent tools (static signatures)
CMP_SIGS = {
    "onetrust": ["cdn.cookielaw.org", "otsdkstub", "optanon", "onetrust"],
    "cookiebot": ["consent.cookiebot.com", "consent.cookiebot.eu", "cookiebot"],
    "usercentrics": ["usercentrics"], "didomi": ["didomi"], "quantcast": ["quantcast.mgr.consensu.org", "cmp.quantcast.com", "quantcast choice"],
    "inmobi_choice": ["cmp.inmobi.com"], "sourcepoint": ["sourcepoint", "sp-prod.net", "privacy-mgmt.com"],
    "trustarc": ["trustarc", "truste.com", "consent.trustarc"], "termly": ["termly.io"], "osano": ["cmp.osano.com", "osano.com"],
    "iubenda": ["iubenda"], "cookieyes": ["cookieyes", "cdn-cookieyes.com", "cookie-law-info"], "complianz": ["complianz", "cmplz"],
    "axeptio": ["axeptio"], "borlabs": ["borlabs"], "cookiefirst": ["cookiefirst"], "cookiehub": ["cookiehub"],
    "cookie_script": ["cookie-script.com"], "consentmanager_net": ["consentmanager.net", "delivery.consentmanager"],
    "klaro": ["klaro"], "tarteaucitron": ["tarteaucitron"], "ketch": ["ketchcdn", "global.ketchcdn.com"],
    "transcend": ["transcend.io", "transcend-cdn"], "securiti": ["securiti.ai"], "civic": ["civiccomputing", "cookiecontrol"],
    "cookie_information": ["cookieinformation.com", "policy.app.cookieinformation"], "commanders_act": ["trustcommander", "tagcommander", "commander1.com"],
    "google_funding_choices": ["fundingchoicesmessages.google.com"], "clickio": ["clickio.com/clickioconsent", "clickiocmp", "clickio.mgr.consensu"],
    "sirdata": ["cmp.sirdata"], "liveramp": ["privacymanager.io", "gdpr-wrapper"], "cookie_notice_wp": ["cookie-notice", "cn-cookie-notice"],
    "gdpr_cookie_compliance_wp": ["moove_gdpr", "gdpr-cookie-compliance"], "real_cookie_banner_wp": ["real-cookie-banner", "rcb-banner"],
    "cookieconsent_osano_oss": ["cookieconsent.min.js", "cookieconsent2", "cc_banner"], "orestbida_cc": ["cookieconsent.umd", "orestbida"],
    "admiral": ["getadmiral.com"], "piwik_pro_consent": ["piwik.pro"], "seers": ["seersco"], "enzuzo": ["enzuzo"], "cookieyes_legacy": ["cky-consent"],
    "c15t": ["c15t"], "pandectes": ["pandectes"], "consentmo": ["consentmo.com", "consentmo-gdpr", "gdpr-legal-cookie", "isenselabs"], "hubspot_banner": ["hs-banner", "hubspot-cookie"],
    "shopify_privacy_banner": ["shopify-privacy-banner"], "wix_banner": [], "bigcommerce_consent": [], "zaraz_cmp": [],
}
TCF_RE = re.compile(r"__tcfapi|consensu\.org", re.I)
GPP_RE = re.compile(r"__gpp\b", re.I)
GCM_DEFAULT_RE = re.compile(r"""gtag\(\s*['"]consent['"]\s*,\s*['"]default['"]""", re.I)

# ---------------------------------------------------------------- platforms
WIX_RE = re.compile(r"static\.parastorage\.com|wix-thunderbolt|wixBiSession|viewerModel|Wix\.com Website Builder", re.I)
BC_RE = re.compile(r"cdn\d*\.bigcommerce\.com|stencil-utils|window\.BCData|BCData\s*=|bigcommerce\.com/s-", re.I)
SHOPIFY_RE = re.compile(r"Shopify\.shop\s*=|cdn\.shopify\.com|/cdn/shop/|web-pixels-manager", re.I)

# ---------------------------------------------------------------- Partytown
PT_SCRIPT_RE = re.compile(r"<script\b[^>]*\btype\s*=\s*[\"']?text/partytown[\"'\s>][^>]*>(.*?)</script>", re.I | re.S)
PT_LIB_RE = re.compile(r"~partytown|partytown-(?:sw|atomics|ww-sw|ww-atomics|media|config)\b|@builder\.io/partytown|@qwik\.dev/partytown|"
                       r"partytown\s*=\s*\{|window\.partytown|web-worker-offloading|nuxt-partytown|astrojs/partytown|data-partytown", re.I)
PT_FORWARD_RE = re.compile(r"forward\s*[:=]\s*\[([^\]]{0,400})\]", re.I)
SRC_RE = re.compile(r"\bsrc\s*=\s*[\"']([^\"']+)[\"']", re.I)

# ---------------------------------------------------------------- Zaraz
ZARAZ_RE = re.compile(r"/cdn-cgi/zaraz/|zarazData|zaraz\.(?:track|set|ecommerce|consent|showConsentModal)|\bzaraz\s*=", re.I)
ZARAZ_PATH_RE = re.compile(r"/cdn-cgi/zaraz/[a-z0-9_./-]*", re.I)
ZARAZ_GCM_RE = re.compile(r"""zaraz\.set\(\s*["']google_consent_(default|update)""", re.I)

# ---------------------------------------------------------------- first-party tag gateways
GOOGLE_HOSTS = re.compile(r"(^|\.)(googletagmanager\.com|google-analytics\.com|googleadservices\.com|googlesyndication\.com|"
                          r"doubleclick\.net|google\.com|gstatic\.com|googleapis\.com|googleusercontent\.com)$", re.I)
URL_RE = re.compile(r"""(?:https?:)?//([a-z0-9][a-z0-9.-]*\.[a-z]{2,})(/[^"'\s<>\\)]*)?""", re.I)
REL_TAG_RE = re.compile(r"""["'](/[^"'\s<>]{0,120}?(?:gtm\.js|gtag/js)[^"'\s<>]*)["']""", re.I)
GTAG_ID_RE = re.compile(r"[?&]id=((?:GTM|G|AW|DC|GT)-[A-Z0-9]{4,})", re.I)
GTM_SNIPPET_HOST_RE = re.compile(r"""['"]https?://([a-z0-9.-]+)/[^'"]*?(?:gtm\.js\?id=|gtag/js\?id=)['"]?""", re.I)
B64_ID_RE = re.compile(r"(aWQ9R1RNL|aWQ9Ry0|aWQ9QVct)")          # base64 of "id=GTM-", "id=G-", "id=AW-" (custom loaders)
SST_CONFIG_RE = re.compile(r"""(server_container_url|transport_url)['"]?\s*[:,]\s*['"](https?://[^'"]+)['"]""", re.I)
CAPIG_RE = re.compile(r"""https?://(capig\.[a-z0-9.-]+|[a-z0-9.-]*capig[a-z0-9.-]*\.[a-z]{2,})""", re.I)
KNOWN_SST_HOSTS = re.compile(r"(\.|^)(stape\.io|stape\.net|stape\.eu|taggrs\.io|addingwell\.com|tagserver\.|jentis\.com|"
                             r"elevar\.io|tagmanager-proxy)", re.I)

# ---------------------------------------------------------------- vendor hints in inline code (which ad tags)
VENDOR_HINTS = {
    "google_tag": re.compile(r"gtag\(|googletagmanager|GTM-[A-Z0-9]{4,}|\bG-[A-Z0-9]{6,}", re.I),
    "google_ads": re.compile(r"\bAW-\d{6,}|googleadservices|doubleclick", re.I),
    "meta": re.compile(r"fbq\(|connect\.facebook\.net|fbevents\.js", re.I),
    "tiktok": re.compile(r"ttq\.|analytics\.tiktok\.com", re.I),
    "pinterest": re.compile(r"pintrk\(|s\.pinimg\.com/ct", re.I),
    "snap": re.compile(r"snaptr\(|sc-static\.net", re.I),
    "microsoft_uet": re.compile(r"bat\.bing\.com|uetq", re.I),
    "linkedin": re.compile(r"snap\.licdn\.com|_linkedin_partner_id", re.I),
    "x_twitter": re.compile(r"static\.ads-twitter\.com|twq\(", re.I),
    "reddit": re.compile(r"rdt\(|redditstatic\.com/ads", re.I),
    "criteo": re.compile(r"criteo", re.I),
    "hotjar": re.compile(r"hotjar", re.I),
    "clarity": re.compile(r"clarity\.ms", re.I),
}

# ---------------------------------------------------------------- Wix / BigCommerce consent config
WIX_BANNER_RE = re.compile(r"cookie[_-]?(?:consent|banner)|consentPolicy|consent-policy|ccpa|gdpr|privacy[_-]?center", re.I)
BC_CONSENT_RE = re.compile(r"consentManagerStoreConfig|data-bc-cookie-consent|/api/storefront/consent|"
                           r"improvedConsentManagerEnabled|c15t-consent|storefront/consent-manager", re.I)   # consentManagerTranslations is on every store
WIX_POLICY_RE = re.compile(r'"siteConsentPolicy"\s*:\s*(\{[^{}]*\})')
GENERIC_BANNER_RE = re.compile(r"""(?:id|class)=["'][^"']*(?:cookie[-_]?(?:banner|consent|notice|bar|popup|law)|gdpr[-_]?(?:banner|consent|cookie)|consent[-_]?banner)""", re.I)
BC_CAT_RE = re.compile(r"""data-bc-cookie-consent\s*=\s*["']?(\d)""", re.I)
PROD_WIX_RE = re.compile(r"""href=["']((?:https?://[^"'/]+)?/product-page/[^"'?#\s]+)""", re.I)
PROD_BC_RE = re.compile(r"""<a[^>]+href=["']([^"'#\s]+)["'][^>]*(?:data-event-type=["']product-click["']|class=["'][^"']*card-figure__link)""", re.I)
PROD_BC_RE2 = re.compile(r"""<a[^>]+(?:data-event-type=["']product-click["']|class=["'][^"']*card-figure__link)[^>]*href=["']([^"'#\s]+)["']""", re.I)
PROD_GENERIC_RE = re.compile(r"""href=["']((?:https?://[^"'/]+)?/(?:products?|shop|p)/[a-z0-9][^"'?#\s]{2,120})["']""", re.I)


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(s or "")).strip()[:200]


def reg_domain(host):
    """Crude registrable domain: last two labels, or last three for common 2nd-level public suffixes."""
    host = (host or '').lower().strip('.')
    parts = host.split('.')
    if len(parts) >= 3 and (parts[-2] in ('co', 'com', 'net', 'org', 'gov', 'ac', 'edu', 'or', 'ne', 'go') and len(parts[-1]) == 2):
        return '.'.join(parts[-3:])
    return '.'.join(parts[-2:])


def cmp_signals(low):
    found = sorted(k for k, sigs in CMP_SIGS.items() if sigs and any(s in low for s in sigs))
    return found


def gateway_signals(text, site_rd):
    """First-party (or proxied) Google tag serving and server-side tagging hints."""
    out = dict(fp_tag_urls=[], proxy_tag_urls=[], sst_endpoints=[], custom_loader=False, capig=[], tag_ids=[])
    seen = set()
    cand = []
    for m in URL_RE.finditer(text):
        host = m.group(1).lower(); path = m.group(2) or ''
        cand.append((host, path))
    for m in REL_TAG_RE.finditer(text):
        if m.group(1).startswith('//'):     # protocol-relative URL (host handled by URL_RE); fixed 27 Sep 03:30 PDT:
            continue                        # '//www.googletagmanager.com/gtag/js' was read as a same-host path
        cand.append(('', m.group(1)))
    for host, path in cand:
        pl = path.lower()
        is_tag = ('gtm.js' in pl or 'gtag/js' in pl) and GTAG_ID_RE.search(path)
        is_b64 = bool(B64_ID_RE.search(path))
        if not (is_tag or is_b64):
            continue
        if host and GOOGLE_HOSTS.search(host):
            continue
        key = (host, path[:160])
        if key in seen:
            continue
        seen.add(key)
        url = ('//' + host if host else '') + path[:200]
        first_party = (not host) or reg_domain(host) == site_rd
        (out['fp_tag_urls'] if first_party else out['proxy_tag_urls']).append(url)
        if is_b64:
            out['custom_loader'] = True
        idm = GTAG_ID_RE.search(path)
        if idm:
            out['tag_ids'].append(idm.group(1).upper())
    for m in GTM_SNIPPET_HOST_RE.finditer(text):
        h = m.group(1).lower()
        if not GOOGLE_HOSTS.search(h):
            u = '//' + h + '/(gtm snippet)'
            if u not in out['fp_tag_urls'] and u not in out['proxy_tag_urls']:
                (out['fp_tag_urls'] if reg_domain(h) == site_rd else out['proxy_tag_urls']).append(u)
    for m in SST_CONFIG_RE.finditer(text):
        out['sst_endpoints'].append(m.group(2)[:120])
    for m in CAPIG_RE.finditer(text):
        out['capig'].append(m.group(1).lower())
    out['known_sst_host'] = sorted({h for h, p in cand if KNOWN_SST_HOSTS.search(h)})
    for k in ('fp_tag_urls', 'proxy_tag_urls', 'sst_endpoints', 'capig', 'tag_ids'):
        out[k] = sorted(set(out[k]))[:12]
    out['any'] = bool(out['fp_tag_urls'] or out['proxy_tag_urls'] or out['sst_endpoints'] or out['capig'])
    return out


def partytown_signals(text):
    scripts = PT_SCRIPT_RE.findall(text)
    tags = re.findall(r"<script\b[^>]*\btype\s*=\s*[\"']?text/partytown[^>]*>", text, re.I)
    srcs = []
    for t in tags:
        m = SRC_RE.search(t)
        if m:
            srcs.append(m.group(1)[:160])
    inline_vendors = sorted({k for k, rx in VENDOR_HINTS.items() for body in scripts if rx.search(body or '')})
    src_vendors = sorted({k for k, rx in VENDOR_HINTS.items() for s in srcs if rx.search(s)})
    fw = PT_FORWARD_RE.search(text) if PT_LIB_RE.search(text) else None
    return dict(n_scripts=len(tags), srcs=srcs[:10], vendors=sorted(set(inline_vendors) | set(src_vendors)),
                lib=bool(PT_LIB_RE.search(text)), forward=(fw.group(1).strip()[:200] if fw else ''),
                any=len(tags) > 0)


def zaraz_signals(text, headers):
    paths = sorted(set(p[:60] for p in ZARAZ_PATH_RE.findall(text)))[:6]
    gcm = sorted(set(ZARAZ_GCM_RE.findall(text)))
    hit = bool(ZARAZ_RE.search(text))
    return dict(any=hit, paths=paths, custom_path=hit and not paths, gcm=gcm,
                cloudflare=('cf-ray' in headers) or ('cloudflare' in headers.get('server', '').lower()))


def wix_signals(text, headers):
    low = text.lower()
    plat = bool(WIX_RE.search(text)) or 'x-wix-request-id' in headers
    # banner / consent config markers inside the viewer model (calibrated on the first fetched Wix pages)
    snippets = []
    for kw in ('cookieconsent', 'cookie-consent', 'cookiebanner', 'cookie-banner', 'consentpolicy', 'consent-policy',
               'ccpa', 'privacycenter', 'isgdpr', 'gdpr', 'usercentrics', 'cookiebot'):
        i = low.find(kw)
        if i >= 0:
            snippets.append(kw)
    integ = sorted({k for k, rx in VENDOR_HINTS.items() if rx.search(text)})
    pol = None
    m = WIX_POLICY_RE.search(text)
    if m:
        try:
            import json as _j
            pol = _j.loads(m.group(1))
        except Exception:
            pol = None
    banner = bool(pol) and any(pol.get(k) is False for k in ('functional', 'analytics', 'advertising'))
    return dict(platform=plat, consent_keywords=snippets, vendors=integ, site_consent_policy=pol, native_banner_requires_consent=banner,
                gcm_bridge=('gdprEnforcedGeo' in text), html_embeds=text.count('wix/htmlEmbeds'))


def bc_signals(text, headers):
    plat = bool(BC_RE.search(text)) or any(k.startswith('x-bc-') for k in headers)
    consent = sorted(set(m.lower() for m in BC_CONSENT_RE.findall(text)))
    cats = {}
    for c in BC_CAT_RE.findall(text):
        cats[c] = cats.get(c, 0) + 1
    integ = sorted({k for k, rx in VENDOR_HINTS.items() if rx.search(text)})
    enabled = 'consentmanagerstoreconfig' in consent
    return dict(platform=plat, consent=consent, consent_enabled=enabled, consent_categories=cats, vendors=integ)


def product_link(text, final_url, kind):
    fu = urllib.parse.urlsplit(final_url)
    rxs = {'wix': [PROD_WIX_RE], 'bigcommerce': [PROD_BC_RE, PROD_BC_RE2]}.get(kind, [PROD_GENERIC_RE])
    for rx in rxs:
        for m in rx.finditer(text):
            u = html.unescape(m.group(1))
            full = urllib.parse.urljoin(final_url, u)
            pu = urllib.parse.urlsplit(full)
            if pu.scheme in ('http', 'https') and reg_domain(pu.hostname or '') == reg_domain(fu.hostname or '') and pu.path not in ('', '/'):
                if re.search(r"(cart|checkout|login|account|wishlist|compare|search|\.(?:jpg|png|webp|pdf)$)", pu.path, re.I):
                    continue
                return full[:300]
    return ''


def analyse(domain, final_url, headers, text):
    h = {k.lower(): v for k, v in headers.items()}
    low = text.lower()
    fu = urllib.parse.urlsplit(final_url)
    site_rd = reg_domain(fu.hostname or domain)
    title = clean(RE_TITLE.search(text).group(1) if RE_TITLE.search(text) else '')
    dm = RE_DESC.search(text) or RE_DESC2.search(text)
    desc = clean(dm.group(1) if dm else '')
    og = RE_OGSITE.search(text)
    site = clean(og.group(1) if og else '')
    lm = RE_LANG.search(text)
    audience = ' '.join([title, desc, site])
    adult = bool(RE_RATING.search(text)) or bool(ADULT_RE.search(audience)) or bool(ADULT_DOMAIN.search(domain))
    t2 = ' '.join([title, site])
    child_txt = bool(CHILD_RE.search(t2)) and not ADULT_AUDIENCE.search(t2)
    child_dom = bool(CHILD_DOMAIN.search(domain))
    wix = wix_signals(text, h)
    bc = bc_signals(text, h)
    pt = partytown_signals(text)
    zz = zaraz_signals(text, h)
    gw = gateway_signals(text, site_rd)
    cmps = cmp_signals(low)
    if bc['platform'] and bc['consent_enabled']:
        cmps.append('bigcommerce_consent')
    if wix['platform'] and wix['native_banner_requires_consent']:
        cmps.append('wix_banner')
    generic = bool(GENERIC_BANNER_RE.search(text))
    kind = 'wix' if wix['platform'] else 'bigcommerce' if bc['platform'] else 'generic'
    return dict(
        final_host=(fu.hostname or '').lower(), cross_site_redirect=(site_rd != reg_domain(domain)),
        title=title, description=desc[:160], site_name=site, lang=(lm.group(1) if lm else ''),
        adult_flag=adult, child_flag_domain=child_dom, child_flag_text=child_txt,
        shopify=bool(SHOPIFY_RE.search(text)) or 'x-shopid' in h,
        wix=wix, bigcommerce=bc, partytown=pt, zaraz=zz, gateway=gw,
        cmps=sorted(set(cmps)), generic_banner_markup=generic, tcf=bool(TCF_RE.search(text)), gpp=bool(GPP_RE.search(text)),
        gcm_default=bool(GCM_DEFAULT_RE.search(text)),
        vendors=sorted({k for k, rx in VENDOR_HINTS.items() if rx.search(text)}),
        product_url=product_link(text, final_url, kind) if kind != 'generic' else '',
        server=h.get('server', '')[:40], powered_by=h.get('x-powered-by', '')[:40],
        body_len=len(text))
