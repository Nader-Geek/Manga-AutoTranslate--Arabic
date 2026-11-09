#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تشخیصِ ریشهٔ نقطه‌های سیاه: بیرونِ ماسکِ کامپوز مانده‌اند یا
داخلِ ماسک ولی donor آنها را پاک نکرده؟"""

import cv2
import numpy as np

ORIG = "ci_imgs/img6.jpg"
OUT = "/tmp/pc_img6d/img6.jpg"
DONOR = "/tmp/donor.png"
CMP = "/tmp/cmp.png"

# نواحی از لاگ اجرا (x, y, w, h)
REGIONS = [
    (1449, 13, 293, 495), (1113, 75, 284, 563), (890, 144, 219, 440),
    (142, 218, 145, 301), (0, 406, 167, 247), (35, 958, 358, 667),
    (1341, 1718, 315, 377), (445, 1951, 224, 163), (335, 2102, 193, 301),
]

o = cv2.imread(ORIG)
c = cv2.imread(OUT)
d = cv2.imread(DONOR)
m = cv2.imread(CMP, 0)
# اورجینال ممکن است کوچکتر باشد (نرمال‌سازیِ عرضِ هوشمند) → هم‌مقیاس
if o.shape[:2] != c.shape[:2]:
    o = cv2.resize(o, (c.shape[1], c.shape[0]),
                   interpolation=cv2.INTER_AREA)
print("shapes:", o.shape, c.shape, d.shape, m.shape)

go = cv2.cvtColor(o, cv2.COLOR_BGR2GRAY).astype(int)
gc = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY).astype(int)
gd = cv2.cvtColor(d, cv2.COLOR_BGR2GRAY).astype(int)

PAD = 14
n_out = n_in = 0
out_px = 0
in_px = 0
samples = []
for (rx, ry, rw, rh) in REGIONS:
    x0, y0 = max(0, rx - PAD), max(0, ry - PAD)
    x1, y1 = min(o.shape[1], rx + rw + PAD), min(o.shape[0], ry + rh + PAD)
    sub_o = go[y0:y1, x0:x1]
    sub_c = gc[y0:y1, x0:x1]
    sub_m = (m[y0:y1, x0:x1] > 0)
    # بقایای جوهر: در خروجی تیره و در اورجینال هم تیره بوده (جوهرِ اصل)
    resid = (sub_c < 110) & (sub_o < 110)
    n_comp, lab, stats, cent = cv2.connectedComponentsWithStats(
        resid.astype(np.uint8), 8)
    for i in range(1, n_comp):
        a = int(stats[i, cv2.CC_STAT_AREA])
        if a < 3 or a > 2000:
            continue
        comp = (lab == i)
        in_mask = int((comp & sub_m).sum())
        if in_mask > a * 0.5:
            n_in += 1
            in_px += a
            if len(samples) < 400:
                samples.append(("IN", int(cent[i][0]) + x0,
                                int(cent[i][1]) + y0, a))
        else:
            n_out += 1
            out_px += a
            if len(samples) < 400:
                samples.append(("OUT", int(cent[i][0]) + x0,
                                int(cent[i][1]) + y0, a))

print(f"\n[*] اجزای بقایا: داخلِ ماسک (donor پاک نکرده) = {n_in} "
      f"({in_px}px) | بیرونِ ماسک = {n_out} ({out_px}px)")
print("[*] نمونه‌ها (نوع، x، y، مساحت):")
by_type = {}
for s in samples:
    by_type.setdefault(s[0], []).append(s)
for t, lst in by_type.items():
    lst.sort(key=lambda s: -s[3])
    print(f"  --- {t}: {len(lst)}")
    for s in lst[:12]:
        print(f"      x={s[1]:5d} y={s[2]:5d} area={s[3]}")
