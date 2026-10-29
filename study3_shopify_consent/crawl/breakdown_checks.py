"""Quick diagnostic breakdowns behind two surprising headline rates (written to breakdown_checks.txt):
(1) sandboxed ad requests on opt-in (M denied) banner stores in A0; (2) sandboxed ad requests on the next page after Decline.
Shows vendor x origin x declared privacyPurposes of the originating pixel (store counts)."""
import os
import pandas as pd

H = os.path.dirname(os.path.abspath(__file__))
L = pd.read_csv(os.path.join(H, 'loads.csv'), low_memory=False)
R = pd.read_csv(os.path.join(H, 'requests.csv.gz'), low_memory=False)
ok = (L.goto_status.fillna(0).between(200, 399)) & (L.has_shopify == True) & (L.blocked_hint != True) & (L.n_requests.fillna(0) > 20)
L = L[ok & (L.stratum == 'main')]
sb = R[(R.is_advertising == True) & R.origin.isin(['strict_worker', 'lax_iframe'])].copy()
sb['pp'] = sb.pixel_type.fillna('?') + ':' + sb.pixel_purposes.fillna('(no config match)')
out = []
a0 = L[(L.arm == 'A0') & (L.banner_visible == True) & (L.cmp_allow_m == False)]
x = sb[sb.load_id.isin(a0.load_id)]
out.append(f'(1) A0 banner stores in opt-in mode (M denied): {a0.store_id.nunique()} stores; with sandboxed ad request: {x.store_id.nunique()}')
out.append(x.groupby(['vendor', 'origin', 'pp']).store_id.nunique().sort_values(ascending=False).head(15).to_string())
a1 = L[(L.arm == 'A1') & L.click_method.isin(['playwright_click', 'playwright_force', 'js_click'])]
y = sb[sb.load_id.isin(a1.load_id) & (sb.phase == 'next_page')]
out.append(f'\n(2) A1 clicked loads: {a1.store_id.nunique()}; with sandboxed ad request on next page: {y.store_id.nunique()}')
out.append(y.groupby(['vendor', 'origin', 'pp']).store_id.nunique().sort_values(ascending=False).head(15).to_string())
z = y.merge(a1[['load_id', 'cp_marketing_end']], on='load_id')
out.append('\nnext-page sandboxed-ad stores by Shopify marketingAllowed() at end of load:\n' + z.groupby('cp_marketing_end', dropna=False).store_id.nunique().to_string())
txt = '\n'.join(out)
open(os.path.join(H, 'breakdown_checks.txt'), 'w').write(txt + '\n')
print(txt)
