"""Region default ('allowed until choice' vs 'denied until consent') among Default-arm banner stores, by the CMP
that showed the banner. Used for one sentence in Section 5.2 of the manuscript.
Input : analysis/outputs/store_table.csv. Output: paper/tables/banner_region_by_cmp.json
"""
import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(os.path.dirname(HERE))
st = pd.read_csv(os.path.join(STUDY, 'analysis', 'outputs', 'store_table.csv'))
b = st[(st.stratum == 'main') & (st.banner_A0 == True) & st.region_optout.notna()]
out = {}
for cmp_, g in b.groupby('cmp'):
    if len(g) >= 10:
        out[cmp_] = dict(n=int(len(g)), denied=int((g.region_optout == False).sum()),
                         share_denied=round(float((g.region_optout == False).mean()), 3))
out['_all_banner_stores'] = dict(n=int(len(b)), denied=int((b.region_optout == False).sum()),
                                 share_denied=round(float((b.region_optout == False).mean()), 3))
json.dump(out, open(os.path.join(HERE, 'banner_region_by_cmp.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
