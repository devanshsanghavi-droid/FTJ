"""Figure 3 -- pixels fire before any choice. Final size 190 x 122 mm.
Data: analysis/outputs/fig3a.csv, fig3b.csv, fig3c.csv, stats.json.
Revised after review: one % axis (0-100 by 25) for every store-share panel; within-arm contrasts use a vertical-bar
glyph, never an arm shape; headline rows show Wilson (thick) and cluster-bootstrap (thin) intervals; 3b shows the
PAIRED gap (banner time minus first sandboxed request) with the 250 ms polling interval marked; 3c uses the revised
origin classes (relay only when the stack holds nothing but Shopify / store scripts).
Referee revision (2026-09-26): 3a marks 'no banner' with an open circle, so the vertical bar keeps one meaning ('pixel
declaring marketing', 3d and 4a); 3c counts frames nested in a LAX sandbox as sandboxed and leaves out CORS preflights."""
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

from figutil import (THICK, THIN, C, arm_handle, ax_mm, ci_dot2, ci_handles, fig_mm, letter, open_dot, open_handle, panel_title, save, stats, table,
                     vendor_axis, within_dot, within_handle, xgrid, ygrid)

W, H = 190, 122


def pct_ax(ax):
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    xgrid(ax)


def panel_a(fig, S):
    T = table('fig3a.csv')
    letter(fig, 0, 0, 'a', W, H)
    panel_title(fig, 0, 0, 'Pre-choice firing, by vendor', W, H, sub='sandboxed ad requests in the Default load')
    ax = ax_mm(fig, 27, 17, 62, 36, W, H)
    rows = C.VENDOR_ORDER + ['Any vendor']
    ys = np.arange(len(rows))[::-1].astype(float)
    for y, v in zip(ys, rows):
        col = C.VENDOR.get(v)
        rb = T[(T.vgroup == v) & (T.group == 'banner')].iloc[0]
        rn = T[(T.vgroup == v) & (T.group == 'no_banner')].iloc[0]
        if v == 'Any vendor':
            ci_dot2(ax, y + 0.17, 100 * rb.p, 100 * rb.lo, 100 * rb.hi, 100 * rb.cb_lo, 100 * rb.cb_hi, arm='Default')
            ax.plot([100 * rn.cb_lo, 100 * rn.cb_hi], [y - 0.17] * 2, color=C.INK, lw=THIN, solid_capstyle='butt', zorder=1)
            open_dot(ax, y - 0.17, 100 * rn.p, 100 * rn.lo, 100 * rn.hi, lw=THICK)
        else:
            # every row: thick = Wilson, thin = cluster bootstrap by consent tool (review FIG-04: one meaning per line weight)
            ci_dot2(ax, y + 0.17, 100 * rb.p, 100 * rb.lo, 100 * rb.hi, 100 * rb.cb_lo, 100 * rb.cb_hi, arm='Default', color=col)
            ax.plot([100 * rn.cb_lo, 100 * rn.cb_hi], [y - 0.17] * 2, color=col, lw=THIN, solid_capstyle='butt', zorder=1)
            open_dot(ax, y - 0.17, 100 * rn.p, 100 * rn.lo, 100 * rn.hi, color=col, lw=THICK)
    ax.axhline(0.5, color=C.GRID, lw=0.5)
    vendor_axis(ax, ys, rows)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    pct_ax(ax)
    ax.set_xlabel('% of stores (95% CI)')
    ax.spines['left'].set_visible(False)
    nb, nn = S['fig3']['a']['any']['banner']['n'], S['fig3']['a']['any']['no_banner']['n']
    fig.legend([arm_handle('Default'), open_handle()] + ci_handles(),
               [f'banner shown (n = {nb:,})', f'no banner (n = {nn:,})', 'Wilson CI', 'cluster bootstrap'],
               loc='upper left', bbox_to_anchor=(5.5 / W, 1 - 9.6 / H), ncol=4, fontsize=7, handletextpad=0.3, columnspacing=0.8,
               handlelength=1.3, borderaxespad=0, borderpad=0, frameon=False)


def ecdf(x):
    x = np.sort(np.asarray(x))
    return np.concatenate([[x[0]], x]), np.concatenate([[0], np.arange(1, len(x) + 1) / len(x)])


def panel_b(fig, S):
    T = table('fig3b.csv')
    b = S['fig3']['b']
    poll = S['design']['banner_poll_ms'] / 1000
    letter(fig, 100, 0, 'b', W, H)
    panel_title(fig, 100, 0, 'Pixel before banner', W, H,
                sub=f"{b['n']} banner stores with a pre-choice sandboxed ad request, paired per store")
    ax = ax_mm(fig, 115, 17, 71, 36, W, H)
    lim = S['design']['timeline_axis_s'] / 2
    g = T.gap / 1000
    ax.add_patch(Rectangle((0, 0), poll, 1.0, facecolor=C.GREY_XL, edgecolor='none', zorder=0))
    x, y = ecdf(np.clip(g, -lim, lim))
    # plot the share of stores whose gap is AT LEAST x: 1 - ECDF read from the right
    ax.step(x, 1 - y, where='post', color=C.INK, lw=1.2, zorder=3)
    ax.axvline(0, color=C.INK, lw=0.6, zorder=2)
    ax.axvline(poll, color=C.GREY_M, lw=0.6, ls=(0, (2, 1.5)), zorder=2)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(['0', '25', '50', '75', '100'])
    ax.set_ylabel('% of stores with gap ≥ x')
    ax.set_xlabel('banner visible minus first sandboxed request (s)')
    ygrid(ax)
    k0, k1 = b['before_banner'], b['before_banner_by_poll']
    ax.plot([0], [k0['p']], marker='o', ms=3.2, color=C.INK, zorder=4)
    ax.plot([poll], [k1['p']], marker='o', ms=3.2, color=C.INK, zorder=4)
    ax.text(-0.12, k0['p'] - 0.02, f"{100 * k0['p']:.0f}%: request first", ha='right', va='top', fontsize=7, color=C.INK)
    ax.text(poll + 0.12, k1['p'] + 0.04, f"{100 * k1['p']:.0f}%: first by more than\none polling interval ({1000 * poll:.0f} ms)",
            ha='left', va='bottom', fontsize=7, color=C.INK, linespacing=1.0)
    ax.text(-lim + 0.1, 0.3, '← banner came first', ha='left', va='bottom', fontsize=7, color=C.GREY_D)
    ax.text(lim - 0.1, 0.92, 'pixel came first →', ha='right', va='bottom', fontsize=7, color=C.GREY_D)


def panel_c(fig, S):
    T = table('fig3c.csv').set_index('vgroup')
    c = S['fig3']['c']
    letter(fig, 0, 64, 'c', W, H)
    panel_title(fig, 0, 64, 'Where pre-choice ad requests come from', W, H, sub='share of all ad requests in the Default load')
    ax = ax_mm(fig, 27, 84, 70, 29, W, H)
    rows = C.VENDOR_ORDER + ['All']
    ys = np.arange(len(rows))[::-1].astype(float)
    hgt = 0.62
    for y, v in zip(ys, rows):
        left = 0.0
        for o in C.ORIGIN_ORDER:
            w = 100 * T.loc[v, o]
            if w <= 0:
                continue
            st = C.ORIGIN[o]
            if o == 'sandbox':
                ax.add_patch(Rectangle((left, y - hgt / 2), w, hgt, facecolor=C.SURFACE, edgecolor=C.GREY_M, hatch='//////', lw=0, zorder=2))
            else:
                ax.add_patch(Rectangle((left, y - hgt / 2), w, hgt, facecolor=st['facecolor'], edgecolor='none', zorder=2))
            left += w
            if left < 99.9:
                ax.plot([left, left], [y - hgt / 2, y + hgt / 2], color=C.SURFACE, lw=0.8, zorder=3)
        lab = f"{100 * T.loc[v, 'sandbox']:.0f}%"
        if v == 'All':
            r = c['share_sandbox_boot']
            lab = f"{100 * r['p']:.0f}% ({100 * r['lo']:.0f}–{100 * r['hi']:.0f})"
            ax.plot([100 * r['lo'], 100 * r['hi']], [y - hgt / 2 - 0.12] * 2, color=C.INK, lw=THICK, solid_capstyle='butt', zorder=4, clip_on=False)
        ax.text(102, y, lab, va='center', ha='left', fontsize=7, color=C.INK)
        ax.text(124, y, f"{int(T.loc[v, 'n_requests']):,}", va='center', ha='left', fontsize=7, color=C.GREY_D)
    ax.text(102, len(rows) - 0.35, 'sandboxed', ha='left', va='bottom', fontsize=7, color=C.GREY_D)
    ax.text(124, len(rows) - 0.35, 'requests', ha='left', va='bottom', fontsize=7, color=C.GREY_D)
    ax.axhline(0.5, color=C.GRID, lw=0.5)
    vendor_axis(ax, ys, [r if r != 'All' else 'All vendors' for r in rows])
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.6, len(rows) - 0.45)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel('% of ad requests')
    ax.spines['left'].set_visible(False)
    handles = [Patch(facecolor=C.SURFACE, edgecolor=C.GREY_M, hatch='//////', lw=0), Patch(facecolor=C.GREY_M), Patch(facecolor=C.GREY_D),
               Patch(facecolor=C.GREY_L)]
    labels = ['Shopify sandbox (worker, iframe, frames inside it)', 'relayed by Shopify (only Shopify code in the stack)', 'Shopify OPEN pixel',
              'ordinary page scripts and frames']
    fig.legend(handles, labels, loc='upper left', bbox_to_anchor=(5.5 / W, 1 - 73.2 / H), ncol=2, fontsize=7, handlelength=1.3,
               handleheight=0.9, columnspacing=0.9, handletextpad=0.35, borderaxespad=0, borderpad=0, frameon=False)


def panel_d(fig, S):
    d = S['fig3']['d']
    letter(fig, 140, 64, 'd', W, H)
    panel_title(fig, 140, 64, "Shopify’s region default", W, H, sub='banner stores, Default load')
    ax = ax_mm(fig, 160, 89, 27, 24, W, H)
    groups = [('opt_out', "‘allowed\nuntil choice’\n(n = %d)" % d['opt_out']['any_sbx']['n']),
              ('opt_in', "‘denied\nuntil consent’\n(n = %d)" % d['opt_in']['any_sbx']['n'])]
    ys = [1, 0]
    for (key, lab), y in zip(groups, ys):
        r = d[key]['any_sbx']
        ci_dot2(ax, y + 0.16, 100 * r['p'], 100 * r['lo'], 100 * r['hi'], 100 * r['cb_lo'], 100 * r['cb_hi'], arm='Default')
        r = d[key]['mkt_sbx']
        ax.plot([100 * r['cb_lo'], 100 * r['cb_hi']], [y - 0.16] * 2, color=C.INK, lw=THIN, solid_capstyle='butt', zorder=1)
        within_dot(ax, y - 0.16, 100 * r['p'], 100 * r['lo'], 100 * r['hi'], lw=THICK)
    ax.set_yticks(ys)
    ax.set_yticklabels([g[1] for g in groups], linespacing=1.0)
    ax.tick_params(axis='y', length=0)
    ax.spines['left'].set_visible(False)
    ax.set_ylim(-0.55, 1.5)
    pct_ax(ax)
    ax.set_xticks([0, 50, 100])
    ax.set_xticks([25, 75], minor=True)
    ax.xaxis.grid(True, which='minor', color=C.GRID, linewidth=0.4)
    ax.set_xlabel('% of stores (95% CI)')
    fig.legend([arm_handle('Default'), within_handle()], ['any sandboxed ad pixel', "pixel declaring ‘marketing’"],
               loc='upper left', bbox_to_anchor=(145.5 / W, 1 - 73.2 / H), ncol=1, fontsize=7, handletextpad=0.3, borderaxespad=0, borderpad=0,
               labelspacing=0.2, frameon=False)
    g = d['opt_in_mkt_fired_after_cmp_grant']
    fig.text(145.5 / W, 1 - 81.0 / H, f"{g['k']} of the {g['n']} ‘denied’ stores with a\n‘marketing’ pixel: the CMP\ntold Shopify ‘yes’ first",
             fontsize=7, color=C.GREY_D, va='top', ha='left', linespacing=1.0)


def main():
    S = stats()
    fig = fig_mm(W, H)
    panel_a(fig, S)
    panel_b(fig, S)
    panel_c(fig, S)
    panel_d(fig, S)
    save(fig, 'fig3_prechoice')


if __name__ == '__main__':
    main()
