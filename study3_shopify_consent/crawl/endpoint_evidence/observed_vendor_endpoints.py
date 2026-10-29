"""Tabulate vendor endpoints actually observed in Study 2 (1,408 loads) to ground
vendor_endpoints.json. Uses Study 2's vendor host table (analyze_capture.V). Output:
observed_vendor_endpoints.csv (vendor, host, path prefix, resource type, n requests, n loads)."""
import gzip, json, glob, os, re, sys, collections
from urllib.parse import urlsplit
CAP = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../study2_creator_links/capture'))
sys.path.insert(0, CAP)
import analyze_capture as A
cnt = collections.Counter(); loads = collections.defaultdict(set)
for f in glob.glob(os.path.join(CAP, 'evidence', '*.json.gz')):
    d = json.load(gzip.open(f))
    for x in d['requests']:
        u = urlsplit(x['url'])
        v = A.vendor_of(u.hostname or '', u.path)
        if not v:
            continue
        segs = [s for s in u.path.split('/') if s]
        pre = '/' + '/'.join(re.sub(r'\d{3,}', '<n>', s) for s in segs[:2])
        k = (v, u.hostname, pre, x.get('rt'))
        cnt[k] += 1; loads[k].add(os.path.basename(f))
rows = sorted(cnt.items(), key=lambda kv: (kv[0][0], -kv[1]))
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'observed_vendor_endpoints.csv'), 'w') as fo:
    fo.write('vendor,host,path_prefix,resource_type,n_requests,n_loads\n')
    for (v, h, p, rt), n in rows:
        fo.write(f'{v},{h},"{p}",{rt},{n},{len(loads[(v, h, p, rt)])}\n')
print('rows', len(rows))
