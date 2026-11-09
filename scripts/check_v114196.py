#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.196 — «حالتهایِ کدم کلا عوض شه به سبکِ مرجع:
قبلاً ۱۵تا۱۵ ترجمه میفرستادم — حذف کن؛ استخراجش هم همینجوری بود، ۱۵تا
میرسید متوقف میشد پاکسازی میکرد بعد ادامه میداد؛ حالا اول همهٔ عکسها
استخراج بزنه، بعد تموم شد متنهایِ استخراجشده بده به AI، همزمان هم
پاکسازیش انجام بده — حالتِ ۱۵تا۱۵تا حذف شه، مثلِ مرجع بشه» (دستورِ سازنده).

گیتها:
  A. نسخه = 1.14.196 / versionCode=201 (manga.py + manga_app.py + VERSION
     + gradle) + سطرهایِ apkArm64/apkArmv7a/apkUniversal در VERSION.
  B. حذفِ «۱۵تا۱۵تا» از ترجمه: دیگر هیچ حلقه/برشی که بافرِ دیالوگ را
     میانهٔ کار به بستههایِ ۱۵تایی بفرستد وجود ندارد (while len(…)>=
     min_batch حذف؛ سدِ دستهٔ ۱۴.165 و MANGA_CLEAN_PAR حذف)؛ کلِ بافر
     بعد از استخراجِ همهٔ صفحهها در «یک» درخواست میرود
     (chapter_one_request → _make_batches یک بستهٔ کامل).
  C. حذفِ توقفِ استخراج: در حلقهٔ اصلی دیگر _wait_batch_clean_barrier
     نیست؛ پاکسازیٔ هر صفحه بلافاصله بعد از استخراجش در پسزمینه
     (_clean_pages_bg([page_i])) صف میشود — «همزمان هم پاکسازیش».
  D. درخواستِ کلِ فصل به سبکِ مرجع رویِ مسیرِ Gemini:
     استریم (generate_content_stream) + پارسرِ بخشندهٔ افزایشی
     (_salvage_stream_items: regexِ شیءهایِ کاملِ {id,translation} داخلِ
     جریانِ ناقص + unescape) + فالبکِ مسیرِ عادی + سقفِ زمانیِ متناسبِ
     طولِ فصل + هر ۴ دستهٔ HARM = BLOCK_NONE (با فلگِ _sbn_ok برای مدلِ
     نپذیرنده) + قاعدهٔ ضدِ ردکردنِ [CENSORED] در پرامپت.
  E. سلامتِ عمومی: py_compileِ manga.py/manga_app.py + نبودنِ ارجاعِ
     مردهٔ سدِ دسته + رسیدگیِ فلاشِ پایانی در clean_only.
"""

import io
import os
import py_compile
import re
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
gate('APP_VER = "1.14.196"' in _manga, "manga.py: APP_VER = 1.14.196")
gate('APP_VER = "1.14.196"' in _manga_app, "manga_app.py: APP_VER = 1.14.196")
gate("versionCode = 201" in _gradle, "gradle: versionCode = 201")
gate('versionName = "1.14.196"' in _gradle, "gradle: versionName = 1.14.196")
gate("versionCode=201" in _version, "VERSION: versionCode=201")
gate("versionName=1.14.196" in _version, "VERSION: versionName=1.14.196")
for _ln in ("apkArm64=", "apkArmv7a=", "apkUniversal="):
    gate(_ln in _version, f"VERSION: سطرِ {_ln.rstrip('=')} هست")

print("── B. حذفِ ۱۵تا۱۵تا از ترجمه ────────────────")
gate("while len(dialogue_buffer) >= min_batch:" not in _manga,
     "حلقهٔ برشِ ۱۵تاییِ _queue_dialogues حذف شده")
gate("chapter_one_request = True" in _manga,
     "فلگِ chapter_one_request در سازنده روشن است")
gate("if getattr(self, \"chapter_one_request\", False):\n                return [list(items)]" in _manga,
     "_make_batches در سبکِ مرجع کلِ بچ را یک درخواست میفرستد")
gate("_flush_translate_buffer(force=True)" in _manga,
     "فلاشِ پایانی: کلِ بافر بعد از استخراجِ همهٔ صفحهها میرود")
gate("if dialogue_buffer and not getattr(self, \"clean_only\", False):\n            _flush_translate_buffer(force=True)" in _manga,
     "فلاشِ پایانی در clean_only اجرا نمیشود")
gate("cap = max(min_batch, int(getattr(self, \"bubbles_per_request\", 15) or 15))\n                chunk = dialogue_buffer[:cap]" not in _manga,
     "برشِ capِ ۱۵تاییِ بافری حذف شده")
gate("انتظارِ پیشرونده" in _manga and "_preview_ready_pages(force=True)" in _manga,
     "انتظارِ پیشروندهٔ ترجمه + پیشنمایشِ زنده سرِ جایش است")

print("── C. حذفِ توقفِ استخراج (پاکسازیِ همزمان) ──")
gate("_wait_batch_clean_barrier" not in _manga,
     "سدِ دستهٔ ۱۴.165 کلاً حذف شده (نه تعریف، نه صدا)")
gate("_batch_clean_futs" not in _manga, "ثبتِ فیوچرهایِ سدِ دسته حذف شده")
gate("MANGA_CLEAN_PAR" not in _manga, "متغیرِ محیطیِ سدِ دسته حذف شده")
gate("_clean_pages_bg([page_i])" in _manga,
     "پاکسازیٔ هر صفحه بلافاصله بعد از استخراجش در پسزمینه صف میشود")
gate("دستهٔ ۱۵تایی پر شد" not in _manga,
     "پیامِ «استخراج متوقف تا پاکسازیِ بسته» حذف شده")
gate("سبکِ مرجع: اول استخراجِ همهٔ" in _manga,
     "پیامِ سبکِ مرجع در ابتدایِ کار")
gate("clean_pool = ThreadPoolExecutor(\n            max_workers=1" in _manga,
     "صفِ تک‌نمونهٔ پاکسازی (ضدِ قفلِ منابع) سرِ جایش است")

print("── D. درخواستِ کلِ فصل به سبکِ مرجع ──────────")
gate("def _salvage_stream_items" in _manga,
     "پارسرِ بخشندهٔ مرجع (_salvage_stream_items) اضافه شده")
gate('r\'"id"\\s*:\\s*(\\d+)\\s*,\\s*"translation"\\s*:\\s* \'' in _manga.replace("\n                r'", "\n                r'") or '"id"\\s*:\\s*(\\d+)\\s*,\\s*"translation"' in _manga,
     "regexِ شیءهایِ کاملِ {id, translation} در پارسر")
gate("json.loads('\"' + _m.group(2) + '\"')" in _manga,
     "unescapeِ رشتهٔ ترجمه با json.loads")
gate("generate_content_stream" in _manga,
     "استریمِ Gemini (generate_content_stream) وصل شده")
gate("_salvage_stream_items(\n                                \"\".join(_parts), on_item)" in _manga,
     "پارسرِ افزایشی رویِ هر قطعهٔ استریم اجرا میشود")
gate("client.models.generate_content(\n                            model=model, contents=user_prompt, config=config,\n                        )" in _manga,
     "فالبکِ مسیرِ عادی وقتی استریم ممکن نشود")
gate("30.0 + 1.5 * len(work_regions)" in _manga,
     "سقفِ زمانیِ متناسبِ طولِ فصل برایِ درخواستِ بزرگ")
gate("timeout: float = None) -> str:" in _manga.replace(
        "                              timeout: float = None) -> str:",
        "timeout: float = None) -> str:"),
     "_call_ai_with_timeout پارامترِ timeout دارد")
gate("HARM_CATEGORY_HARASSMENT" in _manga and "HARM_CATEGORY_HATE_SPEECH" in _manga
     and "HARM_CATEGORY_SEXUALLY_EXPLICIT" in _manga
     and "HARM_CATEGORY_DANGEROUS_CONTENT" in _manga,
     "هر ۴ دستهٔ HARM در safety_settings")
gate("HarmBlockThreshold.BLOCK_NONE" in _manga,
     "آستانهٔ BLOCK_NONE (سبکِ مرجع)")
gate("self._sbn_ok = False" in _manga,
     "مدلی BLOCK_NONE را نپذیرد → فلگ میشود و بدونِ آن ادامه میدهد")
gate("[CENSORED]" in _manga,
     "قاعدهٔ ضدِ ردکردنِ [CENSORED] در پرامپت")
gate("استریم: {len(_applied)}/" in _manga,
     "پیشرفتِ زندهٔ «X از Y» در استریم")

print("── E. سلامتِ عمومی ─────────────────────────")
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
gate("def _translate_chunk_bg" in _manga and "trans_pool.submit(_job)" in _manga,
     "موتورِ ترجمهٔ پسزمینه سرِ جایش است")
gate("pending_by_page[page_i] = pending_by_page.get(page_i, 0) + queued" in _manga,
     "حسابِ دیالوگهایِ هر صفحه (نهاییِ درست) دستنخورده")
gate("_account_chunk(chunk)" in _manga,
     "کسرِ دیالوگهایِ ترجمهشده از حسابِ صفحه دستنخورده")

print()
if FAILS:
    print(f"[✗] {len(FAILS)} گیتِ مردود:")
    for _f in FAILS:
        print(f"    - {_f}")
    sys.exit(1)
print("[✓] همهٔ گیتهایِ v1.14.196 سبز.")
