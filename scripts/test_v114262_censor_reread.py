#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تستِ v1.14.262 — صافیِ [CENSORED] + پسگیرِ بازخوانیِ نجاتِ OCR.

بخش A: پاسخِ مترجم با [CENSORED]/انکار → ناحیه بیترجمه میماند؛
        ترجمهٔ واقعی بعدی می‌نشیند؛ بندِ ۶ِ پرامپت دیگر «SAFETY
        FALLBACK» نیست؛ یادداشتِ دورِ مجدد پای پرامپت می‌آید.
بخش B: نجاتِ OCR ناحیهٔ بی‌متنِ همپوشان با ناحیهٔ متن‌دار → رد
        (پوششِ پالی ≥۵۵٪ یا زیررشتهٔ متنِ مالکِ همپوشان).
"""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAILS = []


def check(name, cond, extra=""):
    tag = "OK " if cond else "FAIL"
    if not cond:
        FAILS.append(name)
    print(f"[{tag}] {name}" + (f" — {extra}" if extra and not cond else ""))


# ─── بارگذاریِ موتور (بدون OCR/دیتکتور) ───
import manga  # noqa: E402

MT = manga.MangaTranslator
TR = manga.MangaTranslator


class _R:
    """ناحیهٔ مینیمال برایِ تستِ ترجمه."""

    def __init__(self, rid, src, rect=(0, 0, 100, 40)):
        self.id = rid
        self.source_text = src
        self.translated_text = ""
        self.rect = list(rect)
        self.ocr_polys = []
        self.ocr_empty = False
        self.kind = "dialogue"
        self.bubble_style = ""


def _mk_translator():
    t = MT.__new__(MT)
    t.debug = True
    return t


# ═══ بخش A: صافیِ [CENSORED] ═══
t = _mk_translator()

# A1) شناساییِ جای‌نگهدارها
for bad in ("[CENSORED]", "censored", "**[CENSORED]**", "[REDACTED]",
            "I can't translate this.", "I'm sorry, but I can't help with that.",
            "نمی‌توانم این را ترجمه کنم", "[سانسور شد]", "***", "..."):
    check(f"A1 placeholder {bad[:28]!r}", TR._is_censored_translation(bad))

# A2) متنِ واقعی هرگز رد نمیشود
for good in ("اِی، فکر کنم تو این چند هفته اخیر یه مقدار چاق شدم.",
             "*دم عمیق*", "می‌گه نه؟", "Sorry for the wait!",
             "Ei, fekr konam chagh shodam."):
    check(f"A2 real {good[:26]!r}", not TR._is_censored_translation(good))

# A3) نشاندنِ پاسخ: [CENSORED] نمینشیند، بقیه می‌نشینند
regs = [_R(0, "Tsk, I think I've gained some weight."),
        _R(1, "*INHALE*"),
        _R(2, "ht doh op think, Puss?"),
        _R(3, "XHALE*")]
pages = [{"filename": "p1.png", "translations": [
    {"en_text": regs[0].source_text, "fa_text": "اِی، فکر کنم چاق شدم."},
    {"en_text": regs[1].source_text, "fa_text": "*دم عمیق*"},
    {"en_text": regs[2].source_text, "fa_text": "[CENSORED]"},
    {"en_text": regs[3].source_text, "fa_text": "I'm sorry, I can't translate that."},
]}]
n = TR._apply_mt_pages(t, pages, regs, {"p1.png": None} or None)
check("A3 applied=2 (فیک رد شد)", n == 2,
      f"applied={n}")
check("A3 r0 ترجمه نشد؟!", (regs[0].translated_text or "").strip() != "")
check("A3 r2 بیترجمه ماند ([CENSORED])",
      not (regs[2].translated_text or "").strip())
check("A3 r3 بیترجمه ماند (انکار)",
      not (regs[3].translated_text or "").strip())

# A4) خودِ دیالوگِ [CENSORED]دار = ترجمهٔ مجاز (بلیپِ عمدیِ مانگا)
r4 = _R(4, "F[CENSORED]! I'll kill you!")
pages4 = [{"filename": "p1.png", "translations": [
    {"en_text": r4.source_text, "fa_text": "[CENSORED]"}]}]
n4 = TR._apply_mt_pages(t, pages4, [r4], None)
check("A4 بلیپِ عمدیِ مانگا مینشیند",
      n4 == 1 and (r4.translated_text or "").strip() == "[CENSORED]")

# A5) بندِ ۶ِ پرامپت دیگر SAFETY FALLBACK نیست
proto = manga.MT_SYSTEM_PROTOCOL_ITEMS
check("A5 بندِ ۶ = RAW OCR / NO PLACEHOLDERS",
      "RAW OCR INPUT" in proto and "SAFETY FALLBACK" not in proto
      and "NEVER output placeholders" in proto)
check("A5 یادداشتِ دورِ مجدد موجود است",
      "RETRY NOTE" in TR._CENSOR_RETRY_NOTE)

print()
# ═══ بخش B: پسگیرِ بازخوانیِ نجاتِ OCR ═══
import numpy as np

# تصویرِ خالی (نجاتِ OCR بازگشتِ متن را شبیه‌سازی میکند — ما
# مستقیم رشتهٔ نجات را به گارد میدهیم)
img = np.full((600, 800, 3), 255, np.uint8)

# B1) سناریوی Green-Skin 27: ناحیهٔ بی‌متنِ همپوشان با ناحیهٔ
# متن‌دار — نجات «DIDN'T WE?» باید رد شود (زیررشتهٔ مالک)
owner = _R(3, "WE CAME ALL THIS WAY SO YOU COULD TEST YOUR FINDINGS, DIDN'T WE?",
           rect=(151, 3972 - 3900, 484, 204))
dup = _R(4, "", rect=(80, 4120 - 3900, 638, 169))
dup.ocr_empty = True
owner.ocr_polys = [
    np.array([[155, 3990], [630, 3990], [630, 4040], [155, 4040]], np.int32),
    np.array([[155, 4050], [630, 4050], [630, 4100], [155, 4100]], np.int32),
    np.array([[155, 4125], [630, 4125], [630, 4172], [155, 4172]], np.int32),
]
rescue_txt = "DIDN'T WE?"
blocked = TR._rescue_reread_blocked(t, dup, rescue_txt, [owner, dup])
check("B1 بازخوانیِ «DIDN'T WE?» رویِ ناحیهٔ همپوشان رد شد", blocked)

# B2) همان سناریو با پالیهایِ نجات (پوششِ ≥۵۵٪)
dup2 = _R(5, "", rect=(80, 4120 - 3900, 638, 169))
dup2.ocr_empty = True
rescue_polys = [
    np.array([[160, 4130], [620, 4130], [620, 4168], [160, 4168]], np.int32),
]
blocked2 = TR._rescue_reread_blocked(
    t, dup2, "DIDN'T WE?", [owner, dup2], polys=rescue_polys)
check("B2 پوششِ پالیِ ≥۵۵٪ → رد", blocked2)

# B3) یتیمِ واقعی (بیرونِ همهٔ نواحی، بدونِ همپوشانی) رد نمیشود
orphan = _R(6, "", rect=(50, 500, 300, 60))
orphan.ocr_empty = True
blocked3 = TR._rescue_reread_blocked(
    t, orphan, "OUTER GOD'S WHISPER", [owner, dup, orphan],
    polys=[np.array([[60, 510], [290, 510], [290, 550], [60, 550]], np.int32)])
check("B3 یتیمِ واقعی زنده ماند (رد نشد)", not blocked3)

# B4) دو حبابِ جدا با متنِ یکسان («REALLY?») — رد نشود (بدونِ همپوشانی)
a = _R(7, "REALLY?", rect=(32, 100, 336, 223))
b = _R(8, "", rect=(400, 300, 200, 80))
b.ocr_empty = True
blocked4 = TR._rescue_reread_blocked(
    t, b, "REALLY?", [a, b],
    polys=[np.array([[410, 310], [590, 310], [590, 370], [410, 370]], np.int32)])
check("B4 حبابِ جدای هم‌نام رد نشد", not blocked4)

print()
print("═" * 46)
if FAILS:
    print(f"✗ {len(FAILS)} تست قرمز:")
    for f in FAILS:
        print("   -", f)
    sys.exit(1)
print("✓ همهٔ تستها سبز است.")
