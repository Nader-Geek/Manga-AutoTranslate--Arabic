#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ منطقیِ v1.14.237 — «استخراجِ سریع با CPU، مدلِ همان PaddleOCR ONNX».

دو تغییرِ این نسخه:
  ۱) سیاستِ detِ کراپ (RapidOCR): زبانهایِ لاتین = 960/max (پیشفرضِ رسمیِ
     PaddleOCR — بدونِ بزرگنماییِ کراپِ کوچک) | CJK = همان 736/minِ
     rapidocr (حفظِ خواندنِ کانجیِ ریز) | اورراید: MANGA_OCR_DET_LIMIT /
     MANGA_OCR_DET_TYPE | خاموشِ کامل: MANGA_OCR_DET_FAST=0
  ۲) پورتِ فیکسِ مرتب‌سازیِ سطل‌ایِ اندروید (v1.14.185) به PC:
     row_h = ۰.۷۵×میانهٔ بلندیِ خط به‌جایِ ۱.۲۵× (دو خطِ مجاورِ حبابِ
     فشرده دیگر در یک سطل نمی‌افتند → تای‌بریکِ x ترتیب را نمی‌چیند).

این اسکریپتِ «منطقی» است (بدونِ مدل/عکس — سریعِ CI):
  • ۱۳ حالتِ تابعِ سیاستِ det
  • ۵ حالتِ منطقِ سطل‌بندی (حبابِ img7 قبل/بعد + تکههایِ همخط)
  • گاردِ متنِ سورس (پارامترها به موتور وصل شدهاند)
"""

import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = 0
FAIL = 0


def chk(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}")


def policy(lang, **env):
    for k in ("MANGA_OCR_DET_FAST", "MANGA_OCR_DET_LIMIT", "MANGA_OCR_DET_TYPE"):
        os.environ.pop(k, None)
    os.environ.update(env)
    try:
        import importlib
        import manga
        importlib.reload(manga)
        return manga._ocr_det_resize_policy(lang)
    finally:
        for k in ("MANGA_OCR_DET_FAST", "MANGA_OCR_DET_LIMIT", "MANGA_OCR_DET_TYPE"):
            os.environ.pop(k, None)


def main():
    print("── ۱) سیاستِ detِ کراپ (_ocr_det_resize_policy)")
    LATIN = {"Det.limit_side_len": 960, "Det.limit_type": "max"}
    cases = [
        # (برچسب، lang، env، خروجهٔ مطلوب)
        ("لاتین en → 960/max", "en", {}, LATIN),
        ("لاتین fa → 960/max", "fa", {}, LATIN),
        ("لاتین french → 960/max", "french", {}, LATIN),
        ("rollback MANGA_OCR_DET_FAST=0 → None", "en",
         {"MANGA_OCR_DET_FAST": "0"}, None),
        ("rollback مقدارِ false", "en",
         {"MANGA_OCR_DET_FAST": "false"}, None),
        ("ja → None (کانجیِ ریز)", "ja", {}, None),
        ("japan → None", "japan", {}, None),
        ("korean → None", "korean", {}, None),
        ("ko → None", "ko", {}, None),
        ("ch → None", "ch", {}, None),
        ("zh_hans → None", "zh_hans", {}, None),
        ("multi → None (ممکن است کره‌ای باشد)", "multi", {}, None),
        ("اوررایدِ کاربر روی CJK", "ja",
         {"MANGA_OCR_DET_LIMIT": "960", "MANGA_OCR_DET_TYPE": "max"}, LATIN),
        ("اوررایدِ فقط LIMIT روی لاتین", "en",
         {"MANGA_OCR_DET_LIMIT": "480"},
         {"Det.limit_side_len": 480, "Det.limit_type": "max"}),
        ("اوررایدِ فقط TYPE روی لاتین", "en",
         {"MANGA_OCR_DET_TYPE": "min"},
         {"Det.limit_side_len": 960, "Det.limit_type": "min"}),
        ("زبانِ خالی → لاتینِ محتاط؟ خیر — لاتین (enِ پیشفرضِ اپ)", "",
         {}, LATIN),
    ]
    for label, lang, env, want in cases:
        chk(label, policy(lang, **env) == want)

    print("── ۲) منطقِ سطل‌بندیِ مرتب‌سازیِ خطوط (۰.۷۵ به‌جایِ ۱.۲۵)")

    def bucket_order(ytop, hs, xs, labels, factor):
        row_h = max(8.0, float(np.median(hs)) * factor)
        idx = sorted(range(len(labels)),
                     key=lambda i: (int(ytop[i] // row_h), xs[i]))
        return [labels[i] for i in idx]

    # حبابِ img7 «YOU SHOULD ALSO / STOP BEING A SECURITY / …» — مختصاتِ
    # واقعیِ صفحه از دیباگِ detِ 960/max
    ytop = [1831.4, 1848.7, 1867.6, 1884.2]
    hs = [17.2, 18.9, 17.2, 20.0]
    xs = [362.4, 341.3, 353.0, 348.6]
    lbl = ["YOU SHOULD ALSO", "STOP BEING A SECURITY",
           "GUARD HERE AND GO", "SOMEWHERE BETTER~"]
    chk("قدیم (۱.۲۵) این حباب را برمی‌چید",
        bucket_order(ytop, hs, xs, lbl, 1.25) != lbl)
    chk("جدید (۰.۷۵) ترتیبِ درست",
        bucket_order(ytop, hs, xs, lbl, 0.75) == lbl)
    # تکههایِ همخط (دو باکسِ کنارِ هم) همچنان x-مرتب
    chk("تکههایِ همخط x-مرتب میمانند",
        bucket_order([100.0, 100.5], [20.0, 20.0], [50.0, 200.0],
                     ["HELLO", "WORLD"], 0.75) == ["HELLO", "WORLD"])
    # خطِ کجِ ملایم (dy=8px) همخط میماند
    chk("تکههایِ خطِ کجِ ملایم همخط",
        bucket_order([100.0, 108.0], [20.0, 20.0], [50.0, 200.0],
                     ["HELLO", "WORLD"], 0.75) == ["HELLO", "WORLD"])
    # دو خطِ مجاورِ معمولی (گامِ ۱.۳×بلندی) جدا میمانند
    chk("خطهایِ مجاورِ معمولی جدا",
        bucket_order([100.0, 126.0], [20.0, 20.0], [50.0, 50.0],
                     ["L1", "L2"], 0.75) == ["L1", "L2"])

    print("── ۳) سورسِ کد — پارامترها واصل و ضریبِ قدیمی حذف شده")
    src = open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "manga.py"), encoding="utf-8").read()
    chk("_ocr_det_resize_policy تعریف شده", "def _ocr_det_resize_policy" in src)
    chk("پارامترها در مسیرِ rec_params (_p) وصل",
        re.search(r"_p\.update\(_det_speed237\)", src) is not None)
    chk("پارامترها در مسیرِ پیشفرض (_pb) وصل",
        re.search(r"_pb\.update\(_det_speed237\)", src) is not None)
    chk("ضریبِ ۰.۷۵ در مرتب‌سازیِ PC",
        re.search(r"\* 0\.75\)\s*\n\s*merged\.sort", src) is not None)
    chk("ضریبِ قدیمیِ ۱.۲۵ در مرتب‌سازیِ PC حذف",
        re.search(r"\* 1\.25\)\s*\n\s*merged\.sort", src) is None)
    chk("لاگِ det= در پیامِ آمادگیِ موتور",
        "_det_disp237" in src)
    # بازسازیِ موتور بعد از خطایِ GPU هم سیاست را حفظ کند (از همان dict)
    chk("_eng_params233 شاملِ کلِ پارامترهاست (بازسازیِ DML سیاست را نگه میدارد)",
        "_p233 = dict(getattr(self, \"_eng_params233\", None) or {})" in src)

    print(f"\nنتیجه: {PASS} پاس / {FAIL} خطا")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
