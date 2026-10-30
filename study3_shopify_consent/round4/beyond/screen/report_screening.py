"""Print the screening-results tables (markdown) for PROTOCOL.md section 7 from raw/ files. No network."""
import csv, json, os, collections, math

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')


def wilson(k, n, z=1.959964):
    if not n:
        return (float('nan'),) * 2
    p = k / n; den = 1 + z * z / n; c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0, c - h), min(1, c + h)


recs = [json.loads(l) for l in open(os.path.join(RAW, 'screen_results.jsonl'))]
recs = [r for r in recs if r['stratum'] != 'CAL']
first = {}
for r in recs:
    first.setdefault(r['domain'], r)
recs = list(first.values())
for r in recs:   # records screened with the first marker version: drop the two known false-positive CMP signatures
    if r.get('outcome') == 'ok' and 'generic_banner_markup' not in r:
        r['cmps'] = [c for c in r.get('cmps', []) if c not in ('consentmo',) and not (c == 'bigcommerce_consent' and 'consentmanagerstoreconfig' not in r['bigcommerce'].get('consent', []))]
import markers as M
from build_candidates import page_text
for r in recs:   # re-analyse saved (marker) pages with the current markers.py, as build_candidates.py does
    if r.get('outcome') == 'ok':
        t = page_text(r['domain'])
        if t is not None:
            a = M.analyse(r['domain'], r.get('final_url', 'https://%s/' % r['fetch_host']), {'server': r.get('server', '')}, t)
            r.update(partytown=a['partytown'], zaraz=a['zaraz'], gateway=a['gateway'], cmps=a.get('cmps'), tcf=a.get('tcf'))
S = ['W', 'BC', 'R', 'CF', 'J', 'J2']
out = collections.defaultdict(collections.Counter)
for r in recs:
    o = r.get('outcome') or 'error'
    g = ('ok' if o == 'ok' else 'name_screen' if o.startswith('not_contacted_name') else
         'robots' if 'robots_disallowed' in o else 'robots_unreach' if 'unreachable' in o else
         'blocked' if o in ('http_403', 'http_429', 'http_503', 'http_401') else 'other_fail')
    out[r['stratum']][g] += 1
    out[r['stratum']]['all'] += 1
print('| Stratum | Queued & screened | Name screen (not contacted) | robots.txt disallowed | robots.txt unreachable (skipped) | 401/403/429/503 | Other failure | HTTP 200 HTML |')
print('|---|---:|---:|---:|---:|---:|---:|---:|')
for s in S:
    c = out[s]
    print('| %s | %d | %d | %d | %d | %d | %d | %d |' % (s, c['all'], c['name_screen'], c['robots'], c['robots_unreach'], c['blocked'], c['other_fail'], c['ok']))
print()
# marker prevalence per stratum among OK pages (stored fields)
print('| Stratum | OK pages | Partytown scripts | Partytown library only | Zaraz | Gateway (static) | Static CMP or TCF |')
print('|---|---:|---:|---:|---:|---:|---:|')
for s in S:
    ok = [r for r in recs if r['stratum'] == s and r.get('outcome') == 'ok']
    n = len(ok)
    def cnt(f):
        k = sum(1 for r in ok if f(r)); lo, hi = wilson(k, n)
        return '%d (%.1f%%; %.1f–%.1f)' % (k, 100 * k / n if n else 0, 100 * lo, 100 * hi) if n else '0'
    print('| %s | %d | %s | %s | %s | %s | %s |' % (s, n, cnt(lambda r: r['partytown']['any']), cnt(lambda r: r['partytown'].get('lib') and not r['partytown']['any']),
          cnt(lambda r: r['zaraz']['any']), cnt(lambda r: r['gateway']['any']), cnt(lambda r: bool(r.get('cmps')) or r.get('tcf'))))
print()
C = list(csv.DictReader(open(os.path.join(HERE, '..', 'candidates.csv'))))
print('| Setup | Sites with marker | Eligible (A/B/L/Z) | Tier A / B / L-Z | Selected | Reserve | Backup, no static CMP (U) | Main exclusion reasons |')
print('|---|---:|---:|---|---:|---:|---:|---|')
for x in ['partytown', 'zaraz', 'gateway', 'wix', 'bigcommerce']:
    rows = [r for r in C if r['architecture'] == x]
    el = [r for r in rows if r['eligible'] == '1' and r['tier'] != 'U']
    t = collections.Counter(r['tier'] for r in el)
    ex = collections.Counter(e for r in rows if r['eligible'] != '1' for e in r['exclusion'].split('|') if e)
    print('| %s | %d | %d | %d / %d / %d | %d | %d | %d | %s |' % (x, len(rows), len(el), t['A'], t['B'], t['L'] + t['Z'],
          sum(r['selection'] == 'selected' for r in rows), sum(r['selection'] == 'reserve' for r in rows),
          sum(r['selection'] == 'backup_unconfirmed_cmp' for r in rows),
          ', '.join('%s %d' % kv for kv in ex.most_common(4))))
