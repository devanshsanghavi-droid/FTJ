"""Static survey of Shopify Web Pixels Manager configs on a small convenience set of stores.
One plain GET per store home page (honest UA, Accept: text/html, no cookies, >=1.2 s between
requests). Extracts the inline `webPixelsConfigList` (pixel id, type APP/CUSTOM, runtimeContext
STRICT/LAX/OPEN, apiClientId, privacyPurposes, configuration keys) and the server-computed
consent string (Server-Timing `_cmp`). Purpose: learn apiClientId -> vendor and the sandbox /
privacy-purpose mix. NOT the study sample; convenience set drawn from Study 2 Shopify landings.
Outputs: wpm_survey/pixels.csv, wpm_survey/stores.csv, wpm_survey/<host>.html.gz
"""
import csv, gzip, json, os, re, sys, time, urllib.request
UA = 'Mozilla/5.0 (compatible; shopify-consent-study/1.0; non-commercial academic measurement crawler)'
STORES = sys.argv[1:] or ['s0347.store.example', 'www.brooklinen.com', 'c005.store.example/?skipCache=true', 'c011.store.example',
    'www.tower28beauty.com', 's0203.store.example', 's0120.store.example', 'c003.store.example', 's0542.store.example', 'www.hauslabs.com',
    'www.dominique.com', 'www.evo.com', 's0359.store.example', 'www.lillylashes.com', 's0983.store.example', 'www.yfood.com',
    'augustinusbader.com', 's0979.store.example', 'www.chomps.com', 'kyliecosmetics.com', 'skims.com', 's0589.store.example',
    's0146.store.example', 's0499.store.example', 'www.westman-atelier.com', 'www.thorum.com', 'www.cometeer.com', 'dftba.com']
VENDOR_KEYS = [  # configuration-key heuristics -> vendor (checked in order)
    ('tiktok', r'"pixelCode"|pixel_code'), ('meta', r'facebook_pixel|"pixel_id"'), ('google', r'google_tag_ids|"tagId":"(AW|G|GT)-'),
    ('reddit', r'redditPixelId'), ('pinterest', r'pinterest|"tagId":"26'), ('snap', r'snap|"pixelId":"[0-9a-f]{8}-'),
    ('klaviyo', r'"accountID"'), ('microsoft', r'"ti":|uet|bing'), ('x_twitter', r'twitter|"pixelId":"o'), ('elevar', r'getelevar'),
    ('triplewhale', r'triplewhale|"shopId":"[^"]+\.myshopify\.com"'), ('attentive', r'attentive|attn'), ('postscript', r'postscript'),
    ('criteo', r'criteo'), ('applovin', r'applovin|axon'), ('amazon', r'amazon'), ('linkedin', r'linkedin|partnerId'),
    ('northbeam', r'northbeam'), ('impact', r'impact|saasler'), ('yotpo', r'yotpo'), ('redo', r'getredo'), ('littledata', r'littledata')]
def vendor_guess(cfg, name):
    s = (cfg or '') + ' ' + (name or '')
    for v, pat in VENDOR_KEYS:
        if re.search(pat, s, re.I):
            return v
    return ''
store_rows, pix_rows = [], []
for st in STORES:
    url = 'https://' + st if not st.startswith('http') else st
    host = re.sub(r'^https?://([^/]+).*', r'\1', url)
    time.sleep(1.2)
    row = dict(store=host, url=url)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml'})
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read()
            if r.headers.get('Content-Encoding') == 'gzip':
                body = gzip.decompress(body)
            s = body.decode('utf-8', 'ignore')
            stt = ' '.join(r.headers.get_all('Server-Timing') or [])
            m = re.search(r'_cmp;desc="([^"]+)"', stt)
            row.update(status=r.status, final_url=r.geturl(), cmp_raw=m.group(1) if m else '', powered_by=r.headers.get('powered-by', ''),
                       cf_cache_status=r.headers.get('cf-cache-status', ''), bytes=len(s))
        gzip.open(os.path.join('wpm_survey', host + '.html.gz'), 'wt').write(s)
        m = re.search(r'webPixelsConfigList:\s*(\[.*?\])\s*,\s*isMerchantRequest', s, re.S)
        row['has_wpm_config'] = bool(m)
        row['nostra_edge'] = ('window.Nostra' in s) or ('/_nostra/' in s)
        if m:
            lst = json.loads(m.group(1))
            row['n_pixels'] = len(lst)
            for x in lst:
                cfg = x.get('configuration') or ''
                pix_rows.append(dict(store=host, id=x.get('id'), type=x.get('type'), runtimeContext=x.get('runtimeContext'),
                    apiClientId=x.get('apiClientId'), privacyPurposes='|'.join(x.get('privacyPurposes') or []),
                    has_privacyPurposes_key='privacyPurposes' in x, dataSharingState=x.get('dataSharingState'), name=x.get('name'),
                    config_keys='|'.join(sorted(json.loads(cfg).keys())) if cfg.startswith('{') else '', vendor_guess=vendor_guess(cfg, x.get('name'))))
    except Exception as e:
        row['error'] = str(e)[:150]
    store_rows.append(row)
    print(host, row.get('status'), row.get('has_wpm_config'), row.get('n_pixels'), row.get('cmp_raw'), row.get('error', ''), flush=True)
for fn, rows in (('wpm_survey/stores.csv', store_rows), ('wpm_survey/pixels.csv', pix_rows)):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(fn, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
