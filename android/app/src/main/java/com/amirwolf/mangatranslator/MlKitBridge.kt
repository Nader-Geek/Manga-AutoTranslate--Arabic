// v1.14.170 — بازگشتِ MlKitBridge به‌عنوانِ «موتورِ OCRِ کراپِ گوشی»
// (دستورِ سازنده: «حذف کن بره paddle-lite ناقص استخراج میزنه ml kit بزار…
// همه زبان هارو خوب بتونه استخراج کنه»). Paddle-Lite کامل حذف شد؛ این پل
// دقیقاً مثلِ PP-OCRv6 ONNX فقط رویِ کراپهایِ detector-v4-s_int8.onnx
// از manga.py صدا زده میشود (MlKitCropOCR) — هیچ پاسِ تمامصفحهای نیست.
package com.amirwolf.mangatranslator

import android.graphics.BitmapFactory
import android.util.Log
import com.google.android.gms.tasks.Tasks
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.TextRecognizer
import com.google.mlkit.vision.text.chinese.ChineseTextRecognizerOptions
import com.google.mlkit.vision.text.japanese.JapaneseTextRecognizerOptions
import com.google.mlkit.vision.text.korean.KoreanTextRecognizerOptions
import com.google.mlkit.vision.text.latin.TextRecognizerOptions as LatinTextRecognizerOptions


object MlKitBridge {

    private const val TAG = "MlKitBridge"

    // v1.14.143 — کشِ هر چهارِ کلاینت (لاتین/جا/کو/ژ). قبلاً فقط «یک» کلاینت
    // کش میشد و هر تعویضِ زبان close+ساختِ مجدد میخواست؛ حالا همه باندلشده
    // در APK هستند و نگهداشتنشان حافظهای نیست (مدلها از قبل لود شدهاند).
    private val clients = HashMap<String, TextRecognizer>()

    // چسبندگیِ زبان (الگویِ script-id کِی۳): وقتیِ زبانِ یک صفحه قفل شد،
    // تا ۴۸ برشِ بعدی مستقیم با همان کلاینت میرویم — بدونِ گذرِ کشف.
    private const val REMEMBER_MAX = 48
    private var rememberedLang: String? = null
    private var rememberLeft = 0

    @Synchronized
    private fun getClient(lang: String): TextRecognizer {
        val cur = clients[lang]
        if (cur != null) return cur
        val opts = when (lang) {
            "ja" -> JapaneseTextRecognizerOptions.Builder().build()
            "ko" -> KoreanTextRecognizerOptions.Builder().build()
            "zh" -> ChineseTextRecognizerOptions.Builder().build()
            else -> LatinTextRecognizerOptions.Builder().build()
        }
        val c = TextRecognition.getClient(opts)
        clients[lang] = c
        return c
    }

    // بازههایِ یونیکد: کانا (هیراگانا/کاتاکانا/نیمعرض)، هانگول، هان
    private fun isKana(cp: Int): Boolean =
        (cp in 0x3040..0x30FF) || (cp in 0x31F0..0x31FF) || (cp in 0xFF66..0xFF9D)

    private fun isHangul(cp: Int): Boolean =
        (cp in 0xAC00..0xD7A3) || (cp in 0x1100..0x11FF) || (cp in 0x3130..0x318F)

    private fun isHan(cp: Int): Boolean =
        (cp in 0x2E80..0x2EFF) || (cp in 0x3400..0x4DBF) || (cp in 0x4E00..0x9FFF) ||
                (cp in 0xF900..0xFAFF) || (cp in 0x20000..0x2FA1F)

    private fun linesOf(lang: String, img: InputImage): ArrayList<String> {
        val result = Tasks.await(getClient(lang).process(img))
        val out = ArrayList<String>()
        // v1.14.121 — شمارهٔ بلوکِ ML Kit هم پاس داده می‌شود (فیلدِ پنجم در انتهایِ هر خط).
        // موتورِ K3 جداسازیِ حباب‌ها را از همین layout-analysisِ نیتیو میگیرد (هر حباب = یک
        // TextBlock)؛ قبلاً بلوک‌ها صاف می‌شدند و دو حبابِ چسبیده در یک باکسِ detector متنِ درهم
        // میداد. فرمت: ang|conf|box|text|blk
        var blk = -1
        for (block in result.textBlocks) {
            blk++
            for (line in block.lines) {
                val t = line.text.trim()
                if (t.isEmpty()) continue
                val bb = line.boundingBox ?: continue
                val conf = try {
                    val c = line.confidence
                    if (c != null && c > 0f) c else 1.0f
                } catch (_: Exception) {
                    1.0f
                }
                val cps = try { line.cornerPoints } catch (_: Exception) { null }
                val box = if (cps != null && cps.size == 4) {
                    val cxp = (cps[0].x + cps[1].x + cps[2].x + cps[3].x) / 4f
                    val cyp = (cps[0].y + cps[1].y + cps[2].y + cps[3].y) / 4f
                    val sorted = cps.sortedBy { p ->
                        val dx = p.x - cxp
                        val dy = p.y - cyp
                        Math.atan2(dy.toDouble(), dx.toDouble())
                    }
                    (0 until 4).joinToString(",") { k ->
                        val p = sorted[k]
                        "" + p.x.toInt() + "," + p.y.toInt()
                    }
                } else {
                    ("" + bb.left + "," + bb.top + "," +
                            bb.right + "," + bb.top + "," +
                            bb.right + "," + bb.bottom + "," +
                            bb.left + "," + bb.bottom)
                }
                val ang = try { line.angle } catch (_: Exception) { 0f }
                out.add(String.format("%.2f|%.4f|%s|%s|%d",
                        ang, conf, box, t, blk))
            }
        }
        return out
    }

    private fun tryLines(lang: String, img: InputImage): ArrayList<String>? =
        try {
            val ls = linesOf(lang, img)
            if (ls.isEmpty()) null else ls
        } catch (e: Exception) {
            Log.i(TAG, "tryLines($lang): ${e.message}")
            null
        }

    /** رأیِ اسکریپت رویِ متنِ خروجی: کانا=ژاپنیِ قطعی، هانگول=کره‌ایِ قطعی،
     *  هانِ خالص (بدونِ کانا)=چینی؛ اگر هیچکدام نبود و ~همهِ نویسهها ASCII
     *  بودند → لاتین (صفحهٔ انگلیسی). */
    private fun voteOf(lines: List<String>): String? {
        var kana = 0; var hangul = 0; var han = 0
        var ascii = 0; var total = 0
        for (item in lines) {
            val t = item.split("|", limit = 5).getOrNull(3) ?: continue
            var i = 0
            val n = t.length
            while (i < n) {
                val cp = t.codePointAt(i)
                i += Character.charCount(cp)
                total++
                when {
                    isKana(cp) -> kana++
                    isHangul(cp) -> hangul++
                    isHan(cp) -> han++
                    cp in 0x30..0x7A -> ascii++
                }
            }
        }
        if (kana >= 1) return "ja"
        if (hangul >= 1) return "ko"
        if (han >= 2) return "zh"
        if (total > 0 && ascii * 100 / total >= 80) return "latin"
        return null
    }

    private fun meta(lang: String, lines: List<String>): Array<String> {
        val out = ArrayList<String>(lines.size + 1)
        out.add("META|$lang|${lines.size}")
        out.addAll(lines)
        return out.toTypedArray()
    }

    private fun remember(lang: String) {
        rememberedLang = lang
        rememberLeft = REMEMBER_MAX
    }

    @JvmStatic
    @Synchronized
    fun recognize(png: ByteArray, lang: String): Array<String> {
        val bmp = BitmapFactory.decodeByteArray(png, 0, png.size)
            ?: return arrayOf()
        return try {
            val img = InputImage.fromBitmap(bmp, 0)
            linesOf(lang, img).toTypedArray()
        } catch (e: Exception) {
            throw RuntimeException("ML Kit: " + (e.message ?: e.toString()), e)
        } finally {
            try {
                bmp.recycle()
            } catch (_: Exception) {
            }
        }
    }

    /** v1.14.143 — کشفِ خودکارِ اسکریپت (الگویِ کِی۳ + حافظهٔ صفحه):
     *  «هردفعه یک جور» و «ژاپنی/کره‌ای/چینی اصلا استخراج نمیشود» از جایی
     *  میآمد که با ocr_lang=en فقط کلاینتِ لاتین صدا زده میشد و مدلِ لاتین
     *  رویِ کانا/هانگول/هان یا خالی برمیگشت یا علامتِ درهم میداد.
     *  راهحل: با lang=latin و auto=1 اول کلاینتِ «ژاپنی» (باندلشده) میخواند
     *  که همهٔ اسکریپتها را میبیند؛ رأیِ کانا/هانگول/هان زبان را قطعی
     *  میکند (چینی = هانِ خالص)، صفحهٔ انگلیسی با گذرِ دومِ لاتین دقیق
     *  میشود، و زبانِ قفلشده تا ۴۸ برشِ بعدی بهیاد میماند. برشِ جوهرمندِ
     *  خالی هم بهترتیب ko→zh→latin پروب میشود. خروجی: سطرِ اولِ
     *  META|lang|n + همان فرمتِ ang|conf|box|text|blk. */
    @JvmStatic
    @Synchronized
    fun recognizeAuto(png: ByteArray, lang: String, auto: Int, hasInk: Int): Array<String> {
        val bmp = BitmapFactory.decodeByteArray(png, 0, png.size)
            ?: return arrayOf()
        try {
            val img = InputImage.fromBitmap(bmp, 0)
            // زبانِ صریحِ غیرِلاتین = رفتارِ قبلی (کلاینتِ همان زبان) + META
            if (auto != 1 || lang != "latin") {
                val ls = linesOf(lang, img)
                return if (auto == 1) meta(lang, ls) else ls.toTypedArray()
            }
            // ۱) چسبندگی: زبانِ قفلشدهٔ صفحه — یک گذرِ مستقیم
            val mem = rememberedLang
            if (mem != null && rememberLeft > 0) {
                rememberLeft--
                val ls = tryLines(mem, img)
                if (ls != null) return meta(mem, ls)
                // خالی/خطا → به کشف میرویم
            }
            // ۲) کشف: کلاینتِ ژاپنی همهٔ اسکریپتها را میخواند
            val jaLines = tryLines("ja", img)
            if (jaLines != null) {
                when (voteOf(jaLines)) {
                    "ja" -> { remember("ja"); return meta("ja", jaLines) }
                    "ko" -> {
                        val ls = tryLines("ko", img) ?: jaLines
                        remember("ko"); return meta("ko", ls)
                    }
                    "zh" -> {
                        val ls = tryLines("zh", img) ?: jaLines
                        remember("zh"); return meta("zh", ls)
                    }
                    "latin" -> {
                        // صفحهٔ انگلیسی: گذرِ دومِ لاتین (دقیقترین برایِ EN)
                        val ls = tryLines("latin", img) ?: jaLines
                        remember("latin"); return meta("latin", ls)
                    }
                    else -> {}
                }
            }
            // ۳) برشِ جوهرمندِ خالی → پروبِ ترتیبی ko→zh→latin
            if (hasInk == 1) {
                for (cand in listOf("ko", "zh", "latin")) {
                    val ls = tryLines(cand, img)
                    if (ls != null) { remember(cand); return meta(cand, ls) }
                }
            }
            // ۴) هیچ رأیی نبود ولی ژاپنی متنی برگردانده بود → همان را بده
            //    (بدونِ قفل — دفعهٔ بعد دوباره کشف میشود)
            if (jaLines != null && jaLines.isNotEmpty()) return meta("ja", jaLines)
            return meta("latin", emptyList())
        } catch (e: Exception) {
            throw RuntimeException("ML Kit: " + (e.message ?: e.toString()), e)
        } finally {
            try {
                bmp.recycle()
            } catch (_: Exception) {
            }
        }
    }
}
