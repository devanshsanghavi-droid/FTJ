"""Steps 5-6 of the K-Dense 'scientific-visualization' skill (v1.4) for Figure 5 (v7; ../../DESIGN_V7.md), on the
machinery of the v7 worked example ../../fig1/scripts/skill_qa_fig1.py (6 pt tick / note floor, words >= 7 pt except
muted SP_MUTED secondary text, accepted low-contrast neutrals and tokens) with Figure 5's ROLE table (the skill's own
CLIs were read, not executed):

  1. inspect the delivered file: page size, fonts (embedded? TrueType/Type 42, never Type 3), raster content
  2. audit every colour actually drawn: WCAG 2.2 sRGB contrast against the white surface (4.5:1 text, 3:1 graphical
     objects needed to read the figure) and pairwise CIE L* separation of the colours that distinguish categories
     (the skill's grayscale screen: delta L* >= 10, a heuristic, not a standard)
  3. screen against the skill's dated Elsevier snapshot (Computers & Security is an Elsevier journal): widths 90 / 140 /
     190 mm, lettering about 7 pt (6 pt floor only for sub/superscripts), PDF for vector and text, RGB
  4. write the export manifest (dimensions, format, package versions, source references, provenance)

The skill is explicit that none of this certifies accessibility or journal compliance ('a zero failure count is not
acceptance'); the C&S Guide for Authors must still be checked before upload.

Run:  python3 scripts/skill_qa_fig5.py fig5.pdf   (writes skill_qa_fig5.txt, fig5_export_manifest.json)
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
FIG5 = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.normpath(os.path.join(FIG5, '..', 'style')))
import figstyle as fs  # noqa: E402
import qa_check as qa  # noqa: E402  (PDF resource / content walkers)
from pypdf import PdfReader  # noqa: E402

PT2MM = 25.4 / 72
ELSEVIER_WIDTHS_MM = (90.0, 140.0, 190.0)
REVIEW_PNG = '_v7_review-p01.png'   # the build's QA render (200 dpi; the one review PNG kept)
TEXT_MIN_PT = 6.0                   # v7 (DESIGN_V7 section 2, the sciplot clean-nature scale): tick labels and muted
                                    # notes 6 pt; words 7 pt; letters 8 pt (was 6.5 pt ticks in v6)
WORD_MIN_PT = 7.0                   # non-tick text: axis titles, category / row labels, direct labels, the keys
NOTE_PT = fs.FS['note']             # ... except muted secondary text (fill SP_MUTED only) at 6 pt (none in Fig 5)
ROLE = {                            # what each drawn colour is used for in Fig 5 (decides its contrast threshold)
    '#000000': ('the panel letters (composite); the Default circles, their CIs and key marker (a)', 4.5),
    fs.SP_FG: ("sciplot text colour: category and row labels, axis titles, b's three class names at the Decline bar, "
               "the two block labels (c); each bar's total (a short rising tick) and its CI line just under the bar "
               "(b, Fig. 4a's grammar)", 4.5),
    fs.SP_AXIS: ('sciplot chrome: the open L axes, their outward major and minor ticks and tick labels (a, b, c); the '
                 "two segments of c's broken row axis and the two cut marks in its break", 3.0),
    fs.SP_MUTED: ('sciplot muted text: the two keys (a: the arms; c: the tick colours, as Fig. S8d)', 4.5),
    fs.GREY_D: ("the Decline open squares, their CIs and key marker (a); the 'no purpose' segments (b, Fig. S8c's "
                "colour for that class)", 3.0),
    fs.NEUTRAL: ("NEUTRAL grey: the GPC triangles, their CIs and key marker (a); the 'only purposes left allowed' "
                 "segments and the three label leaders (b); the sandboxes that started after the 'no' and their key "
                 "handle (c)", 3.0),
    fs.LIGHT: ("decorative: the thin line joining each group's three estimates (a)", None),
    fs.LEAK: ("LEAK brick, consent lost: the 'a refused purpose' segment (b); the sandboxes that started before the "
              "CMP wrote 'no' and their key handle (c)", 3.0),
    fs.HONOUR: ("HONOUR slate, consent honoured: the sandboxes of the 'yes' loads and their key handle (c)", 3.0),
    fs.EVENT: ("EVENT amber: the CMP's consent write, the rule at 0 (c)", 3.0),
    fs.TINT['LEAK']: ("ground: c's key area, row by row from each 'no' load's first sandbox to the write (the brick "
                      'ticks drawn on it, 3.9:1)', None),
    '#ffffff': ('surface; open-square fills (a); the thin white gaps between stacked segments (b)', None),
}
ACCEPTED_LOW = {fs.NEUTRAL: 'DESIGN_V7 section 3.2 neutral and the fixed GPC arm grey (figstyle.ARM); the GPC mark is '
                            'told apart by shape (a triangle) and the key, the b segment by its direct label and white '
                            'gaps, the leaders are hairlines to labelled segments, and the c ticks are context (their '
                            'side of the amber rule carries the point; the key names them)',
                fs.EVENT: 'DESIGN_V7 section 3.1 fixes amber for the consent moment; the rule sits on the labelled 0 '
                          "tick of an axis titled 'minus the CMP's consent write', so it is never read by colour alone"}
CATEGORY_PAIRS = [(fs.INK, fs.GREY_D, 'Default vs Decline (a; also filled circle vs open square)'),
                  (fs.GREY_D, fs.NEUTRAL, "Decline vs GPC (a; also open square vs triangle); 'only purposes left "
                                          "allowed' vs 'no purpose' (b, adjacent segments split by a white gap and "
                                          "named at the Decline bar)"),
                  (fs.LEAK, fs.NEUTRAL, "'a refused purpose' vs 'only purposes left allowed' (b, adjacent segments "
                                        "split by a white gap); before vs after the 'no' (c, also left vs right of the "
                                        "amber rule)"),
                  (fs.LEAK, fs.HONOUR, "'no' loads before the write vs 'yes' loads (c; also upper vs lower block and "
                                       "left vs right of the amber rule)")]


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
    lines.append("   No vendor hue is drawn: a uses the arm neutrals of Fig. S8a (the vendor groups are named by their "
                 "tick labels), so the key's marks are the plotted marks. Arms differ by marker shape (filled circle, "
                 "open square, filled triangle) as well as grey level. In b the classes are split by white gaps and "
                 "named once by direct labels at the Decline bar (Fig. S8c's names, colours and order), so b's greys "
                 "are never read through a's arm key; in c brick, grey and slate also differ by block and by side of "
                 "the amber rule, and a key names them (Fig. S8d's). Brick and slate (delta L* 1.4) never have to be told apart by lightness "
                 "alone. The one fill is a pre-mixed tint (sciplot), never alpha, repeating its token's meaning: TINT "
                 "LEAK, c's key area where consent was lost.")
    png = os.path.join(FIG5, REVIEW_PNG)
    pngrep = inspect_png(png, reports[0]['width_mm']) if os.path.exists(png) else None
    if pngrep:
        lines.append(f"== preview {pngrep['path']}: {pngrep['px'][0]} x {pngrep['px'][1]} px, {pngrep['mode']}, "
                     f"opaque={pngrep['opaque']}, {pngrep['effective_ppi_at_final_width']} ppi at {reports[0]['width_mm']:g} mm "
                     f"(a review render; the submission file is the vector PDF)")
    lines.append('   v7 type check: words 7 pt; tick labels 6 pt; letters 8 pt (DESIGN_V7 section 2). Elsevier asks '
                 'for about 7 pt lettering: 6 pt is the sciplot Nature tick size the v7 spec adopts; confirm against '
                 'the C&S Guide for Authors before submission.')
    lines.append('RESULT: ' + ('PASS (automatic screen; not a compliance certificate)' if not fails else f'FAIL ({fails})'))
    open(os.path.join(FIG5, 'skill_qa_fig5.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))

    study = fs.STUDY
    srcs = {'stats.json': fs.STATS_JSON, 'derived_numbers.json': fs.DERIVED_JSON,
            'fig5/derived_numbers.json': os.path.join(FIG5, 'derived_numbers.json')}
    try:
        tect = subprocess.run([os.environ.get('TECTONIC', 'tectonic'), '--version'], capture_output=True,
                              text=True).stdout.strip()
    except Exception:
        tect = None
    manifest = dict(
        figure='Figure 5 (v7: DESIGN_V7.md, the sciplot clean theme with the nature-figure grafts; worked example fig1; K-Dense skill v1.4 screen)',
        destination=dict(journal='Computers & Security (Elsevier)', article_type='research article',
                         phase='initial submission', width='full (190 mm)',
                         publisher_rules='PENDING VERIFICATION against the live C&S Guide for Authors; screened only '
                                         "against the skill's dated Elsevier snapshot"),
        outputs=[dict(file=os.path.basename(r['path']), format='PDF (vector, Type 42 / CID TrueType Arial, opaque '
                      'white, RGB)', width_mm=r['width_mm'], height_mm=r['height_mm'], bytes=r['bytes'],
                      sha256=sha256(r['path'])) for r in reports] + ([dict(file=pngrep['path'], format='PNG review '
                      'render, 200 ppi', px=pngrep['px'])] if pngrep else []),
        sources={k: dict(path=os.path.relpath(v, study), sha256=sha256(v)) for k, v in srcs.items()},
        transformations=['analysis/analyze.py -> analysis/outputs/stats.json (Wilson CIs, Newcombe paired '
                         'differences, exact McNemar test; gate audit; exclusive store classes; the race per load)',
                         'figures/v7/scripts/derive_numbers.py -> figures/v7/derived_numbers.json (exclusive classes '
                         'of the stores still sending; per-sandbox race lags, medians and out-of-axis counts)',
                         'fig5/scripts/derive_fig5_numbers.py -> fig5/derived_numbers.json (per-load race lags for the '
                         'raster, asserted against stats.json)',
                         'fig5/scripts/make_fig5_panels.py (drawing only; the panels print no number besides axis '
                         'ticks; every drawn value registered as a mark in panels/fig5_numbers.csv, the ticks in '
                         'panels/fig5_ticks.csv; checked by scripts/trace_fig5.py)',
                         'fig5/scripts/make_caption_fig5.py (the caption and alt text carry every count; registry '
                         'panels/caption_fig5_numbers.csv)', 'fig5.tex (composite, tectonic)'],
        uncertainty=f"a: Wilson 95% CIs of a share (stores are the unit; the three arms are the same "
                    f"{fs.stat('fig5/a/n_clicked')} stores), drawn as vertical lines in the colour of their mark; "
                    'paired differences in the caption: Newcombe hybrid-score 95% CIs and an exact McNemar test. b: the '
                    'Wilson 95% CI of each bar total (stores still sending), drawn by figstyle.bar_ci as a horizontal '
                    'line; the class '
                    'segments are complete counts. c: complete counts (no interval). No bootstrap (no seed needed).',
        missing_data=(f"b: {fs.derived('fig5b_exclusive_classes/gpc/other_unmatched')} GPC store matched no class "
                      f"and is not drawn (stated in the caption; it is inside the CI's total); what the gate held is "
                      f"stated in the caption, not drawn. c: none (every sandbox lies inside the symmetric-log axis, "
                      f"asserted)."),
        software=dict(python=platform.python_version(), matplotlib=version('matplotlib'), numpy=version('numpy'),
                      pypdf=version('pypdf'), pandas=version('pandas'), tectonic=tect),
        alt_text='alt_text_fig5.txt',
        note='No automated report here certifies accessibility or journal compliance (skill guardrail).',
    )
    json.dump(manifest, open(os.path.join(FIG5, 'fig5_export_manifest.json'), 'w'), indent=1)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main([os.path.abspath(p) for p in sys.argv[1:]] or [os.path.join(FIG5, 'fig5.pdf')])
