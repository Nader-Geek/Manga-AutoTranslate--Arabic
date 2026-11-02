#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.176 — «آزمایشگاهِ سرعتِ استخراج» در اپ:

دستورِ سازنده: «بازم استخراج کنده… یک گزینه تو گوشی بزار هر روشی بود
براش دکمه بذار — روشن کنم تست کنم ببینم کدوم سریعه».

۱) پنلِ «🧪 آزمایشگاه سرعت استخراج» در manga_app.py (۵ کلید):
   ocr_ep (auto/nnapi/xnnpack/cpu) | ocr_ladder (full/fast/rapid/
   paddle/flutter/padandroid) | ocr_threads (0-8) | ocr_detcap
   (640/960/1280) | ocr_boost.
   استخراجِ واقعیِ فرمِ گوشی (extract_ui) — نوع/گزینهها/پیشفرض.
۲) manga.py: K3LadderOCR حالتِ MANGA_K3_MODE (روشهایِ استخراج؛ v1.14.183:
   mlkit حذف شد، پلهٔ ۱ = پدلِ رسمیِ اندروید) +
   speed_lab_env (env + ریستِ سنجهها) + _k3_speed_report (گزارشِ آخرِ کار).
۳) bridge.py: سیمکشیِ speed_lab_env قبلِ موتور + گزارشِ سرعت در finally.
۴) rapidocr_mobile: کلیدِ کَشِ پلنِ EP = کلیدِ پروب + wanted → تعویضِ
   شتابدهنده از اپ همان اجرا اثر میکند (پلنِ کهنه برنمیگردد).
۵) عملی: AST-استخراجِ K3LadderOCR و speed_lab_env از manga.py و تستِ
   واقعیِ ۸ سناریویِ نردبان + ۶ سناریویِ env + گزارش.
۶) نسخه (سازگاریِ درونی — مستقل از شماره).
"""
import ast
import importlib.util
import io
import os
import json
import re
import sys
import time

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MP = os.path.join(ROOT, "manga.py")
AP = os.path.join(ROOT, "manga_app.py")
BRP = os.path.join(ROOT, "android", "app", "src", "main", "python",
                   "bridge.py")
RP = os.path.join(ROOT, "android", "app", "src", "main", "python",
                  "rapidocr_mobile", "__init__.py")


def fail(msg):
    print("[✗]", msg)
    sys.exit(1)


def ok(msg):
    print("[✓]", msg)


src = io.open(MP, encoding="utf-8").read()
rsrc = io.open(RP, encoding="utf-8").read()
asrc = io.open(AP, encoding="utf-8").read()
bsrc = io.open(BRP, encoding="utf-8").read()

# ۰) نسخه — 181/1.14.176
_m = re.search(r'^APP_VER = "([\d.]+)"', src, re.M)
_ver = io.open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read()
_vn = re.search(r"versionName=([\d.]+)", _ver)
_vc = re.search(r"versionCode=(\d+)", _ver)
if not _m or not _vn or not _vc:
    fail("APP_VER/VERSION ناقص است")
if _m.group(1) != (_vn.group(1) if _vn else None):
    fail(f"نسخه ناهمخوان: APP_VER={_m.group(1)} versionName="
         f"{_vn.group(1) if _vn else '?'}")
if not (_vc and _vc.group(1).isdigit()):
    fail(f"versionCode نامعتبر: {_vc.group(1) if _vc else '?'}")
if 'os.environ.setdefault("MANGA_APP_VER", APP_VER)' not in src:
    fail("manga.py باید MANGA_APP_VER را ست کند")
ok(f"نسخه {_vc.group(1) if _vc else '?'}/{_vn.group(1) if _vn else '?'}"
   " (APP_VER↔versionName↔versionCode)")

# ۱) گیتهایِ manga.py — نردبانِ حالtdار + آزمایشگاه
for s in ('_K3_MODES = ("full", "fast", "rapid", "paddle", "flutter",',
          '"padandroid")',
          'os.environ.get("MANGA_K3_MODE"',
          'self._mode = _m if _m in self._K3_MODES else "padandroid"',
          'if _mode in ("padandroid", "full", "fast"):',
          'if _mode in ("full", "paddle"):',
          'if _mode == "paddle":',
          'def speed_lab_env(p: dict) -> str:',
          'def _k3_speed_report() -> str:',
          '_SPEED_LAB_EP = ("auto", "nnapi", "xnnpack", "cpu")',
          '_SPEED_LAB_LADDER = ("full", "fast", "rapid", "paddle", "flutter",',
          'os.environ["MANGA_K3_MODE"]',
          # v1.14.183 — mlkit حذف شد؛ forceِ پدلِ رسمی سرِ جایش
          'os.environ["MANGA_K3_MODE"] = "padandroid"',
          '_SPEED_TEST_FILE = "speed_test.json"',
          'def speed_test_run(',
          'speed_test_load()'):
    if s not in src:
        fail(f"گیتِ manga.py نیست: {s!r}")
ok("manga.py: نردبانِ بدونِ ML Kit + speed_lab_env (پدلِ رسمی) + گزارش")

# ۲) rapidocr_mobile — کلیدِ کَش با wanted
if '+ "#" + ",".join(_wanted)' not in rsrc:
    fail("کلیدِ کَشِ پلنِ EP باید wanted را هم داشته باشد (تعویضِ EP از اپ)")
ok("rapidocr_mobile: کَشِ پلنِ EP حساس به wanted")

# ۳) bridge.py — سیمکشی
if 'getattr(_manga(), "speed_lab_env", None)' not in bsrc:
    fail("bridge باید speed_lab_env را قبلِ موتور صدا بزند")
if 'getattr(_manga(), "_k3_speed_report", None)' not in bsrc:
    fail("bridge باید گزارشِ سرعت را در finally لاگ کند")
ok("bridge.py: speed_lab_env + گزارشِ سرعت در finally")

# ۴) استخراجِ واقعیِ فرمِ گوشی — v1.14.181: دکمهٔ «تستِ سرعت» حذف شد
sys.path.insert(0, os.path.dirname(os.path.dirname(RP)))
from extract_ui import extract  # noqa: E402

mf = extract(AP)
FLDS = {}
for s in mf["sections"]:
    for f in s["fields"]:
        FLDS[f["id"]] = f
SEC = None
for s in mf["sections"]:
    if any(f["id"] == "ocr_speedtest" for f in s["fields"]):
        SEC = s
if SEC is not None:
    fail("v1.14.181: بخشِ تستِ سرعت نباید در فرمِ گوشی باشد")
_oldk = [k for k in ("ocr_ep", "ocr_ladder", "ocr_threads",
                     "ocr_detcap", "ocr_boost", "ocr_speedtest") if k in FLDS]
if _oldk:
    fail("سوییچهایِ کهنه/دکمهٔ تست هنوز در فرمِ گوشی هستند: %s" % _oldk)
ok("فرمِ گوشی: دکمهٔ «تستِ سرعت» هم حذف شد — فقط پدلِ رسمیِ اندروید (استخراجِ واقعی)")

tree = ast.parse(src)
_NEEDED = {"K3LadderOCR", "_k3_boost_crop", "_k3_map_boxes",
           "_k3_ink_coverage", "_k3_best_conf", "_k3_stats_note",
           "speed_lab_env", "_k3_speed_report",
           "speed_test_load", "_speed_test_path",
           "_speed_test_save",
           "_purge_loser_onnx_models"}  # v1.14.181
_CONSTS = {"_K3_STATS", "_SPEED_LAB_EP",
           "_SPEED_LAB_LADDER", "_SPEED_TEST_FILE", "_K3_MODE_FA",
           "_K3_PURGE_EXTRA", "_PURGE_MARKER"}  # v1.14.181
_nodes = []
for n in tree.body:
    if isinstance(n, ast.ClassDef) and n.name == "K3LadderOCR":
        _nodes.append(n)
    elif isinstance(n, ast.FunctionDef) and n.name in _NEEDED:
        _nodes.append(n)
    elif isinstance(n, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id in _CONSTS
            for t in n.targets):
        _nodes.append(n)
_got = set()
for n in _nodes:
    if isinstance(n, ast.ClassDef):
        _got.add(n.name)
    elif isinstance(n, ast.FunctionDef):
        _got.add(n.name)
if _got != _NEEDED:
    fail(f"AST-استخراج ناقص: کم است {_NEEDED - _got}")
ns = {"os": os, "time": time, "cv2": cv2, "np": np, "json": json,
      # v1.14.181 — وابستگیهایِ تابعِ پاکسازی (رویِ PC گیت False = skip)
      "_android_gate": lambda name: False,
      "_RAPIDOCR_FILES": {"PP-OCRv6_tiny_det.onnx": "u",
                          "ppocr_keys_v6_tiny_utf8.txt": "u"},
      "_fmt_mb": lambda n: "%.1fMB" % (n / (1024 * 1024)),
      # v1.14.182 — speed_lab_env این سنجه را هم ریست میکند
      "_PAD_STATS": {"ms": 0.0, "n": 0, "lines": 0},
      "APP_VER": "1.14.181"}
exec(compile(ast.Module(body=_nodes, type_ignores=[]), "<chk176>", "exec"),
     ns)
speed_lab_env = ns["speed_lab_env"]
k3_report = ns["_k3_speed_report"]
K3LadderOCR = ns["K3LadderOCR"]

# ── ۵الف) speed_lab_env — ۶ سناریو ──


import json  # noqa: E402
import tempfile  # noqa: E402

_tmpdir = tempfile.mkdtemp(prefix="chk176_")
os.environ["MANGA_FILES_DIR"] = _tmpdir
_STF = os.path.join(_tmpdir, "speed_test.json")


def _st_write(d):
    io.open(_STF, "w", encoding="utf-8").write(json.dumps(d))


def _st_del():
    try:
        os.remove(_STF)
    except OSError:
        pass


def _env_pop(*ks):
    for k in ks:
        os.environ.pop(k, None)


def sc_env(name, data, checks):
    """قراردادِ v1.14.178 — برندهٔ speed_test.json → env + خطِ لاگ."""
    _env_pop("MANGA_MOBILE_OCR_EP", "MANGA_K3_MODE", "MANGA_OCR_THREADS",
             "MANGA_XNN_THREADS", "MANGA_CROP_DET_CAP", "MANGA_CROP_ENH_SCALE")
    if data is None:
        _st_del()
    else:
        _st_write(data)
    line = speed_lab_env({}) or ""
    for desc, fn in checks:
        if not fn():
            fail(f"{name}: {desc}")
    return line


# v1.14.181 — speed_lab_env در «هر دو» شاخه فقط ML Kit را force میکند
# (برندهٔ تستِ ۱۷۹؛ مدلهایِ بازنده پاک، دکمهٔ تست حذف)؛ EP/کلیدهایِ کهنه
# سرِ جایشان هستند.
sc_env("E1 بدونِ نتیجه", None, [
    ("EP پاک", lambda: "MANGA_MOBILE_OCR_EP" not in os.environ),
    ("MODE=padandroid",
     lambda: os.environ.get("MANGA_K3_MODE") == "padandroid"),
    ("نخ پاک", lambda: "MANGA_OCR_THREADS" not in os.environ),
    ("سقف پاک", lambda: "MANGA_CROP_DET_CAP" not in os.environ),
    ("بزرگنمایی پاک", lambda: "MANGA_CROP_ENH_SCALE" not in os.environ),
])
_l1 = speed_lab_env({})
for frag in ("پدلِ رسمیِ اندروید", "v1.14.183"):
    if frag not in _l1:
        fail(f"E1 خطِ لاگ باید {frag!r} داشته باشد: {_l1}")
ok("E1 بدونِ نتیجه = پدلِ رسمیِ اندروید (پیشفرضِ 183) + پاکسازیِ کلیدهایِ کهنه")

sc_env("E2 برندهٔ fast+nnapi",
       {"ladder": "fast", "ep": "nnapi", "ladder_ms": {"fast": 123}},
       [("EP=nnapi", lambda: os.environ.get("MANGA_MOBILE_OCR_EP") == "nnapi"),
        ("MODE=padandroid (forceِ 183)",
         lambda: os.environ.get("MANGA_K3_MODE") == "padandroid")])
_l2 = speed_lab_env({})
for frag in ("پدلِ رسمیِ اندروید", "nnapi", "v1.14.183"):
    if frag not in _l2:
        fail(f"E2 خطِ برنده باید {frag!r} داشته باشد: {_l2}")
ok("E2 برندهٔ فایل → EP + روشِ پدلِ رسمیِ اندروید (forceِ 183)")

sc_env("E3 برندهٔ full+auto", {"ladder": "full", "ep": "auto"}, [
    ("EP پاک", lambda: "MANGA_MOBILE_OCR_EP" not in os.environ),
    ("MODE=padandroid (forceِ 183)",
     lambda: os.environ.get("MANGA_K3_MODE") == "padandroid"),
])
ok("E3 full/auto = EP پاک + پدلِ رسمیِ اندروید (forceِ 183)")

sc_env("E4 نامعتبر", {"ladder": "weird", "ep": "nope"}, [
    ("EP→پاک", lambda: "MANGA_MOBILE_OCR_EP" not in os.environ),
    ("MODE=padandroid (forceِ 183)",
     lambda: os.environ.get("MANGA_K3_MODE") == "padandroid"),
])
ok("E4 مقدارهایِ نامعتبر → EPِ امن + پدلِ رسمیِ اندروید (forceِ 183)")

# E5 کلیدهایِ کهنهٔ سوییچهایِ 176/177 نباید زنده بمانند
os.environ["MANGA_OCR_THREADS"] = "8"
os.environ["MANGA_XNN_THREADS"] = "8"
os.environ["MANGA_CROP_DET_CAP"] = "640"
os.environ["MANGA_CROP_ENH_SCALE"] = "1.0"
_st_del()
speed_lab_env({})
for _k in ("MANGA_OCR_THREADS", "MANGA_XNN_THREADS",
           "MANGA_CROP_DET_CAP", "MANGA_CROP_ENH_SCALE"):
    if _k in os.environ:
        fail(f"E5 کلیدِ کهنهٔ {_k} پاک نشد")
ok("E5 کلیدهایِ کهنهٔ سوییچها پاک میشوند")

# E6 ریستِ سنجهها
ns["_K3_STATS"].update({"n": 7, "ms": 7000.0, "st1": 3, "st2": 2, "st3": 2})
ns["_PAD_STATS"].update({"ms": 3000.0, "n": 6, "lines": 9})
_st_del()
speed_lab_env({})
if ns["_K3_STATS"]["n"] != 0 or ns["_PAD_STATS"]["n"] != 0:
    fail("E6 سنجهها باید بینِ کارها ریست شوند")
ok("E6 ریستِ سنجههایِ سرعت بینِ کارها")

# ── ۵ب) _k3_speed_report ──
if k3_report() != "":    fail("گزارش با سنجهٔ صفر باید خالی باشد")
ns["_K3_STATS"].update({"n": 40, "ms": 800000.0, "st1": 20, "st2": 15,
                        "st3": 5})
_r = k3_report()
for frag in ("40 کراپ", "20000ms", "رسمی=20", "پدل=15", "رپید=5"):
    if frag not in _r:
        fail(f"گزارشِ سرعت باید {frag!r} داشته باشد: {_r}")
# v1.14.182/183 — روشِ فعلی = padandroid (forceِ پدلِ رسمی)
if "روش=padandroid" not in _r:
    fail("گزارش باید روشِ فعلی را بگوید: " + _r)
ok("گزارشِ سرعت: میانگین/پلهها/روش — فرمتِ درست")

# ── ۵پ) نردبانِ K3 — ۸ سناریو با موتورهایِ فیک ──
_CROP = np.zeros((200, 300, 3), dtype=np.uint8)  # سیاهِ خالص → پوشش=1.0


def _lines(*pairs):
    box = np.array([[0, 0], [100, 0], [100, 40], [0, 40]], dtype=np.float32)
    return [[box.copy(), (t, float(c))] for t, c in pairs]


class FakePad:
    """پلهٔ ۱ (پدلِ رسمیِ اندروید — v1.14.183): eng0.ocr(boosted)."""

    def __init__(self, lines):
        self.lines = lines
        self.calls = 0

    def ocr(self, img):
        self.calls += 1
        return [list(self.lines)] if self.lines else None


class FakeEng:
    def __init__(self, lines, name):
        self.lines = lines
        self.name = name
        self.calls = 0

    def ocr(self, img, crop_mode=False):
        self.calls += 1
        return [list(self.lines)] if self.lines else None


class FakeBuild:
    def __init__(self, med_lines=None, sml_lines=None):
        self.med_lines = med_lines
        self.sml_lines = sml_lines
        self.made = []

    def __call__(self, small):
        self.made.append(bool(small))
        return FakeEng(list(self.sml_lines or []) if small
                       else list(self.med_lines or []),
                       "sml" if small else "med")


def reset_ladder(monkey_env):
    _env_pop("MANGA_K3_MODE")
    os.environ.update(monkey_env or {})
    ns["_K3_STATS"].update({"n": 0, "ms": 0.0, "st1": 0, "st2": 0, "st3": 0})


STRONG = _lines(("Hello", 0.95))
WEAK = _lines(("hm", 0.30))
MED_OK = _lines(("Medium text", 0.90))
MED_WEAK = _lines(("med weak", 0.50))
SML_OK = _lines(("Rapid text", 0.85))

# T1 — full + پدلِ رسمیِ قوی: همان رفتار؛ موتورِ ONNX هرگز ساخته نمیشود
# (v1.14.183: پلهٔ ۱ = پدلِ رسمی؛ full فقط برایِ این سناریوهایِ فیک)
reset_ladder({"MANGA_K3_MODE": "full"})
ml, fb = FakePad(STRONG), FakeBuild(MED_OK, SML_OK)
lad = K3LadderOCR("en", fb, build_pad=lambda: ml)
r = lad.ocr(_CROP, crop_mode=True)
if not r or not r[0] or r[0][0][1][0] != "Hello":
    fail(f"T1 نتیجهٔ پدلِ رسمیِ قوی خراب: {r}")
if fb.made or ml.calls != 1:
    fail(f"T1 در full نباید ONNX ساخته شود: made={fb.made}")
if ns["_K3_STATS"]["st1"] != 1:
    fail("T1 باید پلهٔ ۱ شمرده شود")
ok("T1 full + پدلِ رسمیِ قوی → پلهٔ ۱ (بدونِ ساختنِ ONNX)")

# T2 — full + پدلِ رسمیِ ضعیف + پدلِ ONNXِ قوی: پلهٔ ۲؛ رپید ساخته نمیشود
reset_ladder({"MANGA_K3_MODE": "full"})
ml, fb = FakePad(WEAK), FakeBuild(MED_OK, SML_OK)
lad = K3LadderOCR("en", fb, build_pad=lambda: ml)
r = lad.ocr(_CROP, crop_mode=True)
if not r or r[0][0][1][0] != "Medium text":
    fail(f"T2 پلهٔ ۲ خراب: {r}")
if fb.made != [False] or ns["_K3_STATS"]["st2"] != 1:
    fail(f"T2 باید فقط پدل ساخته شود: made={fb.made}")
ok("T2 full + پدلِ قوی → پلهٔ ۲ (رپید ساخته نمیشود)")

# T3 — full + پدلِ ضعیف: پلهٔ ۳ (رپید)
reset_ladder({"MANGA_K3_MODE": "full"})
ml, fb = FakePad(WEAK), FakeBuild(MED_WEAK, SML_OK)
lad = K3LadderOCR("en", fb, build_pad=lambda: ml)
r = lad.ocr(_CROP, crop_mode=True)
if not r or r[0][0][1][0] != "Rapid text":
    fail(f"T3 پلهٔ ۳ خراب: {r}")
if fb.made != [False, True] or ns["_K3_STATS"]["st3"] != 1:
    fail(f"T3 باید پدل+رپید ساخته شود: made={fb.made}")
ok("T3 full + پدلِ ضعیف → پلهٔ ۳ رپید")

# T4 — fast: پدلِ medium هرگز ساخته/صدا زده نمیشود؛ رپید جای آن
reset_ladder({"MANGA_K3_MODE": "fast"})
ml, fb = FakePad(WEAK), FakeBuild(MED_OK, SML_OK)
lad = K3LadderOCR("en", fb, build_pad=lambda: ml)
r = lad.ocr(_CROP, crop_mode=True)
if not r or r[0][0][1][0] != "Rapid text":
    fail(f"T4 فست خراب: {r}")
if fb.made != [True]:
    fail(f"T4 در fast باید فقط مجموعهٔ سبک ساخته شود: made={fb.made}")
ok("T4 fast = پدلِ رسمی ← رپید (مدلِ سنگینِ پدل حذف)")

# T5 — padandroid: حتی با اطمینانِ ضعیف همان پدلِ رسمی برگردانده میشود؛
# بدونِ ONNX (v1.14.183: mlkit حذف شد — فقط پدلِ رسمی)
reset_ladder({"MANGA_K3_MODE": "padandroid"})
ml, fb = FakePad(WEAK), FakeBuild(MED_OK, SML_OK)
lad = K3LadderOCR("en", fb, build_pad=lambda: ml)
r = lad.ocr(_CROP, crop_mode=True)
if not r or r[0][0][1][0] != "hm":
    fail(f"T5 فقط-ML Kit خراب: {r}")
if fb.made:
    fail(f"T5 در mlkit نباید ONNX ساخته شود: made={fb.made}")
reset_ladder({"MANGA_K3_MODE": "mlkit"})
ml, fb = FakePad([]), FakeBuild(MED_OK, SML_OK)
r = K3LadderOCR("en", fb, build_pad=lambda: ml).ocr(_CROP, crop_mode=True)
if r is not None or fb.made:
    fail(f"T5b ML Kitِ خالی در mlkit باید None بدهد: {r}")
ok("T5 mlkit = فقط ML Kit (ضعیف هم برمیگردد؛ خالی = None؛ بدونِ ONNX)")

# T6 — rapid: پدلِ رسمی اصلاً صدا زده نمیشود؛ فقط رپید
reset_ladder({"MANGA_K3_MODE": "rapid"})
ml, fb = FakePad(STRONG), FakeBuild(MED_OK, SML_OK)
lad = K3LadderOCR("en", fb, build_pad=lambda: ml)
r = lad.ocr(_CROP, crop_mode=True)
if not r or r[0][0][1][0] != "Rapid text":
    fail(f"T6 فقط-رپید خراب: {r}")
if ml.calls != 0 or fb.made != [True]:
    fail(f"T6 باید بدونِ پدلِ رسمی و فقط سبک باشد: calls={ml.calls} "
         f"made={fb.made}")
ok("T6 rapid = فقط رپید (پلهٔ ۱ هم صدا زده نمیشود)")

# T7 — paddle: فقط پدل؛ بدونِ پلهٔ ۳ حتی با اطمینانِ زیرِ ۸۰٪
reset_ladder({"MANGA_K3_MODE": "paddle"})
ml, fb = FakePad(WEAK), FakeBuild(MED_WEAK, SML_OK)
lad = K3LadderOCR("en", fb, build_pad=lambda: ml)
r = lad.ocr(_CROP, crop_mode=True)
if not r or r[0][0][1][0] != "med weak":
    fail(f"T7 فقط-پدل خراب: {r}")
if fb.made != [False]:
    fail(f"T7 در paddle نباید رپید ساخته شود: made={fb.made}")
if ns["_K3_STATS"]["st3"] != 0:
    fail("T7 پلهٔ ۳ نباید شمرده شود")
ok("T7 paddle = فقط پدل (رپید هرگز)")

# T8 — حالتِ ناشناخته → padandroid (پیشفرضِ امنِ 183؛ پدلِ رسمیِ ضعیف
# برمیگردد — بازندههایِ ONNX بیدار نمیشوند و فالبکی هم نیست)
reset_ladder({"MANGA_K3_MODE": "weird"})
ml, fb = FakePad(WEAK), FakeBuild(MED_OK, SML_OK)
lad = K3LadderOCR("en", fb, build_pad=lambda: ml)
if lad._mode != "padandroid":
    fail("T8 حالتِ ناشناخته باید padandroid شود")
r = lad.ocr(_CROP, crop_mode=True)
if not r or r[0][0][1][0] != "hm":
    fail(f"T8 فالبکِ padandroid خراب: {r}")
if fb.made:
    fail(f"T8 در فالبکِ padandroid نباید ONNX ساخته شود: made={fb.made}")
ok("T8 MANGA_K3_MODEِ ناشناخته → padandroid (پیشفرضِ امنِ 183)")

# ۶) py_compile نهایی
import py_compile  # noqa: E402
for p in (MP, AP, BRP, RP):
    py_compile.compile(p, doraise=True)
ok("py_compile: manga.py / manga_app.py / bridge.py / rapidocr_mobile")

print("\nهمهٔ گیتهایِ v1.14.176 PASS ✓")
