#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بنچمارک استخراج v1.14.237 — همان پایپ‌لاین واقعیِ manga.py
(RTDetrV2ONNXDetector + _extract_regions_from_bubbles + RapidOCR)
روی عکسِ نمونه، با زمان‌بندیِ فازها و قابلیتِ اوررایدِ پارامترها
تا A/B بین تنظیمات ممکن باشد. خروجیِ JSON در scripts/bench_out/."""

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("MANGA_NO_INSTALL", "1")

import manga  # noqa: E402
from manga import (  # noqa: E402
    MangaTranslator, RTDetrV2ONNXDetector, RapidOCRBackend, TextRegion,
)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bench_out")
os.makedirs(OUT_DIR, exist_ok=True)


class BenchTR(MangaTranslator):
    """MangaTranslator بدونِ __init__ سنگین — فقط صفاتی که مسیرِ
    استخراج لازم دارد."""

    def __init__(self, ocr, det, max_workers, lang="en", debug=False):
        # عمداً super().__init__ صدا زده نمیشود
        self.ocr = ocr
        self.det = det
        self.max_workers = max_workers
        self.lang = lang
        self.debug = debug
        self.min_confidence = 0.25
        self._ocr_crop_cache226 = None
        self._page_bubble_boxes = []
        self._par_note90 = False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default="ci_imgs/img4.jpg")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--det-threads", type=int, default=0,
                    help="نخِ سشنِ دیتکتور (۰ = پیشفرضِ کد)")
    ap.add_argument("--ocr-threads", type=int, default=0,
                    help="MANGA_OCR_THREADS (۰ = پیشفرضِ کد = ۲ روی PC)")
    ap.add_argument("--workers", type=int, default=0,
                    help="MANGA_OCR_WORKERS (۰ = پیشفرضِ کد)")
    ap.add_argument("--ort-threads", type=int, default=0,
                    help="MANGA_ORT_THREADS (۰ = پیشفرضِ کد)")
    ap.add_argument("--det-multi-scale", type=int, default=1,
                    help="پاسِ دومِ multi_scale دیتکتور (۱=روشن)")
    ap.add_argument("--det-limit", type=int, default=0,
                    help="Det.limit_side_len (۰ = پیشفرضِ rapidocr=736)")
    ap.add_argument("--det-limit-type", default="",
                    choices=("", "min", "max"),
                    help="Det.limit_type (خالی = پیشفرضِ rapidocr=min)")
    ap.add_argument("--arena", type=int, default=0,
                    help="enable_cpu_mem_arena (۰ = پیشفرضِ rapidocr)")
    ap.add_argument("--rec-batch", type=int, default=0,
                    help="RecUse.rec_batch_num (۰ = پیشفرضِ rapidocr)")
    ap.add_argument("--runs", type=int, default=2,
                    help="تعدادِ تکرار (اولین = گرم)")
    ap.add_argument("--tag", default="run")
    ap.add_argument("--save-text", action="store_true")
    args = ap.parse_args()

    if args.ocr_threads > 0:
        os.environ["MANGA_OCR_THREADS"] = str(args.ocr_threads)
    if args.workers > 0:
        os.environ["MANGA_OCR_WORKERS"] = str(args.workers)
    if args.ort_threads > 0:
        os.environ["MANGA_ORT_THREADS"] = str(args.ort_threads)
    else:
        os.environ.pop("MANGA_ORT_THREADS", None)

    import cv2
    img = cv2.imread(args.image)
    if img is None:
        print(f"[!] عکس پیدا نشد: {args.image}")
        return 2
    print(f"[*] عکس: {args.image} {img.shape[1]}x{img.shape[0]}")

    # ── فاز ۱: ساختِ دیتکتور (کاشی‌بندی + multi_scale عینِ اپ) ──
    det_kw = dict(
        prefer_gpu=False,
        conf_thresh=0.28,
        iou_thresh=0.45,
        threads=(args.det_threads if args.det_threads > 0
                 else max(1, int(os.cpu_count() or 2) - 0)),
        multi_scale=bool(args.det_multi_scale),
    )
    t0 = time.time()
    det = RTDetrV2ONNXDetector(**det_kw)
    t_det_build = time.time() - t0
    print(f"[*] دیتکتور ساخته شد در {t_det_build:.1f}s | "
          f"threads={det_kw['threads']} ms={det_kw['multi_scale']}")

    # ── فاز ۲: ساختِ موتورِ OCR (RapidOCR — همانِ PC) ──
    t0 = time.time()
    ocr = RapidOCRBackend(lang=args.lang, prefer_gpu=False)
    t_ocr_build = time.time() - t0
    print(f"[*] RapidOCR ساخته شد در {t_ocr_build:.1f}s | "
          f"threads={getattr(ocr, 'ocr_threads', '?')}")

    # اوررایدِ پارامترهای rapidocr بعد از ساخت (A/B)
    _ov_applied = []
    try:
        eng = getattr(ocr, "engine", None)
        cfg = getattr(eng, "cfg", None)
        if cfg is not None:
            if args.det_limit > 0:
                cfg.Det.limit_side_len = int(args.det_limit)
                _ov_applied.append(f"det_limit={args.det_limit}")
            if args.det_limit_type:
                cfg.Det.limit_type = str(args.det_limit_type)
                _ov_applied.append(f"det_limit_type={args.det_limit_type}")
            if args.rec_batch > 0:
                cfg.Rec.rec_batch_num = int(args.rec_batch)
                _ov_applied.append(f"rec_batch={args.rec_batch}")
            if args.arena:
                cfg.EngineConfig.onnxruntime.enable_cpu_mem_arena = True
                _ov_applied.append("arena=1")
            # بعد از اولین فراخوانیِ OCR ماژولها lazy لود میشوند؛
            # مقدارهای det را هم روی ماژولِ لودشده اعمال میکنیم
            def _patch_det_modules():
                td = getattr(eng, "text_det", None)
                if td is not None:
                    if args.det_limit > 0:
                        td.limit_side_len = int(args.det_limit)
                    if args.det_limit_type:
                        td.limit_type = str(args.det_limit_type)
            _orig_run = ocr._engine_run233_nolock

            def _patching_run(image_bgr):
                _patch_det_modules()
                return _orig_run(image_bgr)
            ocr._engine_run233_nolock = _patching_run
        if _ov_applied:
            print(f"[*] اورراید: {', '.join(_ov_applied)}")
    except Exception as e:
        print(f"[!] اوررایدِ کانفیگ نشد: {e}")

    workers = args.workers if args.workers > 0 else max(
        1, int(getattr(ocr, "ocr_threads", 2) or 2))
    tr = BenchTR(ocr, det, max_workers=workers, lang=args.lang)

    # زمان‌بندیِ det جدا از OCR: det.detect را می‌پیچیم
    _det_time = {"s": 0.0, "n": 0}
    _orig_detect = det.detect

    def _timed_detect(image_bgr, fast=False):
        t = time.time()
        r = _orig_detect(image_bgr, fast=fast)
        _det_time["s"] += time.time() - t
        _det_time["n"] += 1
        return r

    det.detect = _timed_detect

    # زمان‌بندیِ OCRِ هر کراپ (فراخوانیِ موتور)
    _eng_time = {"s": 0.0, "n": 0}
    _eng_orig = ocr._engine_run233

    def _timed_eng(im):
        t = time.time()
        r = _eng_orig(im)
        _eng_time["s"] += time.time() - t
        _eng_time["n"] += 1
        return r

    ocr._engine_run233 = _timed_eng

    results = []
    for run in range(args.runs):
        _det_time["s"] = _det_time["n"] = 0
        _eng_time["s"] = _eng_time["n"] = 0
        tr._ocr_crop_cache226 = None
        det.detect = _timed_detect  # پیچِ تازه برای هر ران
        ocr._engine_run233 = _timed_eng
        t0 = time.time()
        regions = tr._extract_regions_from_bubbles(img)
        total = time.time() - t0
        n_lines = sum(len(r.ocr_polys or []) for r in regions)
        texts = []
        for r in regions:
            texts.append(str(r.source_text or ""))
        joined = " ".join(t for t in texts if t.strip())
        res = {
            "run": run,
            "total_s": round(total, 2),
            "det_s": round(_det_time["s"], 2),
            "det_calls": _det_time["n"],
            "ocr_engine_s": round(_eng_time["s"], 2),
            "ocr_engine_calls": _eng_time["n"],
            "regions": len(regions),
            "lines": n_lines,
            "chars": len(joined),
        }
        results.append(res)
        print(f"[*] رانِ {run}: کل={res['total_s']}s | det={res['det_s']}s "
              f"({res['det_calls']} پاس) | OCRِ موتور={res['ocr_engine_s']}s "
              f"({res['ocr_engine_calls']} فراخوانی) | "
              f"ناحیه={res['regions']} خط={res['lines']} حرف={res['chars']}")
        if args.save_text:
            fn = os.path.join(OUT_DIR, f"{args.tag}_text_r{run}.txt")
            with open(fn, "w", encoding="utf-8") as f:
                for r in regions:
                    f.write(str(r.source_text or "") + "\n")
            print(f"[*] متن در {fn}")

    out = {
        "tag": args.tag,
        "image": args.image,
        "shape": f"{img.shape[1]}x{img.shape[0]}",
        "cpu": os.cpu_count(),
        "ort": __import__("onnxruntime").__version__,
        "params": {
            "det_threads": det_kw["threads"],
            "multi_scale": det_kw["multi_scale"],
            "ocr_threads": args.ocr_threads,
            "workers": args.workers,
            "det_limit": args.det_limit,
            "det_limit_type": args.det_limit_type or "default(min)",
            "arena": args.arena,
            "rec_batch": args.rec_batch,
        },
        "build_s": {"det": round(t_det_build, 2),
                    "ocr": round(t_ocr_build, 2)},
        "runs": results,
    }
    fn = os.path.join(OUT_DIR, f"{args.tag}.json")
    with open(fn, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"[*] نتیجه در {fn}")


if __name__ == "__main__":
    main()
