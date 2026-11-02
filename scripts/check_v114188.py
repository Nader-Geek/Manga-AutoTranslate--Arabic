#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.188 — مدلِ v6_medium رویِ گوشی + PC + ضدِ چرت‌پرت.

دستورِ سازنده (نقلِ مستقیم):
  «چرت پرت هم زیاد استخراج میکنه نمیشه یک کاری کرد از نسخهٔ پی سی
   استخراج استفاده کنه همون مدل onnx v6 ocr با همون سرعت استخراج ک تو
   گوشی هست مدل v6_medium استفاده کن بعد توجه ک کردم رو پی سی هم ناقص
   استخراج میشه رو اونم چک کن هردوشو چک بزن»

گیتها:
  A. نسخه = 1.14.188 / versionCode=193 در VERSION + gradle + APP_VER.
  B. manga.py — گوشی: PaddleAndroidOCR با det=PP-OCRv6_small +
     rec=PP-OCRv6_medium (باندلِ APK)؛ پیامِ «روشِ استخراج» با
     PP-OCRv6. PC: هر دو call-site از _pc_ocr_small() استفاده میکنند
     (پیشفرض = ستِ mediumِ K3؛ MANGA_OCR_SMALL=1/امولاتور = ستِ سبکِ
     CI). ضدِ چرت‌پرت: _line_is_foreign188 (مالکیتِ خطِ ناحیهٔ مجاور) +
     _latin_junk_line188 (خطِ آشغالِ لاتین) — رویِ هر دو مسیر (PC و
     اندروید) داخلِ _ocr_crop (حلقهٔ واریانت‌ها + نجاتِ لبه).
  C. PaddleOcrBridge.kt — واریانتهایِ ja/ko؛ latin/zh = recِ پیشفرضِ
     medium (rec_en حذف)؛ sdkInfo = v6.
  D. ppocr-sdk — ارتفاعِ rec = ۴۸ (ورودیِ v6_medium هم ۴۸ است) +
     CTCِ داینامیک (۱۸۷۱۰ کلاس از خروجیِ مدل خوانده میشود).
  E. CI — build.yml + android-emulator.yml باندلِ v6 (det small + rec
     MEDIUM + ppocrv6_chars)؛ بدونِ rec_en؛ fetch_models.yml charsetِ
     ۱۸۷۰۸ی را از inference.ymlِ رسمی میسازد.
  F. py_compile + نمادهایِ PC + تستِ عملیِ فیلترها.
"""

import ast
import io
import os
import py_compile
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

FAILS = []


def ok(msg):
    print(f"[✓] {msg}")


def fail(msg):
    FAILS.append(msg)
    print(f"[✗] {msg}")


def gate(cond, msg):
    if cond:
        ok(msg)
    else:
        fail(msg)


# ── A. نسخه ─────────────────────────────────────────────────────────
try:
    _v = {}
    for ln in open("VERSION", encoding="utf-8"):
        k, _, val = ln.strip().partition("=")
        _v[k.strip()] = val.strip()
    gate(_v.get("versionCode") == "193"
         and _v.get("versionName") == "1.14.188",
         "A: VERSION = 1.14.188 / versionCode=193")
except Exception as e:
    fail(f"A: VERSION خوانده نشد: {e}")

_gradle = open("android/app/build.gradle.kts", encoding="utf-8").read()
gate('versionCode = 193' in _gradle
     and 'versionName = "1.14.188"' in _gradle,
     "A: build.gradle.kts = 193 / 1.14.188")

_manga = io.open("manga.py", encoding="utf-8").read()
gate('APP_VER = "1.14.188"' in _manga, "A: APP_VERِ manga.py = 1.14.188")

# ── B. manga.py ─────────────────────────────────────────────────────
try:
    _tree = ast.parse(_manga)
except SyntaxError as e:
    fail(f"B: manga.py سینتکس ندارد: {e}")
    _tree = None

# B1. PC = ستِ medium با گیتِ سبکِ CI
gate("def _pc_ocr_small()" in _manga
     and 'os.environ.get("MANGA_OCR_SMALL"' in _manga
     and "_android_x86_emulator()" in _manga.split(
         "def _pc_ocr_small(")[1].split("\ndef ")[0],
     "B1: _pc_ocr_small = MANGA_OCR_SMALL/امولاتور → ستِ سبک؛ پیشفرضِ PC = medium")
gate(_manga.count("small=_pc_ocr_small()") >= 2,
     f"B1: هر دو call-siteِ PC از _pc_ocr_small استفاده میکنند "
     f"({_manga.count('small=_pc_ocr_small()')} جای)")

# B2. گوشی = v6 باندل
_cls = ""
if _tree is not None:
    for n in _tree.body:
        if isinstance(n, ast.ClassDef) and n.name == "PaddleAndroidOCR":
            _cls = ast.get_source_segment(_manga, n) or ""
for _frag in ("det=PP-OCRv6_small", "rec=PP-OCRv6_medium/",
              "RapidOcrAndroidOnnx", "باندلِ APK",
              "com.amirwolf.mangatranslator.PaddleOcrBridge"):
    if _frag not in _cls:
        fail(f"B2: PaddleAndroidOCR فاقدِ {_frag!r}")
if "PP-OCRv4_mobile" in _cls:
    fail("B2: PaddleAndroidOCR هنوز رشتهٔ v4_mobile دارد")
ok("B2: PaddleAndroidOCR = detِ v6_small + recِ v6_medium باندل")
for _frag in ("PP-OCRv6ِ باندل (det=small + rec=MEDIUM — ",
              '_K3_MODES = ("padandroid",)'):
    if _frag not in _manga:
        fail(f"B2: پیام/نردبانِ اندروید فاقدِ {_frag!r}")

# B3. ضدِ چرت‌پرت — تعریفها + فراخوانیها (واریانت + نجاتِ لبه)
gate(_manga.count("def _line_is_foreign188(") == 1
     and _manga.count("def _latin_junk_line188(") == 1
     and _manga.count("def _latin_lang188(") == 1,
     "B3: سه helperِ ضدِ چرت‌پرت تعریف شدهاند")
gate(_manga.count("_line_is_foreign188(") >= 3
     and _manga.count("_latin_junk_line188(") >= 3,
     "B3: هر دو فیلتر در حلقهٔ واریانت‌ها + نجاتِ لبه صدا زده میشوند")
gate("if len(_keep188) != len(entries):" in _manga
     and '" ".join(e[0] for e in entries).strip()' in _manga,
     "B3: حذفِ خط → بازسازیِ txt/polys/conf همان واریانت")

# B4. PC بیت‌به‌بیتِ لازم — جدولِ مدلها + dictِ medium سر جایش
for _frag in ("PP-OCRv6_medium_det_onnx.onnx",
              "PP-OCRv6_medium_rec_onnx.onnx",
              "PP-OCRv6_det_small.onnx",
              '"ppocrv6_chars.txt"',
              'if _rec_n52 in ("PP-OCRv6_medium_rec_onnx.onnx",'):
    if _frag not in _manga:
        fail(f"B4: نمادِ PCِ {_frag!r} افتاده")
ok("B4: جدولِ مدلهایِ PC + نگاشتِ dictِ medium سر جایش")

# B5. تستِ عملیِ فیلترها (بدونِ importِ manga.py — execِ همان دو تابع)
_g = {"re": __import__("re")}
for _fn in ("_latin_junk_line188", "_line_is_foreign188"):
    _seg = ""
    for n in (_tree.body if _tree else []):
        if isinstance(n, ast.FunctionDef) and n.name == _fn:
            _seg = ast.get_source_segment(_manga, n) or ""
    if not _seg:
        fail(f"B5: {_fn} استخراج نشد")
        continue
    exec(compile(_seg, _fn, "exec"), _g)
_junk = _g["_latin_junk_line188"]
for _t in ("FL", "SS", "Px", "23", "豊", "H/", "77,I", "", "   "):
    if not _junk(_t):
        fail(f"B5: {_t!r} باید آشغال باشد")
for _t in ("GO! EVEN FASTER...", "Wha!?", "OK", "Alright!", "I",
           "THE VILLA'S POOL IS NOT BAD FOR RELAXING, BUT..."):
    if _junk(_t):
        fail(f"B5: {_t!r} نباید آشغال باشد")
_foreign = _g["_line_is_foreign188"]
# سناریوی img6: ناحیهٔ بزرگِ زرد #02 (60,34,356,674) + همسایهٔ تنگ #04
_own02 = float((356 - 60) * (674 - 34))
_blks02 = [(6, 414, 157, 638)]  # rectِ #04 (x1,y1,x2,y2)
_line_ya = (70.0, 430.0, 140.0, 470.0)   # «You're» — داخلِ #04
if not _foreign(_line_ya, _blks02, _own02):
    fail("B5: خطِ حبابِ مجاورِ تنگتر باید حذف شود (سناریوی img6 #02)")
_line_self = (200.0, 120.0, 320.0, 160.0)  # «THEN I'LL…» — خودِ #02
if _foreign(_line_self, _blks02, _own02):
    fail("B5: خطِ خودِ ناحیه نباید حذف شود")
_line_big = (500.0, 120.0, 700.0, 160.0)   # بیرونِ همسایه
if _foreign(_line_big, _blks02, _own02):
    fail("B5: خطِ بیرونِ همسایه نباید حذف شود")
ok("B5: فیلترهایِ ضدِ چرت‌پرت = سناریوی img6 (#02/#04) + نمونه‌هایِ متن")

# ── C. PaddleOcrBridge.kt ───────────────────────────────────────────
_kt = io.open(os.path.join(
    "android", "app", "src", "main", "java", "com", "amirwolf",
    "mangatranslator", "PaddleOcrBridge.kt"),
    encoding="utf-8", errors="ignore").read()
for _frag in ("object PaddleOcrBridge", "fun recognizeAuto(",
              "\"META|", "RapidOcr.create", "LANG_VARIANTS",
              "models/det/inference.onnx", "models/rec/inference.onnx",
              "models/rec/dict.txt",
              "models/rec_ja/inference.onnx", "models/rec_ko/inference.onnx",
              "PP-OCRv6_MEDIUM", "setLanguageVariant", "ERR|"):
    if _frag not in _kt:
        fail(f"C: PaddleOcrBridge.kt فاقدِ {_frag!r}")
if "models/rec_en/" in _kt:
    fail("C: پل هنوز مسیرِ rec_en دارد (v1.14.188: latin = پیشفرضِ medium)")
ok("C: پل = detِ v6_small + recِ پیشفرضِ v6_MEDIUM؛ واریانتِ ja/ko")

# ── D. ppocr-sdk ────────────────────────────────────────────────────
_rec = io.open(os.path.join(
    "android", "ppocr-sdk", "src", "main", "java", "com", "paddle",
    "ocr", "preprocess", "RecPreprocessor.kt"),
    encoding="utf-8", errors="ignore").read()
gate("FIXED_HEIGHT = 48" in _rec,
     "D: ارتفاعِ rec = ۴۸ (ورودیِ v6_medium هم ۴۸ است)")
_ctc = io.open(os.path.join(
    "android", "ppocr-sdk", "src", "main", "java", "com", "paddle",
    "ocr", "postprocess", "CTCDecoder.kt"),
    encoding="utf-8", errors="ignore").read()
gate("numClasses = shape[2].toInt()" in _ctc,
     "D: CTC کلاسها را از خروجیِ مدل میخواند (v6 = ۱۸۷۱۰)")
_mdl = io.open(os.path.join(
    "android", "ppocr-sdk", "src", "main", "java", "com", "paddle",
    "ocr", "model", "ModelConfig.kt"),
    encoding="utf-8", errors="ignore").read()
gate("fun fromDictText(" in _mdl and 'add(" ")' in _mdl,
     "D: دیکشنریِ ۱۸۷۰۸یِ v6 + فاصلهٔ خودکار")

# ── E. CI ───────────────────────────────────────────────────────────
for _wf in (".github/workflows/build.yml",
            ".github/workflows/android-emulator.yml"):
    _w = io.open(_wf, encoding="utf-8").read()
    for _frag in ("PP-OCRv6_det_small.onnx",
                  "PP-OCRv6_medium_rec_onnx.onnx",
                  "ppocrv6_chars.txt",
                  "ch_ppocr_mobile_v2.0_cls_mobile.onnx",
                  "japan_PP-OCRv4_rec_mobile.onnx",
                  "korean_PP-OCRv4_rec_mobile.onnx",
                  "$A/rec/dict.txt",
                  "mkdir -p $A/det $A/cls $A/rec $A/rec_ja $A/rec_ko",
                  "test $(stat -c%s $A/rec/inference.onnx) -gt 60000000"):
        if _frag not in _w:
            fail(f"E: {_wf} فاقدِ {_frag!r}")
    if "rec_en" in _w:
        fail(f"E: {_wf} هنوز rec_en را میگیرد")
ok("E: build.yml + android-emulator.yml = باندلِ v6 "
   "(det=small + rec=MEDIUM + charsetِ ۱۸۷۰۸ی) — بدونِ rec_en")

_fm = io.open(".github/workflows/fetch_models.yml", encoding="utf-8").read()
gate("PP-OCRv6_medium_rec_onnx/resolve/main/inference.yml" in _fm
     and "ppocrv6_chars.txt" in _fm and "18708" in _fm,
     "E: fetch_models.yml = ساختِ charsetِ ۱۸۷۰۸ی از ymlِ رسمی")

# ── F. کامپایل + نمادهایِ PC ────────────────────────────────────────
try:
    py_compile.compile("manga.py", doraise=True)
    ok("F: py_compileِ manga.py")
except Exception as e:
    fail(f"F: manga.py کامپایل نمیشود: {e}")

for _pc in ("lama-manga", "RapidOCRBackend", "RTDetrV2ONNXDetector",
            "_ensure_rapidocr_models", "_rapidocr_model_pair"):
    if _pc not in _manga:
        fail(f"F: نمادِ PCِ {_pc!r} از manga.py افتاده!")
gate(_manga.count("_android_gate(") >= 8,
     f"F: گیتِ اندروید/PC پابرجاست ({_manga.count('_android_gate(')} فراخوانی)")
ok("F: نمادهایِ PC سر جایشاند")

# ── پایان ───────────────────────────────────────────────────────────
print()
if FAILS:
    print(f"[✗] {len(FAILS)} گیتِ v1.14.188 شکست خورد")
    sys.exit(1)
print("[✓] همهٔ گیتهایِ v1.14.188 PASS — گوشی = recِ v6_MEDIUM + "
      "detِ v6_small باندل؛ PC = ستِ medium؛ ضدِ چرت‌پرت رویِ هر دو مسیر")
