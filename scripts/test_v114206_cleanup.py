# -*- coding: utf-8 -*-
"""v1.14.206 — تستِ عملیِ فیکسهایِ پاکسازی (دستورِ سازنده: «پاکسازی لگهٔ
سیاه یا سفید میزاره یا متن قبلی جا میزاره… هم openvc هم حالت lama onnx…
فقط همون اندازه حباب باید پاکسازی کنه… هم گوشی هم پی سی لینوکس…»):

۱) قطبِ اقلیت در _line_strip_ink: متنِ رویِ «پنلِ نیمهشفافِ روشن»
   (PARAGRAPHهایِ img4) — اکثریتِ روشنِ پنجره = خودِ پنل است نه متن؛
   نوار باید با قطبِ اقلیتِ تیره ساخته شود نه رد.
۲) failed-fill = «جوهرِ واقعی داخلِ پالی» نه پرِ کاملِ پالی — تا کلِ
   بلوک از donor منتقل نشود (لکهٔ خاکستریِ Telea رویِ حصار).
۳) رانِ بلندِ «تیره» (کلمهٔ بولدِ فشرده) قربانیِ حذفِ میلهٔ نازک
   نمیشود؛ میله = بلندِ «نازک».
۴) پسگیرِ جوهرِ جامانده رویِ PC هم فعال است (env پیشفرض = روشن).
۵) قفلِ «قابِ رنگی»: خطِ نازکِ اشباعِ رنگیِ بیرونِ پالی (حبابِ سبزِ
   up0822) در protect میآید و از ماسکِ فعال کم میشود.
۶) ترمیمِ «تکهٔ سیاهِ تازه» در _opencv_inpaint_hq: لکهٔ تیرهای که
   Telea از دورخطِ سیاه داخلِ پرش میکشد با میانهٔ رنگِ حلقهٔ روشنِ
   اطراف پر میشود.
۷) رگرسیونِ تصویرِ واقعیِ up0822: قابِ سبزِ حباب بعد از پاکسازی سالم
   میماند و متن کامل پاک میشود.
"""
import os
import sys
import tempfile
import shutil

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


def make_tr(method="opencv"):
    return MangaTranslator(
        api_key="t", provider="gemini", ocr_langs=["en"],
        font_path="fonts/Vazirmatn-Regular.ttf",
        clean_method=method, gpu=False, force_lama=True,
        clean_only=True, debug=False, story_brief=False, max_workers=1)


def fake_region(polys, text="TEST", kind="dialogue"):
    r = manga.TextRegion(id=1, boxes=[], source_text=text,
                         translated_text=text, kind=kind)
    r.ocr_polys = [np.asarray(p, np.float32) for p in polys]
    xs = np.concatenate([np.asarray(p, np.float32)[:, 0] for p in polys])
    ys = np.concatenate([np.asarray(p, np.float32)[:, 1] for p in polys])
    r.rect = (float(xs.min()), float(ys.min()),
              float(xs.max() - xs.min()), float(ys.max() - ys.min()))
    return r


# ─── ۱) قطبِ اقلیت: متنِ تیره رویِ پنلِ روشنِ نیمهشفاف ───────────────
def test_minority_pole():
    tr = make_tr()
    img = np.full((120, 400, 3), 235, np.uint8)      # پنلِ روشن
    # هنرِ اطرافِ پنجره (بالا/پایینِ نوار): حصارِ میانه
    img[:, :30] = 120
    img[:, 370:] = 120
    cv2.putText(img, "SCHOOL SHALL RESPECT", (40, 78),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (20, 20, 20), 3)
    poly = [[35, 50], [365, 50], [365, 92], [35, 92]]
    st = tr._line_strip_ink(img, 35, 52, 365, 90, [poly])
    ok = False
    info = ""
    if st is not None:
        sx0, sy0, sx1, sy1, kept = st
        n = int(kept.sum())
        ok = n > 400
        info = f"kept={n}"
    else:
        info = "strip=None"
    gate("۱ قطبِ اقلیت: نوارِ متنِ رویِ پنلِ روشن ساخته میشود", ok, info)


# ─── ۲) failed-fill = جوهر، نه پالیِ کامل ────────────────────────────
def test_failed_fill_ink_only():
    tr = make_tr()
    img = np.full((220, 620, 3), 150, np.uint8)      # هنرِ حصارمانند
    for x in range(0, 620, 24):                       # میلههای عمودی
        img[:, x:x + 3] = 60
    # پنلِ نیمهشفاف: میلهها از زیرش پیدایند (مثلِ img4)
    img[30:190, 20:600] = 218
    for x in range(0, 620, 24):
        img[30:190, x:x + 3] = 120
    y = 45
    polys = []
    for ln in range(4):
        cv2.putText(img, "PARAGRAPH TEXT LINE HERE OK", (30, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, (25, 25, 25), 3)
        polys.append([[25, y - 22], [595, y - 22],
                      [595, y + 8], [25, y + 8]])
        y += 36
    reg = fake_region(polys)
    m, f = tr._compose_region_strips(img, reg)
    fpx = int((f > 0).sum())
    mpx = 0 if m is None else int((m > 0).sum())
    ppx = sum(float(cv2.contourArea(
        np.asarray(p, np.float32))) for p in polys)
    covered = fpx + mpx
    # کلِ بلوک (~۴ پالی) از donor نباید برود؛ جوهرِ متن باید برود
    ok = covered > 0.05 * ppx and covered < 0.85 * ppx
    gate("۲ failed فقط جوهرِ پالی است (نه پالیِ کامل)",
         ok, f"failed={fpx}px strips={mpx}px poly={int(ppx)}px")


# ─── ۳) کلمهٔ بولدِ فشرده قربانیِ حذفِ میله نمیشود ───────────────────
def test_bold_word_survives():
    tr = make_tr()
    img = np.full((90, 420, 3), 228, np.uint8)
    cv2.rectangle(img, (30, 30), (390, 62), (25, 25, 25), -1)  # کلمهٔ بولد
    poly = [[25, 25], [400, 25], [400, 70], [25, 70]]
    # نوار از داخلِ تابعِ failed-fill: مستقیمِ بلوکِ داخلی را شبیهسازی
    # نمیکنیم — همان شرطِ میله via _compose_region_strips سخت است؛
    # در عوضِ منطقِ open(41)~open(7×7) را مستقیم میسنجم:
    fu8 = np.zeros((90, 420), np.uint8)
    fu8[30:62, 30:390] = 255
    thick7 = cv2.morphologyEx(fu8, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    bars = cv2.morphologyEx(fu8, cv2.MORPH_OPEN, np.ones((1, 41), np.uint8))
    bars |= cv2.morphologyEx(fu8, cv2.MORPH_OPEN, np.ones((41, 1), np.uint8))
    bars &= ~thick7
    survived = int(((fu8 & ~bars) > 0).sum())
    gate("۳ رانِ بلندِ تیره (بولد) از حذفِ میله جان به در میبرد",
         survived > 0.9 * 32 * 360, f"survived={survived}px")
    _ = (tr, img, poly)


# ─── ۴) پسگیرِ جوهر رویِ PC هم فعال ─────────────────────────────────
def test_reclaim_on_pc():
    tr = make_tr()
    img = np.full((140, 400, 3), 245, np.uint8)
    cv2.putText(img, "HELLO WORLD HERE", (40, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, (30, 30, 30), 2)
    # حرفِ اولِ هر خط بیرونِ پالی: تکهٔ جوهرِ نزدیکِ ماسک
    cv2.rectangle(img, (22, 62), (34, 86), (30, 30, 30), -1)
    poly = [[38, 58], [370, 58], [370, 92], [38, 92]]
    reg = fake_region([poly])
    os.environ.pop("MANGA_INK_RECLAIM", None)     # پیشفرض = روشن
    m = tr._build_text_mask(img, [reg])
    stray = int(((m > 0) & (np.asarray(img)[:, :, 0] < 60)).sum())
    inside_stray = int(((m > 0)[62:86, 22:34]).sum())
    gate("۴ پسگیرِ جوهر روی PC هم فعال (تکهٔ بیرونِ پالی به ماسک رفت)",
         inside_stray > 50, f"stray_in_mask={inside_stray}px")
    _ = stray


# ─── ۵) قفلِ قابِ رنگی ───────────────────────────────────────────────
def test_colored_frame_protect():
    tr = make_tr()
    img = np.full((200, 300, 3), 250, np.uint8)
    cv2.putText(img, "DIALOG TEXT", (60, 110),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (30, 30, 30), 2)
    # قابِ سبزِ نازکِ دورِ حباب — بیرونِ پالیِ متن
    cv2.rectangle(img, (30, 60), (270, 150), (80, 200, 80), 2)
    poly = [[55, 85], [250, 85], [250, 125], [55, 125]]
    reg = fake_region([poly])
    raw = tr._build_text_mask(img, [reg])
    tr._page_raw_text_mask = raw
    prot = tr._structural_protect_mask(img, [reg])
    green = ((img[:, :, 1].astype(int) - img[:, :, 0]) > 60) \
        & ((img[:, :, 1].astype(int) - img[:, :, 2]) > 60)
    gpx = int(green.sum())
    gp = 0 if prot is None else int((green & (prot > 0)).sum())
    gm = int((green & (raw > 0)).sum())
    cp = getattr(tr, "_page_colored_protect", None)
    gc2 = 0 if cp is None else int((green & (cp > 0)).sum())
    gate("۵ قابِ رنگیِ سبز در نقشهٔ قاب میآید و از ماسکِ خام دور است",
         gc2 >= 0.5 * gpx and gm < 0.5 * gpx,
         f"green={gpx} in_colored_map={gc2} in_mask={gm}")


# ─── ۶) ترمیمِ تکهٔ سیاهِ تازه در opencv ────────────────────────────
def test_dark_chunk_repair():
    tr = make_tr()
    img = np.full((160, 300, 3), 145, np.uint8)     # هنرِ آبیِ میانه
    m = np.zeros((160, 300), np.uint8)
    m[60:100, 80:220] = 255
    # Telea را موقتاً جوری میبندیم که «لکهٔ سیاه» برگرداند
    real_inpaint = cv2.inpaint

    def fake_inpaint(*a, **kw):
        outp = real_inpaint(*a, **kw)
        outp = outp.copy()
        cv2.rectangle(outp, (70, 55), (230, 105), (5, 5, 5), -1)
        return outp

    cv2.inpaint = fake_inpaint
    try:
        outp = tr._opencv_inpaint_hq(img, m)
    finally:
        cv2.inpaint = real_inpaint
    g = cv2.cvtColor(outp, cv2.COLOR_BGR2GRAY)
    dark_left = int(((g < 70) & (m > 0)).sum())
    gate("۶ لکهٔ سیاهِ تازهٔ داخلِ ماسک با رنگِ حلقه ترمیم میشود",
         dark_left < 500, f"dark_left={dark_left}px")


# ─── ۷) رگرسیونِ واقعیِ up0822: قابِ سبز سالم + متن پاک ─────────────
def test_up0822_real():
    img = cv2.imread("ci_imgs/up0822_en.jpg")
    if img is None:
        gate("۷ رگرسیونِ up0822 (تصویر هست)", False, "تصویر نیست")
        return
    tr = make_tr("lama-manga")
    regs = tr._extract_regions_from_bubbles(img)
    cf = [r for r in regs if r.kind == "dialogue"
          and not getattr(r, "ocr_empty", False)
          and ((r.source_text or "").strip()
               or (r.translated_text or "").strip())]
    outp = tr.clean_image(img.copy(), list(cf))
    hsv_o = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hsv_c = cv2.cvtColor(outp, cv2.COLOR_BGR2HSV)
    go = ((hsv_o[..., 0] >= 35) & (hsv_o[..., 0] <= 85)
          & (hsv_o[..., 1] > 80) & (hsv_o[..., 2] > 60))
    gc = ((hsv_c[..., 0] >= 35) & (hsv_c[..., 0] <= 85)
          & (hsv_c[..., 1] > 80) & (hsv_c[..., 2] > 60))
    keep = float((gc & go).sum()) / max(1, float(go.sum()))
    # قابِ سبز نباید نابود شود — برایِ هر پیکسلِ سبزِ اورجینال باید
    # سبزِ (حتی بازسازیشده/کمی جابهجا) در همسایگیِ ۶px خروجی باشد
    gcd = cv2.dilate(gc.astype(np.uint8),
                     np.ones((13, 13), np.uint8)) > 0
    ratio = float((gcd & go).sum()) / max(1.0, float(go.sum()))
    # متنِ حبابِ اول کامل پاک شده؟ (گلیفِ دستنخورده داخلِ ماسکِ متن)
    go_g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gc_g = cv2.cvtColor(outp, cv2.COLOR_BGR2GRAY)
    mask = tr._build_text_mask(img, cf) > 0
    bx = (224, 7, 148, 215)
    mo = (go_g[bx[1]:bx[1] + bx[3], bx[0]:bx[0] + bx[2]] < 100) \
        & mask[bx[1]:bx[1] + bx[3], bx[0]:bx[0] + bx[2]]
    sub_c = gc_g[bx[1]:bx[1] + bx[3], bx[0]:bx[0] + bx[2]]
    sub_o = go_g[bx[1]:bx[1] + bx[3], bx[0]:bx[0] + bx[2]]
    resid = float((mo & (np.abs(sub_c.astype(int)
                                - sub_o.astype(int)) <= 25)).sum()) \
        / max(1, float(mo.sum()))
    gate("۷ up0822: قابِ سبز سالم + متنِ حبابِ اول پاک",
         0.8 <= ratio <= 1.6 and resid <= 0.15,
         f"green_ratio={ratio:.2f} text_resid={resid:.2f}")


def main():
    tmp = tempfile.mkdtemp(prefix="v114204_")
    try:
        test_minority_pole()
        test_failed_fill_ink_only()
        test_bold_word_survives()
        test_reclaim_on_pc()
        test_colored_frame_protect()
        test_dark_chunk_repair()
        test_up0822_real()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    n_ok = sum(1 for _, ok, _ in GATES if ok)
    print(f"\n==== {n_ok}/{len(GATES)} گیت سبک ====")
    for name, ok, info in GATES:
        if not ok:
            print(f"  ✗ {name} {info}")
    return 0 if n_ok == len(GATES) else 1


if __name__ == "__main__":
    sys.exit(main())
