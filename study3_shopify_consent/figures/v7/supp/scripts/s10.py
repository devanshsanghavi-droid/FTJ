"""Supplementary Figure S10 (v7) -- Beyond Shopify: the Round 4 pilot of selected Wix, BigCommerce and
first-party-gateway sites (round4/analysis/RESULTS_R4.md section 3). Per-site rates of a pilot, not population
estimates; no test between setups is drawn.

Binding: figures/v7/DESIGN_V7.md (worked example figures/v7/fig1). fs.v7_context(): open L axes (the rows are named,
so no left spine), Arial 7 / 6 pt, markers 3.5 pt, uncapped 0.75 pt Wilson intervals, no numbers on the marks (every
k of n is in the caption). One row of four small multiples with one geometry and one 0-100 scale (DESIGN_V7 6:
compared panels share their scale); the three setups are the rows of every plot, named once at the far left. Loads
keep the project's arm shapes in the sciplot neutrals (Default filled near-black circle, Decline open square, GPC
filled grey triangle); a group of fewer than design/min_stores_row (10) sites is drawn in light grey (DESIGN_V7 8.1).
No hue anywhere: the pilot has no protagonist series. One key covers all three loads (Default, Decline, GPC; as Figs
S8a and S9a), in one row in the band above c's plot at the figure's top right; c's cell keeps white left of its plot
so that the key clears c's letter (every plot keeps the same top and width, so the rows line up).

Figure contract (DESIGN_V7 section 1): one claim -- ad requests were common before any choice, after a working Decline
and under GPC on the pilot sites. The row of plots is one comparison across measures (small multiples with one scale),
so no single plot is enlarged; a carries the row names.
  a  before any choice: banner sites on which any ad pixel fired (an ad request; Default load).
                                                                    stats round4/beyond/rates/<s>/prechoice_ad_banner
  b  after a working Decline: an ad pixel fired after the click (same or next page; left) and a first-party collect
     beacon after the click (right).                        .../<s>/decline/after_ad, .../decline/after_fp_collect
  c  under GPC: all sites with a Default and a GPC load, any ad pixel fired in each (paired sites; Default above GPC).
                                                                                                   .../<s>/gpc/A*_ad
The Partytown and Zaraz case studies (no rates) are in the caption only.
Layout (mm; must equal figS10.tex, asserted): a | b | c in one row (W_A, W_B, W_C x H); 6 mm gutters; every plot has
the same top, height and width P; b holds two plots 4 mm apart; c's plot starts C_PAD into its cell (room for the key). Drawn values are registered (fmt 'raw') in
panels/figS10_numbers.csv. Nothing but tick labels is printed as a number.
"""
import numpy as np

from s6 import (ANY_FIRED, _glyph_half, astyle, cat_y, check_composite, ci_h, dot, key_row, mark, no_digits,
                no_overlaps, off_spines, plot_box, recolor, rows_ylim, share, tw_mm, value_axis, within)
from supp_common import S, fs, finish, write_registry

R = 'round4/beyond/rates'
SETUPS = [('wix', 'Wix'), ('bigcommerce', 'BigCommerce'), ('gateway', 'First-party gateway')]
G = fs.GUTTER_MM
H = 44.0
TOP, PH = 8.0, 22.5                    # every plot: top and height (x axis at 30.5 mm); the key band is above c's
KEY_BASE = 4.0                         # c: baseline of the key (mm from the panel top)
B_INNER = 4.0                          # b: gap between its two plots
R_PAD = 2.5                            # room right of a plot for its last tick label
LAB = float(np.ceil(fs.INDENT_MM + max(tw_mm(n, fs.FS['cat']) for _, n in SETUPS) + 1.6))   # a: plot left edge
B_PAD = 2.0                            # b: plot left edge inside its cell (no row names there)
KEY_ITEMS = [('marker', astyle(a), a) for a in ('Default', 'Decline', 'GPC')]   # the one key: every load drawn
KEY_GAP, KEY_GLYPH_GAP = 2.6, 1.3      # key_row's gaps (mm)
KEY_W = sum(tw_mm(lab, fs.FS['legend']) + KEY_GLYPH_GAP + 2 * _glyph_half(k, st) for k, st, lab in KEY_ITEMS) \
    + KEY_GAP * (len(KEY_ITEMS) - 1)
LETTER_CLEAR = 4.5 + 1.0               # the letter zone (4.5 mm) plus air: the key starts right of it


def _grid():
    """P (the one plot width) and C_PAD (c's plot inset): the four plots share the row; c's cell is wide enough for
    the key right-aligned to its plot."""
    rest = fs.FIG_W_MM - 2 * G - LAB - R_PAD - (B_PAD + B_INNER + R_PAD) - R_PAD
    c_pad = B_PAD
    for _ in range(20):
        p = np.floor((rest - c_pad) / 4 * 10) / 10
        c_pad = max(B_PAD, float(np.ceil((LETTER_CLEAR + KEY_W - p) * 10) / 10))
    return p, c_pad


P, C_PAD = _grid()
W_A = LAB + P + R_PAD
W_B = B_PAD + 2 * P + B_INNER + R_PAD
W_C = fs.FIG_W_MM - W_A - W_B - 2 * G
assert W_C >= C_PAD + P + R_PAD - 1e-9
CELLS = {k: tuple(round(float(v), 1) for v in c) for k, c in
         {'a': (0, 0, W_A, H), 'b': (W_A + G, 0, W_B, H), 'c': (W_A + W_B + 2 * G, 0, W_C, H)}.items()}
DY2 = 0.2                              # c: Default above GPC
SMALL = 'design/min_stores_row'        # DESIGN_V7 8.1: fewer than 10 units -> grey


def _checks():
    """The pilot's records agree with each other (a drift in stats.json fails loudly)."""
    b = S['round4']['beyond']
    for s, _ in SETUPS:
        r = b['rates'][s]
        assert r['n_A0'] == b['funnel'][s]['captured'] == r['gpc']['n_pairs'], s
        assert (r['gpc']['A0_ad']['k'], r['gpc']['A0_ad']['n']) == (r['prechoice_ad_all']['k'], r['prechoice_ad_all']['n']), s
        assert r['prechoice_ad_banner']['n'] == r['banner']['k'], s
        assert r['decline']['after_ad']['n'] == r['decline']['after_fp_collect']['n'] == r['decline']['click_ok'], s
        assert r['gpc']['A0_ad']['n'] == r['gpc']['A2_ad']['n'], s           # caption: 'k and k of n' (paired sites)


def dot_plot(fig, x0, marks_of, title, row_labels=False):
    """One dot plot whose plot area starts x0 mm into the panel; one row per setup (Wix on top); marks_of(setup) ->
    [(arm, dy, key)]. Returns the axes, the drawn points and the small groups drawn grey."""
    ax = fs.axes_mm(fig, x0, TOP, P, PH)
    ys = np.arange(len(SETUPS), dtype=float)
    small = mark(SMALL)
    assert small == 10
    pts, greys = [], []
    for y, (s, _) in zip(ys, SETUPS):
        for z, (arm, dy, key) in enumerate(marks_of(s)):
            p, lo, hi = share(key)
            mark(key + '/k')
            n = mark(key + '/n')
            st = astyle(arm)
            if n < small:
                st = recolor(st, fs.NEUTRAL)
                greys.append(key)
            ci_h(ax, y + dy, lo, hi, st['color'], zorder=3 + z)
            dot(ax, p, y + dy, st, zorder=4 + z)
            pts += [(lo, y + dy), (hi, y + dy), (p, y + dy)]
    cat_y(ax, ys, [n for _, n in SETUPS] if row_labels else [''] * len(SETUPS))
    rows_ylim(ax, -DY2, len(SETUPS) - 1 + DY2, PH, pad_mm=2.2)           # one row layout in all four plots
    value_axis(ax, 'x', 0, 100, 25, length_mm=P)                       # one 0-100 scale in every plot
    ax.set_xlabel(title, linespacing=1.1)
    off_spines(fig, ax, pts[2::3], title)
    return ax, pts, greys


def panel_a():
    fig = fs.panel(W_A, H)
    ax, _, greys = dot_plot(fig, LAB, lambda s: [('Default', 0.0, f'{R}/{s}/prechoice_ad_banner')],
                            ANY_FIRED, row_labels=True)              # Figs 3a and 4b's title (banner sites, Default)
    assert not greys
    within(fig, ax, 'a')
    no_overlaps(fig, 'a')
    no_digits(fig, 'a')
    finish(fig, 'figS10a_prechoice')
    return plot_box(fig, ax)


def panel_b():
    fig = fs.panel(W_B, H)
    ax1, _, g1 = dot_plot(fig, B_PAD, lambda s: [('Decline', 0.0, f'{R}/{s}/decline/after_ad')],
                          'Ad pixel fired\nafter the click (%)')
    ax2, _, g2 = dot_plot(fig, B_PAD + P + B_INNER, lambda s: [('Decline', 0.0, f'{R}/{s}/decline/after_fp_collect')],
                          'First-party beacon\nafter the click (%)')
    # caption: the gateway's working Decline clicks are fewer than 10 sites, so both its b marks are grey
    assert g1 == [f'{R}/gateway/decline/after_ad'] and g2 == [f'{R}/gateway/decline/after_fp_collect'], (g1, g2)
    for ax, nm in ((ax1, 'b left'), (ax2, 'b right')):
        within(fig, ax, nm)
    no_overlaps(fig, 'b')
    no_digits(fig, 'b')
    finish(fig, 'figS10b_decline')
    return plot_box(fig, ax1)


def panel_c():
    fig = fs.panel(W_C, H)
    ax, pts, greys = dot_plot(fig, C_PAD, lambda s: [('Default', -DY2, f'{R}/{s}/gpc/A0_ad'),
                                                     ('GPC', DY2, f'{R}/{s}/gpc/A2_ad')], ANY_FIRED)
    assert not greys
    # the figure's one key, all three loads (b's open squares are the Decline load), at the top right
    _, kx0 = key_row(fig, C_PAD + P, KEY_BASE, KEY_ITEMS, gap=KEY_GAP, glyph_gap=KEY_GLYPH_GAP)
    assert kx0 >= LETTER_CLEAR - 0.05, f"c: the key reaches the letter zone ({kx0:.2f} mm)"
    within(fig, ax, 'c')
    no_overlaps(fig, 'c')
    no_digits(fig, 'c')
    finish(fig, 'figS10c_gpc')
    return plot_box(fig, ax)


if __name__ == '__main__':
    check_composite('figS10.tex', CELLS, H)
    _checks()
    fs.reset_registry()
    with fs.v7_context():
        boxes = [panel_a(), panel_b(), panel_c()]
    assert len({round(b[2], 3) for b in boxes}) == 1 and len({round(b[3], 3) for b in boxes}) == 1, 'plots misaligned'
    write_registry('figS10')
    print(f'S10: LAB {LAB:g}, P {P:g}, C_PAD {C_PAD:g}; cells a {W_A:g}, b {W_B:g}, c {W_C:g} x {H:g} mm')
