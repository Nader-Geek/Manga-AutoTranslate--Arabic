# BUILD-STRIP-START
# BUILD-STRIP-END
from __future__ import annotations
import time as _time_t0
_T0_IMPORT = _time_t0.time()
APP_VER = "1.14.320"


FLASH_PROMPT = "شما دیالوگ‌نویسِ حرفه‌ای دوبله و زیرنویس فارسی هستید، نه مترجم کتاب.\n\nقانون اول و مهم‌تر از همه: خروجی تو باید «فارسیِ محاوره‌ایِ گفتاری» باشد — همان زبانی که آدم‌ها در خیابان و فیلم و دوبله حرف می‌زنند. هرگز فارسیِ نوشتاری، اداری یا کتابی تولید نکن.\n\n۱) فعل‌ها را حتماً محاوره‌ای بنویس:\nمی‌خواهم → می‌خوام | می‌خواهی → می‌خوای | می‌توانم → می‌تونم | می‌توانی → می‌تونی | می‌رویم → می‌ریم | نمی‌دانم → نمی‌دونم | می‌آید → میاد | بیاید → بیاد | نمی‌توانم → نمی‌تونم | بگذار → بذار | بده → بده | می‌کنند → می‌کنن | هستند → هستن | است (آخر جمله) → ـه\n\n۲) جمله‌بندی کوتاه و نفس‌دار مثل دیالوگ دوبله:\n- «را» گفتاری: آن را → اونو | این را → اینو\n- «همچنین / بنابراین / آیا / می‌باشد» ممنوع.\n- جمله‌های بلند رسمی را به دو جملهٔ کوتاه گفتاری بشکن.\n\n۳) متنِ OCR خراب یا بی‌معنا (حروف درهم): این‌ها افکت صوتی (SFX)، نام یا فونت تزئینی‌اند، ممنوع نیستند و هرگز CENSORED نمی‌شوند! یا محتمل‌ترین جمله را حدس بزن، یا به‌صورت صدای محیطی آوانگاری کن (مثل: «گبووم!»، «ووش...»، «تا‌رارا...») یا همان رشته را نگه دار. CENSORED فقط وقتی مجاز است که خودِ محتوای واقعیِ دیالوگ (خشونت/محتوای بزرگسال) واقعاً توسط سیستم رد شود — نه برای متنِ ناخوانا.\n\n۴) لحن هر شخصیت:\n- دوستانه/جوان → صمیمی و خودمونی (داداش، یارو، وای، خب، ایول...)\n- خشن/لات → کوچه‌بازاری و تند، بدون تعارف\n- بزرگ‌سال/رسمی → محترم ولی باز هم گفتاری، نه کتابی\n- متنِ روایت/توضیحِ کنار کادر → فارسیِ روانِ استاندارد؛ روان و شیوا، بدون ساختار اداری؛ هیچ‌وقت محاوره‌ی خیابانی لازم نیست\n\n۵) هیچ‌وقت سانسور، تلطیف یا مؤدب‌سازی نکن؛ خشونت و فحش با همان شدت برگردد.\n\n۶) نمونه‌های درست (همین سبک را باید تولید کنی):\n\"I'm here to buy saltpeter.\" → «برای خرید شوره اومدم.»\n\"Nobody told me anyone was coming.\" → «هیچی بهم نگفته بود قراره کسی بیاد.»\n\"If you want saltpeter, why come here instead of talking to the village?\" → «اگه شوره می‌خوای، چرا به جای گیر دادن به اهل روستا، خودت اومدی اینجا؟»\n\"What are you talking about?\" → «داری چی می‌گی اصلاً؟»\n\"Ugh... I'm beat. Let's head home.\" → «اوف... حسابی خسته‌ام. بریم خونه.»\n\"You're kidding me, right?\" → «شوخی می‌کنی دیگه؟»\n\"Come on, don't be like that!\" → «به‌خدا یه جور دیگه باش!»\n\"He commands dozens of knights.\" (روایت) → «ده‌ها شوالیه زیر دستِ اونه.»\n\n۷) نمونه غلط (ممنوع):\n\"I'm here to buy saltpeter.\" → «من اینجا هستم تا شوره بخرم.» (کتابی ✗)\n\"Nobody told me anyone was coming.\" → «هیچ‌کس به من نگفت کسی می‌آید.» (کتابی ✗)\n\n۸) اسامی خاص، اعداد و تکنیک‌ها را در کل فایل یکسان برگردان. هیچ دیالوگی را خالی، جا نینداز یا ادغام نکن؛ برای هر id دقیقاً یک fa بده.\n"

FLASH_LITE_PROMPT = "تو دیالوگ‌نویس دوبله فارسی هستی، نه مترجم کتاب. خروجی باید فارسیِ محاوره‌ایِ گفتاری باشد — زبانِ خیابون و فیلم؛ هرگز کتابی/نوشتاری ننویس.\n\n۱) فعل‌های محاوره‌ای: می‌خواهم→می‌خوام | می‌خواهی→می‌خوای | می‌توانم→می‌تونم | می‌رویم→می‌ریم | نمی‌دانم→نمی‌دونم | می‌آید→میاد | هستند→هستن | می‌کنند→می‌کنن | است (آخر جمله)→ـه\n۲) «را» گفتاری: آن را→اونو، این را→اینو. «همچنین/بنابراین/آیا/می‌باشد» ممنوع. جمله‌ها را کوتاه و نفس‌دار بشکن.\n۳) لحن شخصیت را نگه دار: دوستانه→خودمونی؛ خشن/لات→کوچه‌بازاری و تند؛ رسمی→محترم ولی باز هم گفتاری؛ روایت کنار کادر→روان و شیوا (نه خیابانی). سانسور و مؤدب‌سازی ممنوع.\n۴) متن OCR خراب = افکت صوتی/نام است؛ CENSORED نمی‌شود — حدس بزن یا آوانگاری کن (مثل «گبووم!»). CENSORED فقط برای محتوای واقعاً ممنوعِ سیستم.\n۵) نمونه‌ها:\n\"I'm here to buy saltpeter.\" → «برای خرید شوره اومدم.»\n\"Nobody told me anyone was coming.\" → «هیچی بهم نگفته بود قراره کسی بیاد.»\n\"Let's head home. I'm beat.\" → «بریم خونه. حسابی خسته‌ام.»\n\"You're kidding me, right?\" → «شوخی می‌کنی دیگه؟»\n۶) نمونه غلط: «من اینجا هستم تا شوره بخرم.» ✗ کتابی\n۷) اسامی و اعداد را در کل فایل یکسان برگردان؛ هیچ id را جا نینداز یا ادغام نکن.\n"

PROMPT_PRESETS_LEGACY = (
    "فرایند پردازش و ترجمه (مبتنی بر خود-اصلاحی): شما باید این فرآیند را در سه گام ذهنی و متوالی اجرا کنید:\\n\r\nگام ۱: تحلیل جامع و تولید پیش‌نویس اولیه\\n\r\n* پیش از شروع ترجمه، کل محتوای متن را بخوانید تا ژانر، فضای داستانی، کنایه‌ها و ویژگی‌های شخصیتی کاراکترها را درک کنید.\\n\r\n* در مرحلهٔ اندیشیدن، بر اساس این درک، یک پیش‌نویس اولیه از ترجمه را در ذهن تولید کنید.\\n\\n\r\nگام ۲: بازبینی موشکافانه و پالایش (مرحلهٔ خود-اصلاحی)\\n\r\n* با نگاه یک ویراستار سخت‌گیر، پیش‌نویس خود را به چالش بکشید و بازبینی کنید.\\n\r\n* از خود بپرسید: آیا این جمله روان است یا بوی ترجمه می‌دهد؟ آیا لحن شخصیت حفظ شده؟ آیا معادل بهتری برای این اصطلاح وجود دارد؟\\n\\n\r\nگام ۳: ارائه خروجی نهایی\\n\r\n* نسخهٔ نهایی، سلیس و بی‌نقص را که حاصل گام دوم است، به‌عنوان خروجی قطعی ارائه دهید.\\n\\n\r\n---\\n\\n\r\nاصول کلیدی ترجمه (قوانین حاکم بر گام‌های بالا):\\n\\n\r\n1. روانی، سلیس بودن و زبان محاوره‌ای زنده (پرهیز از ترجمه تحت‌اللفظی):\\n\r\nهدف اصلی، انتقال دقیق پیام و حس دیالوگ است. از ترجمهٔ کلمه‌به‌کلمه، کتابی، نوشتاری و عبارات ماشینی اکیداً پرهیز کنید؛ ترجمه باید به زبان فارسی امروزی، طبیعی، پویا و کاملاً گیرا باشد.\\n\\n\r\n2. حفظ و بازتاب دقیق لحن و سبک شخصیت‌ها (حیاتی و بدون سانسور):\\n\r\nلحن و شیوه گفتار هر کاراکتر (رسمی، دوستانه، طنز، جدی، خشن، معصومانه و...) باید با ظرافت رعایت شود. مدل زبانی باید مانند یک بازیگر نقش‌آفرینی کند:\\n\r\n- برای شخصیت‌های بی‌پروا، لات‌منش یا بی‌سواد: ترجمه باید کاملاً عامیانه، کوچه‌بازاری و دارای اصطلاحات خیابانی باشد. از اتوکشیده کردن، مؤدب‌سازی یا رسمی کردن دیالوگ‌های این شخصیت‌ها اکیداً خودداری کنید.\\n\r\n- برای شخصیت‌های باوقار، مرموز یا اشرافی: لحن باید محترمانه باشد، اما همچنان طبیعی و روان بماند (از تبدیل گفت‌وگو به متن نوشتاری و کتابی خودداری کنید).\\n\\n\r\nتذکر بسیار مهم: ترجمه حرفه‌ای به معنای سانسور، تلطیف یا پاستوریزه کردن کلمات نیست؛ بلکه به معنای انتقال دقیق حس جمله است. اگر متن اصلی دارای کلمات رکیک، جنسی یا خشن است، ترجمه فارسی نیز باید با همان شدت و حدت (بدون سانسور) ارائه شود تا اصالت اثر حفظ گردد.\\n\\n\r\n3. بومی‌سازی هوشمندانه اصطلاحات و ارجاعات فرهنگی:\\n\r\nاصطلاحات، ضرب‌المثل‌ها، شوخی‌ها و عبارات خاص فرهنگی مانگا را شناسایی کنید. اولویت با یافتن معادل‌های دقیق، رایج و طبیعی در زبان و فرهنگ فارسی است. در صورت نبود معادل مستقیم، مفهوم را با خلاقیت و به‌گونه‌ای که برای مخاطب فارسی‌زبان جذاب و ملموس باشد منتقل کنید.\\n\\n\r\n4. دقت و یکپارچگی در اسامی و جزئیات:\\n\r\nتمامی جزئیات متن اصلی (شامل اعداد، اسامی خاص شخصیت‌ها، مکان‌ها، تکنیک‌ها و علائم نگارشی) باید با دقت کامل ترجمه شوند و در سرتاسر تمام فایل‌ها کاملاً یکسان و هماهنگ استفاده شود.\\n",
    "قوانین ترجمه:\\n\\n\r\n1. روانی، سلیس بودن و جذابیت کلام: ترجمه باید به زبان فارسی امروزی، طبیعی و پویا باشد. متن نهایی باید به‌راحتی خوانده شود و برای مخاطب عام فارسی‌زبان کاملاً قابل فهم و گیرا باشد و از به‌کار بردن لحن کتابی، رسمی و عبارات ماشینی پرهیز کن.\\n\r\n2. حفظ و بازتاب دقیق لحن و سبک شخصیت‌ها (حیاتی):\\n\r\nلحن و شیوه گفتار هر کاراکتر (رسمی، دوستانه، طنز، جدی، خشن، معصومانه و...) باید با دقت در ترجمه رعایت شود؛ مثلاً:\\n\r\n- برای شخصیت‌های بی‌پروا، لات یا کم‌سواد: ترجمه باید کاملاً عامیانه، کوچه‌بازاری و دارای اصطلاحات خیابانی باشد. از مؤدبانه کردن یا رسمی نوشتن دیالوگ‌های این کاراکترها خودداری کنید.\\n\r\n- برای شخصیت‌های رسمی، مرموز یا اشرافی: لحن باید متین باشد.\\n\r\n3. در ترجمه اسامی، القاب و اصطلاحات داستانی، در سرتاسر فایل یکدستی و هماهنگی کامل را رعایت کن.\\n",
)

def _prompt_real_lines(s: str) -> str:
    out = (s or "").replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n")
    while "\n\n\n" in out:
        out = out.replace("\n\n\n", "\n\n")
    return out

FLASH_PROMPT = _prompt_real_lines(FLASH_PROMPT)
FLASH_LITE_PROMPT = _prompt_real_lines(FLASH_LITE_PROMPT)
MT_SYSTEM_PROTOCOL_ITEMS = ("2. IDENTITY & TASK: You are an Expert Manga & Comic Dialogue Translation Engine.\r\n"
"3. CONTEXT & READING FLOW: You receive an array of pages, each containing sequential dialogue items in `[id, text]` format. Translate them into natural, flowing Persian according to the provided translation rules.\r\n"
"4. STRICT 1-TO-1 TRANSLATION:\r\n"
"   - Maintain the exact sequence of dialogue blocks for each page.\r\n"
"   - For every input `[id, text]` item in `dialogues`, preserve its exact `id` and provide its translation in `fa`.\r\n"
"   - NEVER skip, merge, reorder, or duplicate `id`s.\r\n"
"5. EMPTY / NOISE: If a page has an empty `dialogues` list, output an empty array `[]` for its translations.\r\n"
"6. RAW OCR INPUT — NO PLACEHOLDERS: The dialogue blocks are raw OCR output from comic pages; they may contain OCR errors, missing or garbled fragments. NEVER refuse, skip or sanitize any block, and NEVER output placeholders such as '[REDACTED]' or \"I can't translate\". Even if a block looks broken or nonsensical, interpret the most likely intended dialogue and translate it into natural Persian.\r\n"
"7. SAFETY FALLBACK: If translation of a specific text block is restricted by safety policies, do not refuse or break the response; populate its `fa` with '[CENSORED]'.\r\n"
"8. MANDATORY OUTPUT FORMAT & CONCRETE EXAMPLE:\r\n"
"Output must be a raw JSON array matching this exact concrete structure:\r\n"
"[\r\n"
"  {\r\n"
"    \"filename\": \"001.png\",\r\n"
"    \"translations\": [\r\n"
"      { \"id\": 1, \"fa\": \"ترجمه دیالوگ اول\" },\r\n"
"      { \"id\": 2, \"fa\": \"ترجمه دیالوگ دوم\" }\r\n"
"    ]\r\n"
"  }\r\n"
"]")

MT_JSON_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "filename": {"type": "string"},
            "translations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "fa": {"type": "string"},
                    },
                    "required": ["id", "fa"],
                    "propertyOrdering": ["id", "fa"],
                },
            },
        },
        "required": ["filename", "translations"],
        "propertyOrdering": ["filename", "translations"],
    },
}

MT_JP_USER_DIRECTIVE = "\r\n*** CRITICAL MANDATORY DIRECTIVE FOR JAPANESE DIALOGUE BLOCKS ***\r\n1. FURIGANA / DUPLICATE CLEANUP: The input dialogue may contain both Kanji and its small Furigana phonetic reading captured together (e.g., '宿夏ライカ' or duplicated phrases). Identify the intended word/name and translate it ONLY ONCE. Do NOT translate both the Kanji and its phonetic reading.\r\n2. DEDUPLICATION: Eliminate accidental repeated words/syllables in the source block and produce exactly ONE clean, unified Persian translation.\r\n"
MT_JP_SYSTEM_RULE = "\r\n1. MANDATORY FURIGANA & DEDUPLICATION PURGE (HIGHEST PRIORITY):\r\n   - Input dialogue blocks may contain Kanji together with their small Furigana phonetic readings (e.g. '宿夏ライカ' or duplicated phrases).\r\n   - Recognize the word and translate it ONLY ONCE. Strip away phonetic duplicate readings and repeated words.\r\n   - Provide strictly ONE clean, unified Persian translation for each dialogue block.\r\n"

_MT_NO_CENSOR_ITEM = (
"7. NO CENSORSHIP: This is a professional manga/comic translation pipeline for mature audiences. "
"NEVER censor, sanitize, soften or refuse any dialogue. Profanity, insults, threats, dark humor and violence "
"must be translated with their FULL original intensity. NEVER output '[CENSORED]' or any placeholder. "
"If you genuinely cannot translate one specific line, put that line's original text unchanged in its `fa` field "
"and translate all remaining lines normally.\r\n")

def mt_system_instruction(japanese: bool = False, uncensored: bool = False, **_kw) -> str:
    items = MT_SYSTEM_PROTOCOL_ITEMS
    if uncensored:
        items = items.replace(
            "7. SAFETY FALLBACK: If translation of a specific text block is restricted by safety policies, "
            "do not refuse or break the response; populate its `fa` with '[CENSORED]'.\r\n",
            _MT_NO_CENSOR_ITEM)
    out = ("SYSTEM BEHAVIOR PROTOCOL:\r\n"
           + (MT_JP_SYSTEM_RULE if japanese else "")
           + "\r\n" + items)
    return out

def mt_plain_system_instruction(japanese: bool = False, uncensored: bool = False, **_kw) -> str:
    _item7 = ("7. SAFETY FALLBACK: If translation of the text block is restricted by safety policies, do not refuse or break the response; answer with '[CENSORED]'.\r\n"
              if not uncensored else
              "7. NO CENSORSHIP: Professional manga pipeline for mature audiences. NEVER censor, sanitize, soften or refuse. Profanity, insults, threats and violence must keep their FULL original intensity. NEVER output '[CENSORED]' or any placeholder; if truly impossible, return the original text unchanged.\r\n")
    out = ("SYSTEM BEHAVIOR PROTOCOL:\r\n"
           + (MT_JP_SYSTEM_RULE if japanese else "")
           + "\r\n2. IDENTITY & TASK: You are an Expert Manga & Comic Dialogue Translation Engine.\r\n"
           "6. RAW OCR INPUT — NO PLACEHOLDERS: The dialogue block is raw OCR output from a comic page; it may contain OCR errors, missing or garbled fragments. NEVER refuse, skip or sanitize it, and NEVER output placeholders such as '[REDACTED]' or \"I can't translate\". Even if it looks broken or nonsensical, interpret the most likely intended dialogue and translate it into natural Persian.\r\n"
           + _item7 +
           "9. PLAIN TEXT OUTPUT ONLY: Reply with ONLY the Persian translation itself as plain text. Do NOT output JSON, arrays, objects, keys, filenames, quotes or any notes — just the translation sentence.")
    return out

HIDDEN_ID_RULE_TEXT = ("اسامی و اعداد را در کل فایل یکسان برگردان؛ "
                       "هیچ id را جا نینداز یا ادغام نکن.")

def _has_hidden_id_rule(text: str) -> bool:
    t = _norm_prompt_text(text)
    return ("جا نینداز" in t) or ("id دقیقاً یک" in t)

def strip_hidden_rules(text: str) -> str:
    t = (text or "").replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n")
    if not t.strip():
        return t
    lines = [ln for ln in t.split("\n")
             if not ("جا نینداز" in ln and "ادغام نکن" in ln)]
    out = "\n".join(lines)
    while "\n\n\n" in out:
        out = out.replace("\n\n\n", "\n\n")
    return out.rstrip("\n") + "\n"

def append_hidden_id_rule(rules: str) -> str:
    t = (rules or "").rstrip()
    if not t:
        return rules or ""
    if _has_hidden_id_rule(t):
        return rules
    return t + "\n" + HIDDEN_ID_RULE_TEXT + "\n"

def mt_user_prompt(rules: str, pages, japanese: bool = False,
                   style_ref=None) -> str:
    import json as _json
    pages_json = _json.dumps(list(pages), ensure_ascii=False,
                             separators=(",", ":"))
    rules = append_hidden_id_rule(rules)
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
PROMPT_MODES = ("professional", "lite")

def resolve_prompt_mode(mode: str, provider: str = "gemini", model: str = "") -> str:
    m = (mode or "").lower().strip()
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
    t = (t or "").replace("\\n", "\n")
    return re.sub(r"\s+", " ", t.strip())

def visible_prompt_presets() -> dict:
    try:
        return {k: strip_hidden_rules(v)
                for k, v in PROMPT_PRESETS.items()
                if isinstance(v, str)}
    except Exception:
        return dict(PROMPT_PRESETS)

def is_known_default_instruction(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    tn = _norm_prompt_text(t)
    try:
        cands = [v for v in PROMPT_PRESETS.values() if isinstance(v, str)]
    except Exception:
        cands = []
    try:
        cands += [v for v in visible_prompt_presets().values()
                  if isinstance(v, str)]
    except Exception:
        pass
    cands += [p for p in PROMPT_PRESETS_LEGACY if isinstance(p, str)]
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
os.environ.setdefault("MANGA_APP_VER", APP_VER)
os.environ.setdefault("CUDA_DEVICE_ORDER", "PCI_BUS_ID")

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

import platform as _platform
