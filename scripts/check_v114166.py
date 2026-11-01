#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.166 — بدونِ وابستگی (فقط ast/فایل):

۱) PliteCropOCR و _PLOCR_LiteRunner باید کلاسِ سطحِ بالایِ manga.py باشند
   و هیچ def(self,…) تودرتویی نداشته باشند (درسِ رگرسیونِ _ocr_implِ
   1.14.163-164 — همان قاعدهٔ check_v114164.py).
۲) موتورِ OCRِ گوشی: انتخابِ پیشفرضِ Paddle-Lite + فالبکِ خودکار
   (MANGA_ANDROID_OCR / MANGA_MOBILE_OCR_ENGINE / _plite_backend).
۳) برشِ امن: باندِ ۷۰۰۰–۸۰۰۰ + فالبکِ فقط-به-عقب؛ فالبکِ رو-به-جلویِ
   قدیمی (که برش را تا ۹۰۰۰ میبرد) باید حذف شده باشد.
۴) فایلهایِ اندروید: PaddleLiteBridge.kt، PliteProbeService.kt،
   fetch_paddle.py، jar در build.gradle، سرویسِ :pliteprobe در مانیفست،
   گامِ fetch_paddle در هر دو ورک‌فلوِ بیلد.
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

plite = cls.get("PliteCropOCR")
if plite is None:
    fail("PliteCropOCR در سطحِ بالایِ manga.py نیست (کدِ مرده؟)")
_need = {"ocr", "_det", "_det_boxes", "_box_score", "_order_pts", "_crop_box",
         "_rec_all", "_rec_batches", "_rec_prep", "_rec_batch_tensor",
         "_rec_single_tensor", "_ctc"}
_methods = {m.name for m in plite.body if isinstance(m, ast.FunctionDef)}
if not _need <= _methods:
    fail(f"متدهایِ PliteCropOCR ناقص: {sorted(_need - _methods)}")
for m in plite.body:
    if not isinstance(m, ast.FunctionDef):
        continue
    for ch in ast.iter_child_nodes(m):
        if isinstance(ch, ast.FunctionDef) and any(
                a.arg == "self" for a in ch.args.args):
            fail(f"def(self) تودرتو: PliteCropOCR.{m.name} > {ch.name}")

if cls.get("_PLOCR_LiteRunner") is None:
    fail("_PLOCR_LiteRunner در سطحِ بالاست؟")
if not {"_plite_lang", "_plite_backend", "_plite_probe_run",
        "_plite_probe_ensure", "_plite_banned", "_plite_stats_note"} <= fns:
    fail("توابعِ کمکیِ plite ناقصاند")

for s in ("pplite_det_arm_cpu.nb", "PliteProbeService", ":pliteprobe",
          "MANGA_ANDROID_OCR", "MANGA_MOBILE_OCR_ENGINE",
          "_PLITE_RUN_LOCK", '"paddle", "paddlelite", "plite", "paddle-lite"'):
    if s not in src:
        fail(f"رشتهٔ لازم در manga.py نیست: {s!r}")

# برشِ امن: باندِ ۷۰۰۰–۸۰۰۰ + فالبکِ به-عقب؛ قدیمیِ رو-به-جو حذف شده باشد
if "int(work_h) - 1000" not in src:
    fail("باندِ برشِ امن = work_h−1000 (۷۰۰۰) نیست")
if "_fb_hi = min(_band_lo, max_cut)" not in src:
    fail("فالبکِ فقط-به-عقبِ برشِ امن نیست")
if "search_radius=ih, protected_ranges=protected" in src:
    fail("فالبکِ رو-به-جلویِ قدیمی (تا ۹۰۰۰) هنوز هست!")

# اندروید
checks = [
    ("android/app/src/main/java/com/amirwolf/mangatranslator/"
     "PaddleLiteBridge.kt", "createPaddlePredictor"),
    ("android/app/src/main/java/com/amirwolf/mangatranslator/"
     "PliteProbeService.kt", "verdict ok"),
    ("android/scripts/fetch_paddle.py", "inference_lite_lib.android.armv8"),
    ("android/app/build.gradle.kts", "libs/PaddlePredictor.jar"),
    ("android/app/src/main/AndroidManifest.xml", ":pliteprobe"),
    (".github/workflows/build.yml", "fetch_paddle.py"),
    (".github/workflows/android-emulator.yml", "fetch_paddle.py"),
]
for rel, s in checks:
    p = os.path.join(ROOT, rel)
    if not os.path.isfile(p):
        fail(f"فایل نیست: {rel}")
    if s not in io.open(p, encoding="utf-8", errors="ignore").read():
        fail(f"{rel} محتوایِ لازم را ندارد: {s!r}")

bpy = io.open(os.path.join(ROOT, "android/app/src/main/python/bridge.py"),
              encoding="utf-8").read()
if '"paddlelite", "plite", "paddle-lite"' not in bpy:
    fail("bridge.py مقدارِ paddle را نمیپذیرد")

print("PASS — چکِ رگرسیونِ v1.14.166: PliteCropOCR سرِ جایش است؛ "
      "موتورِ گوشی = Paddle-Lite با فالبکِ خودکار؛ باندِ برشِ امنِ "
      "۷۰۰۰–۸۰۰۰ با فالبکِ فقط-به-عقب؛ فایلهایِ اندرویدِ پدل کاملاند")
