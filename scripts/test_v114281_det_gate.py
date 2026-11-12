#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تستِ v1.14.281 — گیتِ «پدل-det شاهدِ متن» (E279).

خواستهٔ سازنده: «detector-v4-s_int8.onnx یک جا ک متن نیست پیدا
میکنع اگ palledocr det متنی پیدا نکرد الکی نره همون قسمت بپاکع
دیدم داره میپاکه با این ک متنی نیست».

قراردادِ نو در _extract_regions_from_bubbles:
  باکسِ detector-v4-s که OCR برایش «هیچ متنی» نداشت فقط وقتی
  ocr_empty (فقط-پاکسازی) میشود که detِ خودِ OCR در همان باکس
  «خطِ متنی» دیده باشد (line_polys)؛ det بیخط = باکس رد — نه
  پاکسازی، نه نجاتِ OCR (جوهرِ غیرمتنِ دیگر پاکیده نمیشود).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

_ok = [0, 0]


def check(name, cond):
    if cond:
        _ok[0] += 1
        print(f"  ✓ {name}")
    else:
        _ok[1] += 1
        print(f"  ✘ {name}")


src = open(os.path.join(ROOT, "manga_sections", "70_extract.py"),
           encoding="utf-8").read()

print("۱) گیتِ det در ساختِ ocr_empty")
check("شرطِ جدید: line_polys و بازهٔ جوهر",
      "if line_polys and 0.008 <= _gink <= 0.50:" in src)
check("شرطِ قدیمیِ بدونِ det دیگر وجود ندارد",
      "if 0.008 <= _gink <= 0.50:" not in src)
check("تنها محلِ ocr_empty = True همان ناحیهٔ گیت‌دار است",
      src.count("ocr_empty = True") == 1
      and src.find("ocr_empty = True") > src.find(
          "if line_polys and 0.008 <= _gink <= 0.50:"))
check("یادداشتِ قرارداد سرِ گیت",
      "پدل-det شاهدِ متن" in src and "الکی نره همون قسمت بپاکع" in src)

print("۲) مسیرهایِ وابسته دستنخورده")
rsrc = open(os.path.join(ROOT, "manga_sections", "95_run.py"),
            encoding="utf-8").read()
check("نجاتِ OCRِ ocr_empty در رندر سرِ جایش است",
      "_rescue_empty_ocr" in rsrc or "_rescue_empty_ocr" in
      open(os.path.join(ROOT, "manga_sections", "90_render.py"),
           encoding="utf-8").read())
check("لیستِ پاکسازی: dialogue متندار یا ocr_empty",
      "getattr(r, \"ocr_empty\", False)" in rsrc)
check("rec-rescue قبل از گیت اجرا میشود (ترتیب)",
      src.find("_rec_rescue_missed_quads") < src.find(
          "if line_polys and 0.008"))

print()
if _ok[1]:
    print(f"✘ {_ok[1]} چک قرمز")
    sys.exit(1)
print(f"✔ همهٔ چکها سبز است ({_ok[0]} چک — گیتِ detِ بی‌متن)")
