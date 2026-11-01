#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.167 — بدونِ وابستگی (فقط ast/فایل):

زمینه: لاگِ واقعیِ گوشی (manga.log) نشان داد «همهٔ» OCRهایِ پدل با
«memoryview: a bytes-like object is required, not 'HeapFloatBuffer'»
مردود میشوند + دستورِ سازنده: «هر بخش متن یک مقدار ram cpu gpu همزمان
کار کنن… حداکثر توانش — همچنین پاکسازیش همینجور».

۱) باگِ HeapFloatBuffer: manga.py دیگر memoryview(fb) ندارد؛ رانرِ پدل
   با پلِ byte-based (bytesِ little-endian) کار میکند.
۲) موازیِ OCR: PliteCropOCR قفلِ سراسری ندارد (استخرِ predictor در
   Kotlin)؛ حلقهٔ ناحیهها با ThreadPoolExecutor و بودجهٔ موازی اجرا
   میشود؛ _parallel_budget تابعِ سطحِ بالا و استفادهشده در __init__ است.
۳) موازیِ پاکسازی: clean_image باید _fill_one_cluster (تابعِ خوشهٔ
   مستقل) + dispatchِ ThreadPoolExecutor داشته باشد.
۴) Kotlin: predict با data: ByteArray و poolMax؛ استخرِ
   LinkedBlockingDeque؛ پروب با floatBytes.
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

# ۱) باگِ HeapFloatBuffer — از ریشه (الگویِ کد، نه نامش در توضیحات)
if "memoryview(fb)" in src:
    fail("memoryview(fb) هنوز در manga.py است (باگِ HeapFloatBuffer)")
runner_all = ""
if cls.get("_PLOCR_LiteRunner") is not None:
    runner_all = ast.get_source_segment(src, cls["_PLOCR_LiteRunner"]) or ""
runner = cls.get("_PLOCR_LiteRunner")
if runner is None:
    fail("_PLOCR_LiteRunner نیست")
runner_all = ast.get_source_segment(src, runner) or ""
r_run = next((m for m in runner.body
              if isinstance(m, ast.FunctionDef) and m.name == "run"), None)
if r_run is None:
    fail("رانرِ پدل متدِ run ندارد")
if "memoryview" in (ast.get_source_segment(src, r_run) or ""):
    fail("رانرِ پدل هنوز memoryview میخواند")
if 'np.frombuffer(fb, dtype="<f4")' not in src:
    fail("رانرِ پدل خروجیِ byte-based نمیخواند")
if "jarray" in src.split("class _PLOCR_LiteRunner")[1].split("class ")[0] \
        and "_jf" in src.split("class _PLOCR_LiteRunner")[1].split("class ")[0]:
    fail("jarray(jfloat) عنصربه‌عنصر هنوز در رانرِ پدل است")

runner = cls.get("_PLOCR_LiteRunner")
if runner is None:
    fail("_PLOCR_LiteRunner نیست")
r_init = next((m for m in runner.body
               if isinstance(m, ast.FunctionDef) and m.name == "__init__"),
              None)
if r_init is None or not any(a.arg == "pool_max" for a in r_init.args.args):
    fail("_PLOCR_LiteRunner.__init__ پارامترِ pool_max ندارد")

plite = cls.get("PliteCropOCR")
if plite is None:
    fail("PliteCropOCR نیست")
p_init = next((m for m in plite.body
               if isinstance(m, ast.FunctionDef) and m.name == "__init__"),
              None)
p_src = ast.dump(p_init) if p_init else ""
if "_parallel_budget" not in p_src:
    fail("PliteCropOCR.__init__ بودجهٔ موازی نمیگیرد (pool_max)")
p_ocr = next((m for m in plite.body
              if isinstance(m, ast.FunctionDef) and m.name == "ocr"), None)
if p_ocr is None:
    fail("PliteCropOCR.ocr نیست")
if any(a.arg == "self" for ch in ast.iter_child_nodes(p_ocr)
       if isinstance(ch, ast.FunctionDef)
       for a in ch.args.args):
    fail("def(self) تودرتو در PliteCropOCR.ocr")
if "_ctc_lock" not in p_src:
    fail("قفلِ کالیبراسیونِ charset (_ctc_lock) در PliteCropOCR نیست")

# ۲) موازیِ OCR — بودجه + حلقهٔ ناحیهها
budget = fns.get("_parallel_budget")
if budget is None:
    fail("_parallel_budget تابعِ سطحِ بالای manga.py نیست")
if "MANGA_REGION_WORKERS" not in src:
    fail("overrideِ MANGA_REGION_WORKERS نیست")
tree_s = ast.dump(tree)
if tree_s.count("Call") == 0 or '_parallel_budget("ocr")' not in src:
    fail("_parallel_budget(\"ocr\") صدا زده نمیشود")
if '_parallel_budget("clean")' not in src:
    fail("_parallel_budget(\"clean\") صدا زده نمیشود")
if "استخراجِ موازی" not in src:
    fail("لاگِ «استخراجِ موازی» در حلقهٔ ناحیهها نیست")

# ۳) موازیِ پاکسازی — clean_image باید _fill_one_cluster + dispatch داشته باشد
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

# ۴) Kotlin + پروب
kt_rel = ("android/app/src/main/java/com/amirwolf/mangatranslator/"
          "PaddleLiteBridge.kt")
kt = io.open(os.path.join(ROOT, kt_rel), encoding="utf-8",
             errors="ignore").read()
for s in ("data: ByteArray", "poolMax: Int", "LinkedBlockingDeque",
          "ByteOrder.LITTLE_ENDIAN", "floatsToBytes"):
    if s not in kt:
        fail(f"PaddleLiteBridge.kt محتوایِ لازم را ندارد: {s!r}")
if "fun predict(modelPath: String, shape: LongArray, data: ByteArray," \
        not in kt or "): ByteArray?" not in kt:
    fail("امضایِ predict در پل باید (…, data: ByteArray, …) → ByteArray? باشد")
probe_rel = ("android/app/src/main/java/com/amirwolf/mangatranslator/"
             "PliteProbeService.kt")
probe = io.open(os.path.join(ROOT, probe_rel), encoding="utf-8",
                errors="ignore").read()
if "floatBytes" not in probe:
    fail("پروب با پلِ byte-based هماهنگ نیست")

# RESOURCEWARNINGِ لاگِ کاربر — فایلِ verdictِ پروب باید with بسته شود
if 'open(_out, "r", encoding="utf-8").read()' in src:
    fail("خواندنِ verdictِ پروب هنوز فایل را نمیبندد (ResourceWarning)")

print("PASS — چکِ رگرسیونِ v1.14.167: پلِ پدل byte-based (بدونِ "
      "HeapFloatBuffer)؛ OCRِ ناحیهها و پرکنندهٔ خوشه‌هایِ پاکسازی با "
      "بودجهٔ موازیِ cpu+ram+gpu؛ استخرِ predictor در Kotlin؛ پروب "
      "هماهنگ")
