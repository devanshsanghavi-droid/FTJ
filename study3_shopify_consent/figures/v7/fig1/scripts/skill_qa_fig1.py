"""Steps 5-6 of the K-Dense 'scientific-visualization' skill (v1.4) for Figure 1 (v7; ../../DESIGN_V7.md),
copied from the worked example fig3/scripts/skill_qa_fig3.py with Figure 1's ROLE table (the skill's own CLIs were read,
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

Run:  python3 scripts/skill_qa_fig1.py fig1.pdf   (writes skill_qa_fig1.txt, fig1_export_manifest.json)
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
FIG1 = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG1, '..', 'style')))
import figstyle as fs  # noqa: E402
import qa_check as qa  # noqa: E402  (PDF resource / content walkers)
from pypdf import PdfReader  # noqa: E402

PT2MM = 25.4 / 72
ELSEVIER_WIDTHS_MM = (90.0, 140.0, 190.0)
TEXT_MIN_PT = 6.0                   # v7 (DESIGN_V7 section 2, the sciplot clean-nature scale): tick labels, muted notes
                                    # and the loss numerals 6 pt; words 7 pt; letters 8 pt (was 6.5 pt ticks in v6)
WORD_MIN_PT = 7.0                   # non-tick text: axis titles, row labels, direct labels, schematic labels
NOTE_PT = fs.FS['note']             # ... except muted secondary text (fill SP_MUTED only) at 6 pt: the runtime tags,
                                    # the API name and the vendor-group list of a (v7 graft b)
ROLE = {                            # what each drawn colour is used for in Fig 1 (decides its contrast threshold)
    '#000000': ('the panel letters (composite)', 4.5),
    fs.SP_FG: ('sciplot text colour: every label; the script-blocker wall (a) and its miniature, the "blocked" bar (b)',
               4.5),
    fs.SP_AXIS: ('sciplot chrome: the axes and ticks (b, c); schematic outlines and connectors (a)', 3.0),
    fs.SP_MUTED: ('sciplot muted text: the three region names, the API name, runtime tags and vendor-group list (a), '
                  'the tick-height key (b)', 4.5),
    fs.SAND: ('SAND: the pixel-sandbox region outline (a)', 3.0),
    fs.LEAK: ('LEAK brick: the requests that lost consent -- the leak arrows and the outlines of the five loss '
              'numerals (a; the digits are SP_FG), the sandboxed request ticks, key ticks and the late-beacon '
              'arrowhead (b), the first-request line, its arrowheads and the crossing circle (c)', 3.0),
    fs.NEUTRAL: ('NEUTRAL grey: context -- the browser frame and the page-region outline, the stopped tag wire and '
                 'the dotted cut path (a), the label leader (c)', 3.0),
    fs.EVENT: ('EVENT amber: the banner becoming visible (b, c), a rule that is also named ("banner visible" in b; '
               'the zero of the x axis in c); the outline of the cookie-banner box (a)', 3.0),
    fs.SP_CONTEXT: ('sciplot context grey: every request tick of the raster (c)', 3.0),
    fs.TINT['EVENT']: ('fill: amber tint behind the cookie-banner label (a; text on it 13.7:1)', None),
    fs.TINT['SAND']: ('ground: the pixel-sandbox region (a) and the sandbox lane (b); text on it >= 4.1:1 (muted '
                      'region name), 13.8:1 (labels)', None),
    fs.TINT['PAGE']: ('ground: the page region (a) and the page lane (b), one step lighter than the sandbox ground',
                      None),
    fs.TINT['LEAK']: ("ground: c's 'before the banner' area between the first-request line and the amber rule "
                      '(grey ticks drawn on it)', None),
    fs.SP_GUIDE: ('decorative: the two hairline row guides (b)', None),
    '#ffffff': ('surface', None),
}
ACCEPTED_LOW = {fs.NEUTRAL: 'RESTRAINT rule 6 neutral, context only; the point of a and c is carried by the brick '
                            'marks (4.4:1), and the stopped wire also ends at the black wall',
                fs.EVENT: 'RESTRAINT rule 6 fixes amber for the consent event; the rule is named in text (b) and sits '
                          'on the labelled 0 tick (c), and the banner box is named in text (a), so it is never read '
                          'by colour alone',
                fs.SP_CONTEXT: "sciplot: grey for context, colour for signal; the ticks are context behind the brick "
                               "line (4.4:1), which carries c's point; each tick's position, not its colour, is read"}
CATEGORY_PAIRS = [(fs.LEAK, fs.NEUTRAL, 'the requests that lost consent vs context (a: leak arrows vs the stopped tag '
                                        'wire)'),
                  (fs.LEAK, fs.SP_CONTEXT, 'c: first-request line vs request ticks'),
                  (fs.LEAK, fs.EVENT, 'requests (brick) vs the banner rule (amber), b and c; also told apart by mark '
                                      'type (ticks / a line vs one vertical rule)')]


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
        wv = ('ok: words >= 7 pt; tick labels and loss numerals 6 pt; 6 pt words only as muted secondary text '
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
    lines.append("   No vendor hues are drawn (v6: identity is not this figure's point; per-vendor detail is in Fig. S6). "
                 "Brick, amber, SAND and grey each have one meaning, named in the caption; the four fills are pre-mixed "
                 "tints (sciplot), never alpha, each repeating its token's meaning: amber (the banner box), SAND at two "
                 "steps (the page and sandbox regions of a = the two lanes of b) and brick (c's before-the-banner "
                 "ground); b's two request kinds differ by tick height (short / tall, keyed above the axis), not by "
                 "colour.")
    png = os.path.join(FIG1, '_v7_review-p01.png')        # the one review PNG (200 dpi; disk)
    pngrep = inspect_png(png, reports[0]['width_mm']) if os.path.exists(png) else None
    if pngrep:
        lines.append(f"== preview {pngrep['path']}: {pngrep['px'][0]} x {pngrep['px'][1]} px, {pngrep['mode']}, "
                     f"opaque={pngrep['opaque']}, {pngrep['effective_ppi_at_final_width']} ppi at 190 mm "
                     f"(a review render; the submission file is the vector PDF)")
    lines.append('   v7 type check: words 7 pt; tick labels, loss numerals and muted secondary text 6 pt; letters 8 pt '
                 '(DESIGN_V7 section 2). Elsevier asks for about 7 pt lettering: 6 pt is the sciplot Nature tick size '
                 'the v7 spec adopts; confirm against the C&S Guide for Authors before submission.')
    lines.append('RESULT: ' + ('PASS (automatic screen; not a compliance certificate)' if not fails else f'FAIL ({fails})'))
    open(os.path.join(FIG1, 'skill_qa_fig1.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))

    study = fs.STUDY
    srcs = {'stats.json': fs.STATS_JSON, 'fig1/derived_numbers.json': os.path.join(FIG1, 'derived_numbers.json')}
    try:
        tect = subprocess.run([os.environ.get('TECTONIC', 'tectonic'), '--version'], capture_output=True,
                              text=True).stdout.strip()
    except Exception:
        tect = None
    manifest = dict(
        figure='Figure 1 (v7 reference figure: v6 content in the sciplot clean theme, mmd-ahd/scientific-figure-skill, with the FigGenie and nature-figure grafts of DESIGN_V7.md; K-Dense skill v1.4 screen)',
        destination=dict(journal='Computers & Security (Elsevier)', article_type='research article',
                         phase='initial submission', width='full (190 mm)',
                         publisher_rules='PENDING VERIFICATION against the live C&S Guide for Authors; screened only '
                                         "against the skill's dated Elsevier snapshot"),
        outputs=[dict(file=os.path.basename(r['path']), format='PDF (vector, Type 42 / CID TrueType Arial, opaque '
                      'white, RGB)', width_mm=r['width_mm'], height_mm=r['height_mm'], bytes=r['bytes'],
                      sha256=sha256(r['path'])) for r in reports] + ([dict(file=pngrep['path'], format='PNG review '
                      'render, 200 ppi', px=pngrep['px'])] if pngrep else []),
        sources={k: dict(path=os.path.relpath(v, study), sha256=sha256(v)) for k, v in srcs.items()},
        transformations=['analysis/analyze.py -> analysis/outputs/stats.json (Wilson CIs; Round 4 blocklist '
                         'combined sample)',
                         'fig1/scripts/derive_fig1.py -> fig1/derived_numbers.json (fig1b_trace: the re-check load of '
                         'v4 Fig 4d, recomputed from crawl/recheck (read-only) and asserted equal to the Fig 4 record; '
                         'fig1c_raster: the out-of-axis counts of the raster)',
                         'fig1/scripts/make_panels.py (drawing only; no number is printed in the panels besides tick '
                         'labels; every drawn value registered in fig1_numbers.csv and checked by scripts/trace_fig1.py)',
                         'fig1/scripts/make_caption.py (the caption carries every count; registry caption_fig1_numbers.csv)',
                         'fig1a_pipeline.tex (TikZ line art), fig1.tex (composite, tectonic)'],
        uncertainty='Caption: Wilson 95% CIs of a share (stores are the unit) for loss point (2) and the c '
                    'before-the-banner share; b is one load (no interval); a is a schematic.',
        missing_data='c: the requests outside the -4 to +8 s axis are not drawn and are counted in the caption; the '
                     'first-request line leaves the axis (an arrowhead inside the frame) for the stores whose first request lies '
                     'outside it; b: the 1 beacon beyond the axis is an arrowhead inside the right edge of the box, its '
                     'time in the caption.',
        software=dict(python=platform.python_version(), matplotlib=version('matplotlib'), numpy=version('numpy'),
                      pypdf=version('pypdf'), pandas=version('pandas'), tectonic=tect),
        alt_text='alt_text_fig1.txt',
        note='No automated report here certifies accessibility or journal compliance (skill guardrail).',
    )
    json.dump(manifest, open(os.path.join(FIG1, 'fig1_export_manifest.json'), 'w'), indent=1)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main([os.path.abspath(p) for p in sys.argv[1:]] or [os.path.join(FIG1, 'fig1.pdf')])
