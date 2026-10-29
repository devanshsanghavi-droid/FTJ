"""Failure / blocking breakdown, retry outcome, run segments and banner/decline/CMP counts for CRAWL_NOTES.md.
Writes failure_breakdown.json."""
import json, os, glob, gzip, collections
import pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
L = pd.read_csv(os.path.join(H, 'loads.csv'), low_memory=False)
out = {}
L['ok'] = (L.goto_status.fillna(0).between(200, 399)) & (L.has_shopify == True) & (L.blocked_hint != True) & (L.n_requests.fillna(0) > 20)
bad = L[~L.ok].copy()
def reason(r):
    e = str(r.goto_error or '')
    if 'NAME_NOT_RESOLVED' in e: return 'dns_not_resolved'
    if 'TIMED_OUT' in e or 'Timeout' in e: return 'timeout'
    if e and e != 'nan': return 'other_network_error:' + e[:40]
    if r.goto_status in (401, 403, 429, 503): return f'http_{int(r.goto_status)}'
    if r.offsite_redirect == True and r.has_shopify is not True: return 'redirect_off_site:' + str(r.final_host)
    if r.goto_status == 404: return 'http_404_product_gone'
    if r.goto_status == 402: return 'http_402_store_unavailable'
    if r.has_shopify is not True: return 'no_window_Shopify'
    if r.blocked_hint == True: return 'bot_wall'
    return 'other'
bad['reason'] = bad.apply(reason, axis=1)
out['not_ok_loads'] = int(len(bad))
out['not_ok_by_reason'] = {k: int(v) for k, v in bad.reason.map(lambda x: x.split(':')[0]).value_counts().items()}
out['offsite_redirect_hosts'] = {k: int(v) for k, v in bad[bad.reason.str.startswith('redirect_off_site')].final_host.value_counts().items()}
out['not_ok_stores_any_arm'] = int(bad.store_id.nunique())
out['blocked_like_stores(http_403/429/503 or off-site redirect or bot wall)'] = int(bad[bad.reason.str.match(r'http_40[13]|http_429|http_503|redirect_off_site|bot_wall')].store_id.nunique())
# retry outcome
retried = [os.path.basename(f).replace('.json.gz', '') for f in glob.glob(os.path.join(H, 'raw_failed_attempt1', '*.json.gz'))]
out['retried_loads'] = len(retried)
out['retried_ok_now'] = int(L[L.load_id.isin(retried)].ok.sum())
# run segments from the status log
S = [json.loads(x) for x in open(os.path.join(H, 'logs', 'crawl_status.jsonl'))]
seg = collections.Counter()
for s in S:
    t = s['at']
    seg['conc6_first_segment' if t < '2026-09-26T07:34' else ('conc10_coordinator_segment' if t < '2026-09-26T09:59' else 'conc6_retry_pass')] += 1
out['status_log_lines_by_segment'] = dict(seg)
out['first_load_at'] = min(s['at'] for s in S); out['last_load_at'] = max(s['at'] for s in S)
# banners, decline, CMPs (main + creator, ok loads)
ok = L[L.ok]
a0 = ok[ok.arm == 'A0']; a1 = ok[ok.arm == 'A1']
out['A0_ok_loads'] = int(len(a0)); out['A0_banner_visible'] = int((a0.banner_visible == True).sum())
out['A0_banner_by_cmp'] = {k: int(v) for k, v in a0[a0.banner_visible == True].banner_cmp.fillna('generic_detector').value_counts().items()}
out['A0_cmp_detected_stores'] = {k: int(v) for k, v in a0.cmps_detected.dropna().str.split('|').explode().value_counts().items()}
out['A0_no_cmp_detected'] = int(a0.cmps_detected.isna().sum())
out['A0_region_mode'] = {str(k): int(v) for k, v in a0.cmp_allow_m.value_counts(dropna=False).items()}
out['A0_cmp_header_region'] = {str(k): int(v) for k, v in a0.cmp_region.value_counts(dropna=False).head(10).items()}
out['A1_ok_loads'] = int(len(a1)); out['A1_banner_found'] = int((a1.a1_banner_found == True).sum())
out['A1_reject_found'] = int((a1.reject_found == True).sum()); out['A1_no_decline_option'] = int((a1.no_decline_option == True).sum())
out['A1_click_method'] = {k: int(v) for k, v in a1.click_method.value_counts().items()}
out['A1_banner_still_visible_2s_after_click'] = int((a1.banner_still_after_click == True).sum())
out['A1_reject_how'] = {k: int(v) for k, v in a1.reject_how.fillna('').str.split(':').str[0].value_counts().items() if k}
out['A1_reject_text_top'] = {k: int(v) for k, v in a1.reject_text.value_counts().head(12).items()}
out['A1_no_decline_by_cmp'] = {k: int(v) for k, v in a1[a1.no_decline_option == True].banner_cmp.fillna('generic_detector').value_counts().items()}
out['wpm_config_found_ok_loads'] = f"{int((ok.wpm_config_found == True).sum())}/{len(ok)}"
out['nostra_ok_A0'] = int((a0.nostra == True).sum())
out['cf_cache_hit_A0'] = int((a0.cf_cache_status == 'HIT').sum())
out['screenshots'] = len(glob.glob(os.path.join(H, 'screenshots', '*.jpg')))
json.dump(out, open(os.path.join(H, 'failure_breakdown.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
