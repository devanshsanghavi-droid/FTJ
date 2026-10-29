"""Supplementary figures S2-S6 (full width 190 mm). Data: analysis/outputs/figS2.csv ... figS6.csv, figS4_kappa.csv, stats.json.
S1 (static WPM architecture) is a schematic and is not produced here.
Revised after review: no figure titles or notes baked into the figures (captions carry them); 7 pt minimum text;
S2 uses the explicit-refusal and fresh-page Decline measures and adds the region-default column; S4 gains panel d
(repeat-load and native-GPC agreement, moved from Fig 6c, with positive counts); S5 is also written as a booktabs
LaTeX table (figures/tables/tableS5_per_vendor.tex) without zebra shading."""
import os

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from figutil import FIGDIR, C, arm_handle, ax_mm, ci_dot, fig_mm, letter, panel_title, save, stats, table, xgrid

CMP_NAME = {'pandectes': 'Pandectes', 'onetrust': 'OneTrust', 'shopify_native': 'Shopify\u2019s banner', 'cookiebot': 'Cookiebot',
            'osano': 'Osano', 'iubenda': 'iubenda', 'usercentrics': 'Usercentrics', 'axeptio': 'Axeptio', 'trustarc': 'TrustArc',
            'ketch': 'Ketch', 'clarip': 'Clarip', 'cookiescript': 'CookieScript', 'cookieyes': 'CookieYes', 'other': 'other / none'}
MODE_NAME = {'N': 'N', 'A': 'A', 'B': 'B', 'C': 'C', 'X': 'X', 'none': '-'}


def small_multiples(fig, W, H, T, rowkey, rows, rowlabels, metrics, top, left, width, gap, height, min_n=5):
    axes = []
    for j, (m, title, arm) in enumerate(metrics):
        x0 = left + j * (width + gap)
        ax = ax_mm(fig, x0, top, width, height, W, H)
        ys = np.arange(len(rows))[::-1].astype(float)
        for y, r in zip(ys, rows):
            q = T[(T[rowkey] == r) & (T.metric == m)]
            if not len(q):
                continue
            q = q.iloc[0]
            if q.n < min_n:
                ax.text(50, y, f'n = {int(q.n)}', ha='center', va='center', fontsize=7, color=C.GREY_M)
                continue
            ci_dot(ax, y, 100 * q.p, 100 * q.lo, 100 * q.hi, arm=arm, size=3.6, lw=0.7)
            ax.text(112, y, f'{int(q.n)}', ha='left', va='center', fontsize=7, color=C.GREY_D)
        # review FIG-20: pad the axis so that markers at 0% and 100% touch neither the row labels nor the n column
        ax.set_xlim(-6, 104)
        ax.spines['bottom'].set_bounds(0, 100)
        ax.set_xticks([0, 50, 100])
        ax.set_ylim(-0.6, len(rows) - 0.4)
        ax.set_yticks(ys)
        ax.set_yticklabels(rowlabels if j == 0 else [])
        ax.tick_params(axis='y', length=0, pad=6)
        ax.spines['left'].set_visible(False)
        xgrid(ax)
        ax.set_title(title, fontsize=7, loc='left', pad=3, linespacing=1.0)
        ax.set_xlabel('%', labelpad=1)
        for ln in ax.lines:
            ln.set_clip_on(False)
        axes.append(ax)
    return axes


def S2():
    T = table('figS2.csv')
    W, H = 190, 92
    fig = fig_mm(W, H)
    rows = list(dict.fromkeys(T.cmp))
    first = T.drop_duplicates('cmp').set_index('cmp')
    labels = [f"{CMP_NAME.get(r, r)} [{MODE_NAME.get(first.loc[r, 'mode'], first.loc[r, 'mode'])}] ({int(first.loc[r, 'n_banner'])})" for r in rows]
    labels = [l.replace('[-]', '[none]') for l in labels]
    metrics = [('region_denied', 'Shopify default\ndenies marketing', 'Default'),
               ('prechoice_sbx', 'pixel fires before\nany choice', 'Default'),
               ('reject_first_layer', 'reject option on\nthe first layer', 'Decline'),
               ('reached', 'Shopify recorded\nan explicit \u2018no\u2019', 'Decline'),
               ('after_decline', 'next page: new\nsandbox still fires', 'Decline'),
               ('gpc_resid', 'still fires\nunder GPC', 'GPC')]
    small_multiples(fig, W, H, T, 'cmp', rows, labels, metrics, top=13, left=46, width=17.5, gap=6.3, height=70)
    fig.legend([arm_handle('Default', size=3.6), arm_handle('Decline', size=3.6), arm_handle('GPC', size=3.6)],
               ['Default load', 'Decline load', 'GPC load'], loc='upper left', bbox_to_anchor=(0, 1 - 0.3 / H), ncol=3, fontsize=7, borderaxespad=0,
               handletextpad=0.2, frameon=False)
    save(fig, 'figS2_per_cmp')


def S3():
    T = table('figS3.csv')
    W, H = 190, 48
    fig = fig_mm(W, H)
    rows = ['1-10k', '10k-50k', '50k-100k', '100k-200k']
    ncount = T[T.metric == 'banner'].set_index('bucket').n
    labels = [f'Tranco {r.replace("-", "–")} ({int(ncount[r])})' for r in rows]
    metrics = [('banner', 'banner shown', 'Default'),
               ('prechoice_sbx', 'sandboxed pixel\nbefore any choice', 'Default'),
               ('prechoice_sbx_banner', 'same, among\nbanner stores', 'Default'),
               ('after_decline', 'next page: still\nfires after Decline', 'Decline'),
               ('gpc_resid', 'still fires\nunder GPC', 'GPC')]
    small_multiples(fig, W, H, T, 'bucket', rows, labels, metrics, top=9, left=36, width=23, gap=8.2, height=24)
    fig.legend([arm_handle('Default', size=3.6), arm_handle('Decline', size=3.6), arm_handle('GPC', size=3.6)],
               ['Default load', 'Decline load', 'GPC load'], loc='lower left', bbox_to_anchor=(0, 0.0), ncol=3, fontsize=7, borderaxespad=0,
               handletextpad=0.2, frameon=False)
    save(fig, 'figS3_by_rank')


def S4():
    A = stats()['supp']['S4']
    T = table('figS4.csv')
    K = table('figS4_kappa.csv').set_index('pair')
    W, H = 190, 108   # +8 mm for the notes on the Brave check's power (MET-22) and request-count repeatability (MET-30)
    fig = fig_mm(W, H)
    panels = [('banner', 'Banner detection', ['banner detected'], ['banner visible', 'no banner visible'], ['banner\nvisible', 'no\nbanner']),
              ('reject', 'First-layer reject option', ['reject found', 'no reject found'], ['reject visible', 'no reject visible'], ['reject\nvisible', 'no\nreject']),
              ('click', 'Decline click dismissed the banner', ['banner dismissed', 'banner still shown'], ['banner gone', 'banner still shown'], ['banner\ngone', 'still\nshown'])]
    x = 27
    for i, (pn, title, rlabs, clabs, cshort) in enumerate(panels):
        ax = ax_mm(fig, x, 17, 14 * len(clabs), 7 * len(rlabs), W, H)
        fig.text((x - 27) / W, 1 - 0.5 / H, 'abc'[i], fontsize=10, fontweight='bold', va='top')
        fig.text((x - 22) / W, 1 - 0.9 / H, title, fontsize=8, fontweight='bold', va='top')
        for ri, rl in enumerate(rlabs):
            for ci, cl in enumerate(clabs):
                q = T[(T.panel == pn) & (T.crawler == rl) & (T.audit == cl)]
                k = int(q.k.iloc[0]) if len(q) else 0
                agree = (ri == ci) if len(rlabs) > 1 else (ci == 0)
                y = len(rlabs) - 1 - ri
                ax.add_patch(Rectangle((ci, y), 1, 1, facecolor=C.GREY_L if agree else C.SURFACE, edgecolor=C.AXIS, lw=0.5))
                ax.text(ci + 0.5, y + 0.5, f'{k}', ha='center', va='center', fontsize=8, color=C.INK, fontweight='bold' if agree else 'normal')
        ax.set_xlim(0, len(clabs))
        ax.set_ylim(0, len(rlabs))
        ax.set_xticks(np.arange(len(clabs)) + 0.5)
        ax.set_xticklabels(cshort, fontsize=7, linespacing=1.0)
        ax.xaxis.tick_top()
        ax.set_yticks(np.arange(len(rlabs))[::-1] + 0.5)
        ax.set_yticklabels(rlabs, fontsize=7)
        ax.tick_params(length=0, pad=1.5)
        for sp in ax.spines.values():
            sp.set_visible(False)
        fig.text((x + 14 * len(clabs) + 1.5) / W, 1 - 14.5 / H, 'audit', fontsize=7, color=C.GREY_D, va='bottom', ha='left')
        fig.text((x - 1.5) / W, 1 - 14.5 / H, 'crawler', fontsize=7, color=C.GREY_D, va='bottom', ha='right')
        x += 62
    fig.text(1 / W, 1 - 34.5 / H,
             f"{A['n']} seeded Decline loads ({A['n_clicked']} clicked, {A['n_noreject']} without a reject option). Banner detector: "
             f"{A['banner_precision']['k']} of {A['banner_precision']['n']} flagged banners were real. Reject finder: {A['reject_agreement']['k']} of "
             f"{A['reject_agreement']['n']}. Click flag: {A['click_flag_agreement']['k']} of {A['click_flag_agreement']['n']}\n"
             f"clicked loads with a visible banner ({A['clicked_without_visible_banner']} clicked load showed no banner in the screenshot); "
             f"banner gone after {A['click_success_audit']['k']} of {A['click_success_audit']['n']} clicks. Grey cells: crawler and audit agree.",
             fontsize=7, color=C.GREY_D, va='top', linespacing=1.15)
    # d: repeat-load and native-GPC agreement (moved from Fig 6c)
    fig.text(0, 1 - 45.5 / H, 'd', fontsize=10, fontweight='bold', va='top')
    fig.text(5 / W, 1 - 45.9 / H, 'Agreement between loads: Cohen’s κ on ‘a sandboxed ad request fired’', fontsize=8, fontweight='bold', va='top')
    ax = ax_mm(fig, 62, 56, 70, 34, W, H)
    rows = [('A0_vs_A0r', 'Default vs repeat, stores'), ('A0_vs_A0r_vendor', 'Default vs repeat, store × vendor'),
            ('A2_vs_A2r', 'GPC vs repeat, stores'), ('A2_vs_A2r_vendor', 'GPC vs repeat, store × vendor'),
            ('A2_vs_V1', 'emulated vs Brave GPC, stores'), ('A2_vs_V1_vendor', 'emulated vs Brave GPC, store × vendor')]
    ys = np.arange(len(rows))[::-1].astype(float)
    for (k, lab), y in zip(rows, ys):
        r = K.loc[k]
        ci_dot(ax, y, r.kappa, r.lo, r.hi, arm='Repeat', size=4.0)
        ax.text(1.004, y, f'{int(r.agree):,}/{int(r.n):,} agree; {int(r.pos_a):,} and {int(r.pos_b):,} positive', va='center', ha='left',
                fontsize=7, color=C.GREY_D)
    for ln in ax.lines:
        ln.set_clip_on(False)
    # review MET-22: the Brave agreement is informative only where Default and GPC differ
    V = stats()['validation']
    bp = V['brave_power']
    r0, r2 = V['A0_vs_A0r_count_spearman'], V['A2_vs_A2r_count_spearman']   # review MET-30: request counts, not only the binary flag
    fig.text(5 / W, 1 - 100.0 / H,
             f"Emulated vs Brave GPC: Default and GPC differed on {bp['stores_default_gpc_differ']} of the {bp['n_stores']} stores and "
             f"{bp['pairs_default_gpc_differ']} of the {bp['n_pairs']} store \u00d7 vendor pairs; Brave matched GPC on all "
             f"{bp['stores_brave_matches_gpc']} and all {bp['pairs_brave_matches_gpc']}.\n"
             f"Sandboxed ad requests per store, Spearman \u03c1: Default vs repeat {r0['rho']:.3f} ({r0['lo']:.3f}\u2013{r0['hi']:.3f}), "
             f"GPC vs repeat {r2['rho']:.3f} ({r2['lo']:.3f}\u2013{r2['hi']:.3f}); {r0['n']} stores, bootstrap over stores.",
             fontsize=7, color=C.GREY_D, va='top', ha='left', linespacing=1.15)
    ax.set_yticks(ys)
    ax.set_yticklabels([f'{lab} ({int(K.loc[k].n):,})' for k, lab in rows])
    ax.tick_params(axis='y', length=0)
    ax.spines['left'].set_visible(False)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xlim(0.9, 1.0)
    ax.set_xticks([0.9, 0.925, 0.95, 0.975, 1.0])
    ax.set_xticklabels(['0.900', '0.925', '0.950', '0.975', '1.000'])
    ax.set_xlabel('Cohen’s κ (95% CI; store x vendor rows resampled by store)'.replace(' x ', ' × '))
    xgrid(ax)
    save(fig, 'figS4_audit')


VNAME = {'google_ads': 'Google Ads', 'meta': 'Meta', 'google_merchant_center': 'Google Merchant Center', 'tiktok': 'TikTok',
         'microsoft_uet': 'Microsoft Ads (UET)', 'pinterest': 'Pinterest', 'snap': 'Snap', 'tapad': 'Tapad', 'criteo': 'Criteo',
         'reddit': 'Reddit', 'x_twitter': 'X (Twitter)', 'applovin': 'AppLovin', 'tradedesk': 'The Trade Desk', 'amazon_ads': 'Amazon Ads',
         'taboola': 'Taboola', 'liveintent': 'LiveIntent', 'linkedin': 'LinkedIn', 'claritas': 'Claritas', 'mntn': 'MNTN',
         'spotify_ads': 'Spotify Ads'}


def S5():
    T = table('figS5.csv')
    W, H = 190, 104
    fig = fig_mm(W, H)
    cols = [('Vendor', 4, 'left'), ('stores,\nDefault', 58, 'right'), ('% of\nstores', 72, 'right'), ('% requests\nsandboxed', 90, 'right'),
            ('GPC: still\nfires / Default', 116, 'right'), ('GPC: still\nfires, sandbox', 138, 'right'), ('Decline: next\npage / sandboxed', 164, 'right'),
            ('beacons with\nfull URL', 190, 'right')]
    ax = ax_mm(fig, 0, 0, 190, 104, W, H)
    ax.set_xlim(0, 190)
    n = len(T)
    ax.set_ylim(n + 0.9, -1.4)
    ax.axis('off')
    for lab, x, ha in cols:
        ax.text(x, -0.1, lab, ha=ha, va='bottom', fontsize=7, color=C.GREY_D, linespacing=1.0)
    ax.plot([0, 190], [0.25, 0.25], color=C.AXIS, lw=0.5)
    for i, r in T.iterrows():
        y = i + 0.95
        ax.plot([1.6], [y], marker='s', ms=3.6, mfc=C.VENDOR.get(r.vgroup, C.GREY_M), mec='none')
        vals = [VNAME.get(r.vendor, r.vendor), f'{r.stores_default:,}', f'{100 * r.share_stores:.0f}', f'{100 * r.sandbox_share_requests:.0f}',
                f'{r.gpc_still:,}/{r.stores_default:,}', f'{r.gpc_still_sbx:,}/{r.stores_default_sandboxed:,}', f'{r.decline_still:,}/{r.decline_base:,}',
                f'{100 * r.full_url_share:.0f}% of {r.beacons_default:,}']
        for (lab, x, ha), v in zip(cols, vals):
            ax.text(x, y, v, ha=ha, va='center', fontsize=7, color=C.INK)
    save(fig, 'figS5_per_vendor')
    # the same table as booktabs LaTeX (review: tables must be editable, no shading)
    os.makedirs(os.path.join(FIGDIR, 'tables'), exist_ok=True)
    esc = lambda t: str(t).replace('&', '\\&').replace('%', '\\%')
    num = lambda v: f'{int(v):,}'.replace(',', '{,}')
    L = ['% GENERATED by figures/scripts/figS.py from analysis/outputs/figS5.csv; do not edit by hand.',
         '\\begin{tabular}{lrrrrrrr}', '\\toprule',
         'Vendor & Stores (Default) & \\% of stores & \\% requests sandboxed & GPC: still fires / Default & GPC: still fires, sandbox & '
         'Decline: next page / sandboxed & Beacons with full URL \\\\', '\\midrule']
    for _, r in T.iterrows():
        L.append(f"{esc(VNAME.get(r.vendor, r.vendor))} & {num(r.stores_default)} & {100 * r.share_stores:.0f} & {100 * r.sandbox_share_requests:.0f} & "
                 f"{num(r.gpc_still)}/{num(r.stores_default)} & {num(r.gpc_still_sbx)}/{num(r.stores_default_sandboxed)} & "
                 f"{num(r.decline_still)}/{num(r.decline_base)} & {100 * r.full_url_share:.0f}\\% of {num(r.beacons_default)} \\\\")
    L += ['\\bottomrule', '\\end{tabular}']
    open(os.path.join(FIGDIR, 'tables', 'tableS5_per_vendor.tex'), 'w').write('\n'.join(L) + '\n')


def S6():
    T = table('figS6.csv')
    W, H = 190, 131   # +6 mm for the two banner-recall rows (final audit) and +7 mm for the ethics-exclusion rows (polish, COORD-01)
    fig = fig_mm(W, H)
    groups = [('prechoice_sbx_banner', 'Banner stores: sandboxed pixel fires before any choice', 'Default'),
              ('decline_residual', 'Working Decline clicks: a new sandbox fires on the next page', 'Decline'),
              ('gpc_residual', 'Stores with a Default sandboxed pixel: still fires under GPC', 'GPC')]
    kind_mark = {'main': '', 'definition': ' (definition)', 'robustness': '', 'interval': ' (interval only)'}
    ax = ax_mm(fig, 76, 4, 84, 115, W, H)
    y = 0
    ys, labs = [], []
    heads = []
    for g, title, arm in groups:
        heads.append((y, title))
        y += 1
        for _, r in T[T.outcome == g].iterrows():
            if r.kind == 'interval':
                ax.plot([100 * r.lo, 100 * r.hi], [-y, -y], color=C.ARM[arm]['color'], lw=0.55, solid_capstyle='butt')
                ax.plot([100 * r.p], [-y], marker='|', ms=5, color=C.ARM[arm]['color'], ls='none')
            else:
                ci_dot(ax, -y, 100 * r.p, 100 * r.lo, 100 * r.hi, arm=arm, size=3.8, lw=0.8 if r.kind == 'main' else 0.7)
            n = int(r.n)
            txt = f"{int(r.k):,}/{n:,}" if r.k == r.k and r.k is not None else f"n = {n:,}"
            ax.text(101.5, -y, txt, ha='left', va='center', fontsize=7, color=C.GREY_D)
            ys.append(-y)
            labs.append(r.variant + kind_mark.get(r.kind, ''))
            y += 1
        y += 0.5
    for yy, title in heads:
        ax.text(-74 / 84, -yy, title, transform=ax.get_yaxis_transform(), ha='left', va='center', fontsize=7, fontweight='bold', color=C.INK)
    ax.set_yticks(ys)
    ax.set_yticklabels(labs, fontsize=7)
    ax.tick_params(axis='y', length=0)
    ax.spines['left'].set_visible(False)
    ax.set_ylim(-y + 0.5, 0.6)
    ax.set_xlim(-3, 100)   # review FIG-20: a marker at 0% must not touch its row label
    ax.spines['bottom'].set_bounds(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel('% of stores (95% CI)')
    xgrid(ax)
    for ln in ax.lines:
        ln.set_clip_on(False)
    save(fig, 'figS6_sensitivity')


# ---- referee revision (2026-09-26): two tables written from stats.json (booktabs, no shading) ----
RULE_NOTE = {'pandectes': 'v5: bot rule (hide banner, grant consent)', 'usercentrics': 'user-agent test (effect not traced)',
             'shopify_native': 'isBot flag, telemetry only', 'onetrust': 'server-side bot header (effect unknown)',
             'cookiebot': 'bot list, no match', 'cookiehub': 'bot list, no match'}


def table_cmp_detection():
    """Table S (referee 1, M1f and m7): per consent tool, Default-load stores on which it was detected, its banner was shown,
    and its banner element was present but hidden; plus the automation-sensitive rule found in its saved code."""
    S = stats()['automation']
    esc = lambda t: str(t).replace('&', '\\&').replace('%', '\\%').replace('_', '\\_')
    num = lambda v: f'{int(v):,}'.replace(',', '{,}')
    scanned = set(S['static_scan']['products_scanned'])
    L = ['% GENERATED by figures/scripts/figS.py from analysis/outputs/stats.json (automation/detection, automation/static_scan); do not edit by hand.',
         '\\begin{tabularx}{\\linewidth}{@{}lrrr>{\\raggedright\\arraybackslash}X@{}}', '\\toprule',
         ' & Detected & Banner & Element present, & Rule reacting to automation \\\\',
         'Consent tool & (stores) & shown & but hidden & in the saved code \\\\', '\\midrule']
    for r in S['detection']['rows']:
        note = RULE_NOTE.get(r['cmp'], 'none found' if r['cmp'] in scanned else 'code not saved')
        name = {'shopify_native': "Shopify's banner", 'consentmo': 'Consentmo', 'didomi': 'Didomi', 'consentik': 'Consentik'}.get(r['cmp'], CMP_NAME.get(r['cmp'], r['cmp']))
        L.append(f"{esc(name)} & {num(r['detected'])} & {num(r['banner'])} & {num(r['dom_hidden'])} & {esc(note)} \\\\")
    L += ['\\bottomrule', '\\end{tabularx}']
    open(os.path.join(FIGDIR, 'tables', 'tableS_cmp_detection.tex'), 'w').write('\n'.join(L) + '\n')


def table_projection():
    """The projection to the DNS frame (formerly Fig 5e; editor review): share of storefronts (95% CI) and count (95% interval
    including the frame-size uncertainty)."""
    e = stats()['fig5']['e']
    rows = [('banner_and_prechoice_sbx', 'Banner shown, sandboxed ad request before any choice'),
            ('banner_no_first_layer_reject', 'Banner has no first-layer reject option'),
            ('decline_clicked_still_sbx', 'Decline clicked, a new sandbox still sends on the next page'),
            ('gpc_still_sbx', 'GPC on, sandboxed ad requests continue'),
            ('gpc_declared_sale_pixel_fires', 'GPC on, a pixel that declares sale of data sends')]
    num = lambda v: f'{v:,.0f}'.replace(',', '{,}')
    L = ['% GENERATED by figures/scripts/figS.py from analysis/outputs/stats.json (fig5/e); do not edit by hand.',
         f"% Frame: about {e['population_estimate']:,.0f} DNS-flagged storefronts ({e['frame_estimate_ci']['lo']:,.0f}--{e['frame_estimate_ci']['hi']:,.0f}).",
         '\\begin{tabularx}{\\linewidth}{@{}>{\\raggedright\\arraybackslash}Xrr@{}}', '\\toprule', ' & \\% of storefronts & Storefronts \\\\', 'Outcome & (95\\% CI) & (95\\% interval) \\\\', '\\midrule']
    for k, lab in rows:
        r = e[k]
        if r['count'] > 0:
            L.append(f"{lab} & {100 * r['p']:.1f} ({100 * r['lo']:.1f}--{100 * r['hi']:.1f}) & {num(r['count'])} ({num(r['count_lo'])}--{num(r['count_hi'])}) \\\\")
        else:
            L.append(f"{lab} & 0 (upper bound {100 * r['hi']:.1f}) & 0 (at most {num(r['count_hi'])}) \\\\")
    L += ['\\bottomrule', '\\end{tabularx}']
    open(os.path.join(FIGDIR, 'tables', 'table_projection.tex'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    S2()
    S3()
    S4()
    S5()
    S6()
    table_cmp_detection()
    table_projection()
