# -*- coding: utf-8 -*-
"""Draw the (Arabic) text of a chapter.json onto the cleaned pages with the copied effects:
fill / gradient / stroke / glow / drop shadow. Pure PIL (+ arabic_reshaper / python-bidi).

Used by /chapter render:True  ->  rendered/page-001.jpg ... inside the zip.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

FONTS_DIR = Path(__file__).resolve().parent.parent / "fonts"
BUILTIN = {("Vazirmatn", "700"): "Vazirmatn-Bold.ttf", ("Vazirmatn", "400"): "Vazirmatn-Regular.ttf",
           ("Lalezar", ""): "Lalezar-Regular.ttf", ("Gandom", ""): "Gandom.ttf",
           ("Samim", ""): "Samim-Bold.ttf", ("Sahel", ""): "Sahel-Bold.ttf",
           ("Shabnam", ""): "Shabnam-Bold.ttf", ("Nahid", ""): "Nahid.ttf",
           ("Amiri", ""): "Amiri-Regular.ttf"}


def _rgb(h: Optional[str], default=(0, 0, 0)) -> Tuple[int, int, int]:
    try:
        return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]
    except Exception:
        return default


def find_font(family: str, weight: str, pack: Optional[Dict[str, Any]] = None) -> Path:
    fam = (family or "").split(",")[0].strip().strip("'\"")
    if pack:
        for s in pack.get("styles", []):
            if s.get("fontFile") and fam in (s.get("fontName"), s.get("font")):
                p = Path(pack["dir"]) / "fonts" / s["fontFile"]
                if p.is_file():
                    return p
    name = BUILTIN.get((fam, weight)) or BUILTIN.get((fam, "")) or BUILTIN[("Vazirmatn", "700")]
    return FONTS_DIR / name


def shape(text: str) -> str:
    """Logical Arabic -> visual string PIL can draw (joined letters, RTL order)."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


def _wrap(text: str, font: ImageFont.FreeTypeFont, max_w: float, rtl: bool) -> List[str]:
    words, lines, cur = text.split(), [], ""
    disp = shape if rtl else (lambda t: t)
    for w in words:
        t = (cur + " " + w).strip()
        if cur and font.getlength(disp(t)) > max_w:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines or [""]


def _fit(text: str, path: Path, box_w: int, box_h: int, start: float, rtl: bool):
    size = max(8, int(start))
    while True:
        font = ImageFont.truetype(str(path), size, layout_engine=ImageFont.Layout.BASIC)   # we shape ourselves (same result with or without libraqm)
        lines = _wrap(text, font, box_w * 0.94, rtl)
        lh = int(size * 1.25)
        wid = max(font.getlength(shape(l) if rtl else l) for l in lines)
        if (wid <= box_w * 0.96 and lh * len(lines) <= box_h * 0.96) or size <= 8:
            return font, lines, lh
        size -= 1


def _mask(size, lines, font, lh, cx, y0, rtl, stroke=0) -> Image.Image:
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    for i, ln in enumerate(lines):
        d.text((cx, y0 + i * lh), shape(ln) if rtl else ln, font=font, fill=255, anchor="ma",
               stroke_width=stroke, stroke_fill=255 if stroke else None)
    return m


def draw_text(img: Image.Image, t: Dict[str, Any], pack: Optional[Dict[str, Any]] = None) -> None:
    txt = (t.get("text") or "").strip()
    box = t.get("box") or {}
    if not txt or not box.get("w") or not box.get("h"):
        return
    bx, by, bw, bh = int(box["x"]), int(box["y"]), int(box["w"]), int(box["h"])
    comp = t.get("computed") or {}
    rtl = t.get("dir") == "rtl"
    path = find_font(comp.get("fontFamily", ""), str(comp.get("fontWeight", "")), pack)
    font, lines, lh = _fit(txt, path, bw, bh, float(comp.get("fontSize") or 24) * 1.25, rtl)
    total_h = lh * len(lines)
    pad = 24
    # work on a padded crop so glow/shadow can spill outside the box
    x0, y0 = max(0, bx - pad), max(0, by - pad)
    x1, y1 = min(img.width, bx + bw + pad), min(img.height, by + bh + pad)
    size = (x1 - x0, y1 - y0)
    cx, ty = bx - x0 + bw / 2, by - y0 + (bh - total_h) / 2
    base = img.crop((x0, y0, x1, y1)).convert("RGBA")
    fill_m = _mask(size, lines, font, lh, cx, ty, rtl)

    def paint(layer_mask: Image.Image, color) -> None:
        nonlocal base
        base = Image.alpha_composite(base, Image.merge("RGBA", (*[Image.new("L", size, c) for c in color], layer_mask)))

    sh = t.get("shadow")
    if sh:
        m = ImageChops.offset(fill_m, int(round(sh.get("dx", 2))), int(round(sh.get("dy", 2))))
        if sh.get("blur"):
            m = m.filter(ImageFilter.GaussianBlur(float(sh["blur"])))
        paint(m, _rgb(sh.get("color")))
    gl = t.get("glow")
    if gl:
        r = max(2.0, float(gl.get("radius") or 4))
        m = _mask(size, lines, font, lh, cx, ty, rtl, stroke=int(r // 2)).filter(ImageFilter.GaussianBlur(r))
        paint(m.point(lambda v: min(255, int(v * 1.8))), _rgb(gl.get("color")))
    st = t.get("stroke")
    if st and float(st.get("width") or 0) > 0:
        paint(_mask(size, lines, font, lh, cx, ty, rtl, stroke=max(1, int(round(float(st["width"]))))),
              _rgb(st.get("color")))
    gr = t.get("gradient")
    if gr:
        a, b = _rgb(gr.get("from")), _rgb(gr.get("to"))
        g = Image.new("RGB", size)
        gd = ImageDraw.Draw(g)
        top, span = ty, max(1.0, total_h)
        for yy in range(size[1]):
            k = min(1.0, max(0.0, (yy - top) / span))
            gd.line([(0, yy), (size[0], yy)], fill=tuple(int(a[i] * (1 - k) + b[i] * k) for i in range(3)))
        base = Image.composite(g.convert("RGBA"), base, fill_m)
    else:
        paint(fill_m, _rgb((t.get("color") or {}).get("fill"), (0, 0, 0)))
    img.paste(base.convert("RGB"), (x0, y0))


def render_page(img_path: Path, page: Dict[str, Any], out_path: Path,
                pack: Optional[Dict[str, Any]] = None, quality: int = 92) -> int:
    img = Image.open(img_path).convert("RGB")
    n = 0
    for t in page.get("texts", []):
        if t.get("isTranslated") or t.get("text"):
            draw_text(img, t, pack)
            n += 1
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, quality=quality) if out_path.suffix.lower() in (".jpg", ".jpeg") else img.save(out_path)
    return n
