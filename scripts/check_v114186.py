#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.186 — ضدِ لکهٔ شیری (SOFTQC) + کشِ محافظِ ساختار +
فیکسِ گیتِ چندزبانهٔ امولاتور (کلیدِ manga_ocr_lang).

گیتها:
  A. MANGA_SOFTQC (اندروید): پرِ شیریِ LaMa رویِ زمینهٔ بافت‌دار — کتِ
     بژِ صفحهٔ ژاپنیِ 184 — روشناییِ نزدیک به حلقه (از QCِ تیره/دود
     میگذشت) ولی hfِ پر ≈ صفر در برابرِ hfِ واقعیِ حلقه → پرِ ردیفیِ حلقه.
     دروازهٔ ارزانِ stdِ حلقه (≥۱۴) + hfِ حلقه (≥۷) + یکنواختیِ پر (std≤۳).
     مسیرِ دودِ قدیمی دست‌نخورده؛ PC بیت‌به‌بیت.
  B. MANGA_PROT_CACHE (اندروید): بخشهایِ سنگینِ min_len/near_px-مستقلِ
     _structural_protect_mask (medianBlur31، poly_all، بازِ خطیِ سراسری)
     بینِ دو فراخوانیِ هر صفحه کش میشوند؛ محلِ فراخوانی بعد از بارِ دوم
     کش را پاک میکند. PC بدونِ کش — بیت‌به‌بیت.
  C. ext_settings.py: کلیدِ «manga_ocr_lang» (idِ واقعیِ فیلدِ UI) + کلیدِ
     قدیمیِ «ocr_lang» — ریشهٔ FAILِ گیتِ چندزبانهٔ 183→185: گاردِ CJKِ
     v1.14.154 با lang=en کلِ خطهایِ ja/zh/ko را حذف میکرد.
  D. نسخه = 1.14.186 / versionCode=191 در VERSION + gradle + APP_VER؛
     رشتهٔ «روشِ استخراج» حالا از APP_VER میخواند (دیگر کهنه نمیشود).
  E. همهٔ گیتهایِ جدید با _android_gate — PC بیت‌به‌بیت؛ v1.14.185
     دست‌نخورده (سطلِ ۰.۷۵، GRAYQC، پروفایلر)؛ SDKِ رسمی دست‌نخورده.
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


# ── D. نسخه ─────────────────────────────────────────────────────────
try:
    _v = {}
    for ln in open("VERSION", encoding="utf-8"):
        k, _, v = ln.strip().partition("=")
        _v[k.strip()] = v.strip()
    gate(_v.get("versionCode") == "192"
         and _v.get("versionName") == "1.14.187",
         "D: VERSION = 1.14.187 / versionCode=192 (مهاجرتِ 187)")
except Exception as e:
    fail(f"D: VERSION خوانده نشد: {e}")

_gradle = open("android/app/build.gradle.kts", encoding="utf-8").read()
gate('versionCode = 192' in _gradle
     and 'versionName = "1.14.187"' in _gradle,
     "D: build.gradle.kts = 192 / 1.14.187 (مهاجرتِ 187)")

_manga = open("manga.py", encoding="utf-8").read()
gate('APP_VER = "1.14.187"' in _manga,
     "D: APP_VERِ manga.py = 1.14.187 (مهاجرتِ 187)")
# رشتهٔ «روشِ استخراج» دیگر نسخهٔ هاردکد ندارد (با پیشوندِ v)
gate("v1.14.185)%s" not in _manga
     and "باندل (RapidOcrAndroidOnnx — " in _manga
     and '"v%s)%s"' in _manga
     and "% (APP_VER, _ms_l))" in _manga,
     "D: رشتهٔ روشِ استخراج از APP_VER میخواند (دیگر کهنه نمیشود)")

# ── A. MANGA_SOFTQC ─────────────────────────────────────────────────
gate('MANGA_SOFTQC' in _manga and "_soft186" in _manga,
     "A: گیتِ MANGA_SOFTQC در QCِ حلقهٔ LaMa")
gate("_rstd186 >= 14.0" in _manga,
     "A: دروازهٔ ارزانِ بافتِ حلقه (std ≥ ۱۴)")
gate("_hf_rg >= 7.0" in _manga
     and "_hf_in < max(3.0," in _manga
     and "0.35 * _hf_rg)" in _manga,
     "A: شرطِ پرِ شیری (hfِ پر < ۰.۳۵×حلقه با حلقهٔ بافت‌دار ≥۷)")
gate("_hf_sd <= 3.0" in _manga,
     "A: یکنواختیِ پرِ شیری (stdِ hfِ پر ≤ ۳)")
gate("abs(_fmed140 - _rmed140) <= 22.0" in _manga
     and "_rmed140 >= 140.0" in _manga,
     "A: فقط روشناییِ نزدیک (کلاسِ جدید — کلاسِ تیره/دودِ قدیمی سر جایش)")
gate("if _soft186 or abs(_fmed140 - _rmed140) > 22.0 or \\" in _manga
     and "_rmed140 < 140.0:" in _manga,
     "A: تریگرِ قدیمیِ دود/تیره دست‌نخورده + OR با SOFTQC")
gate("if not _soft186:" in _manga,
     "A: محاسبهٔ دوبارهٔ hf برایِ مسیرِ قدیمی حذف شد (سریعتر)")
gate("_tag140 = (\"ضدِ لکهٔ شیری (SOFTQC)\"" in _manga,
     "A: لاگِ قابلِ تشخیصِ SOFTQC در لاگِ گوشی")

# ── B. MANGA_PROT_CACHE ─────────────────────────────────────────────
gate('MANGA_PROT_CACHE' in _manga and "_spm_cache" in _manga,
     "B: گیتِ MANGA_PROT_CACHE + کشِ _spm_cache")
gate("_hit186" in _manga and "_spc186[0] == _key186" in _manga,
     "B: مسیرِ hit با کلیدِ (بافرِ تصویر + ماسکِ خام + ناحیهها)")
gate("self._spm_cache = (_key186, dark_full, poly_all," in _manga,
     "B: ذخیرهٔ dark_full/poly_all/outِ خطی (بخشهایِ مستقل از پارامترها)")
gate("self._spm_cache = None" in _manga,
     "B: پاکسازیِ کش در محلِ فراخوانی (بعد از بارِ دوم — هیچ کهنشدنی)")
gate("if _hit186:" in _manga and "cv2.bitwise_and(dark_full, near)" in _manga,
     "B: مسیرِ hit فقط بخشهایِ near_px-دار را از نو میسازد")
gate("g = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)" in _manga
     and "if _hit186:" in _manga
     and _manga.index("g = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)",
                      _manga.index("def _structural_protect_mask"))
     > _manga.index("if _hit186:",
                    _manga.index("def _structural_protect_mask")),
     "B: medianBlurِ سنگین فقط در مسیرِ miss")

# ── C. فیکسِ گیتِ چندزبانهٔ امولاتور ────────────────────────────────
_ext = open(".ci_scripts/ext_settings.py", encoding="utf-8").read()
gate('manga_ocr_lang' in _ext and 'ocr_lang' in _ext,
     "C: ext_settings هر دو کلیدِ manga_ocr_lang + ocr_lang را مینویسد")
gate(_ext.index("manga_ocr_lang") < _ext.index("</map>"),
     "C: کلیدِ manga_ocr_lang داخلِ mapِ XML است")

# ── E. گیتِ اندروید/PC + 185 دست‌نخورده ─────────────────────────────
_n_gate = _manga.count("_android_gate(")
gate(_n_gate >= 15,
     f"E: فیکسها پشتِ گیتِ اندروید ({_n_gate} فراخوانیِ _android_gate)")
gate("_rh185 = max(8.0, _medhS185 * 0.75)" in _manga,
     "E: v1.14.185 — سطلِ ۰.۷۵ سر جایش")
gate('MANGA_GRAYQC' in _manga and "_gray185" in _manga,
     "E: v1.14.185 — QCِ خاکستری سر جایش")
gate("_stage185(\"ماسک+هاله\")" in _manga,
     "E: v1.14.185 — پروفایلرِ پاکسازی سر جایش")
# PC: سطلِ ۱.۲۵ قدیمیِ _ocr_crop
gate("row_h = max(8.0, (float(np.median(hts)) if hts else 8.0) * 1.25)"
     in _manga,
     "E: مسیرِ PC بیت‌به‌بیت (row_hِ ۱.۲۵ قدیمی)")

# ── موتورِ v1.14.187 سر جایش ────────────────────────────────────────
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
         and "setLanguageVariant" in _bridge187,
         "H: پلِ RapidOcr + موتورِ RapidOcrEngine + انتخابِ زبان (v1.14.187)")
except Exception as e:
    fail(f"H: قراردادِ 187 خوانده نشد: {e}")

# ── AST: ساختارِ SOFTQC داخلِ بلوکِ دودِ 140 ────────────────────────
try:
    _tree = ast.parse(_manga)
    _fn = None
    for _n in ast.walk(_tree):
        if isinstance(_n, ast.FunctionDef) \
                and _n.name == "_lama_group_finish":
            _fn = _n
            break
    gate(_fn is not None, "AST: _lama_group_finish پیدا شد")
    if _fn is not None:
        _src = ast.get_source_segment(_manga, _fn) or ""
        gate("MANGA_SOFTQC" in _src and "_soft186" in _src,
             "AST: SOFTQC داخلِ خودِ _lama_group_finish است")
        gate("MANGA_DARKSMOKE" in _src,
             "AST: مسیرِ دودِ 140 داخلِ همان تابع سر جایش است")
except SyntaxError as e:
    fail(f"AST: manga.py سینتکس ندارد: {e}")

# ── AST: کشِ محافظِ ساختار داخلِ خودِ تابع ──────────────────────────
try:
    _tree = ast.parse(_manga)
    _fn2 = None
    for _n in ast.walk(_tree):
        if isinstance(_n, ast.FunctionDef) \
                and _n.name == "_structural_protect_mask":
            _fn2 = _n
            break
    gate(_fn2 is not None, "AST: _structural_protect_mask پیدا شد")
    if _fn2 is not None:
        _src2 = ast.get_source_segment(_manga, _fn2) or ""
        gate("MANGA_PROT_CACHE" in _src2 and "_spm_cache" in _src2,
             "AST: کش داخلِ خودِ _structural_protect_mask است")
        # min_len/near_px هنوز در مسیرِ member-loop استفاده میشوند
        gate("int(min_len) >= 60" in _src2 and "int(near_px) >= 25" in _src2,
             "AST: پارامترهایِ min_len/near_px در مسیرِ وابسته سر جایش")
except SyntaxError as e:
    fail(f"AST: manga.py سینتکس ندارد: {e}")

# ── py_compile ──────────────────────────────────────────────────────
for _f in ("manga.py", ".ci_scripts/ext_settings.py"):
    try:
        py_compile.compile(_f, doraise=True)
        ok(f"py_compile: {_f}")
    except Exception as e:
        fail(f"py_compile: {_f} → {e}")

# ── سازگاریِ 3.11 (CI = Python 3.11؛ سندباکس = 3.12+) ───────────────
# v1.14.186b — f-stringِ چندخطی (PEP 701) در 3.11 SyntaxError میداد و
# PC-speed CI را کشت؛ حالا همهٔ فایلهایِ تغییرپذیر با گرامرِ 3.11
# پارس میشوند.
try:
    import glob as _glob
    _pyfiles = (["manga.py", ".ci_scripts/ext_settings.py",
                 "scripts/bench_speed.py",
                 "android/app/src/main/python/bridge.py"]
                + sorted(_glob.glob("scripts/check_v11*.py")))
    _bad311 = []
    for _pf in _pyfiles:
        try:
            ast.parse(open(_pf, encoding="utf-8").read(),
                      filename=_pf, feature_version=(3, 11))
        except SyntaxError as _se:
            _bad311.append(f"{_pf}:{_se.lineno} {_se.msg}")
    gate(not _bad311,
         "PY311: همهٔ فایلها با گرامرِ Python 3.11 پارس میشوند"
         if not _bad311 else
         f"PY311: ناسازگارِ 3.11 → {_bad311}")
except Exception as e:
    fail(f"PY311: اسکن شکست خورد: {e}")

print()
if FAILS:
    print(f"[✗] {len(FAILS)} گیتِ v1.14.186 شکست خورد")
    sys.exit(1)
print("[✓] همهٔ گیتهایِ v1.14.186 PASS — SOFTQC + کشِ محافظِ ساختار + "
      "فیکسِ گیتِ چندزبانه — PC بیت‌به‌بیت")
