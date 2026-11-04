#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""گیت‌های v1.14.211 — مرزِ کاذب + همهٔ فیکس‌های ۲۱۰ پابرجا."""
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

m = re.search(r'APP_VER = "([\d.]+)"', mp)
gate("APP_VER = 1.14.211", m and m.group(1) == "1.14.211")
gate("VERSION = 1.14.211/215",
     "versionName=1.14.211" in ver and "versionCode=215" in ver)
gate("build.gradle.kts = 1.14.211/215",
     'versionName = "1.14.211"' in gradle and "versionCode = 215" in gradle)

# فیکسِ E — آستانهٔ عبورِ مرز
seg = mp.split("crossing = any(")[1][:600] if "crossing = any(" in mp else ""
gate("عبورِ مرز = ≥۸px در هر دو طرف (نه ±۲)",
     "seam - 8" in seg and "seam + 8" in seg and "seam - 2" not in seg)
gate("کامنتِ ریشهٔ مرزِ کاذب (211)",
     "دو فایلِ کاملاً نامرتبط به هم میچسبیدند" in mp)

# فیکس‌های ۲۱۰ پابرجا
gate("210: قفلِ سریالِ پاکسازی",
     "_page_clean_lock = threading.Lock()" in mp
     and "def _clean_image_page(" in mp)
gate("210: گاردِ عرضِ بومی در حالتِ مستقل", "_indep_keep_w = (" in mp)
gate("210: بچِ وب = کاما + بدونِ استیچ",
     '_batch_no_stitch = True' in app
     and 'cmd += ["--stitch-max-height", "0"]' in app)
gate("210: پاک‌کردنِ خروجی در هر اجرایِ آپلودی",
     "if up_files or (_prev_src and _prev_src != str(src)):" in app)
gate("209: قانونِ دو-عکسی", "ممنوع — قانونِ دو-عکسی" in mp)

print(f"\n==== {ok}/{ok + bad} گیت سبز ====")
sys.exit(0 if bad == 0 else 1)
