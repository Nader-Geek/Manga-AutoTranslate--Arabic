#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v1.14.202 — واترمارکِ رویِ حباب (گزارشِ سازنده: «هنوزم این دوتا استخراج نمیشه
با این ک زبان انگلیسی گذاشتم و هست» — فصلِ ۱۱۰ Cosmic Heavenly Demon، دو اسکرین‌شاتِ
صفحهٔ آخر + لاگِ v1.14.200/201):

ریشه — نه OCR بود نه detector: هر دو حباب باکس خورده بودند و rapidocr متنشان را
خوانده بود؛ ولی واترمارکِ «LIKEMANGA.INK» که «رویِ» حباب افتاده داخلِ متنِ OCR
میآمد («IT'S EASY, LIKEMANGA.INK BECAUSE…» / «…OR IN MY DREAMS...LIKEMANGA.INK»)
→ DOMAIN_RE کلِ ناحیه را promo میکرد → ازش رد میشد (نه پاکسازی، نه ترجمه).

فیکس — بعدِ برداشتنِ توکنهایِ واترمارک/دامنه، اگرِ باقیِ متن هنوز دیالوگِ واقعی
است (≥۳ واژهٔ مصوتدار و بدونِ نشانهٔ تبلیغِ باقی‌مانده) → دیالوگ؛ و واترمارک از
متنِ ترجمه هم برداشته میشود. بنرهایِ تبلیغِ واقعی (شاملِ عبارتِ تبلیغ بعد از
برداشتنِ دامنه) همان‌طور promo میمانند.

گیتها:
  ۱) دو متنِ واقعیِ فصلِ ۱۱۰ → dialogue (نجات)
  ۲) متنِ دیالوگِ عادی بدونِ واترمارک دستنخورده (رگرسیون)
  ۳) بنرهایِ واقعیِ لاگ (کریدیت/تبلیغ) همچنان promo
  ۴) واترمارکِ تنها همچنان promo
  ۵) _strip_watermark_tokens کارکردی
  ۶) نسخه
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import manga  # noqa: E402

_cls = manga.MangaTranslator._classify_text
_strip = manga.MangaTranslator._strip_watermark_tokens
_ddw = manga.MangaTranslator._dialogue_despite_watermark

_gates = []
_ok = True


def gate(name, cond):
    global _ok
    _gates.append((name, bool(cond)))
    if not cond:
        _ok = False
        print(f"  [✗] {name}")
    else:
        print(f"  [✓] {name}")


# ── ۱) دو متنِ واقعیِ فصلِ ۱۱۰ (عینِ لاگ) → دیالوگ ─────────────────────────
T1 = ("IT'S EASY, LIKEMANGA.INK BECAUSE I WON'T DESPERATELY WISH DEFEND MYSELF. "
      "I FOR IT, TOO. JUST AS THE HEAVENLY DEMON SOUL DID..!!")
T2 = "I'M CERTAIN. IT'S NOWHERE IN MY SOUL... OR IN MY DREAMS...LIKEMANGA.INK"

gate("T1 «IT'S EASY…+LIKEMANGA.INK» → dialogue", _cls(T1) == "dialogue")
gate("T2 «I'M CERTAIN…+LIKEMANGA.INK» → dialogue", _cls(T2) == "dialogue")
gate("T1 _dialogue_despite_watermark", _ddw(T1) is True)
gate("T2 _dialogue_despite_watermark", _ddw(T2) is True)
gate("T1 پاکسازی: LIKEMANGA از متنِ ترجمه میرود",
     "LIKEMANGA" not in _strip(T1).upper() and "BECAUSE" in _strip(T1).upper())
gate("T2 پاکسازی: LIKEMANGA میرود، DREAMS میماند",
     "likemanga" not in _strip(T2).lower() and "DREAMS" in _strip(T2).upper())
gate("DDW: دامنهٔ تنها → دیالوگ نیست", _ddw("LIKEMANGA.INK") is False)
gate("DDW: بنرِ تبلیغِ واقعی → دیالوگ نیست",
     _ddw("DEAR READERS, DIVE DEEPER INTO THE STORY ON VORTEXSCANS.ORG!") is False)

# ── ۲) رگرسیون: دیالوگِ عادی ────────────────────────────────────────────────
gate("دیالوگِ عادی «WHY HAVE YOU COME...?» → dialogue",
     _cls("WHY HAVE YOU COME...?") == "dialogue")
gate("دیالوگِ عادی «AWAKEN ONCE MORE. ...SLAVE WILL» → dialogue",
     _cls("AWAKEN ONCE MORE. ...SLAVE WILL") == "dialogue")
gate("جملهٔ دیالوگی که اسمِ سایت را «ذکر میکند» → dialogue (باقیِ متنِ واقعی)",
     _cls('"THE GREATEST ESTATE DEVELOPER" THE WEBTOON IS A STORY OF A NOBLE') == "dialogue")

# ── ۳) بنرهایِ واقعیِ لاگ همچنان promo ─────────────────────────────────────
promos = [
    "READ THIS SERIES FIRST AT: VORTEXSCANS.COM",
    "SHOW YOUR SUPPORT AND JOIN THE STORM AT VORTEXSCANS.ORG",
    "DEAR READERS, DIVE DEEPER INTO THE STORY AND UNLOCK UP TO THE LATEST "
    "CHAPTER EXCLUSIVELY ON VORTEXSCANS.ORG!",
    "THIS CHAPTER WAS BROUGHT TO JOIN OUR HALLWEEN EVENT YOU BY THE VORTEX "
    "SCANS TEAM. AND ENJOY OFFERS ON SITE ITEMS!",
    "HAPPY READING,",
    "HTTPS://DISCORD.GG/TY6EDWKC4G",
    "CHAPTER 110",
]
for p in promos:
    gate(f"بنرِ واقعی promo میماند: «{p[:44]}…»", _cls(p) == "promo")

# ── ۴) واترمارکِ تنها همچنان promo ─────────────────────────────────────────
for w in ["LIKEMANGA.INK", "IKEMANGA.INK", "KEMANGA.INK", "VORTEXSCANS.COM",
          "VORTEXSCANS.ORG www", "MUNPIA", "www"]:
    gate(f"واترمارکِ تنها promo میماند: «{w}»", _cls(w) == "promo")

# ── ۵) کارکردِ _strip_watermark_tokens ─────────────────────────────────────
gate("strip: دامنهٔ چسبیده («DREAMS...LIKEMANGA.INK»)",
     _strip("DREAMS...LIKEMANGA.INK") == "DREAMS")
gate("strip: وسطِ جمله («IT'S EASY, LIKEMANGA.INK BECAUSE»)",
     _strip("IT'S EASY, LIKEMANGA.INK BECAUSE") == "IT'S EASY, BECAUSE")
gate("strip: تنهایی → خالی", _strip("LIKEMANGA.INK") == "")
gate("strip: کلمهٔ عادی سالم میماند («THE ASURA ATTACKED THE CITY»)",
     "ATTACKED" in _strip("THE ASURA ATTACKED THE CITY"))

# ── ۶) نسخه ────────────────────────────────────────────────────────────────
gate("APP_VER = 1.14.202", manga.APP_VER == "1.14.202")

print()
if _ok:
    print(f"[✓] همهٔ {_gates.__len__()} گیتِ سبز — v1.14.202 واترمارکِ رویِ حباب")
    sys.exit(0)
print(f"[✗] {sum(1 for _, c in _gates if not c)} گیتِ مردود")
sys.exit(1)
