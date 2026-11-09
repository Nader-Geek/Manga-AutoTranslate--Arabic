#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تحلیلِ بقایای پاکسازی: کراپِ هر ناحیهٔ متنی از اورجینال و خروجی،
یافتن اجزای متصلِ تیرهٔ باقیمانده در خروجی داخل ناحیه، اندازه/موقعیت."""

import sys
import cv2
import numpy as np


def analyze(orig_path, out_path, pad=30, ink_thr=90, min_area=2,
            max_area=4000, focus=None):
    o = cv2.imread(orig_path)
    c = cv2.imread(out_path)
    if o.shape != c.shape:
        c = cv2.resize(c, (o.shape[1], o.shape[0]))
    H, W = o.shape[:2]
    gray_o = cv2.cvtColor(o, cv2.COLOR_BGR2GRAY)
    gray_c = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY)
    # جاهایی که خروجی «تیره» است = بقایای احتمالیِ جوهر
    dark_c = (gray_c < ink_thr).astype(np.uint8)
    dark_o = (gray_o < ink_thr).astype(np.uint8)
    # بقایای واقعی = تیره در خروجی، در ناحیهٔ تغییرکرده (diff) یا حتی بدونِ تغییر
    diff = (np.abs(gray_o.astype(int) - gray_c.astype(int)) > 12).astype(np.uint8)
    kernel = np.ones((5, 5), np.uint8)
    dil = cv2.dilate(diff, kernel)
    resid = dark_c & dil  # تیرهٔ نزدیک به جایی که پاکسازی دست زده
    n, lab, stats, cent = cv2.connectedComponentsWithStats(resid, 8)
    comps = []
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if a < min_area or a > max_area:
            continue
        if focus and not (focus[0] <= cent[i][1] < focus[1]):
            continue
        comps.append((int(x), int(y), int(w), int(h), int(a),
                      int(cent[i][0]), int(cent[i][1])))
    print(f"[*] {out_path}: {len(comps)} جزءِ تیرهٔ باقیمانده "
          f"(area {min_area}..{max_area}, قلمِ جوهر<{ink_thr})")
    # خوشه‌بندیِ ساده بر اساسِ y برای دیدنِ الگو
    comps.sort(key=lambda t: t[1])
    rows = []
    for cp in comps:
        if rows and abs(cp[1] - rows[-1][0][1]) < 18:
            rows[-1].append(cp)
        else:
            rows.append([cp])
    for r in rows[:25]:
        r.sort(key=lambda t: t[0])
        print(f"    y~{r[0][1]:5d} h={r[0][3]:3d} | "
              f"{len(r)} نقطه | xها: {', '.join(str(t[0]) for t in r[:12])}"
              + (" ..." if len(r) > 12 else ""))
    return o, c, comps


if __name__ == "__main__":
    orig = sys.argv[1] if len(sys.argv) > 1 else "ci_imgs/img6.jpg"
    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/pc_img6/img6.jpg"
    analyze(orig, out)
