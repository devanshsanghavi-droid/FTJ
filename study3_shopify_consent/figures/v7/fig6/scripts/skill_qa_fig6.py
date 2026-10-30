"""Steps 5-6 of the K-Dense 'scientific-visualization' skill (v1.4) for Figure 6 (v7; ../../DESIGN_V7.md), ported from the
v7 worked example ../../fig1/scripts/skill_qa_fig1.py (words >= 7 pt; 6 pt tick labels; 6 pt words only as SP_MUTED
secondary text; accepted low-contrast tokens with their reasons) with Figure 6's ROLE table (the skill's own CLIs were
read, not executed). Any colour outside the ROLE table FAILs (stricter than fig1's 3:1 fall-through):

  1. inspect the delivered file: page size, fonts (embedded? TrueType/Type 42, never Type 3), raster content
  2. audit every colour actually drawn: WCAG 2.2 sRGB contrast against the white surface (4.5:1 text, 3:1 graphical
     objects needed to read the figure) and pairwise CIE L* separation of the colours that distinguish categories
     (the skill's grayscale screen: delta L* >= 10, a heuristic, not a standard)
  3. screen against the skill's dated Elsevier snapshot (Computers & Security is an Elsevier journal): widths 90 / 140 /
     190 mm, lettering about 7 pt (6 pt floor only for sub/superscripts), PDF for vector and text, RGB
  4. write the export manifest (dimensions, format, package versions, source references, provenance)

The skill is explicit that none of this certifies accessibility or journal compliance ('a zero failure count is not
acceptance'); the C&S Guide for Authors must still be checked before upload.

Run:  python3 scripts/skill_qa_fig6.py fig6.pdf   (writes skill_qa_fig6.txt, fig6_export_manifest.json)
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
FIG6 = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG6, '..', 'style')))
import figstyle as fs  # noqa: E402
import qa_check as qa  # noqa: E402  (PDF resource / content walkers)
from pypdf import PdfReader  # noqa: E402

PT2MM = 25.4 / 72
ELSEVIER_WIDTHS_MM = (90.0, 140.0, 190.0)
TEXT_MIN_PT = 6.0                   # v7 (DESIGN_V7 section 2, the sciplot clean-nature scale): tick labels and muted
                                    # secondary text 6 pt; words 7 pt; letters 8 pt (v6: 6.5 pt ticks)
WORD_MIN_PT = 7.0                   # non-tick text: axis titles, row labels, key, schematic labels
NOTE_PT = fs.FS['note']             # ... except muted secondary text (fill SP_MUTED only) at 6 pt: the runtime tags
                                    # 'strict' / 'lax' and the link's query-string placeholder (a)
MID = fs.ORIGIN['open_pixel']['facecolor']                  # the registry's mid grey #6e6e6e (Fig. S2a's group dots)
ROLE = {                            # what each drawn colour is used for in Fig 6 (decides its contrast threshold)
    '#000000': ('the panel letters (composite)', 4.5),
    fs.SP_FG: ("sciplot text colour: every word label and axis title, the drawing's vendor names (a)", 4.5),
    fs.SP_AXIS: ("sciplot chrome: the bottom axes, ticks and tick labels (a's plot, b, c, d) and d's break mark; the "
                 "drawing's box outlines and connectors (a)", 3.0),
    fs.SP_MUTED: ("sciplot muted text: the drawing's region names, the 'Ad vendors' column name, runtime tags and "
                  "query-string placeholder (a); the key and the group names (a's plot, d)", 4.5),
    fs.SAND: ('SAND: the pixel-sandbox region outline (a)', 3.0),
    fs.LEAK: ('LEAK brick: the code leaving from a Shopify sandbox (consent lost) -- the two leak arrows (a), the '
              '"From a sandbox" circles and key mark (a), the circle and its CI (b)', 3.0),
    fs.NEUTRAL: ('NEUTRAL grey: context -- the browser frame, the page-region outline and the other-routes arrow (a); '
                 'the "Any route" squares and key mark (a), the squares and their CIs (b)', 3.0),
    MID: ('mid grey: the vendor-group and all-vendor circles and their CIs (c), the agreement circles and their CIs '
          '(d), as Fig. S2a\'s groups', 3.0),
    fs.LIGHT: ("decorative: the light line joining a load's two counts (a)", None),
    fs.TINT['LEAK']: ("ground: the all-vendor share's 95% CI carried up through c's rows (the key-area band of Figs "
                      'S2, S3 and S5; no text on it)', None),
    fs.TINT['PAGE']: ("ground: the page region (a), as Fig. 1a's page region and Fig. 1b's page lane; text on it "
                      '>= 4.5:1', None),
    fs.TINT['SAND']: ("ground: the pixel-sandbox region (a), as Fig. 1a's sandbox region and Fig. 1b's sandbox lane; "
                      'text on it >= 4.1:1 (muted region name), 14:1 (labels)', None),
    '#ffffff': ('surface; the white boxes of the drawing (a)', None),
}
ACCEPTED_LOW = {fs.NEUTRAL: 'DESIGN_V7 section 3.2 neutral, context only: the "Any route" series is double-coded by '
                            'shape (square vs the brick circle) and named in the key (a) and on its rows (b); the '
                            'other-routes arrow is named in text ("other routes"); the frame and region outlines are '
                            'containers, named at their top-left; the panels\' point is carried by the brick marks '
                            '(4.4:1)'}
CATEGORY_PAIRS = [(fs.LEAK, fs.NEUTRAL, 'from a sandbox (brick) vs any route (grey), a and b; also told apart by '
                                        'shape (circle vs square) and, in the drawing, by weight (1.0 vs 0.8 pt)'),
                  (fs.TINT['PAGE'], fs.TINT['SAND'], "the drawing's two grounds (page vs pixel sandboxes); also told "
                                                     'apart by their outlines (NEUTRAL vs SAND) and their names')]


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
                images=len(images) + wk.inline_images, text_sizes_pt=dict(sorted(sizes.items())), word_sizes_pt=dict(sorted(words.items())),
                note_sizes_pt=dict(sorted(notes.items())), colours=sorted(colours), bytes=os.path.getsize(path))


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
            if hx not in ROLE:
                verdict = 'FAIL (a colour Fig 6 does not use)'
                fails += 1
            elif need is None:
                verdict = ('n/a (identity hue below 3:1; the vendor is named on its row)' if role.startswith('vendor')
                           else 'n/a (decorative/surface)')
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
    lines.append("   No vendor hue and no EVENT amber in Fig 6 (the vendor is named on its row in c; the creator link is not "
                 "a consent moment). Brick and grey each have one meaning in a and b, named in the caption; c and d "
                 "are mid-grey dots (Fig. S2a's), c's all-vendor CI a pale brick band (the key-area band of Figs S2, "
                 "S3, S5); the grounds are pre-mixed tints (sciplot), never alpha, each repeating its meaning "
                 "elsewhere in the set (a's two as Fig. 1's regions).")
    png = os.path.join(FIG6, '_v7_review-p01.png')         # the one review PNG (200 dpi; disk)
    pngrep = inspect_png(png, reports[0]['width_mm']) if os.path.exists(png) else None
    if pngrep:
        lines.append(f"== preview {pngrep['path']}: {pngrep['px'][0]} x {pngrep['px'][1]} px, {pngrep['mode']}, "
                     f"opaque={pngrep['opaque']}, {pngrep['effective_ppi_at_final_width']} ppi at 190 mm "
                     f"(a review render; the submission file is the vector PDF)")
    lines.append('   v7 type check: words 7 pt; tick labels and muted secondary text 6 pt; letters 8 pt (DESIGN_V7 '
                 'section 2). Elsevier asks for about 7 pt lettering: 6 pt is the sciplot Nature tick size the v7 spec '
                 'adopts; confirm against the C&S Guide for Authors before submission.')
    lines.append('RESULT: ' + ('PASS (automatic screen; not a compliance certificate)' if not fails else f'FAIL ({fails})'))
    open(os.path.join(FIG6, 'skill_qa_fig6.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))

    study = fs.STUDY
    srcs = {'stats.json': fs.STATS_JSON, 'fig6/derived_numbers.json': os.path.join(FIG6, 'derived_numbers.json')}
    try:
        tect = subprocess.run([os.environ.get('TECTONIC', 'tectonic'), '--version'], capture_output=True,
                              text=True).stdout.strip()
    except Exception:
        tect = None
    manifest = dict(
        figure='Figure 6 (v7: DESIGN_V7.md, the sciplot clean theme with the FigGenie and nature-figure grafts; K-Dense skill v1.4 screen)',
        destination=dict(journal='Computers & Security (Elsevier)', article_type='research article',
                         phase='initial submission', width='full (190 mm)',
                         publisher_rules='PENDING VERIFICATION against the live C&S Guide for Authors; screened only '
                                         "against the skill's dated Elsevier snapshot"),
        outputs=[dict(file=os.path.basename(r['path']), format='PDF (vector, Type 42 / CID TrueType Arial, opaque '
                      'white, RGB)', width_mm=r['width_mm'], height_mm=r['height_mm'], bytes=r['bytes'],
                      sha256=sha256(r['path'])) for r in reports] + ([dict(file=pngrep['path'], format='PNG review '
                      'render, 200 ppi', px=pngrep['px'])] if pngrep else []),
        sources={k: dict(path=os.path.relpath(v, study), sha256=sha256(v)) for k, v in srcs.items()},
        transformations=['analysis/analyze.py -> analysis/outputs/stats.json (Wilson CIs; Korn-Graubard CIs clustered '
                         'by store; store-bootstrap CIs; Cohen kappa with its CI; screenshot-audit agreement)',
                         'fig6/scripts/derive_fig6.py -> fig6/derived_numbers.json (Store C per-load grid and vendor '
                         'matrix from analysis/outputs/fig6b_store_c.csv; Wilson CIs of the between-load agreement)',
                         'fig6/scripts/make_fig6_panels.py (drawing only; no number is printed in the panels besides '
                         'tick labels; every drawn value registered in panels/fig6_numbers.csv and checked by '
                         'scripts/trace_fig6.py); fig6a_path.tex (TikZ line drawing of a, no numbers); fig6.tex '
                         '(composite, tectonic)',
                         'fig6/scripts/make_caption_fig6.py (the caption carries every count and share; registry '
                         'caption_fig6_numbers.csv)'],
        uncertainty='b: Wilson 95% CIs (stores are the unit); c: Korn-Graubard 95% CIs clustered by store per vendor '
                    'group, all vendors (the summary row): 95% CI from resampling stores (percentile bootstrap), in the '
                    'caption; d: Wilson 95% CIs of the agreement share; Cohen kappa 95% CI in the caption. a: one '
                    'store, exact counts (no interval).',
        missing_data='c: vendor groups with fewer than design.min_stores_row stores are omitted (none at present). '
                     'd: the axis is truncated at 85% (ticks 85-100; stated in the caption); the screenshot-audit labels have not yet been '
                     'checked by an independent human rater (stated in the caption).',
        software=dict(python=platform.python_version(), matplotlib=version('matplotlib'), numpy=version('numpy'),
                      pypdf=version('pypdf'), pandas=version('pandas'), tectonic=tect),
        alt_text='alt_text_fig6.txt',
        note='No automated report here certifies accessibility or journal compliance (skill guardrail).',
    )
    json.dump(manifest, open(os.path.join(FIG6, 'fig6_export_manifest.json'), 'w'), indent=1)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main([os.path.abspath(p) for p in sys.argv[1:]] or [os.path.join(FIG6, 'fig6.pdf')])
