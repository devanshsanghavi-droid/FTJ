"""Supplementary Figure S9 (v7) -- what reaches vendors: the full landing URL by vendor and load, refusal signals,
Google's Consent Mode states and signal kinds, and the five-load Store C event strip.

Binding: figures/v7/DESIGN_V7.md (worked example figures/v7/fig1). fs.v7_context(): open L axes, Arial 7 / 6 pt,
markers 3.5 pt, uncapped 0.75 pt intervals, no gridlines, no panel titles, no numbers in the plots (tick labels only;
every count is in the caption); no vendor hues (vendors are named in ink). Loads keep the project's arm shapes in the
sciplot neutrals (Default filled near-black circle, Decline open square, GPC filled grey triangle). c: HONOUR slate =
Google beacons whose Consent Mode state denies ad storage (the refusal reached the vendor), greys for the other states
(granted GREY_D, L* 36, so it parts from slate, L* 49, in greyscale print; no state LIGHT).
d (as Fig 1b): one lane per execution context on the ground of its Fig 1a region (TINT SAND: the sandbox lane; TINT
PAGE: the other lane); LEAK brick = the request carried the creator's per-video code (it reached the vendor); requests
without the code in two grey steps (data beacons and other requests NEUTRAL, tall; library loads SP_CONTEXT, short);
amber rules = the banner becoming visible and the Decline click, grey rule = the reload, each event named centred
above its own rule.

Figure contract (DESIGN_V7 section 1): one claim -- what reaches vendors: the full landing URL in every load, refusal
signals mostly from Google, and a creator's per-video code on every load of Store C.
  a  the population: full-URL share of sandboxed ad beacons by vendor group and load; Korn-Graubard 95% CIs clustered
     by store; a load with fewer than design/min_stores_row stores for a vendor is not drawn; the arm key in one row
     above the plot, clear of the row names (as Fig 5a).                                            stats fig6/a
  b  the comparison of signals, one plot on a's 0-100 scale with two groupings named in muted grey above their rows
     (as Fig S8b): 'Ad requests' -- ad requests carrying a refusal signal, by vendor group and load (store-bootstrap
     percentile 95% CIs); 'Stores, all flagged' -- stores still sending on which every remaining sandboxed
     request carried a refusal, after Decline and under GPC (Wilson 95% CIs, drawn only, from the registered k and n).
                                                              stats fig6/c, fig5/flags/resid_*; supp derived s9b_*
  c  the control, Google only: left, the Consent Mode state of Google's beacons by load (thin stacked 100% bars in
     tier order: denied HONOUR, granted mid grey, no state LIGHT; 'other' states are too few to draw), the key above
     the plot; right, each refusal-signal kind: request-level shares (the registered k / n) with 95% CIs from
     resampling stores (percentile bootstrap, design/bootstrap_B resamples, design/seed; analysis.boot_share's
     estimator, recomputed here from analysis/outputs/ad_requests.csv.gz, whose counts are asserted equal to the
     registered k and n; drawn only), markers as in a; the arms of a row sit close (+-0.2 rows) and the rows far apart.
                                                   supp derived s9b_gcs_states, s9c_other_state, s9c_google_flag_shares
  d  (hero; one instance) Store C, five loads, as an event strip on a broken time axis with one scale and marked cuts
     (breaks where nothing happened for > BREAK_S; two neighbouring stretches that each hold fewer than SPARSE_N events
     share one stretch): per load a sandbox lane and an 'other' lane (3.8 mm grounds at a 4 mm pitch); one tick per
     tick group (requests of one vendor group and tick height less than merge_ms apart, drawn at their mid time);
     tall = data beacons and other requests, short = library loads; brick = at least one request of the tick carried
     the per-video code; requests without it in two grey steps (tall NEUTRAL, short SP_CONTEXT). Event names, each
     centred above its own rule: 'banner visible' (once), 'Decline click', 'reload'; the key above the plot.
                                      analysis/outputs/fig6b_store_c.csv; stats fig6/b; supp derived s9d_tick_groups
Layout (mm; must equal figS9.tex, asserted): row 1 a | b (92 x H1); row 2 c (190 x H2); row 3 d (190 x H3); 6 mm
gutters; a's and b's plots share their top and x-axis line (asserted). Drawn values are registered (fmt 'raw') in
panels/figS9_numbers.csv. Nothing but tick labels is printed as a number.
storec_segments() / storec_tick_labels() are imported by trace_supp.py (the S9d tick labels are structural tokens).
"""
import os

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from s6 import (LW_EVENT, astyle, bb_mm, cat_y, check_alignment, check_composite, ci_h, dot, key_row, mark, mark_sd,
                no_digits, no_overlaps, off_spines, plot_box, rows_ylim, share, tw_mm, value_axis, wilson, within)
from supp_common import AOUT, SDv, fs, finish, table, write_registry

LQ, RQ = '‘', '’'
G = fs.GUTTER_MM
W_A = W_B = 92.0
H1, H2, H3 = 64.0, 50.0, 70.0
FIG_H = H1 + G + H2 + G + H3
CELLS = {'a': (0, 0, W_A, H1), 'b': (W_A + G, 0, W_B, H1), 'c': (0, H1 + G, fs.FIG_W_MM, H2),
         'd': (0, H1 + G + H2 + G, fs.FIG_W_MM, H3)}
TOP1, PH1 = 7.5, 45.5                 # row 1: the band above holds a's key (one row)
KEY1_BASE = 3.6                       # baseline of a's key (mm from the panel top)
R_PAD = 2.5
ARMS3 = [('Default', -0.3), ('Decline', 0.0), ('GPC', 0.3)]          # dodge (rows run top to bottom)


# ------------------------------------------------------------------------------------------------ a
def panel_a():
    rows = fs.VENDOR_ORDER + ['All']
    names = [('All vendors' if r == 'All' else r) for r in rows]
    ys = np.array(list(range(len(fs.VENDOR_ORDER))) + [len(fs.VENDOR_ORDER) + 0.7])
    nmin = mark('design/min_stores_row')
    fig = fs.panel(W_A, H1)
    left = np.ceil(fs.INDENT_MM + max(tw_mm(n, fs.FS['cat']) for n in names) + 1.6)
    pw = W_A - left - R_PAD
    ax = fs.axes_mm(fig, left, TOP1, pw, PH1)
    pts, skipped = [], []
    for y, v in zip(ys, rows):
        vv = v.replace('/', '~1')
        for z, (arm, dy) in enumerate(ARMS3):
            key = f'fig6/a/{vv}/{arm}'
            if mark(key + '/n_stores') < nmin:
                skipped.append((v, arm))
                continue
            p, lo, hi = share(key, lo='kg_lo', hi='kg_hi')
            st = astyle(arm)
            ci_h(ax, y + dy, lo, hi, st['color'], zorder=3 + z)
            dot(ax, p, y + dy, st, zorder=4 + z)
            pts += [(lo, y + dy), (hi, y + dy), (p, y + dy)]
    assert skipped == [('Meta', 'GPC'), ('Snap', 'GPC')], skipped          # named in the caption
    value_axis(ax, 'x', 0, 100, 25, length_mm=pw)                       # air beyond 0 and 100 (TikTok GPC: 100 %)
    ax.set_xlabel('Beacons with the full landing URL (%)')
    cat_y(ax, ys, names)
    rows_ylim(ax, ys[0] + ARMS3[0][1], ys[-1] + ARMS3[-1][1], PH1, pad_mm=1.6)
    # the arm key in one row above the plot, right-aligned to it and clear of the row names (Fig 5a's key)
    _, kx0 = key_row(fig, left + pw, KEY1_BASE, [('marker', astyle(a), a) for a, _ in ARMS3], gap=3.0)
    assert kx0 >= left + 5.0, 'a: the key must stand clear of the row names'
    off_spines(fig, ax, pts[2::3], 'a')
    within(fig, ax, 'a')
    no_overlaps(fig, 'a')
    no_digits(fig, 'a')
    finish(fig, 'figS9a_fullurl')
    return plot_box(fig, ax)


# ------------------------------------------------------------------------------------------------ b
B_GROUPS = [('Google', 'Google'), ('Microsoft', 'Microsoft'), ('Other vendors', 'All other vendors')]
B_LOW = [('resid_decline_fresh', 'Decline', 'Decline, fresh page'), ('resid_gpc', 'GPC', 'GPC load')]
B_YS_TOP = np.array([0.0, 1.0, 2.0])             # 'Ad requests': one row per vendor group, the three loads dodged
B_YS_LOW = np.array([4.1, 5.1])                  # 'Stores, every request flagged': one row per load
B_HEADS = [(B_YS_TOP[0], 'Ad requests'), (B_YS_LOW[0], 'Stores, all flagged')]   # caption: every request


def panel_b():
    fig = fs.panel(W_B, H1)
    labs = [g[1] for g in B_GROUPS] + [r[2] for r in B_LOW]
    left = np.ceil(fs.INDENT_MM + max(tw_mm(s, fs.FS['cat']) for s in labs) + 1.6)
    pw = W_B - left - R_PAD
    ax = fs.axes_mm(fig, left, TOP1, pw, PH1)
    pts = []
    for (g, _), y in zip(B_GROUPS, B_YS_TOP):
        for z, (arm, dy) in enumerate(ARMS3):
            p, lo, hi = share(f'fig6/c/{g}/{arm}')
            st = astyle(arm)
            ci_h(ax, y + dy, lo, hi, st['color'], zorder=3 + z)
            dot(ax, p, y + dy, st, zorder=4 + z)
            pts.append((p, y + dy))
    # stores where every remaining sandboxed request carried a refusal (Wilson CIs, drawn only)
    for (k, arm, _), y in zip(B_LOW, B_YS_LOW):
        kk, nn = mark(f'fig5/flags/{k}/stores_all_flagged'), mark(f'fig5/flags/{k}/stores')
        assert (mark_sd(f's9b_refusal_store_share/{k}/k'), mark_sd(f's9b_refusal_store_share/{k}/n')) == (kk, nn)
        lo, hi = wilson(kk, nn)
        st = astyle(arm)
        ci_h(ax, y, 100 * lo, 100 * hi, st['color'])
        p = 100 * mark_sd(f's9b_refusal_store_share/{k}/p')
        dot(ax, p, y, st)
        pts.append((p, y))
    ys = np.concatenate([B_YS_TOP, B_YS_LOW])
    cat_y(ax, ys, labs)
    k = rows_ylim(ax, B_YS_TOP[0] - 1.0, B_YS_LOW[-1], PH1, pad_mm=1.8)
    value_axis(ax, 'x', 0, 100, 25, length_mm=pw)                       # a's scale; air left of 0
    ax.set_xlabel('With a refusal signal (%)')
    # the two groupings named once each, muted 7 pt, above their first row, right-aligned with the row names (as S8b)
    x_lab = left - 3.0 / 72 * 25.4
    for y0, name in B_HEADS:
        fs.text_mm(fig, x_lab, TOP1 + (y0 - 0.95 - ax.get_ylim()[1]) / k, name, ha='right', va='center_baseline',
                   color=fs.SP_MUTED, size=fs.FS['label'])
    off_spines(fig, ax, pts, 'b')
    within(fig, ax, 'b')
    no_overlaps(fig, 'b')
    no_digits(fig, 'b')
    finish(fig, 'figS9b_refusal')
    return plot_box(fig, ax)


# ------------------------------------------------------------------------------------------------ c
C_TOP, C_PH = 6.5, 33.5
C_ARMS = [('Default', 'Default', 'Default'), ('Decline_next', 'Decline', 'Decline, fresh page'),
          ('GPC', 'GPC', 'GPC')]
# DESIGN_V7 8.7 tier order: the story first (HONOUR: ad storage denied, the refusal reached Google), then the mid grey,
# then LIGHT
STATES = [('denied', fs.HONOUR, 'Ad storage denied'), ('granted', fs.GREY_D, 'Granted'),
          ('none', fs.LIGHT, 'No state')]          # granted GREY_D (L* 36) parts from slate (L* 49) in greyscale
C_SPLIT = 100.0                      # c: the left plot (with its labels) ends here; the right one starts after a gutter
C_BAR_MM = 2.0                       # bar thickness (three rows here, so a little more than Fig S6c's)
C_DODGE = 0.2                        # c right: the three arms of a row sit close; the rows stand far apart
C_KINDS = [('gcs_ad_denied', '‘gcs’ denied'), ('gcd_denied', '‘gcd’ denied'), ('npa', '‘npa=1’'),
           ('rdp', '‘rdp=1’'), ('us_privacy_optout', '‘us_privacy’ opt-out')]
C_COND = {'Default': 'A0', 'Decline_next': 'A1next', 'GPC': 'A2'}    # analysis.refusal_signals' conds


def google_signal_cis():
    """95% CIs of c-right's request-level shares from resampling stores: analysis.boot_share's percentile bootstrap
    (B = design/bootstrap_B, seed = design/seed), recomputed from analysis/outputs/ad_requests.csv.gz. The counts
    are asserted equal to the registered k and n, so the intervals belong to the drawn shares. Drawn only."""
    B, seed = int(mark('design/bootstrap_B')), int(mark('design/seed'))
    ad = pd.read_csv(os.path.join(AOUT, 'ad_requests.csv.gz'), low_memory=False,
                     usecols=['store_id', 'stratum', 'cond', 'vgroup', 'flag_kind'])
    g = ad[(ad.stratum == 'main') & (ad.vgroup == 'Google')]
    out = {}
    for key, cond in C_COND.items():
        x = g[g.cond == cond]
        assert len(x) == SDv(f's9c_google_flag_shares/{key}/n'), key
        for kind, _ in C_KINDS:
            num = x.flag_kind.fillna('').str.contains(kind).astype(int)
            assert int(num.sum()) == SDv(f's9c_google_flag_shares/{key}/{kind}/k'), (key, kind)
            df = pd.DataFrame(dict(num=num.values, den=np.ones(len(x)), g=x.store_id.values)).groupby('g').sum()
            rng = np.random.default_rng(seed)
            nv, dv = df.num.values, df.den.values
            idx = rng.integers(0, len(df), size=(B, len(df)))
            est = nv[idx].sum(1) / np.maximum(dv[idx].sum(1), 1)
            out[(key, kind)] = (100 * float(np.percentile(est, 2.5)), 100 * float(np.percentile(est, 97.5)))
    return out
C_KEY_BASE = 3.6


def panel_c():
    fig = fs.panel(fs.FIG_W_MM, H2)
    # left: Consent Mode state of Google's beacons (stacked 100% bars). 'Other' states keep their share of the bar but
    # are not drawn: each is narrower than the white gap between segments (asserted).
    L = np.ceil(fs.INDENT_MM + max(tw_mm(a[2], fs.FS['cat']) for a in C_ARMS) + 1.6)
    PW = C_SPLIT - L - R_PAD
    ax = fs.axes_mm(fig, L, C_TOP, PW, C_PH)
    ys = np.arange(len(C_ARMS), dtype=float)
    k_mm = rows_ylim(ax, ys[0], ys[-1], C_PH, pad_mm=2.4)
    HB = C_BAR_MM * k_mm
    GAP = 0.75 / fs.PT_PER_MM * 100 / PW
    max_other = mark_sd('s9c_other_state/max_share')
    for (key, _, _), y in zip(C_ARMS, ys):
        r = {k: mark_sd(f's9b_gcs_states/{key}/{k}') for k in ('n', 'G100', 'G101', 'G111', 'other_state', 'no_state')}
        vals = dict(denied=r['G100'] + r['G101'], granted=r['G111'], other=r['other_state'], none=r['no_state'])
        assert sum(vals.values()) == r['n']
        assert vals['other'] / r['n'] <= max_other and 100 * vals['other'] / r['n'] <= GAP
        x = 0.0
        for s in ('denied', 'granted', 'other', 'none'):
            w = 100 * vals[s] / r['n']
            if s != 'other':
                col = dict((k, c) for k, c, _ in STATES)[s]
                g = GAP if s != 'none' else 0.0
                ax.add_patch(Rectangle((x, y - HB / 2), max(w - g, 0), HB, zorder=2, facecolor=col, edgecolor='none',
                                       linewidth=0))
            x += w
    cat_y(ax, ys, [a[2] for a in C_ARMS])
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.spines['bottom'].set_bounds(0, 100)
    ax.set_xlabel('Google beacons, by Consent Mode state (%)')
    key_row(fig, L + PW, C_KEY_BASE, [('square', c, lab) for _, c, lab in STATES], gap=2.6)
    # right: each refusal-signal kind, share of Google's ad requests (arm markers as in a)
    kinds = C_KINDS
    cis = google_signal_cis()
    L2 = np.ceil(C_SPLIT + G + max(tw_mm(k[1], fs.FS['cat']) for k in kinds) + 1.6)
    PW2 = fs.FIG_W_MM - L2 - R_PAD
    ax2 = fs.axes_mm(fig, L2, C_TOP, PW2, C_PH)
    ys2 = np.arange(len(kinds), dtype=float)
    pts = []
    for (k, _), y in zip(kinds, ys2):
        for z, ((key, arm, _), dy) in enumerate(zip(C_ARMS, (-C_DODGE, 0.0, C_DODGE))):
            p = 100 * mark_sd(f's9c_google_flag_shares/{key}/{k}/p')
            mark_sd(f's9c_google_flag_shares/{key}/{k}/k')
            mark_sd(f's9c_google_flag_shares/{key}/n')
            lo, hi = cis[(key, k)]
            assert lo <= p <= hi, (key, k)
            st = astyle(arm)
            ci_h(ax2, y + dy, lo, hi, st['color'], zorder=3 + z)
            dot(ax2, p, y + dy, st, zorder=4 + z)
            pts.append((p, y + dy))
    cat_y(ax2, ys2, [k[1] for k in kinds])
    rows_ylim(ax2, ys2[0] - C_DODGE, ys2[-1] + C_DODGE, C_PH, pad_mm=1.4)
    value_axis(ax2, 'x', 0, 100, 25, length_mm=PW2)                     # the shares' 0-100 scale, as the left plot
    ax2.set_xlabel('Google ad requests with the signal (%)')
    off_spines(fig, ax2, pts, 'c right')
    within(fig, ax, 'c left')
    within(fig, ax2, 'c right')
    no_overlaps(fig, 'c')
    no_digits(fig, 'c', allowed=(f'{LQ}npa=1{RQ}', f'{LQ}rdp=1{RQ}'))
    finish(fig, 'figS9c_google')


# ---------------------------------------------------------------------------------------------------- d: Store C
BREAK_S, PAD_S, GRID_S = 2.0, 0.1, 0.05      # axis design: break where no event for > 2 s; pad; rounding
SPARSE_N = 12                                # two neighbouring segments that each hold fewer events are one segment


def time_segments(times):
    """Split the time axis where no event occurs for more than BREAK_S, then join neighbouring segments that each
    hold fewer than SPARSE_N events (no stretch for a handful of ticks); pad each segment and round it to GRID_S.
    Axis design only (the limits of a broken axis); asserted to contain every event."""
    ts = sorted(times)
    groups, cur = [], [ts[0]]
    for t in ts[1:]:
        if t - cur[-1] > BREAK_S:
            groups.append(cur)
            cur = [t]
        else:
            cur.append(t)
    groups.append(cur)
    i = 0
    while i < len(groups) - 1:
        if len(groups[i]) < SPARSE_N and len(groups[i + 1]) < SPARSE_N:
            groups[i:i + 2] = [groups[i] + groups[i + 1]]
        else:
            i += 1
    segs = []
    for g in groups:
        lo = 0.0 if not segs else round(float(np.floor((g[0] - PAD_S) / GRID_S) * GRID_S), 2)
        hi = round(float(np.ceil((g[-1] + PAD_S) / GRID_S) * GRID_S), 2)
        segs.append((lo, hi))
    for t in ts:                                     # every event lies inside a segment, clear of its edges
        assert any(a + 0.6 * PAD_S <= t <= b - 0.6 * PAD_S or (a == 0.0 and t >= 0) for a, b in segs), t
    return segs


STOREC_LOADS = [('A0', 'Default'), ('A0r', 'Default, repeat'), ('A1', 'Decline'), ('A2', 'GPC'), ('A2r', 'GPC, repeat')]


def storec_segments():
    """Time segments of the S9d broken axis, from every request and event time of the five Store C loads."""
    D = table('fig6b_store_c.csv')
    events = list(D.t_ms / 1000)
    for a, _ in STOREC_LOADS:
        info = fs.stat(f'fig6/b/store_c/{a}')
        events += [info[k] / 1000 for k in ('t_banner', 't_click', 't_next_nav') if info[k] is not None]
    return time_segments(events)


def storec_tick_labels():
    """The S9d tick labels (whole seconds inside each segment): structural tokens for trace_supp.py."""
    return {str(t) for a0, a1 in storec_segments() for t in range(int(np.ceil(a0)), int(np.floor(a1)) + 1)}


D_LEFT, D_RIGHT = 37.0, 187.5       # plot extent (mm); the left column holds the load names and the lane names
D_TOP = 7.0                         # top of the first lane (the key and the first event name sit above)
D_SEG_GAP = 3.0                     # white gap between the stretches of the broken axis (the cut)
LANE_PITCH, LANE_H = 4.0, 3.8       # DESIGN_V7 8.4: 3.8 mm lanes at a 4 mm pitch
LOAD_GAP = 3.4                      # white between two loads (an event name fits in it: 7 pt, no descenders)
TALL, SHORT = 3.6, 1.8              # tick heights: data beacons and other requests / library loads (mm), as Fig 1b
TICK_LW = 1.2                       # request ticks (pt), as Fig 1b
LANE_GROUND = {'sandbox': fs.TINT['SAND'], 'other': fs.TINT['PAGE']}   # = Fig 1a's two region grounds
NO_CODE = fs.NEUTRAL                # a data beacon or other request without the code (context, tall)
LIB = fs.SP_CONTEXT                 # a library load (never carries the code here: asserted; context, short, lighter)
RELOAD = fs.NEUTRAL                 # the reload: a context rule (not a consent moment), named
LANE_NAME = {'sandbox': 'Sandbox', 'other': 'Other'}
D_AXIS_GAP = 0.8                    # white between the last lane and the time axis (mm)


def panel_d():
    D = table('fig6b_store_c.csv')
    cr = 'fig6/b/store_c'
    tgk = 's9d_tick_groups/loads'
    loads = STOREC_LOADS
    # lane centres (mm from the panel top): sandbox, then other, per load
    y_lane = {}
    y = D_TOP + LANE_PITCH / 2
    for a, _ in loads:
        y_lane[(a, 'sandbox')] = y
        y_lane[(a, 'other')] = y + LANE_PITCH
        y += 2 * LANE_PITCH + LOAD_GAP
    y_bottom = y - LOAD_GAP - LANE_PITCH / 2 - (LANE_PITCH - LANE_H) / 2       # bottom of the last lane's ground
    fig = fs.panel(fs.FIG_W_MM, H3)
    segs = storec_segments()
    mm_per_s = (D_RIGHT - D_LEFT - D_SEG_GAP * (len(segs) - 1)) / sum(b - a for a, b in segs)
    plot_h = y_bottom + D_AXIS_GAP - D_TOP
    axes, x0 = [], D_LEFT
    for a0, a1 in segs:
        w = (a1 - a0) * mm_per_s
        ax = fs.axes_mm(fig, x0, D_TOP, w, plot_h)
        ax.set_xlim(a0, a1)
        ax.set_ylim(D_TOP + plot_h, D_TOP)            # data y = mm from the panel top
        ax.set_xticks(list(range(int(np.ceil(a0)), int(np.floor(a1)) + 1)))
        ax.set_yticks([])
        ax.spines['left'].set_visible(False)          # an event strip has no value axis (DESIGN_V7 6)
        for (a, sub), yc in y_lane.items():           # the lanes' grounds, square, no outline, under every mark
            ax.add_patch(Rectangle((a0, yc - LANE_H / 2), a1 - a0, LANE_H, facecolor=LANE_GROUND[sub],
                                   edgecolor='none', zorder=0.5))
        axes.append((ax, x0, w))
        x0 += w + D_SEG_GAP
    assert D_TOP + plot_h + 8.5 <= H3, 'd: the lanes and the time axis leave the panel'
    # the cuts: two short parallel slashes on the time axis in each gap between two stretches (one scale throughout)
    Wf, Hf = fs.size_mm(fig)
    yb = D_TOP + plot_h
    for (_, xl, w), _ in zip(axes[:-1], axes[1:]):
        xm = xl + w + D_SEG_GAP / 2
        for dx in (-0.45, 0.45):
            fig.add_artist(Line2D([(xm + dx - 0.45) / Wf, (xm + dx + 0.45) / Wf], [1 - (yb + 0.9) / Hf, 1 - (yb - 0.9) / Hf],
                                  transform=fig.transFigure, color=fs.SP_AXIS, lw=fs.V7_LW['axis'], clip_on=False))

    def seg_ax(t):
        return next(ax for ax, _, _ in axes if ax.get_xlim()[0] <= t <= ax.get_xlim()[1])

    def x_mm(t):
        for ax, xl, w in axes:
            a0, a1 = ax.get_xlim()
            if a0 <= t <= a1:
                return xl + (t - a0) * mm_per_s
        raise ValueError(t)

    n_ticks = n_code_ticks = 0
    ev = {}
    for a, name in loads:
        d = D[D.arm == a]
        info = {k: mark(f'{cr}/{a}/{k}') for k in ('t_banner', 't_click', 't_next_nav')}
        for sub in ('sandbox', 'other'):
            gs = SDv(f'{tgk}/{a}/{sub}')
            dd = d[d.sandbox == (sub == 'sandbox')]
            assert sum(g['n'] for g in gs) == len(dd) and sum(g['n_code'] for g in gs) == int(dd.has_creator_token.sum())
            yc = y_lane[(a, sub)]
            for i, g in enumerate(gs):
                assert (g['t_ms_last'] - g['t_ms_first']) / 1000 * mm_per_s < 1.3, g     # every member within 0.65 mm
                t = (mark_sd(f'{tgk}/{a}/{sub}/{i}/t_ms_first') + mark_sd(f'{tgk}/{a}/{sub}/{i}/t_ms_last')) / 2000
                h = SHORT if g['mark'] == 'short' else TALL
                code = mark_sd(f'{tgk}/{a}/{sub}/{i}/n_code') > 0
                assert not (code and h == SHORT), 'd: a library load with the code would need a fourth key entry'
                col = fs.LEAK if code else (LIB if h == SHORT else NO_CODE)
                seg_ax(t).plot([t, t], [yc - h / 2, yc + h / 2], color=col, lw=TICK_LW, solid_capstyle='butt',
                               zorder=4 if code else 3)
                n_ticks += 1
                n_code_ticks += code
        # the load's events: amber = banner visible and the Decline click (consent moments); grey = the reload
        y0 = y_lane[(a, 'sandbox')] - LANE_H / 2 - 0.2
        y1 = y_lane[(a, 'other')] + LANE_H / 2 + 0.2
        for k, col in (('t_banner', fs.EVENT), ('t_click', fs.EVENT), ('t_next_nav', RELOAD)):
            if info[k] is None:
                continue
            t = info[k] / 1000
            seg_ax(t).plot([t, t], [y0, y1], color=col, lw=LW_EVENT, solid_capstyle='butt', zorder=2)
            ev[(a, k)] = t
        # nothing is sent from a sandbox after the click (until the reload) or after the reload
        if info['t_click'] is not None:
            assert not ((d.t_ms > info['t_click']) & d.sandbox).any()
        # the load's name (7 pt) and its two lane names (muted 6 pt qualifiers), left of its lanes
        for sub in ('sandbox', 'other'):
            fs.text_mm(fig, D_LEFT - 1.4, y_lane[(a, sub)], LANE_NAME[sub], size=fs.FS['note'], ha='right',
                       va='center_baseline', color=fs.SP_MUTED)
        fs.text_mm(fig, D_LEFT - 1.4 - max(tw_mm(s, fs.FS['note']) for s in LANE_NAME.values()) - 2.4,
                   (y_lane[(a, 'sandbox')] + y_lane[(a, 'other')]) / 2, name, size=fs.FS['cat'], ha='right',
                   va='center_baseline', color=fs.SP_FG)
    assert n_ticks == sum(len(SDv(f'{tgk}/{a}/{s}')) for a, _ in loads for s in ('sandbox', 'other'))
    # caption: in the sandbox lanes of Default, its repeat and Decline, the first two ticks are Google's (code), then two
    # short grey TikTok library loads and one brick TikTok tick that stands for the example's code-carrying requests;
    # the GPC loads have no sandboxed request
    ex = SDv('s9d_tick_groups/example')
    assert (ex['load'], ex['sub'], ex['vgroup']) == ('A0', 'sandbox', 'TikTok')
    for a in ('A0', 'A0r', 'A1'):
        gs = SDv(f'{tgk}/{a}/sandbox')
        assert [g['vgroup'] for g in gs] == ['Google', 'Google', 'TikTok', 'TikTok', 'TikTok'], a
        assert [g['n_code'] > 0 for g in gs] == [True, True, False, False, True], a
        assert [g['mark'] for g in gs[2:]] == ['short', 'short', 'tall'] and gs[-1]['n'] == gs[-1]['n_code'] == ex['n']
    assert all(not SDv(f'{tgk}/{a}/sandbox') for a in ('A2', 'A2r'))
    assert mark_sd('s9d_tick_groups/merge_ms') == 50
    # the event names (Fig 1b, Fig 2c): 'banner visible' once, above the first load's rule; 'Decline click' and 'reload'
    # in the white gap above the Decline load, at the top of their rules (7 pt; neither has a descender)
    assert [a for a, k in ev if k == 't_click'] == ['A1'] and [a for a, k in ev if k == 't_next_nav'] == ['A1']
    cap = fs.FS['label'] * fs.CAP_EM / fs.PT_PER_MM
    lb = fs.text_mm(fig, x_mm(ev[('A0', 't_banner')]), D_TOP - 1.4, 'banner visible', ha='center', color=fs.SP_FG)
    y_gap = y_lane[('A1', 'sandbox')] - LANE_H / 2 - (LOAD_GAP + LANE_PITCH - LANE_H) / 2 + cap / 2
    # each name centred above its own rule (as 'banner visible')
    lc = fs.text_mm(fig, x_mm(ev[('A1', 't_click')]), y_gap, 'Decline click', ha='center', color=fs.SP_FG)
    lr = fs.text_mm(fig, x_mm(ev[('A1', 't_next_nav')]), y_gap, 'reload', ha='center', color=fs.SP_FG)
    # no event name crosses a tick of the load above it (the gap is white)
    for t in (lc, lr):
        _, _, top, bot = bb_mm(fig, t)
        assert top >= y_lane[('A0r', 'other')] + LANE_H / 2 + 0.2 and bot <= y_lane[('A1', 'sandbox')] - LANE_H / 2 - 0.2
    # the key above the plot, right-aligned (Fig 1b's key: muted text, marks in the data colour, the tick heights)
    key_row(fig, D_RIGHT, D_TOP - 1.4, [('tick', (fs.LEAK, TALL, TICK_LW), 'Carried the code'),
                                       ('tick', (NO_CODE, TALL, TICK_LW), 'Without the code'),
                                       ('tick', (LIB, SHORT, TICK_LW), 'Library load')], gap=3.2)
    for ax, _, _ in axes:
        ax.set_xlabel('')
    fs.text_mm(fig, (D_LEFT + D_RIGHT) / 2, D_TOP + plot_h + 6.9, 'Time since navigation start (s)',
               size=fs.FS['axis'], ha='center', color=fs.SP_FG)
    for ax, _, _ in axes:
        within(fig, ax, 'd')
    _, x1, _, _ = bb_mm(fig, lb)
    assert x1 < D_RIGHT - 70, "d: 'banner visible' runs into the key"
    no_overlaps(fig, 'd')
    no_digits(fig, 'd')
    finish(fig, 'figS9d_storec')
    print(f'S9d time segments (s): {segs}; scale {mm_per_s:.2f} mm/s; {n_ticks} ticks ({n_code_ticks} with the code)')
    return segs


if __name__ == '__main__':
    check_composite('figS9.tex', CELLS, FIG_H)
    fs.reset_registry()
    with fs.v7_context():
        boxes = dict(a=panel_a(), b=panel_b())
        panel_c()
        panel_d()
    check_alignment(boxes, ['ab'])
    write_registry('figS9')
    print(f'S9 panels written (figure 190 x {FIG_H:g} mm)')
