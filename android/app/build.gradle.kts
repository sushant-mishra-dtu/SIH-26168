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
        getByName("test") {
            java.srcDirs("src/test/kotlin")
        }
    }

    testOptions {
        unitTests {
            // The three classes under test are pure arithmetic, but two of them touch android.jar
            // for constants and for SystemClock. Without this, the stubbed android.jar throws
            // "Method ... not mocked" and the arithmetic never gets exercised.
            //
            // Returning defaults is safe *here* and would not be elsewhere: SessionClock's only
            // use of it is SystemClock.elapsedRealtimeNanos(), whose stubbed 0 makes the boot
            // anchor exactly System.currentTimeMillis() -- which is a legitimate device state
            // (a phone that has just booted) rather than an impossible one, so the mapping under
            // test is the real mapping. Anything that needs a *behaving* framework belongs in
            // androidTest on a device, not here.
            isReturnDefaultValues = true
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

    testImplementation(libs.junit)
    testImplementation("org.json:json:20231013")
}
