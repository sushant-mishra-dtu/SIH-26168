import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

// The Mapbox *public* token (`pk.`), read from the gitignored `local.properties` and injected as
// the `mapbox_access_token` string resource the Maps SDK looks up on its own (D-122). It is never
// committed: `tests/test_android_demo_surface.py` fails on a `pk.`/`sk.` literal anywhere under
// this module. An absent token still builds -- the `mapbox` flavour then shows a screen saying the
// token is missing (`MapView.kt`, D-080) rather than a blank map.
val mapboxPublicToken: String = run {
    val file = rootProject.file("local.properties")
    val fromFile = if (file.exists()) {
        Properties().apply { file.inputStream().use { load(it) } }.getProperty("MAPBOX_PUBLIC_TOKEN")
    } else {
        null
    }
    (fromFile ?: providers.gradleProperty("MAPBOX_PUBLIC_TOKEN").orNull ?: "").trim()
}

android {
    namespace = "com.sih.idr.demo"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.sih.idr.demo"
        minSdk = 26
        targetSdk = 35
        // `versionCode` is the install-ordering integer Android compares on an upgrade; it is
        // independent of `versionName` and increments once per published APK. `versionName` is
        // what the release tag and CHANGELOG.md name.
        versionCode = 2
        versionName = "0.1.2"
    }

    // Two map engines, one screen (D-121). `osm` is the OSMDroid canvas of D-117 and needs no
    // account; it is what CI always builds. `mapbox` is the Navigation SDK the plan is built on
    // (docs/UI_UX_NAVIGATION_PLAN.md section 7) and needs both Mapbox tokens. Everything outside
    // `ui/components/MapView.kt` and `ui/components/MapStack.kt` is shared in `src/main`.
    flavorDimensions += "map"
    productFlavors {
        create("osm") {
            dimension = "map"
            isDefault = true
        }
        create("mapbox") {
            dimension = "map"
            // A suffix so both flavours can sit on the team phone side by side.
            applicationIdSuffix = ".mapbox"
            versionNameSuffix = "-mapbox"
            resValue("string", "mapbox_access_token", mapboxPublicToken)
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

    // `osm` flavour: OSMDroid for online/cached OpenStreetMap raster tiles (D-117).
    "osmImplementation"("org.osmdroid:osmdroid-android:6.1.18")

    // `mapbox` flavour: Navigation SDK v3 core + its map components, and the Maps SDK Compose
    // extension, at the matching sub-version (section 7.10: same x.30 across all three). The
    // `-ndk27` artifacts carry 16 KB page-size support for targetSdk 35. Versions are pinned to
    // what section 7 was reviewed against; bump all three together.
    //
    // Deliberately NOT here: `com.google.android.gms:play-services-location`. The SDK docs suggest
    // it for "better raw location"; it would be a second location source next to ours, which is
    // exactly what rule R1 forbids.
    "mapboxImplementation"("com.mapbox.navigationcore:android-ndk27:3.30.1")
    "mapboxImplementation"("com.mapbox.navigationcore:ui-maps-ndk27:3.30.1")
    "mapboxImplementation"("com.mapbox.extension:maps-compose-ndk27:11.30.1")

    testImplementation("junit:junit:4.13.2")

    debugImplementation("androidx.compose.ui:ui-tooling")
}
