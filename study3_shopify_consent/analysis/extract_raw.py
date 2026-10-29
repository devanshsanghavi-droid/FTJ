"""Pull the per-request initiator stacks and per-load script timings that the review asked for from the raw
load records (crawl/raw/<load_id>.json.gz). No new traffic; reads saved evidence only.

Outputs (analysis/outputs/):
  raw_stacks.csv   one row per ad request that needs its stack:
                     * every ad request labelled wpm_main_proxy (any arm), to decide whether it is a real relay of a
                       sandboxed pixel's beacon (stack holds only Shopify / store scripts) or a main-thread tag that
                       merely reacts to Shopify's event bus (a vendor library or another app script is in the stack);
                     * every sandboxed ad request of a Decline (A1) load after the click (same page and next page),
                       to say whether it was issued by the pixel's own code under Shopify's sandbox bootstrap or by
                       the vendor's library.
                   columns: load_id, i, stack_class, n_urls, has_vendor_lib, has_other_3p, has_wpm_code, first_url
  load_scripts.csv one row per load: t of the first consent-tracking-api.js request (Shopify's Customer Privacy API
                   script; a lower bound for any consent write made through it) and t_obs_end.
Resumable: finished loads are cached in outputs/_extract_cache/*.json and skipped on rerun.
"""
import gzip
import json
import os
import re
import sys
from multiprocessing import Pool
from urllib.parse import urlparse

import pandas as pd

from common import CRAWL, OUT, SANDBOX, load_tables

CACHE = os.path.join(OUT, '_extract_cache')
os.makedirs(CACHE, exist_ok=True)
SHOP = re.compile(r'(/cdn/wpm/|shopifycloud|/web-pixels|cdn\.shopify\.com/s/|/cdn/shop/|/wpm@|/checkouts/)')
WPM_CODE = re.compile(r'(/web-pixels|/wpm@|/cdn/wpm/)')
VENDORLIB = re.compile(r'(googletagmanager|google-analytics|googleadservices|googlesyndication|doubleclick|connect\.facebook|fbevents|'
                       r'analytics\.tiktok|pinimg|pintrk|sc-static|snapchat|bat\.bing|clarity\.ms|redditstatic|reddit|static\.ads-twitter|'
                       r'licdn|linkedin|applovin|axon|adroll|criteo|taboola|stackadapt|tvsquared|tvscientific|amazon-adsystem|'
                       r's\.pinimg|ct\.pinterest|snap\.licdn|tiktok)')


def classify(stack, dom):
    urls = [s for s in stack if s]
    if not urls:
        return 'no_stack', 0, False, False, False, ''
    host_of = lambda s: (urlparse(s).hostname or '').lower()
    d = dom.lower().replace('www.', '')

    def own(s):
        h = host_of(s).replace('www.', '')
        return h == d or h.endswith('.' + d) or s.startswith('blob:') or s.startswith('about:')
    other = [s for s in urls if not SHOP.search(s) and not own(s)]
    vlib = [s for s in other if VENDORLIB.search(s)]
    wpm = any(WPM_CODE.search(s) for s in urls)
    if not other:
        k = 'shopify_or_store_only'
    elif vlib:
        k = 'vendor_library'
    else:
        k = 'other_third_party'
    return k, len(urls), bool(vlib), bool(other) and not vlib, wpm, urls[0][:160]


def work(args):
    lid, wanted = args
    cf = os.path.join(CACHE, lid + '.json')
    if os.path.exists(cf):
        c = json.load(open(cf))
        # reuse the cache only if it holds every wanted request (the referee revision made frames nested in a LAX
        # sandbox sandboxed, so some loads now need more stacks)
        if set(wanted) <= {r['i'] for r in c['rows']}:
            return c
    fn = os.path.join(CRAWL, 'raw', lid + '.json.gz')
    d = json.load(gzip.open(fn))
    dom = d.get('domain') or ''
    rows = []
    want = set(wanted)
    t_ct = None
    for q in d.get('requests', []):
        u = q.get('url') or ''
        if 'consent-tracking-api' in u and (t_ct is None or (q.get('t') is not None and q['t'] < t_ct)):
            t_ct = q.get('t')
        if q.get('i') in want:
            st = ([q.get('ini_url')] if q.get('ini_url') else []) + (q.get('ini_stack') or [])
            k, n, vl, o3, wpm, first = classify(st, dom)
            rows.append(dict(load_id=lid, i=q['i'], stack_class=k, n_urls=n, has_vendor_lib=vl, has_other_3p=o3, has_wpm_code=wpm,
                             first_url=first))
    res = dict(rows=rows, meta=dict(load_id=lid, t_ctapi=t_ct, t_obs_end=d.get('t_obs_end')))
    json.dump(res, open(cf, 'w'))
    return res


def main():
    L, R, captured = load_tables()
    ok = L[L.ok & L.captured]
    ad = R[R.ad & R.load_id.isin(ok.load_id)]
    need = ad[(ad.origin == 'wpm_main_proxy') | ((ad.arm == 'A1') & ad.phase.isin(['post_click', 'next_page']) & ad.origin.isin(SANDBOX))]
    by_load = need.groupby('load_id').i.apply(lambda s: [int(x) for x in s]).to_dict()
    jobs = [(lid, by_load.get(lid, [])) for lid in ok.load_id]
    rows, meta = [], []
    done = 0
    with Pool(6) as pool:
        for res in pool.imap_unordered(work, jobs, chunksize=8):
            rows += res['rows']
            meta.append(res['meta'])
            done += 1
            if done % 500 == 0:
                print('loads', done, 'of', len(jobs), flush=True)
    # final gate (2026-09-26): loads arrive in any order from imap_unordered; sorting makes both files byte-reproducible
    pd.DataFrame(rows).sort_values(['load_id', 'i'], kind='stable').to_csv(os.path.join(OUT, 'raw_stacks.csv'), index=False)
    pd.DataFrame(meta).sort_values('load_id', kind='stable').to_csv(os.path.join(OUT, 'load_scripts.csv'), index=False)
    print('raw_stacks', len(rows), 'of', len(need), 'requests; loads', len(meta))


if __name__ == '__main__':
    main()
