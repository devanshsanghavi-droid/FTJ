"""Figure 4 -- blocked on paper: what consent tools declare vs what sandboxed pixels do. Final size 190 x 116 mm.
Data: analysis/outputs/fig4a.csv, fig4b.csv, fig4c.csv, stats.json.
Revised after review:
  * 4a blocklist row = the vendor the blocklist names fired from its own sandboxed pixel (vendor-matched);
    a vertical-bar glyph (not an arm shape) marks the 'pixel declares marketing' subset;
  * 4b presence comes from the pixel configuration only (apps by apiClientId, custom pixels by name), cells show k/n,
    cells with n < 10 are greyed, a 4-step ordinal blue ramp without Google's hex, and a marginal row gives each
    tool's share of stores whose Shopify default already denies marketing (the confounder of the comparison);
  * 4c is a dot panel restricted to blocklisted vendors whose Shopify pixel is configured on that store, split by
    origin, with the classic-tag / unconfigured entries shown separately.
Referee revision (2026-09-26): 4a compares like with like (any sandboxed ad pixel in every row; a cross marks the blocklisted
vendor's own pixel), leads with the stores whose CMP wrote no 'yes', and adds the region-default comparison with stores that
have no readable declaration; 4b labels Shopify's own banner 'Shopify banner'; 4c draws intervals clustered by store."""
import numpy as np
from matplotlib.patches import Rectangle

from figutil import (C, arm_handle, ax_mm, ci_dot, fig_mm, letter, panel_title, save, stats, table, vendor_axis, within_dot,
                     within_handle, xgrid)

W, H = 190, 128
CMP_NAME = {'pandectes': 'Pandectes', 'onetrust': 'OneTrust', 'shopify_native': 'Shopify banner', 'cookiebot': 'Cookiebot',
            'osano': 'Osano', 'iubenda': 'iubenda', 'other': 'other'}


def declared_dot(ax, y, p, lo, hi, size=4.6, zorder=3):
    """The blocklisted vendor's OWN pixel fired (vendor-matched): a cross, a glyph used nowhere else."""
    ax.plot([lo, hi], [y, y], color=C.INK, lw=0.8, solid_capstyle='butt', zorder=zorder - 1)
    ax.plot([p], [y], marker='X', ms=size, mfc=C.INK, mec=C.SURFACE, mew=0.4, ls='none', zorder=zorder)


def declared_handle(size=4.6):
    from matplotlib.lines import Line2D
    return Line2D([], [], marker='X', ms=size, mfc=C.INK, mec=C.SURFACE, mew=0.4, ls='none')


def panel_a(fig, S):
    """Referee revision (2026-09-26): like-for-like markers. Circle = any sandboxed ad pixel fired before any choice, in every row;
    cross = the blocklisted vendor's own pixel (blocklist rows only). The primary row (stores whose CMP wrote no 'yes') comes first;
    the region-default rows compare blocklist stores with stores that have no readable declaration, among stores whose CMP wrote no
    'yes' (referee 2, S4; the falsification test of prediction P1); the dagger marks the row that includes the CMP 'yes' writers."""
    A = S['fig4']['a']
    b, lf = A['blocklist'], A['like_for_like']
    letter(fig, 0, 0, 'a', W, H)
    panel_title(fig, 0, 0, 'Setup says ‘no’ before any choice', W, H, sub='did a sandboxed ad pixel fire anyway? (stores)')
    ax = ax_mm(fig, 51, 17.5, 39, 45.5, W, H)
    pr = b['primary']
    rows = [  # (y, label, any-sandboxed record, declared-vendor record or None)
        (7.0, f"CMP wrote no ‘yes’ (n = {pr['fired']['n']})", pr['any_sbx'], pr['fired']),
        (6.15, f"all blocklist stores (n = {b['any_sbx']['n']})†", b['any_sbx'], b['declared_vendor_fired_sbx']),
        (4.75, f"blocklist (n = {lf['allowed_no_yes']['blocklist']['n']})", lf['allowed_no_yes']['blocklist'], lf['allowed_no_yes']['blocklist_declared_vendor']),
        (3.9, f"no readable declaration (n = {lf['allowed_no_yes']['reference']['n']})", lf['allowed_no_yes']['reference'], None),
        (2.5, f"blocklist (n = {lf['denied_no_yes']['blocklist']['n']})", lf['denied_no_yes']['blocklist'], lf['denied_no_yes']['blocklist_declared_vendor']),
        (1.65, f"no readable declaration (n = {lf['denied_no_yes']['reference']['n']})", lf['denied_no_yes']['reference'], None),
        (0.45, f"CMP told Shopify\n‘marketing: no’ (n = {A['cpapi_deny']['any_sbx']['n']})", A['cpapi_deny']['any_sbx'], None)]
    for y, lab, r1, r2 in rows:
        if r2 is None:
            ci_dot(ax, y, 100 * r1['p'], 100 * r1['lo'], 100 * r1['hi'], arm='Default')
        else:
            ci_dot(ax, y + 0.17, 100 * r1['p'], 100 * r1['lo'], 100 * r1['hi'], arm='Default')
            declared_dot(ax, y - 0.19, 100 * r2['p'], 100 * r2['lo'], 100 * r2['hi'])
    for ln in ax.lines:
        ln.set_clip_on(False)
    ax.set_yticks([r[0] for r in rows])
    ax.set_yticklabels([r[1] for r in rows], linespacing=1.0)
    ax.tick_params(axis='y', length=0, pad=3)
    ax.spines['left'].set_visible(False)
    for yl in (5.55, 3.2, 1.0):
        ax.axhline(yl, color=C.GRID, lw=0.5)
    tr = ax.get_yaxis_transform()
    x0 = -45.5 / 39
    hdr = dict(transform=tr, fontsize=7, color=C.GREY_D, va='center', ha='left', style='italic', zorder=5,
               bbox=dict(facecolor=C.SURFACE, edgecolor='none', pad=0.6))   # keeps gridlines out of the group headers
    ax.text(x0, 7.65, f"blocklist names an ad vendor ({b['any_sbx']['n']} stores, {b['n_cmps']} tools)", **hdr)
    ax.text(x0, 5.3, "default ‘allowed until choice’, CMP wrote no ‘yes’", **hdr)
    ax.text(x0, 3.0, "default ‘denied until consent’, CMP wrote no ‘yes’", **hdr)
    ax.set_ylim(-0.05, 7.95)
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel('% of stores (95% CI)', labelpad=2)
    xgrid(ax)
    fig.legend([declared_handle(), arm_handle('Default')], ['the blocklisted vendor’s own pixel fired', 'any sandboxed ad pixel fired'],
               loc='upper left', bbox_to_anchor=(5.5 / W, 1 - 9.4 / H), ncol=1, fontsize=7, handletextpad=0.3, borderaxespad=0, borderpad=0,
               labelspacing=0.2, frameon=False)
    ys_ = b['yes_writers_summary']
    fig.text(5.5 / W, 1 - 70.2 / H, f"† includes the {ys_['n']} stores whose CMP itself wrote ‘yes’ without a click, {ys_['bot_rule']} of them\n"
             f"because it detected our automated browser (Pandectes’ bot rule)", fontsize=7, color=C.GREY_D, va='top', ha='left', linespacing=1.1)


def panel_b(fig, S):
    T = table('fig4b.csv')
    b = S['fig4']['b']
    letter(fig, 99, 0, 'b', W, H)
    panel_title(fig, 99, 0, 'Pre-choice firing by vendor and consent tool', W, H,
                sub="banner stores whose configuration lists the vendor’s sandboxed pixel")
    cmps = b['cmps']
    rows = C.VENDOR_ORDER + ['All vendors']
    x0, y0, cw, rh = 121.0, 16, 9.8, 7.0
    nr = len(rows) + 1
    ax = ax_mm(fig, x0, y0, cw * len(cmps), rh * nr, W, H)
    nmin = S['design']['min_cell_n_heatmap']
    for j, cm in enumerate(cmps):
        for i, v in enumerate(rows):
            r = T[(T.cmp == cm) & (T.vgroup == v)].iloc[0]
            y = nr - 1 - i
            if r.n < nmin:
                ax.add_patch(Rectangle((j, y), 1, 1, facecolor=C.GREY_XL, edgecolor=C.SURFACE, lw=1.2))
                ax.text(j + 0.5, y + 0.5, f'{int(r.k)}/{int(r.n)}', ha='center', va='center', fontsize=7, color=C.GREY_D)
                continue
            col = C.ord_color(100 * r.p)
            ax.add_patch(Rectangle((j, y), 1, 1, facecolor=col, edgecolor=C.SURFACE, lw=1.2))
            tc = C.ink_on(col)
            ax.text(j + 0.5, y + 0.66, f'{100 * r.p:.0f}%', ha='center', va='center', fontsize=7, color=tc, fontweight='bold')
            ax.text(j + 0.5, y + 0.28, f'{int(r.k)}/{int(r.n)}', ha='center', va='center', fontsize=7, color=tc)
        # marginal row: share of the tool's banner stores whose Shopify default already denies marketing
        r = T[(T.cmp == cm) & (T.vgroup == 'region_denied')].iloc[0]
        ax.add_patch(Rectangle((j, 0), 1, 1, facecolor=C.SURFACE, edgecolor=C.GREY_L, lw=0.6))
        ax.text(j + 0.5, 0.66, f'{100 * r.p:.0f}%', ha='center', va='center', fontsize=7, color=C.INK)
        ax.text(j + 0.5, 0.28, f'{int(r.k)}/{int(r.n)}', ha='center', va='center', fontsize=7, color=C.GREY_D)
    ax.axhline(2, color=C.INK, lw=0.6)
    ax.axhline(1, color=C.INK, lw=0.6)
    ax.set_xlim(0, len(cmps))
    ax.set_ylim(0, nr)
    ax.set_xticks(np.arange(len(cmps)) + 0.5)
    nb = {c: T[(T.cmp == c)].n_banner_stores.iloc[0] for c in cmps}
    ax.set_xticklabels([f'{CMP_NAME.get(c, c)} ({nb[c]})' for c in cmps], fontsize=7, rotation=35, ha='right', rotation_mode='anchor')
    ax.tick_params(axis='x', length=0, pad=2)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ys = list(np.arange(len(rows))[::-1] + 1.5) + [0.5]
    vendor_axis(ax, ys, rows + ['default denies\nmarketing'])
    ax.set_yticklabels(rows + ['default denies\nmarketing'], linespacing=1.0)
    fig.text((x0 + cw * len(cmps) / 2) / W, 1 - (y0 + rh * nr + 14.0) / H, 'consent tool (banner stores)', ha='center', va='top', fontsize=8)
    # ordinal legend, below the heatmap
    ly = y0 + rh * nr + 20.5
    lx = x0 - 2
    fig.text(lx / W, 1 - (ly + 1.6) / H, '% fired:', fontsize=7, va='center', ha='left')
    items = [(C.ORD_BLUE[i], f'{lo}\u2013{hi}') for i, (lo, hi) in enumerate(zip(C.ORD_EDGES[:-1], C.ORD_EDGES[1:]))] + [(C.GREY_XL, f'n < {nmin}')]
    xx = lx + 10
    steps = [10.5, 12, 12, 13.5, 0]
    for (colr, lab), stp in zip(items, steps):
        axl = ax_mm(fig, xx, ly, 3.4, 3.2, W, H)
        axl.add_patch(Rectangle((0, 0), 1, 1, facecolor=colr, edgecolor='none'))
        axl.axis('off')
        fig.text((xx + 4.2) / W, 1 - (ly + 1.6) / H, lab, fontsize=7, va='center', ha='left')
        xx += stp


def panel_c(fig, S):
    c = S['fig4']['c']
    letter(fig, 0, 78, 'c', W, H)
    panel_title(fig, 0, 78, 'Blocklisted vendors, by configured Shopify pixel', W, H,
                sub=f"{c['n_pairs']} ad-vendor entries declared blocked before any choice on {c['n_stores']} stores")
    ax = ax_mm(fig, 52, 91, 38, 28, W, H)
    g1, g2 = c['cfg'], c['nocfg']
    rows = [(g1['sandbox'], 'from its Shopify sandbox'), (g1['page'], 'from an ordinary page script'), (g1['any'], 'by any route'),
            (g2['any'], 'by any route')]
    ys = [4.4, 3.45, 2.5, 0.3]
    for (r, lab), y in zip(rows, ys):
        # referee 2, S1: entries cluster within stores, so the interval is Korn-Graubard clustered by store
        ci_dot(ax, y, 100 * r['p'], 100 * r['kg_lo'], 100 * r['kg_hi'], arm='Default')
        ax.text(101.5, y, f"{r['k']}/{r['n']}", va='center', ha='left', fontsize=7, color=C.GREY_D)
    for ln in ax.lines:
        ln.set_clip_on(False)
    ax.set_yticks(ys)
    ax.set_yticklabels([r[1] for r in rows])
    ax.tick_params(axis='y', length=0)
    ax.spines['left'].set_visible(False)
    ax.set_ylim(-0.3, 4.85)
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel('% of entries that fired before any choice (95% CI, clustered by store)')
    xgrid(ax)
    ax.axhline(1.55, color=C.GRID, lw=0.5)
    tr = ax.get_yaxis_transform()
    ax.text(-46.5 / 38, 4.87, f"vendor’s Shopify pixel configured ({g1['n']} entries, {g1['n_stores']} stores)", transform=tr, fontsize=7,
            color=C.GREY_D, va='bottom', ha='left', style='italic')
    # review FIG-03: 4 of these entries did fire from a Shopify sandbox (a pixel not mapped to the vendor), so the label
    # says 'identified', and installation of the rest is unknown rather than 'not installed'
    ax.text(-46.5 / 38, 0.72, f"no configured sandboxed pixel of the vendor identified: classic\ntag, OPEN pixel or installation unknown ({g2['n']} entries)", transform=tr, fontsize=7,
            color=C.GREY_D, va='bottom', ha='left', style='italic', linespacing=1.0, zorder=5,
            bbox=dict(facecolor=C.SURFACE, edgecolor='none', pad=0.6))   # keeps the gridlines out of the two-line label


def main():
    S = stats()
    fig = fig_mm(W, H)
    panel_a(fig, S)
    panel_b(fig, S)
    panel_c(fig, S)
    save(fig, 'fig4_blocked_on_paper')


if __name__ == '__main__':
    main()
