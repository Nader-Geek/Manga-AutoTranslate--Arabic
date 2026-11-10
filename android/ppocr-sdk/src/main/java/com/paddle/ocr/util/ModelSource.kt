// Copyright (c) 2026 PaddlePaddle Authors. All Rights Reserved.
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
// http://www.apache.org/licenses/LICENSE-2.0
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// منبعِ مدل: اول assets (باندلِ قدیمی/تستِ CI)، بعد
// filesDir با همان مسیرِ نسبی (دانلودِ زمانِ اجرا — OcrModelStore).
// APK دیگر مدل باندل نمیکند.

package com.paddle.ocr.util

import android.content.Context
import java.io.File
import java.io.FileNotFoundException

object ModelSource {

    /** آیا منبعی برای این مسیر هست؟ (assets یا filesDir) */
    @JvmStatic
    fun exists(context: Context, path: String): Boolean =
        try {
            context.assets.open(path).use { true }
        } catch (_: Throwable) {
            val f = File(context.filesDir, path)
            f.isFile && f.length() > 0L
        }

    /** بایتهایِ مدل/دیکشنری از assets یا filesDir (همان مسیرِ نسبی). */
    @JvmStatic
    fun bytes(context: Context, path: String): ByteArray =
        try {
            context.assets.open(path).use { it.readBytes() }
        } catch (_: Throwable) {
            val f = File(context.filesDir, path)
            if (f.isFile && f.length() > 0L) {
                f.readBytes()
            } else {
                throw FileNotFoundException(
                    "model source not found: $path (assets و filesDir هر دو خالی)")
            }
        }

    /** متنِ دیکشنری/کانفیگ از assets یا filesDir. */
    @JvmStatic
    fun text(context: Context, path: String): String =
        String(bytes(context, path), Charsets.UTF_8)
}
