"""Logistic models of residual sandboxed ad firing after Decline and under GPC (revised after review).

Model D  (Decline clicks that worked, n = 233): y = a sandbox created on the NEXT page (fresh page after the Decline)
         sent an ad request -- the Decline measure that is comparable with GPC.
Model G  (stores with a sandboxed ad request under Default, n = 803): y = any sandboxed ad request under GPC.
Predictor of interest: CMP integration group (reference = Shopify's native banner):
    'CMP writes to Shopify API' (integration modes A and C), 'Blocker only / unknown / none' (B, X, no CMP).
Integration group is a PRODUCT-level variable: its reference level is essentially one product (Shopify's banner),
which nearly always runs with a 'denied until consent' region default, so the mode effect cannot be separated from
product or default. We therefore report
  (1) Firth-penalised logistic ORs with profile-penalised-likelihood 95% CIs (Heinze & Schemper 2002), which do not
      account for clustering (model-based, optimistic);
  (2) a mixed-effects logistic model with a random intercept per CMP product (maximum marginal likelihood with
      Gauss-Hermite quadrature, Wald CIs), which does;
  (3) product-level descriptives (Fig S2 / Table S5).
Adjusted Decline models use the explicit-refusal measure (Shopify recorded 'no' after the click), which is also a
mediator of the mode effect, so the adjusted mode ORs are direct effects at best.
The 'mechanism check' (formerly 'decisive predictor'): whether a sandboxed pixel that does not declare the refused
purpose fired under Default. It is essentially the outcome measured in another load (repeat-load kappa ~0.98), so it
is reported as a 2 x 2 count that shows the mechanism, not as a predictor.
Writes outputs/models.json, outputs/models_table.csv and merges them into outputs/stats.json.
"""
import json
import os
import warnings

import numpy as np
import pandas as pd
from scipy.optimize import brentq, minimize

from common import CRAWL, OUT, dump

warnings.filterwarnings('ignore')


def _pll(b, X, y):
    e = X @ b
    p = 1 / (1 + np.exp(-e))
    ll = np.sum(y * np.log(np.clip(p, 1e-12, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-12, 1)))
    I = X.T @ (X * (p * (1 - p))[:, None])
    sgn, ld = np.linalg.slogdet(I)
    return ll + 0.5 * ld


def firth(X, y, maxit=200, tol=1e-9):
    """Firth-penalised logistic regression (Newton with step halving). Returns beta, inverse Fisher information."""
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    b = np.zeros(X.shape[1])
    for _ in range(maxit):
        p = 1 / (1 + np.exp(-(X @ b)))
        XW = X * (p * (1 - p))[:, None]
        Iinv = np.linalg.pinv(X.T @ XW)
        h = np.einsum('ij,jk,ik->i', XW, Iinv, X)
        step = Iinv @ (X.T @ (y - p + h * (0.5 - p)))
        f0 = _pll(b, X, y)
        t = 1.0
        while t > 1e-4 and _pll(b + t * step, X, y) < f0 - 1e-12:
            t /= 2
        b_new = b + t * step
        if np.max(np.abs(b_new - b)) < tol:
            b = b_new
            break
        b = b_new
    p = 1 / (1 + np.exp(-(X @ b)))
    return b, np.linalg.pinv(X.T @ (X * (p * (1 - p))[:, None]))


def profile_ci(X, y, b_hat, j, chi=3.841459):
    """Profile-penalised-likelihood CI for coefficient j: values of b_j where 2 * (pll_max - pll_profile) = chi."""
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    lmax = _pll(b_hat, X, y)
    others = [i for i in range(X.shape[1]) if i != j]
    start = b_hat[others].copy()

    def prof(bj):
        def f(bo):
            b = np.empty(X.shape[1])
            b[others] = bo
            b[j] = bj
            return -_pll(b, X, y)
        r = minimize(f, start, method='BFGS', options=dict(gtol=1e-7, maxiter=500))
        return -r.fun

    g = lambda bj: 2 * (lmax - prof(bj)) - chi
    out = []
    for sgn in (-1, 1):
        step = 0.5
        hi = b_hat[j] + sgn * step
        k = 0
        while g(hi) < 0 and k < 40:
            step *= 1.6
            hi = b_hat[j] + sgn * step
            k += 1
        if g(hi) < 0:
            out.append(np.nan)
            continue
        out.append(brentq(g, *sorted([b_hat[j], hi]), xtol=1e-6))
    return out[0], out[1]


def design(df, cat, ref, covs):
    X = pd.DataFrame(index=df.index)
    X['const'] = 1.0
    for lev in sorted(df[cat].unique()):
        if lev == ref:
            continue
        X[f'{cat}={lev}'] = (df[cat] == lev).astype(float)
    for c in covs:
        X[c] = df[c].astype(float)
    return X


def fit(df, ycol, cat, ref, covs, name):
    X = design(df, cat, ref, covs)
    y = df[ycol].astype(float).values
    b, cov = firth(X.values, y)
    rows = []
    for i, c in enumerate(X.columns):
        if c == 'const':
            continue
        lo, hi = profile_ci(X.values, y, b, i)
        sub = X[c] == 1 if set(X[c].unique()) <= {0.0, 1.0} else None
        rows.append(dict(model=name, term=c, OR=float(np.exp(b[i])), lo=float(np.exp(lo)), hi=float(np.exp(hi)),
                         n_term=int(sub.sum()) if sub is not None else None, events_term=int(y[sub.values].sum()) if sub is not None else None,
                         n=len(y), events=int(y.sum()), method='Firth, profile-penalised-likelihood CI'))
    return rows


def glmm_ri(X, y, groups, n_nodes=40):
    """Random-intercept logistic regression by maximum marginal likelihood (Gauss-Hermite quadrature over the random
    intercept, as in lme4::glmer with nAGQ > 1). Returns beta, SE (inverse numerical Hessian) and sigma."""
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    labs, inv = np.unique(np.asarray(groups), return_inverse=True)
    xs, ws = np.polynomial.hermite.hermgauss(n_nodes)
    G = len(labs)
    rows_of = [np.where(inv == g)[0] for g in range(G)]

    def nll(theta):
        b, ls = theta[:-1], theta[-1]
        sig = np.exp(ls)
        eta = X @ b
        tot = 0.0
        for g in range(G):
            r = rows_of[g]
            u = np.sqrt(2) * sig * xs                      # nodes
            e = eta[r][:, None] + u[None, :]
            ll = (y[r][:, None] * e - np.logaddexp(0, e)).sum(0)
            mx = ll.max()
            tot += mx + np.log(np.sum(ws * np.exp(ll - mx)) / np.sqrt(np.pi))
        return -tot
    b0, _ = firth(X, y)
    th0 = np.concatenate([b0, [np.log(0.5)]])
    res = minimize(nll, th0, method='BFGS', options=dict(gtol=1e-6, maxiter=2000))
    th = res.x
    k = len(th)
    H = np.zeros((k, k))
    h = 1e-4
    for i in range(k):
        for j in range(i, k):
            ei, ej = np.eye(k)[i] * h, np.eye(k)[j] * h
            H[i, j] = H[j, i] = (nll(th + ei + ej) - nll(th + ei - ej) - nll(th - ei + ej) + nll(th - ei - ej)) / (4 * h * h)
    cov = np.linalg.pinv(H)
    return th[:-1], np.sqrt(np.clip(np.diag(cov)[:-1], 0, None)), float(np.exp(th[-1])), bool(res.success)


def fit_mixed(df, ycol, cat, ref, covs, groups, name):
    """Random intercept per CMP product (stores without a detected CMP share one group)."""
    X = design(df, cat, ref, covs)
    y = df[ycol].astype(float).values
    b, se, sig, ok = glmm_ri(X.values, y, groups)
    rows = []
    for i, c in enumerate(X.columns):
        if c == 'const':
            continue
        rows.append(dict(model=name, term=c, OR=float(np.exp(b[i])), lo=float(np.exp(b[i] - 1.96 * se[i])), hi=float(np.exp(b[i] + 1.96 * se[i])),
                         n=len(y), events=int(y.sum()), n_groups=int(len(np.unique(groups))), re_sd=sig, converged=ok,
                         method='mixed logistic, random intercept per CMP product (Gauss-Hermite ML, Wald CI)'))
    return rows


def main():
    st = pd.read_csv(os.path.join(OUT, 'store_table.csv')).set_index('store_id')
    m = st[st.stratum == 'main'].copy()
    NX = pd.read_csv(os.path.join(OUT, 'next_page_requests.csv'), low_memory=False)
    fresh = set(NX[(NX.next_source == 'new_page')].store_id)
    m['region_optout'] = (m.region_optout == True)
    grp = {'N': 'Shopify native banner', 'A': 'CMP writes to Shopify API', 'C': 'CMP writes to Shopify API'}
    m['mgroup'] = m.cmp_mode.map(lambda x: grp.get(x, 'Blocker only / unknown / none'))
    m['product'] = m.cmp.where(~m.cmp.isin(['none', 'generic', 'multiple']), 'no CMP / unknown')
    ref = 'Shopify native banner'
    out = {}
    rows = []
    clk = m[m.click_ok == True].copy()
    clk['y'] = clk.index.isin(fresh)
    clk['refused'] = clk.refusal_cat == 'refused'
    rows += fit(clk, 'y', 'mgroup', ref, [], 'Decline, unadjusted')
    rows += fit(clk, 'y', 'mgroup', ref, ['refused', 'region_optout'], 'Decline, adjusted')
    s0 = m[m.A0_sbx].copy()
    s0['y'] = s0.A2_sbx
    rows += fit(s0, 'y', 'mgroup', ref, [], 'GPC, unadjusted')
    rows += fit(s0, 'y', 'mgroup', ref, ['region_optout'], 'GPC, adjusted')
    mixed = []
    mixed += fit_mixed(clk, 'y', 'mgroup', ref, [], clk['product'].values, 'Decline, CMP random intercept')
    mixed += fit_mixed(s0, 'y', 'mgroup', ref, [], s0['product'].values, 'GPC, CMP random intercept')
    T = pd.DataFrame(rows + mixed)
    T.to_csv(os.path.join(OUT, 'models_table.csv'), index=False)
    # product-level structure of the integration groups
    out['products_per_group'] = {g: int(x['product'].nunique()) for g, x in m[m.banner_A0 | m.banner_A1].groupby('mgroup')}
    # same definition as Fig 4b / Table S4 (review CE-22): Default-load banner stores with a readable region default
    # (m.region_optout was recoded above for the models, with unknown defaults set to False; use the original column)
    ro_ = st.loc[m.index, 'region_optout']
    nb_ = (m.mgroup == ref) & m.banner_A0 & ro_.notna()
    out['native_banner_default_denied'] = dict(k=int((nb_ & (ro_ == False)).sum()), n=int(nb_.sum()))
    # mechanism check (not a predictor): did a pixel that does not declare the refused purpose fire under Default?
    s0['default_nosale_ad'] = s0.A0_sbx_nodecl_sale.astype(bool)
    clk['default_nomkt_ad'] = clk.A0_sbx_nodecl_mkt.astype(bool)
    out['gpc_fired_without_default_nosale_ad'] = dict(k=int((s0.y & ~s0.default_nosale_ad).sum()), n=int((~s0.default_nosale_ad).sum()))
    out['gpc_fired_with_default_nosale_ad'] = dict(k=int((s0.y & s0.default_nosale_ad).sum()), n=int(s0.default_nosale_ad.sum()))
    out['decline_fired_without_default_nomkt_ad_refused'] = dict(k=int((clk.y & ~clk.default_nomkt_ad & clk.refused).sum()),
                                                                 n=int((~clk.default_nomkt_ad & clk.refused).sum()))
    out['decline_fired_with_default_nomkt_ad_refused'] = dict(k=int((clk.y & clk.default_nomkt_ad & clk.refused).sum()),
                                                              n=int((clk.default_nomkt_ad & clk.refused).sum()))
    out['n_decline'] = len(clk)
    out['n_gpc'] = len(s0)
    out['terms_list'] = rows
    out['mixed_list'] = mixed
    dump(out, 'models.json')
    sp = os.path.join(OUT, 'stats.json')
    S = json.load(open(sp))
    S['models'] = out
    dump(S, 'stats.json')
    pd.set_option('display.width', 220)
    print(T[['model', 'term', 'OR', 'lo', 'hi', 'n_term', 'events_term']].round(3).to_string())
    print({k: v for k, v in out.items() if not k.endswith('_list')})


if __name__ == '__main__':
    main()
