#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.14.176/184 — «آزمایشگاهِ سرعت» = تکروشِ SDKِ رسمی.
speed_lab_env هر envِ کهنه را پاک میکند، همیشه MANGA_K3_MODE=padandroid
را force میکند و پاکسازیِ مدلهایِ بازنده (حتی medium) را صدا میزند؛
پیامِ لاگ = SDKِ رسمیِ PaddleOCR اندروید (PP-OCRv6_smallِ باندل)."""
import ast
import io
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILS = []


def fail(m):
    print("[✗]", m)
    FAILS.append(m)


def ok(m):
    print("[✓]", m)


src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
tree = ast.parse(src)
picks = {}
wanted = ["speed_lab_env", "speed_test_load", "_speed_test_path",
          "_purge_loser_onnx_models", "_fmt_mb"]
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in wanted:
        picks[node.name] = ast.get_source_segment(src, node)
for node in tree.body:
    if isinstance(node, ast.Assign) and getattr(
            node.targets[0], "id", "") in ("_SPEED_LAB_LADDER", "_K3_MODE_FA"):
        picks[getattr(node.targets[0], "id", "")] = \
            ast.get_source_segment(src, node)
missing = [w for w in ("speed_lab_env", "_purge_loser_onnx_models")
           if w not in picks]
if missing:
    fail("توابعِ لازم استخراج نشد: %s" % missing)

lab = picks.get("speed_lab_env") or ""
if 'os.environ["MANGA_K3_MODE"] = "padandroid"' not in lab:
    fail("forceِ padandroid در speed_lab_env نیست")
if 'os.environ.pop("MANGA_MOBILE_OCR_EP", None)' not in lab:
    fail("پاکسازیِ EPِ کهنه در speed_lab_env نیست")
if "RapidOCRِ اندروید" not in lab or \
        "PP-OCRv6" not in lab:
    fail("پیامِ RapidOCR در speed_lab_env نیست")

# ── عملی: execِ sandbox — envِ کهنه پاک + force + پیام ──
import time  # noqa: E402

g = {"os": os, "time": time, "json": json, "print": print,
     "APP_VER": "1.14.184-test",
     "_SPEED_LAB_EP": ("auto",),
     "_K3_MODE_FA": {"padandroid": "پدلِ رسمیِ اندروید"},
     "_K3_STATS": {"ms": 0.0, "n": 0, "st1": 0, "st2": 0, "st3": 0},
     "_PAD_STATS": {"ms": 0.0, "n": 0, "lines": 0},
     "_fmt_mb": lambda b: "%dMB" % (b // (1024 * 1024)),
     "_android_gate": lambda *a, **k: False,
     "_purge_loser_onnx_models": lambda: "",
     "speed_test_load": lambda: None,
     "speed_test_path": lambda: ""}
try:
    exec(compile("\n\n".join(picks.values()), "lab_bits", "exec"), g)
except Exception as e:
    fail("execِ sandbox شکست خورد: %r" % e)

os.environ["MANGA_MOBILE_OCR_EP"] = "nnapi"
os.environ["MANGA_K3_MODE"] = "flutter"
try:
    ret = g["speed_lab_env"]({})
    if os.environ.get("MANGA_K3_MODE") != "padandroid":
        fail("forceِ padandroid اعمال نشد")
    if os.environ.get("MANGA_MOBILE_OCR_EP") is not None:
        fail("EPِ کهنه پاک نشد")
    if "RapidOCRِ اندروید" not in ret or \
            ("v1.14.184" not in ret and "v1.14.185" not in ret
             and "v1.14.187" not in ret and "v1.14.188" not in ret):
        fail("پیامِ خروجیِ 184/187/188 نیست: %r" % ret[:120])
    ok("عملی: EP پاک + padandroid force + پیامِ 184/187/188")
finally:
    os.environ.pop("MANGA_MOBILE_OCR_EP", None)
    os.environ.pop("MANGA_K3_MODE", None)

if FAILS:
    print()
    print("[✗] گیتهایِ v1.14.176/184 شکست خورد")
    sys.exit(1)
print()
print("[✓] همهٔ گیتهایِ v1.14.176/184 PASS — آزمایشگاه = تکروشِ SDKِ رسمی")
