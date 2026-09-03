// Standalone Gradle build. It is deliberately NOT wired into the Python repo's tooling: the
// harness owns every number in the submission and must never be blocked on an Android SDK
// download (the same reasoning that keeps torch out of CI -- see .github/workflows/ci.yml).

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
    }
}

rootProject.name = "idr-logger"
include(":app")
