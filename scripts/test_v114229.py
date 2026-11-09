#!/usr/bin/env python3
"""v1.14.229 — تستهایِ پنج مشکلِ سازنده:
۱) متنِ بدونِ حرف (عدد/علامت) ترجمه نمیشود؛ hi... میشود
۲) (UI — دستی/مرورگری؛ اینجا فقط تابعِ فهرستِ مدل سنجیده میشود)
۳) ریسِسِ «صفحه با صفر ترجمه نهایی شد» — تستِ جدایهٔ race
۴) فونتِ بدونِ لیگاتورِ لا = ناپوشیده → فالبک؛ حملات سالم رندر میشود
۵) جعبهٔ متن: اسنپِ تک-لبه ممنوع (پایین‌نیفتادنِ متن)"""
import os, sys, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, "/home/z/my-project/Manga-AutoTranslate")
os.chdir("/home/z/my-project/Manga-AutoTranslate")

import manga
from manga import (MangaTranslator, TextRegion, source_has_letters,
                   list_provider_models)

PASS = FAIL = 0
def chk(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✔ {name}")
    else:
        FAIL += 1
        print(f"  ✘ {name} {extra}")

print("── ۱) source_has_letters ──")
cases = [
    ("123124", False), ("./....", False), ("[] ,./???!?~", False),
    (",    .", False), ("7[00|0]", False), ("10,000G", False),
    ("hi...", True), ("BUT...", True), ("HELLO", True), ("سلام", True),
    ("A", True), ("", False), ("...!?", False), ("220", False),
]
for txt, want in cases:
    chk(f"{txt!r} → {want}", source_has_letters(txt) == want)

print("── ۱b) translate_regions: فیلترِ بدون‌حرف (مسیرِ fake) ──")
tr = MangaTranslator.__new__(MangaTranslator)
tr.fake_translate = True
tr.clean_only = False
tr._extraction_done = True
tr.font_by_style = {}
try:
    tr._brief_corpus = []
    tr._build_chapter_brief = lambda *a, **k: None
except Exception:
    pass
regions = []
for i, (txt, _) in enumerate(cases if False else []):
    pass
mk = [TextRegion(id=i, boxes=[], source_text=t) for i, t in
      enumerate(["123124", "./....", "[] ,./???!?~", "hi...", "BUT..."])]
# فیلتر قبل از fake است؛ بدونِ حرف → هیچ جوابی نمیگیرند
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    tr.translate_regions(mk)
kept = [r for r in mk if (r.translated_text or "").strip()]
kept_src = {r.source_text for r in kept}
chk("فقطِ بامتنِ حرفی ترجمه شدند", kept_src == {"hi...", "BUT..."},
    f"got={kept_src}")
chk("پیامِ «فقط عدد/علامت» چاپ شد", "عدد/علامت" in buf.getvalue())

print("── ۵) _text_block_box: اسنپِ تک-لبه ممنوع ──")
# حباب rect=(0,0,300,500)؛ بلوکِ متنِ وسط: y=180..330 → نباید به پایینِ حباب باز شود
def mkpolys(x0, y0, x1, y1, n=3, fill=0.7):
    ps = []
    for k in range(n):
        yy0 = y0 + k * (y1 - y0) / n
        yy1 = yy0 + (y1 - y0) / n * fill
        ps.append(np.array([[x0, yy0], [x1, yy0], [x1, yy1], [x0, yy1]],
                           dtype=np.float32))
    return ps
# حالت r0ِ img6: متنِ وسطِ حبابِ بلند (بالا دور، پایین «نزدیک» به钟ِ ۳۰٪)
bb = MangaTranslator._text_block_box(
    mkpolys(20, 180, 260, 330), (0, 0, 300, 500), vert=False)
chk("بدونِ اسنپِ عمودی (بالا دور بود)",
    bb is not None and 150 <= bb[1] < 210 and bb[3] < 260, f"bb={bb}")
# متنِ چسبیده به هر دو لبه (fill=۱ — جوهرِ پیوسته تا ۴۷۰؛ با پد
# ۵۶px از هر دو طرف از حباب بیرون میزند → کلَمپ → کلِ حباب)
bb2 = MangaTranslator._text_block_box(
    mkpolys(20, 30, 260, 470, fill=1.0), (0, 0, 300, 500), vert=False)
chk("اسنپِ هر-دو-لبه → کلِ حباب",
    bb2 is not None and bb2[1] <= 5 and bb2[3] >= 490, f"bb2={bb2}")
# نزدیکِ هر دو لبه ولی داخل (پد کوچک؛ ~۱۴۳px از هر طرف مانده ≤۱۵۰)
bb2b = MangaTranslator._text_block_box(
    mkpolys(20, 60, 260, 440, fill=1.0), (0, 0, 300, 500), vert=False)
chk("نزدیکِ دو-لبه (پد داخلِ حباب) → کلِ حباب",
    bb2b is not None and bb2b[1] <= 5 and bb2b[3] >= 490, f"bb2b={bb2b}")
# افقیِ تک-لبه هم ممنوع
bb3 = MangaTranslator._text_block_box(
    mkpolys(150, 100, 280, 300), (0, 0, 300, 400), vert=False)
chk("بدونِ اسنپِ افقیِ تک-لبه",
    bb3 is not None and bb3[0] >= 120, f"bb3={bb3}")

print("── ۴) گاردِ لیگاتورِ لام-الف ──")
broken = "/tmp/t229/Vazir-Code-broken-backup.ttf"
chk("فایلِ فونتِ خراب برایِ تست هست", os.path.isfile(broken))
MangaTranslator._FONT_COVER_CACHE = {}  # کشِ قدیمی پاک
chk("Vazir-Code (بدونِ لا) → ناپوشیده", not MangaTranslator._font_covers(broken))
chk("Sahel-Bold → پوشیده", MangaTranslator._font_covers("fonts/Sahel-Bold.ttf"))
chk("Vazirmatn-Bold → پوشیده", MangaTranslator._font_covers("fonts/Vazirmatn-Bold.ttf"))
# رندرِ واقعیِ «حملات» با فونتِ سیستمِ جدید
shaped = tr._shape_farsi("قهرمان هدف در برابر حملات جادویی مقاوم است!")
f = ImageFont.truetype("fonts/Sahel-Bold.ttf", 48)
im = Image.new("L", (1600, 90), 255)
ImageDraw.Draw(im).text((15, 15), shaped, font=f, fill=0)
a = np.array(im)
ink = int((a < 128).sum())
chk("«حملات» با Sahel-Bold کامل رندر شد (لا حذف نمیشود)", ink > 4000,
    f"ink={ink}")
# متنِ کامل باید ۴ کلمهقطعهٔ واضح داشته باشد (حداقلِ جوهر در برابرِ حالتِ شکسته)
im2 = Image.new("L", (1600, 90), 255)
ImageDraw.Draw(im2).text((15, 15), tr._shape_farsi("قهرمان هدف در برابر حم ت جادویی مقاوم است!"), font=f, fill=0)
ink_broken = int((np.array(im2) < 128).sum())
chk("جوهرِ درست > حالتِ شکسته (لا واقعاً رسم میشود)", ink > ink_broken + 400,
    f"{ink} vs {ink_broken}")

print("── ۲) list_provider_models (بدونِ کلیدِ واقعی — فقط خطای سالم) ──")
mods, err = list_provider_models("gemini", "", "")
chk("بدونِ کلید → خطای «کلیدی وارد نشده»", not mods and "کلید" in err, f"err={err}")
mods2, err2 = list_provider_models("custom", "k", "")
chk("custom بدونِ لینک → خطای لینک", not mods2 and "لینک" in err2, f"err={err2}")


print("── ۳) گیتِ ریسِسِ ۲۲۹ (مرجع: صفِ درِ صف‌شدن نهایی نمیشود) ──")
_src = open("manga.py", encoding="utf-8").read()
chk("A: گاردِ _qd_inflight در _finish_ready_pages هست",
    "_inflight229 = set(_qd_inflight)" in _src
    and "if page_i in _inflight229:" in _src)
chk("B: پرچم قبل از ثبتِ extracted_map ست میشود",
    _src.index("_qd_inflight.add(page_i)")
    < _src.index("extracted_map[page_i] = (out_file, image, None, regions, dbg)"))
chk("C: آزادسازی در finally (حتی رویِ خطا/کوتا)",
    "_qd_inflight.discard(page_i)" in _src
    and "finally:" in _src.split("_qd_inflight.add")[1][:900])
chk("D: جارویِ پایانیِ بدونِ گارد میماند (بن‌بست نشود)",
    "_finish_page_now(page_i)" in _src.split("_finish_ready_pages()")[-1][:200])
# شبیه‌سازیِ همان پنجرهٔ مرگ: کارگرِ B وسطِ صف‌شدنِ صفحهٔ A
# _finish_ready_pages میزند — با گارد، صفحهٔ A نباید نهایی شود.
import time
import threading
_state = {"inflight": set(), "finished": set(), "lock": threading.Lock()}

def _finish_ready_sim():
    with _state["lock"]:
        _infl = set(_state["inflight"])
    for pg in (1, 2):
        if pg in _state["finished"] or pg in _infl:
            continue  # ← منطقِ ۲۲۹ (همان کدِ manga.py)
        _state["finished"].add(pg)

def _worker_a():
    with _state["lock"]:
        _state["inflight"].add(1)
    time.sleep(0.15)  # پنجرهٔ نجاتِ OCR/صف‌شدن
    with _state["lock"]:
        _state["inflight"].discard(1)

def _worker_b():
    time.sleep(0.05)  # وسطِ پنجرهٔ A
    _finish_ready_sim()

_th_a = threading.Thread(target=_worker_a)
_th_b = threading.Thread(target=_worker_b)
_th_a.start(); _th_b.start(); _th_a.join(); _th_b.join()
chk("E: صفحهٔ درِ صف‌شدن نهایی نشد (قبلِ فیکس: میشد)",
    1 not in _state["finished"] and 2 in _state["finished"],
    f"finished={_state['finished']}")


print(f"\n═══ نتیجه: {PASS} ✔ / {FAIL} ✘ ═══")
sys.exit(1 if FAIL else 0)
