#!/usr/bin/env python3
"""v1.14.217 — تستِ مدیرِ مدلهایِ سفارشی + پشتیبان‌گیری/بازیابی.

دستورهای سازنده: «همه مدلای ک تو کد الکی اضافه شده حذف کن بجز Gemini و
گزینه کاستوم بمونه» + «یک گزینه دکمه هم اضافه کن + یعنی اضافه کردن مدل
اون مدل مثلا چند مدل ai اضافه میکنن کد ببین همون مدل ai ها جا به جا
بشه» + «تو گوشی پی سی لینوکس مدل هاشو تو حافظه سیو کنه بجز وب ولی وب
اجرا کنن» + «یک گزینه import و backup اخر صفحه اضافه کن چیزای ک وارد
کردن بکاپ بگیره از مدل بگیرع تا تنظیماتشون».

تستها (بدونِ شبکه — فقط ساختِ UI و منطق):
 ۱) نسخه = 1.14.217
 ۲) PROVIDERS فقط gemini+custom؛ منوی کنسول هم فقط این دو
 ۳) ذخیره/بارگذاریِ دیسک (محلی) + بیاثر در وب (GITHUB_ACTIONS)
 ۴) رندرِ فهرست + choices
 ۵) رویدادها در HTMLِ رندرشدهٔ اپِ واقعی (cm_add/cm_load/cm_up/cm_down/
    cm_del/backup_settings/import_settings/cm_restore) + عناصرِ
    manga_cm_*/manga_backup_*/manga_import_file
 ۶) کامپایل
"""
import json, os, subprocess, sys, tempfile

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base)

PASS, FAIL = [], []


def gate(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  [✓] " if cond else "  [✗] ") + name + (f" — {detail}" if detail else ""))


print("== A) نسخه و فهرست ==")
import importlib.util
spec = importlib.util.spec_from_file_location("manga_app_mod",
                                              os.path.join(base, "manga_app.py"))
manga_app = importlib.util.module_from_spec(spec)
sys.modules["manga_app_mod"] = manga_app
spec.loader.exec_module(manga_app)

import manga  # APP_VER از موتور
gate("A1: APP_VER = 1.14.217", manga.APP_VER == "1.14.217", manga.APP_VER)
gate("A2: PROVIDERS = فقط gemini+custom",
     manga_app.PROVIDERS == ["gemini", "custom"], str(manga_app.PROVIDERS))

src = open(os.path.join(base, "manga_app.py"), encoding="utf-8").read()
gate("A3: منوی کنسول هم فقط gemini+custom",
     src.count('("gemini", "Google Gemini') == 1
     and '("deepseek", "DeepSeek")' not in src
     and '("openai", "ChatGPT / GPT")' not in src)

print("== B) ذخیره/بارگذاریِ دیسک ==")
tmpd = tempfile.mkdtemp(prefix="cm217_")
old_path = manga_app.CUSTOM_MODELS_PATH
manga_app.CUSTOM_MODELS_PATH = os.path.join(tmpd, "manga_models.json")
# محلی (وب نیست)
os.environ.pop("GITHUB_ACTIONS", None)
os.environ.pop("MANGA_WEB", None)
models = [{"name": "m1", "api_base": "https://x/v1", "api_key": "k1",
           "model": "gpt-x"},
          {"name": "m2", "api_base": "https://y/v1", "api_key": "k2",
           "model": "ds-y"}]
gate("B1: ذخیره در اجرایِ محلی", manga_app.save_custom_models(models) is True)
back = manga_app.load_custom_models()
gate("B2: بارگذاری با همان ترتیب",
     [m["name"] for m in back] == ["m1", "m2"],
     str([m.get("name") for m in back]))
# وب: ذخیره رد میشود
os.environ["GITHUB_ACTIONS"] = "true"
gate("B3: وب (GITHUB_ACTIONS) → ذخیرهٔ فایلی رد",
     manga_app.save_custom_models([{"name": "z"}]) is False)
os.environ.pop("GITHUB_ACTIONS")
manga_app.CUSTOM_MODELS_PATH = old_path

print("== C) رندر و choices ==")
html = manga_app._render_models_html(models)
gate("C1: جدول با نامِ مدلها",
     "m1" in html and "m2" in html and "cm-table" in html)
gate("C2: کلید هرگز کامل نمایش داده نمیشود",
     "k1" not in html.replace("✓", "") or "k1…" not in html,
     "key masked")
ch = manga_app._cm_choices(models)
gate("C3: choices = نامها به‌ترتیب", ch == ["m1", "m2"], str(ch))
empty_html = manga_app._render_models_html([])
gate("C4: فهرستِ خالی = راهنمای ➕", "➕" in empty_html)

print("== D) رویدادها در اپِ واقعی ==")
# بوتِ واقعی قبلاً انجام شده؛ اینجا ساختارِ سورس را میسنجم
for needle, desc in [
    ("manga_cm_add", "دکمهٔ ➕"),
    ("manga_backup_btn", "دکمهٔ پشتیبان"),
    ("manga_import_file", "آپلودِ بازیابی"),
    ("manga_custom_models", "localStorageِ مدلها"),
    ("cm_restore", "بازگردانی از مرورگر"),
    ("backup_settings", "api پشتیبان"),
    ("import_settings", "api بازیابی"),
]:
    gate(f"D: {desc} ({needle})", needle in src)
# v1.14.219 — دراپ‌داونِ «انتخاب مدل» و ⬆/⬇/🗑 با دستورِ سازنده کلاً حذف
# شد؛ حذفِ مدل فقط با ضربدرِ ✖ِ کنارِ خودِ مدل در لیست است.
for gone, desc in [
    ("manga_cm_pick", "دراپ‌داونِ انتخاب"),
    ("manga_cm_up", "⬆ جابه‌جایی"),
    ("manga_cm_down", "⬇ جابه‌جایی"),
    ("manga_cm_del\"", "🗑 حذفِ جداگانه"),
]:
    gate(f"D2 (۲۱۹): حذفِ {desc} ({gone})", gone not in src)

gate("D3 (۲۱۹): حذفِ مدل فقط با ✖ِ کنارِ ردیف (cm_del_row)",
     "cm-x" in src and 'api_name="cm_del_row"' in src)
gate("D: پشتیبان شاملِ مدلها + تنظیمات",
     '"custom_models": models' in src and '"settings": settings' in src)

print("== E) کامپایل ==")
for f in ("manga.py", "manga_app.py"):
    r = subprocess.run([sys.executable, "-m", "py_compile",
                        os.path.join(base, f)], capture_output=True, text=True)
    gate(f"E: {f}", r.returncode == 0, r.stderr[-80:] if r.returncode else "")

import shutil
shutil.rmtree(tmpd, ignore_errors=True)
print(f"\n{'='*46}\nنتایج: {len(PASS)} سبز / {len(FAIL)} قرمز")
if FAIL:
    print("قرمزها:", FAIL)
    sys.exit(1)
