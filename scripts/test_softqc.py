#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تستِ عملیِ MANGA_SOFTQC — پرِ شیریِ LaMa رویِ بافتِ واقعی باید با
پرِ ردیفیِ حلقه نجات یابد؛ پرِ بافتِ سالم دست نخورد.
کالیبراسیون با صفحهٔ واقعیِ ژاپنیِ 184: LFCM ring_std واقعی = ۲۷–۴۰
(لاگِ گوشی) → بافتِ مصنوعی باید std ≥ ۱۴ بدهد و ردیفهایش ≤ ۲۶ بماند."""
import os
import sys

import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["MANGA_DARKSMOKE"] = "1"

import manga  # noqa: E402

H, W = 300, 300


def make_case(kind: str):
    """هر بار rngِ تازه — دو فراخوانیِ یک kind = خروجیِ بیت‌به‌بیت یکی."""
    rng = np.random.RandomState(7)
    img = np.full((H, W, 3), 190.0, np.float32)
    noise = rng.normal(0, 28.0, (H, W)).astype(np.float32)
    noise = cv2.blur(noise, (1, 3))
    img[..., 0] += noise
    img[..., 1] += noise * 0.9
    img[..., 2] += noise * 0.8
    img = np.clip(img, 0, 255).astype(np.uint8)
    msk = np.zeros((H, W), np.uint8)
    msk[80:220, 80:220] = 255
    out = img.copy()
    if kind == "milky":
        # پرِ شیری: فقط داخلِ ماسک — هموار + روشناییِ نزدیک به حلقه
        soft = cv2.GaussianBlur(img, (0, 0), 12)
        soft = cv2.addWeighted(soft, 0.9, np.full_like(soft, 190), 0.1, 0)
        out[msk > 0] = soft[msk > 0]
    elif kind == "healthy":
        # پرِ سالم: بافتِ همان‌جنسِ بازتولیدشده
        fill = img[80:220, 80:220].astype(np.float32).copy()
        nz = rng.normal(0, 28.0, fill.shape[:2]).astype(np.float32)
        nz = cv2.blur(nz, (1, 3))
        for c, k in ((0, 1.0), (1, 0.9), (2, 0.8)):
            fill[..., c] = np.clip(
                fill[..., c] * 0.15 + 190.0 * 0.85 + nz * k, 0, 255)
        out[80:220, 80:220] = fill.astype(np.uint8)
    return img, msk, out


def run_case(kind: str, gate_on: bool):
    img, msk, out = make_case(kind)
    os.environ["MANGA_SOFTQC"] = "1" if gate_on else "0"
    ctx = {"img_h": H, "img_w": W, "ex0": 0, "ey0": 0,
           "ex1": W, "ey1": H, "crop_img": img.copy(),
           "crop_msk": msk.copy()}
    members = [[80, 80, 220, 220, msk[80:220, 80:220].copy(), None, None]]
    sub = out.copy()
    kern = np.ones((3, 3), np.uint8)
    mt = manga.MangaTranslator.__new__(manga.MangaTranslator)
    mt.debug = False
    mt._promo_rect_boxes = None
    manga.MangaTranslator._lama_group_finish(mt, members, ctx, sub, kern)
    # خروجیِ واقعی = members[0][5] (برشِ 140×140 عضو) + members[0][4] (ماسک)
    return members[0][5], members[0][4]


fails = []

# ۰) سنجههایِ زمینه — باید معیارهایِ SOFTQC را پاس کند
img0, msk0, _ = make_case("milky")
qc = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
fm = msk0 > 0
ring = (cv2.dilate(msk0, qc) > 0) & (~fm)
g0 = cv2.cvtColor(img0, cv2.COLOR_BGR2GRAY)
rstd = float(g0[ring].std())
med0 = cv2.medianBlur(g0, 31)
hf0 = np.abs(g0.astype(np.int16) - med0.astype(np.int16))
print(f"    [سنجه] ring_std={rstd:.1f} (≥۱۴) hf_rg={np.median(hf0[ring]):.1f} (≥۷)")
if rstd < 14.0:
    fails.append("زمینهٔ مصنوعی texture ندارد — تست بیاعتبار")

# ۱) پرِ شیری + SOFTQC روشن → نجات (خروجی ≠ ورودیِ شیری)
on, _mk = run_case("milky", True)
_, _, milky = make_case("milky")
ref = milky[80:220, 80:220]
mk = _mk > 0
if np.array_equal(on[mk], ref[mk]):
    fails.append("SOFTQC پرِ شیری را نجات نداد")
else:
    print("[✓] SOFTQC پرِ شیری را با پرِ ردیفی نجات داد")

# ۲) پرِ سالم + SOFTQC روشن → دست‌نخورده (بدونِ false positive)
on_ok, _mk2 = run_case("healthy", True)
_, _, healthy = make_case("healthy")
ref2 = healthy[80:220, 80:220]
mk2 = _mk2 > 0
if np.array_equal(on_ok[mk2], ref2[mk2]):
    print("[✓] پرِ سالمِ بافت‌دار دست نخورد")
else:
    fails.append("پرِ سالمِ بافت‌دار خراب شد — false positive!")

# ۳) SOFTQC خاموش → پرِ شیری همان ورودی میماند (رفتارِ 185)
off, _mkt = run_case("milky", False)
if np.array_equal(off[_mkt > 0], ref[_mkt > 0]):
    print("[✓] SOFTQC خاموش = رفتارِ v1.14.185 (بیت‌به‌بیت)")
else:
    fails.append("SOFTQC خاموش خروجی را عوض کرد — گیت نشتی دارد!")

if fails:
    for f in fails:
        print(f"[✗] {f}")
    sys.exit(1)
print("[✓] SOFTQC: نجاتِ لکهٔ شیری + بدونِ false positive + گیتِ خاموشِ تمیز")
