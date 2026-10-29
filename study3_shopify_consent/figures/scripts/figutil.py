"""Helpers shared by every figure script: style, panel letters, saving at final size."""
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FIGDIR = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, FIGDIR)
import colors as C  # noqa: E402  (the single colour module)

STUDY = os.path.normpath(os.path.join(FIGDIR, '..'))
AOUT = os.path.join(STUDY, 'analysis', 'outputs')
PANELS = os.path.join(FIGDIR, 'panels')
os.makedirs(PANELS, exist_ok=True)
MM = C.MM

C.use_style()

# Interval line weights, one meaning in every figure (review FIG-04): THICK = the primary 95% CI (Wilson for store
# shares, or the design-based / store-bootstrap interval where a caption says so); THIN = the cluster bootstrap by
# consent tool (sensitivity). Figures without a cluster interval use the thin 0.7-0.8 pt line of ci_dot and say so.
THICK = 1.2
THIN = 0.45


def stats():
    return json.load(open(os.path.join(AOUT, 'stats.json')))


def table(name):
    return pd.read_csv(os.path.join(AOUT, name))


def fig_mm(w, h):
    return plt.figure(figsize=(w * MM, h * MM))


def ax_mm(fig, x, y, w, h, W, H):
    """Axes placed by its plot-area rectangle in mm, measured from the figure's top-left corner."""
    return fig.add_axes([x / W, 1 - (y + h) / H, w / W, h / H])


def letter(fig, x, y, s, W, H):
    """Bold 10 pt panel letter with its top-left at (x, y) mm from the figure's top-left."""
    fig.text(x / W, 1 - y / H, s, fontsize=10, fontweight='bold', ha='left', va='top', color=C.INK)


def save(fig, name):
    pdf = os.path.join(PANELS, name + '.pdf')
    png = os.path.join(PANELS, name + '.png')
    fig.savefig(pdf)
    fig.savefig(png, dpi=600)
    plt.close(fig)
    print('wrote', pdf, png)
    return pdf, png


def xgrid(ax):
    ax.xaxis.grid(True, color=C.GRID, linewidth=0.4)
    ax.set_axisbelow(True)


def ygrid(ax):
    ax.yaxis.grid(True, color=C.GRID, linewidth=0.4)
    ax.set_axisbelow(True)


def pct_axis(ax, axis='x', lim=(0, 100), step=25):
    ticks = np.arange(lim[0], lim[1] + 1e-9, step)
    if axis == 'x':
        ax.set_xlim(*lim)
        ax.set_xticks(ticks)
    else:
        ax.set_ylim(*lim)
        ax.set_yticks(ticks)


def ci_dot(ax, y, p, lo, hi, arm='Default', color=None, size=4.2, zorder=3, lw=0.8):
    """One estimate with a thin horizontal 95% CI bar; arm sets marker shape + grey (never hue),
    or pass color (vendor hue) with the arm's marker shape."""
    st = C.ARM[arm]
    ec = color or st['color']
    ax.plot([lo, hi], [y, y], color=ec, lw=lw, solid_capstyle='butt', zorder=zorder - 1)
    mfc = st['mfc'] if color is None else (C.SURFACE if st['mfc'] == C.SURFACE else color)
    ax.plot([p], [y], marker=st['marker'], ms=size, mfc=mfc, mec=ec if color else st['mec'],
            mew=0.9, ls='none', zorder=zorder)


def arm_handle(arm, color=None, size=4.2):
    st = C.ARM[arm]
    from matplotlib.lines import Line2D
    ec = color or st['mec']
    mfc = st['mfc'] if color is None else (C.SURFACE if st['mfc'] == C.SURFACE else color)
    return Line2D([], [], marker=st['marker'], ms=size, mfc=mfc, mec=ec, mew=0.9, ls='none')


def fmt_n(n):
    return f'{int(n):,}'


def vendor_axis(ax, ys, names, chip=True, pad=9):
    """Vendor rows on the y axis: ink label text plus a small vendor-coloured square between label and axis
    (identity from the chip, never from coloured text)."""
    import matplotlib.transforms as mtransforms
    ax.set_yticks(ys)
    ax.set_yticklabels(names)
    ax.tick_params(axis='y', length=0, pad=pad if chip else 3)
    if not chip:
        return
    off = mtransforms.ScaledTranslation(-4.2 / 72, 0, ax.figure.dpi_scale_trans)
    tr = ax.get_yaxis_transform() + off
    for y, n in zip(ys, names):
        col = C.VENDOR.get(n)
        if col:
            ax.plot([0], [y], marker='s', ms=4.0, mfc=col, mec='none', transform=tr, clip_on=False, zorder=5)


def panel_title(fig, x, y, s, W, H, sub=None):
    fig.text((x + 5.5) / W, 1 - (y + 0.4) / H, s, fontsize=8, fontweight='bold', va='top', ha='left', color=C.INK)
    if sub:
        fig.text((x + 5.5) / W, 1 - (y + 4.3) / H, sub, fontsize=7, va='top', ha='left', color=C.GREY_D)


def hatch_bar(ax, y, left, width, height, **kw):
    from matplotlib.patches import Rectangle
    r = Rectangle((left, y - height / 2), width, height, facecolor=C.SURFACE, edgecolor=C.GREY_M, hatch='//////', lw=0, **kw)
    ax.add_patch(r)
    return r


def ci_dot2(ax, y, p, lo, hi, clo=None, chi=None, arm='Default', color=None, size=4.2, zorder=3):
    """Headline estimate: thick inner segment = Wilson 95% CI (primary, design-based); thin outer line = cluster
    bootstrap by consent tool (BCa, sensitivity). The marker follows the arm encoding."""
    st = C.ARM[arm]
    ec = color or st['color']
    if clo is not None and chi is not None:
        ax.plot([clo, chi], [y, y], color=ec, lw=THIN, solid_capstyle='butt', zorder=zorder - 2)
    ax.plot([lo, hi], [y, y], color=ec, lw=THICK, solid_capstyle='butt', zorder=zorder - 1)
    mfc = st['mfc'] if color is None else (C.SURFACE if st['mfc'] == C.SURFACE else color)
    ax.plot([p], [y], marker=st['marker'], ms=size, mfc=mfc, mec=ec if color else st['mec'], mew=0.9, ls='none', zorder=zorder)


def within_dot(ax, y, p, lo, hi, color=None, lw=0.8, zorder=3):
    """Within-arm contrast (e.g. 'only pixels that declare marketing'): a vertical bar glyph, never an arm shape."""
    col = color or C.INK
    ax.plot([lo, hi], [y, y], color=col, lw=lw, solid_capstyle='butt', zorder=zorder - 1)
    ax.plot([p], [y], ls='none', color=col, zorder=zorder, **C.WITHIN)


def open_dot(ax, y, p, lo, hi, color=None, lw=0.8, size=4.2, zorder=3):
    """Comparison group of the same measure (e.g. 'no banner' in Fig 3a): an OPEN circle, never the vertical bar, which
    keeps its single meaning 'pixel declaring marketing' across Figs 3 and 4 (editor review)."""
    col = color or C.INK
    ax.plot([lo, hi], [y, y], color=col, lw=lw, solid_capstyle='butt', zorder=zorder - 1)
    ax.plot([p], [y], marker='o', ms=size, mfc=C.SURFACE, mec=col, mew=0.9, ls='none', zorder=zorder)


def open_handle(color=None, size=4.2):
    from matplotlib.lines import Line2D
    return Line2D([], [], marker='o', ms=size, mfc=C.SURFACE, mec=color or C.INK, mew=0.9, ls='none')


def within_handle(color=None):
    from matplotlib.lines import Line2D
    return Line2D([], [], ls='none', color=color or C.INK, **C.WITHIN)


def ci_handles():
    """Legend handles explaining the two interval widths used for headline rows."""
    from matplotlib.lines import Line2D
    return [Line2D([], [], color=C.INK, lw=THICK), Line2D([], [], color=C.INK, lw=THIN)]


def pct(v, d=0):
    return f'{100 * v:.{d}f}'
