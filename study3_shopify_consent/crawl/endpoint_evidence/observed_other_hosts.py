"""Hosts (not in Study 2's vendor table) matching selected keywords in Study 2 evidence; grounds extra
entries in vendor_endpoints.json. Output: observed_other_hosts.csv"""
import gzip, json, glob, os, re, collections
from urllib.parse import urlsplit
CAP = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../study2_creator_links/capture'))
KW = re.compile(r'postscript|pscript|monorail|shopifysvc|shop\.app|trekkie|triplewhale|northbeam|elevar|littledata|yotpo|attn|attentive|tiktok|snap|pinterest|reddit|bing|twitter|x\.com|linkedin|criteo|applovin|axon|amazon|tvspix|klaviyo|nextdoor|quora|adsrvr|liadm|taboola|outbrain', re.I)
cnt = collections.Counter(); loads = collections.defaultdict(set)
for f in glob.glob(os.path.join(CAP, 'evidence', '*.json.gz')):
    for x in json.load(gzip.open(f))['requests']:
        u = urlsplit(x['url']); h = u.hostname or ''
        if KW.search(h) or re.search(r'/\.well-known/shopify/monorail|/api/collect|/web-pixels', u.path):
            segs = [s for s in u.path.split('/') if s][:2]
            k = (h if not re.search(r'/\.well-known/shopify/monorail', u.path) else '<storefront>', '/' + '/'.join(re.sub(r'[0-9a-f]{12,}|\d{4,}', '<id>', s) for s in segs))
            cnt[k] += 1; loads[k].add(os.path.basename(f))
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'observed_other_hosts.csv'), 'w') as fo:
    fo.write('host,path_prefix,n_requests,n_loads\n')
    for (h, p), n in sorted(cnt.items(), key=lambda kv: -len(loads[kv[0]])):
        fo.write(f'{h},"{p}",{n},{len(loads[(h, p)])}\n')
