#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.181 — «فقط ML Kit» نهایی + حذفِ دکمهٔ تستِ سرعت.

دستورِ سازنده: «خب ml kit بزار ولی ناقص استخراج میزنه بقیش حذف کن تو
گوشی استفاده نکنه و اون دکمه تست همه استخراج حذف کن».

۱) speed_lab_env: روشِ برندهٔ تستِ ۱۷۹ = mlkit (۳۴۹ms) در هر دو شاخه
   force میشود (یک خطِ بیقید و شرط)؛ شتاب‌دهندهٔ ذخیرهشده (xnnpack)
   میماند؛ msِ نمایشدادهشده = ۳۴۹ (mlkit).
۲) پاکسازیِ یکبارِ مدلهایِ ONNXِ بازنده (رپید/پدل/فلاتر-پدل) از پوشهٔ
   rapidocr_modelsِ گوشی — گیتِ اندرویدی MANGA_PURGE_ONNX_MODELS +
   مارکرِ یکبارمصرف؛ PC بیت‌به‌بیت دستنخورده (همان dict/helper برایِ
   موتورِ سبکِ PC سرِ جایش).
۳) دکمهٔ «تستِ سرعت» از همهجا حذف: فرمِ گوشی/PC (manga_app.py)،
   bridge.py (تابعِ _speed_test_job + مسیریابی)، MainActivity.kt
   (پاسِ ocr_speedtest + speedTestSent). ماشینِ خاموشِ speed_test_run
   در manga.py میماند (بدونِ هیچ دکمه).
۴) K3LadderOCR: پیشفرضِ ناشناخته/خالی = mlkit؛ پاسِ تمامصفحهٔ جانبی در
   روشِ mlkit هم مستقیم ML Kit (ONNX بیدار/دانلود نمیشود).
۵) موتورِ کهنهٔ انتخابی (rapidocr/onnx/paddle) در bridge → همه به
   ML Kit.
۶) Paddle-Lite برنگشته.
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
                  "com", "amirwolf", "mangatranslator", "MainActivity.kt")


def fail(msg):
    print("[✗]", msg)
    sys.exit(1)


def ok(msg):
    print("[✓]", msg)


src = io.open(MP, encoding="utf-8").read()
asrc = io.open(AP, encoding="utf-8").read()
bsrc = io.open(BRP, encoding="utf-8").read()
ksrc = io.open(KT, encoding="utf-8").read()

# ── ۰) نسخه ──────────────────────────────────────────────────────
_m = re.search(r'^APP_VER = "([\d.]+)"', src, re.M)
_v = io.open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read()
_vn = re.search(r"versionName=([\d.]+)", _v)
_vc = re.search(r"versionCode=(\d+)", _v)
if not _m or not _vn or not _vc:
    fail("V: نسخه پیدا نشد")
if _m.group(1) != _vn.group(1):
    fail("V: APP_VER(%s) != versionName(%s)" % (_m.group(1), _vn.group(1)))
if _m.group(1) != "1.14.181":
    fail("V: این چک مالِ 1.14.181 است (APP_VER=%s)" % _m.group(1))
if _vc.group(1) != "186":
    fail("V: versionCode باید 186 باشد (=%s)" % _vc.group(1))
if 'os.environ.setdefault("MANGA_APP_VER", APP_VER)' not in src:
    fail("V: MANGA_APP_VER ست نمیشود")
ok("V: نسخه %s / versionCode=%s" % (_m.group(1), _vc.group(1)))

tree = ast.parse(src)


def _func(name):
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and n.name == name:
            return n
    return None


_lab = ast.get_source_segment(src, _func("speed_lab_env")) or ""

# ── ۱) forceِ mlkit + پاکسازی در speed_lab_env ───────────────────
if _lab.count('os.environ["MANGA_K3_MODE"] = "mlkit"') != 1:
    fail("L: forceِ mlkit باید دقیقاً یکبار باشد (پیدا: %d)"
         % _lab.count('os.environ["MANGA_K3_MODE"] = "mlkit"'))
if "flutter" in _lab and 'os.environ["MANGA_K3_MODE"] = "flutter"' in _lab:
    fail("L: forceِ flutterِ 180 هنوز هست")
_i_ov = _lab.index('os.environ["MANGA_K3_MODE"] = "mlkit"')
_i_ms = _lab.index('_ms_l = ""')
if not (_i_ov < _i_ms):
    fail("L: forceِ mlkit باید قبل از _ms_l باشد")
if "_purge_loser_onnx_models()" not in _lab:
    fail("L: speed_lab_env پاکسازی را صدا نمیزند")
if "فقط ML Kit" not in _lab or "v1.14.181" not in _lab:
    fail("L: پیامِ «فقط ML Kit / v1.14.181» در speed_lab_env نیست")
ok("L: speed_lab_env = فقط ML Kit (برندهٔ ۱۷۹) + پاکسازی + EPِ ذخیرهشده")

# ── ۲) تابعِ پاکسازی ─────────────────────────────────────────────
_pl = ast.get_source_segment(src, _func("_purge_loser_onnx_models")) or ""
if not _pl:
    fail("P: _purge_loser_onnx_models در manga.py نیست")
if "os.remove" not in _pl:
    fail("P: تابعِ پاکسازی os.remove ندارد")
if '_android_gate("MANGA_PURGE_ONNX_MODELS")' not in _pl:
    fail("P: پاکسازی باید گیتِ اندرویدی داشته باشد (PC دستنخورده)")
if "os.path.isfile(_mk)" not in _pl or '"w", encoding="utf-8"' not in _pl:
    fail("P: پاکسازی باید یکبارمصرف با مارکر باشد")
if "endswith(\".part\")" not in _pl:
    fail("P: فایلهایِ نیمهتمامِ .part هم باید پاک شوند")
if '_PURGE_MARKER = ".onnx_loser_models_purged_181"' not in src:
    fail("P: ثابتِ مارکر در سطحِ ماژول نیست")
if '"PP-OCRv6_det_small.int8.onnx"' not in src:
    fail("P: int8ِ رپید در _K3_PURGE_EXTRA نیست")
ok("P: پاکسازیِ یکبارِ بازندهها — گیتِ MANGA_PURGE_ONNX_MODELS + مارکر")

# ── ۳) خطِ قرمزِ PC — دستنخورده ─────────────────────────────────
for _u in ("PP-OCRv6_det_small.onnx", "PP-OCRv6_rec_small.onnx",
           "PP-OCRv6_medium_det_onnx.onnx", "PP-OCRv6_medium_rec_onnx.onnx",
           "PP-OCRv6_tiny_det.onnx", "PP-OCRv6_tiny_rec.onnx",
           "ppocr_keys_v6_tiny_utf8.txt"):
    if '"%s":' % _u not in src:
        fail("PC: %s از _RAPIDOCR_FILES حذف شده — PC به آن نیاز دارد" % _u)
if src.count("_rapidocr_model_pair(lang, small=True)") < 2:
    fail("PC: RapidOCRBackend (PC) باید مثلِ قبل small=True بگیرد")
if "def _ensure_rapidocr_models(mdir, files=None):" not in src:
    fail("PC: امضای _ensure_rapidocr_models عوض شده")
ok("PC: _RAPIDOCR_FILES/helperها بیت‌به‌بیت — موتورِ PC دستنخورده")

# ── ۴) K3LadderOCR — پیشفرضِ mlkit + مسیرِ تمامصفحه ─────────────
if 'self._mode = _m if _m in self._K3_MODES else "mlkit"' not in src:
    fail("K: فالبکِ ناشناخته باید mlkit باشد")
_k3_src = src[src.index("class K3LadderOCR:"):src.index(
    "\nclass ", src.index("class K3LadderOCR:") + 10)]
_m0 = _k3_src.index("def ocr(self")
_m1 = _k3_src.index("\n    def ", _m0 + 10)
_ocr_src = _k3_src[_m0:_m1]
_i_fp = _ocr_src.index("if not crop_mode:")
_i_mlk = _ocr_src.find('if self._mode == "mlkit":')
_i_ret = _ocr_src.find("return self._mlkit.ocr(image_bgr)", _i_mlk)
_i_med = _ocr_src.index("eng = self._engine(small=False)")
if _i_mlk == -1 or _i_ret == -1 or not (_i_fp < _i_mlk < _i_med):
    fail("K: گاردِ mlkitِ تمامصفحه باید قبل از ساختِ medium باشد")
ok("K: تمامصفحه در روشِ mlkit = ML Kitِ مستقیم؛ ONNX بیدار نمیشود")

# ── ۵) حذفِ دکمهٔ «تستِ سرعت» از همهجا ───────────────────────────
if "ocr_speedtest" in asrc:
    fail("U: ocr_speedtest هنوز در manga_app است")
if "ocr_speedtest_v" in asrc or 'outputs=[ocr_speedtest]' in asrc:
    fail("U: سیمکشیِ تستِ سرعت هنوز در manga_app است")
if '_env.pop("MANGA_SPEED_TEST", None)' not in asrc:
    fail("U: پاکسازیِ envِ کهنهٔ MANGA_SPEED_TEST در manga_app نیست")
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
    fail("U: فرمِ گوشی هنوز کلیدِ ocr_* دارد: %s" % _ocr_flds)
ok("U: پنلِ گوشی/PC بدونِ دکمهٔ «تستِ سرعت» (استخراجِ واقعیِ فرم)")

if "_speed_test_job(" in bsrc or "ocr_speedtest" in bsrc:
    fail("B: bridge هنوز مسیرِ تستِ سرعت دارد")
if 'getattr(_manga(), "speed_lab_env", None)' not in bsrc:
    fail("B: speed_lab_env سرِ جایش نیست")
if 'if _oe and _oe not in ("mlkit", "ml-kit"):' not in bsrc \
        or '                _oe = "mlkit"' not in bsrc:
    fail("B: انتخابِ موتورِ کهنه باید به ML Kit برود")
ok("B: bridge بدونِ دکمهٔ تست + هر موتورِ کهنه → ML Kit")

if "ocr_speedtest" in ksrc or "speedTestSent" in ksrc:
    fail("K: MainActivity هنوز کلیدِ تستِ سرعت دارد")
ok("K: MainActivity بدونِ ocr_speedtest/speedTestSent")

if "def speed_test_run(" not in src \
        or 'os.environ.get("MANGA_SPEED_TEST"' not in src:
    fail("S: ماشینِ خاموشِ تستِ سرعت (بدونِ دکمه) باید در manga.py بماند")
ok("S: speed_test_run خاموش میماند — بدونِ هیچ دکمه/ورودیِ UI")

# ── ۶) Paddle-Lite برنگشته ───────────────────────────────────────
for _bad in ("PliteCropOCR", "_PLOCR_LiteRunner", "MANGA_K3_PLITE",
             "plite_banned"):
    if _bad in src or _bad in bsrc:
        fail("P: %s برگشته!" % _bad)
if "PaddleLiteBridge" in ksrc or "PaddlePredictor" in ksrc:
    fail("P: Paddle-Lite در MainActivity برگشته")
ok("P: Paddle-Lite برنگشته")

# ── ۷) E2E-الف: speed_lab_env با نتیجهٔ واقعیِ تستِ ۱۷۹ ──────────
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
                                        "_MLKIT_STATS", "_SPEED_TEST_FILE",
                                        "_RAPIDOCR_MIRROR", "_RAPIDOCR_MS",
                                        "_RAPIDOCR_FILES",
                                        "_K3_PURGE_EXTRA",
                                        "_PURGE_MARKER"):
        picks[getattr(n.targets[0], "id", "")] = ast.get_source_segment(src, n)
g = {"os": os, "json": json, "print": print, "time": __import__("time"),
     "APP_VER": "1.14.181",
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
assert os.environ.get("MANGA_K3_MODE") == "mlkit", os.environ.get(
    "MANGA_K3_MODE")
assert os.environ.get("MANGA_MOBILE_OCR_EP") == "xnnpack", os.environ.get(
    "MANGA_MOBILE_OCR_EP")
assert "فقط ML Kit" in ret, ret
assert "349ms" in ret, ret
assert "3855ms" not in ret, ret

# برندهٔ کهنهٔ flutter در فایل هم مهم نیست — forceِ mlkit
with open(os.path.join(td, "speed_test.json"), "w", encoding="utf-8") as f:
    json.dump({"ladder": "flutter", "ep": "cpu",
               "ladder_ms": {"flutter": 3855.0}}, f, ensure_ascii=False)
os.environ.pop("MANGA_K3_MODE", None)
ret1b = g["speed_lab_env"]({})
assert os.environ.get("MANGA_K3_MODE") == "mlkit", "برندهٔ کهنهٔ flutter غلبه کرد"
assert os.environ.get("MANGA_MOBILE_OCR_EP") == "cpu"

# شاخهٔ بدونِ نتیجهٔ ذخیرهشده
os.remove(os.path.join(td, "speed_test.json"))
os.environ.pop("MANGA_K3_MODE", None)
os.environ["MANGA_MOBILE_OCR_EP"] = "nnapi"
ret2 = g["speed_lab_env"]({})
assert os.environ.get("MANGA_K3_MODE") == "mlkit", "بدونِ فایل هم mlkit نیست"
assert os.environ.get("MANGA_MOBILE_OCR_EP") is None, "ep باید auto/pop میشد"
assert "فقط ML Kit" in ret2, ret2
print("LAB_OK", json.dumps({"with": ret[:50], "without": ret2[:40]},
                           ensure_ascii=False))
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
    ok("E2E-LAB: فقط ML Kit در هر سه سناریو + EPِ ذخیرهشده + msِ ۳۴۹")

# ── ۸) E2E-ب: پاکسازیِ واقعیِ مدلهایِ بازنده ─────────────────────
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
     "APP_VER": "1.14.181",
     # همان قراردادِ _android_gate: اجبارِ env؛ _on_android رویِ PC False
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
          "PP-OCRv6_rec_small.onnx", "PP-OCRv6_medium_det_onnx.onnx",
          "PP-OCRv6_medium_rec_onnx.onnx", "PP-OCRv6_tiny_det.onnx",
          "PP-OCRv6_tiny_rec.onnx", "ppocr_keys_v6_tiny_utf8.txt",
          "PP-OCRv6_medium_rec_onnx.onnx.part"]
for i, fn in enumerate(LOSERS):
    with open(os.path.join(mdir, fn), "wb") as f:
        f.write(b"x" * (200000 if not fn.endswith(".part") else 10))
KEEP = "keep_me.txt"
with open(os.path.join(mdir, KEEP), "wb") as f:
    f.write(b"x" * 100)

# گیتِ خاموش (PC) → هیچ کاری نمیکند
os.environ.pop("MANGA_PURGE_ONNX_MODELS", None)
os.environ.pop("MANGA_FORCE_ANDROID_GATE", None)
assert purge() == "", "رویِ PC نباید پاکسازی کند"
assert os.path.isfile(os.path.join(mdir, LOSERS[0])), "PC: فایل حذف شد!"

# گیتِ اجباری (اندروید) → پاکسازیِ یکبار
os.environ["MANGA_PURGE_ONNX_MODELS"] = "1"
msg = purge()
assert msg and "فقط ML Kit" in msg, msg
for fn in LOSERS:
    assert not os.path.isfile(os.path.join(mdir, fn)), "باقی مانده: " + fn
assert os.path.isfile(os.path.join(mdir, KEEP)), "فایلِ بیگناه حذف شد!"
assert os.path.isfile(os.path.join(mdir, g["_PURGE_MARKER"])), "مارکر نبود"

# بارِ دوم → یکبارمصرف (no-op)
assert purge() == "", "بارِ دوم باید no-op باشد"
print("PURGE_OK %d فایل" % len(LOSERS))
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
    ok("E2E-PURGE: ۹ فایلِ بازنده/نیمهتمام پاک، بیگناه و مارکر ماندند، "
       "PC و بارِ دوم no-op")

# ── ۹) E2E-پ: نردبانِ mlkit — بدونِ env هم mlkit + بدونِ ONNX ────
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
calls, ml_calls = [], []
K3 = g["K3LadderOCR"]


class FakeML:
    def ocr(self, image):
        ml_calls.append(1)
        box = [[0, 0], [image.shape[1], 0],
               [image.shape[1], image.shape[0]], [0, image.shape[0]]]
        return [[[box, ("MLKIT", 0.5)]]]   # پوشش/اطمینانِ ضعیف


class FakeEng:
    def __init__(self, tag):
        self.tag = tag

    def ocr(self, image, crop_mode=False):
        calls.append(self.tag)
        box = [[0, 0], [image.shape[1], 0],
               [image.shape[1], image.shape[0]], [0, image.shape[0]]]
        return [[[box, (self.tag.upper(), 0.9)]]]


def builder(small=False, tiny=False):
    calls.append("BUILD-" + ("tiny" if tiny else
                             ("small" if small else "med")))
    return FakeEng("tiny" if tiny else ("small" if small else "med"))


lad = K3(FakeML(), "en", builder)
assert lad._mode == "mlkit", lad._mode   # v1.14.181: پیشفرضِ جدید

img = np.full((200, 160, 3), 200, np.uint8)
out = lad.ocr(img, crop_mode=True)
assert out and out[0] and out[0][0][1][0] == "MLKIT", out  # ضعیف هم برمیگردد
assert not calls, "در mlkit نباید ONNX ساخته شود: %s" % calls

out2 = lad.ocr(img, crop_mode=False)   # پاسِ تمامصفحهٔ جانبی
assert out2 and out2[0][0][1][0] == "MLKIT", out2
assert not calls, "تمامصفحه در mlkit نباید ONNX بیدار کند: %s" % calls
assert ml_calls == [1, 1], ml_calls    # دو بار ML Kit، هیچ ONNX
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
        fail("E2E-K3: نردبانِ mlkit شکست خورد")
    ok("E2E-K3: بدونِ env هم فقط ML Kit — کراپ و تمامصفحه، هیچ ONNX")

# ── ۱۰) py_compile نهایی ─────────────────────────────────────────
import py_compile  # noqa: E402

for p in (MP, AP, BRP):
    py_compile.compile(p, doraise=True)
ok("py_compile: manga.py / manga_app.py / bridge.py")

print()
print("[✓] همهٔ گیتهایِ v1.14.181 PASS")
