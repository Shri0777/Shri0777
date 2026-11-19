#!/usr/bin/env python3
"""One-time: turn assets/portrait-cutout.png into data/portrait.txt (ASCII).

    pip install pillow
    python scripts/make_portrait.py [--rows 96]

The cutout is a transparent PNG; transparent pixels become spaces.
"""
import argparse
import pathlib

from PIL import Image, ImageFilter, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAMP = " .:-=+*#%@"  # light to dense ink; the renderer also tones by index

ap = argparse.ArgumentParser()
ap.add_argument("--rows", type=int, default=96)
ap.add_argument("--cell", type=float, default=0.6, help="glyph width / line height")
ap.add_argument("--gamma", type=float, default=0.72)
ap.add_argument("--box", default="10,12,330,332", help="crop of the cutout, x0,y0,x1,y1 (head and upper shoulders)")
a = ap.parse_args()

im = Image.open(ROOT / "assets" / "portrait-cutout.png").convert("RGBA")
im = im.crop(tuple(int(v) for v in a.box.split(",")))
w, h = im.size
side = max(w, h)
sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
sq.paste(im, ((side - w) // 2, side - h))  # sit the bust on the bottom edge
im = sq

cols = round(a.rows / a.cell)
small = im.resize((cols, a.rows), Image.LANCZOS)
alpha = small.getchannel("A")
# boost local detail before sampling: sharpen at full size, then equalise
# the visible pixels so the face does not sink into the hair and shirt
full_gray = ImageOps.grayscale(im.convert("RGB")).filter(ImageFilter.UnsharpMask(radius=4, percent=220, threshold=2))
gray = full_gray.resize((cols, a.rows), Image.LANCZOS)
gray = ImageOps.equalize(gray, mask=alpha.point(lambda v: 255 if v > 60 else 0))

lines = []
for y in range(a.rows):
    row = []
    for x in range(cols):
        al = alpha.getpixel((x, y)) / 255
        if al < 0.08:
            row.append(" ")
            continue
        ink = 0.08 + 0.92 * (1 - gray.getpixel((x, y)) / 255) ** a.gamma * min(1.0, al * 1.15)
        idx = min(len(RAMP) - 1, max(1, round(ink * (len(RAMP) - 1))))
        row.append(RAMP[idx])
    lines.append("".join(row).rstrip())

(ROOT / "data" / "portrait.txt").write_text("\n".join(lines), encoding="utf-8")
print(f"{a.rows} rows x {cols} cols")
