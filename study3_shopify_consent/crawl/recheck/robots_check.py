"""Retrospective robots.txt check (final audit, 2026-09-26).
The crawl did not consult robots.txt. For every store it loaded (main sample and creator stratum, except the
child-directed motivating store C005, which this re-check does not contact), fetch /robots.txt once from the landing
host with the HTTP library's default user agent (no spoofing), and evaluate, for the group that applies to a crawler
without a named product token (User-agent: *), whether the exact paths we requested were disallowed:
  landing  - the landing URL path + query (with our canary) loaded by the browser crawl
  home     - "/" (the one homepage request of the sampling stage)
  pjson    - "/products.json?limit=1" (sampling stage, only stores whose product URL came from it)
Matching follows RFC 9309 (longest match wins; Allow wins ties; '*' wildcard, '$' end anchor).
Resumable: results are appended to robots_raw.jsonl; rerun skips stores already fetched.
Politeness: one request per site; at most 6 concurrent requests overall.
"""
import csv, json, os, re, sys, time, gzip
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
import requests
H = os.path.dirname(os.path.abspath(__file__))
ST = os.path.join(H, '..', '..')
OUT = os.path.join(H, 'robots'); os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, 'robots_raw.jsonl')
EXCLUDE = {'C005'}  # child-directed motivating store: not contacted again

def stores():
    plan = json.load(open(os.path.join(ST, 'crawl', 'plan.json')))['stores']
    samp = {r['store_id']: r for r in csv.DictReader(open(os.path.join(ST, 'sample', 'sample.csv')))}
    out = []
    for s in plan:
        if s['store_id'] in EXCLUDE:
            continue
        pj = 'product_url_from_products.json' in (samp.get(s['store_id'], {}).get('notes') or '')
        out.append(dict(store_id=s['store_id'], stratum=s['stratum'], url=s['url'], pjson=pj))
    return out

def fetch(s):
    u = urlsplit(s['url'])
    ru = f'{u.scheme}://{u.netloc}/robots.txt'
    rec = dict(store_id=s['store_id'], robots_url=ru, at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    try:
        r = requests.get(ru, timeout=20, allow_redirects=True)
        rec.update(status=r.status_code, final_url=r.url[:300], ctype=r.headers.get('content-type', '')[:80], text=r.text[:200000] if r.status_code == 200 else None)
    except Exception as e:
        rec.update(status=None, error=type(e).__name__)
    return rec

# ---------------- RFC 9309 parsing and matching
def parse(text):
    groups, cur, last_was_rule = [], None, False
    for line in (text or '').splitlines():
        line = line.split('#', 1)[0].strip()
        if ':' not in line:
            continue
        k, v = line.split(':', 1); k = k.strip().lower(); v = v.strip()
        if k == 'user-agent':
            if cur is None or last_was_rule:
                cur = dict(agents=[], rules=[]); groups.append(cur)
            cur['agents'].append(v.lower()); last_was_rule = False
        elif k in ('allow', 'disallow') and cur is not None:
            cur['rules'].append((k, v)); last_was_rule = True
    return groups

def rules_for(groups, token):
    named = [g for g in groups if any(a != '*' and a and a in token for a in g['agents'])]
    if named:
        return [r for g in named for r in g['rules']], 'named'
    star = [g for g in groups if '*' in g['agents']]
    return [r for g in star for r in g['rules']], ('star' if star else 'none')

def pat_rx(p):
    end = p.endswith('$'); p = p[:-1] if end else p
    return re.compile('^' + '.*'.join(re.escape(x) for x in p.split('*')) + ('$' if end else ''))

def allowed(rules, path):
    best = None  # (len, kind)
    for kind, pat in rules:
        if kind == 'disallow' and pat == '':
            continue
        if pat_rx(pat).match(path):
            L = len(pat)
            if best is None or L > best[0] or (L == best[0] and kind == 'allow'):
                best = (L, kind, pat)
    return (best is None or best[1] == 'allow'), (best[2] if best else None)

def main():
    S = stores()
    done = set()
    if os.path.exists(RAW):
        for l in open(RAW):
            try: done.add(json.loads(l)['store_id'])
            except Exception: pass
    todo = [s for s in S if s['store_id'] not in done]
    print('stores', len(S), 'to fetch', len(todo), flush=True)
    with ThreadPoolExecutor(6) as ex, open(RAW, 'a') as f:
        for i, rec in enumerate(ex.map(fetch, todo)):
            f.write(json.dumps(rec) + '\n'); f.flush()
            if i % 100 == 0: print(i, rec['store_id'], rec.get('status'), flush=True)
    recs = {}
    for l in open(RAW):
        r = json.loads(l); recs[r['store_id']] = r
    rows = []
    for s in S:
        r = recs.get(s['store_id'], {})
        u = urlsplit(s['url']); landing = u.path + ('?' + u.query if u.query else '')
        row = dict(store_id=s['store_id'], stratum=s['stratum'], status=r.get('status'), error=r.get('error'))
        if r.get('status') == 200 and r.get('text') is not None and not (r.get('ctype', '').startswith('text/html')):
            g = parse(r['text'])
            rules, which = rules_for(g, 'headlesschrome')
            row['group'] = which; row['n_rules'] = len(rules)
            for name, p in (('landing', landing), ('landing_path', u.path or '/'), ('home', '/'), ('pjson', '/products.json?limit=1' if s['pjson'] else None)):
                if p is None:
                    row[name] = None; continue
                ok, pat = allowed(rules, p)
                row[name] = ok; row[name + '_rule'] = pat
            row['disallow_all'] = not allowed(rules, '/')[0]
        else:
            row['group'] = 'no_robots'  # 4xx: RFC 9309 treats as allow-all; 5xx/unreachable: disallow-all
        rows.append(row)
    import pandas as pd
    D = pd.DataFrame(rows); D.to_csv(os.path.join(OUT, 'robots_eval.csv'), index=False)
    ok200 = D[D.group != 'no_robots']
    st = D.status.fillna(-1).astype(int)
    summ = dict(stores=len(D), main=int((D.stratum == 'main').sum()), creator=int((D.stratum == 'creator').sum()), excluded=sorted(EXCLUDE),
                robots_200=int(len(ok200)), status_4xx=int(((st >= 400) & (st < 500)).sum()), status_5xx=int((st >= 500).sum()), unreachable=int((st == -1).sum()),
                html_instead_of_robots=int(((D.group == 'no_robots') & (st == 200)).sum()),
                landing_disallowed=int((ok200.landing == False).sum()), landing_disallowed_stores=sorted(ok200[ok200.landing == False].store_id),
                landing_disallow_rules=sorted(set(ok200[ok200.landing == False].landing_rule.dropna())),
                landing_path_disallowed=int((ok200.landing_path == False).sum()),
                landing_disallowed_by_query_only=int(((ok200.landing == False) & (ok200.landing_path != False)).sum()),
                landing_disallowed_by_utm_rule=int(ok200[ok200.landing == False].landing_rule.fillna('').str.contains('utm').sum()),
                home_disallowed=int((ok200.home == False).sum()), pjson_checked=int(ok200.pjson.notna().sum()), pjson_disallowed=int((ok200.pjson == False).sum()),
                disallow_all=int(ok200.disallow_all.sum()), named_group_for_headlesschrome=int((ok200.group == 'named').sum()))
    json.dump(summ, open(os.path.join(OUT, 'robots_summary.json'), 'w'), indent=1)
    print(json.dumps(summ, indent=1))

if __name__ == '__main__':
    main()
