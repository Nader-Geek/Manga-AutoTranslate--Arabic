# BUILD-STRIP-START
# ─────────────────────────────────────────────────────────────
# 📦 ارائهدهندههای AI — PROVIDER_PRESETS، تستِ کلید، فهرستِ مدلها (Gemini/custom)
# (متنِ بالا فقط راهنمای همین فایل است؛ در بیلدِ manga.py حذف میشود)
# BUILD-STRIP-END
PROVIDER_PRESETS = {
    "gemini": {
        "type": "gemini",
        "default_model": "gemini-3.5-flash-lite",  # v1.14.147 — پیشفرضِ جدید (Flash-Lite)
        "env_key": "GEMINI_API_KEY",
    },
    "gemini-openai": {
        "type": "openai",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        # v1.14.230 — gemini-3.5-flash (بدونِ Lite) دیگر در فهرستِ مدلهایِ
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
        # v1.14.230 — google/gemini-2.0-flash-001 سمتِ گوگل خاموش شده؛
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


# ── فرمت‌های API که «کلید کاستوم» می‌فهمد ──────────────────────────────
# 1) OpenAI Chat Completions   …/chat/completions
# 2) OpenAI Responses API      …/responses
# 3) Anthropic Compatible      …/messages
# 4) Google Generative AI      …:generateContent
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
      https://opencode.ai/inference/openai/v1/responses        → openai-responses
      https://opencode.ai/inference/anthropic/v1/messages      → anthropic
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
    هر کلید با ✔ / ⚠️ / ✘ مشخص می‌شود؛ بعد از ۶۰ ثانیه در رابط پاک می‌شود."""
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
    """v1.14.229 — دستورِ سازنده: «اگ متنی عدد یا شکل بود یا بهتر بگم
    فقط بجز حروف بود ترجمه نکنه… اگ فقط همین جیزا تو یک متن بود کلا
    نره ترجمه اگ کنارش متن یا حروف واقعی بود بره مثل hi… باید ترجمه شه
    ولی اگ میشد …. نره ترجمه الکی وقت ai میگیره». متنی که «هیچ" 
    حرفی» (دستهٔ یونیکدِ L) ندارد — '123124'، './….'، '[] ,./???!?~' —
    به مترجم نمی‌رود و فقط پاکسازی میشود؛ «hi…» حرف دارد → ترجمه
    میشود. PC/لینوکس/اندروید یکسان."""
    _t229 = str(text or "")
    _letters229 = [_ch for _ch in _t229 if _ch.isalpha()]
    if not _letters229:
        return False
    # «10,000G» (طلا/ارزِ بازی): یک حرفِ لاتینِ تنها چسبیده به رقم =
    # پسوندِ واحد، نه کلمه — ترجمه‌اش دور ریختنِ وقتِ AI است. «hi…»،
    # «A» (بدون رقم) و هر متنِ چندحرفیِ واقعی ترجمه میشوند.
    if len(_letters229) == 1 and _letters229[0].isascii() \
            and any(_c.isdigit() for _c in _t229):
        return False
    return True


# v1.14.232 — لیستِ آفلاینِ مدلهایِ Gemini (دستورِ سازنده: «مدل هارو
# افلاین هم بزار یک بار خودت لیست هارو بگیر بزار کد اگ اپدیتی چیزی شد
# خودشون رفرش میزنن بعد فقط مدلای flash و flash-lite و flash-preview
# این لیست هارو باید بگیره بقیش نباید بگیره»). یک‌بار از فهرستِ رسمیِ
# Gemini API (نوامبر ۲۰۲۶ — aistudio.google.com/docs/models) گرفته شد؛
# فقط مدلهایِ متنِ خانوادهٔ flash (شاملِ flash-lite و flash-preview) —
# بدونِ pro/argon و بدونِ نسل‌هایِ مردهٔ ۱/۲ (۲.۵ها یا محدود به
# کاربرانِ قدیمیاند یا مسیرِ ۳.۵ میشوند). ترتیب = همان _model_sort_key
# (Lite اول، بعدِ آن Flash کامل، بعدِ preview/aliasها). اگر گوگل مدلِ
# تازه‌ای بیاورد، کاربر با دکمهٔ ↻ فهرستِ زنده را میگیرد.
GEMINI_FLASH_MODELS_OFFLINE = [
    "gemini-3.5-flash-lite",     # پایدارِ سبک — پیش‌فرضِ برنامه
    "gemini-3.1-flash-lite",     # پایدارِ سبک
    "gemini-flash-lite-latest",  # alias زنده
    "gemini-3.8-flash",          # جدیدترین Flash کامل
    "gemini-3.6-flash",          # پایدارِ کامل
    "gemini-3-flash-preview",    # preview
    "gemini-flash-latest",       # alias زنده
]


def gemini_offline_models() -> List[str]:
    """v1.14.232 — رونوشتِ مرتبِ لیستِ آفلاین (برایِ دراپ‌داونِ وب و
    فال‌بکِ دکمهٔ ↻ اندروید/وب وقتی اتصال برقرار نشد)."""
    return list(GEMINI_FLASH_MODELS_OFFLINE)


def list_provider_models(provider: str, keys_text: str, api_base: str = "",
                         timeout: float = 20.0) -> Tuple[List[str], str]:
    """v1.14.229 — فهرستِ مدلهایِ موجود از خودِ سرویس (دستورِ سازنده:
    «مدلای موجود تو gemini نشون بده طرف انتخاب کنه بجز تو کاستوم باید
    طرف خودش بنویسه»). Gemini: GET v1beta/models (فقط مدلهایِ ترجمهپذیر؛
    v1.14.232: فقط flash/flash-lite/flash-preview — صافیِ _is_bad_list_model).
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


