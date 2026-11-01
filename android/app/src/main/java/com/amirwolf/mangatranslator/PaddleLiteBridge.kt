package com.amirwolf.mangatranslator

import android.util.Log
import com.baidu.paddle.lite.MobileConfig
import com.baidu.paddle.lite.PaddlePredictor
import com.baidu.paddle.lite.PowerMode
import java.nio.FloatBuffer
import java.util.concurrent.ConcurrentHashMap

/**
 * v1.14.166 — بازگشتِ پلِ Paddle-Lite (مجموعهٔ رسمیِ ppocr_demo) به‌عنوانِ
 * موتورِ OCRِ گوشی (دستورِ سازنده: «استخراجِ متن تو گوشی Paddle-Lite
 * arm arm64 بزار ببینم چجور استخراج میکنه»).
 *
 * برخلافِ سبکِ قدیمیِ K3 دیگر کاسکادی نیست؛ manga.py (PliteCropOCR)
 * پیش/پس‌پردازش را انجام میدهد و فقط «تانسور» میفرستد — و OCR فقط رویِ
 * کراپهایِ detector-v4-s_int8.onnx اجرا میشود، هرگز تمامصفحه:
 *   predict(path, shape, floatData, threads, power) → FloatBuffer خروجی
 *   predictShape(path)                             → شکلِ خروجیِ آخرِ همان مدل
 *   ready(path, threads, power)                    → ساختِ موفقِ predictor؟
 *   backend(path)                                  → "paddle-lite-cpu" یا ""
 *
 * درسهایِ کرشهایِ 1.14.106-119 (RuntimeProgram رویِ POCO F4/Adreno):
 *   ۱) مدلهایِ nb فقط-CPUاند (valid_targets=arm با optِ همان نسخهٔ
 *      v2.14-rc — بدونِ کرنلِ OpenCL) — کرنلهایِ OpenCL تنها مظنونِ
 *      سیگفالتِ قبلی بودند.
 *   ۲) قبل از هر استفاده در پروسهٔ اصلی، PliteProbeService در پروسهٔ
 *      جدا (:pliteprobe) همین مدلها را واقعاً run میکند؛ سیگفالتِ
 *      احتمالی فقط پروب را میکشد و اپِ اصلی سالم میماند (الگویِ
 *      EpProbeServiceِ v1.14.156). بنِ مدل با plite_banned.txt.
 *   ۳) لودِ صریحِ امنِ کتابخانه: اگر so نبود ready()=false → پایتون
 *      خودکار به PP-OCRv6 ONNX برمیگردد.
 */
object PaddleLiteBridge {

    private const val TAG = "PaddleLiteBridge"

    @Volatile
    private var libState: Int = -1 // 1=لود شد، 0=نبود/نشد، -1=هنوز نه

    private fun ensureLib(): Boolean {
        when (libState) {
            1 -> return true
            0 -> return false
        }
        return try {
            System.loadLibrary("paddle_lite_jni")
            libState = 1
            Log.i(TAG, "libpaddle_lite_jni loaded (cpu nb models)")
            true
        } catch (t: Throwable) {
            libState = 0
            Log.e(TAG, "libpaddle_lite_jni load failed — paddle off: "
                    + t.message)
            false
        }
    }

    /** وضعیتِ کتابخانهٔ بومی — برایِ لاگ/پروب */
    @JvmStatic
    fun libOk(): Boolean = ensureLib()

    /** نامِ فایلِ کتابخانهٔ بومی — تستِ آمادهبودن بدونِ ساختِ مدل */
    @JvmStatic
    fun libName(): String = "libpaddle_lite_jni.so"

    // کشِ predictor per-model — det و rec هرکدام یک مسیر
    private val predictors = ConcurrentHashMap<String, PaddlePredictor>()
    private val building = ConcurrentHashMap<String, Any>()
    private val lastOutShape = ConcurrentHashMap<String, LongArray>()

    private fun parsePower(p: String?): PowerMode = when (
        (p ?: "HIGH").trim().uppercase()) {
        "NO_BIND" -> PowerMode.LITE_POWER_NO_BIND
        "LOW" -> PowerMode.LITE_POWER_LOW
        "HIGH" -> PowerMode.LITE_POWER_HIGH
        else -> PowerMode.LITE_POWER_HIGH
    }

    @Synchronized
    private fun getOrCreate(modelPath: String, threads: Int,
                            power: String): PaddlePredictor? {
        if (!ensureLib()) return null
        predictors[modelPath]?.let { return it }
        // ساختِ همزمانِ دوباره را جلوگیری کن (قفلِ ساده per-path)
        synchronized(building.getOrPut(modelPath) { Any() }) {
            predictors[modelPath]?.let { return it }
            return try {
                val cfg = MobileConfig()
                cfg.setModelFromFile(modelPath)
                cfg.threads = if (threads in 1..8) threads else 2
                cfg.powerMode = parsePower(power)
                val p = PaddlePredictor.createPaddlePredictor(cfg)
                if (p != null) {
                    predictors[modelPath] = p
                    Log.i(TAG, "predictor ready: $modelPath (threads=$threads)")
                } else {
                    Log.e(TAG, "createPaddlePredictor returned null: $modelPath")
                }
                p
            } catch (t: Throwable) {
                Log.e(TAG, "createPaddlePredictor failed: $modelPath", t)
                null
            }
        }
    }

    /** آیا این مدل میتواند ساخته شود؟ (بدونِ اجرا) */
    @JvmStatic
    fun ready(modelPath: String, threads: Int = 2,
              power: String = "HIGH"): Boolean =
        getOrCreate(modelPath, threads, power) != null

    /** بکاندِ شتابِ این کتابخانه — برایِ لاگِ پایتون (خالی = لود نشده) */
    @JvmStatic
    fun backend(modelPath: String): String =
        if (ensureLib()) "paddle-lite-cpu" else ""

    /**
     * یک بارِ inference: ورودیِ float با شکلِ [shape] → خروجی بهصورت
     * FloatBuffer (پایتون با memoryview میخواند — بدونِ کپیِ عنصری).
     */
    @JvmStatic
    fun predict(modelPath: String, shape: LongArray, data: FloatArray,
                threads: Int = 2, power: String = "HIGH"): FloatBuffer? {
        if (!ensureLib()) return null
        val p = getOrCreate(modelPath, threads, power) ?: return null
        return try {
            val input = p.getInput(0) ?: return null
            if (!input.resize(shape)) return null
            if (!input.setData(data)) return null
            if (!p.run()) return null
            val out = p.getOutput(0) ?: return null
            val shp = out.shape()
            if (shp != null) lastOutShape[modelPath] = shp
            val arr = out.floatData ?: return null
            FloatBuffer.wrap(arr)
        } catch (t: Throwable) {
            Log.e(TAG, "predict failed: $modelPath", t)
            null
        }
    }

    /** شکلِ خروجیِ آخرِ predict برایِ همین مدل (برایِ reshape در پایتون) */
    @JvmStatic
    fun predictShape(modelPath: String): LongArray? = lastOutShape[modelPath]

    /** آزادسازی — فعلاً predictorها تا پایانِ پروسه کش میمانند */
    @JvmStatic
    fun releaseAll() {
        predictors.clear()
        lastOutShape.clear()
    }
}
