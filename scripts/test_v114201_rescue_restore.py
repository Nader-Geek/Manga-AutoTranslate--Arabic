#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.14.201 — تستِ «نجاتِ بی‌جا ممنوع» + «بازگردانیِ اورجینال بعد از
ترمیمِ ناتمام» — گزارشِ باگِ فصلِ ۱۱۰ (سازنده: «بعضی متن هارو پاک نزده
یا روش متن روشته گذاشته... مشکل استخراج از ocr هست یا detector») —

ریشه‌ها از لاگِ clean-onlyِ خودِ فصل:
  (۱) rapidocr (en) رویِ افکتِ صوتیِ کره‌ای/تایتلِ کره‌ای خالی برمیگردد
      → نجاتِ OCR نویز میدهد ('99'، '年'، '人'، '三弄'، '/'، '/星'، 'C'،
      '得'، 'E') → متنِ آشغال به مترجم میرود → ترجمهٔ آشغالِ فارسی روی
      همان ناحیه مینشیند (اسکرین‌شات: «تو کی هستی؟! جایزه‌ای؟ من!») و
      چون ناحیه «بامتن» شده، پاکسازیِ هنر هم می‌شود → لکه/نصفه‌پاک.
  (۲) وقتی همهٔ مراحلِ ترمیمِ پس از پاکسازی رد میشوند، خروجیِ
      نصفه‌پاک «مانده» میشد (crop@(405,508)/crop@(466,4504)/
      crop@(205,6117)) → تکهٔ جوهرِ نصفه‌محوشده = «پاک نزده/روش متن
      نوشته». حالا اورجینالِ همان ناحیه برمیگردد.
گیت‌ها: فیلترِ نجات (کارکردی) + بازگردانیِ اورجینال (کارکردی رویِ
_verify_repair_clean واقعی) + رگرسیونِ نسخه.
"""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import cv2  # noqa: E402

import manga  # noqa: E402

PASS = 0
FAIL = 0


def gate(name, ok):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}")


print("══ گیتِ ۱: نسخه ══")
gate("APP_VER = 1.14.201", manga.APP_VER == "1.14.201")

print("══ گیتِ ۲: فیلترِ نجاتِ OCR (کارکردی) ══")
# ناحیهٔ ocr_empty واقعی بساز — عینِ مسیرِ extraction (لاگِ فصل:
# Region [N] had no OCR text but has text-like ink → cleaning only)
mt = manga.MangaTranslator.__new__(manga.MangaTranslator)
mt.debug = True
img = np.full((120, 260, 3), 245, np.uint8)
cv2.putText(img, "K", (60, 80), cv2.FONT_HERSHEY_SIMPLEX, 2.0,
            (20, 20, 20), 5)
r = manga.TextRegion(
    id=7, boxes=[np.array([[10, 10], [250, 10], [250, 110], [10, 110]])],
    source_text="", rect=(10, 10, 240, 100), angle=0.0, kind="dialogue",
    ocr_polys=[])
r.ocr_empty = True

# OCR موتور را با فیکِ نویز جایگزین میکنیم — عینِ حالتِ افکتِ کره‌ای:
# برشِ اصلی خالی، برشِ معکوسِ (bitwise_not) «نویزِ» تک‌حرفی میدهد
_calls = {"n": 0}


class _FakeOcrNoise:
    def ocr(self, _img, **kw):
        # هر فراخوانی «年» برمیگرداند — نویزِ recِ CJK رویِ هنر
        return [[([0, 0], ("年", 0.9))]]


mt.ocr = _FakeOcrNoise()
mt._rescue_empty_ocr_1149(img, [r])
gate("نویزِ «年» نجات نمیگیرد (ocr_empty ماند)", bool(r.ocr_empty))
gate("متنِ نویز به source_text ننشست", not (r.source_text or "").strip())

# حالا نجاتِ واقعی: معکوسِ برش «OK» بدهد → باید پذیرفته شود
r2 = manga.TextRegion(
    id=8, boxes=[np.array([[10, 10], [250, 10], [250, 110], [10, 110]])],
    source_text="", rect=(10, 10, 240, 100), angle=0.0, kind="dialogue",
    ocr_polys=[])
r2.ocr_empty = True


class _FakeOcrOk:
    def ocr(self, _img, **kw):
        return [[([0, 0], ("OK", 0.9))]]


mt.ocr = _FakeOcrOk()
mt._rescue_empty_ocr_1149(img, [r2])
gate("نجاتِ سالمِ «OK» پذیرفته شد", (r2.source_text or "") == "OK"
     and not r2.ocr_empty)

# تک‌حرفِ «C» و رقمِ «99» و «/星» هم رد شوند — عینِ لاگِ فصل
for bad in ("C", "99", "/星", "三弄", "E", "得", "/", "人"):
    rb = manga.TextRegion(
        id=9, boxes=[np.array([[10, 10], [250, 10], [250, 110], [10, 110]])],
        source_text="", rect=(10, 10, 240, 100), angle=0.0, kind="dialogue",
        ocr_polys=[])
    rb.ocr_empty = True

    class _FakeOcrBad:
        def __init__(self, t):
            self.t = t

        def ocr(self, _img, **kw):
            return [[([0, 0], (self.t, 0.9))]]

    mt.ocr = _FakeOcrBad(bad)
    mt._rescue_empty_ocr_1149(img, [rb])
    gate(f"نویزِ {bad!r} رد شد", bool(rb.ocr_empty)
         and not (rb.source_text or "").strip())

print("══ گیتِ ۳: بازگردانیِ اورجینال بعد از ترمیمِ ناتمام (کارکردی) ══")
# صحنه: عکسِ اورجینال با جوهرِ تیره؛ cleaned نصفه‌پاک (جوهرِ محو مانده)
rng = np.random.RandomState(7)
base = np.full((220, 240, 3), 235, np.uint8)
base[:, :, 0] = 225
# جوهرِ «متنِ نصفه‌پاک» داخلِ ماسک
orig = base.copy()
cv2.rectangle(orig, (70, 60), (170, 150), (25, 25, 25), -1)
cleaned = orig.copy()
# ترمیمِ فرضیِ نصفه: جوهر را کمی محو کردهایم (لکهٔ خاکستری)
cleaned[70:150, 70:170] = (128, 128, 128)
# ماسکِ هسته با حاشیه — وگرنه حلقه (ring) خالی میشود و تابع زود برمیگردد
crop_msk = np.zeros((90, 100), np.uint8)
crop_msk[8:82, 8:92] = 255
mt2 = manga.MangaTranslator.__new__(manga.MangaTranslator)
mt2.debug = True
mt2._verify_repair_clean(cleaned, orig, 70, 60, 170, 150,
                         crop_msk, "LaMa", limit=None)
_diff = int(np.mean(np.abs(
    cleaned[80:140, 80:160].astype(np.int16) -
    orig[80:140, 80:160].astype(np.int16))))
gate("بعد از ناتمامیِ ترمیم، اورجینال برگشت (جوهرِ تیره سرِ جایش)",
     _diff < 12)

# و در حالتِ عادیِ (ترمیمِ موفقِ شبیهسازی شده) دست نمیخورد:
cleaned2 = orig.copy()
cv2.rectangle(cleaned2, (70, 60), (170, 150), (235, 235, 235), -1)
_before2 = cleaned2.copy()
mt2._verify_repair_clean(cleaned2, orig, 70, 60, 170, 150,
                         crop_msk, "LaMa", limit=None)
gate("پاکِ تمیزِ بدونِ جوهر دستنخورده ماند",
     np.array_equal(_before2, cleaned2))

print("══ گیتِ ۴: سبکِ کد — حداقلِ تغییر ══")
src = open(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "manga.py"), encoding="utf-8").read()
gate("فیلترِ نجات داخلِ _rescue_empty_ocr_1149 است",
     "_lt201" in src and src.index("_lt201") > src.index(
         "def _rescue_empty_ocr_1149"))
gate("بازگردانیِ اورجینال داخلِ _verify_repair_clean است",
     "[↺201] بازگردانیِ اورجینال" in src and src.index(
         "[↺201] بازگردانیِ اورجینال") > src.index(
         "def _verify_repair_clean"))
gate("قفلِ نوارِ کامپوز در بازگردانی هم هست",
     "limit[Y0:Y1, X0:X1]" in src.split("[↺201]")[0][-1200:])

print(f"\n═══ نتیجه: {PASS} سبز / {FAIL} سرخ ═══")
sys.exit(1 if FAIL else 0)
