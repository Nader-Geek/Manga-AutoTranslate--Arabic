# -*- coding: utf-8 -*-
"""User style packs (TypeR "exportedStyles" JSON + font files in one zip) for /chapter.

A pack = a list of named styles (prefixes like "%:", font, size, colour, stroke) plus the font
files. The bot saves one pack per user, maps each bubble tone to a style, and chapter.json then
carries that style's font/colour/stroke. Fonts without Arabic glyphs are never used for Arabic
text (a font from fonts/ replaces them) — the pack's own fonts are only used for source text.
"""
from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

MAX_ZIP = 40 * 1024 * 1024
MAX_FILES = 200
FONT_EXT = (".ttf", ".otf")
ARABIC = "ابتثجحخدذرزسشصضطظعغفقكلمنهويءآأإؤئةى"

TONES = ("normal", "shout", "comedy_shout", "whisper", "thought", "sun_thought", "square_thought",
         "free_text", "system", "monster", "cry", "fear", "broadcast", "letter", "narrator",
         "black", "sfx")
# tone -> style-name guesses (first match wins; case-insensitive, substring)
DEFAULT_MAP: Dict[str, List[str]] = {
    "normal": ["speech"], "thought": ["thinking", "thought"], "sun_thought": ["thinking"],
    "square_thought": ["thinking"], "whisper": ["thinking", "speech"],
    "shout": ["shout"], "comedy_shout": ["stress", "shout"], "monster": ["threat", "shout"],
    "fear": ["terrified", "fear"], "cry": ["stress", "sad"], "black": ["threat"],
    "free_text": ["side text", "out"], "narrator": ["boxes", "narrat"],
    "letter": ["luxury", "letter"], "system": ["system"], "broadcast": ["device", "phone"],
    "sfx": ["hand letters", "sfx", "sound"],
}


class PackError(Exception):
    pass


def _rgb(c: Any, default=(0, 0, 0)):
    if not isinstance(c, dict):
        return default
    g = lambda *k: next((int(c[x]) for x in k if x in c), None)
    r, gg, b = g("r", "red"), g("g", "green"), g("b", "blue")
    return (r, gg, b) if None not in (r, gg, b) else default


def _hex(rgb) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, v)) for v in rgb)


def arabic_coverage(font_path: Path) -> float:
    try:
        from fontTools.ttLib import TTFont
        cm = TTFont(str(font_path), fontNumber=0, lazy=True).getBestCmap() or {}
        return sum(ord(c) in cm for c in ARABIC) / len(ARABIC)
    except Exception:
        return 0.0


def _ps_name(font_path: Path) -> str:
    try:
        from fontTools.ttLib import TTFont
        return TTFont(str(font_path), fontNumber=0, lazy=True)["name"].getDebugName(6) or ""
    except Exception:
        return ""


def install_pack(zip_path: Path, dest: Path) -> Dict[str, Any]:
    """Validate + extract (json and fonts only, flat names) into dest; returns the pack dict."""
    zip_path = Path(zip_path)
    if zip_path.stat().st_size > MAX_ZIP:
        raise PackError("الملف كبير جداً (الحد 40MB).")
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile:
        raise PackError("الملف ليس zip صالحاً.")
    with zf:
        infos = [i for i in zf.infolist() if not i.is_dir()]
        if len(infos) > MAX_FILES:
            raise PackError("عدد الملفات كبير.")
        if sum(i.file_size for i in infos) > 4 * MAX_ZIP:
            raise PackError("حجم الملفات بعد الفك كبير جداً.")
        jsons = [i for i in infos if i.filename.lower().endswith(".json")]
        if not jsons:
            raise PackError("لا يوجد ملف ستايلات (.json) داخل الـ zip.")
        try:
            data = json.loads(zf.read(max(jsons, key=lambda i: i.file_size)).decode("utf-8-sig"))
        except ValueError:
            raise PackError("ملف الستايلات JSON غير صالح.")
        raw_styles = data.get("exportedStyles") if isinstance(data, dict) else None
        if not isinstance(raw_styles, list) or not raw_styles:
            raise PackError("لم أجد `exportedStyles` في ملف الستايلات (المتوقع تصدير ستايلات TypeR).")
        tmp = Path(str(dest) + ".tmp")
        shutil.rmtree(tmp, ignore_errors=True)
        (tmp / "fonts").mkdir(parents=True)
        for i in infos:
            name = Path(i.filename).name
            if name.lower().endswith(FONT_EXT) and not name.startswith("."):
                (tmp / "fonts" / name).write_bytes(zf.read(i))
    by_ps = {}
    for f in sorted((tmp / "fonts").iterdir()):
        by_ps[_ps_name(f)] = f.name
    styles = []
    for s in raw_styles:
        if not isinstance(s, dict) or not s.get("name"):
            continue
        try:
            lt = s["textProps"]["layerText"]
            ts = (lt.get("textStyleRange") or [{}])[0].get("textStyle", {})
        except (KeyError, TypeError, AttributeError):
            ts = {}
        ps = ts.get("fontPostScriptName") or ""
        ffile = by_ps.get(ps)
        stroke = s.get("stroke") or {}
        presets = s.get("sizePresets") or []
        styles.append({
            "name": str(s["name"])[:60], "prefixes": [str(p)[:20] for p in s.get("prefixes") or []][:8],
            "font": ps, "fontName": ts.get("fontName") or ps, "fontFile": ffile,
            "arabic": round(arabic_coverage(tmp / "fonts" / ffile), 2) if ffile else 0.0,
            "size": float(ts.get("size") or (presets[0] if presets else 0) or 0),
            "color": _hex(_rgb(ts.get("color"))),
            "caps": ts.get("fontCaps") == "allCaps",
            "stroke": ({"size": float(stroke.get("size") or 0), "color": _hex(_rgb(stroke.get("color"), (255, 255, 255)))}
                       if stroke.get("enabled") else None)})
    if not styles:
        shutil.rmtree(tmp, ignore_errors=True)
        raise PackError("لا توجد ستايلات صالحة في الملف.")
    pack = {"name": str(data.get("name") or "styles")[:80], "styles": styles,
            "map": auto_map(styles)}
    (tmp / "pack.json").write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.rmtree(dest, ignore_errors=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp.replace(dest)
    return pack


def auto_map(styles: List[Dict[str, Any]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for tone, guesses in DEFAULT_MAP.items():
        for g in guesses:
            hit = next((s["name"] for s in styles if g in s["name"].lower()), None)
            if hit:
                out[tone] = hit
                break
    if "normal" not in out and styles:
        out["normal"] = styles[0]["name"]
    return out


def load_pack(dest: Path) -> Optional[Dict[str, Any]]:
    try:
        pack = json.loads((Path(dest) / "pack.json").read_text(encoding="utf-8"))
        pack["dir"] = str(dest)
        return pack
    except (OSError, ValueError):
        return None


def set_mapping(dest: Path, tone: str, style_name: str) -> Dict[str, Any]:
    pack = load_pack(dest)
    if pack is None:
        raise PackError("لا توجد حزمة ستايلات محفوظة. ارفع واحدة بـ `/styles upload`.")
    if tone not in TONES:
        raise PackError("نوع غير معروف.")
    if style_name not in {s["name"] for s in pack["styles"]}:
        raise PackError("اسم الستايل غير موجود في الحزمة.")
    pack.pop("dir", None)
    pack["map"][tone] = style_name
    (Path(dest) / "pack.json").write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")
    return load_pack(dest)


def style_for(pack: Dict[str, Any], tone: str, kind: str = "") -> Optional[Dict[str, Any]]:
    m = pack.get("map") or {}
    key = "sfx" if kind == "sfx" and "sfx" in m else ("narrator" if kind == "narration" and tone in ("normal", "") and "narrator" in m else (tone or "normal"))
    name = m.get(key) or m.get("normal")
    return next((s for s in pack["styles"] if s["name"] == name), None)


def summary(pack: Dict[str, Any]) -> str:
    inv = {}
    for t, n in (pack.get("map") or {}).items():
        inv.setdefault(n, []).append(t)
    lines = [f"**{pack['name']}** — {len(pack['styles'])} ستايل"]
    for s in pack["styles"]:
        ar = "✅" if s["arabic"] >= 0.9 else "❌"
        used = ("→ " + ", ".join(inv[s["name"]])) if s["name"] in inv else ""
        pre = " ".join(f"`{p}`" for p in s["prefixes"][:2])
        lines.append(f"• {s['name']} {pre} — {s['font'] or '?'} {s['size']:g}px عربي:{ar} {used}")
    return "\n".join(lines)[:3900]
