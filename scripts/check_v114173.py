#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.173 — DEBUGِ سبزِ detector رویِ همان DEBUGِ صفحه +
NNAPI فقط با تستِ صریح (v1.14.174: گیتِ NNAPI به فایلِ nnapi.txt بهروز شد):

درخواستِ سازنده: «عکس جدا نشون نده رو همون عکس اصلی دیباگ بزاره با یک
رنگ دیگ سبز نشون بده» + «استخراج کنده هنوز تو گوشی ولی EP=Nnapi وقتی
رفت اونجا سریعتر شد میشه ولی کرش کرد فعلا رو همون بیاد — nnapi میخوام
تست کنم نه xnnpack».

۱) manga.py: مکانیزمِ عکسِ جدا (<صفحه>_det.jpg/_save_det_debug/_DET_TLS/
   _dbg_cache_*) کامل حذف؛ باکسهایِ خامِ detector-v4-s با det_raw رویِ
   ناحیهها سوار و در _draw_debug_regions با سبزِ (0,255,0) و برچسبِ
   D## رویِ همان DEBUGِ صفحه کشیده میشوند (نقطهٔ واحد — مسیرِ استخراج
   و مسیرِ clean-only هر دو).
۲) rapidocr_mobile/_ep_plan: پیشفرض/auto = فقط XNNPACK — NNAPI از
   تورنمنتِ خودکار حذف شد (پروبِ OK ولی کرشِ نیتیو در اینفرنسِ واقعی —
   لاگِ گوشیِ 1.14.172)؛ تستِ NNAPI فقط با MANGA_MOBILE_OCR_EP=nnapi؛
   گیتِ PC/x86 و MANGA_EP_NO_PROBE دستنخورده.
۳) نسخه — APP_VER↔versionName.
"""
import ast
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fail(msg):
    print("[✗]", msg)
    sys.exit(1)


def ok(msg):
    print("[✓]", msg)


src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
tree = ast.parse(src)
cls = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}

# ۰) نسخه
_m = re.search(r'^APP_VER = "([\d.]+)"', src, re.M)
_vn = re.search(r"versionName=([\d.]+)",
                io.open(os.path.join(ROOT, "VERSION"),
                        encoding="utf-8").read())
if not _m or not _vn:
    fail("APP_VER/VERSION ناقص است")
if _m.group(1) != _vn.group(1):
    fail(f"APP_VER ({_m.group(1)}) با versionName ({_vn.group(1)}) یکی نیست")
ok(f"نسخه {_m.group(1)} (APP_VER↔versionName)")

# ۱) مکانیزمِ سبزِ رویِ DEBUGِ صفحه
dd = cls.get("MangaTranslator")
dd_src = ast.get_source_segment(src, dd) or ""
for gone in ("def _save_det_debug", "_DET_TLS = threading.local()",
             "self._dbg_cache_dir = cache_dir",
             "_DET_TLS.base = os.path.splitext(basename)[0]"):
    if gone in src:
        fail(f"مکانیزمِ عکسِ جدا حذف نشده: {gone!r}")
erb = re.search(r"def _extract_regions_from_bubbles.*?(?=\n    def )",
                dd_src, re.S)
if not erb:
    fail("_extract_regions_from_bubbles پیدا نشد")
erb_src = erb.group(0)
for s in ("_raw_det_dbg = []", "if self.debug:", "det_raw = _raw_det_dbg"):
    if s not in erb_src:
        fail(f"استفادهٔ det_raw در استخراج ناقص است: {s!r}")
i_stash = erb_src.find("_raw_det_dbg = [")
i_drop = erb_src.find("boxes = self._drop_contained_boxes(")
if i_stash < 0 or i_drop < 0 or i_stash > i_drop:
    fail("stashِ باکسِ خام باید قبلِ حذفِ تودرتو باشد")
ddr = re.search(r"def _draw_debug_regions.*?(?=\n    @|\n    def )",
                dd_src, re.S)
if not ddr:
    fail("_draw_debug_regions پیدا نشد")
ddr_src = ddr.group(0)
for s in ('getattr(_r0, "det_raw", None)', "(0, 255, 0)",
          'f"D{_di:02d} {_dcls}"', "cv2.rectangle(vis"):
    if s not in ddr_src:
        fail(f"پوششِ سبز در _draw_debug_regions ناقص است: {s!r}")
if ddr_src.rfind("return vis") < ddr_src.find("det_raw"):
    fail("پوششِ سبز باید قبل از return vis باشد")
ok("باکسهایِ خامِ detector = سبزِ D## رویِ همان DEBUGِ صفحه")

# ۲) EPِ موبایل — پیشفرض فقط XNNPACK؛ NNAPI فقط تستِ صریح
# ۲) EPِ موبایل — از 184 بازنشسته: SDKِ رسمیِ ppocr-android رویِ CPU
if os.path.exists(os.path.join(ROOT, "android", "app", "src", "main",
                               "python", "rapidocr_mobile")):
    fail("rapidocr_mobile/ باید حذف شده باشد (v1.14.184)")
if 'os.environ["MANGA_MOBILE_OCR_EP"]' in src:
    fail("MANGA_MOBILE_OCR_EP هنوز ست میشود")
ok("EPِ موبایل بازنشسته — SDKِ رسمی رویِ CPU (بدونِ rapidocr_mobile)")

# ۳) نردبانِ 184 — تکپلهٔ SDKِ رسمی (بدونِ آستانههایِ پلهای)
lad = cls.get("MtLadderOCR")
lad_src = ast.get_source_segment(src, lad) or ""
for s in ("_mt_boost_crop(image_bgr)", "_mt_map_boxes(r0[0], pad, scale)",
          '_MT_MODES = ("padandroid",)'):
    if s not in lad_src:
        fail(f"نردبانِ 184 تغییر کرده: {s!r}")
rb = cls.get("RapidOCRBackend")
rb_src = ast.get_source_segment(src, rb) or ""
if "_build_paddle_android(lang)" not in rb_src:
    fail("wiringِ 184 (SDKِ رسمی) در _init_mobile_engine نیست")
ok("نردبانِ 184 = تکپلهٔ SDKِ رسمی سرِ جایش")

print("[✓] همهٔ گیتهایِ v1.14.173 PASS")
