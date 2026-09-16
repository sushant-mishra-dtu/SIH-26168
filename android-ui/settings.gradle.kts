pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()

        // Mapbox Maven, for the `mapbox` product flavour only (D-121, D-122). The repository
        // refuses anonymous downloads, so it takes the *secret* `Downloads:Read` token as the
        // password. That token lives in the per-machine `~/.gradle/gradle.properties` (or the
        // `ORG_GRADLE_PROJECT_MAPBOX_DOWNLOADS_TOKEN` environment variable in CI) and never in
        // this repository. The username is the literal string "mapbox", not an account name.
        //
        // The repository is declared only when the token is present so that a machine or CI
        // runner without a Mapbox account still resolves the `osm` flavour. Without it, the
        // `mapbox` flavour fails at dependency resolution with "Could not find
        // com.mapbox.navigationcore:...", which is the honest error for that situation.
        val mapboxToken = providers.gradleProperty("MAPBOX_DOWNLOADS_TOKEN").orNull
        if (!mapboxToken.isNullOrBlank()) {
            maven {
                url = uri("https://api.mapbox.com/downloads/v2/releases/maven")
                authentication {
                    create<BasicAuthentication>("basic")
                }
                credentials {
                    username = "mapbox"
                    password = mapboxToken
                }
            }
        }
    }
}

rootProject.name = "idr-android-ui"
include(":app")
