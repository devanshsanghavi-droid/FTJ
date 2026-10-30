"""Steps 5-6 of the K-Dense 'scientific-visualization' skill (v1.4) for Figure 2 (v7; ../../DESIGN_V7.md section 11,
ported from ../../fig1/scripts/skill_qa_fig1.py: the v7 type floor and the muted-note exception, Fig 2's v7 ROLE
table), re-implemented here (the skill's own CLIs were read, not executed):

  1. inspect the delivered file: page size, fonts (embedded? TrueType/Type 42, never Type 3), raster content
  2. audit every colour actually drawn: WCAG 2.2 sRGB contrast against the white surface (4.5:1 text, 3:1 graphical
     objects needed to read the figure) and pairwise CIE L* separation of the colours that distinguish categories
     (the skill's grayscale screen: delta L* >= 10, a heuristic, not a standard)
  3. screen against the skill's dated Elsevier snapshot (Computers & Security is an Elsevier journal): widths 90 / 140 /
     190 mm, lettering about 7 pt, PDF for vector and text, RGB. v7: words >= 7 pt; 6 pt only for tick labels and for
     muted secondary text (fill SP_MUTED: region-level qualifiers, removal labels, bracket keys, the bus note)
  4. write the export manifest (dimensions, format, package versions, source references, provenance)

The skill is explicit that none of this certifies accessibility or journal compliance ('a zero failure count is not
acceptance'); the C&S Guide for Authors must still be checked before upload (6 pt is the sciplot Nature tick size that
v7 adopts; Elsevier asks for about 7 pt lettering).

Run:  python3 scripts/skill_qa_fig2.py fig2.pdf   (writes skill_qa_fig2.txt, fig2_export_manifest.json)
"""
import collections
import hashlib
import json
import os
import platform
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIG2 = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG2, '..', 'style')))
import figstyle as fs  # noqa: E402
import qa_check as qa  # noqa: E402  (PDF resource / content walkers)
from pypdf import PdfReader  # noqa: E402

PT2MM = 25.4 / 72
ELSEVIER_WIDTHS_MM = (90.0, 140.0, 190.0)
TEXT_MIN_PT = 6.0                   # v7 (DESIGN_V7 section 2, the sciplot clean-nature scale): tick labels and muted
                                    # secondary text 6 pt; words 7 pt; letters 8 pt (was 7 pt everywhere in v6)
WORD_MIN_PT = 7.0                   # non-numeric text: labels, names, axis title
NOTE_PT = fs.FS['note']             # ... except muted secondary text (fill SP_MUTED only) at 6 pt
ROLE = {                            # what each drawn colour is used for in Fig 2 (decides its contrast threshold)
    '#000000': ('the panel letters (composite); the Default arm glyph, a filled circle (c)', 4.5),
    fs.SP_FG: ('sciplot text colour: every 7 pt word and count', 4.5),
    fs.SP_AXIS: ('sciplot chrome: stage boxes and the spine (a); target and crawler boxes, the bus and its fork (b); '
                 'the page-load lines and the time axis (c)', 3.0),
    fs.SP_MUTED: ('sciplot muted text: region names (a, b), removal labels (a), runtime qualifiers, the crawler\'s '
                  "protocol, the bus note, 'Example request' and the bracket keys (b), 'next page', 'reload' and "
                  "'compared window' (c)", 4.5),
    fs.GREY_D: ('the Decline arm glyph, an open square (c)', 3.0),
    fs.NEUTRAL: ('NEUTRAL grey: context lines -- the phase frames and removal branches (a), the browser frame, the page '
                 'outline and the request brackets (b), the window brackets and the reload end tick (c); the GPC arm '
                 'glyph, a filled triangle (c)', 3.0),
    fs.SAND: ('SAND: the pixel-sandbox region outline (b)', 3.0),
    fs.LEAK: ('LEAK brick: the one captured request, a request sent before any choice, landing on its test code (b; '
              'brick as in Fig 1c)', 3.0),
    fs.EVENT: ('EVENT amber: the consent events -- the cookie-banner outline (b) and the banner, Decline-click and GPC '
               'ticks (c), each named in text', 3.0),
    fs.TINT['EVENT']: ('fill: amber tint behind the cookie-banner label (b; text on it 13.7:1)', None),
    fs.TINT['SAND']: ('ground: the pixel-sandbox region (b), = Fig 1a; text on it >= 4.1:1 (muted region name)', None),
    fs.TINT['PAGE']: ('ground: the page region (b), = Fig 1a, one step lighter than the sandbox ground', None),
    '#ffffff': ('surface', None),
}
ACCEPTED_LOW = {fs.NEUTRAL: 'v7 neutral, context only: frames, branches and brackets carry no data, every branch and '
                            'bracket is labelled in muted text, and the GPC triangle is told apart by shape and by the '
                            'arm name beside it',
                fs.EVENT: 'v7 fixes amber for the consent moment; every tick (one per arm) is named in text above it, '
                          'and the banner box is named in its own label'}
CATEGORY_PAIRS = [(fs.SP_AXIS, fs.EVENT, 'page-load lines (near-black) vs consent-event ticks (amber), c; also differ by '
                                         'orientation (horizontal lines, vertical ticks)'),
                  (fs.LEAK, fs.SP_AXIS, 'the captured request (brick, 1.0 pt, larger head) vs the crawler\'s taps (b)'),
                  (fs.SP_AXIS, fs.NEUTRAL, 'stages and the spine vs removal branches (a); load lines vs window brackets '
                                           'and the reload end tick (c)'),
                  (fs.TINT['PAGE'], fs.TINT['SAND'], 'page ground vs sandbox ground (b); also outlined NEUTRAL vs SAND'),
                  ('#000000', fs.NEUTRAL, 'Default vs GPC glyph (c); also differ by shape (circle, triangle)')]


def _lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb(hx):
    return tuple(int(hx[i:i + 2], 16) for i in (1, 3, 5))


def luminance(hx):
    r, g, b = (_lin(v) for v in rgb(hx))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def lstar(hx):
    y = luminance(hx)
    f = y ** (1 / 3) if y > (6 / 29) ** 3 else y / (3 * (6 / 29) ** 2) + 4 / 29
    return 116 * f - 16


def inspect_pdf(path):
    r = PdfReader(path)
    page = r.pages[0]
    w, h = float(page.mediabox.width) * PT2MM, float(page.mediabox.height) * PT2MM
    fonts, images, names, forms = {}, [], set(), []
    qa.walk_resources(page.get('/Resources'), set(), fonts, images, names, forms)
    wk = qa.Walker(r)
    wk.walk(page.get_contents(), page.get('/Resources'), [1, 0, 0, 1, 0, 0])
    sizes = collections.Counter(round(x['size'], 2) for x in wk.runs if x['text'].strip())
    words = collections.Counter(round(x['size'], 2) for x in wk.runs
                                if x['text'].strip() and not re.fullmatch(r'[\d\s,.+\u2212-]+', x['text'].strip())
                                and not (x.get('fill') == fs.SP_MUTED and abs(x['size'] - NOTE_PT) < 0.05))
    notes = collections.Counter(round(x['size'], 2) for x in wk.runs
                                if x['text'].strip() and x.get('fill') == fs.SP_MUTED and abs(x['size'] - NOTE_PT) < 0.05)
    colours = collections.Counter()
    for cnt in wk.colors.values():
        colours.update(cnt)
    return dict(path=path, pages=len(r.pages), width_mm=round(w, 2), height_mm=round(h, 2), fonts=fonts,
                images=len(images) + wk.inline_images, text_sizes_pt=dict(sorted(sizes.items())),
                word_sizes_pt=dict(sorted(words.items())), note_sizes_pt=dict(sorted(notes.items())),
                colours=sorted(colours), bytes=os.path.getsize(path))


def inspect_png(path, width_mm):
    try:
        from PIL import Image
    except ImportError:
        return None
    with Image.open(path) as im:
        px_w, px_h = im.size
        mode = im.mode
        opaque = True
        if 'A' in im.getbands():
            opaque = im.getchannel('A').getextrema()[0] == 255
    return dict(path=os.path.basename(path), px=[px_w, px_h], mode=mode, opaque=opaque,
                effective_ppi_at_final_width=round(px_w / (width_mm / 25.4)))


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        h.update(fh.read())
    return h.hexdigest()


def version(mod):
    try:
        return __import__(mod).__version__
    except Exception:
        return None


def main(pdfs):
    lines, fails = [], 0
    reports = [inspect_pdf(p) for p in pdfs]
    for rep in reports:
        lines.append(f"== {os.path.basename(rep['path'])}: {rep['pages']} page, {rep['width_mm']} x {rep['height_mm']} mm, "
                     f"{rep['bytes'] / 1024:.0f} KB, raster images: {rep['images']}")
        for name, f in sorted(rep['fonts'].items()):
            ok = f['embedded'] and f['subtype'] != '/Type3'
            fails += not ok
            lines.append(f"   font {name}: {f['subtype'].lstrip('/')} ({'CID TrueType, Type 42' if f['subtype'] == '/Type0' else f['subtype']}), "
                         f"{'embedded' if f['embedded'] else 'NOT EMBEDDED'}  [{'ok' if ok else 'FAIL'}]")
        small = {s: n for s, n in rep['text_sizes_pt'].items() if s < TEXT_MIN_PT - 0.05}
        fails += bool(small)
        lines.append(f"   text sizes (pt: runs): {rep['text_sizes_pt']}  -> smallest {min(rep['text_sizes_pt'])} pt "
                     f"[{'ok' if not small else f'FAIL: below {TEXT_MIN_PT:g} pt'}]")
        words = {s: n for s, n in rep['word_sizes_pt'].items() if s < WORD_MIN_PT - 0.05}
        fails += bool(words)
        wv = ('ok: words >= 7 pt; tick labels 6 pt; 6 pt words only as muted secondary text '
              f"(SP_MUTED runs: {rep['note_sizes_pt']})") if not words else 'FAIL: a word label below 7 pt'
        lines.append(f"   non-numeric text sizes (pt: runs): {rep['word_sizes_pt']}  [{wv}]")
        near = min(ELSEVIER_WIDTHS_MM, key=lambda x: abs(x - rep['width_mm']))
        okw = abs(near - rep['width_mm']) < 0.5
        fails += not okw
        lines.append(f"   Elsevier width class: {near:g} mm [{'ok' if okw else 'FAIL'}]; vector PDF "
                     f"[{'ok' if rep['images'] == 0 else 'contains raster'}]; colour space RGB (DeviceRGB operators)")
        lines.append('   colours drawn (WCAG contrast vs #ffffff; CIE L*):')
        for hx in rep['colours']:
            role, need = ROLE.get(hx, ('UNEXPECTED colour', 3.0))
            cr = contrast(hx, '#ffffff')
            if need is None:
                verdict = 'n/a (decorative/surface)'
            elif cr >= need:
                verdict = 'ok'
            elif hx in ACCEPTED_LOW:
                verdict = f'below {need}:1, accepted: {ACCEPTED_LOW[hx]}'
            else:
                verdict = f'FAIL (< {need}:1)'
                fails += 1
            lines.append(f'     {hx}  {cr:5.2f}:1  L*={lstar(hx):5.1f}  {role}  [{verdict}]')
    lines.append('== category separation without hue (skill grayscale screen, delta L* >= 10; heuristic):')
    for a, b, what in CATEGORY_PAIRS:
        d = abs(lstar(a) - lstar(b))
        lines.append(f'     {what}: {a} vs {b}  delta L* = {d:4.1f}  '
                     + ('separates in grayscale' if d >= 10 else 'does NOT separate in grayscale'))
    lines.append("   No vendor hues are drawn (identity is not this figure's point). Brick appears once, as b's one accent "
                 "(the captured request, a request sent before any choice, brick as in Fig 1c). The arms differ by "
                 "glyph shape (filled circle, open square, filled triangle) and are named at the lane; amber has one "
                 "meaning (the consent moment), named in text and in the caption; the two grounds repeat Fig 1a.")
    png = os.path.join(FIG2, '_v7_review-p01.png')
    pngrep = inspect_png(png, reports[0]['width_mm']) if os.path.exists(png) else None
    if pngrep:
        lines.append(f"== preview {pngrep['path']}: {pngrep['px'][0]} x {pngrep['px'][1]} px, {pngrep['mode']}, "
                     f"opaque={pngrep['opaque']}, {pngrep['effective_ppi_at_final_width']} ppi at 190 mm "
                     f"(a review render; the submission file is the vector PDF)")
    lines.append('RESULT: ' + ('PASS (automatic screen; not a compliance certificate)' if not fails else f'FAIL ({fails})'))
    open(os.path.join(FIG2, 'skill_qa_fig2.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))

    study = fs.STUDY
    srcs = {'stats.json': fs.STATS_JSON, 'figures/v7/derived_numbers.json': fs.DERIVED_JSON,
            'fig2/derived_numbers.json': os.path.join(FIG2, 'derived_numbers.json')}
    try:
        tect = subprocess.run([os.environ.get('TECTONIC', 'tectonic'), '--version'], capture_output=True,
                              text=True).stdout.strip()
    except Exception:
        tect = None
    manifest = dict(
        figure='Figure 2 (v7: figures/v7/DESIGN_V7.md; the sciplot clean theme and schematic rules; skill checks from v5)',
        destination=dict(journal='Computers & Security (Elsevier)', article_type='research article',
                         phase='initial submission', width='full (190 mm)',
                         publisher_rules='PENDING VERIFICATION against the live C&S Guide for Authors; screened only '
                                         "against the skill's dated Elsevier snapshot"),
        outputs=[dict(file=os.path.basename(r['path']), format='PDF (vector, Type 42 / CID TrueType Arial, opaque '
                      'white, RGB)', width_mm=r['width_mm'], height_mm=r['height_mm'], bytes=r['bytes'],
                      sha256=sha256(r['path'])) for r in reports] + ([dict(file=pngrep['path'], format='PNG review '
                      'render, 200 ppi', px=pngrep['px'])] if pngrep else []),
        sources={k: dict(path=os.path.relpath(v, study), sha256=sha256(v)) for k, v in srcs.items()},
        transformations=['figures/v7/scripts/derive_*.py -> figures/v7/derived_numbers.json (fig2a_funnel, '
                         'fig2b_worked_request)',
                         'fig2/scripts/derive_fig2.py -> fig2/derived_numbers.json (fig2a_not_drawn; fig2c_timeline: '
                         'the median moments drawn in c, from crawl/loads.csv and the raw Decline records)',
                         'fig2/scripts/make_fig2_panels.py -> build/fig2_layout.tex (cells and coordinates, checked '
                         'against measured Arial widths) and build/fig2_numbers.tex (every printed number and string, registered in '
                         'panels/fig2_numbers.csv; the worked request redacted by fig2/scripts/redact.py)',
                         'fig2/tex/*.tex (TikZ, drawing only: a and b schematics, c timelines under one time axis) -> '
                         'panels/*.pdf -> fig2.tex composite',
                         'fig2/scripts/trace_fig2.py checks every printed number against the current sources'],
        uncertainty='none shown: a methods figure with counts and one worked example (the agreement estimates with '
                    'Wilson CIs moved with v4 panel d to Fig 6d).',
        missing_data='a: domains removed between stages are drawn as grey side branches with their counts (including '
                     'the flagged domains never drawn for checking); the '
                     'creator-linked stores are a separate stratum outside the Tranco frame, not drawn and not counted '
                     'in the analysed sample (caption).',
        software=dict(python=platform.python_version(), matplotlib=version('matplotlib'), numpy=version('numpy'),
                      pypdf=version('pypdf'), pandas=version('pandas'), tectonic=tect),
        alt_text='alt_text_fig2.txt',
        note='No automated report here certifies accessibility or journal compliance (skill guardrail).',
    )
    json.dump(manifest, open(os.path.join(FIG2, 'fig2_export_manifest.json'), 'w'), indent=1)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main([os.path.abspath(p) for p in sys.argv[1:]] or [os.path.join(FIG2, 'fig2.pdf')])
