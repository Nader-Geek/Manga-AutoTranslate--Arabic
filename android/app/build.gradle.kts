plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

android {
    namespace = "com.amirwolf.mangatranslator"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.amirwolf.mangatranslator"
        minSdk = 24
        targetSdk = 34
        versionCode = 189
        versionName = "1.14.184"

        val buildAbis = ((findProperty("appAbis") as String?)
            ?: "arm64-v8a,armeabi-v7a")
            .split(",").map { it.trim() }.filter { it.isNotEmpty() }
        ndk {
            abiFilters += buildAbis
        }

    }

    packaging {
        // v1.14.67 — رویِ امولاتورِ x86_64 (ترجمهٔ arm64) لودِ .soِ
        // فشرده‌نشده از داخلِ APK ممکن است کار نکند → با -PlegacyJni=true
        // کتابخانه‌ها extract می‌شوند (فقط برایِ تستِ CI؛ پیش‌فرض false)
        jniLibs.useLegacyPackaging =
            ((findProperty("legacyJni") as String?) == "true")
        // v1.14.184 — AARِ رسمیِ OpenCV libc++_shared.soِ خودش را دارد؛
        // با chaquopy/ORT دوبله میشود → اولی انتخاب میشود
        jniLibs.pickFirsts += "lib/*/libc++_shared.so"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }
}


val engineRoot = rootProject.projectDir.parentFile
tasks.register<Copy>("copyEngineSources") {
    from(engineRoot) { include("manga.py", "manga_app.py") }
    into("src/main/assets/engine")
}
tasks.named("preBuild") { dependsOn("copyEngineSources") }


chaquopy {
    sourceSets {
        getByName("main") {
            exclude("rapidocr/models/*.onnx")
            exclude("rapidocr/models/*.onnx.*")
            exclude("**/__pycache__/**")
        }
    }
    defaultConfig {
        version = "3.10"
        buildPython = listOf(
            (findProperty("chaquopyBuildPython") as String?) ?: "python3")
        pip {
            install("numpy==1.26.2")
            install("opencv-python==4.5.1.48")
            install("pillow")
            install("arabic-reshaper")
            install("python-bidi==0.4.2")
            install("pyyaml")
            install("requests")
            install("six")
            install("tqdm")
            // v1.14.120 — omegaconf/colorlog/shapely حذف شدند: هیچ جایی از
            // موتور (manga.py/manga_app.py) importشان نمیکند (~۵MB در هر APK)
        }
    }
}

// v1.14.184 — موتورِ OCRِ گوشی = SDKِ رسمیِ PaddleOCR اندروید، بیت‌به‌بیت
// (ماژولِ :ppocr-sdk وندورشده از PaddleOCR/deploy/ppocr-android — پرتِ
// رسمیِ paddleocr.ai …/android_deployment.html). دستورِ سازنده:
// «هرروشی تو و گوشی واسه استخراج شده حذف کن فقط از همین لینک بالا
// استفاده کنه» → پرتِ دستیِ ONNXِ 182/183 (که هیچ متنی برنمیگرداند)
// کامل حذف شد و پلِ PaddleOcrBridge.kt حالا فقط پلِ نازک رویِ
// PaddleOCR.createِ رسمی است. مدلهایِ رسمیِ PP-OCRv6_small (det 9.9MB +
// rec 21.2MB + inference.yml) زمانِ بیلدِ CI از HuggingFaceِ رسمی
// دانلود و در assetsِ APK باندل میشوند (هیچ دانلودِ زمانِ اجرایی —
// آفلاین هم کار میکند). ML Kit از 183 کامل حذف است.
dependencies {
    // v1.14.184 — وابستگیِ مستقیمِ ORT از app حذف شد: ORT فقط مالِ
    // SDKِ رسمی است (نسخهٔ رسمیِ 1.21.1 داخلِ :ppocr-sdk؛ رویِ شبیهسازِ
    // CI همان قراردادِ -PortVer=1.28 اعمال میشود).
    // v1.14.183 — وابستگیهایِ com.google.mlkit حذف شدند (دستورِ سازنده:
    // «ml kit حذف کن خوب نیست») — استخراج = پدلِ رسمیِ اندروید.
    // v1.14.184 — SDKِ رسمی + coroutines (برایِ runBlockingِ پل)
    implementation(project(":ppocr-sdk"))
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.recyclerview:recyclerview:1.3.2")
    implementation("com.google.android.material:material:1.12.0")
}
