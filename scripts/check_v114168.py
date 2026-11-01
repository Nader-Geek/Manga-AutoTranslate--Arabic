#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.170 (بهروزِ 168) — بدونِ وابستگی (فقط ast/فایل):

درسِ 168 («predict takes 5 arguments (6 given)») حالا برایِ پلِ ML Kit:
APKِ قدیمیِ نصبشده MlKitBridge ندارد → سلف‌تستِ دسترسپذیری در
MlKitCropOCR.__init__ باید شکستِ صریحِ یک‌باره بدهد (پیامِ «APKِ جدید»)
تا فالبکِ خودکارِ _mlkit_backend به PP-OCRv6 ONNX فعال شود — نه خطایِ
تکراریِ سرِ هر کراپ.

۱) سلف‌تستِ پلِ ML Kit (recognizeAuto رویِ ۶۴×۶۴؛ پیامِ «APKِ جدید»).
۲) هیچ «open(...).read()»ی بدونِ with در manga.py نمیماند (الگوهایِ عینی).
۳) فالبکِ خودکار: dead + پیامِ ONNX.
۴) نسخه — APP_VER == versionName (مستقل از شمارهٔ نسخه).
"""
import ast
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fail(msg):
    print("[✗]", msg)
    sys.exit(1)


src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
tree = ast.parse(src)
cls = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}

# ۱) سلف‌تستِ پلِ ML Kit در __init__
mk = cls.get("MlKitCropOCR")
if mk is None:
    fail("MlKitCropOCR نیست")
p_init = next((m for m in mk.body
               if isinstance(m, ast.FunctionDef) and m.name == "__init__"),
              None)
if p_init is None:
    fail("MlKitCropOCR.__init__ نیست")
i_src = ast.get_source_segment(src, p_init) or ""
if "recognizeAuto" not in i_src:
    fail("سلف‌تستِ پلِ ML Kit recognizeAuto را صدا نمیزند")
if "(64, 64, 3)" not in i_src:
    fail("سلف‌تستِ ML Kit رویِ کراپِ ریزِ ۶۴×۶۴ نیست")
if "APKِ جدید" not in i_src:
    fail("پلِ غایب (APKِ قدیمی) پیامِ روشنِ «APKِ جدید» ندارد")

# ۲) ResourceWarning — الگوهایِ «فایلِ بستهنشدنی» ممنوع
for bad in ('open(_cachef, "r", encoding="utf-8").read()',
            '(open(p, "r", encoding="utf-8").read() or "")',
            'open(_out, "r", encoding="utf-8").read()',
            'open("plite_banned.txt", "r"'):
    if bad in src:
        fail(f"خواندنِ بدونِ with هنوز هست: {bad!r}")

# ۳) فالبکِ خودکار
fns = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
if "_mlkit_backend" not in fns:
    fail("_mlkit_backend نیست")
mb_src = ""
for n in tree.body:
    if isinstance(n, ast.FunctionDef) and n.name == "_mlkit_backend":
        mb_src = ast.get_source_segment(src, n) or ""
if 'dead"]=True' not in mb_src.replace(" ", ""):
    fail("_mlkit_backend شکست را dead نمیکند (تلاشِ تکراریِ هر کراپ؟)")
if "PP-OCRv6 ONNX" not in mb_src:
    fail("پیامِ فالبکِ ONNX در _mlkit_backend نیست")

# ۴) نسخه — سازگاریِ APP_VER با VERSION
ver = io.open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read()
_m = re.search(r'^APP_VER = "([\d.]+)"', src, re.M)
_vn = re.search(r'^versionName=([\d.]+)', ver, re.M)
if not _m or not _vn:
    fail("APP_VER/VERSION ناقص است")
if _m.group(1) != _vn.group(1):
    fail(f"APP_VER ({_m.group(1)}) با versionName ({_vn.group(1)}) یکی نیست")

print("PASS — چکِ رگرسیونِ v1.14.170/168: سلف‌تستِ پلِ ML Kit (APKِ قدیمی "
      "= فالبکِ خودکارِ ONNX با پیامِ روشن، نه خطایِ هر کراپ)؛ خواندنهایِ "
      "فایل با with؛ APP_VER↔versionName سازگار")
