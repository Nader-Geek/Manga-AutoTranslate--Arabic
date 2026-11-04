# -*- coding: utf-8 -*-
"""v1.14.209 — تستِ فیکسهایِ گزارشِ سازنده («متن قبلی میمونه نمیپاکه …
دست جمع بدی به کد نمیپاکه … کل حباب انتقال میدی حباب خراب میکنی»):

۱) ناحیهٔ ocr_empty (زمینهٔ روشن + جوهرِ متنی — حتی بعد از ردِ نجاتِ 201
   مثلِ '85') حالا «فقط پاکسازی» میشود — هم در مسیرِ صفحهٔ تکی
   (finish_page_phase) هم در مسیرِ بچ (K3/_clean_regions_for_page).
   → «متنِ قبلی» دیگر سرِ جایش نمیماند.
۲) کامپوزِ دو-عکسی دیگر «کلِ حباب/بلوک» را منتقل نمیکند: نه باندِ
   تیرهٔ یکدست (۷۸f) نه اینتریورِ باکسِ سیستم (۱۰۴) — فقط نوارهایِ
   خط‌به‌خط به اندازهٔ متن. خرابیِ احتمالیِ عکسِ اول به عکسِ دوم
   نمیرسد (عکسِ a.jpgِ سازنده: فقطِ قابِ متنِ سبز منتقل میشود).
۳) رگرسیون: پاکسازیِ واقعیِ ناحیهٔ ocr_empty رویِ تصویرِ ساختگی + نسخه.
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("MANGA_SKIP_HEAVY_INIT", "1")

import manga  # noqa: E402

MangaTranslator = manga.MangaTranslator
GATES = []


def gate(name, ok, info=""):
    GATES.append((name, bool(ok), info))
    print(f"[{'✓' if ok else '✗'}] {name}" + (f" — {info}" if info else ""))


SRC = open(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "manga.py"), encoding="utf-8").read()


def make_tr(method="opencv"):
    return MangaTranslator(
        api_key="t", provider="gemini", ocr_langs=["en"],
        font_path="fonts/Vazirmatn-Regular.ttf",
        clean_method=method, gpu=False, force_lama=True,
        clean_only=True, debug=False, story_brief=False, max_workers=1)


# ─── ۱) گیتِ منبع: ناحیهٔ بی‌متن در هر دو مسیرِ پاکسازی ────────────────
def test_source_gates():
    gate("مسیرِ تکی: _ocr_empty_regions = _oe149",
         "_ocr_empty_regions = _oe149" in SRC)
    gate("مسیرِ بچ (K3): ocr_empty در فیلترِ پاکسازی",
         "or getattr(r, \"ocr_empty\", False))]" in SRC
         and "متن قبلی میمونه نمیپاکه" in SRC)
    # فیکسِ B — ممنوعیتِ انتقالِ یکجا
    i0 = SRC.find("def _compose_strip_mask")
    i1 = SRC.find("def _compose_polish")
    csm = SRC[i0:i1] if 0 <= i0 < i1 else ""
    gate("کامپوز: انتقالِ کلِ باندِ تیره حذف شد",
         "out[_by0:_by1, _bx0:_bx1] = True" not in csm
         and "ممنوع — قانونِ دو-عکسی" in csm)
    gate("کامپوز: انتقالِ یکجایِ اینتریورِ سیستم حذف شد",
         "out |= _intr104" not in csm and "یکجا ممنوع" in csm)


# ─── ۲) کارکردی: پاکسازیِ ناحیهٔ ocr_empty (بدونِ ocr_polys) ───────────
def test_ocr_empty_cleaned():
    tr = make_tr("opencv")
    img = np.full((160, 420, 3), 248, np.uint8)   # حبابِ سفیدِ تخت
    cv2.putText(img, "LIKE TIME BOMB", (30, 95),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (15, 15, 15), 3)
    before = float(np.mean(img[60:110, 25:330]))
    r = manga.TextRegion(id=1, boxes=[], source_text="",
                         translated_text=None, kind="dialogue")
    poly = np.array([[25, 55], [335, 55], [335, 115], [25, 115]],
                    np.float32)
    r.boxes = [poly]          # عینِ ساختِ ناحیهٔ ocr_empty (۲۵۶۶۰)
    r.ocr_polys = []          # OCR پالی نداشته
    r.rect = (25.0, 55.0, 310.0, 60.0)
    r.angle = 0.0
    r.ocr_empty = True        # حتی بعد از ردِ نجاتِ ۲۰۱ ('85')
    out = tr.clean_image(img.copy(), [r])
    after = float(np.mean(out[60:110, 25:330]))
    gate("ناحیهٔ ocr_empty واقعاً پاک شد (متنِ قبلی نمیماند)",
         after - before > 18.0,
         f"میانگینِ ناحیه: {before:.0f} → {after:.0f}")


# ─── ۳) کارکردی: کامپوز رویِ باندِ تیرهٔ یکدست = فقط نوارِ خط ─────────
def test_compose_strips_only():
    tr = make_tr("opencv")
    img = np.full((220, 460, 3), 96, np.uint8)    # باندِ تیرهٔ یکدست
    cv2.putText(img, "PARAGRAPH ONE", (24, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (235, 235, 235), 2)
    cv2.putText(img, "PARAGRAPH TWO", (24, 160),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (235, 235, 235), 2)
    polys = [np.array([[20, 42], [260, 42], [260, 78], [20, 78]],
                      np.float32),
             np.array([[20, 132], [260, 132], [260, 168], [20, 168]],
                      np.float32)]
    r = manga.TextRegion(id=2, boxes=[], source_text="P",
                         translated_text="پ", kind="dialogue")
    r.ocr_polys = polys
    r.rect = (10.0, 20.0, 440.0, 180.0)
    r.angle = 0.0
    tr._page_regions = [r]
    tr._page_protect = None
    tr._page_wall_band = None
    tr._page_colored_protect = None
    tr._promo_rect_boxes = []
    tr._lama_force_rect_boxes = []
    tr._donor_boxes = []
    mask = np.zeros((220, 460), np.uint8)
    cmp_mask = tr._compose_strip_mask(img, mask) > 0
    ratio = float(cmp_mask.mean())
    gate("کامپوز رویِ باندِ تیره فقط نوارِ متن است (نه کلِ بلوک)",
         ratio < 0.45, f"سهمِ ماسک از بلوک: {ratio*100:.0f}%")


# ─── ۴) نسخه ──────────────────────────────────────────────────────────
def test_version():
    gate("APP_VER = 1.14.209", 'APP_VER = "1.14.209"' in SRC)
    try:
        v = open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "VERSION"),
            encoding="utf-8").read()
        gate("VERSION = 1.14.209/213",
             "versionName=1.14.209" in v and "versionCode=213" in v)
    except Exception:
        gate("VERSION", False)
    import re as _re
    try:
        gsrc = open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))),
            "android/app/build.gradle.kts"), encoding="utf-8").read()
    except Exception:
        gsrc = ""
    g = _re.search(r'versionName = "([^"]+)"', gsrc)
    gate("build.gradle.kts = 1.14.209",
         bool(g) and g.group(1) == "1.14.209")


if __name__ == "__main__":
    test_source_gates()
    test_ocr_empty_cleaned()
    test_compose_strips_only()
    test_version()
    n_ok = sum(1 for _, ok, _ in GATES if ok)
    print(f"\n==== {n_ok}/{len(GATES)} گیت سبک ====")
    sys.exit(0 if n_ok == len(GATES) else 1)
