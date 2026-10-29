#!/usr/bin/env python3
"""Release checks (standard library only).

  python3 release_tools/check.py verify    every file in MANIFEST.tsv exists with the listed size and SHA-256
  python3 release_tools/check.py compare   after ./reproduce.sh: compare the regenerated figures, tables and
                                           Markdown files with the shipped versions (PDFs compared with their
                                           /CreationDate removed, since it records when the file was written)
Exit code 1 if 'verify' finds a missing or changed file, or if 'compare' finds a changed text file.
"""
import csv
import hashlib
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
REGENERATED = [
    r'^study3_shopify_consent/figures/panels/',
    r'^study3_shopify_consent/figures/tables/',
    r'^study3_shopify_consent/figures/schematics/.*\.(pdf|png|tex)$',
    r'^study3_shopify_consent/figures/fig1_composite\.(pdf|png)$',
    r'^study3_shopify_consent/analysis/RESULTS\.md$',
    r'^study3_shopify_consent/figures/takeaways\.md$',
    r'^study3_shopify_consent/analysis/outputs/number_registry_.*\.csv$',
    r'^study3_shopify_consent/analysis/outputs/trace_check\.txt$',
]
TEXT = ('.md', '.csv', '.tex', '.txt')


def sha256(fn, pdf_normalized=False):
    b = open(fn, 'rb').read()
    if pdf_normalized:
        b = re.sub(rb'/CreationDate \([^)]*\)', b'/CreationDate ()', b)
    return hashlib.sha256(b).hexdigest()


def manifest():
    with open(os.path.join(ROOT, 'MANIFEST.tsv'), newline='') as fh:
        return list(csv.DictReader(fh, delimiter='\t'))


def verify():
    bad = 0
    rows = manifest()
    for r in rows:
        fn = os.path.join(ROOT, r['path'])
        if not os.path.exists(fn):
            print('MISSING', r['path'])
            bad += 1
        elif os.path.getsize(fn) != int(r['bytes']) or sha256(fn) != r['sha256']:
            print('CHANGED', r['path'])
            bad += 1
    print(f'verify: {len(rows) - bad} of {len(rows)} files match MANIFEST.tsv')
    return 1 if bad else 0


def png_of(path):
    """The PNG rendered from a PDF: same folder (panels, Figure 1 composite) or schematics/png/."""
    stem, _ = os.path.splitext(path)
    cands = [stem + '.png']
    d, b = os.path.split(stem)
    cands.append(os.path.join(d, 'png', b + '.png'))
    return next((c for c in cands if c in _ROWS), None)


_ROWS = {}


def compare():
    rx = re.compile('|'.join(REGENERATED))
    rows = manifest()
    _ROWS.update({r['path']: r for r in rows})
    same, same_render, diff_text, diff_bin = [], [], [], []
    ok_of = {}
    for r in rows:
        if not rx.search(r['path']):
            continue
        fn = os.path.join(ROOT, r['path'])
        if not os.path.exists(fn):
            diff_text.append(r['path'] + ' (missing)')
            continue
        if fn.endswith('.pdf'):
            ok = sha256(fn, True) == r['sha256_pdf_normalized']
        else:
            ok = sha256(fn) == r['sha256']
        ok_of[r['path']] = ok
    for p, ok in ok_of.items():
        if ok:
            same.append(p)
        elif p.endswith(TEXT):
            diff_text.append(p)
        elif p.endswith('.pdf') and ok_of.get(png_of(p) or '', False):
            same_render.append(p)   # TeX PDFs embed a timestamp and a random /ID inside compressed objects
        else:
            diff_bin.append(p)
    print(f'compare: {len(same)} regenerated files identical to the shipped ones')
    if same_render:
        print(f'  {len(same_render)} TeX-built PDFs differ in bytes (TeX writes a timestamp and a random document ID into '
              f'compressed objects), but the PNGs rendered from them are identical')
    for p in diff_text:
        print('  TEXT DIFFERS', p)
    for p in diff_bin:
        print('  image differs', p)
    if diff_bin:
        print('  (image differences usually come from a different matplotlib/FreeType version or a missing Arial '
              'font; the numbers drawn come from the same CSV/JSON files)')
    return 1 if diff_text else 0


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'verify':
        sys.exit(verify())
    if cmd == 'compare':
        sys.exit(compare())
    print(__doc__)
    sys.exit(2)
