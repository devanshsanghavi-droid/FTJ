"""Figure 4 panels, v7 (../../DESIGN_V7.md; worked example ../../fig1/): blocked on paper. The sciplot clean theme
(mmd-ahd/scientific-figure-skill, read and re-implemented, never executed) with the bake-off grafts. Panel letters,
contents and every number are those of v6; the explaining and every value live in the caption
(scripts/make_caption_fig4.py).

Messages (venue: Computers & Security, Elsevier, 190 mm double column):
  figure  a vendor that the consent tool's blocklist declares blocked still fired from Shopify's sandbox on about half
          of the stores, and blocklist stores fired more, not less, often than comparable stores (loss point (2) of
          Fig. 1a, measured);
  a       (hero; the population) blocklist stores whose CMP wrote no 'marketing: yes': the share on which the
          declared-blocked vendor fired from its sandboxed pixel before any choice, by sample;
  b       (the comparison, with its control) like for like within each of Shopify's region defaults, blocklist stores
          against banner stores without a readable declaration (left), and the difference pooled over the two
          defaults (right; cited in the text as 'Fig. 4b, right', never 'Fig. 4c').

  a  sciplot 'show the data' for small n (the main sample is 14 stores): each sample is a THIN UNIT BAR on 0-100 %
     (DESIGN_V7 section 8.7), one cell per store, the stores whose declared-blocked vendor fired first, in brick (consent
     lost), the others in LIGHT grey (context), thin white gaps between cells -- so the brick part ends exactly at the
     share and a cell's width shows how few stores a sample has. The bar is a strip (BAR_H, about the height of a
     marker), not a slab: the expansion's 75 cells come out nearly square, a row of units rather than a picket fence.
     Under each bar its summary (section 5: dots + summary): an open brick circle at the share (one sample alone) with
     its uncapped Wilson 95 % CI in brick. Below a gap, the summary row: the combined sample (the primary estimate), a
     filled brick circle with its CI. No value axis on the rows (rows are named, not measured): the left spine is
     dropped and the row names sit at the left. The rows sit at a tight pitch, so the hero is dense and b gets height.
  b  left: per region default, a pair of rows: blocklist stores of both samples (brick circle, consent lost) above
     main-sample banner stores without a readable declaration (NEUTRAL grey square: the comparison, context), Wilson
     CIs in the marker colour (colour AND shape). Not slate: in Fig. 3 slate squares mean 'denied until consent', and
     b's rows are named by the region defaults, so brick / slate keep their one meaning across the main figures and
     the comparison here is grey ('grey for context, colour for signal'). The key area (nature-figure graft; TINT LEAK,
     pre-mixed, never alpha) is the gap between the pair's two shares -- how much more often the blocklist stores
     fired -- bounded exactly by the two drawn estimates and the pair's rows. Two direct labels at the 'denied' pair
     name the two groups (no legend). A muted 7 pt header, 'Region default', sits over the row names.
     Right: the Mantel-Haenszel difference, blocklist minus no declaration, pooled over the two defaults (Sato
     variance), in Fig. 3a-right's grammar (dot + CI only, DESIGN_V7 8.1): no left spine, a solid NEUTRAL 0.6 pt
     zero rule drawn as data from half a pitch above the first pooled row down to the axis, each estimate a
     near-black diamond (open = main sample only, filled = combined: the open / filled meaning of a) with its uncapped
     95 % CI; no bars. One percentage point has the same length in both plots of b, so the differences compare
     directly with the left plot's gaps. Its two rows have
     their own positions, centred in the white between the left plot's two pairs (never on a left row line: the pooled
     rows belong to neither default), under their own muted header, 'Pooled over defaults', on the left header's
     baseline.

Layout (190 x FIG_H mm, two full-width rows, 6 mm gutter, no outer margin): a 190 x A_H (hero), b 190 x B_H. Every
plot area starts at P0 (a's 0 % sits exactly above b-left's 0 %, asserted); a's plot runs P0..P1 and b-right ends at
P1 (asserted); b's two plots share their top and baseline. Row names of a and b-left share one right edge
(P0 - ROW_PAD).

Style: fs.v7_context() (Arial; 7 pt words, 6 pt ticks; open L axes 0.6 pt #3d434b; data 1.0 pt; markers 3.5 pt).
Every panel is linted (sp_lint.lint_fig) before it is saved.
Numbers: nothing is printed in the panels except tick labels; every drawn value (cell counts, dots, CI ends, diamonds)
is read from analysis/outputs/stats.json and registered (fmt 'mark') in ../fig4_numbers.csv for trace_fig4.py.

Run:  python3 figures/v7/fig4/scripts/make_fig4_panels.py      (build_fig4.sh composes and checks)
"""
import json
import os
import re
import sys

from matplotlib.patches import Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
FIG4 = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG4, '..', 'style')))
import figstyle as fs  # noqa: E402
sys.path.insert(0, HERE)
import sp_lint  # noqa: E402  (sciplot step 5: lint every panel before it is saved)

PANELS = os.path.join(FIG4, 'panels')
os.makedirs(PANELS, exist_ok=True)

# ---- composite grid (mm); must equal fig4.tex (asserted in check_composite) ----
FIG_W = 190.0
A_W, A_H = 190.0, 31.0                    # a: the hero (unit bars + summaries), tight row pitch
B_W, B_H = 190.0, 35.0                    # b: like for like (left) and the pooled difference (right)
GUT = fs.GUTTER_MM
FIG_H = A_H + GUT + B_H
assert FIG_W == fs.FIG_W_MM and FIG_H <= fs.FIG_MAX_H_MM
P0, P1 = 32.0, 185.0                      # a's plot area (0..100 %); b-left starts at P0, b-right ends at P1
ROW_PAD = 3.0                             # row names end this far left of their plot (tick pad, length 0)

# ---- v7 marks (DESIGN_V7 sections 4-5) ----
MS = fs.V7_LW['marker']                   # 3.5 pt circle
MS_SQ = MS * 0.95                         # the comparison square, of similar visual weight (figstyle.series_style ratio)
MS_DIA = 3.6                              # diamond: v6's 4.6 pt scaled by 3.5 / 4.5 (Fig. 3: 3.58 pt)
MEW = fs.V7_LW['mew']                     # 0.6 pt edge of a filled marker
MEW_OPEN = 1.0                            # open circle: white with a 1.0 pt edge in the token (section 5: 0.6-1.2)
MEW_OPEN_DIA = 1.0                        # open diamond: Fig. 3a-right's 1.0 pt edge (one grammar for the two figures)
CI_LW = fs.LW['error']                    # 0.75 pt, uncapped
COMPARE = fs.NEUTRAL                      # b left: the comparison stores (grey for context; never slate, see above)

R4 = 'round4/blocklist'                   # stats.json: Round 4 blocklist analysis (main, expansion, combined)
LFL = f'{R4}/combined/like_for_like'
# one-line axis titles, as in v6 and Fig. 3 ('Any ad pixel fired (%)' is Fig. 3's title for the same measure)
A_TITLE = 'Blocked vendor fired (%)'      # a: the declared-blocked vendor sent a sandboxed request before any choice
B_TITLE = 'Any ad pixel fired (%)'        # b left: any sandboxed ad pixel sent a request before any choice
D_TITLE = 'Difference (pp)'               # b right: blocklist minus no declaration, pooled over the two defaults
B_HEAD = 'Region default'                 # b left: muted header over its row names (Shopify's region default)
D_HEAD = 'Pooled over defaults'           # b right: muted header over its row names (the two defaults pooled)


# ------------------------------------------------------------------------------------------------ numbers
def reg_only(key):
    """Register a stats.json value that is drawn (cell count, dot, CI end, diamond) but not printed."""
    fs._REG.append(dict(text='', shown='', source='stats', key=key, fmt='mark', value=json.dumps(fs.stat(key))))
    return fs.stat(key)


def share(key):
    """A stats share record in percentage units (p, lo, hi), each registered as a drawn mark."""
    return tuple(100 * reg_only(f'{key}/{f}') for f in ('p', 'lo', 'hi'))


# ------------------------------------------------------------------------------------------------ helpers
def bb_mm(fig, artist):
    """(x0, x1, top, bottom) of an artist's (tight) extent in panel mm (y measured down from the panel top)."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    bb = artist.get_tightbbox(r) if hasattr(artist, 'get_tightbbox') else artist.get_window_extent(r)
    px = fig.dpi / 25.4
    H = fs.size_mm(fig)[1]
    return bb.x0 / px, bb.x1 / px, H - bb.y1 / px, H - bb.y0 / px


def no_overlaps(fig, name, pad=0.3):
    """Every pair of visible texts in the panel stays at least `pad` mm apart."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    px = fig.dpi / 25.4
    ts = fs._texts(fig)
    bbs = [t.get_window_extent(r) for t in ts]
    for i in range(len(ts)):
        for j in range(i + 1, len(ts)):
            a, b = bbs[i], bbs[j]
            gap = max(b.x0 - a.x1, a.x0 - b.x1, b.y0 - a.y1, a.y0 - b.y1)
            assert gap >= pad * px, f'{name}: texts {ts[i].get_text()!r} and {ts[j].get_text()!r} closer than {pad} mm'


def within_panel(fig, ax, name):
    """The plot and all its labels end inside the panel, at least INDENT_MM right of the figure's left edge."""
    W, H = fs.size_mm(fig)
    x0, x1, t, b = bb_mm(fig, ax)
    assert x0 >= fs.INDENT_MM and x1 <= W - 0.3 and t >= 0.3 and b <= H - 0.3, \
        f'{name}: plot or labels leave the panel ({x0:.2f}, {x1:.2f}, {t:.2f}, {b:.2f})'
    return x0, x1, t, b


def rows_axis(ax, ys, names, ph):
    """A row axis (DESIGN_V7 sections 6, 8.1): rows named at the left in 7 pt SP_FG, no tick marks, no left spine
    (rows are named, not measured); y runs DOWN in mm from the plot top (0..ph)."""
    ax.set_ylim(ph, 0)
    ax.set_yticks(list(ys))
    ax.set_yticklabels(list(names), fontsize=fs.FS['cat'], color=fs.SP_FG)
    ax.tick_params(axis='y', length=0, pad=ROW_PAD * fs.PT_PER_MM)
    ax.spines['left'].set_visible(False)


def ci(ax, y, lo, hi, color):
    ax.plot([lo, hi], [y, y], color=color, lw=CI_LW, solid_capstyle='butt', zorder=3, clip_on=False)


def dot(ax, x, y, marker, ms, color, filled=True, mew_open=MEW_OPEN):
    ax.plot([x], [y], ls='none', marker=marker, ms=ms, mfc=color if filled else fs.SURFACE, mec=color,
            mew=MEW if filled else mew_open, zorder=4, clip_on=False)


def ground(ax, x0, x1, y0, y1):
    """The key area (DESIGN_V7 section 3.3): a TINT LEAK ground, square, no outline, under every mark."""
    ax.add_patch(Rectangle((min(x0, x1), min(y0, y1)), abs(x1 - x0), abs(y1 - y0), facecolor=fs.TINT['LEAK'],
                           edgecolor='none', zorder=1))


def x_of(ax, mm_x):
    """Data x of a panel-mm x (for labels placed in mm)."""
    fig = ax.figure
    px = fig.dpi / 25.4
    return ax.transData.inverted().transform((mm_x * px, 0))[0]


def mm_of(ax, x):
    """Panel-mm x of a data x."""
    px = ax.figure.dpi / 25.4
    return ax.transData.transform((x, 0))[0] / px


# ------------------------------------------------------------------------------------------------ panel a
A_TOP = 1.0                               # plot top (mm from the panel top)
AIR = 2.5                                 # white above row 1 and below row n (section 8.3)
BAR_H = 1.6                               # unit bar height (mm): a thin strip, about one marker high (section 8.7)
CELL_GAP_MM = 0.35                        # white between store cells
EST_DY = 2.7                              # bar centre -> its summary row (open circle + CI)
BLOCK_DY = 5.0                            # summary row -> the next bar's centre
SUM_DY = 6.0                              # last summary row -> the combined row (the summary set apart below a gap)
A_ROWS = [('main', 'Main sample'), ('expansion', 'Expansion')]
Y_BAR = [AIR + BAR_H / 2, AIR + BAR_H / 2 + EST_DY + BLOCK_DY]
Y_EST = [y + EST_DY for y in Y_BAR]
Y_COMB = Y_EST[-1] + SUM_DY
A_PH = Y_COMB + 2.7                       # plot height (mm): >= 2 mm of white below the last marker


def unit_bar(ax, yc, k, n):
    """One cell per store on 0-100 %: the k stores whose declared-blocked vendor fired first (LEAK), the n - k others
    in LIGHT; CELL_GAP_MM of white between cells, none at the two ends, so the brick part ends exactly at k / n."""
    w = 100.0 / n
    gap = CELL_GAP_MM / ((P1 - P0) / 100.0)          # in % units
    cells = []
    for i in range(n):
        x0 = i * w + (gap / 2 if i > 0 else 0.0)
        x1 = (i + 1) * w - (gap / 2 if i < n - 1 else 0.0)
        ax.add_patch(Rectangle((x0, yc - BAR_H / 2), x1 - x0, BAR_H, facecolor=fs.LEAK if i < k else fs.LIGHT,
                               edgecolor='none', zorder=2))
        cells.append((x0, x1))
    assert abs(cells[-1][1] - 100.0) < 1e-9 and cells[0][0] == 0.0
    assert abs((cells[k - 1][1] + cells[k][0]) / 2 - 100.0 * k / n) < 1e-9     # brick ends at the share
    return (w - gap) * (P1 - P0) / 100.0                                        # cell width (mm)


def panel_a():
    """The hero: the blocked-on-paper share by sample as thin unit bars (one cell per store) with their summaries,
    and the combined sample (the primary estimate) set apart below. Returns the plot's (x0, x1) in mm."""
    fig = fs.panel(A_W, A_H)
    ax = fs.axes_mm(fig, P0, A_TOP, P1 - P0, A_PH)
    fs.pct_axis(ax, 'x', 0, 100, 25)
    ax.set_xlabel(A_TITLE)
    rows_axis(ax, Y_BAR + [Y_COMB], [nm for _, nm in A_ROWS] + ['Combined'], A_PH)
    widths = {}
    for (g, _), yb, ye in zip(A_ROWS, Y_BAR, Y_EST):
        key = f'{R4}/{g}/primary/fired'
        k, n = int(reg_only(key + '/k')), int(reg_only(key + '/n'))
        p, lo, hi = share(key)
        assert abs(p - 100.0 * k / n) < 1e-9 and 0 < lo < p < hi < 100
        widths[g] = unit_bar(ax, yb, k, n)
        ci(ax, ye, lo, hi, fs.LEAK)
        dot(ax, p, ye, 'o', MS, fs.LEAK, filled=False)          # open: one sample alone
    key = f'{R4}/combined/primary/fired'
    p, lo, hi = share(key)
    kc, nc = fs.stat(key + '/k'), fs.stat(key + '/n')
    assert (kc, nc) == tuple(sum(fs.stat(f'{R4}/{g}/primary/fired/{f}') for g, _ in A_ROWS) for f in ('k', 'n'))
    ci(ax, Y_COMB, lo, hi, fs.LEAK)
    dot(ax, p, Y_COMB, 'o', MS, fs.LEAK, filled=True)            # filled: the combined sample (primary estimate)
    r_mm = MS / fs.PT_PER_MM / 2
    # a strip, not a slab: the bar is no taller than about a marker; the smallest cells come out about square (a row of
    # units, not tall pickets), and every cell keeps >= 1.4 mm of colour between white gaps
    assert BAR_H <= 1.8 and min(widths.values()) >= 1.4, widths
    assert 0.8 <= min(widths.values()) / BAR_H <= 1.25, 'a: the expansion cells should be about square'
    # air: the summary marks keep >= 2 mm from the plot's top and bottom; the bars sit AIR below the top
    assert Y_BAR[0] - BAR_H / 2 >= 2.0 and A_PH - Y_COMB - r_mm >= 2.0
    # a summary row sits closer to its own bar than to the next one (it reads as that bar's estimate), and its marker
    # clears its bar by >= 1 mm
    for i in range(len(A_ROWS)):
        assert (Y_EST[i] - Y_BAR[i]) - BAR_H / 2 - r_mm >= 1.0
    for i in range(len(A_ROWS) - 1):
        assert (Y_EST[i] - Y_BAR[i]) - BAR_H / 2 < (Y_BAR[i + 1] - BAR_H / 2) - Y_EST[i]
    # the combined row is set apart: its gap exceeds the gap between the two sample blocks
    assert SUM_DY > BLOCK_DY
    x0, x1, _, bot = within_panel(fig, ax, 'a')
    print(f'a: content bottom {bot:.2f} of {A_H:g} mm')
    assert A_H - bot <= 1.0, f'a: {A_H - bot:.2f} mm of empty band at the bottom (tighten A_H)'
    no_overlaps(fig, 'a')
    assert not sp_lint.lint_fig(fig, 'fig4a_primary'), 'sciplot lint: fix or justify every warning'
    fs.save_panel(fig, os.path.join(PANELS, 'fig4a_primary.pdf'))
    return x0, x1, widths


# ------------------------------------------------------------------------------------------------ panel b
B_TOP = 4.6                               # plot top (mm from the panel top)
HEAD_Y = B_TOP - 0.2                      # baseline of the two muted headers over the row names (>= 1.5 mm above the
                                          # first row name, >= 1.5 mm below the letter's cap line; asserted)
PAIR_DY = 1.8                             # half the distance between a default's two rows (blocklist above)
G_DY = 13.0                               # between the two defaults' group centres
B_G = [AIR + 0.6 + PAIR_DY, AIR + 0.6 + PAIR_DY + G_DY]       # group centres (mm from the plot top)
B_PH = B_G[-1] + PAIR_DY + 0.6 + AIR
TINT_PAD = 1.1                            # the key area reaches this far beyond the pair's two row lines (> a marker radius)
D_LO, D_HI, D_STEP = -20, 40, 20          # b right: difference axis (pp), 4 signed ticks (section 6: at most 4-5)
MM_PER_PP = (P1 - P0) / 100.0 / 2       # one percentage point, the same length in both plots of b: exactly half of
                                          # a's, so b-left's ticks fall on a's tick grid (its 50 under a's 25, its 100
                                          # under a's 50) instead of missing it by a fraction of a millimetre
BL1 = P0 + 100.0 * MM_PER_PP              # b left: plot right edge (mm)
BR0 = P1 - (D_HI - D_LO) * MM_PER_PP      # b right: plot left edge (mm)
B_MID = BR0 - BL1                         # b: from the left plot to the right one (mm): the right header and row names,
                                          # ROW_PAD and >= 5 mm of white (asserted in panel_b)
R_MID = (B_G[0] + B_G[1]) / 2             # b right: its two rows, centred in the white between the left's two pairs
R_DY = PAIR_DY                            # ... half their distance (Main sample above, Combined below): the
                                          # rhythm of a left pair, so the pooled rows read as one more pair
R_Y = [R_MID - R_DY, R_MID + R_DY]
ZERO_LW = 0.6                             # b right: the zero rule (solid NEUTRAL; = Fig 3a right's ZERO_LW)
ZERO_ABOVE = R_DY                         # b right: the zero rule starts half a pitch above its first pooled row
GROUPS = [('allowed_no_yes', 'Allowed until choice'), ('denied_no_yes', 'Denied until consent')]
D_ROWS = [('main', 'Main sample', f'{R4}/main/like_for_like/mh_no_yes', False),
          ('combined', 'Combined', f'{LFL}/mh_no_yes', True)]
LABEL_DX_MM = 1.3                         # a direct label starts this far right of its interval's end


def panel_b():
    """Like for like (CMP wrote no 'yes'): left, per region default, blocklist (brick circle) above no declaration
    (grey square) with the gap between them as the key area; right, on rows of its own, the pooled Mantel-Haenszel
    difference, main sample (open) and combined (filled), against a grey zero rule. Returns the left plot's
    left edge and the right plot's right edge (mm)."""
    fig = fs.panel(B_W, B_H)
    # ---- left: the two region defaults, a pair of rows each
    ax = fs.axes_mm(fig, P0, B_TOP, BL1 - P0, B_PH)
    fs.pct_axis(ax, 'x', 0, 100, 25)
    ax.set_xlabel(B_TITLE)
    rows_axis(ax, B_G, [s for _, s in GROUPS], B_PH)
    est = {}
    for (g, _), yc in zip(GROUPS, B_G):
        for sub, color, marker, ms, dy in (('blocklist', fs.LEAK, 'o', MS, -PAIR_DY),
                                           ('reference', COMPARE, 's', MS_SQ, PAIR_DY)):
            p, lo, hi = share(f'{LFL}/{g}/{sub}')
            ci(ax, yc + dy, lo, hi, color)
            dot(ax, p, yc + dy, marker, ms, color)
            est[g, sub] = (p, lo, hi, yc + dy)
        # the key area: the gap between the pair's two shares (how much more often the blocklist stores fired)
        pb, pr = est[g, 'blocklist'][0], est[g, 'reference'][0]
        assert pb >= pr                                   # caption: blocklist stores fired at least as often
        ground(ax, pr, pb, yc - PAIR_DY - TINT_PAD, yc + PAIR_DY + TINT_PAD)
    r_mm = MS / fs.PT_PER_MM / 2
    assert TINT_PAD > r_mm + 0.2 and 2 * PAIR_DY >= 2 * r_mm + 1.2   # the pair's marks never touch; ground covers them
    assert B_G[0] - PAIR_DY - TINT_PAD >= 1.8 and B_PH - (B_G[-1] + PAIR_DY + TINT_PAD) >= 1.8   # air around grounds
    # muted header over the row names (the categories are Shopify's region defaults)
    head = fs.text_mm(fig, P0 - ROW_PAD, HEAD_Y, B_HEAD, ha='right', color=fs.SP_MUTED, size=fs.FS['cat'])
    # two direct labels at the 'denied' pair, each just right of its own interval (no legend)
    labs = []
    for sub, name in (('blocklist', 'Blocklist'), ('reference', 'No declaration')):
        p, lo, hi, y = est['denied_no_yes', sub]
        labs.append(fs.direct_label(ax, x_of(ax, mm_of(ax, hi) + LABEL_DX_MM), y, name, va='center_baseline',
                                    color=fs.SP_FG))
    # the labels clear every mark and interval of the 'allowed' pair and stay inside the plot
    fig.canvas.draw()
    for t in labs:
        lx0, lx1, _, _ = bb_mm(fig, t)
        assert lx1 <= BL1 - 1.0 and lx1 < mm_of(ax, est['allowed_no_yes', 'reference'][1]) - 2.0

    # ---- right: pooled Mantel-Haenszel difference on rows of its own (Fig. 3a-right's grammar: dot + CI only, no
    #      left spine, a solid NEUTRAL zero rule drawn as data over the rows that carry a difference)
    comb, main = D_ROWS[1][2], D_ROWS[0][2]
    assert fs.stat(comb + '/rd_lo') > 0 > fs.stat(main + '/rd_lo')     # caption: combined rules out any reduction
    assert D_LO < 100 * min(fs.stat(comb + '/rd_lo'), fs.stat(main + '/rd_lo')) and \
        100 * max(fs.stat(comb + '/rd_hi'), fs.stat(main + '/rd_hi')) < D_HI
    ax2 = fs.axes_mm(fig, BR0, B_TOP, P1 - BR0, B_PH)
    ax2.set_xlim(D_LO, D_HI)
    ax2.set_ylim(B_PH, 0)
    fs.signed_ticks(ax2, list(range(D_LO, D_HI + 1, D_STEP)), 'x')
    ax2.set_xlabel(D_TITLE)
    ax2.spines['left'].set_visible(False)              # rows are named; the zero rule is drawn as data (Fig. 3a right)
    ax2.spines['bottom'].set_bounds(D_LO, D_HI)
    ax2.set_yticks([])
    ax2.tick_params(axis='y', length=0)
    # the zero rule (no difference): solid NEUTRAL, from half a pitch above the first pooled row down to the axis, under
    # every mark (as Fig. 3a right)
    z_top = R_Y[0] - ZERO_ABOVE
    ax2.plot([0, 0], [z_top, B_PH], color=fs.NEUTRAL, lw=ZERO_LW, solid_capstyle='butt', zorder=1, clip_on=False)
    names = []
    for (g, name, key, filled), y in zip(D_ROWS, R_Y):
        rd, rlo, rhi = (100 * reg_only(f'{key}/{f}') for f in ('rd', 'rd_lo', 'rd_hi'))
        ci(ax2, y, rlo, rhi, fs.SP_FG)
        dot(ax2, rd, y, 'D', MS_DIA, fs.SP_FG, filled=filled, mew_open=MEW_OPEN_DIA)
        names.append(ax2.text(-ROW_PAD / (P1 - BR0), y, name, transform=ax2.get_yaxis_transform(), ha='right',
                              va='center_baseline', fontsize=fs.FS['cat'], color=fs.SP_FG))
    head2 = fs.text_mm(fig, BR0 - ROW_PAD, HEAD_Y, D_HEAD, ha='right', color=fs.SP_MUTED, size=fs.FS['cat'])

    # ---- alignment and spacing (nature-figure gate)
    # one scale across b: a percentage point has the same length in both plots; shared top and baseline
    for a_, (lo_, hi_) in ((ax, (0, 100)), (ax2, (D_LO, D_HI))):
        w_mm = a_.get_position().width * B_W
        assert abs(w_mm / (hi_ - lo_) - MM_PER_PP) < 1e-9 and a_.get_xlim() == (lo_, hi_)
    assert ax.get_position().y0 == ax2.get_position().y0 and ax.get_position().y1 == ax2.get_position().y1
    assert ax.get_ylim() == ax2.get_ylim()
    # b-left's scale is exactly half of a's (its 0, 50, 100 under a's 0, 25, 50): no near-miss tick alignments
    assert abs(2 * 100 * MM_PER_PP - (P1 - P0)) < 1e-9
    # the pooled rows belong to neither default: each sits >= 2 mm off every left row line, inside the white between
    # the 'allowed' pair's lower row and the 'denied' pair's upper row, and the pair is centred there
    left_rows = sorted(v[3] for v in est.values())
    assert min(abs(y - yl) for y in R_Y for yl in left_rows) >= 2.0
    assert left_rows[1] < R_Y[0] < R_Y[1] < left_rows[2]
    assert abs((R_Y[0] + R_Y[1]) / 2 - (left_rows[1] + left_rows[2]) / 2) < 1e-9
    assert z_top >= 1.8 and 2 * R_DY - MS_DIA * 2 ** 0.5 / fs.PT_PER_MM >= 1.0    # rule clear of the top; marks apart
    x0, _, _, bot = within_panel(fig, ax, 'b left')
    print(f'b: content bottom {bot:.2f} of {B_H:g} mm')
    assert B_H - bot <= 1.0, f'b: {B_H - bot:.2f} mm of empty band at the bottom (tighten B_H)'
    _, rx1, _, _ = within_panel(fig, ax2, 'b right')
    # the two headers: one baseline, muted, clear of the letter line and of the first row names below them
    hx0, _, ht, hb = bb_mm(fig, head)
    assert hx0 >= fs.LETTER_ZONE_MM[0] + 2.0 and ht >= 0.3, 'b: the header enters the letter zone or the top edge'
    first = [t for t in ax.get_yticklabels() if t.get_text() == GROUPS[0][1]][0]
    assert bb_mm(fig, first)[2] - hb >= 1.5, 'b: the header crowds the first row name'
    assert HEAD_Y - fs.LETTER_CAP_MM >= 1.5, "b: the header sits on the letter's line (it must not read as a title)"
    h2x0, _, h2t, h2b = bb_mm(fig, head2)
    assert abs(h2b - hb) < 0.05 and abs(h2t - ht) < 0.3, 'b: the two headers do not share a baseline'
    assert bb_mm(fig, names[0])[2] - h2b >= 1.5, "b: the right header crowds 'Main sample'"
    # the right header and row names keep >= 5 mm of white from the left plot (they never read as its labels)
    nx0 = min(bb_mm(fig, t)[0] for t in names + [head2])
    assert nx0 - BL1 >= 5.0, f'b: right header / row names {nx0 - BL1:.1f} mm from the left plot'
    assert h2x0 == nx0 or nx0 < h2x0 + 1e-9
    no_overlaps(fig, 'b')
    assert not sp_lint.lint_fig(fig, 'fig4b_like_for_like'), 'sciplot lint: fix or justify every warning'
    fs.save_panel(fig, os.path.join(PANELS, 'fig4b_like_for_like.pdf'))
    return x0, BR0 + (P1 - BR0)


# ------------------------------------------------------------------------------------------------ composite
def check_composite():
    """The cells in fig4.tex must equal the constants above (panels are never rescaled)."""
    tex = open(os.path.join(FIG4, 'fig4.tex')).read()
    cells = {m[0]: tuple(float(v) for v in m[1:5]) for m in
             re.findall(r'\\Panel\s*\{(\w)\}\s*\{([\d.]+)\}\s*\{([\d.]+)\}\s*\{([\d.]+)\}\s*\{([\d.]+)\}', tex)}
    want = {'a': (0, 0, A_W, A_H), 'b': (0, A_H + GUT, B_W, B_H)}
    assert cells == want, (cells, want)
    assert re.search(r'\\FigureCanvas\{%g\}' % FIG_H, tex), 'fig4.tex canvas height differs from FIG_H'


if __name__ == '__main__':
    check_composite()
    fs.reset_registry()
    with fs.v7_context():                        # scoped style, restored on exit
        a_x0, a_x1, widths = panel_a()
        b_x0, b_x1 = panel_b()
    # alignment (nature-figure gate): a's 0 % above b-left's 0 % (both plots start at P0), b-right ends at a's P1
    assert abs(b_x1 - P1) < 1e-9
    fs.write_registry(os.path.join(FIG4, 'fig4_numbers.csv'))
    print(f'wrote panels and registry ({FIG_W:g} x {FIG_H:g} mm; a {A_W:g} x {A_H:g}: plot {P0:g}-{P1:g} mm, '
          f'{A_PH:.1f} mm high, store cells ' + ', '.join(f'{g} {w:.2f} mm' for g, w in widths.items()) +
          f' x {BAR_H:g} mm; b {B_W:g} x {B_H:g}: left plot {P0:g}-{BL1:.2f}, right plot {BR0:.2f}-{P1:g} mm, '
          f'{MM_PER_PP:.4f} mm per pp in both, {B_PH:.1f} mm high)')
