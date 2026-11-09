# تست واحدِ _web_prog_parse / _web_prog_html — سناریوهای مرجع واقعی
import sys, re
sys.path.insert(0, "/home/z/my-project/Manga-AutoTranslate")

# ایمپورتِ سبک: فقط دو تابعِ پارسر را از manga_app بیرون بکش (بدون gradio)
src = open("/home/z/my-project/Manga-AutoTranslate/manga_app.py",
           encoding="utf-8").read()
ns = {"re": re}
start = src.index("_WEB_PROG_PHASES = (")
end = src.index("C_BG = ")
block = src[start:end]
exec(block, ns)
_web_prog_parse = ns["_web_prog_parse"]
_web_prog_html = ns["_web_prog_html"]

CASES = []

def check(name, log, total_txt, running, want_phase, want_cur, want_tot, want_unit):
    ph, cur, tot, unit = _web_prog_parse(log)
    # کل از total.txt وقتی tot==0
    eff_tot = tot or total_txt
    html = _web_prog_html(ph, cur, eff_tot, running, False, unit)
    ok = (ph == want_phase and cur == want_cur and eff_tot == want_tot
          and unit == want_unit)
    CASES.append((name, ok))
    print(("PASS" if ok else "FAIL"),
          f"| {name}: phase={ph!r} cur={cur} tot={eff_tot} unit={unit!r}")
    if not ok:
        print("   خواسته:", want_phase, want_cur, want_tot, want_unit)
        print("   html:", html)

NOISE = "[🔍] جارویِ بنر: 9 کاندید | بودجه 24\n[🔍188] خطِ آشغالِ لاتین حذف شد: '5'\n"

# ۱) وسطِ استخراجِ مرجع — شمارندهٔ استخراج زنده (مشکلِ گیرِ 0٪)
check("استخراجِ زندهٔ مرجع",
      NOISE + "[*] استخراج متن: 5/27 صفحه\n" + NOISE,
      27, True, "استخراج متن", 5, 27, "صفحه")

# ۲) پاکسازیِ هم‌زمانِ فاز ۱ (بعد از خطِ استخراج آمده — آخرین برنده)
check("پاکسازیِ فاز ۱",
      "[*] استخراج متن: 12/27 صفحه\n[*] پاکسازی متن: 3/27 صفحه\n",
      27, True, "پاکسازی", 3, 27, "صفحه")

# ۳) بعد از اتمامِ استخراج: شمارندهٔ استخراج بازنشسته؛ ترجمه جلو است
check("بعد از استخراج — ترجمه",
      "[*] استخراج متن: 27/27 صفحه\n"
      "[✓] استخراجِ همهٔ 27 صفحه کامل شد — 210 دیالوگ جمع شد؛ حالا ترجمه…\n"
      "[*] ترجمهٔ 210 دیالوگ در 6 بستهٔ پشتسرهم (40+40+40+40+40+10)\n"
      "[*] ترجمه: 40/210 ناحیه\n",
      27, True, "ترجمه", 40, 210, "ناحیه")

# ۴) شمارندهٔ استخراجِ جامانده بعد از «صفحه کامل شد» دیگر نمایش داده نمیشود
check("بازنشستگیِ شمارندهٔ استخراج",
      "[*] استخراج متن: 27/27 صفحه\n"
      "[✓] استخراجِ همهٔ 27 صفحه کامل شد (حالتِ فقط-پاکسازی).\n"
      "[*] پاکسازی متن: 10/27 صفحه\n",
      27, True, "پاکسازی", 10, 27, "صفحه")

# ۵) رندرِ نهایی: «N آماده شد» با کلِ total.txt
check("رندرِ نهایی",
      "[*] ترجمه: 210/210 ناحیه\n[*] صفحهٔ 7 آماده شد\n",
      27, True, "رندر و ذخیره", 8, 27, "صفحهٔ")

# ۶) حالتِ قدیمیِ بدونِ شمارنده (لاگِ نسخهٔ قدیمی) — پس‌سازگاری
check("پس‌سازگاریِ قدیمی",
      NOISE + "[+] متن استخراج شد: 6 ناحیه | زمانِ استخراج: 4.5 ثانیه\n"
      "[*] صفحهٔ 3 آماده شد\n",
      27, True, "رندر و ذخیره", 4, 27, "صفحهٔ")

# ۷) خطا — آخرین رخداد
check("خطا",
      "[*] ترجمه: 40/210 ناحیه\n[!] خطا: سهمیهٔ همهٔ کلیدها تمام شد\n",
      27, False, "خطا", 0, 27, "")

# ۸) شروع — هیچ نشانه‌ای نیست
check("شروعِ خالی", NOISE, 0, True, "", 0, 0, "")

# ۹) درصدِ html
h = _web_prog_html("استخراج متن", 5, 27, True, False, "صفحه")
ok = "5 از 27 صفحه (18٪)" in h and "width:18%" in h
CASES.append(("درصدِ html — استخراج 5/27", ok))
print(("PASS" if ok else "FAIL"), "| درصدِ html:", h[h.index("📊"):h.index("📊")+50])
h = _web_prog_html("ترجمه", 80, 210, True, False, "ناحیه")
ok = "80 از 210 ناحیه (38٪)" in h
CASES.append(("درصدِ html — ترجمه 80/210", ok))
print(("PASS" if ok else "FAIL"), "| درصدِ html ترجمه:", h[h.index("📊"):h.index("📊")+50])
h = _web_prog_html("رندر و ذخیره", 8, 27, True, False, "صفحهٔ")
ok = "صفحهٔ 8 از 27 (29٪)" in h
CASES.append(("درصدِ html — رندر 8/27", ok))
print(("PASS" if ok else "FAIL"), "| درصدِ html رندر:", h[h.index("📊"):h.index("📊")+50])
h = _web_prog_html("تمام شد", 27, 27, False, True, "")
ok = "✅ تمام شد" in h and "width:100%" in h
CASES.append(("html تمام‌شده", ok))
print(("PASS" if ok else "FAIL"), "| تمام‌شده:", h[h.index("✅"):h.index("✅")+40])

# ۱۰) لاگِ واقعیِ کاربر (قبل از فیکس) — فقط «صفحهٔ 1 آماده شد» و فازِ استخراج:
#     حالا باید فاز درست برگردد و cur از لاگ
userlog = """[*] استخراج دوطرفه: صفحهٔ ۱→27 و صفحهٔ 27→۱ همزمان (دیدار در وسط).
[*] strip_000_cover.jpg
[+] متن استخراج شد: 6 ناحیه | زمانِ استخراج: 4.5 ثانیه | موتور: rapidocr
[TIME] page#27 load+extract=4.5s
[*] استخراج متن: 2/27 صفحه
"""
ph, cur, tot, unit = _web_prog_parse(userlog)
ok = ph == "استخراج متن" and cur == 2 and tot == 27
CASES.append(("لاگِ واقعیِ کاربر + شمارنده", ok))
print(("PASS" if ok else "FAIL"), f"| لاگِ کاربر: {ph} {cur}/{tot}")

n_fail = sum(1 for _, ok in CASES if not ok)
print(f"\n{len(CASES) - n_fail}/{len(CASES)} پاس")
sys.exit(1 if n_fail else 0)
