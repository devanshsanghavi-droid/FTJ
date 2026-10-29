"""Build vendor_endpoints.json: request-URL patterns -> ad/analytics vendor.

Host table = Study 2's validated vendor table (analyze_capture.V, used on 1,408 loads), extended
with a few vendors seen in Study 2 traffic but not in that table. Per-vendor beacon/library path
patterns and the "observed" examples are taken from endpoint_evidence/observed_vendor_endpoints.csv
and observed_other_hosts.csv (Study 2 evidence, counts = number of loads). Shopify app-pixel
apiClientIds come from static_mechanism/wpm_survey/pixels.csv (vendor confirmed from the pixel's
configuration keys, e.g. pixelCode, redditPixelId, tagID, partnerId).
Matching rule for the crawler: lower-case host; first entry whose host_regex matches AND (path_regex
is null OR matches the path) wins; entries are ordered so that more specific ones come first.
"""
import csv, json, os, sys, re, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '../../study2_creator_links/capture')))
import analyze_capture as A

CLASS = {'ad': 'advertising', 'analytics': 'analytics', 'tag_manager': 'tag_manager', 'marketing': 'marketing_messaging',
         'affiliate': 'affiliate', 'attribution': 'attribution', 'ad_verification': 'ad_verification'}
DISPLAY = {'tiktok': 'TikTok', 'meta': 'Meta (Facebook/Instagram)', 'google_analytics': 'Google Analytics 4 / UA', 'google_ads': 'Google Ads / DoubleClick / Floodlight',
    'google_tagmanager': 'Google Tag Manager / gtag loader', 'google_merchant_center': 'Google Merchant Center analytics', 'snap': 'Snap', 'pinterest': 'Pinterest',
    'reddit': 'Reddit', 'x_twitter': 'X (Twitter)', 'linkedin': 'LinkedIn', 'microsoft_uet': 'Microsoft Advertising UET (Bing)', 'microsoft_clarity': 'Microsoft Clarity',
    'criteo': 'Criteo', 'applovin': 'AppLovin (Axon)', 'amazon_ads': 'Amazon Ads', 'tvscientific': 'tvScientific', 'klaviyo': 'Klaviyo', 'attentive': 'Attentive'}
FIG = {'google_ads': 'Google', 'google_analytics': 'Google', 'google_tagmanager': 'Google', 'google_merchant_center': 'Google', 'tiktok': 'TikTok', 'meta': 'Meta',
       'pinterest': 'Pinterest', 'snap': 'Snap', 'microsoft_uet': 'Microsoft', 'microsoft_clarity': 'Microsoft', 'reddit': 'Reddit/other'}
# beacon vs library path patterns (regex on path), grounded in observed endpoints
PATHS = {
 'tiktok': dict(beacon=[r'^/api/v2/(shopify_pixel|pixel(/act|/batch)?|performance.*|monitor.*)', r'^/ipv6/enrich_ipv6'], library=[r'^/i18n/pixel/']),
 'meta': dict(beacon=[r'^/tr/?$', r'^/tr/'], library=[r'^/en_US/fbevents\.js', r'^/signals/(config|plugins)/', r'^/[a-z]{2}_[A-Z]{2}/(fbevents|sdk)\.js']),
 'google_ads': dict(beacon=[r'^/ccm/(collect|s)', r'^/rmkt/collect', r'^/pagead/(viewthroughconversion|1p-user-list|1p-conversion|conversion|landing|form-data)', r'^/activity(i)?[;/]', r'^/ddm/'], library=[r'^/pagead/(conversion_async|js/)']),
 'google_analytics': dict(beacon=[r'^/g/(collect|s)', r'^/j/collect', r'^/collect'], library=[r'^/analytics\.js', r'^/plugins/']),
 'google_tagmanager': dict(beacon=[], library=[r'^/(gtag/js|gtm\.js|gtag/destination)']),
 'google_merchant_center': dict(beacon=[r'^/mc/collect'], library=[]),
 'pinterest': dict(beacon=[r'^/v3/', r'^/user/', r'^/ct\.html'], library=[r'^/ct/(core\.js|lib)', r'^/js/pinit']),
 'snap': dict(beacon=[r'^/p$', r'^/cm/', r'^/config/'], library=[r'^/scevent\.min\.js', r'^/shopify/']),
 'microsoft_uet': dict(beacon=[r'^/action(p)?/', r'^/p/(action|conversions|insights)'], library=[r'^/bat\.js']),
 'microsoft_clarity': dict(beacon=[r'^/c\.gif', r'^/collect', r'^/tag/shopify'], library=[r'^/\d+\.\d+\.\d+/clarity\.js', r'^/tag/']),
 'reddit': dict(beacon=[r'^/rp(\.gif)?', r'^/pixels/'], library=[r'^/ads/pixel\.js']),
 'x_twitter': dict(beacon=[r'^/i/adsct', r'^/1/i/adsct', r'^/1/i'], library=[r'^/(uwt|oct)\.js']),
 'linkedin': dict(beacon=[r'^/collect', r'^/wa', r'^/px/', r'^/(db_sync|setuid)'], library=[r'^/li\.lms-analytics/']),
 'criteo': dict(beacon=[r'^/event', r'^/rm', r'^/sync', r'^/syncframe', r'^/Delivery/'], library=[r'^/js/ld/']),
 'applovin': dict(beacon=[r'^/v1/(s|pixel|gcm)'], library=[r'^/p/', r'^/pixel\.js']),
 'amazon_ads': dict(beacon=[r'^/(ecm3|iu3|iui3|v3/pr)', r'^/aat/allowlist'], library=[r'^/aat/amzn(-consent)?\.js']),
 'tvscientific': dict(beacon=[r'^/t\.png'], library=[]),
 'klaviyo': dict(beacon=[r'^/onsite/track-analytics', r'^/client/(events|profiles|subscriptions)', r'^/api/(track|identify)', r'^/forms/api', r'^/atlas/'], library=[r'^/onsite/js/']),
 'attentive': dict(beacon=[r'^/ct-ev', r'^/d$', r'^/creative-interactions', r'^/e/'], library=[r'^/(tag|growth-tag-assets|attentive)/']),
}
# Shopify app pixels (apiClientId) whose vendor was confirmed from configuration keys (wpm_survey/pixels.csv)
APP = {'tiktok': ['4383523'], 'meta': ['2329312'], 'google_ads': ['1780363'], 'pinterest': ['3009811'], 'snap': ['2556259'],
       'reddit': ['304258285569'], 'linkedin': ['5829751'], 'applovin': ['256560922625'], 'tvscientific': ['92361228289'], 'klaviyo': ['123074']}
EXTRA = [  # vendors seen in Study 2 traffic but not in Study 2's vendor table
 ('postscript', 'marketing', r'(^|\.)(postscript\.io)$', None, 'Postscript (SMS marketing)'),
 ('shopify_platform', 'shopify_first_party', r'(^|\.)(shopifysvc\.com|shop\.app)$', None, 'Shopify first-party telemetry / Shop Pay (not a third-party ad vendor)'),
]
def load_obs():
    obs = collections.defaultdict(list)
    with open(os.path.join(HERE, 'endpoint_evidence/observed_vendor_endpoints.csv')) as f:
        for r in csv.DictReader(f):
            obs[r['vendor']].append((int(r['n_loads']), r['host'], r['path_prefix'], r['resource_type']))
    with open(os.path.join(HERE, 'endpoint_evidence/observed_other_hosts.csv')) as f:
        for r in csv.DictReader(f):
            h = r['host']
            v = 'postscript' if 'postscript' in h else ('shopify_platform' if re.search(r'shopifysvc\.com$|^shop\.app$', h) else None)
            if v: obs[v].append((int(r['n_loads']), h, r['path_prefix'], ''))
    return obs
obs = load_obs()
px = list(csv.DictReader(open(os.path.join(HERE, 'static_mechanism/wpm_survey/pixels.csv'))))
def app_info(ids):
    rows = [r for r in px if r['apiClientId'] in ids]
    return dict(apiClientIds=ids, n_stores_in_static_survey=len({r['store'] for r in rows}),
                runtimeContext_observed=sorted({r['runtimeContext'] for r in rows}), privacyPurposes_observed=sorted({r['privacyPurposes'] or '[] (none declared)' for r in rows}))
entries = []
seen = set()
for name, grp, hre, pre in A.V:
    e = dict(vendor=name, display_name=DISPLAY.get(name, name), vendor_class=CLASS.get(grp, grp), is_advertising=(grp == 'ad'),
             study2_major_platform=name in A.MAJOR, figure_color_group=FIG.get(name, 'Reddit/other' if grp == 'ad' else None),
             host_regex=hre, path_regex=pre)
    if name not in seen:
        p = PATHS.get(name, {})
        e['beacon_path_regex'] = p.get('beacon', [])
        e['library_path_regex'] = p.get('library', [])
        if name in APP: e['shopify_app_pixel'] = app_info(APP[name])
        if name == 'google_ads': e['shopify_app_pixel']['note'] = 'Google & YouTube app (one pixel sends Google Ads, GA4 and Merchant Center tags); declares no privacy purposes, so the WPM never withholds it; consent is signalled only through Consent Mode parameters (gcs/gcd/npa).'
        if name == 'tiktok': e['worker_marker'] = 'library analytics.tiktok.com/i18n/pixel/shopify.js requested with Playwright resource type "other" = loaded inside the Shopify STRICT web worker (101 Study 2 loads); resource type "script" = classic main-thread pixel.'
        e['observed_study2_top_endpoints'] = [dict(host=h, path_prefix=pp, resource_types=rt, n_loads=n) for n, h, pp, rt in sorted(obs.get(name, []), reverse=True)[:6]]
    seen.add(name)
    entries.append(e)
for name, grp, hre, pre, disp in EXTRA:
    entries.append(dict(vendor=name, display_name=disp, vendor_class=CLASS.get(grp, grp), is_advertising=False, study2_major_platform=False,
                        figure_color_group=None, host_regex=hre, path_regex=pre, beacon_path_regex=[], library_path_regex=[],
                        observed_study2_top_endpoints=[dict(host=h, path_prefix=pp, n_loads=n) for n, h, pp, rt in sorted(obs.get(name, []), reverse=True)[:6]]))
# Shopify web-pixel sandbox and loader URLs (first party, on the storefront's own origin)
shopify_wpm = dict(
  manager_bundle=r'^https://[^/]+/cdn/wpm/b[0-9a-z]+[ml]\.js$',
  strict_worker_bootstrap=r'^https://[^/]+/(web-pixels|wpm)@[0-9a-z]+/web-pixel-(?P<pixel_id>[^@/]+)@(?P<ver>[^/]+)/sandbox/worker\.(modern|legacy)\.js',
  strict_worker_pixel_code=r'^https://[^/]+/(web-pixels|wpm)/strict/app/web-pixel-(?P<pixel_id>[^@/]+)@(?P<ver>[^/.]+)\.js',
  lax_iframe_sandbox=r'^https://[^/]+/(web-pixels|wpm)@[0-9a-z]+/(?P<type>app|custom)/web-pixel-(?P<pixel_id>[^@/]+)@(?P<ver>[^/]+)/sandbox/(modern|legacy)/',
  open_main_thread_pixel=r'^https://[^/]+/(web-pixels|wpm)@[0-9a-z]+/(?P<type>app|custom)/web-pixel-(?P<pixel_id>[^@/]+)@(?P<ver>[^~/]+)~2/pixel\.(modern|legacy)\.js',
  storefront_monorail=r'^https://[^/]+/\.well-known/shopify/monorail/',
  notes='Observed on c005.store.example in Study 2 evidence and in the WPM bundle (hash c8540278we853e1abpb62b2c4amde256306, 2026-09-25). Requests made by a STRICT pixel (e.g. analytics.tiktok.com/i18n/pixel/shopify.js and /api/v2/shopify_pixel) are issued from a dedicated web worker; Playwright reports them with resource type "other"/"fetch" and, in Study 2 capture.js, frame "main" (request.frame() did not throw). Attribute origin by (i) page.on("worker") URLs, (ii) CDP Network.requestWillBeSent initiator / Target info, or (iii) the fact that the vendor library was requested with resource type "other" right after the matching worker bootstrap.')
out = dict(_meta=dict(
    description='Request-URL -> vendor map for Study 3 (Shopify consent). Built by build_vendor_endpoints.py from the Study 2 vendor table plus observed endpoints.',
    built='2026-09-26', matching='lower-case hostname; first entry whose host_regex (Python re.search) matches and whose path_regex (if not null) matches the URL path. beacon_path_regex/library_path_regex refine request kind; anything that is neither is counted as a beacon (Study 2 convention).',
    is_advertising='true for ad platforms, retargeting/ID networks and ad measurement (Study 2 group "ad"); false for analytics, tag managers, email/SMS marketing, affiliate, attribution and Shopify first-party.',
    figure_color_group='FIGURE_PLAN.md vendor colour group (Google, TikTok, Meta, Pinterest, Snap, Microsoft, Reddit/other); null = not an ad vendor in figures.',
    sources=['../../study2_creator_links/capture/analyze_capture.py (V table)', 'endpoint_evidence/observed_vendor_endpoints.csv', 'endpoint_evidence/observed_other_hosts.csv', 'static_mechanism/wpm_survey/pixels.csv']),
  shopify_web_pixels_urls=shopify_wpm, vendors=entries)
json.dump(out, open(os.path.join(HERE, 'vendor_endpoints.json'), 'w'), indent=1)
print('vendors:', len(entries), 'advertising:', sum(e['is_advertising'] for e in entries))
