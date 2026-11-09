#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مترجمِ خودکارِ مانگا/مانهوا به فارسی — لودرِ پلاگینی (v1.14.251+)

این فایل دیگر غول‌پیکر نیست: بدنهٔ اصلیِ برنامه در پوشهٔ
«manga_sections/» است — هر موضوع یک فایل (پایه/پرامپتها، نصب،
مدلها، OCR، سرویسها، و ۷ قطعهٔ کلاسِ MangaTranslator + CLI).
این لودر همه را بهترتیبِ شمارهٔ فایل در «یک» فضایِ نام بارگذاری
میکند — یعنی رفتار عینِ همان manga.pyیِ تکیِ قدیمی است:

    manga_sections/00_base.py      → هدر، نسخه، importها، پرامپتها
    manga_sections/10_install.py   → نصبِ وابستگیها + وضعیتِ توقف
    manga_sections/20_models.py    → ORT/سختافزار، LaMa، تشخیص، مدلها
    manga_sections/30_ocr.py       → موتورهای OCR
    manga_sections/40_api_text.py  → سرویسهای AI + ابزارهای متن
    manga_sections/50_translator.py→ MangaTranslator (شروعِ کلاس)
    manga_sections/60_input.py     → ورودی/دانلود
    manga_sections/70_extract.py   → استخراجِ متن + دوخت/برشِ صفحهها
    manga_sections/80_translate.py → ترجمهٔ AI
    manga_sections/85_cleanup.py   → پاکسازی (یکجا)
    manga_sections/90_render.py    → رندرِ متن + قالبهای خروجی
    manga_sections/95_run.py       → run() — پایانِ کلاس
    manga_sections/99_cli.py       → build_arg_parser و main()

ویرایشِ کد فقط در manga_sections/ — نگهبانِ همخوانی:
    python scripts/build_manga.py --check

عملکرد: خروجیِ ترکیبی یک بار کامپایل و در کشِ marshal
(manga_sections/__pycache__/) ذخیره میشود — دفعاتِ بعدی بارگذاریِ
بخشها تقریباً رایگان است (~میلیثانیه، نه نیمثانیه).
"""
from __future__ import annotations

import hashlib
import marshal
import os as _os
import sys as _sys

# همگام با APP_VER در manga_sections/00_base.py —
# «scripts/build_manga.py --check» ناهمخوانی را رد میکند.
APP_VER = "1.14.251"

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_SECTIONS_DIR = _os.path.join(_HERE, "manga_sections")
_MANIFEST_PATH = _os.path.join(_SECTIONS_DIR, "MANIFEST")
_CACHE_DIR = _os.path.join(_SECTIONS_DIR, "__pycache__")
_CACHE_PREFIX = "manga_loader_"
_CACHE_MAGIC = b"MGLDR\x01"

_STRIP_START = "# BUILD-STRIP-START"
_STRIP_END = "# BUILD-STRIP-END"

# این فایل لودر است — بدنهٔ کلاس/توابعِ واقعی از بخشها میآید.
_MANGA_LOADER = True


def _section_sort_key(name: str):
    i = 0
    while i < len(name) and name[i].isdigit():
        i += 1
    return (int(name[:i]) if i else 10 ** 9, name)


def _read_manifest():
    """فهرستِ بخشها از MANIFEST — سفیدنامهٔ بارگذاری (ضدِ فایلِ زامبی)."""
    try:
        with open(_MANIFEST_PATH, "r", encoding="utf-8") as f:
            names = [ln.strip() for ln in f.read().split("\n")]
    except OSError:
        return None
    return [n for n in names
            if n and not n.startswith("#") and n.endswith(".py")]


def _section_names():
    """نامهای بخش: MANIFEST اگر هست، وگرنه همهٔ *.pyهای عددی پوشه."""
    if not _os.path.isdir(_SECTIONS_DIR):
        _sys.stderr.write(
            "❌ پوشهٔ manga_sections/ کنارِ manga.py پیدا نشد —\n"
            "   از v1.14.251 بدنهٔ موتور در همان پوشه است و فایلِ manga.py\n"
            "   بهتنهایی کافی نیست. نسخهٔ کاملِ برنامه را بگیرید:\n"
            "   https://github.com/amirwolf512k/Manga-AutoTranslate\n")
        # RuntimeError (نه SystemExit) تا گاردهایِ except Exception در
        # bridge/health آپدیتگرها هم آن را بگیرند و با وقار گزارش کنند
        raise RuntimeError("manga_sections/ پیدا نشد — لودرِ manga.py محتوا ندارد")
    on_disk = [n for n in _os.listdir(_SECTIONS_DIR)
               if n.endswith(".py") and n[:1].isdigit()]
    listed = _read_manifest()
    if listed is None:
        return sorted(on_disk, key=_section_sort_key)
    missing = [n for n in listed
               if not _os.path.isfile(_os.path.join(_SECTIONS_DIR, n))]
    if missing:
        _sys.stderr.write(
            "❌ manga_sections/MANIFEST این فایلها را میخواهد ولی نیستند: %s\n"
            "   (ریپو/آپدیت ناقص است — دوباره بگیرید)\n" % ", ".join(missing))
        raise RuntimeError("بخشهایِ MANIFEST غایبند: %s" % ", ".join(missing))
    # فایلِ عددیِ خارج از سفیدنامه = زامبیِ آپدیتِ قبلی — نادیده + هشدار
    extra = [n for n in on_disk if n not in listed]
    if extra:
        print("[manga] ⚠ بخشهایِ خارج از MANIFEST نادیده گرفته شدند: %s"
              % ", ".join(sorted(extra)), flush=True)
    return sorted(listed, key=_section_sort_key)


def _read_stripped(path: str):
    """محتوای بخش بدونِ بلاکهایِ BUILD-STRIP (سربرگها/کلاسِ پوششی)."""
    with open(path, "r", encoding="utf-8", newline="") as f:
        lines = f.read().split("\n")
    out, stripping = [], False
    for ln in lines:
        if ln.strip() == _STRIP_START:
            stripping = True
            continue
        if stripping:
            if ln.strip() == _STRIP_END:
                stripping = False
            continue
        out.append(ln)
    if out and out[-1] == "":
        out = out[:-1]
    return out


def _combined():
    """(source, نگاشتِ شمارهٔ خط ← نامِ بخش) — عینِ بیلدِ تک‌فایلی."""
    parts, line_map, lineno = [], [], 1
    for name in _section_names():
        lines = _read_stripped(_os.path.join(_SECTIONS_DIR, name))
        line_map.append((lineno, name))
        lineno += len(lines) + 1
        parts.append("\n".join(lines) + "\n")
    return "".join(parts), line_map


def _section_for_line(line_map, lineno: str):
    best = None
    for start, name in line_map:
        if int(lineno) >= start:
            best = name
        else:
            break
    return best


def _cache_key(src: str, names):
    h = hashlib.sha256()
    h.update(_CACHE_MAGIC)
    h.update((_sys.implementation.cache_tag or "?").encode("ascii", "ignore"))
    h.update(b"|")
    h.update("\x00".join(names).encode("utf-8"))
    h.update(b"|")
    h.update(src.encode("utf-8"))
    return h.hexdigest()[:16]


def _load_cached(key: str):
    """کدِ کامپایلشده از کشِ marshal — سریع و ارزان."""
    try:
        with open(_os.path.join(_CACHE_DIR, _CACHE_PREFIX + key + ".marshal"),
                  "rb") as f:
            if f.read(6) != _CACHE_MAGIC:
                return None
            return marshal.loads(f.read())
    except Exception:
        return None


def _save_cache(key: str, code):
    try:
        _os.makedirs(_CACHE_DIR, exist_ok=True)
        path = _os.path.join(_CACHE_DIR, _CACHE_PREFIX + key + ".marshal")
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(_CACHE_MAGIC)
            f.write(marshal.dumps(code))
        _os.replace(tmp, path)
        # کشهای کهنه را پاک کن
        for n in _os.listdir(_CACHE_DIR):
            if n.startswith(_CACHE_PREFIX) and n != _CACHE_PREFIX + key + ".marshal":
                try:
                    _os.remove(_os.path.join(_CACHE_DIR, n))
                except OSError:
                    pass
    except Exception:
        pass  # دیرکتوریِ فقط-خواندنی و… — بی‌خطر: دفعهٔ بعد دوباره کامپایل میشود


def _load_sections():
    src, line_map = _combined()
    names = [n for _, n in line_map]
    key = _cache_key(src, names)
    code = _load_cached(key)
    if code is None:
        try:
            code = compile(src, __file__, "exec")
        except SyntaxError as e:
            sec = _section_for_line(line_map, e.lineno or 1)
            _sys.stderr.write(
                "❌ خطای سینتکس در manga_sections/%s (خطِ %s در خروجیِ ترکیبی)\n"
                "   جزئیات: %s\n   برایِ بازبینی: python scripts/build_manga.py --check\n"
                % (sec or "?", e.lineno, e.msg))
            raise
        _save_cache(key, code)
    # یک فضایِ نام — عینِ همان تک‌فایلِ قدیمی: همهٔ تعریفها همینجا
    # مینشینند و import manga / from manga import … بی‌تغییر کار میکند.
    exec(code, globals())


_load_sections()
