"""Steps 5-6 of the K-Dense 'scientific-visualization' skill (v1.4) for Figure 4 (v7; ../../DESIGN_V7.md), copied
from the v7 worked example ../../fig1/scripts/skill_qa_fig1.py with Figure 4's ROLE table (the skill's own CLIs were
read, not executed):

  1. inspect the delivered file: page size, fonts (embedded? TrueType/Type 42, never Type 3), raster content
  2. audit every colour actually drawn: WCAG 2.2 sRGB contrast against the white surface (4.5:1 text, 3:1 graphical
     objects needed to read the figure) and pairwise CIE L* separation of the colours that distinguish categories
     (the skill's grayscale screen: delta L* >= 10, a heuristic, not a standard)
  3. screen against the skill's dated Elsevier snapshot (Computers & Security is an Elsevier journal): widths 90 / 140 /
     190 mm, lettering about 7 pt (6 pt floor only for sub/superscripts), PDF for vector and text, RGB
  4. write the export manifest (dimensions, format, package versions, source references, provenance)

The skill is explicit that none of this certifies accessibility or journal compliance ('a zero failure count is not
acceptance'); the C&S Guide for Authors must still be checked before upload.

Run:  python3 scripts/skill_qa_fig4.py fig4.pdf   (writes skill_qa_fig4.txt, fig4_export_manifest.json)
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
FIG4 = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG4, '..', 'style')))
import figstyle as fs  # noqa: E402
import qa_check as qa  # noqa: E402  (PDF resource / content walkers)
from pypdf import PdfReader  # noqa: E402

PT2MM = 25.4 / 72
ELSEVIER_WIDTHS_MM = (90.0, 140.0, 190.0)
TEXT_MIN_PT = 6.0                   # v7 (DESIGN_V7 section 2, the sciplot clean-nature scale): tick labels, muted notes
                                    # 6 pt; words 7 pt; letters 8 pt (was 6.5 pt ticks in v6)
WORD_MIN_PT = 7.0                   # non-tick text: axis titles, row labels, direct labels, schematic labels
NOTE_PT = fs.FS['note']             # ... except muted secondary text (fill SP_MUTED only) at 6 pt (none drawn in
                                    # Fig 4; the rule is kept as in Fig 1)
ROLE = {                            # what each drawn colour is used for in Fig 4 (decides its contrast threshold)
    '#000000': ('the panel letters (composite)', 4.5),
    fs.SP_FG: ('sciplot text colour: row names, axis titles, the two direct labels (b); the pooled-difference '
               'diamonds and their CIs (b right)', 4.5),
    fs.SP_AXIS: ('sciplot chrome: the bottom spines, ticks and tick labels (a, b)', 4.5),
    fs.SP_MUTED: ("sciplot muted text: the 7 pt headers 'Region default' and 'Pooled over defaults' over b's row names",
                  4.5),
    fs.LEAK: ('LEAK brick, consent lost: the store cells whose declared-blocked vendor fired (a), the open and filled '
              'circles and their CIs (a), the blocklist circles and their CIs (b left)', 3.0),
    fs.NEUTRAL: ('NEUTRAL grey, context: the zero rule of b right (as Fig. 3a right); the comparison as context: '
                 'the no-declaration squares and their CIs (b left; not '
                 "slate, which means 'denied until consent' in Fig. 3)", 3.0),
    fs.LIGHT: ("LIGHT grey, context: the store cells whose declared-blocked vendor did not fire (a)", 3.0),
    fs.TINT['LEAK']: ("ground: b-left's key area, the gap between a pair's two shares (marks and CIs drawn on it)",
                      None),
    '#ffffff': ('surface; the open-circle and open-diamond fill; the white gaps between store cells', None),
}
ACCEPTED_LOW = {fs.LIGHT: "sciplot: grey for context, colour for signal; the light cells are the stores on which the "
                          "vendor did not fire, read as the remainder of a bar whose brick part (4.4:1) carries a's "
                          "point; each cell is bounded by white gaps and the bar's extent is the labelled 0-100 axis",
                fs.NEUTRAL: "sciplot: grey for context, colour for signal (DESIGN_V7 section 3.2: NEUTRAL = context "
                            "series); the comparison is the baseline against which the brick blocklist rows are read, "
                            "double-coded by shape (square) and row (below the brick circle), named by a direct label, "
                            "and it separates from brick in grayscale (delta L* 15); Fig. 3 draws its grey groups in "
                            "the same token; the zero rule of b right is a reference line, not data, drawn as "
                            "Fig. 3a right's (solid NEUTRAL 0.6 pt) and labelled by its 0 tick"}
CATEGORY_PAIRS = [(fs.LEAK, fs.NEUTRAL, 'blocklist (brick circle) vs no declaration (grey square), b left'),
                  (fs.LEAK, fs.LIGHT, 'a: store cells, the declared-blocked vendor fired (brick) vs not (light grey)')]


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
                note_sizes_pt=dict(sorted(notes.items())),
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
    lines.append("   Blocklist vs no declaration is brick vs grey (they separate in grayscale) and is also double-coded "
                 "by shape (circle vs square) and by row (blocklist above, within each region default) and named by "
                 "two direct labels; one sample alone vs the combined sample is open vs filled (circles in a, diamonds "
                 "in b right), never colour alone. Slate is not drawn (in Fig. 3 it means 'denied until consent'). No "
                 "vendor hues are drawn. The one fill is a pre-mixed tint (TINT LEAK, never alpha) repeating brick's "
                 "meaning: the key area of b left.")
    png = os.path.join(FIG4, '_v7_review-p01.png')        # the one review PNG (200 dpi; disk)
    pngrep = inspect_png(png, reports[0]['width_mm']) if os.path.exists(png) else None
    if pngrep:
        lines.append(f"== preview {pngrep['path']}: {pngrep['px'][0]} x {pngrep['px'][1]} px, {pngrep['mode']}, "
                     f"opaque={pngrep['opaque']}, {pngrep['effective_ppi_at_final_width']} ppi at 190 mm "
                     f"(a review render; the submission file is the vector PDF)")
    lines.append('   v7 type check: words 7 pt; tick labels 6 pt; letters 8 pt '
                 '(DESIGN_V7 section 2). Elsevier asks for about 7 pt lettering: 6 pt is the sciplot Nature tick size '
                 'the v7 spec adopts; confirm against the C&S Guide for Authors before submission.')
    lines.append('RESULT: ' + ('PASS (automatic screen; not a compliance certificate)' if not fails else f'FAIL ({fails})'))
    open(os.path.join(FIG4, 'skill_qa_fig4.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))

    study = fs.STUDY
    srcs = {'stats.json': fs.STATS_JSON, 'fig4/derived_numbers.json': os.path.join(FIG4, 'derived_numbers.json')}
    try:
        tect = subprocess.run([os.environ.get('TECTONIC', 'tectonic'), '--version'], capture_output=True,
                              text=True).stdout.strip()
    except Exception:
        tect = None
    manifest = dict(
        figure='Figure 4 (v7: v6 content in the sciplot clean theme, mmd-ahd/scientific-figure-skill, with the '
               'nature-figure grafts of DESIGN_V7.md; K-Dense skill v1.4 screen)',
        destination=dict(journal='Computers & Security (Elsevier)', article_type='research article',
                         phase='initial submission', width='full (190 mm)',
                         publisher_rules='PENDING VERIFICATION against the live C&S Guide for Authors; screened only '
                                         "against the skill's dated Elsevier snapshot"),
        outputs=[dict(file=os.path.basename(r['path']), format='PDF (vector, Type 42 / CID TrueType Arial, opaque '
                      'white, RGB)', width_mm=r['width_mm'], height_mm=r['height_mm'], bytes=r['bytes'],
                      sha256=sha256(r['path'])) for r in reports] + ([dict(file=pngrep['path'], format='PNG review '
                      'render, 200 ppi', px=pngrep['px'])] if pngrep else []),
        sources={k: dict(path=os.path.relpath(v, study), sha256=sha256(v)) for k, v in srcs.items()},
        transformations=['analysis/analyze.py -> analysis/outputs/stats.json (round4.blocklist: Wilson CIs; '
                         'Mantel-Haenszel risk difference with Sato variance)',
                         'fig4/scripts/derive_fig4.py -> fig4/derived_numbers.json (Tranco rank ranges of the two '
                         'samples; also the entry and re-check records read by Fig 1 and the graphical abstract)',
                         'fig4/scripts/make_fig4_panels.py (drawing only; every drawn value -- cell counts k and n, '
                         'dots, CI ends, diamonds -- registered as a mark in fig4_numbers.csv and checked by '
                         'scripts/trace_fig4.py; the panels print only axis ticks)',
                         'fig4/scripts/make_caption_fig4.py (the caption carries every value; registry '
                         'caption_fig4_numbers.csv)',
                         'fig4.tex (composite, tectonic)'],
        uncertainty='a, b left: Wilson 95% CIs of a share (stores are the unit); b right: Mantel-Haenszel difference '
                    'pooled over the two region defaults, Sato variance. Every CI is an uncapped line in the colour '
                    'of its mark. No bootstrap (no seed needed).',
        missing_data="Stores whose CMP wrote 'marketing: yes' are excluded from both panels by design (caption); the "
                     'reference group is main-sample banner stores without a readable declaration. Nothing lies '
                     'outside an axis.',
        software=dict(python=platform.python_version(), matplotlib=version('matplotlib'), numpy=version('numpy'),
                      pypdf=version('pypdf'), pandas=version('pandas'), tectonic=tect),
        alt_text='alt_text_fig4.txt',
        note='No automated report here certifies accessibility or journal compliance (skill guardrail).',
    )
    json.dump(manifest, open(os.path.join(FIG4, 'fig4_export_manifest.json'), 'w'), indent=1)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main([os.path.abspath(p) for p in sys.argv[1:]] or [os.path.join(FIG4, 'fig4.pdf')])
