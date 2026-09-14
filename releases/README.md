# Android Demo Builds

Pre-built APKs for testing on mobile devices without needing a local Android Studio / Gradle
environment. The APK here is the `osm` flavour of `android-ui/` (the operator UI, application id
`com.sih.idr.demo`); the foreground logger in `android/` is a separate app and is not shipped here.

What changed between builds is [CHANGELOG.md](../CHANGELOG.md); why it changed is
[docs/DECISION_LOG.md](../docs/DECISION_LOG.md).

## Available Builds

| Flavour | File | Version | Built from | Description |
|---|---|---|---|---|
| **OSM (Offline Basemap)** | [`app-osm-debug.apk`](app-osm-debug.apk) (16.4 MiB) | v0.1.2 (`versionCode` 2) | `main` @ `8047647`, 14 Sep 2026 | Standalone build using bundled OSMDroid offline raster tiles. Requires no API keys. Includes the navigation UI, the autonomous tunnel state machine (D-126), the turn guidance banner, the error covariance ellipse (D-125), and the course-over-ground heading and duration-based ZUPT fixes from the 14 Sep road test (D-127). |

The `mapbox` flavour is **not** published: it needs a Mapbox downloads token to build and a public
token to run (D-122), and neither is checked in. Build it locally per
[`android-ui/README.md`](../android-ui/README.md) if you have the tokens.

### Direct Mobile Download
On your Android phone, you can download the APK directly from `main`:
- [Direct Raw Download: app-osm-debug.apk](https://github.com/sushant-mishra-dtu/SIH-26168/raw/main/releases/app-osm-debug.apk)

### Latest CI build
Every push to `main` and every pull request also uploads a fresh `app-osm-debug` artifact from the
**operator UI** job of [`.github/workflows/android.yml`](../.github/workflows/android.yml). Open the
run on the Actions tab and download the artifact from the summary page — it is the same flavour
built from the exact commit under test, which is what to install when checking a change before it
is copied here.

### GitHub Releases
Pushing a `v*` tag runs [`.github/workflows/release.yml`](../.github/workflows/release.yml), which
attaches the committed `app-osm-debug.apk` to a GitHub Release named after the tag — the stable
link to hand to judges or teammates who should not be browsing the repo. Note that it publishes
the file *in this folder* at the tagged commit, not a fresh build, so copy the APK in and update
the table above before tagging:

```bash
git tag v0.1.2 && git push origin v0.1.2
```

Copy the APK in **before** tagging, or the release will carry the previous build under the new
version's name.

### Installation
1. Tap the download link on your phone.
2. If prompted, enable "Install unknown apps" for your browser.
3. Open the downloaded file to install or update the app.

### Updating this file
When a new APK is copied in, update the **Version** and **Built from** columns with the
`versionName`/`versionCode` in `android-ui/app/build.gradle.kts` and the commit it was assembled
from, add the entry to [CHANGELOG.md](../CHANGELOG.md), and delete the note under the table — an APK whose origin cannot be named is not evidence of anything (the same rule the
evaluation harness applies to every plot).
