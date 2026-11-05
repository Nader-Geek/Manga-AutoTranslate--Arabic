#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.14.219 — تستِ فیکسهایِ UI به دستورِ سازنده:
«مشکل اول افزودن مدل فقط وقتی بیاد رفتم رو کاستوم»
«مشکل دوم انتخاب مدل (خودش در فیلدهای بالا بارگذاری می‌شود) ⬆ بالا ⬇ پایین
 🗑 حذف اینو کلا حذف کن … حذف مدل کنار خوده مدل بیاد همون لیست»
«مشکل سوم تنظیمات بکاپ همینجوری باز نباشه وقتی زدم باز شه»
«مشکل سوم بکاپ زدم خودکار دانلود کنه نه این ک مجدد برم دکمه دانلود بزنم»
«واسه اندروید پی سی لینوکس وب همشو باید ست کنیا»

فیکسهایِ این نسخه:
 ۱) کلِ مدیرِ مدلها (راهنما + «+ افزودن به لیست مدل‌ها» + لیست با ✖) فقط
    وقتی دیده میشود که منویِ انتخابِ AI رویِ «custom» باشد (gr.Group
    visible=False + provider.change → toggle).
 ۲) دراپ‌داونِ «انتخاب مدل (خودش در فیلدهای بالا بارگذاری می‌شود)» و
    دکمههایِ ⬆ بالا / ⬇ پایین / 🗑 حذف کلاً حذف شدند؛ حذفِ مدل فقط با
    ضربدرِ ✖ِ کنارِ خودِ مدل در همان لیست است.
 ۳) بخشِ «بکاپ و بازیابی» آکاردئونِ بسته است (open=False) — با کلیک باز
    میشود.
 ۴) «⬇️ گرفتن بکاپ» با یکِ کلیک خودکار دانلود میشود: JS رویِ changeِ
    backup_out با a[download] (URLِ سروشده + orig_name) — نه دکمهٔ
    دانلودِ دوم.
 ۵) فیکسِ ریشهٔ مشترک (اندروید/PC/لینوکس/وب): gradio 6 کامپوننتهایِ
    visible=False را اصلاً در DOM نمیگذارد → کانالهایِ مرورگر↔سرور
    (manga_cm_add_box / manga_cm_del_box / manga_cm_restore / manga_sid /
    manga_sid_holder) از DOM افتاده بودند و افزودنِ مدل/✖/بازیابیِ
    localStorage بیصدا از کار میفتاد؛ حالا visible=True + کلاسِ
    manga-hide-channel (CSS مخفی) → همیشه در DOM اند.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base)

PASS, FAIL = [], []


def gate(name, ok, extra=""):
    (PASS if ok else FAIL).append(name)
    print(("  ✅ " if ok else "  ❌ ") + name + ((" — " + extra) if extra and not ok else ""))


src = open(os.path.join(base, "manga_app.py"), encoding="utf-8").read()

print("== A) نسخه ==")
import manga_app  # noqa: E402
gate("A1: APP_VER = 1.14.219", manga_app.APP_VER == "1.14.219", manga_app.APP_VER)
ver = open(os.path.join(base, "VERSION"), encoding="utf-8").read()
gate("A2: VERSION versionName=1.14.219", "versionName=1.14.219" in ver)
gate("A3: VERSION versionCode=223", "versionCode=223" in ver)

print("== B) مشکل ۱ — مدیرِ مدلها فقط رویِ custom ==")
# v1.14.220 — ساختارِ مدیرِ مدلها عمداً عوض شد (چیپهایِ «نام ✖» زیرِ منوی
# AI بهجایِ گروهِ toggleشده) → گیتهایِ B/Cِ ساختاری ممکن است قرمزِ عمدی
# باشند؛ ولی نباید CRASH کنند — با گاردِ امن اجرا میشوند.


def safe_gate(name, fn):
    try:
        gate(name, bool(fn()))
    except Exception as e:
        gate(name, False, f"گیتِ قدیمی دیگر قابلِ ارزیابی نیست ({type(e).__name__}) — قرمزِ عمدیِ ۲۲۰")


safe_gate("B1: گروهِ مخفیِ مدیرِ مدلها",
          lambda: 'gr.Group(visible=False) as cm_manager_group' in src)
safe_gate("B2: provider.change مدیرِ مدلها را toggle میکند",
          lambda: re.search(r"provider\.change\(\s*\n\s*lambda p: \(gr\.update\([^\n]*\),\s*\n\s*gr\.update\([^\n]*\)\),\s*\n\s*inputs=\[provider\], outputs=\[api_base, cm_manager_group\]",
                            src) is not None)
safe_gate("B3: دکمهٔ افزودن و لیست داخلِ همان گروه‌اند (ترتیبِ سورس)",
          lambda: src.index("as cm_manager_group") < src.index('elem_id="manga_cm_add"')
          < src.index('elem_id="manga_cm_list"') < src.index("manga_cm_restore"))
gate("B4: دامنهٔ API هم فقط رویِ custom (رفتارِ قبلی حفظ — ۲۲۱: درونِ _on_provider_change)",
     'is_custom = (v == "custom")' in src and 'gr.update(visible=is_custom)' in src)

print("== C) مشکل ۲ — حذفِ «انتخاب مدل» و ⬆/⬇/🗑؛ ✖ کنارِ مدل در لیست ==")
for gone, desc in [
    ('label="انتخاب مدل (خودش در فیلدهای بالا بارگذاری می‌شود)"', "دراپ‌داونِ انتخابِ مدل"),
    ("manga_cm_pick", "idِ دراپ‌داون"),
    ("manga_cm_up", "دکمهٔ ⬆"),
    ("manga_cm_down", "دکمهٔ ⬇"),
    ('elem_id="manga_cm_del"', "دکمهٔ 🗑 جداگانه"),
    ('api_name="cm_load"', "اتصالِ cm_pick→فیلدها"),
    ('api_name="cm_up"', "اتصالِ ⬆"),
    ('api_name="cm_down"', "اتصالِ ⬇"),
    ('api_name="cm_del"', "اتصالِ 🗑"),
    ("def _cm_load", "تابعِ _cm_load"),
    ("def _cm_move", "تابعِ _cm_move"),
    ("mv_up_btn", "متغیرِ ⬆"),
    ("mv_down_btn", "متغیرِ ⬇"),
    ("del_model_btn", "متغیرِ 🗑"),
]:
    gate(f"C: حذفِ {desc} ({gone[:34]}…)", gone not in src)
# v1.14.221 — ✖ حالا دکمهٔ واقعیِ کنارِ خودِ منویِ AI است؛ معادلهایِ تازه:
for keep, desc in [
    ('elem_id="manga_cm_del_btn"', "ضربدرِ ✖ِ کنارِ خودِ منو (بهجایِ جدول/چیپ)"),
    ('api_name="cm_del_sel"', "رویدادِ حذفِ مدلِ انتخابشده"),
    ("_cm_del_selected", "حذفِ مدلِ انتخابی از لیست و منو"),
]:
    gate(f"C: حفظِ {desc} ({keep})", keep in src)
gate("C: خروجیهایِ ۲۲۱ — cm_json_box/provider/cm_del_btn",
     "outputs=[custom_models_state, cm_json_box, provider,\n                         cm_del_btn, backup_status]" in src
     and "outputs=[custom_models_state, cm_json_box, provider,\n                         cm_del_btn]" in src)
gate("C: بروندهایِ Importِ ۲۲۱",
     "+ [custom_models_state, cm_json_box, provider,\n                           cm_del_btn, backup_status]" in src)

print("== D) مشکل ۳ — بکاپ = آکاردئونِ بسته ==")
gate("D1: Accordion بهجای Group با open=False",
     re.search(r'with gr\.Accordion\("💾 بکاپ و بازیابی[^"]*", open=False', src) is not None)
gate("D2: steptitleِ جداگانه حذف شد (لیبلِ آکاردئون کافی است)",
     '<span class="stepnum">💾</span>' not in src)

print("== E) مشکل ۳دوم — دانلودِ خودکارِ بکاپ با یک کلیک ==")
gate("E1: رویدادِ changeِ backup_out با JSِ خالص",
     re.search(r"backup_out\.change\(\s*\n\s*fn=None, inputs=\[backup_out\], outputs=\[\],\s*\n\s*js=", src) is not None)
_m = re.search(r'backup_out\.change\(\s*\n\s*fn=None, inputs=\[backup_out\], outputs=\[\],\s*\n\s*js="""(.*?)"""',
               src, re.S)
_js = _m.group(1) if _m else ""
for needle, desc in [
    ("a.download", "download attribute"),
    ("a.click()", "کلیکِ برنامه‌ای (همان لحظه)"),
    ("orig_name", "نامِ فایلِ بکاپ"),
    ("v.url", "URLِ سروشدهٔ gradio"),
]:
    gate(f"E2: JSِ دانلودِ خودکار {desc}", _js and needle in _js)
gate("E3: متنِ وضعیت = دانلودِ خودکار شروع شد",
     "پشتیبان ساخته شد و دانلودِ خودکارش" in src)
gate("E4: کارتِ جایگزین (اگر مرورگر بلاک کرد)",
     "از کارتِ «فایلِ پشتیبان»" in src)

print("== F) فیکسِ ریشه — کانالها همیشه در DOM (اندروید/PC/لینوکس/وب) ==")
gate("F1: کلاسِ مخفیسازِ CSS", ".manga-hide-channel{display:none !important" in src)
for ch, desc in [
    ('elem_id="manga_cm_add_box"', "کانالِ افزودن"),
    ('elem_id="manga_cm_restore"', "کانالِ بازیابیِ localStorage"),
    ('elem_id="manga_sid"', "کانالِ sid"),
    ('elem_id="manga_sid_holder"', "کانالِ sid_holder"),
]:
    # v1.14.221 — کانالِ cm_del_box حذف شد (✖ = دکمهٔ واقعیِ کنارِ منو)
    if ch == 'elem_id="manga_cm_del_box"':
        continue
    seg = src[max(0, src.index(ch) - 220): src.index(ch) + 180]
    gate(f"F2: {desc} visible=True + مخفیِ CSS",
         "visible=True" in seg and "manga-hide-channel" in seg)
gate("F3: cm_json_box دستنخورده (سرور→مرورگر؛ به DOM نیاز ندارد)",
     re.search(r'cm_json_box = gr\.Textbox\(\s*\n\s*value=json\.dumps\([^\n]*\)\s*,\s*\n\s*visible=False', src) is not None)

print("== G) منطقِ سرور (بدونِ مرورگر) ==")
models = [{"name": "m1", "api_base": "https://x/v1", "api_key": "k123456789",
           "model": "gpt-x"}, {"name": "m2", "api_base": "", "api_key": "k2",
                               "model": "gemini-2"}]
# v1.14.221 — ✖ِ حذف حالا دکمهٔ واقعیِ کنارِ منویِ AI است (چیپ/HTML حذف)
gate("G1(۲۲۱): _render_models_html حذف شد",
     not hasattr(manga_app, "_render_models_html"))
gate("G2(۲۲۱): دکمهٔ ✖ِ کنارِ منو در سورس هست (manga_cm_del_btn)",
     'elem_id="manga_cm_del_btn"' in src)
gate("G3: ترتیبِ منویِ AI = auto|gemini|مدلها|custom",
     manga_app._ai_choices(models) == ["auto", "gemini", "m1", "m2", "custom"])
r = manga_app.resolve_ai_named(models, "m1")
gate("G4: resolveِ مدلِ نامی → custom/دامنه/کلید/مدل",
     r == ("custom", "https://x/v1", "k123456789", "gpt-x"), str(r))
gate("G5: resolveِ auto/gemini/custom → None (manga.py دستنخورده)",
     all(manga_app.resolve_ai_named(models, p) is None
         for p in ("auto", "gemini", "custom", "")))
probe = manga_app.resolve_ai_auto(models, "", "")
gate("G6: auto با کلید/لینکِ خالی چیزی را برنمی‌گزیند (گاردِ سالم)",
     isinstance(probe, tuple) and probe[0] == ""
     and any("در دسترس نبودند" in x for x in probe[-1]))
gate("G7: بکاپ = مدلها + تنظیمات (ساختارِ سورس)",
     '"custom_models": models' in src and '"settings": settings' in src
     and '"app_ver": APP_VER' in src)

print("== H) کامپایل ==")
for f in ("manga.py", "manga_app.py"):
    r = subprocess.run([sys.executable, "-m", "py_compile", os.path.join(base, f)],
                       capture_output=True, text=True)
    gate(f"H: py_compile {f}", r.returncode == 0,
         r.stderr[-80:] if r.returncode else "")

print("== I) JSِ دانلودِ خودکار — سینتکسِ سالم ==")
tmpd = tempfile.mkdtemp(prefix="manga219_")
m = re.search(r'backup_out\.change\(\s*\n\s*fn=None, inputs=\[backup_out\], outputs=\[\],\s*\n\s*js="""(.*?)"""',
              src, re.S)
node = shutil.which("node")
if _m and node:
    jp = os.path.join(tmpd, "auto_dl.js")
    open(jp, "w", encoding="utf-8").write(
        "const __f = " + _js.strip() + ";\n")
    r = subprocess.run([node, "--check", jp], capture_output=True, text=True)
    gate("I1: node --check رویِ JSِ دانلودِ خودکار", r.returncode == 0,
         r.stderr[-120:] if r.returncode else "")
else:
    gate("I1: JSِ دانلودِ خودکار استخراج شد", _m is not None)

print("== J) بوتِ واقعیِ وب + کانالها در DOM ==")
env = os.environ.copy()
env["MANGA_APP_PORT"] = "7876"
env["MANGA_WEB"] = "1"
env.pop("GITHUB_ACTIONS", None)
proc = subprocess.Popen([sys.executable, "-u", os.path.join(base, "manga_app.py"), "--web"],
                        cwd=base, env=env, stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, text=True,
                        start_new_session=True)
deadline, ok, cfg = time.time() + 110, False, ""
try:
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        try:
            with urllib.request.urlopen("http://127.0.0.1:7876/", timeout=4) as resp:
                resp.read()
            ok = True
            break
        except Exception:
            time.sleep(2)
    if ok:
        for path in ("/config", "/gradio_api/config"):
            try:
                with urllib.request.urlopen("http://127.0.0.1:7876" + path, timeout=6) as resp:
                    cfg += resp.read().decode("utf-8", "replace")
            except Exception:
                pass
    gate("J1: وب بالا آمد", ok)
    if ok:
        for needle, desc in [
            ("cm_add", "api افزودن"),
            ("cm_del_row", "api حذفِ ✖"),
            ("cm_restore", "api بازیابیِ مدلها"),
            ("backup_settings", "api بکاپ"),
            ("import_settings", "api Import"),
            ("toggle_custom_base", "api toggleِ custom"),
        ]:
            gate(f"J2: {desc} در config", needle in cfg)
        for gone, desc in [
            ('"cm_load"', "api دراپ‌داونِ حذفشده"),
            ('"cm_up"', "api ⬆ حذفشده"),
            ('"cm_down"', "api ⬇ حذفشده"),
        ]:
            gate(f"J3: {desc} دیگر در config نیست", gone not in cfg)
        gate("J4: نسخهٔ 1.14.219 در config", "1.14.219" in cfg)
finally:
    try:
        # gradio زیرپروسهٔ سرور را جدا نگه میدارد — کلِ گروهِ پروسه را بکش
        # (وگرنه زامبی پورتِ 7876 را نگه میدارد و بوتِ بعدی میشکند)
        import signal
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=10)
    except Exception:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass

shutil.rmtree(tmpd, ignore_errors=True)
print(f"\n{'=' * 46}\nنتایج: {len(PASS)} سبز / {len(FAIL)} قرمز")
if FAIL:
    print("قرمزها:", FAIL)
    sys.exit(1)
