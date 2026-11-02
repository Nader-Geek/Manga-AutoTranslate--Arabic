pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositories {
        google()
        mavenCentral()
        maven("https://chaquo.com/maven")
    }
}

rootProject.name = "MangaTranslator"
include(":app")
// v1.14.184 — SDKِ رسمیِ PaddleOCR اندروید (وندورشده از
// PaddleOCR/deploy/ppocr-android — گزینهٔ ۱ «Source Code Dependency»
// از READMEِ رسمیِ پرتِ اندروید)
include(":ppocr-sdk")
