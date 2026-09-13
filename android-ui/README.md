# IDR Navigator — operator UI prototype

Jetpack Compose prototype of the demo surface for PS 26168. It is a **second** Gradle root and a
second application id (`com.sih.idr.demo`); the logger that produces the recordings the evaluation
actually reads is `android/`, and the two do not share code.

> **Nothing this app displays is a submission number.** The graded figures — drift as a percentage
> of distance, yaw error, the covariance ellipse — are produced by `eval/run.py` against IO-VNBD
> ground truth and shown on a device by the replay view in `android/`. What runs here is a small
> on-device estimator over the phone's own sensors, so its numbers can be looked at during a drive
> and cannot be quoted anywhere else. `backend/LocalNavigationEstimator.kt` says at the top exactly
> which three things it is not.

## Two map engines, one screen (D-121)

The navigation UI is being built on the **Mapbox Navigation SDK for Android** — the plan is
[`docs/UI_UX_NAVIGATION_PLAN.md`](../docs/UI_UX_NAVIGATION_PLAN.md), and its §7 is the review of
that SDK against the project's rules. Read §7.2 before touching anything under `src/mapbox/`.

| Flavour | Map | Needs | Built by CI |
|---|---|---|---|
| `osm` (default) | OpenStreetMap raster tiles via OSMDroid (D-117) | nothing | always |
| `mapbox` | Mapbox Navigation SDK v3.30.1 + Maps SDK 11.30.1 (Compose) | two Mapbox tokens, see below | only when the `MAPBOX_DOWNLOADS_TOKEN` secret exists |

Everything outside `ui/components/MapView.kt` and `ui/components/MapStack.kt` is shared in
`src/main`. The two flavours install side by side (`com.sih.idr.demo` and
`com.sih.idr.demo.mapbox`).

### Mapbox tokens (D-122)

Two tokens, neither of which is ever committed — `tests/test_android_demo_surface.py` fails on a
`pk.`/`sk.` literal anywhere under this module.

1. **Secret downloads token** (`sk.…`, scope `Downloads:Read`) — authenticates the Maven
   repository. Put it in the per-machine `~/.gradle/gradle.properties`:
   ```properties
   MAPBOX_DOWNLOADS_TOKEN=sk.<secret>
   ```
   Without it `settings.gradle.kts` does not declare the Mapbox repository at all, so the `osm`
   flavour still builds and the `mapbox` flavour fails with `Could not find
   com.mapbox.navigationcore:…`, which is the honest error. In CI the same property arrives as the
   `ORG_GRADLE_PROJECT_MAPBOX_DOWNLOADS_TOKEN` environment variable from a repository secret.
2. **Public token** (`pk.…`) — used by the map at runtime. Put it in this folder's gitignored
   `local.properties`:
   ```properties
   MAPBOX_PUBLIC_TOKEN=pk.<public>
   ```
   `app/build.gradle.kts` injects it as the `mapbox_access_token` string resource of the `mapbox`
   flavour. Without it the build still succeeds and the map area shows a message saying the token
   is missing (D-080: an empty state, not a blank canvas).

Who owns the Mapbox account, and the MAU budget for test phones, is an open decision-log item
(§7.11, row 5): every test device is a billed monthly active user.

### What the `mapbox` flavour does today

The §7.10 hello-world, and no more: the `MapboxMap` composable under the existing screen, with an
**IDR-owned layer** — track, 1 σ covariance ellipse, raw pose dot — drawn from `TelemetryState`
alone (rule R4), and the Navigation SDK configured once per process with **`enableSensors(false)`**
and the InEKF as its only location source at a fixed 10 Hz (`backend/mapbox/InekfLocationProvider.kt`,
rules R1–R3). No trip session, no route, no SDK puck yet: those come with the replay milestone
(§7.9), and the SDK's puck will then sit next to ours, both labelled, because the pair is the only
visual that proves which estimator is driving.

## The rules this module is held to

They are the seat-A constraints in [`android/HANDOVER.md`](../android/HANDOVER.md) §2 as amended
by D-117 and D-122, and `tests/test_android_demo_surface.py` fails if any of them comes back.

1. **The logger (`android/`) never gets a network path.** This module may: D-117 re-admitted online
   OSM tiles for the operator demo, D-122 admits the Mapbox stack for the `mapbox` flavour under a
   rehearsal rule — the venue build must survive airplane mode over a pre-downloaded `TileStore`
   region (§7.4), and the finale rehearsal is run with the SIM out.
2. **The SDK's own dead reckoning stays off** (`enableSensors(false)`, D-123). With it on, the SDK
   "ignores location updates which don't match data from sensors" — its own words — and the tunnel
   demo would silently show Mapbox's estimate instead of ours.
3. **No number on screen that the producer of the record did not produce.** The middle metric card
   reads the estimator's own σ under its own name; no Android surface prints "drift" or a "grade"
   (D-112, D-124). Position uncertainty travels as a 2×2 covariance, not a radius (D-125), and the
   only arithmetic between it and the drawn ellipse is `backend/Covariance.kt`, which is unit
   tested.
4. **No simulated fallback.** With no recording the screen says it has no data; with no token the
   map says there is no token. Nothing is generated to fill either.
5. **Every screenshot says what produced it.** The D-081 caption on the telemetry sheet names the
   estimator, the stream, the not-demonstrated 200 Hz configuration and, since D-121, the map
   engine.

## Open work

- The replay milestone (§7.9): `startReplayTripSession()` over a logger session converted to
  InEKF-output `ReplayEventUpdateLocation`s with `IS_MOCK = true`, through this same screen, in
  airplane mode. First, before the live drive.
- Then the live trip session with the `LocationObserver` sidecar (R5), `DeviceProfile` A/B (R6),
  reroute paused in tunnel states (R7), `NavigationCamera` + `keyPoints` in place of the hello-world
  `easeTo`, and the Stage 2–5 chrome from the plan.
- Replace `LocalNavigationEstimator` with the compiled filter when `core/ffi/` has an
  implementation behind it. It is an interface definition today (D-022, D-043, D-077). The
  covariance fields on `TelemetryState` are the seam it fills.
- Fold this module into the one Gradle root at `android/`, or retire it in favour of the replay
  view there. Two roots and two application ids for one demo is the split `d3d6df3` already
  collapsed once.
- Measure sustained rate, thermal behaviour and battery over a real drive, per device — and CPU at
  the 10 Hz provider cadence on the A55.

## Building

Open this folder — not `android/` — as a project, or from here:

```bash
./gradlew :app:assembleOsmDebug :app:testOsmDebugUnitTest
```

```bash
./gradlew :app:assembleMapboxDebug
```

The bare `:app:assembleDebug` now builds **both** flavours and therefore needs the Mapbox tokens.
On the Windows dev box, `--no-daemon` trips the AF_UNIX socket problem documented in
`android/README.md`; build with the daemon. CI builds both roots on every pull request
(`.github/workflows/android.yml`). A physical device is required for anything beyond layout:
sensor and GNSS behaviour cannot be meaningfully tested in the emulator.
