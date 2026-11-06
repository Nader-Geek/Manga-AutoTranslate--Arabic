#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.14.225 — تستِ واحدِ حذفِ نواحیِ هممتنِ همپوشان (ضدِ رندرِ دوباره).

سناریوی واقعیِ لاگِ گوشیِ v1.14.217 (pick_1793932400065_01.jpg):
  #07 rect=(283,1919,296,178) متنِ «GO! EVEN FASTER...» (۳ خط)
  #08 rect=(445,1951,223,163) متنِ «GO! EVEN FASTER...» (۳ خط)
  → IoU=0.28<0.35 و احتوای ۵۴٪<۶۵٪ → merge قدیمی ردشان میکرد →
    دو رندرِ بالای هم. حالا: متنِ یکسان + همپوشانی → یکی حذف میشود.
"""
import sys
sys.path.insert(0, '/home/z/my-project/Manga-AutoTranslate')
import numpy as np
from manga import MangaTranslator, TextRegion

PASS = FAIL = 0


def ok(cond, name):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [✓] {name}")
    else:
        FAIL += 1
        print(f"  [✗] {name}")


def mk(rid, rect, text, polys=None, kind="dialogue"):
    x, y, w, h = rect
    return TextRegion(
        id=rid,
        boxes=[np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]],
                        dtype=np.int32)],
        source_text=text,
        rect=rect, kind=kind,
        ocr_polys=polys or [])


print("== 1) سناریوی لاگِ گوشی: #07/#08 هممتنِ همپوشان ==")
r07 = mk(7, (283, 1919, 296, 178), "GO!\nEVEN\nFASTER...",
         polys=[[[300, 1920], [500, 1920], [500, 1960], [300, 1960]],
                [[300, 1970], [520, 1970], [520, 2010], [300, 2010]],
                [[300, 2020], [540, 2020], [540, 2060], [300, 2060]]])
r08 = mk(8, (445, 1951, 223, 163), "GO!\nEVEN\nFASTER...",
         polys=[[[450, 1955], [640, 1955], [640, 1995], [450, 1995]],
                [[450, 2005], [650, 2005], [650, 2045], [450, 2045]],
                [[450, 2055], [660, 2055], [660, 2095], [450, 2095]]])
out = MangaTranslator._dedup_duplicate_text_regions([r07, r08])
ok(len(out) == 1, f"یکی حذف شد (خروجی={len(out)})")
ok(out[0].id == 7, "نسخهٔ بزرگتر (#07) ماند")

print("== 2) خطِ یتیمِ چسبیده (متنِ ناحیهٔ موجود) ==")
r07b = mk(7, (283, 1919, 296, 178), "GO!\nEVEN\nFASTER...")
orph = mk(900001, (300, 2050, 270, 47), "GO! EVEN FASTER...")
out = MangaTranslator._dedup_duplicate_text_regions([r07b, orph])
ok(len(out) == 1 and out[0].id == 7, f"یتیمِ تکراری حذف شد (خروجی={[r.id for r in out]})")

print("== 3) یتیمِ واقعی (متنِ متفاوت، بیرونِ ناحیه) میماند ==")
r_sys = mk(3, (332, 2103, 198, 302), "Wha!?")
orph2 = mk(900002, (332, 2410, 400, 40), "OUTER GOD WITHIN 7 YEARS.]")
out = MangaTranslator._dedup_duplicate_text_regions([r_sys, orph2])
ok(len(out) == 2, "هر دو ماندند (متن/جعبهٔ جدا)")

print("== 4) متنِ تکراریِ واقعی در دو حبابِ جدا (بدونِ همپوشانی) ==")
a = mk(1, (100, 100, 120, 60), "NO")
b = mk(2, (900, 900, 120, 60), "NO")
out = MangaTranslator._dedup_duplicate_text_regions([a, b])
ok(len(out) == 2, "هر دو ماندند")

print("== 5) متنِ متفاوت با همپوشانیِ زیاد = دست‌نخورده (رفتارِ قدیمی) ==")
c = mk(1, (100, 100, 300, 200), "THE VILLA'S POOL IS NOT BAD")
d = mk(2, (150, 150, 200, 100), "You're the real attraction here.")
out = MangaTranslator._dedup_duplicate_text_regions([c, d])
ok(len(out) == 2, "متنِ متفاوت هرگز حذف نمیشود")

print("== 6) زیررشتهٔ داخلِ ناحیهٔ بزرگتر (بازخوانیِ نصفه) ==")
e = mk(1, (100, 100, 400, 120), "THE VILLA'S POOL IS NOT BAD FOR RELAXING, BUT...")
f = mk(2, (120, 150, 300, 50), "RELAXING, BUT...")
out = MangaTranslator._dedup_duplicate_text_regions([e, f])
ok(len(out) == 1 and out[0].id == 1, "بخشیِ تکراری حذف شد")

print("== 7) kind متفاوت (dialogue در برابرِ text_free) دست نمیخورد ==")
g = mk(1, (100, 100, 120, 60), "HELLO", kind="dialogue")
h = mk(2, (110, 105, 100, 50), "HELLO", kind="text_free")
out = MangaTranslator._dedup_duplicate_text_regions([g, h])
ok(len(out) == 2, "kind متفاوت = بدونِ حذف")

print("== 8) ناحیهٔ بی‌متن (ocr_empty) هرگز حذف نمیشود ==")
i_ = mk(1, (100, 100, 120, 60), "")
j = mk(2, (110, 105, 100, 50), "")
out = MangaTranslator._dedup_duplicate_text_regions([i_, j])
ok(len(out) == 2, "بی‌متنها ماندند")

print("== 9) متنِ فارسی/ja هم نرمال میشود ==")
k = mk(1, (100, 100, 200, 80), "برو! سریع‌تر...")
l = mk(2, (130, 120, 150, 60), "برو سریعتر")
out = MangaTranslator._dedup_duplicate_text_regions([k, l])
ok(len(out) == 1, "فارسیِ هممتنِ همپوشان یکی شد")
m = mk(1, (100, 100, 200, 80), "むにゅむにゅ")
n = mk(2, (130, 120, 150, 60), "むにゅむにゅ")
out = MangaTranslator._dedup_duplicate_text_regions([m, n])
ok(len(out) == 1, "ژاپنیِ هممتنِ همپوشان یکی شد")

print("== 10) جابهجاییِ واژهها (img6: EVEN GO! FASTER vs GO! FASTER... EVEN) ==")
p = mk(7, (283, 1919, 296, 178), "GO!\nEVEN\nFASTER...")
q = mk(8, (445, 1951, 223, 163), "EVEN GO! FASTER...")
out = MangaTranslator._dedup_duplicate_text_regions([p, q])
ok(len(out) == 1, "جابهجاییِ واژه حذف شد")

print("== 11) بازخوانیِ کج‌وکوله (word-scramble OCR) ==")
s = mk(1, (100, 100, 300, 150), "Alright! I'll increase the speed more!")
t = mk(2, (140, 120, 260, 110), "Alright! increase I'll the speed more!")
out = MangaTranslator._dedup_duplicate_text_regions([s, t])
ok(len(out) == 1, "شبیهِ ۹۰٪ حذف شد")

print("== 12) یتیمِ «زیررشتهٔ بدونِ همپوشانی» میماند (OUTER GOD) ==")
u = mk(3, (332, 2103, 198, 60), "[CLEAR OBJECTIVE: SLAY THE OUTER GOD WITHIN 7 YEARS.]")
v = mk(900003, (332, 2170, 400, 40), "OUTER GOD WITHIN 7 YEARS.]")
out = MangaTranslator._dedup_duplicate_text_regions([u, v])
ok(len(out) == 2, "زیررشتهٔ بیرونِ والد زنده ماند")

print("== 13) متنهایِ کوتاهِ مشابهِ همپوشان (NO در برابرِ NO) ==")
w1 = mk(1, (100, 100, 120, 60), "NO")
w2 = mk(2, (110, 105, 100, 50), "NO")
out = MangaTranslator._dedup_duplicate_text_regions([w1, w2])
ok(len(out) == 1, "کوتاهِ یکسانِ همپوشان یکی شد")

print("== 14) چ_affinity پایین حذف نمیشود (Wha!? vs GO) ==")
x1 = mk(1, (283, 1919, 296, 178), "GO!\nEVEN\nFASTER...")
x2 = mk(2, (332, 2103, 198, 302), "Wha!?")
out = MangaTranslator._dedup_duplicate_text_regions([x1, x2])
ok(len(out) == 2, "متنهایِ متفاوتِ همپوشان ماندند")

print(f"\n{'='*40}\nPASS={PASS} FAIL={FAIL}")
sys.exit(1 if FAIL else 0)
