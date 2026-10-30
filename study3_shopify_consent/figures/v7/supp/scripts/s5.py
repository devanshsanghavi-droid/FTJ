"""Supplementary Figure S5 (v7) -- sensitivity of the three headline rates. Binding: ../../DESIGN_V7.md; the v7 helpers
and mark sizes of s2.py. One dot plot with 95 % intervals per headline rate (a-c), each on an open axis (a bottom
spine bounded to 0-100; the rows are named at the left, not measured), no count column and no numbers on the marks
(the caption carries every k of n), no section heads, no bold.

Figure contract (DESIGN_V7 section 1). Claim (the caption title): robustness variants moved the three headline rates
little; only changes of definition moved them much. Roles: a (the pre-choice rate, the paper's first headline; it
carries the key), b (after a Decline), c (under GPC) -- one rate each, on one shared x origin and scale (the label
column is sized from the widest row name of all three, from the 2 mm indent; asserted).
Encoding (grey for context, colour for signal; all three rates are 'consent lost' rates, so their own estimates are
brick):
  * the main estimate: filled LEAK brick circle with its Wilson 95 % CI;
  * the key area (nature-figure graft; DESIGN_V7 section 3.3): the main estimate's Wilson CI carried through the whole
    plot as a pale pre-mixed brick ground (TINT LEAK, never alpha), square, no outline, under every mark. It replaces
    v6's two dashed lines (v7: no dashes in data panels). A row whose interval reaches into it overlaps the main
    interval;
  * 'Main, bootstrap by consent tool': the same main estimate with the BCa cluster-bootstrap interval: a brick line
    with a short vertical brick tick at the main estimate (a distinct glyph, so the row reads 'same estimate, wider
    interval', never as a new point; the caption says why);
  * robustness variants (same measure, other sample or crawl): open brick circles (white, 0.8 pt brick edge) with
    brick CIs;
  * changed definitions (another measure): mid-grey filled circles with mid-grey CIs, set apart below a gap (no rule,
    no box: DESIGN_V7 section 8.1).
One small frameless key in a, top right over empty space, its text in muted 7 pt (it serves b and c); it lists every
glyph of the plots in row order, the BCa row's line-and-tick included.
Data: stats.json supp/S6 (= analysis/outputs/figS6.csv). c's estimand is 'of the stores with a sandboxed ad request
under Default, still one under GPC'; Fig 5b and Fig 1a report the same stores over ALL GPC stores (stats
fig5/c/composition/gpc/any), drawn as c's last 'changed definition' row ('Denominator: all GPC stores')."""
import math

from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

from s2 import AIR_MM, MEW, MID, MS, W, check_composite, ci_line, dot, open_x, plot_rect_mm, tw_mm
from supp_common import S, fs, finish, write_registry

PITCH = 3.1                  # mm between rows
SEP = 0.9                    # extra rows of white before the 'changed definition' rows
TOP = 5.5                    # plot top (mm below the panel top; clear of the letter zone)
RIGHT = W - 3.0              # plot right edge (mm): room for the '100' tick label
EXTRA_KEY = 'fig5/c/composition/gpc/any'
BLOCKS = [('prechoice_sbx_banner', fs.PRECHOICE_AXIS_TITLE),
          ('decline_residual', 'Ad request from a new sandbox on the fresh page (% of stores)'),
          ('gpc_residual', 'Sandboxed ad request still sent under GPC (% of stores)')]
OPEN_MEW = 0.8
MAIN = dict(marker='o', ms=MS, mfc=fs.LEAK, mec=fs.LEAK, mew=MEW, color=fs.LEAK)
ROBUST = dict(marker='o', ms=MS, mfc=fs.SURFACE, mec=fs.LEAK, mew=OPEN_MEW, color=fs.LEAK)
DEFN = dict(marker='o', ms=MS, mfc=MID, mec=MID, mew=MEW, color=MID)
STYLE = {'main': MAIN, 'robustness': ROBUST, 'definition': DEFN}
BAND = fs.TINT['LEAK']       # the key area: the main estimate's Wilson CI through the plot
# the key lists every glyph of the plot, in row order: the BCa row's brick line with a vertical tick is a glyph too
BCA = dict(marker='|', ms=MS + 0.5, mfc=fs.LEAK, mec=fs.LEAK, mew=fs.V7_LW['data'], color=fs.LEAK)
LEGEND = [(MAIN, 'Main analysis'), (BCA, 'Main, bootstrap interval'), (ROBUST, 'Robustness variant'),
          (DEFN, 'Changed definition')]
# the caption (make_captions.py, 's5') lists every row's k of n by these stats keys, top to bottom (None = the gap)
_K = lambda *ix: [f'supp/S6/{i}' for i in ix]          # noqa: E731
CAPTION_ORDER = [_K(0, 31, 4, 5, 6, 7, 8, 9, 10, 30) + [None] + _K(1, 2, 3),
                 _K(11, 33, 15, 16, 17, 18, 19, 32) + [None] + _K(12, 13, 14),
                 _K(20, 35, 23, 24, 25, 26, 27, 34) + [None] + _K(21, 22, 28, 29) + [EXTRA_KEY]]


def label_map():
    """Row name per stats variant; renders (and registers) the four design numbers the names print."""
    return {'main analysis': 'Main analysis',
         'main analysis (next page, fresh sandboxes)': 'Main analysis (fresh page)',
         'cluster bootstrap by consent tool (BCa)': 'Main, bootstrap by consent tool',
         'crawl run at 6 browsers': 'Crawl segment at ' + fs.N('design/concurrency_limit') + ' browsers',
         'crawl run at 10 browsers': 'Crawl segment at ' + fs.N('design/concurrency_coordinator') + ' browsers',
         'excluding edge-cached pages': 'Without edge-cached pages',
         'only pages with a California consent string': 'California consent string only',
         'adding banners missed by the detector (re-check)': 'Missed banners added',
         'Consentmo + shouldShowBanner() counted as banner': 'Consentmo stores as banner stores',
         'excluding stores flagged in the ethics review': 'Without ethics-flagged stores',
         'weighted to the Tranco top-200k (ratio estimator)': 'Weighted to the Tranco top ' + fs.N('design/tranco_top_n'),
         'including the failed forced clicks': 'Including failed forced clicks',
         'excluding all forced clicks': 'Without any forced click',
         'first 10 s of each load': 'First ' + fs.N('design/equal_window_s') + ' s of each load',
         'data beacons only (no library loads)': 'Data beacons only',
         'beacons carrying our test code only': 'Beacons with our test code only',
         'any origin (not only sandbox)': 'Any origin, not only a sandbox',
         'any time after the click (same or next page)': 'Any time after the click',
         'next page, any sandbox': 'Fresh page, any sandbox',
         'all GPC stores as denominator': 'Denominator: all GPC stores',
         'pixels declaring sale of data only': 'Sale-of-data pixels only'}


def rows_of(idx):
    """The block's rows in print order: main, interval, robustness, None (= the gap), definition. Each row is
    (key, record) with key the stats.json path of the record (the caption cites these keys in this order)."""
    outcome = BLOCKS[idx][0]
    recs = [(f'supp/S6/{i}', r) for i, r in enumerate(S['supp']['S6']) if r['outcome'] == outcome]
    main = [x for x in recs if x[1]['kind'] == 'main']
    inter = [x for x in recs if x[1]['kind'] == 'interval']
    robust = [x for x in recs if x[1]['kind'] == 'robustness']
    defin = [x for x in recs if x[1]['kind'] == 'definition']
    if outcome == 'gpc_residual':
        r = dict(fs.stat(EXTRA_KEY), variant='all GPC stores as denominator', kind='definition')
        defin.append((EXTRA_KEY, r))
    assert len(main) == 1 and len(inter) == 1
    rows = main + inter + robust + [None] + defin
    assert [x[0] if x else None for x in rows] == CAPTION_ORDER[idx], f'{outcome}: rows no longer in caption order'
    return rows


def layout(idx):
    """Row y positions (rows from the top, in row units) and the axis limits (AIR_MM of white at both ends)."""
    ys, y = [], 0.0
    for item in rows_of(idx):
        if item is None:
            y += SEP
            continue
        ys.append(y)
        y += 1.0
    air = AIR_MM / PITCH
    return ys, (-air, ys[-1] + air)


def plot_h(idx):
    lo, hi = layout(idx)[1]
    return (hi - lo) * PITCH


def height(idx):
    return int(math.ceil(TOP + plot_h(idx) + 9.4))


def geometry():
    m = label_map()
    names = [m[item[1]['variant']] for idx in range(3) for item in rows_of(idx) if item is not None]
    fs.reset_registry()                          # the names above were rendered only to be measured
    w_lab = max(tw_mm(s, fs.FS['cat']) for s in names)
    return fs.INDENT_MM + w_lab + 3.0 / fs.PT_PER_MM + 0.4


def block(idx, left):
    outcome, title = BLOCKS[idx]
    order = [x for x in rows_of(idx) if x is not None]
    ys, ylim = layout(idx)
    H = height(idx)
    fig = fs.panel(W, H)
    pw = RIGHT - left
    ax = fs.axes_mm(fig, left, TOP, pw, plot_h(idx))
    ax.set_ylim(ylim[1], ylim[0])                                       # first row on top
    ax.set_xlim(-2, 102)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(['0', '25', '50', '75', '100'])
    open_x(ax)
    ax.set_xlabel(title, labelpad=2.0)
    ax.set_yticks(ys)
    names = label_map()                                                 # this panel's printed numbers, registered once
    assert all(r['variant'] in names for _, r in order)
    ax.set_yticklabels([names[r['variant']] for _, r in order], fontsize=fs.FS['cat'], color=fs.SP_FG)
    ax.tick_params(axis='y', length=0, pad=3.0)
    mrec = order[0][1]
    assert mrec['kind'] == 'main'
    # the key area: the main estimate's Wilson CI through the whole plot (a pre-mixed ground under every mark)
    ax.add_patch(Rectangle((100 * mrec['lo'], ylim[0]), 100 * (mrec['hi'] - mrec['lo']), ylim[1] - ylim[0],
                           facecolor=BAND, edgecolor='none', zorder=0.5))
    for y, (key, r) in zip(ys, order):
        lo, hi = 100 * r['lo'], 100 * r['hi']
        if r['kind'] == 'interval':                                     # BCa interval + a tick at the main estimate
            assert abs(r['p'] - mrec['p']) < 1e-12
            ci_line(ax, lo, hi, y, fs.LEAK, zorder=3)
            ax.plot([100 * r['p']], [y], ls='none', marker=BCA['marker'], ms=BCA['ms'], mew=BCA['mew'],
                    color=BCA['color'], zorder=4, clip_on=False)
            continue
        st = STYLE[r['kind']]
        ci_line(ax, lo, hi, y, st['color'], zorder=3)
        dot(ax, 100 * r['p'], y, st, zorder=4)
    # the caption's claim: every robustness variant's interval overlaps the main interval (reaches into the band)
    for _, r in order:
        if r['kind'] == 'robustness':
            assert r['lo'] <= mrec['hi'] and r['hi'] >= mrec['lo'], r['variant']
    if idx == 0:
        hs = [Line2D([], [], ls='-' if st is BCA else 'none', lw=fs.LW['error'], color=st['color'], marker=st['marker'],
                     ms=st['ms'], mfc=st['mfc'], mec=st['mec'], mew=st['mew']) for st, _ in LEGEND]
        lg = fs.legend(ax, hs, [t for _, t in LEGEND], loc='upper right', frameon=False, fontsize=fs.FS['legend'],
                       handlelength=0.9, handletextpad=0.5, labelspacing=0.35, borderaxespad=0.3, borderpad=0.2,
                       labelcolor=fs.SP_MUTED)
        fig.canvas.draw()
        lgb = lg.get_window_extent(fig.canvas.get_renderer())
        half = MS / 72 * fig.dpi / 2
        for y, (_, r) in zip(ys, order):                                 # every mark / interval clear of the key
            x1, yy = ax.transData.transform((100 * max(r['hi'], r['p']), y))
            assert x1 + half < lgb.x0 - 1.0 / 25.4 * fig.dpi or yy + half < lgb.y0, f'a: key crowds {r["variant"]}'
    fig.canvas.draw()
    x0 = min(t.get_window_extent(fig.canvas.get_renderer()).x0 for t in ax.get_yticklabels()) / fig.dpi * 25.4
    assert x0 >= fs.INDENT_MM - 0.05, f'{outcome}: row labels start {x0:.2f} mm from the edge'
    rect = plot_rect_mm(fig, ax)
    finish(fig, f'figS5{"abc"[idx]}_{outcome}')
    return H, rect


if __name__ == '__main__':
    hs = [height(i) for i in range(3)]
    tops = [0, hs[0] + fs.GUTTER_MM, hs[0] + hs[1] + 2 * fs.GUTTER_MM]
    canvas = sum(hs) + 2 * fs.GUTTER_MM
    check_composite('figS5.tex', {k: (0, t, W, h) for k, t, h in zip('abc', tops, hs)}, canvas)
    with fs.v7_context():
        left = geometry()
        got = [block(i, left) for i in range(3)]
    assert [g[0] for g in got] == hs
    # alignment gate: the three plots share one x origin and scale (left and right plot edges)
    assert max(g[1][0] for g in got) - min(g[1][0] for g in got) < 0.01
    assert max(g[1][2] for g in got) - min(g[1][2] for g in got) < 0.01
    write_registry('figS5')
    print('figS5: panel heights (mm):', hs, 'canvas:', canvas)
