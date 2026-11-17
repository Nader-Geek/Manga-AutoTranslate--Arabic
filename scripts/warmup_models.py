#!/usr/bin/env python3
"""Pre-download engine models (detector + rapidocr) for offline QA runs."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import manga  # noqa: E402  (loader exec; downloads deps on import)

import numpy as np  # noqa: E402
import cv2  # noqa: E402


def main():
    img = np.full((640, 480, 3), 255, np.uint8)
    cv2.ellipse(img, (240, 200), (120, 70), 0, 0, 360, (0, 0, 0), 2)
    cv2.putText(img, "HELLO", (185, 210), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (0, 0, 0), 2)

    # 1) detector model download + session warmup
    det_cls = getattr(manga, "RTDetrV2ONNXDetector", None)
    print("[warmup] detector class:", det_cls, flush=True)
    if det_cls is not None:
        det = det_cls(prefer_gpu=False)
        try:
            out = det(img)
            print("[warmup] detector OK:", str(out)[:200], flush=True)
        except Exception as e:
            print("[warmup] detector call failed:", repr(e)[:300], flush=True)

    # 2) rapidocr warmup
    try:
        from rapidocr import RapidOCR
        eng = RapidOCR()
        r = eng(img)
        print("[warmup] rapidocr OK:", str(r)[:160], flush=True)
    except Exception as e:
        print("[warmup] rapidocr failed:", repr(e)[:300], flush=True)

    print("[warmup] DONE", flush=True)


if __name__ == "__main__":
    main()
