// v1.14.190 — دانلودِ زمانِ اجرایِ مدلهایِ OCRِ گوشی
// دستورِ سازنده (نقلِ مستقیم):
//   «onnx تو گوشی واسه استخراج با نصب نیاد تو خوده اپ دانلود کنه اوکی
//    کنه حجم اپ زیاد میشه  به حساب زبان انتخاب شده همون مدل دانلود کنه
//    مثال انگلیسی onnx  مال انگلیسی بگیره چینی مال چینی onnx استخراج
//    میگما و مثاله همشو یک جا دانلود نزنه»
// v1.14.190 — دستورِ جدید:
//   «وقتی داره onnx دانلود میزنه نشون نمیده تو لاگش چقدر دانلود شده»
//   → پیشرفتِ دانلود (٪ + MB) از طریقِ OcrProgressSink به لاگِ اپ
//   (خروجیِ پایتون) میرود؛ خطا هم دقیق (404/اتصال/ناقص) گزارش میشود
//   و هر فایل ۳ تلاش میشود.
//   «زبان چینی کره ای اصلا استخراج نمیزنه ارور میده» → مدلِ کره‌ای =
//   korean_PP-OCRv5_rec_mobile.onnx + دیکشنریِ رسمیِ خودش
//   ppocrv5_korean_dict.txt (۱۱۹۴۵ نویسه — C=۱۱۹۴۷ عینِ خروجیِ مدل؛
//   جفتِ قبلیِ v4+کره‌ایِدیکشنریِ۳۶۸۷ی غلط بود و onnxِ v4 هم رویِ سرور
//   ۴۰۴ میداد).
//   «دکمه چند زبانه خودش همه زبان هارو استخراج میزنه» → زبانِ «multi»
//   فقط ستِ پایه را میگیرد (recِ v6_medium خودش ja/zh/en را میخواند —
//   بنچمارکِ صفحهٔ تستِ سازنده: v6medium از japan v4 بهتر میخواند)؛
//   واریانتِ ko فقط وقتی متنِ کره‌ای واقعاً دیده شود دانلود میشود
//   (دوئلِ اطمینان در PaddleAndroidOCR — manga.py).
//
// طراحی:
//   • APK هیچ مدلِ OCRی باندل نمیکند — حجمِ APK حدودِ ۱۱۵MB سبکتر.
//   • منبعِ دانلود = ریلیزِ «models»ِ همین ریپو (آینهٔ سریعِ ایران).
//   • چیدمانِ مقصد = filesDir/models/{det,cls,rec,rec_ko}/…
//     ppocr-sdk با ModelSource از همان مسیرِ نسبی میخواند.
//   • به حسابِ زبانِ انتخابی: det/cls/recِ پیشفرض یکبار؛ recِ ko فقط
//     برایِ کره‌ای/چندزبانه‌وقتی-کره‌ای-دید (اگ نبود دانلود میکند).

package com.amirwolf.mangatranslator

import android.content.Context
import android.util.Log
import com.paddle.ocr.util.OcrProgressSink
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.net.HttpURLConnection
import java.net.SocketTimeoutException
import java.net.URL
import java.util.Locale

object OcrModelStore {

    private const val TAG = "OcrModelStore"

    // آینهٔ رسمیِ همین ریپو (fetch_models.yml همینها را آپلود میکند)
    private const val BASE =
        "https://github.com/amirwolf512k/Manga-AutoTranslate/releases/download/models/"

    // مسیرِ نسبی → فایلِ ریلیز (+ حداقلِ حجمِ سالم به بایت)
    // v1.14.190 — واریانتِ ja حذف شد: recِ پیشفرضِ v6_medium ژاپنی را
    // بهتر از japan_PP-OCRv4 میخواند (عکسِ تستِ سازنده: «一緒にがんばり
    // ましょう»✓ در برابرِ «ましよう»✗ + «かわい» فقط با medium) → ژاپنی
    // دیگر دانلودِ اضافه ندارد.
    private val FILES: Map<String, Pair<String, Long>> = mapOf(
        "models/det/inference.onnx" to ("PP-OCRv6_det_small.onnx" to 8_000_000L),
        "models/cls/inference.onnx" to ("ch_ppocr_mobile_v2.0_cls_mobile.onnx" to 300_000L),
        "models/rec/inference.onnx" to ("PP-OCRv6_medium_rec_onnx.onnx" to 60_000_000L),
        "models/rec/dict.txt" to ("ppocrv6_chars.txt" to 60_000L),
        "models/rec_ko/inference.onnx" to ("korean_PP-OCRv5_rec_mobile.onnx" to 12_000_000L),
        "models/rec_ko/dict.txt" to ("ppocrv5_korean_dict.txt" to 40_000L),
    )

    /** واریانتِ زبانِ کره‌ای — هم‌قراردادِ LANG_VARIANTSِ PaddleOcrBridge. */
    val VARIANT_KO = listOf("models/rec_ko/inference.onnx", "models/rec_ko/dict.txt")

    /** اتریبیوتِ «گوشی» که اگر بازِ دانلود در جریان است. */
    @Volatile
    var busyInfo: String = ""
        private set

    @Volatile
    private var progressSink: OcrProgressSink? = null

    /**
     * v1.14.190 — manga.py قبل از init یک پیادهسازیِ پایتونیِ
     * OcrProgressSink ثبت میکند تا خطوطِ پیشرفتِ دانلود به لاگِ اپ
     * برسد (printlnِ کاتلین به آن لاگ نمیرود — دستورِ سازنده).
     */
    @JvmStatic
    fun setProgressSink(sink: OcrProgressSink?) {
        progressSink = sink
    }

    private fun mb(v: Long): String =
        String.format(Locale.US, "%.1f", v / 1048576.0)

    private fun emit(line: String) {
        Log.i(TAG, line)
        println(line)
        try {
            progressSink?.onProgress(line)
        } catch (_: Throwable) {
        }
    }

    /**
     * مسیرهایِ لازم برایِ زبانِ انتخابی. «به حساب زبان انتخاب شده»:
     *   • en/latin/fa/zh/ja/… → فقط ستِ پایه (v6_medium — ja و zh و
     *     latin داخلش هست؛ بنچمارکِ صفحهٔ تستِ سازنده).
     *   • ko/korean → ستِ پایه + واریانتِ کره‌ایِ v5.
     *   • multi (چندزبانه) → فقط ستِ پایه — واریانتِ ko بعداً «فقط
     *     وقتی متنِ کره‌ای دید» لازمالآمد دانلود میشود («همشو یکجا
     *     دانلود نزنه»).
     */
    @JvmStatic
    fun pathsForLang(lang: String?): List<String> {
        val l = (lang ?: "").lowercase().trim()
        val base = listOf(
            "models/det/inference.onnx",
            "models/cls/inference.onnx",
            "models/rec/inference.onnx",
            "models/rec/dict.txt",
        )
        return when (l) {
            "ko", "korean", "kor" -> base + VARIANT_KO
            else -> base
        }
    }

    private fun exists(context: Context, rel: String): Boolean {
        val f = File(context.filesDir, rel)
        if (f.isFile && f.length() > 0L) return true
        return try {
            context.assets.open(rel).use { true }
        } catch (_: Throwable) {
            false
        }
    }

    private fun describe(t: Throwable, asset: String): String = when {
        t is ModelHttpError && t.code == 404 ->
            "فایل «$asset» رویِ سرور پیدا نشد (HTTP 404) — مدلِ این نسخه در ریلیز نیست"
        t is ModelHttpError ->
            "سرورِ مدلها خطا داد (HTTP ${t.code}) برایِ «$asset»"
        t is SocketTimeoutException ->
            "اتصال به سرورِ مدلها طول کشید (تایمآوت) برایِ «$asset»"
        t is IOException ->
            "اتصال به سرورِ مدلها ممکن نشد (اینترنت/فیلترشکن؟) برایِ «$asset»"
        else -> (t.message ?: t.javaClass.simpleName) + " — «$asset»"
    }

    /**
     * هر مسیرِ غایب را دانلود میکند (اگ نبود). هر فایل حداکثر ۳ تلاش
     * (شبکهٔ ناپایدار = خطایِ رایج — v1.14.190). خطا با توضیحِ دقیق
     * بالا میرود (پلِ Kotlin لاگ میکند).
     */
    @JvmStatic
    @Synchronized
    fun ensure(context: Context, relPaths: List<String>) {
        var missing = 0
        var lastErr: Throwable? = null
        var lastAsset = ""
        for (rel in relPaths) {
            if (exists(context, rel)) continue
            val spec = FILES[rel] ?: continue // مسیرِ ناشناخته = باندلِ آینده
            missing++
            var ok = false
            for (attempt in 1..3) {
                try {
                    download(context, rel, spec.first, spec.second)
                    ok = true
                    break
                } catch (t: Throwable) {
                    lastErr = t
                    lastAsset = spec.first
                    Log.e(TAG, "download failed (attempt $attempt/3): $rel", t)
                    if (t is ModelHttpError && t.code == 404) break // تلاشِ دوباره بیهوده
                    if (attempt < 3) {
                        emit("[!] دانلودِ ${spec.first} ناموفق بود — تلاشِ دوباره ($attempt/3)…")
                        try {
                            Thread.sleep(if (attempt == 1) 1500L else 4000L)
                        } catch (_: InterruptedException) {
                        }
                    }
                }
            }
            if (!ok) break // شبکه/سرور نیست — بقیه را هم بلاکردن بیهوده است
        }
        if (missing == 0) {
            emit("[*] مدلهایِ OCR از قبل آمادهاند — دانلودی لازم نبود.")
            return
        }
        lastErr?.let {
            throw RuntimeException(
                "دانلودِ مدلِ OCR ناموفق بود — " + describe(it, lastAsset), it)
        }
    }

    private class ModelHttpError(val code: Int, msg: String) : RuntimeException(msg)

    private fun download(context: Context, rel: String, asset: String, minSize: Long) {
        val dst = File(context.filesDir, rel)
        dst.parentFile?.mkdirs()
        val part = File(dst.parentFile, dst.name + ".part")
        busyInfo = rel
        val url = BASE + asset
        var conn: HttpURLConnection? = null
        val t0 = System.currentTimeMillis()
        try {
            conn = (URL(url).openConnection() as HttpURLConnection).apply {
                connectTimeout = 20_000
                readTimeout = 60_000
                instanceFollowRedirects = true
                setRequestProperty("User-Agent", "Manga-AutoTranslate/1.14.190")
            }
            val code = conn.responseCode
            if (code != 200) {
                throw ModelHttpError(code, "HTTP $code برای $asset")
            }
            val total = conn.contentLengthLong
            if (total > 0) {
                emit("[دانلود] $asset — حجم: ${mb(total)}MB")
            } else {
                emit("[دانلود] $asset …")
            }
            conn.inputStream.use { ins ->
                FileOutputStream(part).use { out ->
                    val buf = ByteArray(1 shl 16)
                    var done = 0L
                    var lastPct = -10
                    while (true) {
                        val n = ins.read(buf)
                        if (n < 0) break
                        out.write(buf, 0, n)
                        done += n
                        if (total > 0) {
                            val pct = ((done * 100L) / total).toInt()
                            if (pct >= lastPct + 10) {
                                lastPct = pct
                                emit("[دانلود] $asset: $pct% (${mb(done)}/${mb(total)}MB)")
                            }
                        }
                    }
                    out.flush()
                    if (part.length() < minSize) {
                        throw IOException(
                            "فایلِ ناقص: ${part.length()} < $minSize برای $asset")
                    }
                }
            }
            if (dst.exists()) dst.delete()
            if (!part.renameTo(dst)) {
                throw IOException("rename نشد: $part → $dst")
            }
            val dt = (System.currentTimeMillis() - t0) / 1000.0
            Log.i(TAG, "ready: ${dst.path} (${dst.length()} bytes)")
            emit("[✔] مدلِ استخراج آماده شد: $asset (${mb(dst.length())}MB در " +
                    String.format(Locale.US, "%.1f", dt) + "ثانیه)")
        } finally {
            busyInfo = ""
            try { conn?.disconnect() } catch (_: Throwable) {}
            if (part.exists() && !dst.exists()) part.delete()
        }
    }
}
