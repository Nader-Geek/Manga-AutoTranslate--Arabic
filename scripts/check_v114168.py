#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.168 — بدونِ وابستگی (فقط ast/فایل):

زمینه: لاگِ واقعیِ گوشی — «predict takes 5 arguments (6 given)»:
APKِ نصب‌شده پلِ قدیمیِ 1.14.166 را دارد (۵آرگومانیِ float[] با
خروجیِ FloatBuffer) و manga.pyِ بهروزشده ۶آرگومان (byte[] + poolMax)
میفرستد → همهٔ OCRهایِ پدل مردود و همهٔ ناحیهها «cleaning only».

۱) سلف‌تستِ پل: _plite_bridge_selftest تابعِ سطحِ بالاست؛ detِ ریزِ
   ۶۴×۶۴ را ران میکند؛ TypeError → RuntimeError با پیامِ «قدیمی»؛
   PliteCropOCR.__init__ آن را بعدِ ساختِ رانرها صدا میزند.
۲) گاردِ TypeError در _PLOCR_LiteRunner.run (پلِ قدیمی = پیامِ روشن).
۳) ResourceWarningِ لاگِ کاربر: هیچ «open(...).read()»ی بدونِ with
   در مسیرِ پروب/بن نمیماند (الگوهایِ قدیمیِ عینی ممنوع).
۴) فالبکِ خودکار: _plite_backend هر شکستِ ساخت را dead میکند → ONNX.
۵) Kotlin: امضایِ ۶آرگومانیِ byte[] + poolMax سرِ جایش (برایِ APKِ جدید).
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

# ۱) سلف‌تستِ پل
st = fns.get("_plite_bridge_selftest")
if st is None:
    fail("_plite_bridge_selftest تابعِ سطحِ بالای manga.py نیست")
st_src = ast.get_source_segment(src, st) or ""
if "(1, 3, 64, 64)" not in st_src:
    fail("سلف‌تستِ پل detِ ریزِ ۶۴×۶۴ را ران نمیکند")
if "except TypeError" not in st_src:
    fail("سلف‌تستِ پل TypeError را نمیگیرد (پلِ قدیمی تشخیص نمیشود)")
if "قدیمی" not in st_src or not isinstance(st, ast.FunctionDef):
    fail("سلف‌تستِ پل برایِ پلِ قدیمی پیامِ روشن ندارد")

plite = cls.get("PliteCropOCR")
if plite is None:
    fail("PliteCropOCR نیست")
p_init = next((m for m in plite.body
               if isinstance(m, ast.FunctionDef) and m.name == "__init__"),
              None)
if p_init is None:
    fail("PliteCropOCR.__init__ نیست")
if "_plite_bridge_selftest" not in ast.dump(p_init):
    fail("PliteCropOCR.__init__ سلف‌تستِ پل را صدا نمیزند")

# ۲) گاردِ TypeError در runِ رانر
runner = cls.get("_PLOCR_LiteRunner")
if runner is None:
    fail("_PLOCR_LiteRunner نیست")
r_run = next((m for m in runner.body
              if isinstance(m, ast.FunctionDef) and m.name == "run"), None)
if r_run is None:
    fail("رانرِ پدل متدِ run ندارد")
r_src = ast.get_source_segment(src, r_run) or ""
if "except TypeError" not in r_src or "پلِ قدیمی" not in r_src:
    fail("runِ رانرِ پدل گاردِ پلِ قدیمی (TypeError) ندارد")
if 'np.frombuffer(fb, dtype="<f4")' not in r_src:
    fail("رانرِ پدل خروجیِ byte-based نمیخواند (باگِ HeapFloatBuffer برگشت؟)")

# ۳) ResourceWarning — الگوهایِ قدیمیِ «فایلِ بستهنشدنی» ممنوع
for bad in ('open(_cachef, "r", encoding="utf-8").read()',
            '(open(p, "r", encoding="utf-8").read() or "")',
            'open(_out, "r", encoding="utf-8").read()'):
    if bad in src:
        fail(f"خواندنِ بدونِ with هنوز هست: {bad!r}")

# ۴) فالبکِ خودکارِ _plite_backend
pb = fns.get("_plite_backend")
if pb is None:
    fail("_plite_backend نیست")
pb_src = ast.get_source_segment(src, pb) or ""
if '"dead"] = True' not in pb_src.replace(" ", "") and 'dead"] = True' \
        not in pb_src:
    fail("_plite_backend شکستِ ساخت را dead نمیکند")
if "PP-OCRv6 ONNX" not in pb_src:
    fail("پیامِ فالبکِ ONNX در _plite_backend نیست")

# ۵) Kotlin — امضایِ جدید (پلِ APKِ جدید)
kt_rel = ("android/app/src/main/java/com/amirwolf/mangatranslator/"
          "PaddleLiteBridge.kt")
kt = io.open(os.path.join(ROOT, kt_rel), encoding="utf-8",
             errors="ignore").read()
for s in ("data: ByteArray", "poolMax: Int = 1", "LinkedBlockingDeque"):
    if s not in kt:
        fail(f"PaddleLiteBridge.kt محتوایِ لازم را ندارد: {s!r}")

# ۶) نسخه
if 'APP_VER = "1.14.168"' not in src:
    fail("APP_VER هنوز 1.14.168 نشده")
ver = io.open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read()
if "versionCode=173" not in ver or "versionName=1.14.168" not in ver:
    fail("VERSION باید 173/1.14.168 باشد")

print("PASS — چکِ رگرسیونِ v1.14.168: سلف‌تستِ پلِ پدل (APKِ قدیمی = "
      "فالبکِ خودکارِ ONNX با پیامِ روشن، نه خطایِ هر کراپ)؛ گاردِ "
      "TypeError در run؛ همهٔ خواندنهایِ پروب/بن با with بسته شد؛ پلِ "
      "۶آرگومانیِ byte[] برایِ APKِ جدید سرِ جایش")
