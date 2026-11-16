#!/usr/bin/env python3
"""QA دسته‌ای ci_imgs: برای هر تصویر clean-only --debug اجرا میکند،
تعداد ناحیهها و متنِ جاماندهٔ خروجیِ پاک را گزارش میدهد."""
import json
import os
import subprocess
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = "/tmp/qa_batch"
os.makedirs(OUT, exist_ok=True)


def ocr_texts(img_bgr):
    from rapidocr import RapidOCR
    global _OCR
    try:
        _OCR
    except NameError:
        _OCR = RapidOCR()
    res = _OCR(img_bgr)
    out = []
    try:
        for box, t, sc in zip(res.boxes, res.txts, res.scores):
            if t and str(t).strip() and float(sc or 0) >= 0.55:
                y = int(np.mean([p[1] for p in box]))
                out.append((y, str(t).strip(), float(sc)))
    except Exception:
        pass
    return out


def main():
    imgs = sys.argv[1:]
    report = []
    for name in imgs:
        src = os.path.join(HERE, "ci_imgs", name)
        if not os.path.isfile(src):
            print(f"[skip] {name} not found")
            continue
        tag = os.path.splitext(name)[0]
        out_pdf = os.path.join(OUT, tag + ".pdf")
        log_p = os.path.join(OUT, tag + ".log")
        cmd = [sys.executable, os.path.join(HERE, "manga.py"),
               "-i", src, "-o", out_pdf,
               "--font", os.path.join(HERE, "fonts", "Vazirmatn-Bold.ttf"),
               "--clean-only", "--cpu", "--debug",
               "--clean-method", "opencv", "--workers", "1"]
        try:
            with open(log_p, "w") as lf:
                rc = subprocess.run(cmd, cwd=HERE, stdout=lf,
                                    stderr=subprocess.STDOUT,
                                    timeout=540).returncode
        except subprocess.TimeoutExpired:
            rc = 99
        log = ""
        try:
            with open(log_p, encoding="utf-8", errors="replace") as f:
                log = f.read()
        except Exception:
            pass
        import re
        m = re.search(r"متن استخراج شد: (\d+) ناحیه", log)
        n_reg = int(m.group(1)) if m else -1
        m2 = re.search(r"(\d+) ناحیه رد شد \(تبلیغ/SFX", log)
        n_promo = int(m2.group(1)) if m2 else 0
        left = []
        if rc == 0 and os.path.isfile(out_pdf):
            import fitz
            try:
                doc = fitz.open(out_pdf)
                pix = doc[0].get_pixmap(dpi=110)
                arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                    pix.height, pix.width, pix.n)[:, :, :3]
                doc.close()
                # OCR روی خروجیِ پاک: متنِ باقی‌مانده = جامانده
                left = ocr_texts(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
            except Exception as e:
                left = [("?", f"pdf-err {e}", 0)]
        status = "OK" if rc == 0 else f"rc={rc}"
        print(f"[{status}] {name}: regions={n_reg} promo={n_promo} "
              f"leftover={len(left)}", flush=True)
        for y, t, s in left[:6]:
            print(f"    leftover y={y} [{s:.2f}] {t[:60]}")
        report.append({"name": name, "rc": rc, "regions": n_reg,
                       "promo": n_promo, "leftover": len(left),
                       "leftover_texts": [t for _, t, _ in left[:8]]})
    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print("\n--- summary ---")
    for r in report:
        flag = "✓" if (r["rc"] == 0) else "✗"
        print(f" {flag} {r['name']:40s} regions={r['regions']:3d} "
              f"leftover={r['leftover']}")


if __name__ == "__main__":
    main()
