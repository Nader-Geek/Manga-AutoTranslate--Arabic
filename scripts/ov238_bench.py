#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.14.238 — بنچمارک OpenVINO EP در برابر CPU EP (همان بیلدِ ۱.۲۴.۱).

مدلها: rec (ورودیهایِ واقعیِ ۳۷۷بچی) | det (کراپهایِ واقعیِ ۹۶۰/max) |
LaMa-nofft (پچِ ۵۱۲×۵۱۲ + ماسک). خروجی: زمان + تطابقِ متن (rec).
اجرا با venvِ onnxruntime-openvino.
"""

import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CALIB = os.path.join(HERE, "quant_calib")
REC = os.path.join(ROOT, "rapidocr_models", "PP-OCRv6_medium_rec_onnx.onnx")
DET = os.path.join(ROOT, "rapidocr_models", "PP-OCRv6_det_small.onnx")
LAMA = os.path.expanduser("~/.cache/manga_translator_models/"
                          "lama-manga-nofft.onnx")

import onnxruntime as ort  # noqa: E402
import cv2  # noqa: E402


def sess(path, providers, threads=2):
    so = ort.SessionOptions()
    so.log_severity_level = 4
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    if threads:
        so.intra_op_num_threads = threads
        so.inter_op_num_threads = 1
    t0 = time.time()
    s = ort.InferenceSession(path, sess_options=so, providers=providers)
    return s, time.time() - t0


def ctc(x):
    idx = x.argmax(axis=-1)
    out, prev = [], -1
    for i in idx:
        if i != prev and i != 0:
            out.append(int(i))
        prev = int(i)
    return tuple(out)


def bench_rec(providers, batches, ref=None):
    s, build = sess(REC, providers)
    inp, out = s.get_inputs()[0], s.get_outputs()[0].name
    for b in batches[:5]:
        try:
            s.run([out], {inp.name: b})
        except Exception as e:
            return {"error": str(e)[:160]}
    t0 = time.time()
    seqs = []
    for b in batches:
        r = s.run([out], {inp.name: b})[0]
        seqs.extend(ctc(x) for x in r)
    dt = time.time() - t0
    res = {"build_s": round(build, 2), "infer_s": round(dt, 2),
           "ms_per_batch": round(1000 * dt / len(batches), 1)}
    if ref is not None:
        same = sum(1 for a, b in zip(seqs, ref) if a == b)
        res["text_same"] = f"{100*same/len(ref):.2f}% ({same}/{len(ref)})"
    else:
        res["seqs"] = seqs
    return res


def make_det_inputs():
    """کراپهایِ واقعی از img6 + img4 — همان پیش‌پردازشِ rapidocr det."""
    mean = np.array([0.485, 0.456, 0.406], np.float32)
    std = np.array([0.229, 0.224, 0.225], np.float32)
    boxes = [(0, 0, 640, 200), (100, 300, 540, 560), (0, 1000, 690, 1400),
             (50, 2000, 600, 2300), (0, 5000, 690, 5400)]
    out = []
    for img_path in ("ci_imgs/img6.jpg", "ci_imgs/img4.jpg"):
        im = cv2.imread(os.path.join(ROOT, img_path))
        if im is None:
            continue
        H, W = im.shape[:2]
        for (x0, y0, x1, y1) in boxes:
            x0, y0 = max(0, x0), max(0, y0)
            x1, y1 = min(W, x1), min(H, y1)
            if x1 - x0 < 10 or y1 - y0 < 10:
                continue
            c = im[y0:y1, x0:x1]
            h, w = c.shape[:2]
            sc = 960.0 / max(h, w)
            if sc < 1:
                c = cv2.resize(c, (int(w * sc), int(h * sc)))
            # detِ PP-OCR مضربِ ۳۲ لازم دارد (rapidocr هم رند میکند) —
            # بدونِ آن Add.178 با broadcast 13×14 میمیرد
            h, w = c.shape[:2]
            h32, w32 = max(32, (h // 32) * 32), max(32, (w // 32) * 32)
            if (h32, w32) != (h, w):
                c = cv2.resize(c, (w32, h32))
            c = cv2.cvtColor(c, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            c = (c - mean) / std
            c = c.transpose(2, 0, 1)[None]
            out.append(np.ascontiguousarray(c))
    return out


def bench_det(providers, inputs, ref=None):
    s, build = sess(DET, providers)
    inp, out = s.get_inputs()[0], s.get_outputs()[0].name
    for x in inputs[:2]:
        try:
            s.run([out], {inp.name: x})
        except Exception as e:
            return {"error": str(e)[:160]}
    t0 = time.time()
    outs = []
    for x in inputs:
        r = s.run([out], {inp.name: x})[0]
        outs.append(float(np.abs(r).sum()))
    dt = time.time() - t0
    res = {"build_s": round(build, 2), "infer_s": round(dt, 2),
           "ms_per_input": round(1000 * dt / len(inputs), 1)}
    if ref is not None:
        dev = max(abs(a - b) / max(1e-6, abs(b)) for a, b in zip(outs, ref))
        res["max_rel_dev"] = f"{dev:.2e}"
    else:
        res["sums"] = outs
    return res


def bench_lama(providers):
    rng = np.random.RandomState(42)
    img = rng.rand(1, 3, 512, 512).astype(np.float32)
    mask = np.zeros((1, 1, 512, 512), np.float32)
    mask[:, :, 100:400, 100:400] = 1.0
    s, build = sess(LAMA, providers)
    names = {i.name for i in s.get_inputs()}
    feed = {"image": img, "mask": mask} if "image" in names else {}
    if not feed:
        in0 = s.get_inputs()[0].name
        in1 = s.get_inputs()[1].name
        feed = {in0: img, in1: mask}
    out = s.get_outputs()[0].name
    try:
        s.run([out], feed)
    except Exception as e:
        return {"error": str(e)[:160]}
    t0 = time.time()
    n = 3
    for _ in range(n):
        r = s.run([out], feed)[0]
    dt = (time.time() - t0) / n
    return {"build_s": round(build, 2),
            "s_per_512_patch": round(dt, 2), "out_abs_sum": float(np.abs(r).sum())}


def main():
    batches = np.load(os.path.join(CALIB, "rec_inputs.npy"),
                      allow_pickle=True).tolist()
    print(f"[*] rec: {len(batches)} بچ | "
          f"{sum(b.shape[0] for b in batches)} خط")
    det_inputs = make_det_inputs()
    print(f"[*] det: {len(det_inputs)} کراپِ واقعی")

    # مرجع = CPU EP همین بیلد (۱.۲۴.۱)
    print("\n=== CPUExecutionProvider (ORT 1.24.1 — همان بیلد) ===")
    r = bench_rec(["CPUExecutionProvider"], batches)
    ref_seqs = r.pop("seqs", None)
    print("rec :", r)
    d = bench_det(["CPUExecutionProvider"], det_inputs)
    ref_sums = d.pop("sums", None)
    print("det :", d)
    print("lama:", bench_lama(["CPUExecutionProvider"]))

    print("\n=== OpenVINOExecutionProvider (ORT 1.24.1) ===")
    r = bench_rec(["OpenVINOExecutionProvider", "CPUExecutionProvider"],
                  batches, ref=ref_seqs)
    print("rec :", r)
    d = bench_det(["OpenVINOExecutionProvider", "CPUExecutionProvider"],
                  det_inputs, ref=ref_sums)
    print("det :", d)
    print("lama:", bench_lama(["OpenVINOExecutionProvider",
                               "CPUExecutionProvider"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
