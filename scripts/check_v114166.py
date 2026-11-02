#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.183 (بهروزِ 166) — بدونِ وابستگی (فقط ast/فایل):

۱) هیچ def(self,…) تودرتویی در کلاسهایِ سطحِ بالایِ manga.py نیست
   (درسِ رگرسیونِ _ocr_implِ 1.14.163-164 — همان قاعدهٔ check_v114164.py).
۲) موتورِ OCRِ گوشی = پدلِ رسمیِ اندروید (دستورِ سازندهٔ v1.14.183:
   «ml kit حذف کن خوب نیست … از PP-OCRv6_medium بزار») — MlKitCropOCR/
   _mlkit_backend/_MLKIT_STATS کامل حذف؛ Paddle-Lite هم همچنان حذف:
   PliteCropOCR/_PLOCR_LiteRunner/_plite_* هیچکدام در manga.py نیستند.
۳) برشِ امن: باندِ ۷۰۰۰–۸۰۰۰ + فالبکِ فقط-به-عقب — دستنخورده.
۴) فایلهایِ اندروید: MlKitBridge.kt و وابستگیهایِ com.google.mlkit هم
   حذف شدند؛ PaddleLiteBridge.kt / PliteProbeService.kt / fetch_paddle.py
   نیستند؛ سرویسِ :pliteprobe در مانیفست نیست؛ گامِ fetch_paddle در
   ورک‌فلوها نیست.
"""
import ast
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ALLOW = {("install_webp_guards", "_safe_save")}  # کلوزورِ عمدیِ bridge.py


def fail(msg):
    print("[✗]", msg)
    sys.exit(1)


src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
tree = ast.parse(src)

cls = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
fns = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}

# ۱) جارویِ AST — هیچ def(self) تودرتویی
for c in tree.body:
    if not isinstance(c, ast.ClassDef):
        continue
    for m in c.body:
        if not isinstance(m, ast.FunctionDef):
            continue
        for ch in ast.iter_child_nodes(m):
            if isinstance(ch, ast.FunctionDef) and any(
                    a.arg == "self" for a in ch.args.args):
                if (c.name, m.name) in ALLOW:
                    continue
                fail(f"def(self) تودرتو: {c.name}.{m.name} > {ch.name}")

# ۲) v1.14.183 — ML Kit حذف شد؛ موتورِ گوشی = پدلِ رسمیِ اندروید
# («MlKitCropOCR» فقط به‌عنوانِ ارجاعِ تاریخی در کامنت مجاز است)
if "MlKitCropOCR" in cls or "class MlKitCropOCR" in src:
    fail("MlKitCropOCR هنوز در manga.py است")
for s in ("_mlkit_lang", "_mlkit_backend", "_mlkit_stats_note",
          "_MLKIT_STATE", "_MLKIT_BUILD_LOCK", "_MLKIT_STATS",
          "_mlbe"):
    if s in src:
        fail(f"بقایایِ mlkit در manga.py: {s!r}")
if "def _mobile_lang(lang):" not in src:
    fail("_mobile_lang (جایِ _mlkit_lang) نیست")
for s in ("PaddleAndroidOCR", "com.amirwolf.mangatranslator.PaddleOcrBridge",
          "recognizeAuto"):
    if s not in src:
        fail(f"رشتهٔ لازم در manga.py نیست: {s!r}")
for s in ("PliteCropOCR", "_PLOCR_LiteRunner", "_plite_backend",
          "MANGA_K3_PLITE", '"paddle", "paddlelite", "plite"'):
    if s in src:
        fail(f"بقایایِ Paddle-Lite در manga.py: {s!r}")

# ۳) برشِ امن — باندِ ۷۰۰۰–۸۰۰۰ + فالبکِ به-عقب (دستنخورده)
if "int(work_h) - 1000" not in src:
    fail("باندِ برشِ امن = work_h−1000 (۷۰۰۰) نیست")
if "_fb_hi = min(_band_lo, max_cut)" not in src:
    fail("فالبکِ فقط-به-عقبِ برشِ امن نیست")

# ۴) اندروید — مانیفست/گرگل/ورک‌فلو
kt = os.path.join(ROOT, "android/app/src/main/java/com/amirwolf/"
                       "mangatranslator/MlKitBridge.kt")
if os.path.exists(kt):
    fail("MlKitBridge.kt هنوز هست (v1.14.183: باید حذف شده باشد)")
kt2 = os.path.join(ROOT, "android/app/src/main/java/com/amirwolf/"
                        "mangatranslator/PaddleOcrBridge.kt")
if not os.path.isfile(kt2):
    fail("PaddleOcrBridge.kt نیست")
kt2s = io.open(kt2, encoding="utf-8", errors="ignore").read()
for s in ("object PaddleOcrBridge", "recognizeAuto", "PP-OCRv6"):
    if s not in kt2s:
        fail(f"PaddleOcrBridge.kt محتوایِ لازم را ندارد: {s!r}")
for rel in ("android/app/src/main/java/com/amirwolf/mangatranslator/"
            "PaddleLiteBridge.kt",
            "android/app/src/main/java/com/amirwolf/mangatranslator/"
            "PliteProbeService.kt",
            "android/scripts/fetch_paddle.py"):
    if os.path.exists(os.path.join(ROOT, rel)):
        fail(f"فایلِ Paddle-Lite هنوز هست: {rel}")

man = io.open(os.path.join(ROOT, "android/app/src/main/AndroidManifest.xml"),
              encoding="utf-8").read()
if "PliteProbeService" in man or ":pliteprobe" in man:
    fail("سرویسِ :pliteprobe هنوز در مانیفست است")
if ".EpProbeService" not in man:
    fail("EpProbeService نباید حذف میشد")

g = io.open(os.path.join(ROOT, "android/app/build.gradle.kts"),
            encoding="utf-8").read()
for s in ('implementation("com.google.mlkit', "text-recognition:16.0.1",
          "text-recognition-japanese", "text-recognition-korean",
          "text-recognition-chinese"):
    if s in g:
        fail(f"وابستگیِ ML Kit هنوز در gradle است: {s!r}")
if "onnxruntime-android" not in g:
    fail("onnxruntime-android از gradle حذف شده!")
if "PaddlePredictor" in g:
    fail("PaddlePredictor.jar هنوز در gradle است")

for wf in (".github/workflows/build.yml",
           ".github/workflows/android-emulator.yml"):
    w = io.open(os.path.join(ROOT, wf), encoding="utf-8").read()
    if "fetch_paddle" in w:
        fail(f"گامِ fetch_paddle هنوز در {wf} است")

print("PASS — چکِ رگرسیونِ v1.14.183/166: ML Kit کامل حذف، موتورِ گوشی = "
      "پدلِ رسمیِ اندروید (PP-OCRv6 medium)؛ جارویِ AST تمیز؛ باندِ برشِ "
      "امنِ ۷۰۰۰–۸۰۰۰ دستنخورده؛ فایلهایِ اندروید هماهنگ")
