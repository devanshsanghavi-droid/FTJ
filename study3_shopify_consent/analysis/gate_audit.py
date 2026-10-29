"""Audit of Shopify's consent gate, one row per sandbox (pixel) creation.

For every ok load of a captured store, every WPM pixel creation request (STRICT worker bootstrap,
LAX sandbox iframe, OPEN pixel script) is matched to the pixel's declared privacyPurposes and to the
Shopify consent state in force at that moment:
  * page start: the navigation's Server-Timing _cmp string (v3; decoded below);
  * later: visitorConsentCollected events (ms-precise; first page) and the ~1 s Customer Privacy
    API readings (consent_states.csv; both pages), whichever is most recent before the creation.
A creation is a GATE VIOLATION if the pixel declares a purpose the state denied at that moment.
For Decline (A1) loads each creation is assigned to the first page or the next page, and next-page
ad requests are split into 'old page' (a sandbox created on the first page still sending, e.g. an
unload beacon) and 'new page' (a sandbox created after the reload).

Outputs: outputs/sandbox_creations.csv, outputs/next_page_requests.csv, outputs/gate_audit.json
_cmp v3 format (mechanism.md 2.4): 3<choices>.<purposes>_<region>_...; in <choices> upper = accepted,
lower = declined; in <purposes> upper = allowed by default, lower = denied by default.
"""
import json
import os

import numpy as np
import pandas as pd

from common import CRAWL, OUT, dump, load_tables

PURP = {'ANALYTICS': 'a', 'MARKETING': 'm', 'PREFERENCES': 'p', 'SALE_OF_DATA': 's'}
EV_KEY = {'a': 'analyticsAllowed', 'm': 'marketingAllowed', 'p': 'preferencesAllowed', 's': 'saleOfDataAllowed'}
CS_KEY = {'a': 'analyticsProcessingAllowed', 'm': 'marketingAllowed', 'p': 'preferencesProcessingAllowed', 's': 'saleOfDataAllowed'}
CREATE_KINDS = ['strict_worker_bootstrap', 'lax_iframe_sandbox', 'open_main_thread_pixel']


def decode_state(v):
    """_cmp v3 string -> {a,m,p,s: True/False/None}. None = not stated (the WPM fails open)."""
    if not isinstance(v, str) or not v.startswith('3'):
        return None
    head = v[1:].split('_')[0]
    choices, purposes = (head.split('.', 1) + [''])[:2]
    out = {}
    for p in 'amps':
        if p.upper() in choices:
            out[p] = True
        elif p in choices:
            out[p] = False
        elif p.upper() in purposes:
            out[p] = True
        elif p in purposes:
            out[p] = False
        else:
            out[p] = None
    return out


def tb(x):
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, str):
        return {'True': True, 'False': False, 'true': True, 'false': False}.get(x)
    return None


def main():
    L, R, captured = load_tables()
    ok = L[L.ok & L.captured].set_index('load_id')
    W = R[(R.vendor == 'shopify_wpm') & R.load_id.isin(ok.index)]
    cre = W[W.kind.isin(CREATE_KINDS)].copy()
    mgr = W[W.kind == 'manager_bundle']
    CE = pd.read_csv(os.path.join(CRAWL, 'consent_events.csv'))
    CS = pd.read_csv(os.path.join(CRAWL, 'consent_states.csv'), low_memory=False)
    CS = CS[CS.error.isna() & (CS.has_cp == True) & CS.load_id.isin(ok.index)]

    # state change points per load: list of (t, page, {p: bool}) ; page in {'first','next'}
    changes = {}
    for lid, row in ok.iterrows():
        ch = []
        st0 = decode_state(row.cmp_header_raw)
        if st0 is not None:
            ch.append((0, 'first', st0, 'header'))
        if row.arm == 'A1' and pd.notna(row.t_next_nav):
            st1 = decode_state(row.next_cmp_header_raw)
            if st1 is not None:
                ch.append((row.t_next_nav, 'next', st1, 'header_next'))
        changes[lid] = ch
    # consent_events.csv comes from the load's LAST page probe: for a clicked Decline load that is the
    # next page, and its page_t is relative to the next page's time origin (checked against the
    # consent_states 'next_page' readings, whose t_ms = t_next_nav + page_t).
    for r in CE[CE.load_id.isin(ok.index)].itertuples():
        d = json.loads(r.detail)
        stv = {p: tb(d.get(EV_KEY[p])) for p in 'amps'}
        tn = ok.loc[r.load_id, 't_next_nav'] if ok.loc[r.load_id, 'arm'] == 'A1' else np.nan
        if pd.notna(tn):
            changes[r.load_id].append((tn + r.page_t, 'next', stv, 'event'))
        else:
            changes[r.load_id].append((r.t_ms, 'first', stv, 'event'))
    for r in CS.itertuples():
        stv = {p: tb(getattr(r, CS_KEY[p])) for p in 'amps'}
        page = 'next' if r.tag == 'next_page' or (r.tag == 'end' and ok.loc[r.load_id, 'arm'] == 'A1' and pd.notna(ok.loc[r.load_id, 't_next_nav'])) else 'first'
        changes[r.load_id].append((r.t_ms, page, stv, 'reading'))
    for k in changes:
        changes[k].sort(key=lambda x: (x[0], x[3] != 'header'))

    def state_at(lid, t, page):
        cur = None
        src = 'none'
        for (tt, pg, stv, s) in changes.get(lid, []):
            if pg != page or tt > t:
                continue
            if cur is None:
                cur = dict(stv)
            else:
                for p, v in stv.items():
                    if v is not None:
                        cur[p] = v
            src = s
        return cur, src

    # page assignment for A1
    cre = cre.drop(columns=['t_click']).join(ok[['arm', 't_next_nav', 't_click', 'stratum']].rename(columns={'arm': 'larm', 'stratum': 'lstratum'}), on='load_id')
    cre['page'] = np.where((cre.larm == 'A1') & cre.t_next_nav.notna() & (cre.t_ms >= cre.t_next_nav), 'next', 'first')
    rows = []
    for r in cre.itertuples():
        pp = r.pixel_purposes if isinstance(r.pixel_purposes, str) else ''
        decl = [PURP[x] for x in pp.split('|') if x in PURP]
        stv, src = state_at(r.load_id, r.t_ms, r.page)
        denied = [p for p in decl if stv is not None and stv.get(p) is False]
        unknown = stv is None
        rows.append(dict(load_id=r.load_id, store_id=r.store_id, stratum=r.lstratum, arm=r.arm, page=r.page, t_ms=r.t_ms,
                         t_click=r.t_click, kind=r.kind, pixel_id=r.pixel_id, pixel_type=r.pixel_type, pixel_api=r.pixel_api,
                         pixel_purposes=pp or ('NONE' if r.pixel_matched else 'UNMATCHED'),
                         declares_marketing='m' in decl, declares_sale='s' in decl, no_purpose=(pp == 'NONE'),
                         state_src=src, state_unknown=unknown,
                         st_a=None if unknown else stv.get('a'), st_m=None if unknown else stv.get('m'),
                         st_p=None if unknown else stv.get('p'), st_s=None if unknown else stv.get('s'),
                         denied_declared='|'.join(denied), violation=bool(denied)))
    SC = pd.DataFrame(rows)
    SC.to_csv(os.path.join(OUT, 'sandbox_creations.csv'), index=False)

    # next-page ad requests of clicked A1 loads: old page (lingering sandbox) vs new page
    a1c = ok[(ok.arm == 'A1') & ok.t_next_nav.notna()]
    newp = SC[(SC.arm == 'A1') & (SC.page == 'next')]
    new_pix = set(zip(newp.load_id, newp.pixel_id.astype(str)))
    first_new = newp.groupby('load_id').t_ms.min()
    # R.ad excludes CORS preflights and R.sandbox includes frames nested in a LAX sandbox (common.load_tables, referee revision)
    nx = R[R.ad & R.load_id.isin(a1c.index) & (R.phase == 'next_page')].copy()
    nx['t_first_new_sandbox'] = nx.load_id.map(first_new)

    def which(r):
        if not r.sandbox:
            return 'main_thread_or_other'
        if (r.load_id, str(r.pixel_id)) in new_pix and (pd.isna(r.t_first_new_sandbox) or r.t_ms >= r.t_first_new_sandbox):
            return 'new_page'
        return 'old_page'
    nx['next_source'] = nx.apply(which, axis=1) if len(nx) else []
    nx[['load_id', 'store_id', 'stratum', 'arm', 't_ms', 'vendor', 'color_group', 'origin', 'pixel_id', 'pixel_type', 'pixel_purposes',
        'kind', 'next_source']].to_csv(os.path.join(OUT, 'next_page_requests.csv'), index=False)

    # summary
    out = {}
    for arm, g in SC.groupby('arm'):
        out[arm] = dict(creations=len(g), loads=int(g.load_id.nunique()), state_unknown=int(g.state_unknown.sum()),
                        with_denied_declared_purpose=int(g.violation.sum()))
    g = SC[SC.violation]
    out['violations'] = g[['load_id', 'arm', 'page', 't_ms', 'kind', 'pixel_id', 'pixel_type', 'pixel_purposes', 'state_src', 'denied_declared']].to_dict('records')
    out['n_creations_total'] = len(SC)
    out['n_violations_total'] = int(SC.violation.sum())
    out['n_violations_main'] = int(SC[SC.stratum == 'main'].violation.sum())
    out['n_creations_main'] = int((SC.stratum == 'main').sum())
    # creations whose declared purposes include one that was denied at SOME point in the load but not at creation
    dump(out, 'gate_audit.json')
    print(json.dumps({k: v for k, v in out.items() if k != 'violations'}, indent=1))
    print('violations', len(g))
    print(g.groupby(['arm', 'page', 'state_src', 'pixel_type']).size())


if __name__ == '__main__':
    main()
