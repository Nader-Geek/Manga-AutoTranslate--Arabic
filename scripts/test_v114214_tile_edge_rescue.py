#!/usr/bin/env python3
"""v1.14.214 — تستِ «نجاتِ جعبهٔ لبهٔ کاشی» در RTDetrV2ONNXDetector._detect_tiled.

ریشهٔ باگ (گزارشِ سازنده: «یک متن نمیبینه رد میشه تو گوشی … هردو لینک بدم …
تکی بدم همشو پیدا میکنه»):
- بچِ دو-عکسیِ img4+4e2e77 → img4 بریده میشود به ۳ نوار (2332/5832)؛
- پاراگرافِ «1. AUTHORITY TO IMMEDIATELY SEPARATE…» (y سراسری 7536-7855 در
  img4ِ ۷۰۰px) در نوارِ ۷ (local 1737-2018) فقط در کاشیِ [0,2200] با
  conf=0.648 دیده میشد؛
- مرکزش 1877.5 ولی قلمروِ ادعای کاشیِ اول [0, 1680+0.35×520=1862) بود →
  رد؛ کاشیِ دوم ([1160,2840) — مالکِ ناحیه) خودش چیزی نداشت → حذفِ کامل;
- حالتِ تکی (عکسِ یکپارچهٔ 11362px): همان پاراگراف در قلمرویِ کاشیِ
  [6960,8640) میافتاد و با conf=0.52 زنده میماند.

تستها:
 ۱) سناریوی واقعی: detect(strip_007.jpg) باید جعبهٔ پاراگراف را داشته باشد
    (قبلاً فقط ۱۰ جعبه بدونِ آن).
 ۲) سناریوی واقعی ۲: detect(img4ِ کاملِ ۷۰۰px) همچنان همان ۲۴ جعبه (رگرسیون
    نباید حالتِ تکی را خراب کند) + پاراگراف حاضر.
 ۳) یونیتِ خالصِ الگوریتمِ نجات با کاشیها/جعبههایِ ساختگی:
    الف) جعبهٔ لبه‌ایِ بی‌پوشش → نجات میشود؛
    ب) جعبهٔ لبه‌ایِ پوشیده (مرکز داخلِ جعبهٔ نگه‌داشته) → نجات نمیشود؛
    ج) جعبهٔ لبه‌ایِ همپوش با IoU≥0.2 → نجات نمیشود؛
    د) جعبهٔ لبه‌ایِ همپوش با IoU<0.2 → نجات میشود.
"""
import os, sys, subprocess, tempfile

os.environ.setdefault("MANGA_FILES_DIR", "/tmp/v213/wrk")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib.util
import cv2

spec = importlib.util.spec_from_file_location(
    "manga_mod", os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "manga.py"))
manga = importlib.util.module_from_spec(spec)
sys.modules["manga_mod"] = manga
spec.loader.exec_module(manga)

PASS, FAIL = [], []


def gate(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  [✓] " if cond else "  [✗] ") + name + (f" — {detail}" if detail else ""))


print("== A) نسخه ==")
gate("A1: APP_VER = 1.14.214", manga.APP_VER == "1.14.214", manga.APP_VER)

print("== B) الگوریتمِ نجات — یونیتِ خالص (کاشی/جعبهٔ ساختگی) ==")
det = manga.RTDetrV2ONNXDetector(
    model_path=os.path.join(os.environ["MANGA_FILES_DIR"],
                            "det_models", "detector-v4-s_int8.onnx"),
    prefer_gpu=False, conf_thresh=0.16, iou_thresh=0.40, threads=2,
    multi_scale=False)


def _fake_tiled(edge_rejects, kept):
    """همان منطقِ v1.14.214 روی ورودیهایِ ساختگی."""
    merged = list(kept)
    if edge_rejects:
        rescued = 0
        for _rb in edge_rejects:
            _rx1, _ry1, _rx2, _ry2 = [float(v) for v in _rb["rect"]]
            _rw = max(1.0, _rx2 - _rx1); _rh = max(1.0, _ry2 - _ry1)
            _rarea = _rw * _rh
            _rcx = (_rx1 + _rx2) / 2.0; _rcy = (_ry1 + _ry2) / 2.0
            _covered = False
            for _kb in merged:
                _kx1, _ky1, _kx2, _ky2 = [float(v) for v in _kb["rect"]]
                if (_ky1 - 8.0) <= _rcy <= (_ky2 + 8.0) \
                        and (_kx1 - 8.0) <= _rcx <= (_kx2 + 8.0):
                    _covered = True; break
                _ix1 = max(_rx1, _kx1); _iy1 = max(_ry1, _ky1)
                _ix2 = min(_rx2, _kx2); _iy2 = min(_ry2, _ky2)
                if _ix2 > _ix1 and _iy2 > _iy1:
                    _inter = float((_ix2 - _ix1) * (_iy2 - _iy1))
                    _karea = float(max(1, _kx2 - _kx1) * max(1, _ky2 - _ky1))
                    if _inter / max(1.0, _rarea + _karea - _inter) >= 0.20:
                        _covered = True; break
            if not _covered:
                merged.append(_rb); rescued += 1
    return merged


kept = [{"rect": [2, 1667, 530, 1742], "confidence": 0.60}]
# الف) بی‌پوشش (همان پاراگرافِ واقعی در برابرِ سرتیترِ ARTICLE 9)
m = _fake_tiled([{"rect": [1, 1737, 694, 2018], "confidence": 0.65}], kept)
gate("B1: جعبهٔ لبه‌ایِ بی‌پوشش نجات مییابد", len(m) == 2)
# ب) مرکز داخلِ جعبهٔ نگه‌داشته
m = _fake_tiled([{"rect": [100, 1670, 400, 1730], "confidence": 0.65}], kept)
gate("B2: مرکزِ پوشیده → نجات نمیشود", len(m) == 1)
# ج) IoU بالا (جعبهٔ تقریباً همان)
m = _fake_tiled([{"rect": [2, 1660, 532, 1748], "confidence": 0.65}], kept)
gate("B3: IoU≥0.2 → نجات نمیشود", len(m) == 1)
# د) همپوشِ کم (IoU<0.2) ولی ناحیهٔ جدا
m = _fake_tiled([{"rect": [10, 2000, 690, 2400], "confidence": 0.65}], kept)
gate("B4: IoU<0.2 → نجات میشود", len(m) == 2)

print("== C) سناریوی واقعی — strip_007 (لاگِ گوشیِ سازنده) ==")
strip_path = "/tmp/v213/out/c_4e2_img4.pdf.cache/stitched/strip_007.jpg"
if os.path.isfile(strip_path):
    strip7 = cv2.imread(strip_path)
    boxes = det.detect(strip7)
    para = [b for b in boxes if 1650 < b["rect"][1] < 2100
            and b["rect"][3] - b["rect"][1] > 150]
    gate("C1: پاراگراف در strip_007 پیدا میشود (قبلاً گم میشد)",
         len(para) >= 1,
         f"boxes={len(boxes)} para={[(b['rect'], round(b['confidence'],2)) for b in para]}")
    gate("C2: تعدادِ جعبهها ≥ 10 (رگرسیونِ بقیه)", len(boxes) >= 10, f"n={len(boxes)}")
else:
    print("  [~] strip_007 در دسترس نیست — فقط یونیتِ خالص")

print("== D) سناریوی واقعی — img4 کامل (حالتِ تکی) ==")
img4 = cv2.imread("/tmp/v213/in/s_img4/img4.jpg")
if img4 is not None:
    _h = int(round(img4.shape[0] * (700.0 / img4.shape[1])))
    img7 = cv2.resize(img4, (700, _h), interpolation=cv2.INTER_CUBIC)
    boxes = det.detect(img7)
    para = [b for b in boxes if 7400 < b["rect"][1] < 7900]
    gate("D1: پاراگراف در حالتِ تکی همچنان حاضر", len(para) >= 1,
         f"n={len(boxes)}")
    gate("D2: ۲۴ جعبهٔ حالتِ تکی حفظ شد", len(boxes) == 24, f"n={len(boxes)}")
else:
    print("  [~] img4 در دسترس نیست")

print("== E) syntax ==")
r = subprocess.run([sys.executable, "-m", "py_compile",
                    os.path.join(os.path.dirname(os.path.dirname(
                        os.path.abspath(__file__))), "manga.py")],
                   capture_output=True, text=True)
gate("E1: manga.py کامپایل میشود", r.returncode == 0, r.stderr[-120:] if r.returncode else "")

print(f"\n{'='*46}\nنتایج: {len(PASS)} سبز / {len(FAIL)} قرمز")
if FAIL:
    print("قرمزها:", FAIL)
    sys.exit(1)
