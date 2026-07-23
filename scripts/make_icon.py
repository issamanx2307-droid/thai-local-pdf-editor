# -*- coding: utf-8 -*-
"""Generate a clean app icon for Thai PDF Editor and save as .ico"""
from PIL import Image, ImageDraw, ImageFont

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# Page geometry with folded top-right corner
margin = 24
fold = 46
left, top, right, bottom = margin, margin, SIZE - margin, SIZE - margin

page = [
    (left, top),
    (right - fold, top),
    (right, top + fold),
    (right, bottom),
    (left, bottom),
]

# soft shadow
shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
sd = ImageDraw.Draw(shadow)
sd.polygon([(x + 6, y + 8) for x, y in page], fill=(20, 30, 40, 90))
shadow = shadow.filter(__import__("PIL.ImageFilter", fromlist=["GaussianBlur"]).GaussianBlur(6))
img.alpha_composite(shadow)

d.polygon(page, fill=(255, 255, 255, 255), outline=(210, 216, 222, 255))
d.polygon([(right - fold, top), (right, top + fold), (right - fold, top + fold)],
          fill=(230, 235, 239, 255), outline=(205, 210, 216, 255))

# blue Thai-flag-inspired accent bar on the left edge
d.rounded_rectangle([left, top, left + 10, bottom], radius=4, fill=(41, 98, 168, 255))

# a few text lines to suggest a document
line_color = (196, 202, 210, 255)
lx0, lx1 = left + 30, right - 60
for i, ly in enumerate(range(top + 40, top + 40 + 4 * 22, 22)):
    end = lx1 if i != 3 else lx1 - 40
    d.rounded_rectangle([lx0, ly, end, ly + 8], radius=4, fill=line_color)

# red ribbon with PDF text
ribbon_h = 56
ry0 = bottom - ribbon_h - 18
d.rectangle([left + 14, ry0, right - fold - 6, ry0 + ribbon_h], fill=(214, 69, 55, 255))

try:
    font = ImageFont.truetype("arialbd.ttf", 40)
except Exception:
    font = ImageFont.load_default()

text = "PDF"
bbox = d.textbbox((0, 0), text, font=font)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
tx = left + 14 + ((right - fold - 6 - (left + 14)) - tw) / 2 - bbox[0]
ty = ry0 + (ribbon_h - th) / 2 - bbox[1]
d.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))

out_path = "D:/PDF editor/assets/icons/pdf_editor.ico"
sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img.save(out_path, format="ICO", sizes=sizes)
print("saved:", out_path)
