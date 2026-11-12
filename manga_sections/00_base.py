# BUILD-STRIP-START
# پایه — هدرِ برنامه: نسخه، importها، زمانِ شروع + پرامپتهای ترجمه
# APP_VER و importهای پایه + ثابتها و سازندههای پرامپتِ سبکهای auto/professional/lite (استخراجِ بایت‌به‌بایتِ مرجع).
# (این سربرگ فقط راهنمای همین فایل است؛ لودرِ manga.py و بیلد حذفش میکنند)
# BUILD-STRIP-END
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# کدِ اصلی در manga_sections/ است؛ manga.py فقط لودر است
# (ترکیبِ بخشها در زمانِ اجرا — نگهبانِ همخوانی: python scripts/build_manga.py --check)
from __future__ import annotations
import time as _time_t0  # سنجشِ زمانِ importها (باید اول باشد)
_T0_IMPORT = _time_t0.time()
APP_VER = "1.14.283"

# پرامپتِ classic کلاً حذف شد (دستورِ سازنده) — تنها سبکها: auto / professional / lite

# پرامپتهای مرجع — استخراجِ بایت‌به‌بایت از APKِ اپِ مرجع ──
# (LibAssemblyStore → XALZ/LZ4 → اسمبلی → دیکدِ C#؛ سه کپچرِ واقعیِ ارسالیِ
# سازنده [تک‌صفحه lite، تک‌صفحه pro، شش‌صفحه pro] با همین ثابتها بایت‌به‌بایت
# بازسازی و تطبیق داده شدند — حتی `\n` لفظی + CRLF عیناً حفظ شده است.)
# سبکِ درخواست (حالتِ نوشتاریِ مرجع = «عکسِ فیک»):
# system = SYSTEM BEHAVIOR PROTOCOL (۲..۶) [+ بلوکِ ژاپنی] [+ بندِ ۷: اسکیما]
# user = TASK: Translate… + [بلوکِ ژاپنی] + TRANSLATION RULES: {pro|lite}
# + INPUT PAGES AND DIALOGUES (JSON): [{filename, dialogues}]
# هیچ عکسی ارسال نمی‌شود — filename فقط شناسهٔ صفحه است (01.png / slice_0001.webp).
# مرجع همهٔ متنها را در «یک» درخواست می‌فرستد و هیچ بریف/خلاصهٔ داستانی ندارد.
# قوانینِ «حرفه‌ای» (پیشفرضِ مرجع — Prompts[0]: «پرامپت ترجمه حرفه‌ای (مدل های Flash, Pro)»)
FLASH_PROMPT = "فرایند پردازش و ترجمه (مبتنی بر خود-اصلاحی): شما باید این فرآیند را در سه گام ذهنی و متوالی اجرا کنید:\\n\r\nگام ۱: تحلیل جامع و تولید پیش‌نویس اولیه\\n\r\n* پیش از شروع ترجمه، کل محتوای متن را بخوانید تا ژانر، فضای داستانی، کنایه‌ها و ویژگی‌های شخصیتی کاراکترها را درک کنید.\\n\r\n* در مرحلهٔ اندیشیدن، بر اساس این درک، یک پیش‌نویس اولیه از ترجمه را در ذهن تولید کنید.\\n\\n\r\nگام ۲: بازبینی موشکافانه و پالایش (مرحلهٔ خود-اصلاحی)\\n\r\n* با نگاه یک ویراستار سخت‌گیر، پیش‌نویس خود را به چالش بکشید و بازبینی کنید.\\n\r\n* از خود بپرسید: آیا این جمله روان است یا بوی ترجمه می‌دهد؟ آیا لحن شخصیت حفظ شده؟ آیا معادل بهتری برای این اصطلاح وجود دارد؟\\n\\n\r\nگام ۳: ارائه خروجی نهایی\\n\r\n* نسخهٔ نهایی، سلیس و بی‌نقص را که حاصل گام دوم است، به‌عنوان خروجی قطعی ارائه دهید.\\n\\n\r\n---\\n\\n\r\nاصول کلیدی ترجمه (قوانین حاکم بر گام‌های بالا):\\n\\n\r\n1. روانی، سلیس بودن و زبان محاوره‌ای زنده (پرهیز از ترجمه تحت‌اللفظی):\\n\r\nهدف اصلی، انتقال دقیق پیام و حس دیالوگ است. از ترجمهٔ کلمه‌به‌کلمه، کتابی، نوشتاری و عبارات ماشینی اکیداً پرهیز کنید؛ ترجمه باید به زبان فارسی امروزی، طبیعی، پویا و کاملاً گیرا باشد.\\n\\n\r\n2. حفظ و بازتاب دقیق لحن و سبک شخصیت‌ها (حیاتی و بدون سانسور):\\n\r\nلحن و شیوه گفتار هر کاراکتر (رسمی، دوستانه، طنز، جدی، خشن، معصومانه و...) باید با ظرافت رعایت شود. مدل زبانی باید مانند یک بازیگر نقش‌آفرینی کند:\\n\r\n- برای شخصیت‌های بی‌پروا، لات‌منش یا بی‌سواد: ترجمه باید کاملاً عامیانه، کوچه‌بازاری و دارای اصطلاحات خیابانی باشد. از اتوکشیده کردن، مؤدب‌سازی یا رسمی کردن دیالوگ‌های این شخصیت‌ها اکیداً خودداری کنید.\\n\r\n- برای شخصیت‌های باوقار، مرموز یا اشرافی: لحن باید محترمانه باشد، اما همچنان طبیعی و روان بماند (از تبدیل گفت‌وگو به متن نوشتاری و کتابی خودداری کنید).\\n\\n\r\nتذکر بسیار مهم: ترجمه حرفه‌ای به معنای سانسور، تلطیف یا پاستوریزه کردن کلمات نیست؛ بلکه به معنای انتقال دقیق حس جمله است. اگر متن اصلی دارای کلمات رکیک، جنسی یا خشن است، ترجمه فارسی نیز باید با همان شدت و حدت (بدون سانسور) ارائه شود تا اصالت اثر حفظ گردد.\\n\\n\r\n3. بومی‌سازی هوشمندانه اصطلاحات و ارجاعات فرهنگی:\\n\r\nاصطلاحات، ضرب‌المثل‌ها، شوخی‌ها و عبارات خاص فرهنگی مانگا را شناسایی کنید. اولویت با یافتن معادل‌های دقیق، رایج و طبیعی در زبان و فرهنگ فارسی است. در صورت نبود معادل مستقیم، مفهوم را با خلاقیت و به‌گونه‌ای که برای مخاطب فارسی‌زبان جذاب و ملموس باشد منتقل کنید.\\n\\n\r\n4. دقت و یکپارچگی در اسامی و جزئیات:\\n\r\nتمامی جزئیات متن اصلی (شامل اعداد، اسامی خاص شخصیت‌ها، مکان‌ها، تکنیک‌ها و علائم نگارشی) باید با دقت کامل ترجمه شوند و در سرتاسر تمام فایل‌ها کاملاً یکسان و هماهنگ استفاده شود.\\n"

# قوانینِ «سبک» («پرامپت ترجمه محاوره‌ای (مدل های Flash Lite)»)
FLASH_LITE_PROMPT = "قوانین ترجمه:\\n\\n\r\n1. روانی، سلیس بودن و جذابیت کلام: ترجمه باید به زبان فارسی امروزی، طبیعی و پویا باشد. متن نهایی باید به‌راحتی خوانده شود و برای مخاطب عام فارسی‌زبان کاملاً قابل فهم و گیرا باشد و از به‌کار بردن لحن کتابی، رسمی و عبارات ماشینی پرهیز کن.\\n\r\n2. حفظ و بازتاب دقیق لحن و سبک شخصیت‌ها (حیاتی):\\n\r\nلحن و شیوه گفتار هر کاراکتر (رسمی، دوستانه، طنز، جدی، خشن، معصومانه و...) باید با دقت در ترجمه رعایت شود؛ مثلاً:\\n\r\n- برای شخصیت‌های بی‌پروا، لات یا کم‌سواد: ترجمه باید کاملاً عامیانه، کوچه‌بازاری و دارای اصطلاحات خیابانی باشد. از مؤدبانه کردن یا رسمی نوشتن دیالوگ‌های این کاراکترها خودداری کنید.\\n\r\n- برای شخصیت‌های رسمی، مرموز یا اشرافی: لحن باید متین باشد.\\n\r\n3. در ترجمه اسامی، القاب و اصطلاحات داستانی، در سرتاسر فایل یکدستی و هماهنگی کامل را رعایت کن.\\n"

# بندهای ۲..۶ پروتکلِ سیستمی (مشترکِ هر دو مسیر)
# v1.14.276 — «\n شو نشون نده»: متنِ پرامپتها از مرجع با بکاسلشِ لفظی
# (دو نویسهٔ «\» و «n») کپی شده بود؛ در کادرِ ویرایشِ پرامپت
# (وبِ پی‌سی/لینوکس و اپِ اندروید) به‌صورتِ «\n» دیده میشد. حالا
# \nِ لفظی و \r\n به خطِ نوِ واقعی تبدیل میشوند — مدل هم فقط
# خطوطِ تمیز میبیند و نمایشِ کادر هم درست میشود.
def _prompt_real_lines(s: str) -> str:
    out = (s or "").replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n")
    while "\n\n\n" in out:
        out = out.replace("\n\n\n", "\n\n")
    return out

FLASH_PROMPT = _prompt_real_lines(FLASH_PROMPT)
FLASH_LITE_PROMPT = _prompt_real_lines(FLASH_LITE_PROMPT)
# بندِ ۶ (دستورِ سازنده — v1.14.262): بندِ قدیمیِ «SAFETY FALLBACK»
# خودش به مدل میگفت محدودشدهها را با '[CENSORED]' پر کند (سیاستِ
# اپِ مرجع) → مترجمِ واسط رویِ متنهایِ OCRِ بههمریخته (لاگِ گوشی:
# «ht doh op think, Puss?»، «XHALE*»، «业业人» …) بهجای ترجمهٔ
# حدسِ بهتر [CENSORED] مینوشت. حالا بندِ ۶ = «ورودیِ خامِ OCR است؛
# هیچ‌وقت رد/سانسور/جای‌نگهدار ننویس؛ بهترین حدسِ منظورِ دیالوگ را
# ترجمه کن» + صافیِ [CENSORED] در 80_translate (ناحیهٔ فیکشده
# بیترجمه میماند و دوباره پرسیده میشود).
MT_SYSTEM_PROTOCOL_ITEMS = "2. IDENTITY & TASK: You are an Expert Manga & Comic Dialogue Translation Engine.\r\n3. CONTEXT & READING FLOW: You receive an array of pages, each containing sequential dialogue text blocks. Translate them into natural, flowing Persian according to the provided translation rules.\r\n4. STRICT 1-TO-1 TRANSLATION:\r\n   - Maintain the exact sequence of dialogue blocks for each page.\r\n   - For every single input text block in a page's `dialogues`, produce exactly one corresponding entry with its original `en_text` and translated `fa_text`.\r\n   - NEVER skip, merge, reorder, or duplicate text blocks.\r\n5. EMPTY / NOISE: If a page has an empty `dialogues` list, output an empty array `[]` for its translations.\r\n6. RAW OCR INPUT — NO PLACEHOLDERS: The dialogue blocks are raw OCR output from comic pages; they may contain OCR errors, missing or garbled fragments. NEVER refuse, skip or sanitize any block, and NEVER output placeholders such as '[CENSORED]', '[REDACTED]' or \"I can't translate\". Even if a block looks broken or nonsensical, interpret the most likely intended dialogue and translate it into natural Persian."

# بلوکهای ژاپنی (فوریگانا) — فقط وقتی زبانِ مبدأ ژاپنی است (عینِ سازندهٔ درخواستِ متنیِ OpenAI در مرجع)
MT_JP_USER_DIRECTIVE = "\r\n*** CRITICAL MANDATORY DIRECTIVE FOR JAPANESE DIALOGUE BLOCKS ***\r\n1. FURIGANA / DUPLICATE CLEANUP: The input dialogue may contain both Kanji and its small Furigana phonetic reading captured together (e.g., '宿夏ライカ' or duplicated phrases). Identify the intended word/name and translate it ONLY ONCE. Do NOT translate both the Kanji and its phonetic reading.\r\n2. DEDUPLICATION: Eliminate accidental repeated words/syllables in the source block and produce exactly ONE clean, unified Persian translation.\r\n"
MT_JP_SYSTEM_RULE = "\r\n1. MANDATORY FURIGANA & DEDUPLICATION PURGE (HIGHEST PRIORITY):\r\n   - Input dialogue blocks may contain Kanji together with their small Furigana phonetic readings (e.g. '宿夏ライカ' or duplicated phrases).\r\n   - Recognize the word and translate it ONLY ONCE. Strip away phonetic duplicate readings and repeated words.\r\n   - Provide strictly ONE clean, unified Persian translation for each dialogue block.\r\n"

# اسکیمای پاسخ (عینِ JsonConvert.SerializeObject(…, Formatting.1) در مرجع)
MT_RESPONSE_SCHEMA_TEXT = "{\n  \"type\": \"ARRAY\",\n  \"description\": \"List of processed manga pages with their translations.\",\n  \"items\": {\n    \"type\": \"OBJECT\",\n    \"properties\": {\n      \"filename\": {\n        \"type\": \"STRING\",\n        \"description\": \"The filename of the image as provided.\"\n      },\n      \"translations\": {\n        \"type\": \"ARRAY\",\n        \"description\": \"Extracted text blocks and their translations.\",\n        \"items\": {\n          \"type\": \"OBJECT\",\n          \"properties\": {\n            \"en_text\": {\n              \"type\": \"STRING\",\n              \"description\": \"Exact original text from the dialogue input.\"\n            },\n            \"fa_text\": {\n              \"type\": \"STRING\",\n              \"description\": \"Creative, natural Persian translation.\"\n            }\n          },\n          \"required\": [\n            \"en_text\",\n            \"fa_text\"\n          ]\n        }\n      }\n    },\n    \"required\": [\n      \"filename\",\n      \"translations\"\n    ]\n  }\n}"

def mt_system_instruction(japanese: bool = False, with_schema: bool = False) -> str:
    """پروتکلِ سیستمیِ مرجع: بندهای ۲..۶؛ در مسیرِ OpenAI-compatible بندِ ۷ (اسکیما)
    هم پایینش می‌آید — در مسیرِ بومیِ Gemini اسکیما از response_schema می‌رود
    (عینِ سازندهٔ درخواستِ متنیِ بومیِ Gemini در مرجع در برابرِ سازندهٔ درخواستِ متنیِ OpenAI در مرجع)."""
    out = ("SYSTEM BEHAVIOR PROTOCOL:\r\n"
           + (MT_JP_SYSTEM_RULE if japanese else "")
           + "\r\n" + MT_SYSTEM_PROTOCOL_ITEMS)
    if with_schema:
        out += ("\r\n7. RESPONSE SCHEMA: Output must strictly conform to "
                "this JSON schema:\r\n" + MT_RESPONSE_SCHEMA_TEXT)
    return out

def mt_user_prompt(rules: str, pages, japanese: bool = False,
                   style_ref=None) -> str:
    """user prompt دقیقِ مرجع (سازندهٔ درخواستِ متنیِ OpenAI در مرجع/سازندهٔ درخواستِ متنیِ بومیِ Gemini در مرجع).
    pages = [{"filename": str, "dialogues": [str, …]}, …] — خروجیِ JSON با
    تورفتگیِ ۲ (عینِ Formatting.1) و بدونِ escapeِ یونیکد.
    style_ref = [(src, fa), …] — فقط در درخواست‌هایِ بعدی (تلاشِ مجدد/
    پسگیری/resume): لنگرِ سبک تا با عوض‌شدنِ توکن یا مدل، لحنِ فصل
    ثابت بماند (درخواستِ اولِ فصل خالی است = عینِ مرجع)."""
    import json as _json
    pages_json = _json.dumps(list(pages), ensure_ascii=False, indent=2)
    _style = ""
    if style_ref:
        _lines = []
        for _s, _f in style_ref[:10]:
            _s2 = str(_s).replace('\r', ' ').replace('\n', ' ')[:120]
            _f2 = str(_f).replace('\r', ' ').replace('\n', ' ')[:120]
            _lines.append('- "' + _s2 + '" -> "' + _f2 + '"')
        _style = ("\r\n\r\nSTYLE REFERENCE — earlier dialogue from this "
                  "same chapter was already translated (possibly by another "
                  "model or token). Your new translations MUST match its tone, "
                  "register and phrasing style exactly — same character "
                  "voices, same level of formality, same naming choices:\r\n"
                  + "\r\n".join(_lines) + "\r\n")
    return ("TASK: Translate the sequential dialogue blocks for the following "
            "manga pages into natural, high-quality Persian according to the "
            "rules below.\r\n"
            + (MT_JP_USER_DIRECTIVE if japanese else "")
            + "\r\nTRANSLATION RULES:\r\n" + (rules or "")
            + _style
            + "\r\n\r\nINPUT PAGES AND DIALOGUES (JSON):\r\n"
            + pages_json + "\r\n")

PROMPT_PRESETS = {
    "professional": FLASH_PROMPT,
    "lite": FLASH_LITE_PROMPT,
}
PROMPT_MODES = ("auto", "professional", "lite")

def resolve_prompt_mode(mode: str, provider: str = "gemini", model: str = "") -> str:
    """انتخابِ سبکِ پرامپت — عینِ مرجع: پیشفرض = حرفه‌ای
    (Prompts[0] در APK)؛ فقط مدل‌های «lite» پرامپتِ سبک می‌گیرند.
    مقدارِ قدیمیِ classic → مسیرِ خودکار (بر اساسِ مدل)."""
    m = (mode or "auto").lower().strip()
    if m in PROMPT_PRESETS:
        return m
    name = (model or "").lower().strip()
    if not name:
        try:
            name = str(PROVIDER_PRESETS["gemini"].get("default_model") or "").lower()
        except Exception:
            name = "gemini-3.5-flash-lite"
    if "lite" in name:
        return "lite"
    return "professional"

def prompt_preset_text(mode: str, provider: str = "gemini", model: str = "") -> str:
    return PROMPT_PRESETS[resolve_prompt_mode(mode, provider, model)]

def _norm_prompt_text(t: str) -> str:
    # v1.14.276 — \nِ لفظیِ پرامپتهایِ قدیمی هم برایِ مقایسه به خطِ نو
    # تبدیل میشود (بکاپ/کانفیگِ قدیمی = باز هم پیشفرض)
    t = (t or "").replace("\\n", "\n")
    return re.sub(r"\s+", " ", t.strip())

def is_known_default_instruction(text: str) -> bool:
    """آیا متنِ دستورِ دادهشده یکی از پیشفرضهایِ شناختهشده است؟
    (فقط پرامپتهایِ مرجع: professional/lite — )
     — فیکسِ «رویِ گوشی پرامپت auto نمیشود»: فرمِ گوشی فیلدِ
    دستور را با متنِ پیشفرض پُر میفرستاد و موتور آن را «سفارشی» میگرفت؛
    حالا متنِ برابرِ پیشفرضها سفارشی حساب نمیشود و مسیرِ سبک (auto) میرود."""
    t = (text or "").strip()
    if not t:
        return False
    tn = _norm_prompt_text(t)
    try:
        cands = [v for v in PROMPT_PRESETS.values() if isinstance(v, str)]
    except Exception:
        cands = []
    for c in cands:
        if c and _norm_prompt_text(c) == tn:
            return True
    return False

import os
import sys
import subprocess

os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_onednn", "0")
os.environ.setdefault("FLAGS_enable_pir_in_executor", "0")
os.environ.setdefault("FLAGS_enable_pir_api", "0")
os.environ.setdefault("FLAGS_pir_apply_shape_optimization_pass", "0")
# نسخهٔ اپ برایِ نشانِ کرشِ NNAPI در rapidocr_mobile
# (آپدیتِ اپ = فرصتِ تازه برایِ NNAPI؛ MANGA_APP_VER در _nnapi_guard_*)
os.environ.setdefault("MANGA_APP_VER", APP_VER)
os.environ.setdefault("CUDA_DEVICE_ORDER", "PCI_BUS_ID")

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

# باگِ تاریخی: `import platform as _platform` فقط داخلِ
# _ensure_all_dependencies بود (محدودهٔ محلیِ تابع) ولی _nvidia_gpu_present
# و _directx_gpu_present آن را در scopeِ ماژول میخوانند → NameError —
# یعنی تشخیصِ DirectMLِ ویندوز هیچ‌وقت اجرا نمیشد (و رویِ ویندوزِ
# بدونِ NVIDIA/DML کلِ بوت‌استرپ میمرد). حالا در سطحِ ماژول.
import platform as _platform
