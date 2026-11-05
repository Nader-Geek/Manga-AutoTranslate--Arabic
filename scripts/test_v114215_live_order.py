#!/usr/bin/env python3
"""v1.14.215 — تستِ گیتِ ترتیبِ نمایشِ زنده (فقط از بالا به پایین).

دستورِ سازنده: «نمایش زنده از پایین به بالا هم لود میکنه باید از بالا
به پایین فقط بره». با استخراج/پاکسازیِ دوطرفه صفحه‌ها بی‌ترتیب تمام
میشوند (لاگِ واقعی: ۱،۲،۷،۳،۴،۶،۵) و صفحهٔ ۷ قبل از ۳-۶ در نمایشگر
ظاهر میشد.

تستها (با تصاویرِ واقعی و پوشهٔ liveِ موقت):
 ۱) نسخه = 1.14.215
 ۲) ترتیبِ آزادسازی: dump(1) → فقط ۱؛ dump(7) → هنوز هیچ ۷؛ dump(3) →
    هنوز هیچ ۳ (منتظرِ ۲)؛ dump(2) → ۲ و ۳ با هم آزاد؛ فلاش → ۷ آزاد
 ۳) به‌روزرسانیِ اسلاتِ آزادشده بی‌تأخیر مینشیند (mtime عوض میشود)
 ۴) resume: گیتِ تازه، اسلات‌هایِ موجود روی دیسک را از قبل آزاد میشمارد
 ۵) mtimes.txt فقط در لحظهٔ آزادسازی خط میگیرد (ترتیبِ ۱،۲،۳،…،۷)
 ۶) کامپایلِ manga.py و bridge.py
"""
import os, sys, subprocess, tempfile, shutil, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import importlib.util

spec = importlib.util.spec_from_file_location(
    "manga_mod", os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "manga.py"))
manga = importlib.util.module_from_spec(spec)
sys.modules["manga_mod"] = manga
spec.loader.exec_module(manga)

import cv2
import numpy as np

PASS, FAIL = [], []


def gate(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  [✓] " if cond else "  [✗] ") + name + (f" — {detail}" if detail else ""))


print("== A) نسخه ==")
gate("A1: APP_VER = 1.14.215", manga.APP_VER == "1.14.215", manga.APP_VER)

tmp = tempfile.mkdtemp(prefix="live_seq_test_")
live = os.path.join(tmp, "live")
os.makedirs(live, exist_ok=True)
os.environ["MANGA_LIVE_DIR"] = live

img1 = np.full((400, 300, 3), 255, np.uint8); cv2.putText(img1, "P1", (80, 200), 0, 2, (0, 0, 0), 3)
img7 = np.full((400, 300, 3), 255, np.uint8); cv2.putText(img7, "P7", (80, 200), 0, 2, (0, 0, 0), 3)
img3 = np.full((400, 300, 3), 255, np.uint8); cv2.putText(img3, "P3", (80, 200), 0, 2, (0, 0, 0), 3)
img2 = np.full((400, 300, 3), 255, np.uint8); cv2.putText(img2, "P2", (80, 200), 0, 2, (0, 0, 0), 3)
p1_path = os.path.join(tmp, "p1.jpg"); cv2.imwrite(p1_path, img1)
p7_path = os.path.join(tmp, "p7.jpg"); cv2.imwrite(p7_path, img7)
p3_path = os.path.join(tmp, "p3.jpg"); cv2.imwrite(p3_path, img3)
p2_path = os.path.join(tmp, "p2.jpg"); cv2.imwrite(p2_path, img2)


def exists(slot):
    return os.path.isfile(os.path.join(live, f"live_{slot:04d}.jpg"))


print("== B) ترتیبِ آزادسازی (الگویِ واقعیِ دوطرفه: ۱،۷،۳،۲) ==")
manga._live_seq_reset()
manga._live_page_dump(p1_path, key="k1", slot=1)
gate("B1: dump(1) → live_0001 فوراً", exists(1))
manga._live_page_dump(p7_path, key="k7", slot=7)
gate("B2: dump(7) → هنوز قفل (منتظرِ ۲..۶)", not exists(7))
manga._live_page_dump(p3_path, key="k3", slot=3)
gate("B3: dump(3) → هنوز قفل (منتظرِ ۲)", not exists(3) and not exists(7))
manga._live_page_dump(p2_path, key="k2", slot=2)
gate("B4: dump(2) → زنجیرهٔ ۲و۳ آزاد؛ ۷ هنوز قفل",
     exists(2) and exists(3) and not exists(7))
manga._live_seq_flush()
gate("B5: فلاش → ۷ آزاد", exists(7))

print("== C) به‌روزرسانیِ اسلاتِ آزادشده بی‌تأخیر ==")
_mt = os.path.join(live, "mtimes.txt")
_before = open(_mt, encoding="utf-8").read().strip().splitlines() if os.path.isfile(_mt) else []
time.sleep(0.02)
manga._live_page_dump(p1_path, key="k1", slot=1)  # به‌روزرسانی (key دار)
gate("C1: به‌روزرسانیِ ۱ بی‌تأخیر نشست (خطِ mtimes تازه)",
     len(open(_mt, encoding="utf-8").read().strip().splitlines()) > len(_before))

print("== D) resume — گیتِ تازه دیسک را میبیند ==")
manga._live_seq_reset()  # شروعِ رانِ بعدی در همان پروسه
gate("D1: next = 4 (۱..۳ موجود؛ ۴ نیست) — ۲ به‌روزرسانیِ آزاد رد میشود",
     manga._live_seq_state(live)["next"] == 4)
manga._live_page_dump(p2_path, key="k2", slot=2)
gate("D2: dump(2) دوباره → فوراً (آزادشده)", exists(2))

print("== E) mtimes.txt — ترتیبِ ثبت ==")
_lines = [int(l.split()[0]) for l in open(_mt, encoding="utf-8").read().strip().splitlines() if l.strip()]
gate("E1: اولین ظهورِ اسلاتها به‌ترتیبِ ۱،۲،۳،۷",
     _lines[:4] == [1, 2, 3, 7] if len(_lines) >= 4 else _lines == [1, 2, 3, 7],
     str(_lines))

print("== F) کامپایل ==")
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
r = subprocess.run([sys.executable, "-m", "py_compile",
                    os.path.join(base, "manga.py")], capture_output=True, text=True)
gate("F1: manga.py", r.returncode == 0, r.stderr[-100:] if r.returncode else "")
r = subprocess.run([sys.executable, "-m", "py_compile",
                    os.path.join(base, "android/app/src/main/python/bridge.py")],
                   capture_output=True, text=True)
gate("F2: bridge.py", r.returncode == 0, r.stderr[-100:] if r.returncode else "")

shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{'='*46}\nنتایج: {len(PASS)} سبز / {len(FAIL)} قرمز")
if FAIL:
    print("قرمزها:", FAIL)
    sys.exit(1)
