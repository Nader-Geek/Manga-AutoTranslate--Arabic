#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.14.238 — میکرو-بنچمارک rec: FP32 در برابرِ int8 (dynamic/static).

ورودیها = همان بچهایِ واقعیِ ضبطشده از پایپ‌لاین (quant_calib/
rec_inputs.npy — ۳۷۷ بچ، ~۱۰۰۰ خطِ متن از ۱۰ عکسِ تست).
خروجی: زمانِ کل/میانگینِ هر بچ + درصدِ خطوطی که argmax-دکدِ int8
دقیقاً همان FP32 را میدهد (پروکسیِ «همان متن»).
"""

import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CALIB = os.path.join(HERE, "quant_calib")
FP32 = os.path.join(ROOT, "rapidocr_models",
                    "PP-OCRv6_medium_rec_onnx.onnx")
VARIANTS = [
    ("fp32", FP32),
    ("dyn_int8", os.path.join(CALIB, "rec_dyn_int8.onnx")),
    ("static_int8", os.path.join(CALIB, "rec_static_int8.onnx")),
]

import onnxruntime as ort  # noqa: E402


def make_session(path, threads=2):
    so = ort.SessionOptions()
    so.log_severity_level = 3
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    so.intra_op_num_threads = threads
    so.inter_op_num_threads = 1
    so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    so.enable_cpu_mem_arena = False  # سندباکسِ ۴GB — آرنا را نمیبندیم
    return ort.InferenceSession(path, sess_options=so,
                                providers=["CPUExecutionProvider"])


def ctc_argmax_str(logits):
    """دکدِ حریصانهٔ CTC رویِ خروجیِ (T, C): ایندکسهایِ argmax بعد ازِ
    حذفِ تکرارها و blank(0). برایِ مقایسهٔ تطابقِ دو مدل کافی است."""
    idx = np.argmax(logits, axis=-1)
    out = []
    prev = -1
    for i in idx:
        if i != prev and i != 0:
            out.append(int(i))
        prev = int(i)
    return tuple(out)


def main():
    batches = np.load(os.path.join(CALIB, "rec_inputs.npy"),
                      allow_pickle=True).tolist()
    n_lines = sum(b.shape[0] for b in batches)
    print(f"[*] {len(batches)} بچ | {n_lines} خطِ متن")
    ref_seqs = None
    for name, path in VARIANTS:
        if not os.path.isfile(path):
            print(f"[--] {name}: فایل نیست → رد")
            continue
        t0 = time.time()
        sess = make_session(path)
        build_s = time.time() - t0
        inp = sess.get_inputs()[0]
        out_name = sess.get_outputs()[0].name
        # گرم‌کردن
        for b in batches[:5]:
            try:
                sess.run([out_name], {inp.name: b})
            except Exception:
                pass
        t0 = time.time()
        n_dec = 0
        agree_n = 0
        seqs = [] if name == "fp32" else None
        for b in batches:
            r = sess.run([out_name], {inp.name: b})[0]
            for x in r:
                s = ctc_argmax_str(x)
                n_dec += 1
                if seqs is not None:
                    seqs.append(s)
                elif s == ref_seqs[n_dec - 1]:
                    agree_n += 1
            del r
        dt = time.time() - t0
        agree = "-"
        if name == "fp32":
            ref_seqs = seqs
            del seqs
        else:
            agree = f"{100.0*agree_n/max(1,n_dec):.2f}% ({agree_n}/{n_dec})"
        print(f"[+] {name:11s} | build={build_s:5.1f}s | "
              f"infer={dt:6.2f}s | {1000*dt/len(batches):6.1f}ms/بچ | "
              f"متنِ یکسان: {agree}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
