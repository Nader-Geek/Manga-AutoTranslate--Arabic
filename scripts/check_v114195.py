#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.195 — «نسخه 1.14.194 هنوز مشکل چشمک داره؛ هر متنِ
جدیدی که اضافه میکنه صفحه سیاه میکنه تو چند صدم ثانیه انگار عکس کامل از
اول لود میشه … دیباگ دو بار نشون میده هم دیباگِ قبلی هست هم دیباگِ تمومشده
هم مجدد همون عکس نشون میده» (گزارشِ سازنده + ویدیو).

گیتها:
  A. نسخه = 1.14.195 / versionCode=200 (manga.py + manga_app.py + VERSION
     + gradle) + سطرهایِ apkArm64/apkArmv7a/apkUniversal در VERSION.
  B. ریشهٔ «دیباگ دو بار»: دیباگِ هر صفحه با «اسلاتِ صریحِ خودش»
     (slot=page_i+1) در live_debug مینشیند — ریزِ دومِ حلقهٔ ذخیرهٔ نهایی
     همان فایل را بهروز میکند؛ هیچ فایلِ تکراریای ساخته نمیشود.
  C. ضدِ چشمکِ سیاه — پوشانهٔ دوبلِ hotSwap در هر دو نمایشگر: تصویرِ نو
     رویِ تصویرِ قدیم نقش میبندد (position:absolute روی همان مختصات)، src
     زیرِ پوشانه عوض میشود، بعد از دیکود پوشانه برداشته میشود؛ تعویضِ
     همزمان صف میشود؛ مسیرِ قدیمیِ «پردیکودِ Imageِ بیرونی» (بیاثر — جوابِ
     intercept در کشِ حافظه نمیماند) حذف شده.
  D. رِویلِ بعدازدیکودِ اسلاتِ تازه (نهایی + دیباگ): placeholder تا دیکودِ
     کامل سرِ جایش میماند؛ imgِ جدا از DOM با loading=eager (lazyِ جدا از
     DOM هرگز نمیآید) و بعد از درج به مدیریتِ لودِ تدریجی سپرده میشود.
  E. رگرسیون: تستِ عملیِ ۱۹۵ سبز، سناریوهایِ ۱۹۳ سبز، چکِ ۱۹۴ فقط
     ۴ گیتِ نسخهاش مردود (طبقِ روالِ چکِ نسخهای) + سلامتِ عمومی.
"""

import io
import os
import py_compile
import re
import subprocess
import sys
import tempfile

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
_reader = io.open("android/app/src/main/assets/reader.html",
                  encoding="utf-8").read()

# ---------- A. نسخه ----------
gate('APP_VER = "1.14.195"' in _manga, "A: manga.py APP_VER = 1.14.195")
gate('APP_VER = "1.14.195"' in _manga_app, "A: manga_app.py APP_VER = 1.14.195")
gate("versionCode=200" in _version and "versionName=1.14.195" in _version,
     "A: VERSION = 200 / 1.14.195")
gate("versionCode = 200" in _gradle and 'versionName = "1.14.195"' in _gradle,
     "A: gradle = 200 / 1.14.195")
for _k in ("apkArm64", "apkArmv7a", "apkUniversal"):
    gate(f"{_k}=https://github.com/amirwolf512k/Manga-AutoTranslate/releases/download/apk/"
         in _version, f"A: VERSION سطرِ {_k} دارد (دکمهٔ دانلودِ درون‌اپی)")

# ---------- B. اسلاتِ صریحِ دیباگ ----------
gate("def _live_dump(src, dbg: bool = False, key: Optional[str] = None,\n"
     "               slot: Optional[int] = None) -> None:" in _manga,
     "B: _live_dump پارامترِ slot را دارد")
gate("if slot is None and key is not None:" in _manga and
     "and not dbg" not in _manga.split("def _live_dump")[1].split("def _live_page_dump")[0],
     "B: رجیستریِ key دیگر دیباگ را مسدود نمیکند (شرطِ «and not dbg» حذف شد)")
gate("_live_dump(dbg_out, dbg=True, slot=page_i + 1)" in _manga,
     "B: ریزِ دیباگِ _finish_page_now با slot=page_i+1")
gate("_live_dump(dbg, dbg=True, slot=page_i + 1)" in _manga,
     "B: ریزِ دیباگِ حلقهٔ ذخیرهٔ نهایی با همان slot=page_i+1 (تکرار حذف شد)")
gate("v1.14.195 — slot: شمارهٔ اسلاتِ صریح" in _manga,
     "B: سندِ _live_dump ریشهٔ «دیباگ دو بار» را ثبت میکند")

# ---------- C. پوشانهٔ دوبلِ hotSwap ----------
for _name, _src in (("reader.html", _reader), ("قالبِ وب", _manga_app)):
    gate("__swapBusy" in _src and "__swapNext" in _src,
         f"C: {_name} — تعویضِ همزمانِ hotSwap صف میشود")
    gate("ov.remove()" in _src and "ov.decode" in _src and "el.decode" in _src,
         f"C: {_name} — پوشانه دیکود، رویِ قدیم مینشیند، بعد از دیکودِ اصلی برداشته میشود")
    gate("position:absolute;z-index:6" in _src,
         f"C: {_name} — پوشانه absolute رویِ همان مختصاتِ اسلات")
    gate("offsetLeft" in _src and "offsetTop" in _src and
         "offsetWidth" in _src and "offsetHeight" in _src,
         f"C: {_name} — مختصاتِ پوشانه از خودِ اسلات خوانده میشود")
gate(".rdrC .lg{width:100%;position:relative}" in _reader,
     "C: reader.html — .lg position:relative (فضایِ مختصاتِ پوشانه)")
gate(".c{max-width:min(100%,900px);margin:0 auto;width:100%;position:relative}" in _manga_app,
     "C: قالبِ وب — .c position:relative (فضایِ مختصاتِ پوشانه)")
gate("pre = new Image();" not in _reader,
     "C: مسیرِ قدیمیِ «پردیکودِ Imageِ بیرونی» حذف شد (در WebView اندروید بیاثر بود)")
gate("hotSwap(el, nu)" in _reader and "hotSwap(el, nx)" in _reader,
     "C: reader.html — pollMtimes همان hotSwap را صدا میزند + صفِ دوباره")
gate("function hotSwap(el, url){" in _manga_app and
     "hotSwap(el, P + curDir() + 'live_' + pad(slot) + '.jpg?r=' + Date.now())" in _manga_app,
     "C: قالبِ وب — hotSwap تعریف و در pollMtimes بهکار رفته")

# ---------- D. رِویلِ بعدازدیکود ----------
gate(_reader.count("__pend") >= 6 and "'eager'" in _reader and _reader.count("mgImg(im)") >= 2,
     "D: reader.html — رِویلِ نهایی و دیباگ: eager + بعدازدیکود + سپردن به لودِ تدریجی")
gate("__pend" in _manga_app and "'eager'" in _manga_app,
     "D: قالبِ وب — رِویلِ بعدازدیکودِ اسلاتِ تازه")

# ---------- E. رگرسیون ----------
def _run(args):
    return subprocess.run([sys.executable] + args, capture_output=True,
                          text=True, timeout=1200)

_r = _run(["scripts/test_v114195_debug_slot_noflash.py"])
gate(_r.returncode == 0, "E: تستِ عملیِ v1.14.195 (اسلاتِ دیباگ + ضدهایِ چشمک) سبز است")

_r = _run(["scripts/test_v114193_live_gate.py"])
gate(_r.returncode == 0, "E: سناریوهایِ v1.14.193 هنوز سبز است")

_r = _run(["scripts/test_v114194_loading_flicker.py"])
_failed = [ln for ln in (_r.stdout or "").splitlines() if ln.startswith("  - G:")]
gate(_r.returncode != 0 and len(_failed) == 3,
     f"E: چکِ ۱۹۴ فقط ۳ گیتِ نسخهاش مردود است (دیده‌شده: {len(_failed)})")

try:
    py_compile.compile("manga.py", doraise=True)
    py_compile.compile("manga_app.py", doraise=True)
    py_compile.compile("android/app/src/main/python/bridge.py", doraise=True)
    ok("E: py_compile — manga.py / manga_app.py / bridge.py سالم")
except Exception as e:
    fail(f"E: py_compile — {e}")

try:
    import yaml  # noqa: E402
    for _y in (".github/workflows/build.yml",
               ".github/workflows/fetch_models.yml",
               ".github/workflows/android-emulator.yml"):
        yaml.safe_load(io.open(_y, encoding="utf-8"))
    ok("E: workflows — YAML سالم")
except Exception as e:
    fail(f"E: workflows — {e}")

print()
if FAILS:
    print(f"[!] {len(FAILS)} گیتِ مردود:")
    for m in FAILS:
        print("   -", m)
    sys.exit(1)
print("[✓] همهٔ گیتهایِ v1.14.195 سبز است.")
