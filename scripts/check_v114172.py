#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.172 — فیکسِ «پدل/رپید آماده نشد»ٔ گوشی + DEBUGِ
جداگانهٔ detector:

لاگِ واقعیِ گوشی (v1.14.171): «[!] مدلِ پدل آماده نشد:
RapidOCRBackend._init_mobile_engine.<locals>.<lambda>() got an unexpected
keyword argument 'small'» + همین برایِ رپید → نردبانِ K3 عملاً فقط
ML Kit بود (پلهها: ML Kit=20 پدل=0 رپید=0) و متنِ ضعیفِ ML Kit
(«Youre attractien nere.») بدونِ پلهٔ ۲ برگشت.

درخواستِ سازنده: «detector-v4-s_int8.onnx جدا نشون بده تو عکس ببینم
detector نتونسته استخراج کنه یا ocr و ارور داد».

۱) لامبداِ wiring: پارامتر باید «small» باشد (فراخوانیِ کلیدواژهایِ
   نردبان: _build_onnx(small=True/False)) — نبودِ «lambda s:» در
   _init_mobile_engine.
۲) تستِ عملیِ builderِ فقط-کلیدواژهای (def build(*, small)) — با باگِ
   قدیمی کرش میکند.
۳) DEBUGِ جداگانهٔ detector: _save_det_debug (باکسهایِ خام قبلِ هر
   فیلتری، رویِ کپی، <صفحه>_det.jpg در debug<tag>) + call-site قبلِ
   حذفِ تودرتو + _DET_TLS + self._dbg_cache_dir/_tag. فقط debug=True —
   هیچ اثری رویِ استخراج/پاکسازیِ PC و اندروید.
۴) نسخه — APP_VER↔versionName.
"""
import ast
import io
import os
import re
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fail(msg):
    print("[✗]", msg)
    sys.exit(1)


def ok(msg):
    print("[✓]", msg)


src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
tree = ast.parse(src)
cls = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}

# ۰) نسخه
_m = re.search(r'^APP_VER = "([\d.]+)"', src, re.M)
_vn = re.search(r"versionName=([\d.]+)",
                io.open(os.path.join(ROOT, "VERSION"),
                        encoding="utf-8").read())
if not _m or not _vn:
    fail("APP_VER/VERSION ناقص است")
if _m.group(1) != _vn.group(1):
    fail(f"APP_VER ({_m.group(1)}) با versionName ({_vn.group(1)}) یکی نیست")
ok(f"نسخه {_m.group(1)} (APP_VER↔versionName)")

# ۱) لامبداِ wiring — امضایِ درست + نبودِ خراب
rb = cls.get("RapidOCRBackend")
if rb is None:
    fail("RapidOCRBackend نیست")
rb_src = ast.get_source_segment(src, rb) or ""
ime = re.search(r"def _init_mobile_engine.*?(?=\n    def )", rb_src, re.S)
if not ime:
    fail("_init_mobile_engine پیدا نشد")
ime_src = ime.group(0)
if not re.search(r"lambda small: self\._build_mobile_onnx\(\s*lang, "
                 r"small=\(True if _emu171 else small\)\)", ime_src):
    fail("لامبداِ wiring باید lambda small: با کلیدواژهٔ small باشد")
if re.search(r"lambda s: self\._build_mobile_onnx", ime_src):
    fail("لامبداِ خرابِ قدیمی (lambda s:) هنوز هست")
ok("لامبداِ wiring = lambda small: (کلیدواژهایِ نردبان)")

# ۲) تستِ عملی — builderِ فقط-کلیدواژهای (دقیقاً مثلِ صدای واقعیِ نردبان)
sys.path.insert(0, ROOT)
os.environ.setdefault("MANGA_K3_LADDER", "1")
import manga  # noqa: E402

H, W = 120, 200
img = np.full((H, W, 3), 245, dtype=np.uint8)


def _box_full():
    return np.array([[2, 2], [W - 2, 2], [W - 2, H - 2], [2, H - 2]],
                    dtype=np.float32)


class FakeMlkit:
    def __init__(self, lines):
        self.lines = lines or []

    def ocr(self, img_, crop_mode=False):
        if not self.lines:
            return None
        return [list(self.lines)]


class FakeEng:
    def __init__(self, text, conf):
        self.text, self.conf = text, conf
        self.calls = []

    def ocr(self, img_, crop_mode=False):
        self.calls.append(crop_mode)
        # قراردادِ RapidOcrMobile: [ [[box,(t,c)], ...] ]
        return [[[_box_full(), (self.text, self.conf)]]]


BUILT = {"med": 0, "sml": 0}
med = FakeEng("FROM PADDLE", 0.9)
sml = FakeEng("FROM RAPID", 0.85)


def build_kw(*, small):
    """فقط-کلیدواژهای — با «lambda s:»ٔ قدیمی = TypeError."""
    BUILT["sml" if small else "med"] += 1
    return sml if small else med


# ۲-الف) پلهٔ ۲: ML Kit خالی → پدل باید با کلیدواژه ساخته شود
BUILT["med"] = BUILT["sml"] = 0
lad2 = manga.K3LadderOCR(FakeMlkit(None), "en", build_kw)
out2 = lad2.ocr(img, crop_mode=True)
assert out2 and out2[0][0][1][0] == "FROM PADDLE", out2
assert BUILT == {"med": 1, "sml": 0}, BUILT
assert med.calls == [True], med.calls
ok("پلهٔ ۲: builderِ فقط-کلیدواژهای → پدل ساخته شد (باگِ 171 کرش میکرد)")

# ۲-ب) پلهٔ ۳: اطمینانِ پدل <80٪ → رپید
BUILT["med"] = BUILT["sml"] = 0
med_weak = FakeEng("WEAK", 0.5)
sml2 = FakeEng("RAPID WINS", 0.85)


def build_kw2(*, small):
    BUILT["sml" if small else "med"] += 1
    return sml2 if small else med_weak


lad3 = manga.K3LadderOCR(FakeMlkit(None), "en", build_kw2)
out3 = lad3.ocr(img, crop_mode=True)
assert out3 and out3[0][0][1][0] == "RAPID WINS", out3
assert BUILT == {"med": 1, "sml": 1}, BUILT
ok("پلهٔ ۳: اطمینانِ <80٪ → رپید با کلیدواژهٔ small ساخته شد")

# ۲-ج) فراخوانیِ مستقیمِ _engine با کلیدواژه (هر دو پله)
BUILT["med"] = BUILT["sml"] = 0
lad4 = manga.K3LadderOCR(FakeMlkit(None), "en", build_kw)
e_med = lad4._engine(small=False)
e_sml = lad4._engine(small=True)
assert e_med is med and e_sml is sml and BUILT == {"med": 1, "sml": 1}, BUILT
ok("_engine(small=False/True) با کلیدواژه ✓")

# ۳) DEBUGِ جداگانهٔ detector
if "def _save_det_debug" not in src or "_DET_TLS = threading.local()" not in src:
    fail("_save_det_debug/_DET_TLS نیست")
dd = cls.get("MangaTranslator")
dd_src = ast.get_source_segment(src, dd) or ""
sd = re.search(r"def _save_det_debug.*?(?=\n    def )", dd_src, re.S)
if not sd:
    fail("_save_det_debug پیدا نشد")
sd_src = sd.group(0)
for s in ("image.copy()", "_dbg_cache_dir", "_dbg_cache_tag",
          "_DET_TLS", '_det.jpg"', "self._write_image(vis, _p)"):
    if s not in sd_src:
        fail(f"_save_det_debug ناقص است: {s!r}")
# call-site: قبلِ حذفِ تودرتو (باکسهایِ خام) و فقط زیرِ self.debug
i_call = src.find("self._save_det_debug(image, boxes)")
i_drop = src.find("boxes = self._drop_contained_boxes(boxes, contain_thresh=0.72)")
if i_call < 0 or i_drop < 0 or i_call > i_drop:
    fail("call-siteِ _save_det_debug باید قبلِ حذفِ تودرتو باشد (باکسِ خام)")
_seg = src[max(0, i_call - 220):i_call]
if "if self.debug:" not in _seg:
    fail("_save_det_debug باید فقط زیرِ self.debug صدا زده شود")
# TLS base + مقصد در پروسهٔ اصلی
if "_DET_TLS.base = os.path.splitext(basename)[0]" not in src:
    fail("_DET_TLS.base در _extract_one ست نمیشود")
if "self._dbg_cache_dir = cache_dir" not in src \
        or "self._dbg_cache_tag = cache_tag" not in src:
    fail("self._dbg_cache_dir/_tag در پروسهٔ اصلی ست نمیشود")
ok("DEBUGِ detector: باکسِ خام، زیرِ debug، TLS + مقصدِ cache")

# ۳-ب) تستِ عملیِ _save_det_debug با fake-self (مسیر/نام/عدمِ تغییرِ اصل)
import cv2  # noqa: E402

SAVED = []
_tmpd = tempfile.mkdtemp(prefix="det_dbg_")


class _FakeSelf:
    _dbg_cache_dir = _tmpd
    _dbg_cache_tag = "_safe_v3"

    def _write_image(self, im, p):
        SAVED.append(p)
        cv2.imwrite(p, im)


_probe = img.copy()
manga._DET_TLS.base = "pick_test_01"
try:
    manga.MangaTranslator._save_det_debug(
        _FakeSelf(), _probe,
        [{"rect": [5, 5, 90, 60], "class_name": "dialogue"}])
finally:
    manga._DET_TLS.base = ""
assert len(SAVED) == 1 and SAVED[0].endswith(
    os.path.join("debug_safe_v3", "pick_test_01_det.jpg")), SAVED
assert os.path.isfile(SAVED[0]) and os.path.getsize(SAVED[0]) > 0
# تصویرِ اصلی نباید دست خورده باشد (رویِ کپی کشیده میشود)
assert (_probe == img).all(), "_save_det_debug تصویرِ اصلی را تغییر داد"
ok("عملیِ det-debug: <صفحه>_det.jpg در debug_safe_v3 + تصویرِ اصل دست‌نخورده")

# ۴) نردبانِ 171 سرِ جایش (آستانهها + فقط-کراپ)
lad = cls.get("K3LadderOCR")
lad_src = ast.get_source_segment(src, lad) or ""
for s in ("cov1 >= 0.70", "conf1 >= 0.55", "conf2 >= 0.80", "if not crop_mode:"):
    if s not in lad_src:
        fail(f"نردبانِ K3 تغییر کرده: {s!r}")
ok("آستانههایِ نردبانِ K3 (70/80/55) دستنخورده")

print("[✓] همهٔ گیتهایِ v1.14.172 PASS")
