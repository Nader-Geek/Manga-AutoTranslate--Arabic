// v1.14.187 — RapidOCRِ اندروید (PP-OCRv4_mobileِ ONNX) — عینِ
// RapidOcrAndroidOnnx (github.com/RapidAI/RapidOcrAndroidOnnx)
// ═══════════════════════════════════════════════════════════════════════
// دستورِ سازنده (v1.14.187 — نقلِ مستقیم):
//   «متن درست استخراج نمیزنه متن هاش اشتباهه بعضی وقتا ۱.۱۴.۱۸۶
//    https://github.com/RapidAI/RapidOcrAndroidOnnx ببین چجور به این
//    خوبی استخراج میکنه همونو رو گوشی بزار و این ک بگم باید اول
//    detector-v4-s_int8.onnx خوب قسمت های متن پیدا کنه بعد همون قسمت
//    باید استخراج متن استفاده کنه اونم درست در بیاره … این خیلی خوب
//    استخراج میزنه متن هاش خوب در میاره»
//
// معماری = همان سهگانهٔ RapidOcrAndroidOnnx ولی رویِ همان ORTِ
// ppocr-sdk (نسخهٔ 1.21.1) و با detِ داخلِ کراپ:
//   • det = ch_PP-OCRv4_det_mobile.onnx (DBNet 4.5MB) — پارامترهایِ
//     پیشفرضِ RapidOCR: maxSideLen=960/max، thresh=0.3،
//     boxScore=0.5، unclip=1.6، dilate 2×2 (مانندِ DbNet.cpp).
//   • cls = ch_ppocr_mobile_v2.0_cls (AngleNet) — resizeِ کشیدهٔ
//     192×48 + (x-127.5)/127.5 + argmaxِ ۲ کلاسه؛ خلافِ mostAngleِ
//     دموی RapidOCR (که همهٔ کراپها را با رأیِ اکثریت میچرخاند — برایِ
//     مانگایِ مخلوطِ افقی/عمودی خطرناک است) چرخشِ ۱۸۰ فقط وقتی انجام
//     میشود که امتیازِ cls ≥ 0.9 باشد (per-crop).
//   • rec = ch_PP-OCRv4_rec_mobile.onnx (CRNN 10.4MB) — resizeِ متناسب
//     با ارتفاعِ ۴۸ + (x-127.5)/127.5 (RGB — قراردادِ رسمیِ
//     PaddleOCR/RapidOCR-python) + CTC با blank=۰ و دیکشنریِ متنیِ
//     (سطرها + « »)؛ دقیقاً keysِ CrnnNet.cpp.
// واریانتِ زبان = تعویضِ داغِ سشنِ rec + دیکشنری (setLanguageVariant):
//   latin→en_PP-OCRv4 ، ja→japan_PP-OCRv4 ، ko→korean_PP-OCRv4 ،
//   zh/پیشفرض→ch_PP-OCRv4 — همان «انتخابِ زبان» که سازنده خواست.
// کانالِ RGB برایِ rec (رسماً درست؛ دموی C++ این تبدیل را ندارد ولی
// RapidOCRِ پایتونی و PaddleOCRِ رسمی BGR→RGB میکنند) — رویِ متنِ
// مانگا (تک رنگ) اثرِ عملی ندارد.
// خروجی = همان OCREngineResult → پلِ PaddleOcrBridge و پارسرِ manga.py
// بدونِ تغییرِ قرارداد (META|lang|n + ang|conf|box|text|blk).
// ═══════════════════════════════════════════════════════════════════════

package com.paddle.ocr.engine

import android.content.Context
import android.graphics.Bitmap
import com.paddle.ocr.EngineConfig
import com.paddle.ocr.PaddleOCRConfig
import com.paddle.ocr.model.ModelConfig
import com.paddle.ocr.model.OCRError
import com.paddle.ocr.model.OCRResult
import com.paddle.ocr.postprocess.BoxSorter
import com.paddle.ocr.postprocess.CTCDecoder
import com.paddle.ocr.postprocess.QuadTextCrop
import com.paddle.ocr.preprocess.RecPreprocessor
import com.paddle.ocr.util.BitmapUtils
import org.opencv.core.Core
import org.opencv.core.CvType
import org.opencv.core.Mat
import org.opencv.core.Scalar
import org.opencv.core.Size
import org.opencv.imgproc.Imgproc

/** پارامترهایِ RapidOCR — پیشفرضها = OcrEngine.kt دموی RapidOcrAndroidOnnx. */
data class RapidOcrParams(
    val maxSideLen: Int = 960,
    val detThresh: Float = 0.3f,
    val boxScoreThresh: Float = 0.5f,
    val unclipRatio: Float = 1.6f,
    val doAngle: Boolean = true,
    val angleScoreThresh: Float = 0.9f,
    val recBatchSize: Int = 1,
    val recScoreThresh: Float = 0.0f,
) {
    internal fun toPaddleConfig(): PaddleOCRConfig = PaddleOCRConfig(
        detLimitSideLen = maxSideLen,
        detLimitType = "max",
        detThresh = detThresh,
        detBoxThresh = boxScoreThresh,
        detUnclipRatio = unclipRatio,
        // RapidOCRِ DbNet همیشه با هستهٔ ۲×۲ dilate میکند (DbNet.cpp) —
        // DBPostProcessorِ رسمی همان هستهٔ ۲×۲ را دارد (Mat.ones(2,2))
        detUseDilation = true,
        recBatchSize = recBatchSize,
        recScoreThresh = recScoreThresh,
    )
}

class RapidOcrEngine(
    context: Context,
    engineConfig: EngineConfig,
    detModelAsset: String,
    clsModelAsset: String,
    recModelAsset: String,
    recDictAsset: String,
    private val params: RapidOcrParams = RapidOcrParams(),
) {
    private val appContext: Context = context.applicationContext
    private val ortManager = ORTSessionManager(appContext, engineConfig)
    private val detectionEngine: DetectionEngine
    private val recLock = Any()

    @Volatile
    private var characters: List<String> = emptyList()

    @Volatile
    private var recAssetPath: String = recModelAsset

    val coldLoadTimeMs: Long get() = ortManager.coldLoadTimeMs

    init {
        try {
            ortManager.loadModels(detModelAsset, recModelAsset)
            if (clsModelAsset.isNotBlank()) {
                ortManager.loadClsModel(clsModelAsset)
            }
            characters = loadDict(appContext, recDictAsset)
        } catch (t: Throwable) {
            ortManager.release()
            throw t
        }
        detectionEngine = DetectionEngine(ortManager, params.toPaddleConfig())
    }

    /**
     * v1.14.187 — انتخابِ زبانِ rec (تعویضِ داغِ سشن + دیکشنری).
     * زبانِ همان = no-op؛ خلافِ آن = سشنِ rec جدید + دیکشنریِ جدید.
     */
    fun setLanguageVariant(recModelAsset: String, recDictAsset: String) =
        synchronized(recLock) {
            if (recModelAsset == recAssetPath) return
            ortManager.loadRecModel(recModelAsset)
            characters = loadDict(appContext, recDictAsset)
            recAssetPath = recModelAsset
        }

    fun run(bitmap: Bitmap): OCREngineResult {
        val srcMat = BitmapUtils.bitmapToBGRMat(bitmap)
        return runWithOwnedMat(srcMat)
    }

    fun run(imageBytes: ByteArray): OCREngineResult {
        val srcMat = BitmapUtils.imdecodeBGR(imageBytes)
        if (srcMat.empty()) {
            srcMat.release()
            throw OCRError.InvalidImage()
        }
        return runWithOwnedMat(srcMat)
    }

    private fun runWithOwnedMat(srcMat: Mat): OCREngineResult =
        try {
            run(srcMat)
        } finally {
            srcMat.release()
        }

    private fun run(srcMat: Mat): OCREngineResult {
        val totalStart = System.currentTimeMillis()
        val detResult = detectionEngine.detect(srcMat)
        val boxes = detResult.boxes

        if (boxes.isEmpty()) {
            return OCREngineResult(
                results = emptyList(),
                detectionTimeMs = detResult.timeMs,
                recognitionTimeMs = 0,
                totalTimeMs = System.currentTimeMillis() - totalStart,
                lineCount = 0,
                detPreprocessMs = detResult.preprocessMs,
                detInferenceMs = detResult.inferenceMs,
                detPostprocessMs = detResult.postprocessMs,
                detInputShape = detResult.inputShape,
                coldLoadTimeMs = ortManager.coldLoadTimeMs,
            )
        }

        val sortedBoxes = BoxSorter.sortInReadingOrder(boxes)
        val crops = mutableListOf<Mat>()
        val cropBoxIndices = mutableListOf<Int>()
        try {
            for ((idx, box) in sortedBoxes.withIndex()) {
                val crop = QuadTextCrop.crop(srcMat, box)
                if (crop.rows() > 0 && crop.cols() > 0) {
                    crops.add(crop)
                    cropBoxIndices.add(idx)
                } else {
                    crop.release()
                }
            }

            // ── cls (AngleNet): چرخشِ ۱۸۰ فقط با امتیازِ بالا (per-crop) ──
            if (params.doAngle && ortManager.hasCls() && crops.isNotEmpty()) {
                try {
                    val flags = classifyAngles(crops)
                    for (i in crops.indices) {
                        if (flags[i]) {
                            val rotated = Mat()
                            Core.flip(crops[i], rotated, -1)
                            crops[i].release()
                            crops[i] = rotated
                        }
                    }
                } catch (_: OCRError) {
                    // clsِ اختیاری است — هر خطا = بدونِ چرخش (مثلِ doAngle=false)
                }
            }

            // ── rec (CRNN با دیکشنریِ زبانِ فعال) ──
            var recPreMs = 0L
            var recInfMs = 0L
            var recPostMs = 0L
            val recShapes = mutableListOf<List<Int>>()
            val allResults = mutableListOf<OCRResult>()
            val batchSize = params.recBatchSize.coerceAtLeast(1)
            var i = 0
            synchronized(recLock) {
                while (i < crops.size) {
                    val batchEnd = minOf(i + batchSize, crops.size)
                    val batch = crops.subList(i, batchEnd)
                    if (batch.isNotEmpty()) {
                        val preStart = System.currentTimeMillis()
                        val pre = RecPreprocessor.preprocessBatch(batch)
                        recPreMs += System.currentTimeMillis() - preStart
                        val infStart = System.currentTimeMillis()
                        val (outData, outShape) = ortManager.runRecognition(pre.tensorData, pre.shape)
                        val postStart = System.currentTimeMillis()
                        val decoded = CTCDecoder.decode(outData, outShape, characters)
                        recPostMs += System.currentTimeMillis() - postStart
                        recInfMs += postStart - infStart
                        recShapes.add(pre.shape.map { it.toInt() })
                        for (j in decoded.indices) {
                            val (text, confidence) = decoded[j]
                            if (confidence >= params.recScoreThresh) {
                                allResults.add(
                                    OCRResult(
                                        box = sortedBoxes[cropBoxIndices[i + j]],
                                        text = text,
                                        confidence = confidence,
                                    )
                                )
                            }
                        }
                    }
                    i = batchEnd
                }
            }

            val totalElapsed = System.currentTimeMillis() - totalStart
            return OCREngineResult(
                results = allResults,
                detectionTimeMs = detResult.timeMs,
                recognitionTimeMs = recInfMs + recPostMs,
                totalTimeMs = totalElapsed,
                lineCount = allResults.size,
                detPreprocessMs = detResult.preprocessMs,
                detInferenceMs = detResult.inferenceMs,
                detPostprocessMs = detResult.postprocessMs,
                recPreprocessMs = recPreMs,
                recInferenceMs = recInfMs,
                recPostprocessMs = recPostMs,
                pipelineOverheadMs = totalElapsed - detResult.timeMs - recInfMs - recPostMs,
                coldLoadTimeMs = ortManager.coldLoadTimeMs,
                detInputShape = detResult.inputShape,
                recInputShapes = recShapes,
            )
        } finally {
            crops.forEach { it.release() }
        }
    }

    /**
     * AngleNetِ RapidOCR — دستهای: همهٔ کراپها به 192×48 کشیده میشوند
     * (BGR — قراردادِ رسمیِ predict_cls) و در یک run دستهبندی میشوند.
     * خروجی: flags[i] = این کراپ ۱۸۰ درجه بچرخد؟
     */
    private fun classifyAngles(crops: List<Mat>): BooleanArray {
        val clsW = 192
        val clsH = 48
        val n = crops.size
        val tensor = FloatArray(n * 3 * clsH * clsW)
        for (i in 0 until n) {
            val resized = Mat()
            Imgproc.resize(crops[i], resized, Size(clsW.toDouble(), clsH.toDouble()))
            val floatMat = Mat(clsH, clsW, CvType.CV_32FC3)
            resized.convertTo(floatMat, CvType.CV_32F)
            resized.release()
            Core.divide(floatMat, Scalar(127.5, 127.5, 127.5), floatMat)
            Core.subtract(floatMat, Scalar(1.0, 1.0, 1.0), floatMat)
            val channels = mutableListOf<Mat>()
            Core.split(floatMat, channels)
            val channelSize = clsH * clsW
            for (c in 0..2) {
                val buf = FloatArray(channelSize)
                channels[c].get(0, 0, buf)
                System.arraycopy(buf, 0, tensor, (i * 3 + c) * channelSize, channelSize)
                channels[c].release()
            }
            floatMat.release()
        }
        val (outData, outShape) = ortManager.runClassification(
            tensor, longArrayOf(n.toLong(), 3, clsH.toLong(), clsW.toLong()),
        )
        // خروجی = [N,2] — کلاسِ ۱ = متن ۱۸۰ درجه چرخیده
        val flags = BooleanArray(n)
        if (outData.size < n * 2) return flags
        for (b in 0 until n) {
            val s0 = outData[b * 2]
            val s1 = outData[b * 2 + 1]
            flags[b] = s1 > s0 && s1 >= params.angleScoreThresh
        }
        return flags
    }

    fun release() {
        synchronized(recLock) {
            ortManager.release()
        }
    }

    private fun loadDict(context: Context, dictAsset: String): List<String> {
        val content = try {
            context.assets.open(dictAsset).bufferedReader().use { it.readText() }
        } catch (t: Throwable) {
            throw OCRError.ConfigParseFailed(dictAsset, t)
        }
        return ModelConfig.fromDictText(content, dictAsset).characterList
    }
}
