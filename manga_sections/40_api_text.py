# BUILD-STRIP-START
# سرویسهای AI و ابزارهای متن — پریستها، کلیدها، TextRegion، لحن
# PROVIDER_PRESETS، آزمایشِ کلیدها، source_has_letters، TextRegion (dataclass)، BalloonToneClassifier و وضعیتِ live.
# (این سربرگ فقط راهنمای همین فایل است؛ لودرِ manga.py و بیلد حذفش میکنند)
# BUILD-STRIP-END
PROVIDER_PRESETS = {
    "gemini": {
        "type": "gemini",
        "default_model": "gemini-3.5-flash-lite",  # پیشفرضِ جدید (Flash-Lite)
        "env_key": "GEMINI_API_KEY",
    },
    "gemini-openai": {
        "type": "openai",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
# gemini-3.5-flash (بدونِ Lite) دیگر در فهرستِ مدلهایِ
# زنده نیست → نزدیکترینِ پایدار: gemini-3.6-flash
        "default_model": "gemini-3.6-flash",
        "env_key": "GEMINI_API_KEY",
    },
    "openai": {
        "type": "openai",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
    },
    "chatgpt": {
        "type": "openai",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
    },
    "deepseek": {
        "type": "openai",
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
    },
    "groq": {
        "type": "openai",
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
    },
    "xai": {
        "type": "openai",
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-2-latest",
        "env_key": "XAI_API_KEY",
    },
    "grok": {
        "type": "openai",
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-2-latest",
        "env_key": "XAI_API_KEY",
    },
    "together": {
        "type": "openai",
        "base_url": "https://api.together.xyz/v1",
        "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "env_key": "TOGETHER_API_KEY",
    },
    "openrouter": {
        "type": "openai",
        "base_url": "https://openrouter.ai/api/v1",
# google/gemini-2.0-flash-001 سمتِ گوگل خاموش شده
# مدلِ زندهٔ فعلیِ OpenRouter: google/gemini-3.8-flash
        "default_model": "google/gemini-3.8-flash",
        "env_key": "OPENROUTER_API_KEY",
    },
    "ollama": {
        "type": "openai",
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3.2",
        "env_key": "OLLAMA_API_KEY",
    },
    "custom": {
        "type": "openai",
        "base_url": "",
        "default_model": "",
        "env_key": "CUSTOM_API_KEY",
    },
}

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

# فرمت‌های API که «کلید کاستوم» می‌فهمد ──────────────────────────────
# 1) OpenAI Chat Completions …/chat/completions
# 2) OpenAI Responses API …/responses
# 3) Anthropic Compatible …/messages
# 4) Google Generative AI …:generateContent
CUSTOM_API_FORMAT_HINTS = {
    "openai": "OpenAI Chat Completions (/chat/completions)",
    "openai-responses": "OpenAI Responses API (/responses)",
    "anthropic": "Anthropic Compatible (/messages)",
    "google-endpoint": "Google Generative AI (:generateContent)",
}

def detect_custom_api_format(url: str) -> Tuple[str, str]:
    """فرمت API را از خودِ لینک تشخیص می‌دهد و لینک را به Base URL
    تمیز تبدیل می‌کند. کاربر می‌تواند هرکدام از این‌ها را بچسباند:
      https://opencode.ai/inference/openai/v1/chat/completions → openai
      https://opencode.ai/inference/openai/v1/responses → openai-responses
      https://opencode.ai/inference/anthropic/v1/messages → anthropic
      https://…/v1beta/models/gemini-2.0-flash:generateContent → google-endpoint
    لینک بدون پسوند → openai (پیش‌فرض سازگار با OpenAI)
    خروجی: (نوع_فرمت, base_url_تمیز)"""
    u = str(url or "").strip().strip('"').strip("'").rstrip("/")
    if not u:
        return "openai", ""
# Google Generative AI: …/models/MODEL:generateContent
    if ":generateContent" in u or ":streamGenerateContent" in u:
        cut = u.find(":generateContent")
        if cut < 0:
            cut = u.find(":streamGenerateContent")
        u = u[:cut]
        if "/models/" in u:
            u = u[: u.rfind("/models/")]
        elif u.endswith("/models"):
            u = u[: -len("/models")]
        return "google-endpoint", u.rstrip("/")
    low = u.lower()
    for suffix, ftype in (
        ("/chat/completions", "openai"),
        ("/responses", "openai-responses"),
        ("/messages", "anthropic"),
        ("/completions", "openai"),
    ):
        if low.endswith(suffix):
            return ftype, u[: -len(suffix)].rstrip("/")
    return "openai", u

def explain_api_http_error(code: int, body: str) -> Tuple[bool, str]:
    """خطای HTTP یک سرویس AI را به پیام فارسیِ قابل‌فهم تبدیل می‌کند.
    خروجی: (کلید_سالم_هست؟, پیام) — بعضی خطاها ربطی به کلید ندارند
    (مثل FreeTierError اوپن‌کد یا «مدل در دسترس نیست») و کلید سالم است."""
    b = str(body or "")
    bl = b.lower()
    if ("freetiererror" in bl or "within opencode" in bl
            or "free tier" in bl and "opencode" in bl):
        return True, ("کلید سالم است ✅ ولی مدل‌های «free» اوپن‌کد فقط داخل "
                      "خود برنامهٔ OpenCode کار می‌کنند و از بیرون رد می‌شوند "
                      "— باید مدل پولی همان سرویس یا کلید/سرویس دیگری بگذاری")
    if ("model is unavailable" in bl or "model_not_found" in bl
            or "does not exist" in bl or "no such model" in bl
            or "model not found" in bl
            or "not allowed to access" in bl
            or "does not have access" in bl
            or "unavailable model" in bl):
        return True, ("کلید پذیرفته شد ✅ ولی این مدل در سرویس فعال نیست "
                      "— نام مدل را عوض کن (مدل باید در پنل سرویس فعال/موجود باشد)")
    if ("quota" in bl and ("exceed" in bl or "exceeded" in bl)) \
            or "insufficient_quota" in bl or "billing" in bl \
            or "insufficient credit" in bl or "credit balance" in bl:
        return True, "کلید سالم است ✅ ولی اعتبار/سهمیهٔ حساب تمام شده"
    if "invalid api key" in bl or ("invalid" in bl and "key" in bl) \
            or "unauthorized" in bl or "authentication" in bl \
            or "invalid_api_key" in bl or "wrong api key" in bl:
        return False, "کلید نامعتبر است — کلید را دوباره چک کن"
    if code in (401, 403):
        return False, f"کلید نامعتبر/رد شد ({code})"
    if code == 429:
        return True, "معتبر ولی Rate-limit (429) — کمی بعد دوباره"
    if code == 402:
        return True, "کلید سالم است ✅ ولی اعتبار حساب تمام شده (402)"
    if code == 404:
        return True, ("کلید پذیرفته شد ✅ ولی این آدرس/مدل روی سرویس نیست "
                      "(404) — لینک و نام مدل را چک کن")
    detail = " ".join(b.split())[:120]
    return False, f"HTTP {code}" + (f" — {detail}" if detail else "")

def test_api_keys(keys_text: str, provider: str = "gemini",
                  api_base: str = "", timeout: float = 15.0,
                  model: str = "") -> list:
    """تست سریع کلیدهای API (تکی/چندتایی) و لینک سفارشی — برای دکمهٔ
    «تست کلید» در همهٔ پلتفرم‌ها (وب/پی‌سی/اندروید). هر کلید با یک
    درخواست سبک (لیست مدل‌ها؛ اگر نبود POST سبک با مدلِ خودِ کاربر)
    بررسی می‌شود؛ نتیجهٔ هر کلید جدا برمی‌گردد: [{'key': 'مخفی‌شده',
    'ok': True/False, 'error': '...', 'ms': 123}, ...]"""
    import urllib.request
    import urllib.error
    import urllib.parse
    import time as _time

    keys = [k.strip() for k in re.split(r"[\s,;\n]+", str(keys_text or ""))
            if k.strip()]
    if not keys:
        return [{"key": "", "ok": False, "error": "کلیدی وارد نشده", "ms": 0}]

    prov = str(provider or "gemini").strip().lower()
    if prov not in PROVIDER_PRESETS:
        prov = "gemini"
    preset = PROVIDER_PRESETS[prov]
    base = normalize_api_base(api_base) or (preset.get("base_url") or "")
    user_model = str(model or "").strip()

    def _mask(k: str) -> str:
        if len(k) <= 12:
            return "***"
        return k[:7] + "…" + k[-4:]

    results = []
    for k in keys:
        r = {"key": _mask(k), "ok": False, "error": "", "ms": 0}
        t0 = _time.time()
        try:
            if preset["type"] == "gemini" and not api_base:
                url = ("https://generativelanguage.googleapis.com/"
                       "v1beta/models?key=" + urllib.parse.quote(k)
                       + "&pageSize=1")
                req = urllib.request.Request(
                    url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    r["ok"] = (getattr(resp, "status", 200) == 200)
                    r["error"] = "" if r["ok"] else f"HTTP {resp.status}"
            else:
                if not base:
                    raise ValueError("لینک (Base URL) وارد نشده")
                ftype, fbase = detect_custom_api_format(base)
                fbase = fbase.rstrip("/")
                if ftype == "anthropic":
# POST سبک /v1/messages — Anthropic یا پراکسی سازگارش
                    post_url = fbase if fbase.endswith("/v1") else fbase + "/v1"
                    post_url += "/messages"
                    body = json.dumps({
                        "model": user_model or "claude-3-5-haiku-20241022",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "hi"}],
                    }).encode("utf-8")
                    req = urllib.request.Request(
                        post_url, data=body, method="POST",
                        headers={
                            "User-Agent": "Mozilla/5.0",
                            "Content-Type": "application/json",
                            "x-api-key": k,
                            "anthropic-version": "2023-06-01",
                            "Authorization": "Bearer " + k,
                        })
                    with urllib.request.urlopen(req, timeout=timeout) as resp:
                        r["ok"] = (getattr(resp, "status", 200) == 200)
                        r["error"] = "" if r["ok"] else f"HTTP {resp.status}"
                elif ftype == "google-endpoint":
# POST سبک :generateContent — Google یا پراکسی سازگارش
                    gmodel = user_model or "gemini-3.5-flash-lite"
                    post_url = fbase + "/models/" \
                        + urllib.parse.quote(gmodel) + ":generateContent"
                    body = json.dumps({
                        "contents": [{"parts": [{"text": "hi"}]}],
                        "generationConfig": {"maxOutputTokens": 1},
                    }).encode("utf-8")
                    req = urllib.request.Request(
                        post_url, data=body, method="POST",
                        headers={
                            "User-Agent": "Mozilla/5.0",
                            "Content-Type": "application/json",
                            "x-goog-api-key": k,
                            "Authorization": "Bearer " + k,
                        })
                    with urllib.request.urlopen(req, timeout=timeout) as resp:
                        r["ok"] = (getattr(resp, "status", 200) == 200)
                        r["error"] = "" if r["ok"] else f"HTTP {resp.status}"
                else:
# openai / openai-responses → اول GET /models سبک
                    url = fbase.rstrip("/")
                    if not url.endswith("/v1"):
                        url += "/v1"
                    url += "/models"
                    req = urllib.request.Request(
                        url, headers={
                            "User-Agent": "Mozilla/5.0",
                            "Authorization": "Bearer " + k,
                        })
                    try:
                        with urllib.request.urlopen(
                                req, timeout=timeout) as resp:
                            r["ok"] = (getattr(resp, "status", 200) == 200)
                            r["error"] = ("" if r["ok"]
                                          else f"HTTP {resp.status}")
                    except urllib.error.HTTPError as e2:
                        if e2.code in (404, 405):
# سرور /models ندارد → POST سبک روی خودِ endpoint
                            m = user_model or "gpt-4o-mini"
                            if ftype == "openai-responses":
                                post_url = fbase.rstrip("/") + "/responses"
                                body = json.dumps({
                                    "model": m,
                                    "input": "hi",
                                    "max_output_tokens": 16,
                                }).encode("utf-8")
                            else:
                                post_url = (fbase.rstrip("/")
                                            + "/chat/completions")
                                body = json.dumps({
                                    "model": m,
                                    "messages": [{"role": "user",
                                                  "content": "hi"}],
                                    "max_tokens": 1,
                                }).encode("utf-8")
                            req2 = urllib.request.Request(
                                post_url, data=body, method="POST",
                                headers={
                                    "User-Agent": "Mozilla/5.0",
                                    "Content-Type": "application/json",
                                    "Authorization": "Bearer " + k,
                                })
                            with urllib.request.urlopen(
                                    req2, timeout=timeout) as resp:
                                r["ok"] = (getattr(resp, "status", 200) == 200)
                                r["error"] = ("" if r["ok"]
                                              else f"HTTP {resp.status}")
                        else:
                            raise
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = (e.read() or b"")[:600].decode("utf-8", "ignore")
            except Exception:
                pass
            ok, msg = explain_api_http_error(e.code, body)
            r["ok"] = ok
            r["error"] = msg
        except urllib.error.URLError as e:
            r["error"] = f"اتصال برقرار نشد: {getattr(e, 'reason', e)}"
        except Exception as e:
            r["error"] = str(e)[:160]
        r["ms"] = int((_time.time() - t0) * 1000)
        results.append(r)
    return results

def format_key_test_text(res: list) -> str:
    """قالب یکسان نتیجهٔ تست کلیدها برای وب / پی‌سی / اندروید.
    هر کلید با / / مشخص می‌شود؛ بعد از ۶۰ ثانیه در رابط پاک می‌شود."""
    if not res:
        return "کلیدی وارد نشده"
    lines = []
    for i, r in enumerate(res, 1):
        key = str(r.get("key", "") or "***")
        ms = int(r.get("ms") or 0)
        err = str(r.get("error") or "")
        if r.get("ok") and err:
            lines.append(f"⚠️ کلید {i} ({key}): سالم ولی هشدار — {err}  [{ms}ms]")
        elif r.get("ok"):
            lines.append(f"✔ کلید {i} ({key}): سالم است  [{ms}ms]")
        else:
            lines.append(f"✘ کلید {i} ({key}): خراب" + (f" — {err}" if err else "") + f"  [{ms}ms]")
    return "\n".join(lines)

def source_has_letters(text: str) -> bool:
    """ — . متنی که «هیچ" 
    حرفی» (دستهٔ یونیکدِ L) ندارد — '123124'، './….'، '[] ,./???!?~' —
    به مترجم نمی‌رود و فقط پاکسازی میشود؛ «hi…» حرف دارد → ترجمه
    میشود. PC/لینوکس/اندروید یکسان."""
    _t = str(text or "")
    _letters = [_ch for _ch in _t if _ch.isalpha()]
    if not _letters:
        return False
# «10,000G» (طلا/ارزِ بازی): یک حرفِ لاتینِ تنها چسبیده به رقم =
# پسوندِ واحد، نه کلمه — ترجمه‌اش دور ریختنِ وقتِ AI است. «hi…»
# «A» (بدون رقم) و هر متنِ چندحرفیِ واقعی ترجمه میشوند.
    if len(_letters) == 1 and _letters[0].isascii() \
            and any(_c.isdigit() for _c in _t):
        return False
    return True

# لیستِ آفلاینِ مدلهایِ Gemini (پیش‌فرضِ برنامه) — عینِ فهرستِ
# ۷تاییِ سازنده (v1.14.288): «gemini-3.5-flash-lite,
# gemini-3.1-flash-lite,gemini-3.8-flash,gemini-3.7-flash,
# gemini-3.6-flash,gemini-3.5-flash,gemini-3-flash-preview».
# این فقط فهرستِ «پیش‌فرض/آفلاین» است — رایگان بودن یا کتابی
# بودنِ هیچ مدلی اینجا با نام تشخیص داده نمیشود (دستورِ
# v1.14.289/290: هیچ نامی دستی نوشته نشود). وقتی رفرش زده
# شود و اینترنت باشد، فهرستِ زنده از گوگل گرفته میشود و
# «سنجشِ زنده» (gemini_style_probe) خودش هر مدلی را که جواب
# نمیدهد (پولی/سهمیه) یا کتابی مینویسد کنار میگذارد — مدلِ
# جدیدِ رایگانِ گوگل هرچه باشد خودش میآید.
GEMINI_FLASH_MODELS_OFFLINE = [
    "gemini-3.5-flash-lite",     # پایدارِ سبک — پیش‌فرضِ برنامه
    "gemini-3.1-flash-lite",     # پایدارِ سبک
    "gemini-4-hydrogen",         # نسلِ ۴ (دستورِ v1.14.291)
    "gemini-3.8-flash",          # جدیدترین Flash کامل
    "gemini-3.7-flash",          # Flash کامل
    "gemini-3.6-flash",          # پایدارِ کامل
    "gemini-3.5-flash",          # Flash کامل
    "gemini-3-flash-preview",    # preview
]

def gemini_offline_models() -> List[str]:
    """ — رونوشتِ مرتبِ لیستِ آفلاین (برایِ دراپ‌داونِ وب و
    فال‌بکِ دکمهٔ ↻ اندروید/وب وقتی اتصال برقرار نشد)."""
    return list(GEMINI_FLASH_MODELS_OFFLINE)

# ── سنجشِ زندهٔ سبکِ مدل (v1.14.290) ─────────────────────────────
# دستورِ سازنده: «چیزی نداره بتونع بفهمه کدوم مدل کتابی میده بیرون؟
# فقط اونای که اوکی خروجی میده نگه داره» + «خودش باید بفهمه کدوم
# مدلها رایگانه — دستی ممنوع». پس هیچ نامِ مدلی (نه فهرستِ سیاهِ
# پولیها، نه لیستِ سفید) در کد نیست؛ تشخیص از رویِ «رفتارِ» خودِ
# مدل است — یک درخواستِ واقعیِ کوچک به هر مدلِ زنده فرستاده
# میشود (۴ خطِ دیالوگِ محاوره‌ای) و نتیجه معلوم میشود:
#   • پاسخ نداد (پولی/سهمیه/قطعی/خاموش) → کنار میرود
#     ← رایگان بودن هم همینجا خودکار معلوم میشود
#   • جوابش کتابی/رسمی بود (می‌باشد، آیا، بیایید…) → کنار میرود
#   • جوابش سالم و محاوره‌ای بود (می‌خوام، بریم، وای…) → میماند
# مدلِ جدیدِ گوگل هرچه باشد (flash یا نه، هر نامی) خودش پیدا میشود.
_GEMINI_PROBE_PROMPT = (
    "این دیالوگ‌های مانگا را به فارسیِ محاوره‌ایِ طبیعیِ گفتاری "
    "ترجمه کن — دقیقاً ۴ خطِ شماره‌دار. لحن: صمیمی و کوچه‌بازاری؛ "
    "هرگز کتابی/رسمی/نوشتاری ننویس.\n"
    "1. Hey, watch this!\n"
    "2. No way! You're kidding me, right?\n"
    "3. Ugh... I'm beat. Let's head home.\n"
    "4. Come on, don't be like that!"
)

# نشانه‌های «کتابی» در جوابِ همین تست (فقط همین جملات؛ لحنِ
# عامیانه هرگز اینها را نمینویسد):
_GEMINI_BOOKISH_MARKERS = (
    "می‌باشد", "می‌باشند", "می‌باشیم", "می‌باشید",
    "آیا", "بنابراین", "می‌گردد", "گردید", "می‌بایست",
    "خواهد بود", "خواهد شد", "خواهد رفت", "خواهد کرد",
    "می‌خواهم", "می‌خواهی", "می‌خواهیم", "می‌توانم",
    "می‌توانی", "می‌رویم", "نمی‌دانم", "لطفاً", "منزل",
)

# نشانه‌های «محاوره‌ای» — مدلِ سالم برایِ همین دیالوگها اینها را
# مینویسد (می‌خوام، بریم، وای، میزاب…):
_GEMINI_CASUAL_MARKERS = (
    "می‌خوام", "می‌خوای", "می‌تونم", "می‌تونی", "می‌ریم",
    "بریم", "بذار", "بزار", "ببین", "نمی‌دونم", "نمی‌دونی",
    "میزاب", "شوخی", "وای", "خب", "ایول", "یارو",
    "خسته‌ام", "خسته‌م", "جمدی", "باور",
)

def _gemini_probe_norm(text: str) -> str:
    """نرمال‌سازی برایِ مقایسهٔ نشانه‌ها (نیم‌فاصله/علامتِ راست‌به‌چپ
    حذف میشوند تا «می‌خواهم» و «میخواهم» هر دو گرفته شوند)."""
    return str(text or "").replace("\u200c", "").replace("\u200f", "")

def _gemini_probe_score(text: str) -> Tuple[str, List[str], List[str]]:
    """امتیازِ سبکِ جوابِ تست: ok (محاوره‌ای/خنثی) یا bookish.
    قانون: دو نشانهٔ کتابی یا «کتابی بدونِ حتی یک نشانهٔ محاوره‌ای»
    = کتابی؛ خنثیِ بی‌نشانه هم اوکی است — تقصیرِ مدل نیست."""
    norm = _gemini_probe_norm(text)
    bookish = [m for m in _GEMINI_BOOKISH_MARKERS
               if _gemini_probe_norm(m) in norm]
    casual = [m for m in _GEMINI_CASUAL_MARKERS
              if _gemini_probe_norm(m) in norm]
    verdict = "ok"
    if len(bookish) >= 2 or (bookish and not casual):
        verdict = "bookish"
    return verdict, bookish, casual

def gemini_style_probe(model: str, api_key: str,
                       timeout: float = 24.0) -> dict:
    """یک درخواستِ واقعیِ کوچک به مدل: ۴ خطِ دیالوگِ محاوره‌ای.
    خروجی: {"verdict": ok|bookish|error, "reason": …, "text": …}
    error = خودِ مدل جواب نداد (پولی/سهمیه/قطعی) — رایگان نبودن هم
    همینجا خودکار معلوم میشود؛ هیچ نامی در کد نیست."""
    import urllib.request
    import urllib.error
    import urllib.parse
    model = str(model or "").replace("models/", "").strip()
    key = str(api_key or "").strip()
    if not model or not key:
        return {"verdict": "error", "reason": "مدل/کلید خالی", "text": ""}
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           + urllib.parse.quote(model)
           + ":generateContent?key=" + urllib.parse.quote(key))
    body = {"contents": [{"role": "user",
                          "parts": [{"text": _GEMINI_PROBE_PROMPT}]}],
            "generationConfig": {"temperature": 0.7,
                                 "maxOutputTokens": 400}}
    try:
        req = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(2 * 1024 * 1024)
            data = json.loads(raw.decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            detail = str(e.read(400), "utf-8", "replace")
        except Exception:
            detail = ""
        why = f"HTTP {e.code}" + (f" — {detail[:110]}" if detail else "")
        return {"verdict": "error", "reason": why, "text": ""}
    except Exception as e:
        return {"verdict": "error",
                "reason": str(e).split(chr(10))[0][:110], "text": ""}
    parts: List[str] = []
    try:
        for cand in (data.get("candidates") or []):
            for p in ((cand.get("content") or {}).get("parts") or []):
                _t = str(p.get("text") or "")
                if _t:
                    parts.append(_t)
    except Exception:
        parts = []
    text = "\n".join(parts).strip()
    if not text:
        return {"verdict": "error",
                "reason": "پاسخِ خالی (سهمیه/مدلِ خاموش)", "text": ""}
    _fa = [ch for ch in text if "\u0600" <= ch <= "\u06ff"]
    if len(_fa) < 12:
        return {"verdict": "error", "reason": "متنِ فارسی در پاسخ نبود",
                "text": text[:80]}
    verdict, bookish, casual = _gemini_probe_score(text)
    reason = ("محاوره‌ای ✓"
              + (f" ({len(casual)} نشانه)" if casual else "")
              ) if verdict == "ok" else (
              "کتابی ✗ — " + "، ".join(bookish[:3]))
    return {"verdict": verdict, "reason": reason, "text": text[:200]}

# کشِ نتیجه‌ها: سنجشِ موفق ۶ ساعت، سنجشِ خطادار ۱۰ دقیقه معتبر
# است (رفرشِ بعدی همان جوابِ کش را میدهد — نه خرجِ دوباره).
_GEMINI_STYLE_CACHE: dict = {}
_GEMINI_STYLE_TTL_OK_S = 6.0 * 3600.0
_GEMINI_STYLE_TTL_ERR_S = 600.0

def gemini_style_probe_many(models, keys_text, timeout: float = 24.0,
                            max_workers: int = 8, fresh: bool = False
                            ) -> Tuple[List[str], dict]:
    """سنجشِ زندهٔ همهٔ مدلها (دکمهٔ ↻ فهرست + چرخِ ترجمه):
    هر مدل یک تستِ کوچک میگیرد — فقط پاسخ‌دهندهٔ محاوره‌ای در
    خروجی میماند (دستورِ v1.14.290: «فقط اونای که اوکی خروجی میده
    نگه داره»). چند-کلیدی: تا ۳ کلید امتحان میشود. موازی
    (ThreadPool) تا ۸ مدل همزمان. خروجی: (مدلهایِ سالم،
    {مدل: نتیجه})."""
    import time as _time
    from concurrent.futures import ThreadPoolExecutor
    keys = [k.strip() for k in re.split(r"[\s,;\n]+", str(keys_text or ""))
            if k.strip()]
    models = [str(m or "").replace("models/", "").strip()
              for m in (models or []) if str(m or "").strip()]
    if not models:
        return [], {}
    now = _time.time()
    results: dict = {}
    todo: List[str] = []
    for m in models:
        hit = _GEMINI_STYLE_CACHE.get(m)
        if hit:
            ttl = (_GEMINI_STYLE_TTL_OK_S
                   if hit[1].get("verdict") == "ok"
                   else _GEMINI_STYLE_TTL_ERR_S)
            if not fresh and (now - hit[0]) < ttl:
                results[m] = hit[1]
                continue
        todo.append(m)

    def _work(m: str):
        last = {"verdict": "error", "reason": "کلیدی نبود", "text": ""}
        for k in keys[:3]:
            last = gemini_style_probe(m, k, timeout)
            if last.get("verdict") != "error":
                break
        return m, last

    if todo:
        try:
            with ThreadPoolExecutor(max_workers=max(1, max_workers)) as ex:
                for m, r in ex.map(_work, todo):
                    results[m] = r
                    _GEMINI_STYLE_CACHE[m] = (_time.time(), r)
        except Exception:
            for m in todo:
                if m not in results:
                    results[m] = {"verdict": "error",
                                  "reason": "سنجش انجام نشد", "text": ""}
    good = [m for m in models
            if (results.get(m) or {}).get("verdict") == "ok"]
    return good, results

def parse_model_list(raw: str) -> List[str]:
    """رشتهٔ «چند مدلِ» کاربر را به فهرستِ تمیز تبدیل میکند.
    جداکننده: کاما / خطِ نو / فاصله / سمی‌کلون — مثال:
      'gemini-3.5-flash-lite, gemini-3.1-flash-lite'
      'gpt-4o-mini,deepseek-chat'"""
    if isinstance(raw, (list, tuple)):
        items = [str(x) for x in raw]
    else:
        items = re.split(r"[\s,;\n]+", str(raw or ""))
    out: List[str] = []
    for m in items:
        m = m.strip().strip('"').strip("'")
        if m and m not in out:
            out.append(m)
    return out

def join_model_list(models: List[str]) -> str:
    """فهرستِ مدلها به رشتهٔ نمایشیِ کاما-جدا (برای فرم/UI)."""
    return ", ".join(str(m or "").strip() for m in (models or [])
                      if str(m or "").strip())

def list_provider_models(provider: str, keys_text: str, api_base: str = "",
                         timeout: float = 20.0) -> Tuple[List[str], str]:
    """ — فهرستِ مدلهایِ موجود از خودِ سرویس (). Gemini: GET v1beta/models
    — فهرستِ خامِ زنده (صافیِ _is_bad_list_model فقط برایِ مدلهایِ
    غیرمتنی/مُردهٔ نسلِ ۱-۲). رایگان بودن و «کتابی نبودنِ» جواب با
    «سنجشِ زنده» (gemini_style_probe_many — تستِ کوچکِ واقعی به
    خودِ مدل) بعد از همین تابع انجام میشود؛ هیچ تشخیصی از رویِ
    نامِ مدل انجام نمیشود (دستورِ سازنده: «خودش باید بفهمه کدوم
    مدلها رایگانه؛ فقط اونای که اوکی خروجی میده نگه داره»).
    custom: GET /models بر اساسِ فرمتِ خودکارِ لینک
    (openai/responses/anthropic/google). خروجی: (مدلها، خطا). برایِ دکمهٔ
    ↻ فهرستِ مدلها در رابط."""
    import urllib.request
    import urllib.error
    import urllib.parse

    prov = str(provider or "gemini").strip().lower()
    keys = [k.strip() for k in re.split(r"[\s,;\n]+", str(keys_text or ""))
            if k.strip()]

    def _get(url: str, headers: dict) -> Tuple[Optional[dict], str]:
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0", **headers})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read(4 * 1024 * 1024)
                return json.loads(raw.decode("utf-8", "replace")), ""
        except urllib.error.HTTPError as e:
            return None, f"HTTP {e.code}"
        except Exception as e:
            return None, str(e).split(chr(10))[0][:120]

    tried = 0
    for k in keys:
        tried += 1
        if prov == "gemini":
            url = ("https://generativelanguage.googleapis.com/v1beta/models"
                   "?key=" + urllib.parse.quote(k) + "&pageSize=200")
            data, err = _get(url, {})
            if not data:
                continue
            out: List[str] = []
            for it in (data.get("models") or []):
                name = str(it.get("name") or "").strip()
                if name.startswith("models/"):
                    name = name[len("models/"):]
                if not name:
                    continue
                meths = it.get("supportedGenerationMethods") or []
                if meths and "generateContent" not in meths:
                    continue
                if MangaTranslator._is_bad_list_model(name):
                    continue
# رایگان/پولی و کتابی/محاوره‌ای اینجا با نامِ مدل تشخیص
# داده نمیشود (دستورِ v1.14.290) — فهرستِ خامِ زنده برگردد و
# «سنجشِ زنده» (gemini_style_probe_many؛ در _refresh_model_list
# و چرخِ ترجمه) خودش هر مدل را با یک درخواستِ واقعیِ کوچک
# میآزماید: بی‌پاسخ (پولی/سهمیه) یا کتابی = حذف.
                out.append(name)
            if out:
                return sorted(set(out), key=MangaTranslator._model_sort_key), ""
            if data.get("models") is not None:
                return [], "مدلی پیدا نشد"
            continue
# custom — بر اساسِ فرمتِ لینک
        base = normalize_api_base(api_base) or ""
        if not base:
            return [], "لینک (Base URL) وارد نشده"
        ftype, fbase = detect_custom_api_format(base)
        fbase = fbase.rstrip("/")
        if ftype == "anthropic":
            u = (fbase if fbase.endswith("/v1") else fbase + "/v1") + "/models"
            data, err = _get(u, {"x-api-key": k,
                                 "anthropic-version": "2023-06-01"})
        elif ftype == "google-endpoint":
            u = fbase + "/models?key=" + urllib.parse.quote(k) + "&pageSize=200"
            data, err = _get(u, {})
        else:  # openai / responses
            u = fbase + ("" if fbase.endswith("/models") else "/models")
            data, err = _get(u, {"Authorization": "Bearer " + k})
        if not data:
            continue
        ids: List[str] = []
        for it in (data.get("models") or data.get("data") or []):
            _id = str((it.get("id") if isinstance(it, dict) else it)
                      or "").strip()
            if _id:
                ids.append(_id)
        if ids:
            return sorted(set(ids)), ""
        continue
    if not tried:
        return [], "کلیدی وارد نشده"
    return [], "دریافت فهرست ناموفق بود (کلید/لینک را با «تست کلیدها» چک کنید)"

def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""

def _prompt_custom_endpoint(base: str = "", model: str = "") -> Tuple[str, str]:

    print("── تنظیم سرویس دلخواه (۴ فرمت: OpenAI / Responses / Anthropic / Google) ──")
    print("    لینک کامل endpoint را هم می‌شود چسباند — فرمت خودکار شناخته می‌شود:")
    print("    …/chat/completions | …/responses | …/messages | …:generateContent")
    for _attempt in range(3):
        if not base:
            raw = _ask("دامنهٔ API (مثال: https://api.example.com/v1) "
                       "[خالی = انصراف]: ")
            if not raw:
                break
            base = normalize_api_base(raw)
            if base:
                print(f"  ✔ دامنه: {base}")
            else:
                print("  ✗ این آدرس معتبر نیست — مثل https://api.example.com/v1 بنویس "
                      "(https:// اگر جا افتاده باشد خودکار اضافه می‌شود).")
                continue
        if model:
            break
        model = _ask("نام مدل (مثال: gpt-4o-mini) [خالی = انصراف]: ")
        if model:
            break
        print("  ✗ مدل نمی‌تواند خالی باشد — مثال: gpt-4o-mini")
    return base, model

class GeminiQuotaExhausted(Exception):
    pass

@dataclass
class TextRegion:
    id: int
    boxes: List[np.ndarray]
    source_text: str = ""
    translated_text: str = ""
    rect: Tuple[int, int, int, int] = field(default=(0, 0, 0, 0))
    angle: float = 0.0
    kind: str = "dialogue"
    bubble_style: str = "normal"
    det_class: str = ""

# سبکِ مرجع: هر دیالوگ صفحهٔ خودش را می‌شناسد تا درخواستِ
# ترجمه به شکلِ [{filename, dialogues}] گروه‌بندی شود (حالتِ نوشتاریِ
# «عکسِ فیک» — هیچ عکسی ارسال نمی‌شود، filename فقط شناسهٔ صفحه است)
    page_index: int = -1
    page_file: str = ""

    ocr_polys: List[np.ndarray] = field(default_factory=list)

# وقتی راستی‌آزماییِ جوهر گفت «خطِ واقعی مسطح است»
# رندر حق ندارد زاویه را دوباره از پالی‌ها بازنویسی کند (متنِ
# استایل‌دار/درخشان زاویهٔ کاذب می‌سازد؛ BLUE MOON/PURPLE MOON)
    angle_flat_veto: bool = False

class BalloonToneClassifier:
    TONES = (
        "normal", "shout", "comedy_shout", "whisper",
        "sun_thought", "thought", "free_text", "system",
        "monster", "cry", "fear", "broadcast", "letter",
        "narrator", "square_thought", "black",
    )

    def __init__(self):
        pass

    def classify(self, crop_bgr: np.ndarray) -> str:
        try:
            if crop_bgr is None or crop_bgr.size == 0:
                return "normal"
            h, w = crop_bgr.shape[:2]
            if h < 10 or w < 10:
                return "normal"
            if crop_bgr.shape[2] == 4:
                alpha = crop_bgr[:, :, 3:4].astype(np.float32) / 255.0
                rgb = crop_bgr[:, :, :3].astype(np.float32)
                white = np.ones_like(rgb) * 255.0
                crop_bgr = (rgb * alpha + white * (1 - alpha)).astype(np.uint8)
            gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
            _, bw = cv2.threshold(gray, 0, 255,
                                  cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            n_fg = int((bw > 0).sum())
            n_bg = bw.size - n_fg
            if n_bg < bw.size * 0.02:
                return "free_text"
            inv = 255 - bw
            cnts, _ = cv2.findContours(inv, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
            if not cnts:
                return "normal"
            cnts_sorted = sorted(cnts, key=cv2.contourArea, reverse=True)
            dash_like = [c for c in cnts_sorted
                         if 50 < cv2.contourArea(c) < bw.size * 0.02]
            if len(dash_like) >= 10:
                largest_area = cv2.contourArea(cnts_sorted[0])
                if largest_area < bw.size * 0.08:
                    return "whisper"
            cnt = cnts_sorted[0]
            area = cv2.contourArea(cnt)
            if area < 100:
                return "normal"
            peri = cv2.arcLength(cnt, True)
            if peri < 1:
                return "normal"
            x, y, bw_, bh_ = cv2.boundingRect(cnt)
            rect_area = float(bw_ * bh_)
            rectangularity = area / rect_area if rect_area > 0 else 0
            hull = cv2.convexHull(cnt)
            hull_area = cv2.contourArea(hull)
            solidity = area / hull_area if hull_area > 0 else 1.0
            approx = cv2.approxPolyDP(cnt, 0.01 * peri, True)
            n_vertices = len(approx)
            defects = 0
            try:
                hull_idx = cv2.convexHull(cnt, returnPoints=False)
                if hull_idx is not None and len(hull_idx) > 3:
                    d = cv2.convexityDefects(cnt, hull_idx)
                    if d is not None:
                        for i in range(d.shape[0]):
                            _, _, f, _ = d[i, 0]
                            if f > 1500:
                                defects += 1
            except Exception:
                pass
            mean_val = float(np.mean(gray))
            dark_ratio = float((gray < 80).mean())
            if dark_ratio > 0.55 and mean_val < 100:
                if n_vertices >= 12:
                    return "monster"
                return "black"
            if rectangularity > 0.88 and n_vertices <= 6 and solidity > 0.92:
                if defects >= 3:
                    return "square_thought"
                return "narrator"
            if 6 <= n_vertices <= 10 and solidity > 0.90 and rectangularity < 0.85:
                return "system"
            if n_vertices >= 16:
                if solidity > 0.88:
                    return "comedy_shout"
                return "shout"
            if n_vertices >= 12 and solidity < 0.85:
                return "shout"
            bumpiness = 0
            try:
                if len(cnt) > 20:
                    pts = cnt[:, 0, :].astype(np.float32)
                    n = len(pts)
                    angs = []
                    for i in range(0, n, max(1, n // 60)):
                        p0 = pts[(i - 2) % n]
                        p1 = pts[i]
                        p2 = pts[(i + 2) % n]
                        v1 = p1 - p0
                        v2 = p2 - p1
                        a1 = np.arctan2(v1[1], v1[0])
                        a2 = np.arctan2(v2[1], v2[0])
                        da = abs(a2 - a1)
                        if da > np.pi:
                            da = 2 * np.pi - da
                        angs.append(da)
                    if angs:
                        bumpiness = sum(1 for a in angs if a > 0.5)
            except Exception:
                pass
            if (defects >= 4 and solidity < 0.90) or (bumpiness >= 10 and solidity < 0.97):
                return "thought"
            if defects >= 3 and 0.82 <= solidity < 0.95:
                return "sun_thought"
            circularity = 4 * 3.14159 * area / (peri * peri)
            if circularity > 0.75 and solidity > 0.93:
                return "normal"
            return "normal"
        except Exception:
            return "normal"

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".avif", ".heic", ".heif"}

WATERMARK_PATTERNS = (
    "lunatoons", "lunatoon", "nadeinkorea", "made in korea", "madeinkorea",
    "asurascans", "asura", "flamecomics", "reaper scans", "reaperscans",
    "mangadex", "webtoon", "tapas", "toomics", "lezhin", "tappytoon",
    "kaynscan", "kayn scan", "scar.com", "scarcom", "wanscan", "wan scan",
    "vortexscans", "vortex scans", "vortexscan", "ikemanga", "likemanga",
    "munpia", "nullscans", "luminous", "flame comics", "cosmic scans",
    "asuracomic", "asuracomics", "discord.gg",
    "read this series", "readthis series", "read thisseries", "readthisseries",
    "series at", "seriesat", "support us", "to support", "supportus",
    "join our community", "discord server", "for the latest updates",
    "your support is needed", "community discord", "invite you", "we invite",
    "this chapter was brought", "brought to you by", "show your support",
    "dear readers", "happy reading", "dive deeper", "unlock up to",
    "exclusively on", "storm at", "join the storm",
    "redice studio", "redice", "leafsky", "wasakbasak", "wasak basak",
    "cho wooneh", "hermode", "dotori", "3b2s",
)

DOMAIN_TLDS = (
    "com", "org", "net", "io", "info", "xyz", "app", "dev",
    "site", "online", "web", "biz", "us", "uk", "kr",
    "jp", "cn", "ru", "de", "fr", "es", "pt", "br", "id",
    "gg", "link", "page", "club", "fun", "live", "news", "blog",
    "ink", "toon", "scans",
# فیلترِ تبلیغ «عمومی» شد: هر دامنهٔ سایتی = تبلیغ
# نه فقط لیستِ ثابت (درخواستِ کاربر)
    "me", "tv", "cc", "co", "ai", "mobi", "pro", "top",
    "store", "shop", "website", "space", "host", "press",
    "media", "team", "wiki", "zone", "run", "icu", "cyou",
    "buzz", "vip", "pw", "art", "fans", "moe", "systems",
    "sbs", "cafe", "tools", "tips", "today", "social",
    "community", "network", "digital",
)

DOMAIN_RE = re.compile(
    r"(?i)\b(?:https?://|www\.)?"
    r"[a-z0-9](?:[a-z0-9\-]{1,61}[a-z0-9])"
    r"\.(?:" + "|".join(DOMAIN_TLDS) + r")\b"
)

PROMO_RE = re.compile(
    r"(?i)("
    r"read\s*this\s*series|"
    r"series\s*(first\s*)?at|"
    r"support\s*us|"
    r"to\s*support|"
    r"show\s*your\s*support|"
    r"brought\s*to\s*you|"
    r"this\s*chapter\s*was\s*brought|"
    r"dear\s*readers|"
    r"happy\s*reading|"
    r"dive\s*deeper|"
    r"unlock\s*up\s*to|"
    r"exclusively\s*on|"
    r"vortex\s*scans?|"
    r"ike\s*manga|"
    r"like\s*manga|"
    r"kayn\s*scan|"
    r"scar\.?\s*com|"
    r"wan\s*scan|"
    r"discord\s*(server|\.gg)|"
    r"join\s*(our|ou|the)\s*(community|storm)|"
    r"latest\s*updates|"
    r"support\s*is\s*needed|"
    r"we\s*invite|"
    r"invite\s*(you|yu)|"
    r"community\s*discord|"
    r"for\s*the\s*latest|"
    r"scan\s*\.?\s*com|"
    r"redice\s*studio|"
    r"wasak\s*basak|"
    r"leaf\s*sky|"
    r"3b2s"
    r")"
)

SFX_WORD_RE = re.compile(
    r"(?i)^("
    r"sfx|효과음?|효과|의성어|의태어|"
    r"boom|bang|crash|whoosh|swish|thud|clang|zap|pow|bam|wham|crack|smash|"
    r"roar|growl|hiss|screech|beep|ding|click|tick|tock|splash|drip|"
    r"gasp|sigh|sniff|cough|hic|ugh|argh|kugh|keck|kahack|gorulz|"
    r"thunk|slash|stab|slash|clang|clank|thump|wham|slam|snap|"
    r"ah+|oh+|uh+|hm+|mm+|ha+ha*|he+he*|hi+hi*|wa+h*|ya+h*|"
    r"kuh+|guh+|ngh+|ugh+|arg+|aarg+|"
    r"ドン|ガン|バン|ドカン|ズドン|バキ|メキ|ゴゴゴ|ドドド|ザワ|シーン|"
    r"クスクス|ゲラゲラ|ワハハ|ヒヒヒ|ニヤニヤ|ギラギラ|キラキラ|ピカピカ|"
    r"쿵|쾅|펑|탁|딱|삐|삑|철컥|덜컹|우당탕|쿵쿵|두근|벌벌|흔들|"
    r"轰|砰|啪|咔|哗|呼|哈|嘿|啊|哦|嗯|哼|"
    r"[!?.…]{2,}"
    r")[!?.…]*$"
)

HANGUL_RE = re.compile(r"[\uac00-\ud7a3]+")

def uncensor_swears(text: str) -> str:

    if not text:
        return text

    result = text

    result = re.sub(
        r"\bwhat\s*the\s*f+[*@#$%^&._\-]*\b",
        "what the fuck ",
        result,
        flags=re.IGNORECASE,
    )
    result = re.sub(r"\bwhat\s*theF\b", "what the fuck", result, flags=re.IGNORECASE)
    result = re.sub(r"\btheF\b", "the fuck", result, flags=re.IGNORECASE)
    result = re.sub(r"\bw+t+f+\b", "what the fuck", result, flags=re.IGNORECASE)
    result = re.sub(
        r"\bthe\s*f+(?:uck)?\s*is\b",
        "the fuck is",
        result,
        flags=re.IGNORECASE,
    )

    replacements = [

        (r"\bf+u+[*@#$%^&._\-]*c+k+i+n+g?\b", "fucking"),
        (r"\bf+u+[*@#$%^&._\-]*c+k+\b", "fuck"),
        (r"\bf+[*@#$%^&._\-]+c+k+\b", "fuck"),
        (r"\bf[*@#$%^&._\-]{1,5}ck(?:ing)?\b", "fuck"),

        (r"\bf+[*@#$%^&._\-]*o+k+\b(?=[?!.,…]|$|\s)", "fuck"),
        (r"\bfck\b", "fuck"),
        (r"\bfuk\b", "fuck"),

        (r"\bs+h+[*@#$%^&._\-]*i+t+\b", "shit"),
        (r"\bs+h+[*@#$%^&._\-]+t+\b", "shit"),
        (r"\bsh[*@#$%^&._\-]{1,4}t\b", "shit"),
        (r"\bsht\b", "shit"),

        (r"\bb+i+[*@#$%^&._\-]*t+c+h+\b", "bitch"),
        (r"\bb+[*@#$%^&._\-]+t+c+h+\b", "bitch"),
        (r"\bb[*@#$%^&._\-]{1,4}tch\b", "bitch"),

        (r"\ba+s+s+[*@#$%^&._\-]*h+o+l+e+\b", "asshole"),
        (r"\ba+r+s+e+[*@#$%^&._\-]*h+o+l+e+\b", "arsehole"),
        (r"\ba[*@#$%^&._\-]{1,4}shole\b", "asshole"),

        (r"\bd+a+m+n+\b", "damn"),
        (r"\bd+a+m+m+i+t+\b", "dammit"),
        (r"\bd+i+c+k+\b", "dick"),
        (r"\bd[*@#$%^&._\-]{1,4}ck\b", "dick"),
        (r"\bc+o+c+k+\b", "cock"),
        (r"\bp+u+s+s+y+\b", "pussy"),
        (r"\bc+u+n+t+\b", "cunt"),
        (r"\bc[*@#$%^&._\-]{1,4}nt\b", "cunt"),
        (r"\bm+o+t+h+e+r+f+u+c+k+e+r+\b", "motherfucker"),
        (r"\bm+o+t+h+e+r+[*@#$%^&._\-]*f+u+c+k+e+r+\b", "motherfucker"),
        (r"\bb+a+s+t+a+r+d+\b", "bastard"),
        (r"\bh+e+l+l+\b", "hell"),
        (r"\bg+o+d\s*d+a+m+n?\b", "goddamn"),
        (r"\bd+a+m+n\s*i+t\b", "dammit"),
    ]

    for pattern, repl in replacements:
        result = re.sub(pattern, repl, result, flags=re.IGNORECASE)

    result = re.sub(r"\s{2,}", " ", result)
    result = re.sub(r"\s+([?!.,…])", r"\1", result)
    return result.strip()

_LIVE_SLOT_BY_KEY: Dict[str, int] = {}
_LIVE_SLOT_LOCK = threading.Lock()

#): با
# گیتِ ترتیبِ نمایشِ زنده (
# استخراج/پاکسازیِ دوطرفه صفحه‌ها بی‌ترتیب تمام میشوند (۱،۲،۷،۳،۴،۶،۵)
# و نمایشگرِ زنده صفحهٔ آخر را «قبل» از وسطِ فصل نشان میداد. حالا
# اسلاتِ صریحِ هر صفحه تا وقتی «همهٔ صفحه‌هایِ قبلش» آزاد نشده‌اند در
# بافر می‌ماند و فقط به‌ترتیبِ ۱،۲،۳,… رها می‌شود — پیشرفتِ نمایش فقط
# از بالا به پایین. به‌روزرسانیِ صفحهٔ قبلاً-آزادشده بی‌تأخیر رد میشود.
_LIVE_SEQ_LOCK = threading.Lock()
_LIVE_SEQ_STATE: Dict[str, dict] = {}

def _live_seq_state(d: str) -> dict:
    """وضعیتِ گیتِ ترتیب برای یک پوشهٔ live. اولین دسترسی: اسلات‌هایِ
    موجود روی دیسک (رانِ قبلی/resume) از قبل آزاد حساب میشوند."""
    st = _LIVE_SEQ_STATE.get(d)
    if st is None:
        _next = 1
        try:
            while os.path.isfile(os.path.join(d, f"live_{_next:04d}.jpg")):
                _next += 1
        except Exception:
            pass
        st = {"next": _next, "pending": {}}
        _LIVE_SEQ_STATE[d] = st
    return st

def _live_seq_reset() -> None:
    """شروعِ رانِ جدید: گیت برای پوشه‌هایِ liveِ همین نشست ریست میشود
    (اسلات‌هایِ روی دیسک دوباره اسکن میشوند — resume خودکار درست است)."""
    try:
        with _LIVE_SEQ_LOCK:
            _LIVE_SEQ_STATE.clear()
    except Exception:
        pass

def _live_seq_flush() -> None:
    """پایانِ کار/لغو: هرچه در بافر مانده به‌ترتیبِ شمارهٔ اسلات آزاد
    میشود تا هیچ صفحه‌ای برای همیشه قفل نشود (صفحهٔ خراب/لغوشده).
    بعدِ فلاش، به‌روزرسانی‌هایِ بعدی بی‌تأخیر مینشینند."""
    try:
        with _LIVE_SEQ_LOCK:
            for d, st in list(_LIVE_SEQ_STATE.items()):
                if not st["pending"]:
                    continue
                _mx = st["next"]
                for _slot in sorted(st["pending"].keys()):
                    _pl = st["pending"].pop(_slot)
                    _img = _live_payload_load(_pl)
                    if _img is not None:
                        _write_live_now(_img, d, _slot, _pl.get("key"),
                                        bool(_pl.get("slot_new")),
                                        bool(_pl.get("dbg")))
                    _mx = max(_mx, _slot + 1)
                st["pending"] = {}
                st["next"] = _mx
    except Exception:
        pass

def _live_payload_load(pl: dict):
    """بارگذاریِ تصویرِ نگه‌داشته‌شده در بافرِ گیت (مسیر یا بایت‌هایِ JPG)."""
    try:
        if pl.get("kind") == "path":
            return cv2.imread(pl["data"])
        _buf = pl.get("data")
        if _buf is not None:
            return cv2.imdecode(_buf, cv2.IMREAD_COLOR)
    except Exception:
        pass
    return None

def _write_live_now(img, d: str, slot: int, key, slot_new: bool,
                    dbg: bool) -> None:
    """نوشتنِ یک اسلاتِ live روی دیسک (قبلاً بدنهٔ دومِ _live_dump بود)."""
# دادهٔ روکشِ دیباگ قبل از هر resize برداشته میشود (بعد از
# resize، آرایهٔ تازه ویژگیهایش را از دست میدهد)
    _ovl = getattr(img, "ovl", None)
    _base = getattr(img, "base", None)
    _sent = os.path.join(d, ".count")
    try:
        with open(_sent, encoding="utf-8") as f:
            n = int(f.read().strip() or "0")
    except Exception:
        n = 0
    h, w = img.shape[:2]
    tw = 900
    _sc = 1.0
    if w > tw:
        _sc = float(tw) / float(w)
        img = cv2.resize(img, (tw, max(1, round(h * tw / w))),
                         interpolation=cv2.INTER_AREA)
    out_name = os.path.join(d, f"live_{slot:04d}.jpg")
# اولین نوشتنِ اسلات = «صفحهٔ N آماده شد»: در سبکِ مرجع همهٔ
# dumpها slotِ صریح دارند و slot_new همیشه False میماند → این خط هرگز
# چاپ نمیشد و نوارِ پیشرفتِ وب هیچ «رندرِ نهایی»ای نمیدید (ریشهٔ
# «صفحهٔ 1 از 105 (0٪)» گیرکرده). به‌روزرسانیِ پیش‌نمایشِ همان اسلات
# (فایلِ موجود) بی‌سروصدا میماند.
    _first_write = not os.path.isfile(out_name)
# پچِ فشرده‌سازی v272: پیش‌نمایشِ زندهٔ سبک‌تر — JPEGِ PIL با کیفیتِ
# ۸۰ + optimize + progressive (~۲۳٪ حجمِ کمتر + لودِ تدریجی رویِ نتِ
# ضعیف). اگر PIL در دسترس نبود، همان cv2 با کیفیتِ ۸۰. سقفِ ۹۰۰px و
# عدمِ بزرگ‌کردن همچنان برقرار است؛ _base.jpg و .json دست‌نخورده.
    try:
        from PIL import Image as _PILImage
        _PILImage.fromarray(
            cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        ).save(out_name, format="JPEG", quality=80,
               optimize=True, progressive=True)
    except Exception:
        cv2.imwrite(out_name, img, [cv2.IMWRITE_JPEG_QUALITY, 80])
# دیباگِ روکشدار: پایهٔ بی‌روکش + jsonِ جعبهها با همان مقیاسِ
# live کنارش مینشینند — نمایشگر با کلیدهای جدا جدا میکشدشان
    if dbg and _ovl is not None and _base is not None:
        try:
            import json as _json
            _bimg = _base
            if _bimg.shape[1] != img.shape[1]:
                _bimg = cv2.resize(
                    _base, (img.shape[1],
                            max(1, round(_base.shape[0] * _sc))),
                    interpolation=cv2.INTER_AREA)
            cv2.imwrite(os.path.join(d, f"live_{slot:04d}_base.jpg"),
                        _bimg, [cv2.IMWRITE_JPEG_QUALITY, 86])
            _oj = {
                "size": [int(img.shape[1]), int(img.shape[0])],
                "det": [[round(float(v) * _sc, 1) for v in b[:4]]
                        + [str(b[4] if len(b) > 4 else "")]
                        for b in (_ovl.get("det") or [])],
                "pdet": [[[round(float(x) * _sc, 1),
                           round(float(y) * _sc, 1)] for x, y in q]
                         for q in (_ovl.get("pdet") or [])],
                "rec": [[round(float(v) * _sc, 1) for v in r[:4]]
                        + [str(v) for v in r[4:]]
                        for r in (_ovl.get("rec") or [])],
            }
            with open(os.path.join(d, f"live_{slot:04d}.json"), "w",
                      encoding="utf-8") as f:
                _json.dump(_oj, f, ensure_ascii=False)
        except Exception:
            pass
# شمارندهٔ پوشه نباید عقبتر از اسلاتهایِ تخصیصی بماند (رفتارِ سابق)
    with open(_sent, "w", encoding="utf-8") as f:
        f.write(str(max(n, slot)))
# زمانِ هر اسلات برایِ به‌روزرسانیِ تدریجیِ نمایشگرِ وب
    try:
        with open(os.path.join(d, "mtimes.txt"), "a", encoding="utf-8") as f:
            f.write(f"{slot} {int(time.time() * 1000)}\n")
    except Exception:
        pass
    if not dbg and (key is None or slot_new or _first_write):
        print(f"[*] صفحهٔ {slot} آماده شد", flush=True)
# به‌روزرسانیِ اسلاتِ قبلی (key دار) بی‌سروصدا است — هر ۱۵ دیالوگ یک بار

class _DebugPageVis(np.ndarray):
    """ — تصویرِ دیباگ + دادهٔ روکش: پایه (صفحهٔ بی‌روکش) و
    فهرستِ جعبه‌های هر موتور (detector.onnx / پدل-det / پدل-rec)
    به خودِ آرایه چسبیده میآیند تا در جایِ ذخیره، live_XX_base و
    live_XX.json کنارِ تصویرِ سوخته بنشینند — نمایشگر با کلیدهایِ
    روشن/خاموش، روکشها را جدا جدا میکشد."""
    ovl = None
    base = None


def _live_dump(src, dbg: bool = False, key: Optional[str] = None,
               slot: Optional[int] = None) -> None:
    """یک صفحهٔ تازه‌تمام‌شده را برای «نمایش زنده» می‌نویسد.

    src یا مسیر فایل است یا آرایهٔ تصویر (مثل دیباگ). برای دیباگ پوشهٔ
    جداگانه از MANGA_LIVE_DEBUG_DIR خوانده می‌شود تا نمایش دیباگ هم
    بتواند زنده باشد.

     — key: شناسهٔ صفحه (مسیرِ خروجیِ همان صفحه). بارِ اول اسلات
    جدید میگیرد (مثلِ قبل)؛ دفعاتِ بعدی «همان اسلات» به‌روز میشود — این
    همان «۱۵ تا ۱۵ تا ترجمه کنه بذاره رو عکس نشون بده» است: هر بستهٔ
    ترجمه همان صفحه را دوباره رندر و جای خودش زنده عوض میکند. برای هر
    به‌روزرسانی یک خط «اسلات زمان» در mtimes.txt نوشته میشود تا نمایشگرِ
    وب فقط اسلاتِ عوضشده را دوباره لود کند (بدونِ پرش اسکرول).

     — slot: شمارهٔ اسلاتِ صریح. «دیباگ دو بار نشون میده — هم
    دیباگِ قبلی هست هم دیباگِ تمومشده»: دیباگِ هر صفحه دوبار ذخیره میشد
    (یکبار در _finish_page_now و یکبار در حلقهٔ ذخیرهٔ نهایی) و چون
    شمارهٔ اسلاتِ دیباگ از رجیستریِ جدا میآمد، هر بار «فایلِ تازه»
    میساخت → پوشهٔ live_debug دو فایل برایِ هر صفحه داشت و نمایشگرِ
    دیباگ هر صفحه را دو بار نشان میداد. حالا دیباگِ صفحهٔ iام همیشه در
    live_00(i+1).jpg همان پوشه مینشیند — ریزِ دوباره همان فایل را
    بهروز میکند، هیچ فایلِ تکراری ساخته نمیشود و ترتیبِ فهرستِ دیباگ =
    ترتیبِ واقعیِ صفحه‌ها."""
    d = (os.environ.get("MANGA_LIVE_DEBUG_DIR" if dbg else "MANGA_LIVE_DIR")
         or "").strip()
    if not d:
        return
    try:
        if isinstance(src, str):
            img = cv2.imread(src)
        elif isinstance(src, np.ndarray):
            img = src
        else:
            img = None
        if img is None:
            return
        os.makedirs(d, exist_ok=True)
        slot_new = False
        if slot is None and key is not None:
            with _LIVE_SLOT_LOCK:
                slot = _LIVE_SLOT_BY_KEY.get(key)
                if slot is None:
                    try:
                        with open(os.path.join(d, ".count"), encoding="utf-8") as f:
                            _n = int(f.read().strip() or "0")
                    except Exception:
                        _n = 0
                    slot = _n + 1
                    _LIVE_SLOT_BY_KEY[key] = slot
                    slot_new = True
        if slot is None:
            try:
                with open(os.path.join(d, ".count"), encoding="utf-8") as f:
                    n = int(f.read().strip() or "0")
            except Exception:
                n = 0
            n += 1
            slot = n
            slot_new = True
# گیتِ ترتیبِ «فقط از بالا به پایین»: اسلاتِ صریح تا
# نوبتش در بافر میماند؛ اسلاتِ قبلاً-آزادشده بی‌تأخیر به‌روز میشود.
        st = _live_seq_state(d)
        with _LIVE_SEQ_LOCK:
            if int(slot) < int(st["next"]):
                _write_live_now(img, d, int(slot), key, slot_new, dbg)
            else:
                _slot = int(slot)
                if isinstance(src, str):
                    _pl = {"kind": "path", "data": src, "key": key,
                           "slot_new": slot_new, "dbg": dbg}
                else:
                    try:
                        _ok, _buf = cv2.imencode(
                            ".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 86])
                        _pl = ({"kind": "bytes", "data": _buf, "key": key,
                                "slot_new": slot_new, "dbg": dbg}
                               if _ok else None)
                    except Exception:
                        _pl = None
                if _pl is not None:
# نسخهٔ تازه‌ترِ همان اسلات، نسخهٔ نگه‌داشته را عوض میکند
                    st["pending"][_slot] = _pl
# زنجیرهٔ آماده‌ها را تا پایین آزاد کن
                while st["next"] in st["pending"]:
                    _pl2 = st["pending"].pop(st["next"])
                    _img2 = _live_payload_load(_pl2)
                    if _img2 is not None:
                        _write_live_now(_img2, d, st["next"],
                                        _pl2.get("key"),
                                        bool(_pl2.get("slot_new")),
                                        bool(_pl2.get("dbg")))
                    st["next"] += 1
    except Exception:
        pass

def _live_page_dump(out_file: str, key: Optional[str] = None,
                    slot: Optional[int] = None) -> None:
    """ — slot: شمارهٔ صریحِ اسلات = شمارهٔ واقعیِ صفحه.

    با استخراجِ دوطرفهٔ ۱۹۷ صفحهها بیترتیبِ شماره تمام میشوند و
    پیشنمایشِ جریانی هم به ترتیبِ رسیدنِ آیتمها از مدل رندر میکند؛
    اسلاتِ «ترتیبِ اتمام» عکسِ وسطِ فصل را جلوی صفحهٔ اول مینشاند
    (). حالا همهٔ مسیرها
    slot=page_i+1 میفرستند — ترتیبِ نمایشِ زنده = ترتیبِ واقعیِ صفحهها؛
    هر صفحه در جایگاهِ خودش پر میشود، وسط فصل وسط میماند."""
    _live_dump(out_file, dbg=False, key=key, slot=slot)

# _one_request_caps/_split_one_request_batches حذف شدند:
# دیکدِ APKِ مرجع نشان داد که هیچ بستهبندی/سقفی وجود ندارد — کلِ فصل در
# «یک» درخواست می‌رود .

def _live_total_write(n: int) -> None:
    """تعداد کل صفحه‌ها را در پوشهٔ live می‌نویسد تا نمایشگر زنده از اول
    برای همه اسلات «در حال ترجمه» بگذارد — اسلات‌ها سر جایشان پر می‌شوند
    و اسکرولِ کاربر هیچ‌وقت نمی‌پرد (). — شروعِ هر ران
    گیتِ ترتیبِ نمایش هم ریست میشود (اسلات‌هایِ رانِ قبلی از دیسک
    خوانده میشوند — resume درست کار میکند)."""
    _live_seq_reset()
    for var in ("MANGA_LIVE_DIR", "MANGA_LIVE_DEBUG_DIR"):
        d = (os.environ.get(var) or "").strip()
        if not d:
            continue
        try:
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "total.txt"), "w", encoding="utf-8") as f:
                f.write(str(int(n)))
        except Exception:
            pass
