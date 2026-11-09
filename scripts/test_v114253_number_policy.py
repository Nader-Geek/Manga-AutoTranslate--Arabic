#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تستِ سیاستِ عدد/نمادِ v1.14.253 (دستورِ سازنده — لاگِ گوشی img7):

  ۱) عددِ چسبیده به متن («.85 LIKE A TIME BOMB..!» — det گوشی جعبه را
     یکی دیده بود): عدد باید «خوانده و پاک» شود، نه «پاک بدونِ خواندن».
  ۲) عددِ تنها («1233»، «85») و پسوندِ واحد («2B»، «10,000G»):
     ناحیه دست‌نخورده (no_touch230) — نه ترجمه، نه پاکسازی.
  ۳) «19 hi»: هر دو خط خوانده شود + ناحیه پاک شود.
  ۴) رگرسیون: سمبل/حرفِ بیواکلِ بی‌رقم در ناحیهٔ حرف‌دار همچنان
     آشغال است («#»، «FL»، «SS»)؛ «77,I» → «I».
  ۵) ناحیهٔ بیحرفِ واقعی: هیچ خطی نمی‌افتد (تا no_touch شود).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import manga

f = manga._latin_junk_line188
shl = manga.source_has_letters
cls = manga.MangaTranslator._classify_text


def run_filter(entries):
    """عینِ حلقهٔ 70_extract: rhas از متنِ کلِ کاندید، بعد فیلترِ خط‌به‌خط."""
    rhas = shl(" ".join(str(e) for e in entries))
    kept = []
    for e in entries:
        v = f(e, rhas)
        if v is False:
            kept.append(e)
        elif isinstance(v, str):
            kept.append(v)
    return kept, rhas


ok = True

kept, rhas = run_filter([".85", "LIKE A TIME BOMB..!"])
k = cls(" ".join(kept))
print(f"۱) ادغام‌شده: kept={kept} classify={k!r}")
ok &= (kept == [".85", "LIKE A TIME BOMB..!"] and k == "dialogue")

for t in ("1233", "85", "2B", "10,000G"):
    rhas = shl(t)
    kept, _ = run_filter([t])
    k2 = cls(t)
    print(f"۲) تنها {t!r}: rhl={rhas} kept={kept} classify={k2!r}")
    ok &= (rhas is False and kept == [t])

kept, rhas = run_filter(["19", "hi"])
print(f"۳) 19 hi: kept={kept} classify={cls('19 hi')!r}")
ok &= (kept == ["19", "hi"] and cls("19 hi") == "dialogue")

kept, _ = run_filter(["#", "GO!", "FL", "SS", "77,I"])
print(f"۴) حرف‌دار: kept={kept}")
ok &= (kept == ["GO!", "I"])

for group in (["؟!", "23", "....", "[ ]"], [".85"]):
    kept, rhas = run_filter(group)
    print(f"۵) بیحرف {group}: rhl={rhas} kept={kept}")
    ok &= (rhas is False and kept == group)

print()
print("✅ همهٔ سناریوهای عدد/نماد پاس شد" if ok else "❌ شکستی هست")
sys.exit(0 if ok else 1)
