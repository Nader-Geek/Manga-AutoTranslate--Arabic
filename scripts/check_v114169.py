#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.170 (بهروزِ 169) — بدونِ وابستگی (فایل/متن):

زمینهٔ 169: «اپ نساخت» — بیلدِ APK از 1.14.167 به بعد شکست میخورد
(FloatBuffer.array → FloatArray). حالا با حذفِ کاملِ Paddle-Lite:
۱) هیچ فایلِ Kotlin/اسکریپتی از خانوادهٔ پدل نمیماند
   (PliteProbeService.kt / PaddleLiteBridge.kt / fetch_paddle.py) و
   الگویِ ممنوعِ «return fbv.array()» در کلِ ریپو نیست.
۲) MlKitBridge.kt (پلِ بازگشته) با Tasks.await + BitmapFactory کار میکند.
۳) نسخه: VERSION = 175/1.14.170 و APP_VER = "1.14.170".
"""
import io
import os
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

# ۲) پلِ ML Kit
kt = os.path.join(ROOT, "android/app/src/main/java/com/amirwolf/"
                       "mangatranslator/MlKitBridge.kt")
if not os.path.isfile(kt):
    fail("MlKitBridge.kt نیست")
k = io.open(kt, encoding="utf-8", errors="ignore").read()
for s in ("Tasks.await", "BitmapFactory.decodeByteArray",
          "InputImage.fromBitmap", "META|"):
    if s not in k:
        fail(f"MlKitBridge.kt محتوایِ لازم را ندارد: {s!r}")
if "com.google.mlkit.vision.text" not in k:
    fail("MlKitBridge.kt به ML Kit وصل نیست")

# ۳) نسخه
src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
if 'APP_VER = "1.14.170"' not in src:
    fail("APP_VER هنوز 1.14.170 نشده")
ver = io.open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read()
if "versionCode=175" not in ver or "versionName=1.14.170" not in ver:
    fail("VERSION باید 175/1.14.170 باشد")

print("PASS — چکِ رگرسیونِ v1.14.170/169: خانوادهٔ Paddle-Lite کامل حذف "
      "(بدونِ الگویِ FloatBuffer.array)؛ پلِ ML Kit با Tasks.await؛ "
      "نسخهٔ 175/1.14.170")
