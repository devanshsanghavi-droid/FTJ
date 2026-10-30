"""Supplementary Figure S8 (v7) -- after a choice, new sandboxes kept sending ad requests, and where a consent tool wrote
'no' without a click a sandbox had almost always started first.

Binding: figures/v7/DESIGN_V7.md (worked example figures/v7/fig1). fs.v7_context(): open L axes, Arial 7 / 6 pt,
markers 3.5 pt, uncapped 0.75 pt intervals, no gridlines, no panel titles, no numbers in the plots (tick labels only;
every count is in the caption). Loads keep the project's arm shapes in the sciplot neutrals (Default filled near-black
circle, Decline open square, GPC filled grey triangle); those shapes mean the loads only (a, b). c draws no marker
shapes: it takes Fig 5b's bar form, names, colours and key order. Grey for context, colour for signal: LEAK brick = a
sandbox that started before the CMP's 'no' (consent lost; in c, a pixel declaring a refused purpose), HONOUR slate =
after a 'yes' (the comparison), EVENT amber = the CMP's consent write. One pre-mixed tint: TINT LEAK, the key area of
the hero d. Every key is frameless and sits above its plot (a: one row; c, d: one column), never among the marks.

Figure contract (DESIGN_V7 section 1): one claim -- after a choice new sandboxes kept firing, and where a CMP wrote 'no'
without a click the sandboxes had usually started before the write.
  a  the population, by vendor: Fig 5a's estimates, repeated (the caption says so) as rows on b's 0-100 scale so that
     the vendors can be read against b's subgroups ('Stores with a new sandbox request (%)', stores where the Decline click worked):
     Default, Decline (fresh page) and GPC, Wilson 95% CIs in the colour of the mark; 'Any vendor' set apart below;
     the arm key in one row above the plot (as Fig 5a).                                             stats fig5/a
  b  the comparison across subgroups: the fresh-page measure of a (any vendor) by banner type and by the state Shopify
     recorded after the click, each group named in muted grey above its rows; open squares (Decline), Wilson CIs; the
     same 0-100 scale as a.                                       stats fig5/b/<group>/decline_residual
  c  what the still-sending pixels declare, by window: Fig 5b's bar form -- one thin bar per class from 0, in Fig 5b's
     names, colours and key order (a refused purpose: brick; only purposes left allowed: grey NEUTRAL; no purpose:
     dark grey GREY_D), with its Wilson 95% CI as an uncapped 0.75 pt SP_AXIS line (Fig 5b's interval colour); the classes
     overlap (a store can be in several), so the bars stand side by side, never stacked; a class with no store has no
     bar (its interval starts at 0); the key above the plot.                         stats fig5/c/composition
  d  (hero; the mechanism in time) Fig 5c's raster on Fig 5c's symmetric-log race axis (fs.RACE_AXIS_TITLE): one row
     per load in which a CMP wrote 'marketing: no' or 'yes' without a click, four blocks ('no' Default, 'no' GPC, 'yes'
     Default, 'yes' GPC) set apart by gaps (a wider gap between the 'no' and the 'yes' blocks, so the two grey ticks
     after a 'no' are not read as 'yes' rows), rows sorted by the load's first third-party marketing sandbox; one tick per
     load at that sandbox's start minus the write; brick = before a 'no', grey = after a 'no', slate = after a 'yes';
     amber rule = the write (named above the plot); a pale brick ground (TINT LEAK) between the brick ticks and the
     rule: the time each of those sandboxes ran before the 'no' (the key area, on the ticks' own coordinates); the key
     above the plot.
                                                         analysis/outputs/fig5d.csv; supp derived s8d_race_loads
Layout (mm; must equal figS8.tex, asserted): row 1 a | b (92 x H1); row 2 c | d (W_C, W_D x H2; d the hero); 6 mm
gutters; the plots of a row share their top and x-axis line (asserted). Drawn values are registered (fmt 'raw') in
panels/figS8_numbers.csv. Nothing but tick labels is printed as a number.
"""
import numpy as np
from matplotlib.patches import Polygon, Rectangle
from matplotlib.ticker import FixedLocator, NullFormatter

from s6 import (LW_CI, astyle, bb_mm, cat_y, check_alignment, check_composite, ci_h, dot, key_column, key_row,
                mark, mark_sd, no_digits, no_overlaps, off_spines, plot_box, rows_ylim, share, tw_mm, value_axis,
                within)
from supp_common import fs, finish, table, write_registry

LQ, RQ = '‘', '’'
G = fs.GUTTER_MM
W_A = W_B = 92.0
W_C, W_D = 66.0, 118.0
assert abs(W_A + G + W_B - fs.FIG_W_MM) < 1e-9 and abs(W_C + G + W_D - fs.FIG_W_MM) < 1e-9
H1, H2 = 64.0, 67.0
FIG_H = H1 + G + H2
CELLS = {'a': (0, 0, W_A, H1), 'b': (W_A + G, 0, W_B, H1), 'c': (0, H1 + G, W_C, H2), 'd': (W_C + G, H1 + G, W_D, H2)}
TOP1, PH1 = 7.5, 45.5                 # row 1: the band above holds a's key (one row)
TOP2, PH2 = 12.5, 43.5                # row 2: the band above holds c's and d's keys (one column each)
KEY1_BASE = 3.6                       # row 1: baseline of a's key (mm from the panel top)
KEY2_BASE, KEY2_PITCH = 3.4, 3.2      # row 2: first baseline and pitch of the key columns
R_PAD = 2.5
ARM_NAME = {'Default': 'Default', 'Decline': 'Decline, fresh page', 'GPC': 'GPC'}
ARMS3 = [('Default', -0.3), ('Decline', 0.0), ('GPC', 0.3)]           # dodge (rows run top to bottom)
ROWS_V = fs.VENDOR_ORDER + ['Any vendor']
YS_V = np.array(list(range(len(fs.VENDOR_ORDER))) + [len(fs.VENDOR_ORDER) + 0.7])


# ------------------------------------------------------------------------------------------------ a
def panel_a():
    fig = fs.panel(W_A, H1)
    left = np.ceil(fs.INDENT_MM + max(tw_mm(v, fs.FS['cat']) for v in ROWS_V) + 1.6)
    pw = W_A - left - R_PAD
    ax = fs.axes_mm(fig, left, TOP1, pw, PH1)
    pts = []
    for y, v in zip(YS_V, ROWS_V):
        vv = v.replace('/', '~1')
        for z, (arm, dy) in enumerate(ARMS3):
            p, lo, hi = share(f'fig5/a/{vv}/{arm}')
            st = astyle(arm)
            ci_h(ax, y + dy, lo, hi, st['color'], zorder=3 + z)
            dot(ax, p, y + dy, st, zorder=4 + z)
            pts += [(lo, y + dy), (hi, y + dy), (p, y + dy)]
    value_axis(ax, 'x', 0, 100, 25, length_mm=pw)                    # DESIGN_V7 6: share axes run 0-100 (as b)
    ax.set_xlabel('Stores with a new sandbox request (%)')            # Fig 5a's title (these are its per-vendor values)
    cat_y(ax, YS_V, ROWS_V)
    rows_ylim(ax, YS_V[0] + ARMS3[0][1], YS_V[-1] + ARMS3[-1][1], PH1, pad_mm=1.6)
    # the arm key in one row above the plot, right-aligned to it (Fig 5a's key; muted 7 pt, marks as drawn)
    _, kx0 = key_row(fig, left + pw, KEY1_BASE, [('marker', astyle(a), ARM_NAME[a]) for a, _ in ARMS3], gap=3.0)
    assert kx0 >= left, 'a: the key reaches over the row names'
    off_spines(fig, ax, pts[2::3], 'a')
    within(fig, ax, 'a')
    no_overlaps(fig, 'a')
    no_digits(fig, 'a')
    finish(fig, 'figS8a_vendor')
    return plot_box(fig, ax)


# ------------------------------------------------------------------------------------------------ b
B_ROWS = [('Shopify native banner', f'Shopify{RQ}s banner'), ('CMP writes to Shopify API', 'CMP writes to Shopify'),
          ('Blocker only / unknown / none', 'Blocker only or unknown'),
          ('Shopify recorded a refusal', 'Refusal recorded'), ('marketing still allowed', f'{LQ}Marketing{RQ} allowed'),
          ('unknown / no record', 'No record')]
B_GROUPS = [(0, 'By banner type'), (3, 'By Shopify’s record')]   # (first row, muted group name above it)


def panel_b():
    T = table('fig5b.csv')
    T = T[T.arm == 'Decline'].set_index('group')
    fig = fs.panel(W_B, H1)
    left = np.ceil(fs.INDENT_MM + max(tw_mm(lab, fs.FS['cat']) for _, lab in B_ROWS) + 1.6)
    pw = W_B - left - R_PAD
    ax = fs.axes_mm(fig, left, TOP1, pw, PH1)
    ys = np.array([0.0, 1.0, 2.0, 4.0, 5.0, 6.0])                      # the two groupings, set apart
    st = astyle('Decline')
    pts = []
    for (g, _), y in zip(B_ROWS, ys):
        key = 'fig5/b/' + g.replace('/', '~1') + '/decline_residual'
        p, lo, hi = share(key)
        r = T.loc[g]
        assert (int(r.k), int(r.n)) == (fs.stat(key + '/k'), fs.stat(key + '/n')) and abs(r.p - p / 100) < 1e-9
        assert fs.stat(key + '/n') >= 10, 'DESIGN_V7 8.1: a group of fewer than 10 would be drawn grey'
        ci_h(ax, y, lo, hi, st['color'])
        dot(ax, p, y, st)
        pts.append((p, y))
    value_axis(ax, 'x', 0, 100, 25, length_mm=pw)
    ax.set_xlabel('Stores with a new sandbox request after Decline (%)')   # a's measure, fresh page, any vendor
    cat_y(ax, ys, [lab for _, lab in B_ROWS])
    k = rows_ylim(ax, ys[0] - 1.0, ys[-1], PH1, pad_mm=2.0)
    # the two groupings named once each, muted 7 pt, above their first row and right-aligned with the row names
    x_lab = left - 3.0 / 72 * 25.4                                     # the row names end here (pad 3 pt)
    for i0, name in B_GROUPS:
        fs.text_mm(fig, x_lab, TOP1 + (ys[i0] - 0.95 - ax.get_ylim()[1]) / k, name, ha='right', va='center_baseline',
                   color=fs.SP_MUTED, size=fs.FS['label'])
    off_spines(fig, ax, pts, 'b')
    within(fig, ax, 'b')
    no_overlaps(fig, 'b')
    no_digits(fig, 'b')
    finish(fig, 'figS8b_subgroups')
    return plot_box(fig, ax)


# ------------------------------------------------------------------------------------------------ c
C_BASE = 'fig5/c/composition'
C_WINDOWS = [(f'{C_BASE}/decline/same_page', 'Same\npage'), (f'{C_BASE}/decline/unload', 'Unload\nbeacon'),
             (f'{C_BASE}/decline/fresh_page', 'Fresh\npage'), (f'{C_BASE}/gpc', 'GPC\nload')]
C_XS = np.array([0.0, 1.0, 2.0, 3.25])          # the GPC load set apart from the three windows after a Decline
# Fig 5b's classes: its names, colours and key order (make_fig5_panels.B_CLASSES: brick, NEUTRAL, GREY_D)
C_CLASSES = [('refused', fs.LEAK, 'A refused purpose'), ('left_allowed', fs.NEUTRAL, 'Only purposes left allowed'),
             ('none', fs.GREY_D, 'No purpose')]
C_BAR_MM, C_STEP_MM = 1.9, 2.5                  # bar width; bar pitch within a window (mm)
C_LEFT = 11.0


def panel_c():
    fig = fs.panel(W_C, H2)
    pw = W_C - C_LEFT - R_PAD
    ax = fs.axes_mm(fig, C_LEFT, TOP2, pw, PH2)
    x_lo, x_hi = C_XS[0] - 0.55, C_XS[-1] + 0.55
    ax.set_xlim(x_lo, x_hi)
    u = (x_hi - x_lo) / pw                       # data units per mm along x
    bw, step = C_BAR_MM * u, C_STEP_MM * u
    hi_max = 0.0
    for x, (key, _) in zip(C_XS, C_WINDOWS):
        for j, (c, col, _) in enumerate(C_CLASSES):
            p, lo, hi = share(f'{key}/{c}')
            xc = x + (j - 1) * step
            if p > 0:                            # a thin bar from 0 (Fig 5b's bar form); a class with no store: no bar
                ax.add_patch(Rectangle((xc - bw / 2, 0.0), bw, p, facecolor=col, edgecolor='none', linewidth=0,
                                       zorder=2))
            ax.plot([xc, xc], [lo, hi], color=fs.SP_AXIS, lw=LW_CI, solid_capstyle='butt', zorder=3, clip_on=False)
            hi_max = max(hi_max, hi)
        mark(f'{key}/any/n')
    assert step - bw >= 0.5 * u, 'c: white between two bars of a window'
    ax.set_xticks(list(C_XS))
    ax.set_xticklabels([lab for _, lab in C_WINDOWS], fontsize=fs.FS['cat'], linespacing=1.05)
    ax.tick_params(axis='x', length=0, pad=3.0)
    for t in ax.get_xticklabels():
        t.set_color(fs.SP_FG)
    ax.spines['bottom'].set_bounds(x_lo + 0.1, x_hi - 0.1)
    fs.pct_axis(ax, 'y', 0, 25, 5)               # Fig 5b's measure, zoomed: every interval ends below 25 %
    assert hi_max <= 25
    top_pad = 2.2 * 25 / (PH2 - 2.2)
    ax.set_ylim(0, 25 + top_pad)                 # bars start at 0, on the axis; air above the top tick
    ax.spines['left'].set_bounds(0, 25)
    ax.set_ylabel('Stores still sending (%)')                           # Fig 5b's title
    # the key above the plot, in Fig 5b's order and swatches, right-aligned to the plot
    key_column(fig, C_LEFT + pw, KEY2_BASE, [('square', col, lab) for _, col, lab in C_CLASSES], pitch=KEY2_PITCH)
    within(fig, ax, 'c')
    no_overlaps(fig, 'c')
    no_digits(fig, 'c')
    finish(fig, 'figS8c_classes')
    return plot_box(fig, ax)


# ------------------------------------------------------------------------------------------------ d
# Fig 5c's raster and race axis (symmetric-log seconds, one tick format: fs.RACE_AXIS_TITLE), one row per load
D_ROWS = [('deny', 'A0', f'{LQ}No{RQ}, Default'), ('deny', 'A2', f'{LQ}No{RQ}, GPC'),
          ('grant', 'A0', f'{LQ}Yes{RQ}, Default'), ('grant', 'A2', f'{LQ}Yes{RQ}, GPC')]
D_XLIM = (-5.0, 2.0)                # s (Fig 5c's limits); every load inside (asserted)
D_LINTHRESH, D_LINSCALE = 0.01, 0.25
D_MAJOR = [-1, -0.1, 0, 0.1, 1]     # DESIGN_V7 6: at most five ticks (Fig 5c's unlabelled +-0.01 are dropped)
D_AIR, D_GAP = 2.5, 3.0             # mm of white above the first and below the last row (DESIGN_V7 8.3); between blocks
D_GAP_NY = 6.5                      # between the last 'no' block and the first 'yes' block (the two groups set apart)
TICK_MS, TICK_MEW = 1.6, 0.75       # Fig 5c's tick
AFTER_NO = fs.NEUTRAL               # grey: a sandbox that started after the 'no' (context)


def race_tick_label(t):
    """Signed race-axis tick label in s ('−1', '−0.1', '0', '+0.1', '+1'), as Fig 5c."""
    if t == 0:
        return '0'
    dec = max(0, -int(np.floor(np.log10(abs(t)) + 1e-9)))
    return ('+' if t > 0 else fs.MINUS) + fs.fmt_dec(abs(t), dec)


def panel_d():
    D = table('fig5d.csv')
    fig = fs.panel(W_D, H2)
    left = np.ceil(fs.INDENT_MM + max(tw_mm(r[2], fs.FS['cat']) for r in D_ROWS) + 1.6)
    pw = W_D - left - R_PAD
    blocks = []
    for ch, arm, _ in D_ROWS:
        g = D[(D.change == ch) & (D.arm == arm)]
        x = np.sort(g.dt_first.values / 1000)                    # rows sorted by the load's first sandbox
        R = f's8d_race_loads/{ch}_{arm}'
        assert len(x) == mark_sd(f'{R}/loads')
        assert abs(x.min() - mark_sd(f'{R}/min_ms') / 1000) < 1e-9 and abs(x.max() - mark_sd(f'{R}/max_ms') / 1000) < 1e-9
        assert D_XLIM[0] < x.min() and x.max() < D_XLIM[1]          # none clipped
        if ch == 'deny':
            assert int((x < 0).sum()) == mark_sd(f'{R}/first_before') and int((x >= 0).sum()) == mark_sd(f'{R}/first_after')
            assert arm == 'A2' or (x < 0).all(), "caption: the 'no' loads whose sandbox started after are GPC loads"
        else:
            assert int((x > 0).sum()) == mark_sd(f'{R}/first_after') == len(x)
        blocks.append(x)
    rows_total = sum(len(b) for b in blocks)
    gaps = [D_GAP_NY if (D_ROWS[i][0], D_ROWS[i + 1][0]) == ('deny', 'grant') else D_GAP for i in range(len(blocks) - 1)]
    pitch = (PH2 - 2 * D_AIR - sum(gaps)) / rows_total      # mm per load (one pitch: honest heights)
    ax = fs.axes_mm(fig, left, TOP2, pw, PH2)
    ax.set_xscale('symlog', base=10, linthresh=D_LINTHRESH, linscale=D_LINSCALE)
    ax.set_xlim(*D_XLIM)
    ax.set_xticks(D_MAJOR)
    ax.set_xticklabels([race_tick_label(t) for t in D_MAJOR])
    minors = sorted(m for m in (s * k * 10.0 ** e for s in (-1, 1) for e in (-2, -1, 0) for k in range(1, 10))
                    if D_XLIM[0] < m < D_XLIM[1] and m not in D_MAJOR)
    ax.xaxis.set_minor_locator(FixedLocator(minors))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.tick_params(axis='x', which='minor', bottom=True, top=False, length=1.5, width=0.4, color=fs.SP_AXIS)
    ax.set_xlabel(fs.RACE_AXIS_TITLE)
    ax.set_ylim(PH2, 0)                                          # data y = mm from the plot top
    ax.spines['left'].set_visible(False)                        # rows are named blocks, not a value axis
    ax.tick_params(axis='y', length=0, pad=3.0)
    fs.event_line(ax, 0.0, zorder=2.5)                           # the CMP's consent write (amber), over the ground
    y0 = D_AIR
    centres, pts = [], []
    for i, ((ch, _, _), x) in enumerate(zip(D_ROWS, blocks)):
        ys = y0 + (np.arange(len(x)) + 0.5) * pitch
        centres.append(y0 + len(x) * pitch / 2)
        if ch == 'deny':      # brick: the first sandbox started before the 'no' (consent lost); grey: after it
            layers = ((x >= 0, AFTER_NO, 3), (x < 0, fs.LEAK, 3.2))
            m = int((x < 0).sum())
            assert (x[:m] < 0).all() and (x[m:] >= 0).all()
            # the key area (TINT LEAK, never alpha): between each brick tick and the amber rule, on the ticks' own
            # coordinates, from the top of the block's first row to the bottom of its last brick row
            top, bot = y0, y0 + m * pitch
            edge = [(x[j], ys[j]) for j in range(m)]
            poly = [(x[0], top)] + edge + [(x[m - 1], bot), (0.0, bot), (0.0, top)]
            ax.add_patch(Polygon(poly, closed=True, facecolor=fs.TINT['LEAK'], edgecolor='none', zorder=1.0))
        else:                 # slate: a 'yes' load (every first sandbox after the write)
            layers = ((x > 0, fs.HONOUR, 3),)
        for msk, col, z in layers:
            if msk.any():
                ax.plot(x[msk], ys[msk], ls='none', marker='|', ms=TICK_MS, mew=TICK_MEW, color=col, zorder=z,
                        clip_on=False)
        pts += list(zip(x, ys))
        y0 += len(x) * pitch
        if i < len(blocks) - 1:
            y0 += gaps[i]
    assert abs(y0 + D_AIR - PH2) < 1e-9
    ax.set_yticks(centres)
    ax.set_yticklabels([r[2] for r in D_ROWS], fontsize=fs.FS['cat'])
    for t in ax.get_yticklabels():
        t.set_color(fs.SP_FG)
    # the event, named once above the plot (as Fig 1b's 'banner visible')
    x0_mm = left + (ax.transData.transform((0, 0))[0] - ax.transData.transform((D_XLIM[0], 0))[0]) / fig.dpi * 25.4
    fs.text_mm(fig, x0_mm, TOP2 - 1.4, 'consent write', ha='center', color=fs.SP_FG)
    # the key above the plot, one column right-aligned to it (as c's), ticks as drawn
    key_column(fig, left + pw, KEY2_BASE, [('tick', (c, 2.6, 1.0), lab) for c, lab in
                                           ((fs.LEAK, f'Before a {LQ}no{RQ}'), (AFTER_NO, f'After a {LQ}no{RQ}'),
                                            (fs.HONOUR, f'After a {LQ}yes{RQ}'))], pitch=KEY2_PITCH)
    within(fig, ax, 'd')
    no_overlaps(fig, 'd')
    no_digits(fig, 'd')
    finish(fig, 'figS8d_race')
    return plot_box(fig, ax), pitch


if __name__ == '__main__':
    check_composite('figS8.tex', CELLS, FIG_H)
    fs.reset_registry()
    with fs.v7_context():
        boxes = dict(a=panel_a(), b=panel_b(), c=panel_c())
        boxes['d'], _ = panel_d()
    check_alignment(boxes, ['ab', 'cd'])
    write_registry('figS8')
    print(f'S8 panels written (figure 190 x {FIG_H:g} mm)')
