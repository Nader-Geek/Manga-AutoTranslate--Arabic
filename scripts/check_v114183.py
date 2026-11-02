#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.183 — حذفِ کاملِ ML Kit + فیکسِ بیلدِ پدلِ رسمی.

دستورِ سازنده: «نسخهٔ 1.14.182 اپ نساخت، ارور داد … بعد ml kit حذف کن
خوب نیست … نسخه RapidOCR-lite استفاده نکن همون PP-OCRv6_medium استفاده
کن همون ک paddleocr.ai …/android_deployment.html گفته».

۱) بیلد: خطاهایِ ۴گانهٔ CIِ 1.14.182 (OptimizationLevel/shape) فیکس —
   APIِ رسمیِ ONNX Runtime 1.31 (OptLevel.ALL_OPT + ot.info.shape).
۲) ML Kit کامل حذف: MlKitBridge.kt + وابستگیهایِ com.google.mlkit +
   MlKitCropOCR/_mlkit_backend/_MLKIT_STATS و همهٔ سیمکشیها.
۳) موتورِ یگانهٔ گوشی = پدلِ رسمیِ اندروید (پرتِ ppocr-android با
   PP-OCRv6 mediumِ رسمی) — پلهٔ ۱ی نردبان رویِ کراپِ تقویتشده،
   خالی/خطا = خروجیِ خالی (فالبکی نیست).
۴) K3LadderOCR: روشهایِ full/fast/rapid/paddle/flutter/padandroid —
   بدونِ mlkit؛ پیشفرضِ ناشناخته/کهنه = padandroid.
۵) PC بیت‌به‌بیت دستنخورده (همان helperها برایِ موتورِ خودش).
۶) قراردادهایِ 181/182 (پاکسازیِ بازندهها + بدونِ دکمهٔ تستِ سرعت).
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
KTD = os.path.join(ROOT, "android", "app", "src", "main", "java",
                   "com", "amirwolf", "mangatranslator")
KT = os.path.join(KTD, "PaddleOcrBridge.kt")
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
if _m.group(1) != "1.14.183":
    fail("V: این چک مالِ 1.14.183 است (APP_VER=%s)" % _m.group(1))
if _vc.group(1) != "188":
    fail("V: versionCode باید 188 باشد (=%s)" % _vc.group(1))
ok("V: نسخه %s / versionCode=%s" % (_m.group(1), _vc.group(1)))

tree = ast.parse(src)


def _func(name):
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and n.name == name:
            return n
    return None


# ── ۱) حذفِ کاملِ ML Kit از پایتون ───────────────────────────────
cls = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
if "MlKitCropOCR" in cls or "class MlKitCropOCR" in src:
    fail("X: MlKitCropOCR هنوز در manga.py است")
for _sym in ("_mlkit_backend", "_MLKIT_STATS", "_MLKIT_STATE",
             "_MLKIT_BUILD_LOCK", "_mlkit_stats_note", "self._mlkit",
             '"mlkit": _mlbe', "MANGA_MLKIT"):
    if _sym in src:
        fail("X: بقایایِ mlkit در manga.py: %r" % _sym)
for _code in ('if _mode == "mlkit":', 'if self._mode == "mlkit":',
              'self._mlkit.ocr', '"mlkit", "ml-kit"'):
    if _code in src:
        fail("X: کدِ mlkit در manga.py: %r" % _code)
if "def _mobile_lang(lang):" not in src:
    fail("X: _mobile_lang (جانشینِ نگاشتِ زبان) نیست")
ok("X: MlKitCropOCR/_mlkit_backend/_MLKIT_STATS و همهٔ کدهایِ mlkit حذف")

# ── ۲) حذفِ کاملِ ML Kit از اندروید ──────────────────────────────
if os.path.exists(os.path.join(KTD, "MlKitBridge.kt")):
    fail("A: MlKitBridge.kt هنوز هست")
for _kf in os.listdir(KTD):
    if _kf.endswith(".kt"):
        _t = io.open(os.path.join(KTD, _kf), encoding="utf-8",
                     errors="ignore").read()
        if "com.google.mlkit" in _t:
            fail("A: com.google.mlkit در %s" % _kf)
for _dep in ('implementation("com.google.mlkit', "text-recognition:16.0.1",
             "text-recognition-japanese", "text-recognition-korean",
             "text-recognition-chinese"):
    if _dep in gsrc:
        fail("A: وابستگیِ ML Kit هنوز در gradle است: %r" % _dep)
if "onnxruntime-android" not in gsrc:
    fail("A: onnxruntime-android از gradle حذف شده!")
for _bad in ("MlKitCropOCR", "_mlkit_backend", "ML Kitِ باندلشده"):
    if _bad in bsrc:
        fail("A: بقایایِ mlkit در bridge.py: %r" % _bad)
ok("A: MlKitBridge.kt + وابستگیهایِ com.google.mlkit + بقایایِ bridge حذف")

# ── ۳) فیکسِ بیلدِ PaddleOcrBridge.kt (ریشهٔ ارورِ CIِ 182) ───────
if "OrtSession.SessionOptions.OptimizationLevel" in ksrc:
    fail("KT: OptimizationLevelِ غلط برگشته (باید OptLevel باشد)")
if "OrtSession.SessionOptions.OptLevel.ALL_OPT" not in ksrc:
    fail("KT: OptLevel.ALL_OPT نیست")
if "ot.shape" in ksrc.replace("ot.info.shape", ""):
    fail("KT: ot.shapeِ غلط مانده (باید ot.info.shape باشد)")
if ksrc.count("ot.info.shape") < 2:
    fail("KT: ot.info.shape برایِ det/rec نیست")
for _frag in ("object PaddleOcrBridge", "DET_THRESH = 0.3f",
              "DET_BOX_THRESH = 0.6f", "DET_UNCLIP_RATIO = 1.5f",
              "DET_USE_DILATION = false", "REC_FIXED_H = 48",
              "VERTICAL_CROP_RATIO = 1.5", "ROW_THRESHOLD_Y = 10f",
              "fun recognizeAuto(", "\"META|$lang|", "character_dict",
              "roundHalfToEven", "polygonUnclip", "BoxSorter",
              "convexHull", "homographyInv"):
    if _frag not in ksrc:
        fail("KT: PaddleOcrBridge.kt فاقدِ %s" % _frag)
for _bad in ("PaddleLite", "paddle.lite", "org.opencv", "org.pytorch"):
    if _bad in ksrc:
        fail("KT: %s در پلِ Kotlin است!" % _bad)
ok("KT: APIِ رسمیِ ORT (OptLevel + info.shape) + پرتِ رسمیِ ppocr-android")

# ── ۴) K3LadderOCR — نردبانِ بدونِ ML Kit ────────────────────────
if 'self._mode = _m if _m in self._K3_MODES else "padandroid"' not in src:
    fail("K: فالبکِ ناشناخته/کهنه باید padandroid باشد")
_k3_src = src[src.index("class K3LadderOCR:"):src.index(
    "\nclass ", src.index("class K3LadderOCR:") + 10)]
if '_K3_MODES = ("full", "fast", "rapid", "paddle", "flutter",\n' \
        '                 "padandroid")' not in _k3_src:
    fail("K: _K3_MODESِ 183 نیست")
if "def __init__(self, lang: str, build_onnx, build_pad=None):" \
        not in _k3_src:
    fail("K: سازندهٔ نردبان (بدونِ آرگومانِ mlkit) نیست")
_ocr0 = _k3_src.index("def ocr(self")
_ocr1 = _k3_src.index("\n    def ", _ocr0 + 10)
_ocr_src = _k3_src[_ocr0:_ocr1]
_i_fp = _ocr_src.index("if not crop_mode:")
_i_pa = _ocr_src.index('if self._mode in ("padandroid", "full", "fast"):')
_i_med = _ocr_src.index("eng = self._engine(small=False)")
if not (_i_fp < _i_pa < _i_med):
    fail("K: گاردِ پلهٔ ۱ (پدلِ رسمی) باید قبل از ساختِ medium باشد")
_i_step1 = _ocr_src.index('if _mode in ("padandroid", "full", "fast"):',
                          _ocr_src.index("# ── پلهٔ ۱"))
_i_boost = _ocr_src.index("_k3_boost_crop(image_bgr)", _i_step1)
_i_ret = _ocr_src.find("return [lines1] if lines1 else None", _i_step1)
if _i_ret == -1 or not (_i_step1 < _i_boost < _i_ret):
    fail("K: پلهٔ ۱ِ پدلِ رسمی/بازگشتِ خروجیِ خالی در کراپ نیست")
if "def _engine_pad(" not in src:
    fail("K: _engine_pad نیست")
ok("K: پلهٔ ۱ = پدلِ رسمی رویِ کراپِ تقویتشده؛ خالی = خروجیِ خالی "
   "(فالبکی نیست — ML Kit حذف)")

# ── ۵) speed_lab_env — forceِ padandroid + بدونِ فالبک ───────────
_lab = ast.get_source_segment(src, _func("speed_lab_env")) or ""
if _lab.count('os.environ["MANGA_K3_MODE"] = "padandroid"') != 1:
    fail("L: forceِ padandroid باید دقیقاً یکبار باشد")
if "فالبک = ML Kit" in _lab or "فالبکِ خطا = ML Kit" in _lab:
    fail("L: فالبکِ ML Kit در پیامها مانده")
if "پدلِ رسمیِ اندروید" not in _lab or "v1.14.183" not in _lab:
    fail("L: پیامِ «پدلِ رسمیِ اندروید / v1.14.183» در speed_lab_env نیست")
ok("L: speed_lab_env = پدلِ رسمیِ اندروید (بدونِ فالبک) + پاکسازی + EP")

# ── ۶) _init_mobile_engine — پیشفرضِ رسمی ────────────────────────
rb = None
for _c in ast.walk(tree):
    if isinstance(_c, ast.ClassDef) and _c.name == "RapidOCRBackend":
        rb = _c
        break
rb_src = ast.get_source_segment(src, rb) or ""
ime = re.search(r"def _init_mobile_engine.*?(?=\n    def )", rb_src, re.S)
ime_src = ime.group(0) if ime else ""
for _frag in ('or "padandroid")', "_build_paddle_android(lang)",
              "build_pad=lambda: _pb", "K3LadderOCR(",
              "small=(True if _emu171 else small)"):
    if _frag not in ime_src:
        fail("W: _init_mobile_engine فاقدِ %s" % _frag)
if "mlkit" in ime_src or "_mlbe" in ime_src:
    fail("W: بقایایِ mlkit در _init_mobile_engine")
ok("W: موتورِ رسمیِ اندروید پیشفرضِ سیمکشی؛ فالبکِ نهایی = ONNXِ خالص")

# ── ۷) قراردادهایِ 181/182 — پاکسازی + بدونِ دکمه ────────────────
_pl = ast.get_source_segment(src, _func("_purge_loser_onnx_models")) or ""
if "os.remove" not in _pl or '_android_gate("MANGA_PURGE_ONNX_MODELS")' \
        not in _pl:
    fail("P: تابعِ پاکسازی تغییر کرده")
if '_PURGE_MARKER = ".onnx_loser_models_purged_181"' not in src:
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
ok("181/182: پاکسازیِ بازندهها + حذفِ دکمه سرِ جایش")

# ── ۸) Paddle-Lite برنگشته + گیتِ CIِ چندزبانه ───────────────────
for _bad in ("PliteCropOCR", "_PLOCR_LiteRunner", "MANGA_K3_PLITE"):
    if _bad in src or _bad in bsrc or _bad in ksrc:
        fail("P: %s برگشته!" % _bad)
if not os.path.isfile(os.path.join(ROOT, ".ci_scripts/check_ocr_gate.py")):
    fail("C: .ci_scripts/check_ocr_gate.py نیست")
emu = io.open(os.path.join(ROOT, ".github/workflows/android-emulator.yml"),
              encoding="utf-8").read()
if "check_ocr_gate.py" not in emu or "check_mlkit.py" in emu:
    fail("C: گامِ گیتِ چندزبانه در emulator workflow درست نیست")
ok("P/C: Paddle-Lite برنگشته؛ گیتِ CI = check_ocr_gate (موتور-آگنوستیک)")

# ── ۹) E2E-الف: speed_lab_env در سه سناریو ───────────────────────
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
                                        "_PAD_STATS", "_SPEED_TEST_FILE",
                                        "_RAPIDOCR_MIRROR", "_RAPIDOCR_MS",
                                        "_RAPIDOCR_FILES",
                                        "_K3_PURGE_EXTRA",
                                        "_PURGE_MARKER"):
        picks[getattr(n.targets[0], "id", "")] = ast.get_source_segment(src, n)
g = {"os": os, "json": json, "print": print, "time": __import__("time"),
     "APP_VER": "1.14.183",
     "_android_gate": lambda name: False}   # PC: پاکسازی skip
exec(compile("\n\n".join(picks.values()), "lab", "exec"), g)

td = tempfile.mkdtemp()
os.environ["MANGA_FILES_DIR"] = td
with open(os.path.join(td, "speed_test.json"), "w", encoding="utf-8") as f:
    json.dump({"app": "1.14.179", "ts": "2026-11-02 03:24", "per_mode": 60,
               "crops": 15, "ladder": "mlkit", "ep": "xnnpack",
               "ladder_ms": {"full": 20782.0, "fast": 12298.0,
                             "mlkit": 349.0, "rapid": 12017.0,
                             "paddle": 21030.0, "flutter": 3855.0,
                             "padandroid": 420.0},
               "ep_ms": {"cpu": 15420.0, "xnnpack": 15200.0,
                         "nnapi": 20994.0}, "nnapi_pending": False},
              f, ensure_ascii=False)
ret = g["speed_lab_env"]({})
assert os.environ.get("MANGA_K3_MODE") == "padandroid", os.environ.get(
    "MANGA_K3_MODE")
assert os.environ.get("MANGA_MOBILE_OCR_EP") == "xnnpack", os.environ.get(
    "MANGA_MOBILE_OCR_EP")
assert "پدلِ رسمیِ اندروید" in ret, ret
assert "v1.14.183" in ret, ret
assert "420ms" in ret, ret
assert "ML Kit" not in ret, ret

with open(os.path.join(td, "speed_test.json"), "w", encoding="utf-8") as f:
    json.dump({"ladder": "flutter", "ep": "cpu",
               "ladder_ms": {"flutter": 3855.0}}, f, ensure_ascii=False)
os.environ.pop("MANGA_K3_MODE", None)
ret1b = g["speed_lab_env"]({})
assert os.environ.get("MANGA_K3_MODE") == "padandroid", "برندهٔ کهنه غلبه کرد"
assert os.environ.get("MANGA_MOBILE_OCR_EP") == "cpu"

os.remove(os.path.join(td, "speed_test.json"))
os.environ.pop("MANGA_K3_MODE", None)
os.environ["MANGA_MOBILE_OCR_EP"] = "nnapi"
ret2 = g["speed_lab_env"]({})
assert os.environ.get("MANGA_K3_MODE") == "padandroid", "بدونِ فایل هم نیست"
assert os.environ.get("MANGA_MOBILE_OCR_EP") is None, "ep باید auto/pop میشد"
assert "پدلِ رسمیِ اندروید" in ret2, ret2
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
    ok("E2E-LAB: padandroid در هر سه سناریو + EPِ ذخیرهشده + بدونِ ML Kit")

# ── ۱۰) E2E-ب: نردبان — پلهٔ ۱ِ پدلِ رسمی، بدونِ فالبک ───────────
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

os.environ.pop("MANGA_K3_MODE", None)
calls, pad_calls = [], []
K3 = g["K3LadderOCR"]


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


class FakePadWeak:
    def ocr(self, image):
        box = [[0, 0], [image.shape[1], 0],
               [image.shape[1], image.shape[0]], [0, image.shape[0]]]
        return [[[box, ("PADWEAK", 0.4)]]]


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

# ۲) پدلِ خالی → None (فالبکی نیست — ML Kit حذف شد)
lad2 = K3("en", builder, build_pad=pad_factory("empty"))
out2 = lad2.ocr(img, crop_mode=True)
assert out2 is None, out2
assert not calls, calls

# ۳) پدلِ خطاداده → None بدونِ کرش
lad3 = K3("en", builder, build_pad=pad_factory("fail"))
out3 = lad3.ocr(img, crop_mode=True)
assert out3 is None, out3
assert not calls, calls

# ۴) پاسِ تمامصفحهٔ جانبی در padandroid → مستقیمِ پدلِ رسمی
pad_calls.clear()
out4 = lad.ocr(img, crop_mode=False)
assert out4 and out4[0][0][1][0] == "PPV6", out4
assert pad_calls == [1], pad_calls

# ۵) پدلِ ضعیف (پوششِ کم) هم در padandroid برگردانده میشود
os.environ.pop("MANGA_K3_MODE", None)
pad_calls.clear()
_padw = FakePadWeak()
lad5 = K3("en", builder, build_pad=lambda: _padw)
out5 = lad5.ocr(img, crop_mode=True)
assert out5 and out5[0][0][1][0] == "PADWEAK", out5
assert not calls, calls

# ۶) مقدارِ کهنهٔ mlkit (env) → فالبکِ ناشناخته = padandroid
os.environ["MANGA_K3_MODE"] = "mlkit"
pad_calls.clear()
lad6 = K3("en", builder, build_pad=pad_factory("ok"))
assert lad6._mode == "padandroid", lad6._mode
out6 = lad6.ocr(img, crop_mode=True)
assert out6 and out6[0][0][1][0] == "PPV6", out6
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
        fail("E2E-K3: نردبانِ بدونِ ML Kit شکست خورد")
    ok("E2E-K3: پلهٔ ۱ِ پدلِ رسمی + خالی/خطا = None + ضعیفِ برگشتی + "
       "mlkitِ کهنه → padandroid")

# ── ۱۱) E2E-پ: پاکسازی — پیامِ 183 ───────────────────────────────
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
     "APP_VER": "1.14.183",
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
          "PP-OCRv6_medium_rec_onnx.onnx.part"]
for i, fn in enumerate(LOSERS):
    with open(os.path.join(mdir, fn), "wb") as f:
        f.write(b"x" * (200000 if not fn.endswith(".part") else 10))
KEEP = "PP-OCRv6_medium_det_onnx.onnx"
with open(os.path.join(mdir, KEEP), "wb") as f:
    f.write(b"x" * 200000)

os.environ.pop("MANGA_PURGE_ONNX_MODELS", None)
os.environ.pop("MANGA_FORCE_ANDROID_GATE", None)
assert purge() == "", "رویِ PC نباید پاکسازی کند"
assert os.path.isfile(os.path.join(mdir, LOSERS[0])), "PC: فایل حذف شد!"

os.environ["MANGA_PURGE_ONNX_MODELS"] = "1"
msg = purge()
assert msg and "پدلِ رسمیِ اندروید" in msg, msg
for fn in LOSERS:
    assert not os.path.isfile(os.path.join(mdir, fn)), "باقی مانده: " + fn
assert os.path.isfile(os.path.join(mdir, KEEP)), "mediumِ رسمی حذف شد!"
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

# ── ۱۲) py_compile نهایی ─────────────────────────────────────────
import py_compile  # noqa: E402

for p in (MP, AP, BRP):
    py_compile.compile(p, doraise=True)
ok("py_compile: manga.py / manga_app.py / bridge.py")

print()
print("[✓] همهٔ گیتهایِ v1.14.183 PASS")
