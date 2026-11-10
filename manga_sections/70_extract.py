# BUILD-STRIP-START
# MangaTranslator (۳ از ۷) — استخراجِ متن + دوخت/برشِ امنِ صفحهها
# این فایل «قطعهای از بدنهٔ کلاس MangaTranslator» است و بهتنهایی
# اجرا نمیشود — لودرِ manga.py این محتوا را بههمان ترتیبِ شمارهٔ
# فایل، داخلِ کلاس میچسباند. کلاسِ پوششیِ زیر فقط برایِ معتبر
# بودنِ سینتکسِ این فایلِ تکی است و موقعِ بارگذاری حذف میشود.
# (ترکیب از: 180_translator_extract.py + 210_translator_stitch.py)
class _MangaTranslatorBody_70:
# BUILD-STRIP-END
    @staticmethod
    def _estimate_skew_angle(crop_bgr: np.ndarray) -> float:

        try:
            g = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
            med = float(np.median(g))
            ink = (g < max(60, med - 45)).astype(np.uint8) * 255
            ink = cv2.dilate(ink, np.ones((3, 3), np.uint8), iterations=2)
            n, lab, st, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
            crop_area = float(max(1, crop_bgr.shape[0] * crop_bgr.shape[1]))
            angs: List[float] = []
            for i in range(1, n):
                a = int(st[i, cv2.CC_STAT_AREA])
                bw = int(st[i, cv2.CC_STAT_WIDTH])
                bh = int(st[i, cv2.CC_STAT_HEIGHT])
                if a < 150 or max(bw, bh) < 40:
                    continue

                if max(bw, bh) < 2.0 * max(1, min(bw, bh)):
                    continue
                if a > 0.5 * crop_area:
                    continue
                pts = np.column_stack(np.where(lab == i))[:, ::-1].astype(np.float32)
                rect = cv2.minAreaRect(pts)
                box = cv2.boxPoints(rect)
                best_a, best_len = 0.0, 0.0
                for k in range(4):
                    p0, p1 = box[k], box[(k + 1) % 4]
                    dx, dy = float(p1[0] - p0[0]), float(p1[1] - p0[1])
                    ln = float(np.hypot(dx, dy))
                    if ln > best_len:
                        best_len = ln
                        if dx < 0.0:
                            dx, dy = -dx, -dy
                        best_a = float(np.degrees(np.arctan2(dy, dx)))
                if best_a > 90:
                    best_a -= 180.0
                elif best_a < -90:
                    best_a += 180.0
                if abs(best_a) <= 45:
                    angs.append(best_a)
            if not angs:
                return 0.0
            return float(np.median(angs))
        except Exception:
            return 0.0

# تشخیص «پنجرهٔ سیستم» (System Window / Quest / INFO …) از
# نشانه‌های متنی — براکت  ، دونقطه، کلیدواژه و فاصلهٔ خط‌ها — برای
# همهٔ زبان‌ها: انگلیسی، ژاپنی، کره‌ای، چینی. هر خط جدا ترجمه و با
# فونت مخصوص سیستم رندر می‌شود (خواستهٔ کاربر).
    _SYSTEM_KEYWORDS = (
# انگلیسی
        "system", "info", "information", "quest", "mission", "level", "status",
        "window", "menu", "alert", "notice", "warning", "shop", "store",
        "skill", "inventory", "reward", "daily", "weekly", "tutorial",
        "settings", "objective", "complete", "completed", "failed", "bonus",
        "achievement", "notification", "loading", "confirm", "cancel",
        "accept", "decline", "points", "exp", "time left", "countdown",
        "timer", "update", "guild", "dungeon", "penalty", "runaway",
# ژاپنی
        "システム", "情報", "インフォ", "クエスト", "ミッション", "レベル",
        "ステータス", "警告", "注意", "通知", "ショップ", "商店", "アイテム",
        "報酬", "デイリー", "ウィークリー", "達成", "実績", "完了", "失敗",
        "確認", "キャンセル", "設定", "スキル", "経験値", "所持", "メニュー",
        "討伐", "侵入", "準備",
# کره‌ای
        "시스템", "정보", "퀘스트", "미션", "레벨", "상태", "경고", "알림",
        "상점", "아이템", "보상", "일일", "주간", "업적", "완료", "실패",
        "확인", "취소", "설정", "스킬", "경험치", "메뉴", "공지",
# چینی
        "系统", "信息", "任务", "等级", "状态", "警告", "提醒", "通知", "商店",
        "道具", "奖励", "日常", "每周", "成就", "完成", "失败", "确认", "取消",
        "设置", "技能", "经验", "公告", "菜单", "副本", "公会",
    )

    @staticmethod
    def _system_window_score(text: str, line_texts, line_polys, rect) -> int:
        """امتیاز ۰..۱۲ برای «پنجرهٔ سیستم» از نشانه‌های متنی/هندسی.
        ≥۵ → پنجرهٔ سیستم: خط‌ها جدا و با فونت سیستم رندر می‌شوند."""
        try:
            t = str(text or "").strip()
            if not t:
                return 0
            lines = [str(l or "").strip() for l in (line_texts or [])
                     if str(l or "").strip()]
            if not lines:
                lines = [p for p in re.split(r"[\n]+", t) if p.strip()]
            n = len(lines)
            if n <= 0:
                return 0
            score = 0
# ۱) براکتِ سرصفحه — قوی‌ترین نشانه ([ Daily Quest ] / 【】)
            if re.search(r"[\[\u3010][^\]\u3011\n]{1,48}[\]\u3011]", t):
                score += 3
# ۲) کلیدواژه‌های سیستم (چهار زبان — لاتین با مرزِ کلمه)
            kw = MangaTranslator._sys_keyword_hits(lines)
            if kw >= 1:
                score += 2
            if kw >= 3:
                score += 1
# ۳) دونقطه‌های لیبل (HP: 120 / TIME : 05:00)
            colons = sum(l.count(":") + l.count("\uff1a") + l.count("\uff1d")
                         for l in lines)
            if colons >= 2:
                score += 2
# ۴) یکنواختی طول خط‌ها — ترازِ متنِ پنجره (فاصلهٔ متن‌ها)
            lens = [len(l) for l in lines]
            if n >= 3 and max(lens) - min(lens) <= max(6, int(0.35 * max(lens))):
                score += 2
# ۵) فاصلهٔ عمودی باز بین خط‌ها — تایپوگرافی UI
            if line_polys and len(line_polys) >= 3:
                try:
                    tops, hts = [], []
                    for _p in line_polys:
                        _a = np.asarray(_p, dtype=np.float32).reshape(-1, 2)
                        tops.append(float(_a[:, 1].min()))
                        hts.append(max(1.0, float(_a[:, 1].max() - _a[:, 1].min())))
                    tops.sort()
                    gaps = [tops[i2 + 1] - tops[i2] for i2 in range(len(tops) - 1)]
                    hmed = float(np.median(hts))
                    if hmed > 1 and gaps and float(np.median(gaps)) >= hmed * 1.35:
                        score += 2
                except Exception:
                    pass
# ۶) خط‌های کوتاه متعدد
            if n >= 4 and max(lens) <= 42:
                score += 1
# ۷) بدون نقطه‌گذاری جمله‌ای
            if n >= 3 and not any(re.search(r"[\u3002\uff0e\uff01!?\u2026]$", l)
                                  for l in lines):
                score += 1
# ۸) پنجرهٔ عریض با چند خط
            try:
                w_ = int(rect[2]) - int(rect[0])
                h_ = int(rect[3]) - int(rect[1])
                if w_ > 0 and h_ > 0 and (w_ / float(h_)) >= 2.2 and n >= 3:
                    score += 1
            except Exception:
                pass
            return score
        except Exception:
            return 0

    @staticmethod
    def _sys_keyword_hits(lines) -> int:
        """تعداد خط‌های دارای کلیدواژهٔ سیستم. کلیدواژهٔ لاتین با «مرزِ کلمه»
        (\bexp\b نه «unexpected»!) — ژاپنی/کره‌ای/چینی زیررشته."""
        n = 0
        for l in (lines or []):
            ll = str(l or "").strip().lower()
            if not ll:
                continue
            for k in MangaTranslator._SYSTEM_KEYWORDS:
                try:
                    if k.isascii():
                        if re.search(r"(?<![a-z0-9])" + re.escape(k)
                                     + r"(?![a-z0-9])", ll):
                            n += 1
                            break
                    elif k in ll:
                        n += 1
                        break
                except Exception:
                    continue
        return n

    @staticmethod
    def _is_label_block(line_texts) -> bool:
        """: «بلوکِ برچسب» — جعبهٔ مشخصاتِ شخصیت (NAME / AGE: 40 /
        RACE: …) و پنجره‌های UI چندخطیِ کوتاه. این خط‌ها باید «جدا جدا»
        ترجمه شوند (خواستهٔ کاربر)، ولی حبابِ دیالوگِ عادی هرگز نباید.
        شرط‌ها: چند خطِ کوتاه + حداقل ۲ لیبلِ دونقطه‌دار یا براکتِ سرصفحه +
        هیچ خطی با نقطه‌گذاریِ جملهٔ گفتاری تمام نشود (؟ ! …)."""
        try:
            lines = [str(l or "").strip() for l in (line_texts or [])
                     if str(l or "").strip()]
            n = len(lines)
            if not (2 <= n <= 12):
                return False
            lens = [len(l) for l in lines]
            if max(lens) > 46 or (sum(lens) / float(n)) > 30.0:
                return False
# جملهٔ گفتاری — هیچ خط نباید با ؟/!/… تمام شود (جعبهٔ مشخصات ندارد)
            if any(re.search(r"[?!…\u3002\uff01\uff1f]$", l) for l in lines):
                return False
            colon_lines = sum(1 for l in lines if re.search(r"[:\uff1a\uff1d=]", l))
            has_bracket = any(
                re.search(r"[\[\u3010][^\]\u3011]{1,48}[\]\u3011]", l)
                for l in lines)
            if colon_lines >= 2 or has_bracket:
                return True
# بلوکِ کلیدواردی — لیستِ مهارت‌ها (SKILL(S): … / MEDITATION
# / MOBILE MEDITATION (LV.11) / …): یک خطِ کلیدواژه + یک لیبلِ
# دونقطه‌دار + همهٔ خط‌ها ≤۴ کلمه (نثرِ گفتاری این‌قدر کوتاه نیست)
            if len(lines) >= 3 and all(len(l.split()) <= 4 for l in lines):
                kw = MangaTranslator._sys_keyword_hits(lines)
                if kw >= 1 and colon_lines >= 1:
                    return True
            return False
        except Exception:
            return False

    @staticmethod
    def _system_window_strong(text: str, line_texts) -> bool:
        """: نشانهٔ «قوی» پنجرهٔ سیستم — بدون این هیچ حباب عادی
        نباید پنجره حساب شود (براکت سرصفحه / کلیدواژهٔ سیستم / ≥۲ لیبلِ
        دونقطه‌دار). حباب عادی فقط امتیازهای ظاهری دارد (فاصله، تراز)،
        پس این شرط جلوی جدا شدن حباب‌های دیالوگ را می‌گیرد.
        براکت = فقط [ ] و 【 】 — پرانتزِ عادی («(CLRD & TS)») نشانه نیست."""
        try:
            t = str(text or "")
# ۱) براکت سرصفحه — قوی‌ترین ([ Daily Quest ] / 【…】)
            if re.search(r"[\[\u3010][^\]\u3011\n]{1,48}[\]\u3011]", t):
                return True
            lines = [str(l or "").strip().lower() for l in (line_texts or [])
                     if str(l or "").strip()]
            if not lines:
                lines = [p.strip().lower() for p in re.split(r"[\n]+", t) if p.strip()]
# ۲) کلیدواژهٔ سیستم در یکی از خط‌ها (مرزِ کلمه برای لاتین)
            if MangaTranslator._sys_keyword_hits(lines) >= 1:
                return True
# ۳) لیبل‌های دونقطه‌دار (HP: 120 / TIME : 05:00 / GOAL :)
            colons = sum(l.count(":") + l.count("\uff1a") + l.count("\uff1d")
                         for l in lines)
            if colons >= 2:
                return True
            return False
        except Exception:
            return False

    @staticmethod
    def _cluster_ocr_lines(polys, texts, y_tol_factor: float = 0.65):
        """جعبه‌های OCR (که گاهی کلمه‌به‌کلمه‌اند) را به «خط» خوشه‌بندی می‌کند.
        خروجی: [(x0, y0, x1, y1, text)] مرتب بر اساس y."""
        try:
            items = []
            for _i, _p in enumerate(list(polys or [])):
                _t = str((list(texts or []) + [""] * (len(polys or []) ))[_i] or "").strip()
                if not _t:
                    continue
                _a = np.asarray(_p, dtype=np.float32).reshape(-1, 2)
                items.append([float(_a[:, 1].min()), float(_a[:, 1].max()),
                              float(_a[:, 0].min()), float(_a[:, 0].max()), _t])
            if not items:
                return []
            _hs = sorted(it[1] - it[0] for it in items)
            _hmed = max(1.0, float(np.median(_hs)))
            items.sort(key=lambda it: ((it[0] + it[1]) / 2.0, it[2]))
            lines: List[dict] = []
            for it in items:
                _cy = (it[0] + it[1]) / 2.0
                _hit = None
                for ln in lines:
                    _lcy = (ln["y0"] + ln["y1"]) / 2.0
                    if abs(_cy - _lcy) <= max(_hmed * y_tol_factor,
                                              (ln["y1"] - ln["y0"]) * 0.6):
                        _hit = ln
                        break
                if _hit is None:
                    lines.append({"y0": it[0], "y1": it[1], "x0": it[2],
                                  "x1": it[3], "words": [it]})
                else:
                    _hit["y0"] = min(_hit["y0"], it[0])
                    _hit["y1"] = max(_hit["y1"], it[1])
                    _hit["x0"] = min(_hit["x0"], it[2])
                    _hit["x1"] = max(_hit["x1"], it[3])
                    _hit["words"].append(it)
            out = []
            for ln in lines:
                ln["words"].sort(key=lambda w2: w2[2])
                _txt = " ".join(w2[4] for w2 in ln["words"]).strip()
                out.append((ln["x0"], ln["y0"], ln["x1"], ln["y1"], _txt))
            out.sort(key=lambda t2: t2[1])
            return out
        except Exception:
            return []

    def _ocr_pool_workers(self, n_tasks: int) -> int:
        """ — تعدادِ workerِ موازیِ OCR برایِ حلقههایِ کراپ.
        فقط RapidOCRBackend (سشنهای det/recِ ORT مشترک و thread-safe
        هستند — الگویِ _ocr_one90 از ). بقیهٔ بکاندها (Paddle)
        ترتیبی میمانند. پیشفرض: min(4, هستهٔ فیزیکی) —
        MANGA_OCR_WORKERS=N اورراید. خروجیِ OCR در همهٔ حالتها یکسان
        است (همان فراخوانیها، فقط همزمان)."""
        try:
            if n_tasks is None or int(n_tasks) <= 1:
                return 1
            if not isinstance(getattr(self, "ocr", None), RapidOCRBackend):
                return 1
        except Exception:
            return 1
        try:
            w = int(os.environ.get("MANGA_OCR_WORKERS", "0") or 0)
        except Exception:
            w = 0
        if w <= 0:
            try:
# سشنِ OCR خودش intra=2 نخ دارد (تuned در
# RapidOCRBackend) → workerِ موازی = هستهٔ فیزیکی ÷ 2 تا
# مجموعِ نخها اشباع نشود (واگرنه حتی کندتر از ترتیبی
# میشود — بنچمارکِ 2core: 19.1s→18.6s با workers=2×intra2).
                w = max(1, min(4, int(_physical_core_count()) // 2))
            except Exception:
                w = 1
        try:
            return max(1, min(int(w), int(n_tasks)))
        except Exception:
            return 1

    def _ocr_crop(self, image_bgr: np.ndarray, rect,
                  block_rects: Optional[List[Tuple[int, int, int, int]]] = None) \
            -> Tuple[str, List[np.ndarray]]:

        x1, y1, x2, y2 = [int(v) for v in rect]
        h, w = image_bgr.shape[:2]
# کشِ نتیجهٔ OCRِ همان برش: نجاتِ یتیم/خالی گاهی
# همان مستطیلِ نردبانِ اصلی را دوباره OCR میکرد (پروفایل:
# ۶۷ فراخوانی برایِ ۳۱ ناحیه). کلید = مختصاتِ برش + ابعادِ
# تصویر؛ عمرِ کش = یک صفحه (بازیابی در extract_regions_phase).
        try:
            _ck = (x1, y1, x2, y2, w, h,
                      tuple(map(tuple, block_rects)) if block_rects else None)
            _cc = getattr(self, "_ocr_crop_cache226", None)
            if _cc is not None and _ck in _cc:
                return _cc[_ck]
        except Exception:
            pass
        _rv = self._ocr_crop_run(image_bgr, rect, block_rects)
        try:
            if getattr(self, "_ocr_crop_cache226", None) is None:
                self._ocr_crop_cache = {}
            if len(self._ocr_crop_cache) < 512:
                self._ocr_crop_cache[_ck] = _rv
        except Exception:
            pass
        return _rv

    def _ocr_crop_run(self, image_bgr: np.ndarray, rect,
                      block_rects: Optional[List[Tuple[int, int, int, int]]] = None) \
            -> Tuple[str, List[np.ndarray]]:
        x1, y1, x2, y2 = [int(v) for v in rect]
        h, w = image_bgr.shape[:2]
        pad = 8
        x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
        x2, y2 = min(w, x2 + pad), min(h, y2 + pad)
        if x2 - x1 < 8 or y2 - y1 < 8:
            return "", [], [], []
        crop0 = image_bgr[y1:y2, x1:x2]
        ch0, cw0 = crop0.shape[:2]

        try:
            _sk = self._estimate_skew_angle(crop0)
        except Exception:
            _sk = 0.0
        _tilted0 = abs(_sk) >= 8.0
        if _tilted0:
            pad2 = min(120, int(abs(np.sin(np.radians(_sk))) * max(x2 - x1, y2 - y1)) + 16)
            nx1, ny1 = max(0, int(rect[0]) - pad2), max(0, int(rect[1]) - pad2)
            nx2, ny2 = min(w, int(rect[2]) + pad2), min(h, int(rect[3]) + pad2)
            if (nx2 - nx1) > (x2 - x1) or (ny2 - ny1) > (y2 - y1):
                x1, y1, x2, y2 = nx1, ny1, nx2, ny2
                crop0 = image_bgr[y1:y2, x1:x2]
                ch0, cw0 = crop0.shape[:2]

        def _run(crop_bgr, scale: float, apply_offset: bool = True,
                 ang_corr: float = 0.0, origin=None):
            if scale > 1.01:
                crop_bgr = cv2.resize(
                    crop_bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC
                )
            try:
# اندروید: OCRِ برش با crop_mode (detِ بدونِ
# بزرگنمایی) — نردبانِ variantها ۴-۶× ارزانتر میشود
# PC بیت‌به‌بیت دستنخورده.
                _oc = self.ocr
                if _on_android() and getattr(_oc, "_mobile", None) \
                        is not None:
                    results = _oc.ocr(crop_bgr, crop_mode=True)
                else:
                    results = _oc.ocr(crop_bgr)
            except Exception as _e:
# خرابیِ OCRِ برش دیگر بیصدا نمیماند
# (دیباگ: خطِ کوتاهِ خطا — ریشهِ «متن پیدا نشد» فوراً
# در لاگ دیده میشود).
                if getattr(self, "debug", False):
                    print(f"    [!] OCRِ برش خطا داد: {str(_e)[:140]}")
                return "", [], 0.0, []
            if not results or not results[0]:
                return "", [], 0.0, []
            lines, polys, confs, entries = [], [], [], []
            for line in results[0]:
                try:
                    if not (isinstance(line, (list, tuple)) and len(line) >= 2):
                        continue
                    pair = line[1]
                    eng_ang = 0.0
                    if isinstance(pair, (list, tuple)):
                        text = str(pair[0]).strip()
                        conf = float(pair[1]) if len(pair) > 1 else 1.0
                        if len(pair) > 2:
                            try:
                                eng_ang = float(pair[2])
                                if eng_ang > 180.0:
                                    eng_ang -= 360.0
                                if abs(eng_ang) > 45.0:
                                    eng_ang = 0.0
                            except (TypeError, ValueError):
                                eng_ang = 0.0
                    else:
                        text, conf = str(pair).strip(), 1.0
                    if not text or conf < self.min_confidence:
                        continue
                    if self._is_non_english_script(text):
                        continue
                    lines.append(text)
                    confs.append(conf)
                    box0 = line[0] if len(line) >= 1 else None
# blk = شمارهٔ بلوکِ ML Kit (فقط بکاندِ mlkit)
                    _blk_id = -1
                    if isinstance(pair, (list, tuple)) and len(pair) > 3:
                        try:
                            _blk_id = int(pair[3])
                        except (TypeError, ValueError):
                            _blk_id = -1

                    entry_poly = None
                    if box0 is not None and isinstance(box0, (list, tuple, np.ndarray)) and len(box0) >= 3:
                        poly = np.array(line[0], dtype=np.float32).reshape(-1, 2)
                        if poly.min() >= -8 and poly.max() < 100000:
                            if scale > 1.01:
                                poly = poly / scale
                            if apply_offset:
                                _ox, _oy = origin if origin is not None else (x1, y1)
                                poly = poly + np.array([_ox, _oy], dtype=np.float32)
                            polys.append(poly.astype(np.int32))
                            entry_poly = poly.astype(np.float32)
                    entries.append((text, conf, entry_poly,
                                    float(eng_ang) + float(ang_corr),
                                    int(_blk_id)))
                except Exception:
                    continue
            joined = " ".join(lines).strip()
            avg_conf = float(np.mean(confs)) if confs else 0.0
            return joined, polys, avg_conf, entries

# اندروید: امتیازدهیِ واریانت باید «متنِ درستِ هر
# اسکریپت» را بپذیرد؛ فرمولِ قدیمی فقط لاتین را می‌شمرد → رویِ
# صفحهٔ ژاپنی، واریانتِ آشغالِ لاتینِ با confِ تصادفیِ بالاتر
# خوانشِ درستِ CJK را می‌بَرد (نمونه: «描いて精神統一» ← «bI 2 2い»).
# PC بیت‌به‌بیت فرمولِ قدیمی.
        _sc_cjk = _on_android()

        def _score(txt: str, conf: float) -> float:
            if not txt:
                return -1.0
            latin = sum(1 for c in txt if c.isascii() and c.isalpha())
            if _sc_cjk:
                _cjk = sum(
                    1 for c in txt
                    if (0x3040 <= ord(c) <= 0x30FF)
                    or (0x3400 <= ord(c) <= 0x9FFF)
                    or (0xAC00 <= ord(c) <= 0xD7AF))
                return (max(latin, _cjk) * 2.0 + conf * 3.0
                        + min(len(txt), 24) * 0.15)

            return latin * 2.0 + conf * 3.0 + min(len(txt), 24) * 0.15

        candidates = []

        m = max(ch0, cw0)
        if m < 200:
            base_scale = 2.4
        elif m < 360:
            base_scale = 1.8
        elif m < 600:
            base_scale = 1.35
        else:
            base_scale = 1.0

        inset = int(min(ch0, cw0) * 0.06)
        if min(ch0, cw0) >= 160 and ch0 > 2 * inset + 20 and cw0 > 2 * inset + 20:
            core = crop0[inset:ch0 - inset, inset:cw0 - inset]
        else:
            core = crop0

        variants = []
        variants.append(("raw", core, base_scale))
# گیتِ کنتراست برایِ CLAHE: رویِ کراپِ پرکنتراستِ
# تمیز (متنِ سیاهِ حباب رویِ سفید: p90−p10 ≥ ۱۲۰) خروجیِ CLAHE
# عملاً همانِ raw است — یک فراخوانیِ OCRِ کاملِ اضافه به ازایِ
# هر ناحیه (پروفایلِ up0822: ۱۶ فراخوانیِ نردبان برایِ ۵ ناحیه)
# که هیچ واریانتِ تازهای نمیآورد. رویِ کراپِ کمکنتراست/سایهدار
# (دلیلِ وجودِ CLAHE) همچنان اجرا میشود.
        _clahe_skip = False
        try:
            _gc = cv2.cvtColor(core, cv2.COLOR_BGR2GRAY)
            _p10 = float(np.percentile(_gc, 10))
            _p90 = float(np.percentile(_gc, 90))
            _clahe_skip = (_p90 - _p10) >= 120.0
        except Exception:
            _clahe_skip = False
        if not _clahe_skip:
            try:
                lab = cv2.cvtColor(core, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                l2 = cv2.createCLAHE(2.5, (8, 8)).apply(l)
                enh = cv2.cvtColor(cv2.merge((l2, a, b)), cv2.COLOR_LAB2BGR)
                variants.append(("clahe", enh, base_scale))
            except Exception:
                pass
        try:
            g = cv2.cvtColor(core, cv2.COLOR_BGR2GRAY)
            _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            if float(np.mean(bw)) < 127:
                bw = cv2.bitwise_not(bw)
            bw = cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)
            variants.append(("otsu", bw, min(base_scale + 0.25, 2.2)))

            if float(np.median(g)) < 110:
                inv = cv2.cvtColor(cv2.bitwise_not(g), cv2.COLOR_GRAY2BGR)
                variants.append(("inv", inv, min(base_scale + 0.4, 2.6)))
        except Exception:
            pass

        def _bb_of(poly):
            if poly is None:
                return None
            p = np.asarray(poly, dtype=np.float32).reshape(-1, 2)
            return (float(p[:, 0].min()), float(p[:, 1].min()),
                    float(p[:, 0].max()), float(p[:, 1].max()))

        def _overlap_frac(a, b):
            ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
            iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
            inter = ix * iy
            if inter <= 0:
                return 0.0
            aa = max(1e-6, (a[2] - a[0]) * (a[3] - a[1]))
            ab = max(1e-6, (b[2] - b[0]) * (b[3] - b[1]))
            return inter / min(aa, ab)

        merged: List[List] = []
        best = ("", [], -1.0, [], [], [])
        inset_used = inset if core is not crop0 else 0
        early_stop = False

        #). پروفایلِ واقعیِ img6: ۵۹ پاسِ OCR برایِ ۹ ناحیه — ۴۰ پاسش
# «تک‌پاسِ OCR» (
# نردبانِ واریانتها (raw→clahe→otsu→inv) بود در حالی که پاسِ اولِ
# raw همان ۵-۱۱ خطِ نهایی را با conf بالا خوانده بود. حالا: پاسِ
# اولِ (raw) اگر «خوانشِ خوب» داد — متنِ واقعی + conf ≥ ۰٫۸۰ +
# پوششِ جوهرِ عمودی کافی — نردبان اصلاً اجرا نمیشود (۱ پاس به‌ازایِ
# ناحیه). خوانشِ ضعیف/خالی → نردبان کامل مثلِ قبل (کراپِ تیره/کم-
# کنتراست نجاتِ خودش را دارد). پوششِ جوهر = بازهٔ عمودیِ خطهایِ
# یافتشده در برابرِ بازهٔ عمودیِ جوهرِ کراپ — اگر نصفِ حبابِ پر-
# متن ناخوانده مانده باشد، تک‌پاس قبول نمیشود.
        _ink_rows = None
        try:
            _g2 = cv2.cvtColor(core, cv2.COLOR_BGR2GRAY)
            _med2 = float(np.median(_g2))
            _rowink = ((_g2 < max(60.0, _med2 - 45.0)).mean(axis=1))
            _rows = np.flatnonzero(_rowink > 0.02)
            if len(_rows) >= 4:
                _ink_rows = (int(_rows[0]), int(_rows[-1]))
        except Exception:
            _ink_rows = None

        _vi = -1
        for name, crop_v, sc in variants:
            _vi += 1
            txt, polys, conf, entries = _run(crop_v, sc)
            if inset_used and entries:
                polys = [p + inset_used for p in polys]
                for e in entries:
                    if e[2] is not None:
                        e[2][:, 0] += inset_used
                        e[2][:, 1] += inset_used
            #) — PC و اندروید یکسان:
# دو فیلترِ ضدِ «چرت‌پرت» (
# الف) مالکیتِ خط: خطی که به ناحیهٔ همسایهٔ تنگتر تعلق دارد
# از این ناحیه حذف میشود (نمونهٔ img6 #02: نشتِ متنِ حبابِ
# «You're the real attraction here.» به کراپِ حبابِ زرد).
# ب) خطِ آشغالِ لاتین: خطِ تکقسمتیِ بیواکل/بیحرفِ کوتاه
# («FL»، «SS»، «23»، «豊») که فقط جوهرِ هنر است.
# هر دو رویِ مختصاتِ صفحه (بعد از جبرانِ inset) اعمال میشوند.
            _own = max(1.0, float((x2 - x1) * (y2 - y1)))
            if entries:
# سیاستِ عدد/سمبل در سطحِ ناحیه: متنِ «کلِ»
# کاندید (قبل از فیلتر) تعیین میکند که خطِ عدد محتواست
# («19 hi») یا ناحیهٔ فقط-عدد است (no_touch میشود).
                try:
                    _rhas3 = source_has_letters(
                        " ".join(str(_e[0]) for _e in entries))
                except Exception:
                    _rhas3 = None
                _keep = []
                _fix = False
                for _e in entries:
                    _bb = _bb_of(_e[2]) if _e[2] is not None else None
                    if _bb is not None and _line_is_foreign(
                            _bb, block_rects, _own):
                        if self.debug:
                            print(f"    [🔍188] خطِ ناحیهٔ مجاور حذف شد: "
                                  f"{str(_e[0])[:36]!r}")
                        continue
                    _j = _latin_junk_line(_e[0], _rhas3) \
                        if _latin_lang(self) else False
                    if _j:
                        if isinstance(_j, str):
# ترمیمِ «77,I» → «I» بهجایِ حذف
                            _e = (_j,) + tuple(_e[1:])
                            _fix = True
                        else:
                            if self.debug:
                                print(f"    [🔍188] خطِ آشغالِ لاتین حذف شد: "
                                      f"{str(_e[0])[:36]!r}")
                            continue
                    _keep.append(_e)
                if _fix or len(_keep) != len(entries):
                    entries = _keep
                    txt = " ".join(e[0] for e in entries).strip()
                    polys = [np.asarray(e[2], dtype=np.int32)
                             for e in entries if e[2] is not None]
                    conf = (float(np.mean([e[1] for e in entries]))
                            if entries else 0.0)
            _poly_angs = [float(e[3]) if len(e) > 3 else 0.0
                          for e in entries if e[2] is not None]
            for e in entries:
                text, e_conf, e_poly = e[0], e[1], e[2]
                e_ang = float(e[3]) if len(e) > 3 else 0.0
                bb = _bb_of(e_poly)
                hit = None
                if bb is not None:
                    for m_item in merged:
                        mb = _bb_of(m_item[2])
                        if mb is not None and _overlap_frac(bb, mb) > 0.35:
                            hit = m_item
                            break
                if hit is None:
                    merged.append([text, e_conf, e_poly, e_ang,
                                   (e[4] if len(e) > 4 else -1)])
                elif e_conf > hit[1]:
                    hit[0], hit[1], hit[3] = text, e_conf, e_ang
                    if len(hit) > 4:
                        hit[4] = (e[4] if len(e) > 4 else -1)

            scv = _score(txt, conf)
            if scv > best[2]:
                best = (txt, polys, scv, _poly_angs,
                        [e[0] for e in entries if e[2] is not None],
                        [(e[4] if len(e) > 4 else -1)
                         for e in entries if e[2] is not None])

            _latin_n = len(re.sub(r"[^A-Za-z]", "", txt or ""))
# گیتِ «تک‌پاسِ OCR»: پاسِ اولِ (raw) با خوانشِ
# خوب، نردبانِ clahe/otsu/inv را دور میزند (پروفایلِ img6:
# ۴۰ پاسِ نردبان برایِ ۹ ناحیه — اکثرشان بعد از خوانشِ
# موفقِ raw زده میشدند). شرطها: متنِ واقعی (لاتین ≥ ۳ یا
# CJK ≥ ۲) + conf ≥ ۰٫۸۰ + پوششِ عمودیِ جوهر (خطهایِ
# یافته ≥ ۶۰٪ بازهٔ جوهر — حبابِ نصفه‌خوانده قبول نیست).
            if os.environ.get("MANGA_DBG") and _vi == 0:
                print(f"    [DBG230] vi0 name={name} conf={conf:.3f} "
                      f"latin={_latin_n} entries={len(entries)} "
                      f"tilt={_tilted0} ink={_ink_rows}", flush=True)
            if (_vi == 0 and not _tilted0 and entries
                    and conf >= 0.80
                    and (_latin_n >= 3
                         or sum(1 for _ch in (txt or "")
                                if 0x3040 <= ord(_ch) <= 0x30FF
                                or 0x3400 <= ord(_ch) <= 0x9FFF
                                or 0xAC00 <= ord(_ch) <= 0xD7AF) >= 2)):
                if os.environ.get("MANGA_DBG"):
                    print(f"    [DBG230] gate-pass vi={_vi} conf={conf:.2f} "
                          f"latin={_latin_n} entries={len(entries)} "
                          f"ink={_ink_rows}", flush=True)
                _cover_ok = True
                if _ink_rows is not None and merged:
                    _ys = [_bb_of(m[2]) for m in merged
                              if m[2] is not None]
                    _ys = [b for b in _ys if b is not None]
                    if _ys:
                        _fy0 = min(b[1] for b in _ys)
                        _fy1 = max(b[3] for b in _ys)
                        _span = max(1.0, float(
                            _ink_rows[1] - _ink_rows[0]))
                        _cov = (_fy1 - _fy0) / _span
                        _cover_ok = _cov >= 0.60
                if _cover_ok:
                    early_stop = True
                    break

            if ((not _tilted0)
                    and ((conf >= 0.86 and _latin_n >= 8)
                         or (conf >= 0.78 and _latin_n >= 20))):
                early_stop = True
                break

            if (not _tilted0) and conf >= 0.80:
                _cjk = 0
                for _ch in (txt or ""):
                    _o = ord(_ch)
                    if (0x3040 <= _o <= 0x30FF or 0x3400 <= _o <= 0x9FFF
                            or 0xAC00 <= _o <= 0xD7AF):
                        _cjk += 1
                if _cjk >= 3:
                    early_stop = True
                    break

# نجاتِ خطهایِ جامانده در کراپهایِ کشیده (مشکل۱) ──
# لاگِ گوشیِ ۱۸۸ (img6): حبابِ زرد فقط ۴ خط از ۷ خط داد و کلِ صفحه
# ۴۸ خط در برابرِ ۷۱ خطِ PC — detِ خطیِ یکجا رویِ کراپِ بلند
# خطهایِ وسط را از دست میدهد. اگر بینِ خطهایِ یافتشده شکافِ
# بزرگی (>۲× ضخامتِ معمولِ خط) باشد، دو نیمهٔ همپوشانِ کراپ جدا
# OCR میشوند؛ خطهایِ تازه از راهِ dedupِ همپوشانیِ همان به
# merged اضافه میشوند و فیلترهایِ ۱۸۸ هم رویشان اجرا میشود.
# کراپِ سالم (شکافِ نرمال) = صفر هزینهٔ اضافه.
        try:
            if merged and not _tilted0:
                _mx, _mn = max(ch0, cw0), min(ch0, cw0)
                if _mx >= 260 and _mx / max(1, _mn) >= 1.5:
                    _bxs = [_bb_of(m[2]) for m in merged
                               if m[2] is not None]
                    _bxs = [b for b in _bxs if b is not None]
                    if 2 <= len(_bxs) <= 30:
                        _dims = [max(2.0, min(b[2] - b[0], b[3] - b[1]))
                                    for b in _bxs]
                        _med = float(np.median(_dims))
                        _vert = sum(
                            1 for b in _bxs
                            if (b[3] - b[1]) > (b[2] - b[0])
                        ) > len(_bxs) / 2
                        _sb = sorted(_bxs, key=(
                            (lambda b: b[0]) if _vert
                            else (lambda b: b[1])))
                        _maxgap = 0.0
                        for _i in range(len(_sb) - 1):
                            _g = (
                                (_sb[_i + 1][0] - _sb[_i][2])
                                if _vert else
                                (_sb[_i + 1][1] - _sb[_i][3]))
                            if _g > _maxgap:
                                _maxgap = _g
                        if _maxgap > 2.0 * _med:
                            _halves = []
                            if ch0 >= cw0:
                                _oh = max(60, int(ch0 * 0.58))
                                if 60 <= _oh < ch0:
                                    _halves = [
                                        ("half-top", crop0[0:_oh], 0, 0),
                                        ("half-bot", crop0[ch0 - _oh:],
                                         0, ch0 - _oh)]
                            else:
                                _ow = max(60, int(cw0 * 0.58))
                                if 60 <= _ow < cw0:
                                    _halves = [
                                        ("half-left", crop0[:, 0:_ow],
                                         0, 0),
                                        ("half-right",
                                         crop0[:, cw0 - _ow:],
                                         cw0 - _ow, 0)]
                            if _halves and self.debug:
                                print(f"    [🔍189] شکافِ خط {_maxgap:.0f}px "
                                      f"(میانه {_med:.0f}px) → OCRِ نیمهها")
                            for _hn, _hc, _hox, _hoy in _halves:
                                try:
                                    _t2, _p2, _c2, _e2 = _run(
                                        _hc, base_scale,
                                        origin=(x1 + _hox, y1 + _hoy))
                                except Exception:
                                    continue
                                for _e3 in (_e2 or []):
                                    _bb2 = (_bb_of(_e3[2])
                                            if _e3[2] is not None else None)
                                    if _bb2 is None:
                                        continue
                                    if _line_is_foreign(
                                            _bb2, block_rects, _own):
                                        continue
# ناحیه = merged + نیمه‌ها
                                    try:
                                        _rhas = source_has_letters(
                                            " ".join(
                                                [str(_m2[0]) for _m2 in merged]
                                                + [str(_e5[0]) for _e5 in (_e2 or [])]))
                                    except Exception:
                                        _rhas = None
                                    _j2 = _latin_junk_line(_e3[0], _rhas) \
                                        if _latin_lang(self) else False
                                    if _j2:
                                        if isinstance(_j2, str):
                                            _e3 = (_j2,) + tuple(_e3[1:])
                                        else:
                                            continue
                                    _hit2 = None
                                    for _m in merged:
                                        _bm = _bb_of(_m[2])
                                        if _bm is not None and \
                                                _overlap_frac(_bb2, _bm) > 0.35:
                                            _hit2 = _m
                                            break
                                    if _hit2 is None:
                                        merged.append(
                                            [_e3[0], float(_e3[1]), _e3[2],
                                             float(_e3[3]) if len(_e3) > 3 else 0.0,
                                             (int(_e3[4]) if len(_e3) > 4 else -1)])
                                        if self.debug:
                                            print(f"    [🔍189] خطِ بازیابی‌شده از "
                                                  f"{_hn}: {str(_e3[0])[:36]!r}")
        except Exception:
            pass

# نجاتِ خطِ لبه‌بریدهٔ کراپ (متنِ کنارِ حباب) ──
# OCRِ کراپِ حباب متنی را که فقط «گوشه‌اش» داخلِ باکس است نصفه
# می‌خواند (نمونهٔ 01.jpg: «You're the real attraction here.» کنارِ
# حبابِ زرد → تکه‌هایِ «su're / ereal / traction» چسبیده به لبهٔ
# کراپ). اگر خطی به لبهٔ چپ/راستِ کراپ چسبیده بود، کراپ در همان سمت
# باز می‌شود (سقفِ ۱۱۰px یا ۳۵٪ عرض؛ بدونِ عبور از باکسِ ناحیهٔ
# دیگر) و یک پاسِ OCR رویِ کراپِ بازشده زده می‌شود؛ خطِ کامل‌تر
# جایگزینِ تکهٔ نصفه می‌شود. فقط خط‌هایی پذیرفته می‌شوند که در
# نوارِ عمودیِ همان خطِ بریده باشند (جوهرِ نامربوطِ بالا/پایینِ
# نوار جذب نمی‌شود).
        try:
            if merged and not _tilted0:
                _dbg = bool(os.environ.get("MANGA_R90_DBG"))
                _edge = 3 + int(inset_used or 0)
                for _side in (0, 1):
                    if _side == 0:
                        _clip = [m for m in merged if m[2] is not None
                                   and _bb_of(m[2])[0] <= x1 + _edge]
                    else:
                        _clip = [m for m in merged if m[2] is not None
                                   and _bb_of(m[2])[2] >= x2 - _edge]
                    if not _clip:
                        continue
                    _ext = min(110, int((x2 - x1) * 0.35))
                    if _ext < 12:
                        continue
                    if _side == 0:
                        _nb = max(0, x1 - _ext)
                        if block_rects:
                            for (_bx1, _by1, _bx2, _by2) in block_rects:
                                try:
                                    if (_bx1 < x1 and _bx2 > _nb
                                            and _by1 < y2 and _by2 > y1):
                                        _nb = max(_nb,
                                                    min(x1 - 2, _bx2 + 6))
                                except Exception:
                                    continue
                        if _nb >= x1 - 4:
                            continue
                        _crop = image_bgr[y1:y2, _nb:x2]
                        _org = (_nb, y1)
                    else:
                        _nb = min(w, x2 + _ext)
                        if block_rects:
                            for (_bx1, _by1, _bx2, _by2) in block_rects:
                                try:
                                    if (_bx2 > x2 and _bx1 < _nb
                                            and _by1 < y2 and _by2 > y1):
                                        _nb = min(_nb,
                                                    max(x2 + 2, _bx1 - 6))
                                except Exception:
                                    continue
                        if _nb <= x2 + 4:
                            continue
                        _crop = image_bgr[y1:y2, x1:_nb]
                        _org = (x1, y1)
                    if _crop.size == 0 or _crop.shape[0] < 12 \
                            or _crop.shape[1] < 12:
                        continue
                    _ylo = min(_bb_of(m[2])[1] for m in _clip) - 10
                    _yhi = max(_bb_of(m[2])[3] for m in _clip) + 10
                    if _dbg:
                        print(f"    [r90] crop=({x1},{y1},{x2},{y2}) side="
                              f"{'L' if _side == 0 else 'R'} → تاِ {_nb} | "
                              f"بریده: {[m[0] for m in _clip]}", flush=True)
                    _txtE, _polE, _confE, _entE = _run(
                        _crop, base_scale, apply_offset=True, origin=_org)
                    for _e6 in (_entE or []):
                        _tE = str(_e6[0] or "").strip()
                        _pE = _e6[2] if len(_e6) > 2 else None
                        if not _tE or _pE is None:
                            continue
                        _bE = _bb_of(_pE)
                        if _bE is None or (_bE[3] - _bE[1]) < 8:
                            continue
# همان دو فیلترِ ضدِ چرت‌پرت رویِ نجاتِ لبه
                        if _line_is_foreign(_bE, block_rects, _own):
                            continue
# ناحیه = merged + خطِ نجات‌یافته
                        try:
                            _rhasE = source_has_letters(
                                " ".join(
                                    [str(_m2[0]) for _m2 in merged]
                                    + [_tE]))
                        except Exception:
                            _rhasE = None
                        _jE = _latin_junk_line(_tE, _rhasE) \
                            if _latin_lang(self) else False
                        if _jE:
                            if isinstance(_jE, str):
                                _tE = _jE  # ترمیم
                            else:
                                continue
                        _oyE = min(_yhi, _bE[3]) - max(_ylo, _bE[1])
                        if _oyE <= 0.3 * max(1.0, _bE[3] - _bE[1]):
                            continue
                        if _side == 0 and _bE[0] >= x1 - 2:
                            continue
                        if _side == 1 and _bE[2] <= x2 + 2:
                            continue
                        _hitE = None
                        for _m3 in merged:
                            _bM = _bb_of(_m3[2]) if _m3[2] is not None else None
                            if _bM is not None and _overlap_frac(_bE, _bM) > 0.40:
                                _hitE = _m3
                                break
                        if _hitE is None:
                            merged.append([_tE, float(_e6[1]), _pE,
                                           float(_e6[3]) if len(_e6) > 3 else 0.0,
                                           (int(_e6[4]) if len(_e6) > 4 else -1)])
                            if _dbg:
                                print(f"    [r90]   + «{_tE}» "
                                      f"x[{_bE[0]:.0f}-{_bE[2]:.0f}] "
                                      f"y[{_bE[1]:.0f}-{_bE[3]:.0f}]", flush=True)
                        elif _hitE in _clip and (
                                len(_tE) >= len(_hitE[0] or "")):
# تکهٔ بریده جایگزینِ کامل‌تر می‌شود؛ خوانشِ
# کراپِ بازشده کلِ خط را دیده (حتی اگر هم‌طول
# باشد، خوانشِ ناقصِ لبه اعتمادِ کمتری دارد)
                            if _dbg:
                                print(f"    [r90]   ~ «{_hitE[0]}» → «{_tE}»",
                                      flush=True)
                            _hitE[0] = _tE
                            _hitE[1] = float(_e6[1])
                            _hitE[2] = _pE
                            if len(_e6) > 3:
                                _hitE[3] = float(_e6[3])
                            if len(_hitE) > 4 and len(_e6) > 4:
                                _hitE[4] = int(_e6[4])
                        elif _dbg and _hitE is not None:
                            print(f"    [r90]   . نگهِ «{_hitE[0]}» "
                                  f"(جدید: «{_tE}»)", flush=True)
        except Exception:
            pass

        if merged:
            _allow_en, _allow_ko, _allow_ja, _allow_zh = self._ocr_lang_flags()
            if _allow_ja and len(merged) > 1:
                _hts0 = []
                for m_item in merged:
                    mb = _bb_of(m_item[2])
                    if mb is not None:
                        _hts0.append(mb[3] - mb[1])
                _hmax0 = max(_hts0) if _hts0 else 0.0
                if _hmax0 > 0:
                    _kana_re = re.compile(r"^[\u3040-\u30FFー・]+$")
                    _kept = [
                        m for m in merged
                        if not (
                            _kana_re.match((m[0] or "").replace(" ", "").replace("　", ""))
                            and _bb_of(m[2]) is not None
                            and (_bb_of(m[2])[3] - _bb_of(m[2])[1]) < _hmax0 * 0.62
                        )
                    ]
                    if _kept:
                        merged = _kept
# اندروید: فیلترِ «خون‌جهٔ جهت‌به‌در» — متنِ چرخیدهٔ
# ۹۰°ِ کنارِ حباب (یا حبابِ مجاور) که داخلِ کراپِ این ناحیه
# می‌افتد، باکس‌هایی با «جهتِ برعکسِ اکثریت» میسازد و بعداً
# متنِ ناحیه را درهم میریزد (نمونهٔ img6 ناحیهٔ THEN I'LL PULL:
# تکه‌هایِ «re / real / action nere» از متنِ چرخیدهٔ لبهٔ صفحه).
# در ناحیهٔ غالبِ افقی (≥۵۵٪)، باکسِ خیلی‌بلندِ باریک؛ در ناحیهٔ
# غالبِ عمودی، باکسِ خیلی‌پهنِ کوتاه حذف میشود. آستانه‌ها
# محافظه‌کار (۱.۷× میانه + نسبتِ ۱.۶×) و فقط با ≥۳ باکس و بقایِ ≥۲ خط.
# PC بیت‌به‌بیت بدونِ این فیلتر.
            if _on_android() and len(merged) >= 3:
                try:
                    _bbsF = [_bb_of(m[2]) for m in merged]
                    _vF = [b for b in _bbsF if b is not None]
                    if len(_vF) >= 3:
                        _medhF = float(np.median(
                            [b[3] - b[1] for b in _vF]))
                        _medwF = float(np.median(
                            [b[2] - b[0] for b in _vF]))
                        _tallF = sum(
                            1 for b in _vF
                            if (b[3] - b[1]) > 1.4 * (b[2] - b[0]))
                        _wideF = len(_vF) - _tallF
                        _keepF = None
                        if _tallF * 20 >= len(_vF) * 11:
                            _keepF = [
                                m for m, b in zip(merged, _bbsF)
                                if b is None or not (
                                    (b[2] - b[0]) > max(
                                        1.7 * _medwF, _medwF + 28.0)
                                    and (b[2] - b[0]) > 1.6 * (b[3] - b[1]))
                            ]
                        elif _wideF * 20 >= len(_vF) * 11:
                            _keepF = [
                                m for m, b in zip(merged, _bbsF)
                                if b is None or not (
                                    (b[3] - b[1]) > max(
                                        1.7 * _medhF, _medhF + 28.0)
                                    and (b[3] - b[1]) > 1.6 * (b[2] - b[0]))
                            ]
                        if (_keepF is not None and len(_keepF) >= 2
                                and len(_keepF) < len(merged)):
                            merged = _keepF
                except Exception:
                    pass
            hts = []
            for m_item in merged:
                mb = _bb_of(m_item[2])
                if mb is not None:
                    hts.append(mb[3] - mb[1])
            if _on_android():
# اندروید: ترتیبِ درستِ خط‌ها/ستون‌ها.
# ریشهٔ «GO! FASTER. EVEN» / «THERE ATTRACTIONS, ARE NO»:
# row_hِ قدیمی = ۱.۲۵×بلندیِ خط از گامِ واقعیِ خط‌ها بلندتر
# بود → دو خطِ مجاور در یک سطلِ y//row_h می‌افتادند و
# تای‌بریکِ x ترتیبشان را عوض می‌کرد. حالا سطل = ۰.۷۵×میانه
# (کوچکتر از گامِ خط) → هیچ برخوردی. برایِ ستون‌هایِ عمودیِ
# ژاپنی/کره‌ای (اکثریتِ باکس‌ها بلند): ترتیبِ راست‌به‌چپِ
# واقعیِ منگا با x نزولی (rtl) — قدیمی x صعودی می‌خواند.
                _bbsS = [_bb_of(m[2]) for m in merged]
                _vS = [b for b in _bbsS if b is not None]
                if _vS:
                    _medhS = float(np.median(
                        [b[3] - b[1] for b in _vS]))
                    _tallS = sum(
                        1 for b in _vS
                        if (b[3] - b[1]) > 1.4 * (b[2] - b[0]))
                    _rtlS = (
                        getattr(self, "reading_order", "rtl") == "rtl")
                    if len(_vS) >= 2 and _tallS * 2 >= len(_vS):
                        if _rtlS:
                            merged.sort(key=lambda m_item: (
                                (-(_bb_of(m_item[2])[0])
                                 if m_item[2] is not None else 0.0),
                                (_bb_of(m_item[2])[1]
                                 if m_item[2] is not None else 0.0)))
                        else:
                            merged.sort(key=lambda m_item: (
                                (_bb_of(m_item[2])[0]
                                 if m_item[2] is not None else 0.0),
                                (_bb_of(m_item[2])[1]
                                 if m_item[2] is not None else 0.0)))
                    else:
                        _rh = max(8.0, _medhS * 0.75)
                        merged.sort(key=lambda m_item: (
                            ((_bb_of(m_item[2])[1]
                              if m_item[2] is not None else 0.0) // _rh),
                            (_bb_of(m_item[2])[0]
                             if m_item[2] is not None else 0.0)))
            else:
# پورتِ فیکسِ اندروید  به PC: سطلِ
# ۱.۲۵×بلندیِ خط از گامِ واقعیِ خط‌ها بلندتر بود → دو خطِ
# مجاورِ حبابِ با leadingِ فشرده (گامِ ~۱.۰×بلندی) در یک
# سطلِ y//row_h می‌افتادند و تای‌بریکِ x ترتیبشان را
# برمی‌چید (نمونهٔ img7 با detِ 960/max: «STOP BEING A
# SECURITY YOU SHOULD ALSO GUARD…» و «WHEN WERE SINCE WE
# FRIENDS?»؛ رویِ 736/min هم نهفته بود — فقط شانسِ
# ارتفاعِ باکسها جور نبود). سطل = ۰.۷۵×میانه (کوچکتر از
# گامِ خط) → هیچ برخوردی؛ تای‌بریکِ x فقط برای تکههایِ
# همخط (دو باکسِ کنارِ هم) میماند.
                row_h = max(8.0, (float(np.median(hts)) if hts else 8.0) * 0.75)
                merged.sort(key=lambda m_item: (
                    ((_bb_of(m_item[2])[1] if m_item[2] is not None else 0.0) // row_h),
                    (_bb_of(m_item[2])[0] if m_item[2] is not None else 0.0),
                ))
# ستون‌بندیِ خط‌ها: دو ستونِ کنارِ هم (متنِ حباب +
# متنِ دست‌نویسِ کنارش) با مرتب‌سازیِ (y,x) در هم می‌پیچد
# هر ستون متنِ خودش را می‌گیرد و ستون‌ها با \n جدا می‌شوند
# (مترجم دو متنِ جدا را با \n ترجمه/رندر می‌کند).
            try:
                _cg = MangaTranslator._column_line_groups(
                    list(range(len(merged))),
                    [_bb_of(m_item[2]) for m_item in merged],
                    rtl=(getattr(self, "reading_order", "rtl") == "rtl"))
            except Exception:
                _cg = None
            if _cg and len(_cg) > 1:
                _parts = []
                for _g3 in _cg:
                    _gs = sorted(_g3, key=lambda _k: (
                        (_bb_of(merged[_k][2])[1]
                         if merged[_k][2] is not None else 0.0),
                        (_bb_of(merged[_k][2])[0]
                         if merged[_k][2] is not None else 0.0)))
                    _tg = " ".join(
                        str(merged[_k][0] or "").strip() for _k in _gs
                    ).strip()
                    if _tg:
                        _parts.append(_tg)
                u_txt = "\n".join(_parts)
            else:
                u_txt = " ".join(m_item[0] for m_item in merged).strip()
            u_txt = u_txt.strip()
            u_conf = float(np.mean([m_item[1] for m_item in merged])) if merged else 0.0
            u_polys = [
                np.rint(np.asarray(m_item[2], dtype=np.float32)).astype(np.int32)
                for m_item in merged if m_item[2] is not None
            ]
            u_angs = [float(m_item[3]) if len(m_item) > 3 else 0.0
                      for m_item in merged if m_item[2] is not None]
            u_texts = [str(m_item[0] or "") for m_item in merged if m_item[2] is not None]
            u_blks = [int(m_item[4]) if len(m_item) > 4 else -1
                      for m_item in merged if m_item[2] is not None]
            scv = _score(u_txt, u_conf)
            if scv >= best[2]:
                best = (u_txt, u_polys, scv, u_angs, u_texts, u_blks)

        best_txt = best[0] or ""
        latin_n = len(re.sub(r"[^A-Za-z]", "", best_txt))

        skew = self._skew_from_quads(core, best[1], x1, y1, inset_used)
        if skew == 0.0:
            skew = _sk if _sk != 0.0 else self._estimate_skew_angle(core)
        if (not early_stop) and skew != 0.0 and 4.0 <= abs(skew) <= 40.0 and (latin_n < 3 or abs(skew) >= 5.0):
            try:
                hc, wc = core.shape[:2]
                M = cv2.getRotationMatrix2D((wc / 2.0, hc / 2.0), skew, 1.0)
                nw = int(round(wc * abs(np.cos(np.radians(skew))) +
                               hc * abs(np.sin(np.radians(skew))))) + 4
                nh = int(round(wc * abs(np.sin(np.radians(skew))) +
                               hc * abs(np.cos(np.radians(skew))))) + 4
                M[0, 2] += nw / 2.0 - wc / 2.0
                M[1, 2] += nh / 2.0 - hc / 2.0
                desk = cv2.warpAffine(
                    core, M, (nw, nh),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_CONSTANT,
                    borderValue=(255, 255, 255),
                )
                txt, polys, conf, _entries = _run(desk, base_scale,
                                                  apply_offset=False,
                                                  ang_corr=float(skew))
                if txt and polys:
                    M_inv = cv2.getRotationMatrix2D((wc / 2.0, hc / 2.0), -skew, 1.0)
                    M_inv[0, 2] += wc / 2.0 - nw / 2.0
                    M_inv[1, 2] += hc / 2.0 - nh / 2.0
                    off = np.array([x1, y1], dtype=np.float32)
                    back_polys = []
                    for p in polys:
                        pp = p.astype(np.float32).reshape(-1, 2)
                        ones = np.hstack([pp, np.ones((pp.shape[0], 1), dtype=np.float32)])
                        backp = (M_inv @ ones.T).T + off[None, :]
                        back_polys.append(np.rint(backp).astype(np.int32))
                    if inset_used:
                        for pp in back_polys:
                            pp[:, 0] += inset_used
                            pp[:, 1] += inset_used
                    scv = _score(txt, conf)
                    latin_d = len(re.sub(r"[^A-Za-z]", "", txt or ""))
                    if scv > best[2] and latin_d >= latin_n:
                        _desk_angs = []
                        for _bp in back_polys:
                            try:
                                _desk_angs.append(float(
                                    MangaTranslator._poly_long_side_angle(_bp)))
                            except Exception:
                                _desk_angs.append(0.0)
                        _desk_texts = [str(e[0] or "") for e in _entries
                                       if e[2] is not None]
                        _desk_blks = [(int(e[4]) if len(e) > 4 else -1)
                                      for e in _entries if e[2] is not None]
                        best = (txt, back_polys, scv, _desk_angs, _desk_texts,
                                _desk_blks)
            except Exception:
                pass

# نجاتِ متنِ عمودی (±۹۰°): تستِ عکس‌های چرخیدهٔ
# ساختهشده نشان داد ≤۳۵° با deskewِ موجود درست خوانده میشود ولی
# ۶۰-۹۰° خراب میخوانَد (ستونهایِ عمودی به‌شکلِ خطهایِ خیلیبلندِ
# باریک: «OoR U' W EVER» از متنِ افقیِ چرخیده). محرک: کراپِ
# عمودی (h ≥ ۱٫۲×w) که یا هیچ خطی ندارد یا خطهایش «بلندتر از
# عرضِ کراپ»ند (نشانهٔ خوانشِ ستونی). دو پاسِ ±۹۰ (فقط همین دو
# فقط در این حالت) زده میشود و چندضلعیها به مختصاتِ صفحه
# برمیگردند.
        try:
            _latin_b = len(re.sub(r"[^A-Za-z]", "", best[0] or ""))
            _tall = False
            if merged:
                _hb = []
                for m_item in merged:
                    mb = _bb_of(m_item[2])
                    if mb is not None:
                        _hb.append((mb[3] - mb[1], mb[2] - mb[0]))
                if _hb:
                    _mh = float(np.median([b[0] for b in _hb]))
                    _mw = float(np.median([b[1] for b in _hb]))
                    _tall = _mh > max(1.3 * _mw, 1.15 * cw0)
            _need = (
                cw0 >= 40 and ch0 >= 1.2 * cw0
                and ((not merged) or _tall
                     or (_latin_b < 4 and bool(merged))))
# ستونِ عمودیِ واقعیِ CJK (ژاپنی/کره‌ایِ مانگا) متنِ درستِ
# عمودی است — چرخشِ ±۹۰ آن را خراب میکند. اگر متنِ موجودِ
# حروفِ CJK دارد، نجاتِ ۹۰ درجه اجرا نمیشود.
            if _need and merged:
                _cjk_b = sum(
                    1 for _ch in (best[0] or "")
                    if 0x3040 <= ord(_ch) <= 0x30FF
                    or 0x3400 <= ord(_ch) <= 0x9FFF
                    or 0xAC00 <= ord(_ch) <= 0xD7AF)
                if _cjk_b >= 2:
                    _need = False
            if _need:
                for _rotk in (cv2.ROTATE_90_CLOCKWISE,
                                 cv2.ROTATE_90_COUNTERCLOCKWISE):
                    try:
                        _rot_img = cv2.rotate(crop0, _rotk)
                        _rt, _rp, _rc, _re = _run(
                            _rot_img, base_scale, apply_offset=False)
                        if not _re:
                            continue
                        _keep2 = []
# سیاستِ عدد در سطحِ ناحیه برایِ نجاتِ ۹۰°
                        try:
                            _rhas2 = source_has_letters(
                                " ".join(str(_e[0])
                                          for _e in (_re or [])))
                        except Exception:
                            _rhas2 = None
                        for _e4 in (_re or []):
                            if _e4[2] is None:
                                continue
                            _j3 = _latin_junk_line(_e4[0], _rhas2) \
                                if _latin_lang(self) else False
                            if _j3:
                                if isinstance(_j3, str):
                                    _e4 = (_j3,) + tuple(_e4[1:])
                                else:
                                    continue
                            _keep2.append(_e4)
                        if not _keep2:
                            continue
                        _back = []
                        for _e4 in _keep2:
                            _pp = np.asarray(_e4[2], np.float32).reshape(-1, 2)
                            if _rotk == cv2.ROTATE_90_CLOCKWISE:
# (x',y') → (x,y) = (y', ch0-1-x')
                                _bx = _pp[:, 1].copy()
                                _by = (ch0 - 1.0) - _pp[:, 0]
                            else:
# (x',y') → (x,y) = (cw0-1-y', x')
                                _bx = (cw0 - 1.0) - _pp[:, 1]
                                _by = _pp[:, 0].copy()
                            _bp2 = np.stack(
                                [_bx + x1, _by + y1], axis=1)
                            if inset_used:
                                _bp2 += float(inset_used)
                            _back.append(np.rint(_bp2).astype(np.int32))
                        _btxt = " ".join(str(e[0]) for e in _keep2).strip()
                        _bconf = float(np.mean([e[1] for e in _keep2]))
                        _scv = _score(_btxt, _bconf)
                        _bl = len(re.sub(r"[^A-Za-z]", "", _btxt))
                        if _scv > best[2] and _bl >= _latin_b:
                            _bangs = []
                            for _bp2 in _back:
                                try:
                                    _bangs.append(float(
                                        MangaTranslator._poly_long_side_angle(_bp2)))
                                except Exception:
                                    _bangs.append(0.0)
                            best = (_btxt, _back, _scv, _bangs,
                                    [str(e[0]) for e in _keep2],
                                    [(int(e[4]) if len(e) > 4 else -1)
                                     for e in _keep2])
                            if self.debug:
                                print(f"    [🔍230] نجاتِ ±۹۰°: "
                                      f"{_btxt[:60]!r}")
                            break
                    except Exception:
                        continue
        except Exception:
            pass

        return (best[0], best[1], (best[3] if len(best) > 3 else []),
                (best[4] if len(best) > 4 else []),
                (best[5] if len(best) > 5 else []))

    @staticmethod
    def _drop_contained_boxes(boxes: List[dict], contain_thresh: float = 0.72) -> List[dict]:

        if len(boxes) < 2:
            return boxes

        def _area(r):
            return max(0, int(r[2]) - int(r[0])) * max(0, int(r[3]) - int(r[1]))

        def _iou(a, b):
            ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
            iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
            inter = ix * iy
            if inter <= 0:
                return 0.0
            ua = _area(a) + _area(b) - inter
            return inter / float(ua) if ua > 0 else 0.0

        def _contain(big, small):
            ix = max(0, min(big[2], small[2]) - max(big[0], small[0]))
            iy = max(0, min(big[3], small[3]) - max(big[1], small[1]))
            a_s = _area(small)
            return (ix * iy) / a_s if a_s > 0 else 0.0

        n_all = len(boxes)
        is_group = [False] * n_all
        if n_all >= 3:
            for i in range(n_all):
                members = [j for j in range(n_all) if j != i
                           and _contain(boxes[i]["rect"], boxes[j]["rect"]) >= 0.82]
                disjoint: List[int] = []
                for j in members:
                    if all(_iou(boxes[j]["rect"], boxes[k]["rect"]) < 0.10
                           for k in disjoint):
                        disjoint.append(j)
                if len(disjoint) >= 2:
                    is_group[i] = True
        boxes = [b for i, b in enumerate(boxes) if not is_group[i]]

        priority = {"text_bubble": 2, "text_free": 1, "bubble": 0}
        boxes = sorted(
            boxes,
            key=lambda x: (priority.get(x.get("class_name", ""), 0),
                           float(x.get("confidence", 0.0)),
                           _area(x["rect"])),
            reverse=True,
        )
        kept: List[dict] = []
        for b in boxes:
            rb = b["rect"]
            ab = _area(rb)
            if ab < 1:
                continue
            dup = False
            for k in kept:
                rk = k["rect"]

                ix = max(0, min(rb[2], rk[2]) - max(rb[0], rk[0]))
                iy = max(0, min(rb[3], rk[3]) - max(rb[1], rk[1]))
                inter = ix * iy
                smaller = min(ab, _area(rk))
                if smaller > 0 and inter / smaller >= contain_thresh:
                    dup = True
                    break

                if _iou(rb, rk) >= 0.45:
                    dup = True
                    break
            if not dup:
                kept.append(b)
        return kept

    @staticmethod
    def _split_adjacent_balloons(image_bgr: np.ndarray, rect,
                                 min_area_frac: float = 0.16) -> List[list]:

        try:
            x1, y1, x2, y2 = [int(v) for v in rect[:4]]
            h_img, w_img = image_bgr.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w_img, x2), min(h_img, y2)
            full = [x1, y1, x2, y2]
            if x2 - x1 < 48 or y2 - y1 < 48:
                return [full]
            crop = image_bgr[y1:y2, x1:x2]
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            if float(np.mean(bw)) < 127:
                bw = 255 - bw
            k = min(9, max(3, min(bw.shape) // 80))
            bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
            n, _lab, st, _ = cv2.connectedComponentsWithStats(bw, connectivity=8)
            box_area = float((x2 - x1) * (y2 - y1))
            comps: List[list] = []
            for i in range(1, n):
                area = float(st[i, cv2.CC_STAT_AREA])
                cw_, ch_ = int(st[i, cv2.CC_STAT_WIDTH]), int(st[i, cv2.CC_STAT_HEIGHT])
                if area >= box_area * min_area_frac and cw_ >= 32 and ch_ >= 32:
                    comps.append([int(st[i, cv2.CC_STAT_LEFT]), int(st[i, cv2.CC_STAT_TOP]),
                                  cw_, ch_, area])
            if len(comps) < 2:
                return [full]
            comps.sort(key=lambda c: -c[4])
            comps = comps[:4]
            if sum(c[4] for c in comps) < box_area * 0.50:
                return [full]
            subs: List[list] = []
            for cx, cy, cw_, ch_, _a in comps:
                sx1, sy1 = max(x1, x1 + cx), max(y1, y1 + cy)
                sx2, sy2 = min(x2, x1 + cx + cw_), min(y2, y1 + cy + ch_)
                if sx2 - sx1 >= 28 and sy2 - sy1 >= 28:
                    subs.append([sx1, sy1, sx2, sy2])
            if len(subs) < 2:
                return [full]
            ded = MangaTranslator._drop_contained_boxes(
                [{"rect": r} for r in subs], contain_thresh=0.85)
            subs = [d["rect"] for d in ded]
            return subs if len(subs) >= 2 else [full]
        except Exception:
            try:
                return [[int(v) for v in rect[:4]]]
            except Exception:
                return [rect]

    def _ocr_guard_line_boxes(self, crop: np.ndarray):
        """ — جعبههایِ خطِ متنِ داخلِ کراپ (برایِ گاردِ برش).

        از همان فراخوانیِ عادیِ ocr() استفاده میکند (مثلِ کارگرهایِ
        موازی) — نه از حالتِ det-only: rapidocr نسخهٔ ۳ در __call__
        پارامترها را با update_params «دائمی» رویِ موتورِ مشترک
        میگذارد (use_rec=False → همهٔ پاسهایِ بعدیِ همهٔ کارگرها بی‌متن
        میشدند!) پس مسیرِ عادیِ بدونِ تغییرِ وضعیتِ موتور تنها راهِ
        امن است. خروجی: [(x0,y0,x1,y1,h), …] در مختصاتِ کراپ."""
        try:
            try:
                _res = self.ocr.ocr(crop, crop_mode=True)
            except TypeError:
# PaddleOCRWrapper امضایِ crop_mode ندارد (بدونِ تغییرِ
# رفتار — همان پاسِ عادی کافی است)
                _res = self.ocr.ocr(crop)
            boxes = []
            for _pg in (_res or []):
                for _it in (_pg or []):
                    try:
                        boxes.append(np.asarray(
                            _it[0], dtype=np.float32).reshape(-1, 2))
                    except Exception:
                        continue
        except Exception:
            return []
        out = []
        for _p in (boxes or []):
            try:
                _pp = np.asarray(_p, dtype=np.float32).reshape(-1, 2)
                if _pp.shape[0] < 4:
                    continue
                _w = float(_pp[:, 0].max() - _pp[:, 0].min())
                _h = float(_pp[:, 1].max() - _pp[:, 1].min())
                if _w >= 12.0 and _h >= 6.0:
                    out.append((float(_pp[:, 0].min()),
                                float(_pp[:, 1].min()),
                                float(_pp[:, 0].max()),
                                float(_pp[:, 1].max()), _h))
            except Exception:
                continue
        return out

    def _split_cuts_text(self, image: np.ndarray, full_rect, parts) -> bool:
        """ — آیا برشِ حبابهایِ چسبیده از وسطِ «خطِ متن» میگذرد؟

        ریشهٔ باگِ فصلِ Green-Skin 22 (لاگِ سازنده): کپشنِ یک‌خطیِ
        «HELLO, I AM JANG HA-YEON.» با باکسِ درستِ (41,4607,723,4745)
        پیدا شده بود ولی _split_adjacent_balloons آن را به دو نیمه برید
        (خوشههایِ روشنِ پسزمینه دو «حباب» تصور شدند) → دو ناحیهٔ
        «HELLO, I AM JANG HA» + «HA-YEON.» با ترجمههایِ جدا و «HA»
        دوبار. حالا: قبل از پذیرشِ برش، detِ OCR رویِ کراپِ باکسِ کامل
        اجرا میشود؛ اگر خطی از مرزِ بینِ دو پارت (با حاشیهٔ امنِ
        متناسبِ بلندیِ خط — جبرانِ گسترشِ unclip) دو طرف عبور کند، برش
        لغو و باکسِ کامل حفظ میشود. خطی که کامل داخلِ یک پارت است
        (حبابهایِ واقعیِ چسبیده با متنِ جدا) برش را بازنمیگرداند."""
        try:
            _ocr = getattr(self, "ocr", None)
            if _ocr is None:
                return False
            x1, y1, x2, y2 = [int(v) for v in full_rect[:4]]
            _pad = 6
            _cx1 = max(0, x1 - _pad)
            _cy1 = max(0, y1 - _pad)
            _cx2 = min(int(image.shape[1]), x2 + _pad)
            _cy2 = min(int(image.shape[0]), y2 + _pad)
            if _cx2 - _cx1 < 24 or _cy2 - _cy1 < 24:
                return False
            crop = image[_cy1:_cy2, _cx1:_cx2]
            if crop is None or crop.size == 0:
                return False
            lines = self._ocr_guard_line_boxes(crop)
            if not lines:
                return False
# خطهای عمدتاً داخلِ باکس (نه لکهٔ لبهٔ کراپِ همسایه)
            _bx0, _by0 = float(x1 - _cx1), float(y1 - _cy1)
            _bx1, _by1 = float(x2 - _cx1), float(y2 - _cy1)
            _good = []
            for _L in lines:
                _lx0, _ly0, _lx1, _ly1, _lh = _L
                _mxc = (_lx0 + _lx1) * 0.5
                _myc = (_ly0 + _ly1) * 0.5
                if _bx0 - 2 <= _mxc <= _bx1 + 2 and _by0 - 2 <= _myc <= _by1 + 2:
                    _good.append(_L)
            if not _good:
                return False
            _parts = sorted(
                [[int(v) for v in p[:4]] for p in parts],
                key=lambda p: (p[0], p[1]))
            for _a, _b in zip(_parts, _parts[1:]):
# کنارهم (درزِ عمودی) یا رویهم (درزِ افقی)؟
                _ovx = min(_a[2], _b[2]) - max(_a[0], _b[0])
                _ovy = min(_a[3], _b[3]) - max(_a[1], _b[1])
                _wa = max(1, _a[2] - _a[0])
                _ha = max(1, _a[3] - _a[1])
                _side = (_ovy >= 0.5 * min(_ha, max(1, _b[3] - _b[1])))
                _stack = (_ovx >= 0.5 * min(_wa, max(1, _b[2] - _b[0])))
                if not _side and not _stack:
                    continue
                if _side:
                    _lo = max(_a[0], _b[0])
                    _hi = min(_a[2], _b[2])
                    if _hi <= _lo:            # دو پارتِ جدا از هم → درز = فاصله
                        _lo, _hi = min(_a[2], _b[2]), max(_a[0], _b[0])
                    for _lx0, _ly0, _lx1, _ly1, _lh in _good:
                        _tol = min(24.0, max(4.0, 0.12 * max(1.0, _lh)))
                        if (_lo - _lx0) >= _tol and (_lx1 - _hi) >= _tol:
                            return True
                if _stack:
                    _lo = max(_a[1], _b[1])
                    _hi = min(_a[3], _b[3])
                    if _hi <= _lo:
                        _lo, _hi = min(_a[3], _b[3]), max(_a[1], _b[1])
                    for _lx0, _ly0, _lx1, _ly1, _lh in _good:
                        _tol = min(24.0, max(4.0, 0.12 * max(1.0, _lh)))
                        if (_lo - _ly0) >= _tol and (_ly1 - _hi) >= _tol:
                            return True
            return False
        except Exception:
            return False

    @staticmethod
    def _merge_overlapping_regions(regions: List[TextRegion],
                                   iou_thresh: float = 0.35,
                                   contain_thresh: float = 0.65) -> List[TextRegion]:

        if len(regions) < 2:
            return regions

        def _line_min_dims(r):
            """ضخامتِ هر خطِ OCR (minِ عرض/ارتفاع — برایِ متنِ عمودی هم درست)."""
            out = []
            for p in (getattr(r, "ocr_polys", None) or []):
                try:
                    pp = np.asarray(p, dtype=np.float32).reshape(-1, 2)
                    w = float(pp[:, 0].max() - pp[:, 0].min())
                    h = float(pp[:, 1].max() - pp[:, 1].min())
                    d = min(w, h)
                    if d > 2.0:
                        out.append(d)
                except Exception:
                    continue
            return out

        def _incoherent_lines(a, b):
            """ — مشکل۱: دو متنِ جدا در یک ناحیه ممنوع.
            سناریوی img6 (گوشی): باکسِ detِ شلِ حبابِ زرد برچسبِ کوچکِ
            «You're the real attraction here.» را میبلعید؛ merge با
            contain_thresh دو ناحیه را یکی میکرد و دو دیالوگِ مستقل
            قاطی میشدند. اگر هر دو ناحیه چندخطیاند و بلندیِ خطهایشان
            ناهماهنگ است (دو فونتِ متفاوت) و متنِ یکی داخلِ دیگری
            نیست → این جفت نباید ادغام شود."""
            ha = _line_min_dims(a)
            hb = _line_min_dims(b)
            if len(ha) < 2 or len(hb) < 2:
                return False
            ma, mb = float(np.median(ha)), float(np.median(hb))
            if ma <= 0 or mb <= 0:
                return False
            return (max(ma, mb) / min(ma, mb)) >= 1.35

        def rect_xyxy(r: TextRegion):
            x, y, w, h = r.rect
            return [x, y, x + w, y + h]

        def area(xyxy):
            return max(0, xyxy[2] - xyxy[0]) * max(0, xyxy[3] - xyxy[1])

        def iou(a, b):
            ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
            iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
            inter = ix * iy
            if inter <= 0:
                return 0.0
            ua = area(a) + area(b) - inter
            return inter / float(ua) if ua > 0 else 0.0

        def contain_ratio(inner, outer):
            ix = max(0, min(inner[2], outer[2]) - max(inner[0], outer[0]))
            iy = max(0, min(inner[3], outer[3]) - max(inner[1], outer[1]))
            inter = ix * iy
            ai = area(inner)
            return inter / float(ai) if ai > 0 else 0.0

# درِ باکسِ detector: mergeِ دو ناحیه فقط وقتی مجاز
# است که باکسهایِ detectorِ خودشان همپوشانی دارند — نه مستطیلِ
        # detector سه حباب/تایتلِ کج را جدا داده بود؛ ادغامِ
# گسترشیافتهٔ angle.
# مستطیلیِ همپوشانیِ گسترشیافته آنها را یکجا میگرفت.
        def _det_box(r):
            try:
                bs = getattr(r, "boxes", None) or []
                if not bs:
                    return None
                p = np.asarray(bs[0], dtype=np.float32).reshape(-1, 2)
                if p.size < 8:
                    return None
                return [float(p[:, 0].min()), float(p[:, 1].min()),
                        float(p[:, 0].max()), float(p[:, 1].max())]
            except Exception:
                return None

        ordered = sorted(
            regions,
            key=lambda r: (len((r.source_text or "").strip()), r.rect[2] * r.rect[3]),
            reverse=True,
        )
        used = [False] * len(ordered)
        merged: List[TextRegion] = []
        n_merged = 0
        for i, a in enumerate(ordered):
            if used[i]:
                continue
            cur = a
            used[i] = True
            ca = rect_xyxy(cur)
            _cur_det = [d for d in [_det_box(cur)] if d]
            changed = True
            while changed:
                changed = False
                for j, b in enumerate(ordered):
                    if used[j]:
                        continue
                    cb = rect_xyxy(b)
                    _db = _det_box(b)
                    if _cur_det and _db:
                        if not any(
                                iou(cd, _db) >= iou_thresh
                                or contain_ratio(_db, cd) >= contain_thresh
                                or contain_ratio(cd, _db) >= contain_thresh
                                for cd in _cur_det):
# باکسِ detectorِ جدا = متنِ جدا
# مستطیلِ گسترشیافته حقِ جذبِ همسایه را ندارد
                            continue
                    ov = iou(ca, cb)
                    cont_ab = contain_ratio(cb, ca)
                    cont_ba = contain_ratio(ca, cb)
                    if ov < iou_thresh and cont_ab < contain_thresh and cont_ba < contain_thresh:
                        continue

                    nx0 = min(ca[0], cb[0]); ny0 = min(ca[1], cb[1])
                    nx1 = max(ca[2], cb[2]); ny1 = max(ca[3], cb[3])
                    ta = (cur.source_text or "").strip()
                    tb = (b.source_text or "").strip()
                    if not ta:
                        joined = tb
                    elif not tb:
                        joined = ta
                    elif tb.lower() in ta.lower():
                        joined = ta
                    elif ta.lower() in tb.lower():
                        joined = tb
                    elif _incoherent_lines(cur, b):
# مشکل۱: دو متنِ مستقل با فونتِ متفاوت —
# جدا بمانند (img6: حبابِ زرد + برچسبِ کوچک)
                        continue
                    else:

                        if ca[1] <= cb[1]:
                            joined = (ta + " " + tb).strip()
                        else:
                            joined = (tb + " " + ta).strip()
                        joined = re.sub(r"\s{2,}", " ", joined)
                    _aa = float(cur.angle or 0.0)
                    _ba = float(b.angle or 0.0)
                    if abs(_aa) < 3.0:
                        _ang = _ba
                    elif abs(_ba) < 3.0:
                        _ang = _aa
                    elif (_aa > 0.0) == (_ba > 0.0):
                        _ang = (_aa + _ba) / 2.0
                    else:
                        _ang = _aa if abs(_aa) >= abs(_ba) else _ba
                    cur = TextRegion(
                        id=cur.id,
                        boxes=list(cur.boxes or []) + list(b.boxes or []),
                        source_text=joined,
                        rect=(nx0, ny0, nx1 - nx0, ny1 - ny0),
                        angle=_ang,
                        kind=cur.kind if cur.kind == "dialogue" else b.kind,
                        ocr_polys=list(getattr(cur, "ocr_polys", None) or [])
                        + list(getattr(b, "ocr_polys", None) or []),
                    )
                    ca = [nx0, ny0, nx1, ny1]
                    if _db is not None:
                        _cur_det.append(_db)
                    used[j] = True
                    n_merged += 1
                    changed = True
            merged.append(cur)
        return merged

    @staticmethod
    def _poly_long_side_angle(pts) -> float:
        try:
            pts = np.asarray(pts, dtype=np.float32).reshape(-1, 2)
        except Exception:
            return 0.0
        if pts.shape[0] < 2:
            return 0.0
        try:
            box = cv2.boxPoints(cv2.minAreaRect(pts.astype(np.float32)))
        except Exception:
            return 0.0
        best_a, best_len = 0.0, 0.0
        for k in range(4):
            p0, p1 = box[k], box[(k + 1) % 4]
            dx, dy = float(p1[0] - p0[0]), float(p1[1] - p0[1])
            ln = float(np.hypot(dx, dy))
            if ln > best_len:
                best_len = ln
                if dx < 0.0:
                    dx, dy = -dx, -dy
                best_a = float(np.degrees(np.arctan2(dy, dx)))
        if abs(best_a) > 45:
            return 0.0
        return best_a

    @staticmethod
    def _ink_slant_angle(crop_bgr) -> float:
        return MangaTranslator._ink_slant_measure(crop_bgr)[0]

    @staticmethod
    def _ink_slant_support(crop_bgr, angle_deg: float) -> Optional[float]:
        """ — آیا زاویهٔ «ادعاشده» جوهرِ این کراپ را واقعاً رویِ
        هم میاندازد؟ نسبتِ شکستِ ردیفها در زاویهٔ ادعایی بر افقی:
        score(angle)/score(0). ≥~۱٫۱۰ یعنی خطِ واقعاً کج است (وتو نکن)؛
        ~۱٫۰ یعنی کجیِ کاذبِ پالی/فونتِ استایل‌دار (وتو کن).

        ریشه (img3): وتویِ «جوهر مسطح» زاویهٔ واقعیِ ‎-۶٫۷°/-۱۳٫۲° را
        صفر میکرد — سنجشِ قبلی «بهترینِ خودش» را با افقی مقایسه میکرد و
        برایِ خطهایِ کوتاهِ کج، بهترینِ سنجش (~۴°) فقط ۱٫۱× بهتر ازِ
        افقی بود و رأیِ «مسطح» میداد؛ حالا خودِ زاویهٔ ادعایی آزموده
        میشود ()."""
        try:
            if crop_bgr is None or getattr(crop_bgr, "size", 0) == 0:
                return None
            h_c, w_c = crop_bgr.shape[:2]
            if w_c < 40 or h_c < 14:
                return None
            g = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
            med = float(np.median(g))
            _dark = (g < max(60.0, med - 45.0))
            _bright = (g > min(195.0, max(med + 45.0, 150.0)))
            _fd = float(_dark.mean())
            _fb = float(_bright.mean())
            _cands = []
            if 0.010 <= _fd <= 0.45:
                _cands.append(_dark)
            if 0.010 <= _fb <= 0.45:
                _cands.append(_bright)
            if not _cands:
                if 0.45 < _fd <= 0.60:
                    _cands.append(_dark)
                elif 0.010 <= _fb <= 0.60:
                    _cands.append(_bright)
                else:
                    return None
            _cands.sort(key=lambda _b: float(_b.mean()))

            def _sup(ink: np.ndarray) -> Optional[float]:
                try:
                    ys_, xs_ = np.nonzero(ink)
                    if len(ys_) < 60:
                        return None
                    ys_f = ys_.astype(np.float64)
                    xs_f = xs_.astype(np.float64)

                    def _score(theta_deg: float) -> float:
                        t = float(np.tan(np.radians(theta_deg)))
                        rows = ys_f - t * xs_f
                        idx = (rows - rows.min()).astype(np.int32)
                        hist = np.bincount(idx)
                        hf = hist.astype(np.float64)
                        return float(np.dot(hf, hf))

                    s0 = max(1.0, _score(0.0))
                    sa = _score(float(angle_deg))
                    return sa / s0
                except Exception:
                    return None

            for _ink_b in _cands:
                _r = _sup(_ink_b)
                if _r is not None:
                    return _r
            return None
        except Exception:
            return None

    def _ink_slant_measure(crop_bgr) -> Tuple[float, bool]:
        """ — (زاویه، قابل‌اتکا) + قطب‌آگاهیِ تیره/روشن.

        قبلاً فقط جوهرِ تیره سنجیده می‌شد؛ متنِ روشن/درخشان روی زمینهٔ
        تیره (تیترهای BLUE MOON / RED MOON و…) اصلاً سنجیده نمی‌شد و
        وتویِ «جوهرِ مسطح» ممکن نبود — حروفِ استایل‌دار زاویهٔ کاذبِ
        ±۱۵..۲۰° می‌ساختند و متنِ افقی کج رندر می‌شد. حالا قطبِ جوهر
        با جرمِ معقولِ متن (۱٪..۴۵٪) انتخاب می‌شود. خروجیِ دوم یعنی
        «سنجش به نتیجه رسید» (حتی وقتی جواب «مسطح» است) تا caller
        بتواند کجیِ کاذب را صفر کند."""
        try:
            if crop_bgr is None or getattr(crop_bgr, "size", 0) == 0:
                return 0.0, False
            h_c, w_c = crop_bgr.shape[:2]
            if w_c < 40 or h_c < 14:
                return 0.0, False
            g = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
            med = float(np.median(g))
# قطبِ تیره اول (رفتارِ قدیمی)؛ اگر جرمش در بازهٔ متن نبود
# قطبِ روشن (متنِ سفید/درخشان روی زمینهٔ تیره) سنجیده می‌شود
            _dark = (g < max(60.0, med - 45.0))
# آستانهٔ روشن حداقل ۱۵۰: با زمینهٔ تیره، آستانهٔ
# قبلیِ (med+45) هالهٔ گلو و ستاره‌ها را هم «جوهر» می‌گرفت و
# جرم از بازهٔ مجاز بیرون می‌زد → سنجش شکست → کجیِ کاذبِ
# عنوان‌های درخشان (BLUE/RED/PURPLE MOON) وتو نمی‌شد
            _bright = (g > min(195.0, max(med + 45.0, 150.0)))
            _fd = float(_dark.mean())
            _fb = float(_bright.mean())
            _cands = []
            if 0.010 <= _fd <= 0.45:
                _cands.append(_dark.astype(np.uint8))
            if 0.010 <= _fb <= 0.45:
                _cands.append(_bright.astype(np.uint8))
            if not _cands:
# بیرونِ بازه: جرمِ تیرهٔ پر (۰.۴۵..۰.۶۰) مثلِ قبل مجاز
                if 0.45 < _fd <= 0.60:
                    _cands.append(_dark.astype(np.uint8))
                elif 0.010 <= _fb <= 0.60:
                    _cands.append(_bright.astype(np.uint8))
                else:
                    return 0.0, False
# قطبِ کم‌جرم‌تر اول: خودِ متن تقریباً همیشه
# کم‌جرم‌تر از پس‌زمینه است (متنِ روشن روی تیره: bright ~۳۰٪
# در برابر نویزِ تیره ~۴۳٪). قبلاً قطبِ تیره (نویزِ ستاره‌های
# پس‌زمینه) زودتر سنجیده می‌شد و کجیِ کاذبِ مرزیِ (-۱۵°)
# برمی‌گرداند و قطبِ متنِ واقعی هرگز دیده نمی‌شد
# (BLUE MOON روی تصویرِ normalized)
            _cands.sort(key=lambda _b: float(_b.mean()))
            for _ink_b in _cands:
                _res = MangaTranslator._ink_slant_core(_ink_b, h_c, w_c)
                if _res is not None:
                    return _res
            return 0.0, False
        except Exception:
            return 0.0, False

    @staticmethod
    def _ink_slant_core(ink, h_c: int, w_c: int) -> Optional[Tuple[float, bool]]:
        try:
            if float(ink.mean()) < 0.010 or float(ink.mean()) > 0.60:
                return None
            n, lab, st, _cents = cv2.connectedComponentsWithStats(ink, connectivity=8)
            crop_area = float(max(1.0, h_c * w_c))
            clean = np.zeros_like(ink)
            comp_ang: List[float] = []
            for i in range(1, n):
                a_ = int(st[i, cv2.CC_STAT_AREA])
                if a_ < 12 or a_ > 0.08 * crop_area:
                    continue
                x_c = int(st[i, cv2.CC_STAT_LEFT])
                y_c = int(st[i, cv2.CC_STAT_TOP])
                bw_ = int(st[i, cv2.CC_STAT_WIDTH])
                bh_ = int(st[i, cv2.CC_STAT_HEIGHT])
                touches = ((x_c <= 0) + (y_c <= 0)
                           + (x_c + bw_ >= w_c) + (y_c + bh_ >= h_c))
                aspect = max(bw_, bh_) / max(1.0, float(min(bw_, bh_)))
                if a_ < 0.25 * float(max(1, bw_ * bh_)):
                    continue
                if touches >= 2 or (touches >= 1 and aspect > 3.0):
                    continue
                if touches == 1:
                    border_span = 0.0
                    if x_c <= 0 or x_c + bw_ >= w_c:
                        border_span = bh_ / float(h_c)
                    else:
                        border_span = bw_ / float(w_c)
                    if border_span > 0.45 or aspect > 1.9:
                        continue
                clean[lab == i] = 1
                try:
                    _pc = np.column_stack(np.nonzero(lab == i))[:, ::-1].astype(np.float32)
                    _ca = MangaTranslator._poly_long_side_angle(_pc)
                    if abs(_ca) >= 3.0:
                        comp_ang.append(_ca)
                except Exception:
                    pass
            if float(clean.mean()) < 0.008:
                return None
            ys_, xs_ = np.nonzero(clean)
            if len(ys_) < 60:
                return None
            ys_f = ys_.astype(np.float64)
            xs_f = xs_.astype(np.float64)

            def _score(theta_deg: float) -> float:
                t = float(np.tan(np.radians(theta_deg)))
                rows = ys_f - t * xs_f
                idx = (rows - rows.min()).astype(np.int32)
                hist = np.bincount(idx)
                hf = hist.astype(np.float64)
                return float(np.dot(hf, hf))

            best_t, best_s = 0.0, -1.0
            for td in range(-45, 46, 3):
                s_ = _score(float(td))
                if s_ > best_s:
                    best_s, best_t = s_, float(td)
            for td in np.arange(best_t - 3.0, best_t + 3.01, 0.5):
                s_ = _score(float(td))
                if s_ > best_s:
                    best_s, best_t = s_, float(td)
            try:
                if best_s < 1.12 * max(1.0, _score(0.0)):
# سنجید و جوابش «مسطح» است — قابل‌اتکا برایِ وتو
                    return (0.0, True)
            except Exception:
                pass
            a = float(best_t)
            if abs(a) > 45.0:
                return None
            if abs(a) < 5.0:
                return (0.0, True)
            if len(comp_ang) >= 3:
                _med = float(np.median(comp_ang))
                if abs(_med) >= 5.0 and (_med > 0.0) != (a > 0.0):
                    return (_med, True)
            return (a, True)
        except Exception:
            return None

    @staticmethod
    def _polys_vertical(polys) -> bool:
        tall = wide = 0
        for p in list(polys or []):
            try:
                pp = np.asarray(p, dtype=np.float32).reshape(-1, 2)
            except Exception:
                continue
            if pp.shape[0] < 3:
                continue
            pw_ = float(pp[:, 0].max() - pp[:, 0].min())
            ph_ = float(pp[:, 1].max() - pp[:, 1].min())
            if ph_ >= 1.3 * pw_ and ph_ >= 18.0:
                tall += 1
            elif pw_ >= 1.3 * ph_ and pw_ >= 18.0:
                wide += 1
        return tall > wide

    @staticmethod
    def _polys_dense(polys) -> bool:
        tall = wide = 0
        _pl: List[np.ndarray] = []
        for p in list(polys or []):
            try:
                pp = np.asarray(p, dtype=np.float32).reshape(-1, 2)
            except Exception:
                continue
            if pp.shape[0] < 3:
                continue
            _pl.append(pp)
            pw_ = float(pp[:, 0].max() - pp[:, 0].min())
            ph_ = float(pp[:, 1].max() - pp[:, 1].min())
            if ph_ >= 1.3 * pw_ and ph_ >= 18.0:
                tall += 1
            elif pw_ >= 1.3 * ph_ and pw_ >= 18.0:
                wide += 1
        if tall > 0 or wide < 2 or len(_pl) < 2:
            return False
        try:
            _all = np.concatenate(_pl, axis=0)
            _ua = max(1.0, float(_all[:, 0].max() - _all[:, 0].min())
                      * float(_all[:, 1].max() - _all[:, 1].min()))
            _sa = 0.0
            for _q in _pl:
                _sa += 0.5 * abs(float(np.dot(
                    _q[:, 0], np.roll(_q[:, 1], -1))
                    - np.dot(_q[:, 1], np.roll(_q[:, 0], -1))))
            return (_sa / _ua) >= 0.34
        except Exception:
            return False

    @staticmethod
    def _text_block_box(polys, rect, vert: bool):
        try:
            _pl = []
            for p in list(polys or []):
                try:
                    pp = np.asarray(p, dtype=np.float32).reshape(-1, 2)
                except Exception:
                    continue
                if pp.shape[0] >= 3:
                    _pl.append(pp)
            if not _pl:
                return None
            _all = np.concatenate(_pl, axis=0)
            ux0 = float(_all[:, 0].min())
            ux1 = float(_all[:, 0].max())
            uy0 = float(_all[:, 1].min())
            uy1 = float(_all[:, 1].max())
            _ws = [float(p[:, 0].max() - p[:, 0].min()) for p in _pl]
            _hs = [float(p[:, 1].max() - p[:, 1].min()) for p in _pl]
            if vert:
                _mw = float(np.median(_ws)) if _ws else 30.0
                pad_x = max(6.0, 0.55 * _mw)
                pad_y = max(4.0, 0.30 * _mw)
            else:
                _mh = float(np.median(_hs)) if _hs else 20.0
                pad_y = max(6.0, 0.55 * _mh)
                pad_x = max(4.0, 0.35 * _mh)
            ux0 -= pad_x
            ux1 += pad_x
            uy0 -= pad_y
            uy1 += pad_y
            if rect:
                rx, ry, rw, rh = [float(v) for v in rect]
                if not vert:
                    _capw = 0.18 * max(4.0, rw)
                    _caph = 0.30 * max(4.0, rh)
# گشایشِ «تک-لبه» ممنوع: قبلاً هر لبهٔ
# نزدیک جدا گیر میافتاد و اگر فقط «پایینِ» بلوکِ متن
# به پایینِ حباب نزدیک بود (بالا دور — حالتِ طبیعیِ
# متنِ وسطِ حبالِ بلند) جعبه فقط از پایین به لبهٔ حباب
# باز میشد؛ وسطچینیِ بعدی متن را پایین میانداخت
# (img6: حبابِ بالا-راست +53px، وسط +59px پایین‌تر از
# متنِ اصلی — «کمی پایین چپ مینویسه»). حالا هر محور
# فقط وقتی «هر دو» لبه‌اش به حباب نزدیک است به کلِ
# حباب باز میشود؛ وگرنه جعبهٔ خودِ متن میماند.
                    _near_t = 0.0 <= uy0 - ry <= _caph
                    _near_b = 0.0 <= (ry + rh) - uy1 <= _caph
                    _near_l = 0.0 <= ux0 - rx <= _capw
                    _near_r = 0.0 <= (rx + rw) - ux1 <= _capw
                    if _near_t and _near_b:
                        uy0, uy1 = ry, ry + rh
                    if _near_l and _near_r:
                        ux0, ux1 = rx, rx + rw
                ux0 = max(ux0, rx)
                uy0 = max(uy0, ry)
                ux1 = min(ux1, rx + max(4.0, rw))
                uy1 = min(uy1, ry + max(4.0, rh))
            bx0, by0 = int(np.floor(ux0)), int(np.floor(uy0))
            bx1, by1 = int(np.ceil(ux1)), int(np.ceil(uy1))
            if bx1 - bx0 >= 8 and by1 - by0 >= 8:
                return (bx0, by0, bx1 - bx0, by1 - by0)
        except Exception:
            return None
        return None

    @staticmethod
    def _estimate_angle_from_polys(polys) -> float:
        angs: List[float] = []
        for p in list(polys or []):
            angs.append(MangaTranslator._poly_long_side_angle(p))
        if not angs:
            return 0.0
        return float(np.median(angs))

    def _split_mixed_column_regions(self, regions: List["TextRegion"]) -> List["TextRegion"]:
        """ — ستون‌هایِ x-جدا از هم در یک ناحیه → ناحیه‌هایِ جدا.

         متنِ کنارِ حباب (کراپِ بازشدهٔ لبه) را با \n داخلِ «همان»
        ناحیهٔ حباب نگه می‌داشت: جوهرش در ماسکِ حباب پاک می‌شد ولی ترجمه‌اش
        فقط داخلِ حباب رندر می‌شد → «جایش سفید می‌شود، متنش استخراج
        نمی‌شود». حالا وقتی خط‌هایِ OCRِ یک ناحیه در ≥۲ ستونِ با فاصلهٔ
        مرکزیِ واقعی قرار می‌گیرند (خروجیِ _column_line_groups) و متنِ
        \n-دار دقیقاً همان تعداد بخش دارد، هر ستون → ناحیهٔ مستقل با
        rect/پالی/ترجمه/رندرِ خودش. تکی و دسته‌ای یکسان.
        """
        out: List["TextRegion"] = []
        for r in regions:
            try:
                if getattr(r, "sys_span", None) or getattr(r, "sys_split", False):
                    out.append(r)
                    continue
                if abs(float(getattr(r, "angle", 0.0) or 0.0)) >= 8.0:
                    out.append(r)
                    continue
                if getattr(r, "kind", "dialogue") in (
                        "system", "promo", "junk", "sfx", "free_text"):
                    out.append(r)
                    continue
                polys = [p for p in (r.ocr_polys or [])
                         if p is not None and len(np.asarray(p).reshape(-1, 2)) >= 3]
                txt = (r.source_text or "").strip()
                if len(polys) < 4 or "\n" not in txt:
                    out.append(r)
                    continue
                parts = [p.strip() for p in txt.split("\n") if p.strip()]
                if len(parts) < 2:
                    out.append(r)
                    continue
                bbs = []
                for p in polys:
                    pp = np.asarray(p, dtype=np.float32).reshape(-1, 2)
                    bbs.append((float(pp[:, 0].min()), float(pp[:, 1].min()),
                                float(pp[:, 0].max()), float(pp[:, 1].max())))
                groups = MangaTranslator._column_line_groups(
                    list(range(len(polys))), bbs,
                    rtl=(getattr(self, "reading_order", "rtl") == "rtl"))
                if not groups or len(groups) < 2 or len(groups) != len(parts):
                    out.append(r)
                    continue
                med_h = float(np.median([bbs[i][3] - bbs[i][1]
                                         for i in range(len(polys))]))
                spans = sorted(
                    [(min(bbs[i][0] for i in g), max(bbs[i][2] for i in g))
                     for g in groups], key=lambda s: s[0])
                _ok = True
                for _a in range(len(spans) - 1):
                    if spans[_a][1] - spans[_a + 1][0] > max(10.0, 0.45 * med_h):
                        _ok = False
                        break
                if not _ok:
                    out.append(r)
                    continue
                if self.debug:
                    try:
                        print("    [*]ناحیهٔ چندستونی → "
                              f"{len(groups)} ناحیهٔ جدا: "
                              + " | ".join(p[:30] for p in parts))
                    except Exception:
                        pass
                for gi, g in enumerate(groups):
                    xs0 = int(min(bbs[i][0] for i in g)) - 3
                    ys0 = int(min(bbs[i][1] for i in g)) - 3
                    xs1 = int(max(bbs[i][2] for i in g)) + 3
                    ys1 = int(max(bbs[i][3] for i in g)) + 3
                    nx0, ny0 = max(0, xs0), max(0, ys0)
                    out.append(TextRegion(
                        id=-1,
                        boxes=[np.array([[nx0, ny0], [max(nx0 + 1, xs1), ny0],
                                         [max(nx0 + 1, xs1), max(ny0 + 1, ys1)],
                                         [nx0, max(ny0 + 1, ys1)]],
                                        dtype=np.int32)],
                        source_text=parts[gi],
                        rect=(nx0, ny0, max(1, xs1 - nx0), max(1, ys1 - ny0)),
                        angle=float(getattr(r, "angle", 0.0) or 0.0),
                        kind=getattr(r, "kind", "dialogue"),
                        bubble_style=getattr(r, "bubble_style", "normal"),
                        det_class=getattr(r, "det_class", "") or "",
                        ocr_polys=[np.asarray(polys[i], dtype=np.int32)
                                   for i in g],
                    ))
            except Exception:
                out.append(r)
        return out

    def _extract_regions_from_bubbles(self, image: np.ndarray) -> List[TextRegion]:

        if self.det is None:
            return []
        boxes = self.det.detect(image)
        if not boxes:
            return []
        n0 = len(boxes)
# باکسهایِ خامِ detector برایِ رسمِ سبز رویِ همان
        #) — فایلِ جدا حذف شد
# DEBUGِ صفحه (
# باکسها رویِ خودِ ناحیهها سوار میشوند تا از استخرِ استخراج تا
# فازِ صفحه (پاکسازی/رندر) زنده بمانند — استخرهایِ موازی/مختلف.
        _raw_det_dbg = []
        if self.debug:
            try:
                _raw_det_dbg = [
                    ([int(v) for v in _b["rect"][:4]],
                     str(_b.get("class_name") or ""))
                    for _b in boxes]
            except Exception:
                _raw_det_dbg = []
        boxes = self._drop_contained_boxes(boxes, contain_thresh=0.72)
        if len(boxes) < n0 and self.debug:
            print(f"    [*] {n0 - len(boxes)} باکس تودرتو/تکراری حذف شد (از {n0})")

        expanded: List[dict] = []
        split_groups: List[Tuple[List[int], list]] = []
        for b in boxes:
            try:
                parts = MangaTranslator._split_adjacent_balloons(image, b["rect"])
            except Exception:
                parts = [b["rect"]]
            if len(parts) > 1:
# گاردِ «برش، خط را نبُرد»: اگر خطی از مرزِ
# بینِ پارتها عبور کند، باکسِ کامل حفظ میشود (کپشنِ
# یک‌خطیِ Green-Skin 22 دیگر نصف نمیشود).
                try:
                    if self._split_cuts_text(image, b["rect"], parts):
                        print(f"    [*] برشِ باکس {b['rect']} به {len(parts)} "
                              f"حباب لغو شد — خطِ متن از مرز میگذشت (باکس کامل حفظ شد)")
                        parts = [[int(v) for v in b["rect"][:4]]]
                except Exception:
                    pass
            if len(parts) > 1:
                print(f"    [*] باکس {b['rect']} شامل {len(parts)} حباب چسبیده → جدا شدند")
                idxs: List[int] = []
                for p in parts:
                    idxs.append(len(expanded))
                    nb = dict(b)
                    nb["rect"] = p
                    expanded.append(nb)
                split_groups.append((idxs, [int(v) for v in b["rect"][:4]]))
            else:
                expanded.append(b)
        boxes = expanded
# باکس‌های خامِ حباب/متنِ صفحه نگه داشته می‌شوند تا
# گسترشِ donor (کلِ داخلِ حباب در عکسِ اول) ناحیه‌هایِ بدونِ
# det_class (gap-OCR/free-text) هم بتوانند حبابِ خود را پیدا
# کنند.
        try:
            self._page_bubble_boxes = [
                (int(b["rect"][0]), int(b["rect"][1]),
                 int(b["rect"][2]), int(b["rect"][3]),
                 str(b.get("class_name") or ""))
                for b in boxes
            ]
        except Exception:
            self._page_bubble_boxes = []

        regions: List[TextRegion] = []
        h, w = image.shape[:2]
# آستانهٔ نسبیِ «باکسِ خیلی کوچک» باید در مقیاسِ یک
# صفحه/تایل بماند نه کلِ نوار: ۰.۰۸٪ِ نوارِ ۷۰۰×۷۷۹۲ = ۴۳۶۴px²
# می‌شود و حبابِ کوچکِ واقعی («YEAH, YEAH~» با ۵۸×۶۱ — لاگِ
# ۲۴ خام → ۲۳ OCR بدونِ هیچ «حذف شد») با لرزشِ ±چندpxِ
        # + دیباگِ سبزِ D11 رویِ همان حباب).
# باکس غیب می‌شد (
        page_area = float(max(1, min(h, RTDetrV2ONNXDetector.TILE_HEIGHT) * w))
        cand: List[Tuple[int, dict, int, int, int, int, int, int]] = []
        for i, b in enumerate(boxes):
            x1, y1, x2, y2 = b["rect"]
            x1, y1 = max(0, int(x1)), max(0, int(y1))
            x2, y2 = min(w, int(x2)), min(h, int(y2))
            bw, bh = x2 - x1, y2 - y1
            if bw < 16 or bh < 16:
                if self.debug:
                    print(f"    [*] باکسِ ریزِ detector حذف شد: ({x1},{y1},{bw}x{bh})")
                continue

            if bw * bh < page_area * 0.0008 and max(bw, bh) < 60:
                if self.debug:
                    print(f"    [*] باکسِ خیلی کوچک حذف شد: ({x1},{y1},{bw}x{bh})")
                continue
            cand.append((i, b, x1, y1, x2, y2, bw, bh))
        ocr_results: List[Tuple[str, List[np.ndarray], List[float]]] = [
            ("", [], [], [], [])] * len(cand)
# سبکِ جدیدِ استخراج (PC/لینوکس/اندروید یکسان):
# detector-v4-s_int8.onnx محلِ متن را پیدا کرده و OCR فقط رویِ
# همان کراپها تمرکز میکند — هیچ پاسِ تمامصفحه/کاسکادی.
        if cand:
# باکس‌هایِ همسایه به _ocr_crop داده میشود تا
# نجاتِ خطِ لبه‌بریده، کراپ را تا باکسِ ناحیهٔ دیگر باز نکند
# (جذبِ متنِ حبابِ مجاور ممنوع).
            _all_rects = [(t[2], t[3], t[4], t[5]) for t in cand]

            def _ocr_one(k: int):
                _t = cand[k]
                _blk = [_all_rects[j]
                          for j in range(len(_all_rects)) if j != k]
                return self._ocr_crop(
                    image, [_t[2], _t[3], _t[4], _t[5]],
                    block_rects=_blk)

            n_workers = max(1, min(int(getattr(self, "max_workers", 3) or 1), len(cand)))
# همهٔ ناحیهها همزمان (حداکثرِ توانِ سیستم):
# RapidOCR مجازِ موازی: سشن‌های det/rec ORT مشترک و
# thread-safe هستند؛ موتورِ Paddle-Lite هم حالا با «استخرِ
# predictor» در پلِ جاوا موازی شد (هر کارگر یک نمونهٔ
# predictor خودش را برمیدارد — قفلِ سراسریِ run حذف شد).
            _ocr_ts = isinstance(self.ocr, RapidOCRBackend)
            if n_workers > 1 and _ocr_ts:
                if self.debug and not getattr(self, "_par_note90", False):
                    self._par_note = True
                    print(f"    [*] استخراجِ موازی: {len(cand)} ناحیه × "
                          f"{n_workers} کارگر (cpu={os.cpu_count()})")
                with ThreadPoolExecutor(max_workers=n_workers) as ex:
                    ocr_results = list(ex.map(_ocr_one, range(len(cand))))
            else:
                ocr_results = [_ocr_one(k) for k in range(len(cand))]

# خطِ بیرونِ باکسِ detector مالِ این ناحیه نیست
# (توضیحِ کامل در helper) — هر ناحیه فقط متنِ داخلِ باکسِ خودش
# را میگیرد؛ دیگر تایتلِ کجِ مجاور داخلِ حبابِ کوچک نمیآید و
# ناحیهٔ بزرگ هم خطِ حبابهایِ کوچکِ داخلِ باکسش را برنمیدارد
# (مسیرِ deskewِ _ocr_crop از فیلترِ ۱۸۸ رد میشود — اینجا
# بعد ازِ خروجیِ نهایی پوشش داده میشود).
        for _k in range(len(cand)):
            _t = cand[_k]
            ocr_results[_k] = _clamp_lines_to_det(
                ocr_results[_k], (_t[2], _t[3], _t[4], _t[5]),
                _all_rects)

        if split_groups:
            for idxs, full_rect in split_groups:
                try:
                    any_text = any(
                        str(ocr_results[j][0] or "").strip()
                        for j in idxs if 0 <= j < len(ocr_results)
                    )
                except Exception:
                    any_text = True
                if any_text:
                    continue
                full_txt, full_polys, full_angs, _full_lts, _full_blks = \
                    _clamp_lines_to_det(
                        self._ocr_crop(
                            image, full_rect,
                            block_rects=[(cand[j][2], cand[j][3], cand[j][4],
                                          cand[j][5])
                                         for j in range(len(cand))
                                         if j not in idxs]),
                        full_rect,
                        [(cand[j][2], cand[j][3], cand[j][4], cand[j][5])
                         for j in range(len(cand)) if j not in idxs])
                if not str(full_txt or "").strip():
                    continue
                if self.debug:
                    print(f"    [*] اجزای شکسته خالی بودند → OCR باکس کامل {full_rect}")
                fx1, fy1, fx2, fy2 = full_rect
                cand.append((len(cand), {
                    "class_name": "text_bubble", "confidence": 0.40,
                    "rect": full_rect, "shape_type": "round", "mask_poly": None,
                }, fx1, fy1, fx2, fy2, fx2 - fx1, fy2 - fy1))
                ocr_results.append((full_txt, full_polys, full_angs,
                                    _full_lts, _full_blks))

        for (i, b, x1, y1, x2, y2, bw, bh), (text, line_polys, line_angs,
                                             line_texts, line_blks) in zip(
                cand, ocr_results):
            if not text:
                _gink = 0.0
                try:
                    _gx1, _gy1 = max(0, int(x1)), max(0, int(y1))
                    _gx2 = min(image.shape[1], int(x2))
                    _gy2 = min(image.shape[0], int(y2))
                    if _gx2 - _gx1 >= 12 and _gy2 - _gy1 >= 12:
                        _gcrop = image[_gy1:_gy2, _gx1:_gx2]
                        _gg = cv2.cvtColor(_gcrop, cv2.COLOR_BGR2GRAY)
                        _gmed = float(np.median(_gg))
                        _gink = float((_gg < max(60.0, _gmed - 45.0)).mean())
                except Exception:
                    _gink = 0.0
                if 0.008 <= _gink <= 0.50:
# باکسِ تکراریِ حبابِ متن‌دار: ناحیهٔ
# بی‌متنِ هم‌پوشان با ناحیه‌ای که «متن» دارد = دو
# تشخیصِ همان یک حباب (فصلِ Green-Skin 22: باکسِ
# خالیِ 142,5443,740,5680 رویِ باکسِ 200,5602,646,5789
# با متنِ «AHHH!!! AREN'T YOU MY MAN'S PRIZE?» — هر
# دو مالِ یک حبابِ جگ‌دارند؛ خطهایِ باکسِ خالی همه
# به «ناحیهٔ مجاور» (فیلترِ 188) واگذار شده بودند).
# ناحیهٔ خالی حذف میشود: نه پاکسازیِ دوباره، نه
# نجاتِ OCR با متنِ همسایه (ریشهٔ «AHHH!!!» دوبار).
                    try:
                        _dupe = None
                        for _j in range(len(cand)):
                            if _j == i:
                                continue
                            _jt = ""
                            if _j < len(ocr_results):
                                _jt = str(
                                    (ocr_results[_j][0] if ocr_results[_j]
                                     else "") or "").strip()
                            if not _jt:
                                continue
                            _jc = cand[_j]
                            _jx1, _jy1 = float(_jc[2]), float(_jc[3])
                            _jx2, _jy2 = float(_jc[4]), float(_jc[5])
                            _ix3 = max(0.0, min(x2, _jx2) - max(x1, _jx1))
                            _iy3 = max(0.0, min(y2, _jy2) - max(y1, _jy1))
                            _inter = _ix3 * _iy3
                            if _inter <= 0:
                                continue
                            _aA = max(1e-6, float((x2 - x1) * (y2 - y1)))
                            _aB = max(1e-6, (_jx2 - _jx1) * (_jy2 - _jy1))
                            _iom = _inter / min(_aA, _aB)
                            if _iom >= 0.28:
                                _dupe = (_j, _iom)
                                break
                        if _dupe is not None:
                            if self.debug:
                                print(f"    [*] Region [{i}] باکسِ تکراریِ "
                                      f"حبابِ متن‌دار (هم‌پوشانیِ "
                                      f"{_dupe[1]*100:.0f}% با کاندیدِ "
                                      f"{_dupe[0]}) → حذف شد")
                            continue
                    except Exception:
                        pass
# گاردِ «نقطه/نمادِ بی‌متن»: اگر جوهرِ
# ناحیه فقط چند لکهٔ ریز است (مثلِ «....» که det خطی
# برایش نمیسازد؛ بزرگترین مؤلفهٔ جوهر < ۱۸٪ بلندیِ
# کراپ و ≤۱۰ مؤلفه)، دیگر «متنِ ناخوانده» حساب
# نمیشود و دست‌نخورده میمانَد. متنِ واقعیِ
# ناخوانده (دست‌خط/فونتِ عجیب) حروفِ بزرگ دارد و
# از این گارد رد میشود.
                    _dots = False
                    try:
                        _gx1, _gy1 = max(0, int(x1)), max(0, int(y1))
                        _gx2 = min(image.shape[1], int(x2))
                        _gy2 = min(image.shape[0], int(y2))
                        _gc2 = image[_gy1:_gy2, _gx1:_gx2]
                        _gg2 = cv2.cvtColor(_gc2, cv2.COLOR_BGR2GRAY)
                        _gm2 = float(np.median(_gg2))
                        _mk2 = ((_gg2 < max(60.0, _gm2 - 45.0))
                                .astype(np.uint8))
                        _nl2, _l2, _st2, _c2 = cv2.connectedComponentsWithStats(
                            _mk2, connectivity=8)
                        _ncomp2 = 0
                        _maxh2 = 0.0
                        for _ci2 in range(1, _nl2):
                            _a2 = float(_st2[_ci2, cv2.CC_STAT_AREA])
                            if _a2 < 6:
                                continue
                            _w2 = float(_st2[_ci2, cv2.CC_STAT_WIDTH])
                            _h2 = float(_st2[_ci2, cv2.CC_STAT_HEIGHT])
# خطِ نازکِ دورِ حباب (حلقهٔ بیضی، fill کم) حساب
# نمیشود — فقط محتوای توپُر (نقطه/حرف)
                            if _w2 * _h2 > 0 and \
                                    _a2 / (_w2 * _h2) < 0.22:
                                continue
                            _ncomp2 += 1
                            _maxh2 = max(_maxh2, _h2)
                        if _ncomp2 <= 10 and \
                                _maxh2 < 0.18 * max(1, _gy2 - _gy1):
                            _dots = True
                    except Exception:
                        _dots = False
                    if _dots:
                        if self.debug:
                            print(f"    [*] Region [{i}] جوهرِ نقطه/نمادِ "
                                  f"ریز است → دست‌نخورده")
                        continue
                    _epoly = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
                                      dtype=np.int32)
                    regions.append(TextRegion(
                        id=i,
                        boxes=[_epoly],
                        source_text="",
                        rect=(x1, y1, bw, bh),
                        angle=0.0,
                        kind="dialogue",
                        ocr_polys=[],
                        det_class=b.get("class_name", "") or "",
                    ))
                    regions[-1].ocr_empty = True
                    if self.debug:
                        print(f"    [!] Region [{i}] had no OCR text but has "
                              f"text-like ink → cleaning only")
                continue

            if self._is_non_english_script(text):
                continue

# پنجرهٔ سیستم → خط‌به‌خط جدا (نه یک متن یکجا) ──
# فقط با «نشانهٔ قوی»: براکت/کلیدواژه/لیبل دونقطه‌دار.
# حباب عادی (فقط فاصله و تراز) دیگر جدا نمی‌شود.
            try:
                _sys_score = MangaTranslator._system_window_score(
                    text, line_texts, line_polys, (x1, y1, x2, y2))
                _sys_strong = MangaTranslator._system_window_strong(
                    text, line_texts)
            except Exception:
                _sys_score, _sys_strong = 0, False
# جعبهٔ مشخصات (NAME / AGE: 40 / RACE: …) همیشه جدا شود —
# بلوکِ برچسبِ کوتاه با نشانهٔ قوی (≥۲ لیبل دونقطه‌دار یا براکت)
# کافی است؛ دیگر به امتیازِ هندسیِ سخت‌گیر وابسته نیست (قبلاً
# جعبهٔ «DEVON … AGE: 18» با امتیاز ۳ از دست می‌رفت).
            _lbl_block = MangaTranslator._is_label_block(line_texts or [])
            _sys_ok = _sys_strong and (
                _sys_score >= 5
# برچسبِ تک‌خطیِ کوتاه مثل «Status» / «NOTICE» — امتیازِ ظاهری
# به چند خط نیاز دارد؛ برچسب تک‌خطی با نشانهٔ قوی کافی است
                or (len(line_polys) <= 1
                    and len(str(text or '').strip()) <= 28)
                or _lbl_block)
            _sys_can_split = (
                _sys_ok
                and len(line_polys) >= 2
                and len(line_texts or []) == len(line_polys)
                and (_lbl_block or _sys_score >= 6))
            if os.environ.get("MANGA_SYS_DEBUG"):
                try:
                    print(f"    [SYSDBG] text={str(text)[:60]!r} score={_sys_score} "
                          f"strong={_sys_strong} nlp={len(line_polys)} "
                          f"nlt={len(line_texts or [])} lbl={_lbl_block} "
                          f"ok={_sys_ok} cansplit={_sys_can_split}")
                except Exception:
                    pass
            if _sys_can_split:
# OCR گاهی هر «کلمه» را جدا می‌دهد → اول خط‌سازی کن
                _lines = MangaTranslator._cluster_ocr_lines(
                    line_polys, line_texts or [])
                _made = 0
                for (_qx1, _qy1, _qx2, _qy2, _lt) in _lines:
                    _lt = _lt.strip()
                    if not _lt:
                        continue
                    _lx1 = int(max(0, np.floor(_qx1)) - 4)
                    _ly1 = int(max(0, np.floor(_qy1)) - 3)
                    _lx2 = int(min(w - 1, np.ceil(_qx2)) + 4)
                    _ly2 = int(min(h - 1, np.ceil(_qy2)) + 3)
                    if _lx2 - _lx1 < 12 or _ly2 - _ly1 < 8:
                        continue
                    _lpoly = np.array(
                        [[_lx1, _ly1], [_lx2, _ly1], [_lx2, _ly2], [_lx1, _ly2]],
                        dtype=np.int32)
                    _sr = TextRegion(
                        id=len(regions),
                        boxes=[_lpoly],
                        source_text=_lt,
                        rect=(_lx1, _ly1, _lx2 - _lx1, _ly2 - _ly1),
                        angle=0.0,
                        kind="dialogue",
                        bubble_style="system",
                        ocr_polys=[_lpoly],
                        det_class=b.get("class_name", "") or "",
                    )
                    _sr.style_locked = True
                    _sr.sys_split = True
# مستطیلِ والد برای پوششِ gap-OCR (تا خط‌ها دوباره OCR نشوند)
                    _sr.cover_rect = (x1, y1, x2, y2)
                    regions.append(_sr)
                    _made += 1
                if _made:
                    if self.debug:
                        print(f"    [*] پنجرهٔ سیستم → {_made} خط جداگانه")
                    continue

            kind = self._classify_text(text)

            if kind == "dialogue":
                if MangaTranslator._is_watermark_text(text):
# واترمارکِ رویِ حباب: باقیِ متنِ واقعی =
# دیالوگ میماند (واترمارک از متنِ ترجمه هم برداشته میشود)
                    _scrub = MangaTranslator._strip_watermark_tokens(text)
                    if _scrub and self._classify_text(_scrub) == "dialogue":
                        text = _scrub
                    else:
                        kind = "promo"

            if kind == "junk":
                if not MangaTranslator._is_watermark_text(text):
                    latin = re.sub(r"[^A-Za-z]", "", text)
                    if len(latin) >= 3 and any(c in "AEIOUaeiou" for c in latin):
                        kind = "dialogue"
            poly = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.int32)
            eng_angs = []
            for _a in (line_angs or []):
                try:
                    _af = float(_a)
                except (TypeError, ValueError):
                    continue
                if _af > 180.0:
                    _af -= 360.0
                if abs(_af) > 45.0:
                    continue
                if abs(_af) >= 1.0:
                    eng_angs.append(_af)
            ang_src = "ink"
            poly_ang = self._estimate_angle_from_polys(line_polys)
            if abs(poly_ang) >= 3.0:
                ang_ = poly_ang
                ang_src = "poly"
            elif eng_angs:
                ang_ = float(np.median(eng_angs))
                ang_src = "engine"
            else:
                ang_ = poly_ang
            _is_vert = self._polys_vertical(line_polys)
            if abs(ang_) < 5.0:
                try:
                    if _is_vert:
                        _tx1, _ty1 = float(x1), float(y1)
                        _tx2, _ty2 = float(x2), float(y2)
                    else:
                        _tx1 = _ty1 = None
                        if line_polys:
                            try:
                                _pts_all = np.concatenate(
                                    [np.asarray(p).reshape(-1, 2) for p in line_polys])
                                _tx1, _ty1 = float(_pts_all[:, 0].min()), float(_pts_all[:, 1].min())
                                _tx2, _ty2 = float(_pts_all[:, 0].max()), float(_pts_all[:, 1].max())
                            except Exception:
                                _tx1 = _ty1 = None
                        if _tx1 is None:
                            _tx1, _ty1, _tx2, _ty2 = float(x1), float(y1), float(x2), float(y2)
                    _iy1, _iy2 = max(0, int(_ty1)), min(image.shape[0], int(_ty2) + 1)
                    _ix1, _ix2 = max(0, int(_tx1)), min(image.shape[1], int(_tx2) + 1)
                    if _ix2 - _ix1 >= 40 and _iy2 - _iy1 >= 14:
                        a_ink2 = MangaTranslator._ink_slant_angle(
                            image[_iy1:_iy2, _ix1:_ix2])
                        _thr_ink = 7.0 if _is_vert else 5.0
                        if abs(a_ink2) >= _thr_ink and abs(a_ink2) > abs(ang_) + 1.0:
                            ang_ = a_ink2
                            ang_src = "ink"
                except Exception:
                    pass
            rx1, ry1, rw_, rh_ = x1, y1, bw, bh
            if line_polys and abs(ang_) >= 8.0:
                try:
# فقط خطهایی که بیشترشان داخلِ باکسِ detector
# اند در گسترشِ مستطیل شرکت میکنند؛ خطِ ترکیبیِ عابر
# (تکهٔ حبابِ مجاور چسبیده به تایتلِ کج) نباید مستطیلِ
# ناحیه را تا رویِ حبابِ مجاور بکشد (همان «کلِ سه حباب
# گرفته») — خودِ خط برایِ ترجمه/پاکسازی میماند.
                    _rx_pts = []
                    for _p in line_polys:
                        try:
                            _pp = np.asarray(_p,
                                                dtype=np.float32).reshape(-1, 2)
                            _qx1 = float(_pp[:, 0].min())
                            _qy1 = float(_pp[:, 1].min())
                            _qx2 = float(_pp[:, 0].max())
                            _qy2 = float(_pp[:, 1].max())
                            _qa = max(1.0, (_qx2 - _qx1) * (_qy2 - _qy1))
                            _ix = max(0.0, min(_qx2, float(x2))
                                         - max(_qx1, float(x1)))
                            _iy = max(0.0, min(_qy2, float(y2))
                                         - max(_qy1, float(y1)))
                            if (_ix * _iy) / _qa >= 0.60:
                                _rx_pts.append(_pp)
                        except Exception:
                            _rx_pts.append(
                                np.asarray(_p).reshape(-1, 2))
                    if not _rx_pts:
                        _rx_pts = [np.asarray(p).reshape(-1, 2)
                                      for p in line_polys]
                    pts = np.concatenate(_rx_pts)
                    px1, py1 = int(pts[:, 0].min()), int(pts[:, 1].min())
                    px2, py2 = int(pts[:, 0].max()) + 1, int(pts[:, 1].max()) + 1
                    rx1, ry1 = min(rx1, px1), min(ry1, py1)
                    rw_ = max(x1 + bw, px2) - rx1
                    rh_ = max(y1 + bh, py2) - ry1
                except Exception:
                    rx1, ry1, rw_, rh_ = x1, y1, bw, bh
            regions.append(TextRegion(
                id=i,
                boxes=[poly],
                source_text=text,
                rect=(rx1, ry1, rw_, rh_),
                angle=ang_,
                kind=kind,
                ocr_polys=line_polys,
                det_class=b.get("class_name", "") or "",
            ))
            regions[-1].angle_src = ang_src
            if _raw_det_dbg:
# باکسِ خامِ detector برایِ DEBUGِ سبزِ صفحه
                regions[-1].det_raw = _raw_det_dbg
            if _sys_ok:
# تک‌خطی/تگ براکت‌دار مثل [ Daily Quest ] — فونت سیستم
                regions[-1].bubble_style = "system"
                regions[-1].style_locked = True
                if self.debug:
                    print(f"    [*] برچسب/پنجرهٔ سیستم (تک‌قطعه) → فونت سیستم")

# خط‌های تکراریِ پنجرهٔ سیستم (والدهای هم‌پوشان detector) → یکی
        try:
            _sreg = [r for r in regions if getattr(r, "sys_split", False)]
            if len(_sreg) > 1:
                def _riou(_a, _b):
                    ax, ay, aw, ah = _a.rect
                    bx, by, bw2, bh2 = _b.rect
                    ix = max(0, min(ax + aw, bx + bw2) - max(ax, bx))
                    iy = max(0, min(ay + ah, by + bh2) - max(ay, by))
                    inter = ix * iy
                    if inter <= 0:
                        return 0.0
                    return inter / float(min(aw * ah, bw2 * bh2) or 1)
                _keep = []
                for _r in sorted(_sreg, key=lambda r: -(len(r.source_text or "")
                                                        * 1000 + r.rect[2] * r.rect[3])):
                    if any(_riou(_r, _k) >= 0.45 for _k in _keep):
                        continue
                    _keep.append(_r)
                if len(_keep) < len(_sreg):
                    _drop_ids = {id(r) for r in _sreg if r not in _keep}
                    regions = [r for r in regions if id(r) not in _drop_ids]
                    if self.debug:
                        print(f"    [*] {len(_drop_ids)} خط تکراری پنجرهٔ سیستم حذف شد")
        except Exception:
            pass

# «پهنای پنجره» برای خط‌های پنجرهٔ سیستم — OCR گاهی تهِ خط را
# نمی‌گیرد («speed)» می‌ماند)؛ پس افقی تا پهنای مشترک همهٔ خط‌های همان
# پنجره (یا والد، با حاشیهٔ امن) گسترش بده تا پاکسازی کامل شود.
        try:
            _sys_groups: Dict[Tuple[int, int], List[TextRegion]] = {}
            for _r in regions:
                if not getattr(_r, "sys_split", False):
                    continue
                _cr = getattr(_r, "cover_rect", None)
                _key = (int(_cr[0]), int(_cr[1])) if _cr else (
                    int(_r.rect[0]), int(_r.rect[1]))
                _sys_groups.setdefault(_key, []).append(_r)
            for _grp in _sys_groups.values():
                if not _grp:
                    continue
                _cr = getattr(_grp[0], "cover_rect", None)
                if _cr:
                    _pw = max(1, int(_cr[2]) - int(_cr[0]))
                    _inset = max(6, int(0.03 * _pw))
                    _sx0 = min(int(_cr[0]) + _inset,
                               min(int(r_.rect[0]) for r_ in _grp))
                    _sx1 = max(int(_cr[2]) - _inset,
                               max(int(r_.rect[0] + r_.rect[2]) for r_ in _grp))
                else:
                    _sx0 = min(int(r_.rect[0]) for r_ in _grp)
                    _sx1 = max(int(r_.rect[0] + r_.rect[2]) for r_ in _grp)
                for r_ in _grp:
                    r_.sys_span = (max(0, _sx0), _sx1)
        except Exception:
            pass

        before = len(regions)
        regions = self._split_mixed_column_regions(regions)
        regions = self._merge_overlapping_regions(regions, iou_thresh=0.35, contain_thresh=0.65)
        if self.debug:
            print(f"    [*] RT-DETR: {n0} خام → {before} OCR → {len(regions)} نهایی")
# نجاتِ «خطِ یتیم»: خطی که detector اصلاً نبینیده
# (نمونهٔ واقعی: «OUTER GOD WITHIN 7 YEARS.]» زیرِ پنجرهٔ
# [CLEAR OBJECTIVE…]) — بدونِ این نجات نه ترجمه میشد نه پاکسازی.
        try:
            regions = self._rescue_orphan_lines(image, regions)
        except Exception:
            pass
        return regions

    @staticmethod
    def _dedup_duplicate_text_regions(
            regions: List["TextRegion"]) -> List["TextRegion"]:
        """ — حذفِ نواحیِ «هممتنِ همپوشان» (ضدِ رندرِ دوباره).

        . ریشه: دو باکسِ detectorِ
        همپوشان (IoU < آستانهٔ NMS ولی همپوشانیِ واقعیِ ۵۰٪+) هر دو
        زنده میمانند، OCRِ هر دو همان متنِ فیزیکی را میخواند → دو ناحیه
        با متنِ یکسان و مستطیلهای همپوشان → دو ترجمه → دو رندرِ
        بالای هم (لاگِ گوشی: #07/#08 «GO! EVEN FASTER…»). همینطور
        خطِ یتیمِ نجات‌یافته (216) که در نوارِ مجاورِ ناحیهٔ موجود،
        خطِ «همان» ناحیه را دوباره پیدا میکند.

        قواعد (محافظهکار — متنِ متفاوت هرگز حذف نمیشود):
          ۱) نرمالسازی: حروف کوچک + حذفِ نویسههای غیرِ واژه (علائم/
             فاصله) — برایِ همهٔ خطها (لاتین/فارسی/ja/ko/zh).
          ۲) جفتِ «متنِ یکسان» (یا جابهجاییِ واژهها — همانِ چندمجموعهٔ
             نویسهها؛ نمونهٔ واقعیِ img6: «EVEN GO! FASTER...» در برابر
             «GO! FASTER... EVEN»): همپوشانی ≥۱۸٪ مساحتِ کوچکتر یا
             احتوای ≥۴۵٪ → نسخهٔ کوچکتر (خط/مساحتِ کمتر) حذف.
          ۳) جفتِ «شبیهِ هم» (بازخوانیِ کج‌وکولهٔ OCRِ همان متن —
             نسبتهایِ difflib ≥۰٫۶۲ با طولِ ≥۶): مثلِ ۲.
          ۴) جفتِ «زیررشته»: متنِ یکی داخلِ دیگری + احتوای ≥۶۰٪ →
             ناحیهٔ درونی (بخشی) حذف — بازخوانیِ نصفهٔ همان متن.
        متنِ تکراریِ واقعی در دو حبابِ جدا = بدونِ همپوشانی → دست‌نخورده.
        یتیمِ واقعی (خطِ نو با متنِ تازه، بیرونِ مستطیلِ والد) =
        بدونِ همپوشانی → دست‌نخورده (سناریوی «OUTER GOD…»).
        """
        if not regions or len(regions) < 2:
            return regions

        def _norm(t) -> str:
            try:
                return re.sub(r"[\W_]+", "", str(t or "").lower())
            except Exception:
                return str(t or "").lower()

        def _sim(a: str, b: str) -> float:
            """شباهتِ دو متنِ نرمال — ۱٫۰ = یکی."""
            if a == b:
                return 1.0
            try:
                import difflib as _dl
                return _dl.SequenceMatcher(None, a, b).ratio()
            except Exception:
                return 0.0

        def _xyxy(r):
            try:
                x, y, w, h = [float(v) for v in r.rect]
                return (x, y, x + w, y + h)
            except Exception:
                return (0.0, 0.0, 0.0, 0.0)

        def _inter(a, b):
            ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
            iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
            return max(0.0, ix) * max(0.0, iy)

        def _area(a):
            return max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])

        infos = []
        for r in regions:
            try:
                n = _norm(getattr(r, "source_text", ""))
            except Exception:
                n = ""
            if not n:
                continue  # بی‌متن (ocr_empty و…) هرگز اینجا حذف نمیشود
            try:
                npol = len(getattr(r, "ocr_polys", None) or [])
            except Exception:
                npol = 0
            infos.append((r, n, _xyxy(r), _area(_xyxy(r)), npol))
        if len(infos) < 2:
            return regions

        drop_ids: set = set()
        n_eq = n_sub = 0
        for i in range(len(infos)):
            ra, na, ba, aa, pa = infos[i]
            if id(ra) in drop_ids:
                continue
            for j in range(i + 1, len(infos)):
                rb, nb, bb, ab, pb = infos[j]
                if id(rb) in drop_ids:
                    continue
                if getattr(rb, "kind", "") != getattr(ra, "kind", ""):
                    continue
# خواهرانِ پنجرهٔ سیستمِ هم‌والد هرگز «تکرارِ
# دوباره‌رندر» نیستند: خطوطِ split از «یک» پاسِ OCRِ والد
# در ردیفهایِ مجزا ساخته شدهاند (متنهایِ متفاوتِ فیزیکی).
# قربانیِ واقعی (فصلِ ۸۸، لاگِ 8e7dd2bc): «THE EAST WING
# AND» ≈ «THE WEST WING.» با شباهتِ فازیِ ۰٫۷۷ (آستانهٔ
# ۰٫۶۲) + ۱۰px همپوشانیِ عمودی → خطِ چهارمِ حباب، به‌عنوانِ
# «هممتن» حذف شد و متن رویِ خروجی ماند. خواهرِ هم‌والد
# (cover_rect یکسان + sys_split) از هر دو شاخهٔ «یکسان» و
# «بخشی» مستثناست؛ دوباره‌رندرِ واقعی = دو باکسِ detector
# (cover_rect متفاوت) — همان محافظتِ ۲۲۵ سرِ جایش میماند.
                try:
                    if getattr(ra, "sys_split", False) \
                            and getattr(rb, "sys_split", False) \
                            and getattr(ra, "cover_rect", None) is not None \
                            and getattr(ra, "cover_rect", None) \
                            == getattr(rb, "cover_rect", None):
                        continue
                except Exception:
                    pass
                inter = _inter(ba, bb)
                if inter <= 0.0:
                    continue
                amin = min(aa, ab) or 1.0
                ov_min = inter / amin
# احتوای bb در ba و برعکس
                cont_ba = inter / (ab or 1.0)
                cont_ab = inter / (aa or 1.0)
                _kill = None
# «یکسان» = متنِ برابر یا جابهجاییِ واژهها (چندمجموعهٔ
# نویسهها)؛ «شبیه» = بازخوانیِ کج‌وکولهٔ OCR (≥۰٫۶۲)
                _same_txt = (na == nb) or (
                    len(na) >= 6 and len(nb) >= 6
                    and sorted(na) == sorted(nb))
                if not _same_txt and len(na) >= 6 and len(nb) >= 6:
                    _same_txt = _sim(na, nb) >= 0.62
                if _same_txt:
                    if ov_min >= 0.18 or max(cont_ba, cont_ab) >= 0.45:
# بزرگتر/پرخطتر میماند؛ کوچکتر حذف میشود
                        _kill = ra if (pa, aa) <= (pb, ab) else rb
                        n_eq += 1
                elif nb in na and cont_ba >= 0.60:
                    _kill = rb
                    n_sub += 1
                elif na in nb and cont_ab >= 0.60:
                    _kill = ra
                    n_sub += 1
                if _kill is not None:
                    drop_ids.add(id(_kill))
        if not drop_ids:
            return regions
        out = [r for r in regions if id(r) not in drop_ids]
        try:
            print(f"    [*] {len(drop_ids)} ناحیهٔ هممتنِ همپوشان حذف شد "
                  f"(ضدِ رندرِ دوباره — {n_eq} یکسان / {n_sub} بخشی)",
                  flush=True)
        except Exception:
            pass
        return out

    def _rescue_orphan_lines(self, image: np.ndarray,
                             regions: List["TextRegion"]) -> List["TextRegion"]:
        """ — نجاتِ خطِ یتیمِ همسایهٔ ناحیهٔ متن.

        ریشه (لاگِ واقعیِ strip_001ِ بچِ img4+4e2e77): پنجرهٔ سیستمِ
        «[CLEAR OBJECTIVE: SLAY THE / OUTER GOD WITHIN 7 YEARS.]» دو خط
        داشت؛ detector فقط باکسِ خطِ اول را داد (پایینِ آن، نزدیکِ لبهٔ
        نوار) → خطِ دوم نه استخراج شد (متنش به خطِ اولِ کج‌وکوله چسبید)،
        نه پاکسازی (بیرونِ هر ماسکی بود) → حروفِ سفیدِ کامل در خروجی
        ماند («لگهٔ متنِ قبلی»). اینجا برایِ هر ناحیهٔ متنی، نوارِ
        بالای/پایینِ مستطیلش (به پهنایِ همان ناحیه) برایِ «جوهرِ
        خط‌مانندِ بی‌صاحب» اسکن میشود؛ اگر OCR رویِ آن متنِ لاتینِ
        معتبر خواند → ناحیهٔ جدید ساخته میشود (ترجمه + پاکسازی).
        MANGA_ORPHAN_RESCUE=0 برایِ خاموشیِ دستی."""
        if os.environ.get("MANGA_ORPHAN_RESCUE", "1") == "0":
            return regions
        try:
            h_img, w_img = image.shape[:2]
        except Exception:
            return regions
        if self.ocr is None:
            return regions
        parents = [r for r in regions
                   if (getattr(r, "source_text", "") or "").strip()
                   and getattr(r, "kind", "") == "dialogue"]
        if not parents:
            return regions
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        except Exception:
            return regions
# باکسهای اشغالشده (با حاشیه) — خطِ یتیم باید بیرونِ همه باشد
        covered = []
        for r in regions:
            try:
                rx, ry, rw_, rh_ = [int(v) for v in r.rect]
                covered.append((rx - 12, ry - 12, rx + rw_ + 12, ry + rh_ + 12))
            except Exception:
                continue
        _next_id = 900000
        try:
            _next_id = 900000 + max(
                (int(getattr(r, "id", 0) or 0) for r in regions), default=0)
        except Exception:
            pass
        rescued: List[TextRegion] = []
        _seen_bands: List[Tuple[int, int, int, int]] = []
# بودجهٔ پاسهایِ OCRِ یتیم: حداکثرِ ۲ پاس به‌ازایِ هر
# ناحیهٔ والد (پروفایلِ img6: ۳۵ پاسِ تقریباً بی‌نتیجه). وقتیِ هنر
# از همهٔ گاردها رد شود، این سقف جلویِ «دومین استخراجِ کاملِ صفحه»
# را میگیرد؛ خطِ یتیمِ واقعی (≥۶ حرفِ خوانا) تقریباً همیشه در
# پاسهایِ اولِ همان ناحیه پیدا میشود.
        _orphan_budget = max(12, 2 * len(parents))
        for r in parents:
            try:
                x, y, rw_, rh_ = [int(v) for v in r.rect]
            except Exception:
                continue
# بلندیِ خط از پالیهای خودِ ناحیه (مستطیلِ چندخطی نه)
            _lhs = []
            for _p in (getattr(r, "ocr_polys", None) or []):
                try:
                    _pp = np.asarray(_p, dtype=np.float32).reshape(-1, 2)
                    _lhs.append(float(_pp[:, 1].max() - _pp[:, 1].min()))
                except Exception:
                    continue
            lh = float(np.median(_lhs)) if _lhs else float(rh_)
            lh = float(np.clip(lh, 12.0, 140.0))
# شروعِ نوار چسبیده به لبهٔ ناحیه: خطِ ادامه‌دار
# ممکن است فقط ۲۰-۳۰px بیرونِ مستطیل باشد (پنجرهٔ [CLEAR
# OBJECTIVE…]: خطِ دوم تا ۳۳۴۴ و مستطیل تا ۳۳۱۸) — شیارِ بزرگ
# (⅓ خط) از رویش میپرید. ۱۲٪ خط + ۴px کافی است؛ ردِ «پوشیده»
# با محتوای ≥۷۰٪ داخلِ باکس انجام میشود نه هر همپوشانی.
            gap = max(4, int(round(lh * 0.12)))
            reach = int(round(lh * 2.2))
            for _b0, _b1 in ((y + rh_ + gap, y + rh_ + gap + reach),
                             (y - gap - reach, y - gap)):
                _b0 = max(0, int(_b0))
                _b1 = min(h_img, int(_b1))
                if _b1 - _b0 < int(lh * 0.6):
                    continue
                _x0 = max(0, x - int(rw_ * 0.25))
                _x1 = min(w_img, x + rw_ + int(rw_ * 0.25))
                if _x1 - _x0 < 40:
                    continue
                band = gray[_b0:_b1, _x0:_x1]
                if band.size == 0:
                    continue
                med = float(np.median(band))
                if med >= 128.0:
                    ink = (band < med - 60.0)
                else:
                    ink = (band > med + 60.0)
                _dens = float(ink.mean())
                if _dens < 0.004 or _dens > 0.55:
                    continue
# تفکیکِ «ردیفهایِ خط‌مانند»: نوارِ جستجو
# کلِ پنجره/لبه‌ها را دارد؛ bboxِ خامِ جوهر کلِ نوار را
# میگیرد و OCR رویِ هنر میافتد. ردیفها به اجراهایِ
# پیوستهٔ جوهرِدار شکسته میشوند؛ هر اجرا = یک خطِ
# کاندید (بلندیِ ۸..۲.۵×خط، نه خطِ نازکِ کادر/لبهٔ
# تمام-عرض، نه میلهٔ توپُر).
                _rows = ink.sum(axis=1).astype(np.float32)
                _row_thr = max(12.0, 0.08 * (_x1 - _x0))
                _runs: List[Tuple[int, int]] = []
                _in_run = False
                _rs = 0
                for _i in range(len(_rows)):
                    if _rows[_i] >= _row_thr:
                        if not _in_run:
                            _rs = _i
                            _in_run = True
                    else:
                        if _in_run:
                            _runs.append((_rs, _i))
                            _in_run = False
                if _in_run:
                    _runs.append((_rs, len(_rows)))
                for (_r0, _r1) in _runs:
                    _rhh = _r1 - _r0
                    if _rhh < 8 or _rhh > max(30, int(lh * 2.5)):
                        continue
# پسکشِ هیسترزیسی: آستانهٔ هستهٔ خط فقط
# تنهٔ پرپیکسلِ حروف را میگیرد؛ دُم/سرِ نازکِ خط
# (نصفِ پایینیِ حروفِ رویِ نوارِ تیرهٔ پایینِ پنجره)
# زیرِ آستانه ماند و برشِ OCR نصفه میشد («P»/«T»).
# مرزهای اجرا تا جایی که ردیف هنوز ~۳۰٪ آستانه را
# دارد کشیده میشوند (سقف: نصفِ بلندیِ خط هر طرف).
                    _soft_thr = _row_thr * 0.30
                    _ext_max = max(4, int(lh * 0.5))
                    _e0 = 0
                    while (_r0 - _e0 - 1 >= 0 and _e0 < _ext_max
                           and _rows[_r0 - _e0 - 1] >= _soft_thr):
                        _e0 += 1
                    _e1 = 0
                    while (_r1 + _e1 < len(_rows) and _e1 < _ext_max
                           and _rows[_r1 + _e1] >= _soft_thr):
                        _e1 += 1
                    _r0 -= _e0
                    _r1 += _e1
                    _rhh = _r1 - _r0
                    if _rhh > max(30, int(lh * 2.8)):
                        continue
                    _sub = ink[_r0:_r1, :]
                    if float(_sub.mean()) > 0.55:
                        continue
# گیتِ «حرف‌مانندی» پیش از OCR: پروفایلِ
# img6 نشان داد پاسهایِ یتیم گرانترین بخشِ استخراج
# بعد از نردبان‌اند (~۳۵ فراخوانیِ OCR که تقریباً همه‌اش
# هنر/کادر/بافت بود و ۰ خط داد — حسِ «دوبار استخراج
# میزنه»). متنِ واقعی ≥۵ مؤلفهٔ پیوستهٔ حرف‌اندازه دارد
# (هر حرف ~۱ مؤلفه)؛ خطِ کادر/هنر ۱-۲ مؤلفهٔ عظیم یا
# خرده‌نویزهایِ ریز دارد. cv2.connectedComponents ~۱ms
# است در برابرِ ~۱.۳s هر پاسِ OCR.
                    try:
                        _nlab, _labs, _stat, _cent = \
                            cv2.connectedComponentsWithStats(
                                _sub.astype(np.uint8), connectivity=8)
                        _letters = 0
                        _bots: List[int] = []
                        for _li in range(1, _nlab):
                            _sx, _sy, _sw, _sh, _sa = \
                                _stat[_li]
                            if _sa < 8:
                                continue
                            if not (3 <= _sh <= max(12.0, lh * 1.6)):
                                continue
                            if _sw <= max(14.0, lh * 1.2):
                                _letters += 1
                                _bots.append(int(_sy + _sh))
                            elif _sw <= max(30.0, lh * 3.5):
                                _letters += 2  # حروفِ چسبیده (فونتِ ضخیم)
                                _bots.append(int(_sy + _sh))
                        if _letters < 5:
                            continue
# هم‌ترازیِ بیس‌لاین: حروفِ یک خطِ واقعی
# پایینِ تقریباً یکسان دارند (واریانسِ کوچک)؛ لکهها/
# بافتهایِ هنریِ حرف‌اندازه به‌طورِ تصادفی پخش‌اند.
                        if len(_bots) >= 5:
                            _bstd = float(np.std(_bots))
                            if _bstd > max(6.0, 0.45 * lh):
                                continue
                    except Exception:
                        pass
                    try:
                        _ys, _xs = np.nonzero(_sub)
                    except Exception:
                        continue
                    _ix0, _ix1 = int(_xs.min()), int(_xs.max())
                    if (_ix1 - _ix0) < 30:
                        continue
                    gx0 = max(0, _x0 + _ix0)
                    gy0 = max(0, _b0 + _r0 - 3)
                    gx1 = min(w_img, _x0 + _ix1 + 1)
                    gy1 = min(h_img, _b0 + _r1 + 3)
                    if gx1 - gx0 < 30 or gy1 - gy0 < 8:
                        continue
# گاردِ «لایهٔ خطِ همسایه»: لبهٔ بالایی/
# پایینیِ خطِ «موجودِ» بعدی که مستطیلش دیرتر شروع
# میشود، در نوارِ جستجو به‌صورتِ لایهٔ نازک ظاهر میشود
# (لاگِ واقعی: «YAA»/«WAND»/«¿Thur» رویِ strip_007) —
# خطِ واقعیِ بی‌صاحب بلندیِ کاملِ خط را دارد (≥۴۵٪
# بلندیِ خطِ والد) و حروفِ کافی (≥۶ حرفِ لاتین). تنها
# استثنا: اجرایِ چسبیده به «لبهٔ» نوار (بریدهٔ مرز) —
# دُمِ خطی که به ناحیهٔ والد ادامه دارد (نمونهٔ واقعی:
# دُمِ ۲۰pxیِ «OUTER GOD WITHIN 7 YEARS.]» در بندِ
# ۳۳۲۹-۳۳۴۶) به‌طورِ طبیعی کوتاه است؛ برایش فقط
# حداقلِ ۱۲px کافی است (فیلترِ حروف جلویِ لایههایِ
# ناخواسته را میگیرد).
                    _clipped_edge = (_r0 <= 0 or _r1 >= len(_rows))
                    if not _clipped_edge \
                            and (gy1 - gy0) < max(12, int(round(lh * 0.45))):
                        continue
                    if (gy1 - gy0) < 12:
                        continue
                    _ga = float(max(1, (gx1 - gx0) * (gy1 - gy0)))
                    if any(not (gx1 < c[0] or gx0 > c[2]
                                or gy1 < c[1] or gy0 > c[3])
                           and (min(gx1, c[2]) - max(gx0, c[0]))
                               * (min(gy1, c[3]) - max(gy0, c[1]))
                               >= 0.70 * _ga
                           for c in covered):
                        continue  # تقریباً کامل داخلِ ناحیهٔ موجود
                    if any(not (gx1 < s[0] or gx0 > s[2]
                                or gy1 < s[1] or gy0 > s[3])
                           and (min(gx1, s[2]) - max(gx0, s[0]))
                               * (min(gy1, s[3]) - max(gy0, s[1]))
                               >= 0.70 * _ga
                           for s in _seen_bands):
                        continue
                    _seen_bands.append((gx0, gy0, gx1, gy1))
# گیتِ پیش از OCR — «جوهرِ دارایِ صاحب»:
# بازخوانیِ متنِ موجود، پرهزینهترین بخشِ استخراج بود
# (پروفایلِ 4e2e77: ۲۶ فراخوانیِ OCRِ یتیم = ۳۲ثانیه
# که اکثراً بعدش با گاردِ ۲۲۵ رد میشدند — «انگار
# دوبار اون متن میخونه» درست بود). سنجشِ پیش از OCR:
# چند درصدِ «پیکسلهایِ جوهرِ» این باند داخلِ
# چندضلعیهایِ OCRِ نواحیِ موجود است؟ ≥۵۵٪ → متنِ
# دارایِ صاحب → بدونِ OCR رد میشود (عینِ گاردِ ۲۲۵
# فقط این‌بار روی جوهرِ واقعی نه جعبهٔ خامِ هنر-آلود).
                    try:
                        _inkys, _inkxs = np.nonzero(
                            ink[_r0:_r1, :])
                        if _inkys.size >= 12:
                            _gx = _inkxs.astype(np.int32) + _x0
                            _gy = _inkys.astype(np.int32) + _b0
                            _inany = np.zeros(
                                _gx.shape, bool)
                            for _rp in regions:
                                for _rpoly in (
                                        getattr(_rp, "ocr_polys", None)
                                        or []):
                                    try:
                                        _pp3 = np.asarray(
                                            _rpoly,
                                            np.float32).reshape(-1, 2)
                                        _bx226a = int(_pp3[:, 0].min())
                                        _by226a = int(_pp3[:, 1].min())
                                        _bx226b = int(
                                            _pp3[:, 0].max()) + 1
                                        _by226b = int(
                                            _pp3[:, 1].max()) + 1
                                        _selb = (
                                            (_gx >= _bx226a)
                                            & (_gx < _bx226b)
                                            & (_gy >= _by226a)
                                            & (_gy < _by226b))
                                        if not _selb.any():
                                            continue
                                        _bw = max(
                                            1, _bx226b - _bx226a)
                                        _bh = max(
                                            1, _by226b - _by226a)
                                        _pm = np.zeros(
                                            (_bh, _bw), np.uint8)
                                        cv2.fillPoly(
                                            _pm,
                                            [np.rint(
                                                _pp3
                                                - [_bx226a,
                                                   _by226a]).astype(
                                                np.int32)], 255)
                                        _inany[_selb] |= (
                                            _pm[
                                                _gy[_selb]
                                                - _by226a,
                                                _gx[_selb]
                                                - _bx226a] > 0)
                                    except Exception:
                                        continue
                                if float(
                                        _inany.mean()) >= 0.55:
                                    break
                            if float(_inany.mean()) >= 0.55:
                                continue
                    except Exception:
                        pass
                    if _orphan_budget <= 0:
                        continue
                    try:
                        _oc = self._ocr_crop(
                            image, (max(0, gx0 - 6), max(0, gy0 - 6),
                                    min(w_img, gx1 + 6), min(h_img, gy1 + 6)))
                        _orphan_budget -= 1
                        _txt = (_oc[0] or "").strip()
                        _polys = list(_oc[1] or []) if len(_oc) > 1 else []
                    except Exception:
                        _txt, _polys = "", []
                    _lt = sum(1 for _c in _txt
                              if _c.isascii() and _c.isalpha())
                    if not _txt or _lt < 6 \
                            or _lt * 2 < len(_txt.replace(" ", "")):
                        continue
# پسگیرِ «بازخوانیِ متنِ پوشیدهشده»:
# جعبهٔ خامِ جوهرِ نوار با هنرِ اطراف پهن میشود و
# گاردِ ۷۰٪یِ بالای سر ردش میکند (لاگِ واقعیِ img6:
# «attraction A» و «atfrach here.» — بازخوانیِ
# کج‌وکولهٔ «You're the real attraction here.» از
# نوارِ زیرِ حبابِ همسایه؛ ناحیهٔ ۶ با پسگیرِ جوهر
# +1614px رویِ دُمِ حباب چسبید = خطِ حباب پاک شد).
# سنجشِ درست = چندضلعیهایِ خودِ OCR (جعبهٔ واقعیِ
# حروف): اگر ≥۶۰٪ حروف داخلِ ناحیههایِ موجودند
# این «همان متنِ دارایِ صاحب» است نه خطِ یتیم →
# رد. یتیمِ واقعی (سناریوی «OUTER GOD…» — خطِ
# دومی که detector ندید) بیرونِ همهٔ ناحیههاست
# و زنده میماند.
                    try:
                        _ta = 0.0
                        _ca = 0.0
                        for _p2 in _polys:
                            try:
                                _pp2 = np.asarray(
                                    _p2, np.float32).reshape(-1, 2)
                                _pbx0 = float(_pp2[:, 0].min())
                                _pby0 = float(_pp2[:, 1].min())
                                _pbx1 = float(_pp2[:, 0].max())
                                _pby1 = float(_pp2[:, 1].max())
                                _pba = max(1.0, (_pbx1 - _pbx0)
                                           * (_pby1 - _pby0))
                                _pin = 0.0
                                for _c in covered:
                                    _ix = max(
                                        0.0, min(_pbx1, _c[2])
                                        - max(_pbx0, _c[0]))
                                    _iy = max(
                                        0.0, min(_pby1, _c[3])
                                        - max(_pby0, _c[1]))
                                    _pin = max(_pin, (_ix * _iy)
                                               / _pba)
                                _ta += _pba
                                _ca += _pba * min(1.0, _pin)
                            except Exception:
                                continue
                        if _ta > 0.0 and \
                                _ca / _ta >= 0.55:
                            if self.debug:
                                print(f"    [🔍225] یتیمِ بازخوانیِ "
                                      f"متنِ پوشیدهشده رد شد: "
                                      f"{_txt[:44]!r}", flush=True)
                            continue
                    except Exception:
                        pass
                    _boxes = []
                    for _p in _polys:
                        try:
                            _pp = np.asarray(_p, dtype=np.float32).reshape(-1, 2)
                            _boxes.append(_pp.astype(np.int32))
                        except Exception:
                            continue
                    nr = TextRegion(
                        id=_next_id, boxes=_boxes or [np.array(
                            [[gx0, gy0], [gx1, gy0], [gx1, gy1], [gx0, gy1]],
                            dtype=np.int32)],
                        source_text=_txt,
                        rect=(gx0, gy0, gx1 - gx0, gy1 - gy0),
                        kind="dialogue",
                        bubble_style=str(getattr(r, "bubble_style", "normal")
                                         or "normal"),
                        det_class=str(getattr(r, "det_class", "") or ""),
                        ocr_polys=_polys)
                    _next_id += 1
                    rescued.append(nr)
                    covered.append((gx0 - 12, gy0 - 12, gx1 + 12, gy1 + 12))
                    if self.debug:
                        print(f"    [+] نجاتِ خطِ یتیم زیر/بالای "
                              f"({x},{y},{x + rw_},{y + rh_}): {_txt[:56]!r}")
        if rescued:
            regions = list(regions) + rescued
            print(f"    [+] {len(rescued)} خطِ یتیم (همسایهٔ نواحیِ متن) "
                  f"نجات یافت → ترجمه و پاکسازی میشوند")
        return regions

    def _verify_angle_signs(self, image: np.ndarray,
                            regions: List["TextRegion"]) -> None:
        for r in regions:
            ang = float(getattr(r, "angle", 0.0) or 0.0)
            if abs(ang) > 45.0:
                r.angle = 0.0
                continue
            if abs(ang) < 6.0:
                _is_vert = self._polys_vertical(getattr(r, "ocr_polys", None))
                try:
                    _px = getattr(r, "ocr_polys", None) or []
                    _vx1 = _vy1 = None
                    if _px and not _is_vert:
                        try:
                            _vp = np.concatenate(
                                [np.asarray(p).reshape(-1, 2) for p in _px])
                            _vx1, _vy1 = float(_vp[:, 0].min()), float(_vp[:, 1].min())
                            _vx2, _vy2 = float(_vp[:, 0].max()), float(_vp[:, 1].max())
                        except Exception:
                            _vx1 = _vy1 = None
                    if _vx1 is None:
                        _vx, _vy, _vw, _vh = [int(v) for v in r.rect]
                        _vx1, _vy1 = float(_vx), float(_vy)
                        _vx2, _vy2 = float(_vx + _vw), float(_vy + _vh)
                    _uy1 = max(0, int(_vy1))
                    _ux1 = max(0, int(_vx1))
                    _ux2 = min(int(image.shape[1]), int(_vx2) + 1)
                    _uy2 = min(int(image.shape[0]), int(_vy2) + 1)
                    if _ux2 - _ux1 >= 40 and _uy2 - _uy1 >= 14:
                        _ai = MangaTranslator._ink_slant_angle(
                            image[_uy1:_uy2, _ux1:_ux2])
                        if abs(_ai) >= (7.0 if _is_vert else 6.0):
                            print(f"    [!] بازیابی کجی [{r.id}]: {ang:+.1f}° → "
                                  f"{_ai:+.1f}° (جوهر؛ موتور از دست داده بود)")
                            r.angle = _ai
                except Exception:
                    pass
                continue
            try:
                x1 = y1 = None
                polys = list(getattr(r, "ocr_polys", None) or [])
                if polys:
                    try:
                        _pa = np.concatenate(
                            [np.asarray(p).reshape(-1, 2) for p in polys])
                        x1, y1 = float(_pa[:, 0].min()), float(_pa[:, 1].min())
                        x2, y2 = float(_pa[:, 0].max()), float(_pa[:, 1].max())
                    except Exception:
                        x1 = y1 = None
                if x1 is None:
                    x, y, w_, h_ = [int(v) for v in r.rect]
                    x1, y1 = max(0, x), max(0, y)
                    x2 = min(int(image.shape[1]), x + max(8, w_))
                    y2 = min(int(image.shape[0]), y + max(8, h_))
                x1, y1 = max(0, int(x1)), max(0, int(y1))
                x2 = min(int(image.shape[1]), int(x2) + 1)
                y2 = min(int(image.shape[0]), int(y2) + 1)
                if x2 - x1 < 40 or y2 - y1 < 14:
                    continue
                _a_ink, _a_ok = MangaTranslator._ink_slant_measure(
                    image[y1:y2, x1:x2])
                if os.environ.get("MANGA_DBG_VERIFY"):
                    print(f"    [dbg-verify] {r.id} ang={ang:+.1f} "
                          f"bbox=({x1},{y1},{x2},{y2}) ok={_a_ok} a={_a_ink:+.1f}")
                if not _a_ok:
                    continue
                if abs(_a_ink) >= 6.0 and (_a_ink > 0.0) != (ang > 0.0):
# عاقل‌نگه‌داشتِ مقدار: اگر جوهر با پالی فقط
# «علامت» را عوض کند و مقدارشان نزدیک باشد، جایگزین
# اما پرشِ فاحش (>15°) یعنی یکی‌شان خطا کرده (حروفِ
# استایل‌دار) → امن‌ترین: رندرِ مسطح. ARTiCLE-2 واقعیِ
# مسطح بود ولی ‎-7°→+39.8° رندر شد (باگِ «برعکس»)
                    if abs(abs(_a_ink) - abs(ang)) > 15.0:
                        print(f"    [!] وتوی کجیِ ناسازگار [{r.id}]: "
                              f"{ang:+.1f}° ← جوهر {_a_ink:+.1f}° "
                              "(پرشِ فاحش) → 0.0°")
                        r.angle = 0.0
                        r.angle_flat_veto = True
                    else:
                        print(f"    [!] اصلاح علامتِ چرخش [{r.id}]: {ang:+.1f}° → "
                              f"{_a_ink:+.1f}° (راستی‌آزمایی جوهر)")
                        r.angle = _a_ink
                elif abs(_a_ink) < 6.0:
# جوهر می‌گوید «مسطح» ولی زاویهٔ پالی‌ها
# کجِ ±۶..۴۵° است (حروفِ استایل‌دارِ تیترها زاویهٔ
# کاذب می‌سازند؛ BLUE MOON -15° در حالی‌که واقعی ~0°)
# اما اول خودِ زاویهٔ ادعایی آزموده میشود:
# اگر ردیفهایِ جوهر را واقعاً رویِ هم میاندازد (≥۱٫۱۰×)
# کجی واقعی است و وتو نمیشود (img3: ‎-۶٫۷°/-۱۳٫۲°
# واقعی بودند و به‌غلط صفر میشدند — «بعد چرخش همچین
# بعضی متن ها درست نمیچرخه»).
                    _sup = MangaTranslator._ink_slant_support(
                        image[y1:y2, x1:x2], ang)
                    if _sup is not None and _sup >= 1.10:
                        if os.environ.get("MANGA_DBG_VERIFY"):
                            print(f"    [dbg-verify] {r.id} ang={ang:+.1f}° "
                                  f"تأییدِ جوهر (پشتیبانی={_sup:.2f}) — "
                                  f"وتو نشد")
                        continue
                    print(f"    [!] حذف کجیِ کاذب [{r.id}]: {ang:+.1f}° → 0.0° "
                          f"(جوهرِ واقعیِ خط مسطح است)")
                    r.angle = 0.0
# رندر حقِ بازنویسی از پالی‌ها را ندارد
                    r.angle_flat_veto = True
            except Exception:
                continue

    def _discover_sfx_regions(self, image: np.ndarray,
                              regions: List["TextRegion"]) -> List["TextRegion"]:
        """ — افکتِ صوتی/متنِ استایل‌دارِ بیرونِ حباب (HAA، SFX
        کره‌ای، پلاکِ اسم و…) با فیلترهایِ شل‌شده پیدا می‌شود تا در
        «کپیِ اولِ تهاجمی» کامل پاک شود. فقط وقتی MANGA_CLEAN_SFX=1 یا
        --clean-sfx."""
        try:
            out = self._discover_free_text_regions(image, regions,
                                                   relaxed=True)
        except Exception:
            return []
# تکه‌های یک SFX (حروفِ دور از هم مثل HAA..) را به هم بچسبان
        return self._merge_sfx_fragments(image, out)

    def _merge_sfx_fragments(self, image: np.ndarray,
                             regions: List["TextRegion"]) -> List["TextRegion"]:
        """ — ناحیه‌های sfxِ نزدیکِ هم (تکه‌های یک افکت) را ادغام
        می‌کند و rect را تا جوهرِ نزدیک گسترش می‌دهد تا ماسکِ توپر کلِ
        کلمه (مثل HAA..) را بپوشاند."""
        if not regions:
            return regions
        try:
            h, w = image.shape[:2]
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            med = cv2.medianBlur(gray, 31)
            ink = (np.abs(gray.astype(np.int16) - med.astype(np.int16))
                   > 52).astype(np.uint8) * 255
        except Exception:
            ink = None
        try:
            rs = sorted(regions, key=lambda r: (r.rect[1], r.rect[0]))
            merged: List["TextRegion"] = []
            for r in rs:
                placed = False
                try:
                    x, y, w_, h_ = [int(v) for v in r.rect]
                except Exception:
                    merged.append(r)
                    continue
                for m in merged:
                    try:
                        mx, my, mw, mh = [int(v) for v in m.rect]
                    except Exception:
                        continue
                    if (x - 70 < mx + mw and mx - 70 < x + w_
                            and y - 70 < my + mh and my - 70 < y + h_):
                        nx0, ny0 = min(mx, x), min(my, y)
                        nx1, ny1 = max(mx + mw, x + w_), max(my + mh, y + h_)
                        m.rect = (nx0, ny0, nx1 - nx0, ny1 - ny0)
                        try:
                            m.boxes = list(m.boxes or []) + list(r.boxes or [])
                            m.ocr_polys = (list(m.ocr_polys or [])
                                           + list(r.ocr_polys or []))
                        except Exception:
                            pass
                        try:
                            _t1 = (m.source_text or "").strip()
                            _t2 = (r.source_text or "").strip()
                            if _t2 and _t2 not in _t1:
                                m.source_text = (_t1 + " " + _t2).strip()
                        except Exception:
                            pass
                        placed = True
                        break
                if not placed:
                    merged.append(r)
            if ink is not None:
                for m in merged:
                    try:
                        mx, my, mw, mh = [int(v) for v in m.rect]
# گسترشِ تکراری: تا ۳ بار، هر بار ۸۰px باز و به
# مرزِ جوهر بچسبان (حالتِ تهاجمیِ SFX — سقفِ رشد
# برداشته شد؛ کاربر گفته «بیشتر پاک شه» اشکال ندارد)
                        for _ in range(3):
                            ex0, ey0 = max(0, mx - 80), max(0, my - 80)
                            ex1 = min(w, mx + mw + 80)
                            ey1 = min(h, my + mh + 80)
                            sub = ink[ey0:ey1, ex0:ex1]
                            ys, xs = np.nonzero(sub)
                            if len(xs) < 20:
                                break
                            nx0, ny0 = ex0 + int(xs.min()), ey0 + int(ys.min())
                            nx1 = ex0 + int(xs.max()) + 1
                            ny1 = ey0 + int(ys.max()) + 1
                            if (nx0 == mx and ny0 == my
                                    and nx1 == mx + mw and ny1 == my + mh):
                                break
                            mx, my, mw, mh = nx0, ny0, nx1 - nx0, ny1 - ny0
                        m.rect = (mx, my, mw, mh)
                    except Exception:
                        pass
            return merged
        except Exception:
            return regions

    def _dbg_collect_det_quads(self, image: np.ndarray,
                                   regions: List[TextRegion]) -> None:
        """ — جعبههایِ خامِ detِ OCR برایِ دیباگِ آبیِ صفحه.

        برایِ هر کراپِ detector (حباب)، یک پاسِ فقط-det (بدونِ rec، موتورِ
        جدایِ 30_ocr.det_only) زده میشود؛ جعبهها به مختصاتِ صفحه میروند
        و در self._dbg_det_quads_252 برایِ رسمِ آبی (90_render) می‌نشینند.

        تفسیر (لاگِ [252] + تصویر):
          • جعبهٔ آبی هست ولی ناحیه/متن ندارد → det دید، rec/فیلتر حذف کرد
          • جعبهٔ آبی هم ندارد → det اصلاً آن خط را ندید
        فقط با self.debug — هیچ اثری روی استخراجِ اصلی ندارد (کراپ/نردبان
        دستنخورده؛ پاسِ detِ جدا رویِ همان RECTهایِ detector)."""

        self._dbg_det_quads = []
        _fn = getattr(self.ocr, "det_only", None)
        if not callable(_fn):
            return
        _bubbles = list(getattr(self, "_page_bubble_boxes", None) or [])
        if not _bubbles:
            return
        try:
            _h, _w = image.shape[:2]
        except Exception:
            return
        _quads: List[np.ndarray] = []
        _t = time.time()
        for _b in _bubbles:
            try:
                _bx1, _by1, _bx2, _by2 = [int(v) for v in _b[:4]]
                _pad = 8
                _x1 = max(0, _bx1 - _pad)
                _y1 = max(0, _by1 - _pad)
                _x2 = min(_w, _bx2 + _pad)
                _y2 = min(_h, _by2 + _pad)
                if _x2 - _x1 < 8 or _y2 - _y1 < 8:
                    continue
                _crop = image[_y1:_y2, _x1:_x2]
                if _crop is None or _crop.size == 0:
                    continue
# همان بُستِ نردبانِ _ocr_crop برایِ متنِ ریز (کوچک = بُست)
                _m = max(_crop.shape[:2])
                if _m < 200:
                    _sc = 2.4
                elif _m < 360:
                    _sc = 1.8
                elif _m < 600:
                    _sc = 1.35
                else:
                    _sc = 1.0
                _passes = [(_crop, 1.0)]
                if _sc > 1.01:
                    _passes.append(
                        (cv2.resize(_crop, None, fx=_sc, fy=_sc,
                                    interpolation=cv2.INTER_CUBIC), _sc))
                for _cimg, _cs in _passes:
                    for _q in (_fn(_cimg) or []):
                        try:
                            _qf = np.asarray(
                                _q, dtype=np.float32).reshape(-1, 2).copy()
                            if _cs > 1.01:
                                _qf = _qf / _cs
                            _qf[:, 0] += _x1
                            _qf[:, 1] += _y1
                            _quads.append(_qf)
                        except Exception:
                            continue
            except Exception:
                continue
# دداپ — پاسهایِ ۱×/بُست همان خط را دوبار میآورند (همپوشانیِ
# ≥۰٫۶ → یکی میماند)
        try:
            _keep: List[np.ndarray] = []
            _bb = []
            for _q in _quads:
                _bx1_ = float(np.min(_q[:, 0])); _by1_ = float(np.min(_q[:, 1]))
                _bx2_ = float(np.max(_q[:, 0])); _by2_ = float(np.max(_q[:, 1]))
                _dup = False
                for _kb in _bb:
                    _ix = max(0.0, min(_bx2_, _kb[2]) - max(_bx1_, _kb[0]))
                    _iy = max(0.0, min(_by2_, _kb[3]) - max(_by1_, _kb[1]))
                    _inter = _ix * _iy
                    if _inter <= 0:
                        continue
                    _aq = max(1e-6, (_bx2_ - _bx1_) * (_by2_ - _by1_))
                    _bq = max(1e-6, (_kb[2] - _kb[0]) * (_kb[3] - _kb[1]))
                    if _inter / min(_aq, _bq) >= 0.6:
                        _dup = True
                        break
                if not _dup:
                    _keep.append(_q)
                    _bb.append((_bx1_, _by1_, _bx2_, _by2_))
            _quads = _keep
        except Exception:
            pass
        self._dbg_det_quads = _quads
# لاگِ تشخیصی — پاسخِ مستقیمِ «det دید یا rec نگرفت؟»: جعبهٔ آبی
# که هیچ ناحیهٔ نهایی (rect یا پالیِ OCR) نپوشانده = دیدهشده توسطِ
# det ولی استخراج نشده
        try:
            _cov = []
            for _r in (regions or []):
                try:
                    _rx, _ry, _rw, _rh = [int(v) for v in _r.rect]
                    _cov.append((_rx, _ry,
                                    _rx + _rw, _ry + _rh))
                except Exception:
                    pass
                for _p in (getattr(_r, "ocr_polys", None) or []):
                    try:
                        _pp = np.asarray(_p, dtype=np.float32).reshape(-1, 2)
                        _cov.append((float(np.min(_pp[:, 0])),
                                        float(np.min(_pp[:, 1])),
                                        float(np.max(_pp[:, 0])),
                                        float(np.max(_pp[:, 1]))))
                    except Exception:
                        continue
            _miss = []
            for _q in _quads:
                try:
                    _qx1_ = float(np.min(_q[:, 0])); _qy1_ = float(np.min(_q[:, 1]))
                    _qx2_ = float(np.max(_q[:, 0])); _qy2_ = float(np.max(_q[:, 1]))
                except Exception:
                    continue
                _hit = False
                for _cb in _cov:
                    _ix = max(0.0, min(_qx2_, _cb[2]) - max(_qx1_, _cb[0]))
                    _iy = max(0.0, min(_qy2_, _cb[3]) - max(_qy1_, _cb[1]))
                    if _ix * _iy <= 0:
                        continue
                    _aq = max(1e-6, (_qx2_ - _qx1_) * (_qy2_ - _qy1_))
                    if (_ix * _iy) / _aq >= 0.35:
                        _hit = True
                        break
                if not _hit:
                    _miss.append((int(_qx1_), int(_qy1_),
                                     int(_qx2_ - _qx1_), int(_qy2_ - _qy1_)))
            if _quads or _miss:
                _ms = ""
                if _miss:
                    _ms = (" | " + str(len(_miss)) + " خط: det دید ولی "
                              "rec/فیلتر نگرفت → " +
                              ", ".join(f"({a},{b} {c}x{d})"
                                        for a, b, c, d in _miss[:8]))
                print(f"    [🔍252] دیباگِ det (آبی): {len(_quads)} جعبهٔ خام"
                      f" در {time.time() - _t:.1f}s{_ms}")
        except Exception:
            pass

    def extract_regions_phase(self, image: np.ndarray) -> Tuple[List[TextRegion], Optional[np.ndarray]]:
# عمرِ کشِ OCR = یک صفحه (کلید = مختصات؛ محتوا عوض
# میشود بین صفحات)
        self._ocr_crop_cache = {}
# جعبههایِ خامِ det (دیباگِ آبی) هم هر صفحه از نو
        self._dbg_det_quads = []
        h, w = image.shape[:2]
        _t_ext = time.time()  # کرونومترِ استخراج (نمایشِ سرعت)
# نشانگرِ شروعِ فاز برایِ اعلان (فقط اندروید؛ PC بدونِ
# این خط = لاگِ PC بیت‌به‌بیت)
        if _android_gate("MANGA_PHASE_PRINTS"):
            print("[*] استخراج متن…", flush=True)
        unique_regions: List[TextRegion] = []

        _raise_if_stop()
        if self.det is not None:
            unique_regions = self._extract_regions_from_bubbles(image)
        else:
# استخراج = فقط رویِ نواحیِ detector-v4-s؛ «جای
# دیگ پیگیر نشه» — بدونِ detector هیچ پاسِ تمامصفحه‌ای نیست.
            print("    [!] detector-v4-s در دسترس نیست → ناحیهٔ متنی پیدا نشد")
        _raise_if_stop()

# ضدِ «ترجمهٔ دوبارهٔ همان قسمت» — دو باکسِ detectorِ همپوشان که
# NMS/merge نتوانست یکی کند (لاگِ واقعیِ گوشی: «GO! EVEN
# FASTER…» = ناحیهٔ ۷ با rect=(283,1919,296,178) و ناحیهٔ ۸ با
# rect=(445,1951,223,163) — همپوشانیِ ۵۴٪ ولی IoU=۰.۲۸<۰.۳۵)
# هر دو ترجمه و رندر میشدند → متنِ فارسی دوبار، بالای هم.
# همینطور خطِ یتیمِ نجات‌یافته که به ناحیهٔ موجود چسبیده بود.
# قاعدهٔ تازه: متنِ «یکسان» (بعد از نرمالسازی) + همپوشانیِ
# جعبه‌ها = همان متنِ فیزیکی است → فقط یکی (بزرگتر) میماند
# متنِ «محتوایِ» دیگری (زیررشته) با احتیاطِ بیشتر (۶۰٪ داخل).
# متنِ تکراریِ واقعی در حبابهایِ جدا = بدونِ همپوشانی → هر دو
# میمانند (رفتارِ قبلی).
        try:
            unique_regions = self._dedup_duplicate_text_regions(
                unique_regions)
        except Exception:
            pass
        _raise_if_stop()

# نشانه‌گذاریِ «فقط عدد/نماد» برایِ همهٔ فازها:
# متنِ بدونِ هیچ حرف ('....'، '123124') نه ترجمه میشود نه
# پاکسازی (فیلترِ ۲۲۹ فقط ترجمه را میبست؛ پاکسازی میماند و
        #). «hi...» حرف دارد → کاملاً عادی.
# هنرِ عدد/نقطه را پاک میکرد —
        _nt_n = 0
        for _r in unique_regions:
            _t = (_r.source_text or "").strip()
            if _t and not source_has_letters(_t):
                _r.no_touch = True
                _nt_n += 1
            else:
                _r.no_touch = False
        if _nt_n:
            print(f"[*] {_nt_n} ناحیهٔ فقط عدد/نماد → دست‌نخورده "
                  f"(نه ترجمه، نه پاکسازی)")

# پاکسازیِ SFX: افکتِ صوتی/متنِ استایل‌دارِ بیرونِ حباب
# فقط وقتی --clean-sfx یا MANGA_CLEAN_SFX=1 (پیش‌فرض: SFX هنر
# است و دست‌نخورده می‌ماند)
        if unique_regions and getattr(self, "clean_sfx", False):
            _raise_if_stop()
            try:
                _sfx = self._discover_sfx_regions(image, unique_regions)
                if _sfx:
                    unique_regions.extend(_sfx)
            except Exception:
                pass
        _raise_if_stop()
        if unique_regions:
            self._verify_angle_signs(image, unique_regions)

        if self.reading_order == "rtl":
            unique_regions.sort(key=lambda r: (r.rect[1] // 80, -(r.rect[0] + r.rect[2])))
        else:
            unique_regions.sort(key=lambda r: (r.rect[1] // 80, r.rect[0]))
        for idx, r in enumerate(unique_regions):
            r.id = idx

        dbg = None
        if self.debug:
# پاسِ فقط-det رویِ کراپهایِ حباب → جعبههایِ آبی +
# لاگِ «det دید ولی rec/فیلتر نگرفت» (پاسخِ مستقیمِ سؤالِ سازنده)
            try:
                self._dbg_collect_det_quads(image, unique_regions)
            except Exception:
                self._dbg_det_quads = []
        if self.debug and unique_regions:
            dbg = self._draw_debug_regions(image, unique_regions)
# دیباگِ متنیِ کامل — متنِ استخراجی + مکان + زاویه + فاصلهٔ خط‌ها
            try:
                _vh, _vw = image.shape[:2]
                _ob = getattr(self, "_ocr_backend_name", "") or "?"
                print(f"    [🔍] دیباگِ استخراج — {len(unique_regions)} ناحیه | "
                      f"تصویر {_vw}×{_vh} | ترتیب: {self.reading_order} | OCR: {_ob}")
                for r in unique_regions:
                    try:
                        x, y, rw, rh = [int(v) for v in r.rect]
                        polys = getattr(r, "ocr_polys", None) or []
                        _lys = []
                        for _p in polys:
                            try:
                                _pa = np.asarray(_p, dtype=np.float32).reshape(-1, 2)
                                _lys.append((float(_pa[:, 1].min()),
                                             float(_pa[:, 1].max())))
                            except Exception:
                                pass
                        _lys.sort()
                        _hs = [int(_b - _a) for _a, _b in _lys]
                        _gs = [int(_lys[_i + 1][0] - _lys[_i][1])
                               for _i in range(len(_lys) - 1)]
                        _txt = (r.source_text or "").replace("\n", " ⏎ ")
                        print(f"      #{r.id:02d} {r.kind}/{r.bubble_style} | "
                              f"rect=({x},{y},{rw},{rh}) | "
                              f"زاویه={float(getattr(r, 'angle', 0.0) or 0.0):+.1f}° | "
                              f"خط={len(_lys)} بلندی={_hs} فاصله={_gs}")
                        if _txt:
                            print(f"          متن: {_txt[:200]}"
                                  f"{'…' if len(_txt) > 200 else ''}")
                    except Exception:
                        continue
            except Exception:
                pass

# جارویِ بنرهایِ تبلیغاتیِ OCR‌نخوانده (واترمارکِ سایت)
        try:
            _ads = self._scan_watermark_banners(image, unique_regions)
            if _ads:
                print(f"[*] {len(_ads)} بنرِ تبلیغ شناسایی شد")
                unique_regions = list(unique_regions) + _ads
        except Exception:
            pass

        _ob2 = getattr(self, "_ocr_backend_name", "") or "?"
        _dt = time.time() - _t_ext
        if unique_regions:
            print(f"[+] متن استخراج شد: {len(unique_regions)} ناحیه | "
                  f"زمانِ استخراج: {_dt:.1f} ثانیه | موتور: {_ob2}")
        else:
            print("[!] هیچ متن/حبابی یافت نشد.")
        return unique_regions, dbg

    def _scan_watermark_banners(self, image: np.ndarray,
                                regions: List[TextRegion]) -> List[TextRegion]:
        """ — جارویِ «بنرهایِ تبلیغاتیِ سایت» (واترمارکِ دامنه) که
        OCRِ عادیِ صفحه از آن‌ها چیزی نخوانده (نمونه: بنرِ ASURASCANS.COM
        وسطِ نوارِ بلند). کاندید: بلابِ پهن‌وکوتاهِ پرتراکم از ضربه‌هایِ
        متضاد با زمینهٔ محلی، بدونِ همپوشانی با نواحیِ موجود → کراپ ×۳ →
        OCR → اگر متن با `_is_watermark_text` (دامنه/برند) خوانده شد →
        ناحیهٔ promo ساخته می‌شود؛ ماسکِ سازنده کلِ بنر را توپر پاک
        می‌کند (تبلیغ باید کامل فیلتر شود)."""
        found: List[TextRegion] = []
        try:
            h, w = image.shape[:2]
        except Exception:
            return found
        if getattr(self, "ocr", None) is None:
            return found
        try:
# جارویِ تمام‌رزولوشنِ کاشی‌شده: بنرهایِ کوچک در
# نوارهایِ بلند با downscale نابود می‌شدند (۴px!) → صفحه به
# کاشی‌هایِ ~۲۲۰۰px با هم‌پوشانی تقسیم می‌شود و هر کاشی در
# رزولوشنِ کامل جارو می‌شود.
            _tile = 2200
            _ovl = 120
            _exist = []
            for r in (regions or []):
                try:
                    _exist.append([int(v) for v in r.rect])
                except Exception:
                    continue
            _kb = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 5))
            _kd = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 5))
            _found_rects: list = []
            _cands: list = []
            _cand_n = 0
            _ty0 = 0
            while _ty0 < h:
                _y1 = min(h, _ty0 + _tile)
                tile = image[_ty0:_y1]
                _tnext = _y1 if _y1 >= h else _y1 - _ovl
                g = cv2.cvtColor(tile, cv2.COLOR_BGR2GRAY)
                _med = cv2.medianBlur(g, 21)
                _stk = (np.abs(g.astype(np.int16)
                               - _med.astype(np.int16)) > 42)
                _blob = cv2.morphologyEx((_stk * 255).astype(np.uint8),
                                         cv2.MORPH_CLOSE, _kb)
                _blob = cv2.dilate(_blob, _kd)
                n, lab, st, _ = cv2.connectedComponentsWithStats(_blob, 8)
                for i in range(1, n):
                    bx = int(st[i, cv2.CC_STAT_LEFT])
                    by = int(st[i, cv2.CC_STAT_TOP])
                    bw_ = int(st[i, cv2.CC_STAT_WIDTH])
                    bh_ = int(st[i, cv2.CC_STAT_HEIGHT])
                    if bw_ < 60 or bh_ < 12 or bh_ > 170 or bw_ > 1000:
                        continue
                    if bw_ < 2.2 * bh_:
                        continue
                    _fill = float(st[i, cv2.CC_STAT_AREA]) / float(bw_ * bh_)
                    if _fill < 0.06 or _fill > 0.95:
                        continue
# بنرِ توپر (fillِ بالا؛ خودِ جعبهٔ رنگی هم
# بلاب می‌شود): باید ضربهٔ متنیِ داخلش باشد وگرنه
# تابلو/جعبهٔ هنر است. داورِ نهایی OCR + الگویِ دامنه است.
                    if bw_ >= 60 and bh_ >= 12:
                        _sub = _stk[by:by + bh_, bx:bx + bw_]
                        _sr = float(_sub.mean()) if _sub.size else 0.0
                        if _sr < 0.025 or _sr > 0.60:
                            continue
                    else:
                        continue
                    X0, X1 = bx, bx + bw_
                    Y0, Y1 = by + _ty0, by + bh_ + _ty0
                    _skip = False
                    for (rx, ry, rw, rh) in _exist:
                        if not (X1 < rx or X0 > rx + rw
                                or Y1 < ry or Y0 > ry + rh):
                            _skip = True
                            break
                    if _skip:
                        continue
                    _dup = False
                    for (fx0, fy0, fx1, fy1) in _found_rects:
                        ix0, iy0 = max(X0, fx0), max(Y0, fy0)
                        ix1, iy1 = min(X1, fx1), min(Y1, fy1)
                        if ix1 - ix0 > 0.5 * min(X1 - X0, fx1 - fx0) \
                                and iy1 - iy0 > 0.5 * min(Y1 - Y0, fy1 - fy0):
                            _dup = True
                            break
                    if _dup:
                        continue
                    cx0, cy0 = max(0, X0 - 8), max(0, Y0 - 8)
                    cx1, cy1 = min(w, X1 + 8), min(h, Y1 + 8)
                    if cx1 - cx0 < 30 or cy1 - cy0 < 12:
                        continue
# OCR فقط برایِ کاندیدهایِ منتخب. امتیاز:
# (چسبیده‌به‌لبه اول — واترمارکِ سایت‌ها معمولاً در حاشیه
# است، بعد تراکمِ ضربه = متن‌مانند، بعد پُری). کاندیدها
# «گردشی» (round-robin) بینِ کاشی‌ها مصرف می‌شوند تا
# بنرِ دورِ نوارِ بلند (img1: y≈11000) همیشه به نوبت
# برسد — رتبه‌بندیِ سراسری بنرِ دور را قربانیِ بلاب‌هایِ
# بالای صفحه می‌کرد (رگرسیونِ اکشن).
                    _edge = 0 if min(int(X0), w - int(X1)) <= 40 else 1
                    _cands.append((
                        int(_ty0),
                        _edge,
                        -float(_sr),
                        -float(_fill),
                        cx0, cy0, cx1, cy1))
                _ty0 = _tnext
# بودجهٔ OCRِ جارو + مصرفِ گردشیِ بینِ کاشی‌ها.
            try:
                _max_calls = int(os.environ.get(
                    "MANGA_BANNER_OCR_MAX", "0") or 0)
            except Exception:
                _max_calls = 0
            if _max_calls <= 0:
                _nt = max(1, int((h + _tile - 1) // max(1, _tile - _ovl)))
                _max_calls = min(40, 24 + 6 * max(0, _nt - 2))
            _buckets: dict = {}
            for _c3 in _cands:
                _buckets.setdefault(_c3[0], []).append(_c3)
            for _b in _buckets.values():
                _b.sort(key=lambda t: (t[1], t[2], t[3]))
            _ordered: list = []
            while any(_buckets.values()):
                for _tk in sorted(_buckets):
                    if _buckets[_tk]:
                        _ordered.append(_buckets[_tk].pop(0))
            if self.debug:
                try:
                    _top = ", ".join(
                        f"({c[4]},{c[5]},edge{c[1]},s{-c[2]:.2f})"
                        for c in _ordered[:12])
                    print(f"  [🔍] جارویِ بنر: {len(_cands)} کاندید | "
                          f"بودجه {_max_calls} | ترتیبِ گردشی: {_top}")
                except Exception:
                    pass
            _ocr_calls = 0
            _stop_all = False  # توقفِ زودهنگام
            try:
                _empty_max = int(os.environ.get(
                    "MANGA_BANNER_EARLY_STOP", "8") or 0)
            except Exception:
                _empty_max = 8
            _empty_streak = 0
# سقفِ زمانیِ جارو (MANGA_BANNER_TLIMIT ثانیه
# ‎0=خاموش). OCRِ خالی رویِ PC (RapidOCR) ~۲.۳s است و ۱۲+
# کاندید = ~۳۰s فقط جارو؛ موتورِ گوشی سریع است و سقف
# نمی‌خورد. کاندیدهایِ رتبهٔ بالا (لبه/تراکم) اول مصرف
# می‌شوند پس بنرِ واقعی همیشه در اولین‌هاست.
            try:
                _tlimit = float(os.environ.get(
                    "MANGA_BANNER_TLIMIT", "0") or 0)
            except Exception:
                _tlimit = 0.0
            if _tlimit <= 0:
                try:
                    if _on_android():
                        _tlimit = 0.0
                    else:
# PC: کاندیدهایِ هر کاشی به نوبت مصرف می‌شوند؛ سقف
# با تعدادِ کاشی‌ها می‌سد تا بنرِ دورِ نوارِ بلند
# (نوبتِ کاشیِ آخر) قربانیِ نشود، ولی جارو هم
# بی‌نهایت OCRِ خالی (RapidOCR ~۱.۹s/فراخوانی)
# خرج نکند.
                        _nt2 = max(1, int((h + _tile - 1)
                                           // max(1, _tile - _ovl)))
                        _tlimit = max(8.0, 3.0 * _nt2)
                except Exception:
                    _tlimit = 8.0
            _t = time.time()
# کاندیدها بچهای (W=workerِ OCR) موازی OCR میشوند
# داوری/بودجه/streak در همان ترتیبِ قبل اعمال میشود → نتیجه
# همان (یا یادآوریِ بیشترِ محدود به W-1 کاندیدِ اضافه). پلّهٔ
# زومِ داخلِ هر کاندید ترتیبی میماند (برندهٔ همان واریانتِ اول).
            _wm_pw = self._ocr_pool_workers(len(_ordered))
            _wm_i = 0

            def _wm_scan_one(_c):
                (_s0, _s1, _s2, _s3, cx0, cy0, cx1, cy1) = _c
                out = {"calls": 0, "empty": 0, "nonempty": False,
                       "txt": "", "found": False}
                try:
                    crop = image[cy0:cy1, cx0:cx1]
                    if crop.size == 0:
                        return out
                    _pad_h = max(0, 48 - crop.shape[0])
                    _pad_w = max(0, 160 - crop.shape[1])
                    if _pad_h or _pad_w:
                        crop = cv2.copyMakeBorder(
                            crop, _pad_h // 2, _pad_h - _pad_h // 2,
                            _pad_w // 2, _pad_w - _pad_w // 2,
                            cv2.BORDER_REPLICATE)
                    _txt = ""
# کاندیدِ خالی گران است (پروفایلِ img6: ۸
# پاسِ OCR رویِ ۴ لکهٔ هنریِ بی‌متن). اگر در زومِ ۳
# هیچ متنی نبود (هر دو واریانت)، زومِ ۲ هم نمیآید —
# متنِ واقعیِ بنر در زومِ ۳ پیدا میشود.
                    for _zm in (3, 2):
                        _zm_empty = True
                        _big = cv2.resize(
                            crop, (crop.shape[1] * _zm,
                                   crop.shape[0] * _zm),
                            interpolation=cv2.INTER_CUBIC)
                        for _var in (0, 1):
                            _try = _big
                            if _var == 1:
                                try:
                                    _lab2 = cv2.cvtColor(_big,
                                                         cv2.COLOR_BGR2LAB)
                                    _clahe = cv2.createCLAHE(
                                        2.2, (8, 8))
                                    _l2 = _clahe.apply(_lab2[..., 0])
                                    _try = cv2.cvtColor(
                                        cv2.merge([_l2, _l2, _l2]),
                                        cv2.COLOR_BGR2GRAY)
                                    _try = cv2.cvtColor(
                                        _try, cv2.COLOR_GRAY2BGR)
                                except Exception:
                                    _try = _big
                            try:
                                _res = self.ocr.ocr(_try)
                            except Exception:
                                _res = None
                            out["calls"] += 1
                            _txts = []
                            if _res:
                                for _ln in (_res[0] or []):
                                    try:
                                        _tv = _ln[1]
                                        if isinstance(_tv, (tuple, list)):
                                            _tv = _tv[0]
                                        if str(_tv).strip():
                                            _txts.append(str(_tv).strip())
                                    except Exception:
                                        continue
                            _txt = " ".join(_txts)
                            if _txt:
                                out["nonempty"] = True
                                _zm_empty = False
                            else:
                                out["empty"] += 1
                            if self._is_watermark_text(_txt):
                                break
                            if _txt:
                                break
                        if _zm_empty and _zm == 3:
                            break  # زومِ ۲ هم خالی می‌مانَد
                    if _txt and self._is_watermark_text(_txt):
                        out["found"] = True
                        out["txt"] = _txt
                except Exception:
                    pass
                return out

            _wm_results: list = []
            while _wm_i < len(_ordered):
                if _tlimit > 0 and time.time() - _t > _tlimit:
                    if self.debug:
                        try:
                            print(f"  [🔍] جارویِ بنر: سقفِ زمانیِ "
                                  f"{_tlimit:.0f}s — {_ocr_calls} "
                                  f"فراخوانی از {len(_ordered)} کاندید",
                                  flush=True)
                        except Exception:
                            pass
                    break
                if _stop_all:
                    if self.debug:
                        try:
                            print("  [🔍] جارویِ بنر: توقفِ زودهنگام — "
                                  f"{_empty_streak} فراخوانیِ خالیِ پیاپی "
                                  f"(اکاندی‌هایِ بعدی هم بافتِ هنرند)",
                                  flush=True)
                        except Exception:
                            pass
                    break
                if _ocr_calls >= _max_calls:
                    if self.debug:
                        try:
                            print(f"  [🔍] جارویِ بنر: بودجهٔ OCR تمام شد "
                                  f"({_max_calls} فراخوانی) — "
                                  f"{len(_cands)} کاندید")
                        except Exception:
                            pass
                    break
# یک بچِ W کاندید موازی OCR میشود
                _batch = _ordered[_wm_i:_wm_i + max(1, _wm_pw)]
                _wm_i += len(_batch)
                if _wm_pw > 1:
                    try:
                        with ThreadPoolExecutor(max_workers=_wm_pw) as _wmx:
                            _wm_res = list(_wmx.map(_wm_scan_one, _batch))
                    except Exception:
                        _wm_res = [_wm_scan_one(_c) for _c in _batch]
                else:
                    _wm_res = [_wm_scan_one(_c) for _c in _batch]
                for (_c2, _r) in zip(_batch, _wm_res):
                    (_s0, _s1, _s2, _s3, cx0, cy0, cx1, cy1) = _c2
                    _ocr_calls += int(_r.get("calls", 0))
                    _txt = str(_r.get("txt", "") or "")
# شمارِ فراخوانیِ بی‌متنِ پیاپی (به همان
# ترتیبِ کاندیدها؛ بینِ بچها ارزیابی میشود)
                    if _r.get("nonempty"):
                        _empty_streak = 0
                    else:
                        _empty_streak += int(_r.get("empty", 0))
                        if (_empty_max > 0
                                and _empty_streak >= _empty_max):
                            _stop_all = True
                    if _r.get("found"):
                        _tr = TextRegion(
                            id=10000 + len(found),
                            boxes=[np.array([[cx0, cy0], [cx1, cy0],
                                             [cx1, cy1], [cx0, cy1]],
                                            dtype=np.float32)],
                            source_text=_txt,
                            rect=(cx0, cy0, cx1 - cx0, cy1 - cy0),
                            kind="promo")
                        found.append(_tr)
                        _found_rects.append((cx0, cy0, cx1, cy1))
# بعد از اولین بنر، بودجهٔ باقی‌مانده
# به یک‌سوم فشرده می‌شود (چند بنر در یک صفحه
# نادر است؛ ادامه با بودجهٔ کامل فقط وقت می‌گیرد)
                        try:
                            _max_calls = min(
                                _max_calls,
                                _ocr_calls + max(6,
                                                 (_max_calls - _ocr_calls) // 3))
                        except Exception:
                            pass
                        if self.debug:
                            try:
                                print(f"  [🔍] بنرِ تبلیغ: rect={_tr.rect} "
                                      f"متن: {_txt[:60]}")
                            except Exception:
                                pass
            if self.debug:
                try:
                    print(f"  [🔍] جارویِ بنر: {len(found)} تبلیغ شناسایی شد")
                except Exception:
                    pass
        except Exception:
            import traceback as _tb
            if self.debug:
                try:
                    print("  [🔍] جارویِ بنر: خطا —")
                    _tb.print_exc()
                except Exception:
                    pass
            return found
        return found

    def finish_page_phase(self, image: np.ndarray, regions: List[TextRegion],
                          skip_translate: bool = False,
                          precleaned: Optional[np.ndarray] = None,
                          final: bool = False,
                          ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        _raise_if_stop()
        if not regions:
            return image.copy(), None

        page_debug: Optional[np.ndarray] = None

        dialogue_regions = [r for r in regions if r.kind == "dialogue"]
        promo_regions = [r for r in regions if r.kind == "promo"]
        sfx_regions = [r for r in regions if r.kind == "sfx"]
        junk_regions = [r for r in regions if r.kind == "junk"]
        raw_image_copy = image.copy()

        if getattr(self, "clean_only", False):
# درخواستِ کاربر: «متنِ تبلیغِ سایت (ASURASCANS.COM
# و…) و SFX نباید پاک شه یا حساب شه — ازش رد شه.» در حالتِ
# فقط-پاکسازی فقط دیالوگ (+junk: شمارهٔ صفحه) پاک می‌شود
# بنرِ تبلیغ و افکتِ صوتی دست‌نخورده می‌مانند.
            clean_targets = [r for r in regions if r.kind in ("dialogue", "junk")]
# اندروید (MANGA_CLEAN_TEXTFREE): ناحیههایِ
# text_free در clean-only پاک نمیشدند (فیلترِ فقط
# dialogue/junk) — ولی text_free = متنِ واقعیِ OCRشده
# (بنرِ تبلیغ جداگانه kind=promo میگیرد از جارویِ بنر) —
# لاگِ گوشیِ : ناحیهٔ نجاتخوردهٔ «PARAGRAPH 3
# WHEN THE EXERCISE…» (15,3256) بعد از ادغام با ناحیهٔ
# جارو kind=text_free گرفت → از پاکسازی رد شد = کلِ متن
# دستنخورده ماند؛ «THIS IS ONLY A DRAFT…» (0,10605) هم
# همیشه از تاکنون پاک نشده بود. PC بیت‌به‌بیت.
            if _android_gate("MANGA_CLEAN_TEXTFREE"):
                _tf = [r for r in regions if r.kind == "text_free"]
                if _tf:
                    clean_targets = clean_targets + _tf
                    if self.debug:
                        try:
                            print(f"  [*]text_free: +{len(_tf)} "
                                  f"ناحیه به پاکسازی اضافه شد "
                                  f"(متنِ واقعی — نه تبلیغ)", flush=True)
                        except Exception:
                            pass
            if self.debug and regions:
                page_debug = self._draw_debug_regions(image, regions)
                try:
                    _kc = {}
                    for _r in regions:
                        if _r.kind not in ("dialogue", "junk"):
                            _kc[_r.kind] = _kc.get(_r.kind, 0) + 1
                    if _kc:
                        print(f"  [*]{len(regions) - len(clean_targets)}"
                              f" ناحیه رد شد (تبلیغ/SFX دست‌نخورده): {_kc}")
                except Exception:
                    pass
            if clean_targets:
# ضدِ «دوبارِ پاکسازی در حالتِ فقط-پاکسازی»
# :
# فازِ پسزمینه (فاز ۱/۲) همین صفحه را از قبل پاک کرده
# و precleaned داده شده — قبلاً این شاخه آن را نادیده
# میگرفت و کلِ پاکسازی از نو اجرا میشد (لاگِ واقعیِ
# PC: clean=51.7s و بعدش clean+render=53.5s = دوبرابر).
# حالا نتیجهٔ فازِ پسزمینه همان لحظه استفاده میشود
# فاصلهٔ هدفها هم با افزودنِ junk به فازِ پسزمینه
# (بالا) همسان شد.
                if precleaned is not None:
                    final_image = precleaned
                else:
                    if _android_gate("MANGA_PHASE_PRINTS"):
                        print("[*] پاکسازی متن…", flush=True)
                    _t0 = time.time()
                    final_image = self.clean_image(image, clean_targets)
                    print(f"[+] پاکسازی: {time.time() - _t0:.1f} ثانیه با {self._clean_label()}")
            else:
                final_image = precleaned.copy() if precleaned is not None else image.copy()
            return final_image, page_debug

# نجاتِ OCR: ناحیههایِ «حبابِ پیدا شده ولی
# متنِ نخوانده» یک تلاشِ دیگر میگیرند (متدِ مشترک — مسیرِ
# ترجمهٔ درونصفحهای؛ مسیرِ بچ هم قبل از صف فراخوانی میکند).
        if (not skip_translate and dialogue_regions
                and not getattr(self, "clean_only", False)):
            self._rescue_empty_ocr(image, dialogue_regions)

        if skip_translate:
            pass
        elif dialogue_regions:
            print(f"[*] ترجمه: {len(dialogue_regions)} حباب…")
            self.translate_regions(dialogue_regions)

# «Ai وقتی خالی برمیگردونه عکسِ انگلیسیش نشون نده تا
# وقتی همشو ترجمه کنه … نمایش زنده کنه کم کم بذاره تو نمایش انگار
# داره لود بشه» (PC/لینوکس/اندروید). صفحهٔ نهایی با حبابِ بیترجمه
# تمام نمیشود: تا وقتی حبابِ بامتنِ بیجواب مانده، دوباره و دوباره
# از مدل پرسیده میشود (هر دورِ translate_regions خودش ۳ دورِ بچ
# + نجاتِ تکآیتمی دارد). فقط پیش‌نمایشِ زنده (final=False) بدونِ
# این سد کار میکند تا حبابها «کمکم» همان لحظه که ترجمهشان میرسد
# رویِ نمایش بنشینند (حبابِ هنوز بیترجمه = خالیِ روشن = لودینگ).
# سدِ دو-فازی: در فازِ استخراجِ بچ هیچ دورِ ترجمه‌ای
# زده نمیشود (دستور: «استخراج تموم شد بعدش بره ترجمه»)
# پسگیریِ خالیها بعد از اتمامِ کل، در run با بستههایِ ۳۰تایی است.
        if (final and not getattr(self, "clean_only", False)
                and not getattr(self, "fake_translate", False)
                and getattr(self, "_extraction_done", True)):
            for _g_round in range(1, 4):
                if stop_requested():
                    break
                _g_missing = [r for r in dialogue_regions
                              if not (r.translated_text or "").strip()
                              and (r.source_text or "").strip()
                              and source_has_letters(r.source_text)
                              and not getattr(r, "ocr_empty", False)]
                if not _g_missing:
                    break
                print(f"[193] دورِ {_g_round}/۳: {_g_missing.__len__()} حباب هنوز ترجمه نشده — "
                      "تا ترجمهٔ کامل صبر میشود، انگلیسی نشان داده نمیشود…")
                try:
                    self.translate_regions(_g_missing)
                except (GeminiQuotaExhausted, JobCancelled):
                    raise
                except Exception as _g_err:
                    print(f"    [193] دورِ {_g_round} خطا: {str(_g_err)[:80]}")
                    time.sleep(0.6)

        translated_regions = [r for r in dialogue_regions if r.translated_text]
# باگِ «ترجمهٔ خالی» (PC/لینوکس/اندروید).
# در مسیرِ بچ، پاکسازی همهٔ دیالوگها را از قبل پاک میکند
# (precleaned)؛ اگر ترجمهٔ مدل برای بعضی ناحیهها نرسیده باشد، آن
# ناحیه در translated_regions نیست → حبابِ سفیدِ «خالی» رویِ خروجی
# میماند. قانونِ 189 («هیچ حبابِ خالی») اینجا هم اجرا میشود:
# متنِ مبدأ رویِ حبابِ پاکشده رندر میشود — رویِ «کپی»، نه خودِ
# ناحیه، تا دورِ بعدیِ ترجمهٔ واقعی (بافرِ چندصفحهای/پیشنمایش)
# دستنخورده بماند. فقط وقتی متنِ اصلی از قبل پاک شده
# (precleaned)؛ در مسیرِ تکصفحهای متنِ اصلی سرِ جایش است.
# فقط در رندرِ «نهایی» (final=True): پیش‌نمایشِ زنده
# دیگر متنِ مبدأ (انگلیسی) را رویِ حبابهایِ درانتظار نمینشاند —
# آنها خالیِ روشن میمانند (= لودینگ) تا ترجمهٔ واقعی کمکم بنشیند.
# قبل از این رندر، سدِ [193] بالا تا ۳ دورِ دیگر از مدل پرسیده است.
        _fb: List[TextRegion] = []
        if final and precleaned is not None:
            for _r2 in dialogue_regions:
                if (_r2.translated_text or "").strip() \
                        or not (_r2.source_text or "").strip() \
                        or not source_has_letters(_r2.source_text) \
                        or getattr(_r2, "ocr_empty", False):
                    continue
                _c = copy.copy(_r2)
                _c.translated_text = _r2.source_text
                _fb.append(_c)
            if _fb:
                print(f"  [192] {len(_fb)} حباب بدونِ ترجمه ولی پاکشده → "
                      "متنِ مبدأ رندر شد (ضدِ حبابِ خالی)")
                if self.debug:
                    for _c in _fb:
                        try:
                            print(f"    [192] حباب[{_c.id}] rect="
                                  f"{tuple(int(v) for v in _c.rect)} → "
                                  f"متنِ مبدأ: {(_c.translated_text or '')[:60]}")
                        except Exception:
                            pass
# بازگشتِ «فقط پاکسازی» برایِ ناحیههایِ بی‌متن — اینها را از
# پاکسازی بیرون کشیده بود (ترسِ حبابِ سیاه رویِ زمینهٔ تیره از
# ۰۱۲_p1) — ولی هر ناحیهٔ ocr_empty از گیتِ «زمینهٔ روشن + جوهرِ
# تیره» (گیتِ جوهرِ متنی در ساختِ ناحیه) گذشته و ماسکِ پاکسازی هم
# فقط جوهرِ متن را برمیدارد نه مستطیلِ توپر → حبابِ سیاه رخ
# نمیدهد؛ «متنِ قبلی میمونه» بدتر از هر لکهٔ احتمالی بود.
        _oe = [r for r in dialogue_regions
                  if not r.translated_text
                  and getattr(r, "ocr_empty", False)]
        _ocr_empty_regions = _oe
        if _oe:
            for _r in _oe:
                try:
                    print(f"  [!] ناحیهٔ {_r.id} بدونِ متنِ OCR → فقط پاکسازی (rect={tuple(int(v) for v in _r.rect)}) — متنِ قبلی نمیماند")
                except Exception:
                    pass
# قانونِ نهاییِ کاربر: «متنِ تبلیغِ سایت حسابش نکن —
# ازش رد شه.» بنرِ تبلیغ/واترمارک دیگر در هیچ حالتی پاک نمی‌شود
# (قبلاً در حالتِ ترجمه‌دار کلِ بنر توپر ماسک و LaMa می‌شد که
# هم خودش ریسکِ لکّه داشت و هم خلافِ خواستهٔ تازهٔ کاربر بود).
# ترجمه/رندر هم رویش نمی‌نشیند (فقطِ dialogue ترجمه می‌شود).
        _clean_regions = (translated_regions + _ocr_empty_regions)
# با --clean-sfx، افکت‌های صوتی هم پاک می‌شوند
# (ترجمه نمی‌شوند؛ فقط حذف)
        if getattr(self, "clean_sfx", False) and sfx_regions:
            _clean_regions = _clean_regions + sfx_regions
# اندروید (همان MANGA_CLEAN_TEXTFREEِ مسیرِ
# clean-only): در حالتِ ترجمه‌دار هم ناحیههایِ text_free فقط
# «پاک» میشوند (ترجمه نمیشوند — متنِ اصلی حذف میماند) وگرنه
# «PARAGRAPH 3…» و «THIS IS ONLY A DRAFT…» در خروجیِ ترجمهشده
# هم زنده میمانند. PC بیت‌به‌بیت.
        if _android_gate("MANGA_CLEAN_TEXTFREE"):
            _tf140t = [r for r in regions if r.kind == "text_free"]
            if _tf140t:
                _clean_regions = _clean_regions + _tf140t
# فقط ناحیههایِ «بامتنِ مبدأ ولی بیترجمه» «ترجمه نشد"
# حساب میشوند؛ ناحیهٔ بی‌متن (چرتِ فیلترشده) اصلاً ترجمه ندارد.
# فقط در رندرِ نهایی چاپ میشود؛ در پیش‌نمایشِ زنده
# حبابهایِ درانتظار طبیعیاند و نباید هر ۲ ثانیه هشدار بدهند.
        missing_n = sum(1 for r in dialogue_regions
                        if not r.translated_text
                        and not getattr(r, "ocr_empty", False)
                        and (r.source_text or "").strip()
                        and source_has_letters(r.source_text))
        if missing_n and final:
            print(f"[!] {missing_n} حباب ترجمه نشد")
        if self.debug:
            if promo_regions:
                print(f"  [*] {len(promo_regions)} تبلیغ → دست‌نخورده «ازش رد شه»")
            if sfx_regions:
# با --clean-sfx پاک می‌شوند، وگرنه دست‌نخورده
                _sfx = "پاک شدند" if getattr(self, "clean_sfx", False) else "دست‌نخورده"
                print(f"  [*] {len(sfx_regions)} SFX → {_sfx}")
            if junk_regions:
                print(f"  [*] {len(junk_regions)} junk → دست‌نخورده")

        if self.debug and regions:
            page_debug = self._draw_debug_regions(image, regions)

# «or _fb192»: وقتی «هیچ» حیابی ترجمه نشده (مدلِ کامل
# خالی)، _clean_regions خالی است و رندر کلاً رد میشد → صفحهٔ
# تمامسفیدِ حباب تحویل میگرفتی. با فال‌بکِ 192 باید رندر انجام
# شود تا لااقل متنِ مبدأ رویِ کپیها بنشیند (ضدِ حبابِ خالی).
        if _clean_regions or _fb:
            if precleaned is not None:
                cleaned_image = precleaned
            else:
                if _android_gate("MANGA_PHASE_PRINTS"):
                    print("[*] پاکسازی متن…", flush=True)
                _t0 = time.time()
                cleaned_image = self.clean_image(image, _clean_regions)
                print(f"[+] پاکسازی: {time.time() - _t0:.1f} ثانیه با {self._clean_label()}")
            final_image = self.render_translations(
                cleaned_image,
                (translated_regions + _fb) if _fb else translated_regions,
                raw_image_copy)
            if not self.debug:
                for _r in translated_regions:
                    _txt = (_r.translated_text or "").strip().replace("\n", " / ")
                    if _txt:
                        print(f"    {_txt[:150]}")
        else:
            final_image = precleaned.copy() if precleaned is not None else image.copy()
# «اون قسمتهایی که متن نداره خالیه — وقتی متن نباشه شکلِ
# لودینگ بیار جایِ متن؛ متنش ترجمه شد بذار سرجاش» (پیشنمایشِ زندهٔ
# کمکم). در مسیرِ بچ، متنِ همهٔ دیالوگها از قبل پاک شده (precleaned)
# حبابِ هنوز بیجواب = جایِ خالی. حالا بهجایِ خالی، نشانِ لودینگ
# (چرخِ چرخان) وسطِ حباب می‌نشیند؛ همین که ترجمهٔ واقعی برسد
# رندرِ بعدیِ پیشنمایش متن را سرِ جایش میگذارد و نشانِ لودینگ از
# آن ناحیه حذف میشود. فقط پیشنمایش (final=False) — رندرِ نهایی
# یا متنِ مبدأ دارد (فالبکِ 192) یا سدِ 193 صفحه را کامل نگه میدارد.
        if (not final and precleaned is not None
                and not getattr(self, "clean_only", False)):
            _wait_regions = [r for r in dialogue_regions
                             if not (r.translated_text or "").strip()
                             and not getattr(r, "ocr_empty", False)
                             and (r.source_text or "").strip()]
            if _wait_regions:
                try:
                    final_image = self._draw_loading_marks(
                        final_image, _wait_regions)
                except Exception as _lg_err:
                    if self.debug:
                        try:
                            print(f"    [194] نشانِ لودینگ: {str(_lg_err)[:80]}")
                        except Exception:
                            pass
        return final_image, page_debug

    def _draw_loading_marks(self, image: np.ndarray,
                                 regions: List[TextRegion]) -> np.ndarray:
        """ — نشانِ «در حال ترجمه…» وسطِ حبابهایِ درانتظار.
        یک قوسِ خاکستریِ نازک (چرخِ لودینگ) + سه نقطهٔ کوچک زیرش؛
        قوس با هر رندرِ پیشنمایش کمی میچرخد تا حسِ «لود شدن» بدهد.
        خاکستریِ ملایم رویِ حبابِ روشن = لودینگِ محسوس ولی مزاحمِ صفحه
        نمیشود؛ در رندرِ نهایی هرگز صدا زده نمیشود."""
        img = image
        if img is None or img.size == 0 or not regions:
            return img
        h, w = img.shape[:2]
# چرخشِ نرم: هر رندرِ پیشنمایش زاویهٔ شروعِ قوس جلو
# میرود؛ چون پیشنمایش هر ۲+ ثانیه با رسیدنِ ترجمهٔ تازه رندر
# میشود، چرخ بهتدریج «میچرخد».
        _spin = int((time.time() * 90.0) % 360.0)
        for r in regions:
            try:
# rect = (x, y, عرض، ارتفاع) است (قراردادِ
# TextRegion؛ rect=(x0, y0, x1-x0, y1-y0) در محلِ ساخت) —
# نه گوشه‌ها؛ با گوشه فرضکردن، نشان وسطِ جایِ غلط می‌نشست.
                _rx, _ry, _rw, _rh = r.rect
                x0, y0 = max(0, int(_rx)), max(0, int(_ry))
                x1 = min(w - 1, int(_rx + _rw) - 1)
                y1 = min(h - 1, int(_ry + _rh) - 1)
                bw, bh = x1 - x0, y1 - y0
                if bw < 26 or bh < 26:
                    continue  # حبابِ خیلی ریز — جای نشان ندارد
                cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                rad = int(min(bw, bh) * 0.17)
                rad = max(8, min(rad, 44))
                th = max(2, rad // 5)
                col = (150, 150, 150)  # خاکستریِ ملایم (BGR)
# قوسِ ناتمام = چرخِ لودینگ؛ زاویهٔ شروع با زمان میچرخد
                cv2.ellipse(img, (cx, cy), (rad, rad), _spin % 360,
                            0, 250, col, th, cv2.LINE_AA)
# سه نقطهٔ «…» زیرِ چرخ — داخلِ حباب میماند (خارجِ ناحیه نمیرود)
                _d = max(2, th - 1)
                _dy = min(cy + rad + th * 3, y1 - _d - 1)
                if _dy > cy:
                    for _k in (-1, 0, 1):
                        _px = cx + _k * (rad // 2 + _d * 2)
                        if x0 + _d < _px < x1 - _d:
                            cv2.circle(img, (_px, _dy), _d, col, -1, cv2.LINE_AA)
            except Exception:
                continue
        return img

    def process_core(self, image: np.ndarray) -> np.ndarray:
# زمان‌گیریِ مراحل (درخواستِ کاربر: از استخراج تا آخرِ
# پاکسازی رویِ PC و اندروید زمان بگیر تا سریع‌سازیِ بدونِ افت بشود)
        _t_all = time.time()
        _t = time.time()
        regions, dbg = self.extract_regions_phase(image)
        _t_ext = time.time() - _t
        if dbg is not None:
            self._last_debug_image = dbg
        else:
            self._last_debug_image = None
        if not regions:
            try:
                print(f"[TIME] extract={_t_ext:.1f}s | "
                      f"total={time.time() - _t_all:.1f}s (بدونِ متن)",
                      flush=True)
            except Exception:
                pass
            return image
        _t = time.time()
        try:
            self._classify_balloon_tones(image, regions)
        except Exception:
            pass
        _t_tone = time.time() - _t
        _t = time.time()
        final_image, _ = self.finish_page_phase(image, regions, final=True)
        _t_fin = time.time() - _t
        try:
            print(f"[TIME] extract={_t_ext:.1f}s tone={_t_tone:.1f}s "
                  f"translate+clean+render={_t_fin:.1f}s "
                  f"total={time.time() - _t_all:.1f}s", flush=True)
        except Exception:
            pass
        return final_image

    def _classify_balloon_tones(self, image: np.ndarray,
                                regions: List[TextRegion]) -> None:
        clf = getattr(self, "_tone_clf", None)
        if clf is None:
            clf = BalloonToneClassifier()
            self._tone_clf = clf
        h, w = image.shape[:2]
        for r in regions:
            if getattr(r, "style_locked", False):
                continue  # سبکِ قفل‌شده (پنجرهٔ سیستم) دست‌نخورده می‌ماند
            try:
                x0, y0, x1, y1 = r.rect
                x0, y0 = max(0, int(x0)), max(0, int(y0))
                x1, y1 = min(w, int(x1)), min(h, int(y1))
                if x1 - x0 < 10 or y1 - y0 < 10:
                    continue
                pad = 8
                px0 = max(0, x0 - pad)
                py0 = max(0, y0 - pad)
                px1 = min(w, x1 + pad)
                py1 = min(h, y1 + pad)
                crop = image[py0:py1, px0:px1]
                tone = clf.classify(crop)
                if tone and tone in BalloonToneClassifier.TONES:
                    r.bubble_style = tone
            except Exception:
                continue

    @staticmethod
    def _is_mostly_blank(image: np.ndarray, std_thresh: float = 12.0, unique_thresh: int = 24) -> bool:
        if image is None or image.size == 0:
            return True
        h, w = image.shape[:2]
        if h < 40 or w < 40:
            return True
        y0, y1 = int(h * 0.15), int(h * 0.85)
        x0, x1 = int(w * 0.1), int(w * 0.9)
        crop = image[y0:y1, x0:x1]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
        if float(np.std(gray)) < std_thresh:
            return True
        hist = cv2.calcHist([gray], [0], None, [64], [0, 256]).flatten()
        if int(np.count_nonzero(hist > (gray.size * 0.002))) < unique_thresh and float(np.std(gray)) < 22:
            return True
        return False

    @staticmethod
    def _is_url(s: str) -> bool:
        return s.lower().startswith("http://") or s.lower().startswith("https://")

    @staticmethod
    def _cluster_widths(widths: List[int], abs_tol: int = 180, rel_tol: float = 0.18) -> Dict[int, int]:
        if not widths:
            return {}
        indexed = sorted(enumerate(widths), key=lambda t: t[1])
        clusters: List[List[Tuple[int, int]]] = []
        for idx, w in indexed:
            if not clusters:
                clusters.append([(idx, w)])
                continue
            cur = clusters[-1]
            vals = [x[1] for x in cur]
            med = int(np.median(vals))

            last_w = cur[-1][1]
            tol = max(abs_tol, int(med * rel_tol), int(last_w * rel_tol))
            if abs(w - med) <= tol or abs(w - last_w) <= tol:
                cur.append((idx, w))
            else:
                clusters.append([(idx, w)])
        mapping: Dict[int, int] = {}
        for cur in clusters:
            vals = [x[1] for x in cur]
            med = float(np.median(vals))

            target = int(round(med / 100.0) * 100)
            if target < 1:
                target = max(1, int(round(med)))
            for idx, _ in cur:
                mapping[idx] = target
        return mapping

    def _normalize_page_width(self, im: np.ndarray, target_w: Optional[int] = None) -> np.ndarray:
        if im is None or im.size == 0:
            return im
        if target_w is None:
            target_w = self.max_output_width
        if not target_w or target_w <= 0:
            return im
        h, w = im.shape[:2]
        if w == target_w:
            return im
        cap = self.max_output_width
        if cap and cap > 0 and target_w > cap:
            target_w = cap
        scale = target_w / float(w)
        new_w = int(target_w)
        new_h = max(1, int(round(h * scale)))

        if scale < 0.95:
            interp = cv2.INTER_AREA
        elif scale > 1.05:
            interp = cv2.INTER_CUBIC
        else:
            interp = cv2.INTER_LINEAR
        out = cv2.resize(im, (new_w, new_h), interpolation=interp)
        return np.ascontiguousarray(out)

    def _find_safe_cut_y_smart(
        self,
        strip: np.ndarray,
        target_y: int,
        min_y: int,
        max_y: int,
        search_radius: int = 900,
        protected_ranges: Optional[List[Tuple[int, int]]] = None,
        spans_ready: bool = False,
    ) -> Optional[int]:
        #) — دیگر هیچ هوریستیکِ پیکسلی/Canny و هیچ OCRِ
# سبکِ جدیدِ برشِ امن (
# وسط نیست. فقط detector-v4-s: باکسهایِ متن در پنجرهٔ جستجو پیدا
# میشوند، با حاشیهٔ امن دورشان میشوند و برش داخلِ بزرگترین فاصلهٔ
# بی‌متن (نزدیکترین به target_y = وسطِ باندِ برش) زده
# میشود. متن هرگز برش نمیخورد.
        if strip is None or strip.size == 0 or self.det is None:
            return None
        try:
            ih, iw = strip.shape[:2]
            #) — حاشیهٔ دورِ
# برشِ نزدیکِ متن مجاز است (
# باکسها کوچک شد؛ مرزِ ممنوع همچنان خودِ باکسِ detector-v4-s
# است پس متن/حباب هرگز بریده نمیشود.
            clearance = max(12, int(round(iw * 0.02)))
            edge_margin = max(14, int(round(iw * 0.02)))
            y0 = max(int(min_y), int(target_y) - int(search_radius),
                     clearance + edge_margin)
            y1 = min(int(max_y), int(target_y) + int(search_radius),
                     ih - clearance - edge_margin)
            if y1 < y0:
                return None
# سرعتِ برش به سبکِ مرجع (ManhwaSlicer.
# راستیآزما/جابهجاییِ برش با تشخیصِ متن در مرجع): (۱) باندِ برش از
# قبل پوشش داده شده (کشِ دوطرفه یا اسکنِ زندهٔ _scan_band)
# → دیگر هیچ تشخیصِ دومی رویِ همان ناحیه اجرا نمیشود
# (قبلاً هر برش یک det.detectِ تمام‌عیارِ ~۱۵۰۰px با پاسِ
# چندمقیاسیِ کند اضافه میگرفت)؛ (۲) مسیرِ تشخیصِ زنده فقط
# پنجرهٔ کوچکِ دورِ هدف و fast=True (تک‌مقیاس — عینِ
# _scan_window)؛ (۳) خروجِ زودهنگامِ «هدف بی‌متن است» +
# جستجوی مارپیچِ ±۱px (پایینتر) — عینِ مرجع.
            spans: List[Tuple[int, int]] = []
            if spans_ready:
# spans از _scan_band از قبل حاشیهدار شدهاند (پدینگ =
# max(14, 2%·target_w) — همان مقیاسِ edge_margin چون عرضِ
# نوار = target_w)؛ دوباره پد نمیشوند.
                for top, bottom in (protected_ranges or []):
                    t, b = int(top), int(bottom)
                    if b > t:
                        spans.append((max(0, t), min(ih, b)))
            else:
                probe_half = max(250, int(round((y1 - y0) * 0.25)),
                                 clearance + edge_margin)
                wy0 = max(0, y0 - probe_half)
                wy1 = min(ih, y1 + probe_half)
                if wy1 - wy0 < 100:
                    return None
                band = strip[wy0:wy1]
                boxes = self.det.detect(band, fast=True)
                for box in boxes:
                    _, by1, _, by2 = box["rect"]
                    top = max(0, wy0 + int(by1) - edge_margin)
                    bot = min(ih, wy0 + int(by2) + 1 + edge_margin)
                    if bot > top:
                        spans.append((top, bot))
                for top, bottom in (protected_ranges or []):
                    spans.append((max(0, int(top) - edge_margin),
                                  min(ih, int(bottom) + 1 + edge_margin)))
            spans.sort()
            merged: List[Tuple[int, int]] = []
            for top, bot in spans:
                if merged and top <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], bot))
                else:
                    merged.append((top, bot))

            def _hit_text(_y: int) -> bool:
                return any(top <= _y <= bottom for top, bottom in merged)

# نقطهٔ هدف (وسطِ باند) خودش بی‌متن است؟ → همیشه بهترین برش
            if y0 <= int(target_y) <= y1 and not _hit_text(int(target_y)):
                return int(target_y)
# حداقلِ فاصلهٔ برش تا متن کوچک شد (کرانِ نزدیکِ متن)
            pad = max(14, int(round(iw * 0.015)))
            cands: List[int] = []
            if merged:
                first_top = merged[0][0] - pad
                if y0 <= first_top <= y1:
                    cands.append(first_top)
                for j in range(len(merged) - 1):
                    gap = merged[j + 1][0] - merged[j][1]
                    if gap >= 2 * pad:
                        mid = merged[j][1] + gap // 2
                        if y0 <= mid <= y1:
                            cands.append(mid)
                last_bot = merged[-1][1] + pad
                if y0 <= last_bot <= y1:
                    cands.append(last_bot)
            cands = [c for c in cands if not _hit_text(c)]
            if cands:
                return min(cands, key=lambda y: abs(y - target_y))
# جستجوی مارپیچِ ±۱px دورِ هدف (عینِ مرجع:
# VerifyAndAdjust — localCutY∓n): نزدیکترین ردیفِ بی‌متن به
# هدف، قبل از ردِ کلِ باند → فالبکِ اسکنِ مجددِ باندِ عقبتر
# کمتر لازم میشود.
            _t = int(target_y)
            for _d in range(1, max(y1 - _t, _t - y0) + 1):
                _yy = _t - _d
                if y0 <= _yy <= y1 and not _hit_text(_yy):
                    return _yy
                _yy = _t + _d
                if y0 <= _yy <= y1 and not _hit_text(_yy):
                    return _yy
            return None
        except Exception:
            return None

    def _repair_page_seams(self, image_files: List[str], work_dir: str) -> List[str]:

        if len(image_files) < 2 or not getattr(self, "repair_page_seams", True):
            return image_files
        if self.det is None:
            print("[!] ترمیم مرز متن انجام نشد: مدل تشخیص حباب در دسترس نیست.")
            return image_files

        os.makedirs(work_dir, exist_ok=True)
        result: List[str] = []
        group: List[np.ndarray] = []
        group_path = image_files[0]
        group_height = 0
        joined_count = 0

        def emit_group() -> None:
            if len(group) == 1:
                result.append(group_path)
                return

            width = group[0].shape[1]
            scale = (self.max_output_width / float(width)
                     if self.max_output_width else 1.0)
            fmt = (getattr(self, "img_format", None) or "webp").lstrip(".").lower()
            limit = {"webp": 16383, "jpg": 65500, "jpeg": 65500}.get(fmt)
            if limit and max(round(width * scale), round(group_height * scale)) > limit:
                raise RuntimeError("تصاویرِ دارای متن مشترک برای فرمت خروجی بیش از حد بلند شدند؛ "
                                   "--stitch-max-height 3600 یا --img-format png را انتخاب کنید. "
                                   "از وسط متن برش زده نشد.")
            path = os.path.join(work_dir, f"joined_{len(result) + 1:03d}.png")
            if not cv2.imwrite(path, np.vstack(group)):
                raise RuntimeError(f"ذخیرهٔ تصاویر متصل‌شده ناموفق بود: {path}")
            result.append(path)

        for path in image_files:
            image = MangaTranslator._imread_any(path)
            if image is None:
                raise RuntimeError(f"خواندن تصویر برای ترمیم مرز متن ناموفق بود: {path}")
            if not group:
                group = [image]
                group_height = len(image)
                continue
            previous = group[-1]
            width = min(previous.shape[1], image.shape[1])
            if self.max_output_width and self.max_output_width > 0:
                width = min(width, self.max_output_width)
            left = self._normalize_page_width(previous, target_w=width)
            right = self._normalize_page_width(image, target_w=width)
            context = max(320, int(round(width * 0.75)))
            tail, head = left[-context:], right[:context]
            preview = np.vstack([tail, head])
            seam = len(tail)
            try:
                boxes = self.det.detect(preview)
            except Exception as exc:
                raise RuntimeError("تشخیص متن در مرز دو تصویر ناموفق بود؛ "
                                   "برای جلوگیری از OCR متن نصفه، پردازش متوقف شد.") from exc
# عبورِ واقعی = جعبه‌ای که در «هر دو طرفِ» مرز
# تودهٔ قابل‌توجه دارد (≥۸px هر طرف). تلورانسِ قدیمیِ ±۲ هر
# جعبهٔ لبه‌چسب (متنِ بالایِ صفحهٔ بعد که مستطیلش چند px
# بالاتر از لبهٔ خودِ تصویر تشخیص میشود) را «متنِ ردشونده»
# میپنداشت → دو فایلِ کاملاً نامرتبط به هم میچسبیدند و
# دومی بی‌دلیل به عرضِ اولی ریسایز میشد (نمونهٔ واقعی:
# img2+img4 در تستِ وبِ سازنده — مرزشان کاملاً غیرمرتبط بود).
            crossing = any(box["rect"][1] <= seam - 8 and box["rect"][3] >= seam + 8
                           for box in boxes)
            if crossing:
                image = self._normalize_page_width(image, target_w=group[0].shape[1])
                if image.shape[1] != group[0].shape[1]:
                    raise RuntimeError("عرض تصاویر متصل‌شده یکسان نیست؛ ابتدا عرض ورودی‌ها را یکسان کنید.")
                if group_height + len(image) > 32000:
                    raise RuntimeError("زنجیرهٔ تصاویر دارای متن مشترک بیش از حد بلند شد؛ "
                                       "--stitch-max-height 3600 را فعال کنید.")
                group.append(image)
                group_height += len(image)
                joined_count += 1
                print(f"[*] متن/حباب روی مرز {os.path.basename(path)} ادامه دارد؛ "
                      "دو بخش پیش از OCR متصل شدند.")
            else:
                emit_group()
                group, group_path, group_height = [image], path, len(image)
        emit_group()
        if joined_count:
            print(f"[*] ترمیم خودکار مرز متن: {len(image_files)} تصویر → {len(result)} تصویر؛ "
                  "بدون برش مجدد ارتفاع.")
        return result

    def _stitch_pages_for_efficiency(self, image_files: List[str], work_dir: str) -> List[str]:

        if not image_files:
            return image_files
        if self.stitch_max_height <= 0:
            return self._repair_page_seams(image_files, work_dir)

        work_h = int(self.stitch_max_height)

        soft_h = int(getattr(self, "stitch_short_threshold", 0) or 0)
        if soft_h > work_h:
            work_h = soft_h
        lookahead = max(512, min(2000, work_h // 2))

        os.makedirs(work_dir, exist_ok=True)
        result: List[str] = []
        start_idx = 0

        if self.det is None and (len(image_files) > 1 or not self.stitch_keep_first):
# برشِ امن فقط با detector-v4-s_int8.onnx (سبکِ
# جدید؛ OCR دیگر نقشی ندارد). بدونِ detector برشِ
# امنِ بی‌متن ممکن نیست → خطا، نه برشِ کور.
            raise RuntimeError("برش امن به detector-v4-s نیاز دارد؛ مدل تشخیص بارگذاری نشده است. "
                               "برای حفظ فایل‌های اصلی --stitch-max-height 0 را بزنید.")

        keep_first = bool(self.stitch_keep_first)
        current_protected: List[Tuple[int, int]] = []
        if keep_first and len(image_files) > 1:

            first = MangaTranslator._imread_any(image_files[0])
            second = MangaTranslator._imread_any(image_files[1])
            if first is None or second is None:
# به‌جایِ ریختنِ کلِ کار، حدِ امن را می‌گیریم —
# صفحهٔ اول جدا می‌ماند و بدونِ چسباندن ادامه می‌دهیم.
                print("[!] خواندن دو تصویر اول برای بررسیِ مرز امن نشد؛ "
                      "صفحهٔ اول جدا نگه داشته می‌شود و ادامه می‌دهیم.")
            else:
                seam_w = min(first.shape[1], second.shape[1])
                if self.max_output_width and self.max_output_width > 0:
                    seam_w = min(seam_w, self.max_output_width)
                first = self._normalize_page_width(first, target_w=seam_w)
                second = self._normalize_page_width(second, target_w=seam_w)
                context = max(320, int(round(seam_w * 0.75)))
                tail, head = first[-context:], second[:context]
                preview = np.vstack([tail, head])
                seam_y = len(tail)
# حاشیهٔ دورِ باکسها کوچک (برشِ نزدیکِ متن مجاز)
                padding = max(14, int(round(seam_w * 0.02)))
                try:
# مرزِ صفحهٔ اول هم فقط با detector-v4-s
                    protected = [
                        (box["rect"][1] - padding, box["rect"][3] + padding)
                        for box in self.det.detect(preview)
                    ]
                except Exception as exc:
                    raise RuntimeError("بررسی مرز صفحهٔ اول ناموفق بود؛ برای جلوگیری از قطع متن "
                                       "صفحه جدا نشد.") from exc
                keep_first = self._find_safe_cut_y_smart(
                    preview, seam_y, seam_y, seam_y, protected_ranges=protected,
# protected همین الان از detect(preview) ساخته
# شد و کلِ پنجره را پوشش میدهد؛ تشخیصِ دوم حذف شد
                    spans_ready=True,
                ) is not None
                if not keep_first:
                    current_protected = [
                        (top + len(first) - seam_y, bottom + len(first) - seam_y)
                        for top, bottom in protected
                    ]
                    print("[*] مرز صفحهٔ اول امن نیست؛ برای حفظ متنِ ادامه‌دار به صفحهٔ بعد چسبانده می‌شود.")
                del first, second, tail, head, preview

        if keep_first:
            ext_s = "." + (getattr(self, "img_format", None) or "webp").lstrip(".")
            if ext_s == ".jpeg":
                ext_s = ".jpg"
            first_out = os.path.join(work_dir, f"strip_000_cover{ext_s}")
            shutil.copy2(image_files[0], first_out)
            result.append(first_out)
            start_idx = 1
            if start_idx >= len(image_files):
                return result

        sample_widths = []
        for f in image_files[start_idx:start_idx + min(8, len(image_files) - start_idx)]:
            im = MangaTranslator._imread_any(f)
            if im is None:
                raise RuntimeError(f"خواندن تصویر ناموفق بود؛ صفحه حذف نشد: {f}")
            sample_widths.append(im.shape[1])
        sample_widths.sort()
        target_w = sample_widths[len(sample_widths) // 2]
        if current_protected:

            scale = target_w / float(seam_w)
            current_protected = [
                (int(np.floor(top * scale)) - 2, int(np.ceil(bottom * scale)) + 2)
                for top, bottom in current_protected
            ]

        strip_i = 0
        current_pages: List[np.ndarray] = []
        current_h = 0
        min_strip = max(1, int(work_h * 0.65))
        scan_from = 0

# برش امن دوطرفه ──
# نقشهٔ صفحه‌ها در مختصات «عمرِ نوار» (هرگز ری‌بیس نمی‌شود) + کشِ
# پیش‌تشخیص. دو کارگرِ تشخیص فصل را از دو سر می‌خورند: یکی از صفحهٔ
# اول به آخر، یکی از صفحهٔ آخر به اول (خواستهٔ کاربر) → جعبه‌های
# حباب آماده‌اند و حلقهٔ برش منتظر تشخیصِ زنده نمی‌ماند.
        _page_spans: List[List[int]] = []   # [abs_page_idx, y0_lifetime]
        _life = [0, 0]                      # [life_h, life_off]
        _pre_boxes: Dict[int, Tuple[float, List[Tuple[int, int]], bool]] = {}
        _pre_lock = threading.Lock()
        _pre_pages = list(range(start_idx, len(image_files)))

        def _pre_detect_page(_idx: int) -> None:
            try:
                _im = cv2.imread(image_files[_idx])
                if _im is None:
                    with _pre_lock:
                        _pre_boxes[_idx] = (0.0, [], True)
                    return
                _pw = float(_im.shape[1])
                _blank = False
                try:
                    _g = (cv2.cvtColor(_im, cv2.COLOR_BGR2GRAY)
                          if _im.ndim == 3 else _im)
                    if int(_g.min()) >= 205:
                        _blank = True
                except Exception:
                    pass
                _bx: List[Tuple[int, int]] = []
                if not _blank:
# پیش‌تشخیصِ برشِ امن فقط با detector-v4-s
                    try:
                        for _box in self.det.detect(_im, fast=True):
                            _r = _box.get("rect")
                            if not _r:
                                continue
                            _bx.append((int(_r[1]), int(_r[3])))
                    except Exception:
                        _bx = []
                with _pre_lock:
                    _pre_boxes[_idx] = (_pw, _bx, _blank)
            except Exception:
                with _pre_lock:
                    _pre_boxes.setdefault(_idx, (0.0, [], True))

        _pre_threads: List[threading.Thread] = []
        if _pre_pages and self.det is not None:
            try:
                from collections import deque as _deque
                _dq = _deque(_pre_pages)
                _pre_total = len(_pre_pages)
                _pre_prog = {"جلو": 0, "عقب": 0}
                _pre_step = max(3, _pre_total // 6)
                _pre_t0 = time.time()
                _pre_done_flag = {"d": False}
                try:
                    _n_pre = 2 if _on_android() else max(2, min(4, (os.cpu_count() or 2)))
                except Exception:
                    _n_pre = 2
                _n_pre = max(1, min(_n_pre, len(_pre_pages)))

                def _pre_worker(_from_right: bool) -> None:
                    _tag = "عقب" if _from_right else "جلو"
                    while True:
                        try:
                            _idx = _dq.pop() if _from_right else _dq.popleft()
                        except IndexError:
                            return
                        _pre_detect_page(_idx)
# پیشرفتِ قابلِ دیدنِ دو سر: کاربر باید
# در لاگ ببیند که یک رشته از صفحهٔ اول و همزمان
# رشتهٔ دیگر از صفحهٔ آخر جلو میرود
                        _show = _fin = False
                        with _pre_lock:
                            _pre_prog[_tag] += 1
                            _show = (_pre_total >= 6
                                     and _pre_prog[_tag] % _pre_step == 0)
                            if (not _pre_done_flag["d"]
                                    and (_pre_prog["جلو"] + _pre_prog["عقب"])
                                    >= _pre_total):
                                _pre_done_flag["d"] = True
                                _fin = True
                        if _show:
                            print(f"    [برش {_tag}] صفحهٔ {_idx + 1} از "
                                  f"{_pre_total} کش شد")
                        if _fin:
                            print(f"[✓] برش امن دوطرفه: هر {_pre_total} صفحه "
                                  f"از دو طرف کش شد "
                                  f"({time.time() - _pre_t0:.1f}s)")

                for _k in range(_n_pre):
                    _t = threading.Thread(
                        target=_pre_worker, args=(bool(_k % 2),), daemon=True)
                    _t.start()
                    _pre_threads.append(_t)
                print(f"[*] برش امن دوطرفه (RT-DETR / detector-v4-s): {_n_pre} کارگر تشخیص "
                      f"— یکی از صفحهٔ اول به آخر، یکی از آخر به اول")
            except Exception:
                _pre_threads = []

        def _pre_wait(_idx: int, _timeout: float = 120.0) -> bool:
            _t0 = time.time()
            while time.time() < _t0 + _timeout:
                with _pre_lock:
                    if _idx in _pre_boxes:
                        return True
                if _pre_threads and not any(_t.is_alive() for _t in _pre_threads):
                    break
                time.sleep(0.04)
            with _pre_lock:
                return _idx in _pre_boxes
        print(
            f"[*] چسباندن streaming + برش امن: هدف={work_h}px | "
            f"نگاه به جلو={lookahead}px | ارتفاع هدف است، نه برش اجباری"
        )

        def _stack_pages(pages: List[np.ndarray]) -> np.ndarray:
            return np.vstack(pages) if len(pages) > 1 else pages[0]

        def _emit_array(arr: np.ndarray, label: str = "") -> None:
            nonlocal strip_i
            if arr is None or arr.size == 0:
                return
            ext_s = "." + (getattr(self, "img_format", None) or "webp").lstrip(".")
            if ext_s == ".jpeg":
                ext_s = ".jpg"
            out_path = os.path.join(work_dir, f"strip_{strip_i + 1:03d}{ext_s}")
            scale = (self.max_output_width / float(arr.shape[1])
                     if getattr(self, "max_output_width", 0) else 1.0)
            encoded_size = [max(1, int(round(d * scale))) for d in arr.shape[:2]]
            codec_limit = {".webp": 16383, ".jpg": 65500}.get(ext_s)
            if codec_limit and max(encoded_size) > codec_limit:
                raise RuntimeError("نوار امن برای این فرمت بیش از حد بزرگ است؛ "
                                   "با --img-format png دوباره اجرا کنید. "
                                   "برای رعایت محدودیت فرمت از وسط متن برش زده نشد.")
            self._write_image(arr, out_path)
            result.append(out_path)
            print(f"    [+] نوار {strip_i + 1}: {label} ({arr.shape[0]}px)")
            strip_i += 1

        def _cut_and_emit(final: bool = False) -> None:
            nonlocal current_pages, current_h, current_protected, scan_from
            if not current_pages or (not final and current_h < work_h + lookahead):
                return

            strip = _stack_pages(current_pages)
            ih = int(strip.shape[0])
            protected = list(current_protected)
# برشِ نزدیکِ متن مجاز است؛ حاشیهٔ دورِ باکسها کوچک شد
            padding = max(14, int(round(target_w * 0.02)))

# پرش از پنجره‌های خالی (کاغذ سفید) + تشخیص موازی +
# fast-mode (بدون پاس دوم multi_scale) — برش امن چند برابر سریع‌تر.
            def _scan_window(_top: int, _limit: int) -> List[Tuple[int, int]]:
                _bottom = min(_limit, _top + 1680)
# خواندن از کش دوطرفه (اگر صفحه‌ها کش شدند) ──
                try:
                    if _page_spans and _pre_threads:
                        _ih_now = int(strip.shape[0])
                        _end_cur = _life[0] - _life[1]
                        _out_c: List[Tuple[int, int]] = []
                        _have_all = True
                        for _j in range(len(_page_spans)):
                            _pid, _y0 = _page_spans[_j]
                            _seg_a = _y0 - _life[1]
                            _y0n = _page_spans[_j + 1][1] \
                                if _j + 1 < len(_page_spans) else _life[0]
                            _seg_b = _y0n - _life[1]
                            if _seg_b <= _top or _seg_a >= _bottom:
                                continue
                            if not _pre_wait(_pid):
                                _have_all = False
                                break
                            with _pre_lock:
                                _ent = _pre_boxes.get(_pid)
                            if _ent is None or _ent[0] <= 0:
                                _have_all = False
                                break
                            _pw, _bx, _blank = _ent
                            if _blank:
                                continue
                            _sc = target_w / _pw
                            _base = _seg_a
                            for (_by1, _by2) in _bx:
                                _sy1 = _base + int(_by1 * _sc)
                                _sy2 = _base + int(_by2 * _sc)
                                if _sy2 < _top or _sy1 > _bottom:
                                    continue
                                _out_c.append((_sy1, _sy2))
                        if _have_all:
                            return [(_sy1 - padding, _sy2 + padding)
                                    for (_sy1, _sy2) in _out_c]
                except Exception:
                    pass
                _win = strip[_top:_bottom]
                try:
                    _g = (cv2.cvtColor(_win, cv2.COLOR_BGR2GRAY)
                          if _win.ndim == 3 else _win)
                    if int(_g.min()) >= 205:
                        return []  # پنجرهٔ کاملاً خالی — حباب/متنی ندارد
                except Exception:
                    pass
                _out: List[Tuple[int, int]] = []
# پنجره‌هایِ اسکنِ برشِ امن فقط با detector-v4-s
                try:
                    for box in self.det.detect(_win, fast=True):
                        _, y1, _, y2 = box["rect"]
                        _out.append((_top + y1 - padding, _top + y2 + padding))
                except Exception as exc:
                    raise RuntimeError("تشخیص detector-v4-s برای برش امن ناموفق بود؛ "
                                       "برش اجباری انجام نشد.") from exc
                return _out

            # + «برش امن ک دفعه اول انجام میده سریعتر
# اسکنِ «فقطِ باندِ برش» (
# باشه»): قبلاً قبلِ اولین برش کلِ نوار تا سقفِ کاندیدهایِ برش
# اسکن میشد (برایِ نوارِ ~۲۰هزارpx = ~۱۴ پنجرهٔ detector)؛ حالا
# فقط پنجرههایِ همان باندِ ۷۰۰۰–۸۰۰۰ (۱–۲ پنجره، بیشترشان از
# کشِ دوطرفه) — اولین برش چندبرابر سریعتر. باکسهایِ بیرونِ باند
# را خودِ _find_safe_cut_y_smart زنده پیدا میکند؛ امنیتِ برش
# دستنخورده میماند.
            def _scan_band(_band_top: int, _band_bot: int) -> None:
                nonlocal scan_from
                _s_lo = max(0, _band_top - 520)
                _s_hi = min(ih, _band_bot + 480)
                if _s_hi <= scan_from or _s_hi - _s_lo < 100:
                    return
                _win_starts = list(range(max(scan_from - 520, _s_lo), _s_hi, 1160))
                if not _win_starts:
                    return
                if _win_starts[-1] + 1680 < _s_hi:
                    _win_starts.append(max(_win_starts[-1] + 1160,
                                           _s_hi - 1680))
                _scan_tw = 1
                try:
                    if len(_win_starts) > 1:
                        _scan_tw = (2 if _on_android()
                                    else max(2, min(3, (os.cpu_count() or 2) // 2)))
                except Exception:
                    _scan_tw = 1
                _scan_tw = max(1, min(_scan_tw, len(_win_starts)))
                if _scan_tw > 1:
                    with ThreadPoolExecutor(max_workers=_scan_tw) as _sex:
                        for _res in _sex.map(
                                lambda _t: _scan_window(_t, _s_hi), _win_starts):
                            protected.extend(_res)
                else:
                    for _t in _win_starts:
                        protected.extend(_scan_window(_t, _s_hi))
                scan_from = max(scan_from, _s_hi)

            offset = 0
            while ih - offset >= work_h + min_strip:
                max_cut = ih - max(min_strip, lookahead if not final else 0)
# باندِ برشِ امن = ۷۰۰۰–۸۰۰۰ — هدف = وسطِ باند (۷۵۰۰)؛ برش فقط جایی که
# detector-v4-s هیچ متنی نبیند.
                _band_lo = offset + max(0, int(work_h) - 1000)
                _band_hi = offset + int(work_h)
                _band_mid = (_band_lo + _band_hi) // 2
                cut_y = None
                if min(_band_hi, max_cut) >= _band_lo:
# فقطِ پنجرههایِ همین باند اسکن میشود
                    _scan_band(_band_lo, min(_band_hi, max_cut))
                    cut_y = self._find_safe_cut_y_smart(
                        strip, _band_mid, _band_lo, min(_band_hi, max_cut),
                        search_radius=max(250, (_band_hi - _band_lo) // 2),
                        protected_ranges=protected,
# باند بالا همین الان با _scan_band
# اسکن شد؛ تشخیصِ دوم لازم نیست (سبکِ مرجع)
                        spans_ready=True,
                    )
                if cut_y is None:
# فالبکِ فقط-به-عقب: اگر کلِ باندِ
# ۷۰۰۰–۸۰۰۰ پُر از متن بود، نزدیکترین جایِ بی‌متنِ
# «قبل از» باند گرفته میشود. سقفِ برش هرگز از work_h
# (۸۰۰۰) بالاتر نمیرود — رفتنِ به ۹۰۰۰ (فالبکِ
# رو-به-جلوِ قدیمی) کلاً حذف شد؛ متن هم برش نمیخورد.
                    _fb_hi = min(_band_lo, max_cut)
                    _fb_lo = offset + max(120, int(work_h) // 3)
                    if _fb_hi - _fb_lo >= 200:
                        _scan_band(_fb_lo, _fb_hi)
                        cut_y = self._find_safe_cut_y_smart(
                            strip, _fb_hi, _fb_lo, _fb_hi,
                            search_radius=max(200, _fb_hi - _fb_lo),
                            protected_ranges=protected,
                            spans_ready=True,  # همین الان با _scan_band اسکن شد
                        )
                if cut_y is None:
                    break
                _emit_array(strip[offset:cut_y], f"برش بررسی‌شده y={cut_y}")
                offset = cut_y

            current_h = ih - offset
            current_protected = [(max(0, top - offset), bottom - offset)
                                 for top, bottom in current_protected if bottom >= offset]
            scan_from = max(0, scan_from - offset)
# مختصات عمرِ نوار جلو می‌رود + صفحه‌های کاملاً مصرف‌شده حذف
            _life[1] += offset
            while len(_page_spans) > 1 and (_page_spans[1][1] - _life[1]) <= 0:
                _page_spans.pop(0)
            if final:
                label = ("پایان فصل" if current_h <= work_h + min_strip
                         else "بزرگ‌تر از هدف: محل برش امن پیدا نشد")
                _emit_array(strip[offset:], label)
                current_pages, current_h = [], 0
            else:

                current_pages = [strip[offset:].copy()]
                if current_h > max(32000, work_h * 8):
                    raise RuntimeError("نوار بدون محل برش امن بیش از حد بلند شد؛ "
                                       "برای جلوگیری از قطع متن، پردازش متوقف شد.")

        for _abs_i, f in enumerate(image_files[start_idx:], start=start_idx):
            im = MangaTranslator._imread_any(f)
            if im is None:
                raise RuntimeError(f"خواندن تصویر ناموفق بود؛ صفحه حذف نشد: {f}")
            h, w = im.shape[:2]
# دستهٔ ترکیبی (مثلاً صفحهٔ ۱۸۰۰px + نوارِ ۸۰۰px):
# صفحه‌ای که عرضش خیلی با عرضِ گروهِ فعلی فرق دارد دیگر با
# کوچک/بزرگ‌سازی داخلِ همان نوار له نمی‌شود — متنِ ریز
# (مثلِ متنِ کنارِ حبابِ بالا-چپِ 01.jpg) ناخوانا می‌شد و
# تشخیص/OCR در حالتِ دسته‌ای از دست می‌رفت. به‌جایش گروهِ
# فعلی جدا می‌شود و صفحه در نوارِ خودش با عرضِ اصلی پردازش
# می‌شود = استخراجِ دقیقاً مثلِ حالتِ تکی.
            if (target_w > 0
                    and abs(w - target_w) > max(180, int(target_w * 0.18))):
                if current_pages:
                    _cut_and_emit(final=True)
                    current_protected = []
                    scan_from = 0
                    _page_spans.clear()
                    _life[0] = 0
                    _life[1] = 0
                print(f"[*] عرضِ {w}px با گروهِ {target_w}px فرق دارد → "
                      f"نوارِ جدا؛ استخراجِ دقیقاً تک-حالتی (بدونِ له‌شدن)")
                target_w = w
            if w != target_w and target_w > 0:

                new_h = max(1, int(round(h * (target_w / float(w)))))
                interp = cv2.INTER_AREA if target_w < w else cv2.INTER_CUBIC
                im = cv2.resize(im, (target_w, new_h), interpolation=interp)
                h, w = im.shape[:2]
            current_pages.append(im)
            _page_spans.append([_abs_i, _life[0]])
            _life[0] += h
            current_h += h
            _cut_and_emit()

        _cut_and_emit(final=True)

        print(
            f"[*] چسباندن صفحات: {len(image_files)} صفحه → {len(result)} نوار "
            f"(هدف={work_h}px / نگاه به جلو={lookahead}px"
            f"{'، صفحهٔ اول جدا (مرز امن)' if keep_first else ''})"
        )
        return result if result else image_files
