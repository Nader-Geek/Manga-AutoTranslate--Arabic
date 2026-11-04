#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""گیت‌های v1.14.210 — بچِ وب = حالتِ تکی + قفلِ سریالِ پاکسازی.

۱) نسخه در سه جا هم‌گام (manga.py APP_VER / VERSION / build.gradle.kts)
۲) قفلِ سریالِ پاکسازی: clean_image پوستهٔ قفل‌دار + بدنه در _clean_image_page
۳) گاردِ خوشهٔ عرض: صفحاتِ مستقلِ بدونِ استیچ عرضِ بومی را نگه میدارند
۴) manga_app: بچِ چند-فایلی = کاما-جدا + --stitch-max-height 0
۵) manga_app: پاک‌کردنِ خروجی در هر اجرایِ آپلودی (کشِ resumeِ کهنه)
"""
import io
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ok = 0
bad = 0


def gate(name, cond):
    global ok, bad
    if cond:
        ok += 1
        print(f"[✓] {name}")
    else:
        bad += 1
        print(f"[✗] {name}")


mp = io.open(os.path.join(REPO, "manga.py"), encoding="utf-8").read()
app = io.open(os.path.join(REPO, "manga_app.py"), encoding="utf-8").read()
ver = io.open(os.path.join(REPO, "VERSION"), encoding="utf-8").read()
gradle = io.open(os.path.join(REPO, "android", "app", "build.gradle.kts"),
                 encoding="utf-8").read()

# ۱) نسخه
m = re.search(r'APP_VER = "([\d.]+)"', mp)
gate("APP_VER = 1.14.210", m and m.group(1) == "1.14.210")
gate("VERSION = 1.14.210/214",
     "versionName=1.14.210" in ver and "versionCode=214" in ver)
gate("build.gradle.kts = 1.14.210/214",
     'versionName = "1.14.210"' in gradle and "versionCode = 214" in gradle)

# ۲) قفلِ سریال
gate("قفلِ کلاسیِ _page_clean_lock تعریف شد",
     "_page_clean_lock = threading.Lock()" in mp)
gate("clean_image = پوستهٔ قفل‌دار",
     "def clean_image(" in mp and "_clean_image_page(image, regions)" in mp
     and "with _lk:" in mp)
gate("بدنه = _clean_image_page (نواحیِ صفحه همچنان ذخیره)",
     "def _clean_image_page(" in mp
     and "self._page_regions = list(regions or [])" in mp.split(
         "def _clean_image_page(")[1][:2000])

# ۳) گاردِ خوشهٔ عرض
seg = mp.split("_indep_keep_w = (")[1][:900] if "_indep_keep_w = (" in mp else ""
gate("گاردِ _indep_keep_w (مستقل + بدونِ استیچ)",
     "_independent_pages" in seg and "stitch_max_height" in seg
     and "wmap = {i: widths[i] for i in range(len(valid_files))}" in seg)

# ۴) بچِ وب = کاما + بدونِ استیچ
gate("manga_app: بچ = کاما-جدا (نه پوشه)",
     '_bf_sorted = sorted(os.listdir(batch_dir))' in app
     and 'src = ",".join(' in app)
gate("manga_app: --stitch-max-height 0 برایِ بچ",
     '_batch_no_stitch = True' in app
     and 'cmd += ["--stitch-max-height", "0"]' in app)

# ۵) پاک‌کردنِ خروجی در هر اجرایِ آپلودی
gate("manga_app: پاک‌کردنِ خروجی در هر اجرایِ آپلودی",
     "if up_files or (_prev_src and _prev_src != str(src)):" in app)

# ۶) رگرسیونِ 209 — قانونِ دو-عکسی هنوز پابرجا
gate("209: بلوکِ باندِ تیره فقط نوار (کلِ بلوک ممنوع)",
     "ممنوع — قانونِ دو-عکسی" in mp)
gate("209: اینتریورِ باکسِ سیستم یکجا ممنوع",
     "یکجا ممنوع" in mp)
gate("209: ناحیهٔ ocr_empty در فیلترِ بچ",
     "or getattr(r, \"ocr_empty\", False))]" in mp)

print(f"\n==== {ok}/{ok + bad} گیت سبز ====")
sys.exit(0 if bad == 0 else 1)
