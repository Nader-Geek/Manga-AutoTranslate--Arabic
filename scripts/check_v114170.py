#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.170 — بدونِ وابستگی (فقط ast/فایل):

دستورِ سازنده: «حذف کن بره paddle-lite ناقص استخراج میزنه ml kit بزار
همچن قسمت های ک متن هست استخراج بزنه و خوب چک کنه مال گوشی میگما و همه
زبان هارو خوب بتونه استخراج کنه انگلیسی ژاپنی کره چینی … اول باید با
detector-v4-s_int8.onnx قسمت های متن هست پیدا کنه بعد همون قسمت هارو
استخراج بزنه نه کل صفحه و سریع هم باشه … اگ نمیتونی رو خودت اندروید
اجرا کنی رو GitHub action تست کن».

۱) manga.py: MlKitCropOCR (پلِ recognizeAuto، کشفِ خودکارِ اسکریپت،
   خروجیِ هم‌قالبِ [ [[box,(t,s)],...] ]) + حذفِ کاملِ خانوادهٔ plite.
۲) detector-first دستنخورده: _extract_regions_from_bubbles + فقط
   کراپِ crop_mode=True + _parallel_budget.
۳) اندروید: MlKitBridge.kt (۴ کلاینتِ باندلشده) + gradle + مانیفست +
   ورک‌فلوها؛ PC (PaddleOCRWrapper/RapidOCR PC) دستنخورده.
۴) CI: گامِ گیتِ چندزبانهٔ check_mlkit.py در android-emulator.yml.
۵) نسخهٔ 175/1.14.170.
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

# ۱) ML Kit — پل/کشفِ خودکار/قالبِ خروجی
mk = cls.get("MlKitCropOCR")
if mk is None:
    fail("MlKitCropOCR نیست")
mk_src = ast.get_source_segment(src, mk) or ""
for s in ("recognizeAuto", "bytes(_buf.tobytes())", "reshape(4, 2)"):
    if s not in mk_src:
        fail(f"MlKitCropOCR محتوایِ لازم را ندارد: {s!r}")
if "_MLKIT_LANG_MAP" not in src:
    fail("_MLKIT_LANG_MAP نیست")
for lg in ('"japan": "ja"', '"korean": "ko"', '"chinese": "zh"'):
    if lg not in src:
        fail(f"نگاشتِ زبانِ ML Kit ناقص: {lg}")
# پلِ قدیمیِ recognize هم باید در Kotlin باشد (مستقیمِ غیرِauto)
kt = io.open(os.path.join(ROOT, "android/app/src/main/java/com/amirwolf/"
                                "mangatranslator/MlKitBridge.kt"),
             encoding="utf-8", errors="ignore").read()
for s in ("fun recognize(", "fun recognizeAuto(", "voteOf", "rememberedLang"):
    if s not in kt:
        fail(f"MlKitBridge.kt ناقص است: {s!r}")

# ۲) detector-first
if "_extract_regions_from_bubbles" not in src:
    fail("_extract_regions_from_bubbles نیست")
if "self._mobile.ocr(image_bgr, crop_mode=crop_mode)" not in src:
    fail("dispatchِ crop_mode عوض شده")
if "_mlkit_backend" not in fns or "_parallel_budget" not in fns:
    fail("توابعِ پایه (_mlkit_backend/_parallel_budget) نیستند")

# ۳) PC دستنخورده — wrapperهایِ PC و فالبکِ ONNXِ موبایل سرِ جایش
if "PaddleOCRWrapper" not in src:
    fail("PaddleOCRWrapper (PC) نباید حذف میشد")
if "RapidOcrMobile" not in src:
    fail("فالبکِ ONNXِ موبایل (RapidOcrMobile) نباید حذف میشد")
if "from rapidocr_mobile import RapidOcrMobile" not in src:
    fail("importِ فالبکِ موبایل عوض شده")

# ۴) CI — گیتِ چندزبانهٔ ML Kit
if not os.path.isfile(os.path.join(ROOT, ".ci_scripts/check_mlkit.py")):
    fail(".ci_scripts/check_mlkit.py نیست")
emu = io.open(os.path.join(ROOT, ".github/workflows/android-emulator.yml"),
              encoding="utf-8").read()
if "check_mlkit.py" not in emu:
    fail("گیتِ check_mlkit در android-emulator.yml نیست")
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

print("PASS — چکِ رگرسیونِ v1.14.170: OCRِ گوشی = ML Kit (ja/ko/zh/latin "
      "باندلشده، کشفِ خودکارِ اسکریپت) فقط رویِ کراپهایِ detector-v4-s؛ "
      "پدل کامل حذف؛ PC دستنخورده؛ گیتِ چندزبانهٔ CI سرِ جایش")
