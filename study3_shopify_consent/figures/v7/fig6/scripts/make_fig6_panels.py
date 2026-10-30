"""Figure 6 panels, v7 (binding spec ../../DESIGN_V7.md; worked example ../../fig1): what reaches the ad vendors -- the
landing URL, including a creator's per-video code -- and how stable the measurements behind it are. The sciplot clean
theme (mmd-ahd/scientific-figure-skill; read, never executed) through fs.v7_context(), plus the bake-off grafts.

Figure contract (DESIGN_V7 section 1; venue Computers & Security, 190 mm double column):
  figure  ad vendors receive the landing URL, including a creator's per-video code, and the measurements behind this
          repeat across loads and agree with a screenshot audit;
  a       (hero: mechanism + one instance; the full top row) Store C. Left, fig6a_path.tex: the code's path as a small
          line drawing on Fig. 1a's grammar (nested regions on the page / sandbox grounds, left-aligned; the creator's
          link enters the browser, the page hands its URL to the sandboxed pixels, brick paths leave the browser for
          the ad vendors, each vendor that received the code named at the head of the path that reached it; the
          page's other routes in grey). Right, fig6a_loads.pdf (here): one row per load, grouped 'Before
          any choice' / 'After a refusal'; x = ad vendors that received the code (a count, 0-5); brick circle = from
          a sandbox (LEAK, consent lost), grey square = by any route (NEUTRAL, context); a LIGHT 0.5 pt line joins
          the two counts of a load (DESIGN_V7 section 5: paired values). A two-entry key above the box in sentence
          case ('From a sandbox', 'Any route'), muted, frameless;
  b       (the population of creator-linked stores) three shares with Wilson 95% CIs, one row per category with the
          labels at the left (DESIGN_V7 section 8.1; v6 drew it vertically): the code reached any ad vendor / a
          vendor other than Google (grey squares: by any route) / an ad vendor from a sandbox (brick circle) -- a's
          marks. The rows sit at c's and d's row pitch, top-aligned with their first rows;
  c       (the population, by vendor) sandboxed ad beacons carrying the full landing URL, by vendor group (Default
          load): dark grey circles (MID #6e6e6e, as Fig. S2a's groups) with Korn-Graubard 95% CIs clustered by store;
          the all-vendor share is a summary row set apart below a gap (section 8.1), and its 95% CI is carried up
          through the vendor rows as a pale brick band (TINT LEAK, square, no outline, under every mark): the key-area
          band of the main estimates in Figs S2, S3 and S5 (these beacons are sandboxed requests sent before any
          choice, i.e. consent lost), so each vendor group reads against all vendors;
  d       (control / robustness) agreement between loads and with a screenshot audit: dark grey circles (MID) with
          Wilson 95% CIs on a truncated axis (ticks 85-100; it does not start at zero, so the six checks at 96-100%
          stay legible): the axis carries a break mark at its left end and the caption says so; each group named once
          in muted 7 pt above its rows.
If covering a panel would not weaken the argument it would be merged or moved; each panel above carries a distinct role.

Categorical axes (a's plot, b, c, d; as Figs 3 and 4 and the supplementary dot plots): no left spine and no y ticks --
the rows are named at the left, ROW_GAP mm before the bottom spine's left end; every panel's rows sit on one grid
(ROW_YLIM: first row ROW_YLIM[1] slots below the box top, last row ROW_LAST, so one row pitch, PH / 8.8 mm, in a, b, c
and d; groups and summary rows are set apart by the same GROUP_GAP).

Layout (190 x FIG_H mm; 6 mm gutters; no outer margin): row 1 is a, full width: the drawing cell (A_DW, TikZ) and
the plot cell (A_PW) side by side, one letter. Row 2: b | c | d (b narrowed for its three rows; c, with eight rows,
the widest). Every plot box (a's plot, b, c, d) has the same top (TOP below its cell top) and height (PH), so the four
boxes share their top and their baseline across both rows.
Cells live HERE and reach fig6.tex through the generated panels/fig6_layout.tex; check_composite() asserts that
fig6.tex and fig6a_path.tex use them.

Numbers: every drawn value (dot, CI end, count) is read from analysis/outputs/stats.json or ../derived_numbers.json
and registered as a drawn mark (fmt 'mark') in panels/fig6_numbers.csv for scripts/trace_fig6.py; the only numbers
printed in the panels are axis tick labels; the drawing prints no digit. Store C stays anonymous (no domain, no real
code: the query string is a placeholder). Every panel is linted with sciplot's rules (sp_lint.lint_fig) before saving.

Run:  PATH=/opt/anaconda3/bin:$PATH python3 figures/v7/fig6/scripts/make_fig6_panels.py   (build_fig6.sh composes)
"""
import json
import os
import re
import sys

import matplotlib as mpl

HERE = os.path.dirname(os.path.abspath(__file__))
FIG6 = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG6, '..', 'style')))
import figstyle as fs  # noqa: E402
sys.path.insert(0, HERE)
import sp_lint  # noqa: E402  (sciplot step 5: lint every panel before it is saved)

PANELS = os.path.join(FIG6, 'panels')
os.makedirs(PANELS, exist_ok=True)
DERIVED_JSON = os.path.join(FIG6, 'derived_numbers.json')
_D = json.load(open(DERIVED_JSON))

# ---- composite grid (mm): one source for fig6.tex (via panels/fig6_layout.tex), fig6a_path.tex and the panels ----
FIG_W = fs.FIG_W_MM                       # 190 (Elsevier double column)
GUT = fs.GUTTER_MM                        # 6
A_H = 48.0                                # row 1: panel a (hero)
A_DW = 114.0                              # a, left: the line drawing (TikZ \PanelCanvas{114}{48})
A_PW = FIG_W - A_DW                       # a, right: the per-load plot (76)
R2_H = 48.0                               # row 2: b | c | d
B_W, C_W = 54.0, 70.0                     # b holds three rows, c eight: c takes the width (b = d)
D_W = FIG_W - B_W - C_W - 2 * GUT         # 54
FIG_H = A_H + GUT + R2_H                  # 102
assert 100.0 <= FIG_H <= 150.0            # DESIGN_V7 section 9: about 100-150 mm at 190 mm

TOP, PH = 5.5, 34.0                       # every plot box: top TOP below its cell top (below the 4.5 mm letter zone)
ROW_GAP = 3.0                             # row names end this far left of the bottom spine's left end (as fig4's
                                          # ROW_PAD; no left spine, no y ticks: the rows are named, not measured)
ROW_YLIM = (8.2, -0.6)                    # every categorical panel (a's plot, b, c, d): y limits in row slots, so
ROW_LAST = 7.6                            # one row pitch PH / 8.8 = 3.86 mm everywhere; the last row of a, c and d
GROUP_GAP = 0.6                           # sits on ROW_LAST; groups and summary rows are set apart by GROUP_GAP
PITCH_MM = PH / (ROW_YLIM[0] - ROW_YLIM[1])
RIGHT_PAD = 0.5                           # a box's last tick label ends this far inside its cell
CI_LW = fs.LW['error']                    # 0.75 pt, no caps (DESIGN_V7 section 4)
MK, MEW = fs.V7_LW['marker'], fs.V7_LW['mew']               # 3.5 pt markers, 0.6 pt edge (sciplot)
SQ = MK * 0.9                             # a square of about the circle's visual weight
LINK_LW = 0.5                             # the LIGHT line joining a load's two counts (section 5, paired values)
MID = fs.ORIGIN['open_pixel']['facecolor']  # the registry's mid grey (DESIGN_V7 section 8.7; Fig. S2a's group dots)
assert MID == '#6e6e6e'
BAND = fs.TINT['LEAK']                    # c: the all-vendor CI carried through the rows (the S2 / S3 / S5 band)

# marks: brick circle = the code left from a sandbox (LEAK, the protagonist); grey square = by any route (context);
# the same two marks in a and in b. c and d: dark grey circles (MID), as Fig. S2a's groups on their pale brick band.
SBX = dict(marker='o', ms=MK, mfc=fs.LEAK, mec=fs.LEAK, mew=MEW, color=fs.LEAK)
ANY = dict(marker='s', ms=SQ, mfc=fs.NEUTRAL, mec=fs.NEUTRAL, mew=MEW, color=fs.NEUTRAL)
DOT = dict(marker='o', ms=MK, mfc=MID, mec=MID, mew=MEW, color=MID)


# ------------------------------------------------------------------------------------------------ numbers
def _dv(key):
    name, _, rest = key.partition('/')
    return fs._walk(_D[name]['value'], rest) if rest else _D[name]['value']


def DN(key, f='int'):
    """Render a number from fig6/derived_numbers.json ('record/path', the 'value' level implied) and register it
    (used by the caption script; the panels print no numbers)."""
    v = _dv(key)
    s = fs.render(v, f)
    fs._REG.append(dict(text=s, shown=fs.typo(s), source='fig6_derived', key=key, fmt=f, value=json.dumps(v)))
    return fs.typo(s)


def mark6(key):
    """Register a fig6 derived value that is drawn but not printed (a dot position, a CI end, a count)."""
    v = _dv(key)
    fs._REG.append(dict(text='', shown='', source='fig6_derived', key=key, fmt='mark', value=json.dumps(v)))
    return v


def reg_only(key):
    """Register a stats.json value that is drawn but not printed."""
    fs._REG.append(dict(text='', shown='', source='stats', key=key, fmt='mark', value=json.dumps(fs.stat(key))))
    return fs.stat(key)


def share(key, lo='lo', hi='hi', src='stats'):
    """A share record in percentage units (p, lo, hi), each registered as a drawn mark."""
    get = reg_only if src == 'stats' else mark6
    return tuple(100 * get(f'{key}/{f}') for f in ('p', lo, hi))


# ------------------------------------------------------------------------------------------------ geometry helpers
def text_w_mm(s, size=fs.FS['cat']):
    f = fs.panel(80, 20)
    t = f.text(0, 0.5, s, fontsize=size)
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
    """Every pair of visible texts in the panel stays at least `pad` mm apart (the panel-level collision audit;
    qa_check repeats it on the composite with Arial ink boxes)."""
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
    """The plot and all its labels end inside the panel, clear of its edges."""
    W, H = fs.size_mm(fig)
    x0, x1, t, b = bb_mm(fig, ax)
    assert x0 >= 0.8 and x1 <= W - 0.3 and t >= 0.3 and b <= H - 0.3, \
        f'{name}: plot or labels leave the panel ({x0:.2f}, {x1:.2f}, {t:.2f}, {b:.2f})'
    return x0, x1


def x_mm(fig, ax, xd):
    """Panel mm (from the left) of data x."""
    return ax.transData.transform((xd, 0))[0] / fig.dpi * 25.4


def y_mm(fig, ax, yd):
    """Panel mm (from the top) of data y."""
    return fs.size_mm(fig)[1] - ax.transData.transform((0, yd))[1] / fig.dpi * 25.4


def mark(ax, x, y, st, zorder=4):
    ax.plot([x], [y], ls='none', marker=st['marker'], ms=st['ms'], mfc=st['mfc'], mec=st['mec'], mew=st['mew'],
            zorder=zorder, clip_on=False)


def hci(ax, y, lo, hi, color, zorder=3):
    """A horizontal 95% CI (0.75 pt, uncapped) in the colour of its mark."""
    ax.plot([lo, hi], [y, y], color=color, lw=CI_LW, solid_capstyle='butt', zorder=zorder, clip_on=False)


def row_axis(ax, ys, labels, spine_left_mm=None):
    """Categorical y axis (as Figs 3 and 4 and the supplementary dot plots): no left spine and no tick marks; 7 pt row
    labels in the text colour, right-aligned ROW_GAP mm before the bottom spine's left end (spine_left_mm: its distance
    from the box's left edge, 0 when the spine starts at the box); the rows on the shared grid ROW_YLIM."""
    ax.set_ylim(*ROW_YLIM)
    ax.spines['left'].set_visible(False)
    ax.set_yticks(list(ys))
    ax.set_yticklabels(labels, fontsize=fs.FS['cat'], color=fs.SP_FG)
    ax.tick_params(axis='y', length=0, pad=(ROW_GAP - (spine_left_mm or 0.0)) * fs.PT_PER_MM)
    assert all(ROW_YLIM[1] < y <= ROW_LAST + 1e-9 for y in ys)


def group_slots(groups, gap=GROUP_GAP):
    """Row positions for grouped rows: each group's name in its own slot above its rows, GROUP_GAP extra space
    before every group after the first. Returns (row ys, header ys)."""
    ys, head_y, y = [], [], 0.0
    for g, rows in enumerate(groups):
        if g:
            y += gap
        head_y.append(y)
        y += 1.0
        for _ in rows:
            ys.append(y)
            y += 1.0
    return ys, head_y


def group_names(fig, ax, names, head_y):
    """Each group named once, left-aligned at the indent on its own slot: 7 pt, SP_MUTED (secondary text)."""
    cap = fs.FS['cat'] * fs.CAP_EM / fs.PT_PER_MM
    return [fs.text_mm(fig, fs.INDENT_MM, y_mm(fig, ax, yh) + cap / 2, h, size=fs.FS['cat'], color=fs.SP_MUTED)
            for h, yh in zip(names, head_y)]


def label_end(labels):
    """Right end (mm in the cell) of the widest row or group label, set from the INDENT."""
    return fs.INDENT_MM + max(text_w_mm(n) for n in labels)


def box_left(labels):
    """The bottom spine's left end (mm in the cell): ROW_GAP after the widest row or group label."""
    return label_end(labels) + ROW_GAP


def axis_line(fig, x0, x1, y):
    """A piece of the bottom axis line drawn by hand (mm in the panel): the spine's colour and width, butt caps."""
    (fx0, fy), (fx1, _) = fs.fig_xy(fig, x0, y), fs.fig_xy(fig, x1, y)
    fig.add_artist(mpl.lines.Line2D([fx0, fx1], [fy, fy], color=fs.SP_AXIS, lw=fs.V7_LW['axis'],
                                    solid_capstyle='butt', transform=fig.transFigure))


def right_margin(last_tick):
    """Box right edge -> cell right edge (mm): half the last tick label plus RIGHT_PAD."""
    return text_w_mm(last_tick, fs.FS['tick']) / 2 + RIGHT_PAD


def lint_save(fig, name):
    assert not sp_lint.lint_fig(fig, name), f'sciplot lint ({name}): fix or justify every warning'
    fs.save_panel(fig, os.path.join(PANELS, name + '.pdf'))


# ------------------------------------------------------------------------------------------------ panel a (plot)
A_GROUPS = [('Before any choice', [('A0', 'Default'), ('A0r', 'Default repeat'), ('A1pre', 'Decline, before click')]),
            ('After a refusal', [('A1after', 'Decline, after click'), ('A2', 'GPC'), ('A2r', 'GPC repeat')])]
A_LOADS = [ld for _, rows in A_GROUPS for ld in rows]
A_KEY = (('From a sandbox', SBX), ('Any route', ANY))      # laid out left to right, right-aligned to the box;
                                                           # sentence case, as every key of Figs 3-5 and S5-S10
A_XTITLE = 'Ad vendors that received the code'
A_XMAX = 5
A_AIR = 0.2                                # x units of air past 0 and 5 inside the box (the spine is bounded to 0-5)
A_NAME_BASE = 4.3                          # baseline (mm) of fig6a_path.tex's level-1 name: the key shares it
A_VENDOR_NAME = {'google_ads': 'Google Ads', 'google_merchant_center': 'Google Merchant Center', 'tiktok': 'TikTok'}


def a_counts():
    """Store C per load: (vendors that got the code by any route, of them from a sandbox), registered as drawn marks.
    The derived grid must agree with stats.json wherever stats.json holds the cell, and with the vendor matrix."""
    cl = 'fig6/b/store_c'
    stat_any = {'A0': f'{cl}/A0/n_vendors_with_token', 'A0r': f'{cl}/A0r/n_vendors_with_token',
                'A1pre': 'fig6/b/store_c_pre_click/n_vendors',
                'A1after': 'fig6/b/store_c_after_decline/n_vendors',
                'A2': f'{cl}/A2/n_vendors_with_token', 'A2r': f'{cl}/A2r/n_vendors_with_token'}
    stat_sbx = {'A1pre': 'fig6/b/store_c_pre_click/n_vendors_sandboxed',
                'A1after': 'fig6/b/store_c_after_decline/n_vendors_sandboxed'}
    out = {}
    m = _D['fig6a_store_c_vendors']['value']
    for c, _ in A_LOADS:
        n_any = mark6(f'fig6a_store_c_grid/{c}/vendors_code')
        n_sbx = mark6(f'fig6a_store_c_grid/{c}/vendors_code_sbx')
        assert n_any == fs.stat(stat_any[c]), c
        if c in stat_sbx:
            assert n_sbx == fs.stat(stat_sbx[c]), c
        assert sum(r > 0 for r in m['routes'][c]) == n_any and sum(r == 2 for r in m['routes'][c]) == n_sbx, c
        assert 0 <= n_sbx < n_any <= A_XMAX                 # the two marks of a load never coincide
        out[c] = (n_any, n_sbx)
    # the groups: the same counts in the three loads before any choice, none from a sandbox after a refusal
    assert len({out[c] for c, _ in A_GROUPS[0][1]}) == 1 and all(out[c][1] == 0 for c, _ in A_GROUPS[1][1])
    # the drawing's two leak paths are the two vendors that received the code from a sandbox before any choice
    sbx = [v for v, r in zip(m['vendors'], m['routes']['A0']) if r == 2]
    assert sbx == ['google_ads', 'tiktok'] and out['A0'][1] == len(sbx)
    return out


def a_box():
    """(left, width, air) of a's plot box in its cell: the bottom spine runs 0-5 from ROW_GAP after the widest label
    to the box's right end less the air; the box adds A_AIR units of air at both ends (air: mm)."""
    s = box_left([n for _, n in A_LOADS] + [g for g, _ in A_GROUPS])      # x = 0
    r = A_PW - right_margin(str(A_XMAX))                                   # box right (x = 5 + A_AIR)
    u = (r - s) / (A_XMAX + A_AIR)                                         # mm per vendor
    left = s - A_AIR * u
    return left, r - left, A_AIR * u


def panel_a():
    """a, right: one row per load of Store C in two named groups; brick circle = vendors that got the code from a
    sandbox, grey square = by any route, joined by a LIGHT line; a two-entry key above the box."""
    cnt = a_counts()
    fig = fs.panel(A_PW, A_H)
    left, width, air = a_box()
    ax = fs.axes_mm(fig, left, TOP, width, PH)
    ys, head_y = group_slots([rows for _, rows in A_GROUPS])
    assert abs(ys[-1] - ROW_LAST) < 1e-9 and head_y[0] == 0.0
    row_axis(ax, ys, [n for _, n in A_LOADS], spine_left_mm=air)
    ax.set_xlim(-A_AIR, A_XMAX + A_AIR)
    ax.spines['bottom'].set_bounds(0, A_XMAX)                # as fig3: the count axis runs exactly 0-5
    ax.set_xticks(list(range(A_XMAX + 1)))
    ax.set_xticklabels([str(v) for v in range(A_XMAX + 1)])
    ax.set_xlabel(A_XTITLE)
    for (c, _), y in zip(A_LOADS, ys):
        n_any, n_sbx = cnt[c]
        ax.plot([n_sbx, n_any], [y, y], color=fs.LIGHT, lw=LINK_LW, solid_capstyle='butt', zorder=2)
        mark(ax, n_any, y, ANY, zorder=4)
        mark(ax, n_sbx, y, SBX, zorder=5)
    names = group_names(fig, ax, [g for g, _ in A_GROUPS], head_y)
    # the key (sciplot: frameless, ordered like the data, muted 7 pt, marks in the data colour): above the box,
    # right-aligned to its right end, on one baseline (as Fig. 1b's tick-height key)
    W, H = fs.size_mm(fig)
    kx, ky = left + width, A_NAME_BASE                      # on the baseline of the drawing's 'Store C in the browser'
    cap = fs.FS['legend'] * fs.CAP_EM / fs.PT_PER_MM
    keys = []
    for name, st in reversed(A_KEY):                        # laid out right to left
        t = fs.text_mm(fig, kx, ky, name, ha='right', color=fs.SP_MUTED, size=fs.FS['legend'])
        x0, _, _, _ = bb_mm(fig, t)
        xm = x0 - 1.5
        fx, fy = fs.fig_xy(fig, xm, ky - cap / 2)
        fig.add_artist(mpl.lines.Line2D([fx], [fy], ls='none', marker=st['marker'], ms=st['ms'], mfc=st['mfc'],
                                        mec=st['mec'], mew=st['mew'], transform=fig.transFigure))
        keys.append((t, xm))
        kx = xm - 3.0
    # guards: the key stays above the box, clear of the first group name; the marks at 0 clear the row names by
    # >= 2 mm and the marks at 5 stay inside the box; the rows sit at the shared pitch
    for t, _ in keys:
        _, _, kt, kb = bb_mm(fig, t)
        assert kt >= 0.3 and kb <= TOP - 0.3, 'a: the key leaves its band above the box'
    _, nx1, nt, _ = bb_mm(fig, names[0])
    assert keys[-1][1] - 1.5 > nx1 + 3.0 or nt > TOP, 'a: the key crowds the first group name'
    r_mm = MK / fs.PT_PER_MM / 2
    lab_end = label_end([n for _, n in A_LOADS] + [g for g, _ in A_GROUPS])
    assert x_mm(fig, ax, 0) - r_mm - lab_end >= 2.0 and left + width - (x_mm(fig, ax, A_XMAX) + r_mm) >= 0.5
    assert abs(x_mm(fig, ax, 0) - (lab_end + ROW_GAP)) < 1e-6
    assert abs((y_mm(fig, ax, ys[1]) - y_mm(fig, ax, ys[0])) - PITCH_MM) < 1e-6
    within_panel(fig, ax, 'a')
    no_overlaps(fig, 'a')
    lint_save(fig, 'fig6a_loads')
    return left, width


# ------------------------------------------------------------------------------------------------ panel b
B_ROWS = [('creator_token_reached_ad_vendor_A0', 'Any ad vendor', ANY),
          ('creator_token_reached_nongoogle_A0', 'Non-Google vendor', ANY),
          ('creator_token_reached_sandboxed_A0', 'From a sandbox', SBX)]
B_XTITLE = 'Creator-linked stores (%)'


def panel_b():
    """Creator-linked stores, Default load: three shares, one row each, with Wilson 95% CIs in the colour of their
    marks (a's marks). The rows sit at the shared pitch, top-aligned with c's and d's first rows (the critics' review:
    b's rows were spread over the whole box). Returns the box (left, width) in the cell."""
    fig = fs.panel(B_W, R2_H)
    left = box_left([n for _, n, _ in B_ROWS])
    width = B_W - right_margin('100') - left
    ax = fs.axes_mm(fig, left, TOP, width, PH)
    ys = [float(i) for i in range(len(B_ROWS))]                   # slots 0, 1, 2: c's first three rows' lines
    row_axis(ax, ys, [n for _, n, _ in B_ROWS])
    fs.pct_axis(ax, 'x', 0, 100, 25)
    ax.set_ylim(*ROW_YLIM)                                       # (pct_axis touches x only; kept explicit)
    assert abs((y_mm(fig, ax, ys[1]) - y_mm(fig, ax, ys[0])) - PITCH_MM) < 1e-6
    ax.set_xlabel(B_XTITLE)
    b = 'fig6/b'
    for y, (k, _, st) in zip(ys, B_ROWS):
        p, lo, hi = share(f'{b}/{k}')
        assert 0 < lo < p < hi < 100
        hci(ax, y, lo, hi, st['color'])
        mark(ax, p, y, st)
    # nested shares: sandbox <= any ad vendor and non-Google <= any ad vendor (the caption reads them as subsets)
    ks = [fs.stat(f'{b}/{k}/k') for k, _, _ in B_ROWS]
    assert ks[0] >= ks[1] and ks[0] >= ks[2]
    within_panel(fig, ax, 'b')
    no_overlaps(fig, 'b')
    lint_save(fig, 'fig6b_creators')
    return left, width


# ------------------------------------------------------------------------------------------------ panel c
C_REF = 'fig6/a/sandboxed_A0'             # all vendors (the same beacons, pooled)
C_REF_LABEL = 'All vendors'


def c_rows():
    nmin = fs.stat('design/min_stores_row')
    return [v for v in fs.VENDOR_ORDER if fs.stat(f"fig6/a/{v.replace('/', '~1')}/Default/n_stores") >= nmin]


def panel_c():
    """Full landing URL in sandboxed ad beacons by vendor group (Default load): dark grey circles, Korn-Graubard 95%
    CIs clustered by store; the all-vendor share as a summary row set apart below a gap, its 95% CI carried up through
    the vendor rows as a pale brick band (TINT LEAK; the key-area band of Figs S2, S3 and S5). Returns the vendor rows."""
    fig = fs.panel(C_W, R2_H)
    rows = c_rows()
    left = box_left(rows + [C_REF_LABEL])
    width = C_W - right_margin('100') - left
    ax = fs.axes_mm(fig, left, TOP, width, PH)
    ys = [float(i) for i in range(len(rows))]
    y_all = ys[-1] + 1.0 + GROUP_GAP
    assert abs(y_all - ROW_LAST) < 1e-9, 'c: the summary row must sit on the shared last row line'
    row_axis(ax, ys + [y_all], rows + [C_REF_LABEL])
    fs.pct_axis(ax, 'x', 0, 100, 25)
    ax.set_ylim(*ROW_YLIM)
    ax.set_xlabel('Beacons with the full landing URL (%)')
    for v, y in zip(rows, ys):
        key = f"fig6/a/{v.replace('/', '~1')}/Default"
        p, lo, hi = share(key, 'kg_lo', 'kg_hi')
        assert 0 < lo < p < hi < 100
        hci(ax, y, lo, hi, MID)
        mark(ax, p, y, DOT)
    p, lo, hi = share(C_REF)                                # resampling stores (stats.json lo / hi)
    assert 0 < lo < p < hi < 100
    hci(ax, y_all, lo, hi, MID)
    mark(ax, p, y_all, DOT)
    # the summary's CI carried up through the vendor rows (DESIGN_V7 section 3.3, key area; as Figs S2, S3, S5): a
    # pale pre-mixed brick ground (never alpha), square, no outline, under every mark, the plot's full height; its
    # edges are exactly the summary row's interval ends (the same registered lo / hi)
    ax.add_patch(mpl.patches.Rectangle((lo, ROW_YLIM[1]), hi - lo, ROW_YLIM[0] - ROW_YLIM[1], facecolor=BAND,
                                       edgecolor='none', zorder=0.5))
    within_panel(fig, ax, 'c')
    no_overlaps(fig, 'c')
    lint_save(fig, 'fig6c_url')
    return rows, left, width


# ------------------------------------------------------------------------------------------------ panel d
D_GROUPS = [
    ('Between loads', [
        ('Default vs repeat', 'fig6', 'fig6d_agreement/A0_vs_A0r'),
        ('GPC vs repeat', 'fig6', 'fig6d_agreement/A2_vs_A2r'),
        ('GPC vs Brave', 'fig6', 'fig6d_agreement/A2_vs_V1'),       # emulated GPC vs Brave's native GPC
    ]),
    ('Screenshot audit', [                                          # crawler vs saved screenshots (Fig. S4)
        ('Banner detected', 'stats', 'supp/S4/banner_precision'),
        ('Reject button', 'stats', 'supp/S4/reject_agreement'),
        ('Click outcome', 'stats', 'supp/S4/click_flag_agreement'),
    ]),
]
D_LO, D_HI = 85, 101.5                    # the first tick (85) and the box's right end (1.5 units of headroom past 100)
D_TICKS = [85, 90, 95, 100]
D_STUB_MM, D_CUT_MM = 0.9, 0.8            # the break: a 0.9 mm stub of axis, a 0.8 mm cut between two slashes,
D_TICK0_MM = 3.0                          # then the axis again; the 85 tick 3.0 mm from the axis's left end
D_SLASH_MM = (0.45, 0.9)                  # each slash: half its width and half its height (mm), crossing the axis
D_LO_CLEAR_MM = 2.0                       # every interval's left end at least this far right of the break
D_HI_CLEAR_MM = 1.0                       # every mark's right edge at least this far inside the box end


def panel_d():
    """Agreement between loads and with the screenshot audit: dark grey circles, Wilson 95% CIs, a truncated axis
    (ticks 85-100) whose left end carries a break mark (critic: the truncation was stated only in the caption); each
    group named once in muted 7 pt, its rows under it. Returns the box (left, width) in the cell."""
    fig = fs.panel(D_W, R2_H)
    names = [n for _, rows in D_GROUPS for n, _, _ in rows]
    heads = [h for h, _ in D_GROUPS]
    left = box_left(names + heads)                          # the axis line (its stub) starts at the box's left edge
    width = D_W - right_margin('100') - left
    ax = fs.axes_mm(fig, left, TOP, width, PH)
    ys, head_y = group_slots([rows for _, rows in D_GROUPS])
    assert abs(ys[-1] - ROW_LAST) < 1e-9 and head_y[0] == 0.0
    row_axis(ax, ys, names)
    u = (width - D_TICK0_MM) / (D_HI - D_LO)                # mm per percentage point
    x_lo = D_LO - D_TICK0_MM / u                            # the box's left edge in data units
    ax.set_xlim(x_lo, D_HI)
    cut1 = left + D_STUB_MM + D_CUT_MM                      # the axis resumes here, after the cut
    ax.spines['bottom'].set_bounds(x_lo + (D_STUB_MM + D_CUT_MM) / u, 100)
    ax.spines['bottom'].set_capstyle('butt')
    ax.set_xticks(D_TICKS)
    ax.set_xticklabels([str(t) for t in D_TICKS])
    ax.set_xlabel('Agreement (%)')
    # the break mark at the axis's left end: a short stub (the axis's run from zero, compressed), a cut, and two
    # parallel slashes across the axis line at the cut's ends, in the spine's colour and width
    y_ax = TOP + PH
    axis_line(fig, left, left + D_STUB_MM, y_ax)
    sw, sh = D_SLASH_MM
    for xs in (left + D_STUB_MM, cut1):
        (fx0, fy0), (fx1, fy1) = fs.fig_xy(fig, xs - sw, y_ax + sh), fs.fig_xy(fig, xs + sw, y_ax - sh)
        fig.add_artist(mpl.lines.Line2D([fx0, fx1], [fy0, fy1], color=fs.SP_AXIS, lw=fs.V7_LW['axis'],
                                        solid_capstyle='butt', transform=fig.transFigure))
    assert abs(x_mm(fig, ax, D_LO) - (left + D_TICK0_MM)) < 1e-6 and x_mm(fig, ax, D_LO) - cut1 >= 1.0
    r_dot = MK / fs.PT_PER_MM / 2
    i = 0
    for _, rows in D_GROUPS:
        for _, src, key in rows:
            p, lo, hi = share(key, src=src)
            assert D_LO <= lo <= p <= hi + 1e-9 and hi <= 100 + 1e-9
            # honest scale: the interval ends visibly right of the break; the mark clears the box end
            assert x_mm(fig, ax, lo) - cut1 >= D_LO_CLEAR_MM, f'd: {key} interval reaches the break'
            assert left + width - (x_mm(fig, ax, p) + r_dot) >= D_HI_CLEAR_MM, f'd: {key} mark reaches the axis end'
            hci(ax, ys[i], lo, hi, MID)
            mark(ax, p, ys[i], DOT)
            i += 1
    assert abs((y_mm(fig, ax, ys[1]) - y_mm(fig, ax, ys[0])) - PITCH_MM) < 1e-6
    group_names(fig, ax, heads, head_y)
    within_panel(fig, ax, 'd')
    no_overlaps(fig, 'd')
    lint_save(fig, 'fig6d_validation')
    return left, width


# ------------------------------------------------------------------------------------------------ composite
LAYOUT = dict(FigH=FIG_H, AH=A_H, ADW=A_DW, APX=A_DW, APW=A_PW, RowTwoY=A_H + GUT, RowTwoH=R2_H,
              BW=B_W, CX=B_W + GUT, CW=C_W, DX=B_W + GUT + C_W + GUT, DW=D_W)


def layout_tex():
    """panels/fig6_layout.tex: cell sizes and positions (mm) for fig6.tex."""
    L = ['% fig6_layout.tex -- GENERATED by scripts/make_fig6_panels.py (cell sizes and positions, mm); do not edit.']
    L += [f'\\def\\{k}{{{v:g}}}' for k, v in LAYOUT.items()]
    open(os.path.join(PANELS, 'fig6_layout.tex'), 'w').write('\n'.join(L) + '\n')


def check_composite():
    """fig6.tex places the five cells by the generated macros (panels are never rescaled); the TikZ canvas of a's
    drawing is A_DW x A_H; the drawing prints no digit; its two regions share their left edge; each vendor that
    received the code is named at the head of the path that reached it (asserted against derived_numbers.json
    fig6a_store_c_vendors)."""
    tex = open(os.path.join(FIG6, 'fig6.tex')).read()
    code = '\n'.join(re.sub(r'(?<!\\)%.*', '', ln) for ln in tex.splitlines())
    want = [('Panel', 'a', r'0', r'0', r'\ADW', r'\AH', 'fig6a_path.pdf'),
            ('PanelPart', '', r'\APX', r'0', r'\APW', r'\AH', 'fig6a_loads.pdf'),
            ('Panel', 'b', r'0', r'\RowTwoY', r'\BW', r'\RowTwoH', 'fig6b_creators.pdf'),
            ('Panel', 'c', r'\CX', r'\RowTwoY', r'\CW', r'\RowTwoH', 'fig6c_url.pdf'),
            ('Panel', 'd', r'\DX', r'\RowTwoY', r'\DW', r'\RowTwoH', 'fig6d_validation.pdf')]
    got = []
    for m in re.finditer(r'\\(Panel|PanelPart)\s*(?:\{(\w)\})?\s*\{([^{}]*)\}\s*\{([^{}]*)\}\s*\{([^{}]*)\}\s*'
                         r'\{([^{}]*)\}\s*\{([^{}]*)\}', code):
        got.append((m[1], m[2] or '', m[3].strip(), m[4].strip(), m[5].strip(), m[6].strip(),
                    os.path.basename(m[7].strip())))
    assert got == want, (got, want)
    assert re.search(r'\\FigureCanvas\{\\FigH\}', code), 'fig6.tex: the canvas must be \\FigH'
    # the cells tile the figure: row 1 = drawing + plot; row 2 = b | gutter | c | gutter | d
    assert abs(A_DW + A_PW - FIG_W) < 1e-9 and abs(B_W + C_W + D_W + 2 * GUT - FIG_W) < 1e-9
    a = open(os.path.join(FIG6, 'fig6a_path.tex')).read()
    acode = '\n'.join(re.sub(r'(?<!\\)%.*', '', ln) for ln in a.splitlines())
    assert re.search(r'\\PanelCanvas\{%g\}\{%g\}' % (A_DW, A_H), acode), 'fig6a_path.tex canvas differs'
    # row 1 shares one top line (the page region = a's plot box) and one baseline (the level-1 name =
    # the plot's key)
    assert re.search(r'\\def\\yTop\{-%g\}' % TOP, acode), 'fig6a_path.tex: yTop must equal TOP'
    assert re.search(r'\\node\[regionlbl\] at \(20\.8,-%g\) \{Store C in the browser\}' % A_NAME_BASE, acode)
    texts = [re.sub(r'(\\\\)\[[^\]]*\]', r'\1', t) for t in re.findall(r'\{([^{}]*)\};', acode)]
    assert not re.search(r'\d', ''.join(texts)), 'a: the drawing prints a digit (numbers live in the caption)'
    # the two level-2 regions share their left (\\xL) and right (\\xR) edges (critic: the sandbox region was indented)
    assert re.search(r'\\draw\[region page\] \(\\xL,\\yTop\) rectangle \(\\xR,', acode), 'a: page region edges'
    assert re.search(r'\\draw\[region sbx\] \(\\xL,[^)]*\) rectangle \(\\xR,\\yBot\)', acode), 'a: sandbox region edges'
    # the code's placeholder is the caption's ('utm_campaign=desc-' + an elided identifier), never a real code
    assert 'utm\\_campaign=desc-…' in acode and 'textless' not in acode, 'a: the placeholder differs from the caption'
    # the vendors that received the code in the Default load, each named at the head of its path: the sandboxed ones
    # at the leak paths of their pixels (\\yT TikTok, \\yG Google Ads), the others at the grey arrow (\\yP); vendors
    # outside the three named products are shown by their group (Reddit/other), as in the caption
    m = _D['fig6a_store_c_vendors']['value']
    sbx = [A_VENDOR_NAME.get(v, g) for v, g, r in zip(m['vendors'], m['groups'], m['routes']['A0']) if r == 2]
    oth = list(dict.fromkeys(A_VENDOR_NAME.get(v, g) for v, g, r in zip(m['vendors'], m['groups'], m['routes']['A0'])
                             if r == 1))
    at = {}
    for y, names in re.findall(r'\\node\[vend\] at \(\\xV,\\y(\w)\) \{([^{}]*)\};', acode):
        at.setdefault(y, []).extend(n.strip() for n in re.split(r'\\\\(?:\[[^\]]*\])?', names))
    assert sorted(at.get('T', []) + at.get('G', [])) == sorted(sbx) and at.get('P', []) == oth, (at, sbx, oth)
    assert set(at) == {'P', 'T', 'G'}, at
    # each name at the head of its path: the grey arrow ends at the \\yP names, the leak arrows at \\yT and \\yG
    assert re.search(r'\\draw\[otherarr\] \(land\.east\) -- \(\\xV-0\.8,\\yP\);', acode)
    assert re.search(r'\\draw\[leakarr\] \(tt\.east\) -- \(\\xV-0\.8,\\yT\);', acode)
    assert re.search(r'\\draw\[leakarr\] \(ga\.east\) -- \(\\xV-0\.8,\\yG\);', acode)
    assert re.search(r'\\node\[regionlbl\] at \(\\xV,\\yTop-3\.5\) \{Ad vendors\};', acode)
    assert re.search(r'\(tt\) at \(\\xB,\\yT\)', acode) and re.search(r'\(ga\) at \(\\xB,\\yG\)', acode)
    assert at['T'] == ['TikTok'] and at['G'] == ['Google Ads'] and 'TikTok pixel' in texts and 'Google Ads pixel' in texts


if __name__ == '__main__':
    check_composite()
    fs.reset_registry()
    with fs.v7_context():                        # scoped style (sciplot clean theme), restored on exit
        layout_tex()
        a_left, a_width = panel_a()
        b_left, b_width = panel_b()
        rows, c_left, c_width = panel_c()
        d_left, d_width = panel_d()
    fs.write_registry(os.path.join(PANELS, 'fig6_numbers.csv'))
    print(f'wrote panels a (plot), b, c, d, fig6_layout.tex, fig6_numbers.csv (figure 190 x {FIG_H:g} mm; a: drawing '
          f'{A_DW:g} + plot {A_PW:g} mm, plot box {a_width:.1f} x {PH:g} from x {a_left:.1f}; b box {b_width:.1f} from '
          f'{b_left:.1f}; c box {c_width:.1f} from {c_left:.1f}; d box {d_width:.1f} from {d_left:.1f}; c rows: '
          f'{", ".join(rows)})')
