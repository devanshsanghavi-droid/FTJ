"""Beyond-Shopify pilot (Part B2), screening step 1: DNS-only platform flags.

Passive: only DNS lookups through the system resolver (no request to any website).

* Tranco ranks 1-200,000: re-uses study3 sample/raw/dns_results.csv (apex + www, resolved 26 Sep 2026).
* Tranco ranks 200,001-1,000,000 (same list L5PZ4): resolves www.<domain> only (the www host catches
  ~95% of Wix/BigCommerce domains in the top 200k: 147/153 Wix, 133/141 BigCommerce).

Flags (a domain is flagged when a resolved host is flagged):
  wix         A record in 185.230.60.0/22 (RIPE: wix_com_inc / Wixcom-EU), the Wix edge 34.149.87.45,
              or CNAME chain ending in wixdns.net
  bigcommerce A record in a BigCommerce ARIN net (org INTER-1370: 63.141.128.0/19, 192.200.160.0/19,
              104.195.64.0/18) or CNAME containing "bigcommerce"
  shopify     study3 rule (23.227.32.0/19 or *.myshopify.com CNAME) - recorded so these can be excluded
  cloudflare  A record in Cloudflare's published IPv4 ranges (inputs/cloudflare_ips_v4.txt)
  vercel / netlify  common Jamstack hosts (Partytown oversampling stratum)

Outputs (in raw/): platform_flags.csv.gz (one row per flagged domain: any flag other than cloudflare-only in
ranks > 200k; all flags in ranks <= 200k), dns_beyond_progress.json (checkpoint), dns_beyond_summary.json.
Politeness: <= 40 lookups in flight. Resumable (watermark checkpoint).
Usage: python dns_platforms.py top200k | scan | summary
"""
import csv, gzip, ipaddress, json, os, socket, sys, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
RAW = os.path.join(HERE, 'raw'); os.makedirs(RAW, exist_ok=True)
TRANCO = os.path.join(STUDY, 'sample', 'raw', 'tranco_L5PZ4_top1m.csv')
DNS200 = os.path.join(STUDY, 'sample', 'raw', 'dns_results.csv')
CF_FILE = os.path.join(HERE, '..', 'inputs', 'cloudflare_ips_v4.txt')
OUT_TOP = os.path.join(RAW, 'platform_flags_top200k.csv.gz')
OUT_SCAN = os.path.join(RAW, 'platform_flags_200k_1m.csv')      # appended per chunk, gzipped at the end
PROG = os.path.join(RAW, 'dns_beyond_progress.json')
CONC = 40
CHUNK = 4000
socket.setdefaulttimeout(8)

WIX = [ipaddress.ip_network('185.230.60.0/22')]
WIX_IPS = {'34.149.87.45'}
BC = [ipaddress.ip_network(x) for x in ('63.141.128.0/19', '192.200.160.0/19', '104.195.64.0/18')]
SHOP = [ipaddress.ip_network('23.227.32.0/19')]
VERCEL = [ipaddress.ip_network(x) for x in ('76.76.21.0/24', '66.33.60.0/24', '216.198.79.0/24')]
NETLIFY_IPS = {'75.2.60.5', '99.83.231.61'}
CF = [ipaddress.ip_network(l.strip()) for l in open(CF_FILE) if l.strip()]
FIELDS = ['rank', 'domain', 'host', 'canon', 'ips', 'wix', 'bigcommerce', 'shopify', 'cloudflare', 'vercel', 'netlify']


def flags(canon, ips_s):
    ips = []
    for s in ips_s:
        try:
            ips.append(ipaddress.ip_address(s))
        except ValueError:
            pass
    inn = lambda nets: int(any(i in n for i in ips for n in nets))
    canon = (canon or '').lower()
    return dict(
        wix=int(inn(WIX) or bool(set(ips_s) & WIX_IPS) or canon.endswith('wixdns.net')),
        bigcommerce=int(inn(BC) or 'bigcommerce' in canon),
        shopify=int(inn(SHOP) or canon == 'shop.myshopify.com' or canon.endswith('.myshopify.com')),
        cloudflare=inn(CF),
        vercel=int(inn(VERCEL) or 'vercel' in canon),
        netlify=int(bool(set(ips_s) & NETLIFY_IPS) or 'netlify' in canon))


def resolve(host):
    try:
        infos = socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_STREAM, 0, socket.AI_CANONNAME)
        canon, ips = '', []
        for fam, typ, proto, cn, sa in infos:
            if cn and not canon:
                canon = cn
            if sa[0] not in ips:
                ips.append(sa[0])
        return canon.rstrip('.').lower(), ips, ''
    except socket.gaierror as e:
        return '', [], 'gaierror:%s' % e.errno
    except Exception as e:  # noqa
        return '', [], 'err:%s' % type(e).__name__


def step_top200k():
    """Flags for ranks 1-200k from the existing study3 DNS results (no new lookups)."""
    rows = []
    for r in csv.DictReader(open(DNS200)):
        f = flags(r['canon'], r['ips'].split())
        if any(f.values()):
            rows.append(dict(rank=r['rank'], domain=r['domain'], host=r['host'], canon=r['canon'], ips=r['ips'], **f))
    with gzip.open(OUT_TOP, 'wt', newline='') as fh:
        w = csv.DictWriter(fh, FIELDS); w.writeheader(); w.writerows(rows)
    print('top200k flagged host rows', len(rows))


def step_scan():
    doms = []
    with open(TRANCO) as f:
        for row in csv.reader(f):
            r = int(row[0])
            if 200000 < r <= 1000000:
                doms.append((r, row[1].strip().lower()))
    # Streaming with <= CONC lookups in flight. Checkpoint = watermark (every index below it is finished);
    # a resume restarts at the watermark, so a few rows can be written twice (deduplicated in `summary`).
    prog = json.load(open(PROG)) if os.path.exists(PROG) else dict(watermark=0, resolved=0, nx=0, err=0, flagged=0, done=0)
    if 'next_chunk' in prog:          # first (chunked) version of this script
        prog['watermark'] = prog.pop('next_chunk') * CHUNK
    start = prog['watermark']
    print('domains', len(doms), 'resume at index', start, flush=True)
    from concurrent.futures import wait, FIRST_COMPLETED
    t0 = time.time()
    fh = open(OUT_SCAN, 'a', newline='')
    w = csv.DictWriter(fh, FIELDS)
    if fh.tell() == 0:
        w.writeheader()
    finished = set()
    wm = start
    with ThreadPoolExecutor(CONC) as ex:
        it = iter(range(start, len(doms)))
        pending = {}
        for _ in range(CONC):
            i = next(it, None)
            if i is None:
                break
            pending[ex.submit(resolve, 'www.' + doms[i][1])] = i
        n = 0
        while pending:
            fin, _ = wait(list(pending), return_when=FIRST_COMPLETED)
            for fu in fin:
                i = pending.pop(fu)
                r, d = doms[i]
                canon, ips, err = fu.result()
                prog['done'] += 1
                if ips:
                    prog['resolved'] += 1
                elif err.startswith('gaierror'):
                    prog['nx'] += 1
                else:
                    prog['err'] += 1
                f = flags(canon, ips)
                if f['wix'] or f['bigcommerce'] or f['shopify'] or f['vercel'] or f['netlify']:
                    prog['flagged'] += 1
                    w.writerow(dict(rank=r, domain=d, host='www.' + d, canon=canon, ips=' '.join(ips), **f))
                finished.add(i)
                n += 1
                j = next(it, None)
                if j is not None:
                    pending[ex.submit(resolve, 'www.' + doms[j][1])] = j
            while wm in finished:
                finished.discard(wm); wm += 1
            if n >= 5000:
                n = 0
                fh.flush()
                prog['watermark'] = wm
                json.dump(prog, open(PROG, 'w'))
                print('watermark=%d/%d resolved=%d flagged=%d %.0fs' % (wm, len(doms), prog['resolved'], prog['flagged'], time.time() - t0), flush=True)
    fh.flush(); fh.close()
    prog['watermark'] = len(doms)
    json.dump(prog, open(PROG, 'w'))
    print('FINISHED', json.dumps(prog), flush=True)


def step_summary():
    import collections
    c = collections.Counter()
    for path, opener in ((OUT_TOP, lambda p: gzip.open(p, 'rt')), (OUT_SCAN, open)):
        if not os.path.exists(path):
            continue
        seen = {}
        for r in csv.DictReader(opener(path)):
            s = seen.setdefault(r['domain'], dict(rank=int(r['rank']), **{k: 0 for k in FIELDS[5:]}))
            for k in FIELDS[5:]:
                s[k] |= int(r[k])
        for d, s in seen.items():
            band = 'top200k' if s['rank'] <= 200000 else '200k_1m'
            for k in FIELDS[5:]:
                if s[k]:
                    c['%s_%s' % (band, k)] += 1
    prog = json.load(open(PROG)) if os.path.exists(PROG) else {}
    out = dict(counts=dict(sorted(c.items())), scan_progress=prog,
               note='top200k: apex+www from study3 dns_results.csv; 200k_1m: www host only. Domains counted once per flag.')
    json.dump(out, open(os.path.join(RAW, 'dns_beyond_summary.json'), 'w'), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    {'top200k': step_top200k, 'scan': step_scan, 'summary': step_summary}[sys.argv[1]]()
