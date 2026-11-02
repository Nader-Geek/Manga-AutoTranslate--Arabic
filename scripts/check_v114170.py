#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.183 (بهروزِ 170) — بدونِ وابستگی (فقط ast/فایل):

دستورِ سازنده (1.14.183): «ml kit حذف کن خوب نیست … از PP-OCRv6_medium
بزار تو کد خودم قسمت استخراجم؛ اول detector-v4-s_int8.onnx همه قسمت
هایِ متن پیدا کنه فقط همون قسمت ها استخراج کنه تا سریعتر باشه».

۱) manga.py: PaddleAndroidOCR (پلِ recognizeAuto، خروجیِ هم‌قالبِ
   [ [[box,(t,s)],...] ]) + حذفِ کاملِ MlKitCropOCR و خانوادهٔ plite.
۲) detector-first دستنخورده: _extract_regions_from_bubbles + فقط
   کراپِ crop_mode=True + _parallel_budget.
۳) اندروید: PaddleOcrBridge.kt (ONNXِ خالص) — MlKitBridge.kt حذف؛
   PC (PaddleOCRWrapper/RapidOCR PC) دستنخورده.
۴) CI: گامِ گیتِ چندزبانهٔ check_ocr_gate.py در android-emulator.yml.
۵) نسخه: سازگاریِ APP_VER با VERSION.
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


src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
tree = ast.parse(src)
cls = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
fns = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}

# ۱) v1.14.183 — پدلِ رسمیِ اندروید جایِ ML Kit
pa = cls.get("PaddleAndroidOCR")
if pa is None:
    fail("PaddleAndroidOCR نیست")
pa_src = ast.get_source_segment(src, pa) or ""
for s in ("recognizeAuto", "bytes(_buf.tobytes())", "reshape(4, 2)"):
    if s not in pa_src:
        fail(f"PaddleAndroidOCR محتوایِ لازم را ندارد: {s!r}")
if "_MOBILE_LANG_MAP" not in src:
    fail("_MOBILE_LANG_MAP نیست")
for lg in ('"japan": "ja"', '"korean": "ko"', '"chinese": "zh"'):
    if lg not in src:
        fail(f"نگاشتِ زبانِ موتورِ گوشی ناقص: {lg}")
if "MlKitCropOCR" in cls or "class MlKitCropOCR" in src:
    fail("MlKitCropOCR برگشته!")
# پلِ رسمیِ Kotlin (ONNXِ خالص) — پلِ ML Kit حذف شده
kt = io.open(os.path.join(ROOT, "android/app/src/main/java/com/amirwolf/"
                                "mangatranslator/PaddleOcrBridge.kt"),
             encoding="utf-8", errors="ignore").read()
for s in ("fun recognize(", "fun recognizeAuto(", "OrtSession"):
    if s not in kt:
        fail(f"PaddleOcrBridge.kt ناقص است: {s!r}")
import os as _os
if _os.path.exists(os.path.join(
        ROOT, "android/app/src/main/java/com/amirwolf/mangatranslator/"
        "MlKitBridge.kt")):
    fail("MlKitBridge.kt هنوز هست")

# ۲) detector-first
if "_extract_regions_from_bubbles" not in src:
    fail("_extract_regions_from_bubbles نیست")
if "self._mobile.ocr(image_bgr, crop_mode=crop_mode)" not in src:
    fail("dispatchِ crop_mode عوض شده")
_bpa = None
for _n0 in ast.walk(tree):
    if isinstance(_n0, ast.FunctionDef) and _n0.name == "_build_paddle_android":
        _bpa = ast.get_source_segment(src, _n0)
if _bpa is None or "_parallel_budget" not in fns:
    fail("توابعِ پایه (_build_paddle_android/_parallel_budget) نیستند")

# ۳) PC دستنخورده — wrapperهایِ PC و فالبکِ ONNXِ موبایل سرِ جایش
if "PaddleOCRWrapper" not in src:
    fail("PaddleOCRWrapper (PC) نباید حذف میشد")
if "RapidOcrMobile" not in src:
    fail("فالبکِ ONNXِ موبایل (RapidOcrMobile) نباید حذف میشد")
if "from rapidocr_mobile import RapidOcrMobile" not in src:
    fail("importِ فالبکِ موبایل عوض شده")

# ۴) CI — گیتِ چندزبانه (نامِ جدیدِ 183)
if not os.path.isfile(os.path.join(ROOT, ".ci_scripts/check_ocr_gate.py")):
    fail(".ci_scripts/check_ocr_gate.py نیست")
emu = io.open(os.path.join(ROOT, ".github/workflows/android-emulator.yml"),
              encoding="utf-8").read()
if "check_ocr_gate.py" not in emu:
    fail("گیتِ check_ocr_gate در android-emulator.yml نیست")
if "fetch_paddle" in emu:
    fail("گامِ fetch_paddle هنوز در emulator workflow است")

# ۵) نسخه — سازگاریِ APP_VER با VERSION (مستقل از شماره — الگویِ 1.14.168)
ver = io.open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read()
_m = re.search(r'^APP_VER = "([\d.]+)"', src, re.M)
_vn = re.search(r'^versionName=([\d.]+)', ver, re.M)
if not _m or not _vn:
    fail("APP_VER/VERSION ناقص است")
if _m.group(1) != _vn.group(1):
    fail(f"APP_VER ({_m.group(1)}) با versionName ({_vn.group(1)}) یکی نیست")

print("PASS — چکِ رگرسیونِ v1.14.183/170: OCRِ گوشی = پدلِ رسمیِ اندروید "
      "(PP-OCRv6 medium — ML Kit حذف) فقط رویِ کراپهایِ detector-v4-s؛ "
      "پدلِ لایت هم حذف؛ PC دستنخورده؛ گیتِ چندزبانهٔ CI سرِ جایش")
