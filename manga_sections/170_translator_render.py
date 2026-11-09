# BUILD-STRIP-START
# ─────────────────────────────────────────────────────────────
# ⚠️ MangaTranslator (۸ از ۱۳) — رندرِ متن: فونتها، شکلدهیِ فارسی، wrap_and_fit، render_translations
# این فایل «قطعهای از بدنهٔ کلاس MangaTranslator» است و بهتنهایی
# اجرا نمیشود — scripts/build_manga.py این محتوا را بههمان ترتیبِ
# شمارهٔ فایل، داخلِ کلاس در manga.py میچسباند. کلاسِ پوششیِ زیر فقط
# برای معتبر بودنِ سینتکسِ این فایلِ تکی است و موقعِ بیلد حذف میشود.
class _MangaTranslatorBody_170:
# BUILD-STRIP-END
    @staticmethod
    def _fa_probe_text() -> str:
        if MangaTranslator._FA_PROBE_CACHE is not None:
            return MangaTranslator._FA_PROBE_CACHE
        letters = "ابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهیآأإئءؤئةی"
        parts: List[str] = []
        for _L in letters:
            parts += [_L, _L + _L, "ب" + _L + "ب", "ب" + _L, _L + "ب"]
        sample = " ".join(parts) + " ۰۱۲۳۴۵۶۷۸۹ 0123456789 .,!?…:;()«»-"
        try:
            shaped = get_display(arabic_reshaper.reshape(sample))
        except Exception:
            shaped = sample
        txt = "".join(sorted({c for c in shaped
                              if not c.isspace() and c != "\u200c"}))
        # v1.14.229 — لیگاتورهایِ لام-الف (ﻻ/ﻼ و همزه/مده): فونتی که این
        # شش گلیف را ندارد «حملات» را «حم ت» رندر میکند (لا کلاً غیب
        # میشود — فونتِ واقعیِ Vazir-Code همین است؛ حتی نسخهٔ رسمیِ
        # upstream هم ندارد). پروبِ پوشش باید بگیردشان تا فونتِ خراب
        # به فونتِ اصلی فالبک شود. «سلام» هم «لا» دارد — فقط عدد/علامت
        # بی‌خطر است.
        txt += "\uFEF5\uFEF6\uFEF7\uFEF8\uFEFB\uFEFC"
        MangaTranslator._FA_PROBE_CACHE = txt
        return txt

    @staticmethod
    def _font_covers(path: str) -> bool:
        if not path or not os.path.isfile(path):
            return False
        key = os.path.abspath(path)
        cached = MangaTranslator._FONT_COVER_CACHE.get(key)
        if cached is not None:
            return cached
        ok = True
        try:
            f = ImageFont.truetype(path, 32)

            def _rb(ch: str) -> bytes:
                im = Image.new("L", (96, 96), 0)
                ImageDraw.Draw(im).text((24, 24), ch, font=f, fill=255)
                return im.tobytes()

            refs = {_rb("\uE0FA"), _rb("\uE0F9"), _rb("\uE0EF")}
            for _ch in MangaTranslator._fa_probe_text():
                b = _rb(_ch)
                if not any(b) or b in refs:
                    ok = False
                    break
        except Exception:
            ok = True
        MangaTranslator._FONT_COVER_CACHE[key] = ok
        return ok

    def _warn_font(self, key: str, msg: str) -> None:
        seen = getattr(self, "_font_warned", None)
        if seen is None:
            seen = set()
            self._font_warned = seen
        if key not in seen:
            seen.add(key)
            print(msg)

    def _cover_fallback_font(self, exclude: str) -> str:
        cands: List[str] = []
        d = os.path.dirname(os.path.abspath(exclude or self.font_path or ""))
        try:
            if os.path.isdir(d):
                cands += [os.path.join(d, f) for f in sorted(os.listdir(d))
                          if f.lower().endswith((".ttf", ".otf"))]
        except Exception:
            pass
        cands += [
            "/system/fonts/NotoNaskhArabic-Regular.ttf",
            "/system/fonts/NotoNaskhArabicUI-Regular.ttf",
            "/system/fonts/NotoSansArabic-Regular.ttf",
            "/system/fonts/NotoSansArabicUI-Regular.ttf",
            "/system/fonts/DroidSansArabic.ttf",
            "/system/fonts/NotoNaskhArabic-Bold.ttf",
        ]
        ex = os.path.abspath(exclude) if exclude else ""
        for c in cands:
            if os.path.isfile(c) and os.path.abspath(c) != ex and self._font_covers(c):
                return c
        return ""

    def _load_font(self, size: int, style: str = "") -> ImageFont.FreeTypeFont:
        path = self.font_path
        if style:
            cand = (getattr(self, "font_by_style", None) or {}).get(style) or path
            if cand and os.path.isfile(cand):
                if self._font_covers(cand):
                    path = cand
                else:
                    self._warn_font(
                        "style:" + style,
                        f"[!] فونت لحن «{style}» ({os.path.basename(cand)}) گلیف‌های "
                        f"فارسی را کامل ندارد (به‌جای حرف مربع می‌افتاد) → فونت اصلی.")
        if not self._font_covers(path):
            alt = self._cover_fallback_font(path)
            if alt:
                self._warn_font(
                    "main:" + str(path),
                    f"[!] فونت اصلی ({os.path.basename(str(path))}) حروف فارسی را کامل "
                    f"ندارد → {os.path.basename(alt)}")
                path = alt
        return ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.BASIC)

    @staticmethod
    def _stroke_width_for(size: int) -> int:

        if size <= 14:
            return 1
        if size <= 22:
            return 2
        return max(2, size // 16)

    def _max_font_for_region(self, region: "TextRegion") -> int:


        polys = list(getattr(region, "ocr_polys", None) or []) or list(getattr(region, "boxes", None) or [])
        if not polys:
            return 48
        try:
            ang = float(getattr(region, "angle", 0.0) or 0.0)
        except (TypeError, ValueError):
            ang = 0.0
        a = np.deg2rad(ang)
        ca, sa = np.cos(-a), np.sin(-a)
        hs: List[float] = []
        for p in polys:
            try:
                pts = np.asarray(p, dtype=np.float32).reshape(-1, 2)
            except Exception:
                continue
            if pts.shape[0] < 2:
                continue
            rot = np.empty_like(pts)
            rot[:, 0] = pts[:, 0] * ca - pts[:, 1] * sa
            rot[:, 1] = pts[:, 0] * sa + pts[:, 1] * ca
            hs.append(float(rot[:, 1].max() - rot[:, 1].min()))
        if not hs:
            return 48
        h_line = float(np.median(hs))
        if h_line <= 2:
            return 48

        return int(np.clip(round(h_line * 1.2), 12, 48))

    def _wrap_and_fit(
        self, draw: ImageDraw.ImageDraw, text: str, max_w: int, max_h: int,
        style: str = "", max_size: int = 48,
    ) -> Tuple[ImageFont.FreeTypeFont, List[str], int]:

        words = text.split()
        if not words:
            words = [""]
        # دو متن هرگز یکی نمی‌شوند: هر شکستِ \n (از مدل یا از جداکنندهٔ
        # چندمتن) در خطِ خودش می‌ماند و زیرِ خطِ قبل رندر می‌شود.
        _segments = [s.strip() for s in str(text).split("\n")]
        _segments = [s for s in _segments if s] or [str(text).strip() or " "]


        def wrap_at(size: int, line_gap: int):
            font = self._load_font(size, style=style)
            sw = self._stroke_width_for(size)

            usable_w = max(8, max_w - 2 * sw)
            lines: List[str] = []
            for seg in _segments:
                seg_words = seg.split()
                if not seg_words:
                    lines.append("")
                    continue
                current = ""
                for word in seg_words:
                    candidate = f"{current} {word}".strip()
                    w = draw.textbbox(
                        (0, 0), self._shape_farsi(candidate), font=font, stroke_width=sw
                    )[2]
                    if w <= usable_w or not current:
                        current = candidate
                    else:
                        lines.append(current)
                        current = word
                if current:
                    lines.append(current)


            bb = font.getbbox("آیگچ", stroke_width=sw)
            glyph_h = bb[3] - bb[1]
            line_h = glyph_h + line_gap
            total_h = line_h * len(lines) if lines else line_h

            total_h += 2 * sw
            widest = max(
                (
                    draw.textbbox(
                        (0, 0), self._shape_farsi(l), font=font, stroke_width=sw
                    )[2]
                    for l in lines
                ),
                default=0,
            )
            return font, lines, sw, total_h, widest, line_h


        n_words = len(words)
        short_text = n_words <= 2 and sum(len(w) for w in words) <= 12
        min_size = 14 if short_text else 11
        max_size = max(min_size, min(48, int(max_size or 48)))

        smallest_attempt = None

        for line_gap in (4, 2, 1, 0):
            for size in range(max_size, min_size - 1, -1):
                font, lines, sw, total_h, widest, line_h = wrap_at(size, line_gap)
                smallest_attempt = (font, lines, sw, line_h)
                if total_h <= max_h and widest <= max_w:
                    return font, lines, sw


        for size in range(min_size - 1, 5, -1):
            font, lines, sw, total_h, widest, line_h = wrap_at(size, 0)
            smallest_attempt = (font, lines, sw, line_h)
            if total_h <= max_h and widest <= max_w:
                return font, lines, sw

        if smallest_attempt is None:
            font = self._load_font(11, style=style)
            sw = self._stroke_width_for(11)
            return font, [" ".join(words)], sw
        return smallest_attempt[0], smallest_attempt[1], smallest_attempt[2]

    @staticmethod
    def _pick_text_and_stroke(
        cleaned: np.ndarray, original: np.ndarray, region: TextRegion
    ) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
        h_img, w_img = original.shape[:2]
        x, y, w, h = region.rect
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(w_img, x + w), min(h_img, y + h)

        poly_mask = np.zeros((h_img, w_img), dtype=np.uint8)
        for poly in region.boxes:
            cv2.fillPoly(poly_mask, [poly], 255)

        local_mask = poly_mask[y0:y1, x0:x1]
        local_orig = original[y0:y1, x0:x1]
        local_clean = cleaned[y0:y1, x0:x1] if cleaned is not None else local_orig

        if local_orig.size == 0:
            return (15, 15, 15), (255, 255, 255)

        if local_clean.size > 0:
            bg_gray = float(np.median(cv2.cvtColor(local_clean, cv2.COLOR_BGR2GRAY)))
        else:
            bg_gray = 128.0

        orig_gray = cv2.cvtColor(local_orig, cv2.COLOR_BGR2GRAY).astype(np.float32)
        if bg_gray < 128:
            ink_m = (orig_gray > bg_gray + 20) & (local_mask > 0)
        else:
            ink_m = (orig_gray < bg_gray - 20) & (local_mask > 0)

        ink_pixels = local_orig[ink_m]

        if len(ink_pixels) >= 8:
            bgr = np.median(ink_pixels, axis=0)
            r, g, b = int(bgr[2]), int(bgr[1]), int(bgr[0])

            mx, mn = max(r, g, b), min(r, g, b)
            saturation = mx - mn
            lum = 0.299 * r + 0.587 * g + 0.114 * b

            if saturation < 25:
                if bg_gray >= 140:
                    text_rgb = (18, 18, 18)
                    stroke_rgb = (255, 255, 255)
                else:
                    text_rgb = (245, 245, 245)
                    stroke_rgb = (10, 10, 10)
            else:
                text_rgb = (r, g, b)
                if lum >= 140:
                    stroke_rgb = (20, 20, 20)
                else:
                    stroke_rgb = (255, 255, 255)
        else:
            if bg_gray >= 140:
                text_rgb, stroke_rgb = (18, 18, 18), (255, 255, 255)
            else:
                text_rgb, stroke_rgb = (245, 245, 245), (10, 10, 10)

        return text_rgb, stroke_rgb

    def render_translations(self, image: np.ndarray, regions: List[TextRegion],
                            original_image: np.ndarray) -> np.ndarray:
        pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)

        for region in regions:
            if not region.translated_text:
                continue

            try:
                self._render_one_region(pil_img, draw, image, original_image, region)
            except Exception as e:
                # v1.14.149 — «حبابِ سیاه ممنوع»: رندرِ خطاخورده
                # هرگز ناحیهٔ پاکشدهٔ بی‌متن نمیگذارد. گام۱:
                # GC + تلاشِ دوباره (بیشترِ خطاها تخصیصِ لحظهای
                # است). گام۲: رندرِ سادهٔ فال‌بک. گام۳: برگرداندنِ
                # پیکسلهایِ اصلی — هیچ مسیری به باکسِ خالی نیست.
                print(f"  [!] رندر ناحیه {region.id} خطا داد ({e}) → فال‌بک…")
                _done149 = False
                try:
                    import gc as _gc149
                    _gc149.collect()
                    self._render_one_region(pil_img, draw, image, original_image, region)
                    _done149 = True
                    print(f"  [+] ناحیه {region.id} در تلاشِ دوم رندر شد.")
                except Exception:
                    pass
                if not _done149:
                    try:
                        self._render_one_region_fallback(
                            pil_img, draw, image, original_image, region)
                        _done149 = True
                        print(f"  [+] ناحیه {region.id} با رندرِ فال‌بک رندر شد.")
                    except Exception as _e149b:
                        print(f"  [!] فال‌بکِ ناحیه {region.id} هم مرد ({_e149b})")
                if not _done149:
                    try:
                        self._restore_region_pixels(
                            pil_img, image, original_image, region)
                        print(f"  [+] ناحیه {region.id} به پیکسلهایِ اصلی برگشت (حبابِ سیاه ساخته نشد).")
                    except Exception as _e149c:
                        print(f"  [!] بازگردانیِ ناحیه {region.id} ناموفق ({_e149c})")
                continue

        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    def _render_one_region_fallback(self, pil_img, draw, image,
                                    original_image, region) -> None:
        """v1.14.149 — سادهترین رندرِ ممکن برایِ ناحیه‌ای که
        رندرِ اصلی مرد: متنِ چندخطیِ وسطچین با رنگِ خودکار.
        هر گام گاردشده است؛ خطا به caller برمیگردد تا گامِ سوم
        (بازگردانیِ پیکسل) اجرا شود."""
        txt = str(getattr(region, "translated_text", "") or "").strip()
        if not txt:
            return
        try:
            x, y, w, h = region.rect
            x, y, w, h = int(x), int(y), int(w), int(h)
        except Exception:
            return
        try:
            text_rgb, stroke_rgb = self._pick_text_and_stroke(
                image, original_image, region)
        except Exception:
            text_rgb, stroke_rgb = (255, 255, 255), (0, 0, 0)
        sw = 0
        try:
            font = self._load_font(
                max(10, min(48, max(12, h // 3))),
                (getattr(region, "bubble_style", None) or ""))
        except Exception:
            font = self._load_font(18)
        try:
            raw_lines = [s for s in txt.splitlines() if s.strip()] or [txt]
        except Exception:
            raw_lines = [txt]
        max_w = max(20, w - 8)
        lines = []
        for _ln in raw_lines:
            try:
                _sh = self._shape_farsi(_ln.strip())
            except Exception:
                _sh = _ln.strip()
            try:
                _lw = draw.textbbox((0, 0), _sh, font=font,
                                    stroke_width=sw)[2]
            except Exception:
                _lw = 0
            if _lw <= max_w or not _sh:
                lines.append(_sh)
                continue
            _cur = ""
            for _wd in _sh.split(" "):
                _cand = (_cur + " " + _wd).strip()
                try:
                    _cw = draw.textbbox((0, 0), _cand, font=font,
                                        stroke_width=sw)[2]
                except Exception:
                    _cw = 0
                if _cur and _cw > max_w:
                    lines.append(_cur)
                    _cur = _wd
                else:
                    _cur = _cand
            if _cur:
                lines.append(_cur)
        if not lines:
            lines = [txt]
        try:
            _lh = font.getbbox("آیگ", stroke_width=sw)[3] + 6
        except Exception:
            _lh = (getattr(font, "size", 16) or 16) + 8
        total_h = _lh * len(lines)
        _ty = max(0, y + max(0, (h - total_h) // 2))
        for _ln in lines:
            try:
                _tw = draw.textbbox((0, 0), _ln, font=font,
                                    stroke_width=sw)[2]
            except Exception:
                _tw = 0
            _tx = max(0, x + max(0, (w - _tw) // 2))
            draw.text((_tx, _ty), _ln, font=font,
                      fill=tuple(text_rgb)[:3],
                      stroke_width=sw,
                      stroke_fill=tuple(stroke_rgb)[:3])
            _ty += _lh

    def _restore_region_pixels(self, pil_img, image, original_image,
                               region) -> None:
        """v1.14.149 — آخرین گاردِ ضدحبابِ سیاه: پیکسلهایِ
        اورجینالِ ناحیه برمیگردند (متنِ اصلی دیده میشود)."""
        try:
            x, y, w, h = region.rect
            x, y, w, h = int(x), int(y), int(w), int(h)
        except Exception:
            return
        H, W = original_image.shape[:2]
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(W, x + w), min(H, y + h)
        if x1 - x0 < 2 or y1 - y0 < 2:
            return
        _crop149 = original_image[y0:y1, x0:x1]
        _rgb149 = cv2.cvtColor(_crop149, cv2.COLOR_BGR2RGB)
        pil_img.paste(Image.fromarray(_rgb149), (x0, y0))

    def _rescue_empty_ocr_1149(self, image: np.ndarray,
                               regions: List[TextRegion]) -> None:
        """v1.14.149 — نجاتِ OCR برایِ نواحیِ ocr_empty: برشِ
        استانداردِ _ocr_crop + معکوس (متنِ سفید-روی-تیره). متنِ
        نجاتیده → source_text/ocr_polys → ناحیه ترجمه و رندر
        میشود؛ بهجایِ «پاکسازیِ بی‌متن» (حبابِ سیاه)."""
        _resc = 0
        for _r149 in regions:
            if (_r149.source_text or "").strip() \
                    or not getattr(_r149, "ocr_empty", False):
                continue
            try:
                _rx149, _ry149, _rw149, _rh149 = [
                    int(v) for v in _r149.rect]
                _oc149 = self._ocr_crop(
                    image, (_rx149, _ry149,
                            _rx149 + _rw149, _ry149 + _rh149))
                _t2149 = (_oc149[0] or "").strip()
                _p2149 = list(_oc149[1] or []) if len(_oc149) > 1 else []
            except Exception:
                _t2149, _p2149 = "", []
            if not _t2149:
                try:
                    _crop149 = image[
                        max(0, _ry149):_ry149 + _rh149,
                        max(0, _rx149):_rx149 + _rw149]
                    if _crop149.size:
                        _res2149 = None
                        try:
                            _res2149 = self.ocr.ocr(
                                cv2.bitwise_not(_crop149))
                        except Exception:
                            _res2149 = None
                        _txts149 = []
                        if _res2149:
                            for _ln149 in (_res2149[0] or []):
                                try:
                                    _tv149 = _ln149[1]
                                    if isinstance(_tv149, (tuple, list)):
                                        _tv149 = _tv149[0]
                                    if str(_tv149).strip():
                                        _txts149.append(
                                            str(_tv149).strip())
                                except Exception:
                                    continue
                        _t2149 = " ".join(_txts149).strip()
                except Exception:
                    pass
            # v1.14.201 — نجاتِ بی‌جا ممنوع: «۹۹»، «年»، «/»، «三弄» و
            # امثالِ آن نویزِ OCR رویِ افکتِ صوتیِ کره‌ای/هنر است نه متنِ
            # نجاتیده — اگر پذیرفته شود به مترجم میرود و ترجمهٔ آشغالِ
            # فارسی رویِ همان ناحیه مینشیند (لاگِ فصلِ ۱۱۰: حباب با
            # «تو کی هستی؟! جایزه‌ای؟ من!»). نجات فقط با حداقلِ ۲ حرفِ
            # لاتین و برتریِ حرف بر نویز پذیرفته میشود؛ باقی ocr_empty
            # میماند (متنِ اصلی سرِ جایش — پاک نشد به همان قاعدهٔ ۱۴۹).
            _lt201 = sum(1 for _c201 in _t2149
                         if _c201.isascii() and _c201.isalpha())
            if _t2149 and _lt201 >= 2 and \
                    _lt201 * 2 >= len(_t2149.replace(" ", "")):
                _r149.source_text = _t2149
                if _p2149:
                    _r149.ocr_polys = _p2149
                _r149.ocr_empty = False
                _resc += 1
                try:
                    print(f"    [+] نجاتِ OCR ناحیه {_r149.id}: {_t2149[:48]!r}")
                except Exception:
                    pass
            elif _t2149 and self.debug:
                try:
                    print(f"    [🔍201] نجاتِ ناحیه {_r149.id} رد شد "
                          f"(نویز، نه متن): {_t2149[:32]!r}")
                except Exception:
                    pass
        if _resc:
            print(f"    [+] {_resc} ناحیه با نجاتِ OCR متن گرفت → ترجمه میشوند")

    def _draw_debug_regions(self, image: np.ndarray, regions: List[TextRegion]) -> np.ndarray:
      vis = image.copy()


      colors = {
        "dialogue": (0, 0, 255),
        "promo": (0, 165, 255),
        "sfx": (255, 255, 0),
        "junk": (128, 128, 128),
    }

      for r in regions:
        x, y, w, h = r.rect
        color = colors.get(r.kind, (0, 0, 255))


        cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)


        cx = x + w // 2
        cv2.circle(vis, (cx, y + h // 2), 3, (0, 255, 255), -1)


        label = f"[{r.id}] {r.kind[:3].upper()}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.rectangle(vis, (x, y - th - 6), (x + tw + 4, y), color, -1)
        cv2.putText(vis, label, (x + 2, y - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)


        short = (r.source_text or "")[:28]
        if short:
            cv2.putText(vis, short, (x, y + h + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 0), 1, cv2.LINE_AA)
        # v1.14.43: مختصاتِ ناحیه روی خودِ تصویر دیباگ — «مکانش کجاست» بدون لاگ
        # چیپِ تیره + متنِ زرد تا روی هر پس‌زمینه‌ای خوانا باشد
        try:
            _ct = f"({x},{y} {w}x{h})"
            (_cw, _ch), _ = cv2.getTextSize(_ct, cv2.FONT_HERSHEY_SIMPLEX,
                                            0.38, 1)
            _cy = y + h + 34
            cv2.rectangle(vis, (x, _cy), (x + _cw + 4, _cy + _ch + 6),
                          (30, 30, 30), -1)
            cv2.putText(vis, _ct, (x + 2, _cy + _ch + 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255),
                        1, cv2.LINE_AA)
        except Exception:
            pass

        ai = (r.translated_text or "").strip()
        if ai:

            ai_show = ai if all(ord(c) < 128 for c in ai[:20]) else f"AI[{r.id}] OK"
            cv2.putText(vis, ai_show[:32], (x, y + h + 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 128, 0), 1, cv2.LINE_AA)
            st = (getattr(r, "bubble_style", None) or "").strip()
            if st:
                cv2.putText(vis, st, (x + 2, y + 14),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1, cv2.LINE_AA)

      # v1.14.173 — باکسهایِ خامِ detector-v4-s با رنگِ سبز رویِ همین
      # DEBUGِ صفحه — مقایسهٔ مستقیمِ detector در برابرِ OCR بدونِ عکسِ
      # جدا (دستورِ سازنده: «عکس جدا نشون نده رو همون عکس اصلی دیباگ
      # بزاره با یک رنگ دیگ سبز نشون بده»): سبزِ D## = باکسِ خامِ
      # detectorِ قبلِ فیلتر/OCR؛ قرمزِ [##] = ناحیهٔ نهاییِ بعدِ OCR.
      # اگر متنی در DEBUG سبزِ نداشته باشد → detector نتونسته پیدا کند؛
      # اگر سبز دارد ولی متنِ قرمزش غلط/خالی است → مقصرِ OCR است.
      _det_raw0 = None
      for _r0 in regions:
        _v0 = getattr(_r0, "det_raw", None)
        if _v0:
          _det_raw0 = _v0
          break
      if _det_raw0:
        try:
          _v_h, _v_w = vis.shape[:2]
          for _di, (_dbox, _dcls) in enumerate(_det_raw0):
            try:
              _dx1 = max(0, int(_dbox[0]))
              _dy1 = max(0, int(_dbox[1]))
              _dx2 = max(_dx1 + 1, min(int(_dbox[2]), _v_w - 1))
              _dy2 = max(_dy1 + 1, min(int(_dbox[3]), _v_h - 1))
              cv2.rectangle(vis, (_dx1, _dy1), (_dx2, _dy2),
                            (0, 255, 0), 3)
              cv2.putText(vis, f"D{_di:02d} {_dcls}".strip(),
                          (_dx1 + 4, min(_v_h - 2, _dy1 + 26)),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                          (0, 255, 0), 2, cv2.LINE_AA)
            except Exception:
              continue
        except Exception:
          pass

      return vis


    @staticmethod
    def _skew_from_quads(core_bgr: np.ndarray, quads, ox: int, oy: int, inset: int) -> float:


        try:
            g = cv2.cvtColor(core_bgr, cv2.COLOR_BGR2GRAY)
            med = float(np.median(g))
            ink = (g < max(60, med - 45)).astype(np.uint8) * 255
            h_c, w_c = ink.shape[:2]
            zone = np.zeros_like(ink)
            got = False
            for p in list(quads or []):
                pts = np.asarray(p, dtype=np.float32).reshape(-1, 2).copy()
                pts[:, 0] -= ox + inset
                pts[:, 1] -= oy + inset
                cv2.fillPoly(zone, [pts.astype(np.int32)], 255)
                got = True
            if not got:
                return 0.0
            zone = cv2.dilate(zone, np.ones((5, 5), np.uint8), iterations=1)
            ink = cv2.bitwise_and(ink, zone)
            ink = cv2.dilate(ink, np.ones((3, 3), np.uint8), iterations=1)
            n, lab, st, cents = cv2.connectedComponentsWithStats(ink, connectivity=8)
            pts_list = []
            for i in range(1, n):
                a = int(st[i, cv2.CC_STAT_AREA])
                if a < 60:
                    continue
                pts_list.append(cents[i])
            if len(pts_list) < 3:
                return 0.0
            data = np.asarray(pts_list, dtype=np.float32)
            _, eig, _ = cv2.PCACompute2(data, mean=None)
            v = eig[0]
            a = float(np.degrees(np.arctan2(float(v[1]), float(v[0]))))
            if a > 90:
                a -= 180.0
            elif a < -90:
                a += 180.0
            if abs(a) > 45:
                return 0.0
            return a
        except Exception:
            return 0.0

