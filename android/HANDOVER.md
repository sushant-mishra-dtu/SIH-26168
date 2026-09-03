# Handover — seat A, Android: the map view and production readiness

**Written:** 3 Sep 2026, at the end of the session that built the foreground logger.
**Branch:** `a/foreground-logger` — `6ac18e5` (module), `384a2ef` (ignore rules), `d3d6df3` (one Gradle root).

Read this with [phases.md](../phases.md) §1's loop in mind: restate, plan, edit small, verify with a
command, report. This file does not supersede [docs/IMPLEMENTATION_PLAN.md](../docs/IMPLEMENTATION_PLAN.md);
where it disagrees, the plan wins and the disagreement is a bug here.

---

## 1. What you are actually picking up

Verifiable, not remembered:

| Claim | How to check |
|---|---|
| The logger module exists — 11 Kotlin sources, 2,060 lines | `find android/app/src -name "*.kt" \| xargs wc -l` |
| It builds | `android/app/build/outputs/apk/debug/app-debug.apk` exists |
| It has been seen **only in its idle state** | no session folder on any device |
| **No drive has ever been recorded** | no `*_session.json` exists anywhere |
| The CSV schema is pinned to the harness loader | `pytest tests/test_android_logger_schema.py` — 34 pass |
| Full Python suite is green | `pytest -q` — 456 pass |

**The single most important sentence in this file:** the app's reason to exist — the achieved sample
rate and timestamp jitter per team device, asked for in
[IMPLEMENTATION_PLAN.md](../docs/IMPLEMENTATION_PLAN.md) §4 — is **not measured**. Everything below is
lower priority than one two-minute stationary recording followed by one real drive. Do that first.
If you build a map view before there is a single measured number, you have made the demo prettier
and the submission no more defensible.

Also: **Gate 1 is still unmeasured** (D-088) and is the real critical path for the 8 Sep screening.
Nothing in this file is on it. Confirm with seat D before spending days here.

---

## 2. Hard constraints — each one silently ruins the work if ignored

1. **Do not start the JNI layer.** [core/ffi/idr_core.h](../core/ffi/idr_core.h) is an interface
   definition with no implementation behind it (D-022, D-043, D-077) and says so in capitals. There
   is no on-device filter. Anything that needs live filter output is blocked, not slow.
2. **The main CSV header is a whitelist of the entire file.** `io_vnbd.py::_canonicalise` runs
   `assert_no_leakage` over *every* column, so one added column raises `LeakageError` on the whole
   recording (D-089). New quantities go to a sidecar. `tests/test_android_logger_schema.py` will
   catch you; do not "fix" it by widening `ALLOWED_COLUMNS`.
3. **No network at runtime, ever.** D-041 claims 100% offline and D-080 forbids the renderer any
   fetch. That rules out Google Maps SDK, Mapbox, any tile server, any CDN font. A judging venue's
   wifi is not a dependency worth having.
4. **The view computes no physics.** D-079: every displayed number is computed by the producer of
   the record, never by the renderer. If the Android view divides by `distance_m`, it can display a
   number the evaluation never produced — and it will agree with the harness for a while, which is
   how that error survives review.
5. **No simulated fallback.** D-080: a missing artefact shows an empty state. No generator, no demo
   data, no `Math.random`. The one failure the frozen protocol exists to prevent is a cockpit fed by
   its own generator.
6. **`org.gradle.java.home` is never committed.** It is an absolute path, true on one machine. It
   was committed once, in the nested root that `d3d6df3` removed. See §6.

---

## 3. "Add the map" is two tasks, and only one is unblocked

### 3a. Trajectory view — buildable today, no filter needed

`eval/run.py::trajectory_record` already emits **`idr-trajectory/1`**: a versioned, measured record
carrying `truth_ned`, `filter_ned`, `strapdown_ned`, `gnss_ned`, `position_sigma_m` (the ellipse),
`drift_pct`, `yaw_error_deg`, and the raw 10 Hz accel/gyro traces. `eval/replay/replay.html` (364
lines) already draws all of it — trajectories, the covariance ellipse growing through the outage and
collapsing at re-acquisition, a scrubber, the traces.

**So the Android map view is a second view of an artefact that already exists.** It renders a
trajectory record loaded from a file. No JNI, no filter, no map matcher, no network. It is the
demo `android/README.md` describes — "judges respond to watching the covariance grow inside the
tunnel and collapse on exit" — minus the live pose, which nothing on-device can produce yet.

- **Files in scope:** `android/app/src/main/kotlin/org/idr26168/logger/` (new `replay/` package),
  `android/app/src/main/res/`, `android/HANDOVER.md`.
- **Do not touch:** `eval/`, `core/`, the logger's `Channels.kt` / `Records.kt` schema.
- **Read first:** `eval/replay/replay.html` in full, and D-079/D-080/D-081 in the decision log.
- **Exit criterion:** load a real `idr-trajectory/1` file produced by `eval/run.py`, draw all four
  tracks plus the 1σ ellipse at a scrubbed epoch, and show `drift_pct` / `yaw_error_deg` **read from
  the record**. A record with an unrecognised `schema` string is refused with a visible message. A
  test asserts the view contains no division by `distance_m` and no RNG — mirror
  `tests/test_replay.py`, which asserts exactly that for the web page.
- **Caption discipline (D-081):** the caption says `S-` smartphone stream at 10 Hz and states in as
  many words that the 200 Hz FOG configuration is not demonstrated. Do not drop it because it is
  ugly on a slide.

### 3b. Road geometry underneath it — blocked, and not on you

Less blocked than it first looks — check before assuming either way.

**The raw OSM data is already on disk.** `maps/extracts/` holds `northern-zone-latest.osm.pbf`
(222 MB) and `central-zone-latest.osm.pbf` (350 MB) with their `.poly` boundaries, downloaded
27 Aug. They are gitignored by design (D-none needed; `maps/README.md` says never commit extracts),
so they exist on the machine that fetched them and nowhere else — confirm they are on yours with
`ls -la maps/extracts` before planning around them.

**What is missing is the pipeline, not the source:** no `.pbf` → filtered drivable `highway=*` →
CSR adjacency builder exists, no matcher exists, and the library choice is still logged as pending
in `maps/README.md`. The online HMM matcher is deferred to October (seat P) and the emission σ
contract with seat S is unwritten.

For a *view*, none of the matcher is needed — only geometry. A read-only offline extract of one
demo route's road polylines is a much smaller task than the matcher, and it is the honest way to get
roads behind the trajectory. It is still seat P's file format to define, so agree it first.

Do not work around this by pulling tiles from a network map SDK — that breaks constraint 3 and the
offline claim, which is worth more than the visual. And whatever is drawn is a **backdrop**, not
evidence: captioned as fixed geometry, never as a match, until a matcher exists to make that claim.

---

## 4. "Production ready" — what it means here, in priority order

Not a vibe. This list is ordered so that each item is worth more than the one below it.

1. **JVM unit tests. There are currently zero.** The three highest-value targets are pure functions
   and need no device: `RateStats` percentile/Welford arithmetic (feed a known Δt sequence, assert
   median/p95/stdev), `Records.formatCsvRow` (assert the 24-field shape, empty cells before the
   first fix, the `%.6f` precision, no `NaN` text), `SessionClock` timebase classification. Add
   `android/app/src/test/kotlin/`, wire `testImplementation` JUnit, exit criterion
   `./gradlew :app:test`.
2. **A recording must survive the process being killed.** `stopRecording()` writes the sidecar, and
   `onDestroy` calls it — but a `SIGKILL` from the OS writes nothing, leaving three CSVs and no
   device metadata. Write a provisional sidecar at *start* and rewrite it at stop, so a killed
   session is still attributable.
3. **Free-space and duration guards.** There is no size cap, no rotation, no free-space check. The
   raw sidecar at 100 Hz is roughly 4 MB/minute; a two-hour drive fills half a gigabyte and a full
   disk fails mid-drive with no warning. Check free space at start, warn at a threshold, stop
   cleanly rather than truncating.
4. **`startRecording` partial-failure path.** `sensorThread`/`gnssThread`/`tickThread` are
   `lateinit`. If `startRecording` throws after `startForeground` but before they are assigned,
   `stopRecording` dereferences them and crashes. Guard it, and add a test.
5. **Export.** Files land in app-specific external storage; today they come off the device by `adb`
   or a file manager. A share/export action (SAF, `ACTION_CREATE_DOCUMENT`) is what makes the app
   usable by a teammate who is not you.
6. **Battery and thermal over a real drive**, per `android/README.md`'s own instruction: sustained
   sensing heats the SoC and throttles, which appears as a *falling achieved rate partway through*.
   The measurement exists to catch that. Record the numbers per device.
7. **Play Store readiness, only if it is actually going to be listed.**
   `HIGH_SAMPLING_RATE_SENSORS` requires a written justification at review, `foregroundServiceType`
   requires a declared use case on Android 14+, and a privacy policy is required for location. If it
   is only ever side-loaded to team devices, say so and skip this item rather than half-doing it.
8. **CI.** The wrapper **jar** is not committed, so nothing can build this in CI today. A workflow
   that runs `:app:assembleDebug` and `:app:test` is what stops the module silently rotting while
   the Python suite stays green.

---

## 5. Known gaps in the code as written

Stated so you do not rediscover them as bugs:

- `RateStats.percentileMs` returns the **upper edge of a 100 µs histogram bin**, not an exact
  percentile. Deliberate — bounded memory over a 40-minute drive — and documented in the class.
- The `date` column uses a dot sub-second separator on purpose (D-092), because the colon that
  IO-VNBD ships only parses after D-086, which is on the unmerged `d/shipped-date-format` branch.
  If that branch lands, re-run the schema test; it asserts against the live pattern.
- `SensorHub` shares `rotationMatrix`/`orientationRad` across calls. Safe only because every sensor
  callback is on the one sensor thread. If you add a second listener thread, that breaks.
- Calibrated data goes in the main CSV and uncalibrated in the sidecar (D-090). This is not an
  oversight and reversing it silently changes what `accel_*` *means* relative to every IO-VNBD
  sequence it is compared against.

---

## 6. Environment, so you do not lose a morning

One Gradle root: **`android/`**. Open that in the IDE, never `android/app/`. Wrapper pins Gradle
8.14.5, the version that actually built this.

On the machine this was written on, Gradle **cannot start** under Microsoft JDK 17 (what `JAVA_HOME`
points at) or Studio's bundled JBR 25: `java.nio.channels.Pipe.open()` fails with an AF_UNIX
`EINVAL`, surfacing as `Unable to establish loopback connection`. **JBR 21 works.** Set the Gradle
JDK per machine — Studio's *Gradle JDK* setting or your own `~/.gradle/gradle.properties` — and see
`android/README.md` for what was ruled out by measurement.

That machine's user-level `JAVA_HOME` also points at an Adoptium install containing only a `lib`
folder. Unrelated to this module, but it will bite anything that reads `JAVA_HOME`.

---

## 7. Questions to settle before writing code

1. **Seat D:** is any Android work justified before Gate 1 is measured? If not, this file waits.
2. **Seat P:** is a static offline road backdrop acceptable ahead of the CSR graph, and who owns
   the extract?
3. **Seat S:** does the trajectory view stay a replay-only view until the October port, or is there
   an intermediate contract worth agreeing now?
4. **Whoever owns submission:** is the app ever listed on Play, or side-loaded only? Item 7 of §4
   depends entirely on the answer.
