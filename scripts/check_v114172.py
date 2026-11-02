#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.172 — فیکسِ «پدل/رپید آماده نشد»ٔ گوشی + DEBUGِ
جداگانهٔ detector:

لاگِ واقعیِ گوشی (v1.14.171): «[!] مدلِ پدل آماده نشد:
RapidOCRBackend._init_mobile_engine.<locals>.<lambda>() got an unexpected
keyword argument 'small'» + همین برایِ رپید → نردبانِ K3 عملاً فقط
پلهٔ ۱ بود (پلهها: پله۱=20 پدل=0 رپید=0؛ در آن زمان ML Kit) و متنِ
ضعیفِ پلهٔ ۱ («Youre attractien nere.») بدونِ پلهٔ ۲ برگشت.

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
# v1.14.184 — wiring بدونِ لامبدا: مستقیمِ SDKِ رسمی
if "lambda small" in ime_src or "_build_mobile_onnx" in ime_src:
    fail("wiringِ قدیمی (lambda/_build_mobile_onnx) هنوز در _init_mobile_engine است")
if "_build_paddle_android(lang)" not in ime_src:
    fail("_init_mobile_engine باید _build_paddle_android را صدا بزند")
ok("wiringِ 184 = SDKِ رسمیِ اندروید (بدونِ لامبدا/ONNX)")

# ۲) تستِ عملی — build_onnx هرگز صدا نمیشود؛ فقط SDKِ رسمی
sys.path.insert(0, ROOT)
os.environ["MANGA_K3_MODE"] = "padandroid"
import manga  # noqa: E402

H, W = 120, 200
img = np.full((H, W, 3), 245, dtype=np.uint8)


def _box_full():
    return np.array([[2, 2], [W - 2, 2], [W - 2, H - 2], [2, H - 2]],
                    dtype=np.float32)


class FakePad:
    """هم‌قراردادِ PaddleAndroidOCR (پلهٔ ۱ = پدلِ رسمی — v1.14.183)."""

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


class _Forbidden:
    def __call__(self, *a, **k):
        raise AssertionError("موتورِ ONNXِ گوشی باید هرگز ساخته نمیشود")


_forbidden = _Forbidden()
pad_ok = FakePad([[_box_full(), ("FROM OFFICIAL", 0.9)]])
lad = manga.K3LadderOCR("en", _forbidden, build_pad=lambda: pad_ok)
out = lad.ocr(img, crop_mode=True)
assert out and out[0][0][1][0] == "FROM OFFICIAL", out
outf = lad.ocr(img, crop_mode=False)
assert outf and outf[0][0][1][0] == "FROM OFFICIAL", outf
pad_none = FakePad(None)
lad2 = manga.K3LadderOCR("en", _forbidden, build_pad=lambda: pad_none)
assert lad2.ocr(img, crop_mode=True) is None
ok("تکپلهٔ 184: SDKِ رسمی جواب میدهد؛ خالی = None؛ build_onnx هرگز صدا نشد")

# ۳) DEBUGِ detector — v1.14.173: دیگر فایلِ جدا نیست؛ باکسهایِ خامِ
# detector رویِ همان DEBUGِ صفحه با سبز کشیده میشوند (دستورِ سازنده:
# «عکس جدا نشون نده رو همون عکس اصلی دیباگ بزاره با یک رنگ دیگ سبز»)
for gone in ("def _save_det_debug", "_DET_TLS = threading.local()",
             "self._dbg_cache_dir = cache_dir",
             '_DET_TLS.base = os.path.splitext(basename)[0]'):
    if gone in src:
        fail(f"مکانیزمِ قدیمیِ عکسِ جدا حذف نشده: {gone!r}")
dd = cls.get("MangaTranslator")
dd_src = ast.get_source_segment(src, dd) or ""
erb = re.search(r"def _extract_regions_from_bubbles.*?(?=\n    def )",
                dd_src, re.S)
if not erb:
    fail("_extract_regions_from_bubbles پیدا نشد")
erb_src = erb.group(0)
for s in ("_raw_det_dbg", "det_raw = _raw_det_dbg", "if self.debug:"):
    if s not in erb_src:
        fail(f"استفادهٔ det_raw در استخراج ناقص است: {s!r}")
# سبز باید داخلِ _draw_debug_regions باشد (نقطهٔ واحد — هم استخراج
# هم clean-only که خودش دوباره صدا میزند)
ddr = re.search(r"def _draw_debug_regions.*?(?=\n    @|\n    def )",
                dd_src, re.S)
if not ddr:
    fail("_draw_debug_regions پیدا نشد")
ddr_src = ddr.group(0)
for s in ("det_raw", "(0, 255, 0)", 'f"D{_di:02d} {_dcls}"', "cv2.rectangle"):
    if s not in ddr_src:
        fail(f"پوششِ سبزِ detector در _draw_debug_regions ناقص است: {s!r}")
i_green = ddr_src.find("det_raw")
i_ret = ddr_src.rfind("return vis")
if i_green < 0 or i_ret < 0 or i_green > i_ret:
    fail("پوششِ سبز باید قبل از return vis در _draw_debug_regions باشد")
ok("DEBUGِ detector = سبز رویِ همان DEBUGِ صفحه (بدونِ فایلِ جدا)")

# ۳-ب) تستِ عملیِ پوششِ سبز رویِ خروجیِ _draw_debug_regions
import cv2  # noqa: E402


class _FR:
    """ناحیهٔ فیک با هم قراردادِ TextRegion برایِ رسمِ دیباگ."""

    def __init__(self, rid, det_raw=None):
        self.id = rid
        self.rect = (10, 10, 80, 50)
        self.kind = "dialogue"
        self.source_text = "HELLO"
        self.translated_text = ""
        if det_raw is not None:
            self.det_raw = det_raw


_raw = [([5, 5, 90, 60], "dialogue")]
_vis = manga.MangaTranslator._draw_debug_regions(None, img.copy(),
                                                 [_FR(0, _raw)])
# سبزِ خالص (0،255،0) باید در تصویر باشد (باکسِ D00)
_green = int(((_vis[:, :, 1] > 240) & (_vis[:, :, 0] < 40)
              & (_vis[:, :, 2] < 40)).sum())
assert _green > 50, f"پیکسلِ سبزِ detector نیست: {_green}"
# بدونِ det_raw → بدونِ سبزِ D (فقط سبزِ متنِ کوتاهِ (0،200،0) که
# فیلترِ بالا آن را نمیگیرد)
_vis2 = manga.MangaTranslator._draw_debug_regions(None, img.copy(),
                                                  [_FR(1)])
_green2 = int(((_vis2[:, :, 1] > 240) & (_vis2[:, :, 0] < 40)
               & (_vis2[:, :, 2] < 40)).sum())
assert _green2 == 0, f"بدونِ det_raw نباید سبزِ detector باشد: {_green2}"
ok("عملیِ پوششِ سبز: با det_raw سبزِ D رسم میشود؛ بدونِ آن نه")

# ۴) تکپلهٔ 184 — تقویتِ کراپ → SDKِ رسمی → بازگشت
lad = cls.get("K3LadderOCR")
lad_src = ast.get_source_segment(src, lad) or ""
for s in ("_k3_boost_crop(image_bgr)", "_k3_map_boxes(r0[0], pad, scale)",
          "if not crop_mode:", '_K3_MODES = ("padandroid",)'):
    if s not in lad_src:
        fail(f"نردبانِ 184 تغییر کرده: {s!r}")
ok("تکپلهٔ 184 (تقویت → SDKِ رسمی → بازگشت) سرِ جایش")

print("[✓] همهٔ گیتهایِ v1.14.172 PASS")
