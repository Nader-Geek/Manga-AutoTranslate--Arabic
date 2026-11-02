// v1.14.184 — ماژولِ «ppocr-sdk» = SDKِ رسمیِ PaddleOCR اندروید، وندورشده
// بیت‌به‌بیت از پرتِ رسمیِ (PaddleOCR/deploy/ppocr-android) — همان لینکی که
// سازنده دستور داده: «فقط از همین لینک بالا استفاده کنه»
//   https://www.paddleocr.ai/latest/en/version3.x/inference_deployment/
//   cross_platform/android_deployment.html
// کدِ com.paddle.ocr.** هیچ تغییری نکرده (DetPreprocessor → DBPostProcessor
// → QuadTextCrop → RecPreprocessor → CTCDecoder — عینِ الگوریتمِ رسمی).
// فقط فایلِ build این ماژول با ساختارِ این اپ سازگار شده:
//   • version-catalog نداریم → وابستگیها با نشانیِ مستقیم (همان شمارههایِ
//     رسمیِ README: ORT 1.21.1 / OpenCV 4.5.3 / coroutines 1.9.0).
//   • ortVer: رویِ شبیهسازِ x86_64 (CI) ORTِ 1.31 در sess.run خطایِ
//     SIGFPE میدهد → CI با -PortVer=1.28 بیلد میکند (قراردادِ قدیمیِ
//     v1.14.67)؛ رویِ گوشی پیشفرضِ رسمیِ 1.21.1 استفاده میشود.
//   • androidTestِ رسمی (بنچمارک) حذف شد — مدلها در assetsِ خودِ اپ
//     قرار میگیرند، نه assetsِ SDK؛ اجرایِ تستِ رسمی اینجا مدل ندارد.
plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.paddle.ocr"
    compileSdk = 35

    defaultConfig {
        minSdk = 26
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            consumerProguardFiles("proguard-rules.pro")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation("com.microsoft.onnxruntime:onnxruntime-android:${(rootProject.findProperty("ortVer") as String?) ?: "1.21.1"}")
    implementation("com.quickbirdstudios:opencv:4.5.3")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
}
