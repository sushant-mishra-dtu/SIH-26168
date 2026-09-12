plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.sih.idr.demo"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.sih.idr.demo"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
    }

    packaging {
        resources.excludes += "/META-INF/{AL2.0,LGPL2.1}"
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.12.01")
    implementation(composeBom)
    androidTestImplementation(composeBom)

    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.10.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-service:2.8.7")

    // Compose UI
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")

    // Compose Animation
    implementation("androidx.compose.animation:animation")

    // --- what is deliberately NOT here ----------------------------------------------------
    // `ui-text-google-fonts` downloads its faces through the Play Services font provider, and
    // `osmdroid-android` fetches raster tiles from a tile server. Both are network calls at
    // runtime, and both were in this file. D-041 claims 100% offline and D-080 forbids the demo
    // surface any fetch -- a judging venue's wifi is not a dependency worth having. The map is a
    // Compose canvas over the recorded track instead; see MapView.kt.

    debugImplementation("androidx.compose.ui:ui-tooling")
}

