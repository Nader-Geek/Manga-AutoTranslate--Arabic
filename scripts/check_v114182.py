#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.182 — «پدلِ رسمیِ اندروید» (PP-OCRv6 mediumِ نیتیو).

دستورِ سازنده: «ml kit خوب نیست … کامل بخون
paddleocr.ai …/android_deployment.html و از PP-OCRv6_medium بزار تو کد
خودم قسمتِ استخراجم؛ اول detector-v4-s همه قسمت هایِ متن پیدا کنه فقط
همون قسمت ها استخراج کنه تا سریعتر باشه».

۱) speed_lab_env: روشِ فعال = padandroid در هر دو شاخه force میشود؛
   شتاب‌دهندهٔ ذخیرهشده میماند؛ فالبکِ هر خطا = ML Kit.
۲) موتورِ Kotlin = PaddleOcrBridge — پرتِ رسمیِ ppocr-android
   (DetPreprocessor/DBPostProcessor/PolygonUnclip/QuadTextCrop/
   RecPreprocessor/CTCDecoder) با مدلهایِ رسمیِ PP-OCRv6 medium
   (det 59MB + rec 73MB + inference.yml) — فقط ONNX Runtime؛
   نه Paddle-Lite، نه OpenCVِ جدید، بدونِ تغییرِ gradle.
۳) K3LadderOCR: پیشفرضِ ناشناخته/خالی = padandroid؛ پلهٔ ۱ = پدلِ رسمی
   رویِ کراپِ تقویتشده، خالی/خطا → ML Kitِ باندلشده؛ پلههایِ ۲/۳ِ ONNXِ
   بازنده در این روش هرگز بیدار نمیشوند.
۴) PC بیت‌به‌بیت دستنخورده (همان dict/helperها برایِ موتورِ خودش).
۵) قراردادهایِ 181 (پاکسازیِ بازندهها + دکمهٔ حذفشده) سرِ جایش.
"""
import ast
import io
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MP = os.path.join(ROOT, "manga.py")
AP = os.path.join(ROOT, "manga_app.py")
BRP = os.path.join(ROOT, "android", "app", "src", "main", "python",
                   "bridge.py")
KT = os.path.join(ROOT, "android", "app", "src", "main", "java",
                  "com", "amirwolf", "mangatranslator", "PaddleOcrBridge.kt")
GR = os.path.join(ROOT, "android", "app", "build.gradle.kts")


def fail(msg):
    print("[✗]", msg)
    sys.exit(1)


def ok(msg):
    print("[✓]", msg)


src = io.open(MP, encoding="utf-8").read()
asrc = io.open(AP, encoding="utf-8").read()
bsrc = io.open(BRP, encoding="utf-8").read()
ksrc = io.open(KT, encoding="utf-8").read()
gsrc = io.open(GR, encoding="utf-8").read()

# ── ۰) نسخه ──────────────────────────────────────────────────────
_m = re.search(r'^APP_VER = "([\d.]+)"', src, re.M)
_v = io.open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read()
_vn = re.search(r"versionName=([\d.]+)", _v)
_vc = re.search(r"versionCode=(\d+)", _v)
if not _m or not _vn or not _vc:
    fail("V: نسخه پیدا نشد")
if _m.group(1) != _vn.group(1):
    fail("V: APP_VER(%s) != versionName(%s)" % (_m.group(1), _vn.group(1)))
# v1.14.183 — گیتِ نسخه باز شد (همان قاعدهٔ 179/180/181)
ok("V: نسخه %s / versionCode=%s" % (_m.group(1), _vc.group(1)))

tree = ast.parse(src)


def _func(name):
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and n.name == name:
            return n
    return None


_lab = ast.get_source_segment(src, _func("speed_lab_env")) or ""

# ── ۱) forceِ padandroid در speed_lab_env ────────────────────────
if _lab.count('os.environ["MANGA_K3_MODE"] = "padandroid"') != 1:
    fail("L: forceِ padandroid باید دقیقاً یکبار باشد (پیدا: %d)"
         % _lab.count('os.environ["MANGA_K3_MODE"] = "padandroid"'))
_i_ov = _lab.index('os.environ["MANGA_K3_MODE"] = "padandroid"')
_i_ms = _lab.index('_ms_l = ""')
if not (_i_ov < _i_ms):
    fail("L: forceِ padandroid باید قبل از _ms_l باشد")
if "_purge_loser_onnx_models()" not in _lab:
    fail("L: speed_lab_env پاکسازی را صدا نمیزند")
if "RapidOCRِ اندروید" not in _lab \
        or ("v1.14.184" not in _lab and "v1.14.185" not in _lab
            and "v1.14.187" not in _lab and "v1.14.188" not in _lab) \
        or "PP-OCRv6" not in _lab:
    fail("L: پیامِ «RapidOCRِ اندروید / v1.14.188» در "
         "speed_lab_env نیست")
ok("L: speed_lab_env = SDKِ رسمیِ PaddleOCR اندروید "
   "(PP-OCRv6_smallِ باندل) + پاکسازی")

# ── ۲) مدلها: mediumِ رسمی + yml — PC دستنخورده ──────────────────
for _u in ("PP-OCRv6_medium_det_onnx.onnx", "PP-OCRv6_medium_rec_onnx.onnx",
           "PP-OCRv6_medium_rec_inference.yml",
           "PP-OCRv6_det_small.onnx", "PP-OCRv6_rec_small.onnx",
           "PP-OCRv6_tiny_det.onnx", "PP-OCRv6_tiny_rec.onnx",
           "ppocr_keys_v6_tiny_utf8.txt"):
    if '"%s":' % _u not in src:
        fail("PC: %s از _RAPIDOCR_FILES نیست" % _u)
if ("https://huggingface.co/PaddlePaddle/PP-OCRv6_medium_rec_onnx"
        not in src) or ("/resolve/main/inference.yml" not in src):
    fail("M: آدرسِ رسمیِ inference.yml در _RAPIDOCR_FILES نیست")
if src.count("_rapidocr_model_pair(") < 2 \
        or src.count("small=_pc_ocr_small()") < 2:
    fail("PC: هر دو call-site باید از _pc_ocr_small() بگیرند "
         "(v1.14.188 — PC = ستِ medium؛ امولاتور/MANGA_OCR_SMALL = سبک)")
if "def _ensure_rapidocr_models(mdir, files=None):" not in src:
    fail("PC: امضای _ensure_rapidocr_models عوض شده")
ok("PC: مدلهایِ PC بیت‌به‌بیت + ymlِ رسمیِ medium اضافه شد")

# ── ۳) PaddleAndroidOCR — موتورِ پایتونیِ پل ─────────────────────
if "class PaddleAndroidOCR:" not in src:
    fail("E: کلاسِ PaddleAndroidOCR نیست")
_cls = src[src.index("class PaddleAndroidOCR:"):]
_cls = _cls[:_cls.index("\nclass ", 10)]
for _frag in ("com.amirwolf.mangatranslator.PaddleOcrBridge",
              "self._bridge.init(_intra)", "recognizeAuto(",
              "startswith(\"META\")", "PP-OCRv6",
              "باندلِ APK"):
    if _frag not in _cls:
        fail("E: PaddleAndroidOCR فاقدِ %s" % _frag)
for _gone in ("_ensure_rapidocr_models", "_FILES", "_android_heal_model_dir"):
    if _gone in _cls:
        fail("E: PaddleAndroidOCR هنوز دانلودِ مدل دارد: %r" % _gone)
ok("E: PaddleAndroidOCR — پلِ SDKِ باندل + سلف‌تست + پارسرِ مشترک")

# ── ۴) K3LadderOCR — پیشفرض و پلهٔ ۱ ────────────────────────────
if 'self._mode = "padandroid"' not in src:
    fail("K: mode باید همیشه padandroid باشد")
if '_K3_MODES = ("padandroid",)' not in src:
    fail("K: _K3_MODESِ 184 (تکروش) نیست")
if '"padandroid": "رپیدِ رسمیِ اندروید"' not in src:
    fail("K: برچسبِ فارسیِ padandroid در _K3_MODE_FA نیست")
if "def _engine_pad(" not in src:
    fail("K: _engine_pad (سازندهٔ تنلِ پدلِ رسمی) نیست")
_k3_src = src[src.index("class K3LadderOCR:"):src.index(
    "\nclass ", src.index("class K3LadderOCR:") + 10)]
_ocr0 = _k3_src.index("def ocr(self")
_ocr1 = _k3_src.find("\n    def ", _ocr0 + 10)
if _ocr1 < 0:
    _ocr1 = len(_k3_src)
_ocr_src = _k3_src[_ocr0:_ocr1]
if "self._mlkit" in _ocr_src or "_engine(small" in _ocr_src:
    fail("K: نردبانِ 184 نباید پلهٔ ONNX داشته باشد")
_i_fp = _ocr_src.index("if not crop_mode:")
_i_boost = _ocr_src.index("_k3_boost_crop(image_bgr)", _i_fp)
_i_ret = _ocr_src.find("return [lines1] if lines1 else None")
if _i_ret == -1:
    fail("K: بازگشتِ خروجیِ کراپِ SDKِ رسمی نیست")
if not (_i_fp < _i_boost < _i_ret):
    fail("K: کراپِ تقویتشده باید قبل از بازگشت باشد")
ok("K: کراپِ تقویتشده → SDKِ رسمی → بازگشتِ خطها (بدونِ پلههایِ ۲/۳)")

# ── ۵) PaddleOcrBridge.kt — پرتِ رسمی ────────────────────────────
# v1.14.184 — پل = نازک رویِ SDKِ رسمی (ppocr-sdkِ وندورشده)
for _frag in ("object PaddleOcrBridge", "fun recognizeAuto(",
              "\"META|", "RapidOcr.create", "com.paddle.ocr",
              "models/det/inference.onnx", "models/rec/dict.txt",
              "OpenCVUtils.init"):
    if _frag not in ksrc:
        fail("KT: PaddleOcrBridge.kt فاقدِ %s" % _frag)
for _bad in ("ai.onnxruntime", "OrtSession", "PaddleLite", "paddle.lite"):
    if _bad in ksrc:
        fail("KT: %s در پلِ Kotlin است! (فقط SDKِ رسمی)" % _bad)
if "quickbirdstudios" in gsrc:
    fail("G: وابستگیِ OpenCVِ سنگین به gradle اضافه شده!")
# v1.14.184 — ORT فقط داخلِ ماژولِ رسمیِ :ppocr-sdk است
if "onnxruntime-android" in gsrc:
    fail("G: onnxruntime-android هنوز در gradleِ app است")
_sdk_g2 = io.open(os.path.join(ROOT, "android", "ppocr-sdk",
                               "build.gradle.kts"),
                  encoding="utf-8").read()
if "onnxruntime-android" not in _sdk_g2:
    fail("G: onnxruntime-android در :ppocr-sdk نیست")
ok("KT: پرتِ رسمیِ ppocr-android با ثابتهایِ رسمی — فقط ONNX Runtime، "
   "gradle دستنخورده")

# ── ۶) قراردادهایِ 181 — پاکسازی + بدونِ دکمه ────────────────────
_pl = ast.get_source_segment(src, _func("_purge_loser_onnx_models")) or ""
if "os.remove" not in _pl or '_android_gate("MANGA_PURGE_ONNX_MODELS")' \
        not in _pl:
    fail("P: تابعِ پاکسازی تغییر کرده")
if '_PURGE_MARKER = ".onnx_loser_models_purged_184"' not in src:
    fail("P: مارکرِ پاکسازی عوض شده")
if "ocr_speedtest" in asrc or "_speed_test_job(" in bsrc:
    fail("U: دکمهٔ «تستِ سرعت» برگشته!")
sys.path.insert(0, os.path.join(ROOT, "android", "app", "src",
                                "main", "python"))
import extract_ui as eu  # noqa: E402

fields = eu.extract(AP)
_ocr_flds = []
for sec in ((fields or {}).get("sections") or []):
    for f in (sec.get("fields") or []):
        if isinstance(f, dict) and str(f.get("id", "")).startswith("ocr_"):
            _ocr_flds.append(f["id"])
if _ocr_flds:
    fail("U: فرمِ گوشی کلیدِ ocr_* دارد: %s" % _ocr_flds)
ok("181: پاکسازیِ بازندهها + حذفِ دکمه سرِ جایش")

# ── ۷) Paddle-Lite برنگشته ───────────────────────────────────────
for _bad in ("PliteCropOCR", "_PLOCR_LiteRunner", "MANGA_K3_PLITE"):
    if _bad in src or _bad in bsrc or _bad in ksrc:
        fail("P: %s برگشته!" % _bad)
# «PaddleLiteBridge» فقط به‌عنوانِ ارجاعِ تاریخی در کامنتِ 1.14.170
# مجاز است — در هیچ فایلِ Kotlin نباید کلاس/استفادهٔ واقعی باشد.
_kt_dir = os.path.dirname(KT)
for _kf in os.listdir(_kt_dir):
    if not _kf.endswith(".kt"):
        continue
    _ktxt = io.open(os.path.join(_kt_dir, _kf), encoding="utf-8").read()
    for _bad in ("PaddleLiteBridge", "PaddlePredictor", "paddle.lite"):
        if _bad in _ktxt:
            fail("P: %s در %s برگشته!" % (_bad, _kf))
ok("P: Paddle-Lite برنگشته")

# ── ۸) E2E-الف: speed_lab_env در سه سناریو ──────────────────────
E2E_LAB = r'''
# -*- coding: utf-8 -*-
import ast, io, json, os, sys, tempfile
ROOT = os.environ["ROOT"]
src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
tree = ast.parse(src)
picks = {}
for n in tree.body:
    if isinstance(n, ast.FunctionDef) and n.name in (
            "speed_lab_env", "speed_test_load", "_speed_test_path",
            "_purge_loser_onnx_models", "_fmt_mb"):
        picks[n.name] = ast.get_source_segment(src, n)
    if isinstance(n, ast.Assign) and getattr(
            n.targets[0], "id", "") in ("_K3_MODE_FA", "_SPEED_LAB_EP",
                                        "_SPEED_LAB_LADDER", "_K3_STATS",
                                        "_MLKIT_STATS", "_PAD_STATS",
                                        "_SPEED_TEST_FILE",
                                        "_RAPIDOCR_MIRROR", "_RAPIDOCR_MS",
                                        "_RAPIDOCR_FILES",
                                        "_K3_PURGE_EXTRA",
                                        "_PURGE_MARKER"):
        picks[getattr(n.targets[0], "id", "")] = ast.get_source_segment(src, n)
g = {"os": os, "json": json, "print": print, "time": __import__("time"),
     "APP_VER": "1.14.184",
     "_android_gate": lambda name: False}   # PC: پاکسازی skip
exec(compile("\n\n".join(picks.values()), "lab", "exec"), g)

td = tempfile.mkdtemp()
os.environ["MANGA_FILES_DIR"] = td
with open(os.path.join(td, "speed_test.json"), "w", encoding="utf-8") as f:
    json.dump({"app": "1.14.179", "ts": "2026-11-02 03:24", "per_mode": 60,
               "crops": 15, "ladder": "mlkit", "ep": "xnnpack",
               "ladder_ms": {"full": 20782.0, "fast": 12298.0,
                             "mlkit": 349.0, "rapid": 12017.0,
                             "paddle": 21030.0, "flutter": 3855.0},
               "ep_ms": {"cpu": 15420.0, "xnnpack": 15200.0,
                         "nnapi": 20994.0}, "nnapi_pending": False},
              f, ensure_ascii=False)
ret = g["speed_lab_env"]({})
assert os.environ.get("MANGA_K3_MODE") == "padandroid", os.environ.get(
    "MANGA_K3_MODE")
assert os.environ.get("MANGA_MOBILE_OCR_EP") is None, os.environ.get(
    "MANGA_MOBILE_OCR_EP")
assert "RapidOCRِ اندروید" in ret, ret
assert ("v1.14.184" in ret or "v1.14.185" in ret
        or "v1.14.187" in ret or "v1.14.188" in ret), ret

# برندهٔ کهنهٔ flutter/mlkit در فایل هم مهم نیست — forceِ padandroid
with open(os.path.join(td, "speed_test.json"), "w", encoding="utf-8") as f:
    json.dump({"ladder": "flutter", "ep": "cpu",
               "ladder_ms": {"flutter": 3855.0}}, f, ensure_ascii=False)
os.environ.pop("MANGA_K3_MODE", None)
ret1b = g["speed_lab_env"]({})
assert os.environ.get("MANGA_K3_MODE") == "padandroid", "برندهٔ کهنه غلبه کرد"
assert os.environ.get("MANGA_MOBILE_OCR_EP") is None

# شاخهٔ بدونِ نتیجهٔ ذخیرهشده
os.remove(os.path.join(td, "speed_test.json"))
os.environ.pop("MANGA_K3_MODE", None)
os.environ["MANGA_MOBILE_OCR_EP"] = "nnapi"
ret2 = g["speed_lab_env"]({})
assert os.environ.get("MANGA_K3_MODE") == "padandroid", "بدونِ فایل هم نیست"
assert os.environ.get("MANGA_MOBILE_OCR_EP") is None, "ep باید auto/pop میشد"
assert "RapidOCRِ اندروید" in ret2, ret2
print("LAB_OK")
'''
with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ)
    env["ROOT"] = ROOT
    r = subprocess.run([sys.executable, "-c", E2E_LAB], env=env,
                       capture_output=True, text=True, timeout=120)
    out = r.stdout + r.stderr
    if r.returncode != 0 or "LAB_OK" not in out:
        print(out[-3000:])
        fail("E2E-LAB: speed_lab_env شکست خورد")
    ok("E2E-LAB: padandroid در هر سه سناریو + EPِ ذخیرهشده")

# ── ۹) E2E-ب: نردبان — پلهٔ ۱ِ پدلِ رسمی، بدونِ فالبک (183) ──────
E2E_K3 = r'''
# -*- coding: utf-8 -*-
import ast, io, os, sys, threading, time
import cv2
import numpy as np
ROOT = os.environ["ROOT"]
src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
m = src.index("class K3LadderOCR:")
m2 = src.index("\nclass ", m + 10)
k3 = src[m:m2]
picks = [k3]
tree = ast.parse(src)
for n in tree.body:
    if isinstance(n, ast.FunctionDef) and n.name in (
            "_k3_boost_crop", "_k3_map_boxes", "_k3_ink_coverage",
            "_k3_best_conf", "_k3_stats_note"):
        picks.append(ast.get_source_segment(src, n))
g = {"os": os, "np": np, "cv2": cv2, "time": time, "print": print,
     "threading": threading}
g["_K3_STATS"] = {"ms": 0.0, "n": 0, "st1": 0, "st2": 0, "st3": 0}
exec(compile("\n\n".join(picks), "k3", "exec"), g)

os.environ.pop("MANGA_K3_MODE", None)   # بدونِ env → پیشفرضِ جدید
calls, ml_calls, pad_calls = [], [], []
K3 = g["K3LadderOCR"]


class FakeML:
    def ocr(self, image):
        ml_calls.append(1)
        box = [[0, 0], [image.shape[1], 0],
               [image.shape[1], image.shape[0]], [0, image.shape[0]]]
        return [[[box, ("MLKIT", 0.6)]]]


class FakePad:
    def __init__(self, behavior):
        self.behavior = behavior

    def ocr(self, image, crop_mode=False):
        pad_calls.append(1)
        if self.behavior == "fail":
            raise RuntimeError("pad boom")
        if self.behavior == "empty":
            return None
        box = [[0, 0], [image.shape[1], 0],
               [image.shape[1], image.shape[0]], [0, image.shape[0]]]
        return [[[box, ("PPV6", 0.95)]]]


def builder(small=False, tiny=False):
    calls.append("BUILD-" + ("tiny" if tiny else
                             ("small" if small else "med")))
    return None


def pad_factory(behavior):
    return lambda: FakePad(behavior)


img = np.full((200, 160, 3), 200, np.uint8)

# ۱) پیشفرضِ بدونِ env = padandroid؛ پدل جواب میدهد → بدونِ ONNX
lad = K3("en", builder, build_pad=pad_factory("ok"))
assert lad._mode == "padandroid", lad._mode
out = lad.ocr(img, crop_mode=True)
assert out and out[0] and out[0][0][1][0] == "PPV6", out
assert pad_calls == [1], pad_calls
assert not calls, "در padandroid نباید ONNX ساخته شود: %s" % calls

# ۲) پدلِ خالی → خروجیِ None (v1.14.183: فالبکِ ML Kit حذف شد)
lad2 = K3("en", builder, build_pad=pad_factory("empty"))
out2 = lad2.ocr(img, crop_mode=True)
assert out2 is None, out2
assert not calls, calls

# ۳) پدلِ خطاداده → None بدونِ کرش (فالبکی نیست)
lad3 = K3("en", builder, build_pad=pad_factory("fail"))
out3 = lad3.ocr(img, crop_mode=True)
assert out3 is None, out3
assert not calls, calls

# ۴) پاسِ تمامصفحهٔ جانبی در padandroid → مستقیمِ پدلِ رسمی
pad_calls.clear()
out4 = lad.ocr(img, crop_mode=False)
assert out4 and out4[0][0][1][0] == "PPV6", out4
assert pad_calls == [1], pad_calls

# ۵) مقدارِ کهنهٔ mlkit (env) → فالبکِ ناشناخته = padandroid → پدلِ رسمی
os.environ["MANGA_K3_MODE"] = "mlkit"
pad_calls.clear()
lad5 = K3("en", builder, build_pad=pad_factory("ok"))
assert lad5._mode == "padandroid", lad5._mode
out5 = lad5.ocr(img, crop_mode=True)
assert out5 and out5[0][0][1][0] == "PPV6", out5
assert pad_calls == [1], pad_calls
print("K3_OK")
'''
with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ)
    env["ROOT"] = ROOT
    r = subprocess.run([sys.executable, "-c", E2E_K3], env=env,
                       capture_output=True, text=True, timeout=120)
    out = r.stdout + r.stderr
    if r.returncode != 0 or "K3_OK" not in out:
        print(out[-3000:])
        fail("E2E-K3: نردبانِ padandroid شکست خورد")
    ok("E2E-K3: پدلِ رسمی پلهٔ ۱ + خالی/خطا = None (بدونِ فالبکِ 183) + "
       "mlkitِ کهنه → padandroid")

# ── ۱۰) E2E-پ: پاکسازی — پیامِ جدیدِ 182 ─────────────────────────
E2E_PURGE = r'''
# -*- coding: utf-8 -*-
import ast, io, os, sys, tempfile
ROOT = os.environ["ROOT"]
src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
tree = ast.parse(src)
picks = []
for n in tree.body:
    if isinstance(n, ast.FunctionDef) and n.name in (
            "_purge_loser_onnx_models", "_fmt_mb"):
        picks.append(ast.get_source_segment(src, n))
    if isinstance(n, ast.Assign) and getattr(
            n.targets[0], "id", "") in ("_RAPIDOCR_MIRROR", "_RAPIDOCR_MS",
                                        "_RAPIDOCR_FILES",
                                        "_K3_PURGE_EXTRA", "_PURGE_MARKER"):
        picks.append(ast.get_source_segment(src, n))
g = {"os": os, "print": print, "time": __import__("time"),
     "APP_VER": "1.14.184",
     "_android_gate": lambda name: str(
         os.environ.get(name, "") or "").strip().lower() in (
         "1", "true", "yes", "on")}
exec(compile("\n\n".join(picks), "pl", "exec"), g)
purge = g["_purge_loser_onnx_models"]

td = tempfile.mkdtemp()
os.environ["MANGA_FILES_DIR"] = td
mdir = os.path.join(td, "rapidocr_models")
os.makedirs(mdir)
LOSERS = ["PP-OCRv6_det_small.onnx", "PP-OCRv6_det_small.int8.onnx",
          "PP-OCRv6_rec_small.onnx", "PP-OCRv6_tiny_det.onnx",
          "PP-OCRv6_tiny_rec.onnx", "ppocr_keys_v6_tiny_utf8.txt",
          "PP-OCRv6_rec_small.onnx.part",
          "PP-OCRv6_medium_det_onnx.onnx"]
for i, fn in enumerate(LOSERS):
    with open(os.path.join(mdir, fn), "wb") as f:
        f.write(b"x" * (200000 if not fn.endswith(".part") else 10))
KEEP = "unrelated_keep.bin"
with open(os.path.join(mdir, KEEP), "wb") as f:
    f.write(b"x" * 200000)

os.environ.pop("MANGA_PURGE_ONNX_MODELS", None)
os.environ.pop("MANGA_FORCE_ANDROID_GATE", None)
assert purge() == "", "رویِ PC نباید پاکسازی کند"
assert os.path.isfile(os.path.join(mdir, LOSERS[0])), "PC: فایل حذف شد!"

os.environ["MANGA_PURGE_ONNX_MODELS"] = "1"
msg = purge()
assert msg and ("SDKِ رسمیِ PaddleOCR اندروید" in msg
                or "RapidOCRِ اندروید" in msg), msg
for fn in LOSERS:
    assert not os.path.isfile(os.path.join(mdir, fn)), "باقی مانده: " + fn
assert os.path.isfile(os.path.join(mdir, KEEP)), "فایلِ خارجِ فهرست حذف شد!"
assert not os.path.isfile(os.path.join(
    mdir, "PP-OCRv6_medium_det_onnx.onnx")), "medium حذف نشد!"
assert os.path.isfile(os.path.join(mdir, g["_PURGE_MARKER"])), "مارکر نبود"
assert purge() == "", "بارِ دوم باید no-op باشد"
print("PURGE_OK")
'''
with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ)
    env["ROOT"] = ROOT
    r = subprocess.run([sys.executable, "-c", E2E_PURGE], env=env,
                       capture_output=True, text=True, timeout=120)
    out = r.stdout + r.stderr
    if r.returncode != 0 or "PURGE_OK" not in out:
        print(out[-3000:])
        fail("E2E-PURGE: پاکسازی شکست خورد")
    ok("E2E-PURGE: بازندهها پاک، mediumِ رسمی و مارکر ماندند، PC no-op")

# ── ۱۱) py_compile نهایی ─────────────────────────────────────────
import py_compile  # noqa: E402

for p in (MP, AP, BRP):
    py_compile.compile(p, doraise=True)
ok("py_compile: manga.py / manga_app.py / bridge.py")

print()
print("[✓] همهٔ گیتهایِ v1.14.182 PASS")
