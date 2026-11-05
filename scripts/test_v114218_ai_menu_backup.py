#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.14.218 — تستِ ۴ کارِ خواستهشدهٔ سازنده:
  ۱) دکمهٔ «گرفتن بکاپ» جدا از Import (فایلِ JSONِ همهچیز + بازیابیِ کامل)
  ۲) حذفِ «نام مدل جدید» و جایش «+ افزودن به لیست مدل‌ها» (ماندگار در
     localStorage + داخلِ بکاپ)
  ۳) منویِ انتخابِ AI با گزینهٔ auto (auto → gemini → مدلهایِ کاربر → custom؛
     auto خودش اولینِ در دسترس را انتخاب میکند و رویِ خطا میرود بعدی؛
     resolve در manga_app.py — manga.py دستنخورده)
  ۴) ضربدرِ ✖ کنارِ هر مدلِ کاربر (حذف از لیست و از منویِ AI)
اجرا:  python3 scripts/test_v114218_ai_menu_backup.py
"""
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(base)
sys.path.insert(0, base)

PASS, FAIL = [], []


def gate(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  [✓] " if cond else "  [✗] ") + name + (f" — {detail}" if detail else ""))


print("== A) نسخه‌ها ==")
with open(os.path.join(base, "VERSION"), encoding="utf-8") as f:
    _v = f.read()
gate("A1: VERSION = 1.14.218 / 222",
     "versionName=1.14.218" in _v and "versionCode=222" in _v,
     _v.split()[0:1].__str__())
import importlib.util
spec = importlib.util.spec_from_file_location(
    "manga_app_mod", os.path.join(base, "manga_app.py"))
manga_app = importlib.util.module_from_spec(spec)
sys.modules["manga_app_mod"] = manga_app
spec.loader.exec_module(manga_app)
gate("A2: manga_app.APP_VER = 1.14.218", manga_app.APP_VER == "1.14.218",
     manga_app.APP_VER)
import manga  # APP_VER از موتور — نباید عوض شده باشد
gate("A3: manga.py دستنخورده (APP_VER = 1.14.217)",
     manga.APP_VER == "1.14.217", manga.APP_VER)
gate("A4: PROVIDERS = فقط gemini+custom (کنسول)",
     manga_app.PROVIDERS == ["gemini", "custom"], str(manga_app.PROVIDERS))

print("== B) منویِ AI: auto | gemini | مدلهایِ من | custom ==")
models = [{"name": "m1", "api_base": "https://x/v1", "api_key": "k1", "model": "gpt-x"},
          {"name": "m2", "api_base": "https://y/v1", "api_key": "k2", "model": "ds-y"}]
ch = manga_app._ai_choices(models)
gate("B1: ترتیب = auto, gemini, m1, m2, custom",
     ch == ["auto", "gemini", "m1", "m2", "custom"], str(ch))
gate("B2: خالی = auto, gemini, custom",
     manga_app._ai_choices([]) == ["gemini", "custom"])
gate("B3: نامِ همسان با رزرو تکراری نمیشود",
     manga_app._ai_choices([{"name": "gemini"}, {"name": "m1"}])
     == ["auto", "gemini", "m1", "custom"])

print("== C) resolveِ مدلِ مشخص (manga.py دستنخورده) ==")
r = manga_app.resolve_ai_named(models, "m1", "fallback_key", "fallback_mdl")
gate("C1: m1 → custom + فیلدهای خودش",
     r == ("custom", "https://x/v1", "k1", "gpt-x"), str(r))
r2 = manga_app.resolve_ai_named(
    [{"name": "n1", "api_base": "", "api_key": "kk", "model": "mm"}], "n1")
gate("C2: بدونِ دامنه → gemini", r2 is not None and r2[0] == "gemini", str(r2))
gate("C3: نامِ ناشناخته → None",
     manga_app.resolve_ai_named(models, "nope") is None)
gate("C4: auto/gemini/custom → None (مسیرِ خودشان)",
     manga_app.resolve_ai_named(models, "auto") is None
     and manga_app.resolve_ai_named(models, "gemini") is None
     and manga_app.resolve_ai_named(models, "custom") is None)

print("== D) رفتارِ auto: انتخابِ اولینِ در دسترس + fallback ==")


def _probe_ok(key, prov, base, model="", **kw):
    return [{"key": "***", "ok": True, "error": "", "ms": 1}]


def _probe_all_bad(key, prov, base, model="", **kw):
    return [{"key": "***", "ok": False, "error": "HTTP 401", "ms": 1}]


def _probe_gemini_bad_rest_ok(key, prov, base, model="", **kw):
    if prov == "gemini":
        return [{"key": "***", "ok": False, "error": "کلیدی وارد نشده", "ms": 0}]
    return [{"key": "***", "ok": True, "error": "", "ms": 2}]


p, b, k, m, lines = manga_app.resolve_ai_auto(
    models, "gkey", "gm", probe=_probe_ok)
gate("D1: gemini سالم → همان انتخاب میشود",
     (p, b, k, m) == ("gemini", "", "gkey", "gm"), f"{p}|{lines[-1]}")
p, b, k, m, lines = manga_app.resolve_ai_auto(
    models, "", "gm", probe=_probe_gemini_bad_rest_ok)
gate("D2: gemini خراب → بعدی = m1 (به ترتیبِ افزودن)",
     (p, b, k, m) == ("custom", "https://x/v1", "k1", "gpt-x"),
     f"{p}|{len(lines)} خط")
p, b, k, m, lines = manga_app.resolve_ai_auto(
    models, "gkey", "gm", probe=_probe_all_bad)
gate("D3: هیچکدام نبود → خروجیِ خالی + پیام",
     p == "" and any("هیچ‌کدام" in x for x in lines), f"{p}|{lines[-1] if lines else ''}")


def _probe_raise(key, prov, base, model="", **kw):
    raise RuntimeError("network down")


p2, *_rest = manga_app.resolve_ai_auto(models, "gkey", "gm", probe=_probe_raise)
gate("D4: probeِ خراب خودش = در دسترس نبود (crash نمیکند)",
     p2 == "" and "network down" in " ".join(_rest[-1]), p2)

print("== E) حذفِ مدل — ۲۲۱: ✖ِ واقعیِ کنارِ منو (جدول/چیپِ HTML حذف) ==")
gate("E1: _render_models_html حذف شد؛ ✖ = دکمهٔ manga_cm_del_btn",
     not hasattr(manga_app, "_render_models_html")
     and 'elem_id="manga_cm_del_btn"' in open("manga_app.py", encoding="utf-8").read())
gate("E2: _cm_del_selected مدلِ انتخابشده را حذف میکند",
     manga_app and "def _cm_del_selected" in open("manga_app.py", encoding="utf-8").read())
gate("E3: افزودن به لیست همچنان هست (manga_cm_add)",
     'elem_id="manga_cm_add"' in open("manga_app.py", encoding="utf-8").read())

print("== F) ذخیره/بارگذاریِ دیسک (گوشی/PC/لینوکس) ==")
tmpd = tempfile.mkdtemp(prefix="cm218_")
old_path = manga_app.CUSTOM_MODELS_PATH
manga_app.CUSTOM_MODELS_PATH = os.path.join(tmpd, "manga_models.json")
os.environ.pop("GITHUB_ACTIONS", None)
os.environ.pop("MANGA_WEB", None)
gate("F1: ذخیره در اجرایِ محلی", manga_app.save_custom_models(models) is True)
back = manga_app.load_custom_models()
gate("F2: بارگذاری با همان ترتیب",
     [m.get("name") for m in back] == ["m1", "m2"],
     str([m.get("name") for m in back]))
os.environ["GITHUB_ACTIONS"] = "true"
gate("F3: وب → ذخیرهٔ فایلی رد (localStorage مرورگر)",
     manga_app.save_custom_models([{"name": "z"}]) is False)
os.environ.pop("GITHUB_ACTIONS")
manga_app.CUSTOM_MODELS_PATH = old_path

print("== G) گیتهایِ ساختاریِ سورس ==")
src = open(os.path.join(base, "manga_app.py"), encoding="utf-8").read()
for needle, desc in [
    ("+ افزودن به لیست مدل‌ها", "دکمهٔ جدیدِ افزودن"),
    ("manga_cm_add", "idِ دکمهٔ افزودن"),
    ("manga_cm_add_box", "کانالِ افزودن از مرورگر"),
    ("manga_cm_del_box", "کانالِ حذفِ ✖"),
    ("cm_del_row", "رویدادِ حذفِ ✖"),
    ("cm-x", "کلاسِ ضربدر"),
    ("__mangaCmXBound", "بستنِ یکبارِ کلیکِ ✖"),
    ("window.prompt", "پرسیدنِ نامِ دلخواه"),
    ("manga_backup_btn", "دکمهٔ گرفتن بکاپ"),
    ("گرفتن بکاپ", "برچسبِ دکمهٔ بکاپ"),
    ("manga_import_file", "آپلودرِ Import"),
    ("backup_settings", "api بکاپ"),
    ("import_settings", "api بازیابی"),
    ("manga_custom_models", "localStorageِ مدلها"),
    ("cm_restore", "بازگردانی از مرورگر"),
    ('_init_prov = "auto" if "auto" in _init_ch else "gemini"', "پیشفرضِ پویایِ منویِ AI (۲۲۱)"),
]:
    gate(f"G: {desc} ({needle})", needle in src)
gate("G: «نام مدل جدید» حذف شده",
     "نام مدل جدید" not in src and "manga_cm_name" not in src)
gate("G: بکاپ شاملِ مدلها + تنظیمات",
     '"custom_models": models' in src and '"settings": settings' in src)
gate("G: app_ver از APP_VER (نه هاردکد)",
     '"app_ver": APP_VER' in src and '"app_ver": "1.14.217"' not in src)
gate("G: اتصالِ cm_pick → فیلدها (از 217 حفظ؛ در 219 با خودِ دراپ‌داون حذف شد)",
     "outputs=[provider, api_base, api_keys, model]" not in src
     and "cm_pick" not in src.replace("cm_pick ندارد", ""))
gate("G: بایدهایِ run_translation شاملِ لیستِ مدلها",
     re.search(r"glossary_text, story_brief, api_base,\s*\n\s*custom_models_state", src)
     is not None)
gate("G: resolveِ auto در manga_app (نه manga.py)",
     "resolve_ai_auto(" in src and "models_v" in src)
gate("G: byId یکبار و بیرونِ شرط (فیکسِ localStorage→سرور)",
     src.count("const byId = (id)") == 1
     and src.index("const byId = (id)") < src.index("const apply = () =>"))

print("== H) کامپایل ==")
for f in ("manga.py", "manga_app.py"):
    r = subprocess.run([sys.executable, "-m", "py_compile", os.path.join(base, f)],
                       capture_output=True, text=True)
    gate(f"H: py_compile {f}", r.returncode == 0,
         r.stderr[-80:] if r.returncode else "")

print("== I) بوتِ واقعیِ وب (gradio) ==")


def _boot_web():
    env = os.environ.copy()
    env["MANGA_APP_PORT"] = "7863"
    env["MANGA_WEB"] = "1"
    env.pop("GITHUB_ACTIONS", None)
    proc = subprocess.Popen(
        [sys.executable, "-u", os.path.join(base, "manga_app.py"), "--web"],
        cwd=base, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    deadline = time.time() + 110
    ok, page, cfg = False, "", ""
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        try:
            with urllib.request.urlopen(
                    "http://127.0.0.1:7863/", timeout=4) as resp:
                page = resp.read().decode("utf-8", "replace")
            ok = True
            break
        except Exception:
            time.sleep(2)
    if ok:
        for path in ("/config", "/gradio_api/config"):
            try:
                with urllib.request.urlopen(
                        "http://127.0.0.1:7863" + path, timeout=6) as resp:
                    cfg += resp.read().decode("utf-8", "replace")
            except Exception:
                pass
    return proc, ok, page + cfg


proc, ok, blob = _boot_web()
try:
    gate("I1: صفحهٔ وب بالا آمد", ok)
    if ok:
        for needle, desc in [
            ("منوی انتخاب AI", "منویِ AI"),
            ("+ افزودن به لیست مدل‌ها", "دکمهٔ افزودن"),
            ("گرفتن بکاپ", "دکمهٔ بکاپ"),
            ("Import", "آپلودرِ بازیابی"),
            ("manga_cm_add_box", "کانالِ افزودن"),
            ("manga_cm_del_box", "کانالِ حذف"),
            ("manga_backup_btn", "دکمهٔ بکاپ"),
        ]:
            gate(f"I2: {desc} در صفحهٔ رندرشده", needle in blob)
        gate("I3: «نام مدل جدید» در صفحه نیست",
             "نام مدل جدید" not in blob and "manga_cm_name" not in blob)
        gate("I4: گزینهٔ auto در منویِ AI (config)",
             '"auto"' in blob)
finally:
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass

import shutil
shutil.rmtree(tmpd, ignore_errors=True)
print(f"\n{'=' * 46}\nنتایج: {len(PASS)} سبز / {len(FAIL)} قرمز")
if FAIL:
    print("قرمزها:", FAIL)
    sys.exit(1)
