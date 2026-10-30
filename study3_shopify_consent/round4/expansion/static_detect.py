"""Static (no JavaScript) detection of the three blocklist CMPs and of their published blocklists.

Inputs are the homepage HTML (one GET) and, for OneTrust and Cookiebot, the blocklist file that the page
tells every visitor's browser to load from the CMP vendor's own CDN (OtAutoBlock.js on cdn.cookielaw.org;
configuration.js on consentcdn.cookiebot.com). Pandectes publishes its lists inline in the page.

The rules mirror crawl/build_tables.py:declared_by_vendor (the main crawl's "declared" logic), so that a
store is a screening candidate here under the same definition that put stores in the main study's
blocklist row, except that the visitor-dependent part (OneTrust active groups, Cookiebot consent state)
cannot be known without running the page and is left to the measurement crawl.

Signatures: crawl/cmp_signatures.json (script_url_regex, globals). Vendor map: crawl/vendor_endpoints.json.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
CRAWL = os.path.normpath(os.path.join(HERE, "..", "..", "crawl"))
SIG = json.load(open(os.path.join(CRAWL, "cmp_signatures.json")))["cmps"]
VE = json.load(open(os.path.join(CRAWL, "vendor_endpoints.json")))
VEND = [(v["vendor"], re.compile(v["host_regex"]), bool(v.get("is_advertising"))) for v in VE["vendors"]]
TARGET = ("pandectes", "onetrust", "cookiebot")
SCRIPT_RX = {k: [re.compile(x) for x in (c.get("detect") or {}).get("script_url_regex") or []] for k, c in SIG.items()}
GLOBALS = {k: [g for g in (c.get("detect") or {}).get("globals") or [] if g not in ("__tcfapi", "__cmp", "CookieConsent")]
           for k, c in SIG.items()}
CA_REGION = "USCA"  # Shopify getRegion() for our California vantage (as recorded in the main crawl)


def vendor_of_host(h):
    h = (h or "").lower().lstrip(".").lstrip("*").lstrip(".")
    for name, rx, ad in VEND:
        if rx.search(h):
            return name, ad
    return None, False


def _host_of_pattern(alt):
    a = re.sub(r"^https?://", "", alt.strip()).replace("\\", "")
    a = a.lstrip("/")
    return a.split("/")[0].split("?")[0]


def json_after(text, marker):
    i = text.find(marker)
    if i < 0:
        return None
    i += len(marker)
    while i < len(text) and text[i] in " \t\r\n":
        i += 1
    try:
        return json.JSONDecoder().raw_decode(text, i)[0]
    except Exception:
        return {"_parse_error": True}


RE_URLISH = re.compile(r"""(?:src|href)\s*=\s*["']([^"']{4,600})|((?:https?:)?//[a-z0-9.-]+\.[a-z]{2,}[^\s"'<>)]{0,600})""", re.I)


def url_blob(text):
    """All URL-like strings in the page (attributes and quoted absolute URLs), one per line; escaped slashes undone."""
    t = text.replace("\\/", "/")
    seen = set()
    for m in RE_URLISH.finditer(t):
        seen.add(m.group(1) or m.group(2))
    return "\n".join(seen)


def detect_cmps(text):
    """Static CMP detection: script URLs from the signatures anywhere in the HTML, or an assignment to a
    CMP-specific global (window.X = / X =) in an inline script."""
    out = {}
    blob = url_blob(text)
    for k in SIG:
        ev = []
        if any(rx.search(blob) for rx in SCRIPT_RX.get(k, [])):
            ev.append("script")
        for g in GLOBALS.get(k, []):
            if g in text and re.search(r"\b" + re.escape(g) + r"\s*=", text):
                ev.append("global:" + g)
                break
        if ev:
            out[k] = ev
    # extra evidence for the three targets
    if "pandectes" not in out and re.search(r"shopify://apps/pandectes", text):
        out["pandectes"] = ["app_block"]
    if "cookiebot" not in out and re.search(r"consent\.cookiebot\.(com|eu)/uc\.js", text):
        out["cookiebot"] = ["script"]
    return out


def pandectes_config(text):
    """Blocklists published inline by Pandectes (v4: PandectesSettings / PandectesRulesSettings; v5: pandectesRulesSettings)."""
    res = {"version": "", "blocker_active": None, "entries": [], "parse_error": False, "strict_has_ca": None,
           "default_blocked": None}
    found = False
    for key, marker in (("pandectes", "window.PandectesSettings ="), ("pandectes_rules", "window.PandectesRulesSettings ="),
                        ("pandectes", "PandectesSettings="), ("pandectes_rules", "PandectesRulesSettings=")):
        o = json_after(text, marker)
        if o is None:
            continue
        found = True
        if o.get("_parse_error"):
            res["parse_error"] = True
            continue
        b = o.get("blocker") or {}
        pat = b.get("patterns") or {}
        try:
            db = int(b.get("defaultBlocked") if b.get("defaultBlocked") is not None else ((o.get("banner") or {}).get("cookiesBlockedByDefault") or 0))
        except Exception:
            db = 0
        active = bool(b.get("isActive"))
        res["version"] = res["version"] or "v4"
        res["blocker_active"] = bool(res["blocker_active"]) or active
        res["default_blocked"] = db if res["default_blocked"] is None else res["default_blocked"]
        geo = o.get("geolocation") or {}
        if isinstance(geo, dict) and geo:
            res["v4_geo_only"] = sorted(k for k, v in geo.items() if v is True and k != "globalVisibility")
            res["v4_global_visibility"] = geo.get("globalVisibility")
        for lst in ("blackList", "iframesBlackList", "beaconsBlackList"):
            bl = pat.get(lst) or {}
            if isinstance(bl, list):
                bl = {"0": bl}
            for cat, pats in bl.items():
                try:
                    c = int(cat)
                except Exception:
                    c = 0
                for p in pats or []:
                    for alt in str(p).split("|"):
                        v, ad = vendor_of_host(_host_of_pattern(alt))
                        if not v:
                            continue
                        res["entries"].append(dict(vendor=v, ad=ad, src=f"v4 {key}.{lst}[{cat}]", pattern=alt[:80],
                                                   pre=bool(active and (db & c) != 0), post=bool(active and c != 0)))
    for marker in ("window.pandectesRulesSettings =", "pandectesRulesSettings="):
        o = json_after(text, marker)
        if o is None:
            continue
        found = True
        if o.get("_parse_error"):
            res["parse_error"] = True
            continue
        res["version"] = "v5"
        b = o.get("blocker") or {}
        active = bool(b.get("enabled"))
        res["blocker_active"] = active
        strict = (o.get("regions") or {}).get("strict") or []
        optin = CA_REGION in strict or CA_REGION[:2] in strict
        res["strict_has_ca"] = optin
        for lst in ("scripts", "iframes", "pixels"):
            for cat, pats in (b.get(lst) or {}).items():
                try:
                    c = int(cat)
                except Exception:
                    c = 0
                for p in pats or []:
                    for alt in str(p).split("|"):
                        v, ad = vendor_of_host(_host_of_pattern(alt))
                        if not v:
                            continue
                        res["entries"].append(dict(vendor=v, ad=ad, src=f"v5 blocker.{lst}[{cat}]", pattern=alt[:80],
                                                   pre=bool(active and optin and c != 0), post=bool(active and c != 0)))
        break
    return res if found else None


RE_OTAB = re.compile(r"https?://cdn\.cookielaw\.org/consent/([0-9a-f-]{20,})(?:-test)?/OtAutoBlock\.js", re.I)
RE_OT_DS = re.compile(r"data-domain-script=[\"']([0-9a-f-]{20,}(?:-test)?)[\"']", re.I)
RE_CB_TAG = re.compile(r"<script[^>]*consent\.cookiebot\.(?:com|eu)/uc\.js[^>]*>", re.I)


def onetrust_page(text):
    m = RE_OTAB.search(text)
    ds = RE_OT_DS.search(text)
    return {"autoblock_url": m.group(0) if m else "", "domain_script": ds.group(1) if ds else "",
            "shopify_app": bool(re.search(r"onetrust-consent-management-\d+/assets/storefront-consent\.js|shopify://apps/onetrust", text, re.I)),
            "sdk_stub": "otSDKStub.js" in text}


def cookiebot_page(text):
    m = RE_CB_TAG.search(text)
    if not m:
        return {"tag": False, "cbid": "", "blockingmode": "", "georegions": "", "shopify_app": bool(re.search(r"shopify://apps/cookiebot", text, re.I))}
    tag = m.group(0)
    g = lambda a: (re.search(a + r"\s*=\s*[\"']([^\"']*)[\"']", tag, re.I) or [None, ""])[1]
    return {"tag": True, "cbid": g("data-cbid"), "blockingmode": g("data-blockingmode").lower(), "georegions": g("data-georegions")[:300],
            "cdn_eu": "cookiebot.eu" in tag.lower(),
            "shopify_app": bool(re.search(r"shopify://apps/cookiebot|cookiebot-[a-z-]*\d+/assets", text, re.I))}


def parse_otautoblock(txt):
    t = txt.replace('\\"', '"').replace("\\/", "/")
    out = []
    for m in re.finditer(r'\{[^{}]*?"Tag"\s*:\s*"([^"]*)"[^{}]*?"CategoryId"\s*:\s*\[([^\]]*)\]', t):
        out.append({"tag": m.group(1)[:300], "cat": re.findall(r'"([^"]+)"', m.group(2))})
        if len(out) >= 2000:
            break
    return out


def parse_cookiebot_config(txt):
    out = []
    for m in re.finditer(r'tags\.push\(\{[^}]*?url:"([^"]*)"[^}]*?cat:\[([^\]]*)\]', txt):
        if m.group(1):
            out.append({"url": m.group(1)[:300], "cat": [int(x) for x in m.group(2).split(",") if x.strip().isdigit()]})
        if len(out) >= 3000:
            break
    return out


def onetrust_entries(tags):
    ents = []
    for tg in tags:
        m = re.match(r"^(?:https?:)?//([^/]+)", tg.get("tag") or "")
        if not m:
            continue
        v, ad = vendor_of_host(m.group(1))
        if not v:
            continue
        cats = tg.get("cat") or []
        # post = blocked after 'reject all' unless strictly necessary; pre depends on active groups (unknown statically)
        ents.append(dict(vendor=v, ad=ad, src="OtAutoBlock", pattern=(tg.get("tag") or "")[:80], cat=",".join(cats),
                         pre=None, post="C0001" not in cats))
    return ents


def cookiebot_entries(tags, blockingmode):
    auto = blockingmode == "auto"
    ents = []
    for tg in tags:
        m = re.match(r"^(?:https?:)?//([^/]+)", tg.get("url") or "")
        if not m:
            continue
        v, ad = vendor_of_host(m.group(1))
        if not v:
            continue
        cats = set(tg.get("cat") or [])
        ents.append(dict(vendor=v, ad=ad, src="cookiebot configuration.js", pattern=(tg.get("url") or "")[:80],
                         cat=",".join(map(str, sorted(cats))), pre=None, post=bool(auto and not cats.issubset({1}))))
    return ents


def summarize(entries):
    ad = sorted({e["vendor"] for e in entries if e["ad"] and e["post"]})
    pre = sorted({e["vendor"] for e in entries if e["ad"] and e["pre"] is True})
    unknown = any(e["ad"] and e["post"] and e["pre"] is None for e in entries)
    return {"ad_vendors_blocklisted": ad, "ad_vendors_blocked_prechoice_ca": pre,
            "prechoice_ca": ("yes" if pre else ("unknown" if unknown else "no")) if ad else ""}
