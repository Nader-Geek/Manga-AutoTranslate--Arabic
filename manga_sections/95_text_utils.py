# BUILD-STRIP-START
# ─────────────────────────────────────────────────────────────
# 📦 متن و ابزارها — TextRegion، BalloonToneClassifier، uncensor_swears، خروجیِ زندهٔ صفحات
# (متنِ بالا فقط راهنمای همین فایل است؛ در بیلدِ manga.py حذف میشود)
# BUILD-STRIP-END
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


