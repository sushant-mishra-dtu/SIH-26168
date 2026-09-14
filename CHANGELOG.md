# Changelog — operator UI (`android-ui/`)

Every released build of the demo app, newest first. This file covers the **operator UI**
(`android-ui/`, application id `com.sih.idr.demo`); the foreground logger in `android/` versions
separately and is not published as an APK.

Each entry names the decision-log rows behind it. The decision log
([docs/DECISION_LOG.md](docs/DECISION_LOG.md)) is where the *reasons* live and is append-only;
this file is the shorter question — what changed on the phone between two installable builds.

`versionCode` is the integer Android compares on an upgrade. It increments once per published
APK and has nothing to do with `versionName`; the two are listed together so a build on a device
can be traced back to a commit.

---

## v0.1.2 — 14 Sep 2026 (`versionCode` 2)

**Heading and speed, both found in a road test on 14 Sep.** The traced curve was wrong, and its
direction followed the phone instead of the vehicle. Both faults were in the demo estimator and
neither showed anything on screen.

### Fixed

- **The phone's mounting angle no longer steers the track.** The heading was the azimuth of the
  device's +Y axis projected onto the ground plane, assigned straight to the pose, so a cradle
  canted 30° rotated the whole traced path by 30°. A phone upright in a cradle — +Y pointing at
  the sky — was computing `atan2(0, 0)`, which is why a couple of degrees of tilt swung the
  heading. Course over ground is now its own state (`backend/CourseTracker.kt`), anchored to the
  GNSS course; the handset's own attitude carries a mount offset and nothing else. (D-127)
- **Turns are measured about the world vertical, not about device Z.** The yaw rate was the raw
  device-frame Z rate, which is the vehicle's turn rate only when the phone lies flat; in a
  windscreen cradle most of a turn lands on device Y, so only a fraction of each turn was
  integrated. It is now the gyro's projection onto gravity, correct at any attitude. The sign was
  also inverted — a right-hand-positive rate about up *decreases* a compass bearing. (D-127)
- **Re-seating the phone mid-drive no longer turns the map.** Handling is detected from the tilt
  rate and from rates no vehicle can produce; while it lasts the course is held, and the mount
  offset is re-learned against the unchanged course once the phone settles. A stopped vehicle
  never changes course at all, whatever is done with the handset. (D-127)
- **The speedometer no longer flickers to zero on smooth road.** The standstill detector wanted
  12 consecutive quiet samples, which at the requested 200 Hz is 60 ms — something a car cruising
  on good tarmac delivers several times a second, and each time the speed was zeroed. The hold is
  now a duration (0.6 s on foot, 2 s in a vehicle) and a measured GNSS speed vetoes it outright.
  (D-127)
- **The traced track no longer stalls mid-corner.** The dead-reckoning branch propagates along the
  speed, so every false standstill also stopped the track. Same fix. (D-127)
- **Road vibration is no longer counted as footsteps.** Nothing gated the pedestrian step model by
  mode, so engine and road noise past 1.2 m/s² queued 0.5–0.78 m strides at up to 3.8 Hz — roughly
  2.5 m/s of invented travel, laid down along a stale heading. The step model is off once a fix
  has reported 4.5 m/s. (D-127)
- **Sustained acceleration is no longer absorbed into "gravity".** The gravity-magnitude baseline
  ran at a 0.33 s time constant, so ten seconds of pulling away read back as zero dynamic
  acceleration. It now runs at 20 s, and is seeded from the first sample only when that sample
  could plausibly be gravity. (D-127)
- **A tunnel no longer brings the vehicle to a halt on its own.** Coasting decayed at a fixed
  0.35 m/s², which parks a 20 m/s car 57 s into an outage and stops the track with it. Coasting
  now holds constant velocity with a slow bleed; ZUPT is what stops it. (D-127)
- **Slow fixes are believed.** `onLocation` ignored `location.speed` below 0.3 m/s and fell back
  to differencing fixes, which let the standstill detector zero a speedometer against a fix that
  said otherwise. (D-127)

### Added

- A heading-provenance chip in the diagnostics drawer: whether the heading is a GNSS-anchored
  **course** or still only the **phone azimuth**, whether it is currently **held** because the
  phone is being handled, the learned **mount offset** in degrees, and which motion model is
  running. Both faults above rendered identically to correct behaviour, so there was nothing to
  look at in the field. (D-127)
- `TelemetryState` carries `headingIsCourse`, `mountOffsetRad`, `attitudeDisturbed` and
  `motionMode`.

### Tests

31 JUnit scenarios over `CourseTracker` and `MotionClassifier` — both pure Kotlin with the clock
injected, for the reason `TunnelFsm` is (D-126) — and 5 over the chip's labels. One of them pins
that the standstill veto does not compare a GNSS timestamp against a sensor timestamp: those are
different clocks on some devices, which is why `android/.../SessionClock.kt` exists.

### Not verified on a device

No phone was reachable from the session that made this change. The chip above is what the road
test should read.

---

## v0.1.0 — 14 Sep 2026 (`versionCode` 1)

The first installable build, published as `releases/app-osm-debug.apk` from `5bf605d`.

- Navigation screen with the OSMDroid basemap, course-up and north-up cameras, destination search
  and turn-by-turn guidance banner (D-117, D-121).
- Autonomous tunnel state machine driving GNSS suppression, with a manual force override whose
  release runs the honest exit path (D-126).
- Position uncertainty drawn as a covariance ellipse rather than a circle, and reported as
  `est. σ` — never as drift, which a phone cannot measure (D-124, D-125).
- Tap and swipe gestures on the operator screen; layout fixes from the Galaxy A55 desk run.
- A `mapbox` product flavour exists behind two tokens that are not checked in, and is not
  published (D-122).
