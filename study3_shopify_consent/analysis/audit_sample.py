"""Draw the seeded screenshot-audit sample for Figure S4 (banner detection, first-layer reject option,
Decline-click success). Frame: main-sample captured stores whose Decline load found a banner (screenshots
exist only for those). Strata: clicked (pre + post screenshots) and no-reject-option (pre only).
Writes outputs/audit_sample.csv with the crawler's own labels; the visual labels are entered in
audit_labels.csv (one row per sampled load) after looking at each screenshot.
"""
import os

import numpy as np
import pandas as pd

from common import CRAWL, OUT, SEED

N_CLICKED = 36
N_NOREJECT = 18


def main():
    st = pd.read_csv(os.path.join(OUT, 'store_table.csv')).set_index('store_id')
    m = st[(st.stratum == 'main') & st.banner_A1]
    shots = set(os.listdir(os.path.join(CRAWL, 'screenshots')))
    rng = np.random.default_rng(SEED)
    clicked = sorted(s for s in m[m.clicked].index if f'{s}__A1__pre.jpg' in shots and f'{s}__A1__post.jpg' in shots)
    norej = sorted(s for s in m[m.no_decline_option].index if f'{s}__A1__pre.jpg' in shots)
    a = list(rng.choice(clicked, N_CLICKED, replace=False))
    b = list(rng.choice(norej, N_NOREJECT, replace=False))
    L = pd.read_csv(os.path.join(CRAWL, 'loads.csv'), low_memory=False).set_index('load_id')
    rows = []
    for s in sorted(a) + sorted(b):
        l = L.loc[f'{s}__A1']
        rows.append(dict(store_id=s, stratum='clicked' if s in a else 'no_reject_option', cmp=st.loc[s, 'cmp'],
                         crawler_banner=True, crawler_reject_found=bool(l.reject_found == True), crawler_reject_text=l.reject_text,
                         crawler_click_method=l.click_method, crawler_banner_still_after_click=l.banner_still_after_click,
                         pre=f'{s}__A1__pre.jpg', post=f'{s}__A1__post.jpg' if s in a else ''))
    pd.DataFrame(rows).to_csv(os.path.join(OUT, 'audit_sample.csv'), index=False)
    print(len(clicked), len(norej), len(rows))
    print(pd.DataFrame(rows)[['store_id', 'stratum', 'cmp', 'crawler_reject_text', 'crawler_banner_still_after_click']].to_string())


if __name__ == '__main__':
    main()
