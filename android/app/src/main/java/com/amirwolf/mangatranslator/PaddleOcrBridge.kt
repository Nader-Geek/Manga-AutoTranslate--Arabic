// v1.14.182 — موتورِ OCRِ رسمیِ PP-OCR رویِ اندروید (پرتِ رسمیِ ppocr-android)
// دستورِ سازنده: «ml kit خوب نیست … کامل بخون
// paddleocr.ai …/android_deployment.html و از PP-OCRv6_medium بزار تو کد
// خودم قسمت استخراجم؛ اول detector-v4-s همه قسمت های متن پیدا کنه فقط
// همون قسمت ها استخراج کنه تا سریعتر باشه».
//   • موتور = پرتِ یک‌به‌یکِ SDKِ رسمیِ PaddleOCR (ppocr-android، v3.7):
//     DetPreprocessor (ImageNet/BGR/limit min-64/roundHalfToEven32/cap 4000)
//     → DBPostProcessor (thresh 0.3، sside≥3، score-fast ≥0.6،
//       PolygonUnclip ×1.5، sside≥5، بدونِ dilate — پیشفرضِ رسمی)
//     → QuadTextCrop (minAreaRect + پرسپکتیو + چرخشِ CCW اگر h/w≥1.5)
//     → RecPreprocessor (RGB، h=48، ceil(aspect)، cap 3200، x/127.5-1،
//       بچِ پدشده تا maxW) → CTCDecoder (blank=0، idx-1، charset از
//       inference.yml «character_dict» + فاصله).
//   • مدلها = رسمیِ PaddlePaddle: PP-OCRv6_medium det (59MB) + rec (73MB)
//     — دانلودِ زمانِ اجرا مثلِ بقیهٔ مدلها (نه باندل در APK).
//   • تفاوتهایِ مجاز با SDKِ رسمی (بدونِ OpenCV AAR — ~80MB صرفهجویی):
//     findContours/minAreaRect = مؤلفههایِ همبند + پوشِ محدب +
//     کالیپرسِ چرخان (هم‌نتیجه: پوشِ هر مؤلفه = پوشِ کانتورِ آن)؛
//     warpPerspectiveِ INTER_CUBIC = هوموگرافیِ دستی با نمونهبرداریِ
//     خطی (بعدش rec به h=48 کوچک میکند — اثرِ کیفی ناچیز)؛ resize =
//     خطیِ دستی. بقیه = عینِ الگوریتمِ رسمی.
//   • فقط ONNX Runtime (واردِ gradle از قبل) — هیچ Paddle-Lite/native
//     جدیدی نیست. sشنها thread-safe برایِ run — کارگرهایِ موازیِ OCR
//     بدونِ قفل صدا میزنند (کلِ وضعیتِ مشترک = immutable).
//   • پروتکلِ خروجی = همان MlKitBridge: سطرِ «META|lang|n» + سطرهایِ
//     «ang|conf|box|text|blk» (box = ۴ گوشهٔ TL,TR,BR,BL) تا manga.py
//     (PaddleAndroidOCR) بدونِ تغییرِ پارسر وصل شود.
package com.amirwolf.mangatranslator

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Log
import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import java.io.File
import java.nio.FloatBuffer
import java.util.Locale
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.ceil
import kotlin.math.cos
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin

object PaddleOcrBridge {

    private const val TAG = "PaddleOcrBridge"

    // ── پیشفرضهایِ رسمیِ PaddleOCRConfig (v3.7) ──
    private const val DET_THRESH = 0.3f          // detThresh
    private const val DET_BOX_THRESH = 0.6f      // detBoxThresh (score-fast)
    private const val DET_UNCLIP_RATIO = 1.5f    // detUnclipRatio
    private const val DET_MAX_CANDIDATES = 3000  // detMaxCandidates
    private const val DET_USE_DILATION = false   // detUseDilation (پیشفرضِ رسمی)
    private const val DET_LIMIT_SIDE = 64        // detLimitSideLen
    private const val DET_LIMIT_TYPE = "min"     // detLimitType
    private const val DET_MAX_SIDE = 4000        // detMaxSideLimit
    private const val MIN_SIZE_BEFORE_UNCLIP = 3f
    private const val MIN_SIZE_AFTER_UNCLIP = 5f
    private const val REC_FIXED_H = 48           // FIXED_HEIGHT
    private const val REC_MAX_W = 3200           // MAX_IMG_W
    private const val VERTICAL_CROP_RATIO = 1.5  // QuadTextCrop
    private const val ROW_THRESHOLD_Y = 10f      // BoxSorter
    private const val REC_SCORE_FLOOR = 0.4f     // کفِ اطمینانِ خط (فیلترِ جارو)

    private val detMean = doubleArrayOf(0.485, 0.456, 0.406)
    private val detStd = doubleArrayOf(0.229, 0.224, 0.225)

    @Volatile private var env: OrtEnvironment? = null
    @Volatile private var detSession: OrtSession? = null
    @Volatile private var recSession: OrtSession? = null
    @Volatile private var characters: List<String> = emptyList()
    @Volatile private var inited: Boolean = false
    private val initLock = Any()

    // ── init از مسیرِ فایل (مدلها دانلودِ زمانِ اجرا هستند، asset نیستند) ──
    @JvmStatic
    fun init(detPath: String, recPath: String, ymlPath: String, numThreads: Int): Boolean =
        synchronized(initLock) {
            try {
                if (inited) return true
                for (p in listOf(detPath, recPath, ymlPath)) {
                    val f = File(p)
                    if (!f.isFile || f.length() < 1000L) {
                        Log.i(TAG, "init: فایل نیست: $p")
                        return false
                    }
                }
                characters = parseCharset(File(ymlPath).readText())
                if (characters.isEmpty()) {
                    Log.i(TAG, "init: character_dictِ خالی در yml")
                    return false
                }
                val e = OrtEnvironment.getEnvironment()
                val opts = OrtSession.SessionOptions().apply {
                    setIntraOpNumThreads(numThreads.coerceIn(1, 8))
                    setInterOpNumThreads(1)
                    setOptimizationLevel(
                        OrtSession.SessionOptions.OptimizationLevel.ALL_OPT)
                }
                detSession = e.createSession(detPath, opts)
                recSession = e.createSession(recPath, opts)
                env = e
                inited = true
                Log.i(TAG, "init: OK | charset=${characters.size} | threads=$numThreads")
                true
            } catch (t: Throwable) {
                Log.i(TAG, "init: ${t.message}")
                inited = false
                false
            }
        }

    @JvmStatic
    fun ready(): Boolean = inited && detSession != null && recSession != null

    /** خروجی = سطرهایِ «ang|conf|box|text|blk» (بدونِ META — هم‌قالبِ
     *  MlKitBridge.recognize). باکس = ۴ گوشهٔ TL,TR,BR,BL مختصاتِ ورودی. */
    @JvmStatic
    fun recognize(png: ByteArray): Array<String> {
        if (!ready()) return arrayOf()
        val bmp = BitmapFactory.decodeByteArray(png, 0, png.size) ?: return arrayOf()
        try {
            val rows = ArrayList<String>()
            for (item in detectBitmap(bmp)) {
                val (quad, text, conf) = item
                val box = (0 until 4).joinToString(",") { k ->
                    "${quad[k * 2].toInt()},${quad[k * 2 + 1].toInt()}"
                }
                rows.add(String.format(Locale.US, "%.2f|%.4f|%s|%s|%d",
                    0f, conf, box, text, 0))
            }
            return rows.toTypedArray()
        } catch (t: Throwable) {
            Log.i(TAG, "recognize: ${t.message}")
            return arrayOf()
        } finally {
            try { bmp.recycle() } catch (_: Exception) {}
        }
    }

    /** هم‌امضایِ MlKitBridge.recognizeAuto — سطرِ اولِ META|lang|n. */
    @JvmStatic
    fun recognizeAuto(png: ByteArray, lang: String,
                      auto: Int, hasInk: Int): Array<String> {
        val rows = recognize(png)
        val out = ArrayList<String>(rows.size + 1)
        out.add("META|$lang|${rows.size}")
        out.addAll(rows)
        return out.toTypedArray()
    }

    // ════════════════ هستهٔ تشخیص ════════════════

    private data class Line(val quad: FloatArray, val text: String, val conf: Float)

    private fun detectBitmap(bmp: Bitmap): List<Line> {
        val w = bmp.width
        val h = bmp.height
        if (w < 4 || h < 4) return emptyList()
        val px = IntArray(w * h)
        bmp.getPixels(px, 0, w, 0, 0, w, h)
        // ── DetPreprocessor (رسمی): limit min/64 + cap 4000 + گردِ ۳۲ ──
        var (nh, nw) = resize32(h, w, DET_LIMIT_SIDE, DET_LIMIT_TYPE, DET_MAX_SIDE)
        val channel = nw * nh
        val tensor = FloatArray(3 * channel)
        bilinearResizeNormalize(px, w, h, nw, nh, tensor)
        val e = env!!
        val prob: FloatArray
        val pH: Int
        val pW: Int
        OnnxTensor.createTensor(e, FloatBuffer.wrap(tensor),
            longArrayOf(1, 3, nh.toLong(), nw.toLong())).use { t ->
            detSession!!.run(mapOf(detInputName() to t)).use { r ->
                val ot = r[0] as OnnxTensor
                val sh = ot.shape
                pH = sh[2].toInt(); pW = sh[3].toInt()
                val fb = ot.floatBuffer
                val buf = FloatArray(pH * pW)
                fb.get(buf)
                prob = buf
            }
        }
        // ── DBPostProcessor (رسمی) ──
        val boxes = dbPostProcess(prob, pH, pW, h, w)
        if (boxes.isEmpty()) return emptyList()
        // ── BoxSorter (رسمی): ترتیبِ خواندن ──
        val sorted = boxSorter(boxes)
        // ── QuadTextCrop + RecPreprocessor (بچِ رسمی) + CTC ──
        val crops = sorted.map { q -> cropQuad(px, w, h, q) }
        val texts = recBatchWithDims(crops)
        val out = ArrayList<Line>(sorted.size)
        for (i in sorted.indices) {
            val (txt, cf) = texts[i]
            if (txt.isEmpty()) continue
            if (cf < REC_SCORE_FLOOR) continue
            val q = sorted[i]
            out.add(Line(q, txt, cf))
        }
        return out
    }

    private fun detInputName(): String =
        detSession!!.inputNames.iterator().next()

    // ── ImageUtils.resizeToMultipleOf32 (رسمی) ──
    private fun resize32(h: Int, w: Int, limitSide: Int,
                         limitType: String, maxSide: Int): Pair<Int, Int> {
        var ratio = when (limitType.lowercase(Locale.US)) {
            "max" -> if (maxOf(h, w) > limitSide) limitSide.toDouble() / maxOf(h, w) else 1.0
            "min" -> if (minOf(h, w) < limitSide) limitSide.toDouble() / minOf(h, w) else 1.0
            "resize_long" -> limitSide.toDouble() / maxOf(h, w)
            else -> 1.0
        }
        var newH = (h * ratio).toInt()
        var newW = (w * ratio).toInt()
        if (maxOf(newH, newW) > maxSide) {
            val r = maxSide.toDouble() / maxOf(newH, newW)
            newH = (newH * r).toInt()
            newW = (newW * r).toInt()
        }
        newH = maxOf(roundHalfToEven(newH / 32.0) * 32, 32)
        newW = maxOf(roundHalfToEven(newW / 32.0) * 32, 32)
        return Pair(newH, newW)
    }

    // ── MathUtils.roundHalfToEven (رسمی) ──
    private fun roundHalfToEven(v: Double): Int {
        val f = kotlin.math.floor(v)
        val d = v - f
        return when {
            d < 0.5 -> f.toInt()
            d > 0.5 -> f.toInt() + 1
            f.toInt() % 2 == 0 -> f.toInt()
            else -> f.toInt() + 1
        }
    }

    /** resizeِ خطیِ دستی + نرمالسازیِ ImageNet — بجایِ OpenCVِ
     *  DetPreprocessor (imgMode پیشفرضِ رسمی = BGR → بدونِ تعویضِ کانال). */
    private fun bilinearResizeNormalize(px: IntArray, sw: Int, sh: Int,
                                        dw: Int, dh: Int, out: FloatArray) {
        val chan = dw * dh
        val xRatio = if (dw > 1) (sw - 1).toDouble() / (dw - 1) else 0.0
        val yRatio = if (dh > 1) (sh - 1).toDouble() / (dh - 1) else 0.0
        for (c in 0 until 3) {
            val mean = detMean[c]
            val std = detStd[c]
            val o = c * chan
            for (y in 0 until dh) {
                val fy = y * yRatio
                val y0 = fy.toInt()
                val y1 = min(y0 + 1, sh - 1)
                val ly = fy - y0
                for (x in 0 until dw) {
                    val fx = x * xRatio
                    val x0 = fx.toInt()
                    val x1 = min(x0 + 1, sw - 1)
                    val lx = fx - x0
                    val p00 = px[y0 * sw + x0]
                    val p01 = px[y0 * sw + x1]
                    val p10 = px[y1 * sw + x0]
                    val p11 = px[y1 * sw + x1]
                    // کانال: 0=B، 1=G، 2=R (آرایهٔ ARGB اندروید)
                    val v00 = when (c) { 0 -> p00 and 0xFF; 1 -> (p00 shr 8) and 0xFF; else -> (p00 shr 16) and 0xFF }
                    val v01 = when (c) { 0 -> p01 and 0xFF; 1 -> (p01 shr 8) and 0xFF; else -> (p01 shr 16) and 0xFF }
                    val v10 = when (c) { 0 -> p10 and 0xFF; 1 -> (p10 shr 8) and 0xFF; else -> (p10 shr 16) and 0xFF }
                    val v11 = when (c) { 0 -> p11 and 0xFF; 1 -> (p11 shr 8) and 0xFF; else -> (p11 shr 16) and 0xFF }
                    val top = v00 + (v01 - v00) * lx
                    val bot = v10 + (v11 - v10) * lx
                    val v = (top + (bot - top) * ly).toFloat()
                    // (x/255 - mean) / std — دقیقاً DetPreprocessor
                    out[o + x] = ((v / 255.0 - mean) / std).toFloat()
                }
            }
        }
    }

    // ── DBPostProcessor (رسمی) — بجایِ findContours/minAreaRectِ OpenCV:
    //    مؤلفههایِ همبند (۸-وصل) → پوشِ محدب → کالیپرسِ چرخان ──
    private fun dbPostProcess(prob: FloatArray, pH: Int, pW: Int,
                              origH: Int, origW: Int): List<FloatArray> {
        val scaleX = origW.toDouble() / pW
        val scaleY = origH.toDouble() / pH
        val bin = BooleanArray(pH * pW)
        for (i in bin.indices) bin[i] = prob[i] > DET_THRESH
        if (DET_USE_DILATION) {
            val d = BooleanArray(pH * pW)
            for (y in 0 until pH) {
                val base = y * pW
                val baseUp = if (y > 0) base - pW else base
                for (x in 0 until pW) {
                    val xL = if (x > 0) x - 1 else x
                    d[base + x] = bin[base + x] || bin[base + xL] ||
                            bin[baseUp + x] || bin[baseUp + xL]
                }
            }
            System.arraycopy(d, 0, bin, 0, bin.size)
        }
        val visited = BooleanArray(pH * pW)
        val stack = IntArray(pH * pW)
        val boxes = ArrayList<FloatArray>()
        var candidates = 0
        for (start in bin.indices) {
            if (!bin[start] || visited[start]) continue
            if (candidates >= DET_MAX_CANDIDATES) break
            candidates++
            var sp = 0
            stack[sp++] = start
            visited[start] = true
            var minX = pW; var maxX = 0; var minY = pH; var maxY = 0
            val comp = ArrayList<Int>()
            while (sp > 0) {
                val cur = stack[--sp]
                val cy = cur / pW
                val cx = cur - cy * pW
                comp.add(cur)
                if (cx < minX) minX = cx
                if (cx > maxX) maxX = cx
                if (cy < minY) minY = cy
                if (cy > maxY) maxY = cy
                for (dy in -1..1) {
                    val ny = cy + dy
                    if (ny < 0 || ny >= pH) continue
                    for (dx in -1..1) {
                        val nx = cx + dx
                        if (nx < 0 || nx >= pW) continue
                        val ni = ny * pW + nx
                        if (bin[ni] && !visited[ni]) {
                            visited[ni] = true
                            stack[sp++] = ni
                        }
                    }
                }
            }
            // مؤلفههایِ ریز را کامل نگه نمی‌داریم — فقط پوششان لازم است
            if (comp.size < 3) continue
            // مرزِ مؤلفه = پیکسلهایی که همسایهٔ غیرِعضو دارند → پوشِ دقیق
            val hullPts = ArrayList<DoubleArray>(comp.size / 2 + 4)
            for (cur in comp) {
                val cy = cur / pW
                val cx = cur - cy * pW
                var border = false
                outer@ for (dy in -1..1) {
                    val ny = cy + dy
                    if (ny < 0 || ny >= pH) { border = true; break }
                    for (dx in -1..1) {
                        val nx = cx + dx
                        if (nx < 0 || nx >= pW) { border = true; break@outer }
                        if (!bin[ny * pW + nx]) { border = true; break@outer }
                    }
                }
                if (border) hullPts.add(doubleArrayOf(cx.toDouble(), cy.toDouble()))
            }
            if (hullPts.size < 3) hullPts.add(doubleArrayOf(minX.toDouble(), minY.toDouble()))
            val hull = convexHull(hullPts) ?: continue
            val rect = minAreaRect(hull) ?: continue
            // sside < 3 → رد (رسمی: MIN_SIZE_BEFORE_UNCLIP)
            if (minOf(rect[2], rect[3]) < MIN_SIZE_BEFORE_UNCLIP) continue
            var quad = orderRectPoints(cornersOf(rect))
            // score-fast (رسمی): میانگینِ prob داخلِ چهارضلعی
            val score = boxScoreFast(quad, prob, pH, pW)
            if (score < DET_BOX_THRESH) continue
            // PolygonUnclip (رسمی ×1.5) → minAreaRectِ دوباره
            val expanded = polygonUnclip(quad, DET_UNCLIP_RATIO)
            val hull2 = convexHull(expanded) ?: continue
            val rect2 = minAreaRect(hull2) ?: continue
            if (minOf(rect2[2], rect2[3]) < MIN_SIZE_AFTER_UNCLIP) continue
            val quad2 = orderRectPoints(cornersOf(rect2))
            // مقیاسِ برگشت به ابعادِ اصلی (رسمی: roundHalfToEven + clamp [0,W])
            val scaled = FloatArray(8)
            for (k in 0 until 4) {
                val sx = roundHalfToEven(quad2[k * 2] * scaleX)
                    .coerceIn(0, origW).toFloat()
                val sy = roundHalfToEven(quad2[k * 2 + 1] * scaleY)
                    .coerceIn(0, origH).toFloat()
                scaled[k * 2] = sx
                scaled[k * 2 + 1] = sy
            }
            val bw = hypot((scaled[2] - scaled[0]).toDouble(),
                (scaled[3] - scaled[1]).toDouble())
            val bh = hypot((scaled[6] - scaled[0]).toDouble(),
                (scaled[7] - scaled[1]).toDouble())
            if (bw <= 3.0 || bh <= 3.0) continue
            boxes.add(scaled)
        }
        return boxes
    }

    // ── QuadGeometry.orderMinAreaRectPoints (رسمی) — ورودی/خروجی:
    //    FloatArray(8) به ترتیبِ TL,TR,BR,BL ──
    private fun orderRectPoints(corners: Array<DoubleArray>): FloatArray {
        val sorted = corners.sortedBy { it[0] }
        val tl: DoubleArray
        val bl: DoubleArray
        if (sorted[1][1] > sorted[0][1]) { tl = sorted[0]; bl = sorted[1] }
        else { tl = sorted[1]; bl = sorted[0] }
        val tr: DoubleArray
        val br: DoubleArray
        if (sorted[3][1] > sorted[2][1]) { tr = sorted[2]; br = sorted[3] }
        else { tr = sorted[3]; br = sorted[2] }
        val out = FloatArray(8)
        val pts = listOf(tl, tr, br, bl)
        for (k in 0 until 4) {
            out[k * 2] = pts[k][0].toFloat()
            out[k * 2 + 1] = pts[k][1].toFloat()
        }
        return out
    }

    // score-fast (رسمی computeBoxScore): میانگینِ prob داخلِ چهارضلعیِ محدب
    private fun boxScoreFast(quad: FloatArray, prob: FloatArray,
                             pH: Int, pW: Int): Float {
        var minX = pW - 1; var maxX = 0; var minY = pH - 1; var maxY = 0
        for (k in 0 until 4) {
            val x = quad[k * 2]; val y = quad[k * 2 + 1]
            minX = min(minX, kotlin.math.floor(x).toInt().coerceIn(0, pW - 1))
            maxX = max(maxX, kotlin.math.ceil(x).toInt().coerceIn(0, pW - 1))
            minY = min(minY, kotlin.math.floor(y).toInt().coerceIn(0, pH - 1))
            maxY = max(maxY, kotlin.math.ceil(y).toInt().coerceIn(0, pH - 1))
        }
        var sum = 0.0
        var n = 0
        for (y in minY..maxY) {
            for (x in minX..maxX) {
                if (pointInQuad(quad, x + 0.5, y + 0.5)) {
                    sum += prob[y * pW + x]
                    n++
                }
            }
        }
        return if (n > 0) (sum / n).toFloat() else 0f
    }

    private fun pointInQuad(q: FloatArray, px: Double, py: Double): Boolean {
        var pos = false
        var neg = false
        for (k in 0 until 4) {
            val x1 = q[k * 2].toDouble()
            val y1 = q[k * 2 + 1].toDouble()
            val x2 = q[((k + 1) % 4) * 2].toDouble()
            val y2 = q[((k + 1) % 4) * 2 + 1].toDouble()
            val cross = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
            if (cross > 0) pos = true else if (cross < 0) neg = true
        }
        return !(pos && neg)
    }

    // ── PolygonUnclip (رسمی — پرتِ مستقیم؛ خروجی = رئوسِ منبسطشده) ──
    private fun polygonUnclip(points: FloatArray, unclipRatio: Float):
            List<DoubleArray> {
        val n = 4
        val pts = ArrayList<DoubleArray>(n)
        for (k in 0 until n) {
            pts.add(doubleArrayOf(points[k * 2].toDouble(),
                points[k * 2 + 1].toDouble()))
        }
        var signed = 0.0
        var per = 0.0
        for (i in 0 until n) {
            val p1 = pts[i]
            val p2 = pts[(i + 1) % n]
            signed += p1[0] * p2[1] - p2[0] * p1[1]
            per += hypot(p2[0] - p1[0], p2[1] - p1[1])
        }
        val area = abs(signed / 2.0)
        if (area <= 1e-6 || per <= 1e-6) return pts
        val distance = area * unclipRatio / per
        val clockwise = signed > 0.0
        val normals = ArrayList<DoubleArray>(n)
        for (i in 0 until n) {
            val p1 = pts[i]
            val p2 = pts[(i + 1) % n]
            val dx = p2[0] - p1[0]
            val dy = p2[1] - p1[1]
            val len = hypot(dx, dy)
            if (len <= 1e-6) return pts
            normals.add(if (clockwise) doubleArrayOf(dy / len, -dx / len)
            else doubleArrayOf(-dy / len, dx / len))
        }
        val out = ArrayList<DoubleArray>(n)
        for (i in 0 until n) {
            // تقاطعِ خطِ جابهجاشدهٔ یالِ (i-1) و یالِ (i) — برایِ
            // چهارضلعیِ محدب معادلِ ClipperOffsetِ رسمی است (گوشههایِ
            // گردِ clipper رویِ minAreaRectِ بعدی اثری ندارند)
            val a0 = doubleArrayOf(pts[(i - 1 + n) % n][0] + normals[(i - 1 + n) % n][0] * distance,
                pts[(i - 1 + n) % n][1] + normals[(i - 1 + n) % n][1] * distance)
            val a1 = doubleArrayOf(pts[i][0] + normals[(i - 1 + n) % n][0] * distance,
                pts[i][1] + normals[(i - 1 + n) % n][1] * distance)
            val b0 = doubleArrayOf(pts[i][0] + normals[i][0] * distance,
                pts[i][1] + normals[i][1] * distance)
            val b1 = doubleArrayOf(pts[(i + 1) % n][0] + normals[i][0] * distance,
                pts[(i + 1) % n][1] + normals[i][1] * distance)
            val adx = a1[0] - a0[0]; val ady = a1[1] - a0[1]
            val bdx = b1[0] - b0[0]; val bdy = b1[1] - b0[1]
            val det = adx * (-bdy) - (-bdx) * ady
            if (abs(det) < 1e-9) {
                out.add(doubleArrayOf(b0[0], b0[1]))
            } else {
                val t = ((b0[0] - a0[0]) * (-bdy) - (b0[1] - a0[1]) * (-bdx)) / det
                out.add(doubleArrayOf(a0[0] + adx * t, a0[1] + ady * t))
            }
        }
        return out
    }

    // ── پوشِ محدب (monotone chain) ──
    private fun convexHull(ptsIn: List<DoubleArray>): Array<DoubleArray>? {
        if (ptsIn.size < 3) return null
        val pts = ptsIn.sortedWith(compareBy({ it[0] }, { it[1] }))
        val lower = ArrayList<DoubleArray>(pts.size)
        for (p in pts) {
            while (lower.size >= 2 && cross(lower[lower.size - 2], lower[lower.size - 1], p) <= 0) {
                lower.removeAt(lower.size - 1)
            }
            lower.add(p)
        }
        val upper = ArrayList<DoubleArray>(pts.size)
        for (i in pts.indices.reversed()) {
            val p = pts[i]
            while (upper.size >= 2 && cross(upper[upper.size - 2], upper[upper.size - 1], p) <= 0) {
                upper.removeAt(upper.size - 1)
            }
            upper.add(p)
        }
        lower.removeAt(lower.size - 1)
        upper.removeAt(upper.size - 1)
        lower.addAll(upper)
        return if (lower.size >= 3) lower.toTypedArray() else null
    }

    private fun cross(o: DoubleArray, a: DoubleArray, b: DoubleArray): Double =
        (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    /** minAreaRect با کالیپرسِ چرخان — خروجی: [cx, cy, w, h, angle].
     *  معادلِ Imgproc.minAreaRect (پوشِ محدبِ ورودی ملاک است). */
    private fun minAreaRect(hull: Array<DoubleArray>): DoubleArray? {
        if (hull.size < 3) return null
        var best = DoubleArray(5)
        var bestArea = Double.MAX_VALUE
        val n = hull.size
        for (i in 0 until n) {
            val p1 = hull[i]
            val p2 = hull[(i + 1) % n]
            val dx = p2[0] - p1[0]
            val dy = p2[1] - p1[1]
            val len = hypot(dx, dy)
            if (len < 1e-9) continue
            val ux = dx / len
            val uy = dy / len
            var minA = Double.MAX_VALUE; var maxA = -Double.MAX_VALUE
            var minB = Double.MAX_VALUE; var maxB = -Double.MAX_VALUE
            for (p in hull) {
                val a = p[0] * ux + p[1] * uy
                val b = -p[0] * uy + p[1] * ux
                if (a < minA) minA = a
                if (a > maxA) maxA = a
                if (b < minB) minB = b
                if (b > maxB) maxB = b
            }
            val area = (maxA - minA) * (maxB - minB)
            if (area < bestArea) {
                bestArea = area
                // مرکز در چارچوبِ چرخیده → برگشت به مختصاتِ اصلی
                val ca = (minA + maxA) / 2.0
                val cb = (minB + maxB) / 2.0
                val cx = ca * ux - cb * uy
                val cy = ca * uy + cb * ux
                best = doubleArrayOf(cx, cy, maxA - minA, maxB - minB,
                    atan2(uy, ux))
            }
        }
        return if (bestArea < Double.MAX_VALUE) best else null
    }

    /** گوشههایِ RotatedRect (همان قراردادِ cv::RotatedRect::points). */
    private fun cornersOf(rect: DoubleArray): Array<DoubleArray> {
        val cx = rect[0]; val cy = rect[1]
        val hw = rect[2] / 2.0; val hh = rect[3] / 2.0
        val cosA = cos(rect[4])
        val sinA = sin(rect[4])
        return arrayOf(
            doubleArrayOf(cx - cosA * hw - (-sinA) * hh, cy - sinA * hw - cosA * hh),
            doubleArrayOf(cx + cosA * hw - (-sinA) * hh, cy + sinA * hw - cosA * hh),
            doubleArrayOf(cx + cosA * hw + (-sinA) * hh, cy + sinA * hw + cosA * hh),
            doubleArrayOf(cx - cosA * hw + (-sinA) * hh, cy - sinA * hw + cosA * hh),
        )
    }

    // ── BoxSorter (رسمی) ──
    private fun boxSorter(boxes: List<FloatArray>): List<FloatArray> {
        if (boxes.size <= 1) return boxes
        val list = boxes.toMutableList()
        list.sortWith(compareBy({ it[1] }, { it[0] }))
        for (i in 0 until list.size - 1) {
            var j = i
            while (j >= 0) {
                val next = list[j + 1]
                val curr = list[j]
                if (abs(next[1] - curr[1]) < ROW_THRESHOLD_Y &&
                    next[0] < curr[0]
                ) {
                    list[j] = next
                    list[j + 1] = curr
                    j--
                } else break
            }
        }
        return list
    }

    // ── QuadTextCrop (رسمی): minAreaRectِ دوباره + پرسپکتیو + چرخش ──
    /** خروجی: (پیکسلها یا null، [w, h] بعد از چرخشِ احتمالی) */
    private fun cropQuad(px: IntArray, sw: Int, sh: Int,
                         quad: FloatArray): Pair<IntArray?, IntArray> {
        val rect = minAreaRect(convexHull((0 until 4).map {
            doubleArrayOf(quad[it * 2].toDouble(), quad[it * 2 + 1].toDouble())
        }) ?: return Pair(null, intArrayOf(0, 0)))
            ?: return Pair(null, intArrayOf(0, 0))
        val ordered = orderRectPoints(cornersOf(rect))
        val wt = hypot((ordered[2] - ordered[0]).toDouble(),
            (ordered[3] - ordered[1]).toDouble())
        val wb = hypot((ordered[4] - ordered[6]).toDouble(),
            (ordered[5] - ordered[7]).toDouble())
        val hl = hypot((ordered[6] - ordered[0]).toDouble(),
            (ordered[7] - ordered[1]).toDouble())
        val hr = hypot((ordered[4] - ordered[2]).toDouble(),
            (ordered[5] - ordered[3]).toDouble())
        val dstW = max(wt, wb).toInt().coerceAtLeast(1)
        val dstH = max(hl, hr).toInt().coerceAtLeast(1)
        if (dstW < 2 || dstH < 2) return Pair(null, intArrayOf(0, 0))
        // bboxِ محصورکنندهٔ چهارضلعی + هموگرافیِ dst→src
        var minX = sw - 1; var maxX = 0; var minY = sh - 1; var maxY = 0
        for (k in 0 until 4) {
            val x = ordered[k * 2].toInt().coerceIn(0, sw - 1)
            val y = ordered[k * 2 + 1].toInt().coerceIn(0, sh - 1)
            if (x < minX) minX = x
            if (x > maxX) maxX = x
            if (y < minY) minY = y
            if (y > maxY) maxY = y
        }
        if (maxX <= minX || maxY <= minY) return Pair(null, intArrayOf(0, 0))
        val bw = maxX - minX + 1
        val bh = maxY - minY + 1
        val srcPts = Array(4) { k ->
            doubleArrayOf((ordered[k * 2] - minX).toDouble(),
                (ordered[k * 2 + 1] - minY).toDouble())
        }
        val dstPts = arrayOf(
            doubleArrayOf(0.0, 0.0),
            doubleArrayOf(dstW.toDouble(), 0.0),
            doubleArrayOf(dstW.toDouble(), dstH.toDouble()),
            doubleArrayOf(0.0, dstH.toDouble()))
        val inv = homographyInv(srcPts, dstPts)
            ?: return Pair(null, intArrayOf(0, 0))
        val out = IntArray(dstW * dstH)
        for (y in 0 until dstH) {
            for (x in 0 until dstW) {
                val denom = inv[6] * x + inv[7] * y + inv[8]
                val sx = (inv[0] * x + inv[1] * y + inv[2]) / denom
                val sy = (inv[3] * x + inv[4] * y + inv[5]) / denom
                // BORDER_REPLICATE + نمونهبرداریِ خطی (بجایِ INTER_CUBIC)
                val x0 = sx.toInt().coerceIn(0, bw - 1)
                val y0 = sy.toInt().coerceIn(0, bh - 1)
                val x1 = min(x0 + 1, bw - 1)
                val y1 = min(y0 + 1, bh - 1)
                val fx = (sx - x0).coerceIn(0.0, 1.0)
                val fy = (sy - y0).coerceIn(0.0, 1.0)
                val p00 = px[(minY + y0) * sw + (minX + x0)]
                val p01 = px[(minY + y0) * sw + (minX + x1)]
                val p10 = px[(minY + y1) * sw + (minX + x0)]
                val p11 = px[(minY + y1) * sw + (minX + x1)]
                out[y * dstW + x] = bilinearArgb(p00, p01, p10, p11, fx, fy)
            }
        }
        // h/w ≥ 1.5 → چرخشِ ۹۰ درجهٔ پادساعتگرد (رسمی Core.ROTATE_90_CCW)
        if (dstH.toDouble() / dstW.toDouble() >= VERTICAL_CROP_RATIO) {
            val rot = IntArray(dstW * dstH)
            // rot[i][j] = src[j][W-1-i]؛ ابعاد عوض میشوند (dstH×dstW)
            for (i in 0 until dstW) {
                for (j in 0 until dstH) {
                    rot[i * dstH + j] = out[j * dstW + (dstW - 1 - i)]
                }
            }
            return Pair(rot, intArrayOf(dstH, dstW))
        }
        return Pair(out, intArrayOf(dstW, dstH))
    }

    private fun bilinearArgb(p00: Int, p01: Int, p10: Int, p11: Int,
                             fx: Double, fy: Double): Int {
        var out = 0
        for (shift in intArrayOf(16, 8, 0)) {
            val c00 = (p00 shr shift) and 0xFF
            val c01 = (p01 shr shift) and 0xFF
            val c10 = (p10 shr shift) and 0xFF
            val c11 = (p11 shr shift) and 0xFF
            val top = c00 + (c01 - c00) * fx
            val bot = c10 + (c11 - c10) * fx
            val v = (top + (bot - top) * fy).toInt().coerceIn(0, 255)
            out = out or (v shl shift)
        }
        return out or (0xFF shl 24)
    }

    /** هموگرافیِ src→dst و معکوسِ آن (حلِ دستگاهِ ۸×۸ — هم‌کارِ
     *  getPerspectiveTransform). خروجی: عناصرِ ماتریسِ ۳×۳ِ معکوس
     *  (dst→src) به‌ترتیبِ سطری. */
    private fun homographyInv(src: Array<DoubleArray>,
                              dst: Array<DoubleArray>): DoubleArray? {
        val A = Array(8) { DoubleArray(9) }
        for (k in 0 until 4) {
            val x = src[k][0]; val y = src[k][1]
            val u = dst[k][0]; val v = dst[k][1]
            A[2 * k][0] = x; A[2 * k][1] = y; A[2 * k][2] = 1.0
            A[2 * k][3] = 0.0; A[2 * k][4] = 0.0; A[2 * k][5] = 0.0
            A[2 * k][6] = -u * x; A[2 * k][7] = -u * y
            A[2 * k][8] = u
            A[2 * k + 1][0] = 0.0; A[2 * k + 1][1] = 0.0; A[2 * k + 1][2] = 0.0
            A[2 * k + 1][3] = x; A[2 * k + 1][4] = y; A[2 * k + 1][5] = 1.0
            A[2 * k + 1][6] = -v * x; A[2 * k + 1][7] = -v * y
            A[2 * k + 1][8] = v
        }
        // حذفِ گوس با محورِ جزئی
        for (col in 0 until 8) {
            var piv = col
            var bestAbs = abs(A[col][col])
            for (r in col + 1 until 8) {
                val v = abs(A[r][col])
                if (v > bestAbs) { bestAbs = v; piv = r }
            }
            if (bestAbs < 1e-12) return null
            if (piv != col) {
                val tmp = A[col]; A[col] = A[piv]; A[piv] = tmp
            }
            val dv = A[col][col]
            for (c in col until 9) A[col][c] /= dv
            for (r in 0 until 8) {
                if (r == col) continue
                val fct = A[r][col]
                if (fct == 0.0) continue
                for (c in col until 9) A[r][c] -= fct * A[col][c]
            }
        }
        val h = DoubleArray(9)
        for (k in 0 until 8) h[k] = A[k][8]
        h[8] = 1.0
        // معکوسِ استانداردِ ۳×۳ (سطری):
        // [a b c; d e f; g h i] → inverse/det =
        // [ei−fh  ch−bi  bf−ce; fg−di  ai−cg  cd−af; dh−eg  bg−ah  ae−bd]
        val m = h
        val a = m[0]; val b = m[1]; val c = m[2]
        val d = m[3]; val e2 = m[4]; val f = m[5]
        val g = m[6]; val hh = m[7]; val i2 = m[8]
        val t00 = e2 * i2 - f * hh
        val t11 = a * i2 - c * g
        val t22 = a * e2 - b * d
        val det = a * t00 - b * (d * i2 - f * g) + c * (d * hh - e2 * g)
        if (abs(det) < 1e-12) return null
        return doubleArrayOf(
            t00 / det, (c * hh - b * i2) / det, (b * f - c * e2) / det,
            (f * g - d * i2) / det, t11 / det, (c * d - a * f) / det,
            (d * hh - e2 * g) / det, (b * g - a * hh) / det, t22 / det)
    }

    // ── RecPreprocessor (رسمی): RGB، h=48، بچِ پدشده + CTCDecoder ──
    private fun recBatchWithDims(crops: List<Pair<IntArray?, IntArray>>):
            List<Pair<String, Float>> {
        val n = crops.size
        if (n == 0) return emptyList()
        val mats = ArrayList<Triple<FloatArray, Int, Int>>(n)
        var maxW = 8
        for ((pix, dims) in crops) {
            if (pix == null) {
                mats.add(Triple(FloatArray(3 * REC_FIXED_H * 8), 8, REC_FIXED_H))
                continue
            }
            val w = dims[0]
            val h = dims[1]
            val newW = ceil(REC_FIXED_H * (w.toDouble() / max(1, h).toDouble()))
                .toInt().coerceAtMost(REC_MAX_W).coerceAtLeast(1)
            val chan = REC_FIXED_H * newW
            val data = FloatArray(3 * chan)
            resizeTo48RgbNormalize(pix, w, h, newW, data)
            mats.add(Triple(data, newW, REC_FIXED_H))
            if (newW > maxW) maxW = newW
        }
        val channel = REC_FIXED_H * maxW
        val tensor = FloatArray(n * 3 * channel)
        for (b in 0 until n) {
            val (data, w, h) = mats[b]
            for (c in 0 until 3) {
                val srcOff = c * w * h
                val dstOff = (b * 3 + c) * channel
                for (y in 0 until h) {
                    System.arraycopy(data, srcOff + y * w,
                        tensor, dstOff + y * maxW, w)
                }
            }
        }
        val e = env!!
        val out = ArrayList<Pair<String, Float>>(n)
        OnnxTensor.createTensor(e, FloatBuffer.wrap(tensor),
            longArrayOf(n.toLong(), 3, REC_FIXED_H.toLong(), maxW.toLong())
        ).use { t ->
            recSession!!.run(mapOf(recInputName() to t)).use { r ->
                val ot = r[0] as OnnxTensor
                val sh = ot.shape
                val tSteps = sh[1].toInt()
                val nCls = sh[2].toInt()
                val fb = ot.floatBuffer
                val buf = FloatArray(n * tSteps * nCls)
                fb.get(buf)
                for (b in 0 until n) {
                    out.add(ctcDecode(buf, b, tSteps, nCls))
                }
            }
        }
        return out
    }

    private fun recInputName(): String =
        recSession!!.inputNames.iterator().next()

    /** resizeِ خطیِ دستی + BGR→RGB + (x/127.5 − 1) — دقیقاً
     *  RecPreprocessorِ رسمی (نرمالسازیِ یک‌ارزشی به هر ۳ کانال). */
    private fun resizeTo48RgbNormalize(px: IntArray, sw: Int, sh: Int,
                                       dw: Int, out: FloatArray) {
        val dh = REC_FIXED_H
        val chan = dw * dh
        val xRatio = if (dw > 1) (sw - 1).toDouble() / (dw - 1) else 0.0
        val yRatio = if (dh > 1) (sh - 1).toDouble() / (dh - 1) else 0.0
        // کانالهایِ RGB در NCHW: c=0 → R، c=1 → G، c=2 → B
        for (c in 0 until 3) {
            val o = c * chan
            for (y in 0 until dh) {
                val fy = y * yRatio
                val y0 = fy.toInt()
                val y1 = min(y0 + 1, sh - 1)
                val ly = fy - y0
                for (x in 0 until dw) {
                    val fx = x * xRatio
                    val x0 = fx.toInt()
                    val x1 = min(x0 + 1, sw - 1)
                    val lx = fx - x0
                    val p00 = px[y0 * sw + x0]
                    val p01 = px[y0 * sw + x1]
                    val p10 = px[y1 * sw + x0]
                    val p11 = px[y1 * sw + x1]
                    val ch = when (c) { 0 -> 16; 1 -> 8; else -> 0 }
                    val v00 = (p00 shr ch) and 0xFF
                    val v01 = (p01 shr ch) and 0xFF
                    val v10 = (p10 shr ch) and 0xFF
                    val v11 = (p11 shr ch) and 0xFF
                    val top = v00 + (v01 - v00) * lx
                    val bot = v10 + (v11 - v10) * lx
                    val v = (top + (bot - top) * ly).toFloat()
                    out[o + y * dw + x] = (v / 127.5f) - 1.0f
                }
            }
        }
    }

    /** CTCDecoder (رسمی): blank=0، idx−1، اطمینان = میانگینِ نمرههایِ
     *  نویسههایِ نگهشده. */
    private fun ctcDecode(output: FloatArray, b: Int, tSteps: Int,
                          nCls: Int): Pair<String, Float> {
        val base = b * tSteps * nCls
        val sb = StringBuilder()
        var sum = 0.0
        var kept = 0
        var prev = -1
        for (t in 0 until tSteps) {
            val off = base + t * nCls
            var maxIdx = 0
            var maxVal = output[off]
            for (c in 1 until nCls) {
                val v = output[off + c]
                if (v > maxVal) { maxVal = v; maxIdx = c }
            }
            if (maxIdx != 0 && maxIdx != prev) {
                val ci = maxIdx - 1
                if (ci >= 0 && ci < characters.size) {
                    sb.append(characters[ci])
                    sum += maxVal
                    kept++
                }
            }
            prev = maxIdx
        }
        val conf = if (kept > 0) (sum / kept).toFloat() else 0f
        return Pair(sb.toString(), conf)
    }

    // ── ModelConfig.parse (رسمی): character_dict از inference.yml ──
    private fun parseCharset(content: String): List<String> {
        val lines = content.replace("\r\n", "\n").replace('\r', '\n').split("\n")
        val postLine = lines.indexOfFirst { it.trim() == "PostProcess:" }
        if (postLine < 0) return emptyList()
        val postIndent = leadingSpaces(lines[postLine])
        // character_dict:
        var dictLine = -1
        for (i in postLine + 1 until lines.size) {
            val trimmed = lines[i].trim()
            if (trimmed.isEmpty() || trimmed.startsWith("#")) continue
            val indent = leadingSpaces(lines[i])
            if (indent <= postIndent) break
            if (trimmed == "character_dict:") { dictLine = i; break }
        }
        if (dictLine < 0) return emptyList()
        val dictIndent = leadingSpaces(lines[dictLine])
        val chars = ArrayList<String>(2048)
        var i = dictLine + 1
        while (i < lines.size) {
            val line = lines[i]
            val indent = leadingSpaces(line)
            val content2 = line.substring(min(indent, line.length))
            val key = content2.trim()
            if (key.isEmpty() || key.startsWith("#")) { i++; continue }
            if (!content2.startsWith("-")) {
                if (indent <= dictIndent) break
                i++
                continue
            }
            chars.add(parseYamlScalar(content2.substring(1)))
            i++
        }
        if (chars.isEmpty()) return emptyList()
        // رسمی: اگر آخری فاصله نیست، « » اضافه شود
        val out = chars.toMutableList()
        if (out.lastOrNull() != " ") out.add(" ")
        return out
    }

    private fun leadingSpaces(line: String): Int {
        val i = line.indexOfFirst { it != ' ' }
        return if (i < 0) line.length else i
    }

    private fun parseYamlScalar(raw: String): String {
        val v = raw.dropWhile { it == ' ' }
        if (v.length >= 2 && v.first() == '\'' && v.last() == '\'') {
            return v.substring(1, v.length - 1).replace("''", "'")
        }
        if (v.length >= 2 && v.first() == '"' && v.last() == '"') {
            return v.substring(1, v.length - 1)
        }
        return v
    }
}
