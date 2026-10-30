"""Figure 5 panels, v7 (binding: ../../DESIGN_V7.md; worked example ../../fig1). The sciplot clean theme
(mmd-ahd/scientific-figure-skill; read, never executed) through fs.v7_context(), plus the bake-off grafts that apply to
data panels: the figure contract and the tinted key area (nature-figure), "grey for context, colour for signal"
(sciplot). Panel letters, contents and every number are those of v6; every count lives in the caption
(scripts/make_caption_fig5.py).

Figure contract (DESIGN_V7 section 1)
  claim   A refusal stops new pixels that declare the refused purpose; pixels that started earlier, declare other
          purposes or declare none keep sending.
  a       (the population comparison; quiet, neutrals only) the 231 working-click stores loaded three ways: in every
          vendor group a refusal lowers new-sandbox firing but does not stop it.
  b       (the decomposition; quiet, brick + greys) what still got through after a refusal, one class per store: the
          brick share (a pixel that started earlier and declares the refused purpose) exists only after Decline.
  c       (HERO, full width: the mechanism of 'started earlier') when a CMP writes 'no' without a click, almost every
          marketing sandbox has already started (brick ticks on a pale brick key area left of the amber write);
          when it writes 'yes', every sandbox starts after it (slate).

  a  dot plot, one small multiple per vendor group along x ('Any vendor' set apart by a wider gap), the three arms left
     to right in the arm coding of Fig. S8a (colors.ARM shapes in neutrals; DESIGN_V7 section 5: the v6 sizes scaled
     by 3.5 / 4.5, so the Default circle is 3.5 pt), each with its uncapped 0.75 pt Wilson 95% CI in the mark's colour,
     joined by a 0.75 pt LIGHT line (the same stores; section 8.2). The y axis is the section 6 share scale, 0-100 %
     (Fig. S8a v7 plots the same values on 0-100), titled 'Stores with a new / sandbox request (%)' in two lines (one
     line would be longer than the plot). Open L axes; 2.2 mm of air under 0 so a mark at 0 never sits on the spine
     (checked). The arms are keyed once, frameless, in muted 7 pt, in one row in the empty top right (section 6: a key
     is the last resort; three arms would need three direct labels).
  b  thin horizontal stacked bars on 0-100 % (section 8.7), one per refusal arm: the share of stores still sending a
     sandboxed ad request, one class per store, stacked from 0 in the order the classes are assigned (= Fig. S8c's
     key and the caption): LEAK brick (a refused purpose), NEUTRAL (only purposes left allowed), GREY_D (no purpose),
     with thin white gaps; these are Fig. S8c's class colours (its dots need visible greys). No track and no key: the
     three classes are named once by direct labels at the Decline bar's segments, a staircase of 7 pt names on 0.35 pt
     NEUTRAL leaders (no leader crosses a name, checked), so b's greys are never read through a's arm key. Under each
     bar, Fig. 4a's grammar: the bar's total as a short 1.0 pt ink tick rising toward the bar's end, on its uncapped
     0.75 pt Wilson 95% CI line (no interval is drawn over a segment). Row names at the left; no left spine (the bars'
     common 0 is the axis origin).
  c  raster, one row per page load in which a CMP wrote 'marketing: no' (upper block) or 'yes' (lower block) without a
     click; one tick per third-party 'marketing' sandbox at its start minus the CMP's consent write, which is the amber
     rule at 0 (on the labelled 0 tick). Symmetric-log time axis (linear between the two ticks nearest 0) so that
     seconds before the write and milliseconds after it are both visible; every sandbox is drawn (checked). Ticks:
     LEAK = started before the 'no' (consent lost), NEUTRAL = after the 'no', HONOUR slate = the 'yes' loads, named by
     Fig. S8d's three-entry tick key (muted 7 pt, the empty top right, clear of every tick: checked). The key area
     (section 3.3, as Fig. 1c): a TINT LEAK ground under the marks, row by row from each 'no' load's first sandbox to
     the write -- the time those sandboxes ran before the refusal arrived. Row ticks count the loads within each
     block, so the row axis is drawn as two spine segments with a 5 mm block gap and two short cut marks ('//', as
     S9d's) in the break. 2.5 mm of air above row 1 and below row n. Two direct labels name the blocks, at one x near
     the left, on white (checked: no tick, no ground under them).
Alignment (section 9, asserted): a's plot and c's plot share their left edge; b's plot and c's plot share their right
edge; a's and b's plots share their top and baseline; row 1 ends just under a's category labels.

Numbers: every drawn value comes from analysis/outputs/stats.json (fs.stat), the shared figures/v7/derived_numbers.json
(source='derived') or figures/v7/fig5/derived_numbers.json (source='derived_fig5', written by derive_fig5_numbers.py) and
is registered as a drawn mark (fmt 'mark') in panels/fig5_numbers.csv; the panels print no number except axis ticks
(panels/fig5_ticks.csv). The trace check (scripts/trace_fig5.py) re-reads both from the current sources.
Every panel is linted by sciplot's rules (scripts/sp_lint.lint_fig) before it is saved.
Run: python3 figures/v7/fig5/scripts/make_fig5_panels.py   (build_fig5.sh composes and checks)
"""
import csv
import json
import os
import re
import sys

import numpy as np
from matplotlib import transforms as mtrans
from matplotlib.lines import Line2D
from matplotlib.markers import TICKUP
from matplotlib.patches import Polygon, Rectangle
from matplotlib.ticker import FixedLocator, NullFormatter

HERE = os.path.dirname(os.path.abspath(__file__))
FIG5 = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG5, '..', 'style')))
import figstyle as fs  # noqa: E402
sys.path.insert(0, HERE)
import sp_lint  # noqa: E402  (sciplot step 5: lint every panel before it is saved)

PANELS = os.path.join(FIG5, 'panels')
LOCAL_DERIVED = os.path.join(FIG5, 'derived_numbers.json')
os.makedirs(PANELS, exist_ok=True)

LQ, RQ = '‘', '’'          # typographic single quotes, as in the other figures

# ---- composite grid (mm); must equal fig5.tex (asserted in check_composite) ----
GUT = fs.GUTTER_MM
A_W, B_W = 132.0, 52.0      # row 1 cells: a | b, the style's 6 mm gutter
assert abs(A_W + GUT + B_W - fs.FIG_W_MM) < 1e-9
R1_H = 50.0                 # row 1: ends just under a's two-line category labels (checked: slack <= R1_SLACK)
R1_SLACK = 0.8
C_H = 58.0                  # row 2: c, the hero (full width, the largest cell)
FIG_H = R1_H + GUT + C_H
TOP, PH = 4.6, 38.0         # a and b: every plot top at TOP; 38 mm so a's 0-100 % axis keeps the arms apart
YR_A = 16.0                 # a and c (one shared left edge): room for a two-line rotated y title + 3-digit ticks
RM = 0.6                    # a's and b's plots end 0.6 mm inside their cells
CI_LW = fs.LW['error']      # 0.75 pt, no caps
assert 100.0 <= FIG_H <= 150.0          # DESIGN_V7 section 9
assert C_H * fs.FIG_W_MM >= 0.35 * FIG_H * fs.FIG_W_MM          # the hero gets >= 35 % of the figure

# ---- local v7 additions (DESIGN_V7 section 5; nothing here is a new token: the style is not edited) ----
V7_ARM_SCALE = fs.V7_LW['marker'] / fs.ARM['Default']['ms']     # 3.5 / 4.5: the Default circle is 3.5 pt
V7_ARM_MEW = {'Default': fs.V7_LW['mew'], 'Decline': 0.8, 'GPC': fs.V7_LW['mew']}   # open square: a heavier edge
CONNECT_LW = 0.75           # section 8.2: lines joining arms are 0.75 pt LIGHT
MINOR_LEN, MINOR_LW = 1.5, 0.48         # sciplot clean-nature minor ticks (c's log decades)

# a
A_PW = A_W - YR_A - RM
A_ANY_GAP = 1.45            # 'Any vendor' at 0, the vendor groups at A_ANY_GAP + i: the summary set apart by a gap
A_DX = 0.25                 # within a group: Default -A_DX, Decline 0, GPC +A_DX (category units)
A_PAD = 0.24                # category units of air between the outermost marks and the plot's ends (>= 2 mm)
A_XLIM = (-A_DX - A_PAD, A_ANY_GAP + 6 + A_DX + A_PAD)
A_YMAX, A_YSTEP = 100, 25  # section 6: share axes run 0-100 (Fig. S8a v7 plots the same values on 0-100 too)
A_AIR_MM = 2.2              # section 6: air between the 0 line and the bottom spine
A_YLO = -A_AIR_MM * A_YMAX / (PH - A_AIR_MM)
A_TITLE = 'Stores with a new\nsandbox request (%)'  # a: a newly created sandbox sent an ad request within 10 s (caption)
ARMS = ('Default', 'Decline', 'GPC')

# b (one plot; horizontal thin bars in Fig. 4a's grammar: the bar, then its total and CI on a line just under it)
B_X0 = 11.5                 # plot left: the 7 pt row names 'Decline', 'GPC' sit left of it, >= 2 mm from the edge
B_RM = 2.3                  # b's plot ends 2 mm inside its cell: the '100' tick label is centred on its right end
B_PW = B_W - B_X0 - B_RM
BAR_MM = 2.8                # thin bars, as Fig. 4a's
B_EST_DY = 3.6              # bar centre -> its total's tick and CI line (Fig. 4a's EST_DY)
B_ROW_Y_MM = {'decline_refused': 19.4, 'gpc': 7.8}  # bar centres, mm above the baseline (Decline above GPC, as in a)
B_TITLE = 'Stores still sending (%)'    # b: stores with a sandboxed ad request after the refusal
B_CLASSES = [   # stacked from 0 in the order the classes are assigned (= Fig. S8c's key and the caption):
    ('kept_sending_refused_purpose', fs.LEAK, 'A refused purpose'),       # declares the refused purpose, started before
    ('only_left_allowed_purposes', fs.NEUTRAL, 'Only purposes left allowed'),   # Fig. S8c: the same names and colours
    ('no_purpose', fs.GREY_D, 'No purpose'),
]
B_ASSIGN_ORDER = ['kept_sending_refused_purpose', 'only_left_allowed_purposes', 'no_purpose']   # caption
B_SEG_GAP_PT = 0.6          # thin white gap between segments
B_TOTAL_MS, B_TOTAL_MEW = fs.V7_LW['marker'], 1.0   # the total: a short 1.0 pt tick (section 5's summary tick) that
                            # rises from the CI line toward its bar's end (a centred tick would read as '+')
B_LAB_DY0 = 3.6             # class names (direct labels at the Decline bar's segments, a staircase): the lowest
B_LAB_PITCH = 3.4           # baseline sits B_LAB_DY0 mm above the bar's top, the others B_LAB_PITCH mm apart
B_LEAD_GAP = 0.5            # leaders stop this short of the bar's top and of their label (section 7.3)

# c (its left edge = a's plot left, its right edge = b's plot right)
C_X0 = YR_A
C_X1 = A_W + GUT + B_X0 + B_PW
C_TOP = 1.0
C_PH = C_H - C_TOP - 9.0    # under the plot: 6 pt ticks + the 7 pt axis title
C_AIR, C_GAP = 2.5, 5.0     # mm of white above row 1 and below row n; the gap between the two blocks (>= 2.5 mm, so
                            # the 'no' block's last rows read as 'no')
C_SPINE_GAP = 3.0           # mm: the row axis breaks in the middle of the block gap (two row scales), marked by
CUT_W, CUT_H, CUT_SEP = 1.8, 0.9, 0.9   # two short cut marks ('//', S9d's, turned 90 degrees): each 1.8 x 0.9 mm,
                                        # 0.9 mm apart, centred on the spine in the break
C_KEY_MS = 2.6 * fs.PT_PER_MM           # the tick key (Fig. S8d's): '|' handles 2.6 mm tall, 1.0 pt wide
TICK_MS, TICK_MEW = 1.6, 0.75           # sandbox ticks: the ticks are the story here (Fig 1c's context ticks: 1.4 x 0.5)
C_XLIM = (-5.0, 2.0)        # s; every sandbox inside (checked)
C_LINTHRESH = 0.01          # s; symlog: linear inside +-C_LINTHRESH, logarithmic beyond (base 10)
C_LINSCALE = 0.25           # each half of the linear part spans 0.25 / 0.9 = 0.28 decade
C_MAJOR = [-1, -0.1, -0.01, 0, 0.01, 0.1, 1]
C_ROW_TICKS = {'deny': (1, 50, 100), 'grant': (1, 25)}     # rows counted within each block (Fig 1c: 1, 50, 100, ...)
C_TITLE_Y = 'Page loads'


def check_composite():
    """The cells in fig5.tex must equal the constants above (panels are never rescaled)."""
    tex = open(os.path.join(FIG5, 'fig5.tex')).read()
    cells = {m[0]: tuple(float(v) for v in m[1:5]) for m in
             re.findall(r'\\Panel\s*\{(\w)\}\s*\{([\d.]+)\}\s*\{([\d.]+)\}\s*\{([\d.]+)\}\s*\{([\d.]+)\}', tex)}
    want = {'a': (0, 0, A_W, R1_H), 'b': (A_W + GUT, 0, B_W, R1_H), 'c': (0, R1_H + GUT, fs.FIG_W_MM, C_H)}
    bad = {k: (cells.get(k), w) for k, w in want.items() if cells.get(k) is None or
           any(abs(a - b) > 1e-6 for a, b in zip(cells[k], w))}
    assert not bad, f'fig5.tex cells differ from make_fig5_panels.py: {bad}'
    assert re.search(r'\\FigureCanvas\{%g\}' % FIG_H, tex), 'fig5.tex canvas height differs from FIG_H'


# ------------------------------------------------------------------------------------------------ number helpers
_LD = None


def ld(key):
    """Value at a '/'-separated key of fig5/derived_numbers.json (the record's 'value' level implied)."""
    global _LD
    if _LD is None:
        _LD = json.load(open(LOCAL_DERIVED))
    name, _, rest = key.partition('/')
    cur = _LD[name]['value']
    for part in rest.split('/') if rest else []:
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    return cur


def NL(key, f='int'):
    """Render and register a number from fig5/derived_numbers.json (same registry as fs.N; used by the caption)."""
    v = ld(key)
    s = fs.render(v, f)
    fs._REG.append(dict(text=s, shown=fs.typo(s), source='derived_fig5', key=key, fmt=f, value=json.dumps(v)))
    return fs.typo(s)


def mark(key, source='stats'):
    """Register a value that is drawn but not printed (dot position, CI end, bar height, lag list) and return it."""
    v = fs.stat(key) if source == 'stats' else fs.derived(key) if source == 'derived' else ld(key)
    fs._REG.append(dict(text='', shown='', source=source, key=key, fmt='mark', value=json.dumps(v)))
    return v


def share(key):
    """A stats share record in percentage units (p, lo, hi), each registered as a drawn mark."""
    return tuple(100 * mark(f'{key}/{f}') for f in ('p', 'lo', 'hi'))


TICKS = []


def record_ticks(fig, panel):
    """Tick labels are axis scale, not results: record them so the trace check can tell them from data numbers."""
    fig.canvas.draw()
    for ax in fig.axes:
        for axis, labs in (('x', ax.get_xticklabels()), ('y', ax.get_yticklabels())):
            for t in labs:
                if t.get_visible() and t.get_text().strip():
                    TICKS.append(dict(panel=panel, axis=axis, text=t.get_text()))


def vkey(v):
    return v.replace('/', '~1')          # JSON-pointer escape for 'Reddit/other'


def arm_style(arm):
    """The arm marker of colors.ARM in its v6 neutrals (fs.marker_style), at the v7 size (section 5)."""
    st = fs.marker_style(arm)
    st['ms'] = st['ms'] * V7_ARM_SCALE
    st['mew'] = V7_ARM_MEW[arm]
    return st


def arm_handle(arm):
    st = arm_style(arm)
    return Line2D([], [], ls='none', marker=st['marker'], ms=st['ms'], mfc=st['mfc'], mec=st['mec'], mew=st['mew'])


# ------------------------------------------------------------------------------------------------ geometry helpers
def bb_mm(fig, artist):
    """(x0, x1, top, bottom) of an artist's extent in panel mm (y measured down from the panel top)."""
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


def label_gaps(fig, ax):
    """Horizontal white space (mm) between neighbouring x tick labels of a categorical axis."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    px = fig.dpi / 25.4
    bbs = sorted((t.get_window_extent(r) for t in ax.get_xticklabels() if t.get_text()), key=lambda b: b.x0)
    return [(b.x0 - a.x1) / px for a, b in zip(bbs, bbs[1:])]


def within_panel(fig, ax, name):
    """The plot and all its labels end inside the panel, clear of the letter zone. Returns (x0, x1, bottom) mm."""
    W, H = fs.size_mm(fig)
    x0, x1, _, b = bb_mm(fig, ax)
    assert x0 >= 0.8 and x1 <= W - 0.3 and b <= H - 0.3, f'{name}: plot or labels leave the panel ({x0:.2f}, {x1:.2f}, {b:.2f})'
    return x0, x1, b


def legend_clear(fig, lg, boxes, name, pad_mm=1.0):
    """The key stays at least pad_mm clear of every drawn box (display-unit extents of marks, CIs, bars)."""
    fig.canvas.draw()
    px = fig.dpi / 25.4
    lgb = lg.get_window_extent(fig.canvas.get_renderer())
    for (x0, y0, x1, y1) in boxes:
        clear = (x1 < lgb.x0 - pad_mm * px or x0 > lgb.x1 + pad_mm * px or
                 y1 < lgb.y0 - pad_mm * px or y0 > lgb.y1 + pad_mm * px)
        assert clear, f'{name}: the key crowds a drawn mark'


def legend_inside(fig, ax, lg, name, pad_mm=0.3):
    """The key lies inside the plot area."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    px = fig.dpi / 25.4
    lb, ab = lg.get_window_extent(r), ax.get_window_extent(r)
    assert (lb.x0 >= ab.x0 + pad_mm * px and lb.x1 <= ab.x1 - pad_mm * px and lb.y0 >= ab.y0 + pad_mm * px
            and lb.y1 <= ab.y1 - pad_mm * px), f'{name}: the key leaves the plot area'


def muted_key(ax, handles, labels, **kw):
    """Section 6: a key is frameless, ordered like the data, in muted 7 pt (SP_MUTED text; marks as drawn)."""
    lg = fs.legend(ax, handles, labels, frameon=False, fontsize=fs.FS['legend'], borderpad=0.0, **kw)
    for t in lg.get_texts():
        t.set_color(fs.SP_MUTED)
    return lg


# ================================================================================================= panel a
def panel_a():
    """Dot plot: share of the 231 working-click stores on which a newly created sandbox sent an ad request, per vendor
    group and arm, with Wilson 95% CIs, in the arm neutrals. Returns (label gaps, bottom of the text, mark clearance,
    plot (top, baseline) mm)."""
    fig = fs.panel(A_W, R1_H)
    base = 'fig5/a'
    av = 'Any vendor'
    ax = fs.axes_mm(fig, YR_A, TOP, A_PW, PH)
    fs.pct_axis(ax, 'y', 0, A_YMAX, A_YSTEP)
    ax.set_ylim(A_YLO, A_YMAX)
    ax.set_ylabel(A_TITLE, linespacing=1.15)                # two centred lines: the plot is shorter than one line
    groups = [av] + list(fs.VENDOR_ORDER)
    xs = [0.0] + [A_ANY_GAP + i for i in range(len(fs.VENDOR_ORDER))]
    labels = ['Any\nvendor'] + [v.replace('/', '/\n') for v in fs.VENDOR_ORDER]
    ax.set_xlim(*A_XLIM)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=fs.FS['cat'], linespacing=1.1, color=fs.SP_FG)
    fs.category_axis(ax, 'x')                            # category names under each group, no tick marks
    mark(base + '/n_clicked')
    off = {'Default': -A_DX, 'Decline': 0.0, 'GPC': A_DX}
    px = fig.dpi / 25.4
    mm_per_unit = PH / (A_YMAX - A_YLO)
    mm_per_cat = A_PW / (A_XLIM[1] - A_XLIM[0])
    assert A_PAD * mm_per_cat >= 2.0, 'a: less than 2 mm of air between the outer marks and the plot ends'
    drawn = []                                           # display extents of every mark and CI (key clearance)
    clear_min = np.inf                                   # smallest gap (mm) between a mark and the bottom spine
    for g, x in zip(groups, xs):
        est = {arm: share(f'{base}/{vkey(g)}/{arm}') for arm in ARMS}
        # the thin line through the three estimates: the same stores, three loads (LIGHT, behind the marks)
        ax.plot([x + off[a] for a in ARMS], [est[a][0] for a in ARMS], color=fs.LIGHT, lw=CONNECT_LW,
                solid_joinstyle='round', solid_capstyle='round', zorder=1.5)
        for arm in ARMS:
            p, lo, hi = est[arm]
            assert 0 <= lo <= p <= hi <= A_YMAX, (g, arm)
            st = arm_style(arm)
            xa = x + off[arm]
            ax.plot([xa, xa], [lo, hi], color=st['color'], lw=CI_LW, solid_capstyle='butt', zorder=3, clip_on=False)
            ax.plot([xa], [p], ls='none', marker=st['marker'], ms=st['ms'], mfc=st['mfc'], mec=st['mec'],
                    mew=st['mew'], zorder=4, clip_on=False)
            half_mm = (st['ms'] + st['mew']) / 2 / fs.PT_PER_MM
            clear_min = min(clear_min, (p - A_YLO) * mm_per_unit - half_mm)
            fig.canvas.draw()
            (dx, dlo), (_, dhi) = ax.transData.transform((xa, lo)), ax.transData.transform((xa, hi))
            _, dp = ax.transData.transform((xa, p))
            half = half_mm * px
            drawn.append((dx - half, min(dlo, dp - half), dx + half, max(dhi, dp + half)))
        # within every vendor group (and overall) Default is the highest of the three (caption, alt text)
        assert est['Default'][0] > max(est['Decline'][0], est['GPC'][0]), g
    assert clear_min >= 1.2, f'a: a mark at 0 nearly touches the bottom spine (clearance {clear_min:.2f} mm)'
    # the one key: the arm marks as plotted, one row, top right, frameless, muted 7 pt
    lg = muted_key(ax, [arm_handle(a) for a in ARMS], list(ARMS), loc='upper right', ncol=3, handlelength=0.8,
                   handletextpad=0.45, columnspacing=1.5, borderaxespad=0.15)
    legend_clear(fig, lg, drawn, 'a')
    legend_inside(fig, ax, lg, 'a', pad_mm=0.0)
    gaps = label_gaps(fig, ax)
    assert min(gaps) >= 2.5, f'a: category labels {gaps} mm apart (crowded)'
    x0, _, bottom = within_panel(fig, ax, 'a')
    assert x0 >= 2.0, f'a: the y title starts {x0:.2f} mm from the figure edge (section 9: >= 2 mm)'
    no_overlaps(fig, 'a')
    record_ticks(fig, 'a')
    assert not sp_lint.lint_fig(fig, 'fig5a_dots'), 'sciplot lint: fix or justify every warning'
    fs.save_panel(fig, os.path.join(PANELS, 'fig5a_dots.pdf'))
    return gaps, bottom, clear_min


# ================================================================================================= panel b
def panel_b():
    """Share of stores still sending after the refusal, as thin horizontal bars stacked by exclusive class in the order
    the classes are assigned (Fig. S8c's key order), the classes named once by direct labels at the Decline bar's
    segments; under each bar its total (a short tick) with the Wilson CI (Fig. 4a's grammar). Returns the bottom of
    the panel's text (mm)."""
    fig = fs.panel(B_W, R1_H)
    ex = 'fig5b_exclusive_classes'
    ax = fs.axes_mm(fig, B_X0, TOP, B_PW, PH)
    fs.pct_axis(ax, 'x', 0, 100, 25)
    ax.set_xlabel(B_TITLE)
    ax.set_ylim(0, PH)                                    # y in mm above the baseline (rows are named, not measured)
    ax.spines['left'].set_visible(False)                  # the bars' common 0 is the axis origin; rows are named
    rows = [('decline_refused', 'Decline', 'fig5/c/decline_n', 'fig5/b/Shopify recorded a refusal/decline_any_after',
             None),
            ('gpc', 'GPC', 'fig5/c/gpc_n', 'fig5/c/composition/gpc/any', 'other_unmatched')]
    ax.set_yticks([B_ROW_Y_MM[r[0]] for r in rows])
    ax.set_yticklabels([r[1] for r in rows], fontsize=fs.FS['cat'], color=fs.SP_FG)
    ax.tick_params(axis='y', length=0, pad=3.0)
    # the gate held every new pixel declaring the refused purpose (caption): nothing of it is drawn, assert the claim
    assert fs.derived(f'{ex}/decline_refused/new_pixel_declaring_refused_purpose') == 0
    assert fs.derived(f'{ex}/gpc/pixel_declaring_sale') == 0
    assert B_ASSIGN_ORDER == [c for c, _, _ in B_CLASSES]  # one order: bars, labels, caption, Fig. S8c's key
    gap = B_SEG_GAP_PT / fs.PT_PER_MM * 100 / B_PW        # white gap between segments, in % units
    bh = BAR_MM                                           # bar thickness in y units (mm)
    px = fig.dpi / 25.4
    mm_x = B_PW / 100.0                                   # mm per % unit
    seg_mid = {}                                          # Decline: class -> (segment centre %, bar top mm)
    for blk, _, nkey, anykey, unclassed in rows:
        y = B_ROW_Y_MM[blk]
        n = mark(nkey)
        k_any = mark(anykey + '/k')
        assert mark(anykey + '/n') == n and k_any == fs.derived(f'{ex}/{blk}/any'), blk
        segs = []
        for cls, c, _ in B_CLASSES:
            k = mark(f'{ex}/{blk}/{cls}', 'derived') if cls in fs.derived(f'{ex}/{blk}') else 0
            segs.append((cls, k, c))
        unc = mark(f'{ex}/{blk}/{unclassed}', 'derived') if unclassed else 0
        assert sum(k for _, k, _ in segs) + unc == k_any, blk           # every still-sending store in one class
        x = 0.0
        live = [(cls, k, c) for cls, k, c in segs if k > 0]
        for j, (cls, k, c) in enumerate(live):
            w = 100 * k / n
            x0 = x + (gap / 2 if j > 0 else 0)
            x1 = x + w - (gap / 2 if j < len(live) - 1 else 0)
            ax.add_patch(Rectangle((x0, y - bh / 2), x1 - x0, bh, facecolor=c, edgecolor='none', linewidth=0,
                                   zorder=2))
            if blk == 'decline_refused':
                seg_mid[cls] = ((x0 + x1) / 2, x1 - x0)
            x += w
        assert abs(x - 100 * (k_any - unc) / n) < 1e-9
        # the bar's total (all still-sending stores) with its Wilson 95% CI on a line just under the bar, in ink:
        # Fig. 4a's grammar (the summary sits under its bar), so no interval is ever drawn over a segment
        p, lo, hi = share(anykey)
        assert lo <= x <= hi and abs(p - x) * mm_x < 0.1  # the tick sits at the bar's end (GPC: + 1 unmatched store)
        ye = y - B_EST_DY
        ax.plot([lo, hi], [ye, ye], color=fs.SP_FG, lw=CI_LW, solid_capstyle='butt', zorder=3, clip_on=False)
        ax.plot([p], [ye], ls='none', marker=TICKUP, ms=B_TOTAL_MS, mew=B_TOTAL_MEW, color=fs.SP_FG, zorder=3.2,
                clip_on=False)
        assert B_TOTAL_MS / fs.PT_PER_MM <= B_EST_DY - bh / 2 - 0.6     # the tick stops short of its bar
        fig.canvas.draw()
        (_, dy0), (_, dy1) = ax.transData.transform((0, y - bh / 2)), ax.transData.transform((0, y + bh / 2))
        assert abs((dy1 - dy0) / px - BAR_MM) < 0.05
        # the summary line sits closer to its own bar than to anything below it (it reads as that bar's total)
        assert B_EST_DY - bh / 2 >= 1.5
    gy = B_ROW_Y_MM['gpc'] - B_EST_DY
    assert gy - B_TOTAL_MS / fs.PT_PER_MM / 2 >= 2.0, "b: the GPC total sits on the axis"           # section 6 air
    assert (B_ROW_Y_MM['decline_refused'] - B_EST_DY) - (B_ROW_Y_MM['gpc'] + bh / 2) >= 4.0, 'b: rows crowd'
    # the Decline bar is the longer one (caption: 'a third of Decline stores, a fifth of GPC stores')
    assert fs.stat(rows[0][3] + '/p') > fs.stat(rows[1][3] + '/p')
    # the class names: direct labels at the Decline bar's segments, a staircase in class order (top = first class),
    # each left-aligned on a 0.35 pt NEUTRAL leader that rises from its segment's centre (section 4: leader)
    assert set(seg_mid) == {c for c, _, _ in B_CLASSES}, 'b: the Decline bar must show every class'
    bar_top = B_ROW_Y_MM['decline_refused'] + bh / 2
    labs, leads = [], []
    nc = len(B_CLASSES)
    for i, (cls, _, name) in enumerate(B_CLASSES):
        xm, wseg = seg_mid[cls]
        assert wseg * mm_x >= 1.2, f'b: the {cls} segment is too thin to label'
        yb = bar_top + B_LAB_DY0 + (nc - 1 - i) * B_LAB_PITCH          # baseline of this label
        t = fs.direct_label(ax, xm, yb, name, ha='left', va='baseline', color=fs.SP_FG)
        ln = fs.leader(ax, (xm, bar_top + B_LEAD_GAP), (xm, yb - B_LEAD_GAP), color=fs.NEUTRAL)
        labs.append((t, xm))
        leads.append((ln, xm, yb - B_LEAD_GAP))
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    inv = ax.transData.inverted()
    xs_lead = [xm for _, xm in labs]
    assert all(b - a >= 0.8 / mm_x for a, b in zip(xs_lead, xs_lead[1:])), 'b: leaders closer than 0.8 mm'
    for (t, xm) in labs:                                   # no leader passes through a label (section 4)
        bb = t.get_window_extent(r)
        (lx0, ly0), (lx1, ly1) = inv.transform((bb.x0, bb.y0)), inv.transform((bb.x1, bb.y1))
        for (_, xl, ytop) in leads:
            if ytop > ly0 and xl < xm:                    # a leader that rises past this label runs left of it
                assert lx0 - xl >= 0.6 / mm_x, f'b: a leader runs into {t.get_text()!r}'
        assert ly1 <= PH - 2.0, f'b: {t.get_text()!r} reaches the top of the plot'
    _, _, bottom = within_panel(fig, ax, 'b')
    no_overlaps(fig, 'b')
    record_ticks(fig, 'b')
    assert not sp_lint.lint_fig(fig, 'fig5b_gate'), 'sciplot lint: fix or justify every warning'
    fs.save_panel(fig, os.path.join(PANELS, 'fig5b_gate.pdf'))
    return bottom


# ================================================================================================= panel c
def race_tick_label(t):
    """Signed race-axis tick label in s ('−1', '−0.1', '−0.01', '0', '+0.01', ...): as fs.signed_ticks, with the
    decimals each decade needs."""
    if t == 0:
        return '0'
    dec = max(0, -int(np.floor(np.log10(abs(t)) + 1e-9)))
    return ('+' if t > 0 else fs.MINUS) + fs.fmt_dec(abs(t), dec)


def panel_c():
    """Raster: one row per load, one tick per third-party 'marketing' sandbox at (start minus the CMP's consent write);
    the loads where the CMP wrote 'no' above those where it wrote 'yes', on a symmetric-log time axis; the key area
    (TINT LEAK) between each 'no' load's first sandbox and the write."""
    fig = fs.panel(fs.FIG_W_MM, C_H)
    d = 'fig5/d'
    rc = 'fig5c_race_per_sandbox'
    rl = 'fig5c_race_loads'
    XL, XR = C_XLIM
    lags = {ch: mark(f'{rl}/{ch}/lags_ms', 'derived_fig5') for ch in ('deny', 'grant')}
    n = {ch: len(v) for ch, v in lags.items()}
    for ch in lags:
        assert n[ch] == ld(f'{rl}/{ch}/n_loads') == mark(f'{d}/{ch}/loads')
    rows_total = n['deny'] + n['grant']
    pitch = (C_PH - 2 * C_AIR - C_GAP) / rows_total          # mm per load row (both blocks: one pitch, honest heights)
    gap_rows = C_GAP / pitch
    air_rows = C_AIR / pitch
    y_off = {'deny': 0.0, 'grant': n['deny'] + gap_rows}       # row 1 of a block sits at y_off + 1
    ax = fs.axes_mm(fig, C_X0, C_TOP, C_X1 - C_X0, C_PH)
    ax.set_xscale('symlog', base=10, linthresh=C_LINTHRESH, linscale=C_LINSCALE)
    ax.set_xlim(XL, XR)
    y_top, y_bot = 0.5 - air_rows, rows_total + gap_rows + 0.5 + air_rows
    ax.set_ylim(y_bot, y_top)                                   # rows run top to bottom
    ax.set_xticks(C_MAJOR)
    ax.set_xticklabels([race_tick_label(t) for t in C_MAJOR])
    minors = [s * k * 10.0 ** e for s in (-1, 1) for e in (-2, -1, 0) for k in range(2, 10)]
    minors = sorted(m for m in minors if XL < m < XR)                         # log minor ticks (2-9 per decade)
    ax.xaxis.set_minor_locator(FixedLocator(minors))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.tick_params(axis='x', which='minor', bottom=True, top=False, length=MINOR_LEN, width=MINOR_LW, color=fs.SP_AXIS)
    ax.set_xlabel(fs.RACE_AXIS_TITLE)
    ytk, ylab = [], []
    for ch, rows in C_ROW_TICKS.items():
        assert max(rows) <= n[ch]
        ytk += [y_off[ch] + r for r in rows]
        ylab += [str(r) for r in rows]
    ax.set_yticks(ytk)
    ax.set_yticklabels(ylab)
    ax.tick_params(axis='y', which='minor', left=False)
    ax.set_ylabel(C_TITLE_Y)
    # the row axis restarts at 1 in each block: two spine segments, broken in the middle of the block gap
    ax.spines['left'].set_visible(False)
    y_sep = n['deny'] + 0.5 + gap_rows / 2
    half_break = C_SPINE_GAP / 2 / pitch
    tr = mtrans.blended_transform_factory(ax.transAxes, ax.transData)
    for y0, y1 in ((y_top, y_sep - half_break), (y_sep + half_break, y_bot)):
        ax.add_line(Line2D([0, 0], [y0, y1], transform=tr, color=fs.SP_AXIS, lw=fs.V7_LW['axis'],
                           solid_capstyle='projecting', clip_on=False, zorder=2.5))
    # ... and the break is marked: two short parallel cut marks across the spine in the break (S9d's '//', turned
    # 90 degrees for a vertical axis), so the two row scales never read as one
    assert CUT_SEP + CUT_H <= C_SPINE_GAP - 0.6 and C_SPINE_GAP <= C_GAP - 1.0
    Wf, Hf = fs.size_mm(fig)
    ysep_mm = C_TOP + (y_sep - y_top) / (y_bot - y_top) * C_PH                  # panel mm from the top
    for dy in (-CUT_SEP / 2, CUT_SEP / 2):
        yc = ysep_mm + dy
        fig.add_artist(Line2D([(C_X0 - CUT_W / 2) / Wf, (C_X0 + CUT_W / 2) / Wf],
                              [1 - (yc + CUT_H / 2) / Hf, 1 - (yc - CUT_H / 2) / Hf], transform=fig.transFigure,
                              color=fs.SP_AXIS, lw=fs.V7_LW['axis'], clip_on=False))

    # the CMP's consent write: amber rule at 0, full plot height, under the ticks (it sits on the labelled 0 tick)
    fs.event_line(ax, 0.0, zorder=1.5)

    pts = {}
    for ch in ('deny', 'grant'):
        xs = np.array([v / 1000 for row in lags[ch] for v in row])
        ys = np.array([y_off[ch] + i + 1 for i, row in enumerate(lags[ch]) for _ in row])
        pts[ch] = (xs, ys)
        before = xs < 0
        assert len(xs) == mark(f'{d}/{ch}/pixels')
        assert int(before.sum()) == mark(f'{d}/{ch}/pixels_before')
        assert ((xs > XL) & (xs < XR)).all(), f'c: a {ch} sandbox lies outside the axis'      # every sandbox drawn
        if ch == 'deny':      # brick: started before the 'no' (consent lost); grey: started after it
            layers = ((~before, fs.NEUTRAL, 3), (before, fs.LEAK, 3.2))
            assert int((~before).sum()) == mark(f'{rc}/deny/after', 'derived')
        else:                 # slate: the 'yes' loads, every sandbox after the write (consent honoured)
            assert int(before.sum()) == 0 and (xs > 0).all()
            layers = ((xs > 0, fs.HONOUR, 3),)
        for m, col, z in layers:
            ax.plot(xs[m], ys[m], ls='none', marker='|', ms=TICK_MS, mew=TICK_MEW, color=col, zorder=z)
    # the medians the caption states sit on the drawn side of the line
    assert mark(f'{rc}/deny/median_lag_ms', 'derived') < 0 < mark(f'{rc}/grant/median_lag_ms', 'derived')

    # the key area (TINT LEAK, never alpha): for every 'no' load whose first sandbox started before the write, the
    # time from that first sandbox to the write, row by row -- a staircase on the drawn ticks' own rows and times,
    # bounded by the amber rule, under every mark. Rows are sorted by the first sandbox, so the 'no' loads whose
    # first sandbox came after the write (no ground) are the last rows of the block.
    firsts = np.array([min(row) / 1000 for row in lags['deny']])
    assert (np.diff(firsts) >= 0).all(), "c: the 'no' rows are not sorted by their first sandbox"
    k_pre = int((firsts < 0).sum())
    assert (firsts[:k_pre] < 0).all() and (firsts[k_pre:] >= 0).all()
    poly = []
    for i in range(k_pre):
        yc = y_off['deny'] + i + 1
        poly += [(firsts[i], yc - 0.5), (firsts[i], yc + 0.5)]
    poly += [(0.0, y_off['deny'] + k_pre + 0.5), (0.0, y_off['deny'] + 0.5)]
    ax.add_patch(Polygon(poly, closed=True, facecolor=fs.TINT['LEAK'], edgecolor='none', zorder=1.0))

    # two short direct labels naming the blocks: same x, near the left of the plot, each on white in its own block
    fig.canvas.draw()
    px = fig.dpi / 25.4
    x_lab = ax.transData.inverted().transform(ax.transAxes.transform((0, 0)) + np.array([2.0 * px, 0]))[0]
    lab_no = fs.direct_label(ax, x_lab, y_off['deny'] + 0.86 * n['deny'], f'CMP wrote {LQ}no{RQ}', ha='left',
                             va='center', color=fs.SP_FG)
    lab_yes = fs.direct_label(ax, x_lab, y_off['grant'] + (n['grant'] + 1) / 2, f'CMP wrote {LQ}yes{RQ}', ha='left',
                              va='center', color=fs.SP_FG)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    inv = ax.transData.inverted()
    for lab in (lab_no, lab_yes):
        bb = lab.get_window_extent(r)
        for xs, ys in pts.values():
            dxy = ax.transData.transform(np.column_stack([xs, ys]))
            hit = ((dxy[:, 0] >= bb.x0 - 0.6 * px) & (dxy[:, 0] <= bb.x1 + 0.6 * px) &
                   (dxy[:, 1] >= bb.y0 - 0.6 * px) & (dxy[:, 1] <= bb.y1 + 0.6 * px))
            assert not hit.any(), f'c: label {lab.get_text()!r} covers ticks'
    # the 'no' label sits on white: right of it, every row it spans starts its ground >= 1 mm further right
    bb = lab_no.get_window_extent(r)
    (xr, ya), (_, yb) = inv.transform((bb.x1 + 1.0 * px, bb.y1)), inv.transform((bb.x1, bb.y0))
    span = [i for i in range(k_pre) if min(ya, yb) - 0.5 <= y_off['deny'] + i + 1 <= max(ya, yb) + 0.5]
    assert span and all(firsts[i] > xr for i in span), "c: the 'no' label runs onto the key area"
    # each label stays inside its own block, and both start at the same x
    for lab, ch in ((lab_no, 'deny'), (lab_yes, 'grant')):
        bb = lab.get_window_extent(r)
        _, ya = inv.transform((0, bb.y1))
        _, yb = inv.transform((0, bb.y0))
        assert y_off[ch] + 0.5 <= ya and yb <= y_off[ch] + n[ch] + 0.5, f'c: label {lab.get_text()!r} leaves its block'
    assert abs(lab_no.get_window_extent(r).x0 - lab_yes.get_window_extent(r).x0) < 0.01
    # the tick key (Fig. S8d's three entries, its order and handles): frameless, muted 7 pt, in the empty top right,
    # right of the amber rule and clear of every tick (it explains the few grey ticks after the 'no')
    hs = [Line2D([], [], ls='none', marker='|', ms=C_KEY_MS, mew=1.0, color=c) for c in (fs.LEAK, fs.NEUTRAL, fs.HONOUR)]
    lg = muted_key(ax, hs, [f'Before a {LQ}no{RQ}', f'After a {LQ}no{RQ}', f'After a {LQ}yes{RQ}'], loc='upper right',
                   handlelength=0.7, handletextpad=0.6, labelspacing=0.35, borderaxespad=0.2)
    legend_inside(fig, ax, lg, 'c', pad_mm=0.0)
    fig.canvas.draw()
    lgb = lg.get_window_extent(fig.canvas.get_renderer())
    for xs, ys in pts.values():
        dxy = ax.transData.transform(np.column_stack([xs, ys]))
        hit = ((dxy[:, 0] >= lgb.x0 - 1.0 * px) & (dxy[:, 0] <= lgb.x1 + 1.0 * px) &
               (dxy[:, 1] >= lgb.y0 - 1.0 * px) & (dxy[:, 1] <= lgb.y1 + 1.0 * px))
        assert not hit.any(), 'c: the key crowds a sandbox tick'
    assert lgb.x0 >= ax.transData.transform((0.0, 0))[0] + 10 * px, 'c: the key crowds the amber rule'
    x0, _, _ = within_panel(fig, ax, 'c')
    assert x0 >= fs.LETTER_ZONE_MM[0] + 0.1, f'c: the y title reaches into the letter column ({x0:.2f} mm)'
    no_overlaps(fig, 'c')
    record_ticks(fig, 'c')
    # widths (mm) of the two blocks' spans along x, for the build log: the 'yes' block is not a sliver
    xa = lambda v: ax.transData.transform((v, 0))[0] / px                    # noqa: E731
    span = {ch: xa(np.percentile(pts[ch][0], 95)) - xa(np.percentile(pts[ch][0], 5)) for ch in pts}
    assert span['grant'] >= 15, f"c: the 'yes' block spans only {span['grant']:.1f} mm"
    assert not sp_lint.lint_fig(fig, 'fig5c_race'), 'sciplot lint: fix or justify every warning'
    fs.save_panel(fig, os.path.join(PANELS, 'fig5c_race.pdf'))
    return pitch, span, k_pre


if __name__ == '__main__':
    check_composite()
    fs.reset_registry()
    with fs.v7_context():                            # scoped v7 style (sciplot clean theme), restored on exit
        a_gaps, a_bottom, a_clear = panel_a()
        b_bottom = panel_b()
        pitch, span, k_pre = panel_c()
    # row 1 ends just under its lowest text: the gap to c is the 6 mm gutter, not an empty band
    slack = R1_H - max(a_bottom, b_bottom)
    assert 0.3 <= slack <= R1_SLACK, f'row 1 has {slack:.2f} mm of empty band under its labels'
    fs.write_registry(os.path.join(PANELS, 'fig5_numbers.csv'))
    with open(os.path.join(PANELS, 'fig5_ticks.csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['panel', 'axis', 'text'])
        w.writeheader()
        w.writerows(TICKS)
    print(f'wrote panels and registry in {PANELS} (190 x {FIG_H:g} mm; a {A_W:g} x {R1_H:g}: plot {A_PW:.1f} x {PH:g}, '
          f'label gaps >= {min(a_gaps):.1f} mm, marks >= {a_clear:.2f} mm above the bottom spine; b {B_W:g} x {R1_H:g}: '
          f'plot {B_PW:.1f} x {PH:g}, bars {BAR_MM:g} mm; row 1 slack {slack:.2f} mm; c 190 x {C_H:g} (hero): plot '
          f'{C_X1 - C_X0:.1f} x {C_PH:g}, {pitch:.3f} mm per load row, key area on {k_pre} rows; 5-95 % spans: no '
          f'{span["deny"]:.1f} mm, yes {span["grant"]:.1f} mm)')
