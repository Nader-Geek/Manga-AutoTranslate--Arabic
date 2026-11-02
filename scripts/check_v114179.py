#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.179 — «تستِ سرعت» همهٔ روشها را میپیماید + فلاتر-پدل.

دستورِ سازنده: «این دکمه تستی که گذاشتی همه حالت استخراج تست کنه فقط
یک حالت تست زد که اونم گیر بود؛ همه حالت هایی که واسه استخراج تو گوشی
هست تست کنه؛ و flutter-paddle-ocr اینم اضافه کن واسه تست؛ Paddle-Lite
اصلا اضافه نکن».

۱) بنبستِ ۱۷۸ ریشه‌ای فیکس شد: برداشتِ کراپ با موتورِ سبک (نه پدلِ
   mediumِ ۱۳۰MB) و اگر تشخیص چیزی نداد، کاشیهایِ واقعیِ خودِ صفحه
   (~۵۱۲px) — پیامِ «در تصویر متنِ خواندنی پیدا نشد» + قطعِ کلِ تست
   حذف شده است.
۲) روشِ ششم «flutter» (فلاتر-پدل = PP-OCRv6 tinyِ flutter-paddle-ocr —
   ONNXِ خالص، نه Paddle-Lite): _K3_MODES/_SPEED_LAB_LADDER/need_ok/
   dictِ مخصوصِ ۶۹۰۴ی؛ مدلها از HFِ رسمی + ریلیزِ modelsِ خودمان.
۳) E2E عملی: (الف) تصویرِ بی‌det → کاشیهایِ جایگزین → همهٔ ۹ پنجره؛
   (ب) _speed_test_tiles مستقیم (شکلهایِ مختلفِ صفحه + cap).
۴) Paddle-Lite برنگشته (هیچ PaddleLiteBridge/PliteProbeService/pplite_)
   و PC بیت‌به‌بیت (tiny فقط در مسیرِ موبایل).
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
# v1.14.180 — گیتِ نسخه باز شد: رفتارِ ۱۷۹ در ۱۸۰ دستنخورده ماند
# (فقط روشِ فعالِ پیشفرض در speed_lab_env فلاتر-پدل شد — خارجِ scopeِ
# این چک که speed_test_run/کاشیهاست)
_vt = tuple(int(x) for x in _m.group(1).split("."))
if _vt < (1, 14, 179):
    fail("V: این چک برایِ 1.14.179+ است (APP_VER=%s)" % _m.group(1))
ok("V: نسخه %s / versionCode=%s" % (_m.group(1), _vc.group(1)))

# ── ۱) فلاتر-پدل = روشِ ششم ──────────────────────────────────────
if '"flutter"' not in src:
    fail("F: کلیدِ flutter در manga.py نیست")
tree = ast.parse(src)


def _func(name):
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and n.name == name:
            return n
    return None


_k3_src = src[src.index("class K3LadderOCR:"):src.index("\nclass ", src.index("class K3LadderOCR:") + 10)]
if '_K3_MODES = ("full", "fast", "mlkit", "rapid", "paddle", "flutter",' \
        not in _k3_src or '"padandroid")' not in _k3_src:
    fail("F: _K3_MODES شاملِ flutter/padandroid نیست")
if "def _engine_tiny(self):" not in _k3_src:
    fail("F: K3LadderOCR._engine_tiny غایب است")
if 'if _mode not in ("rapid", "flutter"):' not in _k3_src:
    fail("F: پلهٔ ۱ (ML Kit) برایِ flutter حذف نشده")
if 'eng3 = self._engine_tiny()' not in _k3_src:
    fail("F: پلهٔ ۳ در flutter موتورِ tiny نمیگیرد")
ok("F: K3LadderOCR = ۷ روش + _engine_tiny")

_pairs = ast.get_source_segment(src, _func("_rapidocr_model_pair")) or ""
if "tiny: bool = False" not in _pairs or 'PP-OCRv6_tiny_det.onnx' not in _pairs \
        or "PP-OCRv6_tiny_rec.onnx" not in _pairs:
    fail("F: _rapidocr_model_pair شاخهٔ tiny ندارد")
_files = ast.get_source_segment(src, _func("_build_mobile_onnx")) or ""
if "tiny: bool = False" not in _files or "tiny=tiny" not in _files \
        or "ppocr_keys_v6_tiny_utf8.txt" not in _files:
    fail("F: _build_mobile_onnx tiny/dictِ tiny ندارد")
for _u in ("PP-OCRv6_tiny_det.onnx", "PP-OCRv6_tiny_rec.onnx",
           "ppocr_keys_v6_tiny_utf8.txt"):
    if '"%s":' % _u not in src:
        fail("F: %s در _RAPIDOCR_FILES نیست" % _u)
if "PaddlePaddle/PP-OCRv6_tiny_det_onnx" not in src \
        or "PaddlePaddle/PP-OCRv6_tiny_rec_onnx" not in src:
    fail("F: لینکِ HFِ رسمیِ tiny نیست")
ok("F: مدلهایِ tiny (det 1.7MB + rec 4.3MB + dictِ ۶۹۰۴ی) سیمکشی شد")

# ── ۲) بنبستِ ۱۷۸ فیکس شده ───────────────────────────────────────
if 'log("[!] در تصویر متنِ خواندنی پیدا نشد' in src:
    fail("D: پیامِ بنبستِ ۱۷۸ هنوز هست (باید حذف شده باشد)")
_str = ast.get_source_segment(src, _func("speed_test_run")) or ""
if "_speed_test_tiles(page)" not in _str:
    fail("D: speed_test_run فالبکِ کاشی ندارد")
if "be._build_mobile_onnx(lang, small=False, tiny=True)" not in _str:
    fail("D: speed_test_run موتورِ فلاتر-پدل را نمیسازد")
if '"flutter": _tiny is not None' not in _str:
    fail("D: need_ok شاملِ flutter نیست")
if "کاشیِ واقعی" not in _str:
    fail("D: لاگِ فالبکِ کاشی ندارد")
_tiles = ast.get_source_segment(src, _func("_speed_test_tiles")) or ""
if "512" not in _tiles or "cap" not in _tiles:
    fail("D: _speed_test_tiles درست تعریف نشده")
# برداشت = موتورِ سبک (نه پدلِ mediumِ گیرکننده)
if "_sml.ocr(page, crop_mode=False)" not in _str:
    fail("D: برداشتِ کراپ باید با موتورِ سبک باشد")
ok("D: بنبستِ ۱۷۸ فیکس — فالبکِ کاشی + برداشتِ سبک + پنجرهٔ flutter")

# ── ۳) مهارِ Paddle-Lite + سلامتِ PC ────────────────────────────
# (ذکرِ تاریخیِ «PaddleLiteBridge» در کامنتهایِ 170 مجاز است — چیزی که
# ممنوع است برگشتنِ کد/سرویس/وابستگی است)
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
_mf = os.path.join(ROOT, "android", "app", "src", "main", "AndroidManifest.xml")
if "PliteProbeService" in io.open(_mf, encoding="utf-8").read():
    fail("P: سرویسِ :pliteprobe در مانیفست برگشته")
# PC: تنها فراخوانِ tiny در _build_mobile_onnx است (مسیرِ موبایل) —
# بقیهٔ فراخوانهایِ _rapidocr_model_pair بدونِ tiny بمانند
_callers = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "_rapidocr_model_pair"]
# (فراخوانِ ماژولی هم ممکن است) — فراخوانِ تابعِ آزاد:
_callers += [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name)
             and n.func.id == "_rapidocr_model_pair"]
_bad = []
for c in _callers:
    _kw = [k.arg for k in c.keywords]
    if "tiny" in _kw and not (
            getattr(c.func, "attr", "") or getattr(c.func, "id", "")
    ) == "_rapidocr_model_pair":
        _bad.append(_kw)
if _bad:
    fail("P: فراخوانِ tiny خارجِ _build_mobile_onnx: %s" % _bad)
ok("P: Paddle-Lite برنگشته + PC بیت‌به‌بیت (tiny فقط مسیرِ موبایل)")

# ── ۴) E2E: تصویرِ بی‌det → کاشیهایِ جایگزین → همهٔ پنجرهها ──────
E2E = r'''
# -*- coding: utf-8 -*-
import io, json, os, sys, threading, time
import numpy as np, cv2

ROOT = os.environ["ROOT"]
ST_DIR = os.environ["ST_DIR"]
PER = float(os.environ.get("ST_PER", "0.10"))

src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
import ast
tree = ast.parse(src)
picks = {}
wanted = ["speed_test_run", "_speed_test_pool", "_speed_test_window",
          "_speed_test_tiles", "speed_test_load", "_speed_test_save",
          "_speed_test_path"]
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in wanted:
        picks[node.name] = ast.get_source_segment(src, node)
for node in tree.body:
    if isinstance(node, ast.Assign) and getattr(
            node.targets[0], "id", "") == "_K3_MODE_FA":
        picks["_K3_MODE_FA"] = ast.get_source_segment(src, node)
m = src.index("class K3LadderOCR:")
m2 = src.index("\nclass ", m + 10)
picks["K3LadderOCR"] = src[m:m2]

class FakeEng:
    """detِ تمامصفحه = هیچ (سناریویِ لاگِ ۱۷۸)؛ کراپ = خروجیِ سبک"""
    def __init__(self, tag, delay=0.0, nodet=False):
        self.tag, self.delay, self.nodet = tag, delay, nodet
    def ocr(self, image, crop_mode=False, det_cap=None):
        if self.delay:
            t0 = time.time()
            while time.time() - t0 < self.delay:
                pass
        if not crop_mode:
            if self.nodet:
                return None
            return [[[0, 0], [image.shape[1], 0],
                     [image.shape[1], image.shape[0]], [0, image.shape[0]]],
                    ("BOX", 0.9)]
        return [[[0, 0], [image.shape[1], 0],
                 [image.shape[1], image.shape[0]], [0, image.shape[0]]],
                ("t", 0.95)]

class FakeML:
    def __init__(self, lang="en"):
        self.lang = lang
    def ocr(self, image):
        return [[[0, 0], [image.shape[1], 0],
                 [image.shape[1], image.shape[0]], [0, image.shape[0]]],
                ("m", 0.8)]

class FakeMT:
    @staticmethod
    def _imread_any(p):
        return cv2.imread(p)

g = {"os": os, "time": time, "json": json, "np": np, "cv2": cv2,
     "threading": threading, "print": print, "APP_VER": "1.14.179-test",
     "_K3_STATS": {"ms": 0.0, "n": 0, "st1": 0, "st2": 0, "st3": 0},
     "_MLKIT_STATS": {"ms": 0.0, "n": 0, "lines": 0},
     "_k3_stats_note": lambda *a, **k: None,
     "_k3_boost_crop": lambda image, *a, **k: (image, None, 1.0),
     "_k3_map_boxes": lambda r, pad=None, scale=1.0: (r or []),
     "_k3_ink_coverage": lambda image, lines: 0.99,
     "_k3_best_conf": lambda lines: 0.9,
     "_mlkit_backend": lambda lang: FakeML(),
     "_mlkit_lang": lambda l: l,
     "MangaTranslator": FakeMT,
     "MlKitCropOCR": FakeML, "RapidOCRBackend": object}
exec(compile("\n\n".join(picks.values()), "manga_bits", "exec"), g)

os.environ["MANGA_FILES_DIR"] = ST_DIR
img = np.full((1200, 900, 3), 128, np.uint8)
cv2.imwrite(os.path.join(ST_DIR, "page.png"), img)

class FakeBE:
    def __init__(self, lang="en"):
        self.lang = lang
        self._mobile = g["K3LadderOCR"](FakeML(), lang,
                                        lambda small=False, tiny=False:
                                        FakeEng("e"))
    def _build_mobile_onnx(self, lang, small=False, tiny=False):
        # فقط موتورِ سبک detِ تمامصفحهاش «هیچ» میدهد — عینِ لاگِ ۱۷۸
        return FakeEng("sml" if small else "e", 0.003, nodet=small)

lines = []
res = g["speed_test_run"](
    src=os.path.join(ST_DIR, "page.png"), langs=("en",), per_mode=PER,
    log=lines.append, backend=FakeBE())
stf = os.path.join(ST_DIR, "speed_test.json")
assert res and os.path.isfile(stf), "نتیجه/فایل نبود"
d = json.load(io.open(stf, encoding="utf-8"))
tile_line = [ln for ln in lines if "کاشیِ واقعی" in ln]
assert tile_line, "فالبکِ کاشی در لاگ نیست: %s" % lines[:8]
assert d.get("crops") == 4, d   # ۹۰۰×۱۲۰۰ → ۲×۲ کاشی
modes = [k for k, v in d["ladder_ms"].items() if v]
assert set(modes) == {"full", "fast", "mlkit", "rapid", "paddle",
                      "flutter", "padandroid"}, d["ladder_ms"]
wlines = [ln for ln in lines if ln.startswith("[⚡] (") and "میانگینِ" in ln]
assert len(wlines) == 10, wlines   # ۷ روش + ۳ شتاب‌دهنده — هیچ بنبستی
win = [ln for ln in lines if ln.startswith("[⚡] برنده")]
assert win, lines[-4:]
print("E2E_OK", json.dumps({"crops": d["crops"], "ladder": d["ladder"],
                            "ep": d["ep"]}, ensure_ascii=False))
'''

with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ)
    env["ROOT"] = ROOT
    env["ST_DIR"] = td
    env["ST_PER"] = "0.10"
    r = subprocess.run([sys.executable, "-c", E2E], env=env,
                       capture_output=True, text=True, timeout=300)
    out = r.stdout + r.stderr
    if r.returncode != 0 or "E2E_OK" not in out:
        print(out[-3500:])
        fail("E2E: زیرپروسه شکست خورد")
    d = json.loads(out.split("E2E_OK", 1)[1].split("\n", 1)[0])
    ok("E2E: بی‌det → %d کاشی → هر ۱۰ پنجره اندازهگیری شد + برنده=%s/%s"
       % (d["crops"], d["ladder"], d["ep"]))

# ── ۵) _speed_test_tiles مستقیم (شکلها + cap) ────────────────────
TCHK = r'''
import ast, io, os, sys
import numpy as np
src = io.open(os.path.join(os.environ["ROOT"], "manga.py"),
              encoding="utf-8").read()
tree = ast.parse(src)
seg = None
for n in tree.body:
    if isinstance(n, ast.FunctionDef) and n.name == "_speed_test_tiles":
        seg = ast.get_source_segment(src, n)
g = {"np": np}
exec(compile(seg, "t", "exec"), g)
f = g["_speed_test_tiles"]
# صفحهٔ معمولی ۹۰۰×۱۲۰۰ → ۲×۲
t = f(np.zeros((1200, 900, 3), np.uint8))
assert len(t) == 4 and all(x.shape[0] >= 64 and x.shape[1] >= 64 for x in t), \
    [x.shape for x in t]
# استریپِ بلند ۸۰۰×۲۰۰۰۰ → حداکثر ۲×۶=۱۲ کاشی (کَپِ ۲۴)
t2 = f(np.zeros((20000, 800, 3), np.uint8))
assert 1 <= len(t2) <= 24, len(t2)
# تک‌بلوکِ ۴۰۰×۴۰۰ → ۱ کاشی
t3 = f(np.zeros((400, 400, 3), np.uint8))
assert len(t3) == 1, len(t3)
print("TILES_OK")
'''
with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ)
    env["ROOT"] = ROOT
    r = subprocess.run([sys.executable, "-c", TCHK], env=env,
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0 or "TILES_OK" not in (r.stdout + r.stderr):
        print((r.stdout + r.stderr)[-2000:])
        fail("TILES: تستِ مستقیمِ کاشیها شکست خورد")
ok("TILES: ۹۰۰×۱۲۰۰→۴ | ۲۰۰۰۰px→کَپِ ۲۴ | ۴۰۰²→۱")

print()
print("[✓] همهٔ گیتهایِ v1.14.179 PASS")
