"""Compare one ConsentCheck result with the study crawl's results for the same store (read-only use of
analysis/outputs/store_table.csv, store_vendor.csv, residual_composition.csv and crawl/pixels.csv).

    python3 test/compare_with_crawl.py STORE_ID CONSENTCHECK.json OUT.md

The crawl ran on 2026-09-26 (Default A0, Decline A1 + next page, GPC A2, one load each); ConsentCheck repeats the same
three conditions with the same instrumentation library, so the verdicts should agree unless the store changed.
The output names the store only by its study code.
"""
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
OUT = os.path.join(STUDY, 'analysis', 'outputs')
sid, ccf, outf = sys.argv[1], sys.argv[2], sys.argv[3]
cc = json.load(open(ccf))
st = pd.read_csv(os.path.join(OUT, 'store_table.csv'), low_memory=False).set_index('store_id').loc[sid]
sv = pd.read_csv(os.path.join(OUT, 'store_vendor.csv'))
sv = sv[sv.store_id == sid].set_index('vgroup')
rc = pd.read_csv(os.path.join(OUT, 'residual_composition.csv'))
rc = rc[rc.store_id == sid]
px = pd.read_csv(os.path.join(STUDY, 'crawl', 'pixels.csv'), dtype=str)
px = px[px.store_id == sid]

rows = []


def add(item, crawl, consentcheck, note=''):
    agree = 'yes' if str(crawl) == str(consentcheck) else 'NO'
    rows.append((item, str(crawl), str(consentcheck), agree, note))


# ---- store level
s = cc['store']
add('Shopify default before any choice: marketing allowed', bool(st.region_optout), s['shopify_default']['marketing_allowed_before_choice'])
add('Consent tool', st.cmp, s['consent_app'])
add('Banner shown (Default or Decline visit)', bool(st.banner_A0) or bool(st.banner_A1), s['banner']['shown'])
add('Decline control clicked', bool(st.clicked), s['decline']['clicked'])
crawl_dec = {'refused': 'recorded', 'still_allowed': 'not_recorded_still_allowed', 'no_record_default_denied': 'not_recorded_default_denied'}.get(st.refusal_cat, st.refusal_cat)
cc_dec = s['decline']['status'].replace('recorded_marketing_only', 'recorded')
add('Decline written to Shopify as an explicit "no"', crawl_dec, cc_dec, 'crawl: refusal_cat')
add('GPC: Shopify recorded sale of data "no"', st.cp_sale_end_A2 in (False, 'False'), s['gpc']['shopify_recorded_opt_out'], 'crawl: cp_sale_end_A2 == False')
add('Default visit: marketing allowed at the first reading', st.cp_marketing_first_A0 in (True, 'True'), s['automatic_before_choice']['first_no_ms'] is None, 'both: an automatic "no" came first' if s['automatic_before_choice']['first_no_ms'] is not None else '')

# ---- vendor groups
groups = ['Google', 'TikTok', 'Meta', 'Pinterest', 'Snap', 'Microsoft', 'Reddit/other']
ccg = {g: dict(pre=False, pre_sbx=False, next_fresh=False, after_any=False, gpc=False, gpc_sbx=False) for g in groups}
for v in cc['vendors']:
    g = v['group'] if v['group'] in groups else 'Reddit/other'
    d = v['detail']
    ccg[g]['pre'] |= v['before_choice'] == 'sends'
    ccg[g]['pre_sbx'] |= v['before_choice'] == 'sends' and 'sandbox' in v['where_before']
    ccg[g]['next_fresh'] |= v['decline'] == 'not_stopped'
    ccg[g]['after_any'] |= v['decline'] in ('not_stopped', 'partly')
    ccg[g]['gpc'] |= v['gpc'] == 'not_stopped'
    ccg[g]['gpc_sbx'] |= v['gpc'] == 'not_stopped' and 'sandbox' in (d['gpc'].get('where') or [])
unload_vendors = set(rc[(rc.window == 'unload')].vendor.dropna())
for g in groups:
    c = sv.loc[g]
    if not (c.A0_any or c.A2_any or c.A1next_any or ccg[g]['pre'] or ccg[g]['gpc']):
        continue
    add(f'{g}: sent before any choice (Default)', bool(c.A0_any), ccg[g]['pre'])
    add(f'{g}: sent from the sandbox before any choice', bool(c.A0_sbx), ccg[g]['pre_sbx'])
    add(f'{g}: any sandboxed request after Decline (same page or next page)', bool(c.A1post_sbx or c.A1next_sbx), ccg[g]['after_any'])
    add(f'{g}: GPC did not stop it (sent in the GPC visit)', bool(c.A2_any), ccg[g]['gpc'])
    add(f'{g}: sandboxed under GPC', bool(c.A2_sbx), ccg[g]['gpc_sbx'])
# after-Decline windows: the crawl's residual classes (unload vs fresh page) vs ConsentCheck's
crawl_fresh = sorted(set(rc[rc.window == 'fresh_page'].pixel_type.astype(str) + ':' + rc[rc.window == 'fresh_page'].purposes.astype(str)))
cc_fresh = sorted({f"{p.get('type')}:{'|'.join(x.upper().replace('DATA SALE', 'SALE_OF_DATA') for x in p['purposes']) or 'NONE'}" for v in cc['vendors'] if v['decline'] == 'not_stopped' for p in v['pixels'] if p['id'] in (v['detail']['decline']['next_page'].get('pixels') or [])})
add('After Decline, fresh page: sending pixels (type:purposes)', ';'.join(crawl_fresh), ';'.join(cc_fresh), 'crawl: residual_composition window fresh_page')
cc_unload = sorted({v['vendor'] for v in cc['vendors'] if v['detail']['decline']['unload']['sent']})
add('After Decline, unload beacons as the page reloads (vendors)', ';'.join(sorted(unload_vendors)), ';'.join(cc_unload), 'crawl: residual_composition window unload')

# ---- pixel configuration
own = {'shopify-app-pixel', 'shopify-custom-pixel'}
crawl_px = {r.pixel_id: (r.type, r.runtimeContext, r.privacyPurposes if isinstance(r.privacyPurposes, str) else '') for r in px.itertuples()}
cc_px = {p['id']: (p['type'], p['runtime'], '|'.join(x.upper().replace('DATA SALE', 'SALE_OF_DATA') for x in p['purposes'])) for p in cc['pixels']}
add('Installed pixels (count)', len(crawl_px), len(cc_px))
add('Same pixel ids as the crawl', True, set(crawl_px) == set(cc_px), '' if set(crawl_px) == set(cc_px) else f'added {sorted(set(cc_px) - set(crawl_px))}, removed {sorted(set(crawl_px) - set(cc_px))}')
same_cfg = all(crawl_px.get(k) == cc_px.get(k) for k in set(crawl_px) & set(cc_px))
add('Same type, container and purposes for every common pixel', True, same_cfg)
crawl_np = sorted(k for k, v in crawl_px.items() if k not in own and not v[2])
cc_np = sorted(p['id'] for p in cc['pixels'] if p['flags']['no_purpose'])
add('Pixels declaring no purpose (ids)', ';'.join(crawl_np), ';'.join(cc_np))

n_agree = sum(r[3] == 'yes' for r in rows)
with open(outf, 'w') as f:
    f.write(f'# ConsentCheck test vs. the study crawl: store {sid}\n\n')
    f.write(f'ConsentCheck run: {cc["run"]["started_at"]} (one visit per condition, {len(cc["run"]["navigations"])} page loads). '
            f'Crawl: 2026-09-26, loads A0, A1 (+ next page), A2. The store is named here only by its study code.\n\n')
    f.write(f'**Agreement: {n_agree} of {len(rows)} checks.**\n\n')
    f.write('| Check | Crawl | ConsentCheck | Agree | Note |\n|---|---|---|---|---|\n')
    for r in rows:
        f.write('| ' + ' | '.join(x.replace('|', '/') for x in r) + ' |\n')
    f.write('\nTiming (Default visit, ms after the navigation started): crawl first sandboxed ad request '
            f'{st.A0_first_sbx_t:.0f}; ConsentCheck first sandboxed ad request {s["automatic_before_choice"]["first_sandboxed_ad_ms"]}, '
            f'automatic "no" from the consent tool {s["automatic_before_choice"]["first_no_ms"]}.\n')
print(f'{n_agree}/{len(rows)} checks agree -> {outf}')
