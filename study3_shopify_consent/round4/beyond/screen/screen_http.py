"""Beyond-Shopify pilot (Part B2), screening step 2: robots.txt + ONE static homepage GET per candidate.

Ethics / politeness (binding rules of the ethics request, section 5.1, as applied to screening):
  * GET only, no JavaScript, no cookies kept (fresh requests.Session per site), no forms, logins, cart,
    purchases or banner interaction. Library-default User-Agent (python-requests/x.y.z): no spoofing.
  * robots.txt is fetched BEFORE the homepage and obeyed (RFC 9309 groups via urllib.robotparser, token
    "python-requests" else "*"): 2xx -> parse; 4xx -> allowed; 5xx / network error / >5 redirects -> site skipped.
    Redirects of the homepage are followed by hand; before any request to a new host, that host's robots.txt is
    checked too (robots files reached through a robots.txt redirect are re-used for their host).
  * One homepage request per candidate (its redirect hops count as that one request). No retries.
  * Adult and child-directed domains are screened out by name BEFORE contact; titles/descriptions after.
  * Rate: <= 1 homepage GET per second overall (the crawl's navigation cap), <= 1 robots.txt GET per second
    (2 per second from 00:30 PDT 27 Sep; robots.txt files are not page loads; total stays below Part A's 4 req/s),
    <= 6 sites in flight (8 from 00:20 PDT 27 Sep, as in Part A's screening). Each site gets exactly one homepage load, so the 10 s per-site gap holds trivially.
  * Storage: only pages with a target marker (Partytown, Zaraz, first-party tag gateway, Wix, BigCommerce) are
    kept, gzipped, capped at 3 MB raw; everything else is reduced to the extracted fields. Set-Cookie values are
    never stored (names only). The job stops if free disk falls below 1.2 GB.
Usage: python screen_http.py <queue.csv> [max_items]      (queue columns: domain,rank,stratum,fetch_host)
Output: raw/screen_results.jsonl (append, resumable by domain), raw/pages/<sha1(domain)[:16]>.html.gz
"""
import csv, gzip, hashlib, json, os, re, shutil, sys, threading, time, urllib.parse, urllib.robotparser
from concurrent.futures import ThreadPoolExecutor
import requests
import markers as M

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
PAGES = os.path.join(RAW, 'pages'); os.makedirs(PAGES, exist_ok=True)
OUT = os.path.join(RAW, os.environ.get('SCREEN_OUT', 'screen_results.jsonl'))
WORKERS = int(os.environ.get('WORKERS', '6'))     # <= 8 sites in flight (Part A screening used 8)
HOME_RPS = float(os.environ.get('HOME_RPS', '1.0'))   # 0.5 for the J2 extension (03:20 PDT 27 Sep), which ran alongside the round4/expansion screener
ROBOTS_RPS = float(os.environ.get('ROBOTS_RPS', '1.0'))   # 2.0 from 00:30 PDT 27 Sep (total <= 3 req/s; Part A screening allowed 4)
MAX_BODY = 3_000_000
MAX_ROBOTS = 500 * 1024
TIMEOUT = (8, 15)
MIN_FREE = 1.2e9
UA = requests.utils.default_user_agent()
TOKEN = UA.split('/')[0]

_locks = {'home': threading.Lock(), 'robots': threading.Lock()}
_last = {'home': 0.0, 'robots': 0.0}
_rate = {'home': 1.0 / HOME_RPS, 'robots': 1.0 / ROBOTS_RPS}
_out_lock = threading.Lock()
STOP = threading.Event()


def throttle(kind):
    with _locks[kind]:
        wait = _last[kind] + _rate[kind] - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[kind] = time.time()


def free_bytes():
    return shutil.disk_usage(HERE).free


def decode(body, ctype):
    m = re.search(r"charset=([\w-]+)", ctype or '', re.I)
    enc = m.group(1) if m else 'utf-8'
    try:
        return body.decode(enc, errors='replace')
    except LookupError:
        return body.decode('utf-8', errors='replace')


def get_limited(session, url, limit):
    r = session.get(url, timeout=TIMEOUT, allow_redirects=False, stream=True)
    body = b''
    for chunk in r.iter_content(65536):
        body += chunk
        if len(body) > limit:
            break
    r.close()
    return r, body[:limit]


class Robots:
    """Per-site robots cache. Fetches https://<host>/robots.txt (<= 5 redirects), RFC 9309 status semantics."""

    def __init__(self, session):
        self.s = session
        self.cache = {}   # host -> (status_word, parser or None)
        self.log = []

    def check(self, host, path):
        if host not in self.cache:
            self.cache[host] = self._fetch(host)
        word, rp = self.cache[host]
        if word == 'unreachable':
            return False, 'robots_unreachable'
        if word == 'allow_all':
            return True, 'robots_4xx_allow'
        ok = rp.can_fetch(TOKEN, 'https://%s%s' % (host, path))
        return ok, ('robots_allowed' if ok else 'robots_disallowed')

    def _fetch(self, host):
        url = 'https://%s/robots.txt' % host
        hops = []
        for _ in range(6):
            throttle('robots')
            try:
                r, body = get_limited(self.s, url, MAX_ROBOTS)
            except Exception as e:  # noqa
                self.log.append(dict(host=host, url=url, error=type(e).__name__))
                return ('unreachable', None)
            hops.append(r.status_code)
            if r.is_redirect or r.status_code in (301, 302, 303, 307, 308):
                nxt = urllib.parse.urljoin(url, r.headers.get('location', ''))
                url = nxt
                continue
            self.log.append(dict(host=host, final=url, status=r.status_code, hops=hops))
            if 200 <= r.status_code < 300:
                rp = urllib.robotparser.RobotFileParser()
                rp.parse(decode(body, r.headers.get('content-type', '')).splitlines())
                res = ('parsed', rp)
                fh = urllib.parse.urlsplit(url).hostname
                if fh and fh != host and fh not in self.cache:
                    self.cache[fh] = res            # the same file governs the redirect target host
                return res
            if 400 <= r.status_code < 500:
                return ('allow_all', None)
            return ('unreachable', None)
        self.log.append(dict(host=host, url=url, error='too_many_redirects', hops=hops))
        return ('unreachable', None)


def page_path(domain):
    return os.path.join(PAGES, hashlib.sha1(domain.encode()).hexdigest()[:16] + '.html.gz')


def screen(item):
    rec = dict(item)
    rec['ts_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    d = item['domain']
    if M.ADULT_DOMAIN.search(d) or M.CHILD_DOMAIN.search(d):
        rec.update(outcome='not_contacted_name_screen', adult_domain=bool(M.ADULT_DOMAIN.search(d)),
                   child_domain=bool(M.CHILD_DOMAIN.search(d)))
        return rec
    if STOP.is_set():
        rec.update(outcome='not_contacted_stopped')
        return rec
    s = requests.Session()
    s.max_redirects = 5
    robots = Robots(s)
    try:
        url = 'https://%s/' % item['fetch_host']
        chain = []
        r = body = None
        ok, why = robots.check(item['fetch_host'], '/')
        if not ok:
            rec.update(outcome=why, robots_log=robots.log)
            return rec
        throttle('home')
        t0 = time.time()
        for hop in range(6):
            r, body = get_limited(s, url, MAX_BODY)
            chain.append([url[:200], r.status_code])
            if r.status_code in (301, 302, 303, 307, 308) and r.headers.get('location'):
                nxt = urllib.parse.urljoin(url, r.headers['location'])
                pu = urllib.parse.urlsplit(nxt)
                if pu.scheme not in ('http', 'https') or not pu.hostname:
                    break
                path = (pu.path or '/') + (('?' + pu.query) if pu.query else '')
                ok, why = robots.check(pu.hostname, path)
                if not ok:
                    rec.update(outcome='redirect_' + why, chain=chain, robots_log=robots.log)
                    return rec
                url = nxt
                continue
            break
        rec['elapsed_s'] = round(time.time() - t0, 2)
        rec['chain'] = chain
        rec['status'] = r.status_code
        hdrs = {k.lower(): v for k, v in r.headers.items() if k.lower() != 'set-cookie'}
        rec['set_cookie_names'] = sorted({c.split('=', 1)[0].strip() for c in r.raw.headers.getlist('set-cookie')})[:30] \
            if hasattr(r.raw, 'headers') else []
        rec['robots_log'] = robots.log
        if r.status_code != 200:
            rec['outcome'] = 'http_%d' % r.status_code
            return rec
        ctype = r.headers.get('content-type', '')
        if 'html' not in ctype.lower() and not body.lstrip()[:200].lower().startswith((b'<!doctype', b'<html')):
            rec['outcome'] = 'not_html'
            return rec
        text = decode(body, ctype)
        a = M.analyse(d, url, hdrs, text)
        rec.update(a)
        rec['final_url'] = url[:300]
        rec['outcome'] = 'ok'
        rec['truncated'] = len(body) >= MAX_BODY
        target = a['partytown']['any'] or a['zaraz']['any'] or a['gateway']['any'] or a['wix']['platform'] or a['bigcommerce']['platform']
        if target and free_bytes() > MIN_FREE:
            with gzip.open(page_path(d), 'wb', compresslevel=6) as fh:
                fh.write(body)
            rec['page_saved'] = True
        # robots check for the page a measurement crawl would load (homepage path, and product page if any)
        if a.get('product_url'):
            pu = urllib.parse.urlsplit(a['product_url'])
            okp, whyp = robots.check(pu.hostname, pu.path or '/')
            rec['product_robots'] = whyp
    except Exception as e:  # noqa
        rec.update(outcome='error', error=type(e).__name__, robots_log=robots.log)
    finally:
        s.close()
    return rec


def main():
    qpath = sys.argv[1]
    lim = int(sys.argv[2]) if len(sys.argv) > 2 else None
    done = set()
    if os.path.exists(OUT):
        for l in open(OUT):
            try:
                done.add(json.loads(l)['domain'])
            except Exception:
                pass
    items = [r for r in csv.DictReader(open(qpath)) if r['domain'] not in done]
    if lim:
        items = items[:lim]
    print('UA', UA, 'queue', qpath, 'todo', len(items), 'already', len(done), 'free GB %.2f' % (free_bytes() / 1e9), flush=True)
    t0 = time.time()
    n = 0
    with open(OUT, 'a') as fh, ThreadPoolExecutor(WORKERS) as ex:
        for rec in ex.map(screen, items):
            with _out_lock:
                fh.write(json.dumps(rec) + '\n'); fh.flush()
            n += 1
            if n % 50 == 0:
                fb = free_bytes()
                print('%d/%d %.0fs free=%.2fGB last=%s %s' % (n, len(items), time.time() - t0, fb / 1e9, rec['domain'], rec.get('outcome')), flush=True)
                if fb < MIN_FREE:
                    STOP.set()
                    print('STOP: free disk below 1.2 GB', flush=True)
    print('FINISHED n=%d %.0fs' % (n, time.time() - t0), flush=True)


if __name__ == '__main__':
    main()
