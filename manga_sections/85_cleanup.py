# BUILD-STRIP-START
# MangaTranslator (۵ از ۷) — پاکسازی (یکجا): ماسک، LaMa، پرکردن، صفحه، بازرسی
# این فایل «قطعهای از بدنهٔ کلاس MangaTranslator» است و بهتنهایی
# اجرا نمیشود — لودرِ manga.py این محتوا را بههمان ترتیبِ شمارهٔ
# فایل، داخلِ کلاس میچسباند. کلاسِ پوششیِ زیر فقط برایِ معتبر
# بودنِ سینتکسِ این فایلِ تکی است و موقعِ بارگذاری حذف میشود.
# (ترکیب از: 110_translator_masks.py + 120_translator_lama_groups.py + 130_translator_fill_compose.py + 140_translator_clean_page.py + 150_translator_clean_verify.py)
class _MangaTranslatorBody_85:
# BUILD-STRIP-END
    def _is_non_english_script(self, text: str) -> bool:

        if not text:
            return True
        allow_en, allow_ko, allow_ja, allow_zh = self._ocr_lang_flags()

        has_latin = False
        has_hangul = False
        has_kana = False
        has_han = False
        for ch in text:
            o = ord(ch)
            if ch.isascii() and ch.isalpha():
                has_latin = True
            elif 0xAC00 <= o <= 0xD7A3:
                has_hangul = True
            elif 0x3040 <= o <= 0x30FF or 0xFF66 <= o <= 0xFF9D:
                has_kana = True
            elif (0x3400 <= o <= 0x9FFF) or (0xF900 <= o <= 0xFAFF) or (0x3000 <= o <= 0x303F):
                has_han = True

        if has_hangul and not allow_ko:
            return True
        if has_kana and not allow_ja:
            return True

        if has_han and not (allow_ja or allow_zh):
            return True

        allowed_any = (
            (has_latin and allow_en)
            or (has_hangul and allow_ko)
            or (has_kana and allow_ja)
            or (has_han and (allow_ja or allow_zh))
        )
        if not allowed_any and (has_latin or has_hangul or has_kana or has_han):
            if has_latin and not (has_hangul or has_kana or has_han):
                try:
                    latin = re.sub(r"[^A-Za-z]", "", str(text))
                    if len(latin) >= 3 and any(c in "AEIOUaeiou" for c in latin):
                        return False
                except Exception:
                    pass
            return True
        return False

    @staticmethod
    def _strip_watermark_tokens(text: str) -> str:

        t = text or ""
        t = DOMAIN_RE.sub(" ", t)
        for w in WATERMARK_PATTERNS:
            if w and re.search(r"(?i)(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", t):
                t = re.sub(r"(?i)(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", " ", t)
        return re.sub(r"\s{2,}", " ", t).strip(" \t.,:;!?…")

    @staticmethod
    def _dialogue_despite_watermark(text: str) -> bool:

# واترمارکِ رویِ حباب: اگرِ بعدِ برداشتنِ دامنهها
# باقیِ متن هنوز دیالوگِ واقعی باشد (≥۳ واژهٔ حرفدارِ مصوتدار و
# بدونِ نشانهٔ تبلیغِ باقی‌مانده) → promo نیست. فقطِ دامنه برداشته
# میشود تا عبارتِ تبلیغِ باقی‌مانده («DEAR READERS»، …) هنوز دیده
# شود و بنرِ واقعی promo بماند.
        residue = DOMAIN_RE.sub(" ", text or "")
        if not residue.strip() or MangaTranslator._is_watermark_text(residue):
            return False
        words = [w for w in re.findall(r"[A-Za-z]{2,}", residue)
                 if any(c in "AEIOUaeiou" for c in w)]
        return len(words) >= 3

    @staticmethod
    def _classify_text(text: str) -> str:

        stripped = (text or "").strip()
        if not stripped:
            return "junk"

        latin_core = re.sub(r"[^A-Za-z]", "", stripped)
        _looks_promo = bool(DOMAIN_RE.search(stripped) or PROMO_RE.search(stripped))
# نامِ پلتفرم/واترمارک در متنِ کوتاه = کاندیدِ تبلیغ
# وگرنه شاخهٔ «شبیهِ جمله → دیالوگ» قبل از چکِ واترمارک برمی‌گشت
# و بنرهایِ «READ ON WEBTOON» / «NAVER WEBTOON» دیالوگ حساب میشدند.
        if not _looks_promo and len(stripped) <= 40:
            _low_probe = stripped.lower()
            for _w in WATERMARK_PATTERNS:
                if _w and _w in _low_probe:
                    _looks_promo = True
                    break
# واترمارکِ رویِ حباب: OCR واترمارک/دامنهٔ سایت را «داخلِ»
# متنِ حباب میخواند («IT'S EASY, LIKEMANGA.INK BECAUSE…» /
# «…DREAMS...LIKEMANGA.INK» — فصلِ ۱۱۰) و کلِ ناحیه promo میشد →
# ازش رد میشد (نه پاکسازی، نه ترجمه). اگرِ بعدِ برداشتنِ توکنها
# باقیِ متن هنوز دیالوگِ واقعی است → دیالوگ، نه promo.
        if _looks_promo and MangaTranslator._dialogue_despite_watermark(stripped):
            return "dialogue"
        if len(latin_core) >= 3 and not _looks_promo and re.fullmatch(r"[A-Za-z][A-Za-z\s.'\-]*[.!?…~]*", stripped.replace("...", ".").replace("…", ".")):

            if any(c in "AEIOUaeiou" for c in latin_core):
                return "dialogue"
        if len(latin_core) >= 2 and not _looks_promo and stripped.endswith(("?", "!", "?!", "!?", "...?", "...!")):
            if any(c in "AEIOUaeiou" for c in latin_core):
                return "dialogue"

        low_full = stripped.lower()
        low_compact = re.sub(r"[\s.\-_]", "", low_full)
        alpha_only = re.sub(r"[^\w]", "", stripped, flags=re.UNICODE)
        words = re.findall(r"[A-Za-z\uac00-\ud7a3]+", stripped)
        has_cjk = any(
            0x2E80 <= ord(c) <= 0x9FFF or 0xF900 <= ord(c) <= 0xFAFF
            or 0x3040 <= ord(c) <= 0x30FF or 0xAC00 <= ord(c) <= 0xD7A3
            for c in stripped
        )

        dialogue_short = {
            "i", "im", "i'm", "me", "my", "you", "u", "he", "she", "we", "they",
            "no", "yes", "ok", "okay", "oh", "ah", "eh", "uh", "hm", "hmm",
            "hi", "hey", "yo", "bye", "wow", "yay", "ouch", "ow", "ugh",
            "stop", "go", "run", "help", "wait", "hold", "look", "come",
            "move", "fire", "ready", "now", "true", "lie", "die", "what",
            "why", "how", "who", "where", "when", "huh", "eh?", "ah!",
            "no!", "yes!", "ok!", "oh!", "ah!", "hey!", "wow!", "stop!",
            "go!", "run!", "help!", "wait!", "what?", "why?", "how?",
            "who?", "huh?", "no?", "yes?", "really", "sure", "fine",
            "damn", "shit", "fuck", "hell", "god", "please", "sorry",
            "thanks", "thank", "bye", "later", "never", "always", "maybe",
            "huh", "nah", "yep", "yup", "nope", "yea", "yeah", "yup",
            "one", "two", "all", "any", "out", "off", "up", "down", "in",
            "on", "at", "to", "of", "for", "and", "but", "or", "so",
            "the", "a", "an", "this", "that", "it", "its", "his", "her",
            "our", "your", "their", "us", "them", "him", "do",
            "did", "does", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "will", "would", "can", "could",
            "should", "must", "may", "might", "let", "get", "got",
            "see", "saw", "know", "knew", "think", "say", "said",
            "tell", "told", "ask", "asked", "came", "went",
            "id", "sir", "boss", "man", "boy", "girl", "kid", "guys",
            "hey!", "what!", "huh!", "no!!", "yes!!", "stop!!", "wait!!",
            "die!", "die!!", "run!", "run!!", "help!", "help!!",

            "much", "rich", "gold", "hard", "find", "gone", "took", "last",
            "tiny", "piece", "way", "need", "want", "money", "carry", "dream",
            "found", "single", "league", "hand", "look", "part",
            "tokyo", "hokkaido", "meiji", "nuggets", "flakes", "prospectors",
        }

        core = re.sub(r"[!?.…~\-]+$", "", low_full).strip()

        _lonely_func = {
            "of", "to", "in", "on", "at", "a", "an", "the", "is", "it", "as",
            "or", "so", "be", "do", "if", "by",
        }
        if len(stripped) <= 3 and core in _lonely_func and not any(c in stripped for c in "!?…"):
            return "junk"

        if core in dialogue_short or low_full in dialogue_short:
            return "dialogue"
        if alpha_only.lower() in dialogue_short:
            return "dialogue"

        if stripped.upper() == "I":
            return "dialogue"

        digits_only = re.sub(r"[^\d]", "", stripped)

        is_progress = bool(re.fullmatch(
            r"[\(\[\{]?\s*\d+\s*/\s*\d+\s*[\)\]\}]?",
            stripped,
        ))
        if is_progress:
            return "dialogue"

        if (
            re.search(r"\d+\s*화", stripped)
            or re.search(r"(?i)\b(?:ch(?:apter)?|ep(?:isode)?)\s*\.?\s*\d+", stripped)
            or re.search(r"(?i)^\d+\s*(?:화|wolat|etdt|chapter|episode)\b", stripped)
            or re.search(r"(?i)\b\d{1,3}\s*화\b", stripped)
            or (re.search(r"(?i)wolat|etdt", stripped) and re.search(r"\d", stripped))
        ):
            return "promo"

# «عدد در کنارِ حروفِ واقعی = دیالوگ است، نه آشغال»
# : قوانینِ
# عددیِ junk فقط وقتی صدا میزنند که متن «هیچ حرفِ واقعی» نداشته
# باشد (source_has_letters) — آن‌وقت سیاست در سطحِ ناحیه
# (no_touch) دست میگیرد و ناحیه دست‌نخورده میماند. «1233»
# همچنان junk میماند (بدونِ حرف) ولی «19 hi» / «19th» دیالوگ.
        _has_letters = source_has_letters(stripped)
        if not _has_letters:
            if stripped.isdigit() or re.fullmatch(r"[\d\s.%oO]+", stripped):
                return "junk"
            if re.fullmatch(r"[QOIl]?\d{2,}", stripped, re.I):
                return "junk"
            if re.fullmatch(r"[A-Za-z]{0,2}\d{3,}", stripped) and len(digits_only) >= 3:
                return "junk"

            if re.fullmatch(r"[A-Za-z]?\d{2,6}", stripped) and len(stripped) <= 7:
                return "sfx"
            if digits_only and len(stripped) <= 12:
                non_digit_alpha = re.sub(r"[\d\s.%oOQIl]", "", stripped, flags=re.I)
                non_digit_alpha = re.sub(r"[/()\[\]{}]", "", non_digit_alpha)
                if len(non_digit_alpha) <= 2:
                    return "junk"
            if not has_cjk and len(alpha_only) <= 1 and len(stripped) <= 3 and stripped.upper() != "I":
                return "junk"
            if not has_cjk and len(alpha_only) <= 2 and len(stripped) <= 5 and not any(
                c.isalpha() and c.isascii() for c in stripped if len(stripped) > 3
            ):
                return "junk"

        if getattr(MangaTranslator, "_title_skip_enabled", False):
            title_pats = getattr(MangaTranslator, "_title_skip_patterns", None) or []
            for pat in title_pats:
                if not pat or len(pat) < 6:
                    continue
                if pat not in low_compact:
                    continue
                remainder = low_compact.replace(pat, "")
                if len(remainder) <= 6 and len(low_compact) <= 40:
                    return "promo"

        if MangaTranslator._is_watermark_text(stripped):
            return "promo"
        if PROMO_RE.search(stripped):
            return "promo"
        if DOMAIN_RE.search(stripped):
            return "promo"
        if low_compact in {
            "org", "com", "net", "www", "http", "https", "wwwcom", "wwworg",
            "comto", "ink", "scans", "scan", "asura", "asuras", "asuran",
        }:
            return "promo"
        if re.fullmatch(r"(?i)[a-z0-9\-]+\.(?:" + "|".join(DOMAIN_TLDS) + r")[a-z]{0,3}", stripped):
            return "promo"
        if re.search(r"(?i)\.(?:com|org|net|io|ink)\b", stripped):
            return "promo"
# پسوند/پیشوندِ سایتِ «الزامی» شد؛ قبلاً هر متنی که
# فقط «manga» داشت (تا ۲۴ کاراکتر) promo میشد.
        if re.search(r"(?i)((like|ike|vortex|kayn|asura|reaper)manga|manga[.\s]?(ink|unk|com|org))", stripped) and len(stripped) <= 24:
            return "promo"
# نشانهٔ دامنه لازم شد؛ قبلاً دیالوگِ کوتاهِ «DRUNK»/
# «BLINK»/«THINK» (پایانش unk/ink) promo میشد و رد میشد.
        if low_compact.endswith(("com", "org", "net", "ink", "unk")) and (
            "." in stripped or "scan" in low_compact or "manga" in low_compact or "series" in low_full
        ):
            return "promo"

        if len(words) >= 2 or len(stripped) > 10:
            return "dialogue"

        hangul_chars = HANGUL_RE.findall(stripped)
        hangul_len = sum(len(h) for h in hangul_chars)
        if hangul_len >= 1 and hangul_len == len(alpha_only) and len(stripped) <= 8:
            compact_h = re.sub(r"[^\uac00-\ud7a3]", "", stripped)
            unit = compact_h[:2] if len(compact_h) >= 4 else compact_h[:1]
            if unit and re.fullmatch("(" + re.escape(unit) + ")+", compact_h):
                return "sfx"
            return "dialogue"

        if len(stripped) <= 12 and SFX_WORD_RE.match(stripped):
            if core not in dialogue_short and alpha_only.lower() not in dialogue_short:
                return "sfx"

        if (
            3 <= len(stripped) <= 12
            and stripped.isupper()
            and " " not in stripped
            and stripped.isalpha()
        ):
            upper_dialogue = {w.upper() for w in dialogue_short if w.isalpha()}
            if stripped in upper_dialogue:
                return "dialogue"

            _common_upper = {
                "CONTROL", "EVERYTHING", "ORDERS", "ORDER", "SOMETHING",
                "ANYTHING", "NOTHING", "SOMEONE", "ANYONE", "EVERYONE",
                "ANYWHERE", "EVERYWHERE", "SOMEWHERE", "WHATEVER",
                "HOWEVER", "BECAUSE", "WITHOUT", "THROUGH", "BETWEEN",
                "ANOTHER", "ALREADY", "ALWAYS", "NEVER", "REALLY",
                "PROBABLY", "CERTAINLY", "ABSOLUTELY", "COMPLETELY",
                "PERFECTLY", "EXACTLY", "ACTUALLY", "SERIOUSLY",
                "OBVIOUSLY", "FINALLY", "SUDDENLY", "QUICKLY",
                "BEFORE", "AFTER", "UNDER", "OVER", "AGAINST",
                "TOWARD", "TOWARDS", "INSIDE", "OUTSIDE", "AROUND",
                "DURING", "WITHIN", "BEHIND", "BEYOND", "ACROSS",
                "PEOPLE", "PERSON", "FRIEND", "ENEMY", "POWER",
                "POWERS", "WORLD", "PLACE", "THING", "THINGS",
                "RIGHT", "WRONG", "GREAT", "SMALL", "LARGE",
                "FIRST", "LAST", "NEXT", "OTHER", "SAME",
                "STILL", "EVEN", "JUST", "ONLY", "ALSO",
                "ABOUT", "AGAIN", "BEING", "DOING", "GOING",
                "COMING", "LOOKING", "THINKING", "KNOWING",
                "WANTING", "NEEDED", "CALLED", "TURNED", "MADE",
                "SURE", "WHEN", "WHERE", "WHICH", "WHILE",
                "THESE", "THOSE", "THERE", "THEIR", "THEM",
                "YOUR", "YOURS", "MINE", "OURS", "THEIRS",
                "REPORT", "RESISTANCE", "INFORMATION", "AUDIENCE",
                "PUPPETS", "REBELLION", "CLEANERS", "CHOKERS",
                "FESTIVAL", "VENUE", "MICROPHONE", "RANGE",
                "NORMAL", "LORD", "MOMENT", "EFFORT", "RULE",
            }
            if stripped in _common_upper:
                return "dialogue"

            has_strong_repeat = bool(re.search(r"(.)\1{2,}", stripped))
            vowel_count = sum(1 for c in stripped if c in "AEIOU")

            consonant_run = bool(re.search(r"[BCDFGHJKLMNPQRSTVWXYZ]{4,}", stripped))
            ends_with_impact = any(
                stripped.endswith(suf)
                for suf in (
                    "AC", "ACK", "AK", "UM", "OOM", "ANG", "ONG",
                    "ASH", "ISH", "USH", "AMM", "ANN",

                )
            )
            looks_invented = (
                has_strong_repeat
                or consonant_run
                or ends_with_impact
                or (vowel_count == 0 and len(stripped) >= 3)
            )

            if looks_invented:
                return "sfx"

            return "dialogue"

        if not has_cjk and len(alpha_only) <= 2 and len(stripped) <= 4 and stripped.upper() != "I":
            return "junk"

        return "dialogue"

    @staticmethod
    def _column_line_groups(idxs, bbs, rtl: bool = True):
        """ — ستون‌بندیِ خط‌هایِ OCRِ یک ناحیه.

        وقتی چند خطِ افقی در «دو ستونِ» کنارِ هم‌اند (مثلاً متنِ حباب +
        متنِ دست‌نویسِ کنارِ حباب در 01.jpg) مرتب‌سازیِ (y,x) آن‌ها را در
        هم می‌پیچد («THEN PULL I'LL THE 're FLOAT FOR real YOU! action
        nere.»). اینجا خط‌ها با فاصلهٔ مرکزِ x خوشه می‌شوند؛ فقط وقتی
        ≥۲ خوشهٔ ≥۲خطی که بازهٔ yشان همپوشانیِ معنادار دارد و همهٔ خط‌ها
        افقی‌اند، گروه‌بندی معتبر است. خروجی: لیستِ گروه‌ها (هر گروه لیستِ
        اندیس، ستون‌ها به ترتیبِ جهتِ خواندن) یا None = مرتب‌سازیِ عادی.
        """
        try:
            if len(idxs) < 4:
                return None
            lines = []
            for i in idxs:
                bb = bbs[i] if (bbs and 0 <= i < len(bbs)) else None
                if bb is None:
                    return None
                bw = float(bb[2] - bb[0])
                bh = float(bb[3] - bb[1])
                if bw <= 0 or bh <= 0:
                    return None
                if bw < bh * 1.15:
                    return None  # خطِ عمودی/کوتاه → ستون‌بندی ممنوع
                lines.append(((float(bb[0]) + float(bb[2])) / 2.0,
                              float(bb[1]), float(bb[3]), i))
            lines.sort(key=lambda t: t[0])
            med_h = sorted(t[2] - t[1] for t in lines)[len(lines) // 2]
            gap_thr = max(0.85 * med_h, 32.0)
            clusters = [[lines[0]]]
            for ln in lines[1:]:
                if ln[0] - clusters[-1][-1][0] > gap_thr:
                    clusters.append([ln])
                else:
                    clusters[-1].append(ln)
            clusters = [c for c in clusters if len(c) >= 2]
            if len(clusters) < 2:
                return None
            spans = [(min(t[1] for t in c), max(t[2] for t in c))
                     for c in clusters]
            for a in range(len(clusters)):
                for b in range(a + 1, len(clusters)):
                    oy = (min(spans[a][1], spans[b][1])
                          - max(spans[a][0], spans[b][0]))
                    short = min(spans[a][1] - spans[a][0],
                                spans[b][1] - spans[b][0])
                    if short <= 0 or oy < short * 0.35:
                        return None
            clusters.sort(
                key=lambda c: -(sum(t[0] for t in c) / len(c)) if rtl
                else (sum(t[0] for t in c) / len(c)))
            return [[t[3] for t in c] for c in clusters]
        except Exception:
            return None

    def _ink_mask_inside_bubble(self, gray: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> np.ndarray:

        crop = gray[y0:y1, x0:x1]
        ch, cw = crop.shape[:2]
        if ch < 8 or cw < 8:
            return np.zeros((ch, cw), dtype=np.uint8)

        med = float(np.median(crop))

        def _mask(dark: bool) -> np.ndarray:
            if dark:
                hard = (crop < max(100, med - 40)).astype(np.uint8) * 255
                flag = cv2.THRESH_BINARY_INV
            else:

                if med < 128:
                    bright_t = max(150, med + 60)
                else:
# سقفِ ۱۸۰ برای زمینهٔ روشنِ رنگی (زرد با
# مدین ~۲۰۰) کلِ زمینه را هم «متنِ روشن» می‌خواند
# سقف برداشته شد تا فقط واقعاً روشن‌تر از زمینه بیاید.
                    bright_t = med + 40
                hard = (crop > bright_t).astype(np.uint8) * 255
                flag = cv2.THRESH_BINARY
            try:
                ad = cv2.adaptiveThreshold(
                    crop, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    flag, 15, 11,
                )

                mean = cv2.boxFilter(crop, ddepth=cv2.CV_32F, ksize=(15, 15))
                flat = np.abs(crop.astype(np.float32) - mean) < 12.0
                ad[flat] = 0
            except Exception:
                ad = hard
            m = cv2.bitwise_or(hard, ad)
            return cv2.morphologyEx(
                m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8), iterations=1
            )

        dark_ink = _mask(True)
        dark_cov = float(np.count_nonzero(dark_ink)) / float(max(1, ch * cw))

# متنِ روشن روی زمینهٔ رنگی (حبابِ زرد با متنِ سفید):
# وقتی dark_cov خیلی کم است (متنِ تیره‌ای نیست) هم باید bright را
# امتحان کرد؛ قبلاً فقط وقتی dark_cov > 0.45 بود bright چک می‌شد
# → متنِ سفید روی زرد هرگز ماسک نمی‌شد و «جا می‌ماند».
        if dark_cov > 0.45 or dark_cov < 0.08:
            bright_ink = _mask(False)
            bright_cov = float(np.count_nonzero(bright_ink)) / float(max(1, ch * cw))
            if 0.02 < bright_cov < 0.60:
                if dark_cov < 0.08 or bright_cov < dark_cov:
                    return bright_ink
        return dark_ink

    @staticmethod
    def _text_zone_in_crop(region: "TextRegion", x0: int, y0: int, x1: int, y1: int):

        cw, ch = x1 - x0, y1 - y0
        if cw < 4 or ch < 4:
            return None

        polys = list(getattr(region, "ocr_polys", None) or [])
        _, _, rw, rh = region.rect
        rect_area = max(1, int(rw) * int(rh))

        if not polys:
            for b in list(getattr(region, "boxes", None) or []):
                pts = np.asarray(b, dtype=np.int32).reshape(-1, 2)
                if pts.size < 6:
                    continue
                bx0, by0 = int(pts[:, 0].min()), int(pts[:, 1].min())
                bx1, by1 = int(pts[:, 0].max()), int(pts[:, 1].max())
                b_area = max(1, (bx1 - bx0) * (by1 - by0))
                if b_area >= 0.75 * rect_area:
                    continue
                polys.append(pts)

        if not polys:
            return None

        zone = np.zeros((ch, cw), dtype=np.uint8)
        for poly in polys:
            pts = np.asarray(poly, dtype=np.int32).reshape(-1, 2).copy()
            if pts.size == 0:
                continue
            pts[:, 0] -= x0
            pts[:, 1] -= y0
            cv2.fillPoly(zone, [pts], 255)
        if zone.max() == 0:
            return None

        return zone

    @staticmethod
    def _protect_bubble_wall(ink: np.ndarray, gray_crop: np.ndarray) -> np.ndarray:

        ch, cw = ink.shape[:2]
        if ch < 12 or cw < 12:
            return ink

        border = max(6, min(20, min(ch, cw) // 7))
        protected = ink.copy()
        protected[:border, :] = 0
        protected[-border:, :] = 0
        protected[:, :border] = 0
        protected[:, -border:] = 0

        try:
            edges = cv2.Canny(gray_crop, 50, 120)
            edges = cv2.dilate(edges, np.ones((2, 2), np.uint8), iterations=1)
            n, lab, st, _ = cv2.connectedComponentsWithStats(edges, connectivity=8)
            wall = np.zeros_like(edges)
            for i in range(1, n):
                a = int(st[i, cv2.CC_STAT_AREA])
                bw = int(st[i, cv2.CC_STAT_WIDTH])
                bh = int(st[i, cv2.CC_STAT_HEIGHT])
                ls, ss = max(bw, bh), max(1, min(bw, bh))

                if ss <= 5 and ls >= max(18, int(0.25 * max(ch, cw))):
                    wall[lab == i] = 255
                elif a > 0.08 * ch * cw and ss <= 8:
                    wall[lab == i] = 255
            wall = cv2.dilate(wall, np.ones((2, 2), np.uint8), iterations=1)
            protected = cv2.bitwise_and(protected, cv2.bitwise_not(wall))
        except Exception:
            pass

        n2, lab2, st2, _ = cv2.connectedComponentsWithStats(protected, connectivity=8)
        keep = np.zeros_like(protected)
        page_a = float(max(1, ch * cw))
        for i in range(1, n2):
            a = int(st2[i, cv2.CC_STAT_AREA])
            bw = int(st2[i, cv2.CC_STAT_WIDTH])
            bh = int(st2[i, cv2.CC_STAT_HEIGHT])
            if a < 3:
                continue
            ls, ss = max(bw, bh), max(1, min(bw, bh))
            if ss <= 3 and ls >= int(0.30 * max(ch, cw)):
                continue
            if a > 0.20 * page_a:
                continue
            if ls >= int(0.70 * max(ch, cw)) and ss <= 6:
                continue
            keep[lab2 == i] = 255

        keep = cv2.dilate(keep, np.ones((2, 2), np.uint8), iterations=1)
        return keep

    @staticmethod
    def _drop_non_text_components(ink: np.ndarray, ch: int, cw: int) -> np.ndarray:

        try:
            n, lab, st, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
        except Exception:
            return ink
        keep = np.zeros_like(ink)
        crop_area = float(max(1, ch * cw))
        for i in range(1, n):
            a = int(st[i, cv2.CC_STAT_AREA])
            if a < 6:
                continue
            bw = int(st[i, cv2.CC_STAT_WIDTH])
            bh = int(st[i, cv2.CC_STAT_HEIGHT])
            if a > 0.12 * crop_area:
                continue
            if bh > 0.50 * ch or bw > 0.90 * cw:
                continue
            keep[lab == i] = 255
        return keep

    @staticmethod
    def _fill_holes_mask(m: np.ndarray) -> np.ndarray:
        """ — حفره‌هایِ یک ماسکِ بولی را پر می‌کند (خروجی: بولی).
        برای «نسخهٔ پرشدهٔ» کامپوننتِ زمینهٔ روشن: جزیره‌هایِ تیرهٔ متنِ
        داخلش جزوِ آن می‌شوند؛ ساختارهایِ وصلِ به بیرون (دیوارِ حباب که
        شکاف دارد و به زمینه می‌رسد) هرگز حفره حساب نمی‌شوند."""
        m_u8 = (np.asarray(m).astype(np.uint8)) * 255
        padc = cv2.copyMakeBorder(m_u8, 1, 1, 1, 1,
                                  cv2.BORDER_CONSTANT, value=0)
        ff = padc.copy()
        ffm = np.zeros((padc.shape[0] + 2, padc.shape[1] + 2), np.uint8)
        cv2.floodFill(ff, ffm, (0, 0), 255)
        return cv2.bitwise_or(padc, cv2.bitwise_not(ff))[1:-1, 1:-1] > 0

    def _bubble_interior_mask(self, gray_crop: np.ndarray, zone: np.ndarray,
                              erode_iters: int = 2) -> Optional[np.ndarray]:
        """ — اینتریورِ «ضدِ نشت».
        روشِ قدیم: کامپوننتِ روشنِ چسبیده به ماسک + پرکردنِ حفره — اگر دیوارِ
        حباب شکافِ JPEG داشت (۱-۳px)، کامپوننت از شکاف به زمینهٔ بیرون
        «نشت» می‌کرد → اینتریور = حباب + کلِ زمینه (b03: ۸۷٪ کراپ!) →
        گاردِ ضدتوهم حباب را «ناحیهٔ باز» می‌خواند و رد می‌کرد → توهمِ
        LaMa قبول؛ tighten/limit کار نمی‌کردند؛ سویپ‌ها دامینِ غلط
        می‌گرفتند و دیوار را می‌بلعیدند (حبابِ «THIS IS THE DRAFT…» در
        chapter-264/8 کلاً پاک می‌شد).
        روشِ جدید: «دیوار» (نقطهٔ مقابلِ رنگِ اینتریور) را اول CLOSE 5x5
        می‌کنیم (شکافِ ≤۴px مهر می‌شود) بعد از مرزِ کراپ سیلاب می‌بریم —
        هر پیکسلِ هم‌رنگِ اینتریور که از مرز قابل‌دسترس نباشد = جیبِ
        محصور = اینتریورِ واقعی. حفره‌هایِ داخلِ جیب (جزیره‌هایِ متن)
        پر می‌شوند؛ دیوار (بیرونِ جیب) هرگز داخلِ خروجی نمی‌آید."""
        ch, cw = gray_crop.shape[:2]
        if zone is None or cv2.countNonZero(zone) == 0:
            return None
        med = float(np.median(gray_crop))
        if med >= 128:
            fill_s = (gray_crop >= max(120, med - 60))
        else:
            fill_s = (gray_crop <= min(150, med + 60))
        wall = (~fill_s).astype(np.uint8) * 255
# مهرِ شکاف‌هایِ دیوار — جایگزینِ CLOSE/erodeِ قدیمی
        wall = cv2.morphologyEx(wall, cv2.MORPH_CLOSE,
                                np.ones((5, 5), np.uint8))
        fill_c = (wall == 0)
# سیلاب از مرزِ کراپ روی «پر» → بیرون؛ هرچه unreachable = جیبِ محصور
        pad = cv2.copyMakeBorder(fill_c.astype(np.uint8) * 255, 1, 1, 1, 1,
                                 cv2.BORDER_CONSTANT, value=255)
        ffm = np.zeros((pad.shape[0] + 2, pad.shape[1] + 2), np.uint8)
        cv2.floodFill(pad, ffm, (0, 0), 128)
        outside = (pad == 128)[1:-1, 1:-1]
        pockets = fill_c & ~outside
        if not pockets.any():
            return None
        n, lab = cv2.connectedComponents(pockets.astype(np.uint8),
                                         connectivity=4)
        seed = cv2.dilate(zone, np.ones((3, 3), np.uint8), iterations=3)
        labs = lab[seed > 0]
        vals, cnts = np.unique(labs[labs > 0], return_counts=True)
        if len(vals) == 0:
            return None
        comp = (lab == vals[int(np.argmax(cnts))])
        if int(np.count_nonzero(comp)) < 0.10 * ch * cw:
            return None
# پر کردن جزیره‌هایِ متنِ داخلِ جیب — دیوار بیرونِ جیب است و هرگز
# داخلِ filled نمی‌آید (همین تضمینِ زنده‌ماندنِ دیوار است)
        padc = cv2.copyMakeBorder(comp.astype(np.uint8) * 255, 1, 1, 1, 1,
                                  cv2.BORDER_CONSTANT, value=0)
        ff = padc.copy()
        ffm2 = np.zeros((padc.shape[0] + 2, padc.shape[1] + 2), np.uint8)
        cv2.floodFill(ff, ffm2, (0, 0), 255)
        filled = cv2.bitwise_or(padc, cv2.bitwise_not(ff))[1:-1, 1:-1]
        if float(np.count_nonzero(filled)) > 0.95 * ch * cw:
            return None
# erode_iters — مسیرِ limit/tighten/guard با ۱ (۳px)، بقیه ۲ (۶px)
        it = max(0, int(erode_iters))
        if it:
            filled = cv2.erode(filled, np.ones((3, 3), np.uint8),
                               iterations=it)
        return filled

    @staticmethod
    def _box_bg_stats(image: np.ndarray, bx0: int, by0: int,
                     bx1: int, by1: int):
        """ — آمارِ «خوشهٔ رنگِ غالبِ» داخلِ باکس (بر مبنای
        هیستوگرامِ سه‌کاناله، نه فقط خاکستری — باکسِ حبابِ بیضی گوشه‌هایش
        زمینهٔ پنل است و باستِ تک‌کاناله قاطی می‌شود).
        خروجی: (frac, cstd, hf, fillc) یا None."""
        try:
            _ih, _iw = image.shape[:2]
            bx0 = max(0, int(bx0)); by0 = max(0, int(by0))
            bx1 = min(_iw, int(bx1)); by1 = min(_ih, int(by1))
            if bx1 - bx0 < 24 or by1 - by0 < 24:
                return None
            oc = image[by0:by1, bx0:bx1]
# خوشهٔ غالب: هیستوگرامِ درشتِ ۱۶×۱۶×۱۶
            q = (oc.astype(np.int32) >> 4)  # 0..15
            flat = (q[..., 0] * 256 + q[..., 1] * 16 + q[..., 2]).ravel()
            hist = np.bincount(flat, minlength=4096)
            dom = int(np.argmax(hist))
            dc = np.array([(dom >> 8) * 16 + 8,
                           ((dom >> 4) & 15) * 16 + 8,
                           (dom & 15) * 16 + 8], np.float32)
            bg = (np.abs(oc.astype(np.float32) - dc[None, None, :])
                  <= 22.0).all(axis=2)
            frac = float(bg.mean())
            if frac < 0.35:
                return None
            bpx = oc[bg].astype(np.float32)
            cstd = float(bpx.std(axis=0).max())
            og = cv2.cvtColor(oc, cv2.COLOR_BGR2GRAY)
            bl = cv2.blur(og, (9, 9))
            hf = float((np.abs(og.astype(np.float32) - bl) > 15.0)[bg].mean())
            fillc = np.median(bpx, axis=0)
            return (frac, cstd, hf, fillc)
        except Exception:
            return None

    @staticmethod
    def _box_bg_textured(image: np.ndarray, bx0: int, by0: int,
                         bx1: int, by1: int) -> bool:
        """ — آیا «زمینهٔ داخلِ جعبه/حباب» بافت‌مند است؟
        (پرده/بوکه = LaMa بهتر؛ سیاهِ خالص/گرادیانِ صاف = پرِ فوریِ
        گرادیانیِ خودش تمیزتر است — نمونهٔ کارتِ Crimson Dragon).
         — با خوشهٔ غالبِ سه‌کاناله (باکسِ بیضی گوشه‌هایش
        زمینهٔ پنل است)."""
        st = MangaTranslator._box_bg_stats(image, bx0, by0, bx1, by1)
        if st is None:
            return True
        frac, cstd, hf, _fillc = st
# گرادیانِ صاف (کارتِ Crimson Dragon) cstd بالا ولی
# hf پایین دارد → «بافت‌مند» نیست؛ پرِ فوریِ گرادیانیِ خودش بهتر است.
# فقط بافتِ فرکانس‌بالا (پرده/بوکه/سکرین‌تون) LaMa می‌خواهد.
        return hf >= 0.05

    def _uncovered_ink_bands(self, image: np.ndarray, box,
                             known_mask: np.ndarray) -> Optional[np.ndarray]:
        """ — «نجاتِ جوهرِ پوشش‌داده‌نشده»: OCR گاهی خطی را در
        پالی‌ها جا می‌اندازد یا پالی‌اش را جایِ غلط می‌گذارد (نمونه‌ها:
        خطِ «기회야…!» در تستِ کره‌ای، متنِ کوچکِ لبهٔ صفحه در 01.jpg،
        «段/子» ژاپنی). این جوهر نه در نوارهای کامپوز بود نه در ماسکِ
        donor → در خروجی زنده می‌ماند.
        راه‌حل: کامپوننت‌های جوهرِ تازه (تیره یا روشن — قطب با جرم) داخلِ
        حباب که هیچ نوار/ماسکی نمی‌پوشاند → نوارِ نجات با دیلیتِ ۷."""
        try:
            bx0, by0, bx1, by1 = [int(v) for v in box]
            ih, iw = image.shape[:2]
            bx0 = max(0, bx0); by0 = max(0, by0)
            bx1 = min(iw, bx1); by1 = min(ih, by1)
            if bx1 - bx0 < 24 or by1 - by0 < 24:
                return None
            oc = image[by0:by1, bx0:bx1]
            g = cv2.cvtColor(oc, cv2.COLOR_BGR2GRAY)
            med = float(np.median(g))
            dark = (g < med - 32.0)
            bright = (g > med + 42.0)
            core = dark if float(dark.mean()) >= float(bright.mean()) else bright
            if float(core.mean()) > 0.30:
                return None  # بلوکِ تیره/پر از جوهر — هنر است نه خطِ جا‌مانده
            cu = cv2.morphologyEx(
                core.astype(np.uint8) * 255, cv2.MORPH_CLOSE,
                np.ones((3, 3), np.uint8))
            known = known_mask[by0:by1, bx0:bx1] > 0
            _k7 = np.ones((7, 7), np.uint8)
            known_d = cv2.dilate(known.astype(np.uint8), _k7) > 0
            fresh = (cu > 0) & ~known_d
            if not fresh.any():
                return None
            nz, lal, sts, _ = cv2.connectedComponentsWithStats(
                fresh.astype(np.uint8), connectivity=8)
# اضلاعِ جعبه که به لبهٔ تصویر می‌خورند: تکه‌متنِ
# بریدهٔ لبه (نیم‌خطِ وبتون) ممکن است در یک کامپوننتِ پهن
# ادغام شده باشد؛ سقفِ معمولیِ 100px آن را رد می‌کرد →
# برایِ کامپوننت‌هایی که به ضلعِ لبه‌ای چسبیده‌اند سقف بزرگ‌تر.
            _edge_sides = {"t": by0 <= 0, "b": by1 >= ih,
                           "l": bx0 <= 0, "r": bx1 >= iw}
            keep = np.zeros_like(cu)
            for ci in range(1, nz):
                a = int(sts[ci, cv2.CC_STAT_AREA])
                cwd = int(sts[ci, cv2.CC_STAT_WIDTH])
                chg = int(sts[ci, cv2.CC_STAT_HEIGHT])
                _cy0 = int(sts[ci, cv2.CC_STAT_TOP])
                _cx0 = int(sts[ci, cv2.CC_STAT_LEFT])
                _on_edge = (
                    (_edge_sides["t"] and _cy0 <= 1)
                    or (_edge_sides["b"] and _cy0 + chg >= (by1 - by0) - 1)
                    or (_edge_sides["l"] and _cx0 <= 1)
                    or (_edge_sides["r"] and _cx0 + cwd >= (bx1 - bx0) - 1))
                _max_dim = 240 if _on_edge else 100
                _max_area = 2800 if _on_edge else 1600
# حروف: کوچک/کشیده؛ هنر: تودهٔ بزرگ یا مستطیلِ عظیم
                if a < 8 or a > _max_area or max(cwd, chg) > _max_dim:
                    continue
                if _on_edge:
# قوسِ دیوارِ حباب هم به لبه می‌چسبد ولی «بلند» است
# (نیم‌خطِ حرف ≤ ~16px)؛ بلندیِ >40px یا >45٪ جعبه =
# دیوار/قاب، نه تکه‌متن.
                    if chg > 40 or chg > 0.45 * max(24, by1 - by0):
                        continue
# فقط «قلمِ نازکِ متن» (ضخامت ≤۶px): خطِ
# دست‌کشیدهٔ ضخیمِ حبابِ کیمتسو/ژاپنی جوهر نیست — دیوار است
                try:
                    _cmc = (lal == ci)
                    _dtc = cv2.distanceTransform(
                        _cmc.astype(np.uint8), cv2.DIST_L2, 3)
                    if float(_dtc.max()) * 2.0 > 12.0:
                        continue
                except Exception:
                    pass
# «قوسِ دیواره از مرزِ جعبه می‌گذرد»:
# گزارشِ سازنده (صفحهٔ SHAN SHAN?!/DON'T TELL ME —
# 10.jpg): «جای پاک شده ک متن نیست … سمت چپ پایین …
# بخاطر همین میگم حباب خراب کرده». ریشهٔ یابی‌شده با
# دامپِ مرحله‌ای: قطعهٔ قوسِ دیوارهٔ حباب که جعبهٔ
# donor از میانش می‌گذرد (۴ نمونهٔ این صفحه: 49×93 و
# 97×26 و 44×82 و 43×77 — همه به ضلعِ «داخلیِ» جعبه
# چسبیده) «جوهرِ پوشش‌نداده‌شده» خوانده میشد → نوارِ
# نجات → ماسکِ کامپوز + دامنهٔ جارویِ بقایا → جارو آن
# را «بقایایِ متنِ پاک‌نشده» می‌پنداشت و با TELEA
# پاکش میکرد → دیوارِ پایینِ حباب ناپدید میشد و
# کامپوزِ گارانتیِ نهایی هم (چون دیوار داخلِ ماسکِ
# کامپوز بود) نسخهٔ خراب را نگه میداشت. متنِ جاماندهٔ
# واقعی همیشه «داخلِ» جعبه شناور است؛ ساختار
# (دیوار/قاب/قوس) از مرزِ برش عبور میکند و در سمتِ
# دیگر هم ادامه دارد. گارد: اگر همان خطِ جوهر در
# ≤۶px بیرونِ جعبه — در ستونهایِ تماسِ کامپوننت با
# آن ضلع — ادامه داشته باشد (≥۳۵٪ ستونها)، کامپوننت
# دیوار/ساختار است، نه تکه‌متن → از نجات خارج.
# ضلعِ «لبهٔ تصویر» (وبتونِ بریده — ) مشمولِ
# این گارد نیست؛ فقط ضلعِ داخلیِ جعبه.
                try:
                    _cmc2 = (lal == ci)
                    _sides = []
                    if _cy0 <= 1:
                        _sides.append("t")
                    if _cy0 + chg >= (by1 - by0) - 1:
                        _sides.append("b")
                    if _cx0 <= 1:
                        _sides.append("l")
                    if _cx0 + cwd >= (bx1 - bx0) - 1:
                        _sides.append("r")
                    _interior = {"t": by0 > 0, "b": by1 < ih,
                                    "l": bx0 > 0, "r": bx1 < iw}
                    if any(_interior[_s] for _s in _sides):
                        _bright = float(bright.mean()) > float(dark.mean())
                        _cont = False
                        for _sd in _sides:
                            if not _interior[_sd]:
                                continue
                            if _sd in ("t", "b"):
                                _tr = (_cmc2[:2, :] if _sd == "t"
                                          else _cmc2[-2:, :])
                                _cols = np.nonzero(
                                    _tr.any(axis=0))[0]
                                if _cols.size == 0:
                                    continue
                                if _sd == "t":
                                    _og = cv2.cvtColor(
                                        image[max(0, by0 - 6):by0,
                                              bx0:bx1],
                                        cv2.COLOR_BGR2GRAY)
                                    _ig = g[:2, :]
                                else:
                                    _og = cv2.cvtColor(
                                        image[by1:min(ih, by1 + 6),
                                              bx0:bx1],
                                        cv2.COLOR_BGR2GRAY)
                                    _ig = g[-2:, :]
                                if _og.shape[0] == 0:
                                    continue
                                _out = _og.min(axis=0)
                                _in = (_ig.max(axis=0)
                                          if _bright
                                          else _ig.min(axis=0))
                            else:
                                _tc = (_cmc2[:, :2] if _sd == "l"
                                          else _cmc2[:, -2:])
                                _rows = np.nonzero(
                                    _tc.any(axis=1))[0]
                                if _rows.size == 0:
                                    continue
                                if _sd == "l":
                                    _og = cv2.cvtColor(
                                        image[by0:by1,
                                              max(0, bx0 - 6):bx0],
                                        cv2.COLOR_BGR2GRAY)
                                    _ig = g[:, :2]
                                else:
                                    _og = cv2.cvtColor(
                                        image[by0:by1,
                                              bx1:min(iw, bx1 + 6)],
                                        cv2.COLOR_BGR2GRAY)
                                    _ig = g[:, -2:]
                                if _og.shape[1] == 0:
                                    continue
                                _out = _og.min(axis=1)
                                _in = (_ig.max(axis=1)
                                          if _bright
                                          else _ig.min(axis=1))
                            if _bright:
                                _hit = (
                                    _out[_cols if _sd in ("t", "b")
                                            else _rows]
                                    >= np.minimum(
                                        _in[_cols
                                               if _sd in ("t", "b")
                                               else _rows] - 35.0,
                                        105.0))
                            else:
                                _hit = (
                                    _out[_cols if _sd in ("t", "b")
                                            else _rows]
                                    <= np.maximum(
                                        _in[_cols
                                               if _sd in ("t", "b")
                                               else _rows] + 35.0,
                                        150.0))
                            if float(_hit.mean()) >= 0.35:
                                _cont = True
                                break
                        if _cont:
                            continue
                except Exception:
                    pass
                keep |= (lal == ci)
# پاسِ ویژهٔ لبه: نیم‌خطِ بریدهٔ وبتون (صفحه‌ای که
# از وسطِ حباب شروع/تمام می‌شود) هیچ پالیِ OCR ندارد و
# known_d (دیلیتِ ۷ ماسکِ خطِ بعدی) آن را «پوشش‌داده» جا
# می‌زند. اینجا CC رویِ جوهرِ کاملِ جعبه: فقط کامپوننت‌هایی که
# (۱) پیکسلِ تازه در نوارِ ۱۴px لبه دارند (۲) خودِ کامپوننتِ
# کامل به ضلعِ لبه‌ای چسبیده (۳) کوتاه‌اند (≤40px و ≤45٪ جعبه —
# قوسِ بلندِ دیوار رد می‌شود) (۴) قلمِ نازک‌اند → نجات.
            if any(_edge_sides.values()):
                _eb = 14
                _bandm = np.zeros_like(cu)
                if _edge_sides["t"]:
                    _bandm[:_eb, :] = 1
                if _edge_sides["b"]:
                    _bandm[-_eb:, :] = 1
                if _edge_sides["l"]:
                    _bandm[:, :_eb] = 1
                if _edge_sides["r"]:
                    _bandm[:, -_eb:] = 1
                _fresh_edge = (cu > 0) & (_bandm > 0)
# نکته: «known» اینجا ماسکِ کارشده (نوارهای دیلیت‌شده) است
# و ردیف‌هایِ لبه را از قبل بلعیده؛ پس در نوارِ لبهِ ۱۴px
# همهٔ جوهرِ جعبه کاندید است — اجتماع با ماسکِ موجود
# بیضرر است و دیوار/محافظتها پایینتر فیلتر میشوند.
                if _fresh_edge.any():
                    _nz2, _lal2, _sts2, _ = cv2.connectedComponentsWithStats(
                        cu.astype(np.uint8), connectivity=8)
                    _bh = max(24, by1 - by0)
                    for _c2 in range(1, _nz2):
                        _comp = (_lal2 == _c2)
                        if not bool((_comp & _fresh_edge).any()):
                            continue
                        _a2 = int(_sts2[_c2, cv2.CC_STAT_AREA])
                        _w2 = int(_sts2[_c2, cv2.CC_STAT_WIDTH])
                        _h2 = int(_sts2[_c2, cv2.CC_STAT_HEIGHT])
                        _y2 = int(_sts2[_c2, cv2.CC_STAT_TOP])
                        _x2 = int(_sts2[_c2, cv2.CC_STAT_LEFT])
                        if not (
                                (_edge_sides["t"] and _y2 <= 1)
                                or (_edge_sides["b"] and
                                    _y2 + _h2 >= (by1 - by0) - 1)
                                or (_edge_sides["l"] and _x2 <= 1)
                                or (_edge_sides["r"] and
                                    _x2 + _w2 >= (bx1 - bx0) - 1)):
                            continue
# قوسِ دیوار = بلند؛ تکه‌متنِ حرف = کوتاه
                        if _h2 > 40 or _h2 > 0.45 * _bh:
                            continue
                        if _a2 < 8 or _a2 > 2800 or max(_w2, _h2) > 240:
                            continue
                        try:
                            _dt2 = cv2.distanceTransform(
                                _comp.astype(np.uint8), cv2.DIST_L2, 3)
                            if float(_dt2.max()) * 2.0 > 12.0:
                                continue
                        except Exception:
                            pass
# ~known نمیخواهیم: کامپوننتِ کوتاهِ نازکِ چسبیده
# به لبه validated شده؛ اجتماع با ماسکِ موجود
# idempotent است.
                        keep |= _comp
            if int(cv2.countNonZero(keep)) < 16:
                return None
            bands = cv2.dilate(keep, _k7)
# دیوار/کادر هرگز داخلِ نجات نیاید
            for _pm in (getattr(self, "_page_protect", None),
                        getattr(self, "_page_wall_band", None)):
                if _pm is not None and _pm.shape == image.shape[:2]:
                    bands &= (_pm[by0:by1, bx0:bx1] == 0)
            if int(cv2.countNonZero(bands)) < 16:
                return None
            full = np.zeros(image.shape[:2], dtype=np.uint8)
            full[by0:by1, bx0:bx1] = bands
            return full
        except Exception:
            return None

    def _expand_donor_text_strips(self, image: np.ndarray,
                                  mask: np.ndarray,
                                  regions) -> np.ndarray:
        """ — ماسکِ donor (عکسِ اول) = «فقط نوارهایِ متن + پدِ
        سخاوتمندانه» — نه کلِ داخلِ حباب. درخواستِ صریحِ کاربر:
        «عکسِ اول متن‌هاش کامل بپاکه — اشکال نداره حباب خراب شه یا بیشتر
        پاک شه. بعد خط به خط برش بخوره به عکسِ دوم بچسونه» +
        «چرا کل حباب انتقال میدی؟ اگ یک کلمه کل حباب حساب میشه حروف به
        حروف برش بزنه انتقال بده».

        چرا کلِ داخلِ حباب (/73) بد بود:
        ۱) LaMa با ماسکِ عظیمِ اینتریور، داخلِ حبابِ رنگی را با خمیرِ
           خاکستریِ بی‌رنگ پر می‌کند (نمونهٔ 01.jpg: حبابِ زردِ
           [125,235,253] → خاکستریِ [220,227,220] = «لگه») چون مرزِ ماسک
           دور از زمینهٔ زرد است و LaMa رنگِ حباب را «زمینه» نمی‌بیند.
        ۲) ماسکِ ۵-۱۰ برابری = LaMaی کند روی گوشی (لاگِ POCO: 93.9s برای
           یک صفحه) + موج‌های «parallel rescue / LaMa group rejected».
        با نوارِ متن + پد، پرِ LaMa از هر طرف با زمینهٔ اورجینالِ خودِ
        حباب لنگر می‌شود (حبابِ زرد → پرِ زرد) و ماسک کوچک می‌ماند.
        دیوارِ حباب در donor ممکن است بخورد — اشکالی ندارد: کامپوز فقط
        نوارِ متن را منتقل می‌کند و دیوار همیشه از عکسِ دوم می‌آید
        (گارانتیِ _compose_two_image با protect/wall_band).

        نوارهایِ نجاتِ جوهرِ جا‌مانده (`_uncovered_ink_bands` — خطی که OCR
        پالی‌اش را جا انداخته) مثل قبل به ماسک اضافه می‌شوند تا در donor
        پاک شوند؛ فقط «افزودنِ کلِ اینتریور» حذف شد."""
        try:
            if mask is None or not np.any(mask):
                self._donor_skip_ids = set()
                self._donor_boxes = []
                return mask
            h_img, w_img = image.shape[:2]
            _base_n = int(np.count_nonzero(mask))
# پدِ سخاوتمندانه دورِ نوارها: مرزِ ماسک رویِ زمینهٔ تمیز
# بیفتد نه رویِ هالهٔ جوهر → بازسازیِ LaMa شبح نمی‌گیرد.
# دیوار در donor آزاد است (بالا) ولی برای پرکننده‌هایِ فوری
# همان protect حفظ می‌شود تا پرِ تخت رویِ دیوار نسازد.
            _pad = np.ones((9, 9), np.uint8)
            out = cv2.dilate(mask, _pad)
            _protect = getattr(self, "_page_protect", None)
            if _protect is not None and _protect.shape == out.shape:
# فقط «قابِ رنگیِ» 206j از donor آزاد میشود
# (رنگِ قاب نباید واردِ پرِ متن شود — لکهٔ سبزِ up0822)
# دیوارِ تیره مثلِ قبل در donor دستنخورده میماند تا پرِ
# LaMa سیاهیِ دیوار را داخلِ نوار نکشد (img6).
                _colj2 = getattr(self, "_page_colored_protect", None)
                if _colj2 is not None and _colj2.shape == out.shape:
                    out = cv2.bitwise_and(out, cv2.bitwise_not(_colj2))
                else:
                    out = cv2.bitwise_and(out, cv2.bitwise_not(_protect))
            if not np.any(out):
                out = mask.copy()
            _added = int(np.count_nonzero(out)) - _base_n
# «اگ یک کلمه کل حباب حساب میشه حروف به حروف برش
# بزنه»: ناحیه‌هایِ «متنِ متراکم» (≥۳۴٪ پوششِ پالی‌ها — همان
# شرطِ _polys_denseِ سازندهٔ ماسک) در ماسکِ خام «مستطیلِ بلوک»
# می‌شوند که تقریباً کلِ داخلِ حباب است → LaMa با سوراخِ عظیم
# داخلِ حبابِ زرد را خمیرِ خاکستری می‌کرد (نمونهٔ 01.jpg).
# در donor، بلوک با «نوارِ خط‌به‌خطِ جوهر + پد» جایگزین می‌شود
# (همان نوارهایی که کامپوز منتقل می‌کند) + جوهرِ واقعیِ اطراف
# (تیره یا روشن) تا هیچ مرکبِ جا‌مانده‌ای زنده نماند.
            try:
                _k = np.ones((11, 11), np.uint8)
                for region in (regions or []):
                    try:
                        _pl = []
                        for _p in (getattr(region, "ocr_polys", None)
                                     or []):
                            try:
                                _pp = np.asarray(
                                    _p, dtype=np.float32).reshape(-1, 2)
                            except Exception:
                                continue
                            if _pp.shape[0] >= 3:
                                _pl.append(_pp)
                        if len(_pl) < 2:
                            continue
                        if not MangaTranslator._polys_dense(_pl):
                            continue
                        _res = self._compose_region_strips(image, region)
                        _st = None
                        if _res:
                            _m, _f = _res[0], _res[1]
                            if _m is None or _m.shape != out.shape:
                                _m = np.zeros(out.shape, np.uint8)
                            if _f is None or _f.shape != out.shape:
                                _f = np.zeros(out.shape, np.uint8)
                            _st = (_m > 0) | (_f > 0)
                        if _st is None or not _st.any():
                            continue
                        _bb = MangaTranslator._text_block_box(
                            _pl, region.rect, False)
                        if not _bb:
                            continue
# خروجیِ _text_block_box = (x, y, w, h)
                        _zx0 = max(0, int(_bb[0]))
                        _zy0 = max(0, int(_bb[1]))
                        _zx1 = min(w_img, _zx0 + int(_bb[2]))
                        _zy1 = min(h_img, _zy0 + int(_bb[3]))
                        if _zx1 - _zx0 < 24 or _zy1 - _zy0 < 24:
                            continue
                        _keep = cv2.dilate(
                            _st.astype(np.uint8), _k) > 0
# جوهرِ واقعیِ داخلِ بلوک (تیره یا روشن) که نوارها
# نپوشانده‌اند — نوارِ نجاتِ مکمل؛ دیوار (protect)
# هرگز واردِ donor نمی‌شود.
# گاردِ «ساختار»: معیارِ «هرچه از میانه
# دور است = جوهر» رویِ بلوک‌هایِ نیمه‌شفاف/قاب‌دار
# فاجعه می‌ساخت: قابِ سفیدِ باکس (روشنِ واضح مقابلِ
# میانهٔ تیره) و بافتِ پشتِ شیشه هر دو «جوهر» خوانده
# می‌شدند → ماسکِ donor = کلِ بلوک + قاب → LaMa کلِ
# باکس را بازسازی می‌کرد (لبهٔ دوبلِ قاب + لکهٔ تخت +
# «MONSTERS..»). پس: فقط «قطعه‌هایِ حرفیِ» فشرده —
# نه خط‌هایِ بلند/حلقه‌ای — و اگر باز هم بیش از
# ~۴۵٪ بلوک شد، یعنی معیار جوهر نیست، بافت است →
# کلِ نجاتِ جوهر رد می‌شود (فقط نوارها می‌مانند).
                        try:
                            _oc = image[_zy0:_zy1, _zx0:_zx1]
                            _g = cv2.cvtColor(_oc, cv2.COLOR_BGR2GRAY)
                            _med = float(np.median(_g))
# فقط «بقایایِ پرکنتراست»: بازماندهٔ
# واقعیِ جوهر (آپاستروف/خطِ جاافتاده) در برابر
# زمینهٔ بلوک خیلی دور است (≥۹۰). بافتِ پشتِ
# شیشه/گرادیانِ پلاک در همین بازه نیست → دیگر
# واردِ ماسکِ LaMa نمی‌شود و لکهٔ سایه نمی‌سازد.
                            _ink = ((_g < _med - 90.0)
                                      | (_g > _med + 90.0))
                            _ink_u8 = _ink.astype(np.uint8)
                            _nz = int(_ink_u8.sum())
                            _blk_area = max(1, (_zx1 - _zx0) * (_zy1 - _zy0))
                            _wall_ok = True
                            if _nz >= max(400, int(0.45 * _blk_area)):
# بافت/گرادیان — نه جوهر؛ کلِ نجات رد.
                                _wall_ok = False
                            else:
                                try:
                                    _n, _lb, _stt, _ = \
                                        cv2.connectedComponentsWithStats(
                                            _ink_u8, 8)
                                    _okc = np.zeros_like(_ink_u8)
                                    for _i in range(1, _n):
                                        _cw = int(_stt[_i,
                                                          cv2.CC_STAT_WIDTH])
                                        _ch = int(_stt[_i,
                                                          cv2.CC_STAT_HEIGHT])
                                        _mx = max(_cw, _ch)
                                        _mn = max(1, min(_cw, _ch))
# خطِ بلندِ نازک = دیوار/قاب، نه حرف
                                        if _mx >= 64 and _mn <= max(
                                                12, int(0.09 * _mx)):
                                            continue
# حلقه/قاب: کادرِ بزرگ با پرشدگیِ کم
                                        _fa = _cw * _ch
                                        _px = int(_stt[_i,
                                                          cv2.CC_STAT_AREA])
                                        if _mx >= 96 and _fa > 0 and \
                                                _px / _fa < 0.38:
                                            continue
                                        _okc[_lb == _i] = 1
                                    _ink_u8 = _okc
                                except Exception:
                                    pass
                            if _wall_ok:
                                _ink = cv2.dilate(
                                    _ink_u8,
                                    np.ones((5, 5), np.uint8)) > 0
                                if _protect is not None \
                                        and _protect.shape == out.shape:
                                    _ink &= (_protect[_zy0:_zy1,
                                                        _zx0:_zx1] == 0)
                                _keep[_zy0:_zy1, _zx0:_zx1] |= _ink
                        except Exception:
                            pass
# جایگزینی: داخلِ بلوک فقط نوارها + جوهر می‌ماند
                        out[_zy0:_zy1, _zx0:_zx1] = np.where(
                            _keep[_zy0:_zy1, _zx0:_zx1], 255, 0
                        ).astype(out.dtype)
                    except Exception:
                        continue
            except Exception:
                pass
# روکشِ حاشیه‌نویسیِ ورودی (قابِ سبز + شستشویِ
# نیمه‌شفافِ up0822) هم در donor پاک میشود — بعد از جایگزینیِ
# بلوکهایِ متراکم میآید تا با np.where پاک نشود؛ دیوارها
# (protect) از قبل در نقشهٔ روکش حذف شدهاند.
            try:
                _anD = getattr(self, "_page_annotation_overlay", None)
                if _anD is not None and _anD.shape == out.shape:
                    _addD = (_anD > 0) & (out == 0)
                    if bool(_addD.any()):
                        out[_addD] = 255
                        _added += int(np.count_nonzero(_addD))
            except Exception:
                pass
# جعبه‌هایِ جستجو برایِ نجاتِ جوهرِ جا‌مانده (مثلِ قبل:
# ناحیه ∩ داخلِ حباب) — فقط دامنهٔ «جستجو»، نه افزودنِ ماسک.
            _stored = getattr(self, "_page_bubble_boxes", None) or []
            donor_boxes = []
            for region in (regions or []):
                try:
                    _dc = (getattr(region, "det_class", "") or "")
                    x, y, rw, rh = [int(v) for v in region.rect]
                    box = None
                    if _dc in ("bubble", "text_bubble"):
                        box = (x, y, x + rw, y + rh)
                    else:
                        _cx, _cy = x + rw // 2, y + rh // 2
                        _best = None
                        for _sb in _stored:
                            _sx1, _sy1, _sx2, _sy2, _sc = _sb
                            if _sc not in ("bubble", "text_bubble"):
                                continue
                            if (_sx2 - _sx1) < 24 or (_sy2 - _sy1) < 24:
                                continue
                            if not (_sx1 <= _cx <= _sx2
                                    and _sy1 <= _cy <= _sy2):
                                continue
                            _ov = (min(x + rw, _sx2) - max(x, _sx1)) * \
                                  (min(y + rh, _sy2) - max(y, _sy1))
                            if _ov < 0.55 * max(1, rw * rh):
                                continue
                            _area = (_sx2 - _sx1) * (_sy2 - _sy1)
                            if _area > 0.40 * h_img * w_img:
                                continue
                            if _best is None or _area < _best[0]:
                                _best = (_area, (_sx1, _sy1, _sx2, _sy2))
                        if _best is not None:
                            box = _best[1]
                    if box is None:
                        box = (x, y, x + rw, y + rh)
                    bx0, by0, bx1, by1 = box
                    bw, bh = bx1 - bx0, by1 - by0
                    _pad_b = int(np.clip(min(bw, bh) * 0.10, 4, 14))
# وبتون‌هایی که صفحه‌شان از وسطِ حباب شروع
# می‌شود (نمونهٔ واقعی: imgsrv5 chapter-264 صفحهٔ ۱ =
# نیم‌خطِ بریده در y=0): جعبهٔ حباب به لبهٔ تصویر
# می‌خورد و تکه‌متنِ بریده آن‌سویِ اینستِ ۴-۱۴px پنهان
# می‌ماند → «متنِ قبلی جا می‌ماند». ضلعِ برخوردی با
# لبهٔ تصویر اینست نمی‌گیرد تا نجاتِ جوهرِ لبه ببیندش.
                    _e_top = by0 <= 1
                    _e_bot = by1 >= h_img - 1
                    _e_lft = bx0 <= 1
                    _e_rgt = bx1 >= w_img - 1
                    ix0 = bx0 if _e_lft else max(0, bx0 + _pad_b)
                    iy0 = by0 if _e_top else max(0, by0 + _pad_b)
                    ix1 = bx1 if _e_rgt else min(w_img, bx1 - _pad_b)
                    iy1 = by1 if _e_bot else min(h_img, by1 - _pad_b)
                    if ix1 - ix0 < 24 or iy1 - iy0 < 24:
                        continue
                    if not (out[iy0:iy1, ix0:ix1] > 0).any():
                        continue
                    donor_boxes.append((ix0, iy0, ix1, iy1))
# نجاتِ جوهرِ پوشش‌داده‌نشده — خطی که OCR ندیده
                    try:
                        _bands = self._uncovered_ink_bands(
                            image, (ix0, iy0, ix1, iy1), out)
                        if _bands is not None:
                            _b_n = int((_bands > 0).sum())
                            if _b_n:
                                out[_bands > 0] = 255
                                _added += _b_n
                    except Exception:
                        pass
                except Exception:
                    continue
            self._donor_skip_ids = set()
            self._donor_boxes = donor_boxes
            if getattr(self, "debug", False):
                try:
                    print(f"  [*]donor = فقط نوارِ متن + پد "
                          f"(+{_added}px) — کلِ حباب LaMa نمی‌شود"
                          f" | {len(donor_boxes)} جعبهٔ نجاتِ جوهر")
                except Exception:
                    pass
            return out
        except Exception:
            self._donor_skip_ids = set()
            self._donor_boxes = []
            return mask

    def _bubble_domain_local(self, bgr_crop: np.ndarray,
                             seed_mask: np.ndarray,
                             rect_box: Optional[tuple] = None
                             ) -> Optional[np.ndarray]:
        try:
            ch, cw = bgr_crop.shape[:2]
            zm = seed_mask > 0
            if ch < 16 or cw < 16 or not zm.any():
                return None
            hsv = cv2.cvtColor(bgr_crop, cv2.COLOR_BGR2HSV)
            S = hsv[..., 1].astype(np.float32)
            V = hsv[..., 2].astype(np.float32)
            s_med = float(np.median(S[zm]))
            v_med = float(np.median(V[zm]))
            base = ((np.abs(S - s_med) <= 55.0)
                    & (np.abs(V - v_med) <= 55.0)).astype(np.uint8)
            base = cv2.morphologyEx(base, cv2.MORPH_CLOSE,
                                    np.ones((3, 3), np.uint8))
            n, lab = cv2.connectedComponents(base, connectivity=4)
            seed_d = cv2.dilate(seed_mask,
                                np.ones((3, 3), np.uint8), iterations=2)
            labs = lab[seed_d > 0]
            labs = labs[labs > 0]
            if len(labs) == 0:
                return None
            vals, cnts = np.unique(labs, return_counts=True)
            comp = (lab == vals[int(np.argmax(cnts))]).astype(np.uint8) * 255
            if int(np.count_nonzero(comp)) < 0.10 * ch * cw:
                return None
            padc = cv2.copyMakeBorder(comp, 1, 1, 1, 1,
                                      cv2.BORDER_CONSTANT, value=0)
            ff = padc.copy()
            ffm = np.zeros((padc.shape[0] + 2, padc.shape[1] + 2), np.uint8)
            cv2.floodFill(ff, ffm, (0, 0), 255)
            filled = cv2.bitwise_or(padc, cv2.bitwise_not(ff))[1:-1, 1:-1]
            if float(np.count_nonzero(filled)) > 0.92 * ch * cw:
                return None
            if rect_box is not None:
                try:
                    _bx, _by, _bw, _bh = [int(v) for v in rect_box]
                    _ys, _xs = np.where(filled > 0)
                    if len(_ys):
                        _m = 14
                        if (_xs.min() < _bx - _m or _ys.min() < _by - _m
                                or _xs.max() > _bx + _bw + _m
                                or _ys.max() > _by + _bh + _m):
                            return None
                except Exception:
                    pass
            try:
                _ring = cv2.dilate(filled, np.ones((5, 5), np.uint8))
                _ring = (_ring > 0) & (filled == 0)
                if int(np.count_nonzero(_ring)) >= 30:
                    _rs = S[_ring]
                    _rv = V[_ring]
                    _edge = ((np.abs(_rs - s_med) > 35.0)
                             | (np.abs(_rv - v_med) > 35.0))
                    if float(_edge.mean()) < 0.45:
                        return None
            except Exception:
                pass
            filled = cv2.erode(filled, np.ones((3, 3), np.uint8), iterations=6)
            if int(np.count_nonzero(filled)) < 0.08 * ch * cw:
                return None
            return filled
        except Exception:
            return None

    def _fast_bubble_guard(self, image: np.ndarray, rm: np.ndarray,
                           region: "TextRegion", has_polys: bool) -> bool:
        try:
            h, w = image.shape[:2]
            x, y, rw, rh = [int(v) for v in region.rect]
            M = 34
            cx0, cy0 = max(0, x - M), max(0, y - M)
            cx1, cy1 = min(w, x + rw + M), min(h, y + rh + M)
            if cx1 - cx0 < 16 or cy1 - cy0 < 16:
                return True
            sub = rm[cy0:cy1, cx0:cx1]
            if not np.any(sub):
                return True
            gray = cv2.cvtColor(image[cy0:cy1, cx0:cx1], cv2.COLOR_BGR2GRAY)
            if not has_polys:
                try:
                    _dom = self._bubble_domain_local(
                        image[cy0:cy1, cx0:cx1], sub,
                        rect_box=(x - cx0, y - cy0, rw, rh))
                    if _dom is not None:
                        _rectm = np.zeros_like(sub)
                        _px0, _py0 = max(0, x - cx0 + 2), max(0, y - cy0 + 2)
                        _px1 = min(sub.shape[1], x - cx0 + rw - 2)
                        _py1 = min(sub.shape[0], y - cy0 + rh - 2)
                        if _px1 - _px0 >= 10 and _py1 - _py0 >= 10:
                            _rectm[_py0:_py1, _px0:_px1] = 255
                            _inter = cv2.bitwise_and(_dom, _rectm)
                            if cv2.countNonZero(_inter) >= 0.06 * rw * rh:
                                rm[cy0:cy1, cx0:cx1] = _inter
                                return True
                except Exception:
                    pass
                try:
                    _gm = np.zeros_like(sub)
                    _rx0, _ry0 = x - cx0 + 2, y - cy0 + 2
                    _rx1, _ry1 = x - cx0 + rw - 2, y - cy0 + rh - 2
                    if _rx1 - _rx0 >= 10 and _ry1 - _ry0 >= 10:
                        _rc = gray[_ry0:_ry1, _rx0:_rx1]
                        _rmed = float(np.median(_rc))
                        _dk = ((_rc < _rmed - 40.0).astype(np.uint8)) * 255
                        _nzg, _labg, _stg, _ = cv2.connectedComponentsWithStats(
                            _dk, 8)
                        _gh2, _gw2 = _dk.shape
                        _tot = 0
                        for _ci in range(1, _nzg):
                            _ca = int(_stg[_ci, cv2.CC_STAT_AREA])
                            if _ca < 12 or _ca > 0.25 * _gh2 * _gw2:
                                continue
                            _cxg = int(_stg[_ci, cv2.CC_STAT_LEFT])
                            _cyg = int(_stg[_ci, cv2.CC_STAT_TOP])
                            _cwg = int(_stg[_ci, cv2.CC_STAT_WIDTH])
                            _chg = int(_stg[_ci, cv2.CC_STAT_HEIGHT])
                            if _cxg <= 0 or _cyg <= 0 \
                                    or _cxg + _cwg >= _gw2 \
                                    or _cyg + _chg >= _gh2:
                                continue
                            if max(_cwg, _chg) > 3.2 * max(1, min(_cwg, _chg)):
                                continue
                            if _ca / float(max(1, _cwg * _chg)) < 0.25:
                                continue
                            _gm[_ry0 + _cyg:_ry0 + _cyg + _chg,
                                _rx0 + _cxg:_rx0 + _cxg + _cwg][
                                _labg[_cyg:_cyg + _chg,
                                      _cxg:_cxg + _cwg] == _ci] = 255
                            _tot += _ca
                        if _tot >= 30:
                            rm[cy0:cy1, cx0:cx1] = _gm
                            return True
                except Exception:
                    pass
                return False
            interior = self._bubble_domain_local(
                image[cy0:cy1, cx0:cx1], sub,
                rect_box=(x - cx0, y - cy0, rw, rh))
            if interior is not None and cv2.countNonZero(interior) > 0:
                n_sub = int(cv2.countNonZero(sub))
                clipped = cv2.bitwise_and(sub, interior)
                try:
                    _outside = ((sub > 0) & (interior == 0)).astype(np.uint8)
                    if int(np.count_nonzero(_outside)) > 0:
                        _dn = cv2.dilate(interior,
                                         np.ones((7, 7), np.uint8)) > 0
                        _onz, _olab, _ost, _ = cv2.connectedComponentsWithStats(
                            _outside, 8)
                        _oh, _ow = _outside.shape
                        for _oi in range(1, _onz):
                            _oa = int(_ost[_oi, cv2.CC_STAT_AREA])
                            _ox = int(_ost[_oi, cv2.CC_STAT_LEFT])
                            _oy = int(_ost[_oi, cv2.CC_STAT_TOP])
                            _owd = int(_ost[_oi, cv2.CC_STAT_WIDTH])
                            _oht = int(_ost[_oi, cv2.CC_STAT_HEIGHT])
                            _comp = (_olab[_oy:_oy + _oht,
                                           _ox:_ox + _owd] == _oi)
                            if not bool(_dn[_oy:_oy + _oht,
                                            _ox:_ox + _owd][_comp].any()):
                                continue
                            _big = (_owd >= 0.40 * _ow
                                    or _oht >= 0.40 * _oh)
                            _hollow = (_oa / float(max(1, _owd * _oht))) < 0.30
                            if _big or _hollow:
                                clipped[_oy:_oy + _oht,
                                        _ox:_ox + _owd][_comp] = 0
                except Exception:
                    pass
                if n_sub > 0 and cv2.countNonZero(clipped) >= 0.45 * n_sub:
                    sub = clipped
                rm[cy0:cy1, cx0:cx1] = sub
                return True
            try:
                _raw = []
                _tall_n = 0
                _wide_n = 0
                _ws = []
                for _p in (getattr(region, "ocr_polys", None) or []):
                    _pp = np.asarray(_p, dtype=np.float32).reshape(-1, 2)
                    if _pp.shape[0] < 3:
                        continue
                    _raw.append(np.rint(_pp).astype(np.int32))
                    _pw = float(_pp[:, 0].max() - _pp[:, 0].min())
                    _ph = float(_pp[:, 1].max() - _pp[:, 1].min())
                    _ws.append(max(8.0, _pw))
                    if _ph >= 1.3 * _pw and _ph >= 18.0:
                        _tall_n += 1
                    if _pw >= 1.3 * _ph and _pw >= 18.0:
                        _wide_n += 1
                if _raw:
                    _tight = np.zeros_like(sub)
                    _off = np.array([cx0, cy0], dtype=np.int32)
                    cv2.fillPoly(_tight, [p - _off for p in _raw], 255)
                    _tight = cv2.dilate(_tight, np.ones((3, 3), np.uint8))
                    if cv2.countNonZero(_tight) > 0 and \
                            cv2.countNonZero(_tight) >= 0.25 * max(
                                1, cv2.countNonZero(sub)):
                        rm[cy0:cy1, cx0:cx1] = _tight
                        if _tall_n >= 2 and _tall_n >= _wide_n:
                            try:
                                _tx0 = min(int(p[:, 0].min()) for p in _raw)
                                _ty0 = min(int(p[:, 1].min()) for p in _raw)
                                _tx1 = max(int(p[:, 0].max()) for p in _raw)
                                _ty1 = max(int(p[:, 1].max()) for p in _raw)
                                manga_cls = type(self)
                                manga_cls._absorb_block_neighbors(
                                    image, rm,
                                    (_tx0 - 4, _ty0 - 4,
                                     _tx1 - _tx0 + 8, _ty1 - _ty0 + 8),
                                    levels=2, band=100)
                            except Exception:
                                pass
                        return True
            except Exception:
                pass
            return True
        except Exception:
            return True

    def _limit_mask_to_bubble(self, image: np.ndarray, rm: np.ndarray,
                              region: "TextRegion") -> np.ndarray:
        """ — بازنویسیِ کامل — درخواستِ کاربر: «حباب متن نباید بپاکه
        و لگه نباید بزاره، متن نباید بمونه».
        قانونِ طلایی: این تابع فقط «کوچک» می‌کند، هرگز بزرگ نمی‌کند.
        ۱) اگر حبابِ واقعی (جزیرهٔ بسته با دیوارِ تیره) دورِ متن پیدا شود →
           ماسک به داخلِ حباب گیرده می‌شود (کلیپ)؛ دیوارِ حباب و بیرونِ آن
           هرگز پاک نمی‌شود و متنِ نزدیکِ دیوار هم داخلِ ماسک می‌ماند.
        ۲) اگر ماسک از قبل کاملاً داخلِ حباب است → دست نمی‌خورد.
        ۳) اگر حباب معتبر نبود → ماسک با پالی‌های تنگِ OCR «تقاطع» می‌شود —
           بلوکِ مستطیلی جمع می‌شود ولی هیچ پیکسلی بیرونِ ماسکِ قبلی اضافه
           نمی‌شود (نسخهٔ این‌جا ماسک را با پالی‌های 1.18x «جایگزین»
           می‌کرد و از دیوارِ حباب رد می‌شد → لگهٔ سیاه/سفید و حبابِ پاک‌شده)."""
        try:
            ys, xs = np.nonzero(rm)
            if xs.size == 0:
                return rm
            h, w = image.shape[:2]
            n_orig = int(xs.size)
            M = 26
            x0 = max(0, int(xs.min()) - M)
            y0 = max(0, int(ys.min()) - M)
            x1 = min(w, int(xs.max()) + 1 + M)
            y1 = min(h, int(ys.max()) + 1 + M)
            if x1 - x0 < 12 or y1 - y0 < 12:
                return rm
            sub = rm[y0:y1, x0:x1]
            gray = cv2.cvtColor(image[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
            interior = self._bubble_interior_mask(gray, sub, erode_iters=1)
            try:
                _di = os.environ.get("MANGA_DUMP_INTERIOR")
                if _di and interior is not None:
                    _full_i = np.zeros(image.shape[:2], dtype=np.uint8)
                    _full_i[y0:y1, x0:x1] = interior
                    cv2.imwrite(_di, _full_i)
                    print(f"  [🔍] interior dumped: px={int(cv2.countNonZero(interior))} med={float(np.median(gray[interior > 0])):.0f}")
            except Exception:
                pass
            if interior is not None and int(cv2.countNonZero(interior)) > 0:
                ch, cw = gray.shape[:2]
                _area = float(ch * cw)
                _fa = float(cv2.countNonZero(interior))
                if 0.10 * _area <= _fa <= 0.94 * _area:
# اعتبارسنجیِ «دیوار» — حلقهٔ دورِ اینتریور باید
# به‌طورِ معناداری تیره‌تر از خودِ اینتریور باشد (خطِ حباب/
# کادر). چکِ قبلیِ «تعدادِ لبه‌های کراپ که اینتریور لمس
# می‌کند ≤ ۱» حباب‌های واقعی را وقتی متن به لبهٔ حباب
# نزدیک بود (کراپ تنگ) رد می‌کرد و مسیرِ جایگزینیِ
# بزرگ‌کننده فعال می‌شد.
                    _wall_ok = False
                    try:
                        _ring = cv2.dilate(interior, np.ones((5, 5), np.uint8))
                        _ring = (_ring > 0) & (interior == 0)
                        _n_ring = int(np.count_nonzero(_ring))
                        if _n_ring >= 30:
                            _g_in = float(np.median(gray[interior > 0]))
                            _g_rg = float(np.median(gray[_ring]))
# دیوار باید واقعاً تیره باشد (خطِ
# حباب/کادر) — سایهٔ ملایمِ هنر کافی نیست
                            _wall_ok = (_g_rg <= _g_in - 40.0)
                        else:
                            _wall_ok = True
                    except Exception:
                        _wall_ok = True
                    if _wall_ok:
                        _out = ((sub > 0) & (interior == 0))
                        _n_out = int(np.count_nonzero(_out))
                        if _n_out == 0:
                            return rm
                        clipped = cv2.bitwise_and(sub, interior)
                        _n_clip = int(cv2.countNonZero(clipped))
# 0.75 — کلیپ فقط برای «سرریزِ کم»؛ اگر
# بیش از ~۲۵٪ ماسک بیرونِ «حباب» است، این یک جزیرهٔ
# کاذب روی هنر است (متنِ روشن روی زمینهٔ تیره) و
# کلیپ، متنِ واقعی را قربانی می‌کند
                        if _n_clip >= max(150, 0.75 * n_orig) and _n_clip < n_orig:
                            rm[y0:y1, x0:x1] = clipped
                            return rm
# : مسیرِ «جایگزینی با پالی‌هایِ تنگ» حذف شد ----
# این مسیر ماسکِ حاصل از جذبِ جوهر (که کلِ ستون/بلوکِ متن را
# دارد) را با پالی‌هایِ ناقصِ OCR قطعه‌قطعه می‌کرد و متنِ
# باقی‌مانده (شبح/متنِ ناپاک‌شده) می‌ساخت — مثالِ واقعی:
# region#1 در صفحهٔ چینی 2487→676 می‌شد و «木濑！电影很有趣»
# ناپاک می‌ماند. امنیتِ دیوارِ حباب با کلیپِ اینتریور (بالا)
# و پرکردنِ اختصاصیِ محفظه تأمین می‌شود.
            return rm
        except Exception:
            return rm

    def _pad_dilate_wall_safe(self, rm: np.ndarray, image: np.ndarray,
                              region: "TextRegion",
                              pad_k) -> np.ndarray:
        """ — دیلیشنِ ماسک + گیردهِ دوباره به داخلِ حباب (فقطِ
        اندروید — ). دیکدِ مرجع: اپِ مرجع هیچ مدلِ inpaintی ندارد و فقط پالیِ تنگِ
        خطهایِ OCR را با رنگِ زمینه پر میکند — دیوارِ حباب هرگز لمس
        نمیشود. نزدیکترین معادلِ امنِ همین‌جا: پدِ ماسکِ اندروید (۸px —
        درسِ برایِ دورخطِ ضخیمِ حبابهایِ زرد) بعد از گیردهِ حباب
        اعمال میشود و میتواند ۸ پیکسل از دیوار را ببلعد؛ پس بعدِ دیلیشن
        دوباره به داخلِ حباب گیرده میکنیم. _limit_mask_to_bubble فقط
        کوچک میکند و فقط با «حبابِ واقعیِ تاییدشده» (دیوارِ تیرهٔ +۴۰
        گری + گیتِ سرریزِ ۰.۷۵) کلیپ میکند → متنِ آزادِ بیرونِ حباب
        دستنخورده میماند و درسِ (پوششِ دورخطِ داخلِ حباب) هم
        سرِ جایش است. PC/لینوکس هرگز این مسیر را نمیرود (گیتِ اندرویدِ
        MANGA_MASK_WALL_RECLIP) — رفتارِ PC بیت‌به‌بیتِ قبلی."""
        if pad_k is not None:
            rm = cv2.dilate(rm, pad_k)
        try:
            if _android_gate("MANGA_MASK_WALL_RECLIP"):
                rm = self._limit_mask_to_bubble(image, rm, region)
        except Exception:
            pass
        return rm

    def _ink_is_light(self, image: np.ndarray,
                      ink: Optional[np.ndarray]) -> bool:
        """ — قطبیتِ متن: جوهرِ گلیف‌ها به‌وضوح روشن‌تر از زمینهٔ
        چسبیده است؟ (متنِ سفید/کرم روی بنر/کارتِ تیره — Crimson Dragon،
        بنرهایِ هدر). برای گاردهایِ کارو و اجبارِ LaMa."""
        try:
            if ink is None or not np.any(ink):
                return False
            g = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            im = ink > 0
            if int(np.count_nonzero(im)) < 40:
                return False
            t_ink = float(np.median(g[im]))
            ring = (cv2.dilate(ink, np.ones((9, 9), np.uint8)) > 0) & (~im)
            if int(np.count_nonzero(ring)) < 40:
                return False
            t_out = float(np.median(g[ring]))
            return t_ink > t_out + 45.0
        except Exception:
            return False

    def _block_bg_stats(self, image: np.ndarray, rect,
                        ink_b: Optional[np.ndarray]):
        """ — آمارِ «زمینهٔ بیرونِ جوهر» داخلِ مستطیلِ بلوک.

        «متنِ روشن روی محفظهٔ تیره» () فقط وقتی مستطیلِ کاملِ
        بلوک را برای LaMa می‌خواهد که زمینه یکدست باشد (بنرِ صاف). روی
        گرادیان/برف‌نوی/نقش‌ونگار (412e9e: EXEC + GREEN MOON — std≈۶۷/۵۸
        در برابرِ باندِ واقعیِ img4 با std≈۱۸) حفرهٔ بزرگِ LaMa پرِ تختِ
        بی‌بافت می‌سازد. خروجی: (med, std, bright_frac) یا None."""
        try:
            h, w = image.shape[:2]
            bx, by, bw, bh = [int(v) for v in rect]
            x0, y0 = max(0, bx), max(0, by)
            x1, y1 = min(w, bx + bw), min(h, by + bh)
            if x1 - x0 < 24 or y1 - y0 < 14:
                return None
            g = cv2.cvtColor(image[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
            if ink_b is None or ink_b.shape != image.shape[:2] \
                    or not np.any(ink_b):
                return None
            ink = cv2.dilate((ink_b[y0:y1, x0:x1] > 0).astype(np.uint8),
                             np.ones((9, 9), np.uint8)) > 0
            bg = (~ink)
            if int(np.count_nonzero(bg)) < 200:
                return None
            vals = g[bg].astype(np.float32)
            med = float(np.median(vals))
            std = float(vals.std())
            bright = float((vals > 170.0).mean())
            return (med, std, bright)
        except Exception:
            return None

    def _carve_structural_walls(self, image: np.ndarray, rm: np.ndarray,
                                region: "TextRegion",
                                polys_raw: list,
                                ink_mask: Optional[np.ndarray] = None) -> np.ndarray:
        """ — باگِ «حبابِ پاک‌شده» (صفحهٔ LIKE A TIME BOMB — ناحیهٔ
        «YOU'RE LEAVING THE COMPANY?»): ماسکِ بلوکِ متن تقریباً به‌اندازهٔ
        خودِ حباب می‌شود و تا دیوارِ حباب/کادرِ پنل پیش می‌رود؛ پرکننده
        (flat/TELEA/LaMa) دیوار را هم با رنگِ زمینه می‌پوشاند → کلِ بادکنک
        نابود می‌شود و «تمیز درآمده» ولی حباب دیگر وجود ندارد.
        این تابع مؤلفه‌هایِ تیرهٔ «ساختاری» (دیوارِ حباب، کادرِ پنل —
        کامپوننت‌هایِ بزرگ/کشیده/لبه‌به‌لبه) را از ماسک بیرون می‌کشد تا
        پرکننده هرگز دیوار را نقاشی نکند. گلیف‌هایِ متن (کامپوننت‌هایِ
        کوچکِ داخلِ ناحیهٔ OCR) دست‌نخورده می‌مانند."""
        try:
            h, w = image.shape[:2]
            ys, xs = np.nonzero(rm)
            if xs.size == 0:
                return rm
# متنِ روشن روی محفظهٔ تیره: «کامپوننتِ تیرهٔ ساختاری»
# اینجا خودِ زمینه است نه دیوار → کارو ماسک را پنیرِ سوری می‌کند
# (حروفِ سفید سالم می‌مانند = «متنِ قبلی سرِ جایش»). رها کن.
            if ink_mask is not None and self._ink_is_light(image, ink_mask):
                return rm
            M = 24
            x0 = max(0, int(xs.min()) - M)
            y0 = max(0, int(ys.min()) - M)
            x1 = min(w, int(xs.max()) + 1 + M)
            y1 = min(h, int(ys.max()) + 1 + M)
            if x1 - x0 < 24 or y1 - y0 < 24:
                return rm
            sub = rm[y0:y1, x0:x1]
            if not np.any(sub):
                return rm
            gray = cv2.cvtColor(image[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
            ch_, cw_ = gray.shape
            if ch_ < 24 or cw_ < 24:
                return rm
            dark = (gray < 120).astype(np.uint8) * 255
            dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE,
                                    np.ones((3, 3), np.uint8))
            n, lab, st, _ = cv2.connectedComponentsWithStats(dark, 8)
# ناحیهٔ متنِ OCR — برای اینکه گلیفِ چسبیده به دیوار قربانی نشود
            polyf = None
            try:
                _pts = []
                for p in (polys_raw or []):
                    try:
                        pp = np.asarray(p, dtype=np.float32).reshape(-1, 2)
                    except Exception:
                        continue
                    if pp.shape[0] >= 3:
                        _pts.append(pp)
                if _pts:
                    polyf = np.zeros_like(dark)
                    _off = np.array([x0, y0], dtype=np.int32)
                    for pp in _pts:
                        cv2.fillPoly(
                            polyf,
                            [np.rint(pp).astype(np.int32) - _off], 255)
                    polyf = cv2.dilate(polyf, np.ones((5, 5), np.uint8))
            except Exception:
                polyf = None
# گاردِ قطبیت (همه‌جایی): متنِ روشن روی محفظهٔ تیره
# (کارتِ عنوانِ Crimson Dragon، بنرهایِ هدر) — اینجا «کامپوننتِ
# تیرهٔ ساختاری» خودِ زمینه است نه دیوار؛ کارو آن را از ماسک
# بیرون می‌کشد = ماسکِ پنیرِ سوری = حروفِ قدیمی سالم می‌مانند.
# تشخیصِ قطبیت: فاصلهٔ صدکِ ۹۰ِ پیکسل‌هایِ داخلِ پالی‌ها تا
# میانهٔ زمینهٔ چسبیده، بیشتر از فاصلهٔ صدکِ ۱۰ باشد → جوهرِ
# روشن → کارو ممنوع.
            if polyf is not None and np.any(polyf):
                try:
                    _pg = gray[polyf > 0].astype(np.float32)
                    _rg2 = ((cv2.dilate(polyf, np.ones((21, 21), np.uint8)) > 0)
                            & (polyf == 0))
                    if _pg.size >= 60 and int(np.count_nonzero(_rg2)) >= 40:
                        _tout2 = float(np.median(gray[_rg2]))
                        _p90 = float(np.percentile(_pg, 90))
                        _p10 = float(np.percentile(_pg, 10))
                        if (_p90 - _tout2) > (_tout2 - _p10):
                            return rm
                except Exception:
                    pass
            carve = np.zeros_like(dark)
            n_carved = 0
            for i in range(1, n):
                a = int(st[i, cv2.CC_STAT_AREA])
                if a < 60:
                    continue
                bx = int(st[i, cv2.CC_STAT_LEFT])
                by = int(st[i, cv2.CC_STAT_TOP])
                bw_ = int(st[i, cv2.CC_STAT_WIDTH])
                bh_ = int(st[i, cv2.CC_STAT_HEIGHT])
                comp = np.zeros_like(dark, dtype=bool)
                comp[by:by + bh_, bx:bx + bw_][
                    lab[by:by + bh_, bx:bx + bw_] == i] = True
                touches = (bx == 0 or by == 0
                           or bx + bw_ >= cw_ or by + bh_ >= ch_)
                out_of_mask = int(np.count_nonzero(comp & (sub == 0)))
                structural = (
                    touches
                    or bw_ >= 0.55 * cw_ or bh_ >= 0.55 * ch_
                    or out_of_mask >= max(120, 0.30 * a))
                if not structural:
                    continue
                if polyf is not None:
                    on_poly = int(np.count_nonzero(comp & (polyf > 0)))
                    if on_poly > 0.45 * float(a):
                        continue  # بیشترِ این کامپوننت متن است، نه دیوار
                    _part = comp & (polyf == 0)
                else:
                    _part = comp
                _pa = int(np.count_nonzero(_part))
                if _pa < 40:
                    continue
                carve[_part] = 255
                n_carved += 1
            if n_carved == 0 or not np.any(carve):
                return rm
            carve = cv2.dilate(carve, np.ones((3, 3), np.uint8))
            n_sub = int(np.count_nonzero(sub))
            left = int(np.count_nonzero((sub > 0) & (carve == 0)))
            if n_sub > 0 and left < max(150, 0.30 * n_sub):
                return rm  # کارو بیش از حد بزرگ می‌شد → رها کن
            out = ((sub > 0) & (carve == 0)).astype(np.uint8) * 255
            rm[y0:y1, x0:x1] = out
            return rm
        except Exception:
            return rm

    def _free_text_tight_ok(self, image: np.ndarray, rect_mask: np.ndarray,
                            ink: np.ndarray, polys_raw: list) -> bool:
        """ — متنِ آزاد روی زمینهٔ هنری/گرادیانی (بدونِ حباب): نمونهٔ
        واقعی «SINCE WHEN WERE WE FRIENDS?» — ماسکِ مستطیلی روی گرادیانِ
        دیوار با یک رنگِ تخت پر می‌شود → لکهٔ بژِ واضح. ماسکِ جوهریِ تنگ
        (فقط گلیف‌ها) روی گرادیان تقریباً نامرئی است. شرط‌ها: حبابِ معتبر
        دورِ متن وجود ندارد + جوهر پوششِ کافی روی پالی‌ها دارد + جوهر
        به‌وضوح تیره‌ترِ زمینهٔ چسبیده است (متنِ تیره روی زمینهٔ روشن).
         — گیتِ بافت: فقط روی زمینهٔ «صاف/گرادیانی» (دیوارِ رنگی
        کاغذ) تنگ می‌کنیم. لاگِ 9.jpg کاربر: پاراگراف‌های روی «عکس» (حصار/
        درخت/چوب/صورت) با ماسکِ تنگ فقط استوکِ تیرهٔ گلیف را می‌گرفتند و
        هالهٔ خاکستریِ Anti-Alias دورِ حروف (سطح ~med−۵۵ تا med) باقی
        می‌ماند → «متنِ قبلی جا گذاشته». LaMa روی عکس با مستطیلِ کامل
        زمینه را عالی بازسازی می‌کند (خروجیِ تأیید) → زمینهٔ
        بافت‌دار = مستطیل (مسیرِ قبلی)، زمینهٔ صاف = تنگ."""
        try:
            ys, xs = np.nonzero(rect_mask)
            if xs.size == 0:
                return False
            h, w = image.shape[:2]
            M = 26
            x0 = max(0, int(xs.min()) - M)
            y0 = max(0, int(ys.min()) - M)
            x1 = min(w, int(xs.max()) + 1 + M)
            y1 = min(h, int(ys.max()) + 1 + M)
            if x1 - x0 < 24 or y1 - y0 < 24:
                return False
            sub = rect_mask[y0:y1, x0:x1]
            if not np.any(sub):
                return False
            gray = cv2.cvtColor(image[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
            if self._bubble_interior_mask(gray, sub, erode_iters=1) is not None:
                return False  # داخلِ حباب است → مسیرِ حباب بهتر است
            off = np.array([x0, y0], dtype=np.int32)
            polyf = np.zeros((y1 - y0, x1 - x0), dtype=np.uint8)
            npoly = 0
            for pp in (polys_raw or []):
                try:
                    q = np.rint(np.asarray(pp, dtype=np.float32)).astype(
                        np.int32) - off
                except Exception:
                    continue
                if q.shape[0] < 3:
                    continue
                cv2.fillPoly(polyf, [q], 255)
                npoly += 1
            if npoly == 0 or int(cv2.countNonZero(polyf)) < 120:
                return False
            inkc = None
            try:
                inkc = ink[y0:y1, x0:x1] > 0
            except Exception:
                return False
            n_poly = int(cv2.countNonZero(polyf))
            cov = float(np.count_nonzero(inkc & (polyf > 0))) / float(
                max(1, n_poly))
            if cov < 0.28 or cov > 0.85:
                return False
            ink_px = gray[inkc & (polyf > 0)]
            if ink_px.size < 60:
                return False
            t_ink = float(np.median(ink_px))
            ring = ((cv2.dilate(polyf, np.ones((7, 7), np.uint8)) > 0)
                    & (polyf == 0) & (~inkc))
            if int(np.count_nonzero(ring)) < 40:
                return False
            t_out = float(np.median(gray[ring]))
            if t_ink > t_out - 55.0:
                return False
# گیتِ بافتِ زمینه — هالهٔ دورِ گلیف فقط روی زمینهٔ
# صاف توسط پرکننده/LaMaِ تنگ پوشش داده می‌شود؛ روی عکس/بافت
# مستطیلِ کامل برمی‌گردیم تا LaMa کلِ زمینه را بازسازی کند
            try:
                _ring_d = cv2.dilate(polyf, np.ones((21, 21), np.uint8))
                _ring_band = ((_ring_d > 0) & (polyf == 0))
                if int(np.count_nonzero(_ring_band)) >= 60:
                    _rg = gray[_ring_band].astype(np.float32)
                    _lap = np.abs(cv2.Laplacian(gray, cv2.CV_32F))
                    _lap_band = float(np.mean(_lap[_ring_band]))
                    if float(np.std(_rg)) > 17.0 or _lap_band > 5.0:
                        return False  # زمینهٔ بافت‌دار → مستطیل امن‌تر است
            except Exception:
                pass
            return True
        except Exception:
            return False

    def _ink_tight_ok(self, image: np.ndarray, rect_mask: np.ndarray,
                      ink: np.ndarray, polys_raw: list) -> bool:
        """ — تشخیصِ «متن داخلِ محفظهٔ باکنتراست» (مثلاً متنِ سفید روی
        بنرِ سیاه که رنگِ متن با صفحهٔ بیرون یکی است). در این حالت مستطیلِ
        بلوک، زمینهٔ تیرهٔ بینِ حروف را هم قورت می‌دهد و پرکننده با رنگِ
        صفحه (روشن) آن را می‌پوشاند → لگهٔ سفید روی بنر. فقط در همین حالت
        ماسکِ جوهریِ تنگ جای مستطیل را می‌گیرد؛ بقیهٔ حالت‌ها مستطیل
        بی‌خطر است و مثل قبل می‌ماند."""
        try:
            ys, xs = np.nonzero(rect_mask)
            if xs.size == 0:
                return False
            h, w = image.shape[:2]
            x0, y0 = int(xs.min()), int(ys.min())
            x1, y1 = int(xs.max()) + 1, int(ys.max()) + 1
            g = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            sub_ink = ink[y0:y1, x0:x1] > 0
            if int(sub_ink.sum()) < 80:
                return False
            off = np.array([x0, y0], dtype=np.int32)
            polyf = np.zeros((y1 - y0, x1 - x0), dtype=np.uint8)
            for pp in polys_raw:
                q = np.rint(np.asarray(pp, dtype=np.float32)).astype(np.int32) - off
                cv2.fillPoly(polyf, [q], 255)
            n_poly = int(cv2.countNonZero(polyf))
            if n_poly < 100:
                return False
            _core = sub_ink & (polyf > 0)
            _cov = float(np.count_nonzero(_core)) / float(n_poly)
            if _cov < 0.22:
                return False
            _ink_px = g[y0:y1, x0:x1][_core]
            if _ink_px.size < 30:
                return False
            t_ink = float(np.median(_ink_px))
            _rx0, _ry0 = max(0, x0 - 8), max(0, y0 - 8)
            _rx1, _ry1 = min(w, x1 + 8), min(h, y1 + 8)
            _ring = np.ones((_ry1 - _ry0, _rx1 - _rx0), dtype=bool)
            _ring[(y0 - _ry0):(y1 - _ry0), (x0 - _rx0):(x1 - _rx0)] = False
            _ring &= (ink[_ry0:_ry1, _rx0:_rx1] == 0)
            if int(_ring.sum()) < 40:
                return False
            t_out = float(np.median(g[_ry0:_ry1, _rx0:_rx1][_ring]))
            return abs(t_ink - t_out) <= 40.0
        except Exception:
            return False

    def _enclosure_tight_mask(self, image: np.ndarray, polys_raw: list,
                              rect: Optional[Tuple[int, int, int, int]] = None
                              ) -> Optional[np.ndarray]:
        """ — متن روی «محفظهٔ تیرهٔ یکدست» (بنرِ سیاهِ هدر، کادرِ
        تیره، حبابِ سیاه): ماسکِ جوهریِ تنگ می‌سازد. مستطیلِ بلوک در این
        حالت زمینهٔ تیرهٔ بینِ حروف را می‌بلعد و پرکننده با رنگِ صفحهٔ
        بیرون آن را روشن می‌کند (لگهٔ سفید / بنرِ разруш شده). فقط وقتی
        فعال است که زمینهٔ چسبیده به متن تیره، یکدست و باکنتراست با
        دورتر باشد — بقیهٔ حالت‌ها (حبابِ روشن) مسیرِ قبلی می‌روند.
        : اگر پالی‌هایِ OCR فقط پاری از rect را پوشش می‌دهند
        (تشخیصِ ناقص — مثلاً فقط «、» در یک ستونِ متن) این مسیر فعال
        نمی‌شود تا بقیهٔ متن بی‌ماسک نماند؛ مسیرِ معمولی با جذبِ جوهر
        کلِ ستون را می‌گیرد."""
        try:
            pts = []
            for p in (polys_raw or []):
                try:
                    pp = np.asarray(p, dtype=np.float32).reshape(-1, 2)
                except Exception:
                    continue
                if pp.shape[0] >= 3:
                    pts.append(pp)
            if not pts:
                return None
            if rect is not None:
                try:
                    _rx, _ry, _rw, _rh = [int(v) for v in rect]
                    if _rw > 4 and _rh > 4:
                        _pf = 0.0
                        for pp in pts:
                            _pw = float(pp[:, 0].max() - pp[:, 0].min())
                            _ph = float(pp[:, 1].max() - pp[:, 1].min())
                            _pf += _pw * _ph
                        if _pf < 0.30 * float(_rw * _rh):
                            return None
                except Exception:
                    pass
            h, w = image.shape[:2]
            _all = np.concatenate(pts, axis=0)
            mg = 26
            wx0 = max(0, int(_all[:, 0].min()) - mg)
            wy0 = max(0, int(_all[:, 1].min()) - mg)
            wx1 = min(w, int(_all[:, 0].max()) + 1 + mg)
            wy1 = min(h, int(_all[:, 1].max()) + 1 + mg)
            if wx1 - wx0 < 16 or wy1 - wy0 < 16:
                return None
            g = cv2.cvtColor(image[wy0:wy1, wx0:wx1], cv2.COLOR_BGR2GRAY)
            polyf = np.zeros(g.shape, dtype=np.uint8)
            off = np.array([wx0, wy0], dtype=np.int32)
            for pp in pts:
                q = np.rint(pp).astype(np.int32) - off
                cv2.fillPoly(polyf, [q], 255)
            if int(cv2.countNonZero(polyf)) < 120:
                return None
# (بازبینی): enclosure = «کامپوننتِ تیرهٔ یکدستی که متن
# روی آن نشسته و از متن بزرگ‌تر است» (بنرِ هدر، کادرِ تیره
# حبابِ سیاه). حلقهٔ آماریِ ساده روی بنرهای نازک (که متن تقریباً
# تمامِ ارتفاعش را گرفته) به لبهٔ بنر می‌خورد و می‌شکند.
            _ys, _xs = np.nonzero(polyf)
            px0, py0 = int(_xs.min()), int(_ys.min())
            px1, py1 = int(_xs.max()) + 1, int(_ys.max()) + 1
            pbw, pbh = px1 - px0, py1 - py0
            dark = (g < 120).astype(np.uint8)
            dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE,
                                    np.ones((3, 3), np.uint8))
            n_d, lab_d, st_d, _ = cv2.connectedComponentsWithStats(dark, 8)
            touch = cv2.dilate(polyf, np.ones((7, 7), np.uint8)) > 0
            best_id, best_a = 0, 0
            for i in range(1, n_d):
                if not bool((lab_d[touch] == i).any()):
                    continue
                _a = int(st_d[i, cv2.CC_STAT_AREA])
                if _a < 0.80 * float(pbw * pbh):
                    continue
                _cx = int(st_d[i, cv2.CC_STAT_LEFT])
                _cy = int(st_d[i, cv2.CC_STAT_TOP])
                _cw = int(st_d[i, cv2.CC_STAT_WIDTH])
                _ch = int(st_d[i, cv2.CC_STAT_HEIGHT])
                if not (_cx <= px0 + 2 and _cy <= py0 + 2
                        and _cx + _cw >= px1 - 2 and _cy + _ch >= py1 - 2):
                    continue
                if not (_cw > pbw + 8 or _ch > pbh + 8):
                    continue
# محفظهٔ واقعی (بنر/کادر/حبابِ سیاه) «توپُر» است
# شبکهٔ خطوطِ هنر و متنِ روی art پراکنده → رد شود وگرنه
# پرکننده روی هنر لکه می‌گذارد.
                if _a / float(max(1, _cw * _ch)) < 0.35:
                    continue
                if _a > best_a:
                    best_a, best_id = _a, i
            if best_id == 0:
                return None
            comp = (lab_d == best_id)
            t_near = float(np.median(g[comp]))
            if t_near > 130.0:
                return None
            zone = cv2.dilate(polyf, np.ones((5, 5), np.uint8))
            ink = ((np.abs(g.astype(np.float32) - t_near) > 45.0)
                   & (zone > 0)).astype(np.uint8) * 255
            ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE,
                                   np.ones((3, 3), np.uint8))
            n_i, lab_i, st_i, _ = cv2.connectedComponentsWithStats(ink, 8)
            keep = np.zeros_like(ink)
            for i in range(1, n_i):
                if int(st_i[i, cv2.CC_STAT_AREA]) >= 12:
                    keep[lab_i == i] = 255
            ink = keep
            n_ink = int(cv2.countNonZero(ink))
            n_pf = int(cv2.countNonZero(polyf))
            if n_ink < 60 or n_ink > 0.92 * n_pf:
                return None
            if float(np.count_nonzero(ink & (polyf > 0))) < 0.25 * n_pf:
                return None
            out = np.zeros((h, w), dtype=np.uint8)
            out[wy0:wy1, wx0:wx1] = cv2.dilate(
                ink, np.ones((3, 3), np.uint8), iterations=1)
# کلِ محفظهٔ تیره با «پر شدنِ حفره‌ها» (حروفِ روشن داخلِ
# comp سوراخ‌اند!) تا ماسکِ حالتِ LaMaِ کیفیت توپر باشد — نه پنیرِ
# سوری که حروفِ قدیمی را بیرون بگذارد (کارتِ عنوانِ Crimson Dragon)
            _crop_c = comp.astype(np.uint8) * 255
# stroke/glow رنگی دورِ حروف (RED MOON: حروفِ سفید
# با stroke قرمز روی texture آبی): enclosure فقط کامپوننتِ
# «تیره» را می‌گیرد و strokeِ رنگیِ وسطِ روشن جا می‌ماند →
# بقایای قرمز در خروجی. پیکسل‌هایِ رنگیِ «غیرِ پس‌زمینه»
# (فاصلهٔ hue از رنگِ اطرافِ متن) به محفظه اضافه می‌شوند.
            try:
                _hsv = cv2.cvtColor(image[wy0:wy1, wx0:wx1], cv2.COLOR_BGR2HSV)
                _hue = _hsv[:, :, 0].astype(np.float32)
                _sat = _hsv[:, :, 1]
                _near = cv2.dilate(polyf, np.ones((13, 13), np.uint8))
                _bg_m = ((_near > 0) & (polyf == 0) & (_sat > 60))
                if np.count_nonzero(_bg_m) >= 50:
                    _hue_bg = float(np.median(_hue[_bg_m]))
                    _dh = np.abs(_hue - _hue_bg)
                    _dh = np.minimum(_dh, 180.0 - _dh)
                    _colorful = (((_sat > 80) & (_dh > 40.0)
                                  & (_near > 0)).astype(np.uint8) * 255)
                    _colorful = cv2.morphologyEx(
                        _colorful, cv2.MORPH_CLOSE,
                        np.ones((5, 5), np.uint8))
                    _add = cv2.bitwise_and(
                        _colorful,
                        cv2.dilate(_crop_c, np.ones((15, 15), np.uint8)))
                    if int(cv2.countNonZero(_add)) >= 40:
                        _crop_c = cv2.bitwise_or(_crop_c, _add)
            except Exception:
                pass
            _ff = _crop_c.copy()
            _fm2 = np.zeros((_ff.shape[0] + 2, _ff.shape[1] + 2), np.uint8)
            cv2.floodFill(_ff, _fm2, (0, 0), 255)
            _holes = cv2.bitwise_not(_ff)
            _holes &= cv2.dilate(
                _crop_c, np.ones((25, 25), np.uint8))
            _enc_full = np.zeros((h, w), dtype=np.uint8)
            _enc_full[wy0:wy1, wx0:wx1] = _crop_c | _holes
            self._last_enclosure_full = _enc_full
            return out
        except Exception:
            return None

    def _white_bubble_tighten(self, image: np.ndarray, rm: np.ndarray,
                              ink: Optional[np.ndarray]) -> np.ndarray:
        """ — باگِ «حبابِ کلاً عوض شده / سیاه شده» (لاگِ گوشیِ کاربر:
        حبابِ «YOU'RE LEAVING THE COMPANY?» با مدلِ LaMa-Manga به یک صورتِ
        خاکستری تبدیل شد). ریشه: وقتی پالی‌هایِ OCR متراکم‌اند یا پالی نیست،
        ماسکِ مستطیلی + جذبِ جوهر تقریباً «کلِ داخلِ حباب» را می‌گیرد؛
        حفرهٔ بزرگِ داخلِ حباب به LaMa-Manga مدل را وادار می‌کند به‌جای
        بازسازیِ زمینهٔ سفید، «محتوای مانگایی» (صورت/بافتِ درخت) توهم بزند —
        گیتِ QC فعلی فقط fillِ تیره را رد می‌کند و fillِ قهوه‌ای/صورتِ روشن
        رد می‌شود.
        قانون: اگر ماسک ≥ ~۴۵٪ اینتریورِ یک حبابِ «سفیدِ یکدست» را بپوشاند،
        ماسک به جوهرِ تنگِ گلیف‌ها جمع می‌شود (حفرهٔ کوچک = بازسازیِ امنِ
        سفید بینِ حروف). فقط کوچک می‌کند؛ هرگز بزرگ نمی‌کند."""
        try:
            ys, xs = np.nonzero(rm)
            if xs.size == 0:
                return rm
            h, w = image.shape[:2]
            M = 30
            x0 = max(0, int(xs.min()) - M)
            y0 = max(0, int(ys.min()) - M)
            x1 = min(w, int(xs.max()) + 1 + M)
            y1 = min(h, int(ys.max()) + 1 + M)
            if x1 - x0 < 24 or y1 - y0 < 24:
                return rm
            sub = rm[y0:y1, x0:x1]
            gray = cv2.cvtColor(image[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
            interior = self._bubble_interior_mask(gray, sub, erode_iters=1)
            if interior is None or int(cv2.countNonZero(interior)) < 400:
                return rm
            _fa = float(cv2.countNonZero(interior))
            _med_in = float(np.median(gray[interior > 0]))
            if _med_in < 185.0:
                return rm  # حبابِ سفیدِ یکدست نیست (تیره/اسکرین‌تون) → دست نزن
# فقط «حبابِ واقعی». لاگِ 9.jpg: پاراگرافِ روی عکسِ
# (حصار/درخت/سکویِ بتنی) — ناحیهٔ روشنِ عکس «حبابِ سفید» خوانده
# می‌شد (med≥185) و ماسکِ ۱۸۰Kpxِ پاراگراف به جوهرِ ~۴Kpx جمع
# می‌شد → هالهٔ خاکستریِ متن می‌ماند. حبابِ واقعی دیوارِ تیرهٔ
# دورِ اینتریور دارد و اینتریورش یکنواخت است — همان دو گاردِ
# _bubble_interior_sweep؛ بدونِ دیوار (کاغذ/عکس) دست نزن.
            try:
                _int_e = cv2.erode(interior, np.ones((5, 5), np.uint8))
                _ne = int(cv2.countNonZero(_int_e))
                if _ne < 400:
                    return rm
                _med_e = float(np.median(gray[_int_e > 0]))
                _ring = (cv2.dilate(interior, np.ones((5, 5), np.uint8)) > 0) \
                    & (interior == 0)
# countNonZero روی bool exception می‌داد → tighten
# از همیشه بی‌صدا در همین گیت شکست می‌خورد!
                if int(np.count_nonzero(_ring)) < 30:
                    return rm
                if float(np.median(gray[_ring])) > _med_e - 40.0:
                    return rm  # دیوارِ تیره نیست (کاغذ/عکسِ روشنِ باز) → رد
                if float((gray[_int_e > 0] >= _med_e - 30.0).mean()) < 0.85:
                    return rm  # اینتریورِ ناهمگون (بافت/سایه) → حباب نیست
            except Exception:
                if os.environ.get("MANGA_GUARD_DBG"):
                    import traceback
                    print("      [tighten] wall-gate exc:", flush=True)
                    traceback.print_exc()
                return rm
            cov = float(np.count_nonzero((sub > 0) & (interior > 0))) / _fa
            if cov < 0.45:
                return rm  # حفره نسبت به حباب کوچک است → LaMa امن است
# ماسکِ تنگ: جوهرِ جذب‌شده (اگر هست) وگرنه پیکسل‌هایِ تیرهٔ داخلِ ناحیه
            tight = None
            if ink is not None and ink.shape == rm.shape:
                ink_c = ink[y0:y1, x0:x1]
                _nik = int(np.count_nonzero((ink_c > 0) & (interior > 0)))
                if _nik >= 120:
                    tight = ((ink_c > 0) & (interior > 0)).astype(np.uint8) * 255
                    tight = cv2.dilate(tight, np.ones((3, 3), np.uint8))
                    tight = cv2.bitwise_and(tight, interior)
            if tight is None or int(cv2.countNonZero(tight)) < 120:
                _base = cv2.dilate(sub, np.ones((9, 9), np.uint8))
                _base = (_base > 0) & (interior > 0)
                if int(np.count_nonzero(_base)) < 100:
                    return rm
                _t = _med_in - 60.0
                tight = ((gray < _t) & _base).astype(np.uint8) * 255
                tight = cv2.morphologyEx(tight, cv2.MORPH_CLOSE,
                                         np.ones((5, 5), np.uint8))
                tight = cv2.dilate(tight, np.ones((3, 3), np.uint8))
                tight = cv2.bitwise_and(tight, interior)
# اگر tightِ جوهرِ جذب‌شده عملاً هم‌اندازهٔ خودِ ماسک شد
# (پالی‌هایِ گشادِ OCR + جذبِ جوهر = تقریباً کلِ اینتریور)
# با tightِ «پیکسلِ تیره» جایگزین کن — هدفِ tighten دقیقاً همین
# است: ماسکِ کل-حباب = حفرهٔ بزرگ = توهمِ LaMa-Manga و بعدش
# گارد/سویپ مجبور به مداخلهٔ خطرناک می‌شوند (chapter-264/8:
# ماسکِ ۱۵۴Kpxِ بیضیِ کامل → حبابِ کامل پاک‌شده)
            if int(cv2.countNonZero(tight)) >= max(
                    120, int(0.85 * int(cv2.countNonZero(sub)))):
                _base = cv2.dilate(sub, np.ones((9, 9), np.uint8))
                _base = (_base > 0) & (interior > 0)
                _t = _med_in - 60.0
                _tk = ((gray < _t) & _base).astype(np.uint8) * 255
                _tk = cv2.morphologyEx(_tk, cv2.MORPH_CLOSE,
                                       np.ones((5, 5), np.uint8))
                _tk = cv2.dilate(_tk, np.ones((3, 3), np.uint8))
                _tk = cv2.bitwise_and(_tk, interior)
                if 120 <= int(cv2.countNonZero(_tk)) < int(
                        cv2.countNonZero(sub)):
                    tight = _tk
            if int(cv2.countNonZero(tight)) < 120:
                return rm
# نوارِ هاله — ماسکِ تنگ فقط استوکِ تیره را می‌گرفت و
# Anti-Aliasِ خاکستریِ دورِ حروف (روی کاغذِ سفید ~سطح med−۲۵..۶۰)
# باقی می‌ماند → شبحِ متن. پیکسل‌هایِ «کم‌تر از med−۲۵» در
# همسایگیِ ~۵px جوهر را هم بگیر (فقط داخلِ اینتریور) و CLOSE کن
# حفرهٔ بینِ خط‌ها همچنان بزرگ می‌ماند → خطرِ توهمُ تغییر نمی‌کند.
            try:
                _halo_t = _med_in - 25.0
                if _halo_t > 40.0:
                    _near = cv2.dilate(tight,
                                       np.ones((11, 11), np.uint8)) > 0
                    _halo = ((gray < _halo_t) & _near
                             & (interior > 0)).astype(np.uint8) * 255
                    _halo = cv2.morphologyEx(_halo, cv2.MORPH_CLOSE,
                                             np.ones((3, 3), np.uint8))
                    _tight2 = cv2.bitwise_or(tight, _halo)
                    _tight2 = cv2.bitwise_and(_tight2, interior)
# اگر نوارِ هاله ماسک را تا ~کلِ اینتریور باد کرد، رد
                    if (int(cv2.countNonZero(_tight2))
                            < 0.72 * int(cv2.countNonZero(interior))):
                        tight = _tight2
            except Exception:
                pass
            if int(cv2.countNonZero(tight)) >= int(cv2.countNonZero(sub)):
                return rm  # کوچک‌تر نشد → بی‌فایده
            out = np.zeros_like(rm)
            out[y0:y1, x0:x1] = tight
            return out
        except Exception:
            return rm

    @staticmethod
    def _group_polys_to_lines(polys_raw) -> list:
        """ — پالی‌های OCR را «خط به خط» گروه می‌کند (ایدهٔ کاربر:
        «متنِ دقیق اندازه بگیره، یک خط کامل یک خط کامل»).
        خروجی: باکسِ هر خط [(x0, y0, x1, y1), …] مرتب از بالا به پایین."""
        items = []
        for p in list(polys_raw or []):
            try:
                pp = np.asarray(p, dtype=np.float32).reshape(-1, 2)
            except Exception:
                continue
            if pp.shape[0] < 3:
                continue
            items.append([float(pp[:, 0].min()), float(pp[:, 1].min()),
                          float(pp[:, 0].max()), float(pp[:, 1].max())])
        if not items:
            return []
        items.sort(key=lambda b: (b[1], b[0]))
        lines = []
        for b in items:
            bh = max(1.0, b[3] - b[1])
            hit = None
            for ln in lines:
                oy0 = max(b[1], ln[1])
                oy1 = min(b[3], ln[3])
                ov = oy1 - oy0
                if ov > 0.45 * min(bh, ln[3] - ln[1]):
                    hit = ln
                    break
            if hit is not None:
                hit[0] = min(hit[0], b[0])
                hit[1] = min(hit[1], b[1])
                hit[2] = max(hit[2], b[2])
                hit[3] = max(hit[3], b[3])
            else:
                lines.append(list(b))
        lines.sort(key=lambda b: b[1])
        return lines

    def _line_strips_mask(self, image: np.ndarray, polys_raw: list,
                          region: "TextRegion") -> Optional[np.ndarray]:
        """ — ماسکِ «خط‌به‌خط» — پیاده‌سازیِ ایدهٔ دو-عکسیِ کاربر:
        «دو تا عکس شه؛ اولی همون ک متن کامل پاک میشه — به اندازهٔ همون متنِ
        استخراج‌شده برش شه خط به خط؛ بعد عکسِ دوم ک متنِ اصلی توش هست،
        خط به خط در جایِ دقیقِ خودش جایگزین بشه.»

        یعنی: به‌جایِ ماسکِ مستطیلیِ کلِ بلوک (که در حباب‌هایِ تنگ با
        snapِ `_text_block_box` تقریباً «کلِ حباب» می‌شود و LaMa حباب را
        می‌بلعد)، فقط «نوارِ هر خطِ متن» — دقیقاً به اندازهٔ جوهرِ همان خط
        که از عکسِ اصلی اندازه گرفته می‌شود — ماسک می‌شود:
          - فضایِ خالیِ بینِ خط‌ها هرگز واردِ ماسک نمی‌شود → حبابِ سفید
            بینِ خط‌ها دست‌نخورده می‌ماند.
          - دیوارِ حباب اصلاً نزدیکِ ماسک نیست → هیچ پرکننده‌ای آن را
            نمی‌بلعد → حباب سالم می‌ماند.
          - پچِ LaMa بسیار کوچک‌تر → سریع‌تر.
        خروجی: ماسکِ صفحه‌کامل (uint8) یا None برای فال‌بک به مسیرِ قدیمی."""
        try:
            h, w = image.shape[:2]
        except Exception:
            return None
# نواحیِ چرخیده (|angle| ≥ ۳°): نوارها در فضای
# همسطح‌شده (مسیرِ مشترکِ کامپوز). MANGA_ROT_STRIPS=0 = خاموش.
        try:
            _ang = float(getattr(region, "angle", 0.0) or 0.0)
        except Exception:
            _ang = 0.0
        if 3.0 <= abs(_ang) <= 45.0 \
                and os.environ.get("MANGA_ROT_STRIPS", "1") != "0":
            try:
                _rot = self._rotated_region_strips(
                    image, polys_raw, _ang)
            except Exception:
                _rot = None
            if _rot is not None:
                _m = _rot[0]
                _a = int(cv2.countNonZero(_m))
                try:
                    _rw = float(region.rect[2])
                    _rh = float(region.rect[3])
                except Exception:
                    _rw = float(w)
                    _rh = float(h)
                if 150 <= _a <= 0.95 * max(1.0, _rw * _rh):
                    return _m
# بیرونِ دامنه → مسیرِ عادیِ محور-تراز
        lines = MangaTranslator._group_polys_to_lines(polys_raw)
        if not lines:
            return None
        try:
            rw, rh = float(region.rect[2]), float(region.rect[3])
        except Exception:
            rw, rh = float(w), float(h)
        _hs = [b[3] - b[1] for b in lines]
        _ws = [b[2] - b[0] for b in lines]
        med_h = float(np.median(_hs))
        med_w = float(np.median(_ws))
        _lsm_dbg = bool(os.environ.get("MANGA_LSM_DBG"))
# متنِ افقی — نه عمودی/هنر: خطِ معقول + بلوکِ پهن‌تر از ارتفاعِ خط
# (: کفِ ۸px موقتاً ۵ شد ولی رویِ متنِ ریزِ ۷pxِ رویِ هنرِ
# شلوغ (up0929) نوارِ تنگ‌تر از فال‌بکِ block-rect∪ink نتیجهٔ
# بدتری داد → برگشت به ۸؛ متنِ ریز از فال‌بکِ پهن‌تر پاک میشود)
        if med_h < 8.0 or med_h > 0.45 * max(8.0, rh):
            if _lsm_dbg:
                print(f"      [📐dbg] رد: med_h={med_h:.1f} rh={rh:.1f}",
                      flush=True)
            return None
        if len(lines) >= 2 and med_w < 1.6 * med_h:
            if _lsm_dbg:
                print(f"      [📐dbg] رد: باریک med_w={med_w:.1f} "
                      f"med_h={med_h:.1f}", flush=True)
            return None
        if rw > 0 and rh > 0 and (med_w > 1.4 * rw or med_h > 0.75 * rh):
            if _lsm_dbg:
                print(f"      [📐dbg] رد: ناسازگار با rect med_w={med_w:.1f}"
                      f" rw={rw:.1f} med_h={med_h:.1f} rh={rh:.1f}",
                      flush=True)
            return None
        m = np.zeros((h, w), dtype=np.uint8)
        total_area = 0
        rect_area = max(1.0, rw * rh)
        for (lx0, ly0, lx1, ly1) in lines:
            _strip = self._line_strip_ink(image, lx0, ly0, lx1, ly1,
                                          polys_raw, dbg=_lsm_dbg)
            if _strip is None:
                return None
            sx0, sy0, sx1, sy1, kept = _strip
            m[sy0:sy1, sx0:sx1][kept] = 255
            total_area += int(np.count_nonzero(kept))
        if total_area < 150:
            if _lsm_dbg:
                print(f"      [📐dbg] رد: خیلی کوچک {total_area}",
                      flush=True)
            return None
# ماسکِ خط‌به‌خط نباید خودش «تقریباً کلِ ناحیه» شود — وگرنه هدف
# (نماندنِ حباب در ماسک) از بین می‌رود → فال‌بک
# اندروید: برایِ متنِ ضخیمِ دورخط‌دار (You're… در
# 01.jpg) نوارها تا ~۸۸٪ rect پر می‌شوند؛ فال‌بکِ block-rect∪ink
# «همیشه» بزرگ‌تر یا مساویِ strips است → آستانه ۰.۹۵ (فقط وقتی
# strips واقعاً از خودِ rect بدتر شوند رد).
        _rect_thr = 0.72
        if _android_gate("MANGA_LSM_POLY_RESCUE"):
            _rect_thr = 0.95
        if total_area > _rect_thr * rect_area:
            if _lsm_dbg:
                print(f"      [📐dbg] رد: نزدیکِ کلِ rect {total_area}"
                      f"/{int(rect_area)}", flush=True)
            return None
        return m

    def _line_strip_ink(self, image: np.ndarray, lx0: float, ly0: float,
                        lx1: float, ly1: float, polys_raw: list,
                        dbg: bool = False):
        """ — جوهرِ یک خطِ متن (نوارِ خط‌به‌خط) — «اندازهٔ دقیقِ
        متن».

        این همان هستهٔ محاسباتیِ `_line_strips_mask` است ولی جدا شد تا
        «کامپوزِ دو-عکسی» هم بتواند نوارهایِ خط‌به‌خط را *بدونِ* شرط‌هایِ
        ردِ ناحیه‌ای بسازد (کامپوز باید «به اندازهٔ متن» باشد، نه بیشتر).

        خروجی: (sx0, sy0, sx1, sy1, kept) یا None (این خط هنر است/معتبر
        نیست). kept ماسکِ جوهرِ خط در مختصاتِ برش است."""
        try:
            h, w = image.shape[:2]
            lh = max(1.0, ly1 - ly0)
            pad_y = max(2.0, 0.32 * lh)
            pad_x = max(3.0, 0.22 * lh)
            sx0 = int(max(0.0, lx0 - pad_x))
            sx1 = int(min(float(w), lx1 + pad_x + 1.0))
            sy0 = int(max(0.0, ly0 - pad_y))
            sy1 = int(min(float(h), ly1 + pad_y + 1.0))
            if sx1 - sx0 < 8 or sy1 - sy0 < 8:
                return None
            g = cv2.cvtColor(image[sy0:sy1, sx0:sx1], cv2.COLOR_BGR2GRAY)
            med = float(np.median(g))
# قطبِ جوهر با «جرم» انتخاب می‌شود نه با روشنیِ زمینه —
# متنِ سفید روی باکسِ آبیِ میانه (پنجرهٔ سیستمِ asura) قبلاً فقط
# دورخطِ تیره را ماسک می‌کرد و بدنهٔ سفیدِ حروف می‌ماند.
            _dark = (g < med - 30.0)
            _bright = (g > med + 30.0)
            _fd = float(_dark.mean())
            _fb = float(_bright.mean())
# پنلِ نیمهشفافِ روشنِ پشتِ متن (سبکِ webtoon —
# PARAGRAPHهایِ img4 رویِ حصار): پنجرهٔ نوار هم پنل دارد هم
# هنرِ اطراف → اکثریتِ روشن «خودِ پنل» است نه متن؛ متنِ واقعی
# اقلیتِ تیره است. جوهرِ متن همیشه تراکمِ کم دارد (≤~۵۰٪
# نوار) → اگر قطبِ انتخابیِ اکثریت از ۰٫۵۵ بیشتر شد، قطبِ
# اقلیت جوهرِ واقعی است (تا نوارِ سالمِ متن رد نشود و به
# failedِ چاق نیفتد).
            _sw = False
            if _fb > _fd:
                core = _bright
                if _fb > 0.55 and 0.015 <= _fd <= 0.45:
# سوئیچِ 206c فقط وقتی معتبر است که قطبِ
# اقلیت «متن» باشد. متنِ سفید رویِ بنرِ سیاه (CHAPTER
# PAGE — img1018): اکثریتِ روشن = حروفِ سفید + حاشیهٔ
# سفیدِ صفحه در پدِ نوار؛ اقلیتِ تیره = خودِ بنر (یک
# تودهٔ عظیمِ پیوسته = زمینه) → سوئیچ، «زمینه» را
# جوهر میگرفت و حروفِ سفید هرگز ماسک نمیشدند. پس اگر
# قطبِ اقلیت یک تودهٔ عظیمِ سراسریِ پهنایِ نوار است
# سوئیچ نکن (اقلیت = زمینه، اکثریت = جوهرِ واقعی).
                    _mincg = _dark
                    _swg_ok = True
                    try:
                        _nsg, _lsg, _ssg, _ = cv2.connectedComponentsWithStats(
                            _mincg.astype(np.uint8), 8)
                        for _iig in range(1, _nsg):
                            if int(_ssg[_iig, cv2.CC_STAT_WIDTH]) \
                                    >= 0.9 * (sx1 - sx0) \
                                    and int(_ssg[_iig, cv2.CC_STAT_AREA]) \
                                    >= 0.25 * float(max(1, _mincg.sum())):
                                _swg_ok = False
                                break
                    except Exception:
                        pass
                    if _swg_ok:
                        core = _dark | (_bright
                                        & (cv2.dilate(
                                            _dark.astype(np.uint8) * 255,
                                            np.ones((5, 5), np.uint8)) > 0))
                        _sw = True
                if not _sw and _fd > 0.004:
# سایه/دورخطِ تیرهٔ چسبیده به حروفِ روشن هم جوهر است
                    _nc = cv2.dilate(core.astype(np.uint8) * 255,
                                     np.ones((7, 7), np.uint8)) > 0
                    core = core | (_dark & _nc)
            else:
                core = _dark
                if _fd > 0.55 and 0.015 <= _fb <= 0.45:
# قرینهٔ همان گیت برایِ قطبِ اقلیتِ روشن
                    _mincg = _bright
                    _swg_ok = True
                    try:
                        _nsg, _lsg, _ssg, _ = cv2.connectedComponentsWithStats(
                            _mincg.astype(np.uint8), 8)
                        for _iig in range(1, _nsg):
                            if int(_ssg[_iig, cv2.CC_STAT_WIDTH]) \
                                    >= 0.9 * (sx1 - sx0) \
                                    and int(_ssg[_iig, cv2.CC_STAT_AREA]) \
                                    >= 0.25 * float(max(1, _mincg.sum())):
                                _swg_ok = False
                                break
                    except Exception:
                        pass
                    if _swg_ok:
                        core = _bright | (_dark
                                          & (cv2.dilate(
                                              _bright.astype(np.uint8) * 255,
                                              np.ones((5, 5), np.uint8)) > 0))
                        _sw = True
                if not _sw:
# متنِ تیره با دورخطِ روشن (حروفِ قهوه‌ایِ
# 01.jpg با دورخطِ سفید روی حبابِ زرد): بدنهٔ روشنِ
# دورخطِ چسبیده به حروف هم جوهر است؛ وگرنه فقط خطِ
# تیره پاک می‌شود و شبحِ سفیدِ دورخطِ حروف می‌ماند
# (متریکِ VLM: متنِ خوانا ماند!).
                    if _fb > 0.004:
# دورخطِ روشنِ متنِ تیره (حبابِ سفیدِ کلاسیک
# «This is great, Butler-kun!!» در 01.jpg): دیلیتِ ۷
# بدنهٔ سفیدِ دورِ حروفِ تیره را کامل نمی‌گیرد (شبقِ
# سفید در خروجی). هم‌چنین پیکسل‌هایِ روشنِ تنگِ جدا که
# به قطعهٔ حروفِ تیره نزدیک‌اند (فاصلهٔ ≤۱۱px) هم جزو
# نوار — فاصلهٔ بینِ خط‌ها معمولاً ≥۱۴px است.
                        _nb = cv2.dilate(core.astype(np.uint8) * 255,
                                         np.ones((5, 5), np.uint8)) > 0
                        _brw = cv2.dilate(_bright.astype(np.uint8) * 255,
                                          np.ones((3, 3), np.uint8))
                        _nz2b, _lab2b, _st2b, _ = cv2.connectedComponentsWithStats(
                            _brw, connectivity=8)
                        for _ci2b in range(1, _nz2b):
                            _a2b = int(_st2b[_ci2b, cv2.CC_STAT_AREA])
                            _cw2b = int(_st2b[_ci2b, cv2.CC_STAT_WIDTH])
                            _ch2b = int(_st2b[_ci2b, cv2.CC_STAT_HEIGHT])
                            if _a2b <= 4 or max(_cw2b, _ch2b) > 3.0 * max(8.0, lh):
                                continue
                            _m2b = (_lab2b == _ci2b)
                            if bool((_m2b & _nb).any()):
                                core = core | _bright
                                break
                            _near2b = cv2.dilate(core.astype(np.uint8) * 255,
                                                 np.ones((11, 11), np.uint8)) > 0
                            if bool((_m2b & _near2b).any()):
                                core |= _m2b
                    if _fb > 0.004:
                        _nc = cv2.dilate(core.astype(np.uint8) * 255,
                                         np.ones((7, 7), np.uint8)) > 0
                        core = core | (_dark & _nc)
# نوارِ خط عمدتاً زمینه است؛ اگر بیشترِ نوار «جوهر» باشد یعنی
# هنر/بلوکِ تیره است — نه خطِ متن → فال‌بک
# متنِ ضخیمِ دورخط‌دار (حبابِ زردِ 01.jpg): بدنهٔ
# تیره + دورخطِ روشنِ چسبیده ( به core اضافه می‌شود)
# core را تا ~0.45 می‌رساند و نوارِ سالمِ متن رد می‌شد → فال‌بکِ
# block-rect∪ink → حفرهٔ بزرگ → پرِ تیرهٔ LaMa رویِ گوشی. روی
# زمینهٔ روشنِ یکدست آستانه سخاوتمندانه‌تر (0.55) — بلوکِ تیره
# (med پایین) همچنان با همان 0.42 رد می‌شود.
# آستانهٔ سخاوتمندانهٔ زمینهٔ روشن دیگر «فقطِ اندروید»
# نیست (دستور: «هم گوشی هم پی سی لینوکس باید هردو چک کنی») —
# فونتِ درشتِ کمیک («This is great, Butler-kun!!» — img6) رویِ
# PC نوارش رد میشد → نصفِ حروف جا میماند. MANGA_LSM_POLY_RESCUE=0
# رویِ هر دو پلتفرم رفتارِ قدیمیِ سختگیرانه را برمیگرداند.
            _thr_core = 0.42
            if med >= 170.0 and str(os.environ.get(
                    "MANGA_LSM_POLY_RESCUE", "")).strip().lower() != "0":
                _thr_core = 0.65
            if float(core.mean()) > _thr_core:
                if dbg:
                    print(f"      [📐dbg] رد: نوارِ پر از جوهر "
                          f"core={float(core.mean()):.2f} med={med:.0f}",
                          flush=True)
                return None
            core_u = (core.astype(np.uint8)) * 255
            core_u = cv2.morphologyEx(core_u, cv2.MORPH_CLOSE,
                                      np.ones((3, 3), np.uint8))
            near = cv2.dilate(core_u, np.ones((5, 5), np.uint8)) > 0
# هالهٔ 14..30 (قبلاً 18..30): لبه‌هایِ نرمِ JPEGِ
# حروف که ۱۴-۱۷ سطح تیره‌تر از زمینه‌اند قبلاً بیرونِ ماسک
# می‌ماندند و شبحِ خاکستریِ کم‌کنتراست جا می‌گذاشتند (حبابِ
# «WE KNEW.» فصلِ 264). ۱۰ امتحان شد ولی کنارِ قوسِ حباب
# پخشِ خاکستریِ LaMa را بزرگ میکرد → ۱۴ (تعادل).
            halo = (np.abs(g.astype(np.float32) - med) >= 14.0) \
                & (np.abs(g.astype(np.float32) - med) <= 30.0) & near
            lm = ((core_u > 0) | halo)
# نقشهٔ پالی‌هایِ OCR در برشِ نوار: حروف داخلِ پالی‌ها
# هستند، دیوارِ حباب/قوس/کادرِ پنل بیرونِ آن‌ها
            _pm = np.full(lm.shape, 255, dtype=np.uint8)
            _pm_ok = False
            try:
                _pm = np.zeros(lm.shape, dtype=np.uint8)
                for _pp in (polys_raw or []):
                    _ppa = np.asarray(_pp, dtype=np.float32).reshape(-1, 2)
                    if _ppa.shape[0] < 3:
                        continue
                    _pii = np.rint(_ppa).astype(np.int32)
                    _pii[:, 0] -= sx0
                    _pii[:, 1] -= sy0
                    cv2.fillPoly(_pm, [_pii], 255)
                    _pm_ok = True
                _pm = cv2.dilate(_pm, np.ones((3, 3), np.uint8))
            except Exception:
                _pm = np.full(lm.shape, 255, dtype=np.uint8)
                _pm_ok = False
# قطعه‌هایِ عظیم = هنر، نه حرف — امن‌تر: ردِ خط
            nz, lal, sts, _ = cv2.connectedComponentsWithStats(
                lm.astype(np.uint8), connectivity=8)
            kept = np.zeros_like(lm)
            for ci in range(1, nz):
                ca = int(sts[ci, cv2.CC_STAT_AREA])
                cwd = int(sts[ci, cv2.CC_STAT_WIDTH])
                chg = int(sts[ci, cv2.CC_STAT_HEIGHT])
                if ca > 0.55 * (sy1 - sy0) * (sx1 - sx0) \
                        and max(cwd, chg) > 2.5 * max(8.0, lh):
# نجاتِ متنِ دورخط‌دار: کامپوننتی که «هنر»
# خوانده میشود ولی ≥۵۵٪ پیکسلهایش داخلِ پالیهایِ OCR
# خودِ خط است = حروفِ ضخیمِ بههمپیوسته (THEN…/the speed
# در 01.jpg)، نه هنر. هنرِ واقعی (قوسِ دیوار، افکتِ صدا)
# بیرونِ پالیهاست و مثلِ قبل رد می‌شود.
                    if _pm_ok and _android_gate("MANGA_LSM_POLY_RESCUE"):
                        _cm2 = (lal == ci)
                        _in = float(np.count_nonzero(_cm2 & (_pm > 0)))
                        if _in >= 0.55 * float(max(1, ca)):
                            if dbg:
                                print(f"      [📐dbg] نجاتِ متنِ دورخط‌دار "
                                      f"ca={ca} {cwd}×{chg} "
                                      f"درپالی={_in / max(1, ca):.2f}",
                                      flush=True)
                            kept |= _cm2
                            continue
                    if dbg:
                        print(f"      [📐dbg] رد: قطعهٔ هنر ca={ca} "
                              f"{cwd}×{chg}", flush=True)
                    return None
# باگِ «متنِ کج یا ناقص پاک میشه»: قوسِ دیوارِ
# حباب/خطِ کادرِ پنل که از لبهٔ بالایی/پایینیِ نوارِ خط
# می‌گذرد، «جوهرِ تیرهٔ» نوار خوانده می‌شد → داخلِ ماسکِ
# می‌رفت → LaMa قوس را نمی‌ساخت و کامپوز حذفش را به خروجی
# می‌برد (قوسِ حباب گم می‌شد). جوهرِ متن همیشه ≥pad_y از
# لبهٔ نوار فاصله دارد؛ کامپوننتی که به لبهٔ افقیِ نوار
# بچسبد و بیرونِ پالی‌هایِ OCR باشد = ساختار است → از ماسک
# بیرون کشیده می‌شود.
                if sy0 > 0 and sy1 < h:
                    _ct = int(sts[ci, cv2.CC_STAT_TOP])
                    if (_ct <= 0 or _ct + chg >= (sy1 - sy0)) \
                            and chg >= max(6.0, 0.75 * lh):
                        _cm = (lal == ci)
                        _onp = float(np.count_nonzero(_cm & (_pm > 0)))
                        if _onp < 0.35 * float(max(1, ca)):
# مثلِ 206b: حروفِ چاقِ بههمپیوستهٔ
# فونتِ کمیک («This is great, Butler-kun!!» —
# img6) به لبهٔ بالا/پایینِ نوار میرسند و
# «ساختار» خوانده میشوند → کلِ کامپوننت (= یک
# کلمهٔ کامل) از نوارِ کامپوز حذف = کلمه در
# عکسِ دوم برمیگشت. حالا فقط پیکسلهایِ بیرونِ
# پالی حذف میشوند؛ حروفِ داخلِ پالی میمانند
# (پیکسلِ بیرونِ پالی در donor دستنخورده است
# پس برگشتِ آن بیخطر است).
                            if _onp > 0:
                                kept |= (_cm & (_pm > 0))
                                if dbg:
                                    print(f"      [📐dbg] ساختارِ لبه‌ای "
                                          f"ترکیبی — فقطِ حروفِ درپالی "
                                          f"({_onp:.0f}/{ca})", flush=True)
                                continue
                            if dbg:
                                print(f"      [📐dbg] حذفِ ساختارِ لبه‌ای "
                                      f"ca={ca} chg={chg}", flush=True)
                            continue
# همان گاردِ برایِ لبهٔ چپ/راستِ نوار:
# قابِ رنگیِ حباب (حبابِ شش‌ضلعیِ سبزِ up0822) از انتهایِ
# خطِ متن رد میشود، «جوهرِ تیرهٔ» نوار خوانده می‌شد → داخلِ
# نوارِ کامپوز میرفت و قابِ رنگی تکه‌تکه به خروجی می‌رفت.
# کامپوننتی که به لبهٔ چپ/راستِ نوار بچسبد، عریض (پهنایِ
# عبور از نوار) و عمدتاً بیرونِ پالیهایِ OCR باشد = قاب است
# → از نوار بیرون کشیده میشود؛ حروف (داخلِ پالی) میمانند.
                if sx0 > 0 and sx1 < w:
                    _cl = int(sts[ci, cv2.CC_STAT_LEFT])
                    if (_cl <= 0 or _cl + cwd >= (sx1 - sx0)) \
                            and cwd >= max(4.0, 0.22 * lh):
                        _cm = (lal == ci)
                        _onp = float(np.count_nonzero(_cm & (_pm > 0)))
                        if _onp < 0.35 * float(max(1, ca)):
                            if dbg:
                                print(f"      [📐dbg] حذفِ قابِ لبه‌ای "
                                      f"ca={ca} cwd={cwd}", flush=True)
                            continue
# حروفِ چسبیده به میله/قاب (متنِ سفیدِ
# img4 رویِ حصار): کلِ کامپوننت حذف نشود — فقط
# پیکسلهایِ بیرونِ پالی (میله/قاب)؛ حروفِ داخلِ
# پالی میمانند وگرنه متن جا میماند.
                        if _onp < float(max(1, ca)):
                            kept |= (_cm & (_pm > 0))
                            if dbg:
                                print(f"      [📐dbg] قابِ لبه‌ای ترکیبی — "
                                      f"فقطِ حروفِ درپالی "
                                      f"({_onp:.0f}/{ca})", flush=True)
                            continue
                kept |= (lal == ci)
# مثلِ thr_core: آستانهٔ 0.80ِ زمینهٔ روشن دیگر فقطِ
# اندروید نیست؛ فونتِ درشتِ کمیک (kept≈۰٫۶۴ — img6) رویِ PC
# «نوارِ اشباع» رد میشد → نصفِ حروف جا میماند.
            if float(kept.mean()) > (0.80 if (
                    med >= 170.0
                    and str(os.environ.get("MANGA_LSM_POLY_RESCUE",
                                           "")).strip().lower() != "0")
                    else 0.60):
                if dbg:
                    print(f"      [📐dbg] رد: نوارِ اشباع "
                          f"kept={float(kept.mean()):.2f}", flush=True)
                return None
# متنِ سفید با دورخطِ تیره (مثلِ «WE FRIENDS?»):
# بدنهٔ سفیدِ حرف «حفره»ٔ دورخط است → نوار فقط دورخط را
# می‌گرفت و بدنهٔ حروف (خودِ متن!) باقی می‌ماند. پرکردنِ
# حفره‌هایِ کوچک نوار = پوششِ کاملِ حروف. اگر پرکردن سطحِ
# زیادی اضافه کند (ساختارِ بزرگ) → همان نوارِ قبلی می‌ماند.
# kept باید بولی بماند (نحوهٔ ایندکسِ m[...][kept] ماسکِ
# صفحه bool است و kept هم باید bool باشد).
            try:
                _kept_n = int(np.count_nonzero(kept))
                if _kept_n > 0:
                    _filled = self._fill_holes_mask(kept)
                    _filled_n = int(np.count_nonzero(_filled))
                    if _filled_n > _kept_n and _filled_n <= 2.2 * _kept_n:
                        kept = np.asarray(_filled, dtype=bool)
            except Exception:
                pass
            return (sx0, sy0, sx1, sy1, kept)
        except Exception:
            return None

    @staticmethod
    def _panel_leftover_ink(image: np.ndarray, rect, excl: np.ndarray,
                            ret_stats: bool = False,
                            med_h: float = 0.0):
        """ — ماسکِ «متنِ جامانده» در بلوک (فقطِ مصرفِ اندروید).

        وقتی OCRِ گوشی خطهایِ یک بلوکِ متراکم را هرز/ناقص خوانده، بینِ
        نوارهایِ خط دهها گلیفِ واقعی باقی میماند (متنِ نیمهپاکِ صفحهٔ
        قانونیِ 700×11362). خروجی: ماسکِ «فقطِ گلیفهای جامانده» (هر
        ناحیه به اندازهٔ حروف — قانونِ دو-عکسی؛ NOT مستطیلِ توپر —
        LaMaِ بلوکِ کامل رویِ زمینهٔ عکسی توهمِ متن/نویز میسازد) و
        اگر ret_stats: (n_gلیف، med، stdِ زمینهٔ روشن).

        نکتهٔ کالیبراسیون (اندازهگیریِ صفحهٔ 700×11362): stdِ کلِ bg به
        خاطرِ «خودِ متنِ جامانده» تا ۸۵ میرسد → تخت بودن روی «زمینهٔ
        روشنِ بیرونِ جوهر» سنجیده میشود. گلیف = قطعهٔ ۸..۲۶۰۰px با
        ارتفاعِ ۳..۶۴ و عرضِ ≤۱۸۰ (زیرخط/استروکِ هنریِ بلند رد میشود).
        excl = ماسکِ نوارها/پالیها که از جستجو خارج میشود.

         — سقفهایِ اندازهٔ گلیف سازگار با ارتفاعِ خطِ همان
        ناحیه شدند (med_h): فونتِ درشتِ کمیک (img6 — بلندیِ خط ۶۹..۷۹)
        با سقفِ ثابتِ ۶۴ رد میشد و گلیفهای جامانده هیچ‌وقت نجات
        نمیافتادند. med_h=۰ = رفتارِ قبلی."""
        try:
            h, w = image.shape[:2]
# سقفهایِ سازگار با ارتفاعِ خط
            _mh = float(med_h or 0.0)
            _hh_max = max(64.0, 1.15 * _mh + 4.0) if _mh > 0 \
                else 64.0
            _a_max = max(2600.0, 0.60 * _mh * _mh) if _mh > 0 \
                else 2600.0
            _ww_max = max(180.0, 2.6 * _mh) if _mh > 0 else 180.0
            rx, ry, rw, rh = [int(v) for v in rect]
            x0, y0 = max(0, rx), max(0, ry)
            x1, y1 = min(w, rx + rw), min(h, ry + rh)
            if x1 - x0 < 48 or y1 - y0 < 32:
                return (None, (0, 0.0, -1.0)) if ret_stats else None
            sub = image[y0:y1, x0:x1]
            g = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
            ex = excl[y0:y1, x0:x1] > 0
            bg = ~ex
            nbg = int(bg.sum())
            if nbg < 400:
                return (None, (0, 0.0, -1.0)) if ret_stats else None
            med = float(np.median(g[bg]))
            if med < 150.0:
                return (None, (0, med, -1.0)) if ret_stats else None
            ink = (g.astype(np.int16) < (med - 55.0)) & bg
            ink_n = int(ink.sum())
            if ink_n < 40 or ink_n > 0.42 * nbg:
                return (None, (0, med, -1.0)) if ret_stats else None
# معیارِ «تخت» رویِ زمینهٔ روشنِ بیرونِ جوهر — خودِ متنِ
# جامانده نباید std را بترکاند
            _lite = (bg & ~cv2.dilate(
                ink.astype(np.uint8),
                np.ones((15, 15), np.uint8)).astype(bool))
            if int(_lite.sum()) < 300:
                return (None, (0, med, -1.0)) if ret_stats else None
            std_l = float(np.std(g[_lite]))
            if std_l > 52.0:
                return (None, (0, med, std_l)) if ret_stats else None
            nl, lbl, st, _ = cv2.connectedComponentsWithStats(
                ink.astype(np.uint8), connectivity=8)
            gm = np.zeros_like(lbl, dtype=np.uint8)
            n_g = 0
            for i in range(1, nl):
                a = int(st[i, cv2.CC_STAT_AREA])
                hh = int(st[i, cv2.CC_STAT_HEIGHT])
                ww = int(st[i, cv2.CC_STAT_WIDTH])
                if 8 <= a <= _a_max and 3 <= hh <= _hh_max \
                        and ww <= _ww_max:
                    gm[lbl == i] = 255
                    n_g += 1
            if n_g < 10:
                return (None, (n_g, med, std_l)) if ret_stats else None
            full = np.zeros((h, w), dtype=np.uint8)
            full[y0:y1, x0:x1] = gm
            return (full, (n_g, med, std_l)) if ret_stats else full
        except Exception:
            return (None, (0, 0.0, -1.0)) if ret_stats else None

    @staticmethod
    def _ring_flat_stats(crop_img: np.ndarray, crop_msk: np.ndarray,
                         band: int = 26):
        """ — آمارِ حلقهٔ اطرافِ کلاستر (فقطِ مصرفِ اندروید).
        اگر حلقهٔ اطرافِ حفره «تخت» باشد (گسترهٔ صدکیِ ≤۲۴)، پرِ
        درجه‌دومِ حلقه بهجایِ LaMa کافی و صدها برابر سریعتر است.
        خروجی: (میانه، std) یا None (حلقهٔ کوچک/بافت‌مند → LaMa)."""
        try:
            g = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
            mk = (crop_msk > 0)
            if not mk.any():
                return None
            din = cv2.dilate(crop_msk, np.ones((9, 9), np.uint8)) > 0
            mout = cv2.dilate(
                crop_msk,
                np.ones((2 * band + 1, 2 * band + 1), np.uint8)) > 0
            ring = mout & ~din
            if int(ring.sum()) < 500:
                return None
            med = float(np.median(g[ring]))
            std = float(np.std(g[ring]))
            p = np.percentile(g[ring], [10, 90])
            if (float(p[1]) - float(p[0])) > 24.0:
                return None
            return (med, std)
        except Exception:
            return None

    def _build_text_mask_fast(self, image: np.ndarray,
                              regions: List[TextRegion]) -> Optional[np.ndarray]:
        try:
            h, w = image.shape[:2]
            m = np.zeros((h, w), dtype=np.uint8)
        except Exception:
            return None
# صندوق‌هایِ «متنِ روشن روی محفظهٔ تیره» که باید اجباری
# با LaMa و ماسکِ بلوکِ کامل پاک شوند (شبحِ متنِ قدیمی — کارتِ عنوانِ
# Crimson Dragon). در ابتدایِ هر صفحه خالی می‌شود.
        self._lama_force_rect_boxes = []
# باکس‌هایِ «فقط-جوهر»: فقط «روشِ» پاکسازی را LaMa
# اجباری می‌کند؛ ماسک هرگز توپُر نمی‌شود (قانونِ دو-عکسیِ کاربر)
        self._lama_ink_boxes = []
# بنرهایِ تبلیغاتی (واترمارکِ دامنهٔ سایت‌ها): کلِ بنر
# توپر پاک می‌شود و در کامپوز هم کلِ بنر از عکسِ پاک‌شده می‌آید
        self._promo_rect_boxes = []
        padding = max(0, int(getattr(self, "mask_padding", 3)))
# اندروید: متنِ ضخیمِ دورخط‌دار (حبابهایِ زردِ 01.jpg) —
# پدِ ۳ ماسک را دقیقاً رویِ دورخطِ سفیدِ حروف میگذارد و LaMaِ گوشی
# دورخط را داخلِ حفره «ادامه» میدهد (شبحِ سفیدِ گلیفی). پدِ ۸ لبهٔ
# ماسک را در زمینهٔ تمیز میبرد (تستِ H: حبابِ TL تقریباً عالی شد).
        if padding < 8 and _android_gate("MANGA_LSM_POLY_RESCUE"):
            padding = 8
# دیلیشنِ padding به‌ازایِ هر ناحیه و «قبلِ» گارد/لیمیت انجام
# می‌شود (قبلاً بعد از حلقه روی کلِ ماسک بود و بعد از کلیپِ حباب
# ماسک را ۳px داخلِ دیوار می‌فرستاد). حالا لیمیتِ حباب آخربُر است.
        _pad_k = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (2 * padding + 1, 2 * padding + 1)) \
            if padding > 0 else None
        n_ok = 0
        n_skip = 0
        for region in regions:
# تبلیغ/واترمارکِ دامنه («ASURASCANS.COM مثل دیسکورد
# و... سایت هارو کامل فیلتر تبلیغ بزن»): کلِ بنرِ تبلیغ توپر
# ماسک می‌شود — نه نوارِ خط‌ها — تا هیچ ذره‌ای از حروفِ تبلیغ
# در خروجی نماند. (حذفِ بیش از اندازه مجاز است.)
# SFX هم توپر: پلیِ OCR اغلب فقط بخشی از حروفِ
# درشت را می‌گیرد («HAA»→«10») و بقیه می‌ماند؛ rect ناحیه از
# روی جوهر تنگ بریده شده پس توپرکردنش امن است.
            if getattr(region, "kind", "") in ("promo", "sfx"):
                try:
                    _px0, _py0, _pw, _ph = [int(v) for v in region.rect]
                    _px1, _py1 = _px0 + _pw, _py0 + _ph
                    if getattr(region, "kind", "") == "promo":
# بنر کامل: قابِ سفید/سایه/ماسکوت هم پوشانده
# شود (باکسِ OCR همیشه تنگ‌تر از گرافیکِ بنر است)
                        _px0, _py0, _px1, _py1 = self._expand_promo_rect(
                            image, _px0, _py0, _px1, _py1)
                    if _px1 - _px0 >= 8 and _py1 - _py0 >= 8:
                        m[_py0:_py1, _px0:_px1] = 255
                        n_ok += 1
                        if self.debug:
                            try:
                                print(f"  [🔍] {getattr(region, 'kind', '')} → ماسکِ توپر "
                                      f"rect=({_px0},{_py0},"
                                      f"{_px1 - _px0},{_py1 - _py0})")
                            except Exception:
                                pass
                        if getattr(region, "kind", "") == "promo":
                            _prb = getattr(self, "_promo_rect_boxes", None)
                            if _prb is None:
                                _prb = []
                                self._promo_rect_boxes = _prb
                            _prb.append([_px0, _py0, _px1, _py1])
                        continue
                except Exception:
                    pass
            pts_list = []
            _tall = 0
            _wide = 0
            _polys_raw = []
            for p in (getattr(region, "ocr_polys", None) or []):
                try:
                    pp = np.asarray(p, dtype=np.float32).reshape(-1, 2)
                except Exception:
                    continue
                if pp.shape[0] < 3:
                    continue
                _polys_raw.append(pp)
                c = pp.mean(axis=0)
                pts_list.append(np.rint(c + (pp - c) * 1.2).astype(np.int32))
                _pw_ = float(pp[:, 0].max() - pp[:, 0].min())
                _ph_ = float(pp[:, 1].max() - pp[:, 1].min())
                if _ph_ >= 1.3 * _pw_ and _ph_ >= 18.0:
                    _tall += 1
                if _pw_ >= 1.3 * _ph_ and _pw_ >= 18.0:
                    _wide += 1
            if pts_list:
                if self.debug:
                    try:
                        print(f"  [🔍] ناحیه rect={tuple(int(v) for v in region.rect)} polys={len(_polys_raw)} tall={_tall} wide={_wide}")
                    except Exception:
                        pass
# متن روی محفظهٔ تیرهٔ یکدست (بنرِ سیاه و امثالش)
# → ماسکِ جوهریِ تنگ؛ قبل از شاخه‌هایِ مستطیلی
                try:
                    _enc = self._enclosure_tight_mask(
                        image, _polys_raw,
                        rect=tuple([int(v) for v in region.rect]))
                except Exception:
                    _enc = None
                if _enc is not None and np.any(_enc):
# قانونِ دقیقِ دو-عکسیِ کاربر: ماسک = فقط
# جوهرِ متن (تنگ)، نه کلِ محفظه! قبلاً  ماسک
# با _enc_full (کلِ محفظهٔ تیره) جابه‌جا و باکسِ کاملش
# به بلوکِ اجباری-LaMa می‌رفت → LaMa کلِ داخلِ کارت/
# حباب را «بازسازی» می‌کرد (قابِ سفید + هنرِ داخل =
# رنگِ تخت — گزارشِ کاربر: «کل حباب انتقال داده شد و
# با رنگ پر شد؛ لاما روش استفاده نشد»). حالا فقط جوهرِ
# حروف پاک می‌شود؛ LaMa استروک‌ها را از بافتِ اطراف پر
# می‌کند و هنر سرِ جایش می‌ماند. باکسِ جوهر فقط «روشِ»
# پاکسازی را LaMa اجباری می‌کند (نه توپُرشدنِ ماسک).
                    if self.debug:
                        try:
                            print("  [🔍] ماسکِ #مسیر: enclosure-tight (فقطِ جوهر)")
                        except Exception:
                            pass
                    if (getattr(self, "use_lama", False)
                            and self._clean_level() != "fast"):
                        try:
                            _ysI, _xsI = np.nonzero(_enc)
                            if _ysI.size:
                                self._lama_ink_boxes.append(
                                    [int(_xsI.min()) - 8, int(_ysI.min()) - 8,
                                     int(_xsI.max()) + 9,
                                     int(_ysI.max()) + 9])
                        except Exception:
                            pass
                    if _pad_k is not None:
                        _enc = cv2.dilate(_enc, _pad_k)
                    _enc = self._limit_mask_to_bubble(image, _enc, region)
                    m = cv2.bitwise_or(m, _enc)
                    n_ok += 1
                    continue
                if _tall >= 2 and len(_polys_raw) >= 2:
                    if self.debug:
                        try:
                            print("  [🔍] → تلاشِ vert-block")
                        except Exception:
                            pass
                    try:
                        _bb = MangaTranslator._text_block_box(
                            _polys_raw, region.rect, vert=True)
                        if _bb is not None:
                            x0, y0 = max(0, _bb[0]), max(0, _bb[1])
                            x1, y1 = min(w, _bb[0] + _bb[2]), min(h, _bb[1] + _bb[3])
                            if x1 - x0 >= 6 and y1 - y0 >= 6:
                                _rm = np.zeros_like(m)
                                cv2.rectangle(_rm, (x0, y0), (x1, y1), 255, -1)
                                if not self._fast_bubble_guard(
                                        image, _rm, region, True):
                                    n_skip += 1
                                    continue
# دیوارِ حباب/کادر از ماسک جدا شود
                                try:
                                    _rm = self._carve_structural_walls(
                                        image, _rm, region, _polys_raw)
                                except Exception:
                                    pass
                                _rm = self._limit_mask_to_bubble(
                                    image, _rm, region)
# ماسکِ تقریباً-کلِ-حبابِ-سفید →
# جوهرِ تنگ (جلوگیریِ توهمِ LaMa-Manga)
                                try:
                                    _rm = self._white_bubble_tighten(
                                        image, _rm, None)
                                except Exception:
                                    pass
                                _rm = self._pad_dilate_wall_safe(
                                    _rm, image, region, _pad_k)
                                m = cv2.bitwise_or(m, _rm)
                                n_ok += 1
                                continue
                    except Exception:
                        pass
# حبابِ تکخطی (polys=1): _polys_dense به ≥۲
# پالی نیاز دارد و حبابهایِ تکخطی («WE KNEW.») هرگز به
# line-strips نمیرسیدند → فالبکِ fillPoly = پرکردنِ کلِ
# داخلِ حباب با LaMa = نوار/لکهٔ خاکستریِ شبح‌مانند.
# پالیِ واحدِ پهن (خطِ متنِ افقی) هم مجاز شد؛ شرطهایِ داخلیِ
# _line_strips_mask (سهمِ جوهر، سازگاریِ rect) همچنان رد
# میکنند.
                _dense = MangaTranslator._polys_dense(_polys_raw)
                if not _dense:
                    try:
                        _pp2 = [np.asarray(p, dtype=np.float32).reshape(-1, 2)
                                  for p in (_polys_raw or [])
                                  if np.asarray(p).size]
                        if len(_pp2) == 1:
                            _pw2 = float(_pp2[0][:, 0].max()
                                           - _pp2[0][:, 0].min())
                            _ph2 = float(_pp2[0][:, 1].max()
                                           - _pp2[0][:, 1].min())
                            _dense = (_pw2 >= 1.3 * _ph2
                                         and _pw2 >= 18.0
                                         and _ph2 >= 8.0)
                    except Exception:
                        _dense = False
                if _dense:
                    if self.debug:
                        try:
                            print("  [🔍] → تلاشِ line-strips")
                        except Exception:
                            pass
# ایدهٔ «دو عکس» کاربر: اولی = پاک‌شده که فقط
# «به اندازهٔ متنِ استخراج‌شده، خط به خط» برش می‌خورد
# دومی = اصلی که جایِ دقیقِ هر خط از روی آن اندازه گرفته
# می‌شود. ماسکِ خط‌به‌خط → فضایِ بینِ خط‌ها و دیوارِ حباب
# هرگز در ماسک نیست → حباب سالم + پچِ کوچک‌ترِ LaMa.
                    try:
                        _lsm = self._line_strips_mask(image, _polys_raw, region)
                    except Exception:
                        _lsm = None
                    if _lsm is not None and np.any(_lsm):
                        _rm = _lsm
                        if self.debug:
                            try:
                                print(f"  [🔍] ماسکِ #مسیر: line-strips px={int(cv2.countNonZero(_rm))}")
                            except Exception:
                                pass
                        if self._fast_bubble_guard(image, _rm, region, True):
                            try:
                                _rm = self._carve_structural_walls(
                                    image, _rm, region, _polys_raw)
                                if self.debug:
                                    try:
                                        print(f"  [🔍] پس از کارو (strips) px={int(cv2.countNonZero(_rm))}")
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                            _rm = self._limit_mask_to_bubble(
                                image, _rm, region)
                            _rm = self._pad_dilate_wall_safe(
                                _rm, image, region, _pad_k)
                            m = cv2.bitwise_or(m, _rm)
                            n_ok += 1
                            continue
                    try:
                        _bb = MangaTranslator._text_block_box(
                            _polys_raw, region.rect, vert=False)
                        if _bb is not None:
                            x0, y0 = max(0, _bb[0]), max(0, _bb[1])
                            x1, y1 = min(w, _bb[0] + _bb[2]), min(h, _bb[1] + _bb[3])
                            if x1 - x0 >= 6 and y1 - y0 >= 6:
                                _rm = np.zeros_like(m)
                                cv2.rectangle(_rm, (x0, y0), (x1, y1), 255, -1)
                                if not self._fast_bubble_guard(
                                        image, _rm, region, True):
                                    n_skip += 1
                                    continue
                                _inkB = None
                                try:
                                    _inkB = MangaTranslator._ink_absorb_mask(
                                        image, _rm, _polys_raw, band=14,
                                        box=tuple([int(v) for v in region.rect]),
                                        levels=3)
                                    if _inkB is not None and np.any(_inkB):
# در محفظهٔ باکنتراست (متنِ
# روشن روی بنرِ تیره هم‌رنگِ صفحه) فقط
# جوهرِ گلیف — نه مستطیلِ بلوک
# متنِ آزاد روی زمینهٔ گرادیانی
# (بدونِ حباب) هم ماسکِ جوهریِ تنگ
# می‌گیرد — مستطیل لکهٔ تخت می‌سازد
                                        if self._ink_tight_ok(
                                                image, _rm, _inkB, _polys_raw):
# محفظهٔ تیره + متنِ روشن:
# تنگِ جوهری فقط هستهٔ گلیف را می‌گرفت
# → پرکنندهٔ رنگی روی گرادیانِ تیره شبحِ
# حروف جا می‌گذاشت و در ترکیبِ دو-عکسی
# هم پیکسلِ بینِ گلیف‌ها از عکسِ اصلی
# می‌ماند = «متنِ قبلی سرِ جایش». طبقِ سبکِ
# کاربر (عکسِ اول باید کامل پاک شود؛ حباب/
# محفظه هم آسیب دید مهم نیست) در حالتِ
# LaMaِ کیفیت مستطیلِ کاملِ بلوک ∪ جوهر
# می‌ماند و کلاستر اجباراً به LaMa می‌رود
# سقفِ ترکیبِ دو-عکسی هنرِ بیرونِ بلوک را
# سالم نگه می‌دارد. مسیرِ opencv مثل قبل تنگ.
                                            if (getattr(self, "use_lama", False)
                                                    and self._clean_level() != "fast"
                                                    and self._ink_bg_dark(
                                                        image, _inkB)):
                                                _rm = cv2.bitwise_or(_rm, _inkB)
                                                try:
                                                    _ys2, _xs2 = np.nonzero(_rm)
                                                    self._lama_force_rect_boxes.append(
                                                        [int(_xs2.min()), int(_ys2.min()),
                                                         int(_xs2.max()) + 1,
                                                         int(_ys2.max()) + 1,
                                                         int(getattr(region, "id", -1))])
                                                except Exception:
                                                    pass
                                            elif getattr(self, "use_lama", False):
# زمینهٔ روشن → بلوکِ
# کامل ممنوع؛ ماسکِ سخاوتمند ∪ جوهر
# با مسیرِ عادی (flat/color/LaMaِ
# کلاستر) پاک می‌شود
                                                _rm = cv2.bitwise_or(_rm, _inkB)
                                            else:
                                                _rm = _inkB
                                        elif self._free_text_tight_ok(
                                                image, _rm, _inkB, _polys_raw):
                                            _rm = _inkB
                                        else:
                                            _rm = cv2.bitwise_or(_rm, _inkB)
                                            if self.debug:
                                                try:
                                                    print("  [🔍] ماسکِ #مسیر: block-rect∪ink")
                                                    _g2 = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                                                    _im2 = _inkB > 0
                                                    _ti = float(np.median(_g2[_im2])) if np.any(_im2) else -1
                                                    _ri2 = ((cv2.dilate(_inkB, np.ones((9, 9), np.uint8)) > 0) & (~_im2))
                                                    _to = float(np.median(_g2[_ri2])) if np.any(_ri2) else -1
                                                    print(f"  [🔍] inkB px={int(cv2.countNonZero(_inkB))} t_ink={_ti:.0f} t_out={_to:.0f} light={self._ink_is_light(image, _inkB)}")
                                                except Exception as _e:
                                                    print("  [🔍] inkB dbg fail:", _e)
# متنِ روشن روی محفظهٔ تیره:
# ماسکِ توپر (مستطیل ∪ جوهر) قطعی است —
# کارو/کلیپِ حباب/تایتِن اینجا فقط خرابکاری
# می‌کنند (پنیرِ سوری = شبحِ حروف) →
# مستقیم در ماسک می‌نشیند و ادامه نمی‌دهد
                                            if (getattr(self, "use_lama", False)
                                                    and self._clean_level() != "fast"
                                                    and self._ink_is_light(
                                                        image, _inkB)):
# گاردِ بافتِ زمینه:
# مستطیلِ کاملِ بلوک فقط برای
# محفظهٔ «یکدست» (بنرِ صاف).
# روی گرادیان/برف‌نوی/نقش‌ونگار
# حفرهٔ بزرگِ LaMa = پرِ تختِ
# بی‌بافت (412e9e: EXEC و
# GREEN MOON) → ماسکِ
# پالی‌به‌پالی ∪ جوهر.
                                                _bgst = self._block_bg_stats(
                                                    image,
                                                    tuple([int(v) for v in
                                                           region.rect]),
                                                    _inkB)
                                                if _bgst is not None and (
                                                        _bgst[1] > 36.0
                                                        or _bgst[2] > 0.12):
                                                    try:
                                                        _rm2 = np.zeros_like(m)
# پالیِ
# «خام» (نه ۱.۲×):
# گسترشِ ۱.۲× روی
# پلاک/قاب‌هایِ تزئینی
# قاب را هم ماسک
# می‌کند → رگهٔ قاب
# در مرجع‌ها (412e9e)
                                                        for _pl2 in (region.ocr_polys or []):
                                                            try:
                                                                _pq = np.asarray(
                                                                    _pl2,
                                                                    dtype=np.float32).reshape(
                                                                    -1, 2)
                                                            except Exception:
                                                                continue
                                                            if _pq.shape[0] < 3:
                                                                continue
                                                            cv2.fillPoly(
                                                                _rm2,
                                                                [np.rint(
                                                                    _pq
                                                                ).astype(np.int32)],
                                                                255)
                                                        _rm = cv2.bitwise_or(
                                                            _inkB, _rm2)
                                                    except Exception:
                                                        _rm = _inkB
                                                    _rm = self._pad_dilate_wall_safe(
                                                        _rm, image, region,
                                                        _pad_k)
                                                    m = cv2.bitwise_or(m, _rm)
                                                    n_ok += 1
                                                    if self.debug:
                                                        try:
                                                            print(
                                                                "  [🔍] ماسکِ #مسیر: "
                                                                "poly-bands∪ink "
                                                                f"(زمینهٔ بافت‌مند "
                                                                f"std={_bgst[1]:.0f} "
                                                                f"bright={_bgst[2]:.2f})"
                                                            )
                                                        except Exception:
                                                            pass
                                                    continue
                                                try:
                                                    _ys2, _xs2 = np.nonzero(_rm)
                                                    self._lama_force_rect_boxes.append(
                                                        [int(_xs2.min()), int(_ys2.min()),
                                                         int(_xs2.max()) + 1,
                                                         int(_ys2.max()) + 1,
                                                         int(getattr(region, "id", -1))])
                                                except Exception:
                                                    pass
                                                _rm = self._pad_dilate_wall_safe(
                                                    _rm, image, region, _pad_k)
                                                m = cv2.bitwise_or(m, _rm)
                                                n_ok += 1
                                                continue
                                except Exception:
                                    pass
# دیوارِ حباب/کادر از ماسک جدا شود
                                try:
                                    _rm = self._carve_structural_walls(
                                        image, _rm, region, _polys_raw,
                                        ink_mask=_inkB)
                                except Exception:
                                    pass
                                _rm = self._limit_mask_to_bubble(
                                    image, _rm, region)
# ماسکِ تقریباً-کلِ-حبابِ-سفید →
# جوهرِ تنگ (جلوگیریِ توهمِ LaMa-Manga)
                                try:
                                    _rm = self._white_bubble_tighten(
                                        image, _rm, _inkB)
                                except Exception:
                                    pass
                                if _pad_k is not None:
                                    _rm = self._pad_dilate_wall_safe(
                                        _rm, image, region, _pad_k)
                                m = cv2.bitwise_or(m, _rm)
                                try:
                                    _dm3 = os.environ.get("MANGA_DUMP_MASK_3")
                                    if _dm3:
                                        cv2.imwrite(_dm3, m)
                                except Exception:
                                    pass
                                n_ok += 1
                                continue
                    except Exception:
                        pass
                _rm = np.zeros_like(m)
                cv2.fillPoly(_rm, pts_list, 255)
                if self.debug:
                    try:
                        print(f"  [🔍] ماسکِ #مسیر: fillPoly px={int(cv2.countNonZero(_rm))}")
                    except Exception:
                        pass
                if not self._fast_bubble_guard(image, _rm, region, True):
                    try:
                        _ink = MangaTranslator._ink_absorb_mask(
                            image, _rm, _polys_raw, band=26,
                            box=tuple([int(v) for v in region.rect]), levels=2)
                        if _ink is not None and np.any(_ink):
                            m = cv2.bitwise_or(m, _ink)
                            n_ok += 1
                            continue
                    except Exception:
                        pass
                    n_skip += 1
                    continue
                _ink2 = None
                try:
                    _ink2 = MangaTranslator._ink_absorb_mask(
                        image, _rm, _polys_raw, band=14,
                        box=tuple([int(v) for v in region.rect]), levels=3)
                except Exception:
                    _ink2 = None
                if _ink2 is not None and np.any(_ink2):
# همان قانونِ محفظهٔ باکنتراست برای مسیرِ
# پالی‌هایِ معمولی
# متنِ آزادِ گرادیانی هم ماسکِ تنگ
                    if self._ink_tight_ok(
                            image, _rm, _ink2, _polys_raw):
# همان قانونِ محفظهٔ تیره برای مسیرِ پالی‌ها
# force-box فقط برای زمینهٔ «تیره»
# پنجره‌هایِ آبیِ روشن ([SPECIAL CHANGES]) بلوکِ
# کامل نشوند — LaMaِ کلِ بلوک + اسنپ‌شاتِ کثیف
# (که هنوز متن دارد) = متنِ شبح. زمینهٔ روشن →
# مسیرِ عادی با ماسکِ سخاوتمند ∪ جوهر.
                        if (getattr(self, "use_lama", False)
                                and self._clean_level() != "fast"
                                and self._ink_bg_dark(image, _ink2)):
                            _rm = cv2.bitwise_or(_rm, _ink2)
                            try:
                                _ys2, _xs2 = np.nonzero(_rm)
                                self._lama_force_rect_boxes.append(
                                    [int(_xs2.min()), int(_ys2.min()),
                                     int(_xs2.max()) + 1,
                                     int(_ys2.max()) + 1,
                                     int(getattr(region, "id", -1))])
                            except Exception:
                                pass
                        elif getattr(self, "use_lama", False):
                            _rm = cv2.bitwise_or(_rm, _ink2)
                        else:
                            _rm = _ink2
                    elif self._free_text_tight_ok(
                            image, _rm, _ink2, _polys_raw):
                        _rm = _ink2
                    else:
                        _rm = cv2.bitwise_or(_rm, _ink2)
# متنِ روشن روی محفظهٔ تیره → اجباری LaMa
# «متنِ روشن» کافی نیست؛ زمینه هم باید
# واقعاً تیره باشد (_ink_bg_dark). حبابِ سفیدِ
# بزرگِ 01.jpg («THE VILLA'S POOL…») متنِ سره
# دارد ولی زمینه حباب «روشن» است → کولرِ
# _ink_is_light کلِ حباب را force-box می‌کرد و
# کامپوز، حباب را کلاً از عکسِ خرابِ اول می‌آورد.
                        if (getattr(self, "use_lama", False)
                                and self._clean_level() != "fast"
                                and self._ink_is_light(image, _ink2)
                                and self._ink_bg_dark(image, _ink2)):
                            try:
                                _ys2, _xs2 = np.nonzero(_rm)
                                self._lama_force_rect_boxes.append(
                                    [int(_xs2.min()), int(_ys2.min()),
                                     int(_xs2.max()) + 1,
                                     int(_ys2.max()) + 1,
                                     int(getattr(region, "id", -1))])
                            except Exception:
                                pass
# دیوارِ حباب/کادر از ماسک جدا شود
                try:
                    _rm = self._carve_structural_walls(
                        image, _rm, region, _polys_raw, ink_mask=_ink2)
                except Exception:
                    pass
                _rm = self._limit_mask_to_bubble(
                    image, _rm, region)
# ماسکِ تقریباً-کلِ-حبابِ-سفید → جوهرِ تنگ
                try:
                    _rm = self._white_bubble_tighten(image, _rm, _ink2)
                except Exception:
                    pass
                if _pad_k is not None:
                    _rm = self._pad_dilate_wall_safe(
                        _rm, image, region, _pad_k)
                m = cv2.bitwise_or(m, _rm)
                n_ok += 1
            else:
                try:
                    x, y, rw, rh = [int(v) for v in region.rect]
                    x0, y0 = max(0, x + 2), max(0, y + 2)
                    x1, y1 = min(w, x + rw - 2), min(h, y + rh - 2)
                    if x1 - x0 >= 6 and y1 - y0 >= 4:
                        _rm = np.zeros_like(m)
                        cv2.rectangle(_rm, (x0, y0), (x1, y1), 255, -1)
                        if not self._fast_bubble_guard(image, _rm, region, False):
                            n_skip += 1
                            continue
# دیوارِ حباب/کادر از ماسک جدا شود
                        try:
                            _rm = self._carve_structural_walls(
                                image, _rm, region, [])
                        except Exception:
                            pass
                        _rm = self._limit_mask_to_bubble(
                            image, _rm, region)
# مستطیلِ بدونِ پالی در حبابِ سفید → جوهرِ تنگ
                        try:
                            _rm = self._white_bubble_tighten(
                                image, _rm, None)
                        except Exception:
                            pass
                        if _pad_k is not None:
                            _rm = self._pad_dilate_wall_safe(
                                _rm, image, region, _pad_k)
                        m = cv2.bitwise_or(m, _rm)
                        n_ok += 1
                except Exception:
                    continue
# «پنلِ متنی» با استخراجِ ناقص (فقطِ اندروید —
# MANGA_TEXTPANEL): وقتی OCRِ گوشیِ قدیمی (ML Kitِ آن روز) خطهایِ
# یک بلوکِ
# متراکم را هرز/ناقص خوانده (صفحهٔ قانونیِ 700×11362)، نوارهایِ
# خط فقط تکههایی از متن را میپوشانند و حروفِ بینِ نوارها در
# خروجی زنده میمانند (متنِ نیمهپاک + لکه). اگر زمینهٔ بلوک
# روشن باشد و بیرونِ پالیها دهها گلیفِ جامانده دیده شود
# «فقطِ همان گلیفها» (دیلِ ۴px) به ماسکِ پاکسازی اضافه
# میشود — نه مستطیلِ توپر (LaMaِ بلوکِ کامل رویِ زمینهٔ عکسی
# توهمِ متن/نویز میسازد — بازتولیدِ A/B). کامپوزِ همتا همان
# گلیفها را از عکسِ پاکشده برمیگرداند. حبابِ کاملخوانده
# (بینِ پالیهاش گلیفِ جامانده ندارد) هرگز تریگر نمیشود.
# گیتِ پنلِ متنی پیشفرض رویِ «هر دو» پلتفرم روشن شد
# (env=0 خاموش): باقیماندهٔ گلیف بینِ نوارها رویِ PC هم «متنِ
# نیمه‌پاک» میسازد — همان گونه که فلسفهٔ میگوید.
# پنلِ متنی دوباره «فقطِ اندروید» (رفتارِ testm):
# رویِ PC با OCRِ کامل، گلیفِ جاماندهای بینِ نوارها وجود ندارد و
# آشکارسازِ گلیف، «هنرِ بینِ خطهایِ سند» (شیشه/برگ/قابِ پنجرهٔ
# 9.jpg و img4) را گلیف میپندارد → ۳۴هزارpx هنر به ماسکِ LaMa →
# حفرهٔ غول → پرِ مه‌آلود رویِ خودِ نوارها (شکایتِ «شبحِ خاکستری»).
# گلیفِ جاماندهٔ واقعیِ PC حالا از مسیرِ کاملِ donor (پالیِ کاملِ
# خطوطِ fail — ) پاک میشود؛ img4 با گیتِ خاموش حتی
# تمیزتر شد (تستِ مو‌به‌مو). MANGA_TEXTPANEL=1 برایِ اجبار.
        if _android_gate("MANGA_TEXTPANEL") and n_ok > 0:
            try:
                _pg = float(max(1, w * h))
                _n_tp = 0
                for _rg in regions:
                    if getattr(_rg, "kind", "") in ("promo", "sfx"):
                        continue
                    _polys = getattr(_rg, "ocr_polys", None) or []
                    if not _polys:
                        continue
                    try:
                        _rx, _ry, _rw, _rh = [int(v) for v in _rg.rect]
                    except Exception:
                        continue
                    if _rw < 60 or _rh < 40:
                        continue
                    if (_rw * _rh) > 0.06 * _pg or _rh > 0.12 * h:
                        continue
                    _pm = np.zeros((h, w), dtype=np.uint8)
                    for _p in _polys:
                        try:
                            _pp = np.asarray(
                                _p, dtype=np.float32).reshape(-1, 2)
                            if _pp.shape[0] >= 3:
                                cv2.fillPoly(
                                    _pm,
                                    [np.rint(_pp).astype(np.int32)], 255)
                        except Exception:
                            continue
                    if not int(_pm.sum()):
                        continue
                    _blk = np.zeros((h, w), dtype=np.uint8)
                    _blk[max(0, _ry):min(h, _ry + _rh),
                            max(0, _rx):min(w, _rx + _rw)] = 255
                    _cov = float(cv2.countNonZero(
                        cv2.bitwise_and(_pm, _blk))) / \
                        max(1.0, float(_rw * _rh))
                    if _cov > 0.90:
                        continue  # متن کامل خوانده شده — دست نمی‌زنیم
                    _pmd = cv2.dilate(_pm, np.ones((9, 9), np.uint8))
# med_hِ ناحیه برایِ سقفهایِ سازگار با
# فونتِ درشت (img6: بلندیِ خط ۶۹..۷۹)
                    _mh = 0.0
                    try:
                        _pl = []
                        for _p in _polys:
                            try:
                                _ppb = np.asarray(
                                    _p, dtype=np.float32).reshape(-1, 2)
                                if _ppb.shape[0] >= 3:
                                    _pl.append(_ppb)
                            except Exception:
                                continue
                        _ln = MangaTranslator._group_polys_to_lines(
                            _pl)
                        if _ln:
                            _mh = float(np.median(
                                [b[3] - b[1] for b in _ln]))
                    except Exception:
                        _mh = 0.0
                    _ink3 = MangaTranslator._panel_leftover_ink(
                        image, _rg.rect, _pmd, med_h=_mh)
                    if _ink3 is None:
                        continue
                    _ink3 = cv2.dilate(
                        _ink3, np.ones((9, 9), np.uint8))
                    m = cv2.bitwise_or(m, _ink3)
                    _n_tp += 1
                    if self.debug:
                        try:
                            print(
                                f"  [🔍] پنلِ متنی (گلیفِ جامانده "
                                f"n={int(cv2.countNonZero(_ink3))}px) → "
                                f"ماسکِ گلیف rect={(_rx, _ry, _rw, _rh)}")
                        except Exception:
                            pass
                if _n_tp and self.debug:
                    print(f"  [🔍] پنلِ متنی: {_n_tp} بلوکِ ناقص‌خوانده → "
                          f"گلیفهای جامانده به ماسک رفت")
            except Exception as _e2:
                if self.debug:
                    print("  [!] پنلِ متنی خطا:", _e2)
# پسگیرِ جوهرِ جامانده: قطعههایِ
# گلیفِ همسایهٔ ماسک که OCRِ ناقص بیرونِ پالی گذاشته
# ('Yo'/'th'/'a' — حبابِ چپبالای 01.jpg) به ماسک برمیگردند.
        #) — با env=0
# رویِ PC هم فعال شد (
# قابلِ خاموشکردن است.
        if (os.environ.get("MANGA_INK_RECLAIM", "1") != "0") \
                and n_ok > 0:
            try:
                _add = self._stray_ink_reclaim(image, m, regions)
                if _add is not None and np.any(_add):
                    m = cv2.bitwise_or(m, _add)
                    if self.debug:
                        try:
                            print(f"  [🔍]پسگیرِ جوهر: +"
                                  f"{int(cv2.countNonZero(_add))}px به ماسک")
                        except Exception:
                            pass
            except Exception:
                pass
        if n_ok <= 0 and n_skip <= 0:
            return None
# «بالنِ سیستم»: اینتریورِ باکسِ سیستم اینجا به ماسک
# اضافه «نمی‌شود» — پرِ فلتِ قطعیِ آن در clean_image انجام می‌شود
# (self._fill_system_box_interiors). چرا اینجا نه؟ ماسکِ کلِ
# اینتریور، گاردِ ضدتوهمِ LaMa (که به «حلقهٔ روشنِ دورِ ماسک»
# تکیه دارد) را کور می‌کند — حلقهٔ دورِ اینتریور = قابِ سیاهِ
# باکس است → خروجیِ تیرهٔ توهمیِ LaMa بدونِ اعتبارسنجی می‌ماند
# (لگهٔ سیاه — بازتولید در تستِ img1018).
        try:
            _dm2 = os.environ.get("MANGA_DUMP_MASK2")
            if _dm2:
                cv2.imwrite(_dm2, m)
        except Exception:
            pass
        return m

    @staticmethod
    def _ink_absorb_mask(image: np.ndarray, seed_mask: np.ndarray,
                         polys_raw: list, band: int = 14,
                         box: Optional[Tuple[int, int, int, int]] = None,
                         levels: int = 3) -> Optional[np.ndarray]:
        try:
            h, w = image.shape[:2]
            if not polys_raw:
                return None
            _all = np.concatenate(polys_raw, axis=0)
            px0, py0 = float(_all[:, 0].min()), float(_all[:, 1].min())
            px1, py1 = float(_all[:, 0].max()), float(_all[:, 1].max())
            if box is not None:
                try:
                    bx0, by0, bw0, bh0 = [int(v) for v in box]
                    px0, py0 = min(px0, bx0), min(py0, by0)
                    px1, py1 = max(px1, bx0 + bw0), max(py1, by0 + bh0)
                except Exception:
                    pass
            mg = 12
            wx0, wy0 = max(0, int(px0) - mg), max(0, int(py0) - mg)
            wx1, wy1 = min(w, int(px1) + mg), min(h, int(py1) + mg)
            if wx1 - wx0 < 12 or wy1 - wy0 < 12:
                return None
            g = cv2.cvtColor(image[wy0:wy1, wx0:wx1], cv2.COLOR_BGR2GRAY)
            med = float(np.median(g))
            dark = g < med - 55.0
            bright = None
            if med < 200.0:
                _thr_b = min(232.0, med + 55.0)
                _br = g > _thr_b
                if float(_br.mean()) <= 0.40:
                    bright = _br
            seed = seed_mask[wy0:wy1, wx0:wx1] > 0
            if not np.any(seed):
                return None
            _cands = []
            _dv = g[seed & dark]
            if _dv.size >= 30:
                _cands.append((abs(float(np.median(_dv)) - med), dark,
                               float(np.median(_dv))))
            if bright is not None:
                _bv = g[seed & bright]
                if _bv.size >= 30:
                    _cands.append((abs(float(np.median(_bv)) - med), bright,
                                   float(np.median(_bv))))
            if not _cands:
                return None
            _cands.sort(key=lambda t: -t[0])
            ink, _tone = _cands[0][1], _cands[0][2]
            if float(ink.mean()) > 0.55:
                return None
            n, lab, st, _ = cv2.connectedComponentsWithStats(
                ink.astype(np.uint8), connectivity=8)
            out = np.zeros_like(g, dtype=np.uint8)

            kb = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (2 * band + 1, 2 * band + 1))
            _cur_seed = seed.copy()
            _n_kept = 0
            _acap = min(max(0.35 * ink.size, 2.5 * float(seed.sum())),
                        0.8 * ink.size)
# «راهرویِ متن» — جذب فقط در همسایگیِ ناحیهٔ متن.
# راهرو = مستطیلِ ناحیه (بلوکِ متنِ detector/OCR) ∪ پالی‌ها.
# بدونِ این، جذبِ ۳ سطحی تا ~۴۲px از seed خز می‌کند و هنرِ
# نزدیک (موی/گونهٔ شخصیت کنارِ حباب) را می‌بلعد → پرکننده با
# رنگِ زمینه روی هنر نقاشی می‌کند.
# اما راهروِ «فقط پالی‌ها» هم غلط بود: وقتی OCR ناقص است (متنِ
# عمودیِ سفیدِ test2 — فقط ۱ گلیف شناسایی شد) خزشِ قانونیِ
# گلیف‌به‌گلیفِ داخلِ بلوکِ متن باید بماند → مستطیلِ ناحیه
# هم بخشی از راهرو است؛ هنرِ بیرونِ ناحیه محافظت می‌شود.
            _cor = None
            try:
                _co = np.zeros_like(g, dtype=np.uint8)
                _made = False
                _off = np.array([wx0, wy0], dtype=np.int32)
                for pp in (polys_raw or []):
                    try:
                        q = np.rint(np.asarray(pp, dtype=np.float32)).astype(
                            np.int32) - _off
                    except Exception:
                        continue
                    if q.shape[0] >= 3:
                        cv2.fillPoly(_co, [q], 255)
                        _made = True
                if box is not None:
                    try:
                        _bx0, _by0, _bw0, _bh0 = [int(v) for v in box]
                        _rx0, _ry0 = max(0, _bx0 - wx0), max(0, _by0 - wy0)
                        _rx1 = min(g.shape[1], _bx0 + _bw0 - wx0)
                        _ry1 = min(g.shape[0], _by0 + _bh0 - wy0)
                        if _rx1 > _rx0 and _ry1 > _ry0:
                            _co[_ry0:_ry1, _rx0:_rx1] = 255
                            _made = True
                    except Exception:
                        pass
                if _made:
                    _co = cv2.dilate(_co, cv2.getStructuringElement(
                        cv2.MORPH_ELLIPSE, (15, 15)))
                    _cor = _co > 0
            except Exception:
                _cor = None
            if _cor is None:
                _cor = cv2.dilate(seed.astype(np.uint8), kb) > 0
            for _lvl in range(max(1, levels)):
                seed_band = cv2.dilate(
                    _cur_seed.astype(np.uint8), kb) > 0
                _lvl_new = np.zeros_like(out, dtype=bool)
                _wh, _ww = g.shape[:2]
                for i in range(1, n):
                    a = int(st[i, cv2.CC_STAT_AREA])
                    if a < 12 or a > _acap:
                        continue
                    cy, cx = int(st[i, cv2.CC_STAT_TOP]), int(st[i, cv2.CC_STAT_LEFT])
                    ch, cw = int(st[i, cv2.CC_STAT_HEIGHT]), int(st[i, cv2.CC_STAT_WIDTH])
                    if (cx <= 1 or cy <= 1 or cx + cw >= _ww - 1
                            or cy + ch >= _wh - 1):
                        continue
                    comp = (lab[cy:cy + ch, cx:cx + cw] == i)
                    _sl3 = (slice(cy, cy + ch), slice(cx, cx + cw))
# کامپوننت باید عمدتاً داخلِ راهرویِ متن باشد
                    _cor_hit = int(np.count_nonzero(comp & _cor[_sl3]))
                    if _cor_hit <= 0 or _cor_hit < 0.30 * float(a):
                        continue
                    _elong = max(ch, cw) / max(1.0, float(min(ch, cw)))
                    _fill = a / float(max(1, ch * cw))
                    if _elong > 4.0 and _fill < 0.25:
                        continue
                    _touch = seed_band[_sl3] & comp
                    if not np.any(_touch):
                        if _tone is None:
                            continue
                        _vals = g[_sl3][comp]
                        if _vals.size < 12:
                            continue
                        if abs(float(np.median(_vals)) - _tone) > 55.0:
                            continue
                        if ch > 90 or cw > 0.85 * g.shape[1]:
                            continue
                    elif a > 200 and (float(np.count_nonzero(_touch)) / a) < 0.12:
                        continue
                    _sub = out[_sl3]
                    _sub[comp] = 255
                    _lvl_new[_sl3] |= comp
                    _n_kept += 1
                if not _lvl_new.any():
                    break
                _cur_seed = seed | (_lvl_new)
            if not _n_kept:
                return None
            full = np.zeros((h, w), dtype=np.uint8)
            full[wy0:wy1, wx0:wx1] = out
            full = cv2.morphologyEx(full, cv2.MORPH_CLOSE,
                                    np.ones((3, 3), np.uint8))
            return full
        except Exception:
            return None

    def _stray_ink_reclaim(self, image: np.ndarray,
                           page_mask: np.ndarray,
                           regions) -> Optional[np.ndarray]:
        """ — «پسگیرِ جوهرِ جامانده» (فقطِ اندروید — گیتِ
        MANGA_INK_RECLAIM).

        ریشهٔ «متن جا میمونه سمت چپِ حباب» (01.jpg، لاگِ گوشیِ
        ): پالیهایِ OCRِ ناقصِ آن روز ('ure' بهجایِ You're
        'neredl' بهجایِ the real، 'tractien' بهجایِ attraction) کادرِ
        ناحیه را از x=39 شروع میکنند در حالی که جوهرِ واقعیِ حباب از
        x=13 شروع میشود → حروفِ اولِ هر خط ('Yo'/'th'/'a') بیرونِ
        ماسکِ پاکسازی و بیرونِ نوارهایِ کامپوز میمانند و در خروجی
        برمیگردند. جارویِ بقایا هم نمیکشد چون دامنهٔ آن «فقط نوارهایِ
        متن» است.

        راهحل: بعد از ساختهشدنِ ماسکِ هر ناحیه، قطعههایِ همتونِ جوهرِ
        خودِ ناحیه که (۱) به ماسک چسبیده/نزدیکاند (باندِ ۰.۵×ارتفاعِ
        خط)، (۲) هماندازهٔ حرفاند (بعد و جرمِ ≤~۳ برابرِ گلیف)، (۳)
        داخلِ راهرویِ ناحیهاند (پالیها ∪ rect منبسط به ۱×ارتفاعِ خط —
        ضدِ خزش به هنرِ دور) و (۴) سقفِ کلِ جذبِ ۳۵٪ ماسکِ ناحیه را
        ندارند، پس گرفته میشوند. قطعههایِ بزرگ (هنر/دیوارِ حباب) با
        گاردهایِ بعد و جرم رد میشوند — درسِ (قطعهٔ هنرِ
        ca=5504).

        خروجی: «فقط الحاقیاتِ تازه» (ماسکِ صفحهکامل) یا None.
        PC بایت‌به‌بیت دست‌نخورده — فراخوانی فقط زیرِ _android_gate."""
        try:
            h, w = image.shape[:2]
        except Exception:
            return None
        if page_mask is None or not np.any(page_mask):
            return None
        out = None
        try:
            for region in regions:
                if getattr(region, "kind", "") in ("promo", "sfx"):
                    continue
                polys = []
                for p in (getattr(region, "ocr_polys", None) or []):
                    try:
                        pp = np.asarray(p, dtype=np.float32).reshape(-1, 2)
                    except Exception:
                        continue
                    if pp.shape[0] >= 3:
                        polys.append(pp)
                if not polys:
                    continue
                lines = MangaTranslator._group_polys_to_lines(polys)
                if not lines:
                    continue
                med_h = float(np.median([b[3] - b[1] for b in lines]))
                if med_h < 8.0:
                    continue
# رسا = ۰.۸×ارتفاعِ خط — شکافِ واقعیِ 01.jpg تا ۰.۶۷× بود
# ۰.۸ حاشیهٔ امن میدهد بدونِ رسیدن به هنرِ دور
                reach = int(min(40.0, max(12.0, 0.8 * med_h)))
                _all = np.concatenate(polys, axis=0)
                px0, py0 = float(_all[:, 0].min()), float(_all[:, 1].min())
                px1, py1 = float(_all[:, 0].max()), float(_all[:, 1].max())
                try:
                    rx, ry, rw2, rh2 = [float(v) for v in region.rect]
                    px0, py0 = min(px0, rx), min(py0, ry)
                    px1, py1 = max(px1, rx + rw2), max(py1, ry + rh2)
                except Exception:
                    pass
                wx0, wy0 = max(0, int(px0) - reach), max(0, int(py0) - reach)
                wx1, wy1 = min(w, int(px1) + reach), min(h, int(py1) + reach)
                if wx1 - wx0 < 12 or wy1 - wy0 < 12:
                    continue
                g = cv2.cvtColor(image[wy0:wy1, wx0:wx1], cv2.COLOR_BGR2GRAY)
                med = float(np.median(g))
                seed = page_mask[wy0:wy1, wx0:wx1] > 0
                if not np.any(seed):
                    continue
                dark = g < med - 55.0
                bright = None
                if med < 200.0:
                    _br = g > min(232.0, med + 55.0)
                    if float(_br.mean()) <= 0.40:
                        bright = _br
                _cands = []
                _dv = g[seed & dark]
                if _dv.size >= 30:
                    _cands.append(
                        (abs(float(np.median(_dv)) - med), dark))
                if bright is not None:
                    _bv = g[seed & bright]
                    if _bv.size >= 30:
                        _cands.append(
                            (abs(float(np.median(_bv)) - med), bright))
                if not _cands:
                    continue
                _cands.sort(key=lambda t: -t[0])
                ink = _cands[0][1]
                if float(ink.mean()) > 0.55:
                    continue
                n, lab, st, _ = cv2.connectedComponentsWithStats(
                    ink.astype(np.uint8), connectivity=8)
                _band = max(6, int(0.4 * med_h))
                _near = cv2.dilate(
                    seed.astype(np.uint8),
                    np.ones((2 * _band + 1, 2 * _band + 1), np.uint8)) > 0
# راهرو = پالیها ∪ rectِ ناحیه، منبسط به reach —
# جذب فقط در همسایگیِ بلوکِ متنِ خودِ ناحیه
                _cor = np.zeros(g.shape[:2], dtype=np.uint8)
                _off = np.array([wx0, wy0], dtype=np.int32)
                for pp in polys:
                    try:
                        q = np.rint(pp).astype(np.int32) - _off
                        if q.shape[0] >= 3:
                            cv2.fillPoly(_cor, [q], 255)
                    except Exception:
                        continue
                try:
                    _cx0 = max(0, int(px0) - wx0)
                    _cy0 = max(0, int(py0) - wy0)
                    _cx1 = min(g.shape[1], int(px1) - wx0)
                    _cy1 = min(g.shape[0], int(py1) - wy0)
                    if _cx1 > _cx0 and _cy1 > _cy0:
                        _cor[_cy0:_cy1, _cx0:_cx1] = 255
                except Exception:
                    pass
                _cor = cv2.dilate(
                    _cor, np.ones((2 * reach + 1, 2 * reach + 1), np.uint8))
                _cand2 = []
                _wh, _ww = g.shape[:2]
# گاردِ رنگ: قطعه باید همرنگِ جوهرِ خودِ ناحیه
# باشد (
# پسگیرِ ۲۰۶ رویِ img6 ضربهٔ صورتیِ SFXِ «あ» کنارِ متن را
# همتونِ حرف میپنداشت و به ماسکِ پاکسازی میبرد = حذفِ
# هنر). متنِ آبیِ تیره (هیو ~۱۱۰) و صورتیِ SFX (هیو ~۳۰۰)
# از رویِ فاصلهٔ هیو جدا میشوند؛ متنِ خاکستری/سیاه/سفید
# (اشباعِ کم) هرگز قطعهٔ اشباعِ رنگی نمیگیرد.
                _sub_bgr = image[wy0:wy1, wx0:wx1]
                _seed_ink = (seed & ink)
                _seed_h = _seed_s = None
                if int(np.count_nonzero(_seed_ink)) >= 30:
                    try:
                        _hsv = cv2.cvtColor(
                            _sub_bgr, cv2.COLOR_BGR2HSV)
                        _sv = _hsv[_seed_ink]
                        _seed_h = float(np.median(_sv[:, 0])) * 2.0
                        _seed_s = float(np.median(_sv[:, 1]))
                    except Exception:
                        _seed_h = _seed_s = None
                for ci in range(1, n):
                    ca = int(st[ci, cv2.CC_STAT_AREA])
                    if ca < 6 or ca > 2.5 * med_h * med_h:
                        continue
                    cwd = int(st[ci, cv2.CC_STAT_WIDTH])
                    chg = int(st[ci, cv2.CC_STAT_HEIGHT])
                    if cwd > 2.2 * med_h or chg > 2.2 * med_h:
                        continue
# قطعهٔ بریدهشده به مرزِ پنجره = ساختارِ بزرگِ ادامهدار
# (هنر/دیوار) → رد (همان گاردِ _ink_absorb_mask)
                    _cx = int(st[ci, cv2.CC_STAT_LEFT])
                    _cy = int(st[ci, cv2.CC_STAT_TOP])
                    if (_cx <= 1 or _cy <= 1
                            or _cx + cwd >= _ww - 1
                            or _cy + chg >= _wh - 1):
                        continue
                    _cm = (lab == ci)
                    if not bool((_cm & _near).any()):
                        continue
                    if not bool((_cm & (_cor > 0)).any()):
                        continue
# همرنگی با جوهرِ ناحیه (گاردِ رنگِ بالا)
# MANGA_RECLAIM_COLORGUARD=0 برایِ خاموشکردنِ دستی
                    if _seed_h is not None \
                            and os.environ.get(
                                "MANGA_RECLAIM_COLORGUARD", "1") != "0":
                        try:
                            _pc = _sub_bgr[_cm]
                            _ph = cv2.cvtColor(
                                _pc.reshape(-1, 1, 3).astype(
                                    np.uint8), cv2.COLOR_BGR2HSV)
                            _phh = float(np.median(_ph[:, 0, 0])) * 2.0
                            _phs = float(np.median(_ph[:, 0, 1]))
                            _hue_d = abs(_phh - _seed_h)
                            _hue_d = min(_hue_d, 360.0 - _hue_d)
# فقطِ عدمِتطابقِ «قوی»: آستانهٔ
# سختگیرانه (S≥۹۰ / هیو≥۷۰) تا قطعههایِ
# سفیدِ کمی-رنگگرفته (JPEG bleed رویِ پنل — img4)
# که متنِ واقعیاند رد نشوند (رگرسیونِ img4:
# گاردِ ساده نصفِ گلیفها را ازِ پسگیر میگرفت و
# پرِ LaMa را کلاً عوض میکرد).
                            if _phs > 120.0 and _seed_s < 45.0:
                                continue  # قطعهٔ رنگی، متنِ بی‌رنگ
                            if (_phs > 110.0 and _seed_s > 110.0
                                    and _hue_d > 70.0):
                                continue  # رنگِ غلط (SFX/هنرِ همسایه)
                        except Exception:
                            pass
# فقط «پیکسلِ تازه» (بیرونِ ماسکِ فعلی) شمرده شود —
# بازجذبِ خودِ متنِ ازقبل-ماسکشده هم سقف را پُر میکرد
# و دیلیتِ بعدی هالویِ بیفایده حولِ متن میداد
                    _new = int(np.count_nonzero(_cm & (~seed)))
                    if _new < 6:
                        continue
                    _cand2.append((_new, ci))
                _cand2.sort(key=lambda t: t[0])
                _cap = 0.35 * float(max(1, int(seed.sum())))
                _got = 0
                for ca, ci in _cand2:
                    if _got + ca > _cap:
                        break
                    _got += ca
                    if out is None:
                        out = np.zeros((h, w), dtype=np.uint8)
                    out[wy0:wy1, wx0:wx1][(lab == ci) & (~seed)] = 255
                if self.debug and _got > 0:
                    try:
                        print(f"  [🔍]پسگیرِ جوهر: ناحیهٔ "
                              f"{getattr(region, 'id', '?')} +{_got}px "
                              f"(رسا={reach}px، باند={_band}px)")
                    except Exception:
                        pass
        except Exception:
            return out
        if out is not None and np.any(out):
            out = cv2.dilate(out, np.ones((7, 7), np.uint8))
        return out

    @staticmethod
    def _absorb_block_neighbors(image: np.ndarray, mask: np.ndarray,
                                box: Tuple[int, int, int, int],
                                levels: int = 2,
                                band: int = 20) -> None:
        try:
            bx0, by0, bw, bh = [int(v) for v in box]
            bx1, by1 = bx0 + bw, by0 + bh
            H, W = mask.shape[:2]
            _win = max(140, 2 * band + 50)
            ex0, ey0 = max(0, bx0 - _win), max(0, by0 - _win)
            ex1, ey1 = min(W, bx1 + _win), min(H, by1 + _win)
            if ex1 - ex0 < 24 or ey1 - ey0 < 24:
                return
            sub = image[ey0:ey1, ex0:ex1]
            g = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(sub, cv2.COLOR_BGR2HSV)
            zmed = float(np.median(g))
            cand = ((g < zmed - 40.0) | (hsv[..., 1] >= 90))
            cand &= (mask[ey0:ey1, ex0:ex1] == 0)
            block_area = float(max(1.0, float(bw * bh)))
            cap = 0.60 * block_area
            added_total = 0
            _kern = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE,
                (2 * band + 1, 2 * band + 1))
            zh, zw = cand.shape
            for _lv in range(max(1, levels)):
                zone = np.zeros(cand.shape, dtype=bool)
                by0b = max(0, by0 - band - ey0)
                by1b = min(zh, by1 + band - ey0)
                bx0b = max(0, bx0 - band - ex0)
                bx1b = min(zw, bx1 + band - ex0)
                zone[by0b:by1b, bx0b:bx1b] = True
                grow = cv2.dilate(
                    (mask[ey0:ey1, ex0:ex1] > 0).astype(np.uint8),
                    _kern) > 0
                touch = zone & grow
                _nz, _lab, _st, _ = cv2.connectedComponentsWithStats(
                    cand.astype(np.uint8), 8)
                _added = 0
                _cands = []
                for _ci in range(1, _nz):
                    _ca = int(_st[_ci, cv2.CC_STAT_AREA])
                    if _ca < 40:
                        continue
                    _cx = int(_st[_ci, cv2.CC_STAT_LEFT])
                    _cy = int(_st[_ci, cv2.CC_STAT_TOP])
                    _cw = int(_st[_ci, cv2.CC_STAT_WIDTH])
                    _ch = int(_st[_ci, cv2.CC_STAT_HEIGHT])
                    if _cx <= 0 or _cy <= 0 or _cx + _cw >= zw or _cy + _ch >= zh:
                        continue
                    if not bool(((_lab[_cy:_cy + _ch, _cx:_cx + _cw] == _ci)
                                 & touch[_cy:_cy + _ch,
                                         _cx:_cx + _cw]).any()):
                        continue
                    _cands.append((_ca, _ci, _cx, _cy, _cw, _ch))
                _cands.sort(reverse=True)
                for _ca, _ci, _cx, _cy, _cw, _ch in _cands:
                    if _ca > 0.35 * block_area:
                        continue
                    if added_total + _ca > cap:
                        continue
                    _mind = min(_cw, _ch)
                    if _mind < 6 or (max(_cw, _ch)
                                     / float(max(1, _mind))) > 7.0:
                        continue
                    if _ca / float(max(1, _cw * _ch)) < 0.20:
                        continue
                    mask[ey0:ey1, ex0:ex1][_lab == _ci] = 255
                    _added += _ca
                    added_total += _ca
                if not _added:
                    break
        except Exception:
            pass

    def _line_instant_fill(self, image: np.ndarray, cleaned: np.ndarray,
                              regions: List[TextRegion],
                              mask: np.ndarray,
                              skip_ids=None) -> int:
        n_fill = 0
        try:
            h, w = image.shape[:2]
            _gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            _gx_full = cv2.Sobel(_gray, cv2.CV_32F, 1, 0, ksize=3)
            _gy_full = cv2.Sobel(_gray, cv2.CV_32F, 0, 1, ksize=3)
            _grad_full = cv2.magnitude(_gx_full, _gy_full)
        except Exception:
            return 0
        for region in regions:
# ناحیهٔ donor-گسترش‌یافته: پرِ فوری نگیرد (حالتِ کیفی)
            if skip_ids and int(getattr(region, "id", -1)) in skip_ids:
                continue
# بنرِ تبلیغ (promo) با پرکنندهٔ فوریِ خطی دست‌کاری
# نشود: پرِ فوریِ نوارِ متنِ بنر + کِیلِ ماسک = حفره در ماسکِ
# توپرِ بنر → LaMa متنِ بنر را نمی‌بیند → «ASURASCANS.COM» در
# خروجی می‌ماند (بازتولیدِ سندباکس). بنر فقط با ماسکِ توپر +
# LaMa/فال‌بک پاک می‌شود.
            if getattr(region, "kind", "") == "promo":
                continue
            for poly in (getattr(region, "ocr_polys", None) or []):
                try:
                    pp = np.asarray(poly, dtype=np.float32).reshape(-1, 2)
                except Exception:
                    continue
                if pp.shape[0] < 3:
                    continue
                try:
                    c = pp.mean(axis=0)
                    ring_pts = []
                    n_pts = pp.shape[0]
                    for i in range(n_pts):
                        a = pp[i]
                        b = pp[(i + 1) % n_pts]
                        seg = float(np.hypot(*(b - a)))
                        n_s = max(2, int(round(seg / 6.0)))
                        for t in np.linspace(0.0, 1.0, n_s, endpoint=False):
                            ring_pts.append(a + (b - a) * t)
                    ring_pts = np.asarray(ring_pts, dtype=np.float32)

                    def _sample(scale):
                        rs = c + (ring_pts - c) * scale
                        xs = np.clip(np.rint(rs[:, 0]), 0, w - 1).astype(np.int32)
                        ys = np.clip(np.rint(rs[:, 1]), 0, h - 1).astype(np.int32)
                        return image[ys, xs].astype(np.float32)

                    def _sample_xy(scale):
                        rs = c + (ring_pts - c) * scale
                        xs = np.clip(np.rint(rs[:, 0]), 0, w - 1).astype(np.int32)
                        ys = np.clip(np.rint(rs[:, 1]), 0, h - 1).astype(np.int32)
                        return xs, ys, image[ys, xs].astype(np.float32)

                    fill_col = None
                    fill_exp = 1.0
                    fill_plane = None  # پرِ صفحهٔ گرادیانی
                    _xs1, _ys1, r1 = _sample_xy(1.025)
                    if r1.shape[0] >= 12:
                        avg1 = r1.mean(axis=0)
                        dev1 = np.sqrt(((r1 - avg1[None, :]) ** 2).sum(axis=1))
                        if float((dev1 <= 15.0).mean()) >= 0.99:
                            fill_col = avg1
                            fill_exp = 1.05
# پرِ صفحه (plane) بهجایِ رنگِ تخت
                            #): حلقهٔ تنگِ ۲.۵٪
# رویِ گرادیانِ آرام (
# رویِ گرادیانِ آرام «یکدست» از آب میآید (dev≤۱۵)
# ولی هر خط رنگِ محلیِ خودش را میگیرد → خطوطِ
# چسبیده با رنگهایِ ناهمسان = پلههایِ روی-هم. اگر
# حلقه به صفحهٔ (x,y) خوب بچسبد و نوسانِ رنگیِ
# داخلِ پالی معنادار باشد (≥۸)، پالی با همان
# صفحه پر میشود — گرادیان پیوسته، بدونِ پله.
                            try:
                                if (float(_ys1.max() - _ys1.min()) >= 20
                                        and r1.shape[0] >= 24):
                                    _A = np.stack([
                                        np.ones(r1.shape[0], np.float32),
                                        _xs1.astype(np.float32),
                                        _ys1.astype(np.float32)], axis=1)
                                    _coefs, *_ = np.linalg.lstsq(
                                        _A, r1, rcond=None)
                                    _pred = _A @ _coefs
                                    _resid = np.sqrt(((_pred - r1) ** 2)
                                                     .sum(axis=1))
                                    if float(np.mean(_resid)) <= 12.0:
                                        _bx = float(np.abs(_coefs[1]).max())
                                        _by = float(np.abs(_coefs[2]).max())
                                        _pw_ = float(pp[:, 0].max()
                                                     - pp[:, 0].min())
                                        _ph_ = float(pp[:, 1].max()
                                                     - pp[:, 1].min())
                                        if (_bx * _pw_ + _by * _ph_) >= 8.0:
                                            fill_plane = _coefs
                            except Exception:
                                fill_plane = None
# حلقهٔ تنگِ «نایکنواخت» هم صفحهای
# سنجیده میشود: پنجرهٔ سیستمِ 4e2e77
# («[CLEAR OBJECTIVE…]» رویِ گرادیانِ آبی):
# حلقهٔ تنگ رویِ گرادیانِ اشباع هیچ‌وقت dev≤۱۵
# نمیشود (۷۰-۴۵٪ نمونهها بیرونند) و حلقهٔ پهن
# (۱.۱×) به هنرِ بیرونِ پنل می‌رسد (resid=۱۱.۲ > ۱۰)
# → هیچ صفحهای پر نمیشد → خط به LaMa میفتاد →
# LaMa-manga (سیاهوسفید) رویِ آبیِ اشباع پرِ تختِ
# تیره + شبحِ سفیدِ حروف میگذاشت (لگهٔ مستطیلیِ
# تیره + متنِ قبلی — گزارشِ سازنده). صفحهٔ خودِ
# حلقهٔ تنگ (resid≤۱۰ پس از حذفِ ۲۰٪ بدترین
# نمونهها) همین گرادیان را پیوسته بازسازی میکند.
                        if fill_col is None and fill_plane is None \
                                and r1.shape[0] >= 24 \
                                and float(_ys1.max() - _ys1.min()) >= 20:
                            try:
                                _A2 = np.stack([
                                    np.ones(r1.shape[0], np.float32),
                                    _xs1.astype(np.float32),
                                    _ys1.astype(np.float32)], axis=1)
                                _c, *_ = np.linalg.lstsq(
                                    _A2, r1, rcond=None)
                                _p = _A2 @ _c
                                _r = np.sqrt(
                                    ((_p - r1) ** 2).sum(axis=1))
                                _rs = np.sort(_r)
                                _k = max(8, int(_rs.shape[0] * 0.8))
                                if float(_rs[:_k].mean()) <= 10.0:
                                    _bx2 = float(np.abs(_c[1]).max())
                                    _by2 = float(np.abs(_c[2]).max())
                                    _pw = float(pp[:, 0].max()
                                                   - pp[:, 0].min())
                                    _ph = float(pp[:, 1].max()
                                                   - pp[:, 1].min())
                                    if (_bx2 * _pw
                                            + _by2 * _ph) >= 8.0:
                                        fill_plane = _c
                                        fill_col = avg1
                                        fill_exp = 1.05
                            except Exception:
                                fill_plane = None
                    if fill_col is None:
                        if self._clean_level() != "fast":
# پرِ صفحهٔ گرادیانی برایِ حلقهٔ
# «نایکنوخت ولی صاف»: پنجرههایِ UIِ وبتون
# (کارتِ آبیِ [CLEAR OBJECTIVE]…) گرادیانِ آرامِ
# رنگی دارند — حلقهٔ تنگ یکدست نیست (ردِ dev≤۱۵)
# و خوشه به TELEA/LaMa میافتد: TELEA پخشِ
# ناهمسان میسازد و LaMa-manga (مدلِ سیاهوسفیدِ
# مانگا) رویِ گرادیانِ اشباع لکهٔ خاکستریِ
# خیشامی میسازد («کوه»/گِل). اگر حلقهٔ پهن‌تر
# (۱.۱×) به «صفحهٔ» (x,y) با خطایِ کم بچسبد
# (resid≤۱۰) همان صفحه پالی را پر میکند —
# بازسازیِ دقیقِ گرادیان، بدونِ لکه.
                            try:
                                _xs2g, _ys2g, r2g = _sample_xy(1.10)
                                if (r2g.shape[0] >= 40
                                        and float(_ys2g.max()
                                                 - _ys2g.min()) >= 40):
                                    _Ag = np.stack([
                                        np.ones(r2g.shape[0], np.float32),
                                        _xs2g.astype(np.float32),
                                        _ys2g.astype(np.float32)], axis=1)
                                    _cg, *_ = np.linalg.lstsq(
                                        _Ag, r2g, rcond=None)
                                    _pg = _Ag @ _cg
                                    _rg = np.sqrt(((_pg - r2g) ** 2)
                                                  .sum(axis=1))
# پسِ مقاوم: ۲۵٪ بدترین
# نمونهها (هنرِ بیرونِ پنل/لبهٔ قاب)
# خطایِ میانگین را کور میکرد (۴e2e77:
# mean=11.2 رد، بدونِ کانیوت=۸.۶)
                                    _rgs = np.sort(_rg)
                                    _kg = max(12, int(
                                        _rgs.shape[0] * 0.75))
                                    if float(_rgs[:_kg].mean()) <= 10.0:
                                        _bxg = float(np.abs(_cg[1]).max())
                                        _byg = float(np.abs(_cg[2]).max())
                                        _pwg = float(pp[:, 0].max()
                                                     - pp[:, 0].min())
                                        _phg = float(pp[:, 1].max()
                                                     - pp[:, 1].min())
                                        if (_bxg * _pwg + _byg * _phg) >= 6.0:
                                            fill_plane = _cg
                                            fill_col = r2g.mean(axis=0)
                                            fill_exp = 1.05
                            except Exception:
                                fill_plane = None
                        if fill_col is None:
                            _xs2f, _ys2f, r2 = _sample_xy(1.10)
                            if r2.shape[0] >= 16:
                                avg2 = r2.mean(axis=0)
                                dev2 = np.sqrt(((r2 - avg2[None, :]) ** 2).sum(axis=1))
                                _close = dev2 <= 35.0
                                if float(_close.mean()) >= 0.75:
                                    _cls_px = r2[_close]
                                    _xs2 = np.clip(np.rint(
                                        (c + (ring_pts - c) * 1.10)[:, 0]),
                                        0, w - 1).astype(np.int32)
                                    _ys2 = np.clip(np.rint(
                                        (c + (ring_pts - c) * 1.10)[:, 1]),
                                        0, h - 1).astype(np.int32)
                                    _g2 = _grad_full[_ys2, _xs2].astype(np.float32)[_close]
                                    if _g2.size >= 16:
                                        if float(np.median(_g2)) > 22.0:
                                            continue
                                    _s2 = _hsv[..., 1][_ys2, _xs2].astype(np.float32)[_close]
                                    if float(np.median(_s2)) > 60.0:
                                        continue
                                    if float(_s2.std()) > 30.0:
                                        continue
# گاردِ شیبِ عمودی: حلقهٔ
# «آسمان/گرادیان» که بالا و پایینش
# ناهمسان است (>۱۶ کانالِ) با رنگِ تخت
# پر نشود — پرِ فوریِ تختِ هر خط با
# میانگینِ حلقه = نوارِ شیریِ بی‌بافت
# (لگهٔ سفیدِ img4 — آسمانِ ابری).
# چنین خطی به LaMa/TELEA واگذار میشود.
                                    try:
                                        _ym = float(np.median(
                                            _ys2f[_close]))
                                        _top = _close & (_ys2f <= _ym)
                                        _bot = _close & (_ys2f > _ym)
                                        if int(_top.sum()) >= 8 \
                                                and int(_bot.sum()) >= 8:
                                            _mt = np.median(
                                                r2[_top], axis=0)
                                            _mb = np.median(
                                                r2[_bot], axis=0)
                                            if float(np.abs(
                                                    _mt - _mb).max()) \
                                                    > 16.0:
                                                continue
                                    except Exception:
                                        pass
                                    fill_col = np.median(_cls_px, axis=0)
                                    fill_exp = 1.10
                    if fill_col is None:
                        continue
                    fill_col = tuple(int(min(255, max(0, round(v))))
                                     for v in fill_col)
                    fill_pts = np.rint(
                        c + (pp - c) * fill_exp).astype(np.int32)
                    if fill_plane is not None:
                        try:
                            _pm = np.zeros(cleaned.shape[:2], np.uint8)
                            cv2.fillPoly(_pm, [fill_pts], 255)
                            _fy, _fx = np.nonzero(_pm)
                            if _fx.size:
                                for _ch in range(3):
                                    _vals = (fill_plane[0, _ch]
                                             + fill_plane[1, _ch] * _fx
                                             + fill_plane[2, _ch] * _fy)
                                    cleaned[_fy, _fx, _ch] = np.clip(
                                        np.rint(_vals), 0, 255).astype(np.uint8)
                                n_fill += 1
                                continue
                        except Exception:
                            pass
                    cv2.fillPoly(cleaned, [fill_pts], fill_col)
                    n_fill += 1
                except Exception:
                    continue
        return n_fill

    def _build_text_mask(self, image: np.ndarray, regions: List[TextRegion]) -> np.ndarray:

        if (os.environ.get("MANGA_FAST_MASK", "1") != "0"
                and not getattr(self, "erase_bubble_interior", False)):
            _fm = self._build_text_mask_fast(image, regions)
            if _fm is not None:
                return _fm

        h_img, w_img = image.shape[:2]
        text_mask = np.zeros((h_img, w_img), dtype=np.uint8)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        padding = max(0, int(getattr(self, "mask_padding", 3)))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * padding + 1,) * 2)

        for region in regions:
            x, y, rw, rh = region.rect
            polys = list(getattr(region, "ocr_polys", None) or [])
            if polys:
                pts = np.concatenate([np.asarray(p).reshape(-1, 2) for p in polys])
                x, y = min(x, pts[:, 0].min()), min(y, pts[:, 1].min())
                right = max(region.rect[0] + rw, pts[:, 0].max() + 1)
                bottom = max(region.rect[1] + rh, pts[:, 1].max() + 1)
            else:
                right, bottom = x + rw, y + rh
            x0 = max(0, int(x) - padding)
            y0 = max(0, int(y) - padding)
            x1 = min(w_img, int(right) + padding)
            y1 = min(h_img, int(bottom) + padding)
            if x1 - x0 < 8 or y1 - y0 < 8:
                continue
            _fill_poly = None
            try:
                _angs = float(getattr(region, "angle", 0.0) or 0.0)
            except Exception:
                _angs = 0.0
            if _angs != _angs or _angs in (float("inf"), float("-inf")):
                _angs = 0.0
            if abs(_angs) >= 8.0:
                _th = np.radians(_angs)
                _c, _s = float(np.cos(_th)), float(np.sin(_th))
                _den = _c * _c - _s * _s
                if _den > 0.05:
                    _bx, _by, _bw, _bh = [float(v) for v in region.rect]
                    _ws = (_bw * _c - _bh * _s) / _den
                    _hs = (_bh * _c - _bw * _s) / _den
                    if 16 < _ws < (_bw + _bh) and 8 < _hs < (_bw + _bh):
                        _c0 = np.array([_bx + _bw / 2.0, _by + _bh / 2.0], dtype=np.float32)
                        _u = np.array([_c, _s], dtype=np.float32)
                        _v = np.array([-_s, _c], dtype=np.float32)
                        _hw = _ws * 0.5 + max(8.0, _ws * 0.06)
                        _hh = _hs * 0.5
                        _corners = [
                            _c0 + _hw * _u + _hh * _v,
                            _c0 - _hw * _u + _hh * _v,
                            _c0 - _hw * _u - _hh * _v,
                            _c0 + _hw * _u - _hh * _v,
                        ]
                        _fill_poly = np.rint(np.stack(_corners)).astype(np.int32)
                        _pb = _fill_poly
                        x0 = max(0, min(int(x0), int(_pb[:, 0].min()) - 2))
                        y0 = max(0, min(int(y0), int(_pb[:, 1].min()) - 2))
                        x1 = min(w_img, max(int(x1), int(_pb[:, 0].max()) + 3))
                        y1 = min(h_img, max(int(y1), int(_pb[:, 1].max()) + 3))

            zone = self._text_zone_in_crop(region, x0, y0, x1, y1)
            ch, cw = y1 - y0, x1 - x0
            det_class = (getattr(region, "det_class", "") or "")
            ink = zone
            if ink is not None and det_class not in ("bubble", "text_bubble"):
                try:
                    _gz = self._glyph_mask_in_zone(gray[y0:y1, x0:x1], ink)
                    if _gz is not None:
                        ink = _gz
                except Exception:
                    pass
            if getattr(self, "erase_bubble_interior", False) and zone is not None and det_class in ("bubble", "text_bubble"):
                interior = self._bubble_interior_mask(gray[y0:y1, x0:x1], zone)
                if interior is not None and interior.max() > 0:
                    ink = interior
            elif zone is not None and det_class in ("bubble", "text_bubble"):
                try:
                    extra = self._ink_mask_inside_bubble(gray, x0, y0, x1, y1)
                    extra = self._drop_non_text_components(extra, ch, cw)
                    extra = self._protect_bubble_wall(extra, gray[y0:y1, x0:x1])
                    _domain = self._bubble_interior_mask(gray[y0:y1, x0:x1], zone)
                    if _domain is not None and _domain.max() > 0:
                        extra = cv2.bitwise_and(extra, _domain)
                    else:
                        _zn = cv2.dilate(zone, np.ones((9, 9), np.uint8), iterations=1)
                        extra = cv2.bitwise_and(extra, _zn)
                    extra_area = int(np.count_nonzero(extra))
                    if 0 < extra_area <= 0.30 * ch * cw:
                        ink = cv2.bitwise_or(ink, extra)
                except Exception:
                    pass
            if ink is None:

                ink = self._ink_mask_inside_bubble(gray, x0, y0, x1, y1)
                ink = self._drop_non_text_components(ink, ch, cw)
                ink = self._protect_bubble_wall(ink, gray[y0:y1, x0:x1])
                if np.count_nonzero(ink) > 0.45 * ch * cw:
                    try:
                        _zfull = np.full((ch, cw), 255, dtype=np.uint8)
                        _gz0 = self._glyph_mask_in_zone(gray[y0:y1, x0:x1], _zfull)
                        if (_gz0 is not None
                                and 60 <= int(np.count_nonzero(_gz0))
                                <= 0.45 * ch * cw):
                            ink = _gz0
                    except Exception:
                        pass
                if np.count_nonzero(ink) > 0.45 * ch * cw:
                    continue
            if _fill_poly is not None:
                _ink_t = self._tilted_ink_mask(gray, x0, y0, x1, y1,
                                               _fill_poly, _angs)
                _fill = np.zeros((y1 - y0, x1 - x0), dtype=np.uint8)
                cv2.fillPoly(_fill, [_fill_poly - np.array([x0, y0], dtype=np.int32)], 255)
                if _ink_t is not None and int(np.count_nonzero(_ink_t)) >= 60:
                    _fill = _ink_t
                else:
                    try:
                        _gz = self._glyph_mask_in_zone(gray[y0:y1, x0:x1], _fill)
                        if _gz is not None and int(np.count_nonzero(_gz)) >= 60:
                            _fill = _gz
                        elif ink is not None and np.count_nonzero(ink):
                            _tight = cv2.bitwise_and(
                                _fill,
                                cv2.dilate(ink, np.ones((7, 7), np.uint8), iterations=1))
                            if int(np.count_nonzero(_tight)) >= 60:
                                _fill = _tight
                    except Exception:
                        pass
                ink = cv2.bitwise_or(ink, _fill) if ink is not None else _fill
            if padding:
                ink = cv2.dilate(ink, kernel)
            text_mask[y0:y1, x0:x1] = cv2.bitwise_or(text_mask[y0:y1, x0:x1], ink)

        return text_mask

    def _tilted_ink_mask(self, gray: np.ndarray, x0: int, y0: int, x1: int, y1: int,
                         poly_abs: np.ndarray, ang: float) -> Optional[np.ndarray]:
        try:
            crop = gray[y0:y1, x0:x1]
            ch, cw = crop.shape[:2]
            if crop.size == 0 or ch < 8 or cw < 8:
                return None
            quad = np.rint(poly_abs).astype(np.int32) - np.array([x0, y0], dtype=np.int32)
            solid = np.zeros((ch, cw), dtype=np.uint8)
            cv2.fillPoly(solid, [quad], 255)
            if int(np.count_nonzero(solid)) < 120:
                return None
            _c0 = quad.reshape(-1, 2).mean(axis=0)
# علامتِ + برایِ همسطح‌سازی (قراردادِ مشترک با deskew و
# نوارهایِ چرخیده؛ قبلاً -ang کجی را دوبرابر می‌کرد)
            M = cv2.getRotationMatrix2D((float(_c0[0]), float(_c0[1])), float(ang), 1.0)
            _cos, _sin = abs(M[0, 0]), abs(M[0, 1])
            nw = int(ch * _sin + cw * _cos) + 2
            nh = int(ch * _cos + cw * _sin) + 2
            M[0, 2] += (nw / 2.0) - float(_c0[0])
            M[1, 2] += (nh / 2.0) - float(_c0[1])
            rot = cv2.warpAffine(crop, M, (nw, nh),
                                 flags=cv2.INTER_NEAREST, borderValue=255)
            rot_solid = cv2.warpAffine(solid, M, (nw, nh),
                                       flags=cv2.INTER_NEAREST, borderValue=0)
            vals = rot[rot_solid > 0]
            if vals.size < 80:
                return None
            med = float(np.median(vals))
            ink = ((rot < min(med - 35.0, 170.0)) & (rot_solid > 0)).astype(np.uint8) * 255
            ink = self._drop_non_text_components(ink, nh, nw)
            n_ink = int(np.count_nonzero(ink))
            n_zone = int(np.count_nonzero(rot_solid > 0))
            if n_ink < 60 or n_ink > 0.55 * n_zone:
                return None
            Minv = cv2.invertAffineTransform(M)
            back = cv2.warpAffine(ink, Minv, (cw, ch),
                                  flags=cv2.INTER_NEAREST, borderValue=0)
            out = ((back > 0) & (solid > 0)).astype(np.uint8) * 255
            if int(np.count_nonzero(out)) < 60:
                return None
            return out
        except Exception:
            return None

    @staticmethod
    def _glyph_mask_in_zone(crop_gray: np.ndarray,
                            zone: np.ndarray) -> Optional[np.ndarray]:
        try:
            z = (zone > 0)
            zc = int(z.sum())
            if zc < 200:
                return None
            bg = cv2.medianBlur(crop_gray, 31)
            diff = cv2.absdiff(crop_gray, bg)
            g = ((diff > 26) & z).astype(np.uint8) * 255
            g = cv2.morphologyEx(g, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
            n, lab, st, _ = cv2.connectedComponentsWithStats(
                (g > 0).astype(np.uint8), 8)
            if n > 1:
                keep = np.zeros_like(g)
                for i in range(1, n):
                    if int(st[i, cv2.CC_STAT_AREA]) >= 20:
                        keep[lab == i] = 255
                if int(np.count_nonzero(keep)) >= 120:
                    g = keep
            cov = float(np.count_nonzero(g)) / float(zc)
            if cov < 0.06 or cov > 0.92:
                return None
            return g
        except Exception:
            return None

    @staticmethod
    def _flat_fill_uniform(crop_img: np.ndarray,
                           crop_msk: np.ndarray) -> Optional[np.ndarray]:
        try:
            m = crop_msk > 0
            if not m.any():
                return None
# حلقهٔ نزدیک (۲-۵px بیرونِ ماسک) رنگِ واقعیِ زمینهٔ
# چسبیده به متن است — هم برای حبابِ سفید و هم بنرِ سیاه. (تغییرِ
# حلقهٔ دورترِ آزمایشی حباب روی بنرِ تیره را خراب می‌کرد → حذف.)
            ring = (cv2.dilate(crop_msk, np.ones((5, 5), np.uint8)) > 0) & (~m)
            n_ring = int(np.count_nonzero(ring))
            if n_ring < 40:
                return None
            rp = crop_img[ring].astype(np.int16)
            med = np.median(rp, axis=0)
            d = np.abs(rp - med[None, :]).max(axis=1)
# نسخهٔ «مدِ غالبِ bimodal» حذف شد — روی هنر با
# زمینهٔ روشنِ پراکنده هم پاس می‌شد و پرکردنِ خاکستری روی هنر
# می‌ساخت. بنرها الان توسط _enclosure_instant_fill پاک می‌شوند
# و این تابع مثل قبل فقط حلقهٔ یکدست را می‌پذیرد.
            if float((d <= 20).mean()) < 0.96:
                return None
            sel = rp[d <= 22]
            fill = np.median(sel, axis=0) if sel.shape[0] >= 30 else med
            out = crop_img.copy()
            out[m] = np.clip(fill, 0, 255).astype(np.uint8)
            return out
        except Exception:
            return None

    @staticmethod
    def _color_fill_cluster(crop_img: np.ndarray,
                            crop_msk: np.ndarray) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        try:
            m = crop_msk > 0
            if not m.any():
                return None
            ring = (cv2.dilate(crop_msk, np.ones((9, 9), np.uint8)) > 0) & (~m)
            if int(np.count_nonzero(ring)) < 60:
                return None
            hsv = cv2.cvtColor(crop_img, cv2.COLOR_BGR2HSV)
            sat = hsv[..., 1][ring].astype(np.float32)
            if float(np.median(sat)) < 75.0:
                return None
            g = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
            gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
            grad = cv2.magnitude(gx, gy)[ring]
            if float(np.median(grad)) > 24.0:
                return None
            #): TELEA روی
# گاردِ گرادیان (
# زمینهٔ «گرادیانیِ رنگی» (کارت/پنجرهٔ آبیِ وبتون) از هر طرف
# با رنگِ متفاوت پخش میکند → لکهٔ همگام‌نشده + دایلِ ماسک تا
# ۲۵px رویِ خطِ بعدی = پلههایِ روی-هم‌افتاده («کوه»). حلقه اگر
# پهنایِ رنگیِ قابلِ دیدن دارد (p90-p10 ≥ ۱۶ در یک کانال —
# نوارِ متنِ پنجرهٔ [CLEAR OBJECTIVE] با گرادیانِ ~۲۰ واحدی
# همین‌جا از آستانهٔ اولیهٔ ۲۸ رد میشد و نوارِ ۵۰-واحدیِ
# روشن میساخت) یعنی گرادیان است، نه رنگِ تخت → رد میشود تا
# خوشه به LaMa برود. MANGA_COLOR_TELEA=1 برایِ برگشتِ دستی.
            if os.environ.get("MANGA_COLOR_TELEA", "0") != "1":
                try:
                    _rp = crop_img[ring].astype(np.int16)
                    if _rp.shape[0] >= 120:
                        _spread = float(np.max(
                            np.percentile(_rp, 90, axis=0)
                            - np.percentile(_rp, 10, axis=0)))
                        if _spread >= 16.0:
                            return None
                except Exception:
                    pass
            try:
                _thick = float(cv2.distanceTransform(
                    m.astype(np.uint8), cv2.DIST_L2, 3).max())
            except Exception:
                _thick = 4.0
            _kd = int(np.clip(2 * int(round(max(3.0, _thick * 0.75))) + 1, 9, 25))
            kk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (_kd, _kd))
            dil = cv2.morphologyEx(cv2.dilate(crop_msk, kk, iterations=1),
                                   cv2.MORPH_CLOSE, kk)
            out = cv2.inpaint(crop_img, dil, 5, cv2.INPAINT_TELEA)
            return dil, out
        except Exception:
            return None

    @staticmethod
    def _paper_fill_cluster(crop_img: np.ndarray,
                            crop_msk: np.ndarray) -> Optional[np.ndarray]:
        try:
            m = crop_msk > 0
            if not m.any():
                return None
            R = (cv2.dilate(crop_msk, np.ones((15, 15), np.uint8)) > 0) & (~m)
            n_R = int(np.count_nonzero(R))
            if n_R < 200:
                return None
            px = crop_img[R].astype(np.float32)
            if not np.isfinite(px).all():
                return None
            _WB, _WG, _WR = 0.114, 0.587, 0.299
            with np.errstate(invalid="ignore", over="ignore"):
                _lum = px[:, 0] * _WB + px[:, 1] * _WG + px[:, 2] * _WR
            _lit = _lum >= 190.0
            n_lit = int(np.count_nonzero(_lit))
            if n_lit < 200 or n_lit < 0.60 * n_R:
                return None
            hsv = cv2.cvtColor(crop_img, cv2.COLOR_BGR2HSV)
            _sat_lit = hsv[..., 1][R].astype(np.float32)[_lit]
            if float(np.median(_sat_lit)) > 60.0:
                return None
            g = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
            gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
            _grad_lit = cv2.magnitude(gx, gy)[R][_lit]
            if float(np.median(_grad_lit)) > 18.0:
                return None
            anchor = np.median(px[_lit], axis=0)
            out = crop_img.copy()
            out[m] = np.clip(np.rint(anchor), 0, 255).astype(np.uint8)
            return out
        except Exception:
            return None

    def _flat_fill_cluster(self, crop_img: np.ndarray, crop_msk: np.ndarray,
                           light_ring: bool = False,
                           fit_tol: float = 6.0) -> Optional[np.ndarray]:
        m = crop_msk > 0
        if not m.any():
            return None
        ring = cv2.dilate(crop_msk, np.ones((9, 9), np.uint8)) > 0
        ring &= ~m
        if light_ring:
# اندروید/حفرهٔ بزرگِ کنارِ هنر: حلقه ممکن است
# اقلیتِ «دیوار/کاغذِ روشن» + اقلیتِ هنرِ تیره داشته باشد
# (بلوکِ متنِ چسبیده به صحنه)؛ fit فقط از پیکسلهایِ روشنِ
# حلقه — نتیجه: پرِ دیوارِ یکدست بدونِ آلودگیِ هنرِ تیره.
# (پیشفرض light_ring=False → رفتارِ PC بیت‌به‌بیت همان است)
            try:
                _gl = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
                ring &= (_gl >= 170.0)
            except Exception:
                return None
        if int(np.count_nonzero(ring)) < 60:
            return None
        ring_px = crop_img[ring].astype(np.float32)

        if not np.isfinite(ring_px).all():
            return None
        _WB, _WG, _WR = 0.114, 0.587, 0.299
        with np.errstate(invalid="ignore", over="ignore"):
            _lum = ring_px[:, 0] * _WB + ring_px[:, 1] * _WG + ring_px[:, 2] * _WR
            _paper = ring_px[_lum >= 200.0]
            _paper_share = float(_paper.shape[0]) / float(max(1, ring_px.shape[0]))
            if _paper_share >= 0.85:
                _anchor = np.median(_paper, axis=0)
                _al = float(_anchor[0] * _WB + _anchor[1] * _WG + _anchor[2] * _WR)
                if _al >= 190.0:
                    _dev = np.abs(ring_px - _anchor[None, :]).max(axis=1)
                    if float(np.percentile(_dev, 90)) <= 26.0:
                        out = crop_img.copy()
                        out[m] = np.clip(np.rint(_anchor), 0, 255).astype(np.uint8)
                        return out
            if _paper_share >= 0.35:
                _anchor = np.median(_paper, axis=0)
                _sel = (np.abs(ring_px - _anchor[None, :]).max(axis=1) <= 20.0)
                if int(_sel.sum()) < 60:
                    return None
                ring_px = ring_px[_sel]
                ring[ring] = _sel
            h, w = m.shape
            yy, xx = np.mgrid[-1:1:complex(h), -1:1:complex(w)]
            basis = np.stack((np.ones_like(xx), xx, yy, xx * yy, xx * xx, yy * yy), axis=-1)
            samples = basis[ring]
            keep = np.ones(int(samples.shape[0]), dtype=bool)
            fit = None
            for _ in range(4):
                fit = np.linalg.lstsq(samples[keep], ring_px[keep], rcond=None)[0]
                if not np.isfinite(fit).all():
                    return None
                error = np.max(np.abs(samples @ fit - ring_px), axis=1)
                keep = error <= max(5.0, float(np.median(error)) * 2.5)
                if keep.sum() < max(60, 0.55 * len(samples)):
                    return None
# fit_tol: مسیرِ حلقهٔ روشنِ اندروید با تلورانسِ
# بالاتر (گرادیانِ آسمان→دیوار قابلِ fit میشود؛ ضدِ توهمِ LaMa)
            if float(np.percentile(error[keep], 90)) > float(fit_tol):
                return None
            fill = basis[m] @ fit
            if not np.isfinite(fill).all():
                return None
            if _paper_share >= 0.35 and _paper.shape[0] > 0:
                _fill_lum = float(np.median(fill[:, 0] * _WB + fill[:, 1] * _WG + fill[:, 2] * _WR))
                _anchor_lum = float(np.median(_paper[:, 0] * _WB + _paper[:, 1] * _WG + _paper[:, 2] * _WR))
                if _fill_lum < 170.0 or _fill_lum < _anchor_lum - 25.0:
                    return None
            if np.any(fill < ring_px[keep].min(axis=0) - 8) or np.any(fill > ring_px[keep].max(axis=0) + 8):
                return None
        out = crop_img.copy()
        out[m] = np.clip(np.rint(fill), 0, 255).astype(np.uint8)
        return out

    @staticmethod
    def _mask_clusters(mask: np.ndarray, pad: int = 18, max_clusters: int = 14) -> List[Tuple[int, int, int, int]]:

        n, _lab, st, _ = cv2.connectedComponentsWithStats(
            (mask > 0).astype(np.uint8), connectivity=8
        )
        boxes: List[List[int]] = []
        for i in range(1, n):
            if int(st[i, cv2.CC_STAT_AREA]) < 4:
                continue
            bx, by = int(st[i, cv2.CC_STAT_LEFT]), int(st[i, cv2.CC_STAT_TOP])
            bw, bh = int(st[i, cv2.CC_STAT_WIDTH]), int(st[i, cv2.CC_STAT_HEIGHT])
            boxes.append([bx - pad, by - pad, bx + bw + pad, by + bh + pad])
        if not boxes:
            return []

        def _merge_all(rects: List[List[int]]) -> List[List[int]]:
            merged = True
            while merged:
                merged = False
                out: List[List[int]] = []
                for b in rects:
                    hit = None
                    for o in out:
                        if b[0] < o[2] and b[2] > o[0] and b[1] < o[3] and b[3] > o[1]:
                            hit = o
                            break
                    if hit is None:
                        out.append(list(b))
                    else:
                        hit[0] = min(hit[0], b[0])
                        hit[1] = min(hit[1], b[1])
                        hit[2] = max(hit[2], b[2])
                        hit[3] = max(hit[3], b[3])
                        merged = True
                rects = out
            return rects

        boxes = _merge_all(boxes)
        if len(boxes) > max_clusters:

            boxes = _merge_all([
                [b[0] - pad * 2, b[1] - pad * 2, b[2] + pad * 2, b[3] + pad * 2]
                for b in boxes
            ])
        return [
            (max(0, b[0]), max(0, b[1]), b[2], b[3]) for b in boxes
        ]

    @staticmethod
    def _wall_lines(image: np.ndarray, max_side: int = 1600) -> Optional[np.ndarray]:
        try:
            g = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            oh, ow = g.shape[:2]
            sc = min(1.0, float(max_side) / float(max(oh, ow)))
            if sc < 1.0:
                g = cv2.resize(g, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
            e = cv2.Canny(g, 60, 150)
            e = cv2.dilate(e, np.ones((3, 3), np.uint8), iterations=1)
            n, lab, st, _ = cv2.connectedComponentsWithStats(e, 8)
            wall = np.zeros_like(e)
            lim = 0.16 * max(e.shape)
            for i in range(1, n):
                bw = int(st[i, cv2.CC_STAT_WIDTH])
                bh = int(st[i, cv2.CC_STAT_HEIGHT])
                ls, ss = max(bw, bh), min(bw, bh)
                if ss <= 14 and ls >= lim:
                    wall[lab == i] = 255
            if sc < 1.0:
                wall = cv2.resize(wall, (ow, oh), interpolation=cv2.INTER_NEAREST)
            return wall
        except Exception:
            return None

    @staticmethod
    def _group_nearby_patches(pending: List[list], gap: int = 24,
                              max_members: int = 6) -> List[List[list]]:
        n = len(pending)
        if n < 2:
            return [list(pending)] if pending else []
        rects = [[c[0] - gap, c[1] - gap, c[2] + gap, c[3] + gap]
                 for c in pending]
        parent = list(range(n))

        def _find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for i in range(n):
            for j in range(i + 1, n):
                a, b = rects[i], rects[j]
                if a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]:
                    ri, rj = _find(i), _find(j)
                    if ri != rj:
                        parent[rj] = ri
        buckets: Dict[int, List[int]] = {}
        for i in range(n):
            buckets.setdefault(_find(i), []).append(i)
# سقفِ اتحادِ گروه (فقط اندروید — MANGA_LAMA_GROUP_CAP):
# هر ورودیِ LaMa به سقفِ پچ (۳۸۴/۵۱۲) داوناسکیل میشود؛ اتحادِ
# چند خوشهٔ پراکنده رویِ نوارِ بلند (700×2000+) → مقیاسِ ~0.2 →
# LaMa «متنِ قلابی/نویزِ گلیفی» میسازد (لکهٔ کثیفِ بلوکهایِ
# متراکم — بازتولیدِ A/B). گروههایی که اتحادشان از ~2.2×پچ
# بزرگتر است به زیرگروههایِ همسایه شکسته میشوند → مقیاسِ ≥0.45.
# PC (گیت اندروید) دست‌نخورده.
        _gcap = 0
        try:
            if _on_android() and os.environ.get(
                    "MANGA_LAMA_GROUP_CAP", "1").strip() != "0":
                _sb = _lama_static_side() or 384
                _gcap = int(_sb * 2.2)
        except Exception:
            _gcap = 0
        out: List[List[list]] = []
        for idxs in buckets.values():
            chunks = [idxs[k:k + max_members]
                      for k in range(0, len(idxs), max_members)]
            if _gcap > 0 and len(chunks) >= 1:
                _resplit: List[List[int]] = []
                for _ch in chunks:
                    _cur: List[int] = []
                    _box = None
                    for _i in sorted(
                            _ch,
                            key=lambda t: (pending[t][1], pending[t][0])):
                        _c = pending[_i]
                        _nb = (_c[0] - gap, _c[1] - gap,
                               _c[2] + gap, _c[3] + gap)
                        if _box is not None:
                            _nb = (min(_box[0], _nb[0]),
                                   min(_box[1], _nb[1]),
                                   max(_box[2], _nb[2]),
                                   max(_box[3], _nb[3]))
                        if _cur and max(_nb[2] - _nb[0],
                                        _nb[3] - _nb[1]) > _gcap:
                            _resplit.append(_cur)
                            _cur = [_i]
                            _box = (_c[0] - gap, _c[1] - gap,
                                    _c[2] + gap, _c[3] + gap)
                        else:
                            _cur.append(_i)
                            _box = _nb
                        if len(_cur) >= max_members:
                            _resplit.append(_cur)
                            _cur = []
                            _box = None
                    if _cur:
                        _resplit.append(_cur)
                chunks = _resplit
            for k in chunks:
                out.append([pending[i] for i in k])
        return out

    def _lama_group_prep(self, image: np.ndarray, members: List[list],
                         page_kernel) -> Optional[dict]:
        """-speed (SRV-G phase2) — فازِ «آماده‌سازی»ِ `_lama_run_group`
        قبلی: کراپِ گروه + ماسک + پد + داون‌اسکیلِ >max_side — بدونِ هیچ
        run. خروجی ctx بینِ prep/run/finish مشترک است تا مسیرِ batched
        بایت‌به‌بایت همان ورودی‌هایِ امروز را بسازد. None = گروهِ ردشده
        (مثلِ returnهایِ زودهنگامِ قبل)."""
        img_h, img_w = image.shape[:2]
        gx0 = min(c[0] for c in members)
        gy0 = min(c[1] for c in members)
        gx1 = max(c[2] for c in members)
        gy1 = max(c[3] for c in members)
        bw = max(1, gx1 - gx0)
        bh = max(1, gy1 - gy0)
        pad_x = int(np.clip(round(bw * 0.15), 12, 48))
        pad_y = int(np.clip(round(bh * 0.15), 12, 48))
# گروه‌هایِ بنرِ تبلیغ (promo): پدِ بزرگ‌تر الزامی است.
# با پدِ معمولی (~40px) حفرهٔ بنر ~۵۰٪ کراپ را می‌گیرد و LaMa-Manga
# «بنفشِ خیالی/صورتی» نقاشی می‌کند (بازتولیدِ سندباکس: بنرِ
# ASURASCANS.COM). با پدِ ~۵۵٪ (حفره ~۲۰٪) مدل راه‌راه‌ها را
# واقعاً ادامه می‌دهد — آزمایش: pad=130 → نتیجهٔ تمیز.
        try:
            for _pg in (getattr(self, "_promo_rect_boxes", None) or []):
                if not (gx1 < int(_pg[0]) or gx0 > int(_pg[2])
                        or gy1 < int(_pg[1]) or gy0 > int(_pg[3])):
                    _pp2 = int(np.clip(round(0.55 * max(bw, bh)), 48, 200))
                    pad_x = max(pad_x, _pp2)
                    pad_y = max(pad_y, _pp2)
                    break
        except Exception:
            pass
        ex0 = max(0, gx0 - pad_x)
        ey0 = max(0, gy0 - pad_y)
        ex1 = min(img_w, gx1 + pad_x)
        ey1 = min(img_h, gy1 + pad_y)
        if ex1 - ex0 < 96:
            d = 96 - (ex1 - ex0)
            ex0 = max(0, ex0 - d // 2)
            ex1 = min(img_w, max(96, ex0 + 96))
        if ey1 - ey0 < 96:
            d = 96 - (ey1 - ey0)
            ey0 = max(0, ey0 - d // 2)
            ey1 = min(img_h, max(96, ey0 + 96))
        if ex1 - ex0 < 32 or ey1 - ey0 < 32:
            return
        sub_img = image[ey0:ey1, ex0:ex1]
        sub_msk = np.zeros(sub_img.shape[:2], dtype=np.uint8)
        for c in members:
            cx0, cy0, cx1, cy1, crop_msk = c[:5]
            cx1, cy1 = min(cx1, img_w), min(cy1, img_h)
            if cx1 <= cx0 or cy1 <= cy0:
                continue
            dm = cv2.dilate(crop_msk, page_kernel)
            region = sub_msk[cy0 - ey0:cy1 - ey0, cx0 - ex0:cx1 - ex0]
            sub_msk[cy0 - ey0:cy1 - ey0, cx0 - ex0:cx1 - ex0] = \
                np.maximum(region, dm)
# دیوارِ حباب/کادر از ماسکِ LaMa هم حذف شود تا به‌عنوان
# زمینه بماند و بازسازی نشود
        _pp = getattr(self, "_page_protect", None)
        if _pp is not None:
            try:
                _pp_sub = _pp[ey0:ey1, ex0:ex1]
                if _pp_sub.shape == sub_msk.shape:
                    sub_msk[_pp_sub > 0] = 0
            except Exception:
                pass
# ساختارِ روشنِ قفل‌شده (خطِ حباب/قابِ کارت) هم از
# ماسکِ LaMa خارج شود — LaMa باید آن را «زمینه» ببیند، نه حفره
# (وگرنه قابِ سفیدِ کارت با رنگِ کارت بازسازی می‌شد — img2-r10).
        try:
            _pag = getattr(self, "_prot_all", None)
            if _pag is not None:
                _pa_sub = _pag[ey0:ey1, ex0:ex1]
                if _pa_sub.shape == sub_msk.shape:
                    sub_msk[_pa_sub > 0] = 0
        except Exception:
            pass
        if not sub_msk.any():
            return  # ماسکِ خالی — طبیعی، لاگ لازم نیست
        try:
            _max_side = int(os.environ.get("MANGA_LAMA_MAX_SIDE", "0") or 0)
        except Exception:
            _max_side = 0
        if _max_side <= 0:
            _max_side = 1024 if _on_android() else 2048
        _pl, _ph = int(sub_img.shape[1]), int(sub_img.shape[0])
        ctx = {"img_h": int(img_h), "img_w": int(img_w),
               "ex0": int(ex0), "ey0": int(ey0),
               "ex1": int(ex1), "ey1": int(ey1),
               "crop_img": sub_img, "crop_msk": sub_msk,
               "run_img": sub_img, "run_msk": sub_msk,
               "pl": _pl, "ph": _ph,
               "was_resized": False, "nw2": 0, "nh2": 0,
               "resize_failed": False}
        if max(_pl, _ph) > _max_side:
            _sc = float(_max_side) / float(max(_pl, _ph))
            _nw = max(64, (int(round(_pl * _sc)) // 8) * 8)
            _nh = max(64, (int(round(_ph * _sc)) // 8) * 8)
            try:
                ctx["run_img"] = cv2.resize(sub_img, (_nw, _nh),
                                            interpolation=cv2.INTER_AREA)
                ctx["run_msk"] = cv2.resize(sub_msk, (_nw, _nh),
                                            interpolation=cv2.INTER_NEAREST)
                ctx["was_resized"], ctx["nw2"], ctx["nh2"] = True, _nw, _nh
            except Exception:
                ctx["resize_failed"] = True
        return ctx

    def _lama_try_fn(self, lama):
        """-speed (SRV-G phase2) — همان `_lama_try` قبلی (بدنه دست
        نخورده) به‌صورتِ کارخانهٔ closure تا مسیرِ batched هم دقیقاً همان
        فال‌بک‌ها (EP-mortal → CPU-safe → resize-retry) را داشته باشد."""
        def _lama_try(si, sm, side):
# حافظهٔ مرگِ EP: بعد از اولین ORT_FAIL واقعی
# بقیهٔ پچ‌هایِ همین ران مستقیم با سشنِ امنِ CPU اجرا می‌شوند
# (تلاشِ مجدد با سشنِ مرده فقط اتلافِ زمان است) + انتخابِ «cpu»
# در فایلِ .epab ذخیره می‌شود تا ران‌هایِ بعدیِ گوشی از همان
# ابتدا CPU برود و هرگز به فال‌بکِ OpenCV (لکهٔ قرمز) نیفتد.
            _ep_dead = getattr(self, "_lama_ep_dead", False)

            def _call_main(ai, am):
                if _ep_dead:
                    _s0 = self._get_lama_cpu_safe()
                    if _s0 is not None:
                        return _s0(ai, am)
                return lama(ai, am)

            try:
                return _call_main(si, sm)
            except Exception as _e0:
# سکوتِ ممنوع: EPِ پروب‌شده (مثلاً xnnpack) ورودیِ
# ثابتِ پروب (۲۵۶²) را پاس می‌کند ولی رویِ شکلِ واقعیِ پچ
# (مثلاً ۳۸۴×۱۸۰) ORT_FAIL می‌دهد (لاگِ POCO F4: پچِ کارتِ
# Crimson Dragon بی‌صدا رد شد → فال‌بکِ OpenCV → لکهٔ قرمز).
# یک بار با سشنِ امنِ CPU دوباره تلاش می‌کنیم.
                self._lama_ep_dead = True
                try:
                    _lama_ep_store(getattr(self, "_lama_model_path", "") or "",
                                   "cpu")
                    print(f"    [!] LaMa EP failed "
                          f"({str(_e0)[:90]}) → CPU retry + ذخیرهٔ CPU "
                          f"برای ران‌های بعد", flush=True)
                except Exception:
                    pass
                try:
                    _safe = self._get_lama_cpu_safe()
                except Exception:
                    _safe = None
                if _safe is not None:
                    try:
                        return _safe(si, sm)
                    except Exception as _e1:
                        try:
                            print(f"    [!] LaMa CPU retry failed too: "
                                  f"{str(_e1)[:90]}", flush=True)
                        except Exception:
                            pass
            try:
                _s2 = float(side) / float(max(1, max(si.shape[0], si.shape[1])))
                if _s2 >= 0.98:
                    return None
                _nw2 = max(64, (int(round(si.shape[1] * _s2)) // 8) * 8)
                _nh2 = max(64, (int(round(si.shape[0] * _s2)) // 8) * 8)
                _si2 = cv2.resize(si, (_nw2, _nh2), interpolation=cv2.INTER_AREA)
                _sm2 = cv2.resize(sm, (_nw2, _nh2), interpolation=cv2.INTER_NEAREST)
                _o2 = _call_main(_si2, _sm2)
                _ob2 = _o2 if isinstance(_o2, np.ndarray) else np.array(_o2)
                if _ob2.ndim == 2:
                    _ob2 = cv2.cvtColor(_ob2, cv2.COLOR_GRAY2BGR)
                else:
                    _ob2 = cv2.cvtColor(_ob2, cv2.COLOR_RGB2BGR)
                if _ob2.shape[:2] != (_nh2, _nw2):
                    return None
                return cv2.resize(_ob2, (si.shape[1], si.shape[0]),
                                  interpolation=cv2.INTER_LANCZOS4)
            except Exception as _e2:
                try:
                    print(f"    [!] LaMa retry(×{side}) failed too: "
                          f"{str(_e2)[:90]}", flush=True)
                except Exception:
                    pass
                return None

        return _lama_try  # پایانِ closureِ _lama_try_fn

    def _lama_run_group(self, image: np.ndarray, members: List[list],
                        lama, page_kernel) -> None:
        """مسیرِ تکیِ امروز: prep → run (همان `_lama_try`) → finish.
        -speed (SRV-G phase2) — فقط بازچینی شد؛ رفتارِ بایت‌به‌بایت
        همان قبل است."""
        if os.environ.get("MANGA_GROUP_DBG"):
            try:
                _mb = ";".join(f"({c[0]},{c[1]},{c[2]},{c[3]})" for c in members)
                print(f"    [grp-dbg] n={len(members)} boxes={_mb}",
                      flush=True)
            except Exception:
                pass
        ctx = self._lama_group_prep(image, members, page_kernel)
        if ctx is None:
            return
        if ctx.get("resize_failed"):
            try:
                print(f"    [!] LaMa group skipped: resize-path failed "
                      f"(box {ctx['pl']}x{ctx['ph']})", flush=True)
            except Exception:
                pass
            return
        out = self._lama_try_fn(lama)(ctx["run_img"], ctx["run_msk"], 640)
        sub_bgr = self._lama_group_out_to_bgr(ctx, out)
        if sub_bgr is None:
            return
        self._lama_group_finish(members, ctx, sub_bgr, page_kernel)

    def _lama_group_out_to_bgr(self, ctx, out):
        """خروجیِ LaMa (PIL/ndarray) → BGRِ کراپ؛ دقیقاً منطقِ شاخه‌هایِ
        resize/مستقیمِ `_lama_run_group` قبلی (با همان لاگ‌ها/quirkها)."""
        _pl, _ph = ctx["pl"], ctx["ph"]
        if ctx["was_resized"]:
            _ob = None
            if out is not None:
                _ob = out if isinstance(out, np.ndarray) else np.array(out)
                if _ob.ndim == 2:
                    _ob = cv2.cvtColor(_ob, cv2.COLOR_GRAY2BGR)
                else:
                    _ob = cv2.cvtColor(_ob, cv2.COLOR_RGB2BGR)
            if _ob is None or _ob.shape[:2] != (ctx["nh2"], ctx["nw2"]):
                try:
                    print(f"    [!] LaMa group skipped: resize-path failed "
                          f"(box {_pl}x{_ph})", flush=True)
                except Exception:
                    pass
                return None
            return cv2.resize(_ob, (_pl, _ph),
                              interpolation=cv2.INTER_LANCZOS4)
        if out is None:
            try:
                print(f"    [!] LaMa group skipped: all attempts failed "
                      f"(box {_pl}x{_ph})", flush=True)
            except Exception:
                pass
            return None
        sub_bgr = out if isinstance(out, np.ndarray) else np.array(out)
        if sub_bgr.ndim == 2:
            sub_bgr = cv2.cvtColor(sub_bgr, cv2.COLOR_GRAY2BGR)
        else:
            sub_bgr = cv2.cvtColor(sub_bgr, cv2.COLOR_RGB2BGR)
        if sub_bgr.shape[:2] != ctx["crop_img"].shape[:2]:
            return None
        return sub_bgr

    def _lama_group_finish(self, members: List[list], ctx: dict,
                           sub_bgr, page_kernel) -> None:
        """-speed (SRV-G phase2) — فازِ «پس‌پردازشِ» `_lama_run_group`
        قبلی (QCِ dark-fill + اعتبارسنجیِ ضدتوهم + انتسابِ اعضا) — دست
        نخورده؛ فقط ورودی‌هایش از ctx می‌آید."""
        img_h, img_w = ctx["img_h"], ctx["img_w"]
        ex0, ey0 = ctx["ex0"], ctx["ey0"]
        ex1, ey1 = ctx["ex1"], ctx["ey1"]
        sub_img, sub_msk = ctx["crop_img"], ctx["crop_msk"]
        try:
            _qc = getattr(self, "_qc_kernel31", None)
            if _qc is None:
                _qc = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
                self._qc_kernel31 = _qc
            _fm = sub_msk > 0
            _ring = (cv2.dilate(sub_msk, _qc) > 0) & (~_fm)
            if _fm.any() and _ring.any():
                _g = cv2.cvtColor(sub_bgr, cv2.COLOR_BGR2GRAY)
                _bg_px = _g[_ring]
                _bright = _bg_px[_bg_px >= 160.0]
# QCِ «پرِ تیره» فقط وقتی معتبر است که حلقهٔ
# کلاستر «واقعاً» روشن باشد. بنرِ سیاهِ «CHAPTER 1 PAGE 1»
# (img1018) داخلِ کلاسترِ بالایِ صفحه بود؛ حلقهٔ ۳۱pxِ
# کلاستر عمدتاً سفیدِ صفحه است → bg_med=۲۵۵ → پرِ «سیاهِ
# درستِ» LaMa رویِ بنر رد میشد و جایگزینِ سفید = «لگهٔ
# سفیدِ» بزرگ رویِ بنر. حالا اگر ≥۱۰٪ حلقه تیرهِ واقعی
# باشد (زمینهٔ مختلط)، این QCِ کورِ سطحِ کلاستر پرش را رد
# نمیکند؛ اعتبارسنجیِ محلیِ هر عضو (گاردِ ضدتوهم) خودش
# درست قضاوت میکند.
                _darkqc = float((_bg_px < 110.0).mean())
                if (_bright.size >= max(50, int(0.02 * _bg_px.size))
                        and _bright.size >= 0.55 * _bg_px.size
                        and _darkqc < 0.10):
                    _bg_med = float(np.median(_bright))
                    _fill_med = float(np.median(_g[_fm]))
# اندروید: رویِ حلقهٔ تختِ روشن (حبابِ زرد)
# پرِ ~۱۳۰-۱۶۰ (بلوکِ خاکستریِ LaMaِ xnnpack) از آستانهٔ
# قدیمیِ (-55) رد میشد و به خروجی میرفت. رویِ حلقهٔ یکدست
# (std≤30) آستانه به -30 سختگیرانهتر میشود؛ بافتِ
# واقعی (std بالا) مثلِ قبل -55.
                    _dqc_thr = 55.0
                    if _android_gate("MANGA_DARKQC_HARD"):
                        try:
                            if float(np.std(_bg_px)) <= 30.0:
                                _dqc_thr = 30.0
                        except Exception:
                            pass
# اندروید (MANGA_GRAYQC): بلوکِ خاکستریِ
# LaMaِ xnnpack (پرِ ~۱۲۰-۱۸۰ رویِ حبابِ سفید/روشن)
# ازQCِ قدیمی می‌گذشت چون شرطِ قدیمی فقط «پرِ تیره‌ترِ
# 115» را میگرفت = «لکهٔ خاکستری» در خروجی (نمونه:
# حبابِ جرقهٔ صفحهٔ ژاپنیِ ). حالا هر پرِ
# محسوسِ تیره‌تر از حلقهٔ روشن (≥۴۲ واحد) هم رد میشود
# و پرِ تختِ نجاتِ حلقه جایگزینش میشود. PC بیت‌به‌بیت.
                    _gray = False
                    if _android_gate("MANGA_GRAYQC"):
                        try:
                            _gray = (_bg_med >= 185.0
                                        and _fill_med < _bg_med - 42.0)
                        except Exception:
                            _gray = False
                    if _gray or (_fill_med < 115.0
                                    and _fill_med < _bg_med - _dqc_thr):
# لاگ شود؛ این ردِ خاموش = فال‌بکِ OpenCV
                        try:
                            print(f"    [!] LaMa group rejected: dark fill "
                                  f"({_fill_med:.0f} vs bg {_bg_med:.0f})",
                                  flush=True)
                        except Exception:
                            pass
# اندروید: به‌جایِ رهاشدن به TELEA (اسمیرِ
# کم‌رنگ رویِ حفرهٔ بزرگ)، اگر حلقه تختِ روشن است خودم
# با رنگِ میانهٔ حلقه پر می‌کنم (همان پرِ تختِ امن).
# پرِ موفق → return نمی‌خوریم تا کامیتِ پایینی اجرا
# شود؛ اعتبارسنجیِ عضویِ بعدی رویِ پرِ تختِ
# نجات‌یافته badf≈۰ می‌گیرد و دست نمی‌زند.
                        _rescued = False
# پیشفرضِ روشن رویِ PC هم: گروهِ ردشده
# (پرِ تیره) بدونِ نجات، یا متنِ اورجینال جا میماند
# یا فال‌بکِ Telea اسمیر میسازد (img6: 88 vs bg 226).
                        if _gate_default_on("MANGA_FILL_RESCUE"):
                            try:
# نجاتِ «عضو به عضو» به‌جایِ
                                #): پرِ تختِ یکرنگِ کلِ ماسکِ گروه
# پرِ تختِ کلِ گروه (
# رویِ حبابِ گرادیانی = «لکهٔ سفیدِ
# مستطیلی» (GO! EVEN FASTER — img6). حالا
# هر عضو (خطِ متن) با ماسکِ خودش و حلقهٔ
# «محلیِ روشنِ» خودش ردیف‌به‌ردیف پر میشود —
# رنگِ محلیِ همان خط + گرادیانِ عمودیِ
# حفظشده؛ عضوی که حلقهٔ معتبر ندارد به پرِ
# تختِ محلیِ خودش برمیگردد.
                                _sub_g = cv2.cvtColor(
                                    sub_img, cv2.COLOR_BGR2GRAY)
                                _resc_px = 0
                                _resc_rows = 0
                                sub_bgr = sub_bgr.copy()
                                for _mem in members:
                                    try:
                                        _mx0, _my0, _mx1, _my1, _mm = \
                                            _mem[:5]
                                        _mm2 = np.zeros(
                                            sub_img.shape[:2], np.uint8)
                                        _ox0 = max(0, int(_mx0) - ex0)
                                        _oy0 = max(0, int(_my0) - ey0)
                                        _ox1 = min(sub_img.shape[1],
                                                   int(_mx1) - ex0)
                                        _oy1 = min(sub_img.shape[0],
                                                   int(_my1) - ey0)
                                        if _ox1 <= _ox0 or _oy1 <= _oy0:
                                            continue
                                        _mmk = (_mm > 0)
                                        if _mmk.shape != (_oy1 - _oy0,
                                                          _ox1 - _ox0):
                                            _mmk = np.ones(
                                                (_oy1 - _oy0, _ox1 - _ox0),
                                                bool)
                                        _mm2[_oy0:_oy1, _ox0:_ox1] = \
                                            (_mmk.astype(np.uint8)) * 255
                                        _mm2 = cv2.dilate(
                                            _mm2, page_kernel)
                                        _mfm = (_mm2 > 0) & _fm
                                        if not _mfm.any():
                                            continue
                                        _tmask = (_mfm.astype(np.uint8)) * 255
                                        _inp = cv2.inpaint(
                                            sub_bgr, _tmask, 5,
                                            cv2.INPAINT_TELEA)
                                        sub_bgr[_mfm] = _inp[_mfm]
                                        _resc_px += int(_mfm.sum())
                                    except Exception:
                                        continue
                                if _resc_px > 0:
                                    _rescued = True
                                    print(f"    [✓] پرِ عضو-به-عضویِ نجات از "
                                          f"حلقهٔ محلی ({_resc_px}px، "
                                          f"{_resc_rows} ردیفِ گرادیانی)",
                                          flush=True)
                                else:
# هیچ عضوی حلقهٔ معتبر نداشت → پرِ تختِ
# کل (رفتارِ ۲۱۲)
                                    _src = _ring
                                    _b = _bg_px >= 160.0
                                    if float(_b.mean()) < 0.98:
                                        _ri2 = np.where(_ring)
                                        _bi = np.where(_b)[0]
                                        _src = (_ri2[0][_bi],
                                                   _ri2[1][_bi])
                                    _px2 = sub_img[_src].astype(
                                        np.float32)
                                    _rc2 = np.median(_px2, axis=0)
                                    _sd = float(np.std(_px2))
                                    if _sd <= 40.0 and np.isfinite(
                                            _rc2).all():
                                        sub_bgr[_fm] = np.clip(
                                            np.rint(_rc2), 0, 255).astype(
                                                np.uint8)
                                        _rescued = True
                                        print(f"    [✓] پرِ تختِ نجات از حلقه "
                                              f"(rgb="
                                              f"{_rc2.round(0).tolist()})",
                                              flush=True)
                            except Exception:
                                _rescued = False
                        if not _rescued:
                            return
        except Exception:
            pass
# /141 — اندروید (MANGA_DARKSMOKE): QCِ «پرِ ناهمخوان
# با حلقه» رویِ زمینهٔ تیره/مختلط. بلوکِ بالایی فقط حلقهٔ روشن
# (≥۵۵٪ پیکسل ≥160) را بازرسی میکند؛ رویِ کتِ تیرهٔ (#20)
# صفحهٔ 700×11362 حلقه مختلط است (دستکشِ روشن + کت) → LaMaِ
# xnnpack در داوناسکیلِ پچِ 512 «دودِ خاکستری» (تیره — لاگِ
# گوشیِ ) یا «هَزِ روشن» (آرتیفکتِ شبیهساز) میسازد و
# بدونِ هیچ بازرسی به خروجی میرود = «لگه». —
# تریگرِ بی‌قطبیت: (الف) دود — انرژیِ فرکانس-بالایِ پر ≫ حلقه
# (hf_in > 2.2×hf_ring+4 و hf_in>6)، یا (ب) ناهمخوانیِ
# روشنایی — |پر − حلقه| > 22. درمان: پرِ «ردیفی» از حلقهٔ
# همان ردیف (گرادیانِ قائم حفظ؛ ردیفِ هنری/شلوغ همان LaMa را
# نگه میدارد). PC بیت‌به‌بیت.
        try:
            if _android_gate("MANGA_DARKSMOKE") and _fm.any() \
                    and _ring.any():
                _g2 = cv2.cvtColor(sub_bgr, cv2.COLOR_BGR2GRAY)
                _rmed = float(np.median(_g2[_ring]))
                _fmed = float(np.median(_g2[_fm]))
# اندروید (MANGA_SOFTQC): کلاسِ جدیدِ «لکهٔ
# شیری» — پرِ LaMa رویِ زمینهٔ بافت‌دار (کتِ بژِ صفحهٔ
# ژاپنیِ ) که روشناییاش به حلقه نزدیک است
# (از QCِ تیره/دود رد میشود) ولی بافتِ داخلِ پر تقریباً
# صفر است در حالیکه حلقه بافتِ واقعی دارد = اسمیرِ
# نیمه‌شفافِ لباس/هنر. دروازهٔ ارزان: stdِ حلقه؛ بعد
# سنجشِ hf. PC بیت‌به‌بیت.
                _soft = False
                _rstd = 0.0
                if _android_gate("MANGA_SOFTQC") \
                        and abs(_fmed - _rmed) <= 22.0 \
                        and _rmed >= 140.0:
                    try:
                        _rstd = float(_g2[_ring].std())
                        if _rstd >= 14.0:
                            _med2 = cv2.medianBlur(_g2, 31)
                            _hf2 = np.abs(
                                _g2.astype(np.int16)
                                - _med2.astype(np.int16))
                            _hf_in = float(np.median(_hf2[_fm]))
                            _hf_rg = float(np.median(_hf2[_ring]))
                            _hf_sd = float(_hf2[_fm].std())
                            _soft = (_hf_rg >= 7.0
                                        and _hf_in < max(3.0,
                                                         0.35 * _hf_rg)
                                        and _hf_sd <= 3.0)
                    except Exception:
                        _soft = False
                if _soft or abs(_fmed - _rmed) > 22.0 or \
                        _rmed < 140.0:
                    if not _soft:
                        _med = cv2.medianBlur(_g2, 31)
                        _hf = np.abs(
                            _g2.astype(np.int16)
                            - _med.astype(np.int16))
                        _hf_in = float(np.median(_hf[_fm]))
                        _hf_rg = float(np.median(_hf[_ring]))
                    if _soft or (_hf_in > 2.2 * _hf_rg + 4.0
                                    and _hf_in > 6.0) or \
                            abs(_fmed - _rmed) > 22.0:
# پرِ «ردیفی» از حلقهٔ همان ردیف
# (بهجایِ پرِ تختِ کل): هر ردیفِ ماسک که نمونهٔ
# آزادِ کافیِ یکدست دارد با میانهٔ همان ردیف
# پر میشود → گرادیانِ عمودیِ کت/دیوار حفظ و
# چینِ کت (stdِ کلِ حلقه بالا ولی هر ردیف صاف)
# هم پوشش داده میشود؛ ردیفِ شلوغ (هنر) همان
# LaMa را نگه میدارد.
                        _hW = _fm.shape[1]
                        _rOK = np.zeros(_fm.shape[0], bool)
                        _rC = np.zeros((_fm.shape[0], 3), np.float32)
                        for _ri in range(_fm.shape[0]):
                            _free = ~_fm[_ri]
                            _nf = int(_free.sum())
                            if _nf < 12 or _nf > int(0.9 * _hW):
                                continue
                            _px = sub_img[_ri][_free].astype(
                                np.float32)
                            if float(_px.std()) > 26.0:
                                continue
                            _rC[_ri] = np.median(_px, axis=0)
                            _rOK[_ri] = True
                        _okI = np.nonzero(_rOK)[0]
                        if _okI.size >= max(
                                4, int(0.3 * _fm.shape[0])):
                            _last = int(_okI[0])
                            for _ri in range(_fm.shape[0]):
                                if _rOK[_ri]:
                                    _last = _ri
                                    continue
                                _j = int(np.searchsorted(
                                    _okI, _ri))
                                if _j >= _okI.size:
                                    _rC[_ri] = _rC[_last]
                                elif _j == 0:
                                    _rC[_ri] = _rC[int(_okI[0])]
                                else:
                                    _ya2 = int(_okI[_j - 1])
                                    _yb2 = int(_okI[_j])
                                    _t2 = float(_ri - _ya2) / \
                                        float(_yb2 - _ya2)
                                    _rC[_ri] = _rC[_ya2] * \
                                        (1.0 - _t2) + _rC[_yb2] * _t2
                            _fill = np.repeat(
                                _rC[:, None, :], _hW, axis=1)
                            sub_bgr = sub_bgr.copy()
                            sub_bgr[_fm] = np.clip(
                                _fill, 0, 255).astype(
                                    np.uint8)[_fm]
# f-stringِ چندخطی در 3.11
# سینتکس-ارور میداد (PEP 701 = 3.12) → لیبل
# قبل از print محاسبه میشود
                            _tag = ("ضدِ لکهٔ شیری (SOFTQC)"
                                       if _soft else
                                       "ضدِ دودِ زمینهٔ تیره")
                            print(f"    [✓] {_tag}: "
                                  f"hf={_hf_in:.1f} vs "
                                  f"حلقه={_hf_rg:.1f} → پرِ ردیفیِ "
                                  f"حلقه ({int(_okI.size)}/"
                                  f"{_fm.shape[0]} ردیف)",
                                  flush=True)
        except Exception:
            pass
# اعتبارسنجیِ ضدتوهمِ هر عضو: LaMa-Manga وقتی حفرهٔ بزرگ
# داخلِ حبابِ سفید می‌بیند گاهی «محتوا» (صورت/بافتِ درخت/بافتِ
# اسکرین‌تونِ درشت) نقاشی می‌کند (لاگِ کاربر: حبابِ «YOU'RE
# LEAVING…» سیاه/صورت شد). اگر ماسکِ عضو بخشِ عمدهٔ اینتریورِ یک
# حبابِ سفید را بپوشاند و نتیجهٔ LaMa محتوایِ تیرهٔ «درشت» داشته
# باشد → همان عضو با رنگِ تختِ زمینه پر می‌شود (کارِ flat).
# گاردها: نقطه‌هایِ ریزِ اسکرین‌تون با OPEN حذف می‌شوند؛ ماسکِ
# کوچک (متنِ کنارِ عکسِ داخلِ حباب) اعتبارسنجی نمی‌شود تا عکس
# قانونی قربانی نشود.
        try:
            _k = getattr(self, "_qc_kernel31", None)
            if _k is None:
                _k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
                self._qc_kernel31 = _k
            _g_org = cv2.cvtColor(sub_img, cv2.COLOR_BGR2GRAY)
            _g_out = cv2.cvtColor(sub_bgr, cv2.COLOR_BGR2GRAY)
            _n_rej = 0
            _dbg = bool(os.environ.get("MANGA_GUARD_DBG"))
            for c in members:
                cx0, cy0, cx1, cy1, crop_msk = c[:5]
                cx1, cy1 = min(cx1, img_w), min(cy1, img_h)
                if cx1 <= cx0 or cy1 <= cy0:
                    continue
                ox, oy = cx0 - ex0, cy0 - ey0
                oh2 = min(cy1, ey1) - cy0
                ow2 = min(cx1, ex1) - cx0
                if oh2 < 8 or ow2 < 8:
                    continue
                dm = cv2.dilate(crop_msk, page_kernel)
                if dm.shape[0] > oh2 or dm.shape[1] > ow2:
                    dm = dm[:oh2, :ow2]
                mm = dm > 0
                _n_mm = int(mm.sum())
                if _n_mm < 400:
                    if _dbg:
                        print(f"      [🛡dbg] skip tiny mask {_n_mm}px", flush=True)
                    continue
# QCِ کروما (رنگ، نه فقط روشنایی) — «قبل از»
# همهٔ گاردهایِ خاکستری و مستقل از اینتریور: همهٔ QCهایِ
# قدیمی خاکستریند؛ LaMa (xnnpackِ گوشی + پچِ ثابتِ ۳۸۴)
# رویِ مرزِ دو حبابِ همپوشان با رنگهایِ متفاوت (img6:
# حبابِ سفیدِ «You're the real attraction here.» داخلِ
# کراپِ خوشهٔ حبابِ زردِ بزرگ — خوشهٔ واقعی: ماسکِ ۶۳هزارpx
# با حلقهٔ ذاتیِ مخلوطِ زرد+سفید+آسمان) پرِ «روشنِ زرد»
# میسازد که از هر بی‌رنگی سربلند بیرون میآید = «با حباب
# داخل به بیرون رنگ زده» (خروجیِ واقعیِ گوشیِ 226 —
# چپ‌بالا؛ PC هم در همان مرز لکهٔ خاکستریِ آبی میسازد).
# چون حلقهٔ کلِ چنین عضوی مخلوط است (و ماسکِ گسترش‌یافتهٔ
# چندخطی اغلب یک مؤلفهٔ عظیمِ به‌هم‌چسبیده است)، سنجش
# «پنجره‌پنجرهٔ شبکه‌ای (~۱۱۲px)» با حلقهٔ ۳۱pxیِ محلیِ
# همان پنجره انجام میشود: پنجره‌ای با حلقهٔ یکدست و پرِ
# تخت که ≥۴۸ واحد در یک کانال با حلقه‌اش فرق دارد = پرِ
# رنگِ غلط → همان پنجره با TELEAیِ محلی پر میشود (درمانِ
# ۲۱۳ — گرادیان حفظ، رنگِ حبابِ همسایه دیگر بیرون
# نمی‌ریزد). گاردها: حلقه/پرِ بافت‌دار (std بالا) و
# پنجره‌هایِ مرزی (حلقهٔ مخلوط) سنجیده نمیشوند تا هنرِ
# قانونی (سکرین‌تون/گرادیان/مرز) قربانی نشود.
                try:
                    _sic2 = sub_img[oy:oy + dm.shape[0],
                                      ox:ox + dm.shape[1]]
                    _rc3 = sub_bgr[oy:oy + dm.shape[0],
                                     ox:ox + dm.shape[1]]
                    _ch, _cw = mm.shape[:2]
                    _cell = 112

                    _wins = []
                    _tofix = []
# انرژیِ فرکانس-بالای زمینه (ضدِ هنرِ هموارنما):
# مو/پوستِ رگه‌دار (img4_s02: پیشانی) رنگِ غالب و
# stdِ پایین دارد ولی بافتِ ریزش hf بالا است — حباب/
# آسمانِ تخت hf≈۰. فقط حلقههایِ تختِ واقعی سنجیده
# میشوند.
                    try:
                        _gS = cv2.cvtColor(_sic2,
                                              cv2.COLOR_BGR2GRAY)
                        _hfS = np.abs(
                            _gS.astype(np.float32)
                            - cv2.medianBlur(_gS, 31).astype(
                                np.float32))
                    except Exception:
                        _hfS = None
                    _gy = 0
                    while _gy < _ch:
                        _gx = 0
                        while _gx < _cw:
                            _win = mm[_gy:_gy + _cell,
                                         _gx:_gx + _cell]
                            if int(_win.sum()) >= 200:
                                _pad = np.zeros(mm.shape, np.uint8)
                                _pad[_gy:_gy + _cell,
                                        _gx:_gx + _cell] = \
                                    _win.astype(np.uint8) * 255
                                _ring2 = (cv2.dilate(
                                    _pad, _k) > 0) & (~mm)
                                if int(_ring2.sum()) >= 40:
                                    _rngC = _sic2[
                                        _ring2].astype(np.float32)
                                    _flC = _rc3[
                                        _gy:_gy + _cell,
                                        _gx:_gx + _cell][
                                            _win].astype(np.float32)
                                    if _flC.shape[0] >= 40:
                                        _rmedC = np.median(
                                            _rngC, axis=0)
# رنگِ غالب: سهمِ پیکسلهایِ حلقه
# که در ≤۳۰ از میانهاند — بهتر از
# std (خطِ دیوار/دورخطِ نازک در
# حلقهٔ سالم دیگر رد نمیکند)
                                        _fracC = float((np.max(
                                            np.abs(_rngC
                                                   - _rmedC),
                                            axis=1) <= 30.0).mean())
                                        _fmedC = np.median(
                                            _flC, axis=0)
                                        _fstdC = float(np.std(
                                            _flC, axis=0).max())
                                        _rstdC = float(np.std(
                                            _rngC, axis=0).max())
                                        _hfC = 0.0
                                        if _hfS is not None:
                                            try:
                                                _hfC = float(np.median(
                                                    _hfS[_ring2]))
                                            except Exception:
                                                _hfC = 0.0
                                        _dch = float(np.max(np.abs(
                                            _fmedC - _rmedC)))
# قانونِ «کروما یا
# قطب»: پرِ غلطِ قابلِ درمان فقط
# (الف) جابهجاییِ کرومایی است
# (کانالها با نسبتِ نابرابر
# جابهجا شدهاند — زرد رویِ آسمان)
# یا (ب) حلقهٔ قطبیِ ناب (سفیدِ
# ≥۲۳۵/سیاهِ ≤۷۰ — بلوکِ خاکستری
# رویِ حبابِ سفید / پرِ سفید رویِ
# پنلِ سیاه). «همفامِ تیرهترِ
# تناسبی» رویِ زمینهٔ میانه (سایهٔ
# پوست/مو — img4_s02: پیشانی) =
# بازسازیِ قانونیِ LaMa → دست
# نمیزیم.
                                        _rel = ((_rmedC - _fmedC)
                                                   / np.maximum(_rmedC,
                                                                40.0))
                                        _chroma = float(np.max(np.abs(
                                            _rel - np.median(_rel)))) \
                                            >= 0.25
                                        _extreme = (
                                            (float(np.min(_rmedC))
                                             >= 200.0)
                                            or (float(np.max(_rmedC))
                                                <= 70.0))
# گاردِ سه‌گانه: رنگِ غالب ≥۵۵٪
# «و» stdِ کانالیِ حلقه ≤۳۴ «و»
# hfِ حلقه ≤۶ — هنرِ هموارنما
# (مو/پوست) بافت/پراکندگی دارد
# بازسازیِ LaMa رویِ چنین حلقههایی
# قانونی است و دست نمی‌زنیم.
                                        if (_fracC >= 0.55
                                                and _rstdC <= 34.0
                                                and _hfC <= 6.0
                                                and _fstdC <= 46.0
                                                and _dch >= 48.0
                                                and (_chroma
                                                     or _extreme)):
# گاردِ «حلقه باید
# نمایندهٔ زمینهٔ زیرِ پنجره
# باشد» (همان درسِ 228): پنجرهٔ
# متنِ رویِ دیوارِ روشن که
# حلقه‌اش به مویِ قهوهایِ
# شخصِ زیرش میخورد (9.jpg:
# حلقه=[100,102,166] ولی پرِ
# درست=[213,213,221]) → رنگِ
# حلقه رویِ پرِ سالم «هارمونیک»
# میشود = «مستطیلِ قهوهای».
# میانهٔ لومیایِ «زیرِ پنجره در
# اورجینال» (زمینهٔ اکثریت) با
# لومیایِ حلقه سنجیده میشود
# فاصلهٔ >۶۰ = حلقه زمینهٔ
# دیگری است → پنجره دستنخورده.
# سنجشِ «پر در
# برابرِ زمینهٔ زیرِ خودِ
# پنجره»: زمینهٔ زیر = قطبِ
# روشنِ اورجینالِ زیرِ ماسک
# (جوهرِ متن اقلیت است
# صدکِ ۷۵ ≈ زمینه). اگر پر با
# آن همرنگ بود، پر درست است و
# حلقه (که هنرِ مجاور را
# میبیند — مویِ قهوهای/کتِ
# تیره) حقِ قضاوت ندارد.
                                            _skip = False
                                            try:
                                                _uw = _sic2[
                                                    _gy:_gy + _cell,
                                                    _gx:_gx + _cell
                                                ][_win]
                                                if _uw.shape[0] >= 40:
                                                    _ulb = float(np.percentile(
                                                        0.299 * _uw[:, 2]
                                                        + 0.587 * _uw[:, 1]
                                                        + 0.114 * _uw[:, 0],
                                                        75.0))
                                                    _flb = float(
                                                        0.299 * _fmedC[2]
                                                        + 0.587 * _fmedC[1]
                                                        + 0.114 * _fmedC[0])
                                                    if abs(_flb
                                                           - _ulb) < 45.0:
                                                        if os.environ.get(
                                                                "MANGA_GUARD_DBG"):
                                                            print(
                                                                f"      [227d"
                                                                f"241] win@("
                                                                f"{_gx + cx0},"
                                                                f"{_gy + cy0})"
                                                                f" پر==زمینهٔ"
                                                                f" زیر ({_flb:.0f}"
                                                                f"≈{_ulb:.0f})"
                                                                f" → رد",
                                                                flush=True)
# False = حلقه
# نمایندهٔ زمینهٔ
# زیرِ پنجره نیست
# سرایت هم حقِ
# ترمیم ندارد
                                                        _wins.append(
                                                            (False, _gy,
                                                             _gx,
                                                             _win,
                                                             _fmedC,
                                                             _dch,
                                                             _rmedC,
                                                             _fstdC,
                                                             _fracC,
                                                             _rstdC,
                                                             _hfC))
                                                        _skip = True
                                            except Exception:
                                                pass
                                            if not _skip:
                                                _tofix.append(
                                                    (_gy, _gx, _win,
                                                     _fmedC, _dch,
                                                     _rmedC, "",
                                                     _fracC, _rstdC,
                                                     _hfC, _fstdC))
                                        else:
                                            _wins.append(
                                                (True, _gy, _gx,
                                                 _win, _fmedC,
                                                 _dch, _rmedC,
                                                 _fstdC, _fracC,
                                                 _rstdC, _hfC))
                            _gx += _cell
                        _gy += _cell
# دورِ سرایتِ رنگ: پنجرهٔ ترمیم‌نشده که «پرِ»اش همان
# رنگِ غلطِ پنجرهٔ ترمیم‌شده است (Δ≤۱۲ — همان لکهٔ
# LaMa ادامه دارد) و با رنگِ غالبِ حلقهٔ خودش هم
# نمیخواند (غالبِ ≥۴۰٪، Δ≥۴۸) → همان درمان؛ تا لبهٔ
# لکه نصفه نماند (پنجره‌های مرزیِ آسمان+زرد).
                    _fm2 = [t[3] for t in _tofix]
                    for (_dmy, _gy, _gx, _win, _fmedC,
                         _dch, _rmedC, _fstdC, _fracC,
                         _rstdC, _hfC) in _wins:
# سرایت بدونِ گاردِ rstd: پرِ این پنجره عینِ پرِ
# غلطِ پنجرهٔ ترمیم‌شده است (Δ≤۱۲) — یعنی همان
# لکهی LaMa ادامه دارد، نه بازسازیِ هنر؛ گاردِ
# هنرِ متقارن لازم نیست. مرزهایِ دو رنگِ همپوشان
# (آسمان+زرد) همین‌جا ترمیم میشوند. hfِ هنری همچنان
# رد میشود (بافتِ ریز = بازسازیِ قانونیِ LaMa).
                        if not _dmy:
                            continue  # پنجرهٔ «حلقه≠زمینه» ترمیم/سرایت ممنوع
                        if _fstdC > 46.0 or _hfC > 6.0 \
                                or _fracC < 0.40 or _dch < 48.0:
                            continue
# قانونِ کروما/قطب اینجا هم (لنگرِ سرایت معاف
# نیست — پرِ همفامِ تیرهتر تناسبی رد).
                        if any(float(np.max(np.abs(
                                _fmedC - _f2))) <= 12.0
                               for _f2 in _fm2):
                            _tofix.append(
                                (_gy, _gx, _win, _fmedC,
                                 _dch, _rmedC, "(سرایت)",
                                 _fracC, _rstdC, _hfC,
                                 _fstdC))
# یک پخشِ واحد برای «همهٔ» پنجرههایِ تصمیمشده:
# مرز = پیکسلهایِ اصلِ بیرونِ ماسک + پرهایِ درستِ
# داخلِ ماسک (پنجرهٔ زرد-روی-زرد مرزِ درست میماند)
# نه پخشِ تک‌پنجره‌ای که از لکهٔ همسایه آلوده میشد.
                    if _tofix:
# پرِ «محلی» به‌ازایِ پنجره: برازشِ صفحهٔ
# z=a+bx+cy رویِ زیرمجموعهٔ غالبِ حلقهٔ «همان
# پنجره» (بدون نشتِ رنگِ حبابِ همسایه — پخش/
# میانگینِ جعبه‌ای زردِ #02 را تا آسمانِ #04
# میکشید)؛ بعدِ پر، نوارِ لبهٔ ۴px با تار کردن
# نرم میشود تا درزِ پنجرهها/findها دیده نشود.
                        try:
                            _union = np.zeros(mm.shape, bool)
                            for (_gyF, _gxF, _winF, _fmedF, _dchF,
                                 _rmedF, _whyF, _fracd, _rstdd,
                                 _hfd, _fstdd) in _tofix:
                                _union[_gyF:_gyF + _cell,
                                          _gxF:_gxF + _cell] |= _winF
                            for (_gyF, _gxF, _winF, _fmedF, _dchF,
                                 _rmedF, _whyF, _fracd, _rstdd,
                                 _hfd, _fstdd) in _tofix:
                                _padF = np.zeros(mm.shape, np.uint8)
                                _padF[_gyF:_gyF + _cell,
                                      _gxF:_gxF + _cell] = \
                                    _winF.astype(np.uint8) * 255
                                _winfF = _padF > 0
                                _ringF = (cv2.dilate(
                                    _padF, _k) > 0) & (~mm)
                                _wyF, _wxF = np.nonzero(_winfF)
                                if _wyF.size == 0:
                                    continue
# انتسابِ فاصله‌ای: فقط پیکسلهایِ ماسکی
# که به «حلقهٔ غالب» نزدیکترند پر میشوند —
# سمتِ دیگری از پنجرهٔ مرزی (نزدیکِ رنگِ
# دیگر) دستنخورده میماند (Voronoi ساده).
                                _selF = _winfF.copy()
                                _planeImgF = None
                                _hasPF = None
                                _selOFok = None
                                if int(_ringF.sum()) >= 60:
                                    _ryF, _rxF = np.nonzero(_ringF)
                                    _rcF = _sic2[_ringF].astype(
                                        np.float32)
                                    _domF = (np.max(np.abs(
                                        _rcF - _rmedF),
                                        axis=1) <= 30.0)
                                    _domPF = np.zeros(mm.shape, np.uint8)
                                    _othPF = np.zeros(mm.shape, np.uint8)
                                    if int(_domF.sum()) >= 40:
                                        _domPF[_ryF[_domF],
                                               _rxF[_domF]] = 255
                                    _othPF[_ryF[~_domF],
                                           _rxF[~_domF]] = 255
                                    if (_domPF > 0).any() \
                                            and (_othPF > 0).any():
                                        _ddF = cv2.distanceTransform(
                                            ((_domPF == 0) * 255).astype(
                                                np.uint8),
                                            cv2.DIST_L2, 3)
                                        _doF = cv2.distanceTransform(
                                            ((_othPF == 0) * 255).astype(
                                                np.uint8),
                                            cv2.DIST_L2, 3)
                                        _selF = _winfF & (_ddF <= _doF)
                                        _selOF = _winfF & (_ddF > _doF)
# سمتِ «دیگر» هم پر میشود — با
# برازشِ حلقهٔ خودش (پنجرهٔ مرزی:
# هر سمت رنگِ خودش را میگیرد؛ وگرنه
# لکهٔ غلطِ آن سمت سرِ جایش میماند)
                                        try:
                                            _ryO = _ryF[~_domF]
                                            _rxO = _rxF[~_domF]
                                            _rcO = _rcF[~_domF]
                                            if (_ryO.size >= 60
                                                    and _selOF.any()):
                                                _medO = np.median(
                                                    _rcO, axis=0)
                                                _uniO = (np.max(np.abs(
                                                    _rcO - _medO),
                                                    axis=1) <= 30.0)
                                                if float(
                                                        _uniO.mean()) >= 0.6:
                                                    _AOF = np.stack([
                                                        np.ones(
                                                            _rxO.size,
                                                            np.float32),
                                                        _rxO.astype(
                                                            np.float32),
                                                        _ryO.astype(
                                                            np.float32)],
                                                        axis=1)
                                                    _coefOF, *_ = \
                                                        np.linalg.lstsq(
                                                            _AOF, _rcO,
                                                            rcond=None)
                                                    try:
                                                        _mSlO = float(
                                                            np.max(np.abs(
                                                                _coefOF[
                                                                    1:, :])))
                                                    except Exception:
                                                        _mSlO = 999.0
                                                    if (_mSlO * _cell
                                                            <= 110.0):
                                                        _syO, _sxO = \
                                                            np.nonzero(
                                                                _selOF)
                                                        _POF = np.stack([
                                                            np.ones(
                                                                _syO.size,
                                                                np.float32),
                                                            _sxO.astype(
                                                                np.float32),
                                                            _syO.astype(
                                                                np.float32)],
                                                            axis=1)
                                                        if _planeImgF \
                                                                is None:
                                                            _planeImgF = \
                                                                np.zeros(
                                                                    mm.shape
                                                                    + (3,),
                                                                    np.float32)
                                                            _hasPF = \
                                                                np.zeros(
                                                                    mm.shape,
                                                                    bool)
                                                        _planeImgF[
                                                            _syO, _sxO] = \
                                                            _POF @ _coefOF
                                                        _hasPF[
                                                            _syO, _sxO] = \
                                                            True
                                                        _selOFok = _selOF
                                                        _union |= \
                                                            _selOF
                                        except Exception:
                                            pass
                                    if int(_domF.sum()) >= 60:
                                        try:
                                            _ryD = _ryF[_domF]
                                            _rxD = _rxF[_domF]
                                            _rcD = _rcF[_domF]
                                            _AF = np.stack([
                                                np.ones(_rxD.size,
                                                        np.float32),
                                                _rxD.astype(np.float32),
                                                _ryD.astype(np.float32)],
                                                axis=1)
                                            _coefF, *_ = \
                                                np.linalg.lstsq(
                                                    _AF, _rcD,
                                                    rcond=None)
                                            try:
                                                _maxSlopeF = float(
                                                    np.max(np.abs(
                                                        _coefF[1:, :])))
                                            except Exception:
                                                _maxSlopeF = 999.0
                                            if (_maxSlopeF * _cell
                                                    <= 110.0
                                                    and _selF.any()):
                                                _syF, _sxF = np.nonzero(
                                                    _selF)
                                                _PF = np.stack([
                                                    np.ones(
                                                        _syF.size,
                                                        np.float32),
                                                    _sxF.astype(
                                                        np.float32),
                                                    _syF.astype(
                                                        np.float32)],
                                                    axis=1)
                                                if _planeImgF is None:
                                                    _planeImgF = np.zeros(
                                                        mm.shape + (3,),
                                                        np.float32)
                                                    _hasPF = np.zeros(
                                                        mm.shape, bool)
                                                _planeImgF[_syF, _sxF] = \
                                                    _PF @ _coefF
                                                _hasPF[_syF, _sxF] = True
                                        except Exception:
                                            pass
                                _useF = _selF if _selOFok is None \
                                    else (_selF | _selOFok)
                                _union |= _useF
                                if not _useF.any():
                                    continue
                                _subF = _rc3[_gyF:_gyF + _cell,
                                               _gxF:_gxF + _cell]
                                _subW = _useF[_gyF:_gyF + _cell,
                                              _gxF:_gxF + _cell]
                                _flatF = np.clip(
                                    np.rint(np.asarray(
                                        _rmedF, np.float32)),
                                    0, 255).astype(np.uint8)
                                if _planeImgF is None or _hasPF is None:
                                    _subF[_subW] = _flatF
                                else:
                                    _pwF = _planeImgF[
                                        _gyF:_gyF + _cell,
                                        _gxF:_gxF + _cell]
                                    _hwF = _hasPF[
                                        _gyF:_gyF + _cell,
                                        _gxF:_gxF + _cell]
                                    _subF[_subW] = _flatF
                                    _selP = _subW & _hwF
                                    if _selP.any():
                                        _subF[_selP] = np.clip(
                                            np.rint(_pwF),
                                            0, 255).astype(
                                                np.uint8)[_selP]
# نرمسازیِ لبه: نوارِ ۴px دورِ اجتماعِ
# پنجرههایِ پرشده با میانگینِ ۹px مینشیند
                            _edgeF = cv2.erode(
                                _union.astype(np.uint8),
                                np.ones((9, 9), np.uint8)) > 0
                            _bandF = _union & (~_edgeF)
                            if _bandF.any():
                                _blE = cv2.blur(
                                    _rc3.astype(np.float32), (9, 9))
                                _rc3[_bandF] = np.clip(
                                    np.rint(_blE), 0,
                                    255).astype(np.uint8)[_bandF]
                        except Exception:
                            for (_gyF, _gxF, _winF, _fmedF, _dchF,
                                 _rmedF, _whyF, _fracd, _rstdd,
                                 _hfd, _fstdd) in _tofix:
                                _colF = np.zeros(_rc3.shape, np.uint8)
                                _colF[:, :] = np.clip(
                                    np.rint(_rmedF),
                                    0, 255).astype(np.uint8)
                                _subF = _rc3[_gyF:_gyF + _cell,
                                               _gxF:_gxF + _cell]
                                _subF[_winF] = _colF[
                                    _gyF:_gyF + _cell,
                                    _gxF:_gxF + _cell][_winF]
                        for (_gyF, _gxF, _winF, _fmedF, _dchF, _rmedF,
                             _whyF, _fracd, _rstdd, _hfd,
                             _fstdd) in _tofix:
                            _n_rej += 1
                            print(f"    [🛡227] پرِ رنگِ غلط رد شد "
                                  f"@({cx0 + _gxF},{cy0 + _gyF}) "
                                  f"px={int(_winF.sum())} "
                                  f"Δch={_dchF:.0f} "
                                  f"حلقه={_rmedF.round(0).tolist()} "
                                  f"پر={_fmedF.round(0).tolist()}) "
                                  f"{_whyF} → پرِ هارمونیکِ محلی",
                                  flush=True)
                            try:
                                print(f"    [🛡227stats] frac="
                                      f"{_fracd:.2f} rstd="
                                      f"{_rstdd:.0f} hf="
                                      f"{_hfd:.1f} fstd="
                                      f"{_fstdd:.0f}",
                                      flush=True)
                            except Exception:
                                pass
                except Exception:
                    pass
                _gcr = _g_org[oy:oy + dm.shape[0], ox:ox + dm.shape[1]]
                _intm = self._bubble_interior_mask(_gcr, dm, erode_iters=1)
                try:
                    _dumpd = os.environ.get("MANGA_GUARD_DUMP")
                    if _dumpd:
                        _di = int(c[0]) if len(c) > 0 else 0
                        _dj = int(c[1]) if len(c) > 1 else 0
                        cv2.imwrite(os.path.join(
                            _dumpd, f"g_{_di}_{_dj}_gcr.png"), _gcr)
                        cv2.imwrite(os.path.join(
                            _dumpd, f"g_{_di}_{_dj}_dm.png"), dm)
                        if _intm is not None:
                            cv2.imwrite(os.path.join(
                                _dumpd, f"g_{_di}_{_dj}_intm.png"), _intm)
                except Exception:
                    pass
                if _intm is None or int(cv2.countNonZero(_intm)) < 400:
                    if _dbg:
                        print(f"      [🛡dbg] ({cx0},{cy0}) interior invalid/"
                              f"small", flush=True)
                    continue
                _fa_in = float(cv2.countNonZero(_intm))
                _med_i = float(np.median(_gcr[_intm > 0]))
                _cov = float(np.count_nonzero(mm & (_intm > 0))) / _fa_in
                if _dbg:
                    print(f"      [🛡dbg] ({cx0},{cy0}) msk={_n_mm} "
                          f"int={_fa_in:.0f} med_i={_med_i:.0f} "
                          f"cov={_cov:.2f}", flush=True)
# فقط «حبابِ واقعی» — رویِ عکس (پاراگرافِ روی حصار در
# 9.jpg) ناحیهٔ روشنِ دیوار «حبابِ سفید» خوانده می‌شد و
# بازسازیِ درستِ LaMa (حصار/درخت) با پرِ تخت جایگزین می‌شد
# → لکهٔ بژِ بزرگ. ولی حبابِ نیمه‌شفاف (chinese01) دیوارِ
# «روشنِ یکنواخت» دارد — پس: دیوارِ تیره «یا» حلقهٔ
# یکنواختِ روشن + اینتریورِ یکنواخت + بدونِ نشتِ ۴لبه.
# اندازه‌گیریِ واقعی: حصار=ring_std ۴۳.۶/uniform ۰.۶۰ —
# حباب=ring_std ۲۱.۱/uniform ۰.۸۶
                _wall_ok = False
                _uni = 0.0
                _t4 = 4
                _ring_blk = False
                try:
                    _ring_in = (cv2.dilate(_intm, np.ones((5, 5),
                                np.uint8)) > 0) & (_intm == 0)
# cv2.countNonZero روی آرایهٔ bool exception
# می‌داد → except → _ring_blk=True → مسیرِ ok49 از
# همیشه مُرده بود و همیشه فال‌بک اجرا می‌شد!
                    _n_ring = int(np.count_nonzero(_ring_in))
                    if _n_ring < 30:
                        if _dbg:
                            print(f"      [🛡dbg] ring tiny {_n_ring}", flush=True)
                        _ring_blk = True
                    else:
                        _med_i = float(np.median(_gcr[_intm > 0]))
                        _ring_med = float(np.median(_gcr[_ring_in]))
                        _ring_std = float(np.std(_gcr[_ring_in]))
                        _wall_ok = (_ring_med <= _med_i - 40.0) or (
                            _ring_std <= 30.0 and _ring_med >= _med_i - 60.0)
                        _uni = float((_gcr[_intm > 0] >= _med_i - 30.0).mean())
                        _t4 = 0
                        for _ln in (_intm[0, :], _intm[-1, :], _intm[:, 0],
                                    _intm[:, -1]):
                            if int(np.count_nonzero(_ln)) >= 6:
                                _t4 += 1
                        if _dbg:
                            print(f"      [🛡dbg] ring_med={_ring_med:.0f} "
                                  f"ring_std={_ring_std:.0f} "
                                  f"wall_ok={_wall_ok} "
                                  f"uni={_uni:.2f} t4={_t4}", flush=True)
                except Exception:
                    _ring_blk = True
# نشتِ اینتریور (دو صورتِ مختلف):
# ۱) حبابِ لبهٔ صفحه/دیوارِ شکافته روی زمینهٔ سفید — لاگِ گوشیِ
# حبابِ «YOU'RE LEAVING…» → اینتریور از شکافِ دیوار
# به پنلِ بیرون نشت می‌کند (int≈۴۱Kpx، t4=4، wall_ok=False)
# → حبابِ واقعی «ناحیهٔ باز» خوانده شد → توهمِ LaMa (صورتِ
# خاکستری + لکهٔ سیاه) قبول شد.
# ۲) حبابِ روی هنرِ تیره — «OH BOY…» روی نیمکت: نشت به
# نیمکتِ قهوه‌ای med_i را به ~۱۴۰ می‌کاهد → «حبابِ سفید
# نیست» → اعتبارسنجی رد → LaMa نیمکت را داخلِ حباب کامل
# می‌کند → حباب کلاً پاک می‌شود (بازتولیدِ سندباکس).
# فال‌بکِ محلیِ مشترک: کامپوننتِ «روشنِ» چسبیده به خودِ ماسک
# (درونِ کراپ) = زمینهٔ سفیدِ محلی. اگر بزرگ (≥۵۵٪ ماسک)
# روشن (med≥۲۲۵)، یکنواخت (≥۷۵٪) و ماسک ≥۴۵٪ آن را بپوشاند
# → «زمینهٔ سفید» معتبر است؛ تصمیمِ نهایی را چکِ badf
# (توهمِ تیره) می‌گیرد. عکس/هنر (بافتِ تیره/مخلوط) رد می‌شود
# (اندازه‌گیری: همهٔ نواحیِ عکسِ 9.jpg رد بدونِ رگرسیون).
# گیتِ «متنِ داخلِ اینتریور»: اعتبار‌سنجیِ ضدتوهم فقط
# وقتی معنا دارد که خودِ متنِ عضو عمدتاً «داخلِ همان زمینهٔ
# سفیدِ تأییدشده» باشد (حباب). کپشنِ رویِ هنر (مثلِ «AND TO
# REQUIRE…» روی کت/چوب در ۹.jpg): فقط ~۲۵٪ ماسک داخلِ
# اینتریورِ (میزِ سفید) است → بازسازیِ تیرهٔ درستِ LaMa با
# bg_medِ «میز» سنجیده می‌شد → ۶۵٪ «توهم» خوانده شد → عضو به
# اصلِ خودش برمی‌گشت → متنِ کامل می‌ماند. حالا اگر متنِ
# عضو داخلِ اینتریورِ سفیدِ نباشد، اصلاً اعتبارسنجی نمی‌شود
# و خروجیِ LaMa (بازسازیِ هنر) قبول می‌شود.
                _m_in_i = (float(np.count_nonzero(mm & (_intm > 0)))
                           / max(1, _n_mm))
                _ok = (_med_i >= 185.0 and _cov >= 0.45 and not _ring_blk
                         and _wall_ok and _uni >= 0.80 and _t4 < 4
                         and _m_in_i >= 0.55)
                if _dbg:
                    print(f"      [🛡dbg] m_in_i={_m_in_i:.2f}", flush=True)
                _fb_comp = None
                if not _ok:
                    try:
                        _bmk = (_gcr >= 180.0).astype(np.uint8) * 255
                        _bmk = cv2.morphologyEx(
                            _bmk, cv2.MORPH_CLOSE,
                            np.ones((5, 5), np.uint8))
                        _n8, _l8 = cv2.connectedComponents(
                            _bmk, connectivity=4)
                        _sdm = (cv2.dilate(dm, np.ones((3, 3),
                                               np.uint8)) > 0) & (_bmk > 0)
                        _lbs = _l8[_sdm]
                        _vls, _cns = np.unique(_lbs[_lbs > 0],
                                               return_counts=True)
                        if not len(_vls):
                            if _dbg:
                                print(f"      [🛡dbg] leak-fallback: "
                                      f"no bright seed → skip", flush=True)
                            continue
                        _fb_comp = (_l8 == _vls[int(np.argmax(_cns))])
# کامپوننتِ روشن گاهی از شکافِ دیوار به
# هایلایتِ روشنِ هنرِ اطراف هم می‌رسد (OH BOY: نیمکتِ
# روشن) → پر تا آن‌جا می‌رود و بلاب می‌سازد. پلِ باریک
# را با فرسایش ببر و بزرگ‌ترین جزء را نگه دار.
                        try:
                            _fe = cv2.erode(_fb_comp.astype(np.uint8),
                                            np.ones((3, 3), np.uint8),
                                            iterations=2)
                            if int(cv2.countNonZero(_fe)) >= 200:
                                _n9, _l9 = cv2.connectedComponents(
                                    _fe, connectivity=4)
                                if _n9 > 1:
                                    _sz = np.bincount(_l9.ravel())
                                    _sz[0] = 0
                                    _fb_comp = cv2.dilate(
                                        (_l9 == int(np.argmax(_sz)))
                                        .astype(np.uint8),
                                        np.ones((3, 3), np.uint8),
                                        iterations=2) > 0
                        except Exception:
                            pass
                        _ca = int(_fb_comp.sum())
                        _cm = float(np.median(_gcr[_fb_comp]))
                        _cu = float((_gcr[_fb_comp] >= _cm - 30.0).mean())
                        _fcov = float(np.count_nonzero(
                            mm & _fb_comp)) / max(1, _ca)
# مثلِ ok49 — متنِ عضو باید عمدتاً داخلِ
# کامپوننتِ روشنِ تأییدشده باشد (کپشنِ رویِ هنر:
# fcov=۰.۵۲ ولی m_in_c=۰.۳۲ → رد )
                        _m_in_c = (float(np.count_nonzero(mm & _fb_comp))
                                   / max(1, _n_mm))
# آستانهٔ uni: ۰.۷۵ → ۰.۶۰. کارت‌هایِ
# معرفی رویِ پنلِ عکس‌دار (GLENDA HOLLY — img1018)
# اینتریورِ کاملاً یکنواخت ندارند (لبهٔ عکس/سایه در
# کامپوننت‌ هست → uni≈۰.۶۶) و اعتبارسنجیِ
# ضدتوهم رد می‌شد → لکهٔ سیاهِ LaMa در باکسِ سفید
# می‌ماند. بقیهٔ گیت‌ها (med≥۲۲۵، fcov≥۰.۴۵
# m_in_c≥۰.۵۵) و خودِ آستانهٔ badf≥۰.۱۰ سرِ
# جایشان‌اند؛ این فقط «اجازهٔ سنجش» است نه اجازهٔ
# پر کردن.
                        _lr_ok = (_ca >= max(600, 0.55 * _n_mm)
                                  and _cm >= 225.0 and _cu >= 0.60
                                  and _fcov >= 0.45 and _m_in_c >= 0.55)
                        if _dbg:
                            print(f"      [🛡dbg] leak-fallback "
                                  f"comp={_ca} med={_cm:.0f} "
                                  f"uni={_cu:.2f} fcov={_fcov:.2f} "
                                  f"m_in_c={_m_in_c:.2f} "
                                  f"ok={_lr_ok}", flush=True)
                        if not _lr_ok:
                            _fb_comp = None
                            continue
                    except Exception:
                        _fb_comp = None
                        continue
                elif _cov < 0.45:
                    continue  # حفرهٔ کوچک → LaMa امن است
                ring = (cv2.dilate(dm, _k) > 0) & (~mm)
                if int(ring.sum()) < 80:
                    continue
                rg = _gcr[ring]
                if rg.size < 80:
                    continue
# درِ «متنِ پاکنشده» (مستقل از قطب): گاردهای
# قبلی فقط «پرِ تیره‌تر از حلقهٔ روشن» را خطرناک میدانستند
# متنِ روشن رویِ زمینهٔ تیره (بنرِ CHAPTER PAGE — img1018
# در کلاسترِ بزرگ) پرِ «روشنِ خودِ متن» میگرفت و بدونِ
# چک میماند = «متنِ قبلی جا میماند». سنجه: از جوهرِ
# اصلیِ عضو (پیکسلهایِ دورِ >۶۰ از میانهٔ حلقه) چه
# نسبتی همچنان دستنخورده مانده؟ ≥۳۵٪ → عضو رد و با
# «قطبِ غالبِ حلقهٔ هر کامپوننت» پر میشود.
                try:
                    _medJ = float(np.median(rg))
                    _sicJ = sub_img[oy:oy + dm.shape[0],
                                    ox:ox + dm.shape[1]]
# _ppc در این نقطه از حلقه هنوز ساخته
# نشده (در بلوکِ ردِ پایینتر ساخته میشود) → نامِ
# تعریفنشده = استثنایِ خاموش = گیتِ بیاثر. اینجا
# نسخهٔ محلیِ خودش را میسازد.
                    _ppcJ = None
                    try:
                        _ppJoin = getattr(self, "_page_protect", None)
                        if _ppJoin is not None:
                            _ptJ = _ppJoin[cy0:cy1, cx0:cx1]
                            if _ptJ.shape[:2] == _sicJ.shape[:2]:
                                _ppcJ = _ptJ
                    except Exception:
                        _ppcJ = None
                    _gJ = cv2.cvtColor(_sicJ, cv2.COLOR_BGR2GRAY)
                    _inkJ = mm & (np.abs(_gJ.astype(np.float32)
                                         - _medJ) > 60.0)
                    if int(_inkJ.sum()) >= 60:
                        _outJ = _g_out[oy:oy + dm.shape[0],
                                       ox:ox + dm.shape[1]]
                        _sameJ = (np.abs(_outJ.astype(np.float32)
                                         - _gJ.astype(np.float32))
                                  <= 30.0)
                        _sfJ = float(_sameJ[_inkJ].mean())
                        if _dbg:
                            print(f"      [🛡dbg] ink-kept gate "
                                  f"same={_sfJ:.2f} "
                                  f"ink={int(_inkJ.sum())}", flush=True)
                        if _sfJ >= 0.35:
# فقط «جوهرِ جامانده» پر شود نه
# کلِ عضو: پرِ تختِ سراسری، بازسازیِ سالمِ
# LaMa را هم نابود میکرد (r0/r7 — bN جهش).
# ماسکِ جراحی = (جوهر ∩ دستنخورده) + ۵px
# محدود به mm؛ رنگ = قطبِ غالبِ حلقهٔ هر
# کامپوننتِ باقیمانده.
# «روشنشدههایِ بيجا»: پیکسلِ
# «زمینه»ای که LaMa روشنش کرده (لکهٔ سفیدِ
# رویِ بنرِ سیاه — r9) نه جوهر است نه
# دستنخورده؛ پرچمش = اصلِ تیرهٔ همرنگِ
# حلقه + خروجیِ ≥۴۵ روشنتر و ≥۱۷۰.
                            _outJf = _outJ.astype(np.float32)
                            _gJf = _gJ.astype(np.float32)
                            _brightJ = (mm & (~_inkJ)
                                        & ((_outJf - _gJf) > 45.0)
                                        & (_outJf >= 170.0))
                            _resJ = (_inkJ & _sameJ) | _brightJ
                            _resJ = cv2.dilate(
                                _resJ.astype(np.uint8),
                                np.ones((11, 11), np.uint8)) > 0
                            _resJ = _resJ & mm
                            if _ppcJ is not None:
                                _resJ = _resJ & (_ppcJ == 0)
                            _rcJ = sub_bgr[oy:oy + dm.shape[0],
                                           ox:ox + dm.shape[1]]
                            try:
                                _unmJ = ~mm
                                _rcJ[_unmJ] = _sicJ[_unmJ]
                            except Exception:
                                _rcJ[:] = _sicJ
                            try:
# رنگِ قطبِ «سطحِ عضو» بهعنوانِ
# پشتیبان: برایِ تودههایِ بزرگِ باقیمانده
# حلقهٔ ۱۳px داخلِ خودِ ماسک گیر میکند
# (ring<۲۰ → skip) و لکه پر نمیشد. حلقهٔ
# عضو (rg) قطبِ درست را دارد → همان رنگ.
                                _poleColM = None
                                try:
                                    if float((rg < 110.0).mean()) >= 0.5:
                                        _selM = ring & (_gJ < 110.0)
                                    else:
                                        _selM = ring & (_gJ >= 110.0)
                                    if int(_selM.sum()) < 8:
                                        _selM = ring
                                    _poleColM = np.median(
                                        _sicJ[_selM].astype(np.float32),
                                        axis=0).astype(np.uint8)
                                except Exception:
                                    _poleColM = None
                                _nJ2, _labJ2 = cv2.connectedComponents(
                                    _resJ.astype(np.uint8), 8)
                                for _iJ2 in range(1, _nJ2):
                                    _cmJ2 = (_labJ2 == _iJ2)
                                    _ringJ2 = (cv2.dilate(
                                        _cmJ2.astype(np.uint8),
                                        np.ones((13, 13), np.uint8)) > 0) \
                                        & (~mm)
                                    _rgJ2 = _gJ[_ringJ2]
                                    if _rgJ2.size < 20:
                                        if _poleColM is not None \
                                                and _cmJ2.any():
                                            _rcJ[_cmJ2] = _poleColM
                                        continue
                                    if float((_rgJ2 < 110.0).mean()) >= 0.5:
                                        _selJ2 = _ringJ2 & (_gJ < 110.0)
                                    else:
                                        _selJ2 = _ringJ2 & (_gJ >= 110.0)
                                    if int(_selJ2.sum()) < 8:
                                        _selJ2 = _ringJ2
                                    _colJ2 = np.median(
                                        _sicJ[_selJ2].astype(np.float32),
                                        axis=0).astype(np.uint8)
                                    if _cmJ2.any():
                                        _rcJ[_cmJ2] = _colJ2
                            except Exception:
                                pass
                            _n_rej += 1
                            try:
                                print(f"    [🛡] ink-kept reject → "
                                      f"residual pole fill "
                                      f"(same={_sfJ:.2f})", flush=True)
                            except Exception:
                                pass
                            continue
                except Exception:
                    if _dbg:
                        import traceback as _tbJ
                        _tbJ.print_exc()
                    pass
                _rb = rg >= 170.0
                _rbm = float(_rb.mean())
# عضوِ فال‌بک‌تأییدشده (اینتریورِ سفیدِ چسبیده به
# ماسک) گیتِ «حلقه عمدتاً سفید» را رد می‌کند — حبابِ روی
# هنرِ تیره (OH BOY روی نیمکت) حلقهٔ تیره دارد ولی داخلش
# سفید است؛ bg_med از پیکسل‌هایِ روشنِ حلقه هنوز درست درمی‌آید.
                if _fb_comp is None and _rbm < 0.50:
# تصویرِ آینهٔ همین گارد: حلقهٔ «تیره»
# (متنِ روشن رویِ بنر/پنلِ سیاه — «CHAPTER 1 PAGE 1»
# در img1018). گاردِ قدیمی اینجا «اعتبارسنجی نه» میکرد
# و پرِ سفیدِ توهمیِ LaMa (یا متنِ پاکنشدهٔ روشن)
# بدونِ چک میماند. حالا: اگر حلقه عمدتاً تیره است و
# پرِ داخلِ ماسک همچنان «روشن» (≥۳۵٪ ≥۱۷۰)، عضو رد
# میشود و ماسکِ عضو با «قطبِ غالبِ حلقهٔ هر کامپوننت»
# پر میشود — بنر سیاهِ خالص، حبابِ رویِ پنلِ تیره
# رنگِ پنل.
                    try:
                        _dkrf = float((rg < 110.0).mean())
                        _fgf = _g_out[oy:oy + dm.shape[0],
                                         ox:ox + dm.shape[1]][mm]
                        _brtf = (float((_fgf >= 170.0).mean())
                                    if _fgf.size else 0.0)
                        if _dbg:
                            print(f"      [🛡dbg] dark-ring mirror "
                                  f"dark={_dkrf:.2f} "
                                  f"fillbright={_brtf:.2f}", flush=True)
                        if _dkrf >= 0.50 and _brtf >= 0.35:
                            _sicF = sub_img[oy:oy + dm.shape[0],
                                            ox:ox + dm.shape[1]]
                            _rcF = sub_bgr[oy:oy + dm.shape[0],
                                           ox:ox + dm.shape[1]]
                            try:
                                _unmF = ~mm
                                _rcF[_unmF] = _sicF[_unmF]
                            except Exception:
                                _rcF[:] = _sicF
                            try:
                                _nF, _labF = cv2.connectedComponents(
                                    mm.astype(np.uint8), 8)
                                _gF = cv2.cvtColor(
                                    _sicF, cv2.COLOR_BGR2GRAY)
                                for _iF in range(1, _nF):
                                    _cmF = (_labF == _iF)
                                    _ringF = (cv2.dilate(
                                        _cmF.astype(np.uint8),
                                        np.ones((13, 13), np.uint8)) > 0) \
                                        & (~mm)
                                    _rgF = _gF[_ringF]
                                    if _rgF.size < 20:
                                        continue
                                    if float((_rgF < 110.0).mean()) >= 0.5:
                                        _selF = _ringF & (_gF < 110.0)
                                    else:
                                        _selF = _ringF & (_gF >= 110.0)
                                    if int(_selF.sum()) < 8:
                                        _selF = _ringF
                                    _colF = np.median(
                                        _sicF[_selF].astype(np.float32),
                                        axis=0).astype(np.uint8)
                                    _tgtF = _cmF if _ppc is None \
                                        else (_cmF & (_ppc == 0))
                                    if _tgtF.any():
                                        _rcF[_tgtF] = _colF
                            except Exception:
                                pass
                            _n_rej += 1
                            try:
                                print(f"    [🛡] dark-ring mirror → "
                                      f"local pole fill (bright fill "
                                      f"on dark ring)", flush=True)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    if _dbg:
                        print(f"      [🛡dbg] ring bright frac {_rbm:.2f} "
                              f"< 0.50 → no validate", flush=True)
                    continue  # دورِ ماسک عمدتاً سفید نیست → اعتبارسنجی نه
                if int(_rb.sum()) < 80:
                    continue
                _bg_med = float(np.median(rg[_rb]))
                fg = _g_out[oy:oy + dm.shape[0], ox:ox + dm.shape[1]][mm]
                _bad = (fg < (_bg_med - 42.0))
                _badf = float(_bad.mean())
                _bm = np.zeros(dm.shape, dtype=np.uint8)
                _bm[mm] = np.where(_bad, 255, 0).astype(np.uint8)
                _bm = cv2.morphologyEx(_bm, cv2.MORPH_OPEN,
                                       np.ones((3, 3), np.uint8))
                _ba = int(cv2.countNonZero(_bm))
                if _dbg:
                    print(f"      [🛡dbg] bg_med={_bg_med:.0f} "
                          f"badf={_badf:.2f} ba={_ba}", flush=True)
                if _badf < 0.10:
                    continue
                if _ba < 40 or _ba < 0.45 * int(_bad.sum()):
                    continue  # نقطه‌هایِ ریز (اسکرین‌تونِ روشن) → توهم نیست
# پرِ تختِ «اینتریور» — کراپ اول به تصویرِ اصل
# برمی‌گردد (خروجیِ توهم‌زدهِ LaMa کامل حذف می‌شود)، بعد فقط
# mm ∩ همسایگیِ کامپوننتِ روشن (اینتریورِ سفیدِ واقعی + ۵px)
# با رنگِ همان کامپوننت پر می‌شود → دیوار/نیمکت/هنرِ اطراف
# دست‌نخورده می‌ماند (بازتولید: b03 و OH BOY تمیز).
                _rc = sub_bgr[oy:oy + dm.shape[0], ox:ox + dm.shape[1]]
                _sic = sub_img[oy:oy + dm.shape[0], ox:ox + dm.shape[1]]
                _pp = getattr(self, "_page_protect", None)
                _ppc = None
                if _pp is not None:
                    try:
                        _pt = _pp[cy0:cy1, cx0:cx1]
                        if _pt.shape[:2] == _rc.shape[:2]:
                            _ppc = _pt
                    except Exception:
                        _ppc = None
                if _fb_comp is not None:
                    _fill_col = np.median(
                        _sic[_fb_comp].astype(np.float32), axis=0)
# «نسخهٔ پرشدهٔ» comp — جزیره‌هایِ تیرهٔ متنِ
# داخلِ زمینهٔ روشن جزوِ آن می‌شوند ولی دیوارِ حباب (که
# از بیرون به زمینهٔ وصل است) هرگز حفره حساب نمی‌شود.
# قبلاً cd_e≈comp خودِ حروف را «حفره» می‌دید → جوهرِ
# وسطِ حروف از پر افت می‌افتاد → شبحِ متن می‌ماند و
# residue-sweep بعداً برای پاک کردنش دیوار را هم می‌بلعید
# (حبابِ کامل پاک می‌شد — chapter-264/8).
                    _ffc = self._fill_holes_mask(_fb_comp)
                    _cm2 = float(np.median(_gcr[_fb_comp]))
                    _ink8 = ((_gcr < _cm2 - 40.0) & (dm > 0) & _ffc)
                    _ink8 = _ink8.astype(np.uint8) * 255
                    _ink8 = cv2.morphologyEx(_ink8, cv2.MORPH_CLOSE,
                                             np.ones((5, 5), np.uint8))
                    _ink8 = cv2.dilate(_ink8, np.ones((5, 5), np.uint8))
                    _ink8[~_ffc] = 0  # سقف: هرگز بیرونِ نسخهٔ پرشده (دیوار)
# نشتِ اینتریور (دمِ بازِ حباب) نباید متن را
# زنده بگذارد: جوهرِ تیرهٔ داخلِ ماسک (بدونِ گیتِ comp)
                    _ink8b = self._mask_ink_only(_gcr, dm, _cm2 - 40.0)
                    _pnt = mm & ((cv2.dilate(
                        _fb_comp.astype(np.uint8),
                        np.ones((3, 3), np.uint8)) > 0) | (_ink8 > 0)
                        | (_ink8b > 0))
                else:
# مسیرِ ok49 هم «پوسته‌ای» شد — قبلاً _pnt=mm
# بود و هر جا ماسک تا دیوار کشیده شده بود، کلِ ناحیه
# (شاملِ دیوار) با رنگِ تخت سفید می‌شد → حباب کامل پاک.
# حالا فقط داخلِ اینتریورِ تأییدشده (±۱px) + جوهرِ تنگِ
# داخلِ آن؛ دیوار/هنرِ بیرونِ اینتریور دست‌نخورده.
                    _fill_col = np.median(
                        _sic[_intm > 0].astype(np.float32), axis=0)
                    _int_d = cv2.dilate(_intm, np.ones((3, 3), np.uint8))
                    _ink9 = ((_gcr < _med_i - 40.0) & (dm > 0) & (_intm > 0))
                    _ink9 = _ink9.astype(np.uint8) * 255
                    _ink9 = cv2.morphologyEx(_ink9, cv2.MORPH_CLOSE,
                                             np.ones((5, 5), np.uint8))
                    _ink9 = cv2.dilate(_ink9, np.ones((5, 5), np.uint8))
                    _ink9[_int_d == 0] = 0
# «متنِ کج/ناقص پاک میشه» و «بعضی متن‌ها
# جا می‌مونه»: ریشه‌اش این بود که اینتریورِ حباب از
# دمِ بازِ حباب نشت می‌کرد → پیکسل‌هایِ ماسکِ متن که
# بیرونِ اینتریور می‌افتادند اصلاً رنگ نمی‌گرفتند و چون
# _rc به «اصل» برمی‌گردد، همان‌جا متن زنده می‌ماند
# (نمونهٔ «I GOT TO QUIT… / BUT YOU CAN'T, RIGHT~?» —
# دو خطِ آخر نصفه پاک می‌شدند). حالا جوهرِ تیرهٔ داخلِ
# ماسک هم رنگ می‌گیرد (دیوارهای کشیده حذف می‌شوند) →
# خطِ متن کامل پاک می‌شود و دیوارِ حباب دست‌نخورده
# می‌ماند.
                    _ink9b = self._mask_ink_only(_gcr, dm, _med_i - 40.0)
                    _pnt = mm & ((_int_d > 0) | (_ink9 > 0) | (_ink9b > 0))
                if _ppc is not None:
                    _pnt = _pnt & (_ppc == 0)
# «بازگشت به اصل» فقط بیرونِ ماسک: قبلاً کلِ
# کراپ به اصل برمی‌گشت (`_rc[:] = _sic`) → هر پیکسلِ متنی
# که رنگ نگرفته بود دوباره متن می‌شد. حالا فقط ناحیهٔ
# بیرونِ ماسک (لغزشِ LaMa) به اصل برمی‌گردد و داخلِ ماسک
# پرِ تخت می‌گیرد → نه متن می‌ماند، نه لکه.
                try:
                    _unm = ~mm
                    _rc[_unm] = _sic[_unm]
                except Exception:
                    _rc[:] = _sic
                if True:
# پسگیریِ «متنِ جامانده در پسگیریِ گارد»:
# _pnt فقط «اینتریور/کامپوننتِ روشن ∪ جوهرِ تیره» را پر
# میکرد؛ متنِ «روشن» رویِ زمینهٔ تیره (بنرِ سیاهِ
# CHAPTER PAGE — img1018) نه در کامپوننتِ روشن بود نه
# جوهرِ تیره → بعدِ ردِ LaMa به اصلِ خودش برمیگشت =
# متنِ سفیدِ کامل رویِ بنر. حالا هر پیکسلِ ماسک که
# «جوهرمانند» است (تفاوتِ >۴۲ با زمینهٔ محلیِ تخمینیِ
# 207b) هم پر میشود؛ پیکسلِ همرنگِ زمینه (دیوار/بافت)
# مثلِ قبل به اصل برمیگردد.
                    _fill2 = None
                    try:
                        _kn = (~mm).astype(np.float32)
                        _sicf = _sic.astype(np.float32) * _kn[..., None]
                        _den = cv2.boxFilter(_kn, -1, (25, 25))
                        _num = cv2.boxFilter(_sicf, -1, (25, 25))
                        _loc = (_num
                                   / np.maximum(_den, 1e-3)[..., None])
# میانگینِ ساده رویِ زمینهٔ «دوقطبی»
# (بنرِ سیاه + حروفِ سفیدِ کنارِ ماسک — img1018)
# رنگِ خاکستریِ ناخالص میدهد. پس پرِ محلی =
# «قطبِ غالبِ محلی» (همان منطقِ دو-قطبیِ 206d):
# در هر پنجره بینِ قطبِ تیره و روشنِ پیکسلهایِ
# معلوم، قطبی که تراکمش بیشتر است برنده میشود —
# رویِ بنرِ سیاه سیاهِ خالص، رویِ حبابِ سفید سفید
# رویِ حبابِ ماتِ رنگی رنگِ مات.
                        try:
                            _gimg = cv2.cvtColor(
                                _sic, cv2.COLOR_BGR2GRAY).astype(np.float32)
                            _drk = ((_gimg < 110.0)
                                       & (_kn > 0)).astype(np.float32)
                            _brt = ((_gimg >= 110.0)
                                       & (_kn > 0)).astype(np.float32)
                            _denD = cv2.boxFilter(_drk, -1, (25, 25))
                            _denB = cv2.boxFilter(_brt, -1, (25, 25))
                            _locD = (cv2.boxFilter(
                                _sic.astype(np.float32) * _drk[..., None],
                                -1, (25, 25))
                                / np.maximum(_denD, 1e-3)[..., None])
                            _locB = (cv2.boxFilter(
                                _sic.astype(np.float32) * _brt[..., None],
                                -1, (25, 25))
                                / np.maximum(_denB, 1e-3)[..., None])
                            _poleD = (_denD >= _denB)[..., None]
                            _locP = np.where(_poleD, _locD, _locB)
                            _valP = np.maximum(_denD, _denB)
                            _loc = np.where(
                                (_valP >= 0.03)[..., None], _locP, _loc)
                        except Exception:
                            pass
                        _fill2 = np.where(
                            (_den >= 0.03)[..., None],
                            _loc.astype(np.uint8),
                            np.broadcast_to(np.asarray(
                                _fill_col, dtype=np.uint8), _loc.shape))
                        try:
# پسگیریِ «متنِ جامانده» به روشِ
# کامپوننت‌محور: تخمینِ پیکسلیِ 207b کنارِ
# حروفِ سفیدِ بنر توسطِ لبههایِ روشنِ بیرونِ
# ماسک آلوده میشد (|g-bg|<42 → پر نشد → متن
# برمیگشت). برای هر کامپوننتِ «ماسکِ بدونِ
# _pnt»: رنگ = قطبِ غالبِ حلقهٔ ۱۳px دورِ
# کامپوننت (پایدار، بدونِ لبههایِ حروف)؛ اگر
# خودِ کامپوننت با آن رنگ فاصلهٔ معنیدار
# داشته = جوهر است → پر.
                            _gSic = cv2.cvtColor(
                                _sic, cv2.COLOR_BGR2GRAY)
                            _resi = mm & (~_pnt)
                            if _ppc is not None:
                                _resi = _resi & (_ppc == 0)
                            _cci = []
                            if _resi.any():
                                _nCi, _labCi = cv2.connectedComponents(
                                    _resi.astype(np.uint8), 8)
                                for _ic in range(1, _nCi):
                                    _cmC = (_labCi == _ic)
                                    _ringC = (cv2.dilate(
                                        _cmC.astype(np.uint8),
                                        np.ones((13, 13), np.uint8)) > 0) \
                                        & (~mm)
                                    _rgC = _gSic[_ringC]
                                    if _rgC.size < 20:
                                        continue
                                    if float((_rgC < 110.0).mean()) >= 0.5:
                                        _selC = _ringC & (_gSic < 110.0)
                                    else:
                                        _selC = _ringC & (_gSic >= 110.0)
                                    if int(_selC.sum()) < 8:
                                        _selC = _ringC
                                    _colC = np.median(
                                        _sic[_selC].astype(np.float32),
                                        axis=0)
                                    _dC = np.abs(
                                        _gSic[_cmC].astype(np.float32)
                                        - (0.299 * _colC[2]
                                           + 0.587 * _colC[1]
                                           + 0.114 * _colC[0]))
                                    if float(_dC.mean()) > 42.0:
                                        _pnt = _pnt | _cmC
                                        _cci.append(
                                            (_cmC, _colC.astype(np.uint8)))
                        except Exception:
                            _cci = []
                    except Exception:
                        _fill2 = None
                        _cci = []
                    if _pnt.any():
                        if _fill2 is not None:
                            _rc[_pnt] = _fill2[_pnt]
                        else:
                            _rc[_pnt] = _fill_col
# رنگِ قطبِ حلقهٔ هر کامپوننتِ
# «جوهرِ شناساییشده» رویِ پرِ عمومی مینشیند
                        try:
                            for _cmC, _colC in (_cci or []):
                                _rc[_cmC] = _colC
                        except Exception:
                            pass
                _n_rej += 1
                try:
                    _dumpd2 = os.environ.get("MANGA_GUARD_DUMP")
                    if _dumpd2:
                        cv2.imwrite(os.path.join(
                            _dumpd2, f"rj_{cx0}_{cy0}_sic.jpg"), _sic)
                        cv2.imwrite(os.path.join(
                            _dumpd2, f"rj_{cx0}_{cy0}_rc.jpg"), _rc)
                        cv2.imwrite(os.path.join(
                            _dumpd2, f"rj_{cx0}_{cy0}_pnt.png"),
                            (_pnt.astype(np.uint8) * 255))
                        cv2.imwrite(os.path.join(
                            _dumpd2, f"rj_{cx0}_{cy0}_dm.png"),
                            (mm.astype(np.uint8) * 255))
                        if _fb_comp is not None:
                            cv2.imwrite(os.path.join(
                                _dumpd2, f"rj_{cx0}_{cy0}_comp.png"),
                                (_fb_comp.astype(np.uint8) * 255))
                except Exception:
                    pass
            if _n_rej:
                try:
                    print(f"    [🛡] {_n_rej} LaMa fill(s) → flat white "
                          "(anti-hallucination)", flush=True)
                except Exception:
                    pass
        except Exception:
            pass

        for c in members:
            cx0, cy0, cx1, cy1, crop_msk = c[:5]
            cx1, cy1 = min(cx1, img_w), min(cy1, img_h)
            if cx1 <= cx0 or cy1 <= cy0:
                continue
# ماسکِ نتیجه هم از پیکسل‌هایِ قفل‌شده تمیز شود
            try:
                _pam = getattr(self, "_prot_all", None)
                if _pam is not None:
                    _pa_c = _pam[cy0:cy1, cx0:cx1]
                    if _pa_c.shape == crop_msk.shape:
                        crop_msk = cv2.bitwise_and(
                            crop_msk, cv2.bitwise_not(_pa_c))
            except Exception:
                pass
            c[4] = cv2.dilate(crop_msk, page_kernel)
            c[5] = sub_bgr[cy0 - ey0:cy1 - ey0, cx0 - ex0:cx1 - ex0]
            c[6] = "LaMa"

    @staticmethod
    def _lama_batch_cap() -> int:
        """ (SRV-H4) — بچینگِ پچ‌هایِ LaMa پیش‌فرضِ خاموش (رویِ
        سرور در هر دو حالتِ CPU/GPU کندتر بود — SRV-H2/H3؛ مسیرِ موازیِ
        قدیمیِ per-patch مثلِ e32bccf پیش‌فرض است). opt-in:
        MANGA_LAMA_BATCH=1 → روشن با سقفِ خودکارِ قدیمی (PC=8؛
        اندروید/رمِ کم=2)؛ MANGA_LAMA_BATCH=N>1 → سقفِ N.
        MANGA_NO_BATCH=1 همچنان خاموشِ قهری (برِ بالایِ opt-in)."""
        try:
            if str(os.environ.get("MANGA_NO_BATCH", "")).strip() == "1":
                return 0
        except Exception:
            pass
        try:
            _n = int(os.environ.get("MANGA_LAMA_BATCH", "0") or 0)
            if _n > 0:
                if _n > 1:
                    return max(1, _n)
# =1 → روشن با سقفِ خودکارِ قدیمی (SRV-G)
                try:
                    if _on_android() or _android_like_env():
                        return 2
                    _av = _sys_avail_ram_gb()
                    if _av is not None and _av < 3.0:
                        return 2
                except Exception:
                    pass
                return 8
        except Exception:
            pass
        return 0

    def _lama_run_groups_batched(self, image: np.ndarray,
                                 groups: List[List[list]],
                                 lama, page_kernel) -> None:
        """-speed (SRV-G phase2) — اجرایِ دسته‌ایِ پچ‌هایِ LaMa-Manga.

        پچ‌هایی که تنسورِ پدشدهٔ «دقیقاً هم‌شکل» دارند (مثلاً همهٔ
        1x3x512x512) در «یک» session.run با بعدِ batch=N می‌روند — همان
        پدینگ/همان ترتیبِ امروز (`_prep_sample` per-sample) و خروجیِ هر
        نمونه در همان ترتیب برش و به همان QC/انتسابِ قبل می‌رود. باکتِ
        تک‌نفره و خطایِ batch → مسیرِ تکیِ امروز با تمامِ فال‌بک‌هایش
        (`_lama_try_fn`). سقفِ batch از `_lama_batch_cap`."""
        _cap = self._lama_batch_cap()
        if _cap <= 0 or not (hasattr(lama, "run_batch_tensors")
                             and hasattr(lama, "_prep_sample")
                             and hasattr(lama, "_finish_sample")):
            for grp in groups:
                try:
                    self._lama_run_group(image, grp, lama, page_kernel)
                except Exception:
                    pass
            return
        _try1 = self._lama_try_fn(lama)
        items = []
        for grp in groups:
            _raise_if_stop()
            try:
                ctx = self._lama_group_prep(image, grp, page_kernel)
            except JobCancelled:
                raise
            except Exception:
                continue
            if ctx is None:
                continue
            if ctx.get("resize_failed"):
                try:
                    print(f"    [!] LaMa group skipped: resize-path failed "
                          f"(box {ctx['pl']}x{ctx['ph']})", flush=True)
                except Exception:
                    pass
                continue
            try:
                t = lama._prep_sample(ctx["run_img"], ctx["run_msk"])
            except JobCancelled:
                raise
            except Exception:
                continue
            if not t.get("has_mask"):
                continue  # امروز هم گروهِ بی‌ماسک return می‌کرد
            items.append((ctx, grp, t))
        if not items:
            return
        buckets: Dict[tuple, list] = {}
        for it in items:
            buckets.setdefault(tuple(it[2]["img_in"].shape), []).append(it)
        if getattr(self, "debug", False):
            try:
                print(f"  [*] LaMa batched: {len(items)}/{len(groups)} patches "
                      f"→ {len(buckets)} shape-bucket(s) (cap={_cap})",
                      flush=True)
            except Exception:
                pass
        for _shape, lst in buckets.items():
            for _k in range(0, len(lst), _cap):
                chunk = lst[_k:_k + _cap]
                if len(chunk) == 1:
                    _ctx, _grp, _t = chunk[0]
                    out = _try1(_ctx["run_img"], _ctx["run_msk"], 640)
                    sub_bgr = self._lama_group_out_to_bgr(_ctx, out)
                    if sub_bgr is not None:
                        self._lama_group_finish(_grp, _ctx, sub_bgr,
                                                page_kernel)
                    continue
                try:
                    outs = lama.run_batch_tensors([c[2] for c in chunk])
                except JobCancelled:
                    raise
                except Exception as _be:
# همان قراردادِ `_lama_try`: مرگِ EP → CPU-safe برایِ
# بقیهٔ ران + ذخیرهٔ «cpu» برایِ ران‌هایِ بعد
                    self._lama_ep_dead = True
                    try:
                        _lama_ep_store(getattr(self, "_lama_model_path", "")
                                       or "", "cpu")
                        print(f"    [!] LaMa batch failed "
                              f"({str(_be)[:90]}) → per-sample fallback",
                              flush=True)
                    except Exception:
                        pass
                    for _ctx, _grp, _t in chunk:
                        out = _try1(_ctx["run_img"], _ctx["run_msk"], 640)
                        sub_bgr = self._lama_group_out_to_bgr(_ctx, out)
                        if sub_bgr is not None:
                            self._lama_group_finish(_grp, _ctx, sub_bgr,
                                                    page_kernel)
                    continue
                for (_ctx, _grp, _t), _oe in zip(chunk, outs):
                    try:
                        pil = lama._finish_sample(_t, _oe)
                    except Exception:
                        continue
                    sub_bgr = self._lama_group_out_to_bgr(_ctx, pil)
                    if sub_bgr is not None:
                        self._lama_group_finish(_grp, _ctx, sub_bgr,
                                                page_kernel)

    @staticmethod
    def _mask_ink_only(gray_crop: np.ndarray, zone: np.ndarray,
                       thr: float) -> np.ndarray:
        """ — جوهرِ تیرهٔ داخلِ ماسک (بدونِ گیتِ اینتریور).

        ریشهٔ «بعضی متن‌ها جا می‌مونه / کج پاک میشه»: اینتریورِ حباب از
        دمِ بازِ حباب (یا شکافِ JPEGِ دیوار) نشت می‌کرد → پیکسل‌هایِ متن
        که بیرونِ اینتریور می‌افتادند در پرِ تختِ ضدتوهم شرکت نمی‌کردند و
        چون کراپ به «اصل» برمی‌گشت، همان متن زنده می‌ماند.

        این تابع جوهرِ تیرهٔ داخلِ ماسک را برمی‌گرداند ولی «ساختارهای
        کشیده» (دیوارِ حباب/قابِ پنل) را حذف می‌کند تا حباب خراب نشود:
        کامپوننتی که قدش ≥ ۲.۵ برابرِ پهنایش و ≥ ۳۰پیکسل باشد = دیوار،
        نه حرف."""
        try:
            if gray_crop is None or zone is None:
                return np.zeros((1, 1), np.uint8)
            ink = ((gray_crop < float(thr)) & (zone > 0)).astype(np.uint8) * 255
            if not ink.any():
                return ink
            ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
            ink = cv2.dilate(ink, np.ones((5, 5), np.uint8))
            n, lab, st, _ = cv2.connectedComponentsWithStats(ink, 8)
            keep = np.zeros_like(ink)
            for i in range(1, n):
                a = int(st[i, cv2.CC_STAT_AREA])
                if a < 8:
                    continue
                cw_ = int(st[i, cv2.CC_STAT_WIDTH])
                ch_ = int(st[i, cv2.CC_STAT_HEIGHT])
# دیوار/قاب: بلند و نازک (عمودی) یا خیلی کشیده (افقی)
                if ch_ >= 30 and ch_ >= 2.5 * cw_:
                    continue
                if cw_ >= 120 and cw_ >= 6.0 * max(1, ch_):
                    continue
                keep[lab == i] = 255
            return keep
        except Exception:
            return np.zeros((1, 1), np.uint8)

    def _clean_level(self) -> str:
        try:
            lv = (os.environ.get("MANGA_CLEAN_LEVEL", "quality")
                  or "quality").strip().lower()
        except Exception:
            lv = "quality"
        return lv if lv in ("quality", "fast") else "quality"

    def _lama_workers_auto(self) -> int:
# سرعتِ LaMa — درخواستِ کاربر «سرعتِ پاکسازیِ lama سریع‌تر کن».
# روی گوشیِ ۸ هسته‌ای قبلاً فقط ۶ پچِ موازی اجرا می‌شد (۲ هسته بیکار)
# → حالا تا ۸ پچِ موازی (همهٔ هسته‌ها)؛ دینامیکِ لاما در سقفِ ۳۸۴px
# حافظهٔ هر رشته کم است و fallbackِ OpenCV در رمِ واقعاً کم سرِ جاست.
        try:
            _wa = int(os.environ.get("MANGA_LAMA_WORKERS", "0") or 0)
            if _wa > 0:
                return max(1, min(_wa, 8))
            try:
                _av = float(self._available_ram_gb())
            except Exception:
                _av = 0.0
            try:
                _cores = self._cpu_core_count()
            except Exception:
                _cores = 0
            if _cores >= 8:
                return 8 if _av >= 0.25 else 4
            if _cores >= 6:
                return 5 if _av >= 0.25 else 3
            return 2 if _av >= 0.5 else 1
        except Exception:
            return 1

    def _lama_rescue_boxes(self, cleaned: np.ndarray,
                           boxes: List[Tuple[int, int, int, int, np.ndarray]],
                           page_kernel) -> int:
        if not boxes:
            return 0
        try:
            lama = self._get_lama()
        except Exception:
            lama = None
        if lama is None:
            return 0
        h, w = cleaned.shape[:2]
        members = []
        for (x0, y0, x1, y1, mc) in boxes:
            x1, y1 = min(int(x1), w), min(int(y1), h)
            x0, y0 = max(0, int(x0)), max(0, int(y0))
            if x1 - x0 < 8 or y1 - y0 < 8:
                continue
            msk = np.zeros((y1 - y0, x1 - x0), dtype=np.uint8)
            mh, mw = min(mc.shape[0], y1 - y0), min(mc.shape[1], x1 - x0)
            msk[:mh, :mw] = mc[:mh, :mw]
            members.append([x0, y0, x1, y1, msk, None, ""])
        if not members:
            return 0
        if len(members) > 1:
            try:
                groups = self._group_nearby_patches(members, gap=24)
            except Exception:
                groups = [[m] for m in members]
        else:
            groups = [members]
        try:
            _rw = min(int(self._lama_workers_auto()), len(groups))
        except Exception:
            _rw = 1
        _rw = max(1, min(_rw, len(groups)))
# مانند مسیرِ اصلی — پچِ کم → نخِ بیشتر برای هر پچ
        try:
            _rcores = int(self._cpu_core_count())
        except Exception:
            _rcores = 0
        _rthr = (1 if _rw >= 5
                 else max(1, min(4, max(2, _rcores) // _rw)))
        try:
            lama = self._get_lama(threads=_rthr) or lama
        except Exception:
            pass
        _no_batch_r = self._lama_batch_cap() <= 0 \
            or not hasattr(lama, "run_batch_tensors")
        if not _no_batch_r:
# speed (SRV-G phase2) — بچینگِ rescue هم مثلِ مسیرِ اصلی
            self._lama_run_groups_batched(cleaned, groups, lama, page_kernel)
        elif _rw > 1:
            try:
                _rt = max(1, int(getattr(lama, "thr_used", 1) or 1))
                print(f"  [🩹] {_rw} parallel rescue patches × {_rt} thread(s)")
            except Exception:
                pass
            _rex = ThreadPoolExecutor(max_workers=_rw)
            _rfuts = []
            try:
                for grp in groups:
                    _rfuts.append(_rex.submit(self._lama_run_group,
                                              cleaned, grp, lama, page_kernel))
                for _rf in _rfuts:
                    try:
                        _rf.result(timeout=600)
                    except Exception:
                        pass
            finally:
                try:
                    _rex.shutdown(wait=True)
                except Exception:
                    pass
        else:
            for grp in groups:
                try:
                    self._lama_run_group(cleaned, grp, lama, page_kernel)
                except Exception:
                    pass
        n_ok = 0
        _pp = getattr(self, "_page_protect", None)
        for c in members:
            if c[6] != "LaMa" or c[5] is None:
                continue
            cx0, cy0, cx1, cy1, dm = c[0], c[1], c[2], c[3], c[4]
            mm = dm > 0
# دیوارِ محافظت‌شده در rescue هم دست‌نخورده بماند
            if _pp is not None:
                try:
                    mm = mm & (_pp[cy0:cy1, cx0:cx1] == 0)
                except Exception:
                    pass
            cleaned[cy0:cy1, cx0:cx1][mm] = c[5][mm]
            n_ok += 1
        return n_ok

    @staticmethod
    def _telea_fix_boxes(cleaned: np.ndarray,
                         boxes: List[Tuple[int, int, int, int, np.ndarray]]) -> int:
        n = 0
        for (x0, y0, x1, y1, mc) in boxes:
            try:
                cc = cleaned[y0:y1, x0:x1]
                if cc.shape[:2] != mc.shape[:2]:
                    mh = min(cc.shape[0], mc.shape[0])
                    mw = min(cc.shape[1], mc.shape[1])
                    sub = cc[:mh, :mw]
                    msub = mc[:mh, :mw]
                else:
                    sub = cc
                    msub = mc
# TELEA رویِ زمینهٔ تختِ روشن (داخلِ حبابِ سفید)
# خاکستریِ لکه‌دار/مستطیلِ محو می‌سازد (لاگِ گوشی: حباب‌هایِ
# 002 — «لگه میزاره»). اگر رینگِ اطرافِ ماسک تخت و روشن است
# → پرکردن با رنگِ خودِ زمینه (همان سبکِ پرکننده‌ها)
# وگرنه مثل قبل TELEA (زمینهٔ بافت‌دار/تیره).
                _done = False
                try:
                    _m = msub > 0
                    _rg = cv2.dilate(msub, np.ones((13, 13), np.uint8)) > 0
                    _ring = _rg & (~_m)
                    if int(_ring.sum()) >= 60 and int(_m.sum()) >= 8:
                        _gg = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
                        _rp = _gg[_ring]
                        _rmed = float(np.median(_rp))
                        _rstd = float(_rp.std())
                        if _rmed >= 150.0 and _rstd <= 14.0:
                            _col = np.median(
                                sub[_ring].reshape(-1, 3), axis=0)
                            out = sub.copy()
                            out[_m] = np.clip(_col, 0, 255).astype(np.uint8)
                            cleaned[y0:y0 + out.shape[0],
                                    x0:x0 + out.shape[1]] = out
                            _done = True
                except Exception:
                    _done = False
                if not _done:
                    sub2 = cv2.inpaint(sub, msub, 6, cv2.INPAINT_TELEA)
                    cleaned[y0:y0 + sub2.shape[0],
                            x0:x0 + sub2.shape[1]] = sub2
                n += 1
            except Exception:
                continue
        return n

    def _enclosure_instant_fill(self, image: np.ndarray, cleaned: np.ndarray,
                                regions: List[TextRegion],
                                mask: np.ndarray,
                                skip_ids=None) -> int:
        """ — پرکردنِ فوریِ متنِ روی محفظهٔ تیرهٔ یکدست (بنرِ هدر
        حبابِ سیاه). مستقیم با TELEA و رنگِ خودِ محفظه پر می‌شود و پیکسل‌ها
        از ماسکِ اصلی حذف می‌شوند تا حلقهٔ کلاسترها دیگر سراغشان نرود —
        چون ringِ پرکننده‌ها روی بنرِ نازک همیشه به بیرون نشت می‌کند و لگه
        می‌سازد."""
        n_fill = 0
        for region in regions:
# ناحیهٔ donor-گسترش‌یافته: پرِ فوری نگیرد تا LaMa
# کلِ داخل را با بافتِ خودش بازسازی کند (حالتِ کیفی)
            if skip_ids and int(getattr(region, "id", -1)) in skip_ids:
                continue
# بنرِ تبلیغ (promo): پرکنندهٔ فوریِ محفظه نباید
# ماسکِ توپرِ بنر را بکُشد (همان حفرهٔ رویِ متنِ بنر)
            if getattr(region, "kind", "") == "promo":
                continue
# ناحیهِ «فقط-جوهر»: پرِ فوریِ محفظه/هاله ممنوع —
# پرکنندهِ میانه‌ای روی هنرِ داخلِ کارت لکهِ تخت می‌گذارد.
# جوهرش با LaMa پاک می‌شود.
            try:
                _ibf = getattr(self, "_lama_ink_boxes", None) or []
                if _ibf:
                    _rx, _ry, _rw, _rh = [
                        int(v) for v in region.rect]
                    _hit = False
                    for _ib in _ibf:
                        if not (_rx + _rw < _ib[0] or _rx > _ib[2]
                                or _ry + _rh < _ib[1]
                                or _ry > _ib[3]):
                            _hit = True
                            break
                    if _hit:
                        continue
            except Exception:
                pass
            _raise_if_stop()
            polys = list(getattr(region, "ocr_polys", None) or [])
            if not polys:
                continue
            try:
                enc = self._enclosure_tight_mask(
                    image, polys,
                    rect=tuple([int(v) for v in region.rect]))
            except Exception:
                enc = None
            if enc is None or not np.any(enc):
                continue
            try:
                ys, xs = np.nonzero(enc)
                h, w = image.shape[:2]
# حاشیهٔ ۲۰px (قبلاً ۱۲): گشادکردنِ ۱۳pxِ ماسکِ
# پرکردن (برجستگیِ متن) باید داخلِ پنجره جا شود
                x0 = max(0, int(xs.min()) - 20)
                y0 = max(0, int(ys.min()) - 20)
                x1 = min(w, int(xs.max()) + 21)
                y1 = min(h, int(ys.max()) + 21)
                if x1 - x0 < 8 or y1 - y0 < 8:
                    continue
                sub = cleaned[y0:y1, x0:x1]
                m2 = cv2.dilate(enc[y0:y1, x0:x1],
                                np.ones((3, 3), np.uint8), iterations=1)
# هاله/درخششِ اطرافِ حروف (نمونه: تیترِ «The
# Crimson Dragon…» که متنِ سفیدِ شعاع‌دار روی کارتِ تیره
# دارد) فقط با m2 پر نمی‌شود و شبحِ روشن جا می‌گذارد.
# پیکسل‌هایِ روشنِ داخلِ خودِ محفظهٔ تیره که نزدیکِ جوهرند
# هم به ماسکِ پرکردن اضافه می‌شوند؛ قابِ تزئینیِ دور از
# متن دست‌نخورده می‌ماند.
                try:
                    _full_c = getattr(self, "_last_enclosure_full", None)
                    if (_full_c is not None
                            and _full_c.shape == enc.shape
                            and int(_full_c.any())):
                        _fc = _full_c[y0:y1, x0:x1] > 0
                        _gg = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
# «نزدیکِ جوهر» نه «نزدیکِ کلِ محفظه»!
# قبلاً دیلهٔ ۲۵ِ خودِ enc بود و در محفظهٔ بزرگ
# (کارتِ img2-r10، حبابِ بزرگ) هر ساختارِ روشنِ
# داخلِ محفظه — قابِ سفیدِ کارت، خطِ حباب — را هم
# «هالهٔ حروف» می‌گرفت و با رنگِ کارت پاک می‌کرد
# («حباب به کل حذف زده» — گزارشِ کاربر).
# حالاseed = ماسکِ خامِ متن (_compose_text_mask)
# اگر خالی بود fallback به enc.
                        try:
                            _ctm = getattr(self, "_compose_text_mask",
                                             None)
                            _mkw = None
                            if (_ctm is not None
                                    and _ctm.shape == enc.shape):
                                _mkw = ((_ctm[y0:y1, x0:x1] > 0)
                                          .astype(np.uint8))
                            if (int(cv2.countNonZero(_mkw)) < 50
                                    if _mkw is not None else True):
                                _mkw = ((enc[y0:y1, x0:x1] > 0)
                                          .astype(np.uint8))
                        except Exception:
                            _mkw = ((enc[y0:y1, x0:x1] > 0)
                                      .astype(np.uint8))
                        _near = cv2.dilate(
                            _mkw,
                            np.ones((25, 25), np.uint8)) > 0
                        _halo = (_gg >= 110) & _fc & _near & (m2 == 0)
                        if int(_halo.sum()):
                            m2 = m2 | _halo.astype(np.uint8)
# هالهٔ گرمِ «تیره» (قرمزِ گلو روی کارتِ
# تیره — لکهٔ قرمزِ POCO F4) در خاکستری تیره است و
# با _gg>=110 نمی‌آمد → قرمزِ غالبِ نزدیکِ جوهر هم
# داخلِ پرکردن می‌آید (اجازهٔ «بیشتر پاک شه»).
                        try:
                            _rr = sub[..., 2].astype(np.int16)
                            _gg2 = sub[..., 1].astype(np.int16)
                            _bb = sub[..., 0].astype(np.int16)
                            _sv = cv2.cvtColor(sub,
                                               cv2.COLOR_BGR2HSV)[..., 1]
                            _warm = ((_rr > _gg2 + 15) & (_rr > _bb + 15)
                                     & (_sv >= 45) & (_gg >= 14)
                                     & _fc & _near & (m2 == 0))
                            if int(_warm.sum()):
                                m2 = (m2 |
                                      _warm.astype(np.uint8))
                        except Exception:
                            pass
# برجستگی/سایهٔ متنِ روشن روی کارتِ تیره
# (اندازه‌گیری رویِ کارتِ Crimson Dragon: قرمزِ
# اشباعِ تیره تا ۶.۷px از گلیف — p99=5.6px) نه در
# _halo می‌آید نه _warm → شبحِ تیره‌قرمزِ حروف در
# خروجی می‌ماند. پرکردن = گشادکردنِ ۱۳px ماسک
# محدود به خودِ محفظهٔ تیره → ۱۰۰٪ برجستگی +
# اجازهٔ «بیشتر پاک شه»؛ قابِ تزئینی بیرونِ محفظه
# دست‌نخورده می‌ماند.
                        try:
                            _growE = cv2.dilate(m2,
                                                np.ones((13, 13), np.uint8))
                            _absE = ((_growE > 0) & _fc)
                            if int(_absE.sum()):
                                m2 = (m2 |
                                      _absE.astype(np.uint8))
                        except Exception:
                            pass
                except Exception:
                    pass
                if not int(cv2.countNonZero(m2)):
                    continue
# تابِ نورِ پس‌زمینه (قفلِ نرم) قربانیِ
# هاله‌گیری نشود — پرتوِ نور پشتِ متن باید بماند
                try:
                    _pge = getattr(self, "_prot_glow", None)
                    if (_pge is not None
                            and _pge.shape == enc.shape):
                        _sube = _pge[y0:y1, x0:x1] > 0
                        if int(_sube.sum()):
                            m2 = m2 & (~_sube).astype(np.uint8)
                except Exception:
                    pass
# TELEA روی متنِ درشتِ روی بنر، خاکستریِ لکه‌دار
# می‌سازد (لبه‌هایِ نویزیِ JPEG را پخش می‌کند). رنگِ هر
# پیکسل = میانهٔ محلیِ پیکسل‌هایِ تیرهٔ خودِ محفظه بیرونِ
# جوهر → روی بنرِ سیاه، سیاهِ خالص؛ روی بنرِ گرادیانی
# محلی تطبیق می‌شود.
                _g = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
                _dark = ((_g < 130).astype(np.uint8)
                         & (m2 == 0).astype(np.uint8))
                _src_f = sub.astype(np.float32)
                _k = 31
                _num = cv2.blur(_src_f * _dark[..., None], (_k, _k))
                _den = cv2.blur(_dark.astype(np.float32), (_k, _k))
                _dk_px = _src_f[_dark > 0]
                _fb = (np.median(_dk_px, axis=0) if _dk_px.size >= 30
                       else np.median(
                           _src_f[m2 == 0].reshape(-1, 3), axis=0)
                       if int((m2 == 0).sum()) > 30
                       else np.array([0.0, 0.0, 0.0]))
                _fill = np.where(
                    _den[..., None] > 0.02,
                    _num / np.maximum(_den, 1e-6)[..., None],
                    _fb[None, None, :]).astype(np.float32)
                _sel = m2 > 0
                sub[_sel] = np.clip(
                    np.rint(_fill[_sel]), 0, 255).astype(np.uint8)
                cleaned[y0:y1, x0:x1] = sub
# حلقهٔ padِ دورِ ماسکِ این ناحیه هم حذف شود تا
# حلقهٔ کلاسترها روی پس‌ماندِ آن لکه نسازد
# (: کِیل بر اساس m2 — شاملِ هالهٔ پرشده هم هست)
                _kill = cv2.dilate(m2, np.ones((9, 9), np.uint8)) > 0
                mask[y0:y1, x0:x1][_kill] = 0
                n_fill += 1
            except Exception:
                continue
        return n_fill

    def _ink_bg_dark(self, image: np.ndarray, ink: np.ndarray) -> bool:
        """ — آیا زمینهٔ دورِ جوهرِ این ناحیه واقعاً تیره است؟
        بلوکِ اجباریِ LaMa (force-box) فقط برای «متنِ روشن روی محفظهٔ تیره»
        معنا دارد. پنجره‌هایِ آبیِ روشن (مثل [SPECIAL CHANGES]) را هم بلوکِ
        کامل می‌گرفت → LaMa کلِ پنل را بازسازی می‌کرد و بعدِ مقایسه با
        اسنپ‌شاتِ قبل از LaMa (که هنوز متن دارد) «لکه» تشخیص می‌داد و
        اسنپ‌شاتِ کثیف جایگزین می‌شد = متنِ انگلیسی برمی‌گشت. حلقهٔ دورِ
        جوهر (دیلیت ۱۳ منهای دیلیت ۳) میانهٔ خاکستری ≤ ۱۴۵ → تیره."""
        try:
            g = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _d1 = cv2.dilate(ink, np.ones((13, 13), np.uint8))
            _d0 = cv2.dilate(ink, np.ones((3, 3), np.uint8))
            _ring = (_d1 > 0) & (_d0 == 0)
            if int(_ring.sum()) < 40:
                return False
            return float(np.median(g[_ring])) <= 145.0
        except Exception:
            return False

    @staticmethod
    def _mem_trim() -> None:
        """ — آزادسازیِ حافظهٔ کش‌شده به OS بینِ فازهایِ سنگین.
        روی نوارِ بلندِ وب‌تون، ماسک‌سازی و LaMa پیکِ رم را بالا می‌برند و
        آللوکاتور حافظه را نگه می‌دارد؛ در گوشیِ کم‌رم (POCO F4 با ۰.۶GB
        آزاد) همین نگه‌داشتن OOM می‌آورد. gc + malloc_trim (glibc)."""
        try:
            import gc as _gc
            _gc.collect()
        except Exception:
            pass
        try:
            import ctypes as _ct
            _libc = _ct.CDLL("libc.so.6")
            _libc.malloc_trim(0)
        except Exception:
            pass

    def _compose_kernel9(self):
        _k = getattr(self, "_compose_k9", None)
        if _k is None:
            _k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
            self._compose_k9 = _k
        return _k

    @staticmethod
    def _system_box_interior(image: np.ndarray, cover_rect,
                             seed_rects=None) -> Optional[np.ndarray]:
        """ — اینتریورِ «بالنِ سیستم» (باکسِ مشخصاتِ سفید).

        خواستهٔ کاربر: «حبابِ سیستم متن‌هاش جدا حساب شه (رندر) ولی
        پاکسازیش: متن‌های نزدیک با هم پاک بشه — فقط سیستم اینجور باشه».
        یعنی در پاکسازی، کلِ داخلِ باکسِ سیستم «یک واحد» پاک می‌شود
        (نه خط‌به‌خط) تا هیچ لکهٔ سیاه/شبحی بینِ خط‌ها و چسبیده به قاب
        نماند و LaMa کلِ باکس را با هم ببیند.

        روش: داخلِ cover_rect، مؤلفه‌هایِ «روشنِ» تصویر که به خط‌هایِ
        متن (seed) می‌رسند = اینتریورِ سفید؛ حفره‌هایِ محبوس (خودِ
        حروفِ تیره) پر می‌شوند؛ ۱px از قابِ تیره فاصله می‌گیرد.
        فقط باکسِ «سفید» (میانهٔ روشن ≥۱۸۰) — پنجرهٔ سیستمِ تیره (آبیِ
        asura) مثلِ قبل خط‌به‌خط پاک می‌شود (رفتارِ فعلی حفظ است).

        خروجی: ماسکِ boolِ تمام‌صفحه؛ None = مسیر سیستمی/سفید نیست."""
        try:
            h, w = image.shape[:2]
            bx0 = max(0, int(cover_rect[0]))
            by0 = max(0, int(cover_rect[1]))
            bx1 = min(w, int(cover_rect[2]))
            by1 = min(h, int(cover_rect[3]))
            if bx1 - bx0 < 24 or by1 - by0 < 16:
                return None
            crop = image[by0:by1, bx0:bx1]
            g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            bright = (g >= 120).astype(np.uint8)
            if float(bright.mean()) < 0.30:
                return None
            seed = np.zeros_like(bright)
            n_seed = 0
            for _sr in (seed_rects or []):
                try:
                    _sx0 = max(0, int(_sr[0]) - bx0)
                    _sy0 = max(0, int(_sr[1]) - by0)
                    _sx1 = min(bx1 - bx0, int(_sr[2]) - bx0)
                    _sy1 = min(by1 - by0, int(_sr[3]) - by0)
                except Exception:
                    continue
                if _sx1 - _sx0 >= 6 and _sy1 - _sy0 >= 6:
                    seed[_sy0:_sy1, _sx0:_sx1] = 1
                    n_seed += 1
            if n_seed <= 0:
                return None
            n, lab = cv2.connectedComponents(bright, 8)
            keep = np.zeros_like(bright)
            _hit = set(int(v) for v in np.unique(lab[seed > 0])) - {0}
            for _i in _hit:
                keep[lab == _i] = 1
            if int(keep.sum()) < 300:
                return None
# فقط باکسِ «سفیدِ سیستم»: میانهٔ روشناییِ اینتریور ≥۱۸۰
            if float(np.median(g[keep > 0])) < 180.0:
                return None
# حفره‌هایِ محبوس (حروفِ تیره داخلِ سفید) پر شوند
            inv = (keep == 0).astype(np.uint8)
            nh, nlab = cv2.connectedComponents(inv, 8)
            hole = np.zeros_like(inv)
            for _j in range(1, nh):
                _cm = (nlab == _j)
                if (_cm[0, :].any() or _cm[-1, :].any()
                        or _cm[:, 0].any() or _cm[:, -1].any()):
                    continue  # به مرزِ کراپ می‌رسد = بیرونِ باکس
                hole[_cm] = 1
            interior = ((keep + hole) > 0).astype(np.uint8)
# ۱px فاصله از قابِ تیره — قابِ سیستم هرگز واردِ ماسک نشود
            interior = cv2.erode(interior, np.ones((3, 3), np.uint8))
            out = np.zeros((h, w), dtype=bool)
            out[by0:by1, bx0:bx1] = interior > 0
            if int(out.sum()) < 400:
                return None
            return out
        except Exception:
            return None

    def _rotated_region_strips(self, image: np.ndarray, polys: list,
                               ang: float):
        """ — نوارهایِ خط‌به‌خط برایِ نواحیِ «چرخیده».

        ریشهٔ سه شکایتِ همزمان (حبابِ زردِ چپ‌بریدهٔ img6 با زاویهٔ
        -۹.۵°، تابلوهایِ MINISTRYِ img4 با -۱۵/-۱۹.۳°، خطِ جاماندهٔ
        10.jpg با -۱۵°): نوارِ محور-ترازِ متنِ کج (۱) از دیوارِ حباب
        رد میشود → حلقهٔ رنگِ پر، داخل+بیرونِ حباب را قاطی میکند →
        «لکهٔ سبز-خاکستری روی زرد»؛ (۲) لبهٔ نوار وسطِ حروف میگذرد و
        گاردِ ساختار () تکههایِ گلیفِ چسبیده به لبه را از
        ماسک بیرون میکشد → «نقطه‌های سیاه»؛ (۳) خطوطِ کج در یک سطلِ
        y می‌افتند → نوارِ چاق. راه‌حل: برشِ ناحیه با +angle همسطح
        میشود (قراردادِ همسطح‌سازیِ OCR و _max_font_for_region —
        : علامتِ درست؛ قبلاً -angle بود و کجی را «دوبرابر»
        میکرد = ریشهٔ «برعکس میچرخونه» و جوهرِ جامانده)، نوارها در فضای
        چرخیده ساخته میشوند (خطوط افقند؛ لبه‌ها هرگز حروف را نمیبرند)
        و ماسک با اینترپولیشنِ NEAREST به مختصاتِ اصلی برمیگردد.
        خروجی: (strips, failed) یا None (فراخواننده به مسیرِ عادی
        برمیگردد)."""
        try:
            h, w = image.shape[:2]
            _all = np.concatenate(polys, axis=0)
            bx0 = float(_all[:, 0].min())
            bx1 = float(_all[:, 0].max())
            by0 = float(_all[:, 1].min())
            by1 = float(_all[:, 1].max())
            cx, cy = (bx0 + bx1) / 2.0, (by0 + by1) / 2.0
            pad = 30.0
# علامتِ + : زاویهٔ مثبت = نزولی-به-راست (قراردادِ y-down)
# همسطح‌سازی نیاز به چرخشِ پادساعتگرد دارد = getRotationMatrix2D(+ang)
# (عینِ قراردادِ اثبات‌شدهٔ deskew در _ocr_crop و _max_font_for_region).
# قبلاً -ang بود → کجی دوبرابر می‌شد (چرخشِ برعکس + جوهرِ جامانده).
            M = cv2.getRotationMatrix2D((cx, cy), float(ang), 1.0)
            _cos, _sin = abs(M[0, 0]), abs(M[0, 1])
            bw = (bx1 - bx0) + 2.0 * pad
            bh = (by1 - by0) + 2.0 * pad
            nw = int(bh * _sin + bw * _cos) + 4
            nh = int(bh * _cos + bw * _sin) + 4
            if nw < 16 or nh < 16 or nw > 4 * w or nh > 4 * h:
                return None
            M[0, 2] += (nw / 2.0) - cx
            M[1, 2] += (nh / 2.0) - cy
            rot_img = cv2.warpAffine(image, M, (nw, nh),
                                     flags=cv2.INTER_LINEAR,
                                     borderValue=(255, 255, 255))
            rot_polys = []
            for p in polys:
                q = np.asarray(p, dtype=np.float32).reshape(-1, 2)
                qh = np.hstack(
                    [q, np.ones((q.shape[0], 1), np.float32)])
                rq = (M @ qh.T).T
                rot_polys.append(rq.astype(np.float32))
            lines = MangaTranslator._group_polys_to_lines(rot_polys)
            if not lines:
                return None
            m_rot = np.zeros((nh, nw), dtype=np.uint8)
            f_rot = np.zeros((nh, nw), dtype=np.uint8)
            for (lx0, ly0, lx1, ly1) in lines:
                st = self._line_strip_ink(rot_img, lx0, ly0, lx1, ly1,
                                          rot_polys)
                if st is None:
# پالیِ خودِ خط (اندازهٔ متن) — همان قراردادِ failed
                    try:
                        for _pa in rot_polys:
                            _px0 = float(_pa[:, 0].min())
                            _px1 = float(_pa[:, 0].max())
                            _py0 = float(_pa[:, 1].min())
                            _py1 = float(_pa[:, 1].max())
                            if (_px1 >= lx0 - 2 and _px0 <= lx1 + 2
                                    and _py1 >= ly0 - 2
                                    and _py0 <= ly1 + 2):
                                cv2.fillPoly(
                                    f_rot,
                                    [np.rint(_pa).astype(np.int32)], 255)
                    except Exception:
                        pass
                    continue
                sx0, sy0, sx1, sy1, kept = st
                m_rot[sy0:sy1, sx0:sx1][kept] = 255
            if not m_rot.any() and not f_rot.any():
                return None
            Minv = cv2.invertAffineTransform(M)
            m = cv2.warpAffine(m_rot, Minv, (w, h),
                               flags=cv2.INTER_NEAREST, borderValue=0)
            f = cv2.warpAffine(f_rot, Minv, (w, h),
                               flags=cv2.INTER_NEAREST, borderValue=0)
# ماسکِ برگشتی فقط تا پالی‌های اصلی + پد معتبر است؛ بیرونِ
# آن وارپ ممکن است نوچ بسازد
            _valid = np.zeros((h, w), dtype=np.uint8)
            for p in polys:
                try:
                    cv2.fillPoly(
                        _valid,
                        [np.rint(np.asarray(p, np.float32).reshape(-1, 2))
                         .astype(np.int32)], 255)
                except Exception:
                    continue
            _valid = cv2.dilate(_valid, np.ones((25, 25), np.uint8)) > 0
            m = (m > 0) & _valid
            f = (f > 0) & _valid
            return (m.astype(np.uint8) * 255, f.astype(np.uint8) * 255)
        except Exception:
            return None

    def _compose_region_strips(self, image: np.ndarray,
                               region: "TextRegion") -> Optional[np.ndarray]:
        """ — نوارهایِ خط‌به‌خطِ «اندازهٔ دقیقِ متن» برایِ یک ناحیه.

        خواستِ کاربر: «عکس اول کامل میپاکه بعد همون اندازه متن برش میزنه
        به عکس دوم میزاره نه بیشتر نه کمتر حباب خراب نشه». پس ماسکِ
        کامپوز باید دقیقاً «جوهرِ حروف» باشد — نه مستطیلِ بلوک (که حباب
        را با خود می‌برد) و نه کلِ ناحیه."""
        try:
            polys = []
            for p in (getattr(region, "ocr_polys", None) or []):
                try:
                    pp = np.asarray(p, dtype=np.float32).reshape(-1, 2)
                except Exception:
                    continue
                if pp.shape[0] >= 3:
                    polys.append(pp)
            if not polys:
                return None, np.zeros((1, 1), dtype=np.uint8)
# نواحیِ چرخیده (|angle| ≥ ۳°): نوارها در فضای
# همسطح‌شده ساخته میشوند — نوارِ محور-ترازِ متنِ کج از دیوارِ
# حباب رد میشود (لکهٔ رنگِ قاطی) و لبه‌اش حروف را میبرد
# (نقطه‌های سیاه). MANGA_ROT_STRIPS=0 = خاموش.
            try:
                _ang = float(getattr(region, "angle", 0.0) or 0.0)
            except Exception:
                _ang = 0.0
            if 3.0 <= abs(_ang) <= 45.0 \
                    and os.environ.get("MANGA_ROT_STRIPS", "1") != "0":
                _rot = self._rotated_region_strips(image, polys, _ang)
                if _rot is not None:
                    return _rot
            lines = MangaTranslator._group_polys_to_lines(polys)
            if not lines:
                return None, np.zeros((1, 1), dtype=np.uint8)
            h, w = image.shape[:2]
            m = np.zeros((h, w), dtype=np.uint8)
            failed = np.zeros((h, w), dtype=np.uint8)
            n = 0
            _dbgc = bool(os.environ.get("MANGA_LSM_DBG"))
            for (lx0, ly0, lx1, ly1) in lines:
                st = self._line_strip_ink(image, lx0, ly0, lx1, ly1, polys,
                                          dbg=_dbgc)
                if st is None:
# خطی که نوارش ساخته نشد (مثلِ متنِ سفید با
# دورخطِ تیره روی زمینهٔ روشن) نباید از کامپوز بیفتد وگرنه
# متن از عکسِ دوم برمی‌گردد («WE FRIENDS?»). برایِ این
# خط، پالیِ خودش جایگزین می‌شود (اندازهٔ متن).
# بازگشت به قراردادِ testm: «کلِ پالی» از
# donor منتقل میشود. جایگزینِ فقط «جوهرِ
# دو-قطبیِ ±۴۵» را منتقل میکرد و بلوکِ مورفولوژیِ
# میله‌ها بهخاطرِ NameErrorِ _fu8 (متغیر هرگز تعریف
# نشده بود → except بیصدا) هرگز اجرا نمیشد → متنِ
# کمرنگ/آنتی‌الیاس‌شدهٔ اسنادِ وبتون (9.jpg: ARTICLEها
# و y=9536) و حروفِ کم‌کنتراستِ img6 («THE FLOAT FOR
# YOU!») در عکسِ دوم زنده میماند = «متنِ قبلی میماند
# شبحِ خاکستری، لکه» — گزارشِ سازنده. حصارِ img4
# (نگرانیِ 206) اکنون دو لایهٔ دیگر دارد: (۱) 206c
# نوارِ سالمِ متن را میسازد و خط به این شاخه نمیافتد
# (۲) پانچِ میلهٔ نازکِ بلند پایین — میلهٔ حصار/قاب از
# پالیِ خط حذف میشود ولی حروف (تیره + ضخیم
# GUARDIANS/TEACHERS) میمانند.
                    try:
                        for _pa in polys:
                            _bx0 = float(_pa[:, 0].min())
                            _bx1 = float(_pa[:, 0].max())
                            _by0 = float(_pa[:, 1].min())
                            _by1 = float(_pa[:, 1].max())
                            if (_bx1 >= lx0 - 2 and _bx0 <= lx1 + 2
                                    and _by1 >= ly0 - 2 and _by0 <= ly1 + 2):
# بدونِ پانچِ میله: پانچِ
# نسخهٔ اول حروفِ چسبیده/خطهایِ متن را هم
# «میله» میگرفت → جوهرِ اورجینال در عکسِ
# دوم زنده میماند (سه لکهٔ سیاهِ 9.jpg).
# حصارِ img4 توسطِ 206c (نوارِ سالم) محفوظ
# است؛ این شاخه فقط برایِ خطی است که نوارش
# اصلاً ساخته نشد — قراردادِ testm: کلِ پالی.
                                cv2.fillPoly(failed,
                                             [np.rint(_pa)
                                              .astype(np.int32)], 255)
                    except Exception:
                        pass
                    continue
                sx0, sy0, sx1, sy1, kept = st
                m[sy0:sy1, sx0:sx1][kept] = 255
# شبحِ لبهٔ حروف: ماسکِ پاکسازی هستهٔ تیره + هالهٔ
# ۱۴..۳۰ را میگیرد ولی پیکسلهایِ خیلی روشنِ لبهٔ حرف
# (≤۱۴ سطح از زمینه) را نه؛ کامپوزِ فقط-هسته آنها را از عکسِ
# اورجینال برمی‌گرداند = شبحِ خوانایِ «ALSO» در حبابِ
                #). پیکسلهایِ روشنِ چسبیده
# «YOU SHOULD ALSO…» (img7 —
# به هسته (≤۳px) از عکسِ پاک‌شده بیایند — پیکسلی که پاک
# نشده در هر دو عکس یکسان است پس خطری ندارد و زمینهٔ هنریِ
# پرقاومت (|Δ|>۱۴ — حصارِ پشتِ ARTICLEها) همچنان از
# اورجینال میماند.
                try:
                    _g = cv2.cvtColor(image[sy0:sy1, sx0:sx1],
                                         cv2.COLOR_BGR2GRAY)
                    _med = float(np.median(_g))
                    _lite = (np.abs(_g.astype(np.float32) - _med)
                                <= 14.0)
                    _kd = cv2.dilate(kept.astype(np.uint8),
                                        np.ones((7, 7), np.uint8)) > 0
                    _add2 = _kd & _lite & (~kept)
                    if _add2.any():
                        m[sy0:sy1, sx0:sx1][_add2] = 255
                except Exception:
                    pass
                n += 1
            if n == 0:
# هیچ خطی نوار نشد → کلِ ناحیه به مسیرِ خام سپرده شود
                return None, failed
# «نه بیشتر نه کمتر»: نوارها فقط داخلِ پالیِ OCR
# (همان باکسِ متن) می‌مانند. بدونِ این محدودیت، دیوارِ حباب
# که در نوارِ بالا/پایینِ خط می‌افتد جزوِ «جوهر» می‌شد و از
# عکسِ پاک‌شده (که حبابش خراب شده) برمی‌گشت → حباب می‌شکست.
            _pm = np.zeros((h, w), dtype=np.uint8)
            for _pa in polys:
                try:
                    cv2.fillPoly(
                        _pm, [np.rint(_pa).astype(np.int32)], 255)
                except Exception:
                    continue
            if not _pm.any():
                return None, failed
            _pm = cv2.dilate(_pm, np.ones((7, 7), np.uint8)) > 0
            m = (m & _pm).astype(np.uint8) * 255
            failed = (failed & _pm).astype(np.uint8) * 255
            if not m.any() and not failed.any():
                return None, np.zeros((h, w), dtype=np.uint8)
# پسگیرِ جوهرِ جامانده در کامپوز:
# قطعههایِ گلیفِ بیرونِ پالی ('Yo'/'th'/'a' — 01.jpg) باید در
# نوارِ انتقال هم بیایند وگرنه «فقط-نوار» آنها را از عکسِ
# اصلی زنده نگه میدارد. همگام با ماسکِ پاکسازی.
# رویِ PC هم فعال شد (هر دو پلتفرم باید خوب پاک
# کند؛ env=0 خاموش میکند).
            if os.environ.get("MANGA_INK_RECLAIM", "1") != "0":
                try:
                    _base = cv2.bitwise_or(m, failed)
                    _add = self._stray_ink_reclaim(image, _base,
                                                      [region])
                    if _add is not None and np.any(_add):
                        _add = cv2.bitwise_and(
                            _add, cv2.bitwise_not(_base))
                        m = cv2.bitwise_or(m, _add)
                except Exception:
                    pass
# ساختارِ محافظتشده (دیوار/قابِ رنگی) هرگز از
# نوارِ کامپوز منتقل نمیشود — حتی تکههایِ داخلِ پالی+۷ —
# تا پرِ LaMa که رنگِ قاب را به داخلِ متن کشیده (لکهٔ سبزِ
# حبابِ ۳ در up0822) جایِ قابِ اصلی را نگیرد؛ قاب همیشه
# پیکسلِ عکسِ دوم است.
# «قابِ رنگی» هرگز از نوارِ کامپوز منتقل نمیشود
# حتی تکههایِ داخلِ پالی+۷. قاب در ماسکِ فعال میماند (LaMa
# آن را با زمینهٔ حباب پر میکند — نه اینکه رنگش را به متن
# بکشد: لکهٔ سبزِ up0822) و در خروجی، پیکسلِ قاب همیشه از
# عکسِ دوم میآید.
            try:
                _ppm = getattr(self, "_page_colored_protect", None)
                if _ppm is not None and _ppm.shape == m.shape:
                    m = cv2.bitwise_and(m, cv2.bitwise_not(_ppm))
                    failed = cv2.bitwise_and(failed,
                                             cv2.bitwise_not(_ppm))
            except Exception:
                pass
            return m, failed
        except Exception:
            return None, np.zeros((1, 1), dtype=np.uint8)

    def _compose_strip_mask(self, image: np.ndarray,
                            mask: np.ndarray) -> np.ndarray:
        """ — ماسکِ کامپوزِ «فقط نوارِ متن، خط به خط»:
        پایه = ماسکِ متنِ خام (self._compose_text_mask — بعدِ کارو/پروتکت،
        قبلِ کِیل/توپرشدن). برایِ بلوک‌هایِ محفظهٔ تیره که ماسکِ فعال‌شان
        «کلِ محفظه» است، به‌جایِ کلِ بلوک فقط «نوارِ هر خطِ متن» — از رویِ
        جوهرِ همان خط در عکسِ اصلی اندازه‌گاری شده — واردِ ماسکِ کامپوز
        می‌شود؛ دقیقاً طبقِ اصلاحِ کاربر:
        «به اندازهٔ متنِ اصلی برش بخوره بذاره رو عکسِ اصلی — چرا کلِ حباب
        رو منتقل می‌کنی به عکسِ دوم؟ گفتم خط به خط برش بخوره.»
        نتیجه: دیوار/زمینه/هنرِ دورِ متن همیشه پیکسل‌به‌پیکسل از عکسِ
        اصلیِ دوم می‌ماند و فقط محلِ متن با نسخهٔ پاک‌شده جایگزین می‌شود."""
        try:
# «صفرِ شوِرَه»: ماسکِ پایه (که enclosure/پرِ فوری
# کلِ حباب را دارد) نقطهٔ شروعِ کامپوز نمی‌شود. اگر نقطهٔ
# شروعِ «پایهٔ کامل» باشد، هر نواحی از حباب بیرونِ نوارهایِ
# خط (دیوار، زمینهٔ گرادیانی) در ماسک می‌ماند و کلِ حباب از
# عکسِ پاک‌شده (donor) به عکسِ دوم منتقل می‌شود — اعتراضِ کاربر:
# «مگ داری کل حباب انتقال میدی؟؟» (نمونه: حبابِ زردِ img1).
# حالا شروع = خالی؛ سپس هر ناحیه دقیقاً نوارهایِ خط‌به‌خط
# خودش را می‌گیرد. ناحیه‌هایِ بدونِ نوار (بنر/متنِ آزاد) به
# ماسکِ خامِ محدودِ ناحیهٔ خودشان برمی‌گردند.
            base = getattr(self, "_compose_text_mask", None)
            _raw = (mask > 0) if (base is None
                                  or base.shape != mask.shape[:2]) \
                else (base > 0)
            out = np.zeros_like(_raw)
# هر فراخوانیِ کامپوز، گروه‌هایِ سیستم را از نو
# پردازش کند (کامپوز دوبار صدا می‌شود: اصلی + گارانتیِ نهایی)
            self._compose_sys_done = set()
            h, w = mask.shape[:2]
# «نه بیشتر نه کمتر»: برایِ هر ناحیه‌ای که پالیِ
# OCR دارد، نوارهایِ خط‌به‌خط (اندازهٔ دقیقِ حروف) جایِ
# مستطیلِ بلوکِ ماسکِ خام می‌نشینند. نتیجه: دیوارِ حباب
# قوس، قابِ پنل و هنرِ اطراف هرگز از عکسِ پاک‌شده نمی‌آیند
# → حباب سالم می‌ماند؛ فقط خودِ حروف پاک می‌شوند.
            _regions = getattr(self, "_page_regions", None) or []
            _n_str = 0
# دامنهٔ امنِ «جارویِ بقایا»: فقط نوارهایِ متن.
# قبلاً دامنه = ماسکِ خام (مستطیلِ بلوک) بود → دیوارِ حباب که
# داخلِ بلوک می‌افتد «بقایایِ متن» خوانده می‌شد و پاک می‌شد
# → حباب می‌شکست. دامنهٔ جدید = دقیقاً حروف.
            _sweep = np.zeros((h, w), dtype=np.uint8)
            for _rg in _regions:
                try:
                    _res = self._compose_region_strips(image, _rg)
                except Exception:
                    _res = None
                if not _res:
                    continue
                _strips, _failed = _res[0], _res[1]
                if _strips is None:
                    _strips = np.zeros((h, w), dtype=np.uint8)
                if _failed is None:
                    _failed = np.zeros((h, w), dtype=np.uint8)
                if not _strips.any() and not _failed.any():
                    continue
# ناحیهٔ متنیِ این منطقه از ماسکِ خام حذف می‌شود (تا
# مستطیلِ بلوک به خروجی نیاید) و نوارهای خط جایگزین می‌شوند
                _area = np.zeros((h, w), dtype=np.uint8)
                _ok = False
                for _p in (getattr(_rg, "ocr_polys", None) or []):
                    try:
                        _pa = np.asarray(_p, dtype=np.float32).reshape(-1, 2)
                    except Exception:
                        continue
                    if _pa.shape[0] < 3:
                        continue
                    cv2.fillPoly(_area, [np.rint(_pa).astype(np.int32)], 255)
                    _ok = True
                if not _ok:
                    continue
                _area = cv2.dilate(_area, np.ones((13, 13), np.uint8)) > 0
                out[_area] = False
                out |= (_strips > 0)
                out |= (_failed > 0)
                _sweep |= (_strips > 0)
                _sweep |= (_failed > 0)
# «بلوکِ باندِ تیره»: اگر متن روی باندِ
# نیمه‌شفافِ تیره باشد (PARAGRAPHهایِ img4 روی حصار)
# donor کلِ باند را بازسازی کرده (پرکننده‌هایِ فوری/
# LaMa) ولی کامپوزِ فقط-نوار، باندِ تیرهٔ اورجینال را
# بینِ نوارها زنده نگه می‌دارد → «بلوک‌هایِ قاطیِ
# تکه‌تکه». راه‌حل: اگر زمینهٔ بلوک (بیرونِ نوارها)
# تیره باشد، کلِ مستطیلِ بلوک از donor می‌آید —
# حباب‌هایِ سفید (زمینهٔ روشن) هرگز وارد این مسیر
# نمی‌شوند (اعتراضِ «کلِ حباب را منتقل نکن» محفوظ است).
                try:
                    _brx, _bry, _brw, _brh = [int(v) for v in _rg.rect]
                    _bx0 = max(0, _brx)
                    _by0 = max(0, _bry)
                    _bx1 = min(w, _brx + _brw)
                    _by1 = min(h, _bry + _brh)
                    if _bx1 - _bx0 >= 24 and _by1 - _by0 >= 14:
                        _bl = (_strips[_by0:_by1, _bx0:_bx1] > 0) | \
                              (_failed[_by0:_by1, _bx0:_bx1] > 0)
                        _bld = cv2.dilate(
                            _bl.astype(np.uint8),
                            np.ones((7, 7), np.uint8)) > 0
                        _bgo = cv2.cvtColor(
                            image[_by0:_by1, _bx0:_bx1],
                            cv2.COLOR_BGR2GRAY)
                        _outb = (~_bld)
                        if int(np.count_nonzero(_outb)) >= 200:
                            _medb = float(np.median(_bgo[_outb]))
# گاردِ بافت: «کلِ بلوک از donor»
# فقط برای باندِ تیرهٔ «یکدست» (std کم —
# PARAGRAPHهایِ img4 روی حصار). روی زمینهٔ
# بافت‌مند (برف‌نوی/نقش‌ونگارِ 412e9e با
# std≈۶۷/۵۸) کلِ بلوک = پرِ تختِ LaMa →
# فقط نوارهایِ خط از donor می‌آیند.
                            _stdb = float(np.std(_bgo[_outb]))
                            if _medb < 140.0 and _stdb <= 36.0:
# قانونِ دو-عکسی: حتی
# رویِ باندِ تیرهٔ یکدست فقط نوارهایِ خط از
# donor میآیند (بالا: out |= strips/failed)
# بینِ خطها = پیکسلِ اورجینالِ باند (جوهرش
# داخلِ نوارها پاک شده). خرابیِ احتمالیِ
# عکسِ اول (لگه/لکهٔ LaMa) دیگر هرگز با
# کلِ بلوک به عکسِ دوم نمیرسد.
                                if self.debug:
                                    try:
                                        print(f"  [*]بلوکِ "
                                              f"باندِ تیره (med={_medb:.0f}"
                                              f" std={_stdb:.0f})"
                                              f" → فقطِ نوارِ خط از donor "
                                              f"(کلِ بلوکِ {_bx1-_bx0}x{_by1-_by0}"
                                              f" ممنوع — قانونِ دو-عکسی)")
                                    except Exception:
                                        pass
# «پنلِ متنیِ روشن» (همتایِ ماسکِ
# توپرِ بلوک — فقط اندروید، MANGA_TEXTPANEL):
# اگر بینِ نوارها هنوز جوهرِ حروفِ جامانده
# (OCRِ هرزِ آن روز) دیده شود، کلِ بلوک از
# عکسِ پاکشده میآید — وگرنه متنِ نیمهپاک +
# لکه در خروجی میماند. اگر donor آنجا پاک
# نشده باشد، پیکسلِ donor = اورجینال (بیضرر).
# هماهنگ با گیتِ ماسک: فقطِ اندروید
                            elif _android_gate("MANGA_TEXTPANEL"):
                                try:
                                    _ex = cv2.dilate(
                                        ((_strips > 0) | (_failed > 0))
                                        .astype(np.uint8),
                                        np.ones((9, 9), np.uint8))
# med_hِ ناحیه (فونتِ
# درشتِ img6: بلندیِ خط ۶۹..۷۹)
                                    _mh = 0.0
                                    try:
                                        _pl = []
                                        for _p2 in (getattr(
                                                _rg, "ocr_polys", None)
                                                or []):
                                            try:
                                                _pp = np.asarray(
                                                    _p2,
                                                    dtype=np.float32
                                                ).reshape(-1, 2)
                                                if _pp.shape[0] >= 3:
                                                    _pl.append(_pp)
                                            except Exception:
                                                continue
                                        _ln = MangaTranslator \
                                            ._group_polys_to_lines(_pl)
                                        if _ln:
                                            _mh = float(np.median(
                                                [b[3] - b[1]
                                                 for b in _ln]))
                                    except Exception:
                                        _mh = 0.0
                                    _ink = \
                                        MangaTranslator._panel_leftover_ink(
                                            image,
                                            (_bx0, _by0,
                                             _bx1 - _bx0, _by1 - _by0),
                                            _ex, med_h=_mh)
                                    if _ink is not None:
# فقط گلیفهای جامانده از donor —
# نه کلِ بلوک (LaMaِ بلوکِ کامل
# رویِ زمینهٔ عکسی توهم/نویز)
                                        _im = _ink > 0
                                        out[_im] = True
                                        _sweep[_im] = True
                                        if self.debug:
                                            try:
                                                print(
                                                    f"  [*]پنلِ متنی → "
                                                    f"گلیفهای جامانده از "
                                                    f"donor ("
                                                    f"{int(cv2.countNonZero(_ink))}"
                                                    f"px @({_bx0},{_by0})")
                                            except Exception:
                                                pass
                                except Exception:
                                    pass
                except Exception:
                    pass
# «بالنِ سیستم»: اینتریورِ باکسِ سیستم (که در
# پاکسازی «یکجا» پاک شد) در کامپوز هم «یکجا» از عکسِ
# پاک‌شده منتقل می‌شود — وگرنه شبح/لکهٔ بینِ خط‌ها از
# عکسِ اصلی برمی‌گردد. قابِ سیستم بیرونِ اینتریور است و
# طبقِ قاعدهٔ همیشگی از عکسِ اصلی می‌ماند.
                try:
                    if getattr(_rg, "sys_split", False):
                        _cov = getattr(_rg, "cover_rect", None)
                        if _cov is not None:
                            _sys_done = getattr(
                                self, "_compose_sys_done", None)
                            if _sys_done is None:
                                _sys_done = set()
                                self._compose_sys_done = _sys_done
                            _key = tuple(
                                int(v) for v in _cov[:4])
                            if _key not in _sys_done:
                                _sys_done.add(_key)
                                _seeds = []
                                for _rgs2 in _regions:
                                    if not getattr(_rgs2, "sys_split",
                                                   False):
                                        continue
                                    _cv2b = getattr(_rgs2, "cover_rect",
                                                    None)
                                    if _cv2b is None or tuple(
                                            int(v) for v in _cv2b[:4]) \
                                            != _key:
                                        continue
                                    try:
                                        _qx, _qy, _qw, _qh = [
                                            int(v) for v in _rgs2.rect]
                                    except Exception:
                                        continue
                                    _seeds.append((_qx, _qy,
                                                      _qx + _qw,
                                                      _qy + _qh))
                                if len(_seeds) >= 2:
                                    _intr = \
                                        MangaTranslator._system_box_interior(
                                            image, _key, _seeds)
                                    if _intr is not None:
# قانونِ دو-عکسی:
# اینتریورِ کاملِ باکسِ سیستم هم دیگر
# یکجا منتقل نمیشود — فقط نوارهایِ
# خط (sys_split). بینِ خطها = اورجینال
# خرابیِ عکسِ اول به عکسِ دوم نمیرسد.
                                        if self.debug:
                                            try:
                                                print(f"  [*]بالنِ سیستم → "
                                                      f"فقطِ نوارِ خط "
                                                      f"(اینتریورِ "
                                                      f"{int(_intr.sum())}px "
                                                      f"یکجا ممنوع)")
                                            except Exception:
                                                pass
                except Exception:
                    pass
                _n_str += 1
# ناحیه‌هایی که نوار ندارند (متنِ آزاد/بنر) → ماسکِ خامِ آن‌ها
            for _rg in _regions:
                if getattr(_rg, "kind", "") == "promo":
                    continue
                if (getattr(_rg, "ocr_polys", None) or []):
                    continue
                try:
                    _rx, _ry, _rw2, _rh2 = [int(v) for v in _rg.rect]
                except Exception:
                    continue
                _x0 = max(0, _rx - 6)
                _y0 = max(0, _ry - 6)
                _x1 = min(w, _rx + _rw2 + 7)
                _y1 = min(h, _ry + _rh2 + 7)
                if _x1 > _x0 and _y1 > _y0:
# ناحیهٔ بی‌نوار (متنِ آزاد/بنر): ماسکِ خام
# فقط داخلِ ناحیهٔ خودش برمی‌گردد (نه کلِ صفحه).
                    out[_y0:_y1, _x0:_x1] |= _raw[_y0:_y1, _x0:_x1]
                    _sweep[_y0:_y1, _x0:_x1] |= (out[_y0:_y1, _x0:_x1])
            self._compose_sweep_mask = _sweep
            if _n_str and self.debug:
                try:
                    print(f"  [*]کامپوز = {_n_str} ناحیه با "
                          f"نوارِ خط‌به‌خط (اندازهٔ دقیقِ متن)")
                except Exception:
                    pass
            try:
                _dc = os.environ.get("MANGA_DUMP_COMPOSE", "")
                if _dc:
                    cv2.imwrite(_dc, (out.astype(np.uint8)) * 255)
                    print(f"  [*] compose mask dumped → {_dc}")
            except Exception:
                pass
# بنرهایِ تبلیغ: کلِ بنر (نه نوارِ خط‌ها) از عکسِ
# پاک‌شده به خروجی می‌رود — «کامل فیلتر تبلیغ»
            for _pb in (getattr(self, "_promo_rect_boxes", None) or []):
                try:
                    _qx0 = max(0, int(_pb[0]))
                    _qy0 = max(0, int(_pb[1]))
                    _qx1 = min(w, int(_pb[2]))
                    _qy1 = min(h, int(_pb[3]))
                    if _qx1 - _qx0 >= 8 and _qy1 - _qy0 >= 8:
                        out[_qy0:_qy1, _qx0:_qx1] = True
                except Exception:
                    pass
            for _fb in (getattr(self, "_lama_force_rect_boxes",
                                None) or []):
                try:
                    bx0 = max(0, int(_fb[0]) - 4)
                    by0 = max(0, int(_fb[1]) - 4)
                    bx1 = min(w, int(_fb[2]) + 5)
                    by1 = min(h, int(_fb[3]) + 5)
                    if bx1 - bx0 < 8 or by1 - by0 < 8:
                        continue
# کلِ بلوک از کامپوز حذف؛ فقط نوارِ خط‌ها برمی‌گردد
                    out[by0:by1, bx0:bx1] = False
                    g = cv2.cvtColor(image[by0:by1, bx0:bx1],
                                     cv2.COLOR_BGR2GRAY)
                    med = float(np.median(g))
                    ink = (g > med + 30.0)
                    if not bool(ink.any()):
                        ink = (np.abs(g.astype(np.float32) - med) > 30.0)
                    if not bool(ink.any()):
                        continue
                    ink_u = cv2.dilate(
                        ink.astype(np.uint8),
                        np.ones((7, 7), np.uint8)) > 0
                    _ridx = np.nonzero(ink_u.any(axis=1))[0]
                    if _ridx.size == 0:
                        continue
                    if _ridx.size > 1:
                        _gap = float(np.median(np.diff(_ridx)))
                    else:
                        _gap = 24.0
                    _gap = max(6.0, 0.9 * max(8.0, _gap))
                    _bands = []
                    _s = int(_ridx[0])
                    _p = int(_ridx[0])
                    for _i in range(1, _ridx.size):
                        _r = int(_ridx[_i])
                        if _r - _p > _gap:
                            _bands.append((_s, _p))
                            _s = _r
                        _p = _r
                    _bands.append((_s, _p))
                    bh0, bw0 = by1 - by0, bx1 - bx0
                    for (r0, r1) in _bands:
                        _cols = np.nonzero(
                            ink_u[r0:r1 + 1].any(axis=0))[0]
                        if _cols.size == 0:
                            continue
                        c0, c1 = int(_cols[0]), int(_cols[-1])
                        bh = r1 - r0 + 1
                        pady = max(6, int(0.40 * bh))
                        padx = max(6, int(0.30 * bh))
                        sy0 = max(0, r0 - pady)
                        sy1 = min(bh0, r1 + pady + 1)
                        sx0 = max(0, c0 - padx)
                        sx1 = min(bw0, c1 + padx + 1)
                        if sx1 - sx0 < 8 or sy1 - sy0 < 8:
                            continue
                        out[by0 + sy0:by0 + sy1,
                            bx0 + sx0:bx0 + sx1] = True
                except Exception:
# در خطا: همان بلوکِ کامل مثلِ قبل — امن‌تر از برگشتِ متن
                    try:
                        out[max(0, int(_fb[1])):min(h, int(_fb[3]) + 1),
                            max(0, int(_fb[0])):min(w, int(_fb[2]) + 1)] = True
                    except Exception:
                        pass
# نجاتِ نوارِ جوهرِ پوشش‌داده‌نشده در کامپوز:
# خطی که OCR پالی‌اش را نداشته باشد نه در نوارهاست → متنِ
# اصل از عکسِ دوم برمی‌گشت. نوارِ نجات (همانِ ماسکِ donor)
# جای آن را می‌گیرد.
            try:
                for _db4 in (getattr(self, "_donor_boxes", None) or []):
                    try:
                        _bands4 = self._uncovered_ink_bands(
                            image, _db4, (out.astype(np.uint8)) * 255)
                        if _bands4 is not None:
                            out[_bands4 > 0] = True
                            _sweep[_bands4 > 0] = 255
                    except Exception:
                        continue
            except Exception:
                pass
# روکشِ حاشیه‌نویسی (قاب/شستشویِ سبزِ up0822) هم
# در ماسکِ کامپوز میآید تا با نوارهایِ پاک‌شده به عکسِ دوم
# منتقل شود — وگرنه قابِ سبز در خروجیِ نهایی زنده میماند
# («هرنگی لگه بشه قبول نمیکنم»).
            try:
                _anW = getattr(self, "_page_annotation_overlay", None)
                if _anW is not None and _anW.shape == out.shape \
                        and bool((_anW > 0).any()):
                    out |= (_anW > 0)
                    _sweep[(_anW > 0)] = 255
            except Exception:
                pass
            return (out.astype(np.uint8)) * 255
        except Exception:
            return mask

    def _strip_ghost_polish(self, image: np.ndarray, cleaned: np.ndarray,
                            mask: np.ndarray) -> Tuple[np.ndarray, int]:
        """ — پولیشِ شبحِ نوارهایِ کامپوز.

        . ریشه (img6 — حبابِ دوگانهٔ بالا-وسط): لبهٔ ماسکِ LaMa
        از وسطِ جوهر میگذرد → donor خطِ ۱-۸px نصفهپاک نگه میدارد
        (تیرگیِ میانه ~۳۵-۵۳) → کامپوزِ دو-عکسی همان نوار را از donor
        میآورد → خطوطِ محوِ «متن قبلی». سویپِ بقایا فقط تیرگیِ ۴۵+ و
        «دقیقاً تغییرنکرده» را میبیند؛ همساز/پولیشِ نوار هم رویِ حلقهٔ
        چندخطی گیت میخورد.

        اینجا: فقط داخلِ نوارهایِ کامپوز، اجزایِ «نازک» (جانِ خط — با
        openِ خطی ۷ زنده و با فرسایشِ ۵×۵ میمیرد؛ blobهایِ هنر مثل
        سرِ چیبی زنده میمانند و رد میشوند)، نزدیکِ جوهرِ متنِ اصلی،
        با حلقهٔ زمینهٔ تخت (std≤۳۰) → پرِ پیازی از پیکسلهایِ تمیزِ
        اطراف (هر منبعِ جوهرمانند — کنتراستِ >۱۲ — از چشمه حذف میشود).
        بیرونِ نوارها هیچ پیکسل عوض نمیشود (قراردادِ دو-عکسی)."""
        try:
            if mask is None or cleaned is None or image is None:
                return cleaned, 0
            h, w = cleaned.shape[:2]
            if mask.shape != (h, w):
                return cleaned, 0
            m = (mask > 0)
            if not m.any():
                return cleaned, 0
            g = cv2.cvtColor(cleaned, cv2.COLOR_BGR2GRAY)
            go = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            bg = cv2.medianBlur(g, 41).astype(np.int16)
# فقطِ شبحِ «محو» (کنتراستِ ۲۲..۶۰): خطِ تیرهٔ
# واقعی (هنر/دست/مو — کنتراستِ ۸۰+) هرگز پر نمیشود (img4:
# ضربههایِ دست رویِ میز داخلِ نوار، پاک نشود).
            _d = (bg - g.astype(np.int16))
            _b = (g.astype(np.int16) - bg)
            dark = (_d > 22) & (_d < 60)
            bright = (_b > 22) & (_b < 60)
            cand = (dark | bright) & m
            if not cand.any():
                return cleaned, 0
            bgo = cv2.medianBlur(go, 41).astype(np.int16)
            oink = ((bgo - go.astype(np.int16)) > 20) | \
                ((go.astype(np.int16) - bgo) > 20)
            oink_near = cv2.dilate(
                oink.astype(np.uint8), np.ones((25, 25), np.uint8)) > 0
# نازک: با openِ خطی زنده، با فرسایشِ ۵×۵ مرده (blobِ ضخیم
# = هنر/گلیفِ محافظتشده → رد)
            k_lh = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 1))
            k_lv = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 7))
            u = cand.astype(np.uint8)
            thin = cv2.morphologyEx(u, cv2.MORPH_OPEN, k_lh) | \
                cv2.morphologyEx(u, cv2.MORPH_OPEN, k_lv)
            thick_core = cv2.erode(u, np.ones((5, 5), np.uint8)) > 0
            thin = ((thin > 0) & ~thick_core).astype(np.uint8)
            if not np.any(thin):
                return cleaned, 0
# «باندِ لبهٔ نوار»: شبحِ LaMa پدِّ تراسِ لبهٔ
# ماسک است و همیشه به لبهٔ نوارِ کامپوز چسبیده؛ ضربهٔ هنر
# (دست/مو داخلِ نوار — img4) وسطِ نوار است و رد میشود.
            _core = cv2.erode(m.astype(np.uint8),
                                 np.ones((13, 13), np.uint8)) > 0
            _edge = m & ~_core
# نقشههایِ حفاظت: دیوار/قاب/روکش هرگز پر نمیشوند
            _prot = None
            try:
                for _pmN in (getattr(self, "_page_protect", None),
                             getattr(self, "_page_wall_band", None),
                             getattr(self, "_page_colored_protect", None)):
                    if _pmN is not None and _pmN.shape == (h, w):
                        _prot = (_pmN > 0) if _prot is None \
                            else (_prot | (_pmN > 0))
            except Exception:
                _prot = None
            n, lab, st, _ = cv2.connectedComponentsWithStats(thin, 8)
            fills = np.zeros((h, w), bool)
            for i in range(1, n):
                a = int(st[i, cv2.CC_STAT_AREA])
                cw = int(st[i, cv2.CC_STAT_WIDTH])
                ch = int(st[i, cv2.CC_STAT_HEIGHT])
                if a < 6 or a > 1600 or max(cw, ch) > 220:
                    continue
                comp = (lab == i)
                if _prot is not None and bool((comp & _prot).any()):
                    continue  # دیوار/قاب → رد
                if not (comp & oink_near).any():
                    continue  # دور از متنِ اصلی → هنر است نه شبح
                _eb = cv2.dilate(comp.astype(np.uint8),
                                    np.ones((9, 9), np.uint8)) > 0
                if not bool((_eb & _edge).any()):
                    continue  # وسطِ نوار = محتوای واقعی، نه تراسِ لبه
                ring = cv2.dilate(comp.astype(np.uint8),
                                  np.ones((15, 15), np.uint8)) > 0
                ring &= ~cand
                ring &= ~thick_core
                if int(ring.sum()) < 40:
                    continue
                rv = g[ring].astype(np.float32)
                if float(np.std(rv)) > 30.0:
                    continue  # زمینهٔ بافت‌مند → بافتِ LaMa میماند
                fills |= comp
            if not fills.any():
                return cleaned, 0
# اهدافِ پر + هاله؛ چشمهها = پیکسلهایِ تمیز (جوهرِ محو هم
# چشمه نیست وگرنه سیاهی میکشد)
            tgt = cv2.dilate(fills.astype(np.uint8),
                             np.ones((5, 5), np.uint8)) > 0
            tgt &= (m | fills)
            tgt |= (cand & cv2.dilate(fills.astype(np.uint8),
                                      np.ones((9, 9), np.uint8)) > 0)
            if _prot is not None:
                tgt &= ~_prot
            faint = (np.abs(bg - g.astype(np.int16)) > 12)
            near_m = cv2.dilate(m.astype(np.uint8),
                                np.ones((5, 5), np.uint8)) > 0
            src_ok = ~(faint & near_m)
            out = cleaned.copy()
            n2, lab2, st2, _ = cv2.connectedComponentsWithStats(
                tgt.astype(np.uint8), 8)
            for i in range(1, n2):
                x = int(st2[i, cv2.CC_STAT_LEFT])
                y = int(st2[i, cv2.CC_STAT_TOP])
                cw = int(st2[i, cv2.CC_STAT_WIDTH])
                ch = int(st2[i, cv2.CC_STAT_HEIGHT])
                pad = 26
                x0, y0 = max(0, x - pad), max(0, y - pad)
                x1 = min(w, x + cw + pad)
                y1 = min(h, y + ch + pad)
                sub_t = tgt[y0:y1, x0:x1]
                sub_src = src_ok[y0:y1, x0:x1]
                sub_v = out[y0:y1, x0:x1].astype(np.float32)
                sub_k = (sub_src & ~sub_t).astype(np.float32)
                unk = sub_t.copy()
                _it = 0
                while bool(unk.any()) and _it < 400:
                    _it += 1
                    wsum = cv2.boxFilter(sub_k, -1, (3, 3),
                                         normalize=False)
                    hit = (wsum > 0.05) & unk
                    if not bool(hit.any()):
                        break
                    num = cv2.boxFilter(sub_v * sub_k[:, :, None], -1,
                                        (3, 3), normalize=False)
                    _ws = wsum[hit][:, None]
                    _ws[_ws == 0] = 1.0
                    sub_v[hit] = np.clip(num[hit] / _ws, 0.0, 255.0)
                    sub_k[hit] = 1.0
                    unk &= ~hit
                out[y0:y1, x0:x1] = sub_v.astype(np.uint8)
            return out, int(fills.sum())
        except Exception:
            return cleaned, 0

    def _compose_polish(self, image: np.ndarray, composed: np.ndarray,
                         mask: np.ndarray) -> np.ndarray:
        """ — «پاکسازیِ کثیف»: لکهٔ خاکستری/سبزِ LaMa داخلِ حبابِ
        سفید، وقتی به عکسِ دوم منتقل می‌شود، به‌صورتِ لکهٔ محو دیده می‌شود
        (نمونه: حبابِ «YEP!» و «OH BOY…»). راه‌حل: اگر حلقهٔ دورِ نوار یکنواخت
        باشد (زمینهٔ ساده)، هر پیکسلِ نوار که از رنگِ حلقه تیره‌تر/روشن‌تر
        است «لکه» خوانده می‌شود و با رنگِ خودِ حلقه پر می‌شود.

        فقط جایی اعمال می‌شود که حلقه یکنواخت باشد → روی متنِ رویِ هنر
        (عکس/بافت) دست نمی‌زند."""
        try:
            if mask is None or not np.any(mask):
                return composed
            _pdbg = bool(os.environ.get("MANGA_POLISH_DBG"))
            m = (mask > 0).astype(np.uint8)
            n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
            if n <= 1:
                return composed
            out = composed
            _k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
# کامپوز با دیلیتِ ۹ انجام می‌شود → هر چیزی تا ۹px
# اطرافِ نوار از «عکسِ پاک‌شده» (donor) می‌آید. حلقه باید از
# «اورجینال» باشد وگرنه هالهٔ donor رنگِ فلتن را می‌شکند
# (نمونه: پرِ نوارهایِ حبابِ زرد با بژِ خاکستری).
            _m9 = cv2.dilate(m, np.ones((9, 9), np.uint8)) > 0
            _k2 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
            for i in range(1, n):
                x = int(st[i, cv2.CC_STAT_LEFT])
                y = int(st[i, cv2.CC_STAT_TOP])
                w = int(st[i, cv2.CC_STAT_WIDTH])
                h = int(st[i, cv2.CC_STAT_HEIGHT])
                a = int(st[i, cv2.CC_STAT_AREA])
                if a < 40 or w < 6 or h < 6:
                    continue
                if w > 0.9 * out.shape[1] or h > 0.9 * out.shape[0]:
                    continue
                _pad = 18
                x0 = max(0, x - _pad)
                y0 = max(0, y - _pad)
                x1 = min(out.shape[1], x + w + _pad)
                y1 = min(out.shape[0], y + h + _pad)
                sub = out[y0:y1, x0:x1]
                subm = (lab[y0:y1, x0:x1] == i)
                if not subm.any():
                    continue
                ring = cv2.dilate(subm.astype(np.uint8), _k2) > 0
                ring &= ~subm
                ring &= ~_m9[y0:y1, x0:x1]
# حلقه فقط از پیکسل‌هایِ «اورجینال» ساخته شود:
# نوارهایِ همسایه (موتیلینگِ LaMa/TELEA) آمارِ حلقه را
# آلوده می‌کنند و rstd بی‌دلیل بالا می‌رود. اگر بعد از
# حذف، حلقه خیلی کوچک شد، همان حلقهٔ قبلی (با نوارها).
                try:
                    _ring_o = ring & (m[y0:y1, x0:x1] == 0)
                    if int(np.count_nonzero(_ring_o)) >= 40:
                        ring = _ring_o
                except Exception:
                    pass
# دیوار از حلقه بیرون بماند تا سفیدیِ حباب را
# «تیره» نگیرد و پولیشِ نوارهایِ چسبیده به دیوار هم فعال شود
                try:
                    for _pmN in (getattr(self, "_page_protect", None),
                                 getattr(self, "_page_wall_band", None),
                                 getattr(self, "_page_colored_protect",
                                         None)):
                        if _pmN is not None and _pmN.shape == out.shape[:2]:
                            ring &= (_pmN[y0:y1, x0:x1] == 0)
                except Exception:
                    pass
                if int(np.count_nonzero(ring)) < 40:
                    _ring_n = 0
                else:
                    _ring_n = int(np.count_nonzero(ring))
                rg = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
# گیت‌های فلتنِ «کلِ نوار»:
# آمارِ حلقه از «عکسِ اورجینال» گرفته شود نه
# خروجی — پرِ LaMa (در خروجی) حلقه را آلوده می‌کند و
# متادیتای هر پولیشِ درست را خراب می‌کند.
                try:
                    _rimg = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                    _rv_o = _rimg[y0:y1, x0:x1][ring]
                    if _rv_o.size >= 40:
                        rmed = float(np.median(_rv_o))
                        rstd = float(np.std(_rv_o))
                    else:
                        rmed = rstd = None
                except Exception:
                    rmed = rstd = None
# گیتِ بافتِ خروجی: اگر «نتیجهٔ» کامپوز روی این
# مؤلفه بافت‌مند است (هنرِ حفظ‌شده — مثلِ کارتِ img2 با
# قابِ سفید و خطوطِ داخل)، پولیش (فلت/لکه‌گیری) ممنوع —
# وگرنه فازِ «لکه» هر پیکسلِ روشن‌تر از زمینه (قابِ سفید
# هایلایتِ هنر) را با رنگِ حلقه پر می‌کند («کل حباب با
# رنگ پر شد — لاما روش استفاده نشد»). سنجه روی خروجی
# سنجیده می‌شود نه اورجینال (اورجینال خودِ متن را دارد).
# کالیبراسیون img2: هنر std=66/lap=9.3 ؛ پنلِ تخت std≤4.
# این گیت فقط وقتی معنا دارد که حلقه هم
# «غیریکنواخت» است (نوارِ وسطِ هنر). اگر حلقهٔ اورجینال
# تخت باشد (حبابِ سفید/رنگیِ تخت)، بافتِ خروجی = خودِ
# لکهٔ پرِ LaMa است (لکهٔ سبزِ قابِ رنگی در up0822 —
# پرِ LaMa رنگِ قاب را داخلِ متن کشیده) و باید فلت شود
# پس فقط ترکیبِ «بافت‌مند + حلقهٔ بافت‌مند» رد میشود.
                if rstd is not None and rstd > 12.0:
                    try:
                        _vT = rg[subm].astype(np.float32)
                        if _vT.size >= 200:
                            _lapT = np.abs(cv2.Laplacian(rg, cv2.CV_32F))
                            if (float(np.std(_vT)) > 12.0
                                    or float(np.mean(_lapT[subm])) > 2.5):
# استثنایِ بلوکِ اجباری-LaMa:
# «بافتِ» نوارِ بلوکهایِ اجباری، خودِ شبحِ
# حروفِ LaMa است نه هنر (SFXِ 4e2e77:
# CHANGES TO… ذوب‌شده ولی خوانا — std=۳۴)
# → رد نکن؛ بگذار به گیتها/بازپرِ گرادیانی
# برسد.
                                _fhitd = False
                                try:
                                    for _fbd in (getattr(
                                            self, "_lama_force_rect_boxes",
                                            None) or []):
                                        if not (x > _fbd[2]
                                                or x + w < _fbd[0]
                                                or y > _fbd[3]
                                                or y + h < _fbd[1]):
                                            _fhitd = True
                                            break
                                except Exception:
                                    _fhitd = False
                                if not _fhitd:
                                    if _pdbg:
                                        print(f"  [dbg-polish] SKIP-textured "
                                              f"comp x={x} y={y} {w}x{h} "
                                              f"std={float(np.std(_vT)):.1f} "
                                              f"lap={float(np.mean(_lapT[subm])):.2f}",
                                              flush=True)
                                    continue
                                if _pdbg:
                                    print(f"  [dbg-polish] force-block "
                                          f"comp x={x} y={y} {w}x{h} "
                                          f"(بافت=شبح) → گیتها",
                                          flush=True)
                    except Exception:
                        pass
                elif rstd is None:
                    try:
                        _vT = rg[subm].astype(np.float32)
                        if _vT.size >= 200:
                            _lapT = np.abs(cv2.Laplacian(rg, cv2.CV_32F))
                            if (float(np.std(_vT)) > 12.0
                                    or float(np.mean(_lapT[subm])) > 2.5):
                                continue
                    except Exception:
                        pass
# الف) حلقهٔ اورجینال یکنواخت — حبابِ سفید/رنگیِ تخت که
# حلقه‌اش داخلِ حباب است.
# یکنواختیِ «اکثریتِ» حلقه (≥۷۵٪ در ±۱۲ از
# میانهٔ حلقه) کافی است؛ رینگِ حبابِ سفیدِ بزرگِ 01.jpg
# لبهٔ هنرِ استخر را هم می‌گیرد و rstd کل را بالا می‌برد
# اقلیتِ هنر نباید فلتِ نوار را بلاک کند وگرنه شبحِ
# محوِ متن زنده می‌ماند.
# ب) خودِ نوار «اکثریت‌یکنواخت» (≥۸۰٪ نزدیکِ میانهٔ خودش)
# برای بلوک‌هایِ بزرگ (ماسکِ بلوک/حبابِ زرد) که حلقه‌شان
# هنر است و گیتِ الف نمی‌گیرد؛ اقلیتِ باقی‌مانده =
# جوهرِ شبحِ متن است.
# گیتِ رنگی (درسِ ): «یکنواختی» فقط در
# خاکستری دیده نمی‌شود. کارتِ قرمزِ 890fb1: خاکستریِ حلقه
# یکنواختِ ~۱۲ (rstd=4!) ولی کانالِ R گرادیانِ ۵۰→۱۳ دارد
# پولیشِ فلتِ خاکستری‌فکر کلِ بلوک را با «میانهٔ حلقه»
# یک‌رنگ می‌کند = لگهٔ قرمزِ مستطیلی. سنجه = بیشینهٔ
# stdِ کانال‌هایِ BGR رویِ حلقهٔ اورجینال + اکثریتِ هر کانال.
                _cstd = None
                try:
                    _roc = image[y0:y1, x0:x1][ring].astype(np.float32)
                    if _roc.shape[0] >= 40:
                        _cstd = float(_roc.std(axis=0).max())
                except Exception:
                    _cstd = None
                _cmaj = None
                try:
                    _rocb = image[y0:y1, x0:x1][ring].astype(np.float32)
                    if _rocb.shape[0] >= 40:
                        _cmaj = min(
                            float((np.abs(_rocb[:, _c] -
                                          np.median(_rocb[:, _c]))
                                   <= 12.0).mean())
                            for _c in range(3))
                except Exception:
                    _cmaj = None
                _can_flat = False
                _gate2 = ""
                if rstd is not None and rstd <= 10.0 and (
                        _cstd is None or _cstd <= 10.0):
                    _can_flat = True
                    _gate2 = "A:rstd<=10"
                elif rstd is not None and rstd <= 60.0:
# اکثریتِ یکنواختِ حلقه (حباب با لبهٔ هنر):
                    try:
                        _rvv = rg[ring]
                        _rmv = float(np.median(_rvv))
                        if (float((np.abs(_rvv.astype(np.float32) - _rmv)
                                  <= 12.0).mean()) >= 0.75
                                and (_cmaj is None
                                     or _cmaj >= 0.75)):
                            _can_flat = True
                            _gate2 = "B:ring-majority"
                    except Exception:
                        pass
                if not _can_flat and _pdbg:
                    print(f"  [dbg-polish] comp x={x} y={y} {w}x{h} "
                          f"rstd={rstd if rstd is None else round(rstd,2)} "
                          f"ring_n={_ring_n}")
                if not _can_flat:
# گیتِ «اکثریت‌یکنواخت» فقط برای نوارهایِ
# «داخلِ حباب» (donor box)؛ نوارِ رویِ هنرِ بیرون (راوی
# رویِ زمین/پرده) فلت شود = میلهٔ رنگیِ تخت (img4).
                    try:
                        _in_donor = False
                        for _db2 in (getattr(self, "_donor_boxes", None)
                                     or []):
                            if not (x > _db2[2] or x + w < _db2[0]
                                    or y > _db2[3] or y + h < _db2[1]):
                                _in_donor = True
                                break
                    except Exception:
                        _in_donor = False
                    if _in_donor:
                        try:
                            _gd = rg[subm]
                            if _gd.size >= 40:
                                _gmode = float(np.median(_gd))
# گیتِ C هم رنگی: کامپوننتِ
# گرادیانِ رنگی (کارتِ 890fb1 در خاکستری
# «اکثریت‌یکنواخت» است!) فلت نشود.
                                _gdC = None
                                try:
                                    _subC = sub[subm].astype(np.float32)
                                    if _subC.shape[0] >= 40:
                                        _gdC = min(
                                            float((np.abs(
                                                _subC[:, _c]
                                                - np.median(
                                                    _subC[:, _c]))
                                                <= 10.0).mean())
                                            for _c in range(3))
                                except Exception:
                                    _gdC = None
                                if (float((np.abs(
                                        _gd.astype(np.float32) - _gmode)
                                        <= 10.0).mean()) >= 0.80
                                        and (_gdC is None
                                             or _gdC >= 0.80)):
                                    _can_flat = True
                                    _gate2 = "C:comp-majority"
                        except Exception:
                            pass
                if _can_flat and _pdbg:
                    print(f"  [dbg-polish] FLATTEN comp x={x} y={y} "
                          f"{w}x{h} gate={_gate2} rstd="
                          f"{rstd if rstd is None else round(rstd, 2)} "
                          f"ring_n={_ring_n}", flush=True)
                if _can_flat:
# دامنهٔ فلتن = خودِ نوار + هالهٔ دورِ آن:
# «اثرِ فشردنِ جوهر روی کاغذ» (۴-۱۵ سطحِ زیرِ زمینه
# شکلِ حروف) تا ~۱۳px بیرونِ نوار می‌ریزد (نمونهٔ
# حبابِ زرد: «Alright! I'll increase…» خوانا ماند) —
# با فلت‌کردنِ فقط ۵px زنده می‌ماند.
# شبحِ داخلِ نوارهایِ بزرگِ بلوکی حبابِ زرد
# (لکههای تیرهٔ تیره‌تر از زمینه) با ۱۳px هم اسمش نمی‌شد
# چون گیتِ رنگِ ±۲۶ حفره‌ها را نمی‌گرفت — دیلیتِ ۱۷ +
# گیتِ رنگِ آماری: پیکسلی که «آوتلایرِ» توزیعِ سایهٔ
# نوار است (bis basal) هم داخلِ فلتن.
                    _flat_dom = cv2.dilate(
                        subm.astype(np.uint8),
                        cv2.getStructuringElement(
                            cv2.MORPH_ELLIPSE, (17, 17))) > 0
# گیتِ رنگ: فقط پیکسل‌هایِ «هم‌رنگِ نوار»
# فلت می‌شوند — دیوارِ ضخیم/خشنِ بیرونِ protect (خطِ
# دست‌کشیدهٔ کیمتسو) و هنرِ چسبیده به نوار محفوظ می‌مانند.
                    try:
                        _fm = float(np.median(rg[subm]))
# استثنایِ هستهٔ نوار: بقایایِ روشنِ
# حروف (خاکستریِ ۲۵۰ در برابرِ میانهٔ ۱۶۰) از گیتِ
# رنگ بیرون میافتادند و همان شبحهایِ سفید زنده
# میماندند (پنجرهٔ 4e2e77) — گیت فقط برایِ هاله.
                        _flat_dom &= ((np.abs(
                            rg.astype(np.float32) - _fm) <= 26.0) | subm)
                    except Exception:
                        pass
                    try:
                        for _pmF in (getattr(self, "_page_protect", None),
                                     getattr(self, "_page_wall_band", None)):
                            if _pmF is not None and _pmF.shape == out.shape[:2]:
                                _flat_dom &= (_pmF[y0:y1, x0:x1] == 0)
                    except Exception:
                        pass
                    if int(np.count_nonzero(_flat_dom)) >= 20:
# رنگِ فلتن از «حلقهٔ اورجینال» گرفته می‌شود
# نه از خودِ نوار: اگر LaMa نوار را با رنگِ کمی غلط
# پر کرده باشد (لگهٔ روشنِ حبابِ زردِ 01.jpg / لگهٔ
# سرخِ کارتِ 890fb1)، میانهٔ خودِ نوار همان رنگِ غلط
# را تثبیت می‌کرد. حلقهٔ اورجینال (پیکسل‌هایِ عکسِ
# اصلیِ اطرافِ نوار) = رنگِ واقعیِ زمینهٔ حباب.
# فال‌بک: اگر حلقه‌ی قابلِ اعتماد نبود، همان
# میانهٔ خودِ نوار (رفتارِ قبلی).
                        _refc = None
                        try:
                            _ring_u8 = ring.astype(np.uint8)
                            if int(_ring_u8.sum()) >= 40:
                                _ring_med = float(
                                    np.median(rg[_ring_u8 > 0]))
                                _ring_ok = float((np.abs(
                                    rg[_ring_u8 > 0] - _ring_med)
                                    <= 12.0).mean())
                                if _ring_ok >= 0.75:
                                    _refc = np.median(
                                        sub[_ring_u8 > 0].astype(np.float32),
                                        axis=0)
                        except Exception:
                            _refc = None
                        if _refc is None:
                            _refc = np.median(
                                sub[_flat_dom].astype(np.float32), axis=0)
# فلتنِ گرادیان‌آگاه: پنجرهٔ سیستمِ
# 4e2e77 — هر خطِ متن رویِ گرادیانِ آبی، حلقهٔ
# «محلیِ» خودش را یکنواخت دارد (rstd≤۱۰) و فلت با
# میانهٔ خودش پاک میشد → پلههایِ آبیِ ناهمسانِ
# روی-هم (اسکرینشاتِ سازنده). سنجشِ شیب روی
# «همهٔ پیکسلهایِ زمینهٔ اورجینالِ پنجرهٔ محلی»
# (بیرونِ ماسکِ نوارها — نه فقط حلقهٔ ۲۵px که
# همسایههاشان آن را میبلعند): شیبِ >۶ در هر
# کانال بین ربعِ اول و آخرِ ردیفهای زمینه =
# گرادیان → فلتن بهجایِ رنگِ تخت، «رنگِ ردیفی»
# میان‌یابی‌شده میگیرد — گرادیان زنده میماند
# لکههایِ LaMa هم پاک میشوند.
                        try:
                            _prof = None
                            try:
# پنجرهٔ پروفایلِ بازتر
# (±۶۰): در بلوکهایِ چندخطی، ماسکهایِ
# خطوط، پنجرهٔ ۱۸px را میبلعند و مدل از
# ۲-۳ ردیفِ باقیمانده ساخته میشد (رنگِ
# غلط → دوختِ عمودی).
                                _py = max(0, y - 60)
                                _py2 = min(m.shape[0], y + h + 60)
                                _bgw = (m[_py:_py2, x0:x1] == 0)
                                if int(_bgw.sum()) >= 60:
                                    _subO = image[_py:_py2, x0:x1]
                                    _rows = []
                                    _cols = []
                                    _free = max(
                                        6, int(0.45 * _bgw.shape[1]))
                                    for _rr in range(
                                            _bgw.shape[0]):
                                        _selr = _bgw[_rr]
                                        if int(_selr.sum()) >= _free:
                                            _rows.append(
                                                _rr + _py - y0)
                                            _cols.append(np.median(
                                                _subO[_rr][_selr],
                                                axis=0))
                                    if len(_rows) >= 2 \
                                            and (_rows[-1] - _rows[0]) \
                                            >= 24:
                                        _rarr = np.asarray(
                                            _rows, np.float32)
                                        _carr = np.asarray(
                                            _cols, np.float32)
                                        _q = max(
                                            1, len(_rows) // 4)
                                        _mt = np.median(
                                            _carr[:_q], axis=0)
                                        _mb = np.median(
                                            _carr[-_q:], axis=0)
                                        _dr = float(np.abs(
                                            _mt - _mb).max())
                                        if _pdbg:
                                            try:
                                                print(
                                                    f"  [dbg-grad26] comp "
                                                    f"x={x} y={y} {w}x{h} "
                                                    f"drift={_dr:.1f} "
                                                    f"nrows={len(_rows)}",
                                                    flush=True)
                                            except Exception:
                                                pass
                                        if _dr > 6.0:
                                            _prof = (
                                                _rarr, _carr)
                            except Exception:
                                _prof = None
                            if _prof is not None:
                                _rarr, _carr = _prof
                                _h = sub.shape[0]
                                _allr = np.arange(_h, dtype=np.float32)
                                _rowc = np.zeros((_h, 3), np.float32)
                                for _ch in range(3):
                                    _rowc[:, _ch] = np.interp(
                                        _allr, _rarr, _carr[:, _ch])
                                _sF2 = sub.copy()
                                _rowg = (0.299 * _rowc[:, 2]
                                           + 0.587 * _rowc[:, 1]
                                           + 0.114 * _rowc[:, 0])
                                for _rr in range(_h):
                                    _rd = _flat_dom[_rr]
                                    if not _rd.any():
                                        continue
                                    _gate = np.abs(
                                        rg[_rr].astype(np.float32)
                                        - float(_rowg[_rr])) <= 26.0
# گیتِ رنگ فقط رویِ هاله:
# هستهٔ نوار (= خودِ متن) همیشه بازپر
# میشود — بقایایِ سفیدِ حروف از مدل
# >۲۶ فاصله داشتند و گیت، همان شبحها
# را زنده نگه میداشت (خطوطِ سفیدِ
# پایینِ پنجرهٔ 4e2e77).
                                    _gate |= subm[_rr]
                                    _rd = _rd & _gate
                                    if not _rd.any():
                                        continue
                                    _sF2[_rr][_rd] = np.clip(
                                        np.rint(_rowc[_rr]), 0,
                                        255).astype(np.uint8)
                                sub[:] = _sF2
                                out[y0:y1, x0:x1] = sub
                                continue
                        except Exception:
                            pass
                        fillc = _refc
                        _sF = sub.copy()
                        _sF[_flat_dom] = np.clip(
                            np.rint(fillc[None, None, :]), 0, 255).astype(np.uint8)
                        sub[:] = _sF
                        out[y0:y1, x0:x1] = sub
                        continue
# بلوکِ بزرگِ «فلت رویِ گرادیان»: بلوکهایِ
# اجباری-LaMaیِ پنجرهٔ سیستمِ 4e2e77 ([TRAITS…]/[CLASS…])
# گیتهایِ فلتن (A/B/C) رینگِ پهنِ پنل+هنر را رد
# میکنند (rstd>10) و پرِ تختِ روشنِ LaMa [77,190,251]
# رویِ گرادیانِ آبی میماند = قابِ مستطیلیِ روشن
# (اسکرینشاتِ سازنده). مدلِ «جداکردنی» = ردیف(y)+ستون(x):
# گرادیانِ عمودی و افقی هر دو بازسازی میشوند؛ خشنیِ
# پروفایل = هنر/بافت → رد. انحرافِ پر از مدل ≥۳.۵ =
# پرِ غلط → بازپرِ ردیفی-ستونی.
                if not _can_flat and a >= 4000 and (w >= 60 or h >= 60):
                    try:
                        _pyc = max(0, y - 60)
                        _pye = min(m.shape[0], y + h + 60)
                        _bgwc = (m[_pyc:_pye, x0:x1] == 0)
                        _subO = image[_pyc:_pye, x0:x1]
                        _offc = y0 - _pyc
                        _sepc = None
                        if int(_bgwc.sum()) >= 200:
# پروفایلِ ردیفی
                            _rowsc = []
                            _colsc = []
                            _freec = max(
                                6, int(0.45 * _bgwc.shape[1]))
                            for _rrc in range(_bgwc.shape[0]):
                                _selrc = _bgwc[_rrc]
                                if int(_selrc.sum()) >= _freec:
                                    _rowsc.append(_rrc - _offc)
                                    _colsc.append(np.median(
                                        _subO[_rrc][_selrc], axis=0))
# پروفایلِ ستونی
                            _colsxc = []
                            _colsvc = []
                            for _colidx in range(_bgwc.shape[1]):
                                _selcc = _bgwc[:, _colidx]
                                if int(_selcc.sum()) >= 6:
                                    _colsxc.append(_colidx)
                                    _colsvc.append(np.median(
                                        _subO[:, _colidx][_selcc],
                                        axis=0))
                            if len(_rowsc) >= 4 and len(_colsxc) >= 4 \
                                    and (_rowsc[-1] - _rowsc[0]) >= 24:
                                _rarrc = np.asarray(_rowsc, np.float32)
                                _carrc = np.asarray(_colsc, np.float32)
                                _xarrc = np.asarray(
                                    _colsxc, np.float32)
                                _varrc = np.asarray(
                                    _colsvc, np.float32)
                                _quat = max(1, len(_rowsc) // 4)
                                _mtc = np.median(
                                    _carrc[:_quat], axis=0)
                                _mbc = np.median(
                                    _carrc[-_quat:], axis=0)
                                _drc = float(np.abs(
                                    _mtc - _mbc).max())
                                _gmean = float(np.mean(_carrc))
                                if _drc > 6.0:
# هموارسازی (۹تایی) + گیتِ خشنی
                                    try:
                                        _kc = np.ones(
                                            9, np.float32) / 9.0
                                        _csc = np.zeros_like(_carrc)
                                        _vsc = np.zeros_like(_varrc)
                                        for _chan in range(3):
                                            _csc[:, _chan] = np.convolve(
                                                np.pad(_carrc[:, _chan],
                                                       (4, 4),
                                                       mode='edge'),
                                                _kc, mode='valid')
                                            _vsc[:, _chan] = np.convolve(
                                                np.pad(_varrc[:, _chan],
                                                       (4, 4),
                                                       mode='edge'),
                                                _kc, mode='valid')
                                        _dcol = float(np.abs(np.diff(
                                            _csc, n=2,
                                            axis=0)).mean())
                                        _d2xc = float(np.abs(np.diff(
                                            _vsc, n=2,
                                            axis=0)).mean())
                                        if _dcol <= 1.2 \
                                                and _d2xc <= 1.2:
                                            _sepc = (_rarrc, _csc,
                                                       _xarrc, _vsc,
                                                       _gmean)
                                    except Exception:
                                        _sepc = None
                        if _sepc is not None:
                            _rarrc, _csc, _xarrc, _vsc, _gmean = \
                                _sepc
                            _subh = sub.shape[0]
                            _wc = sub.shape[1]
# مدلِ ردیفی (گرادیانِ عمودی) — پروفایلِ ستونی
# کنار گذاشته شد: ستونهایِ قابِ سفیدِ پنل
# میانگینِ ستون را می‌کشند و رنگِ مدل را در
# کلِ ستون غلط میکنند (لکهٔ زردِ بالای پنل)
                            _rowcc = np.zeros((_subh, 3), np.float32)
                            for _chan in range(3):
                                _rowcc[:, _chan] = np.interp(
                                    np.arange(_subh, dtype=np.float32),
                                    _rarrc, _csc[:, _chan])
                            _modelcc = np.repeat(
                                _rowcc[:, None, :], _wc, axis=1)
                            _mgc = (0.299 * _modelcc[..., 2]
                                      + 0.587 * _modelcc[..., 1]
                                      + 0.114 * _modelcc[..., 0])
# انحرافِ پرِ فعلی از مدل (فقط روی نوار)
                            _fillrows = []
                            _modelrows = []
                            for _rrc in range(_subh):
                                _srow = subm[_rrc]
                                if int(_srow.sum()) >= 6:
                                    _fillrows.append(float(np.median(
                                        rg[_rrc][_srow])))
                                    _modelrows.append(float(np.median(
                                        _mgc[_rrc][_srow])))
                            _devc = (float(np.mean(np.abs(
                                np.asarray(_fillrows)
                                - np.asarray(_modelrows))))
                                if len(_fillrows) >= 4 else 99.0)
                            if _pdbg:
                                try:
                                    print(f"  [dbg-grad26c] x={x} y={y} "
                                          f"{w}x{h} dev={_devc:.1f}",
                                          flush=True)
                                except Exception:
                                    pass
                            if _devc >= 3.5:
                                _domc = cv2.dilate(
                                    subm.astype(np.uint8),
                                    cv2.getStructuringElement(
                                        cv2.MORPH_ELLIPSE, (17, 17))) > 0
                                try:
                                    for _pmc in (
                                            getattr(self, "_page_protect",
                                                    None),
                                            getattr(self, "_page_wall_band",
                                                    None)):
                                        if _pmc is not None \
                                                and _pmc.shape == \
                                                out.shape[:2]:
                                            _domc &= (
                                                _pmc[y0:y1, x0:x1] == 0)
                                except Exception:
                                    pass
                                _sF = sub.copy()
# بدونِ گیتِ رنگ: خودِ پرِ غلطِ LaMa در
# ردیفهایِ پایین از مدل >۲۶ فاصله داشت و
# گیت، همان پرِ غلط را زنده نگه میداشت =
# نوارِ ترکیبی. دامنه = نوار+هاله منهایِ
# نقشههایِ حفاظت — کافی است.
                                _rdc = _domc
                                if int(_rdc.sum()) >= 20:
                                    _sF[_rdc] = np.clip(np.rint(
                                        _modelcc[_rdc]), 0,
                                        255).astype(np.uint8)
                                    sub[:] = _sF
                                    out[y0:y1, x0:x1] = sub
                                    continue
                    except Exception:
                        pass
                if rstd is None or rstd > 26.0:
                    continue  # زمینهٔ بافت‌دار → دست نزن
                _dv_thr = 14.0 if rstd <= 18.0 else 26.0
                stain = subm & (np.abs(rg.astype(np.float32) - rmed) > _dv_thr)
                if not stain.any():
                    continue
                if int(np.count_nonzero(stain)) > 0.8 * int(subm.sum()):
                    continue  # کلِ نوار متفاوت است → ساختارِ واقعی، نه لکه
                fill = np.median(sub[ring].astype(np.float32), axis=0)
                _s = sub.copy()
                _s[stain] = np.clip(np.rint(fill[None, None, :]), 0, 255
                                    ).astype(np.uint8)
                sub[:] = _s
                out[y0:y1, x0:x1] = sub
# «فلتنِ کلِ داخلِ حباب»  حذف شد:
# کاربر: «عکسِ دوم حبابش پاک نشه» — در خروجی فقط نوارِ متن
# مجاز به تغییر است. فلتنِ کلِ اینتریور حتی با «گیتِ رنگ»
# هرگاه LaMa داخل را با رنگِ غلط پر کرده بود همان رنگِ غلط
# را تثبیت می‌کرد (نمونهٔ 01.jpg: حبابِ زرد → خاکستریِ تخت).
# شبحِ بینِ نوارها را «پولیشِ نوار + ۱۳px» و جارویِ بقایا
# می‌برند؛ زمینهٔ حباب همیشه پیکسلِ اورجینال می‌ماند.
            return out
        except Exception:
            return composed

    def _texture_refill_donor(self, donor: np.ndarray,
                              original: np.ndarray,
                              cmp_mask: np.ndarray) -> None:
        """ — بازپرِ بافت برای زمینه‌هایِ نویز/نقش‌ونگار.

        LaMa روی برف‌نوی/خال‌خال (EXECِ 412e9e، پلاکِ GREEN MOON) پرِ
        «تختِ بی‌بافت» می‌دهد — نویزِ ریز میانگین می‌شود و مستطیلِ صاف
        می‌ماند. برای هر مؤلفهٔ نوارمانندِ ماسک که حلقه‌اش بافت‌مند است
        (std حلقه > ۳۶):
          low-freq = میان‌یابیِ قائمِ ستونی بینِ ردیف‌هایِ تمیزِ
                      بالا/پایینِ نوار (گرادیانِ واقعی)
          high-freq = نویزِ واقعیِ نزدیک‌ترین پیکسلِ «تمیزِ بی‌لبه»
                      (برفِ زمینه بدونِ لبهٔ دیوار/قاب)
        حباب‌ها/پلاک‌هایِ صاف (std ≤ ۳۶) دست‌نخورده می‌مانند."""
        try:
            if donor is None or original is None or cmp_mask is None:
                return
            h, w = donor.shape[:2]
            g = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
            blur_b = cv2.GaussianBlur(original, (0, 0), 3.5).astype(
                np.float32)
            resid = original.astype(np.float32) - blur_b
            resid_max = np.max(np.abs(resid), axis=2)
            n, lb, stt, _ = cv2.connectedComponentsWithStats(
                cmp_mask.astype(np.uint8), 8)
            _dbg = bool(os.environ.get("MANGA_TR_DBG"))
            for i in range(1, n):
                cx, cy, cw, ch, _a = [int(v) for v in stt[i]]
                if cw < 24 or ch > 380 or ch < 6:
                    continue
                x0, y0 = max(0, cx - 6), max(0, cy - 6)
                x1, y1 = min(w, cx + cw + 6), min(h, cy + ch + 6)
                comp = (lb[y0:y1, x0:x1] == i)
                mall = cmp_mask[y0:y1, x0:x1]
                ring = (cv2.dilate(comp.astype(np.uint8),
                                   np.ones((13, 13), np.uint8)) > 0) \
                    & (~comp) & (~mall)
                if int(np.count_nonzero(ring)) < 200:
                    continue
                rvals = g[y0:y1, x0:x1][ring].astype(np.float32)
                if float(rvals.std()) <= 36.0:
                    continue
# پیکسل‌هایِ «تمیزِ بی‌لبه» برای برداشتِ نویز — لبه‌های
# تیز (دیوار/قاب) با resid بزرگ حذف می‌شوند
                clean = ring & (resid_max[y0:y1, x0:x1] <= 45.0)
                if int(np.count_nonzero(clean)) < 200:
                    continue
                crop_o = blur_b[y0:y1, x0:x1]
                crop_d = donor[y0:y1, x0:x1]
# فقط پیکسل‌هایِ «واقعاً پرشده» (پرِ LaMa)
# بازپر می‌شوند؛ جایی که donor = اصلِ عکس است (ماسکِ
# تنگِ پالی‌به‌پالی) بافتِ اورجینال دست‌نخورده می‌ماند —
# نویزِ مصنوعی هرگز جایِ بافتِ واقعی را نمی‌گیرد.
                _chg = (np.abs(crop_d.astype(np.int16)
                                 - original[y0:y1, x0:x1].astype(np.int16))
                          .max(axis=2) > 6)
                _chg = cv2.dilate(_chg.astype(np.uint8),
                                    np.ones((5, 5), np.uint8)) > 0
                _tgt = comp & _chg
                if int(np.count_nonzero(_tgt)) < 300:
                    continue
                if int(np.count_nonzero(_tgt)) < \
                        0.25 * max(1, int(np.count_nonzero(comp))):
# تغییراتِ جزئی → donor همین‌جا سالم است
                    continue
                lowf = cv2.GaussianBlur(crop_d.astype(np.float32),
                                        (0, 0), 3.5)
                ys_i = np.nonzero(comp.any(axis=1))[0]
                if ys_i.size == 0:
                    continue
                ymin, ymax = int(ys_i.min()), int(ys_i.max())
                span = float(max(1, ymax - ymin))
# مرجعِ هموارشده در محورِ x: میانگینِ ۵ ردیفِ
# هر ستون «رگهٔ عمودی» می‌سازد؛ ابتدا ستون‌هایِ آلوده به
# ماسک حذف و با میان‌یابیِ افقی پر، بعد نرمِ گاوسیِ ۱بعدی.
                W96 = x1 - x0
                ty0, ty1 = max(0, ymin - 6), ymin
                by0b, by1b = ymax + 1, min(mall.shape[0], ymax + 7)
                tband = crop_o[ty0:ty1] if ty1 > ty0 else None
                bband = crop_o[by0b:by1b] if by1b > by0b else None
                tvalid = (~mall[ty0:ty1]) if ty1 > ty0 else None
                bvalid = (~mall[by0b:by1b]) if by1b > by0b else None

                def _band_ref(band, valid):
                    if band is None or valid is None:
                        return None
                    vals = np.where(valid[..., None], band, np.nan)
                    with np.errstate(invalid="ignore"):
# میانهٔ跨-ردیف (مقاوم به خالِ بافت)
                        ref = np.nanmedian(vals, axis=0)
                    bad = ~np.isfinite(ref).all(axis=-1)
                    if bool(bad.all()):
                        return None
                    if bad.any():
                        xs_ok = np.nonzero(~bad)[0]
                        for cc in np.nonzero(bad)[0]:
                            j = xs_ok[np.argmin(np.abs(xs_ok - cc))]
                            ref[cc] = ref[j]
# GaussianBlur رویِ (W,3) کانال‌هایِ رنگ را
# با هم قاطی می‌کند (خاکستری!) → شکلِ (1,W,3) لازم است
# میانهٔ پهنِ跨-ستون (۴۱): نوارِ تیره/روشنِ
# قاب و شیارها (۱۰–۲۵px) را حذف می‌کند
                    ref2 = np.clip(ref, 0, 255).astype(
                        np.uint8).reshape(1, -1, 3)
                    ref2 = cv2.medianBlur(ref2, 41)
                    ref2 = cv2.GaussianBlur(ref2, (0, 0), 3.0)
                    return ref2.reshape(-1, 3).astype(np.float32)

                tref_full = _band_ref(tband, tvalid)
                bref_full = _band_ref(bband, bvalid)
                if tref_full is None and bref_full is None:
                    continue
# اگر یک باندِ مرجع «آلودهٔ ساختار» است
# (قاب/شیار از باند عبور می‌کند — پلاکِ GREEN MOON:
# tref std=35 در برابرِ bref std=13) فقط باندِ پایدار
# ملاک می‌شود؛ وگرنه میان‌یابیِ قائمِ کامل.
                _tstd = float(np.std(tref_full.mean(axis=1))) \
                    if tref_full is not None else 1e9
                _bstd = float(np.std(bref_full.mean(axis=1))) \
                    if bref_full is not None else 1e9
                if min(_tstd, _bstd) > 0 and \
                        max(_tstd, _bstd) > 1.8 * min(_tstd, _bstd) \
                        and min(_tstd, _bstd) <= 20.0:
                    _const = bref_full if _bstd <= _tstd else tref_full
                else:
                    _const = None
                _ref_fail = False
                for x in np.nonzero(_tgt.any(axis=0))[0]:
                    yy = np.nonzero(_tgt[:, x])[0]
                    if yy.size == 0:
                        continue
                    if _const is not None:
                        lowf[yy, x] = _const[x][None, :]
                        continue
                    tref = tref_full[x] if tref_full is not None else None
                    bref = bref_full[x] if bref_full is not None else None
                    t = (yy.astype(np.float32) - float(ymin)) / span
                    if tref is not None and bref is not None:
                        lowf[yy, x] = ((1.0 - t)[:, None] * tref[None, :]
                                       + t[:, None] * bref[None, :])
                    elif tref is not None:
                        lowf[yy, x] = tref[None, :]
                    else:
                        lowf[yy, x] = bref[None, :]
                if _ref_fail:
                    continue
# نویزِ واقعی از نزدیک‌ترین پیکسلِ تمیزِ بی‌لبه
                dist, lab = cv2.distanceTransformWithLabels(
                    (~clean).astype(np.uint8), cv2.DIST_L2, 5,
                    labelType=cv2.DIST_LABEL_PIXEL)
                cy_i, cx_i = np.nonzero(clean)
                mys, mxs = np.nonzero(_tgt)
                idx = np.clip(lab[mys, mxs] - 1, 0, cy_i.size - 1)
                hf_map = np.zeros_like(lowf)
                hf_map[mys, mxs] = \
                    resid[y0:y1, x0:x1][cy_i[idx], cx_i[idx]]
# نمونه‌برداریِ نزدیک‌ترین‌همسایه «قفلِ ستونی»
# می‌سازد (رگهٔ عمودی)؛ بلورِ ریز آن را می‌شکند
                hf_map = cv2.GaussianBlur(hf_map, (0, 0), 0.8)
                fill = np.clip(lowf + hf_map, 0, 255).astype(np.uint8)
                sub = crop_d.copy()
                sub[_tgt] = fill[_tgt]
                donor[y0:y1, x0:x1] = sub
                try:
                    _trd = os.environ.get("MANGA_TR_DUMP", "")
                    if _trd:
                        cv2.imwrite(os.path.join(
                            _trd, f"comp_{cx}_{cy}_before.png"),
                            crop_d.astype(np.uint8))
                        cv2.imwrite(os.path.join(
                            _trd, f"comp_{cx}_{cy}_fill.png"), fill)
                        if tref_full is not None:
                            cv2.imwrite(os.path.join(
                                _trd, f"comp_{cx}_{cy}_tref.png"),
                                np.clip(tref_full, 0, 255).astype(
                                    np.uint8).reshape(1, -1, 3))
                        if bref_full is not None:
                            cv2.imwrite(os.path.join(
                                _trd, f"comp_{cx}_{cy}_bref.png"),
                                np.clip(bref_full, 0, 255).astype(
                                    np.uint8).reshape(1, -1, 3))
                except Exception:
                    pass
                if _dbg:
                    try:
                        print(f"  [🔍]texture-refill comp@({cx},{cy}) "
                              f"{cw}x{ch} ring_std="
                              f"{float(g[cy:cy+ch, cx:cx+cw].std()):.0f}")
                    except Exception:
                        pass
        except Exception:
            if _dbg:
                import traceback as _tb
                print("  [!]texture-refill error:")
                _tb.print_exc()

    def _fill_harmony_qc(self, donor: np.ndarray, original: np.ndarray,
                         zone: np.ndarray, verbose: bool = True) -> int:
        """ — QCِ هماهنگیِ رنگِ پر، برایِ «همهٔ» پرکنندهها.

        پرِ خاکستری LaMa رویِ
        زمینهٔ سفید/بنفش (img4ِ #13/#14/#20)، پرِ سفید رویِ آسمان/پوست
        (#03/CMP1)، و پرِ یکرنگی که مرزِ حباب را میپوشاند از هر مسیری
        (فوری/TELEA/LaMa/هارمونیکِ ۲۲۷) میآیند. QCهایِ قبلی فقطِ LaMa و
        فقطِ کروما بودند. این QC درست قبلِ کامپوز میآید:
          ۱) نوارِ متن به قطعههایی که «مرزِ قویِ اورجینال» بینشان حایل
             است شکسته میشود → داخلِ حباب و بیرونِ حباب هرکدام رنگِ
             سمتِ خودشان را میگیرند (ریشهٔ «یک رنگ کرده»).
          ۲) هر قطعه: میانهٔ پرِ فعلی در برابرِ حلقهٔ محلیاش از
             اورجینال (لومیا + کروما با هم) سنجیده میشود؛ اختلافِ
             ≥۲۰ = دوبارهپر از حلقه (پلن رویِ گرادیانِ نرم، میانه رویِ
             زمینهٔ تخت) با فدرِ نرم.
          ۳) حلقهٔ شلوغ (بافت/گرادیانِ تند — هنر) هرگز دستنخورده
             میماند؛ فقط پیکسلهایِ واقعاً پرشده (تغییرکرده) لمس
             میشوند؛ هیچ نوشتنی بیرونِ نوارِ متن نمیرود.
        """
        try:
            if donor is None or original is None or zone is None:
                return 0
            if donor.shape[:2] != original.shape[:2]:
                return 0
            if zone.shape[:2] != donor.shape[:2]:
                return 0
            zm = zone > 0
            if not zm.any():
                return 0
            _diff = cv2.absdiff(donor, original).max(axis=2)
            ch = (_diff > 12) & zm
            if not ch.any():
                return 0
            _g = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
# فقط «مرزهایِ ساختاریِ درشت» (کادرِ حباب، قابِ
# پنل، ستون) قطعه‌بندی میکنند. Canny رویِ اصل، لبههایِ
# «گلیفِ متن» را هم میداد → نوارهایِ متنِ متراکم به خردههایی
# زیرِ آستانهٔ ۴۰px میشکستند و QC هیچوقت به آنها نمیرسید
# (باقیماندهٔ خاکستریِ y=8500ِ img4). با بلورِ σ=۴ لبههایِ
# گلیف (کشِ ~۴-۶px) محو میشوند و مرزهایِ درشت میمانند.
            _gb = cv2.GaussianBlur(_g, (0, 0), 4.0)
            _ed = cv2.Canny(_gb, 40, 120)
            _ed = (cv2.dilate(
                _ed, cv2.getStructuringElement(
                    cv2.MORPH_ELLIPSE, (7, 7))) > 0)
            zm_c = zm & (~_ed)
            if not zm_c.any():
                return 0
            _n_lab, _lab, _stats, _cents = \
                cv2.connectedComponentsWithStats(
                    zm_c.astype(np.uint8), 8)
            H, W = zm.shape[:2]
            _k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17))
            _dbg = os.environ.get("MANGA_HQC_DBG", "0") == "1"
            n_fix = 0
            n_px = 0
            for _i in range(1, _n_lab):
                try:
                    _a = int(_stats[_i, cv2.CC_STAT_AREA])
                    if _a < 40:
                        continue
                    _sx = int(_stats[_i, cv2.CC_STAT_LEFT])
                    _sy = int(_stats[_i, cv2.CC_STAT_TOP])
                    _sw = int(_stats[_i, cv2.CC_STAT_WIDTH])
                    _sh = int(_stats[_i, cv2.CC_STAT_HEIGHT])
                    pcc = (_lab[_sy:_sy + _sh, _sx:_sx + _sw] == _i)
                    y0, y1, x0, x1 = _sy, _sy + _sh - 1, _sx, _sx + _sw - 1
                    ch_b = ch[_sy:_sy + _sh, _sx:_sx + _sw]
                    pch_b = pcc & ch_b
                    if int(pch_b.sum()) < 25:
                        continue
# حلقه از اورجینال — داخلِ جعبهٔ گسترش‌یافته تا سبک بماند
                    _pad = 20
                    by0 = max(0, y0 - _pad)
                    bx0 = max(0, x0 - _pad)
                    by1 = min(H, y1 + _pad + 1)
                    bx1 = min(W, x1 + _pad + 1)
                    _pcp = np.zeros((by1 - by0, bx1 - bx0), np.uint8)
                    _pcp[y0 - by0:y1 - by0 + 1,
                         x0 - bx0:x1 - bx0 + 1] = \
                        pcc.astype(np.uint8)
# حلقهٔ «مد-خوشهای»: نامزدها = دیلاتِ قطعه (۱۷px
# درِ کم تا ۳۱px) منهایِ مرزهایِ قوی؛ «مهم نیست داخلِ
# zm باشد» — فاصلهٔ بینخطِ اورجینال هم پسزمینه است.
# جوهرِ متنِ خطهایِ مجاور با پیکِ هیستوگرامِ لومیا +
# پنجرهٔ ±۴۰ دورِ همان خوشه کنار گذاشته میشود تا
# حلقه = رنگِ پسزمینهٔ غالب باشد نه جوهر.
                    _oc = original[by0:by1, bx0:bx1]
                    _ocf = _oc.astype(np.float32)
                    _lum_map = (_ocf[:, :, 0] * 0.114
                                + _ocf[:, :, 1] * 0.587
                                + _ocf[:, :, 2] * 0.299)
                    _edc = _ed[by0:by1, bx0:bx1]
                    _chc = ch[by0:by1, bx0:bx1]
# نامزدها = دورِ قطعه − مرز − «همهٔ پیکسلهایِ پروشده»
# (خودِ قطعه و خطهایِ مجاور) → حلقه = پسزمینهٔ واقعیِ
# دستنخورده (بینخط/حاشیه)، هرگز رنگِ خودِ پرها.
                    cand = (cv2.dilate(_pcp, _k) > 0) \
                        & (~_edc) & (~_chc)
                    if int(cand.sum()) < 80:
                        cand = (cv2.dilate(_pcp, _kernel) > 0) \
                            & (~_edc) & (~_chc)
                    _nr = int(cand.sum())
                    if _nr < 80:
                        if _dbg:
                            print(f"    [228d] قطعه@({x0},{y0}) "
                                  f"حلقهکم={_nr}", flush=True)
                        continue
                    _gl = _lum_map[cand]
                    _hist, _edges = np.histogram(_gl, bins=32,
                                                 range=(0, 256))
                    _mb = int(_hist.argmax())
                    if int(_hist[_mb]) < 0.22 * _nr:
# هیچ خوشهای حتی ۱۲٪ هم نیست (هنرِ کاملاً مرکب)
# → نه آمارِ معتبر نه میدانِ امن؛ دستنخورده.
                        if _dbg:
                            print(f"    [228d] قطعه@({x0},{y0}) "
                                  f"حلقهٔ بیخوشه "
                                  f"({_hist[_mb]}/{_nr}) رد",
                                  flush=True)
                        continue
# همترازیِ pch با جعبهٔ پَددار (pch_b رویِ جعبهٔ stats است)
                    pch_p = np.zeros((by1 - by0, bx1 - bx0), bool)
                    pch_p[y0 - by0:y1 - by0 + 1,
                          x0 - bx0:x1 - bx0 + 1] = pch_b
                    _m0 = float(0.5 * (_edges[_mb] + _edges[_mb + 1]))
                    fbm = cand & (np.abs(_lum_map - _m0) <= 40.0)
                    if int(fbm.sum()) < 80:
                        if _dbg:
                            print(f"    [228d] قطعه@({x0},{y0}) "
                                  f"خوشهکم={int(fbm.sum())}", flush=True)
                        continue
# همترازیِ pch (بالا انجام شد) — آمارِ حلقه
                    rpx = _ocf[fbm]
                    rmed = np.median(rpx, axis=0)
                    rsp = float(np.max(
                        np.percentile(rpx, 90, axis=0)
                        - np.percentile(rpx, 10, axis=0)))
                    _rl = float(rmed[0] * 0.114 + rmed[1] * 0.587
                                + rmed[2] * 0.299)
                    fpx = donor[by0:by1, bx0:bx1][pch_p].astype(
                        np.float32)
                    if fpx.shape[0] < 25:
                        continue
                    fmed = np.median(fpx, axis=0)
                    fstd = float(np.median(np.std(fpx, axis=0)))
                    d = float(np.abs(fmed - rmed).max())
# آستانهٔ تطبیقی: چشم رویِ زمینهٔ روشن/تیره حساستر است
                    _thr = 20.0
                    if _rl >= 232.0:
                        _thr = 13.0
                    elif _rl <= 60.0:
                        _thr = 14.0
                    _fsp = float(np.max(fmed) - np.min(fmed))
                    if _fsp <= 12.0 and rsp >= 30.0:
                        _thr = min(_thr, 14.0)  # پرِ خنثی رویِ رنگی
                    if d < _thr:
                        if _dbg:
                            print(f"    [228d] قطعه@({x0},{y0}) "
                                  f"سالم d={d:.0f} پ={fmed.round(0)} "
                                  f"ح={rmed.round(0)}", flush=True)
                        continue
# گاردِ «حلقه باید نمایندهٔ زمینهٔ زیرِ
# خودِ قطعه باشد»: قطعههایِ متنِ رویِ کتِ تیره که
# حلقه‌شان تا دیوار/زمینهٔ روشنِ پشتِ شخص میرسد
# (y=9536ِ 9.jpg: حلقه=دیوارِ روشن ~۲۲۵، زمینهٔ زیرِ
# متن=کتِ تیره ~۷۰) → QCِ حلقه پرِ «درستِ» تیرهٔ LaMa
# را ناهماهنگ میخواند و با رنگِ روشنِ حلقه دوبارهپر
# میکرد = «لکهٔ سفیدِ ابرمانند» (۲۴۸هزارpx در یک
# صفحه!). حالا اگر میانهٔ لومیایِ «زمینهٔ زیرِ قطعه در
# اورجینال» (پس‌زمینه اکثریت است — متن اقلیت) با
# مرکزِ خوشهٔ حلقه بیش از ۶۰ واحد فاصله داشته باشد
# حلقه زمینهٔ «دیگری» را توصیف میکند → قطعه
# دستنخورده میماند.
                    try:
                        _ul = _lum_map[pch_p]
                        if _ul.size >= 40:
                            _umed = float(np.median(_ul))
                            if abs(_umed - _m0) > 60.0:
                                if _dbg:
                                    print(
                                        f"    [228d] قطعه@({x0},{y0}) "
                                        f"حلقه=زمینهٔ دیگر "
                                        f"(زیرِ قطعه {_umed:.0f} vs "
                                        f"حلقه {_m0:.0f}) → رد",
                                        flush=True)
                                continue
                    except Exception:
                        pass
                    if _dbg:
                        print(f"    [228d] قطعه@({x0},{y0}) d={d:.0f} "
                              f"پ={fmed.round(0)} ح={rmed.round(0)} "
                              f"rsp={rsp:.0f}", flush=True)
                    plane = None
# «میدانِ فرکانسِ پایین» پیشفرضِ خاموش: درِ تستِ واقعی
# (img4ِ r20) نزدیکِ مرزِ هنر، رنگِ تیرهِ هنرِ مجاور را
# به داخلِ پر میکشید (Δ منفیِ نوارهایِ بالا). فقط با
# MANGA_HQC_FIELD=1 برایِ آزمایش.
                    _field = (os.environ.get("MANGA_HQC_FIELD", "0") == "1"
                              and fstd <= 32.0)
                    if not _field:
                        if rsp <= 16.0:
                            tgt = rmed
                        elif fstd <= 55.0:
                            try:
                                ry, rx = np.nonzero(fbm)
                                _A = np.stack(
                                    [np.ones(rx.size, np.float32),
                                     (rx + bx0 - x0).astype(np.float32),
                                     (ry + by0 - y0).astype(np.float32)],
                                    axis=1)
                                _rpx = rpx
                                _coef, *_ = np.linalg.lstsq(
                                    _A, _rpx, rcond=None)
                                _res = np.sqrt(
                                    ((_A @ _coef - _rpx) ** 2)
                                    .sum(axis=1)).mean()
                                if _res > 13.0:
                                    if _dbg:
                                        print(f"    [228d] قطعه@({x0},{y0}) "
                                              f"حلقهشلوغ res={_res:.0f} رد",
                                              flush=True)
                                    continue  # هنر؛ دستنخورده
                                plane = _coef
                            except Exception:
                                continue
                        else:
                            if _dbg:
                                print(f"    [228d] قطعه@({x0},{y0}) "
                                      f"پربافت fstd={fstd:.0f} رد",
                                      flush=True)
                            continue
# مقدارِ نو فقط رویِ پیکسلهایِ پرشده — همراستا با
# جعبهٔ پَددار (pch_p بالا ساخته شد)
                    repl = donor[by0:by1, bx0:bx1].copy()
                    if _field:
                        try:
                            _pp2 = 24
                            _fy0 = max(0, by0 - _pp2)
                            _fx0 = max(0, bx0 - _pp2)
                            _fy1 = min(H, by1 + _pp2)
                            _fx1 = min(W, bx1 + _pp2)
                            _oc2 = original[_fy0:_fy1, _fx0:_fx1] \
                                .astype(np.float32)
                            _dc2 = donor[_fy0:_fy1, _fx0:_fx1] \
                                .astype(np.float32)
                            _ring2 = np.zeros(_oc2.shape[:2], np.float32)
                            _ring2[(by0 - _fy0):(by1 - _fy0),
                                   (bx0 - _fx0):(bx1 - _fx0)] = \
                                fbm.astype(np.float32)
                            _fill2 = np.zeros(_oc2.shape[:2], np.float32)
                            _fill2[(by0 - _fy0):(by1 - _fy0),
                                   (bx0 - _fx0):(bx1 - _fx0)] = \
                                pch_p.astype(np.float32)
                            _kb = cv2.GaussianBlur(_ring2, (0, 0), 13.0)
                            _kn = cv2.GaussianBlur(_fill2, (0, 0), 13.0)
                            _num = np.zeros_like(_oc2)
                            for _c3 in range(3):
                                _num[:, :, _c3] = cv2.GaussianBlur(
                                    _oc2[:, :, _c3] * _ring2, (0, 0), 13.0)
                            _den = np.maximum(_kb, 1e-3)[..., None]
                            _bgf = _num / _den
                            _fnum = np.zeros_like(_oc2)
                            for _c3 in range(3):
                                _fnum[:, :, _c3] = cv2.GaussianBlur(
                                    _dc2[:, :, _c3] * _fill2, (0, 0), 13.0)
                            _flf = _fnum / np.maximum(_kn, 1e-3)[..., None]
                            _ratio = _bgf / np.maximum(_flf, 30.0)
                            _ratio = np.clip(_ratio, 0.70, 1.45)
                            _mis = (np.abs(_ratio - 1.0).max(axis=2)
                                    > 0.10)
                            _mis &= (_fill2 > 0)
                            if int(_mis.sum()) >= 25:
                                _newv = np.clip(
                                    np.rint(_dc2 * _ratio), 0,
                                    255).astype(np.uint8)
                                _msk = np.zeros(_oc2.shape[:2], bool)
                                _msk[(by0 - _fy0):(by1 - _fy0),
                                     (bx0 - _fx0):(bx1 - _fx0)] = pch_p
                                _use = _msk & _mis
                                _wmf = _use.astype(np.float32)
                                _wmf = cv2.GaussianBlur(_wmf, (0, 0), 2.0)
                                _wmf = np.minimum(_wmf * 1.6, 1.0)
                                _wmf *= zm[_fy0:_fy1,
                                           _fx0:_fx1].astype(np.float32)
                                _subf = donor[_fy0:_fy1,
                                              _fx0:_fx1].astype(np.float32)
                                donor[_fy0:_fy1, _fx0:_fx1] = np.clip(
                                    _subf * (1.0 - _wmf[..., None])
                                    + _newv.astype(np.float32)
                                    * _wmf[..., None],
                                    0, 255).astype(np.uint8)
                                n_fix += 1
                                n_px += int(_use.sum())
                            continue
                        except Exception:
                            continue
                    if plane is None:
                        repl[pch_p] = np.clip(
                            np.rint(tgt), 0, 255).astype(np.uint8)
                    else:
                        _py, _px = np.nonzero(pch_p)
                        _A2 = np.stack(
                            [np.ones(_px.size, np.float32),
                             (_px + bx0 - x0).astype(np.float32),
                             (_py + by0 - y0).astype(np.float32)],
                            axis=1)
                        repl[pch_p] = np.clip(
                            np.rint(_A2 @ plane), 0, 255).astype(np.uint8)
# فدرِ نرمِ مرز — فقط داخلِ نوارِ متن
                    _wm = pch_p.astype(np.float32)
                    _wm = cv2.GaussianBlur(_wm, (0, 0), 2.0)
                    _wm = np.minimum(_wm * 1.6, 1.0)
                    _wm *= zm[by0:by1, bx0:bx1].astype(np.float32)
                    _sub = donor[by0:by1, bx0:bx1].astype(np.float32)
                    donor[by0:by1, bx0:bx1] = np.clip(
                        _sub * (1.0 - _wm[..., None])
                        + repl.astype(np.float32) * _wm[..., None],
                        0, 255).astype(np.uint8)
                    n_fix += 1
                    n_px += int(pch_b.sum())
                except Exception:
                    continue
            if n_fix and verbose:
                try:
                    print(f"  [✓QC] QCِ هماهنگیِ پر: {n_fix} قطعه "
                          f"دوباره رنگ شد ({n_px}px)", flush=True)
                except Exception:
                    pass
            return n_fix
        except Exception:
            return 0

    def _compose_two_image(self, donor: np.ndarray, original: np.ndarray,

                           mask: np.ndarray,
                           verbose: bool = True,
                           refill: bool = False,
                           extra: Optional[np.ndarray] = None) -> np.ndarray:
# نقشهٔ «چه چیزی واقعاً منتقل شد» برایِ گاردهایِ
# پساکامپوز (وارسیِ نهایی/جارویِ بازمانده): هیچ ترمیمی بعد از
# کامپوز حقِ نوشتن بیرونِ این مجموعه را ندارد — قراردادِ
# دو-عکسی: «بیرونِ نوارِ متن = پیکسلِ اورجینال، همیشه». خطایِ
# کاربر (۱۰۱۸/sexyverse): tier6ِ «پرِ سفیدِ ناب» و جارویِ
# بازماندهٔ تیره بیرونِ نوار می‌نوشتند → خطِ حباب/نوارِ هدر/قابِ
# پنل سفید می‌شد = «کلِ حباب پاکیده».
        self._compose_final_cmp = None
        try:
            _ddz = os.environ.get("MANGA_DUMP_DONOR", "")
            if _ddz:
                cv2.imwrite(_ddz, donor)
                print(f"  [*] donor dumped -> {_ddz}")
        except Exception:
            pass
        """ترکیبِ «دو عکس» — عینِ ایدهٔ خودِ کاربر:
        «عکسِ اول متن‌هاش کامل بپاکه؛ اشکال نداره حباب خراب شه یا بیشتر پاک
        شه. بعد این ک کامل پاکیده شده به اندازهٔ همون متن خط به خط برش
        بخوره، به عکسِ دوم بچسونه جایِ متن‌هایِ اصلی‌شون. عکسِ دوم باید
        خروجی بشه.»

        یعنی: خروجی از رویِ «عکسِ اصلی» ساخته می‌شود و فقط پیکسل‌هایِ
        «نوارِ متن» — همان ماسکی که واقعاً متن بود — از عکسِ پاک‌شده
        (عکسِ اول) برش می‌خورند و روی عکسِ اصلی می‌نشینند. هرچیزِ بیرونِ
        ماسک — دیوارِ حباب، فضایِ بینِ خط‌ها، هنرِ اطراف — پیکسل‌به‌پیکسل
        از عکسِ اصلی برمی‌گردد؛ اگر پاک‌کننده‌ای (LaMa/گارد/سویپ) حباب را
        بلعیده باشد، آن خرابی «هرگز» به خروجی نمی‌رسد."""
        try:
            if donor is None or original is None or mask is None:
                return donor
            if donor.shape[:2] != original.shape[:2]:
                return donor
# QCِ هماهنگیِ رنگِ پر (همهٔ پرکنندهها، مرزآگاه)
# درست قبلِ کامپوز: خاکستری-روی-سفید/بنفش، سفید-روی-آسمان
# و پرِ یکرنگِ رو-مرزِ حباب اینجا اصلاح میشوند — بیرونِ نوار
# نمینویسد و حلقهٔ شلوغ (هنر) را دستنخورده میگذارد.
            if os.environ.get("MANGA_NO_HQC", "0") != "1":
                try:
                    self._fill_harmony_qc(donor, original, mask,
                                          verbose=verbose or self.debug)
                except Exception:
                    pass
            _cmp = cv2.dilate(mask, self._compose_kernel9()) > 0
# دیوارِ حباب/قوس/کادرِ پنل (نقشهٔ ساختاریِ محافظت)
# هرگز از عکسِ پاک‌شده به خروجی نمی‌رود — حتی اگر لبهٔ نوارِ متن
# به آن چسبیده باشد. این «قوسِ ناپدیدشده» را ریشه‌کن می‌کند.
# استثنا: گلیفِ تنهاِ جاافتاده (Wِ WICKED) که
# نقشهٔ حفاظت آن را «قاب» خوانده — اجزایِ کوچکِ هم‌اندازهٔ
# حرفِ محافظت‌شده که کاملاً داخلِ نوارِ متن‌اند = بقایایِ
# حرف‌اند → مثلِ بقیهٔ نوار منتقل می‌شوند. قاب/خطِ کشیده
# محافظت می‌ماند.
            try:
                _ppC = getattr(self, "_page_protect", None)
                if _ppC is not None and _ppC.shape == _cmp.shape:
                    _excl = (_ppC > 0) & _cmp
                    if int(_excl.sum()) > 0:
                        _nE, _lE, _sE, _ = \
                            cv2.connectedComponentsWithStats(
                                _excl.astype(np.uint8), 8)
                        _keep = np.zeros_like(_cmp)
                        for _jE in range(1, _nE):
                            _aE = int(_sE[_jE, cv2.CC_STAT_AREA])
                            _wE = int(_sE[_jE, cv2.CC_STAT_WIDTH])
                            _hE = int(_sE[_jE, cv2.CC_STAT_HEIGHT])
                            if _aE <= 1200 and max(_wE, _hE) <= 90:
                                _keep |= (_lE == _jE)
                        _cmp &= ~((_ppC > 0) & (~_keep))
                    else:
                        _cmp &= (_ppC == 0)
            except Exception:
                pass
# دیوارِ ریز (حباب‌هایِ کوچک — YEP!/OH BOY که دیوارشان
# <۶۰px است و از نقشهٔ protect بزرگ جا می‌ماند) هم هرگز از عکسِ
# پاک‌شده منتقل نمی‌شود → حباب‌هایِ کوچک هم سالم می‌مانند.
            try:
                _wbC = getattr(self, "_page_wall_band", None)
                if _wbC is not None and _wbC.shape == _cmp.shape:
                    _cmp &= (_wbC == 0)
            except Exception:
                pass
# قابِ رنگی (نقشهٔ جدا) هم هرگز از donor
# منتقل نمیشود — در ماسکِ فعال پر شده و در خروجی اورجینالش
# میماند (حبابِ سبزِ up0822)
# استثنا: پیکسلهایِ «روکشِ حاشیه‌نویسی» خودشان
# رنگیاند و از قابِ رنگی جدا شدهاند (حلقهٔ خنثی + هالِ
# پالی) — آنها باید منتقل شوند تا لگهٔ رنگی در خروجی نماند.
            try:
                _pcC = getattr(self, "_page_colored_protect", None)
                if _pcC is not None and _pcC.shape == _cmp.shape:
                    _anC = getattr(self,
                                      "_page_annotation_overlay", None)
                    if _anC is not None \
                            and _anC.shape == _cmp.shape:
                        _cmp &= ((_pcC == 0) | (_anC > 0))
                    else:
                        _cmp &= (_pcC == 0)
            except Exception:
                pass
# جاهای پاک‌شدهٔ جاروهایِ پساکامپوز (متنِ جامانده/خرده‌گلیف):
# آنها هم «منتقل‌شده» حساب میشوند و از قفلِ دیوار/protect
# معافند — جارو خودش مراقبِ دیوار بوده؛ قفل، متنِ جامانده را
# زنده نگه میداشت (خلافِ قانونِ «هیچ متنی نمیماند»).
            try:
                if extra is not None and extra.shape == _cmp.shape \
                        and int(cv2.countNonZero(extra)) > 0:
                    _cmp = _cmp | (extra > 0)
            except Exception:
                pass
            try:
                _dc2 = os.environ.get("MANGA_DUMP_CMP2", "")
                if _dc2:
                    cv2.imwrite(_dc2, (_cmp.astype(np.uint8)) * 255)
                    for _fbX in (getattr(self, "_lama_force_rect_boxes",
                                         None) or []):
                        print(f"  [DBG-force] box={list(_fbX)}")
            except Exception:
                pass
            if not _cmp.any():
                self._compose_final_cmp = np.zeros_like(_cmp)
                return np.ascontiguousarray(original)
# بازپرِ بافت (آزمایشی): روی زمینهٔ برف‌نوی/نقش‌ونگار
# پرِ LaMa «تختِ بی‌بافت» است → نواری که حلقه‌اش بافت‌مند است
# با low-freqِ میان‌یابی‌شده + نویزِ واقعی بازپر می‌شود.
# پیش‌فرضِ «خاموش»: در تستِ A/B، نسخهٔ بدونِ
# بازپر برنده بود (ماسکِ پالی‌باندیِ خودش پرِ
# لایما را آن‌قدر تنگ کرده که بازپرِ نویزِ مصنوعی نوار
# می‌سازد). فقط با MANGA_TEXTURE_REFILL=1 فعال شود.
            if refill and os.environ.get("MANGA_TEXTURE_REFILL", "0") == "1":
                self._texture_refill_donor(donor, original, _cmp)
# زباله‌روبی قبل از تخصیصِ خروجیِ تمام‌قد: رویِ
# نوارهایِ بلندِ وبتون (۹۰۰×۱۶۰۰۰) RSSِ انباشتهٔ پایپ‌لاین به
# مرزِ OOM می‌رسد؛ هر MB آزادشده اینجا کمکه (فقط semantics
# reference-counting — بدونِ تغییرِ داده)
            try:
                import gc as _gc
                _gc.collect()
            except Exception:
                pass
            self._compose_final_cmp = _cmp.copy()
            _out = np.ascontiguousarray(
                np.where(_cmp[..., None], donor, original))
# روکشِ حاشیه‌نویسی: نواحیِ «سفیدِ تختِ واقعی»
# (جعبهٔ حاشیه‌نویسیِ سفید — گواهِ شکاف) با سفیدِ همان جعبه
# تخت پر میشوند؛ سبز/شستشو/قاب کاملاً محو میشود. LaMa رویِ
# ناحیهٔ شسته‌شده خودش شستشو را زمینه میپندارد و سبز میسازد.
# (MANGA_ANNOT_FLAT=0 خاموش — برایِ مقایسهٔ A/B)
            try:
                _anF = getattr(self, "_page_annotation_fill", None)
                _anFl = getattr(self, "_page_annotation_flat", None)
                if os.environ.get("MANGA_ANNOT_FLAT", "1") != "0" \
                        and _anF is not None \
                        and _anFl is not None \
                        and _anF.shape[:2] == _out.shape[:2] \
                        and _anFl.shape == _cmp.shape:
                    _sel = (_anFl > 0) & _cmp
                    if bool(_sel.any()):
                        _out[_sel] = _anF[_sel]
            except Exception:
                pass
# ضدِ «باندِ سفید» در کامپوز (فقط اندروید —
# MANGA_STRIP_HARM): donorِ LaMa رویِ زمینهٔ گرادیانی/کرم
# گاهی «روشنتر/سفیدتر» از زمینهٔ اطراف برمیگردد و کامپوزِ
# فقط-نوار همان پیکسلهایِ سفید را میبرد (لاگِ گوشیِ
# نوارهایِ سفیدِ #19/#20 رویِ دیوارِ کرمِ
# 700×11362 = «لگه»).
# همسازِ «خط‌به‌خط» (بازنویسیِ همسازِ ردیفی):
# نوارهایِ خطِ چسبیده در بلوکِ متراکم در باندِ ردیفیِ مشترک
# ادغام میشوند و لنگرِ قائمِ آزاد پیدا نمیکنند → حالا برای
# هر «خطِ» هر ناحیه (همان گروه‌بندیِ خطِ نوارهایِ کامپوز)
# هدفِ هر ردیف = میانهٔ پیکسلهایِ «آزادِ همان ردیف» (شکافِ
# بینِ کلمات + حاشیهٔ خط) از عکسِ اورجینال گرفته میشود —
# لنگرِ افقی، مستقل ازِ گپِ بینِ خطها؛ گرادیانِ قائم هم
# چون هر ردیف هدفِ خودش را دارد حفظ میشود. گاردها: باندِ
# غیرتخت (std>15) / ردیفِ بدونِ نمونهٔ آزاد / هدفِ ناهوار
# (هنر) / دلتایِ ناچیز (<15) یا افراطی (>60) → دست نخوردن.
# پیشفرضِ روشن رویِ PC هم (گیتِ _gate_default_on):
# درزها/دال‌هایِ تختِ LaMa رویِ گرادیانِ آسمانِ وبتونها
# (img4/4e2e77 — ) دیگر فقط
# اندروید نیست؛ همسازِ ردیفیِ خط، نوار را با زمینهٔ اورجینالِ
# همان ردیف تراز میکند (گاردها: std/هدفِ ناهوار/دلتا ۱۵-۶۰).
            if _gate_default_on("MANGA_STRIP_HARM"):
                try:
                    _hH, _wH = _cmp.shape
                    _orgH = original.astype(np.float32)
                    _outH = _out.astype(np.float32)
                    _nfixH = 0
                    for _rgH in (getattr(self, "_page_regions",
                                         None) or []):
                        _plH = getattr(_rgH, "ocr_polys", None) or []
                        if not _plH:
                            continue
                        try:
                            _lnsH = MangaTranslator._group_polys_to_lines(
                                list(_plH))
                        except Exception:
                            continue
                        for (lx0, ly0, lx1, ly1) in (_lnsH or []):
                            _yA = max(0, int(ly0) - 1)
                            _yZ = min(_hH, int(ly1) + 2)
# ±۱۸px بیرونِ باکسِ خط = نمونهٔ زمینهٔ
# اطرافِ خط (گپِ کلمه + حاشیهٔ دو سر) —
# پالیِ OCR تاِ لبهٔ متن است و بدونِ
# این بسط، ستونِ آزادِ کافی وجود ندارد
                            _xA = max(0, int(lx0) - 18)
                            _xZ = min(_wH, int(lx1) + 19)
                            _bh = _yZ - _yA
                            if _bh < 12 or _bh > 220 or \
                                    _xZ - _xA < 40:
                                continue
                            _mB = _cmp[_yA:_yZ, _xA:_xZ]
                            if int(_mB.sum()) < 400:
                                continue
                            _sub = _outH[_yA:_yZ, _xA:_xZ]
                            _orgB = _orgH[_yA:_yZ, _xA:_xZ]
                            _mBc = _mB
                            _src = _sub[_mBc]
                            if _src.size < 400 or \
                                    float(_src.std()) > 15.0:
                                continue
                            _medS = np.median(
                                _src.reshape(-1, 3), axis=0)
# هدفِ هر ردیف از ستونهایِ آزادِ همان ردیف —
# «آزاد» بر اساسِ ماسکِ بدونِ دیلیت است (گپِ
# ۸-۱۴px کلمهها بعد از دیلیتِ 4px بسته
# میشود)؛ نمونهها = شکافِ بینِ کلمات +
# ردیفهایِ بالایِ سریف/پایینِ دم — همه
# زمینهٔ اورجینال
                            _mrawH = mask[_yA:_yZ, _xA:_xZ] > 0
                            _tgt = np.zeros((_bh, 3), np.float32)
                            _have = np.zeros(_bh, bool)
                            for _ri in range(_bh):
                                _free = ~_mrawH[_ri]
                                _nf = int(_free.sum())
                                if _nf < 12:
                                    continue
# گاردِ ناهمگنیِ درون‌ردیف:
# ردیفِ آزاد رویِ هنرِ شلوغ (یقه/کراوات/
# خطِ سیاه + پنل + متنِ جامانده — r4886ِ
# 9.jpg) میانهٔ «مخلوط» میدهد؛ همسازِ
# ردیفی نوارِ سالمِ donor را به آن تراز
# میکرد = «باندِ خاکستریِ افقی». ردیفی که
# پیکسلهایِ آزادش یکدست نیستند (std>۱۸)
# هدفِ معتبر ندارد؛ اگر اکثریتِ ردیفها
# معتبر نباشند کلِ خط دستنخورده میماند
# (گرادیانِ نرمِ آسمانِ img4/4e2e77 هر
# ردیفش یکدست است → همساز همچنان کار
# میکند).
                                try:
                                    _rf = _orgB[_ri][_free]
                                    if float(np.max(np.std(
                                            _rf, axis=0))) > 18.0:
                                        continue
                                except Exception:
                                    pass
                                _tgt[_ri] = np.median(
                                    _orgB[_ri][_free], axis=0)
                                _have[_ri] = True
                            if int(_have.sum()) < max(
                                    4, int(0.3 * _bh)):
                                continue
# پرکردنِ ردیفهایِ نمونه‌نداشته + اسموث
                            _idxH = np.nonzero(_have)[0]
                            for _ri in range(_bh):
                                if _have[_ri]:
                                    continue
                                _j = int(np.searchsorted(
                                    _idxH, _ri))
                                if _j == 0:
                                    _tgt[_ri] = _tgt[_idxH[0]]
                                elif _j >= _idxH.size:
                                    _tgt[_ri] = _tgt[_idxH[-1]]
                                else:
                                    _ya2, _yb2 = int(_idxH[_j - 1]), \
                                        int(_idxH[_j])
                                    _t2 = float(_ri - _ya2) / \
                                        float(_yb2 - _ya2)
                                    _tgt[_ri] = _tgt[_ya2] * \
                                        (1.0 - _t2) + _tgt[_yb2] * _t2
                            if _bh >= 5:
                                _kH = np.ones(5, np.float32) / 5.0
                                for _c2 in range(3):
                                    _tgt[:, _c2] = np.convolve(
                                        _tgt[:, _c2], _kH,
                                        mode='same')
                            if float(_tgt.std()) > 24.0:
                                continue  # هدفِ ناهوار = هنر
# سازگاریِ قائم: هدفِ افقی باید با زمینهٔ
# قائمِ همان ستونها همخوان باشد — وگرنه
# خط رویِ مرزِ هنر است (نوارِ تیرهٔ
# بالا/پایین) و لنگرِ افقی به آن اعمال
# نمیشود. میانه در برابرِ گلیفِ خطِ
# مجاورِ ناخوانده مقاوم است.
                            _vtA = max(0, _yA - 9)
                            _vtB = max(0, _yA - 3)
                            _vbA = min(_hH, _yZ + 4)
                            _vbB = min(_hH, _yZ + 10)
                            _vok = []
                            if _vtB > _vtA:
                                _vok.append(np.median(
                                    _orgH[_vtA:_vtB, _xA:_xZ]
                                    .reshape(-1, 3), axis=0))
                            if _vbB > _vbA:
                                _vok.append(np.median(
                                    _orgH[_vbA:_vbB, _xA:_xZ]
                                    .reshape(-1, 3), axis=0))
                            if not _vok:
                                continue
                            _vmid = np.median(
                                np.stack(_vok, axis=0), axis=0)
                            if float(np.abs(
                                    np.median(_tgt, axis=0) -
                                    _vmid).max()) > 30.0:
                                continue
                            _dlt = float(np.abs(
                                _medS - np.median(
                                    _tgt, axis=0)).max())
                            if _dlt < 15.0 or _dlt > 60.0:
                                continue
                            _dRow = np.clip(
                                _tgt[:, None, :] - _medS[None, None],
                                -34.0, 34.0)
                            _wgt = cv2.GaussianBlur(
                                (_mBc.astype(np.uint8)) * 255,
                                (0, 0), 2.0).astype(
                                    np.float32) / 255.0
                            _sub += _dRow * _wgt[..., None]
                            _outH[_yA:_yZ, _xA:_xZ] = _sub
                            _nfixH += 1
                    if _nfixH:
                        _out = np.clip(
                            _outH, 0, 255).astype(np.uint8)
                        if verbose:
                            print(f"  [✓]همسازِ نوار: {_nfixH} "
                                  f"خطِ ناهمرنگ اصلاح شد")
                except Exception:
                    pass
            try:
                if verbose:
                    print(f"  [*] دو-عکسی: خروجی = عکسِ اصلی + "
                          f"{int(_cmp.sum())}px نوارِ متنِ پاک‌شده")
# انتقالِ «همین لحظه، همین تصویر»: هر عکس بلافاصله
# بعد از پاک‌شدنش کامپوز می‌شود (نه اینکه همه در آخر بیایند) —
# درخواستِ کاربر: «دفعه اول هر عکس جدا انتقال بده».
                    print(f"  [*]انتقالِ فوریِ همین صفحه — "
                          f"عکسِ دوم = خروجیِ نهایی")
            except Exception:
                pass
            return _out
        except Exception:
            return donor

    def _fill_system_box_interiors(self, image: np.ndarray,
                                   regions: List[TextRegion],
                                   mask: np.ndarray,
                                   cleaned: np.ndarray) -> int:
        """ — پرِ فلتِ «قطعیِ» اینتریورِ بالنِ سیستم (باکسِ سفید).

        درخواستِ کاربر: «حبابِ سیستم متن‌هاش جدا حساب شه (رندر)، ولی
        پاکسازیش: متن‌های نزدیک با هم پاک بشه — فقط سیستم اینجور باشه».

        پیاده‌سازی: کلِ اینتریورِ سفیدِ باکس (خط‌ها + فاصلهٔ بینِ خط‌ها)
        «یک واحد» با رنگِ خودِ اینتریور فلت پر می‌شود — بدونِ LaMa.
        چرا بدونِ LaMa؟ ماسکِ کلِ اینتریور، گاردِ ضدتوهمِ LaMa (که به
        «حلقهٔ روشنِ دورِ ماسک» تکیه دارد) را کور می‌کند: حلقهٔ دورِ
        اینتریور = قابِ سیاهِ باکس → خروجیِ تیرهٔ توهمیِ LaMa بدونِ
        اعتبارسنجی می‌ماند (لگهٔ سیاهِ باکس — بازتولیدشده در تست).
        پرِ فلتِ قطعی = صفرِ ریسک؛ قاب/سایه بیرونِ اینتریور محفوظ
        (اینتریور با erode از قاب فاصله می‌گیرد)؛ اینتریور از ماسکِ
        LaMa هم کِیل می‌شود تا هیچ پرکننده‌ای رویش نرود. پنجرهٔ سیستمِ
        تیره/تصویردار (گیت‌های _system_box_interior) مثلِ قبل خط‌به‌خط
        پاک می‌شود — فقط باکسِ سفیدِ سیستم این‌گونه است."""
        n_done = 0
        try:
            _groups: Dict[tuple, list] = {}
            for _rgs in regions:
                _cov = getattr(_rgs, "cover_rect", None)
                if _cov is None or not getattr(_rgs, "sys_split", False):
                    continue
                try:
                    _rx, _ry, _rw, _rh = [int(v) for v in _rgs.rect]
                except Exception:
                    continue
                _key = tuple(int(v) for v in _cov[:4])
                _groups.setdefault(_key, []).append(
                    (_rx, _ry, _rx + _rw, _ry + _rh))
            if not _groups:
                return 0
            for _key, _seeds in _groups.items():
                if len(_seeds) < 2:
                    continue  # باکسِ تک‌خطی: مستطیلِ خودش کافی است
                _intr = MangaTranslator._system_box_interior(
                    image, _key, _seeds)
                if _intr is not None:
# گیتِ «اکثریتِ سفید»: اینتریورِ عکس‌دار/متنیِ سنگین
# فلت نشود (رفتارِ خط‌به‌خطِ قبلی محفوظ)
                    try:
                        _g = cv2.cvtColor(
                            image, cv2.COLOR_BGR2GRAY)
                        _px = _g[_intr]
                        if float((_px >= 180).mean()) < 0.45:
                            _intr = None
                    except Exception:
                        _intr = None
                if _intr is None or _intr.shape != mask.shape[:2]:
                    continue
# ۲px فاصلهٔ بیشتر از قاب برایِ خودِ پر
                _intr_w = cv2.erode(
                    _intr.astype(np.uint8),
                    np.ones((5, 5), np.uint8)) > 0
                if int(_intr_w.sum()) < 200:
                    continue
# رنگِ پر = میانهٔ پیکسل‌هایِ «سفیدِ» اینتریور (مصون از
# آلودگیِ خودِ حروفِ تیره)
                try:
                    _gb = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                    _wsel = _intr_w & (_gb >= 180)
                    if int(_wsel.sum()) >= 100:
                        _fill = np.median(
                            image[_wsel].astype(np.float32), axis=0)
                    else:
                        _fill = np.median(
                            image[_intr_w].astype(np.float32), axis=0)
                except Exception:
                    continue
                cleaned[_intr_w] = np.clip(_fill, 0, 255).astype(np.uint8)
# اینتریور از ماسکِ LaMa/پرکننده‌ها کِیل شود — پرِ فلت
# «قطعی» است و هیچ پرکنندهٔ دیگری نباید رویش برود
                mask[_intr] = 0
                n_done += 1
                if self.debug:
                    try:
                        print(f"  [*]بالنِ سیستم → پرِ فلتِ یکجایِ "
                              f"اینتریور ({int(_intr_w.sum())}px, "
                              f"رنگ={tuple(int(v) for v in _fill)})")
                    except Exception:
                        pass
            return n_done
        except Exception:
            return n_done

    def _clean_label(self) -> str:
# نامِ کوتاهِ روشِ پاکسازی برای لاگ
        return {"lama-manga": "lama.onnx", "lama-big": "big-lama"}.get(
            str(getattr(self, "clean_method", "") or "").lower(), "opencv")

    @staticmethod
    def _absorb_text_halo(bgr: np.ndarray, mask: np.ndarray,
                          band: int = 17, s_min: int = 55) -> np.ndarray:
        """ — هالهٔ گلوِ اشباعِ گرمِ دورِ متن (قرمز/نارنجی/زرد/
        سرخابی — مثلِ کارتِ «Crimson Dragon») جزوِ جوهرِ متن حساب می‌شود.
        پیکسل‌هایِ پُراشباعِ گرمِ «چسبیده به ماسک» (تا band پیکسل) به ماسک
        اضافه می‌شوند تا هر مسیرِ پاکسازی آن‌ها را هم ببرد — وگرنه هاله
        زنده می‌ماند و «لکهٔ قرمز» دیده می‌شود (POCO F4). فقط توده‌های
        چسبیده به ماسک؛ تراشهٔ پراکنده و هنرِ دور دست‌نخورده می‌ماند.
        درخواستِ صریحِ کاربر: «اشکال نداره بیشتر پاک شه».
         — گوشیِ POCO F4 هنوز لکه داشت: دنبالهٔ کم‌رنگِ هاله
        (S<80) و فراتر از ۱۳پیکسل زنده می‌ماند → band ۱۷، s_min ۵۵،
        و گشادش‌کردنِ نهاییِ هالهٔ جذب‌شده با ۷px تا مرزِ ماسک روی
        «زمینهٔ پاک» بفتد نه دنبالهٔ هاله (فیلِ بعدی قرمز نمی‌گیرد)."""
        try:
            if bgr is None or mask is None:
                return mask
            if bgr.shape[:2] != mask.shape[:2] or not mask.size:
                return mask
            m0 = (mask > 0)
            if not m0.any():
                return mask
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            hh, ss = hsv[..., 0], hsv[..., 1]
            warm = (((hh <= 40) | (hh >= 150)) & (ss >= int(s_min)))
            k = 2 * int(band) + 1
            ring = (cv2.dilate(m0.astype(np.uint8),
                               np.ones((k, k), np.uint8)) > 0) & (~m0)
            halo = (warm & ring).astype(np.uint8)
            if int(halo.sum()) < 40:
                return mask
            n, lab, stats, _ = cv2.connectedComponentsWithStats(halo, 8)
            keep = np.zeros_like(halo)
# «هالهِ واقعی در برابر زمینهِ هنری»:
# هالهِ حقیقی نارین نازکی است که چند پیکسل بعد از لبهِ حروف
# تمام می‌شود. اگر تودهِ گرمِ هم‌ماهِ یک مؤلفهٌ خیلی
# بیرونِ حلقه (تا 3×band) ادامه داشته باشد = خودِ
# زمینهِ قرمز/گرمِ کارت است، نه هالهِ حروف → هرگز
# جذب نشود (خطای کارت img2: +107هزارpx هنر جذب ماسک
# شد و کل کارت با رنگ پر شد).
            try:
                _warmfree = (warm & (~m0)).astype(np.uint8)
                _nw, _lw = cv2.connectedComponents(_warmfree, 8)
                if _nw > 1:
                    _k = 2 * int(band) * 3 + 1
                    _out = (cv2.dilate(
                        m0.astype(np.uint8),
                        np.ones((_k, _k), np.uint8)) > 0)
                    _far = (warm & (~_out) & (~m0))
                    _tot2 = np.bincount(
                        _lw[_warmfree > 0].ravel(), minlength=_nw)
                    _farc = np.bincount(
                        _lw[_far].ravel(), minlength=_nw)
                else:
                    _lw = None
            except Exception:
                _lw = None
            hgt, wdt = halo.shape
            for i in range(1, n):
                if stats[i, cv2.CC_STAT_AREA] < 12:
                    continue
                if _lw is not None:
                    try:
                        _wid = int(np.bincount(
                            _lw[lab == i].ravel(),
                            minlength=_nw).argmax())
                        if _wid != 0:
                            _tot = int(_tot2[_wid])
                            _fr = int(_farc[_wid])
                            if _tot > 0 and _fr > 0.30 * _tot:
                                continue
                    except Exception:
                        pass
                x0 = max(0, int(stats[i, cv2.CC_STAT_LEFT]) - 2)
                y0 = max(0, int(stats[i, cv2.CC_STAT_TOP]) - 2)
                w0 = min(wdt - x0, int(stats[i, cv2.CC_STAT_WIDTH]) + 4)
                h0 = min(hgt - y0, int(stats[i, cv2.CC_STAT_HEIGHT]) + 4)
                if w0 <= 0 or h0 <= 0:
                    continue
                if (lab[y0:y0 + h0, x0:x0 + w0] == i).any() and \
                        m0[y0:y0 + h0, x0:x0 + w0].any():
                    keep[lab == i] = 1
            if not keep.any():
                return mask
            keep = cv2.morphologyEx(keep, cv2.MORPH_CLOSE,
                                    np.ones((5, 5), np.uint8))
# گشادکردنِ ۷px: مرزِ ماسک باید از دنبالهٔ هاله
# رد شود؛ وگرنه پرکنندهٔ گرادیانی رنگِ هاله را داخل می‌کشد
            keep = cv2.dilate(keep, np.ones((7, 7), np.uint8))
            return ((m0 | (keep > 0)).astype(np.uint8)) * 255
        except Exception:
            return mask

    def _sweep_fix_record(self, fix_mask) -> None:
        """ — ثبتِ جاهایی که جاروهایِ پساکامپوز پاک کردهاند —
        کامپوزِ نهایی این جاها را مثلِ نوارِ متن «منتقل‌شده"
        حساب میکند (عکسِ دوم فقط همین‌جا + نوارها عوض میشود)."""
        try:
            if fix_mask is None:
                return
            _m = np.asarray(fix_mask)
            if _m.dtype != bool:
                _m = _m > 0
            _cur = getattr(self, "_sweep_fix_mask", None)
            if _cur is None or _cur.shape != _m.shape:
                self._sweep_fix_mask = _m.copy()
            else:
                self._sweep_fix_mask |= _m
        except Exception:
            pass

    def clean_image(self, image: np.ndarray, regions: List[TextRegion],
                    page_boxes: Optional[List] = None) -> np.ndarray:
# پوستهٔ قفل‌دار: بدنهٔ اصلی در _clean_image_page زیرِ
# قفلِ سریالِ کلاس اجرا میشود تا پاکسازیِ همزمانِ دو صفحهٔ بچ
# (کارگرهایِ فازِ دوم) وضعیتِ صفحه‌محور را قاطی نکند.
# حالتِ تکی تغییری نمی‌بیند (یک صفحه =
# یک قفلِ بی‌رقیب).
        _lk = getattr(MangaTranslator, "_page_clean_lock", None)
        if _lk is None:
            return self._clean_image_page(image, regions, page_boxes)
        with _lk:
            return self._clean_image_page(image, regions, page_boxes)

    def _clean_image_page(self, image: np.ndarray,
                          regions: List[TextRegion],
                          page_boxes: Optional[List] = None) -> np.ndarray:
# باکسهایِ حبابِ «همین صفحه» — از فراخواننده میآید (page_ctx)؛
# اگر نیامد (مسیرهایِ قدیمی/ادامهٔ از کش) از خودِ ناحیهها
# بازسازی میشود. نوشتن اینجا (زیرِ قفلِ سریال) یعنی دیگر هیچ
# کارگرِ استخراجِ موازی وسطِ پاکسازی جعبه‌هایِ صفحهٔ دیگر را
# رویِ این مقدار نمینشاند.
        try:
            if page_boxes:
                self._page_bubble_boxes = list(page_boxes)
            else:
                _rb = []
                for _r0 in (regions or []):
                    try:
                        if str(getattr(_r0, "det_class", "") or "") \
                                in ("bubble", "text_bubble"):
                            _x0, _y0 = int(_r0.rect[0]), int(_r0.rect[1])
                            _rb.append((_x0, _y0,
                                        _x0 + int(_r0.rect[2]),
                                        _y0 + int(_r0.rect[3]),
                                        str(getattr(_r0, "det_class", ""))))
                    except Exception:
                        continue
                self._page_bubble_boxes = _rb
        except Exception:
            self._page_bubble_boxes = []
# نواحیِ صفحه نگه داشته می‌شوند تا «کامپوزِ دو-عکسی»
# بتواند نوارهایِ خط‌به‌خط (اندازهٔ دقیقِ متن) را بسازد.
        self._page_regions = list(regions or [])
# نقشهٔ «جاهای پاک‌شدهٔ» جاروهایِ پساکامپوز — قراردادِ
# دو-عکسی: عکسِ دوم فقط در «نوارهایِ متن + همین جاها»
# پیکسل عوض میکند، هر جایِ دیگر همیشه اورجینال است.
        self._sweep_fix_mask = None
# «متنِ فقط عدد/نماد دست‌نخورده بماند»: ناحیه‌ای که متنِ OCRشدهاش «هیچ حرفی»
# ندارد ('....'، '123124'، ' ,./???!?~') نه ترجمه میشود
# (فیلترِ عدد/نماد در translate_regions) و نه پاکسازی — هنر/عدتِ
# صفحه دست‌نخورده میماند. ناحیهٔ «جوهرِ بی‌متن» (ocr_empty:
# حبابِ واقعی که OCR نخواند) همچنان پاک میشود — متنِ واقعی
# گم نشود.
        _nt = [r for r in (regions or [])
                  if getattr(r, "no_touch", False)]
        if _nt:
            regions = [r for r in (regions or [])
                       if not getattr(r, "no_touch", False)]
            self._page_regions = list(regions)
            try:
                print(f"    [*] {len(_nt)} ناحیهٔ فقط عدد/نماد "
                      f"→ دست‌نخورده (نه ترجمه، نه پاکسازی)")
            except Exception:
                pass
        if not regions:
            return image.copy()
# اندروید: پروفایلرِ سبکِ مرحله‌هایِ پاکسازی — هر
# مرحله چند ثانیه میگیرد را در لاگ نشان میدهد تا کندیِ «پاکسازیِ
# کلی یک کم طول میکشه» دقیق پیدا شود. PC هیچ چیزی چاپ نمیکند.
        _tc = time.time()

        def _stage(tag: str) -> None:
            try:
                if _on_android():
                    print(f"  [⏱] پاکسازی | {tag} | "
                          f"{time.time() - _tc:.1f}s", flush=True)
            except Exception:
                pass

        mask = self._build_text_mask(image, regions)
        if not np.any(mask):
            return image.copy()
        self._mem_trim()  # پیکِ ماسک‌سازی به OS برگردد

# دیوارِ حباب/کادرِ پنل را از ماسکِ فعال جدا کن —
# پرکننده‌ها ماسک را گشاد می‌کنند و دیوار را می‌بلعند
# (بدونِ copy — bitwise_and خروجیِ جدید می‌سازد و raw می‌ماند)
        self._page_raw_text_mask = mask
        try:
            _dm = os.environ.get("MANGA_DUMP_MASK")
            if _dm:
                cv2.imwrite(_dm, mask)
                print(f"  [*] mask dumped → {_dm}")
        except Exception:
            pass
        _protect = self._structural_protect_mask(image, regions)
        self._page_protect = _protect
# نقشهٔ «دیوارِ ریز»: دیوارِ حباب‌هایِ کوچک (<۶۰px —
# مثلِ YEP!) هم مثلِ بزرگ‌ها در کامپوز محافظت می‌شود تا هرگز
# پیکسلِ آن از عکسِ پاک‌شده به خروجی نرود (حبابِ نازک نشکند).
        try:
            self._page_wall_band = self._structural_protect_mask(
                image, regions, min_len=16, near_px=13)
        except Exception:
            self._page_wall_band = None
# پایانِ اعتبارِ کشِ MANGA_PROT_CACHE: هرگز کهنه نمیماند
        self._spm_cache = None
# protect دیگر از ماسکِ «فعال» کم نمیشود: عکسِ اول
# (donor) طبقِ سبکِ خودِ سازنده حقِ «بیشتر پاک کردن» دارد
# («اشکال نداره حباب خراب شه یا بیشتر پاک شه») — چون کامپوزِ
# دو-عکسی (206m) و پولیشِ حلقه، ساختار را هرگز از عکسِ دوم
# منتقل نمیکنند و پولیش هم protect را از نمونهٔ حلقه بیرون
# میگذارد. قبلاً حذفِ protect از ماسک، پرِ LaMa را وادار میکرد
# دورِ قابِ رنگی بچرخد و رنگِ قاب را داخلِ متن میکشید (لکهٔ
# سبزِ حبابهایِ ۳/۴ در up0822).

# هالهٔ گلوِ اشباعِ دورِ متن (لکهٔ قرمزِ کارتِ عنوان)
# قبل از اسنپ‌شاتِ کامپوز و همهٔ مسیرهایِ پاکسازی به ماسک می‌چسبد
# تا نوارِ ترکیبِ دو-عکسی هم هاله را بپوشاند (خروجی = بدونِ لکه).
        try:
            _t = time.time()
            _n2 = int((mask > 0).sum())
            _mask = MangaTranslator._absorb_text_halo(image, mask)
            if _mask is not mask:
                mask = _mask
                if self.debug:
                    print(f"  [+]هالهٔ گلو → ماسک "
                          f"(+{int((mask > 0).sum()) - _n2}px, "
                          f"{time.time() - _t:.2f}s)", flush=True)
        except Exception:
            pass
        _stage("ماسک+هاله")

# ماسکِ کامپوزِ «خط‌به‌خط»: نسخهٔ خامِ ماسکِ متنِ همین
# لحظه (بعدِ کارو/پروتکت، «قبلِ» کِیلِ پرکننده‌هایِ فوری و «قبلِ»
# توپرشدنِ بلوک‌هایِ تیره) برایِ ترکیبِ دو-عکسی نگه داشته می‌شود.
# طبقِ حرفِ تازهٔ کاربر: «به اندازهٔ متنِ اصلی برش بخوره بذاره رو
# عکسِ اصلی — چرا کلِ حباب رو منتقل می‌کنی؟» → کامپوز فقط نوارِ
# متن را می‌گیرد، نه کلِ حباب/محفظه/پیکسل‌هایِ تغییرکردهٔ پراکنده.
        self._compose_text_mask = mask.copy()

# درخواستِ نهاییِ کاربر: «عکسِ اول متن‌هاش کامل بپاکه —
# اشکال نداره حباب خراب شه یا بیشتر پاک شه. بعد خط به خط برش
# بخوره به عکسِ دوم بچسونه جایِ متن‌هایِ اصلی‌شون. عکسِ دوم باید
# خروجی بشه» + «چرا کل حباب انتقال میدی؟ حروف به حروف برش بزنه».
# ماسکِ donor = فقط نوارِ متن + پدِ سخاوتمندانه (+ نجاتِ جوهرِ
# جا‌مانده). «کلِ داخلِ حباب» (/73) حذف شد: LaMa داخلِ
# حبابِ رنگی را خمیرِ خاکستری می‌کرد («لگه») و روی گوشی کند بود.
        try:
            mask = self._expand_donor_text_strips(
                image, mask, regions)
        except Exception:
            pass
# donor دیگر اینتریور ندارد → هیچ ناحیه‌ای از پرکردنِ
# فوری مستثنا نیست (پرِ فلت برای حبابِ تخت، LaMa برای بافت —
# همان مسیرِ همیشگیِ سبکِ پاکسازی).
        _donor_skip = None

# نقشهٔ «ساختارِ روشنِ دور از متن» (خطِ سفیدِ حباب
# قابِ کادر). خطایِ واقعیِ کاربر رویِ img2: «این قسمت حباب به کل
# حذف زده و اون یکی کامل سیاه کرده» — بلوکِ اجباری-LaMa خطِ سفیدِ
# حباب را می‌بلید و LaMa پنلِ تیره را سیاهِ خالص می‌کرد.
# پیکسل‌هایِ روشن (≥۱۵۰) که بیش از ~۳۱px از جوهرِ متن فاصله
# دارند «قفل» می‌شوند: ۱) از ماسکِ توپرِ بلوکِ اجباری خارج‌اند
# ۲) بعد از هر مرحله از عکسِ اصل به cleaned برمی‌گردند.
        self._prot_bright = None
        self._prot_glow = None
        self._prot_all = None
        try:
            _ink = getattr(self, "_compose_text_mask", None)
            if (_ink is not None
                    and _ink.shape == image.shape[:2]
                    and int(cv2.countNonZero(_ink))):
                _g3 = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                _near = cv2.dilate(
                    _ink, np.ones((31, 31), np.uint8)) > 0
                _pb3 = (((_g3 >= 150) & (~_near))
                         .astype(np.uint8)) * 255
                if int(cv2.countNonZero(_pb3)):
                    self._prot_bright = _pb3
                    if self.debug:
                        print(f"  [✓]حفاظتِ ساختارِ روشن — "
                              f"{int(cv2.countNonZero(_pb3))}px قفل شد")
# قفلِ «تابِ نورِ پس‌زمینه»: مؤلفهٔ روشنِ (≥۱۰۰)
# که بخشِ بزرگی‌اش (≥۲۰۰۰px) بیش از ~۱۰۰px از متن فاصله
# دارد = نورِ صحنه/پنل است، نه هالهٔ حروف — نمونه: پرتوِ
# بالایِ پنلِ img2 که پرکنندهٔ هاله سیاهش می‌کرد.
# قرمزِ اشباع (خاکستریِ ~۷۶) عمداً زیرِ آستانه می‌ماند تا
# لکهٔ قرمزِ کارتِ عنوان طبقِ /67 پاک شود.
                try:
                    _b = (_g3 >= 100).astype(np.uint8)
                    _d = cv2.distanceTransform(
                        (cv2.dilate(_ink,
                                    np.ones((5, 5), np.uint8)) == 0)
                        .astype(np.uint8), cv2.DIST_L2, 3)
                    _far = (_d > 100.0) & (_b > 0)
                    if int(_far.sum()) >= 2000:
                        _cnt, _lbl = cv2.connectedComponents(
                            _b, connectivity=8)
                        _fcnt = np.bincount(
                            _lbl[_far].ravel(), minlength=_cnt)
                        _fids = np.unique(_lbl[_far])
                        _fids = _fids[_fids != 0]
                        _keep = [int(i) for i in _fids if _fcnt[i] >= 2000]
                        if _keep:
                            _lut = np.zeros(_cnt, dtype=np.uint8)
                            _lut[_keep] = 255
                            _pg = _lut[_lbl]
                            _pg &= cv2.dilate(
                                _ink, np.ones((5, 5), np.uint8)) == 0
                            _pg = (_pg > 0).astype(np.uint8) * 255
                            if int(cv2.countNonZero(_pg)):
                                self._prot_glow = _pg
                                if self.debug:
                                    print(f"  [✓]قفلِ تابِ نور — "
                                          f"{int(cv2.countNonZero(_pg))}px "
                                          f"({len(_keep)} مؤلفه)")
                except Exception:
                    self._prot_glow = None
# قفل‌ها از ماسکِ پاکسازی خارج می‌شوند (LaMa/پرکننده‌ها
# حقِ بازنویسی‌شان را ندارند)
                try:
                    _pa = None
                    if self._prot_bright is not None:
                        _pa = self._prot_bright.copy()
                    if self._prot_glow is not None:
                        _pa = (self._prot_glow.copy() if _pa is None
                                 else _pa | self._prot_glow)
                    if _pa is not None and int(cv2.countNonZero(_pa)):
                        mask[_pa > 0] = 0
                        self._prot_all = _pa
# قفلِ خطِ سراسری (کادرِ پنل) هم در
# _prot_all: ترمیمها/جارو/چسباندنِ LaMa حقِ بازنویسی
# قاب را ندارند
                    try:
                        _pgp = getattr(self, "_page_protect", None)
                        if _pgp is not None \
                                and _pgp.shape == mask.shape[:2] \
                                and int(cv2.countNonZero(_pgp)):
                            mask[_pgp > 0] = 0
                            if self._prot_all is None:
                                self._prot_all = _pgp.copy()
                            else:
                                self._prot_all = cv2.bitwise_or(
                                    self._prot_all, _pgp)
                    except Exception:
                        pass
                except Exception:
                    pass
# پروبِ وضعیتِ قفلِ پیکسل
                try:
                    _pv2 = os.environ.get("MANGA_PROBE", "")
                    if _pv2 and "," in _pv2:
                        _qx, _qy = [int(v) for v in _pv2.split(",")]
                        _inb = bool(self._prot_bright is not None
                                    and self._prot_bright[_qy, _qx] > 0)
                        _ing = bool(self._prot_glow is not None
                                    and self._prot_glow[_qy, _qx] > 0)
                        _inm = bool(mask[_qy, _qx] > 0)
                        print(f"  [🔍PROBE] ({_qx},{_qy}) "
                              f"gray={int(_g3[_qy, _qx])} "
                              f"prot_bright={_inb} prot_glow={_ing} "
                              f"in_mask_after_sub={_inm}", flush=True)
                except Exception:
                    pass
        except Exception:
            self._prot_bright = None
            self._prot_glow = None
        _stage("قفلها")
        try:
            _pvp = os.environ.get("MANGA_PROBE", "")
            if _pvp and "," in _pvp:
                _qxp, _qyp = [int(v) for v in _pvp.split(",")]
                print(f"  [🔍PROBE] after_prot_build="
                      f"({cleaned[_qyp, _qxp]})", flush=True)
        except Exception:
            pass
# قفلِ ساختارِ روشنِ نازک (قابِ تزئینی/نوارِ لبه) که
# باکسِ بلوکِ اجباری از رویش عبور می‌کند — قبل از توپرشدنِ ماسک
# وگرنه LaMa قاب را له می‌کند (GREEN MOON). در `_prot_all`
# ادغام می‌شود تا همهٔ مسیرها (پرکنندهٔ فوری، LaMa، paste) آن را
# محترم بشمارند.
        try:
            _fbs2 = (getattr(self, "_lama_force_rect_boxes", None) or [])
            if _fbs2:
                _slk = self._rect_structure_lock(image, _fbs2)
                if _slk is not None and int(cv2.countNonZero(_slk)):
                    if getattr(self, "_prot_all", None) is None:
                        self._prot_all = _slk
                    else:
                        self._prot_all = cv2.bitwise_or(
                            self._prot_all, _slk)
                    if self.debug:
                        print(f"  [✓]قفلِ ساختارِ روشن — "
                              f"{int(cv2.countNonZero(_slk))}px از "
                              f"{len(_fbs2)} بلوک محافظت شد", flush=True)
        except Exception:
            pass

# بلوک‌هایِ «متنِ روشن روی محفظهٔ تیره» (کارتِ عنوانِ
# Crimson Dragon و امثالش): هرچه کارو/کلیپِ حباب/پروتکت از ماسک
# کم کرده باشد بی‌اثر — ماسک در این بلوک‌ها اجباری توپر می‌شود تا
# ۱) LaMa کلِ بلوک را بازسازی کند (پرکنندهٔ تخت شبح نمی‌گذارد)
# ۲) نوارِ ترکیبِ دو-عکسی کلِ بلوک را از عکسِ پاک‌شده بگیرد
# (پیکسلِ بینِ حروف از عکسِ اصلی نماند = «متنِ قبلی سرِ جایش»).
# سقفِ ترکیب هنرِ بیرونِ بلوک را سالم نگه می‌دارد.
        try:
            _fb_list = (getattr(self, "_lama_force_rect_boxes", None) or [])
            _h, _w = mask.shape[:2]
            _fb_new = []
            for _fb in _fb_list:
                _fx0 = max(0, int(_fb[0]) - 4)
                _fy0 = max(0, int(_fb[1]) - 4)
                _fx1 = min(_w, int(_fb[2]) + 5)
                _fy1 = min(_h, int(_fb[3]) + 5)
                if _fx1 - _fx0 < 8 or _fy1 - _fy0 < 8:
                    _fb_new.append([int(_fb[0]), int(_fb[1]),
                                    int(_fb[2]), int(_fb[3])])
                    continue
# سنجشِ باکس به «متنِ واقعی»: باکسِ ناحیهٔ
# دیتکتور تا مرزِ پنل می‌رود و LaMa قابِ تزئینی را له
# می‌کند (نمونه: GREEN MOON). باکسِ پرشده = bboxِ
# جوهر+هالهٔ داخلِ باکس + پدِ ۱۲px — ساختارِ بیرونِ متن
# هرگز بلعیده نمی‌شود؛ تضمینِ («پیکسلِ بینِ
# حروف از اصل نماند») همچنان برقرار است چون کلِ بلوکِ
# متن پوشیده می‌شود.
                _nx0, _ny0 = _fx0, _fy0
                _nx1, _ny1 = _fx1, _fy1
                _bx0, _by0 = _fx0, _fy0
                _bx1, _by1 = _fx1, _fy1
                try:
                    _sub3 = mask[_fy0:_fy1, _fx0:_fx1]
                    _ys2, _xs2 = np.nonzero(_sub3)
                    if _ys2.size >= 400:
                        _p = 12
                        _nx0 = max(0, _fx0 + int(_xs2.min()) - _p)
                        _ny0 = max(0, _fy0 + int(_ys2.min()) - _p)
                        _nx1 = min(_w,
                                   _fx0 + int(_xs2.max()) + 1 + _p)
                        _ny1 = min(_h,
                                   _fy0 + int(_ys2.max()) + 1 + _p)
                        _bx0, _by0, _bx1, _by1 = _nx0, _ny0, _nx1, _ny1
                except Exception:
                    pass
# پرِ بلوکِ اجباری «خط‌به‌خط»: به‌جایِ یک
# مستطیلِ توپرِ چندخطی (حفرهٔ غول = خمیرِ LaMa + لکهٔ
# تخت روی گرادیان)، هر خطِ متن نوارِ خودش را می‌گیرد
# (bboxِ سطر + پد). بینِ خط‌ها = پس‌زمینهٔ اصل می‌ماند —
# LaMa هر نوار را از بافتِ واقعیِ بالا/پایین بازسازی
# می‌کند (فلسفهٔ «خط به خط» کاربر) و جعبه‌هایِ
# اسنپ‌شات/مقایسه هم نواریند.
                _strips = []
                _p = 12
                try:
# جدایشِ خطی از پالی‌هایِ OCR: پروفیلِ جوهر
# وقتی هالهٔ درخشش بینِ خط‌ها پُرش کند (نمونهٔ «The
# Crimson Dragon,» رویِ پلاک) هر دو خط را یک باند
# می‌کند → حفرهٔ LaMa غول می‌شود و لبهٔ تختِ محسوس
# رویِ گرادیان می‌ماند. مرزِ باند از مرکزِ پالی‌ها
# ولی گسترهٔ باند از «جوهرِ خامِ» همان باند — وگرنه
# پالیِ فونتِ تزئینی (بلندیِ ۱۳۲px) باز کلِ بلوک را
# می‌پوشاند .
                    _src = None
                    if _sub3 is not None and _ys2.size >= 400:
                        _src = _sub3
                        try:
                            _rawS = getattr(
                                self, "_page_raw_text_mask", None)
                            if (_rawS is not None
                                    and _rawS.shape == mask.shape[:2]):
                                _rsub = _rawS[
                                    _fy0:_fy1, _fx0:_fx1]
                                if int(cv2.countNonZero(_rsub)) >= 400:
                                    _src = _rsub
                        except Exception:
                            pass
                    _pl = []
                    try:
                        _rid = int(_fb[4]) if len(_fb) > 4 else -1
                        if _rid >= 0:
                            for _rreg in (getattr(self, "_page_regions",
                                                  None) or []):
                                if int(getattr(_rreg, "id", -2)) == _rid:
                                    for _ppoly in (
                                            getattr(_rreg, "ocr_polys",
                                                    None) or []):
                                        try:
                                            _pp2 = np.asarray(
                                                _ppoly,
                                                dtype=np.float32).reshape(-1, 2)
                                            if _pp2.shape[0] >= 3:
                                                _pl.append(_pp2)
                                        except Exception:
                                            continue
                                    break
                    except Exception:
                        _pl = []
                    if len(_pl) >= 2:
# بازهٔ خامِ y (بدونِ پد) — اگر پدِ قبل از ادغام
# اضافه شود، خط‌هایِ نزدیک (پلاکِ «The Crimson
# Dragon,») در هم می‌لغزند و یک باند می‌شوند.
# مختصاتِ پالی = مطلق؛ بازه‌ها نسبت به باکس‌اند.
                        _ivs = []
                        for _pp2 in _pl:
                            _iy0 = max(0, int(np.floor(
                                _pp2[:, 1].min())) - _fy0)
                            _iy1 = min(_fy1 - _fy0, int(np.ceil(
                                _pp2[:, 1].max())) + 1 - _fy0)
                            _ix0 = max(0, int(np.floor(
                                _pp2[:, 0].min())) - _fx0 - _p)
                            _ix1 = min(_fx1 - _fx0, int(np.ceil(
                                _pp2[:, 0].max())) + 1 - _fx0 + _p)
                            if _iy1 - _iy0 >= 8 and _ix1 - _ix0 >= 8:
                                _ivs.append([_iy0, _iy1, _ix0, _ix1])
                        _ivs.sort(key=lambda _v: (_v[0], _v[1]))
                        _mrg = []
                        for _iv in _ivs:
                            if _mrg and _iv[0] < _mrg[-1][1]:
                                _mrg[-1][1] = max(_mrg[-1][1], _iv[1])
                                _mrg[-1][2] = min(_mrg[-1][2], _iv[2])
                                _mrg[-1][3] = max(_mrg[-1][3], _iv[3])
                            else:
                                _mrg.append(list(_iv))
                        if not (2 <= len(_mrg) <= 12):
# تلاشِ ۲ — شکافِ مرکزها: فونت‌هایِ تزئینی پالیِ
# بلند می‌سازند و بازه‌هایِ y خط‌ها همپوشانی
# دارند (پلاک: [5-137]/[76-205]). مرزِ خط‌ها =
# میانهٔ بزرگ‌ترینِ شکافِ بینِ مرکزِ خط‌ها
# هر باند در مرز کِیل می‌شود.
                            try:
                                _cents = sorted(
                                    (v[0] + v[1]) / 2.0 for v in _ivs)
                                _gaps = [(_cents[_i + 1]
                                            - _cents[_i], _i)
                                           for _i
                                           in range(len(_cents) - 1)]
                                if _gaps:
                                    _gmax, _gi = max(
                                        _gaps, key=lambda t: t[0])
                                    if _gmax >= 14.0:
                                        _bnd = (_cents[_gi]
                                                  + _cents[_gi + 1]) / 2.0
                                        _up = [v for v in _ivs
                                                 if (v[0] + v[1]) / 2.0 < _bnd]
                                        _dn = [v for v in _ivs
                                                 if (v[0] + v[1]) / 2.0 >= _bnd]
                                        if _up and _dn:
                                            _mrg = [
                                                [min(v[0] for v in _up),
                                                 min(_bnd,
                                                     max(v[1] for v in _up)),
                                                 min(v[2] for v in _up),
                                                 max(v[3] for v in _up)],
                                                [max(_bnd,
                                                     min(v[0] for v in _dn)),
                                                 max(v[1] for v in _dn),
                                                 min(v[2] for v in _dn),
                                                 max(v[3] for v in _dn)]]
                            except Exception:
                                _mrg = []
                        if 2 <= len(_mrg) <= 12:
# گسترهٔ باند از «جوهرِ خامِ همان
# باند» نه از bboxِ پالی (فونتِ تزئینی پالیِ
# بلند می‌سازد → نوارها همپوشان می‌شوند و
# حفرهٔ LaMa باز کلِ بلوک می‌شود).
                            _profC = None
                            if _src is not None:
                                _profC = (_src > 0).sum(axis=1)
                                _thrC = max(3.0, 0.04 * (_fx1 - _fx0))
                            for (_ay, _qy2, _ax, _qx2) in _mrg:
                                _ay = int(round(_ay))
                                _qy2 = int(round(_qy2))
                                _ax = int(round(_ax))
                                _qx2 = int(round(_qx2))
                                if _profC is not None:
                                    _seg = _profC[_ay:_qy2]
                                    _rr = np.nonzero(
                                        _seg >= _thrC)[0]
                                    if _rr.size >= 8:
                                        _ny0 = max(0, _ay
                                                   + int(_rr.min()) - 6)
                                        _ny1 = min(_fy1 - _fy0,
                                                   _ay
                                                   + int(_rr.max()) + 7)
                                        if _ny1 - _ny0 >= 10:
                                            _ay, _qy2 = _ny0, _ny1
# پدِ ۲۰px: هالهٔ درخششِ
# متن تا ~۲۰px بیرونِ جوهر می‌رود؛ اگر
# نوار تنگ باشد، هاله دورِ پرِ تازه
# می‌ماند و «قابِ روشنِ» محسوس می‌سازد
# (اسکرین‌شاتِ پلاکِ کاربر).
                                _ay = max(0, _ay - 20)
                                _qy2 = min(_fy1 - _fy0, _qy2 + 20)
                                if _qy2 - _ay < 10:
                                    continue
                                _strips.append([_fx0 + _ax, _fy0 + _ay,
                                                _fx0 + _qx2, _fy0 + _qy2])
                            if self.debug and _strips:
                                print(f"  [🔍] bands از پالیِ OCR: "
                                      f"{len(_strips)} خط")
                        elif self.debug:
                            try:
                                _ivs_dbg = [f"[{v[0]}-{v[1]}]"
                                            for v in _ivs]
                            except Exception:
                                _ivs_dbg = []
                            print(f"  [🔍] poly-bands رد شد: rid={_rid if len(_fb) > 4 else '-'} "
                                  f"polys={len(_pl)} mrg={len(_mrg)} "
                                  f"iv={' '.join(_ivs_dbg)}")
                    if not _strips and _sub3 is not None \
                            and _ys2.size >= 400:
# پروفیلِ سطر/ستون از «جوهرِ خام»
# (قبلِ هاله‌گیریِ ) — هاله، سطرها را به
# هم می‌چسباند و جدایشِ خطی را می‌کُشد
                        _src = _sub3
                        try:
                            _rawS = getattr(
                                self, "_page_raw_text_mask", None)
                            if (_rawS is not None
                                    and _rawS.shape == mask.shape[:2]):
                                _rsub = _rawS[
                                    _fy0:_fy1, _fx0:_fx1]
                                if int(cv2.countNonZero(_rsub)) >= 400:
                                    _src = _rsub
                        except Exception:
                            _src = _sub3
                        _prof = (_src > 0).sum(axis=1)
                        _thr = max(3.0, 0.04 * (_fx1 - _fx0))
                        _rows = _prof >= _thr
                        _bands = []
                        _s = None
                        _g4 = 0
                        for _r in range(_rows.size):
                            if _rows[_r]:
                                if _s is None:
                                    _s = _r
                                _g4 = 0
                            elif _s is not None:
                                _g4 += 1
                                if _g4 > 6:
                                    _bands.append(
                                        (_s, _r - _g4 + 1))
                                    _s = None
                                    _g4 = 0
                        if _s is not None:
                            _bands.append((_s, _rows.size))
                        _pg2 = 8
                        for (_a, _b2) in _bands:
                            _ay = max(0, _a - _pg2)
                            _qy2 = min(_fy1 - _fy0, _b2 + _pg2)
                            if _qy2 - _ay < 10:
                                continue
                            _colp = (_src[_a:_b2] > 0).sum(axis=0)
                            _cols = np.nonzero(_colp > 0)[0]
                            if _cols.size < 8:
                                continue
                            _ax = max(0, int(_cols.min()) - _p
                                        if _ys2.size >= 400 else 4)
                            _qx2 = min(_fx1 - _fx0,
                                        int(_cols.max()) + 1 + _p
                                        if _ys2.size >= 400 else _fx1 - _fx0)
                            if _qx2 - _ax < 8:
                                continue
                            _strips.append([_fx0 + _ax, _fy0 + _ay,
                                            _fx0 + _qx2, _fy0 + _qy2])
                except Exception as _es:
                    if self.debug:
                        import traceback as _tb2
                        print(f"  [!] strips builder error: {_es}")
                        _tb2.print_exc()
                    _strips = []
                if len(_strips) < 1 or len(_strips) > 12:
                    if self.debug:
                        print(f"  [🔍]strips={len(_strips)} "
                              f"→ fallback box", flush=True)
                    _strips = [[_bx0, _by0, _bx1, _by1]]
                if self.debug:
                    try:
                        _sbs = " | ".join(
                            f"({s[0]},{s[1]},{s[2]},{s[3]})" for s in _strips)
                        print(f"  [🔍]force strips: {_sbs}",
                              flush=True)
                    except Exception:
                        pass
                for (_sx0, _sy0, _sx1, _sy1) in _strips:
                    _fb_new.append([_sx0, _sy0, _sx1, _sy1])
                    if os.environ.get("MANGA_NO_FORCE_LAMA", "0") != "1":
                        mask[_sy0:_sy1, _sx0:_sx1] = 255
# ساختارِ روشن/تابِ نور از بلوکِ اجباری خارج
                        try:
                            _pa = getattr(self, "_prot_all", None)
                            if _pa is not None:
                                _sub2 = _pa[_sy0:_sy1, _sx0:_sx1] > 0
                                if int(_sub2.sum()):
                                    mask[_sy0:_sy1, _sx0:_sx1][_sub2] = 0
                                    if self.debug:
                                        print(f"  [✓]"
                                              f"{int(_sub2.sum())}px ساختارِ "
                                              f"روشن از بلوکِ اجباری خارج شد")
                        except Exception:
                            pass
            if _fb_new:
                self._lama_force_rect_boxes = _fb_new
            if _fb_list:
# سقفِ رنگ‌آمیزی (cap) هم باید کلِ بلوک را بپوشاند
                self._page_raw_text_mask = mask.copy()
                if self.debug:
                    try:
                        print(f"  [✓]{len(_fb_new)} بلوکِ محفظهٔ تیره توپر شد")
                    except Exception:
                        pass
        except Exception:
            pass

        cleaned = image.copy()
        counts = {"flat": 0, "color": 0, "LaMa": 0, "OpenCV": 0}
# ماسکِ اتحادِ وارسی: فقط نواحیِ EP-وابسته (LaMa/OpenCV)
# انباشته می‌شوند تا وارسیِ نهاییِ ضدِ خرابیِ GPU دقیقاً روی
# همان‌ها برود؛ پرهایِ فلت/رنگیِ قطعی و SFX/تبلیغ خارج‌اند
        self._verify_union = None
# «بالنِ سیستم»: پرِ فلتِ قطعیِ اینتریورِ باکسِ سفیدِ
# سیستم (یک واحد — خط‌ها + بینِ خط‌ها) قبل از هر پرکنندهٔ دیگر.
# جزئیاتِ چرایی → docstringِ _fill_system_box_interiors.
        try:
            _n_sys = self._fill_system_box_interiors(
                image, regions, mask, cleaned)
            if _n_sys and self.debug:
                print(f"  [*]{_n_sys} اینتریورِ بالنِ سیستم → "
                      f"پرِ فلتِ قطعی (بدونِ LaMa)")
        except Exception:
            pass
        try:
            _n_enc = self._enclosure_instant_fill(
                image, cleaned, regions, mask, skip_ids=_donor_skip)
            if _n_enc and self.debug:
                print(f"  [*] {_n_enc} enclosure filled with own background")
        except Exception:
            pass
        try:
            _n_inst = self._line_instant_fill(
                image, cleaned, regions, mask, skip_ids=_donor_skip)
            if _n_inst and self.debug:
                print(f"  [*] {_n_inst} lines instantly filled")
        except Exception:
            pass
        _stage("پرکنندهٔ فوری")
# قفلِ ساختارِ روشن/تابِ نور: پرکننده‌هایِ فوری حقِ
# دست‌زدن به این پیکسل‌ها را ندارند — خطِ سفیدِ حباب و پرتوِ نور
# باید زنده بمانند (خطایِ img2: «حباب به کل حذف زده»)
        try:
            _pa = getattr(self, "_prot_all", None)
            if _pa is not None and int(cv2.countNonZero(_pa)):
                _sel2 = _pa > 0
                cleaned[_sel2] = image[_sel2]
                if self.debug:
                    print(f"  [✓]{int(_sel2.sum())}px قفلِ روشن "
                          f"بعد از پرکنندهٔ فوری ترمیم شد")
                try:
                    _pvr = os.environ.get("MANGA_PROBE", "")
                    if _pvr and "," in _pvr:
                        _qxr, _qyr = [int(v) for v in _pvr.split(",")]
                        print(f"  [🔍PROBE] after_fill_restore="
                              f"({cleaned[_qyr, _qxr]})", flush=True)
                except Exception:
                    pass
        except Exception:
            pass
# باگِ «لکهٔ بلوکی/سیاهی روی کارتِ تیره»: پرکننده‌هایِ
# فوری ناحیهٔ پرشده را از ماسک کِیل می‌کنند؛ بعد کلاسترِ بعدی با
# «سوراخِ حروف» به LaMa می‌رسید → LaMa متنِ سفیدِ باقی‌مانده در
# حفره‌ها را زمینه فرض می‌کرد و دورش لکهٔ قرمزِ بلوکی می‌ساخت
# (نمونه: تیترِ Crimson Dragon و پلیتِ AIDE ZEPHYROS رویِ گوشی).
# پس از کِیل، باکسِ کاملِ بلوک‌هایِ اجباری-LaMa دوباره توپر می‌شود
# تا LaMa کلِ متن را با هم ببیند و پاک کند (سبکِ پاکسازی عوض
# نمی‌شود — همان مسیرِ اجباری-LaMa با ماسکِ کاملِ ).
        try:
            for _fb in (getattr(self, "_lama_force_rect_boxes",
                                None) or []):
                if os.environ.get("MANGA_NO_FORCE_LAMA", "0") != "1":
                    mask[_fb[1]:_fb[3], _fb[0]:_fb[2]] = 255
# همان حفاظت (بعد از کِیلِ پرکننده‌های فوری
# هم بلوک دوباره توپر می‌شود)
                    try:
                        _pa = getattr(self, "_prot_all", None)
                        if _pa is not None:
                            _sub2 = _pa[_fb[1]:_fb[3],
                                           _fb[0]:_fb[2]] > 0
                            if int(_sub2.sum()):
                                mask[_fb[1]:_fb[3],
                                     _fb[0]:_fb[2]][_sub2] = 0
                    except Exception:
                        pass
        except Exception:
            pass
# اسنپ‌شاتِ «وضعیتِ پرکنندهٔ فوری» برایِ بلوک‌هایِ محفظهٔ
# تیره، قبل از حلقهٔ LaMa. چرا: در نوارِ ترکیبی، بازسازیِ بلوکِ کامل
# توسطِ LaMa-Manga (مدلِ گوشی/سقفِ پچِ ۳۸۴) رویِ صفحهٔ گرادیانیِ تیره
# «لکهٔ بلوکی» می‌سازد (کارتِ عنوانِ Crimson Dragon — بازتولیدِ
# سندباکس در strip_003). پرکنندهٔ فوریِ گرادیانی  رویِ همان
# بلوک «کاملاً تمیز» است (اثبات: MANGA_NO_FORCE_LAMA=1). پس نتیجهٔ
# LaMaِ هر بلوک در اعمالِ نهایی با این اسنپ‌شات سنجیده می‌شود؛ اگر
# انحرافِ لکه‌ای بزرگ داشت، همان اسنپ‌شات جایگزین می‌شود.
        self._force_pre_snap = None
        try:
            _fbs = (getattr(self, "_lama_force_rect_boxes", None) or [])
            if _fbs:
                _hS, _wS = mask.shape[:2]
                _snaps = []
                for _fb in _fbs:
                    _sx0 = max(0, int(_fb[0]) - 6)
                    _sy0 = max(0, int(_fb[1]) - 6)
                    _sx1 = min(_wS, int(_fb[2]) + 7)
                    _sy1 = min(_hS, int(_fb[3]) + 7)
                    if _sx1 - _sx0 >= 8 and _sy1 - _sy0 >= 8:
                        _snaps.append([_sx0, _sy0, _sx1, _sy1,
                                       cleaned[_sy0:_sy1, _sx0:_sx1].copy()])
                if _snaps:
                    self._force_pre_snap = _snaps
                    _sddS = os.environ.get("MANGA_STAGE_DUMP", "")
                    if _sddS:
                        try:
                            _siS = int(getattr(self, "_snap_i", 0))
                            self._snap_i = _siS + 1
                            _sdS = os.path.join(_sddS, f"snap{_siS:02d}")
                            os.makedirs(_sdS, exist_ok=True)
                            for _kS, _sn in enumerate(_snaps):
                                cv2.imwrite(os.path.join(
                                    _sdS, f"box{_kS:02d}.jpg"), _sn[4])
                        except Exception:
                            pass
        except Exception:
            self._force_pre_snap = None
        if not np.any(mask):
            if self.debug:
                print("  [*] everything cleaned by instant fill")
# /63: در این مسیر هم خروجی = عکسِ اصلی + فقط نوارِ متن
            try:
                _cmp = self._compose_strip_mask(image, mask)
                cleaned = self._compose_two_image(cleaned, image, _cmp,
                                                  refill=True)
            except Exception:
                pass
            return cleaned
        page_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        if self.debug:
            try:
                _nf = len(getattr(self, "_lama_force_rect_boxes", None) or [])
                if _nf:
                    print(f"  [*]{_nf} محفظهٔ تیره → اجباری LaMa با ماسکِ کامل")
            except Exception:
                pass
        _wall_cache = {"tried": False, "val": None}

        def _page_wall():
            if not _wall_cache["tried"]:
                _wall_cache["tried"] = True
                try:
                    _wall_cache["val"] = self._wall_lines(image)
                except Exception:
                    _wall_cache["val"] = None
            return _wall_cache["val"]

        crops = []
        _raise_if_stop()
        _q_lama = (bool(getattr(self, "use_lama", False))
                   and self._clean_level() != "fast")
        _pg_h, _pg_w = image.shape[:2]
        _pg_area = float(max(1, _pg_h * _pg_w))
        _webtoon = (min(_pg_h, _pg_w) * 2.5 < max(_pg_h, _pg_w))
# حلقهٔ پرکنندهٔ خوشه‌ها به تابعِ مستقل تبدیل شد تا
# خوشه‌ها همزمان پر شوند (بودجهٔ موازیِ سیستم — «پاکسازیش
# همینجور»): هر خوشه فقط result میسازد و رویِ cleaned نمینویسد
# نوشتنِ نتیجه‌ها همان مسیرِ ترتیبیِ بعدِ LaMa است.
        _clusters_l = list(self._mask_clusters(mask, pad=3))

        def _fill_one_cluster(bx0, by0, bx1, by1):
            cx0, cy0 = max(0, bx0 - 29), max(0, by0 - 29)
            cx1, cy1 = min(image.shape[1], bx1 + 29), min(image.shape[0], by1 + 29)
            crop_img = image[cy0:cy1, cx0:cx1]
            crop_msk = np.zeros((cy1 - cy0, cx1 - cx0), dtype=np.uint8)
            ex1, ey1 = min(bx1, image.shape[1]), min(by1, image.shape[0])
            crop_msk[by0-cy0:ey1-cy0, bx0-cx0:ex1-cx0] = mask[by0:ey1, bx0:ex1]
            _ok_flat = True
            if _q_lama:
                _cb_area = float(max(1, (bx1 - bx0) * (by1 - by0)))
                _ok_flat = (_cb_area <= 0.0035 * _pg_area
                            and (bx1 - bx0) <= 0.30 * _pg_w
                            and (by1 - by0) <= 0.22 * _pg_h)
# کلاسترهایِ «متنِ روشن روی محفظهٔ تیره» اجباری LaMa:
# پرکنندهٔ تخت/رنگی روی گرادیانِ تیره شبحِ حروف جا می‌گذارد
            _force_lama = False
            if _q_lama:
                try:
                    for _fb in (getattr(self, "_lama_force_rect_boxes",
                                        None) or []):
                        if not (bx1 < _fb[0] - 8 or bx0 > _fb[2] + 8
                                or by1 < _fb[1] - 8 or by0 > _fb[3] + 8):
                            _force_lama = True
                            break
# جوهرِ محفظهِ تیره: فقط روشِ LaMa —
# پرکنندهِ تخت/رنگی هنرِ اطرافِ حروف را نابود می‌کند
                    if not _force_lama:
                        for _ib in (getattr(self, "_lama_ink_boxes",
                                            None) or []):
                            if not (bx1 < _ib[0] or bx0 > _ib[2]
                                    or by1 < _ib[1] or by0 > _ib[3]):
                                _force_lama = True
                                break
                except Exception:
                    pass
            if _force_lama:
                result = None
                method = "flat"
                _pf_ok = False
            else:
                result = (self._flat_fill_uniform(crop_img, crop_msk)
                          if _ok_flat else None)
                method = "flat"
                _pf_ok = False
                if result is None:
                    _cr = self._color_fill_cluster(crop_img, crop_msk)
                    if _cr is not None:
                        crop_msk, result = _cr
# پرکنندهٔ رنگی ماسک را با دیلهٔ ۲۵+کلوز
# گسترش می‌دهد و همین گسترش، ساختارِ روشنِ نزدیک
# (قابِ سفیدِ کارتِ img2-r10) را هم می‌بلعید و با
# TELEA پاک می‌کرد («اون یکی کامل سیاه کرده»).
# پیکسل‌هایِ قفل‌شده از ماسکِ برگشتی خارج می‌شوند.
                        try:
                            _pasub = getattr(self, "_prot_all", None)
                            if _pasub is not None:
                                _subc = _pasub[cy0:cy1, cx0:cx1] > 0
                                if int(_subc.sum()):
                                    crop_msk = crop_msk.copy()
                                    crop_msk[_subc] = 0
                                    if self.debug:
                                        print(f"  [✓]"
                                              f"{int(_subc.sum())}px قفل از "
                                              f"پرکنندهٔ رنگی خارج شد")
                        except Exception:
                            pass
                        method = "color"
                if result is None:
                    if not _q_lama:
                        _pf = self._paper_fill_cluster(crop_img, crop_msk)
                        if _pf is not None:
                            result = _pf
                            _pf_ok = True
                _keep_flat = False
                if result is None and not _q_lama:
                    result = self._flat_fill_cluster(crop_img, crop_msk)
                elif result is None and _q_lama \
                        and _android_gate("MANGA_FILL_RESCUE") \
                        and float(cv2.countNonZero(crop_msk)) >= 0.40 * float(
                            max(1, (bx1 - bx0) * (by1 - by0))):
# اندروید: فقط «حفرهٔ بزرگ» (ماسکِ block-rect∪ink
# ~≥۴۰٪ باکس) → پرِ درجه‌دومِ تخت از حلقه؛ نوارهایِ باریکِ
# line-strips (~۱۵-۳۰٪) همچنان به LaMa میروند که رویِ
# حفرهٔ کوچک از پرِ تختِ درجه‌دوم تمیزتر است (گرادیانِ
# حباب را از زمینهٔ بزرگتر میخواند).
                    result = self._flat_fill_cluster(crop_img, crop_msk)
                    if result is not None:
# ضدِ توهمِ LaMa (MANGA_BIGCAV_FLAT):
# LaMaِ حفرهٔ بزرگِ چندخطی (بلوکِ متنِ متراکم) در
# داوناسکیل «متنِ قلابی/نویزِ گلیفی» میسازد (لاگِ
# گوشیِ 700×11362 + بازتولیدِ A/B — «لکهٔ کثیف»).
# اگر حلقه عمدتاً «روشنِ یکدست» باشد (دیوار/کاغذِ
# صاف — اقلیتِ تیرهٔ حلق = هنرِ چسبیده رد میشود)
# پرِ درجه‌دومِ حلقه «نگه داشته میشود» حتی اگر
# گاردِ بافتِ کل-کراپ (بهخاطرِ همان اقلیتِ تیره)
# textured بگوید.
                        try:
                            _gr = cv2.cvtColor(crop_img,
                                                  cv2.COLOR_BGR2GRAY)
                            _m = crop_msk > 0
                            _rg = (cv2.dilate(
                                crop_msk, np.ones((9, 9), np.uint8)) > 0) \
                                & (~_m)
                            _rv = _gr[_rg].astype(np.float32)
                            if _rv.size >= 200:
                                _rm = float(np.median(_rv))
                                _share = float((np.abs(
                                    _rv - _rm) <= 26.0).mean())
                                if (_rm >= 170.0 and _share >= 0.55):
                                    _keep_flat = True
                        except Exception:
                            pass
                    elif result is None and _android_gate(
                            "MANGA_BIGCAV_FLAT"):
# fitِ حلقهٔ روشن: وقتی اقلیتِ تیرهٔ
# حلقه (هنرِ چسبیده) fitِ عادی را میشکند ولی
# دیوار/کاغذِ روشن هنوز حاکم است، fit فقط از
# پیکسلهایِ روشنِ حلقه → پرِ تمیز بهجایِ
# LaMaِ توهمزن.
                        _lrg = self._flat_fill_cluster(
                            crop_img, crop_msk, light_ring=True,
                            fit_tol=13.0)
                        if _lrg is not None:
                            result = _lrg
                            _keep_flat = True
                            if self.debug:
                                try:
                                    print(f"  [⚡]حفرهٔ بزرگ → پرِ حلقهٔ "
                                          f"روشن بهجایِ LaMa "
                                          f"@({cx0},{cy0})")
                                except Exception:
                                    pass
                elif result is None and _q_lama \
                        and _android_gate("MANGA_FLATRING"):
# اندروید/سرعت: حلقهٔ اطرافِ حفره «تخت» است
# (گسترهٔ صدکیِ ≤۲۴ — متن روی کاغذِ سفید/پنلِ تخت) →
# پرِ درجه‌دومِ حلقه بهجایِ LaMa (LaMaِ خوشهایِ 21
# کلاسترِ صفحهٔ 700×11362 = 42.7s؛ بیشترشان کاغذِ
# سفیداند). گاردِ بافتِ پایین (textured) اگر پرِ تخت
# را نپسندد به LaMa برمیگرداند — کیفیتِ وبتونِ
# گرادیانی دست‌نخورده میماند.
                    _rf = MangaTranslator._ring_flat_stats(crop_img,
                                                              crop_msk)
                    if _rf is not None:
                        result = self._flat_fill_cluster(crop_img, crop_msk)
                        if result is not None and self.debug:
                            try:
                                print(f"  [⚡]حلقهٔ تخت (med={_rf[0]:.0f} "
                                      f"std={_rf[1]:.0f}) → پرِ حلقه "
                                      f"بهجایِ LaMa @({cx0},{cy0})")
                            except Exception:
                                pass
                if (result is not None and not _pf_ok
                        and not _keep_flat
                        and self._bg_is_textured(crop_img, crop_msk,
                                                 strong=True)):
                    result = None
            return [cx0, cy0, cx1, cy1, crop_msk, result, method]

        _fill_w = 1
        try:
            _fill_w = _parallel_budget("clean")
        except Exception:
            _fill_w = 1
        if len(_clusters_l) >= 2 and _fill_w > 1:
            try:
                with ThreadPoolExecutor(max_workers=min(
                        _fill_w, len(_clusters_l))) as _fillx:
                    crops = list(_fillx.map(
                        lambda _cc: _fill_one_cluster(*_cc),
                        _clusters_l))
            except Exception:
                crops = [_fill_one_cluster(*_cc)
                         for _cc in _clusters_l]
        else:
            crops = [_fill_one_cluster(*_cc) for _cc in _clusters_l]
        try:
            _pvc = os.environ.get("MANGA_PROBE", "")
            if _pvc and "," in _pvc:
                _qxc, _qyc = [int(v) for v in _pvc.split(",")]
                print(f"  [🔍PROBE] after_cluster_fills="
                      f"({cleaned[_qyc, _qxc]})", flush=True)
        except Exception:
            pass

        pending = [c for c in crops if c[5] is None]
        if pending and getattr(self, "use_lama", False):
            lama = self._get_lama()
            if lama is not None:
                _qc_kernel = getattr(self, "_qc_kernel31", None)
                if _qc_kernel is None:
                    _qc_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
                    self._qc_kernel31 = _qc_kernel
                _img_h, _img_w = image.shape[:2]
                _extreme = os.environ.get("MANGA_LAMA_FULLPAGE", "0") != "1"
                _long = float(max(_img_h, _img_w))
                _short = float(max(1.0, min(_img_h, _img_w)))
                if _extreme:
                    _mode = "patch-wise"
# فیکس groups=pending — قبلاً groups=لیستِ تختِ کراپ‌ها بود و وقتی
# فقط «یک» کلاستر در صف بود (صفحهٔ تک‌ناحیه‌ای)، حلقهٔ for grp همان
# «کراپِ تکی» را به‌جای «لیستِ کراپ‌ها» می‌داد → _lama_group_prep
# روی int کرش → استثنایِ بی‌صدا → LaMa کلاً می‌مُرد → پرِ
# گرادیانی/TELEA → شبحِ لکه. در دسته‌ای نوارها چندکلاستری‌اند
# (len>1) و باگ شلیک نمی‌کرد. حالا ساختار از ابتدا درست است.
                    groups = [[c] for c in pending]
                    if os.environ.get("MANGA_LAMA_GROUP", "1") != "0" and len(pending) > 1:
                        _gap = 24
                        if _long >= 2.5 * _short:
# بازگشت به فرمولِ testm
# (0.16×ضلعِ کوتاه، سقفِ ۱۴۴): گپِ ۰.۲۴/۲۲۰ِ
# زنجیرههایِ دورتر (فاصلهٔ ۱۵۰-۲۴۰px
# بلوکهایِ سندِ 9.jpg مثلِ y=1552..3844) را هم
# میچسباند → پچِ ۷۰۰×۲۳۰۰ → داوناسکیلِ ۰.۵۶ِ
# big-lama → «مهِ خاکستری/باندِ کدر» رویِ donor
# زنجیرههایِ
# واقعیِ ۶۰-۹۰px (منطقِ ۲۱۶) هنوز با گپِ ۱۱۲
# گروه میشوند — پلهٔ رنگیِ «کوه» برنمیگردد.
                            _gap = int(max(32, min(144, round(_short * 0.16))))
                        elif _on_android():
                            _gap = int(max(24, min(96, round(_short * 0.04))))
                        try:
                            _mm = int(os.environ.get(
                                "MANGA_LAMA_MAX_MEMBERS", "0") or 0)
                        except Exception:
                            _mm = 0
# هزینهٔ هر فراخوانیِ LaMa با مساحتِ داخلیِ
# سقف‌خورده (≤۳۸۴) متناسب است — پچِ بزرگ‌تر = مجموعِ
# محاسبهٔ کمتر. اندروید ۶→۱۰ عضو (~۲x سریع‌تر)
                        if _mm <= 0:
                            _mm = 10 if _on_android() else 6
                        groups = self._group_nearby_patches(
                            pending, gap=_gap, max_members=_mm)
# بنرِ تبلیغ (promo) هرگز با کلاسترهایِ
# دیگر گروه نمی‌شود: گروهِ بزرگ‌تر = کراپِ بزرگ‌تر =
# داون‌اسکیلِ بیشتر (مثلاً 0.61) → LaMa-Manga بنر را
# «موشِ بنفش/صورتی» بازسازی می‌کند (بازتولیدِ
# سندباکس). بنرِ تنها با پدِ ۵۵٪ = تمیزِ کامل.
                        try:
                            _prbG = (getattr(self, "_promo_rect_boxes",
                                             None) or [])
                            if _prbG:
                                _ng = []
                                for _grp in groups:
                                    _hp = False
                                    for _c in _grp:
                                        for _pb in _prbG:
                                            if not (_c[2] < int(_pb[0])
                                                    or _c[0] > int(_pb[2])
                                                    or _c[3] < int(_pb[1])
                                                    or _c[1] > int(_pb[3])):
                                                _hp = True
                                                break
                                        if _hp:
                                            break
                                    if _hp and len(_grp) > 1:
                                        _ng.extend([[_c] for _c in _grp])
                                    else:
                                        _ng.append(_grp)
                                groups = _ng
                        except Exception:
                            pass
                    if _short * 2.5 < _long:
                        _mode += " — long strip"
                    if self.debug:
                        print(f"  [*] LaMa {_mode}: {len(pending)} clusters → "
                              f"{len(groups)} patches on {_img_w}x{_img_h}")
                    t0 = time.time()
# یک منبعِ حقیقت — همان _lama_workers_auto
# (قبلاً یک جدولِ تکراریِ همین‌جا بود که با آن فرق داشت)
                    try:
                        _workers = self._lama_workers_auto()
                    except Exception:
                        _workers = 1
# بیش از cores÷2 پچِ همزمان، حافظه/کش را اشباع
# می‌کند (صفحهٔ ۶ پچیِ POCO: 6×1نخی = 53.8s!) — 4×2نخی
# همان‌ها را در ۲ موج و سریع‌تر تمام می‌کند
                    if _on_android():
                        try:
                            _workers = max(1, min(
                                _workers, len(groups),
                                max(1, self._cpu_core_count() // 2)))
                        except Exception:
                            pass
                    _workers = max(1, min(_workers, len(groups)))
# نخِ هر پچ = هسته‌ها ÷ پچِ موازی — پچِ کم →
# نخِ بیشتر (قبلاً همیشه ۱ نخ بود و هسته‌ها بیکار می‌ماند)
                    try:
                        _cores_n = int(self._cpu_core_count())
                    except Exception:
                        _cores_n = 0
                    _thr_want = (1 if _workers >= 5
                                 else max(1, min(4, max(2, _cores_n) // _workers)))
                    try:
                        lama = self._get_lama(threads=_thr_want) or lama
                    except Exception:
                        pass
                    _thr_eff = max(1, int(getattr(lama, "thr_used", 1) or 1))
# اگر سشن با نخِ متفاوت باز است، همین‌جا یک‌بار
# با force سوئیچ کن — خنک‌کاریِ ۲s بعدِ لودِ پس‌زمینه‌ای
# اولین سوئیچ را می‌خورد و زمان‌بند روی ۲×۴ (کند روی
# big.LITTLE) می‌ماند. بعدِ سوئیچ: پچِ موازیِ بیشتر ×
# نخِ کمتر (تنظیمِ سریعِ v47 روی POCO F4).
                    if _thr_eff != _thr_want and _workers >= 2:
                        try:
                            lama = self._get_lama(threads=_thr_want,
                                                  force=True) or lama
                        except Exception:
                            pass
                        _thr_eff = max(1, int(getattr(lama, "thr_used", 1)
                                              or 1))
# ضدِ اشباعِ نخ — لاگِ POCO F4 (۸ هسته) نشان کرد
# سشنِ اولیه با ۴ نخ باز می‌ماند (سوئیچِ ۴→۲ با گاردِ رم
# رد می‌شود) و زمان‌بند ۴ پچِ موازی × ۴ نخ = ۱۶ نخ روی
# ۸ هسته می‌سازد → Over-subscription و کندی (۶۵s به‌جای
# ~۵۰s). اگر سشن نخِ بیشتری از نیاز دارد، تعدادِ پچِ
# موازی را کم کن تا workers × threads ≈ هسته‌ها بماند.
                    if _thr_eff > _thr_want and _cores_n >= 4:
                        try:
                            _workers = max(1, min(
                                _workers, _cores_n // _thr_eff))
                        except Exception:
                            pass
                    _no_batch_m = self._lama_batch_cap() <= 0 \
                        or not hasattr(lama, "run_batch_tensors")
                    if not _no_batch_m:
# (SRV-H4) — بچینگِ هم‌شکلِ پدشده فقط opt-in
# (MANGA_LAMA_BATCH=1/N)؛ پیش‌فرض: مسیرِ موازیِ قدیمیِ
# per-patch (e32bccf).
                        _raise_if_stop()
                        self._lama_run_groups_batched(image, groups, lama,
                                                      page_kernel)
                        _raise_if_stop()
                    elif _workers > 1:
                        try:
                            _cores = self._cpu_core_count()
                        except Exception:
                            _cores = "?"
                        if self.debug:
                            print(f"  [*] {_workers} parallel patches × "
                                  f"{_thr_eff} thread(s)")
                        _pex = ThreadPoolExecutor(max_workers=_workers)
                        _futs = []
                        try:
                            for grp in groups:
                                _raise_if_stop()
                                _futs.append(_pex.submit(
                                    self._lama_run_group, image, grp,
                                    lama, page_kernel))
                            for _f in _futs:
                                try:
                                    _f.result(timeout=600)
                                except FuturesTimeout:
                                    print("    [!] LaMa patch exceeded 600s → skipped")
                                except Exception:
                                    pass
                                _raise_if_stop()
                        except BaseException:
                            for _f in _futs:
                                _f.cancel()
                            _pex.shutdown(wait=False)
                            raise
                        _pex.shutdown(wait=True)
                    else:
                        for grp in groups:
                            _raise_if_stop()
                            try:
                                self._lama_run_group(image, grp, lama, page_kernel)
                            except Exception as _ge:
                                if os.environ.get("MANGA_LAMA_DBG"):
                                    import traceback
                                    print("    [lama-dbg] group crashed:\n"
                                          + traceback.format_exc(), flush=True)
                                continue
                    dt = time.time() - t0
                    _done = sum(1 for c in pending if c[6] == "LaMa")
                    if _done and self.debug:
                        print(f"  [*] LaMa clustered: {dt:.1f}s "
                              f"({_done}/{len(pending)} clusters in {len(groups)} patches)")
                    self._mem_trim()  # رمِ فازِ LaMa آزاد شود
                else:
                    try:
                        page_mask = cv2.dilate(mask, page_kernel)
                        _wall = self._wall_lines(image)
                        if _wall is not None:
                            pm = page_mask > 0
                            mk = mask > 0
                            wl = _wall > 0
                            page_mask = ((pm & mk) | (pm & ~wl)).astype(np.uint8) * 255
                        t0 = time.time()
                        page_out = lama(image, page_mask)
                        dt = time.time() - t0
                        if isinstance(page_out, np.ndarray):
                            page_bgr = page_out
                        else:
                            page_bgr = np.array(page_out)
                        if page_bgr.ndim == 2:
                            page_bgr = cv2.cvtColor(page_bgr, cv2.COLOR_GRAY2BGR)
                        else:
                            page_bgr = cv2.cvtColor(page_bgr, cv2.COLOR_RGB2BGR)
                        if page_bgr.shape[:2] != image.shape[:2]:
                            raise ValueError("LaMa returned an unexpected image shape")
                        if self.debug:
                            print(f"  [*] LaMa full-page: {dt:.1f}s "
                                  f"({len(pending)} clusters)")
                        for c in pending:
                            cx0, cy0, cx1, cy1, crop_msk = c[:5]
                            result = page_bgr[cy0:cy1, cx0:cx1]
                            try:
                                _fm = (cv2.dilate(crop_msk, page_kernel) > 0)
                                _ring_m = (cv2.dilate(crop_msk, _qc_kernel) > 0) & (~_fm)
                                if _fm.any() and _ring_m.any():
                                    _g = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
                                    _bg_px = _g[_ring_m]
                                    _bright = _bg_px[_bg_px >= 160.0]
                                    if _bright.size >= max(50, int(0.02 * _bg_px.size)) and _bright.size >= 0.55 * _bg_px.size:
                                        _bg_med = float(np.median(_bright))
                                        _fill_med = float(np.median(_g[_fm]))
                                        if _fill_med < 115.0 and _fill_med < _bg_med - 55.0:
                                            print(f"  [!] LaMa left a dark stain "
                                                  f"({_fill_med:.0f} vs paper {_bg_med:.0f}) "
                                                  f"→ flat/OpenCV fill for this cluster")
                                            result = None
                            except Exception:
                                pass
                            if result is not None:
                                c[4] = cv2.dilate(crop_msk, page_kernel)
                                c[5] = result
                                c[6] = "LaMa"
                    except Exception as e:
                        print(f"  [!] LaMa failed ({e}); using OpenCV fallback.")
            else:
                print("  [!] LaMa unavailable → OpenCV for remaining clusters")
        _stage("LaMa/پرکننده‌ها")

        for cx0, cy0, cx1, cy1, crop_msk, result, method in crops:
            if os.environ.get("MANGA_FILL_DBG"):
                try:
                    print(f"    [paste-dbg] @({cx0},{cy0}) "
                          f"{cx1-cx0}x{cy1-cy0} "
                          f"msk={int((crop_msk>0).sum())} "
                          f"method={method} ok={result is not None}",
                          flush=True)
                except Exception:
                    pass
# اعتبارسنجیِ نتیجهٔ LaMa رویِ بلوک‌هایِ محفظهٔ تیره:
# در نوارِ ترکیبی، بازسازیِ بلوکِ کاملِ LaMa-Manga رویِ صفحهٔ
# گرادیانیِ تیره «لکهٔ بلوکیِ تیره» می‌سازد (کارتِ عنوانِ Crimson
# Dragon — بازتولیدِ سندباکس). اسنپ‌شاتِ پرکنندهٔ فوریِ گرادیانی
# (قبل از LaMa) مرجع است؛ انحرافِ بزرگ = لکه → جایگزینی با
# اسنپ‌شات (سبکِ پاکسازی عوض نمی‌شود — همان پرکنندهٔ فوریِ خودم).
            if (method == "LaMa" and result is not None
                    and getattr(self, "_force_pre_snap", None)):
                try:
                    for _sn in self._force_pre_snap:
                        _ix0 = max(cx0, _sn[0])
                        _iy0 = max(cy0, _sn[1])
                        _ix1 = min(cx1, _sn[2])
                        _iy1 = min(cy1, _sn[3])
                        if _ix1 - _ix0 < 24 or _iy1 - _iy0 < 24:
                            continue
                        _ra = (np.asarray(result[
                            _iy0 - cy0:_iy1 - cy0,
                            _ix0 - cx0:_ix1 - cx0],
                            dtype=np.int16))
                        _rb = (np.asarray(_sn[4][
                            _iy0 - _sn[1]:_iy1 - _sn[1],
                            _ix0 - _sn[0]:_ix1 - _sn[0]],
                            dtype=np.int16))
                        if _ra.shape != _rb.shape or _ra.size < 400:
                            continue
# بلوکِ donor-گسترش‌یافته: مرجع = نتیجهٔ
# LaMa، نه اسنپ‌شاتِ پرکنندهٔ فوری (تخت = همان
# «لگِ سیاه» که کاربر گزارش کرد). کاربر گفته عکسِ
# اول کامل پاک شه؛ جعبهٔ تیره هم با LaMa بافت‌مند
# بازسازی می‌شود و نوارِ خط‌به‌خطِ آن تمیز می‌ماند.
# فقط وقتی زمینهٔ دورِ بلوک «بافت‌مند»
# است (پرده/بوکه). کارتِ گرادیانیِ صاف: پرِ فوریِ
# گرادیانیِ اسنپ‌شات تمیز‌تر است (کارتِ Crimson
# Dragon — LaMa رویِ گرادیانِ تیره شبح/لکهٔ بلوکی
# می‌گذارد) → همان منطقِ جایگزینیِ بماند.
                        try:
                            _dn_hit = False
                            for _db in (getattr(self, "_donor_boxes", None)
                                        or []):
                                if not (_ix1 < _db[0] or _ix0 > _db[2]
                                        or _iy1 < _db[1] or _iy0 > _db[3]):
                                    _dn_hit = True
                                    break
                            if _dn_hit:
# فقط جعبه‌هایی که «داخلشان» بافت‌مند
# است LaMa را مرجع می‌گیرند؛ داخلِ صاف/گرادیانی
# (کارتِ Crimson Dragon) → منطقِ بماند.
                                if MangaTranslator._box_bg_textured(
                                        image, _sn[0], _sn[1], _sn[2], _sn[3]):
# «نگه‌داشتنِ LaMa» فقط وقتی
# که روشناییِ زمینهٔ غیرمتن هم همان ماند.
# img2: پنلِ تیرهٔ ~۶۰ → LaMa سیاهِ ~۱۲
# داد («کامل سیاه کرده» کاربر) → منطقِ
# (جایگزینی با اسنپ‌شات) بسنجد.
                                    _keep3 = True
                                    try:
                                        _gA = cv2.cvtColor(
                                            np.clip(_ra, 0, 255).astype(np.uint8),
                                            cv2.COLOR_BGR2GRAY)
                                        _gB = cv2.cvtColor(
                                            np.clip(_rb, 0, 255).astype(np.uint8),
                                            cv2.COLOR_BGR2GRAY)
                                        _gO2 = cv2.cvtColor(
                                            image[_iy0:_iy1, _ix0:_ix1],
                                            cv2.COLOR_BGR2GRAY)
                                        _txt = cv2.dilate(
                                            (_gO2 >= 150).astype(np.uint8),
                                            np.ones((5, 5), np.uint8)) > 0
                                        _bg2 = ~_txt
                                        if int(_bg2.sum()) >= 300:
                                            _mA = float(np.median(_gA[_bg2]))
                                            _mB2 = float(np.median(_gB[_bg2]))
                                            if abs(_mA - _mB2) > 30.0:
                                                _keep3 = False
                                                print(f"  [!]LaMa زمینه را "
                                                      f"{_mB2:.0f} → {_mA:.0f} تغییرِ شدید داد "
                                                      f"→ اسنپ‌شاتْ مرجع",
                                                      flush=True)
                                    except Exception:
                                        _keep3 = True
                                    if _keep3:
                                        if self.debug:
                                            try:
                                                print(f"  [✓]بلوکِ "
                                                      f"بافت‌مند → نتیجهٔ "
                                                      f"LaMa نگه داشته شد",
                                                      flush=True)
                                            except Exception:
                                                pass
                                        continue  # زمینهٔ بافت‌مند → LaMa مرجع
# نامعتبر → منطقِ پایین‌تر
                        except Exception:
                            pass
                        _dM = np.abs(_ra - _rb).max(axis=2).astype(np.uint8)
                        _dM = cv2.GaussianBlur(_dM, (0, 0), 4)
                        _dm_mean = float(_dM.mean())
                        _dm_big = float((_dM > 26).mean())
# گاردِ «متنِ شبح»: اگر اسنپ‌شات هنوز
# جوهرِ متنیِ زیاد دارد (پرکنندهٔ فوری ناکام مانده —
# پنلِ روشن) ولی نتیجهٔ LaMa هموارتر است، جایگزینی
# ممنوع — وگرنه متنِ انگلیسی برمی‌گشت. سنجش:
# انرژیِ فرکانسِ بالا نسبت به میانهٔ محلی (حروف نازک
# = ساختار؛ لکه/گرادیانِ نرم = بی‌ساختار).
                        _gs = cv2.cvtColor(
                            np.clip(_rb, 0, 255).astype(np.uint8),
                            cv2.COLOR_BGR2GRAY)
                        _gl = cv2.cvtColor(
                            np.clip(_ra, 0, 255).astype(np.uint8),
                            cv2.COLOR_BGR2GRAY)
                        _mk = (41 if min(_gs.shape) >= 41
                                 else 31 if min(_gs.shape) >= 31 else 15)
                        _ms = cv2.medianBlur(_gs, _mk)
                        _ml = cv2.medianBlur(_gl, _mk)
                        _fs = float((np.abs(
                            _gs.astype(np.int16)
                            - _ms.astype(np.int16)) > 30).mean())
                        _fl = float((np.abs(
                            _gl.astype(np.int16)
                            - _ml.astype(np.int16)) > 30).mean())
                        if _fs > _fl * 1.6 + 0.02:
                            if self.debug:
                                print(f"  [✓]اسنپ‌شاتِ بلوک هنوز "
                                      f"متن دارد (جوهرِ اسنپ={_fs:.3f} > "
                                      f"LaMa={_fl:.3f}) → نتیجهٔ LaMa "
                                      f"نگه داشته شد (جلوگیری از متنِ شبح)",
                                      flush=True)
                            continue
# گاردِ جوهرِ هستهٔ ماسک: اسنپ‌شاتی که
# هنوز «جوهرِ متن» درونِ ماسکِ متن دارد هرگز
# جایگزینِ LaMa نمیشود. آستانهٔ ۳۰ِ 62b شبحِ
# نیمه‌پوشیده را نمیبیند (پرکنندهٔ فوریِ ناموفق
# کنتراستِ ~۲۰) — لاگِ کاملِ 4e2e77: «LaMa زمینه
# را 146→183 → اسنپ‌شاتْ مرجع» = برگشتِ خوانای
# [TRAITS: FILTHY RICH…] (اسکرینشاتِ سازنده).
# سنجشِ مستقیم روی «هستهٔ ماسک» (جایی که میدانیم
# متن بوده) با آستانهٔ ۲۰ + برتریِ ۲× از LaMa.
                        try:
                            _mc = None
                            try:
                                _mc = (crop_msk > 0) \
                                    if crop_msk.shape[:2] == _gs.shape \
                                    else None
                            except Exception:
                                _mc = None
                            if _mc is not None \
                                    and int(_mc.sum()) >= 200:
                                _ds = np.abs(
                                    _gs.astype(np.int16)
                                    - _ms.astype(np.int16))
                                _dl = np.abs(
                                    _gl.astype(np.int16)
                                    - _ml.astype(np.int16))
                                _iks = float(
                                    (_ds[_mc] > 20).mean())
                                _ikl = float(
                                    (_dl[_mc] > 20).mean())
                                if _iks > 0.045 and \
                                        _iks > _ikl * 2.0 + 0.02:
                                    if self.debug:
                                        print(
                                            f"  [✓]جوهرِ متن در اسنپ‌شات "
                                            f"(هسته={_iks:.3f} > "
                                            f"LaMa={_ikl:.3f}) → LaMa "
                                            f"نگه داشته شد (ضدِ شبح)",
                                            flush=True)
                                    continue
                        except Exception:
                            pass
# فقط «لکهٔ بلوکی» — لکهٔ واقعی (کارتِ عنوان) در
# Δ>26 بوم‌بوم است (اندازه‌گیری: ۰.۶۲/۰.۷۶) ولی
# بازسازیِ سالمِ LaMa روی پنل‌هایِ آبی فقط Δμ=۶-۷
# و Δ>26≈۰.۰۱ دارد → شرط روی فراکسیونِ لکه‌ای است
# نه میانگین (وگرنه پاکیِ سالم جایگزین می‌شد!)
                        if _dm_big > 0.08 and _dm_mean > 9.0:
                            _res2 = np.array(result)
                            _res2[_iy0 - cy0:_iy1 - cy0,
                                  _ix0 - cx0:_ix1 - cx0] = \
                                _sn[4][_iy0 - _sn[1]:_iy1 - _sn[1],
                                       _ix0 - _sn[0]:_ix1 - _sn[0]]
                            result = _res2
                            if self.debug:
                                print(f"  [✓]لکهٔ بلوکیِ LaMa روی "
                                      f"بلوکِ تیره (Δμ={_dm_mean:.1f}, "
                                      f"Δ>{_dm_big:.2f}) → پرکنندهٔ فوریِ "
                                      f"گرادیانی جایگزین شد", flush=True)
                            break
                except Exception:
                    pass
            _prot_c = None
            if getattr(self, "_page_protect", None) is not None:
                try:
                    _prot_c = self._page_protect[cy0:cy1, cx0:cx1]
                except Exception:
                    _prot_c = None
# سقفِ ترکیب — هیچ پرکننده‌ای نباید بیش از ~۷px
# بیرونِ ماسکِ خامِ متن نقاشی کند. _dil/_color ماسک را تا ۲۵px
# گشاد + CLOSE می‌کنند و روی هنرِ اطرافِ حباب لکهٔ خاکستری
# می‌سازند (رینگِ اسمیر دورِ «BUT I LIKE IT HERE.»)
            _cap_k = getattr(self, "_cap_kernel7", None)
            if _cap_k is None:
                _cap_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
                self._cap_kernel7 = _cap_k
            _mm_cap = None
            try:
                _raw_c = self._page_raw_text_mask[cy0:cy1, cx0:cx1]
                _mm_cap = (cv2.dilate(_raw_c, _cap_k) > 0)
            except Exception:
                _mm_cap = None
            if result is None:
# بلوکِ اجباری-LaMa (محفظهٔ تیره) که LaMa آن را
# از دست داد: پرِ گرادیانیِ توپرِ داخلِ باکس (همان ریاضیِ
# اثبات‌شدهٔ پرکنندهٔ فوری) به‌جای فال‌بکِ OpenCV؛ وگرنه
# refineِ تنگِ گلیف، هالهٔ قرمز را زنده می‌گذارد (لکهٔ
# قرمزِ POCO F4). اسنپ‌شاتِ قبلِ LaMa هم قابلِ اعتماد نیست —
# در مسیرِ block-rect∪ink هنوز خودِ متن را دارد.
                try:
                    _res3 = self._force_box_gradient_fill(
                        image, cx0, cy0, cx1, cy1)
                except Exception:
                    _res3 = None
                if _res3 is not None:
                    result = _res3
                    if self.debug:
                        print(f"  [✓]LaMaِ بلوکِ تیره در دسترس "
                              f"نبود → پرِ گرادیانیِ توپرِ باکس (ضدِ لکهٔ "
                              f"قرمز)", flush=True)
            if result is None:
                crop_img = image[cy0:cy1, cx0:cx1]
                try:
                    _thick0 = float(cv2.distanceTransform(
                        (crop_msk > 0).astype(np.uint8), cv2.DIST_L2, 3).max())
                except Exception:
                    _thick0 = 0.0

                _kd = int(np.clip(2 * int(round(max(3.0, _thick0 * 0.55))) + 1, 7, 25))
                _oc_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (_kd, _kd))
                _dil = cv2.morphologyEx(
                    cv2.dilate(crop_msk, _oc_k, iterations=1),
                    cv2.MORPH_CLOSE, _oc_k)
# هالهٔ گلو (متنِ روشن روی پنلِ تیره): رویِ
# زمینهٔ تیره، ماسکِ فال‌بک باید هالهٔ دورِ گلیف را هم
# بپوشاند وگرنه جوهرِ قرمز/روشنِ دورِ حرف می‌ماند
                _bg_med2 = None
                try:
                    _g2 = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
                    _m = _dil > 0
                    _ring2 = (cv2.dilate(_dil,
                                          np.ones((13, 13), np.uint8)) > 0) \
                        & (~_m)
                    if int(_ring2.sum()) >= 60:
                        _bg_med2 = float(np.median(_g2[_ring2]))
                        if _bg_med2 < 100.0:
                            _glow = (_g2 >= _bg_med2 + 26.0) & \
                                (cv2.dilate(_dil, np.ones(
                                    (15, 15), np.uint8)) > 0)
                            _glow = cv2.morphologyEx(
                                _glow.astype(np.uint8), cv2.MORPH_CLOSE,
                                np.ones((7, 7), np.uint8))
                            _dil = cv2.bitwise_or(
                                _dil, (_glow > 0).astype(np.uint8) * 255)
                except Exception:
                    _bg_med2 = None
                try:
                    _thick = float(cv2.distanceTransform(
                        (_dil > 0).astype(np.uint8), cv2.DIST_L2, 3).max())
                except Exception:
                    _thick = _thick0
# رویِ پنلِ تیره هرگز «نازک» حساب نشو (گلو)
                _thin = (_thick <= 28.0) and not (
                    _bg_med2 is not None and _bg_med2 < 100.0)
# استروکِ نازک روی گرادیان → پرکردنِ صفحه‌ایِ حلقه
# (قبل از TELEA که رنگِ هنرِ نزدیک را می‌کشد)
                if _thick0 <= 14.0:
                    try:
                        _rpf = self._ring_plane_fill(crop_img, crop_msk)
                    except Exception:
                        _rpf = None
                    if _rpf is not None:
                        result = _rpf
# refineِ تنگِ گلیف فقط رویِ زمینهٔ روشن: رویِ
# پنلِ تیره ماسک را تا هستهٔ حرف جمع می‌کند و هالهٔ قرمزِ
# دورِ حرف زنده می‌ماند (بازتولیدِ لکهٔ قرمزِ POCO F4)
# + برایِ خوشهٔ تبلیغ (promo) هرگز refine نکن — ماسکِ توپرِ
# بنر باید توپر بماند وگرنه بینِ حروفِ بنر بنفش می‌ماند
                _is_promo = False
                try:
                    for _pb2 in (getattr(self, "_promo_rect_boxes",
                                          None) or []):
                        if not (cx1 < int(_pb2[0]) or cx0 > int(_pb2[2])
                                or cy1 < int(_pb2[1]) or cy0 > int(_pb2[3])):
                            _is_promo = True
                            break
                except Exception:
                    _is_promo = False
                if self._bg_is_textured(crop_img, _dil) and \
                        not _is_promo and \
                        (_bg_med2 is None or _bg_med2 >= 100.0):
                    _refined = self._glyph_refine_mask(crop_img, _dil)
                    if _refined is not None:
                        _tl = self._opencv_inpaint_hq(crop_img, _refined)
                        if _tl is not None:
                            crop_msk = _refined
                            result = _tl
                if result is None:
                    _sm = self._smooth_bg_fill(crop_img, _dil)
                    if _sm is not None:
                        crop_msk = _dil
                        result = _sm
                    elif _thin and not _is_promo:
                        _refined = self._glyph_refine_mask(crop_img, _dil)
                        if _refined is not None:
                            _sm2 = self._smooth_bg_fill(crop_img, _refined)
                            if _sm2 is not None:
                                crop_msk = _refined
                                result = _sm2
                    if result is None:
                        result = self._opencv_fill_components(crop_img,
                                                              crop_msk,
                                                              wall=_page_wall())
                method = "OpenCV"
                try:
                    result = self._scrub_dark_residuals(result, crop_msk)
                except Exception:
                    pass
                try:
                    result = self._scrub_bright_residuals(result, crop_msk)
                except Exception:
                    pass
# تنظیمِ رنگِ حلقه + بلندِ آلفا برایِ OpenCV هم:
# فال‌بکِ TELEA رویِ آسمانِ نقش‌دار «مستطیلِ کثیف» می‌ساخت
# (img3) چون فقط نتیجهٔ LaMa تنظیمِ رنگ می‌شد.
            if method in ("LaMa", "OpenCV"):
                try:
                    try:
                        _ann_in = cv2.dilate(
                            (crop_msk > 0).astype(np.uint8),
                            np.ones((19, 19), np.uint8)) > 0
                        _ann_out = cv2.dilate(
                            (crop_msk > 0).astype(np.uint8),
                            np.ones((41, 41), np.uint8)) > 0
                        _ring = _ann_out & (~_ann_in)
                        if int(_ring.sum()) >= 200:
                            _dstc = cleaned[cy0:cy1, cx0:cx1]
                            _ring_std = float(
                                _dstc[_ring].astype(np.float32).std())
# زمینهٔ بافت‌مند (آسمانِ نقش‌دارِ
# img3): stdِ حلقه بالاست ولی IQR کوچک —
# تنظیمِ رنگِ نتیجهٔ LaMa نباید رد شود، وگرنه
# نوارها به‌صورتِ «مستطیلِ کثیفِ کدر» می‌مانند.
                            try:
                                _rq = np.percentile(
                                    _dstc[_ring].astype(np.float32),
                                    [25, 75])
                                _ring_ok = (_ring_std <= 26.0) or (
                                    float(_rq[1] - _rq[0]) <= 42.0)
                            except Exception:
                                _ring_ok = _ring_std <= 26.0
                            if _ring_ok:
                                _deltas = []
                                for _ch in range(3):
                                    _m_r = float(np.median(
                                        _dstc[..., _ch][_ring]
                                        .astype(np.float32)))
                                    _m_l = float(np.median(
                                        result[..., _ch][_ring]
                                        .astype(np.float32)))
                                    _deltas.append(max(
                                        -16.0, min(16.0, _m_r - _m_l)))
                                if any(abs(_d) > 1.0 for _d in _deltas):
                                    _core_t = cv2.erode(
                                        (crop_msk > 0).astype(np.uint8),
                                        np.ones((5, 5), np.uint8))
                                    _soft = cv2.GaussianBlur(
                                        _core_t.astype(np.float32),
                                        (9, 9), 2.5)
                                    _soft = np.clip(_soft, 0.0, 1.0)[..., None]
                                    _res_f = result.astype(np.float32)
                                    _res_f = _res_f + (
                                        np.array(_deltas, dtype=np.float32)
                                        [None, None, :] * _soft)
                                    result = np.clip(
                                        _res_f, 0, 255).astype(np.uint8)
                    except Exception:
                        pass
# تطبیقِ لو-فرکانسِ پرِ LaMa با زمینهٔ
# پیرامون. نکتهٔ مهمِ تستِ واقعی (412e9e/890fb1 رویِ
# CPUِ پچِ ۳۸۴): میدانِ دیفرانسِ باکسِ بزرگ خودش
# «باندِ موج‌دار/بلوکی» می‌سازد — پرکنندهٔ LaMa در
# اکثرِ موارد خودش درست است → پیش‌فرضِ خاموش
# فقط با MANGA_LFCM=1 برایِ آزمایش فعال می‌شود.
                    try:
# گیتِ بافتِ LFCM: فقط رویِ زمینهٔ
# «صاف/گرادیانی» (کارتِ عنوان) اجرا شود؛ رویِ
# زمینهٔ بافت‌مند میدانِ دیفرانسِ باکسِ بزرگ خودش
# باندِ موج‌دار می‌سازد (تستِ 412e9e) → خودکار رد.
                        _go = False
                        if method == "LaMa" \
                                and os.environ.get(
                                    "MANGA_NO_LFCM", "0") != "1":
                            try:
                                _mbT = (crop_msk > 0)
                                if int(_mbT.sum()) >= 2000:
                                    _ri = cv2.dilate(
                                        _mbT.astype(np.uint8),
                                        np.ones((19, 19), np.uint8)) > 0
                                    _ro = cv2.dilate(
                                        _mbT.astype(np.uint8),
                                        np.ones((41, 41), np.uint8)) > 0
                                    _rt = _ro & (~_ri)
                                    _gT = cv2.cvtColor(
                                        image[cy0:cy1, cx0:cx1],
                                        cv2.COLOR_BGR2GRAY)
                                    _rs = (float(_gT[_rt].std())
                                             if int(_rt.sum()) >= 200
                                             else 99.0)
                                    _go = (_rs <= 34.0)
                                    if self.debug:
                                        print(f"  [🔍]LFCM "
                                              f"gate crop@({cx0},{cy0}) "
                                              f"ring_std={_rs:.0f} → "
                                              f"{'RUN' if _go else 'skip'}",
                                              flush=True)
                            except Exception:
                                _go = False
                        _mB3 = (crop_msk > 0) if crop_msk.dtype != np.uint8 \
                            else (crop_msk > 0)
                        _nMB = int(_mB3.sum())
                        if _go and _nMB >= 2000:
                            _th = float(cv2.distanceTransform(
                                _mB3.astype(np.uint8), cv2.DIST_L2, 3).max())
# پنجرهٔ LFCM باید نسبت به «پهنایِ
# نوار» هم مقیاس شود؛ وگرنه در انتهایِ نوارهایِ
# عریض (پلاکِ ۶۰۰px) پروفیلِ افقیِ وینیت را
# نمی‌گیرد و لبهٔ روشن/تیرهٔ نوار پیدا می‌ماند.
                            _cw = int(crop_msk.shape[1])
                            _k = int(np.clip(
                                round(max(_th * 3.0, _cw * 0.45)),
                                41, 331))
                            if _k % 2 == 0:
                                _k += 1
                            _img = image[cy0:cy1, cx0:cx1].astype(
                                np.float32)
                            _res4 = result.astype(np.float32)
                            _wb = (~_mB3).astype(np.float32)
                            try:
                                _raw = getattr(
                                    self, "_page_raw_text_mask", None)
                                if (_raw is not None
                                        and _raw.shape
                                        == image.shape[:2]):
                                    _rd = cv2.dilate(
                                        _raw[cy0:cy1, cx0:cx1],
                                        np.ones((9, 9), np.uint8))
                                    _wb[(_rd > 0) & (~_mB3)] = 0.0
                            except Exception:
                                pass
# پیکسل‌هایِ قفلِ ساختار (قاب/نوارِ
# روشن) هم نمونهٔ زمینه نیستند؛ وگرنه بلورِ
# بزرگ رنگِ نقره‌ایِ قاب را وسطِ حفره می‌کشد
                            try:
                                _pa2 = getattr(self, "_prot_all", None)
                                if (_pa2 is not None
                                        and _pa2.shape
                                        == image.shape[:2]):
                                    _pd = cv2.dilate(
                                        _pa2[cy0:cy1, cx0:cx1],
                                        np.ones((5, 5), np.uint8))
                                    _wb[(_pd > 0)
                                          & (~_mB3)] = 0.0
                            except Exception:
                                pass
                            _den = cv2.boxFilter(
                                _wb, -1, (_k, _k))
                            _num = cv2.boxFilter(
                                _img * _wb[..., None], -1,
                                (_k, _k))
                            _bg3 = _num / np.maximum(
                                _den, 1e-3)[..., None]
                            _fl2 = cv2.boxFilter(
                                _res4, -1, (_k, _k))
                            _d2 = np.clip(_bg3 - _fl2, -44.0, 44.0)
                            _w2 = cv2.GaussianBlur(
                                (cv2.dilate(
                                    _mB3.astype(np.uint8),
                                    np.ones((3, 3), np.uint8)) * 255),
                                (0, 0), 3.0).astype(np.float32) / 255.0
                            _w2 = np.clip(_w2, 0.0, 1.0)[..., None]
# جاهایی که زمینهٔ نمونه‌گیریِ کافی
# ندارند وزنِ نرمِ پایین (نه cutoffِ بلوکی)
                            try:
                                _low = (_den < 0.05).astype(np.float32)
                                if float(_low.mean()) > 0.001:
                                    _low = cv2.GaussianBlur(
                                        _low, (31, 31), 8.0)
                                    _w2 = _w2 * (
                                        1.0 - 0.65 * _low[..., None])
                            except Exception:
                                pass
                            _res4 = _res4 + _d2 * _w2
                            result = np.clip(
                                _res4, 0, 255).astype(np.uint8)
                            if self.debug:
                                try:
                                    _dm2 = float(np.abs(
                                        _d2 * _w2).mean())
                                    print(f"  [✓]LFCM "
                                          f"crop@({cx0},{cy0}) "
                                          f"k={_k} |Δ|={_dm2:.1f}",
                                          flush=True)
                                except Exception:
                                    pass
                    except Exception:
                        pass
# هم‌سازِ ستونیِ نوارهایِ عریض رویِ
# زمینهٔ تیرهٔ صاف (پلاکِ «Crimson Dragon»): پرِ
# LaMa پروفیلِ قائمِ وینیت را ادامه نمی‌دهد →
# باندِ تیره‌تر/روشن‌تر با لبهٔ واضح (اسکرین‌شاتِ
# کاربر). هدف = میان‌یابیِ خطیِ حلقهٔ بالا/پایینِ
# هر ستون (: به‌جایِ corrِ ثابت، شیبِ
# کاملِ قائم جایگزینِ فرکانسِ پایینِ پر می‌شود —
# بافتِ فرکانس‌بالا دست‌نخورده می‌ماند).
                    try:
                        _mB4 = (crop_msk > 0)
                        _h2, _w3 = _mB4.shape
                        if int(_mB4.sum()) >= 8000 and _w3 >= 260:
                            _ysB, _xsB = np.nonzero(_mB4)
                            _ty, _by = (int(_ysB.min()),
                                            int(_ysB.max()))
                            _gO3 = cv2.cvtColor(
                                image[cy0:cy1, cx0:cx1],
                                cv2.COLOR_BGR2GRAY).astype(np.float32)
                            _top = max(0, _ty - 16)
                            _topb = max(1, _ty - 3)
                            _bot = min(_h2, _by + 4)
                            _botb = min(_h2, _by + 17)
                            if (_by - _ty) >= 40 and \
                                    (_topb - _top) >= 6 and \
                                    (_botb - _bot) >= 6:
                                _resf = result.astype(np.float32)
                                _corr = np.zeros(
                                    (_h2, _w3, 3), dtype=np.float32)
                                _nok = 0
                                for _x in range(_w3):
                                    if not _mB4[_ty:_by + 1,
                                                 _x].any():
                                        continue
                                    if _mB4[_top:_topb, _x].any() \
                                            or _mB4[_bot:_botb,
                                                     _x].any():
                                        continue
                                    _rt2 = _gO3[_top:_topb, _x]
                                    _rb2 = _gO3[_bot:_botb, _x]
                                    if _rt2.size < 4 or _rb2.size < 4:
                                        continue
                                    if max(_rt2.std(), _rb2.std()) > 22.0:
                                        continue
                                    _yy = np.linspace(
                                        0.0, 1.0, _by - _ty + 1,
                                        dtype=np.float32)[:, None]
                                    for _c2 in range(3):
                                        _mt = float(np.median(
                                            image[cy0 + _top:
                                                  cy0 + _topb,
                                                  cx0 + _x,
                                                  _c2]).astype(np.float32))
                                        _mb = float(np.median(
                                            image[cy0 + _bot:
                                                  cy0 + _botb,
                                                  cx0 + _x,
                                                  _c2]).astype(np.float32))
                                        _tgt = (_mt * (1.0 - _yy)
                                                  + _mb * _yy)
                                        _lo = cv2.GaussianBlur(
                                            _resf[_ty:_by + 1,
                                                    _x, _c2],
                                            (0, 0), 0.02 * max(
                                                8.0, _by - _ty))
                                        _corr[_ty:_by + 1, _x,
                                                _c2] = np.clip(
                                            _tgt - _lo, -26.0, 26.0
                                        ).reshape(-1)
                                    _nok += 1
                                if _nok >= max(40, int(0.35 * _w3)):
                                    _corr[:, :, 0] = cv2.GaussianBlur(
                                        _corr[:, :, 0], (0, 0), 9.0)
                                    _corr[:, :, 1] = cv2.GaussianBlur(
                                        _corr[:, :, 1], (0, 0), 9.0)
                                    _corr[:, :, 2] = cv2.GaussianBlur(
                                        _corr[:, :, 2], (0, 0), 9.0)
                                    _wcol = (cv2.GaussianBlur(
                                        (cv2.dilate(
                                            _mB4.astype(np.uint8),
                                            np.ones((3, 3),
                                                    np.uint8)) * 255),
                                        (0, 0), 3.0
                                    ).astype(np.float32) / 255.0)
                                    _rese = _resf + _corr \
                                        * _wcol[..., None]
                                    result = np.clip(
                                        _rese, 0, 255).astype(np.uint8)
                                    if self.debug:
                                        _act = float(np.abs(
                                            _corr).mean())
                                        print(f"  [✓]col-harmonize "
                                              f"crop@({cx0},{cy0}) "
                                              f"cols={_nok} "
                                              f"|corr|={_act:.1f}",
                                              flush=True)
                    except Exception:
                        pass
                    _m8 = (crop_msk if crop_msk.dtype == np.uint8
                           else (crop_msk > 0).astype(np.uint8) * 255)
                    if _prot_c is not None:
                        _m8 = _m8.copy()
                        _m8[_prot_c > 0] = 0  # دیوار محافظت شود
# پیکسل‌هایِ قفلِ روشن هم هرگز نوشته نشوند
                    try:
                        _paw = getattr(self, "_prot_all", None)
                        if _paw is not None:
                            _pa_c2 = _paw[cy0:cy1, cx0:cx1]
                            if _pa_c2.shape == _m8.shape:
                                _m8[_pa_c2 > 0] = 0
                    except Exception:
                        pass
                    if _mm_cap is not None:
                        _m8 = cv2.bitwise_and(_m8, _mm_cap.astype(np.uint8) * 255)
                    _core = cv2.erode(_m8, np.ones((3, 3), np.uint8)) > 0
                    _alpha = cv2.GaussianBlur(_m8, (7, 7), 2.0)
                    _alpha = np.minimum(_alpha, _m8)
                    _alpha[_core] = 255
                    _a3 = (_alpha.astype(np.float32) / 255.0)[..., None]
                    _dst = cleaned[cy0:cy1, cx0:cx1].astype(np.float32)
                    _res = (result if result.dtype == np.float32
                            else result.astype(np.float32))
                    _bl = _dst * (1.0 - _a3) + _res * _a3
                    cleaned[cy0:cy1, cx0:cx1] = _bl.astype(np.uint8)
                except Exception:
                    mm = crop_msk > 0
                    if _prot_c is not None:
                        mm = mm & (_prot_c == 0)
                    try:
                        _pax = getattr(self, "_prot_all", None)
                        if _pax is not None:
                            _pa_c3 = _pax[cy0:cy1, cx0:cx1]
                            if _pa_c3.shape == mm.shape:
                                mm = mm & (_pa_c3 == 0)
                    except Exception:
                        pass
                    if _mm_cap is not None:
                        mm = mm & _mm_cap
                    cleaned[cy0:cy1, cx0:cx1][mm] = result[mm]
            else:
                mm = crop_msk > 0
                if _prot_c is not None:
                    mm = mm & (_prot_c == 0)
                try:
                    _pay = getattr(self, "_prot_all", None)
                    if _pay is not None:
                        _pa_c4 = _pay[cy0:cy1, cx0:cx1]
                        if _pa_c4.shape == mm.shape:
                            mm = mm & (_pa_c4 == 0)
                except Exception:
                    pass
                if _mm_cap is not None:
                    mm = mm & _mm_cap
                cleaned[cy0:cy1, cx0:cx1][mm] = result[mm]
            counts[method] += 1
            if os.environ.get("MANGA_DUMP_AFTER_PASTE"):
                try:
                    cv2.imwrite(
                        os.environ["MANGA_DUMP_AFTER_PASTE"], cleaned)
                except Exception:
                    pass
# انباشتنِ ماسکِ وارسی (وارسیِ واقعی یک‌بار در
# پایانِ پاکسازی انجام می‌شود — بدونِ تداخل با LFCM/سویپ و
# بدونِ فشارِ حافظهٔ LaMa در میانهٔ کار)
            try:
                if method in ("LaMa", "OpenCV"):
                    if self._verify_union is None:
                        self._verify_union = np.zeros(
                            image.shape[:2], dtype=bool)
                    self._verify_union[cy0:cy1, cx0:cx1] |= (crop_msk > 0)
            except Exception:
                pass
# پروبِ درونِ حلقه: چه کراپی پیکسلِ قفل‌شده را می‌نویسد؟
            try:
                _pvl = os.environ.get("MANGA_PROBE", "")
                if _pvl and "," in _pvl:
                    _qxl, _qyl = [int(v) for v in _pvl.split(",")]
                    if cx0 <= _qxl < cx1 and cy0 <= _qyl < cy1:
                        _ly, _lx = _qyl - cy0, _qxl - cx0
                        _lmsk = crop_msk if crop_msk.shape[0] > _ly else None
                        _inm2 = bool(_lmsk is not None and _lmsk[_ly, _lx] > 0)
                        print(f"  [🔍PROBE] crop@({cx0},{cy0}) method={method} "
                              f"px_in_crop_msk={_inm2} "
                              f"after=({cleaned[_qyl, _qxl]})", flush=True)
            except Exception:
                pass
        try:
            _pva = os.environ.get("MANGA_PROBE", "")
            if _pva and "," in _pva:
                _qxa, _qya = [int(v) for v in _pva.split(",")]
                print(f"  [🔍PROBE] after_crops_apply="
                      f"({cleaned[_qya, _qxa]})", flush=True)
        except Exception:
            pass
# ماسک‌ها/نتیجه‌هایِ کراپ‌ها بعد از ترکیب آزاد شوند —
# روی نوارِ بلند ~۵۰-۱۵۰MB است که در سویپ‌ها و ذخیره لازم می‌آید
        try:
            del crops, pending, groups
        except Exception:
            pass
        self._mem_trim()  # قبل از سویپ‌ها رم آزاد شود

# بازرسیِ رنگیِ بنرِ تبلیغ: LaMa-Manga برایِ حفرهٔ بزرگِ
# بنر رویِ خطوطِ سرعت گاهی بنفشِ «خیالی» نقاشی می‌کند (منبعش
# لبه‌هایِ بنفشِ نیم‌پوشانده است). داخلِ هر بنرِ promo اگر پیکسلِ
# بنفشِ اشباعِ معنادار ماند → همان پیکسل‌ها با TELEA از حلقهٔ خود
# بنر پر می‌شود (خروجی: راه‌راهِ محو — بی‌بنفش).
        try:
            _prbC = (getattr(self, "_promo_rect_boxes", None) or [])
            if _prbC:
                _hC, _wC = cleaned.shape[:2]
                for _pbC in _prbC:
                    _qx0 = max(0, int(_pbC[0]))
                    _qy0 = max(0, int(_pbC[1]))
                    _qx1 = min(_wC, int(_pbC[2]))
                    _qy1 = min(_hC, int(_pbC[3]))
                    if _qx1 - _qx0 < 16 or _qy1 - _qy0 < 16:
                        continue
                    _roiC = cleaned[_qy0:_qy1, _qx0:_qx1]
                    _hsvC = cv2.cvtColor(_roiC, cv2.COLOR_BGR2HSV)
                    _pC = ((_hsvC[..., 0] >= 95) & (_hsvC[..., 0] <= 178)
                           & (_hsvC[..., 1] >= 60) & (_hsvC[..., 2] >= 30))
                    _nC = int(_pC.sum())
                    if _nC < 120:
                        continue
                    _mC = cv2.dilate(_pC.astype(np.uint8),
                                     np.ones((9, 9), np.uint8)) * 255
                    _roiC2 = cv2.inpaint(_roiC, _mC, 7,
                                         cv2.INPAINT_TELEA)
                    cleaned[_qy0:_qy1, _qx0:_qx1] = _roiC2
                    if self.debug:
                        try:
                            print(f"  [✓]{_nC}px رنگِ بنرِ "
                                  f"تبلیغ در خروجی ماند → TELEA re-scrub",
                                  flush=True)
                        except Exception:
                            pass
        except Exception:
            pass

# جاروی جوهرِ روشنِ باقی‌مانده «داخلِ» بلوک‌هایِ محفظهٔ
# تیره (کارتِ عنوان). کاربر: «عکس‌ها را کامل خوب پاک کنه؛ اضافه پاک
# کردن هم اشکال نداره». نمونهٔ واقعی: تکهٔ سفیدِ «S(» وسطِ کارتِ
# Crimson Dragon که نه در کِیلِ پرکنندهٔ فوری بود و نه LaMa کامل
# برداشت. داخلِ این بلوک‌ها هر پیکسلِ روشن (پس‌زمینهٔ کارت تیره است)
# با رنگِ محلیِ خودِ صفحه (همان پرکنندهٔ فوریِ گرادیانی) پر می‌شود
# قابِ تزئینی بیرونِ باکس است (باکس ۸px فرسایش می‌گیرد) و دست
# نمی‌خورد.
        try:
            _fbsW = (getattr(self, "_lama_force_rect_boxes", None) or [])
            if _fbsW:
                _hW, _wW = cleaned.shape[:2]
                _gW = cv2.cvtColor(cleaned, cv2.COLOR_BGR2GRAY)
                _protW = getattr(self, "_page_protect", None)
                _nW = 0
                for _fbW in _fbsW:
                    _wx0 = max(0, int(_fbW[0]) + 8)
                    _wy0 = max(0, int(_fbW[1]) + 8)
                    _wx1 = min(_wW, int(_fbW[2]) - 7)
                    _wy1 = min(_hW, int(_fbW[3]) - 7)
                    if _wx1 - _wx0 < 12 or _wy1 - _wy0 < 12:
                        continue
                    _sub = _gW[_wy0:_wy1, _wx0:_wx1]
# گاردِ زمینه: این سویپ فقط برایِ کارت‌هایِ
# «تیرهٔ یکنواخت» است (کارتِ Crimson). اگر حلقهٔ دورِ
# باکس در عکسِ اصل بافت‌مند/روشن باشد (نئبولا، بافتِ
# پنل، قابِ نقره‌ای)، پیکسل‌هایِ روشنِ داخلِ باکس
# احتمالاً زمینهٔ قانونی‌اند نه جوهرِ جامانده → سویپ
# ممنوع؛ وگرنه نئبولای روشنِ داخلِ نوارِ EXEC
# MEETING با رنگِ تیرهٔ تخت پر می‌شد (بازتولیدِ
# «بلوک‌هایِ تخت»).
                    try:
                        _rgW = 14
                        _rx0W = max(0, int(_fbW[0]) - _rgW)
                        _ry0W = max(0, int(_fbW[1]) - _rgW)
                        _rx1W = min(_wW, int(_fbW[2]) + _rgW)
                        _ry1W = min(_hW, int(_fbW[3]) + _rgW)
                        if _rx1W - _rx0W >= 20 and _ry1W - _ry0W >= 20:
                            _gOW = cv2.cvtColor(
                                image[_ry0W:_ry1W, _rx0W:_rx1W],
                                cv2.COLOR_BGR2GRAY)
                            _boxW = np.zeros_like(_gOW)
                            _boxW[int(_fbW[1]) - _ry0W:int(_fbW[3]) - _ry0W,
                                  int(_fbW[0]) - _rx0W:int(_fbW[2]) - _rx0W] = 255
                            _ringW = ((cv2.dilate(_boxW,
                                                  np.ones((31, 31), np.uint8))
                                       > 0) & (_boxW == 0))
                            try:
                                _rawW = getattr(
                                    self, "_page_raw_text_mask", None)
                                if (_rawW is not None
                                        and _rawW.shape
                                        == image.shape[:2]):
                                    _ringW &= (cv2.dilate(
                                        _rawW[_ry0W:_ry1W,
                                                _rx0W:_rx1W],
                                        np.ones((5, 5), np.uint8)) == 0)
                            except Exception:
                                pass
                            if int(_ringW.sum()) >= 120:
                                _ringV = _gOW[_ringW]
                                _rstdW = float(_ringV.std())
                                _rbriW = float((_ringV >= 140).mean())
# معیارِ stdِ حلقه حذف شد:
# حلقهٔ باکس‌هایِ داخلِ صحنهٔ پرجزئیات
# (سکه/قابِ WICKEDِ 012_p1) همیشه
# بافت‌مند است ولی «محفظهٔ» خودِ باکس
# سیاهِ یکنواخت است — سویپ فقط
# پیکسل‌هایِ روشنِ داخل را با رنگِ
# تیرهٔ محلی پر می‌کند. گاردِ واقعی =
# یکنواختیِ محفظهٔ تیره (پایین‌تر) +
# حلقهٔ روشن (کارتِ سفید).
                                if _rbriW > 0.30:
                                    if self.debug:
                                        print(f"  [✓]سویپِ جوهرِ "
                                              f"روشن رد شد — حلقهٔ "
                                              f"روشن (کارتِ سفید؟) "
                                              f"bright={_rbriW:.2f}",
                                              flush=True)
                                    continue
                    except Exception:
                        pass
# آستانهٔ ۱۴۰ دست‌نخورده ماند: آزمایشِ سندباکس
# نشان داد آستانهٔ نسبی (med+26) بافتِ اسپَتِر خودِ کارت
# را هم می‌گیرد و «شبحِ تیره» می‌سازد. هالهٔ قرمز باید در
# «ماسک» پوشانده شود (اسنپ‌شات/LaMa)، نه با سویپ.
                    _bright = (_sub >= 140)
                    if _protW is not None:
                        _bright = _bright & (
                            _protW[_wy0:_wy1, _wx0:_wx1] == 0)
# حبابیِ OCR گاهی یک گلیف را از قلم
# می‌اندازد (Wِ «WICKED» در 012_p1) و نقشهٔ
# حفاظتِ ساختاری آن گلیفِ تنها را «قاب/خطِ
# روشن» می‌خواند و همیشه زنده نگهش می‌دارد.
# اجزایِ کوچکِ هم‌اندازهٔ حرف (<۱۲۰۰px و
# <۹۰px درازا) که داخلِ محفظهٔ تیرهٔ یکدست
# قفس شده‌اند = بقایایِ حرف‌اند، نه قاب —
# به سویپ برگردانده می‌شوند. قاب/پرتوِ
# کشیده دست‌نخورده می‌ماند.
                        try:
                            _bP = (_sub >= 140) & (
                                _protW[_wy0:_wy1, _wx0:_wx1] > 0)
                            if int(_bP.sum()) > 0:
                                _nP, _lP, _sP, _ = \
                                    cv2.connectedComponentsWithStats(
                                        _bP.astype(np.uint8), 8)
                                for _jP in range(1, _nP):
                                    _aP = int(_sP[_jP,
                                                      cv2.CC_STAT_AREA])
                                    _wP = int(_sP[_jP,
                                                      cv2.CC_STAT_WIDTH])
                                    _hP = int(_sP[_jP,
                                                      cv2.CC_STAT_HEIGHT])
                                    if _aP <= 1200 and \
                                            max(_wP, _hP) <= 90:
                                        _bright |= (_lP == _jP)
                        except Exception:
                            pass
                    _bright = cv2.morphologyEx(
                        _bright.astype(np.uint8), cv2.MORPH_OPEN,
                        np.ones((3, 3), np.uint8)) > 0
                    if int(_bright.sum()) < 16:
                        continue
                    if float(_bright.mean()) > 0.5:
                        continue  # بلوک عمدتاً روشن؟ → این کارتِ تیره نیست
# گاردِ یکنواختیِ محفظه: سویپ فقط وقتی
# امن است که پیکسل‌هایِ تیرهٔ داخلِ باکس یکدست باشند
# (کارتِ سیاه/سرخِ صاف). محفظهٔ بافت‌مند/گرادیانی
# (نئبولای EXEC) با std تیره‌هایِ بالا رد می‌شود.
                    _darkM2 = ((_sub < 120).astype(np.uint8))
                    _dkV = _sub[_darkM2 > 0]
                    if _dkV.size >= 200 and \
                            float(_dkV.std()) > 30.0:
                        if self.debug:
                            print(f"  [✓]سویپِ جوهرِ روشن رد شد — "
                                  f"محفظهٔ یکدست نیست "
                                  f"(std={float(_dkV.std()):.0f})",
                                  flush=True)
                        continue
                    _subC = cleaned[_wy0:_wy1, _wx0:_wx1]
                    _darkM = ((_sub < 120).astype(np.uint8)
                              & (~_bright).astype(np.uint8))
                    _srcF = _subC.astype(np.float32)
                    _kW = 31
                    _numW = cv2.blur(_srcF * _darkM[..., None], (_kW, _kW))
                    _denW = cv2.blur(_darkM.astype(np.float32), (_kW, _kW))
                    _dkW = _srcF[_darkM > 0]
                    _fbW2 = (np.median(_dkW, axis=0) if _dkW.size >= 30
                             else np.median(
                                 _srcF[_bright == 0].reshape(-1, 3),
                                 axis=0)
                             if int((_bright == 0).sum()) > 30
                             else np.array([0.0, 0.0, 0.0]))
                    _fillW = np.where(
                        _denW[..., None] > 0.02,
                        _numW / np.maximum(_denW, 1e-6)[..., None],
                        _fbW2[None, None, :]).astype(np.float32)
                    _dilW = cv2.dilate(
                        _bright.astype(np.uint8),
                        np.ones((5, 5), np.uint8)) > 0
                    _selW = _dilW
                    _subC[_selW] = np.clip(
                        np.rint(_fillW[_selW]), 0, 255).astype(np.uint8)
                    cleaned[_wy0:_wy1, _wx0:_wx1] = _subC
                    _nW += int(_bright.sum())
                if _nW and self.debug:
                    print(f"  [✓]{_nW}px جوهرِ روشنِ باقی‌مانده "
                          f"داخلِ بلوک‌هایِ تیره پاک شد", flush=True)
        except Exception:
            pass

# روشِ «دو عکس» کاربر: عکسِ اول = پاک‌شدهٔ کامل (حتی اگر
# حباب در آن خراب یا بیشتر پاک شده باشد — مهم نیست)، عکسِ دوم =
# عکسِ اصلی که «خروجی» روی آن ساخته می‌شود. فقط نوارهایِ متن از
# عکسِ اول برش می‌خورند؛ هر آسیبی که پاک‌سازی بیرونِ نوارها زده
# باشد (دیوارِ حباب، بینِ خط‌ها، هنر) اینجا دور ریخته می‌شود.
# سویپ‌هایِ بعدی روی همین تصویرِ ترکیب‌شده کار می‌کنند تا اگر جوهرِ
# بیرونِ نوار مانده باشد، همان‌جا پاک شود.
# باگِ «متن پاک نشده»: کامپوز فقط با «ماسکِ بازمانده»
# بود؛ اما _enclosure_instant_fill ناحیهٔ محفظه را از ماسک کِیل
# می‌کند و حاصلِ پرکردنِ فوری‌اش (و هر پرکنندهٔ دیگر بیرونِ ماسکِ
# کِیل‌شده) با کامپوز دور ریخته می‌شد → متنِ قدیمی از عکسِ اصلی
# برمی‌گشت (نمونه: تیترِ «The Crimson Dragon…»). حالا ماسکِ کامپوز
# = ماسکِ متن ∪ همهٔ پیکسل‌هایِ واقعاً تغییرکرده — مثلِ مسیرِ
# early-return در بالا. سقفِ تغییرها قبلاً با mm_cap (~۱۵px بیرونِ
# ماسکِ خام) کنترل شده، پس لکهٔ دور از متن ساخته نمی‌شود.
# ابزارِ دیباگِ مرحله‌ای (MANGA_STAGE_DUMP=پوشه) — قبل/بعدِ کامپوز و
# سویپِ بقایا؛ برایِ ریشه‌یابیِ «لکه» که کدام مرحله ساخته
        _sdd = os.environ.get("MANGA_STAGE_DUMP", "")
# پروبِ نقطه‌ای: MANGA_PROBE="x,y" → مقدارِ cleaned در
# هر مرحله چاپ می‌شود (ریشه‌یابیِ «چه مرحله‌ای پیکسل را کشت»)
        _probe = None
        try:
            _pv = os.environ.get("MANGA_PROBE", "")
            if _pv and "," in _pv:
                _px2, _py2 = [int(v) for v in _pv.split(",")]
                _probe = (_px2, _py2)
        except Exception:
            _probe = None
        if _probe is not None:
            print(f"  [🔍PROBE] start=({cleaned[_probe[1], _probe[0]]}) "
                  f"orig=({image[_probe[1], _probe[0]]})", flush=True)
        if _sdd:
            try:
                _si = int(getattr(self, "_stage_i", 0))
                self._stage_i = _si + 1
                _sd = os.path.join(_sdd, f"s{_si:02d}")
                os.makedirs(_sd, exist_ok=True)
                cv2.imwrite(os.path.join(_sd, "pre_compose.jpg"), cleaned)
                if _probe is not None:
                    print(f"  [🔍PROBE] pre_compose={cleaned[_probe[1], _probe[0]]}", flush=True)
            except Exception:
                _sd = ""
# کامپوزِ دو-عکسیِ «خط‌به‌خطِ سخت»: فقط نوارِ متنِ خام
# (نه پیکسل‌هایِ تغییرکردهٔ پراکنده، نه کلِ حباب/محفظه). قبلًا
# «تغییرکرده ∪ ماسک» بود که کلِ حبابِ پُرشده را به خروجی می‌برد —
# اعتراضِ کاربر: «چرا کلِ حباب رو منتقل می‌کنی؟ خط به خط برش بزن».
        if os.environ.get("MANGA_TWO_IMAGE", "1") != "0":
            try:
                _cmp2 = self._compose_strip_mask(image, mask)
            except Exception:
                _cmp2 = mask
            cleaned = self._compose_two_image(cleaned, image, _cmp2)
# پولیشِ نوارها به «بعد از» سویپ‌ها منتقل شد:
# سویپ‌هایِ LaMa/TELEA بعد از پولیش، بافتِ موتیلینگ را دوباره
# روی نوارهایِ فلت‌شده می‌ریختند (شبحِ متن زنده می‌گشت).
        else:
            _cmp2 = None
        if _sdd and _sd:
            try:
                cv2.imwrite(os.path.join(_sd, "post_compose.jpg"), cleaned)
                if _probe is not None:
                    print(f"  [🔍PROBE] post_compose={cleaned[_probe[1], _probe[0]]}", flush=True)
            except Exception:
                pass

        _lama_fix = 0
        _kern_r = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        try:
            _n_res = 0
# «سریع بپاکه بره دیگ»: بعد از کامپوزِ دو-عکسی
# دیگر هیچ «نجاتِ LaMa»ای اجرا نمی‌شود (موج‌هایِ «parallel
# rescue patches» و «LaMa group rejected … منتظر می‌مونه» روی
# گوشی ۵ دقیقه معطل می‌کردند). کیفیتِ نوارها در donor، قبل
# از کامپوز تضمین شده (پرکنندهٔ فلت/LaMa + پولیشِ نوار)
# جارویِ بقایا فقط با TELEA/پرِ فلتِ سریع کار می‌کند.
# برای آزمایشِ قدیمی: MANGA_RESCUE_LAMA=1
            _rescue_lama = (os.environ.get("MANGA_RESCUE_LAMA", "0") == "1"
                            and bool(getattr(self, "use_lama", False))
                            and self._clean_level() != "fast")
            for _pass in range(3):
                _want_lama = (_pass >= 1 and _rescue_lama)
                _rboxes: List[Tuple[int, int, int, int, np.ndarray]] = []
# جاروی بقایا با «ماسکِ متنِ خام» نه ماسکِ
# کِیل‌شده: پرکننده‌هایِ فوری ماسک را کِیل می‌کنند و سویپ
# قبلاً آن ناحیه‌ها را کامل رد می‌کرد (_m_px<80) → متنِ
# قدیمیِ دست‌نخورده (نمونهٔ گوشی: «L» کنارِ «جملهٔ کوتاه»)
# هرگز پیدا نمی‌شد. ماسکِ خام = همان نوارهایِ متن.
                _mres = getattr(self, "_compose_text_mask", None)
                if _mres is None or _mres.shape != mask.shape[:2]:
                    _mres = mask
# دامنهٔ امن: فقط نوارهایِ متن (نه مستطیلِ
# بلوک) — با دامنهٔ بلوک، دیوارِ حباب «بقایایِ متن»
# خوانده می‌شد و پاک می‌شد → حباب خراب.
                _msw = getattr(self, "_compose_sweep_mask", None)
                if _msw is not None and _msw.shape == mask.shape[:2] \
                        and int(np.count_nonzero(_msw)) >= 40:
                    _mres = _msw
                _n = self._residue_sweep(
                    image, cleaned, regions, _mres,
                    collect=(_rboxes if _want_lama else None))
                if _want_lama and _rboxes:
                    _n_l = self._lama_rescue_boxes(cleaned, _rboxes, _kern_r)
                    _lama_fix += _n_l
                    if _n_l < len(_rboxes):
                        _n = _n_l + self._telea_fix_boxes(
                            cleaned, _rboxes[_n_l:])
                    else:
                        _n = _n_l
                _n_res += _n
                if not _n:
                    break
            if _n_res and self.debug:
                _how = (f"{_lama_fix} LaMa patch + "
                        f"{_n_res - _lama_fix} TELEA" if _lama_fix
                        else "TELEA rescue")
                print(f"  [*] residue sweep: {_n_res} fixes in "
                      f"{_pass + 1} passes ({_how})")
        except Exception:
            import traceback as _tb
            print("  [!] Residue sweep error:")
            _tb.print_exc()
        _stage("جارویِ پسماند")
        if _sdd and _sd:
            try:
                cv2.imwrite(os.path.join(_sd, "post_sweep.jpg"), cleaned)
            except Exception:
                pass

# جاروی لکهٔ محوِ داخلِ حباب‌هایِ سفید (halo حروف) —
# نمونهٔ کاربر: لکهٔ وسطِ «BUT I LIKE IT HERE.» / نقطهٔ «MR. JUN~»
        try:
            _n_int = self._bubble_interior_sweep(image, cleaned, regions)
            if _n_int and self.debug:
                print(f"  [*] bubble sweep: {_n_int} fixed")
        except Exception:
            import traceback as _tb
            print("  [!] Bubble interior sweep error:")
            _tb.print_exc()
        _stage("جارویِ حباب")

# «گارانتیِ کامپوزِ دوباره»: بعدازِ همهٔ سویپ‌ها/سویپ
# نجات/پولیش، خروجیِ نهایی دوباره با _compose_two_image روی
# ماسکِ «کامپوزِ خط‌به‌خط» فیلتر می‌شود. قبلاً بعضی سویپ‌ها
# (بقایا/حباب/نجات) بیرونِ نوارِ متن هم پیکسل عوض می‌کردند و
# حباب — که عکسِ اولِ خرابش به خروجی نرسیده بود — برمی‌گشت
# (نمونهٔ 01.jpg: حبابِ سفیدِ بزرگِ «THE VILLA'S POOL…»)
        try:
            if _cmp2 is not None:
# قبل از کامپوزِ نهایی: پیکسل‌هایِ قفل‌شده
# (خطِ حباب/قاب/تابِ نور) از اصل ترمیم می‌شوند تا نوارها
# بُرشِ سالم ببرند — نه سیاهیِ LaMa، نه پرشِ فوری.
# استثنا: گلیفِ تنهاِ جاافتاده (Wِ «WICKED»)
# که نقشهٔ حفاظت آن را قاب خوانده — اگر از اصل ترمیم
# شود، کامپوزِ نهایی خودِ متنِ اصلی را منتقل می‌کند!
# اجزایِ کوچکِ هم‌اندازهٔ حرفِ محافظت‌شده که داخلِ
# نوارهایِ کامپوز‌اند ترمیم «نمی‌شوند» تا پاک‌شدهٔ
# سویپ/LaMa زنده بماند. قاب/خطِ کشیده مثلِ قبل ترمیم.
                try:
                    _paf = getattr(self, "_prot_all", None)
                    if _paf is not None and int(cv2.countNonZero(_paf)):
                        _self = _paf > 0
                        try:
                            _ins = _self & (_cmp2 > 0)
                            if int(_ins.sum()) > 0:
                                _nG, _lG, _sG, _ = \
                                    cv2.connectedComponentsWithStats(
                                        _ins.astype(np.uint8), 8)
                                for _jG in range(1, _nG):
                                    _aG = int(_sG[_jG,
                                                      cv2.CC_STAT_AREA])
                                    _wG = int(_sG[_jG,
                                                      cv2.CC_STAT_WIDTH])
                                    _hG = int(_sG[_jG,
                                                      cv2.CC_STAT_HEIGHT])
                                    if _aG <= 1200 and \
                                            max(_wG, _hG) <= 90:
                                        _self &= ~(_lG == _jG)
                        except Exception:
                            pass
                        cleaned[_self] = image[_self]
                except Exception:
                    pass
                cleaned = self._compose_two_image(cleaned, image, _cmp2,
                                                 verbose=False,
                                                 refill=True)
                try:
                    _sddz = os.environ.get("MANGA_STAGE_DUMP", "")
                    if _sddz:
                        cv2.imwrite(os.path.join(
                            _sddz, "post_recompose.jpg"), cleaned)
                except Exception:
                    pass
        except Exception:
            pass
# پولیشِ نهاییِ نوارها — «بعد از» همهٔ سویپ‌ها:
# حلقهٔ کاملاً یکنواخت (حبابِ سفید/رنگیِ تخت) → کلِ نوار + ۵px
# هالهٔ دورِ آن با رنگِ اورجینالِ حلقه هم‌سطح می‌شود → شبحِ
# ۱-۳ سطحیِ متن (که سویپ‌ها نمی‌بینندش) صفر می‌شود و هیچ
# سویپی دیگر بعدش بافت نمی‌ریزد.
        if _cmp2 is not None:
            try:
                cleaned = self._compose_polish(image, cleaned, _cmp2)
            except Exception:
                pass
        #): بقایایِ نازکِ جوهر
# پولیشِ شبحِ نوار (
# که LaMa لبهٔ ماسکشان را نصفه گذاشته (خطوطِ ۱-۸px داخلِ نوار —
# تیرگیِ ~۳۵ که سویپِ ۴۵+ و همسطحیِ پولیش نمی‌بینندش) با پرِ
# پیازی از زمینهٔ تمیزِ اطراف پاک میشوند؛ فقط نوارهایِ کامپوز
# فقط اجزایِ نازکِ نزدیکِ جوهرِ متنِ اصلی و فقط حلقهٔ تخت — دیوار/
# هنر/حبابهایِ بافت‌دار هرگز دست نمیخورند. MANGA_GHOST_POLISH=0
# برایِ خاموشکردنِ دستی.
        if _cmp2 is not None \
                and os.environ.get("MANGA_GHOST_POLISH", "1") != "0":
            try:
                cleaned, _n_gp = self._strip_ghost_polish(
                    image, cleaned, _cmp2)
                if _n_gp and self.debug:
                    print(f"  [*] پولیشِ شبحِ نوار: {_n_gp} پیکسل "
                          f"پاک شد")
            except Exception:
                pass
        if _sdd and _sd:
            try:
                cv2.imwrite(os.path.join(_sd, "post_polish.jpg"), cleaned)
            except Exception:
                pass

# «پرِ پیازیِ نوارهایِ داخلِ حباب»: نوارهایِ متنِ
# داخل حباب (donor box) که پرِ LaMa رنگشان کمی غلط است
# (شبحِ سفیدِ «This is great» روی گرادیانِ آبی-سفید)، هم‌چنین
# حبابِ زردِ img1 که با TELEA سفید می‌شد (TELEA سفیدیِ شبح را
# به داخل پخش می‌کند): پیکسل‌های نوار از «پیکسل‌هایِ
# پس‌زمینهٔ اورجینالِ اطرافشان» پر می‌شوند — کامپوزِ گارانتی
# تضمین کرده هر پیکسلِ بیرونِ نوارِ داخلِ جعبه پیکسلِ
# اورجینال است. fill پیازی (هر دور، حاشیهٔ ناشناخته با
# میانگینِ همسایه‌هایِ شناخته 3×3): گرادیانِ رنگِ حباب دست
# نخورده ادامه می‌یابد و هیچ سفیدی وارد نمی‌شود. بیرونِ حباب
# (متن روی هنر) دست نمی‌خورد.
        try:
            if _cmp2 is not None:
                _instrip = (_cmp2 > 0)
                _inb = np.zeros(_instrip.shape, dtype=bool)
# «گیتِ پیازی»: پیازی فقط برایِ زمینهٔ
# تخت/گرادیانی (حباب/کارت) — جایی که donor رنگِ غلط
# گرفته. رویِ هنرِ بافت‌مند (نرده/صورت/کت — img4)
# پیازی بافتِ LaMa را به «ابر» تبدیل می‌کند
# (1.9Mpx = ۲۴٪ صفحه!). معیار: کسری از حلقهٔ
# اطرافِ جعبه که محله‌هایِ ۱۱px آن تخت است (std<12)
# باید ≥۰٫۵ باشد؛ وگرنه جعبه از پیازی مستثنا می‌شود
# و بافتِ بازسازیِ LaMa می‌ماند.
                try:
                    _gsrc = cv2.cvtColor(
                        image, cv2.COLOR_BGR2GRAY).astype(np.float32)
                    _ma = cv2.blur(_gsrc, (11, 11))
                    _msq = cv2.blur(_gsrc * _gsrc, (11, 11))
                    _std = np.sqrt(np.maximum(
                        _msq - _ma * _ma, 0))
# علاوه بر «تخت»، «بی‌لبه» هم لازم است:
# پس‌زمینهٔ بوکهٔ ساختمان/نرده محلی-تخت است ولی
# لبه‌هایِ ساختاری دارد (میلهٔ نرده، قاب پنجره) —
# پیازی آن لبه‌ها را می‌بَرد (img4 PARAGRAPH2).
# تخت + بدونِ لبه = حباب/گرادیانِ نرم → پیازی اوکی.
                    _lap = np.abs(cv2.Laplacian(
                        _gsrc, cv2.CV_32F))
                    _edgef = cv2.blur(
                        (_lap > 25.0).astype(np.float32),
                        (31, 31))
                    _flatf = ((cv2.blur(
                        (_std < 12.0).astype(np.float32),
                        (31, 31)) > 0.55)
                        & (_edgef < 0.06))
                except Exception:
                    _flatf = None
                for _dbT in (getattr(self, "_donor_boxes", None) or []):
                    _tx0, _ty0, _tx1, _ty1 = [int(v) for v in _dbT]
                    _tx0 = max(0, _tx0); _ty0 = max(0, _ty0)
                    _tx1 = min(cleaned.shape[1], _tx1)
                    _ty1 = min(cleaned.shape[0], _ty1)
                    if _tx1 - _tx0 >= 10 and _ty1 - _ty0 >= 10:
                        if _flatf is not None:
                            try:
                                _ry0, _ry1 = max(0, _ty0 - 12), min(
                                    _flatf.shape[0], _ty1 + 12)
                                _rx0, _rx1 = max(0, _tx0 - 12), min(
                                    _flatf.shape[1], _tx1 + 12)
                                _rg = np.zeros(
                                    (_ry1 - _ry0, _rx1 - _rx0),
                                    dtype=bool)
                                _rg[:, :] = _flatf[_ry0:_ry1,
                                                     _rx0:_rx1]
                                _rg[_ty0 - _ry0:_ty1 - _ry0,
                                    _tx0 - _rx0:_tx1 - _rx0] = False
                                if _rg.size < 30 or float(
                                        _rg.mean()) < 0.5:
                                    continue  # زمینهٔ بافت‌مند
                            except Exception:
                                pass
                        _inb[_ty0:_ty1, _tx0:_tx1] = True
                _sel = _instrip & _inb
                if _sel.any():
                    _known = (_inb & ~_instrip).astype(np.float32)
# «سدِ دیوار»: اگر donor یک ساختارِ تیرهٔ
# اورجینال (دورِ حباب/دُم/کادر) را *حفظ* کرده باشد
# (تیره در اورجینال ≈ تیره در خروجی)، آن پیکسل‌ها
# نباید دوباره پیازی پر شوند — وگرنه پرِ پیازی از دو
# طرفِ مرزِ سفید↔کرم قاطی می‌شود: دورِ حباب می‌شکند و
# رنگِ بیرون به داخل نشت می‌کند (نمونه: حبابِ YEP!
# img7). آن پیکسل‌ها «شناخته» با مقدارِ خودشان
# می‌مانند → هم سالم می‌مانند، هم سدِ جلوگیریِ نشت
# هستند. پیکسلِ متنِ پاک‌شده (تیره در اورجینال، روشن
# در خروجی) باز هم «ناشناخته» می‌ماند و پر می‌شود.
                    try:
                        _gO = cv2.cvtColor(
                            image, cv2.COLOR_BGR2GRAY).astype(np.float32)
                        _gC = cv2.cvtColor(
                            cleaned, cv2.COLOR_BGR2GRAY).astype(np.float32)
                        _bg = cv2.medianBlur(
                            _gO.astype(np.uint8), 31).astype(np.float32)
                        _drk = (_gO < 120.0) | (
                            (_bg - _gO) > 45.0)
                        _keep2 = cv2.dilate(
                            (_drk & (np.abs(_gC - _gO) < 22.0)
                             ).astype(np.uint8),
                            np.ones((3, 3), np.uint8)) > 0
                        _keep2 &= _sel
                        if bool(_keep2.any()):
                            _sel = _sel & (~_keep2)
                            _known = np.maximum(
                                _known,
                                _keep2.astype(np.float32))
                            if self.debug:
                                print(f"  [🛡]"
                                      f"{int(_keep2.sum())}px دیوارِ "
                                      f"حفظ‌شده = سدِ پیازی")
                    except Exception:
                        pass
                    _vals = cleaned.astype(np.float32).copy()
                    _unk = _sel.copy()
                    _it = 0
                    while int(_unk.sum()) > 0 and _it < 400:
                        _it += 1
                        _wsum = cv2.boxFilter(_known, -1, (3, 3),
                                              normalize=False)
                        _new = (_wsum > 0) & _unk
                        if not bool(_new.any()):
                            break
                        for _c in range(3):
                            _sv = cv2.boxFilter(
                                _vals[:, :, _c] * _known, -1, (3, 3),
                                normalize=False)
                            _vals[_new, _c] = (
                                _sv[_new] / _wsum[_new])
                        _known = np.maximum(_known, _new.astype(np.float32))
                        _unk &= ~_new
                    cleaned[_sel] = np.clip(
                        np.rint(_vals[_sel]), 0, 255).astype(np.uint8)
                    if self.debug:
                        print(f"  [*]پرِ پیازیِ حباب = "
                              f"{int(_sel.sum())}px ({_it} دور)")
        except Exception:
            pass

            pass

# پاسِ مرجع حذف شد — درخواستِ کاربر: «این خط خط چیه
# mm خوب می‌پاکه». پاسِ هندسی مرجع  بعد از همهٔ پاس‌ها
# روی هر خطِ OCR هیل/پرکردن انجام می‌داد و روی زمینه‌های روشن
# نوارهای افقیِ هم‌راستا با خطوطِ متن می‌ساخت (خط‌خطیِ
# اسکرین‌شاتِ کاربر: ۲۴/۲۴ خطِ heal). شاخهٔ mm این پاس را
# ندارد و کاربر تأیید کرده پاکسازیِ mm تمیز است → حذفِ کاملِ
# پاس تا خطِ لوله‌ایِ پاکسازی دقیقاً برابرِ mm بشود. خودِ تابع
# نگه داشته شده (بدونِ فراخوانی) برای استفادهٔ آزمایشی با
# MANGA_MT=1 در CLI.
        try:
            if os.environ.get("MANGA_MT", "0") == "1":
                _n_mt, _mt_how = self._mt_polygon_clean(cleaned, image,
                                                        regions)
                if _n_mt and self.debug:
                    print(f"  [*] MT polygon clean: {_n_mt} lines "
                          f"({_mt_how})")
        except Exception:
            import traceback as _tb
            print("  [!] MT polygon clean error:")
            _tb.print_exc()

# «تیکِ جامانده»: جوهرِ کوچکِ ریز (نقطهٔ !، تیکِ جدا
# خشِ کوتاه) که ماسکِ نوار ندیده بود و در خروجی دست‌نخورده ماند
# (نمونه: تیکِ 4x17 در (533,965) img7 کنارِ «ME BOMB..!»). فقط
# داخلِ نوارهایِ متن، فقط لُختهٔ کوچکِ مستقل (≤300px، جعبه≤30)
# فقط اگر در اورجینال هم بخشی از ساختارِ کوچکِ مستقل باشد (نه
# مو/هنرِ متصل) و نزدیکِ متنی که پاک شده → پیازی از اطرافِ
# خروجی پر می‌شود. «به اندازهٔ متن» — چیزی اضافه پاک نمی‌شود.
        try:
            if _cmp2 is not None and int(np.count_nonzero(_cmp2)) > 40:
                _gO = cv2.cvtColor(
                    image, cv2.COLOR_BGR2GRAY).astype(np.float32)
                _gC = cv2.cvtColor(
                    cleaned, cv2.COLOR_BGR2GRAY).astype(np.float32)
                _bgc = cv2.medianBlur(
                    _gO.astype(np.uint8), 31).astype(np.float32)
                _inkO = (_gO < 120.0) | ((_bgc - _gO) > 45.0)
# نوارِ گشادشده: تیکِ ندیده‌شده *داخلِ* ماسک نیست ولی در
# باندِ همان خطِ متن است
                _zonec = cv2.dilate(
                    _cmp2, cv2.getStructuringElement(
                        cv2.MORPH_ELLIPSE, (25, 25))) > 0
                _unch = _inkO & _zonec & (
                    np.abs(_gC - _gO) < 18.0)
                _nA, _labA, _stA, _ = cv2.connectedComponentsWithStats(
                    _unch.astype(np.uint8), 8)
                _nB, _labB = cv2.connectedComponents(
                    _inkO.astype(np.uint8), 8)
                _fix_m = np.zeros(_unch.shape, dtype=bool)
                _n_ok = 0
                for _ci in range(1, _nA):
                    if _n_ok >= 6 or int(np.count_nonzero(
                            _fix_m)) > 1200:
                        break
                    _aA = int(_stA[_ci, cv2.CC_STAT_AREA])
                    _wA = int(_stA[_ci, cv2.CC_STAT_WIDTH])
                    _hA = int(_stA[_ci, cv2.CC_STAT_HEIGHT])
                    if _aA > 300 or _wA > 30 or _hA > 30 or _aA < 6:
                        continue
                    _cyb = int(_stA[_ci, cv2.CC_STAT_TOP]) \
                        + max(0, int(_hA) // 2)
                    _cxb = int(_stA[_ci, cv2.CC_STAT_LEFT]) \
                        + max(0, int(_wA) // 2)
                    _lbB = int(_labB[_cyb, _cxb])
                    if _lbB <= 0:
                        continue
                    _mB = (_labB == _lbB)
                    if int(np.count_nonzero(_mB)) > 400:
                        continue  # به ساختارِ بزرگِ هنر وصل است
                    _ys, _xs = np.where(_mB)
                    _bx0, _bx1 = int(_xs.min()), int(_xs.max()) + 1
                    _by0, _by1 = int(_ys.min()), int(_ys.max()) + 1
                    _pad = 22
                    _vx0, _vx1 = max(0, _bx0 - _pad), min(
                        cleaned.shape[1], _bx1 + _pad)
                    _vy0, _vy1 = max(0, _by0 - _pad), min(
                        cleaned.shape[0], _by1 + _pad)
                    _win_cleaned = ((_inkO[_vy0:_vy1, _vx0:_vx1])
                                    & (_zonec[_vy0:_vy1, _vx0:_vx1])
                                    & ~_unch[_vy0:_vy1, _vx0:_vx1])
                    if int(np.count_nonzero(_win_cleaned)) < 30:
                        continue  # متنِ همسایه پاک نشده → بخشی از آن متن
# زمینهٔ اطراف در اورجینال باید روشن و یکنواخت باشد
# (حباب/کادر) — نه بافتِ اسکرین‌تون/هنرِ پرنقطه
                    _ry0, _ry1 = max(0, _by0 - 7), min(
                        image.shape[0], _by1 + 7)
                    _rx0, _rx1 = max(0, _bx0 - 7), min(
                        image.shape[1], _bx1 + 7)
                    _ring3 = ~cv2.dilate(
                        _mB.astype(np.uint8),
                        np.ones((5, 5), np.uint8)).astype(bool)
                    _ring3[:_ry0, :] = False
                    _ring3[_ry1:, :] = False
                    _ring3[:, :_rx0] = False
                    _ring3[:, _rx1:] = False
                    _rgv = _gC[_ring3]  # 2 — زمینه از
# «خروجیِ پاک‌شده» نه اورجینال؛ وگرنه گلیف‌های
# اطرافِ متن std را منفجر می‌کنند و تیکِ واقعی
# رد می‌شد. اسکرین‌تون/هنر در خروجی هم ناهموار
# می‌ماند → باز هم رد می‌شود.
                    if _rgv.size < 40 or float(
                            np.median(_rgv)) < 150.0 or float(
                            np.std(_rgv)) > 34.0:
                        continue
                    _fix_m |= _mB
                    _n_ok += 1
                if bool(_fix_m.any()):
                    _knownM = (~_fix_m).astype(np.float32)
                    _valsM = cleaned.astype(np.float32).copy()
                    _unkM = _fix_m.copy()
                    _itM = 0
                    while bool(_unkM.any()) and _itM < 200:
                        _itM += 1
                        _wsumM = cv2.boxFilter(
                            _knownM, -1, (3, 3), normalize=False)
                        _newM = (_wsumM > 0) & _unkM
                        if not bool(_newM.any()):
                            break
                        for _cM in range(3):
                            _svM = cv2.boxFilter(
                                _valsM[:, :, _cM] * _knownM, -1, (3, 3),
                                normalize=False)
                            _valsM[_newM, _cM] = (
                                _svM[_newM] / _wsumM[_newM])
                        _knownM = np.maximum(
                            _knownM, _newM.astype(np.float32))
                        _unkM &= ~_newM
                    cleaned[_fix_m] = np.clip(
                        np.rint(_valsM[_fix_m]), 0, 255).astype(np.uint8)
                    if self.debug:
                        print(f"  [*]{int(_fix_m.sum())}px "
                              f"تیکِ جامانده پاک شد ({_itM} دور)")
        except Exception:
            pass

        if self.debug:
            print(f"  - Cleanup: {counts}")
# وارسیِ نهاییِ ضدِ خرابیِ EP (یک‌بار برای کلِ صفحه):
# خروجیِ ناقص/کثیفِ LaMa رویِ GPUهایِ ویندوزی (CUDA/DML) را روی
# نواحیِ پاک‌شده می‌سنجد و پلکانی ترمیم می‌کند
        try:
            self._final_verify_repair(cleaned, image)
        except Exception:
            pass
        try:
            _pp = os.environ.get("MANGA_PROBE_REPAIR", "")
            if _pp and getattr(self, "_probe_repair_pts", None):
                for (_px, _py) in self._probe_repair_pts:
                    cv2.imwrite(f"{_pp}_end_{_px}_{_py}.png",
                                cleaned[max(0, _py - 200):_py + 200,
                                        max(0, _px - 200):_px + 200].copy())
                    print(f"  [PROBE] end-of-clean @{_px},{_py} "
                          f"val={cleaned[_py, _px]}", flush=True)
        except Exception:
            pass
# QCِ پایانیِ هماهنگیِ پر (بعد از همهٔ سویپها).
# درِ تستِ img4 همین پاس بود که نوارهایِ خاکستریِ باقیماندهٔ
# r20/#13/#16 را سفید کرد (۱۷ قطعه/۴۳۳هزارpx) — قطعاتِ بعد از
# سویپها بزرگترند (مرزهایِ ساختاریِ σ4) و حلقهشان پاکتر.
# با MANGA_HQC_FINAL=0 خاموش میشود.
        if os.environ.get("MANGA_HQC_FINAL", "1") == "1" \
                and os.environ.get("MANGA_NO_HQC", "0") != "1":
            try:
                _zq = getattr(self, "_compose_final_cmp", None)
                if not isinstance(_zq, np.ndarray) \
                        or _zq.ndim < 2 or not bool(_zq.any()):
                    _zq = _cmp2
                if isinstance(_zq, np.ndarray) and _zq.any():
                    self._fill_harmony_qc(cleaned, image, _zq,
                                          verbose=self.debug or True)
                    _hqcd = os.environ.get("MANGA_HQC_DUMP", "")
                    if _hqcd:
                        cv2.imwrite(_hqcd, cleaned)
                        cv2.imwrite(_hqcd + ".zone.png",
                                    (_zq.astype(np.uint8)) * 255)
                        print(f"  [*] HQC dump -> {_hqcd}", flush=True)
            except Exception:
                pass
        # نمونهٔ img4:
# جارویِ متنِ جاماندهٔ خوانا (
# «…COUNSELING SESSION» رویِ کت، بیرونِ نوارِ ماسک).
        if os.environ.get("MANGA_NO_LEFTOVER", "0") != "1":
            try:
                self._leftover_text_sweep(cleaned, image, _cmp2, regions)
            except Exception:
                pass
# جارویِ خرده‌گلیف/نقطه‌هایِ جاماندهٔ داخلِ ناحیه
# .
        if os.environ.get("MANGA_DOT_SWEEP", "1") != "1":
            pass
        else:
            try:
                self._compose_dot_sweep(cleaned, image, _cmp2, regions,
                                        verbose=self.debug)
            except Exception:
                pass
# قراردادِ دو-عکسی — تضمینِ نهایی: عکسِ دوم (خروجی) فقط درِ
# «نوارهایِ خط‌به‌خطِ پاک‌شده + جاهایی که جاروها پاک کردند»
# پیکسلِ عوض‌شده دارد؛ هر پیکسلِ دیگر، حتی اگر پرکننده/سویپی
# اشتباهاً نوشته باشد، از عکسِ اصلی برمیگردد. جاروها هم فقط
# داخلِ همین مجموعه اثر میگذارند (مسیرِ دیگری برای ویرایشِ
# عکسِ دوم باز نیست).
        try:
            if _cmp2 is not None:
                _extras = getattr(self, "_sweep_fix_mask", None)
                _extra_u8 = None
                _m_final = _cmp2
                if _extras is not None and _extras.shape == _cmp2.shape \
                        and bool(_extras.any()):
                    _extra_u8 = _extras.astype(np.uint8) * 255
                    _m_final = ((_cmp2 > 0) | _extras).astype(np.uint8) * 255
                cleaned = self._compose_two_image(
                    cleaned, image, _m_final, verbose=False, refill=True,
                    extra=_extra_u8)
                if self.debug:
                    print("  [✓] قراردادِ دو-عکسی: بیرونِ نوارهایِ "
                          "پاک‌شده = پیکسلِ اورجینال (تضمینِ نهایی)")
        except Exception:
            pass
        return cleaned

    def _compose_dot_sweep(self, cleaned: np.ndarray,
                           original: np.ndarray,
                           zone: Optional[np.ndarray],
                           regions: List[TextRegion],
                           verbose: bool = True) -> int:
        """ — جارویِ خرده‌گلیف/نقطه‌هایِ جاماندهٔ داخلِ ناحیه.

        ریشه (img6 — حبابِ زردِ بالا + حباب‌هایِ سفید): تکههایِ
        دورخط/ضدآلیاسِ حروف که بیرونِ نوارهایِ کامپوز ماندند =
        «نقطه‌نقطهٔ سیاه جایِ هر متن». پسگیرِ جوهر گاردهایش (لبهٔ
        پنجره/سقفِ جرم/باند) بعضی را رد میکند و جارویِ خوانا فقط
        متنِ قابلِOCR را میگیرد. اینجا بعد از کامپوز، داخلِ مستطیلِ
        هر ناحیهٔ متنی، قطعههایِ گلیف‌مانندِ «تیره روی زمینهٔ روشنِ
        تخت» که در زونِ کامپوز نیستند و به مرزِ ناحیه نمیچسبند با
        TELEA پاک میشوند — هنرِ بیرونِ ناحیه و دیوارِ حباب (مرز)
        هرگز دستنخورده میمانند."""
        n_fix = 0
        n_px = 0
        try:
            if cleaned is None or original is None:
                return 0
            if cleaned.shape[:2] != original.shape[:2]:
                return 0
            h, w = cleaned.shape[:2]
            _zm = None
            if isinstance(zone, np.ndarray) and zone.shape == (h, w):
                _zm = (zone > 0)
            for r in (regions or []):
                try:
                    if getattr(r, "kind", "") in ("promo", "sfx"):
                        continue
                    _polys = getattr(r, "ocr_polys", None) or []
                    if not _polys:
                        continue
                    rx, ry, rw, rh = [int(v) for v in r.rect]
                    x0 = max(0, rx - 4)
                    y0 = max(0, ry - 4)
                    x1 = min(w, rx + rw + 5)
                    y1 = min(h, ry + rh + 5)
                    if x1 - x0 < 48 or y1 - y0 < 32:
                        continue
# بلندیِ میانهٔ خط برایِ سقفهایِ سازگار
                    try:
                        _pl = []
                        for p in _polys:
                            _pp = np.asarray(p, np.float32).reshape(-1, 2)
                            if _pp.shape[0] >= 3:
                                _pl.append(_pp)
                        _ln = MangaTranslator._group_polys_to_lines(_pl)
                        if not _ln:
                            continue
                        med_h = float(np.median([b[3] - b[1] for b in _ln]))
                    except Exception:
                        continue
                    if med_h < 8.0:
                        continue
                    _hh_max = max(64.0, 1.15 * med_h + 4.0)
                    _a_max = max(2600.0, 0.60 * med_h * med_h)
                    _ww_max = max(180.0, 2.6 * med_h)
                    sub = cleaned[y0:y1, x0:x1]
                    g = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
                    ex = np.zeros(g.shape, bool)
                    if _zm is not None:
                        ex = _zm[y0:y1, x0:x1]
# آمارِ زمینه از «زونِ تمیز» (بیرونِ نوارها) — ولی
# شکارِ جوهر رویِ «کلِ برش»: خرده‌لکه‌ها هم بیرونِ
# نوار ماندند (نقطهٔ جامانده) هم داخلِ نوار (لکهٔ
# خودِ پرکنندهٔ donor) — هر دو باید پاک شوند
                    exd = cv2.dilate(
                        ex.astype(np.uint8),
                        np.ones((3, 3), np.uint8)) > 0
                    bg = ~exd
                    nbg = int(bg.sum())
                    if nbg < 400:
                        continue
                    med = float(np.median(g[bg]))
                    if med < 150.0:
                        continue
                    ink = (g.astype(np.int16) < (med - 40.0))
                    ink_n = int((ink & bg).sum())
                    if ink_n < 4 or ink_n > 0.20 * nbg:
                        continue
                    _lite = (bg & ~cv2.dilate(
                        (ink & bg).astype(np.uint8),
                        np.ones((13, 13), np.uint8)).astype(bool))
                    if int(_lite.sum()) < 200:
                        continue
                    if float(np.std(g[_lite])) > 52.0:
                        continue  # زمینهٔ بافت‌دار/هنر — دخالت ممنوع
                    nl, lab, st, _ = cv2.connectedComponentsWithStats(
                        ink.astype(np.uint8), 8)
                    gm = np.zeros(g.shape, np.uint8)
                    n_g = 0
                    _sub_h, _sub_w = g.shape[:2]
                    for i in range(1, nl):
                        a = int(st[i, cv2.CC_STAT_AREA])
                        hh = int(st[i, cv2.CC_STAT_HEIGHT])
                        ww = int(st[i, cv2.CC_STAT_WIDTH])
                        if a < 4 or a > _a_max or hh < 2 or hh > _hh_max \
                                or ww > _ww_max:
                            continue
# چسبیده به مرزِ برش = دیوار/ساختور — دست نزن
                        _cx = int(st[i, cv2.CC_STAT_LEFT])
                        _cy = int(st[i, cv2.CC_STAT_TOP])
                        if _cx <= 1 or _cy <= 1 \
                                or _cx + ww >= _sub_w - 1 \
                                or _cy + hh >= _sub_h - 1:
                            continue
                        _cm = (lab == i)
# داخلِ نوارِ کامپوز = لکهٔ خودِ پرکننده — فقط
# خرده‌لکهٔ ریز مجاز (نه تکهٔ بزرگِ احتمالیِ هنر)
                        if bool((_cm & ex).any()):
                            if a > 300 or ww > 64 or hh > 44:
                                continue
                        gm[_cm] = 255
                        n_g += 1
                    if n_g <= 0:
                        continue
                    if int(cv2.countNonZero(gm)) < 4:
                        continue
# پاسِ دوم — فقط «داخلِ نوارها»: رگه‌های خاکستریِ
# ملایمِ پرکنندهٔ donor (۲۵..۴۰ زیرِ زمینه) که با
# آستانهٔ اصلی رد شدند («خطوطِ محو»)
                    try:
                        _ink2 = (g.astype(np.int16) < (med - 26.0)) \
                            & ex & (~cv2.dilate(
                                ink.astype(np.uint8),
                                np.ones((3, 3), np.uint8)).astype(bool))
                        n2, l2, s2, _ = cv2.connectedComponentsWithStats(
                            _ink2.astype(np.uint8), 8)
                        for i2 in range(1, n2):
                            a2 = int(s2[i2, cv2.CC_STAT_AREA])
                            h2 = int(s2[i2, cv2.CC_STAT_HEIGHT])
                            w2 = int(s2[i2, cv2.CC_STAT_WIDTH])
                            if a2 < 6 or a2 > 420 or h2 > 40 or w2 > 130:
                                continue
                            _c2x = int(s2[i2, cv2.CC_STAT_LEFT])
                            _c2y = int(s2[i2, cv2.CC_STAT_TOP])
                            if _c2x <= 1 or _c2y <= 1 \
                                    or _c2x + w2 >= _sub_w - 1 \
                                    or _c2y + h2 >= _sub_h - 1:
                                continue
                            gm[l2 == i2] = 255
                            n_g += 1
                    except Exception:
                        pass
                    gm = cv2.dilate(gm, np.ones((3, 3), np.uint8))
                    sub_fix = cv2.inpaint(sub, gm, 3, cv2.INPAINT_TELEA)
                    _m = gm > 0
                    sub[_m] = sub_fix[_m]
                    try:
                        _fm = np.zeros((h, w), bool)
                        _fm[y0:y1, x0:x1] = _m
                        self._sweep_fix_record(_fm)
                    except Exception:
                        pass
                    n_fix += n_g
                    n_px += int(cv2.countNonZero(gm))
                    if verbose:
                        try:
                            print(f"  [✓گلیف] جارویِ خرده‌گلیف: ناحیهٔ "
                                  f"{getattr(r, 'id', '?')} — {n_g} قطعه "
                                  f"({int(cv2.countNonZero(gm))}px) TELEA شد")
                        except Exception:
                            pass
                except Exception:
                    continue
            if verbose and n_fix:
                try:
                    print(f"  [✓گلیف] جارویِ خرده‌گلیف: {n_fix} قطعه / "
                          f"{n_px}px در {len(regions or [])} ناحیه")
                except Exception:
                    pass
            return n_fix
        except Exception:
            return 0

    def _leftover_text_sweep(self, cleaned: np.ndarray,
                             original: np.ndarray,
                             zone: Optional[np.ndarray],
                             regions: List[TextRegion],
                             verbose: bool = True) -> int:
        """ — جارویِ متنِ جاماندهٔ خوانا با گیتِ OCR.

        OCR رویِ خروجیِ پاکشده؛ هر خطِ لاتینِ بااطمینان (≥۰٫۷۲) که
        ≥۴۰٪ آن داخلِ «زونِ مجاز» (نوارِ کامپوز + مستطیلهایِ ناحیه
        با پدِ ۴px) باشد و درِ اصلِ همان‌جا جوهرِ متن داشته → پیکسلهایِ
        «پاکنشده» (همانِ اصل، |Δ|≤۲۰) با TELEA پاک میشوند. متنِ هنریِ
        بیرونِ نواحی (SFX/تابلو/کاغذِ دکور) هرگز دستنخورده میماند و
        هیچ نوشتنی بیرونِ زون نمیرود.
        """
        n_fix = 0
        n_px = 0
        try:
            if cleaned is None or original is None:
                return 0
            if cleaned.shape[:2] != original.shape[:2]:
                return 0
            h, w = cleaned.shape[:2]
            ok = np.zeros((h, w), bool)
            if zone is not None and zone.shape == (h, w):
                ok |= (zone > 0)
            for r in (regions or []):
                try:
                    rx, ry, rw, rh = [int(v) for v in r.rect]
                except Exception:
                    continue
                _x0 = max(0, rx - 4)
                _y0 = max(0, ry - 4)
                _x1 = min(w, rx + rw + 5)
                _y1 = min(h, ry + rh + 5)
                if _x1 > _x0 and _y1 > _y0:
                    ok[_y0:_y1, _x0:_x1] = True
            if not ok.any():
                return 0
            try:
                _res = self.ocr.ocr(cleaned)
            except Exception:
                return 0
            if not _res or not _res[0]:
                return 0
            go = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
            gc = cv2.cvtColor(cleaned, cv2.COLOR_BGR2GRAY)
            same = (np.abs(gc.astype(np.int16)
                           - go.astype(np.int16)) <= 20)
            _ker3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            _k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            for _ln in (_res[0] or []):
                try:
                    box = np.asarray(_ln[0], np.float32).reshape(-1, 2)
                    _tv = _ln[1]
                    if isinstance(_tv, (tuple, list)):
                        txt = str(_tv[0]) if len(_tv) > 0 else ""
                        sc = float(_tv[1]) if len(_tv) > 1 else 0.0
                    else:
                        txt = str(_tv)
                        sc = 0.0
                except Exception:
                    continue
                t = txt.strip()
                if len(t) < 3 or sc < 0.72:
                    continue
                if not re.search(r"[A-Za-z]{3,}", t):
                    continue
                bx0 = int(max(0, np.floor(box[:, 0].min())) - 2)
                by0 = int(max(0, np.floor(box[:, 1].min())) - 2)
                bx1 = int(min(w, np.ceil(box[:, 0].max())) + 3)
                by1 = int(min(h, np.ceil(box[:, 1].max())) + 3)
                if bx1 - bx0 < 12 or by1 - by0 < 10:
                    continue
                sub_ok = ok[by0:by1, bx0:bx1]
                if float(sub_ok.mean()) < 0.40:
                    continue  # متنِ هنریِ بیرونِ نواحی
                sub_go = go[by0:by1, bx0:bx1]
                sub_same = same[by0:by1, bx0:bx1]
                _med = float(np.median(sub_go))
                _inko = ((sub_go < _med - 45.0)
                         | (sub_go > min(232.0, _med + 45.0)))
# درِ اصل باید جوهرِ متن بوده باشد (≥۴٪)
                if float(_inko.mean()) < 0.04:
                    continue
                resid = (_inko & sub_same & sub_ok)
                resid = cv2.morphologyEx(
                    resid.astype(np.uint8), cv2.MORPH_OPEN, _ker3) > 0
                resid = cv2.dilate(resid.astype(np.uint8), _k5) > 0
                resid &= sub_ok
                _np = int(resid.sum())
                if _np < 40:
                    continue
                _m = np.zeros((h, w), np.uint8)
                _m[by0:by1, bx0:bx1] = resid.astype(np.uint8) * 255
                _patch = cv2.inpaint(cleaned, _m, 4, cv2.INPAINT_TELEA)
                cleaned[resid] = _patch[resid]
                self._sweep_fix_record(resid)
                n_fix += 1
                n_px += _np
            if n_fix and verbose:
                try:
                    print(f"  [✓جارو] جارویِ متنِ جامانده: {n_fix} خط "
                          f"پاک شد ({n_px}px)", flush=True)
                except Exception:
                    pass
            return n_fix
        except Exception:
            return n_fix

    def _residue_sweep(self, image: np.ndarray, cleaned: np.ndarray,
                       regions: List[TextRegion],
                       mask: Optional[np.ndarray] = None,
                       collect: Optional[List[Tuple[int, int, int, int,
                                               np.ndarray]]] = None) -> int:
        n_fix = 0
        try:
            h, w = cleaned.shape[:2]
        except Exception:
            return 0
        if mask is None or mask.shape != (h, w):
            try:
                mask = self._build_text_mask(image, regions)
            except Exception:
                return 0
            if mask is None or mask.shape != (h, w):
                return 0
        try:
            _mdil = (cv2.dilate(mask, cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (15, 15))) > 0)
        except Exception:
            _mdil = (mask > 0)
        for r in regions:
            try:
                x, y, rw, rh = [int(v) for v in r.rect]
            except Exception:
                continue
            x0, y0 = max(0, x), max(0, y)
            x1, y1 = min(w, x + rw), min(h, y + rh)
            if x1 - x0 < 12 or y1 - y0 < 12:
                continue
            oc = image[y0:y1, x0:x1]
            cc = cleaned[y0:y1, x0:x1]
            if oc.size == 0 or cc.shape != oc.shape:
                continue
            g = cv2.cvtColor(oc, cv2.COLOR_BGR2GRAY)
            med = float(np.median(g))
            thr = max(70.0, med - 60.0)
            ink = (g < thr)
            if med < 205.0:
                _thr_b = min(232.0, med + 60.0)
                _br = (g > _thr_b)
                if float(_br.mean()) <= 0.35:
                    ink = (ink | _br)
            _ir = float(ink.mean())
            if _ir < 0.005 or _ir > 0.50:
                continue
            _mzone = _mdil[y0:y1, x0:x1]
            _m_px = int(np.count_nonzero(_mzone))
            if _m_px < 80:
                continue
            gc = cv2.cvtColor(cc, cv2.COLOR_BGR2GRAY)
            same = (np.abs(gc.astype(np.int16) - g.astype(np.int16)) <= 14)
            _mcore = (mask[y0:y1, x0:x1] > 0)
            resid = ink & same & _mcore
            try:
                _zp = cc[_mcore].astype(np.float32)
                _zlum = (_zp[:, 0] * 0.114 + _zp[:, 1] * 0.587 + _zp[:, 2] * 0.299)
                if _zlum.size >= 300 and float((_zlum >= 170.0).mean()) >= 0.30:
                    _bg_lum = float(np.median(_zlum[_zlum >= 170.0]))
                    _gcl = (gc.astype(np.float32) * _mcore
                            + np.where(_mcore, 0.0, _bg_lum))
                    _dark_raw = (_gcl < _bg_lum - 45.0) & _mcore & ink
                    _k5 = np.ones((5, 5), np.uint8)
                    _blob = cv2.morphologyEx(
                        _dark_raw.astype(np.uint8), cv2.MORPH_OPEN, _k5) > 0
                    _band = cv2.dilate(
                        _blob.astype(np.uint8),
                        cv2.getStructuringElement(
                            cv2.MORPH_ELLIPSE, (31, 31))) > 0
                    resid = resid | _blob | (_dark_raw & _band)
# بقایایِ جوهرِ «بیرونِ» ماسکِ هسته (مثلاً
# آپاستروف/کامایِ بینِ نوارهایِ خط — نمونهٔ گوشی: مارکِ
# کنارِ «جملهٔ کوتاه») رویِ زمینهٔ تختِ روشنِ حباب:
# داخلِ مستطیلِ ناحیه (بدونِ حاشیهٔ ۱۲px که کادرِ حباب
# است) هم جارو می‌شود — فقط رویِ زمینهٔ تختِ روشن که
# آسیب به هنر ممکن نیست.
                    try:
                        _er = 12
                        _rh, _rw = _mcore.shape
                        if _rh > 2 * _er + 8 and _rw > 2 * _er + 8:
                            _ri = np.zeros((_rh, _rw), dtype=bool)
                            _ri[_er:_rh - _er, _er:_rw - _er] = True
                            _dark2 = ((gc.astype(np.int16)
                                       < int(_bg_lum) - 45.0)
                                      & _ri & ink)
                            _blob2 = cv2.morphologyEx(
                                _dark2.astype(np.uint8), cv2.MORPH_OPEN,
                                _k5) > 0
# باگِ «متنِ کج یا ناقص»: قوسِ دیوارِ
# حباب/خطِ کادرِ پنلِ بیرونِ ماسک، «بقایایِ جوهر»
# خوانده می‌شد و جارو می‌شد (قوسِ ناپدیدشده).
# ساختار = کامپوننتِ کشیدهٔ افقی (عریضِ ≥۱۰۰px و
# ≥۲.۵ برابرِ بلندی‌اش). بقایایِ واقعیِ متن =
# قطعه‌هایِ حرفیِ کوچک/فشرده — رد نمی‌شوند.
                            if float(_blob2.mean()) <= 0.10:
                                try:
                                    _nz2, _lb2, _st2, _ = \
                                        cv2.connectedComponentsWithStats(
                                            _blob2.astype(np.uint8), 8)
                                    _ok2 = np.zeros_like(_blob2)
                                    for _i2 in range(1, _nz2):
                                        _cw2 = int(_st2[_i2,
                                                       cv2.CC_STAT_WIDTH])
                                        _ch2 = int(_st2[_i2,
                                                        cv2.CC_STAT_HEIGHT])
                                        if _cw2 >= 100 \
                                                and _cw2 >= 2.5 * max(1, _ch2):
                                            continue
                                        _ok2 |= (_lb2 == _i2)
                                    resid = resid | _ok2
                                except Exception:
                                    resid = resid | _blob2
                    except Exception:
                        pass
            except Exception:
                pass
            if r.kind == "dialogue" and not getattr(r, "ocr_empty", False):
                try:
                    _bx, _by = max(0, x0 - 34), max(0, y0 - 34)
                    _bx2 = min(w, x1 + 34)
                    _by2 = min(h, y1 + 34)
                    if _bx2 - _bx < 20 or _by2 - _by < 20:
                        continue
                    _dseed = ((_mdil[_by:_by2, _bx:_bx2] > 0)
                              .astype(np.uint8) * 255)
                    _ddom = self._bubble_domain_local(
                        image[_by:_by2, _bx:_bx2], _dseed,
                        rect_box=(x0 - _bx, y0 - _by,
                                  x1 - x0, y1 - y0))
                    _paper_mode = False
                    if _ddom is None:
                        try:
                            _hc = cv2.cvtColor(
                                image[_by:_by2, _bx:_bx2],
                                cv2.COLOR_BGR2HSV)
                            _frac = float(((_hc[..., 2] >= 170.0)
                                           & (_hc[..., 1] <= 60.0)).mean())
                            if _frac >= 0.70:
                                _paper_mode = True
                        except Exception:
                            _paper_mode = False
                    if _ddom is None and not _paper_mode:
                        continue
                except Exception:
                    continue
                try:
                    _sp = getattr(r, "ocr_polys", None) or []
                    _spl = [np.asarray(p, dtype=np.float32).reshape(-1, 2)
                            for p in _sp if np.asarray(p).size >= 6]
                    _spl = [p for p in _spl if p.shape[0] >= 3]
                    if _spl:
                        _spts = np.concatenate(_spl, axis=0)
                        _sx0, _sx1 = float(_spts[:, 0].min()), float(_spts[:, 0].max())
                        _sy0, _sy1 = float(_spts[:, 1].min()), float(_spts[:, 1].max())
                        _sdims = [max(8.0, float(min(
                            p[:, 0].max() - p[:, 0].min(),
                            p[:, 1].max() - p[:, 1].min()))) for p in _spl]
                        _gz = max(20.0, 2.0 * float(np.median(_sdims)))
                        _ax0 = float(x0) if _paper_mode else max(float(x0), _sx0 - _gz)
                        _ay0 = max(float(y0), _sy0 - _gz)
                        _ax1 = float(x1) if _paper_mode else min(float(x1), _sx1 + _gz)
                        _ay1 = min(float(y1), _sy1 + _gz)
                        if _ax1 - _ax0 >= 20 and _ay1 - _ay0 >= 20:
                            _lx0, _ly0 = int(_ax0 - x0), int(_ay0 - y0)
                            _lx1, _ly1 = int(_ax1 - x0), int(_ay1 - y0)
                            _zmed = float(np.median(g[_ly0:_ly1, _lx0:_lx1]))
                            _zthr = _zmed - 45.0
                            _zin = ((g[_ly0:_ly1, _lx0:_lx1] < _zthr)
                                    & ~_mdil[_ly0:_ly1, _lx0:_lx1])
                            if 0.002 <= float(_zin.mean()) <= 0.40:
                                try:
                                    _wx0 = max(0, int(x0) - 120)
                                    _wy0 = max(0, int(y0) - 120)
                                    _wx1 = min(w, int(x1) + 120)
                                    _wy1 = min(h, int(y1) + 120)
                                    _wg = cv2.cvtColor(
                                        image[_wy0:_wy1, _wx0:_wx1],
                                        cv2.COLOR_BGR2GRAY)
                                    _wdark = (_wg < _zthr).astype(np.uint8)
                                    _wnz, _wlab, _wst, _ = \
                                        cv2.connectedComponentsWithStats(
                                            _wdark, 8)
                                    _wh, _ww = _wdark.shape
                                    _wgood = np.zeros((_wh, _ww), dtype=bool)
                                    for _wi in range(1, _wnz):
                                        _wa = int(_wst[_wi, cv2.CC_STAT_AREA])
                                        if _wa < 24:
                                            continue
                                        _wxp = int(_wst[_wi, cv2.CC_STAT_LEFT])
                                        _wyp = int(_wst[_wi, cv2.CC_STAT_TOP])
                                        _wwd = int(_wst[_wi, cv2.CC_STAT_WIDTH])
                                        _wht = int(_wst[_wi, cv2.CC_STAT_HEIGHT])
                                        if _wxp <= 0 or _wyp <= 0 \
                                                or _wxp + _wwd >= _ww \
                                                or _wyp + _wht >= _wh:
                                            continue
                                        if _wwd > 0.60 * _ww \
                                                or _wht > 0.60 * _wh:
                                            continue
                                        if _wa / float(max(1, _wwd * _wht)) < 0.22:
                                            continue
                                        _wgood[_wlab == _wi] = True
                                    _gxo = int(x0) + _lx0 - _wx0
                                    _gyo = int(y0) + _ly0 - _wy0
                                    _subg = _wgood[
                                        _gyo:_gyo + (_ly1 - _ly0),
                                        _gxo:_gxo + (_lx1 - _lx0)]
                                    if _subg.shape == (_ly1 - _ly0,
                                                       _lx1 - _lx0):
                                        _zin = _zin & _subg
                                except Exception:
                                    pass
                                _nz, _lab, _st, _ce = cv2.connectedComponentsWithStats(
                                    _zin.astype(np.uint8), 8)
                                _zh, _zw = _zin.shape
                                _keep = np.zeros((_zh, _zw), dtype=bool)
                                for _ci in range(1, _nz):
                                    _ca = int(_st[_ci, cv2.CC_STAT_AREA])
                                    if _ca < 24 or _ca > 0.06 * _zw * _zh:
                                        continue
                                    _cx = int(_st[_ci, cv2.CC_STAT_LEFT])
                                    _cy = int(_st[_ci, cv2.CC_STAT_TOP])
                                    _cw = int(_st[_ci, cv2.CC_STAT_WIDTH])
                                    _ch = int(_st[_ci, cv2.CC_STAT_HEIGHT])
                                    if _ca / float(max(1, _cw * _ch)) < 0.30:
                                        continue
# ساختارِ کشیدهٔ نازک (قوسِ
# دیوار/کادر) بقایایِ متن نیست
                                    if _cw >= 100 and _cw >= 2.5 * max(1, _ch):
                                        continue
                                    _touch = ((_cx <= 0) + (_cy <= 0)
                                              + (_cx + _cw >= _zw)
                                              + (_cy + _ch >= _zh))
                                    if _touch >= 2:
                                        continue
                                    if _cw > 0.75 * _zw or _ch > 0.75 * _zh:
                                        continue
                                    _keep |= (_lab == _ci)
                                _same3 = (same[_ly0:_ly1, _lx0:_lx1] & _keep)
                                _n3 = int(np.count_nonzero(_same3))
                                _ink_n = int(np.count_nonzero(
                                    g[_ly0:_ly1, _lx0:_lx1] < _zthr))
                                if 30 <= _n3 <= max(60, int(0.35 * max(1, _ink_n))):
                                    _res3 = np.zeros_like(resid)
                                    _res3[_ly0:_ly1, _lx0:_lx1] = _same3
                                    resid = resid | _res3
                except Exception:
                    pass
            try:
                _gx0, _gy0 = max(0, x0 - 34), max(0, y0 - 34)
                _gx1, _gy1 = min(w, x1 + 34), min(h, y1 + 34)
                if _gx1 - _gx0 >= 20 and _gy1 - _gy0 >= 20:
                    _gseed = ((_mdil[_gy0:_gy1, _gx0:_gx1] > 0)
                              .astype(np.uint8) * 255)
                    _ggray = cv2.cvtColor(
                        image[_gy0:_gy1, _gx0:_gx1], cv2.COLOR_BGR2GRAY)
                    _dom = self._bubble_domain_local(
                        image[_gy0:_gy1, _gx0:_gx1], _gseed)
# اعتبارسنجیِ دیوار — دامینِ کاذب (موی/سایهٔ
# شخصیت کنارِ حباب) دیوارِ تیرهٔ دورِ خودش ندارد →
# کلِ شاخه رد شود وگرنه بقایایِ موی/گونه resid می‌شوند
# و LaMa-rescue روی صورت لکه می‌سازد
                    if _dom is not None and cv2.countNonZero(_dom) > 0:
                        try:
                            _dr = (cv2.dilate(_dom, np.ones((7, 7), np.uint8))
                                   > 0) & (_dom == 0)
                            if int(np.count_nonzero(_dr)) >= 30:
                                _g_in = float(np.median(_ggray[_dom > 0]))
                                _g_rg = float(np.median(_ggray[_dr]))
                                if _g_rg > _g_in - 40.0:
                                    _dom = None
                        except Exception:
                            pass
                    if _dom is not None and cv2.countNonZero(_dom) > 0:
                        _cmed = float(np.median(_ggray[_dom > 0]))
                        _ccc = cv2.cvtColor(
                            cleaned[_gy0:_gy1, _gx0:_gx1], cv2.COLOR_BGR2GRAY)
                        _csame4 = (np.abs(
                            _ccc.astype(np.int16)
                            - _ggray.astype(np.int16)) <= 14)
                        _cin = ((_ggray < _cmed - 40.0)
                                & (_dom > 0) & _csame4).astype(np.uint8)
                        _nz4, _lab4, _st4, _ = cv2.connectedComponentsWithStats(
                            _cin, 8)
                        _res4m = np.zeros(_cin.shape, dtype=bool)
                        _n4 = 0
                        _dom_area = float(max(1.0, cv2.countNonZero(_dom)))
                        _cap4 = max(500.0, 0.00025 * float(w * h))
                        _cap4 = min(_cap4, 0.010 * _dom_area)
                        _gnear = cv2.dilate(
                            _gseed, np.ones((81, 81), np.uint8)) > 0
                        _k7r = np.ones((7, 7), np.uint8)
                        for _ci in range(1, _nz4):
                            _ca = int(_st4[_ci, cv2.CC_STAT_AREA])
                            if _ca < 10 or _ca > _cap4:
                                continue
                            _cx4 = int(_st4[_ci, cv2.CC_STAT_LEFT])
                            _cy4 = int(_st4[_ci, cv2.CC_STAT_TOP])
                            _cw4 = int(_st4[_ci, cv2.CC_STAT_WIDTH])
                            _ch4 = int(_st4[_ci, cv2.CC_STAT_HEIGHT])
                            if max(_cw4, _ch4) > 56:
                                continue
                            if max(_cw4, _ch4) > 3.5 * max(1, min(_cw4, _ch4)):
                                continue
                            if _ca / float(max(1, _cw4 * _ch4)) < 0.30:
                                continue
                            if not bool(_gnear[_cy4:_cy4 + _ch4,
                                               _cx4:_cx4 + _cw4][
                                _lab4[_cy4:_cy4 + _ch4,
                                      _cx4:_cx4 + _cw4] == _ci].any()):
                                continue
# بقایایِ واقعیِ متن داخلِ حبابِ سفید
# شناورند — حلقهٔ دورشان روشن است. تکه‌هایِ
# موی/گونه در لبهٔ دامینِ کاذب حلقهٔ تیره دارند
# → رد (لکهٔ LaMa-rescue روی گونهٔ «BUT I
# LIKE IT HERE.»)
                            try:
                                _cm = (_lab4[_cy4:_cy4 + _ch4,
                                             _cx4:_cx4 + _cw4] == _ci)
                                _rg = (cv2.dilate(_cm.astype(np.uint8), _k7r)
                                       > 0) & (~_cm)
                                if int(np.count_nonzero(_rg)) >= 12:
                                    _rgv = _ggray[_cy4:_cy4 + _ch4,
                                                  _cx4:_cx4 + _cw4][_rg]
                                    if float(
                                            (_rgv >= _cmed - 30.0).mean()
                                    ) < 0.60:
                                        continue
                            except Exception:
                                pass
                            _res4m |= (_lab4 == _ci)
                            _n4 += _ca
                        if _n4 >= 10:
                            _r4 = np.zeros_like(resid)
                            _r4[_gy0:_gy1, _gx0:_gx1] = _res4m
                            resid = resid | _r4
            except Exception:
                pass
# دیوارِ حباب/کادر (ساختارِ محافظت‌شده) هرگز resid
# نیست — شاخه‌هایِ «پیکسلِ تیرهٔ بیرونِ ماسک» دیوار را مثل
# متنِ باقی‌مانده هیل می‌کردند و حباب را نابود می‌کردند
            _pp = getattr(self, "_page_protect", None)
            if _pp is not None:
                try:
                    resid = resid & (_pp[y0:y1, x0:x1] == 0)
                except Exception:
                    pass
            n_res = int(np.count_nonzero(resid))
            if n_res < max(40, int(0.003 * _m_px)):
                continue
            if n_res > 0.45 * _m_px:
                continue
            mc = (resid.astype(np.uint8)) * 255
            mc = cv2.dilate(mc, cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (11, 11)))
            if collect is not None:
                collect.append((int(x0), int(y0), int(x1), int(y1), mc.copy()))
                n_fix += 1
                continue
            try:
                patch = cv2.inpaint(cc, mc, 6, cv2.INPAINT_TELEA)
                cleaned[y0:y1, x0:x1] = patch
                n_fix += 1
            except Exception:
                continue
        return n_fix

    def _mt_ring_samples(self, img: np.ndarray, hull: np.ndarray,
                         out_px: int):
        """نمونه‌گیری رنگ پس‌زمینه از بیرونِ چندضلعی — رئوس + میانه‌های
        یال، همه به اندازهٔ out_px بیرون‌زده از مرکز (الگوی مرجع:
        ×1.025 روی رئوس — اینجا فاصلهٔ پیکسلیِ صریح برای اطمینان)."""
        c = hull.mean(axis=0)
        samples = []
        n = len(hull)
        for i in range(n):
            for pt in (hull[i],
                       (hull[i] + hull[(i + 1) % n]) * 0.5):
                d = pt - c
                nd = float(np.hypot(d[0], d[1]))
                if nd < 1e-3:
                    continue
                sp = c + d * (1.0 + out_px / nd)
                sx, sy = int(round(sp[0])), int(round(sp[1]))
                if 0 <= sx < img.shape[1] and 0 <= sy < img.shape[0]:
                    samples.append(img[sy, sx])
        if not samples:
            return np.empty((0, 3), np.float32)
        return np.asarray(samples, dtype=np.float32)

    def _mt_polygon_clean(self, cleaned: np.ndarray, image: np.ndarray,
                          regions: List[TextRegion]) -> Tuple[int, str]:
        n_fill = 0
        n_heal = 0
        try:
            H, W = cleaned.shape[:2]
        except Exception:
            return 0, ""
        _dbg_path = os.environ.get("MANGA_DEBUG_MT", "")
        _dbg_img = image.copy() if _dbg_path else None
        try:
            if _dbg_img is not None:
                for r in regions:
                    for p in (getattr(r, "ocr_polys", None) or []):
                        _pp = np.asarray(p, np.int32).reshape(-1, 2)
                        if len(_pp) >= 3:
                            cv2.polylines(_dbg_img, [_pp], True,
                                          (0, 165, 255), 1)
        except Exception:
            pass
        for r in regions:
            polys = [p for p in (getattr(r, "ocr_polys", None) or [])
                     if p is not None and len(np.asarray(p).reshape(-1, 2)) >= 3]
            if not polys:
                bs = getattr(r, "boxes", None) or []
                polys = [np.asarray(b, dtype=np.float32).reshape(-1, 2)
                         for b in bs
                         if b is not None and len(np.asarray(b).reshape(-1, 2)) >= 3]
            for poly in polys:
                try:
                    pts = np.asarray(poly, dtype=np.float32).reshape(-1, 2)
                    if len(pts) < 3:
                        continue
# فاصلهٔ امن بیرونِ متن: متن + هالهٔ JPEG را می‌پوشاند
                    px0, py0 = pts[:, 0].min(), pts[:, 1].min()
                    px1, py1 = pts[:, 0].max(), pts[:, 1].max()
                    pw, ph = float(px1 - px0), float(py1 - py0)
                    if pw < 5 or ph < 5:
                        continue
                    margin = int(max(3, min(12, round(ph * 0.25))))
                    hull = cv2.convexHull(
                        pts.astype(np.int32)).reshape(-1, 2).astype(np.float32)
                    cx, cy = float(hull[:, 0].mean()), float(hull[:, 1].mean())
# چندضلعیِ منبسط (حاوی هاله) — رئوس از مرکز به بیرون
                    exp = hull.copy()
                    _d = hull - np.array([cx, cy], np.float32)
                    _nd = np.hypot(_d[:, 0], _d[:, 1])
                    _nd = np.maximum(_nd, 1e-3)
                    _push = (_nd + margin) / _nd
                    exp = (np.array([cx, cy], np.float32)[None, :]
                           + _d * _push[:, None])
                    exp[:, 0] = np.clip(exp[:, 0], 0, W - 1)
                    exp[:, 1] = np.clip(exp[:, 1], 0, H - 1)
# آیا جوهری داخل چندضلعی مانده؟ (در وضعیت فعلی)
# برش باید پدینگ داشته باشد وگرنه رینگِ بیرونیِ ماسک
# داخلِ crop نمی‌افتد (باگِ رینگِ خالی) و هیچ ترمیمی رخ نمی‌دهد
                    _pad = margin + 16
                    ex0, ey0 = int(exp[:, 0].min()) - _pad, int(exp[:, 1].min()) - _pad
                    ex1, ey1 = int(exp[:, 0].max()) + 1 + _pad, int(exp[:, 1].max()) + 1 + _pad
                    ex0, ey0 = max(0, ex0), max(0, ey0)
                    ex1, ey1 = min(W, ex1), min(H, ey1)
                    if ex1 - ex0 < 4 or ey1 - ey0 < 4:
                        continue
                    sub = cleaned[ey0:ey1, ex0:ex1]
                    emask = np.zeros(sub.shape[:2], np.uint8)
                    cv2.fillPoly(emask, [exp.astype(np.int32)
                                         - np.array([ex0, ey0], np.int32)],
                                 255)
                    if not emask.any():
                        continue
# رنگ مرجع — اول از نمونه‌های رأسِ مرجع (گوشه‌های خط =
# انتهای متن = پس‌زمینهٔ واقعی)، بعد رینگِ بیرونی
                    _sub_f = sub.astype(np.float32)
                    samp = self._mt_ring_samples(cleaned, exp, margin + 2)
                    bg_med = None
                    if len(samp) >= 3:
                        _v_med = np.median(samp, axis=0)
                        _dv = np.linalg.norm(samp - _v_med, axis=1)
                        _kv = samp[_dv <= 45.0]
                        if len(_kv) >= max(3, int(0.5 * len(samp))):
                            bg_med = np.median(_kv, axis=0)
                    ring = (cv2.dilate(emask, np.ones((13, 13), np.uint8)) > 0) \
                        & (emask == 0)
                    if bg_med is None:
                        if int(ring.sum()) < 24:
                            continue
                        ring_cols = _sub_f[ring]
                        _bg0 = np.median(ring_cols, axis=0)
                        _d_ring = np.linalg.norm(ring_cols - _bg0, axis=1)
                        _okr = ring_cols[_d_ring <= 45.0]
                        if len(_okr) < 24:
                            continue
                        bg_med = np.median(_okr, axis=0)
# گیتِ ضدبافت — اگر خودِ رینگِ دورِ خط پر از
# پیکسلِ «جوهرگونه» باشد، زمینه الگودار است (پارچه/
# هافتون/هنر) نه پس‌زمینهٔ متن → ترمیم الگو را له می‌کند
# → ردّ. سایه/گرادیانِ نرم از این گیت رد می‌شود.
                    if int(ring.sum()) >= 24:
                        _rg = _sub_f[ring]
                        _rgd = np.linalg.norm(_rg - bg_med[None, :], axis=1)
                        _rfrac = float((_rgd > 45.0).sum()) / len(_rgd)
                        if _rfrac > 0.35:
                            continue

# جوهرِ جامانده داخل چندضلعی؟
                    in_d = np.linalg.norm(_sub_f - bg_med[None, None, :],
                                          axis=2)
                    ink = (in_d > 45.0) & (emask > 0)
                    ink_frac = float(ink.sum()) / float((emask > 0).sum())
                    if ink_frac < 0.010:
                        continue  # تمیز است — دست نمی‌زنیم (کارِ LaMa می‌ماند)
# رینگِ پاکِ IDW — نمونه‌های جوهرگونه حذف می‌شوند
                    ring_ok = ring & (in_d <= 45.0)
                    if _dbg_img is not None:
                        _pe = exp.astype(np.int32).reshape(-1, 1, 2)
                        cv2.polylines(_dbg_img, [_pe], True, (0, 255, 0), 2)
# رنگِ پرکردن: نمونه‌های رأسِ نزدیکِ رنگِ پس‌زمینه
                    _sf = samp[np.linalg.norm(samp - bg_med, axis=1) <= 45.0] \
                        if len(samp) >= 3 else samp
                    fill_color = (np.median(_sf, axis=0) if len(_sf) >= 3
                                  else bg_med)
# گیتِ یکنواختی مرجع: فاصلهٔ اقلیدسیِ RGB ≤ ۲۵
                    _unif = samp[np.linalg.norm(samp - fill_color,
                                                axis=1) <= 25.0]
                    uniform = (len(samp) >= 3
                               and len(_unif) >= max(3, int(0.90 * len(samp))))
# پرکردنِ جامد حذف شد — حتی وقتی رینگ «یکنواخت»
# است، روی گرادیان/سایهٔ نرم نوارِ تختِ هم‌رنگ می‌سازد
# (بلوکی که کاربر روی گوشی دید). هِیلِ IDW از خودِ
# پیرامون درون‌یابی می‌کند → روی گرادیان هم نامرئی است.
# ترمیمِ جراحیِ جوهر — فقط پیکسل‌های جوهرِ
# جامانده (و هالهٔ نازکِ دورشان) با IDW از پیرامونِ پاکِ
# همان حوالی بازسازی می‌شوند؛ کلِ چندضلعی هرگز رنگ دوباره
# نمی‌شود تا کارِ LaMa و بافتِ زمینه سالم بماند —
# نوار/بلوکی که کاربر روی گوشی دید دیگر ساخته نمی‌شود.
                    _ink_m = (ink * 255).astype(np.uint8)
                    _ink_d = cv2.dilate(_ink_m, np.ones((5, 5), np.uint8),
                                        iterations=1) > 0
                    _target = _ink_d & (emask > 0)
                    _tgt = np.argwhere(_target)
                    if not len(_tgt):
                        continue
# نمونه‌های تمیز: اول داخلِ خودِ چندضلعیِ منبسط (نزدیک‌ترین
# زمینه)، بعد رینگِ بیرونی
                    _clean_in = np.argwhere((emask > 0) & (~_target)
                                            & (in_d <= 45.0))
                    _rpts = np.argwhere(ring_ok)
                    if len(_clean_in):
                        _rpts = (np.vstack([_clean_in, _rpts])
                                 if len(_rpts) else _clean_in)
                    elif len(_rpts) < 40:
                        _rpts = np.argwhere(ring)
                    if not len(_rpts):
                        continue
                    if len(_rpts) > 320:
                        _step = max(1, len(_rpts) // 320)
                        _rpts = _rpts[::_step]
                    _rcol = _sub_f[_rpts[:, 0], _rpts[:, 1]]
                    _res_f = _sub_f.copy()
# تکه‌تکه برای حافظهٔ امن روی نوارهای بلند
                    for _c0 in range(0, len(_tgt), 20000):
                        _c1 = min(len(_tgt), _c0 + 20000)
                        _tc = _tgt[_c0:_c1]
                        _dd = ((_tc[:, 0][:, None] - _rpts[:, 0][None, :]) ** 2
                               + (_tc[:, 1][:, None] - _rpts[:, 1][None, :]) ** 2
                               ).astype(np.float32)
                        _ww = 1.0 / (_dd + 0.001)
                        _ww /= _ww.sum(axis=1, keepdims=True)
                        _heal = _ww @ _rcol
                        _res_f[_tc[:, 0], _tc[:, 1]] = _heal
# فِدرِ ملایم روی مرزِ هدف تا لبهٔ ترمیم دیده نشود
                    _tm = (_target * 255).astype(np.uint8)
                    _core = cv2.erode(_tm, np.ones((3, 3), np.uint8))
                    _alpha = cv2.GaussianBlur(_tm, (5, 5), 1.2)
                    _alpha = np.minimum(_alpha, _tm)
                    _alpha[_core > 0] = 255
                    _a3 = (_alpha.astype(np.float32) / 255.0)[..., None]
                    _bl = _sub_f * (1.0 - _a3) + _res_f * _a3
                    sub[:] = np.clip(_bl, 0, 255).astype(np.uint8)
                    n_heal += 1
                except Exception:
                    continue
        if _dbg_path and _dbg_img is not None:
            try:
                cv2.imwrite(_dbg_path, _dbg_img)
            except Exception:
                pass
        if not (n_fill + n_heal):
            return 0, ""
        return n_fill + n_heal, f"{n_fill} fill, {n_heal} heal"

    def _opencv_fill_components(self, crop_img: np.ndarray, crop_msk: np.ndarray,
                                wall: Optional[np.ndarray] = None) -> np.ndarray:
        try:
            n, lab, st, _ = cv2.connectedComponentsWithStats(
                (crop_msk > 0).astype(np.uint8), 8)
        except Exception:
            return self._opencv_inpaint_hq(crop_img, crop_msk)
        k9 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        wall_m = None if wall is None else (wall > 0)
        out = crop_img.copy()
        h_c, w_c = crop_img.shape[:2]
        for i in range(1, n):
            x, y, w, h, a = (int(v) for v in st[i])
            if a < 4:
                continue
            pad = 24
            x0, y0 = max(0, x - pad), max(0, y - pad)
            x1 = min(w_c, x + w + pad)
            y1 = min(h_c, y + h + pad)
            sub_img = out[y0:y1, x0:x1]
            raw_m = (lab[y0:y1, x0:x1] == i)
            sub_m = cv2.morphologyEx(
                cv2.dilate(raw_m.astype(np.uint8) * 255, k9, iterations=1),
                cv2.MORPH_CLOSE, k9)
            dm = sub_m > 0
            if wall_m is not None:
                wl = wall_m[y0:y1, x0:x1]
                dm = (dm & raw_m) | (dm & ~wl)
            if a > 9000:
                try:
                    if self._inpaint_big_component_banded(out, sub_img,
                                                          raw_m, y0, x0):
                        continue
                except Exception:
                    pass
            _gm = None
            try:
                _g = self._glyph_refine_mask(sub_img, (raw_m.astype(np.uint8) * 255))
                if _g is not None:
                    _gm = (_g > 0)
            except Exception:
                _gm = None
            if _gm is not None:
                fill = self._opencv_inpaint_hq(sub_img, (_gm.astype(np.uint8) * 255))
                out[y0:y1, x0:x1][_gm] = fill[_gm]
            else:
                fill = self._opencv_inpaint_hq(sub_img, dm.astype(np.uint8) * 255)
                out[y0:y1, x0:x1][dm] = fill[dm]
        return out

    def _inpaint_big_component_banded(self, out: np.ndarray, sub_img: np.ndarray,
                                      raw_m: np.ndarray, y0: int, x0: int) -> bool:
        try:
            rh, rw = raw_m.shape
            if rh < 24:
                return False
            rows = raw_m.sum(axis=1)
            nz = rows > 0
            bands = []
            s = None
            gap = 0
            for r in range(rh):
                if nz[r]:
                    if s is None:
                        s = r
                    gap = 0
                elif s is not None:
                    gap += 1
                    if gap >= 4:
                        bands.append((s, r - gap + 1))
                        s = None
            if s is not None:
                bands.append((s, rh))
            bands = [(bs, be) for (bs, be) in bands if be - bs >= 4]
            if len(bands) < 2:
                return False
            for (bs, be) in bands:
                band_m = np.zeros_like(raw_m)
                band_m[bs:be] = raw_m[bs:be]
                gm = None
                try:
                    g = self._glyph_refine_mask(sub_img,
                                                band_m.astype(np.uint8) * 255)
                    if g is not None:
                        gm = (g > 0)
                except Exception:
                    gm = None
                target = gm if gm is not None else band_m
                fill = self._opencv_inpaint_hq(sub_img,
                                               target.astype(np.uint8) * 255)
                out[y0:y0 + rh, x0:x0 + rw][target] = fill[target]
            return True
        except Exception:
            return False

    @staticmethod
    def _bg_is_textured(crop_img: np.ndarray, crop_msk: np.ndarray,
                        strong: bool = False) -> bool:
        try:
            m = crop_msk > 0
            ring = (cv2.dilate(crop_msk, np.ones((9, 9), np.uint8)) > 0) & (~m)
            if int(np.count_nonzero(ring)) < 60:
                return False
            g = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
            rf = g[ring].astype(np.float32)
            t_std, t_lap = (25.0, 8.0) if strong else (17.0, 5.0)
            if float(np.std(rf)) > t_std:
                return True
            lap = np.abs(cv2.Laplacian(g, cv2.CV_32F))
            return bool(float(np.mean(lap[ring])) > t_lap)
        except Exception:
            return False

    def _glyph_refine_mask(self, image: np.ndarray, mask: np.ndarray) -> Optional[np.ndarray]:
        try:
            m0 = (mask > 0).astype(np.uint8)
            area0 = int(m0.sum())
            if area0 < 80:
                return None
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            bg = cv2.medianBlur(gray, 31)
            diff = gray.astype(np.int16) - bg.astype(np.int16)
            zone = cv2.dilate(m0, np.ones((7, 7), np.uint8), iterations=1)
            ink = ((np.abs(diff) > 26) & (zone > 0)).astype(np.uint8) * 255
            ink = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
            ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
            try:
                _n, _lab, _st, _ = cv2.connectedComponentsWithStats(
                    (ink > 0).astype(np.uint8), connectivity=8)
                if _n > 1:
                    _keep = np.zeros_like(ink)
                    for _i in range(1, _n):
                        if int(_st[_i, cv2.CC_STAT_AREA]) >= 24:
                            _keep[_lab == _i] = 255
                    if int(np.count_nonzero(_keep)) >= 40:
                        ink = _keep
            except Exception:
                pass
            ink = cv2.dilate(
                ink, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)), iterations=1
            )
            cov = float(np.count_nonzero(ink)) / float(area0)
            if cov < 0.12 or cov > 0.92:
                return None
            return ink
        except Exception:
            return None

    def _ring_plane_fill(self, crop_img: np.ndarray,
                         crop_msk: np.ndarray) -> Optional[np.ndarray]:
        """ — پرکردنِ استروک‌هایِ نازک روی زمینهٔ گرادیانی با
        «صفحهٔ رنگیِ برازش‌شده از حلقه» — به‌جای TELEA که رنگِ هنرِ نزدیک
        (دست/شانه) را داخلِ زمینه می‌کشد (لکهٔ خاکستریِ صفحهٔ TIME BOMB
        کنارِ «SINCE WHEN WERE WE FRIENDS?»). برای هر کامپوننت: حلقهٔ ۹px
        → حذفِ پرت‌ها نسبت به میانه → برازشِ صفحهٔ خطیِ BGR → پرکردن.
        روی گرادیانِ ملایم تقریباً نامرئی است و هرگز رنگِ هنر را پخش
        نمی‌کند."""
        try:
            n, lab, st, _ = cv2.connectedComponentsWithStats(
                (crop_msk > 0).astype(np.uint8), 8)
            if n <= 1:
                return None
            out = crop_img.copy()
            h_c, w_c = crop_img.shape[:2]
            k9 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
            _filled = 0
            for i in range(1, n):
                x, y, w, h, a = (int(v) for v in st[i])
                if a < 8:
                    continue
                pad = 10
                x0, y0 = max(0, x - pad), max(0, y - pad)
                x1 = min(w_c, x + w + pad)
                y1 = min(h_c, y + h + pad)
                raw = (lab[y0:y1, x0:x1] == i)
                ring = (cv2.dilate(raw.astype(np.uint8) * 255, k9) > 0) & (~raw)
                n_ring = int(np.count_nonzero(ring))
                if n_ring < 30:
                    continue
                px = crop_img[y0:y1, x0:x1][ring].astype(np.float32)
                med = np.median(px, axis=0)
                d = np.abs(px - med[None, :]).max(axis=1)
                _sel = d <= 30.0
                if float(_sel.mean()) < 0.45 or int(_sel.sum()) < 30:
                    continue  # حلقهٔ آشفته (هنر دورِ متن) → این روش نه
                rys, rxs = np.nonzero(ring)
                rv = crop_img[y0:y1, x0:x1][ring][_sel].astype(np.float32)
                rsx = rxs[_sel].astype(np.float32) / max(1.0, float(w_c))
                rsy = rys[_sel].astype(np.float32) / max(1.0, float(h_c))
                A = np.stack([np.ones_like(rsx), rsx, rsy], axis=1)
                try:
                    coef, *_ = np.linalg.lstsq(A, rv, rcond=None)
                except Exception:
                    continue
                if not np.isfinite(coef).all():
                    continue
                mys, mxs = np.nonzero(raw)
                mx = mxs.astype(np.float32) / max(1.0, float(w_c))
                my = mys.astype(np.float32) / max(1.0, float(h_c))
                Am = np.stack([np.ones_like(mx), mx, my], axis=1)
                vals = Am @ coef
                vals = np.clip(np.rint(vals), 0, 255).astype(np.uint8)
                reg = out[y0:y1, x0:x1]
                reg[raw] = vals
                out[y0:y1, x0:x1] = reg
                _filled += 1
            if _filled <= 0:
                return None
            return out
        except Exception:
            return None

    def _opencv_inpaint_hq(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        if mask is None or not np.any(mask):
            return image.copy()
        m = (mask > 0).astype(np.uint8) * 255
        radius = max(1, int(getattr(self, "inpaint_radius", 3)))

        out = cv2.inpaint(image, m, inpaintRadius=radius, flags=cv2.INPAINT_TELEA)
        out[m == 0] = image[m == 0]

        try:
            h, w = image.shape[:2]
            if cv2.countNonZero(m) > 0.004 * h * w and max(h, w) > 640:
                sc = 640.0 / float(max(h, w))
                sm = cv2.resize(out, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
                mm = cv2.resize(m, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST)
                sm = cv2.inpaint(sm, mm, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
                up = cv2.resize(sm, (w, h), interpolation=cv2.INTER_CUBIC)
                out[m > 0] = up[m > 0]
        except Exception:
            pass
# ترمیمِ «تکهٔ سیاهِ تازه»: Telea از مرزِ ماسک رنگ
# میکشد و اگر دورِ ماسک تیره باشد (دورخطِ سیاهِ متنِ دورخط‌دار
# img3 / جوهرِ چسبیده به ماسک)، داخلِ پرشده لکهٔ سیاه میسازد.
# تکههایِ تیرهٔ تازهٔ داخلِ ماسک (خروجی <70 جایی که حاشیهٔ
# اورجینالِ اطراف روشن >110 بوده) پیدا، گشاد ۹px و یک Telea
# کوچکِ دیگر — مرزِ این بار هنرِ اطراف است نه خودِ دورخط.
        try:
            _go = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _gc = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
# بیشینهٔ محلی بهجایِ میانگین — کنارِ دورخطِ سیاهِ خودِ متن
# میانگینِ ۲۱×۲۱ زیرِ ۱۱۰ میافتد و تکه پیدا نمیشد
            _ring = cv2.dilate(_go, np.ones((31, 31), np.uint8))
            _dkn = ((_gc < 70) & (_ring > 110) & (m > 0))
            _dkn = cv2.morphologyEx(
                _dkn.astype(np.uint8), cv2.MORPH_OPEN,
                np.ones((3, 3), np.uint8))
            if int(cv2.countNonZero(_dkn)) >= 40:
# تله‌آیِ دوم هم از همان دورِ تیره رنگ میکشد
# هر تکه با «میانهٔ رنگِ حلقهٔ روشنِ اطرافش» پر میشود
# (پچِ تختِ همرنگِ هنر با لبهٔ فدر) — تیرهٔ باقیمانده
# نمیماند و لکهٔ سیاه جایش لکهٔ همرنگِ زمینه میشود.
                _nzg, _lbg, _stg, _ = cv2.connectedComponentsWithStats(
                    _dkn.astype(np.uint8), 8)
                for _ig in range(1, _nzg):
                    if int(_stg[_ig, cv2.CC_STAT_AREA]) < 40:
                        continue
                    _cg = (_lbg == _ig)
                    _cgd = cv2.dilate(_cg.astype(np.uint8),
                                      np.ones((15, 15), np.uint8)) > 0
                    _ring = (cv2.dilate(_cg.astype(np.uint8),
                                        np.ones((31, 31), np.uint8)) > 0)
                    _ring &= ~_cgd & (_gc > 90)
                    if int(np.count_nonzero(_ring)) < 30:
                        continue
                    _med = np.median(out[_ring], axis=0)
                    _msk = (_cg.astype(np.uint8)) * 255
                    _msk_f = cv2.GaussianBlur(
                        _msk, (7, 7), 2).astype(np.float32) / 255.0
                    _patch = out.copy()
                    _patch[_cg] = _med
                    out = (_patch * _msk_f[..., None]
                           + out * (1.0 - _msk_f[..., None])).astype(np.uint8)
                    _gc = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
        except Exception:
            pass
        return out

    @staticmethod
    def _smooth_bg_fill(crop_img: np.ndarray, crop_msk: np.ndarray,
                        k1: int = 51, k2: int = 21, feather: int = 3):
        try:
            if crop_img is None or crop_msk is None:
                return None
            m0 = (crop_msk > 0).astype(np.uint8) * 255
            if not m0.any() or m0.all():
                return None
            h_c, w_c = crop_img.shape[:2]
            k_a = k1 if k1 % 2 == 1 else k1 + 1
            k_b = k2 if k2 % 2 == 1 else k2 + 1
            if k_a >= min(h_c, w_c):
                k_a = max(3, (min(h_c, w_c) - 1) // 2 * 2 - 1)
            if k_b >= min(h_c, w_c):
                k_b = max(3, (min(h_c, w_c) - 1) // 2 * 2 - 1)
            m_d = cv2.dilate(m0, np.ones((2 * feather + 1, 2 * feather + 1), np.uint8))
            try:
                dist = cv2.distanceTransform((m0 > 0).astype(np.uint8),
                                             cv2.DIST_L2, 3)
                dmax = float(dist.max())
                if dmax > 16.0:
                    ring = (cv2.dilate(m0, np.ones((15, 15), np.uint8)) > 0) & ~(m0 > 0)
                    soft = False
                    if int(np.count_nonzero(ring)) >= 200:
                        g = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY).astype(np.float32)
                        lap = cv2.Laplacian(g, cv2.CV_32F)
                        soft = float(lap[ring].std()) < 9.0
                    if not soft:
                        return None
            except Exception:
                pass
# به نسخهٔ medianBlur برگشت — بنرهایِ تیره حالا توسط
# _enclosure_instant_fill قبل از این‌جا پاک می‌شوند و این تابع
# فقط زمینه‌هایِ روشن/هنری را می‌گیرد که medianBlur خطوطِ هنر
# را بهتر از پخشِ کانولوشن حفظ می‌کند (مقایسهٔ صفحهٔ چینی).
            bg = cv2.medianBlur(crop_img, k_a)
            bg = cv2.medianBlur(bg, k_b)
            alpha = cv2.GaussianBlur(m_d, (7, 7), 0).astype(np.float32) / 255.0
            af = alpha[..., None]
            out = crop_img.astype(np.float32) * (1.0 - af) + bg.astype(np.float32) * af
            return np.clip(out, 0, 255).astype(np.uint8)
        except Exception:
            return None

    def _rect_structure_lock(self, image: np.ndarray,
                             rects) -> Optional[np.ndarray]:
        """ — قفلِ «ساختارِ روشنِ نازک» در بلوک‌هایِ اجباری-LaMa
        (). باکسِ توپرِ بلوکِ تیره گاهی از مرزِ پنل عبور می‌کند و
        قابِ تزئینی/نوارِ لبهٔ پنل (ساختارِ روشنِ نازک) را هم می‌بلعد —
        LaMa با حفرهٔ بزرگِ رویِ ساختار، قاب را «له» می‌کند (نمونهٔ کاربر:
        GREEN MOON — قابِ کنارِ متن ذوب شد). معیارِ ساختار: مؤلفهٔ روشن
        (≥۱۴۸) که ۱) بخشِ معناداری‌اش (≥۲۵٪ یا ≥۴۰۰px) بیرونِ باکس است و
        ۲) نازک است (ضخامتِ تبدیلِ فاصله ≤ 64px) — یعنی قاب/نوار، نه
        تودهٔ پس‌زمینه (گلیفِ متن هم کاملاً داخلِ باکس‌اند و هرگز قفل
        نمی‌شوند). پیکسل‌هایِ قفل از ماسکِ
        بلوک خارج می‌شوند تا LaMa آن‌ها را «زمینه» ببیند و دستِ
        پرکننده‌ها هم به آن‌ها نرسد (مکانیزمِ )."""
        try:
            if os.environ.get("MANGA_NO_STRUCT_LOCK", "0") == "1":
                return None
            g = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        except Exception:
            return None
        h, w = g.shape[:2]
        out = np.zeros((h, w), dtype=np.uint8)
        _any = False
        for _fb in (rects or []):
            try:
                x0, y0 = int(_fb[0]), int(_fb[1])
                x1, y1 = int(_fb[2]), int(_fb[3])
            except Exception:
                continue
            _m = 26
            ex0, ey0 = max(0, x0 - _m), max(0, y0 - _m)
            ex1, ey1 = min(w, x1 + _m), min(h, y1 + _m)
            if ex1 - ex0 < 32 or ey1 - ey0 < 32:
                continue
            reg = g[ey0:ey1, ex0:ex1]
            bright = ((reg >= 148).astype(np.uint8)) * 255
            if not int(cv2.countNonZero(bright)):
                continue
# پلِ نازکِ گلو بینِ حرف و قاب بشکند
            try:
                bright = cv2.morphologyEx(bright, cv2.MORPH_OPEN,
                                          np.ones((2, 2), np.uint8))
            except Exception:
                pass
            n, lab, st, _ = cv2.connectedComponentsWithStats(bright, 8)
            if n <= 1:
                continue
# باکسِ توپرِ داخلِ ناحیه (همان +4/-5 مسیرِ )
            rx0 = max(0, (x0 - 4) - ex0)
            ry0 = max(0, (y0 - 4) - ey0)
            rx1 = min(ex1 - ex0, (x1 + 5) - ex0)
            ry1 = min(ey1 - ey0, (y1 + 5) - ey0)
            inside = np.zeros_like(bright)
            inside[ry0:ry1, rx0:rx1] = 255
            hit = np.zeros_like(bright)
            for i in range(1, n):
                a = int(st[i, cv2.CC_STAT_AREA])
                if a < 150:
                    continue
                comp = (lab == i)
                out_px = int(np.count_nonzero(comp & (inside == 0)))
                if out_px < max(400, int(0.25 * a)):
                    continue  # کاملاً داخلِ باکس = گلیفِ متن
                try:
                    _dt = cv2.distanceTransform(
                        comp.astype(np.uint8), cv2.DIST_L2, 3)
                    _thick = float(_dt.max()) * 2.0
                except Exception:
                    _thick = 24.0
                if _thick > 64.0:
                    continue  # خیلی ضخیم = تودهٔ پس‌زمینه، نه قاب
                hit[comp] = 255
                _any = True
            if not int(cv2.countNonZero(hit)):
                continue
# حفره‌هایِ بینِ پیچ‌هایِ قاب هم پوشیده شود + رشدِ ملایم
            hit = cv2.morphologyEx(hit, cv2.MORPH_CLOSE,
                                   np.ones((13, 13), np.uint8))
            hit = cv2.dilate(hit, np.ones((7, 7), np.uint8))
            out[ey0:ey1, ex0:ex1] = np.maximum(
                out[ey0:ey1, ex0:ex1], hit)
        if not _any or not int(cv2.countNonZero(out)):
            return None
        return out

    def _structural_protect_mask(self, image: np.ndarray,
                                 regions: List["TextRegion"],
                                 min_len: int = 60,
                                 near_px: int = 25) -> Optional[np.ndarray]:
        """ — نقشهٔ «ساختارِ محافظت‌شده» در سطحِ صفحه: دیوارِ حباب و
        کادرِ پنل (خطوطِ تیرهٔ نازکِ بلند) هرگز نباید پاک شوند. همهٔ
        مرحله‌هایِ پرکردن ماسک را تا ۲۵px گشاد + CLOSE می‌کنند و خطِ
        ۳-۴ پیکسلیِ دیوار را می‌بلعند → باگِ «حبابِ پاک‌شده ولی تمیز»
        (صفحهٔ TIME BOMB — «YOU'RE LEAVING THE COMPANY?»).
        معیارِ ساختاری: کامپوننتِ تیرهٔ نزدیکِ ماسکِ متن که بلند است
        (≥۶۰px)، نازک (ضخامت ≤ ۱۴px)، و بیشترِ آن بیرونِ پالی‌هایِ OCR —
        گلیف‌هایِ متن (داخلِ پالی‌ها) محافظت نمی‌شوند تا پاک‌سازیِ متن
        مختل نشود. این نقشه در ترکیبِ نهایی و ماسکِ LaMa از ماسکِ فعال
        کم می‌شود."""
        try:
            h, w = image.shape[:2]
# ناحیهٔ موردِ توجه: حوالیِ ماسکِ متنِ خام (بدونِ protect)
            _raw_mask = getattr(self, "_page_raw_text_mask", None)
            if _raw_mask is None or _raw_mask.shape != (h, w) \
                    or not np.any(_raw_mask):
                return None
# اندروید (MANGA_PROT_CACHE): این تابع در هر صفحه
# «دو بار» صدا زده میشود (protect + wall_bandِ با
# min_len/near_pxِ متفاوت) و بخشهایِ سنگینش (medianBlurِ ۳۱
# ساختِ poly_all، بازِ خطیِ سراسری + distanceTransformها)
# از min_len/near_px مستقلاند → کشِ کوتاهِ بینِ همان دو
# فراخوانی (صرفهٔ ~۱-۴ ثانیه در هر صفحه). کلید = آدرسِ بافرِ
# تصویر + ماسکِ خام + تعدادِ ناحیه؛ و محلِ فراخوانی بعد از
# بارِ دوم آن را پاک میکند (self._spm_cache = None) تا کش
# هیچ‌وقت کهنه نشود. PC بدونِ کش — بیت‌به‌بیت.
            _spc = None
            _key = None
            if _android_gate("MANGA_PROT_CACHE"):
                try:
                    _key = (
                        image.__array_interface__["data"][0],
                        image.shape,
                        _raw_mask.__array_interface__["data"][0],
                        len(regions or []))
                except Exception:
                    _key = None
                _spc = getattr(self, "_spm_cache", None)
            _ln = _vl = _hl = None
            _hit = bool(_spc is not None and _key is not None
                           and _spc[0] == _key
                           and len(_spc) == 7)
            if _hit:
                dark_full, poly_all = _spc[1], _spc[2]
                out = _spc[3].copy()
                _ln, _vl, _hl = _spc[4], _spc[5], _spc[6]
# بخشهایِ وابسته به near_px — ارزان — از نو
                _nk = 25 if int(near_px) >= 25 \
                    else (13 if int(near_px) >= 13 else 9)
                near = cv2.dilate(_raw_mask,
                                  np.ones((_nk, _nk), np.uint8))
                dark = cv2.bitwise_and(dark_full, near)
                n, lab, st, _ = cv2.connectedComponentsWithStats(dark, 8)
                if n <= 1:
                    return None
            else:
                g = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                _nk = 25 if int(near_px) >= 25 \
                    else (13 if int(near_px) >= 13 else 9)
                near = cv2.dilate(_raw_mask,
                                  np.ones((_nk, _nk), np.uint8))
# تیرگیِ «نسبی» هم — دیوارِ محوِ JPEG (خاکستریِ ۱۲۰-۱۹۰
# روی زمینهٔ روشن) با آستانهٔ مطلقِ ۱۲۰ گم می‌شد و بخشی از دیوار
# باز هم لکه می‌شد. medianBlurِ ۳۱ زمینهٔ محلی است.
                try:
                    _bg = cv2.medianBlur(g, 31)
                    dark_rel = ((_bg.astype(np.int16)
                                 - g.astype(np.int16)) > 45)
                    dark = ((g < 120) | dark_rel).astype(np.uint8) * 255
                except Exception:
                    dark = (g < 120).astype(np.uint8) * 255
                dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE,
                                        np.ones((3, 3), np.uint8))
# تیرهٔ کاملِ صفحه (قبل از برشِ باندِ ۲۵px) برای
# بازِ خطیِ سراسری؛ سرِ کادرِ پنل داخلِ باند است ولی بدنه‌اش
# بیرونِ باند — خط باید تا انتها محافظت شود نه فقط سرش.
                dark_full = dark
                dark = cv2.bitwise_and(dark, near)
                n, lab, st, _ = cv2.connectedComponentsWithStats(dark, 8)
                if n <= 1:
                    return None
# پالی‌هایِ OCR — گلیف‌ها اینجایند و نباید محافظت شوند
                poly_all = np.zeros((h, w), dtype=np.uint8)
                for r in (regions or []):
                    for p in (getattr(r, "ocr_polys", None) or []):
                        try:
                            pp = np.asarray(
                                p, dtype=np.float32).reshape(-1, 2)
                        except Exception:
                            continue
                        if pp.shape[0] >= 3:
                            cv2.fillPoly(
                                poly_all,
                                [np.rint(pp).astype(np.int32)], 255)
                poly_all = cv2.dilate(poly_all,
                                      np.ones((9, 9), np.uint8))
                out = np.zeros((h, w), dtype=np.uint8)
# بازِ خطیِ سراسری: کادرِ پنل/خطِ جدابندِ سرراست
# (اجرای ≥۶۰px، ضخامت ≤۱۰px، بیرونِ پالیهایِ OCR) سراسری
# محافظت میشود — نه فقط تکهٔ داخلِ باندِ متن. کیسِ ۱۰۱۸:
# ماسکِ لوگو/حباب قابِ چپِ پنل را در میان بریده بود و تکههای
# یتیم مثل «لبهٔ سیاه» دیده میشدند.
                try:
                    _vl = cv2.morphologyEx(
                        dark_full, cv2.MORPH_OPEN,
                        np.ones((60, 1), np.uint8))
                    _hl = cv2.morphologyEx(
                        dark_full, cv2.MORPH_OPEN,
                        np.ones((1, 60), np.uint8))
                    if int(cv2.countNonZero(_vl)) or \
                            int(cv2.countNonZero(_hl)):
# ضخامتِ بدونِ پخش: erodeِ بدونِ dilate
# تا هستهٔ توپر حذف شود ولی خطِ نازکِ چسبیده به آن زنده
# بماند (dilateِ ±۷px قابِ ۵px کناری را هم میکشت —
# کیسِ ۱۰۱۸: کلِ قابِ چپِ پنل)
                        _vth = cv2.erode(_vl,
                                         np.ones((1, 15), np.uint8))
                        _hth = cv2.erode(_hl,
                                         np.ones((15, 1), np.uint8))
                        _ln = ((_vl | _hl) & ~_vth & ~_hth
                               & (poly_all == 0)).astype(np.uint8) * 255
                        _ln = cv2.morphologyEx(
                            _ln, cv2.MORPH_CLOSE,
                            np.ones((3, 3), np.uint8))
                        _n2, _l2, _s2, _ = \
                            cv2.connectedComponentsWithStats(_ln, 8)
                        for _i2 in range(1, _n2):
                            _a2 = int(_s2[_i2, cv2.CC_STAT_AREA])
                            if _a2 < 60:
                                continue
                            _bx2 = int(_s2[_i2, cv2.CC_STAT_LEFT])
                            _by2 = int(_s2[_i2, cv2.CC_STAT_TOP])
                            _bw2 = int(_s2[_i2, cv2.CC_STAT_WIDTH])
                            _bh2 = int(_s2[_i2, cv2.CC_STAT_HEIGHT])
                            _cp2 = (_l2[_by2:_by2 + _bh2,
                                        _bx2:_bx2 + _bw2] == _i2)
# در سطحِ پیکسل: فقط پیکسلهایِ نازک
# (≤۱۰px) محافظت میشوند؛ لبِ ساختارِ توپر که به
# خط چسبیده قربانیِ کلِ کامپوننت نمیشود
                            try:
# پدِ ۱px — کامپوننتِ توپر (خطِ کامل در باکسِ
# خودش) هیچ پیکسلِ صفر ندارد → dt=FLT_MAX و
# همه رد میشد (کیسِ قابِ ۱۰۱۸)
                                _pd2 = np.zeros(
                                    (_cp2.shape[0] + 2,
                                     _cp2.shape[1] + 2), np.uint8)
                                _pd2[1:-1, 1:-1] = _cp2.astype(np.uint8)
                                _dt2 = cv2.distanceTransform(
                                    _pd2, cv2.DIST_L2, 3)[1:-1, 1:-1]
                                _thin2 = _cp2 & ((_dt2 * 2.0) <= 10.0)
                            except Exception:
                                _thin2 = _cp2
                            if int(_thin2.sum()) < 40:
                                continue
                            out[_by2:_by2 + _bh2,
                                _bx2:_bx2 + _bw2][_thin2] = 255
                    if self.debug:
                        _nl = int(cv2.countNonZero(out))
                        if _nl:
                            print(f"  [✓]قفلِ خطِ سراسری — {_nl}px",
                                  flush=True)
                except Exception:
                    if self.debug:
                        import traceback as _tb
                        print("  [!]قفلِ خط خطا:", flush=True)
                        _tb.print_exc()
                if _key is not None:
                    try:
                        self._spm_cache = (_key, dark_full, poly_all,
                                           out.copy(), _ln, _vl,
                                           _hl)
                    except Exception:
                        pass
            try:
                import os as _os
                _dp = _os.environ.get("MANGA_DUMP_PROTECT")
                if _dp:
                    cv2.imwrite(_dp + "_ln.png", _ln)
                    cv2.imwrite(_dp + "_vl.png", _vl)
                    cv2.imwrite(_dp + "_dark.png", dark_full)
                    cv2.imwrite(_dp + "_poly.png", poly_all)
                    cv2.imwrite(_dp + "_out.png", out)
                    print("[DUMP] protect →", _dp, flush=True)
            except Exception as _e:
                print("[DUMP] fail", _e, flush=True)
            for i in range(1, n):
                a = int(st[i, cv2.CC_STAT_AREA])
                if a < (90 if int(min_len) >= 60 else 48):
                    continue
                bx = int(st[i, cv2.CC_STAT_LEFT])
                by = int(st[i, cv2.CC_STAT_TOP])
                bw_ = int(st[i, cv2.CC_STAT_WIDTH])
                bh_ = int(st[i, cv2.CC_STAT_HEIGHT])
                if not (bw_ >= int(min_len) or bh_ >= int(min_len)):
                    continue
# فقط در bbox کار کن — آرایهٔ کاملِ صفحه در هر
# کامپوننت (مخصوصاً distanceTransformِ float32) روی نوارِ
# بلند رم را می‌بلعد و OOM می‌آورد
                comp = (lab[by:by + bh_, bx:bx + bw_] == i)
                on_poly = float(np.count_nonzero(
                    comp & (poly_all[by:by + bh_, bx:bx + bw_] > 0)))
                if on_poly > 0.30 * float(a):
                    continue  # بیشترِ آن متن است (زیرخط/حرفِ چسبیده)
                try:
                    _dt = cv2.distanceTransform(
                        comp.astype(np.uint8), cv2.DIST_L2, 3)
                    _thick = float(_dt.max()) * 2.0
                except Exception:
                    _thick = 16.0
                if _thick > 14.0:
                    continue
                out[by:by + bh_, bx:bx + bw_][comp] = 255
# «قابِ رنگیِ» حباب: خطِ نازکِ بلندِ «اشباعِ
# رنگی» (حبابِ ششضلعیِ سبزِ up0822) تیرهِ خالص نیست و از
# معیارِ dark جا میماند → داخلِ ماسکِ متن میفتد، donor
# پاکش میکند و قاب تکهتکه به خروجی میرود. همان شرطهایِ
# بلندی/نازکی/بیرونِ پالی رویِ کانالِ اشباع اعمال میشود
# متنِ رنگیِ خودِ ناحیه داخلِ پالیهاست و محافظت نمیشود و
# هالهٔ پهنِ گلو  هم «نازک» نیست و رد میشود.
            _out_colj = np.zeros((h, w), dtype=np.uint8)
            try:
                _hsvj = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
# رسایِ ۶۰px: کمانهایِ قابِ دورِ متن (بالای
# حبابِ ششضلعی) از باندِ ۲۵px بیروناند و بدونِ آنها قاب
# خطچین میماند. بازپسگیریِ «اورجینال» در بدترین حالت
# یعنی اصلِ آنجا دستنخورده میماند — امن.
                _nearj = cv2.dilate(_raw_mask,
                                    np.ones((121, 121), np.uint8))
# S≥70: لبههایِ ضدآلیاسِ حرفِ رنگی-روی-زمینه (S=45..70)
# نباید واردِ map شوند وگرنه بازپسگیری، متنِ رنگی را
# برمیگرداند («l»یِ Alright در img6) — تقاطعهایِ قاب با
# حرف فدای متنِ تمیز میشوند.
                _colj = (((_hsvj[..., 1] >= 70)
                          & (_hsvj[..., 2] >= 60))
                         & _nearj).astype(np.uint8) * 255
# گسترشِ درامتدادِ خط: تکههایِ تقاطعِ قاب با
# حرف (S=45..70 — سبزِ تیرهشده رویِ جوهر) فقط اگر به
# خطِ تأییدشدهٔ قاب چسبیده باشند واردِ map میشوند؛ لبهٔ
# حرفِ دور از قاب («l»یِ Alright در img6) وسطِ حباب است
# و به قاب نمیرسد → متن پاک میماند.
                try:
# فقط همرنگِ خطِ قاب (فاصلهٔ هیوئیِ سیرشارکی ≤۲۵) —
# لبهٔ حرفِ قهوهایِ دور از قاب (img6) وصل نمیشود
                    _mhj = _hsvj[..., 0][_colj > 0]
                    if _mhj.size >= 30:
                        _medh = float(np.median(_mhj))
                        _dh = np.abs(_hsvj[..., 0].astype(np.float32)
                                     - _medh)
                        _dh = np.minimum(_dh, 180.0 - _dh)
                        _extj = ((cv2.dilate(
                            _colj, np.ones((15, 15), np.uint8)) > 0)
                            & (_hsvj[..., 1] >= 45)
                            & (_hsvj[..., 2] >= 45)
                            & (_dh <= 25.0)
                            & (_nearj > 0))
                        _colj = ((_colj > 0)
                                 | _extj).astype(np.uint8) * 255
                except Exception:
                    pass
                _ncj, _lcj, _scj, _ = cv2.connectedComponentsWithStats(
                    _colj, 8)
# پالیِ «خام» — قابِ رنگی فقط لبهٔ پالی را میبُرد
# با poly_allِ گشادِ ۹ همهٔ تکهها on_poly میشدند
                _polyrawj = np.zeros((h, w), dtype=np.uint8)
                for _rj in (regions or []):
                    for _pj in (getattr(_rj, "ocr_polys", None) or []):
                        try:
                            _ppj = np.asarray(
                                _pj, dtype=np.float32).reshape(-1, 2)
                        except Exception:
                            continue
                        if _ppj.shape[0] >= 3:
                            cv2.fillPoly(
                                _polyrawj,
                                [np.rint(_ppj).astype(np.int32)], 255)
# قابِ حبابهایِ کوچک هم تکههایِ ریز دارد
# (حبابِ «HE'S KNOWN…» در up0822: ~۸۷px در کلِ قاب) →
# آستانه = همترازِ wall_band (۱۶px)
# تکههایِ قابِ رنگی خیلی ریزند (۲×۸px —
# JPEG + تقاطع با حرف它们 را میشکند) → گیتِ طول/مساحت/
# پالی حذف شد؛ فقط «نازکِ اشباعِ نزدیکِ متن» (dt≤۱۴)
# کافی است — رنگِ تختِ پهن (هالهٔ گلو/زمینه) «نازک»
# نیست و رد میشود؛ متنِ رنگیِ نازک هم restored میشود
# ولی متنِ رنگیِ نازک در دیالوگ نادر است.
                for _ij in range(1, _ncj):
                    _aj = int(_scj[_ij, cv2.CC_STAT_AREA])
                    if _aj < 3:
                        continue
                    _bxj = int(_scj[_ij, cv2.CC_STAT_LEFT])
                    _byj = int(_scj[_ij, cv2.CC_STAT_TOP])
                    _bwj = int(_scj[_ij, cv2.CC_STAT_WIDTH])
                    _bhj = int(_scj[_ij, cv2.CC_STAT_HEIGHT])
                    _cpj = (_lcj[_byj:_byj + _bhj,
                                 _bxj:_bxj + _bwj] == _ij)
# «قابِ رنگی» نباید خودِ حروفِ رنگی را
# ببلعد: متنِ بنفشِ اشباعِ درشتِ img6 (S≥۷۰ و «نازکِ»
# ≤۱۴px!) ۱۲هزارpx حرف را داخلِ map برد → کامپوزِ
# دو-عکسی آن حرفها را از خروجی حذف کرد = «متنِ قبلی
# جا میماند». کامپوننتِ بزرگِ «عمدتاً داخلِ پالیِ
# OCR» = حرف است نه قاب (قابِ حباب عمدتاً بیرونِ
# پالیست) → رد. تکههایِ ریزِ تقاطعِ قاب/حرف
# (۲×۸px — ) بدونِ گیت میمانند.
                    if _aj >= 24:
                        try:
                            _onpj = float(np.count_nonzero(
                                _cpj & (_polyrawj[_byj:_byj + _bhj,
                                                  _bxj:_bxj + _bwj] > 0)))
                            if _onpj >= 0.60 * float(_aj):
                                continue
                        except Exception:
                            pass
                    try:
                        _dtj = cv2.distanceTransform(
                            _cpj.astype(np.uint8), cv2.DIST_L2, 3)
                        if float(_dtj.max()) * 2.0 > 14.0:
                            continue
                    except Exception:
                        pass
# فقط نقشهٔ «قابِ رنگی» — protectِ تیره دستنخورده
                    _out_colj[_byj:_byj + _bhj,
                              _bxj:_bxj + _bwj][_cpj] = 255
            except Exception:
                if self.debug or os.environ.get('MANGA_OVERLAYDBG'):
                    import traceback as _tbj
                    print("  [!]قفلِ قابِ رنگی خطا:", flush=True)
                    _tbj.print_exc()
# نقشهٔ «فقطِ قابِ رنگی» جدا نگه داشته میشود تا
# _expand_donor_text_strips فقط قابِ رنگی را در donor آزاد
# کند (رنگِ قاب واردِ پرِ متن نشود) — دیوارِ تیره مثلِ قبل.
            self._page_colored_protect = _out_colj \
                if int(np.count_nonzero(_out_colj)) else None
# نقشهٔ «روکشِ حاشیه‌نویسیِ ورودی» (up0822):
# اسکرینشاتهایی که از اپهایِ ترجمهٔ دیگر میآیند یک لایهٔ
# حاشیه‌نویسی «چسبیده به متن» دارند — قابِ ششضلعیِ سبزِ
# اشباع + شستشویِ نیمه‌شفافِ سبز رویِ کلِ بلوکِ متن. قانونِ
# 206j/n این قاب را از پاکسازی و کامپوز «محرمانه» میکند تا
# رنگش واردِ پر نشود → نتیجه: قابِ سبز + شستشو در خروجیِ
# نهایی زنده میماند = «هرنگی لگه بشه قبول نمیکنم».
# تشخیصِ ایمن (فقط حالتِ قطعی): حلقهٔ اطرافِ بلوکِ متن
# «تقریباً خنثیِ یکنواخت» باشد (سفید/خاکستریِ حباب —
# std≤۳۴ و S≤۳۰) و داخلِ هالِ پالیها پیکسلِ «رنگیِ»
# (S≥۲۴) بهاندازهٔ کافی باشد (≥۵٪ هال) → کلِ آن ناحیهٔ
# رنگی مثلِ خودِ متن پاک و منتقل میشود؛ LaMa با حلقهٔ
# سفیدِ دورش سفیدِ تمیز پر میکند. حبابِ رنگی (زردِ img6)
# و آسمانِ اشباعِ وبتون → حلقه S بالاست → رد (بی‌خطر).
            try:
                _anl = np.zeros((h, w), dtype=np.uint8)
                _flatm = np.zeros((h, w), dtype=np.uint8)
                _fill = np.zeros((h, w, 3), dtype=np.uint8)
                _hsv_an = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
                _gray_an = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                _nsat_an = 0
                for _rg_an in (regions or []):
                    try:
                        if (getattr(_rg_an, "kind", "") or "") \
                                in ("promo", "sfx"):
                            continue
                        _pls_an = []
                        for _p_an in (getattr(_rg_an, "ocr_polys", None)
                                      or []):
                            try:
                                _pp_an = np.asarray(
                                    _p_an, dtype=np.float32).reshape(-1, 2)
                            except Exception:
                                continue
                            if _pp_an.shape[0] >= 3:
                                _pls_an.append(_pp_an)
                        if not _pls_an:
                            continue
                        _rx, _ry, _rw2, _rh2 = \
                            [int(v) for v in _rg_an.rect]
# هالِ پالیهایِ این ناحیه + ۱۲px = قلمروِ روکش
                        _hz = np.zeros((h, w), dtype=np.uint8)
                        try:
                            _hull_cv = cv2.convexHull(
                                np.rint(np.concatenate(
                                    _pls_an, axis=0)).astype(np.int32))
                            cv2.fillPoly(_hz, [_hull_cv], 255)
                        except Exception:
                            _allp = np.concatenate(_pls_an, axis=0)
                            _hz[max(0, int(_allp[:, 1].min())):
                                int(_allp[:, 1].max()) + 1,
                                max(0, int(_allp[:, 0].min())):
                                int(_allp[:, 0].max()) + 1] = 255
                        _hz_raw = _hz.copy()
                        _hz = cv2.dilate(
                            _hz, np.ones((25, 25), np.uint8))
# «شکاف»: باندِ ۶..۲۷px دورِ متنِ خام =
# درونِ روکش (بینِ متن و قاب). حبابِ سفیدِ واقعی:
# شکاف = سفیدِ تخت. روکش رویِ هنر (پنلِ راستِ
# up0822): شکاف = پوست/بافت — حلقهٔ بیرونی به
# حاشیهٔ سفیدِ صفحه می‌رسد و غلط می‌شد.
                        _gap = cv2.subtract(
                            cv2.dilate(_hz_raw, np.ones((55, 55),
                                                        np.uint8)),
                            cv2.dilate(_hz_raw, np.ones((13, 13),
                                                        np.uint8)))
# حلقه = باندِ ~۳۰px دورِ هال (منهایِ خودِ هال)
# مستطیلِ ناحیه خودش میتواند هماندازهٔ روکش باشد
# (تشخیصِ حباب، هگزاگونِ حاشیه‌نویسی را میبوسد)
# پس حلقهٔ «rect+16 منهایِ هال» خالی میشد.
                        _rz = cv2.subtract(
                            cv2.dilate(_hz, np.ones((89, 89), np.uint8)),
                            cv2.dilate(_hz, np.ones((31, 31), np.uint8)))
# محدود به حوالیِ ناحیه (نه فراتر از ۶۰px بیرونِ
# مستطیلِ ناحیه — دور از هنرِ بی‌ربط)
                        _cl = np.zeros((h, w), dtype=np.uint8)
                        _cl[max(0, _ry - 60):min(h, _ry + _rh2 + 60),
                               max(0, _rx - 60):
                               min(w, _rx + _rw2 + 60)] = 255
                        _rz = cv2.bitwise_and(_rz, _cl)
                        _n_rz = int(np.count_nonzero(_rz))
                        if _n_rz < 400:
                            continue
# «شاهدِ سبز»: جوهرِ رنگیِ داخلِ هال اگر
# عمدتاً سبزفام باشد (هیویِ ۳۵..۸۵ — رنگِ کلاسیکِ
# هایلایتِ اپهایِ ترجمه)، خودش گواهِ روکش است و
# گاردهایِ حلقه (که پنلِ شلوغ را رد میکنند — ناحیهٔ
# «ONE CLEAN RIGHT HOOK» در up0822 با rstd=۹۰ از
# فیلتر میافتاد) دور زده میشوند. متنِ واقعیِ کمیک
# سبزِ خالص نیست؛ قابِ حاشیه‌نویسی هست.
# نکتهٔ S≥۶۰: fringeیِ JPEG دورِ متنِ سفید-روی-
# مشکی (lang_ko — S=۲۴..۶۰) شاهد نیست؛ فقط قلبِ
# اشباعِ قاب.
                        try:
                            _cin = (_hz > 0) \
                                & (_hsv_an[..., 1] >= 60) \
                                & (_hsv_an[..., 2] >= 60)
                            _chue = _hsv_an[..., 0][_cin]
                            _gproof = False
                            if _chue.size >= 200:
                                _dH = np.abs(_chue - 60.0)
                                _dH = np.minimum(_dH,
                                                    180.0 - _dH)
                                _gproof = float(
                                    (_dH <= 25.0).mean()) >= 0.60
                            else:
                                _gproof = False
                        except Exception:
                            _gproof = False
                        if not _gproof:
# حلقه فقط «روشنِ» خودش را نشانِ
# زمینه میدهد: باندِ دورِ بلوک، دیوارِ تیرهٔ
# حباب/هنر هم دارد (rstd تا ۱۰۰ رویِ up0822)
# زمینهٔ واقعی = پیکسلهایِ «روشنِ کم‌اشباعِ»
# حلقه (کاغذ/داخلِ حبابِ سفید).
                            _rzpx = _rz > 0
                            _rv_an = _hsv_an[..., 2][_rzpx]
                            _rs_an = _hsv_an[..., 1][_rzpx]
                            _br = (_rv_an >= 160.0) \
                                & (_rs_an <= 35.0)
                            _bfrac = float(_br.mean()) \
                                if _br.size else 0.0
                            if _bfrac < 0.35:
                                continue
                            _rgray = _gray_an[_rzpx][_br] \
                                if bool(_br.any()) else None
                            if _rgray is None \
                                    or float(np.std(_rgray)) > 26.0:
                                continue  # حتی روشنها هم ناهموار — هنر
                            _rsv = _hsv_an[_rzpx][_br]
                            if float(np.median(_rsv[:, 1])) > 30.0:
                                continue  # حلقهٔ رنگی (زرد/آسمان) — رد
# «سفیدِ تختِ واقعی» از «شکافِ درونِ
# روکش» سنجیده میشود (نه حلقهٔ بیرونی که تا
# حاشیهٔ سفیدِ صفحه می‌رسد): شکافِ «تختِ سفیدِ
# بی‌بافت» = حبابِ سفیدِ واقعی → پرِ تختِ سفید.
# شکافِ هنری حتی وقتی شستشویِ سبز آن را کم‌اشباعِ
# روشن کرده، «بافت» دارد (هاشور/اسکرین‌تون —
# انرژیِ فرکانسِ بالا) → LaMa (پنلِ راستِ up0822).
                        try:
                            _gpx = _gap > 0
                            _gv = _hsv_an[..., 2][_gpx]
                            _gs = _hsv_an[..., 1][_gpx]
                            _gb = (_gv >= 220.0) & (_gs <= 25.0)
                            _gfrac = float(_gb.mean()) \
                                if _gb.size else 0.0
                            _hf = 99.0
                            try:
                                _med = cv2.medianBlur(
                                    _gray_an, 5)
                                _hf_in = np.abs(
                                    _gray_an.astype(np.int16)
                                    - _med.astype(np.int16))
                                _hf = float(np.median(
                                    _hf_in[_gpx]))
                            except Exception:
                                pass
                            _whiteflat = (
                                _gfrac >= 0.45
                                and bool(_gb.any())
                                and float(np.median(_gv[_gb]))
                                >= 240.0
                                and _hf <= 3.0)
                        except Exception:
                            _whiteflat = False
                        if os.environ.get("MANGA_ANNOTDBG") == "2":
                            try:
                                _ovw = int(np.count_nonzero(
                                    (_hz > 0)
                                    & (_hsv_an[..., 1] >= 24)
                                    & (_hsv_an[..., 2] >= 60)))
                                print(f"    rect=({_rx},{_ry},"
                                      f"{_rw2}x{_rh2}) "
                                      f"colpx={_ovw} "
                                      f"gap={int((_gap > 0).sum())} "
                                      f"gfrac={_gfrac:.2f} "
                                      f"gV={float(np.median(_gv[_gb])) if bool(_gb.any()) else -1:.0f} "
                                      f"ghf={_hf:.1f} "
                                      f"flat={_whiteflat}",
                                      flush=True)
                            except Exception:
                                pass
# پیکسلهایِ رنگیِ داخلِ هال = روکشِ حاشیه‌نویسی
                        _col_an = ((_hsv_an[..., 1] >= 24)
                                   & (_hsv_an[..., 2] >= 60))
                        _ov = ((_hz > 0) & _col_an)
                        _n_ov = int(np.count_nonzero(_ov))
# حضور = رنگِ فراوان (S≥۲۴ — شستشو)
# + «قابِ سبزِ اشباع» (S≥۶۰، هیویِ سبزِ ۴۰..۸۰
# ≥۱۵۰px): fringeیِ JPEG (lang_ko — هیویِ آبیِ
# ۱۰۰..۱۲۰) و متنِ آبی-خاکستری قابِ سبز ندارند.
                        _n = 0
                        try:
                            _hue = _hsv_an[..., 0].astype(np.int32)
                            _n = int(np.count_nonzero(
                                (_hz > 0)
                                & (_hsv_an[..., 1] >= 60)
                                & (_hsv_an[..., 2] >= 60)
                                & (_hue >= 40) & (_hue <= 80)))
                        except Exception:
                            _n = 0
                        if _n_ov < max(400, int(0.03 * int(
                                np.count_nonzero(_hz)))) \
                                or _n < 150:
                            continue
# ناحیهٔ روکش = هالِ متن + ۲۵px
# (داخلِ جعبه) ∪ کمانهایِ نازکِ رنگیِ قاب تا
# ~۸۱px (محدود به مستطیلِ ناحیه + ۲۴px). جعبهٔ
# حاشیه‌نویسی خودش «جعبهٔ سفید» است — پرِ تختِ
# سفیدِ همانِ داخلِ جعبه (شکاف) درست است؛ هنرِ
# پشتِ جعبه اساساً در اورجینال هم پنهان است.
                        _ov = (_hz > 0)
                        try:
                            _clb = np.zeros((h, w), dtype=np.uint8)
                            _clb[max(0, _ry - 24):
                                    min(h, _ry + _rh2 + 24),
                                    max(0, _rx - 24):
                                    min(w, _rx + _rw2 + 24)] = 255
                            _hz_far2 = cv2.dilate(
                                _hz, np.ones((163, 163), np.uint8))
                            _far = ((_hz_far2 > 0) & _col_an
                                       & (~(_hz > 0))
                                       & (_clb > 0))
                            if bool(_far.any()):
                                _nz, _lbb, _stb, _ = \
                                    cv2.connectedComponentsWithStats(
                                        _far.astype(np.uint8), 8)
                                _thin = np.zeros_like(_far)
                                for _ci in range(1, _nz):
                                    _ar = int(_stb[
                                        _ci, cv2.CC_STAT_AREA])
                                    if _ar < 4 or _ar > 12000:
                                        continue
                                    _cm = (_lbb == _ci)
                                    try:
                                        _dt3 = cv2.distanceTransform(
                                            _cm.astype(np.uint8),
                                            cv2.DIST_L2, 3)
                                        if float(_dt3.max()) * 2.0 > 14.0:
                                            continue  # قطور = هنر
                                    except Exception:
                                        continue
                                    _thin |= _cm
# حاشیهٔ آنتیآلیاسِ قاب (سبزِ کماشباعِ
# S<۲۴ زیرِ آستانه میماند = ردِ کم‌رنگ)
# → ۳px دیلیت دورِ هر کمان
                                _thin = cv2.dilate(
                                    _thin.astype(np.uint8),
                                    np.ones((7, 7), np.uint8)) > 0
                                _ov = _ov | _thin
                        except Exception:
                            pass
# دیوار/ساختارِ تیره (protect) هرگز پاک نشود
                        _ov = _ov & (out == 0)
                        _n_ov = int(np.count_nonzero(_ov))
                        if _n_ov < 400:
                            continue
                        _anl[_ov] = 255
# رنگِ پر = میانهٔ پیکسلهایِ «روشنِ» حلقه — فقط
# برایِ نواحیِ «سفیدِ تختِ واقعی»؛ نواحیِ هنری از
# donor (LaMa) می‌گیرند. LaMa رویِ ناحیهٔ شسته‌شده
# خودش شستشو را زمینه میپندارد و سبز میسازد؛ پرِ
# تختِ حلقه چون حلقه تخت است درست است (عینِ 133).
                        if _whiteflat:
                            _flatm[_ov] = 255
# رنگِ پر = میانهٔ «سفیدِ شکاف» (داخلِ جعبه) —
# جعبهٔ حاشیه‌نویسی خودش سفید است؛ حلقهٔ بیرونی
# ممکن است هنر/خاکستری باشد (پنلِ راست = 224).
                            try:
                                _fc = np.median(
                                    image[_gpx][_gb], axis=0)
                                _fill[_ov] = np.clip(
                                    np.rint(_fc), 0, 255).astype(
                                        np.uint8)
                            except Exception:
                                pass
                        _nsat_an += 1
                    except Exception:
                        continue
                self._page_annotation_overlay = _anl \
                    if int(np.count_nonzero(_anl)) else None
                self._page_annotation_flat = _flatm \
                    if int(np.count_nonzero(_anl)) else None
                self._page_annotation_fill = _fill \
                    if int(np.count_nonzero(_anl)) else None
                try:
                    _dp2 = os.environ.get("MANGA_DUMP", "")
                    if _dp2:
                        cv2.imwrite(_dp2 + "_overlay.png", _anl)
                        cv2.imwrite(_dp2 + "_flat.png", _flatm)
                        cv2.imwrite(_dp2 + "_fill.png", _fill)
                        print("[DUMP] annot ->", _dp2, flush=True)
                except Exception:
                    pass
                if _nsat_an and (self.debug
                                 or os.environ.get("MANGA_ANNOTDBG")):
                    try:
                        print(f"  [*]روکشِ حاشیه‌نویسی: "
                              f"{int(np.count_nonzero(_anl))}px در "
                              f"{_nsat_an} ناحیه — پاک میشود",
                              flush=True)
                    except Exception:
                        pass
            except Exception:
                self._page_annotation_overlay = None
                self._page_annotation_flat = None
                self._page_annotation_fill = None
# بنرِ تبلیغ هرگز protect نمی‌شود: سایه/لبهٔ تیرهٔ بنر
# «ساختارِ نازکِ تیره» حساب می‌شد → از ماسکِ LaMa کم می‌شد →
# بنفشِ بنر در ورودیِ مدل می‌ماند و خروجیِ «صورتی/بنفشِ خیالی»
# می‌ساخت (بازتولیدِ سندباکس: بنرِ ASURASCANS.COM)
            for _pbP in (getattr(self, "_promo_rect_boxes", None) or []):
                try:
                    _qx0 = max(0, int(_pbP[0]))
                    _qy0 = max(0, int(_pbP[1]))
                    _qx1 = min(w, int(_pbP[2]))
                    _qy1 = min(h, int(_pbP[3]))
                    if _qx1 > _qx0 and _qy1 > _qy0:
                        out[_qy0:_qy1, _qx0:_qx1] = 0
                except Exception:
                    pass
            if not np.any(out):
                return None
            _out_d = cv2.dilate(out, np.ones((3, 3), np.uint8))
            for _pbP in (getattr(self, "_promo_rect_boxes", None) or []):
                try:
                    _qx0 = max(0, int(_pbP[0]))
                    _qy0 = max(0, int(_pbP[1]))
                    _qx1 = min(w, int(_pbP[2]))
                    _qy1 = min(h, int(_pbP[3]))
                    if _qx1 > _qx0 and _qy1 > _qy0:
                        _out_d[_qy0:_qy1, _qx0:_qx1] = 0
                except Exception:
                    pass
            return _out_d
        except Exception:
            return None

    @staticmethod
    def _expand_promo_rect(image: np.ndarray,
                           rx0: int, ry0: int, rx1: int, ry1: int):
        """ — بنرِ تبلیغ تقریباً همیشه بزرگ‌تر از باکسِ OCR است:
        قابِ سفید، سایه، و ماسکوت/لوگویِ کنارِ متن (نمونهٔ ASURASCANS.COM:
        لوگو تا ۲۹px بیرونِ باکسِ OCR). پدِ ثابت برایِ قاب/سایه + رشدِ
        hue-محور برایِ لوگویِ رنگیِ چسبیده. طبقِ سبکِ کاربر «حباب خراب شه
        یا بیشتر پاک شه اشکال نداره» — رشد محتاطانه ولی کامل."""
        try:
            h, w = image.shape[:2]
# پدِ ثابتِ سخاوتمندانه: قابِ سفید (±)، سایه، و ماسکوتِ کِرمِ
# کنارِ بنر (ماسکوتِ ASURA «کرم» است — hue‌اش با زمینهٔ بژ
# یکسان است و با hue پیدا نمی‌شود؛ نمونه: تا +۲۹px بیرونِ OCR)
            rx0 = max(0, int(rx0) - 22)
            ry0 = max(0, int(ry0) - 14)
            rx1 = min(w, int(rx1) + 30)
            ry1 = min(h, int(ry1) + 24)
            for _ in range(2):
                wx0, wy0 = max(0, rx0 - 48), max(0, ry0 - 28)
                wx1, wy1 = min(w, rx1 + 48), min(h, ry1 + 28)
                roi = image[wy0:wy1, wx0:wx1]
                if roi.size == 0:
                    break
                hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                _p = ((hsv[..., 0] >= 95) & (hsv[..., 0] <= 178)
                      & (hsv[..., 1] >= 45) & (hsv[..., 2] >= 25))
                ys, xs = np.nonzero(_p)
                if ys.size < 40:
                    break
                px0 = int(wx0 + int(xs.min()))
                px1 = int(wx0 + int(xs.max())) + 1
                py0 = int(wy0 + int(ys.min()))
                py1 = int(wy0 + int(ys.max())) + 1
                _nx0 = min(rx0, px0)
                _ny0 = min(ry0, py0)
                _nx1 = max(rx1, px1)
                _ny1 = max(ry1, py1)
                if (_nx0, _ny0, _nx1, _ny1) == (rx0, ry0, rx1, ry1):
                    break
                rx0, ry0, rx1, ry1 = _nx0, _ny0, _nx1, _ny1
        except Exception:
            pass
        return int(rx0), int(ry0), int(rx1), int(ry1)

    def _bubble_interior_sweep(self, image: np.ndarray,
                               cleaned: np.ndarray,
                               regions: List["TextRegion"]) -> int:
        """ — جاروی لکه‌هایِ محوِ داخلِ حباب‌هایِ سفیدِ تمیز.
        بعد از پاکسازی، هالهٔ خاکستریِ محو (halo حروف/JPEG) داخلِ حباب
        می‌ماند — نمونه‌هایِ واقعیِ صفحهٔ TIME BOMB: «BUT I LIKE IT HERE.»
        (لکهٔ وسطِ حباب)، «MR. JUN~» (نقطهٔ خاکستری)، «GUARD» (سایهٔ
        کم‌رنگ). فقط حباب‌هایی که اینتریورِ معتبر با دیوارِ تیره و
        زمینهٔ یکدستِ روشن دارند اسکن می‌شوند؛ بلاب‌هایِ خاکستریِ کوچکِ
        نزدیکِ محلِ متنِ قبلی با TELEA پر می‌شوند.
        گاردها: بلاب باید نزدیکِ جوهرِ متنِ اصلی باشد، کم‌اشباع (خاکستری
        نه نقاشیِ رنگی)، و مجموعِ بلاب‌ها ≤ ۲۵٪ اینتریور."""
        n_fix = 0
        try:
            h, w = cleaned.shape[:2]
        except Exception:
            return 0
        for r in regions:
            try:
                if (getattr(r, "kind", "") or "") != "dialogue":
                    continue
                x, y, rw, rh = [int(v) for v in r.rect]
            except Exception:
                continue
            M = 30
            x0, y0 = max(0, x - M), max(0, y - M)
            x1, y1 = min(w, x + rw + M), min(h, y + rh + M)
            if x1 - x0 < 32 or y1 - y0 < 32:
                continue
# ناحیهٔ عظیم (بنر/پروموی تمام‌صفحه در نوارِ بلند)
# → کراپِ چند ده مگاپیکسلی و انفجارِ رم (OOM) → رد.
# سقفِ ۱۵۰K px حباب‌هایِ معمولی را پوشش می‌دهد؛ نوارهایِ عریضِ
# پرومو/راوی که حبابِ سفیدِ یکدست نیستند رد می‌شوند
            if (x1 - x0) * (y1 - y0) > 150_000:
                continue
            oc = image[y0:y1, x0:x1]
            cc = cleaned[y0:y1, x0:x1]
            if oc.size == 0 or cc.shape != oc.shape:
                continue
            try:
                g = cv2.cvtColor(oc, cv2.COLOR_BGR2GRAY)
                gc = cv2.cvtColor(cc, cv2.COLOR_BGR2GRAY)
                hsv = cv2.cvtColor(cc, cv2.COLOR_BGR2HSV)
# بذر = جوهرِ متنِ اصلی (برای پیدا کردنِ اینتریورِ حباب)
                med_o = float(np.median(g))
                zone = ((g < med_o - 60.0) | (g > min(255.0, med_o + 60.0))
                        ).astype(np.uint8) * 255
                if int(cv2.countNonZero(zone)) < 80:
                    continue
                interior = self._bubble_interior_mask(g, zone, erode_iters=0)
                if interior is None or int(cv2.countNonZero(interior)) == 0:
                    continue
# اینتریور نباید از دیوار نشت کرده باشد — protect
# (دیوار/کادر) را از اینتریور کم کن و فقط بزرگ‌ترین جزیرهٔ
# باقی‌مانده (داخلِ واقعیِ حباب) را نگه دار؛ وگرنه سویپ روی
# هنرِ بیرونِ حباب (گونه/مویِ کنارِ دیوار) بلاب می‌بیند و
# TELEA روی صورت لکه می‌سازد
                _pp0 = getattr(self, "_page_protect", None)
                if _pp0 is not None:
                    try:
                        interior = cv2.bitwise_and(
                            interior, cv2.bitwise_not(_pp0))
                    except Exception:
                        pass
                try:
                    _n_i, _l_i, _s_i, _ = cv2.connectedComponentsWithStats(
                        (interior > 0).astype(np.uint8), 8)
                    if _n_i > 2:
                        _best, _best_a = 0, 0
                        for _i in range(1, _n_i):
                            _a = int(_s_i[_i, cv2.CC_STAT_AREA])
                            if _a > _best_a:
                                _best_a, _best = _a, _i
                        interior = ((_l_i == _best).astype(np.uint8)) * 255
                except Exception:
                    pass
                _area = float(interior.shape[0] * interior.shape[1])
                _fa = float(cv2.countNonZero(interior))
                if not (0.10 * _area <= _fa <= 0.94 * _area):
                    continue
# چکِ نشت: اینتریورِ واقعیِ حباب هیچ‌وقت به لبهٔ
# کراپ (rect+۳۰px) نمی‌رسد؛ اگر برسد یعنی از شکافِ JPEGِ دیوار
# به پنلِ بیرونی نشته (پنلِ سفید همه‌جا متصله) → سویپ دیوار و
# هنر را می‌خورد (حبابِ «YOU'RE LEAVING…» که کلاً خراب شد)
                try:
                    _touch = (int(np.count_nonzero(interior[0, :]))
                              + int(np.count_nonzero(interior[-1, :]))
                              + int(np.count_nonzero(interior[:, 0]))
                              + int(np.count_nonzero(interior[:, -1])))
                    if _touch >= 6:
                        continue
                except Exception:
                    pass
# دیوارِ معتبر: حلقهٔ دورِ اینتریور باید تیره‌تر باشد
                _ring = cv2.dilate(interior, np.ones((5, 5), np.uint8))
                _ring = (_ring > 0) & (interior == 0)
                if int(np.count_nonzero(_ring)) < 30:
                    continue
                if float(np.median(g[_ring])) > float(
                        np.median(g[interior > 0])) - 40.0:
                    continue
# اینتریورِ یکدستِ روشن (حبابِ سفیدِ تمیز)؟
# فرسایشِ ۷px — با erode_iters=0 اینتریور از
# شکافِ ریزِ دیوار (JPEG) به بیرون نشت می‌کند و خودِ دیوار
# داخلِ اینتریور می‌افتد → سویپ دیوار را «بلاب» می‌خواند و
# می‌خورد (دقیقاً همان لکه‌محوییِ باقی‌مانده روی دیوار)
                _int_e = cv2.erode(interior, np.ones((7, 7), np.uint8))
                if int(cv2.countNonZero(_int_e)) < 400:
                    continue
# نوارِ امن — فقط پیکسل‌هایِ حداقل ~۹px داخلِ اینتریور
# مجاز به بلاب/پولیش‌اند؛ بلابِ چسبیده‌به-دیوار = دیوارِ
# فرسوده/سایهٔ دیوار است نه هالهٔ متن
                _edge_safe = cv2.erode(interior, np.ones((19, 19), np.uint8))
                if int(cv2.countNonZero(_edge_safe)) < 200:
                    continue
                med_c = float(np.median(gc[_int_e > 0]))
                if med_c < 185.0:
                    continue
                if float((gc[_int_e > 0] >= med_c - 30.0).mean()) < 0.90:
                    continue
# نزدیکی به جوهرِ اصلی (هالوی حروف) — نقاشیِ دور از متن
# هرگز جارو نمی‌شود
                _ink_d = cv2.dilate(zone, np.ones((17, 17), np.uint8)) > 0
# سقفِ مکانی — بلاب‌ها فقط تا ~۱۲px بیرونِ مستطیلِ
# متنِ خودِ ناحیه. اینتریورِ نشتی از شکافِ دیوار (که protect
# هم آنجا سوراخ است) نمی‌تواند به گونه/مویِ بیرونِ حباب برسد
                try:
                    _rb = np.zeros_like(_int_e)
                    _ry0, _rx0 = max(0, y - y0), max(0, x - x0)
                    _ry1 = min(_int_e.shape[0], y + rh - y0)
                    _rx1 = min(_int_e.shape[1], x + rw - x0)
                    _rb[_ry0:_ry1, _rx0:_rx1] = 255
                    _rb = cv2.dilate(_rb, np.ones((25, 25), np.uint8))
                    _rb_band = (_rb > 0)
                except Exception:
                    _rb_band = None
# بلاب‌هایِ محو: تیره‌تر از زمینهٔ تمیز یا رنگیِ کم‌اشباع
                _dist = np.abs(
                    cc.astype(np.int16)
                    - np.array([med_c, med_c, med_c], dtype=np.int16)
                ).max(axis=2)
                _blobs = ((_int_e > 0) & (gc < med_c - 26.0)
                          & _ink_d).astype(np.uint8) * 255
                _blobs |= ((_int_e > 0) & (_dist > 30) & _ink_d
                           & (hsv[..., 1] < 60)).astype(np.uint8) * 255
# هالهٔ خیلی محو (ارواحِ بازسازیِ LaMa / JPEG halo)
# فقط در همسایگیِ ۲۵px جوهرِ متنِ اصلی — آستانهٔ ملایم‌تر
                try:
                    _blobs |= (((_int_e > 0) & (gc < med_c - 16.0) & _ink_d)
                               .astype(np.uint8) * 255)
                except Exception:
                    pass
# ساختارِ محافظت‌شده (دیوار/کادر) هرگز بلاب نیست
                _pp2 = getattr(self, "_page_protect", None)
                if _pp2 is not None:
                    try:
                        _blobs[_pp2[y0:y1, x0:x1] > 0] = 0
                    except Exception:
                        pass
                if _rb_band is not None:
                    _blobs[~_rb_band] = 0
# بلابِ نزدیکِ دیوار هرگز (TELEA دیوار را می‌خورد)
                try:
                    _blobs[_edge_safe == 0] = 0
                except Exception:
                    pass
                _blobs = cv2.morphologyEx(_blobs, cv2.MORPH_OPEN,
                                          np.ones((2, 2), np.uint8))
                _nb, _lb, _sb, _ = cv2.connectedComponentsWithStats(
                    _blobs, 8)
                _fix_m = None
                if _nb > 1:
                    keep = np.zeros_like(_blobs)
                    _tot = 0
                    for i in range(1, _nb):
                        a = int(_sb[i, cv2.CC_STAT_AREA])
                        if a < 10 or a > 0.08 * _fa:
                            continue
                        keep[_lb == i] = 255
                        _tot += a
                    if 0 < _tot <= 0.25 * _fa:
                        _fix_m = cv2.dilate(keep, np.ones((3, 3), np.uint8))
                        _fix_m = cv2.bitwise_and(_fix_m, _int_e)
                        if int(cv2.countNonZero(_fix_m)) < 10:
                            _fix_m = None
# پولیشِ سفید — موتیلینگِ محوِ بازسازیِ LaMa داخلِ
# حبابِ یکدست (ارواحِ خاکستریِ چرخانی) به رنگِ زمینه نرم شود
# پولیش فقط در همسایگیِ جوهرِ متنِ قبلی — نه کلِ
# داخلِ حباب (سایه/گرادیانِ ملایمِ قانونیِ حباب نباید تخت
# شود — «بعضی حباب‌ها یک کم دست خورده»)
                _polish = None
                try:
                    _mott = ((_int_e > 0) & (gc < med_c - 7.0)
                             & (gc >= med_c - 45.0) & _ink_d
                             & (_edge_safe > 0))
                    _frac = float(np.count_nonzero(_mott)) / float(
                        max(1, cv2.countNonZero(_int_e)))
                    if 0.02 <= _frac <= 0.50:
                        _bright = _int_e & (gc >= med_c - 7.0)
                        if int(np.count_nonzero(_bright)) >= 300:
                            _fill_col = np.median(
                                cc[_bright].astype(np.float32), axis=0)
                            _am = cv2.GaussianBlur(
                                _mott.astype(np.float32), (9, 9), 2.5)
                            _am = np.clip(_am * 1.6, 0.0, 1.0)[..., None]
                            _polish = (cc.astype(np.float32) * (1.0 - _am)
                                       + _fill_col[None, None, :] * _am)
                            _polish = np.clip(_polish, 0, 255).astype(np.uint8)
                except Exception:
                    _polish = None
                if _polish is not None:
                    cc = _polish
                if _fix_m is None and _polish is None:
                    continue
                if _fix_m is not None:
                    _inp = cv2.inpaint(cc, _fix_m, 4, cv2.INPAINT_TELEA)
                    cc = _inp
                cleaned[y0:y1, x0:x1] = cc
                n_fix += 1
            except Exception:
                continue
        return n_fix

# وارسیِ نهاییِ ضدِ خرابیِ EP — یک‌بار برای کلِ صفحه
# درست قبل از خروجِ clean_image. چرا آخرِ کار و نه بعد از هر باکس:
# ۱) وسطِ پایپ‌لاین، منطق‌هایِ بعدی (LFCM، ردِ گروهِ LaMa، سویپِ
# باقی‌مانده، پرِ دونورِ بلوکِ تیره) هنوز کارشان تمام نشده و
# وارسیِ میان‌راهی هم‌پوشانی/تناقض می‌سازد (تریگرهایِ کاذبِ 01)
# ۲) هر ترمیمِ میان‌راهی یک فراخوانیِ LaMaِ دیگر است → arenaِ ONNX
# رویِ نوارهایِ بلندِ وبتون (۹۰۰×۱۶۰۰۰، باکسِ ۴GB) OOM می‌دهد
# ۳) آنچه کاربر می‌بیند خروجیِ نهایی است — سنجش هم باید رویِ همان
# انجام شود. ماسکِ اتحادِ (فقط LaMa/OpenCV) از حلقه می‌آید
# کامپوننت‌هایِ به‌هم‌چسبیده جدا سنجیده می‌شوند؛ SFX/تبلیغ که هرگز
# پاک نشده‌اند ذاتاً بیرونِ ماسک‌اند و دست نمی‌خورند.
    def _final_verify_repair(self, cleaned: np.ndarray,
                             image: np.ndarray) -> None:
        u = getattr(self, "_verify_union", None)
        self._verify_union = None
        import os as _os
        if _os.environ.get("MANGA_DUMP_UNION") and u is not None:
            try:
                import cv2 as _cv
                _cv.imwrite(_os.environ["MANGA_DUMP_UNION"], (u.astype(np.uint8) * 255))
                print("[DUMP] union →", _os.environ["MANGA_DUMP_UNION"])
            except Exception as _e:
                print("[DUMP] fail", _e)
        if u is None or cleaned is None or image is None:
            return
        if not u.any():
            return
        if cleaned.shape[:2] != image.shape[:2]:
            return
# قراردادِ دو-عکسی: وارسی/ترمیم فقط رویِ چیزی که
# «واقعاً» به خروجی منتقل شده معنا دارد؛ بیرونِ نوارِ کامپوز
# پیکسلِ اورجینال است و هر «ترمیمی» آن = حذفِ هنر (کلِ حباب
# پاکیده — کیسِ ۱۰۱۸). خوشه‌ها و نوشتن‌ها به همین مجموعه قفل
# می‌شوند؛ اگر چیزی منتقل نشده، گارد کاری نمیکند.
        _cmpF = getattr(self, "_compose_final_cmp", None)
        if _cmpF is not None and _cmpF.shape == u.shape:
            u = u & (_cmpF > 0)
            if not u.any():
                return
        else:
            _cmpF = None
        try:
            import gc as _gc
            um = u.astype(np.uint8) * 255
# خوشه‌بندیِ نزدیک‌ها: حروف/خط‌هایِ یک بلوکِ متن
# (تا ۴۱px فاصله) یکی می‌شوند تا مثلِ باکسِ اصلیِ پایپ‌لاین
# یک‌جا سنجیده/ترمیم شوند؛ جداکردنِ حرف‌به‌حرف حلقهٔ سنجش را
# با خرابیِ همسایه آلوده می‌کند و ترمیم را می‌شکند (تستِ B/C/D)
            um_d = cv2.dilate(um, np.ones((41, 41), np.uint8))
            n_lab, lab, stats, _ = cv2.connectedComponentsWithStats(
                um_d, connectivity=8)
            pad = 26
            n_chk = 0
            n_fix = 0
            for li in range(1, n_lab):
                area = int(stats[li, cv2.CC_STAT_AREA])
                if area < 60:
                    continue
                x0 = int(stats[li, cv2.CC_STAT_LEFT])
                y0 = int(stats[li, cv2.CC_STAT_TOP])
                w_c = int(stats[li, cv2.CC_STAT_WIDTH])
                h_c = int(stats[li, cv2.CC_STAT_HEIGHT])
                X0 = max(0, x0 - pad)
                Y0 = max(0, y0 - pad)
                X1 = min(cleaned.shape[1], x0 + w_c + pad)
                Y1 = min(cleaned.shape[0], y0 + h_c + pad)
                if (X1 - X0) < 12 or (Y1 - Y0) < 12:
                    continue
# ماسکِ واقعیِ اتحاد (نه دیلیت) — مثلِ crop_mskِ باکس
                comp = ((lab[Y0:Y1, X0:X1] == li) &
                        (um[Y0:Y1, X0:X1] > 0)).astype(np.uint8) * 255
                if int((comp > 0).sum()) < 60:
                    continue
                n_chk += 1
                _before = cleaned[Y0:Y1, X0:X1].copy()
                self._verify_repair_clean(cleaned, image, X0, Y0, X1, Y1,
                                          comp, "LaMa", limit=_cmpF)
                if not np.array_equal(_before, cleaned[Y0:Y1, X0:X1]):
                    n_fix += 1
                    _gc.collect()
# جاروی بازماندهٔ تیره (لبه/نوارِ سیاهِ کنارِ پاکشدهها)
# فقط داخلِ نوارِ کامپوز؛ بیرونِ نوار = اورجینال
            try:
                _nsw = self._dark_remnant_sweep(cleaned, u, limit=_cmpF)
                if _nsw and self.debug:
                    print(f"  [🧹] جاروی بازمانده: {_nsw} خوشهٔ تیره حذف شد",
                          flush=True)
            except Exception:
                if self.debug:
                    try:
                        import traceback as _tb2
                        print("  [!] جاروی بازمانده خطا داد:", flush=True)
                        _tb2.print_exc()
                    except Exception:
                        pass
            if self.debug and n_chk:
                print(f"  [*]وارسیِ نهاییِ EP: {n_chk} ناحیه سنجیده شد، "
                      f"{n_fix} ترمیم شد", flush=True)
        except Exception:
            if self.debug:
                try:
                    import traceback as _tb
                    print("  [!]وارسیِ نهاییِ EP خطا داد:", flush=True)
                    _tb.print_exc()
                except Exception:
                    pass
            pass

# جاروی بازماندهٔ تیره: لبه/نوارِ سیاهی که بعد از پاکسازی
# همسایهٔ مستقیمِ نواحیِ پاکشده میماند (سایهٔ لوگو/بنرِ بیرونِ ماسکِ
# متن — کیسِ ۱۰۱۸). فقط خوشهٔ تیرهٔ کوچکِ محصور در سفیدِ صافِ همسایه
# قاب/سایهٔ جعبههایِ سیستم (دور ازِ نواحیِ LaMa) و خطِ هنریِ بلند هرگز.
# «limit» = نوارِ کامپوز: هدف‌ها و نوشتن‌ها فقط داخلِ
# چیزی که واقعاً به خروجی منتقل شده؛ بیرونِ نوار = اورجینال (خطِ
# حباب/دُم/قابِ پنل هرگز هدف نمیشود — کیسِ «کلِ حباب پاکیده»).
    def _dark_remnant_sweep(self, cleaned: np.ndarray,
                            union: np.ndarray,
                            limit: Optional[np.ndarray] = None) -> int:
        try:
            if cleaned is None or union is None:
                return 0
            if cleaned.shape[:2] != union.shape[:2]:
                return 0
            g = cv2.cvtColor(cleaned, cv2.COLOR_BGR2GRAY)
        except Exception:
            return 0
        h, w = g.shape
        u8 = union if union.dtype == np.uint8 else \
            (union.astype(np.uint8) * 255)
        near = cv2.dilate(u8, np.ones((19, 19), np.uint8))
        zone = cv2.dilate(u8, np.ones((35, 35), np.uint8))
        dark = ((g < 150) & (zone > 0)).astype(np.uint8)
        _pa = getattr(self, "_prot_all", None)
        if _pa is not None and _pa.shape == g.shape:
            dark[(_pa > 0)] = 0
# قفلِ نوارِ کامپوز رویِ هدف‌ها
        if limit is not None and limit.shape == g.shape:
            dark[(limit <= 0)] = 0
        if int(dark.sum()) == 0:
            return 0
        dark_d = cv2.dilate(dark * 255, np.ones((5, 5), np.uint8)) > 0
        try:
            n_lab, lab, stats, _ = cv2.connectedComponentsWithStats(
                dark, connectivity=8)
        except Exception:
            return 0
        n_fix = 0
        for li in range(1, n_lab):
            area = int(stats[li, cv2.CC_STAT_AREA])
            if area < 25 or area > 3000:
                continue
            bw = int(stats[li, cv2.CC_STAT_WIDTH])
            bh = int(stats[li, cv2.CC_STAT_HEIGHT])
            if bw > 180 or bh > 120:
                continue
            x0 = int(stats[li, cv2.CC_STAT_LEFT])
            y0 = int(stats[li, cv2.CC_STAT_TOP])
            _crop = lab[y0:y0 + bh, x0:x0 + bw]
            _nc = near[y0:y0 + bh, x0:x0 + bw]
            if not bool(_nc[_crop == li].any()):
                continue
            ex0, ey0 = max(0, x0 - 18), max(0, y0 - 18)
            ex1, ey1 = min(w, x0 + bw + 18), min(h, y0 + bh + 18)
            lc = (lab[ey0:ey1, ex0:ex1] == li).astype(np.uint8) * 255
            ring = (cv2.dilate(lc, np.ones((31, 31), np.uint8)) > 0)
            ring &= ~(lc > 0) & (~dark_d[ey0:ey1, ex0:ex1])
            rg = g[ey0:ey1, ex0:ex1][ring]
            if rg.size < 60:
                continue
            if float((rg >= 238).mean()) < 0.70:
                continue
            if float(np.percentile(rg, 95)) < 248:
                continue
            bright = ring & (g[ey0:ey1, ex0:ex1] >= 238)
            if int(bright.sum()) < 30:
                continue
            col = np.median(cleaned[ey0:ey1, ex0:ex1][bright],
                            axis=0).astype(np.float32)
            fm = cv2.dilate(lc, np.ones((3, 3), np.uint8))
            al = (fm.astype(np.float32) / 255.0)[..., None]
# نوشتن هم فقط داخلِ نوارِ کامپوز
            if limit is not None and limit.shape == g.shape:
                _limC = (limit[ey0:ey1, ex0:ex1] > 0)
                if _limC.shape == al.shape[:2]:
                    al = al * _limC[..., None].astype(np.float32)
            if not bool((al > 0).any()):
                continue
            sub = cleaned[ey0:ey1, ex0:ex1]
            sub[:] = (sub.astype(np.float32) * (1.0 - al)
                      + col[None, None, :] * al).astype(np.uint8)
            n_fix += 1
        return n_fix

# وارسیِ پس از پاکسازی + ترمیمِ پلکانی (ضدِ خروجیِ بدِ EP)
# زمینه: رویِ برخی اجراکننده‌ها (CUDA/DML رویِ ویندوز) خروجیِ LaMa ناقص
# یا کثیف برمی‌گردد در حالی که همان ورودی رویِ CPU تمیز پاک می‌شود —
# دو نمونهٔ واقعیِ :
# الف) «GREEN MOON» روی پلاکِ بافت‌مند: نصفِ متن جا مانده (اسیرِ عمودی)
# ب) داخلِ حباب/جعبهٔ سفید: پرِ LaMa خاکستریِ کثیف به‌جای سفید
# این گارد مستقل از EP بعد از کامپوزِ هر باکس می‌دود. سنجش‌ها:
# ۱) جوهرِ باقی‌مانده: نسبتِ «پیکسلِ متن‌نما» (اختلاف از میانهٔ محلی)
# داخلِ ماسک در برابرِ حلقهٔ زمینه — بافتِ خودِ زمینه (نقطه‌چین/
# موزاییک) با نرخِ حلقه خنثی می‌شود
# ۲) تیرگیِ نسبی: رویِ حلقهٔ صاف، میانهٔ روشناییِ ناحیهٔ پاکشده اگر
# ≥ ۱۸ واحد از حلقه تیره‌تر باشد (نوارِ خاکستریِ حباب).
# ترمیمِ پلکانی — هر مرحله دوباره سنجیده می‌شود:
# ۱) LaMa دوباره با ماسکِ گشادِ ۱۷px (هاله/گلو هم می‌گیرد)
# ۲) LaMa دوباره با ماسکِ گشادِ ۳۳px
# ۳) پرِ هموارِ زمینه (_smooth_bg_fill) وگرنه TELEA
# ۴) TELEA با ماسکِ گشاد
# ۵) پرِ تختِ رنگِ حلقه — فقط وقتی حلقه واقعاً صاف است
# هیچ مرحله‌ای بیرونِ ماسک نمی‌نویسد؛ پیکسل‌هایِ قفل (_prot_all) و
# سقفِ (_page_raw_text_mask + کپِ ۲۵px) همیشه محترم هستند.
    def _verify_repair_clean(self, cleaned: np.ndarray, image: np.ndarray,
                             cx0: int, cy0: int, cx1: int, cy1: int,
                             crop_msk, method: str = "",
                             limit: Optional[np.ndarray] = None) -> None:
# «limit» = نقشهٔ نوارِ کامپوز (self._compose_final_cmp):
# تمامِ نوشتن‌هایِ ترمیم با آلفایِ صفر بیرونِ آن قفل می‌شوند —
# قراردادِ دو-عکسی: بیرونِ نوار = پیکسلِ اورجینال، همیشه.
        try:
            if method not in ("LaMa", "OpenCV"):
                return
            if cleaned is None or image is None or crop_msk is None:
                return
            m0 = (crop_msk > 0)
            if not m0.any():
                return
            h_c, w_c = m0.shape
            if h_c < 12 or w_c < 12:
                return
            pad = 26
            X0 = max(0, cx0 - pad)
            Y0 = max(0, cy0 - pad)
            X1 = min(cleaned.shape[1], cx1 + pad)
            Y1 = min(cleaned.shape[0], cy1 + pad)
            out = cleaned[Y0:Y1, X0:X1]
            orig = image[Y0:Y1, X0:X1]
            if out.shape[0] < 12 or out.shape[1] < 12:
                return
            m = np.zeros(out.shape[:2], np.uint8)
            m[cy0 - Y0:cy1 - Y0, cx0 - X0:cx1 - X0] = \
                m0.astype(np.uint8) * 255
            n_m = int((m > 0).sum())
            if n_m < 60:
                return
            _mk = 21 if min(out.shape[:2]) >= 21 else (
                15 if min(out.shape[:2]) >= 15 else 9)
            g = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)

            def _ink(g_, m_, r_):
                med = cv2.medianBlur(g_, _mk)
                hf = np.abs(g_.astype(np.int16) - med.astype(np.int16))
                ink_m = float((hf[m_ > 0] >= 26).mean()) \
                    if int((m_ > 0).sum()) >= 40 else 0.0
                ink_r = float((hf[r_] >= 26).mean()) \
                    if int(r_.sum()) >= 80 else 0.0
                return ink_m, ink_r

            md = cv2.dilate(m, np.ones((21, 21), np.uint8))
            mdin = cv2.dilate(m, np.ones((13, 13), np.uint8))
            ring = (md > 0) & (mdin == 0) & (m == 0)
            if int(ring.sum()) < 80:
                return
# ارزیابی/نوشتن تا ۹px بیرونِ ماسک (هاله/گلو):
# اسیرِ سبزِ دورِ «GREEN MOON» بیرونِ هستهٔ ماسک است؛ ارزیابیِ
# فقط-داخلِ ماسک آن را نمی‌بیند. نوشتن هم فقط تا همین ۹px است
# (داخلِ ماسکِ ترمیمِ ۱۷px) — هنرِ دورتر هرگز دست نمی‌خورد.
            m_eval = cv2.dilate(m, np.ones((19, 19), np.uint8))
            ink_m, ink_r = _ink(g, m_eval, ring)
            gm = float(np.median(g[m_eval > 0]))
            gr = float(np.median(g[ring]))
# گیتِ تیرگیِ پرِ کثیف (نوارِ خاکستریِ GPU در حبابِ سفید):
# برای بلوکِ چندخطی، حلقه خط‌هایِ خاکستریِ دیگر را هم می‌گیرد →
# میانهٔ حلقه آلوده است. سه سیگنالِ مقاوم:
# ۱) یکنواختیِ پر (پرِ خاکستریِ GPU یکدست است؛ بافتِ بازسازی‌شده
# پلاک/اسکری‌تون پهنایِ زیاد دارد)
# ۲) خنثاییِ رنگیِ پر (پرِ خرابِ GPU خاکستریِ خنثی است؛ آسمانِ
# گرادیانی آبی، پلاک آبی — B-R بزرگ)
# ۳) فاصله از صدک‌هایِ حلقه (p90 حلقه = سفیدِ حباب، p10 = تیرهٔ پنل)
# رویِ هستهٔ ماسک سنجیده می‌شود نه m_eval؛ وگرنه گپِ سفیدِ
# بینِ خط‌ها spread را می‌شکند
            _msel = m > 0
            try:
                _mp = np.percentile(g[_msel], [10, 90])
                mask_spread = float(_mp[1] - _mp[0])
            except Exception:
                mask_spread = 99.0
            try:
                _brc = out[..., 0].astype(np.int16) - \
                    out[..., 2].astype(np.int16)
                neutr = float(np.median(np.abs(_brc[_msel])))
            except Exception:
                neutr = 99.0
            try:
                _rp = np.percentile(g[ring], [10, 90])
                gap_dark = float(_rp[1]) - gm
            except Exception:
                gap_dark = 0.0
            try:
                _rq = np.percentile(g[ring], [10, 90])
                rs = float(_rq[1] - _rq[0])  # گسترهٔ صدکیِ حلقه (گیتِ پرِ تخت)
                rp90 = float(_rq[1])
            except Exception:
                rs = float(g[ring].std())
                rp90 = float(np.percentile(g[ring], 90))
# بارِ سفیدِ سخت: داخلِ حباب/جعبهٔ سفیدِ تخت
# (حلقهٔ روشن و صاف) ترمیمِ «فقط-بد-نباشد» کافی نیست؛ دودِ
# کم‌رنگ (جوهرِ ۰.۰۳) هنوز به چشم می‌آید → مراحل ادامه پیدا
# می‌کنند تا پرِ ناب (LaMa گشادتر/هموار/تخت) به دست آید
            white_flat = (rs <= 16.0) and (rp90 >= 240.0)
# سنجشِ جوهر: هم نسبی (حلقه = خطِ پایهٔ بافت) هم tierِ مطلق —
# پلاکِ «GREEN MOON»: بافتِ حلقه ink_r≈0.13 است ولی پاکِ سالم
# ink_m≈0.01 دارد؛ متنِ نصفه‌پاک ≈0.32 → tierِ مطلقِ 0.22 می‌گیردش
# tierِ مطلق فقط وقتی که حلقه نسبتاً صاف است
# (ink_r≤0.18) فعال است تا زمینه‌هایِ بافت‌مند (ink_r تا 0.22+)
# تریگرِ کاذب نسازند؛ خرابیِ پرَخشن با tierِ پرزورِ 0.40 می‌آید
# کالیبراسیون رویِ رگرسیونِ CPU: tier1 از ۰٫۱۰→۰٫۱۵
# (چ264_9 crop@(575,3189) جوهرِ ۰٫۱۳ = بافتِ قانونیِ پنجره بود
# نه باقی‌مانده) — کیس‌هایِ واقعیِ GPU: A=۰٫۲۵+ (tier2)
# B=تیرگی، C=۰٫۳۲ (tier2)، D=تیرگی → همه سرِ جایشان
# FPِ 01 (جوهرِ ۰٫۲۳ خطِ موج‌دار) با گاردِ فقط-LaMa رویِ بافت
# و قفلِ خطِ هنری ردِ ترمیم می‌شود → خروجیِ دست‌نخورده
            bad_ink = (ink_m > max(0.15, ink_r * 2.0 + 0.04)) or \
                ((ink_m >= 0.22 and ink_r <= 0.18 and
                  ink_m > ink_r * 1.2 + 0.02) or
                 (ink_m >= 0.40 and ink_m > ink_r * 1.1 + 0.02))
# تیرگیِ نسبیِ آستانه ۲۲→۳۰ + حلقهٔ روشن (rp90≥۱۹۰):
# «پرِ کثیفِ سفید» فقط وقتی معنا دارد که اطراف روشن باشد؛ پنلِ
# تیرهٔ 012p1 (p90=۱۳۶) تریگرِ کاذب نمی‌سازد؛ نوارِ خاکستریِ
# واقعیِ GPU (۱۰۱۸) گپِ ۳۹ با حلقهٔ ۲۵۵ دارد
# p90ِ حلقه برایِ «متنِ سفید رویِ بنرِ سیاه»
# (هدرِ CHAPTER PAGE — img1018) کافی نیست: حلقه = بنرِ سیاه +
# نوارِ سفیدِ صفحه در ۳۱px → rp90=۲۵۵ و پرِ «سیاهِ درستِ» LaMa
# «تیرگی» پرچم میخورد → LaMa×۱۷/×۳۳ → بازگردانیِ اورجینال =
# کلِ متنِ بنر برمیگشت. حالا حلقه باید «عمدتاً» روشن باشد
# (≥۵۰٪ ≥۱۷۰) نه فقط صدکِ ۹۰.
            bad_gray = (mask_spread <= 22.0) and (neutr <= 14.0) and \
                (gap_dark >= 30.0) and (rp90 >= 190.0) and \
                (float((g[ring] >= 170.0).mean()) >= 0.50)
# دودِ متنِ بازمانده (ghost imprint): پرِ LaMa گاهی
# امضایِ کمرنگِ متنِ قبلی (۱۹۵–۲۵۰، اختلافِ فقط ۵–۲۵ از سفید)
# را نگه میدارد؛ «جوهرِ» hf≥۲۶ آن را نمیبیند و رویِ صفحهِ گوشی
# کاربر دیده میشود (۱۰۱۸: نرخِ دود تا ۰٫۱۴ در حبابِ دولوبه).
# فقط در زمینهٔ سفیدِ صاف (white_flat) معنا دارد؛ اندازهگیری روی
# هستهٔ فرسودهٔ ماسک تا لبهٔ فِدرِ blend شمرده نشود.
            _mcore = cv2.erode(m, np.ones((5, 5), np.uint8)) \
                if min(m.shape[:2]) > 7 else m
            if int((_mcore > 0).sum()) < 40:
                _mcore = m

            def _ghost_frac(g_):
# (نرخِ دود، روشناییِ نابِ هسته) — دود = 195..252
# coreW آستانهٔ زمینهٔ سفید است: پرِ بازسازی‌شدهٔ زمینهٔ
# بافت‌دار (هاف‌تون) خودش تیره است → coreW کم → گیت نمیگیرد
                v = g_[_mcore > 0]
                if v.size < 40:
                    return 0.0, 0.0
                gh = float(((v >= 195) & (v <= 252)).mean())
                cw = float((v >= 253).mean())
                return gh, cw

            ghost_m, corew_m = _ghost_frac(g)
# گیتِ زمینهٔ سفیدِ «واقعی»: دود فقط رویِ زمینهٔ
# سفید معنا دارد (بندِ بالای سرش همین را میگوید) ولی سنجهٔ
# قبلی corew روشناییِ «پرِ فعلی» بود نه زمینه → رویِ متنِ
# سفید-رو-سیاه (هدرِ ۱۰۱۸: پرِ سفیدِ LaMa رویِ نوارِ سیاه)
# تریگرِ کاذب می‌ساخت و tier6 کلِ نوار را سفید میکرد. حالا
# حلقهٔ واقعی باید روشن باشد (≥۴۵٪ پیکسلِ حلقه ≥۲۴۰).
            _rgw = float((g[ring] >= 240).mean())
            bad_ghost = (ghost_m >= 0.05) and (corew_m >= 0.55) and \
                (_rgw >= 0.45)
# «نویزِ توهمِ LaMa» (MANGA_LAMA_NOISEQC):
# حفرهٔ بزرگِ چندخطی در داوناسکیلِ پچِ ۳۸۴ «متنِ قلابیِ گری»
# میسازد که انرژیِ فرکانس-بالایش ≫ حلقهٔ روشنِ اطراف است ولی
# جوهرِ >=26 ندارد → پرچمهایِ بالا نمیگیرندش (بازتولیدِ A/B
# رویِ 700×11362 — لکهٔ کثیف). اینجا فقط پرچم؛ درمان در گامِ ۰.
            bad_noise = False
            _nq_in = _nq_lr = -1.0
            try:
                if _android_gate("MANGA_LAMA_NOISEQC") \
                        and int((m > 0).sum()) >= 4000:
                    _nq_hf = np.abs(g.astype(np.float32) -
                                    cv2.medianBlur(g, 31).astype(
                                        np.float32))
                    _nq_m = ring & (g >= 170.0)
                    _nq_n = int(_nq_m.sum())
                    if _nq_n >= 200:
                        _nq_in = float(np.median(_nq_hf[m > 0]))
                        _nq_lr = float(np.median(_nq_hf[_nq_m]))
                        bad_noise = _nq_in > 2.2 * _nq_lr + 4.0
            except Exception:
                bad_noise = False
            if not (bad_ink or bad_gray or bad_ghost or bad_noise):
                return
            if self.debug:
                try:
                    print(f"  [!]وارسیِ پس از پاکسازی crop@({cx0},{cy0}) "
                          f"ink={ink_m:.2f}/حلقه={ink_r:.2f} "
                          f"lum={gm:.0f}/p90={gap_dark + gm:.0f} "
                          f"spread={mask_spread:.0f} neutr={neutr:.0f} "
                          f"دود={ghost_m:.2f} "
                          f"({'جوهر' if bad_ink else ''}"
                          f"{'+تیرگی' if bad_gray else ''}"
                          f"{'+دود' if bad_ghost else ''}) → ترمیم",
                          flush=True)
                except Exception:
                    pass

# گیتِ «هنر/سایه» (فقط اندروید — MANGA_VERIFY_ARTSKIP):
# اگر تنها تریگر «جوهرِ» ضعیف باشد (ink<0.30) و بیش از ۴۰٪
# ناحیه خاکستریِ خنثی (سایه/بافتِ هنر — نه متنِ جامانده)
# LaMa×17/×33 هیچ‌وقت «OK» نمیشود (لاگِ گوشیِ 700×11362:
# crop@(573,3189) بوتهٔ تیره — ~۱۵-۳۰ ثانیه هدررفت در هر
# ناحیه، بارها) → ترمیم رد میشود. متنِ واقعی (ink≥0.30) و
# دودِ زمینهٔ سفید (bad_ghost) هرگز اینجا رد نمیشوند.
# PC بایت‌به‌بیت دست‌نخورده.
            if (_android_gate("MANGA_VERIFY_ARTSKIP") and bad_ink
                    and not (bad_gray or bad_ghost or bad_noise)
                    and ink_m < 0.30 and neutr >= 40.0):
                if self.debug:
                    try:
                        print(f"  [🔍]وارسی: جوهرِ ضعیف + زمینهٔ خنثیِ "
                              f"هنر/سایه crop@({cx0},{cy0}) → ترمیم رد شد",
                              flush=True)
                    except Exception:
                        pass
                return

# ماسکِ گشادِ محدود: قفل‌ها ممنوع، حداکثر ۲۵px از جوهرِ خام
            def _bounded(dil_k: int):
                wb = cv2.dilate(
                    m, cv2.getStructuringElement(
                        cv2.MORPH_ELLIPSE, (dil_k, dil_k)))
                try:
                    _pa = getattr(self, "_prot_all", None)
                    if _pa is not None:
                        _pac = _pa[Y0:Y1, X0:X1]
                        if _pac.shape == wb.shape:
                            wb[_pac > 0] = 0
                except Exception:
                    pass
                try:
                    _raw = getattr(self, "_page_raw_text_mask", None)
                    if _raw is not None and _raw.shape == image.shape[:2]:
                        _rc = cv2.dilate(
                            _raw[Y0:Y1, X0:X1],
                            cv2.getStructuringElement(
                                cv2.MORPH_ELLIPSE, (25, 25)))
                        wb = cv2.bitwise_and(wb, _rc)
                except Exception:
                    pass
                if int((wb > 0).sum()) < 50:
                    return None
                if float((wb > 0).mean()) > 0.92:
                    return None
                return wb

            def _blend(res_):
                alpha = cv2.GaussianBlur(m_eval, (7, 7), 2.0)
                alpha = np.minimum(alpha, m_eval)
# قفلِ نوارِ کامپوز: هیچ ترمیمی بیرونِ نوار
# نوشته نمیشود (خطِ حباب/قاب/نوارِ هدر دست‌نخورده)
                if limit is not None:
                    _limB = limit[Y0:Y1, X0:X1]
                    if _limB.shape == alpha.shape:
                        alpha = alpha * (
                            (_limB > 0).astype(np.uint8))
# قفلِ ساختار (ضدِ «حبابِ بیرون با حبابِ
# داخل یک رنگ»): هالهٔ ۱۹pxیِ m_eval وقتی متن به دیوارِ
# حباب چسبیده باشد از رویِ دیوار میگذشت و پرِ تختِ
# ترمیم (سفیدِ ناب/تختِ حلقه) دیوار را با رنگِ یکسان
# میپوشاند = بیرون و داخلِ حباب همرنگ. دیوار/قفلها
# (_prot_all = ساختارِ روشن + گلو + خطِ سراسری +
# page_protect) از نوشتنِ ترمیم خارج میشوند — همان
# قانونی که پرکنندههایِ اصلی از قبل دارند.
                try:
                    _pab = getattr(self, "_prot_all", None)
                    if _pab is not None:
                        _pacb = _pab[Y0:Y1, X0:X1]
                        if _pacb.shape == alpha.shape:
                            alpha = alpha * (
                                (_pacb == 0).astype(np.uint8))
                except Exception:
                    pass
                a3 = (alpha.astype(np.float32) / 255.0)[..., None]
                dst = out.astype(np.float32)
                bl = dst * (1.0 - a3) + res_.astype(np.float32) * a3
                cleaned[Y0:Y1, X0:X1] = bl.astype(np.uint8)

# سخت‌گیریِ مطلق برایِ مسیرِ پرِ خاکستری (بد_gray): پرِ سالمِ
# حباب تقریباً بی‌جوهر است (hf≈0.02)؛ توهمِ متنِ LaMa (وقتی
# حلقه به متنِ سالمِ اطراف آلوده است) تا 0.20 می‌رسد —
# گیتِ نسبی آن را نمی‌بیند → سقفِ مطلقِ 0.10
# مسیرِ دود هم سختگیریِ مطلق می‌خواهد (جوهرِ دود
# زیرِ آستانه است وگرنه گیتِ نسبی زود OK می‌کند)
            _strict = bool(bad_gray or bad_ghost)

            def _quality(g_res, what):
                im2, ir2 = _ink(g_res, m_eval, ring)
                gm2 = float(np.median(g_res[m_eval > 0]))
                try:
                    _rp2 = np.percentile(g[ring], [10, 90])
                    gd2 = float(_rp2[1]) - gm2
                except Exception:
                    gd2 = 0.0
                gh2, cw2 = _ghost_frac(g_res)
                bad2 = (im2 > max(0.15, ir2 * 2.0 + 0.04)) or \
                    ((im2 >= 0.22 and ir2 <= 0.18 and
                      im2 > ir2 * 1.2 + 0.02) or
                     (im2 >= 0.40 and im2 > ir2 * 1.1 + 0.02)) or \
                    ((mask_spread <= 22.0) and (neutr <= 14.0) and \
                     (gd2 >= 30.0) and (rp90 >= 190.0)) or \
                    (_strict and im2 > 0.10) or \
                    ((gh2 >= 0.05) and (cw2 >= 0.55))
                soft = bool((white_flat and
                             (im2 > 0.015 or gm2 < rp90 - 16.0))
                            or (gh2 > 0.015 and cw2 >= 0.55))
                if self.debug:
                    try:
                        _tag = 'OK' if not bad2 else 'هنوز بد'
                        if (not bad2) and soft:
                            _tag = 'OK-ولی-دوددار→ادامه'
                        print(f"    [🔍ترمیم] {what}: "
                              f"ink={im2:.2f}/حلقه={ir2:.2f} "
                              f"lum={gm2:.0f} → {_tag}",
                              flush=True)
                    except Exception:
                        pass
                return (not bad2), (not bad2 and not soft), im2

            fallback = None  # (res، برچسب) — خوب ولی نه ناب

# ۰ — — ضدِ «نویزِ توهمِ LaMa» در حفرهٔ بزرگ
# (فقط اندروید — MANGA_LAMA_NOISEQC): درمان = پرِ حلقهٔ روشن
# ارزان، بی‌نویز و همرنگِ زمینه. (پرچم در bad_noise بالای
# سر محاسبه شد.)
            try:
                if bad_noise:
                    if self.debug:
                        try:
                            print(f"    [🔍]ضدنویز: hf_in={_nq_in:.1f} "
                                  f"hf_ring={_nq_lr:.1f} "
                                  f"m={int((m > 0).sum())}px → ترمیم")
                        except Exception:
                            pass
                    _res0 = self._flat_fill_cluster(
                        orig, m, light_ring=True, fit_tol=13.0)
                    if _res0 is not None:
                        g0 = cv2.cvtColor(_res0,
                                          cv2.COLOR_BGR2GRAY)
                        ok_b0, ok_s0, _im0 = _quality(
                            g0, "پرِ حلقهٔ روشن-ضدنویز")
                        if ok_s0:
                            _blend(_res0)
                            return
                        if ok_b0 and fallback is None:
                            fallback = (_res0,
                                        "پرِ حلقهٔ روشن-ضدنویز")
            except Exception:
                pass

# ۱ و ۲ — LaMa دوباره با ماسکِ گشاد
# کپِ حافظه: برایِ کامپوننت‌هایِ بزرگِ (>۰٫۴Mpx)
# LaMaِ مجدد صدا زده نمی‌شود (arenaِ ONNX رویِ نوارهایِ بلندِ
# وبتون OOM می‌دهد) → همان مراحلِ OpenCV (هموار/TELEA/تخت)
# اندروید/میان‌بُرِ حلقهٔ روشن-تخت
# (MANGA_VERIFY_FASTFILL): وقتی حلقه «سفیدِ صاف» است
# (white_flat — لاگِ گوشیِ 700×11362: lum=254/p90=255/
# spread=3)، ترمیمِ LaMa×17 و ×33 هر دو «هنوز بد» میدهند و
# در نهایت پرِ تخت/سفید برنده است (~۲۰-۴۰ ثانیهٔ هدررفت در
# هر ناحیهٔ بد) → مستقیم به نردبانِ ارزان (هموار/TELEA/تخت).
# PC دست‌نخورده.
            _skip_lama = (_android_gate("MANGA_VERIFY_FASTFILL")
                             and bool(white_flat))
            _lama_cap = 400_000
            lama = None
            try:
                if not _skip_lama and \
                        out.shape[0] * out.shape[1] <= _lama_cap * 4:
                    lama = self._get_lama()
            except Exception:
                lama = None
# خروجِ زودهنگام (فقط اندروید —
# MANGA_VERIFY_FASTEXIT): اگر LaMa جوهر را نسبت به ورودی
# عملاً کم نکرد (Δ<0.02 — لاگِ گوشیِ 700×11362:
# crop@(573,3189) 0.17→0.16 و crop@(420,3261) 0.66→0.60
# بعدش هم تخت)، دورِ بعدی هم بیاثر است → دورِ بعدی و
# (برایِ جوهرِ ضعیفِ هنرمانند) تلاشِ ×۲ هم حذف — صرفهٔ
# ۱-۲ اینفرنسِ LaMa در هر ناحیهٔ بیاثر. PC دست‌نخورده.
            _fx = _android_gate("MANGA_VERIFY_FASTEXIT")
            _lama_gain = True
            if lama is not None:
                for _dk in (17, 33):
                    if _fx and not _lama_gain:
                        if self.debug:
                            try:
                                print(f"    [🔍]ترمیم: LaMa بیاثر "
                                      f"(Δجوهر<0.02) → دورِ بعدی حذف",
                                      flush=True)
                            except Exception:
                                pass
                        break
                    wb = _bounded(_dk)
                    if wb is None:
                        break
                    res1 = None
                    try:
                        _o = lama(orig, wb)
                        _ob = _o if isinstance(_o, np.ndarray) \
                            else np.array(_o)
                        if _ob.ndim == 2:
                            _ob = cv2.cvtColor(_ob, cv2.COLOR_GRAY2BGR)
                        else:
                            _ob = cv2.cvtColor(_ob, cv2.COLOR_RGB2BGR)
                        if _ob.shape[:2] == orig.shape[:2]:
                            res1 = _ob
                    except Exception:
                        res1 = None
                    if res1 is None:
                        continue
                    g1 = cv2.cvtColor(res1, cv2.COLOR_BGR2GRAY)
                    ok_b, ok_s, _im = _quality(g1, f"LaMa×{_dk}")
                    if ok_s:
                        _blend(res1)
                        return
                    _lama_gain = bool(_im < ink_m - 0.02)
                    if ok_b and fallback is None:
                        fallback = (res1, f"LaMa×{_dk}")

# ۳ — پرِ هموارِ زمینه، وگرنه TELEA — فقط رویِ حلقهٔ صافِ روشن
# رویِ بافت (پنجره/کفِ چ264_9) هموار/تخت = پاک‌کنِ بافت‌اند
            if not (rs <= 16.0):
                res2 = None
                _via = "skip-بافت"
            else:
                wb = _bounded(17)
                if wb is None:
                    wb = m
                res2 = None
                _via = ""
                try:
                    res2 = self._smooth_bg_fill(orig, wb)
                    if res2 is not None:
                        _via = "smooth"
                except Exception:
                    res2 = None
                if res2 is None:
                    try:
                        res2 = cv2.inpaint(orig, wb, 5, cv2.INPAINT_TELEA)
                        _via = "TELEA"
                    except Exception:
                        res2 = None
            if res2 is not None:
                g2 = cv2.cvtColor(res2, cv2.COLOR_BGR2GRAY)
                ok_b2, ok_s2, _im2b = _quality(g2, _via or "fill")
                if ok_s2:
                    _blend(res2)
                    return
                if ok_b2 and fallback is None:
                    fallback = (res2, _via or "fill")

# ۴ — TELEA با ماسکِ گشاد (اگر مرحلهٔ ۳ smooth بود)
            if _via == "smooth":
                try:
                    res3 = cv2.inpaint(orig, wb, 5, cv2.INPAINT_TELEA)
                    g3 = cv2.cvtColor(res3, cv2.COLOR_BGR2GRAY)
                    ok_b3, ok_s3, _im3b = _quality(g3, "TELEA-گشاد")
                    if ok_s3:
                        _blend(res3)
                        return
                    if ok_b3 and fallback is None:
                        fallback = (res3, "TELEA-گشاد")
                except Exception:
                    pass

# ۵ — پرِ تختِ رنگِ حلقه — فقط حلقهٔ واقعاً صاف
            try:
                if rs <= 16.0:
                    col = np.median(out[ring].astype(np.float32),
                                    axis=0).astype(np.float32)
                    flat = np.repeat(
                        col[None, None, :], out.shape[0], axis=0).repeat(
                            out.shape[1], axis=1)
                    g5 = cv2.cvtColor(flat.astype(np.uint8),
                                      cv2.COLOR_BGR2GRAY)
                    ok_b5, _ok_s5, _im5b = _quality(g5, "پرِ تختِ حلقه")
                    if ok_b5:
                        _blend(flat.astype(np.uint8))
                        return
            except Exception:
                pass
# ۶ — — پرِ سفیدِ ناب: زمینهٔ سفیدِ اثباتشده
# (coreW≥۰٫۵۵ یعنی پرِ کنونی عمدتاً سفیدِ ناب است و فقط دودِ
# متن مانده) → رنگِ میانهٔ پیکسلهایِ روشنِ حلقه (۲۵۵ حباب) کل
# ماسک را پر میکند؛ حباب/صفحهٔ سفید را دودِ ناپذیر میکند.
# بافت‌ها (coreW کم) هرگز به این مرحله نمی‌رسند.
            try:
                if corew_m >= 0.55:
                    rb = ring & (g >= 245)
# سفیدِ حلقه باید «غالب» باشد نه فقط حاضر
# رویِ نوارِ سیاهِ هدر، حاشیهٔ سفیدِ صفحه کافی بود که
# rb.sum≥۸۰ پاس شود و کلِ نوار سفید میشد
                    if int(rb.sum()) >= 80 and \
                            float((g[ring] >= 245).mean()) >= 0.45:
                        col6 = np.median(out[rb].astype(np.float32),
                                         axis=0).astype(np.float32)
                        flat6 = np.repeat(
                            col6[None, None, :], out.shape[0], axis=0).repeat(
                                out.shape[1], axis=1)
                        g6 = cv2.cvtColor(flat6.astype(np.uint8),
                                          cv2.COLOR_BGR2GRAY)
                        ok_b6, _s6, _im6b = _quality(g6, "پرِ سفیدِ ناب")
                        if ok_b6:
                            _blend(flat6.astype(np.uint8))
                            return
            except Exception:
                pass
# ۷ — — تلاشِ بزرگ‌نمایی‌شده (فقط اندروید —
# MANGA_VERIFY_UP2): وقتی هیچ پلهای جواب نداد (لاگِ گوشیِ
# 700×11362: crop@(420,3261) ink=0.66 — LaMa×17 و ×33 هر دو
# «هنوز بد» و در نهایت «خروجیِ فعلی ماند» = متنِ کثیفِ پابرجا)
# برش ×۲ بزرگ میشود (سقفِ 1600px — ضدفِ لهشدگیِ پچِ 384) و
# LaMa با ماسکِ گشادِ ×۲ دوباره ران میشود؛ بازسازیِ ریزتر
# جوهرِ جامانده را اغلب میگیرد. نتیجه با همان گیتِ کیفیت
# سنجیده میشود؛ قبول نشد → همان «خروجیِ فعلی ماند».
# PC بایت‌به‌بیت دست‌نخورده.
            if lama is not None and _android_gate("MANGA_VERIFY_UP2") \
                    and out.shape[0] * out.shape[1] <= 400_000 \
                    and not (_fx and not _lama_gain and ink_m < 0.30):
                try:
                    _wb = _bounded(17)
                    if _wb is None:
                        _wb = m
                    _uh = out.shape[0] * 2
                    _uw = out.shape[1] * 2
                    if _uh <= 1600 and _uw <= 1600:
                        _o2 = cv2.resize(
                            orig, (_uw, _uh),
                            interpolation=cv2.INTER_CUBIC)
                        _m2 = cv2.resize(
                            _wb, (_uw, _uh),
                            interpolation=cv2.INTER_NEAREST)
                        _r2raw = None
                        try:
                            _r2raw = lama(_o2, _m2)
                        except Exception:
                            _r2raw = None
                        if _r2raw is not None:
                            _r2b = _r2raw if isinstance(
                                _r2raw, np.ndarray) else np.array(_r2raw)
                            if _r2b.ndim == 2:
                                _r2b = cv2.cvtColor(
                                    _r2b, cv2.COLOR_GRAY2BGR)
                            else:
                                _r2b = cv2.cvtColor(
                                    _r2b, cv2.COLOR_RGB2BGR)
                            if _r2b.shape[:2] == (_uh, _uw):
                                _r2 = cv2.resize(
                                    _r2b, (out.shape[1], out.shape[0]),
                                    interpolation=cv2.INTER_AREA)
                                g7 = cv2.cvtColor(
                                    _r2, cv2.COLOR_BGR2GRAY)
                                ok_b7, ok_s7, _im7b = _quality(
                                    g7, "LaMa×2-برش")
                                if ok_s7:
                                    _blend(_r2)
                                    return
                                if ok_b7 and fallback is None:
                                    fallback = (_r2, "LaMa×2-برش")
                except Exception:
                    pass

# ۸ — — فالبکِ نهاییِ «پرِ ردیفی» (فقط اندروید —
# MANGA_VERIFY_ROWFILL): وقتی هیچ پلی جواب نداد و جوهرِ
# جامانده «واقعی» است (bad_ink با ink≥0.22 — لاگِ گوشیِ
# 700×11362: crop@(420,3261) ink=0.66 = متنِ شبحِ LaMaِ
# چندخطی که ×17/×33/×2 هر سه نگرفتند و «خروجیِ فعلی ماند»)
# برایِ هر ردیفِ ماسک، رنگِ میانهٔ پیکسلهایِ بیرونِ ماسکِ
# همان ردیف (شکافِ بینِ خطها/حاشیهٔ بلوک) جایگزینِ ماسک
# میشود — گرادیانِ عمودیِ زمینه حفظ میشود و متنِ شبح حذف
# ردیفِ کاملاً ماسک از نزدیکترینِ ردیفهایِ زمینهدار
# درون‌یابی میشود. گاردِ ضدِ هنر: زمینهٔ رنگیِ قوی (نوتار
# >۴۰ — بوته/سایه مثلِ ARTSKIP) هرگز پر نمیشود. گیتِ
# قبولیِ آسانتر (جوهرِ پر ≈۰ و فاصله از میانهٔ حلقه ≤۳۵)
# چون حلقهٔ بلوکِ چندخطی خودش آلوده به خطهایِ دیگر است و
# گیتِ معمولی معیارِ غلط میگیرد.
# PC بایت‌به‌بیت دست‌نخورده.
            def _row_fill_res():
                mo = (m > 0)
                if not mo.any():
                    return None
                hgt, wid = mo.shape
                mfill = m_eval > 0
# نمونهگیری با دیلِ ۱۵ (نه بیشتر): درِ بلوکِ متراکمِ
# چندخطی حاشیهٔ بلوک + شکافِ بینِ خطها تنها نمونهٔ
# زمینهایِ هر ردیفاند (میانه در برابرِ گلیفِ جامانده
# مقاوم است)؛ دیلِ بزرگتر همهٔ ردیف را میبلعد
                msamp = cv2.dilate(
                    m, cv2.getStructuringElement(
                        cv2.MORPH_ELLIPSE, (15, 15))) > 0
                xs_idx = np.nonzero(mo.any(axis=0))[0]
                if xs_idx.size < 20:
                    return None
                x0b, x1b = int(xs_idx[0]), int(xs_idx[-1]) + 1
                rows = np.nonzero(mfill.any(axis=1))[0]
                if rows.size < 4:
                    return None
                rowcol = {}
                hrows = []
# نمونه از «همهٔ» ردیفهایِ برش (حاشیهٔ بالا/پایینِ بلوک
# هم لنگرِ گرادیاناند — نه فقط ردیفهایِ ماسک)
                for yy in range(hgt):
                    free = ~msamp[yy, x0b:x1b]
                    if int(free.sum()) >= max(
                            10, int(0.05 * (x1b - x0b))):
                        rowcol[yy] = np.median(
                            out[yy, x0b:x1b][free].astype(np.float32),
                            axis=0)
                        hrows.append(yy)
                if not hrows:
                    return None
                hidx = np.asarray(hrows, dtype=np.int64)
                bg = np.zeros((hgt, 3), np.float32)
                _j = 0
                for yy in range(hgt):
                    if yy in rowcol:
                        bg[yy] = rowcol[yy]
                        continue
                    j = int(np.searchsorted(hidx, yy))
                    if j == 0:
                        bg[yy] = rowcol[int(hidx[0])]      # گیرِ لبهٔ بالا
                    elif j >= hidx.size:
                        bg[yy] = rowcol[int(hidx[-1])]     # گیرِ لبهٔ پایین
                    else:
                        ya = int(hidx[j - 1])
                        yb = int(hidx[j])
                        t = float(yy - ya) / float(yb - ya)
                        bg[yy] = rowcol[ya] * (1.0 - t) + \
                            rowcol[yb] * t
                fill = np.repeat(bg[:, None, :], wid, axis=1)
                fill = cv2.blur(fill, (1, 9))
                res = out.copy()
                res[mfill] = np.clip(
                    fill, 0, 255).astype(np.uint8)[mfill]
                return res

# دامنهٔ پرِ ردیفی جوهرِ ضعیفِ تأییدشده را هم
# میگیرد: لاگِ گوشیِ — crop@(573,3189) با
# ink=0.16/حلقه=0.03/neutr=31 توسطِ خودِ وارسی «جوهر» پرچم
# شد (دود=1.00) ولی گیتِ قدیمیِ ink≥0.22 فالبکِ نهایی را
# قفل کرد → «ترمیمِ کامل نشد — خروجیِ فعلی ماند» = تکهٔ
# حرف رویِ تصویر. شرطِ تازه: جوهرِ ≥۰٫۱۰ وقتی حلقه پاک
# است (ink_r≤0.10) و حلقه گسترهٔ صدکیِ معقول دارد (rs≤30
# ضدِ زمینهٔ بافت‌مند/هنری). PC بیت‌به‌بیت.
            if _android_gate("MANGA_VERIFY_ROWFILL") and bad_ink and \
                    neutr <= 40.0 and \
                    (ink_m >= 0.22 or (ink_m >= 0.10 and
                                       ink_r <= 0.10 and rs <= 30.0)):
                try:
                    _rf = _row_fill_res()
                    if _rf is not None:
                        g8 = cv2.cvtColor(_rf, cv2.COLOR_BGR2GRAY)
                        _im8, _ir8 = _ink(g8, m_eval, ring)
                        _med_r = float(np.median(g[ring])) \
                            if int(ring.sum()) else 200.0
                        _gm8 = float(np.median(g8[m_eval > 0]))
                        _ok8 = (bool(_im8 <= 0.10) and
                                abs(_gm8 - _med_r) <= 35.0)
                        if self.debug:
                            try:
                                print(f"    [🔍ترمیم] پرِ ردیفی: "
                                      f"ink={_im8:.2f}/حلقه={_ir8:.2f} "
                                      f"lum={_gm8:.0f} (حلقه={_med_r:.0f}) "
                                      f"→ {'OK' if _ok8 else 'رد'}",
                                      flush=True)
                            except Exception:
                                pass
                        if _ok8:
                            _blend(_rf)
                            return
                except Exception:
                    pass
# هیچ مرحله‌ای بارِ سفیدِ سخت را پاس نکرد — اگر دست‌کم یک
# نتیجهٔ «بد-نیست» داشتیم، همان را blend می‌کنیم (به‌مراتب
# بهتر از خروجیِ کثیفِ اولیهٔ EP)
            if fallback is not None:
                _fr, _fw = fallback
                if self.debug:
                    try:
                        print(f"  [*]ترمیمِ crop@({cx0},{cy0}) با «{_fw}» "
                              f"blend شد (بارِ نابِ سفید برآورده نشد)",
                              flush=True)
                    except Exception:
                        pass
                _blend(_fr)
                return
            if self.debug:
                try:
                    print(f"  [!]ترمیمِ پلکانیِ crop@({cx0},{cy0}) "
                          f"کامل نشد → فالبکِ نهاییِ پرِ ردیفی/تخت",
                          flush=True)
                except Exception:
                    pass
# پایانِ «بازگردانیِ اورجینال» —
# برگرداندنِ پیکسلِ اورجینال در ناحیهٔ «متن» یعنی خودِ
# متنِ انگلیسیِ خام برمیگشت (لاگِ واقعیِ گوشیِ :
# crop@(1673,0) — LaMa×2-برش «هنوز بد» → [↺] → متنِ
# اورجینال سرِ جایش ماند). قاعدهٔ تازه: هیچ مسیری حقِ
# برگرداندنِ اورجینالِ «متن» را ندارد؛ آخرین فالبک = «پرِ
# ردیفیِ بی‌گیت» (رنگِ میانهٔ زمینهٔ همان ردیف — گرادیانِ
# عمودی حفظ، جوهر به سازهٔ پیکسلیِ ردیف جایگزین میشود =
# از ساخت، بدونِ متن) و اگر نشد «پرِ تختِ حلقه». بدترین
# حالتِ تازه = یک لکهٔ همرنگِ زمینه — هرگز متنِ جامانده.
# گاردِ هنر (همارزِ ARTSKIPِ اندروید، حالا رویِ PC هم):
# جوهرِ ضعیف + حلقهٔ بافت‌مند + زمینهٔ رنگی = سایه/بوتهٔ
# هنر — نه متن؛ در آن حالت «خروجیِ فعلی» میماند (هرگز
# اورجینالِ متن برنمیگردد، هیچ پُری هم رویِ هنر نمیرود).
            _art_like = bool(
                rs > 22.0 and ink_m < 0.30 and neutr >= 40.0)
            if _art_like:
                if self.debug:
                    try:
                        print(f"  [🔍هنر] جوهرِ ضعیف + زمینهٔ هنریِ "
                              f"crop@({cx0},{cy0}) → خروجیِ فعلی ماند "
                              f"(بدونِ پر و بدونِ بازگردانی)", flush=True)
                    except Exception:
                        pass
            else:
                try:
                    _rf2 = _row_fill_res()
                    if _rf2 is not None:
                        _blend(_rf2)
                        if self.debug:
                            try:
                                print(f"  [✓پرِردیفی] پرِ ردیفیِ نهاییِ "
                                      f"crop@({cx0},{cy0}) — بدونِ "
                                      f"بازگردانیِ اورجینال", flush=True)
                            except Exception:
                                pass
                    else:
                        _col = np.median(
                            out[ring].astype(np.float32),
                            axis=0).astype(np.float32) \
                            if int(ring.sum()) else np.array(
                                [252.0, 252.0, 252.0], np.float32)
                        _flat = np.repeat(
                            _col[None, None, :], out.shape[0],
                            axis=0).repeat(out.shape[1], axis=1)
                        _blend(_flat.astype(np.uint8))
                        if self.debug:
                            try:
                                print(f"  [✓پرتخت] پرِ تختِ نهاییِ "
                                      f"crop@({cx0},{cy0}) — بدونِ "
                                      f"بازگردانیِ اورجینال", flush=True)
                            except Exception:
                                pass
                except Exception:
# حتی در خطا هم «خروجیِ فعلی» میماند — دیگر هرگز
# اورجینال برنمیگردد.
                    pass
        except Exception:
            return

    def _scrub_dark_residuals(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        if mask is None or not np.any(mask):
            return image
        m0 = (mask > 0).astype(np.uint8)
        if int(m0.sum()) < 15:
            return image

        out = image.copy()
        gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
        local_med = cv2.medianBlur(gray, 15)
        dark = ((gray.astype(np.int16) < local_med.astype(np.int16) - 35) & (m0 > 0)).astype(np.uint8) * 255
        dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        if np.count_nonzero(dark) > 12:
            dark = cv2.dilate(dark, np.ones((3, 3), np.uint8), iterations=1)
            dark[m0 == 0] = 0
            out = cv2.inpaint(out, dark, inpaintRadius=4, flags=cv2.INPAINT_TELEA)
        return out

    def _scrub_bright_residuals(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:

        if mask is None or not np.any(mask):
            return image
        m0 = (mask > 0).astype(np.uint8)
        if int(m0.sum()) < 20:
            return image

        out = image.copy()

        n, lab, st, _ = cv2.connectedComponentsWithStats(m0, connectivity=8)
        for i in range(1, n):
            area = int(st[i, cv2.CC_STAT_AREA])
            if area < 25:
                continue
            bx = int(st[i, cv2.CC_STAT_LEFT])
            by = int(st[i, cv2.CC_STAT_TOP])
            bw = int(st[i, cv2.CC_STAT_WIDTH])
            bh = int(st[i, cv2.CC_STAT_HEIGHT])

            pad = 14
            x0 = max(0, bx - pad)
            y0 = max(0, by - pad)
            x1 = min(out.shape[1], bx + bw + pad)
            y1 = min(out.shape[0], by + bh + pad)
            crop = out[y0:y1, x0:x1]
            clab = lab[y0:y1, x0:x1]
            cm = (clab == i)
            if not cm.any():
                continue

            ring = cv2.dilate(cm.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
            ring &= ~cm

            border = 2
            ring[:border, :] = False
            ring[-border:, :] = False
            ring[:, :border] = False
            ring[:, -border:] = False
            if int(ring.sum()) < 40:
                continue

            ring_px = crop[ring].astype(np.float32)

            if float(ring_px.std(axis=0).mean()) > 22.0:
                local_m = (cm.astype(np.uint8) * 255)
                fixed = cv2.inpaint(crop, local_m, inpaintRadius=4, flags=cv2.INPAINT_TELEA)
                out[y0:y1, x0:x1] = fixed
                continue

            bg = np.median(ring_px, axis=0)

            inside = crop[cm].astype(np.float32)

            bg_lum = 0.114 * bg[0] + 0.587 * bg[1] + 0.299 * bg[2]
            in_lum = 0.114 * inside[:, 0] + 0.587 * inside[:, 1] + 0.299 * inside[:, 2]

            bright = in_lum > bg_lum + 18

            dark = in_lum < bg_lum - 28
            bad = bright | dark
            if not np.any(bad):
                continue

            ys, xs = np.where(cm)
            bad_full = np.zeros(cm.shape, dtype=bool)
            bad_full[ys[bad], xs[bad]] = True
            if int(bad_full.sum()) < 8:
                continue

            inv = (~cm).astype(np.float32)
            k = 21
            filled = crop.astype(np.float32).copy()
            for c in range(3):
                num = cv2.blur(filled[:, :, c] * inv, (k, k))
                den = cv2.blur(inv, (k, k))
                est = np.full_like(num, bg[c])
                np.divide(num, den, out=est, where=den > 1e-4)
                filled[:, :, c][bad_full] = est[bad_full]
            filled = np.clip(filled, 0, 255).astype(np.uint8)

            bm = bad_full.astype(np.uint8) * 255
            bm = cv2.dilate(bm, np.ones((3, 3), np.uint8), iterations=1)
            bm[~cm] = 0
            filled = cv2.inpaint(filled, bm, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
            out[y0:y1, x0:x1] = filled

        return out

    @staticmethod
    def _is_daily_quota_error(err: Exception) -> bool:

        msg = str(err)
        low = msg.lower()

        daily_markers = (
            "PerDay", "RequestsPerDay", "GenerateRequestsPerDay",
            "per day", "daily quota", "quota per day",
        )
        if any(m in msg or m.lower() in low for m in daily_markers):
            return True

        if any(x in msg for x in ("PerMinute", "PerModel", "PerHour", "rateLimit", "RateLimit")):
            return False
        if any(x in low for x in ("per minute", "per model", "rate limit", "too many requests")):
            return False
        return False
