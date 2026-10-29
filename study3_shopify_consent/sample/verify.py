"""Step 3: verify DNS-flagged domains as live Shopify storefronts with ONE homepage GET.

Politeness / ethics
  * GET only; no cookies kept between sites (fresh requests.Session per site); no forms, logins,
    cart or checkout; no consent interaction (this step does not run JavaScript at all).
  * The User-Agent is the library default (python-requests/x.y.z): no spoofing.
  * One homepage request per site (redirects followed); a single /products.json?limit=1 request
    only when the homepage exposes no /products/ link.  No retries.
  * <= WORKERS sites in flight and a global cap of MAX_RPS requests per second.
  * Results are appended to raw/verify_results.jsonl; the script resumes from that file.

Usage: python verify.py <queue.csv with column 'domain' [and others]> [max_items]
"""
import csv, gzip, hashlib, html, json, os, re, sys, threading, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor

import requests

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "raw", os.environ.get("VERIFY_OUT", "verify_results.jsonl"))
HTML_DIR = os.path.join(BASE, "raw", "homepages")
os.makedirs(HTML_DIR, exist_ok=True)
WORKERS = int(os.environ.get("WORKERS", "8"))
MAX_RPS = float(os.environ.get("MAX_RPS", "4"))
MAX_BODY = 4_000_000
TIMEOUT = (10, 20)

_rate_lock = threading.Lock()
_last = [0.0]
_out_lock = threading.Lock()


def throttle():
    with _rate_lock:
        now = time.time()
        wait = _last[0] + 1.0 / MAX_RPS - now
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()


def reg_host(h):
    h = (h or "").lower()
    return h[4:] if h.startswith("www.") else h


def decode(body, content_type):
    enc = "utf-8"
    m = re.search(r"charset=([\w-]+)", content_type or "", re.I)
    if m:
        enc = m.group(1)
    try:
        return body.decode(enc, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def fetch(session, url):
    throttle()
    t0 = time.time()
    r = session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True)
    body = b""
    for chunk in r.iter_content(65536):
        body += chunk
        if len(body) > MAX_BODY:
            break
    r.close()
    return r, body, decode(body, r.headers.get("content-type", "")), round(time.time() - t0, 2)


RE_SHOP = re.compile(r"Shopify\.shop\s*=\s*[\"']([^\"']+)[\"']")
RE_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
RE_DESC = re.compile(r"<meta[^>]+name=[\"']description[\"'][^>]*content=[\"']([^\"']*)[\"']", re.I)
RE_DESC2 = re.compile(r"<meta[^>]+content=[\"']([^\"']*)[\"'][^>]*name=[\"']description[\"']", re.I)
RE_OGSITE = re.compile(r"<meta[^>]+property=[\"']og:site_name[\"'][^>]*content=[\"']([^\"']*)[\"']", re.I)
RE_PROD = re.compile(r"href=[\"']((?:https?://([^/\"']+))?((?:/[a-z]{2}(?:-[a-z]{2})?)?)(?:/collections/[^/\"'?#]+)?/products/([^/\"'?#]+))", re.I)
RE_RATING = re.compile(r"<meta[^>]+name=[\"']rating[\"'][^>]*content=[\"'](adult|mature|RTA-5042-1996-1400-1577-RTA)[\"']", re.I)

CMP_SIGS = {
    "pandectes": ["pandectes"], "onetrust": ["cdn.cookielaw.org", "otSDKStub", "onetrust"],
    "cookiebot": ["consent.cookiebot.com", "cookiebot"], "consentmo": ["consentmo", "gdpr-legal-cookie", "isenselabs"],
    "cookieyes": ["cookieyes", "cdn-cookieyes.com"], "usercentrics": ["usercentrics"], "didomi": ["didomi"],
    "osano": ["osano.com"], "iubenda": ["iubenda"], "trustarc": ["trustarc", "truste.com"], "termly": ["termly.io"],
    "enzuzo": ["enzuzo"], "transcend": ["transcend.io", "transcend-cdn"], "ketch": ["ketchcdn", "ketch.com"],
    "cookie-script": ["cookie-script.com"], "complianz": ["complianz"], "axeptio": ["axeptio"],
    "sourcepoint": ["sourcepoint", "sp-prod.net"], "cookiefirst": ["cookiefirst"], "clarip": ["clarip"],
    "securiti": ["securiti.ai"], "civic": ["civiccomputing", "cookie-control"], "cookiehub": ["cookiehub"],
    "shopify_privacy_banner": ["shopify-privacy-banner", "privacy-banner/storefront-banner", "/storefront-banner.js"],
}

ADULT_RE = re.compile(r"\b(porn\w*|xxx|sex\s*toys?|adult\s*(?:toys?|store|shop|products)|sex\s*shop|erotic\w*|fetish\w*|bdsm|"
                      r"vibrators?|dildos?|nsfw|hentai|onlyfans|escorts?|masturbat\w*|sexual\s+wellness|kink\w*)\b", re.I)
ADULT_DOMAIN = re.compile(r"(porn|xxx|sextoy|sexshop|adulttoy|erotic|fetish|hentai|dildo|vibrator)", re.I)
CHILD_RE = re.compile(r"\b(kids?|kid'?s|toys?|children'?s?|child|preschool|tweens?)\b", re.I)
CHILD_DOMAIN = re.compile(r"(kids|toys|toddler|children|preschool)", re.I)
ADULT_AUDIENCE = re.compile(r"\b(men'?s?|women'?s?|adults?|mom|moms|mothers?|parents?|dad|dads|family)\b", re.I)


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(s or "")).strip()[:300]


def analyse(domain, final, h, text):
    """h: dict of lower-cased response headers of the final response."""
    markers = []
    m = RE_SHOP.search(text)
    if m:
        markers.append("Shopify.shop")
    if "cdn.shopify.com" in text:
        markers.append("cdn.shopify.com")
    if "/cdn/shop/" in text:
        markers.append("/cdn/shop/")
    if "x-shopid" in h:
        markers.append("hdr:x-shopid")
    if "shopify" in h.get("powered-by", "").lower():
        markers.append("hdr:powered-by")
    if "x-shopify-stage" in h:
        markers.append("hdr:x-shopify-stage")
    wpm = ("web-pixels-manager" in text) or ("webPixelsManager" in text)
    if wpm:
        markers.append("web-pixels-manager")
    fu = urllib.parse.urlsplit(final)
    title = clean(RE_TITLE.search(text).group(1) if RE_TITLE.search(text) else "")
    dm = RE_DESC.search(text) or RE_DESC2.search(text)
    desc = clean(dm.group(1) if dm else "")
    og = RE_OGSITE.search(text)
    site = clean(og.group(1) if og else "")
    password = fu.path.rstrip("/").endswith("/password") or "template-password" in text or \
        re.search(r"<form[^>]+action=[\"'][^\"']*/password[\"']", text, re.I) is not None
    cmps = sorted(k for k, sigs in CMP_SIGS.items() if any(s.lower() in text.lower() for s in sigs))
    n_app = len(re.findall(r"\\?\"type\\?\"\s*:\s*\\?\"APP\\?\"", text))
    n_custom = len(re.findall(r"\\?\"type\\?\"\s*:\s*\\?\"CUSTOM\\?\"", text))
    audience_text = " ".join([title, desc, site])
    adult = bool(RE_RATING.search(text)) or bool(ADULT_RE.search(audience_text)) or bool(ADULT_DOMAIN.search(domain))
    child_dom = bool(CHILD_DOMAIN.search(domain))
    title_text = " ".join([title, site])
    child_txt = bool(CHILD_RE.search(title_text)) and not ADULT_AUDIENCE.search(title_text)
    agegate = bool(re.search(r"age[-_ ]?(verification|gate|check)|are you (?:over|at least) (?:18|21)|21\+|must be (?:18|21)", text, re.I))
    # product links on the final host only
    prod = ""
    fh = (fu.hostname or "").lower()
    for mm in RE_PROD.finditer(text):
        host = (mm.group(2) or fh).lower()
        if host != fh:
            continue
        handle = mm.group(4)
        if not handle or handle.startswith("{{") or "%7b" in handle.lower():
            continue
        prod = "https://%s%s/products/%s" % (fh, mm.group(3) or "", handle)
        break
    return {
        "markers": markers, "myshopify": m.group(1) if m else "", "wpm": int(wpm), "final_url": final,
        "final_host": fh, "title": title, "description": desc[:200], "og_site_name": site,
        "password": int(bool(password)), "cmp_hints": cmps, "n_app_pixel_cfg": n_app,
        "n_custom_pixel_cfg": n_custom, "adult_flag": int(adult), "child_flag_domain": int(child_dom),
        "child_flag_text": int(child_txt), "age_gate_hint": int(agegate), "product_url": prod,
        "server": h.get("server", ""), "x_shopid": h.get("x-shopid", ""),
    }


def verify(item):
    domain = item["domain"]
    rec = dict(item)
    rec["ts_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rec["n_requests"] = 0
    s = requests.Session()
    url = "https://%s/" % (item.get("fetch_host") or domain)
    try:
        r, body, text, el = fetch(s, url)
        rec["n_requests"] += 1
        hdrs = {k.lower(): v for k, v in r.headers.items() if k.lower() != "set-cookie"}
        rec.update({"status": r.status_code, "elapsed_s": el, "n_redirects": len(r.history),
                    "redirect_chain": [x.url for x in r.history][:10], "bytes": len(body), "error": "",
                    "headers": hdrs})
        rec.update(analyse(domain, r.url, hdrs, text))
        hp = os.path.join(HTML_DIR, hashlib.sha1(domain.encode()).hexdigest()[:16] + ".body.gz")
        with gzip.open(hp, "wb") as f:
            f.write(body)
        rec["body_file"] = os.path.relpath(hp, BASE)
        live = r.status_code == 200 and rec["markers"] and not rec["password"]
        if live and not rec["product_url"]:
            fh = rec["final_host"]
            try:
                r2, _b2, t2, _ = fetch(s, "https://%s/products.json?limit=1" % fh)
                rec["n_requests"] += 1
                rec["products_json_status"] = r2.status_code
                if r2.status_code == 200:
                    js = json.loads(t2)
                    ps = js.get("products") or []
                    if ps and ps[0].get("handle"):
                        rec["product_url"] = "https://%s/products/%s" % (fh, ps[0]["handle"])
                        rec["product_url_source"] = "products.json"
            except Exception as e:  # noqa
                rec["products_json_error"] = type(e).__name__
        elif rec["product_url"]:
            rec["product_url_source"] = "homepage_link"
    except requests.exceptions.SSLError as e:
        rec.update({"status": None, "error": "SSLError"})
    except requests.exceptions.ConnectTimeout:
        rec.update({"status": None, "error": "ConnectTimeout"})
    except requests.exceptions.ReadTimeout:
        rec.update({"status": None, "error": "ReadTimeout"})
    except requests.exceptions.TooManyRedirects:
        rec.update({"status": None, "error": "TooManyRedirects"})
    except requests.exceptions.ConnectionError as e:
        rec.update({"status": None, "error": "ConnectionError"})
    except Exception as e:  # noqa
        rec.update({"status": None, "error": "%s:%s" % (type(e).__name__, str(e)[:120])})
    finally:
        s.close()
    with _out_lock:
        with open(OUT, "a") as f:
            f.write(json.dumps(rec) + "\n")
    return rec


def done_domains():
    d = set()
    if os.path.exists(OUT):
        with open(OUT) as f:
            for line in f:
                try:
                    d.add(json.loads(line)["domain"])
                except Exception:
                    pass
    return d


def main():
    q = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    items = list(csv.DictReader(open(q)))
    done = done_domains()
    todo = [it for it in items if it["domain"] not in done]
    if limit:
        todo = todo[:limit]
    print("queue=%d already=%d todo=%d UA=%s" % (len(items), len(items) - len([i for i in items if i['domain'] not in done]),
                                                len(todo), requests.utils.default_user_agent()), flush=True)
    t0 = time.time()
    n = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for rec in ex.map(verify, todo):
            n += 1
            if n % 50 == 0:
                print("%d/%d %.0fs" % (n, len(todo), time.time() - t0), flush=True)
    print("FINISHED n=%d %.0fs" % (n, time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
