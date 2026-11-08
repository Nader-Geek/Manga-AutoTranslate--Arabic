#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""دیباگ v2 — پیدا کردنِ حبابهای هدف با OCRِ اولیه، بعد مقایسهٔ دو تنظیم."""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import manga  # noqa: E402
from manga import RTDetrV2ONNXDetector, RapidOCRBackend  # noqa: E402
import cv2  # noqa: E402


def run(ocr, crop):
    try:
        return ocr._engine_run233(crop)
    except Exception as e:
        print("    err:", str(e)[:100])
        return None


def dump(out, label):
    print(f"  ── {label}")
    txts = getattr(out, "txts", None)
    boxes = getattr(out, "boxes", None)
    if txts is None:
        print("    (متن خالی)")
        return
    for i, t in enumerate(txts):
        b = boxes[i] if boxes is not None and i < len(boxes) else None
        if b is None:
            print(f"    [{i}] {str(t)[:44]!r}")
            continue
        ys = [p[1] for p in b]
        xs = [p[0] for p in b]
        print(f"    [{i}] y_top={min(ys):7.1f} y_bot={max(ys):7.1f} "
              f"x0={min(xs):7.1f} h={max(ys)-min(ys):5.1f} | {str(t)[:44]!r}")


def main():
    img = cv2.imread("ci_imgs/img7.jpg")
    det = RTDetrV2ONNXDetector(prefer_gpu=False, conf_thresh=0.28,
                               iou_thresh=0.45, threads=2, multi_scale=True)
    boxes = det.detect(img)
    boxes = manga.MangaTranslator._drop_contained_boxes(boxes, 0.72)
    h, w = img.shape[:2]

    ocr_old = RapidOCRBackend(lang="en", prefer_gpu=False)
    ocr_old.engine.cfg.Det.limit_side_len = 736
    ocr_old.engine.cfg.Det.limit_type = "min"
    ocr_new = RapidOCRBackend(lang="en", prefer_gpu=False)

    for k, b in enumerate(boxes):
        x1, y1, x2, y2 = b["rect"]
        crop = img[max(0, y1 - 8):min(h, y2 + 8), max(0, x1 - 8):min(w, x2 + 8)]
        m = max(crop.shape[0], crop.shape[1])
        sc = 2.4 if m < 200 else 1.8 if m < 360 else 1.35 if m < 600 else 1.0
        cc = cv2.resize(crop, None, fx=sc, fy=sc,
                        interpolation=cv2.INTER_CUBIC) if sc > 1.01 else crop
        out_o = run(ocr_old, cc)
        t_o = " ".join(getattr(out_o, "txts", None) or [])
        if "SECURITY" not in t_o and "SINCE" not in t_o:
            continue
        print(f"\n═══ حبابِ هدف #{k} rect={b['rect']} sc={sc} "
              f"کراپ={cc.shape[1]}x{cc.shape[0]} ═══")
        dump(out_o, "OLD 736/min")
        dump(run(ocr_new, cc), "NEW 960/max")


if __name__ == "__main__":
    main()
