"""Static code scan of consent-management (CMP) scripts seen on Shopify stores in Study 2.

For each CMP we download (once, honest UA, no cookies, >=1 s apart) the script files that the
Study 2 browser actually loaded, then count code indicators of the two integration paths:
  * Shopify Customer Privacy API (CPAPI): setTrackingConsent, customerPrivacy, loadFeatures,
    consent-tracking-api, visitorConsentCollected
  * main-thread script blocking: MutationObserver + script type rewriting (text/plain),
    document.createElement overrides, blocklist keys.
Output: cmp_code_scan.csv (+ raw files in cmp_code/). Indicator present != feature enabled on
any particular store; per-store behaviour must be verified dynamically.
"""
import csv, os, re, time, urllib.request, hashlib, sys
UA = 'Mozilla/5.0 (compatible; shopify-consent-study/1.0; non-commercial academic measurement crawler)'
FILES = [
 ('pandectes', 'https://cdn.shopify.com/extensions/01a0d309-5aa0-76cf-9f48-2a42b2760403/gdpr-cookie-consent-411/assets/pandectes-core-latest.js'),
 ('pandectes', 'https://cdn.shopify.com/extensions/01a0d309-5aa0-76cf-9f48-2a42b2760403/gdpr-cookie-consent-411/assets/pandectes-rules-latest.js'),
 ('consentmo', 'https://cdn.shopify.com/extensions/01a0d7a2-a36b-73ee-b8cb-ead3ca4862c3/gdpr-backpack-896/assets/consentmo_cookie_consent.js'),
 ('consentmo', 'https://cdn.shopify.com/extensions/01a0d7a2-a36b-73ee-b8cb-ead3ca4862c3/gdpr-backpack-896/assets/63.consentmo.js'),
 ('consentmo', 'https://gdprcdn.b-cdn.net/js/gdpr_cookie_consent.min.js'),
 ('cookiebot', 'https://consent.cookiebot.com/uc.js'),
 ('onetrust', 'https://cdn.shopify.com/extensions/01a061ba-09b8-7f28-a51f-be55b3ced758/onetrust-consent-management-67/assets/storefront-consent.js'),
 ('onetrust', 'https://cdn.cookielaw.org/scripttemplates/otSDKStub.js'),
 ('onetrust', 'https://cdn.cookielaw.org/consent/019074af-b6fa-794f-b5d2-dc43921ade93/OtAutoBlock.js'),
 ('osano', 'https://cmp.osano.com/16A4AHTHturum1urg/1a7c3e51-0f22-486d-bcda-6820a1c1d35e/osano.js'),
 ('usercentrics', 'https://web.cmp.usercentrics.eu/ui/loader.js'),
 ('usercentrics', 'https://privacy-proxy.usercentrics.eu/latest/uc-block.bundle.js'),
 ('trustarc', 'https://consent.trustarc.com/autoblockasset/core.min.js'),
 ('transcend', 'https://transcend-cdn.com/cm/1c1f8e90-47d0-4bba-a1a2-472d59b002a2/airgap.js'),
 ('ketch', 'https://cdn.ketchjs.com/ketchtag/stable/v2.12/ketch-sdk.js'),
 ('clarip', 'https://cdn.clarip.com/kendo/cookieconsent/assets/js/clarip-cookie-manager.min.js'),
 ('consentmanager', 'https://cdn.consentmanager.net/delivery/js/semiautomatic.min.js'),
 ('cookiefirst', 'https://consent.cookiefirst.com/sh-customer-privacy.js'),
 ('cookiefirst', 'https://consent.cookiefirst.com/consentBanner.no-autoblock.js'),
 ('cookiehub', 'https://cdn.cookiehub.eu/c2/22f94c69.js'),
 ('cookiescript', 'https://geo.cookie-script.com/s/bd8c35f83798de652c5ca16479412bf1.js'),
 ('fides_ethyca', 'https://bitly.fides-cdn.ethyca.com/fides.js'),
 ('didomi', 'https://sdk.privacy-center.org/6548bad1-0168-47ce-ac9b-870e1cd36b26/loader.js'),
] + [tuple(a.split('=', 1)) for a in sys.argv[1:]]
IND = {
 'setTrackingConsent': r'setTrackingConsent',
 'customerPrivacy': r'customerPrivacy',
 'loadFeatures_consent_api': r'loadFeatures|consent-tracking-api',
 'visitorConsentCollected': r'visitorConsentCollected',
 'sale_of_data_key': r'sale_of_data',
 'globalPrivacyControl': r'globalPrivacyControl',
 'MutationObserver': r'MutationObserver',
 'type_text_plain': r'text/plain',
 'createElement_override': r'document\.createElement\s*=|createElement\s*=\s*function|Document\.prototype\.createElement',
 'blocklist_keys': r'blackList|blacklist|blockList|blocklist|blockedScripts|autoblock|AutoBlock',
 'web_pixel_mention': r'web-pixel|webPixel|web_pixel|analytics\.subscribe',
}
rows = []
for cmp, url in FILES:
    fn = os.path.join('cmp_code', cmp + '__' + re.sub(r'[^A-Za-z0-9._-]', '_', url.split('/')[-1] or 'index')[:80])
    row = dict(cmp=cmp, url=url, file=fn)
    try:
        if not os.path.exists(fn):
            time.sleep(1.0)
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=25) as r:
                data = r.read()
                if r.headers.get('Content-Encoding') == 'gzip':
                    import gzip; data = gzip.decompress(data)
            open(fn, 'wb').write(data)
        s = open(fn, 'rb').read().decode('utf-8', 'ignore')
        row.update(bytes=len(s), sha1=hashlib.sha1(s.encode()).hexdigest()[:12])
        for k, pat in IND.items():
            row[k] = len(re.findall(pat, s))
    except Exception as e:
        row['error'] = str(e)[:120]
    rows.append(row)
    print(cmp, row.get('bytes'), {k: row.get(k) for k in ('setTrackingConsent', 'customerPrivacy', 'MutationObserver', 'type_text_plain', 'blocklist_keys', 'globalPrivacyControl')}, row.get('error', ''), flush=True)
keys = ['cmp', 'url', 'file', 'bytes', 'sha1', 'error'] + list(IND)
with open('cmp_code_scan.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
