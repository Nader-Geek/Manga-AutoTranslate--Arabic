#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.193 — «Ai وقتی خالی برمیگردونه عکسِ انگلیسیش نشون
نده تا وقتی همشو ترجمه کنه … نمایش زنده کم کم بذاره تو نمایش انگار داره
لود بشه» (گزارشِ سازنده — PC/لینوکس/اندروید).

گیتها:
  A. نسخه = 1.14.193 / versionCode=198 (manga.py + manga_app.py +
     VERSION + gradle) + خطِ لاگِ گوشی.
  B. ریشهٔ «انگلیسی رویِ عکس» — نجاتِ 189 دیگر متنِ مبدأ را داخلِ
     translated_text نمینشاند (val = src حذف شد).
  C. سدِ نهاییِ [193] در finish_page_phase: پارامترِ final + تا ۳ دورِ
     پرسیدنِ دوباره از مدل تا «همشو ترجمه کنه» — صفحهٔ نهایی با حبابِ
     بیترجمه تمام نمیشود.
  D. [192] فقط در رندرِ نهایی: پیش‌نمایشِ زنده متنِ مبدأ را رویِ حبابهایِ
     درانتظار نمینشاند (خالیِ روشن = لودینگ) + هشدارِ «حباب ترجمه نشد»
     فقط در نهایی (نه هر ۲ ثانیه).
  E. مسیرهایِ نهایی final=True میگذارند (_finish_page_now + _finish_one +
     process_core) و رندرِ فال‌بکِ 192 با «or _fb192» حتی در شکستِ کاملِ
     مدل اجرا میشود (ضدِ صفحهٔ تمامسفید).
  F. رگرسیونهایِ ۱۹۲/۱۹۰/۱۹۱ + سلامتِ عمومی (py_compile + YAML).
"""

import io
import os
import py_compile
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
    return cond


_manga = io.open("manga.py", encoding="utf-8").read()
_manga_app = io.open("manga_app.py", encoding="utf-8").read()
_gradle = io.open("android/app/build.gradle.kts", encoding="utf-8").read()
_main_kt = io.open(
    "android/app/src/main/java/com/amirwolf/mangatranslator/MainActivity.kt",
    encoding="utf-8").read()
_service_kt = io.open(
    "android/app/src/main/java/com/amirwolf/mangatranslator/TranslationService.kt",
    encoding="utf-8").read()
_store_kt = io.open(
    "android/app/src/main/java/com/amirwolf/mangatranslator/OcrModelStore.kt",
    encoding="utf-8").read()

# ── A. نسخه ──────────────────────────────────────────────────────────
gate('APP_VER = "1.14.193"' in _manga, "A: APP_VERِ manga.py = 1.14.193")
gate('APP_VER = "1.14.193"' in _manga_app, "A: APP_VERِ manga_app.py = 1.14.193")
_v = {}
try:
    for ln in open("VERSION", encoding="utf-8"):
        if "=" in ln:
            k, val = ln.strip().split("=", 1)
            _v[k] = val
    gate(_v.get("versionCode") == "198"
         and _v.get("versionName") == "1.14.193",
         "A: VERSION = 1.14.193 / versionCode=198")
except Exception as e:
    fail(f"A: VERSION خوانده نشد: {e}")
gate("versionCode = 198" in _gradle and 'versionName = "1.14.193"' in _gradle,
     "A: build.gradle.kts = 198 / 1.14.193")
gate("دانلودی — v1.14.193" in _manga, "A: خطِ لاگِ آمادهشدنِ موتورِ گوشی = v1.14.193")

# ── B. ریشه: نجاتِ 189 دیگر متنِ مبدأ را مسموم نمیکند ────────────────
gate("\n                val = src" not in _manga
     and "متنِ مبدأ جایگزین شد" not in _manga,
     "B: «val = src» (نشاندنِ متنِ مبدأ در translated_text) کلاً حذف شد")
gate("بیترجمه میماند تا دورِ بعد دوباره پرسیده شود" in _manga,
     "B: پیامِ جدیدِ نجات — ناحیهٔ بیجواب برایِ دورِ بعد میماند")
gate("v1.14.193 — دیگر متنِ مبدأ جایگزین نمیشود" in _manga,
     "B: داکیومنتِ نجاتِ 189 بهروز شد")

# ── C. سدِ نهاییِ [193] در finish_page_phase ─────────────────────────
gate("precleaned: Optional[np.ndarray] = None,\n                          final: bool = False," in _manga,
     "C: پارامترِ final به finish_page_phase اضافه شد")
gate("for _g_round in range(1, 4):" in _manga
     and "self.translate_regions(_g_missing)" in _manga,
     "C: سدِ [193] — تا ۳ دورِ پرسیدنِ دوباره از مدل تا «همشو ترجمه کنه»")
gate("except (GeminiQuotaExhausted, JobCancelled):\n                    raise" in _manga,
     "C: کوتا/لغو از سدِ [193] رد میشود (رفتارِ بالادست دستنخورده)")
gate("تا ترجمهٔ کامل صبر میشود، انگلیسی نشان داده نمیشود" in _manga,
     "C: پیامِ لاگِ سدِ [193]")
gate("if (final and not getattr(self, \"clean_only\", False)\n                and not getattr(self, \"fake_translate\", False)):" in _manga,
     "C: سدِ [193] فقط در رندرِ نهایی — نه clean_only نه fake")

# ── D. [192] فقط نهایی؛ پیش‌نمایشِ زنده = لودینگِ خالیِ روشن ──────────
gate("if final and precleaned is not None:" in _manga,
     "D: فال‌بکِ 192 فقط در رندرِ نهایی — پیش‌نمایش متنِ مبدأ نمینشاند")
gate("if missing_n and final:" in _manga,
     "D: هشدارِ «حباب ترجمه نشد» فقط در نهایی (نه هر ۲ ثانیه در پیش‌نمایش)")
gate("v1.14.193 — فقط در رندرِ «نهایی» (final=True): پیش‌نمایشِ زنده" in _manga,
     "D: توضیحِ لودینگِ پیش‌نمایش در کد ثبت شد")

# ── E. مسیرهایِ نهایی + ضدِ صفحهٔ تمامسفید ───────────────────────────
gate("final=True)  # v1.14.193 — رندرِ نهایی با سدِ «تا همشو ترجمه کنه»" in _manga,
     "E: _finish_page_now (مسیرِ بچ) final=True")
gate("final=True)  # v1.14.193 — مسیرِ نهایی" in _manga,
     "E: _finish_one final=True")
gate("finish_page_phase(image, regions, final=True)  # v1.14.193" in _manga,
     "E: process_core (تکصفحهای/اندروید) final=True")
gate("if _clean_regions or _fb192:" in _manga,
     "E: ضدِ صفحهٔ تمامسفید — با فال‌بکِ 192 رندر حتی در شکستِ کاملِ مدل اجرا میشود")
gate("(translated_regions + _fb192) if _fb192 else translated_regions" in _manga,
     "E: رگرسیونِ 192 — لیستِ رندر = ترجمهشدهها + فال‌بکهایِ ۱۹۲")

# ── F. سلامتِ عمومی + رگرسیونهایِ ۱۹۲/۱۹۰/۱۹۱ ────────────────────────
try:
    py_compile.compile("manga.py", doraise=True)
    py_compile.compile("manga_app.py", doraise=True)
    py_compile.compile("android/app/src/main/python/bridge.py", doraise=True)
    ok("F: py_compile manga.py + manga_app.py + bridge.py")
except Exception as e:
    fail(f"F: py_compile: {e}")

try:
    import yaml
    for y in (".github/workflows/build.yml",
              ".github/workflows/fetch_models.yml",
              ".github/workflows/android-emulator.yml"):
        yaml.safe_load(io.open(y, encoding="utf-8"))
    ok("F: YAMLِ workflowها سالم")
except Exception as e:
    fail(f"F: YAML: {e}")

# رگرسیونِ ۱۹۲ — نجاتِ نهاییِ داخلِ translate_regions سرِ جایش
gate("نجاتِ نهایی در translate_regions انجام شد" in _manga
     and "if self._force_translate_missing_1189(regions):" in _manga,
     "F: رگرسیونِ 192 — سدِ نجاتِ داخلِ translate_regions")
# رگرسیونِ ۱۹۲ — سه سدِ ضدِ حبابِ خالی
gate("_c192 = copy.copy(_r192)" in _manga
     and "_c192.translated_text = _r192.source_text" in _manga,
     "F: رگرسیونِ 192 — فال‌بکِ متنِ مبدأ رویِ «کپیِ» ناحیه")
gate("((r.source_text or \"\").strip()\n                         or (r.translated_text or \"\").strip())" in _manga,
     "F: رگرسیونِ 192 — _clean_regions_for_page ناحیهٔ بی‌متن را پاک نمیکند")
# رگرسیونِ ۱۹۲ — آپدیت/لاگ/UI
gate("private fun checkAppUpdate(): Boolean" in _main_kt
     and "private fun checkAppUpdateWithRetry()" in _main_kt,
     "F: رگرسیونِ 192 — آپدیتِ درون‌اپیِ ۳تلاشی")
gate("private fun deleteAllMangaLogsInDownloads()" in _main_kt,
     "F: رگرسیونِ 192 — جارویِ لاگهایِ Downloads")
gate("logBox.postDelayed({ scrollLogToBottom() }, 90)" in _main_kt,
     "F: رگرسیونِ 192 — اسکرولِ خودکارِ لاگِ اندروید")
gate("const attachFollow = () => {{" in _manga_app,
     "F: رگرسیونِ 192 — فالویِ لاگِ وب (PC/لینوکس)")
gate(".setLargeIcon(" not in _service_kt,
     "F: رگرسیونِ 192 — اعلانِ تک‌آیکون")
# رگرسیونِ ۱۹۰/۱۹۱
gate("interface OcrProgressSink" in io.open(
    "android/ppocr-sdk/src/main/java/com/paddle/ocr/util/OcrProgressSink.kt",
    encoding="utf-8").read(),
    "F: رگرسیونِ 190 — sinkِ پیشرفتِ دانلود")
gate('"PP-OCRv6_medium_det_onnx.onnx" if _pc_det_medium()' in _manga,
     "F: رگرسیونِ 191 — detِ PC")
gate('"multi": "multi"' in _manga and "def _ocr_multi(self, buf):" in _manga,
     "F: رگرسیونِ 190 — چندزبانه")

print()
if FAILS:
    print(f"✗ {len(FAILS)} گیتِ مردود:")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ همهٔ گیت‌هایِ v1.14.193 سبز است.")
