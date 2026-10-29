"""Summarise wpm_survey/pixels.csv and stores.csv (convenience set; descriptive only)."""
import pandas as pd
px = pd.read_csv('wpm_survey/pixels.csv', dtype=str).fillna('')
st = pd.read_csv('wpm_survey/stores.csv', dtype=str).fillna('')
print('stores fetched:', len(st), '| with WPM config:', (st.has_wpm_config == 'True').sum(), '| pixels:', len(px))
print('\nruntimeContext x type:'); print(pd.crosstab(px.runtimeContext, px.type))
print('\nprivacyPurposes x type:'); print(pd.crosstab(px.privacyPurposes.replace('', '[] (none)'), px.type))
app = px[px.type == 'APP']
g = app.groupby(['apiClientId']).agg(n=('store', 'nunique'), vendor=('vendor_guess', lambda s: '|'.join(sorted(set(x for x in s if x)))),
    runtime=('runtimeContext', lambda s: '|'.join(sorted(set(s)))), purposes=('privacyPurposes', lambda s: ' / '.join(sorted(set(x or '[]' for x in s)))),
    keys=('config_keys', lambda s: ' / '.join(sorted(set(s)))[:90])).sort_values('n', ascending=False)
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 90)
print('\nAPP pixels by apiClientId (n = stores):'); print(g.to_string())
def dec(v):
    if not v.startswith('3'): return None
    head = v[1:].split('_')[0]; purposes = head.split('.', 1)[1] if '.' in head else head
    return 'opt-in (A/M denied by default)' if ('M' not in purposes) else 'opt-out (A/M allowed by default)'
st['shopify_mode_USCA'] = st.cmp_raw.map(lambda v: dec(v) if v else 'no _cmp header')
print('\nShopify consent mode seen by our US-CA vantage (from _cmp):'); print(st.shopify_mode_USCA.value_counts().to_string())
print(st[['store', 'cmp_raw', 'shopify_mode_USCA', 'nostra_edge']].to_string(index=False))

print('\n--- headline counts (convenience set; descriptive) ---')
n_app = len(app)
print(f'APP pixels: {n_app}; STRICT {int((app.runtimeContext=="STRICT").sum())}, LAX {int((app.runtimeContext=="LAX").sum())}, OPEN {int((app.runtimeContext=="OPEN").sum())}')
print(f'CUSTOM pixels: {int((px.type=="CUSTOM").sum())} (all LAX: {bool((px[px.type=="CUSTOM"].runtimeContext=="LAX").all())})')
print(f'APP pixels declaring SALE_OF_DATA (GPC-gated): {int(app.privacyPurposes.str.contains("SALE_OF_DATA").sum())}/{n_app}')
print(f'APP pixels declaring MARKETING: {int(app.privacyPurposes.str.contains("MARKETING").sum())}/{n_app}')
print(f'APP pixels declaring no purpose (load regardless of consent): {int((app.privacyPurposes=="").sum())}/{n_app}')
cu = px[px.type == 'CUSTOM']
print(f'CUSTOM pixels declaring no purpose: {int((cu.privacyPurposes=="").sum())}/{len(cu)}')
KEY = {'4383523': 'TikTok', '2329312': 'Meta (Facebook & Instagram app)', '1780363': 'Google & YouTube app', '3009811': 'Pinterest', '2556259': 'Snapchat',
       '304258285569': 'Reddit', '5829751': 'LinkedIn', '256560922625': 'AppLovin Axon', '92361228289': 'tvScientific', '123074': 'Klaviyo', 'shopify-pixel': 'Shopify (own app pixel)'}
print('\nconfirmed vendor apps (apiClientId -> stores, runtime, purposes):')
for k, name in KEY.items():
    g = app[app.apiClientId == k]
    if len(g):
        print(f'  {name:32s} id={k:14s} stores={g.store.nunique():2d} runtime={sorted(set(g.runtimeContext))} purposes={sorted(set(x or "[]" for x in g.privacyPurposes))}')
