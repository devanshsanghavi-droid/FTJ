"""Figure 1b (situating data) and 1c (one real page load). Final sizes: 1b 66 x 79 mm (right of 1a), 1c 190 x 47 mm.
Data: analysis/outputs/fig1b.csv, fig1c_timeline.csv, stats.json.
Revised after review: 1b shows the relationship (banner vs no banner, split fires / does not fire) plus Shopify's region
default; 1c gives every vendor group its own sub-row (colour is redundant), tall ticks = data beacons, short ticks =
library loads, a dot above = the request carries the full page URL with our test code."""
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from figutil import THICK, THIN, C, ax_mm, ci_handles, fig_mm, letter, save, stats, vendor_axis


def fig1b():
    S = stats()
    f = S['fig1b']
    W, H = 66, 79
    fig = fig_mm(W, H)
    letter(fig, 0, 0.5, 'b', W, H)
    # non-causal title (review CE-12): the panel compares banner and no-banner stores, it does not test the banner's effect
    fig.text(6 / W, 1 - 0.9 / H, 'Pixels fire, banner or not', fontsize=8, fontweight='bold', va='top', ha='left')
    fig.text(6 / W, 1 - 5.0 / H, f"{S['design']['n_main']:,} popular Shopify stores, Default load", fontsize=7, color=C.GREY_D, va='top')
    ax = ax_mm(fig, 2.5, 10.5, 61, 45, W, H)
    hb = 0.30
    rows = [(2.0, 'banner_fires', f"Consent banner shown ({f['banner_fires']['n']} stores)", 'accent'),
            (1.0, 'nobanner_fires', f"No banner ({f['nobanner_fires']['n']} stores)", 'grey')]
    for y, key, lab, style in rows:
        r = f[key]
        p = 100 * r['p']
        if style == 'accent':
            ax.add_patch(Rectangle((0, y - hb / 2), p, hb, facecolor=C.ACCENT, edgecolor='none', zorder=2))
        else:
            # editor review: solid grey, not hatched -- hatching means 'runs in a sandbox' in Figs 1a and 3c; both bars measure the same outcome
            ax.add_patch(Rectangle((0, y - hb / 2), p, hb, facecolor=C.GREY_M, edgecolor='none', zorder=2))
        ax.add_patch(Rectangle((p, y - hb / 2), 100 - p, hb, facecolor=C.SURFACE, edgecolor=C.GREY_D, lw=0.5, zorder=2))
        ax.add_patch(Rectangle((0, y - hb / 2), 100, hb, facecolor='none', edgecolor=C.GREY_D, lw=0.5, zorder=3))
        # CIs below the bar (thick = Wilson, thin = cluster bootstrap by consent tool), labels above it
        yc = y - hb / 2 - 0.1
        ax.plot([100 * r['cb_lo'], 100 * r['cb_hi']], [yc, yc], color=C.INK, lw=THIN, solid_capstyle='butt', zorder=4)
        ax.plot([100 * r['lo'], 100 * r['hi']], [yc, yc], color=C.INK, lw=THICK, solid_capstyle='butt', zorder=4)
        ax.plot([p, p], [yc - 0.05, y - hb / 2], color=C.INK, lw=0.5, zorder=4)
        ax.text(0, y + hb / 2 + 0.26, lab, va='bottom', ha='left', fontsize=7, color=C.INK)
        ax.text(0.5, y + hb / 2 + 0.04, f"{p:.0f}% pixel fires before any choice", va='bottom', ha='left', fontsize=7,
                color=C.INK, fontweight='bold' if style == 'accent' else 'normal')
        ax.text(99.5, y + hb / 2 + 0.04, f"{100 - p:.0f}% not", va='bottom', ha='right', fontsize=7, color=C.GREY_D)
    # Shopify's region default
    r = f['region_allowed']
    y = 0.0
    p = 100 * r['p']
    ax.add_patch(Rectangle((0, y - hb / 2), p, hb, facecolor=C.INK, edgecolor='none', zorder=2))
    ax.add_patch(Rectangle((0, y - hb / 2), 100, hb, facecolor='none', edgecolor=C.GREY_D, lw=0.5, zorder=3))
    # thin: cluster bootstrap by consent tool (the default is set per consent product, so it is strongly clustered; review FIG-04)
    ax.plot([100 * r['cb_lo'], 100 * r['cb_hi']], [y - hb / 2 - 0.1] * 2, color=C.INK, lw=THIN, solid_capstyle='butt', zorder=4)
    ax.plot([100 * r['lo'], 100 * r['hi']], [y - hb / 2 - 0.1] * 2, color=C.INK, lw=THICK, solid_capstyle='butt', zorder=4)
    ax.plot([p, p], [y - hb / 2 - 0.15, y - hb / 2], color=C.INK, lw=0.5, zorder=4)
    ax.text(0, y + hb / 2 + 0.26, f"Shopify\u2019s region default ({r['n']:,} stores)", va='bottom', ha='left', fontsize=7, color=C.INK)
    ax.text(0.5, y + hb / 2 + 0.04, f"{p:.0f}% ‘allowed until choice’", va='bottom', ha='left', fontsize=7, color=C.INK)
    ax.set_ylim(-0.42, 2.66)
    ax.set_xlim(0, 100)
    ax.set_yticks([])
    for sp in ('left', 'bottom'):
        ax.spines[sp].set_visible(False)
    ax.set_xticks([])
    fig.legend(ci_handles(), ['95% CI (Wilson)', 'cluster bootstrap by consent tool'], loc='upper left', bbox_to_anchor=(2.5 / W, 1 - 60.0 / H),
               ncol=1, fontsize=7, handlelength=1.4, borderaxespad=0, borderpad=0, labelspacing=0.25, frameon=False)
    fig.text(2.5 / W, 1 - 69.5 / H, 'vantage point: California, USA', fontsize=7, color=C.GREY_D, va='top')
    save(fig, 'fig1b_situating_data')


def fig1c():
    S = stats()['fig1c']
    tl = table('fig1c_timeline.csv')
    W, H = 190, 47
    fig = fig_mm(W, H)
    letter(fig, 0, 0.5, 'c', W, H)
    fig.text(6 / W, 1 - 0.9 / H, 'One real page load: ad requests before any choice', fontsize=8, fontweight='bold', va='top', ha='left')
    ax = ax_mm(fig, 30, 7.5, 156, 31.0, W, H)
    tmax = 10.0
    groups = [v for v in C.VENDOR_ORDER if (tl.sandbox & (tl.vgroup == v)).any()]
    rows = groups + ['not sandboxed\n(all vendors)']
    ypos = {r: len(rows) - 1 - i for i, r in enumerate(rows)}
    ypos[rows[-1]] = -0.45      # the two-line 'not sandboxed' row sits a little apart from the vendor rows
    bot = -1.05
    top = len(rows) + 0.35
    ax.add_patch(Rectangle((0, bot), tmax, top - bot, facecolor=C.GREY_XL, edgecolor='none', zorder=0))
    for r in rows:
        ax.axhline(ypos[r], color=C.SURFACE, lw=0.8, zorder=1)
    for _, q in tl.iterrows():
        row = q.vgroup if q.sandbox else 'not sandboxed\n(all vendors)'
        y = ypos[row]
        col = C.VENDOR[q.vgroup] if q.sandbox else C.GREY_M
        hh = 0.34 if q.kind != 'library' else 0.16
        ax.plot([q.t_ms / 1000] * 2, [y - hh, y + hh], color=col, lw=1.0, solid_capstyle='butt', zorder=3)
        if q.has_full_url:
            ax.plot([q.t_ms / 1000], [y + 0.46], marker='o', ms=1.6, color=C.INK, ls='none', zorder=4)
    tb = S['t_banner'] / 1000
    ax.plot([tb, tb], [bot, top], color=C.INK, lw=0.9, zorder=5)
    ax.text(tb + 0.06, top - 0.1, f'banner visible ({tb:.1f} s)', ha='left', va='top', fontsize=7, color=C.INK)
    t2 = S['t_first_sandboxed'] / 1000
    first = tl[tl.sandbox].iloc[0]
    ax.text(t2 - 0.08, ypos[first.vgroup], f"first sandboxed ({t2:.1f} s)", ha='right', va='center', fontsize=7, color=C.INK)
    ax.text(tmax - 0.08, top - 0.1, 'no choice made during the whole load', ha='right', va='top', fontsize=7, color=C.GREY_D)
    ax.set_xlim(0, tmax)
    ax.set_ylim(bot, top)
    ys = [ypos[r] for r in rows]
    vendor_axis(ax, ys, rows)
    ax.set_yticklabels(rows, linespacing=1.0)
    # editor review: the vendor rows hold ONLY sandboxed requests; a bracket says so (every other ad request is in the bottom row)
    tr = ax.get_yaxis_transform()
    xb = -23.5 / 156          # 23.5 mm left of the plot area (axes fraction of its 156 mm width)
    y0_, y1_ = ypos[groups[-1]] - 0.35, ypos[groups[0]] + 0.35
    ax.plot([xb + 0.012, xb, xb, xb + 0.012], [y0_, y0_, y1_, y1_], color=C.GREY_D, lw=0.6, transform=tr, clip_on=False)
    ax.text(xb - 0.012, (y0_ + y1_) / 2, 'sandboxed\n(worker or iframe)', transform=tr, rotation=90, ha='right', va='center', fontsize=7,
            color=C.GREY_D, linespacing=1.0)
    ax.spines['left'].set_visible(False)
    ax.set_xticks(range(0, 11))
    ax.set_xlabel('time since navigation start (s)', labelpad=1)
    h = [Line2D([], [], color=C.INK, lw=1.0, marker='|', ms=7, ls='none'), Line2D([], [], color=C.INK, lw=1.0, marker='|', ms=3.5, ls='none'),
         Line2D([], [], marker='o', ms=1.8, color=C.INK, ls='none')]
    fig.legend(h, ['data beacon', 'library (script) load', 'carries the full page URL with our test code'], loc='upper left',
               bbox_to_anchor=(80 / W, 1 - 1.0 / H), ncol=3, fontsize=7, handlelength=0.8, columnspacing=1.2, frameon=False, borderaxespad=0, borderpad=0)
    save(fig, 'fig1c_page_load_timeline')


from figutil import table  # noqa: E402

if __name__ == '__main__':
    fig1b()
    fig1c()
