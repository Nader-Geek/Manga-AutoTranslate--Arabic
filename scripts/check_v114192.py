#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.192 — شش فیکسِ سازنده:

گیتها:
  A. نسخه = 1.14.192 / versionCode=197 (manga.py + manga_app.py +
     VERSION + gradle) + خطِ لاگِ گوشی.
  B. مشکل۱ — «ai ترجمش برنمیگردونه … خالی میده» (PC/لینوکس/اندروید):
     سه سدِ ضدِ حبابِ خالی —
       B1) translate_regions: نجاتِ نهاییِ 189 بعد از ۳ دور (خروجهای
           زودبرگشتیِ 403 را هم میپوشاند).
       B2) finish_page_phase: مسیرِ precleaned (بچ) — حبابِ بامتنِ
           بیترجمه با «کپیِ» ناحیه و متنِ مبدأ رندر میشود (خودِ ناحیه
           دستنخورده تا ترجمهٔ واقعی بعداً بنشیند) + پیامِ [192].
       B3) _clean_regions_for_page: ناحیهٔ dialogueِ «بی‌متن» پاک
           نمیشود (پاکسازیِ بی‌جایگزین = حبابِ خالی).
       B4) شمارشِ «حباب ترجمه نشد» فقط برایِ ناحیهٔ بامتن.
  C. مشکل۲ — «اپدیت تو خوده اپ نمیاد»: checkAppUpdate → Boolean +
       checkAppUpdateWithRetry (۳ تلاش: ۰/۲۰/۶۰ ثانیه) + چکِ دوبارهٔ
       onResume با سقفِ ۳۰ دقیقه.
  D. مشکل۳ — «Downloads/manga/*log هروقت استارت پاک شه کامل، بعدِ تموم
       شدن فقط دوتا»: deleteAllMangaLogsInDownloads (فقط Downloads —
       بدونِ لاگِ خصوصی) فراخوانی در onStartJob + پاسِ دومِ تضمینیِ
       cleanupLogDuplicates (۲.۵ ثانیه بعد) در autoSaveLog.
  E. مشکل۴ — «قسمت پرامپت \n دیده میشه»: FLASH_PROMPT و
       FLASH_LITE_PROMPT بدونِ هیچ دنبالهٔ literalِ بک‌اسلش-n (۳۹ مورد
       پاک شد) — هم در کادرِ اپ هم در پرامپتِ واقعیِ مدل.
  F. مشکل۵ — «لاگ باید خودش بره پایین نه ثابت بمونه»:
       اندروید: همهٔ logBox.text=... از setLog میگذرند + اسکرولِ دومِ
       postDelayed(90) + logFollow=true در استارتِ هر اجرا؛
       وب (PC/لینوکس): attachFollow در client_restore_js (فالوِ
       دستیِ textarea با سابقهٔ دستِ کاربر).
  G. مشکل۶ — «قسمت لینک null نشون میده»: savedOr دیگر JSONObject.NULL
       را مقدار برنمیگرداند + dfltStr در شاخهٔ text (NULL/«null» = خالی).
  H. مشکل۷ — «اعلان دوتا ایکون اپ»: setLargeIcon حذف شد — فقط
       smallIcon (ic_notif) میماند.
  I. سلامتِ عمومی: py_compileِ manga.py/manga_app.py/bridge.py +
       YAMLِ workflowها + رگرسیونهایِ کلیدیِ ۱۹۰/۱۹۱ (sink، ko=v5،
       multi، detِ smallِ PC، نخِ ۲).
"""

import ast
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
_sink_kt = io.open(
    "android/ppocr-sdk/src/main/java/com/paddle/ocr/util/OcrProgressSink.kt",
    encoding="utf-8").read()

# ── A. نسخه ──────────────────────────────────────────────────────────
gate('APP_VER = "1.14.192"' in _manga, "A: APP_VERِ manga.py = 1.14.192")
gate('APP_VER = "1.14.192"' in _manga_app, "A: APP_VERِ manga_app.py = 1.14.192")
_v = {}
try:
    for ln in open("VERSION", encoding="utf-8"):
        if "=" in ln:
            k, val = ln.strip().split("=", 1)
            _v[k] = val
    gate(_v.get("versionCode") == "197"
         and _v.get("versionName") == "1.14.192",
         "A: VERSION = 1.14.192 / versionCode=197")
except Exception as e:
    fail(f"A: VERSION خوانده نشد: {e}")
gate("versionCode = 197" in _gradle and 'versionName = "1.14.192"' in _gradle,
     "A: build.gradle.kts = 197 / 1.14.192")
gate("دانلودی — v1.14.192" in _manga, "A: خطِ لاگِ آمادهشدنِ موتورِ گوشی = v1.14.192")

# ── B. مشکل۱: ضدِ حبابِ خالی (سه سد) ────────────────────────────────
gate("نجاتِ نهایی در translate_regions انجام شد" in _manga
     and "if self._force_translate_missing_1189(regions):\n                    print(\"    [✓] 192" in _manga,
     "B1: سدِ ۱ — نجاتِ نهاییِ 189 داخلِ translate_regions (خروجِ زودهنگامِ 403 هم پوشیده میشود)")
gate("_fb192: List[TextRegion] = []" in _manga
     and "_c192 = copy.copy(_r192)" in _manga
     and "_c192.translated_text = _r192.source_text" in _manga,
     "B2: سدِ ۲ — fallbackِ متنِ مبدأ رویِ «کپیِ» ناحیه در مسیرِ precleaned")
gate("(translated_regions + _fb192) if _fb192 else translated_regions" in _manga,
     "B2: سدِ ۲ — لیستِ رندر = ترجمهشدهها + فال‌بکهایِ ۱۹۲")
gate("حباب بدونِ ترجمه ولی پاکشده" in _manga
     and "ضدِ حبابِ خالی" in _manga,
     "B2: سدِ ۲ — پیامِ لاگِ [192] برایِ نجاتِ متنِ مبدأ")
gate("import copy" in _manga, "B2: import copy اضافه شد")
gate("((r.source_text or \"\").strip()\n                         or (r.translated_text or \"\").strip())" in _manga,
     "B3: سدِ ۳ — _clean_regions_for_page ناحیهٔ بی‌متن را پاک نمیکند")
gate("and (r.source_text or \"\").strip())\n        if missing_n:" in _manga,
     "B4: «حباب ترجمه نشد» فقط برایِ ناحیهٔ بامتن شمرده میشود")

# ── C. مشکل۲: آپدیتِ درون‌اپی ────────────────────────────────────────
gate("private fun checkAppUpdate(): Boolean" in _main_kt
     and "private fun checkAppUpdateWithRetry()" in _main_kt,
     "C: checkAppUpdate → Boolean + بستهٔ ۳تلاشیِ retry")
gate("Thread { checkAppUpdateWithRetry() }.start()" in _main_kt,
     "C: استارتِ اپ = مسیرِ retry")
gate("if (attempt == 1) 20_000L else 40_000L" in _main_kt,
     "C: فاصلهٔ تلاشها = ۲۰ و ۶۰ ثانیه")
gate("System.currentTimeMillis() - lastUpdCheckAt > 30 * 60_000L" in _main_kt,
     "C: چکِ دوبارهٔ onResume با سقفِ ۳۰ دقیقه")
gate("if (updRow == null &&" in _main_kt,
     "C: onResume فقط وقتی ردیفِ آپدیت هنوز نیامده چک میکند")

# ── D. مشکل۳: لاگهایِ Downloads/manga ───────────────────────────────
gate("private fun deleteAllMangaLogsInDownloads()" in _main_kt
     and "Thread { deleteAllMangaLogsInDownloads() }.start()" in _main_kt,
     "D: جارویِ لاگهایِ Downloads در لحظهٔ استارتِ هر اجرا")
gate("deleteAllMangaLogsOnStart() {\n        deleteAllMangaLogsInDownloads()" in _main_kt,
     "D: پاکسازیِ بازشدنِ اپ همان مسیرِ مشترک + لاگِ خصوصی")
gate("try { Thread.sleep(2500) } catch (_: Exception) {}\n                    synchronized(this@MainActivity) {\n                        cleanupLogDuplicates()\n                    }" in _main_kt,
     "D: پاسِ دومِ تضمینیِ cleanupLogDuplicates (۲.۵ ثانیه بعد از ذخیره)")

# ── E. مشکل۴: پرامپت بدونِ \nِ کپچری ────────────────────────────────
import re as _re
for _name in ("FLASH_PROMPT", "FLASH_LITE_PROMPT"):
    _m = _re.search(_name + r"\s*=\s*r'''(.*?)'''", _manga, _re.S)
    if not _m:
        fail(f"E: ثابتِ {_name} پیدا نشد")
        continue
    gate(_m.group(1).count("\\n") == 0,
         f"E: {_name} بدونِ هیچ دنبالهٔ literalِ \\n (کادرِ اپ + پرامپتِ مدل)")
gate("با \\\\n جدا کن" in _manga or "با \\n جدا کن" in _manga,
     "E: دستورِ عمدیِ «با \\n جدا کن» در پرامپتِ اجرا دستنخورده (رفتارِ دو-متنی)")

# ── F. مشکل۵: اسکرولِ خودکارِ لاگ ───────────────────────────────────
_direct = [ln for ln in _main_kt.splitlines()
           if "logBox.text = " in ln and "logBox.text = t" not in ln]
gate(not _direct,
     f"F: اندروید — همهٔ نوشتنِ لاگ از setLog میگذرد (0 مستقیم؛ شد {len(_direct)})")
gate("logBox.postDelayed({ scrollLogToBottom() }, 90)" in _main_kt
     and "private fun scrollLogToBottom()" in _main_kt,
     "F: اندروید — اسکرولِ دوم بعد از چیدمانِ نهایی (متنهایِ بلند)")
gate("logFollow = true" in _main_kt.split("private fun onStartJob")[1].split("runBtn.isEnabled = true")[0],
     "F: اندروید — هر اجرای تازه دوباره دنبالِ لاگ میشود")
gate("const attachFollow = () => {{" in _manga_app
     and "ta.addEventListener(\"wheel\", () => {{ ta._mangaFollow = atBottom(); }}, {{passive: true}});" in _manga_app,
     "F: وب (PC/لینوکس) — فالویِ دستیِ لاگ با سابقهٔ دستِ کاربر")
gate("setInterval(() => {{" in _manga_app
     and "ta.scrollTop = ta.scrollHeight" in _manga_app,
     "F: وب (PC/لینوکس) — پایشِ تغییرِ متنِ لاگ و پرش به ته")

# ── G. مشکل۶: «null» در قسمت لینک ───────────────────────────────────
gate("if (dflt === org.json.JSONObject.NULL) return null" in _main_kt,
     "G: savedOr — JSONObject.NULL دیگر مقدار حساب نمیشود")
gate("dflt == null || dflt === org.json.JSONObject.NULL -> \"\"" in _main_kt
     and "setText(saved.ifBlank { dfltStr })" in _main_kt,
     "G: شاخهٔ text — defaultِ null = رشتهٔ خالی (نه «null»)")
gate('s.equals("null", true) || s.equals("undefined", true)) "" else s' in _main_kt,
     "G: defaultِ رشته‌ایِ «null/undefined» هم خالی میشود")
gate('it.isNotBlank() && !it.equals("null", true)' in _main_kt,
     "G: مسیرِ «تست کلیدها/لینک» و خطایِ start_job هم ضدِ رشتهٔ «null» سختگیر شد")

# ── H. مشکل۷: اعلانِ تک‌آیکون ───────────────────────────────────────
gate(".setLargeIcon(" not in _service_kt,
     "H: setLargeIcon حذف شد — اعلان فقط یک آیکون دارد")
gate(".setSmallIcon(R.drawable.ic_notif)" in _service_kt,
     "H: smallIcon (漫) سرِ جایش است")

# ── I. سلامتِ عمومی + رگرسیونهایِ ۱۹۰/۱۹۱ ────────────────────────────
try:
    py_compile.compile("manga.py", doraise=True)
    py_compile.compile("manga_app.py", doraise=True)
    py_compile.compile("android/app/src/main/python/bridge.py", doraise=True)
    ok("I: py_compile manga.py + manga_app.py + bridge.py")
except Exception as e:
    fail(f"I: py_compile: {e}")

try:
    import yaml
    for y in (".github/workflows/build.yml",
              ".github/workflows/fetch_models.yml",
              ".github/workflows/android-emulator.yml"):
        yaml.safe_load(io.open(y, encoding="utf-8"))
    ok("I: YAMLِ workflowها سالم")
except Exception as e:
    fail(f"I: YAML: {e}")

gate("interface OcrProgressSink" in _sink_kt
     and "fun setProgressSink(sink: OcrProgressSink?)" in _store_kt,
     "I: رگرسیون — sinkِ پیشرفتِ دانلود (۱۹۰) سرِ جایش")
gate('"korean_PP-OCRv5_rec_mobile.onnx" to 12_000_000L' in _store_kt
     and "korean_PP-OCRv4_rec_mobile.onnx" not in _store_kt,
     "I: رگرسیون — ko = v5 + بدونِ v4 (۱۹۰)")
gate('"multi": "multi"' in _manga
     and "def _ocr_multi(self, buf):" in _manga,
     "I: رگرسیون — چندزبانه (۱۹۰)")
gate('"PP-OCRv6_medium_det_onnx.onnx" if _pc_det_medium()' in _manga,
     "I: رگرسیون — detِ PC = smallِ گوشی (۱۹۱)")

print()
if FAILS:
    print(f"✗ {len(FAILS)} گیتِ مردود:")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ همهٔ گیت‌هایِ v1.14.192 سبز است.")
