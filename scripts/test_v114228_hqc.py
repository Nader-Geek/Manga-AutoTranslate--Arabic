#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.14.228 — تستِ واحدِ QCِ هماهنگیِ رنگِ پر (_fill_harmony_qc).

دستورِ سازنده: «معلومه از حباب داخل با بیرون حباب یکی حساب کرده یک
رنگ کرده» + «لگه قهوی سفید رنگی نیوفته» — پرِ خاکستری/سفیدِ ناهماهنگ
از هر پرکنندهای باید قبلِ کامپوز با رنگِ حلقهٔ خودِ قطعه درست شود و
مرزِ حباب، دو سمتِ جدا بگیرد. (رفتارِ واقعی رویِ img4 در
scripts/test_v114228_img4_metrics.py سنجیده میشود.)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402
import cv2  # noqa: E402

os.environ.setdefault("MANGA_ORPHAN_RESCUE", "0")

import manga  # noqa: E402

PASS = 0
FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [✓] {name}")
    else:
        FAIL += 1
        print(f"  [✗] {name} {extra}")


def _t():
    return object.__new__(manga.MangaTranslator)


def _case_gray_on_white():
    """پرِ خاکستری رویِ زمینهٔ سفید → به سفیدِ حلقه نزدیک میشود."""
    org = np.full((120, 300, 3), 255, np.uint8)
    zone = np.zeros((120, 300), bool)
    zone[40:80, 40:260] = True
    donor = org.copy()
    donor[zone] = (190, 190, 190)
    n = _t()._fill_harmony_qc(donor, org, zone, verbose=False)
    med = np.median(donor[zone].reshape(-1, 3), axis=0)
    check("خاکستری-روی-سفید → سفید",
          n >= 1 and float(med.min()) > 225,
          f"n={n} med={med}")


def _case_gray_on_purple():
    """پرِ خاکستری رویِ بنفش → بنفشِ حلقه."""
    org = np.full((120, 300, 3), (200, 170, 210), np.uint8)
    zone = np.zeros((120, 300), bool)
    zone[40:80, 40:260] = True
    donor = org.copy()
    donor[zone] = (190, 190, 190)
    n = _t()._fill_harmony_qc(donor, org, zone, verbose=False)
    med = np.median(donor[zone].reshape(-1, 3), axis=0)
    check("خاکستری-روی-بنفش → بنفش",
          n >= 1 and abs(float(med[0]) - 200) < 14
          and abs(float(med[2]) - 210) < 14,
          f"n={n} med={med}")


def _case_correct_untouched():
    """پرِ درست (سفید رویِ سفید) → بدونِ دخالت."""
    org = np.full((100, 200, 3), 255, np.uint8)
    zone = np.zeros((100, 200), bool)
    zone[30:70, 30:170] = True
    donor = org.copy()
    donor[zone] = (252, 252, 252)
    n = _t()._fill_harmony_qc(donor, org, zone, verbose=False)
    check("پرِ درست دستنخورده", n == 0, f"n={n}")


def _case_busy_art_not_flattened():
    """حلقهٔ شلوغ (بافتِ هنر) → «تختِ همرنگِ حلقه» نمیشود."""
    rng = np.random.RandomState(7)
    org = rng.randint(40, 220, (140, 300, 3)).astype(np.uint8)
    zone = np.zeros((140, 300), bool)
    zone[50:90, 60:240] = True
    donor = org.copy()
    donor[zone] = (120, 120, 120)
    n = _t()._fill_harmony_qc(donor, org, zone, verbose=False)
    reg = donor[zone].reshape(-1, 3).astype(np.float32)
    std_after = float(np.std(reg))
    med_after = np.median(reg, axis=0)
    ring_med = np.median(org[~zone].reshape(-1, 3), axis=0)
    flat_ring = std_after < 6.0 and float(np.abs(
        med_after - ring_med).max()) < 6.0
    check("حلقهٔ شلوغ → تختِ همرنگِ حلقه نمیشود", not flat_ring,
          f"n={n} std={std_after:.0f} med={med_after} ring={ring_med}")


def _case_ink_cluster_not_darkening():
    """بلوکِ متراکم: پر نباید به رنگِ جوهرِ جامانده تیره شود."""
    org = np.full((200, 300, 3), 255, np.uint8)
    zone = np.zeros((200, 300), bool)
    for yb in (30, 90, 150):
        zone[yb:yb + 52, 30:270] = True
        org[yb + 5:yb + 47, 34:266:6] = 35
    donor = org.copy()
    donor[zone] = (225, 225, 225)
    n = _t()._fill_harmony_qc(donor, org, zone, verbose=False)
    dark_frac = float((donor[zone].reshape(-1, 3).max(axis=1)
                       < 120).mean())
    check("خوشهٔ جوهری پر را تیره نمیکند", dark_frac < 0.10,
          f"n={n} dark={dark_frac:.2f}")


def _case_no_zone_no_crash():
    """زونِ خالی / ابعادِ ناهمخوان → بدونِ کرش."""
    org = np.zeros((50, 50, 3), np.uint8)
    z = np.zeros((50, 50), bool)
    n1 = _t()._fill_harmony_qc(org.copy(), org, z, verbose=False)
    n2 = _t()._fill_harmony_qc(None, org, z, verbose=False)
    check("ورودیِ خالی/ناهمخوان", n1 == 0 and n2 == 0, f"{n1},{n2}")


print("── QCِ هماهنگیِ رنگِ پر (228) ──")
_case_gray_on_white()
_case_gray_on_purple()
_case_correct_untouched()
_case_busy_art_not_flattened()
_case_ink_cluster_not_darkening()
_case_no_zone_no_crash()
print(f"\nنتیجه: {PASS} سبز / {FAIL} قرمز")
sys.exit(1 if FAIL else 0)
