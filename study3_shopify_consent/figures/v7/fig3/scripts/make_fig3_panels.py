"""Figure 3 panels, v7 (binding: ../../DESIGN_V7.md; worked example ../../fig1): before any choice, whether sandboxed
pixels fire tracks Shopify's region default, even within the same consent tool. The sciplot clean theme
(mmd-ahd/scientific-figure-skill, read and re-implemented, never executed) with the bake-off grafts: nature-figure's
figure contract and its tinted key area, FigGenie's labelled groups, sciplot's 'grey for context, colour for signal'
and dots + summary for small n. Panel letters, contents and every number are those of v6; the counts live in the
caption (scripts/make_caption_fig3.py).

Figure contract (DESIGN_V7 section 1). Claim: the region default, not the consent tool, decides whether sandboxed
pixels fire before any choice.
  a  (hero; the comparison, then its control) one forest plot read left to right on shared rows.
     left: the share of stores whose sandboxed ad pixel sent a request before any choice, under Shopify's two region
       defaults: 'allowed until choice' (LEAK brick circle, a little above the row line) and 'denied until consent'
       (HONOUR slate square, a little below), each with its uncapped Wilson 95 % CI in the colour of its mark. Rows: the
       consent products with at least design.min_cell_n stores under both defaults, in Mantel-Haenszel (MH) weight
       order, under a muted group name 'Consent product', then, set apart below a gap, the summary row 'All banner
       stores' (section 8.1). A group of fewer than design.min_stores_row stores is drawn grey (NEUTRAL marks and CI; a
       row whose groups are all small gets its name in SP_MUTED; section 8.1), and a one-line 6 pt muted note on the
       group name's baseline says so in the panel ('Grey: fewer than 10 stores'; the 10 is the registered value). The
       key area (nature-figure; TINT LEAK, pre-mixed, never alpha): a pale brick band from the 'denied' share to the
       'allowed' share, between the two marks, in every row whose two groups are both drawn in colour -- the stores
       that lost consent to the default. The summary row carries the two direct labels (allowed above its circle,
       denied below its square).
     right ('Fig. 3a, right'; the control): the difference 'allowed' minus 'denied' (pp), on the SAME mm per
       percentage point as the left plot and on the same rows, in the dot + CI grammar of section 8.1 (no bars): a
       near-black diamond with its uncapped 95 % CI against a solid NEUTRAL zero rule on an axis from -20 (the zero
       idiom of Fig. 4b right before 2026-10-19 22:16; no dashes in a data panel, section 4). The rule runs only over
       the rows that carry a difference. The difference pooled within product over all the MH strata (filled
       diamond, Sato CI; the estimate the text cites) sits level with the middle of the product rows, which a thin
       NEUTRAL bracket in the white between the two plots groups (FigGenie: a labelled group); the crude difference
       over all banner stores (open diamond, Newcombe CI) sits on the 'All banner stores' row. Each diamond carries
       its own direct label above it: 'Within product', 'Crude'.
  b  (the mechanism) the same measure counting only pixels that declare a purpose ('marketing', not 'marketing', no
     purpose at all): a vertical paired dot plot on a's markers and CIs, a pale brick band between each pair, on one-line
     category names. No direct labels: a's summary row names the two marks on the same baseline, and the caption says
     b uses a's markers. The default gates the pixels that declare 'marketing'; the others barely move.

Style: fs.v7_context() (Arial; 7 pt words, 6 pt ticks and notes; open L axes 0.6 pt SP_AXIS; markers 3.5 pt; CIs
0.75 pt uncapped). A categorical axis has no spine (as Fig 1b's event strip): a left and a right keep only their
bottom value axes (a left trimmed to 0-100, a right to -20..+60); b's bottom spine is its 0 % baseline. Colours per
panel: LEAK, HONOUR, NEUTRAL, SP_FG and the one tint (<= 5). Every panel is linted (sp_lint.lint_fig) before it is saved.

Every drawn value (dot, CI end, diamond, band end) is read from analysis/outputs/stats.json or
figures/v7/fig3/derived_numbers.json (scripts/derive_fig3.py) and registered as a drawn mark in panels/fig3_numbers.csv
for the trace check (scripts/trace_fig3.py). The numbers printed in the panels are the axis ticks and the registered
threshold in a's grey note.

Run:  python3 figures/v7/fig3/scripts/make_fig3_panels.py      (build_fig3.sh composes and checks)
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIG3 = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG3, '..', 'style')))
import figstyle as fs  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
sys.path.insert(0, HERE)
import sp_lint  # noqa: E402  (sciplot step 5: lint every panel before it is saved)

PANELS = os.path.join(FIG3, 'panels')
DERIVED3 = os.path.join(FIG3, 'derived_numbers.json')
os.makedirs(PANELS, exist_ok=True)

# ---- composite grid (mm); must equal fig3.tex (asserted in check_composite) ----
FIG_W = fs.FIG_W_MM                       # 190 mm (Elsevier full width): a holds two plots, b one
FIG_H = 61.0
A_W = 120.5                               # a: the hero, about two thirds of the width
B_W = FIG_W - A_W - fs.GUTTER_MM          # 63.5: b wide enough for one-line category names
MM_PER_PP = 0.48                          # one percentage point is 0.48 mm in every plot of the figure (25 pp = 12 mm)
PCT_HI = 100.0                            # b: the value axis runs 0-100 % over PH, so ...
TOP, PH = 5.5, PCT_HI * MM_PER_PP         # every plot: top at TOP, x axis at TOP + PH (one line across the figure)
X_LIM = (-4.0, 104.0)                     # a left: 0-100 % (spine trimmed to 0-100) plus air for marks near the ends
D_LIM = (-22.0, 62.0)                     # a right: -20..+60 pp (spine trimmed to the ticks) plus air at both ends
D_LO, D_HI, D_STEP = -20, 60, 20          # a right ticks (pp; fs.signed_ticks); trace_fig3 reads these
AL_X0 = 22.0                              # a left: room for the row names (>= fs.INDENT_MM from the edge)
AL_PW = (X_LIM[1] - X_LIM[0]) * MM_PER_PP  # 51.84 mm
AR_PW = (D_LIM[1] - D_LIM[0]) * MM_PER_PP  # 40.32 mm
AR_RM = 1.2                               # a right: margin for half of the '+60' tick label
AR_X0 = A_W - AR_RM - AR_PW               # a right's plot left edge (its -22)
B_YR = 10.5                               # b: room for the y title + ticks
B_PW = B_W - B_YR - 0.5
assert abs(A_W + fs.GUTTER_MM + B_W - FIG_W) < 1e-9 and B_PW >= 50, (A_W, B_W, B_PW)
assert AR_X0 - (AL_X0 + AL_PW) >= 5.0, 'a: the two plots of a run together'

# a: rows in data units (downwards, 1 unit = one row pitch)
GAP_ALL = 0.55                            # extra space above the summary row 'All banner stores' (section 8.1)
EDGE_TOP, EDGE_BOT = 0.62, 0.80           # top row centre -> plot top; summary row centre -> x axis (room for the
                                          # 'denied' label under the summary row's square)
DODGE = 0.14                              # half the vertical split of a row's pair ('allowed' above, 'denied' below):
                                          # the pair sits 0.28 of a pitch apart, the rows 0.72 (v6 critic r1)
CI_LW = fs.LW['error']                    # 0.75 pt, uncapped (DESIGN_V7 section 4)
LBL_GAP_MM = 0.7                          # direct label <-> its mark (edge to ink)
ZERO_LW = 0.6                             # a right: the zero rule (solid NEUTRAL; = Fig 4b right's ZERO_LW)
BRACKET_LW = 0.6                          # a: the product-row bracket (NEUTRAL, the weight of a region frame)
BRACKET_DX_MM = 1.2                       # its spine sits this far right of a left's plot edge ...
BRACKET_ARM_MM = 0.8                      # ... with arms this long pointing back at the rows ...
BRACKET_NUB_MM = 1.2                      # ... and a nub this long at its middle, pointing at the pooled row
BRACKET_PAD_MM = 0.5                      # it reaches this far beyond the outermost marks of the product rows
ZERO_ABOVE = 0.5                          # a right: the zero rule starts half a pitch above its first data row
B_DX_MM = 1.8                             # b: half the split of a pair (circle left, square right); the band between
                                          # them is 2 * B_DX_MM wide

# one-line axis titles (sentence case, unit in parentheses); the caption defines each measure in full
AL_TITLE = 'Any ad pixel fired (%)'       # = Fig 4b left: a sandboxed ad request before any choice, % of stores
D_TITLE = 'Difference (pp)'               # 'allowed' minus 'denied'
B_TITLE = AL_TITLE                        # b: the same measure, counting only pixels that declare the purpose
B_XTITLE = 'Declared purpose'
ALLOWED_LAB, DENIED_LAB = 'Allowed until choice', 'Denied until consent'   # = Fig 4b's category names
POOLED_LAB, CRUDE_LAB = 'Within product', 'Crude'
HDR_LAB = 'Consent product'               # the group name of the product rows (muted)
HDR_ABOVE_MM = 3.6                        # its baseline above the first row's centre line
GREY_NOTE = 'Grey: fewer than {} stores'  # a left: 6 pt muted note on the header's baseline (section 8.1 rule)

# ---- marks (DESIGN_V7 section 5): 3.5 pt markers (v6 ratios x 3.5 / 4.5), edge 0.6 pt; colour AND shape
MS = fs.V7_LW['marker']                   # 3.5 pt
MEW = fs.V7_LW['mew']                     # 0.6 pt
ALLOWED = dict(marker='o', ms=MS, mfc=fs.LEAK, mec=fs.LEAK, mew=MEW, color=fs.LEAK)
DENIED = dict(marker='s', ms=MS * 0.95, mfc=fs.HONOUR, mec=fs.HONOUR, mew=MEW, color=fs.HONOUR)
MS_DIA = 3.6                              # a right: v6's 4.6 pt diamond x 3.5 / 4.5 (= Fig 4b right's MS_DIA)
DIA_OPEN_MEW = 1.0                        # open marker: white with a 1.0 pt edge (section 5; = Fig 4's MEW_OPEN)
DIA_HALF_MM = (MS_DIA * 2 ** 0.5 / 2 + DIA_OPEN_MEW / 2) / fs.PT_PER_MM   # matplotlib's 'D' is the ms square turned
                                          # 45 degrees: its half-height is ms / sqrt(2), plus half its edge (0.90 mm)


def small(st):
    """The grey treatment of a group with fewer than design.min_stores_row stores (section 8.1): its shape, NEUTRAL."""
    return dict(st, mfc=fs.NEUTRAL, mec=fs.NEUTRAL, color=fs.NEUTRAL)


# consent-product display names (= figures/v7/supp/scripts/supp_common.py CMP_NAME, plus consentmanager)
CMP_NAME = {'pandectes': 'Pandectes', 'onetrust': 'OneTrust', 'shopify_native': 'Shopify’s banner',
            'cookiebot': 'Cookiebot', 'osano': 'Osano', 'iubenda': 'iubenda', 'usercentrics': 'Usercentrics',
            'ketch': 'Ketch', 'clarip': 'Clarip', 'cookiescript': 'CookieScript', 'cookieyes': 'CookieYes',
            'consentmanager': 'consentmanager'}
ALL_LAB = 'All banner stores'
D_ROWS = [('pooled', 'fig3/d/mh_by_product', ('rd', 'rd_lo', 'rd_hi'), True, POOLED_LAB),
          ('crude', 'fig3/d/mh_by_product/crude', ('diff', 'diff_lo', 'diff_hi'), False, CRUDE_LAB)]
PURPOSES = [('mkt_sbx', 'Marketing'), ('nomkt_sbx', 'Not marketing'), ('nopurpose_sbx', 'No purpose')]


# ------------------------------------------------------------------------------------------------ numbers
_D3 = None


def _d3():
    global _D3
    if _D3 is None:
        _D3 = json.load(open(DERIVED3))
    return _D3


def _D3_value(key):
    """Unregistered read of a fig3 derived value (geometry, order); printed values go through N3, drawn ones mark3."""
    name, _, rest = key.partition('/')
    v = _d3()[name]['value']
    return fs._walk(v, rest) if rest else v


def N3(key, f='int'):
    """Render a value of figures/v7/fig3/derived_numbers.json and register it (used by the caption)."""
    v = _D3_value(key)
    s = fs.render(v, f)
    fs._REG.append(dict(text=s, shown=fs.typo(s), source='derived_fig3', key=key, fmt=f, value=json.dumps(v)))
    return fs.typo(s)


def mark3(key):
    """Register a fig3 derived value that is drawn but not printed (dot position, CI end)."""
    v = _D3_value(key)
    fs._REG.append(dict(text='', shown='', source='derived_fig3', key=key, fmt='mark', value=json.dumps(v)))
    return v


def reg_only(key):
    """Register a stats.json value that is drawn (dot position, CI end, diamond, threshold) but not printed."""
    fs._REG.append(dict(text='', shown='', source='stats', key=key, fmt='mark', value=json.dumps(fs.stat(key))))
    return fs.stat(key)


def share(key):
    """A stats share record in percentage units (p, lo, hi) plus its n, each registered as a drawn mark."""
    return tuple(100 * reg_only(f'{key}/{f}') for f in ('p', 'lo', 'hi')) + (reg_only(f'{key}/n'),)


def share3(key):
    """A fig3-derived share record in percentage units (p, lo, hi) plus its n, each registered as a drawn mark."""
    return tuple(100 * mark3(f'{key}/{f}') for f in ('p', 'lo', 'hi')) + (mark3(f'{key}/n'),)


# ------------------------------------------------------------------------------------------------ helpers
def check_composite():
    """The cells in fig3.tex must equal the constants above (panels are never rescaled)."""
    tex = open(os.path.join(FIG3, 'fig3.tex')).read()
    cells = {m[0]: tuple(float(v) for v in m[1:5]) for m in
             re.findall(r'\\Panel\s*\{(\w)\}\s*\{([\d.]+)\}\s*\{([\d.]+)\}\s*\{([\d.]+)\}\s*\{([\d.]+)\}', tex)}
    want = {'a': (0, 0, A_W, FIG_H), 'b': (A_W + fs.GUTTER_MM, 0, B_W, FIG_H)}
    assert cells == want, (cells, want)
    assert re.search(r'\\FigureCanvas\{%g\}' % FIG_H, tex), 'fig3.tex canvas height differs from FIG_H'


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


def label_gaps(fig, ax):
    """Horizontal white space (mm) between neighbouring x tick labels of a categorical axis."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    px = fig.dpi / 25.4
    bbs = sorted((t.get_window_extent(r) for t in ax.get_xticklabels() if t.get_text()), key=lambda b: b.x0)
    return [(b.x0 - a.x1) / px for a, b in zip(bbs, bbs[1:])]


def text_clear(fig, ax, t, boxes, name, pad_mm=0.5):
    """A direct label stays >= pad_mm clear of every mark, interval and band in `boxes` [(x0, x1, y0, y1, half_mm) in
    data units; half_mm = the mark's half size added around the box], except the one it labels (left out by the
    caller)."""
    fig.canvas.draw()
    px = fig.dpi / 25.4
    tb = t.get_window_extent(fig.canvas.get_renderer())
    to = ax.transData.transform
    for x0, x1, y0, y1, half in boxes:
        (a0, b0), (a1, b1) = to((x0, y0)), to((x1, y1))
        h = half * px
        l, r, b, tp = min(a0, a1) - h, max(a0, a1) + h, min(b0, b1) - h, max(b0, b1) + h
        p = pad_mm * px
        clear = r < tb.x0 - p or l > tb.x1 + p or tp < tb.y0 - p or b > tb.y1 + p
        assert clear, f'{name}: label {t.get_text()!r} crowds the mark / interval / band at {(x0, x1, y0, y1)}'


def ci_v(ax, x, lo, hi, color, zorder=3):
    ax.plot([x, x], [lo, hi], color=color, lw=CI_LW, solid_capstyle='butt', zorder=zorder, clip_on=False)


def ci_h(ax, y, lo, hi, color, zorder=3):
    ax.plot([lo, hi], [y, y], color=color, lw=CI_LW, solid_capstyle='butt', zorder=zorder, clip_on=False)


def mark(ax, x, y, st, zorder=4):
    ax.plot([x], [y], ls='none', marker=st['marker'], ms=st['ms'], mfc=st['mfc'], mec=st['mec'], mew=st['mew'],
            zorder=zorder, clip_on=False)


def band(ax, x0, x1, y0, y1):
    """The key area (DESIGN_V7 section 3.3): a TINT LEAK ground, square, no outline, under every mark."""
    ax.add_patch(Rectangle((min(x0, x1), min(y0, y1)), abs(x1 - x0), abs(y1 - y0), facecolor=fs.TINT['LEAK'],
                           edgecolor='none', linewidth=0, zorder=1))


def half_mm(st):
    return st['ms'] / fs.PT_PER_MM / 2


def within_panel(fig, ax, name, left_min=0.8):
    """The plot and all its labels end inside the panel, clear of its edges."""
    W, H = fs.size_mm(fig)
    x0, x1, _, b = bb_mm(fig, ax)                         # the axes incl. tick labels and titles
    assert x0 >= left_min and x1 <= W - 0.3 and b <= H - 0.3, \
        f'{name}: plot or labels leave the panel ({x0:.2f}, {x1:.2f}, {b:.2f})'
    return x0, x1, b


# ------------------------------------------------------------------------------------------------ panel a
def a_rows():
    """Row centres (data units, downwards) of a: the products with >= min_cell_n stores under both defaults, in
    MH-weight order, then, after GAP_ALL, the summary row. Returns ([(key, y)], y of the summary row)."""
    S3 = 'fig3a_strata'
    order = _D3_value(S3 + '/order')
    min_n = _D3_value(S3 + '/min_cell_n')
    full = [c for c in order if min(_D3_value(f'{S3}/rows/{c}/allowed/n'), _D3_value(f'{S3}/rows/{c}/denied/n')) >= min_n]
    assert full == order[:len(full)] and len(full) == _D3_value(S3 + '/n_full'), 'MH order no longer puts them first'
    rows = [(c, float(i)) for i, c in enumerate(full)]
    rows.append(('all', len(full) - 1 + 1.0 + GAP_ALL))
    return rows, rows[-1][1]


def a_pitch():
    """mm per row unit of a (the rows fill the plot height)."""
    _, y_last = a_rows()
    return PH / (y_last + EDGE_TOP + EDGE_BOT)


def small_groups():
    """[(product, group)] drawn grey in a left: fewer than design.min_stores_row stores (caption, alt text)."""
    few = fs.stat('design/min_stores_row')
    rows, _ = a_rows()
    out = []
    for k, _ in rows:
        if k == 'all':
            continue
        for g in ('allowed', 'denied'):
            if _D3_value(f'fig3a_strata/rows/{k}/{g}/n') < few:
                out.append((k, g))
    return out


def panel_a():
    """Left: the two shares per row; right: the pooled within-product and the crude difference, on the same rows and
    the same mm per percentage point. Returns the right edge (mm) of everything drawn, the gap inside a (mm), the row
    pitch (mm) and the bottom of a's content (mm)."""
    S3 = 'fig3a_strata'
    few = reg_only('design/min_stores_row')               # drawn: the grey treatment of small groups
    fig = fs.panel(A_W, FIG_H)
    rows, y_last = a_rows()
    pitch = a_pitch()
    ylim = (y_last + EDGE_BOT, -EDGE_TOP)

    # ---- left: dot plot, products on the y axis, summary row last
    ax = fs.axes_mm(fig, AL_X0, TOP, AL_PW, PH)
    ax.set_ylim(*ylim)
    ax.set_xlim(*X_LIM)
    ax.set_xticks(range(0, 101, 25))
    ax.spines['bottom'].set_bounds(0, 100)
    ax.spines['left'].set_visible(False)                  # a categorical axis has no spine (rows are named)
    ax.set_xlabel(AL_TITLE)
    ax.set_yticks([y for _, y in rows])
    ax.tick_params(axis='y', length=0, pad=3.0)
    boxes, drawn, summary = [], {}, None
    for k, y in rows:
        if k == 'all':
            a, d = share('fig3/d/opt_out/any_sbx'), share('fig3/d/opt_in/any_sbx')
        else:
            a, d = share3(f'{S3}/rows/{k}/allowed'), share3(f'{S3}/rows/{k}/denied')
            assert a[0] > d[0], k                    # caption / alt text: higher under 'allowed' in every drawn product
        sa = ALLOWED if a[3] >= few else small(ALLOWED)
        sd = DENIED if d[3] >= few else small(DENIED)
        coloured = sa is ALLOWED and sd is DENIED
        if coloured:                                 # the key area: the excess under 'allowed', between the two marks
            band(ax, d[0], a[0], y - DODGE, y + DODGE)
            boxes.append((d[0], a[0], y - DODGE, y + DODGE, 0.0))
        for (p, lo, hi, _n), st, yy in ((a, sa, y - DODGE), (d, sd, y + DODGE)):
            assert lo - 1e-9 <= p <= hi + 1e-9       # (Wilson ends at 0 or 1 carry float rounding)
            assert X_LIM[0] + 2.0 / MM_PER_PP <= lo and hi <= X_LIM[1] - 2.0 / MM_PER_PP   # >= 2 mm air at the ends
            ci_h(ax, yy, lo, hi, st['color'])
            mark(ax, p, yy, st)
            boxes.append((lo, hi, yy, yy, half_mm(st)))
        drawn[k] = (sa, sd)
        if k == 'all':
            summary = (a, d, y)
    # row names 7 pt SP_FG; a row whose groups are all small (all grey) gets its name in SP_MUTED (section 8.1)
    ax.set_yticklabels([ALL_LAB if k == 'all' else CMP_NAME[k] for k, _ in rows])
    for (k, _), t in zip(rows, ax.get_yticklabels()):
        sa, sd = drawn[k]
        t.set_fontsize(fs.FS['cat'])
        t.set_color(fs.SP_MUTED if (sa is not ALLOWED and sd is not DENIED) else fs.SP_FG)
    assert 2 * DODGE <= 0.3, DODGE                   # a pair reads as one row (0.28 vs 0.72 of a pitch)
    # the product rows' group name (FigGenie: a labelled group; 7 pt SP_MUTED, as Fig 1's region names), right-aligned
    # on the row names, in the headroom above the first row and clear of the letter zone
    lab_x1 = max(bb_mm(fig, t)[1] for t in ax.get_yticklabels())
    y0_mm = TOP + (rows[0][1] + EDGE_TOP) * pitch          # first row centre (mm from the panel top)
    hdr_y = y0_mm - HDR_ABOVE_MM
    hdr = fs.text_mm(fig, lab_x1, hdr_y, HDR_LAB, ha='right', color=fs.SP_MUTED, size=fs.FS['label'])
    hx0, _, htop, _ = bb_mm(fig, hdr)
    assert htop >= fs.LETTER_ZONE_MM[1] + 0.3 or hx0 >= fs.LETTER_ZONE_MM[0] + 0.3, 'a: header in the letter zone'
    # the grey rule in the panel (critic r1 of v7): one 6 pt muted note on the header's baseline, right-aligned on the
    # 100 % tick, so 'grey' does not depend on the caption. Its number is the registered design value (traced).
    note_txt = GREY_NOTE.format(fs.N('design/min_stores_row'))
    x100_mm = AL_X0 + (100 - X_LIM[0]) * MM_PER_PP
    note = fs.text_mm(fig, x100_mm, hdr_y, note_txt, ha='right', color=fs.SP_MUTED, size=fs.FS['note'])
    nx0, nx1, ntop, nbot = bb_mm(fig, note)
    assert nx0 - bb_mm(fig, hdr)[1] >= 10.0, 'a: the grey note runs into the group name'
    text_clear(fig, ax, note, boxes, 'a left (note)', pad_mm=1.0)
    assert ntop >= 0.3

    # the two direct labels, on the summary row: 'allowed' centred above its circle, 'denied' centred below its square
    (pa, _, _, _), (pd, _, _, _), ys = summary
    off = (half_mm(ALLOWED) + LBL_GAP_MM) / pitch
    t_al = ax.text(pa, ys - DODGE - off, ALLOWED_LAB, ha='center', va='baseline', fontsize=fs.FS['label'],
                   color=fs.SP_FG)
    off_d = (half_mm(DENIED) + LBL_GAP_MM) / pitch
    t_de = ax.text(pd, ys + DODGE + off_d, DENIED_LAB, ha='center', va='top', fontsize=fs.FS['label'],
                   color=fs.SP_FG)
    others = [b for b in boxes if not (abs(b[2] - (ys - DODGE)) < 1e-9 and b[0] <= pa <= b[1] and b[4] > 0)]
    text_clear(fig, ax, t_al, [b for b in others if b[2] < ys - DODGE - 1e-9], 'a left')
    text_clear(fig, ax, t_de, [b for b in boxes if b[2] > ys + DODGE + 1e-9], 'a left')
    _, _, _, de_bot = bb_mm(fig, t_de)
    assert TOP + PH - de_bot >= 1.2, f"a: the 'denied' label sits {TOP + PH - de_bot:.2f} mm above the x axis"
    # row names start at least INDENT_MM from the figure's left edge (the letter column stands alone)
    lab_x0 = min(bb_mm(fig, t)[0] for t in ax.get_yticklabels())
    assert lab_x0 >= fs.INDENT_MM - 0.05, f'a: row names start {lab_x0:.2f} mm from the edge'

    # ---- the product bracket (FigGenie: a labelled group): a thin NEUTRAL ']' in the white right of a left, from the
    # first product row's top mark to the last one's bottom mark, arms pointing back at the rows, a nub at its middle
    # pointing at the pooled row of a right (which carries the label 'Within product')
    prod_ys = [y for k, y in rows if k != 'all']
    y_pool = (min(prod_ys) + max(prod_ys)) / 2
    reach = DODGE + (half_mm(ALLOWED) + BRACKET_PAD_MM) / pitch
    yb0, yb1 = min(prod_ys) - reach, max(prod_ys) + reach
    xb = X_LIM[1] + BRACKET_DX_MM / MM_PER_PP
    arm, nub = BRACKET_ARM_MM / MM_PER_PP, BRACKET_NUB_MM / MM_PER_PP
    br = dict(color=fs.NEUTRAL, lw=BRACKET_LW, solid_capstyle='butt', solid_joinstyle='miter', zorder=2,
              clip_on=False)
    ax.plot([xb - arm, xb, xb, xb - arm], [yb0, yb0, yb1, yb1], **br)
    ax.plot([xb, xb + nub], [y_pool, y_pool], **br)
    data_max = max(b[1] for b in boxes)                   # the rightmost CI end of a left
    assert (xb - arm - data_max) * MM_PER_PP >= 2.0, 'a: the bracket crowds the rightmost interval'

    # ---- right: the difference, pooled within product (level with the bracket's middle) and crude (summary row)
    assert D_LIM[0] < 100 * min(fs.stat(k + '/' + f[1]) for _, k, f, _, _ in D_ROWS) and \
        100 * max(fs.stat(k + '/' + f[2]) for _, k, f, _, _ in D_ROWS) <= D_HI
    assert min(fs.stat(k + '/' + f[1]) for _, k, f, _, _ in D_ROWS) > 0      # caption: both intervals exclude zero
    ax2 = fs.axes_mm(fig, AR_X0, TOP, AR_PW, PH)
    ax2.set_ylim(*ylim)
    ax2.set_xlim(*D_LIM)
    fs.signed_ticks(ax2, list(range(D_LO, D_HI + 1, D_STEP)), 'x')
    ax2.spines['bottom'].set_bounds(D_LO, D_HI)
    ax2.spines['left'].set_visible(False)                # rows are a left's rows; the zero rule is drawn as data
    ax2.set_yticks([])
    ax2.set_xlabel(D_TITLE)
    y_of = {'crude': y_last, 'pooled': y_pool}
    # the crude difference is exactly the summary row's gap (Newcombe's estimate is p1 - p2)
    cr = fs.stat('fig3/d/mh_by_product/crude')
    assert abs(100 * cr['diff'] - (summary[0][0] - summary[1][0])) < 1e-9
    # the zero rule (no difference): solid NEUTRAL, only over the rows that carry a difference (from half a pitch above
    # the pooled row down to the axis), under every mark
    z_top = y_pool - ZERO_ABOVE
    ax2.plot([0, 0], [z_top, ylim[0]], color=fs.NEUTRAL, lw=ZERO_LW, solid_capstyle='butt', zorder=1, clip_on=False)
    boxes2, est = [(0.0, 0.0, z_top, ylim[0], ZERO_LW / fs.PT_PER_MM / 2)], {}
    dia = []
    for name, key, (fe, flo, fhi), filled, _ in D_ROWS:
        rd, rlo, rhi = (100 * reg_only(f'{key}/{f}') for f in (fe, flo, fhi))
        assert rhi <= D_LIM[1] - 2.0 / MM_PER_PP     # >= 2 mm air at the axis end
        y = y_of[name]
        ci_h(ax2, y, rlo, rhi, fs.SP_FG)
        mark(ax2, rd, y, dict(marker='D', ms=MS_DIA, mfc=fs.SP_FG if filled else fs.SURFACE, mec=fs.SP_FG,
                              mew=MEW if filled else DIA_OPEN_MEW))
        boxes2.append((rlo, rhi, y, y, CI_LW / fs.PT_PER_MM / 2))
        dia.append((rd, rd, y, y, DIA_HALF_MM))
        est[name] = (rd, y)
    # one direct label per diamond, centred above it (as a left's summary-row labels); the label's box bottom (its
    # descender: the p of 'product') clears the diamond's top by LBL_GAP_MM, checked against every mark of a right
    off_dia = (DIA_HALF_MM + LBL_GAP_MM) / pitch
    labs2 = []
    for name, _, _, _, lab in D_ROWS:
        rd, y = est[name]
        t = ax2.text(rd, y - off_dia, lab, ha='center', va='bottom', fontsize=fs.FS['label'], color=fs.SP_FG)
        text_clear(fig, ax2, t, boxes2 + dia, 'a right', pad_mm=LBL_GAP_MM - 0.05)
        labs2.append(t)
    # the zero rule's top sits level with the pooled label's top (the rule spans exactly the labelled rows)
    _, _, pool_top, _ = bb_mm(fig, labs2[0])
    z_top_mm = TOP + (z_top + EDGE_TOP) * pitch
    assert abs(z_top_mm - pool_top) <= 1.5, (z_top_mm, pool_top)
    x0a, _, bot_l = within_panel(fig, ax, 'a left', left_min=fs.INDENT_MM - 0.05)
    _, x1, bot_r = within_panel(fig, ax2, 'a right')
    title_bot = bb_mm(fig, ax.xaxis.label)[3]             # a's two x titles share one line (b's is put on it)
    assert abs(bb_mm(fig, ax2.xaxis.label)[3] - title_bot) < 0.02
    for t in labs2:
        assert bb_mm(fig, t)[1] <= A_W - 0.3, f'a right: label {t.get_text()!r} leaves the panel'
    inner = AR_X0 - (bb_mm(fig, ax)[1])
    # the bracket's nub stays clear of a right's tick labels and plot
    assert AR_X0 - (AL_X0 + (xb + nub - X_LIM[0]) * MM_PER_PP) >= 2.5, 'a: the bracket nub crowds a right'
    # alignment (nature-figure gate, DESIGN_V7 section 9): a's two plots share their top, baseline and rows, and one
    # percentage point has the same length in both (and in b)
    assert ax.get_position().bounds[1::2] == ax2.get_position().bounds[1::2] and ax.get_ylim() == ax2.get_ylim()
    for a_, (lo_, hi_) in ((ax, X_LIM), (ax2, D_LIM)):
        w_mm = a_.get_position().width * A_W
        assert abs(w_mm / (hi_ - lo_) - MM_PER_PP) < 1e-9 and a_.get_xlim() == (lo_, hi_)
    no_overlaps(fig, 'a')
    assert not sp_lint.lint_fig(fig, 'fig3a_default'), 'sciplot lint: fix or justify every warning'
    fs.save_panel(fig, os.path.join(PANELS, 'fig3a_default.pdf'))
    return x1, inner, pitch, max(bot_l, bot_r), title_bot


# ------------------------------------------------------------------------------------------------ panel b
def panel_b(a_title_bot):
    """The same stores by declared purpose: per purpose, 'allowed' (brick circle) and 'denied' (slate square) side by
    side, Wilson CIs in the marker colour, a pale brick band between them. Returns the left edge (mm) of everything
    drawn, the label gaps (mm) and the bottom of b's content (mm)."""
    fig = fs.panel(B_W, FIG_H)
    ax = fs.axes_mm(fig, B_YR, TOP, B_PW, PH)
    fs.pct_axis(ax, 'y', 0, 100, 25)
    ax.set_ylabel(B_TITLE)
    n = len(PURPOSES)
    ax.set_xlim(-0.5, n - 0.5)
    ax.set_xticks(range(n))
    ax.set_xticklabels([lab for _, lab in PURPOSES], fontsize=fs.FS['cat'], color=fs.SP_FG)
    assert all('\n' not in lab for _, lab in PURPOSES), 'b: category names are one line (critic r1 of v7)'
    ax.tick_params(axis='x', length=0, pad=3.0)          # categorical: no tick marks
    # the categories' group name (as a's 'Consent product'; DESIGN_V7 section 7.1 style): 7 pt SP_MUTED, so it never
    # reads as a second line of the SP_FG category names above it (critic r1 of v7), on the baseline of a's x titles
    ax.set_xlabel(B_XTITLE, color=fs.SP_MUTED)
    lp = ax.xaxis.labelpad
    for _ in range(3):
        ax.xaxis.labelpad = lp + (a_title_bot - bb_mm(fig, ax.xaxis.label)[3]) * fs.PT_PER_MM
        lp = ax.xaxis.labelpad
    assert abs(bb_mm(fig, ax.xaxis.label)[3] - a_title_bot) < 0.02, 'b: x title off the baseline of a\'s titles'
    cat_mm = B_PW / n
    dx = B_DX_MM / cat_mm                                 # the pair's half split in category units
    boxes = []
    for i, (m, _) in enumerate(PURPOSES):
        a, d = share(f'fig3/d/opt_out/{m}'), share(f'fig3/d/opt_in/{m}')
        assert d[0] < a[0], m                     # caption: in every purpose 'denied' fired less often
        assert a[3] >= fs.stat('design/min_stores_row') and d[3] >= fs.stat('design/min_stores_row')
        band(ax, i - dx, i + dx, d[0], a[0])
        boxes.append((i - dx, i + dx, d[0], a[0], 0.0))
        for (p, lo, hi, _n), st, xx in ((a, ALLOWED, i - dx), (d, DENIED, i + dx)):
            assert lo * MM_PER_PP >= 1.95         # ~2 mm of air above the 0 % baseline (the 'marketing' / 'denied'
                                                  # interval ends 2.00 mm above it at 0.48 mm per pp)
            ci_v(ax, xx, lo, hi, st['color'])
            mark(ax, xx, p, st)
            boxes.append((xx, xx, lo, hi, half_mm(st)))
    # the pair's two marks never touch, and a pair stays a pair (well inside its category)
    assert 2 * B_DX_MM - 2 * half_mm(ALLOWED) >= 2.0 and 2 * B_DX_MM <= 0.3 * cat_mm
    # b shares a's plot top and baseline and its scale (DESIGN_V7 section 9)
    assert abs(ax.get_position().height * FIG_H - PH) < 1e-9 and abs((1 - ax.get_position().y1) * FIG_H - TOP) < 1e-9
    assert ax.get_ylim() == (0, PCT_HI) and abs(PH / (ax.get_ylim()[1] - ax.get_ylim()[0]) - MM_PER_PP) < 1e-9
    x0, _, bot = within_panel(fig, ax, 'b')
    gaps = label_gaps(fig, ax)
    assert min(gaps) >= 3.0, f'b: category labels {gaps} mm apart (crowded)'
    # the group name clears the one-line category names by more than the house label pad (2.5 pt = 0.88 mm)
    tick_bot = max(bb_mm(fig, t)[3] for t in ax.get_xticklabels() if t.get_text())
    title_top = bb_mm(fig, ax.xaxis.label)[2]
    assert title_top - tick_bot >= 1.0, f'b: x title {title_top - tick_bot:.2f} mm under the category names'
    no_overlaps(fig, 'b')
    assert not sp_lint.lint_fig(fig, 'fig3b_purpose'), 'sciplot lint: fix or justify every warning'
    fs.save_panel(fig, os.path.join(PANELS, 'fig3b_purpose.pdf'))
    return x0, gaps, bot, title_top - tick_bot


if __name__ == '__main__':
    check_composite()
    fs.reset_registry()
    with fs.v7_context():                        # scoped style, restored on exit
        a_right, inner, pitch, a_bot, a_title_bot = panel_a()
        b_left, b_gaps, b_bot, b_title_gap = panel_b(a_title_bot)
    # grouping: the white space between a and b is clearly wider than the gap inside a
    outer = (A_W - a_right) + fs.GUTTER_MM + b_left
    # the canvas is no taller than its content needs (<= 1.5 mm of white under the lowest axis title)
    assert FIG_H - max(a_bot, b_bot) <= 1.5, f'canvas {FIG_H - max(a_bot, b_bot):.2f} mm taller than its content'
    fs.write_registry(os.path.join(PANELS, 'fig3_numbers.csv'))
    print(f'wrote panels and registry ({FIG_W:g} x {FIG_H:g} mm; {MM_PER_PP:g} mm per percentage point in every plot; '
          f'a {A_W:g} wide: left plot {AL_PW:.2f} x {PH:g} at x {AL_X0:g}, difference plot {AR_PW:.2f} at x '
          f'{AR_X0:.2f}, row pitch {pitch:.2f} mm, band {2 * DODGE * pitch:.2f} mm; b {B_W:g} wide: plot {B_PW:g} x '
          f'{PH:g}, pair split {2 * B_DX_MM:g} mm; white space a->b {outer:.1f} mm, between a\'s plots {inner:.1f} mm; '
          f'label gaps b ' + ', '.join(f'{g:.1f}' for g in b_gaps) + f' mm; b title gap {b_title_gap:.2f} mm; '
          f'content bottom a {a_bot:.2f}, b {b_bot:.2f} of {FIG_H:g} mm)')
