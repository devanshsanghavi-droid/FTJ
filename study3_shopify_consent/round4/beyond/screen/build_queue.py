"""Build the screening queues for the beyond-Shopify pilot (Part B2) from DNS flags only.

Strata (all from Tranco list L5PZ4):
  W   Wix-hosted domains, ranks 1-1,000,000 (census of the DNS-flagged set)
  BC  BigCommerce-hosted domains, ranks 1-1,000,000 (census)
  R   seeded simple random sample of resolved ranks 1-200,000 domains (prevalence stratum for Partytown,
      Zaraz and tag gateways; the only stratum used for prevalence estimates)
  CF  seeded random sample of Cloudflare-proxied ranks 1-200,000 domains (Zaraz oversample; Zaraz needs Cloudflare)
  J   Vercel- or Netlify-hosted ranks 1-200,000 domains (Partytown oversample; census)
  J2  Vercel- or Netlify-hosted ranks 200,001-1,000,000 domains (www host flagged), rank order (added 27 Sep 03:20 PDT
      to top up Partytown and gateway candidates after the top-200k strata fell short)
Always excluded before any contact: Shopify-flagged domains and the study3 main sample (measured in Part A),
platform/vendor corporate domains, and names matching the adult / child-directed screens (markers.py).
Usage: python build_queue.py <stratum> [n]     writes queues/queue_<stratum>.csv (domain,rank,stratum,fetch_host)
"""
import csv, gzip, os, random, sys
import markers as M

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
RAW = os.path.join(HERE, 'raw')
QD = os.path.join(HERE, 'queues'); os.makedirs(QD, exist_ok=True)
SEED = 20260927
CORP = ('wix.com', 'wixsite.com', 'wixstatic.com', 'parastorage.com', 'wixpress.com', 'wixmp.com', 'wixapps.net',
        'wix-code.com', 'wixstudio.com', 'editorx.com', 'wixanswers.com', 'wixappcloud.com', 'expiredwixdomain.com',
        'wixdns.net', 'bigcommerce.com', 'mybigcommerce.com', 'bigcommerce.net', 'cloudflare.com', 'cloudflare.net',
        'cloudflare-dns.com', 'cloudflareinsights.com', 'vercel.com', 'vercel.app', 'netlify.com', 'netlify.app',
        'shopify.com', 'myshopify.com', 'partytown.qwik.dev', 'builder.io', 'qwik.dev', 'stape.io', 'google.com',
        'googletagmanager.com', 'workers.dev', 'pages.dev')


def load_flags():
    F = {}
    def add(r):
        d = F.setdefault(r['domain'], dict(rank=int(r['rank']), hosts={}, **{k: 0 for k in ('wix', 'bigcommerce', 'shopify', 'cloudflare', 'vercel', 'netlify')}))
        for k in ('wix', 'bigcommerce', 'shopify', 'cloudflare', 'vercel', 'netlify'):
            if int(r[k]):
                d[k] = 1
                d['hosts'].setdefault(k, set()).add(r['host'])
    for r in csv.DictReader(gzip.open(os.path.join(RAW, 'platform_flags_top200k.csv.gz'), 'rt')):
        add(r)
    p = os.path.join(RAW, 'platform_flags_200k_1m.csv')
    if os.path.exists(p):
        for r in csv.DictReader(open(p)):
            add(r)
    return F


def resolved_top200k():
    out = {}
    for r in csv.DictReader(open(os.path.join(STUDY, 'sample', 'raw', 'dns_results.csv'))):
        if r['ips']:
            d = out.setdefault(r['domain'], dict(rank=int(r['rank']), hosts=set()))
            d['hosts'].add(r['host'])
    return out


def excluded(d, F):
    if any(d == c or d.endswith('.' + c) for c in CORP):
        return True
    if F.get(d, {}).get('shopify'):
        return True
    return bool(M.ADULT_DOMAIN.search(d) or M.CHILD_DOMAIN.search(d))


def part_a():
    s = set()
    for r in csv.DictReader(open(os.path.join(STUDY, 'sample', 'sample.csv'))):
        s.add(r['domain'].lower())
    return s


def pick_host(d, hosts):
    return d if d in hosts else ('www.' + d if 'www.' + d in hosts else d)


def main():
    st = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else None
    F = load_flags()
    A = part_a()
    rows = []
    if st in ('W', 'BC'):
        key = 'wix' if st == 'W' else 'bigcommerce'
        for d, v in sorted(F.items(), key=lambda x: x[1]['rank']):
            if v[key] and d not in A and not excluded(d, F):
                rows.append(dict(domain=d, rank=v['rank'], stratum=st, fetch_host=pick_host(d, v['hosts'][key])))
    elif st == 'J2':
        for d, v in sorted(F.items(), key=lambda x: x[1]['rank']):
            if v['rank'] <= 200000 or not (v['vercel'] or v['netlify']) or v['wix'] or v['bigcommerce']:
                continue
            if d in A or excluded(d, F):
                continue
            hs = set().union(*[v['hosts'].get(k, set()) for k in ('vercel', 'netlify')])
            rows.append(dict(domain=d, rank=v['rank'], stratum=st, fetch_host=pick_host(d, hs)))
    elif st in ('R', 'CF', 'J'):
        R = resolved_top200k()
        pool = []
        for d, v in R.items():
            if d in A or excluded(d, F):
                continue
            f = F.get(d, {})
            if f.get('wix') or f.get('bigcommerce'):
                continue
            if st == 'CF' and not f.get('cloudflare'):
                continue
            if st == 'J' and not (f.get('vercel') or f.get('netlify')):
                continue
            pool.append((d, v))
        pool.sort(key=lambda x: x[1]['rank'])
        rnd = random.Random(SEED + {'R': 0, 'CF': 1, 'J': 2}[st])
        rnd.shuffle(pool)
        for d, v in pool:
            rows.append(dict(domain=d, rank=v['rank'], stratum=st, fetch_host=pick_host(d, v['hosts'])))
    if n:
        rows = rows[:n]
    path = os.path.join(QD, 'queue_%s.csv' % st)
    with open(path, 'w', newline='') as fh:
        w = csv.DictWriter(fh, ['domain', 'rank', 'stratum', 'fetch_host']); w.writeheader(); w.writerows(rows)
    print(st, 'rows', len(rows), '->', path)


if __name__ == '__main__':
    main()
