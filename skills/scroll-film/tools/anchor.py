"""Anchor-frame compositor: generated plate + EXACT vector logo (the mark is never generated).

usage: python anchor.py --plate plate.png --svg logo.svg --out anchor.png --size 1920x1080 \
         [--at auto|center|X,Y] [--mark-frac 0.20] [--glow "#00ada7"] [--glow-alpha 0.55]
--at auto : finds the brightest glow core (G+B-1.5R on a blurred copy; override --score for other palettes).
The anchor becomes Seedance --end-image (forward) or --start-image (backward, then reverse).
Needs: pillow, numpy, playwright (chromium) to rasterise the SVG exactly as a browser does.
"""
import argparse
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter, ImageColor
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("--plate", required=True); ap.add_argument("--svg", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--size", default="1920x1080"); ap.add_argument("--at", default="auto"); ap.add_argument("--mark-frac", type=float, default=0.20)
ap.add_argument("--glow", default="#00ada7"); ap.add_argument("--glow-alpha", type=float, default=0.55)
a = ap.parse_args()
W, H = map(int, a.size.lower().split("x")); ar = W / H

def crop_to(im, ar):
    w, h = im.size
    if w / h > ar: nw = int(h * ar); return im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    nh = int(w / ar); return im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))

plate = crop_to(Image.open(a.plate).convert("RGB"), ar).resize((W, H), Image.LANCZOS)
m = int(min(W, H) * a.mark_frac) if ar >= 1 else int(W * a.mark_frac * 1.5)
svg = Path(a.svg).read_text()
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": m, "height": m})
    pg.set_content('<html><body style="margin:0;background:transparent">' + svg.replace("<svg ", f'<svg width="{m}" height="{m}" ', 1) + "</body></html>")
    tmp = Path(a.out).with_suffix(".mark.png"); pg.screenshot(path=str(tmp), omit_background=True, clip={"x": 0, "y": 0, "width": m, "height": m}); b.close()
mark = Image.open(tmp).convert("RGBA"); tmp.unlink()

if a.at == "auto":
    arr = np.asarray(plate.filter(ImageFilter.GaussianBlur(W * 0.01))).astype(float)
    y, x = np.unravel_index((arr[..., 1] + arr[..., 2] - 1.5 * arr[..., 0]).argmax(), arr.shape[:2])
elif a.at == "center": x, y = W // 2, H // 2
else: x, y = map(int, a.at.split(","))

r, g, bl = ImageColor.getrgb(a.glow)
glow = Image.new("RGBA", mark.size, (r, g, bl, 0))
glow.putalpha(mark.split()[3].filter(ImageFilter.GaussianBlur(m * 0.06)).point(lambda v: int(v * a.glow_alpha)))
out = plate.convert("RGBA"); pos = (int(x - m / 2), int(y - m / 2))
out.alpha_composite(glow, pos); out.alpha_composite(mark, pos)
out.convert("RGB").save(a.out)
print(f"{a.out} core=({x},{y}) mark={m}px")
