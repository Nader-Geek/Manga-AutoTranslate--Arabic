#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.14.174/184 — EPِ ONNXِ گوشی (nnapi/xnnpack) بازنشسته شد.
SDKِ رسمیِ ppocr-android رویِ CPU با EngineConfig.numThreads اجرا
میشود؛ هیچ envِ MANGA_MOBILE_OCR_EP ست نمیشود و پاکسازی همیشه
انجام میشود (قراردادِ قدیمیِ -PortVer فقط برایِ بیلدِ شبیهساز است)."""
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

# ۱) هیچ ستِ EP در موتورِ گوشی نیست
if 'os.environ["MANGA_MOBILE_OCR_EP"]' in src:
    fail("MANGA_MOBILE_OCR_EP هنوز ست میشود (SDKِ رسمی EP ندارد)")
ok("هیچ ستِ MANGA_MOBILE_OCR_EP در manga.py نیست")

# ۲) speed_lab_env همیشه EPِ کهنه را پاک میکند
tree = ast.parse(src)
segs = {}
for n in ast.walk(tree):
    if isinstance(n, ast.FunctionDef) and n.name in (
            "speed_lab_env", "speed_test_run"):
        segs[n.name] = ast.get_source_segment(src, n)
lab = segs.get("speed_lab_env") or ""
if 'os.environ.pop("MANGA_MOBILE_OCR_EP", None)' not in lab:
    fail("speed_lab_env EPِ کهنه را پاک نمیکند")
ok("speed_lab_env پاکسازیِ EPِ کهنه")

# ۳) تورنمنتِ EPِ قدیمی برگشته؟
if '"auto", "nnapi", "xnnpack", "cpu"' in src:
    fail("تورنمنتِ EPِ قدیمی برگشته")
str_run = segs.get("speed_test_run") or ""
if "for _ep in (" in str_run:
    fail("پنجرههایِ شتاب‌دهندهٔ EP در speed_test_run برگشته")
ok("تورنمنت/پنجرههایِ EP حذف")

# ۴) پلِ Kotlin رویِ CPU با numThreadsِ رسمی
kt = io.open(os.path.join(
    ROOT, "android/app/src/main/java/com/amirwolf/mangatranslator/"
    "PaddleOcrBridge.kt"), encoding="utf-8", errors="ignore").read()
if "EngineConfig(numThreads" not in kt:
    fail("پلِ Kotlin از EngineConfig(numThreads) استفاده نمیکند")
if "nnapi" in kt.lower() or "xnnpack" in kt.lower():
    fail("پلِ Kotlin هنوز EPِ ONNX را میدهد")
ok("پلِ Kotlin = EngineConfig(numThreads) — رسمی")

# ۵) نسخه — سازگاریِ APP_VER با VERSION
ver = io.open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read()
_m = re.search(r'^APP_VER = "([\d.]+)"', src, re.M)
_vn = re.search(r"versionName=([\d.]+)", ver, re.M)
if not _m or not _vn or _m.group(1) != _vn.group(1):
    fail("APP_VER↔versionName ناسازگار")
ok("نسخهٔ سازگار (%s)" % (_m.group(1) if _m else "?"))

if FAILS:
    print()
    print("[✗] گیتهایِ v1.14.174/184 شکست خورد")
    sys.exit(1)
print()
print("[✓] همهٔ گیتهایِ v1.14.174/184 PASS — EP بازنشسته؛ SDKِ رسمی رویِ CPU")
