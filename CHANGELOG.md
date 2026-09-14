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

## v0.1.4 — 14 Sep 2026 (`versionCode` 4)

**Destination search that reaches past the seven presets, and a calibration pass reviewed before
it shipped.** Two branches merged to `main` the same evening (`827f876`, `607a293`), each with a
follow-up commit that fixed what review and simulation found (`fc2bd59`, `8a3889b`, D-129).

### Added

- **Search anywhere in India.** The search bar now queries Photon (`photon.komoot.io`, prefix
  autocomplete biased to your position) from the first character, with Nominatim as the fallback
  for queries of three characters or more, throttled to its one-call-per-second policy. The seven
  Delhi presets are still there and still work offline; online results are merged in, deduplicated
  by position and title, and ranked by how well the title matches with distance as the tie-break.
- **Recent destinations.** The last ten places you chose, most recent first, under a *Recent*
  header when the field is focused and empty; long-press to remove one. Stored in
  `SharedPreferences`, no new dependency.
- **Category pills that search online.** *Fuel*, *Food*, *Parking* and *Hospitals* filter the
  online results by OSM tag; with an empty query they run a nearby-POI search within 5 km.
- **A dropped pin gets a name.** A long press on the map still starts routing immediately under the
  coordinate string; the route's destination name is then patched with the reverse-geocoded place
  name when it arrives, without a second route fetch.
- **The gyro null offset starts from the hardware's own estimate.** `TYPE_GYROSCOPE_UNCALIBRATED`
  ships a drift vector alongside the rate; it now seeds the bias for the stretch between launch and
  the first standstill or GNSS-tracked window that measures it here. Taken once; after that the
  estimate is the app's own. (D-129)
- **A fix without a bearing still anchors the course** — from the direction between the previous
  applied fix and this one, when they are within 2.5 s, at least 3 m apart and above the anchor's
  2 m/s floor. (D-129)

### Fixed

- **`docs/METHOD.md` §13 and `SUBMISSION_AUDIT.md` no longer list the accelerometer sign
  convention as open.** D-085 closed R-8 on 1 Sep with real stationary segments; the two documents
  still said otherwise. The remaining gap is the offline detector's 10 Hz blind spot (D-075), and
  the text now says what the on-device tilt rule does and does not see about it.

### Caught in review, before this build

Not regressions on a phone — none of this reached a device — but the reason the two merges carry
follow-up commits:

- Photon's tag filter is `key:value`; the service sent `key=value`, which matches nothing, so every
  category-filtered search would have returned zero online results, and the nearby search went to
  an endpoint that is HTTP 400 without a query. Both checked against the public instance. (`fc2bd59`)
- A yaw-rate gate on the bias observation window, meant to keep GNSS bearing lag out of the
  estimate, kept only the catch-up half of the lag's effect and tripled the error it was there to
  remove: simulated over five city turns with the bearing 0.8 s late, −0.04 °/s without it, −0.11
  with it. Reverted, with a lagged-turn test that fails on the gate. (D-129)
- The bearing fallback took the direction of the *innovation* (fix minus estimate), which after a
  dead-reckoned stretch is the direction of the pose error, not of travel. Rewritten to consecutive
  applied fixes. (D-129)

### Tests

157 JUnit scenarios on the `osm` flavour, run on the Windows dev box: 10 new with the search
(Photon parsing incl. the `[lon, lat]` order, the non-India drop, the Nominatim fallback, the
network-failure path, ranking, reverse geocoding; recents order, cap, bump and remove), 3 on the
Photon request shapes, 1 on the HAL drift seed, 1 on the lagged bearing through turns.

### Installing over v0.1.3

This build is signed with the dev box's debug keystore; v0.1.3 was a CI artifact signed with a
per-runner one. Android refuses an upgrade across signing keys, so if the install fails with
"App not installed" or a signature error, uninstall v0.1.3 first.

---

## v0.1.3 — 14 Sep 2026 (`versionCode` 3)

**The traced curve in tunnel mode, from the same 14 Sep road test.** The speedometer and heading
faults of v0.1.2 were fixed and the curve was still wrong: the track left the bore, ran out to a
vertex in open ground and came straight back, over a banner reading *235 m on IDR · 20 s ·
χ² gate: 16 accepted · 20 rejected · applied by the anti-lockout rule*. Three separate defects.

### Fixed

- **The gyro's null offset is measured and removed.** Nothing estimated it, and the only thing
  that had ever hidden it — the GNSS course anchor — is exactly what a tunnel takes away, so it
  integrated straight into the heading. Simulated over that outage's own numbers (20 s, 14 m/s,
  280 m), an uncompensated 1 °/s leaves 20° of heading and **48 m** of lateral error in the bore;
  after one traffic-light stop, **0.33 m**. The bias is now measured at every detected standstill
  (ZARU) and across windows of GNSS-tracked driving, and no window may span an outage — so what
  runs inside a tunnel is what the last clean stretch of driving measured. (D-128)
- **The anti-lockout rule now applies the fix it forces.** A fix rejected five times running was
  computed, counted, reported to the state machine and printed on screen as *applied by the
  anti-lockout rule* — and then the pose was never touched. The rule exists precisely because a
  pose that has drifted past the χ² gate rejects every fix it is offered, so nothing re-acquired
  and the drift ran to the end of the outage. It is applied now. (D-128)
- **A tunnel exit bends onto the road instead of jumping to it.** The first fix after an outage
  carries the whole accumulated drift and went in at up to 85% in one step, straight into the
  drawn polyline — the spike. The estimate still takes the correction at once; what is *drawn* is
  offset by exactly the step and walks that offset off over ~0.7 s, inside the machine's 2 s
  reconvergence window, so `SEAMLESS_RECONVERGENCE` is now a state in which something
  reconverges. Corrections over 75 m are not hidden, the offset is added to `est. σ` while it
  lasts so the ellipse still covers the estimate, and none of it counts as distance travelled.
  (D-128)

### Added

- A **gyro bias** field on the heading-provenance chip (`bias +1.0°/s`), and
  `gyroBiasRadPerSec` on `TelemetryState`. An uncompensated bias is silent: it draws a perfectly
  smooth curve that is simply in the wrong place. (D-128)
- `backend/ReacquisitionSlew.kt` — the exit slew as its own pure-Kotlin unit, for the reason
  `TunnelFsm` and `CourseTracker` are: a rule a laptop cannot drive is a rule nobody can argue
  about. (D-126, D-127, D-128)

### Tests

20 new JUnit scenarios — 10 over the bias (a standstill measures it; a handled phone does not; a
real turn is not mistaken for one; the bearing at a tunnel mouth is not a calibration; an absurd
value is clamped), 8 over the slew (the drawn point does not move when the correction lands, the
offset is gone inside the reconvergence window, no frame moves it more than a puck's width, and a
correction too large to hide is not hidden), 2 over the new chip label.

### Not verified on a device

No phone was reachable, and this container has no Android SDK, so the Gradle unit-test task could
not run here — CI runs it. The pure-Kotlin units were compiled and run standalone; the
Android-coupled estimator was type-checked against `Location` and `SystemClock` stubs. The `bias`
field on the chip is what the next road test should read at the portal.

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
