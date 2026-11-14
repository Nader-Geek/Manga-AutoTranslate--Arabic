# -*- coding: utf-8 -*-
"""Package a finished job as  chapter.zip = images/ (cleaned pages) + chapter.json.

chapter.json follows the "manhuarmtl-v1" layout (pages -> texts with box/color/layout/computed),
filled from typer_job.json. Pages are NOT stitched, so stitchMode is "none" and every page is
its own image. Colours are measured on the cleaned page (the bubble fill is the background);
font sizes are estimates fitted to the bubble box — a reader/editor may refine them.
"""
from __future__ import annotations

import json
import math
import re
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA = "manhuarmtl-v1"
FONT_FAMILY = "Vazirmatn, sans-serif"


def slugify(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", text or "").strip("-").lower()
    return s[:80]


def _bg_and_fill(img, rect) -> Dict[str, Any]:
    """Background = median colour of the cleaned box; fill = black/white for best contrast."""
    try:
        import numpy as np
        x, y, w, h = rect
        crop = np.asarray(img.crop((x, y, x + max(1, w), y + max(1, h))).convert("RGB"))
        if crop.size == 0:
            raise ValueError
        med = [int(v) for v in np.median(crop.reshape(-1, 3), axis=0)]
        lum = 0.299 * med[0] + 0.587 * med[1] + 0.114 * med[2]
        fill = (8, 8, 8) if lum > 140 else (245, 245, 245)
        return {"fill": "#%02x%02x%02x" % fill, "outline": None,
                "background": "#%02x%02x%02x" % tuple(med), "confidence": 0.7}, fill
    except Exception:
        return {"fill": None, "outline": None, "background": None, "confidence": None}, (0, 0, 0)


def fit_font_size(text: str, w: int, h: int, lo: int = 8, hi: int = 80) -> float:
    """Largest font size whose wrapped lines (0.55em per char, 1.2 line height) fit w x h."""
    n = max(1, len((text or "").strip()))
    best = lo
    for fs in range(min(hi, max(lo, int(min(w, h)))), lo - 1, -1):
        per_line = max(1, int(w // (0.55 * fs)))
        lines = math.ceil(n / per_line)
        if lines * 1.2 * fs <= h:
            return float(fs)
    return float(best)


def build_chapter_json(typer: Dict[str, Any], pages_dir: Path, *, title: str, source_lang: str,
                       translated: bool, target_lang: str = "ar",
                       source_names: Optional[Dict[int, str]] = None) -> Dict[str, Any]:
    from PIL import Image
    pages_out: List[Dict[str, Any]] = []
    stitched: List[Dict[str, Any]] = []
    total = done = 0
    for pg in typer.get("pages", []):
        idx = int(pg.get("index", len(pages_out)))
        fname = pg.get("file") or f"page_{idx + 1:03d}.jpg"
        out_name = f"page-{idx + 1:03d}{Path(fname).suffix.lower()}"
        w, h = int(pg.get("width") or 0), int(pg.get("height") or 0)
        try:
            img = Image.open(pages_dir / fname)
            img.load()
            w, h = img.size
        except Exception:
            img = None
        texts = []
        for r in pg.get("regions") or []:
            src = (r.get("source") or "").strip()
            tr = (r.get("text") or "").strip() if translated else ""
            shown = tr if translated else src
            x, y, bw, bh = [int(v) for v in (r.get("rect") or [0, 0, 0, 0])]
            color, rgb = _bg_and_fill(img, (x, y, bw, bh)) if img else (
                {"fill": None, "outline": None, "background": None, "confidence": None}, (0, 0, 0))
            fs = fit_font_size(shown, bw, bh)
            is_tr = bool(translated and tr)
            total += 1
            done += 1 if is_tr else 0
            tone = r.get("tone") or "normal"
            texts.append({
                "text": shown, "sourceText": src, "displayText": shown, "isTranslated": is_tr,
                "lang": None if is_tr else source_lang, "dir": "rtl" if is_tr else "ltr",
                "box": {"x": x, "y": y, "w": bw, "h": bh},
                "kind": r.get("kind") if r.get("kind") in ("dialogue", "sfx", "narration", "thought") else "",
                "style": [] if tone == "normal" else [str(tone)],
                "color": color,
                "layout": {"baseFontSize": round(fs * 1.36, 2), "maxWidth": None,
                           "capSize": None, "pageWidth": w},
                "computed": {"fontFamily": FONT_FAMILY, "fontSize": fs, "fontWeight": "700",
                             "fontStyle": "normal", "textTransform": "none", "textAlign": "center",
                             "color": "rgb(%d, %d, %d)" % rgb, "lineHeight": f"{fs * 1.2:.1f}px",
                             "letterSpacing": "normal"},
                "stroke": None})
        pages_out.append({
            "index": idx, "sourceFilename": (source_names or {}).get(idx) or pg.get("origin") or "",
            "imageFilename": out_name, "width": w, "height": h, "textCount": len(texts),
            "texts": texts, "sourcePageIndexes": [idx], "imageSource": "bot-clean"})
        stitched.append({"filename": out_name, "width": w, "height": h, "pageIndexes": [idx]})
    return {
        "schema": SCHEMA, "title": title, "mangaSlug": slugify(title), "chapterSlug": "",
        "url": "", "extractedAt": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "userAgent": "manga-autotranslate-bot", "pageCount": len(pages_out),
        "targetLang": target_lang, "displayField": "text",
        "translation": {"sourceLang": source_lang, "active": bool(translated),
                        "translatedTexts": done, "totalTexts": total,
                        "insufficient": bool(translated and total and done < total * 0.8)},
        "stitchMode": "none", "stitchedImages": stitched, "failedPages": [], "pages": pages_out}


def build_chapter_zip(typer_dir: Path, out_zip: Path, *, title: str, source_lang: str = "en",
                      translated: bool = False, target_lang: str = "ar",
                      source_names: Optional[Dict[int, str]] = None) -> Dict[str, Any]:
    """typer_dir holds the cleaned pages + typer_job.json (with 'text' filled when translated).
    Returns the chapter.json dict that was written into the zip."""
    typer = json.loads((Path(typer_dir) / "typer_job.json").read_text(encoding="utf-8"))
    chapter = build_chapter_json(typer, Path(typer_dir), title=title, source_lang=source_lang,
                                 translated=translated, target_lang=target_lang,
                                 source_names=source_names)
    out_zip = Path(out_zip)
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_STORED) as zf:
        for pg, entry in zip(typer.get("pages", []), chapter["pages"]):
            src = Path(typer_dir) / (pg.get("file") or "")
            if src.is_file():
                zf.write(src, f"images/{entry['imageFilename']}")   # images are already compressed
        zf.writestr("chapter.json", json.dumps(chapter, ensure_ascii=False, indent=2))
    return chapter


async def make_chapter(typer_dir: Path, out_zip: Path, *, title: str, opts: Dict[str, Any],
                       ollama_url: str, model: str, num_ctx: int = 8192,
                       on_progress=None) -> Dict[str, Any]:
    """Optionally translate the extracted texts (opts['translate']) then write chapter.zip.
    Translation failures never abort: untranslated lines keep their source text."""
    typer_dir = Path(typer_dir)
    job_path = typer_dir / "typer_job.json"
    typer = json.loads(job_path.read_text(encoding="utf-8"))
    translated = bool(opts.get("translate"))
    src = opts.get("ocr", "en")
    if translated:
        from .providers import API_PROVIDERS, api_key
        from .translate_ollama import translate_texts
        prov = opts.get("provider") or "ollama"
        key = ""
        if prov in API_PROVIDERS:
            key = api_key(prov)
            if not key:
                raise RuntimeError(f"مفتاح {prov} غير مضبوط على السيرفر")
            ollama_url = API_PROVIDERS[prov]["base"]
            model = opts.get("api_model") or API_PROVIDERS[prov]["model"]
        regs = [r for pg in typer.get("pages", []) for r in (pg.get("regions") or [])
                ]
        outs = await translate_texts(
            [(r.get("source") or "") for r in regs], url=ollama_url, model=model, src=src,
            dialect=opts.get("dialect", "msa"), num_ctx=num_ctx, on_progress=on_progress,
            api_key=key)
        for r, t in zip(regs, outs):
            r["text"] = t
        typer["translated"] = True
        job_path.write_text(json.dumps(typer, ensure_ascii=False, indent=1), encoding="utf-8")
    return build_chapter_zip(typer_dir, out_zip, title=title, source_lang=src,
                             translated=translated)
