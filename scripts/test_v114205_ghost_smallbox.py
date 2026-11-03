#!/usr/bin/env python3
# v1.14.205 — «yeah yeah استخراج نشده یا پاک نشده؟» + «متن also هم دیده
# میشه یا پاک نشده یا نگرفته؟» (گزارشِ سازنده + لاگِ v1.14.200 + debug PDF)
# ── باگِ ۱ (YEAH, YEAH~ غیب): فیلترِ «باکسِ خیلی کوچک» در
#     _extract_regions_from_bubbles با page_areaِ «کلِ نوار» مقیاس میگرفت:
#     ۰.۰۸٪ِ ۷۰۰×۷۷۹۲ = ۴۳۶۴px² — حبابِ ۵۸×۶۱ (لاگِ سبزِ D11 رویِ خودِ
#     حباب) با لرزشِ ±چندpx زیرِ ۶۰px میرفت و «۲۴ خام → ۲۳ OCR» بیصدا
#     میشد. فیکس: مبنا = یک تایلِ detector (min(h, TILE_HEIGHT)×w) →
#     آستانه ≈۹۴۱px² — حبابِ واقعی با هر لرزشی زنده میماند، خاکِ نویز
#     (۲۵×۲۵) همچنان حذف. + لاگِ حذفهایِ بیصدا (لاگِ کاملِ سازنده).
# ── باگِ ۲ (شبحِ «ALSO»): ماسکِ پاکسازی هستهٔ تیره + هالهٔ ۱۴..۳۰ را
#     میگیرد ولی لبهٔ خیلی روشنِ حرف (≤۱۴ سطح از زمینه) را نه؛ کامپوزِ
#     فقط-هسته آن پیکسلها را از عکسِ اورجینال برمیگرداند = شبحِ خوانا.
#     فیکس: در _compose_region_strips پیکسلهایِ روشنِ چسبیده به هسته
#     (dilate7 ∩ |Δ|≤۱۴) از عکسِ پاک‌شده بیایند — پیکسلِ ناپاکشده در هر
#     دو عکس یکسان است (صفر ریسک) و زمینهٔ هنریِ پرقاومت از اورجینال
#     میماند.
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
import manga
from manga import MangaTranslator, TextRegion

import numpy as np
import cv2

_GATES = []


def gate(name, ok):
    _GATES.append((name, bool(ok)))
    print(f"  [{'✓' if ok else '✗'}] {name}")


def _quad(x1, y1, x2, y2):
    return np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.int32)


def _region(x1, y1, x2, y2, text, polys=None):
    return TextRegion(id=-1, boxes=[_quad(x1, y1, x2, y2)],
                      source_text=text, rect=(x1, y1, x2 - x1, y2 - y1),
                      angle=0.0, kind="dialogue",
                      ocr_polys=polys or [])


print("── الف) نسخهٔ ۳جا ──")
_src = open(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "manga.py"), encoding="utf-8").read()
gate("APP_VER = 1.14.205", 'APP_VER = "1.14.205"' in _src)
_vf = open(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "VERSION"), encoding="utf-8").read()
gate("VERSION versionName=1.14.205", "versionName=1.14.205" in _vf)
_gk = open(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "android", "app", "build.gradle.kts"),
    encoding="utf-8").read()
gate("build.gradle.kts versionName 1.14.205",
     'versionName = "1.14.205"' in _gk)

print("── ب) فیلترِ باکسِ کوچک در مقیاسِ تایل، نه نوار (کارکردی) ──")
# نوارِ ۷۰۰×۷۷۹۲ مثلِ strip_001 لاگِ v1.14.200 — زمینهٔ سفید
H, W = 7792, 700
img = np.full((H, W, 3), 252, dtype=np.uint8)


class _StubDet:
    def __init__(self, rects):
        self._rects = rects

    def detect(self, image, fast=False):
        out = []
        for (x1, y1, x2, y2) in self._rects:
            out.append({"class_id": 1, "class_name": "text_bubble",
                        "confidence": 0.9, "rect": [x1, y1, x2, y2],
                        "shape_type": "round", "mask_poly": None})
        return out


class _StubT(manga.MangaTranslator):
    pass


def _run_extract(rects):
    s = _StubT.__new__(_StubT)
    s.det = _StubDet(rects)
    s.debug = False
    s.max_workers = 1
    s.min_confidence = 0.5
    s.ocr = None
    s._k3_used = False
    orig_ocr = manga.MangaTranslator._ocr_crop
    manga.MangaTranslator._ocr_crop = (
        lambda self, image_bgr, rect, block_rects=None:
        ("YEAH, YEAH~",
         [np.array([[rect[0] + 2, rect[1] + 2], [rect[2] - 2, rect[1] + 2],
                    [rect[2] - 2, rect[3] - 2], [rect[0] + 2, rect[3] - 2]],
                   dtype=np.int32)],
         [0.0], ["YEAH, YEAH~"], [-1]))
    try:
        return s._extract_regions_from_bubbles(img)
    finally:
        manga.MangaTranslator._ocr_crop = orig_ocr


# حبابِ واقعیِ «YEAH, YEAH~» (لاگِ سبزِ D11: ۵۸×۶۱) + نسخههایِ لرزیده
# + خاکِ نویزِ ۲۵×۲۵ که باید حذف بماند — هرکدام در رانِ جدا (تا
# _drop_contained_boxes بینِ باکسهایِ همپوشانِ آزمون قاطی نکند)
_y1 = [r for r in _run_extract([(568, 2096, 626, 2157)])      # 58x61 = 3538px²
       if abs(int(r.rect[0]) - 568) <= 2 and abs(int(r.rect[1]) - 2096) <= 2]
_y2 = [r for r in _run_extract([(569, 2103, 625, 2157)])      # 56x54 = 3024px²
       if abs(int(r.rect[0]) - 569) <= 2 and abs(int(r.rect[1]) - 2103) <= 2]
_r3 = _run_extract([(568, 2096, 626, 2157), (100, 4000, 125, 4025)])
_spk = [r for r in _r3 if abs(int(r.rect[0]) - 100) <= 2]
gate("باکسِ 58x61 ناحیه شد", bool(_y1))
gate("باکسِ لرزیدهٔ 56x54 هم ناحیه شد (ریشهٔ «۲۴→۲۳»)", bool(_y2))
gate("نویزِ 25x25 همچنان حذف", not _spk)
gate("عکسِ یعنی متنِ حباب سرِ جایش",
     bool(_y2) and "YEAH" in (_y2[0].source_text or ""))

print("── پ) لاگِ حذفهایِ بیصدا (لاگِ کامل) ──")
s = _StubT.__new__(_StubT)
s.det = _StubDet([(100, 4000, 125, 4025)])
s.debug = True
s.max_workers = 1
s.min_confidence = 0.5
s.ocr = None
import io
import contextlib
_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    try:
        s._extract_regions_from_bubbles(img)
    except Exception:
        pass
gate("حذفِ باکسِ کوچک حالا در لاگ میآید",
     "باکسِ خیلی کوچک حذف شد" in _buf.getvalue())

print("── ت) کامپوز: شبحِ لبهٔ حروف (کارکردیِ مصنوعی) ──")
# زمینهٔ سفید + «متن» = خطهایِ تیرهٔ گسسته + لبهٔ خیلی روشن (۲۴۲ = Δ۱۳)
img2 = np.full((120, 260, 3), 255, dtype=np.uint8)
for cx in range(40, 200, 7):
    img2[58:66, cx:cx + 4] = 70            # هستهٔ تیره (مثلِ حرف)
    img2[56:58, cx:cx + 4] = 242           # لبهٔ روشنِ بالا (Δ=۱۳)
    img2[66:68, cx:cx + 4] = 242           # لبهٔ روشنِ پایین
img2[10:18, 10:26] = 242                   # لکهٔ روشنِ دور از متن (باید بماند)


def _compose_of(polys):
    s2 = _StubT.__new__(_StubT)
    s2.debug = False
    rg = _region(20, 50, 220, 74, "X", polys=polys)
    m, _failed = s2._compose_region_strips(img2, rg)
    return (m > 0) if m is not None else np.zeros(img2.shape[:2], bool)


poly = _quad(36, 58, 204, 66)
m = _compose_of([poly])
_core = (img2[:, :, 0] == 70)
_ring = (img2[:, :, 0] == 242) & (np.arange(120)[:, None] >= 54) \
    & (np.arange(120)[:, None] <= 70)
gate("هستهٔ تیره در کامپوز", bool((m & _core).sum() >= 0.9 * _core.sum()))
gate("لبهٔ روشنِ چسبیده به هسته حالا از عکسِ پاک‌شده میآید (فیکسِ شبح)",
     float((m & _ring).sum()) >= 0.75 * float(_ring.sum()))
gate("لکهٔ روشنِ دور از متن از کامپوز بیرون مانده",
     not bool(m[10:18, 10:26].any()))

print("── ث) کامپوز رویِ صفحهٔ واقعیِ img7 (حبابِ YOU SHOULD ALSO) ──")
_det_ok = os.path.isfile(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "det_models", "detector-v4-s_int8.onnx"))
if not _det_ok:
    print("  [skip] مدلِ detector در det_models نیست — گیتِ واقعی رد شد")
    gate("صفحهٔ واقعی (مدل نبود — skip)", True)
else:
    p7 = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "ci_imgs", "img7.jpg")
    if not os.path.isfile(p7):
        p7 = "/home/z/my-project/upload/img7.jpg"
    im7 = cv2.imread(p7)
    im7n = cv2.resize(im7, (700, round(im7.shape[0] * 700 / im7.shape[1])),
                      interpolation=cv2.INTER_AREA)
    s3 = _StubT.__new__(_StubT)
    s3.ocr = manga.RapidOCRBackend(lang="en")
    s3.min_confidence = 0.5
    s3.debug = False
    s3.max_workers = 2
    s3.det = manga.RTDetrV2ONNXDetector(prefer_gpu=False)
    regs3 = s3._extract_regions_from_bubbles(im7n)
    tgt = None
    for r in regs3:
        x, y = int(r.rect[0]), int(r.rect[1])
        if 275 <= x <= 295 and 1575 <= y <= 1600:
            tgt = r
            break
    gate("حبابِ YOU-should-ALSO استخراج شد", tgt is not None)
    if tgt is not None:
        m3, _f3 = s3._compose_region_strips(im7n, tgt)
        m3 = m3 > 0
        g3 = cv2.cvtColor(im7n, cv2.COLOR_BGR2GRAY).astype(np.float32)
        pm3 = np.zeros(g3.shape, np.uint8)
        for p in tgt.ocr_polys:
            cv2.fillPoly(pm3, [np.rint(np.asarray(p, dtype=np.float32)
                                       .reshape(-1, 2)).astype(np.int32)], 255)
        pm3 = cv2.dilate(pm3, np.ones((7, 7), np.uint8)) > 0
        _med3 = float(np.median(g3[pm3]))
        _lite3 = pm3 & (np.abs(g3 - _med3) <= 14.0)
        _dark3 = pm3 & (g3 < 150)
        cov_lite = float((m3 & _lite3).sum()) / max(1.0, float(_lite3.sum()))
        cov_dark = float((m3 & _dark3).sum()) / max(1.0, float(_dark3.sum()))
        gate(f"جوهرِ تیره ۱۰۰٪ در کامپوز ({cov_dark:.2f})", cov_dark >= 0.99)
        gate(f"لبهٔ روشنِ چسبیده پوشش داده شد ({cov_lite:.2f} — قبل: فقط هسته)",
             cov_lite >= 0.70)
        # خطِ داغِ رگرسیون: ماسکِ کامپوز از بلوکِ پالی بیرون نزند
        gate("کامپوز داخلِ پالیهایِ OCR مانده (نه بیشتر)",
             bool((m3 & ~pm3).sum()) <= 0.02 * max(1, int(m3.sum())))

print()
_n_ok = sum(1 for _, ok in _GATES if ok)
print(f"{'✅' if _n_ok == len(_GATES) else '❌'} "
      f"{_n_ok}/{len(_GATES)} گیت سبز")
sys.exit(0 if _n_ok == len(_GATES) else 1)
