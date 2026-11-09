# BUILD-STRIP-START
# ─────────────────────────────────────────────────────────────
# 📦 دانلودِ مدلها — آینهها، _dl_to، _mirror_model، _ensure_rapidocr_models
# (متنِ بالا فقط راهنمای همین فایل است؛ در بیلدِ manga.py حذف میشود)
# BUILD-STRIP-END
_RAPIDOCR_MIRROR = ("https://github.com/amirwolf512k/Manga-AutoTranslate/"
                    "releases/download/models/")
_RAPIDOCR_MS = ("https://www.modelscope.cn/models/RapidAI/RapidOCR/"
                "resolve/v3.9.2/onnx")
_RAPIDOCR_FILES = {
    "PP-OCRv6_det_small.onnx":
        _RAPIDOCR_MS + "/PP-OCRv6/det/PP-OCRv6_det_small.onnx",
    "PP-OCRv6_rec_small.onnx":
        _RAPIDOCR_MS + "/PP-OCRv6/rec/PP-OCRv6_rec_small.onnx",
    "ch_ppocr_mobile_v2.0_cls_mobile.onnx":
        _RAPIDOCR_MS + "/PP-OCRv4/cls/ch_ppocr_mobile_v2.0_cls_mobile.onnx",
    "korean_PP-OCRv5_rec_mobile.onnx":
        _RAPIDOCR_MS + "/PP-OCRv5/rec/korean_PP-OCRv5_rec_mobile.onnx",
    "japan_PP-OCRv4_rec_mobile.onnx":
        _RAPIDOCR_MS + "/PP-OCRv4/rec/japan_PP-OCRv4_rec_mobile.onnx",
    # v1.14.152 — مجموعهٔ مرجع (منبعِ فالبک = رسمیِ PaddlePaddle/modelscope؛
    # منبعِ اصلی = ریلیزِ «models» خودمان با همین نامها)
    "PP-OCRv6_medium_det_onnx.onnx":
        "https://huggingface.co/PaddlePaddle/PP-OCRv6_medium_det_onnx"
        "/resolve/main/inference.onnx",
    "PP-OCRv6_medium_rec_onnx.onnx":
        "https://huggingface.co/PaddlePaddle/PP-OCRv6_medium_rec_onnx"
        "/resolve/main/inference.onnx",
    "PP-OCRv5_korean_rec.onnx":
        "https://huggingface.co/PaddlePaddle/korean_PP-OCRv5_mobile_rec_onnx"
        "/resolve/main/inference.onnx",
    "ch_PP-OCRv4_det_infer.onnx":
        _RAPIDOCR_MS + "/PP-OCRv4/det/ch_PP-OCRv4_det_mobile.onnx",
    "ch_PP-OCRv4_rec_infer.onnx":
        _RAPIDOCR_MS + "/PP-OCRv4/rec/ch_PP-OCRv4_rec_mobile.onnx",
    # v1.14.179 — موتورِ «فلاتر-پدل» (flutter-paddle-ocr) = PP-OCRv6 tiny
    # (دستورِ سازنده: «flutter-paddle-ocr اینم اضافه کن واسه تست» —
    # github.com/mencomao/flutter-paddle-ocr همان PP-OCRv6 tinyِ ONNXِ
    # خالص رویِ ONNX Runtime است، نه Paddle-Lite). منبعِ اصلی = HFِ
    # رسمیِ PaddlePaddle (همان الگویِ medium)؛ فالبک = ریلیزِ modelsِ
    # خودمان. det 1.7MB + rec 4.3MB — سبکترین جفتِ خانوادهٔ v6.
    "PP-OCRv6_tiny_det.onnx":
        "https://huggingface.co/PaddlePaddle/PP-OCRv6_tiny_det_onnx"
        "/resolve/main/inference.onnx",
    "PP-OCRv6_tiny_rec.onnx":
        "https://huggingface.co/PaddlePaddle/PP-OCRv6_tiny_rec_onnx"
        "/resolve/main/inference.onnx",
    # dictِ مخصوصِ tiny (۶۹۰۴ نویسه — استخراجشده از inference.ymlِ مدلِ
    # رسمی؛ جدا از medium ۱۸۷۰۷ی و small ۶۶۲۳ی) — فقط از ریلیزِ خودمان
    "ppocr_keys_v6_tiny_utf8.txt":
        _RAPIDOCR_MIRROR + "ppocr_keys_v6_tiny_utf8.txt",
    # v1.14.182 — charsetِ رسمیِ PP-OCRv6 medium rec (paddleocr.aiِ
    # android_deployment: «rec = inference.onnx + inference.yml»)؛
    # ۱۸۷۰۸ نویسه + فاصله. v1.14.184 — پلِ PaddleOcrBridge از
    # inference.ymlِ باندلشده در assets میخواند (SDKِ رسمی) — این مدخل
    # فقط برایِ سازگاریِ نگاشتِ URLهایِ قدیمی مانده است.
    "PP-OCRv6_medium_rec_inference.yml":
        "https://huggingface.co/PaddlePaddle/PP-OCRv6_medium_rec_onnx"
        "/resolve/main/inference.yml",
}


def _pc_det_medium() -> bool:
    """v1.14.191 — سوئیچِ نجاتِ detِ سنگینِ قبلی رویِ PC.

    دستورِ سازنده: «نمیشه کاری کرد مثل گوشی پی سی لینوکس هم استخراجش
    سریع باشه؟» → پیشفرضِ PC از v1.14.191 = عینِ ستِ گوشی (detِ
    PP-OCRv6_small ۱۰MB). با MANGA_OCR_DET_MEDIUM=1 رفتارِ
    v1.14.188..190 (detِ mediumِ ۵۹MB — مرجع) برگردد (کسانی که detِ
    حداکثری میخواهند؛ CPUهایِ قوی).
    """
    _v = str(os.environ.get("MANGA_OCR_DET_MEDIUM", "") or "").strip().lower()
    return _v in ("1", "true", "yes", "on")


def _rapidocr_model_pair(lang: str, small: bool = False,
                         tiny: bool = False):
    """v1.14.152 — جفتِ (det, rec) بر اساسِ زبان.

    v1.14.191 — پیشفرضِ PC = عینِ ستِ گوشی (دستورِ سازنده: «مثل گوشی
    پی سی لینوکس هم استخراجش سریع باشه»):
      det = PP-OCRv6_det_small.onnx (۱۰MB — همان detِ گوشی؛ بنچمارکِ
            کلاسِ PCِ قدیم/۲ هسته رویِ ۹ کراپِ lang_zh.jpg:
            detِ medium ۲۹.۷s → detِ small ۱۸.۴s با همان متن — #01 حتی
            تمیزتر: «6 DIALOGUE BUBBLES» کامل)
      recِ en/zh/ja = PP-OCRv6_medium_rec_onnx.onnx (73.01MiB)
      recِ ko = PP-OCRv5_korean_rec.onnx (رسمی، 12.80MiB)
    v1.14.191 — zh هم عینِ گوشی شد: جفتِ قدیمیِ ch_PP-OCRv4 (v1.14.152)
    فاصلههایِ لاتین را میبلعید («ONESOURCEART-3PANELS») و پسِ ویرگول
    تکراری میساخت («،自 自己»)؛ v6_medium مو به مو متنِ گوشی را میدهد.
    MANGA_OCR_DET_MEDIUM=1 = detِ mediumِ قبلی (مرجع — v1.14.188..190).
    small=True (فقط شبیهسازِ x86_64 در CI) = مجموعهٔ سبکِ قبلی تا
    بودجهٔ زمانی و گیتهایِ CI دستنخورده بمانند.
    tiny=True = «فلاتر-پدل» (v1.14.179 — بدونِ تغییر).
    """
    _low = str(lang).lower()
    if tiny:
        _det = "PP-OCRv6_tiny_det.onnx"
        if _low in ("korean", "ko"):
            return _det, "korean_PP-OCRv5_rec_mobile.onnx"
        if _low in ("japan", "ja", "japanese"):
            return _det, "japan_PP-OCRv4_rec_mobile.onnx"
        return _det, "PP-OCRv6_tiny_rec.onnx"
    if small:
        _det = "PP-OCRv6_det_small.onnx"
        if _low in ("korean", "ko"):
            return _det, "korean_PP-OCRv5_rec_mobile.onnx"
        if _low in ("japan", "ja", "japanese"):
            return _det, "japan_PP-OCRv4_rec_mobile.onnx"
        return _det, "PP-OCRv6_rec_small.onnx"
    # v1.14.191 — detِ PC = عینِ گوشی (small ۱۰MB؛ نه mediumِ ۵۹MB)
    _det = ("PP-OCRv6_medium_det_onnx.onnx" if _pc_det_medium()
            else "PP-OCRv6_det_small.onnx")
    if _low in ("korean", "ko"):
        return _det, "PP-OCRv5_korean_rec.onnx"
    # v1.14.190 — ja هم از recِ mediumِ پیشفرض میخواند (بنچمارکِ صفحهٔ
    # تستِ سازنده: v6_medium ژاپنیِ مانگا را کاملتر از japan v4 میخواند —
    # عینِ تصمیمِ گوشی؛ recِ جداگانهیِ ja حذف شد)
    # v1.14.191 — zh هم از همین rec (عینِ گوشی — جفتِ v4 حذف شد)
    return _det, "PP-OCRv6_medium_rec_onnx.onnx"


def _pc_ocr_small() -> bool:
    """v1.14.188 — مجموعهٔ مدلِ OCRِ PC. دستورِ سازنده: «چرت پرت هم زیاد
    استخراج میکنه نمیشه یک کاری کرد از نسخهٔ پی سی استخراج استفاده کنه
    همون مدل onnx v6 ocr … مدل v6_medium استفاده کن بعد توجه ک کردم رو
    پی سی هم ناقص استخراج میشه رو اونم چک کن هردوشو چک بزن» → PC هم از
    مجموعهٔ کاملِ medium استفاده میکند (detِ medium + recِ medium —
    همان ستِ مرجع). MANGA_OCR_SMALL=1 یا شبیهسازِ x86_64 (CI) = ستِ سبک
    (small) تا بودجهٔ زمانیِ CI دستنخورده بماند."""
    _v = str(os.environ.get("MANGA_OCR_SMALL", "") or "").strip().lower()
    if _v in ("1", "true", "yes", "on"):
        return True
    if _v in ("0", "false", "no", "off"):
        return False
    return bool(_android_x86_emulator())


def _ocr_det_resize_policy(lang: str):
    """v1.14.237 — سیاستِ تغییرِ اندازهٔ detِ داخلِ RapidOCR رویِ کراپها.

    دستورِ سازنده: «میخوام یک کاری کنی استخراج خوب کار کنی … به پایین
    ترین حد ممکن زمانش برسونی سریع استخراج کنه با cpu … مدل استخراج باید
    همین paddleocr onnx باشه». ریشه‌یابی با بنچمارکِ واقعیِ img4
    (690×11200 — سندباکسِ ۲هسته، پایپ‌لاینِ کاملِ _extract_regions_from_
    bubbles): پیشفرضِ rapidocr پایتون یعنی Det.limit_type="min" با
    limit_side_len=736 — «هر» کراپی که ضلعِ کوتاهش <736 باشد قبل از det
    بزرگ میشود تا ضلعِ کوتاهش ۷۳۶ شود. کراپِ متعارفِ حباب (پهن اما
    کم‌ارتفاع؛ مثلِ 613×84) با نسبتِ ۸.۷۶× به detِ 736×5376 میرود!
    نتیجه: detِ داخلِ کراپ ۶۰٪+ زمانِ OCR بود (پروفایل: det 5.7s /
    rec 25.2s بعد از فیکس). این همان دلیلی است که «گوشی سریعتر از PC
    استخراج میکرد»: موتورِ اندروید (RapidOcrEngine.kt) از اول
    maxSideLen=960 با سیاستِ max بود و پایتون نه.

    سیاستِ تازه برایِ زبانهایِ لاتین = 960/max — دقیقاً پیشفرضِ رسمیِ
    PaddleOCR («The default setting of the parameters is limit_type=max,
    det_limit_side_len=960» — مستنداتِ inferenceِ PaddleOCR): بزرگنماییِ
    کراپهای کوچک دیگر انجام نمیشود؛ فقط کراپِ بلندتر از ۹۶۰ کوچک
    میشود. بنچمارکِ A/B (متنِ کاملِ مقایسه شد):
      • img4 (انگلیسی، وبتونِ ۱۱۲۰۰px): کلِ استخراج ۹۹.۹s → ۴۳.۲s
        (۲.۳×) و متنِ «بهتر»: ARTCLE9(TEACHERSAUTHORTY)/E7(STUDREPE)ی
        غلط → ARTICLE9(TEACHERS'AUTHORITY) درست + ARTICLE7ی جاافتاده
        پیدا شد (۲۴→۲۶ ناحیه، ۱۰۶→۱۰۹ خط).
      • img6 (کمیکِ انگلیسی): ۳۲.۸s → ۱۴.۷s (۲.۲×)، متنِ همارز
        (فقط جابهجاییِ ترتیبِ واژه در باکسها + ترمیمِ I'Ll→I'll).
      • lang_ja_color (پیشنمایشِ ژاپنیِ ریز 1200×675): متنِ کانجیِ ریز
        به بزرگنمایی نیاز دارد → با 960/max از ۱۰ خط به ۲ خط سقوط
        کرد. پس زبانهایِ CJK (ja/ko/zh/multi) روی همان 736/minِ
        rapidocr میمانند — کیفیتِ امروز، ریسکِ صفر؛ سرعتِ CJK از
        سمتِ مدلها تغییر نمیکند.
    نردبانِ واریانتها (raw→clahe/otsu/inv) و تقویتِ کراپ (scale تا 2.4)
    دستنخوردهاند — همان جبرانِ کیفیتِ قبلی برایِ متنِ ریز.

    اوررایدها: MANGA_OCR_DET_FAST=0 → خاموش (رفتارِ کاملِ قدیم =
    736/min برایِ همه) | MANGA_OCR_DET_LIMIT=N | MANGA_OCR_DET_TYPE=
    min|max (برایِ هر زبان — تستِ دستی). خروجی: dictِ پارامترهایِ
    rapidocr یا None (= پیشفرضِ rapidocr)."""
    try:
        _v237 = str(os.environ.get("MANGA_OCR_DET_FAST", "")).strip().lower()
        if _v237 in ("0", "false", "no", "off"):
            return None
    except Exception:
        pass
    _low237 = str(lang or "").lower()
    _cjk237 = _low237 in ("japan", "ja", "japanese", "ko", "korean",
                          "zh", "ch", "chinese", "ch_sim", "zh_hans",
                          "zh_hant", "zh-tw", "zh_tw", "multi")
    # اوررایدهای صریحِ کاربر
    try:
        _e_lim237 = int(os.environ.get("MANGA_OCR_DET_LIMIT", "0") or 0)
    except Exception:
        _e_lim237 = 0
    _e_typ237 = str(os.environ.get("MANGA_OCR_DET_TYPE", "") or "").strip().lower()
    if _cjk237:
        # CJK: پیشفرضِ rapidocr (736/min) + اوررایدِ صریحِ کاربر
        if _e_lim237 > 0 or _e_typ237 in ("min", "max"):
            out = {}
            if _e_lim237 > 0:
                out["Det.limit_side_len"] = int(_e_lim237)
            if _e_typ237 in ("min", "max"):
                out["Det.limit_type"] = _e_typ237
            return out or None
        return None
    # لاتین: 960/maxِ رسمیِ PaddleOCR (اورراید بر آن هم اعمال میشود)
    out = {"Det.limit_side_len": 960, "Det.limit_type": "max"}
    if _e_lim237 > 0:
        out["Det.limit_side_len"] = int(_e_lim237)
    if _e_typ237 in ("min", "max"):
        out["Det.limit_type"] = _e_typ237
    return out


def _latin_lang188(tr) -> bool:
    """v1.14.188 — زبانِ صفحه لاتین است؟ (برایِ فیلترِ آشغالِ لاتین؛
    صفحاتِ ja/ko/zh هرگز این فیلتر را نمیگیرند.)"""
    try:
        _lg = str(getattr(getattr(tr, "ocr", None), "lang", "") or "").lower()
        if not _lg:
            _lg = str(getattr(tr, "lang", "") or "en").lower()
    except Exception:
        _lg = "en"
    return _lg not in ("ja", "japan", "japanese", "ko", "korean",
                       "zh", "ch", "chinese", "ch_sim", "zh_hans",
                       "zh_hant", "zh-tw", "zh_tw")


def _line_is_foreign188(bb, block_rects, own_area: float) -> bool:
    """v1.14.188 — مالکیتِ خط. خطی که مرکزش داخلِ مستطیلِ «ناحیهٔ
    همسایهٔ» تنگتر است (مساحتِ همسایه < ۸۵٪ ناحیهٔ خودی) و حداقل ۴۵٪
    خط در آن افتاده، متعلق به همان همسایه است — نه این کراپ. ریشهٔ
    «چرت‌پرت» در img6: متنِ حبابِ کوچکِ «You're the real attraction
    here.» داخلِ کراپِ ناحیهٔ بزرگِ زرد نشت میکرد (rectهای RT-DETR
    همپوشانی دارند)."""
    if not block_rects or bb is None:
        return False
    try:
        cx = (float(bb[0]) + float(bb[2])) * 0.5
        cy = (float(bb[1]) + float(bb[3])) * 0.5
        lw = max(1.0, float(bb[2]) - float(bb[0]))
        lh = max(1.0, float(bb[3]) - float(bb[1]))
        la = lw * lh
    except Exception:
        return False
    for _r in (block_rects or []):
        try:
            bx1, by1, bx2, by2 = [float(v) for v in _r]
            if not (bx1 - 4.0 <= cx <= bx2 + 4.0
                    and by1 - 4.0 <= cy <= by2 + 4.0):
                continue
            ix = max(0.0, min(float(bb[2]), bx2) - max(float(bb[0]), bx1))
            iy = max(0.0, min(float(bb[3]), by2) - max(float(bb[1]), by1))
            if la <= 0 or (ix * iy) / la < 0.45:
                continue
            nb_area = max(1.0, (bx2 - bx1) * (by2 - by1))
            if nb_area < own_area * 0.85:
                return True
        except Exception:
            continue
    return False


def _clamp_lines_to_det204(res, box, block_rects=None, tol: float = 10.0):
    """v1.14.206 — استخراج نباید از باکسِ detector بیرون بزند (دستورِ
    سازنده: «وقتی detector متن در اورد نباید استخراج از اون بیشتر بگیره —
    الان میشه دید کل سه حباب گرفته»). دو قاعدهٔ مالکیتِ خط:
      ۱) مرکزِ خط داخلِ باکسِ detectorِ خودِ ناحیه نیست → مالِ این ناحیه
         نیست (کراپِ گسترشیافتهٔ متنِ کج تا ۱۲۰px خطِ مجاور را میخواند؛
         فیلترِ ۱۸۸ فقط «همسایهٔ کوچکتر» را حذف میکند — خطِ همسایهٔ
         بزرگتر مثلِ تایتلِ کجِ کاغذ در ناحیهٔ حبابِ کوچک میماند →
         گسترشِ angle مستطیل را منفجر میکند و mergeِ همپوشانی سه حباب
         را یکجا میگیرد).
      ۲) اگر مرکزِ خط داخلِ باکسِ «کوچکتری» از همسایهها هم هست، خط مالِ
         همان است — دوباره‌پردازیِ deskewِ _ocr_crop از فیلترِ ۱۸۸ رد
         میشود و ناحیهٔ بزرگ (تایتل) خطِ حبابهایِ کوچکِ داخلِ باکسش را
         نگه میدارد → باز همان انفجارِ مستطیل. این قفل بعد ازِ خروجیِ
         نهاییِ _ocr_crop اجرا میشود → همهٔ مسیرها پوشش داده میشوند.
    خط/متن/زاویه/بلوکِ همترازِ خطِ حذفشده با هم میروند."""
    try:
        txt, polys, angs, texts, blks = res
        if not polys or not box or len(box) < 4:
            return res
        if not (len(polys) == len(texts) == len(angs) == len(blks)):
            return res  # ساختارِ غیرمنتظره — دستنخورده (فیلترِ ۱۸۸ پوشش میدهد)
        bx1, by1, bx2, by2 = [float(v) for v in box[:4]]
        own_area = max(1.0, (bx2 - bx1) * (by2 - by1))
        _others = []
        for _r in (block_rects or []):
            try:
                ox1, oy1, ox2, oy2 = [float(v) for v in _r[:4]]
                if ox2 - ox1 > 1.0 and oy2 - oy1 > 1.0:
                    _others.append((ox1, oy1, ox2, oy2,
                                    (ox2 - ox1) * (oy2 - oy1)))
            except Exception:
                continue
        keep = []
        for p in polys:
            try:
                pp = np.asarray(p, dtype=np.float32).reshape(-1, 2)
                cx = float(pp[:, 0].mean())
                cy = float(pp[:, 1].mean())
            except Exception:
                keep.append(True)
                continue
            if not ((bx1 - tol) <= cx <= (bx2 + tol)
                    and (by1 - tol) <= cy <= (by2 + tol)):
                keep.append(False)  # قاعدهٔ ۱ — بیرونِ باکسِ خودِ ناحیه
                continue
            _stolen = False
            for (ox1, oy1, ox2, oy2, oa) in _others:
                if oa >= own_area:
                    continue  # فقط همسایهٔ کوچکتر مالکیت را میگیرد
                if ((ox1 - tol) <= cx <= (ox2 + tol)
                        and (oy1 - tol) <= cy <= (oy2 + tol)):
                    _stolen = True
                    break
            keep.append(not _stolen)  # قاعدهٔ ۲ — مالِ کوچکترین باکس
        if all(keep):
            return res
        _txt = " ".join(str(texts[i] or "").strip()
                        for i in range(len(polys)) if keep[i]).strip()
        return (_txt,
                [polys[i] for i in range(len(polys)) if keep[i]],
                [angs[i] for i in range(len(angs)) if keep[i]],
                [texts[i] for i in range(len(texts)) if keep[i]],
                [blks[i] for i in range(len(blks)) if keep[i]])
    except Exception:
        return res


def _latin_junk_line188(text, region_has_letters: Optional[bool] = None):
    """v1.14.188 — خطِ آشغالِ لاتین («چرت‌پرت») — فقط کلِ خط:
      • بدونِ هیچ حرفِ لاتین و کوتاه (≤۴ نویسه): «23»، «豊»، «H/»
      • همهٔ توکنها ≤۲ حرف و هیچ واکه‌ای ندارند: «FL»، «SS»، «Px»
    خطهایِ واقعی («GO!»، «Wha!?»، «OK») میمانند؛ فقط برایِ صفحاتِ
    لاتین صدا زده میشود (_latin_lang188).

    v1.14.245 — عدد/نماد دیگر «حذفِ خط» نیست (دستورِ سازنده:
    «19 hi باید هردوشو بخونه حذف شه — اشتباه ک میکنه hi میخونه 19
    میپاکه» و «1233 نباید حذف شه»): سیاستِ عدد/نماد در «سطحِ ناحیه»
    تعیین میشود (source_has_letters + no_touch230)، نه در سطحِ خط.
    در ناحیهٔ حرف‌دار، خطِ عدد = محتوای دیالوگ است («19 hi»)؛ در
    ناحیهٔ بی‌حرف، ماندنِ خطها باعث میشود ناحیه «فقط-عدد/نماد» شناخته
    شود (no_touch230 = دست‌نخورده) نه «OCR-خالی» که پاک میشود.
    پارامترِ region_has_letters: متنِ کلِ ناحیه حرف دارد یا نه؛
    None = رفتارِ قدیمی (برایِ فراخوانی‌های بدونِ متنِ ناحیه)."""
    s = str(text or "").strip()
    if not s:
        return True
    toks = re.findall(r"[A-Za-z]+", s)
    if not toks:
        # v1.14.245 — خطِ عددِ خالص («19»، «10,000»، «۳:۳۰») محتواست:
        # در ناحیهٔ حرف‌دار میماند (باید خوانده و پاک شود)؛ در ناحیهٔ
        # بی‌حرف هم میماند (تا ناحیه no_touch شود). فقط سمبل/نویسهٔ
        # بی‌حرفِ کوتاه (H/، ؟!) در ناحیهٔ حرف‌دار هنوز آشغال است.
        if region_has_letters is False:
            return False
        if re.fullmatch(
                r"[\d\u06F0-\u06F9\u0660-\u0669]"
                r"[\d\u06F0-\u06F9\u0660-\u0669\s.,:'\-]*", s):
            return False
        return len(s) <= 4
    # «77,I» / «1,I» — دو digits + حرفِ تک؛ خوانشِ اشتباهِ حرفِ ایتالیک
    _alpha188 = [c for c in s if c.isascii() and c.isalpha()]
    if sum(c.isdigit() for c in s) >= 2 and len(_alpha188) <= 2:
        # v1.14.189 — اگر حرفها فقط I/i/l باشند، خط حذف نمیشود؛
        # به «I» ترمیم میشود («77,I» = «I'll» ناخوانا — لاگ گوشی ۱۸۸).
        if _alpha188 and all(c in "Iil" for c in _alpha188):
            return "I"
        # v1.14.245 — «19 hi» / «19th»: عدد در متنِ حرف‌دار محتواست؛
        # در ناحیهٔ بی‌حرف هم خط میماند تا ناحیه no_touch شود.
        if region_has_letters is not None:
            return False
        return True
    if all(len(t) <= 2 for t in toks):
        _vow = "AEIOUaeiou"
        if not any(any(c in _vow for c in t) for t in toks):
            return True
    return False


def _fmt_mb(n: float) -> str:
    return f"{n / (1024 * 1024):.1f}MB"


def _dl_progress(name: str, done: int, total: int, _last: list = [0.0, 0]) -> None:
    import time as _t
    now = _t.time()
    if total > 0:
        pct = min(100, int(done * 100 / total))
        if now - _last[0] < 0.8 and pct - _last[1] < 5 and pct < 100:
            return
        _last[0], _last[1] = now, pct
        print(f"\r    دانلود {name}: {pct}% ({_fmt_mb(done)}/{_fmt_mb(total)})"
              + (" " * 4), end="", flush=True)
    else:
        if now - _last[0] < 1.5:
            return
        _last[0] = now
        print(f"\r    دانلود {name}: {_fmt_mb(done)}", end="", flush=True)


def _dl_to(url, dst, name: str = "", attempts: int = 3):
    """v1.14.234 — دانلودِ مقاوم: (۱) ادامهٔ دانلودِ نیمه‌کاره با هدرِ
    Range — لاگِ کاربر: detector.onnx دو بار تا ~۷۵٪ (121MB از 160.7MB)
    آمد و ریستِ اتصالِ WinError 10054 هر دو بار همه چیز را دور ریخت چون
    .part بعد از شکست حذف میشد و دفعهٔ بعد از صفر شروع میشد؛ (۲) تا
    «attempts» تلاشِ خودکار با مکثِ ۲s — هر تلاش از همان‌جا ادامه
    مییابد (GitHub/HF هر دو به Range جوابِ 206 میدهند). (۳) نشانِِ
    url کنارِ .part (‏.part.url): ادامهٔ دانلود فقط از «همین» url مجاز
    است — الحاقِ بایتهای دو سرورِ مختلف (mirror + HF) = فایلِ خراب؛
    .partِ بی‌نشان یا از سرورِ دیگر → دور ریخته میشود. 416 =
    .partِ بی‌اعتبار → حذف و شروعِ تازه در تلاشِ بعدی."""
    import time as _t
    import urllib.error
    import urllib.request
    if not name:
        name = os.path.basename(dst)
    t0 = _t.time()
    done = 0
    total = 0
    _n234 = max(1, int(attempts))
    _part234 = dst + ".part"
    _mark234 = _part234 + ".url"
    for _try234 in range(_n234):
        try:
            _start234 = 0
            if os.path.isfile(_part234):
                _same234 = False
                try:
                    with open(_mark234, "r", encoding="utf-8") as _mf234:
                        _same234 = _mf234.read().strip() == url.strip()
                except Exception:
                    _same234 = False
                if _same234:
                    _start234 = os.path.getsize(_part234)
                else:
                    # بی‌نشان یا از سرورِ دیگر → الحاق ممنوع
                    try:
                        os.remove(_part234)
                    except Exception:
                        pass
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            if _start234 > 0:
                req.add_header("Range", f"bytes={_start234}-")
            with urllib.request.urlopen(req, timeout=900) as r:
                _code234 = int(r.getcode() or 200)
                _clen234 = int(r.headers.get("Content-Length") or 0)
                if _start234 > 0 and _code234 == 206:
                    # ادامهٔ همان فایلِ نیمه‌کاره از همان سرور
                    total = _start234 + _clen234
                    done = _start234
                    _mode234 = "ab"
                else:
                    # .part نبود یا سرور Range را نگرفد (200) → از صفر
                    total = _clen234
                    done = 0
                    _mode234 = "wb"
                with open(_part234, _mode234) as f:
                    # نشانِ منبع — پیش از بایتهای بعدی بنویس تا شکستِ
                    # میان‌راه نشان را با خود داشته باشد
                    try:
                        with open(_mark234, "w", encoding="utf-8") as _mf234:
                            _mf234.write(url)
                    except Exception:
                        pass
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
                        done += len(chunk)
                        _dl_progress(name, done, total)
            if total and done < total:
                raise RuntimeError(f"ناقص: {done}/{total} بایت")
            break
        except Exception as _e234:
            if isinstance(_e234, urllib.error.HTTPError) \
                    and int(getattr(_e234, "code", 0) or 0) == 416 \
                    and os.path.isfile(_part234):
                # .part از قبل کامل/بی‌اعتبار است → دورش بریز و تازه بگیر
                for _del234 in (_part234, _mark234):
                    try:
                        if os.path.isfile(_del234):
                            os.remove(_del234)
                    except Exception:
                        pass
            if _try234 + 1 < _n234:
                print(f"\n    [!] {name}: قطع شد ({_e234}) → "
                      f"تلاشِ {_try234 + 2}/{_n234} از همان‌جا ...")
                _t.sleep(2.0)
                continue
            raise
    if os.path.isfile(_part234) and os.path.getsize(_part234) > 1000:
        dt = _t.time() - t0
        print(f"\r    ✔ {name}: {_fmt_mb(done)} در {dt:.0f}s" + " " * 8)
        os.replace(_part234, dst)
        try:
            if os.path.isfile(_mark234):
                os.remove(_mark234)
        except Exception:
            pass
        return dst
    raise RuntimeError("فایل ناقص")


def _model_cache_dir(sub):
    d = os.path.join(os.environ.get("MANGA_FILES_DIR") or os.getcwd(), sub)
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d


def _mirror_model(fname):
    loc = os.path.join(_model_cache_dir("det_models"), fname)
    if os.path.isfile(loc) and os.path.getsize(loc) > 1000:
        return loc
    try:
        print(f"    [mirror] {fname} ...")
        _dl_to(_RAPIDOCR_MIRROR + fname, loc)
        return loc
    except Exception as e:
        print(f"    [!] mirror نشد: {e}")
        # v1.14.234 — .part «حفظ» میشود تا دانلودِ بعدی با Range از
        # همان‌جا ادامه یابد (قبلاً حذف میشد و 121MBِ نیمه‌کاره دور
        # ریخته میشد).
        return None




# v1.14.162 — قفلِ تک‌نمونهٔ دانلودِ هر فایل: دو ورکرِ همزمان که همان
# فایلِ مدل را میخواهند، هر دو «همان فایل را دانلود میکردند»؛ یکی تمام
# میشد و .part را rename میکرد، دومی وسطِ نوشتن/rename با «[Errno 2] No such
# file or directory … .part» میرفت و لاگِ «دانلود ناموفق — اینترنت/VPN
# را چک کن» میداد در حالیکه فایل سالم بود. حالا هر فایل قفلِ خودش را
# دارد؛ نفرِ دوم منتظر میماند و بعد داخلِ قفل «از قبل هست» را میبیند.
_DL_FILE_LOCKS: Dict[str, threading.Lock] = {}
_DL_FILE_LOCKS_GUARD = threading.Lock()


def _dl_file_lock(dst: str) -> threading.Lock:
    with _DL_FILE_LOCKS_GUARD:
        lk = _DL_FILE_LOCKS.get(dst)
        if lk is None:
            lk = threading.Lock()
            _DL_FILE_LOCKS[dst] = lk
        return lk


def _ensure_rapidocr_models(mdir, files=None):
    wanted = files or list(_RAPIDOCR_FILES)
    for fname in wanted:
        dst = os.path.join(mdir, fname)
        # v1.14.152 — فایلهایِ dict (txt) کوچکاند (47-75KB)؛ آستانهٔ
        # 100KB فقط برایِ مدلهاست وگرنه dict هر بار دوباره دانلود میشد.
        _min_sz = 100 if fname.endswith(".txt") else 100_000
        if os.path.isfile(dst) and os.path.getsize(dst) > _min_sz:
            continue
        done = False
        _lk = _dl_file_lock(dst)
        with _lk:
            # داخلِ قفلِ همان فایل دوباره چک کن — شاید ورکرِ دیگر همین
            # حالا آن را دانلود کرده باشد (ریشهٔ ارورِ .part)
            if os.path.isfile(dst) and os.path.getsize(dst) > _min_sz:
                continue
            for url in (_RAPIDOCR_MIRROR + fname, _RAPIDOCR_FILES.get(fname)):
                if not url:
                    continue
                try:
                    print(f"  دانلود {fname} ...")
                    _dl_to(url, dst, name=fname)
                    done = True
                    break
                except Exception as e:
                    # اگر ورکرِ دیگر فایل را تمام کرده، این شکست نیست
                    if os.path.isfile(dst) and os.path.getsize(dst) > _min_sz:
                        done = True
                        break
                    host = url.split("/")[2] if url else "?"
                    print(f"  [!] {fname} از {host} نشد: {e}")
            if not done:
                print(f"  [!] دانلود {fname} ناموفق — اینترنت/VPN را چک کن "
                      "(دانلودِ بعدی از همان‌جا ادامه مییابد)")
            # v1.14.234 — .part حفظ میشود (ادامهٔ دانلود با Range)


