"""Figure 6 -- what reaches the vendors. Final size 190 x 121 mm.
Data: analysis/outputs/fig6a.csv, fig6b_store_c.csv, fig6c.csv, stats.json.
Revised after review: Fig 6 now carries one message (what reaches the vendors). The validation panel moved to
Fig S4d and the projection to Fig 5e.
  * 6a plots the SANDBOXED beacons' full-URL share (the claim). Polish (review FIG-01): intervals are Korn-Graubard
    intervals clustered by store (the store bootstrap was degenerate for small rows), the store count of every arm is
    given per row, and estimates from fewer than 10 stores are not drawn;
  * 6b (new, review: Google Consent Mode) shows how often ad requests carry a refusal signal in their URL;
  * 6c (Store C) splits every load into a sandbox sub-row and an 'other' sub-row, marks TikTok requests that carry
    the per-video code with a star and other code-carrying requests with a dot (Google included), and reports the
    Decline load as pre-click / after the reload.
Panel letters follow reading order (review FIG-19): a top left, b top right, c the full-width strip below."""
import numpy as np
from matplotlib.lines import Line2D

from figutil import C, arm_handle, ax_mm, ci_dot, fig_mm, letter, panel_title, save, stats, table, vendor_axis, xgrid

W, H = 190, 121


def panel_a(fig, S):
    T = table('fig6a.csv')
    T = T[T.origin == 'sandboxed']
    letter(fig, 0, 0, 'a', W, H)
    panel_title(fig, 0, 0, 'The full landing URL reaches ad vendors', W, H,
                sub='sandboxed ad beacons carrying the page URL with our test code')
    ax = ax_mm(fig, 27, 17, 50, 38, W, H)
    rows = C.VENDOR_ORDER + ['All']
    ys = np.arange(len(rows))[::-1].astype(float)
    nmin = S['design']['min_stores_row']
    cols = [('Default', 103), ('Decline', 118), ('GPC', 133)]
    for y, v in zip(ys, rows):
        for (arm, xc), dy in zip(cols, (0.25, 0.0, -0.25)):
            r = T[(T.vgroup == v) & (T.arm == arm)].iloc[0]
            small = r.n_stores < nmin
            if r.n > 0 and not small:
                ci_dot(ax, y + dy, 100 * r.p, 100 * r.kg_lo, 100 * r.kg_hi, arm=arm, size=3.4, lw=0.7)
            ax.text(xc + 11, y, f'{int(r.n_stores):,}', va='center', ha='right', fontsize=7, color=C.GREY_M if small else C.GREY_D)
    # column heads: the arm glyphs, then 'stores'
    for arm, xc in cols:
        st_ = C.ARM[arm]
        ax.plot([xc + 7.5], [len(rows) - 0.28], marker=st_['marker'], ms=3.4, mfc=st_['mfc'], mec=st_['mec'], mew=0.9, ls='none', clip_on=False)
    ax.text(103, len(rows) + 0.15, 'stores per arm', va='bottom', ha='left', fontsize=7, color=C.GREY_D)
    for ln in ax.lines:
        ln.set_clip_on(False)
    ax.axhline(0.5, color=C.GRID, lw=0.5)
    vendor_axis(ax, ys, [r if r != 'All' else 'All vendors' for r in rows])
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel('% of sandboxed ad beacons (95% CI)')
    xgrid(ax)
    ax.spines['left'].set_visible(False)
    fig.legend([arm_handle('Default', size=3.4), arm_handle('Decline', size=3.4), arm_handle('GPC', size=3.4)], ['Default', 'Decline load', 'GPC'],
               loc='upper left', bbox_to_anchor=(5.5 / W, 1 - 9.6 / H), ncol=3, fontsize=7, handletextpad=0.2, columnspacing=0.9,
               borderaxespad=0, borderpad=0, frameon=False)


def panel_b(fig, S):
    T = table('fig6c.csv')
    T = T[T.origin == 'all']
    fl = S['fig5']['flags']
    letter(fig, 104, 0, 'b', W, H)
    panel_title(fig, 104, 0, 'Do requests carry the refusal?', W, H, sub='ad requests with a refusal signal in the URL')
    ax = ax_mm(fig, 133, 17, 53, 22, W, H)
    rows = ['Google', 'Microsoft', 'Other vendors']
    ys = [2, 1, 0]
    for y, g in zip(ys, rows):
        for arm, dy in (('Default', 0.25), ('Decline', 0.0), ('GPC', -0.25)):
            r = T[(T.group == g) & (T.arm == arm)].iloc[0]
            ci_dot(ax, y + dy, 100 * r.p, 100 * r.lo, 100 * r.hi, arm=arm, size=3.4, lw=0.7)
    for ln in ax.lines:
        ln.set_clip_on(False)
    labs = ['Google (Consent Mode,\nnpa, rdp, us_privacy)', 'Microsoft (asc=D)', 'all other vendors']
    vendor_axis(ax, ys, rows)
    ax.set_yticklabels(labs, linespacing=1.0)
    ax.set_ylim(-0.55, 2.5)
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel('% of ad requests, any origin (95% CI)')
    xgrid(ax)
    ax.spines['left'].set_visible(False)
    fig.legend([arm_handle('Default', size=3.4), arm_handle('Decline', size=3.4), arm_handle('GPC', size=3.4)],
               ['Default', 'Decline: next page', 'GPC'], loc='upper left', bbox_to_anchor=(109.5 / W, 1 - 9.6 / H), ncol=3, fontsize=7,
               handletextpad=0.2, columnspacing=0.9, borderaxespad=0, borderpad=0, frameon=False)
    rd, rg = fl['resid_decline_fresh'], fl['resid_gpc']
    gd = fl['google_beacons_gcs']['Decline_next']
    fig.text(109.5 / W, 1 - 47.2 / H,
             f"Google beacons on the next page after Decline: {gd['G100']:,}\n"
             f"‘storage denied’ (G100), {gd['G111']:,} ‘granted’ (G111), {gd['none']:,} no state.\n"
             f"Stores where every remaining sandboxed request carried\n"
             f"a refusal: {rd['stores_all_flagged']} of {rd['stores']} after Decline, {rg['stores_all_flagged']} of {rg['stores']} under GPC.",
             fontsize=7, color=C.GREY_D, va='top', ha='left', linespacing=1.1)


def panel_c(fig, S):
    D = table('fig6b_store_c.csv')
    cr = S['fig6']['b']['store_c']
    after = S['fig6']['b']['store_c_after_decline']
    pre = S['fig6']['b']['store_c_pre_click']
    letter(fig, 0, 68, 'c', W, H)
    panel_title(fig, 0, 68, "A creator’s per-video code (Store C)", W, H,   # store pseudonymized until disclosure is complete (final audit)
                sub="landing page from the creator’s video link, 5 loads; each load split into its sandbox and its other ad requests")
    ax = ax_mm(fig, 36, 81, 124, 30.5, W, H)
    arms = [('A0', 'Default'), ('A0r', 'Default, repeat'), ('A1', 'Decline'), ('A2', 'GPC'), ('A2r', 'GPC, repeat')]
    tmax = 21
    ys, labs = [], []
    y = 0
    base = {}
    for a, lab in arms[::-1]:
        base[a] = y
        ys += [y + 1.1, y]
        labs += [f'{lab}: sandbox', 'other']
        y += 2.75
    for a, lab in arms:
        d = D[D.arm == a]
        y0 = base[a]
        ax.axhspan(y0 - 0.4, y0 + 1.6, color=C.GREY_XL, lw=0, zorder=0)
        for _, r in d.iterrows():
            yy = y0 + (1.1 if r.sandbox else 0.0)
            col = C.VENDOR.get(r.vgroup, C.GREY_M)
            hh = 0.28 if r.kind != 'library' else 0.13
            ax.plot([r.t_ms / 1000] * 2, [yy - hh, yy + hh], color=col, lw=0.9, solid_capstyle='butt', zorder=2)
            if r.has_creator_token:
                if r.vgroup == 'TikTok':
                    ax.plot([r.t_ms / 1000], [yy + 0.44], marker='*', ms=5.0, mfc=C.INK, mec=C.INK, mew=0.3, ls='none', zorder=5)
                else:
                    ax.plot([r.t_ms / 1000], [yy + 0.4], marker='o', ms=1.7, color=C.INK, ls='none', zorder=4)
        info = cr[a]
        if info['t_banner'] is not None:
            ax.plot([info['t_banner'] / 1000] * 2, [y0 - 0.4, y0 + 1.6], color=C.INK, lw=0.6, zorder=3)
        if info['t_click'] is not None:
            st = C.ARM['Decline']
            ax.plot([info['t_click'] / 1000], [y0 + 0.55], marker=st['marker'], ms=4.4, mfc=st['mfc'], mec=st['mec'], mew=1.0, zorder=5)
        if info['t_next_nav'] is not None:
            tn = info['t_next_nav'] / 1000
            ax.plot([tn, tn], [y0 - 0.4, y0 + 1.6], color=C.GREY_D, lw=0.6, ls=(0, (2, 1.5)), zorder=3)
            ax.text(tn - 0.15, y0 + 1.55, 'reload', fontsize=7, color=C.GREY_D, va='top', ha='right')
        if a == 'A1':
            txt = f"before click {pre['n_vendors']}; after\nreload {after['n_vendors']} ({after['n_vendors_sandboxed']} sandboxed)"
        else:
            txt = f"{info['n_vendors_with_token']} ({info['n_vendors_with_token_nongoogle']} non-Google)"
        ax.text(tmax + 0.4, y0 + 0.55, txt, va='center', ha='left', fontsize=7, color=C.INK, linespacing=1.0)
    ax.text(tmax + 0.4, y - 1.05, 'vendors with the code', va='bottom', ha='left', fontsize=7, color=C.GREY_D)
    ax.set_yticks(ys)
    ax.set_yticklabels(labs)
    ax.tick_params(axis='y', length=0)
    ax.spines['left'].set_visible(False)
    ax.set_ylim(-0.45, y - 1.1)
    ax.set_xlim(0, tmax)
    ax.set_xticks([0, 5, 10, 15, 20])
    ax.set_xlabel('time since navigation start (s)', labelpad=1)
    h = [Line2D([], [], color=C.VENDOR['TikTok'], lw=1.4), Line2D([], [], color=C.VENDOR['Google'], lw=1.4),
         Line2D([], [], color=C.VENDOR['Meta'], lw=1.4), Line2D([], [], color=C.VENDOR['Reddit/other'], lw=1.4),
         Line2D([], [], marker='*', ms=5.0, mfc=C.INK, mec=C.INK, ls='none'), Line2D([], [], marker='o', ms=2.0, color=C.INK, ls='none'),
         Line2D([], [], color=C.INK, lw=0.8), Line2D([], [], marker='s', ms=4, mfc=C.SURFACE, mec=C.GREY_D, ls='none')]
    fig.legend(h, ['TikTok', 'Google', 'Meta', 'Reddit/other', 'TikTok + video code', 'other vendor + code',
                   'banner visible', 'Decline click'],
               loc='upper left', bbox_to_anchor=(5.5 / W, 1 - 76.4 / H), ncol=8, fontsize=7, handlelength=1.0, handletextpad=0.3,
               columnspacing=0.7, borderaxespad=0, borderpad=0, frameon=False)


def main():
    S = stats()
    fig = fig_mm(W, H)
    panel_a(fig, S)
    panel_b(fig, S)
    panel_c(fig, S)
    save(fig, 'fig6_reach')   # renamed from fig6_reach_validation (validation moved to Fig S4d)


if __name__ == '__main__':
    main()
