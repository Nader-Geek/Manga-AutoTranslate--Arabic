# BUILD-STRIP-START
# ─────────────────────────────────────────────────────────────
# ⚠️ MangaTranslator (۵ از ۱۳) — پاکسازیِ صفحه: _clean_image_page (۲۶۶۸ خط) + جاروهای باقیمانده
# این فایل «قطعهای از بدنهٔ کلاس MangaTranslator» است و بهتنهایی
# اجرا نمیشود — scripts/build_manga.py این محتوا را بههمان ترتیبِ
# شمارهٔ فایل، داخلِ کلاس در manga.py میچسباند. کلاسِ پوششیِ زیر فقط
# برای معتبر بودنِ سینتکسِ این فایلِ تکی است و موقعِ بیلد حذف میشود.
class _MangaTranslatorBody_140:
# BUILD-STRIP-END
    def _clean_image_page(self, image: np.ndarray, regions: List[TextRegion]) -> np.ndarray:
        # v1.14.70 — نواحیِ صفحه نگه داشته می‌شوند تا «کامپوزِ دو-عکسی»
        # بتواند نوارهایِ خط‌به‌خط (اندازهٔ دقیقِ متن) را بسازد.
        self._page_regions = list(regions or [])
        # v1.14.230 — «متنِ فقط عدد/نماد دست‌نخورده بماند» (دستورِ
        # سازنده: «ولی اگ میشد .... نره ترجمه و همچنین نباید پاک کنه
        # هیچ دستی بهش نزنه»): ناحیه‌ای که متنِ OCRشدهاش «هیچ حرفی»
        # ندارد ('....'، '123124'، '[] ,./???!?~') نه ترجمه میشود
        # (فیلترِ ۲۲۹ در translate_regions) و نه پاکسازی — هنر/عدتِ
        # صفحه دست‌نخورده میماند. ناحیهٔ «جوهرِ بی‌متن» (ocr_empty:
        # حبابِ واقعی که OCR نخواند) همچنان پاک میشود — متنِ واقعی
        # گم نشود.
        _nt230 = [r for r in (regions or [])
                  if getattr(r, "no_touch230", False)]
        if _nt230:
            regions = [r for r in (regions or [])
                       if not getattr(r, "no_touch230", False)]
            self._page_regions = list(regions)
            try:
                print(f"    [*] {len(_nt230)} ناحیهٔ فقط عدد/نماد "
                      f"→ دست‌نخورده (نه ترجمه، نه پاکسازی)")
            except Exception:
                pass
        if not regions:
            return image.copy()
        # v1.14.185 — اندروید: پروفایلرِ سبکِ مرحله‌هایِ پاکسازی — هر
        # مرحله چند ثانیه میگیرد را در لاگ نشان میدهد تا کندیِ «پاکسازیِ
        # کلی یک کم طول میکشه» دقیق پیدا شود. PC هیچ چیزی چاپ نمیکند.
        _tc185 = time.time()

        def _stage185(tag: str) -> None:
            try:
                if _on_android():
                    print(f"  [⏱] پاکسازی | {tag} | "
                          f"{time.time() - _tc185:.1f}s", flush=True)
            except Exception:
                pass

        mask = self._build_text_mask(image, regions)
        if not np.any(mask):
            return image.copy()
        self._mem_trim()  # v1.14.48c: پیکِ ماسک‌سازی به OS برگردد

        # v1.14.48: دیوارِ حباب/کادرِ پنل را از ماسکِ فعال جدا کن —
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
        # v1.14.73 — نقشهٔ «دیوارِ ریز»: دیوارِ حباب‌هایِ کوچک (<۶۰px —
        # مثلِ YEP!) هم مثلِ بزرگ‌ها در کامپوز محافظت می‌شود تا هرگز
        # پیکسلِ آن از عکسِ پاک‌شده به خروجی نرود (حبابِ نازک نشکند).
        try:
            self._page_wall_band = self._structural_protect_mask(
                image, regions, min_len=16, near_px=13)
        except Exception:
            self._page_wall_band = None
        # v1.14.186 — پایانِ اعتبارِ کشِ MANGA_PROT_CACHE: هرگز کهنه نمیماند
        self._spm_cache = None
        # v1.14.206n — protect دیگر از ماسکِ «فعال» کم نمیشود: عکسِ اول
        # (donor) طبقِ سبکِ خودِ سازنده حقِ «بیشتر پاک کردن» دارد
        # («اشکال نداره حباب خراب شه یا بیشتر پاک شه») — چون کامپوزِ
        # دو-عکسی (206m) و پولیشِ حلقه، ساختار را هرگز از عکسِ دوم
        # منتقل نمیکنند و پولیش هم protect را از نمونهٔ حلقه بیرون
        # میگذارد. قبلاً حذفِ protect از ماسک، پرِ LaMa را وادار میکرد
        # دورِ قابِ رنگی بچرخد و رنگِ قاب را داخلِ متن میکشید (لکهٔ
        # سبزِ حبابهایِ ۳/۴ در up0822).

        # v1.14.66 — هالهٔ گلوِ اشباعِ دورِ متن (لکهٔ قرمزِ کارتِ عنوان)
        # قبل از اسنپ‌شاتِ کامپوز و همهٔ مسیرهایِ پاکسازی به ماسک می‌چسبد
        # تا نوارِ ترکیبِ دو-عکسی هم هاله را بپوشاند (خروجی = بدونِ لکه).
        try:
            _t66 = time.time()
            _n66 = int((mask > 0).sum())
            _mask66 = MangaTranslator._absorb_text_halo(image, mask)
            if _mask66 is not mask:
                mask = _mask66
                if self.debug:
                    print(f"  [+]هالهٔ گلو → ماسک "
                          f"(+{int((mask > 0).sum()) - _n66}px, "
                          f"{time.time() - _t66:.2f}s)", flush=True)
        except Exception:
            pass
        _stage185("ماسک+هاله")

        # v1.14.63 — ماسکِ کامپوزِ «خط‌به‌خط»: نسخهٔ خامِ ماسکِ متنِ همین
        # لحظه (بعدِ کارو/پروتکت، «قبلِ» کِیلِ پرکننده‌هایِ فوری و «قبلِ»
        # توپرشدنِ بلوک‌هایِ تیره) برایِ ترکیبِ دو-عکسی نگه داشته می‌شود.
        # طبقِ حرفِ تازهٔ کاربر: «به اندازهٔ متنِ اصلی برش بخوره بذاره رو
        # عکسِ اصلی — چرا کلِ حباب رو منتقل می‌کنی؟» → کامپوز فقط نوارِ
        # متن را می‌گیرد، نه کلِ حباب/محفظه/پیکسل‌هایِ تغییرکردهٔ پراکنده.
        self._compose_text_mask = mask.copy()

        # v1.14.74 — درخواستِ نهاییِ کاربر: «عکسِ اول متن‌هاش کامل بپاکه —
        # اشکال نداره حباب خراب شه یا بیشتر پاک شه. بعد خط به خط برش
        # بخوره به عکسِ دوم بچسونه جایِ متن‌هایِ اصلی‌شون. عکسِ دوم باید
        # خروجی بشه» + «چرا کل حباب انتقال میدی؟ حروف به حروف برش بزنه».
        # ماسکِ donor = فقط نوارِ متن + پدِ سخاوتمندانه (+ نجاتِ جوهرِ
        # جا‌مانده). «کلِ داخلِ حباب» (v1.14.71/73) حذف شد: LaMa داخلِ
        # حبابِ رنگی را خمیرِ خاکستری می‌کرد («لگه») و روی گوشی کند بود.
        try:
            mask = self._expand_donor_text_strips(
                image, mask, regions)
        except Exception:
            pass
        # v1.14.74 — donor دیگر اینتریور ندارد → هیچ ناحیه‌ای از پرکردنِ
        # فوری مستثنا نیست (پرِ فلت برای حبابِ تخت، LaMa برای بافت —
        # همان مسیرِ همیشگیِ سبکِ پاکسازی).
        _donor_skip = None

        # v1.14.81 — نقشهٔ «ساختارِ روشنِ دور از متن» (خطِ سفیدِ حباب،
        # قابِ کادر). خطایِ واقعیِ کاربر رویِ img2: «این قسمت حباب به کل
        # حذف زده و اون یکی کامل سیاه کرده» — بلوکِ اجباری-LaMa خطِ سفیدِ
        # حباب را می‌بلید و LaMa پنلِ تیره را سیاهِ خالص می‌کرد.
        # پیکسل‌هایِ روشن (≥۱۵۰) که بیش از ~۳۱px از جوهرِ متن فاصله
        # دارند «قفل» می‌شوند: ۱) از ماسکِ توپرِ بلوکِ اجباری خارج‌اند،
        # ۲) بعد از هر مرحله از عکسِ اصل به cleaned برمی‌گردند.
        self._prot_bright = None
        self._prot_glow = None
        self._prot_all = None
        try:
            _ink81 = getattr(self, "_compose_text_mask", None)
            if (_ink81 is not None
                    and _ink81.shape == image.shape[:2]
                    and int(cv2.countNonZero(_ink81))):
                _g81 = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                _near81 = cv2.dilate(
                    _ink81, np.ones((31, 31), np.uint8)) > 0
                _pb81 = (((_g81 >= 150) & (~_near81))
                         .astype(np.uint8)) * 255
                if int(cv2.countNonZero(_pb81)):
                    self._prot_bright = _pb81
                    if self.debug:
                        print(f"  [✓]حفاظتِ ساختارِ روشن — "
                              f"{int(cv2.countNonZero(_pb81))}px قفل شد")
                # v1.14.81b — قفلِ «تابِ نورِ پس‌زمینه»: مؤلفهٔ روشنِ (≥۱۰۰)
                # که بخشِ بزرگی‌اش (≥۲۰۰۰px) بیش از ~۱۰۰px از متن فاصله
                # دارد = نورِ صحنه/پنل است، نه هالهٔ حروف — نمونه: پرتوِ
                # بالایِ پنلِ img2 که پرکنندهٔ هاله سیاهش می‌کرد.
                # قرمزِ اشباع (خاکستریِ ~۷۶) عمداً زیرِ آستانه می‌ماند تا
                # لکهٔ قرمزِ کارتِ عنوان طبقِ v1.14.66/67 پاک شود.
                try:
                    _b100 = (_g81 >= 100).astype(np.uint8)
                    _d81 = cv2.distanceTransform(
                        (cv2.dilate(_ink81,
                                    np.ones((5, 5), np.uint8)) == 0)
                        .astype(np.uint8), cv2.DIST_L2, 3)
                    _far100 = (_d81 > 100.0) & (_b100 > 0)
                    if int(_far100.sum()) >= 2000:
                        _cnt81, _lbl81 = cv2.connectedComponents(
                            _b100, connectivity=8)
                        _fcnt = np.bincount(
                            _lbl81[_far100].ravel(), minlength=_cnt81)
                        _fids = np.unique(_lbl81[_far100])
                        _fids = _fids[_fids != 0]
                        _keep = [int(i) for i in _fids if _fcnt[i] >= 2000]
                        if _keep:
                            _lut = np.zeros(_cnt81, dtype=np.uint8)
                            _lut[_keep] = 255
                            _pg81 = _lut[_lbl81]
                            _pg81 &= cv2.dilate(
                                _ink81, np.ones((5, 5), np.uint8)) == 0
                            _pg81 = (_pg81 > 0).astype(np.uint8) * 255
                            if int(cv2.countNonZero(_pg81)):
                                self._prot_glow = _pg81
                                if self.debug:
                                    print(f"  [✓]قفلِ تابِ نور — "
                                          f"{int(cv2.countNonZero(_pg81))}px "
                                          f"({len(_keep)} مؤلفه)")
                except Exception:
                    self._prot_glow = None
                # قفل‌ها از ماسکِ پاکسازی خارج می‌شوند (LaMa/پرکننده‌ها
                # حقِ بازنویسی‌شان را ندارند)
                try:
                    _pa81 = None
                    if self._prot_bright is not None:
                        _pa81 = self._prot_bright.copy()
                    if self._prot_glow is not None:
                        _pa81 = (self._prot_glow.copy() if _pa81 is None
                                 else _pa81 | self._prot_glow)
                    if _pa81 is not None and int(cv2.countNonZero(_pa81)):
                        mask[_pa81 > 0] = 0
                        self._prot_all = _pa81
                    # v1.14.106 — قفلِ خطِ سراسری (کادرِ پنل) هم در
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
                # v1.14.81 — پروبِ وضعیتِ قفلِ پیکسل
                try:
                    _pv81 = os.environ.get("MANGA_PROBE", "")
                    if _pv81 and "," in _pv81:
                        _qx81, _qy81 = [int(v) for v in _pv81.split(",")]
                        _inb = bool(self._prot_bright is not None
                                    and self._prot_bright[_qy81, _qx81] > 0)
                        _ing = bool(self._prot_glow is not None
                                    and self._prot_glow[_qy81, _qx81] > 0)
                        _inm = bool(mask[_qy81, _qx81] > 0)
                        print(f"  [🔍PROBE] ({_qx81},{_qy81}) "
                              f"gray={int(_g81[_qy81, _qx81])} "
                              f"prot_bright={_inb} prot_glow={_ing} "
                              f"in_mask_after_sub={_inm}", flush=True)
                except Exception:
                    pass
        except Exception:
            self._prot_bright = None
            self._prot_glow = None
        _stage185("قفلها")
        try:
            _pv81p = os.environ.get("MANGA_PROBE", "")
            if _pv81p and "," in _pv81p:
                _qx81p, _qy81p = [int(v) for v in _pv81p.split(",")]
                print(f"  [🔍PROBE] after_prot_build="
                      f"({cleaned[_qy81p, _qx81p]})", flush=True)
        except Exception:
            pass
        # v1.14.94 — قفلِ ساختارِ روشنِ نازک (قابِ تزئینی/نوارِ لبه) که
        # باکسِ بلوکِ اجباری از رویش عبور می‌کند — قبل از توپرشدنِ ماسک،
        # وگرنه LaMa قاب را له می‌کند (GREEN MOON). در `_prot_all`
        # ادغام می‌شود تا همهٔ مسیرها (پرکنندهٔ فوری، LaMa، paste) آن را
        # محترم بشمارند.
        try:
            _fbs94 = (getattr(self, "_lama_force_rect_boxes", None) or [])
            if _fbs94:
                _slk94 = self._rect_structure_lock(image, _fbs94)
                if _slk94 is not None and int(cv2.countNonZero(_slk94)):
                    if getattr(self, "_prot_all", None) is None:
                        self._prot_all = _slk94
                    else:
                        self._prot_all = cv2.bitwise_or(
                            self._prot_all, _slk94)
                    if self.debug:
                        print(f"  [✓]قفلِ ساختارِ روشن — "
                              f"{int(cv2.countNonZero(_slk94))}px از "
                              f"{len(_fbs94)} بلوک محافظت شد", flush=True)
        except Exception:
            pass

        # v1.14.59 — بلوک‌هایِ «متنِ روشن روی محفظهٔ تیره» (کارتِ عنوانِ
        # Crimson Dragon و امثالش): هرچه کارو/کلیپِ حباب/پروتکت از ماسک
        # کم کرده باشد بی‌اثر — ماسک در این بلوک‌ها اجباری توپر می‌شود تا
        # ۱) LaMa کلِ بلوک را بازسازی کند (پرکنندهٔ تخت شبح نمی‌گذارد)
        # ۲) نوارِ ترکیبِ دو-عکسی کلِ بلوک را از عکسِ پاک‌شده بگیرد
        # (پیکسلِ بینِ حروف از عکسِ اصلی نماند = «متنِ قبلی سرِ جایش»).
        # سقفِ ترکیب هنرِ بیرونِ بلوک را سالم نگه می‌دارد.
        try:
            _fb_list = (getattr(self, "_lama_force_rect_boxes", None) or [])
            _h59, _w59 = mask.shape[:2]
            _fb_new = []
            for _fb in _fb_list:
                _fx0 = max(0, int(_fb[0]) - 4)
                _fy0 = max(0, int(_fb[1]) - 4)
                _fx1 = min(_w59, int(_fb[2]) + 5)
                _fy1 = min(_h59, int(_fb[3]) + 5)
                if _fx1 - _fx0 < 8 or _fy1 - _fy0 < 8:
                    _fb_new.append([int(_fb[0]), int(_fb[1]),
                                    int(_fb[2]), int(_fb[3])])
                    continue
                # v1.14.94b — سنجشِ باکس به «متنِ واقعی»: باکسِ ناحیهٔ
                # دیتکتور تا مرزِ پنل می‌رود و LaMa قابِ تزئینی را له
                # می‌کند (نمونه: GREEN MOON). باکسِ پرشده = bboxِ
                # جوهر+هالهٔ داخلِ باکس + پدِ ۱۲px — ساختارِ بیرونِ متن
                # هرگز بلعیده نمی‌شود؛ تضمینِ v1.14.59 («پیکسلِ بینِ
                # حروف از اصل نماند») همچنان برقرار است چون کلِ بلوکِ
                # متن پوشیده می‌شود.
                _nx0, _ny0 = _fx0, _fy0
                _nx1, _ny1 = _fx1, _fy1
                _bx0, _by0 = _fx0, _fy0
                _bx1, _by1 = _fx1, _fy1
                try:
                    _sub94 = mask[_fy0:_fy1, _fx0:_fx1]
                    _ys94, _xs94 = np.nonzero(_sub94)
                    if _ys94.size >= 400:
                        _p94 = 12
                        _nx0 = max(0, _fx0 + int(_xs94.min()) - _p94)
                        _ny0 = max(0, _fy0 + int(_ys94.min()) - _p94)
                        _nx1 = min(_w59,
                                   _fx0 + int(_xs94.max()) + 1 + _p94)
                        _ny1 = min(_h59,
                                   _fy0 + int(_ys94.max()) + 1 + _p94)
                        _bx0, _by0, _bx1, _by1 = _nx0, _ny0, _nx1, _ny1
                except Exception:
                    pass
                # v1.14.94c — پرِ بلوکِ اجباری «خط‌به‌خط»: به‌جایِ یک
                # مستطیلِ توپرِ چندخطی (حفرهٔ غول = خمیرِ LaMa + لکهٔ
                # تخت روی گرادیان)، هر خطِ متن نوارِ خودش را می‌گیرد
                # (bboxِ سطر + پد). بینِ خط‌ها = پس‌زمینهٔ اصل می‌ماند —
                # LaMa هر نوار را از بافتِ واقعیِ بالا/پایین بازسازی
                # می‌کند (فلسفهٔ «خط به خط» کاربر) و جعبه‌هایِ
                # اسنپ‌شات/مقایسه هم نواریند.
                _strips = []
                _p94 = 12
                try:
                    # v1.14.95 — جدایشِ خطی از پالی‌هایِ OCR: پروفیلِ جوهر
                    # وقتی هالهٔ درخشش بینِ خط‌ها پُرش کند (نمونهٔ «The
                    # Crimson Dragon,» رویِ پلاک) هر دو خط را یک باند
                    # می‌کند → حفرهٔ LaMa غول می‌شود و لبهٔ تختِ محسوس
                    # رویِ گرادیان می‌ماند. مرزِ باند از مرکزِ پالی‌ها،
                    # ولی گسترهٔ باند از «جوهرِ خامِ» همان باند — وگرنه
                    # پالیِ فونتِ تزئینی (بلندیِ ۱۳۲px) باز کلِ بلوک را
                    # می‌پوشاند (v1.14.95c).
                    _src94 = None
                    if _sub94 is not None and _ys94.size >= 400:
                        _src94 = _sub94
                        try:
                            _rawS94 = getattr(
                                self, "_page_raw_text_mask", None)
                            if (_rawS94 is not None
                                    and _rawS94.shape == mask.shape[:2]):
                                _rsub94 = _rawS94[
                                    _fy0:_fy1, _fx0:_fx1]
                                if int(cv2.countNonZero(_rsub94)) >= 400:
                                    _src94 = _rsub94
                        except Exception:
                            pass
                    _pl94 = []
                    try:
                        _rid94 = int(_fb[4]) if len(_fb) > 4 else -1
                        if _rid94 >= 0:
                            for _r94o in (getattr(self, "_page_regions",
                                                  None) or []):
                                if int(getattr(_r94o, "id", -2)) == _rid94:
                                    for _p94b in (
                                            getattr(_r94o, "ocr_polys",
                                                    None) or []):
                                        try:
                                            _pp94 = np.asarray(
                                                _p94b,
                                                dtype=np.float32).reshape(-1, 2)
                                            if _pp94.shape[0] >= 3:
                                                _pl94.append(_pp94)
                                        except Exception:
                                            continue
                                    break
                    except Exception:
                        _pl94 = []
                    if len(_pl94) >= 2:
                        # بازهٔ خامِ y (بدونِ پد) — اگر پدِ قبل از ادغام
                        # اضافه شود، خط‌هایِ نزدیک (پلاکِ «The Crimson
                        # Dragon,») در هم می‌لغزند و یک باند می‌شوند.
                        # مختصاتِ پالی = مطلق؛ بازه‌ها نسبت به باکس‌اند.
                        _ivs94 = []
                        for _pp94 in _pl94:
                            _iy0 = max(0, int(np.floor(
                                _pp94[:, 1].min())) - _fy0)
                            _iy1 = min(_fy1 - _fy0, int(np.ceil(
                                _pp94[:, 1].max())) + 1 - _fy0)
                            _ix0 = max(0, int(np.floor(
                                _pp94[:, 0].min())) - _fx0 - _p94)
                            _ix1 = min(_fx1 - _fx0, int(np.ceil(
                                _pp94[:, 0].max())) + 1 - _fx0 + _p94)
                            if _iy1 - _iy0 >= 8 and _ix1 - _ix0 >= 8:
                                _ivs94.append([_iy0, _iy1, _ix0, _ix1])
                        _ivs94.sort(key=lambda _v: (_v[0], _v[1]))
                        _mrg94 = []
                        for _iv in _ivs94:
                            if _mrg94 and _iv[0] < _mrg94[-1][1]:
                                _mrg94[-1][1] = max(_mrg94[-1][1], _iv[1])
                                _mrg94[-1][2] = min(_mrg94[-1][2], _iv[2])
                                _mrg94[-1][3] = max(_mrg94[-1][3], _iv[3])
                            else:
                                _mrg94.append(list(_iv))
                        if not (2 <= len(_mrg94) <= 12):
                            # تلاشِ ۲ — شکافِ مرکزها: فونت‌هایِ تزئینی پالیِ
                            # بلند می‌سازند و بازه‌هایِ y خط‌ها همپوشانی
                            # دارند (پلاک: [5-137]/[76-205]). مرزِ خط‌ها =
                            # میانهٔ بزرگ‌ترینِ شکافِ بینِ مرکزِ خط‌ها؛
                            # هر باند در مرز کِیل می‌شود.
                            try:
                                _cents94 = sorted(
                                    (v[0] + v[1]) / 2.0 for v in _ivs94)
                                _gaps94 = [(_cents94[_i94 + 1]
                                            - _cents94[_i94], _i94)
                                           for _i94
                                           in range(len(_cents94) - 1)]
                                if _gaps94:
                                    _gmax94, _gi94 = max(
                                        _gaps94, key=lambda t: t[0])
                                    if _gmax94 >= 14.0:
                                        _bnd94 = (_cents94[_gi94]
                                                  + _cents94[_gi94 + 1]) / 2.0
                                        _up94 = [v for v in _ivs94
                                                 if (v[0] + v[1]) / 2.0 < _bnd94]
                                        _dn94 = [v for v in _ivs94
                                                 if (v[0] + v[1]) / 2.0 >= _bnd94]
                                        if _up94 and _dn94:
                                            _mrg94 = [
                                                [min(v[0] for v in _up94),
                                                 min(_bnd94,
                                                     max(v[1] for v in _up94)),
                                                 min(v[2] for v in _up94),
                                                 max(v[3] for v in _up94)],
                                                [max(_bnd94,
                                                     min(v[0] for v in _dn94)),
                                                 max(v[1] for v in _dn94),
                                                 min(v[2] for v in _dn94),
                                                 max(v[3] for v in _dn94)]]
                            except Exception:
                                _mrg94 = []
                        if 2 <= len(_mrg94) <= 12:
                            # v1.14.95c — گسترهٔ باند از «جوهرِ خامِ همان
                            # باند» نه از bboxِ پالی (فونتِ تزئینی پالیِ
                            # بلند می‌سازد → نوارها همپوشان می‌شوند و
                            # حفرهٔ LaMa باز کلِ بلوک می‌شود).
                            _profC94 = None
                            if _src94 is not None:
                                _profC94 = (_src94 > 0).sum(axis=1)
                                _thrC94 = max(3.0, 0.04 * (_fx1 - _fx0))
                            for (_ay94, _qy94, _ax94, _qx94) in _mrg94:
                                _ay94 = int(round(_ay94))
                                _qy94 = int(round(_qy94))
                                _ax94 = int(round(_ax94))
                                _qx94 = int(round(_qx94))
                                if _profC94 is not None:
                                    _seg94 = _profC94[_ay94:_qy94]
                                    _rr94 = np.nonzero(
                                        _seg94 >= _thrC94)[0]
                                    if _rr94.size >= 8:
                                        _ny0 = max(0, _ay94
                                                   + int(_rr94.min()) - 6)
                                        _ny1 = min(_fy1 - _fy0,
                                                   _ay94
                                                   + int(_rr94.max()) + 7)
                                        if _ny1 - _ny0 >= 10:
                                            _ay94, _qy94 = _ny0, _ny1
                                # v1.14.95f — پدِ ۲۰px: هالهٔ درخششِ
                                # متن تا ~۲۰px بیرونِ جوهر می‌رود؛ اگر
                                # نوار تنگ باشد، هاله دورِ پرِ تازه
                                # می‌ماند و «قابِ روشنِ» محسوس می‌سازد
                                # (اسکرین‌شاتِ پلاکِ کاربر).
                                _ay94 = max(0, _ay94 - 20)
                                _qy94 = min(_fy1 - _fy0, _qy94 + 20)
                                if _qy94 - _ay94 < 10:
                                    continue
                                _strips.append([_fx0 + _ax94, _fy0 + _ay94,
                                                _fx0 + _qx94, _fy0 + _qy94])
                            if self.debug and _strips:
                                print(f"  [🔍] bands از پالیِ OCR: "
                                      f"{len(_strips)} خط")
                        elif self.debug:
                            try:
                                _ivs_dbg = [f"[{v[0]}-{v[1]}]"
                                            for v in _ivs94]
                            except Exception:
                                _ivs_dbg = []
                            print(f"  [🔍] poly-bands رد شد: rid={_rid94 if len(_fb) > 4 else '-'} "
                                  f"polys={len(_pl94)} mrg={len(_mrg94)} "
                                  f"iv={' '.join(_ivs_dbg)}")
                    if not _strips and _sub94 is not None \
                            and _ys94.size >= 400:
                        # v1.14.94d — پروفیلِ سطر/ستون از «جوهرِ خام»
                        # (قبلِ هاله‌گیریِ v1.14.66) — هاله، سطرها را به
                        # هم می‌چسباند و جدایشِ خطی را می‌کُشد
                        _src94 = _sub94
                        try:
                            _rawS94 = getattr(
                                self, "_page_raw_text_mask", None)
                            if (_rawS94 is not None
                                    and _rawS94.shape == mask.shape[:2]):
                                _rsub94 = _rawS94[
                                    _fy0:_fy1, _fx0:_fx1]
                                if int(cv2.countNonZero(_rsub94)) >= 400:
                                    _src94 = _rsub94
                        except Exception:
                            _src94 = _sub94
                        _prof94 = (_src94 > 0).sum(axis=1)
                        _thr94 = max(3.0, 0.04 * (_fx1 - _fx0))
                        _rows94 = _prof94 >= _thr94
                        _bands94 = []
                        _s94 = None
                        _g94 = 0
                        for _r94 in range(_rows94.size):
                            if _rows94[_r94]:
                                if _s94 is None:
                                    _s94 = _r94
                                _g94 = 0
                            elif _s94 is not None:
                                _g94 += 1
                                if _g94 > 6:
                                    _bands94.append(
                                        (_s94, _r94 - _g94 + 1))
                                    _s94 = None
                                    _g94 = 0
                        if _s94 is not None:
                            _bands94.append((_s94, _rows94.size))
                        _pg94 = 8
                        for (_a94, _b94) in _bands94:
                            _ay94 = max(0, _a94 - _pg94)
                            _qy94 = min(_fy1 - _fy0, _b94 + _pg94)
                            if _qy94 - _ay94 < 10:
                                continue
                            _colp94 = (_src94[_a94:_b94] > 0).sum(axis=0)
                            _cols94 = np.nonzero(_colp94 > 0)[0]
                            if _cols94.size < 8:
                                continue
                            _ax94 = max(0, int(_cols94.min()) - _p94
                                        if _ys94.size >= 400 else 4)
                            _qx94 = min(_fx1 - _fx0,
                                        int(_cols94.max()) + 1 + _p94
                                        if _ys94.size >= 400 else _fx1 - _fx0)
                            if _qx94 - _ax94 < 8:
                                continue
                            _strips.append([_fx0 + _ax94, _fy0 + _ay94,
                                            _fx0 + _qx94, _fy0 + _qy94])
                except Exception as _e95s:
                    if self.debug:
                        import traceback as _tb95
                        print(f"  [!] strips builder error: {_e95s}")
                        _tb95.print_exc()
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
                        # v1.14.81 — ساختارِ روشن/تابِ نور از بلوکِ اجباری خارج
                        try:
                            _pa81 = getattr(self, "_prot_all", None)
                            if _pa81 is not None:
                                _sub81 = _pa81[_sy0:_sy1, _sx0:_sx1] > 0
                                if int(_sub81.sum()):
                                    mask[_sy0:_sy1, _sx0:_sx1][_sub81] = 0
                                    if self.debug:
                                        print(f"  [✓]"
                                              f"{int(_sub81.sum())}px ساختارِ "
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
        # v1.14.105 — ماسکِ اتحادِ وارسی: فقط نواحیِ EP-وابسته (LaMa/OpenCV)
        # انباشته می‌شوند تا وارسیِ نهاییِ ضدِ خرابیِ GPU دقیقاً روی
        # همان‌ها برود؛ پرهایِ فلت/رنگیِ قطعی و SFX/تبلیغ خارج‌اند
        self._verify_union = None
        # v1.14.104 — «بالنِ سیستم»: پرِ فلتِ قطعیِ اینتریورِ باکسِ سفیدِ
        # سیستم (یک واحد — خط‌ها + بینِ خط‌ها) قبل از هر پرکنندهٔ دیگر.
        # جزئیاتِ چرایی → docstringِ _fill_system_box_interiors.
        try:
            _n_sys104 = self._fill_system_box_interiors(
                image, regions, mask, cleaned)
            if _n_sys104 and self.debug:
                print(f"  [*]{_n_sys104} اینتریورِ بالنِ سیستم → "
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
        _stage185("پرکنندهٔ فوری")
        # v1.14.81 — قفلِ ساختارِ روشن/تابِ نور: پرکننده‌هایِ فوری حقِ
        # دست‌زدن به این پیکسل‌ها را ندارند — خطِ سفیدِ حباب و پرتوِ نور
        # باید زنده بمانند (خطایِ img2: «حباب به کل حذف زده»)
        try:
            _pa81 = getattr(self, "_prot_all", None)
            if _pa81 is not None and int(cv2.countNonZero(_pa81)):
                _sel81 = _pa81 > 0
                cleaned[_sel81] = image[_sel81]
                if self.debug:
                    print(f"  [✓]{int(_sel81.sum())}px قفلِ روشن "
                          f"بعد از پرکنندهٔ فوری ترمیم شد")
                try:
                    _pv81r = os.environ.get("MANGA_PROBE", "")
                    if _pv81r and "," in _pv81r:
                        _qx81r, _qy81r = [int(v) for v in _pv81r.split(",")]
                        print(f"  [🔍PROBE] after_fill_restore="
                              f"({cleaned[_qy81r, _qx81r]})", flush=True)
                except Exception:
                    pass
        except Exception:
            pass
        # v1.14.61 — باگِ «لکهٔ بلوکی/سیاهی روی کارتِ تیره»: پرکننده‌هایِ
        # فوری ناحیهٔ پرشده را از ماسک کِیل می‌کنند؛ بعد کلاسترِ بعدی با
        # «سوراخِ حروف» به LaMa می‌رسید → LaMa متنِ سفیدِ باقی‌مانده در
        # حفره‌ها را زمینه فرض می‌کرد و دورش لکهٔ قرمزِ بلوکی می‌ساخت
        # (نمونه: تیترِ Crimson Dragon و پلیتِ AIDE ZEPHYROS رویِ گوشی).
        # پس از کِیل، باکسِ کاملِ بلوک‌هایِ اجباری-LaMa دوباره توپر می‌شود
        # تا LaMa کلِ متن را با هم ببیند و پاک کند (سبکِ پاکسازی عوض
        # نمی‌شود — همان مسیرِ اجباری-LaMa با ماسکِ کاملِ v1.14.59).
        try:
            for _fb in (getattr(self, "_lama_force_rect_boxes",
                                None) or []):
                if os.environ.get("MANGA_NO_FORCE_LAMA", "0") != "1":
                    mask[_fb[1]:_fb[3], _fb[0]:_fb[2]] = 255
                    # v1.14.81 — همان حفاظت (بعد از کِیلِ پرکننده‌های فوری
                    # هم بلوک دوباره توپر می‌شود)
                    try:
                        _pa81 = getattr(self, "_prot_all", None)
                        if _pa81 is not None:
                            _sub81 = _pa81[_fb[1]:_fb[3],
                                           _fb[0]:_fb[2]] > 0
                            if int(_sub81.sum()):
                                mask[_fb[1]:_fb[3],
                                     _fb[0]:_fb[2]][_sub81] = 0
                    except Exception:
                        pass
        except Exception:
            pass
        # v1.14.62 — اسنپ‌شاتِ «وضعیتِ پرکنندهٔ فوری» برایِ بلوک‌هایِ محفظهٔ
        # تیره، قبل از حلقهٔ LaMa. چرا: در نوارِ ترکیبی، بازسازیِ بلوکِ کامل
        # توسطِ LaMa-Manga (مدلِ گوشی/سقفِ پچِ ۳۸۴) رویِ صفحهٔ گرادیانیِ تیره
        # «لکهٔ بلوکی» می‌سازد (کارتِ عنوانِ Crimson Dragon — بازتولیدِ
        # سندباکس در strip_003). پرکنندهٔ فوریِ گرادیانی (v1.14.60) رویِ همان
        # بلوک «کاملاً تمیز» است (اثبات: MANGA_NO_FORCE_LAMA=1). پس نتیجهٔ
        # LaMaِ هر بلوک در اعمالِ نهایی با این اسنپ‌شات سنجیده می‌شود؛ اگر
        # انحرافِ لکه‌ای بزرگ داشت، همان اسنپ‌شات جایگزین می‌شود.
        self._force_pre_snap = None
        try:
            _fbs62 = (getattr(self, "_lama_force_rect_boxes", None) or [])
            if _fbs62:
                _hS, _wS = mask.shape[:2]
                _snaps = []
                for _fb in _fbs62:
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
            # v1.14.54/63: در این مسیر هم خروجی = عکسِ اصلی + فقط نوارِ متن
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
        # v1.14.167 — حلقهٔ پرکنندهٔ خوشه‌ها به تابعِ مستقل تبدیل شد تا
        # خوشه‌ها همزمان پر شوند (بودجهٔ موازیِ سیستم — «پاکسازیش
        # همینجور»): هر خوشه فقط result میسازد و رویِ cleaned نمینویسد؛
        # نوشتنِ نتیجه‌ها همان مسیرِ ترتیبیِ بعدِ LaMa است.
        _clusters_l167 = list(self._mask_clusters(mask, pad=3))

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
            # v1.14.59 — کلاسترهایِ «متنِ روشن روی محفظهٔ تیره» اجباری LaMa:
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
                    # v1.14.82 — جوهرِ محفظهِ تیره: فقط روشِ LaMa —
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
                        # v1.14.81 — پرکنندهٔ رنگی ماسک را با دیلهٔ ۲۵+کلوز
                        # گسترش می‌دهد و همین گسترش، ساختارِ روشنِ نزدیک
                        # (قابِ سفیدِ کارتِ img2-r10) را هم می‌بلعید و با
                        # TELEA پاک می‌کرد («اون یکی کامل سیاه کرده»).
                        # پیکسل‌هایِ قفل‌شده از ماسکِ برگشتی خارج می‌شوند.
                        try:
                            _pa81c = getattr(self, "_prot_all", None)
                            if _pa81c is not None:
                                _subc = _pa81c[cy0:cy1, cx0:cx1] > 0
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
                _keep_flat135 = False
                if result is None and not _q_lama:
                    result = self._flat_fill_cluster(crop_img, crop_msk)
                elif result is None and _q_lama \
                        and _android_gate("MANGA_FILL_RESCUE") \
                        and float(cv2.countNonZero(crop_msk)) >= 0.40 * float(
                            max(1, (bx1 - bx0) * (by1 - by0))):
                    # v1.14.133 — اندروید: فقط «حفرهٔ بزرگ» (ماسکِ block-rect∪ink
                    # ~≥۴۰٪ باکس) → پرِ درجه‌دومِ تخت از حلقه؛ نوارهایِ باریکِ
                    # line-strips (~۱۵-۳۰٪) همچنان به LaMa میروند که رویِ
                    # حفرهٔ کوچک از پرِ تختِ درجه‌دوم تمیزتر است (گرادیانِ
                    # حباب را از زمینهٔ بزرگتر میخواند).
                    result = self._flat_fill_cluster(crop_img, crop_msk)
                    if result is not None:
                        # v1.14.135 — ضدِ توهمِ LaMa (MANGA_BIGCAV_FLAT):
                        # LaMaِ حفرهٔ بزرگِ چندخطی (بلوکِ متنِ متراکم) در
                        # داوناسکیل «متنِ قلابی/نویزِ گلیفی» میسازد (لاگِ
                        # گوشیِ 700×11362 + بازتولیدِ A/B — «لکهٔ کثیف»).
                        # اگر حلقه عمدتاً «روشنِ یکدست» باشد (دیوار/کاغذِ
                        # صاف — اقلیتِ تیرهٔ حلق = هنرِ چسبیده رد میشود)،
                        # پرِ درجه‌دومِ حلقه «نگه داشته میشود» حتی اگر
                        # گاردِ بافتِ کل-کراپ (بهخاطرِ همان اقلیتِ تیره)
                        # textured بگوید.
                        try:
                            _gr135 = cv2.cvtColor(crop_img,
                                                  cv2.COLOR_BGR2GRAY)
                            _m135 = crop_msk > 0
                            _rg135 = (cv2.dilate(
                                crop_msk, np.ones((9, 9), np.uint8)) > 0) \
                                & (~_m135)
                            _rv135 = _gr135[_rg135].astype(np.float32)
                            if _rv135.size >= 200:
                                _rm135 = float(np.median(_rv135))
                                _share135 = float((np.abs(
                                    _rv135 - _rm135) <= 26.0).mean())
                                if (_rm135 >= 170.0 and _share135 >= 0.55):
                                    _keep_flat135 = True
                        except Exception:
                            pass
                    elif result is None and _android_gate(
                            "MANGA_BIGCAV_FLAT"):
                        # v1.14.135b — fitِ حلقهٔ روشن: وقتی اقلیتِ تیرهٔ
                        # حلقه (هنرِ چسبیده) fitِ عادی را میشکند ولی
                        # دیوار/کاغذِ روشن هنوز حاکم است، fit فقط از
                        # پیکسلهایِ روشنِ حلقه → پرِ تمیز بهجایِ
                        # LaMaِ توهمزن.
                        _lrg135 = self._flat_fill_cluster(
                            crop_img, crop_msk, light_ring=True,
                            fit_tol=13.0)
                        if _lrg135 is not None:
                            result = _lrg135
                            _keep_flat135 = True
                            if self.debug:
                                try:
                                    print(f"  [⚡]حفرهٔ بزرگ → پرِ حلقهٔ "
                                          f"روشن بهجایِ LaMa "
                                          f"@({cx0},{cy0})")
                                except Exception:
                                    pass
                elif result is None and _q_lama \
                        and _android_gate("MANGA_FLATRING"):
                    # v1.14.135 — اندروید/سرعت: حلقهٔ اطرافِ حفره «تخت» است
                    # (گسترهٔ صدکیِ ≤۲۴ — متن روی کاغذِ سفید/پنلِ تخت) →
                    # پرِ درجه‌دومِ حلقه بهجایِ LaMa (LaMaِ خوشهایِ 21
                    # کلاسترِ صفحهٔ 700×11362 = 42.7s؛ بیشترشان کاغذِ
                    # سفیداند). گاردِ بافتِ پایین (textured) اگر پرِ تخت
                    # را نپسندد به LaMa برمیگرداند — کیفیتِ وبتونِ
                    # گرادیانی دست‌نخورده میماند.
                    _rf135 = MangaTranslator._ring_flat_stats(crop_img,
                                                              crop_msk)
                    if _rf135 is not None:
                        result = self._flat_fill_cluster(crop_img, crop_msk)
                        if result is not None and self.debug:
                            try:
                                print(f"  [⚡]حلقهٔ تخت (med={_rf135[0]:.0f} "
                                      f"std={_rf135[1]:.0f}) → پرِ حلقه "
                                      f"بهجایِ LaMa @({cx0},{cy0})")
                            except Exception:
                                pass
                if (result is not None and not _pf_ok
                        and not _keep_flat135
                        and self._bg_is_textured(crop_img, crop_msk,
                                                 strong=True)):
                    result = None
            return [cx0, cy0, cx1, cy1, crop_msk, result, method]

        _fill_w167 = 1
        try:
            _fill_w167 = _parallel_budget("clean")
        except Exception:
            _fill_w167 = 1
        if len(_clusters_l167) >= 2 and _fill_w167 > 1:
            try:
                with ThreadPoolExecutor(max_workers=min(
                        _fill_w167, len(_clusters_l167))) as _fillx:
                    crops = list(_fillx.map(
                        lambda _cc: _fill_one_cluster(*_cc),
                        _clusters_l167))
            except Exception:
                crops = [_fill_one_cluster(*_cc)
                         for _cc in _clusters_l167]
        else:
            crops = [_fill_one_cluster(*_cc) for _cc in _clusters_l167]
        try:
            _pv81c = os.environ.get("MANGA_PROBE", "")
            if _pv81c and "," in _pv81c:
                _qxc, _qyc = [int(v) for v in _pv81c.split(",")]
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
                            # v1.14.241 — بازگشت به فرمولِ testm
                            # (0.16×ضلعِ کوتاه، سقفِ ۱۴۴): گپِ ۰.۲۴/۲۲۰ِ
                            # v1.14.216 زنجیرههایِ دورتر (فاصلهٔ ۱۵۰-۲۴۰px
                            # — بلوکهایِ سندِ 9.jpg مثلِ y=1552..3844) را هم
                            # میچسباند → پچِ ۷۰۰×۲۳۰۰ → داوناسکیلِ ۰.۵۶ِ
                            # big-lama → «مهِ خاکستری/باندِ کدر» رویِ donor
                            # (گزارشِ سازنده: شبحِ خاکستری، لکه). زنجیرههایِ
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
                        # v1.14.46: هزینهٔ هر فراخوانیِ LaMa با مساحتِ داخلیِ
                        # سقف‌خورده (≤۳۸۴) متناسب است — پچِ بزرگ‌تر = مجموعِ
                        # محاسبهٔ کمتر. اندروید ۶→۱۰ عضو (~۲x سریع‌تر)
                        if _mm <= 0:
                            _mm = 10 if _on_android() else 6
                        groups = self._group_nearby_patches(
                            pending, gap=_gap, max_members=_mm)
                        # v1.14.65 — بنرِ تبلیغ (promo) هرگز با کلاسترهایِ
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
                    # v1.14.44: یک منبعِ حقیقت — همان _lama_workers_auto
                    # (قبلاً یک جدولِ تکراریِ همین‌جا بود که با آن فرق داشت)
                    try:
                        _workers = self._lama_workers_auto()
                    except Exception:
                        _workers = 1
                    # v1.14.46: بیش از cores÷2 پچِ همزمان، حافظه/کش را اشباع
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
                    # v1.14.45: نخِ هر پچ = هسته‌ها ÷ پچِ موازی — پچِ کم →
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
                    # v1.14.51: اگر سشن با نخِ متفاوت باز است، همین‌جا یک‌بار
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
                    # v1.14.50: ضدِ اشباعِ نخ — لاگِ POCO F4 (۸ هسته) نشان کرد
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
                        # v1.14.99 (SRV-H4) — بچینگِ هم‌شکلِ پدشده فقط opt-in
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
                    self._mem_trim()  # v1.14.48c: رمِ فازِ LaMa آزاد شود
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
        _stage185("LaMa/پرکننده‌ها")

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
            # v1.14.62 — اعتبارسنجیِ نتیجهٔ LaMa رویِ بلوک‌هایِ محفظهٔ تیره:
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
                        # v1.14.73 — بلوکِ donor-گسترش‌یافته: مرجع = نتیجهٔ
                        # LaMa، نه اسنپ‌شاتِ پرکنندهٔ فوری (تخت = همان
                        # «لگِ سیاه» که کاربر گزارش کرد). کاربر گفته عکسِ
                        # اول کامل پاک شه؛ جعبهٔ تیره هم با LaMa بافت‌مند
                        # بازسازی می‌شود و نوارِ خط‌به‌خطِ آن تمیز می‌ماند.
                        # v1.14.73b — فقط وقتی زمینهٔ دورِ بلوک «بافت‌مند»
                        # است (پرده/بوکه). کارتِ گرادیانیِ صاف: پرِ فوریِ
                        # گرادیانیِ اسنپ‌شات تمیز‌تر است (کارتِ Crimson
                        # Dragon — LaMa رویِ گرادیانِ تیره شبح/لکهٔ بلوکی
                        # می‌گذارد) → همان منطقِ جایگزینیِ v1.14.62 بماند.
                        try:
                            _dn_hit = False
                            for _db in (getattr(self, "_donor_boxes", None)
                                        or []):
                                if not (_ix1 < _db[0] or _ix0 > _db[2]
                                        or _iy1 < _db[1] or _iy0 > _db[3]):
                                    _dn_hit = True
                                    break
                            if _dn_hit:
                                # v1.14.73b — فقط جعبه‌هایی که «داخلشان» بافت‌مند
                                # است LaMa را مرجع می‌گیرند؛ داخلِ صاف/گرادیانی
                                # (کارتِ Crimson Dragon) → منطقِ v1.14.62 بماند.
                                if MangaTranslator._box_bg_textured(
                                        image, _sn[0], _sn[1], _sn[2], _sn[3]):
                                    # v1.14.81 — «نگه‌داشتنِ LaMa» فقط وقتی
                                    # که روشناییِ زمینهٔ غیرمتن هم همان ماند.
                                    # img2: پنلِ تیرهٔ ~۶۰ → LaMa سیاهِ ~۱۲
                                    # داد («کامل سیاه کرده» کاربر) → منطقِ
                                    # v1.14.62 (جایگزینی با اسنپ‌شات) بسنجد.
                                    _keep81 = True
                                    try:
                                        _gA81 = cv2.cvtColor(
                                            np.clip(_ra, 0, 255).astype(np.uint8),
                                            cv2.COLOR_BGR2GRAY)
                                        _gB81 = cv2.cvtColor(
                                            np.clip(_rb, 0, 255).astype(np.uint8),
                                            cv2.COLOR_BGR2GRAY)
                                        _gO81 = cv2.cvtColor(
                                            image[_iy0:_iy1, _ix0:_ix1],
                                            cv2.COLOR_BGR2GRAY)
                                        _txt81 = cv2.dilate(
                                            (_gO81 >= 150).astype(np.uint8),
                                            np.ones((5, 5), np.uint8)) > 0
                                        _bg81 = ~_txt81
                                        if int(_bg81.sum()) >= 300:
                                            _mA81 = float(np.median(_gA81[_bg81]))
                                            _mB81 = float(np.median(_gB81[_bg81]))
                                            if abs(_mA81 - _mB81) > 30.0:
                                                _keep81 = False
                                                print(f"  [!]LaMa زمینه را "
                                                      f"{_mB81:.0f} → {_mA81:.0f} تغییرِ شدید داد "
                                                      f"→ اسنپ‌شاتْ مرجع",
                                                      flush=True)
                                    except Exception:
                                        _keep81 = True
                                    if _keep81:
                                        if self.debug:
                                            try:
                                                print(f"  [✓]بلوکِ "
                                                      f"بافت‌مند → نتیجهٔ "
                                                      f"LaMa نگه داشته شد",
                                                      flush=True)
                                            except Exception:
                                                pass
                                        continue  # زمینهٔ بافت‌مند → LaMa مرجع
                                        # نامعتبر → منطقِ v1.14.62 پایین‌تر
                        except Exception:
                            pass
                        _dM = np.abs(_ra - _rb).max(axis=2).astype(np.uint8)
                        _dM = cv2.GaussianBlur(_dM, (0, 0), 4)
                        _dm_mean = float(_dM.mean())
                        _dm_big = float((_dM > 26).mean())
                        # v1.14.62b — گاردِ «متنِ شبح»: اگر اسنپ‌شات هنوز
                        # جوهرِ متنیِ زیاد دارد (پرکنندهٔ فوری ناکام مانده —
                        # پنلِ روشن) ولی نتیجهٔ LaMa هموارتر است، جایگزینی
                        # ممنوع — وگرنه متنِ انگلیسی برمی‌گشت. سنجش:
                        # انرژیِ فرکانسِ بالا نسبت به میانهٔ محلی (حروف نازک
                        # = ساختار؛ لکه/گرادیانِ نرم = بی‌ساختار).
                        _gs62 = cv2.cvtColor(
                            np.clip(_rb, 0, 255).astype(np.uint8),
                            cv2.COLOR_BGR2GRAY)
                        _gl62 = cv2.cvtColor(
                            np.clip(_ra, 0, 255).astype(np.uint8),
                            cv2.COLOR_BGR2GRAY)
                        _mk62 = (41 if min(_gs62.shape) >= 41
                                 else 31 if min(_gs62.shape) >= 31 else 15)
                        _ms62 = cv2.medianBlur(_gs62, _mk62)
                        _ml62 = cv2.medianBlur(_gl62, _mk62)
                        _fs62 = float((np.abs(
                            _gs62.astype(np.int16)
                            - _ms62.astype(np.int16)) > 30).mean())
                        _fl62 = float((np.abs(
                            _gl62.astype(np.int16)
                            - _ml62.astype(np.int16)) > 30).mean())
                        if _fs62 > _fl62 * 1.6 + 0.02:
                            if self.debug:
                                print(f"  [✓]اسنپ‌شاتِ بلوک هنوز "
                                      f"متن دارد (جوهرِ اسنپ={_fs62:.3f} > "
                                      f"LaMa={_fl62:.3f}) → نتیجهٔ LaMa "
                                      f"نگه داشته شد (جلوگیری از متنِ شبح)",
                                      flush=True)
                            continue
                        # v1.14.226 — گاردِ جوهرِ هستهٔ ماسک: اسنپ‌شاتی که
                        # هنوز «جوهرِ متن» درونِ ماسکِ متن دارد هرگز
                        # جایگزینِ LaMa نمیشود. آستانهٔ ۳۰ِ 62b شبحِ
                        # نیمه‌پوشیده را نمیبیند (پرکنندهٔ فوریِ ناموفق،
                        # کنتراستِ ~۲۰) — لاگِ کاملِ 4e2e77: «LaMa زمینه
                        # را 146→183 → اسنپ‌شاتْ مرجع» = برگشتِ خوانای
                        # [TRAITS: FILTHY RICH…] (اسکرینشاتِ سازنده).
                        # سنجشِ مستقیم روی «هستهٔ ماسک» (جایی که میدانیم
                        # متن بوده) با آستانهٔ ۲۰ + برتریِ ۲× از LaMa.
                        try:
                            _mc226 = None
                            try:
                                _mc226 = (crop_msk > 0) \
                                    if crop_msk.shape[:2] == _gs62.shape \
                                    else None
                            except Exception:
                                _mc226 = None
                            if _mc226 is not None \
                                    and int(_mc226.sum()) >= 200:
                                _ds226 = np.abs(
                                    _gs62.astype(np.int16)
                                    - _ms62.astype(np.int16))
                                _dl226 = np.abs(
                                    _gl62.astype(np.int16)
                                    - _ml62.astype(np.int16))
                                _iks226 = float(
                                    (_ds226[_mc226] > 20).mean())
                                _ikl226 = float(
                                    (_dl226[_mc226] > 20).mean())
                                if _iks226 > 0.045 and \
                                        _iks226 > _ikl226 * 2.0 + 0.02:
                                    if self.debug:
                                        print(
                                            f"  [✓]جوهرِ متن در اسنپ‌شات "
                                            f"(هسته={_iks226:.3f} > "
                                            f"LaMa={_ikl226:.3f}) → LaMa "
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
            # v1.14.48: سقفِ ترکیب — هیچ پرکننده‌ای نباید بیش از ~۷px
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
                # v1.14.65 — بلوکِ اجباری-LaMa (محفظهٔ تیره) که LaMa آن را
                # از دست داد: پرِ گرادیانیِ توپرِ داخلِ باکس (همان ریاضیِ
                # اثبات‌شدهٔ پرکنندهٔ فوری) به‌جای فال‌بکِ OpenCV؛ وگرنه
                # refineِ تنگِ گلیف، هالهٔ قرمز را زنده می‌گذارد (لکهٔ
                # قرمزِ POCO F4). اسنپ‌شاتِ قبلِ LaMa هم قابلِ اعتماد نیست —
                # در مسیرِ block-rect∪ink هنوز خودِ متن را دارد.
                try:
                    _res65 = self._force_box_gradient_fill(
                        image, cx0, cy0, cx1, cy1)
                except Exception:
                    _res65 = None
                if _res65 is not None:
                    result = _res65
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
                # v1.14.65 — هالهٔ گلو (متنِ روشن روی پنلِ تیره): رویِ
                # زمینهٔ تیره، ماسکِ فال‌بک باید هالهٔ دورِ گلیف را هم
                # بپوشاند وگرنه جوهرِ قرمز/روشنِ دورِ حرف می‌ماند
                _bg_med65 = None
                try:
                    _g65 = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
                    _m65 = _dil > 0
                    _ring65 = (cv2.dilate(_dil,
                                          np.ones((13, 13), np.uint8)) > 0) \
                        & (~_m65)
                    if int(_ring65.sum()) >= 60:
                        _bg_med65 = float(np.median(_g65[_ring65]))
                        if _bg_med65 < 100.0:
                            _glow65 = (_g65 >= _bg_med65 + 26.0) & \
                                (cv2.dilate(_dil, np.ones(
                                    (15, 15), np.uint8)) > 0)
                            _glow65 = cv2.morphologyEx(
                                _glow65.astype(np.uint8), cv2.MORPH_CLOSE,
                                np.ones((7, 7), np.uint8))
                            _dil = cv2.bitwise_or(
                                _dil, (_glow65 > 0).astype(np.uint8) * 255)
                except Exception:
                    _bg_med65 = None
                try:
                    _thick = float(cv2.distanceTransform(
                        (_dil > 0).astype(np.uint8), cv2.DIST_L2, 3).max())
                except Exception:
                    _thick = _thick0
                # v1.14.65 — رویِ پنلِ تیره هرگز «نازک» حساب نشو (گلو)
                _thin = (_thick <= 28.0) and not (
                    _bg_med65 is not None and _bg_med65 < 100.0)
                # v1.14.48: استروکِ نازک روی گرادیان → پرکردنِ صفحه‌ایِ حلقه
                # (قبل از TELEA که رنگِ هنرِ نزدیک را می‌کشد)
                if _thick0 <= 14.0:
                    try:
                        _rpf = self._ring_plane_fill(crop_img, crop_msk)
                    except Exception:
                        _rpf = None
                    if _rpf is not None:
                        result = _rpf
                # v1.14.65 — refineِ تنگِ گلیف فقط رویِ زمینهٔ روشن: رویِ
                # پنلِ تیره ماسک را تا هستهٔ حرف جمع می‌کند و هالهٔ قرمزِ
                # دورِ حرف زنده می‌ماند (بازتولیدِ لکهٔ قرمزِ POCO F4)
                # + برایِ خوشهٔ تبلیغ (promo) هرگز refine نکن — ماسکِ توپرِ
                # بنر باید توپر بماند وگرنه بینِ حروفِ بنر بنفش می‌ماند
                _is_promo65 = False
                try:
                    for _pb65 in (getattr(self, "_promo_rect_boxes",
                                          None) or []):
                        if not (cx1 < int(_pb65[0]) or cx0 > int(_pb65[2])
                                or cy1 < int(_pb65[1]) or cy0 > int(_pb65[3])):
                            _is_promo65 = True
                            break
                except Exception:
                    _is_promo65 = False
                if self._bg_is_textured(crop_img, _dil) and \
                        not _is_promo65 and \
                        (_bg_med65 is None or _bg_med65 >= 100.0):
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
                    elif _thin and not _is_promo65:
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
            # v1.14.81 — تنظیمِ رنگِ حلقه + بلندِ آلفا برایِ OpenCV هم:
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
                            # v1.14.81 — زمینهٔ بافت‌مند (آسمانِ نقش‌دارِ
                            # img3): stdِ حلقه بالاست ولی IQR کوچک —
                            # تنظیمِ رنگِ نتیجهٔ LaMa نباید رد شود، وگرنه
                            # نوارها به‌صورتِ «مستطیلِ کثیفِ کدر» می‌مانند.
                            try:
                                _rq81 = np.percentile(
                                    _dstc[_ring].astype(np.float32),
                                    [25, 75])
                                _ring_ok = (_ring_std <= 26.0) or (
                                    float(_rq81[1] - _rq81[0]) <= 42.0)
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
                    # v1.14.94 — تطبیقِ لو-فرکانسِ پرِ LaMa با زمینهٔ
                    # پیرامون. نکتهٔ مهمِ تستِ واقعی (412e9e/890fb1 رویِ
                    # CPUِ پچِ ۳۸۴): میدانِ دیفرانسِ باکسِ بزرگ خودش
                    # «باندِ موج‌دار/بلوکی» می‌سازد — پرکنندهٔ LaMa در
                    # اکثرِ موارد خودش درست است → پیش‌فرضِ خاموش؛
                    # فقط با MANGA_LFCM=1 برایِ آزمایش فعال می‌شود.
                    try:
                        # v1.14.94f — گیتِ بافتِ LFCM: فقط رویِ زمینهٔ
                        # «صاف/گرادیانی» (کارتِ عنوان) اجرا شود؛ رویِ
                        # زمینهٔ بافت‌مند میدانِ دیفرانسِ باکسِ بزرگ خودش
                        # باندِ موج‌دار می‌سازد (تستِ 412e9e) → خودکار رد.
                        _go94 = False
                        if method == "LaMa" \
                                and os.environ.get(
                                    "MANGA_NO_LFCM", "0") != "1":
                            try:
                                _mbT94 = (crop_msk > 0)
                                if int(_mbT94.sum()) >= 2000:
                                    _ri94 = cv2.dilate(
                                        _mbT94.astype(np.uint8),
                                        np.ones((19, 19), np.uint8)) > 0
                                    _ro94 = cv2.dilate(
                                        _mbT94.astype(np.uint8),
                                        np.ones((41, 41), np.uint8)) > 0
                                    _rt94 = _ro94 & (~_ri94)
                                    _gT94 = cv2.cvtColor(
                                        image[cy0:cy1, cx0:cx1],
                                        cv2.COLOR_BGR2GRAY)
                                    _rs94 = (float(_gT94[_rt94].std())
                                             if int(_rt94.sum()) >= 200
                                             else 99.0)
                                    _go94 = (_rs94 <= 34.0)
                                    if self.debug:
                                        print(f"  [🔍]LFCM "
                                              f"gate crop@({cx0},{cy0}) "
                                              f"ring_std={_rs94:.0f} → "
                                              f"{'RUN' if _go94 else 'skip'}",
                                              flush=True)
                            except Exception:
                                _go94 = False
                        _mB94 = (crop_msk > 0) if crop_msk.dtype != np.uint8 \
                            else (crop_msk > 0)
                        _nMB94 = int(_mB94.sum())
                        if _go94 and _nMB94 >= 2000:
                            _th94 = float(cv2.distanceTransform(
                                _mB94.astype(np.uint8), cv2.DIST_L2, 3).max())
                            # v1.14.95d — پنجرهٔ LFCM باید نسبت به «پهنایِ
                            # نوار» هم مقیاس شود؛ وگرنه در انتهایِ نوارهایِ
                            # عریض (پلاکِ ۶۰۰px) پروفیلِ افقیِ وینیت را
                            # نمی‌گیرد و لبهٔ روشن/تیرهٔ نوار پیدا می‌ماند.
                            _cw94 = int(crop_msk.shape[1])
                            _k94 = int(np.clip(
                                round(max(_th94 * 3.0, _cw94 * 0.45)),
                                41, 331))
                            if _k94 % 2 == 0:
                                _k94 += 1
                            _img94 = image[cy0:cy1, cx0:cx1].astype(
                                np.float32)
                            _res94 = result.astype(np.float32)
                            _wb94 = (~_mB94).astype(np.float32)
                            try:
                                _raw94 = getattr(
                                    self, "_page_raw_text_mask", None)
                                if (_raw94 is not None
                                        and _raw94.shape
                                        == image.shape[:2]):
                                    _rd94 = cv2.dilate(
                                        _raw94[cy0:cy1, cx0:cx1],
                                        np.ones((9, 9), np.uint8))
                                    _wb94[(_rd94 > 0) & (~_mB94)] = 0.0
                            except Exception:
                                pass
                            # v1.14.94 — پیکسل‌هایِ قفلِ ساختار (قاب/نوارِ
                            # روشن) هم نمونهٔ زمینه نیستند؛ وگرنه بلورِ
                            # بزرگ رنگِ نقره‌ایِ قاب را وسطِ حفره می‌کشد
                            try:
                                _pa94 = getattr(self, "_prot_all", None)
                                if (_pa94 is not None
                                        and _pa94.shape
                                        == image.shape[:2]):
                                    _pd94 = cv2.dilate(
                                        _pa94[cy0:cy1, cx0:cx1],
                                        np.ones((5, 5), np.uint8))
                                    _wb94[(_pd94 > 0)
                                          & (~_mB94)] = 0.0
                            except Exception:
                                pass
                            _den94 = cv2.boxFilter(
                                _wb94, -1, (_k94, _k94))
                            _num94 = cv2.boxFilter(
                                _img94 * _wb94[..., None], -1,
                                (_k94, _k94))
                            _bg94 = _num94 / np.maximum(
                                _den94, 1e-3)[..., None]
                            _fl94 = cv2.boxFilter(
                                _res94, -1, (_k94, _k94))
                            _d94 = np.clip(_bg94 - _fl94, -44.0, 44.0)
                            _w94 = cv2.GaussianBlur(
                                (cv2.dilate(
                                    _mB94.astype(np.uint8),
                                    np.ones((3, 3), np.uint8)) * 255),
                                (0, 0), 3.0).astype(np.float32) / 255.0
                            _w94 = np.clip(_w94, 0.0, 1.0)[..., None]
                            # v1.14.94 — جاهایی که زمینهٔ نمونه‌گیریِ کافی
                            # ندارند وزنِ نرمِ پایین (نه cutoffِ بلوکی)
                            try:
                                _low94 = (_den94 < 0.05).astype(np.float32)
                                if float(_low94.mean()) > 0.001:
                                    _low94 = cv2.GaussianBlur(
                                        _low94, (31, 31), 8.0)
                                    _w94 = _w94 * (
                                        1.0 - 0.65 * _low94[..., None])
                            except Exception:
                                pass
                            _res94 = _res94 + _d94 * _w94
                            result = np.clip(
                                _res94, 0, 255).astype(np.uint8)
                            if self.debug:
                                try:
                                    _dm94 = float(np.abs(
                                        _d94 * _w94).mean())
                                    print(f"  [✓]LFCM "
                                          f"crop@({cx0},{cy0}) "
                                          f"k={_k94} |Δ|={_dm94:.1f}",
                                          flush=True)
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    # v1.14.95e — هم‌سازِ ستونیِ نوارهایِ عریض رویِ
                    # زمینهٔ تیرهٔ صاف (پلاکِ «Crimson Dragon»): پرِ
                    # LaMa پروفیلِ قائمِ وینیت را ادامه نمی‌دهد →
                    # باندِ تیره‌تر/روشن‌تر با لبهٔ واضح (اسکرین‌شاتِ
                    # کاربر). هدف = میان‌یابیِ خطیِ حلقهٔ بالا/پایینِ
                    # هر ستون (v1.14.95g: به‌جایِ corrِ ثابت، شیبِ
                    # کاملِ قائم جایگزینِ فرکانسِ پایینِ پر می‌شود —
                    # بافتِ فرکانس‌بالا دست‌نخورده می‌ماند).
                    try:
                        _mB95 = (crop_msk > 0)
                        _h95, _w95 = _mB95.shape
                        if int(_mB95.sum()) >= 8000 and _w95 >= 260:
                            _ysB95, _xsB95 = np.nonzero(_mB95)
                            _ty95, _by95 = (int(_ysB95.min()),
                                            int(_ysB95.max()))
                            _gO95 = cv2.cvtColor(
                                image[cy0:cy1, cx0:cx1],
                                cv2.COLOR_BGR2GRAY).astype(np.float32)
                            _top95 = max(0, _ty95 - 16)
                            _top95b = max(1, _ty95 - 3)
                            _bot95 = min(_h95, _by95 + 4)
                            _bot95b = min(_h95, _by95 + 17)
                            if (_by95 - _ty95) >= 40 and \
                                    (_top95b - _top95) >= 6 and \
                                    (_bot95b - _bot95) >= 6:
                                _res95f = result.astype(np.float32)
                                _corr95 = np.zeros(
                                    (_h95, _w95, 3), dtype=np.float32)
                                _nok95 = 0
                                for _x95 in range(_w95):
                                    if not _mB95[_ty95:_by95 + 1,
                                                 _x95].any():
                                        continue
                                    if _mB95[_top95:_top95b, _x95].any() \
                                            or _mB95[_bot95:_bot95b,
                                                     _x95].any():
                                        continue
                                    _rt95 = _gO95[_top95:_top95b, _x95]
                                    _rb95 = _gO95[_bot95:_bot95b, _x95]
                                    if _rt95.size < 4 or _rb95.size < 4:
                                        continue
                                    if max(_rt95.std(), _rb95.std()) > 22.0:
                                        continue
                                    _yy95 = np.linspace(
                                        0.0, 1.0, _by95 - _ty95 + 1,
                                        dtype=np.float32)[:, None]
                                    for _c95 in range(3):
                                        _mt95 = float(np.median(
                                            image[cy0 + _top95:
                                                  cy0 + _top95b,
                                                  cx0 + _x95,
                                                  _c95]).astype(np.float32))
                                        _mb95 = float(np.median(
                                            image[cy0 + _bot95:
                                                  cy0 + _bot95b,
                                                  cx0 + _x95,
                                                  _c95]).astype(np.float32))
                                        _tgt95 = (_mt95 * (1.0 - _yy95)
                                                  + _mb95 * _yy95)
                                        _lo95 = cv2.GaussianBlur(
                                            _res95f[_ty95:_by95 + 1,
                                                    _x95, _c95],
                                            (0, 0), 0.02 * max(
                                                8.0, _by95 - _ty95))
                                        _corr95[_ty95:_by95 + 1, _x95,
                                                _c95] = np.clip(
                                            _tgt95 - _lo95, -26.0, 26.0
                                        ).reshape(-1)
                                    _nok95 += 1
                                if _nok95 >= max(40, int(0.35 * _w95)):
                                    _corr95[:, :, 0] = cv2.GaussianBlur(
                                        _corr95[:, :, 0], (0, 0), 9.0)
                                    _corr95[:, :, 1] = cv2.GaussianBlur(
                                        _corr95[:, :, 1], (0, 0), 9.0)
                                    _corr95[:, :, 2] = cv2.GaussianBlur(
                                        _corr95[:, :, 2], (0, 0), 9.0)
                                    _wcol95 = (cv2.GaussianBlur(
                                        (cv2.dilate(
                                            _mB95.astype(np.uint8),
                                            np.ones((3, 3),
                                                    np.uint8)) * 255),
                                        (0, 0), 3.0
                                    ).astype(np.float32) / 255.0)
                                    _res95e = _res95f + _corr95 \
                                        * _wcol95[..., None]
                                    result = np.clip(
                                        _res95e, 0, 255).astype(np.uint8)
                                    if self.debug:
                                        _act95 = float(np.abs(
                                            _corr95).mean())
                                        print(f"  [✓]col-harmonize "
                                              f"crop@({cx0},{cy0}) "
                                              f"cols={_nok95} "
                                              f"|corr|={_act95:.1f}",
                                              flush=True)
                    except Exception:
                        pass
                    _m8 = (crop_msk if crop_msk.dtype == np.uint8
                           else (crop_msk > 0).astype(np.uint8) * 255)
                    if _prot_c is not None:
                        _m8 = _m8.copy()
                        _m8[_prot_c > 0] = 0  # v1.14.48: دیوار محافظت شود
                    # v1.14.81 — پیکسل‌هایِ قفلِ روشن هم هرگز نوشته نشوند
                    try:
                        _pa81w = getattr(self, "_prot_all", None)
                        if _pa81w is not None:
                            _pa_c2 = _pa81w[cy0:cy1, cx0:cx1]
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
                        _pa81x = getattr(self, "_prot_all", None)
                        if _pa81x is not None:
                            _pa_c3 = _pa81x[cy0:cy1, cx0:cx1]
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
                    _pa81y = getattr(self, "_prot_all", None)
                    if _pa81y is not None:
                        _pa_c4 = _pa81y[cy0:cy1, cx0:cx1]
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
            # v1.14.105 — انباشتنِ ماسکِ وارسی (وارسیِ واقعی یک‌بار در
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
            # v1.14.81 — پروبِ درونِ حلقه: چه کراپی پیکسلِ قفل‌شده را می‌نویسد؟
            try:
                _pv81l = os.environ.get("MANGA_PROBE", "")
                if _pv81l and "," in _pv81l:
                    _qxl, _qyl = [int(v) for v in _pv81l.split(",")]
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
            _pv81a = os.environ.get("MANGA_PROBE", "")
            if _pv81a and "," in _pv81a:
                _qxa, _qya = [int(v) for v in _pv81a.split(",")]
                print(f"  [🔍PROBE] after_crops_apply="
                      f"({cleaned[_qya, _qxa]})", flush=True)
        except Exception:
            pass
        # v1.14.48c: ماسک‌ها/نتیجه‌هایِ کراپ‌ها بعد از ترکیب آزاد شوند —
        # روی نوارِ بلند ~۵۰-۱۵۰MB است که در سویپ‌ها و ذخیره لازم می‌آید
        try:
            del crops, pending, groups
        except Exception:
            pass
        self._mem_trim()  # v1.14.48c: قبل از سویپ‌ها رم آزاد شود

        # v1.14.65 — بازرسیِ رنگیِ بنرِ تبلیغ: LaMa-Manga برایِ حفرهٔ بزرگِ
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

        # v1.14.62 — جاروی جوهرِ روشنِ باقی‌مانده «داخلِ» بلوک‌هایِ محفظهٔ
        # تیره (کارتِ عنوان). کاربر: «عکس‌ها را کامل خوب پاک کنه؛ اضافه پاک
        # کردن هم اشکال نداره». نمونهٔ واقعی: تکهٔ سفیدِ «S(» وسطِ کارتِ
        # Crimson Dragon که نه در کِیلِ پرکنندهٔ فوری بود و نه LaMa کامل
        # برداشت. داخلِ این بلوک‌ها هر پیکسلِ روشن (پس‌زمینهٔ کارت تیره است)
        # با رنگِ محلیِ خودِ صفحه (همان پرکنندهٔ فوریِ گرادیانی) پر می‌شود؛
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
                    # v1.14.94 — گاردِ زمینه: این سویپ فقط برایِ کارت‌هایِ
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
                                _rawW94 = getattr(
                                    self, "_page_raw_text_mask", None)
                                if (_rawW94 is not None
                                        and _rawW94.shape
                                        == image.shape[:2]):
                                    _ringW &= (cv2.dilate(
                                        _rawW94[_ry0W:_ry1W,
                                                _rx0W:_rx1W],
                                        np.ones((5, 5), np.uint8)) == 0)
                            except Exception:
                                pass
                            if int(_ringW.sum()) >= 120:
                                _ringV = _gOW[_ringW]
                                _rstdW = float(_ringV.std())
                                _rbriW = float((_ringV >= 140).mean())
                                # v1.14.96i — معیارِ stdِ حلقه حذف شد:
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
                    # v1.14.65 — آستانهٔ ۱۴۰ دست‌نخورده ماند: آزمایشِ سندباکس
                    # نشان داد آستانهٔ نسبی (med+26) بافتِ اسپَتِر خودِ کارت
                    # را هم می‌گیرد و «شبحِ تیره» می‌سازد. هالهٔ قرمز باید در
                    # «ماسک» پوشانده شود (اسنپ‌شات/LaMa)، نه با سویپ.
                    _bright = (_sub >= 140)
                    if _protW is not None:
                        _bright = _bright & (
                            _protW[_wy0:_wy1, _wx0:_wx1] == 0)
                        # v1.14.96j — حبابیِ OCR گاهی یک گلیف را از قلم
                        # می‌اندازد (Wِ «WICKED» در 012_p1) و نقشهٔ
                        # حفاظتِ ساختاری آن گلیفِ تنها را «قاب/خطِ
                        # روشن» می‌خواند و همیشه زنده نگهش می‌دارد.
                        # اجزایِ کوچکِ هم‌اندازهٔ حرف (<۱۲۰۰px و
                        # <۹۰px درازا) که داخلِ محفظهٔ تیرهٔ یکدست
                        # قفس شده‌اند = بقایایِ حرف‌اند، نه قاب —
                        # به سویپ برگردانده می‌شوند. قاب/پرتوِ
                        # کشیده دست‌نخورده می‌ماند.
                        try:
                            _bP96 = (_sub >= 140) & (
                                _protW[_wy0:_wy1, _wx0:_wx1] > 0)
                            if int(_bP96.sum()) > 0:
                                _nP96, _lP96, _sP96, _ = \
                                    cv2.connectedComponentsWithStats(
                                        _bP96.astype(np.uint8), 8)
                                for _jP96 in range(1, _nP96):
                                    _aP96 = int(_sP96[_jP96,
                                                      cv2.CC_STAT_AREA])
                                    _wP96 = int(_sP96[_jP96,
                                                      cv2.CC_STAT_WIDTH])
                                    _hP96 = int(_sP96[_jP96,
                                                      cv2.CC_STAT_HEIGHT])
                                    if _aP96 <= 1200 and \
                                            max(_wP96, _hP96) <= 90:
                                        _bright |= (_lP96 == _jP96)
                        except Exception:
                            pass
                    _bright = cv2.morphologyEx(
                        _bright.astype(np.uint8), cv2.MORPH_OPEN,
                        np.ones((3, 3), np.uint8)) > 0
                    if int(_bright.sum()) < 16:
                        continue
                    if float(_bright.mean()) > 0.5:
                        continue  # بلوک عمدتاً روشن؟ → این کارتِ تیره نیست
                    # v1.14.96i — گاردِ یکنواختیِ محفظه: سویپ فقط وقتی
                    # امن است که پیکسل‌هایِ تیرهٔ داخلِ باکس یکدست باشند
                    # (کارتِ سیاه/سرخِ صاف). محفظهٔ بافت‌مند/گرادیانی
                    # (نئبولای EXEC) با std تیره‌هایِ بالا رد می‌شود.
                    _darkM96 = ((_sub < 120).astype(np.uint8))
                    _dkV96 = _sub[_darkM96 > 0]
                    if _dkV96.size >= 200 and \
                            float(_dkV96.std()) > 30.0:
                        if self.debug:
                            print(f"  [✓]سویپِ جوهرِ روشن رد شد — "
                                  f"محفظهٔ یکدست نیست "
                                  f"(std={float(_dkV96.std()):.0f})",
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

        # v1.14.54 — روشِ «دو عکس» کاربر: عکسِ اول = پاک‌شدهٔ کامل (حتی اگر
        # حباب در آن خراب یا بیشتر پاک شده باشد — مهم نیست)، عکسِ دوم =
        # عکسِ اصلی که «خروجی» روی آن ساخته می‌شود. فقط نوارهایِ متن از
        # عکسِ اول برش می‌خورند؛ هر آسیبی که پاک‌سازی بیرونِ نوارها زده
        # باشد (دیوارِ حباب، بینِ خط‌ها، هنر) اینجا دور ریخته می‌شود.
        # سویپ‌هایِ بعدی روی همین تصویرِ ترکیب‌شده کار می‌کنند تا اگر جوهرِ
        # بیرونِ نوار مانده باشد، همان‌جا پاک شود.
        #
        # v1.14.60 — باگِ «متن پاک نشده»: کامپوز فقط با «ماسکِ بازمانده»
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
        # v1.14.81 — پروبِ نقطه‌ای: MANGA_PROBE="x,y" → مقدارِ cleaned در
        # هر مرحله چاپ می‌شود (ریشه‌یابیِ «چه مرحله‌ای پیکسل را کشت»)
        _probe81 = None
        try:
            _pv = os.environ.get("MANGA_PROBE", "")
            if _pv and "," in _pv:
                _px81, _py81 = [int(v) for v in _pv.split(",")]
                _probe81 = (_px81, _py81)
        except Exception:
            _probe81 = None
        if _probe81 is not None:
            print(f"  [🔍PROBE] start=({cleaned[_probe81[1], _probe81[0]]}) "
                  f"orig=({image[_probe81[1], _probe81[0]]})", flush=True)
        if _sdd:
            try:
                _si = int(getattr(self, "_stage_i", 0))
                self._stage_i = _si + 1
                _sd = os.path.join(_sdd, f"s{_si:02d}")
                os.makedirs(_sd, exist_ok=True)
                cv2.imwrite(os.path.join(_sd, "pre_compose.jpg"), cleaned)
                if _probe81 is not None:
                    print(f"  [🔍PROBE] pre_compose={cleaned[_probe81[1], _probe81[0]]}", flush=True)
            except Exception:
                _sd = ""
        # v1.14.63 — کامپوزِ دو-عکسیِ «خط‌به‌خطِ سخت»: فقط نوارِ متنِ خام
        # (نه پیکسل‌هایِ تغییرکردهٔ پراکنده، نه کلِ حباب/محفظه). قبلًا
        # «تغییرکرده ∪ ماسک» بود که کلِ حبابِ پُرشده را به خروجی می‌برد —
        # اعتراضِ کاربر: «چرا کلِ حباب رو منتقل می‌کنی؟ خط به خط برش بزن».
        if os.environ.get("MANGA_TWO_IMAGE", "1") != "0":
            try:
                _cmp2 = self._compose_strip_mask(image, mask)
            except Exception:
                _cmp2 = mask
            cleaned = self._compose_two_image(cleaned, image, _cmp2)
            # v1.14.73 — پولیشِ نوارها به «بعد از» سویپ‌ها منتقل شد:
            # سویپ‌هایِ LaMa/TELEA بعد از پولیش، بافتِ موتیلینگ را دوباره
            # روی نوارهایِ فلت‌شده می‌ریختند (شبحِ متن زنده می‌گشت).
        else:
            _cmp2 = None
        if _sdd and _sd:
            try:
                cv2.imwrite(os.path.join(_sd, "post_compose.jpg"), cleaned)
                if _probe81 is not None:
                    print(f"  [🔍PROBE] post_compose={cleaned[_probe81[1], _probe81[0]]}", flush=True)
            except Exception:
                pass

        _lama_fix = 0
        _kern_r = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        try:
            _n_res = 0
            # v1.14.74 — «سریع بپاکه بره دیگ»: بعد از کامپوزِ دو-عکسی،
            # دیگر هیچ «نجاتِ LaMa»ای اجرا نمی‌شود (موج‌هایِ «parallel
            # rescue patches» و «LaMa group rejected … منتظر می‌مونه» روی
            # گوشی ۵ دقیقه معطل می‌کردند). کیفیتِ نوارها در donor، قبل
            # از کامپوز تضمین شده (پرکنندهٔ فلت/LaMa + پولیشِ نوار)؛
            # جارویِ بقایا فقط با TELEA/پرِ فلتِ سریع کار می‌کند.
            # برای آزمایشِ قدیمی: MANGA_RESCUE_LAMA=1
            _rescue_lama = (os.environ.get("MANGA_RESCUE_LAMA", "0") == "1"
                            and bool(getattr(self, "use_lama", False))
                            and self._clean_level() != "fast")
            for _pass in range(3):
                _want_lama = (_pass >= 1 and _rescue_lama)
                _rboxes: List[Tuple[int, int, int, int, np.ndarray]] = []
                # v1.14.63 — جاروی بقایا با «ماسکِ متنِ خام» نه ماسکِ
                # کِیل‌شده: پرکننده‌هایِ فوری ماسک را کِیل می‌کنند و سویپ
                # قبلاً آن ناحیه‌ها را کامل رد می‌کرد (_m_px<80) → متنِ
                # قدیمیِ دست‌نخورده (نمونهٔ گوشی: «L» کنارِ «جملهٔ کوتاه»)
                # هرگز پیدا نمی‌شد. ماسکِ خام = همان نوارهایِ متن.
                _mres = getattr(self, "_compose_text_mask", None)
                if _mres is None or _mres.shape != mask.shape[:2]:
                    _mres = mask
                # v1.14.70 — دامنهٔ امن: فقط نوارهایِ متن (نه مستطیلِ
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
        _stage185("جارویِ پسماند")
        if _sdd and _sd:
            try:
                cv2.imwrite(os.path.join(_sd, "post_sweep.jpg"), cleaned)
            except Exception:
                pass

        # v1.14.48: جاروی لکهٔ محوِ داخلِ حباب‌هایِ سفید (halo حروف) —
        # نمونهٔ کاربر: لکهٔ وسطِ «BUT I LIKE IT HERE.» / نقطهٔ «MR. JUN~»
        try:
            _n_int = self._bubble_interior_sweep(image, cleaned, regions)
            if _n_int and self.debug:
                print(f"  [*] bubble sweep: {_n_int} fixed")
        except Exception:
            import traceback as _tb
            print("  [!] Bubble interior sweep error:")
            _tb.print_exc()
        _stage185("جارویِ حباب")

        # v1.14.75 — «گارانتیِ کامپوزِ دوباره»: بعدازِ همهٔ سویپ‌ها/سویپ
        # نجات/پولیش، خروجیِ نهایی دوباره با _compose_two_image روی
        # ماسکِ «کامپوزِ خط‌به‌خط» فیلتر می‌شود. قبلاً بعضی سویپ‌ها
        # (بقایا/حباب/نجات) بیرونِ نوارِ متن هم پیکسل عوض می‌کردند و
        # حباب — که عکسِ اولِ خرابش به خروجی نرسیده بود — برمی‌گشت
        # (نمونهٔ 01.jpg: حبابِ سفیدِ بزرگِ «THE VILLA'S POOL…»)
        try:
            if _cmp2 is not None:
                # v1.14.81 — قبل از کامپوزِ نهایی: پیکسل‌هایِ قفل‌شده
                # (خطِ حباب/قاب/تابِ نور) از اصل ترمیم می‌شوند تا نوارها
                # بُرشِ سالم ببرند — نه سیاهیِ LaMa، نه پرشِ فوری.
                # v1.14.96j — استثنا: گلیفِ تنهاِ جاافتاده (Wِ «WICKED»)
                # که نقشهٔ حفاظت آن را قاب خوانده — اگر از اصل ترمیم
                # شود، کامپوزِ نهایی خودِ متنِ اصلی را منتقل می‌کند!
                # اجزایِ کوچکِ هم‌اندازهٔ حرفِ محافظت‌شده که داخلِ
                # نوارهایِ کامپوز‌اند ترمیم «نمی‌شوند» تا پاک‌شدهٔ
                # سویپ/LaMa زنده بماند. قاب/خطِ کشیده مثلِ قبل ترمیم.
                try:
                    _pa81f = getattr(self, "_prot_all", None)
                    if _pa81f is not None and int(cv2.countNonZero(_pa81f)):
                        _sel81f = _pa81f > 0
                        try:
                            _ins96 = _sel81f & (_cmp2 > 0)
                            if int(_ins96.sum()) > 0:
                                _nG96, _lG96, _sG96, _ = \
                                    cv2.connectedComponentsWithStats(
                                        _ins96.astype(np.uint8), 8)
                                for _jG96 in range(1, _nG96):
                                    _aG96 = int(_sG96[_jG96,
                                                      cv2.CC_STAT_AREA])
                                    _wG96 = int(_sG96[_jG96,
                                                      cv2.CC_STAT_WIDTH])
                                    _hG96 = int(_sG96[_jG96,
                                                      cv2.CC_STAT_HEIGHT])
                                    if _aG96 <= 1200 and \
                                            max(_wG96, _hG96) <= 90:
                                        _sel81f &= ~(_lG96 == _jG96)
                        except Exception:
                            pass
                        cleaned[_sel81f] = image[_sel81f]
                except Exception:
                    pass
                cleaned = self._compose_two_image(cleaned, image, _cmp2,
                                                 verbose=False,
                                                 refill=True)
                try:
                    _sdd81z = os.environ.get("MANGA_STAGE_DUMP", "")
                    if _sdd81z:
                        cv2.imwrite(os.path.join(
                            _sdd81z, "post_recompose.jpg"), cleaned)
                except Exception:
                    pass
        except Exception:
            pass
        # v1.14.73 — پولیشِ نهاییِ نوارها — «بعد از» همهٔ سویپ‌ها:
        # حلقهٔ کاملاً یکنواخت (حبابِ سفید/رنگیِ تخت) → کلِ نوار + ۵px
        # هالهٔ دورِ آن با رنگِ اورجینالِ حلقه هم‌سطح می‌شود → شبحِ
        # ۱-۳ سطحیِ متن (که سویپ‌ها نمی‌بینندش) صفر می‌شود و هیچ
        # سویپی دیگر بعدش بافت نمی‌ریزد.
        if _cmp2 is not None:
            try:
                cleaned = self._compose_polish(image, cleaned, _cmp2)
            except Exception:
                pass
        # v1.14.213 — پولیشِ شبحِ نوار (دستورِ سازنده: «نه لگه سیاهی نه
        # لگه سفیدی یا هرنگی لگه بشه قبول نمیکنم»): بقایایِ نازکِ جوهر
        # که LaMa لبهٔ ماسکشان را نصفه گذاشته (خطوطِ ۱-۸px داخلِ نوار —
        # تیرگیِ ~۳۵ که سویپِ ۴۵+ و همسطحیِ پولیش نمی‌بینندش) با پرِ
        # پیازی از زمینهٔ تمیزِ اطراف پاک میشوند؛ فقط نوارهایِ کامپوز،
        # فقط اجزایِ نازکِ نزدیکِ جوهرِ متنِ اصلی و فقط حلقهٔ تخت — دیوار/
        # هنر/حبابهایِ بافت‌دار هرگز دست نمیخورند. MANGA_GHOST_POLISH=0
        # برایِ خاموشکردنِ دستی.
        if _cmp2 is not None \
                and os.environ.get("MANGA_GHOST_POLISH", "1") != "0":
            try:
                cleaned, _n_gp213 = self._strip_ghost_polish(
                    image, cleaned, _cmp2)
                if _n_gp213 and self.debug:
                    print(f"  [*] پولیشِ شبحِ نوار: {_n_gp213} پیکسل "
                          f"پاک شد")
            except Exception:
                pass
        if _sdd and _sd:
            try:
                cv2.imwrite(os.path.join(_sd, "post_polish.jpg"), cleaned)
            except Exception:
                pass

        # v1.14.75g — «پرِ پیازیِ نوارهایِ داخلِ حباب»: نوارهایِ متنِ
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
                # v1.14.78d — «گیتِ پیازی»: پیازی فقط برایِ زمینهٔ
                # تخت/گرادیانی (حباب/کارت) — جایی که donor رنگِ غلط
                # گرفته. رویِ هنرِ بافت‌مند (نرده/صورت/کت — img4)
                # پیازی بافتِ LaMa را به «ابر» تبدیل می‌کند
                # (1.9Mpx = ۲۴٪ صفحه!). معیار: کسری از حلقهٔ
                # اطرافِ جعبه که محله‌هایِ ۱۱px آن تخت است (std<12)
                # باید ≥۰٫۵ باشد؛ وگرنه جعبه از پیازی مستثنا می‌شود
                # و بافتِ بازسازیِ LaMa می‌ماند.
                try:
                    _g78o = cv2.cvtColor(
                        image, cv2.COLOR_BGR2GRAY).astype(np.float32)
                    _m78a = cv2.blur(_g78o, (11, 11))
                    _m78b = cv2.blur(_g78o * _g78o, (11, 11))
                    _std78 = np.sqrt(np.maximum(
                        _m78b - _m78a * _m78a, 0))
                    # v1.14.78e — علاوه بر «تخت»، «بی‌لبه» هم لازم است:
                    # پس‌زمینهٔ بوکهٔ ساختمان/نرده محلی-تخت است ولی
                    # لبه‌هایِ ساختاری دارد (میلهٔ نرده، قاب پنجره) —
                    # پیازی آن لبه‌ها را می‌بَرد (img4 PARAGRAPH2).
                    # تخت + بدونِ لبه = حباب/گرادیانِ نرم → پیازی اوکی.
                    _lap78 = np.abs(cv2.Laplacian(
                        _g78o, cv2.CV_32F))
                    _edgef78 = cv2.blur(
                        (_lap78 > 25.0).astype(np.float32),
                        (31, 31))
                    _flatf78 = ((cv2.blur(
                        (_std78 < 12.0).astype(np.float32),
                        (31, 31)) > 0.55)
                        & (_edgef78 < 0.06))
                except Exception:
                    _flatf78 = None
                for _dbT in (getattr(self, "_donor_boxes", None) or []):
                    _tx0, _ty0, _tx1, _ty1 = [int(v) for v in _dbT]
                    _tx0 = max(0, _tx0); _ty0 = max(0, _ty0)
                    _tx1 = min(cleaned.shape[1], _tx1)
                    _ty1 = min(cleaned.shape[0], _ty1)
                    if _tx1 - _tx0 >= 10 and _ty1 - _ty0 >= 10:
                        if _flatf78 is not None:
                            try:
                                _ry0, _ry1 = max(0, _ty0 - 12), min(
                                    _flatf78.shape[0], _ty1 + 12)
                                _rx0, _rx1 = max(0, _tx0 - 12), min(
                                    _flatf78.shape[1], _tx1 + 12)
                                _rg = np.zeros(
                                    (_ry1 - _ry0, _rx1 - _rx0),
                                    dtype=bool)
                                _rg[:, :] = _flatf78[_ry0:_ry1,
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
                    # v1.14.78b — «سدِ دیوار»: اگر donor یک ساختارِ تیرهٔ
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
                        _gO78 = cv2.cvtColor(
                            image, cv2.COLOR_BGR2GRAY).astype(np.float32)
                        _gC78 = cv2.cvtColor(
                            cleaned, cv2.COLOR_BGR2GRAY).astype(np.float32)
                        _bg78 = cv2.medianBlur(
                            _gO78.astype(np.uint8), 31).astype(np.float32)
                        _drk78 = (_gO78 < 120.0) | (
                            (_bg78 - _gO78) > 45.0)
                        _keep78 = cv2.dilate(
                            (_drk78 & (np.abs(_gC78 - _gO78) < 22.0)
                             ).astype(np.uint8),
                            np.ones((3, 3), np.uint8)) > 0
                        _keep78 &= _sel
                        if bool(_keep78.any()):
                            _sel = _sel & (~_keep78)
                            _known = np.maximum(
                                _known,
                                _keep78.astype(np.float32))
                            if self.debug:
                                print(f"  [🛡]"
                                      f"{int(_keep78.sum())}px دیوارِ "
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

        # v1.14.44: پاسِ مرجع حذف شد — درخواستِ کاربر: «این خط خط چیه؛
        # mm خوب می‌پاکه». پاسِ هندسی مرجع (v1.14.41) بعد از همهٔ پاس‌ها
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


        # v1.14.78c — «تیکِ جامانده»: جوهرِ کوچکِ ریز (نقطهٔ !، تیکِ جدا،
        # خشِ کوتاه) که ماسکِ نوار ندیده بود و در خروجی دست‌نخورده ماند
        # (نمونه: تیکِ 4x17 در (533,965) img7 کنارِ «ME BOMB..!»). فقط
        # داخلِ نوارهایِ متن، فقط لُختهٔ کوچکِ مستقل (≤300px، جعبه≤30)،
        # فقط اگر در اورجینال هم بخشی از ساختارِ کوچکِ مستقل باشد (نه
        # مو/هنرِ متصل) و نزدیکِ متنی که پاک شده → پیازی از اطرافِ
        # خروجی پر می‌شود. «به اندازهٔ متن» — چیزی اضافه پاک نمی‌شود.
        try:
            if _cmp2 is not None and int(np.count_nonzero(_cmp2)) > 40:
                _gO78c = cv2.cvtColor(
                    image, cv2.COLOR_BGR2GRAY).astype(np.float32)
                _gC78c = cv2.cvtColor(
                    cleaned, cv2.COLOR_BGR2GRAY).astype(np.float32)
                _bg78c = cv2.medianBlur(
                    _gO78c.astype(np.uint8), 31).astype(np.float32)
                _inkO = (_gO78c < 120.0) | ((_bg78c - _gO78c) > 45.0)
                # نوارِ گشادشده: تیکِ ندیده‌شده *داخلِ* ماسک نیست ولی در
                # باندِ همان خطِ متن است
                _zone78c = cv2.dilate(
                    _cmp2, cv2.getStructuringElement(
                        cv2.MORPH_ELLIPSE, (25, 25))) > 0
                _unch = _inkO & _zone78c & (
                    np.abs(_gC78c - _gO78c) < 18.0)
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
                                    & (_zone78c[_vy0:_vy1, _vx0:_vx1])
                                    & ~_unch[_vy0:_vy1, _vx0:_vx1])
                    if int(np.count_nonzero(_win_cleaned)) < 30:
                        continue  # متنِ همسایه پاک نشده → بخشی از آن متن
                    # زمینهٔ اطراف در اورجینال باید روشن و یکنواخت باشد
                    # (حباب/کادر) — نه بافتِ اسکرین‌تون/هنرِ پرنقطه
                    _ry0, _ry1 = max(0, _by0 - 7), min(
                        image.shape[0], _by1 + 7)
                    _rx0, _rx1 = max(0, _bx0 - 7), min(
                        image.shape[1], _bx1 + 7)
                    _ring78 = ~cv2.dilate(
                        _mB.astype(np.uint8),
                        np.ones((5, 5), np.uint8)).astype(bool)
                    _ring78[:_ry0, :] = False
                    _ring78[_ry1:, :] = False
                    _ring78[:, :_rx0] = False
                    _ring78[:, _rx1:] = False
                    _rgv = _gC78c[_ring78]  # v1.14.78c2 — زمینه از
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
        # v1.14.105 — وارسیِ نهاییِ ضدِ خرابیِ EP (یک‌بار برای کلِ صفحه):
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
        # v1.14.228 — QCِ پایانیِ هماهنگیِ پر (بعد از همهٔ سویپها).
        # درِ تستِ img4 همین پاس بود که نوارهایِ خاکستریِ باقیماندهٔ
        # r20/#13/#16 را سفید کرد (۱۷ قطعه/۴۳۳هزارpx) — قطعاتِ بعد از
        # سویپها بزرگترند (مرزهایِ ساختاریِ σ4) و حلقهشان پاکتر.
        # با MANGA_HQC_FINAL=0 خاموش میشود.
        if os.environ.get("MANGA_HQC_FINAL", "1") == "1" \
                and os.environ.get("MANGA_NO_HQC", "0") != "1":
            try:
                _zq228 = getattr(self, "_compose_final_cmp", None)
                if not isinstance(_zq228, np.ndarray) \
                        or _zq228.ndim < 2 or not bool(_zq228.any()):
                    _zq228 = _cmp2
                if isinstance(_zq228, np.ndarray) and _zq228.any():
                    self._fill_harmony_qc(cleaned, image, _zq228,
                                          verbose=self.debug or True)
                    _hqcd = os.environ.get("MANGA_HQC_DUMP", "")
                    if _hqcd:
                        cv2.imwrite(_hqcd, cleaned)
                        cv2.imwrite(_hqcd + ".zone.png",
                                    (_zq228.astype(np.uint8)) * 255)
                        print(f"  [*] HQC dump -> {_hqcd}", flush=True)
            except Exception:
                pass
        # v1.14.228 — جارویِ متنِ جاماندهٔ خوانا (دستورِ سازنده: «بعضی
        # متن هارو نپاکیده متن قبلیش دیده میشه» — نمونهٔ img4:
        # «…COUNSELING SESSION» رویِ کت، بیرونِ نوارِ ماسک).
        if os.environ.get("MANGA_NO_LEFTOVER", "0") != "1":
            try:
                self._leftover_text_sweep(cleaned, image, _cmp2, regions)
            except Exception:
                pass
        # v1.14.238 — جارویِ خرده‌گلیف/نقطه‌هایِ جاماندهٔ داخلِ ناحیه
        # (دستورِ سازنده: «وقتی میپاکه نقطه نقطه سیاه جا میزاره هر متن»).
        if os.environ.get("MANGA_DOT_SWEEP", "1") != "1":
            pass
        else:
            try:
                self._compose_dot_sweep(cleaned, image, _cmp2, regions,
                                        verbose=self.debug)
            except Exception:
                pass
        return cleaned

    def _compose_dot_sweep(self, cleaned: np.ndarray,
                           original: np.ndarray,
                           zone: Optional[np.ndarray],
                           regions: List[TextRegion],
                           verbose: bool = True) -> int:
        """v1.14.238 — جارویِ خرده‌گلیف/نقطه‌هایِ جاماندهٔ داخلِ ناحیه.

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
                        _cm238 = (lab == i)
                        # داخلِ نوارِ کامپوز = لکهٔ خودِ پرکننده — فقط
                        # خرده‌لکهٔ ریز مجاز (نه تکهٔ بزرگِ احتمالیِ هنر)
                        if bool((_cm238 & ex).any()):
                            if a > 300 or ww > 64 or hh > 44:
                                continue
                        gm[_cm238] = 255
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
                    n_fix += n_g
                    n_px += int(cv2.countNonZero(gm))
                    if verbose:
                        try:
                            print(f"  [✓238] جارویِ خرده‌گلیف: ناحیهٔ "
                                  f"{getattr(r, 'id', '?')} — {n_g} قطعه "
                                  f"({int(cv2.countNonZero(gm))}px) TELEA شد")
                        except Exception:
                            pass
                except Exception:
                    continue
            if verbose and n_fix:
                try:
                    print(f"  [✓238] جارویِ خرده‌گلیف: {n_fix} قطعه / "
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
        """v1.14.228 — جارویِ متنِ جاماندهٔ خوانا با گیتِ OCR.

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
                n_fix += 1
                n_px += _np
            if n_fix and verbose:
                try:
                    print(f"  [✓228] جارویِ متنِ جامانده: {n_fix} خط "
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
                    # v1.14.61 — بقایایِ جوهرِ «بیرونِ» ماسکِ هسته (مثلاً
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
                            # v1.14.64 — باگِ «متنِ کج یا ناقص»: قوسِ دیوارِ
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
                    _bx30, _by30 = max(0, x0 - 34), max(0, y0 - 34)
                    _bx31 = min(w, x1 + 34)
                    _by31 = min(h, y1 + 34)
                    if _bx31 - _bx30 < 20 or _by31 - _by30 < 20:
                        continue
                    _dseed = ((_mdil[_by30:_by31, _bx30:_bx31] > 0)
                              .astype(np.uint8) * 255)
                    _ddom = self._bubble_domain_local(
                        image[_by30:_by31, _bx30:_bx31], _dseed,
                        rect_box=(x0 - _bx30, y0 - _by30,
                                  x1 - x0, y1 - y0))
                    _paper_mode = False
                    if _ddom is None:
                        try:
                            _hc = cv2.cvtColor(
                                image[_by30:_by31, _bx30:_bx31],
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
                                    # v1.14.64 — ساختارِ کشیدهٔ نازک (قوسِ
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
                    # v1.14.48: اعتبارسنجیِ دیوار — دامینِ کاذب (موی/سایهٔ
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
                            # v1.14.48: بقایایِ واقعیِ متن داخلِ حبابِ سفید
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
            # v1.14.48: دیوارِ حباب/کادر (ساختارِ محافظت‌شده) هرگز resid
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
                    # ⚠️ برش باید پدینگ داشته باشد وگرنه رینگِ بیرونیِ ماسک
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
                    # v1.14.43: گیتِ ضدبافت — اگر خودِ رینگِ دورِ خط پر از
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
                    # v1.14.43: پرکردنِ جامد حذف شد — حتی وقتی رینگ «یکنواخت»
                    # است، روی گرادیان/سایهٔ نرم نوارِ تختِ هم‌رنگ می‌سازد
                    # (بلوکی که کاربر روی گوشی دید). هِیلِ IDW از خودِ
                    # پیرامون درون‌یابی می‌کند → روی گرادیان هم نامرئی است.
                    # v1.14.43: ترمیمِ جراحیِ جوهر — فقط پیکسل‌های جوهرِ
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


