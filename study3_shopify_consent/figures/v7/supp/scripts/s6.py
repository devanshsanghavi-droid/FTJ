"""Supplementary Figure S6 (v7) -- before any choice, ad pixels of every vendor group fired from Shopify's sandboxes, and
most first sandboxed requests came before the banner was visible.

Binding: figures/v7/DESIGN_V7.md (the sciplot clean theme plus the bake-off grafts; worked example figures/v7/fig1).
Drawn inside fs.v7_context(): open L axes (0.6 pt, #3d434b), Arial 7 pt words / 6 pt ticks, data lines 1.0 pt,
markers 3.5 pt, uncapped 0.75 pt 95% intervals, no gridlines, no panel titles, no numbers in the plots (tick labels
only; every number is in the caption, make_captions.py). Grey for context, colour for signal, and one meaning per hue
in the figure: LEAK brick = consent lost (b: the first sandboxed requests; d: the region default that allows them,
Fig 3a's pair), HONOUR slate = the comparison (d: denied until consent), EVENT amber = the banner becoming visible, SAND
dark slate = the Shopify sandbox as a category in bars (c; the registry token of DESIGN_V7 3.2 and 8.7, figstyle.SAND,
Fig 1a's sandbox outline). The banner contrast of a and e is not a consent contrast, so it takes no hue: banner shown =
ink (SP_FG) circle, no banner = grey (NEUTRAL) square. One pre-mixed tint (never alpha): TINT LEAK, the key area of the
hero b (stores whose first sandboxed request came before the banner).

Figure contract (DESIGN_V7 section 1): one claim -- before any choice, every vendor group's sandboxed pixel fired and in
most banner stores the first sandboxed request came before the banner was visible.
  a  the population, by vendor: ad pixel fired, banner shown (ink circle) vs no banner (grey square), Wilson 95% CIs
     in the colour of the mark; 'Any vendor' set apart below and labelled directly.                    stats fig3/a
  b  (hero; the instance in time) the same banner stores' first sandboxed ad request, timed from the banner becoming
     visible (the axis of Fig 1b, c): cumulative share of the fig3/b/n stores (brick step line); amber rule = banner
     visible (named), a solid LIGHT hairline = one polling interval earlier (named; no dashes or dots in a data panel,
     DESIGN_V7 4); a pale brick ground (TINT LEAK) under the
     curve before the banner (the key area: the stores that sent before the banner), the open crossing ring where the
     curve meets the amber rule (fig3/b/before_banner) and a dot where it meets the hairline
     (fig3/b/before_banner_by_poll); where the curve leaves the axis it ends in Fig 1's leak arrowhead (the stores
     beyond the axis are counted in the caption).          analysis/outputs/fig3b.csv; stats fig3/b, design
  c  the mechanism's footprint: origin of every ad request in the Default load, by vendor group: thin stacked 100% bars
     in tier order -- Shopify sandbox SAND, Shopify's open pixel mid grey #6e6e6e, page scripts LIGHT -- with thin white
     gaps; 'relay' (Google's only) is narrower than a gap and not drawn (asserted; caption).          stats fig3/c
  d  the comparison: banner stores on which any ad pixel fired within five consent products, by Shopify's region
     default ('allowed until choice' brick circle, 'denied until consent' slate square), Wilson CIs; a group of fewer
     than design/min_stores_row (10) stores is drawn grey, and a product whose groups are both that small is named in
     muted grey.                                                   stats fig3/d/mh_by_product/by_product
  e  the robustness of the count: sandboxed ad requests per store before any choice (Default load): share of stores
     with >= n requests (log n), banner shown (ink) vs no banner (grey); the marks at n = 1 are fig1b/banner_fires
     and fig1b/nobanner_fires.                              analysis/outputs/store_table.csv; stats fig1b
Keys (sciplot: frameless, ordered like the data, muted 7 pt) sit in one band above the plots of row 2; a and b are
labelled directly (at most two short labels each).

Layout (mm; must equal figS6.tex, asserted in check_composite): row 1 a | b (W_A, W_B x H1; b the hero); row 2
c | d | e (W_C, W_D, W_E x H2); 6 mm gutters; the plots of a row share their top and x-axis line (asserted).
Every drawn value read from stats.json is registered (fmt 'raw', shown '') in panels/figS6_numbers.csv, so
trace_supp.py re-renders it from the current stats.json; curves drawn from analysis tables are asserted against the
registered shares. Nothing but tick labels is printed as a number.

The helpers in the 'shared v7 helpers' section are also imported by s7.py ... s10.py.
"""
import json
import os
import re

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon, Rectangle

from supp_common import CMP_NAME, SUPP, fs, finish, table, write_registry

LQ, RQ = '‘', '’'


# ================================================================================================ shared v7 helpers
# ---- v7 marks (DESIGN_V7 sections 4-5): markers 3.5 pt with a 0.6 pt edge (open markers: white, 0.8 pt edge in the
#      token); the arm shapes of colors.ARM scaled by 3.5 / 4.5 (Default circle 3.5 pt), drawn in the sciplot neutrals
MS7 = fs.V7_LW['marker']                 # 3.5 pt
MEW7, MEW7_OPEN = fs.V7_LW['mew'], 0.8   # edge of a filled / an open marker (pt)
LW_DATA = fs.V7_LW['data']               # 1.0 pt data lines
LW_CI = fs.LW['error']                   # 0.75 pt uncapped intervals
LW_EVENT = fs.LW['event']                # 0.75 pt event rules
K_ARM = MS7 / fs.ARM['Default']['ms']    # v6 arm sizes -> v7
INK7 = fs.SP_FG                          # the v7 near-black (text, the Default arm)
TICK_GREY = '#6e6e6e'                    # the mid grey of the stacked-bar tiers (= fs.ORIGIN['open_pixel'])
assert fs.ORIGIN['open_pixel']['facecolor'].lower() == TICK_GREY


def sstyle(i, filled=True, color=None):
    """The i-th compared series (0 LEAK circle, 1 HONOUR square, 2 THIRD diamond) at the v7 marker size; open variant
    white with a 0.8 pt edge."""
    c = color or fs.SERIES[i]
    m = fs.SERIES_MARKER[i]
    ms = MS7 * (0.95 if m == 's' else (0.85 if m == 'D' else 1.0))
    return dict(ls='none', marker=m, ms=ms, mfc=c if filled else fs.SURFACE, mec=c,
                mew=MEW7 if filled else MEW7_OPEN, color=c)


def astyle(arm, color=None):
    """A load's marker (colors.ARM shapes: Default filled circle, Decline open square, GPC filled triangle, Repeat open
    diamond) at the v7 size, in the sciplot neutrals (INK -> SP_FG); `color` recolours it (open markers stay white)."""
    st = dict(fs.marker_style(arm))
    st = {k: (INK7 if isinstance(v, str) and v.lower() == fs.INK else v) for k, v in st.items()}
    st['ms'] = st['ms'] * K_ARM
    is_open = str(st['mfc']).lower() == fs.SURFACE
    st['mew'] = MEW7_OPEN if is_open else MEW7
    if color is not None:
        st['mec'] = color
        st['mfc'] = fs.SURFACE if is_open else color
        st['color'] = color
    st['ls'] = 'none'
    return st


def mark(key):
    """A stats.json value that is DRAWN (dot, CI end, bar end), registered so trace_supp.py re-renders it from the
    current stats.json (fmt 'raw'; nothing is printed, so 'shown' is empty)."""
    v = fs.stat(key)
    fs._REG.append(dict(text=fs.render(v, 'raw'), shown='', source='stats', key=key, fmt='raw', value=json.dumps(v)))
    return v


def mark_d(key):
    """A figures/v7/derived_numbers.json value that is drawn (registered as mark())."""
    v = fs.derived(key)
    fs._REG.append(dict(text=fs.render(v, 'raw'), shown='', source='derived', key=key, fmt='raw', value=json.dumps(v)))
    return v


def mark_sd(key):
    """A supp derived_numbers.json value that is drawn (registered as mark())."""
    d = json.load(open(os.path.join(SUPP, 'derived_numbers.json')))
    name, _, rest = key.partition('/')
    v = fs._walk(d[name]['value'], rest) if rest else d[name]['value']
    fs._REG.append(dict(text=fs.render(v, 'raw'), shown='', source='supp_derived', key=key, fmt='raw',
                        value=json.dumps(v)))
    return v


def share(key, lo='lo', hi='hi'):
    """A {p, lo, hi} share record in percentage units, each value registered as drawn."""
    return tuple(100 * mark(f'{key}/{f}') for f in ('p', lo, hi))


def tw_mm(s, size=None, weight='normal'):
    """Rendered width (mm) of an Arial string (widest line) at `size` pt."""
    f = fs.panel(80, 20)
    t = f.text(0, 0.5, s, fontsize=size or fs.FS['label'], fontweight=weight)
    f.canvas.draw()
    w = t.get_window_extent(f.canvas.get_renderer()).width / f.dpi * 25.4
    fs.plt.close(f)
    return w


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


def no_digits(fig, name, allowed=()):
    """No numbers inside a data panel except tick labels (and the listed strings)."""
    ticks = set()
    for ax in fig.axes:
        ticks |= {id(t) for t in ax.get_xticklabels() + ax.get_yticklabels()}
    for t in fs._texts(fig):
        if id(t) not in ticks and re.search(r'\d', t.get_text()) and t.get_text() not in allowed:
            raise AssertionError(f'{name}: number printed in the plot: {t.get_text()!r} (numbers go to the caption)')


def within(fig, ax, name, x_min=0.8):
    """The plot and all its labels end inside the panel."""
    W, H = fs.size_mm(fig)
    x0, x1, t, b = bb_mm(fig, ax)
    assert x0 >= x_min and x1 <= W - 0.3 and b <= H - 0.3, f'{name}: leaves the panel ({x0:.2f}, {x1:.2f}, {b:.2f})'
    return x0, x1, t, b


def wilson(k, n, z=1.959963984540054):
    """Wilson score 95% interval of k / n (drawn only; the caption carries k and n)."""
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def ci_h(ax, y, lo, hi, color, zorder=3):
    """A horizontal 95% CI (0.75 pt, uncapped) in the colour of its mark."""
    ax.plot([lo, hi], [y, y], color=color, lw=LW_CI, solid_capstyle='butt', zorder=zorder, clip_on=False)


def ci_v(ax, x, lo, hi, color, zorder=3):
    ax.plot([x, x], [lo, hi], color=color, lw=LW_CI, solid_capstyle='butt', zorder=zorder, clip_on=False)


def dot(ax, x, y, st, zorder=4):
    ax.plot([x], [y], ls='none', marker=st['marker'], ms=st['ms'], mfc=st['mfc'], mec=st['mec'], mew=st['mew'],
            zorder=zorder, clip_on=False)


def recolor(st, color):
    """A marker style drawn in another colour (open markers keep their white fill)."""
    s = dict(st)
    s['mec'] = color
    s['mfc'] = fs.SURFACE if str(st['mfc']).lower() == fs.SURFACE else color
    s['color'] = color
    return s


def handle(st, line=None):
    """Key handle: the plotted marker at its plotted size (optionally on a line of the given colour)."""
    if line is None:
        return Line2D([], [], ls='none', marker=st['marker'], ms=st['ms'], mfc=st['mfc'], mec=st['mec'], mew=st['mew'])
    return Line2D([], [], color=line, lw=LW_DATA, marker=st['marker'], ms=st['ms'], mfc=st['mfc'],
                  mec=st['mec'], mew=st['mew'])


def legend_in(ax, handles, labels, loc='upper right', **kw):
    """A small key inside the plot (sciplot: frameless, ordered like the data, muted 7 pt; marks in the data colour)."""
    opts = dict(loc=loc, frameon=False, markerscale=1.0, fontsize=fs.FS['legend'], handlelength=0.9,
                handletextpad=0.5, labelspacing=0.4, borderaxespad=0.4, borderpad=0.2, labelcolor=fs.SP_MUTED)
    opts.update(kw)
    return fs.legend(ax, handles, labels, **opts)


def legend_top_right(ax, handles, labels, **kw):
    return legend_in(ax, handles, labels, loc='upper right', **kw)


def legend_clear(fig, lg, ax, pts, name, pad_mm=0.6):
    """The key's box stays clear of every listed data point / interval end (data coordinates of ax)."""
    fig.canvas.draw()
    px = fig.dpi / 25.4
    b = lg.get_window_extent(fig.canvas.get_renderer())
    for (x, y) in pts:
        X, Y = ax.transData.transform((x, y))
        inside = b.x0 - pad_mm * px < X < b.x1 + pad_mm * px and b.y0 - pad_mm * px < Y < b.y1 + pad_mm * px
        assert not inside, f'{name}: the key covers a mark or interval at {(x, y)}'


# ---- keys above a plot (the band of a panel row): drawn by hand, right to left, like Fig 1b's tick-height key
def _key_glyph(fig, kind, spec, xm, yc):
    """Draw one key glyph centred at (xm, yc) panel mm. kind: 'marker' (a marker style), 'square' (a fill colour),
    'tick' ((colour, height mm, lw pt)), 'rule' ((colour, lw pt, linestyle)), 'line' ((marker style, line colour))."""
    if kind == 'marker':
        fx, fy = fs.fig_xy(fig, xm, yc)
        fig.add_artist(Line2D([fx], [fy], ls='none', marker=spec['marker'], ms=spec['ms'], mfc=spec['mfc'],
                              mec=spec['mec'], mew=spec['mew'], transform=fig.transFigure))
        return 0.0
    if kind == 'line':
        st, col = spec
        x0, y0 = fs.fig_xy(fig, xm - 1.9, yc)
        x1, _ = fs.fig_xy(fig, xm + 1.9, yc)
        fig.add_artist(Line2D([x0, x1], [y0, y0], color=col, lw=LW_DATA, solid_capstyle='butt',
                              transform=fig.transFigure))
        fx, fy = fs.fig_xy(fig, xm, yc)
        fig.add_artist(Line2D([fx], [fy], ls='none', marker=st['marker'], ms=st['ms'], mfc=st['mfc'], mec=st['mec'],
                              mew=st['mew'], transform=fig.transFigure))
        return 1.9
    if kind == 'square':
        s = 2.2
        x0, y0 = fs.fig_xy(fig, xm - s / 2, yc + s / 2)
        W, H = fs.size_mm(fig)
        fig.add_artist(Rectangle((x0, y0), s / W, s / H, facecolor=spec, edgecolor='none', transform=fig.transFigure))
        return s / 2
    if kind == 'tick':
        col, h, lw = spec
        fx, fy0 = fs.fig_xy(fig, xm, yc - h / 2)
        _, fy1 = fs.fig_xy(fig, xm, yc + h / 2)
        fig.add_artist(Line2D([fx, fx], [fy0, fy1], color=col, lw=lw, solid_capstyle='butt',
                              transform=fig.transFigure))
        return 0.0
    if kind == 'rule':
        col, lw, ls = spec
        fx, fy0 = fs.fig_xy(fig, xm, yc - 1.4)
        _, fy1 = fs.fig_xy(fig, xm, yc + 1.4)
        fig.add_artist(Line2D([fx, fx], [fy0, fy1], color=col, lw=lw, ls=ls, solid_capstyle='butt',
                              dash_capstyle='round', transform=fig.transFigure))
        return 0.0
    raise ValueError(kind)


def key_row(fig, x_right, baseline, items, gap=3.0, glyph_gap=1.3, color=None):
    """A frameless one-row key, right-aligned at x_right (panel mm), its text on `baseline` (mm from the top): items
    [(kind, spec, label)] in reading order, muted 7 pt text, glyphs in the data colour. Returns the texts and the left
    edge (mm) of the key."""
    cap = fs.FS['legend'] * fs.CAP_EM / fs.PT_PER_MM
    kx = x_right
    texts = []
    for kind, spec, label in reversed(items):
        t = fs.text_mm(fig, kx, baseline, label, ha='right', color=color or fs.SP_MUTED, size=fs.FS['legend'])
        x0, _, _, _ = bb_mm(fig, t)
        _key_glyph(fig, kind, spec, x0 - glyph_gap - _glyph_half(kind, spec), baseline - cap / 2)
        kx = x0 - glyph_gap - 2 * _glyph_half(kind, spec) - gap
        texts.append(t)
    return texts[::-1], kx + gap


def _glyph_half(kind, spec):
    if kind == 'marker':
        return spec['ms'] / fs.PT_PER_MM / 2
    if kind == 'line':
        return 1.9
    if kind == 'square':
        return 1.1
    return 0.3


def key_column(fig, x_right, top_baseline, items, pitch=3.3, glyph_gap=1.3):
    """A frameless key of one item per line, right-aligned (texts end at x_right); glyphs on one column left of the
    widest text. Returns the texts."""
    cap = fs.FS['legend'] * fs.CAP_EM / fs.PT_PER_MM
    widths = [tw_mm(lab, fs.FS['legend']) for _, _, lab in items]
    x_text = x_right - max(widths)
    gh = max(_glyph_half(k, s) for k, s, _ in items)
    texts = []
    for i, (kind, spec, label) in enumerate(items):
        b = top_baseline + i * pitch
        texts.append(fs.text_mm(fig, x_text, b, label, ha='left', color=fs.SP_MUTED, size=fs.FS['legend']))
        _key_glyph(fig, kind, spec, x_text - glyph_gap - gh, b - cap / 2)
    return texts


def cat_y(ax, ys, labels, ylim=None, colors=None, pad=3.0):
    """Categorical y axis (DESIGN_V7 8.1): 7 pt row names in SP_FG at the left, no spine, no tick marks; rows top to
    bottom (the caller inverts ylim). colors: per-row label colour (SP_MUTED for a small group)."""
    ax.set_yticks(list(ys))
    ax.set_yticklabels(list(labels), fontsize=fs.FS['cat'], linespacing=1.05)
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis='y', length=0, pad=pad)
    for i, t in enumerate(ax.get_yticklabels()):
        t.set_color(colors[i] if colors is not None and colors[i] is not None else fs.SP_FG)
    if ylim is not None:
        ax.set_ylim(*ylim)


# Main-figure wording for the pre-choice measure (Fig 3a and Fig 4b: 'Any ad pixel fired (%)'; Fig 3b: 'Ad pixel
# fired (%)'). figstyle.PRECHOICE_AXIS_TITLE is not used in S6-S10 (the style is shared and not edited here).
ANY_FIRED = 'Any ad pixel fired (%)'
FIRED = 'Ad pixel fired (%)'
PAD_MM = 2.2                        # DESIGN_V7 6: 2-2.5 mm of air between the data and an axis end


def value_axis(ax, axis, lo, hi, step, signed=False, pad_mm=PAD_MM, length_mm=None):
    """A value axis with ticks lo..hi (step), PAD_MM of air beyond both end ticks (so no mark sits on an axis end) and
    its spine bounded to the tick range (sciplot range frame). length_mm: the plot's length along this axis (from the
    axes' size when omitted)."""
    fs.pct_axis(ax, axis, lo, hi, step)
    if signed:
        fs.signed_ticks(ax, list(np.arange(lo, hi + 1e-9, step)), axis)
    if length_mm is None:
        bb = ax.get_position()
        W, H = fs.size_mm(ax.figure)
        length_mm = bb.width * W if axis == 'x' else bb.height * H
    pad = pad_mm * (hi - lo) / (length_mm - 2 * pad_mm)
    (ax.set_xlim if axis == 'x' else ax.set_ylim)(lo - pad, hi + pad)
    ax.spines['bottom' if axis == 'x' else 'left'].set_bounds(lo, hi)


def rows_ylim(ax, y_first, y_last, ph_mm, pad_mm=2.0, band_mm=0.0):
    """y limits (rows run top to bottom) that keep the first and last marks pad_mm inside the plot, plus an empty band
    of band_mm at the top for a key. Returns data units per mm."""
    span = y_last - y_first
    k = span / (ph_mm - 2 * pad_mm - band_mm)
    ax.set_ylim(y_last + pad_mm * k, y_first - (pad_mm + band_mm) * k)
    return k


def off_spines(fig, ax, pts, name, min_mm=0.9):
    """Every mark centre (data coordinates) lies at least min_mm inside the plot area, so no marker sits on an axis."""
    fig.canvas.draw()
    px = fig.dpi / 25.4
    bb = ax.get_window_extent(fig.canvas.get_renderer())
    for (x, y) in pts:
        X, Y = ax.transData.transform((x, y))
        d = min(X - bb.x0, bb.x1 - X, Y - bb.y0, bb.y1 - Y) / px
        assert d >= min_mm, f'{name}: a mark at {(x, y)} is {d:.2f} mm from an axis'


def segment_gap(ax, pw_mm, gap_pt=0.75, span=100.0):
    """Data width of a white gap of gap_pt between stacked segments on an axis spanning `span` over pw_mm."""
    return gap_pt / fs.PT_PER_MM * span / pw_mm


def plot_box(fig, ax):
    """(left, right, top, bottom) of the plot area in panel mm (top / bottom measured from the panel top)."""
    bb = ax.get_position()
    W, H = fs.size_mm(fig)
    return bb.x0 * W, bb.x1 * W, (1 - bb.y1) * H, (1 - bb.y0) * H


def check_composite(tex_name, cells, fig_h):
    """The \\Panel cells of a composite .tex must equal the script's grid (panels are never rescaled)."""
    tex = open(os.path.join(SUPP, tex_name)).read()
    got = {m[0]: tuple(float(v) for v in m[1:5]) for m in
           re.findall(r'\\Panel\s*\{(\w)\}\s*\{([\d.]+)\}\s*\{([\d.]+)\}\s*\{([\d.]+)\}\s*\{([\d.]+)\}', tex)}
    want = {k: tuple(float(v) for v in c) for k, c in cells.items()}
    assert got == want, (tex_name, got, want)
    assert re.search(r'\\FigureCanvas\{%g\}' % fig_h, tex), f'{tex_name}: canvas height differs from {fig_h:g}'


# ---- Fig 1's 'continues beyond the axis' arrowhead (the Stealth head of Fig 1a's leak arrows)
HEAD_L_MM, HEAD_W_MM, HEAD_INSET_MM_BACK, HEAD_INSET_MM = 1.5, 1.2, 0.42, 0.35


def edge_head(ax, x_tip, y, direction, color=None):
    """A filled Stealth arrowhead whose tip is at (x_tip, y) data, pointing 'left' or 'right' (= fig1 make_panels.
    edge_head). Call after the limits are final. Returns the data x of its base (where a line into it should stop)."""
    tr = ax.transData
    px = ax.figure.dpi / 25.4
    tx, ty = tr.transform((x_tip, y))
    s = 1 if direction == 'right' else -1
    L, Wd, ins = HEAD_L_MM * px, HEAD_W_MM * px, HEAD_INSET_MM_BACK * px
    pts = [(tx, ty), (tx - s * L, ty + Wd / 2), (tx - s * (L - ins), ty), (tx - s * L, ty - Wd / 2)]
    ax.add_patch(Polygon(tr.inverted().transform(pts), closed=True, facecolor=color or fs.LEAK, edgecolor='none',
                         zorder=5, clip_on=False))
    return tr.inverted().transform((tx - s * (L - ins) * 0.9, ty))[0]


def mm_to_data(ax, dx_mm=0.0, dy_mm=0.0):
    """Data extent of dx_mm / dy_mm on a linear axis (limits final)."""
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    l, r, t, b = plot_box(ax.figure, ax)
    return dx_mm * (x1 - x0) / (r - l), dy_mm * (y1 - y0) / (b - t)


# ================================================================================================ S6 grid (mm)
G = fs.GUTTER_MM
W_A, W_B = 74.0, 110.0                    # b, the hero, gets the most area of the figure
W_C, W_D, W_E = 66.0, 59.0, 53.0
assert abs(W_A + G + W_B - fs.FIG_W_MM) < 1e-9 and abs(W_C + W_D + W_E + 2 * G - fs.FIG_W_MM) < 1e-9
H1, H2 = 56.0, 56.0
FIG_H = H1 + G + H2
TOP1, PH1 = 6.0, 40.0              # row 1: plot top, plot height (x axis at 46 mm)
TOP2, PH2 = 10.0, 36.0             # row 2: below the key band (x axis at 46 mm)
KEY_BASE = 3.2                     # row 2: baseline of the first key line (mm from the panel top)
CELLS = {'a': (0, 0, W_A, H1), 'b': (W_A + G, 0, W_B, H1), 'c': (0, H1 + G, W_C, H2),
         'd': (W_C + G, H1 + G, W_D, H2), 'e': (W_C + W_D + 2 * G, H1 + G, W_E, H2)}
# the banner contrast (a, e) is not a consent contrast: ink circle vs grey square, so that brick and slate keep d's (Fig
# 3a's) meaning in this figure -- brick = allowed until choice (consent lost), slate = denied until consent
BANNER, NOBANNER = sstyle(0, color=INK7), sstyle(1, color=fs.NEUTRAL)
ROWS_V = fs.VENDOR_ORDER + ['Any vendor']
YS_V = np.array(list(range(len(fs.VENDOR_ORDER))) + [len(fs.VENDOR_ORDER) + 0.7])   # 'Any vendor' set apart
VKEY = lambda v: 'any' if v == 'Any vendor' else v.replace('/', '~1')    # noqa: E731
R_PAD = 2.5                        # room right of a plot for its last tick label


def vendor_left():
    """Left edge (mm) of a vendor-row plot: the widest row name plus its pad, from the 2 mm indent."""
    return np.ceil(fs.INDENT_MM + max(tw_mm(v, fs.FS['cat']) for v in ROWS_V + ['All vendors']) + 1.6)


# ------------------------------------------------------------------------------------------------ a
def panel_a():
    fig = fs.panel(W_A, H1)
    left = vendor_left()
    pw = W_A - left - R_PAD
    ax = fs.axes_mm(fig, left, TOP1, pw, PH1)
    dy = 0.2
    pts = []
    for y, v in zip(YS_V, ROWS_V):
        for sub, st, d in (('banner', BANNER, -dy), ('no_banner', NOBANNER, dy)):
            p, lo, hi = share(f'fig3/a/{VKEY(v)}/{sub}')
            ci_h(ax, y + d, lo, hi, st['color'])
            dot(ax, p, y + d, st)
            pts += [(lo, y + d), (hi, y + d), (p, y + d)]
    value_axis(ax, 'x', 0, 100, 25, length_mm=pw)                # DESIGN_V7 6: share axes run 0-100
    ax.set_xlabel(FIRED)                                          # Fig 3b's wording (per row: that vendor's pixel)
    cat_y(ax, YS_V, ROWS_V)
    rows_ylim(ax, YS_V[0] - dy, YS_V[-1] + dy, PH1, pad_mm=1.6)
    # two direct labels on the summary row (no key): left of the brick interval, right of the slate interval
    y_any = YS_V[-1]
    _, lo_b, _ = (100 * fs.stat(f'fig3/a/any/banner/{f}') for f in ('p', 'lo', 'hi'))
    _, _, hi_n = (100 * fs.stat(f'fig3/a/any/no_banner/{f}') for f in ('p', 'lo', 'hi'))
    gx, _ = mm_to_data(ax, 1.2)
    l1 = fs.direct_label(ax, lo_b - gx, y_any - dy, 'Banner shown', ha='right', va='center_baseline', color=fs.SP_FG)
    l2 = fs.direct_label(ax, hi_n + gx, y_any + dy, 'No banner', ha='left', va='center_baseline', color=fs.SP_FG)
    x0, _, _, _ = bb_mm(fig, l1)
    _, x1, _, _ = bb_mm(fig, l2)
    left_mm, right_mm, _, _ = plot_box(fig, ax)
    assert x0 >= left_mm + 1.0 and x1 <= right_mm, 'a: a direct label leaves the plot'
    off_spines(fig, ax, [(x, y) for x, y in pts[2::3]], 'a')
    within(fig, ax, 'a')
    no_overlaps(fig, 'a')
    no_digits(fig, 'a')
    finish(fig, 'figS6a_vendor')
    return plot_box(fig, ax)


# ------------------------------------------------------------------------------------------------ b
B_LEFT = 11.0                       # room for the y title and its ticks
POLL_LW = 0.6                       # the 'one poll' reference: a solid LIGHT hairline (pt)


def panel_b():
    T = table('fig3b.csv')
    lim = mark('design/timeline_axis_s') / 2           # +-3 s, as the v5 panel
    poll = mark('design/banner_poll_ms') / 1000
    n = int(mark('fig3/b/n'))
    rel = np.sort(-T.gap.values / 1000.0)              # first sandboxed request minus banner visible (s)
    assert len(rel) == n
    assert int((np.abs(rel) > lim).sum()) == fs.stat('fig3/b/n_gap_beyond_axis')
    assert (rel < -lim).any() and (rel > lim).any(), 'b: the curve leaves the axis at both ends (two arrowheads)'
    F = lambda t: (rel <= t).sum() / n                 # noqa: E731  (cumulative share, right-continuous)
    p0, p1 = mark('fig3/b/before_banner/p'), mark('fig3/b/before_banner_by_poll/p')
    assert abs(F(0) - p0) < 1e-12 and abs(F(-poll) - p1) < 1e-12, 'b: the curve must give the registered shares'
    fig = fs.panel(W_B, H1)
    pw = W_B - B_LEFT - R_PAD
    ax = fs.axes_mm(fig, B_LEFT, TOP1, pw, PH1)
    ax.set_xlim(-lim, lim)
    fs.signed_ticks(ax, list(range(int(-lim), int(lim) + 1)), 'x')
    value_axis(ax, 'y', 0, 100, 25, length_mm=PH1)
    ax.set_xlabel('First sandboxed request, from banner visible (s)')
    ax.set_ylabel('Stores, cumulative (%)')
    # the step curve, ending in Fig 1's arrowhead where it leaves the axis (stores beyond it: caption)
    inside = rel[(rel > -lim) & (rel < lim)]
    mmx, _ = mm_to_data(ax, 1.0)
    yL, yR = 100 * F(-lim), 100 * F(lim)
    xbL = edge_head(ax, -lim + HEAD_INSET_MM * mmx, yL, 'left')
    xbR = edge_head(ax, lim - HEAD_INSET_MM * mmx, yR, 'right')
    assert xbL < inside.min() and xbR > inside.max()
    xs = np.concatenate([[xbL], inside, [xbR]])
    ys = 100 * np.array([F(-lim)] + [F(t) for t in inside] + [F(lim)])
    ax.step(xs, ys, where='post', color=fs.LEAK, lw=LW_DATA, solid_joinstyle='miter', solid_capstyle='butt', zorder=3)
    # the key area (v7 graft d; TINT LEAK, never alpha): under the drawn curve, from the left frame to the amber rule --
    # the stores whose first sandboxed request came before the banner. On the curve's own vertices; under every mark.
    path = [(-lim, ys[0])]
    for i in range(1, len(xs)):
        path += [(xs[i], ys[i - 1]), (xs[i], ys[i])]
    top = [(x, y) for x, y in path if x <= 0]
    v0 = 100 * (rel < 0).sum() / n                     # the curve just left of the rule
    poly = [(-lim, 0.0)] + top + [(0.0, v0), (0.0, 100 * F(0)), (0.0, 0.0)]
    assert all(x <= 0 for x, _ in poly)
    ax.add_patch(Polygon(poly, closed=True, facecolor=fs.TINT['LEAK'], edgecolor='none', zorder=1.0))
    fs.event_line(ax, 0.0, zorder=2)                                            # banner visible (amber, as Fig 1)
    # one polling interval before the banner: a solid LIGHT hairline (DESIGN_V7 4: no dashes or dots in a data panel)
    ax.axvline(-poll, color=fs.LIGHT, lw=POLL_LW, solid_capstyle='butt', zorder=1.5)
    # the open crossing ring where the curve meets the amber rule; a dot in the line colour where it meets the hairline
    ax.plot([0.0], [100 * p0], ls='none', marker='o', ms=MS7, mfc=fs.SURFACE, mec=fs.LEAK, mew=LW_DATA, zorder=5)
    ax.plot([-poll], [100 * p1], ls='none', marker='o', ms=MS7, mfc=fs.LEAK, mec=fs.LEAK, mew=MEW7, zorder=5)
    # two direct labels: the event (above the plot, as Fig 1b) and the dotted rule (left of it, above the curve)
    x0_mm = B_LEFT + (0.0 + lim) / (2 * lim) * pw                          # the amber rule's x (panel mm)
    fs.text_mm(fig, x0_mm, TOP1 - 1.4, 'banner visible', ha='center', color=fs.SP_FG)
    lab = fs.direct_label(ax, -poll - 0.08, 92, 'one poll', ha='right', va='center', color=fs.SP_FG)
    assert 100 * F(-poll) < 92 - 8, "b: 'one poll' must sit above the curve"
    lx0, lx1, _, _ = bb_mm(fig, lab)
    x_lab0 = -lim + (lx0 - B_LEFT) / pw * 2 * lim
    assert F(x_lab0 + (lx1 - lx0) / pw * 2 * lim) * 100 < 80, 'b: label on the curve'
    within(fig, ax, 'b')
    no_overlaps(fig, 'b')
    no_digits(fig, 'b')
    finish(fig, 'figS6b_ccdf')
    return plot_box(fig, ax)


# ------------------------------------------------------------------------------------------------ c
ORIGINS = ['sandbox', 'open_pixel', 'relay', 'page']            # stacking order, left to right
ORIGIN_NAME = {'sandbox': 'Sandbox', 'open_pixel': 'Open pixel', 'page': 'Page script'}
# DESIGN_V7 8.7 tier order: the story first (SAND: the sandbox as a category), then the mid grey, then LIGHT. 'relay'
# (requests relayed from a sandbox by Shopify code in the page; Google's only) keeps its share of the bar but is not
# drawn: it is narrower than the white gap between two segments (asserted), so it has no key entry (caption).
ORIGIN_FILL = {'sandbox': fs.SAND, 'open_pixel': TICK_GREY, 'page': fs.LIGHT}
C_BAR_MM = 1.2                      # c: bar thickness (mm): thin, so the dark SAND tier does not outweigh the hero


def panel_c():
    rows = fs.VENDOR_ORDER + ['All']
    names = [('All vendors' if v == 'All' else v) for v in rows]
    fig = fs.panel(W_C, H2)
    left = vendor_left()
    pw = W_C - left - R_PAD
    ax = fs.axes_mm(fig, left, TOP2, pw, PH2)
    gap = segment_gap(ax, pw)
    assert [v for v in fs.VENDOR_ORDER if fs.stat(f"fig3/c/{v.replace('/', '~1')}/relay") > 0] == ['Google']
    assert fs.stat('fig3/c/All/relay_k') == fs.stat('fig3/c/Google/relay_k')
    for v in rows:
        assert fs.stat(f"fig3/c/{v.replace('/', '~1')}/relay") * 100 <= gap, 'c: a relayed sliver is wider than a gap'
    k = rows_ylim(ax, YS_V[0], YS_V[-1], PH2, pad_mm=1.6)
    hgt = C_BAR_MM * k
    for y, v in zip(YS_V, rows):
        vv = v.replace('/', '~1')
        r = {o: mark(f'fig3/c/{vv}/{o}') for o in ORIGINS}
        assert abs(sum(r.values()) - 1) < 1e-9, v
        segs = [(o, 100 * r[o]) for o in ORIGINS if r[o] > 0]
        x = 0.0
        for i, (o, w) in enumerate(segs):
            g = gap if i < len(segs) - 1 else 0.0
            if o != 'relay':
                ax.add_patch(Rectangle((x, y - hgt / 2), max(w - g, 0.0), hgt, facecolor=ORIGIN_FILL[o],
                                       edgecolor='none', linewidth=0, zorder=2))
            x += w
    ax.set_xlim(0, 100)                               # a bar starts at 0: the axis starts there
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.spines['bottom'].set_bounds(0, 100)
    ax.set_xlabel('Ad requests (%)')
    cat_y(ax, YS_V, names)
    # the key, in the row's key band above the plot, right-aligned to the plot
    order = ['sandbox', 'open_pixel', 'page']
    key_row(fig, left + pw, KEY_BASE, [('square', ORIGIN_FILL[o], ORIGIN_NAME[o]) for o in order], gap=2.6)
    within(fig, ax, 'c')
    no_overlaps(fig, 'c')
    no_digits(fig, 'c')
    finish(fig, 'figS6c_origin')
    return plot_box(fig, ax)


# ------------------------------------------------------------------------------------------------ d
PRODUCTS = ['pandectes', 'onetrust', 'cookiebot', 'osano', 'shopify_native']
ALLOWED, DENIED = sstyle(0), sstyle(1)       # brick circle (allowed until choice) / slate square


def panel_d():
    base = 'fig3/d/mh_by_product/by_product'
    small = mark('design/min_stores_row')       # DESIGN_V7 8.1: a group of fewer than 10 units is drawn grey
    assert small == 10
    names = [CMP_NAME[p] for p in PRODUCTS]
    fig = fs.panel(W_D, H2)
    left = np.ceil(fs.INDENT_MM + max(tw_mm(s, fs.FS['cat']) for s in names) + 1.6)
    pw = W_D - left - R_PAD
    ax = fs.axes_mm(fig, left, TOP2, pw, PH2)
    ys = np.arange(len(PRODUCTS), dtype=float)
    dy = 0.17
    pts, greys, name_cols = [], [], []
    for y, p in zip(ys, PRODUCTS):
        both_small = True
        for sub, st, d in (('allowed', ALLOWED, -dy), ('denied', DENIED, dy)):
            nn = mark(f'{base}/{p}/{sub}/n')
            pp, lo, hi = share(f'{base}/{p}/{sub}')
            s = recolor(st, fs.NEUTRAL) if nn < small else st
            if nn < small:
                greys.append((p, sub))
            both_small &= nn < small
            ci_h(ax, y + d, lo, hi, s['color'])
            dot(ax, pp, y + d, s)
            pts += [(lo, y + d), (hi, y + d), (pp, y + d)]
        name_cols.append(fs.SP_MUTED if both_small else None)
    # the caption names the small groups: Cookiebot 'denied', both of Osano's, Shopify's banner 'allowed'
    assert greys == [('cookiebot', 'denied'), ('osano', 'allowed'), ('osano', 'denied'), ('shopify_native', 'allowed')], greys
    value_axis(ax, 'x', 0, 100, 25, length_mm=pw)   # the same shares as Fig 3a's product rows, under its axis title
    ax.set_xlabel(ANY_FIRED)
    cat_y(ax, ys, names, colors=name_cols)
    rows_ylim(ax, ys[0] - dy, ys[-1] + dy, PH2, pad_mm=2.0)
    key_column(fig, left + pw, KEY_BASE, [('marker', ALLOWED, 'Allowed until choice'),
                                                ('marker', DENIED, 'Denied until consent')], pitch=3.2)
    off_spines(fig, ax, pts[2::3], 'd')
    within(fig, ax, 'd')
    no_overlaps(fig, 'd')
    no_digits(fig, 'd')
    finish(fig, 'figS6d_products')
    return plot_box(fig, ax)


# ------------------------------------------------------------------------------------------------ e
E_LEFT = 11.0


def _stores():
    st = table('store_table.csv')
    return st[(st.stratum == 'main') & (~st.store_id.isin(fs.stat('design/content_excluded_stores')))]


def panel_e():
    m = _stores()
    fig = fs.panel(W_E, H2)
    pw = W_E - E_LEFT - R_PAD
    ax = fs.axes_mm(fig, E_LEFT, TOP2, pw, PH2)
    xmax = 120
    groups = [(False, 'fig1b/nobanner_fires', NOBANNER, 3), (True, 'fig1b/banner_fires', BANNER, 4)]   # ink over grey
    for banner, key, st, z in groups:
        g = m[m.banner_A0 == banner].A0_n_sbx.fillna(0).astype(int).values
        n, k, p = mark(key + '/n'), mark(key + '/k'), mark(key + '/p')
        assert len(g) == n and int((g >= 1).sum()) == k, (key, len(g), (g >= 1).sum())
        assert g.max() < xmax
        xs = np.arange(1, xmax + 1)
        yv = np.array([100.0 * (g >= x).mean() for x in xs])
        assert abs(yv[0] - 100 * p) < 1e-9
        ax.step(xs, yv, where='post', color=st['color'], lw=LW_DATA, solid_joinstyle='miter', zorder=z)
        dot(ax, 1, 100 * p, st, zorder=z + 2)
    ax.set_xscale('log')
    ax.set_xlim(0.8, 1.04 * xmax)                     # air left of n = 1, so its marks are drawn whole
    ax.set_xticks([1, 10, 100])
    ax.set_xticklabels(['1', '10', '100'])
    ax.minorticks_off()
    value_axis(ax, 'y', 0, 100, 25, length_mm=PH2)
    ax.set_ylim(0, ax.get_ylim()[1])                  # the curves end on 0: the floor stays the axis
    ax.spines['bottom'].set_bounds(1, xmax)
    ax.set_xlabel('Sandboxed requests per store, n')
    ax.set_ylabel('Stores with ≥ n requests (%)')
    key_column(fig, E_LEFT + pw, KEY_BASE, [('line', (BANNER, BANNER['color']), 'Banner shown'),
                                                 ('line', (NOBANNER, NOBANNER['color']), 'No banner')], pitch=3.2)
    off_spines(fig, ax, [(1, 100 * fs.stat(k + '/p')) for _, k, _, _ in groups], 'e')
    within(fig, ax, 'e')
    no_overlaps(fig, 'e')
    no_digits(fig, 'e')
    finish(fig, 'figS6e_requests')
    return plot_box(fig, ax)


def check_alignment(boxes, rows):
    """DESIGN_V7 9: the plots of a row share their top and their x-axis line (panel mm)."""
    for row in rows:
        tops = {round(boxes[k][2], 3) for k in row}
        bottoms = {round(boxes[k][3], 3) for k in row}
        assert len(tops) == 1 and len(bottoms) == 1, f'plots of {row} misaligned: tops {tops}, bottoms {bottoms}'


if __name__ == '__main__':
    check_composite('figS6.tex', CELLS, FIG_H)
    fs.reset_registry()
    with fs.v7_context():
        boxes = dict(a=panel_a(), b=panel_b(), c=panel_c(), d=panel_d(), e=panel_e())
    check_alignment(boxes, ['ab', 'cde'])
    write_registry('figS6')
    print(f'S6 panels written (figure 190 x {FIG_H:g} mm)')
