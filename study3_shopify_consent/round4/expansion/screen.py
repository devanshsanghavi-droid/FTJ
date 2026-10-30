"""Round 4 / B1 expansion, step 2: screen DNS-flagged domains (ranks 200,001-1,000,000) for blocklist CMPs.

Order: the seeded random permutation of dns_scan_ext.py. A flagged domain is screened only after every
domain before it in the permutation has been resolved, so the screened set is always an exact prefix of a
uniformly random order of the frame (a simple random sample without replacement).

Per domain (binding Round 4 rules, ethics request section 5.1 / 5.2):
  1. Domain-name adult/child screen (sample/verify.py regexes): excluded before any request.
  2. robots.txt of the host (RFC 9309, product token 'python-requests'); 4xx = no robots.txt (allowed);
     5xx or unreachable = site skipped. '/' disallowed = site skipped.
  3. ONE homepage GET (redirects followed manually; a new host's robots.txt is checked before each hop).
     Default python-requests User-Agent (no spoofing), no cookies kept, no JavaScript, no retries.
  4. Title/description adult/child screen (sample/verify.py analyse()); Shopify Online Store check;
     password page; duplicates of the main sample and of earlier expansion stores (Shopify.shop).
  5. Static CMP detection (crawl/cmp_signatures.json) and the blocklist the CMP publishes: Pandectes inline;
     OneTrust OtAutoBlock.js and Cookiebot configuration.js from the vendor CDN (one GET per file, cached,
     vendor robots.txt respected).
Pacing: <= 1 homepage GET (navigation) per second overall; redirect hops <= 2 per second; <= 2 robots.txt GETs per second overall (different hosts); <= 1 vendor-CDN GET
per second; WORKERS sites in flight (each worker handles one site at a time; a site gets at most
robots.txt + one homepage GET, plus robots.txt of a redirect target host).
Storage: a compact JSON line per site in raw/screen_results.jsonl; the gzipped homepage is kept only for
blocklist stores (raw/homepages/); a free-disk floor of 1.2 GB stops the run.
Stop: when the screened prefix holds TARGET stratum stores, or the frame is exhausted.
Resumable: re-running skips domains already in screen_results.jsonl.
"""
import csv, gzip, hashlib, json, os, re, shutil, sys, threading, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "sample"))
sys.path.insert(0, HERE)
import build_frame  # noqa: E402  (PLATFORM)
import verify  # noqa: E402  (analyse, ADULT_DOMAIN, CHILD_DOMAIN, decode)
import static_detect as sd  # noqa: E402
from robots import Robots  # noqa: E402

DNS = os.path.join(HERE, "raw", "dns_ext.csv")
OUT = os.path.join(HERE, "raw", "screen_results.jsonl")
HP_DIR = os.path.join(HERE, "raw", "homepages")
VC_DIR = os.path.join(HERE, "raw", "vendor_cfg")
STOPFILE = os.path.join(HERE, "STOP")
WORKERS = int(os.environ.get("WORKERS", "6"))
TARGET = int(os.environ.get("TARGET", "250"))
MIN_FREE = 1.2e9
TIMEOUT = (10, 20)
MAX_BODY = 4_000_000
UA = requests.utils.default_user_agent()
TOKEN = "python-requests"
TEST_QS = "utm_source=privacy-research&utm_medium=measurement&utm_campaign=cmpstudy-E0000"
os.makedirs(HP_DIR, exist_ok=True)
os.makedirs(VC_DIR, exist_ok=True)


class Throttle:
    def __init__(self, per_s):
        self.gap, self.last, self.lock = 1.0 / per_s, 0.0, threading.Lock()

    def wait(self):
        with self.lock:
            now = time.time()
            if self.last + self.gap > now:
                time.sleep(self.last + self.gap - now)
            self.last = time.time()


T_HOME, T_HOP, T_ROBOTS, T_VENDOR = Throttle(1.0), Throttle(2.0), Throttle(2.0), Throttle(1.0)
_out_lock = threading.Lock()
_rob_lock = threading.Lock()
_vc_lock = threading.Lock()
ROBOTS = {}      # host -> ('ok'|'none'|'fail', Robots|None, status)
VCACHE = {}      # url -> (status, text or None)
N_REQ = {"robots": 0, "home": 0, "home_hops": 0, "vendor": 0, "vendor_robots": 0}


def free_bytes():
    return shutil.disk_usage(HERE).free


def get(url, throttle, stream_limit=MAX_BODY):
    throttle.wait()
    r = requests.get(url, timeout=TIMEOUT, allow_redirects=False, stream=True, headers={"User-Agent": UA})
    body = b""
    for ch in r.iter_content(65536):
        body += ch
        if len(body) > stream_limit:
            break
    r.close()
    return r, body


def robots_for(host, is_vendor=False):
    """Fetch and cache robots.txt for host (following up to 5 redirects)."""
    with _rob_lock:
        if host in ROBOTS:
            return ROBOTS[host]
    url = "https://%s/robots.txt" % host
    res = ("fail", None, "err")
    try:
        for _ in range(6):
            r, body = get(url, T_ROBOTS if not is_vendor else T_VENDOR, 512_000)
            N_REQ["vendor_robots" if is_vendor else "robots"] += 1
            if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                url = urllib.parse.urljoin(url, r.headers["location"])
                continue
            if r.status_code == 200:
                res = ("ok", Robots(verify.decode(body, r.headers.get("content-type", "")), TOKEN), 200)
            elif 400 <= r.status_code < 500:
                res = ("none", None, r.status_code)
            else:
                res = ("fail", None, r.status_code)
            break
    except Exception as e:  # noqa
        res = ("fail", None, type(e).__name__)
    with _rob_lock:
        ROBOTS[host] = res
    return res


def allowed(host, path_or_url, is_vendor=False):
    st, rb, _ = robots_for(host, is_vendor)
    if st == "fail":
        return None
    if st == "none":
        return True
    return rb.allowed(path_or_url)


def vendor_get(url):
    with _vc_lock:
        if url in VCACHE:
            return VCACHE[url]
    host = urllib.parse.urlsplit(url).hostname
    ok = allowed(host, url, is_vendor=True)
    if not ok:
        res = ("robots_" + ("disallow" if ok is False else "fail"), None)
    else:
        try:
            r, body = get(url, T_VENDOR, 3_000_000)
            N_REQ["vendor"] += 1
            res = (r.status_code, body.decode("utf-8", "replace") if r.status_code == 200 else None)
        except Exception as e:  # noqa
            res = (type(e).__name__, None)
    with _vc_lock:
        VCACHE[url] = res
    return res


RE_PROD_ESC = re.compile(r"(?:https?:\\?/\\?/([a-z0-9.-]+))?((?:\\?/[a-z]{2}(?:-[a-z]{2})?)?)\\?/products\\?/([a-z0-9][a-z0-9_%.-]*)", re.I)


def product_from_text(text, fh):
    for m in RE_PROD_ESC.finditer(text):
        host = (m.group(1) or fh).lower()
        if host != fh:
            continue
        h = m.group(3)
        if not h or h.endswith(".js") or h.endswith(".json") or h in ("products",):
            continue
        return "https://%s%s/products/%s" % (fh, (m.group(2) or "").replace("\\", ""), h)
    return ""


def main_sample_shops():
    shops, hosts = set(), set()
    samp = {r["domain"] for r in csv.DictReader(open(os.path.join(ROOT, "sample", "sample.csv")))}
    for fn in ("verify_results.jsonl", "creator_verify.jsonl"):
        p = os.path.join(ROOT, "sample", "raw", fn)
        if not os.path.exists(p):
            continue
        for line in open(p):
            r = json.loads(line)
            if fn == "creator_verify.jsonl" or r["domain"] in samp:
                if r.get("myshopify"):
                    shops.add(r["myshopify"].lower())
                for h in (r.get("final_host"), r.get("domain")):
                    if h:
                        hosts.add(verify.reg_host(h))
    for r in csv.DictReader(open(os.path.join(ROOT, "sample", "creator_stratum.csv"))):
        for k in ("domain", "host", "store_host"):
            if r.get(k):
                hosts.add(verify.reg_host(r[k]))
    return shops, hosts


MAIN_SHOPS, MAIN_HOSTS = main_sample_shops()


def screen(item):
    d = item["domain"]
    rec = {"perm": item["perm"], "rank": item["rank"], "domain": d, "fetch_host": item["fetch_host"],
           "apex_flag": item["apex_flag"], "www_flag": item["www_flag"], "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    try:
        if verify.ADULT_DOMAIN.search(d):
            rec["stage"] = "excl_adult_domain"
            return rec
        if verify.CHILD_DOMAIN.search(d):
            rec["stage"] = "excl_child_domain"
            return rec
        host = item["fetch_host"]
        ok = allowed(host, "/")
        rec["robots"] = ROBOTS.get(host, ("?", None, ""))[0] + ":" + str(ROBOTS.get(host, ("", None, ""))[2])
        if ok is None:
            rec["stage"] = "skip_robots_unreachable"
            return rec
        if not ok:
            rec["stage"] = "skip_robots_disallow_home"
            return rec
        time.sleep(1.0)
        url = "https://%s/" % host
        chain = []
        s = requests.Session()
        r = body = None
        try:
            for hop in range(6):
                h = urllib.parse.urlsplit(url).hostname
                a = allowed(h, url)
                if a is None or a is False:
                    rec["stage"] = "skip_robots_redirect_" + ("fail" if a is None else "disallow")
                    rec["redirect_chain"] = chain
                    return rec
                (T_HOME if hop == 0 else T_HOP).wait()
                r = s.get(url, timeout=TIMEOUT, allow_redirects=False, stream=True, headers={"User-Agent": UA})
                N_REQ["home" if hop == 0 else "home_hops"] += 1
                if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                    chain.append(url)
                    url = urllib.parse.urljoin(url, r.headers["location"])
                    r.close()
                    continue
                body = b""
                for ch in r.iter_content(65536):
                    body += ch
                    if len(body) > MAX_BODY:
                        break
                r.close()
                break
        finally:
            s.close()
        rec["redirect_chain"] = chain[:6]
        if body is None:
            rec["stage"] = "err_too_many_redirects"
            return rec
        hdrs = {k.lower(): v for k, v in r.headers.items() if k.lower() != "set-cookie"}
        return post_fetch(rec, d, url, r.status_code, hdrs, body)
    except requests.exceptions.SSLError:
        rec["stage"] = "err_SSLError"
    except requests.exceptions.ConnectTimeout:
        rec["stage"] = "err_ConnectTimeout"
    except requests.exceptions.ReadTimeout:
        rec["stage"] = "err_ReadTimeout"
    except requests.exceptions.ConnectionError:
        rec["stage"] = "err_ConnectionError"
    except Exception as e:  # noqa
        rec["stage"] = "err_%s" % type(e).__name__
        rec["error"] = str(e)[:160]
    return rec


def post_fetch(rec, d, url, status, hdrs, body):
    """Everything after the homepage GET (no request to the store site is made here)."""
    try:
        rec["status"] = status
        rec["bytes"] = len(body)
        text = verify.decode(body, hdrs.get("content-type", ""))
        an = verify.analyse(d, url, hdrs, text)
        for k in ("markers", "myshopify", "final_url", "final_host", "title", "description", "og_site_name", "password",
                  "adult_flag", "child_flag_domain", "child_flag_text", "age_gate_hint", "product_url", "cmp_hints", "wpm"):
            rec[k] = an.get(k)
        rec["title"] = (rec.get("title") or "")[:120]
        rec["description"] = (rec.get("description") or "")[:160]
        if status != 200:
            rec["stage"] = "http_%d" % status
            return rec
        mk = set(an["markers"])
        if not mk:
            rec["stage"] = "not_shopify"
            return rec
        if not (mk & {"Shopify.shop", "/cdn/shop/", "web-pixels-manager", "hdr:x-shopid"}):
            rec["stage"] = "headless"
            return rec
        if an["password"]:
            rec["stage"] = "password"
            return rec
        if an["adult_flag"]:
            rec["stage"] = "excl_adult_text"
            for k in ("title", "description", "og_site_name", "final_url", "product_url"):
                rec[k] = "[withheld: adult flag]"
            return rec
        if an["child_flag_text"]:
            rec["stage"] = "excl_child_text"
            return rec
        shop = (an.get("myshopify") or "").lower()
        if (shop and shop in MAIN_SHOPS) or verify.reg_host(an["final_host"]) in MAIN_HOSTS:
            rec["stage"] = "dup_main_sample"
            return rec
        # duplicates WITHIN the expansion (same Shopify.shop) are resolved at build time: the lowest perm is kept
        # ---- verified eligible storefront: CMP + blocklist
        rec["stage"] = "eligible"
        fh = an["final_host"]
        if not rec["product_url"]:
            pu = product_from_text(text, fh)
            if pu:
                rec["product_url"] = pu
                rec["product_url_source"] = "homepage_escaped"
        elif rec["product_url"]:
            rec["product_url_source"] = "homepage_link"
        cm = sd.detect_cmps(text)
        rec["cmps_static"] = {k: v for k, v in cm.items()}
        ents = []
        tgt = [k for k in sd.TARGET if k in cm]
        rec["target_cmps"] = tgt
        pc = sd.pandectes_config(text) if "pandectes" in tgt or "andectes" in text else None
        if pc:
            rec["pandectes"] = {k: pc.get(k) for k in ("version", "blocker_active", "strict_has_ca", "default_blocked", "parse_error",
                                                       "v4_geo_only", "v4_global_visibility")}
            ents += [dict(e, cmp="pandectes") for e in pc["entries"]]
        ot = sd.onetrust_page(text)
        if ot["autoblock_url"] or "onetrust" in tgt:
            rec["onetrust"] = dict(ot)
            if ot["autoblock_url"]:
                st, txt = vendor_get(ot["autoblock_url"])
                rec["onetrust"]["autoblock_status"] = st
                if txt:
                    tags = sd.parse_otautoblock(txt)
                    rec["onetrust"]["n_tags"] = len(tags)
                    ents += [dict(e, cmp="onetrust") for e in sd.onetrust_entries(tags)]
                    rec["_vc"] = [("ot", ot["autoblock_url"], txt)]
        cb = sd.cookiebot_page(text)
        if cb["tag"]:
            rec["cookiebot"] = dict(cb)
            cbid = cb["cbid"]
            m = re.search(r"region'?\s*:\s*'?(US-06|US)'?\s*,\s*'?cbid'?\s*:\s*'?([0-9a-f-]{36})", cb["georegions"] or "", re.I)
            if m:
                cbid = m.group(2)
                rec["cookiebot"]["cbid_ca"] = cbid
            if cbid:
                cdn = "consentcdn.cookiebot.eu" if cb.get("cdn_eu") else "consentcdn.cookiebot.com"
                tags = []
                for hname in (verify.reg_host(fh), fh):
                    u = "https://%s/consentconfig/%s/%s/configuration.js" % (cdn, cbid, hname)
                    st, txt = vendor_get(u)
                    rec["cookiebot"]["config_status"] = st
                    if txt:
                        tags = sd.parse_cookiebot_config(txt)
                        rec["cookiebot"]["config_url"] = u
                        rec["cookiebot"]["n_tags"] = len(tags)
                        rec.setdefault("_vc", []).append(("cb", u, txt))
                        break
                    if hname == fh:
                        break
                ents += [dict(e, cmp="cookiebot") for e in sd.cookiebot_entries(tags, cb["blockingmode"])]
        sm = sd.summarize(ents)
        rec.update(sm)
        rec["blocklist_cmps"] = sorted({e["cmp"] for e in ents if e["ad"] and e["post"]})
        rec["blocklist_readable"] = int(bool(sm["ad_vendors_blocklisted"]))
        rec["in_stratum"] = int(rec["blocklist_readable"] == 1 and sm["prechoice_ca"] in ("yes", "unknown"))
        if rec["blocklist_readable"]:
            rec["blocklist_entries"] = [{k: e.get(k) for k in ("cmp", "vendor", "src", "pattern", "cat", "pre", "post")}
                                        for e in ents if e["ad"]][:60]
            pu = rec.get("product_url") or ""
            if pu:
                rec["product_allowed_plain"] = bool(allowed(urllib.parse.urlsplit(pu).hostname, pu))
                rec["product_allowed_tagged"] = bool(allowed(urllib.parse.urlsplit(pu).hostname, pu + ("&" if "?" in pu else "?") + TEST_QS))
            hp = os.path.join(HP_DIR, hashlib.sha1(d.encode()).hexdigest()[:16] + ".body.gz")
            with gzip.open(hp, "wb") as f:
                f.write(body)
            rec["body_file"] = os.path.relpath(hp, HERE)
            for kind, u, txt in rec.get("_vc", []):
                vp = os.path.join(VC_DIR, hashlib.sha1(u.encode()).hexdigest()[:16] + ".js.gz")
                if not os.path.exists(vp):
                    with gzip.open(vp, "wt") as f:
                        f.write(txt)
                rec.setdefault("vendor_files", []).append({"kind": kind, "url": u, "file": os.path.relpath(vp, HERE)})
        elif tgt:
            rec["cmp_extract_file"] = save_cmp_extract(d, text)
        return rec
    except Exception as e:  # noqa  (analysis bug: keep the record and the page, for offline re-analysis)
        rec["stage"] = "err_analysis_%s" % type(e).__name__
        rec["error"] = str(e)[:160]
        hp = os.path.join(HP_DIR, hashlib.sha1(d.encode()).hexdigest()[:16] + ".body.gz")
        with gzip.open(hp, "wb") as f:
            f.write(body)
        rec["body_file"] = os.path.relpath(hp, HERE)
    return rec


RE_SCRIPT = re.compile(r"<script\b[^>]*>.*?</script>", re.I | re.S)


def save_cmp_extract(d, text):
    """For target-CMP stores without a readable ad blocklist: keep only the CMP-related script tags (small)."""
    parts = [m.group(0)[:200_000] for m in RE_SCRIPT.finditer(text)
             if re.search(r"andectes|cookielaw|onetrust|cookiebot", m.group(0), re.I)]
    if not parts:
        return ""
    xp = os.path.join(HP_DIR, hashlib.sha1(d.encode()).hexdigest()[:16] + ".cmp_scripts.gz")
    with gzip.open(xp, "wt") as f:
        f.write("\n<!-- ---- -->\n".join(parts))
    return os.path.relpath(xp, HERE)


def write(rec):
    rec.pop("_vc", None)
    with _out_lock:
        with open(OUT, "a") as f:
            f.write(json.dumps(rec, default=str) + "\n")


class Frame:
    """Incrementally reads raw/dns_ext.csv; yields flagged domains in permutation order up to the complete prefix."""
    def __init__(self):
        self.pos = 0
        self.hosts = {}   # perm -> dict
        self.frontier = -1
        self.flagged = []  # (perm, item), appended in perm order up to frontier
        self.n_domains = 0
        self.platform = 0

    def update(self):
        with open(DNS) as f:
            if self.pos == 0:
                f.readline()
                self.pos = f.tell()
            f.seek(self.pos)
            while True:
                line = f.readline()
                if not line or not line.endswith("\n"):
                    break
                self.pos = f.tell()
                row = next(csv.reader([line]))
                p, rank, d, host = int(row[0]), int(row[1]), row[2], row[3]
                e = self.hosts.setdefault(p, {"perm": p, "rank": rank, "domain": d})
                key = "www" if host.startswith("www.") and host != d else "apex"
                e[key] = row
        while (self.frontier + 1) in self.hosts and "apex" in self.hosts[self.frontier + 1] and "www" in self.hosts[self.frontier + 1]:
            self.frontier += 1
            e = self.hosts.pop(self.frontier)
            self.n_domains += 1
            a, w = e["apex"], e["www"]
            af = int(a[5] == "1" or a[7] == "1")
            wf = int(w[5] == "1" or w[7] == "1")
            if not (af or wf):
                continue
            if e["domain"] in build_frame.PLATFORM:
                self.platform += 1
                continue
            self.flagged.append({"perm": e["perm"], "rank": e["rank"], "domain": e["domain"],
                                 "fetch_host": e["domain"] if af else "www." + e["domain"], "apex_flag": af, "www_flag": wf})


def main():
    done = {}
    if os.path.exists(OUT):
        for line in open(OUT):
            r = json.loads(line)
            done[r["domain"]] = r
    fr = Frame()
    n_stratum = sum(1 for r in done.values() if r.get("in_stratum") == 1)
    print("start UA=%s workers=%d target=%d already=%d stratum_already=%d main_shops=%d" %
          (UA, WORKERS, TARGET, len(done), n_stratum, len(MAIN_SHOPS)), flush=True)
    idx = 0
    t0 = time.time()
    last_print = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        pending = set()
        while True:
            if os.path.exists(STOPFILE) or free_bytes() < MIN_FREE:
                print("STOP file present; stopping" if os.path.exists(STOPFILE) else "FREE DISK below 1.2 GB; stopping", flush=True)
                # drain: every submitted site runs to completion and MUST be recorded (it may already have been fetched)
                for fu in list(pending):
                    rec = fu.result()
                    write(rec)
                    done[rec["domain"]] = rec
                    n_stratum += int(rec.get("in_stratum") == 1)
                pending.clear()
                break
            fr.update()
            dns_done = "FINISHED" in open(os.path.join(HERE, "logs", "dns_scan_ext.log")).read()
            # submit work in order
            while idx < len(fr.flagged) and len(pending) < WORKERS * 2 and n_stratum < TARGET:
                it = fr.flagged[idx]
                idx += 1
                if it["domain"] in done:
                    continue
                pending.add(ex.submit(screen, it))
            for fu in [p for p in pending if p.done()]:
                pending.discard(fu)
                rec = fu.result()
                write(rec)
                done[rec["domain"]] = rec
                if rec.get("in_stratum") == 1:
                    n_stratum += 1
            if time.time() - last_print > 60:
                last_print = time.time()
                print("t=%.0fs dns_domains_complete=%d flagged_in_prefix=%d screened=%d stratum=%d req=%s free=%.2fGB" %
                      (time.time() - t0, fr.n_domains, len(fr.flagged), len(done), n_stratum, N_REQ, free_bytes() / 1e9), flush=True)
            if n_stratum >= TARGET and not pending:
                print("TARGET reached", flush=True)
                break
            if dns_done and idx >= len(fr.flagged) and not pending:
                fr.update()
                if idx >= len(fr.flagged):
                    print("FRAME exhausted", flush=True)
                    break
            time.sleep(0.2)
    print("FINISHED screened=%d stratum=%d req=%s elapsed=%.0fs" % (len(done), n_stratum, N_REQ, time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
