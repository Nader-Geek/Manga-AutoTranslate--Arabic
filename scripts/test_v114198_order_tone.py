#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تستِ عملیِ v1.14.198 — دو فیکسِ گزارشِ سازنده:

  ۱. «یهو عکس وسط شده اولی عکس» — ریشه: اسلاتِ نمایشِ زنده از «ترتیبِ
     اتمام» میآمد؛ با استخراجِ دوطرفهٔ ۱۹۷ و پیشنمایشِ جریانی، عکسِ
     وسطِ فصل در اسلاتِ اول مینشست. حالا همهٔ مسیرها slot=page_i+1
     میفرستند — هر صفحه در جایگاهِ خودش پر میشود.
  ۲. «چرا مترجم یهو کتابی شد بخاطر حجم زیاد متن؟» — ریشه: فهرستِ
     چندصدتاییِ درخواستِ واحد، مدل را به ترجمهٔ کتابی/پیوسته میبرد.
     حالا درخواستِ واحد «سقفِ درشت» دارد (۶۰ دیالوگ/۱۰۰۰۰ نویسه،
     MANGA_ONE_REQ_MAX/MANGA_ONE_REQ_CHARS) و در فهرستِ بلند (≥۲۵)
     دستورِ صریحِ ضدِ کتابی به پرامپت مینشیند.
"""

import io
import os
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

FAILS = []


def ok(msg):
    print(f"[✓] {msg}")


def fail(msg):
    FAILS.append(msg)
    print(f"[✗] {msg}")


def gate(cond, msg):
    if cond:
        ok(msg)
    else:
        fail(msg)
    return cond


print("── بارگذاریِ manga.py ──")
import manga  # noqa: E402

gate(manga.APP_VER == "1.14.198", f"APP_VER = {manga.APP_VER}")
src = io.open("manga.py", encoding="utf-8").read()

print("── ۱. ترتیبِ عکس: اسلاتِ صریحِ صفحه ──")
# ۴ مسیرِ زندهٔ صفحه باید slot=page_i+1 بفرستند
n_slot = src.count("_live_page_dump(out_file, key=out_file, slot=page_i + 1)")
n_slot += src.count("_live_page_dump(out_file, key=out_file,\n                                slot=page_i + 1)")
n_slot += src.count("_live_page_dump(out_file, key=out_file, slot=page_i + 1)\n                except")
gate(n_slot >= 3, f"سه مسیرِ finish/preview/final اسلاتِ صریح دارند ({n_slot})")
gate("slot=page_i + 1" in src.split("def process_core")[0] or
     "_live_page_dump(out_file, key=out_file, slot=page_i + 1)\n                except Exception:\n                    pass\n                continue" in src,
     "مسیرِ resume هم اسلاتِ صریح دارد")
gate("def _live_page_dump(out_file: str, key: Optional[str] = None,\n                    slot: Optional[int] = None)" in src,
     "_live_page_dump پارامترِ slot دارد")
# نباید هیچ مسیرِ زندهٔ صفحه بدونِ اسلاتِ صریح مانده باشد
import re as _re  # noqa: E402
_bare = [m.start() for m in _re.finditer(
    r"(?<!def )_live_page_dump\((?![^)]*slot=)[^)]*\)", src)]
gate(len(_bare) == 0,
     f"هیچ _live_page_dump بدونِ slot نمیماند ({len(_bare)} مورد)")

# تستِ کارکردیِ واقعی: صفحات ۲۰ و ۱ و ۲ به ترتیبِ «اتمام» میرسند
# (شبیهسازیِ استخراجِ دوطرفه) — فایلها باید با «شمارهٔ صفحه» ساخته شوند
tmp = tempfile.mkdtemp(prefix="live198_")
os.environ["MANGA_LIVE_DIR"] = tmp
manga._LIVE_SLOT_BY_KEY.clear()


def _img(color):
    a = np.zeros((32, 32, 3), dtype=np.uint8)
    a[:, :] = color
    return a


manga._live_dump(_img((20, 20, 20)), key="p20", slot=20)   # آخرِ فصل اول میرسد
manga._live_dump(_img((255, 0, 0)), key="p1", slot=1)      # صفحهٔ ۱ دوم
manga._live_dump(_img((0, 255, 0)), key="p2", slot=2)      # صفحهٔ ۲ سوم
gate(os.path.isfile(os.path.join(tmp, "live_0001.jpg")),
     "صفحهٔ ۱ در live_0001.jpg (نه اسلاتِ دومِ اتمام)")
gate(os.path.isfile(os.path.join(tmp, "live_0002.jpg")), "صفحهٔ ۲ در live_0002.jpg")
gate(os.path.isfile(os.path.join(tmp, "live_0020.jpg")),
     "صفحهٔ ۲۰ در live_0020.jpg — عکسِ وسط/آخر وسطِ فهرست میماند")
import cv2  # noqa: E402
_px1 = cv2.imread(os.path.join(tmp, "live_0001.jpg"))[16, 16].tolist()
_px20 = cv2.imread(os.path.join(tmp, "live_0020.jpg"))[16, 16].tolist()
gate(all(abs(a - b) <= 3 for a, b in zip(_px1, (255, 0, 0))),
     f"محتوایِ live_0001 = صفحهٔ ۱ ({_px1})")  # jpegِ گرانقدر ±۳
gate(_px20 == [20, 20, 20], f"محتوایِ live_0020 = صفحهٔ ۲۰ ({_px20})")
with io.open(os.path.join(tmp, ".count"), encoding="utf-8") as f:
    gate(f.read().strip() == "20", "شمارندهٔ پوشه = بیشترین اسلات (۲۰)")
_mtimes = io.open(os.path.join(tmp, "mtimes.txt"), encoding="utf-8").read().split()
gate(len(_mtimes) == 6, "mtimes.txt برایِ هر اسلات یک سطر (بهروزرسانیِ تدریجیِ نمایشگر)")

# passthroughِ _live_page_dump
tmp2 = tempfile.mkdtemp(prefix="live198b_")
os.environ["MANGA_LIVE_DIR"] = tmp2
manga._live_page_dump(_img((0, 0, 255)), key="p7", slot=7)
gate(os.path.isfile(os.path.join(tmp2, "live_0007.jpg")),
     "_live_page_dump(slot=…) به _live_dump میرسد")

print("── ۲. «کتابی»: سقفِ درشتِ درخواستِ واحد ──")


def _reg(i, txt="سلام"):
    return manga.TextRegion(id=i, boxes=[], source_text=txt)


g = manga._split_one_request_batches([_reg(i) for i in range(5)])
gate(len(g) == 1 and len(g[0]) == 5,
     "فصلِ معمولی (۵ دیالوگ) همچنان دقیقاً «یک» درخواست")
g = manga._split_one_request_batches([_reg(i) for i in range(130)])
gate([len(x) for x in g] == [60, 60, 10],
     f"۱۳۰ دیالوگ → بستههایِ درشتِ { [len(x) for x in g] } (نه ۱۵تا۱۵تا)")
gate(all(len(x) <= 60 for x in g), "هیچ بستهای از سقفِ ۶۰ بیشتر نیست")
_ids = [r.id for grp in g for r in grp]
gate(_ids == list(range(130)), "ترتیبِ روایی داخلِ بستهها دستنخورده")
_big = [_reg(i, "x" * 1500) for i in range(20)]
g = manga._split_one_request_batches(_big, cap_n=60, cap_c=10000)
gate(all(sum(len(r.source_text) for r in x) <= 10000 for x in g),
     "سقفِ نویسه (۱۰۰۰۰) هم رعایت میشود")
gate(min(len(x) for x in g) >= 2, "بستهها درشت میمانند (تکهتکهٔ ۱۵تایی نمیشود)")
g = manga._split_one_request_batches([], 60, 10000)
gate(g == [], "بافرِ خالی → هیچ بستهای")
gate('os.environ.get(\n                    "MANGA_ONE_REQ_MAX", "60")' in src,
     "سقفِ دیالوگ با MANGA_ONE_REQ_MAX قابلِ تنظیم (پیشفرض ۶۰)")
gate('"MANGA_ONE_REQ_CHARS", "10000"' in src,
     "سقفِ نویسه با MANGA_ONE_REQ_CHARS قابلِ تنظیم (پیشفرض ۱۰۰۰۰)")
gate("return _split_one_request_batches(items, _cap_n, _cap_c)" in src,
     "_make_batches درخواستِ واحد را از helper میگذراند")

print("── ۳. دستورِ ضَدِّ کتابی در پرامپتِ فهرستِ بلند ──")
gate("حبابهایِ دیالوگِ مانگا هستند، نه پاراگرافهایِ" in src,
     "پرامپت: «حبابهایِ دیالوگِ مانگا هستند، نه پاراگرافهایِ یک کتاب»")
gate("لحنِ محاورهایِ زنده بماند" in src and "نه خلاصهسازی" in src,
     "پرامپت: محاورهای بماند، خلاصه/تحتاللفظی ممنوع")
gate("if len(work_regions) >= 25 else \"\")" in src,
     "بلوک فقط برایِ فهرستِ بلند (≥۲۵ آیتم) سوار میشود")

print("── ۴. رگرسیونِ ۱۹۷ (دوطرفه + دوفازی + K3) ──")
gate("def _claim_ext(role" in src, "استخراج دوطرفه سرِ جایش")
gate('extraction_done["v"] = True' in src, "پرچمِ پایانِ استخراج برایِ فاز ۲")
gate('thread_name_prefix="clean2"' in src, "کارگرِ دومِ پاکسازی (پایین→بالا)")
gate("MANGA_TIMEOUT_RETRIES" in src, "AutoRetry همهمدلِ K3 سرِ جایش")
gate("60.0 + 1.5 * len(work_regions)" in src,
     "سقفِ زمانیِ متناسبِ حجمِ K3 سرِ جایش")
gate("_salvage_stream_items" in src, "پارسرِ افزایشیِ استریم سرِ جایش")

print("── ۵. نسخه ──")
_ver = io.open("VERSION", encoding="utf-8").read()
gate("versionName=1.14.198" in _ver, "VERSION = 1.14.198")
gate("versionCode=203" in _ver, "versionCode = 203")
_g = io.open("android/app/build.gradle.kts", encoding="utf-8").read()
gate('versionCode = 203' in _g and 'versionName = "1.14.198"' in _g,
     "build.gradle.kts همگام")

print()
if FAILS:
    print(f"[✗] {len(FAILS)} گیتِ مردود:")
    for m in FAILS:
        print(f"  - {m}")
    sys.exit(1)
print("[✓] همهٔ گیتهایِ v1.14.198 سبز")
