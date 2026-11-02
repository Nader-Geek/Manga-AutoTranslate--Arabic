#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تستِ عملیِ MANGA_PROT_CACHE — خروجیِ کش باید بیت‌به‌بیت با بدونِ کش یکی باشد."""
import os
import sys

import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["MANGA_PROT_CACHE"] = "1"

import manga  # noqa: E402

rng = np.random.RandomState(42)
# صفحهٔ مصنوعی: زمینهٔ روشن + دیوارهایِ تیرهٔ نازک + متنِ تیره
img = np.full((480, 640, 3), 235, np.uint8)
cv2.rectangle(img, (40, 40), (600, 440), (30, 30, 30), 3)       # قابِ پنل
cv2.line(img, (320, 40), (320, 440), (30, 30, 30), 3)           # خطِ وسط
for yy in range(80, 420, 40):                                    # «متن»
    cv2.rectangle(img, (70, yy), (300, yy + 22), (40, 40, 40), -1)
    cv2.rectangle(img, (340, yy), (580, yy + 22), (40, 40, 40), -1)
raw = np.zeros((480, 640), np.uint8)
raw[70:430, 60:310] = 255
raw[70:430, 330:590] = 255


class _FakeRegions(list):
    pass


regions = _FakeRegions()


class _R:
    ocr_polys = []


regions.append(_R())

mt = manga.MangaTranslator.__new__(manga.MangaTranslator)
mt.debug = False
mt._page_raw_text_mask = raw
mt._spm_cache = None


def run(cache_env):
    os.environ["MANGA_PROT_CACHE"] = cache_env
    mt._spm_cache = None
    a = mt._structural_protect_mask(img, regions)
    b = mt._structural_protect_mask(img, regions, min_len=16, near_px=13)
    mt._spm_cache = None
    return a, b


a1, b1 = run("1")   # کش روشن
a0, b0 = run("0")   # کش خاموش — مسیرِ PC


def eq(x, y):
    if x is None and y is None:
        return True
    if x is None or y is None:
        return False
    return x.shape == y.shape and bool(np.array_equal(x, y))


ok = True
if not eq(a1, a0):
    print("[✗] protect با کش ≠ بدونِ کش")
    ok = False
else:
    print("[✓] protect: کش == بدونِ کش (بیت‌به‌بیت)")
if not eq(b1, b0):
    print("[✗] wall_band با کش ≠ بدونِ کش")
    ok = False
else:
    print("[✓] wall_band: کش == بدونِ کش (بیت‌به‌بیت)")
if mt._spm_cache is not None:
    print("[!] کش پاک نشده (محلِ فراخوانی باید None کند)")
    ok = False
else:
    print("[✓] کش بعد از استفاده پاک شد (بدونِ کهنشدگی)")

sys.exit(0 if ok else 1)
