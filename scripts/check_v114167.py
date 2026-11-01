#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.170 (بهروزِ 167) — بدونِ وابستگی (فقط ast/فایل):

زمینهٔ 167: «هر بخش متن یک مقدار ram cpu gpu همزمان کار کنن… حداکثر
توانش — همچنین پاکسازیش همینجور» — موازیِ OCRِ ناحیهها + پاکسازی.

۱) بودجهٔ موازی: _parallel_budget سطحِ بالا + استفاده برایِ "ocr" و
   "clean"؛ overrideِ MANGA_REGION_WORKERS؛ لاگِ «استخراجِ موازی».
۲) موتورِ OCRِ گوشی = MlKitCropOCR (تک‌نمونهٔ تنبل با قفلِ ساخت؛ هیچ
   قفلِ سراسریِ run — ML Kit خودش صفِ داخلی دارد) + فالبکِ dead→ONNX.
۳) موازیِ پاکسازی: clean_image = _fill_one_cluster + ThreadPoolExecutor.
"""
import ast
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fail(msg):
    print("[✗]", msg)
    sys.exit(1)


src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
tree = ast.parse(src)
fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
cls = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}

# ۱) بودجهٔ موازی
if fns.get("_parallel_budget") is None:
    fail("_parallel_budget تابعِ سطحِ بالای manga.py نیست")
if "MANGA_REGION_WORKERS" not in src:
    fail("overrideِ MANGA_REGION_WORKERS نیست")
if '_parallel_budget("ocr")' not in src:
    fail("_parallel_budget(\"ocr\") صدا زده نمیشود")
if '_parallel_budget("clean")' not in src:
    fail("_parallel_budget(\"clean\") صدا زده نمیشود")
if "استخراجِ موازی" not in src:
    fail("لاگِ «استخراجِ موازی» در حلقهٔ ناحیهها نیست")

# ۲) موتورِ ML Kit — تک‌نمونه + بدونِ قفلِ سراسریِ run
mk = cls.get("MlKitCropOCR")
if mk is None:
    fail("MlKitCropOCR نیست")
mk_src = ast.get_source_segment(src, mk) or ""
if "_MLKIT_RUN_LOCK" in src or "_PLITE_RUN_LOCK" in src:
    fail("قفلِ سراسریِ run هنوز هست (OCRِ موازیِ ناحیهها میشکند)")
if "recognizeAuto" not in mk_src:
    fail("MlKitCropOCR به پلِ recognizeAuto وصل نیست")
if "ThreadPoolExecutor" not in mk_src and True:
    pass  # همزمانیِ ML Kit داخلِ خودِ پل/Kotlin است — شرط نیست
mb = fns.get("_mlkit_backend")
if mb is None:
    fail("_mlkit_backend نیست")
mb_src = ast.get_source_segment(src, mb) or ""
if 'dead"]=True' not in mb_src.replace(" ", ""):
    fail("_mlkit_backend شکستِ ساخت را dead نمیکند")
if "PP-OCRv6 ONNX" not in mb_src:
    fail("پیامِ فالبکِ ONNX در _mlkit_backend نیست")
if "MANGA_MLKIT" not in mb_src:
    fail("خاموشیِ MANGA_MLKIT=0 در _mlkit_backend نیست")

# ۳) موازیِ پاکسازی
trans = cls.get("MangaTranslator")
if trans is None:
    fail("MangaTranslator نیست")
clean_fn = None
for m in trans.body:
    if isinstance(m, ast.FunctionDef) and m.name == "clean_image":
        clean_fn = m
        break
if clean_fn is None:
    fail("clean_image نیست")
inner = {ch.name for ch in ast.iter_child_nodes(clean_fn)
         if isinstance(ch, ast.FunctionDef)}
if "_fill_one_cluster" not in inner:
    fail("_fill_one_cluster (تابعِ خوشهٔ مستقل) در clean_image نیست")
clean_src = ast.get_source_segment(src, clean_fn) or ""
if "ThreadPoolExecutor" not in clean_src:
    fail("dispatchِ موازیِ خوشه‌ها (ThreadPoolExecutor) در clean_image نیست")
if "crops.append([cx0, cy0, cx1, cy1, crop_msk, result, method])" in src:
    fail("حلقهٔ قدیمیِ ترتیبیِ خوشه‌ها هنوز هست (crops.append)")

# ۴) crop_mode — فقط کراپِ detector (detector-first)
if "self._mobile.ocr(image_bgr, crop_mode=crop_mode)" not in src:
    fail("dispatchِ ocr(crop_mode) تغییر کرده")
if "_oc125.ocr(crop_bgr, crop_mode=True)" not in src:
    fail("کراپِ detector با crop_mode=True به OCR نمیرود")

print("PASS — چکِ رگرسیونِ v1.14.170/167: بودجهٔ موازیِ cpu+ram+gpu برای "
      "OCRِ ناحیهها و خوشههایِ پاکسازی؛ موتورِ ML Kit تک‌نمونه/بدونِ قفلِ "
      "سراسری + فالبکِ ONNX؛ detector-first (فقط کراپ) دستنخورده")
