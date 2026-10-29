"""Frame-recall check for the DNS sampling frame (final audit, 2026-09-26).

The frame flags a Tranco domain when its apex or www host resolves into Shopify's address block or to a myshopify
CNAME (dns_scan.py). This script estimates, per Tranco rank bucket, how many Shopify Online Store storefronts the rule
misses, in two parts:
  (1) DNS only: for a seeded random sample of SUB_N domains per bucket, resolve shop.<d> and store.<d> and apply the
      same flag rule (stores on those subdomains are outside the frame).
  (2) One homepage GET (same code, user agent and markers as verify.py) for a seeded random sample of HTTP_N
      non-flagged domains per bucket whose apex or www resolved, plus every non-flagged domain from (1) whose shop./store.
      subdomain was flagged (homepage of that subdomain). Domain names matching the adult/child keyword screen of
      verify.py are not contacted. Homepage bodies are NOT saved; only status, markers and flags are kept.
A storefront counts as an Online Store storefront with the definition of build_sample.py (storefront_type), requiring
HTTP 200 and no password page. Recall per bucket = in-frame storefronts / (in-frame + estimated missed).
Politeness: one request per site, <= 6 sites in flight, <= 4 requests/s overall (verify.throttle); DNS <= 40 in flight.
Usage: python frame_recall.py dns | http | summary        (each step resumable)
"""
import csv, json, os, random, sys, time
from concurrent.futures import ThreadPoolExecutor
os.environ.setdefault('MAX_RPS', '4')
import verify as V      # noqa: E402  (analyse, fetch, throttle, ADULT_DOMAIN, CHILD_DOMAIN)
import dns_scan as D    # noqa: E402  (resolve, classify)
import requests         # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
OUTD = os.path.join(BASE, 'raw', 'frame_recall'); os.makedirs(OUTD, exist_ok=True)
SEED = 20260926
SUB_N = 5000
HTTP_N = 600
BUCKETS = [('1-10k', 1, 10000), ('10k-50k', 10001, 50000), ('50k-100k', 50001, 100000), ('100k-200k', 100001, 200000)]


def bucket_of(r):
    for b, lo, hi in BUCKETS:
        if lo <= r <= hi:
            return b


def frame():
    """domain -> dict(rank, bucket, resolved, flagged) from dns_results.csv (apex + www)."""
    F = {}
    for row in csv.DictReader(open(os.path.join(BASE, 'raw', 'dns_results.csv'))):
        d = F.setdefault(row['domain'], dict(rank=int(row['rank']), resolved=False, flagged=False))
        if row['ips']:
            d['resolved'] = True
        if row['in_shopify_block'] == '1' or row['cname_myshopify'] == '1':
            d['flagged'] = True
    for k, v in F.items():
        v['bucket'] = bucket_of(v['rank'])
    return F


def screened(d):
    return bool(V.ADULT_DOMAIN.search(d) or V.CHILD_DOMAIN.search(d))


def step_dns(F):
    out = os.path.join(OUTD, 'subdomain_dns.csv')
    done = set()
    if os.path.exists(out):
        done = {r['host'] for r in csv.DictReader(open(out))}
    hosts = []
    for b, lo, hi in BUCKETS:
        doms = sorted(d for d, v in F.items() if v['bucket'] == b)
        pick = random.Random(SEED + lo).sample(doms, min(SUB_N, len(doms)))
        for d in pick:
            for sub in ('shop', 'store'):
                h = f'{sub}.{d}'
                if h not in done:
                    hosts.append((b, d, h))
    print('subdomain lookups to do', len(hosts), flush=True)
    new = not os.path.exists(out)
    with open(out, 'a', newline='') as fh, ThreadPoolExecutor(40) as ex:
        w = csv.writer(fh)
        if new:
            w.writerow(['bucket', 'domain', 'host', 'canon', 'ips', 'in_shopify_block', 'in_storefront_24', 'cname_myshopify', 'error'])
        for i, ((b, d, h), res) in enumerate(zip(hosts, ex.map(lambda x: D.resolve(x[2]), hosts))):
            _, canon, ips, err, _el = res
            ib, isf, cn = D.classify(canon, ips) if ips or canon else (0, 0, 0)
            w.writerow([b, d, h, canon, ' '.join(ips), ib, isf, cn, err])
            if i % 5000 == 0:
                fh.flush(); print(i, flush=True)


def check(item):
    rec = dict(item); rec['ts_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    s = requests.Session()
    try:
        r, body, text, el = V.fetch(s, 'https://%s/' % item['fetch_host'])
        hdrs = {k.lower(): v for k, v in r.headers.items() if k.lower() != 'set-cookie'}
        a = V.analyse(item['domain'], r.url, hdrs, text)
        rec.update(status=r.status_code, final_host=a['final_host'], markers=a['markers'], wpm=a['wpm'], password=a['password'],
                   adult_flag=a['adult_flag'], child_flag_domain=a['child_flag_domain'], child_flag_text=a['child_flag_text'], error='')
    except Exception as e:  # noqa
        rec.update(status=None, error=type(e).__name__)
    finally:
        s.close()
    return rec


def step_http(F):
    out = os.path.join(OUTD, 'homepage_checks.jsonl')
    done = set()
    if os.path.exists(out):
        for l in open(out):
            try:
                done.add(json.loads(l)['fetch_host'])
            except Exception:
                pass
    items = []
    for b, lo, hi in BUCKETS:
        pool = sorted(d for d, v in F.items() if v['bucket'] == b and v['resolved'] and not v['flagged'])
        pick = random.Random(SEED + 7 + lo).sample(pool, min(HTTP_N, len(pool)))
        for d in pick:
            items.append(dict(part='nonflagged', bucket=b, domain=d, fetch_host=d, screened=screened(d)))
    sub = os.path.join(OUTD, 'subdomain_dns.csv')
    if os.path.exists(sub):
        for r in csv.DictReader(open(sub)):
            if (r['in_shopify_block'] == '1' or r['cname_myshopify'] == '1') and not F[r['domain']]['flagged']:
                items.append(dict(part='subdomain', bucket=r['bucket'], domain=r['domain'], fetch_host=r['host'], screened=screened(r['domain'])))
    todo = [it for it in items if it['fetch_host'] not in done and not it['screened']]
    skipped = [it for it in items if it['screened'] and it['fetch_host'] not in done]
    print('homepage checks', len(items), 'todo', len(todo), 'screened out', len(skipped), 'UA', requests.utils.default_user_agent(), flush=True)
    with open(out, 'a') as fh:
        for it in skipped:
            fh.write(json.dumps(dict(it, status=None, error='not_contacted_keyword_screen')) + '\n')
        fh.flush()
        with ThreadPoolExecutor(6) as ex:
            for i, rec in enumerate(ex.map(check, todo)):
                fh.write(json.dumps(rec) + '\n'); fh.flush()
                if i % 100 == 0:
                    print(i, rec['fetch_host'], rec.get('status'), flush=True)


def storefront(rec):
    ms = set(rec.get('markers') or [])
    return rec.get('status') == 200 and bool(ms & {'Shopify.shop', '/cdn/shop/', 'web-pixels-manager', 'hdr:x-shopid'}) and not rec.get('password')


def same_site(d, host):
    host = (host or '').lower()
    return host == d or host.endswith('.' + d)


def wilson(k, n, z=1.959964):
    if n == 0:
        return (None, None, None)
    p = k / n; den = 1 + z * z / n; c = (p + z * z / (2 * n)) / den; h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return (p, max(0.0, c - h), min(1.0, c + h))


def step_summary(F):
    fun = json.load(open(os.path.join(BASE, 'raw', 'funnel.json')))['per_bucket']
    H = [json.loads(l) for l in open(os.path.join(OUTD, 'homepage_checks.jsonl'))]
    S = list(csv.DictReader(open(os.path.join(OUTD, 'subdomain_dns.csv')))) if os.path.exists(os.path.join(OUTD, 'subdomain_dns.csv')) else []
    out = dict(seed=SEED, sub_n=SUB_N, http_n=HTTP_N, buckets={})
    tot_in, tot_miss, tot_miss_lo, tot_miss_hi = 0.0, 0.0, 0.0, 0.0
    for b, lo, hi in BUCKETS:
        nf = sum(1 for v in F.values() if v['bucket'] == b and v['resolved'] and not v['flagged'])
        h = [r for r in H if r['part'] == 'nonflagged' and r['bucket'] == b]
        contacted = [r for r in h if r.get('error') != 'not_contacted_keyword_screen']
        responded = [r for r in contacted if r.get('status') == 200]   # homepage inspectable (403/errors cannot show markers)
        sf = [r for r in responded if storefront(r)]
        sf_same = [r for r in sf if same_site(r['domain'], r.get('final_host'))]
        sf_ok = [r for r in sf_same if not (r.get('adult_flag') or r.get('child_flag_domain') or r.get('child_flag_text'))]
        p, plo, phi = wilson(len(sf_same), len(responded))
        # in-frame storefronts: flagged domains x live Online Store rate among the verified draw (same definition)
        fb = fun[b]
        inframe = fb['flagged_N'] * fb['verified_live_online_store'] / fb['drawn_n']
        miss = (p or 0) * nf; miss_lo = (plo or 0) * nf; miss_hi = (phi or 0) * nf
        rec = inframe / (inframe + miss) if inframe + miss > 0 else None
        rec_lo = inframe / (inframe + miss_hi) if inframe + miss_hi > 0 else None
        rec_hi = inframe / (inframe + miss_lo) if inframe + miss_lo > 0 else None
        subs = [r for r in S if r['bucket'] == b]
        sub_doms = sorted({r['domain'] for r in subs})
        sub_flag = sorted({r['domain'] for r in subs if (r['in_shopify_block'] == '1' or r['cname_myshopify'] == '1') and not F[r['domain']]['flagged']})
        sub_live = sorted({r['domain'] for r in H if r['part'] == 'subdomain' and r['bucket'] == b and storefront(r)})
        n_sub_sample = len(sub_doms)
        ps = wilson(len(sub_live), n_sub_sample)
        n_dom_b = sum(1 for v in F.values() if v['bucket'] == b)
        out['buckets'][b] = dict(nonflagged_resolved=nf, sampled=len(h), contacted=len(contacted), not_contacted_keyword=len(h) - len(contacted),
                                 inspected_http200=len(responded), not_inspectable=len(contacted) - len(responded),
                                 storefront_same_site=len(sf_same), storefront_other_site=len(sf) - len(sf_same), storefront_same_site_no_content_flag=len(sf_ok),
                                 missed_rate=p, missed_rate_lo=plo, missed_rate_hi=phi,
                                 est_missed=miss, est_missed_lo=miss_lo, est_missed_hi=miss_hi,
                                 inframe_live=inframe, recall=rec, recall_lo=rec_lo, recall_hi=rec_hi,
                                 sub_sample_domains=n_sub_sample, sub_flagged_outside_frame=len(sub_flag), sub_live_storefronts=len(sub_live),
                                 sub_rate=ps[0], sub_rate_hi=ps[2], est_sub_storefronts=(ps[0] or 0) * n_dom_b, est_sub_storefronts_hi=(ps[2] or 0) * n_dom_b)
        tot_in += inframe; tot_miss += miss; tot_miss_lo += miss_lo; tot_miss_hi += miss_hi
    out['overall_counts'] = dict(contacted=sum(v['contacted'] for v in out['buckets'].values()), inspected=sum(v['inspected_http200'] for v in out['buckets'].values()),
                                 storefronts_missed=sum(v['storefront_same_site'] for v in out['buckets'].values()),
                                 sub_live=sum(v['sub_live_storefronts'] for v in out['buckets'].values()),
                                 est_sub_total=sum(v['est_sub_storefronts'] for v in out['buckets'].values()),
                                 not_contacted_keyword=sum(v['not_contacted_keyword'] for v in out['buckets'].values()),
                                 subdomain_homepages_checked=sum(1 for r in H if r['part'] == 'subdomain' and r.get('error') != 'not_contacted_keyword_screen'))
    out['overall'] = dict(inframe_live=tot_in, est_missed=tot_miss, recall=tot_in / (tot_in + tot_miss), recall_lo=tot_in / (tot_in + tot_miss_hi), recall_hi=tot_in / (tot_in + tot_miss_lo),
                          note='bucket-wise Wilson bounds summed; not a joint interval')
    json.dump(out, open(os.path.join(OUTD, 'frame_recall_summary.json'), 'w'), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    F = frame()
    step = sys.argv[1]
    {'dns': step_dns, 'http': step_http, 'summary': step_summary}[step](F)
