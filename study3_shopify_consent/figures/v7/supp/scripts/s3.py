"""Supplementary Figure S3 (v7) -- outcomes by Tranco rank bucket. Binding: ../../DESIGN_V7.md; the grammar of Fig S2a
(s2.py, whose v7 helpers and mark styles it shares): five dot plots side by side that share the bucket rows (names on
the first plot only, under a muted 7 pt 'Tranco rank' group header -- the suite's horizontal header, as Fig S2a, Fig 6d
and Fig S8b -- left-aligned at the 2 mm indent above the first row), each plot one outcome on 0-100 % (ticks 0 / 50 /
100) with a two-line axis title naming it; only a bottom axis, bounded to 0-100 (the rows are named, not measured).

Figure contract (DESIGN_V7 section 1). Claim (the caption title): pre-choice firing on banner stores was about the same
in every Tranco rank bucket below the top one. One panel, the population by rank, so the figure carries no panel letter
(a lone 'a' would read as a missing 'b'; the caption cites no panel). Its five plots have one role each; the claim
lives in the third ('Fired before any choice, banner stores').
Grey for context, colour for signal (sciplot): the three plots that show a consent-lost rate tested in Fig S5 -- before
any choice among banner stores, on the fresh page after Decline, and still under GPC -- are drawn alike: LEAK brick
marks on Fig S5's pale brick band (TINT LEAK, the main estimate's Wilson CI; the four buckets pool to exactly that
estimate, asserted in s2.headline_band), so the lower buckets read as brick lines on the overall rate. The first two
plots (banner shown; fired before any choice among all stores) are context in mid grey (s2.STORY). The top bucket
(fewer than design.min_stores_row stores) takes the set's one small-n treatment in every plot (s2.SMALL: NEUTRAL
marks, LIGHT intervals, its name in SP_MUTED; = Fig S2a's small tools); cells with n < design.min_cell_n are not drawn
(the top bucket's banner-store and fresh-page cells). Wilson 95 % CIs as uncapped 0.75 pt lines in the colour of their
mark. No n column and no counts in the row labels: the caption carries every k and n (stats.json supp/S3). Bucket labels
avoid a bare '1' ('Top 10k' = ranks 1-10,000), so the only digits in the figure are tick labels and the 'k' bucket
bounds (structural, trace_supp.py). Alignment gate: one top line and one baseline (asserted)."""
import numpy as np

from s2 import (GAP_IN, HEAD_CLEAR, MEW, MS, SMALL, SMALL_LABEL, STORY, TOP, W, cat_rows, check_composite, ci_line,
                dot, headline_band, plot_rect_mm, row_ylim, tw_mm, x_pct)
from supp_common import S, fs, finish, write_registry

H = 35
PITCH = 4.0
HEAD = 'Tranco rank'                                                             # the rows' group header
HEAD_ABOVE = 1.0                                                                 # header row: one pitch above row 1
BUCKET = {'1-10k': 'Top 10k', '10k-50k': '10k–50k', '50k-100k': '50k–100k', '100k-200k': '100k–200k'}
METRICS = [('banner', 'Banner\nshown (%)'),                                      # Default load
           ('prechoice_sbx', 'Fired before any\nchoice (%)'),                    # Default load, all stores
           ('prechoice_sbx_banner', 'Fired before any choice,\nbanner stores (%)'),   # Default load, banner stores
           ('after_decline', 'Fired on the\nfresh page (%)'),                    # Decline load (working clicks)
           ('gpc_resid', 'Still fired\nunder GPC (%)')]                          # GPC load (of Default-firing stores)
CLAIM = 'prechoice_sbx_banner'                                                   # the plot the caption title is about
# the plots that show one of Fig S5's headline rates (keyed by S5's outcome names, which these metrics share) and so
# carry its key-area band: the four buckets pool to exactly S5's main estimate (asserted in s2.headline_band)
HEADLINE = {'prechoice_sbx_banner': 'prechoice_sbx_banner', 'after_decline': 'decline_residual',
            'gpc_resid': 'gpc_residual'}
SIGNAL = dict(marker='o', ms=MS, mfc=fs.LEAK, mec=fs.LEAK, mew=MEW, color=fs.LEAK)


def main():
    recs = S['supp']['S3']
    assert [r['bucket'] for r in recs] == list(BUCKET)
    fig = fs.panel(W, H)
    labels = [BUCKET[r['bucket']] for r in recs]
    small = [r['n'] < S['design']['min_stores_row'] for r in recs]
    assert small == [True, False, False, False]                      # caption: only the top bucket is drawn in grey
    min_n = S['design']['min_cell_n']
    n = len(recs)
    ys = np.arange(n)[::-1].astype(float)
    w_lab = max(tw_mm(s, fs.FS['cat']) for s in labels)
    left = fs.INDENT_MM + max(w_lab + 3.0 / fs.PT_PER_MM + 0.4, tw_mm(HEAD, fs.FS['label']) + HEAD_CLEAR)
    right = W - 1.2
    k = len(METRICS)
    plotw = (right - left - (k - 1) * GAP_IN) / k
    ylim = row_ylim(n - 1, PITCH)
    height = (ylim[1] - ylim[0]) * PITCH
    rects = []
    for j, (m, title) in enumerate(METRICS):
        ax = fs.axes_mm(fig, left + j * (plotw + GAP_IN), TOP, plotw, height)
        ax.set_ylim(*ylim)
        x_pct(ax, 50, title=title)
        cat_rows(ax, ys, labels if j == 0 else None, [SMALL_LABEL if s else None for s in small])
        if m in HEADLINE:                                                # the overall rate of the four buckets
            headline_band(ax, HEADLINE[m], recs, m, ylim)
        for y, r, sm in zip(ys, recs, small):
            rec = r[m]
            if rec['n'] < min_n:                                         # too few stores: not drawn (caption)
                continue
            st = SMALL if sm else (SIGNAL if m in HEADLINE else STORY)
            ci_line(ax, 100 * rec['lo'], 100 * rec['hi'], y, st['color'])
            dot(ax, 100 * rec['p'], y, st)
        fig.canvas.draw()
        tw = ax.xaxis.label.get_window_extent(fig.canvas.get_renderer()).width / fig.dpi * 25.4
        assert tw <= plotw + GAP_IN - 0.6, f'axis title {title!r} is {tw:.1f} mm wide (plot {plotw:.1f} mm)'
        rects.append(plot_rect_mm(fig, ax))
        if j == 0:
            # the rows' group header: muted 7 pt, left-aligned at the indent, one pitch above the first row (in the band
            # above the plot, which holds no letter: the figure has one panel)
            y0 = TOP + (ylim[1] - ys[0]) * PITCH
            hd = fs.text_mm(fig, fs.INDENT_MM, y0 - HEAD_ABOVE * PITCH, HEAD, size=fs.FS['label'], color=fs.SP_MUTED,
                            ha='left', va='center_baseline')
            fig.canvas.draw()
            r = fig.canvas.get_renderer()
            hb = hd.get_window_extent(r)
            assert hb.x1 / fig.dpi * 25.4 <= left - HEAD_CLEAR + 0.01, 'the header runs into the plot'
            assert (fig.bbox.y1 - hb.y1) / fig.dpi * 25.4 >= 0.3, 'the header leaves the panel'
            l0 = ax.get_yticklabels()[0].get_window_extent(r)
            assert hb.y0 - l0.y1 >= 0.5 / 25.4 * fig.dpi, "'Tranco rank' crowds the first row's name"
    # the caption's claim: among banner stores, the three lower buckets lie within a few points of each other
    lo, hi = S['supp']['S3_prechoice_banner_range']['lo'], S['supp']['S3_prechoice_banner_range']['hi']
    lower = [r[CLAIM]['p'] for r, sm in zip(recs, small) if not sm]
    assert len(lower) == 3 and abs(min(lower) - lo) < 1e-12 and abs(max(lower) - hi) < 1e-12
    assert recs[0][CLAIM]['n'] < min_n                                   # the top bucket's claim cell is not drawn
    assert TOP + height + 11.0 <= H + 0.01, f'{TOP + height + 11.0:.1f} mm does not fit {H} mm'
    # alignment gate: one top line, one baseline, equal widths
    assert max(r[1] for r in rects) - min(r[1] for r in rects) < 0.01
    assert max(r[3] for r in rects) - min(r[3] for r in rects) < 0.01
    finish(fig, 'figS3_rank', letter_zone=False)                          # no letter: the band holds the header
    write_registry('figS3')


if __name__ == '__main__':
    check_composite('figS3.tex', {'-': (0, 0, W, H)}, H)                 # one panel, no letter
    with fs.v7_context():
        main()
    print(f'figS3: {W} x {H} mm (one panel, no letter)')
