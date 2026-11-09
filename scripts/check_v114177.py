#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""چکِ رگرسیونِ v1.14.177 (بهروزِ 184) — کلیدهایِ «آزمایشگاهِ سرعت» نیستند.
از 181 دکمهٔ «تستِ سرعت» و کلیدهایِ پنل حذف شدند؛ از 184 تنها روش =
SDKِ رسمی — speed_lab_env پارامترِ p را نمیخواند و همیشه padandroid
را force میکند؛ MainActivity هم کلیدهایِ کهنه را نمیفرستد."""
import ast
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILS = []


def fail(m):
    print("[x]", m)
    FAILS.append(m)


def ok(m):
    print("[✓]", m)


src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
ma = io.open(os.path.join(ROOT, "manga_app.py"),
             encoding="utf-8").read()
mk = io.open(os.path.join(
    ROOT, "android/app/src/main/java/com/amirwolf/mangatranslator/"
    "MainActivity.kt"), encoding="utf-8", errors="ignore").read()

# ۱) پنل — هیچ کلیدِ آزمایشگاهی نیست
for gone in ("ocr_ep", "ocr_ladder", "ocr_threads", "ocr_detcap",
             "ocr_boost", "ocr_speedtest"):
    if '"%s"' % gone in ma:
        fail("کلیدِ کهنهٔ %s هنوز در manga_app.py است" % gone)
ok("پنل: هیچ کلیدِ آزمایشگاهی نیست (حذفِ 181)")

# ۲) MainActivity — کلیدهایِ کهنه را collect نمیکند
for gone in ("ocr_ep", "ocr_ladder", "ocr_detcap", "ocr_boost"):
    if '"%s"' % gone in mk:
        fail("کلیدِ کهنهٔ %s هنوز در MainActivity.kt است" % gone)
ok("MainActivity: کلیدهایِ کهنه حذف")

# ۳) speed_lab_env — پارامترِ p خوانده نمیشود + forceِ padandroid
tree = ast.parse(src)
lab = None
for n in ast.walk(tree):
    if isinstance(n, ast.FunctionDef) and n.name == "speed_lab_env":
        lab = ast.get_source_segment(src, n)
if lab is None:
    fail("speed_lab_env نیست")
else:
    if "p.get(" in lab:
        fail("speed_lab_env هنوز پارامترِ p را میخواند")
    if 'os.environ["MANGA_MT_MODE"] = "padandroid"' not in lab:
        fail("forceِ padandroid نیست")
    ok("speed_lab_env = تکروشِ padandroid (بدونِ خواندنِ p)")

# ۴) نسخه — سازگاریِ APP_VER با VERSION
ver = io.open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read()
_m = re.search(r'^APP_VER = "([\d.]+)"', src, re.M)
_vn = re.search(r"versionName=([\d.]+)", ver, re.M)
if not _m or not _vn or _m.group(1) != _vn.group(1):
    fail("V: APP_VER/VERSION ناسازگار")
ok("V: نسخهٔ سازگار (%s)" % (_m.group(1) if _m else "?"))

if FAILS:
    print()
    print("[x] گیتهایِ v1.14.177/184 شکست خورد")
    sys.exit(1)
print()
print("[✓] همهٔ گیتهایِ v1.14.177/184 PASS — آزمایشگاهِ کهنه حذف؛ تکروشِ رسمی")
