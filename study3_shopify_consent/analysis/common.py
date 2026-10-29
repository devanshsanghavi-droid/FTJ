"""Shared loading, definitions and statistics helpers for the Study 3 analysis.

Definitions (identical to crawl/summarize_crawl.py so headline numbers reproduce):
  ok load      HTTP 2xx/3xx, window.Shopify present, no blocking hint, > 20 requests
  captured     store has an ok load in all three base arms A0 (Default), A1 (Decline), A2 (GPC)
  ad request   request to a vendor with is_advertising == True (crawl/vendor_endpoints.json)
  sandboxed    request origin strict_worker (WPM STRICT web worker), lax_iframe (WPM LAX iframe) or lax_nested (a frame
               nested inside a LAX iframe; referee revision 2026-09-26, outputs/nested_lax_frames.csv from extract_probe.py)
  pre-choice   every A0 request; A1 requests before the Decline click
  preflight    CORS preflights (method OPTIONS) are not ad requests: CDP reports the preflight of a worker's fetch in the page
               session, where it was labelled main_thread; the real request that follows is counted (referee revision)
"""
import json
import math
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.normpath(os.path.join(HERE, '..'))
CRAWL = os.path.join(STUDY, 'crawl')
SAMPLE = os.path.join(STUDY, 'sample')
OUT = os.path.join(HERE, 'outputs')
os.makedirs(OUT, exist_ok=True)

SANDBOX = {'strict_worker', 'lax_iframe', 'lax_nested'}
BASE_ARMS = ['A0', 'A1', 'A2']
PRECHOICE_PHASES = ['pre_banner', 'banner_prechoice', 'pre_choice']
SEED = 20260926

# Figure vendor groups (FIGURE_PLAN.md fixed order); the crawl's figure_color_group column
VENDOR_GROUPS = ['Google', 'TikTok', 'Meta', 'Pinterest', 'Snap', 'Microsoft', 'Reddit/other']

# Origin classes (grey encodings; sandbox never red). Revised after review: a request the crawler labelled
# wpm_main_proxy (Shopify's manager bundle somewhere in the initiator stack) counts as RELAYED by Shopify only when
# every script in its stack is a Shopify or store script (outputs/raw_stacks.csv, stack_class
# 'shopify_or_store_only'); otherwise it is a main-thread tag reacting to Shopify's event bus and is visible to a
# blocker, so it joins the ordinary page scripts. Other iframes / workers are merged into 'page' as well.
ORIGIN_CLASSES = ['sandbox', 'relay', 'open_pixel', 'page']


def origin_class(origin, stack_class):
    if origin in SANDBOX:
        return 'sandbox'
    if origin == 'wpm_main_proxy':
        return 'relay' if stack_class == 'shopify_or_store_only' else 'page'
    if origin in ('open_pixel', 'open_pixel_chain'):
        return 'open_pixel'
    return 'page'


# ---- consent / opt-out signals carried in the request URL (review: Google Consent Mode and vendor flags) ----
import re as _re
_GCS = _re.compile(r'[?&]gcs=([^&]+)')
_GCD = _re.compile(r'[?&]gcd=([^&]+)')
_DENIED_GCD = set('pqmu')   # gcd letters whose final state is 'denied' (default x update grid)


def consent_flags(url, vendor):
    """Refusal signals in a vendor request URL. Returns (gcs, flag_any, flag_kind).
    Google: gcs=G10x (ad_storage denied), gcd ad_storage or ad_personalization finally denied, npa=1, rdp=1,
    us_privacy with the opt-out-of-sale position 'Y'. Microsoft UET: asc=D. Reddit: dpm=LDU. URL only (bodies are
    not in the request table), so body-borne flags such as Meta's data-processing options are not seen."""
    u = url if isinstance(url, str) else ''
    kinds = []
    g = _GCS.search(u)
    gcs = g.group(1) if g else ''
    if gcs.startswith('G10'):
        kinds.append('gcs_ad_denied')
    d = _GCD.search(u)
    if d:
        letters = _re.findall(r'[A-Za-z]', d.group(1))
        if len(letters) >= 4 and (letters[0] in _DENIED_GCD or letters[3] in _DENIED_GCD):
            kinds.append('gcd_denied')
    if _re.search(r'[?&]npa=1(?:&|$)', u):
        kinds.append('npa')
    if _re.search(r'[?&]rdp=1(?:&|$)', u):
        kinds.append('rdp')
    m = _re.search(r'[?&]us_privacy=1.(.)', u)
    if m and m.group(1) == 'Y':
        kinds.append('us_privacy_optout')
    if vendor == 'microsoft_uet' and _re.search(r'[?&]asc=D(?:&|$)', u):
        kinds.append('uet_asc_denied')
    if vendor == 'reddit' and _re.search(r'[?&]dpm=LDU', u):
        kinds.append('reddit_ldu')
    return gcs, bool(kinds), '|'.join(kinds)


def wilson(k, n, z=1.959964):
    k, n = int(k), int(n)
    if n == 0:
        return dict(k=k, n=n, p=None, lo=None, hi=None)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return dict(k=k, n=n, p=p, lo=max(0.0, c - h), hi=min(1.0, c + h))


def attribute_nested(R):
    """Relabel requests from frames nested inside a Shopify LAX sandbox iframe (origin 'subframe' in the crawl, which
    looked only at a frame's own URL) as origin 'lax_nested', and join them to the enclosing sandbox's pixel
    configuration. A frame URL that the load also used for a frame outside any sandbox is ambiguous and keeps its
    'subframe' label (conservative). Needs outputs/nested_lax_frames.csv (extract_probe.py); unchanged without it."""
    fn = os.path.join(OUT, 'nested_lax_frames.csv')
    R['origin_crawl'] = R.origin
    if not os.path.exists(fn):
        return R
    N = pd.read_csv(fn, dtype={'lax_pixel_id': str})
    N = N[~N.ambiguous.astype(bool) & N.lax_pixel_id.notna() & (N.n_pixels <= 1)]
    key = dict(zip(zip(N.load_id, N.frame_url), N.lax_pixel_id))
    sel = (R.origin == 'subframe') & pd.Series([(l, u) in key for l, u in zip(R.load_id, R.frame_url)], index=R.index)
    if not sel.any():
        return R
    PX = pd.read_csv(os.path.join(CRAWL, 'pixels.csv'), dtype={'pixel_id': str, 'apiClientId': str}).drop_duplicates(['store_id', 'pixel_id'])
    px = PX.set_index(['store_id', 'pixel_id'])
    R['pixel_id'] = R.pixel_id.astype(object)
    for i in R.index[sel]:
        pid = key[(R.at[i, 'load_id'], R.at[i, 'frame_url'])]
        R.at[i, 'origin'] = 'lax_nested'
        R.at[i, 'origin_evidence'] = 'frame_parent_lax'
        R.at[i, 'pixel_id'] = pid
        k = (R.at[i, 'store_id'], pid)
        if k in px.index:
            p = px.loc[k]
            R.at[i, 'pixel_matched'] = True
            R.at[i, 'pixel_type'] = p['type'] if isinstance(p['type'], str) else ''
            R.at[i, 'pixel_api'] = p['apiClientId'] if isinstance(p['apiClientId'], str) and p['apiClientId'] != 'nan' else ''
            R.at[i, 'pixel_vendor'] = p['vendor'] if isinstance(p['vendor'], str) else ''
            R.at[i, 'pixel_rc'] = p['runtimeContext'] if isinstance(p['runtimeContext'], str) else ''
            R.at[i, 'pixel_name'] = str(p['name'])[:60] if isinstance(p['name'], str) else ''
            R.at[i, 'pixel_purposes'] = p['privacyPurposes'] if isinstance(p['privacyPurposes'], str) and p['privacyPurposes'] else 'NONE'
        else:
            R.at[i, 'pixel_matched'] = False
    return R


def load_tables():
    L = pd.read_csv(os.path.join(CRAWL, 'loads.csv'), low_memory=False)
    L['ok'] = (L.goto_status.fillna(0).between(200, 399)) & (L.has_shopify == True) & (L.blocked_hint != True) & (L.n_requests.fillna(0) > 20)
    okset = L[L.ok].groupby('store_id').arm.apply(set)
    captured = sorted(s for s, arms in okset.items() if set(BASE_ARMS) <= arms)
    L['captured'] = L.store_id.isin(captured)
    R = pd.read_csv(os.path.join(CRAWL, 'requests.csv.gz'), low_memory=False)
    R = attribute_nested(R)
    R['preflight'] = R.method.astype(str).str.upper() == 'OPTIONS'
    R['sandbox'] = R.origin.isin(SANDBOX)
    R['ad'] = (R.is_advertising == True) & ~R.preflight
    R['vgroup'] = R.color_group.fillna('')
    R['beacon'] = R.kind.fillna('') != 'library'
    return L, R, captured


def load_sample():
    S = pd.read_csv(os.path.join(SAMPLE, 'sample.csv'))
    C = pd.read_csv(os.path.join(SAMPLE, 'creator_stratum.csv'))
    return S, C


def primary_cmp(L):
    """Per load: the CMP that showed the banner if known, else the single strongly detected CMP, else
    'multiple' / 'none'. Returns a Series indexed like L."""
    def f(r):
        bc = r.banner_cmp if isinstance(r.banner_cmp, str) and r.banner_cmp else ''
        det = [x for x in str(r.cmps_detected).split('|') if x and x != 'nan']
        if bc and bc != 'generic':
            return bc
        if len(det) == 1:
            return det[0]
        if len(det) > 1:
            # prefer a non-Shopify-native CMP when several are present (native banner is often a fallback)
            nn = [d for d in det if d != 'shopify_native']
            return nn[0] if len(nn) == 1 else 'multiple'
        return 'generic' if bc == 'generic' else 'none'
    return L.apply(f, axis=1)


def cluster_bootstrap_prop(y, clusters, B=2000, seed=SEED):
    """Percentile CI for a proportion, resampling clusters with replacement.
    y: 0/1 array; clusters: array of cluster labels (singleton clusters allowed)."""
    y = np.asarray(y, dtype=float)
    cl = np.asarray(clusters)
    if len(y) == 0:
        return dict(p=None, lo=None, hi=None, n_clusters=0)
    labs, inv = np.unique(cl, return_inverse=True)
    ksum = np.bincount(inv, weights=y)
    nsum = np.bincount(inv).astype(float)
    rng = np.random.default_rng(seed)
    G = len(labs)
    idx = rng.integers(0, G, size=(B, G))
    num = ksum[idx].sum(1)
    den = nsum[idx].sum(1)
    est = num / den
    return dict(p=float(y.mean()), lo=float(np.percentile(est, 2.5)), hi=float(np.percentile(est, 97.5)), n_clusters=int(G))


def cluster_bootstrap_bca(y, clusters, B=2000, seed=SEED):
    """BCa interval for a proportion, resampling clusters (CMP products; stores without a CMP are singleton
    clusters). Acceleration from the cluster jackknife. Used as a SENSITIVITY interval only: clustering by CMP is
    not part of the sampling design (stratified census plus a random draw), for which Wilson is the primary CI."""
    from scipy.stats import norm
    y = np.asarray(y, dtype=float)
    cl = np.asarray(clusters)
    if len(y) == 0:
        return dict(p=None, lo=None, hi=None, n_clusters=0)
    labs, inv = np.unique(cl, return_inverse=True)
    ksum = np.bincount(inv, weights=y)
    nsum = np.bincount(inv).astype(float)
    G = len(labs)
    theta = ksum.sum() / nsum.sum()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, G, size=(B, G))
    est = ksum[idx].sum(1) / nsum[idx].sum(1)
    if G < 3 or np.all(est == theta):
        return dict(p=float(theta), lo=float(theta), hi=float(theta), n_clusters=int(G))
    prop = np.clip((est < theta).mean() + 0.5 * (est == theta).mean(), 1e-6, 1 - 1e-6)
    z0 = norm.ppf(prop)
    jk = (ksum.sum() - ksum) / (nsum.sum() - nsum)
    jm = jk.mean()
    num = ((jm - jk) ** 3).sum()
    den = 6 * (((jm - jk) ** 2).sum()) ** 1.5
    a = num / den if den > 0 else 0.0
    out = []
    for al in (0.025, 0.975):
        z = norm.ppf(al)
        q = norm.cdf(z0 + (z0 + z) / (1 - a * (z0 + z)))
        out.append(float(np.quantile(est, q)))
    return dict(p=float(theta), lo=out[0], hi=out[1], n_clusters=int(G), z0=float(z0), accel=float(a))


def kappa(a, b):
    a = np.asarray(a, dtype=int)
    b = np.asarray(b, dtype=int)
    n = len(a)
    if n == 0:
        return None
    po = (a == b).mean()
    pa, pb = a.mean(), b.mean()
    pe = pa * pb + (1 - pa) * (1 - pb)
    if pe == 1:
        return 1.0 if po == 1 else 0.0
    return float((po - pe) / (1 - pe))


def kappa_boot(a, b, B=2000, seed=SEED, groups=None):
    """Cohen's kappa with a percentile bootstrap CI. groups: resample these units (e.g. stores for store x vendor
    rows) instead of rows. With perfect agreement the interval is degenerate [1, 1]; the positive counts are
    returned so a reader can judge how much the agreement rests on."""
    a = np.asarray(a, dtype=int)
    b = np.asarray(b, dtype=int)
    rng = np.random.default_rng(seed)
    n = len(a)
    ks = []
    if groups is None:
        for _ in range(B):
            i = rng.integers(0, n, n)
            k = kappa(a[i], b[i])
            if k is not None and not np.isnan(k):
                ks.append(k)
    else:
        g = np.asarray(groups)
        labs, inv = np.unique(g, return_inverse=True)
        rows_of = [np.where(inv == j)[0] for j in range(len(labs))]
        for _ in range(B):
            pick = rng.integers(0, len(labs), len(labs))
            i = np.concatenate([rows_of[j] for j in pick])
            k = kappa(a[i], b[i])
            if k is not None and not np.isnan(k):
                ks.append(k)
    return dict(kappa=kappa(a, b), lo=float(np.percentile(ks, 2.5)), hi=float(np.percentile(ks, 97.5)), n=int(n),
                agree=int((a == b).sum()), pos_a=int(a.sum()), pos_b=int(b.sum()), pos_both=int((a & b).sum()),
                n_units=int(len(np.unique(groups))) if groups is not None else int(n))


class NpEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, set):
            return sorted(o)
        return super().default(o)


def dump(obj, name):
    fn = os.path.join(OUT, name)
    with open(fn, 'w') as f:
        json.dump(obj, f, indent=1, cls=NpEncoder)
    return fn
