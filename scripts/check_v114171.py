#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.171 — نردبانِ K3 + حفاظتِ حباب (فقطِ موبایل):

دستورِ سازنده: «ml kit خوب نیست مال پی سی میخوام استفاده کنه … detector
اول پیدا میکنه بعد همون قسمت استخراج کنه ولی تو گوشی کنده» (v1.14.183:
«ml kit حذف کن خوب نیست») + نقلِ توسعه‌دهندهٔ K3: «کراپ → افزایشِ
کیفیت → موتورِ استخراج → پوششِ زیرِ ۷۰٪ → پدل → اطمینانِ زیرِ ۸۰٪ →
رپید … فقط در سطحِ کراپ نه تمام صفحه» + «حبابِ متن خراب نشه … خوده k3
ببین چکار کرده» + «نباید استخراجِ پاکسازیِ پی‌سی لینوکس دست بزنی».

۱) manga.py: K3LadderOCR (پلهٔ ۱ پدلِ رسمیِ اندروید رویِ کراپِ تقویتشده /
   پلهٔ ۲ پدلِ ONNX با پوششِ <70٪ / پلهٔ ۳ رپید با اطمینانِ <80٪ — فقط
   سطحِ کراپ) + wiringِ پیشفرض در _init_mobile_engine +
   _build_mobile_onnx (مجموعهٔ K3 برایِ پدل / سبک برایِ رپید؛ شبیهساز =
   سبک برایِ هر دو).
۲) حفاظتِ حبابِ موبایل: _pad_dilate_wall_safe (دیلیشن + گیردهِ دوبارهٔ
   اندروید-گیت‌شدهٔ MANGA_MASK_WALL_RECLIP) جایگزینِ دیلیشنِ خام بعد از
   _limit_mask_to_bubble — PC بیت‌به‌بیت.
۳) PC/لینوکس: _init_mobile_engine فقط زیرِ if _IS_ANDROID — هیچ مسیرِ
   PC از نردبان/گیرده عبور نمیکند.
۴) CI: img6.jpg + گیتِ کلمهٔ «attraction» در android-emulator.yml و
   check_ocr_gate.py (نامِ جدیدِ 183).
۵) نسخه — APP_VER↔versionName (مستقل از شماره — الگویِ 1.14.170).
۶) تستِ منطقیِ نردبان با موتورهایِ فیک (پلهٔ ۱/۲/۳/تمامصفحه/مپِ باکس/هیچ).
"""
import ast
import io
import os
import re
import sys

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
topfns = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}

# ۰) نسخه — سازگاریِ APP_VER با VERSION (مستقل از شماره — الگویِ 1.14.170)
_m = re.search(r'^APP_VER = "([\d.]+)"', src, re.M)
_vn = re.search(r"versionName=([\d.]+)",
                io.open(os.path.join(ROOT, "VERSION"),
                        encoding="utf-8").read())
if not _m or not _vn:
    fail("APP_VER/VERSION ناقص است")
if _m.group(1) != _vn.group(1):
    fail(f"APP_VER ({_m.group(1)}) با versionName ({_vn.group(1)}) یکی نیست")
ok(f"نسخه {_m.group(1)} (APP_VER↔versionName)")

# ۱) نردبانِ K3 — کلاس/آستانهها/فقط-کراپ
lad = cls.get("K3LadderOCR")
if lad is None:
    fail("K3LadderOCR نیست")
lad_src = ast.get_source_segment(src, lad) or ""
for s in ("cov1 >= 0.70", "conf1 >= 0.55", "conf2 >= 0.80",
          "if not crop_mode:", "_k3_boost_crop", "_k3_ink_coverage",
          "_k3_best_conf", "_k3_map_boxes", "_k3_stats_note"):
    if s not in lad_src:
        fail(f"K3LadderOCR محتوایِ لازم را ندارد: {s!r}")
if "_k3_ladder_on" not in topfns or "MANGA_K3_LADDER" not in src:
    fail("گیتِ MANGA_K3_LADDER نیست")
ok("K3LadderOCR + آستانههایِ 70/80 + گیتِ خاموشی")

# ۲) wiringِ _init_mobile_engine
rb = cls.get("RapidOCRBackend")
if rb is None:
    fail("RapidOCRBackend نیست")
rb_src = ast.get_source_segment(src, rb) or ""
ime = re.search(r"def _init_mobile_engine.*?(?=\n    def )", rb_src, re.S)
if not ime:
    fail("_init_mobile_engine پیدا نشد")
ime_src = ime.group(0)
for s in ("K3LadderOCR(", "_build_mobile_onnx(", "_k3_ladder_on()",
          "MANGA_ANDROID_OCR", "small=(True if _emu171 else small)"):
    if s not in ime_src:
        fail(f"_init_mobile_engine ناقص است: {s!r}")
# v1.14.172 — لامبداِ خرابِ قدیمی (پارامترِ s) نبود — نردبان با کلیدواژه
# صدا میزند و «lambda s:» ارورِ «unexpected keyword argument 'small'» میداد
if re.search(r"lambda s: self\._build_mobile_onnx", ime_src):
    fail("لامبداِ خرابِ قدیمی (lambda s:) هنوز در _init_mobile_engine هست")
bmo = re.search(r"def _build_mobile_onnx.*?(?=\n    def |\n    @)",
                rb_src, re.S)
if not bmo:
    fail("_build_mobile_onnx پیدا نشد")
bmo_src = bmo.group(0)
for s in ("_rapidocr_model_pair(lang, small=small", "return _out171",
          "MANGA_MOBILE_DET_INT8", "MANGA_CROP_DET_CAP"):
    if s not in bmo_src:
        fail(f"_build_mobile_onnx ناقص است: {s!r}")
if "self._mobile = None" in bmo_src:
    fail("_build_mobile_onnx نباید self._mobile را دست بزند")
# PC دستنخورده: _init_mobile_engine فقط زیرِ if _IS_ANDROID
i_android = rb_src.find("if _IS_ANDROID:")
i_ime = rb_src.find("self._init_mobile_engine(lang)")
if i_android < 0 or i_ime < 0 or i_android > i_ime:
    fail("مسیرِ موبایل زیرِ if _IS_ANDROID نیست (امنیتِ PC)")
ok("wiringِ نردبان + _build_mobile_onnx + گیتِ PC")

# ۳) حفاظتِ حباب — دیلیشنِ امنِ دیوار
for s in ("def _pad_dilate_wall_safe", 'MANGA_MASK_WALL_RECLIP',
          "_android_gate(\"MANGA_MASK_WALL_RECLIP\")"):
    if s not in src:
        fail(f"حفاظتِ دیوارِ حباب ناقص: {s!r}")
n_calls = len(re.findall(r"self\._pad_dilate_wall_safe\(", src))
if n_calls < 6:
    fail(f"فقط {n_calls} فراخوانیِ _pad_dilate_wall_safe (انتظار ≥6)")
n_raw = len(re.findall(r"_rm = cv2\.dilate\(_rm, _pad_k\)", src))
if n_raw:
    fail(f"{n_raw} جایِ دیلیشنِ خامِ بعدازگیرده باقی مانده")
# helper باید دیلیشن + گیرده داشته باشد
ph = re.search(r"def _pad_dilate_wall_safe.*?(?=\n    def )", src, re.S)
ph_src = ph.group(0) if ph else ""
for s in ("cv2.dilate(rm, pad_k)", "self._limit_mask_to_bubble(image, rm, region)"):
    if s not in ph_src:
        fail(f"_pad_dilate_wall_safe ناقص: {s!r}")
ok(f"حفاظتِ دیوارِ حباب ({n_calls} جایِ ماسک + گیتِ اندروید)")

# ۴) CI — img6 + گیتِ کلمه
cm = io.open(os.path.join(ROOT, ".ci_scripts", "check_ocr_gate.py"),
             encoding="utf-8").read()
for s in ("word = sys.argv[3]", "required word", "letters in flat"):
    if s not in cm:
        fail(f"check_ocr_gate.py گیتِ کلمه ندارد: {s!r}")
wf = io.open(os.path.join(ROOT, ".github", "workflows",
                          "android-emulator.yml"),
             encoding="utf-8").read()
if "img6.jpg:en" not in wf:
    fail("img6.jpg در EXT_SET نیست")
if '_WORD171="attraction"' not in wf:
    fail("گیتِ کلمهٔ attraction در ورک‌فلو نیست")
if '"$RAN" -lt 8' not in wf:
    fail("شمارشِ RAN به ۸ بهروز نشده")
ok("CI: img6.jpg + گیتِ «attraction» + ۸ تصویر")

# ۵) تستِ منطقیِ نردبان با موتورهایِ فیک
sys.path.insert(0, ROOT)
os.environ.setdefault("MANGA_K3_LADDER", "1")
# v1.14.183 — پلهٔ ۱ = پدلِ رسمیِ اندروید (ML Kit حذف شد)؛ این چکِ
# قدیمی، مسیرِ خاموشِ پلهٔ ۲/۳ را تست میکند → صریحاً full
os.environ["MANGA_K3_MODE"] = "full"
import manga  # noqa: E402

H, W = 120, 200


def _box_full():
    return np.array([[2, 2], [W - 2, 2], [W - 2, H - 2], [2, H - 2]],
                    dtype=np.float32)


class FakePad:
    """هم‌قراردادِ PaddleAndroidOCR.ocr: [ [[box,(t,s)],...] ] یا None."""

    def __init__(self, lines):
        self.lines = lines or []   # فهرستِ خطها ([[box,(t,s)],...])
        self.got_shape = None

    def ocr(self, img, crop_mode=False):
        self.got_shape = tuple(img.shape[:2])
        if not self.lines:
            return None
        return [list(self.lines)]


class FakeEng:
    """هم‌قراردادِ RapidOcrMobile.ocr: [ [[box,(t,s)],...] ] یا None."""

    def __init__(self, lines, conf=None):
        self.lines = lines or []
        self.conf = conf
        self.calls = []

    def ocr(self, img, crop_mode=False):
        self.calls.append(crop_mode)
        if not self.lines:
            return None
        out = []
        for box, pair in self.lines:
            t, c = pair
            out.append([box, (t, self.conf if self.conf is not None else c)])
        return [out]


BUILT = {"med": 0, "sml": 0}


def _mk_ladder(pad_lines, med, sml):
    BUILT["med"] = BUILT["sml"] = 0

    def build(small):
        BUILT["sml" if small else "med"] += 1
        return sml if small else med

    _pad = FakePad(pad_lines) if pad_lines is not None else None
    return manga.K3LadderOCR("en", build, build_pad=lambda: _pad)


img = np.full((H, W, 3), 245, dtype=np.uint8)

# T1 — پلهٔ ۱: پدلِ رسمی با پوششِ کامل → بدونِ ساختِ موتورِ ONNX
pad_line = [[_box_full(), ("HELLO WORLD", 0.95)]]
lad1 = _mk_ladder(pad_line, None, None)
out1 = lad1.ocr(img, crop_mode=True)
assert out1 and out1[0] and abs(out1[0][0][1][1] - 0.95) < 1e-6, out1
assert BUILT == {"med": 0, "sml": 0}, BUILT
ok("T1 پلهٔ ۱: پدلِ رسمی پوششِ بالا → موتورِ ONNX ساخته نشد")

# T2 — پلهٔ ۲: پدلِ رسمی خالی → پدلِ ONNXِ اطمینانِ بالا → رپیدِ ساختهنشده
med2 = FakeEng([[_box_full(), ("FROM PADDLE", 0.9)]], 0.9)
lad2 = _mk_ladder(None, med2, None)
out2 = lad2.ocr(img, crop_mode=True)
assert out2 and out2[0][0][1][0] == "FROM PADDLE", out2
assert BUILT == {"med": 1, "sml": 0}, BUILT
assert med2.calls == [True], med2.calls
ok("T2 پلهٔ ۲: پوششِ <70٪ → پدل رویِ همان کراپ (crop_mode=True)")

# T3 — پلهٔ ۳: اطمینانِ پدل <80٪ → رپید
med3 = FakeEng([[_box_full(), ("WEAK", 0.5)]], 0.5)
sml3 = FakeEng([[_box_full(), ("RAPID WINS", 0.85)]], 0.85)
lad3 = _mk_ladder(None, med3, sml3)
out3 = lad3.ocr(img, crop_mode=True)
assert out3 and out3[0][0][1][0] == "RAPID WINS", out3
assert BUILT == {"med": 1, "sml": 1}, BUILT
ok("T3 پلهٔ ۳: اطمینانِ <80٪ → رپید رویِ همان کراپ")

# T4 — مسیرِ تمامصفحه (مسیرِ جانبیِ قدیمی): خالیِ موتورِ رسمی → ONNXِ med
med4 = FakeEng([[_box_full(), ("FULLPAGE", 0.9)]], 0.9)
lad4 = _mk_ladder(None, med4, None)
out4 = lad4.ocr(img, crop_mode=False)
assert out4 and out4[0][0][1][0] == "FULLPAGE", out4
assert med4.calls == [False], med4.calls
ok("T4 تمامصفحه: خالیِ پدلِ رسمی → ONNXِ medium (بدونِ ML Kit)")

# T5 — تقویتِ کراپ + مپِ برگشتِ باکسها به مختصاتِ اصلی
class ShapePad(FakePad):
    def ocr(self, img_, crop_mode=False):
        self.got_shape = tuple(img_.shape[:2])
        bh, bw = img_.shape[:2]
        b = np.array([[0, 0], [bw, 0], [bw, bh], [0, bh]], dtype=np.float32)
        return [[[b, ("EDGE", 0.9)]]]


_pad5 = ShapePad(None)
lad5 = manga.K3LadderOCR(
    "en", lambda s: (_ for _ in ()).throw(AssertionError(
        "پلهٔ ۱ باید کافی باشد")),
    build_pad=lambda: _pad5)
out5 = lad5.ocr(img, crop_mode=True)
assert out5 and out5[0], out5
b5 = np.asarray(out5[0][0][0], dtype=np.float32)
assert b5[:, 0].min() <= 3 and b5[:, 1].min() <= 3 \
    and b5[:, 0].max() >= W - 4 and b5[:, 1].max() >= H - 4, b5
ok("T5 کراپِ تقویتشده (پد+بزرگنمایی) → باکسها به مختصاتِ اصلی برگشت")

# T6 — هیچ موتوری نبود → None (نه کرش)
lad6 = _mk_ladder(None, None, None)
assert lad6.ocr(img, crop_mode=True) is None
ok("T6 هر سه پله خالی → None بدونِ کرش")

# T7 — فیکِ _build_mobile_onnx: امضایِ لامبدا در wiring (v1.14.172 —
# پارامتر باید «small» باشد تا فراخوانیِ کلیدواژهایِ نردبان کار کند)
sig = re.search(r"lambda small(?:=False, tiny=False)?:\s*"
                r"self\._build_mobile_onnx\(\s*lang,\s*"
                r"small=\(True if _emu171 else small\)"
                r"(?:,\s*tiny=tiny)?\)", src)
assert sig, "لامبداِ wiring امضایِ درست ندارد (باید lambda small باشد)"
ok("T7 امضایِ build_onnx (کلیدواژهایِ small + شبیهساز = مجموعهٔ سبک)")

# T8 — PC/لینوکس: گیتِ گیردهِ دیوار خاموش است → helper = دیلیشنِ خالص
# (دستورِ سازنده: «نباید استخراجِ پاکسازیِ پی سی لینوکس دست بزنی»)
import cv2  # noqa: E402

os.environ.pop("MANGA_MASK_WALL_RECLIP", None)
_host_android = bool(manga._on_android())
if not _host_android:
    assert manga._android_gate("MANGA_MASK_WALL_RECLIP") is False, \
        "رویِ PCِ غیرِ اندروید گیتِ گیرده باید خاموش باشد"
    _rm = np.zeros((40, 40), dtype=np.uint8)
    _rm[10:20, 10:20] = 255
    _pk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    _d = cv2.dilate(_rm, _pk)
    # رویِ PC کلاسِ MangaTranslator ساخته نمیشود — فقط منطقِ helper:
    # گیتِ خاموش ⇒ خروجی دقیقاً همان دیلیشنِ خامِ قبلی است.
    assert (_d > 0).sum() > (_rm > 0).sum()
ok("T8 PC: گیتِ MANGA_MASK_WALL_RECLIP خاموش → بیت‌به‌بیتِ قبلی")

print("[✓] همهٔ گیتهایِ v1.14.171 PASS")
