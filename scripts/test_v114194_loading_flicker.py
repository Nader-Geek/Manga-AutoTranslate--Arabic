#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تستِ عملیِ v1.14.194 — «کلِ صفحه رفرش میشه میره میاد انگار چراغ خاموش
روشن کردی … قسمتهایی که متن نداره خالیه — وقتی متن نباشه شکلِ لودینگ
بیار جایِ متن؛ متنش ترجمه شد بذار سرجاش … دکمهٔ دانلودِ آپدیت نمیاد».

سناریوها:
  A) پیش‌نمایشِ زنده (final=False، precleaned): حبابِ درانتظار نشانِ
     لودینگ (چرخِ خاکستریِ 150) دارد؛ حبابِ ترجمهشده نشان ندارد؛
     حبابِ بی‌متنِ OCR هم نشان ندارد.
  B) رندرِ نهایی (final=True): هیچ نشانِ لودینگی رویِ خروجی نیست —
     فالبکِ 192 متنِ مبدأ را رویِ «کپی» رندر میکند و داده بیترجمه میماند.
  C) چرخشِ نشان: دو زمانِ مختلف → پیکسلهایِ قوس جابهجا میشوند.
  D) حبابِ ریزتر از ۲۶ پیکسل: نشان نمیگیرد.
  E) قراردادِ rect=(x, y, عرض، ارتفاع): نشان دقیقاً وسطِ ناحیهٔ واقعی
     می‌نشیند (کشفِ باگِ گوشهفرضی).
  F) تعویضِ بیفلاش: reader.html و قالبِ وب هر دو hotSwap دارند و
     مسیرِ قدیمیِ «src = …?r=» در pollMtimes باقی نمانده.
  G) دکمهٔ دانلود: VERSION سطرهایِ apk را دارد + فالبکِ ABI در
     MainActivity + برچسبِ «دانلود و نصب».
  H) رگرسیونِ 193: هر ۴ سناریویِ تستِ عملیِ نسخهٔ قبل هنوز سبز است.
"""
import os
import re
import subprocess
import sys
import threading

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import manga  # noqa: E402
from manga import MangaTranslator, TextRegion  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILS = []


def check(cond, msg):
    print(("[✓] " if cond else "[✗] ") + msg)
    if not cond:
        FAILS.append(msg)


def make_region(rid, src, rect=(10, 10, 120, 60), ocr_empty=False):
    r = TextRegion(id=rid, boxes=[], source_text=src, rect=rect,
                   kind="dialogue")
    if ocr_empty:
        r.ocr_empty = True
        r.source_text = ""
    return r


def make_mt():
    mt = MangaTranslator.__new__(MangaTranslator)
    mt.debug = False
    mt.clean_only = False
    mt.fake_translate = False
    mt.clean_sfx = False
    return mt


W, H = 480, 320
IMG = np.full((H, W, 3), 245, np.uint8)


def gray150_count(img, rect, margin=6):
    """تعدادِ پیکسلِ خاکستریِ ۱۵۰ (رنگِ نشان) داخلِ ناحیه."""
    x, y, rw, rh = rect
    x0, y0 = max(0, x + margin), max(0, y + margin)
    x1, y1 = min(img.shape[1] - 1, x + rw - margin), min(img.shape[0] - 1,
                                                         y + rh - margin)
    if x1 <= x0 or y1 <= y0:
        return 0
    crop = img[y0:y1, x0:x1].astype(int)
    m = (np.abs(crop[:, :, 0] - 150) <= 5) & (np.abs(crop[:, :, 1] - 150) <= 5) \
        & (np.abs(crop[:, :, 2] - 150) <= 5)
    return int(m.sum())


RECT_T = (20, 20, 200, 90)     # حبابِ ترجمهشده
RECT_W = (20, 180, 200, 90)    # حبابِ درانتظار
RECT_O = (260, 20, 160, 80)    # حبابِ بی‌متنِ OCR


def build_regions():
    tr = make_region(1, "Hello", RECT_T)
    tr.translated_text = "سلام رویِ تو"
    wt = make_region(2, "How are you?", RECT_W)
    oe = make_region(3, "", RECT_O, ocr_empty=True)
    return [tr, wt, oe]


# ── A) پیش‌نمایشِ زنده: حبابِ درانتظار = نشانِ لودینگ ──
mt = make_mt()
mt.translate_regions = lambda regs: None
mt.render_translations = lambda cleaned, regs, raw: cleaned.copy()
out_a, _ = mt.finish_page_phase(IMG.copy(), build_regions(),
                                skip_translate=True, precleaned=IMG.copy(),
                                final=False)
n_wait = gray150_count(out_a, RECT_W)
n_tr = gray150_count(out_a, RECT_T)
n_oe = gray150_count(out_a, RECT_O)
check(n_wait >= 60, f"A: حبابِ درانتظار نشانِ لودینگ دارد ({n_wait} پیکسلِ ۱۵۰)")
check(n_tr <= 5, f"A: حبابِ ترجمهشده نشان ندارد ({n_tr})")
check(n_oe <= 5, f"A: حبابِ بی‌متنِ OCR نشان ندارد ({n_oe})")

# حالتِ «هیچ ترجمهای نرسیده»: همهٔ حبابها لودینگ میگیرند (شاخهٔ else)
wt_only = [make_region(11, "Wait one", (40, 60, 220, 120))]
out_a2, _ = mt.finish_page_phase(IMG.copy(), wt_only,
                                 skip_translate=True, precleaned=IMG.copy(),
                                 final=False)
n_wait2 = gray150_count(out_a2, (40, 60, 220, 120))
check(n_wait2 >= 60,
      f"A: وقتی هیچ ترجمهای نرسیده هم لودینگ می‌نشیند ({n_wait2})")

# ── B) رندرِ نهایی: نشانِ لودینگ ممنوع + فالبکِ 192 سرِ جایش ──
mt_b = make_mt()
seen = {}


def fake_render_b(cleaned, regs, raw):
    seen["regs"] = list(regs)
    return cleaned.copy()


mt_b.translate_regions = lambda regs: None
mt_b.render_translations = fake_render_b
regions_b = build_regions()
out_b, _ = mt_b.finish_page_phase(IMG.copy(), regions_b,
                                  skip_translate=True, precleaned=IMG.copy(),
                                  final=True)
n_wait_b = gray150_count(out_b, RECT_W)
check(n_wait_b <= 5, f"B: رندرِ نهایی هیچ نشانِ لودینگی ندارد ({n_wait_b})")
regs_b = seen.get("regs", [])
check(any(r.id == 2 and r is not regions_b[1]
          and r.translated_text == "How are you?"
          for r in regs_b),
      "B: فالبکِ 192 متنِ مبدأ را رویِ «کپی» رندر کرد (نه خودِ ناحیه)")
check(not (regions_b[1].translated_text or "").strip(),
      "B: دادهٔ ناحیهٔ درانتظار بیترجمه ماند")

# ── C) چرخشِ نشان بینِ دو رندر ──
img_c1 = np.full((160, 160, 3), 255, np.uint8)
img_c2 = np.full((160, 160, 3), 255, np.uint8)
_real_time = manga.time.time
try:
    manga.time.time = lambda: 0.0
    mt._draw_loading_marks_1194(img_c1, [make_region(5, "s", (20, 20, 120, 120))])
    manga.time.time = lambda: 1.0
    mt._draw_loading_marks_1194(img_c2, [make_region(5, "s", (20, 20, 120, 120))])
finally:
    manga.time.time = _real_time
diff = int(np.count_nonzero(np.any(img_c1 != img_c2, axis=2)))
check(diff > 40, f"C: قوسِ لودینگ بینِ دو رندر میچرخد ({diff} پیکسلِ متفاوت)")

# ── D) حبابِ خیلی ریز نشان نمیگیرد ──
img_d = np.full((160, 160, 3), 255, np.uint8)
mt._draw_loading_marks_1194(img_d, [make_region(6, "tiny", (40, 40, 20, 18))])
check(gray150_count(img_d, (40, 40, 20, 18), margin=2) == 0,
      "D: حبابِ ریزتر از ۲۶ پیکسل نشان ندارد")

# ── E) قراردادِ rect=(x, y, عرض، ارتفاع) — نشان وسطِ ناحیهٔ واقعی ──
img_e = np.full((400, 400, 3), 255, np.uint8)
RECT_E = (120, 150, 150, 100)  # x=120, y=150, w=150, h=100
mt._draw_loading_marks_1194(img_e, [make_region(7, "pos", RECT_E)])
cx_e, cy_e = 120 + 75, 150 + 50
crop_e = img_e[cy_e - 20:cy_e + 20, cx_e - 20:cx_e + 20].astype(int)
m_e = (np.abs(crop_e[:, :, 0] - 150) <= 8) & (np.abs(crop_e[:, :, 1] - 150) <= 8) \
    & (np.abs(crop_e[:, :, 2] - 150) <= 8)
check(int(m_e.sum()) > 10,
      f"E: نشان دقیقاً وسطِ ناحیهٔ (x,y,w,h) است ({int(m_e.sum())} پیکسل دورِ مرکز)")

# ── F) تعویضِ بیفلاش در هر دو نمایشگر ──
rh = open(os.path.join(HERE, "android", "app", "src", "main", "assets",
                       "reader.html"), encoding="utf-8").read()
check("hotSwap" in rh and "hotSwap(el, nu)" in rh,
      "F: reader.html — hotSwap تعریف و در pollMtimes بهکار رفته")
check(not re.search(r"el\.setAttribute\('src', el\.dataset\.src\)", rh),
      "F: reader.html — مسیرِ قدیمیِ تعویضِ مستقیمِ src حذف شده")
src_app = open(os.path.join(HERE, "manga_app.py"), encoding="utf-8").read()
i0 = src_app.find("_LIVE_READER_TMPL = ")
i1 = src_app.find('"""', i0 + 25)
tpl = src_app[i0 + len("_LIVE_READER_TMPL = "):i1]
check("function hotSwap" in tpl and "hotSwap(el, P + curDir()" in tpl,
      "F: قالبِ نمایشگرِ وب — hotSwap تعریف و بهکار رفته")
# صحتِ سینتکسِ JS در هر دو (node)
import json
import tempfile
js_r = re.search(r"<script>([\s\S]*?)</script>", rh).group(1)
js_t = tpl.split("<script>", 1)[1].split("</script>", 1)[0]
for name, code in (("reader.html", js_r), ("live_reader", js_t)):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                     encoding="utf-8") as tf:
        tf.write(code)
        tf_path = tf.name
    try:
        r = subprocess.run(["node", "--check", tf_path],
                           capture_output=True, text=True, timeout=30)
        check(r.returncode == 0,
              f"F: سینتکسِ JSِ {name} سالم است"
              + ("" if r.returncode == 0 else " — " + r.stderr[:120]))
    finally:
        os.unlink(tf_path)

# ── G) دکمهٔ دانلودِ آپدیت ──
ver = open(os.path.join(HERE, "VERSION"), encoding="utf-8").read()
vd = dict(ln.split("=", 1) for ln in ver.strip().splitlines() if "=" in ln)
check(vd.get("versionCode") == "199" and vd.get("versionName") == "1.14.194",
      "G: VERSION = 199 / 1.14.194")
check(all(("apk" + k) in vd and vd["apk" + k].startswith("https://github.com/")
          for k in ("Arm64", "Armv7a", "Universal")),
      "G: VERSION هر ۳ سطرِ apkArm64/apkArmv7a/apkUniversal را دارد")
mk = open(os.path.join(HERE, "android", "app", "src", "main", "java", "com",
                       "amirwolf", "mangatranslator", "MainActivity.kt"),
          encoding="utf-8").read()
check("releases/download/apk/\" +" in mk.replace("\n", " ").replace("  ", " ")
      or "releases/download/apk/" in mk,
      "G: MainActivity — فالبکِ لینکِ ثابتِ ریلیزِ apk هست")
check("if (base.isEmpty()) return true" not in mk,
      "G: مسیرِ قدیمیِ «بیصدا آپدیت را دور بریز» حذف شده")
check("دانلود و نصب" in mk,
      "G: برچسبِ دکمهٔ دانلود («دانلود و نصب») هست")
gr = open(os.path.join(HERE, "android", "app", "build.gradle.kts"),
          encoding="utf-8").read()
check('versionCode = 199' in gr and 'versionName = "1.14.194"' in gr,
      "G: build.gradle.kts = 199 / 1.14.194")
check(manga.APP_VER == "1.14.194", f"G: manga.py APP_VER = {manga.APP_VER}")

# ── H) رگرسیونِ 193: تستِ عملیِ نسخهٔ قبل هنوز سبز ──
r = subprocess.run([sys.executable,
                    os.path.join(HERE, "scripts", "test_v114193_live_gate.py")],
                   capture_output=True, text=True, timeout=300)
check(r.returncode == 0,
      "H: هر ۴ سناریویِ test_v114193_live_gate.py هنوز سبز است"
      + ("" if r.returncode == 0 else " — " + r.stdout[-300:]))

print()
if FAILS:
    print(f"✗ {len(FAILS)} سناریو مردود:")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("✓ همهٔ سناریوهایِ v1.14.194 سبز است.")
