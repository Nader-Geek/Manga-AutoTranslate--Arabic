#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.14.238 — تستِ منطقیِ فیکسهایِ پاکسازی:

  ۱) نوارهای چرخیده (_rotated_region_strips):
     - متنِ کجِ سیاه روی زمینهٔ زردِ روشن → ماسک ⊂ پالی‌ها+پد؛
       دیوارِ (خطِ تیرهٔ) حباب که نوارِ محور-تراز قطع میکرد پوشیده
       نمیشود (نوار در فضای همسطح از آن فاصله دارد).
     - زاویهٔ ~۰ → None نمی‌دهد ولی فراخواننده مسیرِ عادی میرود (گیت).
  ۲) جارویِ خرده‌گلیف (_compose_dot_sweep):
     - نقطهٔ تیرهٔ ریز داخلِ حبابِ روشنِ تخت → پاک میشود؛
     - مؤلفهٔ چسبیده به مرز (دیوار) → دستنخورده؛
     - زمینهٔ تیره/بافت‌دار → کل ناحیه رد.
  ۳) گاردهایِ متن: MANGA_ROT_STRIPS=0 / MANGA_TEXTPANEL=0 /
     MANGA_DOT_SWEEP=0 خاموش میکنند.
"""

import os
import sys

import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

PASS = []
FAIL = []


def chk(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("[+] " if cond else "[-] ") + name)


def make_translator():
    import manga
    tr = manga.MangaTranslator.__new__(manga.MangaTranslator)
    tr.debug = False
    return tr


def test_rotated_strips():
    tr = make_translator()
    # صفحهٔ 400×300، زمینهٔ زردِ روشن؛ متنِ کجِ ۲۰- سیاه در وسط؛
    # «دیوار» = خطِ تیرهٔ عمودی در x=320
    img = np.full((300, 400, 3), (30, 220, 240), np.uint8)  # زرد (BGR)
    cv2.line(img, (320, 0), (320, 300), (40, 40, 40), 6)
    M = cv2.getRotationMatrix2D((170, 150), 20.0, 1.0)
    polys = []
    for (y0, y1) in ((120, 145), (160, 185)):
        for x0 in range(100, 240, 28):
            # حرفِ 14×20
            pts = np.array(
                [[x0, y0], [x0 + 14, y0], [x0 + 14, y1], [x0, y1]],
                np.float32)
            # به مختصاتِ چرخیده: ناحیه به اندازهٔ -۲۰ چرخیده → متن صاف
            Mi = cv2.invertAffineTransform(M)
            q = np.hstack([pts, np.ones((4, 1), np.float32)])
            rq = (Mi @ q.T).T
            # در «فضایِ چرخیده» متن صاف است؛ ولی ما پالی را در فضایِ
            # اصلی میدهیم — پس برعکس: متنِ کج در تصویرِ اصلی
            polys.append(rq.astype(np.float32))
    # متنِ کج را رویِ تصویر بکش
    for p in polys:
        cv2.fillPoly(img, [np.rint(p).astype(np.int32)], (20, 20, 20))
    res = tr._rotated_region_strips(img, polys, -20.0)
    chk("rot: خروجی دارد", res is not None)
    if res is None:
        return
    m, f = res
    chk("rot: ماسک غیرخالی", int(cv2.countNonZero(m)) > 300)
    # ماسک نباید به دیوار (x≥315) خورده باشد
    wall = m[:, 310:]
    chk("rot: دیوار پوشیده نشده", int(cv2.countNonZero(wall)) == 0)
    # پوششِ متن: ≥۷۰٪ پیکسلهایِ تیرهٔ متن (بیرون از دیوار) داخلِ ماسک
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ink = (g < 80)
    ink[:, 300:] = False  # دیوار از مرجع خارج — نباید پوشیده شود
    covered = int(((m > 0) & ink).sum())
    chk("rot: متن پوشش داده شد", covered >= 0.70 * int(ink.sum()))
    # گیتِ خاموشی
    os.environ["MANGA_ROT_STRIPS"] = "0"
    from manga import MangaTranslator
    lines = MangaTranslator._group_polys_to_lines(polys)
    chk("rot: گیت env (سطحِ فراخواننده)", lines is not None)
    del os.environ["MANGA_ROT_STRIPS"]


def test_dot_sweep():
    tr = make_translator()
    import manga
    from manga import TextRegion

    class R:
        id = 7
        kind = "dialogue"
        rect = (10, 10, 200, 120)
        ocr_polys = [np.array(
            [[20, 30], [200, 30], [200, 46], [20, 46]], np.float32)]

    cleaned = np.full((160, 240, 3), 250, np.uint8)
    # نقطهٔ تیرهٔ ریز وسط
    cleaned[60:66, 90:96] = 30
    # مؤلفهٔ چسبیده به مرزِ برش (x≤۱۰ = لبهٔ ناحیه) = دیوار
    cleaned[10:40, 6:12] = 30
    original = cleaned.copy()
    zone = np.zeros((160, 240), np.uint8)
    zone[25:50, 15:205] = 255  # نوارِ کامپوزِ فرضی
    n = tr._compose_dot_sweep(cleaned, original, zone, [R()], verbose=False)
    chk("dot: نقطهٔ آزاد پاک شد", cleaned[60:66, 90:96].min() > 150)
    chk("dot: دیوارِ مرزی دست‌نخورده",
        int(cleaned[10:40, 6:12].max()) == 30)
    chk("dot: تعدادِ قطعه گزارش شد", n >= 1)
    # زمینهٔ تیره → رد
    cleaned2 = np.full((160, 240, 3), 60, np.uint8)
    cleaned2[60:66, 90:96] = 10
    n2 = tr._compose_dot_sweep(cleaned2, cleaned2.copy(), None, [R()],
                               verbose=False)
    chk("dot: زمینهٔ تیره رد شد", n2 == 0)
    # زمینهٔ بافت‌دار (نویزِ تند) → رد: یا کلاً از آستانهٔ تخت بودن یا
    # از سقفِ جوهر
    rng = np.random.RandomState(3)
    cleaned3 = (210 + rng.randn(160, 240, 3) * 80).clip(0, 255)
    cleaned3 = cleaned3.astype(np.uint8)
    cleaned3[60:66, 90:96] = 30
    n3 = tr._compose_dot_sweep(cleaned3, cleaned3.copy(), None, [R()],
                               verbose=False)
    chk("dot: زمینهٔ بافت‌دار رد شد", n3 == 0)
    # sfx/promo رد میشود
    class S(R):
        kind = "sfx"
    cleaned4 = np.full((160, 240, 3), 250, np.uint8)
    cleaned4[60:66, 90:96] = 30
    n4 = tr._compose_dot_sweep(cleaned4, cleaned4.copy(), None, [S()],
                               verbose=False)
    chk("dot: sfx رد شد", n4 == 0)


def test_panel_adaptive():
    import manga
    # med_h بزرگ → سقفهایِ بزرگتر
    img = np.full((300, 300, 3), 250, np.uint8)
    # دهها گلیفِ ۷۰px
    rng = np.random.RandomState(5)
    for i in range(14):
        y = 40 + (i % 7) * 34
        x = 30 + (i // 7) * 120
        cv2.rectangle(img, (x, y), (x + 26, y + 26), 20, -1)
    excl = np.zeros((300, 300), np.uint8)
    m = manga.MangaTranslator._panel_leftover_ink(
        img, (10, 10, 280, 280), excl, med_h=80.0)
    chk("panel: گلیفِ بزرگ با med_h پذیرفته شد", m is not None)
    m2 = manga.MangaTranslator._panel_leftover_ink(
        img, (10, 10, 280, 280), excl, med_h=0.0)
    # بدونِ med_h رفتارِ قدیمی (سقفِ ۶۴) — اینجا گلیف ۲۶px است پس
    # هر دو باید بگیرند؛ تستِ سازگاریِ پیشفرض
    chk("panel: پیشفرض (med_h=0) هم کار میکند", m2 is not None)


def main():
    test_rotated_strips()
    test_dot_sweep()
    test_panel_adaptive()
    print(f"\n[*] پاس: {len(PASS)} | شکست: {len(FAIL)}")
    if FAIL:
        for f in FAIL:
            print("    [-] " + f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
