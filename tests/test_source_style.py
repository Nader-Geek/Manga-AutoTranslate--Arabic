"""Original-text style estimation (fill / stroke / glow / gradient) on synthetic renders."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import manga
S = manga.MangaTranslator._source_style
FONT = ImageFont.truetype(str(Path(__file__).resolve().parent.parent / "fonts/Vazirmatn-Bold.ttf"), 46) \
    if (Path(__file__).resolve().parent.parent / "fonts/Vazirmatn-Bold.ttf").exists() else ImageFont.load_default(46)

def render(bg, fill, stroke=None, glow=None, grad=None):
    base = Image.new("RGB", (320, 120), bg)
    img = base.copy()
    if glow:
        m = Image.new("L", img.size, 0); ImageDraw.Draw(m).text((20, 25), "HELLO", font=FONT, fill=255)
        m = m.filter(ImageFilter.GaussianBlur(5)).point(lambda v: min(255, v * 2))
        img.paste(Image.new("RGB", img.size, glow), mask=m.point(lambda v: int(v * 0.8)))
    d = ImageDraw.Draw(img)
    if grad:
        m = Image.new("L", img.size, 0); ImageDraw.Draw(m).text((20, 25), "HELLO", font=FONT, fill=255,
                                                                stroke_width=3 if stroke else 0)
        g = Image.new("RGB", img.size)
        gd = ImageDraw.Draw(g)
        for yy in range(img.size[1]):
            t = min(1, max(0, (yy - 25) / 60))
            gd.line([(0, yy), (320, yy)], fill=tuple(int(grad[0][i] * (1 - t) + grad[1][i] * t) for i in range(3)))
        if stroke:
            d.text((20, 25), "HELLO", font=FONT, fill=stroke, stroke_width=3, stroke_fill=stroke)
        im2 = Image.new("L", img.size, 0); ImageDraw.Draw(im2).text((20, 25), "HELLO", font=FONT, fill=255)
        img.paste(g, mask=im2)
    else:
        d.text((20, 25), "HELLO", font=FONT, fill=fill, stroke_width=4 if stroke else 0, stroke_fill=stroke)
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR), cv2.cvtColor(np.array(base), cv2.COLOR_RGB2BGR)

rect = (10, 10, 300, 100)
# plain black on white
o, c = render((250, 250, 250), (10, 10, 10)); r = S(o, c, rect)
assert r and r["fill"] < "#222222" and not r["stroke"] and not r["gradient"], r
# white text with black stroke on a dark-blue background
o, c = render((40, 60, 120), (255, 255, 255), stroke=(0, 0, 0)); r = S(o, c, rect)
assert r["stroke"] and r["stroke"]["color"] < "#303030" and r["fill"] > "#d0d0d0", r
# yellow text, red glow
o, c = render((20, 20, 30), (255, 230, 40), glow=(255, 30, 30)); r = S(o, c, rect)
g = r["glow"]["color"] if r["glow"] else "#000000"
assert r["glow"] and int(g[1:3], 16) > 0x80 and int(g[3:5], 16) < 0x50 and int(g[5:7], 16) < 0x50, r
# vertical gradient red -> blue
o, c = render((250, 250, 250), None, grad=((230, 20, 20), (20, 20, 230))); r = S(o, c, rect)
assert r["gradient"] and r["gradient"]["from"][1:3] > "a0" and r["gradient"]["to"][5:7] > "a0", r
# nothing erased -> None ; shape mismatch -> None
assert S(c, c, rect) is None and S(o, c[:50], rect) is None and S(None, c, rect) is None
print("test_source_style OK")
