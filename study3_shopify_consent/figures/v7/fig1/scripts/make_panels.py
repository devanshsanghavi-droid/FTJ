"""Figure 1 panels, v7: the worked example of ../../DESIGN_V7.md (the sciplot skill's clean theme, mmd-ahd/scientific-
figure-skill, re-implemented here and never executed, plus the bake-off grafts from FigGenie and nature-figure). Panel
letters, contents and every number are those of v6; the explaining and every count live in the caption
(scripts/make_caption.py).

Messages (venue: Computers & Security, Elsevier, 190 mm double column):
  figure  consent is lost between the cookie banner and Shopify's sandboxed pixels;
  a       (hero) the CMP's script blocker walls off the page only, while Shopify's consent gate starts pixels in
          sandboxes whose requests leave the browser for the ad vendors underneath the wall (TikZ, fig1a_pipeline.tex;
          nested labelled regions, the five loss numerals of the caption, no data numbers);
  b       (one instance) in one load the blocker stops TikTok's page tag, yet TikTok's sandboxed pixel keeps sending;
  c       (the population) at scale, 205 banner stores' sandboxed pixels sent before any choice, most before the banner.

  b  one re-check load as a two-lane event strip timed from the banner becoming visible: bottom axis only (an event
     strip has no value axis); the two lanes carry very faint pre-mixed grounds that repeat panel a's regions (TINT
     PAGE: the page lane, TINT SAND: the sandbox lane; v7 graft c); the page lane holds panel a's wall in miniature
     where the blocker neutralised TikTok's tag (the tag sent nothing), the sandbox lane one brick tick per request of
     TikTok's sandboxed pixel (short = library load, tall = data beacon, keyed above the axis; requests of one kind
     less than tick_merge_ms apart are drawn side by side, so every request is drawn); the amber rule is the banner
     becoming visible. b's 0 sits exactly above c's 0, on a larger scale, so its axis is visibly inset from c's. The
     one request beyond the axis is the Stealth arrowhead of a's leak arrows at the end of the lane. Direct labels:
     'banner visible' and 'blocked'. Numbers: fig1/derived_numbers.json `fig1b_trace` (derive_fig1.py).
  c  every banner store whose sandboxed pixel sent an ad request before any choice (fig3/b/n), one row each, sorted by
     its first sandboxed ad request relative to the banner becoming visible: one cool-grey tick per request (context),
     the first requests joined by a brick line (the protagonist), the banner as an amber rule at 0, a small open brick
     ring where the line crosses it (the rows above it are the caption's 151 stores), and a pale pre-mixed brick ground
     (TINT LEAK) between the line and the amber rule: the time each of those stores sent before the banner (v7 graft
     d; nature-figure's tinted key region). Where the line leaves the axis it ends in the same arrowhead; 2.5 mm of
     white above row 1 and below row n. One direct label ('first request'). Requests outside the axis are not drawn;
     their counts are in the caption (`fig1c_raster`).

Style: fs.v7_context() (Arial; 7 pt words, 6 pt ticks; the sciplot clean theme: open L-shaped axes, 0.6 pt chrome in
#3d434b, text #1f2328, 2.5 pt outward ticks, data 1.0 pt). LEAK brick = the requests that lost consent, EVENT amber =
the banner, grey = context. Every panel is linted (sp_lint.lint_fig) before it is saved. c's plot area runs P0..P1;
b's axis is placed so that its 0 is c's 0 (c_zero_mm).

Numbers: nothing is printed in the panels except tick labels; every drawn value comes from analysis/outputs/stats.json
or fig1/derived_numbers.json and is registered (fmt 'mark') in fig1_numbers.csv for trace_fig1.py.

Outputs (fig1/panels/): fig1b_trace.pdf, fig1c_raster.pdf; ../fig1_numbers.csv.
Run:  python3 fig1/scripts/make_panels.py   (build.sh runs derive_fig1.py first)
"""
import json
import os
import re
import sys

from contextlib import contextmanager

import matplotlib as mpl
import pandas as pd
from matplotlib.patches import Polygon, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
FIG1 = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG1, '..', 'style')))
import figstyle as fs  # noqa: E402
sys.path.insert(0, HERE)
import sp_lint  # noqa: E402  (sciplot step 5: lint every panel before it is saved)

PANELS = os.path.join(FIG1, 'panels')
os.makedirs(PANELS, exist_ok=True)
DERIVED = json.load(open(os.path.join(FIG1, 'derived_numbers.json')))

# ---- composite grid (mm); must equal fig1.tex (asserted in check_composite) ----
A_W, A_H = 190.0, 44.0          # a: the line drawing (TikZ: \PanelCanvas{190}{44} in fig1a_pipeline.tex)
B_W, B_H = 190.0, 24.0          # b: the two-row event strip
C_W, C_H = 190.0, 52.0          # c: the all-store raster
GUT = fs.GUTTER_MM
FIG_H = A_H + GUT + B_H + GUT + C_H
P0, P1 = 17.0, 186.0            # plot area of c (b's time axis is inset from it, with its 0 above c's 0)
RQ = '’'
LOSS_NUMERALS = (1, 2, 3, 4, 5)  # panel a's outlined numerals = the caption's five points (trace_fig1.py checks both)

assert abs(FIG_H - 132.0) < 1e-9 and 100.0 <= FIG_H <= 150.0     # RESTRAINT rule 9: about 100-150 mm high


# ------------------------------------------------------------------------------------------------ v7 style
SP_LW_DATA = fs.V7_LW['data']   # sciplot: data 1.0 pt in print


def skin():
    """The v7 panel style: fs.v7_context() (style_context() + the sciplot clean theme values fs.V7_RC)."""
    return fs.v7_context()


def check_composite():
    """The cells in fig1.tex must equal the constants above (panels are never rescaled), and the TikZ canvas of a
    must be A_W x A_H."""
    tex = open(os.path.join(FIG1, 'fig1.tex')).read()
    cells = {m[0]: tuple(float(v) for v in m[1:5]) for m in
             re.findall(r'\\Panel\s*\{(\w)\}\s*\{([\d.]+)\}\s*\{([\d.]+)\}\s*\{([\d.]+)\}\s*\{([\d.]+)\}', tex)}
    want = {'a': (0, 0, A_W, A_H), 'b': (0, A_H + GUT, B_W, B_H), 'c': (0, A_H + GUT + B_H + GUT, C_W, C_H)}
    assert cells == want, (cells, want)
    assert re.search(r'\\FigureCanvas\{%g\}' % FIG_H, tex), 'fig1.tex canvas height differs from FIG_H'
    a = open(os.path.join(FIG1, 'fig1a_pipeline.tex')).read()
    assert re.search(r'\\PanelCanvas\{%g\}\{%g\}' % (A_W, A_H), a), 'fig1a_pipeline.tex canvas differs from A_W x A_H'
    code = '\n'.join(re.sub(r'(?<!\\)%.*', '', ln) for ln in a.splitlines())
    texts = [re.sub(r'(\\\\)\[[^\]]*\]', r'\1', t) for t in re.findall(r'\{([^{}]*)\};', code)
             if not re.fullmatch(r'#\d', t)]           # node texts (line-skip lengths dropped; macro parameters out)
    assert not re.search(r'\d', ''.join(texts)), 'panel a prints a number (numbers live in the caption)'
    # v7 graft e: the only digits in a are the five loss numerals, drawn by \lossno in the caption's order 1-5
    nums = re.findall(r'\\lossno\{[^{}]*\}\{([^{}]*)\}', code)
    assert nums == [str(i) for i in LOSS_NUMERALS], f'panel a loss numerals {nums} (must be 1-5, once each, in order)'
    # v7 graft b: the ad-vendor box lists the vendor groups of every figure, in the fixed order (grey, never hues)
    vend = [t for t in texts if 'Google' in t]
    assert len(vend) == 1 and [v.strip() for v in vend[0].split('\\\\')] == fs.VENDOR_ORDER, vend


# ------------------------------------------------------------------------------------------------ numbers
def _dv(key):
    name, _, rest = key.partition('/')
    v = DERIVED[name]['value']
    return fs._walk(v, rest) if rest else v


def DN(key, f='int'):
    """Render a number from figures/v7/fig1/derived_numbers.json ('record/field') and register it (caption)."""
    v = _dv(key)
    s = fs.render(v, f)
    fs._REG.append(dict(text=s, shown=fs.typo(s), source='fig1_derived', key=key, fmt=f, value=json.dumps(v)))
    return fs.typo(s)


def SEC(key, f='f1'):
    """A time stored in ms (fig1 derived) shown in seconds; registered with fmt '<f>/1000'."""
    v = _dv(key)
    s = fs.render(v / 1000.0, f)
    fs._REG.append(dict(text=s, shown=fs.typo(s), source='fig1_derived', key=key, fmt=f + '/1000', value=json.dumps(v)))
    return fs.typo(s)


def mark(key):
    """Register a derived value that is drawn but not printed (event times, request times)."""
    v = _dv(key)
    fs._REG.append(dict(text='', shown='', source='fig1_derived', key=key, fmt='mark', value=json.dumps(v)))
    return v


def mark_stat(key):
    """Register a stats.json value that is drawn but not printed."""
    v = fs.stat(key)
    fs._REG.append(dict(text='', shown='', source='stats', key=key, fmt='mark', value=json.dumps(v)))
    return v


def ext_mm(fig, t):
    """(x0, x1) of a text's extent in panel mm."""
    fig.canvas.draw()
    bb = t.get_window_extent(fig.canvas.get_renderer())
    px = fig.dpi / 25.4
    return bb.x0 / px, bb.x1 / px


# ------------------------------------------------------------------------------------------------ shared marks
HEAD_L_MM, HEAD_W_MM = 1.5, 1.2     # 'leaves the axis' arrowhead (b: the late beacon; c: the first-request line): the
HEAD_INSET_MM_BACK = 0.42           # Stealth head of panel a's leak arrows (4.25 x 3.4 bp, inset 1.2 bp), same shape
HEAD_INSET_MM = 0.35                # its tip stops this far inside the plot area


def edge_head(ax, x_tip, y, direction):
    """A filled LEAK Stealth arrowhead (the head of panel a's leak arrows) whose tip is at (x_tip, y) in data
    coordinates, pointing 'left' or 'right': the mark for 'continues beyond the axis', always drawn inside the plot
    area. Call after the limits are final. Returns the data x of its base (where a line running into it should stop)."""
    tr = ax.transData
    px = ax.figure.dpi / 25.4
    tx, ty = tr.transform((x_tip, y))
    s = 1 if direction == 'right' else -1
    L, Wd, ins = HEAD_L_MM * px, HEAD_W_MM * px, HEAD_INSET_MM_BACK * px
    pts = [(tx, ty), (tx - s * L, ty + Wd / 2), (tx - s * (L - ins), ty), (tx - s * L, ty - Wd / 2)]
    ax.add_patch(Polygon(tr.inverted().transform(pts), closed=True, facecolor=fs.LEAK, edgecolor='none', zorder=5,
                         clip_on=False))
    return tr.inverted().transform((tx - s * (L - ins) * 0.9, ty))[0]


def wall_bar(ax, x, y0, y1, w_mm, color=None, zorder=4):
    """A slim solid bar centred on data x from y0 to y1 (data), w_mm wide: panel a's script-blocker wall, drawn at the
    scale of a mark. Built in data coordinates (so it survives the PDF's 72 dpi). Call after the limits are final."""
    tr = ax.transData
    px = ax.figure.dpi / 25.4
    xa = tr.transform((x, y0))[0]
    xl = tr.inverted().transform((xa - w_mm * px / 2, 0))[0]
    xr = tr.inverted().transform((xa + w_mm * px / 2, 0))[0]
    p = Rectangle((xl, min(y0, y1)), xr - xl, abs(y1 - y0), facecolor=color or fs.SP_FG, edgecolor='none',
                  zorder=zorder)
    ax.add_patch(p)
    return p


# ------------------------------------------------------------------------------------------------ panel b
REQ_LW = 1.2                        # request ticks (pt): brick, short = library load, tall = data beacon, both centred on
TICK_TALL_MM, TICK_SHORT_MM = 3.6, 1.8   # the row (the 'blocked' bar in the page row is panel a's wall at mark size)
SIDE_MM = 0.85                      # requests of one kind < tick_merge_ms apart: drawn side by side, 0.85 mm apart
BLOCK_W_MM = 0.8                    # the 'blocked' bar: a slim solid bar, panel a's script-blocker wall in miniature
LANE_H_MM = 3.8                     # each lane's ground (v7 graft c): 3.8 mm of the 4 mm row pitch, 0.2 mm of white
                                    # between the lanes; the tall 3.6 mm beacon ticks fit inside their lane
LANE_GROUND = {'page': fs.TINT['PAGE'], 'sandbox': fs.TINT['SAND']}   # = panel a's two region grounds
# b is re-based to the banner (time 0 = the banner becoming visible) and its 0 sits exactly above c's 0, so the two
# amber rules form one vertical. b runs on its own, larger scale (one load spans about 1 s; c spans 12 s), so its axis
# is visibly inset from c's on both sides and it keeps its own tick labels and axis title.
B_XLO, B_XHI = -0.3, 2.2            # s from the banner
B_MM_PER_S = 48.0
B_TICKS = [0, 0.5, 1, 1.5, 2]
B_TICKLABELS = ['0', '+0.5', '+1', '+1.5', '+2']
T_AXIS_TITLE = 'Time from banner visible (s)'      # b and c


def c_zero_mm():
    """x (panel mm) of c's time 0: c's plot area runs P0..P1 over fig1c_raster x_lo_s..x_hi_s."""
    lo, hi = _dv('fig1c_raster/x_lo_s'), _dv('fig1c_raster/x_hi_s')
    return P0 + (0 - lo) / (hi - lo) * (P1 - P0)


def panel_b():
    """One re-check load as a two-row event strip, timed from the banner becoming visible (sciplot clean: bottom axis
    only, hairline row guides, direct labels, one small key)."""
    c = 'fig1b_trace'
    fig = fs.panel(B_W, B_H)
    z = c_zero_mm()
    BX0, BX1 = z + B_XLO * B_MM_PER_S, z + B_XHI * B_MM_PER_S
    assert BX0 >= P0 + 25 and BX1 <= P1 - 5, 'b: axis must be visibly inset from c (they do not share a scale)'
    TOP, HGT = 6.0, 10.0                          # plot area (mm from the panel top)
    ax = fs.axes_mm(fig, BX0, TOP, BX1 - BX0, HGT)
    ax.set_xlim(B_XLO, B_XHI)
    ax.set_xticks(B_TICKS)
    ax.set_xticklabels(B_TICKLABELS)
    ax.set_xlabel(T_AXIS_TITLE)
    Y_PAGE, Y_SBX = 1.0, 0.0
    ax.set_ylim(-0.75, 1.75)
    mm_per_y = HGT / 2.5                          # 4 mm between the rows
    ax.spines['left'].set_visible(False)          # an event strip has no value axis: rows are named, not measured
    V = _dv(c + '/vendor_label')
    assert V == 'TikTok' and _dv(c + '/sandbox_origins') == ['lax_iframe']
    ax.set_yticks([Y_SBX, Y_PAGE])
    ax.set_yticklabels([f'{V} pixel (sandbox)', f'{V} tag (page)'], fontsize=fs.FS['cat'], color=fs.SP_FG)
    ax.tick_params(axis='y', length=0, pad=3.0)
    # v7 graft c: the two lanes get very faint pre-mixed grounds that repeat panel a's regions (the page, the pixel
    # sandboxes), across the whole axis span, square, no outline; they replace v6's hairline row guides
    lane_half = LANE_H_MM / 2 / mm_per_y
    assert TICK_TALL_MM <= LANE_H_MM <= mm_per_y * 1.0 - 0.15
    for yr, kind in ((Y_PAGE, 'page'), (Y_SBX, 'sandbox')):
        ax.add_patch(Rectangle((B_XLO, yr - lane_half), B_XHI - B_XLO, 2 * lane_half, facecolor=LANE_GROUND[kind],
                               edgecolor='none', zorder=0.5))

    tb_ms = mark(c + '/t_banner_ms')
    rel = lambda t_ms: (t_ms - tb_ms) / 1000.0    # noqa: E731  (s from the banner)
    # the banner becoming visible: amber rule at 0 (exactly above c's), its name above the axis (text never amber)
    fs.event_line(ax, 0.0, zorder=2)
    lab_banner = fs.text_mm(fig, z, TOP - 1.4, 'banner visible', ha='center', color=fs.SP_FG)

    # page row: the blocker neutralised the tag as it was inserted -- panel a's wall in miniature; the tag sent nothing
    tt = rel(mark(c + '/t_tag_neutralized_ms'))
    assert _dv(c + '/n_page_requests') == 0 and _dv(c + '/neutralized_type') == ['javascript/blocked']
    half = TICK_TALL_MM / 2 / mm_per_y
    wall_bar(ax, tt, Y_PAGE - half, Y_PAGE + half, BLOCK_W_MM)
    lab_blocked = fs.direct_label(ax, tt + 1.3 / B_MM_PER_S, Y_PAGE, 'blocked', va='center_baseline',
                                  color=fs.SP_FG)

    # sandbox row: one brick tick per request, centred on the row (short = library load, tall = data beacon); requests
    # of one kind less than tick_merge_ms apart are drawn side by side SIDE_MM apart around their mean time
    reqs = mark(c + '/requests')
    groups = _dv(c + '/tick_groups')
    axis_ms = _dv(c + '/axis_ms')
    lo_ms, hi_ms = tb_ms + B_XLO * 1000, tb_ms + B_XHI * 1000
    within = [q for q in reqs if lo_ms <= q['t_ms'] <= hi_ms]
    # the re-based axis keeps exactly the requests of the paper-wide 0-6 s window, so the caption's counts still hold
    assert within == [q for q in reqs if q['t_ms'] <= axis_ms]
    assert sum(g['n'] for g in groups) == _dv(c + '/n_within_axis') == len(within)
    spans = []
    for g in groups:
        members = [q for q in reqs if g['t_ms_first'] <= q['t_ms'] <= g['t_ms_last']]
        assert len(members) == g['n'] and all(q['kind'] == g['kind'] for q in members)
        assert g['t_ms_last'] - g['t_ms_first'] < _dv(c + '/tick_merge_ms')
        h = (TICK_TALL_MM if g['kind'] == 'beacon' else TICK_SHORT_MM) / mm_per_y
        mid = rel(sum(q['t_ms'] for q in members) / len(members))
        xs = [mid + (i - (g['n'] - 1) / 2) * SIDE_MM / B_MM_PER_S for i in range(g['n'])]
        for x in xs:
            ax.plot([x, x], [Y_SBX - h / 2, Y_SBX + h / 2], color=fs.LEAK, lw=REQ_LW, solid_capstyle='butt', zorder=5)
        spans.append((min(xs), max(xs)))
    tick_w_mm = REQ_LW / fs.PT_PER_MM
    assert SIDE_MM - tick_w_mm >= 0.4, 'b: side-by-side ticks need >= 0.4 mm of white between them'
    for (a0, a1), (b0, b1) in zip(spans, spans[1:]):     # neighbouring groups stay clearly apart (>= 2 mm)
        assert (b0 - a1) * B_MM_PER_S >= 2.0
    assert _dv(c + '/n_beacons_within_axis') == sum(g['n'] for g in groups if g['kind'] == 'beacon')
    assert _dv(c + '/n_libraries_within_axis') == sum(g['n'] for g in groups if g['kind'] == 'library')
    # the request beyond the axis: a brick arrowhead at the right end of the sandbox row (its time in the caption)
    beyond = mark(c + '/beyond_axis_ms')
    assert len(beyond) == _dv(c + '/n_beyond_axis') == 1 and min(beyond) > hi_ms
    assert _dv(c + '/beyond_axis_kinds') == ['beacon']
    edge_head(ax, B_XHI - HEAD_INSET_MM / B_MM_PER_S, Y_SBX, 'right')
    assert (B_XHI - HEAD_INSET_MM / B_MM_PER_S - HEAD_L_MM / B_MM_PER_S - spans[-1][1]) * B_MM_PER_S >= 5.0

    # one small key (sciplot: frameless, ordered like the data): what the two tick heights mean, right of the label
    # 'banner visible', on its baseline; muted text, marks in the data colour
    kx, ky = BX1 - 1.0, TOP - 1.4                 # right end, baseline (mm)
    keys = [('data beacon', TICK_TALL_MM), ('library load', TICK_SHORT_MM)]
    cap = fs.FS['legend'] * fs.CAP_EM / fs.PT_PER_MM
    for name, hmm in keys:                        # laid out right to left
        t = fs.text_mm(fig, kx, ky, name, ha='right', color=fs.SP_MUTED, size=fs.FS['legend'])
        x0, _ = ext_mm(fig, t)
        xm = x0 - 1.4
        yc = ky - cap / 2
        fx, fy0 = fs.fig_xy(fig, xm, yc - hmm / 2)
        _, fy1 = fs.fig_xy(fig, xm, yc + hmm / 2)
        fig.add_artist(mpl.lines.Line2D([fx, fx], [fy0, fy1], color=fs.LEAK, lw=REQ_LW, solid_capstyle='butt',
                                        transform=fig.transFigure))
        kx = xm - 3.2
    k0 = kx + 3.2 - 1.4

    # geometry guards: the direct labels and the key stay inside the axis span and clear of each other
    bx0, bx1 = ext_mm(fig, lab_banner)
    assert bx0 >= BX0 + 1.0, "b: 'banner visible' runs past the axis's left edge"
    assert k0 - bx1 >= 10.0, "b: the key runs into 'banner visible'"
    x0, x1 = ext_mm(fig, lab_blocked)
    assert x1 <= BX1 - 1.0
    assert not sp_lint.lint_fig(fig, 'fig1b_trace'), 'sciplot lint: fix or justify every warning'
    fs.save_panel(fig, os.path.join(PANELS, 'fig1b_trace.pdf'))


# ------------------------------------------------------------------------------------------------ panel c
def _stores():
    sys.path.insert(0, os.path.join(fs.STUDY, 'analysis'))
    from common import CONTENT_EXCLUDED
    st = pd.read_csv(os.path.join(fs.AOUT, 'store_table.csv'))
    return st[(st.stratum == 'main') & (~st.store_id.isin(CONTENT_EXCLUDED))]


Y_TICKS_C = [1, 50, 100, 150, 200]
C_AIR_MM = 2.5                      # white above row 1 and below row n: the brick line never runs along an axis end
C_RING_MS = 3.5                     # the crossing ring (sciplot: markers ~3.5 pt)
C_LINE_LW = 1.2                     # the first-request line: sciplot's 1.0 pt data stroke, +0.2 pt so the one accent
                                    # stays the strongest mark over 3,233 grey ticks


def panel_c():
    """Every banner store whose sandboxed pixel sent an ad request before any choice (fig3/b/n), one row each, sorted by
    the time of its first sandboxed ad request relative to the banner becoming visible."""
    R = 'fig1c_raster'
    m = _stores()
    g = m[(m.banner_A0 == True) & (m.A0_sbx == True)].set_index('store_id')    # noqa: E712
    nb = fs.stat('fig3/b/before_banner')
    assert len(g) == fs.stat('fig3/b/n') == nb['n'] == _dv(R + '/n_stores')
    mark_stat('fig3/b/n')
    r = pd.read_csv(os.path.join(fs.AOUT, 'ad_requests.csv.gz'), low_memory=False,
                    usecols=['store_id', 'arm', 'sandbox', 'ad', 't_ms'])
    q = r[(r.arm == 'A0') & r.store_id.isin(g.index) & (r.sandbox == True) & (r.ad == True)].copy()   # noqa: E712
    assert q.groupby('store_id').t_ms.min().sub(g.A0_first_sbx_t).abs().max() == 0
    assert len(q) == _dv(R + '/n_requests')
    q['rel'] = (q.t_ms - q.store_id.map(g.t_banner_A0)) / 1000.0
    lead = (g.A0_first_sbx_t - g.t_banner_A0) / 1000.0
    order = lead.sort_values(kind='mergesort').index.tolist()
    assert int((lead < 0).sum()) == nb['k']
    mark_stat('fig3/b/before_banner/k')
    row = {s: i + 1 for i, s in enumerate(order)}          # rows 1..n, top to bottom
    q['y'] = q.store_id.map(row)
    XL, XR = mark(R + '/x_lo_s'), mark(R + '/x_hi_s')
    n_left, n_right = int((q.rel < XL).sum()), int((q.rel > XR).sum())
    assert n_left == _dv(R + '/n_requests_left') and n_right == _dv(R + '/n_requests_right')
    assert len(q) - n_left - n_right == _dv(R + '/n_requests_within')
    lv = lead.loc[order].values
    nL, nR = int((lv < XL).sum()), int((lv > XR).sum())
    assert nL == _dv(R + '/n_first_left') and nR == _dv(R + '/n_first_right') and nL > 0 and nR > 0

    fig = fs.panel(C_W, C_H)
    TOP, HGT = 2.0, 40.0
    ax = fs.axes_mm(fig, P0, TOP, P1 - P0, HGT)
    n = len(order)
    ax.set_xlim(XL, XR)
    AIR = C_AIR_MM * n / (HGT - 2 * C_AIR_MM)   # rows of white at each end
    ax.set_ylim(n + 0.5 + AIR, 0.5 - AIR)
    fs.signed_ticks(ax, [-4, -2, 0, 2, 4, 6, 8], 'x')
    ax.set_xlabel(T_AXIS_TITLE)
    ax.set_yticks(Y_TICKS_C)
    ax.set_yticklabels([str(v) for v in Y_TICKS_C])
    assert max(Y_TICKS_C) <= n
    ax.set_ylabel('Banner stores')
    mm_x = (XR - XL) / (P1 - P0)                 # s per mm
    mm_y = (n + 2 * AIR) / HGT                   # rows per mm
    assert abs(c_zero_mm() - (P0 + (0 - XL) / mm_x)) < 1e-9

    # context: one grey tick per sandboxed ad request on the axis (the requests outside it are counted in the caption)
    qq = q[(q.rel >= XL) & (q.rel <= XR)]
    # (sciplot: grey for context, colour for signal; the theme's cool context grey; 3,233 ticks < the skill's 5,000-
    # point rasterisation threshold, so the panel stays fully vector)
    assert len(qq) == _dv(R + '/n_requests_within') < 5000
    ax.plot(qq.rel, qq.y, ls='none', marker='|', ms=1.4, mew=0.5, color=fs.SP_CONTEXT, zorder=2)
    # the banner moment: amber rule at 0
    fs.event_line(ax, 0.0, zorder=2.5)
    # the protagonist: each store's first request, joined top to bottom (brick). Where the line leaves the axis (the
    # nL stores whose first request came earlier, the nR later) it ends in the arrowhead used in b, inside the frame.
    ys = [row[s] for s in order]
    i0, i1 = nL, n - nR                          # rows i0+1 .. i1 lie on the axis
    yL = ys[i0 - 1] + (XL - lv[i0 - 1]) / (lv[i0] - lv[i0 - 1])          # where the line crosses the left frame
    yR = ys[i1 - 1] + (XR - lv[i1 - 1]) / (lv[i1] - lv[i1 - 1])          # ... and the right frame
    xbL = edge_head(ax, XL + HEAD_INSET_MM * mm_x, yL, 'left')
    xbR = edge_head(ax, XR - HEAD_INSET_MM * mm_x, yR, 'right')
    yb = lambda x, j: ys[j - 1] + (x - lv[j - 1]) / (lv[j] - lv[j - 1])   # noqa: E731  (on the segment j-1 -> j)
    assert lv[i0 - 1] < xbL < lv[i0] and lv[i1 - 1] < xbR < lv[i1]
    lx = [xbL] + list(lv[i0:i1]) + [xbR]
    ly = [yb(xbL, i0)] + ys[i0:i1] + [yb(xbR, i1)]
    ax.plot(lx, ly, color=fs.LEAK, lw=C_LINE_LW, solid_joinstyle='round', solid_capstyle='butt', zorder=3)
    # where the line crosses the amber rule: the last store whose first request came before the banner (row k of n);
    # the rows above it are the k stores of the caption. A small open brick ring marks the crossing (drawn, not printed)
    k = nb['k']
    assert lv[k - 1] < 0 <= lv[k]
    y_cross = ys[k - 1] + (0 - lv[k - 1]) / (lv[k] - lv[k - 1])
    ax.plot([0], [y_cross], ls='none', marker='o', ms=C_RING_MS, mfc=fs.SURFACE, mec=fs.LEAK, mew=C_LINE_LW,
            zorder=4)
    # v7 graft d: a pale pre-mixed brick ground (TINT LEAK, never alpha) between the first-request line and the amber
    # rule for the k rows whose first request came before the banner -- the 'before the banner' area. It follows the
    # drawn line exactly (the same vertices), starts at the left frame for the nL rows whose first request lies left of
    # the axis, runs from the top of row 1 (the 2.5 mm of air above it stays white) and sits under every mark.
    assert i0 < k
    poly = ([(XL, 0.5), (XL, yL)] + [(lv[j], ys[j]) for j in range(i0, k)] + [(0.0, y_cross), (0.0, 0.5)])
    assert all(x <= 0 for x, _ in poly) and all(XL <= x for x, _ in poly)
    ax.add_patch(Polygon(poly, closed=True, facecolor=fs.TINT['LEAK'], edgecolor='none', zorder=1.2))
    # the line stays clear of both ends of the row axis (>= 2 mm of white, line half-width included)
    half_lw_rows = C_LINE_LW / fs.PT_PER_MM / 2 * mm_y
    assert (min(ly) - half_lw_rows - (0.5 - AIR)) / mm_y >= 2.0
    assert ((n + 0.5 + AIR) - max(ly) - half_lw_rows) / mm_y >= 2.0

    # one direct label for the line, in the empty area left of it: its right end 1 mm left of the band's earliest
    # first request (rows are sorted by lead, so no request of a row lies left of that row's first request)
    band = int(round(3.0 * mm_y))
    r0 = 120                                     # band top row (1-based)
    x_end = lv[r0 - 1] - 1.0 * mm_x
    y_lab = r0 + band / 2
    t = fs.direct_label(ax, x_end, y_lab, 'first request', ha='right', va='center', color=fs.SP_FG)
    x0, _ = ext_mm(fig, t)
    assert x0 >= P0 + 1.0, 'c: first-request label leaves the plot area'
    band_rows = set(range(r0 - 1, r0 + band + 2))
    assert not (q.y.isin(band_rows) & (q.rel <= x_end) & (q.rel >= XL)).any(), 'c: label covers ticks'
    r_lab = int(round(y_lab))
    gap_mm = (lv[r_lab - 1] - x_end) / mm_x
    if gap_mm > fs.LEADER_MIN_MM:
        fs.leader(ax, (lv[r_lab - 1] - 0.35 * mm_x, r_lab), (x_end + 0.4 * mm_x, y_lab))
    assert not sp_lint.lint_fig(fig, 'fig1c_raster'), 'sciplot lint: fix or justify every warning'
    fs.save_panel(fig, os.path.join(PANELS, 'fig1c_raster.pdf'))


if __name__ == '__main__':
    check_composite()
    fs.reset_registry()
    with skin():
        panel_b()
        panel_c()
    fs.write_registry(os.path.join(FIG1, 'fig1_numbers.csv'))
    print(f'wrote panels and fig1_numbers.csv (a {A_W:g} x {A_H:g} [TikZ], b {B_W:g} x {B_H:g}, c {C_W:g} x {C_H:g} '
          f'mm; figure 190 x {FIG_H:g} mm)')
