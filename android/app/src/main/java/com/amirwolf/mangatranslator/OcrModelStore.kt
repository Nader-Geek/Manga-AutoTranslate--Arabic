// v1.14.189 — دانلودِ زمانِ اجرایِ مدلهایِ OCRِ گوشی
// دستورِ سازنده (نقلِ مستقیم):
//   «onnx تو گوشی واسه استخراج با نصب نیاد تو خوده اپ دانلود کنه اوکی
//    کنه حجم اپ زیاد میشه  به حساب زبان انتخاب شده همون مدل دانلود کنه
//    مثال انگلیسی onnx  مال انگلیسی بگیره چینی مال چینی onnx استخراج
//    میگما و مثاله همشو یک جا دانلود نزنه»
//
// طراحی:
//   • APK دیگر هیچ مدلِ OCRی باندل نمیکند (build.yml مرحلهٔ Fetch فقط
//     برای تستِ شبیهساز با فلگ میآید) — حجمِ APK حدودِ ۱۱۵MB سبکتر.
//   • منبعِ دانلود = ریلیزِ «models»ِ همین ریپو (همان آینهٔ سریعِ
//     ایرانِ LaMa/detector — fetch_models.yml نگهدارش میکند).
//   • چیدمانِ مقصد = filesDir/models/{det,cls,rec,rec_ja,rec_ko}/…
//     (عینِ چیدمانِ assetsِ قبلی) — ppocr-sdk با ModelSource از همان
//     مسیرِ نسبی میخواند (assets یا filesDir — هرکدام بود).
//   • به حسابِ زبانِ انتخابی: det/cls/recِ پیشفرض یکبار؛ recِ ja/ko فقط
//     وقتی زبانِ انتخابی/کراپِ همان زبان رسید (اگ نبود دانلود میکند).
//   • خطِ آخرِ تلاش: اگر فایل از قبل (نسخهٔ باندلِ قدیمِ v1.14.188
//     ارتقایافته) در filesDir کپی شده باشد، دست نزدہ استفاده میشود.

package com.amirwolf.mangatranslator

import android.content.Context
import android.util.Log
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL

object OcrModelStore {

    private const val TAG = "OcrModelStore"

    // آینهٔ رسمیِ همین ریپو (fetch_models.yml همینها را آپلود میکند)
    private const val BASE =
        "https://github.com/amirwolf512k/Manga-AutoTranslate/releases/download/models/"

    // مسیرِ نسبی → فایلِ ریلیز (+ حداقلِ حجمِ سالم به بایت)
    private val FILES: Map<String, Pair<String, Long>> = mapOf(
        "models/det/inference.onnx" to ("PP-OCRv6_det_small.onnx" to 8_000_000L),
        "models/cls/inference.onnx" to ("ch_ppocr_mobile_v2.0_cls_mobile.onnx" to 300_000L),
        "models/rec/inference.onnx" to ("PP-OCRv6_medium_rec_onnx.onnx" to 60_000_000L),
        "models/rec/dict.txt" to ("ppocrv6_chars.txt" to 60_000L),
        "models/rec_ja/inference.onnx" to ("japan_PP-OCRv4_rec_mobile.onnx" to 7_000_000L),
        "models/rec_ja/dict.txt" to ("japan_dict.txt" to 10_000L),
        "models/rec_ko/inference.onnx" to ("korean_PP-OCRv4_rec_mobile.onnx" to 15_000_000L),
        "models/rec_ko/dict.txt" to ("korean_dict.txt" to 10_000L),
    )

    /** واریانتهایِ زبان — هم‌قراردادِ LANG_VARIANTSِ PaddleOcrBridge. */
    val VARIANT_JA = listOf("models/rec_ja/inference.onnx", "models/rec_ja/dict.txt")
    val VARIANT_KO = listOf("models/rec_ko/inference.onnx", "models/rec_ko/dict.txt")

    /** اتریبیوتِ «گوشی» که اگر بازِ دانلود در جریان است. */
    @Volatile
    var busyInfo: String = ""
        private set

    /**
     * مسیرهایِ لازم برایِ زبانِ انتخابی. زبانِ لاتین/چینی/ناشناخته =
     * فقط ستِ پیشفرض (v6_medium؛ چینی و لاتین داخلش هست) — «همشو یکجا
     * دانلود نزنه»: ja/ko فقط با خودِ زبانشان میآیند.
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
            "ja", "japanese", "jpn" -> base + VARIANT_JA
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

    /**
     * هر مسیرِ غایب را دانلود میکند (اگ نبود). بقیه دستنخورده.
     * مسیرِ اولِ غایب که تمام شد ادامه میدهد تا لیست کامل شود؛
     * خطایِ دانلود → Exception با پیامِ فارسیِ روشن (bridge لاگ میکند).
     */
    @JvmStatic
    @Synchronized
    fun ensure(context: Context, relPaths: List<String>) {
        var lastErr: Throwable? = null
        for (rel in relPaths) {
            if (exists(context, rel)) continue
            val spec = FILES[rel] ?: continue // مسیرِ ناشناخته = باندلِ آینده
            try {
                download(context, rel, spec.first, spec.second)
            } catch (t: Throwable) {
                lastErr = t
                Log.e(TAG, "download failed: $rel", t)
                break // شبکه نیست — بقیه را هم بلاکردن بیهوده است
            }
        }
        lastErr?.let {
            throw RuntimeException(
                "دانلودِ مدلِ OCR ناموفق بود — اینترنت را چک کن و دوباره امتحان کن: "
                        + (it.message ?: it.javaClass.simpleName), it)
        }
    }

    private fun download(context: Context, rel: String, asset: String, minSize: Long) {
        val dst = File(context.filesDir, rel)
        dst.parentFile?.mkdirs()
        val part = File(dst.parentFile, dst.name + ".part")
        busyInfo = rel
        Log.i(TAG, "downloading $asset → ${dst.path}")
        println("[دانلود] مدلِ استخراج: $asset …")
        val url = BASE + asset
        var conn: HttpURLConnection? = null
        try {
            conn = (URL(url).openConnection() as HttpURLConnection).apply {
                connectTimeout = 20_000
                readTimeout = 60_000
                instanceFollowRedirects = true
                setRequestProperty("User-Agent", "Manga-AutoTranslate/1.14.189")
            }
            val code = conn.responseCode
            if (code != 200) {
                throw RuntimeException("HTTP $code برای $asset")
            }
            val total = conn.contentLengthLong
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
                                Log.i(TAG, "download $asset: $pct%")
                                println("[دانلود] $asset: $pct%")
                            }
                        }
                    }
                    out.flush()
                    if (part.length() < minSize) {
                        throw RuntimeException(
                            "فایلِ ناقص: ${part.length()} < $minSize برای $asset")
                    }
                }
            }
            if (dst.exists()) dst.delete()
            if (!part.renameTo(dst)) {
                throw RuntimeException("rename نشد: $part → $dst")
            }
            Log.i(TAG, "ready: ${dst.path} (${dst.length()} bytes)")
            println("[✔] مدلِ استخراج آماده شد: $asset")
        } finally {
            busyInfo = ""
            try { conn?.disconnect() } catch (_: Throwable) {}
            if (part.exists() && !dst.exists()) part.delete()
        }
    }
}
