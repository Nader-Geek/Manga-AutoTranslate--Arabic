#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تستِ عملیِ v1.14.193 — «Ai وقتی خالی برمیگردونه عکسِ انگلیسیش نشون نده
تا وقتی همشو ترجمه کنه … نمایش زنده کم کم بذاره تو نمایش».

سناریوها:
  A) مدل دورِ اول خالی میدهد، دورِ دوم جواب میدهد → سدِ [193] دوباره
     میپرسد و صفحه با «همه» حبابها ترجمهشده تمام میشود؛ هیچ متنِ مبدأ
     رویِ خروجی رندر نمیشود.
  B) مدل هیچوقت جواب نمیدهد → سدِ [193] سه دور میپرسد، بعد سدِ 192 فقط
     «تصویریِ» متنِ مبدأ را رویِ کپی میگذارد؛ دادهٔ ناحیه بیترجمه میماند
     (دورِ بعدیِ ترجمهٔ واقعی دستنخورده).
  C) پیش‌نمایشِ زنده (final=False) هیچ سدّی را راه نمیاندازد و متنِ
     مبدأ را هم رندر نمیکند — حبابهایِ درانتظار خالیِ روشن میمانند (= لودینگ).
  D) نجاتِ 189 دیگر متنِ مبدأ را داخلِ translated_text نمینشیند
     (ریشهٔ قدیمیِ «انگلیسی رویِ عکسِ نهایی»)؛ مسیرِ موفق هم سالم است.
"""
import os
import sys
import threading

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import manga  # noqa: E402
from manga import MangaTranslator, TextRegion  # noqa: E402

FAILS = []


def check(cond, msg):
    print(("[✓] " if cond else "[✗] ") + msg)
    if not cond:
        FAILS.append(msg)


def make_region(rid, src, ocr_empty=False):
    r = TextRegion(id=rid, boxes=[], source_text=src,
                   rect=(10, 10, 80, 40), kind="dialogue")
    if ocr_empty:
        r.ocr_empty = True
        r.source_text = ""
    return r


def make_mt():
    mt = MangaTranslator.__new__(MangaTranslator)
    mt.debug = False
    mt.clean_only = False
    mt.fake_translate = False
    mt.clean_sfx = False
    return mt


IMG = np.full((120, 160, 3), 240, np.uint8)


def run_finish(mt, regions, final, tr_fake):
    mt.translate_regions = tr_fake
    seen = {}

    def fake_render(cleaned, regs, raw):
        seen["regs"] = list(regs)
        return cleaned.copy()

    mt.render_translations = fake_render
    out, _ = mt.finish_page_phase(
        IMG.copy(), regions, skip_translate=True, precleaned=IMG.copy(),
        final=final)
    return out, seen.get("regs", [])


# ── A) مدل دورِ دوم جواب میدهد → صفحه کاملِ ترجمهشده، بدونِ متنِ مبدأ ──
regions_a = [make_region(1, "Hello world"),
             make_region(2, "How are you?"),
             make_region(3, "I am fine."),
             make_region(4, "", ocr_empty=True)]
calls_a = {"n": 0}


def tr_comes_late(regs):
    calls_a["n"] += 1
    if calls_a["n"] >= 2:  # دورِ اول خالی — دورِ دوم ترجمهٔ واقعی
        for r in regs:
            if (r.source_text or "").strip():
                r.translated_text = "ترجمهٔ فارسیِ " + str(r.id)


out_a, regs_a = run_finish(make_mt(), regions_a, final=True, tr_fake=tr_comes_late)
check(calls_a["n"] == 2, f"A: سدِ [193] دوباره پرسید (۲ فراخوانی؛ شد {calls_a['n']})")
check(out_a is not None and regs_a is not None, "A: خروجیِ رندر ساخته شد")
check(len(regs_a) == 3, f"A: ۳ حبابِ ترجمهشده رندر شد (شد {len(regs_a)})")
check(all((r.translated_text or "").strip()
          and r.translated_text != r.source_text for r in regs_a),
      "A: هیچ متنی از مبدأ (انگلیسی) رویِ خروجی نیست")
check(all((r.translated_text or "").strip() for r in regions_a[:3]),
      "A: هر ۳ ناحیه در داده هم ترجمهٔ واقعی دارند")

# ── B) مدل هیچوقت جواب نمیدهد → ۳ دورِ پرسش، بعد سدِ 192 تصویری ──
regions_b = [make_region(1, "Hello world"),
             make_region(2, "How are you?"),
             make_region(3, "I am fine.")]
calls_b = {"n": 0}


def tr_never(regs):
    calls_b["n"] += 1


out_b, regs_b = run_finish(make_mt(), regions_b, final=True, tr_fake=tr_never)
check(calls_b["n"] == 3, f"B: سه دورِ [193] پرسید (شد {calls_b['n']})")
check(len(regs_b) == 3
      and all(r.translated_text == r.source_text for r in regs_b),
      "B: سدِ 192 فقط تصویریِ متنِ مبدأ را رویِ «کپی» رندر کرد (ضدِ حبابِ خالی)")
check(all(not (r.translated_text or "").strip() for r in regions_b),
      "B: دادهٔ ناحیهها بیترجمه ماند — دورِ بعدیِ ترجمهٔ واقعی دستنخورده")

# ── C) پیش‌نمایشِ زنده: بدونِ سد، بدونِ متنِ مبدأ (= لودینگ) ──
regions_c = [make_region(1, "Hello world"),
             make_region(2, "How are you?")]
regions_c[0].translated_text = "ترجمهٔ رسیده"
calls_c = {"n": 0}


def tr_noop(regs):
    calls_c["n"] += 1


out_c, regs_c = run_finish(make_mt(), regions_c, final=False, tr_fake=tr_noop)
check(calls_c["n"] == 0, f"C: پیش‌نمایش هیچ دورِ ترجمهای راه نینداخت (شد {calls_c['n']})")
check(len(regs_c) == 1 and regs_c[0].translated_text == "ترجمهٔ رسیده",
      "C: پیش‌نمایش فقط حبابِ ترجمهشده را رندر کرد؛ حبابِ درانتظار خالیِ روشن ماند")

# ── D) نجاتِ 189: دیگر متنِ مبدأ را داخلِ translated_text نمینشیند ──
mt_d = make_mt()
mt_d._get_system_instruction = lambda: ""
mt_d._api_lock = threading.Lock()
mt_d.provider_type = "gemini"
mt_d._translate_with_gemini = lambda p, s, structured=True: ""
mt_d._parse_translation_response = lambda t, regs: None
reg_d = make_region(9, "Stay down!")
fixed = mt_d._force_translate_missing_1189([reg_d])
check(fixed == 0 and not (reg_d.translated_text or "").strip(),
      "D: مدلِ خالی → ناحیه بیترجمه ماند (متنِ مبدأ مسموم نشد)")

mt_d2 = make_mt()
mt_d2._get_system_instruction = lambda: ""
mt_d2._api_lock = threading.Lock()
mt_d2.provider_type = "gemini"
mt_d2._translate_with_gemini = lambda p, s, structured=True: "پایین بمان!"
mt_d2._parse_translation_response = lambda t, regs: None
reg_d2 = make_region(10, "Stay down!")
fixed2 = mt_d2._force_translate_missing_1189([reg_d2])
check(fixed2 == 1 and reg_d2.translated_text == "پایین بمان!",
      "D: مسیرِ موفقِ نجات سرِ جایش است")

print()
if FAILS:
    print(f"✗ {len(FAILS)} سناریو مردود:")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ همهٔ سناریوهایِ v1.14.193 سبز است.")
