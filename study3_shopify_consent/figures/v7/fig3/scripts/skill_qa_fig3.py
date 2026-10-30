"""Steps 5-6 of the K-Dense 'scientific-visualization' skill (v1.4) for Figure 3 (v7; ../../DESIGN_V7.md), re-based on
the v7 worked example fig1/scripts/skill_qa_fig1.py: the v7 type scale (words 7 pt; tick labels 6 pt; 6 pt words only
as SP_MUTED secondary text), and Figure 3's v7 ROLE table (brick, slate, the grey of small groups, the sciplot text,
chrome and muted greys, the one pale brick tint); any colour outside the table fails (the skill's own CLIs were read,
not executed):

  1. inspect the delivered file: page size, fonts (embedded? TrueType/Type 42, never Type 3), raster content
  2. audit every colour actually drawn: WCAG 2.2 sRGB contrast against the white surface (4.5:1 text, 3:1 graphical
     objects needed to read the figure) and pairwise CIE L* separation of the colours that distinguish categories
     (the skill's grayscale screen: delta L* >= 10, a heuristic, not a standard)
  3. screen against the skill's dated Elsevier snapshot (Computers & Security is an Elsevier journal): widths 90 / 140 /
     190 mm, lettering about 7 pt (6 pt floor only for sub/superscripts), PDF for vector and text, RGB
  4. write the export manifest (dimensions, format, package versions, source references, provenance)

The skill is explicit that none of this certifies accessibility or journal compliance ('a zero failure count is not
acceptance'); the C&S Guide for Authors must still be checked before upload.

Run:  python3 scripts/skill_qa_fig3.py fig3.pdf   (writes skill_qa_fig3.txt, fig3_export_manifest.json)
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
FIG3 = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG3, '..', 'style')))
import figstyle as fs  # noqa: E402
import qa_check as qa  # noqa: E402  (PDF resource / content walkers)
from pypdf import PdfReader  # noqa: E402

PT2MM = 25.4 / 72
ELSEVIER_WIDTHS_MM = (90.0, 140.0, 190.0)
TEXT_MIN_PT = 6.0                   # v7 (DESIGN_V7 section 2, the sciplot clean-nature scale): tick labels 6 pt; words
                                    # 7 pt; letters 8 pt (was 6.5 pt ticks in v6)
WORD_MIN_PT = 7.0                   # non-tick text: axis titles, row labels, direct labels, schematic labels
NOTE_PT = fs.FS['note']             # ... except muted secondary text (fill SP_MUTED only) at 6 pt: in Fig 3 the one
                                    # note 'Grey: fewer than 10 stores' (a left); its other muted texts are 7 pt
ROLE = {                            # what each drawn colour is used for in Fig 3 (decides its contrast threshold)
    '#000000': ('the panel letters (composite)', 4.5),
    fs.SP_FG: ('sciplot text colour: every word label and axis title; the two difference diamonds (filled; open = '
               "white with an SP_FG edge), their CIs and their direct labels 'Within product' and 'Crude' (a right)",
               4.5),
    fs.SP_AXIS: ("sciplot chrome: the open bottom axes, ticks and tick labels; b's left spine", 3.0),
    fs.SP_MUTED: ("sciplot muted text: the product rows' group name 'Consent product', the name of a row whose groups "
                  "are all small and the 6 pt note 'Grey: fewer than 10 stores' (a left); the categories' group name "
                  "'Declared purpose' (b)", 4.5),
    fs.LEAK: ("LEAK brick, 'allowed until choice': circles and their CIs (a left, b)", 3.0),
    fs.HONOUR: ("HONOUR slate, 'denied until consent': squares and their CIs (a left, b)", 3.0),
    fs.NEUTRAL: ('NEUTRAL grey: a group of fewer than design.min_stores_row stores, its mark and CI (a left); the '
                 'zero rule (a right) and the bracket grouping the product rows (a), context lines', 3.0),
    fs.TINT['LEAK']: ("ground: the key area, the excess under 'allowed until choice' -- the band between a row's two "
                      "marks (a left, b); marks drawn on it", None),
    '#ffffff': ('surface; the open diamond (a right)', None),
}
ACCEPTED_LOW = {fs.NEUTRAL: "sciplot: grey for context, colour for signal; grey marks a small group (fewer than "
                            "design.min_stores_row stores), whose estimate is imprecise; its shape (circle / square) "
                            "still names its default, a note in the plot and the caption say what grey means, and "
                            "the caption lists the grey groups. As the zero rule and the product bracket it is a "
                            "context line (DESIGN_V7 section 3.2: NEUTRAL = context lines; = Fig 4b right's zero rule "
                            "before 2026-10-19 22:16), the zero also being the labelled 0 tick"}
CATEGORY_PAIRS = [(fs.LEAK, fs.HONOUR, "'allowed until choice' (brick circle) vs 'denied until consent' (slate square), "
                                       'a left and b'),
                  (fs.LEAK, fs.NEUTRAL, "an 'allowed' group vs a small group (grey), a left"),
                  (fs.HONOUR, fs.NEUTRAL, "a 'denied' group vs a small group (grey), a left")]


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
    colours = collections.Counter()
    for cnt in wk.colors.values():
        colours.update(cnt)
    return dict(path=path, pages=len(r.pages), width_mm=round(w, 2), height_mm=round(h, 2), fonts=fonts,
                images=len(images) + wk.inline_images, text_sizes_pt=dict(sorted(sizes.items())), word_sizes_pt=dict(sorted(words.items())),
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
        wv = ('ok: words >= 7 pt; tick labels 6 pt; 6 pt words only as muted secondary text (DESIGN_V7 section 2)'
              if not words else 'FAIL: a word label below 7 pt')
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
            if hx not in ROLE:                      # r2: a colour Fig 3 does not use fails whatever its contrast
                verdict = 'FAIL (not a Fig 3 colour)'
                fails += 1
            elif need is None:
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
    lines.append("   Brick and slate have nearly equal lightness, so the two region defaults are double-coded by shape "
                 "(circle vs square; DESIGN_V7 section 5) and by position (in a left 'allowed' sits above the row line "
                 "and 'denied' below it; in b 'allowed' is left of 'denied'), and named by direct labels in a; a grey (small) "
                 "group keeps its shape. The crude vs pooled difference (a right) is open vs filled, each on its own "
                 "row with its own direct label. The one tint (pale brick, pre-mixed, never alpha) has one meaning, the excess under 'allowed'. "
                 "No vendor hues are drawn (per-vendor detail is in Fig. S6).")
    lines.append('   v7 type check: words 7 pt; tick labels 6 pt; letters 8 pt (DESIGN_V7 section 2). Elsevier asks for '
                 'about 7 pt lettering: 6 pt is the sciplot Nature tick size the v7 spec adopts; confirm against the '
                 'C&S Guide for Authors before submission.')
    png = os.path.join(FIG3, '_v7_review-p01.png')         # the one review PNG (200 dpi; disk)
    pngrep = inspect_png(png, reports[0]['width_mm']) if os.path.exists(png) else None
    if pngrep:
        lines.append(f"== preview {pngrep['path']}: {pngrep['px'][0]} x {pngrep['px'][1]} px, {pngrep['mode']}, "
                     f"opaque={pngrep['opaque']}, {pngrep['effective_ppi_at_final_width']} ppi at {reports[0]['width_mm']:g} mm "
                     f"(a review render; the submission file is the vector PDF)")
    lines.append('RESULT: ' + ('PASS (automatic screen; not a compliance certificate)' if not fails else f'FAIL ({fails})'))
    open(os.path.join(FIG3, 'skill_qa_fig3.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))

    study = fs.STUDY
    srcs = {'stats.json': fs.STATS_JSON, 'fig3/derived_numbers.json': os.path.join(FIG3, 'derived_numbers.json')}
    try:
        tect = subprocess.run([os.environ.get('TECTONIC', 'tectonic'), '--version'], capture_output=True,
                              text=True).stdout.strip()
    except Exception:
        tect = None
    manifest = dict(
        figure='Figure 3 (v7: DESIGN_V7.md, the sciplot clean theme with the nature-figure key area; K-Dense skill v1.4 screen)',
        destination=dict(journal='Computers & Security (Elsevier)', article_type='research article',
                         phase='initial submission', width='full (190 mm)',
                         publisher_rules='PENDING VERIFICATION against the live C&S Guide for Authors; screened only '
                                         "against the skill's dated Elsevier snapshot"),
        outputs=[dict(file=os.path.basename(r['path']), format='PDF (vector, Type 42 / CID TrueType Arial, opaque '
                      'white, RGB)', width_mm=r['width_mm'], height_mm=r['height_mm'], bytes=r['bytes'],
                      sha256=sha256(r['path'])) for r in reports] + ([dict(file=pngrep['path'], format='PNG review '
                      'render, 200 ppi', px=pngrep['px'])] if pngrep else []),
        sources={k: dict(path=os.path.relpath(v, study), sha256=sha256(v)) for k, v in srcs.items()},
        transformations=['analysis/analyze.py -> analysis/outputs/stats.json (Wilson CIs; Mantel-Haenszel risk '
                         'difference with Sato variance; the crude Newcombe difference)',
                         'fig3/scripts/derive_fig3.py -> fig3/derived_numbers.json (per-product strata with each '
                         "share's Wilson CI, MH weights and Newcombe differences; it also keeps the timing blocks of "
                         'the removed panel c for provenance)',
                         'fig3/scripts/make_fig3_panels.py (drawing only, fs.v7_context(), each panel linted by '
                         'sp_lint.lint_fig; the panels print the axis ticks and the registered threshold of a\'s grey note; '
                         'every drawn value -- marks, CI ends, '
                         'band ends, the grey threshold -- registered as a mark in panels/fig3_numbers.csv and checked '
                         'by scripts/trace_fig3.py)',
                         'fig3/scripts/make_caption_fig3.py (the caption carries every count, the undrawn products\' too; registry '
                         'caption_fig3_numbers.csv)', 'fig3.tex (composite, tectonic)'],
        uncertainty='a left, b: Wilson 95% CIs of a share (stores are the unit), drawn in the colour of their mark; '
                    'a right: Newcombe 95% CI of the crude difference and the Mantel-Haenszel difference pooled over '
                    'the consent products with Sato variance (strata = consent products). No bootstrap (no seed '
                    'needed).',
        missing_data='7 banner stores without a readable region default are excluded (caption). Consent products with '
                     'fewer than 5 stores under either default are not drawn in a left; they enter the pooled '
                     'difference (a right) and their counts are listed in the caption. Groups of fewer than '
                     'design.min_stores_row stores are drawn grey and listed in the caption. Nothing lies outside an '
                     'axis.',
        software=dict(python=platform.python_version(), matplotlib=version('matplotlib'), numpy=version('numpy'),
                      pypdf=version('pypdf'), pandas=version('pandas'), tectonic=tect),
        alt_text='alt_text_fig3.txt',
        note='No automated report here certifies accessibility or journal compliance (skill guardrail).',
    )
    json.dump(manifest, open(os.path.join(FIG3, 'fig3_export_manifest.json'), 'w'), indent=1)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main([os.path.abspath(p) for p in sys.argv[1:]] or [os.path.join(FIG3, 'fig3.pdf')])
