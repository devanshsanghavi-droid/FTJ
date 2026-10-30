#!/usr/bin/env python3
"""qa_check.py -- the QA gate for a v6 figure or panel PDF (binding: ../RESTRAINT.md, which wins over ../DESIGN_V6.md).

Usage
    python3 qa_check.py FIG.pdf                  # a whole figure: 190 +- 0.5 mm wide, at most 230 mm high
    python3 qa_check.py PANEL.pdf --panel 62 66  # a single panel: exactly 62 x 66 mm (+- 0.2 mm)
    options: --dpi 300 (render resolution), --png-prefix PATH (default: next to the PDF, <stem>_qa<dpi>),
             --no-render, --allow-semantic-with-vendors (alias --allow-red-with-vendors; only for the style sheet's
             colour dictionary), --list-text (list every text run with its size, font and panel)

What it checks (exit status 1 on any FAIL)
    size       page width 190 +- 0.5 mm and height <= 230 mm (or the --panel size)
    fonts      every font on the page and inside every nested panel (form XObject): Arial / Helvetica / TeX Gyre
               Heros / Liberation Sans only, embedded, no Type 3 (Font Awesome is accepted but WARNs: no icons in v6)
    raster     any image XObject or inline image FAILs (the figure set is vector only)
    text size  effective size of every text run (Tf x text matrix x CTM): FAIL below FS["min"] (6 pt); WARN between
               6 and 6.5 pt, at a size off the v6 scale (6.5 ticks / notes, 7 labels, 8.5 letters), or above 9 pt
               (RESTRAINT rule 1: no hero numbers); a size histogram
    rescale    any panel drawn with a scale other than 1 (panels are drawn at final size, never rescaled)
    letters    bold single lowercase panel letters at FS["letter"] (8.5 pt): FAIL at another size; FAIL bold text on a
               letter's baseline (a panel title: RESTRAINT rule 2); which letters share a baseline / an x
    colours    fill and stroke colours per panel against the v6 palette (figstyle tokens LEAK, HONOUR, THIRD, EVENT,
               NEUTRAL, LIGHT, AXIS, SAND, the neutrals, the fixed vendor hexes, the ramps). FAIL a semantic token in
               the same panel as vendor hues (each sits within ~10 OKLab dE of one; EVENT-Pinterest 2.0); FAIL cyan
               (debug grid); FAIL any Okabe-Ito hue (figstyle.BANNED_HUES); WARN a retired v5 colour or any other
               colour not in the palette
    leftovers  'MISSING PANEL' placeholders from composite_template.tex
Then it renders the PDF to PNG with paper/tools/pdfpages2png and prints the Visual QA checklist (RESTRAINT rules).
READ THE PNG with the Read tool and answer every item in writing. Delete the PNG when done (disk is tight).
"""
import argparse
import collections
import math
import os
import re
import subprocess
import sys

from pypdf import PdfReader

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import figstyle as fs  # noqa: E402  (palette, sizes, renderer path)

PT2MM = 25.4 / 72
OK_FONT = re.compile(r'^(arial|helvetica|texgyreheros|tex-gyre-heros|liberationsans|fontawesome5)', re.I)
ICON_FONT = re.compile(r'^fontawesome', re.I)       # accepted (older files compile) but WARNs: no icons in v6


# ---------------------------------------------------------------------------------------------------- resources walk
def _embedded(font):
    st = font.get('/Subtype')
    if st == '/Type3':
        return True
    desc = None
    if st == '/Type0':
        dfs = font.get('/DescendantFonts')
        if dfs:
            desc = dfs.get_object()[0].get_object().get('/FontDescriptor')
    else:
        desc = font.get('/FontDescriptor')
    if desc is None:
        return False
    desc = desc.get_object()
    return any(k in desc for k in ('/FontFile', '/FontFile2', '/FontFile3'))


def walk_resources(res, seen, fonts, images, image_names, forms):
    if res is None:
        return
    res = res.get_object()
    fd = res.get('/Font')
    if fd is not None:
        for _, ref in fd.get_object().items():
            f = ref.get_object()
            base = str(f.get('/BaseFont', '?')).lstrip('/')
            base = base.split('+', 1)[-1]
            fonts[base] = dict(subtype=str(f.get('/Subtype')), embedded=_embedded(f))
            if f.get('/Subtype') == '/Type3':
                walk_resources(f.get('/Resources'), seen, fonts, images, image_names, forms)
    xo = res.get('/XObject')
    if xo is not None:
        for name, ref in xo.get_object().items():
            obj = ref.get_object()
            key = getattr(ref, 'idnum', None) or id(obj)
            st = obj.get('/Subtype')
            if st == '/Image':
                image_names.add(str(name))
                if key not in seen:
                    images.append((str(name), obj.get('/Width'), obj.get('/Height')))
            elif st == '/Form':
                m = obj.get('/Matrix')
                if m is not None:
                    m = [float(v) for v in m]
                    forms.append((str(name), math.sqrt(abs(m[0] * m[3] - m[1] * m[2]))))
                if key in seen:
                    continue
                seen.add(key)
                walk_resources(obj.get('/Resources'), seen, fonts, images, image_names, forms)
            seen.add(key)
    pat = res.get('/Pattern')
    if pat is not None:
        for _, ref in pat.get_object().items():
            p = ref.get_object()
            walk_resources(p.get('/Resources'), seen, fonts, images, image_names, forms)


# ---------------------------------------------------------------------------------------------------- content walk
def _mul(m1, m2):
    """PDF matrix product m1 x m2 (apply m1, then m2); matrices are [a b c d e f]."""
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return [a1 * a2 + b1 * c2, a1 * b2 + b1 * d2, c1 * a2 + d1 * c2, c1 * b2 + d1 * d2,
            e1 * a2 + f1 * c2 + e2, e1 * b2 + f1 * d2 + f2]


def _scale(m):
    return math.sqrt(abs(m[0] * m[3] - m[1] * m[2]))


def _tounicode(font):
    """(bytes per code, {code: text}) from a font's ToUnicode CMap (bfchar and bfrange); latin-1 otherwise."""
    width = 2 if font.get('/Subtype') == '/Type0' else 1
    cmap = {}
    tu = font.get('/ToUnicode')
    if tu is None:
        return width, cmap
    data = tu.get_object().get_data().decode('latin-1')

    def u(h):
        try:
            return bytes.fromhex(h).decode('utf-16-be')
        except Exception:
            return '?'
    for block in re.findall(r'beginbfchar(.*?)endbfchar', data, re.S):
        for src, dst in re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', block):
            cmap[int(src, 16)] = u(dst)
    for block in re.findall(r'beginbfrange(.*?)endbfrange', data, re.S):
        for lo, hi, rest in re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(\[[^\]]*\]|<[0-9A-Fa-f]+>)', block):
            lo, hi = int(lo, 16), int(hi, 16)
            if rest.startswith('['):
                for i, d in enumerate(re.findall(r'<([0-9A-Fa-f]+)>', rest)):
                    cmap[lo + i] = u(d)
            else:
                base = bytes.fromhex(rest[1:-1])
                for i in range(hi - lo + 1):
                    v = int.from_bytes(base, 'big') + i
                    cmap[lo + i] = u(v.to_bytes(len(base), 'big').hex())
    return width, cmap


class Walker:
    """Walk the page content and every nested form XObject with a real graphics state (CTM stack, text matrix),
    collecting text runs (decoded text, font, effective size, page position), colours per top-level panel, form
    placement scales and inline images."""

    def __init__(self, reader):
        self.reader = reader
        self.runs, self.scales = [], []
        self.colors = collections.defaultdict(collections.Counter)
        self.inline_images = 0
        self._fontcache = {}

    def _font(self, fobj):
        key = id(fobj)
        if key not in self._fontcache:
            name = str(fobj.get('/BaseFont', '?')).lstrip('/').split('+', 1)[-1]
            w, cmap = _tounicode(fobj)
            self._fontcache[key] = (name, w, cmap)
        return self._fontcache[key]

    @staticmethod
    def _hex(operands):
        nums = [float(o) for o in operands if isinstance(o, (int, float)) or type(o).__name__ in
                ('FloatObject', 'NumberObject')]
        if len(nums) == 1:
            rgb = (nums[0],) * 3
        elif len(nums) == 3:
            rgb = tuple(nums)
        elif len(nums) == 4:
            c, m, y, k = nums
            rgb = ((1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k))
        else:
            return None
        return '#%02x%02x%02x' % tuple(max(0, min(255, round(v * 255))) for v in rgb)

    def _color(self, panel, operands):
        nums = [float(o) for o in operands if isinstance(o, (int, float)) or type(o).__name__ in
                ('FloatObject', 'NumberObject')]
        if len(nums) == 1:
            rgb = (nums[0],) * 3
        elif len(nums) == 3:
            rgb = tuple(nums)
        elif len(nums) == 4:
            c, m, y, k = nums
            rgb = ((1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k))
        else:
            return
        self.colors[panel]['#%02x%02x%02x' % tuple(max(0, min(255, round(v * 255))) for v in rgb)] += 1

    def walk(self, stream_obj, resources, ctm, panel='page', depth=0, seen=None, fill='#000000'):
        # v7: each text run also records its fill colour (the non-stroking colour in force), so a check can tell
        # muted secondary text (fs.SP_MUTED) from words
        from pypdf.generic import ContentStream
        seen = seen or set()
        resources = resources.get_object() if resources is not None else {}
        fonts = resources.get('/Font')
        fonts = fonts.get_object() if fonts is not None else {}
        xobjs = resources.get('/XObject')
        xobjs = xobjs.get_object() if xobjs is not None else {}
        try:
            cs = stream_obj if isinstance(stream_obj, ContentStream) else ContentStream(stream_obj, self.reader)
        except Exception as e:
            print(f'WARN could not parse a content stream in {panel}: {e!r}')
            return
        stack = []
        tm = tlm = [1, 0, 0, 1, 0, 0]
        font, size, leading = None, 0.0, 0.0
        for operands, op in cs.operations:
            if op == b'q':
                stack.append((ctm, fill))
            elif op == b'Q':
                ctm, fill = stack.pop() if stack else (ctm, fill)
            elif op == b'cm':
                ctm = _mul([float(v) for v in operands], ctm)
            elif op == b'BT':
                tm = tlm = [1, 0, 0, 1, 0, 0]
            elif op == b'Tf':
                f = fonts.get(operands[0])
                font = self._font(f.get_object()) if f is not None else ('?', 1, {})
                size = float(operands[1])
            elif op == b'TL':
                leading = float(operands[0])
            elif op == b'Tm':
                tm = tlm = [float(v) for v in operands]
            elif op in (b'Td', b'TD'):
                tx, ty = float(operands[0]), float(operands[1])
                if op == b'TD':
                    leading = -ty
                tm = tlm = _mul([1, 0, 0, 1, tx, ty], tlm)
            elif op in (b'T*', b"'", b'"'):
                tm = tlm = _mul([1, 0, 0, 1, 0, -leading], tlm)
            if op in (b'Tj', b'TJ', b"'", b'"'):
                arr = operands[-1] if op != b'TJ' else operands[0]
                parts = arr if op == b'TJ' else [arr]
                name, w, cmap = font or ('?', 1, {})
                text = ''
                for p in parts:
                    if isinstance(p, (int, float)):
                        if float(p) <= -200:          # a TJ gap of >= 0.2 em is a word space (XeTeX sets no spaces)
                            text += ' '
                        continue
                    raw = p.original_bytes if hasattr(p, 'original_bytes') else bytes(p)
                    codes = [int.from_bytes(raw[i:i + w], 'big') for i in range(0, len(raw) - w + 1, w)]
                    text += ''.join(cmap.get(c, chr(c) if w == 1 else '?') for c in codes)
                trm = _mul(tm, ctm)
                sc = _scale(trm) or 1.0
                self.runs.append(dict(text=text, font=name, size=size * _scale(trm), x=trm[4], y=trm[5],
                                      depth=depth, panel=panel, fill=fill,
                                      rot=(trm[0] / sc, trm[1] / sc, trm[2] / sc, trm[3] / sc)))
            elif op in (b'rg', b'RG', b'g', b'G', b'k', b'K', b'sc', b'SC', b'scn', b'SCN'):
                self._color(panel, operands)
                if op in (b'rg', b'g', b'k', b'sc', b'scn'):
                    fill = self._hex(operands) or fill
            elif op in (b'INLINE IMAGE', b'BI'):
                self.inline_images += 1
            elif op == b'Do':
                ref = xobjs.get(operands[0])
                if ref is None:
                    continue
                obj = ref.get_object()
                if obj.get('/Subtype') != '/Form':
                    continue
                m = [float(v) for v in obj.get('/Matrix', [1, 0, 0, 1, 0, 0])]
                fctm = _mul(m, ctm)
                self.scales.append((str(operands[0]), _scale(fctm)))      # absolute scale on the page
                key = id(obj)
                if key in seen:
                    continue
                self.walk(obj, obj.get('/Resources') or resources, fctm,
                          str(operands[0]) if depth == 0 else panel, depth + 1, seen | {key}, fill)


# ---------------------------------------------------------------------------------------------------- palette
def palette():
    """The v6 palette: every colour a figure may draw, by name (figstyle is the single source)."""
    named = {}
    for n, c in [('white', fs.SURFACE), ('black / ink', fs.INK), ('axis near-black', fs.AXIS),
                 ('dark grey (secondary text)', fs.GREY_D), ('NEUTRAL grey', fs.NEUTRAL), ('LIGHT grey', fs.LIGHT),
                 ('faint grey', fs.GREY_XL), ('SAND sandbox dark slate', fs.SAND),
                 ('LEAK brick (consent lost)', fs.LEAK), ('HONOUR slate (consent honoured)', fs.HONOUR),
                 ('THIRD lavender', fs.THIRD), ('EVENT amber (consent event)', fs.EVENT)]:
        named.setdefault(c.lower(), n)
    for k, c in getattr(fs, 'SKIN', {}).items():                # sciplot clean skin (Figure 1 bake-off 2)
        named.setdefault(c.lower(), 'sciplot ' + k)
    for k in fs.ORIGIN_ORDER:                                   # request-origin ordinal grey ramp
        named.setdefault(fs.ORIGIN[k]['facecolor'].lower(), f'origin {k}')
    for v in fs.VENDOR_ORDER:
        named[fs.VENDOR[v].lower()] = 'vendor ' + v
    for i, c in enumerate(fs.ORD_BLUE):
        named.setdefault(c.lower(), f'ordinal blue {i + 1}')
    for i, c in enumerate(getattr(fs, 'GREY_RAMP', [])):
        named.setdefault(c.lower(), f'ordinal grey {i + 1}')
    return named


# colours of the v5 set that v6 retired: reported by name, so a leftover is easy to find
RETIRED_V5 = {'#d03b3b': 'v5 red #d03b3b (now LEAK #c65358)', '#52514e': 'v5 warm dark grey (now #555555)',
              '#8a8984': 'v5 warm mid grey (now NEUTRAL #a0a0a0)', '#deddd9': 'v5 warm light grey (now LIGHT #d9d9d9)',
              '#c3c2b7': 'v5 context grey (now LIGHT)', '#e1e0d9': 'v5 grid colour (no gridlines in v6)',
              '#f3f2ef': 'v5 faint grey', '#2b2b2b': 'v4/v5 sandbox near-black (now SAND #3b4656)',
              '#0b0b0b': 'colors.py INK (v6 text and marks are #000000)'}


def match(hexc, named, tol=3):
    if hexc.lower() in named:                   # an exact registry hex wins over a near one (e.g. two light greys)
        return named[hexc.lower()]
    r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    for c, n in named.items():
        r2, g2, b2 = (int(c[i:i + 2], 16) for i in (1, 3, 5))
        if max(abs(r - r2), abs(g - g2), abs(b - b2)) <= tol:
            return n
    return None


# ---------------------------------------------------------------------------------------------------- collisions
COLLIDE_MM = 0.1                # v7 (DESIGN_V7 section 11; nature-figure's rendered collision audit): two text runs whose
                                # ink boxes overlap by more than this in both directions collide (FAIL)


def _ink_box(run):
    """Axis-aligned ink box (x0, y0, x1, y1) of a text run in page points, from Arial glyph outlines at the run's size
    and the run's text matrix (rotated runs included)."""
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath
    bold = 'bold' in run['font'].lower()
    try:
        ext = TextPath((0, 0), run['text'], size=run['size'],
                       prop=FontProperties(family='Arial', weight='bold' if bold else 'normal')).get_extents()
    except Exception:
        return None
    a, b, c, d = run.get('rot', (1, 0, 0, 1))
    pts = [(run['x'] + ex * a + ey * c, run['y'] + ex * b + ey * d)
           for ex in (ext.x0, ext.x1) for ey in (ext.y0, ext.y1)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def text_collisions(runs):
    """Pairs of text runs whose ink boxes overlap by more than COLLIDE_MM in x and in y."""
    tol = COLLIDE_MM / PT2MM
    boxes = [(r, _ink_box(r)) for r in runs if r['text'].strip()]
    boxes = [(r, b) for r, b in boxes if b]
    hits = []
    for i in range(len(boxes)):
        r1, b1 = boxes[i]
        for r2, b2 in boxes[i + 1:]:
            ox = min(b1[2], b2[2]) - max(b1[0], b2[0])
            oy = min(b1[3], b2[3]) - max(b1[1], b2[1])
            if ox > tol and oy > tol:
                hits.append((r1['text'].strip()[:24], r2['text'].strip()[:24], ox * PT2MM, oy * PT2MM))
    return hits


# ---------------------------------------------------------------------------------------------------- checklist
CHECKLIST = """
VISUAL QA CHECKLIST (v7, ../DESIGN_V7.md section 11; answer every item in writing in QA.md after READING the PNG)
The test: beside the author's Nature Computational Science exemplars (references/ncs_papers/figpages: AlignIF
01029-2-p02, DIPPER 01015-8-p02, MIRACLE 01030-9-p02, NEP89 01009-6-p04), would it look at home? Refined and crafted,
not busy: if it looks like a poster, dashboard, magazine graphic or AI illustration, simplify.
Figure contract (section 1)
  [ ] One claim (the caption title); one hero panel; every panel a distinct inferential role
  [ ] No headlines, hero numbers, callout bubbles, in-figure prose or panel titles; letters 8 pt bold lowercase
  [ ] Text inside a data panel: axis titles, tick labels, one small key, at most two short direct labels
  [ ] Numbers are in the caption and shown by position
Axes and marks (sections 4-5, 8)
  [ ] Open L axes, 0.6 pt SP_AXIS #3d434b, outward 2.5 pt ticks, no gridlines; data 1.0 pt, markers 3.5 pt
  [ ] Dots + summary for small n; uncapped 95% intervals; honest, shared scales where panels are compared
Colour (section 3)
  [ ] Grey for context, colour for signal; <= 5 colours per panel
  [ ] LEAK brick = consent lost; HONOUR slate = comparison; EVENT amber = banner / click / GPC moment; vendor hexes
      only where vendors are the categories, never with brick
  [ ] Fills are pre-mixed tints (TINT), never alpha; every tint repeats its token's meaning; grounds are very faint
Schematics (sections 6-7)
  [ ] Regions nested at most three levels, each labelled; boxes sized to text (2.4 x 1.6 mm pad), 0.6 pt outlines
  [ ] Connectors stop short; one accent path (LEAK); no empty boxes; muted 6 pt grey secondary text
  [ ] Loss numerals: small outlined brick rings with 6 pt digits, matching the caption; never filled discs
  [ ] No 3D / isometric, shadows, gradients, ribbons, Sankey, icons, emoji, rounded pastel cards
Layout and type (sections 2, 9)
  [ ] Arial; 6 pt ticks and notes, 7 pt words, 8 pt letters; sentence case; nothing below 6 pt
  [ ] Plot areas aligned across panels (shared left / right edges, shared zeros); no text collisions or clipping
  [ ] The five-second test: every panel's point is clear without reading text inside it
Kept
  [ ] Every number traces to stats.json / derived_numbers.json (registry; trace checks pass)
  [ ] Panel letters and contents; Store C anonymity; no placeholder text, debug borders or raster images
"""


def main():
    ap = argparse.ArgumentParser(description='QA gate for a v6 figure/panel PDF')
    ap.add_argument('pdf')
    ap.add_argument('--dpi', type=int, default=300)
    ap.add_argument('--png-prefix')
    ap.add_argument('--panel', nargs=2, type=float, metavar=('W_MM', 'H_MM'))
    ap.add_argument('--width', type=float, default=fs.FIG_W_MM)
    ap.add_argument('--max-height', type=float, default=fs.FIG_MAX_H_MM)
    ap.add_argument('--no-render', action='store_true')
    ap.add_argument('--allow-semantic-with-vendors', '--allow-red-with-vendors', dest='allow_red_with_vendors',
                    action='store_true', help='WARN instead of FAIL when a semantic token shares a panel with vendor '
                    'hues (the style sheet\'s colour dictionary only)')
    ap.add_argument('--list-text', action='store_true',
                    help='also list every text run: size (pt), font, panel form and text (to check the type scale)')
    a = ap.parse_args()

    fails, warns, out = [], [], []
    r = PdfReader(a.pdf)
    n_pages = len(r.pages)
    page = r.pages[0]
    mb = page.mediabox
    w_mm, h_mm = float(mb.width) * PT2MM, float(mb.height) * PT2MM
    out.append(f'QA {os.path.basename(a.pdf)}: {n_pages} page(s), {w_mm:.2f} x {h_mm:.2f} mm')
    if n_pages != 1:
        fails.append(f'{n_pages} pages (a figure is one page)')
    if a.panel:
        if abs(w_mm - a.panel[0]) > 0.2 or abs(h_mm - a.panel[1]) > 0.2:
            fails.append(f'size {w_mm:.2f} x {h_mm:.2f} mm, panel cell is {a.panel[0]:g} x {a.panel[1]:g} mm')
    else:
        if abs(w_mm - a.width) > 0.5:
            fails.append(f'width {w_mm:.2f} mm (must be {a.width:g} +- 0.5 mm)')
        if h_mm > a.max_height + 1e-6:
            fails.append(f'height {h_mm:.2f} mm (must be <= {a.max_height:g} mm)')
    cb = page.cropbox
    if abs(float(cb.width) - float(mb.width)) > 0.5 or abs(float(cb.height) - float(mb.height)) > 0.5:
        warns.append('CropBox differs from MediaBox')

    # resources: fonts, images, forms (page + nested)
    fonts, images, image_names, forms = {}, [], set(), []
    walk_resources(page.get('/Resources'), set(), fonts, images, image_names, forms)
    out.append('fonts: ' + (', '.join(f'{k} ({v["subtype"].lstrip("/")}{"" if v["embedded"] else ", NOT embedded"})'
                                      for k, v in sorted(fonts.items())) or 'none'))
    for k, v in fonts.items():
        if not OK_FONT.match(k):
            fails.append(f'font not allowed: {k} (Arial/Helvetica/TeX Gyre Heros/Liberation Sans only)')
        if not v['embedded']:
            fails.append(f'font not embedded: {k}')
        if v['subtype'] == '/Type3':
            fails.append(f'Type 3 font {k} (matplotlib: pdf.fonttype 42)')
    if images:
        fails.append(f'{len(images)} raster image(s): ' + ', '.join(f'{n} {w}x{h}px' for n, w, h in images[:5]))
    for name, sc in forms:
        if abs(sc - 1) > 0.01:
            fails.append(f'form {name} has a /Matrix with scale {sc:.3f} (rescaled panel)')

    # content: text runs, colours, placements (own walker: exact sizes and positions inside nested panels too)
    wk = Walker(r)
    wk.walk(page.get_contents(), page.get('/Resources'), [1, 0, 0, 1, 0, 0])
    if wk.inline_images:
        fails.append(f'{wk.inline_images} inline raster image(s)')
    for name, sc in wk.scales:
        if abs(sc - 1) > 0.01:
            fails.append(f'panel/form {name} is drawn at scale {sc:.3f} (panels are placed at 100%, never rescaled)')
    runs = [x for x in wk.runs if x['text'].strip()]
    if a.list_text:
        for x in sorted(runs, key=lambda x: (x['panel'], -x['y'], x['x'])):
            out.append(f'  text {x["size"]:5.2f} pt  {x["font"][:18]:18s} [{x["panel"]}] {x["text"].strip()[:60]!r}')
    hist = collections.Counter()
    small = []
    for x in runs:
        n = len(x['text'].strip())
        hist[round(x['size'] * 2) / 2] += n
        if x['size'] < fs.FS['min'] - 0.05:
            small.append(x)
        if 'MISSING PANEL' in x['text']:
            fails.append('placeholder "MISSING PANEL" present (a panel file is missing)')
    if small:
        fails.append(f'{len(small)} text run(s) below {fs.FS["min"]:g} pt, e.g. ' +
                     '; '.join(f'{s["size"]:.2f} pt {s["text"].strip()[:25]!r}' for s in small[:6]))
    floor_ok = min(fs.FS['tick'], fs.FS['note'])
    between = [x for x in runs if fs.FS['min'] - 0.05 <= x['size'] < floor_ok - 0.05]
    if between:
        warns.append(f'{sum(len(x["text"].strip()) for x in between)} characters between {fs.FS["min"]:g} and '
                     f'{floor_ok:g} pt (v6: ticks and notes {fs.FS["tick"]:g} pt, labels {fs.FS["axis"]:g} pt; '
                     f'{fs.FS["min"]:g} pt only for sub/superscripts)')
    scale = sorted(set(fs.FS.values()))
    text_runs = [x for x in runs if not ICON_FONT.match(x['font'])]
    off = collections.Counter(round(x['size'], 2) for x in text_runs
                              if min(abs(x['size'] - v) for v in scale) > 0.06)
    if off:
        warns.append('text at sizes off the v6 scale (' + ', '.join(f'{v:g}' for v in scale) + ' pt): ' +
                     ', '.join(f'{k:g} pt x{n}' for k, n in sorted(off.items())))
    big = [x for x in text_runs if x['size'] > fs.FS['letter'] + 0.55]
    if big:
        warns.append(f'{len(big)} text run(s) above {fs.FS["letter"] + 0.5:g} pt (RESTRAINT rule 1: no hero numbers), e.g. '
                     + '; '.join(f'{x["size"]:.1f} pt {x["text"].strip()[:20]!r}' for x in big[:4]))
    hits = text_collisions(text_runs)
    out.append(f'text collision audit (ink boxes, {len(text_runs)} runs): '
               + ('none' if not hits else f'{len(hits)} overlapping pair(s)'))
    for t1, t2, ox, oy in hits[:8]:
        fails.append(f'text collision: {t1!r} overlaps {t2!r} by {ox:.2f} x {oy:.2f} mm')
    icons = sorted({x['font'] for x in runs if ICON_FONT.match(x['font'])})
    if icons:
        warns.append('icon font(s) used: ' + ', '.join(icons) + ' (RESTRAINT rule 8: no icons)')
    tot = sum(hist.values())
    out.append('text size histogram (pt: characters): ' +
               ', '.join(f'{k:g}: {v}' for k, v in sorted(hist.items())) + f'  [total {tot}]')
    words = ' '.join(x['text'] for x in runs)
    alpha = sum(len(t) for t in re.findall(r'\S+', words) if re.search(r'[A-Za-z]', t))
    out.append(f'non-numeric text: about {alpha} characters (RESTRAINT: axis titles, ticks, one small legend, at most '
               f'two direct labels per panel)')
    run_fonts = collections.Counter(x['font'] for x in runs)
    for f in run_fonts:
        if f != '?' and not OK_FONT.match(f):
            fails.append(f'text set in {f}')

    # panel letters (top-level bold single lowercase letters, FS["letter"] = 8.5 pt) and panel titles (none in v6)
    # (detected from 7.5 pt up, so a letter at a stale size -- e.g. v5's 8 pt -- is found and FAILs below)
    letters = [x for x in runs if x['depth'] == 0 and re.fullmatch(r'[a-z]', x['text'].strip())
               and 'bold' in x['font'].lower() and x['size'] >= min(7.5, fs.FS['letter'] - 0.3)]
    lower = [x for x in runs if re.fullmatch(r'[a-z]', x['text'].strip()) and 'bold' in x['font'].lower()
             and x['size'] >= fs.FS['letter'] + 1.0]
    upper = [x for x in runs if x['depth'] == 0 and re.fullmatch(r'[A-Z]', x['text'].strip())
             and 'bold' in x['font'].lower() and x['size'] >= fs.FS['letter'] - 0.3]
    if letters:
        H = float(mb.height)
        rows = collections.defaultdict(list)
        cols = collections.defaultdict(list)
        desc = []
        for x in sorted(letters, key=lambda x: (round(H - x['y'], 1), x['x'])):
            bl, xm = (H - x['y']) * PT2MM, x['x'] * PT2MM
            desc.append(f'{x["text"].strip()} {x["size"]:.1f}pt x={xm:.2f} baseline={bl:.2f}mm')
            rows[round(bl, 1)].append(x['text'].strip())
            cols[round(xm, 1)].append(x['text'].strip())
            if abs(x['size'] - fs.FS['letter']) > 0.1:
                fails.append(f'panel letter {x["text"].strip()} is {x["size"]:.2f} pt (must be {fs.FS["letter"]:g})')
        out.append('panel letters: ' + '; '.join(desc))
        out.append('  shared baselines: ' + '; '.join(f'{k:.1f} mm: {"".join(v)}' for k, v in sorted(rows.items())))
        out.append('  shared x: ' + '; '.join(f'{k:.1f} mm: {"".join(v)}' for k, v in sorted(cols.items())))
        # RESTRAINT rule 2: a bold run on a letter's baseline, right of the letter, is a panel title
        ids = {id(x) for x in letters}
        for x in runs:
            if x['depth'] != 0 or id(x) in ids or 'bold' not in x['font'].lower() or not x['text'].strip():
                continue
            for lt in letters:
                if abs(x['y'] - lt['y']) * PT2MM < 0.3 and 0 < (x['x'] - lt['x']) * PT2MM < 60:
                    fails.append(f'panel title {x["text"].strip()[:30]!r} beside letter {lt["text"].strip()} '
                                 f'(RESTRAINT rule 2: no panel titles)')
                    break
    elif not a.panel:
        warns.append('no panel letters found (the composite draws them with \\Panel)')
    if a.panel and letters:
        warns.append('panel PDF contains bold single lowercase letters: letters belong to the composite, not the panel')
    if upper:
        warns.append('bold single capital(s) at letter size: ' + ', '.join(x['text'].strip() for x in upper[:6]) +
                     ' (v6 panel letters are lowercase)')
    if lower:
        warns.append(f'bold single lowercase letter(s) >= {fs.FS["letter"] + 1:g} pt: ' +
                     ', '.join(x['text'].strip() for x in lower[:6]) + ' (oversized panel letters?)')

    # colours per panel
    named = palette()
    vendor_hexes = {fs.VENDOR[v].lower(): v for v in fs.VENDOR_ORDER}
    semantic = {c.lower(): k for k, c in fs.SEMANTIC.items()}          # LEAK (= ACCENT), HONOUR, THIRD, EVENT
    all_unknown = collections.Counter()
    for pnl, cnt in sorted(wk.colors.items()):
        names = {}
        for hx, n in cnt.items():
            m = match(hx, named)
            if m is None:
                all_unknown[hx] += n
            names[m or hx] = names.get(m or hx, 0) + n
        sem = sorted({semantic[c] for hx in cnt for c in semantic if match(hx, {c: 1})})
        ven = sorted({vendor_hexes[c] for hx in cnt for c in vendor_hexes if match(hx, {c: 1})})
        out.append(f'colours [{pnl}]: ' + ', '.join(f'{k}' for k in sorted(names)))
        if sem and ven:
            msg = (f'panel {pnl}: semantic token(s) {", ".join(sem)} together with vendor hue(s) {", ".join(ven)} '
                   f'(vendor hexes only where vendors are the categories)')
            (warns if a.allow_red_with_vendors else fails).append(msg)
    for hx, n in all_unknown.items():
        if match(hx, {'#00ffff': 'cyan'}):
            fails.append('cyan lines present (\\FigGridtrue debug grid left on)')
        elif match(hx, {c: 'okabe' for c in getattr(fs, 'BANNED_HUES', ())}):
            fails.append(f'colour {hx} is an Okabe-Ito hue (banned: it collides with a vendor hue)')
        elif RETIRED_V5.get(hx) or match(hx, RETIRED_V5):
            warns.append(f'colour {hx} is a retired v5 colour: {RETIRED_V5.get(hx) or match(hx, RETIRED_V5)} '
                         f'({n} uses)')
        else:
            warns.append(f'colour {hx} is not in the v6 palette ({n} uses)')

    # render
    png = None
    if not a.no_render:
        stem = os.path.splitext(os.path.abspath(a.pdf))[0]
        prefix = a.png_prefix or f'{stem}_qa{a.dpi}'
        res = subprocess.run([fs.PDFPAGES2PNG, a.pdf, prefix, str(a.dpi), '1'], capture_output=True, text=True)
        if res.returncode != 0:
            fails.append('render failed: ' + res.stderr.strip()[:200])
        else:
            png = f'{prefix}-p01.png'

    print('\n'.join(out))
    for w in warns:
        print('WARN ' + w)
    for f in fails:
        print('FAIL ' + f)
    print('RESULT: ' + ('PASS (automatic checks)' if not fails else f'FAIL ({len(fails)} problem(s))'))
    if png:
        print(f'\nPNG ({a.dpi} dpi): {png}\n-> Read it with the Read tool, answer the checklist below, then delete it.')
    print(CHECKLIST)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
