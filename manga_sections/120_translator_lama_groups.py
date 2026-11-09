# BUILD-STRIP-START
# ─────────────────────────────────────────────────────────────
# ⚠️ MangaTranslator (۳ از ۱۳) — گروهبندی و اجرای LaMa: _lama_group_* ، rescue/telea
# این فایل «قطعهای از بدنهٔ کلاس MangaTranslator» است و بهتنهایی
# اجرا نمیشود — scripts/build_manga.py این محتوا را بههمان ترتیبِ
# شمارهٔ فایل، داخلِ کلاس در manga.py میچسباند. کلاسِ پوششیِ زیر فقط
# برای معتبر بودنِ سینتکسِ این فایلِ تکی است و موقعِ بیلد حذف میشود.
class _MangaTranslatorBody_120:
# BUILD-STRIP-END
    def _lama_group_prep(self, image: np.ndarray, members: List[list],
                         page_kernel) -> Optional[dict]:
        """v1.14.96-speed (SRV-G phase2) — فازِ «آماده‌سازی»ِ `_lama_run_group`
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
        # v1.14.65 — گروه‌هایِ بنرِ تبلیغ (promo): پدِ بزرگ‌تر الزامی است.
        # با پدِ معمولی (~40px) حفرهٔ بنر ~۵۰٪ کراپ را می‌گیرد و LaMa-Manga
        # «بنفشِ خیالی/صورتی» نقاشی می‌کند (بازتولیدِ سندباکس: بنرِ
        # ASURASCANS.COM). با پدِ ~۵۵٪ (حفره ~۲۰٪) مدل راه‌راه‌ها را
        # واقعاً ادامه می‌دهد — آزمایش: pad=130 → نتیجهٔ تمیز.
        try:
            for _pg in (getattr(self, "_promo_rect_boxes", None) or []):
                if not (gx1 < int(_pg[0]) or gx0 > int(_pg[2])
                        or gy1 < int(_pg[1]) or gy0 > int(_pg[3])):
                    _pp65 = int(np.clip(round(0.55 * max(bw, bh)), 48, 200))
                    pad_x = max(pad_x, _pp65)
                    pad_y = max(pad_y, _pp65)
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
        # v1.14.48: دیوارِ حباب/کادر از ماسکِ LaMa هم حذف شود تا به‌عنوان
        # زمینه بماند و بازسازی نشود
        _pp = getattr(self, "_page_protect", None)
        if _pp is not None:
            try:
                _pp_sub = _pp[ey0:ey1, ex0:ex1]
                if _pp_sub.shape == sub_msk.shape:
                    sub_msk[_pp_sub > 0] = 0
            except Exception:
                pass
        # v1.14.81 — ساختارِ روشنِ قفل‌شده (خطِ حباب/قابِ کارت) هم از
        # ماسکِ LaMa خارج شود — LaMa باید آن را «زمینه» ببیند، نه حفره
        # (وگرنه قابِ سفیدِ کارت با رنگِ کارت بازسازی می‌شد — img2-r10).
        try:
            _pa81g = getattr(self, "_prot_all", None)
            if _pa81g is not None:
                _pa_sub = _pa81g[ey0:ey1, ex0:ex1]
                if _pa_sub.shape == sub_msk.shape:
                    sub_msk[_pa_sub > 0] = 0
        except Exception:
            pass
        if not sub_msk.any():
            return  # v1.14.65: ماسکِ خالی — طبیعی، لاگ لازم نیست
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
        """v1.14.96-speed (SRV-G phase2) — همان `_lama_try` قبلی (بدنه دست
        نخورده) به‌صورتِ کارخانهٔ closure تا مسیرِ batched هم دقیقاً همان
        فال‌بک‌ها (EP-mortal → CPU-safe → resize-retry) را داشته باشد."""
        def _lama_try(si, sm, side):
            # v1.14.65b — حافظهٔ مرگِ EP: بعد از اولین ORT_FAIL واقعی،
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
                # v1.14.65 — سکوتِ ممنوع: EPِ پروب‌شده (مثلاً xnnpack) ورودیِ
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
        v1.14.96-speed (SRV-G phase2) — فقط بازچینی شد؛ رفتارِ بایت‌به‌بایت
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
        """v1.14.96-speed (SRV-G phase2) — فازِ «پس‌پردازشِ» `_lama_run_group`
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
                # v1.14.207d — QCِ «پرِ تیره» فقط وقتی معتبر است که حلقهٔ
                # کلاستر «واقعاً» روشن باشد. بنرِ سیاهِ «CHAPTER 1 PAGE 1»
                # (img1018) داخلِ کلاسترِ بالایِ صفحه بود؛ حلقهٔ ۳۱pxِ
                # کلاستر عمدتاً سفیدِ صفحه است → bg_med=۲۵۵ → پرِ «سیاهِ
                # درستِ» LaMa رویِ بنر رد میشد و جایگزینِ سفید = «لگهٔ
                # سفیدِ» بزرگ رویِ بنر. حالا اگر ≥۱۰٪ حلقه تیرهِ واقعی
                # باشد (زمینهٔ مختلط)، این QCِ کورِ سطحِ کلاستر پرش را رد
                # نمیکند؛ اعتبارسنجیِ محلیِ هر عضو (گاردِ ضدتوهم) خودش
                # درست قضاوت میکند.
                _darkqc207 = float((_bg_px < 110.0).mean())
                if (_bright.size >= max(50, int(0.02 * _bg_px.size))
                        and _bright.size >= 0.55 * _bg_px.size
                        and _darkqc207 < 0.10):
                    _bg_med = float(np.median(_bright))
                    _fill_med = float(np.median(_g[_fm]))
                    # v1.14.133 — اندروید: رویِ حلقهٔ تختِ روشن (حبابِ زرد)،
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
                    # v1.14.185 — اندروید (MANGA_GRAYQC): بلوکِ خاکستریِ
                    # LaMaِ xnnpack (پرِ ~۱۲۰-۱۸۰ رویِ حبابِ سفید/روشن)
                    # ازQCِ قدیمی می‌گذشت چون شرطِ قدیمی فقط «پرِ تیره‌ترِ
                    # 115» را میگرفت = «لکهٔ خاکستری» در خروجی (نمونه:
                    # حبابِ جرقهٔ صفحهٔ ژاپنیِ v1.14.184). حالا هر پرِ
                    # محسوسِ تیره‌تر از حلقهٔ روشن (≥۴۲ واحد) هم رد میشود
                    # و پرِ تختِ نجاتِ حلقه جایگزینش میشود. PC بیت‌به‌بیت.
                    _gray185 = False
                    if _android_gate("MANGA_GRAYQC"):
                        try:
                            _gray185 = (_bg_med >= 185.0
                                        and _fill_med < _bg_med - 42.0)
                        except Exception:
                            _gray185 = False
                    if _gray185 or (_fill_med < 115.0
                                    and _fill_med < _bg_med - _dqc_thr):
                        # v1.14.65 — لاگ شود؛ این ردِ خاموش = فال‌بکِ OpenCV
                        try:
                            print(f"    [!] LaMa group rejected: dark fill "
                                  f"({_fill_med:.0f} vs bg {_bg_med:.0f})",
                                  flush=True)
                        except Exception:
                            pass
                        # v1.14.133 — اندروید: به‌جایِ رهاشدن به TELEA (اسمیرِ
                        # کم‌رنگ رویِ حفرهٔ بزرگ)، اگر حلقه تختِ روشن است خودم
                        # با رنگِ میانهٔ حلقه پر می‌کنم (همان پرِ تختِ امن).
                        # پرِ موفق → return نمی‌خوریم تا کامیتِ پایینی اجرا
                        # شود؛ اعتبارسنجیِ عضویِ بعدی رویِ پرِ تختِ
                        # نجات‌یافته badf≈۰ می‌گیرد و دست نمی‌زند.
                        _rescued133 = False
                        # v1.14.212 — پیشفرضِ روشن رویِ PC هم: گروهِ ردشده
                        # (پرِ تیره) بدونِ نجات، یا متنِ اورجینال جا میماند
                        # یا فال‌بکِ Telea اسمیر میسازد (img6: 88 vs bg 226).
                        if _gate_default_on("MANGA_FILL_RESCUE"):
                            try:
                                # v1.14.213 — نجاتِ «عضو به عضو» به‌جایِ
                                # پرِ تختِ کلِ گروه (دستورِ سازنده: «نه لگه
                                # سیاهی نه لگه سفیدی یا هرنگی لگه بشه قبول
                                # نمیکنم»): پرِ تختِ یکرنگِ کلِ ماسکِ گروه
                                # رویِ حبابِ گرادیانی = «لکهٔ سفیدِ
                                # مستطیلی» (GO! EVEN FASTER — img6). حالا
                                # هر عضو (خطِ متن) با ماسکِ خودش و حلقهٔ
                                # «محلیِ روشنِ» خودش ردیف‌به‌ردیف پر میشود —
                                # رنگِ محلیِ همان خط + گرادیانِ عمودیِ
                                # حفظشده؛ عضوی که حلقهٔ معتبر ندارد به پرِ
                                # تختِ محلیِ خودش برمیگردد.
                                _sub_g213 = cv2.cvtColor(
                                    sub_img, cv2.COLOR_BGR2GRAY)
                                _resc_px = 0
                                _resc_rows = 0
                                sub_bgr = sub_bgr.copy()
                                for _mem213 in members:
                                    try:
                                        _mx0, _my0, _mx1, _my1, _mm = \
                                            _mem213[:5]
                                        _mm213 = np.zeros(
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
                                        _mm213[_oy0:_oy1, _ox0:_ox1] = \
                                            (_mmk.astype(np.uint8)) * 255
                                        _mm213 = cv2.dilate(
                                            _mm213, page_kernel)
                                        _mfm = (_mm213 > 0) & _fm
                                        if not _mfm.any():
                                            continue
                                        _tmask213 = (_mfm.astype(np.uint8)) * 255
                                        _inp213 = cv2.inpaint(
                                            sub_bgr, _tmask213, 5,
                                            cv2.INPAINT_TELEA)
                                        sub_bgr[_mfm] = _inp213[_mfm]
                                        _resc_px += int(_mfm.sum())
                                    except Exception:
                                        continue
                                if _resc_px > 0:
                                    _rescued133 = True
                                    print(f"    [✓] پرِ عضو-به-عضویِ نجات از "
                                          f"حلقهٔ محلی ({_resc_px}px، "
                                          f"{_resc_rows} ردیفِ گرادیانی)",
                                          flush=True)
                                else:
                                    # هیچ عضوی حلقهٔ معتبر نداشت → پرِ تختِ
                                    # کل (رفتارِ ۲۱۲)
                                    _src133 = _ring
                                    _b133 = _bg_px >= 160.0
                                    if float(_b133.mean()) < 0.98:
                                        _ri133 = np.where(_ring)
                                        _bi = np.where(_b133)[0]
                                        _src133 = (_ri133[0][_bi],
                                                   _ri133[1][_bi])
                                    _px133 = sub_img[_src133].astype(
                                        np.float32)
                                    _rc133 = np.median(_px133, axis=0)
                                    _sd133 = float(np.std(_px133))
                                    if _sd133 <= 40.0 and np.isfinite(
                                            _rc133).all():
                                        sub_bgr[_fm] = np.clip(
                                            np.rint(_rc133), 0, 255).astype(
                                                np.uint8)
                                        _rescued133 = True
                                        print(f"    [✓] پرِ تختِ نجات از حلقه "
                                              f"(rgb="
                                              f"{_rc133.round(0).tolist()})",
                                              flush=True)
                            except Exception:
                                _rescued133 = False
                        if not _rescued133:
                            return
        except Exception:
            pass
        # v1.14.140/141 — اندروید (MANGA_DARKSMOKE): QCِ «پرِ ناهمخوان
        # با حلقه» رویِ زمینهٔ تیره/مختلط. بلوکِ بالایی فقط حلقهٔ روشن
        # (≥۵۵٪ پیکسل ≥160) را بازرسی میکند؛ رویِ کتِ تیرهٔ (#20)
        # صفحهٔ 700×11362 حلقه مختلط است (دستکشِ روشن + کت) → LaMaِ
        # xnnpack در داوناسکیلِ پچِ 512 «دودِ خاکستری» (تیره — لاگِ
        # گوشیِ v1.14.139) یا «هَزِ روشن» (آرتیفکتِ شبیهساز) میسازد و
        # بدونِ هیچ بازرسی به خروجی میرود = «لگه». v1.14.142 —
        # تریگرِ بی‌قطبیت: (الف) دود — انرژیِ فرکانس-بالایِ پر ≫ حلقه
        # (hf_in > 2.2×hf_ring+4 و hf_in>6)، یا (ب) ناهمخوانیِ
        # روشنایی — |پر − حلقه| > 22. درمان: پرِ «ردیفی» از حلقهٔ
        # همان ردیف (گرادیانِ قائم حفظ؛ ردیفِ هنری/شلوغ همان LaMa را
        # نگه میدارد). PC بیت‌به‌بیت.
        try:
            if _android_gate("MANGA_DARKSMOKE") and _fm.any() \
                    and _ring.any():
                _g140 = cv2.cvtColor(sub_bgr, cv2.COLOR_BGR2GRAY)
                _rmed140 = float(np.median(_g140[_ring]))
                _fmed140 = float(np.median(_g140[_fm]))
                # v1.14.186 — اندروید (MANGA_SOFTQC): کلاسِ جدیدِ «لکهٔ
                # شیری» — پرِ LaMa رویِ زمینهٔ بافت‌دار (کتِ بژِ صفحهٔ
                # ژاپنیِ v1.14.184) که روشناییاش به حلقه نزدیک است
                # (از QCِ تیره/دود رد میشود) ولی بافتِ داخلِ پر تقریباً
                # صفر است در حالیکه حلقه بافتِ واقعی دارد = اسمیرِ
                # نیمه‌شفافِ لباس/هنر. دروازهٔ ارزان: stdِ حلقه؛ بعد
                # سنجشِ hf. PC بیت‌به‌بیت.
                _soft186 = False
                _rstd186 = 0.0
                if _android_gate("MANGA_SOFTQC") \
                        and abs(_fmed140 - _rmed140) <= 22.0 \
                        and _rmed140 >= 140.0:
                    try:
                        _rstd186 = float(_g140[_ring].std())
                        if _rstd186 >= 14.0:
                            _med186 = cv2.medianBlur(_g140, 31)
                            _hf186 = np.abs(
                                _g140.astype(np.int16)
                                - _med186.astype(np.int16))
                            _hf_in = float(np.median(_hf186[_fm]))
                            _hf_rg = float(np.median(_hf186[_ring]))
                            _hf_sd = float(_hf186[_fm].std())
                            _soft186 = (_hf_rg >= 7.0
                                        and _hf_in < max(3.0,
                                                         0.35 * _hf_rg)
                                        and _hf_sd <= 3.0)
                    except Exception:
                        _soft186 = False
                if _soft186 or abs(_fmed140 - _rmed140) > 22.0 or \
                        _rmed140 < 140.0:
                    if not _soft186:
                        _med140 = cv2.medianBlur(_g140, 31)
                        _hf140 = np.abs(
                            _g140.astype(np.int16)
                            - _med140.astype(np.int16))
                        _hf_in = float(np.median(_hf140[_fm]))
                        _hf_rg = float(np.median(_hf140[_ring]))
                    if _soft186 or (_hf_in > 2.2 * _hf_rg + 4.0
                                    and _hf_in > 6.0) or \
                            abs(_fmed140 - _rmed140) > 22.0:
                        # v1.14.140b — پرِ «ردیفی» از حلقهٔ همان ردیف
                        # (بهجایِ پرِ تختِ کل): هر ردیفِ ماسک که نمونهٔ
                        # آزادِ کافیِ یکدست دارد با میانهٔ همان ردیف
                        # پر میشود → گرادیانِ عمودیِ کت/دیوار حفظ و
                        # چینِ کت (stdِ کلِ حلقه بالا ولی هر ردیف صاف)
                        # هم پوشش داده میشود؛ ردیفِ شلوغ (هنر) همان
                        # LaMa را نگه میدارد.
                        _hW140 = _fm.shape[1]
                        _rOK = np.zeros(_fm.shape[0], bool)
                        _rC = np.zeros((_fm.shape[0], 3), np.float32)
                        for _ri in range(_fm.shape[0]):
                            _free = ~_fm[_ri]
                            _nf = int(_free.sum())
                            if _nf < 12 or _nf > int(0.9 * _hW140):
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
                            _fill140 = np.repeat(
                                _rC[:, None, :], _hW140, axis=1)
                            sub_bgr = sub_bgr.copy()
                            sub_bgr[_fm] = np.clip(
                                _fill140, 0, 255).astype(
                                    np.uint8)[_fm]
                            # v1.14.186b — f-stringِ چندخطی در 3.11
                            # سینتکس-ارور میداد (PEP 701 = 3.12) → لیبل
                            # قبل از print محاسبه میشود
                            _tag140 = ("ضدِ لکهٔ شیری (SOFTQC)"
                                       if _soft186 else
                                       "ضدِ دودِ زمینهٔ تیره")
                            print(f"    [✓] {_tag140}: "
                                  f"hf={_hf_in:.1f} vs "
                                  f"حلقه={_hf_rg:.1f} → پرِ ردیفیِ "
                                  f"حلقه ({int(_okI.size)}/"
                                  f"{_fm.shape[0]} ردیف)",
                                  flush=True)
        except Exception:
            pass
        # v1.14.49 — اعتبارسنجیِ ضدتوهمِ هر عضو: LaMa-Manga وقتی حفرهٔ بزرگ
        # داخلِ حبابِ سفید می‌بیند گاهی «محتوا» (صورت/بافتِ درخت/بافتِ
        # اسکرین‌تونِ درشت) نقاشی می‌کند (لاگِ کاربر: حبابِ «YOU'RE
        # LEAVING…» سیاه/صورت شد). اگر ماسکِ عضو بخشِ عمدهٔ اینتریورِ یک
        # حبابِ سفید را بپوشاند و نتیجهٔ LaMa محتوایِ تیرهٔ «درشت» داشته
        # باشد → همان عضو با رنگِ تختِ زمینه پر می‌شود (کارِ flat).
        # گاردها: نقطه‌هایِ ریزِ اسکرین‌تون با OPEN حذف می‌شوند؛ ماسکِ
        # کوچک (متنِ کنارِ عکسِ داخلِ حباب) اعتبارسنجی نمی‌شود تا عکس
        # قانونی قربانی نشود.
        try:
            _k49 = getattr(self, "_qc_kernel31", None)
            if _k49 is None:
                _k49 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
                self._qc_kernel31 = _k49
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
                # v1.14.227 — QCِ کروما (رنگ، نه فقط روشنایی) — «قبل از»
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
                    _sic227 = sub_img[oy:oy + dm.shape[0],
                                      ox:ox + dm.shape[1]]
                    _rc227 = sub_bgr[oy:oy + dm.shape[0],
                                     ox:ox + dm.shape[1]]
                    _ch227, _cw227 = mm.shape[:2]
                    _cell227 = 112

                    _wins227 = []
                    _tofix227 = []
                    # انرژیِ فرکانس-بالای زمینه (ضدِ هنرِ هموارنما):
                    # مو/پوستِ رگه‌دار (img4_s02: پیشانی) رنگِ غالب و
                    # stdِ پایین دارد ولی بافتِ ریزش hf بالا است — حباب/
                    # آسمانِ تخت hf≈۰. فقط حلقههایِ تختِ واقعی سنجیده
                    # میشوند.
                    try:
                        _gS227 = cv2.cvtColor(_sic227,
                                              cv2.COLOR_BGR2GRAY)
                        _hfS227 = np.abs(
                            _gS227.astype(np.float32)
                            - cv2.medianBlur(_gS227, 31).astype(
                                np.float32))
                    except Exception:
                        _hfS227 = None
                    _gy227 = 0
                    while _gy227 < _ch227:
                        _gx227 = 0
                        while _gx227 < _cw227:
                            _win227 = mm[_gy227:_gy227 + _cell227,
                                         _gx227:_gx227 + _cell227]
                            if int(_win227.sum()) >= 200:
                                _pad227 = np.zeros(mm.shape, np.uint8)
                                _pad227[_gy227:_gy227 + _cell227,
                                        _gx227:_gx227 + _cell227] = \
                                    _win227.astype(np.uint8) * 255
                                _ring227 = (cv2.dilate(
                                    _pad227, _k49) > 0) & (~mm)
                                if int(_ring227.sum()) >= 40:
                                    _rngC227 = _sic227[
                                        _ring227].astype(np.float32)
                                    _flC227 = _rc227[
                                        _gy227:_gy227 + _cell227,
                                        _gx227:_gx227 + _cell227][
                                            _win227].astype(np.float32)
                                    if _flC227.shape[0] >= 40:
                                        _rmedC227 = np.median(
                                            _rngC227, axis=0)
                                        # رنگِ غالب: سهمِ پیکسلهایِ حلقه
                                        # که در ≤۳۰ از میانهاند — بهتر از
                                        # std (خطِ دیوار/دورخطِ نازک در
                                        # حلقهٔ سالم دیگر رد نمیکند)
                                        _fracC227 = float((np.max(
                                            np.abs(_rngC227
                                                   - _rmedC227),
                                            axis=1) <= 30.0).mean())
                                        _fmedC227 = np.median(
                                            _flC227, axis=0)
                                        _fstdC227 = float(np.std(
                                            _flC227, axis=0).max())
                                        _rstdC227 = float(np.std(
                                            _rngC227, axis=0).max())
                                        _hfC227 = 0.0
                                        if _hfS227 is not None:
                                            try:
                                                _hfC227 = float(np.median(
                                                    _hfS227[_ring227]))
                                            except Exception:
                                                _hfC227 = 0.0
                                        _dch227 = float(np.max(np.abs(
                                            _fmedC227 - _rmedC227)))
                                        # v1.14.227b — قانونِ «کروما یا
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
                                        _rel227 = ((_rmedC227 - _fmedC227)
                                                   / np.maximum(_rmedC227,
                                                                40.0))
                                        _chroma227 = float(np.max(np.abs(
                                            _rel227 - np.median(_rel227)))) \
                                            >= 0.25
                                        _extreme227 = (
                                            (float(np.min(_rmedC227))
                                             >= 200.0)
                                            or (float(np.max(_rmedC227))
                                                <= 70.0))
                                        # گاردِ سه‌گانه: رنگِ غالب ≥۵۵٪
                                        # «و» stdِ کانالیِ حلقه ≤۳۴ «و»
                                        # hfِ حلقه ≤۶ — هنرِ هموارنما
                                        # (مو/پوست) بافت/پراکندگی دارد؛
                                        # بازسازیِ LaMa رویِ چنین حلقههایی
                                        # قانونی است و دست نمی‌زنیم.
                                        if (_fracC227 >= 0.55
                                                and _rstdC227 <= 34.0
                                                and _hfC227 <= 6.0
                                                and _fstdC227 <= 46.0
                                                and _dch227 >= 48.0
                                                and (_chroma227
                                                     or _extreme227)):
                                            # v1.14.241 — گاردِ «حلقه باید
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
                                            # لومیایِ حلقه سنجیده میشود؛
                                            # فاصلهٔ >۶۰ = حلقه زمینهٔ
                                            # دیگری است → پنجره دستنخورده.
                                            # v1.14.241 — سنجشِ «پر در
                                            # برابرِ زمینهٔ زیرِ خودِ
                                            # پنجره»: زمینهٔ زیر = قطبِ
                                            # روشنِ اورجینالِ زیرِ ماسک
                                            # (جوهرِ متن اقلیت است؛
                                            # صدکِ ۷۵ ≈ زمینه). اگر پر با
                                            # آن همرنگ بود، پر درست است و
                                            # حلقه (که هنرِ مجاور را
                                            # میبیند — مویِ قهوهای/کتِ
                                            # تیره) حقِ قضاوت ندارد.
                                            _skip241 = False
                                            try:
                                                _uw241 = _sic227[
                                                    _gy227:_gy227 + _cell227,
                                                    _gx227:_gx227 + _cell227
                                                ][_win227]
                                                if _uw241.shape[0] >= 40:
                                                    _ul241b = float(np.percentile(
                                                        0.299 * _uw241[:, 2]
                                                        + 0.587 * _uw241[:, 1]
                                                        + 0.114 * _uw241[:, 0],
                                                        75.0))
                                                    _fl241b = float(
                                                        0.299 * _fmedC227[2]
                                                        + 0.587 * _fmedC227[1]
                                                        + 0.114 * _fmedC227[0])
                                                    if abs(_fl241b
                                                           - _ul241b) < 45.0:
                                                        if os.environ.get(
                                                                "MANGA_GUARD_DBG"):
                                                            print(
                                                                f"      [227d"
                                                                f"241] win@("
                                                                f"{_gx227 + cx0},"
                                                                f"{_gy227 + cy0})"
                                                                f" پر==زمینهٔ"
                                                                f" زیر ({_fl241b:.0f}"
                                                                f"≈{_ul241b:.0f})"
                                                                f" → رد",
                                                                flush=True)
                                                        # False = حلقه
                                                        # نمایندهٔ زمینهٔ
                                                        # زیرِ پنجره نیست؛
                                                        # سرایت هم حقِ
                                                        # ترمیم ندارد
                                                        _wins227.append(
                                                            (False, _gy227,
                                                             _gx227,
                                                             _win227,
                                                             _fmedC227,
                                                             _dch227,
                                                             _rmedC227,
                                                             _fstdC227,
                                                             _fracC227,
                                                             _rstdC227,
                                                             _hfC227))
                                                        _skip241 = True
                                            except Exception:
                                                pass
                                            if not _skip241:
                                                _tofix227.append(
                                                    (_gy227, _gx227, _win227,
                                                     _fmedC227, _dch227,
                                                     _rmedC227, "",
                                                     _fracC227, _rstdC227,
                                                     _hfC227, _fstdC227))
                                        else:
                                            _wins227.append(
                                                (True, _gy227, _gx227,
                                                 _win227, _fmedC227,
                                                 _dch227, _rmedC227,
                                                 _fstdC227, _fracC227,
                                                 _rstdC227, _hfC227))
                            _gx227 += _cell227
                        _gy227 += _cell227
                    # دورِ سرایتِ رنگ: پنجرهٔ ترمیم‌نشده که «پرِ»اش همان
                    # رنگِ غلطِ پنجرهٔ ترمیم‌شده است (Δ≤۱۲ — همان لکهٔ
                    # LaMa ادامه دارد) و با رنگِ غالبِ حلقهٔ خودش هم
                    # نمیخواند (غالبِ ≥۴۰٪، Δ≥۴۸) → همان درمان؛ تا لبهٔ
                    # لکه نصفه نماند (پنجره‌های مرزیِ آسمان+زرد).
                    _fm227 = [t[3] for t in _tofix227]
                    for (_dmy227, _gy227, _gx227, _win227, _fmedC227,
                         _dch227, _rmedC227, _fstdC227, _fracC227,
                         _rstdC227, _hfC227) in _wins227:
                        # سرایت بدونِ گاردِ rstd: پرِ این پنجره عینِ پرِ
                        # غلطِ پنجرهٔ ترمیم‌شده است (Δ≤۱۲) — یعنی همان
                        # لکهی LaMa ادامه دارد، نه بازسازیِ هنر؛ گاردِ
                        # هنرِ متقارن لازم نیست. مرزهایِ دو رنگِ همپوشان
                        # (آسمان+زرد) همین‌جا ترمیم میشوند. hfِ هنری همچنان
                        # رد میشود (بافتِ ریز = بازسازیِ قانونیِ LaMa).
                        if not _dmy227:
                            continue  # v1.14.241 — پنجرهٔ «حلقه≠زمینه» ترمیم/سرایت ممنوع
                        if _fstdC227 > 46.0 or _hfC227 > 6.0 \
                                or _fracC227 < 0.40 or _dch227 < 48.0:
                            continue
                        # قانونِ کروما/قطب اینجا هم (لنگرِ سرایت معاف
                        # نیست — پرِ همفامِ تیرهتر تناسبی رد).
                        if any(float(np.max(np.abs(
                                _fmedC227 - _f2_227))) <= 12.0
                               for _f2_227 in _fm227):
                            _tofix227.append(
                                (_gy227, _gx227, _win227, _fmedC227,
                                 _dch227, _rmedC227, "(سرایت)",
                                 _fracC227, _rstdC227, _hfC227,
                                 _fstdC227))
                    # یک پخشِ واحد برای «همهٔ» پنجرههایِ تصمیمشده:
                    # مرز = پیکسلهایِ اصلِ بیرونِ ماسک + پرهایِ درستِ
                    # داخلِ ماسک (پنجرهٔ زرد-روی-زرد مرزِ درست میماند)؛
                    # نه پخشِ تک‌پنجره‌ای که از لکهٔ همسایه آلوده میشد.
                    if _tofix227:
                        # پرِ «محلی» به‌ازایِ پنجره: برازشِ صفحهٔ
                        # z=a+bx+cy رویِ زیرمجموعهٔ غالبِ حلقهٔ «همان
                        # پنجره» (بدون نشتِ رنگِ حبابِ همسایه — پخش/
                        # میانگینِ جعبه‌ای زردِ #02 را تا آسمانِ #04
                        # میکشید)؛ بعدِ پر، نوارِ لبهٔ ۴px با تار کردن
                        # نرم میشود تا درزِ پنجرهها/findها دیده نشود.
                        try:
                            _union227 = np.zeros(mm.shape, bool)
                            for (_gyF, _gxF, _winF, _fmedF, _dchF,
                                 _rmedF, _whyF, _frac227d, _rstd227d,
                                 _hf227d, _fstd227d) in _tofix227:
                                _union227[_gyF:_gyF + _cell227,
                                          _gxF:_gxF + _cell227] |= _winF
                            for (_gyF, _gxF, _winF, _fmedF, _dchF,
                                 _rmedF, _whyF, _frac227d, _rstd227d,
                                 _hf227d, _fstd227d) in _tofix227:
                                _padF = np.zeros(mm.shape, np.uint8)
                                _padF[_gyF:_gyF + _cell227,
                                      _gxF:_gxF + _cell227] = \
                                    _winF.astype(np.uint8) * 255
                                _winfF = _padF > 0
                                _ringF = (cv2.dilate(
                                    _padF, _k49) > 0) & (~mm)
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
                                    _rcF = _sic227[_ringF].astype(
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
                                                    if (_mSlO * _cell227
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
                                                        _union227 |= \
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
                                            if (_maxSlopeF * _cell227
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
                                _union227 |= _useF
                                if not _useF.any():
                                    continue
                                _subF = _rc227[_gyF:_gyF + _cell227,
                                               _gxF:_gxF + _cell227]
                                _subW = _useF[_gyF:_gyF + _cell227,
                                              _gxF:_gxF + _cell227]
                                _flatF = np.clip(
                                    np.rint(np.asarray(
                                        _rmedF, np.float32)),
                                    0, 255).astype(np.uint8)
                                if _planeImgF is None or _hasPF is None:
                                    _subF[_subW] = _flatF
                                else:
                                    _pwF = _planeImgF[
                                        _gyF:_gyF + _cell227,
                                        _gxF:_gxF + _cell227]
                                    _hwF = _hasPF[
                                        _gyF:_gyF + _cell227,
                                        _gxF:_gxF + _cell227]
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
                                _union227.astype(np.uint8),
                                np.ones((9, 9), np.uint8)) > 0
                            _bandF = _union227 & (~_edgeF)
                            if _bandF.any():
                                _blE = cv2.blur(
                                    _rc227.astype(np.float32), (9, 9))
                                _rc227[_bandF] = np.clip(
                                    np.rint(_blE), 0,
                                    255).astype(np.uint8)[_bandF]
                        except Exception:
                            for (_gyF, _gxF, _winF, _fmedF, _dchF,
                                 _rmedF, _whyF, _frac227d, _rstd227d,
                                 _hf227d, _fstd227d) in _tofix227:
                                _colF = np.zeros(_rc227.shape, np.uint8)
                                _colF[:, :] = np.clip(
                                    np.rint(_rmedF),
                                    0, 255).astype(np.uint8)
                                _subF = _rc227[_gyF:_gyF + _cell227,
                                               _gxF:_gxF + _cell227]
                                _subF[_winF] = _colF[
                                    _gyF:_gyF + _cell227,
                                    _gxF:_gxF + _cell227][_winF]
                        for (_gyF, _gxF, _winF, _fmedF, _dchF, _rmedF,
                             _whyF, _frac227d, _rstd227d, _hf227d,
                             _fstd227d) in _tofix227:
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
                                      f"{_frac227d:.2f} rstd="
                                      f"{_rstd227d:.0f} hf="
                                      f"{_hf227d:.1f} fstd="
                                      f"{_fstd227d:.0f}",
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
                # v1.14.50: فقط «حبابِ واقعی» — رویِ عکس (پاراگرافِ روی حصار در
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
                    # v1.14.53: cv2.countNonZero روی آرایهٔ bool exception
                    # می‌داد → except → _ring_blk=True → مسیرِ ok49 از
                    # v1.14.50 همیشه مُرده بود و همیشه فال‌بک اجرا می‌شد!
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
                # v1.14.51 — نشتِ اینتریور (دو صورتِ مختلف):
                # ۱) حبابِ لبهٔ صفحه/دیوارِ شکافته روی زمینهٔ سفید — لاگِ گوشیِ
                # v1.14.50: حبابِ «YOU'RE LEAVING…» → اینتریور از شکافِ دیوار
                # به پنلِ بیرون نشت می‌کند (int≈۴۱Kpx، t4=4، wall_ok=False)
                # → حبابِ واقعی «ناحیهٔ باز» خوانده شد → توهمِ LaMa (صورتِ
                # خاکستری + لکهٔ سیاه) قبول شد.
                # ۲) حبابِ روی هنرِ تیره — «OH BOY…» روی نیمکت: نشت به
                # نیمکتِ قهوه‌ای med_i را به ~۱۴۰ می‌کاهد → «حبابِ سفید
                # نیست» → اعتبارسنجی رد → LaMa نیمکت را داخلِ حباب کامل
                # می‌کند → حباب کلاً پاک می‌شود (بازتولیدِ سندباکس).
                # فال‌بکِ محلیِ مشترک: کامپوننتِ «روشنِ» چسبیده به خودِ ماسک
                # (درونِ کراپ) = زمینهٔ سفیدِ محلی. اگر بزرگ (≥۵۵٪ ماسک)،
                # روشن (med≥۲۲۵)، یکنواخت (≥۷۵٪) و ماسک ≥۴۵٪ آن را بپوشاند
                # → «زمینهٔ سفید» معتبر است؛ تصمیمِ نهایی را چکِ badf
                # (توهمِ تیره) می‌گیرد. عکس/هنر (بافتِ تیره/مخلوط) رد می‌شود
                # (اندازه‌گیری: همهٔ نواحیِ عکسِ 9.jpg رد ✓ بدونِ رگرسیون).
                # v1.14.52 — گیتِ «متنِ داخلِ اینتریور»: اعتبار‌سنجیِ ضدتوهم فقط
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
                _ok49 = (_med_i >= 185.0 and _cov >= 0.45 and not _ring_blk
                         and _wall_ok and _uni >= 0.80 and _t4 < 4
                         and _m_in_i >= 0.55)
                if _dbg:
                    print(f"      [🛡dbg] m_in_i={_m_in_i:.2f}", flush=True)
                _fb_comp = None
                if not _ok49:
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
                        # v1.14.51b: کامپوننتِ روشن گاهی از شکافِ دیوار به
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
                        # v1.14.52: مثلِ ok49 — متنِ عضو باید عمدتاً داخلِ
                        # کامپوننتِ روشنِ تأییدشده باشد (کپشنِ رویِ هنر:
                        # fcov=۰.۵۲ ولی m_in_c=۰.۳۲ → رد ✓)
                        _m_in_c = (float(np.count_nonzero(mm & _fb_comp))
                                   / max(1, _n_mm))
                        # v1.14.94e — آستانهٔ uni: ۰.۷۵ → ۰.۶۰. کارت‌هایِ
                        # معرفی رویِ پنلِ عکس‌دار (GLENDA HOLLY — img1018)
                        # اینتریورِ کاملاً یکنواخت ندارند (لبهٔ عکس/سایه در
                        # کامپوننت‌ هست → uni≈۰.۶۶) و اعتبارسنجیِ
                        # ضدتوهم رد می‌شد → لکهٔ سیاهِ LaMa در باکسِ سفید
                        # می‌ماند. بقیهٔ گیت‌ها (med≥۲۲۵، fcov≥۰.۴۵،
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
                ring = (cv2.dilate(dm, _k49) > 0) & (~mm)
                if int(ring.sum()) < 80:
                    continue
                rg = _gcr[ring]
                if rg.size < 80:
                    continue
                # v1.14.207j — درِ «متنِ پاکنشده» (مستقل از قطب): گاردهای
                # قبلی فقط «پرِ تیره‌تر از حلقهٔ روشن» را خطرناک میدانستند؛
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
                    # v1.14.207m — _ppc در این نقطه از حلقه هنوز ساخته
                    # نشده (در بلوکِ ردِ پایینتر ساخته میشود) → نامِ
                    # تعریفنشده = استثنایِ خاموش = گیتِ بیاثر. اینجا
                    # نسخهٔ محلیِ خودش را میسازد.
                    _ppcJ = None
                    try:
                        _pp49J = getattr(self, "_page_protect", None)
                        if _pp49J is not None:
                            _ptJ = _pp49J[cy0:cy1, cx0:cx1]
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
                            # v1.14.207k — فقط «جوهرِ جامانده» پر شود نه
                            # کلِ عضو: پرِ تختِ سراسری، بازسازیِ سالمِ
                            # LaMa را هم نابود میکرد (r0/r7 — bN جهش).
                            # ماسکِ جراحی = (جوهر ∩ دستنخورده) + ۵px،
                            # محدود به mm؛ رنگ = قطبِ غالبِ حلقهٔ هر
                            # کامپوننتِ باقیمانده.
                            # v1.14.207l — «روشنشدههایِ بيجا»: پیکسلِ
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
                                # v1.14.207n — رنگِ قطبِ «سطحِ عضو» بهعنوانِ
                                # پشتیبان: برایِ تودههایِ بزرگِ باقیمانده،
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
                # v1.14.51: عضوِ فال‌بک‌تأییدشده (اینتریورِ سفیدِ چسبیده به
                # ماسک) گیتِ «حلقه عمدتاً سفید» را رد می‌کند — حبابِ روی
                # هنرِ تیره (OH BOY روی نیمکت) حلقهٔ تیره دارد ولی داخلش
                # سفید است؛ bg_med از پیکسل‌هایِ روشنِ حلقه هنوز درست درمی‌آید.
                if _fb_comp is None and _rbm < 0.50:
                    # v1.14.207f — تصویرِ آینهٔ همین گارد: حلقهٔ «تیره»
                    # (متنِ روشن رویِ بنر/پنلِ سیاه — «CHAPTER 1 PAGE 1»
                    # در img1018). گاردِ قدیمی اینجا «اعتبارسنجی نه» میکرد
                    # و پرِ سفیدِ توهمیِ LaMa (یا متنِ پاکنشدهٔ روشن)
                    # بدونِ چک میماند. حالا: اگر حلقه عمدتاً تیره است و
                    # پرِ داخلِ ماسک همچنان «روشن» (≥۳۵٪ ≥۱۷۰)، عضو رد
                    # میشود و ماسکِ عضو با «قطبِ غالبِ حلقهٔ هر کامپوننت»
                    # پر میشود — بنر سیاهِ خالص، حبابِ رویِ پنلِ تیره
                    # رنگِ پنل.
                    try:
                        _dkr207f = float((rg < 110.0).mean())
                        _fg207f = _g_out[oy:oy + dm.shape[0],
                                         ox:ox + dm.shape[1]][mm]
                        _brt207f = (float((_fg207f >= 170.0).mean())
                                    if _fg207f.size else 0.0)
                        if _dbg:
                            print(f"      [🛡dbg] dark-ring mirror "
                                  f"dark={_dkr207f:.2f} "
                                  f"fillbright={_brt207f:.2f}", flush=True)
                        if _dkr207f >= 0.50 and _brt207f >= 0.35:
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
                # v1.14.51: پرِ تختِ «اینتریور» — کراپ اول به تصویرِ اصل
                # برمی‌گردد (خروجیِ توهم‌زدهِ LaMa کامل حذف می‌شود)، بعد فقط
                # mm ∩ همسایگیِ کامپوننتِ روشن (اینتریورِ سفیدِ واقعی + ۵px)
                # با رنگِ همان کامپوننت پر می‌شود → دیوار/نیمکت/هنرِ اطراف
                # دست‌نخورده می‌ماند (بازتولید: b03 و OH BOY تمیز).
                _rc = sub_bgr[oy:oy + dm.shape[0], ox:ox + dm.shape[1]]
                _sic = sub_img[oy:oy + dm.shape[0], ox:ox + dm.shape[1]]
                _pp49 = getattr(self, "_page_protect", None)
                _ppc = None
                if _pp49 is not None:
                    try:
                        _pt = _pp49[cy0:cy1, cx0:cx1]
                        if _pt.shape[:2] == _rc.shape[:2]:
                            _ppc = _pt
                    except Exception:
                        _ppc = None
                if _fb_comp is not None:
                    _fill_col = np.median(
                        _sic[_fb_comp].astype(np.float32), axis=0)
                    # v1.14.53: «نسخهٔ پرشدهٔ» comp — جزیره‌هایِ تیرهٔ متنِ
                    # داخلِ زمینهٔ روشن جزوِ آن می‌شوند ولی دیوارِ حباب (که
                    # از بیرون به زمینهٔ وصل است) هرگز حفره حساب نمی‌شود.
                    # قبلاً cd_e≈comp خودِ حروف را «حفره» می‌دید → جوهرِ
                    # وسطِ حروف از پر افت می‌افتاد → شبحِ متن می‌ماند و
                    # residue-sweep بعداً برای پاک کردنش دیوار را هم می‌بلعید
                    # (حبابِ کامل پاک می‌شد — chapter-264/8).
                    _ffc = self._fill_holes_mask(_fb_comp)
                    _cm49 = float(np.median(_gcr[_fb_comp]))
                    _ink8 = ((_gcr < _cm49 - 40.0) & (dm > 0) & _ffc)
                    _ink8 = _ink8.astype(np.uint8) * 255
                    _ink8 = cv2.morphologyEx(_ink8, cv2.MORPH_CLOSE,
                                             np.ones((5, 5), np.uint8))
                    _ink8 = cv2.dilate(_ink8, np.ones((5, 5), np.uint8))
                    _ink8[~_ffc] = 0  # سقف: هرگز بیرونِ نسخهٔ پرشده (دیوار)
                    # v1.14.70 — نشتِ اینتریور (دمِ بازِ حباب) نباید متن را
                    # زنده بگذارد: جوهرِ تیرهٔ داخلِ ماسک (بدونِ گیتِ comp)
                    _ink8b = self._mask_ink_only(_gcr, dm, _cm49 - 40.0)
                    _pnt = mm & ((cv2.dilate(
                        _fb_comp.astype(np.uint8),
                        np.ones((3, 3), np.uint8)) > 0) | (_ink8 > 0)
                        | (_ink8b > 0))
                else:
                    # v1.14.53: مسیرِ ok49 هم «پوسته‌ای» شد — قبلاً _pnt=mm
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
                    # v1.14.70 — «متنِ کج/ناقص پاک میشه» و «بعضی متن‌ها
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
                # v1.14.70 — «بازگشت به اصل» فقط بیرونِ ماسک: قبلاً کلِ
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
                    # v1.14.207e — پسگیریِ «متنِ جامانده در پسگیریِ گارد»:
                    # _pnt فقط «اینتریور/کامپوننتِ روشن ∪ جوهرِ تیره» را پر
                    # میکرد؛ متنِ «روشن» رویِ زمینهٔ تیره (بنرِ سیاهِ
                    # CHAPTER PAGE — img1018) نه در کامپوننتِ روشن بود نه
                    # جوهرِ تیره → بعدِ ردِ LaMa به اصلِ خودش برمیگشت =
                    # متنِ سفیدِ کامل رویِ بنر. حالا هر پیکسلِ ماسک که
                    # «جوهرمانند» است (تفاوتِ >۴۲ با زمینهٔ محلیِ تخمینیِ
                    # 207b) هم پر میشود؛ پیکسلِ همرنگِ زمینه (دیوار/بافت)
                    # مثلِ قبل به اصل برمیگردد.
                    _fill207 = None
                    try:
                        _kn207 = (~mm).astype(np.float32)
                        _sicf207 = _sic.astype(np.float32) * _kn207[..., None]
                        _den207 = cv2.boxFilter(_kn207, -1, (25, 25))
                        _num207 = cv2.boxFilter(_sicf207, -1, (25, 25))
                        _loc207 = (_num207
                                   / np.maximum(_den207, 1e-3)[..., None])
                        # v1.14.207b — میانگینِ ساده رویِ زمینهٔ «دوقطبی»
                        # (بنرِ سیاه + حروفِ سفیدِ کنارِ ماسک — img1018)
                        # رنگِ خاکستریِ ناخالص میدهد. پس پرِ محلی =
                        # «قطبِ غالبِ محلی» (همان منطقِ دو-قطبیِ 206d):
                        # در هر پنجره بینِ قطبِ تیره و روشنِ پیکسلهایِ
                        # معلوم، قطبی که تراکمش بیشتر است برنده میشود —
                        # رویِ بنرِ سیاه سیاهِ خالص، رویِ حبابِ سفید سفید،
                        # رویِ حبابِ ماتِ رنگی رنگِ مات.
                        try:
                            _g207b = cv2.cvtColor(
                                _sic, cv2.COLOR_BGR2GRAY).astype(np.float32)
                            _drk207 = ((_g207b < 110.0)
                                       & (_kn207 > 0)).astype(np.float32)
                            _brt207 = ((_g207b >= 110.0)
                                       & (_kn207 > 0)).astype(np.float32)
                            _denD = cv2.boxFilter(_drk207, -1, (25, 25))
                            _denB = cv2.boxFilter(_brt207, -1, (25, 25))
                            _locD = (cv2.boxFilter(
                                _sic.astype(np.float32) * _drk207[..., None],
                                -1, (25, 25))
                                / np.maximum(_denD, 1e-3)[..., None])
                            _locB = (cv2.boxFilter(
                                _sic.astype(np.float32) * _brt207[..., None],
                                -1, (25, 25))
                                / np.maximum(_denB, 1e-3)[..., None])
                            _poleD = (_denD >= _denB)[..., None]
                            _locP = np.where(_poleD, _locD, _locB)
                            _valP = np.maximum(_denD, _denB)
                            _loc207 = np.where(
                                (_valP >= 0.03)[..., None], _locP, _loc207)
                        except Exception:
                            pass
                        _fill207 = np.where(
                            (_den207 >= 0.03)[..., None],
                            _loc207.astype(np.uint8),
                            np.broadcast_to(np.asarray(
                                _fill_col, dtype=np.uint8), _loc207.shape))
                        try:
                            # v1.14.207i — پسگیریِ «متنِ جامانده» به روشِ
                            # کامپوننت‌محور: تخمینِ پیکسلیِ 207b کنارِ
                            # حروفِ سفیدِ بنر توسطِ لبههایِ روشنِ بیرونِ
                            # ماسک آلوده میشد (|g-bg|<42 → پر نشد → متن
                            # برمیگشت). برای هر کامپوننتِ «ماسکِ بدونِ
                            # _pnt»: رنگ = قطبِ غالبِ حلقهٔ ۱۳px دورِ
                            # کامپوننت (پایدار، بدونِ لبههایِ حروف)؛ اگر
                            # خودِ کامپوننت با آن رنگ فاصلهٔ معنیدار
                            # داشته = جوهر است → پر.
                            _gSic207i = cv2.cvtColor(
                                _sic, cv2.COLOR_BGR2GRAY)
                            _res207i = mm & (~_pnt)
                            if _ppc is not None:
                                _res207i = _res207i & (_ppc == 0)
                            _cc207i = []
                            if _res207i.any():
                                _nCi, _labCi = cv2.connectedComponents(
                                    _res207i.astype(np.uint8), 8)
                                for _ic in range(1, _nCi):
                                    _cmC = (_labCi == _ic)
                                    _ringC = (cv2.dilate(
                                        _cmC.astype(np.uint8),
                                        np.ones((13, 13), np.uint8)) > 0) \
                                        & (~mm)
                                    _rgC = _gSic207i[_ringC]
                                    if _rgC.size < 20:
                                        continue
                                    if float((_rgC < 110.0).mean()) >= 0.5:
                                        _selC = _ringC & (_gSic207i < 110.0)
                                    else:
                                        _selC = _ringC & (_gSic207i >= 110.0)
                                    if int(_selC.sum()) < 8:
                                        _selC = _ringC
                                    _colC = np.median(
                                        _sic[_selC].astype(np.float32),
                                        axis=0)
                                    _dC = np.abs(
                                        _gSic207i[_cmC].astype(np.float32)
                                        - (0.299 * _colC[2]
                                           + 0.587 * _colC[1]
                                           + 0.114 * _colC[0]))
                                    if float(_dC.mean()) > 42.0:
                                        _pnt = _pnt | _cmC
                                        _cc207i.append(
                                            (_cmC, _colC.astype(np.uint8)))
                        except Exception:
                            _cc207i = []
                    except Exception:
                        _fill207 = None
                        _cc207i = []
                    if _pnt.any():
                        if _fill207 is not None:
                            _rc[_pnt] = _fill207[_pnt]
                        else:
                            _rc[_pnt] = _fill_col
                        # v1.14.207i — رنگِ قطبِ حلقهٔ هر کامپوننتِ
                        # «جوهرِ شناساییشده» رویِ پرِ عمومی مینشیند
                        try:
                            for _cmC, _colC in (_cc207i or []):
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
            # v1.14.81 — ماسکِ نتیجه هم از پیکسل‌هایِ قفل‌شده تمیز شود
            try:
                _pa81m = getattr(self, "_prot_all", None)
                if _pa81m is not None:
                    _pa_c = _pa81m[cy0:cy1, cx0:cx1]
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
        """v1.14.99 (SRV-H4) — بچینگِ پچ‌هایِ LaMa پیش‌فرضِ خاموش (رویِ
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
        """v1.14.96-speed (SRV-G phase2) — اجرایِ دسته‌ایِ پچ‌هایِ LaMa-Manga.

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
        """v1.14.70 — جوهرِ تیرهٔ داخلِ ماسک (بدونِ گیتِ اینتریور).

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
        # v1.14.44: سرعتِ LaMa — درخواستِ کاربر «سرعتِ پاکسازیِ lama سریع‌تر کن».
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
        # v1.14.45: مانند مسیرِ اصلی — پچِ کم → نخِ بیشتر برای هر پچ
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
            # v1.14.96-speed (SRV-G phase2) — بچینگِ rescue هم مثلِ مسیرِ اصلی
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
            # v1.14.48: دیوارِ محافظت‌شده در rescue هم دست‌نخورده بماند
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
                # v1.14.61 — TELEA رویِ زمینهٔ تختِ روشن (داخلِ حبابِ سفید)
                # خاکستریِ لکه‌دار/مستطیلِ محو می‌سازد (لاگِ گوشی: حباب‌هایِ
                # 002 — «لگه میزاره»). اگر رینگِ اطرافِ ماسک تخت و روشن است
                # → پرکردن با رنگِ خودِ زمینه (همان سبکِ پرکننده‌ها)؛
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
        """v1.14.47 — پرکردنِ فوریِ متنِ روی محفظهٔ تیرهٔ یکدست (بنرِ هدر،
        حبابِ سیاه). مستقیم با TELEA و رنگِ خودِ محفظه پر می‌شود و پیکسل‌ها
        از ماسکِ اصلی حذف می‌شوند تا حلقهٔ کلاسترها دیگر سراغشان نرود —
        چون ringِ پرکننده‌ها روی بنرِ نازک همیشه به بیرون نشت می‌کند و لگه
        می‌سازد."""
        n_fill = 0
        for region in regions:
            # v1.14.73 — ناحیهٔ donor-گسترش‌یافته: پرِ فوری نگیرد تا LaMa
            # کلِ داخل را با بافتِ خودش بازسازی کند (حالتِ کیفی)
            if skip_ids and int(getattr(region, "id", -1)) in skip_ids:
                continue
            # v1.14.65 — بنرِ تبلیغ (promo): پرکنندهٔ فوریِ محفظه نباید
            # ماسکِ توپرِ بنر را بکُشد (همان حفرهٔ رویِ متنِ بنر)
            if getattr(region, "kind", "") == "promo":
                continue
            # v1.14.82 — ناحیهِ «فقط-جوهر»: پرِ فوریِ محفظه/هاله ممنوع —
            # پرکنندهِ میانه‌ای روی هنرِ داخلِ کارت لکهِ تخت می‌گذارد.
            # جوهرش با LaMa پاک می‌شود.
            try:
                _ib81f = getattr(self, "_lama_ink_boxes", None) or []
                if _ib81f:
                    _rx81, _ry81, _rw81, _rh81 = [
                        int(v) for v in region.rect]
                    _hit81 = False
                    for _ib in _ib81f:
                        if not (_rx81 + _rw81 < _ib[0] or _rx81 > _ib[2]
                                or _ry81 + _rh81 < _ib[1]
                                or _ry81 > _ib[3]):
                            _hit81 = True
                            break
                    if _hit81:
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
                # v1.14.67 — حاشیهٔ ۲۰px (قبلاً ۱۲): گشادکردنِ ۱۳pxِ ماسکِ
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
                # v1.14.60 — هاله/درخششِ اطرافِ حروف (نمونه: تیترِ «The
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
                        # v1.14.81c — «نزدیکِ جوهر» نه «نزدیکِ کلِ محفظه»!
                        # قبلاً دیلهٔ ۲۵ِ خودِ enc بود و در محفظهٔ بزرگ
                        # (کارتِ img2-r10، حبابِ بزرگ) هر ساختارِ روشنِ
                        # داخلِ محفظه — قابِ سفیدِ کارت، خطِ حباب — را هم
                        # «هالهٔ حروف» می‌گرفت و با رنگِ کارت پاک می‌کرد
                        # («حباب به کل حذف زده» — گزارشِ کاربر).
                        # حالاseed = ماسکِ خامِ متن (_compose_text_mask)؛
                        # اگر خالی بود fallback به enc.
                        try:
                            _ctm81 = getattr(self, "_compose_text_mask",
                                             None)
                            _mk81w = None
                            if (_ctm81 is not None
                                    and _ctm81.shape == enc.shape):
                                _mk81w = ((_ctm81[y0:y1, x0:x1] > 0)
                                          .astype(np.uint8))
                            if (int(cv2.countNonZero(_mk81w)) < 50
                                    if _mk81w is not None else True):
                                _mk81w = ((enc[y0:y1, x0:x1] > 0)
                                          .astype(np.uint8))
                        except Exception:
                            _mk81w = ((enc[y0:y1, x0:x1] > 0)
                                      .astype(np.uint8))
                        _near = cv2.dilate(
                            _mk81w,
                            np.ones((25, 25), np.uint8)) > 0
                        _halo = (_gg >= 110) & _fc & _near & (m2 == 0)
                        if int(_halo.sum()):
                            m2 = m2 | _halo.astype(np.uint8)
                        # v1.14.67 — هالهٔ گرمِ «تیره» (قرمزِ گلو روی کارتِ
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
                        # v1.14.67 — برجستگی/سایهٔ متنِ روشن روی کارتِ تیره
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
                # v1.14.81b — تابِ نورِ پس‌زمینه (قفلِ نرم) قربانیِ
                # هاله‌گیری نشود — پرتوِ نور پشتِ متن باید بماند
                try:
                    _pg81e = getattr(self, "_prot_glow", None)
                    if (_pg81e is not None
                            and _pg81e.shape == enc.shape):
                        _sub81e = _pg81e[y0:y1, x0:x1] > 0
                        if int(_sub81e.sum()):
                            m2 = m2 & (~_sub81e).astype(np.uint8)
                except Exception:
                    pass
                # v1.14.47: TELEA روی متنِ درشتِ روی بنر، خاکستریِ لکه‌دار
                # می‌سازد (لبه‌هایِ نویزیِ JPEG را پخش می‌کند). رنگِ هر
                # پیکسل = میانهٔ محلیِ پیکسل‌هایِ تیرهٔ خودِ محفظه بیرونِ
                # جوهر → روی بنرِ سیاه، سیاهِ خالص؛ روی بنرِ گرادیانی،
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
                # v1.14.47: حلقهٔ padِ دورِ ماسکِ این ناحیه هم حذف شود تا
                # حلقهٔ کلاسترها روی پس‌ماندِ آن لکه نسازد
                # (v1.14.60: کِیل بر اساس m2 — شاملِ هالهٔ پرشده هم هست)
                _kill = cv2.dilate(m2, np.ones((9, 9), np.uint8)) > 0
                mask[y0:y1, x0:x1][_kill] = 0
                n_fill += 1
            except Exception:
                continue
        return n_fill

