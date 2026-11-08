#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.14.238 — کوانتیزاسیونِ int8 مدلِ rec (PP-OCRv6_medium_rec_onnx).

دو واریانت:
  • dynamic — فقط وزینهایِ MatMul (سریعِ ساخت، بردِ محدود)
  • static  — QOperator + per-channel + QInt8/QUInt8 با کالیبراسیون رویِ
    ۹۹۶ خطِ واقعیِ ضبطشده (scripts/quant_calib/rec_inputs.npy) — بردِ
    اصلی: Convها هم int8 میشوند.
"""

import gc
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "rapidocr_models", "PP-OCRv6_medium_rec_onnx.onnx")
CALIB = os.path.join(HERE, "quant_calib")
OUT_DYN = os.path.join(CALIB, "rec_dyn_int8.onnx")
OUT_STA = os.path.join(CALIB, "rec_static_int8.onnx")
# v1.14.238 — سندباکسِ ۴GB با ۳۷۷ بچ OOM میشود (exit 137) → زیرمجموعهٔ
# گام‌دار (تک‌تکِ تصاویرِ JOBS پوشش داده میشوند — بچها به ترتیبِ عکسند)
STRIDE = int(os.environ.get("QUANT_STRIDE", "4"))


class RecCalibReader:
    """v1.14.238 — استریم از دیسک: هر بچ فقط موقعِ خواندن لود میشود
    (کالیبراسیونِ کاملِ ۲۳۳MB در RAM سندباکسِ ۴GB جا نمیشد)."""

    def __init__(self, files):
        self.files = files
        self.i = 0

    def get_next(self):
        if self.i >= len(self.files):
            return None
        x = np.load(self.files[self.i])
        self.i += 1
        return {"x": x}

    def rewind(self):
        self.i = 0


def main():
    from onnxruntime.quantization import (quantize_dynamic, quantize_static,
                                          QuantType, QuantFormat,
                                          CalibrationMethod)
    from onnxruntime.quantization.shape_inference import quant_pre_process

    batches = np.load(os.path.join(CALIB, "rec_inputs.npy"),
                      allow_pickle=True).tolist()
    print(f"[*] {len(batches)} بچِ کالیبراسیون (کل)")
    if STRIDE > 1:
        batches = batches[::STRIDE]
        gc.collect()
        print(f"[*] زیرمجموعهٔ گامِ {STRIDE}: {len(batches)} بچ")
    # استریم: هر بچ یک فایلِ جدا (نامِگذاریِ پایدار با sha1 محتوا)
    import hashlib
    batch_dir = os.path.join(CALIB, "batches")
    os.makedirs(batch_dir, exist_ok=True)
    files = []
    for i, b in enumerate(batches):
        h = hashlib.sha1(np.ascontiguousarray(b).tobytes()).hexdigest()[:10]
        fp = os.path.join(batch_dir, f"b_{i:04d}_{h}.npy")
        if not os.path.isfile(fp):
            np.save(fp, np.ascontiguousarray(b))
        files.append(fp)
    del batches
    gc.collect()
    print(f"[*] {len(files)} بچ روی دیسک آمادهٔ استریم")

    # پیش‌پردازش (shape inference) برایِ static — استنتاجِ سمبولیک رویِ این
    # مدل کامل نمیشود (بُعدهایِ داینامیک) → همان shape-inferenceِ خودِ
    # onnx کافی است
    pre = os.path.join(CALIB, "rec_pre.onnx")
    if not os.path.isfile(pre):
        quant_pre_process(SRC, pre, skip_optimization=False,
                          skip_onnx_shape=False, skip_symbolic_shape=True)
    print("[*] پیش‌پردازش shape انجام شد")
    gc.collect()

    if not os.path.isfile(OUT_DYN):
        quantize_dynamic(SRC, OUT_DYN, weight_type=QuantType.QInt8)
        print(f"[+] dynamic: {os.path.getsize(OUT_DYN)/1e6:.1f}MB")

    if not os.path.isfile(OUT_STA):
        reader = RecCalibReader(files)
        quantize_static(
            pre, OUT_STA, reader,
            quant_format=QuantFormat.QOperator,
            activation_type=QuantType.QUInt8,
            weight_type=QuantType.QInt8,
            calibrate_method=CalibrationMethod.MinMax,
            per_channel=True,
            reduce_range=False,
            op_types_to_quantize=["Conv", "MatMul", "Gemm"],
            calibration_providers=["CPUExecutionProvider"],
        )
        print(f"[+] static: {os.path.getsize(OUT_STA)/1e6:.1f}MB")
    print("[+] تمام")


if __name__ == "__main__":
    main()
