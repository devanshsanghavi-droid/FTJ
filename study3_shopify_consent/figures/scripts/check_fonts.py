"""Automated font check for every figure PDF (review: 7 pt floor, one sans family).
For each PDF, every text-showing operation's effective size (Tf size x text matrix x CTM scale) and font name are
collected with pypdf; sizes below 7 pt (a 0.05 pt tolerance) or fonts outside Arial / Courier New are listed.
Writes figures/font_check.txt; exit 1 on any failure."""
import glob
import os
import sys

from pypdf import PdfReader

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.normpath(os.path.join(HERE, '..'))
FILES = sorted(glob.glob(os.path.join(FIG, 'panels', '*.pdf'))) + [os.path.join(FIG, 'fig1_composite.pdf')] + \
    sorted(glob.glob(os.path.join(FIG, 'schematics', 'fig*.pdf')))
OKFONTS = ('Arial', 'ArialMT', 'Arial-BoldMT', 'Arial-ItalicMT', 'Arial-BoldItalicMT', 'CourierNewPSMT', 'CourierNew')
SKIP = {'fig1b_situating_data.pdf', 'fig1c_page_load_timeline.pdf'}  # checked inside the composite as well


def scan(fn):
    r = PdfReader(fn)
    small, fonts = [], set()
    for page in r.pages:
        def vis(text, cm, tm, fd, fs):
            if not text.strip():
                return
            sc = abs(tm[0] * tm[3] - tm[1] * tm[2]) ** 0.5 * abs(cm[0] * cm[3] - cm[1] * cm[2]) ** 0.5
            size = fs * sc
            name = str(fd.get('/BaseFont', '?')).split('+')[-1].lstrip('/') if fd else '?'
            if name == '?':
                return
            fonts.add(name)
            if size < 6.95:
                small.append((round(size, 2), text.strip()[:40], name))
        page.extract_text(visitor_text=vis)
    return small, fonts


def main():
    out, fails = [], 0
    for fn in FILES:
        if not os.path.exists(fn):
            continue
        small, fonts = scan(fn)
        bad_fonts = [f for f in fonts if not any(f.startswith(o) for o in OKFONTS)]
        b = os.path.basename(fn)
        status = 'OK' if not small and not bad_fonts else 'FAIL'
        if status == 'FAIL':
            fails += 1
        out.append(f'{status} {b}: fonts {sorted(fonts)}; text below 7 pt: {len(small)}')
        for s in small[:12]:
            out.append(f'     {s}')
        for f in bad_fonts:
            out.append(f'     font not allowed: {f}')
    out.append('RESULT: ' + ('PASS' if fails == 0 else f'FAIL ({fails} files)'))
    open(os.path.join(FIG, 'font_check.txt'), 'w').write('\n'.join(out) + '\n')
    print('\n'.join(out))
    sys.exit(0 if fails == 0 else 1)


if __name__ == '__main__':
    main()
