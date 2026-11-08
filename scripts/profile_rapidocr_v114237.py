#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""پروفایلِ داخلِ RapidOCR: سهمِ det / cls / rec / پیش‌پردازش در هر کراپ.
یک کراپِ واقعی از img4 برمیدارد و موتور را با isurrogate تایم‌ها می‌پیچد."""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import manga  # noqa: E402
from manga import RTDetrV2ONNXDetector, RapidOCRBackend  # noqa: E402

import cv2  # noqa: E402


def main():
    img = cv2.imread("ci_imgs/img4.jpg")
    det = RTDetrV2ONNXDetector(prefer_gpu=False, conf_thresh=0.28,
                               iou_thresh=0.45, threads=2, multi_scale=True)
    boxes = det.detect(img)
    boxes = manga.MangaTranslator._drop_contained_boxes(boxes, 0.72)
    print(f"[*] {len(boxes)} باکس")

    ocr = RapidOCRBackend(lang="en", prefer_gpu=False)
    eng = getattr(ocr, "engine", None)
    print("[*] engine:", type(eng).__name__)
    # اجزای داخلی
    for attr in ("det", "cls", "rec"):
        sub = getattr(eng, attr, None)
        print(f"    .{attr} =", type(sub).__name__ if sub else None)
    cfg = getattr(eng, "cfg", None)
    if cfg is not None:
        try:
            print("[*] det_use:", cfg.det_use)
        except Exception:
            pass
        try:
            print("[*] rec_use:", cfg.rec_use)
        except Exception:
            pass

    # کراپهای واقعی (همان منطقِ _ocr_crop_run: پدِ ۸)
    h, w = img.shape[:2]
    crops = []
    for b in boxes[:12]:
        x1, y1, x2, y2 = b["rect"]
        x1, y1 = max(0, x1 - 8), max(0, y1 - 8)
        x2, y2 = min(w, x2 + 8), min(h, y2 + 8)
        if x2 - x1 < 8 or y2 - y1 < 8:
            continue
        crops.append(img[y1:y2, x1:x2])
    print(f"[*] {len(crops)} کراپ برای پروفایل")

    # پیچیدنِ زمان‌سنجی دورِ ساب-ماژولها
    times = {"det": 0.0, "cls": 0.0, "rec": 0.0}
    counts = {"det": 0, "cls": 0, "rec": 0}

    def wrap(name, obj):
        if obj is None:
            return
        orig = obj.__call__

        def timed(*a, **k):
            t = time.time()
            try:
                return orig(*a, **k)
            finally:
                times[name] += time.time() - t
                counts[name] += 1

        obj.__call__ = timed
        try:
            import types
            obj.__call__ = types.MethodType(timed, obj)
        except Exception:
            pass

    for name in ("det", "cls", "rec"):
        wrap(name, getattr(eng, name, None))

    t_all = time.time()
    for i, c in enumerate(crops):
        # همان مقیاسِ نردبان: m<360 → 1.8 و غیره
        m = max(c.shape[0], c.shape[1])
        sc = 2.4 if m < 200 else 1.8 if m < 360 else 1.35 if m < 600 else 1.0
        cc = cv2.resize(c, None, fx=sc, fy=sc,
                        interpolation=cv2.INTER_CUBIC) if sc > 1.01 else c
        t0 = time.time()
        try:
            ocr._engine_run233(cc)
        except Exception as e:
            print("   err:", str(e)[:80])
        print(f"  کراپِ {i}: {c.shape[1]}x{c.shape[0]} sc={sc} → "
              f"{(time.time()-t0):.2f}s")
    wall = time.time() - t_all
    print(f"\n[*] دیوارِ کل: {wall:.1f}s | det={times['det']:.1f}s "
          f"({counts['det']}) | cls={times['cls']:.1f}s | "
          f"rec={times['rec']:.1f}s ({counts['rec']})")
    tot = times['det'] + times['rec'] or 1
    print(f"[*] سهم: det={times['det']/tot*100:.0f}% rec={times['rec']/tot*100:.0f}%")


if __name__ == "__main__":
    main()
