#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.14.175/184 — «ترکیبی/خودکارِ EP» دیگر وجود ندارد.
دستورِ سازنده در 184: «هرروشی تو و گوشی واسه استخراج شده حذف کن فقط
از همین لینک بالا استفاده کنه» → SDKِ رسمی = CPU؛ هیچ انتخاب/تورنمنتِ
EP در موتورِ گوشی نیست؛ فقط عددِ نخها."""
import ast
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILS = []


def fail(m):
    print("[✗]", m)
    FAILS.append(m)


def ok(m):
    print("[✓]", m)


src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
kt = io.open(os.path.join(
    ROOT, "android/app/src/main/java/com/amirwolf/mangatranslator/"
    "PaddleOcrBridge.kt"), encoding="utf-8", errors="ignore").read()
sdk_g = io.open(os.path.join(ROOT, "android", "ppocr-sdk",
                             "build.gradle.kts"),
                encoding="utf-8").read()

# ۱) هیچ مکانیزمِ انتخابِ EP در موتورِ گوشی نیست
for gone in ('os.environ["MANGA_MOBILE_OCR_EP"]',
             'os.environ["MANGA_XNN_THREADS"]'):
    if gone in src:
        fail("مکانیزمِ EPِ قدیمی برگشته: %r" % gone)
ok("هیچ مکانیزمِ EPِ انتخابی در manga.py نیست")

# ۲) SDKِ رسمی = CPU؛ تنها پیکربندیِ موتور = numThreads
if "EngineConfig(numThreads" not in kt:
    fail("پلِ Kotlin از EngineConfig(numThreads) استفاده نمیکند")
for bad in ("nnapi", "xnnpack", "NNAPI", "XNNPACK"):
    if bad in kt:
        fail("پلِ Kotlin هنوز %r را میدهد" % bad)
ok("پلِ Kotlin = CPUِ رسمی با numThreads")

# ۳) ORTِ رسمیِ SDK (1.21.1 — همان READMEِ ppocr-android)
if "1.21.1" not in sdk_g:
    fail("نسخهٔ رسمیِ ORT (1.21.1) در :ppocr-sdk نیست")
ok("ORTِ رسمیِ 1.21.1 در :ppocr-sdk")

# ۴) نسخه — سازگاریِ APP_VER با VERSION
ver = io.open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read()
_m = re.search(r'^APP_VER = "([\d.]+)"', src, re.M)
_vn = re.search(r"versionName=([\d.]+)", ver, re.M)
if not _m or not _vn or _m.group(1) != _vn.group(1):
    fail("APP_VER↔versionName ناسازگار")
ok("نسخهٔ سازگار (%s)" % (_m.group(1) if _m else "?"))

if FAILS:
    print()
    print("[✗] گیتهایِ v1.14.175/184 شکست خورد")
    sys.exit(1)
print()
print("[✓] همهٔ گیتهایِ v1.14.175/184 PASS — EP حذف؛ CPUِ رسمیِ SDK")
