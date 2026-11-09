# -*- coding: utf-8 -*-
"""v1.14.236 — تستِ منطقِ سه فیکس:

(۱) نوارِ پیشرفتِ وب: _web_prog_parse/_web_prog_html — همان نشانگرهایی
    که اعلانِ اندروید میسازد، از دنبالهٔ لاگ؛ درصد مثلِ اندروید
    (صفحهٔ در حال کار = آماده‌شده + ۱، سقفِ کل).
(۲) بریفِ داستان با چرخشِ کلید: هر تلاش کلیدِ تصادفی؛ خطا → کلیدِ
    بعدی؛ پایان → کلیدِ صفحه برمیگردد؛ متنِ بریف در پرامپتِ همهٔ
    درخواستهاست (_brief_prompt_block).
(۳) چیپِ «↓ صفحه‌های جدید» حذف شد — بررسیِ متنِ قالب.
"""
import io
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace")

FAILED = []


def check(name, cond, extra=""):
    tag = "✅" if cond else "❌"
    print(f"  {tag} {name}" + (f" — {extra}" if extra else ""))
    if not cond:
        FAILED.append(name)


# ══════════ (۱) نوار پیشرفت وب ══════════
print("── تست ۱: پارسِ فاز/صفحه + درصدِ نوارِ پیشرفت ──")
import manga_app as MA

# توالیِ واقعیِ لاگ (برگرفته از لاگهایِ واقعیِ کاربر)
seq = [
    "[*] بارگذاری مدل تشخیص حباب…",
    "[+] مدل تشخیص حباب: detector.onnx",
    "[فاز ۱] استخراج متن شروع شد",
    "    [OCR] ناحیهٔ ۱ از ۱۲ …",
    "[*] صفحهٔ 1 آماده شد",
    "    [OCR] ناحیهٔ ۳ …",
    "[فاز ۳] ترجمهٔ بافر — ۲۰ متن",
    "ترجمه با gemini-3.5-flash-lite",
    "[*] صفحهٔ 2 آماده شد",
    "پاکسازی: روش lama.onnx",
    "[*] صفحهٔ 3 آماده شد",
]
log = "\n".join(seq)

ph, pg = MA._web_prog_parse(log)
check("فاز آخرین نشانه (رندر و ذخیره — مثل اندروید: خطِ «آماده شد» برنده است)",
      ph == "رندر و ذخیره", ph)
check("شمارهٔ صفحهٔ آخرین آماده (۳)", pg == 3, str(pg))

ph_c, _ = MA._web_prog_parse("[*] پاکسازی متن…")
check("«پاکسازی متن…» → پاکسازی", ph_c == "پاکسازی")
ph_s, _ = MA._web_prog_parse("[*] ذخیرهٔ نهایی خروجی‌ها...")
check("«ذخیرهٔ نهایی» → ذخیرهٔ نهایی", ph_s == "ذخیرهٔ نهایی")

# درصد در حال اجرا — مثل اندروید: آماده + ۱ سقفِ کل
html = MA._web_prog_html(ph, pg, 21, True, False)
check("در حال اجرا: متنِ «صفحهٔ ۴ از ۲۱ (۱۹٪)»",
      "صفحهٔ 4 از 21" in html and "19٪" in html, html[html.find("mprog-txt"):][:80])
check("در حال اجرا: میلهٔ ۱۹٪", 'width:19%' in html)

html_done = MA._web_prog_html("تمام شد", 21, 21, False, True)
check("پایان: ۱۰۰٪ + سبز", 'width:100%' in html_done and 'done' in html_done)

# فازِ آغازین بدون نشانه
ph0, pg0 = MA._web_prog_parse("   [*] فونت سیستم: Sahel-Bold.ttf")
check("لاگِ بدونِ نشانه → فازِ خالی", ph0 == "" and pg0 == 0)

html_start = MA._web_prog_html("", 0, 0, True, False)
check("شروعِ بی‌فاز → «در حال شروع…»", "در حال شروع" in html_start)

# فاز استخراج وقتی آخرین خط OCR است
ph1, pg1 = MA._web_prog_parse("    [OCR] خط ۲: HELLO WORLD")
check("خطِ OCR] → استخراج متن", ph1 == "استخراج متن")

ph2, _ = MA._web_prog_parse("[فاز ۳ - ترجمه با gemini/flash-lite] شروع.")
check("فاز ۳ → ترجمه", ph2 == "ترجمه")

ph3, _ = MA._web_prog_parse("خطا: خطای شبکه در ترجمه")
check("خطا: → خطا", ph3 == "خطا")
html_err = MA._web_prog_html("خطا", 5, 21, False, False)
check("خطا → میلهٔ قرمز", 'err' in html_err)

# نشانهٔ «آماده شد» باید فازِ «رندر و ذخیره» بدهد (ترتیبِ اندروید)
phr, pgr = MA._web_prog_parse("[*] صفحهٔ 12 آماده شد")
check("«N آماده شد» → رندر و ذخیره + صفحه ۱۲",
      phr == "رندر و ذخیره" and pgr == 12)

# ۱۶۰+ خطِ قدیمی نباید فاز را قفل کند — فقط دنبالهٔ لاگ ملاک است
old = "\n".join(["[فاز ۱] استخراج متن"] * 200) + "\n" + "ترجمه با مدلِ X"
ph_old, _ = MA._web_prog_parse(old)
check("فاز از «انتهای» لاگ (نه از اول)", ph_old == "ترجمه", ph_old)

# ══════════ (۲) بریف داستان + چرخش کلید ══════════
print("── تست ۲: بریف داستان با چرخشِ کلیدها ──")
import manga
import threading


def _mk_mt(keys, fail_times, ret_text="خلاصهٔ زمینهٔ داستان برای مترجم."):
    """نمونهٔ واقعیِ MangaTranslator بدونِ __init__ + شبکهٔ شبیه‌سازی‌شده.
    tls شبیهِ واقعیست: _apply_api_key هم tls.api_key را ست میکند تا
    _mark_key_cooldown/_current_api_key مثلِ اپِ واقعی کار کنند."""
    import types
    mt = object.__new__(manga.MangaTranslator)
    mt.story_brief_enabled = True
    mt._chapter_brief = ""
    mt._brief_attempted = False
    mt.provider_type = "gemini"
    mt._api_keys = list(keys)
    mt._key_index = 0
    mt._tls = types.SimpleNamespace(api_key=keys[0] if keys else None,
                                     client=None, model_name=None)
    mt.model_name = "gemini-pro"
    mt._model_cascade = ["gemini-3.5-flash-lite", "gemini-pro"]
    mt._key_cooldown_until = {}
    mt._pace_lock = threading.Lock()
    mt._fire_times = []
    applied = []
    # کاربردِ کلید مثلِ واقعی: هم اشیای سراسری هم TLS
    def _fake_apply(k):
        applied.append(k)
        mt._tls.api_key = k
    mt._apply_api_key = _fake_apply
    mt._glossary_prompt_block = lambda src=None: ""
    calls = {"n": 0}

    def _fake_translate(prompt, sys_txt, *, structured=False, **kw):
        calls["n"] += 1
        if calls["n"] <= fail_times:
            raise RuntimeError(
                f"429 Quota exceeded retryDelay:34s key={applied[-1]}")
        return ret_text

    mt._translate_with_gemini = _fake_translate
    return mt, applied, calls


# سناریو A: ۳ کلید؛ اولی سهمیه دارد → دومی/سومی ادامه میدهند
mtA, appliedA, callsA = _mk_mt(["K1", "K2", "مرجع"], fail_times=1)
mtA._build_chapter_brief(["TEXT ONE", "TEXT TWO", "TEXT THREE"] * 3)
check("A: بریف ساخته شد با شکستِ تلاشِ اول",
      mtA._chapter_brief == "خلاصهٔ زمینهٔ داستان برای مترجم.",
      repr(mtA._chapter_brief[:40]))
check("A: ۲ فراخوانیِ شبکه (۱ شکست + ۱ موفق)", callsA["n"] == 2, str(callsA["n"]))
check("A: بعد از سهمیهٔ K1 کلیدِ دیگری امتحان شد",
      appliedA[0] != appliedA[1], str(appliedA))
check("A: کلیدِ شکست‌خورده در استراحت (cooldown) رفت",
      appliedA[0] in mtA._key_cooldown_until, str(appliedA))
check("A: مدلِ اصلی بعد از بریف برگشت", mtA.model_name == "gemini-pro",
      mtA.model_name)

# سناریو B: همهٔ کلیدها میشکنند → بریف خالی + بدون کرش
mtB, appliedB, callsB = _mk_mt(["K1", "K2"], fail_times=99)
mtB._build_chapter_brief(["A TEXT", "B TEXT", "C TEXT"])
check("B: شکستِ همه → بریفِ خالی (بدونِ کرش)", mtB._chapter_brief == "")
check("B: هر دو کلید امتحان شدند (۲ تلاش)", callsB["n"] == 2, str(callsB["n"]))

# سناریو C: تک‌کلید — همان رفتارِ قبل (۱ تلاش)
mtC, appliedC, callsC = _mk_mt(["ONLY"], fail_times=0)
mtC._build_chapter_brief(["LONG TEXT ONE", "LONG TEXT TWO", "LONG TEXT THREE"])
check("C: تک‌کلید سالم → بریف یک‌باره", callsC["n"] == 1
      and mtC._chapter_brief != "", f"n={callsC['n']}")

# سناریو D: متن بریف در پرامپتِ «هر» درخواستِ ترجمه میرود
mtD, _, _ = _mk_mt(["K1"], fail_times=0)
mtD._brief_corpus = []
mtD._build_chapter_brief(["PAGE-ONE TEXT", "PAGE-TWO TEXT", "PAGE-THREE TEXT"])
blk = mtD._brief_prompt_block()
check("D: _brief_prompt_block متنِ بریف را برمیگرداند",
      "زمینه کمکی" in blk and "خلاصهٔ زمینه" in blk, blk[:60])
mtE = object.__new__(manga.MangaTranslator)
mtE.story_brief_enabled = False
mtE._chapter_brief = "چهزی"
check("D: بریفِ خاموش → بلوکِ خالی", mtE._brief_prompt_block() == "")

# ══════════ (۳) حذف چیپ نمایشگر زنده ══════════
print("── تست ۳: حذفِ چیپِ «↓ صفحه‌های جدید» ──")
_src = io.open(os.path.join(_ROOT, "manga_app.py"), encoding="utf-8").read()
_tm = re.search(r'_LIVE_READER_TMPL = """(.*?)"""', _src, re.S)
tmpl = _tm.group(1) if _tm else ""  # فقط قالبِ نمایشگرِ زنده
check("قالب استخراج شد", len(tmpl) > 4000, f"{len(tmpl)} نویسه")
check("دکمهٔ chip حذف شد", 'id="chip"' not in tmpl)
check("مارک‌آپِ دکمهٔ chip حذف شد (class=\"chip\")", 'class="chip"' not in tmpl)
check("متنِ «صفحه‌های جدید» فقط در کامنتِ توضیح است (نه عنصرِ مرئی)",
      tmpl.count("صفحه‌های جدید") == 1
      and "حذف شد" in tmpl[tmpl.find("صفحه‌های جدید") - 120:
                            tmpl.find("صفحه‌های جدید") + 40])
check("CSSِ chip نمایشگرِ زنده حذف شد",
      "position:fixed;bottom:18px;left:18px" not in tmpl)
check("var chip حذف شد", "getElementById('chip')" not in tmpl)
check("نوارِ پیشرفتِ پایینِ نمایشگر سر جایش است",
      'class="pbar"' in tmpl and 'id="pf"' in tmpl)
check("دکمهٔ دیباگ سر جایش است", 'id="db"' in tmpl)

print()
if FAILED:
    print(f"❌ {len(FAILED)} تست رد شد: {FAILED}")
    sys.exit(1)
print("✅ همهٔ تستها پاس شدند.")
