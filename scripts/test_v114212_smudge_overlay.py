#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""گیت‌های نسخهٔ 1.14.212 — «لگهٔ سیاه/سفید» + روکشِ حاشیه‌نویسیِ ورودی.

دستورهای سازنده:
  «فقط مشکل لگه سیاه سفید داره یا لگه متن قبلی دیده میشه … نه لگه سیاهی
  نه لگه سفیدی یا هرنگی لگه بشه قبول نمیکنم باید خوب پاک شه با lama onnx»
  + «یک کاری کن حباب متن خراب نشه تو انتقال متن به عکس دوم»
  + «همه عکس هاشو خوب تست کن مو به مو چک کن رد نکن»
"""
import os
import re
import sys

import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import manga  # noqa: E402

OK = 0
BAD = 0


def gate(name, cond):
    global OK, BAD
    if cond:
        print(f"[✓] {name}")
        OK += 1
    else:
        print(f"[✗] {name}")
        BAD += 1


src = open(os.path.join(os.path.dirname(__file__), "..", "manga.py"),
           encoding="utf-8").read()

# ── ۱) نسخهٔ سه‌جا ──
gate("APP_VER = 1.14.212", 'APP_VER = "1.14.212"' in src)
ver = open(os.path.join(os.path.dirname(__file__), "..", "VERSION"),
           encoding="utf-8").read()
gate("VERSION = 1.14.212/216", "versionCode=216" in ver
     and "versionName=1.14.212" in ver)
grad = open(os.path.join(os.path.dirname(__file__), "..",
                         "android/app/build.gradle.kts"),
            encoding="utf-8").read()
gate("build.gradle.kts = 1.14.212/216",
     "versionCode = 216" in grad and 'versionName = "1.14.212"' in grad)

# ── ۲) گیتِ پیشفرضِ روشن رویِ PC (همسازِ نوار + نجاتِ حلقه) ──
gate("گیتِ _gate_default_on تعریف شد", "def _gate_default_on(" in src)
gate("همسازِ نوار (139b) رویِ PC هم روشن",
     '_gate_default_on("MANGA_STRIP_HARM")' in src)
gate("نجاتِ پرِ تختِ حلقه (133) رویِ PC هم روشن",
     '_gate_default_on("MANGA_FILL_RESCUE")' in src)
# env=0 خاموش میکند
os.environ["MANGA_STRIP_HARM"] = "0"
gate("MANGA_STRIP_HARM=0 خاموش", manga._gate_default_on("MANGA_STRIP_HARM")
     is False)
del os.environ["MANGA_STRIP_HARM"]
gate("پیشفرضِ MANGA_STRIP_HARM روشن", manga._gate_default_on(
    "MANGA_STRIP_HARM") is True)

# ── ۳) روکشِ حاشیه‌نویسی: نقشه + ادغام در donor/کامپوز ──
gate("نقشهٔ _page_annotation_overlay ساخته میشود",
     "_page_annotation_overlay = _anl212" in src)
gate("شاهدِ سبز (S≥۶۰، هیویِ ۴۰..۸۰) — نه fringeیِ JPEG",
     "_hue212 >= 40) & (_hue212 <= 80" in src)
gate("حضور = قابِ اشباعِ ≥۱۵۰px", "_n60_212 < 150" in src)
gate("پرِ تختِ سفیدِ شکاف (پیشفرض روشن، env=0 خاموش)",
     'os.environ.get("MANGA_212_FLAT", "1") != "0"' in src)
gate("استثنایِ قابِ رنگی در کامپوز: روکش منتقل شود",
     "_cmp &= ((_pcC == 0) | (_anC212 > 0))" in src)
gate("روکش در ماسکِ donor",
     "_anD212 = getattr(self, \"_page_annotation_overlay\"" in src)
gate("روکش در ماسکِ کامپوز",
     "_anW212 = getattr(self, \"_page_annotation_overlay\"" in src)

# ── ۴) کارکردی: تشخیصِ روکش رویِ تصویرِ ساختگی ──
tr = manga.MangaTranslator(
    api_key=["dummy"], provider="gemini", ocr_langs=["en"],
    font_path="fonts/Vazir-Code.ttf", reading_order="rtl", gpu=False,
    clean_method="opencv", det_confidence=0.16, min_confidence=0.12,
    two_pass_ocr=False, img_format="jpg",
)


class _R:  # ناحیهٔ ساختگی
    def __init__(self, rect, polys):
        self.rect = rect
        self.ocr_polys = polys
        self.kind = "text_free"


def _mk_annotated():
    """حبابِ سفید + قابِ سبزِ حاشیه‌نویسی + متنِ سیاه."""
    img = np.full((400, 400, 3), 255, np.uint8)
    cv2.circle(img, (200, 200), 150, (40, 40, 40), 4)  # دیوارِ حباب
    cv2.rectangle(img, (106, 126), (294, 274), (60, 200, 60), 6)  # قابِ سبز
    cv2.putText(img, "HELLO WORLD TEST", (118, 170), 0, 0.55,
                (20, 20, 20), 2)
    cv2.putText(img, "SECOND LINE HERE", (118, 205), 0, 0.55,
                (20, 20, 20), 2)
    polys = [np.array([[115, 155], [275, 155], [275, 180], [115, 180]],
                      np.float32),
             np.array([[115, 190], [265, 190], [265, 215], [115, 215]],
                      np.float32)]
    return img, _R((100, 120, 200, 160), polys)


def _mk_clean_banner():
    """بنرِ سیاه + متنِ سفید — fringeیِ JPEG نه قابِ سبز."""
    img = np.full((400, 400, 3), 255, np.uint8)
    cv2.rectangle(img, (20, 60), (380, 110), (10, 10, 30), -1)  # بنرِ تیره
    cv2.putText(img, "THE SKYBRIDGE SIGNAL", (30, 92), 0, 0.7,
                (240, 240, 250), 2)
    # فشردهسازیِ JPEG برای fringeیِ کروماتیک
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 72])
    img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    polys = [np.array([[28, 70], [372, 70], [372, 100], [28, 100]],
                      np.float32)]
    return img, _R((20, 60, 360, 50), polys)


# بازسازیِ نقشه از طریقِ _structural_protect_mask
def build_overlay(img, region):
    tr._page_raw_text_mask = None
    h, w = img.shape[:2]
    raw = np.zeros((h, w), np.uint8)
    for p in region.ocr_polys:
        cv2.fillPoly(raw, [np.rint(p).astype(np.int32)], 255)
    tr._page_raw_text_mask = raw
    tr._promo_rect_boxes = []
    manga.MangaTranslator._structural_protect_mask(
        tr, img, [region], min_len=60, near_px=25)
    return getattr(tr, "_page_annotation_overlay", None), img


ov1, img1 = build_overlay(*_mk_annotated())
gate("روکشِ سبز رویِ حبابِ سفید تشخیص داده شد",
     ov1 is not None and int((ov1 > 0).sum()) > 2000)
fl1 = getattr(tr, "_page_annotation_flat", None)
gate("پرِ تختِ سفید برایِ حبابِ سفید مجاز شد",
     fl1 is not None and int((fl1 > 0).sum()) > 2000)

ov2, _ = build_overlay(*_mk_clean_banner())
n2 = int((ov2 > 0).sum()) if ov2 is not None else 0
gate("بنرِ ساده بدونِ قابِ سبز → روکش NOT (کاذبِ صفر)",
     n2 == 0)

print(f"\n==== {OK}/{OK + BAD} گیت سبز ====")
sys.exit(0 if BAD == 0 else 1)
