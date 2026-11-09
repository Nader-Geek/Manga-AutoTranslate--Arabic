# BUILD-STRIP-START
# ─────────────────────────────────────────────────────────────
# ⚠️ MangaTranslator (۲ از ۱۳) — ماسکِ متن: _classify_text، ماسکهای جوهر/حباب، نوارها و compose
# این فایل «قطعهای از بدنهٔ کلاس MangaTranslator» است و بهتنهایی
# اجرا نمیشود — scripts/build_manga.py این محتوا را بههمان ترتیبِ
# شمارهٔ فایل، داخلِ کلاس در manga.py میچسباند. کلاسِ پوششیِ زیر فقط
# برای معتبر بودنِ سینتکسِ این فایلِ تکی است و موقعِ بیلد حذف میشود.
class _MangaTranslatorBody_110:
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

        # v1.14.202 — واترمارکِ رویِ حباب: اگرِ بعدِ برداشتنِ دامنهها،
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
        # v1.14.159 — نامِ پلتفرم/واترمارک در متنِ کوتاه = کاندیدِ تبلیغ؛
        # وگرنه شاخهٔ «شبیهِ جمله → دیالوگ» قبل از چکِ واترمارک برمی‌گشت
        # و بنرهایِ «READ ON WEBTOON» / «NAVER WEBTOON» دیالوگ حساب میشدند.
        if not _looks_promo and len(stripped) <= 40:
            _low_probe = stripped.lower()
            for _w in WATERMARK_PATTERNS:
                if _w and _w in _low_probe:
                    _looks_promo = True
                    break
        # v1.14.202 — واترمارکِ رویِ حباب: OCR واترمارک/دامنهٔ سایت را «داخلِ»
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


        # v1.14.245 — «عدد در کنارِ حروفِ واقعی = دیالوگ است، نه آشغال»
        # (دستورِ سازنده: «19 hi باید هردوشو بخونه حذف شه»): قوانینِ
        # عددیِ junk فقط وقتی صدا میزنند که متن «هیچ حرفِ واقعی» نداشته
        # باشد (source_has_letters) — آن‌وقت سیاست در سطحِ ناحیه
        # (no_touch230) دست میگیرد و ناحیه دست‌نخورده میماند. «1233»
        # همچنان junk میماند (بدونِ حرف) ولی «19 hi» / «19th» دیالوگ.
        _has_letters245 = source_has_letters(stripped)
        if not _has_letters245:
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
        # v1.14.159 — پسوند/پیشوندِ سایتِ «الزامی» شد؛ قبلاً هر متنی که
        # فقط «manga» داشت (تا ۲۴ کاراکتر) promo میشد.
        if re.search(r"(?i)((like|ike|vortex|kayn|asura|reaper)manga|manga[.\s]?(ink|unk|com|org))", stripped) and len(stripped) <= 24:
            return "promo"
        # v1.14.159 — نشانهٔ دامنه لازم شد؛ قبلاً دیالوگِ کوتاهِ «DRUNK»/
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
        """v1.14.90 — ستون‌بندیِ خط‌هایِ OCRِ یک ناحیه.

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
                    # v1.14.72 — سقفِ ۱۸۰ برای زمینهٔ روشنِ رنگی (زرد با
                    # مدین ~۲۰۰) کلِ زمینه را هم «متنِ روشن» می‌خواند؛
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

        # v1.14.72 — متنِ روشن روی زمینهٔ رنگی (حبابِ زرد با متنِ سفید):
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
        """v1.14.53 — حفره‌هایِ یک ماسکِ بولی را پر می‌کند (خروجی: بولی).
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
        """v1.14.53 — اینتریورِ «ضدِ نشت».
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
        # v1.14.53: مهرِ شکاف‌هایِ دیوار — جایگزینِ CLOSE/erodeِ قدیمی
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
        """v1.14.73c — آمارِ «خوشهٔ رنگِ غالبِ» داخلِ باکس (بر مبنای
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
        """v1.14.73b — آیا «زمینهٔ داخلِ جعبه/حباب» بافت‌مند است؟
        (پرده/بوکه = LaMa بهتر؛ سیاهِ خالص/گرادیانِ صاف = پرِ فوریِ
        گرادیانیِ خودش تمیزتر است — نمونهٔ کارتِ Crimson Dragon).
        v1.14.73c — با خوشهٔ غالبِ سه‌کاناله (باکسِ بیضی گوشه‌هایش
        زمینهٔ پنل است)."""
        st = MangaTranslator._box_bg_stats(image, bx0, by0, bx1, by1)
        if st is None:
            return True
        frac, cstd, hf, _fillc = st
        # v1.14.73c — گرادیانِ صاف (کارتِ Crimson Dragon) cstd بالا ولی
        # hf پایین دارد → «بافت‌مند» نیست؛ پرِ فوریِ گرادیانیِ خودش بهتر است.
        # فقط بافتِ فرکانس‌بالا (پرده/بوکه/سکرین‌تون) LaMa می‌خواهد.
        return hf >= 0.05

    def _uncovered_ink_bands(self, image: np.ndarray, box,
                             known_mask: np.ndarray) -> Optional[np.ndarray]:
        """v1.14.73d — «نجاتِ جوهرِ پوشش‌داده‌نشده»: OCR گاهی خطی را در
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
            # v1.14.165 — اضلاعِ جعبه که به لبهٔ تصویر می‌خورند: تکه‌متنِ
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
                # v1.14.73d — فقط «قلمِ نازکِ متن» (ضخامت ≤۶px): خطِ
                # دست‌کشیدهٔ ضخیمِ حبابِ کیمتسو/ژاپنی جوهر نیست — دیوار است
                try:
                    _cmc = (lal == ci)
                    _dtc = cv2.distanceTransform(
                        _cmc.astype(np.uint8), cv2.DIST_L2, 3)
                    if float(_dtc.max()) * 2.0 > 12.0:
                        continue
                except Exception:
                    pass
                # v1.14.240 — «قوسِ دیواره از مرزِ جعبه می‌گذرد»:
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
                # ضلعِ «لبهٔ تصویر» (وبتونِ بریده — v1.14.165) مشمولِ
                # این گارد نیست؛ فقط ضلعِ داخلیِ جعبه.
                try:
                    _cmc240 = (lal == ci)
                    _sides240 = []
                    if _cy0 <= 1:
                        _sides240.append("t")
                    if _cy0 + chg >= (by1 - by0) - 1:
                        _sides240.append("b")
                    if _cx0 <= 1:
                        _sides240.append("l")
                    if _cx0 + cwd >= (bx1 - bx0) - 1:
                        _sides240.append("r")
                    _interior240 = {"t": by0 > 0, "b": by1 < ih,
                                    "l": bx0 > 0, "r": bx1 < iw}
                    if any(_interior240[_s] for _s in _sides240):
                        _bright240 = float(bright.mean()) > float(dark.mean())
                        _cont240 = False
                        for _sd240 in _sides240:
                            if not _interior240[_sd240]:
                                continue
                            if _sd240 in ("t", "b"):
                                _tr240 = (_cmc240[:2, :] if _sd240 == "t"
                                          else _cmc240[-2:, :])
                                _cols240 = np.nonzero(
                                    _tr240.any(axis=0))[0]
                                if _cols240.size == 0:
                                    continue
                                if _sd240 == "t":
                                    _og240 = cv2.cvtColor(
                                        image[max(0, by0 - 6):by0,
                                              bx0:bx1],
                                        cv2.COLOR_BGR2GRAY)
                                    _ig240 = g[:2, :]
                                else:
                                    _og240 = cv2.cvtColor(
                                        image[by1:min(ih, by1 + 6),
                                              bx0:bx1],
                                        cv2.COLOR_BGR2GRAY)
                                    _ig240 = g[-2:, :]
                                if _og240.shape[0] == 0:
                                    continue
                                _out240 = _og240.min(axis=0)
                                _in240 = (_ig240.max(axis=0)
                                          if _bright240
                                          else _ig240.min(axis=0))
                            else:
                                _tc240 = (_cmc240[:, :2] if _sd240 == "l"
                                          else _cmc240[:, -2:])
                                _rows240 = np.nonzero(
                                    _tc240.any(axis=1))[0]
                                if _rows240.size == 0:
                                    continue
                                if _sd240 == "l":
                                    _og240 = cv2.cvtColor(
                                        image[by0:by1,
                                              max(0, bx0 - 6):bx0],
                                        cv2.COLOR_BGR2GRAY)
                                    _ig240 = g[:, :2]
                                else:
                                    _og240 = cv2.cvtColor(
                                        image[by0:by1,
                                              bx1:min(iw, bx1 + 6)],
                                        cv2.COLOR_BGR2GRAY)
                                    _ig240 = g[:, -2:]
                                if _og240.shape[1] == 0:
                                    continue
                                _out240 = _og240.min(axis=1)
                                _in240 = (_ig240.max(axis=1)
                                          if _bright240
                                          else _ig240.min(axis=1))
                            if _bright240:
                                _hit240 = (
                                    _out240[_cols240 if _sd240 in ("t", "b")
                                            else _rows240]
                                    >= np.minimum(
                                        _in240[_cols240
                                               if _sd240 in ("t", "b")
                                               else _rows240] - 35.0,
                                        105.0))
                            else:
                                _hit240 = (
                                    _out240[_cols240 if _sd240 in ("t", "b")
                                            else _rows240]
                                    <= np.maximum(
                                        _in240[_cols240
                                               if _sd240 in ("t", "b")
                                               else _rows240] + 35.0,
                                        150.0))
                            if float(_hit240.mean()) >= 0.35:
                                _cont240 = True
                                break
                        if _cont240:
                            continue
                except Exception:
                    pass
                keep |= (lal == ci)
            # v1.14.165 — پاسِ ویژهٔ لبه: نیم‌خطِ بریدهٔ وبتون (صفحه‌ای که
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
        """v1.14.74 — ماسکِ donor (عکسِ اول) = «فقط نوارهایِ متن + پدِ
        سخاوتمندانه» — نه کلِ داخلِ حباب. درخواستِ صریحِ کاربر:
        «عکسِ اول متن‌هاش کامل بپاکه — اشکال نداره حباب خراب شه یا بیشتر
        پاک شه. بعد خط به خط برش بخوره به عکسِ دوم بچسونه» +
        «چرا کل حباب انتقال میدی؟ اگ یک کلمه کل حباب حساب میشه حروف به
        حروف برش بزنه انتقال بده».

        چرا کلِ داخلِ حباب (v1.14.71/73) بد بود:
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
                # v1.14.206n — فقط «قابِ رنگیِ» 206j از donor آزاد میشود
                # (رنگِ قاب نباید واردِ پرِ متن شود — لکهٔ سبزِ up0822)؛
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
            # v1.14.74b — «اگ یک کلمه کل حباب حساب میشه حروف به حروف برش
            # بزنه»: ناحیه‌هایِ «متنِ متراکم» (≥۳۴٪ پوششِ پالی‌ها — همان
            # شرطِ _polys_denseِ سازندهٔ ماسک) در ماسکِ خام «مستطیلِ بلوک»
            # می‌شوند که تقریباً کلِ داخلِ حباب است → LaMa با سوراخِ عظیم،
            # داخلِ حبابِ زرد را خمیرِ خاکستری می‌کرد (نمونهٔ 01.jpg).
            # در donor، بلوک با «نوارِ خط‌به‌خطِ جوهر + پد» جایگزین می‌شود
            # (همان نوارهایی که کامپوز منتقل می‌کند) + جوهرِ واقعیِ اطراف
            # (تیره یا روشن) تا هیچ مرکبِ جا‌مانده‌ای زنده نماند.
            try:
                _k11 = np.ones((11, 11), np.uint8)
                for region in (regions or []):
                    try:
                        _pl74 = []
                        for _p74 in (getattr(region, "ocr_polys", None)
                                     or []):
                            try:
                                _pp74 = np.asarray(
                                    _p74, dtype=np.float32).reshape(-1, 2)
                            except Exception:
                                continue
                            if _pp74.shape[0] >= 3:
                                _pl74.append(_pp74)
                        if len(_pl74) < 2:
                            continue
                        if not MangaTranslator._polys_dense(_pl74):
                            continue
                        _res74 = self._compose_region_strips(image, region)
                        _st74 = None
                        if _res74:
                            _m74, _f74 = _res74[0], _res74[1]
                            if _m74 is None or _m74.shape != out.shape:
                                _m74 = np.zeros(out.shape, np.uint8)
                            if _f74 is None or _f74.shape != out.shape:
                                _f74 = np.zeros(out.shape, np.uint8)
                            _st74 = (_m74 > 0) | (_f74 > 0)
                        if _st74 is None or not _st74.any():
                            continue
                        _bb74 = MangaTranslator._text_block_box(
                            _pl74, region.rect, False)
                        if not _bb74:
                            continue
                        # خروجیِ _text_block_box = (x, y, w, h)
                        _zx0 = max(0, int(_bb74[0]))
                        _zy0 = max(0, int(_bb74[1]))
                        _zx1 = min(w_img, _zx0 + int(_bb74[2]))
                        _zy1 = min(h_img, _zy0 + int(_bb74[3]))
                        if _zx1 - _zx0 < 24 or _zy1 - _zy0 < 24:
                            continue
                        _keep74 = cv2.dilate(
                            _st74.astype(np.uint8), _k11) > 0
                        # جوهرِ واقعیِ داخلِ بلوک (تیره یا روشن) که نوارها
                        # نپوشانده‌اند — نوارِ نجاتِ مکمل؛ دیوار (protect)
                        # هرگز واردِ donor نمی‌شود.
                        #
                        # v1.14.95 — گاردِ «ساختار»: معیارِ «هرچه از میانه
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
                            _oc74 = image[_zy0:_zy1, _zx0:_zx1]
                            _g74 = cv2.cvtColor(_oc74, cv2.COLOR_BGR2GRAY)
                            _med74 = float(np.median(_g74))
                            # v1.14.95b — فقط «بقایایِ پرکنتراست»: بازماندهٔ
                            # واقعیِ جوهر (آپاستروف/خطِ جاافتاده) در برابر
                            # زمینهٔ بلوک خیلی دور است (≥۹۰). بافتِ پشتِ
                            # شیشه/گرادیانِ پلاک در همین بازه نیست → دیگر
                            # واردِ ماسکِ LaMa نمی‌شود و لکهٔ سایه نمی‌سازد.
                            _ink74 = ((_g74 < _med74 - 90.0)
                                      | (_g74 > _med74 + 90.0))
                            _ink_u8 = _ink74.astype(np.uint8)
                            _nz74 = int(_ink_u8.sum())
                            _blk_area = max(1, (_zx1 - _zx0) * (_zy1 - _zy0))
                            _wall_ok74 = True
                            if _nz74 >= max(400, int(0.45 * _blk_area)):
                                # بافت/گرادیان — نه جوهر؛ کلِ نجات رد.
                                _wall_ok74 = False
                            else:
                                try:
                                    _n74, _lb74, _stt74, _ = \
                                        cv2.connectedComponentsWithStats(
                                            _ink_u8, 8)
                                    _okc74 = np.zeros_like(_ink_u8)
                                    for _i74 in range(1, _n74):
                                        _cw74 = int(_stt74[_i74,
                                                          cv2.CC_STAT_WIDTH])
                                        _ch74 = int(_stt74[_i74,
                                                          cv2.CC_STAT_HEIGHT])
                                        _mx74 = max(_cw74, _ch74)
                                        _mn74 = max(1, min(_cw74, _ch74))
                                        # خطِ بلندِ نازک = دیوار/قاب، نه حرف
                                        if _mx74 >= 64 and _mn74 <= max(
                                                12, int(0.09 * _mx74)):
                                            continue
                                        # حلقه/قاب: کادرِ بزرگ با پرشدگیِ کم
                                        _fa74 = _cw74 * _ch74
                                        _px74 = int(_stt74[_i74,
                                                          cv2.CC_STAT_AREA])
                                        if _mx74 >= 96 and _fa74 > 0 and \
                                                _px74 / _fa74 < 0.38:
                                            continue
                                        _okc74[_lb74 == _i74] = 1
                                    _ink_u8 = _okc74
                                except Exception:
                                    pass
                            if _wall_ok74:
                                _ink74 = cv2.dilate(
                                    _ink_u8,
                                    np.ones((5, 5), np.uint8)) > 0
                                if _protect is not None \
                                        and _protect.shape == out.shape:
                                    _ink74 &= (_protect[_zy0:_zy1,
                                                        _zx0:_zx1] == 0)
                                _keep74[_zy0:_zy1, _zx0:_zx1] |= _ink74
                        except Exception:
                            pass
                        # جایگزینی: داخلِ بلوک فقط نوارها + جوهر می‌ماند
                        out[_zy0:_zy1, _zx0:_zx1] = np.where(
                            _keep74[_zy0:_zy1, _zx0:_zx1], 255, 0
                        ).astype(out.dtype)
                    except Exception:
                        continue
            except Exception:
                pass
            # v1.14.212 — روکشِ حاشیه‌نویسیِ ورودی (قابِ سبز + شستشویِ
            # نیمه‌شفافِ up0822) هم در donor پاک میشود — بعد از جایگزینیِ
            # بلوکهایِ متراکم میآید تا با np.where پاک نشود؛ دیوارها
            # (protect) از قبل در نقشهٔ روکش حذف شدهاند.
            try:
                _anD212 = getattr(self, "_page_annotation_overlay", None)
                if _anD212 is not None and _anD212.shape == out.shape:
                    _addD212 = (_anD212 > 0) & (out == 0)
                    if bool(_addD212.any()):
                        out[_addD212] = 255
                        _added += int(np.count_nonzero(_addD212))
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
                    # v1.14.165 — وبتون‌هایی که صفحه‌شان از وسطِ حباب شروع
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
        """v1.14.47 — بازنویسیِ کامل — درخواستِ کاربر: «حباب متن نباید بپاکه
        و لگه نباید بزاره، متن نباید بمونه».
        قانونِ طلایی: این تابع فقط «کوچک» می‌کند، هرگز بزرگ نمی‌کند.
        ۱) اگر حبابِ واقعی (جزیرهٔ بسته با دیوارِ تیره) دورِ متن پیدا شود →
           ماسک به داخلِ حباب گیرده می‌شود (کلیپ)؛ دیوارِ حباب و بیرونِ آن
           هرگز پاک نمی‌شود و متنِ نزدیکِ دیوار هم داخلِ ماسک می‌ماند.
        ۲) اگر ماسک از قبل کاملاً داخلِ حباب است → دست نمی‌خورد.
        ۳) اگر حباب معتبر نبود → ماسک با پالی‌های تنگِ OCR «تقاطع» می‌شود —
           بلوکِ مستطیلی جمع می‌شود ولی هیچ پیکسلی بیرونِ ماسکِ قبلی اضافه
           نمی‌شود (نسخهٔ ۱.۱۴.۴۶ این‌جا ماسک را با پالی‌های 1.18x «جایگزین»
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
                    # v1.14.47: اعتبارسنجیِ «دیوار» — حلقهٔ دورِ اینتریور باید
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
                            # v1.14.47d: دیوار باید واقعاً تیره باشد (خطِ
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
                        # v1.14.47d: 0.75 — کلیپ فقط برای «سرریزِ کم»؛ اگر
                        # بیش از ~۲۵٪ ماسک بیرونِ «حباب» است، این یک جزیرهٔ
                        # کاذب روی هنر است (متنِ روشن روی زمینهٔ تیره) و
                        # کلیپ، متنِ واقعی را قربانی می‌کند
                        if _n_clip >= max(150, 0.75 * n_orig) and _n_clip < n_orig:
                            rm[y0:y1, x0:x1] = clipped
                            return rm
            # ---- v1.14.47c: مسیرِ «جایگزینی با پالی‌هایِ تنگ» حذف شد ----
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
        """v1.14.171 — دیلیشنِ ماسک + گیردهِ دوباره به داخلِ حباب (فقطِ
        اندروید — دستورِ سازنده: «حبابِ متن خراب نشه … خوده مرجع ببین چکار
        کرده»). دیکدِ مرجع: اپِ مرجع هیچ مدلِ inpaintی ندارد و فقط پالیِ تنگِ
        خطهایِ OCR را با رنگِ زمینه پر میکند — دیوارِ حباب هرگز لمس
        نمیشود. نزدیکترین معادلِ امنِ همین‌جا: پدِ ماسکِ اندروید (۸px —
        درسِ 1.14.133 برایِ دورخطِ ضخیمِ حبابهایِ زرد) بعد از گیردهِ حباب
        اعمال میشود و میتواند ۸ پیکسل از دیوار را ببلعد؛ پس بعدِ دیلیشن
        دوباره به داخلِ حباب گیرده میکنیم. _limit_mask_to_bubble فقط
        کوچک میکند و فقط با «حبابِ واقعیِ تاییدشده» (دیوارِ تیرهٔ +۴۰
        گری + گیتِ سرریزِ ۰.۷۵) کلیپ میکند → متنِ آزادِ بیرونِ حباب
        دستنخورده میماند و درسِ 1.14.133 (پوششِ دورخطِ داخلِ حباب) هم
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
        """v1.14.59 — قطبیتِ متن: جوهرِ گلیف‌ها به‌وضوح روشن‌تر از زمینهٔ
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
        """v1.14.96 — آمارِ «زمینهٔ بیرونِ جوهر» داخلِ مستطیلِ بلوک.

        «متنِ روشن روی محفظهٔ تیره» (v1.14.59) فقط وقتی مستطیلِ کاملِ
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
        """v1.14.48 — باگِ «حبابِ پاک‌شده» (صفحهٔ LIKE A TIME BOMB — ناحیهٔ
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
            # v1.14.59 — متنِ روشن روی محفظهٔ تیره: «کامپوننتِ تیرهٔ ساختاری»
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
            # v1.14.59 — گاردِ قطبیت (همه‌جایی): متنِ روشن روی محفظهٔ تیره
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
        """v1.14.48 — متنِ آزاد روی زمینهٔ هنری/گرادیانی (بدونِ حباب): نمونهٔ
        واقعی «SINCE WHEN WERE WE FRIENDS?» — ماسکِ مستطیلی روی گرادیانِ
        دیوار با یک رنگِ تخت پر می‌شود → لکهٔ بژِ واضح. ماسکِ جوهریِ تنگ
        (فقط گلیف‌ها) روی گرادیان تقریباً نامرئی است. شرط‌ها: حبابِ معتبر
        دورِ متن وجود ندارد + جوهر پوششِ کافی روی پالی‌ها دارد + جوهر
        به‌وضوح تیره‌ترِ زمینهٔ چسبیده است (متنِ تیره روی زمینهٔ روشن).
        v1.14.50 — گیتِ بافت: فقط روی زمینهٔ «صاف/گرادیانی» (دیوارِ رنگی،
        کاغذ) تنگ می‌کنیم. لاگِ 9.jpg کاربر: پاراگراف‌های روی «عکس» (حصار/
        درخت/چوب/صورت) با ماسکِ تنگ فقط استوکِ تیرهٔ گلیف را می‌گرفتند و
        هالهٔ خاکستریِ Anti-Alias دورِ حروف (سطح ~med−۵۵ تا med) باقی
        می‌ماند → «متنِ قبلی جا گذاشته». LaMa روی عکس با مستطیلِ کامل
        زمینه را عالی بازسازی می‌کند (خروجیِ v1.14.47 تأیید) → زمینهٔ
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
            # v1.14.50: گیتِ بافتِ زمینه — هالهٔ دورِ گلیف فقط روی زمینهٔ
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
        """v1.14.47 — تشخیصِ «متن داخلِ محفظهٔ باکنتراست» (مثلاً متنِ سفید روی
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
        """v1.14.47 — متن روی «محفظهٔ تیرهٔ یکدست» (بنرِ سیاهِ هدر، کادرِ
        تیره، حبابِ سیاه): ماسکِ جوهریِ تنگ می‌سازد. مستطیلِ بلوک در این
        حالت زمینهٔ تیرهٔ بینِ حروف را می‌بلعد و پرکننده با رنگِ صفحهٔ
        بیرون آن را روشن می‌کند (لگهٔ سفید / بنرِ разруш شده). فقط وقتی
        فعال است که زمینهٔ چسبیده به متن تیره، یکدست و باکنتراست با
        دورتر باشد — بقیهٔ حالت‌ها (حبابِ روشن) مسیرِ قبلی می‌روند.
        v1.14.47b: اگر پالی‌هایِ OCR فقط پاری از rect را پوشش می‌دهند
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
            # v1.14.47 (بازبینی): enclosure = «کامپوننتِ تیرهٔ یکدستی که متن
            # روی آن نشسته و از متن بزرگ‌تر است» (بنرِ هدر، کادرِ تیره،
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
                # v1.14.47c: محفظهٔ واقعی (بنر/کادر/حبابِ سیاه) «توپُر» است؛
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
            # v1.14.59 — کلِ محفظهٔ تیره با «پر شدنِ حفره‌ها» (حروفِ روشن داخلِ
            # comp سوراخ‌اند!) تا ماسکِ حالتِ LaMaِ کیفیت توپر باشد — نه پنیرِ
            # سوری که حروفِ قدیمی را بیرون بگذارد (کارتِ عنوانِ Crimson Dragon)
            _crop_c = comp.astype(np.uint8) * 255
            # v1.14.80 — stroke/glow رنگی دورِ حروف (RED MOON: حروفِ سفید
            # با stroke قرمز روی texture آبی): enclosure فقط کامپوننتِ
            # «تیره» را می‌گیرد و strokeِ رنگیِ وسطِ روشن جا می‌ماند →
            # بقایای قرمز در خروجی. پیکسل‌هایِ رنگیِ «غیرِ پس‌زمینه»
            # (فاصلهٔ hue از رنگِ اطرافِ متن) به محفظه اضافه می‌شوند.
            try:
                _hsv = cv2.cvtColor(image[wy0:wy1, wx0:wx1], cv2.COLOR_BGR2HSV)
                _hue = _hsv[:, :, 0].astype(np.float32)
                _sat = _hsv[:, :, 1]
                _near13 = cv2.dilate(polyf, np.ones((13, 13), np.uint8))
                _bg_m = ((_near13 > 0) & (polyf == 0) & (_sat > 60))
                if np.count_nonzero(_bg_m) >= 50:
                    _hue_bg = float(np.median(_hue[_bg_m]))
                    _dh = np.abs(_hue - _hue_bg)
                    _dh = np.minimum(_dh, 180.0 - _dh)
                    _colorful = (((_sat > 80) & (_dh > 40.0)
                                  & (_near13 > 0)).astype(np.uint8) * 255)
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
        """v1.14.49 — باگِ «حبابِ کلاً عوض شده / سیاه شده» (لاگِ گوشیِ کاربر:
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
            # v1.14.50 — فقط «حبابِ واقعی». لاگِ 9.jpg: پاراگرافِ روی عکسِ
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
                # v1.14.53: countNonZero روی bool exception می‌داد → tighten
                # از v1.14.50 همیشه بی‌صدا در همین گیت شکست می‌خورد!
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
            # v1.14.53: اگر tightِ جوهرِ جذب‌شده عملاً هم‌اندازهٔ خودِ ماسک شد
            # (پالی‌هایِ گشادِ OCR + جذبِ جوهر = تقریباً کلِ اینتریور)،
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
            # v1.14.50: نوارِ هاله — ماسکِ تنگ فقط استوکِ تیره را می‌گرفت و
            # Anti-Aliasِ خاکستریِ دورِ حروف (روی کاغذِ سفید ~سطح med−۲۵..۶۰)
            # باقی می‌ماند → شبحِ متن. پیکسل‌هایِ «کم‌تر از med−۲۵» در
            # همسایگیِ ~۵px جوهر را هم بگیر (فقط داخلِ اینتریور) و CLOSE کن؛
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
        """v1.14.53 — پالی‌های OCR را «خط به خط» گروه می‌کند (ایدهٔ کاربر:
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
        """v1.14.53 — ماسکِ «خط‌به‌خط» — پیاده‌سازیِ ایدهٔ دو-عکسیِ کاربر:
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
        # v1.14.238 — نواحیِ چرخیده (|angle| ≥ ۳°): نوارها در فضای
        # همسطح‌شده (مسیرِ مشترکِ کامپوز). MANGA_ROT_STRIPS=0 = خاموش.
        try:
            _ang238 = float(getattr(region, "angle", 0.0) or 0.0)
        except Exception:
            _ang238 = 0.0
        if 3.0 <= abs(_ang238) <= 45.0 \
                and os.environ.get("MANGA_ROT_STRIPS", "1") != "0":
            try:
                _rot238 = self._rotated_region_strips(
                    image, polys_raw, _ang238)
            except Exception:
                _rot238 = None
            if _rot238 is not None:
                _m238 = _rot238[0]
                _a238 = int(cv2.countNonZero(_m238))
                try:
                    _rw238 = float(region.rect[2])
                    _rh238 = float(region.rect[3])
                except Exception:
                    _rw238 = float(w)
                    _rh238 = float(h)
                if 150 <= _a238 <= 0.95 * max(1.0, _rw238 * _rh238):
                    return _m238
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
        # (v1.14.207: کفِ ۸px موقتاً ۵ شد ولی رویِ متنِ ریزِ ۷pxِ رویِ هنرِ
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
        # v1.14.133 — اندروید: برایِ متنِ ضخیمِ دورخط‌دار (You're… در
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
        """v1.14.70 — جوهرِ یک خطِ متن (نوارِ خط‌به‌خط) — «اندازهٔ دقیقِ
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
            # v1.14.57: قطبِ جوهر با «جرم» انتخاب می‌شود نه با روشنیِ زمینه —
            # متنِ سفید روی باکسِ آبیِ میانه (پنجرهٔ سیستمِ asura) قبلاً فقط
            # دورخطِ تیره را ماسک می‌کرد و بدنهٔ سفیدِ حروف می‌ماند.
            _dark = (g < med - 30.0)
            _bright = (g > med + 30.0)
            _fd = float(_dark.mean())
            _fb = float(_bright.mean())
            # v1.14.206c — پنلِ نیمهشفافِ روشنِ پشتِ متن (سبکِ webtoon —
            # PARAGRAPHهایِ img4 رویِ حصار): پنجرهٔ نوار هم پنل دارد هم
            # هنرِ اطراف → اکثریتِ روشن «خودِ پنل» است نه متن؛ متنِ واقعی
            # اقلیتِ تیره است. جوهرِ متن همیشه تراکمِ کم دارد (≤~۵۰٪
            # نوار) → اگر قطبِ انتخابیِ اکثریت از ۰٫۵۵ بیشتر شد، قطبِ
            # اقلیت جوهرِ واقعی است (تا نوارِ سالمِ متن رد نشود و به
            # failedِ چاق نیفتد).
            _sw204 = False
            if _fb > _fd:
                core = _bright
                if _fb > 0.55 and 0.015 <= _fd <= 0.45:
                    # v1.14.207g — سوئیچِ 206c فقط وقتی معتبر است که قطبِ
                    # اقلیت «متن» باشد. متنِ سفید رویِ بنرِ سیاه (CHAPTER
                    # PAGE — img1018): اکثریتِ روشن = حروفِ سفید + حاشیهٔ
                    # سفیدِ صفحه در پدِ نوار؛ اقلیتِ تیره = خودِ بنر (یک
                    # تودهٔ عظیمِ پیوسته = زمینه) → سوئیچ، «زمینه» را
                    # جوهر میگرفت و حروفِ سفید هرگز ماسک نمیشدند. پس اگر
                    # قطبِ اقلیت یک تودهٔ عظیمِ سراسریِ پهنایِ نوار است،
                    # سوئیچ نکن (اقلیت = زمینه، اکثریت = جوهرِ واقعی).
                    _minc207g = _dark
                    _swg_ok = True
                    try:
                        _nsg, _lsg, _ssg, _ = cv2.connectedComponentsWithStats(
                            _minc207g.astype(np.uint8), 8)
                        for _iig in range(1, _nsg):
                            if int(_ssg[_iig, cv2.CC_STAT_WIDTH]) \
                                    >= 0.9 * (sx1 - sx0) \
                                    and int(_ssg[_iig, cv2.CC_STAT_AREA]) \
                                    >= 0.25 * float(max(1, _minc207g.sum())):
                                _swg_ok = False
                                break
                    except Exception:
                        pass
                    if _swg_ok:
                        core = _dark | (_bright
                                        & (cv2.dilate(
                                            _dark.astype(np.uint8) * 255,
                                            np.ones((5, 5), np.uint8)) > 0))
                        _sw204 = True
                if not _sw204 and _fd > 0.004:
                    # سایه/دورخطِ تیرهٔ چسبیده به حروفِ روشن هم جوهر است
                    _nc = cv2.dilate(core.astype(np.uint8) * 255,
                                     np.ones((7, 7), np.uint8)) > 0
                    core = core | (_dark & _nc)
            else:
                core = _dark
                if _fd > 0.55 and 0.015 <= _fb <= 0.45:
                    # v1.14.207g — قرینهٔ همان گیت برایِ قطبِ اقلیتِ روشن
                    _minc207g = _bright
                    _swg_ok = True
                    try:
                        _nsg, _lsg, _ssg, _ = cv2.connectedComponentsWithStats(
                            _minc207g.astype(np.uint8), 8)
                        for _iig in range(1, _nsg):
                            if int(_ssg[_iig, cv2.CC_STAT_WIDTH]) \
                                    >= 0.9 * (sx1 - sx0) \
                                    and int(_ssg[_iig, cv2.CC_STAT_AREA]) \
                                    >= 0.25 * float(max(1, _minc207g.sum())):
                                _swg_ok = False
                                break
                    except Exception:
                        pass
                    if _swg_ok:
                        core = _bright | (_dark
                                          & (cv2.dilate(
                                              _bright.astype(np.uint8) * 255,
                                              np.ones((5, 5), np.uint8)) > 0))
                        _sw204 = True
                if not _sw204:
                    # v1.14.75 — متنِ تیره با دورخطِ روشن (حروفِ قهوه‌ایِ
                    # 01.jpg با دورخطِ سفید روی حبابِ زرد): بدنهٔ روشنِ
                    # دورخطِ چسبیده به حروف هم جوهر است؛ وگرنه فقط خطِ
                    # تیره پاک می‌شود و شبحِ سفیدِ دورخطِ حروف می‌ماند
                    # (متریکِ VLM: متنِ خوانا ماند!).
                    if _fb > 0.004:
                        # v1.14.75c — دورخطِ روشنِ متنِ تیره (حبابِ سفیدِ کلاسیک
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
            # v1.14.133 — متنِ ضخیمِ دورخط‌دار (حبابِ زردِ 01.jpg): بدنهٔ
            # تیره + دورخطِ روشنِ چسبیده (v1.14.75 به core اضافه می‌شود)
            # core را تا ~0.45 می‌رساند و نوارِ سالمِ متن رد می‌شد → فال‌بکِ
            # block-rect∪ink → حفرهٔ بزرگ → پرِ تیرهٔ LaMa رویِ گوشی. روی
            # زمینهٔ روشنِ یکدست آستانه سخاوتمندانه‌تر (0.55) — بلوکِ تیره
            # (med پایین) همچنان با همان 0.42 رد می‌شود.
            # v1.14.207 — آستانهٔ سخاوتمندانهٔ زمینهٔ روشن دیگر «فقطِ اندروید»
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
            # v1.14.165 — هالهٔ 14..30 (قبلاً 18..30): لبه‌هایِ نرمِ JPEGِ
            # حروف که ۱۴-۱۷ سطح تیره‌تر از زمینه‌اند قبلاً بیرونِ ماسک
            # می‌ماندند و شبحِ خاکستریِ کم‌کنتراست جا می‌گذاشتند (حبابِ
            # «WE KNEW.» فصلِ 264). ۱۰ امتحان شد ولی کنارِ قوسِ حباب
            # پخشِ خاکستریِ LaMa را بزرگ میکرد → ۱۴ (تعادل).
            halo = (np.abs(g.astype(np.float32) - med) >= 14.0) \
                & (np.abs(g.astype(np.float32) - med) <= 30.0) & near
            lm = ((core_u > 0) | halo)
            # v1.14.64 — نقشهٔ پالی‌هایِ OCR در برشِ نوار: حروف داخلِ پالی‌ها
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
                    # v1.14.133 — نجاتِ متنِ دورخط‌دار: کامپوننتی که «هنر»
                    # خوانده میشود ولی ≥۵۵٪ پیکسلهایش داخلِ پالیهایِ OCR
                    # خودِ خط است = حروفِ ضخیمِ بههمپیوسته (THEN…/the speed
                    # در 01.jpg)، نه هنر. هنرِ واقعی (قوسِ دیوار، افکتِ صدا)
                    # بیرونِ پالیهاست و مثلِ قبل رد می‌شود.
                    if _pm_ok and _android_gate("MANGA_LSM_POLY_RESCUE"):
                        _cm133 = (lal == ci)
                        _in133 = float(np.count_nonzero(_cm133 & (_pm > 0)))
                        if _in133 >= 0.55 * float(max(1, ca)):
                            if dbg:
                                print(f"      [📐dbg] نجاتِ متنِ دورخط‌دار "
                                      f"ca={ca} {cwd}×{chg} "
                                      f"درپالی={_in133 / max(1, ca):.2f}",
                                      flush=True)
                            kept |= _cm133
                            continue
                    if dbg:
                        print(f"      [📐dbg] رد: قطعهٔ هنر ca={ca} "
                              f"{cwd}×{chg}", flush=True)
                    return None
                # v1.14.64 — باگِ «متنِ کج یا ناقص پاک میشه»: قوسِ دیوارِ
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
                            # v1.14.207 — مثلِ 206b: حروفِ چاقِ بههمپیوستهٔ
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
                # v1.14.206 — همان گاردِ v1.14.64 برایِ لبهٔ چپ/راستِ نوار:
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
                        # v1.14.206b — حروفِ چسبیده به میله/قاب (متنِ سفیدِ
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
            # v1.14.207 — مثلِ thr_core: آستانهٔ 0.80ِ زمینهٔ روشن دیگر فقطِ
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
            # v1.14.70 — متنِ سفید با دورخطِ تیره (مثلِ «WE FRIENDS?»):
            # بدنهٔ سفیدِ حرف «حفره»ٔ دورخط است → نوار فقط دورخط را
            # می‌گرفت و بدنهٔ حروف (خودِ متن!) باقی می‌ماند. پرکردنِ
            # حفره‌هایِ کوچک نوار = پوششِ کاملِ حروف. اگر پرکردن سطحِ
            # زیادی اضافه کند (ساختارِ بزرگ) → همان نوارِ قبلی می‌ماند.
            # ⚠️ kept باید بولی بماند (نحوهٔ ایندکسِ m[...][kept] ماسکِ
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
        """v1.14.135 — ماسکِ «متنِ جامانده» در بلوک (فقطِ مصرفِ اندروید).

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

        v1.14.238 — سقفهایِ اندازهٔ گلیف سازگار با ارتفاعِ خطِ همان
        ناحیه شدند (med_h): فونتِ درشتِ کمیک (img6 — بلندیِ خط ۶۹..۷۹)
        با سقفِ ثابتِ ۶۴ رد میشد و گلیفهای جامانده هیچ‌وقت نجات
        نمیافتادند. med_h=۰ = رفتارِ قبلی."""
        try:
            h, w = image.shape[:2]
            # v1.14.238 — سقفهایِ سازگار با ارتفاعِ خط
            _mh238 = float(med_h or 0.0)
            _hh_max238 = max(64.0, 1.15 * _mh238 + 4.0) if _mh238 > 0 \
                else 64.0
            _a_max238 = max(2600.0, 0.60 * _mh238 * _mh238) if _mh238 > 0 \
                else 2600.0
            _ww_max238 = max(180.0, 2.6 * _mh238) if _mh238 > 0 else 180.0
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
            # جامانده نباید std را بترکاند (v1.14.135b)
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
                if 8 <= a <= _a_max238 and 3 <= hh <= _hh_max238 \
                        and ww <= _ww_max238:
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
        """v1.14.135 — آمارِ حلقهٔ اطرافِ کلاستر (فقطِ مصرفِ اندروید).
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
        # v1.14.59 — صندوق‌هایِ «متنِ روشن روی محفظهٔ تیره» که باید اجباری
        # با LaMa و ماسکِ بلوکِ کامل پاک شوند (شبحِ متنِ قدیمی — کارتِ عنوانِ
        # Crimson Dragon). در ابتدایِ هر صفحه خالی می‌شود.
        self._lama_force_rect_boxes = []
        # v1.14.82 — باکس‌هایِ «فقط-جوهر»: فقط «روشِ» پاکسازی را LaMa
        # اجباری می‌کند؛ ماسک هرگز توپُر نمی‌شود (قانونِ دو-عکسیِ کاربر)
        self._lama_ink_boxes = []
        # v1.14.64 — بنرهایِ تبلیغاتی (واترمارکِ دامنهٔ سایت‌ها): کلِ بنر
        # توپر پاک می‌شود و در کامپوز هم کلِ بنر از عکسِ پاک‌شده می‌آید
        self._promo_rect_boxes = []
        padding = max(0, int(getattr(self, "mask_padding", 3)))
        # v1.14.133 — اندروید: متنِ ضخیمِ دورخط‌دار (حبابهایِ زردِ 01.jpg) —
        # پدِ ۳ ماسک را دقیقاً رویِ دورخطِ سفیدِ حروف میگذارد و LaMaِ گوشی
        # دورخط را داخلِ حفره «ادامه» میدهد (شبحِ سفیدِ گلیفی). پدِ ۸ لبهٔ
        # ماسک را در زمینهٔ تمیز میبرد (تستِ H: حبابِ TL تقریباً عالی شد).
        if padding < 8 and _android_gate("MANGA_LSM_POLY_RESCUE"):
            padding = 8
        # v1.14.47: دیلیشنِ padding به‌ازایِ هر ناحیه و «قبلِ» گارد/لیمیت انجام
        # می‌شود (قبلاً بعد از حلقه روی کلِ ماسک بود و بعد از کلیپِ حباب،
        # ماسک را ۳px داخلِ دیوار می‌فرستاد). حالا لیمیتِ حباب آخربُر است.
        _pad_k = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (2 * padding + 1, 2 * padding + 1)) \
            if padding > 0 else None
        n_ok = 0
        n_skip = 0
        for region in regions:
            # v1.14.64 — تبلیغ/واترمارکِ دامنه («ASURASCANS.COM مثل دیسکورد
            # و... سایت هارو کامل فیلتر تبلیغ بزن»): کلِ بنرِ تبلیغ توپر
            # ماسک می‌شود — نه نوارِ خط‌ها — تا هیچ ذره‌ای از حروفِ تبلیغ
            # در خروجی نماند. (حذفِ بیش از اندازه مجاز است.)
            # v1.14.70 — SFX هم توپر: پلیِ OCR اغلب فقط بخشی از حروفِ
            # درشت را می‌گیرد («HAA»→«10») و بقیه می‌ماند؛ rect ناحیه از
            # روی جوهر تنگ بریده شده پس توپرکردنش امن است.
            if getattr(region, "kind", "") in ("promo", "sfx"):
                try:
                    _px0, _py0, _pw, _ph = [int(v) for v in region.rect]
                    _px1, _py1 = _px0 + _pw, _py0 + _ph
                    if getattr(region, "kind", "") == "promo":
                        # v1.14.65 — بنر کامل: قابِ سفید/سایه/ماسکوت هم پوشانده
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
                # v1.14.47: متن روی محفظهٔ تیرهٔ یکدست (بنرِ سیاه و امثالش)
                # → ماسکِ جوهریِ تنگ؛ قبل از شاخه‌هایِ مستطیلی
                try:
                    _enc = self._enclosure_tight_mask(
                        image, _polys_raw,
                        rect=tuple([int(v) for v in region.rect]))
                except Exception:
                    _enc = None
                if _enc is not None and np.any(_enc):
                    # v1.14.82 — قانونِ دقیقِ دو-عکسیِ کاربر: ماسک = فقط
                    # جوهرِ متن (تنگ)، نه کلِ محفظه! قبلاً (v1.14.59) ماسک
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
                                # v1.14.48: دیوارِ حباب/کادر از ماسک جدا شود
                                try:
                                    _rm = self._carve_structural_walls(
                                        image, _rm, region, _polys_raw)
                                except Exception:
                                    pass
                                _rm = self._limit_mask_to_bubble(
                                    image, _rm, region)
                                # v1.14.49: ماسکِ تقریباً-کلِ-حبابِ-سفید →
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
                # v1.14.165 — حبابِ تکخطی (polys=1): _polys_dense به ≥۲
                # پالی نیاز دارد و حبابهایِ تکخطی («WE KNEW.») هرگز به
                # line-strips نمیرسیدند → فالبکِ fillPoly = پرکردنِ کلِ
                # داخلِ حباب با LaMa = نوار/لکهٔ خاکستریِ شبح‌مانند.
                # پالیِ واحدِ پهن (خطِ متنِ افقی) هم مجاز شد؛ شرطهایِ داخلیِ
                # _line_strips_mask (سهمِ جوهر، سازگاریِ rect) همچنان رد
                # میکنند.
                _dense165 = MangaTranslator._polys_dense(_polys_raw)
                if not _dense165:
                    try:
                        _pp165 = [np.asarray(p, dtype=np.float32).reshape(-1, 2)
                                  for p in (_polys_raw or [])
                                  if np.asarray(p).size]
                        if len(_pp165) == 1:
                            _pw165 = float(_pp165[0][:, 0].max()
                                           - _pp165[0][:, 0].min())
                            _ph165 = float(_pp165[0][:, 1].max()
                                           - _pp165[0][:, 1].min())
                            _dense165 = (_pw165 >= 1.3 * _ph165
                                         and _pw165 >= 18.0
                                         and _ph165 >= 8.0)
                    except Exception:
                        _dense165 = False
                if _dense165:
                    if self.debug:
                        try:
                            print("  [🔍] → تلاشِ line-strips")
                        except Exception:
                            pass
                    # v1.14.53 — ایدهٔ «دو عکس» کاربر: اولی = پاک‌شده که فقط
                    # «به اندازهٔ متنِ استخراج‌شده، خط به خط» برش می‌خورد؛
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
                                        # v1.14.47: در محفظهٔ باکنتراست (متنِ
                                        # روشن روی بنرِ تیره هم‌رنگِ صفحه) فقط
                                        # جوهرِ گلیف — نه مستطیلِ بلوک
                                        # v1.14.48: متنِ آزاد روی زمینهٔ گرادیانی
                                        # (بدونِ حباب) هم ماسکِ جوهریِ تنگ
                                        # می‌گیرد — مستطیل لکهٔ تخت می‌سازد
                                        if self._ink_tight_ok(
                                                image, _rm, _inkB, _polys_raw):
                                            # v1.14.59 — محفظهٔ تیره + متنِ روشن:
                                            # تنگِ جوهری فقط هستهٔ گلیف را می‌گرفت
                                            # → پرکنندهٔ رنگی روی گرادیانِ تیره شبحِ
                                            # حروف جا می‌گذاشت و در ترکیبِ دو-عکسی
                                            # هم پیکسلِ بینِ گلیف‌ها از عکسِ اصلی
                                            # می‌ماند = «متنِ قبلی سرِ جایش». طبقِ سبکِ
                                            # کاربر (عکسِ اول باید کامل پاک شود؛ حباب/
                                            # محفظه هم آسیب دید مهم نیست) در حالتِ
                                            # LaMaِ کیفیت مستطیلِ کاملِ بلوک ∪ جوهر
                                            # می‌ماند و کلاستر اجباراً به LaMa می‌رود؛
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
                                                # v1.14.62b — زمینهٔ روشن → بلوکِ
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
                                            # v1.14.59 — متنِ روشن روی محفظهٔ تیره:
                                            # ماسکِ توپر (مستطیل ∪ جوهر) قطعی است —
                                            # کارو/کلیپِ حباب/تایتِن اینجا فقط خرابکاری
                                            # می‌کنند (پنیرِ سوری = شبحِ حروف) →
                                            # مستقیم در ماسک می‌نشیند و ادامه نمی‌دهد
                                            if (getattr(self, "use_lama", False)
                                                    and self._clean_level() != "fast"
                                                    and self._ink_is_light(
                                                        image, _inkB)):
                                                # v1.14.96 — گاردِ بافتِ زمینه:
                                                # مستطیلِ کاملِ بلوک فقط برای
                                                # محفظهٔ «یکدست» (بنرِ صاف).
                                                # روی گرادیان/برف‌نوی/نقش‌ونگار
                                                # حفرهٔ بزرگِ LaMa = پرِ تختِ
                                                # بی‌بافت (412e9e: EXEC و
                                                # GREEN MOON) → ماسکِ
                                                # پالی‌به‌پالی ∪ جوهر.
                                                _bgst96 = self._block_bg_stats(
                                                    image,
                                                    tuple([int(v) for v in
                                                           region.rect]),
                                                    _inkB)
                                                if _bgst96 is not None and (
                                                        _bgst96[1] > 36.0
                                                        or _bgst96[2] > 0.12):
                                                    try:
                                                        _rm96 = np.zeros_like(m)
                                                        # v1.14.96e — پالیِ
                                                        # «خام» (نه ۱.۲×):
                                                        # گسترشِ ۱.۲× روی
                                                        # پلاک/قاب‌هایِ تزئینی
                                                        # قاب را هم ماسک
                                                        # می‌کند → رگهٔ قاب
                                                        # در مرجع‌ها (412e9e)
                                                        for _pl96 in (region.ocr_polys or []):
                                                            try:
                                                                _pq96 = np.asarray(
                                                                    _pl96,
                                                                    dtype=np.float32).reshape(
                                                                    -1, 2)
                                                            except Exception:
                                                                continue
                                                            if _pq96.shape[0] < 3:
                                                                continue
                                                            cv2.fillPoly(
                                                                _rm96,
                                                                [np.rint(
                                                                    _pq96
                                                                ).astype(np.int32)],
                                                                255)
                                                        _rm = cv2.bitwise_or(
                                                            _inkB, _rm96)
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
                                                                f"std={_bgst96[1]:.0f} "
                                                                f"bright={_bgst96[2]:.2f})"
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
                                # v1.14.48: دیوارِ حباب/کادر از ماسک جدا شود
                                try:
                                    _rm = self._carve_structural_walls(
                                        image, _rm, region, _polys_raw,
                                        ink_mask=_inkB)
                                except Exception:
                                    pass
                                _rm = self._limit_mask_to_bubble(
                                    image, _rm, region)
                                # v1.14.49: ماسکِ تقریباً-کلِ-حبابِ-سفید →
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
                    # v1.14.47: همان قانونِ محفظهٔ باکنتراست برای مسیرِ
                    # پالی‌هایِ معمولی
                    # v1.14.48: متنِ آزادِ گرادیانی هم ماسکِ تنگ
                    if self._ink_tight_ok(
                            image, _rm, _ink2, _polys_raw):
                        # v1.14.59 — همان قانونِ محفظهٔ تیره برای مسیرِ پالی‌ها
                        # v1.14.62b — force-box فقط برای زمینهٔ «تیره»؛
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
                        # v1.14.59 — متنِ روشن روی محفظهٔ تیره → اجباری LaMa
                        # v1.14.75 — «متنِ روشن» کافی نیست؛ زمینه هم باید
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
                # v1.14.48: دیوارِ حباب/کادر از ماسک جدا شود
                try:
                    _rm = self._carve_structural_walls(
                        image, _rm, region, _polys_raw, ink_mask=_ink2)
                except Exception:
                    pass
                _rm = self._limit_mask_to_bubble(
                    image, _rm, region)
                # v1.14.49: ماسکِ تقریباً-کلِ-حبابِ-سفید → جوهرِ تنگ
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
                        # v1.14.48: دیوارِ حباب/کادر از ماسک جدا شود
                        try:
                            _rm = self._carve_structural_walls(
                                image, _rm, region, [])
                        except Exception:
                            pass
                        _rm = self._limit_mask_to_bubble(
                            image, _rm, region)
                        # v1.14.49: مستطیلِ بدونِ پالی در حبابِ سفید → جوهرِ تنگ
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
        # v1.14.135 — «پنلِ متنی» با استخراجِ ناقص (فقطِ اندروید —
        # MANGA_TEXTPANEL): وقتی OCRِ گوشیِ قدیمی (ML Kitِ آن روز) خطهایِ
        # یک بلوکِ
        # متراکم را هرز/ناقص خوانده (صفحهٔ قانونیِ 700×11362)، نوارهایِ
        # خط فقط تکههایی از متن را میپوشانند و حروفِ بینِ نوارها در
        # خروجی زنده میمانند (متنِ نیمهپاک + لکه). اگر زمینهٔ بلوک
        # روشن باشد و بیرونِ پالیها دهها گلیفِ جامانده دیده شود،
        # «فقطِ همان گلیفها» (دیلِ ۴px) به ماسکِ پاکسازی اضافه
        # میشود — نه مستطیلِ توپر (LaMaِ بلوکِ کامل رویِ زمینهٔ عکسی
        # توهمِ متن/نویز میسازد — بازتولیدِ A/B). کامپوزِ همتا همان
        # گلیفها را از عکسِ پاکشده برمیگرداند. حبابِ کاملخوانده
        # (بینِ پالیهاش گلیفِ جامانده ندارد) هرگز تریگر نمیشود.
        # v1.14.238 — گیتِ پنلِ متنی پیشفرض رویِ «هر دو» پلتفرم روشن شد
        # (env=0 خاموش): باقیماندهٔ گلیف بینِ نوارها رویِ PC هم «متنِ
        # نیمه‌پاک» میسازد — همان گونه که فلسفهٔ v1.14.212 میگوید.
        # v1.14.241 — پنلِ متنی دوباره «فقطِ اندروید» (رفتارِ testm):
        # رویِ PC با OCRِ کامل، گلیفِ جاماندهای بینِ نوارها وجود ندارد و
        # آشکارسازِ گلیف، «هنرِ بینِ خطهایِ سند» (شیشه/برگ/قابِ پنجرهٔ
        # 9.jpg و img4) را گلیف میپندارد → ۳۴هزارpx هنر به ماسکِ LaMa →
        # حفرهٔ غول → پرِ مه‌آلود رویِ خودِ نوارها (شکایتِ «شبحِ خاکستری»).
        # گلیفِ جاماندهٔ واقعیِ PC حالا از مسیرِ کاملِ donor (پالیِ کاملِ
        # خطوطِ fail — v1.14.241) پاک میشود؛ img4 با گیتِ خاموش حتی
        # تمیزتر شد (تستِ مو‌به‌مو). MANGA_TEXTPANEL=1 برایِ اجبار.
        if _android_gate("MANGA_TEXTPANEL") and n_ok > 0:
            try:
                _pg135 = float(max(1, w * h))
                _n_tp = 0
                for _rg135 in regions:
                    if getattr(_rg135, "kind", "") in ("promo", "sfx"):
                        continue
                    _polys135 = getattr(_rg135, "ocr_polys", None) or []
                    if not _polys135:
                        continue
                    try:
                        _rx, _ry, _rw, _rh = [int(v) for v in _rg135.rect]
                    except Exception:
                        continue
                    if _rw < 60 or _rh < 40:
                        continue
                    if (_rw * _rh) > 0.06 * _pg135 or _rh > 0.12 * h:
                        continue
                    _pm135 = np.zeros((h, w), dtype=np.uint8)
                    for _p135 in _polys135:
                        try:
                            _pp135 = np.asarray(
                                _p135, dtype=np.float32).reshape(-1, 2)
                            if _pp135.shape[0] >= 3:
                                cv2.fillPoly(
                                    _pm135,
                                    [np.rint(_pp135).astype(np.int32)], 255)
                        except Exception:
                            continue
                    if not int(_pm135.sum()):
                        continue
                    _blk135 = np.zeros((h, w), dtype=np.uint8)
                    _blk135[max(0, _ry):min(h, _ry + _rh),
                            max(0, _rx):min(w, _rx + _rw)] = 255
                    _cov135 = float(cv2.countNonZero(
                        cv2.bitwise_and(_pm135, _blk135))) / \
                        max(1.0, float(_rw * _rh))
                    if _cov135 > 0.90:
                        continue  # متن کامل خوانده شده — دست نمی‌زنیم
                    _pm135d = cv2.dilate(_pm135, np.ones((9, 9), np.uint8))
                    # v1.14.238 — med_hِ ناحیه برایِ سقفهایِ سازگار با
                    # فونتِ درشت (img6: بلندیِ خط ۶۹..۷۹)
                    _mh135 = 0.0
                    try:
                        _pl135 = []
                        for _p135 in _polys135:
                            try:
                                _pp135b = np.asarray(
                                    _p135, dtype=np.float32).reshape(-1, 2)
                                if _pp135b.shape[0] >= 3:
                                    _pl135.append(_pp135b)
                            except Exception:
                                continue
                        _ln135 = MangaTranslator._group_polys_to_lines(
                            _pl135)
                        if _ln135:
                            _mh135 = float(np.median(
                                [b[3] - b[1] for b in _ln135]))
                    except Exception:
                        _mh135 = 0.0
                    _ink135 = MangaTranslator._panel_leftover_ink(
                        image, _rg135.rect, _pm135d, med_h=_mh135)
                    if _ink135 is None:
                        continue
                    _ink135 = cv2.dilate(
                        _ink135, np.ones((9, 9), np.uint8))
                    m = cv2.bitwise_or(m, _ink135)
                    _n_tp += 1
                    if self.debug:
                        try:
                            print(
                                f"  [🔍] پنلِ متنی (گلیفِ جامانده "
                                f"n={int(cv2.countNonZero(_ink135))}px) → "
                                f"ماسکِ گلیف rect={(_rx, _ry, _rw, _rh)}")
                        except Exception:
                            pass
                if _n_tp and self.debug:
                    print(f"  [🔍] پنلِ متنی: {_n_tp} بلوکِ ناقص‌خوانده → "
                          f"گلیفهای جامانده به ماسک رفت")
            except Exception as _e135:
                if self.debug:
                    print("  [!] پنلِ متنی خطا:", _e135)
        # v1.14.134 — پسگیرِ جوهرِ جامانده: قطعههایِ
        # گلیفِ همسایهٔ ماسک که OCRِ ناقص بیرونِ پالی گذاشته
        # ('Yo'/'th'/'a' — حبابِ چپبالای 01.jpg) به ماسک برمیگردند.
        # v1.14.206 — رویِ PC هم فعال شد (دستورِ سازنده: «هم گوشی هم
        # پی سی لینوکس باید هردو عکس هاشون چک کنی») — با env=0
        # قابلِ خاموشکردن است.
        if (os.environ.get("MANGA_INK_RECLAIM", "1") != "0") \
                and n_ok > 0:
            try:
                _add134 = self._stray_ink_reclaim(image, m, regions)
                if _add134 is not None and np.any(_add134):
                    m = cv2.bitwise_or(m, _add134)
                    if self.debug:
                        try:
                            print(f"  [🔍]پسگیرِ جوهر: +"
                                  f"{int(cv2.countNonZero(_add134))}px به ماسک")
                        except Exception:
                            pass
            except Exception:
                pass
        if n_ok <= 0 and n_skip <= 0:
            return None
        # v1.14.104 — «بالنِ سیستم»: اینتریورِ باکسِ سیستم اینجا به ماسک
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
            # v1.14.48: «راهرویِ متن» — جذب فقط در همسایگیِ ناحیهٔ متن.
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
                    # v1.14.48: کامپوننت باید عمدتاً داخلِ راهرویِ متن باشد
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
        """v1.14.134 — «پسگیرِ جوهرِ جامانده» (فقطِ اندروید — گیتِ
        MANGA_INK_RECLAIM).

        ریشهٔ «متن جا میمونه سمت چپِ حباب» (01.jpg، لاگِ گوشیِ
        v1.14.133): پالیهایِ OCRِ ناقصِ آن روز ('ure' بهجایِ You're،
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
        گاردهایِ بعد و جرم رد میشوند — درسِ v1.14.133 (قطعهٔ هنرِ
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
                # رسا = ۰.۸×ارتفاعِ خط — شکافِ واقعیِ 01.jpg تا ۰.۶۷× بود؛
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
                _wh132, _ww132 = g.shape[:2]
                # v1.14.213 — گاردِ رنگ: قطعه باید همرنگِ جوهرِ خودِ ناحیه
                # باشد (دستورِ سازنده: «یک کاری کن حباب متن خراب نشه» —
                # پسگیرِ ۲۰۶ رویِ img6 ضربهٔ صورتیِ SFXِ «あ» کنارِ متن را
                # همتونِ حرف میپنداشت و به ماسکِ پاکسازی میبرد = حذفِ
                # هنر). متنِ آبیِ تیره (هیو ~۱۱۰) و صورتیِ SFX (هیو ~۳۰۰)
                # از رویِ فاصلهٔ هیو جدا میشوند؛ متنِ خاکستری/سیاه/سفید
                # (اشباعِ کم) هرگز قطعهٔ اشباعِ رنگی نمیگیرد.
                _sub_bgr213 = image[wy0:wy1, wx0:wx1]
                _seed_ink213 = (seed & ink)
                _seed_h213 = _seed_s213 = None
                if int(np.count_nonzero(_seed_ink213)) >= 30:
                    try:
                        _hsv213 = cv2.cvtColor(
                            _sub_bgr213, cv2.COLOR_BGR2HSV)
                        _sv213 = _hsv213[_seed_ink213]
                        _seed_h213 = float(np.median(_sv213[:, 0])) * 2.0
                        _seed_s213 = float(np.median(_sv213[:, 1]))
                    except Exception:
                        _seed_h213 = _seed_s213 = None
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
                    _cx132 = int(st[ci, cv2.CC_STAT_LEFT])
                    _cy132 = int(st[ci, cv2.CC_STAT_TOP])
                    if (_cx132 <= 1 or _cy132 <= 1
                            or _cx132 + cwd >= _ww132 - 1
                            or _cy132 + chg >= _wh132 - 1):
                        continue
                    _cm = (lab == ci)
                    if not bool((_cm & _near).any()):
                        continue
                    if not bool((_cm & (_cor > 0)).any()):
                        continue
                    # v1.14.213 — همرنگی با جوهرِ ناحیه (گاردِ رنگِ بالا)؛
                    # MANGA_RECLAIM_COLORGUARD=0 برایِ خاموشکردنِ دستی
                    if _seed_h213 is not None \
                            and os.environ.get(
                                "MANGA_RECLAIM_COLORGUARD", "1") != "0":
                        try:
                            _pc213 = _sub_bgr213[_cm]
                            _ph213 = cv2.cvtColor(
                                _pc213.reshape(-1, 1, 3).astype(
                                    np.uint8), cv2.COLOR_BGR2HSV)
                            _phh213 = float(np.median(_ph213[:, 0, 0])) * 2.0
                            _phs213 = float(np.median(_ph213[:, 0, 1]))
                            _hue_d213 = abs(_phh213 - _seed_h213)
                            _hue_d213 = min(_hue_d213, 360.0 - _hue_d213)
                            # v1.14.213b — فقطِ عدمِتطابقِ «قوی»: آستانهٔ
                            # سختگیرانه (S≥۹۰ / هیو≥۷۰) تا قطعههایِ
                            # سفیدِ کمی-رنگگرفته (JPEG bleed رویِ پنل — img4)
                            # که متنِ واقعیاند رد نشوند (رگرسیونِ img4:
                            # گاردِ ساده نصفِ گلیفها را ازِ پسگیر میگرفت و
                            # پرِ LaMa را کلاً عوض میکرد).
                            if _phs213 > 120.0 and _seed_s213 < 45.0:
                                continue  # قطعهٔ رنگی، متنِ بی‌رنگ
                            if (_phs213 > 110.0 and _seed_s213 > 110.0
                                    and _hue_d213 > 70.0):
                                continue  # رنگِ غلط (SFX/هنرِ همسایه)
                        except Exception:
                            pass
                    # فقط «پیکسلِ تازه» (بیرونِ ماسکِ فعلی) شمرده شود —
                    # بازجذبِ خودِ متنِ ازقبل-ماسکشده هم سقف را پُر میکرد
                    # و دیلیتِ بعدی هالویِ بیفایده حولِ متن میداد
                    _new132 = int(np.count_nonzero(_cm & (~seed)))
                    if _new132 < 6:
                        continue
                    _cand2.append((_new132, ci))
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
            k41 = cv2.getStructuringElement(
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
                    k41) > 0
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
            # v1.14.73 — ناحیهٔ donor-گسترش‌یافته: پرِ فوری نگیرد (حالتِ کیفی)
            if skip_ids and int(getattr(region, "id", -1)) in skip_ids:
                continue
            # v1.14.65 — بنرِ تبلیغ (promo) با پرکنندهٔ فوریِ خطی دست‌کاری
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
                    fill_plane = None  # v1.14.216 — پرِ صفحهٔ گرادیانی
                    _xs1, _ys1, r1 = _sample_xy(1.025)
                    if r1.shape[0] >= 12:
                        avg1 = r1.mean(axis=0)
                        dev1 = np.sqrt(((r1 - avg1[None, :]) ** 2).sum(axis=1))
                        if float((dev1 <= 15.0).mean()) >= 0.99:
                            fill_col = avg1
                            fill_exp = 1.05
                            # v1.14.216 — پرِ صفحه (plane) بهجایِ رنگِ تخت
                            # رویِ گرادیانِ آرام (دستورِ سازنده: «انگار رو هم
                            # پیاده شده مثل کوه دیده میشه»): حلقهٔ تنگِ ۲.۵٪
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
                        # v1.14.226 — حلقهٔ تنگِ «نایکنواخت» هم صفحهای
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
                                _A226 = np.stack([
                                    np.ones(r1.shape[0], np.float32),
                                    _xs1.astype(np.float32),
                                    _ys1.astype(np.float32)], axis=1)
                                _c226, *_ = np.linalg.lstsq(
                                    _A226, r1, rcond=None)
                                _p226 = _A226 @ _c226
                                _r226 = np.sqrt(
                                    ((_p226 - r1) ** 2).sum(axis=1))
                                _rs226 = np.sort(_r226)
                                _k226 = max(8, int(_rs226.shape[0] * 0.8))
                                if float(_rs226[:_k226].mean()) <= 10.0:
                                    _bx226 = float(np.abs(_c226[1]).max())
                                    _by226 = float(np.abs(_c226[2]).max())
                                    _pw226 = float(pp[:, 0].max()
                                                   - pp[:, 0].min())
                                    _ph226 = float(pp[:, 1].max()
                                                   - pp[:, 1].min())
                                    if (_bx226 * _pw226
                                            + _by226 * _ph226) >= 8.0:
                                        fill_plane = _c226
                                        fill_col = avg1
                                        fill_exp = 1.05
                            except Exception:
                                fill_plane = None
                    if fill_col is None:
                        if self._clean_level() != "fast":
                            # v1.14.216 — پرِ صفحهٔ گرادیانی برایِ حلقهٔ
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
                                    # v1.14.226 — پسِ مقاوم: ۲۵٪ بدترین
                                    # نمونهها (هنرِ بیرونِ پنل/لبهٔ قاب)
                                    # خطایِ میانگین را کور میکرد (۴e2e77:
                                    # mean=11.2 رد، بدونِ کانیوت=۸.۶)
                                    _rgs226 = np.sort(_rg)
                                    _kg226 = max(12, int(
                                        _rgs226.shape[0] * 0.75))
                                    if float(_rgs226[:_kg226].mean()) <= 10.0:
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
                                    # v1.14.226 — گاردِ شیبِ عمودی: حلقهٔ
                                    # «آسمان/گرادیان» که بالا و پایینش
                                    # ناهمسان است (>۱۶ کانالِ) با رنگِ تخت
                                    # پر نشود — پرِ فوریِ تختِ هر خط با
                                    # میانگینِ حلقه = نوارِ شیریِ بی‌بافت
                                    # (لگهٔ سفیدِ img4 — آسمانِ ابری).
                                    # چنین خطی به LaMa/TELEA واگذار میشود.
                                    try:
                                        _ym226 = float(np.median(
                                            _ys2f[_close]))
                                        _top226 = _close & (_ys2f <= _ym226)
                                        _bot226 = _close & (_ys2f > _ym226)
                                        if int(_top226.sum()) >= 8 \
                                                and int(_bot226.sum()) >= 8:
                                            _mt226 = np.median(
                                                r2[_top226], axis=0)
                                            _mb226 = np.median(
                                                r2[_bot226], axis=0)
                                            if float(np.abs(
                                                    _mt226 - _mb226).max()) \
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
            # v1.14.244 — علامتِ + برایِ همسطح‌سازی (قراردادِ مشترک با deskew و
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
            # v1.14.47: حلقهٔ نزدیک (۲-۵px بیرونِ ماسک) رنگِ واقعیِ زمینهٔ
            # چسبیده به متن است — هم برای حبابِ سفید و هم بنرِ سیاه. (تغییرِ
            # حلقهٔ دورترِ آزمایشی حباب روی بنرِ تیره را خراب می‌کرد → حذف.)
            ring = (cv2.dilate(crop_msk, np.ones((5, 5), np.uint8)) > 0) & (~m)
            n_ring = int(np.count_nonzero(ring))
            if n_ring < 40:
                return None
            rp = crop_img[ring].astype(np.int16)
            med = np.median(rp, axis=0)
            d = np.abs(rp - med[None, :]).max(axis=1)
            # v1.14.47c: نسخهٔ «مدِ غالبِ bimodal» حذف شد — روی هنر با
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
            # v1.14.216 — گاردِ گرادیان (دستورِ سازنده: «تو جایِ متنِ
            # پاکشده انگار رو هم پیاده شده مثل کوه دیده میشه»): TELEA روی
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
            # v1.14.135 — اندروید/حفرهٔ بزرگِ کنارِ هنر: حلقه ممکن است
            # اقلیتِ «دیوار/کاغذِ روشن» + اقلیتِ هنرِ تیره داشته باشد
            # (بلوکِ متنِ چسبیده به صحنه)؛ fit فقط از پیکسلهایِ روشنِ
            # حلقه — نتیجه: پرِ دیوارِ یکدست بدونِ آلودگیِ هنرِ تیره.
            # (پیشفرض light_ring=False → رفتارِ PC بیت‌به‌بیت همان است)
            try:
                _gl135 = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
                ring &= (_gl135 >= 170.0)
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
            # v1.14.135 — fit_tol: مسیرِ حلقهٔ روشنِ اندروید با تلورانسِ
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
        # v1.14.135 — سقفِ اتحادِ گروه (فقط اندروید — MANGA_LAMA_GROUP_CAP):
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

