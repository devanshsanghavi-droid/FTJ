"""Round 4 B1: the 'blocked on paper' estimands on main (Part A) + expansion stores, combined and separately.

Definitions are the main analysis's (analysis/analyze.py, section 'Figure 4: declared vs actual' and 'referee revision:
blocked on paper'), re-implemented line by line on per-store records so that the same code runs on both datasets:
  blocklist store   a captured store with >= 1 advertising vendor whose CMP configuration, read at run time in the
                    Default (A0) load, declares it BLOCKED before any choice (crawl/cmp_declared.csv, declared_prechoice)
  fired (vendor-matched)  a declared-blocked vendor sent a request from Shopify's sandbox (strict_worker, lax_iframe,
                    lax_nested) in the Default load
  yes-writer        the CMP wrote 'marketingAllowed: true' (visitorConsentCollected) in the Default load, no click
  PRIMARY           fired among blocklist stores whose CMP wrote no 'yes' (analyze.py bl['primary'])
  like-for-like     ANY sandboxed ad request in the Default load, blocklist stores vs banner stores without a
                    declared-blocked vendor, within Shopify's region default (allowed = opt-out, denied = opt-in),
                    Mantel-Haenszel over the two defaults; reference 'allowed' excludes stores whose CMP wrote a 'deny'
  The reference stores come from the main (random) sample only: the expansion was sampled on having a blocklist, so
  its non-blocklist stores are not a reference population.
CIs: Wilson (primary) and a store bootstrap (percentile, B = 2000, seed 20260926; stratified by dataset for the
combined sample); entry-level (store x vendor) shares use a cluster bootstrap by store.

Usage:
  python r4_blocklist.py records --ds main|expansion   per-store records -> outputs/<ds>/blocklist_records.csv (+ pairs)
  python r4_blocklist.py combine                         estimands -> outputs/blocklist_r4.json
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(STUDY, 'analysis'))
OUTS = os.path.join(HERE, 'outputs')
B = 2000
SEED = 20260926
SANDBOX = {'strict_worker', 'lax_iframe', 'lax_nested'}


def paths(ds):
    if ds == 'main':
        return dict(crawl=os.path.join(STUDY, 'crawl'), tab=os.path.join(STUDY, 'analysis', 'outputs'), out=os.path.join(OUTS, 'main'), stratum='main',
                    sample=os.path.join(STUDY, 'sample', 'sample.csv'))
    if ds.startswith('selftest:'):   # r4_selftest.py: a copy of main raw files run through r4_tables.py
        d = ds.split(':', 1)[1]
        return dict(crawl=os.path.join(d, 'crawl'), tab=os.path.join(d, 'out'), out=os.path.join(d, 'out'), stratum='main', sample=os.path.join(d, 'out', '_sample', 'sample.csv'))
    return dict(crawl=os.path.join(STUDY, 'round4', 'expansion', 'crawl'), tab=os.path.join(OUTS, 'expansion'), out=os.path.join(OUTS, 'expansion'),
                stratum='expansion', sample=os.path.join(STUDY, 'round4', 'expansion', 'candidates.csv'))


def records(ds):
    P = paths(ds)
    os.makedirs(P['out'], exist_ok=True)
    import common
    common.CRAWL, common.OUT = P['crawl'], P['out']
    import analyze  # noqa: E402  (module-level code only defines functions; consent_changes writes to the patched OUT)
    st = pd.read_csv(os.path.join(P['tab'], 'store_table.csv')).set_index('store_id')
    ad = pd.read_csv(os.path.join(P['tab'], 'ad_requests.csv.gz'), low_memory=False)
    L = pd.read_csv(os.path.join(P['crawl'], 'loads.csv'), low_memory=False)
    L['ok'] = (L.goto_status.fillna(0).between(200, 399)) & (L.has_shopify == True) & (L.blocked_hint != True) & (L.n_requests.fillna(0) > 20)
    CE = pd.read_csv(os.path.join(P['crawl'], 'consent_events.csv'))
    CD = pd.read_csv(os.path.join(P['crawl'], 'cmp_declared.csv'))
    m = st[st.stratum == P['stratum']].copy()
    adm = ad[ad.stratum == P['stratum']]
    grants = analyze.consent_changes(CE, L, st)
    # ---- analyze.py lines 'Figure 4: declared vs actual' ----
    d = CD[(CD.arm == 'A0') & CD.store_id.isin(m.index) & (CD.is_advertising == True)].copy()
    blk_st = sorted(d[d.declared_prechoice == 'blocked'].store_id.unique())
    a0all = adm[adm.cond == 'A0']
    fired_sbx_pairs = set(zip(a0all[a0all.sandbox].store_id, a0all[a0all.sandbox].vendor))
    fired_sbx_mkt_pairs = set(zip(a0all[a0all.sandbox & a0all.decl_mkt].store_id, a0all[a0all.sandbox & a0all.decl_mkt].vendor))
    fired_any_pairs = set(zip(a0all.store_id, a0all.vendor))
    db = d[d.declared_prechoice == 'blocked'].copy()
    decl_vendor_sbx = {s for s in blk_st if any((s, v) in fired_sbx_pairs for v in db[db.store_id == s].vendor)}
    decl_vendor_sbx_mkt = {s for s in blk_st if any((s, v) in fired_sbx_mkt_pairs for v in db[db.store_id == s].vendor)}
    decl_vendor_any = {s for s in blk_st if any((s, v) in fired_any_pairs for v in db[db.store_id == s].vendor)}
    g0g = grants[(grants.arm == 'A0') & (grants.m_change == 'grant') & grants.store_id.isin(m.index)] if len(grants) else grants
    auto_grant = set(g0g.store_id) & set(blk_st) if len(grants) else set()
    ce0 = CE[(CE.arm == 'A0') & CE.detail.astype(str).str.contains('"marketingAllowed":true')]
    yes_any = set(ce0.store_id)
    yes_t = ce0[ce0.store_id.isin(blk_st)].groupby('store_id').t_ms.min().to_dict()
    g0dn = set(grants[(grants.arm == 'A0') & (grants.m_change == 'deny')].store_id) if len(grants) else set()
    ver = {s: str(g.detail.iloc[0])[:2] for s, g in db.groupby('store_id')}
    bcmp = {s: g.cmp.iloc[0] for s, g in db.groupby('store_id')}
    first_decl = {}
    for s in blk_st:
        t_ = a0all[(a0all.store_id == s) & a0all.sandbox & a0all.vendor.isin(set(db[db.store_id == s].vendor))].t_ms
        first_decl[s] = float(t_.min()) if len(t_) else None
    rows = []
    for s in m.index:
        r = m.loc[s]
        ro = r.region_optout
        ro = None if (ro is None or (isinstance(ro, float) and np.isnan(ro))) else (ro == True or ro == 'True')
        rows.append(dict(store_id=s, ds=ds.split(':')[0], domain=r.domain, cmp=r.cmp, banner_A0=bool(r.banner_A0), region_optout=ro,
                         A0_sbx=bool(r.A0_sbx), A0_any=bool(r.A0_any), A0_sbx_decl_mkt=bool(r.A0_sbx_decl_mkt), weight=float(r.weight) if pd.notna(r.weight) else None,
                         blk=s in blk_st, blk_cmp=bcmp.get(s), blk_version=ver.get(s), n_decl_blocked=int((db.store_id == s).sum()),
                         decl_vendors='|'.join(sorted(db[db.store_id == s].vendor.unique())),
                         fired=s in decl_vendor_sbx, fired_mkt=s in decl_vendor_sbx_mkt, fired_any_origin=s in decl_vendor_any,
                         yes_write=s in yes_any, t_yes=yes_t.get(s), t_first_decl_sbx=first_decl.get(s),
                         auto_grant=s in auto_grant, deny_change=s in g0dn))
    R = pd.DataFrame(rows)
    R.to_csv(os.path.join(P['out'], 'blocklist_records.csv'), index=False)
    db['fired_sbx'] = [(a, b) in fired_sbx_pairs for a, b in zip(db.store_id, db.vendor)]
    db['fired_any'] = [(a, b) in fired_any_pairs for a, b in zip(db.store_id, db.vendor)]
    db['ds'] = ds.split(':')[0]
    db.to_csv(os.path.join(P['out'], 'blocklist_pairs.csv'), index=False)
    print(ds, 'stores', len(R), 'blocklist', int(R.blk.sum()), 'fired', int(R[R.blk].fired.sum()), 'primary n', int((R.blk & ~R.yes_write).sum()))


# ------------------------------------------------------------------ estimands
def W(k, n):
    from common import wilson
    return wilson(k, n)


def boot_store(y, strata=None, seed=SEED):
    """Percentile bootstrap of a store-level share, resampling stores (within strata when given)."""
    y = np.asarray(y, dtype=float)
    if len(y) == 0:
        return dict(boot_lo=None, boot_hi=None)
    rng = np.random.default_rng(seed)
    strata = np.zeros(len(y), dtype=int) if strata is None else pd.factorize(np.asarray(strata))[0]
    groups = [np.where(strata == g)[0] for g in np.unique(strata)]
    est = np.empty(B)
    for b in range(B):
        idx = np.concatenate([g[rng.integers(0, len(g), len(g))] for g in groups])
        est[b] = y[idx].mean()
    return dict(boot_lo=float(np.percentile(est, 2.5)), boot_hi=float(np.percentile(est, 97.5)))


def WB(y, strata=None):
    y = np.asarray(y, dtype=int)
    r = W(int(y.sum()), len(y))
    r.update(boot_store(y, strata))
    return r


def boot_cluster_share(y, clusters, strata=None, seed=SEED):
    """Entry-level share with a percentile bootstrap resampling clusters (stores), within strata."""
    df = pd.DataFrame(dict(y=np.asarray(y, dtype=float), g=np.asarray(clusters), s=np.zeros(len(y)) if strata is None else np.asarray(strata)))
    if not len(df):
        return dict(k=0, n=0, p=None)
    agg = df.groupby(['s', 'g']).y.agg(['sum', 'count']).reset_index()
    rng = np.random.default_rng(seed)
    parts = [agg[agg.s == s][['sum', 'count']].values for s in agg.s.unique()]
    est = np.empty(B)
    for b in range(B):
        tot = np.zeros(2)
        for p in parts:
            tot += p[rng.integers(0, len(p), len(p))].sum(0)
        est[b] = tot[0] / tot[1]
    k, n = int(df.y.sum()), len(df)
    r = W(k, n)
    r.update(n_clusters=int(len(agg)), cboot_lo=float(np.percentile(est, 2.5)), cboot_hi=float(np.percentile(est, 97.5)))
    return r


def weighted_share(y, w, strata, seed=SEED):
    """Design-weighted share sum(w y)/sum(w) (ratio estimator) with a stratified store bootstrap. Sensitivity only."""
    y, w = np.asarray(y, dtype=float), np.asarray(w, dtype=float)
    if not len(y) or np.isnan(w).any():
        return None
    p = float((w * y).sum() / w.sum())
    rng = np.random.default_rng(seed)
    st = pd.factorize(np.asarray(strata))[0]
    groups = [np.where(st == g)[0] for g in np.unique(st)]
    est = np.empty(B)
    for b in range(B):
        idx = np.concatenate([g[rng.integers(0, len(g), len(g))] for g in groups])
        est[b] = (w[idx] * y[idx]).sum() / w[idx].sum()
    return dict(p=p, lo=float(np.percentile(est, 2.5)), hi=float(np.percentile(est, 97.5)), sum_w=float(w.sum()), n=int(len(y)))


def estimands(R, pairs, ref):
    """R: per-store records of the blocklist datasets in scope (main and/or expansion); ref: main-sample records
    (reference population for the like-for-like comparison)."""
    import analyze as A
    bl = R[R.blk].copy()
    strata = bl.ds.values
    out = dict(n_blocklist=int(len(bl)), by_ds={k: int(v) for k, v in bl.ds.value_counts().items()},
               by_cmp={k: int(v) for k, v in bl.blk_cmp.value_counts().items()})
    out['unconditioned'] = dict(fired=WB(bl.fired, strata), fired_mkt=WB(bl.fired_mkt, strata), any_sbx=WB(bl.A0_sbx, strata),
                                fired_any_origin=WB(bl.fired_any_origin, strata))
    pr = bl[~bl.yes_write]
    sp = pr.ds.values
    out['yes_writers'] = dict(n=int(bl.yes_write.sum()), auto_grant=int(bl.auto_grant.sum()),
                              yes_before_pixel=int(sum((r.yes_write and (pd.isna(r.t_first_decl_sbx) or r.t_yes <= r.t_first_decl_sbx)) for r in bl.itertuples())))
    out['primary'] = dict(rule="blocklist stores whose CMP wrote no 'marketing: yes' in the Default load", n=int(len(pr)),
                          fired=WB(pr.fired, sp), fired_mkt=WB(pr.fired_mkt, sp), any_sbx=WB(pr.A0_sbx, sp),
                          by_cmp={c: W(int(g.fired.sum()), len(g)) for c, g in pr.groupby('blk_cmp')},
                          by_default={lab: W(int(pr[pr.region_optout == v].fired.sum()), int((pr.region_optout == v).sum())) for lab, v in (('allowed', True), ('denied', False))},
                          n_unknown_default=int(pr.region_optout.isna().sum()))
    if pr.weight.notna().all() and len(pr):
        out['primary']['fired_design_weighted'] = weighted_share(pr.fired, pr.weight, pr.ds)
    out['by_default'] = {lab: dict(fired=W(int(bl[bl.region_optout == v].fired.sum()), int((bl.region_optout == v).sum())),
                                   any_sbx=W(int(bl[bl.region_optout == v].A0_sbx.sum()), int((bl.region_optout == v).sum())))
                         for lab, v in (('allowed', True), ('denied', False))}
    # entry level: declared-blocked (store, vendor) pairs, sandboxed firing, clustered by store
    pp = pairs[pairs.store_id.isin(bl.store_id)]
    ppr = pp[pp.store_id.isin(pr.store_id)]
    out['pairs'] = dict(all=boot_cluster_share(pp.fired_sbx, pp.store_id, pp.ds), primary=boot_cluster_share(ppr.fired_sbx, ppr.store_id, ppr.ds))
    # like-for-like vs the main reference, by Shopify's region default (analyze.py f4['a']['like_for_like'])
    rb = ref[ref.banner_A0 & ~ref.blk]
    ref_al = rb[(rb.region_optout == True) & ~rb.deny_change]
    ref_dn = rb[rb.region_optout == False]
    lf, st1, st2 = {}, [], []
    for lab, rf in (('allowed', ref_al), ('denied', ref_dn)):
        ids = bl[bl.region_optout == (lab == 'allowed')]
        k1, n1, k0, n0 = int(ids.A0_sbx.sum()), len(ids), int(rf.A0_sbx.sum()), len(rf)
        lf[lab] = dict(blocklist=W(k1, n1), reference=W(k0, n0), diff=A.newcombe_indep(k1, n1, k0, n0), blocklist_declared_vendor=W(int(ids.fired.sum()), n1))
        st1.append((k1, n1, k0, n0))
        ids2, rf2 = ids[~ids.yes_write], rf[~rf.yes_write]
        k1, n1, k0, n0 = int(ids2.A0_sbx.sum()), len(ids2), int(rf2.A0_sbx.sum()), len(rf2)
        lf[lab + '_no_yes'] = dict(blocklist=W(k1, n1), reference=W(k0, n0), diff=A.newcombe_indep(k1, n1, k0, n0), blocklist_declared_vendor=W(int(ids2.fired.sum()), n1),
                                   reference_excluded=int(rf.yes_write.sum()))
        st2.append((k1, n1, k0, n0))
    lf['mh'] = A.mantel_haenszel(st1)
    lf['mh_no_yes'] = A.mantel_haenszel(st2)
    if lf['mh_no_yes']:
        lf['mh_no_yes']['reduction_ruled_out_beyond'] = float(max(0.0, -lf['mh_no_yes']['rd_lo']))
    out['like_for_like'] = lf
    return out


def combine():
    import common  # noqa: F401
    Rm = pd.read_csv(os.path.join(OUTS, 'main', 'blocklist_records.csv'))
    Pm = pd.read_csv(os.path.join(OUTS, 'main', 'blocklist_pairs.csv'))
    have_exp = os.path.exists(os.path.join(OUTS, 'expansion', 'blocklist_records.csv'))
    Re = pd.read_csv(os.path.join(OUTS, 'expansion', 'blocklist_records.csv')) if have_exp else Rm.iloc[0:0]
    Pe = pd.read_csv(os.path.join(OUTS, 'expansion', 'blocklist_pairs.csv')) if have_exp else Pm.iloc[0:0]
    for R_ in (Rm, Re):
        R_['region_optout'] = R_.region_optout.map(lambda v: None if pd.isna(v) else (v is True or v == 'True' or v == 1.0))
    out = dict(main=estimands(Rm, Pm, Rm))
    if have_exp and Re.blk.any():
        out['expansion'] = estimands(Re, Pe, Rm)
        out['combined'] = estimands(pd.concat([Rm, Re], ignore_index=True), pd.concat([Pm, Pe], ignore_index=True), Rm)
        # did the expansion differ from the main blocklist stores? (primary, independent samples)
        import analyze as A
        from scipy.stats import fisher_exact
        a, b = out['main']['primary']['fired'], out['expansion']['primary']['fired']
        out['main_vs_expansion_primary'] = dict(A.newcombe_indep(a['k'], a['n'], b['k'], b['n']),
                                                fisher_p=float(fisher_exact([[a['k'], a['n'] - a['k']], [b['k'], b['n'] - b['k']]])[1]))
    out['expansion_funnel'] = expansion_funnel(Re) if have_exp else None
    out['_meta'] = dict(bootstrap_B=B, seed=SEED, reference='main-sample banner stores without a declared-blocked ad vendor',
                        note='unweighted store-level shares (as the main paper); design-weighted primary rate is a sensitivity')
    json.dump(out, open(os.path.join(OUTS, 'blocklist_r4.json'), 'w'), indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
    print(json.dumps({k: (v['primary']['fired'] if isinstance(v, dict) and 'primary' in v else None) for k, v in out.items()}, default=str)[:600])


def expansion_funnel(Re):
    """Candidates -> prepared (robots) -> loads -> captured -> blocklist at run time."""
    import csv
    cand = list(csv.DictReader(open(os.path.join(STUDY, 'round4', 'expansion', 'candidates.csv'))))
    planf = os.path.join(STUDY, 'round4', 'expansion', 'crawl', 'plan_r4.json')
    plan = json.load(open(planf))['sites'] if os.path.exists(planf) else []
    L = pd.read_csv(os.path.join(STUDY, 'round4', 'expansion', 'crawl', 'loads.csv'), low_memory=False)
    L['ok'] = (L.goto_status.fillna(0).between(200, 399)) & (L.has_shopify == True) & (L.blocked_hint != True) & (L.n_requests.fillna(0) > 20)
    dec = pd.Series([p.get('decision') for p in plan]).value_counts().to_dict()
    src = pd.Series([p.get('product_url_source') for p in plan]).value_counts().to_dict()
    ok_arms = L[L.ok].groupby('store_id').arm.apply(set)
    return dict(candidates=len(cand), prepared=len(plan), decisions={k: int(v) for k, v in dec.items()}, page_source={k: int(v) for k, v in src.items()},
                loads_run=int(len(L)), loads_ok=int(L.ok.sum()), loads_ok_by_arm={k: int(v) for k, v in L[L.ok].arm.value_counts().items()},
                stores_with_any_load=int(L.store_id.nunique()), captured_all_three=int(sum({'A0', 'A1', 'A2'} <= a for a in ok_arms)),
                captured_records=int(len(Re)), blocklist_at_runtime=int(Re.blk.sum()),
                blocklist_by_static_prediction={k: int(v) for k, v in Re[Re.blk].merge(pd.DataFrame(cand)[['store_id', 'prechoice_ca']], on='store_id', how='left').prechoice_ca.value_counts().items()},
                static_yes_confirmed=dict(k=int(Re.merge(pd.DataFrame(cand)[['store_id', 'prechoice_ca']], on='store_id').query("prechoice_ca == 'yes'").blk.sum()),
                                          n=int(Re.merge(pd.DataFrame(cand)[['store_id', 'prechoice_ca']], on='store_id').query("prechoice_ca == 'yes'").shape[0])),
                static_unknown_confirmed=dict(k=int(Re.merge(pd.DataFrame(cand)[['store_id', 'prechoice_ca']], on='store_id').query("prechoice_ca == 'unknown'").blk.sum()),
                                              n=int(Re.merge(pd.DataFrame(cand)[['store_id', 'prechoice_ca']], on='store_id').query("prechoice_ca == 'unknown'").shape[0])),
                failed_loads=L[~L.ok][['load_id', 'goto_status', 'goto_error', 'blocked_hint', 'has_shopify', 'n_requests']].astype(str).to_dict('records')[:200])


if __name__ == '__main__':
    if sys.argv[1] == 'records':
        records(sys.argv[sys.argv.index('--ds') + 1])
    elif sys.argv[1] == 'combine':
        combine()
