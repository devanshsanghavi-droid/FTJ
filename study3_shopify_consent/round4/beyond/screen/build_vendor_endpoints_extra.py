"""Builds round4/beyond/vendor_endpoints_extra.json (additions only; crawl/vendor_endpoints.json is read, never written).
Usage: python build_vendor_endpoints_extra.py ../../../crawl/vendor_endpoints.json ../vendor_endpoints_extra.json"""
import json, re, sys
ORIG = sys.argv[1]; OUT = sys.argv[2]
orig = json.load(open(ORIG))

def V(vendor, name, cls, ad, host, path=None, beacon=None, lib=None, color=None, note=None):
    d = dict(vendor=vendor, display_name=name, vendor_class=cls, is_advertising=ad, study2_major_platform=False,
             figure_color_group=color, host_regex=host, path_regex=path, beacon_path_regex=beacon or [], library_path_regex=lib or [])
    if note:
        d['note'] = note
    return d

vendors = [
    # --- programmatic / publisher ad tech common outside e-commerce (not in the Study 2/3 map) ---
    V('xandr', 'Microsoft Xandr (AppNexus)', 'advertising', True, r'(^|\.)(adnxs\.com|adnxs-simple\.com)$', color='Reddit/other'),
    V('pubmatic', 'PubMatic', 'advertising', True, r'(^|\.)(pubmatic\.com)$', color='Reddit/other'),
    V('magnite', 'Magnite (Rubicon Project)', 'advertising', True, r'(^|\.)(rubiconproject\.com)$', color='Reddit/other'),
    V('openx', 'OpenX', 'advertising', True, r'(^|\.)(openx\.net)$', color='Reddit/other'),
    V('index_exchange', 'Index Exchange', 'advertising', True, r'(^|\.)(casalemedia\.com|indexww\.com)$', color='Reddit/other'),
    V('sovrn', 'Sovrn', 'advertising', True, r'(^|\.)(lijit\.com|sovrn\.com)$', color='Reddit/other'),
    V('teads', 'Teads', 'advertising', True, r'(^|\.)(teads\.tv|teads\.com)$', color='Reddit/other'),
    V('equativ', 'Equativ (Smart AdServer)', 'advertising', True, r'(^|\.)(smartadserver\.com|equativ\.com)$', color='Reddit/other'),
    V('adform', 'Adform', 'advertising', True, r'(^|\.)(adform\.net|adformdsp\.net|seadform\.net)$', color='Reddit/other'),
    V('triplelift', 'TripleLift', 'advertising', True, r'(^|\.)(3lift\.com)$', color='Reddit/other'),
    V('sharethrough', 'Sharethrough', 'advertising', True, r'(^|\.)(sharethrough\.com)$', color='Reddit/other'),
    V('media_net', 'Media.net', 'advertising', True, r'(^|\.)(media\.net)$', color='Reddit/other'),
    V('bidswitch', 'BidSwitch', 'advertising', True, r'(^|\.)(bidswitch\.net)$', color='Reddit/other'),
    V('gumgum', 'GumGum', 'advertising', True, r'(^|\.)(gumgum\.com)$', color='Reddit/other'),
    V('id5', 'ID5', 'advertising', True, r'(^|\.)(id5-sync\.com)$', color='Reddit/other', note='identity resolution for advertising'),
    V('lotame', 'Lotame', 'advertising', True, r'(^|\.)(crwdcntrl\.net)$', color='Reddit/other', note='data management platform'),
    V('permutive', 'Permutive', 'advertising', True, r'(^|\.)(permutive\.com|permutive\.app)$', color='Reddit/other', note='publisher audience platform'),
    V('33across', '33Across', 'advertising', True, r'(^|\.)(33across\.com|tynt\.com)$', color='Reddit/other'),
    V('vk_ads', 'VK Ads / Top@Mail.ru', 'advertising', True, r'(^|\.)(top-fwz1\.mail\.ru|ad\.mail\.ru)$|^vk\.com$', path=None, color='Reddit/other',
      note='vk.com is matched for the retargeting pixel paths only if the crawler adds a path filter; host-only match is conservative'),
    # --- B2B de-anonymisation / intent data (frequent on SaaS sites in the Jamstack stratum) ---
    V('demandbase', 'Demandbase', 'advertising', True, r'(^|\.)(company-target\.com|demandbase\.com)$', color='Reddit/other'),
    V('sixsense', '6sense', 'advertising', True, r'(^|\.)(6sc\.co|6sense\.com)$', color='Reddit/other'),
    V('zoominfo', 'ZoomInfo WebSights', 'advertising', True, r'(^|\.)(ws\.zoominfo\.com|zoominfo\.com)$', color='Reddit/other'),
    V('hubspot_ads', 'HubSpot ads pixel', 'advertising', True, r'(^|\.)(hsadspixel\.net)$', color='Reddit/other'),
    V('hubspot', 'HubSpot analytics and forms', 'marketing_analytics', False,
      r'(^|\.)(hs-analytics\.net|hs-scripts\.com|hscollectedforms\.net|hs-banner\.com|hsforms\.com|hsforms\.net|track\.hubspot\.com|hubspot\.com)$'),
    V('marketo', 'Adobe Marketo Munchkin', 'marketing_analytics', False, r'(^|\.)(marketo\.net|mktoresp\.com|mktoutil\.com)$'),
    V('pardot', 'Salesforce Pardot / Account Engagement', 'marketing_analytics', False, r'(^|\.)(pardot\.com)$'),
    V('leadfeeder', 'Dealfront / Leadfeeder', 'marketing_analytics', False, r'(^|\.)(lfeeder\.com|leadfeeder\.com)$'),
    # --- analytics / audience measurement ---
    V('comscore', 'Comscore', 'analytics', False, r'(^|\.)(scorecardresearch\.com)$'),
    V('chartbeat', 'Chartbeat', 'analytics', False, r'(^|\.)(chartbeat\.com|chartbeat\.net)$'),
    V('parsely', 'Parse.ly', 'analytics', False, r'(^|\.)(parsely\.com|parse\.ly)$'),
    V('piwik_pro', 'Piwik PRO', 'analytics', False, r'(^|\.)(piwik\.pro)$'),
    V('matomo_cloud', 'Matomo Cloud', 'analytics', False, r'(^|\.)(matomo\.cloud)$'),
    V('cloudflare_web_analytics', 'Cloudflare Web Analytics', 'analytics', False, r'(^|\.)(cloudflareinsights\.com)$',
      note='cookieless beacon; common on Cloudflare (and so Zaraz) sites; not a Zaraz tool'),
    # --- server-side tagging hosts (third-party-hosted sGTM / tag gateways) ---
    V('stape', 'Stape (hosted server-side GTM)', 'tag_gateway_host', False, r'(^|\.)(stape\.io|stape\.net|stape\.eu|stape\.dev)$',
      note='requests reach a server container that may forward to any vendor server-side (invisible to the browser)'),
    V('taggrs', 'TAGGRS (hosted server-side GTM)', 'tag_gateway_host', False, r'(^|\.)(taggrs\.io)$'),
    V('addingwell', 'Addingwell (hosted server-side GTM)', 'tag_gateway_host', False, r'(^|\.)(addingwell\.com|addingwell\.io)$'),
    V('jentis', 'JENTIS (server-side tag manager)', 'tag_gateway_host', False, r'(^|\.)(jentis\.com|jentis\.io)$'),
    # --- platform first-party analytics and infrastructure ---
    V('wix_platform_bi', 'Wix platform BI / analytics', 'platform_first_party', False, r'^frog\.wix\.com$',
      note='Wix built-in logging and site analytics; not an ad vendor'),
    V('partytown_lib', 'Partytown library from a public CDN', 'library_infra', False, r'(^|\.)(cdn\.jsdelivr\.net|unpkg\.com)$',
      path=r'partytown', lib=[r'partytown']),
]

# overlap check against the original map (first match wins; originals are listed first when merged)
orig_rx = [re.compile(v['host_regex']) for v in orig['vendors']]
samples = {'xandr': 'ib.adnxs.com', 'pubmatic': 'ads.pubmatic.com', 'magnite': 'fastlane.rubiconproject.com', 'openx': 'u.openx.net',
           'index_exchange': 'htlb.casalemedia.com', 'sovrn': 'ap.lijit.com', 'teads': 'a.teads.tv', 'equativ': 'ww.smartadserver.com',
           'adform': 'track.adform.net', 'triplelift': 'eb2.3lift.com', 'sharethrough': 'btlr.sharethrough.com', 'media_net': 'contextual.media.net',
           'bidswitch': 'x.bidswitch.net', 'gumgum': 'g2.gumgum.com', 'id5': 'id5-sync.com', 'lotame': 'bcp.crwdcntrl.net', 'permutive': 'api.permutive.com',
           '33across': 'lexicon.33across.com', 'vk_ads': 'top-fwz1.mail.ru', 'demandbase': 'tag.demandbase.com', 'sixsense': 'j.6sc.co',
           'zoominfo': 'ws.zoominfo.com', 'hubspot_ads': 'x.hsadspixel.net', 'hubspot': 'track.hubspot.com', 'marketo': 'munchkin.marketo.net',
           'pardot': 'pi.pardot.com', 'leadfeeder': 'sc.lfeeder.com', 'comscore': 'sb.scorecardresearch.com', 'chartbeat': 'ping.chartbeat.net',
           'parsely': 'srv.pixel.parsely.com', 'piwik_pro': 'x.containers.piwik.pro', 'matomo_cloud': 'x.matomo.cloud',
           'cloudflare_web_analytics': 'static.cloudflareinsights.com', 'stape': 'x.stape.io', 'taggrs': 'x.taggrs.io', 'addingwell': 'x.addingwell.com',
           'jentis': 'x.jentis.com', 'wix_platform_bi': 'frog.wix.com', 'partytown_lib': 'cdn.jsdelivr.net'}
problems = []
for v in vendors:
    rx = re.compile(v['host_regex'])
    s = samples.get(v['vendor'])
    if s and not rx.search(s):
        problems.append('no self-match %s %s' % (v['vendor'], s))
    if s and any(o.search(s) for o in orig_rx):
        problems.append('shadowed by original: %s %s' % (v['vendor'], s))
if problems:
    print('\n'.join(problems)); sys.exit(1)

GA = 'google_analytics'; GADS = 'google_ads'; GTM = 'google_tagmanager'
first_party_rules = [
    # ---------------- first-party tag gateways / server-side GTM (Google) ----------------
    dict(id='G1', architecture='gateway', scope='same_site_or_known_gateway_host', method='GET', path_regex=r'/gtm\.js$', query_regex=r'(^|&)id=GTM-[A-Z0-9]+',
         attributes_to=GTM, kind='library', evidence='strong', note='Google Tag Manager container served from the site (sGTM web-container client or Google tag gateway)'),
    dict(id='G2', architecture='gateway', scope='same_site_or_known_gateway_host', method='GET', path_regex=r'/gtag/js$', query_regex=r'(^|&)id=(G|AW|DC|GT)-[A-Z0-9]+',
         attributes_to=GTM, kind='library', evidence='strong', note='Google tag (gtag.js) served first-party'),
    dict(id='G3', architecture='gateway', scope='same_site_or_known_gateway_host', method='GET', path_regex=r'\.js$', query_regex=r'(aWQ9R1RNL|aWQ9Ry0|aWQ9QVct)',
         attributes_to=GTM, kind='library', evidence='moderate', note='custom loader: base64 of "id=GTM-", "id=G-" or "id=AW-" in the query (e.g. Stape custom loader)'),
    dict(id='G4', architecture='gateway', scope='same_site_or_known_gateway_host', method='GET|POST', path_regex=r'(^|/)g/collect$', query_regex=r'(^|&)v=2(&|$).*(^|&)tid=G-|(^|&)tid=G-.*(^|&)v=2(&|$)',
         attributes_to=GA, kind='beacon', evidence='strong', note='GA4 hit to a first-party collection path; may be forwarded server-side to GA4 and other vendors'),
    dict(id='G5', architecture='gateway', scope='same_site_or_known_gateway_host', method='GET|POST', path_regex=None, query_or_body_regex=r'(^|&)v=2&.*tid=G-[A-Z0-9]+.*(^|&)en=',
         attributes_to=GA, kind='beacon', evidence='strong', note='GA4 wire format on any first-party path (sGTM GA4 client with a custom path)'),
    dict(id='G6', architecture='gateway', scope='same_site_or_known_gateway_host', method='GET|POST',
         path_regex=r'(^|/)(ccm/collect|pagead/(1p-)?conversion|pagead/viewthroughconversion|pagead/1p-user-list|pagead/landing|rmkt/collect)(/|$)',
         attributes_to=GADS, kind='beacon', evidence='strong', note='Google Ads conversion / remarketing / ccm hit on a first-party path'),
    dict(id='G7', architecture='gateway', scope='same_site_or_known_gateway_host', method='GET|POST', path_regex=r'(^|/)(j/)?collect$', query_regex=r'(^|&)v=1&.*tid=UA-',
         attributes_to=GA, kind='beacon', evidence='strong', note='legacy Universal Analytics wire format'),
    dict(id='G8', architecture='gateway', scope='same_site_or_known_gateway_host', method='GET|POST', path_regex=None, query_regex=r'(^|&)gtm=4[0-9a-z]+.*(^|&)(gcs|gcd)=|(^|&)(gcs|gcd)=.*(^|&)gtm=4[0-9a-z]+',
         attributes_to='google_tag_unknown', kind='beacon', evidence='moderate', note='Google tag hit parameters (gtm= container hash plus consent parameters) on an unrecognised path'),
    dict(id='G9', architecture='gateway', scope='same_site_or_known_gateway_host', method='POST', path_regex=r'(^|/)data/?$', body_regex=r'"?event_name"?\s*[:=]',
         attributes_to='sgtm_data_client', kind='beacon', evidence='moderate', note='server-side GTM "Data client" (e.g. Stape Data Tag) event stream; vendor fan-out is server-side'),
    dict(id='G10', architecture='gateway', scope='same_site_subdomain', host_regex=r'^capig\.', method='GET|POST', path_regex=None,
         attributes_to='meta', kind='beacon', evidence='moderate', note='Meta Conversions API Gateway on a first-party subdomain (conventional "capig." label)'),
    dict(id='G11', architecture='gateway', scope='same_site_or_known_gateway_host', method='GET|POST', path_regex=r'(^|/)tr/?$', query_regex=r'(^|&)id=\d{6,}.*(^|&)ev=|(^|&)ev=.*(^|&)id=\d{6,}',
         attributes_to='meta', kind='beacon', evidence='strong', note='Meta pixel wire format proxied through the site'),
    dict(id='G12', architecture='gateway', scope='same_site_or_known_gateway_host', method='POST', path_regex=r'(^|/)api/v2/pixel(/|$)',
         attributes_to='tiktok', kind='beacon', evidence='strong', note='TikTok pixel wire format proxied through the site'),
    dict(id='G13', architecture='gateway', scope='same_site_or_known_gateway_host', method='any', response_set_cookie_names=r'^(FPID|FPLC|FPAU|FPGCLAW|FPGCLDC|FPGCLGB|FPGSID|_ga|_ga_[A-Z0-9]+|_gcl_au|_fbp|_fbc|_ttp|stape|_dc_gtm_.*)$',
         attributes_to='server_set_identifier', kind='cookie', evidence='strong',
         note='identifier cookie set by a Set-Cookie header on a first-party tag or collect response (sGTM sets FPID/FPLC server-side, HttpOnly); record names only'),
    # ---------------- Cloudflare Zaraz ----------------
    dict(id='Z1', architecture='zaraz', scope='same_site', method='GET', path_regex=r'^/cdn-cgi/zaraz/(i|s)\.js$', attributes_to='zaraz', kind='library', evidence='strong',
         note='Zaraz loader (default path; the path is configurable in Zaraz settings)'),
    dict(id='Z2', architecture='zaraz', scope='same_site', method='POST', path_regex=r'^/cdn-cgi/zaraz/t$', attributes_to='zaraz', kind='beacon', evidence='strong',
         note='Zaraz track call: the event reaches Cloudflare, which runs server-side tools for purposes with consent (or tools with no purpose). Forwarding itself is invisible.'),
    dict(id='Z3', architecture='zaraz', scope='same_site', method='GET|POST', path_regex=None, body_regex=r'zarazData|"zaraz', attributes_to='zaraz', kind='beacon', evidence='moderate',
         note='Zaraz on a custom endpoint path (settings: custom URLs for Zaraz scripts)'),
    # ---------------- Partytown ----------------
    dict(id='P1', architecture='partytown', scope='any', method='GET', path_regex=r'(~partytown|/partytown)/(debug/)?partytown(-atomics|-sw|-ww-atomics|-ww-sw|-media)?\.js$',
         attributes_to='partytown_lib', kind='library', evidence='strong', note='Partytown runtime (main-thread snippet, worker, service worker)'),
    dict(id='P2', architecture='partytown', scope='same_site_or_proxy', method='GET|POST', path_regex=r'(proxytown|~partytown/proxy|partytown-proxy|/proxy)(/|$|\?)',
         query_regex=r'(^|&)(url|u|target)=https?%3A%2F%2F', attributes_to='decode_inner_url', kind='inherit', evidence='strong',
         note='resolveUrl() reverse proxy: URL-decode the inner URL and classify it with the vendor map; attribute the request to that vendor'),
    # ---------------- Wix ----------------
    dict(id='W1', architecture='wix', scope='frame_host', frame_host_regex=r'(^|\.)filesusr\.com$', attributes_to='wix_html_embed_frame', kind='context', evidence='strong',
         note='requests issued inside Wix "Embed HTML" iframes (user code on the filesusr.com sandbox origin); the banner does not govern them'),
    dict(id='W2', architecture='wix', scope='frame_host', frame_host_regex=r'(^|\.)(wixapps\.net|wix\.com)$', attributes_to='wix_app_frame', kind='context', evidence='moderate',
         note='third-party app iframes; apps must read the consent policy themselves (Wix app docs)'),
    # ---------------- BigCommerce ----------------
    dict(id='B1', architecture='bigcommerce', scope='same_site', method='POST', path_regex=r'^/api/storefront/consent$', attributes_to='bigcommerce_consent', kind='consent_signal', evidence='strong',
         note='body {"allow":[...],"deny":[...]}: 2 functional, 3 analytics, 4 targeting (as used by data-bc-cookie-consent); documented storefront consent endpoint'),
]

decoders = {
    'google_gcs': dict(param='gcs', regex=r'^G1([01-])([01-])$', fields=['ad_storage', 'analytics_storage'], values={'1': 'granted', '0': 'denied', '-': 'not_set'},
                       source='Google consent mode documentation (gcs values G100/G110/G101/G111)'),
    'google_gcd': dict(param='gcd', positions={'ad_storage': 2, 'analytics_storage': 4, 'ad_user_data': 6, 'ad_personalization': 8},
                       letters={'l': 'not_set', 'p': 'denied_default', 'q': 'denied_default_and_update', 't': 'granted_default', 'r': 'granted_by_update_after_denied_default',
                                'm': 'denied_by_update', 'n': 'granted_by_update', 'u': 'denied_by_update_after_granted_default', 'v': 'granted_default_and_update'},
                       effective_granted=list('trnv'), effective_denied=list('pqmu'),
                       source='practitioner decoding of the undocumented gcd parameter; verify on calibration pages before relying on it'),
    'google_other': dict(params=['npa', 'dma', 'dma_cps', 'pscdl', 'gcu', 'gcut'], note='npa=1 non-personalised ads; dma = EEA DMA flag; record raw values'),
    'zaraz_consent': dict(cookie='cf_consent', note='name configurable; value maps purpose IDs to true/false (missing = no choice yet). Read zaraz.consent.getAll() in the page as the primary signal.'),
    'wix_consent_policy': dict(api='window.consentPolicyManager.getCurrentConsentPolicy() -> {defaultPolicy, policy:{essential,functional,analytics,advertising,dataToThirdParty}}',
                               cookie='consent-policy', cookie_note='URL-encoded JSON; short keys expected (ess/func/anl/adv/dt3); calibrate on first pilot loads',
                               static='viewer model "siteConsentPolicy" = site default for this visitor region (screening)'),
    'bigcommerce_consent': dict(api='window.consentManagerStoreConfig()', dom='script[type="text/plain"][data-bc-cookie-consent] = scripts held back per category',
                                categories={'1': 'essential', '2': 'functional', '3': 'analytics', '4': 'targeting'},
                                cookie='record all first-party cookie names matching /consent/i at each checkpoint; name to be confirmed on calibration loads'),
    'tcf_gpp': dict(api=['__tcfapi("getTCData")', '__gpp("ping")'], note='as in Part A probes'),
}

runtime = {
    'partytown': dict(dom_pending='script[type="text/partytown"]', dom_executed='script[type="text/partytown-x"]',
                      worker_url_regex=r'partytown-ww-(atomics|sw)|blob:', service_worker_regex=r'partytown-sw\.js',
                      config='window.partytown (forward list, lib path, resolveUrl present?)',
                      attribution='requests from the Partytown web-worker target (CDP auto-attach session type "worker") are "worker-context"; the existing Part A worker attribution applies'),
    'zaraz': dict(globals=['zaraz', 'zarazData'], api='zaraz.consent.APIReady, zaraz.consent.getAll(), zaraz.consent.purposes', events=['zarazConsentAPIReady', 'zarazConsentChoicesUpdated'],
                  note='tools with no purpose skip consent by default; events blocked by consent are queued (zaraz.consent.sendQueuedEvents)'),
    'wix': dict(globals=['consentPolicyManager', 'wixTagManager'], note='wixTagManager.getConfig().gdprEnforcedGeo; Wix site code (Velo) and some apps run in a platform worker or iframes'),
    'bigcommerce': dict(globals=['consentManagerStoreConfig', 'BCData'], note='count text/plain data-bc-cookie-consent scripts before and after Decline'),
}

out = dict(_meta=dict(
    description='ADDITIONS to crawl/vendor_endpoints.json for the beyond-Shopify pilot (Part B2). The original file is not modified.',
    built='2026-09-27', built_by='round4/beyond (screening agent); regexes are Python syntax like the original',
    merge_rule='Append `vendors` AFTER the original list (original entries keep first-match precedence; build_extra.py checked that none of the new host regexes is shadowed by, or shadows, an original entry on sample hosts). `first_party_rules` are evaluated only for requests the host map does not match, in the order listed.',
    scopes={'same_site': 'request host has the same registrable domain (eTLD+1) as the top-level page',
            'same_site_or_known_gateway_host': 'same_site, or a host matched by a vendor with vendor_class tag_gateway_host (stape, taggrs, addingwell, jentis)',
            'same_site_subdomain': 'same_site and host != page host', 'same_site_or_proxy': 'any host whose path/query matches the proxy pattern',
            'frame_host': 'the frame (not the request) host matches', 'any': 'any host'},
    evidence_levels={'strong': 'wire format or path unique to the vendor', 'moderate': 'convention or partial signature; report separately', 'weak': 'not used for headline counts'},
    caveat='Server-to-server forwarding (sGTM, Zaraz server-side tools, Wix/BigCommerce conversion APIs) cannot be observed from a browser. These rules identify data leaving the browser to a first-party or gateway endpoint (a proxy observable), never receipt by a named vendor, unless the wire format itself names the vendor (e.g. tid=G-..., AW- labels, Meta id=).'),
    vendors=vendors, first_party_rules=first_party_rules, consent_signal_decoders=decoders, architecture_runtime_markers=runtime)
for r in first_party_rules:
    for k in ('path_regex', 'query_regex', 'query_or_body_regex', 'body_regex', 'host_regex', 'frame_host_regex', 'response_set_cookie_names'):
        if r.get(k):
            re.compile(r[k])
json.dump(out, open(OUT, 'w'), indent=1)
print('vendors', len(vendors), 'rules', len(first_party_rules), 'OK')
