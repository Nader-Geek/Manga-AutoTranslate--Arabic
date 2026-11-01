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
        versionCode = 84
        versionName = "1.14.70"

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

// v1.14.120 — Paddle-Lite کلاً حذف شد (کرشهایِ RuntimeProgram + درخواستِ
// کاربر). PaddleLiteBridge.kt و PaddlePredictor.jar و fetch_paddle.py
// از مخزن پاک شدند؛ زنجیرهٔ OCR اندروید: ML Kit نیتیو → RapidOCR ONNX.


dependencies {
    // v1.14.67 — ortVer برایِ CIِ امولاتور: AARِ 1.31 رویِ x86_64 در
    // sess.run تقسیم‌برصفر (SIGFPE) می‌دهد → CI با 1.28 بیلد می‌کند
    // (APIِ جاوایِ shim با 1.28 هم سازگار است؛ گوشی همان 1.31 را می‌گیرد)
    implementation("com.microsoft.onnxruntime:onnxruntime-android:${(findProperty("ortVer") as String?) ?: "1.31.0"}")
    // v1.14.163 — ML Kit و Paddle-Lite کلاً حذف شدند (دستورِ سازنده:
    // «سبکِ استخراج و پاکسازی رو گوشی کامل حذف کنی») — استخراجِ متنِ
    // گوشی = detector-v4-s + PP-OCRv6 ONNX (عینِ PC)
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.recyclerview:recyclerview:1.3.2")
    implementation("com.google.android.material:material:1.12.0")
}
