package com.amirwolf.mangatranslator

import android.util.Log
import com.baidu.paddle.lite.MobileConfig
import com.baidu.paddle.lite.PaddlePredictor
import com.baidu.paddle.lite.PowerMode
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.LinkedBlockingDeque
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

/**
 * v1.14.166 — بازگشتِ پلِ Paddle-Lite (مجموعهٔ رسمیِ ppocr_demo) به‌عنوانِ
 * موتورِ OCRِ گوشی (دستورِ سازنده: «استخراجِ متن تو گوشی Paddle-Lite
 * arm arm64 بزار ببینم چجور استخراج میکنه»).
 *
 * برخلافِ سبکِ قدیمیِ K3 دیگر کاسکادی نیست؛ manga.py (PliteCropOCR)
 * پیش/پس‌پردازش را انجام میدهد و فقط «تانسور» میفرستد — و OCR فقط رویِ
 * کراپهایِ detector-v4-s_int8.onnx اجرا میشود، هرگز تمامصفحه:
 *   predict(path, shape, floatBytesLE, threads, power, poolMax) → خروجیِ float بهصورتِ bytesِ LE
 *   predictShape(path)                                         → شکلِ خروجیِ آخرِ همان مدل
 *   ready(path, threads, power)                                → ساختِ موفقِ predictor؟
 *   backend(path)                                              → "paddle-lite-cpu" یا ""
 *
 * v1.14.167 — دو فیکس بر سرِ لاگِ واقعیِ گوشی (manga.log):
 *   ۱) «memoryview: a bytes-like object is required, not 'HeapFloatBuffer'»:
 *      نسخهٔ قبلی خروجی را FloatBuffer.wrap(arr) برمیگرداند؛ Chaquopy
 *      java.nio.FloatBuffer را به پروتکلِ بافرِ پایتون تبدیل نمیکند →
 *      np.frombuffer(memoryview(fb)) در پایتون TypeError میداد و «همهٔ»
 *      ناحیه‌ها «بدونِ متن» میشدند. حالا ورودی و خروجی هر دو byte[] است
 *      (floatهایِ little-endian) — Chaquopy byte[] ↔ bytes را صفر-کپی
 *      تبدیل میکند؛ هم باگ رفع است هم ردِ دادهٔ ۲.۷مگیِ det (که قبلاً
 *      عنصربه‌عنصر از jarray(jfloat) ساخته میشد) حذف شد.
 *   ۲) استخراجِ موازیِ ناحیهها (دستورِ سازنده: «هر بخش متن یک مقدار ram
 *      cpu همزمان کار کنن… حداکثر توانش»): PaddlePredictor برایِ runِ
 *      همزمانِ «یک نمونه» امن نیست ولی نمونههایِ جدا برایِ هر نخ الگویِ
 *      رسمیِ خودِ Paddle-Lite است (هر نخ predictor خودش). پس یک «استخرِ
 *      predictor» بهازای هر مدل ساخته میشود؛ predict یک نمونهٔ آزاد
 *      برمیدارد (تا سقفِ poolMax؛ در صورتِ اشباع تا ۳۰s منتظرِ آزادشدن
 *      میماند) و بعدِ کار برمیگرداند. سقفِ استخر از پایتون میآید
 *      (= تعدادِ کارگرِ OCRِ همان صفحه).
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
    private const val POOL_WAIT_MS = 30_000L

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

    // ── استخرِ predictor per-model (v1.14.167 — OCRِ موازیِ ناحیهها) ──
    private val pools = ConcurrentHashMap<String, LinkedBlockingDeque<PaddlePredictor>>()
    private val poolLive = ConcurrentHashMap<String, AtomicInteger>()
    private val buildLocks = ConcurrentHashMap<String, Any>()
    private val lastOutShape = ConcurrentHashMap<String, LongArray>()

    private fun parsePower(p: String?): PowerMode = when (
        (p ?: "HIGH").trim().uppercase()) {
        "NO_BIND" -> PowerMode.LITE_POWER_NO_BIND
        "LOW" -> PowerMode.LITE_POWER_LOW
        "HIGH" -> PowerMode.LITE_POWER_HIGH
        else -> PowerMode.LITE_POWER_HIGH
    }

    /** ساختِ «یک» نمونهٔ جدید اگر زیرِ سقفِ استخر باشیم؛ وگرنه null */
    private fun createOne(modelPath: String, threads: Int,
                          power: String, poolMax: Int): PaddlePredictor? {
        if (!ensureLib()) return null
        val live = poolLive.getOrPut(modelPath) { AtomicInteger(0) }
        val lock = buildLocks.getOrPut(modelPath) { Any() }
        synchronized(lock) {
            // دوبارِ چکِ داخلِ قفل — شاید نخِ دیگر همین الان ساخت
            if (live.get() >= poolMax) return null
            return try {
                val cfg = MobileConfig()
                cfg.setModelFromFile(modelPath)
                cfg.threads = if (threads in 1..8) threads else 2
                cfg.powerMode = parsePower(power)
                val p = PaddlePredictor.createPaddlePredictor(cfg)
                if (p != null) {
                    live.incrementAndGet()
                    Log.i(TAG, "predictor ready: $modelPath "
                            + "(threads=$threads, pool=${live.get()}/$poolMax)")
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

    /** آیا این مدل میتواند ساخته شود؟ (بدونِ اجرا — یک نمونه در استخر میماند) */
    @JvmStatic
    fun ready(modelPath: String, threads: Int = 2,
              power: String = "HIGH"): Boolean {
        val pool = pools.getOrPut(modelPath) { LinkedBlockingDeque() }
        if (!pool.isEmpty()) return true
        val p = createOne(modelPath, threads, power, 1) ?: return false
        pool.offerFirst(p)
        return true
    }

    /** بکاندِ شتابِ این کتابخانه — برایِ لاگِ پایتون (خالی = لود نشده) */
    @JvmStatic
    fun backend(modelPath: String): String =
        if (ensureLib()) "paddle-lite-cpu" else ""

    /** float[] → byte[] (little-endian) — برایِ خروجیِ به پایتون */
    private fun floatsToBytes(arr: FloatArray): ByteArray {
        val bb = ByteBuffer.allocate(arr.size * 4)
            .order(ByteOrder.LITTLE_ENDIAN)
        bb.asFloatBuffer().put(arr)
        return bb.array()
    }

    /**
     * یک بارِ inference: ورودیِ float32 بهصورتِ bytesِ little-endian با
     * شکلِ [shape] → خروجیِ float32 بهصورتِ bytesِ little-endian.
     * predictor از استخرِ همان مدل برمیدارد (تا poolMax نمونهٔ همزمان —
     * v1.14.167: OCRِ موازیِ ناحیهها) و بعدِ کار برمیگرداند.
     */
    @JvmStatic
    fun predict(modelPath: String, shape: LongArray, data: ByteArray,
                threads: Int = 2, power: String = "NO_BIND",
                poolMax: Int = 1): ByteArray? {
        if (!ensureLib()) return null
        val maxN = if (poolMax in 1..8) poolMax else 1
        val pool = pools.getOrPut(modelPath) { LinkedBlockingDeque() }
        var pred = pool.pollFirst()
        if (pred == null) {
            // استخر خالی → اگر زیرِ سقفیم بساز؛ در سقف → منتظرِ آزادشدن
            pred = createOne(modelPath, threads, power, maxN)
                ?: pool.pollFirst(POOL_WAIT_MS, TimeUnit.MILLISECONDS)
                ?: return null
        }
        var ok = false
        try {
            val floats = FloatArray(data.size / 4)
            ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN)
                .asFloatBuffer().get(floats)
            val input = pred.getInput(0) ?: return null
            if (!input.resize(shape)) return null
            if (!input.setData(floats)) return null
            if (!pred.run()) return null
            val out = pred.getOutput(0) ?: return null
            val shp = out.shape()
            if (shp != null) lastOutShape[modelPath] = shp
            val arr = out.floatData ?: return null
            ok = true
            return floatsToBytes(arr)
        } catch (t: Throwable) {
            Log.e(TAG, "predict failed: $modelPath", t)
            return null
        } finally {
            if (ok) {
                pool.offerFirst(pred)
            } else {
                // نمونهٔ مشکوک به خرابی — به استخر برنمیگردد؛ جایش
                // آزاد است تا در فراخوانیِ بعدی نمونهٔ تازه ساخته شود
                val live = poolLive[modelPath]
                live?.decrementAndGet()
            }
        }
    }

    /** شکلِ خروجیِ آخرِ predict برایِ همین مدل (برایِ reshape در پایتون) */
    @JvmStatic
    fun predictShape(modelPath: String): LongArray? = lastOutShape[modelPath]

    /** آزادسازی — فعلاً predictorها تا پایانِ پروسه کش میمانند */
    @JvmStatic
    fun releaseAll() {
        pools.clear()
        poolLive.clear()
        lastOutShape.clear()
    }
}
