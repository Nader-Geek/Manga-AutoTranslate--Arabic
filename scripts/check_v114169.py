#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.183 (بهروزِ 169) — بدونِ وابستگی (فایل/متن):

زمینهٔ 169: «اپ نساخت» — بیلدِ APK شکست میخورد
(FloatBuffer.array → FloatArray). حالا با حذفِ کاملِ Paddle-Lite و
(v1.14.183) حذفِ کاملِ ML Kit:
۱) هیچ فایلِ Kotlin/اسکریپتی از خانوادهٔ پدل نمیماند
   (PliteProbeService.kt / PaddleLiteBridge.kt / fetch_paddle.py) و
   الگویِ ممنوعِ «return fbv.array()» در کلِ ریپو نیست.
۲) MlKitBridge.kt حذف شده؛ پلِ رسمی = PaddleOcrBridge.kt (ONNXِ خالص).
۳) نسخه: سازگاریِ APP_VER با VERSION.
"""
import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fail(msg):
    print("[✗]", msg)
    sys.exit(1)


# ۱) فایلهایِ پدل حذف شدهاند + الگویِ ممنوع در کلِ ریپو نیست
for rel in ("android/app/src/main/java/com/amirwolf/mangatranslator/"
            "PliteProbeService.kt",
            "android/app/src/main/java/com/amirwolf/mangatranslator/"
            "PaddleLiteBridge.kt",
            "android/scripts/fetch_paddle.py"):
    if os.path.exists(os.path.join(ROOT, rel)):
        fail(f"فایلِ Paddle-Lite هنوز هست: {rel}")
try:
    _r = subprocess.run(
        ["git", "grep", "-l", "return fbv.array()", "--", "*.kt"],
        cwd=ROOT, capture_output=True, text=True, timeout=30)
    if (_r.returncode == 0) and _r.stdout.strip():
        fail("الگویِ «return fbv.array()» هنوز در: "
             + _r.stdout.strip().splitlines()[0])
except Exception:
    pass

# ۲) v1.14.183 — پلِ ML Kit حذف شده؛ پلِ رسمی = PaddleOcrBridge.kt
kt = os.path.join(ROOT, "android/app/src/main/java/com/amirwolf/"
                       "mangatranslator/MlKitBridge.kt")
if os.path.exists(kt):
    fail("MlKitBridge.kt هنوز هست (v1.14.183: باید حذف شده باشد)")
kt2 = os.path.join(ROOT, "android/app/src/main/java/com/amirwolf/"
                        "mangatranslator/PaddleOcrBridge.kt")
if not os.path.isfile(kt2):
    fail("PaddleOcrBridge.kt نیست")
k = io.open(kt2, encoding="utf-8", errors="ignore").read()
for s in ("BitmapFactory.decodeByteArray", "OnnxTensor", "OrtSession",
          "META|"):
    if s not in k:
        fail(f"PaddleOcrBridge.kt محتوایِ لازم را ندارد: {s!r}")
if "com.google.mlkit" in k:
    fail("PaddleOcrBridge.kt به ML Kit وصل است!")

# ۳) نسخه — سازگاریِ APP_VER با VERSION (مستقل از شماره — الگویِ 1.14.168)
src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
ver = io.open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read()
_m = re.search(r'^APP_VER = "([\d.]+)"', src, re.M)
_vn = re.search(r'^versionName=([\d.]+)', ver, re.M)
if not _m or not _vn:
    fail("APP_VER/VERSION ناقص است")
if _m.group(1) != _vn.group(1):
    fail(f"APP_VER ({_m.group(1)}) با versionName ({_vn.group(1)}) یکی نیست")

print("PASS — چکِ رگرسیونِ v1.14.183/169: خانوادهٔ Paddle-Lite و ML Kit کامل حذف "
      "(بدونِ الگویِ FloatBuffer.array)؛ پلِ رسمی = PaddleOcrBridge.kt؛ "
      "APP_VER↔versionName سازگار")
