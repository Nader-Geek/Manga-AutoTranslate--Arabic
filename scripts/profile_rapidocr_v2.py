#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""پروفایل v2 — سهمِ det/rec داخلِ RapidOCR با تنظیمِ det (پس از لودِ
lazy)، روی کراپهای واقعیِ img4. برای پیدا کردنِ گلوگاهِ بعدی."""

import argparse
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import manga  # noqa: E402
from manga import RTDetrV2ONNXDetector, RapidOCRBackend  # noqa: E402

import cv2  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default="ci_imgs/img4.jpg")
    ap.add_argument("--det-limit", type=int, default=960)
    ap.add_argument("--det-limit-type", default="max")
    ap.add_argument("--rec-batch", type=int, default=0)
    ap.add_argument("--n-crops", type=int, default=24)
    args = ap.parse_args()

    img = cv2.imread(args.image)
    det = RTDetrV2ONNXDetector(prefer_gpu=False, conf_thresh=0.28,
                               iou_thresh=0.45, threads=2, multi_scale=True)
    boxes = det.detect(img)
    boxes = manga.MangaTranslator._drop_contained_boxes(boxes, 0.72)

    ocr = RapidOCRBackend(lang="en", prefer_gpu=False)
    eng = ocr.engine
    eng.cfg.Det.limit_side_len = args.det_limit
    eng.cfg.Det.limit_type = args.det_limit_type
    if args.rec_batch > 0:
        eng.cfg.Rec.rec_batch_num = args.rec_batch

    h, w = img.shape[:2]
    crops = []
    for b in boxes[:args.n_crops]:
        x1, y1, x2, y2 = b["rect"]
        x1, y1 = max(0, x1 - 8), max(0, y1 - 8)
        x2, y2 = min(w, x2 + 8), min(h, y2 + 8)
        if x2 - x1 < 8 or y2 - y1 < 8:
            continue
        crops.append(img[y1:y2, x1:x2])
    print(f"[*] {len(crops)} کراپ | det={args.det_limit}/{args.det_limit_type}"
          f"{' rec_batch=' + str(args.rec_batch) if args.rec_batch else ''}")

    # اول یک پاسِ کوچک تا ماژولهایِ lazy لود شوند
    ocr._engine_run233(np.full((64, 320, 3), 255, dtype=np.uint8))
    td = getattr(eng, "text_det", None)
    if td is not None:
        td.limit_side_len = args.det_limit
        td.limit_type = args.det_limit_type

    times = {"det": 0.0, "rec": 0.0}
    counts = {"det": 0, "rec": 0}
    _dac = eng.detect_and_crop
    _rec = eng.recognize_txt

    def t_dac(img2, rec):
        t = time.time()
        try:
            return _dac(img2, rec)
        finally:
            times["det"] += time.time() - t
            counts["det"] += 1

    def t_rec(img2):
        t = time.time()
        try:
            return _rec(img2)
        finally:
            times["rec"] += time.time() - t
            counts["rec"] += 1

    eng.detect_and_crop = t_dac
    eng.recognize_txt = t_rec

    t_all = time.time()
    tot_lines = 0
    for i, c in enumerate(crops):
        m = max(c.shape[0], c.shape[1])
        sc = 2.4 if m < 200 else 1.8 if m < 360 else 1.35 if m < 600 else 1.0
        cc = cv2.resize(c, None, fx=sc, fy=sc,
                        interpolation=cv2.INTER_CUBIC) if sc > 1.01 else c
        t0 = time.time()
        out = ocr._engine_run233(cc)
        nl = len(getattr(out, "txts", None) or [])
        tot_lines += nl
        print(f"  کراپِ {i}: {c.shape[1]}x{c.shape[0]} sc={sc} "
              f"→ {(time.time()-t0):.2f}s ({nl} خط)")
    wall = time.time() - t_all
    print(f"\n[*] دیوار: {wall:.1f}s | det={times['det']:.1f}s "
          f"({counts['det']} پاس) | rec={times['rec']:.1f}s "
          f"({counts['rec']} پاس) | خط={tot_lines}")
    tot = times['det'] + times['rec'] or 1
    print(f"[*] سهم: det={times['det']/tot*100:.0f}% rec={times['rec']/tot*100:.0f}%")


if __name__ == "__main__":
    main()
