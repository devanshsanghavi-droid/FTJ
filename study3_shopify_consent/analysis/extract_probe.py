"""Pull three things the referee reports asked for from the raw load records (crawl/raw/<load_id>.json.gz).
No new traffic; reads saved evidence only (added 2026-09-26, referee revision, review/referee_figure_fixes.md).

Outputs (analysis/outputs/):
  load_probe.csv         one row per load: what the page saw of our browser (navigator.webdriver, a 'HeadlessChrome'
                         user agent), the Pandectes DOM state and declared v5 regions (for the CMP automation rule of
                         referee 1, M1), Pandectes v4 geolocation flags, and the DOM state of every detected CMP.
  worker_pauses.csv      one row per worker target: the time from auto-attach to resume. The crawler attaches with
                         waitForDebuggerOnStart, so every worker waits until its network capture is enabled (referee 1, m6).
  nested_lax_frames.csv  one row per (load, frame URL) whose frame sits INSIDE a Shopify LAX sandbox iframe (a parent,
                         grandparent ... has a LAX sandbox URL) without being one itself; the crawler labelled such frames
                         'subframe' by their own URL only (referee 1, m2). lax_pixel_id is the enclosing sandbox's pixel.
Resumable: finished loads are cached in outputs/_probe_cache/<load_id>.json.
"""
import gzip
import json
import os
import re
from multiprocessing import Pool

import pandas as pd

from common import CRAWL, OUT

CACHE = os.path.join(OUT, '_probe_cache')
os.makedirs(CACHE, exist_ok=True)
LAX = re.compile(r'/(web-pixels|wpm)@[^/]+/.*/sandbox/')      # same rule as crawl/crawl.js (frame_url_loose)
PIX = re.compile(r'web-pixel-(\d+)@')
STRICT = re.compile(r'/web-pixel-\d+@[^/]+/sandbox/worker\.modern\.js')


def work(lid):
    cf = os.path.join(CACHE, lid + '.json')
    if os.path.exists(cf):
        return json.load(open(cf))
    d = json.load(gzip.open(os.path.join(CRAWL, 'raw', lid + '.json.gz')))
    pr = d.get('probe') or {}
    ua = str(pr.get('ua') or '')
    cmpd = pr.get('cmp') or {}
    dec = pr.get('declared') or {}
    p5 = dec.get('pandectes_v5') or {}
    reg = p5.get('regions') or {}
    vis = reg.get('visible')
    strict = reg.get('strict') or []
    p4 = dec.get('pandectes') or {}
    geo = p4.get('geolocation') or {}
    row = dict(load_id=lid, store_id=d.get('store_id'), arm=d.get('arm'), browser=d.get('browser'),
               has_probe=bool(pr), webdriver=(str(pr.get('webdriver')) == 'True') if 'webdriver' in pr else None,
               ua_headlesschrome=('headlesschrome' in ua.lower()) if ua else None, ua=ua[:160],
               pandectes_dom=(cmpd.get('pandectes') or {}).get('dom'),
               pandectes_v5=bool(p5), p5_visible_here=(vis == '*' or (isinstance(vis, list) and 'USCA' in vis)) if p5 else None,
               p5_ca_strict=(strict == '*' or 'USCA' in strict) if p5 else None,
               p4=bool(p4), p4_global_visibility=geo.get('globalVisibility'), p4_ca_only=geo.get('caOnly'), p4_default_blocked=p4.get('defaultBlocked'),
               cmp_dom=json.dumps({k: (v or {}).get('dom') for k, v in cmpd.items()}, sort_keys=True))
    # workers: auto-attach -> resume
    tg = d.get('targets') or []
    tg = tg.values() if isinstance(tg, dict) else tg
    pauses = []
    for x in tg:
        if isinstance(x, dict) and x.get('type') in ('worker', 'shared_worker', 'service_worker') and x.get('t_attach') is not None \
                and x.get('t_resume') is not None:
            pauses.append(dict(load_id=lid, type=x.get('type'), strict=bool(STRICT.search(x.get('url') or '')), waiting=x.get('waiting'),
                               t_attach=x['t_attach'], t_resume=x['t_resume'], pause_ms=x['t_resume'] - x['t_attach']))
    # frames nested inside a LAX sandbox
    fr = d.get('frames') or {}
    nested = {}
    for fid, f in fr.items():
        u = (f or {}).get('url') or ''
        if LAX.search(u):
            continue
        seen, p, depth = set(), (f or {}).get('parent'), 0
        while p and p not in seen:
            seen.add(p)
            depth += 1
            pu = (fr.get(p) or {}).get('url') or ''
            if LAX.search(pu):
                m = PIX.search(pu)
                k = nested.setdefault(u, dict(load_id=lid, frame_url=u, lax_url=pu[:300], lax_pixel_id=m.group(1) if m else None, depth=depth,
                                              n_frames=0, n_pixels=set()))
                k['n_frames'] += 1
                if m:
                    k['n_pixels'].add(m.group(1))
                break
            p = (fr.get(p) or {}).get('parent')
    nrows = []
    for v in nested.values():
        v['n_pixels'] = len(v['n_pixels'])
        nrows.append(v)
    # URL shared by a nested and a non-nested frame (ambiguous for a request that only carries the frame URL)
    urls_top = {((f or {}).get('url') or '') for fid, f in fr.items()}
    for v in nrows:
        same = [fid for fid, f in fr.items() if ((f or {}).get('url') or '') == v['frame_url']]
        v['ambiguous'] = len(same) > v['n_frames']
    res = dict(probe=row, pauses=pauses, nested=nrows, n_urls=len(urls_top))
    json.dump(res, open(cf, 'w'))
    return res


def main():
    lids = sorted(f[:-8] for f in os.listdir(os.path.join(CRAWL, 'raw')) if f.endswith('.json.gz'))
    probe, pauses, nested = [], [], []
    done = 0
    with Pool(6) as pool:
        for res in pool.imap_unordered(work, lids, chunksize=8):
            probe.append(res['probe'])
            pauses += res['pauses']
            nested += res['nested']
            done += 1
            if done % 1000 == 0:
                print('loads', done, 'of', len(lids), flush=True)
    pd.DataFrame(probe).sort_values('load_id').to_csv(os.path.join(OUT, 'load_probe.csv'), index=False)
    # final gate (2026-09-26): loads arrive in any order from imap_unordered; a stable sort by load makes the file byte-reproducible
    pd.DataFrame(pauses).sort_values('load_id', kind='stable').to_csv(os.path.join(OUT, 'worker_pauses.csv'), index=False)
    cols = ['load_id', 'frame_url', 'lax_url', 'lax_pixel_id', 'depth', 'n_frames', 'n_pixels', 'ambiguous']
    pd.DataFrame(nested, columns=cols).sort_values('load_id', kind='stable').to_csv(os.path.join(OUT, 'nested_lax_frames.csv'), index=False)
    print('loads', len(probe), 'worker targets', len(pauses), 'nested frame URLs', len(nested))


if __name__ == '__main__':
    main()
