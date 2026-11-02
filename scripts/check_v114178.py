#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.14.178/184 — «تستِ سرعت» = یک پنجره رویِ روشِ یگانه.
سرعتِ SDKِ رسمیِ ppocr-android رویِ کراپهایِ واقعی/کاشیهایِ جایگزین
اندازهگیری میشود؛ بدونِ پنجرههایِ روشهایِ دیگر و بدونِ EP."""
import ast
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time

import numpy as np

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
wanted = ["speed_test_run", "_speed_test_pool", "_speed_test_window",
          "_speed_test_tiles", "speed_test_load", "_speed_test_save",
          "_speed_test_path"]
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in wanted:
        picks[node.name] = ast.get_source_segment(src, node)
for node in tree.body:
    if isinstance(node, ast.Assign) and getattr(
            node.targets[0], "id", "") == "_K3_MODE_FA":
        picks["_K3_MODE_FA"] = ast.get_source_segment(src, node)
m = src.index("class K3LadderOCR:")
m2 = src.index("\nclass ", m + 10)
picks["K3LadderOCR"] = src[m:m2]

E2E = r'''
import io, json, os, sys, time
import numpy as np, cv2
ROOT = os.environ["ROOT"]
ST_DIR = os.environ["ST_DIR"]
PER = float(os.environ.get("ST_PER", "0.10"))
src = io.open(os.path.join(ROOT, "manga.py"), encoding="utf-8").read()
import ast
tree = ast.parse(src)
picks = {}
wanted = ["speed_test_run", "_speed_test_pool", "_speed_test_window",
          "_speed_test_tiles", "speed_test_load", "_speed_test_save",
          "_speed_test_path"]
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in wanted:
        picks[node.name] = ast.get_source_segment(src, node)
for node in tree.body:
    if isinstance(node, ast.Assign) and getattr(
            node.targets[0], "id", "") == "_K3_MODE_FA":
        picks["_K3_MODE_FA"] = ast.get_source_segment(src, node)
m = src.index("class K3LadderOCR:")
m2 = src.index("\nclass ", m + 10)
picks["K3LadderOCR"] = src[m:m2]

class FakePad:
    """قراردادِ PaddleAndroidOCR: r0 = [ [[box, (text, conf)], ...] ]"""
    def ocr(self, image, crop_mode=False):
        box = [[0, 0], [image.shape[1], 0],
               [image.shape[1], image.shape[0]], [0, image.shape[0]]]
        pair = ("BOX", 0.9) if not crop_mode else ("t", 0.95)
        return [[[box, pair]]]

class FakeMT:
    @staticmethod
    def _imread_any(p):
        return cv2.imread(p)

_pad = FakePad()
g = {"os": os, "time": time, "json": json, "np": np, "cv2": cv2,
     "threading": __import__("threading"), "print": print,
     "APP_VER": "1.14.184-test",
     "_K3_STATS": {"ms": 0.0, "n": 0, "st1": 0, "st2": 0, "st3": 0},
     "_PAD_STATS": {"ms": 0.0, "n": 0, "lines": 0},
     "_k3_stats_note": lambda *a, **k: None,
     "_k3_boost_crop": lambda image, *a, **k: (image, None, 1.0),
     "_k3_map_boxes": lambda r, pad=None, scale=1.0: (r or []),
     "MangaTranslator": FakeMT,
     "RapidOCRBackend": object}
exec(compile("\n\n".join(picks.values()), "manga_bits", "exec"), g)

os.environ["MANGA_FILES_DIR"] = ST_DIR
img = np.full((1200, 900, 3), 128, np.uint8)
cv2.imwrite(os.path.join(ST_DIR, "page.png"), img)

class FakeBE:
    def __init__(self, lang="en"):
        self.lang = lang
        self._mobile = g["K3LadderOCR"](
            lang, build_pad=lambda: _pad)
    def _build_paddle_android(self, lang):
        return _pad

lines = []
res = g["speed_test_run"](
    src=os.path.join(ST_DIR, "page.png"), langs=("en",), per_mode=PER,
    log=lines.append, backend=FakeBE())
stf = os.path.join(ST_DIR, "speed_test.json")
assert res and os.path.isfile(stf), "نتیجه/فایل نبود"
d = json.load(io.open(stf, encoding="utf-8"))
modes = [k for k, v in d["ladder_ms"].items() if v]
assert set(modes) == {"padandroid"}, d["ladder_ms"]
wlines = [ln for ln in lines if ln.startswith("[⚡] (") and "میانگینِ" in ln]
assert len(wlines) == 1, wlines
assert not any("شتاب‌دهندهٔ" in ln and ln.startswith("[⚡] (")
              for ln in lines), \
    "پنجرهٔ EP برگشته: %s" % lines[:6]
print("E2E_OK", json.dumps({"crops": d["crops"], "ladder": d["ladder"]},
                           ensure_ascii=False))
'''

with tempfile.TemporaryDirectory() as td:
    env = dict(os.environ)
    env["ROOT"] = ROOT
    env["ST_DIR"] = td
    env["ST_PER"] = "0.10"
    r = subprocess.run([sys.executable, "-c", E2E], env=env,
                       capture_output=True, text=True, timeout=300)
    out = r.stdout + r.stderr
    if r.returncode != 0 or "E2E_OK" not in out:
        print(out[-3500:])
        fail("E2E: زیرپروسه شکست خورد")
    d = json.loads(out.split("E2E_OK", 1)[1].split("\n", 1)[0])
    ok("E2E: یک پنجره (padandroid) اندازهگیری شد + ذخیره؛ EPها نیستند")

# کاشیهایِ جایگزین هنوز سرِ جایشان
if "_speed_test_tiles(page)" not in (ast.get_source_segment(
        src, next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                  and n.name == "speed_test_run")) or ""):
    fail("فالبکِ کاشی در speed_test_run نیست")
ok("فالبکِ کاشی (بنبستِ ۱۷۸) سرِ جایش")

if FAILS:
    print()
    print("[✗] گیتهایِ v1.14.178/184 شکست خورد")
    sys.exit(1)
print()
print("[✓] همهٔ گیتهایِ v1.14.178/184 PASS — یک دکمه، یک پنجره، SDKِ رسمی")
