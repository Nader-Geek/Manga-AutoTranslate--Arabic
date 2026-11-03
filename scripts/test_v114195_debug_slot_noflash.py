#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تستِ عملیِ v1.14.195 — «دیباگ دو بار نشون میده — هم دیباگِ قبلی هست هم
دیباگِ تمومشده هم مجدد همون عکس نشون میده» + ضدِ چشمکِ سیاه.

سناریوها:
  A) ریشهٔ دیباگِ دوتایی: دیباگِ صفحهٔ ۱ دوبار ذخیره میشود (یکبار در
     _finish_page_now و یکبار در حلقهٔ ذخیرهٔ نهایی — با slot=page_i+1)
     → در پوشهٔ live_debug فقط «یک» فایل ساخته میشود و ریزِ دوم همان
     فایل را بهروز میکند (قبلاً live_0001 + live_0002ِ تکراری میساخت).
  B) اسلاتِ صریحِ دیباگ = شمارهٔ صفحه: صفحهٔ ۳ → live_0003.jpg — فهرستِ
     مرتبشده = ترتیبِ واقعیِ صفحهها؛ دو صفحهٔ متفاوت دو فایلِ متمایز.
  C) اسلاتِ نهاییِ keyدار مثلِ قبل سرِ جاش میماند (رگرسیونِ ۱۶۰):
     دو ریزِ همان key → یک فایل؛ دو key → دو فایل پشتسرهم.
  D) mtimes.txt برای هر ریز خطِ «اسلات زمان» میگیرد (نمایشگرِ وب
     فقط اسلاتِ عوضشده را دوباره لود میکند).
  E) ضدهایِ چشمک در reader.html و قالبِ وب: پوشانهٔ دوبلِ hotSwap
     (__swapBusy/ov.remove/decode) + رِویلِ بعدازدیکودِ اسلاتِ تازه
     (__pend/eager) + position:relative برای مختصاتِ پوشانه — و سینتکسِ
     JS هر دو با node --check سالم.
"""
import os
import re
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAILS = []


def check(cond, msg):
    print(("[✓] " if cond else "[✗] ") + msg)
    if not cond:
        FAILS.append(msg)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

import manga  # noqa: E402

# ---------- A/B: اسلاتِ صریحِ دیباگ ----------
tmp = tempfile.mkdtemp(prefix="m195_dbg_")
os.environ["MANGA_LIVE_DEBUG_DIR"] = tmp
os.environ["MANGA_LIVE_DIR"] = tempfile.mkdtemp(prefix="m195_fin_")
img1 = np.full((40, 30, 3), 200, dtype=np.uint8)
img2 = np.full((40, 30, 3), 90, dtype=np.uint8)

# ریزِ اولِ دیباگِ صفحهٔ ۱ (مثلِ _finish_page_now)
manga._live_dump(img1, dbg=True, slot=1)
f1 = os.path.join(tmp, "live_0001.jpg")
check(os.path.isfile(f1), "A: ریزِ اولِ دیباگِ صفحهٔ ۱ → live_0001.jpg")
n_before = len([f for f in os.listdir(tmp) if f.startswith("live_")])

# ریزِ دومِ پایانِ کار (همان اسلاتِ صریح) — قبلاً فایلِ دومیِ تکراری میساخت
img1_v2 = np.full((40, 30, 3), 150, dtype=np.uint8)
manga._live_dump(img1_v2, dbg=True, slot=1)
files_now = sorted(f for f in os.listdir(tmp) if f.startswith("live_"))
check(len(files_now) == n_before == 1,
      f"A: ریزِ دوباره فایلِ تازه نساخت ({len(files_now)} فایل، باید ۱ باشد)")
check(files_now == ["live_0001.jpg"], "A: همان live_0001.jpg بهروز شد")

# صفحهٔ ۳ → live_0003 (ترتیبِ فهرست = ترتیبِ صفحهها)
manga._live_dump(img2, dbg=True, slot=3)
check(os.path.isfile(os.path.join(tmp, "live_0003.jpg")),
      "B: دیباگِ صفحهٔ ۳ → live_0003.jpg (نه live_0002ِ پشتِ هم)")

# ---------- C: اسلاتِ keyدارِ نهایی (رگرسیونِ ۱۶۰) ----------
fin = os.environ["MANGA_LIVE_DIR"]
manga._LIVE_SLOT_BY_KEY.clear()
manga._live_dump(img1, dbg=False, key="/x/p1.png")
manga._live_dump(img1_v2, dbg=False, key="/x/p1.png")
manga._live_dump(img2, dbg=False, key="/x/p2.png")
fl = sorted(f for f in os.listdir(fin) if f.startswith("live_"))
check(fl == ["live_0001.jpg", "live_0002.jpg"],
      f"C: keyدار — دوبارِ همان صفحه یک فایل، صفحهٔ دوم فایلِ بعد ({fl})")

# ---------- D: mtimes.txt ----------
mt = open(os.path.join(tmp, "mtimes.txt"), encoding="utf-8").read().splitlines()
check(len(mt) == 3 and all(re.match(r"^[13] \d+$", m) for m in mt),
      f"D: mtimes.txt برای هر ریز خطِ «اسلات زمان» دارد ({mt})")

# ---------- E: ضدهایِ چشمک در دو نمایشگر ----------
rh = open("android/app/src/main/assets/reader.html", encoding="utf-8").read()
tpl = open("manga_app.py", encoding="utf-8").read()

for name, src in (("reader.html", rh), ("قالبِ وب", tpl)):
    check("__swapBusy" in src and "__swapNext" in src,
          f"E: {name} — صفِ تعویضِ hotSwap (پوشانهٔ دوبل) هست")
    check("ov.remove()" in src or "ov.remove();" in src.replace("try { ov.remove(); }", "ov.remove();"),
          f"E: {name} — پوشانه بعد از دیکود برداشته میشود")
    check("ov.decode" in src and "el.decode" in src,
          f"E: {name} — دیکودِ پوشانه و دیکودِ اسلات زیرِ پوشانه")
    check("position:absolute;z-index:6" in src,
          f"E: {name} — پوشانه رویِ همان مختصاتِ اسلات (absolute)")
    check("__pend" in src and "'eager'" in src,
          f"E: {name} — رِویلِ بعدازدیکودِ اسلاتِ تازه (lazyِ جدا از DOM نمیآید)")

check(".rdrC .lg{width:100%;position:relative}" in rh,
      "E: reader.html — .lg position:relative (مختصاتِ پوشانه)")
check(".c{max-width:min(100%,900px);margin:0 auto;width:100%;position:relative}" in tpl,
      "E: قالبِ وب — .c position:relative (مختصاتِ پوشانه)")
check("pre = new Image();" not in rh,
      "E: reader.html — مسیرِ قدیمیِ «پردیکودِ Imageِ بیرونی» حذف شد (کش نمیماند؛ بیاثر بود)")
check("hotSwap(el, nu)" in rh and "hotSwap(el, nx)" in rh,
      "E: reader.html — pollMtimes همان hotSwap را صدا میزند + صفِ دوباره")
check("function hotSwap(el, url){" in tpl and
      "hotSwap(el, P + curDir() + 'live_' + pad(slot) + '.jpg?r=' + Date.now())" in tpl,
      "E: قالبِ وب — hotSwap تعریف و در pollMtimes بهکار رفته")

# سینتکسِ JS
for name, html_path, in_tpl in (("reader.html",
                                 "android/app/src/main/assets/reader.html", False),
                                ("قالبِ وب", "manga_app.py", True)):
    s = open(html_path, encoding="utf-8").read()
    if in_tpl:
        i = s.find("_LIVE_READER_TMPL")
        j = s.find("<script>", i)
        k = s.find("</script>", j)
        js = s[j + 8:k]
    else:
        js = re.search(r"<script>(.*)</script>", s, re.S).group(1)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                     encoding="utf-8") as f:
        f.write(js)
        p = f.name
    r = subprocess.run(["node", "--check", p], capture_output=True, text=True)
    check(r.returncode == 0, f"E: سینتکسِ JSِ {name} با node --check سالم")

print()
if FAILS:
    print(f"[!] {len(FAILS)} چک ناموفق:")
    for m in FAILS:
        print("   -", m)
    sys.exit(1)
print("[✓] همهٔ چکهایِ v1.14.195 سبز است.")
