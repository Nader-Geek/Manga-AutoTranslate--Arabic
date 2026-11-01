#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.169 — بدونِ وابستگی (فایل/متن):

زمینه: «اپ نساخت — ارور داد» — بیلدِ APK از v1.14.167 شکست میخورد:
  PliteProbeService.kt:77:16: error: return type mismatch:
  expected 'kotlin.ByteArray', actual 'kotlin.FloatArray!'
ریشه: درِ floatBytes، متغیرِ fbv یک FloatBuffer است و
FloatBuffer.array() برمیگرداند float[] نه byte[] — باید array()
خودِ ByteBuffer برگردد. همین یک ارورِ کامپایلِ Kotlin باعث شد
بیلدِ ۱.۱۴.۱۶۷ و ۱.۱۴.۱۶۸ هر دو درِ گامِ «Build arm64 APK» مردود
شوند (۱۶۶ آخرین APKِ سالم بود — ریلیزِ apk به ساعتِ 10:15:56Z).

۱) فیکسِ floatBytes در PliteProbeService.kt
   («return fbv.array()» ممنوع؛ «bb.asFloatBuffer().put» + «bb.array()» لازم).
۲) همان الگویِ درست در floatsToBytesِ PaddleLiteBridge.kt سرِ جایش.
۳) نسخه: VERSION = 174/1.14.169 و APP_VER = "1.14.169".
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fail(msg):
    print("[✗]", msg)
    sys.exit(1)


probe_rel = ("android/app/src/main/java/com/amirwolf/mangatranslator/"
             "PliteProbeService.kt")
probe = io.open(os.path.join(ROOT, probe_rel), encoding="utf-8",
                errors="ignore").read()

# ۱) فیکسِ floatBytes
if "return fbv.array()" in probe:
    fail("PliteProbeService.kt هنوز FloatBuffer.array() را برمیگرداند "
         "(ارورِ کامپایلِ CI: expected ByteArray, actual FloatArray)")
if "bb.asFloatBuffer().put" not in probe or "return bb.array()" not in probe:
    fail("floatBytes باید با ByteBuffer اصلی ساخته شود "
         "(bb.asFloatBuffer().put + return bb.array())")

# ۲) الگویِ درست در پل باید بماند
kt_rel = ("android/app/src/main/java/com/amirwolf/mangatranslator/"
          "PaddleLiteBridge.kt")
kt = io.open(os.path.join(ROOT, kt_rel), encoding="utf-8",
             errors="ignore").read()
if "bb.asFloatBuffer().put(arr)" not in kt or "return bb.array()" not in kt:
    fail("floatsToBytes در PaddleLiteBridge.kt باید ByteBuffer.array() بدهد")

# ۳) نسخه
src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
if 'APP_VER = "1.14.169"' not in src:
    fail("APP_VER هنوز 1.14.169 نشده")
ver = io.open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read()
if "versionCode=174" not in ver or "versionName=1.14.169" not in ver:
    fail("VERSION باید 174/1.14.169 باشد")

print("PASS — چکِ رگرسیونِ v1.14.169: فیکسِ ارورِ کامپایلِ Kotlinِ "
      "(FloatBuffer.array → ByteBuffer.array درِ floatBytes) که بیلدِ "
      "APKِ ۱.۱۴.۱۶۷/۱۶۸ را میشکست؛ الگویِ درستِ پل سرِ جایش؛ نسخهٔ "
      "174/1.14.169")
