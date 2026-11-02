#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.183 (بهروزِ 184) — فیکسِ بیلدِ CIِ 182 + حذفِ کاملِ
ML Kit. از 184: فیکسِ ORT (OptLevel.ALL_OPT + .info.shape) داخلِ SDKِ
رسمیِ ppocr-android (ORTSessionManager) است و پلِ خودی دیگر ORTِ
مستقیم ندارد."""
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
KTD = os.path.join(ROOT, "android/app/src/main/java/com/amirwolf/",
                   "mangatranslator")
KT = os.path.join(KTD, "PaddleOcrBridge.kt")
ksrc = io.open(KT, encoding="utf-8", errors="ignore").read()
grad = io.open(os.path.join(ROOT, "android/app/build.gradle.kts"),
               encoding="utf-8").read()

# ── ۱) میراثِ 182: MlKitBridge.kt و وابستگیهایِ mlkit حذف ────────
if os.path.exists(os.path.join(KTD, "MlKitBridge.kt")):
    fail("A: MlKitBridge.kt هنوز هست")
for s in ('implementation("com.google.mlkit', "text-recognition:16.0.1"):
    if s in grad:
        fail("A: وابستگیِ %s هنوز در gradle است" % s)
if "MlKitCropOCR" in src or "_MLKIT_STATS" in src:
    fail("A: بقایایِ mlkit در manga.py است")
ok("A: MlKitBridge.kt + وابستگیهایِ mlkit + بقایایِ پایتون حذف")

# ── ۲) فیکسِ بیلدِ 183 — حالا داخلِ SDKِ رسمی ─────────────────────
sdk_mgr_p = os.path.join(ROOT, "android", "ppocr-sdk", "src", "main",
                         "java", "com", "paddle", "ocr", "engine",
                         "ORTSessionManager.kt")
if not os.path.isfile(sdk_mgr_p):
    fail("KT: ORTSessionManagerِ رسمی نیست")
sdk_mgr = io.open(sdk_mgr_p, encoding="utf-8").read()
if "OptLevel.ALL_OPT" not in sdk_mgr:
    fail("KT: OptLevel.ALL_OPT در SDKِ رسمی نیست")
if ".info.shape" not in sdk_mgr:
    fail("KT: .info.shape در SDKِ رسمی نیست")
if "OrtSession.SessionOptions.OptimizationLevel" in sdk_mgr:
    fail("KT: OptimizationLevelِ غلط در SDKِ رسمی است")
for bad in ("ai.onnxruntime", "OrtSession"):
    if bad in ksrc:
        fail("KT: %s در پلِ خودی است (فقط SDKِ رسمی)" % bad)
for frag in ("object PaddleOcrBridge", "fun recognizeAuto(",
             "RapidOcr.create", "com.paddle.ocr"):
    if frag not in ksrc:
        fail("KT: PaddleOcrBridge.kt فاقدِ %s" % frag)
ok("KT: فیکسِ ORT داخلِ SDKِ رسمی؛ پلِ خودی = پلِ نازک")

# ── ۳) ماژولِ :ppocr-sdk وندور شده ────────────────────────────────
sg = io.open(os.path.join(ROOT, "android", "settings.gradle.kts"),
             encoding="utf-8").read()
if 'include(":ppocr-sdk")' not in sg:
    fail("S: :ppocr-sdk در settings.gradle.kts نیست")
if not os.path.isfile(os.path.join(
        ROOT, "android", "ppocr-sdk", "src", "main", "java", "com",
        "paddle", "ocr", "PaddleOCR.kt")):
    fail("S: PaddleOCR.ktِ رسمی نیست")
ok("S: :ppocr-sdk وندورشده و include شده")

# ── ۴) نسخه ─────────────────────────────────────────────────────
ver = io.open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read()
_m = re.search(r'^APP_VER = "([\d.]+)"', src, re.M)
_vn = re.search(r"versionName=([\d.]+)", ver, re.M)
_vc = re.search(r"versionCode=(\d+)", ver, re.M)
if not _m or not _vn or _m.group(1) != _vn.group(1):
    fail("V: APP_VER/VERSION ناسازگار")
if tuple(int(x) for x in _m.group(1).split(".")) < (1, 14, 183):
    fail("V: این چک برایِ 1.14.183+ است (APP_VER=%s)" % _m.group(1))
ok("V: نسخهٔ %s / versionCode=%s"
   % (_m.group(1), _vc.group(1) if _vc else "?"))

if FAILS:
    print()
    print("[✗] گیتهایِ v1.14.183/184 شکست خورد")
    sys.exit(1)
print()
print("[✓] همهٔ گیتهایِ v1.14.183/184 PASS — mlkit حذف؛ فیکسِ ORT داخلِ "
      "SDKِ رسمی؛ پلِ نازک")
