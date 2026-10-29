"""Live validation of the GPC signal inside Shopify's sandboxes, from the crawl's raw records.
For arms A0 (control), A2/A2r (emulated GPC in Chromium) and V1 (native GPC in Brave):
  - workers: Shopify STRICT sandbox workers vs other workers; injection state/marker; whether the worker's own
    code ran after the injection (own-global count grew); navigator.globalPrivacyControl as read at the end
  - frames: navigator.globalPrivacyControl in every frame, incl. Shopify LAX sandbox iframes
  - Sec-GPC request header by issuing session type (page / iframe / worker)
Writes validation/gpc_live_summary.json."""
import collections, glob, gzip, json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, '..', 'raw')
STRICT = re.compile(r'/(web-pixels|wpm)@[0-9a-z]+/web-pixel-[^/]+/sandbox/worker\.(modern|legacy)\.js')
LAX = re.compile(r'/(web-pixels|wpm)@[0-9a-z]+/(app|custom)/web-pixel-[^/]+/sandbox/(modern|legacy)/')
out = {}
for arm in ('A0', 'A2', 'A2r', 'V1'):
    c = collections.Counter()
    for fn in glob.glob(os.path.join(RAW, f'*__{arm}.json.gz')):
        r = json.load(gzip.open(fn, 'rt'))
        if not r.get('requests'):
            continue
        c['loads'] += 1
        tg = {t['sid']: t for t in r.get('targets') or []}
        for w in r.get('workers_gpc') or []:
            v = w.get('val') or {}
            kind = 'strict' if STRICT.search(w.get('url') or '') else 'other'
            c[f'{kind}_workers'] += 1
            c[f'{kind}_workers_gpc_{v.get("gpc")}'] += 1
            inj = v.get('inj')
            if inj:
                c[f'{kind}_workers_marker'] += 1
                if (v.get('n1') or 0) - 1 > (inj.get('n0') or 0):
                    c[f'{kind}_workers_own_globals_added_after_injection'] += 1
            st = ((tg.get(w.get('sid')) or {}).get('inject') or {}).get('state')
            if st:
                c[f'{kind}_workers_inject_state_{st}'] += 1
            if kind == 'strict' and v.get('gpc') == 'undefined' and 'globalPrivacyControl' in (v.get('nav_proto_keys') or ''):
                c['strict_workers_gpc_key_present_but_value_undefined'] += 1
        for f in r.get('frames_gpc') or []:
            kind = 'lax_sandbox' if LAX.search(f.get('h') or '') else 'other'
            c[f'{kind}_frames'] += 1
            c[f'{kind}_frames_gpc_{f.get("g")}'] += 1
        for q in r.get('requests') or []:
            if 'gpc_hdr' in q:
                c[f'req_{q.get("sess")}_with_header_info'] += 1
                if str(q.get('gpc_hdr')) == '1':
                    c[f'req_{q.get("sess")}_sec_gpc_1'] += 1
    out[arm] = dict(sorted(c.items()))
json.dump(out, open(os.path.join(HERE, 'gpc_live_summary.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
