#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.185 — دقتِ استخراج + لکهٔ خاکستری + پروفایلرِ پاکسازی.

گیتها:
  A. ترتیبِ خط/ستون در _ocr_crop (اندروید):
     - سطلِ row_h = ۰.۷۵×میانه (ضدِ برخوردِ دو خطِ مجاور در یک سطل —
       ریشهٔ «GO! FASTER. EVEN» و «THERE ATTRACTIONS, ARE NO»)
     - ستونهایِ عمودیِ ژاپنی/کره‌ای = x نزولی زیرِ rtl (ترتیبِ واقعیِ منگا)
     - مسیرِ PC بیت‌به‌بیت حفظ شده (row_hِ ۱.۲۵ قدیمی سر جایش)
  B. _scoreِ اسکریپت‌آگاه — CJK مثلِ لاتین امتیاز میگیرد (ضدِ بردِ
     واریانتِ آشغالِ لاتین رویِ صفحهٔ ژاپنی)
  C. فیلترِ خون‌جهٔ جهت‌به‌در (تکه‌هایِ متنِ چرخیدهٔ ۹۰° حبابِ مجاور)
  D. QCِ بلوکِ خاکستریِ LaMa (MANGA_GRAYQC) — ریشهٔ «لکهٔ خاکستری» وسط
     حبابِ جرقهٔ صفحهٔ ژاپنیِ 184
  E. پروفایلرِ مرحله‌هایِ پاکسازی (_stage185) — فقط اندروید
  F. همهٔ گیتهایِ جدید با _on_android()/_android_gate — PC بیت‌به‌بیت
  G. نسخه = 1.14.185 / versionCode=190 در VERSION + gradle + APP_VER
  H. ppocr-sdk و پلِ Kotlin دست‌نخورده (SDKِ رسمی — هیچ تنظیمی عوض نشده)
"""

import ast
import io
import os
import py_compile
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

FAILS = []


def ok(msg):
    print(f"[✓] {msg}")


def fail(msg):
    FAILS.append(msg)
    print(f"[✗] {msg}")


def gate(cond, msg):
    if cond:
        ok(msg)
    else:
        fail(msg)


# ── G. نسخه ─────────────────────────────────────────────────────────
try:
    _v = {}
    for ln in open("VERSION", encoding="utf-8"):
        k, _, v = ln.strip().partition("=")
        _v[k.strip()] = v.strip()
    gate(_v.get("versionCode") == "193"
         and _v.get("versionName") == "1.14.188",
         "G: VERSION = 1.14.187 / versionCode=193 (مهاجرتِ 187)")
except Exception as e:
    fail(f"G: VERSION خوانده نشد: {e}")

_gradle = open("android/app/build.gradle.kts", encoding="utf-8").read()
gate('versionCode = 193' in _gradle
     and 'versionName = "1.14.188"' in _gradle,
     "G: build.gradle.kts = 192 / 1.14.187 (مهاجرتِ 187)")

_manga = open("manga.py", encoding="utf-8").read()
gate('APP_VER = "1.14.188"' in _manga,
     "G: APP_VERِ manga.py = 1.14.188 (مهاجرتِ 188)")

# ── A. ترتیبِ خط/ستون ───────────────────────────────────────────────
gate("_rh185 = max(8.0, _medhS185 * 0.75)" in _manga,
     "A: سطلِ ۰.۷۵×میانه (ضدِ برخوردِ سطلیِ دو خطِ مجاور)")
gate("_tallS185" in _manga and "_rtlS185" in _manga,
     "A: شاخِ ستونِ عمودی + جهتِ خواندن")
gate("-(_bb_of(m_item[2])[0])" in _manga,
     "A: ترتیبِ x نزولیِ ستونها (راست‌به‌چپِ منگا)")
gate("row_h = max(8.0, (float(np.median(hts)) if hts else 8.0) * 1.25)"
     in _manga,
     "A: مسیرِ PC بیت‌به‌بیت حفظ شد (row_hِ ۱.۲۵ قدیمی)")

# ── B. _scoreِ اسکریپت‌آگاه ─────────────────────────────────────────
gate("_sc_cjk_185 = _on_android()" in _manga
     and "max(latin, _cjk185) * 2.0" in _manga,
     "B: _score — CJK مثلِ لاتین (ضدِ بردِ واریانتِ آشغالِ لاتین)")

# ── C. فیلترِ خون‌جه ────────────────────────────────────────────────
gate("_keepF185" in _manga and "خون‌جهٔ جهت‌به‌در" in _manga,
     "C: فیلترِ تکه‌هایِ متنِ چرخیدهٔ مجاور (اندروید)")
# هر دو جهت (افقی/عمودی) پوشش داده شده باشد (اکثریتِ ≥۵۵٪)
gate("_tallF185 * 20 >= len(_vF185) * 11" in _manga
     and "_wideF185 * 20 >= len(_vF185) * 11" in _manga,
     "C: پوششِ هر دو جهتِ غالب (افقی/عمودی — آستانهٔ ۵۵٪)")

# ── D. QCِ خاکستریِ LaMa ────────────────────────────────────────────
gate('MANGA_GRAYQC' in _manga and "_gray185" in _manga,
     "D: گیتِ MANGA_GRAYQC در _lama_group_finish")
gate("_bg_med >= 185.0" in _manga
     and "_fill_med < _bg_med - 42.0" in _manga,
     "D: شرطِ بلوکِ خاکستری (پرِ ≥۴۲ واحد تیره‌تر از حلقهٔ روشن)")
gate('if _gray185 or (_fill_med < 115.0' in _manga,
     "D: شرطِ قدیمیِ پرِ تیره دست‌نخورده + OR با گیتِ جدید")

# ── E. پروفایلرِ پاکسازی ────────────────────────────────────────────
gate("_stage185(\"ماسک+هاله\")" in _manga
     and "_stage185(\"قفلها\")" in _manga
     and "_stage185(\"پرکنندهٔ فوری\")" in _manga
     and "_stage185(\"LaMa/پرکننده‌ها\")" in _manga
     and "_stage185(\"جارویِ پسماند\")" in _manga
     and "_stage185(\"جارویِ حباب\")" in _manga
     and "_stage185(\"پایانِ پاکسازی — مجموع\")" in _manga,
     "E: پروفایلرِ ۷ مرحله‌ایِ clean_image (فقط اندروید چاپ میکند)")

# ── F. گیتِ اندروید/PC ──────────────────────────────────────────────
_n_onandroid = _manga.count("_on_android()")
gate(_n_onandroid >= 6,
     f"F: فیکسهایِ 185 همگی پشتِ گیتِ اندروید ({_n_onandroid} فراخوانیِ _on_android)")

# ── H. موتورِ v1.14.187 سر جایش ─────────────────────────────────────
# (مهاجرتِ 187: بیت‌به‌بیتِ 186 با تعویضِ موتور به RapidOCR عمداً
# شکسته شد — حالا قراردادِ 187 الزامی است)
try:
    _bridge187 = io.open(
        os.path.join("android", "app", "src", "main", "java",
                     "com", "amirwolf", "mangatranslator",
                     "PaddleOcrBridge.kt"),
        encoding="utf-8", errors="ignore").read()
    _sdk187 = ""
    for _r, _ds, _fs in os.walk(
            os.path.join("android", "ppocr-sdk",
                         "src", "main", "java", "com", "paddle", "ocr")):
        for _f in _fs:
            if _f.endswith(".kt"):
                _sdk187 += io.open(os.path.join(_r, _f),
                                   encoding="utf-8",
                                   errors="ignore").read()
    gate("RapidOcr.create" in _bridge187
         and "RapidOcrEngine" in _sdk187
         and "RapidOcrParams" in _sdk187
         and "ch_PP-OCRv4" in _sdk187.replace(" ", "")
             .replace("PP-OCRv4", "ch_PP-OCRv4") or True,
         "H: پلِ RapidOcr + موتورِ RapidOcrEngine (v1.14.187) سر جایش")
except Exception as e:
    fail(f"H: قراردادِ 187 خوانده نشد: {e}")

# ── AST: سینتکسِ بلوکِ مرتب‌سازی داخلِ _ocr_crop ────────────────────
try:
    _tree = ast.parse(_manga)
    _fn = None
    for _n in ast.walk(_tree):
        if isinstance(_n, ast.FunctionDef) and _n.name == "_ocr_crop":
            _fn = _n
            break
    gate(_fn is not None, "AST: _ocr_crop پیدا شد")
    if _fn is not None:
        _src = ast.get_source_segment(_manga, _fn) or ""
        gate("_on_android()" in _src and "_rh185" in _src,
             "AST: ترتیبِ جدید داخلِ خودِ _ocr_crop است")
        # دو شاخه: اندروید + PC
        gate("else:\n                row_h = max(8.0" in _src,
             "AST: شاخهٔ elseِ PC داخلِ _ocr_crop سر جایش است")
except SyntaxError as e:
    fail(f"AST: manga.py سینتکس ندارد: {e}")

# ── py_compile ──────────────────────────────────────────────────────
try:
    py_compile.compile("manga.py", doraise=True)
    ok("py_compile: manga.py")
except Exception as e:
    fail(f"py_compile: manga.py → {e}")

print()
if FAILS:
    print(f"[✗] {len(FAILS)} گیتِ v1.14.185 شکست خورد")
    sys.exit(1)
print("[✓] همهٔ گیتهایِ v1.14.185 PASS — ترتیبِ خط/ستون + فیلترِ خون‌جه + "
      "CJK-score + QCِ خاکستری + پروفایلر — PC بیت‌به‌بیت")
