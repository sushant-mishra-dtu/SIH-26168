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
| **Use `TYPE_ACCELEROMETER_UNCALIBRATED` / `TYPE_GYROSCOPE_UNCALIBRATED`.** | Calibrated types silently subtract an OS bias estimate that the filter is *also* estimating. The two fight and the bias state is corrupted. |
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

## Demo UI — **cut for screening (D-039)**

> The screening demo is a **static replay renderer over harness output**: one self-contained HTML
> file, no build step, no server, no map SDK, and **no simulator**. A live cockpit fed by its own
> scenario generator can display numbers the evaluation never produced, which is the failure the
> frozen protocol exists to prevent. **The rule: if the renderer can display it, the harness
> produced it.** Everything below is the October target.

Vector map, smooth 10 Hz car icon, mode indicator, and a **visible uncertainty ellipse**. Judges
respond to watching the covariance grow inside the tunnel and collapse on exit — it makes the
architecture legible in a way a trajectory plot does not.

On tunnel exit: reject the first multipath-corrupted fixes and run a short backward smoother so the
drawn path corrects smoothly instead of snapping.

## Contract

The `core/ffi/` interface is agreed **in writing with seat S before either side writes against it.**

## Status

**Empty, and deliberately so.** The Android app and the JNI layer are **deferred past screening**;
the core is the deliverable and the app is the demo. Seat A's screening deliverable is the replay
renderer (D-039), which cannot start until `eval/run.py` produces output — and it must not be given
a simulator to fall back on.

Still worth doing off the critical path, because it is a slide in the deployment section whether or
not the app ships: build the minimal foreground-service logger and **measure the actual achieved
sample rate and timestamp jitter on every team device.** The nominal rate is not the real rate.
