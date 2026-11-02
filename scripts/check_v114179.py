#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.14.179/184 — «فلاتر-پدل» و همهٔ روشهایِ آزمایشگاهی حذف شدند.
فقط SDKِ رسمیِ ppocr-android میماند؛ Paddle-Lite همچنان ممنوع؛ PC
(متادیتایِ URLهایِ _RAPIDOCR_FILES) دستنخورده."""
import ast
import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILS = []


def fail(m):
    print("[✗]", m)
    FAILS.append(m)


def ok(m):
    print("[✓]", m)


src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
tree = ast.parse(src)

# ── ۱) روشهایِ حذفشده در نردبان نیستند ──────────────────────────
m = src.index("class K3LadderOCR:")
m2 = src.index("\nclass ", m + 10)
_k3_src = src[m:m2]
for gone in ('"flutter"', '_engine_tiny', '_build_onnx(small', "tiny=True"):
    if gone in _k3_src:
        fail("F: نردبانِ 184 هنوز %r دارد" % gone)
if '_K3_MODES = ("padandroid",)' not in _k3_src:
    fail("F: _K3_MODESِ 184 نیست")
ok("F: روشهایِ full/fast/rapid/paddle/flutter حذف — فقط padandroid")

# ── ۲) مهارِ Paddle-Lite + سلامتِ PC ─────────────────────────────
for _bad in ("PliteCropOCR", "_PLOCR_LiteRunner", "PliteProbeService.kt\"",
             "MANGA_K3_PLITE", "plite_banned"):
    if _bad in src:
        fail("P: %s برگشته!" % _bad)
_kt = os.path.join(ROOT, "android", "app", "src", "main", "java",
                   "com", "amirwolf", "mangatranslator", "MainActivity.kt")
if "PaddleLite" in io.open(_kt, encoding="utf-8").read():
    fail("P: Paddle-Lite در MainActivity برگشته")
_grad = io.open(os.path.join(ROOT, "android", "app", "build.gradle.kts"),
                encoding="utf-8").read()
if "PaddlePredictor" in _grad:
    fail("P: وابستگیِ PaddlePredictor برگشته")
_mf = os.path.join(ROOT, "android", "app", "src", "main",
                   "AndroidManifest.xml")
if "PliteProbeService" in io.open(_mf, encoding="utf-8").read():
    fail("P: سرویسِ :pliteprobe در مانیفست برگشته")
ok("P: Paddle-Lite برنگشته")

# ── ۳) PC: متادیتایِ URLهایِ مدلها (فقط data) دستنخورده ─────────
if "_RAPIDOCR_FILES" not in src:
    fail("P: _RAPIDOCR_FILES (متادیتایِ PC) نباید حذف میشد")
if "def _rapidocr_model_pair" not in src:
    fail("P: _rapidocr_model_pair (PC) نباید حذف میشد")
ok("P: PC بیت‌به‌بیت (_RAPIDOCR_FILES/_rapidocr_model_pair سرِ جایش)")

# ── ۴) نسخه ─────────────────────────────────────────────────────
ver = io.open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read()
_m = re.search(r'^APP_VER = "([\d.]+)"', src, re.M)
_vn = re.search(r"versionName=([\d.]+)", ver, re.M)
_vc = re.search(r"versionCode=(\d+)", ver, re.M)
if not _m or not _vn or _m.group(1) != _vn.group(1):
    fail("V: APP_VER/VERSION ناسازگار")
if _vc and int(_vc.group(1)) < 189:
    fail("V: versionCode باید ≥189 باشد")
ok("V: نسخهٔ %s / versionCode=%s"
   % (_m.group(1) if _m else "?", _vc.group(1) if _vc else "?"))

if FAILS:
    print()
    print("[✗] گیتهایِ v1.14.179/184 شکست خورد")
    sys.exit(1)
print()
print("[✓] همهٔ گیتهایِ v1.14.179/184 PASS — flutter/tiny حذف؛ "
      "Paddle-Lite ممنوع؛ PC سالم")
