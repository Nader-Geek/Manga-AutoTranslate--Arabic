#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.178 — «تستِ سرعت»: یک دکمه، همهٔ حالتها.

دستورِ سازنده: «حذف کن یک کار دیگ بکن — یک دونه دکمه بزار، فعال کردم
همه حالت تست کنه، تایم بگیره یک دقیقه هرکدومشون، بعد ببینم کدومش
سریعه».

۱) پنل: فقط یک فیلدِ ocr_speedtest (bool) — هیچ سوییچِ ocr_ep/… نیست
   (extract_uiِ واقعی رویِ manga_app.py).
۲) E2E عملی در زیرپروسه: manga.py main با MANGA_SPEED_TEST=1 و
   per_modeِ کوتاه (متغیرِ محیطیِ چک — رفتارِ اصلی ۶۰ ثانیه) رویِ
   تصویرِ مصنوعی با backendِ تزریقشده → فایلِ speed_test.json + جدولِ
   [⚡] + برنده.
۳) nnapi_pending: اجرایِ قبل که حینِ NNAPI مرده → پنجرهٔ NNAPI رد
   میشود؛ پس از پنجرهٔ سالم نشان پاک میشود.
۴) speed_lab_envِ فایل‌محور: با نتیجه → env + خطِ برنده؛ بدونِ نتیجه →
   پاکسازیِ env + پیشفرض.
۵) قراردادِ bridge (_speed_test_job قبل از چکِ کلید + should_stop) و
   Kotlin (فقط ocr_speedtest در collect + خاموشیِ خودکار در done).
۶) نسخه (سازگاریِ درونی — مستقل از شماره).
"""
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MP = os.path.join(ROOT, "manga.py")
AP = os.path.join(ROOT, "manga_app.py")
BRP = os.path.join(ROOT, "android", "app", "src", "main", "python",
                   "bridge.py")
RP = os.path.join(ROOT, "android", "app", "src", "main", "python",
                  "rapidocr_mobile", "__init__.py")
KTP = os.path.join(ROOT, "android", "app", "src", "main", "java",
                   "com", "amirwolf", "mangatranslator", "MainActivity.kt")


def fail(msg):
    print("[✗]", msg)
    sys.exit(1)


def ok(msg):
    print("[✓]", msg)


def read(p):
    return io.open(p, encoding="utf-8").read()


src = read(MP)
asrc = read(AP)
bsrc = read(BRP)
rsrc = read(RP)
ksrc = read(KTP)

# ── ۰) نسخه ──────────────────────────────────────────────────────
_m = re.search(r'^APP_VER = "([\d.]+)"', src, re.M)
_ver = read(os.path.join(ROOT, "VERSION"))
_vn = re.search(r"versionName=([\d.]+)", _ver)
_vc = re.search(r"versionCode=(\d+)", _ver)
if not _m or not _vn or not _vc:
    fail("V: نسخه پیدا نشد")
elif _m.group(1) != _vn.group(1):
    fail("V: APP_VER(%s) != versionName(%s)" % (_m.group(1), _vn.group(1)))
else:
    ok("V: نسخه %s / versionCode=%s" % (_m.group(1), _vc.group(1)))
APP_VER = _m.group(1)

# ── ۱) پنل: فقط یک کلید ──────────────────────────────────────────
sys.path.insert(0, os.path.join(ROOT, "android", "app", "src",
                                "main", "python"))
import extract_ui as eu  # noqa: E402

fields = eu.extract(AP)
found = {}
for sec in ((fields or {}).get("sections") or []):
    for f in (sec.get("fields") or []):
        if isinstance(f, dict) and str(f.get("id", "")).startswith("ocr_"):
            found[f["id"]] = f
if list(found.keys()) != ["ocr_speedtest"]:
    fail("U: پنل باید فقط ocr_speedtest را داشته باشد (دارد: %s)"
         % list(found.keys()))
elif found["ocr_speedtest"].get("type") != "bool":
    fail("U: ocr_speedtest باید bool باشد")
else:
    ok("U: پنل = فقط «⚡ تستِ سرعت» (bool) — سوییچها حذف شدند")
old_keys = [k for k in ("ocr_ep", "ocr_ladder", "ocr_threads",
                        "ocr_detcap", "ocr_boost")
            if ("gr.Dropdown" in asrc and ('"%s"' % k) in asrc
            and k in asrc.split("def run_translation")[0])]
if old_keys:
    fail("U: سوییچهایِ کهنه هنوز در ویجتها هستند: %s" % old_keys)
else:
    ok("U: هیچ سوییچِ کهنه‌ای در ویجتها نیست")

# ── ۲) قراردادهایِ استاتیک ───────────────────────────────────────
if "def speed_test_run(" not in src or "_speed_test_window(" not in src \
        or "_speed_test_pool(" not in src or "speed_test_load()" not in src:
    fail("S: speed_test_run/_window/_pool/load در manga.py غایب است")
elif 'os.environ.get("MANGA_SPEED_TEST"' not in src:
    fail("S: main() دروازهٔ MANGA_SPEED_TEST ندارد")
elif 'nnapi_pending' not in src:
    fail("S: نشانِ nnapi_pending در manga.py نیست")
else:
    ok("S: ماشینِ «تستِ سرعت» در manga.py کامل است")
if "_speed_test_job(" not in bsrc or 'p.get("ocr_speedtest")' not in bsrc:
    fail("B: bridge مسیرِ تستِ سرعت ندارد")
_pos_branch = bsrc.index('p.get("ocr_speedtest")')
_pos_keys = bsrc.index('keys = [k.strip() for k in str(p.get("keys")')
if _pos_branch > _pos_keys:
    fail("B: مسیرِ تستِ سرعت باید قبل از چکِ کلیدِ API باشد")
else:
    ok("B: bridge مسیرِ تست را قبل از چکِ کلید میگیرد + should_stop")
if 'map.put("ocr_speedtest", optBool(o, "ocr_speedtest"))' not in ksrc:
    fail("K: collect() دیگر ocr_speedtest را نمیفرستد")
for _k in ("ocr_ep", "ocr_ladder", "ocr_threads", "ocr_detcap", "ocr_boost"):
    if _k in ksrc:
        fail("K: کلیدِ کهنهٔ %s هنوز در MainActivity است" % _k)
else:
    ok("K: collect فقط ocr_speedtest + خاموشیِ خودکار در done")
if "speedTestSent" not in ksrc or 'fieldViews["ocr_speedtest"]' not in ksrc:
    fail("K: خاموشیِ خودکارِ کلید بعد از done نیست")
else:
    ok("K: speedTestSent → uncheck/prefs/Toast بعد از پایانِ کار")
if 'MANGA_SPEED_TEST' not in asrc or "ocr_speedtest_v" not in asrc:
    fail("P: manga_app سیمکشیِ MANGA_SPEED_TEST/ocr_speedtest_v ندارد")
elif ".then(" not in asrc or "outputs=[ocr_speedtest]" not in asrc:
    fail("P: خاموشیِ خودکارِ کلید (then→value=False) در manga_app نیست")
else:
    ok("P: PC = MANGA_SPEED_TEST + خاموشیِ خودکارِ Checkbox")

# ── ۳) E2E عملی در زیرپروسه ─────────────────────────────────────
# تصویرِ مصنوعی با جعبههایِ سفید (متنِ فرضی) — backendِ فیک تزریق
# میشود تا بدونِ مدلِ واقعی، همهٔ پنجرهها واقعاً لوپ شوند.
E2E = r'''
# -*- coding: utf-8 -*-
import io, json, os, sys, threading, time, types
import numpy as np, cv2

ROOT = os.environ["ROOT"]
ST_DIR = os.environ["ST_DIR"]
PER = float(os.environ.get("ST_PER", "0.12"))

src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()

# قطعه‌هایِ لازم با AST (بدونِ importِ کلِ manga.py)
import ast
tree = ast.parse(src)
picks = {}
wanted = ["speed_test_run", "_speed_test_pool", "_speed_test_window",
          "speed_test_load", "_speed_test_save", "_speed_test_path"]
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in wanted:
        picks[node.name] = ast.get_source_segment(src, node)
m = src.index("class K3LadderOCR:")
m2 = src.index("\nclass ", m + 10)
picks["K3LadderOCR"] = src[m:m2]

class FakeEng:
    """موتورِ فیک: fullpage = باکسها؛ کراپ = خروجیِ سبک + تأخیرِ واقعی"""
    def __init__(self, tag, delay=0.0):
        self.tag, self.delay = tag, delay
    def ocr(self, image, crop_mode=False, det_cap=None):
        if self.delay:
            t0 = time.time()
            while time.time() - t0 < self.delay:
                pass
        if not crop_mode:
            b1 = [[60, 60], [360, 60], [360, 180], [60, 180]]
            b2 = [[500, 200], [820, 200], [820, 340], [500, 340]]
            b3 = [[120, 700], [380, 700], [380, 810], [120, 810]]
            return [[b1, ("BOX", 0.9)], [b2, ("BOX", 0.9)],
                    [b3, ("BOX", 0.9)]]
        return [[[0, 0], [image.shape[1], 0],
                 [image.shape[1], image.shape[0]], [0, image.shape[0]]],
                ("t", 0.95)]

class FakeML:
    def ocr(self, image):
        return [[[0, 0], [image.shape[1], 0],
                 [image.shape[1], image.shape[0]], [0, image.shape[0]]],
                ("m", 0.8)]

class FakeMT:
    @staticmethod
    def _imread_any(p):
        return cv2.imread(p)

class FakeMlKit:
    """جایگزینِ MlKitCropOCR — _mlkit_backendِ واقعی (در قطعهٔ کلاس هست)
    این را میسازد تا پنجرههایِ mlkit/full/fast هم واقعاً اجرا شوند."""
    def __init__(self, lang="en"):
        self.lang = lang
    def ocr(self, image):
        return [[[0, 0], [image.shape[1], 0],
                 [image.shape[1], image.shape[0]], [0, image.shape[0]]],
                ("m", 0.8)]

# اجزایِ فیک برایِ exec — قبل از اجرایِ قطعه‌ها
g = {"os": os, "time": time, "json": json, "np": np, "cv2": cv2,
     "threading": threading, "print": print, "APP_VER": "1.14.178-test",
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
     "MlKitCropOCR": FakeMlKit, "RapidOCRBackend": object}
exec(compile("\n\n".join(picks.values()), "manga_bits", "exec"), g)

os.environ["MANGA_FILES_DIR"] = ST_DIR

# تصویرِ مصنوعی: ۳ جعبهٔ سفید رویِ سیاه = ۳ کراپ
img = np.zeros((1200, 900, 3), np.uint8)
for (x, y, w, h) in ((60, 60, 300, 120), (500, 200, 320, 140),
                     (120, 700, 260, 110)):
    img[y:y + h, x:x + w] = 255
cv2.imwrite(os.path.join(ST_DIR, "page.png"), img)

class FakeBE:
    def __init__(self, lang="en"):
        self.lang = lang
        self._mobile = g["K3LadderOCR"](
            FakeML(), lang,
            lambda small: FakeEng("sml" if small else "med",
                                  0.004 if small else 0.009))
    def _build_mobile_onnx(self, lang, small=False):
        return FakeEng("sml" if small else "med", 0.004 if small else 0.009)

lines = []
res = g["speed_test_run"](
    src=os.path.join(ST_DIR, "page.png"), langs=("en",), per_mode=PER,
    log=lines.append, backend=FakeBE())
stf = os.path.join(ST_DIR, "speed_test.json")
assert res and os.path.isfile(stf), "نتیجه/فایل نبود"
d = json.load(io.open(stf, encoding="utf-8"))
assert d.get("ladder") in ("full", "fast", "mlkit", "rapid", "paddle"), d
assert d.get("ep") in ("cpu", "xnnpack", "nnapi", "auto"), d
assert d.get("crops") == 3, d
assert not d.get("nnapi_pending"), d
modes = [k for k, v in d["ladder_ms"].items() if v]
assert set(modes) == {"full", "fast", "mlkit", "rapid", "paddle"}, d["ladder_ms"]
eps = [k for k, v in d["ep_ms"].items() if v]
assert {"cpu", "xnnpack"} <= set(eps) and "nnapi" in d["ep_ms"], d["ep_ms"]
tbl = [ln for ln in lines if "جدولِ روشها" in ln]
win = [ln for ln in lines if ln.startswith("[⚡] برنده")]
assert tbl and win, lines[-4:]
# ذخیرهٔ تدریجی: پنجرههایِ واقعی در لاگ با میانگین (NNAPIِ معلق رد
# میشود → ۷ پنجرهٔ اندازهگیری + ۱ ردشدگی)
wlines = [ln for ln in lines
          if ln.startswith("[⚡] (") and "میانگینِ" in ln]
assert len(wlines) == 7, wlines
skip_line = [ln for ln in lines if "رد شد" in ln and "NNAPI از دست رفت" in ln]
assert len(skip_line) == 1, skip_line
# speed_lab_envِ فایل‌محور
sle = ast.get_source_segment(src, next(
    n for n in ast.parse(src).body
    if isinstance(n, ast.FunctionDef) and n.name == "speed_lab_env"))
g2 = {"os": os, "json": json,
      "_K3_STATS": {"n": 5, "ms": 9.0, "st1": 1, "st2": 2, "st3": 3},
      "_MLKIT_STATS": {"ms": 4.0, "n": 2, "lines": 7},
      "_SPEED_LAB_EP": ("auto", "nnapi", "xnnpack", "cpu"),
      "_SPEED_LAB_LADDER": ("full", "fast", "mlkit", "rapid", "paddle"),
      "speed_test_load": g["speed_test_load"], "print": print}
exec(compile(sle, "sle", "exec"), g2)
banner = g2["speed_lab_env"]({"ocr_ep": "nnapi"})  # کلیدهایِ کهنه باید بیاثر باشند
assert "برندهٔ" in banner and d["ladder"] in banner, banner
assert os.environ.get("MANGA_K3_MODE") == \
    ("" if d["ladder"] == "full" else d["ladder"])
assert "MANGA_OCR_THREADS" not in os.environ, "کلیدِ کهنه پاک نشد"
# بدونِ نتیجه → پیشفرض + پاکسازی
os.remove(stf)
banner2 = g2["speed_lab_env"]({})
assert "پیشفرض" in banner2 and "MANGA_K3_MODE" not in os.environ, banner2
print("E2E_OK", json.dumps({"ladder": d["ladder"], "ep": d["ep"]},
                           ensure_ascii=False))
'''

# ۳-الف) E2E با backendِ فیک (همیشه اجرا میشود)
import tempfile  # noqa: E402
with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ)
    env["ROOT"] = ROOT
    env["ST_DIR"] = td
    env["ST_PER"] = "0.12"
    # نتیجهٔ کهنه با nnapi_pending → پنجرهٔ NNAPI باید رد شود
    io.open(os.path.join(td, "speed_test.json"), "w", encoding="utf-8").write(
        json.dumps({"ladder": "rapid", "ep": "cpu", "nnapi_pending": True}))
    r = subprocess.run([sys.executable, "-c", E2E], env=env,
                       capture_output=True, text=True, timeout=300)
    out = r.stdout + r.stderr
    if r.returncode != 0 or "E2E_OK" not in out:
        print(out[-3000:])
        fail("E2E: زیرپروسه شکست خورد")
    d = json.loads(out.split("E2E_OK", 1)[1].split("\n", 1)[0])
    ok("E2E: تستِ سرعت واقعی ۸ پنجره + برنده=%s/%s + ردِ NNAPIِ معلق"
       % (d["ladder"], d["ep"]))

# ── ۴) E2Eِ دروازهٔ main (MANGA_SPEED_TEST=1 قبل از چکِ کلید) ────
if "نردبان ندارد" not in src or "speed_test_run(src=args.input" not in src:
    fail("M: شاخهٔ MANGA_SPEED_TEST/main در manga.py ناقص است")
with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ)
    env["MANGA_SPEED_TEST"] = "1"
    env["MANGA_FILES_DIR"] = td
    r = subprocess.run(
        [sys.executable, MP, "-i", os.path.join(ROOT, "VERSION"),
         "-o", os.path.join(td, "out.png"), "--font", "x"],
        env=env, capture_output=True, text=True, timeout=300)
    out = r.stdout + r.stderr
    if "تستِ سرعتِ استخراج" not in out:
        print(out[-2500:])
        fail("M: main() با MANGA_SPEED_TEST واردِ تست نشد")
    # ورودی = فایلِ غیرتصویری → پیامِ «باز نشد» = واردِ speed_test_run شد
    if "باز نشد" not in out:
        print(out[-2500:])
        fail("M: speed_test_run اجرا نشد (ورودیِ غیرتصویری باید پیامِ بازنشده بدهد)")
    if "provider ناشناخته" in out or "کلید API لازم" in out:
        print(out[-2500:])
        fail("M: main() قبلِ از تست سراغِ اعتبارسنجیِ provider/کلید رفت")
    ok("M: main() زودتر از چکِ provider/کلید به تستِ سرعت میرود")

print()
print("[✓] همهٔ گیتهایِ v1.14.178 PASS")
