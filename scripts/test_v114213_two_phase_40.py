#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""گیت‌های نسخهٔ 1.14.213 — دو-فازیِ استخراج→ترجمهٔ ۴۰تایی + پسگیریِ خالی‌ها
+ پولیشِ شبحِ نوار + گاردِ رنگِ پسگیر + گیتِ زاویهٔ ادعایی.

دستورهای سازنده:
  «وقتی داره استخراج میکنع همزمان داره از ai ترجمه میگیره من میخوام همه
  متن هارو جمع کنه استخراج تموم شد بعدش بره ترجمه ۴۰ تا ۴۰ تا بده
  ترجمش کنه»
  + «اگ متنی خالی برگشت به لیست جدید اضافه کنه 30 تا شد مجدد بره ترجمه
  باید درست برگرونه بزاره سرجاش ست کنه به عکس هاشون»
  + «بعد چرخش همچین بعضی متن ها درست نمیچرخه»
  + «نه لگه سیاهی نه لگه سفیدی یا هرنگی لگه بشه قبول نمیکنم»
"""
import os
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
gate("APP_VER = 1.14.213", 'APP_VER = "1.14.213"' in src)
ver = open(os.path.join(os.path.dirname(__file__), "..", "VERSION"),
           encoding="utf-8").read()
gate("VERSION = 1.14.213", "versionName=1.14.213" in ver
     and "versionCode=217" in ver)
grad = open(os.path.join(os.path.dirname(__file__), "..",
                         "android", "app", "build.gradle.kts"),
            encoding="utf-8").read()
gate("gradle = 1.14.213/217", 'versionName = "1.14.213"' in grad
     and "versionCode = 217" in grad)

# ── ۲) بستهٔ ۴۰تایی (دستور: «۴۰ تا ۴۰ تا بده ترجمش کنه») ──
cap_n, cap_c = manga._one_request_caps()
gate("سقفِ پیشفرضِ بسته = ۴۰", cap_n == 40)
gate("سقفِ نویسه = ۱۰۰۰۰", cap_c == 10000)


class _R:  # آیتمِ ساختگی با متن
    def __init__(self, t):
        self.source_text = t


items = [_R("x" * 20) for _ in range(130)]
sizes = [len(g) for g in manga._split_one_request_batches(items, 40, 10000)]
gate("۱۳۰ دیالوگ → هیچ بستهای زیرِ ۴۰ نیفتد (۴۴/۴۳/۴۳)",
     sizes == [44, 43, 43])
items = [_R("x" * 20) for _ in range(35)]
sizes = [len(g) for g in manga._split_one_request_batches(items, 40, 10000)]
gate("۳۵ دیالوگ → یک بستهٔ واحدِ ۳۵تایی", sizes == [35])
items = [_R("x" * 500) for _ in range(80)]
sizes = [len(g) for g in manga._split_one_request_batches(items, 40, 10000)]
gate("سدِ نویسه: ۸۰×۵۰۰ → ۴ بستهٔ ۲۰تایی", sizes == [20, 20, 20, 20])

# ── ۳) سدِ دو-فازی: هیچ ترجمه‌ای قبل از اتمامِ استخراج ──
gate("پرچمِ _extraction_done در سازنده (پیشفرض True)",
     "self._extraction_done = True" in src)
gate("run(): ریستِ پرچم در شروع", "self._extraction_done = False" in src)
gate("run(): مرزِ صریح بعد از join کارگرها",
     "[✓] استخراجِ همهٔ" in src
     and src.find("_t_bwd.join()") < src.find("[✓] استخراجِ همهٔ"))
gate("لاگِ مرز: «حالا ترجمهٔ … شروع میشود»",
     "شروع میشود…" in src)
gate("سدِ ۱۹۳ در فازِ استخراج قفل (skip وقتی extraction not done)",
     "and getattr(self, \"_extraction_done\", True)):" in src)
gate("زنگِ رگرسیون در translate_regions",
     "رگرسیونِ دو-فازی" in src)
# ترتیبِ واقعی: فلشِ نهایی بعد از join، نه در حلقهٔ استخراج
i_flush_def = src.find("def _flush_translate_buffer")
i_queue = src.find("def _queue_dialogues")
i_join = src.find("_t_bwd.join()")
i_flush_call = src.find("_flush_translate_buffer(force=True)")
gate("فلاشِ ترجمه فقط بعد از joinِ استخراج (نه میانهٔ کار)",
     0 < i_flush_def < i_queue < i_join < i_flush_call)

# ── ۴) پسگیریِ خالیهایِ AI (۳۰تا۳۰تا + رندرِ دوباره) ──
gate("تابعِ جمعِ خالیها", "def _collect_empty_dialogues" in src)
gate("سقفِ بستهٔ پسگیری = ۳۰ (MANGA_EMPTY_RETRY_MAX)",
     "MANGA_EMPTY_RETRY_MAX\", \"30\"" in src)
gate("رندرِ دوبارهٔ صفحهٔ پسگیری‌شده",
     "def _rerender_page_after_empty" in src)
gate("لاگِ پسگیری", "پسگیریِ خالیهایِ AI" in src)
gate("نقشهٔ «صفحه → فایلِ ورودی» برایِ رندرِ دوباره",
     "_src_of_page" in src)

# ── ۵) پولیشِ شبحِ نوار (لکهٔ متنِ قبلی داخلِ نوارها) ──
gate("متدِ _strip_ghost_polish", "def _strip_ghost_polish" in src)
gate("فراخوانی بعد از کامپوزِ نهایی (قراردادِ دو-عکسی)",
     src.find("cleaned = self._compose_polish(image, cleaned, _cmp2)")
     < src.find("self._strip_ghost_polish("))
gate("فقطِ شبحِ محو (کنتراستِ ۲۲..۶۰ — هنرِ تیره دست نمیخورد)",
     "(_d213 > 22) & (_d213 < 60)" in src)
gate("گیتِ باندِ لبهٔ نوار (تراسِ LaMa)، نه ضربههایِ وسطِ نوار",
     "_edge213" in src and "(_eb213 & _edge213).any()" in src)
gate("کلیدِ خاموشکردنِ دستی (MANGA_GHOST_POLISH=0)",
     'MANGA_GHOST_POLISH", "1") != "0"' in src)

# آزمونِ عملکردیِ پولیش رویِ تصویرِ ساختگی
img = np.full((300, 500, 3), 240, np.uint8)
for i in range(4):  # جوهرِ واقعیِ خط + شبحِ محوِ ۲px پایینش
    y = 40 + i * 55
    cv2.putText(img, "TEXT LINE HERE", (60, y + 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (30, 30, 30), 2,
                cv2.LINE_AA)
    cv2.line(img, (62, y + 30), (230, y + 30), (205, 205, 205), 2)  # شبح
mask = np.zeros((300, 500), np.uint8)
for i in range(4):
    y = 40 + i * 55
    mask[y - 4:y + 36, 54:438] = 255
mt = manga.MangaTranslator.__new__(manga.MangaTranslator)
mt.debug = False
clean = img.copy()
# جوهرِ متن در خروجیِ «پاکشده» نیست؛ فقط شبحِ محو مانده است
clean[:] = 240
for i in range(4):
    y = 40 + i * 55
    cv2.line(clean, (62, y + 30), (230, y + 30), (205, 205, 205), 2)
out, nfix = mt._strip_ghost_polish(img, clean, mask)
gate("پولیشِ عملکردی: شبحِ ۲px داخلِ نوار پر میشود", nfix >= 4)
g_in = cv2.cvtColor(clean, cv2.COLOR_BGR2GRAY).astype(np.int16)
g_out = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY).astype(np.int16)
before = int(((240 - g_in) > 25).sum())
after = int(((240 - g_out) > 25).sum())
gate("جوهرِ محوِ داخلِ نوار بعد از پولیش کم شده",
     after < before and after <= before // 3)

# ── ۶) گاردِ رنگِ پسگیر (SFX/هنرِ همسایه پاک نشود) ──
gate("گاردِ رنگ در پسگیرِ جوهر", "_seed_h213" in src
     and "MANGA_RECLAIM_COLORGUARD" in src)
gate("آستانهٔ قوی: فقط قطعهٔ اشباعِ ≥۱۲۰ با متنِ بی‌رنگ",
     "_phs213 > 120.0 and _seed_s213 < 45.0" in src)
gate("آستانهٔ هیو: فقط اختلافِ ≥۷۰ درجه بینِ دو رنگِ اشباع",
     "_hue_d213 > 70.0" in src)

# ── ۷) گیتِ زاویهٔ ادعایی (چرخشِ به‌غلط-صفرشده) ──
gate("متدِ _ink_slant_support", "def _ink_slant_support" in src)
gate("گیتِ ≥۱٫۱۰ برایِ نجاتِ زاویه از وتو (استخراج)",
     "_sup213 >= 1.10" in src)
gate("گیتِ ≥۱٫۱۰ در رندر هم",
     "_sup213r >= 1.10" in src)

# آزمونِ عملکردی: متنِ کجِ واقعی در برابرِ متنِ صاف
sl = np.full((120, 500, 3), 245, np.uint8)
font = cv2.FONT_HERSHEY_SIMPLEX
for i, word in enumerate(["SLANTED", "TEXT", "LINE", "HERE"]):
    x = 30 + i * 110
    y = int(80 + np.tan(np.radians(-15)) * x)
    cv2.putText(sl, word, (x, y), font, 1.2, (20, 20, 20), 3, cv2.LINE_AA)
fl = np.full((120, 500, 3), 245, np.uint8)
for i, word in enumerate(["FLAT", "TEXT", "LINE", "HERE"]):
    cv2.putText(fl, word, (30 + i * 110, 70), font, 1.2, (20, 20, 20), 3,
                cv2.LINE_AA)
s_slant = manga.MangaTranslator._ink_slant_support(sl, -15.0)
s_flat = manga.MangaTranslator._ink_slant_support(fl, -15.0)
gate(f"متنِ کج: پشتیبانیِ زاویهٔ واقعی ≥۱٫۱۰ ({s_slant:.2f})",
     s_slant is not None and s_slant >= 1.10)
gate(f"متنِ صاف: زاویهٔ کاذب رد میشود <۱٫۱۰ ({s_flat:.2f})",
     s_flat is not None and s_flat < 1.10)

# ── ۸) نجاتِ عضو-به-عضوِ گروهِ ردشدهٔ LaMa (به‌جایِ پرِ تختِ کل) ──
gate("پرِ عضو-به-عضو با Telea در نجات",
     "cv2.INPAINT_TELEA" in src and "پرِ عضو-به-عضویِ نجات" in src)

# ── ۹) متنِ لاگِ مرجع با ۴۰تا۴۰تا ──
gate("بنرِ مرجع: «ترجمهٔ ۴۰تا۴۰تایِ پشتسرهم»",
     "ترجمهٔ ۴۰تا۴۰تایِ" in src and "پشتسرهم" in src)
gate("بنرِ قدیمیِ ۳۰تا۳۰تا حذف شد (در متنهایِ جدید)",
     "ترجمهٔ ۳۰تا۳۰تایِ" not in src)

print()
print(f"نتیجه: {OK} سبز / {BAD} مردود")
sys.exit(1 if BAD else 0)
