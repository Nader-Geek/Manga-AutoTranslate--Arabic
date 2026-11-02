#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.14.181/184 — «فقطِ یک موتور» رویِ گوشی + پاکسازیِ بازندهها.
از 184 موتورِ یگانه = SDKِ رسمیِ ppocr-android؛ هیچ فالبکِ ONNX در
مسیرِ موبایل نیست و مدلهایِ بازنده (حتی medium) از گوشی حذف میشوند."""
import ast
import io
import os
import re
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
cls = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}

# ۱) نردبان = تکروش
lad = cls.get("K3LadderOCR")
if lad is None:
    fail("K3LadderOCR نیست")
lad_src = ast.get_source_segment(src, lad) or ""
if '_K3_MODES = ("padandroid",)' not in lad_src:
    fail("تکروشِ padandroid نیست")
for gone in ("_engine(small", "_engine_tiny", "_k3_ink_coverage",
             "_k3_best_conf"):
    if gone in lad_src:
        fail("نردبانِ 184 هنوز %r دارد" % gone)
ok("نردبان = تکپلهٔ SDKِ رسمی")

# ۲) فالبکِ موبایل حذف؛ شکست = خروجیِ خالیِ صریح
rb_src = ast.get_source_segment(src, cls.get("RapidOCRBackend")) or ""
ime = re.search(r"def _init_mobile_engine.*?(?=\n    def )", rb_src, re.S)
ime_src = ime.group(0) if ime else ""
if "_build_mobile_onnx" in ime_src or "MANGA_ANDROID_OCR" in ime_src:
    fail("فالبکِ ONNX در _init_mobile_engine برگشته")
if "فالبکی نیست" not in ime_src or "self._mobile = None" not in ime_src:
    fail("شکستِ موتور = Noneِ صریح نیست")
ok("شکستِ SDK = خروجیِ خالیِ صریح (فالبکی نیست)")

# ۳) purgeِ بازندهها با مارکرِ 184
if '_PURGE_MARKER = ".onnx_loser_models_purged_184"' not in src:
    fail("مارکرِ 184 نیست")
if "_keep = ()" not in src:
    fail("_keep باید خالی باشد")
ok("پاکسازیِ بازندهها (medium هم)")

# ۴) نسخه
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
    print("[✗] گیتهایِ v1.14.181/184 شکست خورد")
    sys.exit(1)
print()
print("[✓] همهٔ گیتهایِ v1.14.181/184 PASS — تکموتور + purgeِ کامل")
