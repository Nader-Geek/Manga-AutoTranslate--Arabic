#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.190 — چهار ایرادِ جدیدِ سازنده رویِ v1.14.189.

گیتها:
  A. نسخه = 1.14.190 / versionCode=195 (manga.py + manga_app.py +
     VERSION + gradle).
  B. مشکل۱ — پیشرفتِ دانلودِ ONNX در لاگِ اپ: اینترفیسِ
     OcrProgressSink (ppocr-sdk) + setProgressSink در OcrModelStore +
     ثبتِ sinkِ پایتونیِ manga.py قبل از init + خطوطِ ٪ و MB + خطایِ
     دقیق (۴۰۴/اتصال/ناقص) + ۳ تلاش برایِ هر فایل.
  C. مشکل۲ (کره‌ای/چینی — ارورِ آمادهسازی): مدلِ کره‌ای =
     korean_PP-OCRv5_rec_mobile + دیکشنریِ رسمیِ خودش
     ppocrv5_korean_dict.txt (۱۱۹۴۵ نویسه — جفتِ غلطِ v4 حذف) +
     initِ پل همیشه ensure میکند (حتی با موتورِ گرم — ریشهٔ
     ERR|ModelDownload در سلف‌تست).
  D. مشکل۳ (چندزبانه): مقدارِ UI = «multi»؛ pathsForLangِ multi = فقط
     ستِ پایه؛ دوئلِ لازمالآمدِ ko در PaddleAndroidOCR؛
     _ocr_lang_flagsِ multi = همه مجاز؛ main_langِ اندروید = multi.
  E. مشکل۴ (ژاپنیِ ضعیف): واریانتِ rec_ja حذف — recِ پیشفرضِ
     v6_medium برایِ ja (بنچمارکِ صفحهٔ تستِ سازنده)؛ build.ymlِ
     باندلِ تست هم هم‌راستا.
  F. py_compile + YAML + تستهایِ عملی (مپِ زبان، پرچمها،
     pathsForLang، پارسِ META، امتیازدهیِ دوئل).
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
_build_yml = io.open(".github/workflows/build.yml", encoding="utf-8").read()
_fetch_yml = io.open(".github/workflows/fetch_models.yml", encoding="utf-8").read()
_app_server = io.open(
    "android/app/src/main/python/app_server.py", encoding="utf-8").read()

# ── A. نسخه ──────────────────────────────────────────────────────────
gate('APP_VER = "1.14.190"' in _manga, "A: APP_VERِ manga.py = 1.14.190")
gate('APP_VER = "1.14.190"' in _manga_app, "A: APP_VERِ manga_app.py = 1.14.190")
_v = {}
try:
    for ln in open("VERSION", encoding="utf-8"):
        if "=" in ln:
            k, val = ln.strip().split("=", 1)
            _v[k] = val
    gate(_v.get("versionCode") == "195"
         and _v.get("versionName") == "1.14.190",
         "A: VERSION = 1.14.190 / versionCode=195")
except Exception as e:
    fail(f"A: VERSION خوانده نشد: {e}")
gate("versionCode = 195" in _gradle and 'versionName = "1.14.190"' in _gradle,
     "A: build.gradle.kts = 195 / 1.14.190")

# ── B. پیشرفتِ دانلود (لاگِ اپ) ──────────────────────────────────────
gate("interface OcrProgressSink" in _sink_kt
     and "fun onProgress(line: String)" in _sink_kt,
     "B: اینترفیسِ OcrProgressSink در ppocr-sdk")
gate("fun setProgressSink(sink: OcrProgressSink?)" in _store_kt
     and "progressSink?.onProgress(line)" in _store_kt,
     "B: OcrModelStore — sink + فراخوانیِ onProgress")
for frag in ('jclass as _jc, dynamic_proxy as _dp',
             '"com.paddle.ocr.util.OcrProgressSink"',
             '"com.amirwolf.mangatranslator.OcrModelStore"',
             "setProgressSink(_PyDlSink())"):
    gate(frag in _manga, f"B: manga.py — ثبتِ sink: {frag[:44]}")
gate("[دانلود] $asset: $pct% (${mb(done)}/${mb(total)}MB)" in _store_kt,
     "B: خطِ پیشرفتِ درصدی + MB در دانلود")
gate("ModelHttpError" in _store_kt and "HTTP 404" in _store_kt
     and "SocketTimeoutException" in _store_kt,
     "B: خطایِ دقیق (۴۰۴ / HTTP / تایمآوت / اتصال)")
gate("for (attempt in 1..3)" in _store_kt
     and "تلاشِ دوباره" in _store_kt,
     "B: ۳ تلاش برایِ هر فایل (شبکهٔ ناپایدار)")

# ── C. کره‌ای/چینی — جفتِ درست + initِ همیشه-ensure ─────────────────
gate('"korean_PP-OCRv5_rec_mobile.onnx" to 12_000_000L' in _store_kt,
     "C: OcrModelStore — مدلِ کره‌ای = v5 (۱۳.۵MB)")
gate('"ppocrv5_korean_dict.txt" to 40_000L' in _store_kt,
     "C: OcrModelStore — دیکشنریِ رسمیِ v5 (۱۱۹۴۵ نویسه)")
gate("korean_PP-OCRv4_rec_mobile.onnx" not in _store_kt
     and '"models/rec_ja/inference.onnx" to' not in _store_kt,
     "C: جفتِ غلطِ v4 و مدخلِ rec_ja حذف شدند")
gate('curl -fL --retry 3 -o models/ppocrv5_korean_dict.txt' in _fetch_yml
     and 'korean_PP-OCRv5_rec_mobile' in _fetch_yml
     and 'korean_PP-OCRv4_rec_mobile.onnx' not in _fetch_yml,
     "C: fetch_models.yml — v5 + دیکشنری؛ خطِ مردهٔ v4 حذف")
gate("if (engine != null) return true" in _bridge_kt
     and _bridge_kt.index("OcrModelStore.ensure(context,")
     < _bridge_kt.index("if (engine != null) return true"),
     "C: پل — ensureِ همیشه قبل از بازگشتِ زودهنگامِ موتورِ گرم")

# ── D. چندزبانه ──────────────────────────────────────────────────────
gate('("چندزبانه (کره‌ای/ژاپنی/چینی/انگلیسی)", "multi")' in _manga_app
     and '("چندزبانه (کره‌ای/ژاپنی/چینی/انگلیسی)", "multi")' in _app_server,
     "D: UI (بومی + وب) — مقدارِ چندزبانه = multi (نه «ko ja zh en»)")
gate('"multi": "multi"' in _manga,
     "D: _MOBILE_LANG_MAP — multi → multi")
gate('main_lang = "multi" if _on_android() else "korean"' in _manga,
     "D: main_lang — اندروید = multi، PC = رفتارِ قبل")
gate('if "multi" in langs:' in _manga
     and "return True, True, True, True" in _manga,
     "D: _ocr_lang_flags — multi = همهٔ خطها مجاز")
gate('"ko", "korean", "kor" -> base + VARIANT_KO' in _store_kt
     and '"ja", "japanese", "jpn" -> base + VARIANT_JA' not in _store_kt,
     "D: pathsForLang — ko = پایه+واریانت؛ ja = فقط پایه")
gate('def _ocr_multi(self, buf):' in _manga
     and "_MULTI_CONF_FLOOR = 0.72" in _manga
     and 'self._call_auto(buf, "ko")' in _manga
     and "متنِ کره‌ای شناخته شد" in _manga,
     "D: دوئلِ لازمالآمدِ ko در PaddleAndroidOCR (بدونِ دانلودِ همه)")

# ── E. ژاپنی — واریانتِ حذف؛ v6_medium ──────────────────────────────
gate('"ja" to ("models/rec_ja/inference.onnx" to "models/rec_ja/dict.txt")'
     not in _bridge_kt
     and '"ko" to ("models/rec_ko/inference.onnx" to "models/rec_ko/dict.txt")'
     in _bridge_kt,
     "E: LANG_VARIANTSِ پل — فقط ko (ja → recِ پیشفرضِ v6_medium)")
gate("rec_ja/inference.onnx" not in _build_yml
     and "PP-OCRv5/rec/korean_PP-OCRv5_rec_mobile.onnx" in _build_yml
     and "ppocrv5_korean_dict.txt" in _build_yml,
     "E: build.yml — باندلِ تست هم ko=v5 + بدونِ rec_ja")

# ── F. کامپایل + تستهایِ عملی ────────────────────────────────────────
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
              ".github/workflows/fetch_models.yml"):
        yaml.safe_load(io.open(y, encoding="utf-8"))
    ok("F: YAMLِ هر دو workflow سالم")
except Exception as e:
    fail(f"F: YAML: {e}")

# — تستِ عملیِ مپِ زبان (بدونِ بارگذاریِ کاملِ manga) —————————————
try:
    tree = ast.parse(_manga)
    _map_src, _ml_src = None, None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", None) == "_MOBILE_LANG_MAP"
                for t in node.targets):
            _map_src = ast.unparse(node)
        if isinstance(node, ast.FunctionDef) and node.name == "_mobile_lang":
            _ml_src = ast.unparse(node)
    gate(bool(_map_src) and bool(_ml_src),
         "F: _MOBILE_LANG_MAP + _mobile_lang پیدا شدند")
    ns = {}
    exec(_map_src, ns)  # noqa: S102 — محیطِ کنترلشدهٔ چک
    exec(_ml_src, ns)
    _ml = ns["_mobile_lang"]
    gate(_ml("multi") == "multi" and _ml("ch") == "zh" and _ml("korean") == "ko"
         and _ml("en") == "latin" and _ml("هرچی") == "latin",
         "F: _mobile_lang — multi/ch/korean/en/ناشناخته")
except Exception as e:
    fail(f"F: تستِ _mobile_lang: {e}")

# — پارسِ _meta_score رویِ سطرهایِ نمونه (همان قراردادِ پل) ————————
try:
    tree = ast.parse(_manga)
    _ms_src = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "PaddleAndroidOCR":
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef) and sub.name == "_meta_score":
                    _ms_src = ast.unparse(sub)
    gate(bool(_ms_src), "F: _meta_score پیدا شد")
    ns2 = {"staticmethod": staticmethod}
    exec(_ms_src, ns2)
    ms = ns2["_meta_score"]
    rows = ["META|multi|2",
            "0|0.9100|1,2,3,4,5,6,7,8|안녕|0",
            "0|0.8800|9,1,2,3,4,5,6,7|hello|0",
            "ERR|ModelDownload|xyz",
            "0|0.1000|1,2,3,4,5,6,7,8|خراب|0"]
    texts, conf = ms(rows)
    gate(texts == ["안녕", "hello"] and abs(conf - 0.895) < 1e-6,
         f"F: _meta_score — نوعارهایِ سالم + میانگین ({texts}, {conf:.3f})")
    t2, c2 = ms(["META|multi|0"])
    gate(t2 == [] and c2 == 0.0, "F: _meta_score — خالی = ([], 0.0)")
    t3, c3 = ms(None)
    gate(t3 == [] and c3 == 0.0, "F: _meta_score — None = ([], 0.0)")
except Exception as e:
    fail(f"F: تستِ _meta_score: {e}")

# — فهرستِ FILES: کره‌ایِ v5 هست، ja نیست ————————————————
gate('"korean_PP-OCRv5_rec_mobile.onnx"' in _store_kt
     and "rec_ja" not in _store_kt,
     "F: OcrModelStore — فهرستِ FILES پاک (بدونِ rec_ja)")

print()
if FAILS:
    print(f"✗ {len(FAILS)} گیتِ مردود:")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ همهٔ گیت‌هایِ v1.14.190 سبز است.")
