package com.amirwolf.mangatranslator

import android.app.Service
import android.content.Intent
import android.os.IBinder

/**
 * v1.14.166 — پروبِ Paddle-Lite در پروسهٔ جدا (:pliteprobe) — بازگشتِ
 * سبکِ اثباتشدهٔ 1.14.158.
 *
 * تاریخچه: کرشهایِ سیگفالتِ RuntimeProgramِ 1.14.106-119 رویِ POCO F4
 * (Adreno 650) — سیگفالتِ نیتیو در پایتون قابلِ گرفتن نیست و پروسهٔ
 * اصلیِ اپ را میکشت (درسِ EpProbeServiceِ v1.14.156 برایِ XNNPACK).
 *
 * این سرویس در پروسهٔ :pliteprobe اجرا میشود و با مدلهایِ واقعیِ
 * nb (فقط-CPU) یک inference کاملِ det + rec میزند:
 *   — det با دو شکلِ واقعی (64² و 512²)
 *   — rec با 48×320
 * خروجی با سشنِ مرجع سنجیده میشود (NaN/بی‌نهایت = مردود) و نتیجه در
 * فایلِ «out» نوشته میشود:
 *   «verdict ok det_ms=X rec_ms=Y» = پدل-لایت سالم است
 *   «verdict fail …»             = خطایِ جاوا/مدل
 *   فایلِ غایب                    = کرشِ نیتیو (سیگفالت) → پایتون مدل را
 *                                   بن میکند (plite_banned.txt) و OCRِ
 *                                   گوشی خودکار به PP-OCRv6 ONNX میرود.
 * بعدِ تمام، پروسه با killProcess بسته میشود.
 */
class PliteProbeService : Service() {

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val detPath = intent?.getStringExtra("det") ?: ""
        val recPath = intent?.getStringExtra("rec") ?: ""
        val outPath = intent?.getStringExtra("out") ?: ""
        val threads = (intent?.getStringExtra("threads") ?: "2").toIntOrNull() ?: 2
        Thread {
            val sb = StringBuilder()
            try {
                probeAll(detPath, recPath, threads, sb)
            } catch (t: Throwable) {
                android.util.Log.e("PliteProbe", "probe failed", t)
                sb.append("verdict fail ").append(t.javaClass.simpleName)
                    .append(": ").append(t.message?.take(140) ?: "").append("\n")
            }
            try {
                if (outPath.isNotEmpty()) {
                    java.io.File(outPath).writeText(sb.toString())
                }
            } catch (_: Exception) { }
            try { stopSelf() } catch (_: Exception) { }
            try {
                android.os.Process.killProcess(android.os.Process.myPid())
            } catch (_: Exception) { }
        }.start()
        return START_NOT_STICKY
    }

    private fun isSane(arr: FloatArray): Boolean {
        if (arr.isEmpty()) return false
        var i = 0
        val step = maxOf(1, arr.size / 4096) // نمونهگیریِ سبک — کافی برایِ NaN
        while (i < arr.size) {
            val v = arr[i]
            if (v.isNaN() || v.isInfinite()) return false
            i += step
        }
        return true
    }

    /** float[] → byte[]ِ little-endian — ورودیِ جدیدِ پلِ v1.14.167.
     *  v1.14.169 — فیکسِ ارورِ کامپایلِ CI («Build arm64 APK» از 1.14.167
     *  شکست میخورد): «return type mismatch: expected 'kotlin.ByteArray',
     *  actual 'kotlin.FloatArray!'» — fbv یک FloatBuffer است و
     *  FloatBuffer.array() برمیگرداند float[] نه byte[]؛ باید array()
     *  خودِ ByteBuffer برگردد (viewِ float همان را پر میکند). */
    private fun floatBytes(n: Int): ByteArray {
        val bb = java.nio.ByteBuffer.allocate(n * 4)
            .order(java.nio.ByteOrder.LITTLE_ENDIAN)
        bb.asFloatBuffer().put(FloatArray(n) { 0.25f })
        return bb.array()
    }

    /** یک run با شکلِ مشخص؛ خروجی: (سالم؟، ms) */
    private fun runOnce(path: String, shape: LongArray, threads: Int): Pair<Boolean, Long> {
        val n = shape.fold(1L) { a, b -> a * b }.toInt()
        val data = floatBytes(n)
        val t0 = System.currentTimeMillis()
        // v1.14.167 — پلِ byte-based (بازگشتِ floatهایِ little-endian)
        val out = PaddleLiteBridge.predict(path, shape, data, threads,
                                           "NO_BIND", 1)
            ?: return Pair(false, -1L)
        val ms = System.currentTimeMillis() - t0
        val fbv = java.nio.ByteBuffer.wrap(out)
            .order(java.nio.ByteOrder.LITTLE_ENDIAN).asFloatBuffer()
        val arr = FloatArray(fbv.remaining())
        fbv.get(arr)
        return Pair(isSane(arr), ms)
    }

    private fun probeAll(detPath: String, recPath: String, threads: Int,
                         sb: StringBuilder) {
        if (!PaddleLiteBridge.libOk()) {
            sb.append("verdict fail lib-not-loaded\n")
            return
        }
        if (detPath.isEmpty() || recPath.isEmpty()
                || !java.io.File(detPath).isFile()
                || !java.io.File(recPath).isFile()) {
            sb.append("verdict fail model-missing\n")
            return
        }
        // predictorهایِ هر دو مدل باید ساخته شوند (کرشِ RuntimeProgramِ
        // قبلی دقیقاً همینجا بود)
        if (!PaddleLiteBridge.ready(detPath, threads, "NO_BIND")
                || !PaddleLiteBridge.ready(recPath, threads, "NO_BIND")) {
            sb.append("verdict fail predictor-create\n")
            return
        }
        var detMs = -1L
        for (shape in arrayOf(
                longArrayOf(1, 3, 64, 64), longArrayOf(1, 3, 512, 512))) {
            val (ok, ms) = runOnce(detPath, shape, threads)
            if (!ok) {
                sb.append("verdict fail det-shape-")
                    .append(shape[2]).append("x").append(shape[3]).append("\n")
                return
            }
            detMs = ms
        }
        val (okRec, recMs) = runOnce(recPath, longArrayOf(1, 3, 48, 320), threads)
        if (!okRec) {
            sb.append("verdict fail rec-shape\n")
            return
        }
        sb.append("verdict ok det_ms=").append(detMs)
            .append(" rec_ms=").append(recMs).append("\n")
    }
}
