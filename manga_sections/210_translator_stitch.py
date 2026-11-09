# BUILD-STRIP-START
# ─────────────────────────────────────────────────────────────
# ⚠️ MangaTranslator (۱۲ از ۱۳) — دوختِ صفحهها: عرضِ یکنواخت، برشِ امن، تعمیرِ درزها، _stitch_pages_for_efficiency
# این فایل «قطعهای از بدنهٔ کلاس MangaTranslator» است و بهتنهایی
# اجرا نمیشود — scripts/build_manga.py این محتوا را بههمان ترتیبِ
# شمارهٔ فایل، داخلِ کلاس در manga.py میچسباند. کلاسِ پوششیِ زیر فقط
# برای معتبر بودنِ سینتکسِ این فایلِ تکی است و موقعِ بیلد حذف میشود.
class _MangaTranslatorBody_210:
# BUILD-STRIP-END
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
        # v1.14.163 — سبکِ جدیدِ برشِ امن (دستورِ سازنده: «بجایِ استفاده
        # از ocr واسهٔ پیدا کردنِ برشِ امن از detector-v4-s_int8.onnx
        # استفاده کنی») — دیگر هیچ هوریستیکِ پیکسلی/Canny و هیچ OCRِ
        # وسط نیست. فقط detector-v4-s: باکسهایِ متن در پنجرهٔ جستجو پیدا
        # میشوند، با حاشیهٔ امن دورشان میشوند و برش داخلِ بزرگترین فاصلهٔ
        # بی‌متن (نزدیکترین به target_y = وسطِ باندِ برش) زده
        # میشود. متن هرگز برش نمیخورد.
        if strip is None or strip.size == 0 or self.det is None:
            return None
        try:
            ih, iw = strip.shape[:2]
            # v1.14.203 — برشِ نزدیکِ متن مجاز است (دستورِ سازنده: «نزدیکِ
            # متن ببرع اشکال نداره فقط نباید متن ببرع حبابو») — حاشیهٔ دورِ
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
            # v1.14.246 — سرعتِ برش به سبکِ مرجع (ManhwaSlicer.
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
            # v1.14.203 — حداقلِ فاصلهٔ برش تا متن کوچک شد (کرانِ نزدیکِ متن)
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
            # v1.14.246 — جستجوی مارپیچِ ±۱px دورِ هدف (عینِ مرجع:
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
            # v1.14.211 — عبورِ واقعی = جعبه‌ای که در «هر دو طرفِ» مرز
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
            # v1.14.163 — برشِ امن فقط با detector-v4-s_int8.onnx (سبکِ
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
                # v1.14.56: به‌جایِ ریختنِ کلِ کار، حدِ امن را می‌گیریم —
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
                # v1.14.203 — حاشیهٔ دورِ باکسها کوچک (برشِ نزدیکِ متن مجاز)
                padding = max(14, int(round(seam_w * 0.02)))
                try:
                    # v1.14.163 — مرزِ صفحهٔ اول هم فقط با detector-v4-s
                    protected = [
                        (box["rect"][1] - padding, box["rect"][3] + padding)
                        for box in self.det.detect(preview)
                    ]
                except Exception as exc:
                    raise RuntimeError("بررسی مرز صفحهٔ اول ناموفق بود؛ برای جلوگیری از قطع متن "
                                       "صفحه جدا نشد.") from exc
                keep_first = self._find_safe_cut_y_smart(
                    preview, seam_y, seam_y, seam_y, protected_ranges=protected,
                    # v1.14.246 — protected همین الان از detect(preview) ساخته
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

        # ── v1.14.31: برش امن دوطرفه ──
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
                    # v1.14.163 — پیش‌تشخیصِ برشِ امن فقط با detector-v4-s
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
                        # v1.14.162 — پیشرفتِ قابلِ دیدنِ دو سر: کاربر باید
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
            # v1.14.203 — برشِ نزدیکِ متن مجاز است؛ حاشیهٔ دورِ باکسها کوچک شد
            padding = max(14, int(round(target_w * 0.02)))

            # v1.14.30: پرش از پنجره‌های خالی (کاغذ سفید) + تشخیص موازی +
            # fast-mode (بدون پاس دوم multi_scale) — برش امن چند برابر سریع‌تر.
            def _scan_window(_top: int, _limit: int) -> List[Tuple[int, int]]:
                _bottom = min(_limit, _top + 1680)
                # ── v1.14.31: خواندن از کش دوطرفه (اگر صفحه‌ها کش شدند) ──
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
                # v1.14.163 — پنجره‌هایِ اسکنِ برشِ امن فقط با detector-v4-s
                try:
                    for box in self.det.detect(_win, fast=True):
                        _, y1, _, y2 = box["rect"]
                        _out.append((_top + y1 - padding, _top + y2 + padding))
                except Exception as exc:
                    raise RuntimeError("تشخیص detector-v4-s برای برش امن ناموفق بود؛ "
                                       "برش اجباری انجام نشد.") from exc
                return _out

            # v1.14.203 — اسکنِ «فقطِ باندِ برش» (دستورِ سازنده: «فقط ببین
            # ۷۰۰۰ تا ۸۰۰۰ بخونه» + «برش امن ک دفعه اول انجام میده سریعتر
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
                # v1.14.166 — باندِ برشِ امن = ۷۰۰۰–۸۰۰۰ (دستورِ سازنده:
                # «برشِ امن گفتم ببین 7000 تا 8000 بررسی کنه پس چرا میره
                # ۹۰۰0؛ نباید وسطِ متن برش بزنه باید با detector-v4-s
                # برش بزنه»). هدف = وسطِ باند (۷۵۰۰)؛ برش فقط جایی که
                # detector-v4-s هیچ متنی نبیند.
                _band_lo = offset + max(0, int(work_h) - 1000)
                _band_hi = offset + int(work_h)
                _band_mid = (_band_lo + _band_hi) // 2
                cut_y = None
                if min(_band_hi, max_cut) >= _band_lo:
                    # v1.14.203 — فقطِ پنجرههایِ همین باند اسکن میشود
                    _scan_band(_band_lo, min(_band_hi, max_cut))
                    cut_y = self._find_safe_cut_y_smart(
                        strip, _band_mid, _band_lo, min(_band_hi, max_cut),
                        search_radius=max(250, (_band_hi - _band_lo) // 2),
                        protected_ranges=protected,
                        # v1.14.246 — باند بالا همین الان با _scan_band
                        # اسکن شد؛ تشخیصِ دوم لازم نیست (سبکِ مرجع)
                        spans_ready=True,
                    )
                if cut_y is None:
                    # v1.14.166 — فالبکِ فقط-به-عقب: اگر کلِ باندِ
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
                            spans_ready=True,  # v1.14.246 — همین الان با _scan_band اسکن شد
                        )
                if cut_y is None:
                    break
                _emit_array(strip[offset:cut_y], f"برش بررسی‌شده y={cut_y}")
                offset = cut_y

            current_h = ih - offset
            current_protected = [(max(0, top - offset), bottom - offset)
                                 for top, bottom in current_protected if bottom >= offset]
            scan_from = max(0, scan_from - offset)
            # v1.14.31: مختصات عمرِ نوار جلو می‌رود + صفحه‌های کاملاً مصرف‌شده حذف
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
            # v1.14.86 — دستهٔ ترکیبی (مثلاً صفحهٔ ۱۸۰۰px + نوارِ ۸۰۰px):
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

