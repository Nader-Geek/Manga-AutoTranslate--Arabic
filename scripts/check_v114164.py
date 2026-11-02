#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# v1.14.164/184 — ریشهٔ چکِ 164: تودرتوشدنِ def هنگامِ ویرایشِ موتور →
# AttributeErrorِ بیصدا و «Region had no OCR text» برایِ همهٔ نواحی.
# v1.14.184 — موتورِ گوشی = SDKِ رسمیِ ppocr-android (وندورشده)؛
# موتورِ پایتونیِ قدیمی (rapidocr_mobile) حذف شد — چکِ ساختارِ SDKِ رسمی:
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FAILS = []


def fail(m):
    print("[✗]", m)
    FAILS.append(m)


def ok(m):
    print("[✓]", m)


# ۱) موتورِ قدیمیِ پایتونیِ گوشی حذف شده (ریشهٔ همان خطایِ بیصدا)
if (ROOT / "android/app/src/main/python/rapidocr_mobile").exists():
    fail("rapidocr_mobile/ باید حذف شده باشد (v1.14.184)")
src = (ROOT / "manga.py").read_text(encoding="utf-8")
for gone in ("def _build_mobile_onnx", "from rapidocr_mobile import"):
    if gone in src:
        fail("«%s» هنوز در manga.py است" % gone)
ok("rapidocr_mobile حذف؛ manga.py مسیرِ قدیمی ندارد")

# ۲) کلاسهایِ کلیدیِ SDKِ رسمی — توپلول و سرِ جایش
SDK = ROOT / "android/ppocr-sdk/src/main/java/com/paddle/ocr"


import re as _re


def toplevel(rel, want_cls):
    # Kotlin فایل است — با regex (astِ پایتون رویِ .kt نمیشود)
    txt = (SDK / rel).read_text(encoding="utf-8")
    for c in want_cls:
        if not _re.search(r"\b(class|object)\s+%s\b" % c, txt):
            fail("%s: کلاسِ %s نیست" % (rel, c))


toplevel("engine/OCREngine.kt", ("OCREngine",))
toplevel("engine/DetectionEngine.kt", ("DetectionEngine",))
toplevel("engine/RecognitionEngine.kt", ("RecognitionEngine",))
toplevel("engine/ORTSessionManager.kt", ("ORTSessionManager",))
toplevel("preprocess/DetPreprocessor.kt", ("DetPreprocessor",))
toplevel("preprocess/RecPreprocessor.kt", ("RecPreprocessor",))
toplevel("postprocess/DBPostProcessor.kt", ("DBPostProcessor",))
toplevel("postprocess/CTCDecoder.kt", ("CTCDecoder",))
toplevel("postprocess/QuadTextCrop.kt", ("QuadTextCrop",))
toplevel("postprocess/BoxSorter.kt", ("BoxSorter",))
toplevel("PaddleOCR.kt", ("PaddleOCR",))
ok("ساختارِ SDKِ رسمی (pre/post/engine) توپلول و سرِ جایش")

# ۳) متدهایِ کلیدیِ OCREngine مستقیمِ کلاس‌اند (نه تودرتو — درسِ 157)
kt_eng = (SDK / "engine/OCREngine.kt").read_text(encoding="utf-8")
for need in ("fun run(bitmap: Bitmap)", "fun run(imageBytes: ByteArray)",
             "fun release()"):
    if need not in kt_eng:
        fail("OCREngine متدِ %s را ندارد" % need)
ok("OCREngine.run/release متدِ مستقیمِ کلاس")

if FAILS:
    print()
    print("[✗] گیتهایِ v1.14.164/184 شکست خورد")
    sys.exit(1)
print()
print("[✓] همهٔ گیتهایِ v1.14.164/184 PASS — SDKِ رسمی سالم؛ "
      "موتورِ قدیمیِ پایتونیِ گوشی حذف")
