"""Figure 5 -- do visitor choices work? Final size 190 x 130 mm.
Data: analysis/outputs/fig5a.csv, fig5b.csv, fig5c.csv, fig5d.csv, stats.json (fig5/e = projection, moved from Fig 6d).
Revised after review:
  * only Decline clicks that worked (banner gone, or an explicit 'no' recorded); failed forced clicks are excluded;
  * 5a compares arms on a fresh page with equal windows (Default and GPC: first 10 s after the load event; Decline:
    sandboxes created on the next page, observed 10 s after its load event), with 95% CIs, arms nudged vertically;
  * 5b uses the fresh-page Decline measure and the explicit-refusal categories; thick = Wilson, thin = cluster bootstrap;
  * 5c: red = a pixel that DECLARES the refused purpose still sent requests (consent failed), outline = allowed by the
    pixel's declaration, or an unload beacon caused by the reload;
  * 5d: one strip of (first third-party 'marketing' sandbox start - consent write) per load, grey arm markers, red only
    on the 'started before the no' region; the two loads right of zero are ringed and named in the note (polish,
    review FIG-10), and the axis runs to +-5 s so that no load is clipped;
  * line weights keep one meaning in the whole figure (review FIG-04): thick = the primary 95% CI (Wilson; in 5e the
    design-based interval), thin = the cluster bootstrap by consent tool (5b only);
  * 5e: projection to all storefronts (moved from Fig 6d), outcomes split, counts include frame-size uncertainty.
All % axes in this figure share 0-100 by 25.
Referee revision (2026-09-26): 5c shows residual classes (declares a refused purpose / only purposes the choice left allowed /
no purpose), with unload beacons of marketing-declaring pixels counted as sends after the refusal and a neutral legend; the
projection (formerly 5e) is a table written by figS.py, which gives 5d more room."""
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from figutil import (THICK, C, arm_handle, ax_mm, ci_dot, ci_dot2, ci_handles, fig_mm, letter, panel_title, save, stats, table, vendor_axis,
                     xgrid)

W, H = 190, 134


def pct_ax(ax, label):
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel(label)
    xgrid(ax)


def panel_a(fig, S):
    T = table('fig5a.csv')
    n = S['fig5']['a']['n_clicked']
    letter(fig, 0, 0, 'a', W, H)
    panel_title(fig, 0, 0, 'Default, Decline and GPC on the same stores', W, H,
                sub=f'{n} stores where the Decline click worked; fresh page, 10 s window')
    ax = ax_mm(fig, 27, 17, 62, 34, W, H)
    rows = C.VENDOR_ORDER + ['Any vendor']
    ys = np.arange(len(rows))[::-1].astype(float)
    for y, v in zip(ys, rows):
        t = T[T.vgroup == v].set_index('arm')
        for a, dy in (('Default', 0.25), ('Decline', 0.0), ('GPC', -0.25)):
            ci_dot(ax, y + dy, 100 * t.loc[a, 'p'], 100 * t.loc[a, 'lo'], 100 * t.loc[a, 'hi'], arm=a, size=3.6, lw=THICK)
    for ln in ax.lines:
        ln.set_clip_on(False)
    ax.axhline(0.5, color=C.GRID, lw=0.5)
    vendor_axis(ax, ys, rows)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    pct_ax(ax, '% of stores with a sandboxed ad request (95% CI)')
    ax.spines['left'].set_visible(False)
    fig.legend([arm_handle('Default', size=3.6), arm_handle('Decline', size=3.6), arm_handle('GPC', size=3.6)],
               ['Default', 'Decline: next page, new sandboxes', 'GPC'],
               loc='upper left', bbox_to_anchor=(5.5 / W, 1 - 9.6 / H), ncol=3, fontsize=7, handletextpad=0.2, columnspacing=0.9,
               borderaxespad=0, borderpad=0, frameon=False)


def panel_b(fig, S):
    T = table('fig5b.csv')
    d = S['fig5']['decline']
    letter(fig, 100, 0, 'b', W, H)
    panel_title(fig, 100, 0, 'Pixels still firing after Decline', W, H, sub='a sandbox created on the next page sent an ad request')
    ax = ax_mm(fig, 146, 17, 40, 34, W, H)
    rows = [('Shopify native banner', 'mode', 'Shopify’s own banner'),
            ('CMP writes to Shopify API', 'mode', 'third-party CMP that\nwrites to Shopify'),
            ('Blocker only / unknown / none', 'mode', 'blocker only / unknown'),
            ('Shopify recorded a refusal', 'refusal', 'Shopify recorded ‘no’'),
            ('marketing still allowed', 'refusal', '‘marketing’ still allowed'),
            ('unknown / no record', 'refusal', 'state unknown')]
    ys = [6.0, 5.0, 4.0, 2.2, 1.2, 0.2]
    labs = []
    for (g, kind, lab), y in zip(rows, ys):
        r = T[(T.group == g) & (T.kind == kind) & (T.arm == 'Decline')].iloc[0]
        ci_dot2(ax, y, 100 * r.p, 100 * r.lo, 100 * r.hi, 100 * r.cb_lo, 100 * r.cb_hi, arm='Decline')
        labs.append(f'{lab} ({int(r.n)})')
    ax.axhline(3.1, color=C.GRID, lw=0.5)
    ax.set_yticks(ys)
    ax.set_yticklabels(labs, linespacing=1.0)
    ax.tick_params(axis='y', length=0)
    ax.spines['left'].set_visible(False)
    ax.set_ylim(-0.4, 6.6)
    pct_ax(ax, '% of stores (95% CI)')
    tr = ax.get_yaxis_transform()
    ax.text(-0.02, 6.62, 'banner type', transform=tr, ha='right', va='bottom', fontsize=7, color=C.GREY_D, style='italic')
    ax.text(-0.02, 2.82, 'after the click', transform=tr, ha='right', va='bottom', fontsize=7, color=C.GREY_D, style='italic')
    fig.legend(ci_handles(), ['Wilson CI', 'cluster bootstrap by consent tool'], loc='upper left', bbox_to_anchor=(105.5 / W, 1 - 9.6 / H),
               ncol=2, fontsize=7, handlelength=1.3, handletextpad=0.3, columnspacing=0.9, borderaxespad=0, borderpad=0, frameon=False)


def panel_c(fig, S):
    """Referee revision (2026-09-26): residual classes after a refusal (referee 1, M3 and m4; referee 2, S3). Solid red = the pixel
    declares a purpose the visitor refused (neutral wording: 'kept sending', not 'consent failed'); red outline = it declares only
    purposes the choice left allowed (Decline: typically sale of data; GPC: marketing or analytics, by Shopify's GPC mapping); grey
    outline = it declares no purpose, so no choice can gate it. Unload beacons of pixels started before the click are sends after
    the refusal and are counted with the same-page sends."""
    T = table('fig5c.csv')
    c = S['fig5']['c']
    letter(fig, 0, 62, 'c', W, H)
    panel_title(fig, 0, 62, 'After Shopify records the refusal', W, H, sub='which sandboxed pixels still sent ad requests?')
    enc = {'refused': dict(color=C.ACCENT, edgecolor='none', lw=0),
           'left_allowed': dict(color=C.SURFACE, edgecolor=C.ACCENT, lw=0.9),
           'none': dict(color=C.SURFACE, edgecolor=C.GREY_D, lw=0.6)}
    h = [Rectangle((0, 0), 1, 1, facecolor=C.ACCENT), Rectangle((0, 0), 1, 1, facecolor=C.SURFACE, edgecolor=C.ACCENT, lw=0.9),
         Rectangle((0, 0), 1, 1, facecolor=C.SURFACE, edgecolor=C.GREY_D, lw=0.6)]
    fig.legend(h, ['declares a purpose the visitor refused', 'declares only purposes the choice left allowed',
                   'declares no purpose (no choice can gate it)'],
               loc='upper left', bbox_to_anchor=(5.5 / W, 1 - 71.6 / H), ncol=1, fontsize=7, handlelength=1.0, handleheight=0.8,
               borderaxespad=0, borderpad=0, labelspacing=0.25, handletextpad=0.4, frameon=False)
    ax = ax_mm(fig, 60, 85, 30, 41, W, H)
    rows = [('GPC', 'declares sale of data', 'declares sale of data'),
            ('GPC', 'declares only purposes GPC leaves allowed', 'declares only purposes GPC leaves allowed'),
            ('GPC', 'declares no purpose', 'declares no purpose'),
            ('Decline', 'started before the click, kept sending (same page or unload beacon)', 'kept sending (same page or unload beacon)'),
            ('Decline', 'new sandbox after the refusal, declares a refused purpose', 'new sandbox declaring a refused purpose'),
            ('Decline', 'declares only purposes the Decline left allowed (any window)', 'declares only purposes Decline left allowed'),
            ('Decline', 'declares no purpose (any window)', 'declares no purpose')]
    ys = [7.9, 7.1, 6.3, 3.9, 3.1, 2.3, 1.5]
    for (blk, bar, lab), y in zip(rows, ys):
        r = T[(T.block == blk) & (T.bar == bar)].iloc[0]
        e = enc[r['cat']]
        ax.barh(y, 100 * r.p, height=0.55, color=e['color'], edgecolor=e['edgecolor'], lw=e['lw'], zorder=2)
        ax.plot([100 * r.lo, 100 * r.hi], [y, y], color=C.INK, lw=THICK, zorder=3, solid_capstyle='butt')
        ax.text(max(100 * r.hi, 1.0) + 3, y, f'{int(r.k)} of {int(r.n):,}', va='center', ha='left', fontsize=7, color=C.INK)
    ax.set_yticks(ys)
    ax.set_yticklabels([r[2] for r in rows])
    ax.tick_params(axis='y', length=0)
    ax.spines['left'].set_visible(False)
    ax.set_ylim(1.0, 9.1)
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(['0', '', '50', '', '100'])
    ax.set_xlabel('% of stores (95% CI)')
    xgrid(ax)
    tr = ax.get_yaxis_transform()
    ax.text(-54.5 / 30, 8.7, f"GPC: Shopify set ‘sale of data: no’ ({c['gpc_n']:,} stores)", transform=tr, fontsize=7,
            color=C.GREY_D, va='center', ha='left', style='italic')
    ax.text(-54.5 / 30, 4.75, f"Decline: Shopify recorded ‘marketing: no’ ({c['decline_n']} stores)", transform=tr, fontsize=7,
            color=C.GREY_D, va='center', ha='left', style='italic')


def panel_d(fig, S):
    D = table('fig5d.csv')
    d = S['fig5']['d']
    letter(fig, 100, 62, 'd', W, H)
    panel_title(fig, 100, 62, 'Race: CMP writes vs third-party pixels', W, H,
                sub='the CMP wrote to Shopify without a click; red: started before the \u2018no\u2019')
    ax = ax_mm(fig, 136, 74, 50, 30, W, H)
    rows = [('deny', 'A0', 'Default'), ('deny', 'A2', 'GPC'), ('grant', 'A0', 'Default'), ('grant', 'A2', 'GPC')]
    ys = [3.3, 2.4, 1.2, 0.3]
    lim = 5.0   # review FIG-10: wide enough for every load (the earliest first start is 4.35 s before the write), none clipped
    ax.add_patch(Rectangle((-lim, 1.85), lim, 2.0, facecolor=C.ACCENT, alpha=0.13, edgecolor='none', zorder=0))
    rng = np.random.default_rng(7)
    labs = []
    late = []
    for (ch, arm, a), y in zip(rows, ys):
        g = D[(D.change == ch) & (D.arm == arm)]
        x = (g.dt_first / 1000).values
        yy = y + rng.uniform(-0.22, 0.22, len(x))
        st = C.ARM[a]
        ax.plot(x, yy, marker=st['marker'], ms=2.8, ls='none', mfc=st['mfc'], mec=st['mec'], mew=0.5, alpha=0.85, zorder=3)
        if ch == 'deny':
            late += [(xi, yi) for xi, yi in zip(x, yy) if xi >= 0]
        word = '\u2018no\u2019' if ch == 'deny' else '\u2018yes\u2019'
        labs.append(f'{word} written, {a} load ({len(g)})')
    # ring the 'no' loads whose first third-party sandbox started after the write (named in the note below the panel)
    for xi, yi in late:
        ax.plot([xi], [yi], marker='o', ms=6.5, mfc='none', mec=C.INK, mew=0.6, ls='none', zorder=4)
    ax.axvline(0, color=C.INK, lw=0.6, zorder=2)
    ax.set_xscale('symlog', linthresh=0.1, linscale=0.6)
    ax.set_xlim(-lim, lim)
    ax.set_xticks([-3, -1, -0.1, 0, 0.1, 1, 3])
    ax.set_xticklabels(['\u22123', '\u22121', '\u22120.1', '0', '0.1', '1', '3'])
    ax.minorticks_off()
    ax.set_yticks(ys)
    ax.set_yticklabels(labs)
    ax.tick_params(axis='y', length=0)
    ax.spines['left'].set_visible(False)
    ax.set_ylim(-0.3, 3.85)
    ax.set_xlabel('first sandbox start minus consent write (s)', labelpad=1)
    xgrid(ax)
    r = d['deny']
    lag = r['first_after_lag_ms']
    assert len(lag) == len(late)
    fig.text(105.5 / W, 1 - 115.5 / H,
             f"\u2018no\u2019: {r['pixels_before']} of {r['pixels']} third-party \u2018marketing\u2019 sandboxes started first,\n"
             f"{r['pixels_before_ctapi']} before Shopify\u2019s consent script was requested; ringed: the {len(lag)} loads\n"
             f"whose first sandbox started after the \u2018no\u2019. \u2018Yes\u2019: all {d['grant']['pixels']} after.",
             fontsize=7, color=C.GREY_D, va='top', ha='left', linespacing=1.1)


def main():
    S = stats()
    fig = fig_mm(W, H)
    panel_a(fig, S)
    panel_b(fig, S)
    panel_c(fig, S)
    panel_d(fig, S)
    # panel e (projection) moved to a table (figures/tables/table_projection.tex, written by figS.py); editor review
    save(fig, 'fig5_choices')


if __name__ == '__main__':
    main()
