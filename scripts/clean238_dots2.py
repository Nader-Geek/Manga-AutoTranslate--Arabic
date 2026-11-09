#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تحلیلِ بقایای پاکسازی برای هر عکس: نواحی از دیتکتور، مقایسهٔ
اورجینال/خروجی/دونور/ماسک؛ دسته‌بندیِ IN (donor پاک نکرده) / OUT
(بیرونِ ماسک)؛ ذخیرهٔ کراپِ بدترین‌ها."""

import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import manga  # noqa: E402
from manga import RTDetrV2ONNXDetector  # noqa: E402


def main(orig_path, out_path, donor_path, cmp_path, n_crop=8):
    o = cv2.imread(orig_path)
    c = cv2.imread(out_path)
    if o.shape[:2] != c.shape[:2]:
        o = cv2.resize(o, (c.shape[1], c.shape[0]),
                       interpolation=cv2.INTER_AREA)
    d = cv2.imread(donor_path)
    m = cv2.imread(cmp_path, 0)
    H, W = c.shape[:2]
    det = RTDetrV2ONNXDetector(prefer_gpu=False, conf_thresh=0.28,
                               iou_thresh=0.45, threads=2, multi_scale=True)
    boxes = det.detect(o)
    rects = []
    for b in (boxes or []):
        try:
            x0, y0, w0, h0 = [int(v) for v in b["rect"][:4]]
            x1, y1 = x0 + w0, y0 + h0
        except Exception:
            try:
                x0, y0, x1, y1 = [int(v) for v in b[:4]]
            except Exception:
                continue
        if x1 - x0 > 20 and y1 - y0 > 16:
            rects.append((x0, y0, x1 - x0, y1 - y0))
    print(f"[*] {len(rects)} ناحیه از دیتکتور")

    go = cv2.cvtColor(o, cv2.COLOR_BGR2GRAY).astype(int)
    gc = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY).astype(int)
    gd = cv2.cvtColor(d, cv2.COLOR_BGR2GRAY).astype(int)
    PAD = 14
    n_in = n_out = 0
    in_px = out_px = 0
    comps = []
    for (rx, ry, rw, rh) in rects:
        x0, y0 = max(0, rx - PAD), max(0, ry - PAD)
        x1, y1 = min(W, rx + rw + PAD), min(H, ry + rh + PAD)
        sub_o = go[y0:y1, x0:x1]
        sub_c = gc[y0:y1, x0:x1]
        sub_d = gd[y0:y1, x0:x1]
        sub_m = (m[y0:y1, x0:x1] > 0)
        resid = (sub_c < 110) & (sub_o < 110) & (sub_d >= 140)
        n_comp, lab, stats, cent = cv2.connectedComponentsWithStats(
            resid.astype(np.uint8), 8)
        for i in range(1, n_comp):
            a = int(stats[i, cv2.CC_STAT_AREA])
            if a < 3 or a > 4000:
                continue
            comp = (lab == i)
            in_mask = int((comp & sub_m).sum())
            t = "IN" if in_mask > a * 0.5 else "OUT"
            if t == "IN":
                n_in += 1
                in_px += a
            else:
                n_out += 1
                out_px += a
            comps.append((t, int(cent[i][0]) + x0, int(cent[i][1]) + y0, a))
    print(f"[*] بقایا: IN(donor پاک نکرده)={n_in} ({in_px}px) | "
          f"OUT(بیرونِ ماسک)={n_out} ({out_px}px)")
    comps.sort(key=lambda t: -t[3])
    print("[*] بزرگ‌ترین‌ها:")
    for s in comps[:12]:
        print(f"    {s[0]} x={s[1]:5d} y={s[2]:5d} area={s[3]}")
    # کولاژ کراپ‌ها
    R = 55
    S = 2 * R
    tiles = []
    for (t, x, y, a) in comps[:n_crop]:
        x0 = min(max(0, x - R), W - S)
        y0 = min(max(0, y - R), H - S)
        row = [cv2.resize(tt[y0:y0 + S, x0:x0 + S], (S, S))
               for tt in (o, d, c)]
        mm = np.dstack([m[y0:y0 + S, x0:x0 + S]] * 3)
        row.append(mm)
        tiles.append(np.hstack(row))
    if tiles:
        col = np.vstack(tiles)
        out_png = "/tmp/resid_collage.png"
        cv2.imwrite(out_png, col)
        print(f"[*] کولاژ {len(tiles)}×۴ → {out_png}")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:5]))
