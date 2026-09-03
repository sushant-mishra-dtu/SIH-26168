# android/ — foreground logger & demo UI

**Seat A.**

Two jobs: collect trustworthy data (Sprint 0 onward), and demo the system (Sprint 3). The core is
the deliverable; the app is the demo. Wrap it last.

## Non-negotiable platform facts

These are not preferences. Each one silently corrupts the data if ignored.

| Constraint | Consequence |
|---|---|
| **Since Android 9, background continuous sensors deliver no events.** | A **foreground service** with a persistent notification is mandatory for continuous logging. |
| **Since API 31, `registerListener()` caps at 200 Hz** without `HIGH_SAMPLING_RATE_SENSORS`; `SensorDirectChannel` caps near 50 Hz. | Declare the permission. Play Store review requires justifying it. |
| **If the user disables mic access via device toggles, motion sensors are rate-limited regardless of the permission.** | Detect and warn, or a collection run silently produces useless data. |
| **Use `TYPE_ACCELEROMETER_UNCALIBRATED` / `TYPE_GYROSCOPE_UNCALIBRATED`.** | Calibrated types silently subtract an OS bias estimate that the filter is *also* estimating. The two fight and the bias state is corrupted. **Amended by D-090:** both are recorded. Uncalibrated is right for what the *filter* consumes; D-085 established that IO-VNBD ships calibrated accel + a separate `GRAVITY` channel, so the harness-facing CSV must carry the same quantity or it means something different from every sequence it is compared against. Calibrated → main CSV, uncalibrated + the OS bias estimate → sidecar. |
| **Sensor timestamps are a monotonic device clock in ns, with jitter and batching. GNSS is UTC.** | Convert both to one base, model the offset, interpolate GNSS onto IMU epochs. **Never assume a nominal Δt.** |
| Sustained 200 Hz sensing + inference heats the SoC and throttles. | Budget for it; measure it over a real drive. |

## Threading

High-rate filter thread reading a lock-free ring buffer · NN inference at 1–10 Hz on a second thread
posting measurement updates · GNSS callback on a third · UI on main, reading a state snapshot.

## GNSS

Rely on **GPS + GLONASS + Galileo + BeiDou**. **NavIC is a bonus, not a dependency** — hardware
support exists on several chipsets, but signals are often filtered out by low-level drivers and
Android's GNSS API lacks standardised NavIC identifiers. Do not build anything that needs it.

Outage detection: `GnssStatus` per-satellite C/N₀ and count, `Location.getAccuracy()`, fix age.
Do not wait for the OS to declare loss — it reports a "good" coasted fix for a while after real
signal loss. Cross-check against the INS prediction and gate on innovation.

## Demo UI

Vector map, smooth 10 Hz car icon, mode indicator, and a **visible uncertainty ellipse**. Judges
respond to watching the covariance grow inside the tunnel and collapse on exit — it makes the
architecture legible in a way a trajectory plot does not.

On tunnel exit: reject the first multipath-corrupted fixes and run a short backward smoother so the
drawn path corrects smoothly instead of snapping.

## Contract

The `core/ffi/` interface is agreed **in writing with seat S before either side writes against it.**

---

# The logger

Built 3 Sep 2026. **The demo UI is not built and must not be started here** — `core/ffi/idr_core.h`
is an interface definition with no implementation behind it (D-022, D-043, D-077), so there is
nothing on-device for a demo to call, and the header says in as many words: *do not start the JNI
layer.* Seat A's screening demo is the replay renderer. The Android app + JNI remain scheduled for
October in [docs/IMPLEMENTATION_PLAN.md](../docs/IMPLEMENTATION_PLAN.md) §2, and this logger is the
Sprint 0–2 item that plan explicitly places **off** the critical path.

## What it does

One job, stated as an exit criterion rather than a feature: **produce the achieved sample rate and
the timestamp jitter for every team device**, on a real drive, in a file that can be pasted into a
slide. Everything else exists to make that number honest.

It also records a drive in a form the harness can already load, which costs nothing extra once the
schema is right.

## Files it writes

Per session, under `Android/data/org.idr26168.logger/files/sessions/<session-id>/`:

| File | Rate | Read by |
|---|---|---|
| `S-IDR-<stamp>-<device>.csv` | 10 Hz | `eval/loaders/io_vnbd.py::load_sequence`, unmodified |
| `..._raw_imu.csv` | requested rate, default 100 Hz | nothing yet — this is where an Allan run on our own hardware comes from |
| `..._gnss_status.csv` | per `GnssStatus` callback | nothing yet — per-satellite C/N₀, the outage-detection evidence |
| `..._session.json` | once | **the deliverable.** Device, per-stream achieved rate and Δt percentiles, sensor timebase, GNSS fix interval, warnings |

The main CSV carries the allowlist and **nothing else** — 24 columns, exactly. This is not tidiness:
`_canonicalise` guards every column in the file, so one invented column fails the whole recording
(D-089). That is why there are sidecars at all.

## Why the numbers in the main CSV are what they are

- **10 Hz rows.** `SAMPLE_RATE_HZ = 10` is a constant the outage windows are sized from; a 100 Hz
  file would be windowed as though it were ten times longer, silently (D-091).
- **km/h in `gps_speed_kmh`.** `Location.getSpeed()` is m/s. The conversion is on our side of the
  wall, where it is visible — the rule `core/ffi/idr_core.h` states for every unit crossing.
- **`GYROSCOPE X/Y/Z`, not `Yaw/Pitch/Roll`.** They normalise to `gyro_yaw/pitch/roll` either way,
  and `gyro_yaw` is device x, not the vertical axis. The X/Y/Z spelling is the one that does not
  invite a reader to assume otherwise.
- **Dot as the sub-second separator in `date`.** It parses both before and after D-086; the colon
  IO-VNBD ships parses only after (D-092).
- **Blank GNSS cells before the first fix, repeated cells between fixes.** What IO-VNBD does and
  what the loader expects — it takes fixes as position changes and refuses to forward-fill.

`tests/test_android_logger_schema.py` asserts all of this against the live loader, by parsing the
header out of `Channels.kt`. It runs in the normal `pytest` suite; no Android toolchain needed.

## Building it

The repo has JDK 17 and `adb`, but **no Android SDK platform or build-tools**. One-time setup:

```bash
sdkmanager --install "platforms;android-35" "build-tools;35.0.0" "platform-tools"
```

Then either open `android/` in Android Studio (it supplies Gradle and will generate the wrapper
jar), or with a system Gradle ≥ 8.9:

```bash
cd android && gradle wrapper && ./gradlew :app:assembleDebug
```

`gradle/wrapper/gradle-wrapper.properties` is committed; the wrapper **jar** is not, because it is a
binary and `gradle wrapper` regenerates it in a second.

## First run, before any drive matters

Record two minutes stationary on a desk and read the front screen. If `got Hz` is materially below
`req Hz`, stop: the device microphone toggle rate-limits motion sensors regardless of permissions,
and thermal throttling looks identical. The app says so in a warning rather than leaving it to be
discovered afterwards. Then record the numbers per device — that is the Sprint 0 exit criterion.

## Status

Logger written, not yet built or run: no Android SDK on the machine it was written on, and **no
number in `_session.json` has been produced by a real device.** Until a drive exists, the achieved
rate and jitter are unmeasured and nothing in this directory may be quoted.
