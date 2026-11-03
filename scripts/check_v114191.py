#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.191 — «خروجیها اوکی شد؛ حالا PC هم مثلِ گوشی سریع
استخراج کند + سیستمِ قدیمیِ PC هم اوکی شود».

گیتها:
  A. نسخه = 1.14.191 / versionCode=196 (manga.py + manga_app.py +
     VERSION + gradle) + خطِ لاگِ گوشی.
  B. PC = عینِ ستِ گوشی (دستور: «مثل گوشی پی سی لینوکس هم استخراجش
     سریع باشه») — detِ همهٔ زبانها = PP-OCRv6_det_small (۱۰MB — همان
     detِ گوشی؛ قبلاً mediumِ ۵۹MB) + zh از جفتِ قدیمیِ ch_PP-OCRv4 به
     recِ v6_medium (عینِ گوشی — بنچمارک: فاصلههایِ لاتین و ویرگولِ
     تکراریِ v4) + ko = PP-OCRv5_korean (ثابت) + فرارِ
     MANGA_OCR_DET_MEDIUM=1 (رفتارِ قبلی) + small/tiny (CI) دستنخورده.
  C. نخِ OCRِ PC = ۲ (عینِ گوشی) — شاخهٔ «۸ نخِ x86» (SRV-L؛ مالِ دورانِ
     پاسِ تمامصفحه — از v1.14.163 OCR فقط کراپ است) حذف؛ اوررایدهایِ
     MANGA_OCR_THREADS/MANGA_ORT_THREADS مقدم (ثابت).
  D. همترازیِ workers × threads ≈ هسته‌ها بعد از ساختِ موتور (ضدِ تشتتِ
     ۷ورکر×۸نخ رویِ ۸ هسته) — فقط PC؛ اندروید دستنخورده.
  E. دیکشنریِ recِ medium/korean برایِ zh هم کشیده میشود (شرطِ
     rec_keys_path هر دو نام را دارد — zh حالا به همان شاخه میافتد).
  F. py_compile + YAML + تستِ عملیِ جفتِ مدل + رگرسیونهایِ کلیدیِ
     v1.14.190 (sinkِ پیشرفتِ دانلود، ko=v5، multi، initِ همیشه-ensure).
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
    return cond


_manga = io.open("manga.py", encoding="utf-8").read()
_manga_app = io.open("manga_app.py", encoding="utf-8").read()
_gradle = io.open("android/app/build.gradle.kts", encoding="utf-8").read()
_bridge_kt = io.open(
    "android/app/src/main/java/com/amirwolf/mangatranslator/PaddleOcrBridge.kt",
    encoding="utf-8").read()
_store_kt = io.open(
    "android/app/src/main/java/com/amirwolf/mangatranslator/OcrModelStore.kt",
    encoding="utf-8").read()
_sink_kt = io.open(
    "android/ppocr-sdk/src/main/java/com/paddle/ocr/util/OcrProgressSink.kt",
    encoding="utf-8").read()

# ── A. نسخه ──────────────────────────────────────────────────────────
gate('APP_VER = "1.14.191"' in _manga, "A: APP_VERِ manga.py = 1.14.191")
gate('APP_VER = "1.14.191"' in _manga_app, "A: APP_VERِ manga_app.py = 1.14.191")
_v = {}
try:
    for ln in open("VERSION", encoding="utf-8"):
        if "=" in ln:
            k, val = ln.strip().split("=", 1)
            _v[k] = val
    gate(_v.get("versionCode") == "196"
         and _v.get("versionName") == "1.14.191",
         "A: VERSION = 1.14.191 / versionCode=196")
except Exception as e:
    fail(f"A: VERSION خوانده نشد: {e}")
gate("versionCode = 196" in _gradle and 'versionName = "1.14.191"' in _gradle,
     "A: build.gradle.kts = 196 / 1.14.191")
gate("دانلودی — v1.14.191" in _manga, "A: خطِ لاگِ آمادهشدنِ موتورِ گوشی = v1.14.191")

# ── B. PC = عینِ ستِ گوشی ────────────────────────────────────────────
gate("def _pc_det_medium()" in _manga
     and 'os.environ.get("MANGA_OCR_DET_MEDIUM"' in _manga,
     "B: سوئیچِ فرارِ MANGA_OCR_DET_MEDIUM تعریف شد")
gate('"PP-OCRv6_medium_det_onnx.onnx" if _pc_det_medium()' in _manga,
     "B: detِ پیشفرضِ PC = smallِ گوشی (medium فقط با سوئیچِ فرار)")
gate('return "ch_PP-OCRv4_det_infer.onnx", "ch_PP-OCRv4_rec_infer.onnx"'
     not in _manga,
     "B: جفتِ قدیمیِ ch_PP-OCRv4 از مسیرِ پیشفرضِ zh حذف شد")
gate("# v1.14.191 — zh هم از همین rec (عینِ گوشی — جفتِ v4 حذف شد)" in _manga,
     "B: کامنتِ تصمیمِ zh = v6_medium")

# — تستِ عملیِ جفتِ مدل (بدونِ بارگذاریِ کاملِ manga) ————————————
try:
    tree = ast.parse(_manga)
    ns = {"os": os}
    _found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in (
                "_rapidocr_model_pair", "_pc_det_medium",
                "_pc_ocr_small", "_android_x86_emulator"):
            exec(ast.unparse(node), ns)
            _found.add(node.name)
    if "_android_x86_emulator" not in _found:
        ns["_android_x86_emulator"] = lambda: False
    gate("_rapidocr_model_pair" in _found and "_pc_det_medium" in _found,
         "B: توابعِ جفتِ مدل پیدا شدند")
    os.environ.pop("MANGA_OCR_DET_MEDIUM", None)
    f = ns["_rapidocr_model_pair"]
    gate(f("en") == ("PP-OCRv6_det_small.onnx", "PP-OCRv6_medium_rec_onnx.onnx"),
         "B: en = detِ smallِ گوشی + recِ medium (عینِ گوشی)")
    gate(f("zh") == ("PP-OCRv6_det_small.onnx", "PP-OCRv6_medium_rec_onnx.onnx"),
         "B: zh = detِ smallِ گوشی + recِ v6_medium (عینِ گوشی — بنچمارک)")
    gate(f("korean") == ("PP-OCRv6_det_small.onnx", "PP-OCRv5_korean_rec.onnx"),
         "B: ko = detِ smallِ گوشی + recِ رسمیِ v5 (ثابت)")
    gate(f("japan") == ("PP-OCRv6_det_small.onnx", "PP-OCRv6_medium_rec_onnx.onnx"),
         "B: ja = detِ smallِ گوشی + recِ v6_medium (تصمیمِ ۱۹۰ — ثابت)")
    gate(f("en", small=True) == ("PP-OCRv6_det_small.onnx", "PP-OCRv6_rec_small.onnx"),
         "B: small=True (CI) دستنخورده — recِ small")
    gate(f("en", tiny=True) == ("PP-OCRv6_tiny_det.onnx", "PP-OCRv6_tiny_rec.onnx"),
         "B: tiny=True (فلاتر-پدل) دستنخورده")
    os.environ["MANGA_OCR_DET_MEDIUM"] = "1"
    gate(f("en")[0] == "PP-OCRv6_medium_det_onnx.onnx",
         "B: MANGA_OCR_DET_MEDIUM=1 → detِ mediumِ قبلی (K3) برمیگردد")
    os.environ.pop("MANGA_OCR_DET_MEDIUM", None)
except Exception as e:
    fail(f"B: تستِ جفتِ مدل: {e}")

# ── C. نخِ OCRِ PC = ۲ ───────────────────────────────────────────────
gate("# v1.14.191 — PC هم عینِ گوشی: ۲ نخ برایِ هر سشنِ OCR." in _manga
     and "                _intra = 2" in _manga,
     "C: شاخهٔ PC — intra = 2 (عینِ گوشی)")
gate("if _pfo.machine().lower() in (\"x86_64\", \"amd64\")" not in _manga,
     "C: شاخهٔ «۸ نخِ x86_64» (SRV-L — دورانِ پاسِ تمامصفحه) حذف شد")
gate("self.ocr_threads = int(_intra)" in _manga,
     "C: ocr_threads رویِ بکاند ثبت میشود (برایِ همترازیِ D)")

# ── D. همترازیِ workers × threads ≈ هسته‌ها ──────────────────────────
gate("همترازیِ OCR: workers=" in _manga
     and "if self.ocr is not None and not _on_android():" in _manga,
     "D: بلوکِ همترازیِ workers (فقط PC — اندروید دستنخورده)")
gate("_want191 = max(2, min(int(self.max_workers or 2),\n                                      max(1, _cores191 // _thr191)))" in _manga,
     "D: فرمولِ workers = هسته ÷ نخ (سقفِ حداقلِ ۲)")

# ── E. دیکشنریِ zh ───────────────────────────────────────────────────
gate('if _rec_n52 in ("PP-OCRv6_medium_rec_onnx.onnx",\n                                    "PP-OCRv5_korean_rec.onnx"):' in _manga
     and '"ppocrv6_chars.txt"' in _manga,
     "E: شرطِ rec_keys_path — zh حالا از همان شاخه، dictِ ppocrv6 کشیده میشود")

# ── F. کامپایل + رگرسیونهایِ کلیدیِ ۱۹۰ ─────────────────────────────
try:
    py_compile.compile("manga.py", doraise=True)
    ok("F: py_compileِ manga.py")
except Exception as e:
    fail(f"F: py_compile: {e}")
try:
    py_compile.compile("manga_app.py", doraise=True)
    ok("F: py_compileِ manga_app.py")
except Exception as e:
    fail(f"F: py_compileِ manga_app: {e}")
for f in ("android/app/src/main/python/bridge.py",
          "android/app/src/main/python/app_server.py"):
    try:
        py_compile.compile(f, doraise=True)
        ok(f"F: py_compileِ {os.path.basename(f)}")
    except Exception as e:
        fail(f"F: py_compileِ {f}: {e}")
try:
    import yaml
    for y in (".github/workflows/build.yml",
              ".github/workflows/fetch_models.yml",
              ".github/workflows/android-emulator.yml"):
        yaml.safe_load(io.open(y, encoding="utf-8"))
    ok("F: YAMLِ workflowها سالم")
except Exception as e:
    fail(f"F: YAML: {e}")

# — رگرسیونِ ۱۹۰: پیشرفتِ دانلود + ko=v5 + multi + initِ همیشه-ensure —
gate("interface OcrProgressSink" in _sink_kt
     and "fun setProgressSink(sink: OcrProgressSink?)" in _store_kt,
     "F: رگرسیون — sinkِ پیشرفتِ دانلود (۱۹۰) سرِ جایش")
gate('"korean_PP-OCRv5_rec_mobile.onnx" to 12_000_000L' in _store_kt
     and "korean_PP-OCRv4_rec_mobile.onnx" not in _store_kt,
     "F: رگرسیون — ko = v5 + بدونِ v4 (۱۹۰)")
gate('"multi": "multi"' in _manga
     and "def _ocr_multi(self, buf):" in _manga,
     "F: رگرسیون — چندزبانه (۱۹۰): multi → multi + دوئلِ ko")
gate("if (engine != null) return true" in _bridge_kt,
     "F: رگرسیون — initِ همیشه-ensureِ پل (۱۹۰)")

print()
if FAILS:
    print(f"✗ {len(FAILS)} گیتِ مردود:")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ همهٔ گیت‌هایِ v1.14.191 سبز است.")
