"""Build cmp_signatures.json for the Study 3 crawler.

For each consent-management platform (CMP) seen on Shopify stores: detection signatures (script URL
regexes, JS globals, DOM selectors, consent cookies), how to click the privacy-preserving choice
(Decline/Reject selectors + text patterns), how to read what the tool *declares* blocked, and its
integration mode with Shopify's Customer Privacy API (CPAPI).

Evidence levels used in the file:
  code     = seen in the vendor's JavaScript we downloaded (static_mechanism/cmp_code/, counts in
             static_mechanism/cmp_code_scan.csv) or in live storefront HTML (static_mechanism/*.html)
  study2   = observed in Study 2 browser captures (banner button texts / selectors that matched)
  docs     = vendor or Shopify documentation (URL given)
  unverified = widely used selector/name not verified in this project; the crawler must confirm it
               (manual screenshot audit, Figure 2d / S4) before relying on it.
Integration-mode codes:
  N = Shopify's own banner (writes CPAPI by construction)
  A = CPAPI only: calls setTrackingConsent on the visitor's choice; no main-thread script blocker
  B = main-thread blocker only: blocks <script>/<iframe>/<img> (and sometimes fetch/XHR/beacon) it
      recognises, never tells Shopify -> cannot gate sandboxed web pixels
  C = both CPAPI and a main-thread blocker
  X = unknown / could not verify
Modes are *capabilities of the product*; whether a given store has the CPAPI sync switched on is a
per-store fact the crawler measures (see _meta.per_store_integration_test).
"""
import csv, json, os, collections
HERE = os.path.dirname(os.path.abspath(__file__))
scan = collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(HERE, 'static_mechanism/cmp_code_scan.csv'))):
    if r.get('bytes'):
        scan[r['cmp']].append({k: (int(r[k]) if k not in ('url',) else r[k]) for k in (
            'url', 'bytes', 'setTrackingConsent', 'customerPrivacy', 'visitorConsentCollected', 'globalPrivacyControl',
            'MutationObserver', 'type_text_plain', 'createElement_override', 'blocklist_keys')})
# Study 2 default loads (n=626) where the CMP was detected / and window.Shopify was defined
S2_ALL = {'shopify_banner': 51, 'cookiebot': 12, 'consentmo': 19, 'usercentrics': 21, 'cookiefirst': 2, 'onetrust': 74, 'pandectes': 38,
          'transcend': 8, 'osano': 13, 'trustarc': 15, 'securiti': 13, 'cookiehub': 1, 'cookiescript': 1, 'clarip': 4, 'ketch': 1,
          'consentmanager': 6, 'cookie_law_info': 1, 'fides_ethyca': 2, 'didomi': 4}
S2_SHOP = {'shopify_banner': 51, 'usercentrics': 11, 'cookiefirst': 2, 'pandectes': 38, 'osano': 5, 'onetrust': 16, 'clarip': 4,
           'consentmo': 14, 'ketch': 1, 'cookie_law_info': 1, 'consentmanager': 1, 'cookiebot': 1}

REJECT_TEXT = (r'^\s*(reject( all)?( cookies| optional cookies)?|decline( all)?( optional( cookies)?)?|deny( all)?( non[- ]essential)?|'
               r'refuse( all)?|disagree|i decline|no,? thanks|(strictly )?necessary( cookies)? only|use (only )?(strictly )?necessary( cookies)?( only)?|'
               r'only (necessary|essential|required)( cookies)?|required only|continue without (accepting|agreeing))\s*$')
NEVER_CLICK = r'accept|agree|allow|consent|got it|^ok(ay)?$|continue$|save|confirm|preferences|manage|settings|customi[sz]e|do not sell|opt[- ]?out|close|x$|×'

C = {}
C['shopify_native'] = dict(
    name="Shopify cookie banner (Customer Privacy app / Settings > Customer privacy)", integration_mode='N', mode_evidence='code+docs',
    detect=dict(script_url_regex=[r'/cdn/shopifycloud/privacy-banner/storefront-banner\.js'], globals=[],
                dom_selectors=['#shopify-pc__banner', '.shopify-pc__banner__dialog', '#shopify-pc__prefs'], cookies=['_tracking_consent'],
                evidence='code (storefront-banner.js element ids) + study2 (selector matched 51 loads)'),
    reject=dict(selectors=['#shopify-pc__banner__btn-decline', '#shopify-pc__prefs__header-decline'], text_regex=REJECT_TEXT,
                observed_texts_study2={'Decline': 20, 'No Thanks': 1, 'DECLINE': 1}, evidence='code'),
    declared_config=dict(available=False, how='No blocklist. What Shopify will allow is readable from Shopify.customerPrivacy (shouldShowBanner(), marketingAllowed() ...) and from the Server-Timing `_cmp` consent string (see _meta.shopify_consent_readout).'),
    cpapi=dict(calls_setTrackingConsent=True, when='on visitor choice', evidence='code: 10 occurrences in storefront-banner.js'),
    script_blocker=dict(present=False),
    notes='Region behaviour is set in Shopify admin; Shopify documents automated settings for EEA/UK/CH and "all processing allowed by default" elsewhere (https://shopify.dev/docs/api/customer-privacy).')
C['pandectes'] = dict(
    name='Pandectes GDPR Compliance', integration_mode='C', mode_evidence='code+docs',
    detect=dict(script_url_regex=[r'cdn\.shopify\.com/extensions/[0-9a-f-]+/gdpr-cookie-consent-\d+/assets/pandectes-(core|rules)(-latest)?\.js',
                                  r'/cdn/shop/(files|t/\d+/assets)/pandectes-(rules|consent)\.js'],
                globals=['PandectesSettings', 'PandectesRulesSettings', 'Pandectes', 'pandectesBannerSettings'],
                dom_selectors=['pandectes-cmp', '#pandectes-banner', '.pd-cookie-banner-window', '[id^="pandectes-"]'],
                cookies=['_pandectes_gdpr'], shadow_dom='open (attachShadow mode "open" in pandectes-core-latest.js; Playwright CSS pierces it)',
                evidence='code + study2 (38 loads)'),
    reject=dict(selectors=[], text_regex=REJECT_TEXT, observed_texts_study2={'DECLINE': 21, 'Decline': 2},
                notes='Button classes are generated; click by text inside the Pandectes container/shadow root. Internal action name is "deny" (code).', evidence='study2+code'),
    declared_config=dict(available=True, how='Inline JSON in page HTML: window.PandectesRulesSettings and PandectesSettings (json.JSONDecoder().raw_decode after "PandectesSettings = ").',
        paths={'blocker_active': 'PandectesSettings.blocker.isActive', 'default_blocked_bitmask': 'PandectesSettings.blocker.defaultBlocked (or PandectesRulesSettings.banner.cookiesBlockedByDefault)',
               'script_blocklist': 'PandectesSettings.blocker.patterns.blackList[<category bit>] -> list of URL substrings ("|" = alternatives)',
               'iframe_blocklist': 'PandectesSettings.blocker.patterns.iframesBlackList', 'beacon_blocklist': 'PandectesSettings.blocker.patterns.beaconsBlackList',
               'gpc_honoured_by_cmp': 'PandectesSettings.blocker.gpcIsActive', 'banner_geo': 'PandectesSettings.geolocation (*Only flags, globalVisibility)'},
        category_bits={'1': 'functionality/preferences', '2': 'performance/analytics', '4': 'targeting/marketing', '8': 'unclassified (inferred; verify)'},
        category_evidence='Store C config: googleConsentMode.adStorageCategory=4, analyticsStorageCategory=2, functionality/personalizationStorageCategory=1 (static_mechanism/store_c_pandectes_settings.json)',
        declared_blocked_rule='vendor URL matches a blackList[c] pattern AND (defaultBlocked & c) != 0 -> declared blocked before choice; after Decline all non-essential categories are declared blocked',
        example='c005.store.example: isActive=true, defaultBlocked=7, gpcIsActive=false, globalVisibility=true, blackList["4"] includes analytics.tiktok.com/i18n/pixel and connect.facebook.net'),
    cpapi=dict(calls_setTrackingConsent=True, when='on visitor choice; can also read Shopify saleOfDataAllowed() when its Shopify consent option is on',
               evidence='code: wrapper around Shopify.customerPrivacy.setTrackingConsent in pandectes-core-latest.js',
               docs=['https://help.pandectes.io/en/article/shopify-customer-privacy-api-1vv23qb/ ("When no country is selected, all Shopify cookies ... will fire before consent")']),
    script_blocker=dict(present=True, mechanism='pandectes-rules: MutationObserver + patched document.createElement, appendChild/insertBefore/replaceChild and XMLHttpRequest.send on the main thread; runs only while consent != all-allowed',
                        reaches_web_workers=False, evidence='code (no Worker/importScripts hooks)'))
C['consentmo'] = dict(
    name='Consentmo GDPR/CCPA compliance (formerly isenselabs)', integration_mode='A', mode_evidence='code+docs (blocking delegated to Shopify)',
    detect=dict(script_url_regex=[r'cdn\.shopify\.com/extensions/[0-9a-f-]+/gdpr-backpack-\d+/assets/(consentmo_cookie_consent|\d+\.consentmo|layout-[a-z-]+\.consentmo)\.js',
                                  r'gdprcdn\.b-cdn\.net/js/(gdpr_cookie_consent\.min|\d+\.consentmo)\.js', r'(^|//)(app|workers)\.consentmo\.com/'],
                globals=['isenseGDPR', 'isConsentmoCMPRegistered', 'iSenseAppSettings'],
                dom_selectors=['csm-cookie-consent', '.csm-cmp-root', '#cookie-bar', '.isense-cc-window', '#gdpr-blocking-page-overlay'],
                cookies=['cookieconsent_status', 'cookieconsent_preferences_disabled'], shadow_dom='open',
                evidence='code + study2 (19 loads; note #cookie-bar is generic and can false-positive)'),
    reject=dict(selectors=[], text_regex=REJECT_TEXT, observed_texts_study2={'NO, THANKS': 1, 'NO THANKS': 1, 'Decline': 1}, evidence='study2+code (actions "deny"/"decline")'),
    declared_config=dict(available=False, how='Per-store settings are fetched from Consentmo servers, not inline; categories in code: strict, analytics, marketing, functionality, sale_of_data. Declared-blocked = category not granted.'),
    cpapi=dict(calls_setTrackingConsent=True, when='on visitor choice', evidence='code: 4 occurrences in consentmo_cookie_consent.js',
               docs=['https://support.consentmo.com/en/article/shopify-customer-privacy-api-integration-1284c47/ (automatic since 2024-12-12)']),
    script_blocker=dict(present='not found', mechanism='no script type-rewriting or createElement patch found; docs say blocking is done by Shopify', evidence='code (text/plain 0, createElement override 0)'))
C['cookiebot'] = dict(
    name='Cookiebot (Usercentrics)', integration_mode='C', mode_evidence='docs (Shopify app sync) + code (auto-blocker); manual theme install = B',
    detect=dict(script_url_regex=[r'consent\.cookiebot\.(com|eu)/uc\.js', r'consent\.cookiebot\.(com|eu)/[0-9a-f-]{36}/cc\.js', r'consentcdn\.cookiebot\.(com|eu)/consentconfig/'],
                globals=['Cookiebot', 'CookieConsent'], dom_selectors=['#CybotCookiebotDialog'], cookies=['CookieConsent'], evidence='code + study2 (12 loads)'),
    reject=dict(selectors=['#CybotCookiebotDialogBodyButtonDecline', '#CybotCookiebotDialogBodyLevelButtonLevelOptinDeclineAll'], text_regex=REJECT_TEXT,
                observed_texts_study2={'Necessary (button text includes cookie count)': 3}, evidence='unverified selectors; study2 texts'),
    declared_config=dict(available=True, how='GET consentcdn.cookiebot.com/consentconfig/<cbid>/<domain>/configuration.js -> lines CookieConsent.configuration.tags.push({url, resolvedUrl, cat:[..]}) (+ trackingDomains). Blocking mode: data-blockingmode="auto" attribute on the uc.js <script> tag.',
                         category_ids='cat numbers as used in configuration.js; mapping 1 necessary, 2 preferences, 3 statistics, 4 marketing, 5 unclassified is unverified',
                         evidence='code: cmp_code/cookiebot__configuration_augustinusbader.js'),
    cpapi=dict(calls_setTrackingConsent='via Shopify app only', evidence='uc.js: 0 occurrences',
               docs=['https://shopify-support.cookiebot.com/hc/en-us/articles/26202116855068 ("handles this Customer Privacy API sync automatically"; manual theme.liquid installs need separate code)']),
    script_blocker=dict(present=True, mechanism='auto-blocking mode: MutationObserver + type rewriting (text/plain) + createElement patch', reaches_web_workers=False, evidence='code (uc.js)'))
C['onetrust'] = dict(
    name='OneTrust', integration_mode='C', mode_evidence='code (Shopify app storefront-consent.js + OtAutoBlock.js) + docs; without the app = B',
    detect=dict(script_url_regex=[r'cdn\.cookielaw\.org/scripttemplates/otSDKStub\.js', r'cdn\.cookielaw\.org/consent/[0-9a-f-]+/OtAutoBlock\.js', r'(cdn\.cookielaw\.org|optanon\.blob\.core\.windows\.net)/',
                                  r'cdn\.shopify\.com/extensions/[0-9a-f-]+/onetrust-consent-management-\d+/assets/storefront-consent\.js', r'geolocation\.onetrust\.com/'],
                globals=['OneTrust', 'OnetrustActiveGroups', 'OptanonActiveGroups', 'OptanonWrapper'], dom_selectors=['#onetrust-banner-sdk', '#onetrust-pc-sdk', '#onetrust-consent-sdk'],
                cookies=['OptanonConsent', 'OptanonAlertBoxClosed'], evidence='code + study2 (74 loads, 16 with window.Shopify)'),
    reject=dict(selectors=['#onetrust-reject-all-handler', '.ot-pc-refuse-all-handler'], text_regex=REJECT_TEXT,
                observed_texts_study2={'Reject All': 6, 'Decline all optional': 3, 'Reject Optional Cookies': 1, 'Necessary Cookies Only': 1},
                notes='US notice-only templates often have no reject button (only a "Do Not Sell or Share" link, which we must not follow into a form); record reject_available=false.', evidence='unverified selectors; study2 texts'),
    declared_config=dict(available=True, how='OtAutoBlock.js (cdn.cookielaw.org/consent/<domainId>/OtAutoBlock.js) embeds JSON.parse(\'[{"Tag":"<url>","CategoryId":["C0004"],...}]\') = URL -> category map used for blocking. Groups: C0001 strictly necessary, C0002 performance, C0003 functional, C0004 targeting, C0005 social media (OneTrust default ids; tenants can rename).',
                         example='[S0589] OtAutoBlock.js: 40 entries incl. https://tiktok.com/ (C0004), https://www.facebook.com/tr/ (C0004) and Shopify web-pixel sandbox iframe URLs',
                         declared_blocked_rule='URL prefix matches Tag and none of its CategoryId is in OnetrustActiveGroups', evidence='code'),
    cpapi=dict(calls_setTrackingConsent='via Shopify app extension', evidence='code: storefront-consent.js calls Shopify.customerPrivacy.setTrackingConsent',
               docs=['https://developer.onetrust.com/onetrust/docs/ecommerce (category mapping C0002->analytics, C0004->marketing & sale_of_data, C0003->preferences; "AutoBlocking can not be used as custom pixels are added as iFrames")']),
    script_blocker=dict(present='if OtAutoBlock.js loaded', mechanism='MutationObserver on script/iframe/img/embed + type text/plain rewriting', reaches_web_workers=False, evidence='code'))
C['osano'] = dict(
    name='Osano', integration_mode='C', mode_evidence='code (setTrackingConsent in osano.js) + docs; blocker capability from code (MutationObserver) not fully characterised',
    detect=dict(script_url_regex=[r'cmp\.osano\.com/[A-Za-z0-9]+/[0-9a-f-]+/osano(-ui)?\.js', r'consent\.api\.osano\.com/'], globals=['Osano'],
                dom_selectors=['.osano-cm-dialog:not(.osano-cm-dialog--hidden)', '.osano-cm-window'], cookies=['osano_consentmanager'], evidence='code + study2 (13 loads)'),
    reject=dict(selectors=['.osano-cm-denyAll', '.osano-cm-deny'], text_regex=REJECT_TEXT, observed_texts_study2={'Deny Non-Essential': 5, 'DENY NON-ESSENTIAL': 1}, evidence='unverified selectors; study2 texts'),
    declared_config=dict(available='partial', how='Per-customer config is compiled into osano.js (config.gpcSupport, doNotSellCategories ...); script/iframe classifications not parsed yet. Categories: ESSENTIAL, ANALYTICS, MARKETING, PERSONALIZATION, OPT_OUT.'),
    cpapi=dict(calls_setTrackingConsent=True, evidence='code: osano.js maps analytics/marketing/personalization/opt-out to setTrackingConsent', docs=['https://docs.osano.com/hc/en-us/articles/22469674240660-Installing-Osano-on-Shopify']),
    script_blocker=dict(present=True, mechanism='Osano intercepts scripts/iframes on the main thread (MutationObserver in osano.js)', reaches_web_workers=False, evidence='code (partial)'))
C['usercentrics'] = dict(
    name='Usercentrics (CMP v2/v3)', integration_mode='B', mode_evidence='code (no CPAPI in loader) + docs (sync needs an event-listener snippet); = C when merchant installs the sync',
    detect=dict(script_url_regex=[r'web\.cmp\.usercentrics\.eu/ui/(loader|v/[\d.]+/)', r'app\.usercentrics\.eu/browser-ui/', r'privacy-proxy\.usercentrics\.eu/latest/uc-block\.bundle\.js',
                                  r'(v1\.api\.service\.cmp|api|consent-api\.service\.consent)\.usercentrics\.eu/'],
                globals=['UC_UI', '__ucCmp', 'usercentrics'], dom_selectors=['#usercentrics-root', '#usercentrics-cmp-ui', 'aside#usercentrics-cmp-ui'], cookies=['uc_settings (localStorage)', 'uc_user_interaction (localStorage)'],
                shadow_dom='v2 #usercentrics-root uses a shadow root', evidence='code + study2 (21 loads, 11 with window.Shopify)'),
    reject=dict(selectors=['[data-testid="uc-deny-all-button"]', '#deny', 'button[data-action-type="deny"]'], text_regex=REJECT_TEXT, observed_texts_study2={}, evidence='unverified'),
    declared_config=dict(available=True, how='Settings/ruleset JSON fetched from v1.api.service.cmp.usercentrics.eu/latest/... lists data-processing services and categories; uc-block.bundle.js blocks listed services.'),
    cpapi=dict(calls_setTrackingConsent='only with merchant-added sync snippet', evidence='code: loader.js 0 occurrences',
               docs=['https://support.usercentrics.com/hc/en-us/articles/21694498850716 (sync via predefined services + event listener; console log "UC consent synced with Shopify Customer Privacy API")']),
    script_blocker=dict(present='if uc-block.bundle.js loaded (Smart Data Protector)', reaches_web_workers=False, evidence='code (uc-block.bundle.js createElement patch)'))
C['trustarc'] = dict(
    name='TrustArc Cookie Consent Manager', integration_mode='C', mode_evidence='docs (Shopify app reads/writes CPAPI) + autoblock asset seen; code not downloaded (empty response)',
    detect=dict(script_url_regex=[r'consent\.trustarc\.com/(notice|asset/notice\.js|autoblockasset/core\.min\.js|autoblockoptout)', r'form-renderer\.trustarc\.com/'],
                globals=['truste'], dom_selectors=['#truste-consent-track', '#truste-consent-content', '.truste_box_overlay', '#consent_blackbar'],
                cookies=['notice_preferences', 'notice_gdpr_prefs', 'cmapi_cookie_privacy', 'TAconsentID'], evidence='study2 (15 loads; #consent_blackbar also used by Securiti -> use script URL to disambiguate)'),
    reject=dict(selectors=['#truste-consent-required'], text_regex=REJECT_TEXT, observed_texts_study2={}, evidence='unverified'),
    declared_config=dict(available='unknown', how='autoblock configuration served by consent.trustarc.com; not parsed.'),
    cpapi=dict(calls_setTrackingConsent='via Shopify app', docs=['https://trustarchelp.zendesk.com/hc/en-us/articles/42823230618259']),
    script_blocker=dict(present='if autoblockasset/core.min.js loaded', reaches_web_workers=False, evidence='study2 URL only'))
C['didomi'] = dict(
    name='Didomi', integration_mode='A', mode_evidence='docs (Shopify beta integration maps purposes to CPAPI); loader code has no CPAPI call; no auto-blocker found',
    detect=dict(script_url_regex=[r'sdk\.privacy-center\.org/'], globals=['Didomi', 'didomiOnReady'], dom_selectors=['#didomi-notice', '#didomi-popup', '#didomi-host'],
                cookies=['didomi_token', 'euconsent-v2'], evidence='study2 (4 loads, 0 with window.Shopify)'),
    reject=dict(selectors=['#didomi-notice-disagree-button', '.didomi-continue-without-agreeing'], text_regex=REJECT_TEXT, observed_texts_study2={}, evidence='unverified'),
    declared_config=dict(available='partial', how='Didomi.getRequiredVendors()/getRequiredPurposes() in page; vendor list, not URL blocklist.'),
    cpapi=dict(calls_setTrackingConsent='via Shopify integration (beta)', docs=['https://docs.didomi.io/integrations/content-management-system-cms/shopify-beta']),
    script_blocker=dict(present=False, evidence='code: loader.js 0 MutationObserver/type-rewrite'))
C['termly'] = dict(
    name='Termly', integration_mode='X', mode_evidence='no CPAPI documentation found; has a resource auto-blocker -> probably B',
    detect=dict(script_url_regex=[r'app\.termly\.io/(resource-blocker|embed(\.min)?\.js|api/)'], globals=['Termly'],
                dom_selectors=['[class*="termly-styles-root"]', '#termly-code-snippet-support div[role="dialog"]'], cookies=[], evidence='study2 selector list (0 loads observed)'),
    reject=dict(selectors=['[data-tid="banner-decline"]'], text_regex=REJECT_TEXT, observed_texts_study2={}, evidence='unverified'),
    declared_config=dict(available='unknown', how='resource-blocker script URL carries ?autoBlock=on|off; category lists served by app.termly.io'),
    cpapi=dict(calls_setTrackingConsent='unknown'), script_blocker=dict(present='probable (resource-blocker)', reaches_web_workers=False, evidence='unverified'))
C['cookieyes'] = dict(
    name='CookieYes', integration_mode='X', mode_evidence='no CPAPI documentation found; auto-blocking product -> probably B',
    detect=dict(script_url_regex=[r'cdn-cookieyes\.com/client_data/[0-9a-f]+/script\.js', r'(app|log)\.cookieyes\.com/'], globals=['getCkyConsent', 'revisitCkyConsent'],
                dom_selectors=['.cky-consent-container', '.cky-consent-bar'], cookies=['cookieyes-consent'], evidence='study2 selector list (0 loads)'),
    reject=dict(selectors=['.cky-btn-reject'], text_regex=REJECT_TEXT, observed_texts_study2={}, evidence='unverified'),
    declared_config=dict(available='unknown', how='client_data script embeds categories and blocked script patterns (not parsed)'),
    cpapi=dict(calls_setTrackingConsent='unknown'), script_blocker=dict(present='probable', reaches_web_workers=False, evidence='unverified'),
    notes='"cookie_law_info" (CookieYes WordPress plugin) seen once in Study 2 on a Shopify landing that loaded it from a WordPress blog; treat as B.')
C['enzuzo'] = dict(
    name='Enzuzo', integration_mode='A', mode_evidence='vendor claim only (enzuzo.com blog: integrates natively with the Customer Privacy API); no code checked',
    detect=dict(script_url_regex=[r'app\.enzuzo\.com/'], globals=[], dom_selectors=['#ez-cookie-notification', '.enzuzo-cookiebanner-container'], cookies=[], evidence='unverified (0 loads observed)'),
    reject=dict(selectors=[], text_regex=REJECT_TEXT, observed_texts_study2={}, evidence='text only'),
    declared_config=dict(available='unknown'), cpapi=dict(calls_setTrackingConsent='claimed', docs=['https://www.enzuzo.com/blog/cookie-consent-platforms-for-shopify']),
    script_blocker=dict(present='unknown'))
C['iubenda'] = dict(
    name='iubenda Privacy Controls and Cookie Solution', integration_mode='A', mode_evidence='docs (Shopify integration uses CPAPI and recommends turning iubenda autoblocking off); C if autoblocking on',
    detect=dict(script_url_regex=[r'cdn\.iubenda\.com/(cs/|autoblocking/)', r'embeds\.iubenda\.com/widgets/'], globals=['_iub'], dom_selectors=['#iubenda-cs-banner'], cookies=['_iub_cs-*'], evidence='study2 selector list (0 loads)'),
    reject=dict(selectors=['.iubenda-cs-reject-btn'], text_regex=REJECT_TEXT, observed_texts_study2={}, evidence='unverified'),
    declared_config=dict(available='partial', how='autoblocking script cdn.iubenda.com/autoblocking/<siteId>.js lists blocked vendors when enabled'),
    cpapi=dict(calls_setTrackingConsent='per docs', docs=['https://www.iubenda.com/en/help/10811-cookie-solution-shopify-3/']),
    script_blocker=dict(present='optional (autoblocking)', reaches_web_workers=False))
C['axeptio'] = dict(
    name='Axeptio', integration_mode='X', mode_evidence='docs describe Shopify integration and forwarding consent to custom pixels; CPAPI write not confirmed',
    detect=dict(script_url_regex=[r'static\.axept\.io/(sdk|sdk-slim)\.js', r'client\.axept\.io/'], globals=['axeptioSDK', '_axcb', 'axeptioSettings'], dom_selectors=['#axeptio_overlay', '.axeptio_mount'], cookies=['axeptio_cookies', 'axeptio_authorized_vendors'], evidence='unverified (0 loads)'),
    reject=dict(selectors=['#axeptio_btn_dismiss'], text_regex=REJECT_TEXT, observed_texts_study2={}, evidence='unverified'),
    declared_config=dict(available='partial', how='axeptio_authorized_vendors cookie / project config JSON'),
    cpapi=dict(calls_setTrackingConsent='unknown', docs=['https://support.axeptio.eu/en/articles/274019-shopify-integration', 'https://support.axeptio.eu/en/articles/274037-handle-axeptio-consent-with-shopify-custom-pixels']),
    script_blocker=dict(present='unknown'))
C['pentos'] = dict(
    name='Pentos', integration_mode='X', mode_evidence='not found: no Shopify app, documentation or script for a CMP named "Pentos" was located (searches 2026-09-26). Keep for completeness; drop if the crawl never detects it.',
    detect=dict(script_url_regex=[], globals=[], dom_selectors=[], cookies=[]), reject=dict(selectors=[], text_regex=REJECT_TEXT), declared_config=dict(available='unknown'),
    cpapi=dict(calls_setTrackingConsent='unknown'), script_blocker=dict(present='unknown'))
C['transcend'] = dict(
    name='Transcend Consent (airgap.js)', integration_mode='B', mode_evidence='code (airgap.js has no CPAPI call; network-level regulation incl. Worker/importScripts hooks) + docs (Shopify sync set up separately)',
    detect=dict(script_url_regex=[r'transcend-cdn\.com/cm/[0-9a-f-]+/(airgap|ui)\.js'], globals=['airgap', 'transcend'], dom_selectors=['#transcend-consent-manager'], cookies=[], evidence='code + study2 (8 loads)'),
    reject=dict(selectors=[], text_regex=REJECT_TEXT, observed_texts_study2={}, evidence='text only'),
    declared_config=dict(available=True, how='airgap.js bundle embeds the regulated purposes/services config (not parsed)'),
    cpapi=dict(calls_setTrackingConsent='only if Shopify sync configured', evidence='code: 0 occurrences', docs=['https://docs.transcend.io/docs/articles/consent-management/configuration/shopify-integration']),
    script_blocker=dict(present=True, mechanism='network-level quarantine of fetch/XHR/beacon/script plus hooks on Worker, SharedWorker, ServiceWorker and importScripts', reaches_web_workers='possibly (code hooks Worker constructors); to test', evidence='code'))
C['ketch'] = dict(
    name='Ketch', integration_mode='C', mode_evidence='code indicators only (setTrackingConsent + customerPrivacy in ketch-sdk.js; tag gating)',
    detect=dict(script_url_regex=[r'global\.ketchcdn\.com/web/v\d/config/', r'cdn\.ketchjs\.com/ketchtag/'], globals=['ketch', 'semaphore', 'ketchConsent'], dom_selectors=['#lanyard_root'], cookies=['_swb_consent_'], evidence='code + study2 (1 load)'),
    reject=dict(selectors=[], text_regex=REJECT_TEXT, observed_texts_study2={'Reject All Cookies': 1}, evidence='study2'),
    declared_config=dict(available=True, how='config.json at global.ketchcdn.com/web/v3/config/<org>/<property>/production/<jurisdiction>/<lang>/config.json (purposes)'),
    cpapi=dict(calls_setTrackingConsent=True, evidence='code: 1 occurrence'), script_blocker=dict(present='probable', reaches_web_workers=False, evidence='code (text/plain rewriting hits)'))
C['clarip'] = dict(
    name='Clarip', integration_mode='C', mode_evidence='code (setTrackingConsent + blocklist/MutationObserver in clarip-cookie-manager.min.js)',
    detect=dict(script_url_regex=[r'cdn\.clarip\.com/[a-z0-9]+/(cookieconsent|donotsell)/'], globals=[], dom_selectors=['.cc-window'], cookies=['clarip_cookie_consent_gpc'], evidence='code + study2 (4 loads)'),
    reject=dict(selectors=['.cc-deny'], text_regex=REJECT_TEXT, observed_texts_study2={'Reject': 1}, evidence='code (cc-deny) + study2'),
    declared_config=dict(available=True, how='configuration JSON cdn.clarip.com/<client>/cookieconsent/configuration/<id>.json (+ -cookie-file.json)'),
    cpapi=dict(calls_setTrackingConsent=True, evidence='code'), script_blocker=dict(present=True, reaches_web_workers=False, evidence='code (blocklist keys 19, MutationObserver 5)'))
C['consentmanager'] = dict(
    name='consentmanager.net', integration_mode='B', mode_evidence='code (semiautomatic blocker, no CPAPI call)',
    detect=dict(script_url_regex=[r'cdn\.consentmanager\.net/delivery/', r'delivery\.consentmanager\.net/delivery/cmp\.php'], globals=['__cmp', '__tcfapi'], dom_selectors=['#cmpwrapper', '#cmpbox'], cookies=['__cmpconsent*', '__cmpcccu*'], evidence='code + study2 (6 loads)'),
    reject=dict(selectors=['#cmpwelcomebtnno', '.cmpboxbtnno'], text_regex=REJECT_TEXT, observed_texts_study2={}, evidence='unverified'),
    declared_config=dict(available='partial', how='customdata/<id>.js served by cdn.consentmanager.net'),
    cpapi=dict(calls_setTrackingConsent=False, evidence='code: 0 occurrences in semiautomatic.min.js (cmp_final.min.js not scanned)'), script_blocker=dict(present=True, reaches_web_workers=False, evidence='product name/URL'))
C['cookiefirst'] = dict(
    name='CookieFirst', integration_mode='A', mode_evidence='code: sh-customer-privacy.js writes CPAPI; banner variant "no-autoblock" seen (would be C with the autoblock build)',
    detect=dict(script_url_regex=[r'consent\.cookiefirst\.com/(sites/|banner/|consentBanner(\.no-autoblock)?\.js|sh-customer-privacy\.js)'], globals=['CookieFirst'], dom_selectors=['.cookiefirst-root'], cookies=['cookiefirst-consent'], evidence='code + study2 (2 loads)'),
    reject=dict(selectors=['[data-cookiefirst-action="reject"]'], text_regex=REJECT_TEXT, observed_texts_study2={'Decline': 2}, evidence='study2 text; selector unverified'),
    declared_config=dict(available=True, how='consent.cookiefirst.com/sites/<site>/consent.js (site config)'),
    cpapi=dict(calls_setTrackingConsent=True, evidence='code: on cf_consent events maps performance->analytics, advertising->marketing and sale_of_data, functional->preferences'),
    script_blocker=dict(present='only with the autoblock banner build', evidence='code (file name consentBanner.no-autoblock.js)'))
C['cookiehub'] = dict(
    name='CookieHub', integration_mode='C', mode_evidence='code + docs (CPAPI integration on by default; auto-blocking)',
    detect=dict(script_url_regex=[r'cdn\.cookiehub\.eu/c2/[0-9a-f]+\.js'], globals=['cookiehub', '__cookiehub'], dom_selectors=['.ch2-container', '.ch2-dialog'], cookies=['cookiehub'], evidence='code + study2 (1 load)'),
    reject=dict(selectors=['.ch2-deny-all-btn'], text_regex=REJECT_TEXT, observed_texts_study2={}, evidence='code'),
    declared_config=dict(available='partial', how='category/vendor config embedded in c2/<id>.js'),
    cpapi=dict(calls_setTrackingConsent=True, evidence='code: 2 occurrences', docs=['https://www.cookiehub.com/shopify-customer-privacy-api']),
    script_blocker=dict(present=True, reaches_web_workers=False, evidence='code (type text/plain, MutationObserver)'))
C['cookiescript'] = dict(
    name='Cookie-Script', integration_mode='X', mode_evidence='script could not be downloaded (TLS error); unknown',
    detect=dict(script_url_regex=[r'(cdn|geo)\.cookie-script\.com/s/[0-9a-f]+\.js'], globals=['CookieScript'], dom_selectors=['#cookiescript_injected'], cookies=['CookieScriptConsent'], evidence='study2 (1 load)'),
    reject=dict(selectors=['#cookiescript_reject'], text_regex=REJECT_TEXT, observed_texts_study2={}, evidence='unverified'),
    declared_config=dict(available='unknown'), cpapi=dict(calls_setTrackingConsent='unknown'), script_blocker=dict(present='probable'))
C['fides_ethyca'] = dict(
    name='Ethyca Fides', integration_mode='A', mode_evidence='code (setTrackingConsent in fides.js; no main-thread blocker found)',
    detect=dict(script_url_regex=[r'fides-cdn\.ethyca\.com/fides\.js', r'/fides\.js(\?|$)'], globals=['Fides'], dom_selectors=['#fides-overlay', '#fides-banner', '#fides-modal'], cookies=['fides_consent'], evidence='code + study2 (2 loads)'),
    reject=dict(selectors=['.fides-reject-all-button'], text_regex=REJECT_TEXT, observed_texts_study2={}, evidence='code'),
    declared_config=dict(available=True, how='privacy-experience API response (/api/v1/privacy-experience) lists notices and their consent mechanisms'),
    cpapi=dict(calls_setTrackingConsent=True, evidence='code: 1 occurrence'), script_blocker=dict(present=False, evidence='code'))
C['consentik'] = dict(
    name='Consentik GDPR Cookie Banner (Shopify app)', integration_mode='X', mode_evidence='Shopify app listing only; not inspected',
    detect=dict(script_url_regex=[r'cdn\.shopify\.com/extensions/[0-9a-f-]+/[a-z-]*consentik[a-z0-9-]*/'], globals=[], dom_selectors=[], cookies=[], evidence='unverified'),
    reject=dict(selectors=[], text_regex=REJECT_TEXT), declared_config=dict(available='unknown'), cpapi=dict(calls_setTrackingConsent='unknown', docs=['https://apps.shopify.com/eu-cookies-notification']),
    script_blocker=dict(present='unknown'))
C['securiti'] = dict(
    name='Securiti', integration_mode='X', mode_evidence='not inspected; Study 2 selector overlaps TrustArc (#consent_blackbar) so its 13 detections co-occurred with TrustArc',
    detect=dict(script_url_regex=[r'cdn-prod\.securiti\.ai/', r'\.securiti\.ai/consent/'], globals=[], dom_selectors=['.cmp-banner', '[class*="securiti"]'], cookies=[], evidence='study2 (weak)'),
    reject=dict(selectors=[], text_regex=REJECT_TEXT), declared_config=dict(available='unknown'), cpapi=dict(calls_setTrackingConsent='unknown'), script_blocker=dict(present='unknown'))

for k, v in C.items():
    v['code_scan'] = scan.get(k, [])
    v['study2_default_loads'] = S2_ALL.get(k, 0)
    v['study2_default_loads_with_window_Shopify'] = S2_SHOP.get(k, 0)

META = dict(
    description=__doc__.strip().split('\n\n')[0],
    built='2026-09-26 by build_cmp_signatures.py',
    evidence_levels={'code': 'seen in downloaded vendor JS or live storefront HTML', 'study2': 'observed in Study 2 captures', 'docs': 'documentation', 'unverified': 'not verified here; confirm in the manual audit'},
    integration_modes={'N': 'Shopify native banner (writes CPAPI)', 'A': 'CPAPI only (setTrackingConsent on choice; no main-thread blocker)',
                       'B': 'main-thread script blocker only (never writes CPAPI; cannot gate sandboxed web pixels)', 'C': 'CPAPI + main-thread blocker', 'X': 'unknown'},
    generic_reject=dict(text_regex=REJECT_TEXT, never_click_regex=NEVER_CLICK,
        procedure=['wait until a known CMP container or the generic banner detector is visible (<=10 s)',
                   'search visible buttons/links (piercing open shadow roots) inside the container; take the first whose trimmed text fully matches text_regex, else a CMP-specific selector',
                   'never click an element whose text matches never_click_regex; never follow "Do Not Sell/Share" links or submit forms',
                   'if no reject-type control exists, record reject_available=false and do not click anything',
                   'screenshot before/after; record click time, selector/text used, and Shopify.customerPrivacy.currentVisitorConsent() 1 s and 5 s after the click']),
    per_store_integration_test=dict(
        definition='A store is CPAPI-integrated (observed) if, after the Decline click, Shopify.customerPrivacy.currentVisitorConsent().marketing becomes "no" (or a visitorConsentCollected event with marketingAllowed=false fires) within 5 s; otherwise the CMP is script-blocking-only on that store (observed mode B) even if the product supports CPAPI.',
        also_record=['_tracking_consent cookie present/changed (value not stored)', 'Shopify.customerPrivacy.shouldShowBanner()', 'Server-Timing _cmp of the navigation response']),
    shopify_consent_readout=dict(
        js_methods=['getRegion()', 'shouldShowBanner()', 'saleOfDataRegion()', 'analyticsProcessingAllowed()', 'marketingAllowed()', 'preferencesProcessingAllowed()',
                    'saleOfDataAllowed()', 'currentVisitorConsent()', 'getTrackingConsent()', 'consentId()'],
        js_methods_source='exports of /cdn/shopifycloud/consent-tracking-api/v0.1/consent-tracking-api.js (static_mechanism/consent_tracking_api.pretty.js); also deprecated aliases userCanBeTracked, userDataCanBeSold, firstPartyMarketingAllowed, thirdPartyMarketingAllowed, setCCPAConsent, getCCPAConsent',
        event='document "visitorConsentCollected" CustomEvent, detail {analyticsAllowed, marketingAllowed, preferencesAllowed, saleOfDataAllowed}',
        server_timing=dict(header='Server-Timing: _cmp;desc="3<choices>.<purposes>_<region>_<display_banner t|f>_<sale_of_data_region t|f>_<consent id>"',
                           decode='choices: lower-case letter = declined, upper-case = accepted, absent = no choice; purposes: upper-case letter present = processing allowed (A analytics, M marketing, P preferences, S sale of data)',
                           examples={'3.AMPS_USCA_f_f_...': 'no choice; all allowed (opt-out mode); no banner required', '3.ampS_USCA_t_t_...': 'no choice; analytics/marketing/preferences NOT allowed until consent (opt-in mode); banner required',
                                     '3s.AMP_USCA_f_t_...': 'Sec-GPC: 1 sent -> sale_of_data declined, S removed'},
                           decoder='static_mechanism/probe_cmp_headers.py: decode_cmp()'),
        web_pixels_config='inline <script> calling wpmLoader({... webPixelsConfigList: [...] ...}); parse the JSON array between "webPixelsConfigList:" and ", isMerchantRequest" (fields id, type APP|CUSTOM, runtimeContext STRICT|LAX|OPEN, apiClientId, privacyPurposes, configuration)',
        edge_cache_flags=['window.Nostra or /_nostra/ scripts', 'response header cf-cache-status: HIT with large age', '_cmp region differs from the vantage region -> consent header cached from another visitor']),
)
out = dict(_meta=META, cmps=C)
json.dump(out, open(os.path.join(HERE, 'cmp_signatures.json'), 'w'), indent=1)
print('CMPs:', len(C), {m: sum(1 for v in C.values() if v['integration_mode'] == m) for m in 'NABCX'})
