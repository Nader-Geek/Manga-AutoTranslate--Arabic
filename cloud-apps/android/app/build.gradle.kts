plugins {
    id("com.android.application")
}

android {
    namespace = "com.amirwolf.mangacloud"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.amirwolf.mangacloud"
        minSdk = 24
        targetSdk = 34
        versionCode = ((findProperty("cloudVersionCode") as String?) ?: "1").toInt()
        versionName = (findProperty("cloudVersionName") as String?) ?: "1.0"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }
}
