#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.14.238 — ضبطِ ورودیهایِ واقعیِ rec از دلِ پایپ‌لاین (برایِ
کالیبراسیونِ کوانتیزاسیونِ int8 + میکرو-بنچمارک).

برایِ هر عکسِ تست، همان پایپ‌لاینِ واقعی (RapidOCRBackend +
_extract_regions_from_bubbles) اجرا میشود و tensörهایِ پیش‌پردازششدهٔ
rec (batch,3,48,W) ضبط و در scripts/quant_calib/ ذخیره میشوند."""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import manga  # noqa: E402
from manga import RTDetrV2ONNXDetector, RapidOCRBackend, MangaTranslator  # noqa: E402

import cv2  # noqa: E402

CALIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "quant_calib")
os.makedirs(CALIB_DIR, exist_ok=True)

# (عکس، زبان) — تنوعِ لاتین + CJK + کره‌ای
JOBS = [
    ("ci_imgs/img4.jpg", "en"),
    ("ci_imgs/img6.jpg", "en"),
    ("ci_imgs/img7.jpg", "en"),
    ("ci_imgs/up0822_en.jpg", "en"),
    ("ci_imgs/IMG_20260929_025420_921.jpg", "en"),
    ("ci_imgs/up0929_zh.jpg", "zh"),
    ("ci_imgs/lang_zh.jpg", "zh"),
    ("ci_imgs/lang_ja_color.jpg", "ja"),
    ("ci_imgs/232264684-5a7bcf8e-707b-4925-86b0-4212382f1680.png", "ja"),
    ("ci_imgs/lang_ko.jpg", "ko"),
]


class BenchTR(MangaTranslator):
    def __init__(self, ocr, det, mw, lang="en"):
        self.ocr = ocr
        self.det = det
        self.max_workers = mw
        self.lang = lang
        self.debug = False
        self.min_confidence = 0.25
        self._ocr_crop_cache226 = None
        self._page_bubble_boxes = []
        self._par_note90 = False


def main():
    all_batches = []
    for img_path, lang in JOBS:
        if not os.path.isfile(img_path):
            print(f"[!] نیست: {img_path}")
            continue
        img = cv2.imread(img_path)
        if img is None:
            continue
        det = RTDetrV2ONNXDetector(prefer_gpu=False, conf_thresh=0.28,
                                   iou_thresh=0.45, threads=2,
                                   multi_scale=True)
        ocr = RapidOCRBackend(lang=lang, prefer_gpu=False)
        eng = ocr.engine

        captured = []

        # هوک رویِ لازیلود: بعد از ساختِ text_rec، سشنش بسته میشود تا
        # tensörهایِ پیش‌پردازششده ضبط شوند (پاسِ سفیدِ قدیمی det را خالی
        # میکرد و rec کلاً لود نمیشد).
        _orig_load = eng._load_rec_model

        def _patched_load():
            rec = _orig_load()
            if not getattr(rec, "_cap238", False):
                orig = rec.session

                class Cap:
                    def __call__(self, x):
                        captured.append(np.asarray(x, dtype=np.float32).copy())
                        return orig(x)

                    def __getattr__(self, a):
                        return getattr(orig, a)

                rec.session = Cap()
                rec._cap238 = True
            return rec

        eng._load_rec_model = _patched_load

        tr = BenchTR(ocr, det, 2, lang=lang)
        regs = tr._extract_regions_from_bubbles(img)
        n_lines = sum(len(r.ocr_polys or []) for r in regs)
        print(f"[*] {os.path.basename(img_path)} [{lang}]: {len(regs)} ناحیه، "
              f"{n_lines} خط، {len(captured)} بچِ rec ضبط شد")
        all_batches.extend(captured)

    if not all_batches:
        print("[!] هیچی ضبط نشد!")
        return 1
    np.save(os.path.join(CALIB_DIR, "rec_inputs.npy"),
            np.asarray(all_batches, dtype=object), allow_pickle=True)
    shapes = [b.shape for b in all_batches]
    n_items = sum(s[0] for s in shapes)
    print(f"\n[+] کل: {len(all_batches)} بچ | {n_items} خطِ متن | "
          f"ابعادِ نمونه: {shapes[:3]}")
    print("[+] ذخیره در quant_calib/rec_inputs.npy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
