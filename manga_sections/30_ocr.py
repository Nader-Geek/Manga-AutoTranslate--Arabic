# BUILD-STRIP-START
# ─────────────────────────────────────────────────────────────
# 📦 OCR — موتورهای متن‌خوانی (Paddle/RapidOCR/نردبان) + تستِ سرعت
# PaddleAndroidOCR، MtLadderOCR و لولهٔ سنجشِ سرعتِ OCR.
# (این سربرگ فقط راهنمای همین فایل است؛ لودرِ manga.py و بیلد حذفش میکنند)
# BUILD-STRIP-END
def _cjk_dominant_154(t: str) -> bool:
    """v1.14.154 — «بعد فارسی بحرف چرا چینی میحرفی» — ریشهٔ واقعی:
    dictِ PP-OCRv6 medium (ppocrv6_chars.txt) = ۱۸۷۰۷ نویسه که ۱۵۷۴۵
    تایش CJK است و فقط ۵۲ تا لاتین؛ با ocr_lang=en رویِ متنِ استایل‌دار،
    argmax میافتد رویِ نویسههایِ CJK → خطِ «انگلیسی» پر از 汉字 میشود
    (ML Kitِ لاتین هرگز نمیساخت). True = خطِ با غلبهٔ CJK → حذف.
    فقط برایِ زبانِ لاتین صدا زده میشود؛ خاموشی: MANGA_CJK_GUARD=0."""
    try:
        _cjk = 0
        _lat = 0
        for _c in t:
            if "\u2e80" <= _c <= "\u9fff" or "\uf900" <= _c <= "\ufaff" \
                    or "\uff00" <= _c <= "\uffef":
                _cjk += 1
            elif _c.isascii() and _c.isalpha():
                _lat += 1
        if _cjk == 0:
            return False
        return _cjk >= max(2, _lat)
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════
# v1.14.187 — موتورِ OCRِ گوشی = RapidOCRِ اندروید (ONNXِ خالص — تنها روش).
# دستورِ سازنده: «متن درست استخراج نمیزنه متن هاش اشتباهه بعضی وقتا
# ۱.۱۴.۱۸۶ https://github.com/RapidAI/RapidOcrAndroidOnnx ببین چجور به
# این خوبی استخراج میکنه همونو رو گوشی بزار … این خیلی خوب استخراج
# میزنه متن هاش خوب در میاره» — یعنی سهگانهٔ RapidOcrAndroidOnnx:
#   det = ch_PP-OCRv4_det_mobile.onnx (DBNet 4.5MB) + cls =
#   ch_ppocr_mobile_v2.0_cls (AngleNet) + rec = ch_PP-OCRv4_rec_mobile
#   (CRNN 10.4MB) — داخلِ ماژولِ «ppocr-sdk» رویِ همان ORTِ رسمی،
#   بیت‌به‌بیتِ پیشپردازش/پسپردازشِ RapidOCR (dilate 2×2، clsِ 192×48،
#   recِ ارتفاعِ ۴۸ + CTCِ blank=۰ + دیکشنریِ متنی).
#   • استخراج فقط رویِ «کراپهایِ detector-v4-s_int8.onnx» صدا زده میشود
#     (همان مسیرِ _ocr_crop → RapidOCRBackend.ocr → self._mobile.ocr)
#     — هیچ پاسِ تمامصفحهای نیست (دستورِ همیشگیِ سازنده: «باید اول
#     detector-v4-s_int8.onnx خوب قسمت های متن پیدا کنه بعد همون قسمت
#     باید استخراج متن استفاده کنه»).
#   • موتور رویِ هر کراپ det+recِ کامل اجرا میکند: DetPreprocessor →
#     DBPostProcessor → QuadTextCrop → cls → RecPreprocessor → CTCDecoder.
#   • قراردادِ خروجی = سطرِ META|lang|n + سطرهایِ ang|conf|box|text|blk
#     (همان قراردادِ همیشه) — پارسرِ مشترک بدونِ تغییر.
# ═══════════════════════════════════════════════════════════════════════

_MOBILE_LANG_MAP = {
    "en": "latin", "latin": "latin", "english": "latin", "fa": "latin",
    "korean": "ko", "ko": "ko",
    "japan": "ja", "ja": "ja", "japanese": "ja",
    "ch": "zh", "zh": "zh", "chinese": "zh", "ch_sim": "zh",
    "zh_hans": "zh", "zh_hant": "zh", "zh-tw": "zh", "zh_tw": "zh",
    # v1.14.190 — چندزبانه: پاسِ اول با recِ پیشفرضِ v6_medium + دوئلِ
    # koِ لازمالآمد (PaddleAndroidOCR._ocr_multi) — «همشو یکجا دانلود نزنه»
    "multi": "multi",
}


def _mobile_lang(lang):
    """نرمالسازیِ زبان برایِ سطرِ METAِ موتورِ گوشی."""
    return _MOBILE_LANG_MAP.get(str(lang or "en").lower(), "latin")


# ═══════════════════════════════════════════════════════════════════
# v1.14.187 — موتورِ OCRِ کراپ = RapidOCRِ اندروید (RapidOcrAndroidOnnx)
# داخلِ ppocr-sdkِ وندورشده رویِ ORTِ رسمی. دستورِ سازنده: «ببین چجور
# به این خوبی استخراج میکنه همونو رو گوشی بزار» + دستورِ قبلی: «اول
# detector-v4-s همه قسمت هایِ متن پیدا کنه فقط همون قسمت ها استخراج
# کنه تا سریعتر باشه». پلِ Kotlin = PaddleOcrBridge (پلِ نازک رویِ
# RapidOcr.create) با قراردادِ سطرهایِ META
# (META|lang|n + ang|conf|box|text|blk) تا پارسرِ مشترک کار کند.
# v1.14.188 — دستورِ سازنده: «چرت پرت هم زیاد استخراج میکنه … همون
# مدل onnx v6 ocr … مدل v6_medium استفاده کن» → مدلها = detِ
# PP-OCRv6_small (10MB — همان detِ PC) + cls (0.6MB) + recِ
# PP-OCRv6_MEDIUM (73MB؛ charsetِ ۱۸۷۰۸یِ ppocrv6_chars) + واریانتهایِ
# زبانِ rec (ja/ko) — دانلودیِ زمانِ اجرا (v1.14.189)؛ latin/zh = recِ mediumِ
# پیشفرض (واریانتِ rec_enِ v4 حذف شد).
# (تاریخچهٔ v1.14.187: سهگانهٔ PP-OCRv4_mobile — det 4.5MB + rec 10.4MB
# + ppocr_keys_v1) انتخابِ زبان (v1.14.188: latin/zh = recِ mediumِ
# پیشفرض؛ فقط ja/ko سشن عوض میکنند) →
# recognizeAuto زبانِ هر کراپ را میفرستد و سشنِ rec رویِ واریانتِ همان
# زبان گرم میشود (ja→japan، ko→korean، بقیه→mediumِ پیشفرض).
# فالبکی نیست؛ خطایِ موتور = خروجیِ خالیِ همان کراپ.
# ═══════════════════════════════════════════════════════════════════
_PAD_STATS = {"ms": 0.0, "n": 0, "lines": 0}


def _pad_stats_note(t0, nlines):
    try:
        _PAD_STATS["ms"] += (time.time() - t0) * 1000.0
        _PAD_STATS["n"] += 1
        _PAD_STATS["lines"] += int(nlines or 0)
        if _PAD_STATS["n"] % 8 == 0:
            print(f"[⚡] پدلِ اندروید: {_PAD_STATS['n']} OCR | "
                  f"مجموعِ {_PAD_STATS['ms'] / 1000.0:.1f}s | "
                  f"میانگینِ {_PAD_STATS['ms'] / max(1, _PAD_STATS['n']):.0f}ms | "
                  f"{_PAD_STATS['lines']} خط")
    except Exception:
        pass


class PaddleAndroidOCR:
    """OCRِ کراپ با موتورِ RapidOCRِ اندروید (RapidOcrAndroidOnnx —
    v1.14.187). det (ch_PP-OCRv4_det_mobile) → DBPostProcess (dilate 2×2،
    unclip 1.6) → کراپِ پرسپکتیو → cls (AngleNetِ 192×48) → rec
    (ch_PP-OCRv4_rec_mobileِ واریانتِ زبان، ارتفاعِ ۴۸، بچِ پدشده) →
    CTC با دیکشنریِ متنی (blank=۰ + سطرها + فاصله). خروجی:
    [ [[box, (text, score)], ...] ] — هم‌قالبِ RapidOcrMobile.
    crop_mode فقط برایِ هم‌امضایی."""

    def __init__(self, lang: str = "en"):
        try:
            from java import jclass
            self._bridge = jclass(
                "com.amirwolf.mangatranslator.PaddleOcrBridge")
        except Exception as e:
            raise RuntimeError(
                "پلِ PaddleOcrBridge در APKِ نصب‌شده نیست — APKِ جدید "
                "(v1.14.187+) را نصب کن: " + str(e)[:90])
        self.lang = _mobile_lang(lang)
        self.debug = True
        # v1.14.190 — وضعیتِ دوئلِ چندزبانه (حافظهٔ کوتاهِ کراپ به کراپ)
        self._multi_pref = None
        self._multi_ko_logged = False
        # v1.14.190 — پیشرفتِ دانلودِ مدلها به لاگِ اپ (دستورِ سازنده:
        # «وقتی داره onnx دانلود میزنه نشون نمیده تو لاگش چقدر دانلود
        # شده») — sinkِ پایتونی به OcrModelStore داده میشود؛ خطوطِ
        # [دانلود] دقیقاً به همان جریانِ لاگی میروند که کاربر میبیند.
        # رویِ APKِ قدیمی/PC بیاثر (best-effort)
        try:
            from java import jclass as _jc, dynamic_proxy as _dp

            class _PyDlSink(_dp(_jc("com.paddle.ocr.util.OcrProgressSink"))):
                def onProgress(self, line):
                    try:
                        print(str(line))
                    except Exception:
                        pass

            _jc("com.amirwolf.mangatranslator.OcrModelStore"
                ).setProgressSink(_PyDlSink())
        except Exception:
            pass
        # v1.14.189 — مدلها دیگر باندلِ APK نیستند (دستورِ سازنده: «onnx
        # تو گوشی واسه استخراج با نصب نیاد … حجم اپ زیاد میشه»)؛ اپ در
        # اولین استفاده فقط مدلهایِ زبانِ انتخابی را از ریلیزِ «models»
        # دانلود میکند (OcrModelStore) و در filesDir/models نگه میدارد.
        try:
            _cpu_n = os.cpu_count() or 4
        except Exception:
            _cpu_n = 4
        _intra = 4 if _cpu_n > 4 else 2
        try:
            _env_th = int(os.environ.get("MANGA_OCR_THREADS", "0") or 0)
            if _env_th > 0:
                _intra = _env_th
        except Exception:
            pass
        try:
            # v1.14.189 — زبانِ انتخابی به init میرود تا فقط مدلِ همان
            # زبان (اگ نبود) دانلود شود؛ نه همهٔ مدلها با هم
            _ok_init = bool(self._bridge.init(_intra, str(self.lang or "en")))
        except TypeError:
            _ok_init = bool(self._bridge.init(_intra))
        if not _ok_init:
            raise RuntimeError(
                "initِ PaddleOcrBridge ناموفق بود (RapidOCR/APK/دانلودِ مدل؟)")
        # سلف‌تستِ دسترسپذیری: کراپِ ریزِ سفید → باید سطرِ META برگردد؛
        # شکستِ یک‌باره = خطایِ صریح (فالبکی نیست — ML Kit حذف شده).
        try:
            _img = np.full((64, 64, 3), 255, dtype=np.uint8)
            _ok, _buf = cv2.imencode(".png", _img)
            _out = self._bridge.recognizeAuto(
                bytes(_buf.tobytes()), self.lang, 1, 1)
            if not _out or not str(_out[0]).startswith("META"):
                raise RuntimeError(
                    "خروجیِ سلف‌تستِ RapidOCRِ اندروید نامعتبر است: "
                    + str([str(x)[:80] for x in (_out or [])])[:200])
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(
                "سلف‌تستِ پلِ RapidOCRِ اندروید مردود شد: "
                + str(e)[:90])
        print(f"[+] OCR گوشی: RapidOCRِ اندروید آماده | "
              f"RapidOcrAndroidOnnx | det=PP-OCRv6_small "
              f"cls=v2.0_cls rec=PP-OCRv6_medium/{self.lang} "
              f"(دانلودی — v1.14.194) | threads={_intra}")

    # v1.14.190 — آستانهٔ دوئلِ چندزبانه: زیرِ این اطمینان، تلاشِ ko هم
    # میشود (متنِ کره‌ای با recِ پیشفرضِ v6 چرت میزند — charsetِ v6
    # هیچ هانگولی ندارد؛ بنچمارکِ دیکشنری: ۰ از ۱۸۷۰۸)
    _MULTI_CONF_FLOOR = 0.72

    def _call_auto(self, buf, lang):
        """فراخوانیِ پل با زبانِ دلخواه — خطا = None (لاگِ کامل)."""
        try:
            return self._bridge.recognizeAuto(bytes(buf), lang, 1, 1)
        except Exception as e:
            print(f"[!] خطایِ پدلِ اندروید: {str(e)[:140]}")
            return None

    @staticmethod
    def _meta_score(out):
        """(نوعارهایِ سالم، میانگینِ اطمینان) از سطرهایِ META —
        سطرهایِ META/ERR رد؛ confِ پایین (<0.25) هم رد."""
        texts, confs = [], []
        for item in (out or []):
            s = str(item)
            if s.startswith(("META", "ERR")):
                continue
            parts = s.split("|", 4)
            if len(parts) < 5:
                continue
            try:
                conf = float(parts[1])
            except Exception:
                continue
            txt = parts[3].strip()
            if not txt or conf < 0.25:
                continue
            texts.append(txt)
            confs.append(conf)
        return texts, (sum(confs) / len(confs) if confs else 0.0)

    def _ocr_multi(self, buf):
        """چندزبانه (v1.14.190 — دستورِ سازنده: «دکمه چند زبانه خودش
        همه زبان هارو استخراج میزنه کار نمیکنه»): پاسِ اول با recِ
        پیشفرضِ v6_medium (latin/zh/ja را میخواند). اگر ضعیف بود =
        مظنونِ کره‌ای (v6 هانگول ندارد) → یک تلاشِ ko؛ بهترِ دو پاس
        برمیگردد. واریانتِ ko همینجا و فقط با اولین کراپِ کره‌ای دانلود
        میشود («همشو یکجا دانلود نزنه» — به حسابِ زبانِ انتخابی). کراپهای
        بعدیِ همان صفحه از ko شروع میکنند (صفحهها معمولاً تکزبانهاند)."""
        if self._multi_pref == "ko":
            out_a = self._call_auto(buf, "ko")
            ta, ca = self._meta_score(out_a)
            if ta and ca >= self._MULTI_CONF_FLOOR \
                    and not str((out_a or [""])[0]).startswith("ERR"):
                return out_a
            out_b = self._call_auto(buf, "multi")
            tb, cb = self._meta_score(out_b)
            if tb and cb > ca + 0.02 \
                    and not str((out_b or [""])[0]).startswith("ERR"):
                self._multi_pref = None
                return out_b
            if ta:
                return out_a
            self._multi_pref = None
            return out_b if tb else out_a
        out1 = self._call_auto(buf, "multi")
        t1, c1 = self._meta_score(out1)
        if (t1 and c1 >= self._MULTI_CONF_FLOOR) \
                or str((out1 or [""])[0]).startswith("ERR"):
            return out1
        out2 = self._call_auto(buf, "ko")
        t2, c2 = self._meta_score(out2)
        if out2 and t2 and c2 > c1 + 0.02 \
                and not str(out2[0]).startswith("ERR"):
            if not self._multi_ko_logged:
                self._multi_ko_logged = True
                print("[*] چندزبانه: متنِ کره‌ای شناخته شد → recِ کره‌ای "
                      "(مدلِ ~۱۳.۵MB فقط بار اول دانلود شد)")
            self._multi_pref = "ko"
            return out2
        return out1 if t1 else (out2 if t2 else out1)

    def ocr(self, image_bgr, crop_mode: bool = False):
        """هم‌امضایِ RapidOcrMobile — خروجیِ [ [[box,(t,s)],...] ]."""
        if image_bgr is None or getattr(image_bgr, "size", 0) == 0:
            return None
        _t0 = time.time()
        try:
            _ok, _buf = cv2.imencode(
                ".png", np.ascontiguousarray(image_bgr))
            if not _ok:
                return None
            # v1.14.190 — چندزبانه: دوئلِ واریانتِ rec (سمتِ manga)
            if self.lang == "multi":
                out = self._ocr_multi(_buf.tobytes())
            else:
                out = self._bridge.recognizeAuto(
                    bytes(_buf.tobytes()), self.lang, 1, 1)
        except Exception as e:
            print(f"[!] خطایِ پدلِ اندروید: {str(e)[:140]}")
            return None
        if not out:
            _pad_stats_note(_t0, 0)
            return None
        lines = []
        for item in out:
            s = str(item)
            if s.startswith("META"):
                continue
            parts = s.split("|", 4)
            if len(parts) < 5:
                continue
            try:
                conf = float(parts[1])
            except Exception:
                conf = 1.0
            txt = parts[3].strip()
            if not txt or conf < 0.25:
                continue
            try:
                nums = [float(v) for v in parts[2].split(",")]
                if len(nums) != 8:
                    continue
                box = np.asarray(nums, dtype=np.float32).reshape(4, 2)
            except Exception:
                continue
            lines.append([box, (txt, float(conf))])
        _pad_stats_note(_t0, len(lines))
        return [lines] if lines else None


def _mt_boost_crop(crop_bgr: np.ndarray):
    """گامِ «افزایشِ کیفیتِ کراپ»ٔ مرجع: پدِ سفید دورِ کراپ (متنِ چسبیده به
    لبه — مثلِ img6 «You're the real attraction here.» که رویِ لبهٔ چپِ
    صفحه است) + بزرگنماییِ کراپهایِ ریز تا موتورِ استخراج بهتر بخواند.
    خروجی: (کراپِ تقویتشده، pad، scale) برایِ برگرداندنِ مختصات."""
    try:
        h, w = crop_bgr.shape[:2]
    except Exception:
        return crop_bgr, 0, 1.0
    pad = 12
    scale = 1.0
    m = min(h, w)
    if m < 96:
        scale = 3.0
    elif max(h, w) < 480:
        scale = 2.0
    out = cv2.copyMakeBorder(crop_bgr, pad, pad, pad, pad,
                             cv2.BORDER_CONSTANT, value=(255, 255, 255))
    if scale > 1.01:
        out = cv2.resize(out, None, fx=scale, fy=scale,
                         interpolation=cv2.INTER_CUBIC)
    return out, pad, scale


def _mt_map_boxes(lines, pad: float, scale: float):
    """باکسهایِ کراپِ تقویتشده → مختصاتِ کراپِ اصلی."""
    out = []
    if pad == 0 and scale == 1.0:
        return lines
    for box, pair in (lines or []):
        try:
            b = np.asarray(box, dtype=np.float32).reshape(-1, 2)
            b = (b - float(pad)) / float(scale)
            out.append([b.astype(np.float32), pair])
        except Exception:
            continue
    return out


_MT_STATS = {"n": 0, "ms": 0.0, "st1": 0, "st2": 0, "st3": 0}


def _mt_stats_note(t0: float, stage: int) -> None:
    try:
        _MT_STATS["n"] += 1
        _MT_STATS["ms"] += (time.time() - t0) * 1000.0
        _MT_STATS[f"st{stage}"] += 1
        if _MT_STATS["n"] % 20 == 0:
            n = _MT_STATS["n"]
            print(f"[⚡] پدلِ اندروید (نردبانِ مرجع): {n} کراپ | "
                  f"رسمی={_MT_STATS['st1']} | "
                  f"میانگینِ {_MT_STATS['ms'] / max(1, n):.0f}ms")
    except Exception:
        pass


class MtLadderOCR:
    """v1.14.187 — استخراجِ کراپ با RapidOCRِ اندروید (ONNXِ خالص).

    دستورِ سازنده: «ببین چجور به این خوبی استخراج میکنه همونو رو گوشی
    بزار» (RapidOcrAndroidOnnx) → سهگانهٔ RapidOCR (detِ v4 + cls + recِ
    v4ِ واریانتِ زبان) جایگزینِ PP-OCRv6_small شد؛ نردبانِ چندپلهای
    قدیمی (پدلِ ONNXِ medium / رپیدِ small / فلاتر-پدلِ tiny و
    مقایسههایِ پوشش/اطمینان) همچنان حذف است. فقط:
      کراپِ detector-v4-s → تقویت (پد + بزرگنماییِ ریزها) →
      RapidOCR (det+cls+rec رویِ همان کراپ — PP-OCRv4_mobileِ باندل) →
      برگرداندنِ مختصات. هیچ پاسِ تمامصفحهای نیست (بهجز مسیرِ جانبیِ
      قدیمیِ crop_mode=False) و هیچ فالبکی وجود ندارد (خالی = خالی)."""

    # v1.14.187 — تنها روشِ استخراجِ گوشی = RapidOCRِ اندروید
    # (دستورِ سازنده: «ببین چجور به این خوبی استخراج میکنه همونو رو
    # گوشی بزار»). مقدارهایِ کهنهٔ MANGA_MT_MODE
    # (full/fast/rapid/paddle/flutter/mlkit/…) همگی نادیده گرفته میشوند.
    _MT_MODES = ("padandroid",)

    def __init__(self, lang: str, build_onnx=None, build_pad=None):
        # v1.14.184 — build_onnx دیگر «هرگز» صدا زده نمیشود (هیچ موتورِ
        # ONNXِ دیگری رویِ گوشی وجود ندارد؛ پارامتر فقط برایِ سازگاریِ
        # امضایِ قدیمی نگاه داشته شده). فقط build_pad = RapidOCRِ اندروید.
        self._lang = lang
        self._build_onnx = None
        self._build_pad = build_pad    # callable() → RapidOCRِ اندروید (ppocr-sdk)
        self._pad = None
        self._pad_tried = False
        # v1.14.184 — هر مقدارِ کهنه (full/fast/rapid/paddle/flutter/
        # mlkit/…) نادیده گرفته میشود؛ تنها روش = «padandroid».
        self._mode = "padandroid"

    def _engine_pad(self):
        """v1.14.187 — موتورِ «RapidOCRِ اندروید» با کشِ خودش.
        هر خطا/نبودِ پل → None (کراپِ بدونِ موتور = خروجیِ خالی)."""
        if self._pad_tried:
            return self._pad
        self._pad_tried = True
        if self._build_pad is None:
            return None
        try:
            self._pad = self._build_pad()
        except Exception as e:
            print(f"[!] رپیدِ رسمیِ اندروید آماده نشد: {str(e)[:110]}")
            self._pad = None
        return self._pad

    def ocr(self, image_bgr: np.ndarray, crop_mode: bool = False):
        if image_bgr is None or getattr(image_bgr, "size", 0) == 0:
            return None
        _t0 = time.time()
        # مسیرِ تمامصفحه (مسیرهایِ جانبیِ قدیمی) → RapidOCR؛ استخراجِ
        # اصلی فقط رویِ کراپ است (دستورِ مرجع: «نه رو تمام صفحه»).
        if not crop_mode:
            eng0 = self._engine_pad()
            if eng0 is None:
                _mt_stats_note(_t0, 1)
                return None
            try:
                return eng0.ocr(image_bgr)
            except Exception as e:
                print(f"[!] رپیدِ رسمیِ اندروید خطا داد: {str(e)[:110]}")
                _mt_stats_note(_t0, 1)
                return None

        # ── RapidOCR رویِ کراپِ تقویتشده (تنها پله؛ بدونِ پلههایِ ۲/۳) ──
        eng0 = self._engine_pad()
        if eng0 is None:
            _mt_stats_note(_t0, 1)
            return None
        try:
            boosted, pad, scale = _mt_boost_crop(image_bgr)
            r0 = eng0.ocr(boosted)
            lines1 = _mt_map_boxes(r0[0], pad, scale) \
                if r0 and r0[0] else []
        except Exception as e:
            print(f"[!] رپیدِ رسمیِ اندروید خطا داد: {str(e)[:110]}")
            lines1 = []
        _mt_stats_note(_t0, 1)
        return [lines1] if lines1 else None


# ── v1.14.187 — انتخابِ موتورِ OCRِ گوشی ─────────────────────────────
#   تنها روش = «RapidOCRِ اندروید» (سهگانهٔ RapidOcrAndroidOnnx با
#   PP-OCRv4_mobileِ باندل در assetsِ APK) — MANGA_ANDROID_OCR /
#   MANGA_MOBILE_OCR_ENGINE و مقدارهایِ کهنهٔ MANGA_MT_MODE همگی
#   نادیده گرفته میشوند (دستورِ سازنده: «همونو رو گوشی بزار»).
# ── v1.14.176 — «آزمایشگاهِ سرعتِ استخراج» ────────────────────────────
# تنظیمها از پنلِ اپ میآیند → bridge آنها را به speed_lab_env() میدهد →
# envهایِ مانده ست/پاک میشوند. پیشفرضِ هر کلید = رفتارِ همین نسخه.

# v1.14.187 — RapidOCR رویِ CPU اجرا میشود؛ EPهایِ ONNXِ قدیمی
# (nnapi/xnnpack/cpu) دیگر معنا ندارند. روشِ یگانه = padandroid.

# اسمِ فارسیِ هر روش برایِ لاگها (کلیدِ انگلیسی هم کنارش میآید تا لاگ
# قابلِ جستجو بماند)
_MT_MODE_FA = {
    "padandroid": "رپیدِ رسمیِ اندروید",
}

# v1.14.181 — پاکسازیِ یکبارِ مصرفِ مدلهایِ ONNXِ بازنده از گوشی.
# دستورِ سازنده: «بقیش حذف کن تو گوشی استفاده نکنه». v1.14.183 —
# ML Kit هم کلاً حذف شد (دستور: «ml kit حذف کن خوب نیست»). v1.14.184 —
# مدلهایِ medium هم بازنده شدند. v1.14.187 — استخراج = RapidOCRِ
# اندروید (RapidOcrAndroidOnnx) با سهگانهٔ PP-OCRv4_mobileِ باندلشده
# در APK (هیچ مدلِ OCRی دانلود نمیشود).
# سه مجموعهٔ مدلِ بازنده از پوشهٔ rapidocr_modelsِ گوشی حذف میشوند:
#   رپید (small): PP-OCRv6_det_small[.int8]/rec_small + cls + ja/ko
#   پدل (medium): PP-OCRv6_medium_det/rec + korean v5 + ch v4
#   فلاتر-پدل (tiny): PP-OCRv6_tiny_det/rec + dictِ tiny
# فهرستِ نامها از خودِ _RAPIDOCR_FILES میآید (بدونِ تغییرِ آن dict —
# PC از همان helper برایِ مجموعهٔ سبکِ خودش استفاده میکند و بیت‌به‌بیت
# دستنخورده میماند) + نوعِ int8ِ detِ رپید.
_MT_PURGE_EXTRA = ("PP-OCRv6_det_small.int8.onnx",)
_PURGE_MARKER = ".onnx_loser_models_purged_184"


def _purge_loser_onnx_models() -> str:
    """v1.14.181 — حذفِ یکبارِ مدلهایِ ONNXِ بازنده از گوشی.

    فقط اندروید (گیتِ MANGA_PURGE_ONNX_MODELS) — PC بیت‌به‌بیت
    دستنخورده (پوشهٔ هم‌نام رویِ PC مدلهایِ موتورِ خودش را دارد و
    rapidocr از همان میخواند). یکبارمصرف با فایلِ مارکر: اگر مسیرِ
    فالبکِ ONNX (مثلاً APKِ خیلی قدیمی بدونِ پلِ ML Kit) بعداً مدلی
    بخواهد، همان موقع دانلود میشود و پاکِ دوباره نمیشود. خروجی = خطِ
    لاگِ «چه چیزی آزاد شد» یا ""."""
    try:
        if not _android_gate("MANGA_PURGE_ONNX_MODELS"):
            return ""
        _mdir = os.path.join(
            os.environ.get("MANGA_FILES_DIR") or os.getcwd(),
            "rapidocr_models")
        if not os.path.isdir(_mdir):
            return ""
        _mk = os.path.join(_mdir, _PURGE_MARKER)
        if os.path.isfile(_mk):
            return ""
        _names = set(_RAPIDOCR_FILES) | set(_MT_PURGE_EXTRA)
        # v1.14.187 — موتورِ گوشی = RapidOCR با سهگانهٔ PP-OCRv4_mobileِ
        # باندل در APK — هیچ فایلِ مدلی در rapidocr_models نگه داشته نمیشود.
        _keep = ()
        _freed = 0
        _n = 0
        for _fn in sorted(os.listdir(_mdir)):
            _fp = os.path.join(_mdir, _fn)
            if not os.path.isfile(_fp):
                continue
            if _fn in _keep:
                continue
            if _fn in _names or _fn.endswith(".part") \
                    or _fn.endswith(".part.url"):
                try:
                    _freed += os.path.getsize(_fp)
                    os.remove(_fp)
                    _n += 1
                except Exception:
                    pass
        try:
            with open(_mk, "w", encoding="utf-8") as _f:
                _f.write("purged at %s (APP_VER %s)\n"
                         % (time.strftime("%Y-%m-%d %H:%M"), APP_VER))
        except Exception:
            pass
        if _n:
            print("[🧹] v1.14.181 — %d فایلِ مدلِ بازنده (%s) از گوشی حذف شد"
                  % (_n, _fmt_mb(_freed)))
            return ("مدلهایِ بازنده حذف شد: %d فایل / %s آزاد شد — "
                    "روشِ فعالِ v1.14.187 = RapidOCRِ اندروید"
                    % (_n, _fmt_mb(_freed)))
        return ""
    except Exception:
        return ""


def speed_lab_env(p: dict) -> str:
    """v1.14.187 — روشِ استخراجِ گوشی = RapidOCRِ اندروید
    (RapidOcrAndroidOnnx با سهگانهٔ PP-OCRv4_mobileِ باندل).

    تاریخچه: 1.14.176 سوییچهایِ پنل؛ 1.14.178 دکمهٔ «تستِ سرعت»؛
    1.14.181 forceِ برنده + پاکسازیِ مدلهایِ بازنده؛ 1.14.182/183 پدلِ
    رسمیِ اندروید و حذفِ ML Kit؛ 1.14.184 — تنها روش = SDKِ رسمی؛
    1.14.187 — دستورِ سازنده: «متن هاش اشتباهه بعضی وقتا … همونو رو
    گوشی بزار» → تنها روش = RapidOCRِ اندروید؛ پارامترِ p خوانده نمیشود
    (سازگاریِ امضا با bridge)."""
    try:
        # کلیدهایِ قدیمیِ سوییچها هرگز از این نسخه ست نمیشوند — پاککاری
        # برایِ اینکه envِ ماندهٔ پروسههایِ قدیمی اثر نگذارد.
        for _k in ("MANGA_OCR_THREADS", "MANGA_XNN_THREADS",
                   "MANGA_CROP_DET_CAP", "MANGA_CROP_ENH_SCALE"):
            os.environ.pop(_k, None)

        # v1.14.187 — RapidOCR رویِ CPU اجرا میشود؛ هر EPِ کهنه پاک
        # میشود و روشِ فعال همیشه «padandroid» است.
        os.environ.pop("MANGA_MOBILE_OCR_EP", None)
        _w = speed_test_load()
        _lad = "padandroid"
        os.environ["MANGA_MT_MODE"] = "padandroid"
        _ms_l = ""
        try:
            _lm = (_w or {}).get("ladder_ms") or {}
            if _lm.get(_lad):
                _ms_l = " (%.0fms/کراپ — تستِ %s)" % (float(_lm[_lad]),
                                                    str((_w or {}).get("ts") or "?"))
        except Exception:
            _ms_l = ""

        # v1.14.181 — پاکسازیِ یکبارِ مدلهایِ ONNXِ بازنده از گوشی
        _purge = _purge_loser_onnx_models()

        # سنجههایِ سرعت = مالِ «این اجرا» — بینِ کارها ریست
        for _k in ("n", "ms", "st1", "st2", "st3"):
            _MT_STATS[_k] = 0 if _k != "ms" else 0.0
        for _k in ("ms", "n", "lines"):
            _PAD_STATS[_k] = 0 if _k != "ms" else 0.0

        if _purge:
            return ("[⚡] روشِ استخراج: RapidOCRِ اندروید — "
                    "PP-OCRv6ِ دانلودی (%s)%s | v%s: %s"
                    % (_MT_MODE_FA.get(_lad, _lad), _ms_l,
                       APP_VER, _purge))
        return ("[⚡] روشِ استخراج: RapidOCRِ اندروید — "
                "PP-OCRv6ِ دانلودی (det=small + rec=MEDIUM — "
                "بدونِ باندل؛ اگ نباشد دانلود میشود — "
                "v%s)%s"
                % (APP_VER, _ms_l))
    except Exception:
        return ""


# ── v1.14.178 — «تستِ سرعت»: یک دکمه، همهٔ حالتها ───────────────────
# دستورِ سازنده پس از دو باگِ زنجیرهٔ پنل (176/177): «حذفش کن — یک
# دکمه بذار، فعال کردم همه حالت تست کنه، تایم بگیره یک دقیقه
# هرکدومشون، بعد ببینم کدومش سریعه». پس: نه سوییچ، نه انتقالِ تنظیم
# از پنل — خودِ موتور همهٔ حالتها را رویِ کراپهایِ واقعیِ همین تصویر
# اندازه میگیرد (هر حالت یک پنجرهٔ ۶۰ ثانیهای) و برنده را در
# speed_test.json ذخیره میکند؛ speed_lab_env از همان فایل هر کار را
# تنظیم میکند. پروبِ ۱۸۰ ثانیهایِ epprobe هم عملاً بازنشسته میشود:
# پنجرهٔ واقعیِ ۶۰ ثانیهای خودش سنجهٔ سالم/کرش را میدهد.

_SPEED_TEST_FILE = "speed_test.json"


def _speed_test_path() -> str:
    return os.path.join(os.environ.get("MANGA_FILES_DIR") or os.getcwd(),
                        _SPEED_TEST_FILE)


def speed_test_load():
    """نتیجهٔ ذخیرهشدهٔ «تستِ سرعت» — dict یا None."""
    try:
        with open(_speed_test_path(), "r", encoding="utf-8") as _f:
            _d = json.loads(_f.read() or "{}")
        if isinstance(_d, dict) and str(_d.get("ladder") or ""):
            return _d
    except Exception:
        pass
    return None


def _speed_test_save(d: dict) -> None:
    try:
        with open(_speed_test_path(), "w", encoding="utf-8") as _f:
            json.dump(d, _f, ensure_ascii=False, indent=2)
    except Exception as _e:
        print(f"[!] ذخیرهٔ نتیجهٔ «تستِ سرعت» ناموفق: {str(_e)[:120]}")


def _speed_test_pool(page, det0, cap: int = 24):
    """کراپهایِ واقعیِ متن از پاسِ تشخیصِ کاملصفحه — بزرگترینها تا
    سقفِ cap. خروجی = لیستِ آرایههایِ BGR."""
    try:
        _boxes = []
        for _item in (det0 or []):
            try:
                if not (isinstance(_item, (list, tuple)) and _item):
                    continue
                _b = np.asarray(_item[0], dtype=np.float32).reshape(-1, 2)
                _x, _y, _w, _h = cv2.boundingRect(_b.astype(np.int32))
                if _w < 8 or _h < 8:
                    continue
                _boxes.append((_w * _h, _x, _y, _w, _h))
            except Exception:
                continue
        if not _boxes:
            return []
        _boxes.sort(key=lambda t: -t[0])
        _H, _W = page.shape[:2]
        _out = []
        for _a, _x, _y, _w, _h in _boxes[:cap]:
            _x0, _y0 = max(0, _x), max(0, _y)
            _x1, _y1 = min(_W, _x + _w), min(_H, _y + _h)
            if _x1 - _x0 < 8 or _y1 - _y0 < 8:
                continue
            _out.append(page[_y0:_y1, _x0:_x1].copy())
        return _out
    except Exception:
        return []


def _speed_test_tiles(page, cap: int = 24):
    """v1.14.179 — کراپهایِ جایگزین: وقتی تشخیصِ تمامصفحه چیزی نداد
    (لاگِ 178: «در تصویر متنِ خواندنی پیدا نشد» → کلِ تست قطع شد و فقط
    یک حالت «تست» شده بود)، صفحه به کاشیهایِ واقعی (~512px) بریده
    میشود تا تستِ سرعت هیچوقت بنبست پیدا نکند و همهٔ روشها همیشه
    اندازهگیری شوند. هر کاشی پیکسلِ واقعیِ همان صفحه است — هدفِ این
    آزمون فقط سنجشِ سرعت است، نه دقت."""
    try:
        _H, _W = page.shape[:2]
        if not _H or not _W:
            return []
        _side = 512.0
        _ny = max(1, min(6, int(round(_H / _side)) or 1))
        _nx = max(1, min(6, int(round(_W / _side)) or 1))
        while _nx * _ny > cap:
            if _nx >= _ny and _nx > 1:
                _nx -= 1
            elif _ny > 1:
                _ny -= 1
            else:
                break
        _out = []
        for _iy in range(_ny):
            for _ix in range(_nx):
                _y0, _y1 = (_H * _iy) // _ny, (_H * (_iy + 1)) // _ny
                _x0, _x1 = (_W * _ix) // _nx, (_W * (_ix + 1)) // _nx
                if _y1 - _y0 < 64 or _x1 - _x0 < 64:
                    continue
                _out.append(page[_y0:_y1, _x0:_x1].copy())
        return _out[:cap]
    except Exception:
        return []


def _speed_test_window(runner, pool, per_mode, should_stop=None):
    """یک پنجرهٔ زمانی رویِ pool: کراپِ اول = گرمکردنِ مدلها (بیرونِ
    سنجه)؛ بعد تا پرشدنِ پنجره کراپها لوپ میشود. خروجی =
    (تعداد، مجموعِ ثانیهٔ خالص، خطا، متوقفشده)."""
    _n, _tsum, _err = 0, 0.0, None
    try:
        runner(pool[0])  # گرمکردن — ساختنِ سشن/مدل در سنجه نمیآید
    except Exception as _e:
        return 0, 0.0, str(_e), False
    _t0 = time.time()
    _stopped = False
    while (time.time() - _t0) < per_mode:
        for _crop in pool:
            if should_stop is not None and should_stop():
                _stopped = True
                break
            _t1 = time.time()
            try:
                runner(_crop)
            except Exception as _e:
                _err = str(_e)
                break
            _tsum += time.time() - _t1
            _n += 1
            if (time.time() - _t0) >= per_mode:
                break
        if _err or _stopped:
            break
    return _n, _tsum, _err, _stopped


def speed_test_run(src, langs=("en",), per_mode=60.0, log=print,
                   should_stop=None, backend=None):
    """«تستِ سرعتِ استخراج» — یک پنجره رویِ روشِ یگانهٔ v1.14.187.

    ۱) تصویر ورودی باز میشود؛ RapidOCRِ اندروید یک پاسِ تشخیصِ
       کاملصفحه میزند و کراپهایِ واقعیِ متن را میدهد (تا ۲۴ کراپ).
       اگر تشخیص چیزی نداد — صفحه به کاشیهایِ واقعیِ (~۵۱۲px) بریده
       میشود؛ تست هیچوقت بنبست پیدا نمیکند (v1.14.179).
    ۲) یک پنجرهٔ روش (padandroid = RapidOCRِ اندروید با
       PP-OCRv4_mobileِ باندل) رویِ همان کراپها؛ موتورِ واقعی
       اندازهگیری میشود. پنجرههایِ روشها/شتاب‌دهندههایِ قدیمی
       (full/fast/rapid/paddle/flutter + cpu/xnnpack/nnapi) حذف شدند —
       فقط یک روش وجود دارد (دستورِ سازنده: «همونو رو گوشی بزار»).
    ۳) نتیجه در speed_test.json ذخیره میشود (speed_lab_env) — دیگر
       هیچ انتخابی در کار نیست؛ فقط برایِ لاگِ سازنده.
    خروجی: dictِ نتیجه (یا None با پیامِ لاگ). backend فقط برایِ تست
    (تزریقِ فیک) — پیشفرض = RapidOCRBackend واقعی."""
    try:
        per_mode = max(5.0, float(per_mode or 60.0))
    except Exception:
        per_mode = 60.0
    lang = (langs[0] if langs else "en") or "en"
    _modes = tuple(MtLadderOCR._MT_MODES)
    log("[⚡] تستِ سرعتِ استخراج: %d روش (%s) × %d ثانیه"
        % (len(_modes),
           " + ".join(_MT_MODE_FA.get(_m, _m) for _m in _modes),
           int(per_mode)))
    log("[⚡] در این حالت ترجمه انجام نمیشود — فقط استخراجِ متن "
        "اندازهگیری میشود؛ لطفاً برنامه را باز نگه دار…")
    _t_all = time.time()
    try:
        page = MangaTranslator._imread_any(src)
    except Exception as _e:
        log("[!] تصویر ورودی باز نشد: %s" % str(_e)[:140])
        return None
    if page is None or getattr(page, "size", 0) == 0:
        log("[!] تصویر ورودی باز نشد (%s)" % os.path.basename(str(src or "")))
        return None
    try:
        be = backend if backend is not None else RapidOCRBackend(lang=lang)
    except Exception as _e:
        log("[!] موتورِ OCR ساخته نشد: %s" % str(_e)[:140])
        return None
    _lad0 = getattr(be, "_mobile", None)
    if not isinstance(_lad0, MtLadderOCR):
        log("[!] «تستِ سرعت» رویِ نردبانِ مرجع کار میکند — این دستگاه "
            "نردبان ندارد (PC/موتورِ دیگر). از اپِ گوشی تست کن.")
        return None

    _prev = speed_test_load() or {}
    _nnapi_pending = bool(_prev.get("nnapi_pending"))

    # v1.14.187 — تنها موتورِ اندازهگیری = RapidOCRِ اندروید
    try:
        _padbe = be._build_paddle_android(lang)
    except Exception:
        _padbe = None

    # ── استخرِ کراپها: یک پاسِ تشخیصِ کاملصفحه با RapidOCR ──
    log("[⚡] استخرِ کراپهایِ واقعی از تصویر…")
    _res0 = None
    if _padbe is not None:
        try:
            _res0 = _padbe.ocr(page, crop_mode=False)
        except Exception as _e:
            _res0 = None
            log("[!] تشخیصِ تمامصفحه خطا داد: %s" % str(_e)[:140])
    pool = _speed_test_pool(page, _res0)
    if not pool:
        # v1.14.179 — پایانِ بنبستِ ۱۷۸: بهجایِ قطعِ کلِ تست (لاگ:
        # «در تصویر متنِ خواندنی پیدا نشد» → فقط یک حالت «تست» شده بود)
        # صفحه به کاشیهایِ واقعیِ خودش بریده میشود؛ همهٔ پنجرهها همیشه
        # پیموده میشوند.
        pool = _speed_test_tiles(page)
        log("[⚡] تشخیصِ تمامصفحه چیزی ندید — با %d کاشیِ واقعیِ خودِ "
            "صفحه ادامه میدهیم؛ همهٔ روشها اندازهگیری میشوند." % len(pool))
    if not pool:
        log("[!] تصویر خیلی ریز/خالی است — یک صفحهٔ بزرگتر امتحان کن.")
        return None
    log("[⚡] %d کراپِ آماده — پنجرهها شروع میشوند…" % len(pool))

    _res = {"app": APP_VER,
            "ts": time.strftime("%Y-%m-%d %H:%M"),
            "per_mode": int(per_mode), "crops": len(pool),
            "ladder": str(_prev.get("ladder") or "full"),
            "ep": str(_prev.get("ep") or "auto"),
            "ladder_ms": {}, "ep_ms": {},
            "ladder_n": {}, "ep_n": {},
            "nnapi_pending": False}
    _total = len(_modes)
    _wi = 0

    # ── پنجرههایِ روشِ استخراج ──
    for _mode in _modes:
        _wi += 1
        _need_ok = {"padandroid": _padbe is not None}[_mode]
        if not _need_ok:
            _res["ladder_ms"][_mode] = None
            log("[⚡] (%d/%d) روشِ %s (%s) → رد شد (موتورش رویِ این دستگاه آماده نیست)"
                % (_wi, _total, _MT_MODE_FA.get(_mode, _mode), _mode))
            continue
        os.environ["MANGA_MT_MODE"] = _mode
        try:
            _lad = MtLadderOCR(lang, build_pad=lambda: _padbe)
        except Exception as _e:
            _res["ladder_ms"][_mode] = None
            log("[⚡] (%d/%d) روشِ %s (%s) → نردبان ساخته نشد: %s"
                % (_wi, _total, _MT_MODE_FA.get(_mode, _mode), _mode,
                   str(_e)[:100]))
            continue
        _n, _ts, _err, _stp = _speed_test_window(
            lambda c, _l=_lad: _l.ocr(c, crop_mode=True),
            pool, per_mode, should_stop=should_stop)
        _ms = (_ts * 1000.0 / _n) if _n else None
        _res["ladder_ms"][_mode] = _ms
        _res["ladder_n"][_mode] = _n
        if _err:
            log("[⚡] (%d/%d) روشِ %s (%s) → خطا: %s"
                % (_wi, _total, _MT_MODE_FA.get(_mode, _mode), _mode,
                   str(_err)[:100]))
        elif _stp:
            log("[⚡] (%d/%d) روشِ %s (%s) → متوقف شد (%d کراپ)"
                % (_wi, _total, _MT_MODE_FA.get(_mode, _mode), _mode, _n))
            _speed_test_save(_res)
            return _res
        else:
            log("[⚡] (%d/%d) روشِ %s (%s) → %d کراپ | میانگینِ %.0fms/کراپ"
                % (_wi, _total, _MT_MODE_FA.get(_mode, _mode), _mode,
                   _n, _ms))
        _speed_test_save(_res)  # بعد از هر پنجره ذخیره — کرش = از دست نمیرود

    # ── v1.14.187 — پنجرههایِ شتاب‌دهنده حذف شدند: RapidOCR رویِ CPU ──

    # ── برندهها + جدولها ──
    _ok_l = {k: v for k, v in _res["ladder_ms"].items() if v}
    _ok_e = {k: v for k, v in _res["ep_ms"].items() if v}
    if not _ok_l and not _ok_e:
        log("[!] هیچ پنجرهٔ سالمی تمام نشد — نتیجه‌ای ذخیره نشد.")
        return None
    _best_l = min(_ok_l, key=_ok_l.get) if _ok_l else \
        str(_prev.get("ladder") or "full")
    _best_e = min(_ok_e, key=_ok_e.get) if _ok_e else \
        str(_prev.get("ep") or "auto")
    _res["ladder"], _res["ep"] = _best_l, _best_e
    _res["seconds"] = int(time.time() - _t_all)
    _speed_test_save(_res)
    _tbl = " | ".join("%s(%s)=%.0fms" % (_MT_MODE_FA.get(k, k), k, v)
                      for k, v in sorted(_ok_l.items(), key=lambda kv: kv[1]))
    log("[⚡] جدولِ روشها (سریع → کند): %s" % (_tbl or "—"))
    log("[⚡] شتاب‌دهندهٔ جداگانه ندارد — RapidOCR رویِ CPU با "
        "EngineConfig.numThreads اجرا میشود (v1.14.184).")
    log("[⚡] برنده: روشِ %s (%s؛ %s) → ذخیره شد (v1.14.184: تنها روش — "
        "شتاب‌دهندهٔ جداگانه ندارد)."
        % (_MT_MODE_FA.get(_best_l, _best_l), _best_l,
           ("%.0fms/کراپ" % _ok_l[_best_l]) if _best_l in _ok_l else "—"))
    try:
        log("[⚡] کلِ تست: %d دقیقه و %d ثانیه"
            % (_res["seconds"] // 60, _res["seconds"] % 60))
    except Exception:
        pass
    return _res


def _mt_speed_report() -> str:
    """گزارشِ سرعتِ «این اجرا» — bridge بعد از پایانِ هر کار لاگش میکند
    تا سازنده بتونه بینِ حالتهایِ آزمایشگاه مقایسه کنه."""
    try:
        _n = int(_MT_STATS.get("n") or 0)
        if _n <= 0:
            return ""
        _ms = float(_MT_STATS.get("ms") or 0.0)
        _out = ("[🧪] گزارشِ سرعتِ استخراج: %d کراپ | میانگینِ %.0fms | "
                "رسمی=%d"
                % (_n, _ms / max(1, _n), int(_MT_STATS.get("st1") or 0)))
        try:
            _pn = int(_PAD_STATS.get("n") or 0)
            if _pn > 0:
                _out += (" | رپیدِ رسمیِ تنهایی: میانگینِ %.0fms"
                         % (float(_PAD_STATS.get("ms") or 0.0) / _pn))
        except Exception:
            pass
        try:
            _lad = str(os.environ.get("MANGA_MT_MODE", "") or "").strip().lower()
            _out += " | روش=%s" % (_lad if _lad else "padandroid")
        except Exception:
            pass
        return _out
    except Exception:
        return ""


_RAPIDOCR_RECOVER_LOCK = threading.Lock()


class RapidOCRBackend:

    def __init__(self, lang: str = "en", prefer_gpu: Optional[bool] = None):
        self.lang = lang
        self._new_api = False
        self._mobile = None
        # v1.14.154 — گاردِ CJK برایِ زبانِ لاتین (اندروید؛ PC بدونِ گیت
        # همیشه خاموش — رفتارِ PC بیت‌به‌بیت)
        try:
            self._cjk_guard = _android_gate("MANGA_CJK_GUARD") and \
                str(lang).lower() in ("en", "latin", "english")
        except Exception:
            self._cjk_guard = False
        # v1.14.123 — اندروید: موتورِ PP-OCRv6 ONNX (عینِ PC/مرجع) از
        # rapidocr_mobile (بدونِ پکیجِ rapidocr/pyclipper/shapely).
        # زمینه: دیکدِ اپِ مرجع نشان داد مرجع رویِ گوشی هم همین پایپلاینِ
        # ONNX را اجرا میکند (RunRapidOcrPipelineOnCrop + _ppOcrDict +
        # ppocrv6_dict.txt) و دقیق/سریع استخراج میزند. درخواستِ کاربر:
        # «استخراجِ مالِ پی‌سی لینوکس هستو رو گوشی اوکی کرد».
        if _IS_ANDROID:
            self._init_mobile_engine(lang)
            return
        # v1.14.96-speed — prefer_gpu از MangaTranslator.use_gpu می‌آید
        # (همان تصمیمِ auto/--cpuِ OCR). None = رفتارِ قبل (فقط CPU).
        self._prefer_gpu = prefer_gpu
        try:
            # v1.14.29: rapidocr فقط همین‌جا (وقتی موتور ONNX واقعاً لازم است) نصب می‌شود
            if not _ensure_rapidocr_pkg():
                raise ImportError("rapidocr نصب نیست و نصب خودکار ناموفق بود")
            from rapidocr import RapidOCR as NewRapidOCR
            # v1.14.95 — سکوتِ لاگِ RapidOCR: هر کراپِ خالی یک خطِ
            # [WARNING] «The text detection result is empty» می‌نوشت و
            # کنسول/وب را پر می‌کرد (شکایتِ «لاگِ اضافه» کاربر).
            # نکته: موتور در init خودش level را INFO می‌کند → setLevel
            # کافی نیست؛ «فیلتر» رویِ همان لاگر ماندگار است.
            try:
                import logging as _lg

                class _QuietRapidOCR(_lg.Filter):
                    def filter(self, rec):
                        return rec.levelno >= _lg.ERROR

                for _ln in ("RapidOCR", "rapidocr"):
                    _lg.getLogger(_ln).addFilter(_QuietRapidOCR())
                    _lg.getLogger(_ln).propagate = False
            except Exception:
                pass
            _low = str(lang).lower()
            _rec_params = None
            if _low in ("korean", "ko"):
                try:
                    from rapidocr import OCRVersion as _OV, ModelType as _MT, LangRec as _LR
                    _rec_params = {
                        "Rec.lang_type": getattr(_LR, "KOREAN", _LR.KOREAN),
                        "Rec.ocr_version": _OV.PPOCRV5,
                        "Rec.model_type": _MT.MOBILE,
                    }
                except Exception as e:
                    print(f"[!] پیکربندی مدل کره‌ای RapidOCR نشد ({e}) → مدل پیش‌فرض")
            elif _low in ("japan", "ja", "japanese"):
                try:
                    from rapidocr import OCRVersion as _OV, ModelType as _MT, LangRec as _LR
                    _japan = getattr(_LR, "JAPAN", None)
                    if _japan is not None:
                        _rec_params = {
                            "Rec.lang_type": _japan,
                            "Rec.ocr_version": _OV.PPOCRV4,
                            "Rec.model_type": _MT.MOBILE,
                        }
                    else:
                        print("[!] LangRec.JAPAN در rapidocr نیست → مدل پیش‌فرض")
                except Exception as e:
                    print(f"[!] پیکربندی مدل ژاپنی RapidOCR نشد ({e}) → مدل پیش‌فرض")
            import os as _os
            _mdir = _os.path.join(
                _os.environ.get("MANGA_FILES_DIR") or _os.getcwd(),
                "rapidocr_models")
            try:
                _os.makedirs(_mdir, exist_ok=True)
            except Exception:
                _mdir = None
            _base = {"Global.model_root_dir": _mdir} if _mdir else {}
            if _mdir:
                try:
                    # v1.14.29: فقط مدل‌های همین زبان دانلود می‌شود — نه همهٔ زبان‌ها
                    # (det مشترک است؛ rec مخصوص زبان؛ cls دیگر استفاده نمی‌شود)
                    # v1.14.152 — مجموعهٔ مرجع با helperِ مشترک
                    _det_n52, _rec_n52 = _rapidocr_model_pair(
                        lang, small=_pc_ocr_small())  # v1.14.188 — PC = ستِ medium (MANGA_OCR_SMALL/امولاتور = سبک)
                    _ensure_rapidocr_models(_mdir,
                                            files=[_det_n52, _rec_n52])
                except Exception as _e:
                    print(f"[!] پیش‌دانلود مدل‌ها ناموفق: {_e}")
            # v1.14.96-speed — مدل‌هایِ det/rec (و cls اگر فایلش موجود باشد)
            # «صریحاً» از فایل‌هایِ دانلودشدهٔ ریلیزِ «models» (GitHub) به
            # موتور داده می‌شوند: rapidocr دیگر خودش دانلود/بررسیِ SHA از
            # modelscope انجام نمی‌دهد و دقیقاً همان فایلِ کش‌شده (که از
            # ریلیزِ models آمده) استفاده می‌شود. فایل نبود؟ → همان رفتارِ
            # قبل: rapidocr خودش برمی‌دارد (model_root_dir).
            _gpu_flags69 = {}
            if _mdir:
                try:
                    # v1.14.152 — مسیرِ صریحِ مدلها از helperِ مجموعهٔ مرجع
                    _det_n52, _rec_n52 = _rapidocr_model_pair(
                        lang, small=_pc_ocr_small())  # v1.14.188 — PC = ستِ medium (MANGA_OCR_SMALL/امولاتور = سبک)
                    for _sec69, _fn69 in (
                            ("Det", _det_n52),
                            ("Rec", _rec_n52),
                            ("Cls", "ch_ppocr_mobile_v2.0_cls_mobile.onnx")):
                        _mp69 = _os.path.join(_mdir, _fn69)
                        if _os.path.isfile(_mp69) \
                                and _os.path.getsize(_mp69) > 100_000:
                            _base[f"{_sec69}.model_path"] = _mp69
                    # v1.14.152 — مدلهایِ رسمیِ PaddlePaddle (medium/korean)
                    # dict را داخلِ metadata ندارند → rapidocr بدونِ
                    # rec_keys_path دنبالِ dict_url میگردد و «Missing key
                    # dict_url» میدهد. فایلِ dict محلیِ همان مدل را میدهیم
                    # (ch v4 و japan خودشان dictِ داخلی دارند — دست نمیخورند).
                    if _rec_n52 in ("PP-OCRv6_medium_rec_onnx.onnx",
                                    "PP-OCRv5_korean_rec.onnx"):
                        _keys52 = ("ppocrv6_chars.txt"
                                   if _rec_n52.startswith("PP-OCRv6")
                                   else "korean_chars.txt")
                        try:
                            _ensure_rapidocr_models(_mdir, files=[_keys52])
                        except Exception:
                            pass
                        _kp52 = _os.path.join(_mdir, _keys52)
                        if _os.path.isfile(_kp52) \
                                and _os.path.getsize(_kp52) > 100:
                            _base["Rec.rec_keys_path"] = _kp52
                except Exception as _e69:
                    print(f"[!] مسیرِ صریحِ مدلِ OCR نشد ({_e69}) → auto")
            # v1.14.96-speed — EPِ سشن‌هایِ OCR هم از انتخابگرِ مرکزیِ
            # _best_providers_for: اگر CUDA/Dml/CoreML واقعاً موجود است و
            # --cpu نزده، rapidocr هم رویِ همان EP می‌رود (همان مدلِ
            # PP-OCRv6؛ فقط سریع‌تر). در بیلدِ CPU-only هیچ فرقی با قبل
            # ندارد و ساختِ سشنِ GPU شکست بخورد → بدونِ GPU دوباره ساخته
            # می‌شود (فال‌بکِ امن).
            try:
                _want69 = bool(prefer_gpu) and (_ORT_CUDA_OK is not False)
                _ocr_head69 = (_best_providers_for("ocr", prefer_gpu=_want69)
                               or ["CPUExecutionProvider"])[0]
                # v1.14.230 — پروبِ «واقعیِ» CUDA قبل از سپردنِ موتورِ OCR
                # به rapidocr: «CUDA در get_available_providers» فقط یعنی
                # بیلدِ GPU نصب است — نه اینکه DLLهایِ cudnn/cublas لود
                # شوند. سشنِ آزمایشی رویِ همان مدلِ det ساخته میشود؛ اگر
                # EPِ فعالِ سشن CUDA نبود، use_cuda هرگز تنظیم نمیشود و
                # کاربر پیامِ روشن میبیند (گزارشِ سازنده: «چک میزنم
                # گرافیک صفر درصده»). فایلِ مدلِ det همین بالا دانلود
                # شده است (_ensure_rapidocr_models).
                _ep_active230 = ""
                if _ocr_head69 == "CUDAExecutionProvider":
                    _cuda_ok230 = False
                    try:
                        _detn230 = ""
                        try:
                            _detn230 = _det_n52
                        except Exception:
                            _detn230 = ""
                        _probe_p230 = _os.path.join(_mdir or "", _detn230 or "")
                        if _os.path.isfile(_probe_p230):
                            _ps230 = ort.InferenceSession(
                                _probe_p230,
                                providers=["CUDAExecutionProvider",
                                           "CPUExecutionProvider"])
                            _cuda_ok230 = (
                                _ps230.get_providers()[0]
                                == "CUDAExecutionProvider")
                            _ep_active230 = ",".join(_ps230.get_providers())
                    except Exception as _pe230:
                        _cuda_ok230 = False
                        _ep_active230 = str(_pe230)[:90]
                    if _cuda_ok230:
                        _gpu_flags69["EngineConfig.onnxruntime.use_cuda"] = True
                        # v1.14.96-speed (SRV-G phase2) — CUDA EP options برایِ
                        # سشن‌هایِ OCR هم (فقط وقتی مسیرِ GPU فعال است تا فال‌بکِ
                        # CPU را آلوده نکند؛ در فال‌بک حذف می‌شود)
                        _gpu_flags69["EngineConfig.onnxruntime.cuda_ep_cfg.cudnn_conv_use_max_workspace"] = "1"
                        # v1.14.98-speed (SRV-H3) — OCR هم MANGA_CUDNN_ALGO را
                        # رعایت کند (سشن‌هایِ det/rec رویِ CUDA بدونِ
                        # EXHAUSTIVE re-search وقتی heuristic خواسته شده)
                        _algo_h3 = _cudnn_algo_search()
                        if _algo_h3:
                            _gpu_flags69["EngineConfig.onnxruntime.cuda_ep_cfg.cudnn_conv_algo_search"] = _algo_h3
                    else:
                        print(f"[!] CUDA در عمل لود نشد ({_ep_active230 or 'بدونِ جزئیات'}) "
                              f"→ OCR روی CPU. راه‌حل: pip install "
                              f"'onnxruntime-gpu[cuda,cudnn]==1.26.0'")
                        _ocr_head69 = "CPUExecutionProvider"
                if _ocr_head69 == "DmlExecutionProvider":
                    # v1.14.233 — پروبِ واقعیِ DML رویِ «هر دو» مدلِ det و
                    # rec + یک اینفرنسِ واقعی (لاگِ 232: سشنها ساخته شدند
                    # ولی اولین Run با 887A0006 مرد). همهٔ فراخوانیهایِ
                    # موتور هم از این پس زیرِ قفلِ سراسریِ DML میروند
                    # (مستندات: DML اجرایِ موازی ندارد).
                    _dml_ok233 = False
                    try:
                        _probe233 = []
                        for _nm233 in (_det_n52, _rec_n52):
                            try:
                                _p233 = _os.path.join(_mdir or "",
                                                      str(_nm233 or ""))
                            except Exception:
                                _p233 = ""
                            if _os.path.isfile(_p233) \
                                    and _os.path.getsize(_p233) > 100_000:
                                _probe233.append(_p233)
                        _dml_ok233 = bool(_probe233) and all(
                            _dml_probe_model(_p233) for _p233 in _probe233)
                    except Exception:
                        _dml_ok233 = False
                    if _dml_ok233:
                        _gpu_flags69["EngineConfig.onnxruntime.use_dml"] = True
                        self._dml_locked233 = True
                    else:
                        print("[!] DirectML در عمل لود نشد (درایور/DirectX را "
                              "آپدیت کن) → OCR روی CPU.")
                        _ocr_head69 = "CPUExecutionProvider"
                elif _ocr_head69 == "CoreMLExecutionProvider":
                    _gpu_flags69["EngineConfig.onnxruntime.use_coreml"] = True
                if _gpu_flags69:
                    _base.update(_gpu_flags69)
                    print(f"[*] EPِ OCR: {_ocr_head69}")
                self._ocr_ep_active = _ocr_head69
            except Exception:
                _gpu_flags69 = {}
            try:
                import os as _os2
                _cpu_n = _os2.cpu_count() or 4
            except Exception:
                _cpu_n = 4
            # v1.14.66 — MANGA_OCR_THREADS همچنان مقدم است (اگر تنظیم شود).
            # v1.14.99 (SRV-H4) — wiringِ SRV-G (‎-1/emulator=1) خنثی شد و
            # wiringِ e32bccf (PC: cores÷2 تا ۴؛ اندروید: ۱/۲) برگشت —
            # «پیش‌فرضِ خودِ rapidocr» (-1 = ORT auto) همان رگرسیونِ
            # extract را می‌داد. MANGA_ORT_THREADS فقط با تنظیمِ صریح به
            # OCR هم اعمال می‌شود (opt-in tuning).
            try:
                _ocr_th = int(_os2.environ.get("MANGA_OCR_THREADS", "0") or 0)
            except Exception:
                _ocr_th = 0
            try:
                _env_ort_h4 = int(_os2.environ.get("MANGA_ORT_THREADS", "0") or 0)
            except Exception:
                _env_ort_h4 = 0
            _intra = None
            if _ocr_th > 0:
                _intra = max(1, _ocr_th)
            elif _env_ort_h4 > 0:
                _intra = max(1, _env_ort_h4)
            elif _on_android():
                # v1.14.66 — اندروید مثلِ قبل (رم)
                _intra = 1 if _cpu_n <= 4 else 2
            else:
                # v1.14.191 — PC هم عینِ گوشی: ۲ نخ برایِ هر سشنِ OCR.
                # چرا؟ از v1.14.163 به بعد OCR فقط رویِ کراپهایِ کوچکِ
                # detector-v4-s اجرا میشود (نه پاسِ تمامصفحه) — هزینهٔ
                # اصلی = rec (CRNN) که بالایِ ۲ نخ بهرهٔ کمی میگیرد؛
                # موازیِ واقعی از workers میآید (ورکرِ بیشتر × نخِ کمتر).
                # «۸ نخ» (SRV-L رویِ سرور) مالِ دورانِ پاسِ تمامصفحه بود؛
                # رویِ کراپ فقط سربارِ context-switch شد — و با ورکرهایِ
                # چندگانه، workers×8 = تشتتِ کامل (۸ هسته → ۵۶ نخ).
                # MANGA_OCR_THREADS/MANGA_ORT_THREADS همچنان مقدمند.
                _intra = 2
            _threads = {
                "EngineConfig.onnxruntime.intra_op_num_threads": int(_intra),
                "EngineConfig.onnxruntime.inter_op_num_threads": 1,
            }
            # v1.14.237 — سیاستِ تغییرِ اندازهٔ detِ کراپ (لاتین = 960/maxِ
            # رسمیِ PaddleOCR — ۲.۲..۲.۳× سریعتر؛ CJK = همان 736/minِ
            # rapidocr برایِ حفظِ خواندنِ کانجیِ ریز). جزئیات و بنچمارک:
            # _ocr_det_resize_policy
            _det_speed237 = _ocr_det_resize_policy(lang) or {}
            _det_disp237 = ""
            if _det_speed237:
                _det_disp237 = (f" | det={_det_speed237.get('Det.limit_side_len', 736)}"
                                f"/{_det_speed237.get('Det.limit_type', 'min')}")
            _intra_disp = _intra
            # v1.14.191 — برایِ همترازیِ workers×threads≈هسته‌ها (MangaTranslator
            # بعد از ساختِ موتور این را میخواند)
            self.ocr_threads = int(_intra)
            if _rec_params is not None:
                _p = dict(_rec_params)
                _p.update(_base)
                _p.update(_threads)
                _p.update(_det_speed237)
                try:
                    self.engine = NewRapidOCR(params=_p)
                    self._eng_params233 = _p
                except Exception as _eg69:
                    # v1.14.96-speed — اگر ساختِ سشنِ GPU شکست، بدونِ EPِ GPU
                    # دوباره (تا فال‌بکِ legacyِ PP-OCRv3 فعال نشود)
                    if not _gpu_flags69:
                        raise
                    print(f"[!] EPِ GPU برایِ OCR نشد ({str(_eg69)[:130]}) → CPU")
                    _p2 = {k: v for k, v in _p.items() if k not in _gpu_flags69}
                    self.engine = NewRapidOCR(params=_p2)
                    self._eng_params233 = _p2
                    # v1.14.233 — موتور CPU شد؛ قفلِ DML بی‌مورد است
                    self._dml_locked233 = False
                self._new_api = True
                _ep_disp230 = (f" | EP={getattr(self, '_ocr_ep_active', '')}"
                               if str(getattr(self, "_ocr_ep_active", "") or "").strip()
                               else "")
                print(f"[+] RapidOCR (ONNX, PP-OCRv5) آماده | lang={lang} | threads={_intra_disp}{_ep_disp230}{_det_disp237} | cls=خاموش")
                return
            _pb = dict(_base)
            _pb.update(_threads)
            _pb.update(_det_speed237)
            try:
                self.engine = NewRapidOCR(params=_pb)
                self._eng_params233 = _pb
            except Exception as _eg69:
                if not _gpu_flags69:
                    raise
                print(f"[!] EPِ GPU برایِ OCR نشد ({str(_eg69)[:130]}) → CPU")
                _pb2 = {k: v for k, v in _pb.items() if k not in _gpu_flags69}
                self.engine = NewRapidOCR(params=_pb2)
                self._eng_params233 = _pb2
                # v1.14.233 — موتور CPU شد؛ قفلِ DML بی‌مورد است
                self._dml_locked233 = False
            self._new_api = True
            _ep_disp230 = (f" | EP={getattr(self, '_ocr_ep_active', '')}"
                           if str(getattr(self, "_ocr_ep_active", "") or "").strip()
                           else "")
            print(f"[+] RapidOCR (ONNX, PP-OCRv5/v6) آماده | lang={lang} | threads={_intra_disp}{_ep_disp230}{_det_disp237} | cls=خاموش")
            return
        except Exception as e:
            import traceback as _tb
            print(f"[!] RapidOCR (API جدید) لود نشد: {e}")
            print("[!] " + _tb.format_exc()[-900:])
        if not _HAS_RAPIDOCR:
            raise ImportError("pip install rapidocr (یا rapidocr-onnxruntime)")
        self.engine = RapidOCR()
        print(f"[+] RapidOCR (ONNX, PP-OCRv3 قدیمی) آماده | lang={lang}")

    def _init_mobile_engine(self, lang: str) -> None:
        """v1.14.187 — موتورِ یگانهٔ استخراجِ گوشی = RapidOCRِ اندروید
        (ppocr-sdkِ وندورشده — سهگانهٔ RapidOcrAndroidOnnx با
        PP-OCRv4_mobileِ باندل در assets).

        دستورِ سازنده: «متن هاش اشتباهه بعضی وقتا … ببین چجور به این
        خوبی استخراج میکنه همونو رو گوشی بزار» → همهٔ موتورهایِ دیگر (پدلِ ONNXِ
        medium، رپیدِ small، فلاتر-پدلِ tiny و envهایِ کهنهٔ انتخابِ
        موتور) حذف شدند؛ فالبکی وجود ندارد — خطایِ
        ساختِ موتور = استخراجِ خالیِ صریح (با لاگ). استخراج همچنان فقط
        رویِ کراپهایِ detector-v4-s اجرا میشود (بدونِ پاسِ تمامصفحه)."""
        _pb = self._build_paddle_android(lang)
        if _pb is not None:
            self._mobile = _pb
            return
        print("[!] RapidOCRِ اندروید آماده نشد — استخراجِ گوشی "
              "خالی میماند (فالبکی نیست — همهٔ روشهایِ دیگر حذف شدند؛ "
              "دستورِ سازنده: «همونو رو گوشی بزار»)")
        self._mobile = None

    def _build_paddle_android(self, lang: str):
        """v1.14.187 — ساختِ موتورِ «RapidOCRِ اندروید»
        (ppocr-sdkِ وندورشده — سهگانهٔ RapidOcrAndroidOnnx با
        PP-OCRv4_mobileِ باندل در assets) — دستورِ سازنده:
        «متن هاش اشتباهه بعضی وقتا … ببین چجور به این خوبی استخراج
        میکنه همونو رو گوشی بزار». پلِ Kotlin = PaddleOcrBridge (پلِ
        نازک رویِ RapidOcr.create). هر خطا (APKِ قدیمی/بیلدِ ناقص) → None
        (هیچ فالبکی نیست — همهٔ روشهایِ دیگر حذف شدهاند)."""
        try:
            return PaddleAndroidOCR(lang)
        except Exception as e:
            print(f"[!] RapidOCRِ اندروید آماده نشد: {str(e)[:130]}")
            return None

    @staticmethod
    def _deaccent(txt: str) -> str:
        try:
            import unicodedata as _ud
            out = _ud.normalize("NFKD", txt)
            out = "".join(ch for ch in out if not _ud.combining(ch))
            return out
        except Exception:
            return txt

    def _engine_run233_nolock(self, image_bgr):
        try:
            return self.engine(image_bgr, use_cls=False)
        except TypeError:
            return self.engine(image_bgr)

    def _engine_run233(self, image_bgr):
        """v1.14.233 — فراخوانیِ موتورِ OCR. رویِ DML زیرِ قفلِ سراسری:
        سشنهایِ داخلیِ rapidocr (det/rec) از چند کارگرِ موازی صدا زده
        میشوند و DML اجرایِ موازی ندارد (887A0006 رویِ RX 5700 XT —
        لاگِ 232). CPU/CUDA/اندروید بدونِ قفل."""
        if getattr(self, "_dml_locked233", False):
            with _DML_RUN_LOCK:
                return self._engine_run233_nolock(image_bgr)
        return self._engine_run233_nolock(image_bgr)

    def _dml_recover233(self, err) -> bool:
        """v1.14.233 — خطایِ GPU (DirectML) در وسطِ OCR: موتور یک‌بار رویِ
        CPU بازساخته میشود (همان APIِ جدید — بدونِ سقوط به «موتورِ
        قدیمی» که در لاگِ 232 نیمی از متنها را از دست داد). فقط
        خطاهایِ GPU؛ خطاهایِ عادیِ OCR دست‌نخورده میمانند. True = بازسازی
        شد (یا نخِ دیگری کرد) → فراخواننده دوباره امتحان کند."""
        if not getattr(self, "_dml_locked233", False):
            return False
        _m233 = str(err).lower()
        if not any(_s233 in _m233 for _s233 in (
                "887a0006", "80070057", "gpu will not respond",
                "device hung", "device removed", "dml", "directml")):
            return False
        with _RAPIDOCR_RECOVER_LOCK:
            if not getattr(self, "_dml_locked233", False):
                # نخِ دیگری همین الان موتور را CPU کرد → همین موتورِ سالم
                return True
            try:
                # مثلِ __init__: importِ محلی (rapidocr ممکن است نصب نباشد)
                from rapidocr import RapidOCR as NewRapidOCR
                _p233 = dict(getattr(self, "_eng_params233", None) or {})
                if not _p233:
                    return False
                for _k233 in list(_p233.keys()):
                    if _k233 in ("EngineConfig.onnxruntime.use_cuda",
                                 "EngineConfig.onnxruntime.use_dml",
                                 "EngineConfig.onnxruntime.use_coreml") \
                            or "cuda_ep_cfg" in _k233:
                        _p233.pop(_k233, None)
                self.engine = NewRapidOCR(params=_p233)
                self._eng_params233 = _p233
                self._dml_locked233 = False
                self._ocr_ep_active = "CPUExecutionProvider"
                print("[!] خطایِ GPU در OCR → موتور رویِ CPU بازساخته شد "
                      "(کیفیت حفظ شد؛ بقیهٔ صفحات بدونِ وقفه)")
                return True
            except Exception:
                return False

    def ocr(self, image_bgr: np.ndarray, crop_mode: bool = False):

        if image_bgr is None or image_bgr.size == 0:
            return None
        # v1.14.123 — اندروید: موتورِ PP-OCRv6 ONNX (خروجی هم‌قالبِ
        # مسیرهایِ دیگر: [ [box, (text, score)], ... ])
        # v1.14.125 — crop_mode: detِ برشِ بدونِ بزرگنمایی با سقفِ
        # det_cap (فقط مسیرهایِ برشِ کاسکاد/نجات میفرستند؛ صفحه = False)
        if self._mobile is not None:
            try:
                # v1.14.163 — سبکِ جدید: OCR فقط رویِ کراپِ detector-v4-s
                # صدا زده میشود (crop_mode=True). هیچ باندهای/کاسکادی
                # نیست؛ فراخوانیِ تمامصفحه فقط برای مسیرهایِ قدیمیِ
                # جانبی (detect_text) میماند.
                _out = self._mobile.ocr(image_bgr, crop_mode=crop_mode)
            except Exception as _e164:
                # v1.14.164 — خطایِ بیصدا ممنوع: رگِ «متن پیدا نشد»ٔ
                # 1.14.163 یک AttributeErrorِ بیصدا بود (رگرسیونِ
                # تودرتوییِ _ocr_impl)؛ حالا هر خرابیِ OCR یک خطِ کوتاه
                # و مشخص در لاگ میدهد تا ریشه فوراً دیده شود.
                print(f"[!] خطایِ OCRِ موبایل: {str(_e164)[:150]}")
                return None
            if not _out or not _out[0]:
                return None
            _lines = []
            _ncjk = 0
            for _box, _pair in _out[0]:
                try:
                    _t = self._deaccent(str(_pair[0])).strip()
                    if not _t:
                        continue
                    if self._cjk_guard and _cjk_dominant_154(_t):
                        _ncjk += 1
                        continue
                    _s = float(_pair[1])
                    _lines.append([_box, (_t, _s)])
                except Exception:
                    continue
            if _ncjk:
                print(f"    [OCR] {_ncjk} خطِ پر از نویسهٔ چینی حذف شد "
                      "(گاردِ لاتین — v1.14.154)")
            return [_lines] if _lines else None
        if self._new_api:
            # v1.14.233 — حداکثر ۲ تلاش: تلاشِ دوم فقط بعد از بازسازیِ
            # موتور رویِ CPU در خطایِ GPU (_dml_recover233) — کیفیتِ
            # نتایج حتی موقعِ خرابیِ GPU حفظ میشود (لاگِ 232: سقوط به
            # «موتورِ قدیمی» ۸ ناحیه از ۱۱ را بی‌متن گذاشت).
            for _att233 in range(2):
                try:
                    out = self._engine_run233(image_bgr)
                    txts = getattr(out, "txts", None)
                    if not txts:
                        return None
                    boxes = getattr(out, "boxes", None)
                    scores = getattr(out, "scores", None)
                    lines = []
                    for i, t in enumerate(txts):
                        t = self._deaccent(str(t)).strip()
                        if not t:
                            continue
                        score = float(scores[i]) if scores is not None and i < len(scores) else 1.0
                        box = boxes[i] if boxes is not None and i < len(boxes) else [[0, 0], [1, 0], [1, 1], [0, 1]]
                        lines.append([np.asarray(box, dtype=np.float32), (t, score)])
                    return [lines] if lines else None
                except Exception as e:
                    msg = str(e).lower()
                    if "text detection result is empty" in msg or "detection result is empty" in msg:
                        return None
                    if _att233 == 0 and self._dml_recover233(e):
                        continue  # موتور رویِ CPU بازساخته شد → تلاشِ دوم
                    print(f"    [OCR] rapidocr جدید خطا: {e} → موتور قدیمی")
                    self._new_api = False
                    if not _HAS_RAPIDOCR:
                        return None
                    break
        try:
            result, _ = self._engine_run233(image_bgr)
        except Exception as e:
            msg = str(e).lower()
            if "text detection result is empty" in msg or "detection result is empty" in msg:
                return None
            # v1.14.233 — خطایِ GPU → موتور رویِ CPU + یک تلاشِ دیگر
            if self._dml_recover233(e):
                try:
                    result, _ = self._engine_run233(image_bgr)
                except Exception:
                    return None
            else:
                return None
        if not result:
            return None
        lines = []
        for item in result:
            if len(item) < 3:
                continue
            box, text, score = item[0], item[1], item[2]
            text = self._deaccent(str(text)).strip()
            if not text:
                continue
            lines.append([box, (text, float(score))])
        return [lines] if lines else None


# ═══════════════════════════════════════════════════════════════════════
# v1.14.163 — سبکِ «استخراج و پاکسازی»ٔ مخصوصِ گوشی کلاً حذف شد (دستورِ
# سازنده: «سبکِ استخراج و پاکسازی رو گوشی کامل حذف کنی؛ مالِ پی‌سی
# لینوکس استفاده کنه»). حذفشده‌ها در این نسخه:
#   • کاسکادِ مرجع (راهنمایِ ML Kit + پلهٔ Paddle-Lite + رپیدِ فالبک)
#   • کلاسِ MlKitBackend و راهنمایِ برشِ امنِ ML Kit (_mlkit_guide)
#   • _mobile_banded_ocr (خواندنِ باندبه‌باندِ تمامصفحه)
#   • MlKitBridge.kt + PaddleLiteBridge.kt + PliteProbeService.kt
#     + وابستگیهایِ mlkit/PaddlePredictor در build.gradle
# سبکِ جدید (PC/لینوکس/اندروید یکسان):
#   • برشِ امن = فقط detector-v4-s_int8.onnx — باندِ ۷۵۰۰–۸۰۰۰، برش
#     فقط جایی که هیچ باکسِ متنی نبیند (متن هرگز برش نمیخورد)
#   • استخراجِ متن = detector-v4-s مکانِ متن را پیدا میکند و OCR فقط
#     رویِ همان کراپها اجرا میشود — هیچ پاسِ تمامصفحه‌ای نیست
# v1.14.166 — Paddle-Lite فقط به‌عنوانِ «موتورِ OCRِ کراپ» برگشت (بالا)؛
# هیچ‌کدام از سبکهایِ حذفشدهٔ این بلاک (کاسکاد/تمامصفحه) بازنگشت.
# v1.14.170 — موتورِ OCRِ کراپ = ML Kit شد (پدل کامل حذف شد)؛ همین
# قاعده پابرجاست: فقط کراپِ detector-v4-s، هیچ پاسِ تمامصفحهای نیست.
# v1.14.183 — ML Kit هم کامل حذف شد (پلِ MlKitBridge.kt + وابستگیهایِ
# com.google.mlkit از APK)؛ موتورِ کراپ = رپیدِ رسمیِ اندروید (PP-OCRv4_mobile)
# — قاعدهٔ «فقط کراپِ detector-v4-s» پابرجاست.
# ═══════════════════════════════════════════════════════════════════════

def _dual_device_enabled() -> bool:
    """v1.14.106 — دو-دستگاهه: GPU و CPU «همزمان» برایِ استخراج/پاکسازی.

    MANGA_DUAL_DEVICE=1 → اجبارِ روشن | 0 → خاموش | پیش‌فرض: خودکار (روشن
    فقط وقتی EPِ سرِ سشن واقعاً GPU-گونه باشد؛ ساختهٔ CPU-خالص هرگز تغییر
    نمی‌کند تا رگرسیونِ بیت‌به‌بیت حفظ شود)."""
    try:
        _v = os.environ.get("MANGA_DUAL_DEVICE", "").strip().lower()
        if _v in ("1", "true", "yes", "on"):
            return True
        if _v in ("0", "false", "no", "off"):
            return False
    except Exception:
        pass
    return True  # خودکار: فقط وقتی EPِ GPU واقعاً هست فعال می‌شود


def _gpu_head_of(session):
    """اولین EPِ سشن که CPU خالص نیست (CUDA/DML/NNAPI/XNNPACK/…) — یا None."""
    try:
        for _p in (session.get_providers() or []):
            if not str(_p).lower().startswith("cpu"):
                return str(_p)
    except Exception:
        pass
    return None


def _android_like_env() -> bool:
    """v1.14.96-speed — تشخیصِ مقاومِ محیطِ اندروید (مکملِ import java).

    Chaquopy فقط با import java شناسایی می‌شود؛ بقیهٔ ران‌تایم‌هایِ
    اندروید (ترماکس و…) با نشانه‌هایِ محیطی: وجودِ /system/build.prop،
    متغیرهایِ ANDROID_ROOT/ANDROID_DATA یا «android» در release هسته."""
    try:
        if os.path.isfile("/system/build.prop"):
            return True
        if os.environ.get("ANDROID_ROOT") or os.environ.get("ANDROID_DATA"):
            return True
        if "android" in (os.uname().release or "").lower():
            return True
    except Exception:
        pass
    return False


# v1.14.110 — گاردِ کرشِ nativeِ Paddle-Lite رویِ گوشی: سیگ‌فالت از
# لاگ‌گیرِ جاوای اپ رد نمیشود → قبل از کارِ خطرناکِ native ردپا
# میگذاریم؛ اگر پروسه مرد، استارتِ بعدیِ اپ لاگ را نشان میدهد و
# موتورِ جایگزین (رپیدِ رسمیِ اندروید/ONNX) میآید — درخواستِ کاربر: «لاگ بزنه
# کرش کنه، مجدد اپ باز کردم لاگ کرشش بیاد»
def _on_android() -> bool:
    try:
        import java
        return True
    except Exception:
        return False


def _android_gate(env_name: str) -> bool:
    """v1.14.133 — گیتِ مشترکِ فیکسهایِ پاکسازیِ اندروید. پیشفرض = فقط
    اندروید (رفتارِ PC بایت‌به‌بایت مثلِ قبل میماند)؛ env=1/0 برایِ اجبار
    (تستِ مسیرِ اندروید رویِ PC)."""
    _v = str(os.environ.get(env_name, "") or "").strip().lower()
    if _v in ("1", "true", "yes", "on"):
        return True
    if _v in ("0", "false", "no", "off"):
        return False
    return bool(_on_android())


def _gate_default_on(env_name: str) -> bool:
    """v1.14.212 — گیتِ پیشفرضِ روشن رویِ «هر دو» پلتفرم (env=0 خاموش).
    فلسفهٔ «PC بیت‌به‌بیت» با گزارشِ سازنده رویِ GitHub Actions (PC)
    منسوخ شد: «همه عکس هارو تست کن مو به مو چک کن رد نکن … نه لگهٔ
    سیاهی نه لگهٔ سفیدی یا هرنگی لگه بشه قبول نمیکنم» — کیفیتِ پاکسازی
    رویِ PC هم باید همانِ اندروید باشد."""
    return str(os.environ.get(env_name, "") or "").strip().lower() \
        not in ("0", "false", "no", "off")


class PaddleOCRWrapper:


    def __init__(self, engine):
        self.engine = engine

    def ocr(self, image_bgr: np.ndarray):
        try:
            if hasattr(self.engine, "predict"):
                return self.engine.predict(image_bgr)
            return self.engine.ocr(image_bgr)
        except Exception:
            return None


