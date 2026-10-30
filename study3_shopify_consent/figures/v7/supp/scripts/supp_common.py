"""supp_common.py -- shared helpers for the v2 Supplementary Figures S1-S9 (binding: ../../FIGURE_PLAN_v2.md, section 3).

Everything visual comes from ../../style/figstyle.py (sizes, strokes, colours, arm markers, audit, number registry).
This module only adds what several supplementary panels share:
  * paths (panels are written to ../panels/, one numbers registry CSV per figure);
  * supp-level derived numbers (../derived_numbers.json, written by derive_supp_numbers.py) read through SD();
  * numbers read from committed analysis tables (analysis/outputs/*.csv) registered through CSVN();
  * a forest-row helper and the small-multiples grid used by S2 and S3.
Numbers are never typed: every rendered value passes through fs.N / fs.KN / SD / CSVN and lands in the registry.
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from matplotlib.transforms import offset_copy

HERE = os.path.dirname(os.path.abspath(__file__))           # figures/v7/supp/scripts
SUPP = os.path.dirname(HERE)                                # figures/v7/supp
V2 = os.path.dirname(SUPP)                                  # figures/v2
sys.path.insert(0, os.path.join(V2, 'style'))
import figstyle as fs  # noqa: E402

fs.use()
PANELS = os.path.join(SUPP, 'panels')
os.makedirs(PANELS, exist_ok=True)
AOUT = fs.AOUT
STUDY = fs.STUDY
SUPP_DERIVED = os.path.join(SUPP, 'derived_numbers.json')
S = json.load(open(fs.STATS_JSON))

# consent-tool display names (Shopify's own banner is "Shopify's banner" everywhere in the supplement)
CMP_NAME = {'pandectes': 'Pandectes', 'onetrust': 'OneTrust', 'shopify_native': 'Shopify’s banner', 'cookiebot': 'Cookiebot',
            'osano': 'Osano', 'iubenda': 'iubenda', 'usercentrics': 'Usercentrics', 'axeptio': 'Axeptio',
            'trustarc': 'TrustArc', 'ketch': 'Ketch', 'clarip': 'Clarip', 'cookiescript': 'CookieScript',
            'cookieyes': 'CookieYes', 'other': 'Other or none'}


def table(name):
    return pd.read_csv(os.path.join(AOUT, name))


# ---------------------------------------------------------------------------------------------------- number sources
_SD = None


def SD(key, f='int'):
    """Render a supp-level derived number (../derived_numbers.json; the record's 'value' level is implied) and register it."""
    global _SD
    if _SD is None:
        _SD = json.load(open(SUPP_DERIVED))
    name, _, rest = key.partition('/')
    v = fs._walk(_SD[name]['value'], rest) if rest else _SD[name]['value']
    s = fs.render(v, f)
    fs._REG.append(dict(text=s, shown=fs.typo(s), source='supp_derived', key=key, fmt=f, value=json.dumps(v)))
    return fs.typo(s)


def SDv(key):
    """Raw value of a supp-level derived number (for drawing; not rendered as text)."""
    global _SD
    if _SD is None:
        _SD = json.load(open(SUPP_DERIVED))
    name, _, rest = key.partition('/')
    return fs._walk(_SD[name]['value'], rest) if rest else _SD[name]['value']


def CSVN(value, source, f='int'):
    """Render a number read from a committed analysis table (source = 'file.csv:row description') and register it."""
    v = value.item() if hasattr(value, 'item') else value
    s = fs.render(v, f)
    fs._REG.append(dict(text=s, shown=fs.typo(s), source='csv', key=source, fmt=f, value=json.dumps(v)))
    return fs.typo(s)


def V(key):
    """Raw stats.json value (for drawing only)."""
    return fs.stat(key)


def finish(fig, name, title=False, letter_zone=True):
    """Save a panel (audited, exact size) into ../panels/."""
    return fs.save_panel(fig, os.path.join(PANELS, name + '.pdf'), title=title, letter_zone=letter_zone)


def write_registry(fig_name):
    p = fs.write_registry(os.path.join(PANELS, fig_name + '_numbers.csv'))
    fs.reset_registry()
    return p


# ---------------------------------------------------------------------------------------------------- drawing helpers
def row_axis(ax, ys, labels, pad=3, colors=None, weights=None):
    """Categorical y axis: labels only (no spine, no ticks); optional per-row label colour / weight."""
    ax.set_yticks(list(ys))
    ax.set_yticklabels(list(labels))
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis='y', length=0, pad=pad)
    for i, t in enumerate(ax.get_yticklabels()):
        if colors is not None and colors[i] is not None:
            t.set_color(colors[i])
        if weights is not None and weights[i] is not None:
            t.set_fontweight(weights[i])


def pct_x(ax, lo=0, hi=100, step=25, label=None, pad_lo=0.0, pad_hi=0.0):
    """Percent x axis 0-100 with the spine bounded to the data range; optional padding so end markers stay whole."""
    fs.pct_axis(ax, 'x', lo, hi, step, percent_sign=False)
    ax.set_xlim(lo - pad_lo, hi + pad_hi)
    ax.spines['bottom'].set_bounds(lo, hi)
    if label:
        ax.set_xlabel(label)


def small_multiples(fig, rows, rowlabels, metrics, get, top, left, colw, plotw, height, min_n=5, row_label_colors=None,
                    row_label_weights=None, row_marker_color=None, n_header=True, n_gap_mm=2.6):
    """Grid of dot plots: one row per group, one column per metric (each column one arm).
    get(row, metric) -> (rec, key) with rec {k, n, p, lo, hi} and key its stats.json path (for the registry).
    Columns: plot area `plotw` mm, then the n column; column pitch `colw` mm. Returns the axes."""
    axes = []
    n = len(rows)
    ys = np.arange(n)[::-1].astype(float)
    for j, (m, title, arm) in enumerate(metrics):
        x0 = left + j * colw
        ax = fs.axes_mm(fig, x0, top, plotw, height)
        ntr = offset_copy(ax.get_yaxis_transform(), fig=fig, x=n_gap_mm * fs.PT_PER_MM, y=0, units='points')
        for y, r in zip(ys, rows):
            rec, key = get(r, m)
            if rec is None:
                continue
            if rec['n'] < min_n:
                fs.note(ax, 50, y, 'n = ' + fs.N(key + '/n'), ha='center', color=fs.GREY_M)
                continue
            col = row_marker_color(r) if row_marker_color else None
            fs.point(ax, 100 * rec['p'], y, arm, ci=(100 * rec['lo'], 100 * rec['hi']), color=col)
            fs.note(ax, 1.0, y, fs.N(key + '/n'), ha='left', color=fs.GREY_D, size=fs.FS['label'], transform=ntr)  # value, 8 pt
        pct_x(ax, 0, 100, 50, pad_lo=4, pad_hi=4)
        ax.set_ylim(-0.6, n - 0.4)
        if j == 0:
            row_axis(ax, ys, rowlabels, pad=5, colors=row_label_colors, weights=row_label_weights)
        else:
            row_axis(ax, ys, [''] * n)
        fs.value_grid(ax, 'x')
        ax.text(0, 1.0, title, transform=ax.transAxes, ha='left', va='bottom', fontsize=fs.FS['cat'],
                linespacing=1.05)                                   # column head = category label, 9 pt (v2.1)
        if n_header and j == 0:
            ax.text(1.0, 1.0, 'n', transform=offset_copy(ax.transAxes, fig=fig, x=n_gap_mm * fs.PT_PER_MM, y=0, units='points'),
                    ha='left', va='bottom', fontsize=fs.FS['note'], color=fs.GREY_D)
        axes.append(ax)
    return axes


# ---------------------------------------------------------------------------------------------------- legend rule
LEGEND_TOP_MM = 5.0     # top of every supplementary legend: just under the composite's letter / title band (as S8A)


def top_right_legend(fig, handles, labels, x_mm=None, top_mm=LEGEND_TOP_MM, **kw):
    """The figure's one legend at the TOP RIGHT of the first panel that needs it (figstyle.legend's LEGEND RULE, cross-
    figure QA 2): right-aligned to the panel's right edge (or to x_mm), its top `top_mm` below the panel top.
    One row by default (ncol = len(handles)); 9 pt, no frame."""
    W, H = fs.size_mm(fig)
    x = W if x_mm is None else x_mm
    opts = dict(loc='upper right', bbox_to_anchor=(x / W, 1 - top_mm / H), ncol=len(handles), borderaxespad=0.0,
                borderpad=0.0, handletextpad=0.3, columnspacing=0.9)
    opts.update(kw)
    return fig.legend(handles, labels, **opts)
