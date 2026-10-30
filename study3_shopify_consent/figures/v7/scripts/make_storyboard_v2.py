"""Hand-drawn-style storyboard of the v2 figure set (figures/v7/FIGURE_PLAN_v2.md) for the mentor.

One A4-landscape page per main figure (drawn at its real 190 mm width on the mm grid of the plan), plus a cover and a
supplement / graphical-abstract page. Shapes are placeholders and every page is stamped SKETCH. Every number printed is
read from analysis/outputs/stats.json or figures/v7/derived_numbers.json (none typed by hand); the Fig 1C and 5C
sketches plot the real event times from the analysis tables.

Run:  python3 figures/v7/scripts/make_storyboard_v2.py      -> figures/v7/storyboard_v2.pdf
"""
import json
import logging
import os
import sys
import textwrap

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle  # noqa: E402

logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT = os.path.join(ROOT, 'analysis', 'outputs')
sys.path.insert(0, os.path.join(ROOT, 'figures'))
from colors import ACCENT, GREY_D, GREY_L, GREY_M, INK, VENDOR, VENDOR_ORDER  # noqa: E402

S = json.load(open(os.path.join(OUT, 'stats.json')))
DN = {k: v['value'] for k, v in json.load(open(os.path.join(ROOT, 'figures', 'v7', 'derived_numbers.json'))).items()}
DST = os.path.join(ROOT, 'figures', 'v7', 'storyboard_v2.pdf')

RED, MID, LIGHT = ACCENT, GREY_M, GREY_L
FX, FY = 10, 30          # figure frame origin on the page (mm)
NX = 207                 # notes column x (mm)


# ---------------- numbers (read, never typed) ----------------
def g(*path):
    d = S
    for p in path:
        d = d[p]
    return d


def kn(d):
    return f"{d['k']:,}/{d['n']:,}"


def kof(d):
    return f"{d['k']:,} of {d['n']:,}"


def pc(d, dec=0):
    return f"{100 * d['k'] / d['n']:.{dec}f}%"


def fr(d):
    return d['k'] / d['n']


def pp(x, dec=1):
    return f'{100 * x:.{dec}f}'


# ---------------- drawing primitives (mm, y down) ----------------
class Page:
    def __init__(self, pdf, title, H, notes, number):
        self.pdf, self.H = pdf, H
        self.fig = plt.figure(figsize=(297 / 25.4, 210 / 25.4))
        self.ax = ax = self.fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 297)
        ax.set_ylim(210, 0)
        ax.axis('off')
        self.t(8, 9, title, fs=12.5, weight='bold', ha='left', abs_=True)
        self.t(8, 17, 'SKETCH - placeholder shapes, not to scale inside panels; every number is read from stats.json / '
                      'derived_numbers.json', fs=7, color=GREY_D, ha='left', abs_=True)
        self.t(286, 10, 'SKETCH', fs=16, color=RED, weight='bold', ha='right', abs_=True,
               bbox=dict(boxstyle='round,pad=0.3', fc='white', ec=RED, lw=1.2))
        if H:
            ax.add_patch(Rectangle((FX, FY), 190, H, fill=False, ec=GREY_M, lw=0.6, ls=(0, (4, 3))))
            self.t(FX + 190, FY + H + 4, f'190 x {H} mm (final print size)', fs=6.5, color=GREY_M, ha='right', abs_=True)
            ax.text(FX + 95, FY + H / 2, 'SKETCH', fontsize=70, color=RED, alpha=0.06, rotation=20, ha='center',
                    va='center', weight='bold', zorder=0)
        y = 30
        for head, body in notes:
            self.t(NX, y, head, fs=8.5, weight='bold', ha='left', abs_=True)
            y += 5
            for line in textwrap.wrap(body, 50):
                self.t(NX, y, line, fs=7, ha='left', abs_=True, color=INK)
                y += 3.6
            y += 3
        self.t(286, 204, f'storyboard v2 - ' + (f'Figure {number}' if 1 <= number <= 6 else ('cover' if number == 0 else 'supplement')),
               fs=6.5, color=GREY_M, ha='right', abs_=True)

    # all coordinates below are figure-relative mm unless abs_=True
    def P(self, x, y):
        return FX + x, FY + y

    def t(self, x, y, s, fs=7, ha='center', va='center', color=INK, weight='normal', abs_=False, **kw):
        X, Y = (x, y) if abs_ else self.P(x, y)
        self.ax.text(X, Y, s, fontsize=fs, ha=ha, va=va, color=color, weight=weight, **kw)

    def box(self, x, y, w, h, text=None, fs=6.8, ec=INK, fc='white', hatch=None, lw=0.9, ls='-', tc=INK, weight='normal'):
        X, Y = self.P(x, y)
        self.ax.add_patch(Rectangle((X, Y), w, h, fc=fc, ec=ec, lw=lw, hatch=hatch, ls=ls))
        if text:
            self.t(x + w / 2, y + h / 2, text, fs=fs, color=tc, weight=weight, linespacing=1.15)

    def arrow(self, x1, y1, x2, y2, color=INK, lw=1.0, ls='-', rad=0.0):
        self.ax.add_patch(FancyArrowPatch(self.P(x1, y1), self.P(x2, y2), arrowstyle='-|>', mutation_scale=8, lw=lw,
                                          color=color, ls=ls, connectionstyle=f'arc3,rad={rad}'))

    def line(self, xs, ys, color=INK, lw=1.0, ls='-', **kw):
        self.ax.plot([FX + x for x in xs], [FY + y for y in ys], color=color, lw=lw, ls=ls, **kw)

    def mark(self, x, y, arm, ms=5.5):
        st = {'Default': dict(marker='o', mfc=INK, mec=INK), 'Decline': dict(marker='s', mfc='white', mec=GREY_D),
              'GPC': dict(marker='^', mfc=GREY_M, mec=GREY_M), 'Repeat': dict(marker='D', mfc='white', mec=GREY_D),
              'open': dict(marker='o', mfc='white', mec=INK)}[arm]
        self.ax.plot([FX + x], [FY + y], ls='none', ms=ms, mew=1.0, zorder=5, **st)

    def panel(self, L, x, y, w, h, title=None):
        self.box(x, y, w, h, ec=GREY_M, lw=0.5, ls=(0, (2, 2)), fc='none')
        self.t(x + 1, y + 2.5, L, fs=12, weight='bold', ha='left')
        if title:
            self.t(x + 7, y + 2.8, title, fs=7.5, weight='bold', ha='left')

    def leak(self, x, y, n):
        X, Y = self.P(x, y)
        self.ax.add_patch(Circle((X, Y), 2.6, fc=RED, ec='white', lw=0.8, zorder=6))
        self.ax.text(X, Y + 0.2, str(n), fontsize=7, color='white', weight='bold', ha='center', va='center', zorder=7)

    def hbar(self, x0, y, length, h, color, ec='none', hatch=None):
        X, Y = self.P(x0, y - h / 2)
        self.ax.add_patch(Rectangle((X, Y), length, h, fc=color, ec=ec, lw=0.6, hatch=hatch))

    def vbar(self, x, y0, height, w, color):
        X, Y = self.P(x - w / 2, y0 - height)
        self.ax.add_patch(Rectangle((X, Y), w, height, fc=color, ec='none'))

    def done(self):
        self.pdf.savefig(self.fig)
        plt.close(self.fig)


# ---------------- pages ----------------
def cover(pdf):
    p = Page(pdf, 'Study 3 figures, v2 storyboard (for the mentor)', 0, [], 0)
    titles = [
        ('1', 'Consent is lost at five points between the cookie banner and Shopify\'s sandboxed pixels', 'situating'),
        ('2', 'We load each store three ways and label every ad request, even inside the sandboxes', 'method'),
        ('3', "Before any choice, firing tracks Shopify's region default, even within one consent tool", 'result'),
        ('4', 'Blocked on paper: blocklisted vendors still fire from the sandbox; blocklists do not lower firing',
         'result'),
        ('5', 'A refusal stops new pixels that declare it; earlier, other-purpose and undeclared pixels keep sending',
         'result / validation'),
        ('6', "Vendors receive the URL, even a creator's per-video code, but not the refusal", 'application'),
    ]
    y = 34
    p.t(10, y - 6, 'Six main figures, one claim each (titles read in order = the paper\'s argument)', fs=9,
        weight='bold', ha='left', abs_=True)
    for n, t_, role in titles:
        p.t(12, y, f'Fig {n}', fs=8.5, weight='bold', ha='left', abs_=True)
        p.t(28, y, t_, fs=8, ha='left', abs_=True)
        p.t(240, y, role, fs=7.5, color=GREY_D, ha='left', abs_=True)
        y += 8
    y += 4
    p.t(10, y, 'One meaning per mark (applies to every figure)', fs=9, weight='bold', ha='left', abs_=True)
    y += 8
    for i, (arm, lab) in enumerate([('Default', 'Default (no interaction)'), ('Decline', 'Decline (reject clicked)'),
                                    ('GPC', 'GPC (Global Privacy Control)'), ('Repeat', 'Repeat / validation')]):
        X = 14 + i * 62
        p.ax.plot([X], [y], **dict(Default=dict(marker='o', mfc=INK, mec=INK), Decline=dict(marker='s', mfc='white', mec=GREY_D),
                                     GPC=dict(marker='^', mfc=GREY_M, mec=GREY_M), Repeat=dict(marker='D', mfc='white', mec=GREY_D))[arm],
                  ms=6, ls='none')
        p.t(X + 4, y, lab, fs=7.5, ha='left', abs_=True)
    y += 9
    p.ax.add_patch(Rectangle((11, y - 2.5), 8, 5, fc=RED, ec='none'))
    p.t(22, y, 'red = consent failed, and nothing else (never next to vendor colours)', fs=7.5, ha='left', abs_=True)
    p.ax.add_patch(Rectangle((150, y - 2.5), 8, 5, fc='white', ec=GREY_M, hatch='////', lw=0.6))
    p.t(161, y, 'hatch = runs in a Shopify sandbox (worker or iframe)', fs=7.5, ha='left', abs_=True)
    y += 9
    for i, v in enumerate(VENDOR_ORDER):
        X = 12 + i * 38
        p.ax.add_patch(Rectangle((X, y - 2), 5, 4, fc=VENDOR[v], ec='none'))
        p.t(X + 7, y, v, fs=7.5, ha='left', abs_=True)
    y += 5
    p.t(12, y + 2, 'vendor colours = identity only (fixed order); text is always ink', fs=7, color=GREY_D, ha='left', abs_=True)
    y += 12
    p.t(10, y, 'Standards used for the build (not visible in a sketch)', fs=9, weight='bold', ha='left', abs_=True)
    y += 7
    for line in ['190 mm wide, <= 230 mm tall; vector PDF composed in LaTeX standalone (no rasters, no AI images)',
                 '12 pt bold UPPERCASE panel letters on a shared baseline; 9 pt axis titles, 8 pt ticks/legend, '
                 '7-8 pt annotations',
                 'white backgrounds; axes 0.6 pt; data 1.25 pt; one CI weight (0.8 pt); arrows 0.8 pt; boxes 0.6 pt',
                 '<= ~700 characters of text inside each figure; no subtitles or footnotes; detail -> Fig S6-S9']:
        p.t(12, y, '- ' + line, fs=7.5, ha='left', abs_=True)
        y += 6
    p.done()


def fig1(pdf):
    H = 150
    reg, share = g('fig1b', 'region_allowed'), g('fig3', 'c', 'share_sandbox_boot')
    deny, gnp, f3 = g('fig5', 'd', 'deny'), g('fig5', 'c', 'gpc_nopurpose_fired'), g('fig5', 'c', 'fig5c_rows', 'f3')
    bf, nbf = g('fig1b', 'banner_fires'), g('fig1b', 'nobanner_fires')
    lead = DN['fig1c_lead_ms']
    notes = [('Takeaway', f"Ad pixels run in sandboxes the banner's blocker cannot see; a sandboxed pixel fired before "
                          f"any choice on {kof(bf)} banner stores ({pc(bf)}) and {kof(nbf)} without a banner."),
             ('Hero', 'A: the pipeline on white with five numbered red leak points, each keyed to the figure that '
                      'measures it (different units, so no single flow diagram).'),
             ('Replaces', f"old 1a (restyled + leaks), 1b (region-default bar -> badge 1), 1c (0-{S['design']['timeline_axis_s']} s, URL dots dropped)."),
             ('Red here', 'leak markers and the banner bar only; vendors in grey in A; C uses vendor colours and no red.')]
    p = Page(pdf, 'Figure 1 - Consent is lost at five points between the cookie banner and the sandbox', H, notes, 1)
    # A: pipeline
    p.panel('A', 0, 0, 190, 78)
    p.box(3, 26, 22, 18, 'visitor\n(link with\ntest code)')
    p.box(30, 6, 92, 50, ec=GREY_D, lw=0.7)
    p.t(32, 9.5, 'storefront page (main thread)', fs=6.5, ha='left', color=GREY_D)
    p.box(34, 14, 36, 14, 'cookie banner (CMP)\n+ script blocker')
    p.box(34, 38, 36, 12, 'vendor page tag\n(blocked)')
    p.line([52, 52], [28, 38], color=GREY_D, lw=0.8, ls=':')
    p.t(53, 33, "blocker's reach", fs=5.8, ha='left', color=GREY_D)
    gx, gy = 92, 31
    X, Y = p.P(gx, gy)
    p.ax.add_patch(Polygon([(X - 8, Y), (X, Y - 7), (X + 8, Y), (X, Y + 7)], closed=True, fc='white', ec=INK, lw=0.9))
    p.t(gx, gy, 'Shopify\ngate', fs=6.3)
    p.box(128, 20, 26, 24, 'Shopify\nsandboxes\nworker | iframe', hatch='////', ec=GREY_M, tc=INK)
    p.box(160, 12, 28, 42, None, ec=GREY_D)
    p.t(174, 16, 'ad vendors', fs=6.8, weight='bold')
    for i, v in enumerate(VENDOR_ORDER):
        p.t(174, 21 + i * 4.4, v, fs=6, color=GREY_D)
    p.arrow(25, 35, 30, 35)
    p.arrow(70, 21, 85, 28)
    p.t(74, 20, 'writes choice', fs=5.8, ha='left', color=GREY_D)
    p.arrow(100, 31, 128, 31)
    p.t(114, 28.5, 'starts pixel', fs=5.8, color=GREY_D)
    p.arrow(154, 32, 160, 32)
    p.arrow(70, 46, 160, 50, color=GREY_M, ls='--')
    p.arrow(92, 54, 92, 38.5)
    p.t(92, 57.5, "region default, GPC", fs=5.8, color=GREY_D)
    p.line([70, 126], [16, 22], color=RED, lw=0.8, ls=':')
    for n, (x, y) in enumerate([(84, 44), (122, 17), (78, 24.5), (112, 34), (157, 28)], start=1):
        p.leak(x, y, n)
    badges = [f"default 'allowed' {kn(reg)} stores (Fig 3)",
              f"blind spot: {100 * fr(share):.1f}% of {share['n']:,} requests sandboxed (Fig 4)",
              f"late 'no': {deny['pixels_before']}/{deny['pixels']} started first (Fig 5C)",
              f"no purpose declared: {kn(gnp)} GPC stores (Fig 5B)",
              f"not stopped: {kn(f3)} after Decline (Fig 5B)"]
    for i, b in enumerate(badges):
        x, y = 4 + (i % 2) * 94, 62 + (i // 2) * 6.2
        p.leak(x + 2, y, i + 1)
        p.t(x + 6, y, b, fs=6.2, ha='left')
    # B: two bars
    p.panel('B', 0, 84, 62, 66)
    x0, W = 20, 36
    for (lab, d, col, y) in [(f"banner\n({d_n(bf)})", bf, RED, 104), (f"no banner\n({d_n(nbf)})", nbf, MID, 124)]:
        p.hbar(x0, y, W * fr(d), 6, col)
        p.line([x0 + W * d['lo'], x0 + W * d['hi']], [y, y], lw=0.9)
        p.t(x0 - 1.5, y, lab, fs=6.3, ha='right')
        p.t(x0 + W * fr(d), y - 6, f"{pc(d)}  {kn(d)}", fs=6.5, ha='center')
    p.t(x0 + W * 0.5, 131.5, 'no choice offered', fs=5.8, color=GREY_D)
    p.line([x0, x0 + W], [140, 140], color=GREY_M, lw=0.6)
    for v in (0, 50, 100):
        p.t(x0 + W * v / 100, 143, f'{v}', fs=6)
    p.t(x0 + W / 2, 147, 'stores firing before any choice (%)', fs=6)
    # C: real timeline
    p.panel('C', 68, 84, 122, 66)
    tl = pd.read_csv(os.path.join(OUT, 'fig1c_timeline.csv'))
    rows = VENDOR_ORDER + ['outside sandbox']
    xa, xs = 100, 14.5  # x at 0 s, mm per s
    for i, r in enumerate(rows):
        y = 94 + i * 5.6
        p.t(xa - 3, y, r, fs=6, ha='right', color=GREY_D if r == 'outside sandbox' else INK)
    for r in tl.itertuples():
        if r.t_ms > 6000:
            continue
        i = rows.index(r.vgroup) if r.sandbox else len(rows) - 1
        y = 94 + i * 5.6
        h = 3.6 if r.beacon else 2.0
        col = VENDOR[r.vgroup] if r.sandbox else GREY_M
        p.line([xa + xs * r.t_ms / 1000] * 2, [y - h / 2, y + h / 2], color=col, lw=1.2)
    tb = g('fig1c', 't_banner') / 1000
    p.line([xa + xs * tb] * 2, [91, 139], lw=1.0)
    p.t(xa + xs * tb + 1, 90, 'banner visible', fs=6, ha='left')
    t1 = g('fig1c', 't_first_sandboxed') / 1000
    p.line([xa + xs * t1, xa + xs * t1, xa + xs * tb, xa + xs * tb], [137, 139.5, 139.5, 137], color=INK, lw=0.8)
    p.t(xa + xs * t1 - 1, 140.5, f"first sandboxed request {lead['first_sandboxed_lead_ms'] / 1000:.2f} s before the banner",
        fs=5.8, ha='right')
    p.line([xa, xa + xs * 6], [144, 144], color=GREY_M, lw=0.6)
    for v in range(0, 7):
        p.t(xa + xs * v, 146.8, f'{v}', fs=6)
    p.t(xa - 3, 146.8, 's', fs=6, ha='right')
    p.t(188, 134, f"+{lead['n_beyond_axis']}\nlater ->", fs=5.6, ha='right', color=GREY_D)
    p.done()


def d_n(d):
    return f"{d['n']:,}"


def fig2(pdf):
    H = 150
    fu = DN['fig2a_funnel']
    wr = DN['fig2b_worked_request']
    notes = [('Takeaway', f"{fu['captured']:,} stores, three arms each; every ad request labelled by origin, vendor, "
                          f"timing, payload, including inside the sandboxes; labels repeat (kappa "
                          f"{g('validation', 'A0_vs_A0r', 'kappa'):.3f})."),
             ('Hero', 'B: drawing of the trick (the crawler plugs into the page, the worker and the iframe) and one real '
                      'request dissected (the first sandboxed beacon with our test code in the Fig 1C load).'),
             ('Replaces', 'old 2a (bars now scale with n), 2b table -> C time strips (+ Table S-arms), 2c prose -> B, '
                          '2d pointers -> D data (+ Fig S4).')]
    p = Page(pdf, 'Figure 2 - How the measurement works (methodology)', H, notes, 2)
    # A funnel
    p.panel('A', 0, 0, 58, 72)
    steps = [('Tranco top list', fu['tranco']), ("DNS points to Shopify", fu['flagged']), ('verified', fu['verified']),
             ('live storefronts', fu['live']), ('sampled', fu['sample']), ('captured, 3 arms', fu['captured'])]
    lo, hi = 3.0, np.log10(fu['tranco'])
    for i, (lab, v) in enumerate(steps):
        y = 12 + i * 9.5
        L = 4 + 44 * (np.log10(v) - lo) / (hi - lo)
        p.hbar(3, y, L, 4, INK if i == len(steps) - 1 else MID)
        p.t(3, y - 3.8, f'{lab}  {v:,}', fs=5.9, ha='left')
    p.t(55, 68, f"+{fu['creator']} creator\nstores (separate)", fs=5.6, ha='right', color=GREY_D)
    p.arrow(38, 66, 12, 60.5, color=GREY_D, lw=0.7)
    # B instrumentation + worked request
    p.panel('B', 64, 0, 126, 72)
    p.box(68, 8, 70, 50, ec=GREY_D)
    p.box(68, 8, 70, 4, 'browser (one page load)', fs=5.8, fc=LIGHT, ec=GREY_D)
    p.box(71, 16, 30, 18, 'page (main thread)\nCMP + blocker')
    p.box(105, 16, 30, 18, 'web worker\n(STRICT)', hatch='////', ec=GREY_M)
    p.box(71, 38, 64, 16, 'sandboxed iframe (LAX)', hatch='////', ec=GREY_M)
    p.box(78, 62, 50, 7, 'crawler (DevTools): attach + inject GPC', fs=5.8)
    for x in (86, 120, 103):
        p.line([x, x], [62, 54 if x == 103 else 34], color=INK, lw=0.7, ls=':')
    p.box(144, 8, 44, 58, ec=INK)
    p.t(166, 12, 'one captured request', fs=6.3, weight='bold')
    rows = [('host', wr['host']), ('vendor', f"{wr['vgroup']} Ads"), ('origin', 'sandboxed iframe (LAX)'),
            ('timing', f"{wr['before_banner_ms']:.0f} ms before banner"),
            ('payload', f"{wr['carrier_param']}=...{wr['carried_path']}"), ('', f"?utm_campaign={wr['test_code']}")]
    for i, (k, v) in enumerate(rows):
        y = 19 + i * 7.5
        if k:
            p.t(146, y, k, fs=5.8, ha='left', color=GREY_D)
        p.t(146, y + 3, v, fs=5.3, ha='left', color=INK, weight='bold' if 'utm' in v else 'normal',
            bbox=dict(fc='none', ec=INK, lw=0.5, pad=1.2) if 'utm' in v else None)
    p.arrow(135, 46, 144, 46, lw=0.8)
    # C arms
    p.panel('C', 0, 78, 120, 72)
    arms = [('Default', 'no interaction', [('before banner', 28, 44), ('before any choice', 28, 98)]),
            ('Decline', 'reject clicked', [('page 1', 28, 58), ('same page', 58, 70), (f"fresh page {S['design']['next_page_observe_s']} s", 70, 98)]),
            ('GPC', 'signal on', [(f"whole load ({S['design']['equal_window_s']} s window for comparisons)", 28, 98)])]
    for i, (arm, sub, segs) in enumerate(arms):
        y = 92 + i * 15
        p.mark(4, y, arm)
        p.t(7, y - 1.5, arm, fs=6.5, ha='left', weight='bold')
        p.t(7, y + 2, sub, fs=5.4, ha='left', color=GREY_D)
        for lab, a, b in segs:
            p.box(a, y - 2.5, b - a, 5, None, ec=GREY_D, lw=0.6)
            p.t((a + b) / 2, y - 5, lab, fs=5.4)
        if arm == 'Decline':
            p.line([58, 58], [y - 4, y + 4], color=INK, lw=1.2)
            p.t(58, y + 5.5, 'click', fs=5.2)
            p.line([70, 70], [y - 4, y + 4], color=INK, lw=1.2)
            p.t(70, y + 5.5, 'reload', fs=5.2)
    nm = S['design']['n_main']
    p.t(101, 92, f'{nm:,}', fs=6, ha='left')
    p.t(101, 107, f"{nm:,}; click\n{g('fig5', 'decline', 'clicked_all')} -> works {g('fig5', 'decline', 'clicked')}", fs=5.4, ha='left')
    p.t(101, 122, f'{nm:,}', fs=6, ha='left')
    p.mark(4, 138, 'Repeat')
    p.t(7, 138, f"repeat Default + GPC ({S['context']['repeat_main_ok']} stores); Brave native GPC "
                f"({S['context']['brave_ok']})", fs=5.8, ha='left')
    # D validation
    p.panel('D', 126, 78, 64, 72)
    vrows = [('Default vs repeat', g('validation', 'A0_vs_A0r')), ('GPC vs repeat', g('validation', 'A2_vs_A2r')),
             ('Brave vs emulated', g('validation', 'A2_vs_V1')), ('audit: banner', g('supp', 'S4', 'banner_precision')),
             ('audit: reject', g('supp', 'S4', 'reject_agreement')), ('audit: click', g('supp', 'S4', 'click_flag_agreement'))]
    xa, xw = 152, 20
    for i, (lab, d) in enumerate(vrows):
        y = 90 + i * 8
        k, n = (d['agree'], d['n']) if 'agree' in d else (d['k'], d['n'])
        p.t(xa - 2, y, lab, fs=5.6, ha='right')
        p.mark(xa + xw * (k / n - 0.9) / 0.1, y, 'Repeat', ms=4.5)
        p.t(xa + xw + 2.5, y, f'{k}/{n}', fs=5.4, ha='left')
    p.line([xa, xa + xw], [140, 140], color=GREY_M, lw=0.6)
    p.t(xa, 143, '90%', fs=5.6)
    p.t(xa + xw, 143, '100%', fs=5.6)
    p.t(xa + xw / 2, 147, 'agreement', fs=5.6)
    p.done()


def fig3(pdf):
    H = 128  # plan grid as built (C is 30 mm tall; see FIGURE_PLAN_v2.md section 8)
    a, d = g('fig3', 'd', 'opt_out'), g('fig3', 'd', 'opt_in')
    mh = g('fig3', 'd', 'mh_by_product')
    ts = DN['fig3c_timing_split']
    notes = [('Takeaway', f"Banner stores fired before any choice on {pc(a['any_sbx'], 1)} ({kn(a['any_sbx'])}) where the "
                          f"default allowed and {pc(d['any_sbx'], 1)} ({kn(d['any_sbx'])}) where it denied; "
                          f"+{pp(mh['rd'])} pp within the same consent tool."),
             ('Hero', 'A: two big bars (red = consent failed) with the within-product bracket.'),
             ('Replaces', 'old 3d -> A + B; old 3b -> C as a 3-part bar (curve to S6B); old 3a -> S6A; old 3c -> S6C; '
                          f"the {100 * fr(g('fig3', 'c', 'share_sandbox_boot')):.1f}% overall -> Fig 1 badge 2.")]
    p = Page(pdf, "Figure 3 - Before any choice, firing tracks Shopify's region default", H, notes, 3)
    p.panel('A', 0, 0, 84, 92)
    base, top = 80, 22
    p.line([12, 12], [base, top], color=GREY_M, lw=0.6)
    for v in (0, 50, 100):
        p.t(10, base - (base - top) * v / 100, f'{v}', fs=6, ha='right')
    for x, dd, lab in [(30, a['any_sbx'], "default\n'allowed'"), (62, d['any_sbx'], "default\n'denied'")]:
        h = (base - top) * fr(dd)
        p.vbar(x, base, h, 9, RED)
        p.line([x, x], [base - (base - top) * dd['lo'], base - (base - top) * dd['hi']], lw=0.9)
        p.t(x, base - (base - top) * dd['hi'] - 5.5, f"{pc(dd)}\n{kn(dd)}", fs=6.5)
        p.t(x, base + 6, lab + f"\n(n = {dd['n']})", fs=6)
    p.line([30, 30, 62, 62], [19, 15, 15, 45], color=INK, lw=0.7)
    p.t(46, 10.5, f"+{pp(mh['rd'], 0)} pp within the same consent tool", fs=5.8)
    p.panel('B', 90, 0, 100, 92)
    rows = [("declares 'marketing'", 'mkt_sbx'), ("does not declare\n'marketing'", 'nomkt_sbx'), ('  of which: no purpose', 'nopurpose_sbx')]
    xa, xw = 132, 54
    for i, (lab, key) in enumerate(rows):
        y = 22 + i * 20
        p.t(xa - 3, y, lab, fs=6.2, ha='right')
        pa, pd_ = fr(a[key]) / 0.75, fr(d[key]) / 0.75
        p.line([xa + xw * pd_, xa + xw * pa], [y, y], color=GREY_M, lw=1.0)
        p.mark(xa + xw * pa, y, 'Default')
        p.mark(xa + xw * pd_, y, 'open')
        p.t(xa + xw * pa, y - 4.5, kn(a[key]), fs=5.6)
        p.t(xa + xw * pd_, y + 4.5, kn(d[key]), fs=5.6)
    p.line([xa, xa + xw], [80, 80], color=GREY_M, lw=0.6)
    for v in (0, 25, 50, 75):
        p.t(xa + xw * v / 75, 83, f'{v}', fs=6)
    p.mark(140, 88, 'Default', ms=4.5)
    p.t(142, 88, "'allowed'", fs=5.8, ha='left')
    p.mark(160, 88, 'open', ms=4.5)
    p.t(162, 88, "'denied'", fs=5.8, ha='left')
    p.panel('C', 0, 98, 190, 30)
    x0, W, y = 22, 160, 110
    parts = [('more than one poll before', ts['more_than_one_poll_before'], INK, 'white'),
             ('within one poll', ts['within_one_poll_before'], MID, INK),
             ('banner first', ts['banner_first_or_same'], LIGHT, INK)]
    x = x0
    for lab, v, col, tc in parts:
        w = W * v / ts['n']
        p.hbar(x, y, w - 0.8, 10, col, ec=GREY_D if col == LIGHT else 'none')
        p.t(x + w / 2, y, f'{lab}: {v}', fs=6.2, color=tc)
        x += w
    p.t(x0 - 2, y, f"{ts['n']}\nstores", fs=6.2, ha='right')
    p.t(x0, 121, 'first sandboxed request, relative to the banner becoming visible (polls every '
                 f"{ts['poll_ms']} ms)", fs=6, ha='left', color=GREY_D)
    p.done()


def fig4(pdf):
    H = 101  # plan grid as built: A and B 56 mm, C 39 mm (see FIGURE_PLAN_v2.md section 8)
    r = DN['fig4a_routes']['primary_no_yes']
    lf = g('fig4', 'a', 'like_for_like')
    mh = lf['mh_no_yes']
    notes = [('Takeaway', f"Counted per blocklist entry, a vendor the consent tool listed as blocked still sent from "
                          f"Shopify's sandbox before any choice for {r['sandbox']} of {r['n']} entries "
                          f"({r['n_stores']} stores whose tool wrote no 'yes'); by store, "
                          f"{kof(g('fig4', 'a', 'blocklist', 'primary', 'fired'))} (RESULTS.md finding 3). "
                          f"Like for like, blocklists did not lower firing (+{pp(mh['rd'])} pp, 95% CI "
                          f"{pp(mh['rd_lo'])} to {pp(mh['rd_hi'])})."),
             ('Hero', f"A: the same {r['n']} blocklist entries (on {r['n_stores']} stores), by route. Corrected "
                      f"numbers: counted independently, the page route fired for {r['page']} (not the hierarchical "
                      f"'page only' count); {r['both']} fired by both routes."),
             ('Replaces', 'old 4c -> A (primary set, independent routes); old 4a like-for-like rows -> B; other 4a rows '
                          f"-> S7A; {kn(g('fig4', 'a', 'cpapi_deny', 'any_sbx'))} row -> S8D; old 4b heatmap -> S2B."),
             ('Mentor questions', '(a) keep C in the main set? (d) accept the corrected hero (independent routes) '
                                  'in place of the critiques\' hierarchical contrast?')]
    p = Page(pdf, 'Figure 4 - Blocked on paper', H, notes, 4)
    p.panel('A', 0, 0, 108, 56)
    n = r['n']
    order = ['both'] * r['both'] + ['sbx'] * r['sandbox_only'] + ['page'] * r['page_only'] + ['none'] * r['neither_route']
    for row, (lab, fired_if, y) in enumerate([("from Shopify's sandbox (a blocker cannot see)", ('both', 'sbx'), 17),
                                              ('from an ordinary page script (a blocker can see)', ('both', 'page'), 37)]):
        p.t(12 if row == 0 else 5, y - 6.5, lab, fs=6.5, ha='left')
        k = 0
        for i, e in enumerate(order):
            fired = e in fired_if
            k += fired
            X = 5 + i * 4.5
            p.box(X, y - 2, 3.8, 3.8, None, fc=RED if fired else 'white', ec=RED if fired else GREY_M, lw=0.6)
        p.t(5 + n * 4.5 + 2, y, f'{k} of {n}', fs=7, ha='left', weight='bold')
        if row == 0:
            p.box(5, y - 8.5, 5, 4, None, hatch='////', ec=GREY_M, lw=0.5)
    p.t(6, 49, f"1 square = 1 blocklist entry; red = sent before any choice; {r['both']} by both routes",
        fs=5.6, ha='left', color=GREY_D)
    p.panel('B', 114, 0, 76, 56)
    xa, xw = 140, 46
    for i, (lab, key) in enumerate([("default\n'allowed'", 'allowed_no_yes'), ("default\n'denied'", 'denied_no_yes')]):
        y = 15 + i * 15
        bl, rf = lf[key]['blocklist'], lf[key]['reference']
        p.t(xa - 3, y, lab, fs=6.2, ha='right')
        p.line([xa + xw * fr(rf), xa + xw * fr(bl)], [y, y], color=GREY_M)
        p.mark(xa + xw * fr(bl), y, 'Default')
        p.mark(xa + xw * fr(rf), y, 'open')
        p.t(xa + xw * fr(bl), y - 4, kn(bl), fs=5.8)
        p.t(xa + xw * fr(rf), y + 4, kn(rf), fs=5.8)
    p.line([xa, xa + xw], [40, 40], color=GREY_M, lw=0.6)
    for v in (0, 50, 100):
        p.t(xa + xw * v / 100, 43, f'{v}', fs=6)
    p.t(152, 48, f"+{pp(mh['rd'])} pp ({pp(mh['rd_lo'])} to {pp(mh['rd_hi'])}): no reduction", fs=5.8)
    p.mark(130, 53, 'Default', ms=4.5)
    p.t(132, 53, 'blocklist', fs=5.6, ha='left')
    p.mark(152, 53, 'open', ms=4.5)
    p.t(154, 53, 'no declaration', fs=5.6, ha='left')
    p.panel('C', 0, 62, 190, 39, 'one re-check load (built; mentor question a)')
    p.t(30, 75, 'vendor page tag', fs=6.3, ha='right')
    p.t(30, 88, 'Shopify sandbox', fs=6.3, ha='right')
    p.line([32, 186], [75, 75], color=GREY_M, lw=0.5)
    p.line([32, 186], [88, 88], color=GREY_M, lw=0.5)
    p.line([70, 70], [71, 79], lw=1.3)
    p.t(72, 71.5, 'neutralised by the blocker', fs=5.8, ha='left')
    for x in (62, 78, 81, 95, 120, 124, 150):
        p.line([x, x], [86, 90], color=GREY_D, lw=1.1)
    p.t(186, 97, f"placeholder positions; seen on {g('checks', 'recheck', 'blocker', 'stores_neutralized_and_sbx')} "
                 f"stores", fs=5.6, ha='right', color=GREY_D)
    p.done()


def fig5(pdf):
    H = 160
    A = g('fig5', 'a')
    cmp_ = g('fig5', 'compare')
    ga = g('fig5', 'c', 'gate_audit')
    ex = DN['fig5b_exclusive_classes']
    rc = DN['fig5c_race_per_sandbox']
    notes = [('Takeaway', f"The gate held ({kof(ga['gpc_sale_pixels'])} sale-declaring pixels started under GPC), "
                          f"yet on the same {A['n_clicked']} stores a new sandbox still fired after Decline on "
                          f"{A['Any vendor']['Decline']['k']} and under GPC on {A['Any vendor']['GPC']['k']} "
                          f"(Default {A['Any vendor']['Default']['k']}); {rc['deny']['before']} of "
                          f"{rc['deny']['sandboxes']} sandboxes started before the 'no'."),
             ('Hero', 'A: paired fan chart; B: the gate-held zero as a stat tile plus mutually exclusive reasons; '
                      'C: the race per sandbox on a linear axis.'),
             ('Replaces', 'old 5a -> A (vendor rows -> S8A); old 5c -> B (overlapping classes -> S8C); old 5d -> C '
                          '(per-load strip -> S8D); old 5b -> S8B.')]
    p = Page(pdf, 'Figure 5 - What a refusal stops, and what keeps sending', H, notes, 5)
    p.panel('A', 0, 0, 76, 92)
    x0, x1, yb, yt = 18, 54, 82, 16

    def Y(v):
        return yb - (yb - yt) * v / 0.5
    p.line([10, 10], [yb, yt], color=GREY_M, lw=0.6)
    for v in (0, 25, 50):
        p.t(8, Y(v / 100), f'{v}', fs=6, ha='right')
    for v in VENDOR_ORDER:
        d0 = fr(A[v]['Default'])
        for arm in ('Decline', 'GPC'):
            p.line([x0, x1], [Y(d0), Y(fr(A[v][arm]))], color=LIGHT, lw=0.6)
    av = A['Any vendor']
    for arm in ('Decline', 'GPC'):
        p.line([x0, x1], [Y(fr(av['Default'])), Y(fr(av[arm]))], color=INK, lw=1.3)
        p.mark(x1, Y(fr(av[arm])), arm)
        p.t(x1 + 3, Y(fr(av[arm])), f"{arm} {kn(av[arm])}", fs=6, ha='left')
    p.mark(x0, Y(fr(av['Default'])), 'Default')
    p.t(x0 + 2, Y(fr(av['Default'])) - 4.5, f"Default {kn(av['Default'])}", fs=6, ha='left')
    p.t(x0, yb + 5, 'Default', fs=6.3)
    p.t(x1, yb + 5, 'after the choice', fs=6.3)
    ew = cmp_['equal_window']
    p.t(x1 + 3, Y(0.30), f"{pp(ew['paired_diff']['diff'])} pp;\n{ew['a_only']} vs {ew['b_only']} stores", fs=5.5,
        ha='left', color=GREY_D)
    p.panel('B', 82, 0, 108, 92)
    for x, big, lab in [(88, kof(ga['gpc_sale_pixels']), 'sale-declaring pixels\nstarted under GPC'),
                        (138, kof(ga['default_denied_mkt_pixels']), 'marketing pixels held\n(denying default)')]:
        p.box(x, 8, 48, 26, None, ec=GREY_M, lw=0.6)
        p.t(x + 24, 16, big, fs=12, weight='bold')
        p.t(x + 24, 27, lab, fs=5.8, color=GREY_D)
    xa, xw = 112, 72
    scale = 0.35
    for i, (lab, blk) in enumerate([(f"Decline\n({ex['decline_refused']['n']})", ex['decline_refused']),
                                    (f"GPC\n({ex['gpc']['n']:,})", ex['gpc'])]):
        y = 50 + i * 16
        p.t(xa - 3, y, lab, fs=6, ha='right')
        x = xa
        segs = [('kept_sending_refused_purpose', RED), ('only_left_allowed_purposes', MID), ('no_purpose', LIGHT)]
        for key, col in segs:
            v = blk.get(key, 0)
            if not v:
                continue
            w = xw * (v / blk['n']) / scale
            p.hbar(x, y, w - 0.6, 7, col, ec=GREY_D if col == LIGHT else 'none')
            p.t(x + w / 2, y + 6.8, f'{v}', fs=5.6)
            x += w
        p.line([xa, xa], [y - 5, y + 5], lw=1.3)
    p.t(xa + 1, 40.5, '0 new pixels declaring the refused purpose', fs=5.6, ha='left')
    p.line([xa, xa + xw], [80, 80], color=GREY_M, lw=0.6)
    for v in (0, 10, 20, 30):
        p.t(xa + xw * v / 35, 83, f'{v}%', fs=5.8)
    for i, (col, lab) in enumerate([(RED, 'kept sending (refused purpose)'), (MID, 'only allowed purposes'),
                                    (LIGHT, 'no purpose declared')]):
        X, y = 90 + i * 33, 89
        p.box(X, y - 1.5, 3, 3, None, fc=col, ec=GREY_D if col == LIGHT else col, lw=0.5)
        p.t(X + 4, y, lab, fs=5.2, ha='left')
    p.panel('C', 0, 98, 190, 62)
    sc = pd.read_csv(os.path.join(OUT, 'sandbox_creations.csv'), low_memory=False, dtype={'pixel_id': str})
    f5d = pd.read_csv(os.path.join(OUT, 'fig5d.csv'))
    sc3 = sc[sc.declares_marketing & (sc.pixel_api.astype(str) != 'shopify-pixel') & (sc.kind != 'open_main_thread_pixel')]
    xz, xs = 150, 36  # x of 0 s, mm per s
    bins = np.arange(-3000, 1001, 100)
    for i, (ch, lab, yb_, hmax) in enumerate([('deny', "'no' written", 130, 22), ('grant', "'yes' written", 154, 16)]):
        j = sc3.merge(f5d[f5d.change == ch][['load_id', 't_update']], on='load_id')
        lag = np.clip((j.t_ms - j.t_update).values, -2999, 999)
        cnt, _ = np.histogram(lag, bins)
        mx = max(cnt.max(), 1)
        for c_, b0 in zip(cnt, bins[:-1]):
            if c_:
                col = RED if (ch == 'deny' and b0 < 0) else MID
                p.vbar(xz + xs * (b0 + 50) / 1000, yb_, hmax * c_ / mx, xs * 0.1 * 0.85, col)
        p.line([xz - 3 * xs, xz + xs], [yb_, yb_], color=GREY_M, lw=0.6)
        r_ = rc[ch]
        txt = (f"{lab}: {r_['before']} of {r_['sandboxes']} started before" if ch == 'deny'
               else f"{lab}: {r_['after']} of {r_['sandboxes']} started after")
        p.t(4, yb_ - hmax / 2, txt, fs=6.3, ha='left', weight='bold')
        edge = r_['n_below_clip'] if ch == 'deny' else r_['n_above_clip']
        p.t(xz - 3 * xs - 1 if ch == 'deny' else xz + xs - 1, yb_ - 4, (f'{edge} <-' if ch == 'deny' else f'{edge} beyond ->'),
            fs=5.6, ha='right', color=GREY_D)
    p.line([xz, xz], [104, 156], lw=1.0)
    p.t(xz + 1, 103, 'CMP writes consent', fs=6, ha='left')
    for v in (-3, -2, -1, 0, 1):
        p.t(xz + xs * v, 158.5, f'{v:+d} s' if v else '0', fs=5.8)
    p.done()


def fig6(pdf):
    H = 150
    cl = g('fig6', 'b', 'store_c')
    ad_ = g('fig6', 'b', 'store_c_after_decline')
    fa = g('fig6', 'a')
    fc = g('fig6', 'c')
    notes = [('Takeaway', f"{pc(fa['sandboxed_A0'], 1)} of {fa['sandboxed_A0']['n']:,} sandboxed ad beacons carried "
                          f"the full landing URL with our test code; on Store C the per-video code reached TikTok from "
                          f"its sandbox before any choice; after a Decline only Google and Microsoft carried a refusal "
                          f"signal (others {kof(fc['Other vendors']['Decline'])})."),
             ('Hero', 'A: the creator case as a flow with a load-by-load check grid (red = the code reached TikTok '
                      'before any choice; TikTok drawn in grey because red is present).'),
             ('Replaces', 'old 6c -> A (full timeline -> S9D); old 6a -> C, Default only (arms -> S9A); old 6b -> D '
                          '(detail -> S9B, S9C); new B from the creator-stratum results.')]
    p = Page(pdf, "Figure 6 - What reaches the vendors (application)", H, notes, 6)
    p.panel('A', 0, 0, 124, 78)
    p.box(4, 9, 26, 20, 'creator video\nlink with\nper-video code', fs=6)
    p.box(36, 9, 24, 20, 'Store C\nlanding page', fs=6)
    p.box(66, 9, 26, 20, 'TikTok pixel\n(sandbox)', hatch='////', ec=GREY_M, fs=6)
    p.box(98, 9, 22, 20, 'TikTok\nserver', fs=6, ec=GREY_D)
    p.arrow(30, 19, 36, 19)
    p.arrow(60, 19, 66, 19)
    p.arrow(92, 19, 98, 19, color=RED, lw=1.4)
    p.t(95, 33, 'code, before any choice', fs=5.6, color=INK)
    cols = [('Default', 'Default', cl['A0']['n_creator_token_tiktok_sbx']),
            ('repeat', 'Repeat', cl['A0r']['n_creator_token_tiktok_sbx']),
            ('Decline:\nbefore click', 'Decline', cl['A1']['n_creator_token_tiktok_sbx']),
            ('Decline:\nafter reload', 'Decline', ad_['tiktok']),
            ('GPC', 'GPC', cl['A2']['n_creator_token_tiktok_sbx']),
            ('GPC repeat', 'Repeat', cl['A2r']['n_creator_token_tiktok_sbx'])]
    for i, (lab, arm, v) in enumerate(cols):
        x = 8 + i * 19
        p.mark(x + 7, 40, arm, ms=4.5)
        p.t(x + 7, 46, lab, fs=5.6)
        p.box(x, 52, 15, 16, None, ec=GREY_M, lw=0.5)
        if v:
            p.vbar(x + 7.5, 66, 12 * v / 4, 5, RED)
            p.t(x + 7.5, 71.5, f'{v} requests', fs=5.4)
        else:
            p.t(x + 7.5, 60, '0', fs=7, color=GREY_D)
    p.t(4, 75, f"after the reload the code still reached {ad_['n_vendors']} other vendors, "
               f"{ad_['n_vendors_sandboxed']} from a sandbox; under GPC {cl['A2']['n_vendors_with_token']}, "
               f"{cl['A2']['n_sandboxed']} from a sandbox", fs=5.6, ha='left', color=GREY_D)
    p.panel('B', 130, 0, 60, 78)
    b = g('fig6', 'b')
    xa, xw = 150, 34
    for i, (lab, key) in enumerate([('an ad vendor', 'creator_token_reached_ad_vendor_A0'),
                                    ('a non-Google\nvendor', 'creator_token_reached_nongoogle_A0'),
                                    ('from a sandbox', 'creator_token_reached_sandboxed_A0')]):
        y = 22 + i * 16
        d = b[key]
        p.hbar(xa, y, xw * fr(d), 4, INK)
        p.t(xa - 1.5, y, lab, fs=5.8, ha='right')
        p.t(xa + xw * fr(d) + 1, y - 5, kn(d), fs=5.8)
    p.t(160, 72, f"all {b['creator_stores']} creator stores", fs=5.8, color=GREY_D)
    p.panel('C', 0, 84, 110, 66)
    xa, xw = 30, 64
    for i, v in enumerate(VENDOR_ORDER):
        y = 94 + i * 6.5
        d = fa[v]['Default']
        p.hbar(xa, y, xw * fr(d), 4, VENDOR[v])
        p.t(xa - 1.5, y, v, fs=5.8, ha='right')
        p.t(xa + xw * fr(d) + 1, y, pc(d), fs=5.6, ha='left')
    ref = fr(fa['sandboxed_A0'])
    p.line([xa + xw * ref] * 2, [90, 141], color=INK, lw=0.7)
    p.t(xa + xw * ref, 144, f"all vendors {pc(fa['sandboxed_A0'], 1)}", fs=5.8)
    p.panel('D', 116, 84, 74, 66)
    xa, xw = 148, 36
    for i, (lab, key, col) in enumerate([('Google', 'Google', VENDOR['Google']), ('Microsoft', 'Microsoft', VENDOR['Microsoft']),
                                         ('all other\nvendors', 'Other vendors', MID)]):
        y = 100 + i * 12
        d = fc[key]['Decline']
        p.t(xa - 1.5, y, lab, fs=5.8, ha='right')
        if d['k']:
            p.hbar(xa, y, xw * fr(d) / 0.5, 5, col)
            p.t(xa + xw * fr(d) / 0.5 + 1, y, f"{pc(d, 1)}", fs=5.8, ha='left')
        else:
            p.line([xa, xa], [y - 3, y + 3], lw=1.3)
            p.t(xa + 1.5, y, f"0 of {d['n']:,}", fs=5.8, ha='left')
    p.line([xa, xa + xw], [138, 138], color=GREY_M, lw=0.6)
    p.t(xa, 141, '0', fs=5.8)
    p.t(xa + xw, 141, '50%', fs=5.8)
    p.t(153, 146, 'requests with a refusal signal, next page after Decline', fs=5.4, color=GREY_D)
    p.done()


def supp(pdf):
    p = Page(pdf, 'Supplementary figures S1-S9 and the graphical abstract', 0, [], 7)
    tiles = [('S1', 'WPM architecture', 'restyled, A-D, white, Arial only'),
             ('S2', 'Per consent tool', 'A small multiples; B old 4b heatmap, grey ramp, no cell text'),
             ('S3', 'By Tranco rank', f"tighter; muted n = {int(g('fig5', 'e', 'buckets', '1-10k', 'n_captured'))} row"),
             ('S4', 'Audit + repeat agreement', 'bigger matrices; kappa; notes to caption'),
             ('S5', 'Sensitivity', 'A-C; main-CI hairlines; definition rows apart; file figS5.pdf'),
             ('S6', 'Before any choice: detail', 'old 3a, 3b curve, 3c origins, product strata'),
             ('S7', 'Blocked on paper: detail', f"old 4a rows, all-store routes, {g('fig4', 'c', 'nocfg', 'n')} no-config entries, re-check"),
             ('S8', 'Choices: detail', f"old 5a vendors, 5b, overlapping classes, race per load, {kn(g('fig4', 'a', 'cpapi_deny', 'any_sbx'))} row"),
             ('S9', 'What reaches vendors: detail', 'A old 6a by arm; B 6b signals; C Consent Mode states; D full Store C timeline')]
    for i, (n, t_, sub) in enumerate(tiles):
        X, Y = 10 + (i % 3) * 94, 28 + (i // 3) * 30
        p.ax.add_patch(Rectangle((X, Y), 88, 25, fc='white', ec=GREY_D, lw=0.7))
        p.t(X + 3, Y + 5, f'{n}  {t_}', fs=8, weight='bold', ha='left', abs_=True)
        for k, line in enumerate(textwrap.wrap(sub, 46)):
            p.t(X + 3, Y + 12 + k * 4.5, line, fs=6.8, ha='left', abs_=True, color=GREY_D)
    p.t(10, 125, 'Deleted: figures/panels/figS5_per_vendor.pdf (content stays as Table S5). '
                 'Supplementary files are named by print number (figS1.pdf ... figS9.pdf); sensitivity is figS5.pdf.', fs=7, ha='left', abs_=True, color=GREY_D)
    # graphical abstract 130 x 50 mm at true size
    gx, gy = 10, 140
    p.ax.add_patch(Rectangle((gx, gy), 130, 50, fc='white', ec=GREY_M, lw=0.6, ls=(0, (4, 3))))
    p.t(gx, gy - 4, 'Graphical abstract, 130 x 50 mm (true size), text >= 10 pt in the build', fs=7.5, weight='bold',
        ha='left', abs_=True)
    p.ax.add_patch(Rectangle((gx + 4, gy + 6), 24, 13, fc='white', ec=INK, lw=0.8))
    p.t(gx + 16, gy + 12.5, 'banner +\nblocker', fs=6.5, abs_=True)
    p.ax.add_patch(Rectangle((gx + 4, gy + 30), 24, 14, fc='white', ec=GREY_M, hatch='////', lw=0.8))
    p.t(gx + 16, gy + 37, 'Shopify\nsandbox', fs=6.5, abs_=True, bbox=dict(fc='white', ec='none', pad=0.5))
    p.ax.add_patch(Rectangle((gx + 42, gy + 30), 20, 14, fc='white', ec=GREY_D, lw=0.8))
    p.t(gx + 52, gy + 37, 'ad\nvendor', fs=6.5, abs_=True)
    p.ax.plot([gx + 16, gx + 16], [gy + 19, gy + 30], color=GREY_D, lw=0.8, ls=':')
    p.ax.add_patch(Circle((gx + 16, gy + 24.5), 2.6, fc=RED, ec='white'))
    p.t(gx + 20, gy + 24.5, 'blind spot', fs=6.3, ha='left', abs_=True)
    p.ax.add_patch(FancyArrowPatch((gx + 28, gy + 37), (gx + 42, gy + 37), arrowstyle='-|>', mutation_scale=8, color=RED))
    tiles_ga = [(pc(g('fig1b', 'banner_fires')), 'banner stores: pixels fire\nbefore any choice'),
                (f"{DN['fig4a_routes']['primary_no_yes']['sandbox']} of {DN['fig4a_routes']['primary_no_yes']['n']}",
                 "'blocked' vendors fired\nfrom sandbox (entries)"),
                (f"{g('fig5', 'd', 'deny', 'pixels_before')} of {g('fig5', 'd', 'deny', 'pixels')}",
                 "sandboxes beat\nthe 'no'")]
    for i, (big, lab) in enumerate(tiles_ga):
        y = gy + 8 + i * 14
        p.t(gx + 70, y, big, fs=10, weight='bold', ha='left', abs_=True)
        p.t(gx + 98, y, lab, fs=6.3, ha='left', abs_=True)
    p.t(150, 150, 'GA rules: vector PDF from TikZ, Arial, white, no generative imagery,\n'
                  '<= 26 words besides the numbers; readable at 5 x 13 cm on screen.\n'
                  'Tile B uses the Fig 4A unit (blocklist entries), so the abstract and Fig 4 share one number.', fs=7, ha='left', abs_=True,
        color=GREY_D)
    p.done()


def main():
    with plt.xkcd(scale=0.5, length=120, randomness=1.2):
        plt.rcParams['pdf.fonttype'] = 42
        plt.rcParams['path.effects'] = []  # keep text as text (the white stroke turns every glyph into a path)
        with PdfPages(DST) as pdf:
            cover(pdf)
            for f in (fig1, fig2, fig3, fig4, fig5, fig6):
                f(pdf)
            supp(pdf)
    print('wrote', DST, os.path.getsize(DST) // 1024, 'KB')


if __name__ == '__main__':
    main()
