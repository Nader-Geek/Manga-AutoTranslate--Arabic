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
<<<<<<< HEAD
        versionCode = 210
        versionName = "1.14.207"
=======
        versionCode = 210
        versionName = "1.14.207"
>>>>>>> a367a3b (v1.14.204: پاکسازی — لگهٔ سیاه/سفید + متنِ جامانده + قابِ رنگیِ حباب (دستورِ سازنده: «پاکسازی لگه سیاه یا سفید میزاره یا متن قبلی جا میزاره… هم openvc هم حالت lama onnx… سبک پاکسازیم اینه دوتا عکس ساخته میشه عکس اول کامل خوب پاک میشه بعد به اندازه خوده متن خط به خط برش بزنه انتقال بده به عکس دوم و نباید عکس دوم حباب متن خراب شه… فقط همون اندازه حباب باید پاکسازی کنه نه کل صحفه رو… هم گوشی هم پی سی لینوکس باید هردو عکس هاشون چک کنی… یک عکس درست کردی از اول دوباره همه عکس هارو مجدد برو پاکسازیش تست کن») — بنچمارکِ عینیِ ۱۳ عکسِ ci_imgs × ۲ روش (scripts/clean_bench.py — متریکِ هر ناحیه: جوهرِ دستنخورده/ضربهٔ باقیمانده/لگهٔ سیاه/سفیدِ تازه/آسیبِ بیرونِ ماسک با پسزمینهٔ محلیِ کانولوشنِ نرمالشده) — (۱) ریشهٔ «متنِ قبلی جا میزاره» رویِ متنِ سند-روی-پنل (PARAGRAPHهایِ img4): قطبِ جوهرِ _line_strip_ink با «اکثریت» انتخاب میشد و پنلِ نیمهشفافِ روشنِ پشتِ متن را جوهر میگرفت → نوار رد → failed = پرِ کاملِ پالی → کامپوزِ کلِ بلوک = ابرِ خاکستریِ Telea (full_diffِ ۱٫۳M). حالا: اگر قطبِ اکثریت >۵۵٪ نوار شد، قطبِ «اقلیت» جوهرِ واقعی است (204c) — نوارِ سالمِ متن ساخته میشود — تست: strips=3853px برایِ پنجرهٔ پنل-روشن (۲) ریشهٔ دوم: خطِ ردشده «کلِ پالی» را در failed پر میکرد (حتی خطِ چاقِ چندسطری) → failed حالا = «جوهرِ دو-قطبیِ داخلِ پالی (+۱۰px برایِ دورخط) + حفرههایِ حروف − میلههایِ بلندِ نازک (openِ ۴۱ منهایِ openِ ۷×۷ تا کلمهٔ بولدِ فشرده GUARDIANS قربانی نشود)» (204d/f) — ترتیبِ میله→حفره→میله چون حفرهِ اول جیبهایِ پنل را پر میکرد و open همه را میبلعید (204e) — نتیجهٔ img4: resid_same ۷۲-۸۹هزارpx → ۳-۱۳هزارpx، متن کامل میرود، حصارِ بینِ خطها اورجینال میماند (۳) ریشهٔ «لگهٔ سیاه» در opencv: Telea دورِ ماسک را میکشد و دورخطِ سیاهِ متنِ دورخط‌دار را داخلِ پرش میآورد (تکههایِ سیاهِ img3-r3) → ترمیمِ «تکهٔ سیاهِ تازه» در انتهایِ _opencv_inpaint_hq: هر کامپوننتِ تیرهٔ تازهٔ داخلِ ماسک (خروجی<۷۰ جایی که بیشینهٔ محلیِ اورجینال>۱۱۰) با «میانهٔ رنگِ حلقهٔ روشنِ اورجینال» + لبهٔ فدر پر میشود (204g/h) — bN: ۲۲۴۱→۲۰۷ (۴) ریشهٔ «قابِ رنگیِ حباب تکهتکه میشه» (حبابهایِ ششضلعیِ سبزِ up0822): قاب = خطِ نازکِ اشباعِ رنگی — نه تیرهِ خالص (از معیارِ darkِ protect جا میماند) نه قابلِ تشخیص در نوار — چرخهٔ کامل: نقشهٔ جداگانهٔ «فقطِ قابِ رنگی» (_page_colored_protect — اشباع≥۷۰ + نازکِ dt≤۱۴ + رسای ۶۰px + گسترشِ هم-هیوئیِ درامتدادِ خط برایِ تقاطع با حرف، 204j/k/l/q/r/s)؛ قاب در ماسکِ فعال میماند تا LaMa آن را با زمینهٔ حباب پر کند (نه اینکه رنگش را به متن بکشد — لکهٔ سبزِ حبابهایِ ۳/۴)، از نوارهایِ کامپوز (204m) و از _cmpِ نهایی (204n) کم میشود و در انتهای clean_image از اورجینال «بازپسگیری» میشود (204p) — خروجی: قابِ هر ۴ حبابِ up0822 سالمِ کامل (green_ratio=۰٫۹۸) + متنِ ۱۰۰٪ پاک؛ رگرسیونِ img6 (حبابِ زردِ rimِ تیره): صفرِ آسیب — «l»یِ Alright برنگشته (گسترشِ هم-هیوئی وسطِ حباب را وصل نمیکند) (۵) پسگیرِ جوهرِ جامانده (_stray_ink_reclaim) از گیتِ اندرویدِ 134 خارج شد — روی PC/Linux هم فعال (دستور: «هم گوشی هم پی سی لینوکس»)؛ با env=0 خاموششدنی (۶) گیتِ پولیشِ ۱۴٫۸۲: skipِ «خروجیِ بافت‌مند» فقط وقتی که حلقهٔ اورجینال هم غیر-یکنواخت است — حلقهٔ تخت (حبابِ زرد/سفید) همیشه پولیش میشود (204o) — تستِ عملی: scripts/test_v114204_cleanup.py (۷ گیتِ سبز: قطبِ اقلیت + failedِ جوهر-نه-پالی + بولد-جان‌به‌در + reclaimِ PC + قابِ رنگی در نقشه + ترمیمِ لکهٔ سیاهِ ساختگی + رگرسیونِ واقعیِ up0822) + بنچمارکِ نهاییِ ۱۳ عکس × ۲ روش: img2/img3/img5/img6/up0904/lang_* = صفرِ خطا در lama؛ img7 = متنِ YEAH YEAH/also/YEP! کامل پاک (فقط coی کم-اهمیت)؛ up0929: res ۲۰-۲۵٪→۷٪؛ img4: بدِ opencv ۷→۶ و lama ۱۲→۱۱ — رگرسیونِ ۱۹۷-۲۰۳: گیتهایِ نسخهای pinشده + رگرسیونِ تصویریِ up0822/img6/img7/img3 کنترلِ چشمی شد)

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

// v1.14.187 — موتورِ OCRِ گوشی = RapidOCRِ اندروید (RapidOcrAndroidOnnx)
// دستورِ سازنده: «متن درست استخراج نمیزنه متن هاش اشتباهه بعضی وقتا
// ۱.۱۴.۱۸۶ … ببین چجور به این خوبی استخراج میکنه همونو رو گوشی بزار …
// نمیشه یک زبان انتخاب کرد مثلا انگلیسی بزارم». سهگانهٔ
// ch_PP-OCRv4_det_mobile + ch_ppocr_mobile_v2.0_cls +
// ch_PP-OCRv4_rec_mobile (+ واریانتهایِ en/ja/ko + دیکشنریها) داخلِ
// ماژولِ :ppocr-sdk رویِ همان ORTِ رسمی (1.21.1) اجرا میشود؛ پلِ
// PaddleOcrBridge.kt فقط پلِ نازک رویِ RapidOcr.create است (هیچ
// ORT/پردازشی از خودش ندارد). مدلها زمانِ بیلدِ CI از ModelScopeِ
// رسمیِ RapidAI/RapidOCR (v3.9.2) دانلود و در assetsِ APK باندل
// میشوند (هیچ دانلودِ زمانِ اجرایی — آفلاین هم کار میکند).
// انتخابِ زبان = تعویضِ داغِ سشنِ rec با واریانتِ زبانِ هر کراپ.
// ML Kit از 183 کامل حذف است.
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
