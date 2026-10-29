"""Probe Shopify's server-computed consent string (Server-Timing `_cmp`) with and without a
`Sec-GPC: 1` request header. Plain GETs, honest UA, no cookies, >=10 s between requests to
the same site. Output: cmp_header_probe.csv

Decoding follows the parser in Shopify's Web Pixels Manager bundle (function Le/qe in
wpm_manager_modern.pretty.js): "3<visitor-choices>.<processing purposes>_<region>_<display_banner t/f>_
<sale_of_data_region t/f>_<consent id>". Visitor choices: lower-case letter = declined,
upper-case = accepted, absent = no choice. Purposes: letter present = processing allowed
(A analytics, M marketing, P preferences, S sale of data).
"""
import csv, time, re, sys, urllib.request, datetime
UA = 'Mozilla/5.0 (compatible; shopify-consent-study/1.0; non-commercial academic measurement crawler)'
SITES = sys.argv[1:] or ['https://c005.store.example/', 'https://c005.store.example/?skipCache=true',
                         'https://s0347.store.example/', 'https://www.brooklinen.com/']
REPS = 2

def decode_cmp(v):
    if not v or not v.startswith('3'):
        return {}
    parts = v[1:].split('_')
    head = parts[0]
    choices, purposes = (head.split('.', 1) + [''])[:2]
    def choice(ch):
        return 'declined' if ch.lower() in choices else ('accepted' if ch.upper() in choices else 'none')
    return dict(choice_analytics=choice('a'), choice_marketing=choice('m'), choice_preferences=choice('p'),
                choice_sale_of_data=choice('s'), allow_analytics='A' in purposes, allow_marketing='M' in purposes,
                allow_preferences='P' in purposes, allow_sale_of_data='S' in purposes,
                region=parts[1] if len(parts) > 1 else '', display_banner=(parts[2] == 't') if len(parts) > 2 else None,
                sale_of_data_region=(parts[3] == 't') if len(parts) > 3 else None)

rows = []
last = {}
plan = [(s, g, r) for r in range(REPS) for g in (0, 1) for s in SITES]
for site, gpc, rep in plan:
    host = re.sub(r'^https?://([^/]+).*', r'\1', site)
    wait = 10 - (time.time() - last.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    hdrs = {'User-Agent': UA}
    if gpc:
        hdrs['Sec-GPC'] = '1'
    req = urllib.request.Request(site, headers=hdrs)
    row = dict(ts=datetime.datetime.utcnow().isoformat() + 'Z', url=site, sec_gpc=gpc, rep=rep)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            st = ' '.join(resp.headers.get_all('Server-Timing') or [])
            row.update(status=resp.status, cf_cache_status=resp.headers.get('cf-cache-status'), age=resp.headers.get('age'))
            m = re.search(r'_cmp;desc="([^"]+)"', st)
            row['cmp_raw'] = m.group(1) if m else ''
            for k in ('country', 'edge'):
                mm = re.search(k + r';desc="([^"]+)"', st)
                row[k] = mm.group(1) if mm else ''
            row.update(decode_cmp(row['cmp_raw']))
    except Exception as e:
        row['error'] = str(e)[:120]
    last[host] = time.time()
    rows.append(row)
    print(row['ts'], site, 'gpc', gpc, row.get('cf_cache_status'), row.get('cmp_raw'), flush=True)
keys = sorted({k for r in rows for k in r}, key=lambda k: (k not in ('ts', 'url', 'sec_gpc', 'rep'), k))
with open('cmp_header_probe.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
