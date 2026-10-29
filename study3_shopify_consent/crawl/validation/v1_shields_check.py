"""Verify that Brave (V1) did not block trackers: compare, per store, ERR_BLOCKED_BY_CLIENT failures and
known-tracker library loads in V1 (Brave, Shields-off profile) vs A2 (Chromium, emulated GPC).
Also checks the native GPC signal in V1 (Sec-GPC header on requests; navigator.globalPrivacyControl in frames/workers).
Writes validation/v1_shields_check.json."""
import glob, gzip, json, os, re, collections
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, '..', 'raw')
LIBS = re.compile(r'connect\.facebook\.net/.+/fbevents\.js|analytics\.tiktok\.com/i18n/pixel/|googletagmanager\.com/(gtag/js|gtm\.js)|s\.pinimg\.com/ct/core\.js|sc-static\.net/scevent\.min\.js|bat\.bing\.com/bat\.js|static\.klaviyo\.com/onsite/js/')
out = collections.OrderedDict()
v1 = sorted(glob.glob(os.path.join(RAW, '*__V1.json.gz')))
rows = []
for fn in v1:
    sid = os.path.basename(fn).split('__')[0]
    a2 = os.path.join(RAW, f'{sid}__A2.json.gz')
    if not os.path.exists(a2):
        continue
    r1 = json.load(gzip.open(fn, 'rt')); r2 = json.load(gzip.open(a2, 'rt'))
    def stats(r):
        rq = r.get('requests') or []
        return dict(n=len(rq), blocked_by_client=sum(1 for x in rq if 'ERR_BLOCKED_BY_CLIENT' in (x.get('fail') or '')),
                    tracker_libs_ok=sum(1 for x in rq if LIBS.search(x.get('url') or '') and (x.get('st') or 0) in range(200, 400)),
                    sec_gpc=sum(1 for x in rq if str(x.get('gpc_hdr')) == '1'), with_hdr_info=sum(1 for x in rq if 'gpc_hdr' in x),
                    frames_gpc_true=sum(1 for f in r.get('frames_gpc') or [] if f.get('g') is True), frames=len(r.get('frames_gpc') or []),
                    workers_gpc_true=sum(1 for w in r.get('workers_gpc') or [] if (w.get('val') or {}).get('gpc') == 'true'),
                    workers=len(r.get('workers_gpc') or []), status=r.get('goto_status'))
    rows.append(dict(store_id=sid, v1=stats(r1), a2=stats(r2), browser_version_v1=r1.get('browser_version')))
out['stores_compared'] = len(rows)
out['v1_loads_with_any_ERR_BLOCKED_BY_CLIENT'] = sum(1 for x in rows if x['v1']['blocked_by_client'] > 0)
out['v1_total_ERR_BLOCKED_BY_CLIENT'] = sum(x['v1']['blocked_by_client'] for x in rows)
out['a2_total_ERR_BLOCKED_BY_CLIENT'] = sum(x['a2']['blocked_by_client'] for x in rows)
out['stores_with_tracker_library_loaded_v1'] = sum(1 for x in rows if x['v1']['tracker_libs_ok'] > 0)
out['stores_with_tracker_library_loaded_a2'] = sum(1 for x in rows if x['a2']['tracker_libs_ok'] > 0)
out['tracker_library_loads_v1'] = sum(x['v1']['tracker_libs_ok'] for x in rows)
out['tracker_library_loads_a2'] = sum(x['a2']['tracker_libs_ok'] for x in rows)
out['v1_requests_with_header_info'] = sum(x['v1']['with_hdr_info'] for x in rows)
out['v1_requests_with_sec_gpc_1'] = sum(x['v1']['sec_gpc'] for x in rows)
out['v1_frames_gpc_true'] = f"{sum(x['v1']['frames_gpc_true'] for x in rows)}/{sum(x['v1']['frames'] for x in rows)}"
out['v1_workers_gpc_true'] = f"{sum(x['v1']['workers_gpc_true'] for x in rows)}/{sum(x['v1']['workers'] for x in rows)}"
out['browser_versions_v1'] = dict(collections.Counter(x['browser_version_v1'] for x in rows))
out['per_store'] = rows
json.dump(out, open(os.path.join(HERE, 'v1_shields_check.json'), 'w'), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != 'per_store'}, indent=1))
