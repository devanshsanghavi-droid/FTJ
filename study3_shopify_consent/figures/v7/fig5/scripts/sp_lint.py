"""sp_lint.py -- step 5 of the sciplot skill (mmd-ahd/scientific-figure-skill) for Figure 5, copied from the v7
worked example ../../fig1/scripts/sp_lint.py and re-implemented from the skill's check.lint (read, never executed): the skill's save() runs lint on every figure and its rule is "fix every lint warning
or consciously justify it".

  lint_fig(fig, name)  matplotlib panels (a, b, c) before saving: text sizes inside the venue range, every visible line and
                       spine >= 0.25 pt (the skill's minimum stroke), the font matplotlib actually renders (silent
                       fallbacks), no rainbow colormap, text contrast >= 3:1 against what lies under it
  lint_pdf(pdf)        the composite: the categorical hues actually drawn (OKLCH chroma > 0.04; tints / shades of one
                       hue merged, as the skill does) must stay >= 10 CIEDE2000 apart under deutan, protan and tritan
                       simulation (Machado et al. 2009, severity 1, linear sRGB): >= 10 pass, 6-10 warn, < 6 fail

Venue: Computers & Security (Elsevier), 190 mm double column; the skill's Nature numbers are used where Elsevier sets
none (minimum stroke 0.25 pt); type is the v7 scale (../../DESIGN_V7.md: 7 pt words, 6 pt ticks / notes / loss
numerals, 8 pt letters).
Run:  python3 scripts/sp_lint.py fig5.pdf     (build_fig5.sh runs it; exit 1 on a failure)
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', '..', 'style')))
import figstyle as fs  # noqa: E402

FONT_MIN, FONT_MAX = 5.0, 9.0       # sciplot nature range 5-7 pt text; 9 pt cap covers the 8 pt panel letters
LINE_MIN = 0.25                     # pt (sciplot VENUES['nature'] line_min)
DE_OK, DE_FAIL = 10.0, 6.0
RAINBOW = {'jet', 'rainbow', 'hsv', 'gist_rainbow', 'gist_ncar', 'nipy_spectral', 'spectral'}
MACHADO = {   # severity 1.0, linear RGB (= ../../style/cvd_check.py)
    'deutan': [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
    'protan': [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    'tritan': [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
}


# ------------------------------------------------------------------------------------------------ colour maths
def _rgb(hx):
    return np.array([int(hx[i:i + 2], 16) / 255 for i in (1, 3, 5)])


def _lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


def oklch(hx):
    m1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566],
                   [0.0883024619, 0.2817188376, 0.6299787005]])
    m2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099],
                   [0.0259040371, 0.7827717662, -0.8086757660]])
    L, a, b = m2 @ np.cbrt(m1 @ _lin(_rgb(hx)))
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def lab(rgb):
    """CIE L*a*b* (D65) of an sRGB triple in 0..1."""
    x, y, z = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750],
                        [0.0193339, 0.1191920, 0.9503041]]) @ _lin(rgb)
    f = lambda t: t ** (1 / 3) if t > (6 / 29) ** 3 else t / (3 * (6 / 29) ** 2) + 4 / 29   # noqa: E731
    fx, fy, fz = f(x / 0.95047), f(y / 1.0), f(z / 1.08883)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def de2000(l1, l2):
    """CIEDE2000 (Sharma, Wu & Dalal 2005)."""
    L1, a1, b1 = l1
    L2, a2, b2 = l2
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = 0 if C1p * C2p == 0 else (h2p - h1p if abs(h2p - h1p) <= 180 else
                                    h2p - h1p - 360 if h2p - h1p > 180 else h2p - h1p + 360)
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dh / 2))
    Lbp, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hbp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbp = (h1p + h2p) / 2
    else:
        hbp = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hbp - 30)) + 0.24 * math.cos(math.radians(2 * hbp))
         + 0.32 * math.cos(math.radians(3 * hbp + 6)) - 0.20 * math.cos(math.radians(4 * hbp - 63)))
    dth = 30 * math.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / math.sqrt(20 + (Lbp - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    Rt = -math.sin(math.radians(2 * dth)) * Rc
    return math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


def simulate(hx, kind):
    return _srgb(np.array(MACHADO[kind]) @ _lin(_rgb(hx)))


assert abs(de2000((50, 2.6772, -79.7751), (50, 0, -82.7485)) - 2.0425) < 1e-3     # Sharma et al. test pair 1


# ------------------------------------------------------------------------------------------------ lint
def lint_fig(fig, name):
    """sciplot check.lint on a matplotlib panel; returns the warnings (also printed)."""
    from matplotlib import font_manager as fm
    from matplotlib.colors import to_hex
    from matplotlib.text import Text
    fig.canvas.draw()
    warns, fonts = [], set()
    for t in fig.findobj(Text):
        if not t.get_visible() or not t.get_text().strip():
            continue
        s = t.get_fontsize()
        if not FONT_MIN - 0.05 <= s <= FONT_MAX + 0.05:
            warns.append(f'text {t.get_text()[:20]!r} at {s:g} pt (range {FONT_MIN:g}-{FONT_MAX:g})')
        fonts.add(fm.get_font(fm.findfont(t.get_fontproperties())).family_name)
        if fs.contrast(to_hex(t.get_color()), fs.SURFACE) < 3:
            warns.append(f'low-contrast text {t.get_text()[:20]!r}')
    thin = 0
    for ax in fig.axes:
        thin += sum(1 for ln in ax.get_lines() if ln.get_visible() and 0 < ln.get_linewidth() < LINE_MIN)
        thin += sum(1 for sp in ax.spines.values() if sp.get_visible() and 0 < sp.get_linewidth() < LINE_MIN)
        for a in ax.get_children():
            cm = getattr(a, 'get_cmap', None)
            if callable(cm) and getattr(a, 'get_array', lambda: None)() is not None and \
                    getattr(cm(), 'name', '').lower() in RAINBOW:
                warns.append(f'rainbow colormap {cm().name}')
    if thin:
        warns.append(f'{thin} line(s)/spine(s) thinner than {LINE_MIN} pt')
    if fonts - {'Arial'}:
        warns.append(f'fonts rendered: {sorted(fonts)} (expected Arial)')
    print(f'sciplot lint [{name}] - ' + ('OK' if not warns else f'{len(warns)} warning(s): ' + '; '.join(warns)) +
          f'  (font: {", ".join(sorted(fonts))})')
    return warns


def lint_pdf(pdf):
    """Categorical hues of the composite under CVD simulation (the skill's palette check). Returns (fails, lines)."""
    from pypdf import PdfReader
    import qa_check as qa
    r = PdfReader(pdf)
    wk = qa.Walker(r)
    p = r.pages[0]
    wk.walk(p.get_contents(), p.get('/Resources'), [1, 0, 0, 1, 0, 0])
    drawn = sorted({hx for cnt in wk.colors.values() for hx in cnt})
    hues = sorted([hx for hx in drawn if oklch(hx)[1] > 0.04], key=lambda h: -oklch(h)[1])
    uniq = []
    for c in hues:                                  # merge tints / shades of one hue (within 10 degrees)
        if all(min(abs(oklch(c)[2] - oklch(u)[2]), 360 - abs(oklch(c)[2] - oklch(u)[2])) > 10 for u in uniq):
            uniq.append(c)
    lines, fails = [f'sciplot palette check [{os.path.basename(pdf)}]: categorical hues drawn {uniq} '
                    f'(of {len(drawn)} colours; OKLCH chroma > 0.04)'], 0
    for i, a in enumerate(uniq):
        for b in uniq[i + 1:]:
            d = {'normal': de2000(lab(_rgb(a)), lab(_rgb(b)))}
            d.update({k: de2000(lab(simulate(a, k)), lab(simulate(b, k))) for k in MACHADO})
            worst = min(d[k] for k in MACHADO)
            verdict = 'pass' if worst >= DE_OK else ('warn' if worst >= DE_FAIL else 'FAIL')
            fails += verdict == 'FAIL'
            lines.append(f'  {a} vs {b}: dE2000 ' + ', '.join(f'{k} {v:.1f}' for k, v in d.items()) +
                         f'  -> {verdict} (>= {DE_OK:g} pass, {DE_FAIL:g}-{DE_OK:g} warn)')
    if len(uniq) > 5:
        lines.append(f'  {len(uniq)} hues: sciplot asks for <= 5 colours per panel')
    lines.append('RESULT: ' + ('PASS' if not fails else f'FAIL ({fails})'))
    return fails, lines


if __name__ == '__main__':
    f, out = lint_pdf(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'fig5.pdf'))
    print('\n'.join(out))
    open(os.path.join(HERE, '..', 'sp_lint_fig5.txt'), 'w').write('\n'.join(out) + '\n')
    sys.exit(1 if f else 0)
