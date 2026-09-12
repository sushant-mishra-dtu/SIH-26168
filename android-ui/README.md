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

## What is included

- Compose operator UI: the track drawn in metres, an uncertainty circle, a heading marker, a 50 m
  graticule and a scale bar.
- GNSS/INS mode, fix status, position, achieved sensor rate and timestamp jitter panels.
- Foreground service for continuous recording, as `android/README.md` requires.
- Uncalibrated accelerometer and gyroscope registration.
- Location updates with explicit runtime permissions and a notification channel.
- `DeadReckoningBackend` as the seam a compiled filter is meant to arrive behind.

## The three rules this module is held to

They are the seat-A constraints in [`android/HANDOVER.md`](../android/HANDOVER.md) §2, and this
module broke all three in its first commit. `tests/test_android_demo_surface.py` now fails if any
of them comes back.

1. **No network at runtime, ever.** D-041 claims 100% offline and D-080 forbids the demo surface
   any fetch. The CartoDB tile source, the Play Services font provider, and the `INTERNET`
   permission that made both possible are gone. The map is a Compose canvas over the recorded
   track: no tiles, no basemap, no API key.
2. **No number on screen that the producer of the record did not produce.** The middle metric card
   was labelled `m drift`; drift is the graded metric and this app cannot compute it, so the card
   now reads the estimator's own σ under its own name.
3. **No simulated fallback.** A `PREVIEW_TELEMETRY` constant used to render whenever the service
   was not running — including on launch — carrying an invented 200 Hz sample rate and 0.8 ms
   jitter, which are precisely the two per-device numbers this project has never measured. Removed.
   With no recording the screen says it has no data.

## Open work

- Draw real road geometry underneath the track, offline, once seat P defines the extract format
  (`android/HANDOVER.md` §3b). Not a tile server, and captioned as fixed geometry rather than as a
  match until a matcher exists.
- Replace `LocalNavigationEstimator` with the compiled filter when `core/ffi/` has an
  implementation behind it. It is an interface definition today (D-022, D-043, D-077).
- Fold this module into the one Gradle root at `android/`, or retire it in favour of the replay
  view there. Two roots and two application ids for one demo is the split `d3d6df3` already
  collapsed once.
- Measure sustained rate, thermal behaviour and battery over a real drive, per device.

## Building

Open this folder — not `android/` — as a project, or `./gradlew :app:assembleDebug` from here. CI
builds both roots on every pull request (`.github/workflows/android.yml`). A physical device is
required for anything beyond layout: sensor and GNSS behaviour cannot be meaningfully tested in the
emulator.
