#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تستِ ریسِسِ v1.14.229 — «عکس دوم یا سوم بیشترِ وقتا ترجمه نمیشه رد
میکنه».

ریشه (اثباتشده با لاگِ گوشیِ v1.14.227): در K3 بینِ نوشتنِ
extracted_map[i] و صفشدنِ دیالوگهایش (_queue_dialogues →
pending_by_page[i]>0) پنجرهٔ چندثانیهایِ باز است (_rescue_empty_ocr_1149
همان‌جا OCRِ نجات میزند). اگر کارگرِ استخراجِ «دیگر» در همین پنجره
_finish_ready_pages بزند، صفحه با pending=0 و clean-ready «کامل» حساب
میشود → رندرِ نهایی با صفر ترجمه → image از extracted_map حذف میشود →
دیگر هرگز دوباره رندر نمیشود («[!] ۷ حباب ترجمه نشد» قبل از شروعِ
بستههایِ ترجمه — عکسِ ۲/۳ فصل انگلیسی میماند).

این تست همان پنجره را «قطعی» باز میکند (نجاتِ OCR = sleep طولانی) تا هر
دو کارگرِ استخراج همزمان داخلِ پنجره باشند و کارگرِ زودتر بیدارشده
_finish_ready_pages بزند. گیت: هر فراخوانِ نهایی (final=True) که ناحیهٔ
بامتنِ حرفی دارد باید «همهٔ» ناحیه‌هایش ترجمه داشته باشند.

کاربرد:  python3 scripts/test_v114229_race.py [ci_imgs_dir]
با کدِ قدیم (قبل از گاردِ _qd_inflight) باید قرمز شود؛ با ۲۲۹ سبز.
"""
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import manga  # noqa: E402

# ── فصلِ کوچکِ واقعی: ۳ صفحهٔ سبک (کاور جدا + نوارِ دوتایی → ۲ کارگر) ──
CI = sys.argv[1] if len(sys.argv) > 1 else "ci_imgs"
SRC = [
    os.path.join(CI, "img7.jpg"),                # کاور (~۲۴ث استخراج)
    os.path.join(CI, "up0904_en.jpg"),           # متنِ انگلیسیِ واقعی
    os.path.join(CI, "IMG_20260929_025420_921.jpg"),
]
for p in SRC:
    if not os.path.isfile(p):
        print(f"✘ ورودی نیست: {p}")
        sys.exit(2)

WORK = "/tmp/t229_race"
shutil.rmtree(WORK, ignore_errors=True)
os.makedirs(f"{WORK}/in")
for p in SRC:
    shutil.copy(p, f"{WORK}/in")

# ── ۱) پنجرهٔ مرگِ قطعی: نجاتِ OCR = sleep ──
_orig_rescue = manga.MangaTranslator._rescue_empty_ocr_1149


def _slow_rescue(self, image, regions, *a, **k):
    time.sleep(12.0)  # هر دو کارگر همزمان داخلِ پنجره میمانند
    try:
        return _orig_rescue(self, image, regions, *a, **k)
    except Exception:
        return None


manga.MangaTranslator._rescue_empty_ocr_1149 = _slow_rescue

# ── ۲) جاسوس: هر فراخوانِ finish_page_phase ثبت میشود ──
_orig_fpp = manga.MangaTranslator.finish_page_phase
CALLS = []
# روی کدِ قدیمِ (<۲۲۹) source_has_letters نیست — فالبکِ معادل
_shl = getattr(manga, "source_has_letters", None) or \
    (lambda t: any(c.isalpha() for c in str(t or "")))


def _spy_fpp(self, image, regions, *a, **k):
    try:
        n_src = sum(1 for r in regions if _shl(r.source_text or ""))
        n_tr = sum(1 for r in regions
                   if (r.translated_text or "").strip())
        CALLS.append({"n": len(regions), "n_src": n_src, "n_tr": n_tr,
                      "final": bool(k.get("final")),
                      "skip": bool(k.get("skip_translate"))})
    except Exception:
        CALLS.append({"err": True})
    return _orig_fpp(self, image, regions, *a, **k)


manga.MangaTranslator.finish_page_phase = _spy_fpp

# ── ۳) رانِ واقعیِ K3 با fake-translate ──
tr = manga.MangaTranslator(
    api_key=["dummy"], provider="gemini", ocr_langs=["en"],
    font_path="fonts/Sahel-Bold.ttf", reading_order="rtl", gpu=False,
    clean_method="opencv", det_confidence=0.16, min_confidence=0.12,
    two_pass_ocr=False, img_format="jpg", fake_translate=True,
    debug=False,
)
t0 = time.time()
import io as _io
import contextlib
_log229 = _io.StringIO()
try:
    with contextlib.redirect_stdout(_log229):
        tr.run(f"{WORK}/in", f"{WORK}/out", resume=False)
finally:
    manga.MangaTranslator._rescue_empty_ocr_1149 = _orig_rescue
    manga.MangaTranslator.finish_page_phase = _orig_fpp
print(f"\n— رانِ K3 در {time.time() - t0:.0f}s —")
LOG229 = _log229.getvalue()

# ── ۴) گیت‌ها ──
FAILS = []


def gate(cond, msg):
    print(("[✓] " if cond else "[✗] ") + msg)
    if not cond:
        FAILS.append(msg)


outs = [f for f in os.listdir(f"{WORK}/out")
        if f.lower().endswith((".jpg", ".png", ".webp"))] \
    if os.path.isdir(f"{WORK}/out") else []
gate(len(outs) >= 2, f"خروجیها: {len(outs)} (کاور+نوار)")

finals = [c for c in CALLS if c.get("final") and not c.get("err")]
gate(len(finals) >= 2, f"فراخوانهایِ نهایی: {len(finals)} (پیشنمایشها جدا)")

for i, c in enumerate(finals):
    gate(c["n_tr"] >= c["n_src"],
         f"نهاییِ {i + 1}: {c['n_tr']}/{c['n_src']} ناحیهٔ بامتن ترجمه دارند"
         + ("" if c["n_tr"] >= c["n_src"] else "  ← ریسِس! صفحه بیترجمه رندر شد"))

raced = [c for c in finals if c["n_src"] > 0 and c["n_tr"] < c["n_src"]]
gate(not raced, f"هیچ صفحهٔ نهایی بیترجمه نماند (ریسِسها: {len(raced)})")

# گیتِ لاگِ خودِ موتور — همان خطی که لاگِ گوشیِ سازنده داشت (۷ حباب)
_n_untr = LOG229.count("حباب ترجمه نشد")
gate(_n_untr == 0,
     f"خطِ «حباب ترجمه نشد» در کلِ ران: {_n_untr}"
     + ("  ← ریسِسِ ۲۲۹ (لاگِ گوشی: ۷ حباب)" if _n_untr else ""))

print(f"\n═══ race-test: {'سبز ✓' if not FAILS else 'قرمز ✗ (' + str(len(FAILS)) + ')'} ═══")
sys.exit(1 if FAILS else 0)
