// v1.14.188 — پلِ استخراجِ متنِ گوشی = RapidOCRِ اندروید (ONNXِ خالص)
// دستورِ سازنده (۱۴.۱۸۸): «چرت پرت هم زیاد استخراج میکنه … همون مدل
// onnx v6 ocr … مدل v6_medium استفاده کن» → det = PP-OCRv6_small
// (همان detِ PC) + rec = PP-OCRv6_MEDIUM (charsetِ ۱۸۷۰۸ی؛ ورودیِ
// ۴۸×W — بدونِ تغییرِ RecPreprocessor/CTCDecoder). بنچمارکِ img6:
// فاصلههایِ درست، «Wha!?» به‌جایِ «ijeym»، حذفِ خطاهایِ حرفیِ v4.
// (تاریخچهٔ ۱۴.۱۸۷ = سهگانهٔ PP-OCRv4_mobile)
// ═══════════════════════════════════════════════════════════════════════
// دستورِ سازنده (v1.14.187 — نقلِ مستقیم):
//   «متن درست استخراج نمیزنه متن هاش اشتباهه بعضی وقتا ۱.۱۴.۱۸۶
//    https://github.com/RapidAI/RapidOcrAndroidOnnx ببین چجور به این
//    خوبی استخراج میکنه همونو رو گوشی بزار … این خیلی خوب استخراج میزنه
//    متن هاش خوب در میاره فقط مشکلش این ک همه زبانس نمیشه یک زبان
//    انتخاب کرد مثلا انگلیسی بزارم»
//
//   • موتور = سهگانهٔ RapidOcrAndroidOnnx داخلِ ماژولِ ppocr-sdk
//     (det: ch_PP-OCRv4_det_mobile + cls: ch_ppocr_mobile_v2.0_cls +
//     rec: ch_PP-OCRv4_rec_mobile + دیکشنریِ متنی) — بیت‌به‌بیتِ همان
//     پیشپردازش/پسپردازش (DB dilate 2×2، clsِ 192×48، recِ ارتفاعِ ۴۸ +
//     CTCِ blank=۰) رویِ همان ORTِ 1.21.1. این پل فقط پلِ نازک است و
//     هیچ ORT/پردازشی از خودش ندارد (قراردادِ v1.14.184 پابرجاست).
//   • مدلها از v1.14.189 دیگر باندلِ APK نیستند (دستورِ سازنده: «onnx
//     تو گوشی واسه استخراج با نصب نیاد … اپ بزار دانلود کنه اگ نبود»):
//     اولین استفاده → OcrModelStore از ریلیزِ «models»ِ همین ریپو در
//     filesDir/models/… دانلود میکند (به حسابِ زبانِ انتخابی — ja/ko
//     فقط با خودشان) و ppocr-sdk با ModelSource از assets یا filesDir
//     میخواند (باندلِ قدیمیِ v1.14.188 هم پابرجا کار میکند):
//       models/det/inference.onnx      (PP-OCRv6_det_small 10MB)
//       models/cls/inference.onnx      (ch_ppocr_mobile_v2.0_cls 0.6MB)
//       models/rec/inference.onnx      (PP-OCRv6_MEDIUM 73MB)
//       models/rec/dict.txt            (ppocrv6_chars — ۱۸۷۰۸ سطر)
//       models/rec_ko/inference.onnx   (korean_PP-OCRv5_rec_mobile 13.5MB)
//       models/rec_ko/dict.txt         (ppocrv5_korean_dict.txt — ۱۱۹۴۵ سطر)
//   • انتخابِ زبان (خلافِ دموی RapidOcrAndroidOnnx که «همه زبان» است):
//     manga.py زبانِ هر کراپ را در recognizeAuto(png, lang, w, h)
//     میفرستد؛ این پل سشنِ rec را رویِ واریانتِ همان زبان گرم میکند:
//       latin/zh/ja/سایر → recِ پیشفرضِ v6_medium (بنچمارکِ v1.14.190:
//         صفحهٔ تستِ سازنده — medium ژاپنی را کاملتر از japan v4 میخواند:
//         «一緒にがんばりましょう»✓ در برابرِ «ましよう»✗؛ کلمهٔ
//         «かわい» فقط با medium)؛ ko→rec_ko؛ multi→پیشفرض + دوئلِ ko
//         (manga.py تصمیم میگیرد — واریانتِ ko لازمالآمد دانلود میشود)
//   • قراردادِ خروجی = همان سطرهایِ META همیشه
//     (META|lang|n + ang|conf|box|text|blk) تا manga.py
//     (PaddleAndroidOCR) بدونِ تغییرِ پارسر وصل شود.
//   • thread-safety: همهٔ recognizeها با یک قفل سری میشوند (کرانکِ
//     OCRِ پایتون چندکارگری است) — تعویضِ زبان هم زیرِ همان قفل.
// ═══════════════════════════════════════════════════════════════════════

package com.amirwolf.mangatranslator

import android.content.Context
import android.util.Log
import com.paddle.ocr.EngineConfig
import com.paddle.ocr.RapidOcr
import com.paddle.ocr.util.OpenCVUtils
import kotlinx.coroutines.runBlocking

object PaddleOcrBridge {

    private const val TAG = "PaddleOcrBridge"

    // مسیرهایِ assets — عینِ چیدمانِ v1.14.184 (build.yml مدلها را همینجا
    // میریزد) + cls و واریانتهایِ زبانِ جدیدِ v1.14.187
    private const val DET_ASSET = "models/det/inference.onnx"
    private const val CLS_ASSET = "models/cls/inference.onnx"
    private const val REC_ASSET = "models/rec/inference.onnx"
    private const val REC_DICT_ASSET = "models/rec/dict.txt"

    // واریانتهایِ زبانِ rec — v1.14.190: همهٔ زبانها recِ پیشفرضِ
    // v6_medium را میگیرند (ja هم — بنچمارکِ صفحهٔ تستِ سازنده)؛ فقط
    // ko سشن عوض میکند (v6 هیچ هانگولی در charset ندارد — ۰ از ۱۸۷۰۸)
    private val LANG_VARIANTS: Map<String, Pair<String, String>> = mapOf(
        "ko" to ("models/rec_ko/inference.onnx" to "models/rec_ko/dict.txt"),
    )

    /** واریانتِ پیشفرض (PP-OCRv6_MEDIUM — latin/zh هم داخلش هست). */
    private val DEFAULT_VARIANT: Pair<String, String> =
        REC_ASSET to REC_DICT_ASSET

    @Volatile
    private var engine: RapidOcr? = null

    @Volatile
    private var ctx: Context? = null

    @Volatile
    private var currentVariant: String = "ch"

    private val lock = Any()

    /** MtApp در onCreateِ کلِ اپ این را صدا میزند (قبل از هر Activity). */
    @JvmStatic
    fun hold(context: Context) {
        // Context فقط برایِ سازندهٔ موتور لازم است — همینجا نگهش میداریم
        // تا init() بدونِ پارامترِ Context از پایتون صدا شود.
        if (ctx == null) ctx = context.applicationContext
    }

    /**
     * v1.14.188 — ساختِ موتورِ RapidOCR (detِ v6_small + recِ v6_MEDIUM).
     * [numThreads] = EngineConfig.numThreads (پیشفرض ۴).
     * true = موتور آماده است؛ false = هیچ فالبکی نیست — manga.py
     * استخراجِ خالی میبیند و پیامِ خطا چاپ میشود.
     */
    @JvmStatic
    fun init(numThreads: Int): Boolean = init(numThreads, null)

    /**
     * v1.14.190 — نسخهٔ زبان‌آگاه با تضمینِ همیشگیِ مدلها: حتی وقتی
     * موتور از اجرایِ قبلیِ همین پروسس گرم است، مدلهایِ زبانِ این اجرا
     * حتماً بررسی/دانلود میشوند (باگِ v1.14.189: موتورِ گرم + واریانتِ
     * غایب = خطایِ ERR|ModelDownload در سلف‌تست — «زبان چینی کره ای
     * اصلا استخراج نمیزنه ارور میده»). [primaryLang] = زبانِ انتخابیِ
     * کاربر («به حساب زبان انتخاب شده همون مدل دانلود کنه») — فقط
     * مدلهایِ همان زبان (اگ نبود) دانلود میشوند؛ نه همه با هم.
     */
    @JvmStatic
    fun init(numThreads: Int, primaryLang: String?): Boolean = synchronized(lock) {
        val context = ctx ?: run {
            Log.e(TAG, "init: MtApp هنوز Context نداده است")
            return false
        }
        try {
            // v1.14.190 — همیشه (موتورِ گرم هم): فایلهایِ زبانِ این اجرا
            OcrModelStore.ensure(context, OcrModelStore.pathsForLang(primaryLang))
        } catch (t: Throwable) {
            Log.e(TAG, "model ensure failed (lang=$primaryLang)", t)
            engine = null
            return false
        }
        if (engine != null) return true
        return try {
            // یادداشتِ رسمیِ ppocr-android: OpenCVUtils.init(context)
            // قبل از ساختِ هر موتوری (کلاسهایِ Mat/OpenCV)
            OpenCVUtils.init(context)
            val threads = numThreads.coerceIn(1, 8)
            engine = runBlocking {
                RapidOcr.create(
                    context = context,
                    engineConfig = EngineConfig(numThreads = threads),
                    detModelAssetPath = DET_ASSET,
                    clsModelAssetPath = CLS_ASSET,
                    recModelAssetPath = REC_ASSET,
                    recDictAssetPath = REC_DICT_ASSET,
                )
            }
            currentVariant = "ch"
            Log.i(TAG, "RapidOCR (RapidOcrAndroidOnnx pipeline) ready — " +
                    "PP-OCRv6 det=small rec=MEDIUM, threads=$threads")
            true
        } catch (t: Throwable) {
            Log.e(TAG, "init failed", t)
            engine = null
            false
        }
    }

    @JvmStatic
    fun ready(): Boolean = engine != null

    /**
     * زبانِ META → واریانتِ rec. zh/ناشناخته = ch (پیشفرض) — همیشه جفتِ
     * معتبر برمیگردد تا تعویضِ برگشت (مثلاً ja→zh) هم انجام شود.
     */
    private fun variantFor(lang: String): Pair<String, Pair<String, String>> {
        val key = lang.lowercase().trim()
        val variant = LANG_VARIANTS[key] ?: DEFAULT_VARIANT
        return if (LANG_VARIANTS.containsKey(key)) key to variant
        else "ch" to variant
    }

    /**
     * کراپ (PNG/JPEG) → سطرهایِ META.
     * قرارداد: سطرِ اول «META|lang|n»؛ بعد هر خطِ متن:
     *   ang|conf|x1,y1,x2,y2,x3,y3,x4,y4|text|blk
     * ang/blk همیشه 0 — چرخشِ ۱۸۰ داخلِ موتور با cls هندل میشود و
     * زاویهٔ جداگانه گزارش نمیکند.
     * هر خطا → سطرِ ERR (manga.py خروجیِ خالی میبیند — فالبکی نیست).
     */
    @JvmStatic
    fun recognizeAuto(png: ByteArray, lang: String, w: Int, h: Int):
            Array<String>? = synchronized(lock) {
        val eng = engine ?: return null
        try {
            // انتخابِ زبانِ rec — تعویضِ داغِ سشن فقط وقتی واریانت عوض شود
            val (variantKey, variant) = variantFor(lang)
            if (variantKey != currentVariant) {
                // v1.14.189 — واریانتِ زبانِ جدید اگر نبود، همینجا دانلود
                // میشود (اگ نبود) — نه همه با هم
                try {
                    ctx?.let { OcrModelStore.ensure(it, listOf(variant.first, variant.second)) }
                } catch (t: Throwable) {
                    Log.e(TAG, "variant download failed: $variantKey", t)
                    return@synchronized arrayOf("ERR|ModelDownload|" +
                            (t.message ?: "no message").replace("|", " "))
                }
                runBlocking {
                    eng.setLanguageVariant(variant.first, variant.second)
                }
                currentVariant = variantKey
                Log.i(TAG, "rec variant → $variantKey (lang=$lang)")
            }
            val res = runBlocking { eng.recognize(png) }
            val items = res.results
            val out = ArrayList<String>(items.size + 1)
            out.add("META|$lang|${items.size}")
            for (item in items) {
                val sb = StringBuilder()
                for (p in item.box.points) {
                    if (sb.isNotEmpty()) sb.append(',')
                    sb.append(fmt(p.x)).append(',').append(fmt(p.y))
                }
                val text = item.text
                    .replace("|", " ")
                    .replace("\r", " ")
                    .replace("\n", " ")
                    .trim()
                out.add("0|" + String.format(java.util.Locale.US, "%.4f",
                        item.confidence) +
                        "|" + sb + "|" + text + "|0")
            }
            out.toTypedArray()
        } catch (t: Throwable) {
            // خطا → سطرِ تشخیصیِ ERR (پارسرِ manga.py آن را مثلِ
            // خروجیِ خالی میبیند) تا سلف‌تست/لاگ، ریشه را نشان دهد
            Log.e(TAG, "recognize failed", t)
            arrayOf("ERR|" + t.javaClass.simpleName + "|" +
                    (t.message ?: "no message").replace("|", " "))
        }
    }

    /** نسخهٔ کوتاه برایِ لاگِ manga.py (کدام موتور رویِ گوشی است). */
    @JvmStatic
    fun sdkInfo(): String =
        "RapidOCR ONNX (RapidOcrAndroidOnnx pipeline) — " +
                "PP-OCRv6 (det=small + rec=MEDIUM)"

    private fun fmt(v: Float): String =
        if (v == v.toLong().toFloat()) v.toLong().toString()
        else String.format(java.util.Locale.US, "%.2f", v)
}
