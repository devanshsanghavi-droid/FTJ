#!/usr/bin/env python3
"""cvd_check.py -- colour-vision and grayscale QA render for one figure preview (v5 graft from the kosmos entry;
binding: ../DESIGN_V5.md, section "QA loop").

Reads the 300 dpi preview PNG of a figure and writes ONE 2 x 2 montage (each tile at half size):
    deuteranopia | protanopia
    tritanopia   | grayscale (CIE luminance)
CVD simulation: Machado, Oliveira & Fernandes (2009) matrices at severity 1.0, applied in linear sRGB -- the same model
as the dataviz skill's validator. Look at the montage and confirm, in the figure's QA.md, that every encoding still
separates (vendor chips + names, filled vs open, ink vs grey emphasis, ordinal ramps keep their order).

Usage:  python3 cvd_check.py PREVIEW.png [OUT.png]      (default OUT: <dir>/_qa_cvd.png)
This is a review aid, not a certificate: a simulation is not a full colour-vision test.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

MACHADO = {   # severity 1.0, linear RGB
    'deuteranopia': [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
    'protanopia': [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    'tritanopia': [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
}


def to_lin(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def to_srgb(a):
    a = np.clip(a, 0, 1)
    return np.where(a <= 0.0031308, 12.92 * a, 1.055 * a ** (1 / 2.4) - 0.055)


def simulate(rgb, kind):
    lin = to_lin(rgb)
    if kind == 'grayscale':
        y = lin @ np.array([0.2126, 0.7152, 0.0722])
        return np.repeat(to_srgb(y)[..., None], 3, axis=-1)
    return to_srgb(lin @ np.array(MACHADO[kind]).T)


def main(src, out=None):
    out = out or os.path.join(os.path.dirname(os.path.abspath(src)), '_qa_cvd.png')
    im = Image.open(src).convert('RGB')
    im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
    rgb = np.asarray(im, dtype=float) / 255
    kinds = ['deuteranopia', 'protanopia', 'tritanopia', 'grayscale']
    pad = 28
    W, H = im.width, im.height + pad
    canvas = Image.new('RGB', (2 * W, 2 * H), 'white')
    draw = ImageDraw.Draw(canvas)
    for i, k in enumerate(kinds):
        tile = Image.fromarray((simulate(rgb, k) * 255 + 0.5).astype('uint8'))
        x, y = (i % 2) * W, (i // 2) * H
        canvas.paste(tile, (x, y + pad))
        draw.text((x + 8, y + 6), k + (' (Machado 2009, severity 1.0)' if k != 'grayscale' else ' (CIE Y)'),
                  fill='black')
    canvas.save(out)
    print('wrote', out)
    return out


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(*sys.argv[1:3])
