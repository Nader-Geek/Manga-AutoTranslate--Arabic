package com.amirwolf.mangatranslator

import android.app.Application
import android.content.Context

/**
 *  — نگهدارندهٔ Contextِ سراسری برایِ پلِ استخراجِ متن.
 *
 * SDKِ رسمیِ PaddleOCR اندروید (ppocr-sdk — deploy/ppocr-android) برایِ
 * خواندنِ مدلها از assets و initِ OpenCV به Context نیاز دارد؛ چاکوپی از
 * داخلِ پایتون Context نمیدهد و پلِ قدیمیِ ONNX هم فایلِ مسیرِ مستقیم
 * میگرفت. MtApp اولین چیزی است که اندروید میسازد (قبل از هر Activity و
 * Service) → Contextِ اپ در onCreate همینجا یکبار ذخیره میشود.
 */
class MtApp : Application() {

    companion object {
        @Volatile
        private var appCtx: Context? = null

        @JvmStatic
        fun context(): Context? = appCtx
    }

    override fun onCreate() {
        super.onCreate()
        appCtx = applicationContext
// پلِ OCR هم همان اول Context را میگیرد (ساختِ موتور تنبل است —
// خودِ مدلها با اولین init(numThreads) لود میشوند)
        PaddleOcrBridge.hold(applicationContext)
    }
}
