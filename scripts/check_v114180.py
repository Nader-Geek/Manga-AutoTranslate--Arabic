#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.14.180/184 — پاکسازیِ مدلهایِ بازنده: از 184 حتی medium هم بازنده
است (موتورِ گوشی = SDKِ رسمی با PP-OCRv6_smallِ باندل) — _keep = خالی.
گیتِ اندروید (MANGA_PURGE_ONNX_MODELS) — PC دستنخورده."""
import ast
import io
import json
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILS = []


def fail(m):
    print("[✗]", m)
    FAILS.append(m)


def ok(m):
    print("[✓]", m)


src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()

if '_PURGE_MARKER = ".onnx_loser_models_purged_184"' not in src:
    fail("مارکرِ 184 نیست")
tree = ast.parse(src)
seg = None
for n in tree.body:
    if isinstance(n, ast.FunctionDef) and \
            n.name == "_purge_loser_onnx_models":
        seg = ast.get_source_segment(src, n)
if seg is None:
    fail("_purge_loser_onnx_models پیدا نشد")
if "_keep = ()" not in seg:
    fail("_keep باید خالی باشد (medium هم بازنده است)")
if "PP-OCRv6_medium_det_onnx.onnx" in seg.split("_keep = ()")[1]:
    fail("بعد از _keep = () نباید keepِ medium بماند")
ok("purge: _keep خالی + مارکرِ 184")

# عملی: sandbox — dirِ فیک؛ فقط فایلهایِ فهرستشده حذف میشوند
CH = r'''
import io, json, os, sys, time
src = io.open(os.path.join(os.environ["ROOT"], "manga.py"),
              encoding="utf-8").read()
import ast
tree = ast.parse(src)
seg = None
for n in tree.body:
    if isinstance(n, ast.FunctionDef) and n.name == "_purge_loser_onnx_models":
        seg = ast.get_source_segment(src, n)
names = {"PP-OCRv6_medium_det_onnx.onnx", "PP-OCRv6_medium_rec_onnx.onnx",
         "PP-OCRv6_medium_rec_inference.yml", "PP-OCRv6_tiny_det.onnx",
         "PP-OCRv6_det_small.int8.onnx"}
os.environ["MANGA_FILES_DIR"] = os.environ["ST_DIR"]
g = {"os": os, "time": time, "APP_VER": "t",
     "_PURGE_MARKER": ".onnx_loser_models_purged_184",
     "_RAPIDOCR_FILES": names, "_K3_PURGE_EXTRA": (),
     "_android_gate": lambda k: True,
     "_fmt_mb": lambda b: "%dMB" % (b // (1024 * 1024))}
d = os.path.join(os.environ["ST_DIR"], "rapidocr_models")
os.makedirs(d, exist_ok=True)
for n in names | {"keep.bin"}:
    io.open(os.path.join(d, n), "wb").write(b"x" * 1024)
g["_fmt_mb"] = lambda b: "0MB"
g["_purge_loser_onnx_models"] = None
exec(compile(seg, "purge", "exec"), g)
ret = g["_purge_loser_onnx_models"]()
left = sorted(os.listdir(d))
assert left == [".onnx_loser_models_purged_184", "keep.bin"], left
assert os.path.isfile(os.path.join(
    d, ".onnx_loser_models_purged_184"))
assert ("v1.14.184" in ret or "v1.14.187" in ret), ret
print("PURGE_OK")
'''
with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ)
    env["ROOT"] = ROOT
    env["ST_DIR"] = td
    r = subprocess.run([sys.executable, "-c", CH], env=env,
                       capture_output=True, text=True, timeout=120)
    out = r.stdout + r.stderr
    if r.returncode != 0 or "PURGE_OK" not in out:
        print(out[-2000:])
        fail("PURGE: زیرپروسه شکست خورد")
    else:
        ok("عملی: medium/tiny/tiny-yml حذف؛ ناگزیر حفظ؛ مارکر نوشته شد")

# PC: گیتِ اندروید
if "_android_gate(" not in seg:
    fail("purge باید زیرِ گیتِ اندروید باشد")
ok("گیتِ اندروید (PC دستنخورده)")

if FAILS:
    print()
    print("[✗] گیتهایِ v1.14.180/184 شکست خورد")
    sys.exit(1)
print()
print("[✓] همهٔ گیتهایِ v1.14.180/184 PASS — purgeِ کاملِ بازندهها")
