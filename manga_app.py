#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Optional

APP_NAME = "مانگا مترجم"
APP_VER = "1.14.239"
HERE = os.path.dirname(os.path.abspath(__file__))
MANGA_PY = os.path.join(HERE, "manga.py")
WORK_DIR = os.path.join(HERE, "workspace")
UPLOAD_DIR = os.path.join(WORK_DIR, "input")
OUT_DIR = os.path.join(WORK_DIR, "output")
FONT_DIR = os.path.join(HERE, "fonts")
CFG_PATH = os.path.join(WORK_DIR, "config.json")
HIST_PATH = os.path.join(WORK_DIR, "history.jsonl")
MODELS_DIR = os.path.expanduser("~/.cache/manga_translator_models")

KEY_ENV_ORDER = ("GEMINI_API_KEYS", "GEMINI_API_KEY", "GOOGLE_API_KEY",
                 "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "GROQ_API_KEY",
                 "XAI_API_KEY", "TOGETHER_API_KEY", "OPENROUTER_API_KEY", "API_KEY")
PROVIDER_ALIASES = {"chatgpt": "openai", "grok": "xai"}
# v1.14.217 — دستورِ سازنده: «همه مدلای ک تو کد الکی اضافه شده حذف کن بجز
# Gemini و گزینه کاستوم بمونه» — فهرستِ ارائه‌دهندگانِ رابط فقط همین دو
# میماند؛ موتور (manga.py) همچنان همه را میشناسد (CLI/سازگاریِ configهای
# قدیمی) و مدلهایِ دلخواه با «custom» اجرا میشوند.
PROVIDERS = ["gemini", "custom"]

DEFAULT_GEMINI_KEYS = []#",".join(["123:])

# v1.14.236 — نوارِ پیشرفتِ زیرِ لاگ در وب (خواستهٔ سازنده: «تو گوشی
# یه قابلیت هست ک میگه چند از چند درصد متن استخراج شده و یا کجای کاره…
# میخوام رو پی سی و لینوکس تو وبش پایین لاگ درصدش نشون بده مثل گوشی»).
# همان نشانگرهایی که اعلانِ اندروید میسازند (bridge.py — v1.14.154) اینجا
# از دنبالهٔ لاگِ وب خوانده میشوند: فاز از آخرین خطِ شناخته‌شده و شمارهٔ
# صفحه از آخرین «N آماده شد»؛ درصد = صفحهٔ در حال کار ÷ کل (total.txt
# پوشهٔ live را موتور همان اول می‌نویسد). ترتیب مهم است (اولین تطبیقِ
# هر خط برنده میشود) — عینِ لیستِ اندروید.
_WEB_PROG_PHASES = (
    ("بارگذاری موتور", "بارگذاری مدلها"),
    ("لود نشد", "خطا"),
    ("استخراج متن", "استخراج متن"),
    ("متن استخراج شد", "استخراج متن"),
    ("(PaddleOCR)", "استخراج متن"),
    ("OCR]", "استخراج متن"),
    ("ترجمه:", "ترجمه"),
    ("فاز ۳", "ترجمه"),
    ("ترجمه با", "ترجمه"),
    ("پاکسازی متن", "پاکسازی"),
    ("روش پاکسازی", "پاکسازی"),
    ("پاکسازی:", "پاکسازی"),
    ("ذخیرهٔ نهایی", "ذخیرهٔ نهایی"),
    ("[✓] تمام شد", "تمام شد"),
    ("لغو شد", "لغو شد"),
    ("خطا:", "خطا"),
    ("آماده شد", "رندر و ذخیره"),
    ("OCR:", "استخراج متن"),
    ("پدلِ رسمیِ اندروید", "استخراج متن"),
    ("پدلِ اندروید", "استخراج متن"),
)

# v1.14.239 — شمارنده‌های صریحِ موتور (manga.py — پایپ‌لاینِ K3):
# «استخراج متن: n/N صفحه»، «پاکسازی متن: n/N صفحه»، «ترجمه: n/N ناحیه».
# n/N از خودِ خط خوانده میشود (کلِ همراه، مستقل از total.txt).
_WEB_PROG_COUNT_RES = (
    (re.compile(r"استخراج متن[:：]\s*(\d{1,4})\s*/\s*(\d{1,4})\s*صفحه"),
     "استخراج متن", "صفحه"),
    (re.compile(r"پاکسازی متن[:：]\s*(\d{1,4})\s*/\s*(\d{1,4})\s*صفحه"),
     "پاکسازی", "صفحه"),
    (re.compile(r"ترجمه[:：]\s*(\d{1,4})\s*/\s*(\d{1,4})\s*ناحیه"),
     "ترجمه", "ناحیه"),
)


def _web_prog_parse(log: str):
    """(فاز، مقدارِ فعلی، کلِ همراهِ خط، واحد) از انتهای لاگ — آخرین رخداد ملاک است.

    v1.14.239 — موتور (manga.py) حالا در سبکِ K3 بعد از «هر» صفحهٔ
    استخراج‌شده «استخراج متن: n/N صفحه»، بعد از هر صفحهٔ پاک‌شده
    «پاکسازی متن: n/N صفحه» و بعد از هر بستهٔ ترجمه «ترجمه: n/N ناحیه»
    چاپ میکند (قبلاً تا پایانِ کلِ استخراج هیچ «N آماده شد»ای نبود و
    درصدِ نوار روی 0٪ گیر میکرد — گزارشِ سازنده). اینجا آخرینِ این
    خطها + «N آماده شد» (رندرِ نهایی) و نشانگرهایِ پایان/خطا با هم
    مقایسه میشوند؛ برنده = آخرین رخداد. tot=0 یعنی کل از total.txt
    پوشهٔ live خوانده شود."""
    tail = (log or "").splitlines()[-400:]
    # ۱) شمارنده‌های صریح — آخرین خطِ هر فاز
    marks = {}
    for idx, ln in enumerate(tail):
        for rx, kind, unit in _WEB_PROG_COUNT_RES:
            m = rx.search(ln)
            if m:
                marks[kind] = (idx, int(m.group(1)), int(m.group(2)), unit)
    _ext_done_idx = None
    _ready_idx, _ready_page = None, 0
    _term_idx, _term_phase = -1, ""
    for idx, ln in enumerate(tail):
        if _ext_done_idx is None and "صفحه کامل شد" in ln:
            _ext_done_idx = idx
        m = re.search(r"(\d{1,4})\s+آماده شد", ln)
        if m:
            _ready_idx, _ready_page = idx, int(m.group(1))
        for _k, _v in _WEB_PROG_PHASES:
            if _k in ln and _v in ("تمام شد", "خطا", "لغو شد"):
                _term_idx, _term_phase = idx, _v
    # صفحهٔ آمادهٔ آخر (برای حالتِ خطا)
    _page_legacy = _ready_page
    # ۲) رویدادها: (idx، فاز، cur، tot، unit) — آخرینِشان برنده
    events = []
    for kind, (idx, cur, tot, unit) in marks.items():
        # شمارندهٔ استخراج بعد از «صفحه کامل شد» بازنشسته میشود
        if (kind == "استخراج متن" and _ext_done_idx is not None
                and idx < _ext_done_idx):
            continue
        events.append((idx, kind, cur, tot, unit))
    if _ready_idx is not None:
        events.append((_ready_idx, "رندر و ذخیره", _ready_page + 1, 0, "صفحهٔ"))
    if _term_idx >= 0:
        events.append((_term_idx, _term_phase, _page_legacy, 0, ""))
    if events:
        events.sort(key=lambda e: e[0])
        _, ph, cur, tot, unit = events[-1]
        return ph, cur, tot, unit
    # ۳) فازِ قدیمیِ بدونِ شمارنده (اولین تطبیقِ آخرین خطِ شناختهشده)
    phase = ""
    for ln in reversed(tail):
        for _k, _v in _WEB_PROG_PHASES:
            if _k in ln:
                phase = _v
                break
        if phase:
            break
    return phase, _page_legacy, 0, ""


def _web_prog_html(phase: str, cur: int, total: int, running: bool,
                   done: bool, unit: str = "") -> str:
    """HTML نوار پیشرفت: میله + «فاز — n از N (p٪)» مثل گوشی."""
    cls = ""
    if done:
        cls = " done"
        pct, now = 100, total
    elif not running and phase == "خطا":
        cls = " err"
        pct = min(100, int(cur * 100 / total)) if total > 0 else 0
        now = cur
    else:
        now = min(cur, total) if total > 0 else cur
        pct = int(now * 100 / total) if total > 0 else 0
    txt = ""
    if done:
        txt = (f"✅ تمام شد — {total if total > 0 else cur} صفحه"
               + (f" ({total}/{total})" if total > 0 else ""))
    elif not running and phase == "خطا":
        txt = f"❌ خطا — آخرین صفحهٔ آماده: {cur}" + (
            f" از {total}" if total > 0 else "")
    elif phase:
        if total > 0:
            if unit == "صفحهٔ":
                txt = f"📊 {phase} — صفحهٔ {now} از {total} ({pct}٪)"
            else:
                _u = f" {unit}" if unit else ""
                txt = f"📊 {phase} — {now} از {total}{_u} ({pct}٪)"
        else:
            txt = f"📊 {phase}…"
    else:
        txt = "📊 در حال شروع…"
    return (
        '<div class="mprog">'
        f'<div class="mprog-track"><div class="mprog-fill{cls}" '
        f'style="width:{pct}%"></div></div>'
        f'<div class="mprog-txt">{txt}</div>'
        '</div>'
    )


C_BG = "#0a0a0c"      # پس‌زمینهٔ اصلی — هم‌خانوادهٔ تم وب
C_BG2 = "#121216"     # هدر/نوارها
C_CARD = "#141419"    # کارت‌ها
C_LINE = "#2a2a31"    # خطوط
C_TXT = "#eceae5"
C_MUT = "#9b978f"
C_ACC = "#e63b2e"     # قرمز جوهری مثل وب
ACCENT = C_ACC
C_OK = "#38c98a"
C_ERR = "#ff6a5e"



FONT_BUNDLES = [
    # v1.14.66 — اول «آینهٔ jsDelivr»: raw.githubusercontent.com در ایران
    # اغلب بسته/کند است و فونت‌ها دانلود نمی‌شدند (درخواستِ کاربر).
    ("normal",       "Vazirmatn-Bold.ttf", "کودک — متن عادی حباب", [
        "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@master/fonts/ttf/Vazirmatn-Bold.ttf",
        "https://raw.githubusercontent.com/rastikerdar/vazirmatn/master/fonts/ttf/Vazirmatn-Bold.ttf",
    ]),
    ("free_text",    "Vazirmatn-Regular.ttf", "متن بیرون حباب", [
        "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@master/fonts/ttf/Vazirmatn-Regular.ttf",
        "https://raw.githubusercontent.com/rastikerdar/vazirmatn/master/fonts/ttf/Vazirmatn-Regular.ttf",
    ]),
    ("shout",        "Lalezar-Fixed.ttf", "داد خشم", [
        "https://cdn.jsdelivr.net/gh/amirwolf512k/Manga-AutoTranslate@main/fonts/Lalezar-Fixed.ttf",
        "https://raw.githubusercontent.com/amirwolf512k/Manga-AutoTranslate/main/fonts/Lalezar-Fixed.ttf",
        "https://cdn.jsdelivr.net/gh/rastikerdar/shabnam-font@master/dist/Shabnam-Bold.ttf",
        "https://raw.githubusercontent.com/rastikerdar/shabnam-font/master/dist/Shabnam-Bold.ttf",
    ]),
    ("comedy_shout", "Gandom.ttf", "داد کمدی", [
        "https://cdn.jsdelivr.net/gh/rastikerdar/gandom-font@master/dist/Gandom.ttf",
        "https://raw.githubusercontent.com/rastikerdar/gandom-font/master/dist/Gandom.ttf",
        "https://cdn.jsdelivr.net/gh/rastikerdar/shabnam-font@master/dist/Shabnam-Bold.ttf",
        "https://raw.githubusercontent.com/rastikerdar/shabnam-font/master/dist/Shabnam-Bold.ttf",
    ]),
    ("whisper",      "Nahid.ttf", "زمزمه دست‌نویس", [
        "https://cdn.jsdelivr.net/gh/rastikerdar/nahid-font@master/dist/Nahid.ttf",
        "https://raw.githubusercontent.com/rastikerdar/nahid-font/master/dist/Nahid.ttf",
        "https://cdn.jsdelivr.net/gh/rastikerdar/sahel-font@master/dist/Sahel.ttf",
        "https://raw.githubusercontent.com/rastikerdar/sahel-font/master/dist/Sahel.ttf",
    ]),
    ("thought",      "Samim-Bold.ttf", "تفکر ابری", [
        "https://cdn.jsdelivr.net/gh/rastikerdar/samim-font@master/dist/Samim-Bold.ttf",
        "https://raw.githubusercontent.com/rastikerdar/samim-font/master/dist/Samim-Bold.ttf",
    ]),
    # v1.14.229 — دستورِ سازنده: «یک فونت تو لیست فونت هام هست ک حملات
    # دو کلمش نمیزاره… ببین کدومه عوض کن یک چیز دیگ بزار». فونتِ مقصر
    # Vazir-Code.ttf بود: فونتِ کدنویسی است و «هیچ‌کدام» از شش گلیفِ
    # لیگاتورِ لام-الف (ﻻ/ﻼ/ﻵ/… U+FEF5..FEFC) را ندارد → «حملات» به‌جایِ
    # رندر، «لا» کلاً غیب میشد و «حم ت» میماند (حتی نسخهٔ رسمیِ
    # upstream هم ندارد — تست شد). جایگزین: Sahel-Bold (همهٔ گلیفها،
    # حسِ پنجرهٔ سیستم، و از قبل در fallback همین باندل بود). گاردِ
    # پوششِ ۲۲۹ در manga.py هم فونتِ خرابِ باقی‌مانده در نصبهای قدیمی را
    # خودکار به فونتِ سالم فالبک میکند.
    ("system",       "Sahel-Bold.ttf", "پنجرهٔ سیستم/UI (دیجیتال)", [
        "https://cdn.jsdelivr.net/gh/rastikerdar/sahel-font@master/dist/Sahel-Bold.ttf",
        "https://raw.githubusercontent.com/rastikerdar/sahel-font/master/dist/Sahel-Bold.ttf",
        "https://cdn.jsdelivr.net/gh/amirwolf512k/Manga-AutoTranslate@main/fonts/Sahel-Bold.ttf",
        "https://raw.githubusercontent.com/amirwolf512k/Manga-AutoTranslate/main/fonts/Sahel-Bold.ttf",
    ]),
    ("letter",       "Amiri-Regular.ttf", "نامه/طومار", [
        "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/amiri/Amiri-Regular.ttf",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/amiri/Amiri-Regular.ttf",
    ]),
    ("narrator",     "Shabnam-Bold.ttf", "راوی مستطیل", [
        "https://cdn.jsdelivr.net/gh/rastikerdar/shabnam-font@master/dist/Shabnam-Bold.ttf",
        "https://raw.githubusercontent.com/rastikerdar/shabnam-font/master/dist/Shabnam-Bold.ttf",
    ]),
]

def _read_py_triple_string(src: str, name: str) -> str:
    m = re.search(
        rf'{re.escape(name)}\s*=\s*"""(.*?)"""',
        src,
        flags=re.DOTALL,
    )
    if not m:
        m = re.search(
            rf"{re.escape(name)}\s*=\s*'''(.*?)'''",
            src,
            flags=re.DOTALL,
        )
    if not m:
        return ""
    text = m.group(1)
    if text.startswith("\n"):
        text = text[1:]
    if text.endswith("\n"):
        text = text[:-1]
    return text.strip()


def strip_locked_instruction_tail(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    for marker in ("۷) ورودی و خروجی", "7) ورودی و خروجی", "{TONE_RULE}", "فقط آرایه JSON معتبر"):
        idx = t.find(marker)
        if idx > 0:
            t = t[:idx].rstrip()
            break
    return t.strip()


def load_default_system_instruction(tone_list=None) -> str:
    path = MANGA_PY
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, encoding="utf-8") as f:
            src = f.read()
    except Exception:
        return ""
    text = _read_py_triple_string(src, "DEFAULT_SYSTEM_INSTRUCTION_STYLE")
    if text:
        return text
    full = _read_py_triple_string(src, "DEFAULT_SYSTEM_INSTRUCTION")
    return strip_locked_instruction_tail(full)


_DEFAULT_INSTR_CACHE = None


def default_system_instruction() -> str:
    global _DEFAULT_INSTR_CACHE
    if _DEFAULT_INSTR_CACHE is None:
        _DEFAULT_INSTR_CACHE = load_default_system_instruction() or ""
    return _DEFAULT_INSTR_CACHE


def _norm_instr(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def is_custom_instruction(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    for d in _known_default_instruction_texts():
        if d and _norm_instr(t) == _norm_instr(d):
            return False
    return True


def _known_default_instruction_texts() -> list:
    """متنهایی که «پیشفرض» حساب میشوند و سفارشی نیستند:
    دستورِ کلاسیکِ فارسی + پرامپتهایِ سبکیِ انگلیسیِ v1.14.144."""
    outs = [default_system_instruction()]
    try:
        from manga import PROMPT_PRESETS  # ایمپورتِ سنگین — فقط همین‌جا
        outs += [v for v in PROMPT_PRESETS.values() if isinstance(v, str)]
    except Exception:
        pass
    return [t for t in outs if t]


def normalize_api_base(url: str) -> str:
    if not url:
        return ""
    u = str(url).strip().strip('"').strip("'").rstrip("/")
    if not u:
        return ""
    if "://" not in u:
        u = "https://" + u
    try:
        from urllib.parse import urlparse
        p = urlparse(u)
        host = (p.hostname or "").lower()
    except Exception:
        return ""
    if not host:
        return ""
    if "." not in host and host != "localhost" and not host.startswith("127."):
        return ""
    return u


def _cli_ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


def instruction_for_config(text: str) -> str:
    t = (text or "").strip()
    return t if is_custom_instruction(t) else ""

PROMPT_MODE_DEFAULT = "auto"  # v1.14.146 — پیشفرضِ مشترکِ وب و فرمِ گوشی

PROMPT_MODE_LABELS = {
    "auto": "خودکار (بر اساس سرویس و مدل)",
    "professional": "حرفه‌ای — مخصوص Gemini Flash و Pro",
    "lite": "سبک — مخصوص Flash Lite و سرویس‌های غیر Gemini",
    "classic": "کلاسیک — دستور فارسی قدیمی",
}


# برچسبهایِ نمایشیِ نسخههایِ قبلیِ وباپ (رادیو) — برایِ سازگاریِ کانفیگِ قدیمی
_PROMPT_MODE_LEGACY_LABELS = {
    "خودکار (بر اساس سرویس و مدل)": "auto",
    "حرفه‌ای — Flash و Pro": "professional",
    "سبک — Flash Lite و غیرِ Gemini": "lite",
    "کلاسیک (فارسیِ قدیمی)": "classic",
}


def sanitize_prompt_mode(v) -> str:
    """هر ورودیِ (مقدار یا برچسبِ قدیمی) به یکی از auto/professional/lite/classic —
    v1.14.145: پیشفرضِ همیشه auto (فیکسِ ارورِ invalid choice در manga.py)."""
    s = str(v or "").strip()
    if s in ("auto", "professional", "lite", "classic"):
        return s
    if s in _PROMPT_MODE_LEGACY_LABELS:
        return _PROMPT_MODE_LEGACY_LABELS[s]
    for _k, _lab in PROMPT_MODE_LABELS.items():
        if s == _lab:
            return _k
    return "auto"


def resolve_prompt_preview(mode_v, provider_v, model_v, instr_v):
    """متنِ کاملِ پرامپتِ مؤثر — v1.14.147: تیترِ «پرامپت فعلی: …» حذف شد
    (خواستهٔ کاربر)؛ فقط خودِ متنِ پرامپت برمی‌گردد."""
    t = (instr_v or "").strip()
    if t and is_custom_instruction(t):
        return t
    m = sanitize_prompt_mode(mode_v)
    prov = (provider_v or "gemini").strip()
    mdl = (model_v or "").strip()
    try:
        from manga import resolve_prompt_mode as _rpm, PROMPT_PRESETS as _PP
        resolved = _rpm(m, prov, mdl)
        txt = _PP[resolved]
    except Exception:
        resolved, txt = "classic", default_system_instruction()
    return txt

def ensure_dirs():
    for d in (WORK_DIR, UPLOAD_DIR, OUT_DIR, FONT_DIR):
        os.makedirs(d, exist_ok=True)


def default_keys() -> str:
    for name in KEY_ENV_ORDER:
        v = os.environ.get(name, "").strip()
        if v:
            return v
    return DEFAULT_GEMINI_KEYS


def load_config() -> dict:
    try:
        with open(CFG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        return {}
    try:
        p = str(cfg.get("provider") or "").strip().lower()
        if p in PROVIDER_ALIASES:
            cfg["provider"] = PROVIDER_ALIASES[p]
    except Exception:
        pass
    return cfg


def save_config(cfg: dict) -> None:
    try:
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ── v1.14.217 — مدیرِ مدلهایِ سفارشی ─────────────────────────────
# دستورهای سازنده: «یک گزینه دکمه هم اضافه کن + یعنی اضافه کردن مدل اون
# مدل مثلا چند مدل ai اضافه میکنن … همون مدل ai ها جا به جا بشه» +
# «تو گوشی پی سی لینوکس مدل هاشو تو حافظه سیو کنه بجز وب ولی وب اجرا
# کنن» + «یک گزینه import و backup اخر صفحه اضافه کن چیزای ک وارد کردن
# بکاپ بگیره از مدل بگیرع تا تنظیماتشون».
CUSTOM_MODELS_PATH = os.path.join(WORK_DIR, "manga_models.json")


def _web_host() -> bool:
    """v1.14.217 — وبِ عمومی (GitHub Actions/سرور): ذخیرهٔ فایلی نمیکینیم؛
    مدلها فقط در مرورگرِ خودِ کاربر (localStorage) و حافظهٔ نشست میمانند
    ولی کاملاً اجرا میشوند. PC/لینوکس/گوشی → فایل روی دیسک (ماندگار)."""
    return (os.environ.get("GITHUB_ACTIONS", "").strip() not in ("", "false")
            or os.environ.get("MANGA_WEB", "").strip() == "1"
            or os.environ.get("RAILWAY_STATIC_URL", "").strip() != "")


def load_custom_models() -> list:
    """مدلهایِ سفارشی از فایلِ دیسک (اجرایِ محلی) — در وب فایل نیست.
    ساختار: [{"name","api_base","api_key","model"}, …] به‌ترتیبِ کاربر."""
    try:
        with open(CUSTOM_MODELS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            out = []
            for it in data:
                if not isinstance(it, dict):
                    continue
                name = str(it.get("name") or "").strip()
                if not name:
                    continue
                out.append({
                    "name": name,
                    "api_base": str(it.get("api_base") or "").strip(),
                    "api_key": str(it.get("api_key") or "").strip(),
                    "model": str(it.get("model") or "").strip(),
                })
            return out
    except Exception:
        pass
    return []


def save_custom_models(models: list) -> bool:
    """ذخیره روی دیسک — فقط در اجرایِ محلی (گوشی/PC/لینوکس). در وب رد
    میشود (حافظهٔ نشست + localStorage مرورگر خودش نگه میدارد)."""
    if _web_host():
        return False
    try:
        with open(CUSTOM_MODELS_PATH, "w", encoding="utf-8") as f:
            json.dump(models, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _cm_names(models: list) -> list:
    """v1.14.221 — فقطِ نامهایِ معتبرِ لیستِ مدلها (بدونِ تکرار/خالی)."""
    out = []
    for m in (models or []):
        nm = str(m.get("name") or "").strip()
        if nm and nm not in out:
            out.append(nm)
    return out


def _cm_mask_key(k) -> str:
    """v1.14.222 — کلیدِ ماسکشده برایِ نمایشِ امن (sk-123456…wxyz)."""
    k = str(k or "").strip()
    if not k:
        return ""
    if len(k) <= 10:
        return k[:2] + "…" + k[-2:]
    return k[:6] + "…" + k[-4:]


def _cm_info_html(models: list, name: str) -> str:
    """v1.14.222 — دستورِ سازنده: «وقتی یک چیز کاستوم سیو میکنم لینکش هم
    باید نشون بده» — وقتی مدلِ ذخیرهشدهٔ کاربر در منو انتخاب میشود، مشخصاتِ
    ذخیرهشدهٔ خودش (لینک + مدلِ هوش + کلیدِ ماسکشده) بهصورتِ فقطخواندنی
    زیرِ منو نشان داده میشود — فیلدها پر نمیشوند (دستورِ قبلی: انتخابِ
    مدل خودش را در فیلدها بارگذاری نکند)."""
    nm = str(name or "").strip()
    m = next((x for x in (models or [])
              if str(x.get("name") or "").strip() == nm), None)
    if not m:
        return ""
    esc = (lambda s: str(s or "").replace("&", "&amp;")
           .replace("<", "&lt;").replace(">", "&gt;"))
    base = str(m.get("api_base") or "").strip()
    mdl = str(m.get("model") or "").strip()
    key = _cm_mask_key(m.get("api_key"))
    parts = [f"مدلِ ذخیره‌شدهٔ «{esc(nm)}»",
             "لینک: " + (f"<code>{esc(base)}</code>" if base
                         else "Gemini رسمی (بدونِ دامنهٔ سفارشی)")]
    if mdl:
        parts.append("مدلِ هوش: " + f"<code>{esc(mdl)}</code>")
    if key:
        parts.append(f"کلید: <code>{esc(key)}</code>")
    return "<div class='hint'>" + " — ".join(parts) + "</div>"


def _cm_choices(models: list) -> list:
    """v1.14.219 — (قبلاً برایِ دراپ‌داونِ «انتخاب مدل» بود که حذف شد؛ برای
    سازگاریِ تستهایِ قدیمی نگه داشته میشود.)"""
    return [str(m.get("name") or "").strip() for m in models
            if str(m.get("name") or "").strip()]


# ── v1.14.218 — منویِ انتخابِ AI با گزینهٔ auto ──────────────────
def _ai_choices(models: list) -> list:
    """گزینههایِ منویِ انتخابِ AI به ترتیبِ خواستهٔ سازنده:
    اول «auto»، دوم «gemini»، بعد مدلهایِ اضافهشدهٔ کاربر به ترتیبِ
    افزودن، و آخری «custom».
    v1.14.221 — دستورِ سازنده: «وقتی مدلی تو کاستوم اضافه نکرده باشم
    دکمه auto نیاد تو لیست مدلا» → «auto» فقط وقتی در لیست حداقل یک
    مدلِ ذخیرهشده باشد در منو میآید؛ بدونِ مدل: gemini | custom."""
    names = [n for n in _cm_names(models)
             if n not in ("auto", "gemini", "custom")]
    out = (["auto"] if names else []) + ["gemini"]
    out.extend(names)
    out.append("custom")
    return out


def _gemini_offline_models() -> list:
    """v1.14.232 — لیستِ آفلاینِ مدلهایِ Gemini (دستورِ سازنده: «مدل
    هارو افلاین هم بزار یک بار خودت لیست هارو بگیر بزار کد») — از
    manga.py میآید (GEMINI_FLASH_MODELS_OFFLINE؛ فقط flash و flash-lite
    و flash-preview). اگر import نشد (مثلاً وبِ هاست با بک‌اندِ سبک)
    همین نسخهٔ داخلی استفاده میشود تا دراپ‌داون هرگز خالی نباشد."""
    try:
        from manga import gemini_offline_models as _g
        _lst = _g()
        if _lst:
            return list(_lst)
    except Exception:
        pass
    return [
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-3.8-flash",
        "gemini-3.6-flash",
        "gemini-3-flash-preview",
        "gemini-flash-latest",
    ]


def resolve_ai_named(models: list, pick: str, api_keys: str = "",
                     model_id: str = ""):
    """v1.14.218 — resolveِ «مدلِ مشخصِ کاربر» از منویِ AI به provider واقعی
    برای manga.py (manga.py دستنخورده میماند). اگر کاربر مدلِ مشخصی
    (مدلِ خودش یا gemini) انتخاب کرده باشد فقط و فقط همان استفاده میشود.
    خروجی: (provider, api_base, api_key, model) — نامِ ناشناخته: None."""
    pick = str(pick or "").strip()
    if not pick or pick in ("auto", "gemini", "custom"):
        return None
    for m in (models or []):
        if str(m.get("name") or "").strip() == pick:
            base = str(m.get("api_base") or "").strip()
            return ("custom" if base else "gemini",
                    base,
                    str(m.get("api_key") or "").strip() or (api_keys or ""),
                    str(m.get("model") or "").strip() or (model_id or ""))
    return None


def resolve_ai_auto(models: list, api_keys: str = "", model_id: str = "",
                    probe=None):
    """v1.14.218 — رفتارِ «auto»: خودش بینِ همهٔ مدلهایِ موجود (gemini +
    مدلهایِ کاربر به ترتیبِ افزودن) انتخاب میکند؛ اگر یکی خطا داد یا در
    دسترس نبود سراغِ بعدی میرود. سنجشِ دسترسی = درخواستِ سبکِ همان موتور
    (manga.test_api_keys) — manga.py هیچ تغییری نمیکند.
    خروجی: (provider, api_base, api_key, model, [خطوطِ لاگ]) —
    هیچ‌کدام در دسترس نبود: ("", "", "", "", [خطوط])."""
    models = [m for m in (models or [])
              if isinstance(m, dict) and str(m.get("name") or "").strip()]
    cands = [("gemini", "Gemini", "", str(api_keys or ""),
              str(model_id or ""))]
    for m in models:
        cands.append(("custom",
                      str(m.get("name") or "").strip(),
                      str(m.get("api_base") or "").strip(),
                      str(m.get("api_key") or "").strip(),
                      str(m.get("model") or "").strip()))
    lines = ["🤖 حالتِ auto — بررسیِ دسترسیِ مدلها…"]
    if probe is None:
        try:
            from manga import test_api_keys as probe
        except Exception as e:
            lines.append(f"⚠ موتور برایِ تستِ دسترسی بارگذاری نشد "
                         f"({str(e)[:120]}) — «gemini» انتخاب شد.")
            return ("gemini", "", str(api_keys or ""),
                    str(model_id or ""), lines)
    for prov, label, base, key, mdl in cands:
        try:
            res = probe(key, prov, base, model=mdl)
            ok = any(isinstance(r, dict) and r.get("ok") for r in (res or []))
            err = "; ".join(str(r.get("error") or "") for r in (res or [])
                            if isinstance(r, dict) and not r.get("ok"))[:160]
        except Exception as e:
            ok, err = False, str(e)[:160]
        if ok:
            lines.append(f"🤖 auto: «{label}» در دسترس است → انتخاب شد.")
            return (prov, base, key, mdl, lines)
        lines.append(f"🤖 auto: «{label}» در دسترس نیست"
                     + (f" ({err})" if err else "") + " → بعدی…")
    lines.append("❌ auto: هیچ‌کدام از مدلها در دسترس نبودند.")
    return ("", "", "", "", lines)


def find_font() -> str:
    cands = []
    if os.path.isdir(FONT_DIR):
        for f in sorted(os.listdir(FONT_DIR)):
            if f.lower().endswith((".ttf", ".otf")):
                cands.append((0 if "vazir" in f.lower() else 1, os.path.join(FONT_DIR, f)))
    for d in (HERE, os.path.expanduser("~/fonts"), os.path.expanduser("~/.fonts")):
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.lower().endswith((".ttf", ".otf")):
                    cands.append((1, os.path.join(d, f)))
    return cands[0][1] if cands else ""


def _download(url: str, dst: str) -> bool:
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r, open(dst, "wb") as f:
            shutil.copyfileobj(r, f)
        return os.path.getsize(dst) > 20_000
    except Exception:
        try:
            os.remove(dst)
        except Exception:
            pass
        return False


def download_fonts(log=print) -> int:
    
    os.makedirs(FONT_DIR, exist_ok=True)
    n = 0
    for slot, fname, desc, urls in FONT_BUNDLES:
        dst = os.path.join(FONT_DIR, fname)
        if os.path.isfile(dst) and os.path.getsize(dst) > 20_000:
            continue
        log(f"  ⬇ {fname} ({desc}) ...")
        ok = False
        for url in urls:
            if _download(url, dst):
                ok = True
                break
        if ok:
            n += 1
            log(f"  ✔ {fname}")
        else:
            log(f"  ✖ {fname} ناموفق — بعداً خودتان در fonts/ بگذارید")
    return n

GITHUB_RAW_BASE = ("https://raw.githubusercontent.com/"
                   "amirwolf512k/Manga-AutoTranslate/main/")
# v1.14.33: لانچرها هم آپدیت می‌شوند (Manga.bat / manga.sh)
UPDATE_FILES = ("manga.py", "manga_app.py", "Manga.bat", "manga.sh")
# v1.14.33: چکِ آپدیت حالا ارزان است (فایل VERSION چندبایتی) → هر ۳۰ دقیقه
UPDATE_INTERVAL_S = 30 * 60
UPD_DIR = os.path.join(WORK_DIR, "updates")


def _read_ver_from_src(src: str) -> str:
    m = re.search(r'APP_VER\s*=\s*"([^"]+)"', src or "")
    return m.group(1) if m else "0"


def _cmp_ver(a: str, b: str) -> int:
    try:
        pa = [int(x) for x in str(a).split(".")]
        pb = [int(x) for x in str(b).split(".")]
    except Exception:
        return 0
    while len(pa) < len(pb):
        pa.append(0)
    while len(pb) < len(pa):
        pb.append(0)
    return (pa > pb) - (pa < pb)


def _local_file_ver(name: str) -> str:
    try:
        with open(os.path.join(HERE, name), encoding="utf-8") as f:
            return _read_ver_from_src(f.read(8192))
    except Exception:
        return "0"


def _http_get(url: str, timeout: float = 30.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _remote_app_ver(log=print) -> str:
    """v1.14.33: نسخهٔ_remote را از فایل VERSION (چند بایت) می‌خواند —
    قبلاً برای چکِ نسخه، خودِ manga.py (~نیم مگابایت) دانلود می‌شد که روی
    اینترنتِ کند عملاً «آپدیت گیر کردن» بود."""
    try:
        txt = _http_get(GITHUB_RAW_BASE + "VERSION?cb="
                        + str(int(time.time() // 300)), timeout=12).decode("utf-8", "ignore")
        m = re.search(r"versionName\s*=\s*([0-9][0-9.]*)", txt or "")
        if m:
            return m.group(1).strip()
    except Exception as e:
        log(f"[!] چک نسخهٔ remote ناموفق: {str(e)[:80]}")
    return ""


def _local_app_ver() -> str:
    """نسخهٔ محلی: اول فایل VERSION کنار برنامه، بعد APP_VER در manga_app.py."""
    try:
        vp = os.path.join(HERE, "VERSION")
        if os.path.isfile(vp):
            with open(vp, encoding="utf-8") as f:
                m = re.search(r"versionName\s*=\s*([0-9][0-9.]*)", f.read(2048) or "")
                if m:
                    return m.group(1).strip()
    except Exception:
        pass
    return _local_file_ver("manga_app.py")


def _stage_update_file(name: str, log=print) -> dict:
    """یک فایل آپدیت را می‌گیرد و کنار بقیه stage می‌کند (برای apply)."""
    info = {"local": "", "remote": "", "newer": False}
    try:
        src = _http_get(GITHUB_RAW_BASE + name + "?cb="
                        + str(int(time.time() // 300)), timeout=60).decode("utf-8", "ignore")
        info["remote"] = _read_ver_from_src(src[:8192])
        info["local"] = _local_file_ver(name)
        os.makedirs(UPD_DIR, exist_ok=True)
        with open(os.path.join(UPD_DIR, name + ".staged"), "w", encoding="utf-8") as f:
            f.write(src)
        info["newer"] = True
    except Exception as e:
        info["error"] = str(e)[:120]
    return info


def check_updates(force: bool = False, log=print) -> dict:
    try:
        last = float(load_config().get("last_update_check", 0) or 0)
    except Exception:
        last = 0.0
    now = time.time()
    if not force and last and (now - last) < UPDATE_INTERVAL_S:
        return {"checked": False}

    rep: dict = {"checked": True, "update_available": False, "files": {}}
    remote_ver = _remote_app_ver(log=log)
    local_ver = _local_app_ver()
    newer_global = bool(remote_ver and _cmp_ver(remote_ver, local_ver) > 0)

    if newer_global:
        # v1.14.33: فقط وقتی نسخهٔ جدید واقعاً هست، فایل‌ها دانلود می‌شوند —
        # و به‌صورت موازی (۴ فایل همزمان) تا آپدیت خیلی سریع‌تر بیاید.
        log(f"🔄 آپدیت جدید پیدا شد: v{local_ver} → v{remote_ver} — در حال گرفتن…")
        results: dict = {}
        threads = []

        def _worker(n):
            results[n] = _stage_update_file(n, log=log)

        for name in UPDATE_FILES:
            th = threading.Thread(target=_worker, args=(name,), daemon=True)
            th.start()
            threads.append(th)
        for th in threads:
            th.join(timeout=180)
        for name in UPDATE_FILES:
            info = results.get(name) or {"local": "", "remote": remote_ver,
                                         "newer": False, "error": "timeout"}
            rep["files"][name] = info
            if info.get("newer"):
                rep["update_available"] = True
    else:
        for name in UPDATE_FILES:
            rep["files"][name] = {"local": _local_file_ver(name),
                                  "remote": local_ver, "newer": False}
        log("✔ برنامه به‌روز است.")
    try:
        cfg = load_config()
        cfg["last_update_check"] = now
        save_config(cfg)
    except Exception:
        pass
    return rep


def apply_updates(report: Optional[dict] = None, log=print) -> list:

    installed = []
    rep = report if (report and report.get("checked")) else check_updates(force=True, log=log)
    gver = _local_app_ver()
    for name, info in (rep.get("files") or {}).items():
        staged = os.path.join(UPD_DIR, name + ".staged")
        if not (info.get("newer") and os.path.isfile(staged)):
            continue
        try:
            dst = os.path.join(HERE, name)
            bak = dst + ".bak"
            if os.path.isfile(dst):
                shutil.copyfile(dst, bak)
            os.replace(staged, dst)
            v = info.get("remote") or gver
            installed.append(f"{name} → v{v}")
            log(f"✔ نصب شد: {name} v{v} (بکاپ: {os.path.basename(bak)})")
        except Exception as e:
            log(f"✖ نصب {name} ناموفق: {e}")
    if installed:
        log("🔁 برای فعال‌شدن کامل، برنامه را ببندید و دوباره باز کنید.")
    return installed


def auto_update_on_start(log=print) -> None:

    def _worker():
        while True:
            try:
                rep = check_updates(force=False, log=log)
                if rep.get("update_available"):
                    apply_updates(rep, log=log)
            except Exception:
                pass
            time.sleep(UPDATE_INTERVAL_S)

    try:
        th = threading.Thread(target=_worker, daemon=True)
        th.start()
    except Exception:
        pass

_ft_checked: dict = {}

def _font_persian_ok(path: str) -> bool:
    if path in _ft_checked:
        return _ft_checked[path]
    ok = True
    try:
        from fontTools.ttLib import TTFont
        import arabic_reshaper
        from bidi.algorithm import get_display
    except ImportError:
        try:
            for _pkg in ("fonttools", "arabic-reshaper", "python-bidi"):
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", _pkg])
            from fontTools.ttLib import TTFont
            import arabic_reshaper
            from bidi.algorithm import get_display
        except Exception:
            _ft_checked[path] = True
            return True
    try:
        shaped = get_display(arabic_reshaper.reshape("من قرفتم باهاش حرف بزنم ژاله پک‌بک"))
        cps = {ord(c) for c in shaped
               if ord(c) > 0x2000 and not 0x200C <= ord(c) <= 0x200F}
        cmap = TTFont(path).getBestCmap()
        ok = all(c in cmap for c in cps)
    except Exception:
        ok = True
    _ft_checked[path] = ok
    return ok


def font_args() -> list:
    
    args = []
    main = find_font()
    if main:
        args += ["--font", main]
    cli_font = {"free_text": "free"}
    for slot, fname, _desc, _urls in FONT_BUNDLES:
        p = os.path.join(FONT_DIR, fname)
        if os.path.isfile(p) and _font_persian_ok(p):
            flag = cli_font.get(slot, slot.replace("_", "-"))
            args += [f"--font-{flag}", p]
    return args


def human_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def system_info() -> str:
    import platform
    lines = [
        f"پایتون: {platform.python_version()} — {platform.system()} {platform.release()}",
        f"هستهٔ CPU: {os.cpu_count()}",
    ]
    try:
        import onnxruntime as ort
        lines.append("ONNX Runtime: " + ort.__version__ + " | " +
                     ", ".join(ort.get_available_providers()))
    except Exception:
        lines.append("ONNX Runtime: نصب نیست")
    try:
        import torch  
        lines.append("GPU (CUDA): ✅")
    except Exception:
        lines.append("GPU (CUDA): —")
    if os.path.isdir(MODELS_DIR):
        lines.append("مدل‌های کش‌شده:")
        for f in sorted(os.listdir(MODELS_DIR)):
            p = os.path.join(MODELS_DIR, f)
            if os.path.isfile(p):
                lines.append(f"  • {f} — {human_size(os.path.getsize(p))}")
    else:
        lines.append("مدل‌های کش‌شده: — (بار اول دانلود می‌شوند)")
    fonts = os.listdir(FONT_DIR) if os.path.isdir(FONT_DIR) else []
    lines.append(f"فونت‌ها: {len(fonts)} فایل در fonts/")
    try:
        du = shutil.disk_usage(HERE)
        lines.append(f"فضای آزاد: {human_size(du.free)}")
    except Exception:
        pass
    return "\n".join(lines)



def smart_output_base(input_path: str) -> str:
    
    raw = (input_path or "").strip()
    if not raw:
        return "chapter_fa"
    
    # چند لینک (با اینتر/کاما/تب): برای نامِ خروجی فقط اولی ملاک است
    raw = re.split(r"[,\n\r\t]+", raw)[0].strip()
    is_url = raw.lower().startswith(("http://", "https://"))
    if is_url:
        from urllib.parse import urlparse, unquote
        path_u = unquote(urlparse(raw).path).strip("/")
        parts = [p for p in path_u.split("/") if p and p != "*"]
        base = "chapter"
        if parts:
            
            while parts and (
                parts[-1].startswith("*")
                or re.search(r"(?i)\.(jpe?g|png|webp|gif|bmp)(\?.*)?$", parts[-1])
                or re.fullmatch(r"\d+", parts[-1] or "")
            ):
                
                if re.fullmatch(r"\d+", parts[-1] or ""):
                    parts.pop()
                    break
                parts.pop()
                if not parts:
                    break
            slug = parts[-1] if parts else "chapter"
            
            m = re.search(
                r"(?i)(?:^|-)(chapter[-_]?\d+|ch[-_]?\d+|ep[-_]?\d+)$",
                slug,
            )
            if m:
                
                series = parts[-2] if len(parts) >= 2 else ""
                ch = m.group(1)
                base = f"{series}-{ch}" if series else ch
            elif re.search(r"(?i)chapter[-_]?\d+", slug):
                base = slug
            elif any(re.search(r"(?i)^chapter[-_]?\d+$", p) for p in parts):
                for p in parts:
                    if re.search(r"(?i)^chapter[-_]?\d+$", p):
                        series = parts[parts.index(p) - 1] if parts.index(p) > 0 else ""
                        base = f"{series}-{p}" if series else p
                        break
            elif "chapter" in [p.lower() for p in parts]:
                low_parts = [p.lower() for p in parts]
                try:
                    idx = low_parts.index("chapter")
                    name = parts[idx - 1] if idx > 0 else "chapter"
                    num = parts[idx + 1] if idx + 1 < len(parts) else ""
                    num = re.sub(r"[^\w\-]", "", num.split("?")[0])
                    base = f"{name}-{num}" if num else name
                except ValueError:
                    base = slug
            else:
                base = slug if slug else "chapter"
        base = re.sub(r"\*+", "", base)
        base = re.sub(r"(?i)\.(jpe?g|png|webp|gif|bmp)$", "", base)
        base = re.sub(r"[^\w\-.]+", "-", base)
        base = re.sub(r"-{2,}", "-", base).strip("-._") or "chapter"
    else:
        path_only = raw.rstrip("/\\")
        base = os.path.splitext(os.path.basename(path_only))[0] or "output"
        base = re.sub(r"\*+", "", base)
        base = re.sub(r"[^\w\-.]+", "-", base).strip("-._") or "output"
    if not base.lower().endswith("_fa"):
        base = base + "_fa"
    return base


def append_history(entry: dict) -> None:
    try:
        with open(HIST_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def history_text() -> str:
    if not os.path.isfile(HIST_PATH):
        return "هنوز اجرایی ثبت نشده."
    rows = []
    try:
        with open(HIST_PATH, encoding="utf-8") as f:
            for line in f:
                e = json.loads(line)
                rows.append(f"{e.get('time','')}  |  "
                            f"{os.path.basename(str(e.get('input','')))[:36]:36}  |  "
                            f"{e.get('status','')}  |  {e.get('duration','')}")
    except Exception:
        return "تاریخچه خوانده نشد."
    return "\n".join(reversed(rows[-60:])) or "هنوز اجرایی ثبت نشده."


def open_path(path: str):
    try:
        if os.name == "nt":
            os.startfile(path)  
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


def has_display() -> bool:
    if os.name == "nt" or sys.platform == "darwin":
        return True
    return bool(os.environ.get("DISPLAY"))


HELP_TEXT = f"""راهنما — {APP_NAME} v{APP_VER}

▶ اجرا (خودکار: دسکتاپ → پنجرهٔ برنامه، Colab/Codespace → وب)
  ویندوز:            دابل‌کلیک Manga.bat
  لینوکس / مک:       ./manga.sh
  مستقیم:            python manga_app.py

▶ اجبار حالت
  python manga_app.py --web       (Colab: لینک عمومی gradio.live چاپ می‌شود)
  python manga_app.py --desktop

▶ Colab — دو فایل لازم است کنار هم باشند:
  manga.py      (فایل مترجم — همان فایل اصلی)
  manga_app.py  (برنامه)
  سپس:  !python manga_app.py
  ⚠ manga_app.py را با نام manga.py ذخیره نکنید — خطای «فایل مترجم نیست» می‌گیرید.

▶ GitHub Codespaces / SSH
  لینک عمومی خودکار چاپ می‌شود (gradio.live) — نیازی به Port Forwarding نیست.
  ⚠ سرور وب به نشست ترمینال چسبیده است: با بستن ترمینال kill می‌شود.
  برای زنده‌ماندن: tmux new -s manga 'python3 manga_app.py --web'
  (detach: Ctrl+B بعد D | بازگشت: tmux attach -t manga)

▶ فونت‌ها
  بار اول خودکار در fonts/ دانلود می‌شوند (کودک، افسانه، کروش، دست‌نویس،
  مروارید، سیستم، نامه، راوی …). برای تغییر، فقط فایل .ttf را با همان نام
  در fonts/ جایگزین کنید و برنامه را دوباره باز کنید.

▶ CLI
  python manga_app.py -- -i input -o out.pdf --font fonts/Vazirmatn-Bold.ttf --api-key KEY --clean-method lama-manga

▶ نکات
  • کلید از aistudio.google.com / platform.openai.com / openrouter.ai — چند کلید = چرخش خودکار
  • مدل‌ها بار اول دانلود و در ~/.cache کش می‌شوند
  • تنظیمات در workspace/config.json ذخیره می‌شود
"""



def manga_py_ok() -> bool:
    
    try:
        with open(MANGA_PY, encoding="utf-8") as f:
            head = f.read()
    except Exception:
        return False
    return ("def run_desktop" not in head) and ("def run_web" not in head)


MANGA_MIXED_MSG = (
    "❌ فایل manga.py کنار برنامه، فایل «مترجم» نیست — کد خود برنامه داخلش ذخیره شده\\n"
    "(احتمالاً manga_app.py را با نام manga.py ذخیره کرده‌اید).\\n"
    "فایل manga.py اصلی (مترجم) را کنار manga_app.py بگذارید و دوباره اجرا کنید."
)



def run_cli_interactive():
    
    print(f"\n══════════ {APP_NAME} v{APP_VER} — CLI ══════════\n")
    if not manga_py_ok():
        print(MANGA_MIXED_MSG)
        return

    cfg = load_config()
    src = input("📄 مسیر فایل/پوشه یا URL ورودی: ").strip().strip('"')
    if not src:
        print("❌ ورودی خالی است.")
        return
    if not os.path.exists(src) and not src.lower().startswith(("http://", "https://")):
        print(f"❌ مسیر پیدا نشد: {src}")
        return

    print("\nقالب خروجی:  1) PDF   2) ZIP   3) HTML   4) پوشهٔ تصاویر   5) PSD")
    f = input("انتخاب [1-5] (پیش‌فرض 1): ").strip() or "1"
    ext = {"1": ".pdf", "2": ".zip", "3": ".html", "4": "", "5": ".psd"}.get(f, ".pdf")

    print("\nارائه‌دهندهٔ AI را انتخاب کنید:")
    # v1.14.217 — فقط Gemini و custom (دستورِ سازنده: «همه مدلای ک تو کد
    # الکی اضافه شده حذف کن بجز Gemini و گزینه کاستوم بمونه»)
    prov_menu = [
        ("gemini", "Google Gemini - رایگان با سهمیه"),
        ("custom", "سرویس دلخواه — ۴ فرمت: OpenAI / Responses / Anthropic / Google (دامنه + توکن + مدل)"),
    ]
    for i, (pid, desc) in enumerate(prov_menu, 1):
        print(f"  {i}) {pid:12} ({desc})")
    pc = input("انتخاب [پیش‌فرض 1]: ").strip() or "1"
    try:
        provider = prov_menu[int(pc) - 1][0]
    except (ValueError, IndexError):
        provider = "gemini"
    keys = input("کلید API (خالی = env/config): ").strip() \
        or cfg.get("api_keys") or default_keys()
    model = input(f"مدل [{cfg.get('model', '') or 'پیش‌فرض'}]: ").strip() \
        or cfg.get("model", "")
    api_base_v = ""
    if provider == "custom":
        print("── سرویس دلخواه (۴ فرمت: OpenAI / Responses / Anthropic / Google) ──")
        api_base_v = str(cfg.get("api_base", "") or "")
        for _try in range(3):
            hint = f" [Enter = همان {api_base_v}]" if api_base_v else " [خالی = انصراف]"
            raw = _cli_ask("دامنهٔ API (مثال: https://api.example.com/v1)" + hint + ": ")
            if not raw and api_base_v:
                break
            if not raw:
                print("  ✗ provider «custom» بدون دامنهٔ API کار نمی‌کند — دوباره وارد کن.")
                continue
            _ab = normalize_api_base(raw)
            if not _ab:
                print("  ✗ آدرس معتبر نیست — مثل https://api.example.com/v1 بنویس "
                      "(https:// خودکار اضافه می‌شود).")
                continue
            api_base_v = _ab
            break
        if not api_base_v:
            print("❌ انصراف — دامنهٔ API داده نشد. provider دیگری انتخاب کن یا دوباره اجرا کن.")
            return
        if not model:
            for _try in range(3):
                model = _cli_ask("نام مدل (مثال: gpt-4o-mini) [اجباری]: ")
                if model:
                    break
                print("  ✗ مدل نمی‌تواند خالی باشد — مثال: gpt-4o-mini")
            if not model:
                print("❌ انصراف — نام مدل داده نشد.")
                return
        print(f"  ✔ دامنه: {api_base_v} | مدل: {model}")

    font_v = cfg.get("font") or find_font()
    if not font_v or not os.path.isfile(font_v):
        print("❌ فونت فارسی پیدا نشد — fonts/ را آماده کنید.")
        return

    base = smart_output_base(src)
    out_v = os.path.join(OUT_DIR, base + ext)
    os.makedirs(OUT_DIR, exist_ok=True)

    cmd = [sys.executable, MANGA_PY, "-i", src, "-o", out_v, "--font", font_v,
           "--provider", provider,
           "--workers", str(int(cfg.get("workers", 2))),
           "--bubbles-per-request", str(int(cfg.get("bubbles", 6))),
           "--api-timeout", str(int(cfg.get("timeout", 40))),
           "--quality", str(int(cfg.get("quality", 92))),
           "--batch-workers", str(int(cfg.get("batch_workers", 3))),
           "--max-retries", str(int(cfg.get("max_retries", 8))),
           "--request-delay", str(float(cfg.get("request_delay", 0))),
           "--temperature", str(float(cfg.get("temperature", 0.6))),
           "--reading-order", str(cfg.get("reading_order", "rtl"))]
    cmd += font_args()
    klist = [k.strip() for k in (keys or "").replace(";", ",").split(",") if k.strip()]
    if klist:
        cmd += ["--api-key", ",".join(klist)]
    if model:
        cmd += ["--model", model]
    if provider == "custom" and api_base_v:
        cmd += ["--api-base", api_base_v]
    cmd += ["--clean-method", str(cfg.get("clean_method") or "lama-manga")]

    print("\n▶ " + " ".join(cmd) + "\n")
    proc = subprocess.Popen(cmd, cwd=HERE, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace", bufsize=1)
    t0 = time.time()
    for line in proc.stdout:
        print(line.rstrip())
    proc.wait()
    dur_s = f"{int((time.time()-t0)//60)}:{int((time.time()-t0)%60):02d}"
    if proc.returncode != 0:
        print(f"\n❌ خطا — کد خروج {proc.returncode}")
    else:
        print(f"\n✅ تمام شد ({dur_s}) — خروجی: {out_v}")


def run_cli(argv):
    if not argv:
        run_cli_interactive()
        return
    if not manga_py_ok():
        print(MANGA_MIXED_MSG)
        sys.exit(1)
    sys.argv = [MANGA_PY] + list(argv)
    import importlib.util
    spec = importlib.util.spec_from_file_location("manga_cli", MANGA_PY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["manga_cli"] = mod
    spec.loader.exec_module(mod)
    if hasattr(mod, "main"):
        mod.main()


def _ensure_webview() -> bool:
    """pywebview را در صورت نبود نصب می‌کند (فقط بار اول، چند MB)."""
    try:
        import webview  # noqa: F401
        return True
    except Exception:
        pass
    try:
        print("[*] نصب pywebview برای پنجرهٔ دسکتاپ (فقط بار اول)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q",
                               "pywebview"], timeout=600)
        import webview  # noqa: F401
        return True
    except Exception as e:
        print(f"[!] pywebview نصب نشد ({e}) → مرورگر")
        return False


def run_desktop():
    """v1.14.30: پنجرهٔ دسکتاپ = دقیقاً همان رابط وب.

    رابط قدیمی tkinter حذف شد؛ حالا سرور وب همان UI محبوبِ گوشی/وب را سرو
    می‌کند و پنجرهٔ نیتیو (pywebview / WebView2) همان صفحه را نشان می‌دهد —
    شکلِ پنجرهٔ ویندوز دقیقاً مثل وب. اگر webview نبود → همان آدرس در مرورگر.
    """
    import socket
    import time as _t
    import webbrowser

    port = int(os.environ.get("MANGA_APP_PORT", "7860") or 7860)
    # v1.14.33: ?desktop=1 → صفحه می‌فهمد داخل پنجرهٔ دسکتاپ است؛ تنظیمات و
    # کلیدهای API برای همیشه ذخیره می‌شوند (مثل اندروید)، نه ۳۰ دقیقه‌ایِ وب.
    url = f"http://127.0.0.1:{port}/?desktop=1"

    def _up() -> bool:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except Exception:
            return False

    proc = None
    if not _up():
        print("[*] راه‌اندازی سرور رابط وب ...")
        proc = subprocess.Popen([sys.executable, os.path.abspath(__file__), "--web"])
        for _ in range(300):  # حداکثر ~۶۰ ثانیه
            if _up():
                break
            _t.sleep(0.2)
            if proc.poll() is not None:
                break
        if not _up():
            print("[!] سرور وب بالا نیامد")
            try:
                proc.terminate()
            except Exception:
                pass
            sys.exit(1)
    print(f"[i] رابط وب آماده: {url}")

    opened_browser = False
    if not _ensure_webview():
        webbrowser.open(url)
        opened_browser = True
    else:
        try:
            import webview
            # v1.14.33: private_mode=False → localStorage مثل اندروید دائمی می‌ماند
            # (کلیدهای API بعد از بستن برنامه هم پاک نمی‌شوند).
            _store = os.path.join(WORK_DIR, "webview_profile")
            try:
                os.makedirs(_store, exist_ok=True)
            except Exception:
                _store = None
            _start_kw = {"private_mode": False}
            if _store:
                _start_kw["storage_path"] = _store
            webview.create_window(f"{APP_NAME} v{APP_VER}", url,
                                  width=1280, height=880,
                                  min_size=(980, 640),
                                  background_color="#060607")
            print("[i] پنجرهٔ دسکتاپ (همان رابط وب) باز شد — با بستن پنجره، برنامه تمام می‌شود")
            webview.start(**_start_kw)
        except Exception as e:
            print(f"[!] پنجرهٔ وب‌ویو ناموفق ({e}) → مرورگر")
            webbrowser.open(url)
            opened_browser = True

    if opened_browser:
        # تا مرورگر باز است، سرور باید بماند
        try:
            if proc is not None:
                proc.wait()
            else:
                while True:
                    _t.sleep(3600)
        except KeyboardInterrupt:
            pass
    else:
        try:
            if proc is not None:
                proc.terminate()
        except Exception:
            pass
    sys.exit(0)


WEB_CSS = """
/* v1.14.33: فونت از سرورِ خودِ برنامه می‌آید (@font-face محلی) — دیگر هیچ
   درخواستی به fonts.googleapis.com نمی‌رود. در ایران آن دامنه کند/مسدود است و
   پنجرهٔ PC ده‌ها ثانیه معطلش می‌ماند («اپ کند میاد بالا»). */
@font-face{font-family:'Vazirmatn';font-style:normal;font-weight:400;
  src:url('__FONTPFX__/Vazirmatn-Regular.ttf') format('truetype');
  font-display:swap}
@font-face{font-family:'Vazirmatn';font-style:normal;font-weight:700;
  src:url('__FONTPFX__/Vazirmatn-Bold.ttf') format('truetype');
  font-display:swap}

:root, .gradio-container {
  --ink-bg: #060607;
  --ink-surface: #0d0d10;
  --ink-surface2: #121216;
  --ink-line: #1f1f24;
  --ink-text: #e8e6e1;
  --ink-dim: #97948c;
  --ink-red: #ff4a3d;
  --ink-red-deep: #c9271c;
}
body, .gradio-container, footer, .gradio-container .prose {
  background: var(--ink-bg) !important; color: var(--ink-text) !important;
  font-family: 'Vazirmatn', 'Segoe UI', Tahoma, system-ui, sans-serif !important;
}
.gradio-container {
  background:
    radial-gradient(ellipse 120% 70% at 50% -10%, rgba(255,74,61,.06), transparent 60%),
    radial-gradient(rgba(232,230,225,.028) 1px, transparent 1.4px) 0 0 / 14px 14px,
    #060607 !important;
}
.gradio-container { max-width: 880px !important; margin: 0 auto !important; }


.nav {
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 10px 16px;
  background: linear-gradient(180deg, #101014, #0a0a0c);
  border: 1px solid var(--ink-line);
  border-radius: 18px; padding: 20px 24px; margin: 6px 0 18px 0;
  box-shadow: 0 18px 40px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.05);
  position: relative; overflow: hidden;
  animation: rise .55s cubic-bezier(.2,.7,.2,1) both;
}
.nav::after {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background: radial-gradient(rgba(232,230,225,.03) 1px, transparent 1.4px) 0 0 / 10px 10px;
}
.nav-left { display: flex; align-items: center; gap: 14px; flex: 1 1 auto; min-width: 230px; }
.stamp {
  width: 52px; height: 52px; flex: none;
  background: linear-gradient(145deg, var(--ink-red), var(--ink-red-deep));
  border-radius: 10px; transform: rotate(-4deg);
  display: flex; align-items: center; justify-content: center;
  font-size: 1.7rem; font-weight: 900; color: #fff;
  box-shadow: 0 6px 18px rgba(224,53,42,.4), inset 0 0 0 2px rgba(255,255,255,.22);
  font-family: serif;
}
.nav-brand { color: var(--ink-text); font-size: 1.3rem; font-weight: 700; line-height: 1.25; white-space: nowrap; }
.nav-brand b { color: var(--ink-red); font-weight: 900; }
.nav-sub { display: block; color: var(--ink-dim); font-size: .74rem; font-weight: 400; letter-spacing: .04em; }
.nav-chips { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.chip {
  font-family: ui-monospace, 'Cascadia Mono', Consolas, monospace; font-size: .7rem;
  background: var(--ink-surface2); border: 1px solid var(--ink-line);
  color: var(--ink-dim); padding: 4px 11px; border-radius: 999px;
  display: inline-flex; align-items: center; gap: 6px;
}
.chip::before { content: ''; width: 5px; height: 5px; border-radius: 50%;
  background: var(--ink-red); box-shadow: 0 0 6px var(--ink-red); }

.stepcard {
  background: linear-gradient(180deg, var(--ink-surface), #0a0a0c) !important;
  border: 1px solid var(--ink-line) !important;
  border-radius: 18px !important; padding: 20px 22px 18px; margin-bottom: 16px;
  box-shadow: 0 10px 28px rgba(0,0,0,.4);
  position: relative;
  animation: rise .55s cubic-bezier(.2,.7,.2,1) both;
}
.stepcard:nth-of-type(1) { animation-delay: .06s; }
.stepcard:nth-of-type(2) { animation-delay: .14s; }
.stepcard:nth-of-type(3) { animation-delay: .22s; }
.stepcard:nth-of-type(4) { animation-delay: .3s; }
@keyframes rise {
  from { opacity: 0; transform: translateY(14px); }
  to   { opacity: 1; transform: none; }
}
.steptitle {
  display: flex; align-items: center; gap: 12px;
  color: var(--ink-text); font-weight: 700; font-size: 1.08rem; margin-bottom: 14px;
  padding-bottom: 10px; border-bottom: 1px solid var(--ink-line);
}
.stepnum {
  background: linear-gradient(145deg, var(--ink-red), var(--ink-red-deep));
  color: #fff; width: 30px; height: 30px; border-radius: 8px;
  transform: rotate(-3deg);
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 1rem; font-weight: 900; flex: none;
  box-shadow: 0 4px 12px rgba(224,53,42,.35), inset 0 0 0 1.5px rgba(255,255,255,.2);
}
.hint { color: var(--ink-dim) !important; font-size: .83rem; margin-top: 8px; }
/* v1.14.224 — دستورِ سازنده: «تو وب لینوکس پی سی لینک مدل بزرگ باشه صفحه
   بزرگ تر میشه اینو درست کن بعد قسمت میگن لینک بلند باشه کش میده» — لینکِ
   بلند (https://api.cloudflare.com/client/v4/accounts/…/chat/completions)
   و اسمِ بلندِ مدل در خطِ مشخصاتِ زیرِ منو شکسته میشوند و دیگر صفحه را
   پهن/بزرگ نمیکند — overflow-wrap:anywhere به همهٔ فرزندان میرسد و
   min-content را هم کوچک میکند تا ستون بتواند جمع شود */
.hint, .hint *, #manga_cm_info, #manga_cm_info * {
  overflow-wrap: anywhere !important;
  word-break: break-word !important;
  max-width: 100% !important;
}
#manga_cm_info code, .hint code { white-space: normal !important; }

/* v1.14.221 — ضربدرِ ✖ِ حذف، چسبیده به خودِ منویِ انتخابِ AI: مدلِ
   خودت را در منو انتخاب کن، ✖ِ کنارِ منو میآید و با یک کلیک از لیست و
   منو پاک میشود (دستورِ سازنده: «هرمدلی ک خودم ساختم انتخاب کنم کنارش
   ضربدر بیاد نه پایینش کلی ضربدر نشون بده»)
   v1.14.222 — دستورِ سازنده: «دکمه ضربدرش بزرگه هم اندازه دکمش کن» →
   ✖ دیگر دکمهٔ درشتِ ۴۴px نیست؛ دقیقاً هماندازهٔ خودِ کنترلِ منو (۳۰px)
   و همترازِ آن ساخته میشود
   v1.14.223 — دستورِ سازنده: «دکمه ضربدرش به بالا کش اومده به اندازهٔ
   دکمه باشه» — ریشه پیدا شد: خودِ ✖ ۳۰×۳۰ است ولی gradio دورِ هر ردیف
   یک قابِ .styler با پسزمینهٔ خاکستریِ آبی (var(--block-border-color))
   میکشد؛ فاصلهٔ خالیِ کنارِ منو همان پسزمینه میشود و شبیهِ اینکه ✖ به
   بالا کشیده شده. قاب شفاف میشود تا فقط خودِ دکمهٔ ✖ دیده شود (وبِ
   PC/لینوکس/گوشی همه همین مرورگر است). */
div.styler{background:transparent !important;border:none !important;
  box-shadow:none !important}
#manga_cm_del_btn{max-width:30px !important;min-width:30px !important;
  width:30px !important;height:30px !important;min-height:30px !important;
  max-height:30px !important;
  flex:none !important;align-self:flex-end !important;
  background:transparent !important;border:1px solid rgba(255,90,90,.4) !important;
  border-radius:999px !important;color:#ff7b7b !important;font-size:.8rem !important;
  line-height:1 !important;padding:0 !important;margin:0 0 16px 0 !important;
  transition:all .15s ease}
#manga_cm_del_btn:hover{background:rgba(255,70,70,.18) !important;color:#ff4d4d !important}
#manga_cm_del_btn:active{transform:scale(.94)}
/* v1.14.223 — دستورِ سازنده: «کلید ک وارد میکنن بشه هاید کرد پیشفرض
   هاید باشه زدن روش دیده بشه» — فیلدِ کلید از سمتِ سرور type="password"
   است (پیشفرضِ مخفی) و دکمهٔ 👁 داخلِ فیلد آن را نشان/مخفی میکند */
#manga_api_keys .wrap, #manga_api_keys .input-container{position:relative !important}
#manga_api_keys input{padding-inline-start:44px !important}
.manga-eye{position:absolute !important;top:50% !important;
  inset-inline-start:6px !important;transform:translateY(-50%) !important;
  width:32px !important;min-width:32px !important;max-width:32px !important;
  height:32px !important;min-height:32px !important;max-height:32px !important;
  border-radius:9px !important;background:rgba(255,255,255,.04) !important;
  border:1px solid rgba(255,255,255,.14) !important;color:#b9b6ad !important;
  font-size:1rem !important;line-height:1 !important;padding:0 !important;
  cursor:pointer !important;z-index:6;transition:all .15s ease;
  box-shadow:none !important;margin:0 !important;flex:none !important}
.manga-eye.on{color:#ffd28a !important;border-color:rgba(255,210,138,.45) !important}
.manga-eye:active{transform:translateY(-50%) scale(.93)}
/* v1.14.219 — کانالهایِ پنهانِ مرورگر↔سرور: gradio 6 کامپوننتهایِ
   visible=False را اصلاً در DOM نمیگذارد و همهٔ JSهایی که با setVal
   به سرور خبر میدهند (افزودنِ مدل، ضربدرِ ✖، بازیابیِ localStorage،
   sid) کور میشوند؛ پس این کانالها visible=True ولی با CSS مخفی
   میشوند تا در DOM بمانند — اندروید/PC/لینوکس/وب همه همان مرورگرند */
.manga-hide-channel{display:none !important;visibility:hidden !important;
  height:0 !important;min-height:0 !important;margin:0 !important;
  padding:0 !important;border:0 !important;overflow:hidden !important}

.livehint { color: var(--ink-dim) !important; font-size: .8rem; margin-top: 8px; text-align: center; }

label, span, .prose, p, li { color: var(--ink-dim) !important; }
span:not(.stepnum):not(.chip) {
  background: transparent !important;
  background-image: none !important;
  box-shadow: none !important;
}
label span, label > span:first-child {
  background: transparent !important;
  background-image: none !important;
  color: var(--ink-dim) !important;
  box-shadow: none !important;
  font-size: .85rem; font-weight: 500;
}
input[type=text], input[type=password], textarea, select {
  background: #08080a !important; color: var(--ink-text) !important;
  border-color: var(--ink-line) !important;
}
.block, .form, .gr-box, .gr-panel, .gr-group, .gr-form,
.gradio-group, .wrap.full, .container > .wrap {
  background: var(--ink-surface) !important; border-color: var(--ink-line) !important;
}
.gr-box input, .gr-box textarea, .gr-input, .gr-textbox {
  background: #08080a !important; color: var(--ink-text) !important;
}
.options, .options ul, ul.options, .dropdown-menu, .wrap .options {
  background: #101014 !important; border-color: var(--ink-line) !important;
}
.options li, .options li:hover { background: #101014 !important; color: var(--ink-text) !important; }
.options li.selected, .options li:hover { background: #1a1114 !important; }
accordion, .accordion, details {
  background: var(--ink-surface) !important; border-color: var(--ink-line) !important; color: var(--ink-dim) !important;
}
summary { color: var(--ink-dim) !important; }
input[type=range], input[type=radio], input[type=checkbox] { accent-color: var(--ink-red) !important; }
input[type=radio], input[type=checkbox] {
  appearance: auto !important;
  background-image: none !important;
  background-color: transparent !important;
  border: none !important;
  width: 16px; height: 16px; margin: 0 2px;
  cursor: pointer;
}
input[type=range] {
  appearance: none !important;
  -webkit-appearance: none !important;
  height: 6px !important; border-radius: 4px !important;
  background: linear-gradient(to right, var(--ink-red) var(--range_progress, 50%),
              #1f1f24 var(--range_progress, 50%)) !important;
  border: none !important;
  cursor: pointer;
}
input[type=range]::-webkit-slider-runnable-track {
  background: linear-gradient(to right, var(--ink-red) var(--range_progress, 50%),
              #1f1f24 var(--range_progress, 50%)) !important;
  height: 6px !important; border-radius: 4px !important; border: none !important;
}
input[type=range]::-moz-range-track {
  background: linear-gradient(to right, var(--ink-red) var(--range_progress, 50%),
              #1f1f24 var(--range_progress, 50%)) !important;
  height: 6px !important; border-radius: 4px !important; border: none !important;
}
input[type=range]::-webkit-slider-thumb {
  -webkit-appearance: none !important; appearance: none !important;
  width: 17px; height: 17px; border-radius: 50%;
  background: var(--ink-red); border: 2.5px solid #fff;
  box-shadow: 0 2px 10px rgba(255, 74, 61, .55);
}
input[type=number], .gr-box input[type=number] {
  background: #08080a !important; color: var(--ink-text) !important;
  border-color: var(--ink-line) !important;
}
.gr-checkbox, .gr-radio, .wrap label { background: transparent !important; }

button.primary, .lg.primary, #runbtn {
  background: linear-gradient(160deg, var(--ink-red), var(--ink-red-deep)) !important;
  color: #fff !important; border: none !important;
  font-weight: 700 !important; letter-spacing: .02em;
  box-shadow: 0 8px 22px rgba(224,53,42,.35), inset 0 1px 0 rgba(255,255,255,.25) !important;
  transition: transform .12s ease, box-shadow .12s ease, filter .12s ease;
}
button.primary:hover, #runbtn:hover { filter: brightness(1.08); transform: translateY(-1px); }
button.primary:active, #runbtn:active { transform: translateY(1px) scale(.99); }
button.secondary, .lg.secondary, button.gr-button {
  background: var(--ink-surface2) !important; color: var(--ink-text) !important;
  border: 1px solid var(--ink-line) !important;
}
button.gr-button:hover { background: #17171c !important; border-color: #2c2c33 !important; }
#runbtn {
  font-size: 1.12rem !important; padding: 15px 0 !important;
  border-radius: 14px !important; margin: 8px 0 12px 0; position: relative; overflow: hidden;
}
#runbtn::after {
  content: ''; position: absolute; inset: 0;
  background: radial-gradient(rgba(255,255,255,.14) 1px, transparent 1.4px) 0 0 / 9px 9px;
  opacity: 0; transition: opacity .18s ease; pointer-events: none;
}
#runbtn:hover::after { opacity: 1; }

textarea { scrollbar-color: var(--ink-line) #08080a !important; }
.compact-upload .empty, .compact-upload button {
  min-height: 48px !important; height: auto !important;
  padding: 6px 8px !important; font-size: .85rem !important;
  background: #08080a !important; color: var(--ink-dim) !important;
  border-color: var(--ink-line) !important;
}
.compact-upload .wrap.center, .compact-upload .wrap {
  padding: 6px 0 !important; min-height: 48px !important;
  background: transparent !important;
}
.compact-upload .empty .icon-wrap { display: none !important; }
.compact-upload label { position: static !important; margin: 4px 0 !important; }


#manga_ocr_lang .wrap { padding: 0 !important; background: transparent !important; }
#manga_ocr_lang svg { display: none !important; }

footer { display: none !important; }

#manga_live_log,
#manga_live_log textarea,
#manga_live_log.generating,
.generating #manga_live_log textarea {
  opacity: 1 !important;
  filter: none !important;
  transition: none !important;
  animation: none !important;
  color: #e8e6e1 !important;
  background: #08080a !important;
  min-height: 220px !important;
  display: block !important;
  visibility: visible !important;
}
#manga_live_log textarea {
  -webkit-text-fill-color: #e8e6e1 !important;
}

.credit {
  display: flex; gap: 12px; justify-content: center; align-items: center;
  padding: 6px 0 22px; flex-wrap: wrap;
}
.credit img.gh-avatar {
  width: 22px; height: 22px; border-radius: 50%;
  object-fit: cover; flex: none;
  border: 1.5px solid var(--ink-line);
}
.credit a {
  display: inline-flex; align-items: center; gap: 7px;
  color: var(--ink-dim) !important; text-decoration: none !important;
  font-size: 13px; border: 1px solid var(--ink-line);
  padding: 7px 16px; border-radius: 999px; background: #0a0a0d;
  transition: border-color .2s, color .2s, transform .2s;
}
.credit a:hover { color: var(--ink-red) !important; border-color: var(--ink-red);
                  transform: translateY(-1px); }
.credit svg { width: 15px; height: 15px; fill: currentColor; flex: none; }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: #060607; }
::-webkit-scrollbar-thumb { background: #232329; border-radius: 6px; }
::-webkit-scrollbar-thumb:hover { background: var(--ink-red-deep); }
::selection { background: var(--ink-red); color: #fff; }
@media (prefers-reduced-motion: reduce) {
  .nav, .stepcard { animation: none; }
}

/* ---- دکمهٔ سیاه «تست کلیدها / لینک» — یک دکمه، هر سه پلتفرم ---- */
#manga_test_key {
  background: linear-gradient(160deg, #16161a, #050506) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 14px !important;
  font-weight: 800 !important;
  font-size: 1rem !important;
  padding: 14px 18px !important;
  min-height: 52px !important;
  box-shadow: 0 8px 22px rgba(0,0,0,.45), inset 0 0 0 1.5px rgba(255,255,255,.16) !important;
  transition: filter .18s ease, transform .18s ease !important;
}
#manga_test_key:hover { filter: brightness(1.35); transform: translateY(-1px); }
#manga_test_key:active { transform: translateY(0); filter: brightness(.9); }
#manga_test_key span, #manga_test_key div { color: #fff !important; }

/* ---- جعبهٔ نتیجهٔ تست هر کلید ---- */
#manga_test_key_out textarea {
  background: #08080a !important;
  color: #d9d9e0 !important;
  font-family: 'IBM Plex Mono', monospace !important;
  font-size: .88rem !important;
  border: 1px solid rgba(255,255,255,.14) !important;
  border-radius: 12px !important;
  direction: rtl !important;
}

/* ---- چیپ وضعیت زندهٔ ترجمه (فاز/زمان/صفحه) ---- */
#manga_status_chip {
  display: none; align-items: center; gap: 9px; flex-wrap: wrap;
  margin: 2px 0 10px; padding: 9px 16px;
  background: linear-gradient(180deg, #101014, #0a0a0c);
  border: 1px solid var(--ink-line); border-radius: 999px;
  width: fit-content; max-width: 100%;
  color: var(--ink-text); font-size: .85rem; line-height: 1;
  box-shadow: 0 4px 14px rgba(0,0,0,.4);
  animation: rise .35s ease both;
}
#manga_status_chip b { color: var(--ink-text); font-weight: 700; }
#manga_status_chip span { background: transparent !important; box-shadow: none !important; }
.chip-sep { color: var(--ink-dim) !important; opacity: .55; }
.chip-dot {
  width: 9px; height: 9px; border-radius: 50%; flex: none;
}
.chip-dot.run  { background: #ffb02e; box-shadow: 0 0 8px #ffb02e; animation: chipPulse 1.15s ease-in-out infinite; }
.chip-dot.ok   { background: #38c98a; box-shadow: 0 0 8px #38c98a; }
.chip-dot.err  { background: var(--ink-red); box-shadow: 0 0 8px var(--ink-red); }
.chip-dot.idle { background: var(--ink-dim); }
@keyframes chipPulse { 50% { opacity: .3; } }

/* ---- نوار پیشرفت زیر لاگ (v1.14.236 — مثل اپ اندروید: فاز + صفحه + درصد) ---- */
#manga_prog_row .mprog {
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  margin: 10px 0 2px; padding: 11px 16px;
  background: linear-gradient(180deg, #101014, #0a0a0c);
  border: 1px solid var(--ink-line); border-radius: 14px;
  box-shadow: 0 4px 14px rgba(0,0,0,.4);
  animation: rise .35s ease both;
}
#manga_prog_row .mprog-track {
  flex: 1 1 170px; height: 10px; border-radius: 999px;
  background: #17171b; overflow: hidden; direction: ltr;
}
#manga_prog_row .mprog-fill {
  height: 100%; border-radius: 999px; min-width: 0;
  background: linear-gradient(90deg, var(--ink-red), #ff8a5e);
  transition: width .6s ease;
}
#manga_prog_row .mprog-fill.done { background: linear-gradient(90deg, #2e7d4f, #38c98a); }
#manga_prog_row .mprog-fill.err  { background: linear-gradient(90deg, #a3271e, #ff6a5e); }
#manga_prog_row .mprog-txt {
  color: var(--ink-text); font-size: .85rem; font-weight: 600;
  white-space: nowrap; line-height: 1.2;
  font-variant-numeric: tabular-nums;
}

/* ---- دکمه‌های ابزار لاگ (کپی/پاک‌کردن) ---- */
.log-tools { display: flex; gap: 8px; margin: 0 0 10px; flex-wrap: wrap; }
.log-tool-btn {
  background: #121216; color: var(--ink-dim);
  border: 1px solid var(--ink-line); border-radius: 999px;
  padding: 7px 16px; font-size: .78rem; cursor: pointer;
  font-family: inherit; min-height: 34px;
  transition: color .18s, border-color .18s, transform .18s;
}
.log-tool-btn:hover { color: var(--ink-red); border-color: var(--ink-red); transform: translateY(-1px); }
.log-tool-btn:active { transform: translateY(0); }

/* ---- موبایل: لمس راحت‌تر و چیدمان فشرده‌تر ---- */
@media (max-width: 620px) {
  .gradio-container { max-width: 100% !important; }
  .stepcard { padding: 14px 12px 12px !important; border-radius: 14px !important; }
  .nav { padding: 14px 12px !important; }
  .nav-brand { font-size: 1.12rem !important; white-space: normal !important; }
  #runbtn, #manga_test_key { min-height: 56px !important; font-size: 1.04rem !important; }
  .stepcard button { min-height: 44px !important; }
  #manga_live_log textarea { font-size: 10.5px !important; max-height: 34vh !important; }
  #manga_status_chip { font-size: .78rem; padding: 8px 13px; }
  .credit { gap: 8px; }
  .credit a { padding: 8px 13px; }
}
"""


def _detect_codespace() -> bool:
    if os.environ.get("CODESPACE_NAME"):
        return True
    if os.environ.get("MANGA_SHARE", "").strip() in ("1", "true", "yes"):
        return True
    try:
        import socket
        if socket.gethostname().startswith("codespaces-"):
            return True
    except Exception:
        pass
    try:
        with open("/etc/environment", encoding="utf-8") as f:
            if "CODESPACE_NAME=" in f.read():
                return True
    except Exception:
        pass
    return False


def _hostname_codespace_name() -> str:
    try:
        import socket
        host = socket.gethostname()
        if host.startswith("codespaces-"):
            return host
    except Exception:
        pass
    return ""


def _safe(cls, *args, **kw):
    while True:
        try:
            return cls(*args, **kw)
        except TypeError as e:
            mobj = re.search(r"unexpected keyword argument '(\w+)'", str(e))
            if not mobj or mobj.group(1) not in kw:
                raise
            kw.pop(mobj.group(1))


def _gradio_major() -> int:
    try:
        import gradio
        return int(gradio.__version__.split(".")[0])
    except Exception:
        return 0



def _dark_js_src() -> str:
    return """() => {
  document.body.classList.add('dark');
  document.documentElement.classList.add('dark');
  // ---- Wake Lock (ماندن روشن بودن صفحه هنگام استخراج/پاکسازی/ترجمه) ----
  try {
    if (window.__mangaWakeLockInstalled) return [];
    window.__mangaWakeLockInstalled = true;
    window.__mangaWL = null;
    const isRunning = () => {
      try {
        const root = document.getElementById('runbtn');
        const btn = root ? (root.querySelector('button') || root) : null;
        const t = (btn && btn.textContent) || '';
        return (t.indexOf('متوقف') >= 0 || t.indexOf('⏹') >= 0);
      } catch (e) { return false; }
    };
    const req = async () => {
      try {
        if (!window.__mangaWL && navigator.wakeLock && navigator.wakeLock.request) {
          window.__mangaWL = await navigator.wakeLock.request('screen');
        }
      } catch (e) {}
    };
    const rel = () => {
      try { if (window.__mangaWL) { window.__mangaWL.release(); } } catch (e) {}
      window.__mangaWL = null;
    };
    setInterval(() => { if (isRunning()) req(); else rel(); }, 4000);
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible' && isRunning()) req();
    });
  } catch (e) {}
  // ---- چیپ وضعیت زنده (فاز + زمان + صفحه‌ها) ----
  window.__mangaUpdateChip = (logText, btnLabel) => {
    try {
      const el = document.getElementById('manga_status_chip');
      if (!el) return;
      const log = (logText || '').toString();
      const t = (btnLabel || '').toString();
      const running = (t.indexOf('متوقف') >= 0 || t.indexOf('⏹') >= 0);
      const done = (log.indexOf('✅') >= 0 || log.indexOf('تمام شد') >= 0);
      const err = (log.indexOf('❌') >= 0 || log.indexOf('خطا — کد خروج') >= 0);
      if (!running && !done && !err &&
          (!log || log.indexOf('— لاگ بعد') === 0)) {
        el.style.display = 'none';
        el.innerHTML = '';
        return;
      }
      let phase = 'شروع';
      const ph = [
        [/\\[فاز ۱/, 'فاز ۱ — تشخیص حباب + OCR'],
        [/\\[فاز ۲/, 'فاز ۲ — ترجمه'],
        [/\\[فاز ۳/, 'فاز ۳ — ترجمهٔ بافر'],
        [/\\[فاز ۴/, 'فاز ۴ — پاکسازی + رندر'],
      ];
      for (const p of ph) {
        if (log.lastIndexOf(p[0]) >= 0) phase = p[1];
      }
      if (log.indexOf('ذخیرهٔ نهایی') >= 0) phase = 'ذخیرهٔ نهایی';
      const pages = (log.match(/شروع عملیات جدید/g) || []).length;
      let state = running ? 'run' : (err ? 'err' : (done ? 'ok' : 'idle'));
      const stateTxt = running ? 'در حال اجرا' : (err ? 'خطا' : (done ? 'تمام شد' : 'آماده'));
      let html = '<span class="chip-dot ' + state + '"></span>' +
        '<b>' + stateTxt + '</b>';
      html += '<span class="chip-sep">•</span><span>' + phase + '</span>';
      if (pages > 0) html += '<span class="chip-sep">•</span><span>📄 ' + pages + ' صفحه</span>';
      el.innerHTML = html;
      el.style.display = 'flex';
    } catch (e) {}
  };
  try { window.__mangaUpdateChip('', ''); } catch (e) {}
  // ---- دکمه‌های کپی/پاک‌کردن لاگ ----
  try {
    const copyBtn = document.getElementById('manga_copy_log');
    if (copyBtn && !copyBtn._bound) {
      copyBtn._bound = true;
      copyBtn.addEventListener('click', () => {
        const ta = document.querySelector('#manga_live_log textarea');
        const txt = ta ? ta.value : '';
        const ok = () => {
          const old = copyBtn.textContent;
          copyBtn.textContent = '✔ کپی شد';
          setTimeout(() => { copyBtn.textContent = old; }, 1400);
        };
        const fallback = () => {
          let tmp = null;
          try {
            tmp = document.createElement('textarea');
            tmp.value = txt;
            tmp.style.position = 'fixed';
            tmp.style.opacity = '0';
            document.body.appendChild(tmp);
            tmp.focus();
            tmp.select();
            document.execCommand('copy');
            tmp.remove();
            tmp = null;
          } catch (e) {
            if (tmp) { try { tmp.remove(); } catch (e2) {} }
          }
          ok();
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(txt).then(ok).catch(fallback);
        } else {
          fallback();
        }
      });
    }
  } catch (e) {}
  // ---- دکمهٔ دانلودِ لاگِ کامل (v1.14.200) ----
  // نمایشِ زنده فقط ۱۲۰ خطِ آخر را نشان میدهد؛ این دکمه فایلِ کاملِ لاگِ
  // رویِ دیسک را میدهد — از اولِ کار تا همین لحظه، بی هیچ برش (خواستهٔ
  // سازنده: «لاگ کامل بگیره ناقص نباشه» — برایِ گزارشِ باگ).
  try {
    const dlLogBtn = document.getElementById('manga_dl_log');
    if (dlLogBtn && !dlLogBtn._bound) {
      dlLogBtn._bound = true;
      dlLogBtn.addEventListener('click', async () => {
        const mark = (t) => {
          const old = dlLogBtn.textContent;
          dlLogBtn.textContent = t;
          setTimeout(() => { dlLogBtn.textContent = old; }, 1600);
        };
        const tools = document.querySelector('.log-tools');
        const sessdir = tools ? (tools.getAttribute('data-sessdir') || '') : '';
        let sid = '';
        try {
          const el = document.querySelector('#manga_sid textarea')
            || document.querySelector('[id*="manga_sid"] textarea');
          sid = ((el && el.value) || '').toString().trim();
          if (!sid) sid = (localStorage.getItem('manga_sid') || '').trim();
        } catch (e) {}
        if (!sessdir || !sid) { mark('✖ لاگی نیست'); return; }
        const url = '/gradio_api/file=' +
          encodeURIComponent(sessdir + '/' + sid + '.log').replace(/%2F/g, '/');
        try {
          const r = await fetch(url, { method: 'HEAD' });
          if (!r.ok) { mark('✖ لاگی نیست'); return; }
        } catch (e) {}
        const a = document.createElement('a');
        a.href = url;
        a.download = 'manga_log_' + sid.slice(0, 8) + '.txt';
        document.body.appendChild(a);
        a.click();
        a.remove();
        mark('✔ دانلود شد');
      });
    }
  } catch (e) {}
  return [];
}
"""

def run_web():
    
    os.environ["GRADIO_ALLOWED_PATHS"] = os.pathsep.join(
        {str(WORK_DIR), str(OUT_DIR), str(UPLOAD_DIR), str(FONT_DIR), str(HERE)})
    os.environ.setdefault("GRADIO_ANALYTICS_CACHE_FREQUENCY", "1000000000")
    try:
        import gradio  
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "gradio"])
    import gradio as gr
    try:
        from gradio import queueing as _q
        _q.Queue.compute_analytics_summary = (
            lambda self, records: self.cached_event_analytics_summary)
    except Exception:
        pass

    cfg = load_config()
    print("[*] بررسی فونت‌های لحن…")
    try:
        n = download_fonts()
        print(f"[+] {n} فونت دانلود شد.")
    except Exception as e:
        print(f"[!] فونت‌ها: {e}")

    def natural_key(s):
        return [int(t) if t.isdigit() else t.lower()
                for t in re.split(r"(\d+)", s)]

    def _dl_label(path: str) -> str:
        """برچسب دکمهٔ دانلود با حجم فایل."""
        try:
            if path and os.path.isfile(path):
                return f"⬇ دانلود ({human_size(os.path.getsize(path))})"
        except Exception:
            pass
        return "⬇ دانلود"



    # صفحهٔ خواندن زندهٔ وب — داخل پوشهٔ live نوشته می‌شود و صفحه‌های جدید خودکار به آن اضافه می‌شوند
    _LIVE_READER_TMPL = """<!DOCTYPE html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>نمایش</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:#000;color:#e8e6e1;font-family:system-ui,-apple-system,sans-serif;overscroll-behavior-y:contain;-webkit-user-select:none;user-select:none}
.bar{display:flex;align-items:center;flex-wrap:wrap;gap:6px;padding:9px 12px;background:#0c0c0e;border-bottom:1px solid #232326;direction:rtl;position:sticky;top:0;z-index:10;transform:translateZ(0);backface-visibility:hidden;will-change:transform}
.dot{width:9px;height:9px;border-radius:50%;background:#ff4a3d;animation:p 1.2s infinite;flex:none}
.dot.off{background:#2e7d4f;animation:none}
@keyframes p{0%,100%{opacity:1}50%{opacity:.25}}
.t{flex:1;color:#97948c;font-size:.82rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.n{color:#fff;background:#ff4a3d;border-radius:999px;padding:3px 11px;font-size:.8rem;font-weight:700;font-variant-numeric:tabular-nums;flex:none}
.n.done{background:#2e7d4f}
.dbtn{display:none;background:#161619;color:#e8e6e1;border:1px solid #2a2a2e;border-radius:8px;padding:7px 11px;font-size:.8rem;cursor:pointer;font-family:inherit;flex:none;min-height:36px}
.dbtn.on{background:#ff4a3d;border-color:#ff4a3d;color:#fff;font-weight:700}
.c{max-width:min(100%,900px);margin:0 auto;width:100%;position:relative}
.c img{display:block;width:100%;height:auto;user-select:none;-webkit-user-drag:none;pointer-events:none;content-visibility:auto;contain-intrinsic-size:auto 1200px}
.ph{width:100%;aspect-ratio:2/3;background:linear-gradient(100deg,#101012 40%,#17171a 50%,#101012 60%);background-size:200% 100%;animation:sh 1.6s infinite;border-radius:10px;margin:0 0 10px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;color:#5d5b55;font-size:.8rem}
@keyframes sh{0%{background-position:120% 0}100%{background-position:-80% 0}}
.sp{width:26px;height:26px;border-radius:50%;border:3px solid #26262a;border-top-color:#ff4a3d;animation:spin 1s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.hint{padding:16px;text-align:center;color:#6b6963;font-size:.85rem}
.zbtn{background:#161619;color:#e8e6e1;border:1px solid #2a2a2e;border-radius:8px;padding:7px 11px;font-size:.85rem;cursor:pointer;font-family:inherit;flex:none;min-height:36px;min-width:36px}
.zbtn:active{background:#2a2a30}
.zv{color:#97948c;font-size:.78rem;min-width:42px;text-align:center;flex:none;font-variant-numeric:tabular-nums}
.pbar{position:fixed;bottom:0;left:0;right:0;height:4px;background:#1a1a1c;z-index:4}
.pfill{height:100%;width:0;background:linear-gradient(90deg,#ff4a3d,#ff8a5e)}
</style></head><body>
<div class="bar"><span class="dot" id="dot"></span><div class="t">نمایش — صفحه‌ها سر جایشان پر می‌شوند</div><button type="button" class="zbtn" id="zo" title="کوچک‌تر">−</button><span class="zv" id="zv">100%</span><button type="button" class="zbtn" id="zi" title="بزرگ‌تر">+</button><button type="button" class="zbtn" id="zf" title="پهنای صفحه">پهنا</button><button type="button" class="dbtn" id="db">🔍 دیباگ</button><div class="n" id="n">0</div></div>
<main class="c" id="c"><div class="hint" id="h">در انتظار اولین صفحه…</div></main>
<div class="pbar"><div class="pfill" id="pf"></div></div>
<script>
(function(){
  var P = "__PREFIX__", D = "__DIR__", DBG = "__DBGDIR__", STAMP = Date.now();
  var arrived = 0, total = 0, dbgArrived = 0, dbgMode = false, busy = false;
  var mtimes = {};  // v1.14.160 — slot → mtime of last image update
  var c = document.getElementById('c'), h = document.getElementById('h'),
      b = document.getElementById('n'), dot = document.getElementById('dot'),
      db = document.getElementById('db');
  var haveDbg = !!DBG, dbgTotal = -1;
  // v1.14.159 — دکمهٔ 🔍 دیباگ فقط وقتی نشان داده میشود که حداقل یک
  // صفحهٔ دیباگ واقعاً وجود دارد (قبلاً فقط وجودِ پوشه کافی بود → دکمه
  // میآمد ولی فعال نبود). total.txt پوشهٔ دیباگ هر ۴ ثانیه چک میشود.
  function pollDbgTotal(){
    if (!haveDbg || dbgTotal > 0) return;
    fetch(P + DBG + 'total.txt?r=' + STAMP, { cache: 'no-store' })
      .then(function(r){ return r.ok ? r.text() : ''; })
      .then(function(t){
        var v = parseInt((t || '').trim(), 10);
        if (v > 0) { dbgTotal = v; render(); }
      })
      .catch(function(){});
  }
  setInterval(pollDbgTotal, 4000);
  pollDbgTotal();
  function pad(i){ return ('000' + i).slice(-4); }
  function curDir(){ return dbgMode ? DBG : D; }
  function curArrived(){ return dbgMode ? dbgArrived : arrived; }
  function imgSrc(i){ return P + curDir() + 'live_' + pad(i + 1) + '.jpg?r=' + STAMP; }
  function nearBottom(){ return (window.innerHeight + window.scrollY) >= (document.body.offsetHeight - 260); }
  function mkPh(){
    var d = document.createElement('div');
    d.className = 'ph';
    d.innerHTML = '<span class="sp"></span>در حال ترجمه…';
    return d;
  }
  function mkImg(i){
    var el = document.createElement('img');
    el.src = imgSrc(i);
    el.alt = 'صفحهٔ ' + (i + 1);
    el.loading = 'lazy'; el.decoding = 'async';
    return el;
  }
  // رندر پایدار: اسلات‌ها سر جایشان می‌مانند، فقط جای خالی با تصویر پر می‌شود.
  // هیچ اسکرول خودکاری انجام نمی‌شود — خواندنِ کاربر نمی‌پرد.
  function render(){
    var a = curArrived(), want = Math.max(total, a);
    if (h && h.parentNode === c) { c.removeChild(h); h = null; }
    while (c.children.length < want) c.appendChild(mkPh());
    for (var i = 0; i < want; i++) {
      var el = c.children[i];
      // v1.14.195 — ضدِ چشمکِ اسلاتِ تازه: تصویر اول کامل دیکود میشود؛
      // placeholderِ «در حال ترجمه…» تا آخرین لحظه سرِ جایش میماند و بعد
      // عوض میشود — زمینهٔ تیرهٔ خالی هرگز دیده نمیشود.
      if (i < a && el.tagName !== 'IMG' && !el.__pend) {
        el.__pend = 1;
        // IIFE: idx/imِ مخصوصِ همین اسلات — varِ بیرونی بینِ تکرارها مشترک است
        (function(idx){
          var im = document.createElement('img');
          im.src = imgSrc(idx);
          im.loading = 'eager';   // تصویرِ جدا از DOM: lazy هرگز نمیآید
          im.decoding = 'async';
          im.alt = 'صفحهٔ ' + (idx + 1);
          var put = function(){
            if (im.parentNode) return;
            var cur = c.children[idx];
            if (cur && cur.tagName !== 'IMG' && cur.__pend) c.replaceChild(im, cur);
          };
          if (im.decode) { im.decode().then(put, put); }
          else { im.onload = put; im.onerror = put; }
        })(i);
      }
    }
    b.textContent = a + (total > 0 ? ' / ' + total : '');
    var fin = (total > 0 && a >= total);
    b.className = 'n' + (fin ? ' done' : '');
    dot.className = 'dot' + (fin ? ' off' : '');
    if (haveDbg) db.style.display = ((dbgTotal > 0 || dbgArrived > 0) && (arrived > 0 || dbgArrived > 0 || total > 0)) ? 'inline-block' : 'none';
  }
  function probe(){
    if (busy) return;
    var a = curArrived(), mode = dbgMode;
    if (total > 0 && a >= total) return;
    busy = true;
    var im = new Image();
    im.onload = function(){
      busy = false;
      if (dbgMode === mode) {
        if (mode) dbgArrived = Math.max(dbgArrived, a + 1);
        else arrived = Math.max(arrived, a + 1);
        render();
        setTimeout(probe, 60);
      }
    };
    im.onerror = function(){ busy = false; };
    im.src = imgSrc(a);
  }
  if (haveDbg) {
    db.addEventListener('click', function(){
      dbgMode = !dbgMode;
      db.classList.toggle('on', dbgMode);
      db.textContent = dbgMode ? '📖 نهایی' : '🔍 دیباگ';
      c.innerHTML = '';
      mtimes = {};  // v1.14.160 — folder switched, reset stamps
      h = document.createElement('div');
      h.className = 'hint';
      h.textContent = dbgMode ? 'در انتظار دیباگ…' : 'در انتظار صفحه…';
      c.appendChild(h);
      render();
      probe();
    });
  }
  // v1.14.160 — progressive 15-by-15 refresh: the engine rewrites the same
  // slot file after every translated batch and logs 'slot mtime' into
  // mtimes.txt; here only the changed slot is re-fetched (no scroll jump).
  // v1.14.194 — گامِ اولِ تعویضِ بیفلاش: تصویرِ نو قبل از تعویضِ src کامل
  // دیکود میشد. ولی جوابِ سرورِ داخلی در کشِ حافظهٔ مرورگر نمیماند —
  // درخواستِ دومِ همان URL دوباره گرفته و دیکود میشد؛ ضمنِ آن چند صدم
  // ثانیه، عنصرِ img فریمِ قبلی را میریزد و زمینهٔ سیاه نشان میداد
  // («هر متنِ جدید صفحه سیاه میکنه انگار عکس کامل از اول لود میشه»).
  // v1.14.195 — گامِ دوم: پوشانهٔ دوبل. تصویرِ نو در یک imgِ روییِ همجایِ
  // اسلات (position:absolute رویِ همان مختصات) دیکود و «رویِ» تصویرِ قدیم
  // می‌نشیند؛ پیکسلهایِ قدیم تا این لحظه هرگز دور نمیشوند. فقط بعدِ
  // نقشدنِ پوشانه، srcِ اسلاتِ اصلی زیرِ پوشانه عوض میشود (نامرئی است) و
  // بعد از دیکودِ کاملِ اسلاتِ اصلی، پوشانه برداشته میشود. در هیچ فریمی
  // تصویرِ خالی/سیاه دیده نمیشود — نه چراغِ خاموش، نه پرشِ چیدمان.
  // اگر بهروزرسانیِ بعدیِ همان اسلات وسطِ تعویض برسد، صف میشود.
  function hotSwap(el, url){
    try {
      if (!el || el.tagName !== 'IMG') return;
      if (el.getAttribute('src') === url) return;
      if (el.__swapBusy) { el.__swapNext = url; return; }
      el.__swapBusy = 1;
      var par = el.parentNode;
      if (!par) { el.__swapBusy = 0; return; }
      var ov = document.createElement('img');
      ov.alt = ''; ov.draggable = false;
      ov.style.cssText = 'position:absolute;z-index:6;pointer-events:none;user-select:none;-webkit-user-drag:none;margin:0;content-visibility:visible;';
      var place = function(){
        try {
          ov.style.left = el.offsetLeft + 'px';
          ov.style.top = el.offsetTop + 'px';
          ov.style.width = el.offsetWidth + 'px';
          ov.style.height = el.offsetHeight + 'px';
        } catch (e0) {}
      };
      var cleanup = function(){
        try { ov.remove(); } catch (e4) { try { par.removeChild(ov); } catch (e6) {} }
        el.__swapBusy = 0;
        var nx = el.__swapNext; el.__swapNext = null;
        if (nx) hotSwap(el, nx);
      };
      var step2 = function(){
        // پوشانه نقشید → srcِ واقعی زیرِ آن عوض میشود (هیچکس نمیبیند)
        try { el.onerror = function(){ cleanup(); }; } catch (e5) {}
        try { el.src = url; } catch (e3) { cleanup(); return; }
        var fin = function(){ requestAnimationFrame(cleanup); };
        if (el.decode) { el.decode().then(fin, fin); } else { setTimeout(fin, 90); }
      };
      var cover = function(){
        try {
          if (ov.naturalWidth > 1 && ov.naturalHeight > 1)
            el.style.aspectRatio = ov.naturalWidth + '/' + ov.naturalHeight;
        } catch (e2) {}
        place();
        par.appendChild(ov);
        requestAnimationFrame(step2);
      };
      ov.src = url;
      if (ov.decode) { ov.decode().then(cover, cover); }
      else { ov.onload = cover; ov.onerror = cover; }
    } catch (err) {
      try { el.src = url; } catch (e2) {}
    }
  }
  var mtimeBusy = false;
  function pollMtimes(){
    if (mtimeBusy || arrived <= 0) return;
    mtimeBusy = true;
    fetch(P + curDir() + 'mtimes.txt?r=' + Date.now(), { cache: 'no-store' })
      .then(function(r){ return r.ok ? r.text() : ''; })
      .then(function(t){
        mtimeBusy = false;
        if (!t) return;
        var lines = t.split('\\n');
        for (var k = 0; k < lines.length; k++) {
          var m = lines[k].trim().split(/\\s+/);
          if (m.length < 2) continue;
          var slot = parseInt(m[0], 10), mt = m[1];
          if (!(slot >= 1 && slot <= arrived)) continue;
          if (mtimes[slot] === mt) continue;
          mtimes[slot] = mt;
          var el = c.children[slot - 1];
          if (el && el.tagName === 'IMG')
            hotSwap(el, P + curDir() + 'live_' + pad(slot) + '.jpg?r=' + Date.now());
        }
      })
      .catch(function(){ mtimeBusy = false; });
  }
  // total.txt: تعداد کل صفحه‌ها → از اول اسلات لودینگ برای همه گذاشته می‌شود
  function pollTotal(){
    if (total > 0) return;
    fetch(P + curDir() + 'total.txt?r=' + STAMP, { cache: 'no-store' })
      .then(function(r){ return r.ok ? r.text() : ''; })
      .then(function(t){
        var v = parseInt((t || '').trim(), 10);
        if (v > 0) { total = v; render(); }
      })
      .catch(function(){});
  }
  // v1.14.236 — چیپِ «↓ صفحه‌های جدید» پایین-چپ حذف شد (دستورِ سازنده:
  // «سمت چپ پایین میزنه چپتر جدید یا قسمت جدید… اونو حذف کن نمیخواد
  // بیاد») — اسکرولِ خودکار و پرشِ صفحه از قبل ممنوع بود؛ چیپ فقط
  // اعلانِ «صفحهٔ تازه آمده» بود.
  setInterval(function(){
    pollTotal();
    pollMtimes();
    probe();
  }, 1800);
  // ——— زوم پهنا (بزرگ/کوچک) + نوار پیشرفت پایین — همان سبکِ نمایشگر نهایی ———
  var zv = document.getElementById('zv'), pf = document.getElementById('pf');
  var z = 1;
  var baseW = function(){ return Math.max(200, Math.min(900, window.innerWidth || 360)); };
  var applyZoom = function(nz){
    nz = Math.min(4, Math.max(0.5, +nz || 1));
    var midY = window.innerHeight / 2;
    var relY = (window.scrollY + midY) / Math.max(0.01, z);
    z = nz;
    c.style.maxWidth = 'none';
    c.style.width = Math.round(baseW() * z) + 'px';
    c.style.marginLeft = 'auto';
    c.style.marginRight = 'auto';
    window.scrollTo(0, Math.max(0, relY * z - midY));
    if (zv) zv.textContent = Math.round(z * 100) + '%';
  };
  var zi = document.getElementById('zi'), zo = document.getElementById('zo'), zf = document.getElementById('zf');
  if (zi) zi.addEventListener('click', function(){ applyZoom(z * 1.25); });
  if (zo) zo.addEventListener('click', function(){ applyZoom(z * 0.8); });
  if (zf) zf.addEventListener('click', function(){ applyZoom(1); });
  window.addEventListener('wheel', function(e){
    if (!e.ctrlKey && !e.metaKey) return;
    e.preventDefault();
    applyZoom(e.deltaY < 0 ? z * 1.12 : z / 1.12);
  }, { passive: false });
  document.addEventListener('keydown', function(e){
    if (e.key === '+' || e.key === '=') applyZoom(z * 1.15);
    else if (e.key === '-' || e.key === '_') applyZoom(z * 0.87);
    else if (e.key === '0') applyZoom(1);
  });
  var updateProgress = function(){
    if (!pf) return;
    var m = document.documentElement.scrollHeight - window.innerHeight;
    pf.style.width = (m > 0 ? Math.min(100, Math.max(0, window.scrollY / m * 100)) : 0) + '%';
  };
  window.addEventListener('scroll', function(){
    updateProgress();
  }, { passive: true });
  window.addEventListener('resize', function(){
    if (z !== 1) applyZoom(z);
    updateProgress();
  });
  pollTotal();
  probe();
  updateProgress();
})();
</script>
</body></html>"""

    def build_reader_html(files, standalone: bool = True):
        
        import gradio as _gr
        gv = getattr(_gr, "__version__", "4")
        major = int(str(gv).split(".")[0] or 4)
        prefix = "/gradio_api/file=" if major >= 5 else "/file="
        urls = [prefix + str(p).replace(os.sep, "/") for p in files]
        if not urls:
            body = "<div style='text-align:center;opacity:.6;padding:24px'>تصویری برای نمایش پیدا نشد.</div>"
            if not standalone:
                return body
            return (
                "<!DOCTYPE html><html lang='fa' dir='rtl'><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                f"<title>خواندن</title></head><body style='background:#000;color:#999'>{body}</body></html>"
            )
        imgs = "".join(
            f'<img src="{u}" loading="lazy" decoding="async" alt="" draggable="false">'
            for u in urls
        )
        title = os.path.basename(os.path.dirname(files[0])) or "مانهوا"
        title_esc = (
            str(title).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;")
        )
        # v1.14.103: نوار بالا sticky است — با اسکرولِ پایین هم بالای صفحه
        # می‌چسبد (خواستهٔ کاربر: روی PC/لینوکس بدون برگشتن به بالا، دکمه‌ها
        # همیشه دسترس باشند — مثل اپ اندروید). اسکرول همچنان طبیعیِ سند است
        # و نوار پیشرفتِ پایین هم ثابت می‌ماند.
        css = (
            "*{box-sizing:border-box;margin:0;padding:0}"
            "html,body{background:#000;color:#e8e6e1;font-family:system-ui,-apple-system,sans-serif;"
            "overscroll-behavior-y:contain;-webkit-user-select:none;user-select:none}"
            ".rdr{background:#000;direction:ltr}"
            ".rdr-bar{display:flex;align-items:center;flex-wrap:wrap;gap:6px;padding:8px 10px;"
            "background:#0c0c0e;border-bottom:1px solid #232326;position:sticky;top:0;"
            "z-index:10;transform:translateZ(0);backface-visibility:hidden;will-change:transform}"
            ".rdr-btn{background:#161619;color:#e8e6e1;border:1px solid #2a2a2e;border-radius:8px;"
            "padding:8px 12px;font-size:.95rem;cursor:pointer;font-family:inherit;"
            "min-width:40px;min-height:40px;touch-action:manipulation;-webkit-tap-highlight-color:transparent}"
            ".rdr-btn:active{background:#2a2a30}"
            ".rdr-btn.fs{background:#ff4a3d;border-color:#ff4a3d;color:#fff;font-weight:700}"
            ".rdr-title{flex:1 1 120px;color:#97948c;font-size:.8rem;white-space:nowrap;"
            "overflow:hidden;text-overflow:ellipsis;text-align:right;direction:rtl;min-width:0}"
            ".rdrS{position:relative;background:#000}"
            ".rdrC{margin:0 auto;max-width:min(100%,900px);width:100%}"
            ".rdrC img{display:block;width:100%;height:auto;max-width:none;user-select:none;"
            "-webkit-user-drag:none;pointer-events:none;content-visibility:auto;contain-intrinsic-size:auto 1200px}"
            ".rdr-progress{position:fixed;bottom:0;left:0;right:0;height:3px;background:#1a1a1c;z-index:3}"
            ".rdrB{height:100%;width:0;background:linear-gradient(90deg,#ff4a3d,#ff8a5e)}"
            ".zlv{color:#97948c;font-size:.8rem;min-width:44px;text-align:center;font-variant-numeric:tabular-nums}"
            ".ph{width:100%;aspect-ratio:2/3;background:linear-gradient(100deg,#101012 40%,#17171a 50%,#101012 60%);background-size:200% 100%;animation:shph 1.6s infinite;border-radius:10px;margin:0 0 10px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;color:#5d5b55;font-size:.8rem}"
            "@keyframes shph{0%{background-position:120% 0}100%{background-position:-80% 0}}"
            ".sp{width:26px;height:26px;border-radius:50%;border:3px solid #26262a;border-top-color:#ff4a3d;animation:spinph 1s linear infinite}"
            "@keyframes spinph{to{transform:rotate(360deg)}}"
            "@media (max-width:480px){"
            ".rdr-bar{gap:4px;padding:6px 8px}"
            ".rdr-btn{padding:7px 10px;font-size:.9rem;min-width:36px}"
            ".rdr-title{font-size:.72rem;order:10;flex:1 1 100%;text-align:center}"
            "}"
        )
        # v1.14.31: جاوااسکریپت روی اسکرولِ خودِ سند (window) — نه داخل باکس؛
        # نوار بالا sticky است و با اسکرول، بالای صفحه می‌چسبد (وب + اندروید).
        js = r"""
(function(){
  const root = document.getElementById('manga_rdr');
  if (!root) return;
  const c = root.querySelector('.rdrC');
  const bar = root.querySelector('.zlv');
  const prog = root.querySelector('.rdrB');
  if (!c) return;
  let z = 1;
  const MIN = 0.5, MAX = 4;
  const baseWidth = () => Math.max(200, Math.min(900, window.innerWidth || 360));
  const applyZoom = (nz, cx, cy) => {
    nz = Math.min(MAX, Math.max(MIN, +nz || 1));
    const sx = (typeof cx === 'number') ? cx : (window.innerWidth / 2);
    const sy = (typeof cy === 'number') ? cy : (window.innerHeight / 2);
    const relX = (window.scrollX + sx) / Math.max(0.01, z);
    const relY = (window.scrollY + sy) / Math.max(0.01, z);
    z = nz;
    c.style.maxWidth = 'none';
    c.style.width = Math.round(baseWidth() * z) + 'px';
    c.style.marginLeft = 'auto';
    c.style.marginRight = 'auto';
    window.scrollTo(Math.max(0, relX * z - sx), Math.max(0, relY * z - sy));
    if (bar) bar.textContent = Math.round(z * 100) + '%';
    root.dataset.zoom = String(z);
  };
  const setZoom = (nz) => applyZoom(nz);
  const zoomBy = (f, cx, cy) => applyZoom(z * f, cx, cy);
  root.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-act]');
    if (!btn || !root.contains(btn)) return;
    e.preventDefault();
    const act = btn.getAttribute('data-act');
    if (act === 'close') {
      try {
        const isFs = document.fullscreenElement || document.webkitFullscreenElement;
        if (isFs) (document.exitFullscreen || document.webkitExitFullscreen).call(document);
      } catch (err) {}
      try { window.close(); } catch (err) {}
      try { if (history.length > 1) history.back(); } catch (err) {}
      return;
    }
    if (act === 'dbg') {
      dbgMode = !dbgMode;
      btn.textContent = dbgMode ? '\ud83d\udcd6 نهایی' : '🔍 دیباگ';
      btn.classList.toggle('fs', dbgMode);
      rebuild();
      return;
    }
    else if (act === 'zoom-in') zoomBy(1.25);
    else if (act === 'zoom-out') zoomBy(0.8);
    else if (act === 'zoom-fit') setZoom(1);
    else if (act === 'fs') {
      const isFs = document.fullscreenElement || document.webkitFullscreenElement
                || document.mozFullScreenElement || document.msFullscreenElement;
      if (isFs) {
        (document.exitFullscreen || document.webkitExitFullscreen
         || document.mozCancelFullScreen || document.msExitFullscreen).call(document);
      } else {
        const el = document.documentElement;
        const req = el.requestFullscreen || el.webkitRequestFullscreen
                 || el.mozRequestFullScreen || el.msRequestFullscreen;
        if (req) {
          try { req.call(el); } catch (err) {
            try { req.call(root); } catch (err2) {}
          }
        }
      }
    }
  });
  window.addEventListener('wheel', (e) => {
    if (!e.ctrlKey && !e.metaKey) return;
    e.preventDefault();
    zoomBy(e.deltaY < 0 ? 1.12 : 1 / 1.12, e.clientX, e.clientY);
  }, { passive: false });
  window.addEventListener('dblclick', (e) => {
    e.preventDefault();
    if (z > 1.3) setZoom(1);
    else zoomBy(2.2, e.clientX, e.clientY);
  });
  let pinch = null, pan = null;
  const dist = (a, b) => Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
  const mid = (a, b) => ({ x: (a.clientX + b.clientX) / 2, y: (a.clientY + b.clientY) / 2 });
  document.addEventListener('touchstart', (e) => {
    if (e.touches.length === 2) {
      pinch = { startDist: dist(e.touches[0], e.touches[1]), startZ: z };
      pan = null;
    } else if (e.touches.length === 1) {
      pan = { x: e.touches[0].clientX, y: e.touches[0].clientY,
              sl: window.scrollX, st: window.scrollY };
    }
  }, { passive: true });
  document.addEventListener('touchmove', (e) => {
    if (pinch && e.touches.length === 2) {
      e.preventDefault();
      const d = dist(e.touches[0], e.touches[1]);
      const m = mid(e.touches[0], e.touches[1]);
      applyZoom(pinch.startZ * (d / Math.max(1, pinch.startDist)), m.x, m.y);
    } else if (pan && e.touches.length === 1 && z > 1.05) {
      e.preventDefault();
      const t = e.touches[0];
      window.scrollTo(pan.sl - (t.clientX - pan.x), pan.st - (t.clientY - pan.y));
    }
  }, { passive: false });
  document.addEventListener('touchend', (e) => {
    if (e.touches.length < 2) pinch = null;
    if (e.touches.length === 0) pan = null;
  });
  document.addEventListener('touchcancel', () => { pinch = null; pan = null; });
  const updateProgress = () => {
    if (!prog) return;
    const m = document.documentElement.scrollHeight - window.innerHeight;
    prog.style.width = (m > 0 ? Math.min(100, Math.max(0, window.scrollY / m * 100)) : 0) + '%';
  };
  window.addEventListener('scroll', updateProgress, { passive: true });
  window.addEventListener('resize', () => { if (z !== 1) applyZoom(z); updateProgress(); });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      try {
        const isFs = document.fullscreenElement || document.webkitFullscreenElement;
        if (isFs) { (document.exitFullscreen || document.webkitExitFullscreen).call(document); return; }
      } catch (err) {}
      try { window.close(); } catch (err) {}
    } else if (e.key === '+' || e.key === '=') zoomBy(1.15);
    else if (e.key === '-' || e.key === '_') zoomBy(0.87);
    else if (e.key === '0') setZoom(1);
    else if (e.key === 'f' || e.key === 'F') {
      const btn = root.querySelector('[data-act="fs"]');
      if (btn) btn.click();
    }
  });
  // ——— نمایش زنده داخل خواننده (اسلات لودینگ) + سوئیچ دیباگ ———
  let dbgMode = false, arrived = c.querySelectorAll('img').length, total = 0, ndbg = 0;
  const mkPh = () => {
    const d = document.createElement('div');
    d.className = 'ph';
    d.innerHTML = '<span class="sp"></span>در حال ترجمه…';
    return d;
  };
  const mkImg = (i) => {
    const im = document.createElement('img');
    im.src = (dbgMode ? 'd/' : 'i/') + i;
    im.loading = 'lazy';
    im.decoding = 'async';
    im.alt = '';
    im.draggable = false;
    return im;
  };
  function rebuild() {
    const a = dbgMode ? ndbg : arrived;
    const w = Math.max(total, a);
    c.innerHTML = '';
    for (let i = 0; i < w; i++) c.appendChild(i < a ? mkImg(i) : mkPh());
  }
  function renderLive() {
    const a = dbgMode ? ndbg : arrived;
    const w = Math.max(total, a);
    while (c.children.length < w) c.appendChild(mkPh());
    for (let i = 0; i < w; i++) {
      const el = c.children[i];
      if (i < a && el && el.tagName !== 'IMG') c.replaceChild(mkImg(i), el);
    }
  }
  window.__mangaLive = function(n, tot, nd) {
    try {
      if (typeof tot === 'number' && tot > 0) total = tot;
      if (typeof nd === 'number' && nd > 0) {
        ndbg = nd;
        const tb = root.querySelector('[data-act="dbg"]');
        if (tb) tb.hidden = false;
      }
      if (!dbgMode) arrived = Math.max(arrived, n | 0);
      renderLive();
    } catch (err) {}
  };
  if (arrived > 0) renderLive();
  updateProgress();
})();
"""

        page = (
            "<!DOCTYPE html>\n"
            '<html lang="fa" dir="rtl">\n'
            "<head>\n"
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=5,user-scalable=yes">\n'
            '<meta name="apple-mobile-web-app-capable" content="yes">\n'
            f"<title>{title_esc}</title>\n"
            f"<style>{css}</style>\n"
            "</head>\n"
            "<body>\n"
            '<div class="rdr" id="manga_rdr" data-zoom="1">\n'
            # v1.14.103: نوار بالا sticky (position:sticky;top:0) — با اسکرولِ پایین
            # هم بالای صفحه می‌ماند. نوار پیشرفت پایین همچنان همیشه دیده می‌شود.
            '  <div class="rdrS">\n'
            '    <div class="rdr-bar">\n'
            '      <button type="button" class="rdr-btn" data-act="close" title="بستن">✕</button>\n'
            f'      <div class="rdr-title">{title_esc}</div>\n'
            '      <button type="button" class="rdr-btn" data-act="zoom-out" title="دور">−</button>\n'
            '      <span class="zlv">100%</span>\n'
            '      <button type="button" class="rdr-btn" data-act="zoom-in" title="نزدیک">+</button>\n'
            '      <button type="button" class="rdr-btn" data-act="zoom-fit" title="پهنای صفحه">پهنا</button>\n'
            '      <button type="button" class="rdr-btn fs" data-act="fs" title="فول‌اسکرین">⛶</button>\n'
            "    </div>\n"
            f'    <div class="rdrC">{imgs}</div>\n'
            "  </div>\n"
            '  <div class="rdr-progress"><div class="rdrB"></div></div>\n'
            "</div>\n"
            f"<script>\n{js}\n</script>\n"
            "</body>\n</html>\n"
        )
        return page

    g6 = _gradio_major() >= 6
    # v1.14.33: فونتِ Vazirmatn از پوشهٔ fonts خود برنامه سرو می‌شود (بدون
    # fonts.googleapis.com — در ایران کند/مسدود است و PC را خیلی دیر بالا می‌آورد).
    try:
        import gradio as _gr_css
        _gmaj = int(str(getattr(_gr_css, "__version__", "4")).split(".")[0] or 4)
    except Exception:
        _gmaj = 4
    _fpfx = ("/gradio_api/file=" if _gmaj >= 5 else "/file=") \
        + urllib.parse.quote(str(FONT_DIR).replace(os.sep, "/"), safe="/")
    WEB_CSS_RUNTIME = WEB_CSS.replace("__FONTPFX__", _fpfx)
    blocks_kw = {} if g6 else {"theme": gr.themes.Soft(primary_hue="indigo",
                                                       neutral_hue="slate"),
                               "css": WEB_CSS_RUNTIME}
    with gr.Blocks(title=APP_NAME, **blocks_kw) as demo:

        
        gr.HTML(
            """
<div class="nav">
  <div class="nav-left">
    <div class="stamp">漫</div>
    <div class="nav-brand">مانگا مترجم <span class="nav-sub">ترجمهٔ خودکار مانهوا</span></div>
  </div>
  <div class="nav-chips">
    <span class="chip">CPU / GPU</span>
    <span class="chip">Gemini · ChatGPT · Groq</span>
    <span class="chip">LaMa-Manga</span>
  </div>
</div>
"""
        )

        
        with gr.Group(elem_classes=["stepcard"]):
            gr.HTML('<div class="steptitle"><span class="stepnum">۱</span> ورودی — فایل یا لینک مانهوا</div>')
            inp_upload = gr.File(label="آپلود فایل‌ها (چندتایی) — کلیک کن",
                                 file_count="multiple", type="filepath",
                                 file_types=[".pdf", ".zip", ".cbz", ".webp", ".jpg", ".jpeg", ".png"],
                                 elem_classes=["compact-upload"])
            inp_path = gr.Textbox(label="یا URL تصویر/مانهوا (چند لینک = هر لینک در یک خط با اینتر)",
                                  placeholder="https://cdn.example.com/chapter/1/001.webp\nhttps://cdn.example.com/chapter/1/002.webp",
                                  info=("چند لینک = هر لینک را در یک خط بگذار (اینتر) — هرچقدر اینتر بزنی خودش می‌خوانَد؛ کاما هم کار می‌کند. حالت‌های دیگر: "
                                        "«…/1 > 14.jpg» از اول تا آخر، "
                                        "«…/1 < 14.jpg» از آخر به اول، "
                                        "«…/*.jpg» هرچه پیدا کند — همه با هم ترجمه می‌شوند."))

        
        with gr.Group(elem_classes=["stepcard"]):
            gr.HTML('<div class="steptitle"><span class="stepnum">۲</span> مترجم هوش مصنوعی</div>')
            # ترتیب خواستهٔ کاربر: ارائه‌دهنده → لینک (custom) → کلید → مدل → تست
            # v1.14.218 — منویِ انتخابِ AI: auto | gemini | مدلهایِ من | custom
            _init_models = list(load_custom_models())
            # v1.14.221 — «auto» فقط وقتی در لیست مدلها مدلی باشد در منو
            # میآید (دستورِ سازنده: «وقتی مدلی تو کاستوم اضافه نکرده باشم
            # دکمه auto نیاد تو لیست مدلا»)؛ بدونِ مدل: gemini | custom.
            _init_ch = _ai_choices(_init_models)
            _init_prov = "auto" if "auto" in _init_ch else "gemini"
            # v1.14.221 — ضربدرِ ✖ِ حذف، چسبیده به خودِ منو (نه لیستی پایینِ
            # صفحه): فقط وقتی مدلِ کاربر در منو انتخاب شده باشد دیده میشود
            # و همان مدلِ انتخابی را از لیست و منو پاک میکند.
            with gr.Row(elem_id="manga_provider_row"):
                provider = gr.Dropdown(
                    _init_ch, value=_init_prov,
                    label="منوی انتخاب AI", scale=6,
                    info=("«auto» (فقط با مدلِ اضافهشده) خودش بینِ Gemini و "
                          "مدل‌هایِ شما اولینِ در دسترس را انتخاب میکند "
                          "(خطا/عدمِ دسترسی → بعدی). مدلِ مشخص = فقط و فقط "
                          "همان. «custom» = فیلدهایِ همین صفحه. حذفِ مدلِ "
                          "خودت = انتخابش در منو + ✖ِ کنارِ منو."))
                cm_del_btn = gr.Button(
                    "✖", variant="secondary", scale=0,
                    elem_id="manga_cm_del_btn",
                    visible=(_init_prov in _cm_names(_init_models)))
            # v1.14.222 — مشخصاتِ مدلِ ذخیرهشدهٔ انتخابشده (لینک/مدلِ هوش/
            # کلیدِ ماسکشده) — فقط وقتی مدلِ کاربر در منو انتخاب شده باشد
            cm_info_md = gr.Markdown("", visible=False,
                                     elem_id="manga_cm_info")
            # v1.14.222 — بانکِ حافظهٔ فیلدها مالِ هر provider: وقتی از
            # Gemini به Custom (یا برعکس) میروی، هر کدام مقادیرِ خودشان را
            # دارند و مقادیرِ کاستوم زیرِ Gemini نشون داده نمیشود (دستورِ
            # سازنده: «میرم Gemini مال کاستوم ک سیو زدم نشون میده»)
            # (baseیِ configِ دیسک برایِ custom بذر میشود — PC/لینوکس)
            fields_bank = gr.State({
                "_last": _init_prov,
                "custom": {"base": str(cfg.get("api_base", "") or ""),
                           "key": "", "model": ""},
                "gemini": {"base": "", "key": "", "model": ""},
            })
            api_base = gr.Textbox(label="دامنهٔ API سفارشی (فقط برای provider «custom»)",
                                  value=str(cfg.get("api_base", "") or ""),
                                  placeholder="https://opencode.ai/inference/openai/v1/chat/completions",
                                  info="۴ فرمت خودکار شناخته می‌شود: …/chat/completions | …/responses | …/messages (Anthropic) | …:generateContent (Google) — لینک کامل endpoint را هم می‌شود چسباند؛ https:// اگر جا افتاده باشد خودکار اضافه می‌شود.",
                                  elem_id="manga_api_base",
                                  visible=False,
                                  scale=3)
            # v1.14.222 — رویِ «auto» ردیفِ ورود از همان ابتدا پنهان است (حالتِ
            # PC/دیسک که منو با «auto» بالا میآید)؛ دستورِ سازنده: «وقتی رو
            # auto بزارن اونجا نشه مدلی چیزی وارد کرد»
            with gr.Row(visible=(_init_prov != "auto")) as api_row:
                api_keys = gr.Textbox(label="کلیدهای API شما (با کاما = چرخش خودکار)",
                                      value="",
                                      type="password", scale=3,
                                      elem_id="manga_api_keys",
                                      info="کلید فقط در localStorage مرورگر شما می‌ماند — نه روی سرور و نه در config دسکتاپ.")

                # v1.14.229 — دستورِ سازنده: «قسمت ai همون قسمت gemini مدل
                # دستی باید بنویسی بجاش تو خوده gemini لیسا مدلای موجود تو
                # gemini نشون بده طرف انتخاب کنه بجز تو کاستوم باید طرف
                # خودش بنویسه»: مدل دستی حذف شد؛ دراپ‌داون + دکمهٔ ↻ —
                # با کلیدهای همین صفحه فهرستِ مدلهایِ زنده از خودِ سرویس
                # میآید (Gemini: فقط مدلهایِ ترجمهپذیر) و کاربر انتخاب
                # میکند؛ در custom هم میشود از فهرستِ همان سرویس گرفت و
                # هم آزادانه تایپ کرد (allow_custom_value).
                # v1.14.231 — دستورِ سازنده: «انتخاب مدل فقط باید تو Gemini
                # بیاد؛ بقیش باید دستی بنویسن و auto کلا نباید چیزی بیاد» —
                # دراپ‌داونِ زنده + ↻ فقط رویِ Gemini؛ رویِ custom فیلدِ دستیِ
                # ساده (لیبلِ جدا)؛ رویِ auto/مدلِ نامی کلِ ردیف پنهان است.
                # v1.14.232 — دستورِ سازنده: «مدل هارو افلاین هم بزار …
                # اگ اپدیتی چیزی شد خودشون رفرش میزنن» → دراپ‌داون از همان
                # اول لیستِ آفلاینِ داخلِ کد را دارد (فقط flash و
                # flash-lite و flash-preview)؛ ↻ همان لحظه از خودِ گوگل
                # فهرستِ تازه میگیرد و جایگزین میکند.
                model = gr.Dropdown(
                    choices=_gemini_offline_models(), value="",
                    allow_custom_value=True,
                    label="مدل — Gemini: فهرستِ آفلاین آماده است؛ ↻ برای "
                          "فهرستِ زنده (یا خودت بنویس) | خالی = پیش‌فرض",
                    scale=2, elem_id="manga_model")
                model_ref_btn = gr.Button(
                    "↻ مدل‌ها", variant="secondary", scale=1,
                    elem_id="manga_model_ref",
                    visible=(_init_prov == "gemini"))
            # ── v1.14.217/218/220 — مدیرِ مدلهایِ سفارشی: بدونِ فیلدِ «نام مدل
            # جدید» — دکمهٔ «+ افزودن به لیست مدل‌ها» مدلِ فعلیِ همین صفحه
            # (نام + دامنه + کلید + شناسهٔ مدل) را در لیست ثبت میکند.
            # v1.14.221 — حذفِ مدل فقط با ✖ِ کنارِ خودِ منو ──
            # v1.14.222 — دستورِ سازنده: «افزودن ai فقط تو کاستوم بیاد نه بقیه
            # چیزاش» → دکمهٔ «+ افزودن» و راهنما فقط رویِ custom دیده میشوند
            # (شروعِ صفحه همیشه auto/gemini است → هر دو از ابتدا پنهان)
            add_model_btn = gr.Button(
                "+ افزودن به لیست مدل‌ها", variant="secondary", scale=1,
                elem_id="manga_cm_add", visible=False)
            # v1.14.223 — دستورِ سازنده: «کسی کاستوم سیو کرد و چیزی ک سیو زده
            # بود بتونن ویرایش کنن ... اگ مدل خودشون رفتن اونجا سیو بیاد ...
            # با قابلیت ویرایش ویرایش زدن گزینه سیو بیاد» →
            # «✎ ویرایش» فقط رویِ مدلِ ذخیرهشدهٔ خودِ کاربر میآید؛ با زدنش
            # مقادیرِ ذخیرهشده (لینک/کلید/مدل) در فیلدها میآید و «افزودن» جای
            # خودش را به «💾 ذخیرهٔ ویرایش» میدهد (بجایِ گزینهٔ افزودن، ذخیره).
            cm_edit_btn = gr.Button(
                "✎ ویرایش این مدل", variant="secondary", scale=1,
                elem_id="manga_cm_edit", visible=False)
            cm_save_btn = gr.Button(
                "💾 ذخیرهٔ ویرایش", variant="primary", scale=1,
                elem_id="manga_cm_save", visible=False)
            cm_hint_md = gr.Markdown("<div class='hint'>«+ افزودن» مدلِ فعلیِ همین صفحه "
                        "(دامنه/کلید/مدل) را با یک نام در «لیست مدل‌ها» ثبت "
                        "میکند؛ مدل در حافظهٔ مرورگر/دستگاه میماند، در منویِ "
                        "انتخابِ AI میآید و در بکاپ هم ذخیره میشود. حذفِ مدل = "
                        "انتخابش در منو و زدنِ ✖ِ کنارِ منو. ویرایشِ مدلِ "
                        "ذخیرهشده = انتخابش در منو، «✎ ویرایش» و بعد «💾 "
                        "ذخیرهٔ ویرایش». رویِ «auto» فیلدها "
                        "قفل میشوند — خودش بینِ مدلها انتخاب میکند. کلید از "
                        "aistudio.google.com (Gemini) یا سرویسِ دلخواهِ خودتان "
                        "بگیرید؛ کلید در فیلد مخفی است — با 👁 دیده میشود؛ "
                        "تنظیمات وب فقط در مرورگر ذخیره میشود.</div>",
                        visible=False)
            test_key_btn = gr.Button(
                "تست کلیدها / لینک",
                scale=1, elem_id="manga_test_key")
            test_key_out = gr.Textbox(
                label="", value="", interactive=False, show_label=False,
                elem_id="manga_test_key_out", visible=False,
                placeholder="وضعیت هر کلید — سالم ✔ / خراب ✘ (بعد از ۶۰ ثانیه خودکار پاک می‌شود)")
            custom_models_state = gr.State(_init_models)
            cm_json_box = gr.Textbox(
                value=json.dumps(custom_models_state.value, ensure_ascii=False),
                visible=False, elem_id="manga_cm_json", container=False)
            # v1.14.219 — کانالهایِ مرورگر↔سرور باید در DOM بمانند (gradio 6
            # کامپوننتِ visible=False را از DOM حذف میکند) → visible=True +
            # کلاسِ مخفیِ CSS؛ در وب هم اندروید هم PC همین مرورگر است.
            cm_restore_box = gr.Textbox(
                value="", visible=True, elem_id="manga_cm_restore",
                elem_classes=["manga-hide-channel"], container=False)
            # v1.14.218 — کانالِ افزودنِ مدل از سمتِ مرورگر
            # (دکمهٔ «+ افزودن به لیست مدل‌ها»)
            cm_add_box = gr.Textbox(
                value="", visible=True, elem_id="manga_cm_add_box",
                elem_classes=["manga-hide-channel"], container=False)
            ocr_lang = gr.Dropdown(
                choices=[
                    ("انگلیسی", "en"),
                    ("کره‌ای (+ انگلیسی)", "ko en"),
                    ("ژاپنی (+ انگلیسی)", "ja en"),
                    ("چینی (+ انگلیسی)", "zh en"),
                    ("چندزبانه (کره‌ای/ژاپنی/چینی/انگلیسی)", "multi"),
                ],
                value=str(cfg.get("ocr_lang", "en")),
                label="زبان متن مانگا (OCR)",
                elem_id="manga_ocr_lang",
                info="زبان اصلی حباب‌ها — برای مانهوا فارسی/انگلیسی همان انگلیسی بماند.", scale=1)

        
        with gr.Group(elem_classes=["stepcard"]):
            gr.HTML('<div class="steptitle"><span class="stepnum">۳</span> خروجی</div>')
            with gr.Row():
                out_fmt = gr.Radio(["PDF", "ZIP", "HTML", "PSD", "پوشهٔ تصاویر"],
                                   value=cfg.get("out_fmt", "PDF"), label="قالب")
                quality = gr.Slider(60, 100, value=int(cfg.get("quality", 92)),
                                    step=1, label="کیفیت تصویر")

        
        with gr.Accordion("✒️ فونت‌ها (اصلی + لحن‌ها — اختیاری، خالی = فونت سرور)", open=False):
            font_upload = gr.File(label="فونت اصلی (.ttf)",
                                  file_count="single", type="filepath",
                                  file_types=[".ttf", ".otf"],
                                  elem_classes=["compact-upload"])
            gr.Markdown("<div class='hint'>هر فونت لحن را جدا آپلود کنید؛ خالی = فونت سرور. "
                        "با سوییچ کنار هر لحن، آن فونت/لحن را فعال یا غیرفعال کن — "
                        "لحن غیرفعال حذف می‌شود و حباب‌ها با فونت اصلی رندر می‌شوند.</div>")
            SLOT_LABELS = {
                "normal": "کودک (عادی)", "shout": "افسانه (خشم)",
                "comedy_shout": "کروش (کمدی)", "whisper": "زمزمه",
                "thought": "تفکر", "system": "سیستم/تگ",
                "letter": "نامه/طومار", "narrator": "راوی", "free_text": "متن آزاد",
            }
            tone_uploads = []
            tone_slots = []
            tone_enables = []
            with gr.Row():
                col1 = gr.Column()
                col2 = gr.Column()
            slots = list(FONT_BUNDLES)
            half = (len(slots) + 1) // 2
            for ci, chunk in enumerate((slots[:half], slots[half:])):
                with (col1 if ci == 0 else col2):
                    for slot, fname, desc, _u in chunk:
                        have = os.path.isfile(os.path.join(FONT_DIR, fname))
                        up = gr.File(label=f"{SLOT_LABELS.get(slot, slot)} ({desc})"
                                          f"{' ✓' if have else ''}",
                                     file_count="single", type="filepath",
                                     file_types=[".ttf", ".otf"],
                                     elem_classes=["compact-upload"])
                        en = gr.Checkbox(label=f"فعال: {SLOT_LABELS.get(slot, slot)}",
                                         value=True)
                        tone_uploads.append(up)
                        tone_slots.append(slot)
                        tone_enables.append(en)
                        try:
                            en.change(lambda v, u=up: gr.update(visible=bool(v)),
                                      inputs=[en], outputs=[up])
                        except Exception:
                            pass

        with gr.Accordion("⚙️ تنظیمات پیشرفته", open=False):
            with gr.Row():
                workers = _safe(gr.Slider, 1, 8, value=int(cfg.get("workers", 2)),
                                step=1, label="ورکر موازی OCR")
                bubbles = _safe(gr.Slider, 1, 12, value=int(cfg.get("bubbles", 6)),
                                step=1, label="حباب در هر درخواست ترجمه")
                batchw = _safe(gr.Slider, 1, 8, value=int(cfg.get("batch_workers", 3)),
                               step=1, label="بستهٔ ترجمهٔ موازی (کلید جدا برای هر بسته)")
            with gr.Row():
                timeout = _safe(gr.Slider, 10, 120, value=int(cfg.get("timeout", 40)),
                                step=5, label="تایم‌اوت هر درخواست (ثانیه)")
                maxre = _safe(gr.Slider, 1, 15, value=int(cfg.get("max_retries", 8)),
                              step=1, label="حداکثر تلاش ترجمه")
                reqdelay = _safe(gr.Slider, 0, 5, value=float(cfg.get("request_delay", 0)),
                                 step=0.5, label="تأخیر بین درخواست‌ها (ثانیه)")
            with gr.Row():
                temp = _safe(gr.Slider, 0, 1.5, value=float(cfg.get("temperature", 0.85)),
                             step=0.05, label="خلاقیت ترجمه (temperature)")
                readord = gr.Radio(["rtl", "ltr"], value=str(cfg.get("reading_order", "rtl")),
                                   label="ترتیب خواندن حباب‌ها")
            with gr.Row():
                _cm0 = str(cfg.get("clean_method") or "lama-manga").strip()
                if _cm0 not in ("lama-manga", "lama-big", "opencv"):
                    _cm0 = "lama-manga"
                clean_method = gr.Radio(
                    choices=[["lama.onnx", "lama-manga"],
                             ["big-lama", "lama-big"],
                             ["opencv", "opencv"]],
                    value=_cm0,
                    label="روش پاکسازی")
            with gr.Row():
                two_pass = gr.Checkbox(label="OCR دومرحله‌ای", value=True)
                fake_test = gr.Checkbox(label="حالت تست",
                                        value=bool(cfg.get("fake_test", False)))
                clean_only = gr.Checkbox(
                    label="حالت پاکسازی",
                    value=bool(cfg.get("clean_only", False)))
                web_debug = gr.Checkbox(label="حالت دیباگ",
                                        value=bool(cfg.get("web_debug", False)))
            glossary_text = gr.Textbox(
                label="واژه‌نامهٔ اسامی و اصطلاحات (هر خط: English=فارسی)",
                placeholder="Raphdonia=رافدونیا\nBarbarian=باربارین",
                lines=3, value=str(cfg.get("glossary_text", "") or ""))
            # v1.14.145: چهار گزینه جمع شد در یک دروپ‌داون (کلیک → گزینه‌ها می‌آید)؛
            # مقادیرِ انگلیسیِ خالص — دقیقاً همان که manga.py میپذیرد (فیکسِ invalid choice).
            # مقدارِ literal «auto» تا استخراجِ فرمِ گوشی (APK قدیمی) هم پیشفرض را ببیند — v1.14.146
            prompt_mode = gr.Dropdown(
                choices=["auto", "professional", "lite", "classic"],
                value=PROMPT_MODE_DEFAULT,
                label="سبک پرامپت مترجم", scale=1)
            # v1.14.145: پرامپتِ دستیِ جدا حذف شد — خودِ پرامپتِ اصلی قابلِ ویرایش است.
            # v1.14.147: تیترِ «پرامپت فعلی: ⚡…» هم حذف شد — فقط دروپ‌داون + کادرِ متن.
            _pp_body0 = resolve_prompt_preview(
                PROMPT_MODE_DEFAULT, cfg.get("provider"), cfg.get("model"),
                str(cfg.get("instruction_text") or ""))
            prompt_preview_body = gr.Textbox(
                label="پرامپت مترجم (همین به مدل فرستاده می‌شود — قابل ویرایش)",
                lines=10, max_lines=25, interactive=True,
                placeholder="خالی = پرامپتِ خودکارِ بر اساسِ سبک و مدل…",
                value=_pp_body0)
            story_brief = gr.Checkbox(
                label="بریف داستان قبل از ترجمه (AI یک‌بار فصل را می‌خواند تا لحن شخصیت‌ها حفظ شود)",
                value=bool(cfg.get("story_brief", True)))

        # ── v1.14.217/218 — بکاپ و بازیابی: «گرفتنِ بکاپ» فایلِ JSONِ همهٔ
        # چیزها را میدهد؛ «Import» همان فایل را کامل برمیگرداند ──
        # v1.14.219 — دستورِ سازنده: «تنظیمات بکاپ همینجوری باز نباشه وقتی
        # زدم باز شه» → آکاردئونِ بسته؛ و «بکاپ زدم خودکار دانلود کنه نه این ک
        # مجدد برم دکمه دانلود بزنم» → با یک کلیک، فایل خودکار دانلود میشود
        # (JS رویِ changeِ فایلِ خروجی — URLِ سرو شده + orig_name).
        with gr.Accordion("💾 بکاپ و بازیابی — مدلها + تنظیمات", open=False,
                          elem_classes=["stepcard"]):
            gr.Markdown("<div class='hint'>دکمهٔ «⬇️ گرفتن بکاپ» = با یکِ کلیک، "
                        "فایلِ JSONِ «همه‌چیز» همین‌جا خودکار دانلود میشود: لیستِ "
                        "مدلهایِ شما (نام + دامنه + کلید API + شناسهٔ مدل) و تمامِ "
                        "تنظیمات. دکمهٔ «⬆️ Import» = یک دکمهٔ کوچکِ مثلِ خودِ "
                        "بکاپ (بدونِ باکسِ بزرگِ آپلود) — کلیک کن، فایلِ بکاپ را "
                        "انتخاب کن، همه‌چیز کامل برمیگردد. دکمه میگیرد (دانلودِ "
                        "خودکار)، دکمه برمیگرداند.</div>")
            with gr.Row():
                backup_btn = gr.Button("⬇️ گرفتن بکاپ (دانلود JSON)",
                                       variant="primary", scale=1,
                                       elem_id="manga_backup_btn")
                # v1.14.220 — دستورِ سازنده: «نمیشد دکمه import مثل همون
                # backup باشه بزرگ نباشه» → بهجایِ باکسِ بزرگِ drag&drop،
                # UploadButtonِ هم‌اندازهٔ دکمهٔ بکاپ: کلیک = پنجرهٔ انتخابِ
                # فایل (اندروید/PC/لینوکس/وب همه همان مرورگرند)
                import_file = gr.UploadButton(
                    "⬆️ Import — بازیابی از بکاپ",
                    file_count="single", type="filepath",
                    file_types=[".json"], variant="secondary", scale=1,
                    elem_id="manga_import_file")
            backup_out = gr.File(label="فایلِ پشتیبان — اگر دانلودِ خودکار شروع "
                                       "نشد، از همین‌جا دانلودش کنید",
                                 visible=False, elem_id="manga_backup_out")
            backup_status = gr.Textbox(
                label="", show_label=False, interactive=False, visible=False,
                elem_id="manga_backup_status")

        # v1.14.176–180 — «آزمایشگاهِ سرعتِ استخراج» و دکمهٔ «تستِ سرعت».
        # v1.14.181 — دستورِ سازنده: «خب ml kit بزار… بقیش حذف کن تو گوشی
        # استفاده نکنه و اون دکمه تست همه استخراج حذف کن» → دکمه کامل
        # حذف شد؛ برندهٔ ذخیرهشدهٔ تستِ ۱۷۹ (mlkit) و پاکسازیِ مدلهایِ
        # بازنده را خودِ پایتون (speed_lab_env) انجام میدهد.
        # v1.14.33: سیوِ فرم در «مرورگر وب» ۳۰ دقیقه می‌ماند (خواستهٔ کاربر).
        # در پنجرهٔ دسکتاپ (?desktop=1) و اپ اندروید (UA مخصوص) ذخیره دائمی است.
        SESSION_TTL = 30 * 60
        JOB_TTL = 12 * 3600
        _perm_js = (
            "const PERM = (new URLSearchParams(location.search)).get('desktop') === '1' "
            "|| !!(window.pywebview) || /MangaTranslatorApp/i.test(navigator.userAgent || '');"
        )
        live_jobs = {}

        def _get_job(sid: str) -> dict:
            if sid not in live_jobs:
                live_jobs[sid] = {
                    "proc": None,
                    "log": "— لاگ بعد از شروع ترجمه اینجا می‌آید —",
                    "lock": threading.Lock(),
                    "ts": time.time(),
                    "download_path": None,
                    "html_state": "",
                    "reader_path": None,
                    "result_visible": False,
                    "running": False,
                    "returncode": None,
                    "buf": [],
                    "t0": None,
                    "live_dir": None,
                    "live_files": [],
                }
            return live_jobs[sid]

        def _job_running(job: dict) -> bool:
            p = job.get("proc")
            if p is not None:
                try:
                    if p.poll() is None:
                        return True
                except Exception:
                    pass
            return bool(job.get("running"))

        def _kill_job(sid: str) -> None:
            job = _get_job(sid)
            with job["lock"]:
                p = job.get("proc")
                job["running"] = False
                if p is not None:
                    try:
                        if p.poll() is None:
                            try:
                                os.killpg(p.pid, signal.SIGTERM)
                            except Exception:
                                try:
                                    p.terminate()
                                except Exception:
                                    pass
                            try:
                                p.wait(timeout=2.5)
                            except Exception:
                                try:
                                    os.killpg(p.pid, signal.SIGKILL)
                                except Exception:
                                    try:
                                        p.kill()
                                    except Exception:
                                        pass
                                try:
                                    p.wait(timeout=1)
                                except Exception:
                                    pass
                    except Exception:
                        pass
                job["proc"] = None
                job["ts"] = time.time()
                job["log"] = (job.get("log") or "") + "\n⏹ ترجمه متوقف شد توسط کاربر."
                _append_job_logfile(sid, "⏹ ترجمه متوقف شد توسط کاربر.")
            try:
                _persist_job_meta(sid)
            except Exception:
                pass

        def _new_sid() -> str:
            import uuid
            return uuid.uuid4().hex

        SESS_DIR = os.path.join(WORK_DIR, "sessions")
        os.makedirs(SESS_DIR, exist_ok=True)

        def _persist_job_meta(sid: str) -> None:
            if not sid:
                return
            job = _get_job(sid)
            try:
                with job["lock"]:
                    meta = {
                        "sid": sid,
                        "running": _job_running(job),
                        "log": (job.get("log") or "")[-24000:],
                        "ts": job.get("ts") or time.time(),
                        "download_path": job.get("download_path"),
                        "download_debug": job.get("download_debug"),
                        "result_visible": bool(job.get("result_visible")),
                        "returncode": job.get("returncode"),
                        "out_v": job.get("out_v"),
                        "src": str(job.get("src") or "")[:500],
                        "reader_path": job.get("reader_path"),
                        "reader_debug_path": job.get("reader_debug_path"),
                        "live_dir": job.get("live_dir"),
                        "html_debug": (job.get("html_debug") or "")[:500] and True,
                        "has_debug": bool(job.get("download_debug") or job.get("reader_debug_path")),
                        "want_debug": bool(job.get("want_debug")),
                    }
                path = os.path.join(SESS_DIR, f"{sid}.json")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False)
            except Exception:
                pass

        def _load_job_meta(sid: str) -> dict:
            path = os.path.join(SESS_DIR, f"{sid}.json")
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}

        def _append_job_logfile(sid: str, text: str) -> None:
            # v1.14.200 — لاگِ کاملِ رویِ دیسک (خواستهٔ سازنده: «لاگ کامل بگیره
            # ناقص نباشه» برایِ گزارشِ باگ). بافرِ زندهٔ UI برایِ سبکماندن فقط
            # ۱۲۰ خطِ آخر را نشان میدهد؛ این فایلِ کامل هرگز بریده نمیشود و
            # دکمهٔ «دانلود لاگ» همین را کامل میدهد — از اولِ کار تا آخر.
            if not sid or not text:
                return
            try:
                os.makedirs(SESS_DIR, exist_ok=True)
                with open(os.path.join(SESS_DIR, f"{sid}.log"), "a",
                          encoding="utf-8") as f:
                    f.write(text if text.endswith("\n") else text + "\n")
            except Exception:
                pass


        def _find_active_sid(preferred: str = "") -> str:
            
            pref = (preferred or "").strip()
            if not pref:
                return ""
            job = live_jobs.get(pref)
            if job is not None:
                return pref
            meta = _load_job_meta(pref)
            if meta:
                j = _get_job(pref)
                with j["lock"]:
                    if meta.get("log"):
                        j["log"] = meta.get("log")
                    if meta.get("download_path"):
                        j["download_path"] = meta.get("download_path")
                    if meta.get("result_visible"):
                        j["result_visible"] = True
                    if meta.get("html_state"):
                        j["html_state"] = meta.get("html_state")
                    if meta.get("reader_path"):
                        j["reader_path"] = meta.get("reader_path")
                    if meta.get("reader_debug_path"):
                        j["reader_debug_path"] = meta.get("reader_debug_path")
                    if meta.get("live_dir"):
                        j["live_dir"] = meta.get("live_dir")
                    if meta.get("download_debug"):
                        j["download_debug"] = meta.get("download_debug")
                    if meta.get("want_debug"):
                        j["want_debug"] = meta.get("want_debug")
                    j["ts"] = meta.get("ts") or time.time()
                    j["out_v"] = meta.get("out_v")
                    j["src"] = meta.get("src")
                    if not _job_running(j):
                        j["running"] = False
                return pref
            return pref

        def _finalize_job_success(sid: str) -> None:
            job = _get_job(sid)
            with job["lock"]:
                if job.get("result_visible"):
                    return
                out_v = job.get("out_v") or ""
                src = job.get("src") or ""
                t0 = job.get("t0") or time.time()
                buf = list(job.get("buf") or [])
            if not out_v:
                return
            el = int(time.time() - t0)
            dur_s = f"{el // 60}:{el % 60:02d}"
            target = out_v
            try:
                if os.path.isdir(out_v):
                    target = shutil.make_archive(out_v, "zip", out_v)
            except Exception:
                target = out_v
            try:
                append_history({
                    "time": datetime.now().strftime("%m-%d %H:%M"),
                    "input": src, "status": "✅", "duration": dur_s
                })
            except Exception:
                pass
            def _collect_imgs(root_paths, exclude_debug=False):
                found = []
                seen = set()
                for root in root_paths:
                    if not root:
                        continue
                    if exclude_debug and "debug" in os.path.basename(str(root)).lower():
                        continue
                    if os.path.isfile(root) and root.lower().endswith(
                        (".webp", ".png", ".jpg", ".jpeg")
                    ):
                        if exclude_debug and "debug" in os.path.basename(root).lower():
                            continue
                        if root not in seen:
                            seen.add(root)
                            found.append(root)
                        continue
                    if not os.path.isdir(root):
                        continue
                    try:
                        names = sorted(os.listdir(root), key=natural_key)
                    except Exception:
                        continue
                    for f in names:
                        if f.lower().endswith((".webp", ".png", ".jpg", ".jpeg")):
                            if exclude_debug and ("debug" in f.lower() or "debug" in root.lower()):
                                continue
                            p = os.path.join(root, f)
                            if p not in seen:
                                seen.add(p)
                                found.append(p)
                return found

            def _pdf_to_reader_imgs(pdf_path, dest_dir, limit=80):
                
                try:
                    import fitz
                except ImportError:
                    try:
                        subprocess.check_call(
                            [sys.executable, "-m", "pip", "install", "-q", "pymupdf"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        )
                        import fitz
                    except Exception:
                        return []
                os.makedirs(dest_dir, exist_ok=True)
                out = []
                try:
                    doc = fitz.open(pdf_path)
                    zoom = 120 / 72.0
                    mat = fitz.Matrix(zoom, zoom)
                    for i, page in enumerate(doc):
                        if i >= limit:
                            break
                        pix = page.get_pixmap(matrix=mat)
                        fp = os.path.join(dest_dir, f"view_{i+1:03d}.jpg")
                        pix.save(fp)
                        out.append(fp)
                    doc.close()
                except Exception as e:
                    print(f"[!] استخراج PDF برای نمایشگر: {e}")
                return out

            parent = os.path.dirname(str(out_v)) or "."
            search_dirs = [
                out_v if os.path.isdir(out_v) else None,
            ]
            _cache_subs = ("out", "out_safe_v3")
            try:
                cache_root = str(out_v) + ".cache"
                if os.path.isdir(cache_root):
                    for sub in _cache_subs:
                        search_dirs.append(os.path.join(cache_root, sub))
                    for name in os.listdir(cache_root):
                        if name.startswith("out"):
                            search_dirs.append(os.path.join(cache_root, name))
            except Exception:
                pass
            cache_debug = os.path.join(str(out_v) + ".cache", "debug_safe_v3")
            if not os.path.isdir(cache_debug):
                cache_debug = os.path.join(str(out_v) + ".cache", "debug")

            imgs = _collect_imgs(search_dirs, exclude_debug=True)
            if not imgs and str(target).lower().endswith((".webp", ".png", ".jpg", ".jpeg")):
                imgs = [target]

            
            pdf_for_view = None
            if not imgs:
                for cand in (out_v, target):
                    if cand and str(cand).lower().endswith(".pdf") and os.path.isfile(cand):
                        pdf_for_view = cand
                        break
            debug_pdf = os.path.splitext(str(out_v))[0] + "_debug.pdf"
            debug_imgs = []
            if os.path.isfile(debug_pdf):
                dbg_dir = os.path.join(parent, "_debug_view")
                debug_imgs = _pdf_to_reader_imgs(debug_pdf, dbg_dir)
            if pdf_for_view and not imgs:
                view_dir = os.path.join(parent, "_pdf_view")
                imgs = _pdf_to_reader_imgs(pdf_for_view, view_dir)

            
            if not debug_imgs:
                debug_imgs = _collect_imgs([cache_debug])

            try:
                reader_html = build_reader_html(imgs, standalone=True)
            except Exception:
                reader_html = ""
            try:
                debug_reader_html = build_reader_html(debug_imgs, standalone=True) if debug_imgs else ""
            except Exception:
                debug_reader_html = ""

            reader_path = None
            debug_reader_path = None
            try:
                base_dir = out_v if os.path.isdir(out_v) else os.path.dirname(str(out_v))
                if not base_dir or not os.path.isdir(base_dir):
                    base_dir = os.path.join(OUT_DIR, sid[:12])
                    os.makedirs(base_dir, exist_ok=True)
                reader_path = os.path.join(base_dir, "reader.html")
                with open(reader_path, "w", encoding="utf-8") as rf:
                    rf.write(reader_html or "")
                if debug_reader_html:
                    debug_reader_path = os.path.join(base_dir, "reader_debug.html")
                    with open(debug_reader_path, "w", encoding="utf-8") as rf:
                        rf.write(debug_reader_html)
            except Exception as e:
                print(f"[!] ذخیره reader.html ناموفق: {e}")
                reader_path = None

            
            download_debug = debug_pdf if os.path.isfile(debug_pdf) else None
            if not download_debug and debug_imgs:
                try:
                    import zipfile
                    zpath = os.path.join(parent, os.path.splitext(os.path.basename(str(out_v)))[0] + "_debug_imgs.zip")
                    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                        for p in debug_imgs:
                            zf.write(p, arcname=os.path.basename(p))
                    download_debug = zpath
                except Exception:
                    download_debug = None

            extra = ""
            if not imgs:
                extra = "\n⚠ تصاویر برای نمایشگر پیدا نشد — فقط دانلود فعال است."
            if debug_imgs or download_debug:
                extra += f"\n🔍 دیباگ: {len(debug_imgs)} صفحه آماده نمایش/دانلود"
            _done_line = (f"✅ تمام شد ({dur_s}) — دکمه‌های نمایش و دانلود پایین فعال شدند"
                          + extra)
            final_log = "\n".join(buf[-120:]) + _done_line
            _append_job_logfile(sid, _done_line)
            with job["lock"]:
                job["log"] = final_log
                job["download_path"] = target
                job["download_debug"] = download_debug
                job["html_state"] = reader_html
                job["html_debug"] = debug_reader_html
                job["reader_path"] = reader_path
                job["reader_debug_path"] = debug_reader_path
                job["result_visible"] = True
                job["ts"] = time.time()
            _persist_job_meta(sid)

        def _start_job_reader(sid: str, proc: subprocess.Popen, t0: float) -> None:
            job = _get_job(sid)

            def _fmt(buf_lines):
                return "\n".join(buf_lines[-120:]) if buf_lines else "… در حال دریافت خروجی …"

            def _reader():
                buf = list(job.get("buf") or [])
                n = 0
                partial = b""
                # v1.14.200 — فایلِ کاملِ لاگِ این نشست: هر خطِ stdoutِ پروسه
                # همین‌جا رویِ دیسک مینشیند. نمایشِ زنده عمداً ۱۲۰ خطِ آخر را
                # نشان میدهد (سبک برایِ مرورگر) ولی «دانلود لاگ» باید کامل
                # باشد نه ناقص — پس جریان کامل، خطبهخط، مینشیند.
                log_fh = None
                try:
                    os.makedirs(SESS_DIR, exist_ok=True)
                    log_fh = open(os.path.join(SESS_DIR, f"{sid}.log"), "a",
                                  encoding="utf-8")
                except Exception:
                    log_fh = None
                try:
                    stream = proc.stdout
                    fd = None
                    try:
                        fd = stream.fileno()
                    except Exception:
                        fd = None
                    while True:
                        with job["lock"]:
                            if job.get("proc") is None and not job.get("running"):
                                break
                        ended = proc.poll() is not None
                        chunk = b""
                        try:
                            if fd is not None:
                                import select as _sel
                                try:
                                    ready, _, _ = _sel.select([stream], [], [], 0.25)
                                except Exception:
                                    ready = [stream]
                                if ready:
                                    chunk = os.read(fd, 8192)
                            else:
                                chunk = stream.read(4096) if stream else b""
                        except Exception:
                            chunk = b""
                        if chunk:
                            if isinstance(chunk, str):
                                chunk = chunk.encode("utf-8", "replace")
                            partial += chunk
                            while b"\n" in partial:
                                line, partial = partial.split(b"\n", 1)
                                text = line.decode("utf-8", "replace").rstrip("\r")
                                buf.append(text)
                                if log_fh is not None:
                                    try:
                                        log_fh.write(text + "\n")
                                        log_fh.flush()
                                    except Exception:
                                        log_fh = None
                                if len(buf) > 400:
                                    del buf[:-300]
                                with job["lock"]:
                                    job["buf"] = buf
                                    job["log"] = _fmt(buf)
                                    job["ts"] = time.time()
                                n += 1
                                
                                if n % 2 == 0:
                                    _persist_job_meta(sid)
                        elif ended:
                            break
                        else:
                            time.sleep(0.05)
                    if partial.strip():
                        _tail_txt = partial.decode("utf-8", "replace").rstrip("\r")
                        buf.append(_tail_txt)
                        if log_fh is not None:
                            try:
                                log_fh.write(_tail_txt + "\n")
                                log_fh.flush()
                            except Exception:
                                log_fh = None
                    try:
                        proc.wait(timeout=5)
                    except Exception:
                        pass
                except Exception as e:
                    with job["lock"]:
                        job["log"] = (job.get("log") or "") + f"\n⚠ reader: {e}"
                    _append_job_logfile(sid, f"⚠ reader: {e}")
                finally:
                    if log_fh is not None:
                        try:
                            log_fh.close()
                        except Exception:
                            pass
                    log_fh = None
                    rc = None
                    try:
                        rc = proc.poll()
                    except Exception:
                        pass
                    with job["lock"]:
                        if job.get("proc") is proc:
                            job["proc"] = None
                        job["running"] = False
                        job["returncode"] = rc
                        job["buf"] = buf
                        if buf:
                            job["log"] = _fmt(buf)
                        job["ts"] = time.time()
                        job["done_event"] = True
                    if rc == 0:
                        try:
                            _finalize_job_success(sid)
                        except Exception as e:
                            with job["lock"]:
                                job["log"] = (job.get("log") or "") + f"\n⚠ finalize: {e}"
                    elif rc not in (None, 0) and rc not in (-15, -9, 15, 9):
                        with job["lock"]:
                            job["log"] = (job.get("log") or "") + f"\n\n❌ خطا — کد خروج {rc}"
                        _append_job_logfile(sid, f"❌ خطا — کد خروج {rc}")
                    _persist_job_meta(sid)

            threading.Thread(target=_reader, daemon=True, name=f"manga-job-{sid[:8]}").start()

            def _heartbeat():
                while True:
                    with job["lock"]:
                        if not _job_running(job):
                            break
                        buf = list(job.get("buf") or [])
                        job["log"] = _fmt(buf)
                        job["ts"] = time.time()
                    try:
                        _persist_job_meta(sid)
                    except Exception:
                        pass
                    time.sleep(1.0)
            threading.Thread(target=_heartbeat, daemon=True, name=f"manga-hb-{sid[:8]}").start()

        session_id = gr.State("")
        sid_box = gr.Textbox(value="", visible=True, elem_id="manga_sid", label="sid",
                             elem_classes=["manga-hide-channel"])
        
        sid_holder = gr.Textbox(value="", visible=True, elem_id="manga_sid_holder",
                                label="sid_holder", elem_classes=["manga-hide-channel"])

        run_btn = gr.Button("🚀  شروع ترجمه", variant="primary", elem_id="runbtn")

        with gr.Accordion("📡 لاگ زنده", open=True):
            # v1.14.200 — «دانلود لاگ» کنارِ «کپی لاگ» (خواستهٔ سازنده برایِ PC/لینوکس):
            # کپی، همان ۱۲۰ خطِ نمایشِ زنده را میدهد؛ دانلود، فایلِ کاملِ لاگِ
            # رویِ دیسک را (از اولِ کار تا همین لحظه) — برایِ گزارشِ باگ. مسیرِ
            # پوشهٔ نشستها در data-sessdir میآید تا JS همان را از روتِ /file بخواهد.
            gr.HTML(
                f"""
<div id="manga_status_chip"></div>
<div class="log-tools" data-sessdir="{SESS_DIR.replace('&', '&amp;').replace('"', '&quot;')}">
  <button type="button" class="log-tool-btn" id="manga_copy_log" title="کپی متن لاگ">📋 کپی لاگ</button>
  <button type="button" class="log-tool-btn" id="manga_dl_log" title="دانلودِ فایلِ کاملِ لاگ — از اولِ کار تا همین لحظه">⬇ دانلود لاگ</button>
</div>
"""
            )
            log_box = _safe(gr.Textbox, lines=16, max_lines=50, autoscroll=True,
                            show_label=False, interactive=True,
                            elem_id="manga_live_log",
                            value="— لاگ بعد از شروع ترجمه اینجا می‌آید —")
            # v1.14.236 — نوارِ پیشرفتِ زیرِ لاگ: فاز + «صفحهٔ n از N» +
            # درصد — مثلِ اعلانِ اپ اندروید؛ هر ۱ ثانیه از همان لاگ
            # بهروزرسانی میشود (تایمرِ _poll_job_status).
            prog_html = _safe(gr.HTML, elem_id="manga_prog_row",
                              visible=False, value="")

        html_state = gr.State("")
        html_debug_state = gr.State("")
        # v1.14.31: فقط «یک» نمایش — دکمه‌های «نمایش اصلی» و «صفحه دیباگ» حذف شدند.
        # دیباگ با همان دکمهٔ 🔍 داخل خود نمایش عوض می‌شود (خواستهٔ کاربر).
        # کامپوننت‌های قدیمی فقط به‌عنوان hidden-stub می‌مانند تا امضای خروجی‌ها نشکند؛
        # همه‌جا visible=False اجباری می‌شود.
        with gr.Group(elem_classes=["stepcard"], visible=False) as result_group:
            gr.HTML('<div class="steptitle"><span class="stepnum">📖</span> '
                    'نمایش</div>')
            live_btn = _safe(gr.Button, "📖 نمایش", visible=False, elem_id="manga_live_btn")
            gr.HTML('<div class="livehint" id="manga_live_hint" style="display:none">'
                    'تا کار در جریان است، هر صفحهٔ جدید خودش داخل نمایش اضافه می‌شود — '
                    'دکمهٔ 🔍 دیباگ هم داخل خودِ نمایش است</div>')
            with gr.Row():
                btn_view = _safe(gr.Button, "👁 نمایش", visible=False,
                                 elem_id="manga_view_btn")
                dl_btn = _safe(gr.DownloadButton, label="⬇ دانلود", visible=False)
            debug_row = gr.Row(visible=False)
            with debug_row:
                btn_view_debug = _safe(gr.Button, "🔍 صفحه دیباگ", visible=False,
                                       elem_id="manga_view_debug_btn")
                dl_btn_debug = _safe(gr.DownloadButton, label="⬇ دانلود دیباگ", visible=False)
            viewer_html = gr.HTML(visible=False, elem_id="reader_wrap")

        LS_KEY = "manga_autotranslate_form_v2"
        JOB_KEY = "manga_job_v1"
        browser_form_json = gr.State("")

        save_form_js = f"""
(sid, sidBox, inp, prov, keys, model, fmt, qual, workers, bubbles, timeout, batchw, maxre, reqdelay, temp, readord, cleanm, twopass, fake, cleano) => {{
  try {{
    const realSid = (sid || sidBox || "").toString().trim();
    const clean = (v) => {{
      const s = (v === null || v === undefined) ? "" : String(v).trim();
      return (s === "null" || s === "undefined") ? "" : s;
    }};
    const data = {{
      sid: realSid,
      inp: clean(inp),
      prov: clean(prov),
      keys: clean(keys),
      model: clean(model),
      fmt: clean(fmt),
      qual: qual,
      workers: workers,
      bubbles: bubbles,
      timeout: timeout,
      batchw: batchw,
      maxre: maxre,
      reqdelay: reqdelay,
      temp: temp,
      readord: readord || "",
      cleanm: clean(cleanm) || "lama-manga",
      twopass: twopass === null || twopass === undefined ? true : !!twopass,
      fake_test: !!fake,
      clean_only: !!cleano,
      ts: Date.now()
    }};
    localStorage.setItem("{LS_KEY}", JSON.stringify(data));
    if (realSid) localStorage.setItem("manga_sid", realSid);
  }} catch (e) {{}}
  return [];
}}
"""
        save_sid_js = f"""
(sid, sidBox) => {{
  try {{
    const realSid = (sid || sidBox || "").toString().trim();
    if (realSid) {{
      localStorage.setItem("manga_sid", realSid);
      let raw = localStorage.getItem("{LS_KEY}");
      let data = {{}};
      try {{ data = raw ? JSON.parse(raw) : {{}}; }} catch (e) {{ data = {{}}; }}
      data.sid = realSid;
      data.ts = Date.now();
      localStorage.setItem("{LS_KEY}", JSON.stringify(data));
      try {{
        let jraw = localStorage.getItem("{JOB_KEY}");
        let job = jraw ? JSON.parse(jraw) : {{}};
        job.sid = realSid;
        job.ts = Date.now();
        localStorage.setItem("{JOB_KEY}", JSON.stringify(job));
      }} catch (e2) {{}}
    }}
  }} catch (e) {{}}
  return [];
}}
"""
        
        save_job_js = f"""
(sid, sidBox, btnLabel, logText) => {{
  try {{ if (window.__mangaUpdateChip) window.__mangaUpdateChip(logText, btnLabel); }} catch (e) {{}}
  try {{
    const JOB = "{JOB_KEY}";
    let prev = {{}};
    try {{ prev = JSON.parse(localStorage.getItem(JOB) || "{{}}"); }} catch (e) {{ prev = {{}}; }}
    const realSid = (sid || sidBox || "").toString().trim();
    const log = (logText || "").toString();
    const btn = (btnLabel || "").toString();
    const running = btn.indexOf("متوقف") >= 0 || btn.indexOf("⏹") >= 0;
    const prevSid = (prev.sid || "").trim();
    const prevLog = (prev.log || "").toString();
    const prevRunning = !!prev.running;

    if (prevRunning && prevSid && realSid && realSid !== prevSid) {{
      return [];
    }}
    if ((!log || log.indexOf("— لاگ بعد") === 0) && prevLog && prevLog.indexOf("— لاگ بعد") !== 0) {{
      return [];
    }}
    const done = (log || prevLog || "").indexOf("تمام شد") >= 0
      || (log || prevLog || "").indexOf("✅") >= 0
      || (log || prevLog || "").indexOf("موفق") >= 0;
    if (prevRunning && !running && !done && prevLog && log && prevLog.length >= log.length) {{
      if (log.length > prevLog.length + 10 && (!realSid || realSid === prevSid)) {{
        prev.log = log;
        prev.ts = Date.now();
        localStorage.setItem(JOB, JSON.stringify(prev));
      }}
      return [];
    }}

    let keepLog = log;
    if (prevLog && log && prevLog.length > log.length + 40) {{
      keepLog = prevLog;
    }}
    if (prevLog && (!log || log.indexOf("— لاگ بعد") === 0)) {{
      keepLog = prevLog;
    }}

    const job = {{
      sid: realSid || prevSid || "",
      log: keepLog || prevLog || "",
      btn: (running || prevRunning) ? (running ? btn : (prev.btn || btn)) : (btn || prev.btn || ""),
      running: running || (prevRunning && (!realSid || realSid === prevSid) && !btn),
      ts: Date.now()
    }};
    const done2 = (keepLog || "").indexOf("تمام شد") >= 0
      || (keepLog || "").indexOf("✅") >= 0;
    if (done2) {{
      job.running = false;
      job.btn = "🚀  شروع ترجمه";
    }} else if (!running && btn.indexOf("شروع") >= 0 && prevRunning && keepLog === prevLog) {{
      job.running = true;
      job.btn = prev.btn || "⏹  متوقف ترجمه";
      job.sid = prevSid || job.sid;
    }}
    localStorage.setItem(JOB, JSON.stringify(job));
    if (job.sid) localStorage.setItem("manga_sid", job.sid);
  }} catch (e) {{}}
  return [];
}}
"""

        load_form_js = f"""
() => {{
  try {{ window.__mangaLoadJsRan = (window.__mangaLoadJsRan || 0) + 1; }} catch (e) {{}}
  try {{
    let raw = localStorage.getItem("{LS_KEY}");
    if (!raw) {{
      raw = localStorage.getItem("manga_autotranslate_form_v1");
      if (raw) {{
        try {{ localStorage.setItem("{LS_KEY}", raw); }} catch (e) {{}}
      }}
    }}
    const sidOnly = (localStorage.getItem("manga_sid") || "").trim();
    let job = {{}};
    try {{ job = JSON.parse(localStorage.getItem("{JOB_KEY}") || "{{}}"); }} catch (e) {{ job = {{}}; }}
    const jobSid = (job.sid || "").trim();
    const bestSid = sidOnly || jobSid || "";

    if (!raw) {{
      if (bestSid) {{
        return [JSON.stringify({{
          sid: bestSid,
          ts: Date.now(),
          _jobLog: job.log || "",
          _jobBtn: job.btn || "",
          _jobRunning: !!job.running
        }})];
      }}
      return [""];
    }}
    const d = JSON.parse(raw);
    {_perm_js}
    if (!d || !d.ts || (!PERM && (Date.now() - d.ts) > {SESSION_TTL * 1000})) {{
      if (bestSid) {{
        return [JSON.stringify({{
          sid: bestSid,
          ts: Date.now(),
          _jobLog: job.log || "",
          _jobBtn: job.btn || "",
          _jobRunning: !!job.running,
          keys: d && d.keys ? d.keys : undefined,
          prov: d && d.prov ? d.prov : undefined,
        }})];
      }}
      try {{ localStorage.removeItem("{LS_KEY}"); }} catch (e) {{}}
      return [""];
    }}
    if (bestSid) d.sid = bestSid;
    d._jobLog = job.log || "";
    d._jobBtn = job.btn || "";
    d._jobRunning = !!job.running;
    return [JSON.stringify(d)];
  }} catch (e) {{
    return [""];
  }}
}}
"""

        client_restore_js = f"""
() => {{
  const KEY = "{LS_KEY}";
  const JOB = "{JOB_KEY}";
  const TTL = {SESSION_TTL * 1000};

  const setVal = (el, val) => {{
    if (!el || val === undefined || val === null) return;
    const s = String(val);
    try {{
      const proto = el.tagName === "TEXTAREA"
        ? (window.HTMLTextAreaElement && window.HTMLTextAreaElement.prototype)
        : (window.HTMLInputElement && window.HTMLInputElement.prototype);
      const desc = proto && Object.getOwnPropertyDescriptor(proto, "value");
      if (desc && desc.set) desc.set.call(el, s);
      else el.value = s;
    }} catch (e) {{ el.value = s; }}
    el.dispatchEvent(new Event("input", {{ bubbles: true }}));
    el.dispatchEvent(new Event("change", {{ bubbles: true }}));
  }};

  const findLogEl = () => {{
    return document.querySelector("#manga_live_log textarea")
      || document.querySelector('[id*="manga_live_log"] textarea')
      || (() => {{
          const areas = Array.from(document.querySelectorAll("textarea"));
          return areas.sort((a,b) => (b.rows||0)-(a.rows||0))[0] || null;
        }})();
  }};

  const findSidEl = () => {{
    return document.querySelector("#manga_sid textarea")
      || document.querySelector("#manga_sid input")
      || document.querySelector('[id*="manga_sid"] textarea')
      || document.querySelector('[id*="manga_sid"] input');
  }};

  const byId = (id) => {{
    const root = document.getElementById(id);
    if (!root) return null;
    return root.querySelector("input, textarea, select") || root;
  }};

  const apply = () => {{
    try {{
      let job = {{}};
      try {{ job = JSON.parse(localStorage.getItem(JOB) || "{{}}"); }} catch (e) {{ job = {{}}; }}
      const sidOnly = (localStorage.getItem("manga_sid") || job.sid || "").trim();
      const jobLog = (job.log || "").toString();

      if (sidOnly) {{
        const sidEl = findSidEl();
        if (sidEl) setVal(sidEl, sidOnly);
      }}

      const jobDone = (jobLog || "").indexOf("تمام شد") >= 0 || (jobLog || "").indexOf("✅") >= 0;
      if (jobDone) {{
        const forceStart = () => {{
          const roots = [document.getElementById("runbtn"), ...Array.from(document.querySelectorAll("button"))];
          for (const r of roots) {{
            if (!r) continue;
            const el = r.tagName === "BUTTON" ? r : (r.querySelector && r.querySelector("button"));
            if (!el) continue;
            const t = (el.textContent || "");
            if (t.indexOf("متوقف") >= 0 || t.indexOf("⏹") >= 0) {{
              el.textContent = "🚀  شروع ترجمه";
            }}
          }}
        }};
        forceStart();
        setTimeout(forceStart, 500);
        setTimeout(forceStart, 1500);
        try {{
          job.running = false;
          job.btn = "🚀  شروع ترجمه";
          localStorage.setItem(JOB, JSON.stringify(job));
        }} catch (e) {{}}
      }}
      if (job.running && !jobDone) {{
        const forceBtn = () => {{
          const roots = [
            document.getElementById("runbtn"),
            ...Array.from(document.querySelectorAll("button")),
          ];
          for (const r of roots) {{
            if (!r) continue;
            const b = r.tagName === "BUTTON" ? r : r.querySelector("button");
            const el = b || (r.tagName === "BUTTON" ? r : null);
            if (!el) continue;
            const t = (el.textContent || "");
            if (t.indexOf("شروع") >= 0 || t.indexOf("🚀") >= 0 || t.indexOf("متوقف") >= 0 || t.indexOf("⏹") >= 0) {{
              el.textContent = "⏹  متوقف ترجمه";
            }}
          }}
        }};
        forceBtn();
        setTimeout(forceBtn, 400);
        setTimeout(forceBtn, 1200);
        setTimeout(forceBtn, 2500);
      }}

      if (jobLog && jobLog.indexOf("— لاگ بعد") !== 0) {{
        const logEl = findLogEl();
        if (logEl) {{
          const cur = (logEl.value || "").trim();
          if (!cur || cur.indexOf("— لاگ بعد") === 0 || jobLog.length >= cur.length) {{
            setVal(logEl, jobLog);
            try {{ logEl.scrollTop = logEl.scrollHeight; }} catch (e) {{}}
          }}
        }}
      }}

      let raw = localStorage.getItem(KEY) || localStorage.getItem("manga_autotranslate_form_v1");
      {_perm_js}
      if (raw) {{
        const d = JSON.parse(raw);
        if (d && (!d.ts || PERM || (Date.now() - d.ts) <= TTL)) {{
          // v1.14.222 — کلید/مدلِ اسنپ‌شات مالِ providerِ لحظهٔ ذخیره است؛
          // اگر منو الآن رویِ providerِ دیگری است پر نمیشود تا مقادیرِ
          // کاستوم زیرِ Gemini نشان داده نشود (دستورِ سازنده: «میرم
          // Gemini مال کاستوم ک سیو زدم نشون میده»)
          let curProv = "";
          try {{
            const pe = document.querySelector("#manga_provider_row input, #manga_provider_row select, #manga_provider_row textarea");
            curProv = String((pe && pe.value) || "").trim();
          }} catch (e) {{ curProv = ""; }}
          const sameProv = !d.prov || !curProv
            || String(d.prov).trim() === curProv;
          if (sameProv) {{
            if (d.keys) {{
              const k = byId("manga_api_keys") || document.querySelector('input[type="password"]');
              if (k) setVal(k, d.keys);
            }}
            if (d.model) {{
              const m = byId("manga_model");
              if (m) setVal(m, d.model);
            }}
          }}
        }}
      }}

      // v1.14.217 — مدلهایِ سفارشیِ مرورگر → پایتون (ادغام با دیسک)
      try {{
        const cmRaw = (localStorage.getItem("manga_custom_models") || "").trim();
        if (cmRaw && cmRaw.charAt(0) === "[") {{
          const cmEl = byId("manga_cm_restore");
          if (cmEl && (cmEl.value || "") !== cmRaw) setVal(cmEl, cmRaw);
        }}
      }} catch (e) {{}}
    }} catch (e) {{ console.warn("manga restore", e); }}
  }};

  apply();
  [100, 300, 600, 1000, 2000, 3500, 5000].forEach((t) => setTimeout(apply, t));

  try {{
    const saveFromDom = () => {{
      try {{
        const logEl = findLogEl();
        if (!logEl) return;
        const log = logEl.value || "";
        if (!log || log.indexOf("— لاگ بعد") === 0) return;
        let job = {{}};
        try {{ job = JSON.parse(localStorage.getItem(JOB) || "{{}}"); }} catch (e) {{ job = {{}}; }}
        if (job.running && job.sid && job.log && job.log.length > log.length + 30) return;
        if (job.running && job.log && (!log || log.indexOf("— لاگ بعد") === 0)) return;
        const sidLs = (localStorage.getItem("manga_sid") || "").trim();
        const sid = (job.running && job.sid) ? job.sid : (sidLs || job.sid || "");
        const runRoot = document.getElementById("runbtn");
        const btn = runRoot ? (runRoot.querySelector("button") || runRoot) : null;
        const btnT = btn ? (btn.textContent || "") : "";
        const runningNow = btnT.indexOf("متوقف") >= 0 || btnT.indexOf("⏹") >= 0;
        if (job.running && !runningNow && job.log && log.length <= job.log.length + 5) {{
          return;
        }}
        if (job.log && job.log.length > log.length + 50) return;
        job.sid = sid;
        job.log = (job.log && job.log.length > log.length) ? job.log : log;
        job.ts = Date.now();
        if (btnT) {{
          job.btn = btnT;
          job.running = runningNow || !!job.running;
        }}
        localStorage.setItem(JOB, JSON.stringify(job));
        if (sid) localStorage.setItem("manga_sid", sid);
      }} catch (e) {{}}
    }};
    const obs = new MutationObserver(() => saveFromDom());
    const startObs = () => {{
      const root = document.getElementById("manga_live_log") || document.body;
      if (root) obs.observe(root, {{ childList: true, subtree: true, characterData: true }});
    }};
    startObs();
    setTimeout(startObs, 800);
    setInterval(saveFromDom, 2000);
  }} catch (e) {{}}

  const syncSidHolder = () => {{
    try {{
      let job = {{}};
      try {{ job = JSON.parse(localStorage.getItem(JOB) || "{{}}"); }} catch (e) {{ job = {{}}; }}
      const sid = (localStorage.getItem("manga_sid") || job.sid || "").trim();
      if (!sid) return;
      const el = document.querySelector("#manga_sid_holder textarea")
        || document.querySelector("#manga_sid_holder input")
        || document.querySelector('[id*="manga_sid_holder"] textarea')
        || document.querySelector('[id*="manga_sid_holder"] input');
      if (!el) return;
      if ((el.value || "").trim() === sid) return;
      setVal(el, sid);
    }} catch (e) {{}}
  }};
  syncSidHolder();
  setInterval(syncSidHolder, 1000);
  [200, 500, 1000, 2000, 4000].forEach((t) => setTimeout(syncSidHolder, t));

  // v1.14.192 — خواستهٔ سازنده (PC/لینوکس = همین رابطِ وب): «وقتی لاگ میده
  // باید خودش با لاگ بره پایین نه ثابت بمونه تا وقتی ک خودم دست نزدم
  // بخوام برم بالا». Gradio فقط هنگامِ streaming اسکرول میکند و با
  // بهروزرسانیِ poll رها میشود — اینجا دنبالکردنِ دستی: اگر کاربر
  // نزدیکِ ته است (یا دستش را نزده) با هر تغییرِ متن به ته میرود؛
  // بهمحضِ بالا بردنِ دست، دنبال کردن قطع و با برگشتن به ته وصل میشود.
  try {{
    const attachFollow = () => {{
      const ta = findLogEl();
      if (!ta || ta._mangaFollowBound) return;
      ta._mangaFollowBound = true;
      ta._mangaFollow = true;
      ta._mangaLogLen = (ta.value || "").length;
      const atBottom = () => {{
        try {{ return ta.scrollTop + ta.clientHeight >= ta.scrollHeight - 28; }}
        catch (e) {{ return true; }}
      }};
      ta.addEventListener("scroll", () => {{ ta._mangaFollow = atBottom(); }}, {{passive: true}});
      ta.addEventListener("wheel", () => {{ ta._mangaFollow = atBottom(); }}, {{passive: true}});
      ta.addEventListener("touchmove", () => {{ ta._mangaFollow = false; }}, {{passive: true}});
      ta.addEventListener("keydown", (ev) => {{
        const k = ev.key || "";
        if (k === "ArrowUp" || k === "PageUp" || k === "Home") ta._mangaFollow = false;
        if (k === "ArrowDown" || k === "PageDown" || k === "End") ta._mangaFollow = true;
      }});
      setInterval(() => {{
        const len = (ta.value || "").length;
        if (len !== ta._mangaLogLen) {{
          const reset = len < ta._mangaLogLen;
          ta._mangaLogLen = len;
          if (ta._mangaFollow || reset) {{
            try {{ ta.scrollTop = ta.scrollHeight; }} catch (e) {{}}
          }}
        }}
      }}, 300);
    }};
    attachFollow();
    [1200, 4000].forEach((t) => setTimeout(attachFollow, t));
  }} catch (e) {{}}

  // v1.14.223 — دستورِ سازنده: «کلید ک وارد میکنن بشه هاید کرد پیشفرض
  // هاید باشه زدن روش دیده بشه» — فیلدِ کلید از سمتِ سرور type="password"
  // است (پیشفرضِ مخفی) و دکمهٔ 👁 داخلِ فیلد آن را نشان/مخفی میکند
  // (gradio 6 دکمهٔ خودکارِ چشم ندارد؛ وبِ PC/لینوکس/گوشی همه همین است)
  try {{
    const attachEye = () => {{
      const kb = document.getElementById("manga_api_keys");
      if (!kb) return;
      const inp = kb.querySelector("input");
      if (!inp || inp.dataset.mangaEyeBound) return;
      inp.dataset.mangaEyeBound = "1";
      const host = inp.closest(".input-container")
        || inp.closest(".wrap") || inp.parentElement;
      if (!host) return;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "manga-eye";
      btn.setAttribute("aria-label", "نمایش / مخفی کردن کلید");
      btn.title = "نمایش / مخفی کردن کلید";
      const paint = () => {{
        inp.type = window.__mangaKeysShown ? "text" : "password";
        btn.textContent = window.__mangaKeysShown ? "🙈" : "👁";
        btn.classList.toggle("on", !!window.__mangaKeysShown);
      }};
      btn.addEventListener("click", (ev) => {{
        ev.preventDefault();
        ev.stopPropagation();
        window.__mangaKeysShown = !window.__mangaKeysShown;
        paint();
      }});
      host.appendChild(btn);
      paint();
    }};
    attachEye();
    [300, 800, 1500, 3000, 5000].forEach((t) => setTimeout(attachEye, t));
    if (!window.__mangaEyeObs) {{
      // v1.14.224 — ریشهٔ «وقتی دکمه ویرایش میزنم شکل نمایش کلید نمیاد
      // تو Gemini میاد ولی تو کاستوم خودم نمیاد»: gradio وقتی ردیفِ کلید
      // پنهان/آشکار میشود (انتخابِ مدلِ ذخیرهشده → ✎ ویرایش) فیلد را از
      // DOM میبرد و دوباره میسازد؛ آبسرورِ چسبیدهبه خودِ فیلد با فیلدِ
      // قدیمی میمیرد و چشم دیگر برنمیگردد (چشمِ Gemini در بارِ اول کار
      // میکرد چون هنوز زنده بود) — حالا همیشه به خودِ body وصل میشود که
      // هرگز از DOM نمیافتد؛ هر ساختِ دوبارهٔ فیلد چشم را برمیگرداند
      let pend = false;
      window.__mangaEyeObs = new MutationObserver(() => {{
        if (pend) return;
        pend = true;
        requestAnimationFrame(() => {{ pend = false; attachEye(); }});
      }});
      try {{
        window.__mangaEyeObs.observe(document.body,
          {{ childList: true, subtree: true }});
      }} catch (e) {{}}
    }}
  }} catch (e) {{}}

  return [];
}}
"""


        def _do_test_key(provider_v, api_keys_v, model_v, api_base_v,
                         models_v=None):
            try:
                from manga import test_api_keys, format_key_test_text
            except Exception as e:
                return gr.update(value=f"خطا در تست: {e}", visible=True)
            prov = str(provider_v or "").strip()
            if prov == "auto":
                # v1.14.218 — تستِ همهٔ مدلها (gemini + مدلهایِ کاربر)
                lines = []
                _cands = [("Gemini", "gemini", "", str(api_keys_v or ""),
                           str(model_v or ""))]
                for m in (models_v or []):
                    if isinstance(m, dict) and str(m.get("name") or "").strip():
                        _cands.append((str(m.get("name")).strip(), "custom",
                                       str(m.get("api_base") or ""),
                                       str(m.get("api_key") or ""),
                                       str(m.get("model") or "")))
                for _lb, _cp, _cb, _ck, _cm in _cands:
                    try:
                        _r = test_api_keys(_ck, _cp, _cb, model=_cm)
                        lines.append(f"—— {_lb} ——\n" + format_key_test_text(_r))
                    except Exception as _e:
                        lines.append(f"—— {_lb} ——\nخطا: {_e}")
                return gr.update(value="\n\n".join(lines), visible=True)
            # v1.14.218 — مدلِ مشخصِ کاربر از منویِ AI → resolve به فیلدهایش
            _nm = resolve_ai_named(models_v, prov,
                                   str(api_keys_v or ""), str(model_v or ""))
            if _nm is not None:
                prov, api_base_v, api_keys_v, model_v = _nm
            try:
                res = test_api_keys(api_keys_v or "", prov or "gemini",
                                    api_base_v or "", model=model_v or "")
                txt = format_key_test_text(res)
                return gr.update(value=txt, visible=True)
            except Exception as e:
                return gr.update(value=f"خطا در تست: {e}", visible=True)

        def run_translation(sid, sid_box_v, inp_path_v, upload, provider_v, api_keys_v, model_v,
                            ocr_lang_v,
                            out_fmt_v, quality_v, font_up,
                            workers_v, bubbles_v, timeout_v,
                            batchw_v, maxre_v, reqdelay_v, temp_v, readord_v,
                            clean_method_v, two_pass_v,
                            fake_test_v, clean_only_v, web_debug_v, prompt_mode_v, prompt_body_v,
                            glossary_text_v, story_brief_v, api_base_v,
                            models_v,
                            *tone_args):
            _t_prep68 = time.time()  # v1.14.68 — زمانِ آماده‌سازیِ اپ
            sid = (sid or sid_box_v or "").strip()
            sid = _find_active_sid(sid) or sid
            if not sid:
                sid = _new_sid()

            job = _get_job(sid)
            n_slots = len(tone_slots)
            tone_files = list(tone_args[:n_slots])
            tone_enables = list(tone_args[n_slots:n_slots * 2])

            def _pack(btn, log, dl=None, view=None, group=None, viewer=None, html="",
                      dl_dbg=None, view_dbg=None, dbg_row=None, html_dbg=""):
                # v1.14.31: «نمایش اصلی» و «نمایش دیباگ» برای همیشه مخفی —
                # فقط یک نمایش (دکمهٔ 📖) وجود دارد.
                return (
                    sid,
                    gr.update(value=sid),
                    gr.update(value=btn),
                    gr.update(value=log),
                    dl if dl is not None else gr.update(),
                    gr.update(visible=False),
                    group if group is not None else gr.update(),
                    viewer if viewer is not None else gr.update(),
                    html if html is not None else gr.update(),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(),
                )

            with job["lock"]:
                running_now = _job_running(job)
            if running_now:
                _kill_job(sid)
                msg = job.get("log") or "⏹ ترجمه متوقف شد.\n(پروسه manga.py بسته شد)"
                return _pack("🚀  شروع ترجمه", msg)

            up_files = upload if isinstance(upload, (list, tuple)) else (
                [upload] if upload else [])
            up_files = [u for u in up_files if u and os.path.isfile(u)]
            src = (inp_path_v or "").strip()
            multi_base = ""
            _batch_no_stitch = False  # v1.14.210 — بچِ چند-فایلی: هر فایل عینِ حالتِ تکی
            if up_files:
                if len(up_files) == 1:
                    src = up_files[0]
                else:
                    # چند فایل انتخاب شده — همه در یک پوشهٔ دسته‌ای قرار می‌گیرند
                    # و همان پوشه به‌عنوان ورودی به موتور داده می‌شود.
                    batch_dir = os.path.join(OUT_DIR, sid[:12], "input_batch")
                    shutil.rmtree(batch_dir, ignore_errors=True)
                    os.makedirs(batch_dir, exist_ok=True)
                    for bi, bf in enumerate(sorted(up_files, key=natural_key), 1):
                        ext_b = os.path.splitext(bf)[1].lower() or ".bin"
                        try:
                            shutil.copyfile(bf, os.path.join(
                                batch_dir, f"file_{bi:03d}{ext_b}"))
                        except Exception:
                            shutil.copyfile(bf, os.path.join(
                                batch_dir, f"file_{bi:03d}" + ext_b.replace(".", "_")))
                    # v1.14.210 — ریشهٔ «تکی اوکیه، دستِ جمعی خراب»: پوشهٔ بچ مسیرِ
                    # چسباندن/برشِ ۸۰۰۰px میرفت (نرمالِ عرضِ گروهی + استیچ +
                    # برش از وسطِ محتوا) — یعنی مسیری کاملاً متفاوت از حالتِ تکی.
                    # حالا فایلها «کاما-جدا» به موتور داده میشوند (=
                    # صفحاتِ مستقل، عینِ حالتِ تکی) و --stitch-max-height 0
                    # چسباندن/برش را خاموش میکند؛ فقط متنِ ردشده از مرزِ دو فایل
                    # (برشِ خوردهٔ کاربر) با ترمیمِ مرز وصل میشود، هیچ برشی از وسطِ
                    # متن زده نمیشود.
                    _bf_sorted = sorted(os.listdir(batch_dir))
                    src = ",".join(
                        os.path.join(batch_dir, _bn) for _bn in _bf_sorted)
                    _batch_no_stitch = True
                    _mb = smart_output_base(up_files[0]) or "batch"
                    multi_base = re.sub(r'[\\/:*?"<>|]+', "_", _mb)[:60] \
                        + f"_{len(up_files)}files"

            if not src:
                return _pack("🚀  شروع ترجمه",
                             "❌ ورودی خالی است — فایل آپلود کنید یا URL بدهید.")

            # v1.14.66 — اگر فونت‌هایِ لحن از استارتِ اپ جامانده‌اند (اینترنتِ
            # موقعِ استارت قطع بوده)، همین‌جا دوباره تلاش کن — نه فقط استارت.
            try:
                if any(not os.path.isfile(os.path.join(FONT_DIR, _fb[1]))
                       for _fb in FONT_BUNDLES):
                    download_fonts(log=lambda *_a: None)
            except Exception:
                pass

            font_v = font_up or find_font()
            if not font_v or not os.path.isfile(font_v):
                return _pack("🚀  شروع ترجمه",
                             "❌ فونت فارسی روی سرور نیست — یک .ttf آپلود کنید.")

            prov_s = str(provider_v or "").strip()
            # ── v1.14.218 — resolveِ منویِ AI در manga_app.py (manga.py
            # دستنخورده): «auto» = اولینِ در دسترس از [gemini + مدلهایِ کاربر]؛
            # مدلِ مشخصِ کاربر = فقط و فقط همان؛ gemini/custom = قبلی ──
            _models_now = [m for m in (models_v or [])
                           if isinstance(m, dict)
                           and str(m.get("name") or "").strip()]
            _auto_log_lines = []
            _named = resolve_ai_named(_models_now, prov_s,
                                      str(api_keys_v or ""), str(model_v or ""))
            if _named is not None:
                prov_s, api_base_v, api_keys_v, model_v = _named
                provider_v = prov_s
                _auto_log_lines.append(
                    f"🎯 مدلِ انتخابیِ شما از «لیست مدل‌ها» استفاده میشود "
                    f"(provider={prov_s}، model={str(model_v or '')[:40]}) — فقط همین.")
            elif prov_s == "auto":
                _ap, _ab, _ak, _am, _auto_log_lines = resolve_ai_auto(
                    _models_now, str(api_keys_v or ""), str(model_v or ""))
                if not _ap:
                    return _pack(
                        "🚀  شروع ترجمه",
                        "❌ حالتِ auto: هیچ مدلِ در دسترسی نبود:\n"
                        + "\n".join(_auto_log_lines)
                        + "\n   یک کلیدِ Gemini وارد کنید یا مدلِ سفارشیِ خود را "
                          "به «لیست مدل‌ها» اضافه کنید.")
                prov_s, api_base_v, api_keys_v, model_v = _ap, _ab, _ak, _am
                provider_v = prov_s
            elif prov_s and prov_s not in ("gemini", "custom"):
                # نامی که دیگر در لیست نیست (مثلاً حذفشده) → gemini
                prov_s, provider_v = "gemini", "gemini"
            if prov_s == "custom":
                _ab = normalize_api_base(str(api_base_v or ""))
                if not _ab:
                    return _pack("🚀  شروع ترجمه",
                                 "❌ provider «custom» به دامنهٔ API معتبر نیاز دارد.\n"
                                 "   مثال: https://api.example.com/v1\n"
                                 "   (https:// اگر جا افتاده باشد خودکار اضافه می‌شود.)")
                if not str(model_v or "").strip():
                    return _pack("🚀  شروع ترجمه",
                                 "❌ provider «custom» به نام مدل نیاز دارد (مثال: gpt-4o-mini).")
                api_base_v = _ab

            ext = {"PDF": ".pdf", "ZIP": ".zip", "HTML": ".html", "PSD": ".psd", "پوشهٔ تصاویر": ""}[out_fmt_v]
            base = multi_base or smart_output_base(str(src))
            user_out_dir = os.path.join(OUT_DIR, sid[:12])
            os.makedirs(user_out_dir, exist_ok=True)
            _prev_src = ""
            with job["lock"]:
                _prev_src = str(job.get("src") or "")
            # v1.14.210 — ریشهٔ «کلا نمیپاکه رد میشه»: بچِ دوباره در همان جلسه
            # srcِ یکسانی داشت (input_batch) → پوشهٔ خروجی پاک نمیشد →
            # کشِ resume سرِ جایه ماند → همهٔ صفحه‌ها «از کش» رد میشدند و
            # خروجیِ قدیمی (باگ‌دار) برمیگشت. حالا هر اجرایِ آپلودی
            # پوشهٔ خروجی را از نو پاک میکند = هر تست واقعاً از صفر
            # اجرا میشود.
            # v1.14.235 — فیکسِ «فایلِ محلیِ عکس میدم ارور میده» (No
            # connection adapters): این پاک‌سازی «همهٔ» زیرپوشه‌های
            # user_out_dir را برمیداشت — از جمله input_batch که فایلهایِ
            # ورودیِ «همین» اجرا چند خط بالاتر در آن کپی شده بودند!
            # موتور بعداً مسیرها را «نبود» میدید → C:\… به requests
            # سپرده میشد → «No connection adapters were found for
            # 'C:\…\file_001.jpg'» → «هیچ تصویری دانلود نشد».
            # input_batch از پاک‌سازی مستثنی شد — در هر اجرا فقط وقتی
            # آپلودِ چندفایلی باشد از نو ساخته میشود، پس محتوایش همیشه
            # تازه است و کشِ کهنه در آن معنا ندارد؛ بقیهٔ زیرپوشه‌ها
            # (کشِ resume/خروجی/…) مثل قبل کامل پاک میشوند = v1.14.210
            # سرِ جایش میماند.
            if up_files or (_prev_src and _prev_src != str(src)):
                try:
                    for _n in os.listdir(user_out_dir):
                        if _n == "input_batch":
                            continue
                        _p = os.path.join(user_out_dir, _n)
                        if os.path.isdir(_p):
                            shutil.rmtree(_p, ignore_errors=True)
                        else:
                            try:
                                os.remove(_p)
                            except Exception:
                                pass
                except Exception:
                    pass
            out_v = os.path.join(user_out_dir, base + ext)

            cmd = [sys.executable, "-u", MANGA_PY, "-i", str(src), "-o", out_v,
                   "--font", font_v,
                   "--provider", provider_v,
                   "--workers", str(int(workers_v)),
                   "--bubbles-per-request", str(int(bubbles_v)),
                   "--api-timeout", str(int(timeout_v)),
                   "--quality", str(int(quality_v)),
                   "--batch-workers", str(int(batchw_v)),
                   "--max-retries", str(int(maxre_v)),
                   "--request-delay", str(float(reqdelay_v)),
                   "--temperature", str(float(temp_v)),
                   "--reading-order", str(readord_v)]
            if prov_s == "custom" and str(api_base_v or "").strip():
                cmd += ["--api-base", str(api_base_v).strip()]
            cmd += font_args()
            active_tones = ["normal"]
            for si, slot in enumerate(tone_slots):
                fp = tone_files[si] if si < len(tone_files) else None
                en = tone_enables[si] if si < len(tone_enables) else True
                if not en:
                    continue
                if not fp:
                    bundle = next((b for b in FONT_BUNDLES if b[0] == slot), None)
                    if bundle:
                        srv = os.path.join(FONT_DIR, bundle[1])
                        if os.path.isfile(srv):
                            fp = srv
                if fp and os.path.isfile(fp):
                    _cli = {"free_text": "free"}
                    cmd += ["--font-" + _cli.get(slot, slot.replace("_", "-")), fp]
                    if slot not in active_tones:
                        active_tones.append(slot)
            if active_tones:
                cmd += ["--active-tones", ",".join(active_tones)]
            klist = [k.strip() for k in (api_keys_v or "").replace(";", ",").split(",") if k.strip()]
            if klist:
                cmd += ["--api-key", ",".join(klist)]
            if ocr_lang_v and str(ocr_lang_v).strip() and str(ocr_lang_v).strip() != "en":
                cmd += ["--ocr-lang"] + [p for p in str(ocr_lang_v).split() if p]
            if model_v and str(model_v).strip():
                cmd += ["--model", str(model_v).strip()]
            _cm_v = str(clean_method_v or "lama-manga").strip()
            if _cm_v not in ("lama-manga", "lama-big", "opencv"):
                _cm_v = "lama-manga"
            cmd += ["--clean-method", _cm_v]
            if _batch_no_stitch:
                # v1.14.210 — بچِ آپلودی: چسباندن/برشِ ۸۰۰۰px خاموش — هر فایل
                # مثلِ حالتِ تکی پردازش میشود
                cmd += ["--stitch-max-height", "0"]
            if not two_pass_v:
                cmd += ["--no-two-pass-ocr"]
            if fake_test_v:
                cmd += ["--fake-translate"]
            if clean_only_v:
                cmd += ["--clean-only"]
            if web_debug_v:
                cmd += ["--debug"]
            instr_text = str(prompt_body_v or "").strip()
            if is_custom_instruction(instr_text):
                instr_path = os.path.join(user_out_dir, "instruction_user.txt")
                with open(instr_path, "w", encoding="utf-8") as _inf:
                    _inf.write(instr_text + "\n")
                cmd += ["--instruction", instr_path]
            cmd += ["--prompt-mode", sanitize_prompt_mode(prompt_mode_v)]
            glos_text = str(glossary_text_v or "").strip()
            if glos_text:
                glos_path = os.path.join(user_out_dir, "glossary_user.txt")
                with open(glos_path, "w", encoding="utf-8") as _gf:
                    _gf.write(glos_text + "\n")
                cmd += ["--glossary", glos_path]
            if not story_brief_v:
                cmd += ["--no-brief"]

            t0 = time.time()
            try:
                print(f"[TIME] app-prep={time.time() - _t_prep68:.1f}s",
                      flush=True)  # v1.14.68
            except Exception:
                pass
            with job["lock"]:
                job["result_visible"] = False
                job["download_path"] = None
                job["download_debug"] = None
                job["html_state"] = ""
                job["html_debug"] = ""
                job["reader_path"] = None
                job["reader_debug_path"] = None
                job["buf"] = []
                job["t0"] = t0
                job["returncode"] = None
                job["done_event"] = False
                job["out_v"] = out_v
                job["src"] = src
                job["running"] = True
                job["log"] = ("\n".join(_auto_log_lines) + "\n"
                              if _auto_log_lines else "") + "▶ در حال شروع…"
                job["ts"] = time.time()
            # v1.14.200 — سطرِ اولِ لاگِ کامل: نسخه + زمانِ شروع — برایِ
            # گزارشِ باگِ سازنده لازم است (فایلِ کامل از همینجا بسته میشود).
            _append_job_logfile(
                sid, f"═══ Manga-AutoTranslate v{APP_VER} — شروعِ کارِ جدید — "
                     f"{time.strftime('%Y-%m-%d %H:%M:%S')} ═══")
            if _auto_log_lines:
                _append_job_logfile(sid, "\n".join(_auto_log_lines))

            live_dir = os.path.join(user_out_dir, "live")
            shutil.rmtree(live_dir, ignore_errors=True)
            os.makedirs(live_dir, exist_ok=True)
            # v1.14.159 — فیکسِ «دکمهٔ دیباگ فعال نیست ولی می‌آید»: پوشهٔ
            # live_debug فقط وقتی ساخته/پاس داده میشود که کاربر «حالت دیباگ»
            # را روشن کرده باشد؛ قبلاً همیشه ساخته میشد → دکمهٔ 🔍 دیباگِ
            # خوانندهٔ زنده همیشه میآمد ولی هیچ‌وقت چیزی نشان نمیداد.
            _dbg_on = bool(web_debug_v)
            live_dbg_dir = ""
            if _dbg_on:
                live_dbg_dir = os.path.join(user_out_dir, "live_debug")
                shutil.rmtree(live_dbg_dir, ignore_errors=True)
                os.makedirs(live_dbg_dir, exist_ok=True)
            try:
                _write_live_reader(live_dir, dbg_dir=live_dbg_dir)
            except Exception as _e:
                print(f"[!] نوشتن live_reader.html ناموفق: {_e}")
            with job["lock"]:
                job["live_dir"] = live_dir
                job["live_dbg_dir"] = live_dbg_dir or None
                job["live_files"] = []

            _env = os.environ.copy()
            _env["PYTHONUNBUFFERED"] = "1"
            _env["PYTHONIOENCODING"] = "utf-8"
            # v1.14.181 — دکمهٔ «تستِ سرعت» حذف شد؛ کلیدِ محیطیِ کهنهٔ
            # نشستهایِ قبلی هم پاک میشود تا مسیرِ آزمایشگاه بیدار نشود.
            _env.pop("MANGA_SPEED_TEST", None)
            _env["MANGA_LIVE_DIR"] = live_dir
            if _dbg_on:
                _env["MANGA_LIVE_DEBUG_DIR"] = live_dbg_dir
            try:
                proc = subprocess.Popen(
                    cmd, cwd=HERE, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    env=_env,
                    bufsize=0,
                    start_new_session=True,
                )
            except Exception as e:
                with job["lock"]:
                    job["running"] = False
                    job["log"] = f"❌ اجرا نشد: {e}"
                _append_job_logfile(sid, f"❌ اجرا نشد: {e}")
                return _pack("🚀  شروع ترجمه", job["log"])

            with job["lock"]:
                job["proc"] = proc
                job["running"] = True
                job["ts"] = time.time()
                job["log"] = (("\n".join(_auto_log_lines) + "\n")
                              if _auto_log_lines else "") \
                    + "▶ شروع شد — لاگ زنده به‌زودی…\n(اگر صفحه را رفرش کنید لاگ از همین جلسه برمی‌گردد)"
            _persist_job_meta(sid)
            _start_job_reader(sid, proc, t0)

            return _pack(
                "⏹  متوقف ترجمه", job["log"],
                dl=gr.update(visible=False),
                view=gr.update(visible=False),
                group=gr.update(visible=False),
                dl_dbg=gr.update(visible=False),
                view_dbg=gr.update(visible=False),
                dbg_row=gr.update(visible=False),
            )

        def _on_provider_change(p, models, bank, cur_base, cur_key, cur_model):
            """v1.14.222 — رفتارِ منو:
            (۱) دستورِ سازنده «افزودن ai فقط تو کاستوم بیاد نه بقیه چیزاش» →
            دکمهٔ «+ افزودن» و راهنما فقط رویِ custom دیده میشوند.
            (۲) رویِ «auto» هیچ فیلدی نمیماند («وقتی رو auto بزارن اونجا نشه
            مدلی چیزی وارد کرد») و رویِ مدلِ نامی هم فیلدها پنهاناند —
            مشخصاتش (لینک/کلید/مدل) فقطخواندنی زیرِ منو میآید («لینکش هم
            باید نشون بده»).
            (۳) بانکِ حافظه: هر provider (gemini/custom) مقادیرِ فیلدهایِ
            خودش را دارد — رفتن به Gemini دیگر مقادیرِ کاستوم را نشان
            نمیدهد («میرم Gemini مال کاستوم ک سیو زدم نشون میده»)؛ مقادیرِ
            providerِ جدید همیشه از بانک میآید (بانکِ خالی = فیلدهایِ خالی).
            v1.14.223 — «✎ ویرایش» فقط رویِ مدلِ ذخیرهشدهٔ خودِ کاربر میآید
            و هر تغییرِ منو حالتِ ویرایش را لغو میکند («💾 ذخیرهٔ ویرایش»
            پنهان میشود)."""
            bank = dict(bank or {})
            v = str(p or "").strip()
            on_auto = (v == "auto")
            is_custom = (v == "custom")
            mine = v in _cm_names(models)
            last = str(bank.get("_last") or "").strip()
            # ذخیرهٔ مقادیرِ فعلی مالِ providerِ قبلی (فقط gemini/custom —
            # رویِ auto/مدلِ نامی فیلدها پنهاناند و چیزی برایِ ذخیره نیست)
            if last in ("gemini", "custom") and last != v:
                bank[last] = {"base": str(cur_base or ""),
                              "key": str(cur_key or ""),
                              "model": str(cur_model or "")}
            bank["_last"] = v
            # v1.14.222 — مقادیرِ providerِ جدید همیشه از بانک میآید (بانکِ
            # خالی = فیلدهای خالی) — هرگز مقادیرِ providerِ قبلی زیرِ منویِ
            # جدید نمیماند («میرم Gemini مال کاستوم ک سیو زدم نشون میده»)
            saved = bank.get(v) if v in ("gemini", "custom") else {}
            saved = saved if isinstance(saved, dict) else {}
            nb = str(saved.get("base") or "")
            nk = str(saved.get("key") or "")
            nm = str(saved.get("model") or "")
            if not is_custom:
                nb = ""   # دامنهٔ API فقط مالِ custom است
            if on_auto or mine:
                nk, nm = "", ""   # رویِ auto/مدلِ نامی فیلدی برایِ ورود نیست
            info = _cm_info_html(models, v) if mine else ""
            row_vis = not on_auto and not mine
            # v1.14.231 — لیبلِ فیلدِ مدل به ازایِ هر provider: رویِ Gemini
            # دراپ‌داونِ زنده + ↻؛ بقیه (custom/ویرایشِ مدلِ نامی) دستی —
            # «بقیش باید دستی مینوشتن»؛ ↻ هم فقط رویِ gemini دیده میشود
            # v1.14.232 — فیکسِ «وقتی میرم کاستوم مدلهایِ gemini نشون
            # میده فقط باید رو خودش میومد»: منویِ دراپ‌داون رویِ هر
            # providerِ غیرِ gemini خالی میشود (choices=[]) تا مدلهایِ
            # Gemini فقط و فقط در خودِ Gemini دیده شوند؛ رویِ Gemini
            # لیستِ آفلاینِ داخلِ کد برمیگردد (دستور: «مدل هارو افلاین
            # هم بزار»).
            if v == "gemini":
                mdl_label = ("مدل — Gemini: فهرستِ آفلاین آماده است؛ ↻ برای "
                             "فهرستِ زنده (یا خودت بنویس) | خالی = پیش‌فرض")
                mdl_upd = gr.update(visible=True, value=nm, label=mdl_label,
                                    choices=_gemini_offline_models())
            else:
                mdl_label = "مدل — شناسهٔ مدل را دستی بنویس | خالی = پیش‌فرض"
                mdl_upd = gr.update(visible=row_vis, value=nm,
                                    label=mdl_label, choices=[])
            return (gr.update(visible=is_custom, value=nb),
                    gr.update(visible=row_vis),
                    gr.update(visible=row_vis, value=nk),
                    mdl_upd,
                    gr.update(visible=is_custom),
                    gr.update(visible=is_custom),
                    gr.update(visible=mine, value=info),
                    gr.update(visible=mine),
                    bank,
                    gr.update(visible=mine),    # cm_edit_btn (v1.14.223)
                    gr.update(visible=False),   # cm_save_btn — خروج از ویرایش
                    gr.update(visible=(v == "gemini")))  # ↻ فقط Gemini (231)

        # ── v1.14.223 — ویرایشِ مدلِ ذخیرهشده ─────────────────────
        def _cm_edit_start(prov, models):
            """دستورِ سازنده: «چیزی ک سیو زده بود بتونن ویرایش کنن ... با
            قابلیت ویرایش ویرایش زدن گزینه سیو بیاد» — با «✎ ویرایش»
            مقادیرِ ذخیرهشدهٔ مدلِ انتخابشده (لینک/کلید/مدل) در فیلدها
            بارگذاری میشود، «افزودن» پنهان و «💾 ذخیرهٔ ویرایش» میآید."""
            nm = str(prov or "").strip()
            m = next((x for x in (models or [])
                      if str(x.get("name") or "").strip() == nm), None)
            if not m:
                return (gr.update(),) * 9
            return (gr.update(visible=True,
                              value=str(m.get("api_base") or "")),
                    gr.update(visible=True),
                    gr.update(visible=True,
                              value=str(m.get("api_key") or "")),
                    gr.update(visible=True,
                              value=str(m.get("model") or ""),
                              label="مدل — شناسهٔ مدل را دستی بنویس | خالی = پیش‌فرض",
                              choices=[]),  # v1.14.232 — ویرایشِ مدلِ نامی هم دستی؛ منویِ Gemini نمیآید
                    gr.update(visible=False),   # «+ افزودن» پنهان
                    gr.update(visible=False),   # «✎ ویرایش» پنهان
                    gr.update(visible=True),    # «💾 ذخیرهٔ ویرایش»
                    gr.update(visible=False),   # راهنما
                    gr.update(visible=False))   # ↻ مدل — دستی (v1.14.231)

        def _cm_save_edits(prov, models, base, key, mdl):
            """«💾 ذخیرهٔ ویرایش»: همان مدلِ انتخابشده با مقادیرِ جدیدِ
            فیلدها بهروزرسانی میشود (نام عوض نمیشود)؛ بعد برگشت به حالتِ
            نمایش (فیلدها پاک/پنهان، مشخصاتِ زیرِ منو تازه میشود)."""
            nm = str(prov or "").strip()
            new_models = [dict(x) for x in (models or [])]
            idx = next((i for i, x in enumerate(new_models)
                        if str(x.get("name") or "").strip() == nm), -1)
            if idx < 0 or not nm:
                # v1.14.239 — فیکسِ همان رده: فهرستِ خروجیها ۱۵ مؤلفه
                # دارد (پایین: cm_save_btn.click) ولی این شاخه ۱۴ برمیگرداند.
                return (gr.update(),) * 15
            entry = {"name": nm,
                     "api_base": str(base or "").strip(),
                     "api_key": str(key or "").strip(),
                     "model": str(mdl or "").strip()}
            new_models[idx] = entry
            _link = entry["api_base"] or "Gemini رسمی (بدونِ دامنهٔ سفارشی)"
            _mdl = f" — مدلِ هوش: {entry['model']}" if entry["model"] else ""
            msg = (f"✅ ویرایشِ «{nm}» ذخیره شد — لینک: {_link}{_mdl}"
                   + (" (روی دیسک)" if not _web_host()
                      else " (در مرورگرِ شما)"))
            return (*_cm_pack(new_models, nm),
                    gr.update(visible=True,
                              value=_cm_info_html(new_models, nm)),
                    gr.update(visible=False),            # ذخیرهٔ ویرایش
                    gr.update(visible=True),             # ✎ ویرایش
                    gr.update(visible=False, value=""),  # دامنهٔ API
                    gr.update(visible=False),            # ردیفِ کلید/مدل
                    gr.update(visible=False, value=""),  # کلید
                    gr.update(visible=False, value=""),  # مدل
                    gr.update(visible=False),            # افزودن
                    gr.update(visible=False),            # راهنما
                    gr.update(value=msg, visible=True),
                    gr.update(visible=False))            # ↻ مدل (v1.14.231)

        try:
            provider.change(
                _on_provider_change,
                inputs=[provider, custom_models_state, fields_bank,
                        api_base, api_keys, model],
                outputs=[api_base, api_row, api_keys, model,
                         add_model_btn, cm_hint_md, cm_info_md,
                         cm_del_btn, fields_bank,
                         cm_edit_btn, cm_save_btn, model_ref_btn],
                api_name="toggle_custom_base",
            )
        except Exception:
            pass
        # v1.14.231 — گاردِ سمتِ مرورگر برایِ دکمهٔ «↻ مدل‌ها»: در gradio 6
        # گاهی updateِ visibleِ دکمهٔ داخلِ ردیفِ کلید/مدل اعمال نمیشود
        # (سرور visible=False میفرستد ولی DOM دکمه را نشان میدهد — باتِ
        # «انتخاب مدل فقط تو Gemini») — این رویدادِ JSِ محضِ بعدِ همان
        # provider.change، نمایشِ دکمه را مستقیم در DOM تنظیم میکند:
        # فقط رویِ gemini دیده شود؛ رویِ custom فقط تایپِ دستی؛ رویِ
        # auto/مدلِ نامی هم ردیفِ کلید/مدل پنهان است.
        try:
            provider.change(
                fn=None,
                inputs=[provider],
                outputs=None,
                js="""(p) => {
  try {
    const b = document.getElementById('manga_model_ref');
    if (b) b.style.display = (String(p || '').trim() === 'gemini') ? '' : 'none';
  } catch (e) {}
}""",
            )
        except Exception:
            pass

        # ── v1.14.229 — ↻ فهرستِ مدل‌ها از خودِ سرویس (دستورِ سازنده:
        # «مدلای موجود تو gemini نشون بده طرف انتخاب کنه») ──
        def _refresh_model_list(provider_v, api_keys_v, api_base_v, model_v):
            try:
                from manga import list_provider_models
            except Exception as e:
                raise gr.Error(f"خطا در بارگذاری: {str(e)[:80]}")
            prov = str(provider_v or "").strip()
            if prov in ("", "auto"):
                raise gr.Error("روی «auto» مدلی وارد نمیشود — یک سرویس انتخاب کنید.")
            # مدلِ نامی (مدلهایِ من) → مشخصاتِ ذخیرهشدهٔ خودش
            _nm = None
            try:
                _nm = resolve_ai_named(custom_models_state.value, prov,
                                       str(api_keys_v or ""),
                                       str(model_v or ""))
            except Exception:
                pass
            if _nm is not None:
                _p, _b, _k, _m = _nm
                prov, api_base_v, api_keys_v = _p, _b, _k
            models, err = list_provider_models(
                prov, str(api_keys_v or ""), str(api_base_v or ""))
            keep = str(model_v or "").strip()
            # v1.14.232 — دستورِ سازنده: «اگ اپدیتی چیزی شد خودشون رفرش
            # میزنن» → ↻ فهرستِ زنده میگیرد؛ اگر اتصال/کلید برقرار نشد،
            # به‌جای خطا، فهرستِ آفلاینِ داخلِ کد برمیگردد (کاربر بی‌درنگ
            # گزینه دارد) و دلیلِ قطعی در لیبل میآید.
            if not models:
                if prov == "gemini":
                    offline = _gemini_offline_models()
                    _why = f" — {str(err or '')[:60]}" if err else ""
                    return gr.update(
                        choices=offline,
                        value=keep,
                        label=(f"مدل — اتصال برقرار نشد{_why}؛ فهرستِ "
                               f"آفلاینِ برنامه ({len(offline)} مدل)"))
                raise gr.Error(err or "مدلی پیدا نشد — کلید/لینک را با «تست کلیدها / لینک» چک کنید.")
            return gr.update(choices=models,
                             value=keep if keep in models else keep,
                             label=f"مدل — {len(models)} مدلِ زنده پیدا شد؛ انتخاب کن")

        try:
            model_ref_btn.click(
                _refresh_model_list,
                inputs=[provider, api_keys, api_base, model],
                outputs=[model],
                api_name="refresh_models", show_progress="full")
        except Exception:
            pass

        # ── v1.14.217/218/219 — رویدادهایِ مدیرِ مدلهایِ سفارشی ──
        # v1.14.219 — دراپ‌داونِ «انتخاب مدل» و دکمههایِ ⬆/⬇/🗑 حذف شدند؛
        # _cm_pack دیگر خروجیِ cm_pick ندارد (۴تایی است).
        def _cm_pack(models, prov_cur=None):
            """v1.14.221 — (مدلها، JSONِ مرورگر، منویِ AI، ✖ِ کنارِ منو).
            مقدارِ نهاییِ منو = انتخابِ فعلی اگر هنوز معتبر است؛ وگرنه
            «auto» اگر مدلی داریم وگرنه «gemini»."""
            models = list(models or [])
            save_custom_models(models)
            _ch = _ai_choices(models)
            _cur = str(prov_cur if prov_cur is not None else "").strip()
            _val = _cur if _cur in _ch else ("auto" if "auto" in _ch
                                             else "gemini")
            return (models,
                    json.dumps(models, ensure_ascii=False),
                    gr.update(choices=_ch, value=_val),
                    gr.update(visible=_val in _cm_names(models)))

        def _cm_add_box(raw, models, prov_cur):
            """v1.14.218 — دکمهٔ «+ افزودن به لیست مدل‌ها»: مرورگر مدلِ فعلی
            (نامِ دلخواه + دامنه + کلید + شناسهٔ مدل) را میفرستد؛ نامِ تکراری
            = بهروزرسانیِ همان مدل. مدل کنارِ Gemini در لیست می‌ماند (دیسک در
            اجرایِ محلی، localStorage مرورگر در وب) و در منویِ AI هم می‌آید."""
            try:
                it = json.loads(raw) if raw else {}
            except Exception:
                it = {}
            name = str((it or {}).get("name") or "").strip() \
                if isinstance(it, dict) else ""
            if not name:
                return (*_cm_pack(models, prov_cur), gr.update())
            entry = {"name": name,
                     "api_base": str(it.get("api_base") or "").strip(),
                     "api_key": str(it.get("api_key") or "").strip(),
                     "model": str(it.get("model") or "").strip()}
            models = [m for m in (models or [])
                      if str(m.get("name") or "") != name]
            models.append(entry)
            # v1.14.222 — دستورِ سازنده: «وقتی یک چیز کاستوم سیو میکنم لینکش
            # هم باید نشون بده» — پیامِ ذخیره لینکِ مدل را هم نشان میدهد
            _link = entry["api_base"] or "Gemini رسمی (بدونِ دامنهٔ سفارشی)"
            _mdl = f" — مدلِ هوش: {entry['model']}" if entry["model"] else ""
            return (*_cm_pack(models, prov_cur),
                    gr.update(value=(f"✅ مدلِ «{name}» ذخیره شد — لینک: {_link}"
                                     f"{_mdl}"
                                     + (" (روی دیسک)" if not _web_host()
                                        else " (در مرورگرِ شما)")),
                              visible=True))

        def _cm_del_selected(prov, models):
            """v1.14.221 — ضربدرِ ✖ِ کنارِ منویِ انتخابِ AI: مدلِ «انتخابشده»
            را از لیست و منو پاک میکند (localStorage مرورگر با changeِ
            cm_json_box همگام میماند)."""
            nm = str(prov or "").strip()
            models = [m for m in (models or [])
                      if str(m.get("name") or "") != nm] if nm \
                else list(models or [])
            return _cm_pack(models, None)

        def _cm_restore(raw, models, prov_cur):
            """v1.14.217 — بازگردانیِ مدلها از localStorage مرورگر (وب) —
            فقط وقتی چیزِ بیشتری از دیسک دارد ادغام میشود."""
            try:
                data = json.loads(raw) if raw else []
            except Exception:
                data = []
            if not isinstance(data, list) or not data:
                return _cm_pack(models, prov_cur)
            merged = list(models or [])
            for it in data:
                if not isinstance(it, dict):
                    continue
                name = str(it.get("name") or "").strip()
                if not name or any(str(m.get("name") or "") == name
                                   for m in merged):
                    continue
                merged.append({"name": name,
                               "api_base": str(it.get("api_base") or ""),
                               "api_key": str(it.get("api_key") or ""),
                               "model": str(it.get("model") or "")})
            return _cm_pack(merged, prov_cur)

        # v1.14.218 — جاوااسکریپتِ دکمهٔ «+ افزودن به لیست مدل‌ها»: نام را با
        # پنجرهٔ prompt میپرسد (خالی = نامِ خودِ مدل)، در localStorage مینویسد
        # و از کانالِ manga_cm_add_box به سرور میدهد تا لیست + منویِ AI شود.
        # v1.14.220 — دکمه مستقل از custom شد: provider از ورودیِ رویداد
        # میآید؛ «دامنهٔ API» فقط وقتی provider=custom است در مدل ثبت
        # میشود (چون در بقیهٔ حالتها فیلدش از DOM پنهان است).
        _cm_add_js = """
(prov) => {
  try {
    const gv = (id) => {
      try {
        const root = document.getElementById(id);
        if (!root) return "";
        const el = root.querySelector("input, textarea") || root;
        return String((el.value || "")).trim();
      } catch (e) { return ""; }
    };
    const onCustom = String(prov || "").trim() === "custom";
    const base = onCustom ? gv("manga_api_base") : "";
    const key = gv("manga_api_keys");
    const mdl = gv("manga_model");
    if (!base && !mdl && !key) {
      try { alert("اول «مدل» و «کلیدهای API» را پر کنید، بعد «+ افزودن به لیست مدل‌ها» را بزنید."); } catch (e) {}
      return [];
    }
    let nm = "";
    try { nm = String(window.prompt("نامِ این مدل در لیست (خالی = نامِ خودِ مدل):", mdl) || "").trim(); } catch (e) { nm = ""; }
    if (!nm) nm = mdl;
    if (!nm) {
      try { alert("نامِ مدل خالی ماند — اول فیلدِ «مدل» را پر کن یا یک نام بنویس."); } catch (e) {}
      return [];
    }
    let list = [];
    try { list = JSON.parse(localStorage.getItem("manga_custom_models") || "[]") || []; } catch (e) { list = []; }
    if (!Array.isArray(list)) list = [];
    list = list.filter((m) => m && m.name !== nm);
    list.push({ name: nm, api_base: base, api_key: key, model: mdl });
    try { localStorage.setItem("manga_custom_models", JSON.stringify(list)); } catch (e) {}
    try {
      const box = document.getElementById("manga_cm_add_box");
      const el = box ? (box.querySelector("textarea") || box.querySelector("input") || box) : null;
      if (el) {
        const s = JSON.stringify({ name: nm, api_base: base, api_key: key, model: mdl });
        const proto = el.tagName === "TEXTAREA"
          ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
        const desc = proto && Object.getOwnPropertyDescriptor(proto, "value");
        if (desc && desc.set) desc.set.call(el, s); else el.value = s;
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
      }
    } catch (e) {}
  } catch (e) {}
  return [];
}
"""

        try:
            add_model_btn.click(
                fn=None, inputs=[provider], outputs=None, js=_cm_add_js)
        except Exception:
            pass
        try:
            cm_add_box.change(
                _cm_add_box,
                inputs=[cm_add_box, custom_models_state, provider],
                outputs=[custom_models_state, cm_json_box, provider,
                         cm_del_btn, backup_status],
                api_name="cm_add")
        except Exception:
            pass
        try:
            cm_del_btn.click(
                _cm_del_selected,
                inputs=[provider, custom_models_state],
                outputs=[custom_models_state, cm_json_box, provider,
                         cm_del_btn],
                api_name="cm_del_sel")
        except Exception:
            pass
        # ── v1.14.223 — ویرایشِ مدلِ ذخیرهشده ──
        try:
            cm_edit_btn.click(
                _cm_edit_start,
                inputs=[provider, custom_models_state],
                outputs=[api_base, api_row, api_keys, model,
                         add_model_btn, cm_edit_btn, cm_save_btn,
                         cm_hint_md, model_ref_btn],
                api_name="cm_edit", show_progress="hidden")
        except Exception:
            pass
        try:
            cm_save_btn.click(
                _cm_save_edits,
                inputs=[provider, custom_models_state, api_base, api_keys,
                        model],
                outputs=[custom_models_state, cm_json_box, provider,
                         cm_del_btn, cm_info_md, cm_save_btn, cm_edit_btn,
                         api_base, api_row, api_keys, model,
                         add_model_btn, cm_hint_md, backup_status,
                         model_ref_btn],
                api_name="cm_save_edits", show_progress="hidden")
        except Exception:
            pass
        try:
            # مرورگرِ وب: هر تغییرِ فهرست → localStorage
            # v1.14.222 — بعدِ حذف/افزودن، اگر متنِ نمایشیِ منویِ AI مدلی
            # باشد که دیگر در فهرست نیست (باگِ نمایشیِ gradio 6 — مقدارِ
            # سرور درست است ولی برچسبِ منو کهنه میماند)، همان لحظه به
            # فالبکِ درست (auto با مدل، وگرنه gemini) برمیگردد
            cm_json_box.change(
                fn=None, inputs=[cm_json_box], outputs=[],
                js="""(js) => {
  try {
    if (js && js.trim().charAt(0) === '[')
      localStorage.setItem('manga_custom_models', js);
  } catch (e) {}
  try {
    let list = [];
    try { list = JSON.parse(js || '[]') || []; } catch (e) { list = []; }
    if (!Array.isArray(list)) list = [];
    const names = list.map((m) => String((m && m.name) || '').trim())
                      .filter(Boolean);
    const inp = document.querySelector('#manga_provider_row input, #manga_provider_row select');
    if (inp) {
      const cur = String(inp.value || '').trim();
      const valid = ['auto', 'gemini', 'custom'].concat(names);
      if (cur && valid.indexOf(cur) < 0) {
        const fb = names.length ? 'auto' : 'gemini';
        try {
          inp.focus();
          const d = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value');
          if (d && d.set) d.set.call(inp, fb); else inp.value = fb;
          inp.dispatchEvent(new Event('input', {bubbles: true}));
          inp.dispatchEvent(new KeyboardEvent('keydown',
            {key: 'Enter', bubbles: true}));
          inp.dispatchEvent(new Event('change', {bubbles: true}));
          inp.blur();
        } catch (e2) {}
      }
    }
  } catch (e) {}
  return [];
}""")
            # بارگذاریِ صفحه: مدلهایِ مرورگر → پایتون (ادغام با دیسک)
            cm_restore_box.change(
                _cm_restore,
                inputs=[cm_restore_box, custom_models_state, provider],
                outputs=[custom_models_state, cm_json_box, provider,
                         cm_del_btn],
                api_name="cm_restore")
        except Exception:
            pass

        # ── v1.14.217/218 — پشتیبان‌گیری/بازیابی: «چیزای ک وارد کردن بکاپ
        # بگیره از مدل بگیرع تا تنظیماتشون» — دکمهٔ «گرفتن بکاپ» جدا از
        # Import؛ داخلِ بکاپ همه‌چیز است (لیستِ مدلها + تمامِ تنظیمات) ──
        _BACKUP_FIELDS = [
            ("provider", provider), ("api_base", api_base),
            ("api_keys", api_keys), ("model", model),
            ("ocr_lang", ocr_lang), ("out_fmt", out_fmt),
            ("quality", quality), ("workers", workers),
            ("bubbles", bubbles), ("timeout", timeout),
            ("batchw", batchw), ("maxre", maxre),
            ("reqdelay", reqdelay), ("temp", temp), ("readord", readord),
            ("clean_method", clean_method), ("two_pass", two_pass),
            ("fake_test", fake_test), ("clean_only", clean_only),
            ("web_debug", web_debug), ("prompt_mode", prompt_mode),
            ("prompt_body", prompt_preview_body),
            ("glossary_text", glossary_text), ("story_brief", story_brief),
        ]

        def _do_backup(*args):
            try:
                import datetime as _dt
                n = len(_BACKUP_FIELDS)
                settings = {k: (v if isinstance(v, (int, float, bool))
                                else str(v or ""))
                            for (k, _), v in zip(_BACKUP_FIELDS, args[:n])}
                models = list(args[n] or [])
                payload = {
                    "_type": "manga_autotranslate_backup",
                    "app_ver": APP_VER,
                    "exported_at": _dt.datetime.now().isoformat(timespec="seconds"),
                    "custom_models": models,
                    "settings": settings,
                }
                ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                path = os.path.join(WORK_DIR, f"manga_backup_{ts}.json")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                # v1.14.219 — دانلودِ خودکار: فایلِ خروجی در backup_out ست
                # میشود و JSِ رویِ changeِ آن بلافاصله دانلودش میکند
                return (gr.update(value=path, visible=True),
                        gr.update(value=f"✅ پشتیبان ساخته شد و دانلودِ خودکارش "
                                        f"شروع شد: {len(models)} مدل + "
                                        f"{len(settings)} تنظیم."
                                        f"\n(اگر مرورگرتان دانلود را بلاک کرد، "
                                        f"از کارتِ «فایلِ پشتیبان» همین‌جا "
                                        f"دستیش کنید.)",
                                  visible=True))
            except Exception as e:
                return (gr.update(),
                        gr.update(value=f"❌ پشتیبان ناموفق: {e}", visible=True))

        def _do_import(file_info, models_cur, prov_cur, bank_cur):
            import datetime as _dt
            n = len(_BACKUP_FIELDS)
            ups = [gr.update()] * n
            bank_up = gr.update()
            try:
                path = (file_info or "").strip() if isinstance(file_info, str) \
                    else (file_info.get("name") if isinstance(file_info, dict) else "")
                # gr.File با type=filepath مسیرِ موقت را میدهد
                if isinstance(file_info, str):
                    path = file_info
                elif isinstance(file_info, dict):
                    path = file_info.get("name") or ""
                if not path or not os.path.isfile(path):
                    return (*ups, gr.update(), gr.update(), gr.update(),
                            gr.update(), bank_up,
                            gr.update(value="❌ فایل پشتیبان انتخاب نشده.",
                                      visible=True))
                with open(path, encoding="utf-8") as f:
                    payload = json.load(f)
                if not isinstance(payload, dict) \
                        or payload.get("_type") != "manga_autotranslate_backup":
                    return (*ups, gr.update(), gr.update(), gr.update(),
                            gr.update(), bank_up,
                            gr.update(value="❌ این فایلِ پشتیبانِ این اپ نیست.",
                                      visible=True))
                st = payload.get("settings") or {}
                for i, (k, _comp) in enumerate(_BACKUP_FIELDS):
                    if k in st and st[k] is not None:
                        ups[i] = gr.update(value=st[k])
                # v1.14.218 — بازیابیِ کامل: لیستِ مدلهایِ فایلِ بکاپ جایگزین
                # میشود (Import = برگشتنِ دقیقِ همه‌چیز به حالتِ بکاپ)
                merged = []
                for it in (payload.get("custom_models") or []):
                    if isinstance(it, dict) and str(it.get("name") or "").strip():
                        merged.append({
                            "name": str(it.get("name") or "").strip(),
                            "api_base": str(it.get("api_base") or "").strip(),
                            "api_key": str(it.get("api_key") or "").strip(),
                            "model": str(it.get("model") or "").strip(),
                        })
                save_custom_models(merged)
                _ch = _ai_choices(merged)
                _imp = str(st.get("provider") or "").strip()
                _old = str(prov_cur or "").strip()
                _newv = _imp if _imp in _ch else (
                    _old if _old in _ch
                    else ("auto" if "auto" in _ch else "gemini"))
                # v1.14.222 — بانکِ فیلدها هم از بکاپ بازسازی میشود تا
                # provider.changeِ بعدی مقادیرِ تازه را جابهجا نکند
                try:
                    _bank = dict(bank_cur or {}) if isinstance(bank_cur, dict) else {}
                except Exception:
                    _bank = {}
                _bank["_last"] = _newv
                if _newv in ("gemini", "custom"):
                    _bank[_newv] = {"base": str(st.get("api_base") or ""),
                                    "key": str(st.get("api_keys") or ""),
                                    "model": str(st.get("model") or "")}
                bank_up = _bank
                return (*ups, merged,
                        json.dumps(merged, ensure_ascii=False),
                        gr.update(choices=_ch, value=_newv),
                        gr.update(visible=_newv in _cm_names(merged)),
                        bank_up,
                        gr.update(value=f"✅ بازیابیِ کامل شد: {len(merged)} مدل + "
                                        f"{len(st)} تنظیم (از فایلِ بکاپ).",
                                  visible=True))
            except Exception as e:
                return (*ups, gr.update(), gr.update(), gr.update(),
                        gr.update(), bank_up,
                        gr.update(value=f"❌ بازیابی ناموفق: {e}", visible=True))

        try:
            _backup_inputs = [c for _, c in _BACKUP_FIELDS] + [custom_models_state]
            backup_btn.click(
                _do_backup, inputs=_backup_inputs,
                outputs=[backup_out, backup_status], api_name="backup_settings")
            # v1.14.219 — دستورِ سازنده: «بکاپ زدم خودکار دانلود کنه نه این ک
            # مجدد برم دکمه دانلود بزنم» — به محضِ آمادهشدنِ فایل (changeِ
            # backup_out) مرورگر همان را با a[download] دانلود میکند؛ رویِ
            # اندروید/PC/لینوکس/وب یکجاست (همه مرورگرِ webview/کروم):
            backup_out.change(
                fn=None, inputs=[backup_out], outputs=[],
                js="""(v) => {
  try {
    let url = null, name = "manga_backup.json";
    if (v && typeof v === "object") {
      url = v.url || null;
      name = v.orig_name || name;
    } else if (typeof v === "string" && v) {
      url = v;
    }
    if (url) {
      const a = document.createElement("a");
      a.href = url;
      a.download = name || "manga_backup.json";
      document.body.appendChild(a);
      a.click();
      a.remove();
    }
  } catch (e) {}
  return [];
}""",
            )
            # v1.14.220 — UploadButton رویدادِ upload دارد (بعد از انتخابِ
            # فایل) — همان هندلرِ قبلیِ _do_import
            import_file.upload(
                _do_import,
                inputs=[import_file, custom_models_state, provider,
                        fields_bank],
                outputs=[c for _, c in _BACKUP_FIELDS]
                        + [custom_models_state, cm_json_box, provider,
                           cm_del_btn, fields_bank, backup_status],
                api_name="import_settings")
        except Exception:
            pass

        def _prompt_preview_update(mode_v, prov_v, mdl_v):
            # v1.14.147: بدونِ تیتر — فقط متنِ کادرِ پرامپت رفرش میشود
            try:
                return gr.update(value=resolve_prompt_preview(mode_v, prov_v, mdl_v, None))
            except Exception as e:
                return gr.update(value=f"خطا در پیش‌نمایش پرامپت: {e}")
        try:
            _pp_inputs = [prompt_mode, provider, model]
            for _pp_comp in (prompt_mode, provider, model):
                _pp_comp.change(
                    _prompt_preview_update, inputs=_pp_inputs,
                    outputs=[prompt_preview_body],
                    api_name=f"prompt_preview_{id(_pp_comp)}",
                )
        except Exception:
            pass

        _click_kw = dict(
            inputs=[session_id, sid_box, inp_path, inp_upload, provider, api_keys, model,
                    ocr_lang,
                    out_fmt, quality, font_upload,
                    workers, bubbles, timeout,
                    batchw, maxre, reqdelay, temp, readord,
                    clean_method, two_pass,
                    fake_test, clean_only, web_debug, prompt_mode, prompt_preview_body,
                    glossary_text, story_brief, api_base,
                    custom_models_state,
                ] + tone_uploads + tone_enables,
            outputs=[session_id, sid_box, run_btn, log_box, dl_btn, btn_view, result_group, viewer_html, html_state,
                     dl_btn_debug, btn_view_debug, debug_row, html_debug_state],
            concurrency_limit=8,
        )
        _hide_test_js = """
            () => {
                setTimeout(() => {
                    const el = document.getElementById('manga_test_key_out');
                    if (el) {
                        el.style.display = 'none';
                    }
                }, 60000);
            }
            """
        try:
            _test_evt = test_key_btn.click(
                _do_test_key,
                inputs=[provider, api_keys, model, api_base,
                        custom_models_state],
                outputs=[test_key_out],
            )
            # پنهان‌سازی بعد از ۶۰ ثانیه — جدا از رویداد اصلی تا ورودی‌ها خراب نشوند
            try:
                _test_evt.then(fn=None, inputs=None, outputs=None, js=_hide_test_js)
            except Exception:
                pass
        except Exception:
            pass
        try:
            _ev178 = None
            try:
                _ev178 = run_btn.click(run_translation,
                                       show_progress="hidden", **_click_kw)
            except TypeError:
                try:
                    _ev178 = run_btn.click(run_translation,
                                           show_progress=False,
                                           **_click_kw)
                except TypeError:
                    _ev178 = run_btn.click(run_translation, **_click_kw)
            # v1.14.181 — کلیدِ یک‌بارمصرفِ «تستِ سرعت» (v1.14.178) با خودِ
            # دکمه حذف شد؛ کارهایِ بعدی همیشه ترجمهٔ عادیاند.
        except Exception:
            pass

        _save_inputs = [
            session_id, sid_box, inp_path, provider, api_keys, model, out_fmt, quality,
            workers, bubbles, timeout, batchw, maxre, reqdelay, temp, readord,
            clean_method, two_pass, fake_test, clean_only,
        ]

        try:
            run_btn.click(fn=None, inputs=_save_inputs, outputs=[], js=save_form_js)
        except Exception:
            pass
        try:
            
            run_btn.click(
                fn=None,
                inputs=[session_id, sid_box, run_btn, log_box],
                outputs=[],
                js=save_job_js,
            )
        except Exception:
            pass
        try:
            sid_box.change(fn=None, inputs=[session_id, sid_box], outputs=[], js=save_sid_js)
        except Exception:
            pass

        for _comp in (api_keys, provider, model, out_fmt, inp_path):
            try:
                _comp.change(fn=None, inputs=_save_inputs, outputs=[], js=save_form_js)
            except Exception:
                try:
                    _comp.blur(fn=None, inputs=_save_inputs, outputs=[], js=save_form_js)
                except Exception:
                    pass
        for _comp in (quality, workers, bubbles, timeout, batchw, maxre, reqdelay, temp, readord,
                      clean_method, two_pass, fake_test, clean_only):
            try:
                _comp.change(fn=None, inputs=_save_inputs, outputs=[], js=save_form_js)
            except Exception:
                pass

        def _apply_browser_restore(raw_json):
            data = {}
            if raw_json:
                try:
                    data = json.loads(raw_json) if isinstance(raw_json, str) else {}
                except Exception:
                    data = {}

            preferred = (data.get("sid") or "").strip()
            
            if preferred:
                sid = _find_active_sid(preferred) or preferred
            else:
                sid = ""
            if not sid:
                return (gr.update(),) * 27
            job = _get_job(sid)
            meta = _load_job_meta(sid) if sid else {}
            
            
            client_log = (data.get("_jobLog") or "").strip()
            client_running = bool(data.get("_jobRunning"))
            client_btn = (data.get("_jobBtn") or "").strip()

            with job["lock"]:
                mem_log = job.get("log") or ""
                meta_log = meta.get("log") or ""
                default_log = "— لاگ بعد از شروع ترجمه اینجا می‌آید —"

                candidates = []
                if mem_log and mem_log != default_log and not mem_log.startswith("—"):
                    candidates.append(mem_log)
                if meta_log and meta_log != default_log:
                    candidates.append(meta_log)
                if client_log and client_log != default_log and not client_log.startswith("—"):
                    candidates.append(client_log)

                if candidates:
                    
                    job["log"] = max(candidates, key=len)

                if meta.get("download_path") and not job.get("download_path"):
                    job["download_path"] = meta.get("download_path")
                if meta.get("result_visible"):
                    job["result_visible"] = True
                if meta.get("html_state") and not job.get("html_state"):
                    job["html_state"] = meta.get("html_state")
                if meta.get("reader_path") and not job.get("reader_path"):
                    job["reader_path"] = meta.get("reader_path")
                if meta.get("out_v") and not job.get("out_v"):
                    job["out_v"] = meta.get("out_v")
                still_running = _job_running(job)
                if not still_running and (meta.get("running") or client_running):
                    
                    if still_running is False and meta.get("running"):
                        cur = job.get("log") or ""
                        if "اتصال به جلسه قطع شد" not in cur:
                            job["log"] = (cur or client_log or meta_log or "") + (
                                "\n\n⚠ اتصال به پروسه روی سرور قطع است. "
                                "اگر ترجمه تمام شده از خروجی استفاده کنید؛ وگرنه دوباره Start بزنید."
                            )
                log = job.get("log") or client_log or default_log
                vis = bool(job.get("result_visible"))
                dl = job.get("download_path")
                html = job.get("html_state") or ""
            
            if still_running or client_running:
                btn = "⏹  متوقف ترجمه"
            else:
                btn = "🚀  شروع ترجمه"

            def u_str(key):
                if key not in data:
                    return gr.update()
                v = data.get(key)
                if v is None:
                    return gr.update()
                s = str(v).strip()
                if s.lower() in ("null", "undefined"):
                    return gr.update()
                return gr.update(value=s)

            def u_num(key):
                if key not in data:
                    return gr.update()
                v = data.get(key)
                if v is None or v == "":
                    return gr.update()
                try:
                    return gr.update(value=float(v))
                except Exception:
                    return gr.update()

            def u_bool(key, default=None):
                if key not in data:
                    return gr.update()
                v = data.get(key)
                if v is None:
                    return gr.update()
                return gr.update(value=bool(v))

            def u_cleanm():
                if "cleanm" in data:
                    v = str(data.get("cleanm") or "").strip()
                    if v in ("lama-manga", "lama-big", "opencv"):
                        return gr.update(value=v)
                    if v:
                        return gr.update(value="lama-manga")
                    return gr.update()
                if data.get("cpu"):
                    return gr.update(value="opencv")
                if data.get("lama"):
                    return gr.update(value="lama-big")
                return gr.update(value="lama-manga")

            return (
                sid,
                gr.update(value=sid),
                gr.update(value=btn),
                gr.update(value=log),
                gr.update(value=dl, label=_dl_label(dl), visible=vis) if vis else gr.update(),
                gr.update(visible=False),
                gr.update(visible=vis),
                gr.update(visible=False),
                html if vis else gr.update(),
                u_str("inp"),
                u_str("prov"),
                u_str("keys"),
                u_str("model"),
                u_str("fmt"),
                u_num("qual"),
                u_num("workers"),
                u_num("bubbles"),
                u_num("timeout"),
                u_num("batchw"),
                u_num("maxre"),
                u_num("reqdelay"),
                u_num("temp"),
                u_str("readord"),
                u_cleanm(),
                u_bool("twopass"),
                u_bool("fake_test"),
                u_bool("clean_only"),
            )

        _restore_outputs = [
            session_id, sid_box, run_btn, log_box, dl_btn, btn_view, result_group, viewer_html, html_state,
            inp_path, provider, api_keys, model, out_fmt, quality,
            workers, bubbles, timeout, batchw, maxre, reqdelay, temp, readord,
            clean_method, two_pass, fake_test, clean_only,
        ]

        # فرم از localStorage: جاوااسکریپت مقدار hidden ترباکس را روی load پر می‌کند،
        # بعد change همان ترباکس، فن سرورِ ری‌استور را با JSON کامل صدا می‌زند.
        hidden_restore_tb = gr.Textbox(visible=False, elem_id="manga_hidden_restore", container=False)
        try:
            demo.load(
                fn=None,
                inputs=None,
                outputs=[hidden_restore_tb],
                js=load_form_js,
            )
        except Exception:
            pass
        try:
            hidden_restore_tb.change(
                _apply_browser_restore,
                inputs=[hidden_restore_tb],
                outputs=_restore_outputs,
            )
        except Exception:
            pass

        try:
            demo.load(None, None, None, js=client_restore_js)
        except Exception:
            try:
                demo.load(fn=None, inputs=None, outputs=None, js=client_restore_js)
            except Exception:
                pass

        try:
            def _on_load_fallback(sid, sid_box_v):
                preferred = (sid or sid_box_v or "").strip()
                if not preferred:
                    return (gr.update(),) * 13
                sid = _find_active_sid(preferred) or preferred
                job = _get_job(sid)
                meta = _load_job_meta(sid)
                with job["lock"]:
                    mem_log = job.get("log") or ""
                    meta_log = meta.get("log") or ""
                    if (not mem_log or mem_log.startswith("—")) and meta_log:
                        job["log"] = meta_log
                    elif meta_log and len(meta_log) > len(mem_log):
                        job["log"] = meta_log
                    if meta.get("download_path"):
                        job["download_path"] = meta.get("download_path")
                    if meta.get("download_debug"):
                        job["download_debug"] = meta.get("download_debug")
                    if meta.get("result_visible"):
                        job["result_visible"] = True
                    if meta.get("reader_path"):
                        job["reader_path"] = meta.get("reader_path")
                    if meta.get("reader_debug_path"):
                        job["reader_debug_path"] = meta.get("reader_debug_path")
                    still_running = _job_running(job)
                    log = job.get("log") or ""
                    vis = bool(job.get("result_visible"))
                    dl = job.get("download_path")
                    dl_dbg = job.get("download_debug")
                    has_dbg = bool(dl_dbg or job.get("reader_debug_path") or meta.get("has_debug"))
                    want_dbg = bool(job.get("want_debug") or meta.get("want_debug") or has_dbg)
                    show_dbg = bool(want_dbg and (vis or still_running))
                    html = job.get("html_state") or ""
                if not log or log.startswith("—"):
                    return (sid, gr.update(value=sid)) + (gr.update(),) * 11
                btn = "⏹  متوقف ترجمه" if still_running else "🚀  شروع ترجمه"
                _dbg_sz = ""
                try:
                    if dl_dbg and os.path.isfile(dl_dbg):
                        _dbg_sz = f" ({human_size(os.path.getsize(dl_dbg))})"
                except Exception:
                    pass
                return (
                    sid,
                    gr.update(value=sid),
                    gr.update(value=btn),
                    gr.update(value=log),
                    gr.update(value=dl, label=_dl_label(dl), visible=vis) if vis else gr.update(),
                    gr.update(visible=False),
                    gr.update(visible=vis),
                    gr.update(visible=False),
                    html if vis else gr.update(),
                    # v1.14.33: دکمهٔ «دانلود دیباگ» بعد از پایان کار دیده می‌شود
                    gr.update(value=dl_dbg,
                              label="⬇ دانلود دیباگ" + _dbg_sz,
                              visible=bool(show_dbg and dl_dbg and vis)),
                    gr.update(visible=False),
                    gr.update(visible=bool(show_dbg and dl_dbg and vis)),
                    gr.update(),
                )

            demo.load(
                _on_load_fallback,
                inputs=[session_id, sid_box],
                outputs=[session_id, sid_box, run_btn, log_box, dl_btn, btn_view, result_group, viewer_html, html_state,
                     dl_btn_debug, btn_view_debug, debug_row, html_debug_state],
            )
        except Exception:
            pass

        def _poll_job_status(sid, sid_box_v):
            preferred = (sid or sid_box_v or "").strip()
            sid = _find_active_sid(preferred) or preferred
            empty = (gr.update(),) * 15
            if not sid:
                return empty
            job = _get_job(sid)
            meta = _load_job_meta(sid)
            with job["lock"]:
                mem_log = job.get("log") or ""
                meta_log = meta.get("log") or ""
                running = _job_running(job)
                # لاگ متادیتا فقط وقتی کار واقعاً در جریان است برمی‌گردد —
                # وگرنه نتیجهٔ تازهٔ کاربر هر ثانیه با لاگ قدیمی جلسهٔ قبل بازنویسی می‌شد!
                if running and meta_log and (
                        len(meta_log) > len(mem_log) or not mem_log
                        or mem_log.startswith("—")):
                    job["log"] = meta_log
                if meta.get("result_visible") and not job.get("result_visible"):
                    job["result_visible"] = True
                if meta.get("download_path") and not job.get("download_path"):
                    job["download_path"] = meta.get("download_path")
                if meta.get("download_debug") and not job.get("download_debug"):
                    job["download_debug"] = meta.get("download_debug")
                if meta.get("reader_path") and not job.get("reader_path"):
                    job["reader_path"] = meta.get("reader_path")
                if meta.get("reader_debug_path") and not job.get("reader_debug_path"):
                    job["reader_debug_path"] = meta.get("reader_debug_path")
                
                running = _job_running(job)
                log = job.get("log") or ""
                # لاگ فقط وقتی از نظر سرور تغییر کرده به مرورگر فرستاده می‌شود —
                # وگرنه هر ثانیه لاگ قدیمی روی تعامل تازهٔ کاربر بازنویسی می‌شد.
                _last_pushed = job.get("_last_poll_log")
                log_changed = bool(log) and log != _last_pushed
                if log_changed:
                    job["_last_poll_log"] = log
                vis = bool(job.get("result_visible"))
                live_cnt = 0
                try:
                    _ld = job.get("live_dir")
                    if _ld and os.path.isdir(_ld):
                        live_cnt = sum(
                            1 for f in os.listdir(_ld)
                            if f.lower().endswith(".jpg") and f.startswith("live_"))
                except Exception:
                    pass
                dl = job.get("download_path")
                dl_dbg = job.get("download_debug")
                has_dbg = bool(dl_dbg or job.get("reader_debug_path") or meta.get("has_debug"))
                want_dbg = bool(job.get("want_debug") or meta.get("want_debug") or has_dbg)
                
                show_dbg = bool(want_dbg and (vis or running))
            # وقتی هیچ کاری در جریان نیست و لاگ همان جای‌نگهدارِ اولیه است،
            # هیچ‌کدام از ۱۴ خروجی را هر ثانیه بازنویسی نکن (هم روان‌تر است
            # هم جلوی پر شدن صفحه با حالت‌های قدیمی را می‌گیرد).
            # ولی اگر کار تمام/خطا شده، وضعیت دکمه و لاگ تازه باید برسد.
            default_log = "— لاگ بعد از شروع ترجمه اینجا می‌آید —"
            if not running and not vis and (not log or log.strip() == default_log):
                return empty
            btn = "⏹  متوقف ترجمه" if running else "🚀  شروع ترجمه"
            html_dbg = ""
            with job["lock"]:
                html_dbg = job.get("html_debug") or ""
            show_card = bool(vis or (running and live_cnt > 0))
            _dbg_sz = ""
            try:
                if dl_dbg and os.path.isfile(dl_dbg):
                    _dbg_sz = f" ({human_size(os.path.getsize(dl_dbg))})"
            except Exception:
                pass
            # v1.14.236 — نوارِ پیشرفتِ زیرِ لاگ (مثلِ اپ اندروید): فاز +
            # «صفحهٔ n از N» + درصد؛ از همان لاگ و total.txt پوشهٔ live.
            _prog_upd = gr.update()
            try:
                if (running or vis) and log:
                    _ld = job.get("live_dir")
                    _ph, _cur, _ltot, _unit = _web_prog_parse(log)
                    _tot = _ltot or (_live_total_of(_ld) if _ld else 0)
                    _done = (not running) and ("✅" in log or "تمام شد" in log)
                    if _done or _ph or running:
                        _prog_upd = gr.update(
                            value=_web_prog_html(_ph, _cur, _tot, running,
                                                 _done, _unit),
                            visible=True)
            except Exception:
                _prog_upd = gr.update()
            # v1.14.31: نمایش اصلی/دیباگ حذف — همه‌جا مخفی؛ فقط «نمایش» (دکمهٔ 📖) می‌ماند
            return (
                sid,
                gr.update(value=sid),
                gr.update(value=sid),
                gr.update(value=btn),
                gr.update(value=log) if (log and log_changed) else gr.update(),
                gr.update(value=dl, label=_dl_label(dl), visible=vis) if vis else gr.update(),
                gr.update(visible=False),
                gr.update(visible=show_card),
                gr.update(),
                gr.update(),
                # v1.14.33: «دانلود دیباگ» — بعد از پایان کار در دسترس است
                gr.update(value=dl_dbg,
                          label="⬇ دانلود دیباگ" + _dbg_sz,
                          visible=bool(dl_dbg and vis)),
                gr.update(visible=False),
                gr.update(visible=bool(dl_dbg and vis)),
                gr.update(),
                _prog_upd,
            )


        _poll_outputs = [session_id, sid_box, sid_holder, run_btn, log_box, dl_btn, btn_view, result_group, viewer_html, html_state,
                         dl_btn_debug, btn_view_debug, debug_row, html_debug_state, prog_html]

        def _scan_live_dir(live_dir):
            try:
                fs = [f for f in os.listdir(live_dir)
                      if f.lower().endswith(".jpg") and f.startswith("live_")]
            except Exception:
                return []
            fs.sort()
            return [os.path.join(live_dir, f) for f in fs]

        def _dbg_sibling(live_dir: str) -> str:
            """پوشهٔ live_debug کنار پوشهٔ live — اگر باشد، خوانندهٔ زنده دکمهٔ دیباگ می‌گیرد."""
            try:
                base = os.path.dirname(os.path.abspath(live_dir))
                cand = os.path.join(base, "live_debug")
                if os.path.isdir(cand):
                    return cand
            except Exception:
                pass
            return ""

        def _live_total_of(d: str) -> int:
            try:
                with open(os.path.join(d, "total.txt"), encoding="utf-8") as f:
                    return int(f.read().strip() or 0)
            except Exception:
                return 0

        def _write_live_reader(live_dir: str, dbg_dir: str = "") -> str:
            """خوانندهٔ زندهٔ وب را داخل پوشهٔ live می‌نویسد — اسلات لودینگ برای
            صفحه‌های نرسیده + سوئیچ دیباگ (اگر پوشهٔ live_debug باشد)."""
            import gradio as _gr
            gv = getattr(_gr, "__version__", "4")
            try:
                major = int(str(gv).split(".")[0] or 4)
            except Exception:
                major = 4
            prefix = "/gradio_api/file=" if major >= 5 else "/file="
            d = str(live_dir).replace(os.sep, "/")
            if not d.endswith("/"):
                d += "/"
            dbg_q = ""
            if dbg_dir:
                dbg_q = str(dbg_dir).replace(os.sep, "/")
                if not dbg_q.endswith("/"):
                    dbg_q += "/"
            html = (_LIVE_READER_TMPL
                    .replace("__PREFIX__", prefix)
                    .replace("__DIR__", urllib.parse.quote(d, safe="/"))
                    .replace("__DBGDIR__", urllib.parse.quote(dbg_q, safe="/")))
            path = os.path.join(live_dir, "live_reader.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            return path

        def _poll_live_gallery(sid_v, sid_box_v):
            pref = (sid_v or sid_box_v or "").strip()
            job = live_jobs.get(pref)
            if job is None:
                return gr.update(), gr.update(), gr.update()
            live_dir = job.get("live_dir")
            files = _scan_live_dir(live_dir) if live_dir else []
            dbg_dir = job.get("live_dbg_dir")
            dbg_files = _scan_live_dir(dbg_dir) if dbg_dir else []
            with job["lock"]:
                prev = list(job.get("live_files") or [])
                prev_dbg = list(job.get("live_dbg_files") or [])
                running = bool(job.get("running")) and (
                    job.get("proc") is None or job["proc"].poll() is None)
            if files == prev and dbg_files == prev_dbg:
                # هیچ تغییر — ولی وضعیتِ در حال اجرا/پایان باید دیده شود
                was_running = bool(job.get("_live_was_running"))
                if running == was_running:
                    return gr.update(), gr.update(), gr.update()
            with job["lock"]:
                job["live_files"] = files
                job["live_dbg_files"] = dbg_files
                job["_live_was_running"] = running
                job["ts"] = time.time()
            if not running:
                # v1.14.31: بعد از پایان هم همان «نمایش» می‌ماند (پوشهٔ live همهٔ
                # صفحه‌های نهایی را دارد) — دیگر پنهان نمی‌شود.
                tot_end = _live_total_of(live_dir) if live_dir else 0
                n_end = len(files)
                if n_end > 0 or tot_end > 0:
                    if tot_end > 0:
                        lbl_end = "📖 نمایش (%d/%d صفحه)" % (n_end, tot_end)
                    elif n_end > 1:
                        lbl_end = "📖 نمایش (%d صفحه)" % n_end
                    else:
                        lbl_end = "📖 نمایش (۱ صفحه)"
                    return (gr.update(value=lbl_end, visible=True),
                            gr.update(),
                            gr.update(visible=False))
                return (gr.update(visible=False), gr.update(), gr.update())
            tot = _live_total_of(live_dir) if live_dir else 0
            if tot > 0:
                label = "📖 نمایش (%d/%d صفحه)" % (len(files), tot)
            elif len(files) > 1:
                label = "📖 نمایش (%d صفحه)" % len(files)
            else:
                label = "📖 نمایش (۱ صفحه)"
            return (gr.update(value=label, visible=True),
                    gr.update(visible=True),
                    gr.update(visible=False))
        try:
            _timer = gr.Timer(1.0, active=True)
            _tick_evt = _timer.tick(
                _poll_job_status,
                inputs=[sid_holder, sid_box],
                outputs=_poll_outputs,
                queue=False,
                concurrency_limit=1,
            )
            try:
                
                _tick_evt.then(
                    fn=None,
                    inputs=[session_id, sid_box, run_btn, log_box],
                    outputs=[],
                    js=save_job_js,
                    queue=False,
                )
            except Exception:
                pass
        except Exception:
            try:
                demo.load(_poll_job_status, inputs=[session_id, sid_box], outputs=_poll_outputs)
            except Exception:
                pass

        try:
            _timer_g = gr.Timer(1.5, active=True)
            _timer_g.tick(
                _poll_live_gallery,
                inputs=[sid_holder, sid_box],
                outputs=[live_btn, result_group, btn_view_debug],
                queue=False,
                concurrency_limit=1,
            )
        except Exception:
            pass

        def _cleanup_old_jobs():
            while True:
                try:
                    now = time.time()
                    dead = []
                    for sid, job in list(live_jobs.items()):
                        try:
                            with job["lock"]:
                                alive = job.get("proc") is not None and job["proc"].poll() is None
                                ts = job.get("ts") or 0
                            if not alive and (now - ts) > JOB_TTL:
                                dead.append(sid)
                                out_sub = os.path.join(OUT_DIR, sid[:12])
                                if os.path.isdir(out_sub):
                                    shutil.rmtree(out_sub, ignore_errors=True)
                        except Exception:
                            dead.append(sid)
                    for sid in dead:
                        live_jobs.pop(sid, None)

                    if os.path.isdir(OUT_DIR):
                        for name in os.listdir(OUT_DIR):
                            p = os.path.join(OUT_DIR, name)
                            if not os.path.isdir(p):
                                continue
                            if len(name) == 12 and all(c in "0123456789abcdef" for c in name.lower()):
                                try:
                                    mtime = os.path.getmtime(p)
                                    for root, dirs, files in os.walk(p):
                                        for f in files:
                                            try:
                                                mtime = max(mtime, os.path.getmtime(os.path.join(root, f)))
                                            except Exception:
                                                pass
                                    if (now - mtime) > JOB_TTL:
                                        shutil.rmtree(p, ignore_errors=True)
                                except Exception:
                                    pass

                    old_sess = os.path.join(WORK_DIR, "sessions")
                    if os.path.isdir(old_sess):
                        for name in os.listdir(old_sess):
                            fp = os.path.join(old_sess, name)
                            try:
                                if (now - os.path.getmtime(fp)) > JOB_TTL:
                                    if os.path.isfile(fp):
                                        os.remove(fp)
                                    elif os.path.isdir(fp):
                                        shutil.rmtree(fp, ignore_errors=True)
                            except Exception:
                                pass
                except Exception:
                    pass
                time.sleep(60)


        def _sid_box_sync(sid_v, sid_box_v):
            preferred = (sid_v or sid_box_v or "").strip()
            if not preferred:
                # v1.14.239 — فیکسِ ارورِ «needed: 15, returned: 14»:
                # _poll_outputs از v1.14.236 پانزده مؤلفه دارد (با
                # prog_html) ولی این شاخهٔ خالی هنوز ۱۴تایی بود.
                return (gr.update(),) * 15
            return _poll_job_status(preferred, preferred)

        try:
            sid_box.change(
                _sid_box_sync,
                inputs=[session_id, sid_box],
                outputs=_poll_outputs,
            )
        except Exception:
            pass

        
        _direct_restore_js = f"""
() => {{
  try {{
    const job = JSON.parse(localStorage.getItem("{JOB_KEY}") || "{{}}");
    const sid = (localStorage.getItem("manga_sid") || job.sid || "").trim();
    const log = (job.log || "").toString();
    const running = !!job.running;
    const btn = running ? "⏹  متوقف ترجمه" : "🚀  شروع ترجمه";
    return [sid, sid, sid, btn, log];
  }} catch (e) {{
    return ["", "", "", "🚀  شروع ترجمه", ""];
  }}
}}
"""

        def _apply_direct_restore(sid, sid2, btn, log):
            sid = (sid or sid2 or "").strip()
            log = (log or "").strip()
            btn = (btn or "").strip() or "🚀  شروع ترجمه"
            if not sid and not log:
                return gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
            server_log = ""
            still = False
            if sid:
                job = _get_job(sid)
                meta = _load_job_meta(sid)
                with job["lock"]:
                    if meta.get("log") and (
                        not job.get("log")
                        or len(meta.get("log") or "") > len(job.get("log") or "")
                    ):
                        job["log"] = meta["log"]
                    still = _job_running(job)
                    server_log = job.get("log") or ""
            client_wants_run = ("متوقف" in btn) or ("⏹" in btn)
            if still:
                btn = "⏹  متوقف ترجمه"
            elif client_wants_run and not still:
                
                if server_log or log:
                    tail = "\n\n⚠ بعد از رفرش اتصال به پروسه قطع شد. اگر کار تمام نشده دوباره Start بزنید."
                    base = server_log if len(server_log) >= len(log) else log
                    if "اتصال به پروسه قطع شد" not in base:
                        log = base + tail
                    else:
                        log = base
                btn = "🚀  شروع ترجمه"
            final_log = server_log if (server_log and len(server_log) >= len(log or "")) else (log or server_log)
            return (
                sid if sid else gr.update(),
                gr.update(value=sid) if sid else gr.update(),
                gr.update(value=sid) if sid else gr.update(),  
                gr.update(value=btn),
                gr.update(value=final_log) if final_log else gr.update(),
            )

        
        try:
            demo.load(
                fn=None,
                js=_direct_restore_js,
                outputs=[session_id, sid_box, sid_holder, run_btn, log_box],
            )
        except Exception:
            try:
                demo.load(
                    _apply_direct_restore,
                    inputs=None,
                    outputs=[session_id, sid_box, sid_holder, run_btn, log_box],
                    js=_direct_restore_js,
                )
            except Exception:
                pass

        
        def _hydrate_after_js(sid, holder):
            preferred = (sid or holder or "").strip()
            if not preferred:
                # v1.14.239 — همان فیکسِ ۱۵-خروجی (ارورِ گوشی روی
                # بارگذاریِ صفحهٔ وب — needed: 15, returned: 14).
                return (gr.update(),) * 15
            return _poll_job_status(preferred, preferred)

        try:
            demo.load(
                _hydrate_after_js,
                inputs=[sid_holder, sid_box],
                outputs=_poll_outputs,
            )
        except Exception:
            pass


        # v1.14.31: نمایش دیباگ جدا حذف شد — دیباگ داخل خود «نمایش» است؛
        # ورودی web_debug فقط علامت می‌زند که موتور دیباگ بسازد.
        threading.Thread(target=_cleanup_old_jobs, daemon=True).start()


        def _reader_file_url(path: str) -> str:
            if not path or not os.path.isfile(path):
                return ""
            import gradio as _gr
            gv = getattr(_gr, "__version__", "4")
            major = int(str(gv).split(".")[0] or 4)
            prefix = "/gradio_api/file=" if major >= 5 else "/file="
            return prefix + str(path).replace(os.sep, "/")

        reader_url_box = gr.Textbox(value="", visible=False, elem_id="manga_reader_url")

        open_live_js = """
(url) => {
  const u = (url || "").toString().trim();
  const isDesk = (new URLSearchParams(location.search)).get('desktop') === '1'
                 || !!(window.pywebview);
  if (!u) {
    try { if (window.__mangaPopup) { window.__mangaPopup.close(); } } catch (e) {}
    window.__mangaPopup = null;
    if (!isDesk) { alert("هنوز صفحه‌ای آماده نشده — چند لحظه بعد دوباره بزن."); }
    return [];
  }
  // v1.14.34: در پنجرهٔ دسکتاپ (pywebview) هرگز window.open نزن —
  // پنجرهٔ مرورگرِ سیستم باز می‌شد (خواستهٔ کاربر: نمایش داخل خود برنامه).
  if (isDesk) { window.location.href = u; return []; }
  let w = window.__mangaPopup;
  if (w && !w.closed) {
    try { w.location.href = u; } catch (err) { w = null; }
  } else { w = null; }
  window.__mangaPopup = null;
  if (!w) { w = window.open(u, "_blank"); }
  if (!w) { window.location.href = u; }
  return [];
}
"""

        def _open_live_viewer(sid, sid_box_v):
            preferred = (sid or sid_box_v or "").strip()
            sid2 = _find_active_sid(preferred) or preferred
            job = _get_job(sid2) if sid2 else None
            url = ""
            if job:
                with job["lock"]:
                    d = job.get("live_dir")
                if d and os.path.isdir(d):
                    try:
                        path = os.path.join(d, "live_reader.html")
                        if not os.path.isfile(path):
                            _write_live_reader(d, dbg_dir=_dbg_sibling(d))
                        url = _reader_file_url(path)
                    except Exception:
                        url = ""
            return url

        try:
            live_btn.click(
                fn=_open_live_viewer,
                inputs=[session_id, sid_box],
                outputs=[reader_url_box],
            ).then(
                fn=None,
                inputs=[reader_url_box],
                outputs=[],
                js=open_live_js,
            )
        except Exception:
            pass

        try:
            demo.load(None, None, None, js=_dark_js_src())
        except Exception:
            try:
                demo.load(js=_dark_js_src())
            except Exception:
                pass

        # گارد پاپ‌آپ: با کلیک روی دکمه‌های نمایش، یک پنجرهٔ خالی «همزمان با
        # کلیک» باز می‌شود تا مرورگر آن را مسدود نکند (رفعِ «هیچی نشون نداد»)
        # v1.14.34: در پنجرهٔ دسکتاپ اجرا نشود — window.open خالی همان‌جا
        # مرورگرِ سیستم را باز می‌کرد (بازشدن خودکار مرورگر روی PC).
        _popup_guard_js = """
() => {
  try {
    const isDesk = (new URLSearchParams(location.search)).get('desktop') === '1'
                   || !!(window.pywebview);
    if (isDesk) return [];
    if (window.__mangaPopupGuard) return [];
    window.__mangaPopupGuard = true;
    document.addEventListener('click', function (e) {
      try {
        const t = e.target && e.target.closest ? e.target.closest('button') : null;
        if (!t) return;
        const tid = (t.id || '').toString();
        if (tid.indexOf('manga_live_btn') === -1 &&
            tid.indexOf('manga_view_btn') === -1 &&
            tid.indexOf('manga_view_debug_btn') === -1) return;
        if (!window.__mangaPopup || window.__mangaPopup.closed) {
          window.__mangaPopup = window.open('', '_blank');
        }
      } catch (err) {}
    }, true);
  } catch (err) {}
  return [];
}
"""
        try:
            demo.load(None, None, None, js=_popup_guard_js)
        except Exception:
            try:
                demo.load(js=_popup_guard_js)
            except Exception:
                pass

        gr.Markdown(
            "<div style='text-align:center; opacity:.45; margin-top:16px'>"
            f"مانگا مترجم PRO v{APP_VER} · RT-DETR + Gemini/… + LaMa-Manga · اجرا روی CPU</div>"
        )

        gr.HTML(
            """
<div class="credit">
  <a href="https://t.me/amir_wolf512" target="_blank" rel="noopener"
     title="کانال تلگرام سازنده">
    <svg viewBox="0 0 24 24"><path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z"/></svg>
    سازنده
  </a>
  <a href="https://github.com/amirwolf512k/Manga-AutoTranslate" target="_blank" rel="noopener"
     title="سورس پروژه در گیت‌هاب">
    <img class="gh-avatar" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACQAAAAkCAYAAADhAJiYAAALoklEQVR42rWYa5Bcx13Ff9197507MzvvfUmr3dVqJdkqeW2tpJhEctZ62OUIIjlJYRIeRQwx4Qu4oAguOx9CIIaqUFQgMRAnOBgIDzsJRQJUnAplJRBDDI4fshVZL6/W69G+tLszs/O8j+7mw2hlO3YcY6Cruqbmzr09p/t/+txzWvAWm7XWvsFvSCnFWxn3f/RQq9WyzWaTMIww2tButzBYpBB4iQSJhEcqmSKbzbxqaCGE+D8FdP/9D9j62hrVapVLly5RrVWoNxpUKhWazRZKKZRSJJMp8tkeejI9bNu6jX379jM2voXegT7yuRzOmwD2I2+440Mfts1mk7V6nVazSaw1sY6J4xhrLX19fdRqVayGUqkXIQQzs7NoLNl0hq2jI+wcHWPH1m309vdxw63vEm8J0O23/6JdXV2l3qgThiEIEEi01sRxDIAxhmKhQBDFCKVIJVPUKzWSAorCJR9DBvCLOdbSLjKTx8+mcFI+9/7uveJNA3rn1EEbRyFCCJTjIIRAa00YRlhrEEIiBWgB1hgSGpx2hG13SCmHfCZDb38v/eMjbN+9m+3X7SCT76Gx1iCdSpPP5fGTaXKF4mv+3/nBC/v2v9Naa3A9DyEEcRwThuFlIAopHYSlWxLlUAhigmab4vAgYzt3sHPPBFt2bGdwZJhCPk+jViPl+fTksmhrWFxYIIpjStk0q8vztti7QbwhIKXUlXJEUYTWGgApHAQCKQSRgM1eip5akxVP8sHf+Qh73349A/19JFyXMIpQrosxhmQyxfzcPIUgwDqCXKlIdaXK9HPPklKvrY585ZepA4csQBzHBEGA0RopJUoqpOh+xkIwkcwz0IyZVjG/9smPccvNh1DWIiyEYUS72SJotrDGonWMn/TRVuNYgelEDAwMki0U6S/18vWH/8a+LqADh2+yAq6Q1hiDEAKJRAoHRykiYdmayjBuXZ7Tde7+vY9x/XWTLK1UCKKQThSBkijXIY7j7mRcl1w+h6dcMtkssYmxxlLcOMzxJ05w592/xWfu+2P7GkD1epMwDNFaI6Ui5adxlIcQEiUEsRRkHY+pTB/Hy9P80l2/wr69kzi+T211GQeBCSKklAgpEUJgsSS8BFIpVqurOJ5Lo9mkVqvgOi5tKwg1fO+JJ169Qldt32nrtTXiWGO0QQCO4yDlZbxSoHXMTYUBnpyZZvzQO3jfkXfRbLVZnL/I4tlTuI6D47lYbbHaYG33FQKGdrvNU//2LS4tLpBMpgmaLcKoweHDN7J3zx7m5xY4/8K0vQLIGIOJNVEQo5TCGkOr1equlpC0dcxkKodsBVzoUdzzm3fSiTSdIGLxzEm2DQ8ThwGRjpHWEnZCpFTYKMZ1EizPzTGxZYT506doN5sIR1Gr1sj05Ji6cT/li3PMzc29vELWWqy1dDptsKJ7WQgEEBpDr3S5Nlnk25U57vnE3YxtHkHHEbZeYffevWyeuIZOvY6OYywWKQWOUgghqFcr+FJw9cFj7LhuJ83qMpmeNDqMiOOAqal9JFNJYt0VW2f79p3WXiZwGIbEcYzjOBhjiYUBY7ghv5En58rsv+3Hedu1Ezx34gTzZ8/SaAc8c3aa0c0jRJ0AsVKhVCyS6kkTdAISbpJnn36KC7MzfP34cVQQsmV0M7l8L8rzWF5e5Bvf+CYHDkxRyOV5qTxnnb6BPi6+VMZzPbTWBEHQ5Y6xdNBcl8xhgg7lguRXDx/gP7/zX3zhTz7HC2fPUMhmOffCBXbsexu/ftdHGE6nCTsB1coql5YvMT07y32f/BSnn3yam257DwemDnH/Zx/gnqFhJvbs5plnTvDQ3/09W7dtxnEcrDHID9/xIeI4uuJjwjAEa4mx5IRiIlngsZUFfu72nyHbk6F30xDDW0cR7YAbDxzkmpFNlMKI7dvHgYhaZQmCFqMjGwgbNUZyJQ7t3s3Bt+/nF375g/zs+3+S4fFxojDkob/4a6yx9Pb1USyWuiW79rprSKfTBJ0IIQSO0xXv2Bp2pkvMNRvITX3ccvAgmXyBnkaTY8eOMDW6Fen5HLn3E/RvG2agvw+LRimJclywivfe+l52DI0SaY11HB790pcpbhxgcHCIh+//MzpPnSGfyzC5a5JEIsHq6ipOqVikVCwyMzNLOp0mkUhgsLgIBt0UJ+oLHHn/+7qmy8LSwjyedNjzEwfJ9pfw0ykcz8MYCdJDCDCmK7BWukwcPMi5s6fwpMOp8xfYtWWcZ08+zTcf+ReuH9jIxeYq41u3oXXcFWLfT5PJZNFak06nu/wRAkdIktKho2PmFhaYPj+NjjWFnhS+MlSaDbxcBqUkOgzR1hDHAVEUIxC4roub8Ig7HTYNjXD6zDmKuRzN0HDnnXfx/FwZXMm2Qolz0y/AZa1WR48e+/jp58+glEOn08F1XSSSEEPaURSky5cee4xmfY29e3fRaLUoOIIUhmajgZ/qwfF8VEKh3B6Um8SagKWlZSq1Oo1mi+OPHufzD/wVEYYvfvFhhJVEwrLFS5IoFjhXWWHy2gkSvo+ampr6+Plz5xkb20wURbTbbRxH4SiHitUMSo96p82ZxUVKuSwmCij4PSRdF1Or0lxcZLk8x4lnTvL4fzzO6bPPM7+4xKbhMUqlPjLZHBPX7uIDP/0BMtkM1lrmlxaRK1UKKsFS3ufosWNsGhoijnXXoH3ta/9kn37qaSrVGmdOn2F+fgFrNbGFPs/jhnQvXz17ktE9O/jnv/wcL504CWkfIk3SwjNnznLfPzzCyVNn2b1nF3/06T9kaNPQFfe3HlDWLfWLL83y6N9+hRcvLXHbHT/PQLGfeqPJ+Pjm7h1LS8s2ikJWlpcpl8t897uPoxwPRwk6ccx4ogcRBHz5e4+zf+c2furGdzAyOYlbKhKv1alXqxz/1nf47U/9Kb9x990cPnwTKyvLjAxvxHFcEr6P4yik7Frgdc9VXatRW62ijUUIwZYtlwFNT89Yx5EopfA8l97e3le52+VqhZXlCstzi3z7+KPU5mYo9GTYsG0Lu39sL1dffRWe6/Dg5x8kv3GUyclJWs0GjuqCSGcy3R0kJYlEAmstSkoy2SzVapVqdQ0QjI2NvBxLLsxcsJ7rMTAwgDEWY7pO0XVdpJQEnQ4XZl4kl81z6vvf56P3fJTDh29mdnaao8eO8O5jR0mme5CoHxoe1zkaBAHVahXf99mwYSO1WoW+vn7xKgvruQ6Dg4PEcVcPlFI4jkO9XicIAjKZDIODA1wsXyRfLJAv9XLk3bcwMbET3091Z24MBnMFwCtjmBACz/PwPA9rLblcjtXVVU6fPk1fX+m1nnpoaFi02nUrUEjZBbO4uIi1lt7eXpRSJBIeuVyWmZlZkkkHrQPy+QJRFF4RtvUupeQH0/a6q1gv3YYNG1AKBgY2/vCs1mw2bBxHdnZ21i4sLFhrrTXGXOnWWhvHsf3zBx+wyyvzNgwjGwSBjaLIRlFktdY21rENw+BVz72yr66s2GqlYo3R9g1NPoBUgkuXlmi1WvT39xNFEca8XIZOp4NSivfceitrtSbadCOS1gZjDFJK5i+W+cwf/D76cvm5vDJaa4QQ/Pu/HucrDz+EEJIfCSjpp8XaWoNSqfeKaXqlljSbTcrlMqlUBt9Psrq6BEJjbBe4tRbPS/DihRnCqOsihJRIKa+8uDP5fNc5vk7Wd16vbFdddZVoNBpWxy9rxjoxS6USa2trlMtlfN+nXm+T9NskUwmM0WitSPg+Y1u3XuFMo1Enjg3WGpJJn41Dwxw4dLN4S4cNQRBYeXmG6xMSQmCtZWVlhaWlFaKozdiWTbiu1zV4QuEn0wi6xF6YX8BYQ61WZdeuSfG/Po6Josi+3u5Zz/zlcplO0KJYyOInfZRyEUgcz0UqhbpciDdzTiTfDCDXdYXjOK8ZbJ3Eo6OjDG0cpt2OWV5epdlsYKThpfPneeSzX0Bcbvx/tlduY621XW8X5y7a41/9R/tWx/1vBfDPJ2Nt0RQAAAAASUVORK5CYII=" width="22" height="22" alt="gh" />
    سورس
  </a>
</div>
"""
        )

    
    
    dark_js = r"""
() => {
  document.body.classList.add('dark');
  document.documentElement.classList.add('dark');
  // ---- Wake Lock (ماندن روشن بودن صفحه هنگام استخراج/پاکسازی/ترجمه) ----
  try {
    if (window.__mangaWakeLockInstalled) return;
    window.__mangaWakeLockInstalled = true;
    window.__mangaWL = null;
    const isRunning = () => {
      try {
        const btn = (document.getElementById('runbtn') || {}).querySelector
          ? document.getElementById('runbtn').querySelector('button') : null;
        const t = (btn || document.getElementById('runbtn') || {}).textContent || '';
        return (t.indexOf('متوقف') >= 0 || t.indexOf('⏹') >= 0);
      } catch (e) { return false; }
    };
    const req = async () => {
      try {
        if (!window.__mangaWL && navigator.wakeLock && navigator.wakeLock.request) {
          window.__mangaWL = await navigator.wakeLock.request('screen');
        }
      } catch (e) {}
    };
    const rel = () => {
      try { if (window.__mangaWL) { window.__mangaWL.release(); } } catch (e) {}
      window.__mangaWL = null;
    };
    setInterval(() => { if (isRunning()) req(); else rel(); }, 4000);
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible' && isRunning()) req();
    });
  } catch (e) {}
  const tryBind = () => {
    try {
      const root = document.getElementById('manga_rdr') || document.querySelector('.rdr');
      if (!root || root._bound) return;
    } catch (e) {}
  };
  try {
    new MutationObserver(tryBind).observe(document.documentElement, { childList: true, subtree: true });
  } catch (e) {}
}
"""
    # ثبت dark_js حالا داخل بلاک Blocks انجام می‌شود (نسخهٔ بیرون context کار نمی‌کرد)
    on_colab = ("google.colab" in sys.modules or bool(os.environ.get("COLAB_RELEASE_TAG")))
    on_codespace = _detect_codespace()
    codespace_name = (os.environ.get("CODESPACE_NAME")
                      or _hostname_codespace_name() or "")
    if on_codespace:
        print("[i] GitHub Codespaces: لینک عمومی gradio.live پایین را باز کنید.")
        if codespace_name:
            print(f"[i] پشتیبان: https://{codespace_name}-7860.app.github.dev")
    print(f"[*] فونت اصلی: {find_font() or 'پیدا نشد'}")
    launch_kw = {}
    if _gradio_major() >= 6:
        launch_kw["theme"] = gr.themes.Soft(primary_hue="indigo", neutral_hue="slate")
        launch_kw["css"] = WEB_CSS_RUNTIME
    demo.queue(max_size=64).launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("MANGA_APP_PORT", "7860")),
        share=on_colab or on_codespace or (not has_display()),
        inline=on_colab,
        show_error=True,
        allowed_paths=[str(WORK_DIR), str(OUT_DIR), str(UPLOAD_DIR), str(FONT_DIR)],
        **launch_kw,
    )



def main():
    ensure_dirs()
    args = sys.argv[1:]

    if not any(a in ("--web", "-h", "--help") for a in args):
        auto_update_on_start(log=print)

    if not manga_py_ok() and not any(a in ("--web", "-h", "--help") for a in args):
        print(MANGA_MIXED_MSG)
        if os.name == "nt":
            try:
                import tkinter as tk
                from tkinter import messagebox
                r = tk.Tk(); r.withdraw()
                messagebox.showerror(APP_NAME, MANGA_MIXED_MSG)
            except Exception:
                pass
        sys.exit(1)

    if args and args[0] == "--":
        run_cli(args[1:])
        return
    if "--cli" in args and "-i" not in args and "--input" not in args:
        run_cli([])
        return
    if any(a in ("-i", "--input", "-h", "--help") for a in args):
        run_cli(args)
        return
    if "--web" in args:
        run_web()
        return
    if "--desktop" in args:
        run_desktop()
        return

    
    on_colab = "google.colab" in sys.modules or bool(os.environ.get("COLAB_RELEASE_TAG"))
    headless = (not has_display()) or bool(os.environ.get("SSH_CONNECTION")) or on_colab
    if headless:
        print("[*] محیط بدون دسکتاپ → رابط وب")
        try:
            run_web()
        except KeyboardInterrupt:
            pass
        return

    try:
        run_desktop()
    except Exception as e:
        print(f"[!] دسکتاپ ممکن نشد ({e}) → رابط وب")
        run_web()


if __name__ == "__main__":
    main()
