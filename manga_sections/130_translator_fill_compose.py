# BUILD-STRIP-START
# ─────────────────────────────────────────────────────────────
# ⚠️ MangaTranslator (۴ از ۱۳) — پرکردن و ترکیب: نوارهای چرخیده، compose_polish، بافت، QC، clean_image
# این فایل «قطعهای از بدنهٔ کلاس MangaTranslator» است و بهتنهایی
# اجرا نمیشود — scripts/build_manga.py این محتوا را بههمان ترتیبِ
# شمارهٔ فایل، داخلِ کلاس در manga.py میچسباند. کلاسِ پوششیِ زیر فقط
# برای معتبر بودنِ سینتکسِ این فایلِ تکی است و موقعِ بیلد حذف میشود.
class _MangaTranslatorBody_130:
# BUILD-STRIP-END
    def _ink_bg_dark(self, image: np.ndarray, ink: np.ndarray) -> bool:
        """v1.14.62b — آیا زمینهٔ دورِ جوهرِ این ناحیه واقعاً تیره است؟
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
        """v1.14.48c — آزادسازیِ حافظهٔ کش‌شده به OS بینِ فازهایِ سنگین.
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
        """v1.14.104 — اینتریورِ «بالنِ سیستم» (باکسِ مشخصاتِ سفید).

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
        """v1.14.238 — نوارهایِ خط‌به‌خط برایِ نواحیِ «چرخیده».

        ریشهٔ سه شکایتِ همزمان (حبابِ زردِ چپ‌بریدهٔ img6 با زاویهٔ
        -۹.۵°، تابلوهایِ MINISTRYِ img4 با -۱۵/-۱۹.۳°، خطِ جاماندهٔ
        10.jpg با -۱۵°): نوارِ محور-ترازِ متنِ کج (۱) از دیوارِ حباب
        رد میشود → حلقهٔ رنگِ پر، داخل+بیرونِ حباب را قاطی میکند →
        «لکهٔ سبز-خاکستری روی زرد»؛ (۲) لبهٔ نوار وسطِ حروف میگذرد و
        گاردِ ساختار (v1.14.64) تکههایِ گلیفِ چسبیده به لبه را از
        ماسک بیرون میکشد → «نقطه‌های سیاه»؛ (۳) خطوطِ کج در یک سطلِ
        y می‌افتند → نوارِ چاق. راه‌حل: برشِ ناحیه با +angle همسطح
        میشود (قراردادِ همسطح‌سازیِ OCR و _max_font_for_region —
        v1.14.244: علامتِ درست؛ قبلاً -angle بود و کجی را «دوبرابر»
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
            # v1.14.244 — علامتِ + : زاویهٔ مثبت = نزولی-به-راست (قراردادِ y-down)؛
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
        """v1.14.70 — نوارهایِ خط‌به‌خطِ «اندازهٔ دقیقِ متن» برایِ یک ناحیه.

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
            # v1.14.238 — نواحیِ چرخیده (|angle| ≥ ۳°): نوارها در فضای
            # همسطح‌شده ساخته میشوند — نوارِ محور-ترازِ متنِ کج از دیوارِ
            # حباب رد میشود (لکهٔ رنگِ قاطی) و لبه‌اش حروف را میبرد
            # (نقطه‌های سیاه). MANGA_ROT_STRIPS=0 = خاموش.
            try:
                _ang238 = float(getattr(region, "angle", 0.0) or 0.0)
            except Exception:
                _ang238 = 0.0
            if 3.0 <= abs(_ang238) <= 45.0 \
                    and os.environ.get("MANGA_ROT_STRIPS", "1") != "0":
                _rot238 = self._rotated_region_strips(image, polys, _ang238)
                if _rot238 is not None:
                    return _rot238
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
                    # v1.14.70 — خطی که نوارش ساخته نشد (مثلِ متنِ سفید با
                    # دورخطِ تیره روی زمینهٔ روشن) نباید از کامپوز بیفتد وگرنه
                    # متن از عکسِ دوم برمی‌گردد («WE FRIENDS?»). برایِ این
                    # خط، پالیِ خودش جایگزین می‌شود (اندازهٔ متن).
                    # v1.14.241 — بازگشت به قراردادِ testm: «کلِ پالی» از
                    # donor منتقل میشود. جایگزینِ v1.14.206 فقط «جوهرِ
                    # دو-قطبیِ ±۴۵» را منتقل میکرد و بلوکِ مورفولوژیِ
                    # میله‌ها بهخاطرِ NameErrorِ _fu8 (متغیر هرگز تعریف
                    # نشده بود → except بیصدا) هرگز اجرا نمیشد → متنِ
                    # کمرنگ/آنتی‌الیاس‌شدهٔ اسنادِ وبتون (9.jpg: ARTICLEها
                    # و y=9536) و حروفِ کم‌کنتراستِ img6 («THE FLOAT FOR
                    # YOU!») در عکسِ دوم زنده میماند = «متنِ قبلی میماند،
                    # شبحِ خاکستری، لکه» — گزارشِ سازنده. حصارِ img4
                    # (نگرانیِ 206) اکنون دو لایهٔ دیگر دارد: (۱) 206c
                    # نوارِ سالمِ متن را میسازد و خط به این شاخه نمیافتد؛
                    # (۲) پانچِ میلهٔ نازکِ بلند پایین — میلهٔ حصار/قاب از
                    # پالیِ خط حذف میشود ولی حروف (تیره + ضخیم؛
                    # GUARDIANS/TEACHERS) میمانند.
                    try:
                        for _pa in polys:
                            _bx0 = float(_pa[:, 0].min())
                            _bx1 = float(_pa[:, 0].max())
                            _by0 = float(_pa[:, 1].min())
                            _by1 = float(_pa[:, 1].max())
                            if (_bx1 >= lx0 - 2 and _bx0 <= lx1 + 2
                                    and _by1 >= ly0 - 2 and _by0 <= ly1 + 2):
                                # v1.14.241b — بدونِ پانچِ میله: پانچِ
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
                # v1.14.205 — شبحِ لبهٔ حروف: ماسکِ پاکسازی هستهٔ تیره + هالهٔ
                # ۱۴..۳۰ را میگیرد ولی پیکسلهایِ خیلی روشنِ لبهٔ حرف
                # (≤۱۴ سطح از زمینه) را نه؛ کامپوزِ فقط-هسته آنها را از عکسِ
                # اورجینال برمی‌گرداند = شبحِ خوانایِ «ALSO» در حبابِ
                # «YOU SHOULD ALSO…» (img7 — گزارشِ سازنده: «متن also هم
                # دیده میشه یا پاک نشده یا نگرفته؟»). پیکسلهایِ روشنِ چسبیده
                # به هسته (≤۳px) از عکسِ پاک‌شده بیایند — پیکسلی که پاک
                # نشده در هر دو عکس یکسان است پس خطری ندارد و زمینهٔ هنریِ
                # پرقاومت (|Δ|>۱۴ — حصارِ پشتِ ARTICLEها) همچنان از
                # اورجینال میماند.
                try:
                    _g205 = cv2.cvtColor(image[sy0:sy1, sx0:sx1],
                                         cv2.COLOR_BGR2GRAY)
                    _med205 = float(np.median(_g205))
                    _lite205 = (np.abs(_g205.astype(np.float32) - _med205)
                                <= 14.0)
                    _kd205 = cv2.dilate(kept.astype(np.uint8),
                                        np.ones((7, 7), np.uint8)) > 0
                    _add205 = _kd205 & _lite205 & (~kept)
                    if _add205.any():
                        m[sy0:sy1, sx0:sx1][_add205] = 255
                except Exception:
                    pass
                n += 1
            if n == 0:
                # هیچ خطی نوار نشد → کلِ ناحیه به مسیرِ خام سپرده شود
                return None, failed
            # v1.14.70 — «نه بیشتر نه کمتر»: نوارها فقط داخلِ پالیِ OCR
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
            # v1.14.134 — پسگیرِ جوهرِ جامانده در کامپوز:
            # قطعههایِ گلیفِ بیرونِ پالی ('Yo'/'th'/'a' — 01.jpg) باید در
            # نوارِ انتقال هم بیایند وگرنه «فقط-نوار» آنها را از عکسِ
            # اصلی زنده نگه میدارد. همگام با ماسکِ پاکسازی.
            # v1.14.206 — رویِ PC هم فعال شد (هر دو پلتفرم باید خوب پاک
            # کند؛ env=0 خاموش میکند).
            if os.environ.get("MANGA_INK_RECLAIM", "1") != "0":
                try:
                    _base134 = cv2.bitwise_or(m, failed)
                    _add134 = self._stray_ink_reclaim(image, _base134,
                                                      [region])
                    if _add134 is not None and np.any(_add134):
                        _add134 = cv2.bitwise_and(
                            _add134, cv2.bitwise_not(_base134))
                        m = cv2.bitwise_or(m, _add134)
                except Exception:
                    pass
            # v1.14.206m — ساختارِ محافظتشده (دیوار/قابِ رنگی) هرگز از
            # نوارِ کامپوز منتقل نمیشود — حتی تکههایِ داخلِ پالی+۷ —
            # تا پرِ LaMa که رنگِ قاب را به داخلِ متن کشیده (لکهٔ سبزِ
            # حبابِ ۳ در up0822) جایِ قابِ اصلی را نگیرد؛ قاب همیشه
            # پیکسلِ عکسِ دوم است.
            # v1.14.206m — «قابِ رنگی» هرگز از نوارِ کامپوز منتقل نمیشود
            # — حتی تکههایِ داخلِ پالی+۷. قاب در ماسکِ فعال میماند (LaMa
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
        """v1.14.63 — ماسکِ کامپوزِ «فقط نوارِ متن، خط به خط»:
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
            # v1.14.76 — «صفرِ شوِرَه»: ماسکِ پایه (که enclosure/پرِ فوری
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
            # v1.14.104 — هر فراخوانیِ کامپوز، گروه‌هایِ سیستم را از نو
            # پردازش کند (کامپوز دوبار صدا می‌شود: اصلی + گارانتیِ نهایی)
            self._compose_sys_done = set()
            h, w = mask.shape[:2]
            # v1.14.70 — «نه بیشتر نه کمتر»: برایِ هر ناحیه‌ای که پالیِ
            # OCR دارد، نوارهایِ خط‌به‌خط (اندازهٔ دقیقِ حروف) جایِ
            # مستطیلِ بلوکِ ماسکِ خام می‌نشینند. نتیجه: دیوارِ حباب،
            # قوس، قابِ پنل و هنرِ اطراف هرگز از عکسِ پاک‌شده نمی‌آیند
            # → حباب سالم می‌ماند؛ فقط خودِ حروف پاک می‌شوند.
            _regions = getattr(self, "_page_regions", None) or []
            _n_str = 0
            # v1.14.70 — دامنهٔ امنِ «جارویِ بقایا»: فقط نوارهایِ متن.
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
                # v1.14.78f — «بلوکِ باندِ تیره»: اگر متن روی باندِ
                # نیمه‌شفافِ تیره باشد (PARAGRAPHهایِ img4 روی حصار)،
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
                            # v1.14.96 — گاردِ بافت: «کلِ بلوک از donor»
                            # فقط برای باندِ تیرهٔ «یکدست» (std کم —
                            # PARAGRAPHهایِ img4 روی حصار). روی زمینهٔ
                            # بافت‌مند (برف‌نوی/نقش‌ونگارِ 412e9e با
                            # std≈۶۷/۵۸) کلِ بلوک = پرِ تختِ LaMa →
                            # فقط نوارهایِ خط از donor می‌آیند.
                            _stdb = float(np.std(_bgo[_outb]))
                            if _medb < 140.0 and _stdb <= 36.0:
                                # v1.14.209 — قانونِ دو-عکسیِ سازنده: «کلِ
                                # حباب انتقال میدی حباب خراب میکنی» → حتی
                                # رویِ باندِ تیرهٔ یکدست فقط نوارهایِ خط از
                                # donor میآیند (بالا: out |= strips/failed)؛
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
                            # v1.14.135 — «پنلِ متنیِ روشن» (همتایِ ماسکِ
                            # توپرِ بلوک — فقط اندروید، MANGA_TEXTPANEL):
                            # اگر بینِ نوارها هنوز جوهرِ حروفِ جامانده
                            # (OCRِ هرزِ آن روز) دیده شود، کلِ بلوک از
                            # عکسِ پاکشده میآید — وگرنه متنِ نیمهپاک +
                            # لکه در خروجی میماند. اگر donor آنجا پاک
                            # نشده باشد، پیکسلِ donor = اورجینال (بیضرر).
                            # v1.14.241 — هماهنگ با گیتِ ماسک: فقطِ اندروید
                            elif _android_gate("MANGA_TEXTPANEL"):
                                try:
                                    _ex135 = cv2.dilate(
                                        ((_strips > 0) | (_failed > 0))
                                        .astype(np.uint8),
                                        np.ones((9, 9), np.uint8))
                                    # v1.14.238 — med_hِ ناحیه (فونتِ
                                    # درشتِ img6: بلندیِ خط ۶۹..۷۹)
                                    _mh35 = 0.0
                                    try:
                                        _pl35 = []
                                        for _p35 in (getattr(
                                                _rg, "ocr_polys", None)
                                                or []):
                                            try:
                                                _pp35 = np.asarray(
                                                    _p35,
                                                    dtype=np.float32
                                                ).reshape(-1, 2)
                                                if _pp35.shape[0] >= 3:
                                                    _pl35.append(_pp35)
                                            except Exception:
                                                continue
                                        _ln35 = MangaTranslator \
                                            ._group_polys_to_lines(_pl35)
                                        if _ln35:
                                            _mh35 = float(np.median(
                                                [b[3] - b[1]
                                                 for b in _ln35]))
                                    except Exception:
                                        _mh35 = 0.0
                                    _ink_35 = \
                                        MangaTranslator._panel_leftover_ink(
                                            image,
                                            (_bx0, _by0,
                                             _bx1 - _bx0, _by1 - _by0),
                                            _ex135, med_h=_mh35)
                                    if _ink_35 is not None:
                                        # فقط گلیفهای جامانده از donor —
                                        # نه کلِ بلوک (LaMaِ بلوکِ کامل
                                        # رویِ زمینهٔ عکسی توهم/نویز)
                                        _im35 = _ink_35 > 0
                                        out[_im35] = True
                                        _sweep[_im35] = True
                                        if self.debug:
                                            try:
                                                print(
                                                    f"  [*]پنلِ متنی → "
                                                    f"گلیفهای جامانده از "
                                                    f"donor ("
                                                    f"{int(cv2.countNonZero(_ink_35))}"
                                                    f"px @({_bx0},{_by0})")
                                            except Exception:
                                                pass
                                except Exception:
                                    pass
                except Exception:
                    pass
                # v1.14.104 — «بالنِ سیستم»: اینتریورِ باکسِ سیستم (که در
                # پاکسازی «یکجا» پاک شد) در کامپوز هم «یکجا» از عکسِ
                # پاک‌شده منتقل می‌شود — وگرنه شبح/لکهٔ بینِ خط‌ها از
                # عکسِ اصلی برمی‌گردد. قابِ سیستم بیرونِ اینتریور است و
                # طبقِ قاعدهٔ همیشگی از عکسِ اصلی می‌ماند.
                try:
                    if getattr(_rg, "sys_split", False):
                        _cov104 = getattr(_rg, "cover_rect", None)
                        if _cov104 is not None:
                            _sys_done104 = getattr(
                                self, "_compose_sys_done", None)
                            if _sys_done104 is None:
                                _sys_done104 = set()
                                self._compose_sys_done = _sys_done104
                            _key104 = tuple(
                                int(v) for v in _cov104[:4])
                            if _key104 not in _sys_done104:
                                _sys_done104.add(_key104)
                                _seeds104 = []
                                for _rgs2 in _regions:
                                    if not getattr(_rgs2, "sys_split",
                                                   False):
                                        continue
                                    _cv2b = getattr(_rgs2, "cover_rect",
                                                    None)
                                    if _cv2b is None or tuple(
                                            int(v) for v in _cv2b[:4]) \
                                            != _key104:
                                        continue
                                    try:
                                        _qx, _qy, _qw, _qh = [
                                            int(v) for v in _rgs2.rect]
                                    except Exception:
                                        continue
                                    _seeds104.append((_qx, _qy,
                                                      _qx + _qw,
                                                      _qy + _qh))
                                if len(_seeds104) >= 2:
                                    _intr104 = \
                                        MangaTranslator._system_box_interior(
                                            image, _key104, _seeds104)
                                    if _intr104 is not None:
                                        # v1.14.209 — قانونِ دو-عکسیِ سازنده:
                                        # اینتریورِ کاملِ باکسِ سیستم هم دیگر
                                        # یکجا منتقل نمیشود — فقط نوارهایِ
                                        # خط (sys_split). بینِ خطها = اورجینال؛
                                        # خرابیِ عکسِ اول به عکسِ دوم نمیرسد.
                                        if self.debug:
                                            try:
                                                print(f"  [*]بالنِ سیستم → "
                                                      f"فقطِ نوارِ خط "
                                                      f"(اینتریورِ "
                                                      f"{int(_intr104.sum())}px "
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
                    # v1.14.76 — ناحیهٔ بی‌نوار (متنِ آزاد/بنر): ماسکِ خام
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
            # v1.14.64 — بنرهایِ تبلیغ: کلِ بنر (نه نوارِ خط‌ها) از عکسِ
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
            # v1.14.73d — نجاتِ نوارِ جوهرِ پوشش‌داده‌نشده در کامپوز:
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
            # v1.14.212 — روکشِ حاشیه‌نویسی (قاب/شستشویِ سبزِ up0822) هم
            # در ماسکِ کامپوز میآید تا با نوارهایِ پاک‌شده به عکسِ دوم
            # منتقل شود — وگرنه قابِ سبز در خروجیِ نهایی زنده میماند
            # («هرنگی لگه بشه قبول نمیکنم»).
            try:
                _anW212 = getattr(self, "_page_annotation_overlay", None)
                if _anW212 is not None and _anW212.shape == out.shape \
                        and bool((_anW212 > 0).any()):
                    out |= (_anW212 > 0)
                    _sweep[(_anW212 > 0)] = 255
            except Exception:
                pass
            return (out.astype(np.uint8)) * 255
        except Exception:
            return mask

    def _strip_ghost_polish(self, image: np.ndarray, cleaned: np.ndarray,
                            mask: np.ndarray) -> Tuple[np.ndarray, int]:
        """v1.14.213 — پولیشِ شبحِ نوارهایِ کامپوز.

        گزارشِ سازنده: «فقط مشکل لگه سیاه سفید داره یا لگه متن قبلی
        دیده میشه … نه لگه سیاهی نه لگه سفیدی یا هرنگی لگه بشه قبول
        نمیکنم». ریشه (img6 — حبابِ دوگانهٔ بالا-وسط): لبهٔ ماسکِ LaMa
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
            # v1.14.213b — فقطِ شبحِ «محو» (کنتراستِ ۲۲..۶۰): خطِ تیرهٔ
            # واقعی (هنر/دست/مو — کنتراستِ ۸۰+) هرگز پر نمیشود (img4:
            # ضربههایِ دست رویِ میز داخلِ نوار، پاک نشود).
            _d213 = (bg - g.astype(np.int16))
            _b213 = (g.astype(np.int16) - bg)
            dark = (_d213 > 22) & (_d213 < 60)
            bright = (_b213 > 22) & (_b213 < 60)
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
            # v1.14.213c — «باندِ لبهٔ نوار»: شبحِ LaMa پدِّ تراسِ لبهٔ
            # ماسک است و همیشه به لبهٔ نوارِ کامپوز چسبیده؛ ضربهٔ هنر
            # (دست/مو داخلِ نوار — img4) وسطِ نوار است و رد میشود.
            _core213 = cv2.erode(m.astype(np.uint8),
                                 np.ones((13, 13), np.uint8)) > 0
            _edge213 = m & ~_core213
            # نقشههایِ حفاظت: دیوار/قاب/روکش هرگز پر نمیشوند
            _prot213 = None
            try:
                for _pmN in (getattr(self, "_page_protect", None),
                             getattr(self, "_page_wall_band", None),
                             getattr(self, "_page_colored_protect", None)):
                    if _pmN is not None and _pmN.shape == (h, w):
                        _prot213 = (_pmN > 0) if _prot213 is None \
                            else (_prot213 | (_pmN > 0))
            except Exception:
                _prot213 = None
            n, lab, st, _ = cv2.connectedComponentsWithStats(thin, 8)
            fills = np.zeros((h, w), bool)
            for i in range(1, n):
                a = int(st[i, cv2.CC_STAT_AREA])
                cw = int(st[i, cv2.CC_STAT_WIDTH])
                ch = int(st[i, cv2.CC_STAT_HEIGHT])
                if a < 6 or a > 1600 or max(cw, ch) > 220:
                    continue
                comp = (lab == i)
                if _prot213 is not None and bool((comp & _prot213).any()):
                    continue  # دیوار/قاب → رد
                if not (comp & oink_near).any():
                    continue  # دور از متنِ اصلی → هنر است نه شبح
                _eb213 = cv2.dilate(comp.astype(np.uint8),
                                    np.ones((9, 9), np.uint8)) > 0
                if not bool((_eb213 & _edge213).any()):
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
            if _prot213 is not None:
                tgt &= ~_prot213
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
        """v1.14.70 — «پاکسازیِ کثیف»: لکهٔ خاکستری/سبزِ LaMa داخلِ حبابِ
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
            # v1.14.73 — کامپوز با دیلیتِ ۹ انجام می‌شود → هر چیزی تا ۹px
            # اطرافِ نوار از «عکسِ پاک‌شده» (donor) می‌آید. حلقه باید از
            # «اورجینال» باشد وگرنه هالهٔ donor رنگِ فلتن را می‌شکند
            # (نمونه: پرِ نوارهایِ حبابِ زرد با بژِ خاکستری).
            _m9 = cv2.dilate(m, np.ones((9, 9), np.uint8)) > 0
            _k25 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
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
                ring = cv2.dilate(subm.astype(np.uint8), _k25) > 0
                ring &= ~subm
                ring &= ~_m9[y0:y1, x0:x1]
                # v1.14.73 — حلقه فقط از پیکسل‌هایِ «اورجینال» ساخته شود:
                # نوارهایِ همسایه (موتیلینگِ LaMa/TELEA) آمارِ حلقه را
                # آلوده می‌کنند و rstd بی‌دلیل بالا می‌رود. اگر بعد از
                # حذف، حلقه خیلی کوچک شد، همان حلقهٔ قبلی (با نوارها).
                try:
                    _ring_o = ring & (m[y0:y1, x0:x1] == 0)
                    if int(np.count_nonzero(_ring_o)) >= 40:
                        ring = _ring_o
                except Exception:
                    pass
                # v1.14.73 — دیوار از حلقه بیرون بماند تا سفیدیِ حباب را
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
                # v1.14.73 — گیت‌های فلتنِ «کلِ نوار»:
                # v1.14.75e — آمارِ حلقه از «عکسِ اورجینال» گرفته شود نه
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
                # v1.14.82 — گیتِ بافتِ خروجی: اگر «نتیجهٔ» کامپوز روی این
                # مؤلفه بافت‌مند است (هنرِ حفظ‌شده — مثلِ کارتِ img2 با
                # قابِ سفید و خطوطِ داخل)، پولیش (فلت/لکه‌گیری) ممنوع —
                # وگرنه فازِ «لکه» هر پیکسلِ روشن‌تر از زمینه (قابِ سفید،
                # هایلایتِ هنر) را با رنگِ حلقه پر می‌کند («کل حباب با
                # رنگ پر شد — لاما روش استفاده نشد»). سنجه روی خروجی
                # سنجیده می‌شود نه اورجینال (اورجینال خودِ متن را دارد).
                # کالیبراسیون img2: هنر std=66/lap=9.3 ؛ پنلِ تخت std≤4.
                # v1.14.206o — این گیت فقط وقتی معنا دارد که حلقه هم
                # «غیریکنواخت» است (نوارِ وسطِ هنر). اگر حلقهٔ اورجینال
                # تخت باشد (حبابِ سفید/رنگیِ تخت)، بافتِ خروجی = خودِ
                # لکهٔ پرِ LaMa است (لکهٔ سبزِ قابِ رنگی در up0822 —
                # پرِ LaMa رنگِ قاب را داخلِ متن کشیده) و باید فلت شود؛
                # پس فقط ترکیبِ «بافت‌مند + حلقهٔ بافت‌مند» رد میشود.
                if rstd is not None and rstd > 12.0:
                    try:
                        _vT82 = rg[subm].astype(np.float32)
                        if _vT82.size >= 200:
                            _lapT82 = np.abs(cv2.Laplacian(rg, cv2.CV_32F))
                            if (float(np.std(_vT82)) > 12.0
                                    or float(np.mean(_lapT82[subm])) > 2.5):
                                # v1.14.226d — استثنایِ بلوکِ اجباری-LaMa:
                                # «بافتِ» نوارِ بلوکهایِ اجباری، خودِ شبحِ
                                # حروفِ LaMa است نه هنر (SFXِ 4e2e77:
                                # CHANGES TO… ذوب‌شده ولی خوانا — std=۳۴)
                                # → رد نکن؛ بگذار به گیتها/بازپرِ گرادیانی
                                # برسد.
                                _fhit26d = False
                                try:
                                    for _fb26d in (getattr(
                                            self, "_lama_force_rect_boxes",
                                            None) or []):
                                        if not (x > _fb26d[2]
                                                or x + w < _fb26d[0]
                                                or y > _fb26d[3]
                                                or y + h < _fb26d[1]):
                                            _fhit26d = True
                                            break
                                except Exception:
                                    _fhit26d = False
                                if not _fhit26d:
                                    if _pdbg:
                                        print(f"  [dbg-polish] SKIP-textured "
                                              f"comp x={x} y={y} {w}x{h} "
                                              f"std={float(np.std(_vT82)):.1f} "
                                              f"lap={float(np.mean(_lapT82[subm])):.2f}",
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
                        _vT82 = rg[subm].astype(np.float32)
                        if _vT82.size >= 200:
                            _lapT82 = np.abs(cv2.Laplacian(rg, cv2.CV_32F))
                            if (float(np.std(_vT82)) > 12.0
                                    or float(np.mean(_lapT82[subm])) > 2.5):
                                continue
                    except Exception:
                        pass
                #  الف) حلقهٔ اورجینال یکنواخت — حبابِ سفید/رنگیِ تخت که
                #     حلقه‌اش داخلِ حباب است.
                #     v1.14.75 — یکنواختیِ «اکثریتِ» حلقه (≥۷۵٪ در ±۱۲ از
                #     میانهٔ حلقه) کافی است؛ رینگِ حبابِ سفیدِ بزرگِ 01.jpg
                #     لبهٔ هنرِ استخر را هم می‌گیرد و rstd کل را بالا می‌برد
                #     — اقلیتِ هنر نباید فلتِ نوار را بلاک کند وگرنه شبحِ
                #     محوِ متن زنده می‌ماند.
                #  ب) خودِ نوار «اکثریت‌یکنواخت» (≥۸۰٪ نزدیکِ میانهٔ خودش)
                #     — برای بلوک‌هایِ بزرگ (ماسکِ بلوک/حبابِ زرد) که حلقه‌شان
                #     هنر است و گیتِ الف نمی‌گیرد؛ اقلیتِ باقی‌مانده =
                #     جوهرِ شبحِ متن است.
                # v1.14.104 — گیتِ رنگی (درسِ v1.14.38): «یکنواختی» فقط در
                # خاکستری دیده نمی‌شود. کارتِ قرمزِ 890fb1: خاکستریِ حلقه
                # یکنواختِ ~۱۲ (rstd=4!) ولی کانالِ R گرادیانِ ۵۰→۱۳ دارد
                # — پولیشِ فلتِ خاکستری‌فکر کلِ بلوک را با «میانهٔ حلقه»
                # یک‌رنگ می‌کند = لگهٔ قرمزِ مستطیلی. سنجه = بیشینهٔ
                # stdِ کانال‌هایِ BGR رویِ حلقهٔ اورجینال + اکثریتِ هر کانال.
                _cstd104 = None
                try:
                    _roc104 = image[y0:y1, x0:x1][ring].astype(np.float32)
                    if _roc104.shape[0] >= 40:
                        _cstd104 = float(_roc104.std(axis=0).max())
                except Exception:
                    _cstd104 = None
                _cmaj104 = None
                try:
                    _roc104b = image[y0:y1, x0:x1][ring].astype(np.float32)
                    if _roc104b.shape[0] >= 40:
                        _cmaj104 = min(
                            float((np.abs(_roc104b[:, _c] -
                                          np.median(_roc104b[:, _c]))
                                   <= 12.0).mean())
                            for _c in range(3))
                except Exception:
                    _cmaj104 = None
                _can_flat = False
                _gate82 = ""
                if rstd is not None and rstd <= 10.0 and (
                        _cstd104 is None or _cstd104 <= 10.0):
                    _can_flat = True
                    _gate82 = "A:rstd<=10"
                elif rstd is not None and rstd <= 60.0:
                    # v1.14.75 — اکثریتِ یکنواختِ حلقه (حباب با لبهٔ هنر):
                    try:
                        _rvv = rg[ring]
                        _rmv = float(np.median(_rvv))
                        if (float((np.abs(_rvv.astype(np.float32) - _rmv)
                                  <= 12.0).mean()) >= 0.75
                                and (_cmaj104 is None
                                     or _cmaj104 >= 0.75)):
                            _can_flat = True
                            _gate82 = "B:ring-majority"
                    except Exception:
                        pass
                if not _can_flat and _pdbg:
                    print(f"  [dbg-polish] comp x={x} y={y} {w}x{h} "
                          f"rstd={rstd if rstd is None else round(rstd,2)} "
                          f"ring_n={_ring_n}")
                if not _can_flat:
                    # v1.14.73b — گیتِ «اکثریت‌یکنواخت» فقط برای نوارهایِ
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
                                # v1.14.104 — گیتِ C هم رنگی: کامپوننتِ
                                # گرادیانِ رنگی (کارتِ 890fb1 در خاکستری
                                # «اکثریت‌یکنواخت» است!) فلت نشود.
                                _gdC104 = None
                                try:
                                    _subC104 = sub[subm].astype(np.float32)
                                    if _subC104.shape[0] >= 40:
                                        _gdC104 = min(
                                            float((np.abs(
                                                _subC104[:, _c]
                                                - np.median(
                                                    _subC104[:, _c]))
                                                <= 10.0).mean())
                                            for _c in range(3))
                                except Exception:
                                    _gdC104 = None
                                if (float((np.abs(
                                        _gd.astype(np.float32) - _gmode)
                                        <= 10.0).mean()) >= 0.80
                                        and (_gdC104 is None
                                             or _gdC104 >= 0.80)):
                                    _can_flat = True
                                    _gate82 = "C:comp-majority"
                        except Exception:
                            pass
                if _can_flat and _pdbg:
                    print(f"  [dbg-polish] FLATTEN comp x={x} y={y} "
                          f"{w}x{h} gate={_gate82} rstd="
                          f"{rstd if rstd is None else round(rstd, 2)} "
                          f"ring_n={_ring_n}", flush=True)
                if _can_flat:
                    # v1.14.73 — دامنهٔ فلتن = خودِ نوار + هالهٔ دورِ آن:
                    # «اثرِ فشردنِ جوهر روی کاغذ» (۴-۱۵ سطحِ زیرِ زمینه،
                    # شکلِ حروف) تا ~۱۳px بیرونِ نوار می‌ریزد (نمونهٔ
                    # حبابِ زرد: «Alright! I'll increase…» خوانا ماند) —
                    # با فلت‌کردنِ فقط ۵px زنده می‌ماند.
                    # v1.14.75 — شبحِ داخلِ نوارهایِ بزرگِ بلوکی حبابِ زرد
                    # (لکههای تیرهٔ تیره‌تر از زمینه) با ۱۳px هم اسمش نمی‌شد
                    # چون گیتِ رنگِ ±۲۶ حفره‌ها را نمی‌گرفت — دیلیتِ ۱۷ +
                    # گیتِ رنگِ آماری: پیکسلی که «آوتلایرِ» توزیعِ سایهٔ
                    # نوار است (bis basal) هم داخلِ فلتن.
                    _flat_dom = cv2.dilate(
                        subm.astype(np.uint8),
                        cv2.getStructuringElement(
                            cv2.MORPH_ELLIPSE, (17, 17))) > 0
                    # v1.14.73d — گیتِ رنگ: فقط پیکسل‌هایِ «هم‌رنگِ نوار»
                    # فلت می‌شوند — دیوارِ ضخیم/خشنِ بیرونِ protect (خطِ
                    # دست‌کشیدهٔ کیمتسو) و هنرِ چسبیده به نوار محفوظ می‌مانند.
                    try:
                        _fm73 = float(np.median(rg[subm]))
                        # v1.14.226b — استثنایِ هستهٔ نوار: بقایایِ روشنِ
                        # حروف (خاکستریِ ۲۵۰ در برابرِ میانهٔ ۱۶۰) از گیتِ
                        # رنگ بیرون میافتادند و همان شبحهایِ سفید زنده
                        # میماندند (پنجرهٔ 4e2e77) — گیت فقط برایِ هاله.
                        _flat_dom &= ((np.abs(
                            rg.astype(np.float32) - _fm73) <= 26.0) | subm)
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
                        # v1.14.75 — رنگِ فلتن از «حلقهٔ اورجینال» گرفته می‌شود
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
                        # v1.14.226 — فلتنِ گرادیان‌آگاه: پنجرهٔ سیستمِ
                        # 4e2e77 — هر خطِ متن رویِ گرادیانِ آبی، حلقهٔ
                        # «محلیِ» خودش را یکنواخت دارد (rstd≤۱۰) و فلت با
                        # میانهٔ خودش پاک میشد → پلههایِ آبیِ ناهمسانِ
                        # روی-هم (اسکرینشاتِ سازنده). سنجشِ شیب روی
                        # «همهٔ پیکسلهایِ زمینهٔ اورجینالِ پنجرهٔ محلی»
                        # (بیرونِ ماسکِ نوارها — نه فقط حلقهٔ ۲۵px که
                        # همسایههاشان آن را میبلعند): شیبِ >۶ در هر
                        # کانال بین ربعِ اول و آخرِ ردیفهای زمینه =
                        # گرادیان → فلتن بهجایِ رنگِ تخت، «رنگِ ردیفی»
                        # میان‌یابی‌شده میگیرد — گرادیان زنده میماند،
                        # لکههایِ LaMa هم پاک میشوند.
                        try:
                            _prof26 = None
                            try:
                                # v1.14.226b — پنجرهٔ پروفایلِ بازتر
                                # (±۶۰): در بلوکهایِ چندخطی، ماسکهایِ
                                # خطوط، پنجرهٔ ۱۸px را میبلعند و مدل از
                                # ۲-۳ ردیفِ باقیمانده ساخته میشد (رنگِ
                                # غلط → دوختِ عمودی).
                                _py026 = max(0, y - 60)
                                _py126 = min(m.shape[0], y + h + 60)
                                _bgw26 = (m[_py026:_py126, x0:x1] == 0)
                                if int(_bgw26.sum()) >= 60:
                                    _subO26 = image[_py026:_py126, x0:x1]
                                    _rows26 = []
                                    _cols26 = []
                                    _free26 = max(
                                        6, int(0.45 * _bgw26.shape[1]))
                                    for _rr26 in range(
                                            _bgw26.shape[0]):
                                        _selr26 = _bgw26[_rr26]
                                        if int(_selr26.sum()) >= _free26:
                                            _rows26.append(
                                                _rr26 + _py026 - y0)
                                            _cols26.append(np.median(
                                                _subO26[_rr26][_selr26],
                                                axis=0))
                                    if len(_rows26) >= 2 \
                                            and (_rows26[-1] - _rows26[0]) \
                                            >= 24:
                                        _rarr26 = np.asarray(
                                            _rows26, np.float32)
                                        _carr26 = np.asarray(
                                            _cols26, np.float32)
                                        _q26 = max(
                                            1, len(_rows26) // 4)
                                        _mt26 = np.median(
                                            _carr26[:_q26], axis=0)
                                        _mb26 = np.median(
                                            _carr26[-_q26:], axis=0)
                                        _dr26 = float(np.abs(
                                            _mt26 - _mb26).max())
                                        if _pdbg:
                                            try:
                                                print(
                                                    f"  [dbg-grad26] comp "
                                                    f"x={x} y={y} {w}x{h} "
                                                    f"drift={_dr26:.1f} "
                                                    f"nrows={len(_rows26)}",
                                                    flush=True)
                                            except Exception:
                                                pass
                                        if _dr26 > 6.0:
                                            _prof26 = (
                                                _rarr26, _carr26)
                            except Exception:
                                _prof26 = None
                            if _prof26 is not None:
                                _rarr26, _carr26 = _prof26
                                _h26 = sub.shape[0]
                                _allr26 = np.arange(_h26, dtype=np.float32)
                                _rowc26 = np.zeros((_h26, 3), np.float32)
                                for _ch26 in range(3):
                                    _rowc26[:, _ch26] = np.interp(
                                        _allr26, _rarr26, _carr26[:, _ch26])
                                _sF26 = sub.copy()
                                _rowg26 = (0.299 * _rowc26[:, 2]
                                           + 0.587 * _rowc26[:, 1]
                                           + 0.114 * _rowc26[:, 0])
                                for _rr26 in range(_h26):
                                    _rd26 = _flat_dom[_rr26]
                                    if not _rd26.any():
                                        continue
                                    _gate26 = np.abs(
                                        rg[_rr26].astype(np.float32)
                                        - float(_rowg26[_rr26])) <= 26.0
                                    # v1.14.226b — گیتِ رنگ فقط رویِ هاله:
                                    # هستهٔ نوار (= خودِ متن) همیشه بازپر
                                    # میشود — بقایایِ سفیدِ حروف از مدل
                                    # >۲۶ فاصله داشتند و گیت، همان شبحها
                                    # را زنده نگه میداشت (خطوطِ سفیدِ
                                    # پایینِ پنجرهٔ 4e2e77).
                                    _gate26 |= subm[_rr26]
                                    _rd26 = _rd26 & _gate26
                                    if not _rd26.any():
                                        continue
                                    _sF26[_rr26][_rd26] = np.clip(
                                        np.rint(_rowc26[_rr26]), 0,
                                        255).astype(np.uint8)
                                sub[:] = _sF26
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
                # v1.14.226c — بلوکِ بزرگِ «فلت رویِ گرادیان»: بلوکهایِ
                # اجباری-LaMaیِ پنجرهٔ سیستمِ 4e2e77 ([TRAITS…]/[CLASS…])
                # — گیتهایِ فلتن (A/B/C) رینگِ پهنِ پنل+هنر را رد
                # میکنند (rstd>10) و پرِ تختِ روشنِ LaMa [77,190,251]
                # رویِ گرادیانِ آبی میماند = قابِ مستطیلیِ روشن
                # (اسکرینشاتِ سازنده). مدلِ «جداکردنی» = ردیف(y)+ستون(x):
                # گرادیانِ عمودی و افقی هر دو بازسازی میشوند؛ خشنیِ
                # پروفایل = هنر/بافت → رد. انحرافِ پر از مدل ≥۳.۵ =
                # پرِ غلط → بازپرِ ردیفی-ستونی.
                if not _can_flat and a >= 4000 and (w >= 60 or h >= 60):
                    try:
                        _py026c = max(0, y - 60)
                        _py126c = min(m.shape[0], y + h + 60)
                        _bgw26c = (m[_py026c:_py126c, x0:x1] == 0)
                        _subO26c = image[_py026c:_py126c, x0:x1]
                        _off26c = y0 - _py026c
                        _sep26c = None
                        if int(_bgw26c.sum()) >= 200:
                            # پروفایلِ ردیفی
                            _rows26c = []
                            _cols26c = []
                            _free26c = max(
                                6, int(0.45 * _bgw26c.shape[1]))
                            for _rr26c in range(_bgw26c.shape[0]):
                                _selr26c = _bgw26c[_rr26c]
                                if int(_selr26c.sum()) >= _free26c:
                                    _rows26c.append(_rr26c - _off26c)
                                    _cols26c.append(np.median(
                                        _subO26c[_rr26c][_selr26c], axis=0))
                            # پروفایلِ ستونی
                            _colsx26c = []
                            _colsv26c = []
                            for _cc26c in range(_bgw26c.shape[1]):
                                _selc26c = _bgw26c[:, _cc26c]
                                if int(_selc26c.sum()) >= 6:
                                    _colsx26c.append(_cc26c)
                                    _colsv26c.append(np.median(
                                        _subO26c[:, _cc26c][_selc26c],
                                        axis=0))
                            if len(_rows26c) >= 4 and len(_colsx26c) >= 4 \
                                    and (_rows26c[-1] - _rows26c[0]) >= 24:
                                _rarr26c = np.asarray(_rows26c, np.float32)
                                _carr26c = np.asarray(_cols26c, np.float32)
                                _xarr26c = np.asarray(
                                    _colsx26c, np.float32)
                                _varr26c = np.asarray(
                                    _colsv26c, np.float32)
                                _q26c = max(1, len(_rows26c) // 4)
                                _mt26c = np.median(
                                    _carr26c[:_q26c], axis=0)
                                _mb26c = np.median(
                                    _carr26c[-_q26c:], axis=0)
                                _dr26c = float(np.abs(
                                    _mt26c - _mb26c).max())
                                _g26c = float(np.mean(_carr26c))
                                if _dr26c > 6.0:
                                    # هموارسازی (۹تایی) + گیتِ خشنی
                                    try:
                                        _k26c = np.ones(
                                            9, np.float32) / 9.0
                                        _cs26c = np.zeros_like(_carr26c)
                                        _vs26c = np.zeros_like(_varr26c)
                                        for _ch26c in range(3):
                                            _cs26c[:, _ch26c] = np.convolve(
                                                np.pad(_carr26c[:, _ch26c],
                                                       (4, 4),
                                                       mode='edge'),
                                                _k26c, mode='valid')
                                            _vs26c[:, _ch26c] = np.convolve(
                                                np.pad(_varr26c[:, _ch26c],
                                                       (4, 4),
                                                       mode='edge'),
                                                _k26c, mode='valid')
                                        _d226c = float(np.abs(np.diff(
                                            _cs26c, n=2,
                                            axis=0)).mean())
                                        _d2x26c = float(np.abs(np.diff(
                                            _vs26c, n=2,
                                            axis=0)).mean())
                                        if _d226c <= 1.2 \
                                                and _d2x26c <= 1.2:
                                            _sep26c = (_rarr26c, _cs26c,
                                                       _xarr26c, _vs26c,
                                                       _g26c)
                                    except Exception:
                                        _sep26c = None
                        if _sep26c is not None:
                            _rarr26c, _cs26c, _xarr26c, _vs26c, _g26c = \
                                _sep26c
                            _h26c = sub.shape[0]
                            _w26c = sub.shape[1]
                            # مدلِ ردیفی (گرادیانِ عمودی) — پروفایلِ ستونی
                            # کنار گذاشته شد: ستونهایِ قابِ سفیدِ پنل،
                            # میانگینِ ستون را می‌کشند و رنگِ مدل را در
                            # کلِ ستون غلط میکنند (لکهٔ زردِ بالای پنل)
                            _rowc26c = np.zeros((_h26c, 3), np.float32)
                            for _ch26c in range(3):
                                _rowc26c[:, _ch26c] = np.interp(
                                    np.arange(_h26c, dtype=np.float32),
                                    _rarr26c, _cs26c[:, _ch26c])
                            _modelc26c = np.repeat(
                                _rowc26c[:, None, :], _w26c, axis=1)
                            _mg26c = (0.299 * _modelc26c[..., 2]
                                      + 0.587 * _modelc26c[..., 1]
                                      + 0.114 * _modelc26c[..., 0])
                            # انحرافِ پرِ فعلی از مدل (فقط روی نوار)
                            _fillrows26 = []
                            _modelrows26 = []
                            for _rr26c in range(_h26c):
                                _sr26c = subm[_rr26c]
                                if int(_sr26c.sum()) >= 6:
                                    _fillrows26.append(float(np.median(
                                        rg[_rr26c][_sr26c])))
                                    _modelrows26.append(float(np.median(
                                        _mg26c[_rr26c][_sr26c])))
                            _dev26c = (float(np.mean(np.abs(
                                np.asarray(_fillrows26)
                                - np.asarray(_modelrows26))))
                                if len(_fillrows26) >= 4 else 99.0)
                            if _pdbg:
                                try:
                                    print(f"  [dbg-grad26c] x={x} y={y} "
                                          f"{w}x{h} dev={_dev26c:.1f}",
                                          flush=True)
                                except Exception:
                                    pass
                            if _dev26c >= 3.5:
                                _dom26c = cv2.dilate(
                                    subm.astype(np.uint8),
                                    cv2.getStructuringElement(
                                        cv2.MORPH_ELLIPSE, (17, 17))) > 0
                                try:
                                    for _pm26c in (
                                            getattr(self, "_page_protect",
                                                    None),
                                            getattr(self, "_page_wall_band",
                                                    None)):
                                        if _pm26c is not None \
                                                and _pm26c.shape == \
                                                out.shape[:2]:
                                            _dom26c &= (
                                                _pm26c[y0:y1, x0:x1] == 0)
                                except Exception:
                                    pass
                                _sF26c = sub.copy()
                                # بدونِ گیتِ رنگ: خودِ پرِ غلطِ LaMa در
                                # ردیفهایِ پایین از مدل >۲۶ فاصله داشت و
                                # گیت، همان پرِ غلط را زنده نگه میداشت =
                                # نوارِ ترکیبی. دامنه = نوار+هاله منهایِ
                                # نقشههایِ حفاظت — کافی است.
                                _rd26c = _dom26c
                                if int(_rd26c.sum()) >= 20:
                                    _sF26c[_rd26c] = np.clip(np.rint(
                                        _modelc26c[_rd26c]), 0,
                                        255).astype(np.uint8)
                                    sub[:] = _sF26c
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
            # v1.14.74 — «فلتنِ کلِ داخلِ حباب» (v1.14.73c) حذف شد:
            # کاربر: «عکسِ دوم حبابش پاک نشه» — در خروجی فقط نوارِ متن
            # مجاز به تغییر است. فلتنِ کلِ اینتریور حتی با «گیتِ رنگ»،
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
        """v1.14.96 — بازپرِ بافت برای زمینه‌هایِ نویز/نقش‌ونگار.

        LaMa روی برف‌نوی/خال‌خال (EXECِ 412e9e، پلاکِ GREEN MOON) پرِ
        «تختِ بی‌بافت» می‌دهد — نویزِ ریز میانگین می‌شود و مستطیلِ صاف
        می‌ماند. برای هر مؤلفهٔ نوارمانندِ ماسک که حلقه‌اش بافت‌مند است
        (std حلقه > ۳۶):
          low-freq  = میان‌یابیِ قائمِ ستونی بینِ ردیف‌هایِ تمیزِ
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
            _dbg96 = bool(os.environ.get("MANGA_TR_DBG"))
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
                # v1.14.96f — فقط پیکسل‌هایِ «واقعاً پرشده» (پرِ LaMa)
                # بازپر می‌شوند؛ جایی که donor = اصلِ عکس است (ماسکِ
                # تنگِ پالی‌به‌پالی) بافتِ اورجینال دست‌نخورده می‌ماند —
                # نویزِ مصنوعی هرگز جایِ بافتِ واقعی را نمی‌گیرد.
                _chg96 = (np.abs(crop_d.astype(np.int16)
                                 - original[y0:y1, x0:x1].astype(np.int16))
                          .max(axis=2) > 6)
                _chg96 = cv2.dilate(_chg96.astype(np.uint8),
                                    np.ones((5, 5), np.uint8)) > 0
                _tgt96 = comp & _chg96
                if int(np.count_nonzero(_tgt96)) < 300:
                    continue
                if int(np.count_nonzero(_tgt96)) < \
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
                # v1.14.96b — مرجعِ هموارشده در محورِ x: میانگینِ ۵ ردیفِ
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
                        # v1.14.96g — میانهٔ跨-ردیف (مقاوم به خالِ بافت)
                        ref = np.nanmedian(vals, axis=0)
                    bad = ~np.isfinite(ref).all(axis=-1)
                    if bool(bad.all()):
                        return None
                    if bad.any():
                        xs_ok = np.nonzero(~bad)[0]
                        for cc in np.nonzero(bad)[0]:
                            j = xs_ok[np.argmin(np.abs(xs_ok - cc))]
                            ref[cc] = ref[j]
                    # v1.14.96c — GaussianBlur رویِ (W,3) کانال‌هایِ رنگ را
                    # با هم قاطی می‌کند (خاکستری!) → شکلِ (1,W,3) لازم است
                    # v1.14.96g — میانهٔ پهنِ跨-ستون (۴۱): نوارِ تیره/روشنِ
                    # قاب و شیارها (۱۰–۲۵px) را حذف می‌کند
                    ref96 = np.clip(ref, 0, 255).astype(
                        np.uint8).reshape(1, -1, 3)
                    ref96 = cv2.medianBlur(ref96, 41)
                    ref96 = cv2.GaussianBlur(ref96, (0, 0), 3.0)
                    return ref96.reshape(-1, 3).astype(np.float32)

                tref_full = _band_ref(tband, tvalid)
                bref_full = _band_ref(bband, bvalid)
                if tref_full is None and bref_full is None:
                    continue
                # v1.14.96g — اگر یک باندِ مرجع «آلودهٔ ساختار» است
                # (قاب/شیار از باند عبور می‌کند — پلاکِ GREEN MOON:
                # tref std=35 در برابرِ bref std=13) فقط باندِ پایدار
                # ملاک می‌شود؛ وگرنه میان‌یابیِ قائمِ کامل.
                _tstd96 = float(np.std(tref_full.mean(axis=1))) \
                    if tref_full is not None else 1e9
                _bstd96 = float(np.std(bref_full.mean(axis=1))) \
                    if bref_full is not None else 1e9
                if min(_tstd96, _bstd96) > 0 and \
                        max(_tstd96, _bstd96) > 1.8 * min(_tstd96, _bstd96) \
                        and min(_tstd96, _bstd96) <= 20.0:
                    _const96 = bref_full if _bstd96 <= _tstd96 else tref_full
                else:
                    _const96 = None
                _ref_fail = False
                for x in np.nonzero(_tgt96.any(axis=0))[0]:
                    yy = np.nonzero(_tgt96[:, x])[0]
                    if yy.size == 0:
                        continue
                    if _const96 is not None:
                        lowf[yy, x] = _const96[x][None, :]
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
                mys, mxs = np.nonzero(_tgt96)
                idx = np.clip(lab[mys, mxs] - 1, 0, cy_i.size - 1)
                hf_map = np.zeros_like(lowf)
                hf_map[mys, mxs] = \
                    resid[y0:y1, x0:x1][cy_i[idx], cx_i[idx]]
                # v1.14.96d — نمونه‌برداریِ نزدیک‌ترین‌همسایه «قفلِ ستونی»
                # می‌سازد (رگهٔ عمودی)؛ بلورِ ریز آن را می‌شکند
                hf_map = cv2.GaussianBlur(hf_map, (0, 0), 0.8)
                fill = np.clip(lowf + hf_map, 0, 255).astype(np.uint8)
                sub = crop_d.copy()
                sub[_tgt96] = fill[_tgt96]
                donor[y0:y1, x0:x1] = sub
                try:
                    _trd96 = os.environ.get("MANGA_TR_DUMP", "")
                    if _trd96:
                        cv2.imwrite(os.path.join(
                            _trd96, f"comp_{cx}_{cy}_before.png"),
                            crop_d.astype(np.uint8))
                        cv2.imwrite(os.path.join(
                            _trd96, f"comp_{cx}_{cy}_fill.png"), fill)
                        if tref_full is not None:
                            cv2.imwrite(os.path.join(
                                _trd96, f"comp_{cx}_{cy}_tref.png"),
                                np.clip(tref_full, 0, 255).astype(
                                    np.uint8).reshape(1, -1, 3))
                        if bref_full is not None:
                            cv2.imwrite(os.path.join(
                                _trd96, f"comp_{cx}_{cy}_bref.png"),
                                np.clip(bref_full, 0, 255).astype(
                                    np.uint8).reshape(1, -1, 3))
                except Exception:
                    pass
                if _dbg96:
                    try:
                        print(f"  [🔍]texture-refill comp@({cx},{cy}) "
                              f"{cw}x{ch} ring_std="
                              f"{float(g[cy:cy+ch, cx:cx+cw].std()):.0f}")
                    except Exception:
                        pass
        except Exception:
            if _dbg96:
                import traceback as _tb96
                print("  [!]texture-refill error:")
                _tb96.print_exc()

    def _fill_harmony_qc(self, donor: np.ndarray, original: np.ndarray,
                         zone: np.ndarray, verbose: bool = True) -> int:
        """v1.14.228 — QCِ هماهنگیِ رنگِ پر، برایِ «همهٔ» پرکنندهها.

        دستورِ سازنده: «معلومه از حباب داخل با بیرون حباب یکی حساب کرده
        یک رنگ کرده یا بعضی متن هارو نپاکیده» — پرِ خاکستری LaMa رویِ
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
            # v1.14.228 — فقط «مرزهایِ ساختاریِ درشت» (کادرِ حباب، قابِ
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
            _k17 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17))
            _dbg228 = os.environ.get("MANGA_HQC_DBG", "0") == "1"
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
                    # حلقهٔ «مد-خوشهای»: نامزدها = دیلاتِ قطعه (۱۷px،
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
                    cand = (cv2.dilate(_pcp, _k17) > 0) \
                        & (~_edc) & (~_chc)
                    if int(cand.sum()) < 80:
                        cand = (cv2.dilate(_pcp, _ker31) > 0) \
                            & (~_edc) & (~_chc)
                    _nr = int(cand.sum())
                    if _nr < 80:
                        if _dbg228:
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
                        if _dbg228:
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
                        if _dbg228:
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
                        if _dbg228:
                            print(f"    [228d] قطعه@({x0},{y0}) "
                                  f"سالم d={d:.0f} پ={fmed.round(0)} "
                                  f"ح={rmed.round(0)}", flush=True)
                        continue
                    # v1.14.241 — گاردِ «حلقه باید نمایندهٔ زمینهٔ زیرِ
                    # خودِ قطعه باشد»: قطعههایِ متنِ رویِ کتِ تیره که
                    # حلقه‌شان تا دیوار/زمینهٔ روشنِ پشتِ شخص میرسد
                    # (y=9536ِ 9.jpg: حلقه=دیوارِ روشن ~۲۲۵، زمینهٔ زیرِ
                    # متن=کتِ تیره ~۷۰) → QCِ حلقه پرِ «درستِ» تیرهٔ LaMa
                    # را ناهماهنگ میخواند و با رنگِ روشنِ حلقه دوبارهپر
                    # میکرد = «لکهٔ سفیدِ ابرمانند» (۲۴۸هزارpx در یک
                    # صفحه!). حالا اگر میانهٔ لومیایِ «زمینهٔ زیرِ قطعه در
                    # اورجینال» (پس‌زمینه اکثریت است — متن اقلیت) با
                    # مرکزِ خوشهٔ حلقه بیش از ۶۰ واحد فاصله داشته باشد،
                    # حلقه زمینهٔ «دیگری» را توصیف میکند → قطعه
                    # دستنخورده میماند.
                    try:
                        _ul241 = _lum_map[pch_p]
                        if _ul241.size >= 40:
                            _umed241 = float(np.median(_ul241))
                            if abs(_umed241 - _m0) > 60.0:
                                if _dbg228:
                                    print(
                                        f"    [228d] قطعه@({x0},{y0}) "
                                        f"حلقه=زمینهٔ دیگر "
                                        f"(زیرِ قطعه {_umed241:.0f} vs "
                                        f"حلقه {_m0:.0f}) → رد",
                                        flush=True)
                                continue
                    except Exception:
                        pass
                    if _dbg228:
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
                                    if _dbg228:
                                        print(f"    [228d] قطعه@({x0},{y0}) "
                                              f"حلقهشلوغ res={_res:.0f} رد",
                                              flush=True)
                                    continue  # هنر؛ دستنخورده
                                plane = _coef
                            except Exception:
                                continue
                        else:
                            if _dbg228:
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
                    print(f"  [✓228] QCِ هماهنگیِ پر: {n_fix} قطعه "
                          f"دوباره رنگ شد ({n_px}px)", flush=True)
                except Exception:
                    pass
            return n_fix
        except Exception:
            return 0

    def _compose_two_image(self, donor: np.ndarray, original: np.ndarray,

                           mask: np.ndarray,
                           verbose: bool = True,
                           refill: bool = False) -> np.ndarray:
        # v1.14.107 — نقشهٔ «چه چیزی واقعاً منتقل شد» برایِ گاردهایِ
        # پساکامپوز (وارسیِ نهایی/جارویِ بازمانده): هیچ ترمیمی بعد از
        # کامپوز حقِ نوشتن بیرونِ این مجموعه را ندارد — قراردادِ
        # دو-عکسی: «بیرونِ نوارِ متن = پیکسلِ اورجینال، همیشه». خطایِ
        # کاربر (۱۰۱۸/sexyverse): tier6ِ «پرِ سفیدِ ناب» و جارویِ
        # بازماندهٔ تیره بیرونِ نوار می‌نوشتند → خطِ حباب/نوارِ هدر/قابِ
        # پنل سفید می‌شد = «کلِ حباب پاکیده».
        self._compose_final_cmp = None
        try:
            _dd81z = os.environ.get("MANGA_DUMP_DONOR", "")
            if _dd81z:
                cv2.imwrite(_dd81z, donor)
                print(f"  [*] donor dumped -> {_dd81z}")
        except Exception:
            pass
        """v1.14.54 — ترکیبِ «دو عکس» — عینِ ایدهٔ خودِ کاربر:
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
            # v1.14.228 — QCِ هماهنگیِ رنگِ پر (همهٔ پرکنندهها، مرزآگاه)
            # درست قبلِ کامپوز: خاکستری-روی-سفید/بنفش، سفید-روی-آسمان،
            # و پرِ یکرنگِ رو-مرزِ حباب اینجا اصلاح میشوند — بیرونِ نوار
            # نمینویسد و حلقهٔ شلوغ (هنر) را دستنخورده میگذارد.
            if os.environ.get("MANGA_NO_HQC", "0") != "1":
                try:
                    self._fill_harmony_qc(donor, original, mask,
                                          verbose=verbose or self.debug)
                except Exception:
                    pass
            _cmp = cv2.dilate(mask, self._compose_kernel9()) > 0
            # v1.14.64 — دیوارِ حباب/قوس/کادرِ پنل (نقشهٔ ساختاریِ محافظت)
            # هرگز از عکسِ پاک‌شده به خروجی نمی‌رود — حتی اگر لبهٔ نوارِ متن
            # به آن چسبیده باشد. این «قوسِ ناپدیدشده» را ریشه‌کن می‌کند.
            # v1.14.96j — استثنا: گلیفِ تنهاِ جاافتاده (Wِ WICKED) که
            # نقشهٔ حفاظت آن را «قاب» خوانده — اجزایِ کوچکِ هم‌اندازهٔ
            # حرفِ محافظت‌شده که کاملاً داخلِ نوارِ متن‌اند = بقایایِ
            # حرف‌اند → مثلِ بقیهٔ نوار منتقل می‌شوند. قاب/خطِ کشیده
            # محافظت می‌ماند.
            try:
                _ppC = getattr(self, "_page_protect", None)
                if _ppC is not None and _ppC.shape == _cmp.shape:
                    _excl96 = (_ppC > 0) & _cmp
                    if int(_excl96.sum()) > 0:
                        _nE96, _lE96, _sE96, _ = \
                            cv2.connectedComponentsWithStats(
                                _excl96.astype(np.uint8), 8)
                        _keep96 = np.zeros_like(_cmp)
                        for _jE96 in range(1, _nE96):
                            _aE96 = int(_sE96[_jE96, cv2.CC_STAT_AREA])
                            _wE96 = int(_sE96[_jE96, cv2.CC_STAT_WIDTH])
                            _hE96 = int(_sE96[_jE96, cv2.CC_STAT_HEIGHT])
                            if _aE96 <= 1200 and max(_wE96, _hE96) <= 90:
                                _keep96 |= (_lE96 == _jE96)
                        _cmp &= ~((_ppC > 0) & (~_keep96))
                    else:
                        _cmp &= (_ppC == 0)
            except Exception:
                pass
            # v1.14.73 — دیوارِ ریز (حباب‌هایِ کوچک — YEP!/OH BOY که دیوارشان
            # <۶۰px است و از نقشهٔ protect بزرگ جا می‌ماند) هم هرگز از عکسِ
            # پاک‌شده منتقل نمی‌شود → حباب‌هایِ کوچک هم سالم می‌مانند.
            try:
                _wbC = getattr(self, "_page_wall_band", None)
                if _wbC is not None and _wbC.shape == _cmp.shape:
                    _cmp &= (_wbC == 0)
            except Exception:
                pass
            # v1.14.206n — قابِ رنگی (نقشهٔ جدا) هم هرگز از donor
            # منتقل نمیشود — در ماسکِ فعال پر شده و در خروجی اورجینالش
            # میماند (حبابِ سبزِ up0822)
            # v1.14.212 — استثنا: پیکسلهایِ «روکشِ حاشیه‌نویسی» خودشان
            # رنگیاند و از قابِ رنگی جدا شدهاند (حلقهٔ خنثی + هالِ
            # پالی) — آنها باید منتقل شوند تا لگهٔ رنگی در خروجی نماند.
            try:
                _pcC = getattr(self, "_page_colored_protect", None)
                if _pcC is not None and _pcC.shape == _cmp.shape:
                    _anC212 = getattr(self,
                                      "_page_annotation_overlay", None)
                    if _anC212 is not None \
                            and _anC212.shape == _cmp.shape:
                        _cmp &= ((_pcC == 0) | (_anC212 > 0))
                    else:
                        _cmp &= (_pcC == 0)
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
            # v1.14.96 — بازپرِ بافت (آزمایشی): روی زمینهٔ برف‌نوی/نقش‌ونگار
            # پرِ LaMa «تختِ بی‌بافت» است → نواری که حلقه‌اش بافت‌مند است
            # با low-freqِ میان‌یابی‌شده + نویزِ واقعی بازپر می‌شود.
            # v1.14.96h — پیش‌فرضِ «خاموش»: در تستِ A/B، نسخهٔ بدونِ
            # بازپر برنده بود (ماسکِ پالی‌باندیِ v1.14.96 خودش پرِ
            # لایما را آن‌قدر تنگ کرده که بازپرِ نویزِ مصنوعی نوار
            # می‌سازد). فقط با MANGA_TEXTURE_REFILL=1 فعال شود.
            if refill and os.environ.get("MANGA_TEXTURE_REFILL", "0") == "1":
                self._texture_refill_donor(donor, original, _cmp)
            # v1.14.105 — زباله‌روبی قبل از تخصیصِ خروجیِ تمام‌قد: رویِ
            # نوارهایِ بلندِ وبتون (۹۰۰×۱۶۰۰۰) RSSِ انباشتهٔ پایپ‌لاین به
            # مرزِ OOM می‌رسد؛ هر MB آزادشده اینجا کمکه (فقط semantics
            # reference-counting — بدونِ تغییرِ داده)
            try:
                import gc as _gc105
                _gc105.collect()
            except Exception:
                pass
            self._compose_final_cmp = _cmp.copy()
            _out = np.ascontiguousarray(
                np.where(_cmp[..., None], donor, original))
            # v1.14.212 — روکشِ حاشیه‌نویسی: نواحیِ «سفیدِ تختِ واقعی»
            # (جعبهٔ حاشیه‌نویسیِ سفید — گواهِ شکاف) با سفیدِ همان جعبه
            # تخت پر میشوند؛ سبز/شستشو/قاب کاملاً محو میشود. LaMa رویِ
            # ناحیهٔ شسته‌شده خودش شستشو را زمینه میپندارد و سبز میسازد.
            # (MANGA_212_FLAT=0 خاموش — برایِ مقایسهٔ A/B)
            try:
                _anF212 = getattr(self, "_page_annotation_fill", None)
                _anFl212 = getattr(self, "_page_annotation_flat", None)
                if os.environ.get("MANGA_212_FLAT", "1") != "0" \
                        and _anF212 is not None \
                        and _anFl212 is not None \
                        and _anF212.shape[:2] == _out.shape[:2] \
                        and _anFl212.shape == _cmp.shape:
                    _sel212 = (_anFl212 > 0) & _cmp
                    if bool(_sel212.any()):
                        _out[_sel212] = _anF212[_sel212]
            except Exception:
                pass
            # v1.14.139 — ضدِ «باندِ سفید» در کامپوز (فقط اندروید —
            # MANGA_STRIP_HARM): donorِ LaMa رویِ زمینهٔ گرادیانی/کرم
            # گاهی «روشنتر/سفیدتر» از زمینهٔ اطراف برمیگردد و کامپوزِ
            # فقط-نوار همان پیکسلهایِ سفید را میبرد (لاگِ گوشیِ
            # v1.14.138 — نوارهایِ سفیدِ #19/#20 رویِ دیوارِ کرمِ
            # 700×11362 = «لگه»).
            # v1.14.139b — همسازِ «خط‌به‌خط» (بازنویسیِ همسازِ ردیفی):
            # نوارهایِ خطِ چسبیده در بلوکِ متراکم در باندِ ردیفیِ مشترک
            # ادغام میشوند و لنگرِ قائمِ آزاد پیدا نمیکنند → حالا برای
            # هر «خطِ» هر ناحیه (همان گروه‌بندیِ خطِ نوارهایِ کامپوز)
            # هدفِ هر ردیف = میانهٔ پیکسلهایِ «آزادِ همان ردیف» (شکافِ
            # بینِ کلمات + حاشیهٔ خط) از عکسِ اورجینال گرفته میشود —
            # لنگرِ افقی، مستقل ازِ گپِ بینِ خطها؛ گرادیانِ قائم هم
            # چون هر ردیف هدفِ خودش را دارد حفظ میشود. گاردها: باندِ
            # غیرتخت (std>15) / ردیفِ بدونِ نمونهٔ آزاد / هدفِ ناهوار
            # (هنر) / دلتایِ ناچیز (<15) یا افراطی (>60) → دست نخوردن.
            # v1.14.212 — پیشفرضِ روشن رویِ PC هم (گیتِ _gate_default_on):
            # درزها/دال‌هایِ تختِ LaMa رویِ گرادیانِ آسمانِ وبتونها
            # (img4/4e2e77 — گزارشِ سازنده: «لگهٔ سیاه سفید») دیگر فقط
            # اندروید نیست؛ همسازِ ردیفیِ خط، نوار را با زمینهٔ اورجینالِ
            # همان ردیف تراز میکند (گاردها: std/هدفِ ناهوار/دلتا ۱۵-۶۰).
            if _gate_default_on("MANGA_STRIP_HARM"):
                try:
                    _hH139, _wH139 = _cmp.shape
                    _org32H = original.astype(np.float32)
                    _out32H = _out.astype(np.float32)
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
                            _yZ = min(_hH139, int(ly1) + 2)
                            # ±۱۸px بیرونِ باکسِ خط = نمونهٔ زمینهٔ
                            # اطرافِ خط (گپِ کلمه + حاشیهٔ دو سر) —
                            # پالیِ OCR تاِ لبهٔ متن است و بدونِ
                            # این بسط، ستونِ آزادِ کافی وجود ندارد
                            _xA = max(0, int(lx0) - 18)
                            _xZ = min(_wH139, int(lx1) + 19)
                            _bh = _yZ - _yA
                            if _bh < 12 or _bh > 220 or \
                                    _xZ - _xA < 40:
                                continue
                            _mB = _cmp[_yA:_yZ, _xA:_xZ]
                            if int(_mB.sum()) < 400:
                                continue
                            _sub = _out32H[_yA:_yZ, _xA:_xZ]
                            _orgB = _org32H[_yA:_yZ, _xA:_xZ]
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
                                # v1.14.241 — گاردِ ناهمگنیِ درون‌ردیف:
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
                                    _rf241 = _orgB[_ri][_free]
                                    if float(np.max(np.std(
                                            _rf241, axis=0))) > 18.0:
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
                            _vbA = min(_hH139, _yZ + 4)
                            _vbB = min(_hH139, _yZ + 10)
                            _vok = []
                            if _vtB > _vtA:
                                _vok.append(np.median(
                                    _org32H[_vtA:_vtB, _xA:_xZ]
                                    .reshape(-1, 3), axis=0))
                            if _vbB > _vbA:
                                _vok.append(np.median(
                                    _org32H[_vbA:_vbB, _xA:_xZ]
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
                            _out32H[_yA:_yZ, _xA:_xZ] = _sub
                            _nfixH += 1
                    if _nfixH:
                        _out = np.clip(
                            _out32H, 0, 255).astype(np.uint8)
                        if verbose:
                            print(f"  [✓]همسازِ نوار: {_nfixH} "
                                  f"خطِ ناهمرنگ اصلاح شد")
                except Exception:
                    pass
            try:
                if verbose:
                    print(f"  [*] دو-عکسی: خروجی = عکسِ اصلی + "
                          f"{int(_cmp.sum())}px نوارِ متنِ پاک‌شده")
                    # v1.14.74 — انتقالِ «همین لحظه، همین تصویر»: هر عکس بلافاصله
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
        """v1.14.104 — پرِ فلتِ «قطعیِ» اینتریورِ بالنِ سیستم (باکسِ سفید).

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
                        _g104 = cv2.cvtColor(
                            image, cv2.COLOR_BGR2GRAY)
                        _px104 = _g104[_intr]
                        if float((_px104 >= 180).mean()) < 0.45:
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
        """v1.14.66 — هالهٔ گلوِ اشباعِ گرمِ دورِ متن (قرمز/نارنجی/زرد/
        سرخابی — مثلِ کارتِ «Crimson Dragon») جزوِ جوهرِ متن حساب می‌شود.
        پیکسل‌هایِ پُراشباعِ گرمِ «چسبیده به ماسک» (تا band پیکسل) به ماسک
        اضافه می‌شوند تا هر مسیرِ پاکسازی آن‌ها را هم ببرد — وگرنه هاله
        زنده می‌ماند و «لکهٔ قرمز» دیده می‌شود (POCO F4). فقط توده‌های
        چسبیده به ماسک؛ تراشهٔ پراکنده و هنرِ دور دست‌نخورده می‌ماند.
        درخواستِ صریحِ کاربر: «اشکال نداره بیشتر پاک شه».
        v1.14.67 — گوشیِ POCO F4 هنوز لکه داشت: دنبالهٔ کم‌رنگِ هاله
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
            # v1.14.82 — «هالهِ واقعی در برابر زمینهِ هنری»:
            # هالهِ حقیقی نارین نازکی است که چند پیکسل بعد از لبهِ حروف
            # تمام می‌شود. اگر تودهِ گرمِ هم‌ماهِ یک مؤلفهٌ خیلی
            # بیرونِ حلقه (تا 3×band) ادامه داشته باشد = خودِ
            # زمینهِ قرمز/گرمِ کارت است، نه هالهِ حروف → هرگز
            # جذب نشود (خطای کارت img2: +107هزارpx هنر جذب ماسک
            # شد و کل کارت با رنگ پر شد).
            try:
                _warmfree = (warm & (~m0)).astype(np.uint8)
                _nw82, _lw82 = cv2.connectedComponents(_warmfree, 8)
                if _nw82 > 1:
                    _k82 = 2 * int(band) * 3 + 1
                    _out82 = (cv2.dilate(
                        m0.astype(np.uint8),
                        np.ones((_k82, _k82), np.uint8)) > 0)
                    _far82 = (warm & (~_out82) & (~m0))
                    _tot82 = np.bincount(
                        _lw82[_warmfree > 0].ravel(), minlength=_nw82)
                    _far82c = np.bincount(
                        _lw82[_far82].ravel(), minlength=_nw82)
                else:
                    _lw82 = None
            except Exception:
                _lw82 = None
            hgt, wdt = halo.shape
            for i in range(1, n):
                if stats[i, cv2.CC_STAT_AREA] < 12:
                    continue
                if _lw82 is not None:
                    try:
                        _wid82 = int(np.bincount(
                            _lw82[lab == i].ravel(),
                            minlength=_nw82).argmax())
                        if _wid82 != 0:
                            _tot = int(_tot82[_wid82])
                            _fr = int(_far82c[_wid82])
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
            # v1.14.67 — گشادکردنِ ۷px: مرزِ ماسک باید از دنبالهٔ هاله
            # رد شود؛ وگرنه پرکنندهٔ گرادیانی رنگِ هاله را داخل می‌کشد
            keep = cv2.dilate(keep, np.ones((7, 7), np.uint8))
            return ((m0 | (keep > 0)).astype(np.uint8)) * 255
        except Exception:
            return mask

    def clean_image(self, image: np.ndarray, regions: List[TextRegion]) -> np.ndarray:
        # v1.14.210 — پوستهٔ قفل‌دار: بدنهٔ اصلی در _clean_image_page زیرِ
        # قفلِ سریالِ کلاس اجرا میشود تا پاکسازیِ همزمانِ دو صفحهٔ بچ
        # (کارگرهایِ فازِ دوم) وضعیتِ صفحه‌محور را قاطی نکند (راغزارشِ
        # سازنده: «دست جمعی متن قبلی میمونه / کلِ حباب انتقال میده حباب
        # خراب میکنه — تکی اوکیه»). حالتِ تکی تغییری نمی‌بیند (یک صفحه =
        # یک قفلِ بی‌رقیب).
        _lk = getattr(MangaTranslator, "_page_clean_lock", None)
        if _lk is None:
            return self._clean_image_page(image, regions)
        with _lk:
            return self._clean_image_page(image, regions)

