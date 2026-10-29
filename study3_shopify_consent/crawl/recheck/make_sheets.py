"""Blind contact sheets for the banner-recall screenshots (final audit re-check).
Stores are shown in a seeded random order under neutral codes (R001...), with no group, CMP or detector result, so
that a labeller cannot see what the crawler decided. Each row: the viewport at about 3, 6 and 10 s after the load event.
The code -> store mapping is in sheets/blind_key.csv (do not open it before labelling).
Labelling question per code: is a cookie/privacy consent banner or dialog visible in any of the three shots?
"""
import csv, os, random
from PIL import Image, ImageDraw, ImageFont
H = os.path.dirname(os.path.abspath(__file__))
SH = os.path.join(H, 'screenshots'); OUT = os.path.join(H, 'sheets'); os.makedirs(OUT, exist_ok=True)
ids = [r['store_id'] for r in csv.DictReader(open(os.path.join(H, 'recheck_list.csv')))]
random.Random(4242).shuffle(ids)
key = [(f'R{i + 1:03d}', s) for i, s in enumerate(ids)]
with open(os.path.join(OUT, 'blind_key.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['code', 'store_id']); w.writerows(key)
TW, TH = 420, 277; ROWS = 5; PAD = 26
try:
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 20)
except Exception:
    font = ImageFont.load_default()
for p in range(0, len(key), ROWS):
    chunk = key[p:p + ROWS]
    img = Image.new('RGB', (3 * TW + 4 * 6, len(chunk) * (TH + PAD) + 6), 'white')
    d = ImageDraw.Draw(img)
    for r, (code, sid) in enumerate(chunk):
        y = r * (TH + PAD) + 4
        d.text((6, y), f'{code}   (3 s | 6 s | 10 s after load)', fill='black', font=font)
        for c, t in enumerate(('3s', '6s', '10s')):
            fp = os.path.join(SH, f'{sid}__R0__{t}.jpg')
            x = 6 + c * (TW + 6)
            if os.path.exists(fp):
                im = Image.open(fp).convert('RGB').resize((TW, TH))
                img.paste(im, (x, y + PAD - 2))
                d.rectangle([x, y + PAD - 2, x + TW - 1, y + PAD - 2 + TH - 1], outline='grey')
            else:
                d.text((x + 10, y + PAD + 100), 'no screenshot', fill='red', font=font)
    img.save(os.path.join(OUT, f'sheet_{p // ROWS + 1:02d}.jpg'), quality=80)
print('sheets', (len(key) + ROWS - 1) // ROWS)
