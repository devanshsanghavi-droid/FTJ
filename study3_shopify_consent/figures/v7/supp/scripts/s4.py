"""Supplementary Figure S4 (v7) -- audit and repeat agreement (the detail behind main Fig 2d). Binding:
../../DESIGN_V7.md; the v7 helpers and mark sizes of s2.py. One row of four plots that share their plot top and bottom
line (asserted: nature-figure's panel-alignment gate).

Figure contract (DESIGN_V7 section 1). Claim (the caption title): the crawler's banner, reject and click labels agreed
with screenshots in almost every audited load, and repeated loads agreed almost perfectly.
a-c  (the label audit, one decision each) 2 x 2 matrices of counts in the one matrix grammar of the supplement
     (DESIGN_V7 section 8.8, = Fig S7b): square 12 x 12 mm cells split by two crossing 0.6 pt SP_AXIS rules -- no
     border, no fills, no ticks; the count of loads in each cell in 7 pt SP_FG (here the counts are the point: the only
     numbers in the figure besides ticks, read from analysis/outputs/figS4.csv and registered). Crawler label (rows) x
     screenshot audit (columns), both Yes / No; the diagonal is where the two agree (the caption says so). No tint: the
     pale brick key cell of Fig S7b means 'consent lost', and nothing here is. The three matrices share their rows, so
     the rows are named once, at the left of a ('Crawler', Yes / No); b and c carry only their columns. a's 'No' row was
     not audited (the sample was drawn from loads with a detected banner): it is drawn as a definite merged row -- the
     vertical rule stops at the horizontal one -- that reads 'not audited' in muted 7 pt, so the matrix is whole.
     The agreement 'k of n' is in the caption, not under the matrix.
d    (the repeat robustness, the widest cell) Cohen's kappa per comparison (Default vs repeat, GPC vs repeat, GPC vs
     Brave) as a vertical dot plot on open L axes: filled SP_FG circles = stores, open circles (white, SP_FG edge) =
     store x vendor pairs, 95 % bootstrap CIs as uncapped 0.75 pt lines; a comparison without any disagreement has a
     degenerate interval and no line. The y axis is truncated (the caption says so): ticks 0.90 / 0.95 / 1.00 (two
     decimals; trace_supp.py TICKS[4] lists exactly these); the spines meet at 0.90 and the left spine runs 2 mm past
     1.00, so the marks at kappa = 1 have air above them (DESIGN_V7 section 6). The key (frameless, muted 7 pt, two
     rows) sits right of the plot, clear of it and level with no data row, so its filled dot never reads as a mark.
     The agree counts and kappas are in the caption (stats.json validation/*). No colour: nothing here is lost consent
     or a consent moment (grey for context; the figure's point is position -- the diagonal, and kappa at 1).
All four plots share their top (TOP) and their bottom line."""
from matplotlib.lines import Line2D

from s2 import MEW, MS, W, check_composite, ci_line, dot, plot_rect_mm, tw_mm
from supp_common import CSVN, S, fs, finish, table, write_registry

CELL = 12.0                               # matrix cells are square, 12 x 12 mm (= Fig S7b)
TOP, PH = 6.0, 2 * CELL                   # every plot: top and height (mm); one top line and one bottom line
H = 39.0
M_LEFT_A = 13.0                           # a's matrix left edge: room for 'Crawler' and Yes / No (the shared rows)
M_LEFT_BC = 1.0                           # b's and c's matrix left edge (their rows are a's)
M_RIGHT = 1.0                             # white right of each matrix inside its cell
W_A = M_LEFT_A + PH + M_RIGHT             # 38
W_BC = M_LEFT_BC + PH + M_RIGHT           # 26
W_D = W - W_A - 2 * W_BC - 3 * fs.GUTTER_MM
X = [0.0, W_A + fs.GUTTER_MM, W_A + W_BC + 2 * fs.GUTTER_MM, W_A + 2 * W_BC + 3 * fs.GUTTER_MM]
RULE = dict(color=fs.SP_AXIS, lw=fs.V7_LW['axis'], solid_capstyle='butt', zorder=1)
NOT_AUDITED = 'not audited'
MARK = fs.SP_FG                           # d's marks and intervals

# (panel, crawler labels Yes / No, audit labels Yes / No, stats key of the agreement); None = row not audited
MATS = [('banner', ['banner detected', None], ['banner visible', 'no banner visible'], 'supp/S4/banner_precision'),
        ('reject', ['reject found', 'no reject found'], ['reject visible', 'no reject visible'],
         'supp/S4/reject_agreement'),
        ('click', ['banner dismissed', 'banner still shown'], ['banner gone', 'banner still shown'],
         'supp/S4/click_flag_agreement')]


def matrix(i):
    pn, rows, cols, agree_key = MATS[i]
    T = table('figS4.csv')
    w = W_A if i == 0 else W_BC
    m_left = M_LEFT_A if i == 0 else M_LEFT_BC
    fig = fs.panel(w, H)
    ax = fs.axes_mm(fig, m_left, TOP, 2 * CELL, PH)
    ax.set_xlim(0, 2)
    ax.set_ylim(0, 2)
    for sp in ax.spines.values():
        sp.set_visible(False)
    agree = 0
    for ri, rl in enumerate(rows):
        y = 1.5 - ri                                          # 'Yes' row on top
        if rl is None:                                        # not audited (a's 'No' row): one definite merged row
            ax.text(1.0, y, NOT_AUDITED, ha='center', va='center_baseline', fontsize=fs.FS['label'],
                    color=fs.SP_MUTED)
            continue
        for ci, cl in enumerate(cols):
            q = T[(T.panel == pn) & (T.crawler == rl) & (T.audit == cl)]
            assert len(q) == 1, (pn, rl, cl)
            k = int(q.k.iloc[0])
            agree += k if ri == ci else 0
            ax.text(ci + 0.5, y, CSVN(k, f'figS4.csv:{pn}/{rl}/{cl}'), ha='center', va='center_baseline',
                    fontsize=fs.FS['label'], color=fs.SP_FG)
    assert agree == S['supp']['S4'][agree_key.split('/')[-1]]['k'], pn       # the caption's 'k of n' is the diagonal
    assert sum(int(v) for v in T[T.panel == pn].k) == S['supp']['S4'][agree_key.split('/')[-1]]['n'], pn
    # the two crossing rules (Fig S7b's grammar); a merged row stops the vertical rule at the horizontal one
    ax.plot([0, 2], [1, 1], **RULE)
    ax.plot([1, 1], [1 if rows[1] is None else 0, 2], **RULE)
    ax.set_xticks([0.5, 1.5])
    ax.set_xticklabels(['Yes', 'No'], fontsize=fs.FS['cat'], color=fs.SP_FG)
    ax.tick_params(axis='both', length=0, pad=2.5)
    ax.set_xlabel('Screenshot audit', labelpad=2.0)
    if i == 0:                                                # the shared rows, named once
        ax.set_yticks([1.5, 0.5])
        ax.set_yticklabels(['Yes', 'No'], fontsize=fs.FS['cat'], color=fs.SP_FG)
        ax.set_ylabel('Crawler', labelpad=2.0)
    else:
        ax.set_yticks([])
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    if i == 0:
        x0 = ax.yaxis.label.get_window_extent(r).x0 / fig.dpi * 25.4
        assert x0 >= fs.INDENT_MM - 0.05, f'{pn}: y title starts {x0:.2f} mm from the edge'
        tw = ax.texts[-1].get_window_extent(r).width / fig.dpi * 25.4
        assert tw <= 2 * CELL - 3.0, f'{pn}: {NOT_AUDITED!r} crowds its row'
    xl = ax.xaxis.label.get_window_extent(r)
    assert xl.x0 >= 0 and xl.x1 <= fig.bbox.x1, f'{pn}: the column title leaves the panel'
    finish(fig, f'figS4{"abc"[i]}_{pn}')
    return plot_rect_mm(fig, ax)


# ------------------------------------------------------------------------------------------------ panel d
PAIRS = [('A0_vs_A0r', 'Default vs\nrepeat'), ('A2_vs_A2r', 'GPC vs\nrepeat'), ('A2_vs_V1', 'GPC vs\nBrave')]
UNITS = [('', 'Stores', True), ('_vendor', 'Store × vendor pairs', False)]      # filled = stores, open = pairs
DX = 0.14                                                                       # half the distance within a pair
D_LEFT = 12.5                                                                   # plot left (room for κ and ticks)
KEY_GAP = 5.0                                                                   # mm from the plot to the key
KTICKS = [0.90, 0.95, 1.00]                                                     # two decimals (trace TICKS[4])
AIR_TOP_MM = 2.0                                                                # white above the marks at kappa = 1
OPEN_MEW = 0.8                                                                  # an open marker's edge (0.6-1.2 pt)


def key_width():
    """Width (mm) of d's key: handle, pad and the longer label (legend handlelength 0.9, handletextpad 0.4 em)."""
    em = fs.FS['legend'] / fs.PT_PER_MM
    return (0.9 + 0.4) * em + max(tw_mm(u[1], fs.FS['legend']) for u in UNITS)


def kappa():
    fig = fs.panel(W_D, H)
    pw = W_D - D_LEFT - KEY_GAP - key_width() - 0.8
    ax = fs.axes_mm(fig, D_LEFT, TOP, pw, PH)
    ax.set_xlim(-0.5, len(PAIRS) - 0.5)
    ax.set_xticks(range(len(PAIRS)))
    ax.set_xticklabels([p[1] for p in PAIRS], fontsize=fs.FS['cat'], linespacing=1.1, color=fs.SP_FG)
    ax.tick_params(axis='x', length=0, pad=3.0)
    ax.spines['bottom'].set_bounds(-0.5, len(PAIRS) - 0.5)
    k_bot = KTICKS[0]
    k_top = 1.0 + AIR_TOP_MM / (PH - AIR_TOP_MM) * (1.0 - k_bot)               # 1.00 sits AIR_TOP_MM below the top
    ax.set_ylim(k_bot, k_top)                                                   # spines meet at 0.90
    ax.set_yticks(KTICKS)
    ax.set_yticklabels([fs.fmt_dec(t, 2) for t in KTICKS])
    ax.set_ylabel('Cohen’s κ', labelpad=2.5)
    V = S['validation']
    assert min(V[b + s]['lo'] for b, _ in PAIRS for s, _, _ in UNITS) > KTICKS[0]       # every interval on the axis
    assert max(V[b + s]['hi'] for b, _ in PAIRS for s, _, _ in UNITS) <= 1.0
    for i, (base, _) in enumerate(PAIRS):
        for (suf, _, filled), dx in zip(UNITS, (-DX, DX)):
            r = V[base + suf]
            if r['hi'] - r['lo'] > 1e-9:                                         # no disagreement: no interval
                ci_line(ax, r['lo'], r['hi'], i + dx, MARK, orient='v')
            dot(ax, i + dx, r['kappa'], dict(marker='o', ms=MS, mfc=MARK if filled else fs.SURFACE, mec=MARK,
                                             mew=MEW if filled else OPEN_MEW))
    hs = [Line2D([], [], ls='none', marker='o', ms=MS, mfc=MARK if f else fs.SURFACE, mec=MARK,
                 mew=MEW if f else OPEN_MEW) for _, _, f in UNITS]
    # the key: two rows, frameless, muted 7 pt, KEY_GAP right of the plot and centred on its height (away from the
    # kappa = 1 line where the last pair's marks sit); a figure legend, so it is not part of the axes' extent
    x_key = D_LEFT + pw + KEY_GAP
    y_mid = TOP + PH / 2
    lg = fig.legend(hs, [u[1] for u in UNITS], loc='center left', frameon=False,
                    bbox_to_anchor=(x_key / W_D, 1 - y_mid / H), fontsize=fs.FS['legend'], ncol=1,
                    handlelength=0.9, handletextpad=0.4, labelspacing=0.5, borderaxespad=0.0, borderpad=0.0,
                    labelcolor=fs.SP_MUTED)
    fig.canvas.draw()
    rr = fig.canvas.get_renderer()
    lgb = lg.get_window_extent(rr)
    axb = ax.get_window_extent(rr)
    mm = fig.dpi / 25.4
    assert lgb.x0 >= axb.x1 + (KEY_GAP - 0.6) * mm, 'd: the key crowds the plot'
    assert lgb.x1 <= fig.bbox.x1 - 0.3 * mm, 'd: the key leaves the panel'
    assert lgb.y0 >= axb.y0 and lgb.y1 <= axb.y1, 'd: the key leaves the plot band'
    # the marks at kappa = 1 sit AIR_TOP_MM below the plot top
    y1 = ax.transData.transform((0, 1.0))[1]
    assert abs((axb.y1 - y1) / mm - AIR_TOP_MM) < 0.05
    finish(fig, 'figS4d_kappa')
    return plot_rect_mm(fig, ax)


if __name__ == '__main__':
    check_composite('figS4.tex', {'a': (X[0], 0, W_A, H), 'b': (X[1], 0, W_BC, H), 'c': (X[2], 0, W_BC, H),
                                  'd': (X[3], 0, W_D, H)}, H)
    with fs.v7_context():
        rects = [matrix(i) for i in range(3)] + [kappa()]
    # alignment gate (nature-figure): the four plots share their top and their bottom line; the three matrices are
    # equally spaced (one shared row axis)
    assert max(r[1] for r in rects) - min(r[1] for r in rects) < 0.01
    assert max(r[3] for r in rects) - min(r[3] for r in rects) < 0.01
    gaps = [X[i + 1] + rects[i + 1][0] - (X[i] + rects[i][2]) for i in range(2)]
    assert abs(gaps[0] - gaps[1]) < 0.01, gaps
    write_registry('figS4')
    print(f'figS4: a {W_A:g} x {H:g} mm, b-c {W_BC:g} x {H:g} mm, d {W_D:g} x {H:g} mm; matrices {gaps[0]:g} mm apart')
