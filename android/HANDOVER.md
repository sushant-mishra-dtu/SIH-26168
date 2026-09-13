# Handover — Android: everything left to do

**Written:** 3 Sep 2026, at the end of the session that built the foreground logger.
**Revised:** 10 Sep 2026 — §3a and §4 items 5 and 8 have landed, §8 is new, and §1's Gate 1 line
was wrong by a week. **13 Sep 2026** — §9 is new and is the part to read: **the complete list of
remaining Android work, in order**, with the phone procedure under item 1. §1–§8 are the history
and the reasoning behind that list; they are not a second list.
**Branch:** `a/foreground-logger` — `6ac18e5` (module), `384a2ef` (ignore rules), `d3d6df3` (one Gradle root).
Since merged; `main` is at `8a6835e`.

Read this with [phases.md](../phases.md) §1's loop in mind: restate, plan, edit small, verify with a
command, report. This file does not supersede [docs/IMPLEMENTATION_PLAN.md](../docs/IMPLEMENTATION_PLAN.md);
where it disagrees, the plan wins and the disagreement is a bug here.

---

## 1. What you are actually picking up

Verifiable, not remembered:

| Claim | How to check |
|---|---|
| The logger module exists — 17 main sources, 3,128 lines | `find android/app/src/main -name "*.kt" \| xargs wc -l` |
| A second app exists at `android-ui/` — 8 sources, 1,184 lines | `find android-ui/app/src/main -name "*.kt" \| xargs wc -l`, and §8 below |
| Stationary session recorded & committed | `android/measured/S-IDR-20260913-031148-samsung-sm-a556e_session.json` (D-116) |
| **24 min stationary session for the Allan run, recorded & committed** | `android/measured/S-IDR-20260913-141119-samsung-sm-a556e_session.json`, curves in `eval/figures/device/S-IDR-20260913-141119-samsung-sm-a556e/` (D-119) |
| **Replay view seen rendering a real record on the phone** | 13 Sep 2026, `trajectory_S3a.json` from a full `eval/run.py` sweep; wrong `schema` refused with a dialog (§3a, §9 item 4) |
| **Drive logging pending** | stationary run done; car drive observation remaining (§9 item 2) |
| **Installed on a phone** | installed on Samsung Galaxy A55 5G (`SM-A556E`) on 13 Sep 2026 |
| The CSV schema is pinned to the harness loader | `pytest tests/test_android_logger_schema.py` |
| Both Android surfaces are pinned to D-041/D-079/D-080 | `pytest tests/test_android_demo_surface.py` — 67 pass |
| It has JVM unit tests | `cd android && ./gradlew :app:test` — 56 `@Test` methods |
| CI compiles both Gradle roots | `.github/workflows/android.yml` |
| `./gradlew` exists at all | the wrapper was committed in `53e0053`; before that there was none |

**The hardware baseline is no longer unmeasured (D-116).** On 13 Sep 2026, the logger was installed
on the team Samsung Galaxy A55 5G (`SM-A556E`) and completed a 246.6 s stationary desk session
(`S-IDR-20260913-031148-samsung-sm-a556e`). Achieved sample rate was **125.0 Hz** across all
accelerometer, gyroscope, and uncalibrated channels (requested 100 Hz), with **8.1 ms** median/p95
Δt jitter (stdev 0.0030 ms) under `ELAPSED_REALTIME` and 0 non-monotonic stamps. The 10 Hz main CSV
loaded directly into `eval.loaders.io_vnbd::load_sequence` with 2,462 rows and zero leakage errors.
The deliverable now turns to §9 item 2: the real drive for thermal and GNSS-denied observation.


**Gate 1 is no longer unmeasured, and the line that said so was stale by a week.** D-110 measured it
on 6 Sep and it **fails**: 136.8% median filter drift at 60 s against a 7.0% GNSS-available
baseline, a ratio of 19.4× where the gate is 3–5×, on 3 windows with half the held-out stems
skipped for divergence. The cause is localised to the ungated NHC pseudo-measurement and a process
noise built from a static Allan run, and the fix is seat S's. Nothing in this file is on that path
either — but "confirm with seat D before spending days here" now means confirming against a
measured failure rather than an unknown.

---

## 2. Hard constraints — each one silently ruins the work if ignored

Constraints 3, 4 and 5 were all broken by `android-ui/` between 5 and 10 Sep, by someone who had
not read this file (§7, D-111 through D-113). They now have a test each —
`pytest tests/test_android_demo_surface.py` — so a violation is a red check rather than a document
nobody opened.

1. **Do not start the JNI layer.** [core/ffi/idr_core.h](../core/ffi/idr_core.h) is an interface
   definition with no implementation behind it (D-022, D-043, D-077) and says so in capitals. There
   is no on-device filter. Anything that needs live filter output is blocked, not slow.
2. **The main CSV header is a whitelist of the entire file.** `io_vnbd.py::_canonicalise` runs
   `assert_no_leakage` over *every* column, so one added column raises `LeakageError` on the whole
   recording (D-104). New quantities go to a sidecar. `tests/test_android_logger_schema.py` will
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
6. **`org.gradle.java.home` is never committed.** It is an absolute path, true on one machine.
   It was committed *twice* -- in the nested root that `d3d6df3` removed, and in the root that
   survived it, where this file previously claimed it was gone. Removed in `53e0053`. See §6.

---

## 3. "Add the map" is two tasks, and only one is unblocked

### 3a. Trajectory view — **built**, in `9fdd261`

Landed under a commit message that says "chore: Update execution history and build output cleanup
lock files", which is how a 700-line feature arrives without a review. What is there, and what of
the exit criterion below it meets:

| Exit criterion, as written below | State |
|---|---|
| Loads a real `idr-trajectory/1` file | `ReplayActivity` + `ACTION_OPEN_DOCUMENT`; `TrajectoryRecord.fromJson` |
| Draws four tracks and the 1σ ellipse at a scrubbed epoch | `TrajectoryMapView`, `SeriesView`, `SensorTraceView`, `SeekBar` |
| `drift_pct` / `yaw_error_deg` **read from the record** | `updateEpoch` indexes `r.driftPct[k]` / `r.yawErrorDeg[k]` |
| Unrecognised `schema` refused with a visible message | `IllegalArgumentException` → `AlertDialog` |
| A test asserts no division by `distance_m` and no RNG | `TrajectoryRecordTest`, **and** `tests/test_android_demo_surface.py` |
| Caption states 200 Hz FOG is not demonstrated | `sensorCaption` in `displayRecord` |

Two things to know about that last row of tests. The Kotlin one is the better test and it runs
nowhere — see §6 on the toolchain. The Python one runs in the harness suite every seat already
runs, reads both modules as text, and has been checked against ten reintroduced violations rather
than merely observed to pass. Neither has ever seen the view render a real file on a phone: the
record loads through SAF, and no one has opened one.

**Closed 13 Sep 2026.** A full `python -m eval.run` sweep (6.5 min on the dev box) wrote
`trajectory_S3a.json`; pushed to `/sdcard/Download/` and opened through *Load JSON...* on the A55,
the view drew the four tracks, the dashed 1σ ellipse shrinking as the scrubber moved from 60 s
(σ 65.2 / 53.5 m) back to 30 s (33.7 / 52.0 m), the drift / yaw readouts from the record, the
sensor traces and the D-081 caption verbatim. The stamp line printed `NOT REPRODUCIBLE`, correctly:
the sweep ran on a dirty tree. A copy with `schema` set to `idr-trajectory/2` produced the
*Invalid Trajectory Record* dialog and left the loaded record untouched behind it. The only fix
needed was one the emulator could not have shown: on Android 15+ the activity draws edge-to-edge,
so `fitsSystemWindows` went on both root layouts to keep the title out from under the status bar.

<details>
<summary>The original brief, kept because it is the argument for what was built</summary>

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

</details>

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

**Items 1 to 5 and item 8 are done** (`53e0053`, `b0aad0f`, `766f503`, `9fdd261`, and this
revision). None of them has run on a phone, for the reason at the top of this file: no drive has
been recorded. They are correct by construction and by unit test, not by observation. **Items 6 and
7 are what is left, and item 6 needs a car.**

1. ~~**JVM unit tests. There are currently zero.**~~ **Done** — 50 of them, over the three targets
   named here: `RateStats` percentile/Welford arithmetic, `Records.formatCsvRow` shape and
   precision, `SessionClock` timebase classification. `./gradlew :app:test` is the exit criterion
   and it passes. Two of them deliberately pin the §5 quirks below so they do not get "fixed".
2. ~~**A recording must survive the process being killed.**~~ **Done** — a provisional sidecar is
   written at start and rewritten at stop, with a `status` field (`recording` / `complete`) so a
   killed session is identifiable as killed rather than as one missing its statistics.
3. ~~**Free-space and duration guards.**~~ **Done** — checked at start and every 10 s after;
   recording stops cleanly at 128 MB with room left to flush and rewrite the sidecar. Still no size
   cap and no rotation, on purpose. The minutes-remaining figure is measured from the recording's
   own bytes rather than assumed, because the write rate depends on the requested rate, the number
   of uncalibrated streams the device actually has, and the GNSS callback rate.
4. ~~**`startRecording` partial-failure path.**~~ **Done** — the three `HandlerThread` fields are
   nullable rather than `lateinit`, `startRecording` is wrapped, and a failed start shuts down
   cleanly instead of leaving a foreground notification over no recording. Not unit-tested: the
   failure needs a `Service` and a framework that misbehaves, which is Robolectric or an
   instrumented test, and that is a dependency decision rather than an oversight.
5. ~~**Export.**~~ **Done** — `SessionExporter.zipSession` behind an `ActivityResultContracts
   .CreateDocument("application/zip")` launcher on the main screen. It zips the whole session
   folder rather than offering a file picker over it, so the CSVs cannot travel apart from their
   `*_session.json` sidecar — a recording whose statistics went missing on the way off the phone is
   a recording of unknown provenance. Two unit tests cover the zip and the empty-directory refusal;
   the SAF half needs a device.
6. **Battery and thermal over a real drive**, per `android/README.md`'s own instruction: sustained
   sensing heats the SoC and throttles, which appears as a *falling achieved rate partway through*.
   The measurement exists to catch that. Record the numbers per device.
7. **Play Store readiness, only if it is actually going to be listed.**
   `HIGH_SAMPLING_RATE_SENSORS` requires a written justification at review, `foregroundServiceType`
   requires a declared use case on Android 14+, and a privacy policy is required for location. If it
   is only ever side-loaded to team devices, say so and skip this item rather than half-doing it.
8. ~~**CI.**~~ **Done** — `.github/workflows/android.yml`, two jobs: `:app:assembleDebug` plus
   `:app:test` for `android/`, and `:app:assembleDebug` for `android-ui/`. Split from `ci.yml` on
   purpose, so the critical-path Python checks stay a two-minute job that cannot be blocked by an
   SDK download. It found one bug on the way in: `android/gradlew` was committed **non-executable**
   (mode 100644, against `android-ui/gradlew`'s 100755), so `./gradlew` on any Linux runner would
   have stopped at "permission denied" — invisible for as long as the only two machines running it
   were Windows and an IDE. Fixed here with `git update-index --chmod=+x`.
   As predicted, a CI runner does not hit the AF_UNIX problem in §6; that one is specific to that
   machine, and this job passing says nothing about it.

---

## 5. Known gaps in the code as written

Stated so you do not rediscover them as bugs:

- `RateStats.percentileMs` returns the **upper edge of a 100 µs histogram bin**, not an exact
  percentile. Deliberate — bounded memory over a 40-minute drive — and documented in the class.
- The `date` column uses a dot sub-second separator on purpose (D-107), because the colon that
  IO-VNBD ships only parses after D-086, which has since landed on `main`. The schema test asserts
  against the live pattern, so it now covers the post-D-086 loader directly.
- `SensorHub` shares `rotationMatrix`/`orientationRad` across calls. Safe only because every sensor
  callback is on the one sensor thread. If you add a second listener thread, that breaks.
- Calibrated data goes in the main CSV and uncalibrated in the sidecar (D-105). This is not an
  oversight and reversing it silently changes what `accel_*` *means* relative to every IO-VNBD
  sequence it is compared against.

---

## 6. Environment, so you do not lose a morning

One Gradle root: **`android/`**. Open that in the IDE, never `android/app/`. Wrapper pins Gradle
8.14.5, the version that actually built this, and as of `53e0053` the wrapper is actually committed.

**The previous version of this paragraph was wrong and cost the morning it was written to save.**
It said Gradle cannot start under Microsoft JDK 17 or Studio's JBR 25 but that "JBR 21 works". JBR 21
fails too, the moment you invoke Gradle from a shell rather than from Studio. Re-measured: all three
JDKs fail identically, and all three recover on one JVM property, so **the JDK is not the variable.**

`Unable to establish loopback connection` comes from `Selector.open()`, which JDK 16+ backs with an
AF_UNIX socketpair on Windows. On this machine `connect()` returns `EINVAL` for a socket created
anywhere under `AppData\Local` — the default — and works under `~/.gradle`. The fix is
`-Djdk.net.unixdomain.tmpdir`, in **both** `org.gradle.jvmargs` (for the daemon) and `GRADLE_OPTS`
(for the client, which opens its socket before it reads any properties file). `android/README.md`
carries the exact values, the 8.3-short-name trap, and the measurement behind all of it.

**In a Claude Code web session, none of this applies and nothing Android builds at all.** The
environment's egress policy rejects `dl.google.com`, which is both the Android SDK and Google's
Maven repository, so there is no `compileSdk`, no AGP, and no way to run `./gradlew :app:anything`.
A Kotlin edit made there is unverified until CI compiles it — which is the second reason
`.github/workflows/android.yml` is worth having, and the reason
`tests/test_android_demo_surface.py` reads the sources as text rather than compiling them.

That machine's user-level `JAVA_HOME` points at an Adoptium install containing only a `lib` folder —
no `bin/java.exe`. Not unrelated after all: `gradlew` picks its launcher JVM from `JAVA_HOME` before
Gradle reads anything, so it stops with "JAVA_HOME is set to an invalid directory". Repoint or unset
it; `org.gradle.java.home` does not help, because that reaches only the daemon.

---

## 7. The second app, at `android-ui/`

It arrived on 5 Sep in one commit (`9a6f6c2`, saksham-eng560), a complete Compose operator UI —
1,184 lines, its own Gradle root, its own application id `com.sih.idr.demo`, no shared code with
`android/`. Nobody read it against §2. **It broke four of the six constraints there**, and the four
are worth reading one at a time, because none of them looks like a violation at the call site.

| Constraint | What was in the code | Why it is not cosmetic |
|---|---|---|
| 3, no network | `basemaps.cartocdn.com` tiles via osmdroid; `ui-text-google-fonts` fetching Inter through Play Services; `INTERNET` in the manifest; a `com.google.android.geo.API_KEY` placeholder | D-041 claims 100% offline. The demo needed a working venue wifi to draw a map, and would have looked fine in every rehearsal on a phone with the tiles cached |
| 4, the view computes no physics | `LocalNavigationEstimator` integrating yaw and position on-device, with `uncertaintyM += 0.08 * sqrt(dt)` | An uncertainty that grows by a hand-chosen constant is not a covariance. Drawn as a circle on a map, it is indistinguishable from one |
| 5, no simulated fallback | `PREVIEW_TELEMETRY` — speed 13.8 m/s, a 14-point track, `sampleRateHz = 200f`, `timestampJitterMs = 0.8f` — rendered **whenever the service was not running**, which includes launch | The last two are §1's "not measured" numbers, and 200 Hz is the FOG configuration D-081 requires captioned as *not demonstrated*. This is the exact failure D-080 exists to prevent, and a screenshot of it is evidence |
| §6, one Gradle root | a third root, after `d3d6df3` collapsed two into one | Two roots, two AGP versions (9.4.0 here against 8.7.3 there), two apps installed side by side on a demo phone |

Also mislabelled: the middle metric card read **`m drift`** over the estimator's own uncertainty
figure. Drift is the metric PS 26168 is graded on, it is an error against truth as a percentage of
distance travelled, and a phone has no truth. That card put the graded metric on a judge's screen
with a number behind it that was never measured against anything.

**What this revision changed, all of it minimal and none of it a redesign:** the tile source, the
font provider, the two network permissions and the Maps key placeholder are gone, and the map is a
Compose canvas over the track in metres with a graticule and a scale bar — no basemap, captioned as
not matched to a road. `PREVIEW_TELEMETRY` is gone and the screen says it has no data when it has
none. The card is labelled `m est. σ`. `LocalNavigationEstimator` carries a header naming the three
things it is not. `tests/test_android_demo_surface.py` fails if any of it comes back — verified by
reintroducing each violation and watching it fail, rather than by watching it pass.

**What is still open, and it is a decision rather than a task:** whether this module exists at all.
The honest demo of a filter this project can defend is the replay view in `android/` §3a, which
renders measured records and computes nothing. `android-ui` renders a toy estimator live. Both are
"the Android demo" and only one of them can be shown to a judge without a paragraph of explanation.
Fold it into the one Gradle root, or retire it — but decide, rather than shipping two.

The general lesson, which is the reason this section is in the handover rather than only in the
decision log: **both violations reached `main` through commit messages that described something
else** — "Add updated Android UI frontend" for the app, "chore: Update execution history and build
output cleanup lock files" for the 700-line replay view. Neither was reviewed against §2. A
constraint list that lives only in a document is a constraint list that gets bypassed; that is why
§2's rules now have a test each.

---

## 8. Questions to settle before writing code

1. **Seat A, and it is now the first question:** does `android-ui/` stay? §7. Two apps for one
   demo, one of them rendering a toy estimator live and the other rendering measured records, is a
   choice that has not been made — it is two people's work that met in `main`.
2. **Seat D:** Gate 1 is measured and fails (D-110), so the old form of this question is answered.
   The live one: is any Android work justified before the NHC and process-noise fix lands, or does
   this file wait on seat S?
3. **Seat P:** is a static offline road backdrop acceptable ahead of the CSR graph, and who owns
   the extract? Unchanged, and now concrete: the canvas in `android-ui` has a place to draw it.
4. **Seat S:** does the trajectory view stay a replay-only view until the October port, or is there
   an intermediate contract worth agreeing now?
5. **Whoever owns submission:** is the app ever listed on Play, or side-loaded only? Item 7 of §4
   depends entirely on the answer.

---

## 9. All the remaining work, in order

One list. Everything open on the Android side of this repo is here, whoever does it, ordered so
that each item is worth more than the one below it. An item says what it is, why, what it is
blocked on if anything, and how to tell it is done. Nothing in this list has been started unless
it says so.

| # | Work | Blocked on | Done when |
|---|---|---|---|
| 1 | **Run the logger on a phone: stationary recording on every team device** (§9.1–9.4) | nothing — one phone, one afternoon | **DONE (Samsung SM-A556E, 13 Sep 2026, D-116)** — `android/measured/S-IDR-20260913-031148-samsung-sm-a556e_session.json` committed (125.0 Hz, 8.1 ms Δt p95) |
| 2 | **Record one real drive** (§9.5), including the battery/thermal observation | item 1, a car, a mount | a drive-length sidecar per device, achieved rate over time noted |
| 3 | **Get the files off, validate, and write the numbers down** (§9.6–9.7) | items 1–2 | **Done for the stationary runs**: D-116 and D-119 rows, both sidecars in `android/measured/`, `docs/SPRINT_BOARD.md` §A ticked with the per-device table; drive numbers pending on item 2 |
| 4 | **See the replay view render a real trajectory record on a device** (§9.8) | a full `eval/run.py` run, which writes `trajectory_<seq>.json` | **DONE (13 Sep 2026, §3a)** — four tracks, ellipse, D-081 caption on the A55; `idr-trajectory/2` refused with a dialog |
| 5 | **CI uploads the debug APK** | nothing | **DONE** — `actions/upload-artifact` in `.github/workflows/android.yml` for logger and operator UI APKs |
| 6 | **Decide `android-ui/`, then act on it** (§7, §8 q1) | a decision, not code | either its Compose screens live under the one Gradle root at `android/` with one application id, or the directory is deleted — and `tests/test_android_demo_surface.py` is updated to match, since it currently reads both roots |

| 7 | **Allan run on our own hardware** from the `_raw_imu.csv` sidecar | items 1–2 (a long stationary segment, ≥ 20 min if the phone can be left on a desk that long) | **DONE (13 Sep 2026, D-119)** — 24.4 min desk session, `eval/allan.py` reads the sidecar at 125 Hz via `eval/loaders/android_raw.py`; gyro ARW 0.56–1.19 °/√hr, accel VRW 0.07–0.15 m/s/√hr, gyro B 18.6 °/hr, in `eval/figures/device/`; **no segment passed the quiet gate**, so the figures describe the desk-mounted phone and `FilterConfig` is untouched. Redo on a car seat with the engine off for a quiet one |
| 8 | **Road geometry under the replay track, offline** (§3b) | `maps/` — designed and sized, no code, no extract format defined | a static geometry file drawn under `TrajectoryMapView`, captioned as fixed geometry and not as a match; no network, no tiles (D-041, D-080) |
| 9 | **Instrumented test for the `startRecording` partial-failure path** (§4 item 4) | a decision to add Robolectric or an `androidTest` source set | a failed start leaves no foreground notification and no half-written session; test runs in CI |
| 10 | **Play Store readiness — only if the app is ever listed** (§4 item 7, §8 q5) | the listing decision | `HIGH_SAMPLING_RATE_SENSORS` justification, `foregroundServiceType` use case, privacy policy for location; **or** a line in `android/README.md` saying side-load only, and this item closed |
| 11 | **A release build type with signing** | item 10 answered yes | `assembleRelease` produces an installable APK; `applicationIdSuffix` stays on debug so the two can coexist on a phone |
| 12 | **The JNI layer and an on-device filter** — the October scope in `docs/IMPLEMENTATION_PLAN.md` §2 | `core/ffi/idr_core.h` having an implementation behind it (D-022, D-043, D-077); **not startable before that** | the header's `init` / `propagate` / update family / pose + covariance bound from Kotlin; `android-ui`'s `DeadReckoningBackend` (or its successor under item 6) fed by it instead of `LocalNavigationEstimator`. **Contract since D-125:** `TelemetryState` carries the 2×2 position covariance (`covNorthM2`, `covNorthEastM2`, `covEastM2`) and `poseElapsedMs` next to WGS-84 lat/lon; the filter fills all three from its P block. The `latPerMetre` flat-earth conversion in the demo estimator is fine for a demo and is not what should feed a map matcher — the filter's global frame should produce lat/lon itself |
| 13 | **Live demo UI on top of item 12** | item 12 | 10 Hz car icon, mode indicator, live uncertainty ellipse; on tunnel exit reject the first multipath fixes and run a short backward smoother so the drawn path corrects rather than snaps (`android/README.md` §Demo UI) |
| 14 | **Car-park mode and the online HMM matcher on device** | items 8, 12; `maps/README.md` §Car-park mode | out of scope until then; listed so it is not forgotten |

Items 1–3 are the entire reason the logger exists. Items 4–7 need no new design. Items 8–11 are
each waiting on one decision. Items 12–14 are blocked on the core, not on Android, and starting
them early produces code against an interface with nothing behind it.

What is **not** on the list, on purpose: the §5 quirks (`percentileMs` bin edge, dot sub-second
separator, calibrated-to-main / uncalibrated-to-sidecar). They are pinned by tests and are not
bugs.

The rest of this section is the procedure for items 1–4. It was written from the code, not from a
phone; the first person to follow it should correct it in place.

### 9.1 What you need

- **A physical phone, Android 8.0 or newer** (`minSdk 26`), with a gyroscope. The emulator is
  useless here: it has no real sensor clock and no GNSS.
- **USB debugging** on the phone: *Settings → About phone → tap Build number seven times →
  Developer options → USB debugging.* Then `adb devices` shows it. On this machine `adb` is at
  `C:\Android\platform-tools\adb`. **Wireless debugging works too and is how the team A55 is
  attached** (13 Sep): pair once from *Developer options → Wireless debugging*, and on later days
  `adb mdns services` lists it as `_adb-tls-connect._tcp` and `adb devices` connects on its own
  — no cable, no re-pairing, the port changes every time and does not matter. Give it a few
  seconds after the daemon starts; the first `adb devices` after `adb start-server` is empty.
- **A build**, from one of two places:
  - locally, after the §6 environment fix on Windows: `cd android && ./gradlew :app:installDebug`
    builds and installs in one step over USB;
  - or from anyone with a working toolchain: `./gradlew :app:assembleDebug` produces
    `android/app/build/outputs/apk/debug/app-debug.apk`, which installs anywhere with
    `adb install -r app-debug.apk`. CI builds exactly this APK on every PR but does not upload it
    — item 5.
- **A car and a mount.** The CSV is in the device frame, and the filter this data will one day feed
  estimates the phone-to-vehicle mounting as a state (D-048, `mount_rw`). A phone loose in a cup
  holder is a recording of the cup holder. Fix it rigidly — a windscreen or vent mount — and leave
  it there for the whole drive.

### 9.2 Before the first tap — device settings that silently ruin a recording

Each of these is a setting on the phone, not in the app, and the app cannot read any of them
(`SensorPrivacyManager` is not ours to call; `LoggerService.liveWarnings` says so). The achieved
rate on the front screen is the only detector.

| Setting | Where | Why |
|---|---|---|
| **Microphone access ON** | Android 12+: Quick Settings tile, or *Settings → Privacy → Microphone access* | With it off, the OS rate-limits *motion sensors* regardless of any permission the app holds (`android/README.md`, constraints table). The recording looks fine and the rate is wrong. |
| **Battery: Unrestricted** for IDR Logger | *Settings → Apps → IDR Logger → Battery* | Samsung, Xiaomi, Oppo, Vivo and OnePlus kill foreground services they consider idle, some within minutes. `LoggerService` returns `START_NOT_STICKY`, so a killed service **does not come back**; what survives is a sidecar still saying `"status": "recording"` (§4 item 2). On Xiaomi also enable *Autostart*; on Samsung take the app out of *Sleeping apps*. |
| **Location on, high accuracy** | *Settings → Location* | The app refuses to start without fine location — a recording with no GNSS reference track is one nothing can be measured against (`MainActivity.permissionLauncher`). |
| **Do not swipe the app out of Recents** during a recording | — | On several OEM skins that kills the process, foreground service included. Lock the screen instead; the service holds a partial wake lock and the notification keeps it alive. |
| **Storage** | — | The app warns under 1 GB free at start and stops itself at 128 MB (§4 item 3). At the default 100 Hz the raw sidecar is the bulk of the write; the app measures MB/min live and shows minutes remaining. |

### 9.3 Install and first launch

```bash
cd android && ./gradlew :app:installDebug
```

The installed app is **IDR Logger**, application id `org.idr26168.logger.debug` — the `.debug`
suffix is set in `app/build.gradle.kts` and there is no release build. Sessions therefore land at
`/sdcard/Android/data/org.idr26168.logger.debug/files/sessions/<session-id>/`, not the un-suffixed
path an older revision of `android/README.md` gave.

Tap **Start recording**. The app asks for location (choose *Precise* and *While using the app* —
the service is a `location`-typed foreground service, so background location is not needed) and,
on Android 13+, for notifications. Deny location and the status line says the recording was not
started, by design. `HIGH_SAMPLING_RATE_SENSORS` is install-time and asks nothing.

Then **stop immediately** and confirm a session folder appeared with four files in it (`adb shell
ls` or a file manager). If `getExternalFilesDir` returned null the recording went to internal
storage instead (`Session.dir`); the session line on the front screen prints the actual directory,
so read it rather than assuming.

### 9.4 The stationary run — two minutes on a desk, every phone

Phone flat, still, screen on so you can watch it. Start, wait until the `stream` table has settled
(the rate warning needs 200 accelerometer events, two seconds at 100 Hz; give it the full two
minutes so the percentiles mean something), and read:

| Line | What it should say | If it does not |
|---|---|---|
| `accelerometer` / `gyroscope` **`got Hz`** against **`req Hz`** (100 by default) | within a few percent of 100 | Below 80% the app prints the microphone-toggle warning. Fix the toggle (§9.2) and start again. Thermal throttling produces the same symptom, but not on a cold phone in two minutes. |
| `p95 ms` | the jitter number this item exists for; a few ms is typical, a value near `2 × 1000/req` means batching | Not a failure; it is the measurement. Note it. |
| `non-monotonic`, `batched` | absent or zero | Non-zero is also a measurement — it says the vendor HAL batches. Keep it. |
| `sensor timebase` | `ELAPSED_REALTIME` | `UPTIME` means the sensor clock stops in deep sleep; `UNKNOWN` means the two disagreed. All three are recorded in the sidecar (`SessionClock`); a phone that says `UNKNOWN` is one to ask about before a drive. |
| the GNSS line | irrelevant indoors | — |

Press **Stop recording**, never the OS. Stop rewrites the sidecar with the measurements; anything
else leaves it provisional. Then check, on the phone or after §9.6:

```bash
adb shell cat /sdcard/Android/data/org.idr26168.logger.debug/files/sessions/<id>/<id>_session.json
```

`"status"` must be `"complete"`. `sensors[].achieved_hz` and `sensors[].dt_ms.{median,p95,p99}`
are the numbers; `sensors[].sensor_name` / `vendor` say which part made them and are what a slide
should name alongside `device.model`.

Do this on every team phone before anyone drives. It takes five minutes per device and it is the
deliverable; the drive is the second recording, not the first. If a phone can be left on a desk
for 20 minutes or more, do that once too — it is the stationary segment item 7 needs. Then run
it through the same tool that produced the IO-VNBD seeds, into a directory of its own:

```bash
python -m eval.allan sessions/<id>/<id>_raw_imu.csv --out-dir eval/figures/device/<id>
```

It reads the sidecar at the rate it was recorded, gates stationarity on the bias-compensated gyro
and computes the curve on the raw one (`eval/loaders/android_raw.py` says why), and refuses to
write into `eval/figures/` itself. Expect `quiet NO` on a desk with a PC on it: D-045's gate is
answering whether the record measures the sensor or the surface, and a desk is not a parked car
either. `--include-noisy` then draws the curves anyway, labelled as describing the desk.

### 9.5 The drive

1. Mount the phone (§9.1) and plug it into power — sustained 100 Hz sensing plus GNSS is the case
   `android/README.md` says heats the SoC, and a drive that ends in a low-battery shutdown is a
   provisional sidecar.
2. Start recording **before moving**, with the car stationary and the phone already mounted. Wait
   for the GNSS line to show `fixes > 0` and `accuracy` under about 10 m; the first row with a fix
   is where the harness's ground-truth track begins, and the loader refuses to forward-fill
   (`io_vnbd.py`, "never forward-fill").
3. Sit still for **60 s** after the first fix. A stationary opening segment is what the SE₂(3)
   gravity-sign check needs (`IMPLEMENTATION_PLAN.md` R-8), and it costs a minute.
4. Drive **20–40 minutes** on ordinary roads, and include at least one GNSS-denied stretch if the
   route has one — an underpass, a covered car park, a tree-lined cut. `_gnss_status.csv` records
   per-satellite C/N₀ through it, which is the outage-detection evidence `GnssHub` exists to
   collect and which no IO-VNBD sequence carries. Two or three genuine stops at lights are worth
   having for the ZUPT/ZARU work D-115 names as next.
5. Glance at `got Hz` a few times through the drive. **A rate that falls partway through is the
   thermal-throttling signature** §4 item 6 asks for; note the elapsed time when it starts. Do not
   stop for it.
6. Stop with the car stationary, with the app's **Stop** button.

Do not run `android-ui` on the same phone at the same time. Two apps registering the same sensors
at different rates share one HAL, and the achieved rate of each is then a property of the pair.

### 9.6 Getting the files off

**Export Zip** on the front screen zips the *most recent* session folder — all four files
together, on purpose (§4 item 5) — through the system file picker, so it can go straight to Drive
or a USB stick. That is the path that always works.

`adb pull /sdcard/Android/data/org.idr26168.logger.debug/files/sessions/ ./sessions/` is the fast
path over a cable; on Android 13+ some vendors deny the shell user access to `Android/data` and it
fails with *Permission denied*, in which case use Export Zip. The A55 on Android 16 allows it, over
wireless debugging too. **From Git Bash, prefix adb with `MSYS_NO_PATHCONV=1`**: it otherwise
rewrites `/sdcard/...` into `C:/Program Files/Git/sdcard/...` before adb sees it, and `adb shell
ls` answers *No such file or directory* for a path that exists.

Then, on a laptop, the two checks that turn a folder into a result:

```bash
python -c "from eval.loaders.io_vnbd import load_sequence; s = load_sequence('sessions/<id>/<id>.csv'); print(s)"
```

This is the harness loader, unmodified. If it raises `LeakageError` the main CSV carries a column it
must not — which `tests/test_android_logger_schema.py` should have caught first, so that is a test
gap, not a logging choice. If it raises `ValueError: ... no GNSS reference channels`, the drive
never got a fix.

```bash
python -c "import json; d=json.load(open('sessions/<id>/<id>_session.json')); print(d['status'], d['device']['model']); [print(x['stream'], x['achieved_hz'], x['dt_ms']['p95']) for x in d['sensors']]"
```

`status` is `complete`, or the drive is unusable for rate and jitter (the CSVs are still fine as
data).

### 9.7 Where the numbers go

1. **Commit the sidecars, never the CSVs.** A `_session.json` is a few kilobytes and carries the
   device fingerprint, the sensor part numbers, the achieved rates and the Δt percentiles; put each
   one under `android/measured/<session-id>_session.json`. The CSVs are tens of megabytes and
   belong wherever the team keeps `data/` (`.gitignore` already excludes `data/IO-VNBD*`). Read the
   `warnings` array before committing: it is the recording's own account of anything that went
   wrong.
2. **Tick the `docs/SPRINT_BOARD.md` §A item** with a per-device table — model, sensor part,
   requested Hz, achieved Hz, Δt median / p95 / p99, timebase, drive length — one row per phone and
   a second row per drive on the same phone, because the stationary and the moving figures differ
   and the difference (thermal) is a finding.
3. **A `DECISION_LOG.md` row**, next free number after D-115, stating the measured figures and what
   they change: D-106 sized the logger at 100 Hz on the assumption a phone delivers it, and this is
   the first evidence either way. D-081's caption ("the 200 Hz FOG configuration is not
   demonstrated") stays exactly as it is regardless.
4. **Retire the "not measured" sentence** in §1 of this file and in `android/README.md` §Status,
   in the commit that adds the first sidecar. Both say they are waiting on this.

Anything quoted before step 1 is a number no artefact backs, which is the failure D-042 and §7 of
this file describe from opposite ends.

### 9.8 Replay, on the same phone, while it is in your hand

`ReplayActivity` (§3a) has been unit-tested and never seen on a screen. It needs an
`idr-trajectory/1` record, which `eval/run.py` writes to `eval/figures/trajectory_<seq>.json` on a
full run — the committed `eval/figures/` currently holds only `summary.json`, `windows.csv` and
the Allan artefacts, so run the sweep first (D-115 says the committed summary is D-110's and a
clean re-run is the one to cite anyway). Then:

```bash
adb push eval/figures/trajectory_S3a.json /sdcard/Download/
```

Open **Replay View** from the front screen, **Load JSON...**, pick the file from Downloads. Four
tracks, the 1σ ellipse growing through the outage and collapsing after it, `drift_pct` and
`yaw_error_deg` read from the record, and the D-081 caption. Then change the `schema` string in a
copy and confirm the view refuses it with a visible message rather than drawing something. That
closes the "still open" line in §3a and item 4 above.
