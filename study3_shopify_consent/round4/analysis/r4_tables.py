"""Round 4 B1 (expansion): build the analysis tables with the MAIN pipeline's own code, unchanged.

Steps (every definition comes from the main code; this script only redirects paths):
  1. crawl/build_tables.py --raw <crawl_dir>/raw --out <crawl_dir>      (loads.csv, requests.csv.gz, consent_*.csv,
                                                                          cmp.csv, cmp_declared.csv, pixels.csv ...)
  2. analysis/extract_probe.py  -> nested_lax_frames.csv (frames nested in LAX sandboxes), load_probe.csv
  3. analysis/extract_raw.py    -> raw_stacks.csv (relay vs page), load_scripts.csv
  4. analysis/build_store_table.py -> store_table.csv, store_vendor.csv, ad_requests.csv.gz
The main modules read their paths from analysis/common.py (CRAWL, OUT, SAMPLE); they are patched here, before the
modules are imported, and multiprocessing uses 'fork' so that worker processes inherit the patched paths.

Usage: python r4_tables.py [--crawl DIR] [--out DIR]
  defaults: --crawl round4/expansion/crawl  --out round4/analysis/outputs/expansion
  (the self-test in r4_selftest.py runs it on a copy of main-crawl raw files and compares with the main tables)
"""
import csv
import json
import multiprocessing as mp
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(STUDY, 'analysis'))


def arg(k, d):
    a = sys.argv[1:]
    return a[a.index(k) + 1] if k in a else d


CRAWL_DIR = os.path.abspath(arg('--crawl', os.path.join(STUDY, 'round4', 'expansion', 'crawl')))
OUT_DIR = os.path.abspath(arg('--out', os.path.join(HERE, 'outputs', 'expansion')))
CANDS = arg('--candidates', os.path.join(STUDY, 'round4', 'expansion', 'candidates.csv'))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    # 1. flatten raw records with the Part A table builder
    subprocess.run([sys.executable, os.path.join(STUDY, 'crawl', 'build_tables.py'), '--raw', os.path.join(CRAWL_DIR, 'raw'), '--out', CRAWL_DIR],
                   check=True, stdout=subprocess.DEVNULL)
    # column shim: build_tables.py writes the union of keys seen, so a small crawl can lack a column that the main
    # tables have (e.g. consent_states.error when no reading failed). Add such columns empty; values are untouched.
    import pandas as pd
    for fn in ('loads.csv', 'consent_states.csv', 'consent_events.csv', 'cmp.csv', 'cmp_declared.csv', 'pixels.csv', 'requests.csv.gz', 'gpc_checks.csv'):
        ref = os.path.join(STUDY, 'crawl', fn)
        new_ = os.path.join(CRAWL_DIR, fn)
        if not os.path.exists(new_):
            continue
        hdr = pd.read_csv(ref, nrows=0).columns
        df = pd.read_csv(new_, low_memory=False)
        miss = [c for c in hdr if c not in df.columns]
        if miss:
            for c in miss:
                df[c] = pd.NA
            df.to_csv(new_, index=False, compression='gzip' if fn.endswith('.gz') else None)
            print('column shim', fn, miss)
    # build_store_table reads cmp_signatures.json from CRAWL: a byte copy of the Part A file (never edited)
    sig = os.path.join(CRAWL_DIR, 'cmp_signatures.json')
    if not os.path.exists(sig):
        shutil.copyfile(os.path.join(STUDY, 'crawl', 'cmp_signatures.json'), sig)
    # sample file stand-in (store_id, domain, tranco_rank, bucket, weight) and an empty creator stratum
    smp = os.path.join(OUT_DIR, '_sample')
    os.makedirs(smp, exist_ok=True)
    rows = []
    if os.path.exists(CANDS):
        for r in csv.DictReader(open(CANDS)):
            if 'store_id' in r:
                rows.append(dict(store_id=r['store_id'], domain=r['domain'], tranco_rank=r.get('rank') or r.get('tranco_rank'), bucket='200k-1M',
                                 weight=r.get('weight') or 1.0))
    with open(os.path.join(smp, 'sample.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['store_id', 'domain', 'tranco_rank', 'bucket', 'weight'])
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(smp, 'creator_stratum.csv'), 'w') as f:
        f.write('store_id,domain,landing_url,token,token_level\n')
    # 2-4. main analysis modules with redirected paths
    mp.set_start_method('fork', force=True)
    import common
    common.CRAWL, common.OUT, common.SAMPLE = CRAWL_DIR, OUT_DIR, smp
    import extract_probe
    extract_probe.main()
    import extract_raw
    extract_raw.main()
    import build_store_table
    build_store_table.main()
    json.dump(dict(crawl_dir=CRAWL_DIR, out_dir=OUT_DIR, candidates=CANDS, n_sample_rows=len(rows)), open(os.path.join(OUT_DIR, '_tables_meta.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
