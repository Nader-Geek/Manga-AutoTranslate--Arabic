#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مترجمِ خودکارِ مانگا/مانهوا به فارسی — لودرِ پلاگینی

این فایل دیگر غول‌پیکر نیست: بدنهٔ اصلیِ برنامه در پوشهٔ
«manga_sections/» است — هر موضوع یک فایل (پایه/پرامپتها، نصب،
مدلها، OCR، سرویسها، و ۷ قطعهٔ کلاسِ MangaTranslator + CLI).
این لودر همه را بهترتیبِ شمارهٔ فایل در «یک» فضایِ نام بارگذاری
میکند — یعنی رفتار عینِ همان manga.pyیِ تکیِ قدیمی است:

    manga_sections/00_base.py → هدر، نسخه، importها، پرامپتها
    manga_sections/10_install.py → نصبِ وابستگیها + وضعیتِ توقف
    manga_sections/20_models.py → ORT/سختافزار، LaMa، تشخیص، مدلها
    manga_sections/30_ocr.py → موتورهای OCR
    manga_sections/40_api_text.py → سرویسهای AI + ابزارهای متن
    manga_sections/50_translator.py→ MangaTranslator (شروعِ کلاس)
    manga_sections/60_input.py → ورودی/دانلود
    manga_sections/70_extract.py → استخراجِ متن + دوخت/برشِ صفحهها
    manga_sections/80_translate.py → ترجمهٔ AI
    manga_sections/85_cleanup.py → پاکسازی (یکجا)
    manga_sections/90_render.py → رندرِ متن + قالبهای خروجی
    manga_sections/95_run.py → run() — پایانِ کلاس
    manga_sections/99_cli.py → build_arg_parser و main()

ویرایشِ کد فقط در manga_sections/ — نگهبانِ همخوانی:
    python scripts/build_manga.py --check

عملکرد: خروجیِ ترکیبی یک بار کامپایل و در کشِ marshal
(manga_sections/__pycache__/) ذخیره میشود — دفعاتِ بعدی بارگذاریِ
بخشها تقریباً رایگان است (~میلیثانیه، نه نیمثانیه).

خودترمیمیِ بخشها (در حالی که اپ سالم کار میکند):
  • غایب/ناقص → همینجا از میرورهایِ ریپو دانلود میشود (blocking،
    با ضرب‌الاجل) و همان لحظه اجرا میشود — دیگر «Clear Data» لازم
    نیست و پنجرهٔ شکستهٔ بینِ نصبِ لودر و رسیدنِ بخشها (مسابقهٔ
    آپدیترِ پس‌زمینه) خودش ترمیم میشود.
  • کهنه (نسخهٔ 00_base < نسخهٔ لودر — گوشیِ کاربر با بخشهایِ
     گیر کرده بود) → تازهسازی در «رشتهٔ پس‌زمینه»: همین
    اجرا با نسخهٔ موجود کار میکند، نسخهٔ تازه از اجرای بعدی فعال
    میشود (بدونِ قفلِ شروعِ اپ). ترتیبِ commit: 00_base.py «آخر»
    تا شکستِ وسطِ راه = نسخهٔ کهنه = تلاشِ دوباره، نه نسخهٔ مخلوط.
"""
from __future__ import annotations

import hashlib
import marshal
import os as _os
import re as _re
import sys as _sys
import time as _time

# همگام با APP_VER در manga_sections/00_base.py —
# «scripts/build_manga.py --check» ناهمخوانی را رد میکند.
APP_VER = "1.14.253"

_HERE = _os.path.dirname(_os.path.abspath(__file__))
_SECTIONS_DIR = _os.path.join(_HERE, "manga_sections")
_MANIFEST_PATH = _os.path.join(_SECTIONS_DIR, "MANIFEST")
_CACHE_DIR = _os.path.join(_SECTIONS_DIR, "__pycache__")
_CACHE_PREFIX = "manga_loader_"
_CACHE_MAGIC = b"MGLDR\x01"

# همان زنجیرهٔ میرورهایِ لانچرِ اندروید (raw گیت‌هاب →
# jsDelivr که در ایران باز است → gh-proxy) — فقط برای خودترمیمی.
_UPDATE_MIRRORS = (
    "https://raw.githubusercontent.com/"
    "amirwolf512k/Manga-AutoTranslate/main/",
    "https://cdn.jsdelivr.net/gh/"
    "amirwolf512k/Manga-AutoTranslate@main/",
    "https://gh-proxy.com/raw.githubusercontent.com/"
    "amirwolf512k/Manga-AutoTranslate/main/",
)
_REFRESH_STAMP = _os.path.join(_HERE, ".manga_sections_refresh")
_STALE_RETRY_S = 600.0   # تازهسازیِ کهنه: حداکثر یک تلاش در ۱۰ دقیقه
_MISSING_RETRY_S = 120.0  # بخشِ غایب/ناقص: یک تلاش در ۲ دقیقه
_FETCH_DEADLINE_S = 100.0  # سقفِ کلِ دانلودِ blocking

_STRIP_START = "# BUILD-STRIP-START"
_STRIP_END = "# BUILD-STRIP-END"

# این فایل لودر است — بدنهٔ کلاس/توابعِ واقعی از بخشها میآید.
_MANGA_LOADER = True
_SELF_UPDATE_TRIED = False

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

def _ver_tuple(v: str):
    try:
        return tuple(int(x) for x in str(v or "0").strip().split("."))
    except ValueError:
        return (0, )

def _ver_cmp(a: str, b: str) -> int:
    ta, tb = _ver_tuple(a), _ver_tuple(b)
    for i in range(max(len(ta), len(tb))):
        xa = ta[i] if i < len(ta) else 0
        xb = tb[i] if i < len(tb) else 0
        if xa != xb:
            return 1 if xa > xb else -1
    return 0

def _sections_app_ver() -> str:
    """نسخهٔ بخشهایِ نصب‌شده — APP_VER داخلِ 00_base.py (بدون exec)."""
    try:
        with open(_os.path.join(_SECTIONS_DIR, "00_base.py"),
                  "r", encoding="utf-8") as f:
            m = _re.search(r'APP_VER\s*=\s*"([^"]+)"', f.read(8192))
        return m.group(1) if m else "0"
    except Exception:
        return "0"

def _fetch_bytes(url: str, timeout: float):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def _fetch_mirrors(name: str, min_size: int, timeout: float, deadline: float):
    last = None
    for base in _UPDATE_MIRRORS:
        if _time.time() > deadline:
            break
        try:
            data = _fetch_bytes(base + name, timeout)
            if len(data) < min_size:
                raise RuntimeError("فایل ناقص (%d بایت)" % len(data))
            return data
        except Exception as e:
            last = e
    raise last if last else RuntimeError("مهلتِ دانلود تمام شد")

def _manifest_names_remote(deadline: float):
    """(فهرستِ نامها، بایتهایِ خودِ MANIFEST) از میرورها — نامِ تودرتو
    (manga_sections/00_base.py) هم پذیرفته میشود؛ فقط نامِ پایه
    میخواهیم؛ لودر پوشه را از قبل میشناسد."""
    man = _fetch_mirrors("manga_sections/MANIFEST", 8, 12.0, deadline)
    names = [ln.strip() for ln in man.decode("utf-8", "ignore").split("\n")
             if ln.strip() and not ln.strip().startswith("#")
             and ln.strip().endswith(".py")]
    return [_os.path.basename(n) for n in names], man

def _throttle_ok(min_seconds: float) -> bool:
    """تلاشِ تازهسازی حداکثر هر min_seconds ثانیه یک بار (mtimeِ مهر).
    مهر «بیرونِ» پوشهٔ بخشهاست تا تلاشِ ناموفیف پوشهٔ خالی نسازد."""
    try:
        age = _time.time() - _os.path.getmtime(_REFRESH_STAMP)
        if age < min_seconds:
            return False
    except OSError:
        pass
    try:
        with open(_REFRESH_STAMP, "w", encoding="utf-8") as f:
            f.write(_time.strftime("%Y-%m-%d %H:%M:%S"))
    except OSError:
        return False
    return True

def _fetch_sections(deadline: float) -> bool:
    """همهٔ بخشها را stage میکند و فقط بعد ازِ موفقیتِ «همه» commit
    میکند (00_base.py آخر — شکستِ وسطِ راه = کهنه میماند = تلاشِ
    دوباره). برگرداندنِ True یعنی بخشها اکنون کامل و همخواناند."""
    try:
        names, man_raw = _manifest_names_remote(deadline)
    except Exception:
        return False
    if not names:
        return False
    try:
        _os.makedirs(_SECTIONS_DIR, exist_ok=True)
    except OSError:
        return False
    staged = []
    try:
        for n in names:
            if _time.time() > deadline:
                raise RuntimeError("مهلتِ دانلود تمام شد")
            data = _fetch_mirrors("manga_sections/" + n, 64, 25.0, deadline)
            tmp = _os.path.join(_SECTIONS_DIR, n + ".new")
            with open(tmp, "wb") as f:
                f.write(data)
            staged.append((n, tmp))
    except Exception:
        for _n, tmp in staged:
            try:
                _os.remove(tmp)
            except OSError:
                pass
        return False
# commit: همه چیز آماده است — MANIFEST اول (سفیدنامه)، بعد بخشها
# و 00_base.py آخر (نشانگرِ نسخه).
    try:
        man_tmp = _MANIFEST_PATH + ".new"
        with open(man_tmp, "wb") as f:
            f.write(man_raw)
        _os.replace(man_tmp, _MANIFEST_PATH)
    except OSError:
        pass
    ordered = [x for x in staged if x[0] != "00_base.py"]
    if any(x[0] == "00_base.py" for x in staged):
        ordered.append(next(x for x in staged if x[0] == "00_base.py"))
    for n, tmp in ordered:
        try:
            _os.replace(tmp, _os.path.join(_SECTIONS_DIR, n))
        except OSError:
            pass
# زامبی: فایلِ عددیِ خارج از MANIFESTِ جدید
    try:
        for n in _os.listdir(_SECTIONS_DIR):
            if n.endswith(".py") and n[:1].isdigit() and n not in names:
                try:
                    _os.remove(_os.path.join(_SECTIONS_DIR, n))
                except OSError:
                    pass
    except OSError:
        pass
    return True

def _self_heal_blocking(reason: str):
    """بخشهایِ غایب/ناقص را همین لحظه دانلود میکند — فقط وقتی صدا
    زده میشود که بدونِ آن موتور اصلاً بالا نمیآید (blocking، با
    ضرب‌الاجل). یک تلاش در هر فراخوانیِ import + مهرِ ۲دقیقهای."""
    global _SELF_UPDATE_TRIED
    if _SELF_UPDATE_TRIED:
        return
    if not _throttle_ok(_MISSING_RETRY_S):
        return
    _SELF_UPDATE_TRIED = True
    print("[manga] 🔧 manga_sections/ %s — تلاش برای دانلودِ خودترمیم…"
          % reason, flush=True)
    ok = _fetch_sections(_time.time() + _FETCH_DEADLINE_S)
    print("[manga] %s" % ("✅ بخشهایِ موتور دانلود شد — ادامه میدهم."
                          if ok else
                          "❌ دانلود ناموفق (اینترنت؟) — پیامِ خطا در ادامه…"),
          flush=True)

def _sections_present() -> bool:
    """پوشهٔ بخشها واقعاً محتوا دارد؟ — پوشهٔ «خالی» (باقیماندهٔ تلاشِ
    ناموفیفِ خودترمیمی/آپدیتر) همان «غایب» تلقی میشود تا موتورِ خالی
    و بی‌صدا بالا نیاید."""
    if not _os.path.isdir(_SECTIONS_DIR):
        return False
    if _os.path.isfile(_MANIFEST_PATH):
        return True
# بدونِ MANIFEST: نصبِ دستی — فقط با فایلِ عددیِ واقعی معتبر است
    try:
        return any(n.endswith(".py") and n[:1].isdigit()
                   for n in _os.listdir(_SECTIONS_DIR))
    except OSError:
        return False

def _maybe_refresh_stale_async():
    """بخشهایِ «کهنه» (نسخهٔ 00_base < لودر) را در پس‌زمینه تازه
    میکند — همین اجرا با نسخهٔ موجود ادامه مییابد (بدونِ قفل) و
    نسخهٔ تازه از import بعدی فعال میشود. فقط با مهرِ ۱۰دقیقهای."""
    try:
        if not _sections_present():
            return  # غایب/خالی = مسیرِ blocking در _section_names
        listed = _read_manifest()
        if listed is None:
            return  # نصبِ دستیِ بدونِ MANIFEST — دست نمی‌زنیم
        missing = [n for n in listed
                   if not _os.path.isfile(_os.path.join(_SECTIONS_DIR, n))]
        if missing:
            return  # ناقص = مسیرِ blocking
        if _ver_cmp(_sections_app_ver(), APP_VER) >= 0:
            return  # هماهنگ یا جلوتر از لودر — کاری نیست
        if not _throttle_ok(_STALE_RETRY_S):
            return
    except Exception:
        return

    def _worker():
        try:
            ok = _fetch_sections(_time.time() + 180.0)
            if ok:
                print("[manga] 🔄 بخشهایِ موتور تازه شد (v%s) — "
                      "از اجرای بعدی فعال میشود." % _sections_app_ver(),
                      flush=True)
            else:
                print("[manga] ⚠ تازهسازیِ بخشها ناموفق — با همین نسخهٔ "
                      "موجود ادامه میدهم.", flush=True)
        except Exception:
            pass

    try:
        import threading
        threading.Thread(target=_worker, daemon=True).start()
    except Exception:
        pass

def _section_names():
    """نامهای بخش: MANIFEST اگر هست، وگرنه همهٔ *.pyهای عددی پوشه."""
    if not _sections_present():
        _self_heal_blocking("غایب")
        if not _sections_present():
            _sys.stderr.write(
                "❌ پوشهٔ manga_sections/ کنارِ manga.py پیدا نشد —\n"
                "   بدنهٔ موتور در همان پوشه است و فایلِ manga.py\n"
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
        _self_heal_blocking("ناقص (MANIFEST میخواهد: %s)" % ", ".join(missing))
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
    _maybe_refresh_stale_async()
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
