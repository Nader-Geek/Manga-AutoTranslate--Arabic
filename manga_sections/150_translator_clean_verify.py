# BUILD-STRIP-START
# ─────────────────────────────────────────────────────────────
# ⚠️ MangaTranslator (۶ از ۱۳) — پاکسازیِ نهایی: _mt_polygon_clean، inpaintهای OpenCV، حفاظتِ ساختاری، بازرسی/تعمیر
# این فایل «قطعهای از بدنهٔ کلاس MangaTranslator» است و بهتنهایی
# اجرا نمیشود — scripts/build_manga.py این محتوا را بههمان ترتیبِ
# شمارهٔ فایل، داخلِ کلاس در manga.py میچسباند. کلاسِ پوششیِ زیر فقط
# برای معتبر بودنِ سینتکسِ این فایلِ تکی است و موقعِ بیلد حذف میشود.
class _MangaTranslatorBody_150:
# BUILD-STRIP-END
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
        """v1.14.48 — پرکردنِ استروک‌هایِ نازک روی زمینهٔ گرادیانی با
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
        # v1.14.206g — ترمیمِ «تکهٔ سیاهِ تازه»: Telea از مرزِ ماسک رنگ
        # میکشد و اگر دورِ ماسک تیره باشد (دورخطِ سیاهِ متنِ دورخط‌دار
        # img3 / جوهرِ چسبیده به ماسک)، داخلِ پرشده لکهٔ سیاه میسازد.
        # تکههایِ تیرهٔ تازهٔ داخلِ ماسک (خروجی <70 جایی که حاشیهٔ
        # اورجینالِ اطراف روشن >110 بوده) پیدا، گشاد ۹px و یک Telea
        # کوچکِ دیگر — مرزِ این بار هنرِ اطراف است نه خودِ دورخط.
        try:
            _go = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _gc = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
            # بیشینهٔ محلی بهجایِ میانگین — کنارِ دورخطِ سیاهِ خودِ متن،
            # میانگینِ ۲۱×۲۱ زیرِ ۱۱۰ میافتد و تکه پیدا نمیشد
            _ring = cv2.dilate(_go, np.ones((31, 31), np.uint8))
            _dkn = ((_gc < 70) & (_ring > 110) & (m > 0))
            _dkn = cv2.morphologyEx(
                _dkn.astype(np.uint8), cv2.MORPH_OPEN,
                np.ones((3, 3), np.uint8))
            if int(cv2.countNonZero(_dkn)) >= 40:
                # v1.14.206h — تله‌آیِ دوم هم از همان دورِ تیره رنگ میکشد؛
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
            # v1.14.47c: به نسخهٔ medianBlur برگشت — بنرهایِ تیره حالا توسط
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
        """v1.14.94 — قفلِ «ساختارِ روشنِ نازک» در بلوک‌هایِ اجباری-LaMa
        (v1.14.59). باکسِ توپرِ بلوکِ تیره گاهی از مرزِ پنل عبور می‌کند و
        قابِ تزئینی/نوارِ لبهٔ پنل (ساختارِ روشنِ نازک) را هم می‌بلعد —
        LaMa با حفرهٔ بزرگِ رویِ ساختار، قاب را «له» می‌کند (نمونهٔ کاربر:
        GREEN MOON — قابِ کنارِ متن ذوب شد). معیارِ ساختار: مؤلفهٔ روشن
        (≥۱۴۸) که ۱) بخشِ معناداری‌اش (≥۲۵٪ یا ≥۴۰۰px) بیرونِ باکس است و
        ۲) نازک است (ضخامتِ تبدیلِ فاصله ≤ 64px) — یعنی قاب/نوار، نه
        تودهٔ پس‌زمینه (گلیفِ متن هم کاملاً داخلِ باکس‌اند و هرگز قفل
        نمی‌شوند). پیکسل‌هایِ قفل از ماسکِ
        بلوک خارج می‌شوند تا LaMa آن‌ها را «زمینه» ببیند و دستِ
        پرکننده‌ها هم به آن‌ها نرسد (مکانیزمِ v1.14.81)."""
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
            # باکسِ توپرِ داخلِ ناحیه (همان +4/-5 مسیرِ v1.14.59)
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
        """v1.14.48 — نقشهٔ «ساختارِ محافظت‌شده» در سطحِ صفحه: دیوارِ حباب و
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
            # v1.14.186 — اندروید (MANGA_PROT_CACHE): این تابع در هر صفحه
            # «دو بار» صدا زده میشود (protect + wall_bandِ v1.14.73 با
            # min_len/near_pxِ متفاوت) و بخشهایِ سنگینش (medianBlurِ ۳۱،
            # ساختِ poly_all، بازِ خطیِ سراسری + distanceTransformها)
            # از min_len/near_px مستقلاند → کشِ کوتاهِ بینِ همان دو
            # فراخوانی (صرفهٔ ~۱-۴ ثانیه در هر صفحه). کلید = آدرسِ بافرِ
            # تصویر + ماسکِ خام + تعدادِ ناحیه؛ و محلِ فراخوانی بعد از
            # بارِ دوم آن را پاک میکند (self._spm_cache = None) تا کش
            # هیچ‌وقت کهنه نشود. PC بدونِ کش — بیت‌به‌بیت.
            _spc186 = None
            _key186 = None
            if _android_gate("MANGA_PROT_CACHE"):
                try:
                    _key186 = (
                        image.__array_interface__["data"][0],
                        image.shape,
                        _raw_mask.__array_interface__["data"][0],
                        len(regions or []))
                except Exception:
                    _key186 = None
                _spc186 = getattr(self, "_spm_cache", None)
            _ln = _vl106 = _hl106 = None
            _hit186 = bool(_spc186 is not None and _key186 is not None
                           and _spc186[0] == _key186
                           and len(_spc186) == 7)
            if _hit186:
                dark_full, poly_all = _spc186[1], _spc186[2]
                out = _spc186[3].copy()
                _ln, _vl106, _hl106 = _spc186[4], _spc186[5], _spc186[6]
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
                # v1.14.48b: تیرگیِ «نسبی» هم — دیوارِ محوِ JPEG (خاکستریِ ۱۲۰-۱۹۰
                # روی زمینهٔ روشن) با آستانهٔ مطلقِ ۱۲۰ گم می‌شد و بخشی از دیوار
                # باز هم لکه می‌شد. medianBlurِ ۳۱ زمینهٔ محلی است.
                try:
                    _bg31 = cv2.medianBlur(g, 31)
                    dark_rel = ((_bg31.astype(np.int16)
                                 - g.astype(np.int16)) > 45)
                    dark = ((g < 120) | dark_rel).astype(np.uint8) * 255
                except Exception:
                    dark = (g < 120).astype(np.uint8) * 255
                dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE,
                                        np.ones((3, 3), np.uint8))
                # v1.14.106 — تیرهٔ کاملِ صفحه (قبل از برشِ باندِ ۲۵px) برای
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
                # v1.14.106 — بازِ خطیِ سراسری: کادرِ پنل/خطِ جدابندِ سرراست
                # (اجرای ≥۶۰px، ضخامت ≤۱۰px، بیرونِ پالیهایِ OCR) سراسری
                # محافظت میشود — نه فقط تکهٔ داخلِ باندِ متن. کیسِ ۱۰۱۸:
                # ماسکِ لوگو/حباب قابِ چپِ پنل را در میان بریده بود و تکههای
                # یتیم مثل «لبهٔ سیاه» دیده میشدند.
                try:
                    _vl106 = cv2.morphologyEx(
                        dark_full, cv2.MORPH_OPEN,
                        np.ones((60, 1), np.uint8))
                    _hl106 = cv2.morphologyEx(
                        dark_full, cv2.MORPH_OPEN,
                        np.ones((1, 60), np.uint8))
                    if int(cv2.countNonZero(_vl106)) or \
                            int(cv2.countNonZero(_hl106)):
                        # v1.14.106b — ضخامتِ بدونِ پخش: erodeِ بدونِ dilate
                        # تا هستهٔ توپر حذف شود ولی خطِ نازکِ چسبیده به آن زنده
                        # بماند (dilateِ ±۷px قابِ ۵px کناری را هم میکشت —
                        # کیسِ ۱۰۱۸: کلِ قابِ چپِ پنل)
                        _vth = cv2.erode(_vl106,
                                         np.ones((1, 15), np.uint8))
                        _hth = cv2.erode(_hl106,
                                         np.ones((15, 1), np.uint8))
                        _ln = ((_vl106 | _hl106) & ~_vth & ~_hth
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
                            # v1.14.106b — در سطحِ پیکسل: فقط پیکسلهایِ نازک
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
                        import traceback as _tb106
                        print("  [!]قفلِ خط خطا:", flush=True)
                        _tb106.print_exc()
                if _key186 is not None:
                    try:
                        self._spm_cache = (_key186, dark_full, poly_all,
                                           out.copy(), _ln, _vl106,
                                           _hl106)
                    except Exception:
                        pass
            try:
                import os as _os106
                _dp = _os106.environ.get("MANGA_DUMP_PROTECT")
                if _dp:
                    cv2.imwrite(_dp + "_ln.png", _ln)
                    cv2.imwrite(_dp + "_vl.png", _vl106)
                    cv2.imwrite(_dp + "_dark.png", dark_full)
                    cv2.imwrite(_dp + "_poly.png", poly_all)
                    cv2.imwrite(_dp + "_out.png", out)
                    print("[DUMP] protect →", _dp, flush=True)
            except Exception as _e106:
                print("[DUMP] fail", _e106, flush=True)
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
                # v1.14.48b: فقط در bbox کار کن — آرایهٔ کاملِ صفحه در هر
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
            # v1.14.206j — «قابِ رنگیِ» حباب: خطِ نازکِ بلندِ «اشباعِ
            # رنگی» (حبابِ ششضلعیِ سبزِ up0822) تیرهِ خالص نیست و از
            # معیارِ dark جا میماند → داخلِ ماسکِ متن میفتد، donor
            # پاکش میکند و قاب تکهتکه به خروجی میرود. همان شرطهایِ
            # بلندی/نازکی/بیرونِ پالی رویِ کانالِ اشباع اعمال میشود؛
            # متنِ رنگیِ خودِ ناحیه داخلِ پالیهاست و محافظت نمیشود و
            # هالهٔ پهنِ گلو (v1.14.66) هم «نازک» نیست و رد میشود.
            _out_colj = np.zeros((h, w), dtype=np.uint8)
            try:
                _hsvj = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
                # v1.14.206r — رسایِ ۶۰px: کمانهایِ قابِ دورِ متن (بالای
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
                # v1.14.206s — گسترشِ درامتدادِ خط: تکههایِ تقاطعِ قاب با
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
                # پالیِ «خام» — قابِ رنگی فقط لبهٔ پالی را میبُرد؛
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
                # v1.14.206l — قابِ حبابهایِ کوچک هم تکههایِ ریز دارد
                # (حبابِ «HE'S KNOWN…» در up0822: ~۸۷px در کلِ قاب) →
                # آستانه = همترازِ wall_band (۱۶px)
                # v1.14.206q — تکههایِ قابِ رنگی خیلی ریزند (۲×۸px —
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
                    # v1.14.207 — «قابِ رنگی» نباید خودِ حروفِ رنگی را
                    # ببلعد: متنِ بنفشِ اشباعِ درشتِ img6 (S≥۷۰ و «نازکِ»
                    # ≤۱۴px!) ۱۲هزارpx حرف را داخلِ map برد → کامپوزِ
                    # دو-عکسی آن حرفها را از خروجی حذف کرد = «متنِ قبلی
                    # جا میماند». کامپوننتِ بزرگِ «عمدتاً داخلِ پالیِ
                    # OCR» = حرف است نه قاب (قابِ حباب عمدتاً بیرونِ
                    # پالیست) → رد. تکههایِ ریزِ تقاطعِ قاب/حرف
                    # (۲×۸px — v1.14.206q) بدونِ گیت میمانند.
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
                if self.debug or os.environ.get('MANGA_204DBG'):
                    import traceback as _tb206j
                    print("  [!]قفلِ قابِ رنگی خطا:", flush=True)
                    _tb206j.print_exc()
            # v1.14.206n — نقشهٔ «فقطِ قابِ رنگی» جدا نگه داشته میشود تا
            # _expand_donor_text_strips فقط قابِ رنگی را در donor آزاد
            # کند (رنگِ قاب واردِ پرِ متن نشود) — دیوارِ تیره مثلِ قبل.
            self._page_colored_protect = _out_colj \
                if int(np.count_nonzero(_out_colj)) else None
            # v1.14.212 — نقشهٔ «روکشِ حاشیه‌نویسیِ ورودی» (up0822):
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
                _anl212 = np.zeros((h, w), dtype=np.uint8)
                _flat212m = np.zeros((h, w), dtype=np.uint8)
                _fill212 = np.zeros((h, w, 3), dtype=np.uint8)
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
                        # v1.14.212d — «شکاف»: باندِ ۶..۲۷px دورِ متنِ خام =
                        # درونِ روکش (بینِ متن و قاب). حبابِ سفیدِ واقعی:
                        # شکاف = سفیدِ تخت. روکش رویِ هنر (پنلِ راستِ
                        # up0822): شکاف = پوست/بافت — حلقهٔ بیرونی به
                        # حاشیهٔ سفیدِ صفحه می‌رسد و غلط می‌شد.
                        _gap212 = cv2.subtract(
                            cv2.dilate(_hz_raw, np.ones((55, 55),
                                                        np.uint8)),
                            cv2.dilate(_hz_raw, np.ones((13, 13),
                                                        np.uint8)))
                        # حلقه = باندِ ~۳۰px دورِ هال (منهایِ خودِ هال)
                        # — مستطیلِ ناحیه خودش میتواند هماندازهٔ روکش باشد
                        # (تشخیصِ حباب، هگزاگونِ حاشیه‌نویسی را میبوسد)
                        # پس حلقهٔ «rect+16 منهایِ هال» خالی میشد.
                        _rz = cv2.subtract(
                            cv2.dilate(_hz, np.ones((89, 89), np.uint8)),
                            cv2.dilate(_hz, np.ones((31, 31), np.uint8)))
                        # محدود به حوالیِ ناحیه (نه فراتر از ۶۰px بیرونِ
                        # مستطیلِ ناحیه — دور از هنرِ بی‌ربط)
                        _cl212 = np.zeros((h, w), dtype=np.uint8)
                        _cl212[max(0, _ry - 60):min(h, _ry + _rh2 + 60),
                               max(0, _rx - 60):
                               min(w, _rx + _rw2 + 60)] = 255
                        _rz = cv2.bitwise_and(_rz, _cl212)
                        _n_rz = int(np.count_nonzero(_rz))
                        if _n_rz < 400:
                            continue
                        # v1.14.212f — «شاهدِ سبز»: جوهرِ رنگیِ داخلِ هال اگر
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
                            _cin212 = (_hz > 0) \
                                & (_hsv_an[..., 1] >= 60) \
                                & (_hsv_an[..., 2] >= 60)
                            _chue212 = _hsv_an[..., 0][_cin212]
                            _gproof212 = False
                            if _chue212.size >= 200:
                                _dH212 = np.abs(_chue212 - 60.0)
                                _dH212 = np.minimum(_dH212,
                                                    180.0 - _dH212)
                                _gproof212 = float(
                                    (_dH212 <= 25.0).mean()) >= 0.60
                            else:
                                _gproof212 = False
                        except Exception:
                            _gproof212 = False
                        if not _gproof212:
                            # v1.14.212b — حلقه فقط «روشنِ» خودش را نشانِ
                            # زمینه میدهد: باندِ دورِ بلوک، دیوارِ تیرهٔ
                            # حباب/هنر هم دارد (rstd تا ۱۰۰ رویِ up0822)؛
                            # زمینهٔ واقعی = پیکسلهایِ «روشنِ کم‌اشباعِ»
                            # حلقه (کاغذ/داخلِ حبابِ سفید).
                            _rzpx = _rz > 0
                            _rv_an = _hsv_an[..., 2][_rzpx]
                            _rs_an = _hsv_an[..., 1][_rzpx]
                            _br212 = (_rv_an >= 160.0) \
                                & (_rs_an <= 35.0)
                            _bfrac212 = float(_br212.mean()) \
                                if _br212.size else 0.0
                            if _bfrac212 < 0.35:
                                continue
                            _rgray = _gray_an[_rzpx][_br212] \
                                if bool(_br212.any()) else None
                            if _rgray is None \
                                    or float(np.std(_rgray)) > 26.0:
                                continue  # حتی روشنها هم ناهموار — هنر
                            _rsv = _hsv_an[_rzpx][_br212]
                            if float(np.median(_rsv[:, 1])) > 30.0:
                                continue  # حلقهٔ رنگی (زرد/آسمان) — رد
                        # v1.14.212d — «سفیدِ تختِ واقعی» از «شکافِ درونِ
                        # روکش» سنجیده میشود (نه حلقهٔ بیرونی که تا
                        # حاشیهٔ سفیدِ صفحه می‌رسد): شکافِ «تختِ سفیدِ
                        # بی‌بافت» = حبابِ سفیدِ واقعی → پرِ تختِ سفید.
                        # شکافِ هنری حتی وقتی شستشویِ سبز آن را کم‌اشباعِ
                        # روشن کرده، «بافت» دارد (هاشور/اسکرین‌تون —
                        # انرژیِ فرکانسِ بالا) → LaMa (پنلِ راستِ up0822).
                        try:
                            _gpx212 = _gap212 > 0
                            _gv212 = _hsv_an[..., 2][_gpx212]
                            _gs212 = _hsv_an[..., 1][_gpx212]
                            _gb212 = (_gv212 >= 220.0) & (_gs212 <= 25.0)
                            _gfrac212 = float(_gb212.mean()) \
                                if _gb212.size else 0.0
                            _hf212 = 99.0
                            try:
                                _med212 = cv2.medianBlur(
                                    _gray_an, 5)
                                _hf_in212 = np.abs(
                                    _gray_an.astype(np.int16)
                                    - _med212.astype(np.int16))
                                _hf212 = float(np.median(
                                    _hf_in212[_gpx212]))
                            except Exception:
                                pass
                            _whiteflat212 = (
                                _gfrac212 >= 0.45
                                and bool(_gb212.any())
                                and float(np.median(_gv212[_gb212]))
                                >= 240.0
                                and _hf212 <= 3.0)
                        except Exception:
                            _whiteflat212 = False
                        if os.environ.get("MANGA_212DBG") == "2":
                            try:
                                _ovw = int(np.count_nonzero(
                                    (_hz > 0)
                                    & (_hsv_an[..., 1] >= 24)
                                    & (_hsv_an[..., 2] >= 60)))
                                print(f"    [212] rect=({_rx},{_ry},"
                                      f"{_rw2}x{_rh2}) "
                                      f"colpx={_ovw} "
                                      f"gap={int((_gap212 > 0).sum())} "
                                      f"gfrac={_gfrac212:.2f} "
                                      f"gV={float(np.median(_gv212[_gb212])) if bool(_gb212.any()) else -1:.0f} "
                                      f"ghf={_hf212:.1f} "
                                      f"flat={_whiteflat212}",
                                      flush=True)
                            except Exception:
                                pass
                        # پیکسلهایِ رنگیِ داخلِ هال = روکشِ حاشیه‌نویسی
                        _col_an = ((_hsv_an[..., 1] >= 24)
                                   & (_hsv_an[..., 2] >= 60))
                        _ov = ((_hz > 0) & _col_an)
                        _n_ov = int(np.count_nonzero(_ov))
                        # v1.14.212f — حضور = رنگِ فراوان (S≥۲۴ — شستشو)
                        # + «قابِ سبزِ اشباع» (S≥۶۰، هیویِ سبزِ ۴۰..۸۰،
                        # ≥۱۵۰px): fringeیِ JPEG (lang_ko — هیویِ آبیِ
                        # ۱۰۰..۱۲۰) و متنِ آبی-خاکستری قابِ سبز ندارند.
                        _n60_212 = 0
                        try:
                            _hue212 = _hsv_an[..., 0].astype(np.int32)
                            _n60_212 = int(np.count_nonzero(
                                (_hz > 0)
                                & (_hsv_an[..., 1] >= 60)
                                & (_hsv_an[..., 2] >= 60)
                                & (_hue212 >= 40) & (_hue212 <= 80)))
                        except Exception:
                            _n60_212 = 0
                        if _n_ov < max(400, int(0.03 * int(
                                np.count_nonzero(_hz)))) \
                                or _n60_212 < 150:
                            continue
                        # v1.14.212e — ناحیهٔ روکش = هالِ متن + ۲۵px
                        # (داخلِ جعبه) ∪ کمانهایِ نازکِ رنگیِ قاب تا
                        # ~۸۱px (محدود به مستطیلِ ناحیه + ۲۴px). جعبهٔ
                        # حاشیه‌نویسی خودش «جعبهٔ سفید» است — پرِ تختِ
                        # سفیدِ همانِ داخلِ جعبه (شکاف) درست است؛ هنرِ
                        # پشتِ جعبه اساساً در اورجینال هم پنهان است.
                        _ov = (_hz > 0)
                        try:
                            _clb212 = np.zeros((h, w), dtype=np.uint8)
                            _clb212[max(0, _ry - 24):
                                    min(h, _ry + _rh2 + 24),
                                    max(0, _rx - 24):
                                    min(w, _rx + _rw2 + 24)] = 255
                            _hz_far2 = cv2.dilate(
                                _hz, np.ones((163, 163), np.uint8))
                            _far212 = ((_hz_far2 > 0) & _col_an
                                       & (~(_hz > 0))
                                       & (_clb212 > 0))
                            if bool(_far212.any()):
                                _nz212, _lbb212, _stb212, _ = \
                                    cv2.connectedComponentsWithStats(
                                        _far212.astype(np.uint8), 8)
                                _thin212 = np.zeros_like(_far212)
                                for _ci212 in range(1, _nz212):
                                    _ar212 = int(_stb212[
                                        _ci212, cv2.CC_STAT_AREA])
                                    if _ar212 < 4 or _ar212 > 12000:
                                        continue
                                    _cm212 = (_lbb212 == _ci212)
                                    try:
                                        _dt212 = cv2.distanceTransform(
                                            _cm212.astype(np.uint8),
                                            cv2.DIST_L2, 3)
                                        if float(_dt212.max()) * 2.0 > 14.0:
                                            continue  # قطور = هنر
                                    except Exception:
                                        continue
                                    _thin212 |= _cm212
                                # حاشیهٔ آنتیآلیاسِ قاب (سبزِ کماشباعِ
                                # S<۲۴ زیرِ آستانه میماند = ردِ کم‌رنگ)
                                # → ۳px دیلیت دورِ هر کمان
                                _thin212 = cv2.dilate(
                                    _thin212.astype(np.uint8),
                                    np.ones((7, 7), np.uint8)) > 0
                                _ov = _ov | _thin212
                        except Exception:
                            pass
                        # دیوار/ساختارِ تیره (protect) هرگز پاک نشود
                        _ov = _ov & (out == 0)
                        _n_ov = int(np.count_nonzero(_ov))
                        if _n_ov < 400:
                            continue
                        _anl212[_ov] = 255
                        # رنگِ پر = میانهٔ پیکسلهایِ «روشنِ» حلقه — فقط
                        # برایِ نواحیِ «سفیدِ تختِ واقعی»؛ نواحیِ هنری از
                        # donor (LaMa) می‌گیرند. LaMa رویِ ناحیهٔ شسته‌شده
                        # خودش شستشو را زمینه میپندارد و سبز میسازد؛ پرِ
                        # تختِ حلقه چون حلقه تخت است درست است (عینِ 133).
                        if _whiteflat212:
                            _flat212m[_ov] = 255
                            # رنگِ پر = میانهٔ «سفیدِ شکاف» (داخلِ جعبه) —
                            # جعبهٔ حاشیه‌نویسی خودش سفید است؛ حلقهٔ بیرونی
                            # ممکن است هنر/خاکستری باشد (پنلِ راست = 224).
                            try:
                                _fc212 = np.median(
                                    image[_gpx212][_gb212], axis=0)
                                _fill212[_ov] = np.clip(
                                    np.rint(_fc212), 0, 255).astype(
                                        np.uint8)
                            except Exception:
                                pass
                        _nsat_an += 1
                    except Exception:
                        continue
                self._page_annotation_overlay = _anl212 \
                    if int(np.count_nonzero(_anl212)) else None
                self._page_annotation_flat = _flat212m \
                    if int(np.count_nonzero(_anl212)) else None
                self._page_annotation_fill = _fill212 \
                    if int(np.count_nonzero(_anl212)) else None
                try:
                    _dp212 = os.environ.get("MANGA_DUMP_212", "")
                    if _dp212:
                        cv2.imwrite(_dp212 + "_overlay.png", _anl212)
                        cv2.imwrite(_dp212 + "_flat.png", _flat212m)
                        cv2.imwrite(_dp212 + "_fill.png", _fill212)
                        print("[DUMP] 212 ->", _dp212, flush=True)
                except Exception:
                    pass
                if _nsat_an and (self.debug
                                 or os.environ.get("MANGA_212DBG")):
                    try:
                        print(f"  [*]روکشِ حاشیه‌نویسی: "
                              f"{int(np.count_nonzero(_anl212))}px در "
                              f"{_nsat_an} ناحیه — پاک میشود",
                              flush=True)
                    except Exception:
                        pass
            except Exception:
                self._page_annotation_overlay = None
                self._page_annotation_flat = None
                self._page_annotation_fill = None
            # v1.14.65 — بنرِ تبلیغ هرگز protect نمی‌شود: سایه/لبهٔ تیرهٔ بنر
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
        """v1.14.65 — بنرِ تبلیغ تقریباً همیشه بزرگ‌تر از باکسِ OCR است:
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
        """v1.14.48 — جاروی لکه‌هایِ محوِ داخلِ حباب‌هایِ سفیدِ تمیز.
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
            # v1.14.48c: ناحیهٔ عظیم (بنر/پروموی تمام‌صفحه در نوارِ بلند)
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
                # v1.14.48b: اینتریور نباید از دیوار نشت کرده باشد — protect
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
                # v1.14.49 — چکِ نشت: اینتریورِ واقعیِ حباب هیچ‌وقت به لبهٔ
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
                # v1.14.48b: فرسایشِ ۷px — با erode_iters=0 اینتریور از
                # شکافِ ریزِ دیوار (JPEG) به بیرون نشت می‌کند و خودِ دیوار
                # داخلِ اینتریور می‌افتد → سویپ دیوار را «بلاب» می‌خواند و
                # می‌خورد (دقیقاً همان لکه‌محوییِ باقی‌مانده روی دیوار)
                _int_e = cv2.erode(interior, np.ones((7, 7), np.uint8))
                if int(cv2.countNonZero(_int_e)) < 400:
                    continue
                # v1.14.49: نوارِ امن — فقط پیکسل‌هایِ حداقل ~۹px داخلِ اینتریور
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
                # v1.14.48b: سقفِ مکانی — بلاب‌ها فقط تا ~۱۲px بیرونِ مستطیلِ
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
                # v1.14.48b: هالهٔ خیلی محو (ارواحِ بازسازیِ LaMa / JPEG halo)
                # فقط در همسایگیِ ۲۵px جوهرِ متنِ اصلی — آستانهٔ ملایم‌تر
                try:
                    _blobs |= (((_int_e > 0) & (gc < med_c - 16.0) & _ink_d)
                               .astype(np.uint8) * 255)
                except Exception:
                    pass
                # v1.14.48b: ساختارِ محافظت‌شده (دیوار/کادر) هرگز بلاب نیست
                _pp2 = getattr(self, "_page_protect", None)
                if _pp2 is not None:
                    try:
                        _blobs[_pp2[y0:y1, x0:x1] > 0] = 0
                    except Exception:
                        pass
                if _rb_band is not None:
                    _blobs[~_rb_band] = 0
                # v1.14.49: بلابِ نزدیکِ دیوار هرگز (TELEA دیوار را می‌خورد)
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
                # v1.14.48b: پولیشِ سفید — موتیلینگِ محوِ بازسازیِ LaMa داخلِ
                # حبابِ یکدست (ارواحِ خاکستریِ چرخانی) به رنگِ زمینه نرم شود
                # v1.14.49: پولیش فقط در همسایگیِ جوهرِ متنِ قبلی — نه کلِ
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

    # v1.14.105 — وارسیِ نهاییِ ضدِ خرابیِ EP — یک‌بار برای کلِ صفحه،
    # درست قبل از خروجِ clean_image. چرا آخرِ کار و نه بعد از هر باکس:
    # ۱) وسطِ پایپ‌لاین، منطق‌هایِ بعدی (LFCM، ردِ گروهِ LaMa، سویپِ
    #    باقی‌مانده، پرِ دونورِ بلوکِ تیره) هنوز کارشان تمام نشده و
    #    وارسیِ میان‌راهی هم‌پوشانی/تناقض می‌سازد (تریگرهایِ کاذبِ 01)؛
    # ۲) هر ترمیمِ میان‌راهی یک فراخوانیِ LaMaِ دیگر است → arenaِ ONNX
    #    رویِ نوارهایِ بلندِ وبتون (۹۰۰×۱۶۰۰۰، باکسِ ۴GB) OOM می‌دهد؛
    # ۳) آنچه کاربر می‌بیند خروجیِ نهایی است — سنجش هم باید رویِ همان
    #    انجام شود. ماسکِ اتحادِ (فقط LaMa/OpenCV) از حلقه می‌آید؛
    #    کامپوننت‌هایِ به‌هم‌چسبیده جدا سنجیده می‌شوند؛ SFX/تبلیغ که هرگز
    #    پاک نشده‌اند ذاتاً بیرونِ ماسک‌اند و دست نمی‌خورند.
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
        # v1.14.107 — قراردادِ دو-عکسی: وارسی/ترمیم فقط رویِ چیزی که
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
            # v1.14.105c — خوشه‌بندیِ نزدیک‌ها: حروف/خط‌هایِ یک بلوکِ متن
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
            # v1.14.106 — جاروی بازماندهٔ تیره (لبه/نوارِ سیاهِ کنارِ پاکشدهها)
            # v1.14.107 — فقط داخلِ نوارِ کامپوز؛ بیرونِ نوار = اورجینال
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
        _stage185("پایانِ پاکسازی — مجموع")

    # v1.14.106 — جاروی بازماندهٔ تیره: لبه/نوارِ سیاهی که بعد از پاکسازی
    # همسایهٔ مستقیمِ نواحیِ پاکشده میماند (سایهٔ لوگو/بنرِ بیرونِ ماسکِ
    # متن — کیسِ ۱۰۱۸). فقط خوشهٔ تیرهٔ کوچکِ محصور در سفیدِ صافِ همسایه؛
    # قاب/سایهٔ جعبههایِ سیستم (دور ازِ نواحیِ LaMa) و خطِ هنریِ بلند هرگز.
    # v1.14.107 — «limit» = نوارِ کامپوز: هدف‌ها و نوشتن‌ها فقط داخلِ
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
        # v1.14.107 — قفلِ نوارِ کامپوز رویِ هدف‌ها
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
            # v1.14.107 — نوشتن هم فقط داخلِ نوارِ کامپوز
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

    # v1.14.105 — وارسیِ پس از پاکسازی + ترمیمِ پلکانی (ضدِ خروجیِ بدِ EP)
    # زمینه: رویِ برخی اجراکننده‌ها (CUDA/DML رویِ ویندوز) خروجیِ LaMa ناقص
    # یا کثیف برمی‌گردد در حالی که همان ورودی رویِ CPU تمیز پاک می‌شود —
    # دو نمونهٔ واقعیِ v1.14.104:
    # الف) «GREEN MOON» روی پلاکِ بافت‌مند: نصفِ متن جا مانده (اسیرِ عمودی)
    # ب) داخلِ حباب/جعبهٔ سفید: پرِ LaMa خاکستریِ کثیف به‌جای سفید
    # این گارد مستقل از EP بعد از کامپوزِ هر باکس می‌دود. سنجش‌ها:
    # ۱) جوهرِ باقی‌مانده: نسبتِ «پیکسلِ متن‌نما» (اختلاف از میانهٔ محلی)
    #    داخلِ ماسک در برابرِ حلقهٔ زمینه — بافتِ خودِ زمینه (نقطه‌چین/
    #    موزاییک) با نرخِ حلقه خنثی می‌شود؛
    # ۲) تیرگیِ نسبی: رویِ حلقهٔ صاف، میانهٔ روشناییِ ناحیهٔ پاکشده اگر
    #    ≥ ۱۸ واحد از حلقه تیره‌تر باشد (نوارِ خاکستریِ حباب).
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
        # v1.14.107 — «limit» = نقشهٔ نوارِ کامپوز (self._compose_final_cmp):
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

            md25 = cv2.dilate(m, np.ones((21, 21), np.uint8))
            mdin = cv2.dilate(m, np.ones((13, 13), np.uint8))
            ring = (md25 > 0) & (mdin == 0) & (m == 0)
            if int(ring.sum()) < 80:
                return
            # v1.14.105b — ارزیابی/نوشتن تا ۹px بیرونِ ماسک (هاله/گلو):
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
            #    پلاک/اسکری‌تون پهنایِ زیاد دارد)
            # ۲) خنثاییِ رنگیِ پر (پرِ خرابِ GPU خاکستریِ خنثی است؛ آسمانِ
            #    گرادیانی آبی، پلاک آبی — B-R بزرگ)
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
            # v1.14.105c — بارِ سفیدِ سخت: داخلِ حباب/جعبهٔ سفیدِ تخت
            # (حلقهٔ روشن و صاف) ترمیمِ «فقط-بد-نباشد» کافی نیست؛ دودِ
            # کم‌رنگ (جوهرِ ۰.۰۳) هنوز به چشم می‌آید → مراحل ادامه پیدا
            # می‌کنند تا پرِ ناب (LaMa گشادتر/هموار/تخت) به دست آید
            white_flat = (rs <= 16.0) and (rp90 >= 240.0)
            # سنجشِ جوهر: هم نسبی (حلقه = خطِ پایهٔ بافت) هم tierِ مطلق —
            # پلاکِ «GREEN MOON»: بافتِ حلقه ink_r≈0.13 است ولی پاکِ سالم
            # ink_m≈0.01 دارد؛ متنِ نصفه‌پاک ≈0.32 → tierِ مطلقِ 0.22 می‌گیردش
            # v1.14.105c — tierِ مطلق فقط وقتی که حلقه نسبتاً صاف است
            # (ink_r≤0.18) فعال است تا زمینه‌هایِ بافت‌مند (ink_r تا 0.22+)
            # تریگرِ کاذب نسازند؛ خرابیِ پرَخشن با tierِ پرزورِ 0.40 می‌آید
            # v1.14.105d — کالیبراسیون رویِ رگرسیونِ CPU: tier1 از ۰٫۱۰→۰٫۱۵
            # (چ264_9 crop@(575,3189) جوهرِ ۰٫۱۳ = بافتِ قانونیِ پنجره بود،
            # نه باقی‌مانده) — کیس‌هایِ واقعیِ GPU: A=۰٫۲۵+ (tier2)،
            # B=تیرگی، C=۰٫۳۲ (tier2)، D=تیرگی → همه سرِ جایشان؛
            # FPِ 01 (جوهرِ ۰٫۲۳ خطِ موج‌دار) با گاردِ فقط-LaMa رویِ بافت
            # و قفلِ خطِ هنری ردِ ترمیم می‌شود → خروجیِ دست‌نخورده
            bad_ink = (ink_m > max(0.15, ink_r * 2.0 + 0.04)) or \
                ((ink_m >= 0.22 and ink_r <= 0.18 and
                  ink_m > ink_r * 1.2 + 0.02) or
                 (ink_m >= 0.40 and ink_m > ink_r * 1.1 + 0.02))
            # v1.14.105c — تیرگیِ نسبیِ آستانه ۲۲→۳۰ + حلقهٔ روشن (rp90≥۱۹۰):
            # «پرِ کثیفِ سفید» فقط وقتی معنا دارد که اطراف روشن باشد؛ پنلِ
            # تیرهٔ 012p1 (p90=۱۳۶) تریگرِ کاذب نمی‌سازد؛ نوارِ خاکستریِ
            # واقعیِ GPU (۱۰۱۸) گپِ ۳۹ با حلقهٔ ۲۵۵ دارد
            # v1.14.207h — p90ِ حلقه برایِ «متنِ سفید رویِ بنرِ سیاه»
            # (هدرِ CHAPTER PAGE — img1018) کافی نیست: حلقه = بنرِ سیاه +
            # نوارِ سفیدِ صفحه در ۳۱px → rp90=۲۵۵ و پرِ «سیاهِ درستِ» LaMa
            # «تیرگی» پرچم میخورد → LaMa×۱۷/×۳۳ → بازگردانیِ اورجینال =
            # کلِ متنِ بنر برمیگشت. حالا حلقه باید «عمدتاً» روشن باشد
            # (≥۵۰٪ ≥۱۷۰) نه فقط صدکِ ۹۰.
            bad_gray = (mask_spread <= 22.0) and (neutr <= 14.0) and \
                (gap_dark >= 30.0) and (rp90 >= 190.0) and \
                (float((g[ring] >= 170.0).mean()) >= 0.50)
            # v1.14.106 — دودِ متنِ بازمانده (ghost imprint): پرِ LaMa گاهی
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
                # (نرخِ دود، روشناییِ نابِ هسته) — دود = 195..252؛
                # coreW آستانهٔ زمینهٔ سفید است: پرِ بازسازی‌شدهٔ زمینهٔ
                # بافت‌دار (هاف‌تون) خودش تیره است → coreW کم → گیت نمیگیرد
                v = g_[_mcore > 0]
                if v.size < 40:
                    return 0.0, 0.0
                gh = float(((v >= 195) & (v <= 252)).mean())
                cw = float((v >= 253).mean())
                return gh, cw

            ghost_m, corew_m = _ghost_frac(g)
            # v1.14.107 — گیتِ زمینهٔ سفیدِ «واقعی»: دود فقط رویِ زمینهٔ
            # سفید معنا دارد (بندِ بالای سرش همین را میگوید) ولی سنجهٔ
            # قبلی corew روشناییِ «پرِ فعلی» بود نه زمینه → رویِ متنِ
            # سفید-رو-سیاه (هدرِ ۱۰۱۸: پرِ سفیدِ LaMa رویِ نوارِ سیاه)
            # تریگرِ کاذب می‌ساخت و tier6 کلِ نوار را سفید میکرد. حالا
            # حلقهٔ واقعی باید روشن باشد (≥۴۵٪ پیکسلِ حلقه ≥۲۴۰).
            _rgw = float((g[ring] >= 240).mean())
            bad_ghost = (ghost_m >= 0.05) and (corew_m >= 0.55) and \
                (_rgw >= 0.45)
            # v1.14.135 — «نویزِ توهمِ LaMa» (MANGA_LAMA_NOISEQC):
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

            # v1.14.136 — گیتِ «هنر/سایه» (فقط اندروید — MANGA_VERIFY_ARTSKIP):
            # اگر تنها تریگر «جوهرِ» ضعیف باشد (ink<0.30) و بیش از ۴۰٪
            # ناحیه خاکستریِ خنثی (سایه/بافتِ هنر — نه متنِ جامانده)،
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
                # v1.14.107 — قفلِ نوارِ کامپوز: هیچ ترمیمی بیرونِ نوار
                # نوشته نمیشود (خطِ حباب/قاب/نوارِ هدر دست‌نخورده)
                if limit is not None:
                    _limB = limit[Y0:Y1, X0:X1]
                    if _limB.shape == alpha.shape:
                        alpha = alpha * (
                            (_limB > 0).astype(np.uint8))
                # v1.14.225 — قفلِ ساختار (ضدِ «حبابِ بیرون با حبابِ
                # داخل یک رنگ»): هالهٔ ۱۹pxیِ m_eval وقتی متن به دیوارِ
                # حباب چسبیده باشد از رویِ دیوار میگذشت و پرِ تختِ
                # ترمیم (سفیدِ ناب/تختِ حلقه) دیوار را با رنگِ یکسان
                # میپوشاند = بیرون و داخلِ حباب همرنگ. دیوار/قفلها
                # (_prot_all = ساختارِ روشن + گلو + خطِ سراسری +
                # page_protect) از نوشتنِ ترمیم خارج میشوند — همان
                # قانونی که پرکنندههایِ اصلی از قبل دارند.
                try:
                    _pa225b = getattr(self, "_prot_all", None)
                    if _pa225b is not None:
                        _pac225b = _pa225b[Y0:Y1, X0:X1]
                        if _pac225b.shape == alpha.shape:
                            alpha = alpha * (
                                (_pac225b == 0).astype(np.uint8))
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
            # v1.14.106 — مسیرِ دود هم سختگیریِ مطلق می‌خواهد (جوهرِ دود
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

            # ۰ — v1.14.135 — ضدِ «نویزِ توهمِ LaMa» در حفرهٔ بزرگ
            # (فقط اندروید — MANGA_LAMA_NOISEQC): درمان = پرِ حلقهٔ روشن
            # — ارزان، بی‌نویز و همرنگِ زمینه. (پرچم در bad_noise بالای
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
            # v1.14.105c — کپِ حافظه: برایِ کامپوننت‌هایِ بزرگِ (>۰٫۴Mpx)
            # LaMaِ مجدد صدا زده نمی‌شود (arenaِ ONNX رویِ نوارهایِ بلندِ
            # وبتون OOM می‌دهد) → همان مراحلِ OpenCV (هموار/TELEA/تخت)
            # v1.14.135 — اندروید/میان‌بُرِ حلقهٔ روشن-تخت
            # (MANGA_VERIFY_FASTFILL): وقتی حلقه «سفیدِ صاف» است
            # (white_flat — لاگِ گوشیِ 700×11362: lum=254/p90=255/
            # spread=3)، ترمیمِ LaMa×17 و ×33 هر دو «هنوز بد» میدهند و
            # در نهایت پرِ تخت/سفید برنده است (~۲۰-۴۰ ثانیهٔ هدررفت در
            # هر ناحیهٔ بد) → مستقیم به نردبانِ ارزان (هموار/TELEA/تخت).
            # PC دست‌نخورده.
            _skip_lama135 = (_android_gate("MANGA_VERIFY_FASTFILL")
                             and bool(white_flat))
            _lama_cap = 400_000
            lama = None
            try:
                if not _skip_lama135 and \
                        out.shape[0] * out.shape[1] <= _lama_cap * 4:
                    lama = self._get_lama()
            except Exception:
                lama = None
            # v1.14.138 — خروجِ زودهنگام (فقط اندروید —
            # MANGA_VERIFY_FASTEXIT): اگر LaMa جوهر را نسبت به ورودی
            # عملاً کم نکرد (Δ<0.02 — لاگِ گوشیِ 700×11362:
            # crop@(573,3189) 0.17→0.16 و crop@(420,3261) 0.66→0.60
            # بعدش هم تخت)، دورِ بعدی هم بیاثر است → دورِ بعدی و
            # (برایِ جوهرِ ضعیفِ هنرمانند) تلاشِ ×۲ هم حذف — صرفهٔ
            # ۱-۲ اینفرنسِ LaMa در هر ناحیهٔ بیاثر. PC دست‌نخورده.
            _fx138 = _android_gate("MANGA_VERIFY_FASTEXIT")
            _lama_gain138 = True
            if lama is not None:
                for _dk in (17, 33):
                    if _fx138 and not _lama_gain138:
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
                    ok_b, ok_s, _im138 = _quality(g1, f"LaMa×{_dk}")
                    if ok_s:
                        _blend(res1)
                        return
                    _lama_gain138 = bool(_im138 < ink_m - 0.02)
                    if ok_b and fallback is None:
                        fallback = (res1, f"LaMa×{_dk}")

            # ۳ — پرِ هموارِ زمینه، وگرنه TELEA — فقط رویِ حلقهٔ صافِ روشن؛
            # رویِ بافت (پنجره/کفِ چ264_9) هموار/تخت = پاک‌کنِ بافت‌اند
            # v1.14.105d
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
            # ۶ — v1.14.106 — پرِ سفیدِ ناب: زمینهٔ سفیدِ اثباتشده
            # (coreW≥۰٫۵۵ یعنی پرِ کنونی عمدتاً سفیدِ ناب است و فقط دودِ
            # متن مانده) → رنگِ میانهٔ پیکسلهایِ روشنِ حلقه (۲۵۵ حباب) کل
            # ماسک را پر میکند؛ حباب/صفحهٔ سفید را دودِ ناپذیر میکند.
            # بافت‌ها (coreW کم) هرگز به این مرحله نمی‌رسند.
            try:
                if corew_m >= 0.55:
                    rb = ring & (g >= 245)
                    # v1.14.107 — سفیدِ حلقه باید «غالب» باشد نه فقط حاضر؛
                    # رویِ نوارِ سیاهِ هدر، حاشیهٔ سفیدِ صفحه کافی بود که
                    # rb.sum()≥۸۰ پاس شود و کلِ نوار سفید میشد
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
            # ۷ — v1.14.136 — تلاشِ بزرگ‌نمایی‌شده (فقط اندروید —
            # MANGA_VERIFY_UP2): وقتی هیچ پلهای جواب نداد (لاگِ گوشیِ
            # 700×11362: crop@(420,3261) ink=0.66 — LaMa×17 و ×33 هر دو
            # «هنوز بد» و در نهایت «خروجیِ فعلی ماند» = متنِ کثیفِ پابرجا)،
            # برش ×۲ بزرگ میشود (سقفِ 1600px — ضدفِ لهشدگیِ پچِ 384) و
            # LaMa با ماسکِ گشادِ ×۲ دوباره ران میشود؛ بازسازیِ ریزتر
            # جوهرِ جامانده را اغلب میگیرد. نتیجه با همان گیتِ کیفیت
            # سنجیده میشود؛ قبول نشد → همان «خروجیِ فعلی ماند».
            # PC بایت‌به‌بیت دست‌نخورده.
            if lama is not None and _android_gate("MANGA_VERIFY_UP2") \
                    and out.shape[0] * out.shape[1] <= 400_000 \
                    and not (_fx138 and not _lama_gain138 and ink_m < 0.30):
                try:
                    _wb17 = _bounded(17)
                    if _wb17 is None:
                        _wb17 = m
                    _uh = out.shape[0] * 2
                    _uw = out.shape[1] * 2
                    if _uh <= 1600 and _uw <= 1600:
                        _o2 = cv2.resize(
                            orig, (_uw, _uh),
                            interpolation=cv2.INTER_CUBIC)
                        _m2 = cv2.resize(
                            _wb17, (_uw, _uh),
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

            # ۸ — v1.14.138 — فالبکِ نهاییِ «پرِ ردیفی» (فقط اندروید —
            # MANGA_VERIFY_ROWFILL): وقتی هیچ پلی جواب نداد و جوهرِ
            # جامانده «واقعی» است (bad_ink با ink≥0.22 — لاگِ گوشیِ
            # 700×11362: crop@(420,3261) ink=0.66 = متنِ شبحِ LaMaِ
            # چندخطی که ×17/×33/×2 هر سه نگرفتند و «خروجیِ فعلی ماند»)،
            # برایِ هر ردیفِ ماسک، رنگِ میانهٔ پیکسلهایِ بیرونِ ماسکِ
            # همان ردیف (شکافِ بینِ خطها/حاشیهٔ بلوک) جایگزینِ ماسک
            # میشود — گرادیانِ عمودیِ زمینه حفظ میشود و متنِ شبح حذف؛
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

            # v1.14.139 — دامنهٔ پرِ ردیفی جوهرِ ضعیفِ تأییدشده را هم
            # میگیرد: لاگِ گوشیِ v1.14.138 — crop@(573,3189) با
            # ink=0.16/حلقه=0.03/neutr=31 توسطِ خودِ وارسی «جوهر» پرچم
            # شد (دود=1.00) ولی گیتِ قدیمیِ ink≥0.22 فالبکِ نهایی را
            # قفل کرد → «ترمیمِ کامل نشد — خروجیِ فعلی ماند» = تکهٔ
            # حرف رویِ تصویر. شرطِ تازه: جوهرِ ≥۰٫۱۰ وقتی حلقه پاک
            # است (ink_r≤0.10) و حلقه گسترهٔ صدکیِ معقول دارد (rs≤30
            # — ضدِ زمینهٔ بافت‌مند/هنری). PC بیت‌به‌بیت.
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
                          f"کامل نشد → فالبکِ نهاییِ ۲۲۵",
                          flush=True)
                except Exception:
                    pass
            # v1.14.225 — پایانِ «بازگردانیِ اورجینال» (۲۰۱). دستورِ
            # سازنده: «متنِ قبلی جا میمونه… باید بتونن خوب بپاکن» —
            # برگرداندنِ پیکسلِ اورجینال در ناحیهٔ «متن» یعنی خودِ
            # متنِ انگلیسیِ خام برمیگشت (لاگِ واقعیِ گوشیِ v1.14.217:
            # crop@(1673,0) — LaMa×2-برش «هنوز بد» → [↺201] → متنِ
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
            _art_like225 = bool(
                rs > 22.0 and ink_m < 0.30 and neutr >= 40.0)
            if _art_like225:
                if self.debug:
                    try:
                        print(f"  [🔍225] جوهرِ ضعیف + زمینهٔ هنریِ "
                              f"crop@({cx0},{cy0}) → خروجیِ فعلی ماند "
                              f"(بدونِ پر و بدونِ بازگردانی)", flush=True)
                    except Exception:
                        pass
            else:
                try:
                    _rf225 = _row_fill_res()
                    if _rf225 is not None:
                        _blend(_rf225)
                        if self.debug:
                            try:
                                print(f"  [✓225] پرِ ردیفیِ نهاییِ "
                                      f"crop@({cx0},{cy0}) — بدونِ "
                                      f"بازگردانیِ اورجینال", flush=True)
                            except Exception:
                                pass
                    else:
                        _col225 = np.median(
                            out[ring].astype(np.float32),
                            axis=0).astype(np.float32) \
                            if int(ring.sum()) else np.array(
                                [252.0, 252.0, 252.0], np.float32)
                        _flat225 = np.repeat(
                            _col225[None, None, :], out.shape[0],
                            axis=0).repeat(out.shape[1], axis=1)
                        _blend(_flat225.astype(np.uint8))
                        if self.debug:
                            try:
                                print(f"  [✓225] پرِ تختِ نهاییِ "
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

