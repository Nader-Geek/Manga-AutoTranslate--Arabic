#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.197 — «استخراج از عکس اول تا آخر بره و از آخر تا
اول — دو طرفه؛ وسطش پاکسازیش همزمان کار کنه از بالا به پایین؛ وقتی
استخراج تموم شد پاکسازیش هم دوطرفه کار کنه (دوطرفه فقط بعد از اتمامِ
کاملِ استخراج)» + فیکسِ تایم‌اوتِ مترجمِ پر متن به سبکِ K3 (گزارش:
«متن زیاد باشه تایم اوت میخوره — k3 متن زیاد چکار کرده؟؟»).

گیتها:
  A. نسخه = 1.14.197 / versionCode=202 (manga.py + manga_app.py + VERSION
     + gradle) + سطرهایِ apkArm64/apkArmv7a/apkUniversal در VERSION.
  B. استخراج دوطرفه: دو کارگر (fwd از صفحهٔ ۱، bwd از صفحهٔ آخر؛ دیدار
     در وسط) + قفلِ صفِ دیالوگ + پرچمِ title_skip فقط مالِ صفحهٔ ۰ +
     مرتبسازیِ رواییِ بافر قبل از درخواستِ واحد.
  C. پاکسازی دوفازی: فاز ۱ حینِ استخراج = جاروی بالا→پایین
     (min(cand))؛ فاز ۲ فقط بعد از extraction_done = نصف از بالا→پایین
     + نصف از پایین→بالا (reversed) با کارگرِ clean2؛ انتظارِ پاکسازی
     با Event (_wait_clean/_clean_ready) — clean_futuresِ قدیمی حذف.
  D. فیکسِ تایم‌اوت به سبکِ K3: سقفِ متناسبِ حجم (۶۰ + ۱.۵×تعداد +
     حجم/۴۰، سقفِ ۱۸۰۰) برایِ «هر» provider (نه فقط Gemini)؛ استریمِ
     SSE در _translate_with_openai با پارسرِ افزایشیِ همان
     _salvage_stream_items + فالبکِ «استریم پذیرفته نشد»؛ AutoRetryِ
     همهمدل (MANGA_TIMEOUT_RETRIES/WAIT، انتظارِ نمایی ۲/۴/۸… سقف ۳۰)
     بهجایِ صبرِ ۰.۵ثانیه و cascadeِ بیفایده؛ حذفِ آیتمهایِ نشسته از
     پرامپتِ تلاشِ بعدی.
  E. سلامتِ عمومی: py_compile + بقایِ سبکِ K3ِ ۱۹۶ (یک درخواست، بدونِ
     ۱۵تا۱۵تا، salvage، BLOCK_NONE، [CENSORED]).
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
_version = io.open("VERSION", encoding="utf-8").read()

print("── A. نسخه ─────────────────────────────────")
gate('APP_VER = "1.14.197"' in _manga, "manga.py: APP_VER = 1.14.197")
gate('APP_VER = "1.14.197"' in _manga_app, "manga_app.py: APP_VER = 1.14.197")
gate("versionCode = 202" in _gradle, "gradle: versionCode = 202")
gate('versionName = "1.14.197"' in _gradle, "gradle: versionName = 1.14.197")
gate("versionCode=202" in _version, "VERSION: versionCode=202")
gate("versionName=1.14.197" in _version, "VERSION: versionName=1.14.197")
for _ln in ("apkArm64=", "apkArmv7a=", "apkUniversal="):
    gate(_ln in _version, f"VERSION: سطرِ {_ln.rstrip('=')} هست")

print("── B. استخراج دوطرفه ───────────────────────")
gate("def _claim_ext(role" in _manga, "ادعای صفحه از دو سر (_claim_ext)")
gate('if role == "fwd":' in _manga and '_ext_bwd["v"] = b - 1' in _manga,
     "کارگرِ جلو از ابتدا، کارگرِ عقب از انتها برمیدارد")
gate('args=("fwd",)' in _manga and 'args=("bwd",)' in _manga,
     "دو رشتهٔ extract-fwd و extract-bwd همزمان (join هر دو)")
gate("if f > b:\n                    return None" in _manga,
     "دیدار در وسط (f > b → پایانِ کارگر)")
gate("استخراج دوطرفه: صفحهٔ ۱→" in _manga,
     "پیامِ اعلانِ استخراج دوطرفه")
gate("with _qd_lock:\n                            _queue_dialogues" in _manga,
     "صفِ دیالوگ زیرِ قفل (دو کارگرِ همزمان)")
gate("if page_i == 0:\n                MangaTranslator._title_skip_enabled = True" in _manga,
     "پرچمِ title_skip فقط توسطِ صفحهٔ ۰ ست میشود")
gate("if page_i == 0:  # v1.14.197 — فقط مالکِ پرچم پاک کند" in _manga,
     "…و فقط توسطِ همان صفحه پاک میشود (بدونِ رقابتِ دو کارگر)")
gate("dialogue_buffer.sort(key=lambda r: page_of_region.get(r.id, 0))" in _manga,
     "بافر قبل از درخواستِ واحد به ترتیبِ طبیعیِ صفحهها مرتب میشود")
gate("except JobCancelled as e:\n                    _ext_err[\"exc\"] = e" in _manga,
     "لغوِ کاربر در کارگر ذخیره و در رشتهٔ اصلی دوباره برمیخیزد")

print("── C. پاکسازی دوفازی ──────────────────────")
gate("pi = min(cand)  # بالا→پایین" in _manga,
     "فاز ۱ حینِ استخراج: همیشه کمترینِ صفحۀِ آماده (بالا→پایین)")
gate("extraction_done[\"v\"] = True" in _manga,
     "پرچمِ «استخراج کامل شد» بعد از joinِ هر دو کارگر")
gate("return  # ماندهها → فازِ دوطرفه" in _manga,
     "فاز ۱ بعد از اتمامِ استخراج برایِ فاز ۲ جا میگذارد")
gate("_top_seq, _bot_seq = _backlog[:_mid], _backlog[_mid:]" in _manga,
     "فاز ۲: باقیماندهٔ صف نصف میشود")
gate("list(reversed(_bot_seq))" in _manga,
     "فاز ۲: نیمۀِ دوم از پایین→بالا (دیدار در وسط)")
gate('thread_name_prefix="clean2"' in _manga,
     "کارگرِ دومِ فازِ دوطرفه (clean2)")
gate("پاکسازی دوطرفه: {len(_top_seq)} صفحه از بالا→پایین، " in _manga,
     "پیامِ اعلانِ فازِ دوطرفه")
gate("def _wait_clean(page_i" in _manga and "def _clean_ready(page_i" in _manga,
     "انتظارِ پاکسازی با Event (_wait_clean/_clean_ready)")
gate("clean_futures" not in _manga,
     "clean_futuresِ قدیمی کاملاً حذف شد")
gate("_clean_pages_bg([page_i])" in _manga,
     "پاکسازیِ همزمانِ هر صفحه بعد از استخراجش (بقایِ ۱۹۶)")
gate("if clean_pool2 is not None:  # v1.14.197 — کارگرِ پایین→بالا" in _manga,
     "خاموشیِ امنِ clean_pool2 در پایان")

print("── D. فیکسِ تایم‌اوت به سبکِ K3 ────────────")
gate("_want_stream = (\n                    getattr(self, \"chapter_one_request\", False)\n                    and len(work_regions) > 6)" in _manga,
     "استریم/سقفِ بزرگ دیگر مخصوصِ Gemini نیست — برایِ هر provider")
gate("60.0 + 1.5 * len(work_regions) + _chars / 40.0" in _manga,
     "سقفِ متناسبِ حجم: ۶۰ + ۱.۵×تعداد + حجم/۴۰")
gate("1800.0," in _manga, "سقفِ مطلق ۳۰ دقیقه")
gate("text = self._translate_via_provider(\n                            user_prompt, system_instruction,\n                            timeout=_tout, on_item=_on_item)" in _manga,
     "timeout/on_item به مسیرِ provider هم پاس میشود")
gate("def _translate_with_openai(self, user_prompt: str, system_instruction: str,\n                               *, structured: bool = True,\n                               timeout: float = None,\n                               on_item=None) -> str:" in _manga,
     "_translate_with_openai پارامترِ timeout/on_item دارد")
gate("_eff_t = max(_eff_t,\n                         float(getattr(self, \"api_timeout\", 45.0) or 45.0))" in _manga,
     "سقفِ HTTP هم به همان سقفِ بزرگ میرسد (نه ۱۰–۴۵ ثانیه)")
gate("skw[\"stream\"] = True" in _manga,
     "استریمِ SSE در مسیرِ openai/custom (سبکِ K3)")
gate("self._salvage_stream_items(\"\".join(parts), on_item)" in _manga,
     "پارسرِ افزایشی رویِ هر قطعهٔ استریمِ openai")
gate('"stream" in _ss and ("support" in _ss or "invalid" in _ss' in _manga,
     "فالبکِ خودکار فقط وقتی endpoint استریم را نمیپذیرد")
gate("صبر ۰.۵ثانیه و تلاش دوباره" not in _manga,
     "رفتارِ قدیمیِ «فقط ۱ تلاش با صبرِ ۰.۵ثانیه» حذف شد")
gate("AutoRetry K3 " in _manga, "پیامِ AutoRetry K3 در لاگ")
gate("MANGA_TIMEOUT_RETRIES" in _manga and "MANGA_TIMEOUT_WAIT" in _manga,
     "قابلِ تنظیم با MANGA_TIMEOUT_RETRIES/WAIT")
gate("same_retries < _k3_max:" in _manga,
     "همان مدلِ «کند ولی سالم» تا K3_max بار دوباره پرسیده میشود")
gate("min(_k3_wait * (2 ** same_retries), 30.0)" in _manga,
     "انتظارِ نمایی ۲/۴/۸… تا سقفِ ۳۰ثانیه")
gate("_still = [r for r in work_regions\n                              if not (r.translated_text or \"\").strip()]" in _manga,
     "آیتمهایِ نشسته از جریانِ قبلی از تلاشِ بعدی حذف میشوند")
gate("_k3_max = min(10, max(1, int(" in _manga,
     "سقفِ K3: حداکثر ۱۰ بار (قابلِ تنظیم، پیشفرض ۳)")

print("── E. سلامتِ عمومی + بقایِ سبکِ K3ِ ۱۹۶ ────")
try:
    py_compile.compile("manga.py", doraise=True)
    ok("py_compile: manga.py")
except Exception as _e:
    fail(f"py_compile: manga.py — {_e}")
try:
    py_compile.compile("manga_app.py", doraise=True)
    ok("py_compile: manga_app.py")
except Exception as _e:
    fail(f"py_compile: manga_app.py — {_e}")
gate("while len(dialogue_buffer) >= min_batch:" not in _manga,
     "۱۹۶: حلقهٔ برشِ ۱۵تایی سرِ حذف است")
gate("if getattr(self, \"chapter_one_request\", False):\n                return [list(items)]" in _manga,
     "۱۹۶: کلِ فصل = یک درخواست")
gate("if dialogue_buffer and not getattr(self, \"clean_only\", False):\n            _flush_translate_buffer(force=True)" in _manga,
     "۱۹۶: فلاشِ پایانی (بدونِ clean_only) سرِ جایش است")
gate("def _salvage_stream_items" in _manga,
     "۱۹۶: پارسرِ بخشندهٔ استریم سرِ جایش است")
gate("HarmBlockThreshold.BLOCK_NONE" in _manga and "[CENSORED]" in _manga,
     "۱۹۶: BLOCK_NONE + قاعدهٔ [CENSORED] سرِ جایش است")
gate("_wait_batch_clean_barrier" not in _manga and "MANGA_CLEAN_PAR" not in _manga,
     "۱۹۶: سدِ دستهٔ قدیمی برگشته نیست")

print()
if FAILS:
    print(f"✗ {len(FAILS)} گیتِ مردود:")
    for _f in FAILS:
        print(f"  - {_f}")
    sys.exit(1)
print("✓ همهٔ گیتهایِ v1.14.197 سبز.")
