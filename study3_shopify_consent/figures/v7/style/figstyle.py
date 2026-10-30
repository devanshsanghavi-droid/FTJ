"""figstyle.py -- the one shared style module for every matplotlib panel of the figure set.
v7 (2026-10-19): binding spec ../DESIGN_V7.md (sciplot clean theme + the bake-off grafts; worked example ../fig1). v7
panels draw inside v7_context() (open L axes, 0.6 pt SP_AXIS chrome, 1.0 pt data, 3.5 pt markers) and use the v7 type
scale (FS: 6 pt ticks and muted notes, 7 pt words, 8 pt bold lowercase letters) and the pre-mixed tints TINT. The v6
notes below describe style_context(), kept unchanged for figures not yet rebuilt to v7.

v6 RESTRAINT style (2026-10-17)
  * chrome: thin FULL box, 0.5 pt near-black (AXIS #222222), outward ticks on the bottom / left only; NO gridlines
    (row_grid() and value_grid() are no-ops, kept so older panel code still runs)
  * type: Arial; axis titles and labels 7 pt, ticks 6.5 pt, notes 6.5 pt, panel letters 8.5 pt bold lowercase (drawn
    by the composite; there are NO panel titles: panel_title() draws nothing, \\Panel ignores its title argument);
    hard floor 6 pt; no hero numbers (FS['hero'] is a 7 pt label size)
  * colour tokens (sampled from the exemplar papers, one meaning each, the same in every figure):
      LEAK    #c65358 brick     protagonist / 'consent lost'      (ACCENT and FAILED are aliases of LEAK)
      HONOUR  #5d769d slate     comparison / 'consent honoured'
      THIRD   #b788ca lavender  a third series, if needed
      EVENT   #e8a33a amber     the consent event (banner, Decline click, GPC)
      NEUTRAL #a0a0a0 grey      context (= GREY_M);  LIGHT #d9d9d9 light grey (= GREY_L)
      SAND    #3b4656 dark slate, the solid 'runs in a Shopify sandbox' fill (LEAK-free, achromatic-reading)
    vendor hexes are fixed (figures/colors.py) and used only where vendors are the categories; no semantic token shares
    a panel with vendor hues (each sits within about 10 OKLab dE of one: LEAK-TikTok, HONOUR-Google, THIRD-Snap,
    EVENT-Pinterest 2.0). White backgrounds only: no tinted lanes, no pastel or warm zones; a pale tint only as an
    error band (error_band()).
  * marks: filled circles / squares / diamonds about 4.5 pt (ARM Default 4.5), data lines 1.3 pt, error bars 0.75 pt
    without caps; double-code series by shape where a reader must tell them apart (SERIES / SERIES_MARKER).
Kept from v5: millimetre canvases at final print size, the number registry (N / KN / PCT / CI), the audit in
save_panel(), the 2 mm left indent, the ink-only colour cycle (colour is always explicit) and the Okabe-Ito ban.

Vendor hexes, arm shapes and origin categories are re-exported from ../../colors.py (the project's colour module,
not edited for v6); the v6 tokens and neutrals are defined below and override colors.py's warm v5 greys and red. The
LaTeX side (tikzstyle_v2.tex, composites) reads the same values from palette_v2.tex, which this module writes
(`python3 figstyle.py --write-tex`), so matplotlib panels, TikZ schematics and composites share one source.

Everything is at FINAL PRINT SIZE. A panel is drawn at exactly the mm size of its cell in the composite and is never
rescaled; the composite (LaTeX, see composite_template.tex) draws the panel letters, so panel scripts must keep the
top-left LETTER_ZONE_MM corner of the panel empty (save_panel() checks this).

Typical panel script
--------------------
    import sys; sys.path.insert(0, '<study>/figures/v7/style')
    import figstyle as fs
    with fs.style_context():                                    # scoped style (fs.use() is the global legacy form)
      fig = fs.panel(62, 66)                                     # panel = composite cell, in mm
    ax = fs.axes_mm(fig, left=15, top=7, width=44, height=50)   # plot area in mm from the panel's top-left
    r = fs.stat('fig1b/banner_fires')                           # numbers only ever come from stats.json / derived
    fs.point(ax, 100 * r['p'], 0, 'Default', ci=(100 * r['lo'], 100 * r['hi']))
    fs.direct_label(ax, ..., fs.N('fig1b/banner_fires/k') + ' of ' + fs.N('fig1b/banner_fires/n'))
    fs.save_panel(fig, 'fig1b.pdf')            # exact size, vector, audited: fonts, sizes, glyphs, letter zone, bounds
    fs.write_registry('fig1b_numbers.csv')     # every number rendered through N()/KN()/PCT(), for trace checks

Command line
------------
    python3 figstyle.py --write-tex     writes palette_v2.tex (colours, sizes, strokes, markers for LaTeX)
    python3 figstyle.py --selftest      checks the encodings against the plan and the formatters against numreg.render
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
from contextlib import contextmanager

import matplotlib

matplotlib.use('Agg')
import matplotlib as mpl  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as _fm  # noqa: E402
from matplotlib import patheffects as _pe  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch, Polygon, Rectangle  # noqa: E402
from matplotlib.text import Text  # noqa: E402
from matplotlib.transforms import Bbox, offset_copy  # noqa: E402

# ------------------------------------------------------------------------------------------------------------------
# paths
# ------------------------------------------------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))                  # figures/v7/style
V2 = os.path.normpath(os.path.join(HERE, '..'))                     # figures/v7 (this figure set)


def _find_study(d):
    """The study root (study3_shopify_consent): the first ancestor holding analysis/ and figures/ (searched, not a
    fixed '..' chain, so a copied figure set at any depth still resolves it)."""
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, 'analysis')) and os.path.isdir(os.path.join(d, 'figures')):
            return d
        d = os.path.dirname(d)
    raise RuntimeError('study root not found above ' + HERE)


STUDY = _find_study(HERE)                                          # study3_shopify_consent
FIGDIR = os.path.join(STUDY, 'figures')                             # figures (colors.py)
AOUT = os.path.join(STUDY, 'analysis', 'outputs')
STATS_JSON = os.path.join(AOUT, 'stats.json')
DERIVED_JSON = os.path.join(V2, 'derived_numbers.json')
STYLE_FILE = os.path.join(HERE, 'style_v2.mplstyle')
PALETTE_TEX = os.path.join(HERE, 'palette_v2.tex')
PDFPAGES2PNG = os.path.join(STUDY, 'paper', 'tools', 'pdfpages2png')

if FIGDIR not in sys.path:
    sys.path.insert(0, FIGDIR)
import colors as _C  # noqa: E402  (the project's single colour module)

# ------------------------------------------------------------------------------------------------------------------
# geometry (mm) and type (pt), all at final print size
# ------------------------------------------------------------------------------------------------------------------
MM = 1 / 25.4                 # inches per mm
PT_PER_MM = 72 / 25.4         # 2.8346 pt per mm
FIG_W_MM = 190.0              # every main and supplementary figure (Elsevier double column)
FIG_MAX_H_MM = 230.0
GUTTER_MM = 6.0               # horizontal and vertical gutter between panel cells; no outer margin
LETTER_ZONE_MM = (4.5, 4.5)   # (w, h) top-left corner of every panel reserved for the composite's panel letter
# v5 graft (judges: kdense's row labels sat flush with the page edge and the 'a'): in a panel whose cell starts at the
# figure's left edge, every row / category label and every mark starts at least INDENT_MM right of that edge, so the
# letter column stands alone. Rotated y-axis titles may sit closer (>= 0.8 mm).
INDENT_MM = 2.0
# v5 graft: labels moved off their mark by more than this get a leader line (never bare nudging).
LEADER_MIN_MM = 0.8
# v5 graft: headroom above the top tick of a value axis that carries in-plot labels at its top (event names such as
# 'banner visible'); the spine stops at the top tick. A fraction of the top tick's value range.
HEADROOM_FRAC = 0.08

# v7 type scale (../DESIGN_V7.md section 2; the sciplot clean-nature theme, Arial instead of Inter): three sizes only --
# 6 pt tick labels and muted secondary text, 7 pt words (axis titles, labels, row names, schematic text), 8 pt bold
# lowercase panel letters. Weight, not size, makes hierarchy (bold only for the panel letters). No panel titles and no
# hero numbers: 'title' and 'hero' are kept only so older helpers still run, at label size. Hard floor 6 pt
# (FS['min']; qa_check FAILs below it). Schematic text in TikZ uses the same macros (\fsLabel 7, \fsNote 6).
# (v6 used 6.5 pt ticks / notes and 8.5 pt letters.)
FS = dict(
    letter=8.0,     # panel letter a, b, c ... bold lowercase (drawn by the composite, never by a panel)
    title=7.0,      # NO panel titles (panel_title() draws nothing); kept for standalone helpers
    axis=7.0,       # axis titles
    tick=6.0,       # tick labels
    legend=7.0,     # the one small legend / marker key
    cat=7.0,        # category / row labels
    label=7.0,      # direct labels (at most two short ones per panel)
    value=7.0,      # alias of label
    note=6.0,       # muted secondary text (SP_MUTED only): qualifiers, the vendor-group list of a schematic box
    numeral=6.0,    # the outlined loss numerals 1-5 of a schematic (DESIGN_V7 section 7.4); never a data value
    hero=7.0,       # (no hero numbers: a stat tile is set at label size, bold)
    hero_sub=6.0,   # the line under a stat tile
    min=6.0,        # hard floor
)
CAP_EM = 1466 / 2048          # Arial / Arial Bold cap height (units per em 2048); the letter baseline sits CAP below top
LETTER_CAP_MM = FS['letter'] * CAP_EM / PT_PER_MM   # 2.02 mm

LW = dict(   # v6 RESTRAINT strokes (pt)
    axis=0.5,       # the full box (all four spines) and the ticks, AXIS near-black (rule 5)
    grid=0.4,       # (no gridlines in v6: row_grid() is a no-op; kept for the TikZ macro only)
    data=1.3,       # data lines: ECDF / CCDF / step / time series (rule 7: 1.2-1.5 pt)
    error=0.75,     # every error bar / CI; no caps
    connect=0.75,   # a line that only JOINS two estimates: never heavier than the CIs
    leader=0.35,    # leader line from a displaced label to its mark, GREY_M
    box=0.5,        # schematic rectangles (thin line art), outlines of light fills
    arrow=0.5,      # thin connectors (schematics, stealth_arrow)
    leakpath=0.75,  # the one accent path of a schematic (the leak path, LEAK)
    event=0.75,     # a consent-event rule (banner shown, Decline click, GPC), EVENT amber
    hatch=0.4,      # (legacy) hatch lines
    context=0.5,    # light context lines
    hairline=0.35,  # brackets, zero lines
    ring=0.8,       # white ring around markers where marks overlap
    ring_thin=0.4,  # white edge of DENSE markers
    tick_dense=0.8, # request ticks in a dense multi-load timeline
)
TICK_LEN_PT = 2.5           # outward major ticks (bottom and left only)
# Named small marks (sizes in pt, matplotlib `ms`); every mark in every panel is one of these or an ARM size.
MS = dict(
    dense=4.0,      # a Default-arm circle drawn DENSE (per-load strip plots): a little under the 4.5 pt marker
    wedge=4.0,      # the median wedge above a histogram
    dot=3.0,        # small ink dot marking a property of a tick
    chip=3.4,       # vendor chip beside a row label
)

# Sandbox hatch: 45 degrees, 0.5 pt, mid grey, 2.12 pt between lines measured perpendicular (tikzstyle_v2.tex uses the
# same distance). matplotlib (hatch.NorthEastHatch, density 6, 72 pt PDF tile) puts N = 6 x count('/') lines across a
# tile whose intercepts span 2 tiles, so lines are 144 / N pt apart along x: '////' was 6 pt along x = 4.24 pt
# perpendicular, twice the TikZ spacing (fig4/QA.md). '////////' gives N = 48: 3 pt along x = 2.12 pt perpendicular.
# Verified 2026-09-26 by rendering a matplotlib hatch next to the TikZ `sandbox` pattern at 1,200 dpi (qa note in
# FIGURE_PLAN_v2.md section 8).
HATCH = '////////'
HATCH_SPACING_PT = 144 / (HATCH.count('/') * 6) / math.sqrt(2)

# Stealth arrow head shared with TikZ (arrows.meta Stealth[length, width, inset]); all pt. v6: sized for 0.5 pt arrows.
STEALTH = dict(length=3.0, width=2.4, inset=0.9)

# Leak marker (legacy numbered disc; RESTRAINT rule 8 bans numbered discs in schematics): LEAK disc, white bold digit.
LEAK_DIAM_MM = 3.2

# ------------------------------------------------------------------------------------------------------------------
# colours (v6 RESTRAINT rule 6). Vendor hexes, arm shapes and origin categories are re-exported from figures/colors.py
# (unchanged); the semantic tokens and the neutrals are v6 values defined here (colors.py keeps its v5 warm greys and
# red for older figure sets, which this module no longer uses).
# ------------------------------------------------------------------------------------------------------------------
VENDOR_ORDER = list(_C.VENDOR_ORDER)            # fixed order: Google, TikTok, Meta, Pinterest, Snap, Microsoft, Reddit/other
VENDOR = dict(_C.VENDOR)                        # identity only; Pinterest, Meta and Snap are < 3:1 -> always direct-label
VENDOR_LOW_CONTRAST = ('Meta', 'Pinterest', 'Snap')

# ---- semantic tokens: one meaning each, the same in every figure. Never in a panel whose categories are vendors:
#      each sits within ~10 OKLab dE of a vendor hue (LEAK-TikTok 10.1, HONOUR-Google 9.6, THIRD-Snap 9.6,
#      EVENT-Pinterest 2.0), so qa_check / palette_gate FAIL a semantic token next to vendor hues.
LEAK = '#c65358'        # muted brick: the protagonist, 'consent lost' (4.4:1 on white)
HONOUR = '#5d769d'      # slate: the comparison, 'consent honoured' (4.6:1)
THIRD = '#b788ca'       # lavender: a third series, only if needed (2.8:1: a mark colour, never text)
EVENT = '#e8a33a'       # amber: the consent event -- banner shown, Decline click, GPC (2.2:1: a mark / rule, never text)
SEMANTIC = dict(LEAK=LEAK, HONOUR=HONOUR, THIRD=THIRD, EVENT=EVENT)
# series in a panel that compares two or three groups: colour AND shape (RESTRAINT rule 7: double-code by shape)
SERIES = (LEAK, HONOUR, THIRD)
SERIES_MARKER = ('o', 's', 'D')
ACCENT = LEAK           # alias kept so v5 panel code (fs.ACCENT = 'consent failed') maps to brick
FAILED = LEAK

# ---- neutrals (true greys; v6 drops colors.py's warm v5 greys)
INK = '#000000'         # all text and primary marks
AXIS = '#222222'        # near-black chrome: the 0.5 pt full box and its ticks
GREY_D = '#555555'      # secondary text (7.5:1); Decline and Repeat arm outlines
NEUTRAL = '#a0a0a0'     # RESTRAINT neutral grey: context marks and series, GPC arm, leaders (2.6:1: never text)
LIGHT = '#d9d9d9'       # light grey: connectors, rules, light fills (decorative, 1.4:1)
GREY_M = NEUTRAL        # alias (v5 name)
GREY_L = LIGHT          # alias (v5 name)
GREY_XL = '#f2f2f2'     # faint neutral fill (absent cells); white is preferred
GRID = LIGHT            # (no gridlines in v6; kept for older code)
CONTEXT = LIGHT         # decorative only: dumbbell connectors, table rules (never needed to read)
SURFACE = '#ffffff'     # white backgrounds only
# emphasis without hue: when one series is the story it is STORY ink and the others CONTEXT_SERIES grey; labels stay ink.
STORY = INK
CONTEXT_SERIES = NEUTRAL
# the one pale tint RESTRAINT allows: an error band behind a line, in the line's own colour at this opacity
BAND_ALPHA = 0.18
ORD_BLUE = list(_C.ORD_BLUE)    # (legacy ordinal blue ramp for heatmaps; it sits near Google's hue -- prefer GREY_RAMP)
# neutral 4-step ordinal grey ramp (light -> dark) for heatmaps: equal sRGB steps, one hue (none), monotone lightness.
GREY_RAMP = ['#c8c8c8', '#969696', '#646464', '#323232']

# ---- 'runs in a Shopify sandbox': ONE solid fill, a LEAK-free neutral dark slate (OKLab chroma 0.03, 9.6:1 on white;
#      white text on it 9.6:1). Not a zone tint: there are no tinted zones, lanes or warm fields anywhere in v6.
SAND = '#3b4656'        # sandbox fill (bars, swatches, the schematic sandbox frame)
SAND_D = SAND           # sandbox outline / label
SAND_T = SURFACE        # no zone tints
MAIN_D = GREY_D         # main-thread outline / label
MAIN_T = SURFACE        # no zone tints
EXT_T = SURFACE         # no zone tints

# ---- sciplot 'clean' skin (bake-off 2: the mmd-ahd/scientific-figure-skill "sciplot", theme clean; values copied from
#      its styles.THEMES['clean'] and clean-nature.mplstyle, re-implemented here, never executed). Used by Figure 1:
#      the theme's near-black text and chrome, its muted grey for secondary labels, its hairline guide grey, and
#      PRE-MIXED tints of the tokens for purposeful fills (the skill: "fills use pre-mixed tints, not alpha"). Each tint
#      is the token mixed with white in OKLab (sp.color.lighten(c, t, "#ffffff")); a tint keeps its token's meaning.
SP_FG = '#1f2328'       # text (15.8:1)
SP_AXIS = '#3d434b'     # spines, ticks, connectors, schematic outlines (10.0:1)
SP_MUTED = '#6b7280'    # secondary labels: container names, row qualifiers (4.8:1)
SP_GUIDE = '#e6e8eb'    # hairline row guides of an event strip (grid.color of the theme; decorative)
SP_CONTEXT = '#b9bec5'  # context marks (the request ticks of a raster; 1.9:1): a cool grey lighter than NEUTRAL
TINT = dict(            # token -> its fill tint (OKLab mix with white, fraction t of white). v7: one meaning each,
    EVENT='#fbeddb',    # t = 0.80: the cookie banner (the consent UI whose appearance is the amber 'banner visible')
    SAND='#e9ebed',     # t = 0.90: the pixel-sandbox region (schematic) and the sandbox lane of a trace
    PAGE='#f4f5f6',     # SAND at t = 0.95: the page (main-thread) region and the page lane -- one step lighter than SAND
    LEAK='#fbeeed',     # LEAK at t = 0.90: a ground behind data marking where consent was lost (c: before the banner)
)
# v7 sciplot clean theme for matplotlib panels (clean-nature.mplstyle values, never its code): open L-shaped axes,
# 0.6 pt chrome and ticks in SP_AXIS, text SP_FG, ticks 2.5 pt outward with a 2 pt pad, label pad 2.5 pt, frameless
# legend with 1.4 em handles, data lines 1.0 pt, markers 3.5 pt. Applied over style_v2.mplstyle by v7_context().
V7_LW = dict(axis=0.6, data=1.0, marker=3.5, mew=0.6)
V7_RC = {
    'axes.spines.top': False, 'axes.spines.right': False,
    'axes.linewidth': V7_LW['axis'], 'axes.edgecolor': SP_AXIS,
    'xtick.major.width': V7_LW['axis'], 'ytick.major.width': V7_LW['axis'], 'xtick.major.size': 2.5,
    'ytick.major.size': 2.5, 'xtick.major.pad': 2.0, 'ytick.major.pad': 2.0, 'axes.labelpad': 2.5,
    'xtick.color': SP_AXIS, 'ytick.color': SP_AXIS, 'xtick.labelcolor': SP_AXIS,
    'ytick.labelcolor': SP_AXIS, 'text.color': SP_FG, 'axes.labelcolor': SP_FG,
    'legend.frameon': False, 'legend.handlelength': 1.4, 'lines.linewidth': V7_LW['data'],
    'lines.markersize': V7_LW['marker'], 'lines.markeredgewidth': V7_LW['mew'],
}
SKIN = dict(SP_FG=SP_FG, SP_AXIS=SP_AXIS, SP_MUTED=SP_MUTED, SP_GUIDE=SP_GUIDE, SP_CONTEXT=SP_CONTEXT,
            **{'TINT_' + k: v for k, v in TINT.items()})

# Arms: shape + grey, never hue (the encoding comes from colors.ARM; colours remapped to the v6 neutrals below).
# Sizes are matplotlib `ms` in pt: circle diameter, square side, triangle width = height, diamond side (its diagonal is
# ms * sqrt(2)). v6: v5's tuned ratios scaled by 4.5 / 4 so the Default circle is the RESTRAINT ~4.5 pt marker.
ARM_ORDER = ['Default', 'Decline', 'GPC', 'Repeat']
_ARM_SIZE = {   # edge 0.7 pt on the circle, shared with its open counterpart (Comparison)
    'Default': dict(ms=4.5, mew=0.7),
    'Decline': dict(ms=4.7, mew=0.85),
    'GPC': dict(ms=5.8, mew=0.7),
    'Repeat': dict(ms=4.2, mew=0.85),
}
ARM = {k: dict(marker=_C.ARM[k]['marker'], mfc=_C.ARM[k]['mfc'], mec=_C.ARM[k]['mec'], color=_C.ARM[k]['color'],
               label=k, long_label=_C.ARM[k]['label'], **_ARM_SIZE[k]) for k in ARM_ORDER}
_V6_NEUTRAL = {_C.INK.lower(): INK, _C.GREY_D.lower(): GREY_D, _C.GREY_M.lower(): GREY_M, _C.SURFACE.lower(): SURFACE}
_ARM_V6 = {k: {f: _V6_NEUTRAL.get(str(ARM[k][f]).lower(), ARM[k][f]) for f in ('mfc', 'mec', 'color')}
           for k in ARM_ORDER}                  # the colors.py arm encodings drawn in the v6 neutrals
# Open circle: the comparison group of the same measure within the Default arm. Never an arm. The open circle has
# exactly the filled Default circle's ms AND mew (matched outer diameters); _check_encodings() asserts it.
COMPARISON = dict(marker='o', mfc=SURFACE, mec=INK, color=INK, ms=_ARM_SIZE['Default']['ms'],
                  mew=_ARM_SIZE['Default']['mew'], label='comparison group')

# Request origin fills: an ordinal grey ramp, sandbox darkest (SAND), page scripts lightest. No hatching anywhere.
ORIGIN_ORDER = list(_C.ORIGIN_ORDER)
ORIGIN = {k: dict(v) for k, v in _C.ORIGIN.items()}
ORIGIN['sandbox'].update(facecolor=SAND, hatch=None, edgecolor=SAND, label='Shopify sandbox (worker, iframe)')
ORIGIN['open_pixel'].update(facecolor='#6e6e6e', edgecolor='#6e6e6e')
ORIGIN['relay'].update(facecolor=NEUTRAL, edgecolor=NEUTRAL)
ORIGIN['page'].update(facecolor=LIGHT, edgecolor=LIGHT)

ink_on = _C.ink_on      # v1 helper (luminance threshold); prefer text_on() below


def _lum(hex_color):
    r, g, b = [int(hex_color.lstrip('#')[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(c1, c2):
    """WCAG contrast ratio of two hex colours."""
    a, b = sorted([_lum(c1), _lum(c2)], reverse=True)
    return (a + 0.05) / (b + 0.05)


def text_on(fill):
    """INK or white for a label inside a filled mark, whichever contrasts more (red -> white, mid grey -> ink)."""
    return SURFACE if contrast(fill, SURFACE) > contrast(fill, INK) else INK


def _check_encodings():
    """The plan fixes these; fail loudly if colors.py or the v6 tokens ever drift."""
    exp = {'Default': ('o', _C.INK, _C.INK), 'Decline': ('s', _C.SURFACE, _C.GREY_D), 'GPC': ('^', _C.GREY_M, _C.GREY_M),
           'Repeat': ('D', _C.SURFACE, _C.GREY_D)}
    for k, (m, fc, ec) in exp.items():
        a = _C.ARM[k]                           # the project encoding (colors.py) ...
        assert (a['marker'], a['mfc'].lower(), a['mec'].lower()) == (m, fc.lower(), ec.lower()), (k, a)
        ARM[k].update(_ARM_V6[k])               # ... drawn in the v6 neutrals
    assert VENDOR_ORDER == ['Google', 'TikTok', 'Meta', 'Pinterest', 'Snap', 'Microsoft', 'Reddit/other'], VENDOR_ORDER
    assert VENDOR == {'Google': '#2a78d6', 'TikTok': '#eb6834', 'Meta': '#1baf7a', 'Pinterest': '#eda100',
                      'Snap': '#e87ba4', 'Microsoft': '#008300', 'Reddit/other': '#4a3aa7'}, 'vendor hexes are fixed'
    assert ACCENT == FAILED == LEAK, 'ACCENT is an alias of LEAK'
    assert (LEAK, HONOUR, THIRD, EVENT, NEUTRAL, LIGHT) == ('#c65358', '#5d769d', '#b788ca', '#e8a33a', '#a0a0a0',
                                                            '#d9d9d9'), 'RESTRAINT rule 6 tokens'
    assert GREY_M == NEUTRAL and GREY_L == LIGHT
    assert ARM['GPC']['mfc'] == NEUTRAL and ARM['Decline']['mec'] == GREY_D and ARM['Default']['mfc'] == INK
    assert all(4.0 <= ARM[k]['ms'] * (math.sqrt(2) if ARM[k]['marker'] == 'D' else 1) <= 6.0 for k in ARM), \
        'arm markers must be about 4.5 pt (4-6 pt across)'
    assert (COMPARISON['ms'], COMPARISON['mew']) == (ARM['Default']['ms'], ARM['Default']['mew']), \
        'open and filled circles must share ms and mew (matched outer diameters)'
    assert INK not in {c.lower() for c in VENDOR.values()} and all(
        c.lower() not in BANNED_HUES for c in list(VENDOR.values()) + list(SEMANTIC.values()) + [SAND] + ORD_BLUE), \
        'palette drift'
    # the sandbox fill is LEAK-free and reads as a neutral: low chroma, far darker than every semantic token
    r, g, b = (int(SAND[i:i + 2], 16) for i in (1, 3, 5))
    assert max(r, g, b) - min(r, g, b) <= 32 and _lum(SAND) < 0.5 * min(_lum(c) for c in SEMANTIC.values()), SAND


# The K-Dense skill's default categorical palette (Okabe-Ito) is NOT used anywhere: its blue, vermillion, green and
# purple sit on the paper's Google, TikTok, Meta and Snap hues. qa_check.py / palette_gate.py FAIL these hexes.
BANNED_HUES = {'#0072b2', '#d55e00', '#009e73', '#cc79a7', '#e69f00', '#56b4e9', '#f0e442'}

_check_encodings()


# ------------------------------------------------------------------------------------------------------------------
# style activation
# ------------------------------------------------------------------------------------------------------------------
def _rc_extras():
    mpl.rcParams['hatch.color'] = GREY_M
    mpl.rcParams['hatch.linewidth'] = LW['hatch']
    # no silent hue cycling: colour is always explicit (vendor hue, accent, ordinal ramp) or it is ink
    mpl.rcParams['axes.prop_cycle'] = mpl.cycler(color=[INK])


def use():
    """Apply style_v2.mplstyle plus the values an mplstyle cannot carry (GLOBAL; prefer style_context())."""
    mpl.style.use(STYLE_FILE)
    _rc_extras()


@contextmanager
def style_context():
    """Scoped style: style_v2.mplstyle (the v6 RESTRAINT values: full 0.5 pt box, 7 / 6.5 pt Arial, no grid) plus the
    few values an mplstyle cannot carry, all restored on exit. Every panel script draws inside
    `with fs.style_context():`."""
    with mpl.style.context(STYLE_FILE):
        _rc_extras()
        yield


@contextmanager
def v7_context():
    """The v7 panel style (../DESIGN_V7.md): style_context() plus the sciplot clean theme values V7_RC, restored on
    exit. Every v7 panel script draws inside `with fs.v7_context():` (worked example: ../fig1/scripts/make_panels.py)."""
    with style_context(), mpl.rc_context(V7_RC):
        yield


# ------------------------------------------------------------------------------------------------------------------
# canvas and axes in millimetres
# ------------------------------------------------------------------------------------------------------------------
def panel(w_mm, h_mm):
    """A figure whose canvas is exactly one composite cell (w_mm x h_mm). Save with save_panel()."""
    fig = plt.figure(figsize=(w_mm * MM, h_mm * MM))
    fig._fs_size_mm = (float(w_mm), float(h_mm))
    return fig


def size_mm(fig):
    return getattr(fig, '_fs_size_mm', tuple(v * 25.4 for v in fig.get_size_inches()))


def axes_mm(fig, left, top, width, height, **kw):
    """Axes whose PLOT AREA (spines) is placed at (left, top) mm from the panel's top-left, width x height mm.
    Stacked panels that must share an x-origin simply use the same `left`."""
    W, H = size_mm(fig)
    return fig.add_axes([left / W, 1 - (top + height) / H, width / W, height / H], **kw)


def axes_margins(fig, left, top, right, bottom, **kw):
    """Axes from margins (mm) between the plot area and the panel edges."""
    W, H = size_mm(fig)
    return axes_mm(fig, left, top, W - left - right, H - top - bottom, **kw)


def fig_xy(fig, x_mm, y_mm):
    """Figure-fraction coordinates of a point given in mm from the panel's top-left."""
    W, H = size_mm(fig)
    return x_mm / W, 1 - y_mm / H


def text_mm(fig, x_mm, y_mm, s, size=None, weight='normal', color=None, ha='left', va='baseline', **kw):
    """Figure-level text placed in mm from the panel's top-left (va='baseline' puts the baseline at y_mm)."""
    x, y = fig_xy(fig, x_mm, y_mm)
    return fig.text(x, y, s, fontsize=size or FS['label'], fontweight=weight, color=color or INK, ha=ha, va=va, **kw)


def panel_title(fig, s):
    """v6 RESTRAINT rule 2: NO panel titles -- panels carry only the composite's bold lowercase letter. Kept so older
    panel code still runs: it draws nothing and returns None (the caption names what a panel shows)."""
    return None


def stat_tile(fig, x_mm, y_mm, big, sub, align='left'):
    """(Legacy; RESTRAINT rule 1 bans hero numbers -- put the number in the caption.) `big` is set at FS['hero'], which
    v6 makes a 7 pt bold label, with a 6.5 pt `sub` line below. (x_mm, y_mm) = top-left of the tile."""
    ha = align
    b = text_mm(fig, x_mm, y_mm + FS['hero'] * CAP_EM / PT_PER_MM, big, size=FS['hero'], weight='bold', ha=ha)
    s = text_mm(fig, x_mm, y_mm + FS['hero'] * CAP_EM / PT_PER_MM + 4.0, sub, size=FS['hero_sub'], ha=ha)
    return b, s


# ------------------------------------------------------------------------------------------------------------------
# chrome helpers
# ------------------------------------------------------------------------------------------------------------------
def value_grid(ax, axis='x'):
    """v6 RESTRAINT rule 5: no gridlines. A no-op, kept so older panel code still runs."""
    return None


def row_grid(ax, axis='x', at=None):
    """v6 RESTRAINT rule 5: no gridlines. A no-op (v5 drew recessive hairlines at the interior ticks of multi-row
    position plots); kept so older panel code still runs. Returns an empty list (no line was drawn)."""
    return []


def headroom(ax, top, axis='y', frac=HEADROOM_FRAC):
    """Extend the value axis `frac` of its range beyond the top tick `top`, so a short direct label at the top of the
    plot sits above the data. v6: the full box stays closed (the spine is no longer stopped at `top`). Call after the
    ticks are set."""
    lo = (ax.get_ylim() if axis == 'y' else ax.get_xlim())[0]
    new_hi = top + frac * (top - lo)
    if axis == 'y':
        ax.set_ylim(lo, new_hi)
    else:
        ax.set_xlim(lo, new_hi)
    return new_hi


def leader(ax, xy_mark, xy_label, transform=None, color=None, zorder=1.5):
    """v5 graft: a straight GREY_M hairline (LW['leader']) from just beside a mark to a label that had to be moved more
    than LEADER_MIN_MM away from it. Both points in the same coordinates (data by default). Never nudge a label off
    its mark without one."""
    tr = transform or ax.transData
    return ax.plot([xy_mark[0], xy_label[0]], [xy_mark[1], xy_label[1]], color=color or GREY_M, lw=LW['leader'],
                   solid_capstyle='butt', transform=tr, zorder=zorder, clip_on=False)[0]


def key_marker(fig, x_mm, y_mm, arm='Default', color=None):
    """v5 graft (marker key): one arm / 'Comparison' marker centred at (x_mm, y_mm) from the panel's top-left, drawn
    in figure coordinates -- put it 1.2 mm left of the key text (7 pt ink, never the series colour). A key in the
    header row replaces any reading of the encoding from label positions."""
    st = marker_style(arm, color)
    x, y = fig_xy(fig, x_mm, y_mm)
    return fig.add_artist(Line2D([x], [y], ls='none', marker=st['marker'], ms=st['ms'], mfc=st['mfc'], mec=st['mec'],
                                 mew=st['mew'], transform=fig.transFigure, zorder=5))


def category_axis(ax, axis='y'):
    """A categorical axis: labels without tick marks. v6: the spine stays, so the thin full box remains closed."""
    if axis == 'y':
        ax.tick_params(axis='y', length=0, pad=3)
    else:
        ax.tick_params(axis='x', length=0, pad=3)


def pct_axis(ax, axis='x', lo=0, hi=100, step=25, decimals=0, percent_sign=False):
    """Percent axis in percentage units (plot 100 * p). One convention in every figure (cross-figure QA): bare numeric
    ticks '0', '25' ... with the unit in the axis title ('... (%)'). percent_sign=True is kept only for old scripts."""
    import numpy as _np
    from matplotlib.ticker import FuncFormatter
    ticks = _np.arange(lo, hi + 1e-9, step)
    fmt = FuncFormatter(lambda v, _: fmt_dec(v, decimals) + ('%' if percent_sign else ''))
    if axis == 'x':
        ax.set_xlim(lo, hi)
        ax.set_xticks(ticks)
        ax.xaxis.set_major_formatter(fmt)
    else:
        ax.set_ylim(lo, hi)
        ax.set_yticks(ticks)
        ax.yaxis.set_major_formatter(fmt)


def vendor_labels(ax, ys, names, chip_pt=MS['chip'], gap_pt=3.0):
    """Vendor rows on the y axis: ink label text plus a vendor-coloured square chip between label and plot
    (identity from the chip, never from coloured text). Non-vendor rows (e.g. 'Any vendor') get no chip.
    Makes the y axis categorical itself (no tick marks; v6 keeps the spine, so the box stays closed): do not call
    category_axis() afterwards."""
    from matplotlib.transforms import ScaledTranslation
    ax.set_yticks(list(ys))
    ax.set_yticklabels(list(names))
    ax.tick_params(axis='y', length=0, pad=chip_pt + 2 * gap_pt)
    off = ScaledTranslation(-(gap_pt + chip_pt / 2) / 72, 0, ax.figure.dpi_scale_trans)
    tr = ax.get_yaxis_transform() + off
    for y, n in zip(ys, names):
        col = VENDOR.get(n)
        if col:
            ax.plot([0], [y], marker='s', ms=chip_pt, mfc=col, mec='none', ls='none', transform=tr, clip_on=False,
                    zorder=5)


# ------------------------------------------------------------------------------------------------------------------
# marks
# ------------------------------------------------------------------------------------------------------------------
def marker_style(arm='Default', color=None, dense=False):
    """Marker kwargs for an arm ('Default', 'Decline', 'GPC', 'Repeat') or 'Comparison' (open circle).
    color: a vendor hue replaces the grey; the shape stays the arm's, open markers keep their white fill.
    dense=True: the DENSE variant for strip plots with many marks per row -- every arm scaled by
    MS['dense'] / ARM['Default']['ms'] (so the shapes keep their relative weights), filled marks get a thin white edge
    (LW['ring_thin']) that separates overlapping marks."""
    st = dict(COMPARISON if arm == 'Comparison' else ARM[arm])
    if color is not None:
        st['mec'] = color
        st['mfc'] = SURFACE if st['mfc'].lower() == SURFACE.lower() else color
        st['color'] = color
    if dense:
        st['ms'] = st['ms'] * MS['dense'] / ARM['Default']['ms']
        if st['mfc'].lower() != SURFACE.lower():
            st['mec'], st['mew'] = SURFACE, LW['ring_thin']
    return st


def dense_marker_kw(arm='Default', color=None):
    """ax.plot kwargs (marker, ms, mfc, mec, mew) of the dense variant of an arm marker, in `color` if given."""
    st = marker_style(arm, color, dense=True)
    return dict(ls='none', marker=st['marker'], ms=st['ms'], mfc=st['mfc'], mec=st['mec'], mew=st['mew'])


def ring(width=None):
    """Path effect: a white ring (default 1 pt) around a marker where marks overlap."""
    return [_pe.withStroke(linewidth=width if width is not None else 2 * LW['ring'], foreground=SURFACE)]


def point(ax, x, y, arm='Default', ci=None, orient='h', color=None, with_ring=False, zorder=3, label=None):
    """One estimate: arm marker plus its 95% CI (LW['error'] 0.75 pt, no caps, same colour as the marker).
    orient='h': the CI runs along x (dot plots, dumbbells); 'v': along y. ci = (lo, hi) in data units."""
    st = marker_style(arm, color)
    if ci is not None:
        lo, hi = ci
        xs, ys = ([lo, hi], [y, y]) if orient == 'h' else ([x, x], [lo, hi])
        ax.plot(xs, ys, color=st['color'], lw=LW['error'], solid_capstyle='butt', zorder=zorder - 1)
    pe = [_pe.withStroke(linewidth=st['mew'] + 2 * LW['ring'], foreground=SURFACE)] if with_ring else None
    # clip_on=False: a mark at 0 % (or at the axis end) is drawn whole, never cut in half by the spine
    (ln,) = ax.plot([x], [y], ls='none', marker=st['marker'], ms=st['ms'], mfc=st['mfc'], mec=st['mec'],
                    mew=st['mew'], zorder=zorder, path_effects=pe, label=label, clip_on=False)
    return ln


def handle(arm='Default', color=None):
    """Legend handle for an arm marker or 'Comparison'."""
    st = marker_style(arm, color)
    return Line2D([], [], ls='none', marker=st['marker'], ms=st['ms'], mfc=st['mfc'], mec=st['mec'], mew=st['mew'])


def line_handle(color=INK, lw=None):
    return Line2D([], [], color=color, lw=lw if lw is not None else LW['data'])


def patch_handle(color, outline=None, hatch=False):
    if hatch:                                   # v3: the sandbox fill is solid SAND
        return Patch(facecolor=SAND, edgecolor=SAND, linewidth=0)
    return Patch(facecolor=color, edgecolor=outline or color, linewidth=LW['box'] if outline else 0)


def legend(ax, handles, labels, loc='upper right', **kw):
    """One small legend per figure at most, 7 pt, no frame. LEGEND RULE (cross-figure QA 2): the legend sits at the TOP RIGHT
    of the first panel that needs it (right-aligned to that panel's right edge, above or level with its first row),
    in main and supplementary figures alike; never at the bottom of a panel or figure."""
    return ax.legend(handles, labels, loc=loc, **kw)


def hatch_kw():
    """kwargs for a sandbox fill (bars, rectangles): solid SAND dark slate, no hatch, no outline."""
    return dict(facecolor=SAND, edgecolor=SAND, linewidth=0)


def light_kw():
    """kwargs for the light-grey fill that must carry an outline (e.g. next to brick): LIGHT with a 0.5 pt GREY_D edge."""
    return dict(facecolor=GREY_L, edgecolor=GREY_D, linewidth=LW['box'])


def sandbox_rect(ax, x, y, w, h, outline=True, zorder=2, transform=None):
    """A solid SAND 'runs in a Shopify sandbox' rectangle, optionally with a 0.5 pt SAND_D outline."""
    tr = transform or ax.transData
    r = Rectangle((x, y), w, h, transform=tr, zorder=zorder, **hatch_kw())
    ax.add_patch(r)
    if outline:
        ax.add_patch(Rectangle((x, y), w, h, transform=tr, zorder=zorder, facecolor='none', edgecolor=SAND_D,
                               linewidth=LW['box']))
    return r


def direct_label(ax, x, y, s, size=None, color=INK, ha='left', va='center', **kw):
    """Direct label (7 pt ink). RESTRAINT rule 3: at most two short direct labels per panel; numbers belong in the
    caption. Text never wears the series colour. For the name of a row or category use cat_label() (7 pt)."""
    return ax.text(x, y, s, fontsize=size or FS['label'], color=color, ha=ha, va=va, **kw)


def cat_label(ax, x, y, s, size=None, color=INK, ha='left', va='center', **kw):
    """Row / category label drawn as text (7 pt ink): a vendor, an arm, a group header."""
    return ax.text(x, y, s, fontsize=size or FS['cat'], color=color, ha=ha, va=va, **kw)


def bar_ci(ax, pos, p, lo, hi, orient='h', zorder=3, base=0.0):
    """The 95% CI of a BAR (bar from `base` to p, all in data units), one rule in every figure: 0.8 pt, no caps; the
    part of the interval that lies over the bar is white, the part beyond the bar end is ink, so the whole interval
    stays visible on any fill (red, ink, vendor hues, light grey). orient='h': bar along x at y = pos; 'v': along y."""
    def seg(a, b, col):
        if b <= a:
            return
        xs, ys = ([a, b], [pos, pos]) if orient == 'h' else ([pos, pos], [a, b])
        ax.plot(xs, ys, color=col, lw=LW['error'], solid_capstyle='butt', zorder=zorder, clip_on=False)
    seg(max(lo, base), min(hi, p), SURFACE)       # over the bar
    seg(max(lo, p), hi, INK)                      # beyond the bar end
    seg(lo, min(hi, base), INK)                   # below the base (only for intervals crossing 0)


BAR_CI_NOTE = 'an interval is drawn white where it lies over its bar'   # the one caption sentence for bar_ci()


def series_style(i, filled=True):
    """Marker kwargs for the i-th compared series (0 protagonist LEAK, 1 comparison HONOUR, 2 THIRD): colour AND shape
    (circle, square, diamond; RESTRAINT rule 7), RESTRAINT marker size. filled=False gives the open variant (white
    fill, same ms and mew)."""
    c, m = SERIES[i], SERIES_MARKER[i]
    ms = ARM['Default']['ms'] * (0.95 if m == 's' else (0.85 if m == 'D' else 1.0))   # similar visual weight
    return dict(ls='none', marker=m, ms=ms, mfc=c if filled else SURFACE, mec=c, mew=ARM['Default']['mew'], color=c)


def error_band(ax, x, lo, hi, color=INK, alpha=BAND_ALPHA, zorder=1, **kw):
    """The one pale tint RESTRAINT allows (rule 6): an error band behind a line, in the line's colour at BAND_ALPHA,
    no outline."""
    return ax.fill_between(x, lo, hi, facecolor=color, alpha=alpha, linewidth=0, edgecolor='none', zorder=zorder, **kw)


def event_line(ax, v, axis='x', color=EVENT, zorder=1.5, **kw):
    """A consent-event rule (banner shown, Decline click, GPC) across the plot at v: EVENT amber, LW['event']."""
    f = ax.axvline if axis == 'x' else ax.axhline
    return f(v, color=color, lw=LW['event'], solid_capstyle='butt', zorder=zorder, **kw)


# ------------------------------------------------------------------------------------------------------------------
# LABEL RULE (cross-figure QA 2, 2026-09-26): one format for every number printed inside a main or supplementary figure
#   1. A proportion labelled at its mark (bar end, marker, reference line, stacked segment, forest-plot count column):
#      'p% · k of n' when n >= SHARE_MIN_N (10), e.g. '46% · 106 of 233'; 'k of n' alone when n < 10 ('6 of 7'),
#      because a percentage of 7 overstates precision. Use PKN() (stats / derived keys) or share_label() (panels that
#      render their numbers through their own registry).
#   2. Every percentage printed inside a figure is a WHOLE number ('32%', SHARE_PCT = 'pct0'); decimals live in the
#      captions. Axis ticks follow their axis (e.g. the kappa axis).
#   3. A difference in percentage points always has ONE decimal and its sign: '+45.6 pp', '+13.6 pp', '+5.2 pp'
#      (PP()); its CI uses the same decimals ('−8.4 to 35.6', fmt_ci / CI()).
#   4. Keys, badges, stat tiles and row headers that state a count read 'k of n' + a unit noun, no percentage
#      ('535 of 545 sandboxes'): they are sentences, not labels of a mark.
# ------------------------------------------------------------------------------------------------------------------
SHARE_MIN_N = 10
SHARE_PCT = 'pct0'
PRECHOICE_AXIS_TITLE = 'Sandboxed ad request before any choice (% of stores)'   # Figs 1B, 3A, 3B, 4B: one title


def wrap(s, before):
    """Break `s` onto a new line before the first occurrence of `before` (e.g. wrap(PRECHOICE_AXIS_TITLE, 'any'))."""
    i = s.index(before)
    return s[:i].rstrip() + '\n' + s[i:]


def share_label(pct_txt, kn_txt, n, sep=' · '):
    """Rule 1 for numbers that are already rendered (and registered) by the caller: 'p% · k of n', or 'k of n' when
    n < SHARE_MIN_N. pct_txt is the whole-number percentage WITHOUT the sign ('46'), kn_txt is 'k of n'."""
    return kn_txt if n < SHARE_MIN_N else f'{pct_txt}%{sep}{kn_txt}'


def PKN(key, f=SHARE_PCT, source='stats', sep=' · '):
    """The ONE direct-label pattern for a proportion (label rule 1): 'p% · k of n', e.g. '50% · 205 of 410', or
    'k of n' when n < 10. Set it with direct_label() (8 pt regular) at the bar or marker end; bold only in a stat tile."""
    n = stat(key + '/n') if source == 'stats' else derived(key + '/n')
    if n < SHARE_MIN_N:
        return KN(key, source)
    return PCT(key, f, source) + sep + KN(key, source)


def PP(key, f='pct1', source='stats', signed=True):
    """A difference in percentage points (label rule 3): one decimal and its sign, '+45.6 pp'. f='pct1' for a value
    stored as a fraction (0.456), f='f1' for one stored in percentage points (45.6)."""
    v = stat(key) if source == 'stats' else derived(key)
    s = N(key, f, source)
    return ('+' if (signed and v > 0) else '') + s + ' pp'


def signed_ticks(ax, ticks, axis='x', decimals=0):
    """Tick labels with an explicit sign for positive values ('−3', '0', '+1'): offsets from an event (time 0)."""
    labs = [('+' if t > 0 else '') + fmt_dec(t, decimals) for t in ticks]
    if axis == 'x':
        ax.set_xticks(ticks)
        ax.set_xticklabels(labs)
    else:
        ax.set_yticks(ticks)
        ax.set_yticklabels(labs)


RACE_AXIS_TITLE = 'Sandbox start minus the CMP’s consent write (s)'   # Fig 5C and Fig S8D: one title, one tick format


def note(ax, x, y, s, size=None, color=GREY_D, ha='left', va='center', **kw):
    """Secondary text (6.5 pt GREY_D)."""
    return ax.text(x, y, s, fontsize=size or FS['note'], color=color, ha=ha, va=va, **kw)


def stealth_arrow(ax, xy0, xy1, color=INK, lw=None, coords='data', zorder=4):
    """A thin (LW['arrow'] 0.5 pt) connector with the shared Stealth head (same geometry as TikZ `arr`). Call after the axes limits and
    the figure size are final: the head is laid out in points once, then stored in data coordinates."""
    import numpy as _np
    lw = LW['arrow'] if lw is None else lw
    tr = ax.transData if coords == 'data' else ax.transAxes
    p0, p1 = _np.asarray(tr.transform(xy0), float), _np.asarray(tr.transform(xy1), float)
    d = p1 - p0
    u = d / _np.hypot(*d)
    n = _np.array([-u[1], u[0]])
    k = ax.figure.dpi / 72.0
    L, Wd, I = STEALTH['length'] * k, STEALTH['width'] * k, STEALTH['inset'] * k
    head = [p1, p1 - L * u + Wd / 2 * n, p1 - (L - I) * u, p1 - L * u - Wd / 2 * n]
    inv = tr.inverted()
    end = inv.transform(p1 - (L - I) * u)
    ax.plot([xy0[0], end[0]], [xy0[1], end[1]], color=color, lw=lw, solid_capstyle='butt', transform=tr,
            zorder=zorder, clip_on=False)
    poly = Polygon(inv.transform(_np.array(head)), closed=True, facecolor=color, edgecolor='none', transform=tr,
                   zorder=zorder, clip_on=False)
    ax.add_patch(poly)
    return poly


def leak_marker(ax, x, y, n, transform=None, zorder=6):
    """(Legacy; RESTRAINT rule 8 bans numbered discs.) LEAK disc (3.2 mm) with a white bold digit, = TikZ \\leak{n}."""
    tr = transform or ax.transData
    ax.plot([x], [y], ls='none', marker='o', ms=LEAK_DIAM_MM * PT_PER_MM, mfc=ACCENT, mec='none', transform=tr,
            zorder=zorder, clip_on=False)
    size = FS['note']
    t = offset_copy(tr, fig=ax.figure, x=0, y=-size * CAP_EM / 2, units='points')
    return ax.text(x, y, str(n), transform=t, fontsize=size, fontweight='bold', color=SURFACE, ha='center',
                   va='baseline', zorder=zorder + 1, clip_on=False)


# ------------------------------------------------------------------------------------------------------------------
# number formatting (identical to analysis/numreg.render, plus typographic minus / en dash for display)
# ------------------------------------------------------------------------------------------------------------------
MINUS = '−'
EN_DASH = '–'


def render(v, f='int'):
    """Same renderings as analysis/numreg.py (so figure text matches RESULTS.md digit for digit)."""
    if f == 'int':
        return f'{int(round(v)):,}'
    if f == 'pct0':
        return f'{100 * v:.0f}'
    if f == 'pct1':
        return f'{100 * v:.1f}'
    if f == 'pct2':
        return f'{100 * v:.2f}'
    if f.startswith('f'):
        return f'{v:.{int(f[1:])}f}'
    if f == 'raw':
        return str(v)
    raise ValueError(f)


def typo(s):
    """ASCII hyphen-minus in a rendered number -> typographic minus."""
    return s.replace('-', MINUS)


def fmt_int(n):
    return f'{int(round(n)):,}'


def fmt_dec(x, decimals=1):
    """Fixed decimals, typographic minus; '-0.0' never appears."""
    s = f'{x:.{decimals}f}'
    if s.lstrip('-').strip('0.') == '':
        s = s.lstrip('-')
    return typo(s)


def fmt_sig(x, sig=2, thousands=True):
    """`sig` significant digits without scientific notation: fmt_sig(0.98489, 3) -> '0.985'; fmt_sig(1234.5, 3) ->
    '1,230'; fmt_sig(9.96, 2) -> '10'; fmt_sig(0.0995, 2) -> '0.10'. Trailing zeros are kept (they are significant)."""
    if x == 0:
        return '0'
    r = float(f'{x:.{sig}g}')
    e = math.floor(math.log10(abs(r)))
    d = sig - 1 - e
    if d > 0:
        s = f'{r:.{d}f}'
    else:
        s = f'{r:,.0f}' if thousands else f'{r:.0f}'
    return typo(s)


def fmt_pct(p, decimals=1):
    """A share (0-1) as a percentage: fmt_pct(0.699, 1) -> '69.9%'."""
    return fmt_dec(100 * p, decimals) + '%'


def fmt_k_of_n(k, n):
    return f'{fmt_int(k)} of {fmt_int(n)}'


def fmt_ci(lo, hi, decimals=1, scale=100):
    """'34.6–56.6'; with a negative bound '−8.4 to 35.6' (an en dash next to a minus sign misreads)."""
    a, b = fmt_dec(scale * lo, decimals), fmt_dec(scale * hi, decimals)
    return f'{a} to {b}' if (lo < 0 or hi < 0) else f'{a}{EN_DASH}{b}'


def fmt_pp(x, decimals=1, scale=100):
    return fmt_dec(scale * x, decimals) + ' pp'


def fmt_p(p):
    return 'p < 0.001' if p < 0.001 else f'p = {p:.3f}'


# ------------------------------------------------------------------------------------------------------------------
# numbers: read from stats.json / derived_numbers.json only, and registered for trace checks
# ------------------------------------------------------------------------------------------------------------------
_STATS = None
_DERIVED = None
_REG = []


def _walk(cur, key):
    for part in key.split('/'):
        part = part.replace('~1', '/')      # JSON-pointer escape, as in analysis/numreg.py ('Reddit~1other')
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    return cur


def stat(key):
    """Value at a '/'-separated key of analysis/outputs/stats.json (e.g. 'fig1b/banner_fires/k')."""
    global _STATS
    if _STATS is None:
        _STATS = json.load(open(STATS_JSON))
    return _walk(_STATS, key)


def derived(key):
    """Value at a '/'-separated key of figures/v7/derived_numbers.json; the record's 'value' level is implied
    ('fig3c_timing_split/before_one_poll' reads D['fig3c_timing_split']['value']['before_one_poll'])."""
    global _DERIVED
    if _DERIVED is None:
        _DERIVED = json.load(open(DERIVED_JSON))
    name, _, rest = key.partition('/')
    rec = _DERIVED[name]['value']
    return _walk(rec, rest) if rest else rec


def N(key, f='int', source='stats'):
    """Render the number at `key` (stats.json, or derived_numbers.json with source='derived') and register it."""
    v = stat(key) if source == 'stats' else derived(key)
    s = render(v, f)
    _REG.append(dict(text=s, shown=typo(s), source=source, key=key, fmt=f, value=json.dumps(v)))
    return typo(s)


def KN(key, source='stats', sep=' of '):
    """'k of n' from a {k, n, ...} record."""
    return N(key + '/k', 'int', source) + sep + N(key + '/n', 'int', source)


def PCT(key, f='pct1', source='stats'):
    """'69.9%' from a {p, ...} record."""
    return N(key + '/p', f, source) + '%'


def CI(key, f='pct1', source='stats'):
    """'63.8–75.4' from a {lo, hi, ...} record (percentage units with pct formats)."""
    lo, hi = N(key + '/lo', f, source), N(key + '/hi', f, source)
    return f'{lo} to {hi}' if (lo.startswith(MINUS) or hi.startswith(MINUS)) else f'{lo}{EN_DASH}{hi}'


def write_registry(path):
    """Write every number rendered through N/KN/PCT/CI since the last reset (text, shown, source, key, fmt, value)."""
    with open(path, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['text', 'shown', 'source', 'key', 'fmt', 'value'])
        w.writeheader()
        w.writerows(_REG)
    return path


def reset_registry():
    _REG.clear()


# ------------------------------------------------------------------------------------------------------------------
# audit and save
# ------------------------------------------------------------------------------------------------------------------
class FigureStyleError(RuntimeError):
    pass


_ARIAL_CMAP = None


def _arial_chars():
    global _ARIAL_CMAP
    if _ARIAL_CMAP is None:
        from matplotlib import ft2font
        cm = set()
        for w in ('normal', 'bold'):
            fn = _fm.findfont(_fm.FontProperties(family='Arial', weight=w), fallback_to_default=False)
            cm |= set(ft2font.FT2Font(fn).get_charmap().keys())
        _ARIAL_CMAP = cm
    return _ARIAL_CMAP


def _texts(fig):
    out = list(fig.texts)
    for lg in fig.legends:
        out += list(lg.get_texts()) + [lg.get_title()]
    for ax in fig.axes:
        if not ax.get_visible():
            continue
        out += list(ax.texts) + [ax.title, ax._left_title, ax._right_title]
        # axis text is drawn only when the axes has its axis on (ax.axis('off') hides it) and that axis is visible
        for axis, ticklabels in ((ax.xaxis, ax.get_xticklabels()), (ax.yaxis, ax.get_yticklabels())):
            if ax.axison and axis.get_visible():
                out += [axis.label, axis.get_offset_text()] + list(ticklabels)
        lg = ax.get_legend()
        if lg is not None:
            out += list(lg.get_texts()) + [lg.get_title()]
    return [t for t in out if isinstance(t, Text) and t.get_visible() and t.get_text().strip()]


def audit(fig, letter_zone=True, tol_mm=0.15, title=False):
    """Return a list of problems: text below FS['min'] (6 pt), tick labels below FS['tick'] (6.5 pt), axis titles not
    FS['axis'] (7 pt), a font other than Arial, a glyph Arial lacks (it would fall back to DejaVu), anything outside
    the canvas, anything in the letter zone, or a canvas that is not the declared size."""
    probs = []
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    W, H = size_mm(fig)
    wi, hi = fig.get_size_inches()
    if abs(wi * 25.4 - W) > 0.01 or abs(hi * 25.4 - H) > 0.01:
        probs.append(f'canvas is {wi * 25.4:.2f} x {hi * 25.4:.2f} mm, declared {W} x {H} mm')
    px = fig.dpi / 25.4
    canvas = Bbox.from_extents(-tol_mm * px, -tol_mm * px, (W + tol_mm) * px, (H + tol_mm) * px)
    zone_w = W if title else LETTER_ZONE_MM[0]      # a composite title runs along the whole top band
    zone = Bbox.from_extents(0, (H - LETTER_ZONE_MM[1]) * px, zone_w * px, H * px)
    arial = _arial_chars()
    ticks = set()
    axis_titles = set()
    for ax in fig.axes:
        ticks |= {id(t) for t in ax.get_xticklabels() + ax.get_yticklabels()}
        axis_titles |= {id(ax.xaxis.label), id(ax.yaxis.label)}
    for t in _texts(fig):
        s = t.get_text()
        size = t.get_fontsize()
        tag = repr(s[:30])
        if size < FS['min'] - 0.01:
            probs.append(f'text {tag} is {size:.2f} pt (< {FS["min"]} pt)')
        if id(t) in ticks and size < FS['tick'] - 0.01:
            probs.append(f'tick label {tag} is {size:.2f} pt (< {FS["tick"]} pt)')
        if id(t) in axis_titles and abs(size - FS['axis']) > 0.01:
            probs.append(f'axis title {tag} is {size:.2f} pt (plan: {FS["axis"]} pt)')
        fn = os.path.basename(_fm.findfont(t.get_fontproperties()))
        if not fn.lower().startswith('arial'):
            probs.append(f'text {tag} resolves to font file {fn} (must be Arial)')
        if '$' not in s:
            missing = sorted({c for c in s if ord(c) not in arial and c not in '\n\t'})
            if missing:
                probs.append(f'text {tag} has glyphs Arial lacks {missing} (would fall back to another font)')
        bb = t.get_window_extent(r)
        if not (canvas.x0 <= bb.x0 and bb.x1 <= canvas.x1 and canvas.y0 <= bb.y0 and bb.y1 <= canvas.y1):
            probs.append(f'text {tag} extends outside the panel canvas')
        if letter_zone and bb.overlaps(zone) and bb.width > 0 and not getattr(t, '_fs_title', False):
            probs.append(f'text {tag} enters the {zone_w:g} x {LETTER_ZONE_MM[1]:g} mm letter/title zone')
    for i, ax in enumerate(fig.axes):
        if not ax.get_visible():
            continue
        bb = ax.get_tightbbox(r)
        if bb is None:
            continue
        if not (canvas.x0 <= bb.x0 and bb.x1 <= canvas.x1 and canvas.y0 <= bb.y0 and bb.y1 <= canvas.y1):
            probs.append(f'axes {i}: artists extend outside the panel canvas by up to '
                         f'{max(canvas.x0 - bb.x0, bb.x1 - canvas.x1, canvas.y0 - bb.y0, bb.y1 - canvas.y1) / px:.2f} mm')
        if letter_zone and bb.overlaps(zone):
            # only a problem if something is actually drawn there (the axes patch is white and invisible)
            inter = Bbox.intersection(bb, zone)
            if inter is not None and inter.width > 0.5 and inter.height > 0.5:
                probs.append(f'axes {i}: its artists enter the {zone_w:g} x {LETTER_ZONE_MM[1]:g} mm letter/title zone')
    return probs


def save_panel(fig, path, strict=True, letter_zone=True, title=False, close=True):
    """Save a panel as a vector PDF at exactly its declared size (never bbox_inches='tight'), after audit().
    title=True: the composite draws a panel title, so the whole top LETTER_ZONE_MM[1] band must stay empty.
    The file is written even when the audit fails (so it can be inspected); strict=True then raises."""
    probs = audit(fig, letter_zone=letter_zone, title=title)
    os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
    fig.savefig(path, format='pdf', metadata={'Creator': 'figstyle.py (study3 figures v6)', 'Producer': None,
                                              'CreationDate': None})
    if close:
        plt.close(fig)
    if probs:
        msg = f'{os.path.basename(path)}: {len(probs)} style problem(s):\n  - ' + '\n  - '.join(probs)
        if strict:
            raise FigureStyleError(msg)
        print('WARNING ' + msg)
    return path


# ------------------------------------------------------------------------------------------------------------------
# LaTeX side: palette_v2.tex (read by tikzstyle_v2.tex)
# ------------------------------------------------------------------------------------------------------------------
_TEX_VENDOR = {'Google': 'vGoogle', 'TikTok': 'vTikTok', 'Meta': 'vMeta', 'Pinterest': 'vPinterest', 'Snap': 'vSnap',
               'Microsoft': 'vMicrosoft', 'Reddit/other': 'vOther'}


def write_tex(path=PALETTE_TEX):
    def hx(c):
        return c.lstrip('#').upper()
    L = ['% palette_v2.tex -- GENERATED by figstyle.py --write-tex (v6 RESTRAINT tokens; vendor hexes from colors.py).',
         '% Do not edit: change figstyle.py and regenerate, so matplotlib and TikZ never drift apart.',
         '% ---- vendors (identity only; fixed order; only where vendors are the categories) ----']
    for v in VENDOR_ORDER:
        L.append(f'\\definecolor{{{_TEX_VENDOR[v]}}}{{HTML}}{{{hx(VENDOR[v])}}}')
    L.append('% ---- v6 semantic tokens (RESTRAINT rule 6): one meaning each; never in a panel with vendor hues ----')
    for name, c in [('LEAK', LEAK), ('HONOUR', HONOUR), ('THIRD', THIRD), ('EVENT', EVENT), ('NEUTRAL', NEUTRAL),
                    ('LIGHT', LIGHT), ('AXIS', AXIS), ('SAND', SAND)]:
        L.append(f'\\definecolor{{{name}}}{{HTML}}{{{hx(c)}}}')
    L.append('% ---- neutrals and legacy names (accent = LEAK; greyM = NEUTRAL; greyL = LIGHT; sand = SAND) ----')
    for name, c in [('ink', INK), ('axisc', AXIS), ('greyD', GREY_D), ('greyM', GREY_M), ('greyL', GREY_L),
                    ('greyXL', GREY_XL), ('gridc', GRID), ('context', CONTEXT), ('surface', SURFACE),
                    ('accent', ACCENT), ('leak', LEAK), ('honour', HONOUR),
                    ('sand', SAND), ('sandD', SAND_D), ('sandT', SAND_T), ('mainD', MAIN_D), ('mainT', MAIN_T),
                    ('extT', EXT_T)]:
        L.append(f'\\definecolor{{{name}}}{{HTML}}{{{hx(c)}}}')
    L.append('% ---- sciplot clean skin (Figure 1 bake-off 2): theme neutrals and OKLab pre-mixed token tints ----')
    for name, c in SKIN.items():
        L.append(f'\\definecolor{{{name.replace("_", "")}}}{{HTML}}{{{hx(c)}}}')
    L.append('% ---- hex strings for display (style sheet) ----')
    for v in VENDOR_ORDER:
        L.append(f'\\def\\hex{_TEX_VENDOR[v][1:]}{{\\#{VENDOR[v].lstrip("#").lower()}}}')
    for name, c in [('Ink', INK), ('Axis', AXIS), ('GreyD', GREY_D), ('GreyM', GREY_M), ('GreyL', GREY_L),
                    ('Grid', GRID), ('Context', CONTEXT), ('Accent', ACCENT), ('Leak', LEAK), ('Honour', HONOUR),
                    ('Third', THIRD), ('Event', EVENT), ('Neutral', NEUTRAL), ('Light', LIGHT), ('Sand', SAND)]:
        L.append(f'\\def\\hex{name}{{\\#{c.lstrip("#").lower()}}}')
    # Units: matplotlib and PDF points are big points (1/72 in); TeX's `pt` is 1/72.27 in. Every size below is therefore
    # given in bp (strokes, markers) or as the TeX-pt number that equals the bp size (\\fontsize takes TeX pt), so a
    # 12 pt letter from LaTeX is exactly as large as a 12 pt matplotlib label.
    L.append('% ---- type sizes: \\figFs<X> = size in bp (for display); \\figFs<X>TeX = the same size in TeX pt ----')
    for k, v in FS.items():
        nm = k.replace("_", "").capitalize()
        L.append(f'\\def\\figFs{nm}{{{v:g}}}\\def\\figFs{nm}TeX{{{v * 72.27 / 72:.4f}}}'
                 f'\\def\\figFs{nm}Lead{{{1.2 * v * 72.27 / 72:.4f}}}')
    L.append('% ---- strokes (bp) ----')
    for k, v in LW.items():
        L.append(f'\\def\\figLw{k.replace("_", "").capitalize()}{{{v:g}bp}}')   # no '_' in TeX names
    L.append(f'\\def\\figTickLen{{{TICK_LEN_PT:g}bp}}')
    L.append(f'\\def\\figHatchDistance{{{HATCH_SPACING_PT:.3f}bp}}')
    L.append(f'\\def\\figStealthLength{{{STEALTH["length"]:g}bp}}')
    L.append(f'\\def\\figStealthWidth{{{STEALTH["width"]:g}bp}}')
    L.append(f'\\def\\figStealthInset{{{STEALTH["inset"]:g}bp}}')
    L.append('% ---- arm markers (bp): the same geometry as matplotlib ms (circle diameter, square side, triangle width =')
    L.append('%      height, diamond half-diagonal = ms / sqrt 2) and edge widths ----')
    for k in ARM_ORDER:
        L.append(f'\\def\\figMs{k}{{{ARM[k]["ms"]:g}bp}}\\def\\figMew{k}{{{ARM[k]["mew"]:g}bp}}')
    L.append(f'\\def\\figMsRepeatHalfDiag{{{ARM["Repeat"]["ms"] / math.sqrt(2):.3f}bp}}')
    L.append(f'\\def\\figMsComparison{{{COMPARISON["ms"]:g}bp}}\\def\\figMewComparison{{{COMPARISON["mew"]:g}bp}}')
    L.append('% ---- layout (mm) ----')
    L.append(f'\\def\\figWidth{{{FIG_W_MM:g}}}\\def\\figMaxHeight{{{FIG_MAX_H_MM:g}}}\\def\\figGutter{{{GUTTER_MM:g}}}')
    L.append(f'\\def\\figLetterZoneW{{{LETTER_ZONE_MM[0]:g}}}\\def\\figLetterZoneH{{{LETTER_ZONE_MM[1]:g}}}')
    L.append(f'\\def\\figLeakDiam{{{LEAK_DIAM_MM:g}mm}}')
    open(path, 'w').write('\n'.join(L) + '\n')
    return path


# ------------------------------------------------------------------------------------------------------------------
# self-test
# ------------------------------------------------------------------------------------------------------------------
def _check_rc():
    """style_v2.mplstyle must carry the same RESTRAINT values as FS / LW / ARM (one source of truth, no drift)."""
    rc = mpl.rc_params_from_file(STYLE_FILE, use_default_template=False)
    want = {'axes.labelsize': FS['axis'], 'xtick.labelsize': FS['tick'], 'ytick.labelsize': FS['tick'],
            'legend.fontsize': FS['legend'], 'font.size': FS['label'], 'axes.linewidth': LW['axis'],
            'xtick.major.width': LW['axis'], 'ytick.major.width': LW['axis'], 'xtick.major.size': TICK_LEN_PT,
            'ytick.major.size': TICK_LEN_PT, 'lines.linewidth': LW['data'], 'lines.markersize': ARM['Default']['ms'],
            'errorbar.capsize': 0, 'axes.grid': False, 'axes.spines.top': True, 'axes.spines.right': True,
            'axes.spines.left': True, 'axes.spines.bottom': True, 'xtick.direction': 'out', 'ytick.direction': 'out'}
    bad = {k: (rc[k], v) for k, v in want.items() if rc[k] != v}
    assert not bad, f'style_v2.mplstyle drifted from figstyle (rc, figstyle): {bad}'
    for k in ('axes.edgecolor', 'xtick.color', 'ytick.color'):
        assert mpl.colors.to_hex(rc[k]) == AXIS, (k, rc[k])


def selftest():
    _check_encodings()
    _check_rc()
    assert fmt_sig(0.98489, 3) == '0.985' and fmt_sig(1234.5, 3) == '1,230' and fmt_sig(9.96, 2) == '10'
    assert fmt_sig(0.0995, 2) == '0.10' and fmt_sig(-8.44, 2) == MINUS + '8.4'
    assert fmt_ci(-0.084, 0.356) == MINUS + '8.4 to 35.6' and fmt_ci(0.346, 0.566) == '34.6' + EN_DASH + '56.6'
    assert fmt_dec(-0.0001, 1) == '0.0'
    # label rule 1 (cross-figure QA 2): 'p% · k of n' from n = 10, 'k of n' below
    assert share_label('86', '6 of 7', 7) == '6 of 7' and share_label('46', '106 of 233', 233) == '46% · 106 of 233'
    assert wrap(PRECHOICE_AXIS_TITLE, 'any') == 'Sandboxed ad request before\nany choice (% of stores)'
    # formatting must equal analysis/numreg.render on real values
    sys.path.insert(0, os.path.join(STUDY, 'analysis'))
    try:
        import numreg
        for key, f in [('fig1b/banner_fires/p', 'pct1'), ('fig1b/banner_fires/lo', 'pct1'), ('design/n_main', 'int'),
                       ('validation/A0_vs_A0r/kappa', 'f3'), ('fig5/a/Any vendor/Default/p', 'pct0')]:
            assert render(stat(key), f) == numreg.render(stat(key), f), key
        print('selftest: formatters match analysis/numreg.render')
    except ImportError:
        print('selftest: analysis/numreg.py not importable; formatter parity not checked')
    assert all(ord(c) in _arial_chars() for c in MINUS + EN_DASH + '≥≤→κ·×'), 'Arial lacks a standard glyph'
    print('selftest: v6 tokens, encodings, mplstyle parity, formatters and glyph coverage OK; letter cap',
          f'{LETTER_CAP_MM:.3f} mm')


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--write-tex', action='store_true', help='write palette_v2.tex next to this module')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.write_tex:
        print('wrote', write_tex())
    if a.selftest:
        selftest()
    if not (a.write_tex or a.selftest):
        ap.print_help()
