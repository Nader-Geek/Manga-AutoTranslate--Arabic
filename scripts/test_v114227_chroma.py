#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.14.227 — تست واحدِ QCِ کروما + گاردِ پاکسازیِ یک‌باره.

دستورِ سازنده (لاگِ گوشیِ v1.14.226 + پیام): «پاکسازیش تو گوشی بدتره یک
کم قسمت چپ بالا دوتا متن هست کنار هم اومده با حباب داخل به بیرون رنگ
زده بعد چرا حس میکنم دو بار استخراج میزنه؟ و سه بار میپاکه؟»

(۱) QCِ کروما (_lama_group_finish / [🛡227]): همهٔ QCهایِ ضدتوهم خاکستری
    بودند؛ پرِ «روشنِ زرد» LaMaِ گوشی رویِ حبابِ سفیدِ همپوشان با حبابِ
    زرد از همه رد میشد. تستِ سینتتیکِ مستقیم روی _lama_group_finish:
    - کیسِ زرد-روی-سفید → باید رد و با TELEAیِ محلی سفید شود ([🛡227])
    - کیسِ پرِ درستِ سفید → هیچ دخالتی نباید بشود
    - کیسِ حلقهٔ مخلوطِ سفید+زرد (مرزِ دو حباب) → گاردِ std باید ردش
      کند (هنر/مرز قانونی قربانی نشود)
    - کیسِ گرادیانِ ملایمِ خاکستری → نباید تریگر شود
(۲) گاردِ پاکسازیِ یک‌باره (مرجع): ادعایِ اتمیک + پرشِ precleaned —
    سورس-تست روی ساختارِ _clean_one_page/فاز۱/فاز۲ (رفتارِ مسابقه فقط
    رویِ گوشی/شبیهسازِ اندروید به‌طورِ قطعی رخ میدهد؛ CIِ اندروید آن را
    میسنجد).
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import contextlib  # noqa: E402
import numpy as np  # noqa: E402

os.environ.setdefault("MANGA_ORPHAN_RESCUE", "0")

import manga  # noqa: E402  (بارگذاریِ سنگین — فقط یک بار)

PASS = 0
FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [✓] {name}")
    else:
        FAIL += 1
        print(f"  [✗] {name} {extra}")


# ── (۱) QCِ کروما رویِ _lama_group_finish ───────────────────────────────
def _make_translator():
    t = object.__new__(manga.MangaTranslator)
    t.debug = False
    return t


def _run_finish(page_img, line_box, fill_bgr, pad_kernel=(5, 5)):
    """یک عضو (خطِ متن) رویِ صفحه میسازد، پرِ LaMa را با fill_bgr
    شبیهسازی میکند و _lama_group_finish واقعی را صدا میزند.
    خروجی: (لاگِ چاپشده، نتیجهٔ عضو c[5]، ماسکِ عضو c[4])"""
    import cv2
    x0, y0, x1, y1 = line_box
    sub = page_img[y0:y1, x0:x1]
    gray = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
    crop_msk = ((gray < 100) * 255).astype(np.uint8)
    if int(crop_msk.sum()) < 200 * 255:
        # جوهرِ کافی نیست — سناریوی بی‌معنا
        return None, None, None
    members = [[x0, y0, x1, y1, crop_msk, None, None]]
    t = _make_translator()
    page_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, pad_kernel)
    ctx = t._lama_group_prep(page_img, members, page_kernel)
    if ctx is None:
        return None, None, None
    sub_bgr = ctx["crop_img"].copy()
    sub_bgr[ctx["crop_msk"] > 0] = fill_bgr
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        t._lama_group_finish(members, ctx, sub_bgr, page_kernel)
    res = None if members[0][5] is None else members[0][5].copy()
    msk = None if members[0][4] is None else (members[0][4] > 0)
    return buf.getvalue(), res, msk


def _median_color(res, msk):
    if res is None or msk is None or not msk.any():
        return None
    return np.median(res[msk].astype(np.float32), axis=0)


def test_chroma():
    import cv2
    print("== (۱) QCِ کروما ==")
    H = W = 460

    # ── کیسِ ۱: حبابِ سفید + ناحیهٔ زردِ همسایه؛ LaMa زرد پر کرده ──
    img = np.full((H, W, 3), 255, np.uint8)
    img[:, 330:, :] = (0, 235, 255)          # حبابِ زرد در راست
    cv2.rectangle(img, (80, 200), (240, 240), (25, 25, 25), -1)  # متن
    yellow = (0, 255, 255)                    # پرِ غلطِ LaMa (روشن — از QC تیره رد میشود)
    log, res, msk = _run_finish(img, (70, 190, 250, 250), yellow)
    check("کیسِ زرد: عضو واردِ اعتبارسنجی شد", res is not None,
          "(لاگ خالی — گاردهای زودهنگام ردش کردند)")
    if res is not None:
        med = _median_color(res, msk)
        check("کیسِ زرد: [🛡227] چاپ شد", "🛡227" in (log or ""),
              f"log={log!r}")
        # B باید به سفیدِ حلقه برگردد (≥۲۰۰) نه زردِ ۰
        check("کیسِ زرد: پر با رنگِ حلقه (سفید) ترمیم شد — B کانال",
              med is not None and med[0] >= 200.0,
              f"median={med}")
        d = float(np.max(np.abs(med - np.array([255.0, 255.0, 255.0])))) \
            if med is not None else 999.0
        check("کیسِ زرد: فاصلهٔ رنگی از سفید ≤ ۶۰", d <= 60.0, f"Δ={d:.0f}")

    # ── کیسِ ۲: پرِ «درستِ» سفید — هیچ دخالتی نباید بشود ──
    img2 = np.full((H, W, 3), 255, np.uint8)
    cv2.rectangle(img2, (80, 200), (240, 240), (25, 25, 25), -1)
    log2, res2, msk2 = _run_finish(img2, (70, 190, 250, 250),
                                   (252, 252, 252))
    check("کیسِ سفیدِ درست: بدونِ [🛡227]", "🛡227" not in (log2 or ""))
    med2 = _median_color(res2, msk2)
    check("کیسِ سفیدِ درست: پر سفید ماند",
          med2 is not None and float(np.max(np.abs(
              med2 - np.array([252.0, 252.0, 252.0])))) <= 12.0,
          f"median={med2}")

    # ── کیسِ ۳: خطِ بلند از سفید تا زرد (دو پنجره: یکی سمتِ سفیدِ
    # تمیز = لنگرِ دورِ ۱، یکی مرزی = سرایت) — پرِ هارمونیک باید مرز را
    # حفظ کند (سمتِ زردِ ماسک زرد بماند، سفید سفید) ──
    img3 = np.full((H, W, 3), 255, np.uint8)
    img3[:, 260:, :] = (0, 235, 255)
    cv2.rectangle(img3, (100, 200), (330, 240), (25, 25, 25), -1)
    log3, res3, msk_3 = _run_finish(img3, (90, 190, 340, 250), yellow)
    if res3 is not None and msk_3 is not None:
        # پنجرهٔ عضو: x محلی 0..250 → صفحه 90..340؛ مرزِ زرد = صفحه 260
        loc = res3.copy()
        mm3 = msk_3
        right = mm3.copy()
        right[:, :160] = False    # سمتِ زردِ صفحه (ستون ≥ 160 محلی)
        left = mm3.copy()
        left[:, 160:] = False    # سمتِ سفیدِ صفحه
        if right.any() and left.any():
            rb = float(np.median(loc[right][:, 0]))
            lb = float(np.median(loc[left][:, 0]))
            check("کیسِ مرزی: سمتِ زرد زرد ماند (B<160)",
                  rb < 160.0, f"B={rb:.0f}")
            check("کیسِ مرزی: سمتِ سفید سفید ماند (B>200)",
                  lb > 200.0, f"B={lb:.0f}")
        else:
            check("کیسِ مرزی: ماسکِ دوطرفه ساخته شد", False)
    else:
        check("کیسِ مرزی: عضو پردازش شد", False)

    # ── کیسِ ۴: گرادیانِ ملایمِ خاکستری — پرِ همرنگِ گرادیان ──
    img4 = np.zeros((H, W, 3), np.uint8)
    for yy in range(H):
        v = int(150 + 80 * yy / H)
        img4[yy, :, :] = (v, v, v)
    cv2.rectangle(img4, (80, 200), (240, 240), (25, 25, 25), -1)
    log4, res4, msk4 = _run_finish(img4, (70, 190, 250, 250),
                                   (178, 178, 178))
    check("کیسِ گرادیان: بدونِ [🛡227]", "🛡227" not in (log4 or ""))


# ── (۲) گاردِ پاکسازیِ یک‌بارهٔ مرجع — سورس-تست ──────────────────────────
def test_double_clean_source():
    print("== (۲) گاردِ پاکسازیِ یک‌باره (مرجع) ==")
    src = open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
    check("clean_claimed تعریف شد",
          "clean_claimed: set = set()" in src)
    check("_clean_one_page امضای bool دارد",
          "def _clean_one_page(_p: int) -> bool:" in src)
    check("ادعایِ اتمیک زیرِ قفل",
          "clean_claimed.add(_p)" in src
          and "if _p in clean_claimed:" in src)
    check("پرشِ صفحهٔ دارایِ precleaned",
          "if _pc is not None:" in src and
          "# فازِ دیگر پاک کرده — precleaned آماده است" in src)
    check("آزادسازیِ ادعا در finally",
          "clean_claimed.discard(_p)" in src and "finally:" in src)
    check("فازِ ۱ فقط با پایانِ کارِ خودش علامت میزند",
          "if _clean_one_page(pi):" in src)
    check("فازِ ۲ فقط با پایانِ کارِ خودش علامت میزند",
          "if _clean_one_page(_p):" in src)
    check("خروجیِ نهاییِ _did227",
          "return _did227" in src)
    # سازگاری: هیچ فراخوانِ بی‌شرطِ _clean_done_mark بعد از _clean_one_page نماند
    bad = ("_clean_one_page(pi)\n                _clean_done_mark(pi)"
           in src) or ("_clean_one_page(_p)\n                _clean_done_mark(_p)"
                       in src)
    check("فراخوانِ بی‌شرطِ قدیمی حذف شد", not bad)


if __name__ == "__main__":
    test_chroma()
    test_double_clean_source()
    print(f"\n{'='*46}\nنسخهٔ {_v if False else ''}v1.14.227: "
          f"{PASS} سبز / {FAIL} قرمز")
    sys.exit(1 if FAIL else 0)
