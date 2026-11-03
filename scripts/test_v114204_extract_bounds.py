#!/usr/bin/env python3
# v1.14.204 — استخراج نباید از باکسِ detector بیرون بزند
# (گزارشِ سازنده: «وقتی detector متن در اورد نباید استخراج از اون بیشتر
#  بگیره — الان میشه دید کل سه حباب گرفته» + عکسِ دیباگِ ci_imgs)
# سناریوی لاگِ CI (strip_001، ناحیهٔ [18] rect=(67,2056,580x273)):
#   حبابِ کوچکِ «AND DON'T GET TOO INVOLVED.» + «SINCE WHEN WERE WE
#   FRIENDS?» + «YEAH, YEAH~» + تایتلِ کجِ کاغذ «PROPOSED ORDINANCE…»
#   همه در «یک» ناحیه — با یک مستطیلِ 580x273 رویِ هر سه حباب.
# ریشه: کراپِ گسترشیافتهٔ متنِ کج خطِ همسایهٔ بزرگتر را میخواند (فیلترِ
# ۱۸۸ فقط همسایهٔ کوچکتر را حذف میکند) → گسترشِ angle مستطیل را منفجر
# میکند → mergeِ همپوشانی سه حباب را یکجا میگیرد.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
import manga
from manga import MangaTranslator, TextRegion, _clamp_lines_to_det204

import numpy as np

_GATES = []


def gate(name, ok):
    _GATES.append((name, bool(ok)))
    print(f"  [{'✓' if ok else '✗'}] {name}")


def _quad(x1, y1, x2, y2):
    return np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.int32)


def _region(x1, y1, x2, y2, text, polys=None, det_box=None, angle=0.0):
    r = TextRegion(id=-1, boxes=[det_box if det_box is not None
                                 else _quad(x1, y1, x2, y2)],
                   source_text=text, rect=(x1, y1, x2 - x1, y2 - y1),
                   angle=angle, kind="dialogue",
                   ocr_polys=polys or [])
    return r


print("── الف) helperِ قفلِ خطها رویِ باکسِ detector (کارکردی) ──")
# باکسِ detectorِ حبابِ کوچک + خطِ خودِ حباب + خطِ نشتیِ تایتلِ کجِ بزرگ
box = (67, 2056, 187, 2146)
own_poly = np.array([[70, 2060], [180, 2060], [180, 2135], [70, 2135]],
                    dtype=np.int32)          # داخلِ باکس
leak_poly = np.array([[200, 2160], [560, 2160], [560, 2260], [200, 2260]],
                     dtype=np.int32)         # تایتلِ کج — بیرونِ باکس
res = ("AND DON'T GET TOO INVOLVED. PROPOSED ORDINANCE ON",
       [own_poly, leak_poly], [-15.0, -15.0],
       ["AND DON'T GET TOO INVOLVED.", "PROPOSED ORDINANCE ON"],
       [-1, -1])
out = _clamp_lines_to_det204(res, box)
gate("خطِ نشتیِ تایتل حذف شد", len(out[1]) == 1)
gate("متنِ ناحیه فقط متنِ خودِ حباب است",
     out[0] == "AND DON'T GET TOO INVOLVED.")
gate("خط/زاویه/بلوکِ همتراز با هم حذف شدند",
     len(out[2]) == 1 and len(out[3]) == 1 and len(out[4]) == 1
     and out[3][0] == "AND DON'T GET TOO INVOLVED.")

own2 = _clamp_lines_to_det204(res, box, tol=10.0)
gate("tol پیشفرض ۱۰px", own2[0] == out[0])

res_all_in = ("HI", [own_poly], [0.0], ["HI"], [-1])
gate("همه داخلِ باکس → دستنخورده",
     _clamp_lines_to_det204(res_all_in, box) is res_all_in)

res_bad = ("X", [own_poly], [0.0], ["HI", "YO"], [-1])
gate("ساختارِ ناهمتراز → دستنخورده",
     _clamp_lines_to_det204(res_bad, box) is res_bad)

gate("باکس/پلی خالی → دستنخورده",
     _clamp_lines_to_det204(res, None) is res
     and _clamp_lines_to_det204(("", [], [], [], []), box) is not None)

print("── ب) درِ باکسِ detector در merge (سناریوی CI: سه حباب + تایتل) ──")
# عینِ هندسهٔ لاگ: rectهایِ گسترشیافته همپوشانند ولی باکسهایِ detector جدایند
# [18] mergeشدهٔ قدیم: (67,2056,580x273) — حالا چهار ناحیهٔ جدا:
d_and = _quad(67, 2056, 187, 2146)      # AND DON'T GET TOO INVOLVED.
d_sin = _quad(218, 2010, 303, 2095)     # SINCE WHEN WERE WE FRIENDS?
d_tit = _quad(150, 2085, 585, 2325)     # PROPOSED ORDINANCE (تایتلِ کج)
d_yea = _quad(575, 2110, 647, 2180)     # YEAH, YEAH~
r_and = _region(67, 2056, 320, 2325, "AND DON'T GET TOO INVOLVED.",
                polys=[_quad(70, 2060, 180, 2135)], det_box=d_and, angle=-15.0)
r_sin = _region(218, 2010, 303, 2130, "SINCE WHEN WERE WE FRIENDS?",
                polys=[_quad(222, 2015, 300, 2090)], det_box=d_sin,
                angle=-12.0)
r_tit = _region(150, 2085, 647, 2325,
                "PROPOSED ORDINANCE ON RESPECTING STUDENT RIGHTS AND "
                "ESTABLISHING CLASSROOM ORDER",
                polys=[_quad(160, 2090, 580, 2320)], det_box=d_tit,
                angle=-15.0)
r_yea = _region(575, 2110, 660, 2250, "YEAH, YEAH~",
                polys=[_quad(580, 2115, 645, 2175)], det_box=d_yea,
                angle=-19.0)
merged = MangaTranslator._merge_overlapping_regions(
    [r_and, r_sin, r_tit, r_yea], iou_thresh=0.35, contain_thresh=0.65)
gate("چهار ناحیهٔ با باکسِ detectorِ جدا یکی نمیشوند", len(merged) == 4)
gate("متنِ تایتل با متنِ حباب قاطی نشد",
     not any("PROPOSED" in (m.source_text or "")
             and "INVOLVED" in (m.source_text or "") for m in merged))

# حذفِ dedupِ واقعی: دو باکسِ همپوشان رویِ یک حباب باید یکی شوند (رفتارِ قدیمی)
d_a = _quad(100, 100, 300, 200)
d_b = _quad(110, 110, 290, 190)
m2 = MangaTranslator._merge_overlapping_regions(
    [_region(100, 100, 300, 200, "HELLO WORLD THIS IS", det_box=d_a),
     _region(110, 110, 290, 190, "HELLO WORLD", det_box=d_b)],
    iou_thresh=0.35, contain_thresh=0.65)
gate("دوبارِ detectionِ یک حباب همچنان یکی میشود", len(m2) == 1)

# ناحیهٔ بدونِ boxes → رفتارِ قدیمی (rect مبنا)
r_nobox = _region(100, 100, 300, 200, "HELLO WORLD", det_box=None)
m3 = MangaTranslator._merge_overlapping_regions(
    [r_nobox, _region(110, 110, 290, 190, "HELLO", det_box=d_b)],
    iou_thresh=0.35, contain_thresh=0.65)
gate("ناحیهٔ بدونِ باکس → fallback به رفتارِ قدیمی", len(m3) == 1)

print("── ج) نسخهٔ سه‌جا ──")
import re
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mp = open(os.path.join(root, 'manga.py'), encoding='utf-8').read()
ver_py = re.search(r'APP_VER = "([^"]+)"', mp).group(1)
vt = open(os.path.join(root, 'VERSION'), encoding='utf-8').read()
ver_code = re.search(r'versionCode\s*=\s*(\d+)', vt).group(1)
ver_name = re.search(r'versionName\s*=\s*"?([^"\n]+)"?', vt).group(1)
gr = open(os.path.join(root, 'android', 'app', 'build.gradle.kts'),
          encoding='utf-8').read()
gr_code = re.search(r'versionCode\s*=\s*(\d+)', gr).group(1)
gr_name = re.search(r'versionName\s*=\s*"([^"]+)"', gr).group(1)
gate(f"APP_VER={ver_py} == VERSION.versionName == gradle.versionName",
     ver_py == ver_name == gr_name)
gate(f"versionCode همتراز: VERSION={ver_code} gradle={gr_code}",
     ver_code == gr_code)
maj, mi, pa = (int(v) for v in ver_py.split('.'))
gate("نسخهٔ جدید ≥ 1.14.204", (maj, mi, pa) >= (1, 14, 204))

bad = [n for n, ok in _GATES if not ok]
print(f"\n{'✅ همهٔ گیتها سبز:' if not bad else '❌ مردود:'} "
      f"{len(_GATES) - len(bad)}/{len(_GATES)}")
sys.exit(1 if bad else 0)
