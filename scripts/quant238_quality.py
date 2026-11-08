#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.14.238 — تحلیلِ کیفیتِ static_int8 در برابرِ fp32 (دکدِ واقعی).

برایِ هر خطِ ۹۹۶تایی: متنِ دکدشده با charsetِ رسمی (ppocrv6_chars.txt +
space + blank) برایِ هر دو مدل؛ سپس دسته‌بندیِ تفاوت:
  identical | minor (شباهتِ نویسه‌ای ≥0.9) | severe (<0.9 یا خالی)
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CALIB = os.path.join(HERE, "quant_calib")
FP32 = os.path.join(ROOT, "rapidocr_models",
                    "PP-OCRv6_medium_rec_onnx.onnx")
STA = os.path.join(CALIB, "rec_static_int8.onnx")
CHARS = os.path.join(ROOT, "rapidocr_models", "ppocrv6_chars.txt")

import onnxruntime as ort  # noqa: E402


def load_charset():
    with open(CHARS, "rb") as f:
        chars = [ln.decode("utf-8").strip("\n").strip("\r\n")
                 for ln in f.readlines()]
    chars.append(" ")
    chars.insert(0, "blank")
    return chars


def make_session(path, threads=2):
    so = ort.SessionOptions()
    so.log_severity_level = 3
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    so.intra_op_num_threads = threads
    so.inter_op_num_threads = 1
    so.enable_cpu_mem_arena = False
    return ort.InferenceSession(path, sess_options=so,
                                providers=["CPUExecutionProvider"])


def decode_batch(logits, charset):
    """دکدِ CTC حریصانه — عینِ rapidocr: dedupe + حذفِ blank(0)."""
    out = []
    for x in logits:
        idx = x.argmax(axis=-1)
        sel = np.ones(len(idx), dtype=bool)
        sel[1:] = idx[1:] != idx[:-1]
        sel &= idx != 0
        out.append("".join(charset[i] for i in idx[sel]))
    return out


def sim(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    # فاصلهٔ لوانشتاینِ سبک (طولِ مشترکِ ساده)
    la, lb = len(a), len(b)
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        for j in range(1, lb + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1,
                         prev[j - 1] + (a[i - 1] != b[j - 1]))
        prev = cur
    return 1.0 - prev[lb] / max(la, lb)


def main():
    charset = load_charset()
    print(f"[*] charset: {len(charset)} نویسه")
    batches = np.load(os.path.join(CALIB, "rec_inputs.npy"),
                      allow_pickle=True).tolist()
    s32 = make_session(FP32)
    s8 = make_session(STA)
    i32 = s32.get_inputs()[0]
    i8 = s8.get_inputs()[0]
    o32 = s32.get_outputs()[0].name
    o8 = s8.get_outputs()[0].name
    n_id = n_min = n_sev = 0
    n_empty8 = n_empty32 = 0
    sev_samples = []
    for b in batches:
        t32 = decode_batch(s32.run([o32], {i32.name: b})[0], charset)
        t8 = decode_batch(s8.run([o8], {i8.name: b})[0], charset)
        for a, c in zip(t32, t8):
            if not a:
                n_empty32 += 1
            if not c:
                n_empty8 += 1
            if a == c:
                n_id += 1
            else:
                s_ = sim(a, c)
                if s_ >= 0.9:
                    n_min += 1
                else:
                    n_sev += 1
                    if len(sev_samples) < 12:
                        sev_samples.append((a, c, round(s_, 2)))
    tot = n_id + n_min + n_sev
    print(f"[*] کلِ خطوط: {tot}")
    print(f"[+] یکسان:   {n_id} ({100*n_id/tot:.1f}%)")
    print(f"[+] جزئی(≥0.9 شباهت): {n_min} ({100*n_min/tot:.1f}%)")
    print(f"[+] شدید(<0.9): {n_sev} ({100*n_sev/tot:.1f}%)")
    print(f"[*] متنِ خالی: fp32={n_empty32} | int8={n_empty8}")
    for a, c, s_ in sev_samples:
        print(f"    [{s_}] fp32={a[:40]!r} | int8={c[:40]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
