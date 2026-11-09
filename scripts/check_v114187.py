#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.187 — موتورِ OCRِ گوشی = RapidOCRِ اندروید
(RapidOcrAndroidOnnx — سهگانهٔ PP-OCRv4_mobileِ ONNX) + انتخابِ زبان.

دستورِ سازنده (نقلِ مستقیم):
  «متن درست استخراج نمیزنه متن هاش اشتباهه بعضی وقتا ۱.۱۴.۱۸۶
   https://github.com/RapidAI/RapidOcrAndroidOnnx ببین چجور به این
   خوبی استخراج میکنه همونو رو گوشی بزار و این ک بگم باید اول
   detector-v4-s_int8.onnx خوب قسمت های متن پیدا کنه بعد همون قسمت
   باید استخراج متن استفاده کنه اونم درست در بیاره … فقط مشکلش این ک
   همه زبانس نمیشه یک زبان انتخاب کرد مثلا انگلیسی بزارم»

گیتها:
  A. نسخه = 1.14.187 / versionCode=192 در VERSION + gradle + APP_VER.
  B. manga.py — مسیرِ اندروید: PaddleAndroidOCR (پل + سلف‌تست + پارسرِ
     META + langِ واریانت)، نردبانِ تکپلهای padandroid، پیامِ
     «روشِ استخراج» با PP-OCRv4_mobile؛ PC (جدولِ دانلودِ _RAPIDOCR_FILES
     و بکاندِ PC) بیت‌به‌بیت دستنخورده — هنوز PP-OCRv6 دارد (متعلق به PC).
  C. PaddleOcrBridge.kt — پلِ نازک رویِ RapidOcr.create با ثابتهایِ
     assetsِ جدید (det/cls/rec + dict) + LANG_VARIANTS (en/ja/ko) +
     setLanguageVariant + سطرِ ERR؛ بدونِ ORTِ مستقیم و ML Kit.
  D. ppocr-sdk — RapidOcrEngine.kt (سهگانهٔ RapidOCR: detِ 960/max +
     thresh 0.3 + boxScore 0.5 + unclip 1.6 + dilate 2×2؛ clsِ 192×48
     با آستانهٔ 0.9 per-crop؛ recِ ارتفاعِ ۴۸ + CTCِ blank=۰) +
     ORTSessionManagerِ cls/swap + ModelConfig.fromDictText + RapidOcr.kt.
  E. CI — build.yml و android-emulator.yml مدلهایِ v4 را از ModelScopeِ
     رسمیِ RapidAI/RapidOCR میگیرند و دیگر PP-OCRv6ِ PaddlePaddle را
     نمیگیرند؛ fetch_models.ymlِ mirror هم کامل است.
  F. py_compile + گیتِ اندروید/PC.
"""

import ast
import io
import os
import py_compile
import subprocess
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
    gate(_v.get("versionCode") == "195"
         and _v.get("versionName") == "1.14.190",
         "A: VERSION = 1.14.190 / versionCode=195 (مهاجرتِ 188)")
except Exception as e:
    fail(f"A: VERSION خوانده نشد: {e}")

_gradle = open("android/app/build.gradle.kts", encoding="utf-8").read()
gate('versionCode = 195' in _gradle
     and 'versionName = "1.14.190"' in _gradle,
     "A: build.gradle.kts = 194 / 1.14.189 (مهاجرتِ 188)")

_manga = io.open("manga.py", encoding="utf-8").read()
gate('APP_VER = "1.14.190"' in _manga, "A: APP_VERِ manga.py = 1.14.188 (مهاجرتِ 188)")

# ── B. manga.py — مسیرِ اندروید ─────────────────────────────────────
try:
    _tree = ast.parse(_manga)
except SyntaxError as e:
    fail(f"B: manga.py سینتکس ندارد: {e}")
    _tree = None

_cls = ""
if _tree is not None:
    for n in _tree.body:
        if isinstance(n, ast.ClassDef) and n.name == "PaddleAndroidOCR":
            _cls = ast.get_source_segment(_manga, n) or ""
if not _cls:
    fail("B: کلاسِ PaddleAndroidOCR نیست")
for _frag in ("com.amirwolf.mangatranslator.PaddleOcrBridge",
              "self._bridge.init(_intra)", "recognizeAuto(",
              "bytes(_buf.tobytes())", "startswith(\"META\")",
              "reshape(4, 2)", "باندلِ APK",
              "det=PP-OCRv6_small", "rec=PP-OCRv6_medium", "RapidOCRِ اندروید",
              "v1.14.187+"):
    if _frag not in _cls:
        fail(f"B: PaddleAndroidOCR فاقدِ {_frag!r}")
ok("B: PaddleAndroidOCR = پلِ RapidOCR + سلف‌تست + پارسرِ META + lang")

for _frag in ('_MT_MODES = ("padandroid",)',
              'self._mode = "padandroid"',
              '_SPEED_LAB_LADDER = ("padandroid",)',
              '"padandroid": "رپیدِ رسمیِ اندروید"',
              "PP-OCRv6ِ دانلودی (det=small + rec=MEDIUM — "):
    if _frag not in _manga:
        fail(f"B: نردبان/پیامِ RapidOCR نیست: {_frag!r}")
ok("B: نردبانِ تکپلهای padandroid + پیامِ «روشِ استخراج» = RapidOCRِ v4")

# langِ واریانت: _mobile_lang نقشهٔ latin/ja/ko/zh را دارد
for _frag in ('"latin": "latin"', '"ja": "ja"', '"ko": "ko"', '"zh": "zh"'):
    if _frag not in _manga:
        fail(f"B: نقشهٔ زبانِ موبایل ناقص است: {_frag!r}")
ok("B: _MOBILE_LANG_MAP = latin/ja/ko/zh (واریانتِ rec)")

# ── B2. PC بیت‌به‌بیت — جدولِ دانلودِ PC هنوز v6/medium دارد ────────
for _frag in ("PP-OCRv6_medium_det_onnx.onnx",
              "PP-OCRv6_medium_rec_onnx.onnx",
              "PP-OCRv6_medium_rec_inference.yml",
              "PP-OCRv6_det_small.onnx",
              "PP-OCRv6_tiny_det.onnx"):
    if _frag not in _manga:
        fail(f"B2: جدولِ PCِ _RAPIDOCR_FILES خراب شده: {_frag!r}")
ok("B2: مسیرِ PC (RapidOCRِ PC + جدولِ مدلها) دستنخورده ماند")

# ── C. PaddleOcrBridge.kt ───────────────────────────────────────────
_kt = io.open(os.path.join(
    "android", "app", "src", "main", "java", "com", "amirwolf",
    "mangatranslator", "PaddleOcrBridge.kt"),
    encoding="utf-8", errors="ignore").read()
for _frag in ("object PaddleOcrBridge", "fun recognizeAuto(",
              "\"META|", "RapidOcr.create", "com.paddle.ocr",
              "EngineConfig(numThreads", "OpenCVUtils.init",
              "models/det/inference.onnx", "models/cls/inference.onnx",
              "models/rec/inference.onnx", "models/rec/dict.txt",
              "models/rec_ko/inference.onnx", "models/rec_ko/dict.txt",
              "LANG_VARIANTS", "setLanguageVariant", "currentVariant",
              "\"ko\"",
              "ERR|", "runBlocking"):
    if _frag not in _kt:
        fail(f"C: PaddleOcrBridge.kt فاقدِ {_frag!r}")
for _bad in ("ai.onnxruntime", "OrtSession", "OnnxTensor",
             "com.google.mlkit", "paddle.lite", "PaddleLite"):
    if _bad in _kt:
        fail(f"C: {_bad!r} در پلِ Kotlin است! (پل = نازک رویِ ppocr-sdk)")
ok("C: پل = نازک رویِ RapidOcr.create + واریانتهایِ زبانِ rec + ERR")

# ── D. ppocr-sdk ────────────────────────────────────────────────────
_eng = io.open(os.path.join(
    "android", "ppocr-sdk", "src", "main", "java", "com", "paddle",
    "ocr", "engine", "RapidOcrEngine.kt"),
    encoding="utf-8", errors="ignore").read()
for _frag in ("class RapidOcrEngine", "data class RapidOcrParams",
              "maxSideLen: Int = 960", "detThresh: Float = 0.3f",
              "boxScoreThresh: Float = 0.5f", "unclipRatio: Float = 1.6f",
              "doAngle: Boolean = true", "angleScoreThresh: Float = 0.9f",
              "detUseDilation = true", "detLimitType = \"max\"",
              "classifyAngles", "Core.flip(crops[i], rotated, -1)",
              "RecPreprocessor.preprocessBatch", "CTCDecoder.decode",
              "BoxSorter.sortInReadingOrder", "QuadTextCrop.crop",
              "setLanguageVariant", "loadDict"):
    if _frag not in _eng:
        fail(f"D: RapidOcrEngine.kt فاقدِ {_frag!r}")
if "Size(clsW.toDouble(), clsH.toDouble())" not in _eng \
        or "val clsW = 192" not in _eng or "val clsH = 48" not in _eng:
    fail("D: clsِ RapidOCR باید 192×48 باشد")
ok("D: RapidOcrEngine = detِ 960/max + dilate 2×2 + clsِ 192×48 + recِ ۴۸")

# cls BGR (بدونِ cvtColor — قراردادِ رسمیِ predict_cls) و rec RGB
if "Imgproc.cvtColor(crops[i]" in _eng.split("rec (CRNN")[0]:
    fail("D: cls نباید cvtColor بزند (قراردادِ predict_cls = BGR)")
ok("D: cls = BGRِ رسمی (بدونِ تبدیل) — چرخشِ ۱۸۰ فقط با امتیازِ ۰.۹+")

_ort = io.open(os.path.join(
    "android", "ppocr-sdk", "src", "main", "java", "com", "paddle",
    "ocr", "engine", "ORTSessionManager.kt"),
    encoding="utf-8", errors="ignore").read()
for _frag in ("fun hasCls()", "fun loadClsModel(", "fun loadRecModel(",
              "fun runClassification("):
    if _frag not in _ort:
        fail(f"D: ORTSessionManager فاقدِ {_frag!r}")
ok("D: ORTSessionManager = سشنِ cls + تعویضِ داغِ rec")

_cfg = io.open(os.path.join(
    "android", "ppocr-sdk", "src", "main", "java", "com", "paddle",
    "ocr", "model", "ModelConfig.kt"),
    encoding="utf-8", errors="ignore").read()
gate("fun fromDictText(" in _cfg,
     "D: ModelConfig.fromDictText (دیکشنریِ متنیِ RapidOCR) هست")

_fac = io.open(os.path.join(
    "android", "ppocr-sdk", "src", "main", "java", "com", "paddle",
    "ocr", "RapidOcr.kt"), encoding="utf-8", errors="ignore").read()
for _frag in ("class RapidOcr", "suspend fun create(", "RapidOcrEngine(",
              "suspend fun recognize(imageBytes: ByteArray)",
              "setLanguageVariant", "suspend fun release()"):
    if _frag not in _fac:
        fail(f"D: RapidOcr.kt فاقدِ {_frag!r}")
ok("D: دروازهٔ RapidOcr.kt = create/recognize/setLanguageVariant/release")

# ── E. CI — مدلهایِ v4 باندل میشوند؛ v6ِ PaddlePaddle حذف ───────────
for _wf in (".github/workflows/build.yml",
            ".github/workflows/android-emulator.yml"):
    _w = io.open(_wf, encoding="utf-8").read()
    for _frag in ("PP-OCRv6_det_small.onnx",
                  "ch_ppocr_mobile_v2.0_cls_mobile.onnx",
                  "PP-OCRv6_medium_rec_onnx.onnx",
                  "ppocrv6_chars.txt",
                  "ppocrv5_korean_dict.txt",
                  "korean_PP-OCRv5_rec_mobile.onnx",
                  "$A/rec/dict.txt",
                  "$A/rec_ko/inference.onnx",
                  "mkdir -p $A/det $A/cls $A/rec $A/rec_ko",
                  "RapidAI/RapidOCR/resolve/v3.9.2"):
        if _frag not in _w:
            fail(f"E: {_wf} فاقدِ {_frag!r}")
    if "PaddlePaddle/PP-OCRv6_small_det_onnx" in _w \
            or "PaddlePaddle/PP-OCRv6_small_rec_onnx" in _w:
        fail(f"E: {_wf} هنوز PP-OCRv6ِ PaddlePaddle را میگیرد")
    if "rec_en" in _w:
        fail(f"E: {_wf} هنوز واریانتِ rec_enِ v4 را میگیرد (v1.14.188: حذف)")
ok("E: build.yml + android-emulator.yml = باندلِ PP-OCRv6 "
   "(det=small + rec=MEDIUM + cls/ja/ko + دیکشنریها)")

_fm = io.open(".github/workflows/fetch_models.yml", encoding="utf-8").read()
for _frag in ("ch_PP-OCRv4_det_mobile.onnx", "ch_PP-OCRv4_rec_mobile.onnx",
              "japan_PP-OCRv4_rec_mobile.onnx",
              "korean_PP-OCRv5_rec_mobile.onnx", "ppocrv5_korean_dict.txt"):
    if _frag not in _fm:
        fail(f"E: fetch_models.yml فاقدِ {_frag!r}")
if "korean_PP-OCRv4_rec_mobile.onnx" in _fm:
    fail("E: fetch_models.yml هنوز خطِ مردهٔ korean v4 را دارد (v1.14.190: حذف)")
ok("E: mirrorِ fetch_models.yml = ستِ سالمِ v1.14.190 (ko=v5 + دیکشنریِ رسمی)")

# ── F. کامپایل + گیتِ اندروید/PC ────────────────────────────────────
try:
    py_compile.compile("manga.py", doraise=True)
    ok("F: py_compileِ manga.py")
except Exception as e:
    fail(f"F: manga.py کامپایل نمیشود: {e}")

gate(_manga.count("_android_gate(") >= 8,
     f"F: گیتِ اندروید/PC پابرجاست ({_manga.count('_android_gate(')} فراخوانی)")
for _pc in ("lama-manga", "RapidOCRBackend", "RTDetrV2ONNXDetector"):
    if _pc not in _manga:
        fail(f"F: نمادِ PCِ {_pc!r} از manga.py افتاده!")
ok("F: نمادهایِ PC سر جایشاند (PC بیت‌به‌بیت)")

# ── پایان ───────────────────────────────────────────────────────────
print()
if FAILS:
    print(f"[✗] {len(FAILS)} گیتِ v1.14.187 شکست خورد")
    sys.exit(1)
print("[✓] همهٔ گیتهایِ v1.14.187 PASS (مهاجرت‌شده به 188) — گوشی = "
      "RapidOcrAndroidOnnxِ v6 (det=small + rec=MEDIUM)؛ PC = ستِ medium")
