// v1.14.184 — پلِ استخراجِ متنِ گوشی = SDKِ رسمیِ PaddleOCR اندروید
// ═══════════════════════════════════════════════════════════════════════
// دستورِ سازنده (نقلِ مستقیم):
//   «استفاده نکرد از onnx استخراج نزد هرروشی تو و گوشی واسه استخراج
//    شده حذف کن فقط از همین لینک بالا استفاده کنه»
// لینکِ رسمی:
//   https://www.paddleocr.ai/latest/en/version3.x/inference_deployment/
//   cross_platform/android_deployment.html
//
//   • موتورِ قبلی (پرتِ دستیِ ONNX با PP-OCRv6 medium که رویِ گوشی هیچ
//     متنی برنگرداند) کامل حذف شد — این فایل دیگر هیچ ONNX/پردازشی از
//     خودش ندارد؛ فقط یک پلِ نازک رویِ ماژولِ رسمیِ «ppocr-sdk» است که
//     بیت‌به‌بیت از PaddleOCR/deploy/ppocr-android وندور شده:
//     DetPreprocessor → DBPostProcessor → QuadTextCrop →
//     RecPreprocessor → CTCDecoder (کدِ com.paddle.ocr رسمی).
//   • مدلها = رسمیِ PP-OCRv6_small (det 9.9MB + rec 21.2MB +
//     inference.yml) باندلشده در assets/models/{det,rec}/ — زمانِ بیلدِ
//     CI از HuggingFaceِ رسمی دانلود میشوند؛ رویِ گوشی هیچ دانلودِ
//     زمانِ اجرایی در کار نیست و آفلاین هم کار میکند.
//   • شکلِ پیکربندی = عینِ بخشِ «SDK Integration» READMEِ رسمی:
//     PaddleOCR.create(context, PaddleOCRConfig(), EngineConfig(threads),
//     "models/det/inference.onnx", "models/rec/inference.onnx",
//     "models/rec/inference.yml") + OpenCVUtils.init(context).
//   • قراردادِ خروجی = همان سطرهایِ META همیشه
//     (META|lang|n + ang|conf|box|text|blk) تا manga.py
//     (PaddleAndroidOCR) بدونِ تغییرِ پارسر وصل شود.
//   • thread-safety: SDKِ رسمی در هر run ماتریسهایِ خودش را میسازد؛
//     برایِ حذفِ هر رقابتِ احتمالی، همهٔ recognizeها با یک قفل
//     سری میشوند (کرانکِ OCRِ پایتون چندکارگری است).
// ═══════════════════════════════════════════════════════════════════════

package com.amirwolf.mangatranslator

import android.content.Context
import android.util.Log
import com.paddle.ocr.EngineConfig
import com.paddle.ocr.PaddleOCR
import com.paddle.ocr.PaddleOCRConfig
import com.paddle.ocr.util.OpenCVUtils
import kotlinx.coroutines.runBlocking

object PaddleOcrBridge {

    private const val TAG = "PaddleOcrBridge"

    // مسیرهایِ رسمیِ READMEِ ppocr-android (بخشِ «SDK Integration»)
    private const val DET_ASSET = "models/det/inference.onnx"
    private const val REC_ASSET = "models/rec/inference.onnx"
    private const val REC_YML_ASSET = "models/rec/inference.yml"

    @Volatile
    private var engine: PaddleOCR? = null

    @Volatile
    private var ctx: Context? = null

    private val lock = Any()

    /** MtApp در onCreateِ کلِ اپ این را صدا میزند (قبل از هر Activity). */
    @JvmStatic
    fun hold(context: Context) {
        // Context فقط برایِ سازندهٔ SDK لازم است — همینجا نگهش میداریم
        // تا init() بدونِ پارامترِ Context از پایتون صدا شود.
        if (ctx == null) ctx = context.applicationContext
    }

    /**
     * v1.14.184 — ساختِ موتورِ رسمی (PP-OCRv6_smallِ باندل).
     * [numThreads] = EngineConfig.numThreadsِ رسمی (پیشفرضِ رسمی ۴).
     * true = موتورِ رسمی آماده است؛ false = هیچ فالبکی نیست — manga.py
     * استخراجِ خالی میبیند و پیامِ خطا چاپ میشود.
     */
    @JvmStatic
    fun init(numThreads: Int): Boolean = synchronized(lock) {
        if (engine != null) return true
        val context = ctx ?: run {
            Log.e(TAG, "init: MtApp هنوز Context نداده است")
            return false
        }
        return try {
            // یادداشتِ رسمیِ README: «Call OpenCVUtils.init(context)
            // before PaddleOCR.create()»
            OpenCVUtils.init(context)
            val threads = numThreads.coerceIn(1, 8)
            engine = runBlocking {
                PaddleOCR.create(
                    context = context,
                    config = PaddleOCRConfig(),
                    engineConfig = EngineConfig(numThreads = threads),
                    detModelAssetPath = DET_ASSET,
                    recModelAssetPath = REC_ASSET,
                    recConfigAssetPath = REC_YML_ASSET,
                )
            }
            Log.i(TAG, "PaddleOCR SDK (official ppocr-android) ready — " +
                    "PP-OCRv6_small, threads=$threads")
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
     * کراپ (PNG/JPEG) → سطرهایِ META.
     * قرارداد: سطرِ اول «META|lang|n»؛ بعد هر خطِ متن:
     *   ang|conf|x1,y1,x2,y2,x3,y3,x4,y4|text|blk
     * ang/blk همیشه 0 — SDKِ رسمیِ v6 خودش کراپِ چرخیده را داخلِ
     * det/rec هندل میکند و زاویهٔ جداگانه گزارش نمیکند.
     * هر خطا → null (manga.py خروجیِ خالی میبیند — فالبکی نیست).
     */
    @JvmStatic
    fun recognizeAuto(png: ByteArray, lang: String, w: Int, h: Int):
            Array<String>? = synchronized(lock) {
        val eng = engine ?: return null
        try {
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
            // v1.14.184 — خطا → سطرِ تشخیصیِ ERR (پارسرِ manga.py آن را
            // مثلِ خروجیِ خالی میبیند) تا سلف‌تست/لاگ، ریشه را نشان دهد
            Log.e(TAG, "recognize failed", t)
            arrayOf("ERR|" + t.javaClass.simpleName + "|" +
                    (t.message ?: "no message").replace("|", " "))
        }
    }

    /** نسخهٔ کوتاه برایِ لاگِ manga.py (کدام SDK رویِ گوشی است). */
    @JvmStatic
    fun sdkInfo(): String = "ppocr-android SDK (official) — PP-OCRv6_small"

    private fun fmt(v: Float): String =
        if (v == v.toLong().toFloat()) v.toLong().toString()
        else String.format(java.util.Locale.US, "%.2f", v)
}
