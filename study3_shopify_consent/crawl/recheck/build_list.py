"""Store list for the final-audit re-check crawl (2026-09-26).
Groups (main sample, stores captured in all three base arms):
  flagged   - Shopify's shouldShowBanner() was true at some A0 reading but the detector found no banner in A0 (the 80 of
              review/review_methods_evidence/banner_recall_proxy.txt)
  random_nb - a seeded random sample of 30 stores with no banner detected in A0 or A1, outside 'flagged'
  blocklist - the 21 stores whose readable CMP blocklist declared an ad vendor blocked before any choice (Fig. 4a)
Writes recheck_list.csv (store_id, groups, url) using the exact landing URL of the main crawl (crawl/plan.json).
"""
import json, os, random
import pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
ST = os.path.join(H, '..', '..')
m = pd.read_csv(os.path.join(ST, 'analysis', 'outputs', 'store_table.csv'))
m = m[m.stratum == 'main'].set_index('store_id')
cs = pd.read_csv(os.path.join(ST, 'crawl', 'consent_states.csv'), usecols=['store_id', 'arm', 'shouldShowBanner'])
ssb = cs[(cs.arm == 'A0') & (cs.shouldShowBanner.astype(str) == 'True')].store_id.unique()
flagged = sorted(s for s in ssb if s in m.index and m.loc[s, 'banner_A0'] == False)
nb = sorted(s for s in m.index if m.loc[s, 'banner_A0'] == False and m.loc[s, 'banner_A1'] == False and s not in set(flagged))
random_nb = sorted(random.Random(20260927).sample(nb, 30))
db = pd.read_csv(os.path.join(ST, 'analysis', 'outputs', 'fig4c_declared_blocked_pairs.csv'))
blocklist = sorted(db.store_id.unique())
plan = {s['store_id']: s for s in json.load(open(os.path.join(ST, 'crawl', 'plan.json')))['stores']}
rows = {}
for g, ids in (('flagged', flagged), ('random_nb', random_nb), ('blocklist', blocklist)):
    for s in ids:
        rows.setdefault(s, []).append(g)
out = pd.DataFrame([dict(store_id=s, groups='|'.join(g), domain=plan[s]['domain'], url=plan[s]['url']) for s, g in sorted(rows.items())])
out.to_csv(os.path.join(H, 'recheck_list.csv'), index=False)
print('main stores', len(m), '| flagged', len(flagged), '| no-banner pool', len(nb), '| random_nb', len(random_nb), '| blocklist', len(blocklist), '| unique stores', len(out))
print('flagged by cmp', m.loc[flagged, 'cmp'].value_counts().to_dict())
