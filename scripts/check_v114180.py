#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.180 — تستِ کیفیتِ «فلاتر-پدل» قبل از حذفِ بازندهها.

دستورِ سازنده: «یک چیزی قبل حذف کنی تست میخوام کنم بجز نسخهٔ ml kit
کدومش سریعتر بود؟ اونو فعال کن ببینم متن هارو درست در میاره».

۱) حذفِ بازندهها انجام نشده — فعلاً هیچ مدلی پاک نمیشود (os.remove در
   speed_lab_env/speed_test_run ممنوع).
۲) speed_lab_env در «هر دو» شاخه روشِ «فلاتر-پدل» (نایبقهرمانِ تستِ
   ۱۷۹ = ۳۸۵۵ms بعد از ML Kitِ ۳۴۹ms) را force میکند؛ شتاب‌دهندهٔ
   ذخیرهشده (xnnpack) میماند. msِ نمایشدادهشده باید مالِ flutter باشد
   (اُوردِرایْد قبل از محاسبهٔ _ms_l).
۳) K3LadderOCR در روشِ flutter: پاسِ تمامصفحهٔ جانبی هم با tiny میرود
   (mediumِ ~۱۳۰MB بیدار نمیشود) و در کراپ، ML Kit صدا زده نمیشود.
۴) Paddle-Lite برنگشته (هیچ PaddleLiteBridge/PliteCropOCR/…).
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
VER = os.path.join(ROOT, "VERSION")


def fail(msg):
    print("[✗]", msg)
    sys.exit(1)


def ok(msg):
    print("[✓]", msg)


src = io.open(MP, encoding="utf-8").read()

# ── ۰) نسخه ──────────────────────────────────────────────────────
_m = re.search(r'^APP_VER = "([\d.]+)"', src, re.M)
_v = io.open(VER, encoding="utf-8").read()
_vn = re.search(r"versionName=([\d.]+)", _v)
_vc = re.search(r"versionCode=(\d+)", _v)
if not _m or not _vn or not _vc:
    fail("V: نسخه پیدا نشد")
if _m.group(1) != _vn.group(1):
    fail("V: APP_VER(%s) != versionName(%s)" % (_m.group(1), _vn.group(1)))
if _m.group(1) != "1.14.182":
    fail("V: این چک مالِ قراردادِ 1.14.182 است (APP_VER=%s)" % _m.group(1))
if _vc.group(1) != "187":
    fail("V: versionCode باید 187 باشد (=%s)" % _vc.group(1))
ok("V: نسخه %s / versionCode=%s" % (_m.group(1), _vc.group(1)))

tree = ast.parse(src)


def _func(name):
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and n.name == name:
            return n
    return None


_lab = ast.get_source_segment(src, _func("speed_lab_env")) or ""

# ── ۱) forceِ «پدلِ رسمیِ اندروید» (قراردادِ 182) + پاکسازیِ بازندهها ──
if _lab.count('os.environ["MANGA_K3_MODE"] = "padandroid"') != 1:
    fail("L: forceِ padandroid باید دقیقاً یکبار (بیقید و شرط) باشد "
         "(پیدا شده: %d)" % _lab.count(
             'os.environ["MANGA_K3_MODE"] = "padandroid"'))
if 'os.environ["MANGA_K3_MODE"] = "flutter"' in _lab:
    fail("L: forceِ flutterِ 180 هنوز در speed_lab_env است")
if 'os.environ["MANGA_K3_MODE"] = "mlkit"' in _lab:
    fail("L: forceِ mlkitِ 181 هنوز در speed_lab_env است")
_i_ov = _lab.index('os.environ["MANGA_K3_MODE"] = "padandroid"')
_i_ms = _lab.index('_ms_l = ""')
if not (_i_ov < _i_ms):
    fail("L: forceِ padandroid باید قبل از محاسبهٔ _ms_l باشد "
         "(msِ ثبتشده باید نمایش داده شود)")
if "_purge_loser_onnx_models()" not in _lab:
    fail("L: speed_lab_env باید _purge_loser_onnx_models را صدا بزند")
if "پدلِ رسمیِ اندروید" not in _lab or "v1.14.182" not in _lab:
    fail("L: پیامِ لاگِ «پدلِ رسمیِ اندروید / v1.14.182» در speed_lab_env نیست")
ok("L: speed_lab_env = پدلِ رسمیِ اندروید در هر دو شاخه + پاکسازیِ بازندهها")


# ── ۲) فعلاً هیچ حذفی نباید باشد ─────────────────────────────────
for _seg_name, _seg in (("speed_lab_env", _lab),
                        ("speed_test_run",
                         ast.get_source_segment(src, _func("speed_test_run"))
                         or "")):
    for _bad in ("os.remove", "os.unlink", "shutil.rmtree"):
        if _bad in _seg:
            fail("D: %s در %s است — دستور: حذفِ بازندهها بعدِ تأییدِ کیفیت"
                 % (_bad, _seg_name))
# مدلهایِ tiny هنوز در _RAPIDOCR_FILES و ensure هستند
for _u in ("PP-OCRv6_tiny_det.onnx", "PP-OCRv6_tiny_rec.onnx",
           "ppocr_keys_v6_tiny_utf8.txt"):
    if '"%s":' % _u not in src:
        fail("D: %s از _RAPIDOCR_FILES حذف شده — نباید حذف میشد" % _u)
ok("D: _RAPIDOCR_FILES/PC دستنخورده — tinyها هنوز در dict هستند")

# ── ۲ب) v1.14.181 — پاکسازیِ یکبارِ مدلهایِ بازنده از گوشی ──
_pl = ast.get_source_segment(src, _func("_purge_loser_onnx_models")) or ""
if not _pl:
    fail("P: تابعِ _purge_loser_onnx_models در manga.py نیست")
if "os.remove" not in _pl:
    fail("P: تابعِ پاکسازی os.remove ندارد")
if '_android_gate("MANGA_PURGE_ONNX_MODELS")' not in _pl:
    fail("P: پاکسازی باید با گیتِ اندروید باشد (PC دستنخورده)")
if "_PURGE_MARKER" not in _pl or 'os.path.isfile(_mk)' not in _pl:
    fail("P: پاکسازی باید یکبارمصرف با مارکر باشد")
if '"w", encoding="utf-8"' not in _pl:
    fail("P: نوشتنِ فایلِ مارکر در تابعِ پاکسازی نیست")
if '_PURGE_MARKER = ".onnx_loser_models_purged_181"' not in src:
    fail("P: ثابتِ مارکرِ پاکسازی در سطحِ ماژول نیست")
if '"PP-OCRv6_det_small.int8.onnx"' not in src:
    fail("P: نوعِ int8ِ detِ رپید در لیستِ پاکسازی نیست")
# PC بیت‌به‌بیت: helperِ سبک هنوز دو بار در RapidOCRBackend صدا زده میشود
if src.count("_rapidocr_model_pair(lang, small=True)") < 2:
    fail("P: PC RapidOCRBackend باید مثلِ قبل small=True بگیرد")
ok("P: پاکسازیِ یکبارِ بازندهها (گیتِ اندروید + مارکر) — PC دستنخورده")

# ── ۳) گاردِ تمامصفحهٔ tiny در K3LadderOCR ───────────────────────
_k3_src = src[src.index("class K3LadderOCR:"):src.index(
    "\nclass ", src.index("class K3LadderOCR:") + 10)]
_m0 = _k3_src.index("def ocr(self")
_m1 = _k3_src.index("\n    def ", _m0 + 10)
_ocr_src = _k3_src[_m0:_m1]
if 'if self._mode == "flutter":' not in _ocr_src:
    fail("K: گاردِ flutter در مسیرِ تمامصفحهٔ K3LadderOCR.ocr نیست")
_i_fp = _ocr_src.index("if not crop_mode:")
_i_guard = _ocr_src.index('if self._mode == "flutter":')
_i_med = _ocr_src.index("eng = self._engine(small=False)")
if not (_i_fp < _i_guard < _i_med):
    fail("K: گاردِ flutter باید قبل از ساختِ medium در مسیرِ تمامصفحه باشد")
if "eng = self._engine_tiny()" not in _ocr_src:
    fail("K: مسیرِ flutter موتورِ tiny نمیگیرد")
_i_mlk = _ocr_src.find('if self._mode == "mlkit":')
if _i_mlk == -1:
    fail("K: گاردِ mlkit در مسیرِ تمامصفحهٔ K3LadderOCR.ocr نیست")
_i_ret = _ocr_src.find("return self._mlkit.ocr(image_bgr)", _i_mlk)
if _i_ret == -1:
    fail("K: مسیرِ mlkitِ تمامصفحه باید مستقیم به ML Kit برود")
if not (_i_fp < _i_mlk < _ocr_src.index("eng = self._engine(small=False)")):
    fail("K: گاردِ mlkit باید قبل از ساختِ medium در مسیرِ تمامصفحه باشد")
ok("K: پاسِ تمامصفحهٔ جانبی در روشِ mlkit هم ML Kit است — ONNX بیدار نمیشود")

# ── ۴) Paddle-Lite برنگشته ───────────────────────────────────────
for _bad in ("PliteCropOCR", "_PLOCR_LiteRunner", "PliteProbeService.kt\"",
             "MANGA_K3_PLITE", "plite_banned"):
    if _bad in src:
        fail("P: %s برگشته!" % _bad)
_kt = os.path.join(ROOT, "android", "app", "src", "main", "java",
                   "com", "amirwolf", "mangatranslator", "MainActivity.kt")
if "PaddleLite" in io.open(_kt, encoding="utf-8").read():
    fail("P: Paddle-Lite در MainActivity برگشته")
_grad = io.open(os.path.join(ROOT, "android", "app", "build.gradle.kts"),
                encoding="utf-8").read()
if "PaddlePredictor" in _grad:
    fail("P: وابستگیِ PaddlePredictor برگشته")
ok("P: Paddle-Lite برنگشته")

# ── ۵) E2E-الف: speed_lab_env با نتیجهٔ واقعیِ تستِ ۱۷۹ ──────────
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
            "_purge_loser_onnx_models", "_fmt_mb"):  # v1.14.181
        picks[n.name] = ast.get_source_segment(src, n)
    if isinstance(n, ast.Assign) and getattr(
            n.targets[0], "id", "") in ("_K3_MODE_FA", "_SPEED_LAB_EP",
                                        "_SPEED_LAB_LADDER", "_K3_STATS",
                                        "_MLKIT_STATS", "_PAD_STATS",
                                        "_SPEED_TEST_FILE",
                                        "_RAPIDOCR_MIRROR",
                                        "_RAPIDOCR_MS",
                                        "_RAPIDOCR_FILES",
                                        "_K3_PURGE_EXTRA",
                                        "_PURGE_MARKER"):  # v1.14.182
        picks[getattr(n.targets[0], "id", "")] = ast.get_source_segment(src, n)
g = {"os": os, "json": json, "print": print, "time": __import__("time"),
     # v1.14.181 — گیتِ False = پاکسازی رویِ PC skip میشود
     "_android_gate": lambda name: False,
     "APP_VER": "1.14.181"}
exec(compile("\n\n".join(picks.values()), "lab", "exec"), g)

td = tempfile.mkdtemp()
os.environ["MANGA_FILES_DIR"] = td
# نتیجهٔ تستِ گوشی (۱۷۹) + padandroidِ 182 (در ماشینِ تست = فالبکِ ML Kit)
with open(os.path.join(td, "speed_test.json"), "w", encoding="utf-8") as f:
    json.dump({"app": "1.14.179", "ts": "2026-11-02 03:24", "per_mode": 60,
               "crops": 15, "ladder": "mlkit", "ep": "xnnpack",
               "ladder_ms": {"full": 20782.0, "fast": 12298.0,
                             "mlkit": 349.0, "rapid": 12017.0,
                             "paddle": 21030.0, "flutter": 3855.0,
                             "padandroid": 349.0},
               "ep_ms": {"cpu": 15420.0, "xnnpack": 15200.0,
                         "nnapi": 20994.0}, "nnapi_pending": False},
              f, ensure_ascii=False)
ret = g["speed_lab_env"]({})
assert os.environ.get("MANGA_K3_MODE") == "padandroid", os.environ.get(
    "MANGA_K3_MODE")
assert os.environ.get("MANGA_MOBILE_OCR_EP") == "xnnpack", os.environ.get(
    "MANGA_MOBILE_OCR_EP")
assert "پدلِ رسمیِ اندروید" in ret, ret
assert "349ms" in ret, ret   # msِ mlkitِ برنده
assert "3855ms" not in ret, ret  # msِ flutterِ بازنده

# شاخهٔ بدونِ نتیجهٔ ذخیرهشده
os.remove(os.path.join(td, "speed_test.json"))
os.environ.pop("MANGA_K3_MODE", None)
os.environ["MANGA_MOBILE_OCR_EP"] = "nnapi"
ret2 = g["speed_lab_env"]({})
assert os.environ.get("MANGA_K3_MODE") == "padandroid", "بدونِ فایل هم padandroid نیست"
assert os.environ.get("MANGA_MOBILE_OCR_EP") is None, "ep باید auto/pop میشد"
assert "پدلِ رسمیِ اندروید" in ret2, ret2
print("LAB_OK", json.dumps({"with": ret[:60], "without": ret2[:40]},
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
    ok("E2E-LAB: نتیجهٔ ذخیرهشده (xnnpack) ← پدلِ رسمیِ اندروید + msِ ۳۴۹ "
       "| بدونِ نتیجه هم پدلِ رسمی")

# ── ۶) E2E-ب: نردبانِ flutter — کراپ و تمامصفحه هر دو tiny ───────
E2E_K3 = r'''
# -*- coding: utf-8 -*-
import ast, io, os, sys, threading, time
import numpy as np
ROOT = os.environ["ROOT"]
src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
m = src.index("class K3LadderOCR:")
m2 = src.index("\nclass ", m + 10)
k3 = src[m:m2]
# هلپرهایِ K3 از بیرونِ کلاس
picks = [k3]
tree = ast.parse(src)
for n in tree.body:
    if isinstance(n, ast.FunctionDef) and n.name in (
            "_k3_boost_crop", "_k3_map_boxes", "_k3_ink_coverage",
            "_k3_best_conf", "_k3_stats_note"):
        picks.append(ast.get_source_segment(src, n))
g = {"os": os, "np": np, "time": time, "print": print,
     "threading": threading}
g["_K3_STATS"] = {"ms": 0.0, "n": 0, "st1": 0, "st2": 0, "st3": 0}
exec(compile("\n\n".join(picks), "k3", "exec"), g)

calls, ml_calls = [], []
K3 = g["K3LadderOCR"]

class FakeML:
    def ocr(self, image):
        ml_calls.append(1)
        box = [[0, 0], [image.shape[1], 0],
               [image.shape[1], image.shape[0]], [0, image.shape[0]]]
        return [[[box, ("MLKIT", 0.8)]]]

class FakeEng:
    def __init__(self, tag):
        self.tag = tag
    def ocr(self, image, crop_mode=False):
        box = [[0, 0], [image.shape[1], 0],
               [image.shape[1], image.shape[0]], [0, image.shape[0]]]
        return [[[box, (self.tag, 0.9)]]]   # = [ lines ] با یک خط

def builder(small=False, tiny=False):
    tag = "tiny" if tiny else ("small" if small else "med")
    calls.append(tag)
    return FakeEng(tag.upper())

os.environ["MANGA_K3_MODE"] = "flutter"
lad = K3(FakeML(), "en", builder)
assert lad._mode == "flutter", lad._mode

img = np.full((200, 160, 3), 200, np.uint8)
out = lad.ocr(img, crop_mode=True)
assert out and out[0] and out[0][0][1][0] == "TINY", out
assert calls == ["tiny"], calls        # فقط tiny ساخته شد
assert not ml_calls, "ML Kit در روشِ flutter نباید صدا زده شود"

out2 = lad.ocr(img, crop_mode=False)   # پاسِ تمامصفحهٔ جانبی
assert out2 and out2[0][0][1][0] == "TINY", out2
assert "med" not in calls and "small" not in calls, calls  # medium/رپید نه
assert calls == ["tiny"], calls        # بارِ دوم از کش میآید
assert not ml_calls, "ML Kit در روشِ flutter نباید صدا زده شود"
print("K3_OK", calls)
'''
with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ)
    env["ROOT"] = ROOT
    r = subprocess.run([sys.executable, "-c", E2E_K3], env=env,
                       capture_output=True, text=True, timeout=120)
    out = r.stdout + r.stderr
    if r.returncode != 0 or "K3_OK" not in out:
        print(out[-3000:])
        fail("E2E-K3: نردبانِ flutter شکست خورد")
    ok("E2E-K3: کراپ و تمامصفحه در روشِ flutter = فقط tiny؛ ML Kit و "
       "medium هر دو خاموش")

print()
print("[✓] قراردادِ v1.14.181 رویِ چکِ 180 PASS")
