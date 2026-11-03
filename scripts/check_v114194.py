#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.194 — «کلِ صفحه رفرش میشه میره میاد تو یک ثانیه
انگار چراغ خاموش روشن کردی … قسمتهایی که متن نداره خالیه — وقتی متن
نباشه شکلِ لودینگ بیار جایِ متن؛ متنش ترجمه شد بذار سرجاش … تو اپ اپدیت
جدید دکمه دانلودش نمیاد» (گزارشِ سازنده).

گیتها:
  A. نسخه = 1.14.194 / versionCode=199 (manga.py + manga_app.py +
     VERSION + gradle) + سطرهایِ apkArm64/apkArmv7a/apkUniversal در
     VERSION (ریشهٔ «دکمه دانلودش نمیاد»).
  B. نشانِ لودینگِ حبابِ درانتظار: _draw_loading_marks_1194 + فراخوانی
     فقط در پیشنمایش (final=False + precleaned) — رندرِ نهایی هرگز.
  C. قراردادِ rect=(x, y, عرض، ارتفاع) در نشان (ضدِ باگِ گوشهفرضی).
  D. تعویضِ بیفلاش: hotSwap در reader.html و قالبِ وب؛ مسیرِ قدیمیِ
     «src مستقیم» در pollMtimes هر دو حذف شده.
  E. دکمهٔ دانلود: فالبکِ ABI در MainActivity + حذفِ «بیصدا آپدیت را
     دور بریز» + برچسبِ «دانلود و نصب».
  F. رگرسیونهایِ ۱۹۳/۱۹۲/۱۹۰/۱۹۱ + سلامتِ عمومی (py_compile + YAML).
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
_version = io.open("VERSION", encoding="utf-8").read()
_reader = io.open("android/app/src/main/assets/reader.html",
                  encoding="utf-8").read()

# ── A. نسخه ──────────────────────────────────────────────────────────
gate('APP_VER = "1.14.194"' in _manga, "A: manga.py APP_VER = 1.14.194")
gate('APP_VER = "1.14.194"' in _manga_app,
     "A: manga_app.py APP_VER = 1.14.194")
gate("versionCode=199" in _version and "versionName=1.14.194" in _version,
     "A: VERSION = 199 / 1.14.194")
gate("versionCode = 199" in _gradle and 'versionName = "1.14.194"' in _gradle,
     "A: gradle = 199 / 1.14.194")
gate(("apkArm64=" in _version and "apkArmv7a=" in _version
      and "apkUniversal=" in _version
      and "releases/download/apk/MangaTranslator-arm64.apk" in _version
      and "releases/download/apk/MangaTranslator-armv7a.apk" in _version
      and "releases/download/apk/MangaTranslator-universal.apk" in _version),
     "A: VERSION سطرهایِ APKِ ریلیزِ apk را دارد (لینکِ ثابتِ CI)")

# ── B. نشانِ لودینگِ حبابِ درانتظار ──────────────────────────────────
gate("def _draw_loading_marks_1194" in _manga,
     "B: متدِ _draw_loading_marks_1194 تعریف شده")
gate("self._draw_loading_marks_1194(" in _manga,
     "B: نشان از finish_page_phase صدا زده میشود")
gate("if (not final and precleaned is not None\n"
     "                and not getattr(self, \"clean_only\", False)):" in _manga,
     "B: نشان فقط در پیشنمایش (final=False + precleaned + غیرِ clean-only)")
_wait_block = _manga[_manga.find("_wait_regions = [r for r in dialogue_regions"):]
_wait_block = _wait_block[:_wait_block.find("if _wait_regions")]
gate("not (r.translated_text or \"\").strip()" in _wait_block
     and "not getattr(r, \"ocr_empty\", False)" in _wait_block
     and "(r.source_text or \"\").strip()" in _wait_block,
     "B: فقط حبابِ «بامتنِ مبدأ ولی بیترجمه» لودینگ میگیرد")
gate(_manga.find("def _draw_loading_marks_1194")
     < _manga.find("def process_core"),
     "B: نشان قبل از process_core جای گرفته (ساختارِ کلاس سالم)")

# ── C. قراردادِ rect ────────────────────────────────────────────────
gate("_rx, _ry, _rw, _rh = r.rect" in _manga
     and "int(_rx + _rw) - 1" in _manga,
     "C: نشان rect را (x, y, عرض، ارتفاع) میخواند (ضدِ باگِ گوشهفرضی)")
gate("cv2.ellipse(img, (cx, cy), (rad, rad), _spin % 360," in _manga,
     "C: قوسِ لودینگ با چرخشِ زمانی رسم میشود")

# ── D. تعویضِ بیفلاش در دو نمایشگر ──────────────────────────────────
gate("const hotSwap = (el, url) => {" in _reader
     and "hotSwap(el, nu);" in _reader,
     "D: reader.html — hotSwap تعریف و در pollMtimes بهکار رفته")
gate("el.setAttribute('src', el.dataset.src)" not in _reader,
     "D: reader.html — تعویضِ مستقیمِ src حذف شده")
_tpl = _manga_app[_manga_app.find("_LIVE_READER_TMPL = "):]
_tpl = _tpl[:_tpl.find('"""', _tpl.find("<script>"))]
gate("function hotSwap(el, url){" in _tpl
     and "hotSwap(el, P + curDir()" in _tpl,
     "D: قالبِ نمایشگرِ وب — hotSwap تعریف و بهکار رفته")
gate("el.src = P + curDir() + 'live_' + pad(slot) + '.jpg?r=' + Date.now();"
     not in _tpl,
     "D: قالبِ نمایشگرِ وب — تعویضِ مستقیمِ src حذف شده")

# ── E. دکمهٔ دانلودِ آپدیت ───────────────────────────────────────────
gate("if (base.isEmpty()) return true" not in _main_kt,
     "E: مسیرِ «بیصدا آپدیت را دور بریز» حذف شد")
gate("val baseUrl = base.ifEmpty {" in _main_kt
     and "releases/download/apk/" in _main_kt
     and "MangaTranslator-arm64.apk" in _main_kt
     and "MangaTranslator-universal.apk" in _main_kt,
     "E: فالبکِ ABIِ لینکِ ثابتِ ریلیزِ apk در MainActivity")
gate("⬇ دانلود و نصب" in _main_kt,
     "E: برچسبِ دکمه = «دانلود و نصب» وقتی فایل هنوز نیست")

# ── F. سلامتِ عمومی + رگرسیونهایِ ۱۹۳/۱۹۲/۱۹۰/۱۹۱ ───────────────────
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

# رگرسیونِ ۱۹۳ — سدِ نهایی + سه مسیرِ final=True + ضدِ صفحهٔ تمامسفید
gate("final: bool = False," in _manga
     and "for _g_round in range(1, 4):" in _manga
     and "except (GeminiQuotaExhausted, JobCancelled):" in _manga,
     "F: رگرسیونِ 193 — سدِ نهاییِ ۳دوری + کوتا/لغو")
gate("finish_page_phase(image, regions, final=True)" in _manga
     and "if _clean_regions or _fb192:" in _manga,
     "F: رگرسیونِ 193 — final=True در process_core + ضدِ صفحهٔ تمامسفید")
gate("_c192 = copy.copy(_r192)" in _manga
     and "_c192.translated_text = _r192.source_text" in _manga,
     "F: رگرسیونِ 192 — فال‌بکِ متنِ مبدأ رویِ «کپیِ» ناحیه")
gate("if missing_n and final:" in _manga,
     "F: رگرسیونِ 193 — هشدارِ «حباب ترجمه نشد» فقط در نهایی")
gate("نجاتِ نهایی در translate_regions انجام شد" in _manga,
     "F: رگرسیونِ 192 — نجاتِ نهایی در translate_regions")
gate("private fun checkAppUpdate(): Boolean" in _main_kt
     and "checkAppUpdateWithRetry()" in _main_kt,
     "F: رگرسیونِ 192 — آپدیتِ درون‌اپیِ ۳تلاشی (دستنخورده)")
gate("logBox.postDelayed({ scrollLogToBottom() }, 90)" in _main_kt,
     "F: رگرسیونِ 192 — اسکرولِ خودکارِ لاگ")
gate(".setLargeIcon(" not in _service_kt,
     "F: رگرسیونِ 192 — اعلانِ تک‌آیکون")
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
print("✓ همهٔ گیت‌هایِ v1.14.194 سبز است.")
