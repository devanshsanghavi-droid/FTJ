"""Replay every captured main-sample store of the study crawl through ConsentCheck's analysis (offline, read-only:
test/replay_crawl.js) and compare its store-level verdicts with analysis/outputs/store_table.csv.
    python3 test/replay_agreement.py            -> test/replay_agreement.txt
This validates ConsentCheck's analysis code against the study pipeline; it does not visit any site."""
import json
import os
import subprocess
import tempfile

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
st = pd.read_csv(os.path.join(STUDY, 'analysis', 'outputs', 'store_table.csv'), low_memory=False).set_index('store_id')
S = st[st.stratum == 'main']
with tempfile.TemporaryDirectory() as td:
    csv = os.path.join(td, 'replay.csv')
    subprocess.run(['node', os.path.join(HERE, 'replay_crawl.js'), *S.index.tolist(), '--csv', csv], check=True, stdout=subprocess.DEVNULL)
    r = pd.read_csv(csv).set_index('store_id').loc[S.index]
px = pd.read_csv(os.path.join(STUDY, 'crawl', 'pixels.csv'), dtype=str)
npc = px[~px.pixel_id.isin({'shopify-app-pixel', 'shopify-custom-pixel'}) & px.privacyPurposes.isna()].groupby('store_id').size()


def anyg(j, k):
    return any(v[k] for v in json.loads(j).values())


cc = {k: r.vg.map(lambda j, k=k: anyg(j, k)) for k in ['pre', 'pre_sbx', 'gpc', 'decl']}
cl = S.clicked == True
k = S.cp_sale_end_A2.notna()
res = [
    ('Ad vendor sent data before any choice (crawl A0_any)', cc['pre'] == S.A0_any),
    ('... from the sandbox (A0_sbx)', cc['pre_sbx'] == S.A0_sbx),
    ('Ad vendor sent data under GPC (A2_any)', cc['gpc'] == S.A2_any),
    ('Clicked stores: ad data on the page after Decline (A1next_any)', cc['decl'][cl] == S.A1next_any[cl]),
    ('Clicked stores: Decline written to Shopify as "no" (refusal_cat)', r.decline_status.isin(['recorded', 'recorded_marketing_only'])[cl] == (S.refusal_cat[cl] == 'refused')),
    ("Shopify's default allows marketing (region_optout)", r.region_allows.astype(str) == S.region_optout.astype(str)),
    ('GPC recorded by Shopify, where the crawl read the API (cp_sale_end_A2)', r.gpc_recorded[k].astype(str) == (S.cp_sale_end_A2[k].astype(str) == 'False').astype(str)),
    ('Number of pixels declaring no purpose (pixels.csv)', r.n_nopurpose == npc.reindex(r.index).fillna(0).astype(int)),
]
lines = ['ConsentCheck analysis replayed on the study crawl (main sample, 1,362 captured stores; offline, no site visited)', '']
for name, v in res:
    lines.append(f'{name:75s} {int(v.sum()):5d} / {len(v):5d}  ({100 * v.mean():.1f}%)')
lines += ['', 'Known differences: (1) replayed crawl records carry no frame/worker ids, so leftover requests of an old sandbox after',
          'the reload count as "fresh page" (a live ConsentCheck run separates them); (2) where the page never loaded Shopify\'s',
          f'Customer Privacy API ({int((~k).sum())} GPC loads) the crawl has no reading, while ConsentCheck also reads the Server-Timing',
          'consent header; (3) the region default can differ on a few stores whose consent header came from an edge cache.']
open(os.path.join(HERE, 'replay_agreement.txt'), 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
