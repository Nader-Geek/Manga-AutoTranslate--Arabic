# BUILD-STRIP-START
# ─────────────────────────────────────────────────────────────
# 📦 سرویسهای AI و ابزارهای متن — پریستها، کلیدها، TextRegion، لحن
# PROVIDER_PRESETS، آزمایشِ کلیدها، source_has_letters، TextRegion (dataclass)، BalloonToneClassifier و وضعیتِ live.
# (این سربرگ فقط راهنمای همین فایل است؛ لودرِ manga.py و بیلد حذفش میکنند)
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

    # v1.14.242 — سبکِ مرجع: هر دیالوگ صفحهٔ خودش را می‌شناسد تا درخواستِ
    # ترجمه به شکلِ [{filename, dialogues}] گروه‌بندی شود (حالتِ نوشتاریِ
    # «عکسِ فیک» — هیچ عکسی ارسال نمی‌شود، filename فقط شناسهٔ صفحه است)
    page_index: int = -1
    page_file: str = ""

    ocr_polys: List[np.ndarray] = field(default_factory=list)

    # v1.14.80 — وقتی راستی‌آزماییِ جوهر گفت «خطِ واقعی مسطح است»،
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
    # v1.14.66 — فیلترِ تبلیغ «عمومی» شد: هر دامنهٔ سایتی = تبلیغ،
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

# v1.14.215 — گیتِ ترتیبِ نمایشِ زنده (دستورِ سازنده: «نمایش زنده از
# پایین به بالا هم لود میکنه باید از بالا به پایین فقط بره»): با
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
    _sent = os.path.join(d, ".count")
    try:
        with open(_sent, encoding="utf-8") as f:
            n = int(f.read().strip() or "0")
    except Exception:
        n = 0
    h, w = img.shape[:2]
    tw = 900
    if w > tw:
        img = cv2.resize(img, (tw, max(1, round(h * tw / w))),
                         interpolation=cv2.INTER_AREA)
    out_name = os.path.join(d, f"live_{slot:04d}.jpg")
    # v1.14.239 — اولین نوشتنِ اسلات = «صفحهٔ N آماده شد»: در سبکِ مرجع همهٔ
    # dumpها slotِ صریح دارند و slot_new همیشه False میماند → این خط هرگز
    # چاپ نمیشد و نوارِ پیشرفتِ وب هیچ «رندرِ نهایی»ای نمیدید (ریشهٔ
    # «صفحهٔ 1 از 105 (0٪)» گیرکرده). به‌روزرسانیِ پیش‌نمایشِ همان اسلات
    # (فایلِ موجود) بی‌سروصدا میماند.
    _first_write239 = not os.path.isfile(out_name)
    cv2.imwrite(out_name, img, [cv2.IMWRITE_JPEG_QUALITY, 86])
    # شمارندهٔ پوشه نباید عقبتر از اسلاتهایِ تخصیصی بماند (رفتارِ سابق)
    with open(_sent, "w", encoding="utf-8") as f:
        f.write(str(max(n, slot)))
    # v1.14.160 — زمانِ هر اسلات برایِ به‌روزرسانیِ تدریجیِ نمایشگرِ وب
    try:
        with open(os.path.join(d, "mtimes.txt"), "a", encoding="utf-8") as f:
            f.write(f"{slot} {int(time.time() * 1000)}\n")
    except Exception:
        pass
    if not dbg and (key is None or slot_new or _first_write239):
        print(f"[*] صفحهٔ {slot} آماده شد", flush=True)
    # به‌روزرسانیِ اسلاتِ قبلی (key دار) بی‌سروصدا است — هر ۱۵ دیالوگ یک بار


def _live_dump(src, dbg: bool = False, key: Optional[str] = None,
               slot: Optional[int] = None) -> None:
    """یک صفحهٔ تازه‌تمام‌شده را برای «نمایش زنده» می‌نویسد.

    src یا مسیر فایل است یا آرایهٔ تصویر (مثل دیباگ). برای دیباگ پوشهٔ
    جداگانه از MANGA_LIVE_DEBUG_DIR خوانده می‌شود تا نمایش دیباگ هم
    بتواند زنده باشد.

    v1.14.160 — key: شناسهٔ صفحه (مسیرِ خروجیِ همان صفحه). بارِ اول اسلات
    جدید میگیرد (مثلِ قبل)؛ دفعاتِ بعدی «همان اسلات» به‌روز میشود — این
    همان «۱۵ تا ۱۵ تا ترجمه کنه بذاره رو عکس نشون بده» است: هر بستهٔ
    ترجمه همان صفحه را دوباره رندر و جای خودش زنده عوض میکند. برای هر
    به‌روزرسانی یک خط «اسلات زمان» در mtimes.txt نوشته میشود تا نمایشگرِ
    وب فقط اسلاتِ عوضشده را دوباره لود کند (بدونِ پرش اسکرول).

    v1.14.195 — slot: شمارهٔ اسلاتِ صریح. «دیباگ دو بار نشون میده — هم
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
        # v1.14.215 — گیتِ ترتیبِ «فقط از بالا به پایین»: اسلاتِ صریح تا
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
    """v1.14.198 — slot: شمارهٔ صریحِ اسلات = شمارهٔ واقعیِ صفحه.

    با استخراجِ دوطرفهٔ ۱۹۷ صفحهها بیترتیبِ شماره تمام میشوند و
    پیشنمایشِ جریانی هم به ترتیبِ رسیدنِ آیتمها از مدل رندر میکند؛
    اسلاتِ «ترتیبِ اتمام» عکسِ وسطِ فصل را جلوی صفحهٔ اول مینشاند
    (گزارشِ سازنده: «یهو عکس وسط شده اولی عکس»). حالا همهٔ مسیرها
    slot=page_i+1 میفرستند — ترتیبِ نمایشِ زنده = ترتیبِ واقعیِ صفحهها؛
    هر صفحه در جایگاهِ خودش پر میشود، وسط فصل وسط میماند."""
    _live_dump(out_file, dbg=False, key=key, slot=slot)


# v1.14.242 — _one_request_caps/_split_one_request_batches حذف شدند:
# دیکدِ APKِ مرجع نشان داد که هیچ بستهبندی/سقفی وجود ندارد — کلِ فصل در
# «یک» درخواست می‌رود (دستورِ سازنده: «کامل سبکش مثل همون باشه»).


def _live_total_write(n: int) -> None:
    """تعداد کل صفحه‌ها را در پوشهٔ live می‌نویسد تا نمایشگر زنده از اول
    برای همه اسلات «در حال ترجمه» بگذارد — اسلات‌ها سر جایشان پر می‌شوند
    و اسکرولِ کاربر هیچ‌وقت نمی‌پرد (v1.14.29). v1.14.215 — شروعِ هر ران
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


