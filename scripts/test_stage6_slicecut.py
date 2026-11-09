# -*- coding: utf-8 -*-
"""تستِ A/B مرحلهٔ ۶ — برشِ امنِ چندصفحه‌ای: تعداد/موقعیتِ برشها + هزینهٔ تشخیص.
استفاده: python3 scripts/test_stage6_slicecut.py <محدودهٔ کد> <پیشوندِ خروجی>"""
import sys, os, time, json, hashlib

sys.path.insert(0, os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.'))
import manga
from manga import MangaTranslator
import cv2

FONT = os.path.join(sys.argv[1] if len(sys.argv) > 1 else '.', 'fonts/Amiri-Regular.ttf')
OUT_PREFIX = sys.argv[2] if len(sys.argv) > 2 else 'new'
PAGES = sorted('/tmp/slice_test/pages/' + f for f in os.listdir('/tmp/slice_test/pages'))
WORK = f'/tmp/slice_test/work_{OUT_PREFIX}'
os.makedirs(WORK, exist_ok=True)

t = MangaTranslator(api_key='x-test', font_path=FONT)
t.stitch_max_height = 8000   # مثلِ حالتِ فصل
t.stitch_keep_first = True
t.repair_page_seams = False  # فقط خودِ برش را میسنجیم

calls = {"n": 0, "t": 0.0, "fast": 0}
_orig = t.det.detect
def counted(img, fast=False):
    t0 = time.time()
    try:
        return _orig(img, fast=fast)
    finally:
        calls["n"] += 1
        calls["t"] += time.time() - t0
        if fast:
            calls["fast"] += 1
t.det.detect = counted

t0 = time.time()
strips = t._stitch_pages_for_efficiency(PAGES, WORK)
dt = time.time() - t0

info = {
    "prefix": OUT_PREFIX,
    "n_strips": len(strips),
    "slice_seconds": round(dt, 2),
    "detect_calls": calls["n"],
    "detect_fast_calls": calls["fast"],
    "detect_seconds": round(calls["t"], 2),
    "strips": [],
}
for s in strips:
    with open(s, 'rb') as f:
        info["strips"].append({
            "file": os.path.basename(s),
            "md5": hashlib.md5(f.read()).hexdigest(),
            "h": cv2.imread(s).shape[0],
        })
print(json.dumps(info, ensure_ascii=False, indent=1))
with open(f'/tmp/slice_test/{OUT_PREFIX}.json', 'w', encoding='utf-8') as f:
    json.dump(info, f, ensure_ascii=False, indent=1)
