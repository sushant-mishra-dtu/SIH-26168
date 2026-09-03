plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "org.idr26168.logger"
    compileSdk = 35

    defaultConfig {
        applicationId = "org.idr26168.logger"
        // 26 (Android 8.0) is the floor, and it is set by two hard requirements, not by taste:
        //   - TYPE_ACCELEROMETER_UNCALIBRATED is API 26,
        //   - Context.startForegroundService / NotificationChannel are API 26.
        // Nothing below 26 can run this logger correctly, so nothing below 26 may install it.
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0-logger"
    }

    buildTypes {
        // Debug only, on purpose. There is no release signing config and no minification: a
        // logger that is obfuscated is a logger whose stack traces cost a drive to read.
        getByName("debug") {
            isMinifyEnabled = false
            applicationIdSuffix = ".debug"
        }
        getByName("release") {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        buildConfig = true
    }

    sourceSets {
        getByName("main") {
            java.srcDirs("src/main/kotlin")
        }
    }

    packaging {
        resources.excludes += "/META-INF/{AL2.0,LGPL2.1}"
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.androidx.activity)
}
