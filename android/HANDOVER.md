# Handover — seat A, Android: the map view and production readiness

**Written:** 3 Sep 2026, at the end of the session that built the foreground logger.
**Revised:** 10 Sep 2026 — §3a and §4 items 5 and 8 have landed, §8 is new, and §1's Gate 1 line
was wrong by a week.
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
| It has been seen **only in its idle state** | no session folder on any device |
| **No drive has ever been recorded** | no `*_session.json` exists anywhere |
| The CSV schema is pinned to the harness loader | `pytest tests/test_android_logger_schema.py` |
| Both Android surfaces are pinned to D-041/D-079/D-080 | `pytest tests/test_android_demo_surface.py` — 67 pass |
| It has JVM unit tests | `cd android && ./gradlew :app:test` — 56 `@Test` methods |
| CI compiles both Gradle roots | `.github/workflows/android.yml` |
| `./gradlew` exists at all | the wrapper was committed in `53e0053`; before that there was none |

**The single most important sentence in this file is unchanged:** the app's reason to exist — the
achieved sample rate and timestamp jitter per team device, asked for in
[IMPLEMENTATION_PLAN.md](../docs/IMPLEMENTATION_PLAN.md) §4 — is **not measured**. Everything below is
lower priority than one two-minute stationary recording followed by one real drive. Do that first.
If you build a map view before there is a single measured number, you have made the demo prettier
and the submission no more defensible.

That sentence has now been broken once, in the direction it warns about. `android-ui`'s launch
screen displayed `sampleRateHz = 200f` and `timestampJitterMs = 0.8f` as though measured, for five
days, on the two numbers this paragraph says do not exist. §8.

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

**Still open here:** load a `trajectory_*.json` from an actual `eval/run.py` run on a device and
look at it. It has been unit-tested, not seen.

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
