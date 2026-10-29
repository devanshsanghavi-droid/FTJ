"""The single colour module for every Study 3 data figure (binding: ../FIGURE_PLAN.md).

Rules encoded here:
  * one fixed colour per vendor across ALL figures (validated categorical order);
  * arms are NEVER encoded by hue: marker shape + neutral grey only;
  * accent red means exactly one thing: consent failed / blind spot;
  * sandbox origin = neutral 45-degree hatch (never red); main thread = solid light grey;
  * heatmaps use a 4-step ORDINAL blue ramp (steps 250/350/550/700 of the validated blue ramp). Revised after review:
    it leaves out step 450 (= Google's vendor hex #2a78d6) and the near-surface steps 100-200 (light-end contrast
    below 2:1); every step is at least 9.8 OKLab units from Google's hex (figures/palette_validation.txt).
The TikZ schematics use the same hexes (schematics/schematic_style.tex).
"""
import os

import matplotlib as mpl

HERE = os.path.dirname(os.path.abspath(__file__))
STYLE = os.path.join(HERE, 'style.mplstyle')

# ---- vendors (FIGURE_PLAN.md table, fixed order) ----
VENDOR_ORDER = ['Google', 'TikTok', 'Meta', 'Pinterest', 'Snap', 'Microsoft', 'Reddit/other']
VENDOR = {
    'Google': '#2a78d6',
    'TikTok': '#eb6834',
    'Meta': '#1baf7a',
    'Pinterest': '#eda100',
    'Snap': '#e87ba4',
    'Microsoft': '#008300',
    'Reddit/other': '#4a3aa7',
}
SPARE = '#e34948'  # 8th slot, unused unless a figure needs it

# ---- neutrals and ink (dataviz palette chrome; identical to schematic_style.tex) ----
INK = '#0b0b0b'       # primary text; Default arm
GREY_D = '#52514e'    # secondary text; Decline + Repeat arms; outlines
GREY_M = '#8a8984'    # GPC arm; sandbox hatch; muted text
GREY_L = '#deddd9'    # main-thread origin (solid)
GREY_XL = '#f3f2ef'   # faint fills (n < 5 cells, containers)
GRID = '#e1e0d9'      # hairline grid
AXIS = '#c3c2b7'      # baseline / axis
SURFACE = '#ffffff'   # print surface

# ---- accent: ONLY "consent failed / blind spot" ----
ACCENT = '#d03b3b'

# ---- arms: shape + grey, never hue ----
ARM = {
    'Default': dict(marker='o', mfc=INK, mec=INK, color=INK, label='Default (no interaction)'),
    'Decline': dict(marker='s', mfc=SURFACE, mec=GREY_D, color=GREY_D, label='Decline (reject clicked)'),
    'GPC': dict(marker='^', mfc=GREY_M, mec=GREY_M, color=GREY_M, label='GPC'),
    'Repeat': dict(marker='D', mfc=SURFACE, mec=GREY_D, color=GREY_D, label='Repeat / validation'),
}

# ---- request origin (Fig 3c, 4c): hatch = sandbox, solid mid grey = relayed by Shopify (reserved for that),
# dark grey = Shopify OPEN pixel, light grey = ordinary page scripts and frames (visible to a blocker) ----
ORIGIN = {
    'sandbox': dict(facecolor=SURFACE, hatch='//////', edgecolor=GREY_M, label='Shopify sandbox (worker, iframe)'),
    'relay': dict(facecolor=GREY_M, hatch=None, edgecolor=GREY_M, label='relayed by Shopify'),
    'open_pixel': dict(facecolor=GREY_D, hatch=None, edgecolor=GREY_D, label='Shopify OPEN pixel'),
    'page': dict(facecolor=GREY_L, hatch=None, edgecolor=GREY_L, label='ordinary page scripts and frames'),
}
ORIGIN_ORDER = ['sandbox', 'relay', 'open_pixel', 'page']

# ---- ordinal blue ramp for heatmap bins 0-25, 25-50, 50-75, 75-100 % (validated --ordinal) ----
ORD_BLUE = ['#86b6ef', '#5598e7', '#1c5cab', '#0d366b']
ORD_EDGES = [0, 25, 50, 75, 100]


def ord_color(pct):
    for i in range(4):
        if pct < ORD_EDGES[i + 1] or i == 3:
            return ORD_BLUE[i]


# ---- within-arm contrast glyph (never an arm shape): a short vertical bar ----
WITHIN = dict(marker='|', ms=6.5, mew=1.3)


def ink_on(hex_fill):
    """White or ink text for a label set inside a coloured fill, chosen by luminance."""
    r, g, b = [int(hex_fill.lstrip('#')[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    L = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    return SURFACE if L < 0.28 else INK


def use_style():
    mpl.style.use(STYLE)
    mpl.rcParams['hatch.color'] = GREY_M


MM = 1 / 25.4  # inches per mm
FULL_W = 190 * MM
SINGLE_W = 90 * MM
