#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.170 (بهروزِ 166) — بدونِ وابستگی (فقط ast/فایل):

۱) هیچ def(self,…) تودرتویی در کلاسهایِ سطحِ بالایِ manga.py نیست
   (درسِ رگرسیونِ _ocr_implِ 1.14.163-164 — همان قاعدهٔ check_v114164.py).
۲) موتورِ OCRِ گوشی = ML Kit (دستورِ سازندهٔ v1.14.170: «حذف کن بره
   paddle-lite ناقص استخراج میزنه ml kit بزار») — Paddle-Lite کامل حذف:
   PliteCropOCR/_PLOCR_LiteRunner/_plite_* هیچکدام در manga.py نیستند.
۳) برشِ امن: باندِ ۷۰۰۰–۸۰۰۰ + فالبکِ فقط-به-عقب — دستنخورده.
۴) فایلهایِ اندروید: MlKitBridge.kt هست؛ PaddleLiteBridge.kt /
   PliteProbeService.kt / fetch_paddle.py نیستند؛ سرویسِ :pliteprobe در
   مانیفست نیست؛ گامِ fetch_paddle در ورک‌فلوها نیست.
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

# ۲) ML Kit جایگزینِ پدل شد
mk = cls.get("MlKitCropOCR")
if mk is None:
    fail("MlKitCropOCR در سطحِ بالایِ manga.py نیست")
_mk_m = {m.name for m in mk.body if isinstance(m, ast.FunctionDef)}
if not {"ocr", "__init__"} <= _mk_m:
    fail(f"متدهایِ MlKitCropOCR ناقص: {sorted(_mk_m)}")
if not {"_mlkit_lang", "_mlkit_backend", "_mlkit_stats_note"} <= fns:
    fail("توابعِ کمکیِ mlkit ناقصاند")
for s in ("MlKitBridge", "recognizeAuto", "ja/ko/zh/latin"):
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
if not os.path.isfile(kt):
    fail("MlKitBridge.kt نیست")
kts = io.open(kt, encoding="utf-8", errors="ignore").read()
for s in ("recognizeAuto", "JapaneseTextRecognizerOptions",
          "KoreanTextRecognizerOptions", "ChineseTextRecognizerOptions"):
    if s not in kts:
        fail(f"MlKitBridge.kt محتوایِ لازم را ندارد: {s!r}")
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
for s in ("text-recognition:16.0.1", "text-recognition-japanese:16.0.1",
          "text-recognition-korean:16.0.1", "text-recognition-chinese:16.0.1"):
    if s not in g:
        fail(f"وابستگیِ ML Kit در gradle نیست: {s!r}")
if "PaddlePredictor" in g:
    fail("PaddlePredictor.jar هنوز در gradle است")

for wf in (".github/workflows/build.yml",
           ".github/workflows/android-emulator.yml"):
    w = io.open(os.path.join(ROOT, wf), encoding="utf-8").read()
    if "fetch_paddle" in w:
        fail(f"گامِ fetch_paddle هنوز در {wf} است")

print("PASS — چکِ رگرسیونِ v1.14.170/166: موتورِ OCRِ گوشی = ML Kit "
      "(پدل کامل حذف)؛ جارویِ AST تمیز؛ باندِ برشِ امنِ ۷۰۰۰–۸۰۰۰ "
      "دستنخورده؛ فایلهایِ اندروید هماهنگ")
