"""Second pass for small notice bars: the top and bottom 130 px of the 3 s and 10 s shots of every code labelled 'no'
in the first pass, stacked (still blind: codes only)."""
import csv, os
from PIL import Image, ImageDraw, ImageFont
H = os.path.dirname(os.path.abspath(__file__)); SH = os.path.join(H, 'screenshots'); OUT = os.path.join(H, 'sheets')
key = {r['code']: r['store_id'] for r in csv.DictReader(open(os.path.join(OUT, 'blind_key.csv')))}
lab = [r for r in csv.DictReader(open(os.path.join(OUT, 'labels_assistant.csv'))) if r['consent_banner_visible'] == 'no']
font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 18)
SW, SHH = 1366 // 2, 130 // 2
per = 10
for p in range(0, len(lab), per):
    ch = lab[p:p + per]
    img = Image.new('RGB', (2 * SW + 18, len(ch) * (2 * SHH + 30) + 4), 'white'); d = ImageDraw.Draw(img)
    for i, r in enumerate(ch):
        y = i * (2 * SHH + 30) + 2
        d.text((4, y), f"{r['code']}  left: 3 s, right: 10 s; upper strip = top of page, lower strip = bottom", fill='black', font=font)
        for c, t in enumerate(('3s', '10s')):
            fp = os.path.join(SH, f"{key[r['code']]}__R0__{t}.jpg")
            if not os.path.exists(fp):
                continue
            im = Image.open(fp).convert('RGB'); w, h = im.size
            top = im.crop((0, 0, w, 130)).resize((SW, SHH)); bot = im.crop((0, h - 130, w, h)).resize((SW, SHH))
            x = 4 + c * (SW + 10)
            img.paste(top, (x, y + 24)); img.paste(bot, (x, y + 24 + SHH + 2))
    img.save(os.path.join(OUT, f'strips_{p // per + 1:02d}.jpg'), quality=85)
print((len(lab) + per - 1) // per)
