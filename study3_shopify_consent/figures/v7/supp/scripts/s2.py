"""Supplementary Figure S2 (v7) -- outcomes per consent tool. Binding: ../../DESIGN_V7.md (the sciplot clean theme and
the bake-off grafts; worked example ../../fig1). Panels are drawn inside fs.v7_context(): Arial, 7 pt words, 6 pt
ticks, open axes in 0.6 pt SP_AXIS, 3.5 pt markers, uncapped 0.75 pt 95 % intervals, no gridlines, no panel titles.

Figure contract (DESIGN_V7 section 1). Claim (the caption title): Shopify's own banner had the lowest pre-choice
firing of any consent tool and also the most denying region default, so the tools cannot be ranked on these data.
  a  (hero; the comparison across tools) small multiples, 14 consent tools x 6 outcomes: six dot plots side by side
     that share the tool rows (names on the first plot only); each plot one outcome on 0-100 % with a two-line axis
     title naming it. Only a bottom axis (the rows are named, not measured: no left spine, no row ticks), its spine
     bounded to 0-100. Rows are grouped by the tool's integration mode, each group set apart by a gap; the four mode
     groups of third-party tools sit under a muted 7 pt group header left-aligned at the indent (GROUP_HEAD; the
     grammar of Fig 6d and Fig S8b), while Shopify's own banner (top) and 'Other or none' (bottom) are single,
     self-named rows. Within a group, stats order.
     Grey for context, colour for signal (sciplot): the claim is about one row, so Shopify's banner is the one
     coloured row -- a slate (HONOUR, 'the comparison') filled square, double-coded by shape -- and every other tool is
     context, a mid-grey filled circle. A tool with fewer than design.min_stores_row banner stores is drawn in the
     set's one small-n treatment (DESIGN_V7 section 8.1; = Fig S3's top bucket): NEUTRAL circle, LIGHT interval, name
     in SP_MUTED. Wilson 95 % CIs as uncapped 0.75 pt lines in the colour of their mark. Cells with n <
     design.min_cell_n are not drawn. No numbers on the marks: every k and n is in Table S-cmp; the caption names
     Shopify's row (stats.json supp/S2).
  b  (the breakdown by vendor) a heatmap: share of configured sandboxed vendor pixels that fired before any choice,
     consent tool (rows, in a's row order: Shopify's banner first) x vendor group (columns, VENDOR_ORDER), in the
     four-step GREY_RAMP (figstyle; monotone in lightness, the lightest step a definite grey, never white), 11 x 8 mm
     cells split by thin white gaps, no frame and no ticks; 'All vendors' (store-vendor pairs of every group) is a
     column set apart at the right, not boxed; a thin colour bar close to the matrix with 6 pt bin-edge ticks and its
     7 pt title above it. b's cell ends at the colour bar (narrower than a). Cells with n < design.min_cell_n_heatmap
     stay blank and carry a muted en dash ('no estimate', DESIGN_V7 section 8.9). No vendor hues (the vendors are
     columns, named in text). Data: analysis/outputs/fig4b.csv; 'All vendors' equals stats fig4/b/by_cmp (asserted).
GPC column of a: 'still fires under GPC' = of the stores with a sandboxed ad request under Default (as Fig S5c).

The small v7 helpers below (tw_mm, dot, ci_line, x_pct, cat_rows, open_x, check_composite) and the mark styles are
shared by s3.py, s4.py and s5.py so S2-S5 read as one system. RAMP stays a module constant (build_supp.sh validates
it). Panel alignment (nature-figure gate): the six plots of a share their top and baseline (asserted), and b's matrix
starts at a's plot-area left edge (asserted)."""
import numpy as np
from matplotlib.patches import Rectangle

from supp_common import CMP_NAME, S, fs, finish, table, write_registry

W = 190
H_A, H_B = 80, 69
FIG_H = H_A + fs.GUTTER_MM + H_B                          # = figS2.tex canvas (asserted in check_composite)
RAMP = list(fs.GREY_RAMP)                                 # light -> dark; shared style (figstyle.GREY_RAMP)
EDGES = list(fs._C.ORD_EDGES)                             # 0, 25, 50, 75, 100 (colors.py; bin edges, not data)
assert EDGES == [0, 25, 50, 75, 100] and len(RAMP) == 4

# ---- v7 marks (DESIGN_V7 section 5): 3.5 pt markers, 0.6 pt edges; intervals 0.75 pt, uncapped, in the mark's colour
MS = fs.V7_LW['marker']                                   # 3.5 pt circle
MS_SQ = round(MS * 0.95, 2)                               # a square of the same visual weight (figstyle.series_style)
MEW = fs.V7_LW['mew']                                     # 0.6 pt
MID = fs.ORIGIN['open_pixel']['facecolor']                # the registry's mid grey #6e6e6e (DESIGN_V7 section 8.7)
assert MID == '#6e6e6e'
# context: an ordinary row (every tool but the one the claim is about), mid grey
STORY = dict(marker='o', ms=MS, mfc=MID, mec=MID, mew=MEW, color=MID)
# signal: the one row the claim is about (Shopify's banner), slate HONOUR square (colour AND shape)
SHOP = dict(marker='s', ms=MS_SQ, mfc=fs.HONOUR, mec=fs.HONOUR, mew=MEW, color=fs.HONOUR)
# a row with few stores (fewer than design.min_stores_row): NEUTRAL marks, LIGHT intervals, the name in SP_MUTED
SMALL = dict(marker='o', ms=MS, mfc=fs.NEUTRAL, mec=fs.NEUTRAL, mew=MEW, color=fs.LIGHT)
SMALL_LABEL = fs.SP_MUTED
TOP = 5.5                                                 # plot top (mm below the panel top; clear of the letter)
X_PAD = 6.0                                               # % of axis beyond 0 and 100, so marks at the ends stay whole
AIR_MM = 2.25                                             # white between the first / last row and the plot's ends


# ------------------------------------------------------------------------------------------------ shared helpers
def tw_mm(s, size, weight='normal'):
    """Rendered width (mm) of a one-line Arial string at `size` pt (measured, never hand-set)."""
    f = fs.panel(60, 20)
    t = f.text(0, 0.5, s, fontsize=size, fontweight=weight)
    f.canvas.draw()
    w = t.get_window_extent(f.canvas.get_renderer()).width / f.dpi * 25.4
    fs.plt.close(f)
    return w


def dot(ax, x, y, st, zorder=4):
    ax.plot([x], [y], ls='none', marker=st['marker'], ms=st['ms'], mfc=st['mfc'], mec=st['mec'], mew=st['mew'],
            zorder=zorder, clip_on=False)


def ci_line(ax, a, b, y, color, orient='h', zorder=3):
    xs, ys = ([a, b], [y, y]) if orient == 'h' else ([y, y], [a, b])
    ax.plot(xs, ys, color=color, lw=fs.LW['error'], solid_capstyle='butt', zorder=zorder, clip_on=False)


def open_x(ax, lo=0, hi=100):
    """An open axis with only a bottom spine (a dot plot's rows are named, not measured), bounded to lo-hi."""
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_bounds(lo, hi)


def x_pct(ax, step=50, pad=X_PAD, title=None):
    """0-100 % x axis: bare ticks every `step` on a bottom spine bounded to 0-100, a little air beyond both ends (marks
    at 0 or 100 stay whole)."""
    ticks = list(range(0, 101, step))
    ax.set_xlim(-pad, 100 + pad)
    ax.set_xticks(ticks)
    ax.set_xticklabels([str(t) for t in ticks])
    open_x(ax)
    if title:
        ax.set_xlabel(title, labelpad=2.5, linespacing=1.1)


def cat_rows(ax, ys, labels=None, colors=None, pad=3.0):
    """Categorical y axis: 7 pt row names in SP_FG without ticks (labels=None: no names); optional per-row name
    colours (SMALL_LABEL for a row with few stores)."""
    ax.set_yticks(list(ys))
    if labels is None:
        ax.tick_params(axis='y', left=False, labelleft=False)
        return
    ax.set_yticklabels(list(labels), fontsize=fs.FS['cat'])
    ax.tick_params(axis='y', length=0, pad=pad)
    for i, t in enumerate(ax.get_yticklabels()):
        c = (colors or [None] * len(labels))[i]
        t.set_color(c if c is not None else fs.SP_FG)


def row_ylim(n_rows_span, pitch):
    """(lo, hi) in row units so the first and last rows sit AIR_MM inside the plot's ends."""
    air = AIR_MM / pitch
    return -air, n_rows_span + air


# ---- the key area (nature-figure graft; DESIGN_V7 section 3.3): wherever one of the three headline rates of Fig S5
#      is broken down by subgroup (tools in S2a, rank buckets in S3), its main estimate's Wilson 95 % CI is carried
#      through that plot as a pale pre-mixed brick ground (TINT LEAK, never alpha; square, no outline, under every
#      mark) -- the same ground as Fig S5's, so a subgroup reads against the overall rate. The subgroups must pool to
#      exactly that main estimate (asserted), so the band is the overall rate of the drawn rows, not a new number.
HEADLINE = {'prechoice_sbx_banner': 'supp/S6/0', 'decline_residual': 'supp/S6/11', 'gpc_residual': 'supp/S6/20'}
BAND = fs.TINT['LEAK']


def headline_band(ax, outcome, recs, metric, ylim):
    """Draw the main estimate of headline rate `outcome` (Fig S5's row) as a pale brick ground across `ylim` and check
    that the subgroup records recs[i][metric] pool to it (k and n). Returns the main record."""
    main = fs.stat(HEADLINE[outcome])
    assert main['outcome'] == outcome and main['kind'] == 'main'
    assert sum(r[metric]['k'] for r in recs) == main['k'] and sum(r[metric]['n'] for r in recs) == main['n'], \
        f'{metric}: the subgroups no longer pool to {HEADLINE[outcome]}'
    lo, hi = min(ylim), max(ylim)
    ax.add_patch(Rectangle((100 * main['lo'], lo), 100 * (main['hi'] - main['lo']), hi - lo, facecolor=BAND,
                           edgecolor='none', zorder=0.5))
    return main


def check_composite(tex_name, cells, canvas_h):
    """The cells of figS<N>.tex must equal the panel sizes drawn here (panels are never rescaled)."""
    import os
    import re
    from supp_common import SUPP
    tex = open(os.path.join(SUPP, tex_name)).read()
    got = {m[0]: tuple(float(v) for v in m[1:5]) for m in
           re.findall(r'\\Panel\s*\{(\w)\}\s*\{([\d.]+)\}\s*\{([\d.]+)\}\s*\{([\d.]+)\}\s*\{([\d.]+)\}', tex)}
    # a single-panel figure places its one panel without a letter (\PanelBare; key '-')
    got.update({'-': tuple(float(v) for v in m) for m in
                re.findall(r'\\PanelBare\s*\{([\d.]+)\}\s*\{([\d.]+)\}\s*\{([\d.]+)\}\s*\{([\d.]+)\}', tex)})
    assert got == cells, (tex_name, got, cells)
    assert re.search(r'\\FigureCanvas\{%g\}' % canvas_h, tex), f'{tex_name}: canvas height differs from {canvas_h}'


def plot_rect_mm(fig, ax):
    """(x0, top, x1, bottom) of an axes' plot area in panel mm (for the alignment asserts)."""
    W_, H_ = fs.size_mm(fig)
    b = ax.get_position()
    return b.x0 * W_, (1 - b.y1) * H_, b.x1 * W_, (1 - b.y0) * H_


# ------------------------------------------------------------------------------------------------ panel a
METRICS = [('region_denied', 'Default denies\nmarketing (%)'),          # Default load
           ('prechoice_sbx', 'Fired before\nany choice (%)'),           # Default load
           ('reject_first_layer', 'Reject on the\nfirst layer (%)'),     # Decline load
           ('reached', 'Refusal\nrecorded (%)'),                        # Decline load
           ('after_decline', 'Fired on the\nfresh page (%)'),           # Decline load
           ('gpc_resid', 'Still fired\nunder GPC (%)')]                 # GPC load (of stores firing under Default)
# the plots of a that show one of Fig S5's headline rates (among banner stores / working clicks / Default-firing
# stores, exactly as in S5), and so carry its key-area band
A_HEADLINE = {'prechoice_sbx': 'prechoice_sbx_banner', 'after_decline': 'decline_residual', 'gpc_resid': 'gpc_residual'}
GAP_IN = 3.4                                                            # mm between plots (equal: a plain grid)
PITCH_A = 3.0                                                           # mm between tool rows
HEAD_GAP = 0.5                                                          # extra rows of white before a group
# integration modes, top to bottom (stats supp/S2 'mode'); the caption names the groups in this order with these tools
MODE_ORDER = ['N', 'C', 'A', 'B', 'X', 'none']
CAPTION_GROUPS = [['shopify_native'],
                  ['pandectes', 'onetrust', 'cookiebot', 'osano', 'ketch', 'clarip', 'trustarc'],
                  ['iubenda'], ['usercentrics'], ['axeptio', 'cookiescript', 'cookieyes'], ['other']]
# the muted 7 pt group headers (FigGenie: labelled groups; the grammar of Fig 6d and Fig S8b), each one row above its
# group, left-aligned at the 2 mm indent so it never reads as a row name (the small tools' names are muted too). The
# claim's row (Shopify's own banner) on top and 'Other or none' at the bottom are single, self-named rows, set apart by
# the same gap without a header (as Fig 3a's summary row). The caption names each header with its mode.
GROUP_HEAD = {'C': 'Writes and blocks', 'A': 'Writes only', 'B': 'Blocks only', 'X': 'Mode unknown'}
HEAD_CLEAR = 1.6                                                        # mm of white between a header and the plot


def rows_a():
    """(record, y) in draw order: grouped by mode (MODE_ORDER), stats order within a group; y in row units, first row
    on top. Each group after the first is set apart by HEAD_GAP extra rows of white; a group with a header (GROUP_HEAD)
    gives it its own row above the group's first row. Returns the rows, the headers [(text, y)] and the y extent."""
    recs = S['supp']['S2']
    assert {r['mode'] for r in recs} <= set(MODE_ORDER)
    groups = [[r for r in recs if r['mode'] == m] for m in MODE_ORDER]
    assert [[r['cmp'] for r in g] for g in groups] == CAPTION_GROUPS, 'S2a: the caption names other groups'
    out, heads, y = [], [], 0.0
    for gi, (m, g) in enumerate(zip(MODE_ORDER, groups)):
        if gi:
            y += HEAD_GAP
        if m in GROUP_HEAD:
            heads.append((GROUP_HEAD[m], y))
            y += 1.0
        for r in g:
            out.append((r, y))
            y += 1.0
    y_last = out[-1][1]
    flip = lambda v: y_last - v                                   # noqa: E731  (first row has the largest y)
    return [(r, flip(yy)) for r, yy in out], [(t, flip(yy)) for t, yy in heads], y_last


def panel_a():
    recs = S['supp']['S2']
    min_n = S['design']['min_cell_n']
    few = S['design']['min_stores_row']
    rows, heads, y_last = rows_a()
    labels = [CMP_NAME.get(r['cmp'], r['cmp']) for r, _ in rows]
    small = [r['n_banner'] < few for r, _ in rows]
    shop = [r['cmp'] == 'shopify_native' for r, _ in rows]
    assert sum(shop) == 1 and not any(s and h for s, h in zip(small, shop))
    for r, _ in rows:
        assert r['prechoice_sbx']['n'] == r['n_banner']               # column 2 is among banner stores
    # the claim of the caption title, checked: Shopify's banner has the lowest pre-choice rate and the most denying
    # region default of all tools with enough stores (so it is the row the colour is spent on)
    big = [r for r in recs if r['prechoice_sbx']['n'] >= min_n]
    i_shop = [r['cmp'] for r in recs].index('shopify_native')
    assert i_shop == 2, 'the caption cites Shopify\'s banner as supp/S2/2'
    assert min(big, key=lambda r: r['prechoice_sbx']['p']) is recs[i_shop]
    assert max(big, key=lambda r: r['region_denied']['p']) is recs[i_shop]
    assert recs[i_shop]['n_banner'] >= few

    w_lab = max(tw_mm(s, fs.FS['cat']) for s in labels)
    w_head = max(tw_mm(t, fs.FS['label']) for t, _ in heads)
    left = fs.INDENT_MM + max(w_lab + 3.0 / fs.PT_PER_MM + 0.4, w_head + HEAD_CLEAR)
    right = W - 1.2
    k = len(METRICS)
    plotw = (right - left - (k - 1) * GAP_IN) / k
    ylim = row_ylim(y_last, PITCH_A)
    height = (ylim[1] - ylim[0]) * PITCH_A
    assert TOP + height + 11.0 <= H_A + 0.01, f'a: {TOP + height + 11.0:.1f} mm does not fit {H_A} mm'
    ys = [y for _, y in rows]
    fig = fs.panel(W, H_A)
    rects = []
    for j, (m, title) in enumerate(METRICS):
        ax = fs.axes_mm(fig, left + j * (plotw + GAP_IN), TOP, plotw, height)
        ax.set_ylim(*ylim)
        x_pct(ax, 50, title=title)
        cat_rows(ax, ys, labels if j == 0 else None, [SMALL_LABEL if s else None for s in small])
        if m in A_HEADLINE:                                            # the overall rate of the drawn tools
            headline_band(ax, A_HEADLINE[m], recs, m, ylim)
        # context first (small tools, then ordinary tools), the one signal row last, on top
        order = sorted(zip(rows, small, shop), key=lambda t: (t[2], not t[1]))
        for (r, y), sm, sh in order:
            rec = r[m]
            if rec['n'] < min_n:                                       # too few stores: not drawn (caption)
                continue
            st = SHOP if sh else (SMALL if sm else STORY)
            z = 6 if sh else (3 if sm else 5)
            ci_line(ax, 100 * rec['lo'], 100 * rec['hi'], y, st['color'], zorder=z - 1)
            dot(ax, 100 * rec['p'], y, st, zorder=z)
        # the axis title fits its plot (two short lines)
        fig.canvas.draw()
        tw = ax.xaxis.label.get_window_extent(fig.canvas.get_renderer()).width / fig.dpi * 25.4
        assert tw <= plotw + GAP_IN - 0.6, f'a: axis title {title!r} is {tw:.1f} mm wide (plot {plotw:.1f} mm)'
        rects.append(plot_rect_mm(fig, ax))
    # the group headers: muted 7 pt, left-aligned at the indent, each on its own row above its group
    rr = fig.canvas.get_renderer()
    for t, yh in heads:
        hd = fs.text_mm(fig, fs.INDENT_MM, TOP + (ylim[1] - yh) * PITCH_A, t, size=fs.FS['label'],
                        color=fs.SP_MUTED, ha='left', va='center_baseline')
        x1 = hd.get_window_extent(rr).x1 / fig.dpi * 25.4
        assert x1 <= left - HEAD_CLEAR + 0.01, f'a: header {t!r} runs into the plot ({x1:.2f} mm)'
    # alignment gate: one top line and one baseline for the six plots, equal widths, equal gaps
    assert max(r[1] for r in rects) - min(r[1] for r in rects) < 0.01
    assert max(r[3] for r in rects) - min(r[3] for r in rects) < 0.01
    assert max(r[2] - r[0] for r in rects) - min(r[2] - r[0] for r in rects) < 0.01
    finish(fig, 'figS2a_tools')
    return left, rects[-1][2]


# ------------------------------------------------------------------------------------------------ panel b
# b is drawn with the consent tools as ROWS, in a's row order (Shopify's banner first, then the tools as a lists them,
# 'All others' last), so a and b read in one order, top to bottom; the vendor groups are the columns, in the fixed
# vendor order of every figure, and 'All vendors' (the store-vendor pairs of every group) is a column set apart at the
# right, not boxed. Vendor names are short, so the cells can approach square: 11 x 8 mm (1.4 : 1; 10.3 x 7.3 mm inside
# the white gaps), the narrowest that still fits the widest one-line vendor name ('Microsoft').
ROW_NAME = {'shopify_native': 'Shopify’s banner', 'other': 'All others'}
COL_HEAD = {'Reddit/other': 'Reddit/\nother', 'All vendors': 'All\nvendors'}
CELL_W, CELL_H = 11.0, 8.0                                            # mm
GAP_PT = 2.0                                                          # white gap between cells (pt): tiles, not a slab
STRIP_GAP = 1.8                                                       # mm between the vendor matrix and 'All vendors'
CBAR_W, CBAR_H = 1.8, 20.0                                            # mm: the thin colour bar
CBAR_GAP = 5.0                                                        # mm from the matrix to the colour bar (close)
CBAR_TITLE = 'Fired before any\nchoice (%)'
EN = '–'                                                              # 'no estimate' (DESIGN_V7 section 8.9)


def b_rows():
    """b's rows: the tools of fig4b.csv in a's row order (Shopify's banner first; 'All others' last)."""
    cmps = list(S['fig4']['b']['cmps'])
    a_order = [c for g in CAPTION_GROUPS for c in g]
    rows = sorted(cmps, key=a_order.index)
    assert set(rows) == set(cmps) and rows[0] == 'shopify_native' and rows[-1] == 'other'
    return rows


def b_width(left):
    """b's cell width (mm): the matrix from a's plot left edge, the 'All vendors' column, the colour bar CBAR_GAP to
    its right with its title and tick labels; rounded up to a whole mm (= figS2.tex, asserted)."""
    ttl_w = max(tw_mm(s, fs.FS['legend']) for s in CBAR_TITLE.split('\n'))
    tick_w = CBAR_W + 2.5 / fs.PT_PER_MM + 2.0 / fs.PT_PER_MM + tw_mm('100', fs.FS['tick'])
    cx = left + (len(fs.VENDOR_ORDER) + 1) * CELL_W + STRIP_GAP + CBAR_GAP
    return float(np.ceil(cx + max(ttl_w, tick_w) + 0.6))


def panel_b(left, right_a):
    T = table('fig4b.csv')
    tools = b_rows()
    nmin = S['design']['min_cell_n_heatmap']
    vend = list(fs.VENDOR_ORDER)
    W_B = b_width(left)
    assert W_B <= right_a, 'b: wider than a'
    fig = fs.panel(W_B, H_B)
    nr, nv = len(tools), len(vend)
    mh = nr * CELL_H
    assert TOP + mh + 7.5 <= H_B + 0.01, 'b: the matrix does not fit'
    ypos = {c: nr - 1 - i for i, c in enumerate(tools)}               # first tool on top
    n_dash = 0

    def bare(ax):
        for sp in ax.spines.values():
            sp.set_visible(False)

    def cells(ax, cols):
        nonlocal n_dash
        for j, v in enumerate(cols):
            for c in tools:
                r = T[(T.cmp == c) & (T.vgroup == v)].iloc[0]
                if r.n < nmin:                                             # too few stores: blank + dash (caption)
                    ax.text(j + 0.5, ypos[c], EN, ha='center', va='center', fontsize=fs.FS['label'],
                            color=fs.SP_MUTED)
                    n_dash += 1
                    continue
                k = int(np.searchsorted(EDGES[1:-1], 100 * r.p, side='right'))
                ax.add_patch(Rectangle((j, ypos[c] - 0.5), 1, 1, facecolor=RAMP[k], edgecolor=fs.SURFACE,
                                       linewidth=GAP_PT, zorder=1))
        ax.set_xlim(0, len(cols))
        ax.set_ylim(-0.5, nr - 0.5)
        ax.set_xticks([j + 0.5 for j in range(len(cols))])
        ax.set_xticklabels([COL_HEAD.get(v, v) for v in cols], fontsize=fs.FS['cat'], linespacing=1.1,
                           color=fs.SP_FG, va='top')
        ax.tick_params(axis='x', length=0, pad=3.0)
        bare(ax)

    # the vendor matrix (7 columns), then 'All vendors' as its own one-column strip right of a gap
    axv = fs.axes_mm(fig, left, TOP, nv * CELL_W, mh)
    cells(axv, vend)
    cat_rows(axv, [ypos[c] for c in tools], [ROW_NAME.get(c, CMP_NAME.get(c, c)) for c in tools])
    xa = left + nv * CELL_W + STRIP_GAP
    axa = fs.axes_mm(fig, xa, TOP, CELL_W, mh)
    cells(axa, ['All vendors'])
    cat_rows(axa, [ypos[c] for c in tools])                           # rows named once, at the left
    # the caption counts the dashes in words ('blank cells with a dash'); every 'All vendors' cell is drawn
    assert n_dash > 0 and all(T[(T.vgroup == 'All vendors')].n >= nmin)
    # the 'All vendors' column is the same estimate as stats fig4/b/by_cmp (cited in the caption, row by row)
    for c in tools:
        r = T[(T.cmp == c) & (T.vgroup == 'All vendors')].iloc[0]
        b = S['fig4']['b']['by_cmp'][c]
        assert (int(r.k), int(r.n), int(r.n_banner_stores)) == (b['k'], b['n'], b['n_banner_stores']), c
    # the lightest ramp step stays darker than #cccccc (a blank 'no estimate' cell never reads as the lowest bin)
    assert all(int(RAMP[0][i:i + 2], 16) <= 0xcc for i in (1, 3, 5))
    # column heads fit their cells; one head line for every column (the two-line heads share the first line's top)
    fig.canvas.draw()
    rr = fig.canvas.get_renderer()
    for t in axv.get_xticklabels() + axa.get_xticklabels():
        assert t.get_window_extent(rr).width / fig.dpi * 25.4 <= CELL_W - 0.8, t.get_text()

    # the thin colour bar: four blocks (one per ramp step) split by the same white gaps, bin edges as 6 pt ticks on its
    # right, its 7 pt title above it; the title's top sits level with the matrix top
    cx = xa + CELL_W + CBAR_GAP
    cy = TOP + 7.0
    cax = fs.axes_mm(fig, cx, cy, CBAR_W, CBAR_H)
    for i in range(4):
        cax.add_patch(Rectangle((0, i), 1, 1, facecolor=RAMP[i], edgecolor=fs.SURFACE, linewidth=GAP_PT))
    cax.set_xlim(0, 1)
    cax.set_ylim(0, 4)
    cax.set_xticks([])
    bare(cax)
    cax.yaxis.tick_right()
    cax.set_yticks(range(5))
    cax.set_yticklabels([str(e) for e in EDGES])
    cax.tick_params(axis='y', right=True, left=False, labelright=True, labelleft=False)
    ttl = fs.text_mm(fig, cx, cy - 1.6, CBAR_TITLE, size=fs.FS['legend'], va='bottom', linespacing=1.1,
                     color=fs.SP_FG)
    fig.canvas.draw()
    rr = fig.canvas.get_renderer()
    x1 = max(ttl.get_window_extent(rr).x1, max(t.get_window_extent(rr).x1 for t in cax.get_yticklabels()))
    x1_mm = x1 / fig.dpi * 25.4
    assert x1_mm <= W_B - 0.3 and W_B - x1_mm < 1.6, f'b: the colour bar ends {x1_mm:.2f} mm (cell {W_B} mm)'
    ttop = (fig.bbox.y1 - ttl.get_window_extent(rr).y1) / fig.dpi * 25.4
    assert abs(ttop - TOP) < 1.2, f'b: the colour-bar title top {ttop:.2f} mm, the matrix top {TOP} mm'
    # alignment gate: b's matrix starts at a's plot-area left edge; the 'All vendors' strip shares its top and bottom
    assert abs(plot_rect_mm(fig, axv)[0] - left) < 0.01
    assert abs(plot_rect_mm(fig, axa)[1] - plot_rect_mm(fig, axv)[1]) < 0.01
    assert abs(plot_rect_mm(fig, axa)[3] - plot_rect_mm(fig, axv)[3]) < 0.01
    finish(fig, 'figS2b_heatmap')


if __name__ == '__main__':
    with fs.v7_context():
        left, right_a = panel_a()
        W_B = b_width(left)
        check_composite('figS2.tex', {'a': (0, 0, W, H_A), 'b': (0, H_A + fs.GUTTER_MM, W_B, H_B)}, FIG_H)
        panel_b(left, right_a)
    write_registry('figS2')
    print(f'figS2: a {W} x {H_A} mm, b {W_B:g} x {H_B} mm, canvas {FIG_H} mm')
