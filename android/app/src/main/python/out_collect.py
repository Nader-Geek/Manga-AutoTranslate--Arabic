# -*- coding: utf-8 -*-
"""جمع‌آوریِ خروجیهایِ یک ران برای «نمایش/دانلود» — جدا از bridge تا
هم تستپذیر باشد هم بدونِ importهایِ سنگین روی گوشی بارگذاری شود.

(v1.14.276) دو فیکسِ بحرانی:
۱) مسیرِ کش: موتور از v275 کشِ «مستقل از فرمت» دارد — پسوندِ
   خروجی از نامِ کش کنار میرود (res.pdf → res.cache). bridge قبلاً
   «res.pdf.cache» میساخت که هیچ‌وقت وجود نداشت → جمعآوریِ کش همیشه
   خالی بود → فالبکِ پوشهٔ live.
۲) نشتِ دیباگ به نمایشِ اصلی: در فالبک، فایلهایِ پوشهٔ live_debug
   (عکسهایِ سوختهٔ دیباگ — در «نامِ فایلشان» debug نیست!) به‌عنوانِ
   خروجیِ نهایی جمع میشدند و صفحههایِ دیباگ وسطِ نمایشِ اصلی
   میآمدند، در حالی که لیستِ دیباگ (دکمهٔ سوئیچ) خالی میماند.
   حالا «پوشه» هم چک میشود: هر پوشهٔ debugدار = دیباگ.

(v1.14.277) نشانگرِ «خروجیِ همین ران» — موتور در کش، last_out.json
می‌نویسد (نامِ پوشهٔ outِ همین ران). وقتی هست، تصاویرِ نهایی فقط از
همان پوشه جمع میشوند تا خروجیِ فقط-پاکسازی با ترجمهٔ قبلی و
سبکهایِ پاکسازیِ قدیمی قاطی نشود (خواستهٔ سازنده: «اگ حالت
پاکسازی گذاشتم فقط پاکسازیش نشون بده نه دیتای قبلی»). نبودِ
نشانگر (کشِ قدیمی) = رفتارِ قبلی.
"""
import json
import os
import re

_IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp")
# پسوندهایی که موتور در نامِ کش کنار میگذارد (MangaTranslator._cache_dir_for)
_KNOWN_OUT_EXTS = (".pdf", ".zip", ".html", ".psd",
                   ".webp", ".png", ".jpg", ".jpeg")
_ORIG_DIRS = ("src", "normalized", "stitched")


def cache_dir_of(out_file_path: str) -> str:
    """همانِ MangaTranslator._cache_dir_for — مستقل از فرمتِ خروجی."""
    p = str(out_file_path or "")
    root, ext = os.path.splitext(p)
    if ext.lower() in _KNOWN_OUT_EXTS:
        return root + ".cache"
    return p + ".cache"


def _natkey(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def last_out_dir(cache):
    """پوشهٔ خروجیِ آخرین ران — نشانگرِ last_out.json موتور (v275+).
    برگشت: مسیرِ پوشه یا "" (نبود/خراب)."""
    try:
        with open(os.path.join(cache, "last_out.json"),
                  encoding="utf-8") as fh:
            name = str((json.load(fh) or {}).get("dir") or "").strip()
        if (name and name not in (".", "..")
                and "/" not in name and os.sep not in name):
            p = os.path.join(cache, name)
            if os.path.isdir(p):
                return p
    except Exception:
        pass
    return ""


def latest_out_dir(cache):
    """جدیدترین پوشهٔ out* با تصویر — فالبکِ نبودِ last_out.json
    (v1.14.279): قبلاً همهٔ پوشههایِ out* جمع میشدند → سبکهایِ
    پاکسازیِ قدیمی/جدید (opencv + lama) با هم نمایش داده میشدند؛
    حالا فقط همان که تازهتر است (mtime)."""
    best, best_mt = "", -1.0
    try:
        for name in os.listdir(cache):
            if name != "out" and not name.startswith("out_"):
                continue
            p = os.path.join(cache, name)
            if not os.path.isdir(p):
                continue
            try:
                if not any(f.lower().endswith(_IMG_EXTS)
                           for f in os.listdir(p)):
                    continue
            except Exception:
                continue
            mt = os.path.getmtime(p)
            if mt > best_mt:
                best, best_mt = p, mt
    except Exception:
        return ""
    return best


def collect(out_file_path: str, job_out: str):
    """(imgs, dbg) — خروجیهایِ نهایی و دیباگِ همین ران، مرتبشده."""
    imgs, dbg = [], []
    cache = cache_dir_of(out_file_path)
    last = last_out_dir(cache) or latest_out_dir(cache)
    # ۱) کشِ خودِ ران: فقط پوشههایِ out*/debug* — بقیهٔ کش (src و …) نه
    for root, _d, files in os.walk(cache):
        dname = os.path.basename(os.path.normpath(root)).lower()
        if any("/" + o + "/" in root.lower().replace(os.sep, "/") + "/"
               for o in _ORIG_DIRS):
            continue
        is_dbg = dname.startswith("debug")
        is_out = dname == "out" or dname.startswith("out_")
        if not is_out and not is_dbg:
            continue
        # v1.14.277: نشانگر هست؟ تصاویرِ نهایی فقط از پوشهٔ خودِ همین
        # ران میآیند (جداییِ فقط-پاکسازی/ترجمه و سبکها)
        take_imgs = (not last) and is_out and not is_dbg
        if last and os.path.normpath(root) == os.path.normpath(last):
            take_imgs = True
        for f in sorted(files):
            if not f.lower().endswith(_IMG_EXTS):
                continue
            lp = os.path.join(root, f)
            if is_dbg or "debug" in f.lower():
                if "_base." in f.lower():
                    continue  # پایهٔ روکش — فقط برای کلیدهای نمایشگر
                dbg.append(lp)
            elif take_imgs:
                imgs.append(lp)
    # ۲) فالبک: پوشهٔ کاریِ همین ران — live (نهایی) + live_debug (دیباگ)
    #    و هیچ چیزِ دیگر (input_batch و … صفحهٔ اصلی را شلوغ نکنند)
    if not imgs:
        for root, dirs_, files in os.walk(job_out):
            rel = root.lower().replace(os.sep, "/")
            segs = [s for s in rel.split("/") if s]
            dname = os.path.basename(os.path.normpath(root)).lower()
            in_cache = any(s.endswith(".cache") for s in segs)
            if in_cache and not (dname == "out" or dname.startswith("out_")
                                 or dname.startswith("debug")):
                dirs_[:] = []
                continue
            if dname == "input_batch":
                dirs_[:] = []
                continue
            if any("/" + o + "/" in rel + "/" for o in _ORIG_DIRS):
                dirs_[:] = []
                continue
            # خودِ نامِ پوشه: live_debug و debug* → دیباگ، حتی اگر نامِ
            # فایلها (live_0001.jpg) خودشان debug نداشته باشند
            dir_dbg = "debug" in dname
            for f in sorted(files):
                lp = os.path.join(root, f)
                if f.lower().endswith(_IMG_EXTS):
                    if "_base." in f.lower():
                        continue  # پایهٔ روکش (live/debug) — فقط نمایشگرِ تعاملی
                    (dbg if (dir_dbg or "debug" in f.lower()) else imgs).append(lp)
    imgs.sort(key=_natkey)
    dbg.sort(key=_natkey)
    return imgs, dbg
