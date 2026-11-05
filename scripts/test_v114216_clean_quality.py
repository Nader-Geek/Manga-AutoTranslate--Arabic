#!/usr/bin/env python3
"""v1.14.216 — تستِ بهبودهایِ پاکسازی (لکه/کوه/متنِ جامانده).

دستورهای سازنده: «خوب کار کن لگع سفید لگع متن قبلی دیده نشه … بعد تو
جای متن قبلی پاک شده انگار رو هم پیاده شده مثل کوه دیده میشه».

تستها:
 ۱) نسخه = 1.14.216
 ۲) گاردِ گرادیان در _color_fill_cluster: حلقهٔ گرادیانی → None (برو به
    LaMa)؛ حلقهٔ تختِ اشباع → همان TELEA (رفتارِ قبل)
 ۳) پرِ صفحهٔ گرادیانی در _line_instant_fill: پالی رویِ گرادیانِ آرام با
    صفحه پر میشود (خطایِ میانه < ۴ واحد)، نه رنگِ تخت
 ۴) نجاتِ خطِ یتیم: خطِ بی‌صاحبِ زیرِ ناحیه → ناحیهٔ جدید؛ لایهٔ نازکِ
    «YAA» (کمتر از ۶ حرف) رد؛ کاندیدای پوشیده رد
 ۵) گپِ گروهِ LaMa برایِ نوارِ بلند = ۲۲۰ (زنجیرهٔ پنجرهها یک پچ)
 ۶) کامپایل
"""
import os, sys, subprocess, tempfile

os.environ.setdefault("MANGA_FILES_DIR", "/tmp/v213/wrk")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import importlib.util
import numpy as np
import cv2

spec = importlib.util.spec_from_file_location(
    "manga_mod", os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "manga.py"))
manga = importlib.util.module_from_spec(spec)
sys.modules["manga_mod"] = manga
spec.loader.exec_module(manga)

PASS, FAIL = [], []


def gate(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  [✓] " if cond else "  [✗] ") + name + (f" — {detail}" if detail else ""))


print("== A) نسخه ==")
gate("A1: APP_VER = 1.14.216", manga.APP_VER == "1.14.216", manga.APP_VER)

print("== B) گاردِ گرادیان در _color_fill_cluster ==")
# تصویرِ گرادیانیِ آبیِ اشباع + ماسکِ خطِ متن
img = np.zeros((120, 300, 3), np.uint8)
for y in range(120):
    img[y, :] = (200 - y, 120, 40)   # گرادیانِ آبیِ تند
msk = np.zeros((120, 300), np.uint8)
msk[45:75, 40:260] = 255
r = manga.MangaTranslator._color_fill_cluster(img, msk)
gate("B1: حلقهٔ گرادیانی → None (به LaMa میرود)", r is None)
# رنگِ تختِ اشباع (بدون گرادیان) → همان TELEA
img2 = np.zeros((120, 300, 3), np.uint8)
img2[:, :] = (200, 120, 40)
r2 = manga.MangaTranslator._color_fill_cluster(img2, msk)
gate("B2: حلقهٔ تختِ اشباع → TELEA باقی (رفتارِ قبل)", r2 is not None)

print("== C) پرِ صفحهٔ گرادیانی در _line_instant_fill ==")
tr = manga.MangaTranslator.__new__(manga.MangaTranslator)
tr.debug = True
tr.font_path = None
tr._clean_level = lambda: "normal"
# متنِ تیره رویِ «گرادیانِ آرامِ تندتر» (شیبِ ۰.۵/px) — حلقهٔ تنگ یکدست
# از آب میآید (dev≤۱۵) ولی شیبِ داخلِ پالی معنادار است (≥۸) → پرِ صفحه
img3 = np.zeros((200, 300, 3), np.uint8)
for y in range(200):
    img3[y, :] = (200 - int(y * 0.5), 130, 60)
cv2.putText(img3, "HELLO WORLD", (40, 100), 0, 0.7, (10, 10, 10), 2)
# پالیِ تنگ دورِ جوهر (از bbox جوهر + ۳px)
_g = cv2.cvtColor(img3, cv2.COLOR_BGR2GRAY)
_ink = (_g < 100)
_ys, _xs = np.nonzero(_ink[60:120, 20:280])
_y0, _y1 = 60 + _ys.min() - 3, 60 + _ys.max() + 3
_x0, _x1 = 20 + _xs.min() - 3, 20 + _xs.max() + 3
poly = np.array([[_x0, _y0], [_x1, _y0], [_x1, _y1], [_x0, _y1]], np.float32)


class _R:
    pass


reg = _R()
reg.id = 1
reg.kind = "dialogue"
reg.ocr_polys = [poly]
cleaned = img3.copy()
n = tr._line_instant_fill(img3, cleaned, [reg], np.zeros((200, 300), np.uint8))
gate("C1: پرِ فوری گرفته شد", n >= 1, f"n={n}")
# پر باید «صفحه» باشد: شیبِ گرادیان (۰.۵/px در کانالِ B) در ناحیهٔ پرشده حفظ شود
_bc = cleaned[:, :, 0].astype(np.float32)
_mid = _bc[_y0 + 3:_y1 - 3, _x0 + 10:_x1 - 10]
_top = float(_mid[:3].mean())
_bot = float(_mid[-3:].mean())
_drop = _bot - _top
_exp = -0.5 * (_y1 - _y0 - 6)
gate("C2: پر با «صفحه» است نه تخت (شیبِ گرادیان حفظ)",
     abs(_drop - _exp) <= 3.0, f"drop={_drop:.1f} expected={_exp:.1f}")

print("== D) نجاتِ خطِ یتیم ==")


class _FakeOCR:
    pass


tr.ocr = _FakeOCR()
tr._clean_level = lambda: "normal"

TXT_MOCK = {"txt": "OUTER GOD WITHIN 7 YEARS.]"}


def _fake_ocr_crop(self, image, rect):
    return (TXT_MOCK["txt"], [np.array(
        [[rect[0] + 6, rect[1] + 4], [rect[2] - 6, rect[1] + 4],
         [rect[2] - 6, rect[3] - 4], [rect[0] + 6, rect[3] - 4]],
        np.float32)])


tr._ocr_crop = _fake_ocr_crop.__get__(tr)

# تصویر: والد (مستطیلِ ناحیه) + خطِ یتیمِ «سفید رویِ تیره» زیرِ آن
img4 = np.full((300, 400, 3), 60, np.uint8)
cv2.putText(img4, "ORPHAN LINE TEXT", (50, 140), 0, 0.8, (240, 240, 240), 2)
parent = manga.TextRegion(
    id=1, boxes=[np.array([[50, 40], [350, 40], [350, 70], [50, 70]])],
    source_text="PARENT LINE TEXT", rect=(50, 40, 300, 30),
    kind="dialogue",
    ocr_polys=[np.array([[50, 40], [350, 40], [350, 70], [50, 70]], np.float32)])
out = tr._rescue_orphan_lines(img4, [parent])
gate("D1: خطِ یتیم نجات یافت", len(out) == 2, f"n={len(out)}")
if len(out) == 2:
    gate("D2: متنِ نجاتیده از OCRِ همان خط میآید",
         "OUTER GOD" in out[1].source_text.upper(), out[1].source_text[:40])

# لایهٔ نازکِ کم‌حرف («YAA») رد میشود
TXT_MOCK["txt"] = "YAA"
out2 = tr._rescue_orphan_lines(img4, [parent])
gate("D3: لایهٔ «YAA» (کمتر از ۶ حرف) رد", len(out2) == 1)

# کاندیدای پوشیده (≥۷۰٪ داخلِ ناحیهٔ موجود) رد
TXT_MOCK["txt"] = "SOME VALID LONGER TEXT LINE HERE"
img5 = np.full((300, 400, 3), 150, np.uint8)
cv2.putText(img5, "LINE ONE TEXT", (50, 60), 0, 0.8, (40, 40, 40), 2)
cv2.putText(img5, "LINE TWO TEXT", (50, 95), 0, 0.8, (40, 40, 40), 2)
big = manga.TextRegion(
    id=1, boxes=[np.array([[40, 40], [360, 40], [360, 110], [40, 110]])],
    source_text="LINE ONE TEXT LINE TWO", rect=(40, 40, 320, 70),
    kind="dialogue",
    ocr_polys=[np.array([[40, 40], [360, 40], [360, 110], [40, 110]],
                        np.float32)])
out3 = tr._rescue_orphan_lines(img5, [big])
gate("D4: کاندیدای پوشیده رد (بدون یتیمِ تکراری)", len(out3) == 1,
     f"n={len(out3)}")

print("== E) گپِ گروهِ LaMa ==")
src = open(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "manga.py"), encoding="utf-8").read()
gate("E1: gap=220 برای زنجیرهٔ پنجرهها",
     "min(220, round(_short * 0.24))" in src)

print("== F) کامپایل ==")
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
r = subprocess.run([sys.executable, "-m", "py_compile",
                    os.path.join(base, "manga.py")], capture_output=True, text=True)
gate("F1: manga.py", r.returncode == 0, r.stderr[-100:] if r.returncode else "")

print(f"\n{'='*46}\nنتایج: {len(PASS)} سبز / {len(FAIL)} قرمز")
if FAIL:
    print("قرمزها:", FAIL)
    sys.exit(1)
